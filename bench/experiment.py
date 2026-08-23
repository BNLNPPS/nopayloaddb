"""Condition orchestration: per repetition, warmup then snapshot, load, snapshot.
Aggregating the repetitions is what gives a comparison its noise floor."""

import logging
from datetime import datetime, timezone

from django.db import transaction

from cdb_rest.models import GlobalTag

from . import db_metrics, http_worker, plan_evidence
from .latency_stats import aggregate_repetitions, summarize
from .pg_snapshot import by_fingerprint, diff_buffers, diff_statements
from .workload import pool_summary

logger = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc).isoformat()


def run_condition(config, *, stdout=None) -> dict:
    """Measure one condition end to end."""
    from . import report as report_mod

    def say(msg):
        # Not both: the project's logging config also writes to the console.
        if stdout:
            stdout.write(msg)
        else:
            logger.info(msg)

    probe = http_worker.probe_endpoints(config)
    endpoints = probe["reachable"]
    if not endpoints:
        raise http_worker.EndpointUnavailable(
            f"No benchmark endpoints reachable at {config.base_url}."
        )

    coverage = {
        "requested": list(config.endpoint_names),
        "exercised": [e.name for e in endpoints],
        "skipped": probe["skipped"],
        "required": list(config.required_endpoints),
        "complete": not probe["skipped"],
    }
    if probe["skipped"]:
        say(f"  coverage WARNING: skipping {sorted(probe['skipped'])} -- "
            "this run does not cover every requested endpoint")

    db_state = db_metrics.capture_db_state(config.db_alias)
    table_stats_start = db_metrics.capture_table_stats(config.db_alias)

    started_at = _now()
    per_rep_latency = {e.name: [] for e in endpoints}
    per_rep_writes = {}
    windowed_runs = []
    warmup_total = 0

    for rep in range(1, config.repetitions + 1):
        say(f"  repetition {rep}/{config.repetitions}: warmup "
            f"({config.resolve_warmup()} req/endpoint, unrecorded)...")
        warmup_total += http_worker.warmup(config, endpoints, rep)

        snap_start = db_metrics.capture_snapshot(config.db_alias)
        say(f"  repetition {rep}/{config.repetitions}: recording "
            f"({config.requests_per_endpoint} req/endpoint, {config.concurrency} clients)...")
        raw = http_worker.run_read_repetition(config, endpoints, rep)

        if config.include_writes:
            raw.update(http_worker.run_write_benchmark(
                config, rep,
                before_clone=_delete_global_tag,
                after_clone=_delete_global_tag,
            ))

        snap_end = db_metrics.capture_snapshot(config.db_alias)
        windowed_runs.append(_window(snap_start, snap_end))

        for name, data in raw.items():
            summary = summarize(data["latencies_ms"], data["errors"])
            summary["requests_issued"] = data.get("requests_issued")
            summary["distinct_parameters"] = data.get("distinct_parameters")
            summary["status_counts"] = data.get("status_counts")
            if name in per_rep_latency:
                per_rep_latency[name].append(summary)
            else:
                per_rep_writes.setdefault(name, []).append(summary)

    finished_at = _now()
    table_stats_end = db_metrics.capture_table_stats(config.db_alias)

    latency = {name: aggregate_repetitions(reps) for name, reps in per_rep_latency.items()}
    latency.update({name: aggregate_repetitions(reps) for name, reps in per_rep_writes.items()})

    plan_raw, plan_features = _capture_plans(config)

    workload_summary = {
        **config.workload.describe(),
        **pool_summary(config.workload),
    }

    report = report_mod.build_condition_report(
        label=config.label,
        config=config,
        workload_summary=workload_summary,
        started_at=started_at,
        finished_at=finished_at,
        endpoint_coverage=coverage,
        latency_by_endpoint=latency,
        db_metrics=_merge_windows(windowed_runs),
        plan_features=plan_features,
        plan_raw=plan_raw,
        table_stats=table_stats_end,
        db_state=db_state,
        warmup_issued=warmup_total,
    )
    report["table_stats_start"] = table_stats_start
    return report


def _window(snap_start, snap_end) -> dict:
    """Windowed metrics for a single repetition."""
    buffers = diff_buffers(snap_start.buffers, snap_end.buffers)
    statements = diff_statements(snap_start, snap_end)
    return {
        **buffers,
        "fingerprints": by_fingerprint(statements),
        "statements": statements,
        "pg_stat_statements_available": snap_end.pg_stat_statements_available,
        "snapshot_start": snap_start.to_dict(),
        "snapshot_end": snap_end.to_dict(),
    }


def _merge_windows(windows: list) -> dict:
    """Sum per-repetition windows. The ratio is recomputed from the summed counters,
    not averaged, which would weight a short repetition like a long one."""
    if not windows:
        return {"windowed_hit_ratio": None, "reason": "no repetitions recorded"}

    reset = any(w.get("stats_reset_detected") for w in windows)
    hit = sum(w.get("delta_blks_hit") or 0 for w in windows)
    read = sum(w.get("delta_blks_read") or 0 for w in windows)
    total = hit + read

    fingerprints = {}
    for w in windows:
        for name, fp in (w.get("fingerprints") or {}).items():
            g = fingerprints.setdefault(name, {
                "delta_calls": 0, "delta_exec_time_ms": 0.0,
                "delta_shared_blks_read": 0, "delta_shared_blks_hit": 0, "usable": True,
            })
            for key in ("delta_calls", "delta_exec_time_ms",
                        "delta_shared_blks_read", "delta_shared_blks_hit"):
                g[key] += fp.get(key) or 0
            g["usable"] = g["usable"] and bool(fp.get("usable"))

    for g in fingerprints.values():
        calls = g["delta_calls"]
        g["windowed_mean_exec_time_ms"] = (g["delta_exec_time_ms"] / calls) if calls > 0 else None

    return {
        "delta_blks_hit": None if reset else hit,
        "delta_blks_read": None if reset else read,
        "windowed_hit_ratio": None if (reset or total <= 0) else hit / total,
        "stats_reset_detected": reset,
        "reason": "statistics were reset during the run" if reset else
                  (None if total > 0 else "no block activity recorded"),
        "fingerprints": fingerprints,
        "repetition_windows": [
            {k: v for k, v in w.items() if k not in ("statements",)} for w in windows
        ],
        "pg_stat_statements_available": all(
            w.get("pg_stat_statements_available") for w in windows),
    }


def _capture_plans(config):
    """Reference EXPLAIN plan for mechanism evidence. Only the SQL endpoint has a
    stable parameterisable query; the ORM ones report "unverifiable" rather than guess."""
    from .workload import request_sequence

    point = request_sequence(config.workload, 1, stream="plan")[0]
    plan = db_metrics.capture_reference_plan(
        config.db_alias, point.gt_name, point.major_iov, point.minor_iov
    )
    raw = {"sql": plan} if plan else {}
    features = {}
    if plan:
        try:
            features["sql"] = plan_evidence.extract_features(plan)
        except ValueError as exc:
            logger.warning("could not extract plan features: %s", exc)
    return raw, features


def _delete_global_tag(gt_name: str) -> bool:
    """Delete a clone target if present; used as both before- and after-callback so
    repeated runs do not grow the dataset. Cascades to PayloadList and PayloadIOV."""
    try:
        with transaction.atomic():
            deleted, _ = GlobalTag.objects.filter(name=gt_name).delete()
        if deleted:
            logger.info("benchmark cleanup: removed cloned GlobalTag %s", gt_name)
        return bool(deleted)
    except Exception as exc:
        logger.error("benchmark cleanup FAILED for GlobalTag %s: %s -- dataset has grown "
                     "and subsequent repetitions are not comparable", gt_name, exc)
        return False
