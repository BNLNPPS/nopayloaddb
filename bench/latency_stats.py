"""Latency statistics and noise-aware comparison, so a single lucky run is
never reported as an improvement. Stdlib only."""

import math
from typing import Optional

# Two-sided t critical values at alpha = 0.05, by degrees of freedom.
_T_CRITICAL_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
    27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042, 40: 2.021, 50: 2.009,
    60: 2.000, 80: 1.990, 100: 1.984,
}

# Must clear significance AND this floor; not tunable, or a rule can be forced to pass.
MIN_RELEVANT_PCT_CHANGE = 3.0


def percentile(values: list, pct: float) -> Optional[float]:
    """Linear-interpolation percentile (pct in [0, 100]). None for empty input."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    rank = (pct / 100) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[int(rank)]
    fraction = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def stdev(values: list) -> Optional[float]:
    """Sample standard deviation (n-1). None for fewer than two samples."""
    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(variance)


def summarize(latencies_ms: list, errors: int = 0) -> dict:
    """Summary of one repetition."""
    count = len(latencies_ms)
    return {
        "count": count,
        "errors": errors,
        "mean_ms": (sum(latencies_ms) / count) if count else None,
        "stdev_ms": stdev(latencies_ms),
        "p50_ms": percentile(latencies_ms, 50),
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
        "min_ms": min(latencies_ms) if latencies_ms else None,
        "max_ms": max(latencies_ms) if latencies_ms else None,
    }


_AGGREGATED_METRICS = ("mean_ms", "p50_ms", "p95_ms", "p99_ms")


def aggregate_repetitions(summaries: list) -> dict:
    """Fold per-repetition summaries into a distribution; `values` keeps every repetition."""
    if not summaries:
        return {"repetitions": 0, "metrics": {}, "errors": 0, "count": 0}

    metrics = {}
    for metric in _AGGREGATED_METRICS:
        values = [s[metric] for s in summaries if s.get(metric) is not None]
        metrics[metric] = {
            "values": values,
            "n": len(values),
            "mean": (sum(values) / len(values)) if values else None,
            "stdev": stdev(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "median": percentile(values, 50),
        }

    return {
        "repetitions": len(summaries),
        "count": sum(s.get("count") or 0 for s in summaries),
        "errors": sum(s.get("errors") or 0 for s in summaries),
        "metrics": metrics,
        "per_repetition": summaries,
    }


def t_critical_95(df: float) -> float:
    if df <= 0:
        return float("inf")
    df_int = int(math.floor(df))
    if df_int >= 100:
        return 1.984 if df_int < 200 else 1.960
    if df_int in _T_CRITICAL_95:
        return _T_CRITICAL_95[df_int]
    # Fall back to the next-lower tabulated df (conservative: larger critical value).
    lower = max(k for k in _T_CRITICAL_95 if k <= df_int)
    return _T_CRITICAL_95[lower]


def welch_test(a_values: list, b_values: list) -> dict:
    """Welch's t-test, alpha=0.05 two-sided. `significant: None` means the test
    could not run -- the verdict logic must treat that as unknown, not "no difference"."""
    na, nb = len(a_values), len(b_values)
    if na < 2 or nb < 2:
        return {
            "t": None, "df": None, "t_critical": None, "significant": None,
            "reason": "need at least 2 repetitions per condition",
        }

    mean_a, mean_b = sum(a_values) / na, sum(b_values) / nb
    var_a = sum((v - mean_a) ** 2 for v in a_values) / (na - 1)
    var_b = sum((v - mean_b) ** 2 for v in b_values) / (nb - 1)

    se_sq = var_a / na + var_b / nb
    if se_sq <= 0:
        # Constant and equal means no effect; constant and unequal is unknown.
        if math.isclose(mean_a, mean_b):
            return {"t": 0.0, "df": None, "t_critical": None, "significant": False,
                    "reason": "both conditions constant and equal"}
        return {"t": None, "df": None, "t_critical": None, "significant": None,
                "reason": "zero observed variance; cannot estimate noise"}

    se = math.sqrt(se_sq)
    t = (mean_b - mean_a) / se
    df_num = se_sq ** 2
    df_den = (var_a / na) ** 2 / (na - 1) + (var_b / nb) ** 2 / (nb - 1)
    df = df_num / df_den if df_den > 0 else float(na + nb - 2)
    crit = t_critical_95(df)

    return {
        "t": t,
        "df": df,
        "t_critical": crit,
        "significant": abs(t) > crit,
        "reason": None,
    }


def compare_metric(baseline_agg: dict, optimized_agg: dict, metric: str = "p95_ms") -> dict:
    """Compare one metric; status is improved / regressed / within_noise / unknown."""
    b = (baseline_agg.get("metrics") or {}).get(metric) or {}
    o = (optimized_agg.get("metrics") or {}).get(metric) or {}
    b_values, o_values = b.get("values") or [], o.get("values") or []

    result = {
        "metric": metric,
        "baseline": {k: b.get(k) for k in ("mean", "median", "stdev", "min", "max", "n")},
        "optimized": {k: o.get(k) for k in ("mean", "median", "stdev", "min", "max", "n")},
        "baseline_values": b_values,
        "optimized_values": o_values,
    }

    if not b_values or not o_values:
        result.update({"delta": None, "pct_change": None, "status": "unknown",
                       "reason": "missing samples on one side", "test": None,
                       "practically_relevant": None, "noise_band": None})
        return result

    b_mean, o_mean = b["mean"], o["mean"]
    delta = o_mean - b_mean
    pct_change = (delta / b_mean * 100) if b_mean else None

    test = welch_test(b_values, o_values)
    # Plain-language noise floor: two pooled standard deviations.
    pooled_sd = math.sqrt(((b.get("stdev") or 0.0) ** 2 + (o.get("stdev") or 0.0) ** 2) / 2)
    noise_band = 2 * pooled_sd

    relevant = pct_change is not None and abs(pct_change) >= MIN_RELEVANT_PCT_CHANGE

    if test["significant"] is None:
        status, reason = "unknown", test["reason"]
    elif not test["significant"]:
        status, reason = "within_noise", "difference does not exceed run-to-run noise"
    elif not relevant:
        status = "within_noise"
        reason = (f"statistically detectable but below the {MIN_RELEVANT_PCT_CHANGE}% "
                  "practical-relevance floor")
    elif delta < 0:
        status, reason = "improved", None
    else:
        status, reason = "regressed", None

    result.update({
        "delta": delta,
        "pct_change": pct_change,
        "noise_band": noise_band,
        "test": test,
        "practically_relevant": relevant,
        "status": status,
        "reason": reason,
    })
    return result
