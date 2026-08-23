"""Execution of approved safe_sql, shared by the suggestions API and the
apply_approved_suggestions command.

CREATE/REINDEX CONCURRENTLY are long-running, so approving only queues them for
the off-peak job. ALTER SYSTEM SET is not executed at all -- it writes
postgresql.auto.conf, which outranks the ConfigMap the Helm charts own. Temp
tables (R13) are advisory: they only help inside the querying session.
"""

import logging

from django.db import connections

from .explain_plan_rule_engine import is_executable_safe_sql

logger = logging.getLogger(__name__)

DDL_QUEUE_PREFIXES = ("CREATE INDEX CONCURRENTLY", "REINDEX CONCURRENTLY")
ADVISORY_ONLY_PREFIXES = ("CREATE TEMP TABLE",)

PRIMARY_ALIAS = "default"


def is_queued_ddl(safe_sql: str) -> bool:
    return safe_sql.strip().upper().startswith(DDL_QUEUE_PREFIXES)


def is_advisory_only(safe_sql: str) -> bool:
    return safe_sql.strip().upper().startswith(ADVISORY_ONLY_PREFIXES)


def apply_safe_sql(safe_sql: str) -> bool:
    """Execute a non-DDL safe_sql immediately. Never raises; False means not applied."""
    if is_queued_ddl(safe_sql):
        raise ValueError("DDL statements must go through apply_approved_suggestions, not apply_safe_sql")

    # Last line of defence: ai_optimizer is also written by the tuner and LLM layer.
    if not is_executable_safe_sql(safe_sql):
        logger.error("refusing to execute non-allow-listed safe_sql: %s", safe_sql)
        return False

    try:
        with connections[PRIMARY_ALIAS].cursor() as cursor:
            cursor.execute(safe_sql)
        return True
    except Exception:
        logger.exception("failed to apply safe_sql: %s", safe_sql)
        return False


def apply_queued_ddl(safe_sql: str) -> bool:
    """Execute queued DDL against the primary, from an off-peak job -- these can
    take minutes on a large table."""
    if not is_queued_ddl(safe_sql):
        raise ValueError("apply_queued_ddl only accepts CREATE/REINDEX CONCURRENTLY statements")

    if not is_executable_safe_sql(safe_sql):
        logger.error("refusing to execute non-allow-listed DDL: %s", safe_sql)
        return False

    try:
        with connections[PRIMARY_ALIAS].cursor() as cursor:
            cursor.execute(safe_sql)
        return True
    except Exception:
        logger.exception("failed to apply queued DDL: %s", safe_sql)
        return False
