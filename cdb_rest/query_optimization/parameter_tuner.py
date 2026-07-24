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
restart, so its suggestion is advisory-only, safe_sql=None); work_mem and
random_page_cost are reloadable via ALTER SYSTEM SET + a reload; and
autovacuum_vacuum_scale_factor for PayloadIOV is a per-table storage
parameter, applied via ALTER TABLE ... SET (...).
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

from django.db import connections

from . import storage
from .explain_plan_rule_engine import Suggestion, validate_safe_sql

BUFFER_HIT_RATIO_THRESHOLD = 0.95
BUFFER_HIT_RATIO_CONSECUTIVE_CYCLES = 3
WORK_MEM_SPILL_RULES = ("R3", "R4")
WORK_MEM_SPILL_THRESHOLD = 5
WORK_MEM_LOOKBACK_DAYS = 7
AUTOVACUUM_SCALE_FACTOR_TARGET = 0.05
RANDOM_PAGE_COST_TARGET = 1.1


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
            "increasing work_mem."
        ),
        safe_sql=validate_safe_sql("ALTER SYSTEM SET work_mem = '64MB';"),
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
            "the SSD latency profile of Ceph-backed OKD persistent volumes "
            "(default of 4.0 assumes spinning disks)."
        ),
        safe_sql=validate_safe_sql(f"ALTER SYSTEM SET random_page_cost = {RANDOM_PAGE_COST_TARGET};"),
        confidence=0.7,
        source="tuner",
        parameter_name="random_page_cost",
    )


class ParameterTuner:
    """DB-backed wrapper: gathers ClusterMetrics from db_alias, computes
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
        buffer_hit_ratio = self._buffer_hit_ratio()
        storage.record_tuner_observation(self.db_alias, self.db_alias, buffer_hit_ratio)
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
            buffer_hit_ratio=buffer_hit_ratio,
            consecutive_low_buffer_cycles=consecutive_low,
            work_mem_spill_fires=work_mem_spill_fires,
            autovacuum_lag_fired=autovacuum_lag_fired,
        )

    def _buffer_hit_ratio(self) -> Optional[float]:
        sql = """
            SELECT blks_hit, blks_read
            FROM pg_stat_database
            WHERE datname = current_database()
        """
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
        if not row:
            return None
        hit, read = float(row[0] or 0), float(row[1] or 0)
        total = hit + read
        if total <= 0:
            return None
        return hit / total


def _parameter_suggestion_hash(suggestion: Suggestion) -> str:
    payload = (
        f"tuner|{suggestion.parameter_name}|{suggestion.category}|"
        f"{suggestion.message}|{suggestion.safe_sql or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
