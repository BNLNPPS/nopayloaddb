"""Turn a pg_stat_statements entry into something PostgreSQL can actually plan.

Stored SQL is normalized to $1/$2 placeholders, and EXPLAIN ANALYZE rejects
those outright, so the collector would find every production endpoint and plan
none of them. Three tiers, most informative first: BOUND_PARAMS replays the
real query with live values, ANALYZE handles statements that already carry
literals, GENERIC_PLAN (PG16+) plans without executing.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import connections

from cdb_rest import queries

logger = logging.getLogger(__name__)

BOUND_PARAMS = "bound_params"
ANALYZE = "analyze"
GENERIC_PLAN = "generic_plan"

_MIN_GENERIC_PLAN_VERSION = 160000


@dataclass
class ExplainTarget:
    sql: str
    params: Optional[dict]
    mode: str
    note: str

    @property
    def has_actuals(self) -> bool:
        """Whether the plan carries Actual Rows / Actual Total Time."""
        return self.mode in (BOUND_PARAMS, ANALYZE)

    def explain_prefix(self) -> str:
        if self.mode == GENERIC_PLAN:
            # Never executed, so BUFFERS and timing are unavailable.
            return "EXPLAIN (GENERIC_PLAN, COSTS, VERBOSE, FORMAT JSON)"
        return "EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE, FORMAT JSON)"


class NotExplainable(ValueError):
    """The statement cannot be planned on this server."""


def _has_placeholders(query_text: str) -> bool:
    import re
    return bool(re.search(r"\$\d+", query_text or ""))


def supports_generic_plan(db_alias: str) -> bool:
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute("SHOW server_version_num")
            return int(cursor.fetchone()[0]) >= _MIN_GENERIC_PLAN_VERSION
    except Exception:
        return False


def sample_iov_parameters(db_alias: str) -> Optional[dict]:
    """A (gt, major_iov, minor_iov) triple from live data that actually returns rows."""
    sql = """
        SELECT gt.name, pi.major_iov, pi.minor_iov
        FROM "GlobalTag" gt
        JOIN "PayloadList" pl ON pl.global_tag_id = gt.id
        JOIN "PayloadIOV" pi ON pi.payload_list_id = pl.id
        ORDER BY pi.comb_iov DESC NULLS LAST
        LIMIT 1
    """
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
    except Exception as exc:
        logger.warning("could not sample IOV parameters on %s: %s", db_alias, exc)
        return None

    if not row:
        return None
    return {"my_gt": row[0], "my_major_iov": int(row[1]), "my_minor_iov": int(row[2])}


def resolve(query_text: str, db_alias: str) -> ExplainTarget:
    """Pick the best available way to plan `query_text`."""
    text = (query_text or "").strip()
    if not text:
        raise NotExplainable("empty statement")

    if ";" in text.rstrip(";"):
        raise NotExplainable("statement contains an embedded semicolon")

    # Tier 1: the production LATERAL JOIN, replayed with real values.
    if "JOIN LATERAL" in text.upper() and '"PayloadIOV"' in text:
        params = sample_iov_parameters(db_alias)
        if params:
            return ExplainTarget(
                sql=queries.get_payload_iovs.strip().rstrip(";"),
                params=params,
                mode=BOUND_PARAMS,
                note=(f"replayed with live parameters gt={params['my_gt']!r} "
                      f"major_iov={params['my_major_iov']} minor_iov={params['my_minor_iov']}"),
            )

    if not text.lower().startswith("select "):
        raise NotExplainable("only SELECT statements are planned")

    # Tier 2: already has literals.
    if not _has_placeholders(text):
        return ExplainTarget(sql=text.rstrip(";"), params=None, mode=ANALYZE,
                             note="statement carries literal values")

    # Tier 3: parameterized, plan without executing.
    if supports_generic_plan(db_alias):
        return ExplainTarget(
            sql=text.rstrip(";"), params=None, mode=GENERIC_PLAN,
            note=("normalized statement planned with GENERIC_PLAN; no actual rows or "
                  "timings, so rules keyed on actuals (R1, R2, R6, R7) stay silent"),
        )

    raise NotExplainable(
        "statement is normalized ($1 placeholders) and this server predates "
        "PostgreSQL 16, so it cannot be planned without bind values. Upgrade to "
        "PG16+ for GENERIC_PLAN, or add a bound-parameter template for it in "
        "explain_targets.resolve()."
    )
