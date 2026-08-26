"""Small shared helpers for reading live PostgreSQL statistics views.

Used by both the dynamic parameter tuner (to decide whether shared_buffers
needs escalating) and the benchmarking harness (to report buffer health
alongside HTTP-level latency numbers), so the query lives in exactly one
place.
"""

from typing import Optional

from django.db import connections


def buffer_hit_ratio(db_alias: str) -> Optional[float]:
    """Cache hit ratio for the current database on db_alias, or None if
    pg_stat_database has no data yet (e.g. right after a restart)."""
    sql = """
        SELECT blks_hit, blks_read
        FROM pg_stat_database
        WHERE datname = current_database()
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    if not row:
        return None
    hit, read = float(row[0] or 0), float(row[1] or 0)
    total = hit + read
    if total <= 0:
        return None
    return hit / total
