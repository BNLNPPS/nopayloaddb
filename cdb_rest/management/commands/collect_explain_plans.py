import hashlib
import json
import logging
import time

from cdb_rest.query_optimization import explain_targets, seeds, storage
from cdb_rest.query_optimization.explain_plan_rule_engine import (
    PlanNode,
    RuleContext,
    RuleEngine,
    parse_explain_plan,
    suggestion_hash,
    validate_safe_sql,
)
from cdb_rest.query_optimization.llm_analyzer import analyze_with_llm
from cdb_rest.query_optimization.llm_backend import get_llm_backend
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

logger = logging.getLogger(__name__)


def _metrics_only_plan():
    # Neutral root for unplanned statements; only the metrics rules can fire.
    return PlanNode(
        node_type="Not Planned",
        relation=None,
        startup_cost=0.0,
        total_cost=0.0,
        plan_rows=0,
        actual_rows=0,
        actual_time_ms=0.0,
        shared_hit_blocks=0,
        shared_read_blocks=0,
    )


class Command(BaseCommand):
    help = "Collect slow queries from pg_stat_statements and persist EXPLAIN plans"

    def add_arguments(self, parser):
        parser.add_argument("--db-alias", default=settings.CDB_AI_OPTIMIZER_DB_ALIAS)
        parser.add_argument("--interval", type=int, default=60)
        parser.add_argument("--min-mean-ms", type=float, default=100.0)
        parser.add_argument("--min-calls", type=int, default=5)
        parser.add_argument("--min-shared-blks-read", type=int, default=0)
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--statement-timeout-ms", type=int, default=5000)
        parser.add_argument("--source", default="pg_stat_statements")
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        db_alias = options["db_alias"]
        interval = options["interval"]
        once = options["once"]
        llm_backend = get_llm_backend()
        if llm_backend is None:
            logger.info("CDB_LLM_BACKEND unset/unrecognized -- LLM escalation disabled")

        while True:
            started_at = timezone.now()
            run_id = None
            try:
                run_id = self._create_run(db_alias, started_at)
                seen, explained, stored, failed = self._run_once(db_alias, options, run_id, llm_backend)
                finished_at = timezone.now()
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                self._finish_run(
                    db_alias, run_id, finished_at, duration_ms, seen, explained, stored, failed, None
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"run={run_id} seen={seen} explained={explained} stored={stored} failed={failed}"
                    )
                )
            except Exception as exc:
                logger.exception("collector run failed")
                if run_id is not None:
                    finished_at = timezone.now()
                    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                    self._finish_run(
                        db_alias, run_id, finished_at, duration_ms, 0, 0, 0, 1, str(exc)
                    )
                self.stderr.write(self.style.ERROR(f"collector error: {exc}"))

            if once:
                break
            time.sleep(interval)

    def _run_once(self, db_alias, options, run_id, llm_backend=None):
        storage.ensure_schema(db_alias)
        self._index_cache = None  # rebuilt each cycle so a new index is seen

        candidates = self._fetch_candidates(
            db_alias=db_alias,
            min_mean_ms=options["min_mean_ms"],
            min_calls=options["min_calls"],
            min_shared_blks_read=options["min_shared_blks_read"],
            limit=options["limit"],
        )

        explained = 0
        stored = 0
        failed = 0

        for row in candidates:
            queryid = str(row[0]) if row[0] is not None else ""
            query_text = row[1]
            mean_exec_time = float(row[2])
            calls = int(row[3])
            rows_count = int(row[4]) if row[4] is not None else 0
            shared_blks_read = int(row[5]) if row[5] is not None else 0
            shared_blks_hit = int(row[6]) if row[6] is not None else 0
            total_exec_time = float(row[7]) if row[7] is not None else 0.0
            stddev_exec_time = float(row[8]) if row[8] is not None else 0.0
            db_name = row[9]

            try:
                # Write-path seeds are tracked on metrics alone; see _metrics_only_plan.
                if seeds.is_explainable(query_text):
                    plan_json, explain_mode = self._explain_query(
                        db_alias=db_alias,
                        query_text=query_text,
                        statement_timeout_ms=options["statement_timeout_ms"],
                    )
                    explained += 1

                    plan_hash = hashlib.sha256(
                        json.dumps(plan_json, sort_keys=True).encode("utf-8")
                    ).hexdigest()

                    plan_id, did_store = storage.store_plan(
                        db_alias=db_alias,
                        queryid=queryid,
                        query_text=query_text,
                        mean_exec_time=mean_exec_time,
                        calls=calls,
                        rows_count=rows_count,
                        shared_blks_read=shared_blks_read,
                        db_name=db_name,
                        source=f'{options["source"]}:{explain_mode}',
                        plan_json=plan_json,
                        plan_hash=plan_hash,
                    )
                    if did_store:
                        stored += 1
                else:
                    # Write-path seeds are judged on metrics alone, never planned.
                    plan_json = None
                    plan_id = None
                    explain_mode = None

                self._analyze_and_store_suggestions(
                    db_alias=db_alias,
                    plan_id=plan_id,
                    explain_mode=explain_mode,
                    queryid=queryid,
                    query_text=query_text,
                    mean_exec_time=mean_exec_time,
                    calls=calls,
                    rows_count=rows_count,
                    shared_blks_read=shared_blks_read,
                    shared_blks_hit=shared_blks_hit,
                    total_exec_time=total_exec_time,
                    stddev_exec_time=stddev_exec_time,
                    plan_json=plan_json,
                    llm_backend=llm_backend,
                )
            except Exception as exc:
                failed += 1
                self._store_error(db_alias, run_id, queryid, query_text, str(exc))

        return len(candidates), explained, stored, failed

    # Columns every candidate query returns, in the order the caller unpacks them.
    _CANDIDATE_COLUMNS = """
        queryid,
        query,
        mean_exec_time,
        calls,
        rows,
        shared_blks_read,
        shared_blks_hit,
        total_exec_time,
        stddev_exec_time,
        current_database()
    """

    def _fetch_candidates(self, db_alias, min_mean_ms, min_calls, min_shared_blks_read, limit):
        """Seeded fingerprints always, plus the top `limit` threshold-crossers.

        Two queries on purpose: under one shared LIMIT the seeds competed with
        everything else, and the production LATERAL JOIN is fast enough (~0.06ms)
        that it ranked ~160th and was evicted every cycle.
        """
        seeded_sql = f"""
            SELECT {self._CANDIDATE_COLUMNS}
            FROM pg_stat_statements
            WHERE query ILIKE ANY(%s)
            ORDER BY mean_exec_time DESC
        """
        threshold_sql = f"""
            SELECT {self._CANDIDATE_COLUMNS}
            FROM pg_stat_statements
            WHERE query ILIKE 'select %%'
              AND (mean_exec_time >= %s OR shared_blks_read >= %s)
              AND calls >= %s
              AND NOT (query ILIKE ANY(%s))
            ORDER BY mean_exec_time DESC
            LIMIT %s
        """

        with connections[db_alias].cursor() as cursor:
            cursor.execute(seeded_sql, [seeds.SEED_PATTERNS])
            seeded = cursor.fetchall()

            cursor.execute(
                threshold_sql,
                [min_mean_ms, min_shared_blks_read, min_calls, seeds.SEED_PATTERNS, limit],
            )
            threshold = cursor.fetchall()

        # Seeds first so they are never displaced, then dedupe by queryid.
        seen, candidates = set(), []
        for row in list(seeded) + list(threshold):
            key = row[0]
            if key in seen:
                continue
            seen.add(key)
            candidates.append(row)
        return candidates

    def _explain_query(self, db_alias, query_text, statement_timeout_ms):
        """Plan one statement, returning (plan_json, mode). explain_targets.resolve
        picks a strategy, since EXPLAIN ANALYZE rejects the stored $1 placeholders."""
        target = explain_targets.resolve(query_text, db_alias)

        with connections[db_alias].cursor() as cursor:
            started_tx = False
            try:
                cursor.execute("BEGIN READ ONLY")
                started_tx = True
                cursor.execute("SET LOCAL statement_timeout = %s", [statement_timeout_ms])
                statement = f"{target.explain_prefix()} {target.sql}"
                if target.params:
                    cursor.execute(statement, target.params)
                else:
                    cursor.execute(statement)
                result = cursor.fetchone()
            finally:
                if started_tx:
                    try:
                        cursor.execute("ROLLBACK")
                    except Exception:
                        logger.exception("failed to rollback explain transaction")

        if result is None:
            raise RuntimeError("No EXPLAIN result returned")

        return result[0], target.mode

    def _analyze_and_store_suggestions(
        self,
        db_alias,
        plan_id,
        explain_mode,
        queryid,
        query_text,
        mean_exec_time,
        calls,
        rows_count,
        shared_blks_read,
        shared_blks_hit,
        total_exec_time,
        stddev_exec_time,
        plan_json,
        llm_backend=None,
    ):
        root = parse_explain_plan(plan_json) if plan_json is not None else _metrics_only_plan()

        # GENERIC_PLAN never executes, so estimate-vs-reality rules must be told.
        has_actuals = explain_mode in (explain_targets.BOUND_PARAMS, explain_targets.ANALYZE)

        window_calls, window_mean = storage.statement_window(
            db_alias, queryid, calls, total_exec_time
        )

        context = RuleContext(
            queryid=queryid,
            query_text=query_text,
            mean_exec_time=mean_exec_time,
            calls=calls,
            rows_count=rows_count,
            shared_blks_read=shared_blks_read,
            shared_blks_hit=shared_blks_hit,
            total_exec_time=total_exec_time,
            stddev_exec_time=stddev_exec_time,
            has_locked_gt=self._has_locked_global_tag(db_alias),
            payloadiov_dead_tuple_ratio=self._payloadiov_dead_tuple_ratio(db_alias),
            window_calls=window_calls,
            window_mean_exec_time=window_mean,
            has_actuals=has_actuals,
            existing_indexes=self._existing_indexes(db_alias),
        )
        suggestions = RuleEngine().run(root, context)

        # Escalate only when all 13 deterministic rules found nothing.
        if not suggestions and llm_backend is not None:
            llm_suggestion = analyze_with_llm(root, context, llm_backend)
            if llm_suggestion is not None:
                suggestions = [llm_suggestion]

        for s in suggestions:
            storage.store_suggestion(
                db_alias=db_alias,
                plan_id=plan_id,
                queryid=queryid,
                rule_id=s.rule_id,
                category=s.category,
                priority=s.priority,
                message=s.message,
                safe_sql=validate_safe_sql(s.safe_sql),
                confidence=s.confidence,
                source=s.source,
                suggestion_digest=suggestion_hash(plan_id, s),
                prerequisite=s.prerequisite,
            )

    def _existing_indexes(self, db_alias):
        """indexdefs on the CDB tables, so a rule does not re-recommend an existing index."""
        if getattr(self, "_index_cache", None) is not None:
            return self._index_cache
        sql = """
            SELECT indexdef FROM pg_indexes
            WHERE tablename IN ('PayloadIOV', 'PayloadList', 'GlobalTag')
        """
        try:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(sql)
                self._index_cache = tuple(r[0] for r in cursor.fetchall())
        except Exception:
            logger.exception("failed to list existing indexes")
            self._index_cache = ()
        return self._index_cache

    def _has_locked_global_tag(self, db_alias):
        # Whether a GlobalTag is actually locked, not whether the status row exists.
        sql = """
            SELECT EXISTS (
                SELECT 1
                FROM "GlobalTag" gt
                JOIN "GlobalTagStatus" s ON s.id = gt.status_id
                WHERE LOWER(s.name) = 'locked'
            )
        """
        try:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
                return bool(row[0]) if row else False
        except Exception:
            logger.exception("failed to inspect locked GlobalTag status")
            return False

    def _payloadiov_dead_tuple_ratio(self, db_alias):
        sql = """
            SELECT
                n_dead_tup,
                n_live_tup
            FROM pg_stat_user_tables
            WHERE relname = 'PayloadIOV'
            LIMIT 1
        """
        try:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
                if not row:
                    return 0.0
                dead = float(row[0] or 0)
                live = float(row[1] or 0)
                if live <= 0:
                    return 0.0
                return dead / live
        except Exception:
            logger.exception("failed to inspect PayloadIOV dead tuple ratio")
            return 0.0

    def _create_run(self, db_alias, started_at):
        return storage.create_run(db_alias, started_at)

    def _finish_run(self, db_alias, run_id, finished_at, duration_ms, seen, explained, stored, failed, error):
        storage.finish_run(db_alias, run_id, finished_at, duration_ms, seen, explained, stored, failed, error)

    def _store_error(self, db_alias, run_id, queryid, query_text, error):
        storage.store_error(db_alias, run_id, queryid, query_text, error)
