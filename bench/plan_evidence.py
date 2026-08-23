"""Plan-shape evidence and per-rule postconditions.

A latency drop alone proves nothing; the decisive evidence is that the plan
changed as predicted. Walks raw EXPLAIN JSON so bench/ stays Django-free.
"""

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

INDEXED_SCAN_TYPES = frozenset({
    "Index Scan", "Index Only Scan", "Bitmap Index Scan", "Bitmap Heap Scan",
})
IN_MEMORY_SORT_METHODS = ("quicksort", "top-n heapsort")

DEFAULT_TARGET_RELATION = "PayloadIOV"

ESTIMATE_HEALTHY_FACTOR = 2.0    # R2/R6: estimate within this factor of reality is healthy
HEAP_FETCH_ZERO_FRACTION = 0.01  # R7: heap fetches below this share of rows count as zero
HIT_RATIO_MIN_GAIN = 0.01        # R5: minimum absolute gain in windowed hit ratio
R1_LARGE_SEQ_SCAN_ROWS = 10000   # R1 only ever fires above this, so its check matches


@dataclass
class PlanFeatures:
    node_types: list = field(default_factory=list)
    scan_types_by_relation: dict = field(default_factory=dict)  # relation -> set of node types
    heap_fetches_by_relation: dict = field(default_factory=dict)
    actual_rows_by_relation: dict = field(default_factory=dict)
    estimate_ratio_by_relation: dict = field(default_factory=dict)  # actual/plan, per loop
    max_hash_batches: Optional[int] = None
    sort_methods: list = field(default_factory=list)
    max_inner_rows_per_outer: Optional[float] = None
    shared_read_blocks: int = 0
    shared_hit_blocks: int = 0
    total_time_ms: Optional[float] = None

    def scans_on(self, relation: str) -> set:
        return self.scan_types_by_relation.get(relation, set())

    def has_external_sort(self) -> bool:
        return any("external" in m.lower() for m in self.sort_methods)

    def worst_estimate_deviation(self) -> Optional[float]:
        """max |log10(actual / plan)|; 0 is a perfect estimate."""
        devs = [abs(math.log10(r)) for r in self.estimate_ratio_by_relation.values() if r and r > 0]
        return max(devs) if devs else None

    def to_dict(self) -> dict:
        return {
            "node_types": self.node_types,
            "scan_types_by_relation": {k: sorted(v) for k, v in self.scan_types_by_relation.items()},
            "heap_fetches_by_relation": self.heap_fetches_by_relation,
            "estimate_ratio_by_relation": self.estimate_ratio_by_relation,
            "worst_estimate_deviation_log10": self.worst_estimate_deviation(),
            "max_hash_batches": self.max_hash_batches,
            "sort_methods": self.sort_methods,
            "max_inner_rows_per_outer": self.max_inner_rows_per_outer,
            "shared_read_blocks": self.shared_read_blocks,
            "shared_hit_blocks": self.shared_hit_blocks,
            "total_time_ms": self.total_time_ms,
        }


def _root_of(plan_json):
    if isinstance(plan_json, list) and plan_json:
        first = plan_json[0]
        if isinstance(first, dict) and isinstance(first.get("Plan"), dict):
            return first["Plan"]
    if isinstance(plan_json, dict) and isinstance(plan_json.get("Plan"), dict):
        return plan_json["Plan"]
    if isinstance(plan_json, dict) and "Node Type" in plan_json:
        return plan_json
    raise ValueError("Unexpected EXPLAIN JSON format: missing root Plan node")


def _walk(node, depth=0):
    yield node, depth
    for child in node.get("Plans") or []:
        yield from _walk(child, depth + 1)


def extract_features(plan_json) -> PlanFeatures:
    root = _root_of(plan_json)
    f = PlanFeatures()
    f.total_time_ms = root.get("Actual Total Time")

    hash_batches = []
    inner_fanouts = []

    for node, _ in _walk(root):
        node_type = str(node.get("Node Type") or "Unknown")
        f.node_types.append(node_type)

        relation = node.get("Relation Name")
        if relation:
            f.scan_types_by_relation.setdefault(relation, set()).add(node_type)

            actual_rows = node.get("Actual Rows")
            plan_rows = node.get("Plan Rows")
            if actual_rows is not None:
                prev = f.actual_rows_by_relation.get(relation)
                f.actual_rows_by_relation[relation] = max(prev or 0, actual_rows)
            if actual_rows is not None and plan_rows:
                ratio = (actual_rows or 0) / plan_rows
                prev = f.estimate_ratio_by_relation.get(relation)
                if prev is None or abs(math.log10(ratio or 1e-9)) > abs(math.log10(prev or 1e-9)):
                    f.estimate_ratio_by_relation[relation] = ratio

            if "Heap Fetches" in node:
                f.heap_fetches_by_relation[relation] = node.get("Heap Fetches")

        if node.get("Hash Batches") is not None:
            hash_batches.append(node["Hash Batches"])
        if node.get("Original Hash Batches") is not None:
            hash_batches.append(node["Original Hash Batches"])

        if node.get("Sort Method"):
            f.sort_methods.append(str(node["Sort Method"]))

        f.shared_read_blocks += int(node.get("Shared Read Blocks") or 0)
        f.shared_hit_blocks += int(node.get("Shared Hit Blocks") or 0)

        if node_type == "Nested Loop":
            for child in (node.get("Plans") or [])[1:]:
                rows = child.get("Actual Rows")
                if rows is not None:
                    inner_fanouts.append(float(rows))

    f.max_hash_batches = max(hash_batches) if hash_batches else None
    f.max_inner_rows_per_outer = max(inner_fanouts) if inner_fanouts else None
    return f


# --- Postconditions ---

CONFIRMED = "confirmed"
REFUTED = "refuted"
UNVERIFIABLE = "unverifiable"
NOT_CHECKED = "not_checked"


@dataclass
class MechanismContext:
    """Non-plan evidence a postcondition may need."""
    target_relation: str = DEFAULT_TARGET_RELATION
    table_stats_before: dict = field(default_factory=dict)   # relation -> row dict
    table_stats_after: dict = field(default_factory=dict)
    baseline_hit_ratio: Optional[float] = None               # windowed
    optimized_hit_ratio: Optional[float] = None


@dataclass
class PostconditionResult:
    rule_id: str
    status: str
    detail: str
    evidence: dict = field(default_factory=dict)

    @property
    def checked(self) -> bool:
        return self.status in (CONFIRMED, REFUTED)

    @property
    def holds(self) -> Optional[bool]:
        if self.status == CONFIRMED:
            return True
        if self.status == REFUTED:
            return False
        return None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "status": self.status,
            "checked": self.checked,
            "holds": self.holds,
            "detail": self.detail,
            "evidence": self.evidence,
        }


_POSTCONDITIONS: dict = {}


def register_postcondition(*rule_ids: str) -> Callable:
    """Register a checker for one or more rule ids."""
    def wrap(fn):
        for rid in rule_ids:
            _POSTCONDITIONS[rid] = fn
        return fn
    return wrap


# Remedies this harness cannot observe, so they never silently pass.
_UNVERIFIABLE_REASONS = {
    "R8": "Redis caching is an application-layer change; this harness measures the "
          "database, so a hit-rate change cannot be attributed to it here.",
    "R9": "Materialized-view precomputation is advisory and requires an application "
          "query rewrite; the benchmarked endpoint still issues the original query.",
    "R12": "Off-peak scheduling changes when the clone runs, not how it performs; "
           "there is no plan-shape or metric postcondition to check.",
    "R13": "CREATE TEMP TABLE is advisory only (never auto-applied) and is scoped to "
           "the suggesting session, so it cannot affect the benchmarked requests.",
}


def check_postcondition(rule_id, before, after, ctx: Optional[MechanismContext] = None) -> PostconditionResult:
    """Evaluate the mechanism postcondition for `rule_id`."""
    ctx = ctx or MechanismContext()

    if rule_id in _UNVERIFIABLE_REASONS:
        return PostconditionResult(rule_id, UNVERIFIABLE, _UNVERIFIABLE_REASONS[rule_id])

    checker = _POSTCONDITIONS.get(rule_id)
    if checker is None:
        return PostconditionResult(
            rule_id, NOT_CHECKED,
            f"No postcondition registered for {rule_id}; mechanism was not verified.",
        )

    if rule_id != "R11" and (before is None or after is None):
        return PostconditionResult(
            rule_id, UNVERIFIABLE,
            "No EXPLAIN plan captured for one or both conditions, so the plan-shape "
            "change could not be compared.",
        )

    return checker(before, after, ctx)


def registered_rules() -> list:
    return sorted(set(_POSTCONDITIONS) | set(_UNVERIFIABLE_REASONS))


@register_postcondition("R1")
def _r1_seq_scan_becomes_indexed(before, after, ctx):
    # Only scans large enough to have triggered R1; a small Seq Scan is correct.
    offenders = {
        rel: types for rel, types in before.scan_types_by_relation.items()
        if "Seq Scan" in types
        and (before.actual_rows_by_relation.get(rel) or 0) > R1_LARGE_SEQ_SCAN_ROWS
    }
    if not offenders:
        return PostconditionResult(
            "R1", UNVERIFIABLE,
            f"Baseline plan has no Seq Scan over {R1_LARGE_SEQ_SCAN_ROWS} rows, so there was "
            "nothing for an index to replace.",
            {"baseline_scans": {r: sorted(t) for r, t in before.scan_types_by_relation.items()},
             "baseline_rows": before.actual_rows_by_relation},
        )
    still_seq = [rel for rel in offenders if "Seq Scan" in after.scans_on(rel)]
    now_indexed = [rel for rel in offenders if after.scans_on(rel) & INDEXED_SCAN_TYPES]
    evidence = {
        "baseline_large_seq_scans": sorted(offenders),
        "baseline_rows": {r: before.actual_rows_by_relation.get(r) for r in offenders},
        "row_threshold": R1_LARGE_SEQ_SCAN_ROWS,
        "still_seq_scanned": sorted(still_seq),
        "now_index_scanned": sorted(now_indexed),
    }
    if not still_seq and now_indexed:
        return PostconditionResult("R1", CONFIRMED,
                                   f"Seq Scan replaced by an index scan on {', '.join(sorted(now_indexed))}.",
                                   evidence)
    return PostconditionResult("R1", REFUTED,
                               f"Large Seq Scan on {', '.join(sorted(still_seq))} survived the "
                               "change; the planner did not adopt the new index.",
                               evidence)


@register_postcondition("R2")
def _r2_estimates_converge(before, after, ctx):
    before_dev = before.worst_estimate_deviation()
    after_dev = after.worst_estimate_deviation()
    evidence = {
        "before_worst_deviation_log10": before_dev,
        "after_worst_deviation_log10": after_dev,
        "before_ratios": before.estimate_ratio_by_relation,
        "after_ratios": after.estimate_ratio_by_relation,
        "healthy_factor": ESTIMATE_HEALTHY_FACTOR,
    }
    if before_dev is None or after_dev is None:
        return PostconditionResult("R2", UNVERIFIABLE,
                                   "Plan rows / actual rows unavailable on one side.", evidence)
    healthy = math.log10(ESTIMATE_HEALTHY_FACTOR)
    if after_dev < before_dev and after_dev <= healthy:
        return PostconditionResult(
            "R2", CONFIRMED,
            f"Planner estimates converged toward reality (worst deviation "
            f"{10 ** before_dev:.1f}x -> {10 ** after_dev:.1f}x).", evidence)
    return PostconditionResult(
        "R2", REFUTED,
        f"Estimates did not converge (worst deviation {10 ** before_dev:.1f}x -> "
        f"{10 ** after_dev:.1f}x); ANALYZE did not fix the row estimate.", evidence)


@register_postcondition("R6")
def _r6_covering_index_used(before, after, ctx):
    rel = ctx.target_relation
    before_scans, after_scans = before.scans_on(rel), after.scans_on(rel)
    before_dev = before.worst_estimate_deviation()
    after_dev = after.worst_estimate_deviation()
    evidence = {
        "relation": rel,
        "before_scan_types": sorted(before_scans),
        "after_scan_types": sorted(after_scans),
        "before_worst_deviation_log10": before_dev,
        "after_worst_deviation_log10": after_dev,
    }
    if not before_scans:
        return PostconditionResult("R6", UNVERIFIABLE,
                                   f"{rel} does not appear in the baseline plan.", evidence)
    if "Seq Scan" not in before_scans:
        return PostconditionResult("R6", UNVERIFIABLE,
                                   f"{rel} was not sequentially scanned in the baseline, so "
                                   "the covering index was not being bypassed.", evidence)
    if "Seq Scan" not in after_scans and (after_scans & INDEXED_SCAN_TYPES):
        return PostconditionResult("R6", CONFIRMED,
                                   f"{rel} moved from Seq Scan to "
                                   f"{', '.join(sorted(after_scans & INDEXED_SCAN_TYPES))}; "
                                   "covering_idx is being used again.", evidence)
    return PostconditionResult("R6", REFUTED,
                               f"{rel} is still sequentially scanned after ANALYZE.", evidence)


@register_postcondition("R3")
def _r3_hash_batches_to_one(before, after, ctx):
    evidence = {"before_hash_batches": before.max_hash_batches,
                "after_hash_batches": after.max_hash_batches}
    if before.max_hash_batches is None:
        return PostconditionResult("R3", UNVERIFIABLE,
                                   "Baseline plan has no Hash node, so there was no spill to fix.",
                                   evidence)
    if before.max_hash_batches <= 1:
        return PostconditionResult("R3", UNVERIFIABLE,
                                   "Baseline hash join did not spill (Hash Batches = 1).", evidence)
    if after.max_hash_batches == 1:
        return PostconditionResult("R3", CONFIRMED,
                                   f"Hash Batches {before.max_hash_batches} -> 1; the hash join "
                                   "now fits in work_mem.", evidence)
    return PostconditionResult("R3", REFUTED,
                               f"Hash Batches {before.max_hash_batches} -> {after.max_hash_batches}; "
                               "the join still spills to disk.", evidence)


@register_postcondition("R4")
def _r4_sort_becomes_in_memory(before, after, ctx):
    evidence = {"before_sort_methods": before.sort_methods,
                "after_sort_methods": after.sort_methods}
    if not before.sort_methods:
        return PostconditionResult("R4", UNVERIFIABLE,
                                   "Baseline plan contains no Sort node.", evidence)
    if not before.has_external_sort():
        return PostconditionResult("R4", UNVERIFIABLE,
                                   "Baseline sort was already in memory.", evidence)
    if after.has_external_sort():
        return PostconditionResult("R4", REFUTED,
                                   "Sort still spills to disk (external merge) after the change.",
                                   evidence)
    if any(m.lower().startswith(IN_MEMORY_SORT_METHODS) for m in after.sort_methods):
        return PostconditionResult("R4", CONFIRMED,
                                   "Sort moved from external merge to an in-memory sort.", evidence)
    return PostconditionResult("R4", REFUTED,
                               "Sort node disappeared or its method is unrecognised; cannot "
                               "confirm the external merge was eliminated.", evidence)


@register_postcondition("R5")
def _r5_cache_pressure_drops(before, after, ctx):
    evidence = {
        "before_shared_read_blocks": before.shared_read_blocks,
        "after_shared_read_blocks": after.shared_read_blocks,
        "baseline_windowed_hit_ratio": ctx.baseline_hit_ratio,
        "optimized_windowed_hit_ratio": ctx.optimized_hit_ratio,
    }
    ratio_gain = None
    if ctx.baseline_hit_ratio is not None and ctx.optimized_hit_ratio is not None:
        ratio_gain = ctx.optimized_hit_ratio - ctx.baseline_hit_ratio
        evidence["windowed_hit_ratio_gain"] = ratio_gain

    reads_dropped = (
        before.shared_read_blocks > 0
        and after.shared_read_blocks < before.shared_read_blocks * 0.9
    )
    if ratio_gain is not None and ratio_gain >= HIT_RATIO_MIN_GAIN:
        return PostconditionResult("R5", CONFIRMED,
                                   f"Windowed buffer hit ratio rose by {ratio_gain * 100:.2f} "
                                   "percentage points.", evidence)
    if reads_dropped:
        return PostconditionResult("R5", CONFIRMED,
                                   f"Shared read blocks fell {before.shared_read_blocks} -> "
                                   f"{after.shared_read_blocks}.", evidence)
    if ratio_gain is None and before.shared_read_blocks == 0:
        return PostconditionResult("R5", UNVERIFIABLE,
                                   "Baseline plan read no blocks from disk and no windowed hit "
                                   "ratio was available; there was no cache pressure to relieve.",
                                   evidence)
    return PostconditionResult("R5", REFUTED,
                               "Neither the windowed hit ratio nor shared read blocks improved "
                               "materially.", evidence)


@register_postcondition("R7")
def _r7_index_only_scan(before, after, ctx):
    rel = ctx.target_relation
    before_scans, after_scans = before.scans_on(rel), after.scans_on(rel)
    heap_after = after.heap_fetches_by_relation.get(rel)
    rows_after = after.actual_rows_by_relation.get(rel) or 0
    zero_threshold = max(1.0, rows_after * HEAP_FETCH_ZERO_FRACTION)

    evidence = {
        "relation": rel,
        "before_scan_types": sorted(before_scans),
        "after_scan_types": sorted(after_scans),
        "before_heap_fetches": before.heap_fetches_by_relation.get(rel),
        "after_heap_fetches": heap_after,
        "heap_fetch_zero_threshold": zero_threshold,
    }

    if "Index Scan" not in before_scans:
        return PostconditionResult(
            "R7", UNVERIFIABLE,
            f"Baseline plan does not use a plain Index Scan on {rel} "
            f"(saw {sorted(before_scans) or 'nothing'}), so there were no heap fetches to remove.",
            evidence)

    if "Index Only Scan" not in after_scans:
        return PostconditionResult(
            "R7", REFUTED,
            f"{rel} is still scanned via {', '.join(sorted(after_scans)) or 'no index'} rather "
            "than an Index Only Scan; the INCLUDE index is not covering the query.", evidence)

    if heap_after is None:
        return PostconditionResult(
            "R7", CONFIRMED,
            f"{rel} moved to an Index Only Scan (Heap Fetches not reported).", evidence)

    if heap_after <= zero_threshold:
        return PostconditionResult(
            "R7", CONFIRMED,
            f"{rel} moved to an Index Only Scan with Heap Fetches = {heap_after} "
            f"(<= {zero_threshold:.0f}).", evidence)

    # Index-only scans skip the heap only for all-visible pages; a stale VM gains nothing.
    return PostconditionResult(
        "R7", REFUTED,
        f"{rel} is an Index Only Scan but still performed {heap_after} heap fetches "
        f"(> {zero_threshold:.0f}). The visibility map is stale -- vacuum {rel} "
        "(see R11) and re-measure before judging this index.", evidence)


@register_postcondition("R10")
def _r10_nested_loop_fanout_drops(before, after, ctx):
    b, a = before.max_inner_rows_per_outer, after.max_inner_rows_per_outer
    evidence = {"before_inner_rows_per_outer": b, "after_inner_rows_per_outer": a}
    if b is None:
        return PostconditionResult("R10", UNVERIFIABLE,
                                   "Baseline plan contains no Nested Loop.", evidence)
    if a is None:
        return PostconditionResult("R10", CONFIRMED,
                                   "Nested Loop eliminated from the plan entirely.", evidence)
    if a < b * 0.9:
        return PostconditionResult("R10", CONFIRMED,
                                   f"Inner rows per outer row fell {b:.0f} -> {a:.0f}.", evidence)
    return PostconditionResult("R10", REFUTED,
                               f"Inner rows per outer row did not fall materially "
                               f"({b:.0f} -> {a:.0f}).", evidence)


@register_postcondition("R11")
def _r11_vacuum_caught_up(before, after, ctx):
    rel = ctx.target_relation
    b = (ctx.table_stats_before or {}).get(rel) or {}
    a = (ctx.table_stats_after or {}).get(rel) or {}
    evidence = {
        "relation": rel,
        "before_n_dead_tup": b.get("n_dead_tup"),
        "after_n_dead_tup": a.get("n_dead_tup"),
        "before_last_autovacuum": b.get("last_autovacuum"),
        "after_last_autovacuum": a.get("last_autovacuum"),
        "before_last_analyze": b.get("last_analyze"),
        "after_last_analyze": a.get("last_analyze"),
    }
    if not b or not a or b.get("n_dead_tup") is None or a.get("n_dead_tup") is None:
        return PostconditionResult("R11", UNVERIFIABLE,
                                   f"pg_stat_user_tables data for {rel} unavailable on one side.",
                                   evidence)

    dead_dropped = a["n_dead_tup"] < b["n_dead_tup"]
    vacuum_advanced = _timestamp_advanced(b.get("last_autovacuum"), a.get("last_autovacuum")) or \
        _timestamp_advanced(b.get("last_vacuum"), a.get("last_vacuum"))
    analyze_advanced = _timestamp_advanced(b.get("last_analyze"), a.get("last_analyze")) or \
        _timestamp_advanced(b.get("last_autoanalyze"), a.get("last_autoanalyze"))
    evidence.update({"dead_tuples_dropped": dead_dropped,
                     "vacuum_advanced": vacuum_advanced,
                     "analyze_advanced": analyze_advanced})

    if dead_dropped and (vacuum_advanced or analyze_advanced):
        return PostconditionResult(
            "R11", CONFIRMED,
            f"Dead tuples on {rel} fell {b['n_dead_tup']} -> {a['n_dead_tup']} and "
            "vacuum/analyze advanced.", evidence)
    if dead_dropped:
        return PostconditionResult(
            "R11", REFUTED,
            f"Dead tuples fell {b['n_dead_tup']} -> {a['n_dead_tup']} but neither "
            "last_autovacuum nor last_analyze advanced, so the drop cannot be "
            "attributed to this suggestion.", evidence)
    return PostconditionResult(
        "R11", REFUTED,
        f"Dead tuples on {rel} did not fall ({b['n_dead_tup']} -> {a['n_dead_tup']}).", evidence)


def _timestamp_advanced(before, after) -> bool:
    if after is None:
        return False
    if before is None:
        return True
    return str(after) > str(before)
