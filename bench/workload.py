"""Deterministic parameter pools. Replaying one tuple makes the workload
perfectly cacheable, which flatters R8 and hides R5/R7 entirely."""

import random

from .config import IOVPoint, WorkloadConfig, WorkloadProfile


def _spread(lo: int, hi: int, count: int, rng: random.Random) -> list:
    """`count` values evenly spread over [lo, hi], then shuffled so the sweep is not monotonic."""
    if hi <= lo:
        return [lo] * count
    span = hi - lo
    if count == 1:
        return [lo + span // 2]
    values = [lo + round(span * i / (count - 1)) for i in range(count)]
    rng.shuffle(values)
    return values


def build_pool(workload: WorkloadConfig) -> list:
    """`pool_size` distinct tuples across GTs and the IOV space."""
    rng = random.Random(workload.seed)
    size = workload.pool_size

    majors = _spread(workload.major_iov_min, workload.major_iov_max, size, rng)
    minors = _spread(workload.minor_iov_min, workload.minor_iov_max, size, rng)
    gts = list(workload.gt_names)

    pool = []
    seen = set()
    for i in range(size):
        point = IOVPoint(
            gt_name=gts[i % len(gts)],
            major_iov=majors[i],
            minor_iov=minors[i],
        )
        if point in seen:
            continue
        seen.add(point)
        pool.append(point)
    return pool


def build_hot_pool(workload: WorkloadConfig) -> list:
    """`hot_pool_size` tuples from the head of the wide pool, so hot is a subset of cold."""
    wide = build_pool(workload)
    n = min(workload.hot_pool_size, len(wide))
    return wide[:n]


def request_sequence(workload: WorkloadConfig, count: int, stream: str = "recorded") -> list:
    """`count` IOVPoints in submission order.

    `stream` namespaces the RNG so warmup and the recorded pass draw different
    sequences from the same pool -- an exact replay would prefetch the recorded
    working set and reintroduce the bias warmup exists to remove.
    """
    if count <= 0:
        return []

    rng = random.Random(f"{workload.seed}|{workload.profile}|{stream}")

    if workload.profile == WorkloadProfile.HOT:
        pool = build_hot_pool(workload)
        return [pool[i % len(pool)] for i in range(count)]

    if workload.profile == WorkloadProfile.COLD:
        return _cycle_permutations(build_pool(workload), count, rng)

    # Shuffled so hot and cold requests are not segregated in time.
    hot = build_hot_pool(workload)
    wide = [p for p in build_pool(workload) if p not in set(hot)] or build_pool(workload)

    hot_count = int(round(count * workload.mixed_hot_fraction))
    cold_count = count - hot_count

    sequence = [hot[i % len(hot)] for i in range(hot_count)]
    sequence.extend(_cycle_permutations(wide, cold_count, rng))
    rng.shuffle(sequence)
    return sequence


def _cycle_permutations(pool: list, count: int, rng: random.Random) -> list:
    """Every pool entry is used before any is reused, so coverage is uniform."""
    if not pool:
        return []
    out = []
    while len(out) < count:
        block = list(pool)
        rng.shuffle(block)
        out.extend(block)
    return out[:count]


def pool_summary(workload: WorkloadConfig) -> dict:
    """What the pool actually contains, for the report."""
    wide = build_pool(workload)
    hot = build_hot_pool(workload)
    return {
        "distinct_points_wide": len(wide),
        "distinct_points_hot": len(hot),
        "sample_points": [p.as_dict() for p in wide[:5]],
        "artificially_cacheable": workload.is_artificially_cacheable,
        "cacheability_reason": workload.cacheability_reason(),
        "distinct_parameter_space": workload.distinct_parameter_space,
    }
