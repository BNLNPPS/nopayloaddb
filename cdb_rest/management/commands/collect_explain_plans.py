import hashlib
import json
import logging
import time

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
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--statement-timeout-ms", type=int, default=5000)
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
                self._finish_run(db_alias, run_id, seen, explained, stored, failed, None)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"run={run_id} seen={seen} explained={explained} stored={stored} failed={failed}"
                    )
                )
            except Exception as exc:
                logger.exception("collector run failed")
                if run_id is not None:
                    self._finish_run(db_alias, run_id, 0, 0, 0, 1, str(exc))
                self.stderr.write(self.style.ERROR(f"collector error: {exc}"))

            if once:
                break
            time.sleep(interval)

    def _run_once(self, db_alias, options, run_id):
        self._ensure_schema(db_alias)

        candidates = self._fetch_candidates(
            db_alias=db_alias,
            min_mean_ms=options["min_mean_ms"],
            min_calls=options["min_calls"],
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

                did_store = self._store_plan(
                    db_alias=db_alias,
                    queryid=queryid,
                    query_text=query_text,
                    mean_exec_time=mean_exec_time,
                    calls=calls,
                    rows_count=rows_count,
                    shared_blks_read=shared_blks_read,
                    plan_json=plan_json,
                    plan_hash=plan_hash,
                )
                if did_store:
                    stored += 1
            except Exception as exc:
                failed += 1
                self._store_error(db_alias, run_id, queryid, query_text, str(exc))

        return len(candidates), explained, stored, failed

    def _ensure_schema(self, db_alias):
        ddl = [
            "CREATE SCHEMA IF NOT EXISTS ai_optimizer",
            """
            CREATE TABLE IF NOT EXISTS ai_optimizer.collection_runs (
                id BIGSERIAL PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL,
                finished_at TIMESTAMPTZ,
                seen INTEGER DEFAULT 0,
                explained INTEGER DEFAULT 0,
                stored INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                error TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ai_optimizer.explain_plans (
                id BIGSERIAL PRIMARY KEY,
                queryid TEXT,
                query_text TEXT NOT NULL,
                captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                collected_minute TIMESTAMPTZ NOT NULL DEFAULT date_trunc('minute', now()),
                mean_exec_time DOUBLE PRECISION,
                calls BIGINT,
                rows_count BIGINT,
                shared_blks_read BIGINT,
                plan_json JSONB NOT NULL,
                plan_hash TEXT NOT NULL
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS explain_plans_dedupe_idx
            ON ai_optimizer.explain_plans (queryid, plan_hash, collected_minute)
            """,
            """
            CREATE TABLE IF NOT EXISTS ai_optimizer.collection_errors (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT,
                queryid TEXT,
                query_text TEXT,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
        ]

        with connections[db_alias].cursor() as cursor:
            for sql in ddl:
                cursor.execute(sql)

    def _fetch_candidates(self, db_alias, min_mean_ms, min_calls, limit):
        sql = """
            SELECT queryid, query, mean_exec_time, calls, rows, shared_blks_read
            FROM pg_stat_statements
            WHERE query ILIKE 'select %'
              AND mean_exec_time >= %s
              AND calls >= %s
            ORDER BY mean_exec_time DESC
            LIMIT %s
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [min_mean_ms, min_calls, limit])
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

    def _store_plan(
        self,
        db_alias,
        queryid,
        query_text,
        mean_exec_time,
        calls,
        rows_count,
        shared_blks_read,
        plan_json,
        plan_hash,
    ):
        sql = """
            INSERT INTO ai_optimizer.explain_plans (
                queryid,
                query_text,
                mean_exec_time,
                calls,
                rows_count,
                shared_blks_read,
                plan_json,
                plan_hash,
                collected_minute
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, date_trunc('minute', now()))
            ON CONFLICT (queryid, plan_hash, collected_minute) DO NOTHING
        """
        payload = json.dumps(plan_json)

        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                sql,
                [
                    queryid,
                    query_text,
                    mean_exec_time,
                    calls,
                    rows_count,
                    shared_blks_read,
                    payload,
                    plan_hash,
                ],
            )
            return cursor.rowcount > 0

    def _create_run(self, db_alias, started_at):
        self._ensure_schema(db_alias)
        sql = """
            INSERT INTO ai_optimizer.collection_runs (started_at)
            VALUES (%s)
            RETURNING id
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [started_at])
            return cursor.fetchone()[0]

    def _finish_run(self, db_alias, run_id, seen, explained, stored, failed, error):
        sql = """
            UPDATE ai_optimizer.collection_runs
            SET finished_at = %s,
                seen = %s,
                explained = %s,
                stored = %s,
                failed = %s,
                error = %s
            WHERE id = %s
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [timezone.now(), seen, explained, stored, failed, error, run_id])

    def _store_error(self, db_alias, run_id, queryid, query_text, error):
        sql = """
            INSERT INTO ai_optimizer.collection_errors (run_id, queryid, query_text, error)
            VALUES (%s, %s, %s, %s)
        """
        with connections[db_alias].cursor() as cursor:
            cursor.execute(sql, [run_id, queryid, query_text[:5000], error[:5000]])
