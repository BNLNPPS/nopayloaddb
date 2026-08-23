"""Statistics that decide whether a measured difference is real."""

import pytest

from bench.latency_stats import (
    MIN_RELEVANT_PCT_CHANGE,
    aggregate_repetitions,
    compare_metric,
    percentile,
    stdev,
    summarize,
    t_critical_95,
    welch_test,
)


def reps(values_per_rep, errors=0):
    return [summarize(v, errors) for v in values_per_rep]


class TestPercentile:
    def test_empty_returns_none(self):
        assert percentile([], 95) is None

    def test_single_value(self):
        assert percentile([42.0], 95) == 42.0

    def test_interpolates(self):
        assert percentile([0, 10], 50) == 5.0

    def test_known_series(self):
        values = list(range(1, 101))
        assert percentile(values, 50) == pytest.approx(50.5)
        assert percentile(values, 95) == pytest.approx(95.05)


class TestStdev:
    def test_needs_two_samples(self):
        assert stdev([]) is None
        assert stdev([1.0]) is None

    def test_sample_stdev(self):
        assert stdev([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.13809, rel=1e-4)


class TestSummarize:
    def test_reports_spread_not_just_a_point(self):
        s = summarize([10, 20, 30, 40], errors=2)
        assert s["count"] == 4 and s["errors"] == 2
        assert s["min_ms"] == 10 and s["max_ms"] == 40
        assert s["stdev_ms"] is not None

    def test_empty_is_all_none_not_zero(self):
        s = summarize([], errors=5)
        assert s["count"] == 0 and s["errors"] == 5
        assert s["p95_ms"] is None and s["mean_ms"] is None


class TestAggregateRepetitions:
    def test_keeps_every_repetition_visible(self):
        agg = aggregate_repetitions(reps([[100], [110], [105], [98], [102]]))
        assert agg["repetitions"] == 5
        assert len(agg["metrics"]["p95_ms"]["values"]) == 5
        assert agg["metrics"]["p95_ms"]["min"] == 98
        assert agg["metrics"]["p95_ms"]["max"] == 110

    def test_empty(self):
        assert aggregate_repetitions([])["repetitions"] == 0


class TestWelchTest:
    def test_refuses_with_one_repetition(self):
        r = welch_test([100.0], [50.0])
        assert r["significant"] is None
        assert "2 repetitions" in r["reason"]

    def test_detects_a_real_shift(self):
        assert welch_test([100, 101, 99, 100, 102], [70, 71, 69, 70, 72])["significant"] is True

    def test_does_not_fire_on_noise(self):
        assert welch_test([100, 130, 80, 120, 90], [95, 135, 85, 125, 88])["significant"] is False

    def test_zero_variance_unequal_means_is_unknown_not_significant(self):
        # Two constant conditions say nothing about noise, so this is not a difference.
        r = welch_test([100.0] * 5, [50.0] * 5)
        assert r["significant"] is None

    def test_t_critical_is_conservative_for_small_samples(self):
        assert t_critical_95(4) > t_critical_95(30) > t_critical_95(1000)


class TestCompareMetric:
    def test_clear_improvement(self):
        r = compare_metric(
            aggregate_repetitions(reps([[100], [101], [99], [100], [102]])),
            aggregate_repetitions(reps([[70], [71], [69], [70], [72]])),
        )
        assert r["status"] == "improved"
        assert r["pct_change"] < 0

    def test_clear_regression(self):
        r = compare_metric(
            aggregate_repetitions(reps([[70], [71], [69], [70], [72]])),
            aggregate_repetitions(reps([[100], [101], [99], [100], [102]])),
        )
        assert r["status"] == "regressed"
        assert r["pct_change"] > 0

    def test_noise_is_not_a_win(self):
        r = compare_metric(
            aggregate_repetitions(reps([[100], [130], [80], [120], [90]])),
            aggregate_repetitions(reps([[95], [135], [85], [125], [88]])),
        )
        assert r["status"] == "within_noise"

    def test_significant_but_trivial_change_is_not_a_win(self):
        # A 1% shift that a t-test can resolve is still not worth claiming.
        baseline = aggregate_repetitions(reps([[100.0], [100.1], [99.9], [100.0], [100.05]]))
        optimized = aggregate_repetitions(reps([[99.0], [99.1], [98.9], [99.0], [99.05]]))
        r = compare_metric(baseline, optimized)
        assert abs(r["pct_change"]) < MIN_RELEVANT_PCT_CHANGE
        assert r["status"] == "within_noise"
        assert r["practically_relevant"] is False

    def test_single_repetition_cannot_produce_a_claim(self):
        r = compare_metric(
            aggregate_repetitions(reps([[100]])),
            aggregate_repetitions(reps([[50]])),
        )
        assert r["status"] == "unknown"

    def test_missing_side(self):
        assert compare_metric({}, {})["status"] == "unknown"

    def test_noise_band_reported(self):
        r = compare_metric(
            aggregate_repetitions(reps([[100], [110], [90], [105], [95]])),
            aggregate_repetitions(reps([[70], [80], [60], [75], [65]])),
        )
        assert r["noise_band"] > 0
        assert r["baseline_values"] and r["optimized_values"]
