import hashlib
import json
import logging
import time

from cdb_rest.query_optimization import storage
from cdb_rest.query_optimization.explain_plan_rule_engine import (
    RuleContext,
    RuleEngine,
    parse_explain_plan,
    suggestion_hash,
    validate_safe_sql,
)
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Collect slow queries from pg_stat_statements and persist EXPLAIN plans"

    def add_arguments(self, parser):
        parser.add_argument("--db-alias", default="read_db_1")
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

        while True:
            started_at = timezone.now()
            run_id = None
            try:
                run_id = self._create_run(db_alias, started_at)
                seen, explained, stored, failed = self._run_once(db_alias, options, run_id)
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

    def _run_once(self, db_alias, options, run_id):
        storage.ensure_schema(db_alias)

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
                plan_json = self._explain_query(
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
                    source=options["source"],
                    plan_json=plan_json,
                    plan_hash=plan_hash,
                )
                if did_store:
                    stored += 1

                self._analyze_and_store_suggestions(
                    db_alias=db_alias,
                    plan_id=plan_id,
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
                )
            except Exception as exc:
                failed += 1
                self._store_error(db_alias, run_id, queryid, query_text, str(exc))

        return len(candidates), explained, stored, failed

    def _fetch_candidates(self, db_alias, min_mean_ms, min_calls, min_shared_blks_read, limit):
        sql = """
            SELECT
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
            FROM pg_stat_statements
            WHERE query ILIKE 'select %%'
              AND query !~ '\\$[0-9]+'
              AND (mean_exec_time >= %s OR shared_blks_read >= %s)
              AND calls >= %s
            ORDER BY mean_exec_time DESC
            LIMIT %s
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [min_mean_ms, min_shared_blks_read, min_calls, limit])
            return cursor.fetchall()

    def _explain_query(self, db_alias, query_text, statement_timeout_ms):
        normalized = query_text.lstrip().lower()
        if not normalized.startswith("select "):
            raise ValueError("Only SELECT statements are allowed for EXPLAIN collection")
        if ";" in query_text:
            raise ValueError("Semicolons are not allowed in EXPLAIN collection query text")

        with connections[db_alias].cursor() as cursor:
            started_tx = False
            try:
                cursor.execute("BEGIN READ ONLY")
                started_tx = True
                cursor.execute("SET LOCAL statement_timeout = %s", [statement_timeout_ms])
                cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query_text}")
                result = cursor.fetchone()
            finally:
                if started_tx:
                    try:
                        cursor.execute("ROLLBACK")
                    except Exception:
                        logger.exception("failed to rollback explain transaction")

        if result is None:
            raise RuntimeError("No EXPLAIN result returned")

        return result[0]

    def _analyze_and_store_suggestions(
        self,
        db_alias,
        plan_id,
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
    ):
        root = parse_explain_plan(plan_json)
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
        )
        suggestions = RuleEngine().run(root, context)
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
            )

    def _has_locked_global_tag(self, db_alias):
        sql = """
            SELECT EXISTS (
                SELECT 1
                FROM "GlobalTagStatus"
                WHERE LOWER(name) = 'locked'
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
