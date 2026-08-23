"""Database-side capture for the benchmark harness. Arithmetic lives in
pg_snapshot.py; nothing here reports a cumulative counter as a result."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from django.db import connections

from cdb_rest import queries

from .pg_snapshot import BufferCounters, DBSnapshot, StatementCounters

logger = logging.getLogger(__name__)

# Matched against normalized pg_stat_statements.query, so keyed on structure.
FINGERPRINT_PATTERNS = {
    "sql": "%JOIN LATERAL%PayloadIOV%",
    "orm_orderby": "%DISTINCT ON%PayloadIOV%",
    "orm_max": "%MAX(%PayloadIOV%",
}

TRACKED_TABLES = ("PayloadIOV", "PayloadList", "GlobalTag")

TRACKED_GUCS = (
    "shared_buffers", "work_mem", "effective_cache_size", "random_page_cost",
    "checkpoint_completion_target", "autovacuum_vacuum_scale_factor",
    "max_connections", "log_min_duration_statement",
)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# --- Snapshots ---


def capture_snapshot(db_alias: str) -> DBSnapshot:
    """Point-in-time snapshot of the counters the benchmark differences."""
    snapshot = DBSnapshot(captured_at=_now_iso())
    snapshot.buffers = _capture_buffers(db_alias)
    available, reset_at, statements = _capture_statements(db_alias)
    snapshot.pg_stat_statements_available = available
    snapshot.statements_stats_reset = reset_at
    snapshot.statements = statements
    return snapshot


def _capture_buffers(db_alias: str) -> BufferCounters:
    sql = """
        SELECT blks_hit, blks_read, stats_reset
        FROM pg_stat_database
        WHERE datname = current_database()
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    if not row:
        return BufferCounters()
    return BufferCounters(
        blks_hit=int(row[0] or 0),
        blks_read=int(row[1] or 0),
        stats_reset=str(row[2]) if row[2] else None,
    )


def _capture_statements(db_alias: str):
    """(available, stats_reset, counters) for the benchmarked fingerprints only."""
    patterns = list(FINGERPRINT_PATTERNS.values())
    sql = """
        SELECT queryid, query, calls, total_exec_time,
               shared_blks_hit, shared_blks_read, rows
        FROM pg_stat_statements
        WHERE query ILIKE ANY(%s)
    """
    statements = {}
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [patterns])
            for row in cursor.fetchall():
                queryid = str(row[0])
                statements[queryid] = StatementCounters(
                    queryid=queryid,
                    query_text=row[1] or "",
                    calls=int(row[2] or 0),
                    total_exec_time=float(row[3] or 0.0),
                    shared_blks_hit=int(row[4] or 0),
                    shared_blks_read=int(row[5] or 0),
                    rows=int(row[6] or 0),
                    fingerprint=_classify(row[1] or ""),
                )
    except Exception as exc:
        logger.warning("pg_stat_statements unavailable on %s: %s", db_alias, exc)
        return False, None, {}

    return True, _statements_stats_reset(db_alias), statements


def _statements_stats_reset(db_alias: str):
    """pg_stat_statements_info exists from PG14; absent is not an error."""
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("SELECT stats_reset FROM pg_stat_statements_info")
            row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None
    except Exception:
        return None


def _classify(query_text: str):
    upper = query_text.upper()
    if "JOIN LATERAL" in upper:
        return "sql"
    if "DISTINCT ON" in upper:
        return "orm_orderby"
    if "MAX(" in upper:
        return "orm_max"
    return None


# --- Table statistics (R11 postcondition) ---


def capture_table_stats(db_alias: str, tables=TRACKED_TABLES) -> dict:
    sql = """
        SELECT relname, n_live_tup, n_dead_tup,
               last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
        FROM pg_stat_user_tables
        WHERE relname = ANY(%s)
    """
    out = {}
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [list(tables)])
            for row in cursor.fetchall():
                out[row[0]] = {
                    "n_live_tup": int(row[1] or 0),
                    "n_dead_tup": int(row[2] or 0),
                    "last_vacuum": str(row[3]) if row[3] else None,
                    "last_autovacuum": str(row[4]) if row[4] else None,
                    "last_analyze": str(row[5]) if row[5] else None,
                    "last_autoanalyze": str(row[6]) if row[6] else None,
                }
    except Exception as exc:
        logger.warning("pg_stat_user_tables read failed on %s: %s", db_alias, exc)
    return out


# --- Plan capture (mechanism evidence) ---


def capture_reference_plan(db_alias: str, gt_name: str, major_iov: int, minor_iov: int,
                           statement_timeout_ms: int = 15000):
    """EXPLAIN (ANALYZE, BUFFERS) the production LATERAL JOIN, read-only and always
    rolled back. Bound parameters, so placeholders never block it. None on failure."""
    query_text = queries.get_payload_iovs.strip().rstrip(";")
    params = {"my_gt": gt_name, "my_major_iov": major_iov, "my_minor_iov": minor_iov}

    connection = connections[db_alias]
    try:
        with connection.cursor() as cursor:
            cursor.execute("BEGIN READ ONLY")
            try:
                cursor.execute("SET LOCAL statement_timeout = %s", [statement_timeout_ms])
                cursor.execute(
                    f"EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE, FORMAT JSON) {query_text}",
                    params,
                )
                row = cursor.fetchone()
            finally:
                cursor.execute("ROLLBACK")
        if not row:
            return None
        plan = row[0]
        return json.loads(plan) if isinstance(plan, str) else plan
    except Exception as exc:
        logger.warning("reference plan capture failed on %s: %s", db_alias, exc)
        return None


# --- Database state fingerprint (experiment reproducibility) ---


def capture_db_state(db_alias: str) -> dict:
    """Everything that must match for two runs to be comparable; a difference is
    flagged on the verdict rather than silently ignored."""
    state = {"captured_at": _now_iso(), "guc": {}, "indexes": {}, "tables": {}}

    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                "SELECT name, setting, unit FROM pg_settings WHERE name = ANY(%s)",
                [list(TRACKED_GUCS)],
            )
            state["guc"] = {r[0]: f"{r[1]}{r[2] or ''}" for r in cursor.fetchall()}

            cursor.execute(
                """
                SELECT tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = current_schema() AND tablename = ANY(%s)
                ORDER BY tablename, indexname
                """,
                [list(TRACKED_TABLES)],
            )
            for tablename, indexname, indexdef in cursor.fetchall():
                state["indexes"].setdefault(tablename, {})[indexname] = indexdef
    except Exception as exc:
        logger.warning("db state capture failed on %s: %s", db_alias, exc)

    # Row counts matter: a leaked clone or a bulk insert changes what the numbers mean.
    stats = capture_table_stats(db_alias)
    state["tables"] = {t: {"n_live_tup": s.get("n_live_tup")} for t, s in stats.items()}
    state["hash"] = state_hash(state)
    return state


def state_hash(state: dict) -> str:
    payload = json.dumps(
        {k: state[k] for k in ("guc", "indexes", "tables") if k in state},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compare_db_state(baseline_state: dict, current_state: dict) -> dict:
    """Field-level diff of two state fingerprints."""
    if not baseline_state or not current_state:
        return {"comparable": None, "reason": "one side has no recorded database state",
                "differences": {}}

    differences = {}
    for section in ("guc", "indexes", "tables"):
        b, c = baseline_state.get(section) or {}, current_state.get(section) or {}
        for key in set(b) | set(c):
            if b.get(key) != c.get(key):
                differences.setdefault(section, {})[key] = {
                    "baseline": b.get(key), "current": c.get(key)}

    return {
        "comparable": not differences,
        "baseline_hash": baseline_state.get("hash"),
        "current_hash": current_state.get("hash"),
        "differences": differences,
        "reason": None if not differences else
                  "database state changed since the baseline was captured",
    }


# --- Workload discovery ---


def discover_workload_bounds(db_alias: str, max_gts: int = 8) -> dict:
    """Derive the parameter pool from data actually present, so a cold sweep hits
    real rows. {} when nothing is found; the caller keeps its configured range."""
    result = {}
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT gt.name, COUNT(pi.id) AS iov_count
                FROM "GlobalTag" gt
                JOIN "PayloadList" pl ON pl.global_tag_id = gt.id
                JOIN "PayloadIOV" pi ON pi.payload_list_id = pl.id
                GROUP BY gt.name
                HAVING COUNT(pi.id) > 0
                ORDER BY iov_count DESC
                LIMIT %s
                """,
                [max_gts],
            )
            gt_rows = cursor.fetchall()
            if not gt_rows:
                return {}
            result["gt_names"] = tuple(r[0] for r in gt_rows)

            cursor.execute(
                """
                SELECT MIN(major_iov), MAX(major_iov), MIN(minor_iov), MAX(minor_iov)
                FROM "PayloadIOV"
                """
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                result["major_iov_min"] = int(row[0])
                result["major_iov_max"] = int(row[1])
                result["minor_iov_min"] = int(row[2])
                result["minor_iov_max"] = int(row[3])
    except Exception as exc:
        logger.warning("workload discovery failed on %s: %s", db_alias, exc)
        return {}

    return result
