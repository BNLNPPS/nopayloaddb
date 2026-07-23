"""Save/load benchmark result reports and diff two of them.

This is what actually answers "is the suggested query more optimized than
before": run the harness once as a baseline, apply exactly one AI
suggestion, run it again with --compare-to pointed at the baseline file,
and read the delta this module computes -- per the proposal's Phase 6 flow
(apply one change at a time, rerun the full benchmark, record the delta,
investigate/rollback if it didn't help).
"""

import json
import os
from datetime import datetime, timezone


def save_report(report: dict, output_dir: str, label: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{timestamp}_{label}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def load_report(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _delta(before: float, after: float) -> dict:
    if before is None or after is None:
        return {"before": before, "after": after, "delta": None, "pct_change": None}
    delta = after - before
    pct_change = (delta / before * 100) if before else None
    return {"before": before, "after": after, "delta": delta, "pct_change": pct_change}


def diff_reports(baseline: dict, current: dict) -> dict:
    """Negative delta / pct_change on latency or exec-time metrics means the
    current run is faster than baseline -- an actual, measured improvement,
    not just a rule engine's confidence score."""
    diff = {"http": {}, "db": {"fingerprints": {}}}

    baseline_http = baseline.get("http", {})
    current_http = current.get("http", {})
    for endpoint in set(baseline_http) | set(current_http):
        b = baseline_http.get(endpoint, {})
        c = current_http.get(endpoint, {})
        diff["http"][endpoint] = {
            "p50_ms": _delta(b.get("p50_ms"), c.get("p50_ms")),
            "p95_ms": _delta(b.get("p95_ms"), c.get("p95_ms")),
            "p99_ms": _delta(b.get("p99_ms"), c.get("p99_ms")),
            "errors": {"before": b.get("errors"), "after": c.get("errors")},
        }

    baseline_db = baseline.get("db", {})
    current_db = current.get("db", {})
    diff["db"]["buffer_hit_ratio"] = _delta(
        baseline_db.get("buffer_hit_ratio_end"), current_db.get("buffer_hit_ratio_end")
    )

    baseline_fp = baseline_db.get("fingerprints", {})
    current_fp = current_db.get("fingerprints", {})
    for name in set(baseline_fp) | set(current_fp):
        b = baseline_fp.get(name, {})
        c = current_fp.get(name, {})
        diff["db"]["fingerprints"][name] = _delta(
            b.get("avg_mean_exec_time_ms"), c.get("avg_mean_exec_time_ms")
        )

    return diff
