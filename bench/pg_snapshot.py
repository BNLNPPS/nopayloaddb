"""Windowed PostgreSQL statistics: snapshot containers and diff maths.

Every pg_stat_* counter is cumulative since the last reset, so a benchmark has
to snapshot both ends and subtract. Django-free so the arithmetic is testable.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BufferCounters:
    blks_hit: int = 0
    blks_read: int = 0
    stats_reset: Optional[str] = None  # moves => counters restarted, deltas untrustworthy


@dataclass
class StatementCounters:
    queryid: str
    calls: int = 0
    total_exec_time: float = 0.0
    shared_blks_hit: int = 0
    shared_blks_read: int = 0
    rows: int = 0
    query_text: str = ""
    fingerprint: Optional[str] = None


@dataclass
class DBSnapshot:
    captured_at: Optional[str] = None
    buffers: BufferCounters = field(default_factory=BufferCounters)
    statements: dict = field(default_factory=dict)  # queryid -> StatementCounters
    statements_stats_reset: Optional[str] = None
    pg_stat_statements_available: bool = True

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at,
            "buffers": {
                "blks_hit": self.buffers.blks_hit,
                "blks_read": self.buffers.blks_read,
                "stats_reset": self.buffers.stats_reset,
            },
            "statements_stats_reset": self.statements_stats_reset,
            "pg_stat_statements_available": self.pg_stat_statements_available,
            "statement_count": len(self.statements),
        }


def diff_buffers(start: BufferCounters, end: BufferCounters) -> dict:
    """Windowed buffer hit ratio. None (never a fabricated number) when the window
    saw no block activity, or the counters reset mid-run."""
    reset = _counters_reset(start, end)

    delta_hit = end.blks_hit - start.blks_hit
    delta_read = end.blks_read - start.blks_read

    if reset:
        return {
            "delta_blks_hit": None,
            "delta_blks_read": None,
            "windowed_hit_ratio": None,
            "stats_reset_detected": True,
            "reason": "pg_stat_database counters reset during the benchmark window",
        }

    total = delta_hit + delta_read
    if total <= 0:
        return {
            "delta_blks_hit": delta_hit,
            "delta_blks_read": delta_read,
            "windowed_hit_ratio": None,
            "stats_reset_detected": False,
            "reason": "no block activity recorded in the window",
        }

    return {
        "delta_blks_hit": delta_hit,
        "delta_blks_read": delta_read,
        "windowed_hit_ratio": delta_hit / total,
        "stats_reset_detected": False,
        "reason": None,
    }


def _counters_reset(start: BufferCounters, end: BufferCounters) -> bool:
    if start.stats_reset and end.stats_reset and start.stats_reset != end.stats_reset:
        return True
    return end.blks_hit < start.blks_hit or end.blks_read < start.blks_read


def diff_statements(start: DBSnapshot, end: DBSnapshot) -> dict:
    """Per-queryid windowed statistics: delta_time / delta_calls.

    Awkward cases are named in `status` rather than silently producing a number:
    first_seen_in_window, disappeared, no_calls_in_window, stats_reset.
    """
    global_reset = bool(
        start.statements_stats_reset
        and end.statements_stats_reset
        and start.statements_stats_reset != end.statements_stats_reset
    )

    out = {}
    for queryid in set(start.statements) | set(end.statements):
        s = start.statements.get(queryid)
        e = end.statements.get(queryid)

        if e is None:
            out[queryid] = _statement_result(
                s, None, "disappeared",
                "queryid vanished from pg_stat_statements (evicted or reset)",
            )
            continue

        if global_reset:
            out[queryid] = _statement_result(
                s, e, "stats_reset",
                "pg_stat_statements was reset during the benchmark window",
            )
            continue

        if s is None:
            zero = StatementCounters(queryid=queryid, query_text=e.query_text,
                                     fingerprint=e.fingerprint)
            out[queryid] = _statement_result(zero, e, "first_seen_in_window", None)
            continue

        if e.calls < s.calls or e.total_exec_time < s.total_exec_time:
            out[queryid] = _statement_result(
                s, e, "stats_reset",
                "counters went backwards; pg_stat_statements entry was reset or recycled",
            )
            continue

        if e.calls == s.calls:
            out[queryid] = _statement_result(
                s, e, "no_calls_in_window",
                "statement was not executed during the benchmark window",
            )
            continue

        out[queryid] = _statement_result(s, e, "ok", None)

    return out


def _statement_result(start, end, status: str, reason: Optional[str]) -> dict:
    base = {
        "queryid": (end or start).queryid if (end or start) else None,
        "fingerprint": (end or start).fingerprint if (end or start) else None,
        "query_text": ((end or start).query_text or "")[:400] if (end or start) else "",
        "status": status,
        "reason": reason,
        "delta_calls": None,
        "delta_exec_time_ms": None,
        "windowed_mean_exec_time_ms": None,
        "delta_shared_blks_read": None,
        "delta_shared_blks_hit": None,
        "delta_rows": None,
    }
    if status not in ("ok", "first_seen_in_window") or start is None or end is None:
        return base

    delta_calls = end.calls - start.calls
    delta_time = end.total_exec_time - start.total_exec_time
    base.update({
        "delta_calls": delta_calls,
        "delta_exec_time_ms": delta_time,
        "windowed_mean_exec_time_ms": (delta_time / delta_calls) if delta_calls > 0 else None,
        "delta_shared_blks_read": end.shared_blks_read - start.shared_blks_read,
        "delta_shared_blks_hit": end.shared_blks_hit - start.shared_blks_hit,
        "delta_rows": end.rows - start.rows,
    })
    if delta_calls <= 0:
        base["status"] = "no_calls_in_window"
        base["reason"] = "statement was not executed during the benchmark window"
    return base


def by_fingerprint(statement_diffs: dict) -> dict:
    """Roll per-queryid diffs up to the named fingerprints, call-weighting the mean."""
    grouped = {}
    for entry in statement_diffs.values():
        name = entry.get("fingerprint")
        if not name:
            continue
        g = grouped.setdefault(name, {
            "queryids": [], "delta_calls": 0, "delta_exec_time_ms": 0.0,
            "delta_shared_blks_read": 0, "delta_shared_blks_hit": 0,
            "statuses": [],
        })
        g["queryids"].append(entry["queryid"])
        g["statuses"].append(entry["status"])
        for key in ("delta_calls", "delta_exec_time_ms",
                    "delta_shared_blks_read", "delta_shared_blks_hit"):
            if entry.get(key) is not None:
                g[key] += entry[key]

    # Uncalled queryids contribute 0; only undifferenceable counters corrupt the sum.
    untrustworthy = {"stats_reset", "disappeared"}
    for g in grouped.values():
        calls = g["delta_calls"]
        g["windowed_mean_exec_time_ms"] = (g["delta_exec_time_ms"] / calls) if calls > 0 else None
        g["usable"] = calls > 0 and not (untrustworthy & set(g["statuses"]))
    return grouped
