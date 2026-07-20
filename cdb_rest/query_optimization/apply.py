"""Execution of approved safe_sql, shared by the suggestions API (immediate
apply) and the apply_approved_suggestions management command (queued DDL).

Routing follows what each statement is actually allowed to do in PostgreSQL,
not a single "run it somewhere" rule:

- CREATE INDEX CONCURRENTLY / REINDEX CONCURRENTLY are long-running DDL. They
  are never executed synchronously from an HTTP request -- approving one only
  marks it 'approved'; a separate off-peak job (apply_approved_suggestions,
  intended to be invoked by a CronJob at the infra layer) applies it and
  marks it 'applied'. This mirrors the proposal's CronJob-queuing design.
- ALTER SYSTEM SET only rewrites the local postgresql.auto.conf file, so
  (unlike ANALYZE/VACUUM/catalog DDL) it is *not* blocked on a read-only
  streaming replica. It's applied to every configured database alias so the
  whole cluster ends up with consistent config, each followed by
  pg_reload_conf() for GUCs that don't require a restart.
- Everything else the allow-list permits (ANALYZE, VACUUM, SET, ALTER TABLE
  ... SET (autovacuum_vacuum_scale_factor=...), ALTER INDEX RENAME) writes to
  the catalog or data and can only run on the primary, since streaming
  replicas reject any such statement in read-only mode.
- CREATE TEMP TABLE (Rule R13) is never auto-applied at all. A temp table is
  only useful inside the same session as the query it's meant to rewrite, so
  the proposal treats it as an advisory suggestion for the operator to
  incorporate manually, not something this service can apply on its behalf.
"""

import logging

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)

DDL_QUEUE_PREFIXES = ("CREATE INDEX CONCURRENTLY", "REINDEX CONCURRENTLY")
CLUSTER_WIDE_PREFIXES = ("ALTER SYSTEM SET",)
ADVISORY_ONLY_PREFIXES = ("CREATE TEMP TABLE",)

PRIMARY_ALIAS = "default"


def is_queued_ddl(safe_sql: str) -> bool:
    return safe_sql.strip().upper().startswith(DDL_QUEUE_PREFIXES)


def is_advisory_only(safe_sql: str) -> bool:
    return safe_sql.strip().upper().startswith(ADVISORY_ONLY_PREFIXES)


def _is_cluster_wide(safe_sql: str) -> bool:
    return safe_sql.strip().upper().startswith(CLUSTER_WIDE_PREFIXES)


def _configured_aliases() -> list[str]:
    return [
        alias
        for alias in (PRIMARY_ALIAS, "read_db_1", "read_db_2")
        if alias in settings.DATABASES
    ]


def apply_safe_sql(safe_sql: str) -> bool:
    """Execute an already-validated, non-DDL safe_sql statement immediately.
    Returns True on success. Never raises -- callers decide what to do with
    a False result (leave the suggestion 'approved' rather than 'applied')."""
    if is_queued_ddl(safe_sql):
        raise ValueError("DDL statements must go through apply_approved_suggestions, not apply_safe_sql")

    try:
        if _is_cluster_wide(safe_sql):
            for alias in _configured_aliases():
                with connections[alias].cursor() as cursor:
                    cursor.execute(safe_sql)
                    cursor.execute("SELECT pg_reload_conf()")
        else:
            with connections[PRIMARY_ALIAS].cursor() as cursor:
                cursor.execute(safe_sql)
        return True
    except Exception:
        logger.exception("failed to apply safe_sql: %s", safe_sql)
        return False


def apply_queued_ddl(safe_sql: str) -> bool:
    """Execute a queued DDL statement (CREATE INDEX CONCURRENTLY /
    REINDEX CONCURRENTLY) against the primary. Intended to be called from an
    off-peak batch job, not a request/response cycle -- these can take
    minutes on a large table."""
    if not is_queued_ddl(safe_sql):
        raise ValueError("apply_queued_ddl only accepts CREATE/REINDEX CONCURRENTLY statements")

    try:
        with connections[PRIMARY_ALIAS].cursor() as cursor:
            cursor.execute(safe_sql)
        return True
    except Exception:
        logger.exception("failed to apply queued DDL: %s", safe_sql)
        return False
