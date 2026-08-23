"""Shared persistence layer for the ai_optimizer schema, so the collector, the
LLM layer and the tuner all agree on one definition."""

import hashlib
import json

from django.db import connections


def ensure_schema(db_alias):
    """Create or upgrade the ai_optimizer schema. Safe to call on every run."""
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
        """
        CREATE TABLE IF NOT EXISTS ai_optimizer.benchmark_runs (
            id BIGSERIAL PRIMARY KEY,
            label TEXT NOT NULL,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            workload_profile TEXT,
            workload_seed BIGINT,
            repetitions INTEGER,
            warmup_requests INTEGER,
            requests_per_endpoint INTEGER,
            concurrency INTEGER,
            endpoints_exercised TEXT[],
            endpoints_skipped TEXT[],
            experiment_mode TEXT,
            applied_suggestions BIGINT[],
            db_state_hash TEXT,
            report JSONB NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS benchmark_runs_label_idx
        ON ai_optimizer.benchmark_runs (label, recorded_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_optimizer.suggestion_evaluations (
            id BIGSERIAL PRIMARY KEY,
            suggestion_id BIGINT REFERENCES ai_optimizer.suggestions(id) ON DELETE CASCADE,
            baseline_run_id BIGINT REFERENCES ai_optimizer.benchmark_runs(id) ON DELETE SET NULL,
            optimized_run_id BIGINT REFERENCES ai_optimizer.benchmark_runs(id) ON DELETE SET NULL,
            evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            rule_id TEXT,
            primary_endpoint TEXT,
            verdict TEXT NOT NULL,
            latency_status TEXT,
            mechanism_status TEXT,
            baseline_p50_ms DOUBLE PRECISION,
            baseline_p95_ms DOUBLE PRECISION,
            baseline_spread_ms DOUBLE PRECISION,
            optimized_p50_ms DOUBLE PRECISION,
            optimized_p95_ms DOUBLE PRECISION,
            optimized_spread_ms DOUBLE PRECISION,
            pct_change_p95 DOUBLE PRECISION,
            noise_band_ms DOUBLE PRECISION,
            exceeds_noise BOOLEAN,
            repetitions INTEGER,
            warmup_requests INTEGER,
            workload_profile TEXT,
            workload JSONB,
            db_metric_deltas JSONB,
            plan_changes JSONB,
            postcondition JSONB,
            experiment_mode TEXT,
            application_order BIGINT[],
            caveats TEXT[],
            rationale TEXT,
            evidence JSONB
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS suggestion_evaluations_suggestion_idx
        ON ai_optimizer.suggestion_evaluations (suggestion_id, evaluated_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS ai_optimizer.statement_counters (
            queryid TEXT PRIMARY KEY,
            calls BIGINT NOT NULL,
            total_exec_time DOUBLE PRECISION NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        # --- idempotent upgrades for columns added after the tables first existed ---
        "ALTER TABLE ai_optimizer.collection_runs ADD COLUMN IF NOT EXISTS duration_ms BIGINT",
        "ALTER TABLE ai_optimizer.explain_plans ADD COLUMN IF NOT EXISTS db_name TEXT",
        "ALTER TABLE ai_optimizer.explain_plans ADD COLUMN IF NOT EXISTS rows BIGINT",
        "ALTER TABLE ai_optimizer.explain_plans ADD COLUMN IF NOT EXISTS source TEXT",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS suggestion_hash TEXT",
        # Nullable: tuner suggestions come from cluster metrics, not a captured plan.
        "ALTER TABLE ai_optimizer.suggestions ALTER COLUMN plan_id DROP NOT NULL",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS parameter_name TEXT",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ",
        # Kept separate from `confidence`, the a priori guess measurement never overwrites.
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS benchmarked_at TIMESTAMPTZ",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMPTZ",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS evaluation_status TEXT",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS empirical_pct_change DOUBLE PRECISION",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS latest_evaluation_id BIGINT",
        # Content-addressed: keying on plan_id re-inserted the suggestion every cycle.
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS fingerprint TEXT",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS occurrences INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ",
        "ALTER TABLE ai_optimizer.suggestions ADD COLUMN IF NOT EXISTS prerequisite TEXT",
        # One open suggestion per remedy; closed ones excluded so a condition can recur.
        """
        CREATE UNIQUE INDEX IF NOT EXISTS suggestions_open_fingerprint_idx
        ON ai_optimizer.suggestions (fingerprint)
        WHERE fingerprint IS NOT NULL AND status IN ('pending', 'approved')
        """,
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


def suggestion_fingerprint(rule_id, category, safe_sql, message):
    """Content address for a remedy, independent of which plan surfaced it, so the
    same finding across many plans is one row with an occurrence count."""
    payload = f"{rule_id}|{category}|{(safe_sql or '').strip()}|{'' if safe_sql else (message or '').strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    prerequisite=None,
):
    """Insert a suggestion, or bump the open one that says the same thing."""
    fingerprint = suggestion_fingerprint(rule_id, category, safe_sql, message)

    sql = """
        INSERT INTO ai_optimizer.suggestions (
            plan_id, queryid, rule_id, category, priority, message, safe_sql,
            confidence, source, suggestion_hash, parameter_name, prerequisite,
            fingerprint, occurrences, last_seen_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, now())
        ON CONFLICT (fingerprint) WHERE fingerprint IS NOT NULL
                                    AND status IN ('pending', 'approved')
        DO UPDATE SET
            occurrences = ai_optimizer.suggestions.occurrences + 1,
            last_seen_at = now(),
            updated_at = now()
        RETURNING (xmax = 0) AS inserted
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [
            plan_id, queryid, rule_id, category, priority, message, safe_sql,
            confidence, source, suggestion_digest, parameter_name, prerequisite,
            fingerprint,
        ])
        row = cursor.fetchone()
        return bool(row[0]) if row else False


def has_open_parameter_suggestion(db_alias, parameter_name):
    """True if an open tuner suggestion already exists for this parameter."""
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
    """Length of the current unbroken streak of observations below `threshold`."""
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


# --- Benchmark results and the suggestion feedback loop ---

# pending -> approved -> applied -> benchmarked -> verified|regressed|inconclusive; rejected ends it.
SUGGESTION_STATUSES = (
    "pending", "approved", "rejected", "applied",
    "benchmarked", "verified", "regressed", "inconclusive",
)

TERMINAL_EVALUATION_STATUSES = ("verified", "regressed", "inconclusive")

VERDICT_TO_STATUS = {
    "VERIFIED": "verified",
    "REGRESSED": "regressed",
    "INCONCLUSIVE": "inconclusive",
}


def record_benchmark_run(db_alias, report):
    """Persist a condition report and return its run id."""
    workload = report.get("workload") or {}
    coverage = report.get("coverage") or {}
    sql = """
        INSERT INTO ai_optimizer.benchmark_runs (
            label, started_at, finished_at, workload_profile, workload_seed,
            repetitions, warmup_requests, requests_per_endpoint, concurrency,
            endpoints_exercised, endpoints_skipped, experiment_mode,
            applied_suggestions, db_state_hash, report
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING id
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, [
            report.get("label"),
            report.get("started_at"),
            report.get("finished_at"),
            workload.get("profile"),
            workload.get("seed"),
            workload.get("repetitions"),
            workload.get("warmup_requests"),
            workload.get("requests_per_endpoint"),
            workload.get("concurrency"),
            list(coverage.get("exercised") or []),
            sorted((coverage.get("skipped") or {}).keys()),
            workload.get("experiment_mode"),
            [int(s) for s in (workload.get("applied_suggestions") or [])],
            (report.get("db_state") or {}).get("hash"),
            json.dumps(report, default=str),
        ])
        return cursor.fetchone()[0]


def record_suggestion_evaluation(db_alias, suggestion_id, comparison,
                                 baseline_run_id=None, optimized_run_id=None):
    """Write measured evidence back against a suggestion. `confidence` is never
    modified, so prediction and measurement sit side by side."""
    verdict = comparison.get("verdict") or {}
    primary = comparison.get("primary_endpoint")
    latency = ((comparison.get("latency") or {}).get(primary) or {})
    p50, p95 = latency.get("p50_ms") or {}, latency.get("p95_ms") or {}
    p95_cmp = p95.get("comparison") or {}
    workload = (comparison.get("workload") or {}).get("optimized") or {}
    plan_evidence_block = comparison.get("plan_evidence") or {}

    status = VERDICT_TO_STATUS.get(verdict.get("status"), "inconclusive")

    sql = """
        INSERT INTO ai_optimizer.suggestion_evaluations (
            suggestion_id, baseline_run_id, optimized_run_id, rule_id,
            primary_endpoint, verdict, latency_status, mechanism_status,
            baseline_p50_ms, baseline_p95_ms, baseline_spread_ms,
            optimized_p50_ms, optimized_p95_ms, optimized_spread_ms,
            pct_change_p95, noise_band_ms, exceeds_noise,
            repetitions, warmup_requests, workload_profile, workload,
            db_metric_deltas, plan_changes, postcondition,
            experiment_mode, application_order, caveats, rationale, evidence
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s::jsonb,
            %s::jsonb, %s::jsonb, %s::jsonb,
            %s, %s, %s, %s, %s::jsonb
        )
        RETURNING id
    """
    params = [
        suggestion_id, baseline_run_id, optimized_run_id, comparison.get("rule_id"),
        primary, verdict.get("status"), verdict.get("latency_status"),
        verdict.get("mechanism_status"),
        (p50.get("baseline") or {}).get("mean"),
        (p95.get("baseline") or {}).get("mean"),
        (p95.get("baseline") or {}).get("stdev"),
        (p50.get("optimized") or {}).get("mean"),
        (p95.get("optimized") or {}).get("mean"),
        (p95.get("optimized") or {}).get("stdev"),
        p95_cmp.get("pct_change"), p95_cmp.get("noise_band"),
        (p95_cmp.get("test") or {}).get("significant"),
        workload.get("repetitions"), workload.get("warmup_requests"),
        workload.get("profile"), json.dumps(workload, default=str),
        json.dumps(comparison.get("db_metrics") or {}, default=str),
        json.dumps(plan_evidence_block.get("detected_changes") or {}, default=str),
        json.dumps(plan_evidence_block.get("postcondition") or {}, default=str),
        workload.get("experiment_mode"),
        [int(s) for s in (workload.get("applied_suggestions") or [])],
        list(verdict.get("caveats") or []),
        verdict.get("rationale"),
        json.dumps({"db_state_comparison": comparison.get("db_state_comparison"),
                    "coverage": comparison.get("coverage")}, default=str),
    ]

    with connections[db_alias].cursor() as cursor:
        cursor.execute(sql, params)
        evaluation_id = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE ai_optimizer.suggestions
            SET status = %s,
                evaluation_status = %s,
                empirical_pct_change = %s,
                benchmarked_at = COALESCE(benchmarked_at, now()),
                evaluated_at = now(),
                latest_evaluation_id = %s,
                updated_at = now()
            WHERE id = %s
            """,
            [status, status, p95_cmp.get("pct_change"), evaluation_id, suggestion_id],
        )

    return evaluation_id, status


def mark_benchmarked(db_alias, suggestion_id):
    """Move an applied suggestion to 'benchmarked' before its verdict is known."""
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            """
            UPDATE ai_optimizer.suggestions
            SET status = 'benchmarked', benchmarked_at = now(), updated_at = now()
            WHERE id = %s AND status = 'applied'
            """,
            [suggestion_id],
        )
        return cursor.rowcount


def get_suggestion(db_alias, suggestion_id):
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            """
            SELECT id, rule_id, category, status, safe_sql, confidence,
                   evaluation_status, empirical_pct_change
            FROM ai_optimizer.suggestions WHERE id = %s
            """,
            [suggestion_id],
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "rule_id": row[1], "category": row[2], "status": row[3],
            "safe_sql": row[4], "confidence": row[5],
            "evaluation_status": row[6], "empirical_pct_change": row[7],
        }


def latest_benchmark_run(db_alias, label):
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            """
            SELECT id, report FROM ai_optimizer.benchmark_runs
            WHERE label = %s ORDER BY recorded_at DESC LIMIT 1
            """,
            [label],
        )
        row = cursor.fetchone()
        return (row[0], row[1]) if row else (None, None)


def statement_window(db_alias, queryid, calls, total_exec_time):
    """Calls and mean exec time since the previous cycle, since the raw counters are
    cumulative. Both None on first sighting or after a reset -- never fabricated."""
    with connections[db_alias].cursor() as cursor:
        cursor.execute(
            "SELECT calls, total_exec_time FROM ai_optimizer.statement_counters WHERE queryid = %s",
            [queryid],
        )
        previous = cursor.fetchone()

        cursor.execute(
            """
            INSERT INTO ai_optimizer.statement_counters (queryid, calls, total_exec_time, observed_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (queryid) DO UPDATE
            SET calls = EXCLUDED.calls,
                total_exec_time = EXCLUDED.total_exec_time,
                observed_at = now()
            """,
            [queryid, calls, total_exec_time],
        )

    if previous is None:
        return None, None

    prev_calls, prev_time = int(previous[0] or 0), float(previous[1] or 0.0)
    if calls < prev_calls or total_exec_time < prev_time:
        return None, None  # counters went backwards: reset or evicted

    delta_calls = calls - prev_calls
    if delta_calls <= 0:
        return 0, None
    return delta_calls, (total_exec_time - prev_time) / delta_calls
