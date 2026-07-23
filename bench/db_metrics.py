"""Database-side metrics captured alongside the HTTP load test.

Fingerprint aggregates are read from ai_optimizer.explain_plans (populated
by collect_explain_plans running as a separate, continuous process) rather
than polling pg_stat_statements directly here, so the benchmark's DB-side
numbers reflect exactly what the AI optimizer itself observed during the
run -- for that to be non-empty, collect_explain_plans must be running
throughout the benchmark window.

Only the three SELECT-based endpoints (sql / orm_orderby / orm_max) can
have fingerprint stats here: the collector only ever runs EXPLAIN on
SELECT statements (see collect_explain_plans._explain_query), so writes
like bulk_piov and cloneGlobalTag are structurally invisible to it. Their
performance is only available from the HTTP-level timings the harness
itself records when --include-writes is passed.
"""

from typing import Optional

from django.db import connections

from cdb_rest.query_optimization.pg_stats import buffer_hit_ratio

FINGERPRINT_PATTERNS = {
    "sql": "query_text ILIKE '%JOIN LATERAL%'",
    "orm_orderby": "query_text ILIKE '%DISTINCT ON%'",
    "orm_max": "query_text ILIKE '%MAX(%' AND query_text NOT ILIKE '%DISTINCT ON%' "
    "AND query_text NOT ILIKE '%JOIN LATERAL%'",
}


def capture_buffer_hit_ratio(db_alias: str) -> Optional[float]:
    return buffer_hit_ratio(db_alias)


def fingerprint_stats(db_alias: str, since, until) -> dict:
    """Aggregate mean_exec_time/calls for plans collected in [since, until]
    for each of the three SELECT-based fingerprints."""
    stats = {}
    with connections[db_alias].cursor() as cursor:
        for name, where_clause in FINGERPRINT_PATTERNS.items():
            cursor.execute(
                f"""
                SELECT AVG(mean_exec_time), COUNT(*)
                FROM ai_optimizer.explain_plans
                WHERE {where_clause}
                  AND captured_at BETWEEN %s AND %s
                """,
                [since, until],
            )
            row = cursor.fetchone()
            avg_ms, count = (row[0], row[1]) if row else (None, 0)
            stats[name] = {
                "avg_mean_exec_time_ms": float(avg_ms) if avg_ms is not None else None,
                "plans_collected": int(count) if count else 0,
            }

    stats["bulk_piov"] = {
        "avg_mean_exec_time_ms": None,
        "plans_collected": 0,
        "note": "writes are never EXPLAINed by the collector; see HTTP-level timings instead",
    }
    stats["clone_global_tag"] = {
        "avg_mean_exec_time_ms": None,
        "plans_collected": 0,
        "note": "writes are never EXPLAINed by the collector; see HTTP-level timings instead",
    }
    return stats
