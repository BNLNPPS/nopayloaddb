import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional


SAFE_SQL_ALLOW = re.compile(
    r"^(CREATE INDEX CONCURRENTLY|ANALYZE|VACUUM|REINDEX CONCURRENTLY"
    r"|SET\s+\w[\w.]*\s*=|ALTER INDEX\s+\S+\s+RENAME TO"
    r"|ALTER SYSTEM SET\s+\w[\w.]*\s*="
    r"|ALTER TABLE\s+\"?\w+\"?\s+SET\s*\(\s*autovacuum_vacuum_scale_factor\s*="
    r"|CREATE TEMP TABLE\s+\S+\s+ON COMMIT DROP)\b",
    re.IGNORECASE,
)


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
    properties: dict[str, Any] = field(default_factory=dict)
    children: list["PlanNode"] = field(default_factory=list)


@dataclass
class RuleContext:
    queryid: str
    query_text: str
    mean_exec_time: float
    calls: int
    rows_count: int
    shared_blks_read: int
    shared_blks_hit: int
    total_exec_time: float
    stddev_exec_time: float
    has_locked_gt: bool = False
    payloadiov_dead_tuple_ratio: float = 0.0


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


class RuleEngine:
    def run(self, root: PlanNode, context: RuleContext) -> list[Suggestion]:
        nodes = list(iter_nodes(root))
        suggestions: list[Suggestion] = []

        suggestions.extend(self._rule_r1_large_seq_scan(nodes))
        suggestions.extend(self._rule_r2_stale_stats(nodes))
        suggestions.extend(self._rule_r3_hash_spill(nodes))
        suggestions.extend(self._rule_r4_external_sort(nodes))
        suggestions.extend(self._rule_r5_cache_miss(nodes))
        suggestions.extend(self._rule_r6_covering_idx_bypassed(nodes))
        suggestions.extend(self._rule_r7_heap_fetch_on_hot_path(nodes, context))
        suggestions.extend(self._rule_r8_repeated_identical_queries(context))
        suggestions.extend(self._rule_r9_locked_gt_high_read_volume(context))
        suggestions.extend(self._rule_r10_nested_loop_fanout(nodes))
        suggestions.extend(self._rule_r11_autovacuum_lag(context))
        suggestions.extend(self._rule_r12_gt_clone_slow_under_load(context))
        suggestions.extend(self._rule_r13_repeated_subquery_materialization(nodes, context))

        deduped: dict[str, Suggestion] = {}
        for s in suggestions:
            key = f"{s.rule_id}|{s.category}|{s.priority}|{s.message}|{s.safe_sql or ''}"
            deduped[key] = s
        return list(deduped.values())

    def _rule_r1_large_seq_scan(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
        out = []
        for n in nodes:
            if n.node_type == "Seq Scan" and n.actual_rows > 10000 and n.relation:
                out.append(
                    Suggestion(
                        rule_id="R1",
                        category="INDEX",
                        priority="HIGH",
                        message=(
                            f"Large Seq Scan detected on {n.relation} ({n.actual_rows} rows). "
                            "Consider adding an index for this access path."
                        ),
                        safe_sql=None,
                        confidence=0.9,
                    )
                )
        return out

    def _rule_r2_stale_stats(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
        out = []
        for n in nodes:
            if not n.relation or n.plan_rows <= 0:
                continue
            ratio = (n.actual_rows / n.plan_rows) if n.plan_rows else 0.0
            if ratio > 10.0 or (ratio < 0.1 and n.actual_rows > 0):
                out.append(
                    Suggestion(
                        rule_id="R2",
                        category="STATISTICS",
                        priority="HIGH",
                        message=(
                            f"Planner estimate mismatch on {n.relation}: plan_rows={n.plan_rows}, "
                            f"actual_rows={n.actual_rows}."
                        ),
                        safe_sql=validate_safe_sql(f'ANALYZE "{n.relation}";'),
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
                        message=f"Hash spill detected (Hash Batches={batches}). Increase work_mem.",
                        safe_sql=validate_safe_sql("SET work_mem = '64MB';"),
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
                        message="External merge sort detected. Increase work_mem.",
                        safe_sql=validate_safe_sql("SET work_mem = '64MB';"),
                        confidence=0.9,
                    )
                )
        return out

    def _rule_r5_cache_miss(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
        out = []
        for n in nodes:
            total_blocks = n.shared_hit_blocks + n.shared_read_blocks
            if total_blocks <= 0:
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

    def _rule_r6_covering_idx_bypassed(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
        for n in nodes:
            if n.node_type == "Seq Scan" and n.relation == "PayloadIOV":
                return [
                    Suggestion(
                        rule_id="R6",
                        category="STATISTICS",
                        priority="HIGH",
                        message=(
                            "PayloadIOV Seq Scan detected while covering_idx exists. "
                            "Likely stale statistics after bulk inserts."
                        ),
                        safe_sql=validate_safe_sql('ANALYZE "PayloadIOV";'),
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
        if has_index_scan and not has_index_only_scan and "LATERAL" in context.query_text.upper():
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
                    confidence=0.9,
                )
            ]
        return []

    def _rule_r8_repeated_identical_queries(self, context: RuleContext) -> list[Suggestion]:
        if context.calls > 1000 and context.stddev_exec_time < 5.0:
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
        if context.has_locked_gt and context.calls > 1000 and "PAYLOADIOV" in context.query_text.upper():
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

    def _rule_r10_nested_loop_fanout(self, nodes: Iterable[PlanNode]) -> list[Suggestion]:
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
        if context.mean_exec_time > 5000 and "GLOBALTAG" in text and "PAYLOADLIST" in text:
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
        if "LATERAL" not in context.query_text.upper():
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
    if sql and SAFE_SQL_ALLOW.match(sql.strip()):
        return sql.strip()
    return None


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


def _parse_plan_node(raw: dict[str, Any]) -> PlanNode:
    children = [_parse_plan_node(child) for child in (raw.get("Plans") or [])]

    return PlanNode(
        node_type=str(raw.get("Node Type") or "Unknown"),
        relation=raw.get("Relation Name"),
        startup_cost=float(raw.get("Startup Cost") or 0.0),
        total_cost=float(raw.get("Total Cost") or 0.0),
        plan_rows=int(raw.get("Plan Rows") or 0),
        actual_rows=int(raw.get("Actual Rows") or 0),
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
