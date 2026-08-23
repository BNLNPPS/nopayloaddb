import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


# Allowed statements. SET is session-scoped and ALTER SYSTEM SET shadows the ConfigMap.
SAFE_SQL_ALLOW = re.compile(
    r"^(?:"
    r"(?:CREATE INDEX CONCURRENTLY|ANALYZE|VACUUM|REINDEX CONCURRENTLY"
    r"|ALTER INDEX\s+\S+\s+RENAME TO"
    r"|CREATE TEMP TABLE\s+\S+\s+ON COMMIT DROP)\b"
    r'|ALTER TABLE\s+"?\w+"?\s+SET\s*\(\s*autovacuum_vacuum_scale_factor\s*='
    r")",
    re.IGNORECASE,
)

# Comment introducers can hide a second statement from a prefix match.
_SQL_SMUGGLING = ("--", "/*", "*/")


@dataclass
class PlanNode:
    node_type: str
    relation: Optional[str]
    startup_cost: float
    total_cost: float
    plan_rows: int
    actual_rows: int
    actual_time_ms: float
    shared_hit_blocks: int
    shared_read_blocks: int
    actual_loops: int = 1  # per-loop counts: total work is actual_rows * actual_loops
    # LIMIT/semi-join ancestor: fewer actual rows than estimated by design, not stale stats.
    beneath_early_stop: bool = False
    properties: dict[str, Any] = field(default_factory=dict)
    children: list["PlanNode"] = field(default_factory=list)


# Below these sizes a misestimate or cache miss is not worth an operator's attention.
MIN_ROWS_FOR_ESTIMATE_RULES = 1000
MIN_BLOCKS_FOR_CACHE_RULES = 1000
LARGE_SEQ_SCAN_ROWS = 10000


@dataclass
class RuleContext:
    queryid: str
    query_text: str
    # Cumulative since the last reset; rules about current load must use window_*.
    mean_exec_time: float
    calls: int
    rows_count: int
    shared_blks_read: int
    shared_blks_hit: int
    total_exec_time: float
    stddev_exec_time: float
    has_locked_gt: bool = False
    payloadiov_dead_tuple_ratio: float = 0.0

    # Since the previous collector cycle; None on first sighting.
    window_calls: Optional[int] = None
    window_mean_exec_time: Optional[float] = None

    # False for GENERIC_PLAN captures, which never execute: no actual rows or buffers.
    has_actuals: bool = True

    # indexdefs on the relations of interest, so a rule does not re-recommend one.
    existing_indexes: tuple = ()

    def hot_calls(self) -> int:
        """The window when we have one, otherwise 0 -- never the cumulative total."""
        return self.window_calls if self.window_calls is not None else 0


def _scan_predicate(node: "PlanNode") -> str:
    """Predicate text on a scan node, lowercased. Empty means the query asked for the
    whole relation, so a Seq Scan is optimal and no index recommendation applies."""
    parts = [
        node.properties.get("Filter"),
        node.properties.get("Recheck Cond"),
        node.properties.get("Index Cond"),
        node.properties.get("Join Filter"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def quote_ident(name: str) -> str:
    """Double-quote an identifier, escaping embedded quotes."""
    return '"' + str(name).replace('"', '""') + '"'


@dataclass
class Suggestion:
    rule_id: str
    category: str
    priority: str
    message: str
    safe_sql: Optional[str]
    confidence: float
    source: str = "rule_engine"
    parameter_name: Optional[str] = None
    # Must hold for the remedy to pay off; surfaced to the operator.
    prerequisite: Optional[str] = None


class RuleEngine:
    def run(self, root: PlanNode, context: RuleContext) -> list[Suggestion]:
        nodes = list(iter_nodes(root))
        suggestions: list[Suggestion] = []

        suggestions.extend(self._rule_r1_large_seq_scan(nodes, context))
        suggestions.extend(self._rule_r2_stale_stats(nodes, context))
        suggestions.extend(self._rule_r3_hash_spill(nodes))
        suggestions.extend(self._rule_r4_external_sort(nodes))
        suggestions.extend(self._rule_r5_cache_miss(nodes, context))
        suggestions.extend(self._rule_r6_covering_idx_bypassed(nodes, context))
        suggestions.extend(self._rule_r7_heap_fetch_on_hot_path(nodes, context))
        suggestions.extend(self._rule_r8_repeated_identical_queries(context))
        suggestions.extend(self._rule_r9_locked_gt_high_read_volume(context))
        suggestions.extend(self._rule_r10_nested_loop_fanout(nodes, context))
        suggestions.extend(self._rule_r11_autovacuum_lag(context))
        suggestions.extend(self._rule_r12_gt_clone_slow_under_load(context))
        suggestions.extend(self._rule_r13_repeated_subquery_materialization(nodes, context))

        deduped: dict[str, Suggestion] = {}
        for s in suggestions:
            key = f"{s.rule_id}|{s.category}|{s.priority}|{s.message}|{s.safe_sql or ''}"
            deduped[key] = s
        return list(deduped.values())

    def _rule_r1_large_seq_scan(self, nodes: Iterable[PlanNode], context: RuleContext) -> list[Suggestion]:
        if not context.has_actuals:
            return []
        out = []
        for n in nodes:
            # Actual Rows is per-loop: 10 rows x 5000 loops is 50k rows of work.
            total_rows = n.actual_rows * max(1, n.actual_loops)
            if not (n.node_type == "Seq Scan" and total_rows > LARGE_SEQ_SCAN_ROWS and n.relation):
                continue
            # An unfiltered full-table read has no predicate for an index to serve.
            if not _scan_predicate(n):
                continue
            if True:
                out.append(
                    Suggestion(
                        rule_id="R1",
                        category="INDEX",
                        priority="HIGH",
                        message=(
                            f"Large Seq Scan detected on {n.relation} ({total_rows} rows "
                            f"across {max(1, n.actual_loops)} loop(s)). "
                            "Consider adding an index for this access path."
                        ),
                        safe_sql=None,
                        confidence=0.9,
                    )
                )
        return out

    def _rule_r2_stale_stats(self, nodes: Iterable[PlanNode], context: RuleContext) -> list[Suggestion]:
        if not context.has_actuals:
            return []
        out = []
        for n in nodes:
            if not n.relation or n.plan_rows <= 0:
                continue
            # Without this floor the rule fires on every trivial node in the plan.
            if max(n.actual_rows, n.plan_rows) < MIN_ROWS_FOR_ESTIMATE_RULES:
                continue
            ratio = (n.actual_rows / n.plan_rows) if n.plan_rows else 0.0
            # Beneath a LIMIT the executor stops early, so fewer rows than estimated is correct.
            over_estimated = ratio < 0.1 and n.actual_rows > 0
            if over_estimated and n.beneath_early_stop:
                continue
            if ratio > 10.0 or over_estimated:
                out.append(
                    Suggestion(
                        rule_id="R2",
                        category="STATISTICS",
                        priority="HIGH",
                        message=(
                            f"Planner estimate mismatch on {n.relation}: plan_rows={n.plan_rows}, "
                            f"actual_rows={n.actual_rows}."
                        ),
                        safe_sql=validate_safe_sql(f"ANALYZE {quote_ident(n.relation)};"),
                        confidence=0.95,
                    )
                )
        return out

    def _rule_r3_hash_spill(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
        out = []
        for n in nodes:
            batches = int((n.properties.get("Hash Batches") or 0) or 0)
            if n.node_type == "Hash" and batches > 1:
                out.append(
                    Suggestion(
                        rule_id="R3",
                        category="WORK_MEM",
                        priority="MEDIUM",
                        message=(
                            f"Hash spill detected (Hash Batches={batches}); the join did not "
                            "fit in work_mem. Raise work_mem in the psql-conf ConfigMap and "
                            "roll the StatefulSet. Not auto-appliable: a session-level SET "
                            "would change only the applying connection, never Django's workers."
                        ),
                        safe_sql=None,
                        confidence=0.9,
                    )
                )
        return out

    def _rule_r4_external_sort(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
        out = []
        for n in nodes:
            sort_method = str(n.properties.get("Sort Method") or "").lower()
            if n.node_type == "Sort" and "external merge" in sort_method:
                out.append(
                    Suggestion(
                        rule_id="R4",
                        category="WORK_MEM",
                        priority="MEDIUM",
                        message=(
                            "External merge sort detected: the sort spilled to disk. Raise "
                            "work_mem in the psql-conf ConfigMap and roll the StatefulSet. "
                            "Not auto-appliable: a session-level SET would change only the "
                            "applying connection, never Django's workers."
                        ),
                        safe_sql=None,
                        confidence=0.9,
                    )
                )
        return out

    def _rule_r5_cache_miss(self, nodes: Iterable[PlanNode], context: RuleContext) -> list[Suggestion]:
        if not context.has_actuals:
            return []
        out = []
        for n in nodes:
            total_blocks = n.shared_hit_blocks + n.shared_read_blocks
            # One miss out of two blocks is a 50% miss ratio and means nothing.
            if total_blocks < MIN_BLOCKS_FOR_CACHE_RULES:
                continue
            miss_ratio = n.shared_read_blocks / total_blocks
            if miss_ratio > 0.10:
                out.append(
                    Suggestion(
                        rule_id="R5",
                        category="SHARED_BUFFERS",
                        priority="MEDIUM",
                        message=(
                            f"High cache miss ratio ({miss_ratio:.2%}) detected. "
                            "Consider increasing shared_buffers."
                        ),
                        safe_sql=None,
                        confidence=0.8,
                    )
                )
                break
        return out

    def _rule_r6_covering_idx_bypassed(self, nodes: Iterable[PlanNode], context: RuleContext) -> list[Suggestion]:
        """PayloadIOV scanned sequentially on the covering-index path. Index present
        means stale statistics (ANALYZE); index absent means it must be created."""
        if not context.has_actuals:
            return []
        for n in nodes:
            if not (n.node_type == "Seq Scan" and n.relation == "PayloadIOV"
                    and n.actual_rows * max(1, n.actual_loops) >= MIN_ROWS_FOR_ESTIMATE_RULES):
                continue
            # Only a scan filtering on payload_list_id was ever a candidate for it.
            if "payload_list_id" not in _scan_predicate(n):
                continue

            covering_exists = any(
                "payload_list_id" in (idx or "") and "comb_iov" in (idx or "")
                for idx in context.existing_indexes
            )
            rows = n.actual_rows * max(1, n.actual_loops)

            if covering_exists:
                return [
                    Suggestion(
                        rule_id="R6",
                        category="STATISTICS",
                        priority="HIGH",
                        message=(
                            f"PayloadIOV sequentially scanned ({rows} rows) on the "
                            "payload_list_id access path even though a covering index on "
                            "(payload_list_id, comb_iov) exists. The planner is declining "
                            "it, which after a bulk insert means stale statistics."
                        ),
                        safe_sql=validate_safe_sql('ANALYZE "PayloadIOV";'),
                        confidence=0.95,
                    )
                ]
            return [
                Suggestion(
                    rule_id="R6",
                    category="INDEX",
                    priority="HIGH",
                    message=(
                        f"PayloadIOV sequentially scanned ({rows} rows) on the "
                        "payload_list_id access path and NO covering index on "
                        "(payload_list_id, comb_iov) exists. ANALYZE will not help here -- "
                        "the index has to be created."
                    ),
                    safe_sql=validate_safe_sql(
                        'CREATE INDEX CONCURRENTLY covering_idx ON "PayloadIOV" '
                        '(payload_list_id, comb_iov DESC NULLS LAST);'
                    ),
                    confidence=0.95,
                )
            ]
        return []

    def _rule_r7_heap_fetch_on_hot_path(
        self, nodes: Iterable[PlanNode], context: RuleContext
    ) -> list[Suggestion]:
        has_index_scan = any(n.node_type == "Index Scan" and n.relation == "PayloadIOV" for n in nodes)
        has_index_only_scan = any(
            n.node_type == "Index Only Scan" and n.relation == "PayloadIOV" for n in nodes
        )
        if not (has_index_scan and not has_index_only_scan
                and "LATERAL" in context.query_text.upper()):
            return []

        # Otherwise the rule re-fires every cycle after being applied.
        if any("covering_idx_v2" in (idx or "") for idx in context.existing_indexes):
            return []
        if any("INCLUDE" in (idx or "").upper() and "PayloadIOV" in (idx or "")
               for idx in context.existing_indexes):
            return []

        return [
                Suggestion(
                    rule_id="R7",
                    category="INDEX_COVERAGE",
                    priority="HIGH",
                    message=(
                        "PayloadIOV hot path uses Index Scan instead of Index Only Scan. "
                        "Consider extending covering_idx with INCLUDE columns."
                    ),
                    safe_sql=validate_safe_sql(
                        'CREATE INDEX CONCURRENTLY covering_idx_v2 ON "PayloadIOV" '
                        '(payload_list_id, comb_iov DESC NULLS LAST) '
                        'INCLUDE (payload_url, checksum, size, major_iov, minor_iov, '
                        'major_iov_end, minor_iov_end);'
                    ),
                    prerequisite=(
                        "An Index Only Scan skips the heap only for pages marked all-visible, "
                        "so VACUUM \"PayloadIOV\" after building this index -- otherwise it "
                        "still performs heap fetches and delivers nothing measurable."
                    ),
                    confidence=0.9,
                )
        ]

    def _rule_r8_repeated_identical_queries(self, context: RuleContext) -> list[Suggestion]:
        if context.hot_calls() > 1000 and context.stddev_exec_time < 5.0:
            return [
                Suggestion(
                    rule_id="R8",
                    category="CACHE",
                    priority="MEDIUM",
                    message=(
                        "High-volume stable query detected. Consider Redis cache keyed by "
                        "(gtName, majorIOV, minorIOV)."
                    ),
                    safe_sql=None,
                    confidence=0.85,
                )
            ]
        return []

    def _rule_r9_locked_gt_high_read_volume(self, context: RuleContext) -> list[Suggestion]:
        if (context.has_locked_gt and context.hot_calls() > 1000
                and "PAYLOADIOV" in context.query_text.upper()):
            return [
                Suggestion(
                    rule_id="R9",
                    category="MATERIALIZED_VIEW",
                    priority="MEDIUM",
                    message=(
                        "High read volume with locked GlobalTag detected. Consider precomputing "
                        "latest valid IOV per PayloadType via materialized view."
                    ),
                    safe_sql=None,
                    confidence=0.8,
                )
            ]
        return []

    def _rule_r10_nested_loop_fanout(self, nodes: Iterable[PlanNode], context: RuleContext) -> list[Suggestion]:
        if not context.has_actuals:
            return []
        out = []
        for n in nodes:
            loops = int((n.properties.get("Actual Loops") or 1) or 1)
            if n.node_type == "Nested Loop" and loops > 0 and (n.actual_rows / loops) > 100:
                out.append(
                    Suggestion(
                        rule_id="R10",
                        category="INDEX",
                        priority="MEDIUM",
                        message=(
                            "Nested Loop fanout detected (>100 rows per outer loop). "
                            "Consider join-order or inner relation indexing improvements."
                        ),
                        safe_sql=None,
                        confidence=0.75,
                    )
                )
        return out

    def _rule_r11_autovacuum_lag(self, context: RuleContext) -> list[Suggestion]:
        if context.payloadiov_dead_tuple_ratio > 0.05:
            return [
                Suggestion(
                    rule_id="R11",
                    category="VACUUM",
                    priority="HIGH",
                    message=(
                        f"PayloadIOV autovacuum lag detected (dead tuple ratio "
                        f"{context.payloadiov_dead_tuple_ratio:.2%})."
                    ),
                    safe_sql=validate_safe_sql('VACUUM (ANALYZE) "PayloadIOV";'),
                    confidence=0.9,
                )
            ]
        return []

    def _rule_r12_gt_clone_slow_under_load(self, context: RuleContext) -> list[Suggestion]:
        text = context.query_text.upper()
        window_mean = (context.window_mean_exec_time
                       if context.window_mean_exec_time is not None
                       else context.mean_exec_time)
        if window_mean > 5000 and "GLOBALTAG" in text and "PAYLOADLIST" in text:
            return [
                Suggestion(
                    rule_id="R12",
                    category="CLONE",
                    priority="MEDIUM",
                    message=(
                        "Potential GT clone slowdown under load detected. Consider off-peak "
                        "scheduling for clone operations."
                    ),
                    safe_sql=None,
                    confidence=0.7,
                )
            ]
        return []

    def _rule_r13_repeated_subquery_materialization(
        self, nodes: Iterable[PlanNode], context: RuleContext
    ) -> list[Suggestion]:
        if not context.has_actuals or "LATERAL" not in context.query_text.upper():
            return []

        high_loop_nodes = [
            n for n in nodes if int((n.properties.get("Actual Loops") or 1) or 1) > 100
        ]
        if high_loop_nodes:
            return [
                Suggestion(
                    rule_id="R13",
                    category="TEMP_TABLE",
                    priority="LOW",
                    message=(
                        "Repeated subquery execution detected across LATERAL iterations. "
                        "Consider temporary table materialization for intermediate lookups."
                    ),
                    safe_sql=validate_safe_sql(
                        'CREATE TEMP TABLE _gt_lookup ON COMMIT DROP AS '
                        'SELECT id, name, status_id FROM "GlobalTag" WHERE name = %(my_gt)s;'
                    ),
                    confidence=0.7,
                )
            ]
        return []


def validate_safe_sql(sql: Optional[str]) -> Optional[str]:
    """Return `sql` if allow-listed, else None.

    SAFE_SQL_ALLOW anchors only at the start, so a prefix match is not enough:
    `ANALYZE "x"; DROP INDEX y` matches ANALYZE. Must be exactly one statement.
    """
    if not sql:
        return None

    statement = sql.strip()
    if not statement:
        return None

    body = statement.rstrip().rstrip(";").rstrip()
    if ";" in body:
        return None
    if any(token in body for token in _SQL_SMUGGLING):
        return None
    if not SAFE_SQL_ALLOW.match(body):
        return None

    return statement


def is_executable_safe_sql(sql: Optional[str]) -> bool:
    """Whether validated `sql` can be handed to cursor.execute(). R13's advice
    contains a %(name)s placeholder psycopg would try to bind, so it cannot."""
    if not validate_safe_sql(sql):
        return False
    return "%" not in sql


def parse_explain_plan(plan_json: Any) -> PlanNode:
    root = _extract_root_plan_node(plan_json)
    return _parse_plan_node(root)


def _extract_root_plan_node(plan_json: Any) -> dict[str, Any]:
    if isinstance(plan_json, list) and plan_json:
        first = plan_json[0]
        if isinstance(first, dict) and isinstance(first.get("Plan"), dict):
            return first["Plan"]
    if isinstance(plan_json, dict) and isinstance(plan_json.get("Plan"), dict):
        return plan_json["Plan"]
    raise ValueError("Unexpected EXPLAIN JSON format: missing root Plan node")


# Node types whose children stop as soon as enough rows have been produced.
_EARLY_STOP_NODE_TYPES = frozenset({"Limit"})
_EARLY_STOP_JOIN_TYPES = frozenset({"Semi", "Anti"})


def _stops_children_early(raw: dict[str, Any]) -> bool:
    return (str(raw.get("Node Type") or "") in _EARLY_STOP_NODE_TYPES
            or str(raw.get("Join Type") or "") in _EARLY_STOP_JOIN_TYPES)


def _parse_plan_node(raw: dict[str, Any], beneath_early_stop: bool = False) -> PlanNode:
    child_early_stop = beneath_early_stop or _stops_children_early(raw)
    children = [_parse_plan_node(child, child_early_stop) for child in (raw.get("Plans") or [])]

    return PlanNode(
        node_type=str(raw.get("Node Type") or "Unknown"),
        relation=raw.get("Relation Name"),
        startup_cost=float(raw.get("Startup Cost") or 0.0),
        total_cost=float(raw.get("Total Cost") or 0.0),
        plan_rows=int(raw.get("Plan Rows") or 0),
        actual_rows=int(raw.get("Actual Rows") or 0),
        actual_loops=int(raw.get("Actual Loops") or 1),
        beneath_early_stop=beneath_early_stop,
        actual_time_ms=float(raw.get("Actual Total Time") or 0.0),
        shared_hit_blocks=int(raw.get("Shared Hit Blocks") or 0),
        shared_read_blocks=int(raw.get("Shared Read Blocks") or 0),
        properties=dict(raw),
        children=children,
    )


def iter_nodes(root: PlanNode) -> Iterable[PlanNode]:
    stack = [root]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def suggestion_hash(plan_id: int, suggestion: Suggestion) -> str:
    payload = (
        f"{plan_id}|{suggestion.rule_id}|{suggestion.category}|{suggestion.priority}|"
        f"{suggestion.message}|{suggestion.safe_sql or ''}|{suggestion.source}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
