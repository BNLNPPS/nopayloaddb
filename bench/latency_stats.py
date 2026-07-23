"""Percentile/summary stats for a list of latency samples, no numpy required."""

import math
from typing import Optional


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


def summarize(latencies_ms: list, errors: int = 0) -> dict:
    count = len(latencies_ms)
    return {
        "count": count,
        "errors": errors,
        "mean_ms": (sum(latencies_ms) / count) if count else None,
        "p50_ms": percentile(latencies_ms, 50),
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
        "max_ms": max(latencies_ms) if latencies_ms else None,
    }
