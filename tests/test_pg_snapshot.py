"""Windowed database statistics: the arithmetic and every awkward edge case."""

import pytest

from bench.pg_snapshot import (
    BufferCounters,
    DBSnapshot,
    StatementCounters,
    by_fingerprint,
    diff_buffers,
    diff_statements,
)


def stmt(qid, calls, exec_ms, fingerprint=None, read=0, hit=0, rows=0):
    return StatementCounters(queryid=qid, calls=calls, total_exec_time=exec_ms,
                             shared_blks_read=read, shared_blks_hit=hit, rows=rows,
                             fingerprint=fingerprint, query_text=f"SELECT {qid}")


def snap(statements, reset=None):
    return DBSnapshot(statements={s.queryid: s for s in statements},
                      statements_stats_reset=reset)


class TestDiffBuffers:
    def test_windowed_ratio_ignores_history(self):
        # Cumulative would read ~99%; the window is 50%.
        start = BufferCounters(blks_hit=10_000_000, blks_read=1000, stats_reset="t0")
        end = BufferCounters(blks_hit=10_000_200, blks_read=1200, stats_reset="t0")
        r = diff_buffers(start, end)
        assert r["windowed_hit_ratio"] == 0.5
        assert r["delta_blks_hit"] == 200 and r["delta_blks_read"] == 200

    def test_zero_denominator_is_none_not_a_number(self):
        c = BufferCounters(blks_hit=100, blks_read=10, stats_reset="t0")
        r = diff_buffers(c, BufferCounters(blks_hit=100, blks_read=10, stats_reset="t0"))
        assert r["windowed_hit_ratio"] is None
        assert "no block activity" in r["reason"]

    def test_stats_reset_timestamp_change_invalidates_the_window(self):
        r = diff_buffers(BufferCounters(1000, 100, "t0"), BufferCounters(1200, 300, "t1"))
        assert r["stats_reset_detected"] is True
        assert r["windowed_hit_ratio"] is None

    def test_counters_going_backwards_is_a_reset(self):
        r = diff_buffers(BufferCounters(1000, 100), BufferCounters(5, 1))
        assert r["stats_reset_detected"] is True
        assert r["windowed_hit_ratio"] is None

    def test_all_hits(self):
        assert diff_buffers(BufferCounters(0, 0), BufferCounters(500, 0))["windowed_hit_ratio"] == 1.0


class TestDiffStatements:
    def test_windowed_mean_is_delta_time_over_delta_calls(self):
        a = snap([stmt("1", calls=1000, exec_ms=500_000.0)])   # cumulative mean 500ms
        b = snap([stmt("1", calls=1100, exec_ms=502_000.0)])   # window: 2000ms / 100 = 20ms
        d = diff_statements(a, b)["1"]
        assert d["status"] == "ok"
        assert d["delta_calls"] == 100
        assert d["windowed_mean_exec_time_ms"] == 20.0

    def test_statement_absent_at_start_counts_from_zero(self):
        d = diff_statements(snap([]), snap([stmt("9", calls=10, exec_ms=250.0)]))["9"]
        assert d["status"] == "first_seen_in_window"
        assert d["windowed_mean_exec_time_ms"] == 25.0

    def test_disappeared_statement_yields_no_mean(self):
        d = diff_statements(snap([stmt("1", 10, 100.0)]), snap([]))["1"]
        assert d["status"] == "disappeared"
        assert d["windowed_mean_exec_time_ms"] is None

    def test_zero_delta_calls_yields_no_mean(self):
        a = snap([stmt("1", calls=50, exec_ms=1000.0)])
        d = diff_statements(a, snap([stmt("1", calls=50, exec_ms=1000.0)]))["1"]
        assert d["status"] == "no_calls_in_window"
        assert d["windowed_mean_exec_time_ms"] is None

    def test_backwards_counters_are_a_reset(self):
        a = snap([stmt("1", calls=500, exec_ms=5000.0)])
        d = diff_statements(a, snap([stmt("1", calls=3, exec_ms=30.0)]))["1"]
        assert d["status"] == "stats_reset"
        assert d["windowed_mean_exec_time_ms"] is None

    def test_global_stats_reset_marks_everything(self):
        a = snap([stmt("1", 10, 100.0)], reset="t0")
        b = snap([stmt("1", 900, 90000.0)], reset="t1")
        d = diff_statements(a, b)["1"]
        assert d["status"] == "stats_reset"
        assert d["windowed_mean_exec_time_ms"] is None

    def test_block_deltas_are_windowed_too(self):
        a = snap([stmt("1", 10, 100.0, read=1000, hit=5000)])
        b = snap([stmt("1", 20, 300.0, read=1100, hit=9000)])
        d = diff_statements(a, b)["1"]
        assert d["delta_shared_blks_read"] == 100
        assert d["delta_shared_blks_hit"] == 4000


class TestByFingerprint:
    def test_call_weights_multiple_queryids(self):
        a = snap([stmt("1", 0, 0.0, "sql"), stmt("2", 0, 0.0, "sql")])
        b = snap([stmt("1", 100, 1000.0, "sql"), stmt("2", 100, 3000.0, "sql")])
        g = by_fingerprint(diff_statements(a, b))["sql"]
        assert g["delta_calls"] == 200
        assert g["windowed_mean_exec_time_ms"] == 20.0  # 4000ms / 200 calls
        assert g["usable"] is True

    def test_unusable_when_a_component_reset(self):
        a = snap([stmt("1", 500, 5000.0, "sql")])
        b = snap([stmt("1", 3, 30.0, "sql")])
        assert by_fingerprint(diff_statements(a, b))["sql"]["usable"] is False

    def test_unfingerprinted_statements_are_dropped(self):
        a, b = snap([stmt("1", 0, 0.0)]), snap([stmt("1", 10, 100.0)])
        assert by_fingerprint(diff_statements(a, b)) == {}

    def test_no_calls_means_not_usable(self):
        a = snap([stmt("1", 10, 100.0, "sql")])
        b = snap([stmt("1", 10, 100.0, "sql")])
        g = by_fingerprint(diff_statements(a, b))["sql"]
        assert g["windowed_mean_exec_time_ms"] is None
        assert g["usable"] is False


class TestByFingerprintUsability:
    """Queryids not called this window must not invalidate the ones that were."""

    def test_uncalled_sibling_queryid_does_not_invalidate_the_aggregate(self):
        a = snap([stmt("called", 100, 1000.0, "sql"), stmt("idle", 5, 50.0, "sql")])
        b = snap([stmt("called", 124, 3400.0, "sql"), stmt("idle", 5, 50.0, "sql")])
        g = by_fingerprint(diff_statements(a, b))["sql"]
        assert g["delta_calls"] == 24
        assert g["windowed_mean_exec_time_ms"] == pytest.approx(100.0)
        assert g["usable"] is True

    def test_a_reset_sibling_does_invalidate_it(self):
        a = snap([stmt("called", 100, 1000.0, "sql"), stmt("reset", 900, 9000.0, "sql")])
        b = snap([stmt("called", 124, 3400.0, "sql"), stmt("reset", 2, 20.0, "sql")])
        assert by_fingerprint(diff_statements(a, b))["sql"]["usable"] is False

    def test_a_disappeared_sibling_does_invalidate_it(self):
        a = snap([stmt("called", 100, 1000.0, "sql"), stmt("gone", 10, 100.0, "sql")])
        b = snap([stmt("called", 124, 3400.0, "sql")])
        assert by_fingerprint(diff_statements(a, b))["sql"]["usable"] is False

    def test_all_idle_is_still_unusable(self):
        a = snap([stmt("a", 10, 100.0, "sql"), stmt("b", 5, 50.0, "sql")])
        assert by_fingerprint(diff_statements(a, a))["sql"]["usable"] is False
