"""Shared persistence layer for the ai_optimizer schema.

Every writer of ai_optimizer data (the EXPLAIN collector, the LLM escalation
layer, and the dynamic parameter tuner) goes through this module so the
schema is defined in exactly one place and stays consistent across all three
producers.
"""

import json

from django.db import connections


def ensure_schema(db_alias):
    """Idempotently create/upgrade the ai_optimizer schema. Safe to call on every run."""
    ddl = [
        "CREATE SCHEMA IF NOT EXISTS ai_optimizer",
        """
        CREATE TABLE IF NOT EXISTS ai_optimizer.collection_runs (
            id BIGSERIAL PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            duration_ms BIGINT,
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
            db_name TEXT,
            captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            collected_minute TIMESTAMPTZ NOT NULL DEFAULT date_trunc('minute', now()),
            mean_exec_time DOUBLE PRECISION,
            calls BIGINT,
            rows BIGINT,
            shared_blks_read BIGINT,
            source TEXT,
            plan_json JSONB NOT NULL,
            plan_hash TEXT NOT NULL
        )
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS explain_plans_dedupe_idx
        ON ai_optimizer.explain_plans (queryid, plan_hash, collected_minute)
        """,
        """
        CREATE INDEX IF NOT EXISTS explain_plans_plan_json_gin_idx
        ON ai_optimizer.explain_plans USING GIN (plan_json)
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
        """
        CREATE TABLE IF NOT EXISTS ai_optimizer.suggestions (
            id BIGSERIAL PRIMARY KEY,
            plan_id BIGINT REFERENCES ai_optimizer.explain_plans(id) ON DELETE CASCADE,
            queryid TEXT,
            rule_id TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            message TEXT NOT NULL,
            safe_sql TEXT,
            confidence DOUBLE PRECISION NOT NULL,
            source TEXT NOT NULL DEFAULT 'rule_engine',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            suggestion_hash TEXT NOT NULL
        )
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS suggestions_dedupe_idx
        ON ai_optimizer.suggestions (plan_id, suggestion_hash)
        """,
        """
        CREATE INDEX IF NOT EXISTS suggestions_status_idx
        ON ai_optimizer.suggestions (status, created_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_optimizer.tuner_observations (
            id BIGSERIAL PRIMARY KEY,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            source_db_alias TEXT NOT NULL,
            buffer_hit_ratio DOUBLE PRECISION
        )
        """,
        # --- idempotent upgrades for columns added after the tables first existed ---
        "ALTER TABLE ai_optimizer.collection_runs ADD COLUMN IF NOT EXISTS duration_ms BIGINT",
        "ALTER TABLE ai_optimizer.explain_plans ADD COLUMN IF NOT EXISTS db_name TEXT",
        "ALTER TABLE ai_optimizer.explain_plans ADD COLUMN IF NOT EXISTS rows BIGINT",
        "ALTER TABLE ai_optimizer.explain_plans ADD COLUMN IF NOT EXISTS source TEXT",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS suggestion_hash TEXT",
        # plan_id is nullable because parameter-tuner suggestions are not tied to a
        # captured EXPLAIN plan -- they're derived from cluster-wide metrics.
        "ALTER TABLE ai_optimizer.suggestions ALTER COLUMN plan_id DROP NOT NULL",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS parameter_name TEXT",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ",
    ]

    with connections[db_alias].cursor() as cursor:
        for sql in ddl:
            cursor.execute(sql)


def store_plan(
    db_alias,
    queryid,
    query_text,
    mean_exec_time,
    calls,
    rows_count,
    shared_blks_read,
    db_name,
    source,
    plan_json,
    plan_hash,
):
    sql = """
        WITH ins AS (
            INSERT INTO ai_optimizer.explain_plans (
                queryid,
                query_text,
                db_name,
                mean_exec_time,
                calls,
                rows,
                shared_blks_read,
                source,
                plan_json,
                plan_hash,
                collected_minute
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, date_trunc('minute', now()))
            ON CONFLICT (queryid, plan_hash, collected_minute) DO NOTHING
            RETURNING id, true AS inserted
        )
        SELECT id, inserted FROM ins
        UNION ALL
        SELECT id, false AS inserted
        FROM ai_optimizer.explain_plans
        WHERE queryid = %s
          AND plan_hash = %s
          AND collected_minute = date_trunc('minute', now())
        LIMIT 1
    """
    payload = json.dumps(plan_json)

    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            sql,
            [
                queryid,
                query_text,
                db_name,
                mean_exec_time,
                calls,
                rows_count,
                shared_blks_read,
                source,
                payload,
                plan_hash,
                queryid,
                plan_hash,
            ],
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert explain plan row")
        return row[0], bool(row[1])


def store_suggestion(
    db_alias,
    plan_id,
    queryid,
    rule_id,
    category,
    priority,
    message,
    safe_sql,
    confidence,
    source,
    suggestion_digest,
    parameter_name=None,
):
    sql = """
        INSERT INTO ai_optimizer.suggestions (
            plan_id,
            queryid,
            rule_id,
            category,
            priority,
            message,
            safe_sql,
            confidence,
            source,
            suggestion_hash,
            parameter_name
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (plan_id, suggestion_hash) DO NOTHING
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            sql,
            [
                plan_id,
                queryid,
                rule_id,
                category,
                priority,
                message,
                safe_sql,
                confidence,
                source,
                suggestion_digest,
                parameter_name,
            ],
        )


def has_open_parameter_suggestion(db_alias, parameter_name):
    """True if a pending/approved tuner suggestion already exists for this parameter.

    Used by the tuner to avoid flooding the queue with a fresh suggestion every
    cycle for a condition that hasn't been resolved yet.
    """
    sql = """
        SELECT EXISTS (
            SELECT 1 FROM ai_optimizer.suggestions
            WHERE parameter_name = %s
              AND source = 'tuner'
              AND status IN ('pending', 'approved')
        )
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [parameter_name])
        row = cursor.fetchone()
        return bool(row[0]) if row else False


def record_tuner_observation(db_alias, source_db_alias, buffer_hit_ratio):
    sql = """
        INSERT INTO ai_optimizer.tuner_observations (source_db_alias, buffer_hit_ratio)
        VALUES (%s, %s)
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [source_db_alias, buffer_hit_ratio])


def consecutive_low_buffer_cycles(db_alias, source_db_alias, threshold=0.95, window=3):
    """Count how many of the most recent `window` observations fell below `threshold`,
    stopping at the first one that didn't (so the streak must be unbroken and recent)."""
    sql = """
        SELECT buffer_hit_ratio FROM ai_optimizer.tuner_observations
        WHERE source_db_alias = %s
        ORDER BY observed_at DESC
        LIMIT %s
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [source_db_alias, window])
        rows = cursor.fetchall()

    streak = 0
    for (ratio,) in rows:
        if ratio is not None and ratio < threshold:
            streak += 1
        else:
            break
    return streak


def count_recent_rule_fires(db_alias, rule_ids, since_days=7):
    sql = """
        SELECT COUNT(*) FROM ai_optimizer.suggestions
        WHERE rule_id = ANY(%s)
          AND created_at > now() - (%s || ' days')::interval
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [list(rule_ids), since_days])
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def create_run(db_alias, started_at):
    ensure_schema(db_alias)
    sql = """
        INSERT INTO ai_optimizer.collection_runs (started_at)
        VALUES (%s)
        RETURNING id
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [started_at])
        return cursor.fetchone()[0]


def finish_run(db_alias, run_id, finished_at, duration_ms, seen, explained, stored, failed, error):
    sql = """
        UPDATE ai_optimizer.collection_runs
        SET finished_at = %s,
            duration_ms = %s,
            seen = %s,
            explained = %s,
            stored = %s,
            failed = %s,
            error = %s
        WHERE id = %s
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            sql, [finished_at, duration_ms, seen, explained, stored, failed, error, run_id]
        )


def store_error(db_alias, run_id, queryid, query_text, error):
    sql = """
        INSERT INTO ai_optimizer.collection_errors (run_id, queryid, query_text, error)
        VALUES (%s, %s, %s, %s)
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [run_id, queryid, query_text[:5000], error[:5000]])
