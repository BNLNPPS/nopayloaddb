"""Dynamic parameter tuner (proposal Section 7.5).

Reads accumulated suggestion history and live pg_stat_* trends to recommend
values for the four cluster parameters that matter most for this workload.
Decision logic is split from DB I/O: the `recommend_*` functions are pure
(given a ClusterMetrics snapshot, they return a Suggestion or None) so they
can be unit tested without a database. ParameterTuner does the I/O -- reading
metrics, persisting a buffer-hit-ratio observation for the "N consecutive
cycles" checks, and handing results to storage.store_suggestion.

Every parameter here is treated according to its actual PostgreSQL semantics
rather than uniformly "SET": shared_buffers is PGC_POSTMASTER (requires a
restart); work_mem and
Cluster-wide GUCs are advisory: they carry the psql-conf ConfigMap change to
make. ALTER SYSTEM SET is deliberately unused -- it writes postgresql.auto.conf,
which silently overrides the ConfigMap. autovacuum_vacuum_scale_factor is a
per-table catalog parameter, so ALTER TABLE is correct there and stays appliable.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

from . import storage
from .explain_plan_rule_engine import Suggestion, validate_safe_sql
from .pg_stats import buffer_hit_ratio as get_buffer_hit_ratio

BUFFER_HIT_RATIO_THRESHOLD = 0.95
BUFFER_HIT_RATIO_CONSECUTIVE_CYCLES = 3
WORK_MEM_SPILL_RULES = ("R3", "R4")
WORK_MEM_SPILL_THRESHOLD = 5
WORK_MEM_LOOKBACK_DAYS = 7
AUTOVACUUM_SCALE_FACTOR_TARGET = 0.05
# 1.1 suits local NVMe; Ceph is network-attached, so sweep 1.1/1.5/2.0 with the harness.
RANDOM_PAGE_COST_TARGET = 1.5


@dataclass
class ClusterMetrics:
    buffer_hit_ratio: Optional[float]
    consecutive_low_buffer_cycles: int
    work_mem_spill_fires: int
    autovacuum_lag_fired: bool


def recommend_shared_buffers(metrics: ClusterMetrics) -> Optional[Suggestion]:
    if metrics.consecutive_low_buffer_cycles < BUFFER_HIT_RATIO_CONSECUTIVE_CYCLES:
        return None
    ratio_pct = (metrics.buffer_hit_ratio or 0.0) * 100
    return Suggestion(
        rule_id="TUNER",
        category="SHARED_BUFFERS",
        priority="HIGH",
        message=(
            f"Buffer hit ratio has stayed below {BUFFER_HIT_RATIO_THRESHOLD:.0%} "
            f"for {metrics.consecutive_low_buffer_cycles} consecutive cycles "
            f"(currently {ratio_pct:.1f}%). Recommend increasing shared_buffers "
            "to ~25% of the pod memory limit. This requires a PostgreSQL "
            "restart (shared_buffers is a postmaster-context parameter), so no "
            "safe_sql is provided -- apply manually via the psql-conf ConfigMap."
        ),
        safe_sql=None,
        confidence=0.85,
        source="tuner",
        parameter_name="shared_buffers",
    )


def recommend_work_mem(metrics: ClusterMetrics) -> Optional[Suggestion]:
    if metrics.work_mem_spill_fires <= WORK_MEM_SPILL_THRESHOLD:
        return None
    return Suggestion(
        rule_id="TUNER",
        category="WORK_MEM",
        priority="MEDIUM",
        message=(
            f"Hash/sort spill rules (R3/R4) fired {metrics.work_mem_spill_fires} "
            f"times in the last {WORK_MEM_LOOKBACK_DAYS} days. Recommend "
            "increasing work_mem. Apply via the psql-conf ConfigMap "
            "(work_mem = 64MB) and roll the StatefulSet -- replica first, then "
            "primary. Not auto-applied: ALTER SYSTEM would write "
            "postgresql.auto.conf, which outranks the ConfigMap and leaves the "
            "chart describing configuration the server is not using."
        ),
        safe_sql=None,  # advisory -- see message; ALTER SYSTEM would shadow the ConfigMap
        confidence=0.8,
        source="tuner",
        parameter_name="work_mem",
    )


def recommend_autovacuum_scale_factor(metrics: ClusterMetrics) -> Optional[Suggestion]:
    if not metrics.autovacuum_lag_fired:
        return None
    return Suggestion(
        rule_id="TUNER",
        category="VACUUM",
        priority="HIGH",
        message=(
            "R11 (autovacuum lag on PayloadIOV) has fired recently. Recommend "
            f"reducing autovacuum_vacuum_scale_factor for PayloadIOV to "
            f"{AUTOVACUUM_SCALE_FACTOR_TARGET} so autovacuum triggers sooner "
            "after bulk inserts."
        ),
        safe_sql=validate_safe_sql(
            'ALTER TABLE "PayloadIOV" SET '
            f"(autovacuum_vacuum_scale_factor = {AUTOVACUUM_SCALE_FACTOR_TARGET});"
        ),
        confidence=0.9,
        source="tuner",
        parameter_name="autovacuum_vacuum_scale_factor",
    )


def recommend_random_page_cost() -> Suggestion:
    return Suggestion(
        rule_id="TUNER",
        category="PLANNER_COST",
        priority="LOW",
        message=(
            f"Recommend random_page_cost = {RANDOM_PAGE_COST_TARGET} to reflect "
            "the latency profile of Ceph-backed OKD persistent volumes: the "
            "default 4.0 assumes spinning disks, but Ceph is network-attached, "
            "so the 1.1 used for local NVMe is too aggressive. Verify by "
            "benchmarking 1.1/1.5/2.0 rather than adopting this on faith."
        ),
        safe_sql=None,  # advisory -- see message; ALTER SYSTEM would shadow the ConfigMap
        confidence=0.7,
        source="tuner",
        parameter_name="random_page_cost",
    )


class ParameterTuner:
    """Gathers ClusterMetrics from db_alias, computes
    recommendations, and persists any that aren't already pending/approved."""

    def __init__(self, db_alias):
        self.db_alias = db_alias

    def run(self) -> list[Suggestion]:
        storage.ensure_schema(self.db_alias)
        metrics = self._gather_metrics()

        candidates = [
            recommend_shared_buffers(metrics),
            recommend_work_mem(metrics),
            recommend_autovacuum_scale_factor(metrics),
            recommend_random_page_cost(),
        ]

        stored = []
        for suggestion in candidates:
            if suggestion is None:
                continue
            if storage.has_open_parameter_suggestion(self.db_alias, suggestion.parameter_name):
                continue
            digest = _parameter_suggestion_hash(suggestion)
            storage.store_suggestion(
                db_alias=self.db_alias,
                plan_id=None,
                queryid=None,
                rule_id=suggestion.rule_id,
                category=suggestion.category,
                priority=suggestion.priority,
                message=suggestion.message,
                safe_sql=suggestion.safe_sql,
                confidence=suggestion.confidence,
                source=suggestion.source,
                suggestion_digest=digest,
                parameter_name=suggestion.parameter_name,
            )
            stored.append(suggestion)
        return stored

    def _gather_metrics(self) -> ClusterMetrics:
        hit_ratio = get_buffer_hit_ratio(self.db_alias)
        storage.record_tuner_observation(self.db_alias, self.db_alias, hit_ratio)
        consecutive_low = storage.consecutive_low_buffer_cycles(
            self.db_alias,
            self.db_alias,
            threshold=BUFFER_HIT_RATIO_THRESHOLD,
            window=BUFFER_HIT_RATIO_CONSECUTIVE_CYCLES,
        )
        work_mem_spill_fires = storage.count_recent_rule_fires(
            self.db_alias, WORK_MEM_SPILL_RULES, since_days=WORK_MEM_LOOKBACK_DAYS
        )
        autovacuum_lag_fired = storage.count_recent_rule_fires(
            self.db_alias, ("R11",), since_days=WORK_MEM_LOOKBACK_DAYS
        ) > 0

        return ClusterMetrics(
            buffer_hit_ratio=hit_ratio,
            consecutive_low_buffer_cycles=consecutive_low,
            work_mem_spill_fires=work_mem_spill_fires,
            autovacuum_lag_fired=autovacuum_lag_fired,
        )


def _parameter_suggestion_hash(suggestion: Suggestion) -> str:
    payload = (
        f"tuner|{suggestion.parameter_name}|{suggestion.category}|"
        f"{suggestion.message}|{suggestion.safe_sql or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
