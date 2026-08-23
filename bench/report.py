"""Benchmark reports: a condition report (one run) and a comparison report
(baseline vs optimized, carrying the verdict)."""

import json
import os
from datetime import datetime, timezone

from . import plan_evidence, verdict as verdict_mod
from .latency_stats import compare_metric


def save_report(report: dict, output_dir: str, label: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(output_dir, f"{timestamp}_{label}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def load_report(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


class NotAConditionReport(ValueError):
    """Raised when --compare-to is handed something that is not a baseline."""


def validate_condition_report(report: dict, path: str) -> dict:
    """Reject a file that cannot serve as a baseline -- typically a comparison report,
    which would otherwise yield an INCONCLUSIVE verdict that looks like a result."""
    if "verdict" in report and "latency" in report and "workload" in report \
            and isinstance(report.get("workload"), dict) \
            and "optimized" in report["workload"]:
        raise NotAConditionReport(
            f"{path} is a comparison report, not a baseline condition report. "
            "Pass the file written by the baseline run itself (the one without "
            "'_vs_baseline' in its name)."
        )
    if not isinstance(report.get("latency"), dict) or not report["latency"]:
        raise NotAConditionReport(f"{path} has no per-endpoint latency data; it cannot be a baseline.")
    if not (report.get("workload") or {}).get("repetitions"):
        raise NotAConditionReport(
            f"{path} does not record how many repetitions it ran, so it cannot be used "
            "as a baseline -- there would be no noise floor to compare against."
        )
    return report


def build_condition_report(*, label, config, workload_summary, started_at, finished_at,
                           endpoint_coverage, latency_by_endpoint, db_metrics,
                           plan_features, plan_raw, table_stats, db_state,
                           warmup_issued) -> dict:
    """One condition's results, in the shape compare_conditions() expects."""
    return {
        "schema_version": 2,
        "label": label,
        "started_at": started_at,
        "finished_at": finished_at,
        "workload": {
            **config.describe(),
            **workload_summary,
            "warmup_requests_issued": warmup_issued,
        },
        "coverage": endpoint_coverage,
        "latency": latency_by_endpoint,
        "db": db_metrics,
        "plan": {name: (feat.to_dict() if feat else None)
                 for name, feat in (plan_features or {}).items()},
        # Kept so a comparison can re-derive features without re-running the query.
        "plan_raw": plan_raw or {},
        "table_stats": table_stats,
        "db_state": db_state,
    }


def _spread(agg_metric: dict) -> dict:
    """Spread shown next to every headline number, so the noise is visible."""
    return {
        "mean": agg_metric.get("mean"),
        "median": agg_metric.get("median"),
        "stdev": agg_metric.get("stdev"),
        "min": agg_metric.get("min"),
        "max": agg_metric.get("max"),
        "n": agg_metric.get("n"),
        "values": agg_metric.get("values"),
    }


def compare_conditions(baseline: dict, optimized: dict, *, rule_id=None,
                       primary_endpoint="sql", target_relation="PayloadIOV",
                       db_state_comparison=None, reversibility=None) -> dict:
    """Full baseline-vs-optimized comparison with a verdict."""
    b_lat = (baseline.get("latency") or {})
    o_lat = (optimized.get("latency") or {})

    endpoints = {}
    for name in sorted(set(b_lat) | set(o_lat)):
        b_agg, o_agg = b_lat.get(name) or {}, o_lat.get(name) or {}
        endpoints[name] = {
            "p50_ms": _metric_block(b_agg, o_agg, "p50_ms"),
            "p95_ms": _metric_block(b_agg, o_agg, "p95_ms"),
            "p99_ms": _metric_block(b_agg, o_agg, "p99_ms"),
            "errors": {"baseline": b_agg.get("errors"), "optimized": o_agg.get("errors")},
            "repetitions": {"baseline": b_agg.get("repetitions"),
                            "optimized": o_agg.get("repetitions")},
        }

    db_block = _db_comparison(baseline.get("db") or {}, optimized.get("db") or {})

    before_features, after_features = _features(baseline, optimized, primary_endpoint)
    ctx = plan_evidence.MechanismContext(
        target_relation=target_relation,
        table_stats_before=baseline.get("table_stats") or {},
        table_stats_after=optimized.get("table_stats") or {},
        baseline_hit_ratio=(baseline.get("db") or {}).get("windowed_hit_ratio"),
        optimized_hit_ratio=(optimized.get("db") or {}).get("windowed_hit_ratio"),
    )
    postcondition = (plan_evidence.check_postcondition(rule_id, before_features,
                                                       after_features, ctx)
                     if rule_id else None)

    primary = endpoints.get(primary_endpoint) or {}
    latency_comparison = (primary.get("p95_ms") or {}).get("comparison") or {"status": "unknown"}

    o_workload = optimized.get("workload") or {}
    repetitions = min(
        (baseline.get("workload") or {}).get("repetitions") or 0,
        o_workload.get("repetitions") or 0,
    )

    v = verdict_mod.evaluate(
        latency_comparison,
        postcondition=postcondition,
        repetitions=repetitions,
        workload_artificially_cacheable=bool(o_workload.get("artificially_cacheable")),
        cacheability_reason=o_workload.get("cacheability_reason"),
        db_metrics=db_block,
        experiment_mode=o_workload.get("experiment_mode", "cumulative"),
        applied_suggestions=o_workload.get("applied_suggestions") or (),
        baseline_state_matches=(db_state_comparison or {}).get("comparable"),
        reversibility=reversibility,
    )

    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rule_id": rule_id,
        "primary_endpoint": primary_endpoint,
        "workload": {"baseline": baseline.get("workload"), "optimized": o_workload},
        "coverage": {"baseline": baseline.get("coverage"),
                     "optimized": optimized.get("coverage")},
        "latency": endpoints,
        "db_metrics": db_block,
        "plan_evidence": {
            "before": (baseline.get("plan") or {}).get(primary_endpoint),
            "after": (optimized.get("plan") or {}).get(primary_endpoint),
            "detected_changes": _plan_changes(before_features, after_features, target_relation),
            "postcondition": postcondition.to_dict() if postcondition else None,
        },
        "db_state_comparison": db_state_comparison,
        "reversibility": reversibility,
        "verdict": v.to_dict(),
    }


def _metric_block(b_agg, o_agg, metric) -> dict:
    b_metrics = (b_agg.get("metrics") or {}).get(metric) or {}
    o_metrics = (o_agg.get("metrics") or {}).get(metric) or {}
    return {
        "baseline": _spread(b_metrics),
        "optimized": _spread(o_metrics),
        "comparison": compare_metric(b_agg, o_agg, metric) if b_agg and o_agg else None,
    }


def _db_comparison(b_db: dict, o_db: dict) -> dict:
    out = {
        "windowed_hit_ratio": {
            "baseline": b_db.get("windowed_hit_ratio"),
            "optimized": o_db.get("windowed_hit_ratio"),
            "delta": _sub(o_db.get("windowed_hit_ratio"), b_db.get("windowed_hit_ratio")),
        },
        "delta_blks_read": {
            "baseline": b_db.get("delta_blks_read"),
            "optimized": o_db.get("delta_blks_read"),
            "delta": _sub(o_db.get("delta_blks_read"), b_db.get("delta_blks_read")),
        },
        "delta_blks_hit": {
            "baseline": b_db.get("delta_blks_hit"),
            "optimized": o_db.get("delta_blks_hit"),
            "delta": _sub(o_db.get("delta_blks_hit"), b_db.get("delta_blks_hit")),
        },
        "stats_reset_detected": bool(b_db.get("stats_reset_detected")
                                     or o_db.get("stats_reset_detected")),
        "fingerprints": {},
    }

    b_fp, o_fp = b_db.get("fingerprints") or {}, o_db.get("fingerprints") or {}
    for name in sorted(set(b_fp) | set(o_fp)):
        b, o = b_fp.get(name) or {}, o_fp.get(name) or {}
        b_mean, o_mean = b.get("windowed_mean_exec_time_ms"), o.get("windowed_mean_exec_time_ms")
        out["fingerprints"][name] = {
            "baseline_delta_calls": b.get("delta_calls"),
            "optimized_delta_calls": o.get("delta_calls"),
            "baseline_delta_exec_time_ms": b.get("delta_exec_time_ms"),
            "optimized_delta_exec_time_ms": o.get("delta_exec_time_ms"),
            "baseline_windowed_mean_exec_time_ms": b_mean,
            "optimized_windowed_mean_exec_time_ms": o_mean,
            "windowed_mean_delta_ms": _sub(o_mean, b_mean),
            "windowed_mean_pct_change": ((o_mean - b_mean) / b_mean * 100)
                                        if (b_mean and o_mean) else None,
            "usable": bool(b.get("usable")) and bool(o.get("usable")),
        }
    return out


def _sub(a, b):
    return (a - b) if (a is not None and b is not None) else None


def _features(baseline, optimized, endpoint):
    raw_b = (baseline.get("plan_raw") or {}).get(endpoint)
    raw_o = (optimized.get("plan_raw") or {}).get(endpoint)
    try:
        fb = plan_evidence.extract_features(raw_b) if raw_b else None
        fo = plan_evidence.extract_features(raw_o) if raw_o else None
    except ValueError:
        return None, None
    return fb, fo


def _plan_changes(before, after, target_relation) -> dict:
    """Summary of what actually changed in the plan."""
    if before is None or after is None:
        return {"available": False,
                "reason": "no EXPLAIN plan captured for one or both conditions"}

    changes = []
    for rel in sorted(set(before.scan_types_by_relation) | set(after.scan_types_by_relation)):
        b_scans, a_scans = before.scans_on(rel), after.scans_on(rel)
        if b_scans != a_scans:
            changes.append(f"{rel}: {', '.join(sorted(b_scans)) or 'absent'} -> "
                           f"{', '.join(sorted(a_scans)) or 'absent'}")

    for rel in sorted(set(before.heap_fetches_by_relation) | set(after.heap_fetches_by_relation)):
        b_h = before.heap_fetches_by_relation.get(rel)
        a_h = after.heap_fetches_by_relation.get(rel)
        if b_h != a_h:
            changes.append(f"{rel} Heap Fetches: {b_h} -> {a_h}")

    if before.max_hash_batches != after.max_hash_batches:
        changes.append(f"Hash Batches: {before.max_hash_batches} -> {after.max_hash_batches}")
    if before.sort_methods != after.sort_methods:
        changes.append(f"Sort Method: {before.sort_methods or 'none'} -> "
                       f"{after.sort_methods or 'none'}")

    return {
        "available": True,
        "changes": changes,
        "target_relation": target_relation,
        "shared_read_blocks": {"before": before.shared_read_blocks,
                               "after": after.shared_read_blocks},
        "worst_estimate_deviation_log10": {
            "before": before.worst_estimate_deviation(),
            "after": after.worst_estimate_deviation()},
    }


def render_text(comparison: dict) -> str:
    """Console rendering, mirroring the JSON so the two cannot disagree."""
    lines = []
    w = (comparison.get("workload") or {}).get("optimized") or {}
    lines.append("WORKLOAD")
    lines.append(f"  profile={w.get('profile')} seed={w.get('seed')} "
                 f"pool={w.get('distinct_points_wide')} "
                 f"gts={w.get('gt_names')} iov_major={w.get('major_iov_range')}")
    lines.append(f"  requests/endpoint={w.get('requests_per_endpoint')} "
                 f"repetitions={w.get('repetitions')} warmup={w.get('warmup_requests')}")

    cov = (comparison.get("coverage") or {}).get("optimized") or {}
    lines.append(f"  endpoints exercised={cov.get('exercised')} skipped={cov.get('skipped') or {}}")

    lines.append("")
    lines.append("LATENCY (negative pct = faster)")
    for name, block in (comparison.get("latency") or {}).items():
        for metric in ("p50_ms", "p95_ms"):
            m = block.get(metric) or {}
            b, o = m.get("baseline") or {}, m.get("optimized") or {}
            comp = m.get("comparison") or {}
            pct = comp.get("pct_change")
            pct_s = f"{pct:+.1f}%" if pct is not None else "n/a"
            lines.append(
                f"  {name:12s} {metric:7s} "
                f"baseline {_fmt(b.get('mean'))} (sd {_fmt(b.get('stdev'))}, "
                f"{_fmt(b.get('min'))}..{_fmt(b.get('max'))})  ->  "
                f"optimized {_fmt(o.get('mean'))} (sd {_fmt(o.get('stdev'))}, "
                f"{_fmt(o.get('min'))}..{_fmt(o.get('max'))})  "
                f"{pct_s} [{comp.get('status', 'n/a')}]"
            )

    db = comparison.get("db_metrics") or {}
    lines.append("")
    lines.append("DATABASE (windowed -- deltas over the benchmark window only)")
    hr = db.get("windowed_hit_ratio") or {}
    lines.append(f"  buffer hit ratio  {_fmt_ratio(hr.get('baseline'))} -> "
                 f"{_fmt_ratio(hr.get('optimized'))} (delta {_fmt_ratio(hr.get('delta'))})")
    br = db.get("delta_blks_read") or {}
    lines.append(f"  blocks read       {br.get('baseline')} -> {br.get('optimized')}")
    for name, fp in (db.get("fingerprints") or {}).items():
        lines.append(
            f"  {name:12s} windowed mean "
            f"{_fmt(fp.get('baseline_windowed_mean_exec_time_ms'))} -> "
            f"{_fmt(fp.get('optimized_windowed_mean_exec_time_ms'))} "
            f"over {fp.get('optimized_delta_calls')} calls"
            + ("" if fp.get("usable") else "   [NOT USABLE -- see status]")
        )

    pe = comparison.get("plan_evidence") or {}
    lines.append("")
    lines.append("PLAN EVIDENCE")
    detected = pe.get("detected_changes") or {}
    if not detected.get("available"):
        lines.append(f"  {detected.get('reason')}")
    elif detected.get("changes"):
        for change in detected["changes"]:
            lines.append(f"  {change}")
    else:
        lines.append("  no plan-shape change detected")
    pc = pe.get("postcondition")
    if pc:
        lines.append(f"  postcondition {pc['rule_id']}: {pc['status'].upper()} -- {pc['detail']}")

    v = comparison.get("verdict") or {}
    lines.append("")
    lines.append(f"VERDICT: {v.get('status')}  "
                 f"(latency={v.get('latency_status')}, mechanism={v.get('mechanism_status')})")
    lines.append(f"  {v.get('rationale')}")
    for caveat in v.get("caveats") or []:
        lines.append(f"  ! {caveat}")

    return "\n".join(lines)


def _fmt(value):
    return f"{value:.1f}ms" if isinstance(value, (int, float)) else "n/a"


def _fmt_ratio(value):
    return f"{value * 100:.2f}%" if isinstance(value, (int, float)) else "n/a"
