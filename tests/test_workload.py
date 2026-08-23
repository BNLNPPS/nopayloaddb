"""The parameter pool: reproducibility, and defeating artificial cacheability."""

import pytest

from bench.config import BenchConfig, WorkloadConfig, WorkloadProfile
from bench.workload import build_hot_pool, build_pool, pool_summary, request_sequence


def cold(**kw):
    base = dict(profile=WorkloadProfile.COLD, gt_names=("gt_a", "gt_b"),
                major_iov_min=0, major_iov_max=500,
                minor_iov_min=0, minor_iov_max=999999, pool_size=64)
    base.update(kw)
    return WorkloadConfig(**base)


class TestValidation:
    def test_rejects_unknown_profile(self):
        with pytest.raises(ValueError):
            WorkloadConfig(profile="warm")

    def test_rejects_inverted_range(self):
        with pytest.raises(ValueError):
            WorkloadConfig(major_iov_min=10, major_iov_max=0)

    def test_rejects_empty_gt_list(self):
        with pytest.raises(ValueError):
            WorkloadConfig(gt_names=())

    def test_rejects_bad_mixed_fraction(self):
        with pytest.raises(ValueError):
            WorkloadConfig(profile="mixed", mixed_hot_fraction=1.5)


class TestDeterminism:
    def test_same_seed_same_sequence(self):
        w1, w2 = cold(seed=7), cold(seed=7)
        assert request_sequence(w1, 200) == request_sequence(w2, 200)

    def test_different_seed_different_sequence(self):
        assert request_sequence(cold(seed=7), 200) != request_sequence(cold(seed=8), 200)

    def test_pool_is_stable_across_calls(self):
        assert build_pool(cold(seed=3)) == build_pool(cold(seed=3))


class TestProfiles:
    def test_hot_replays_a_tiny_pool(self):
        seq = request_sequence(WorkloadConfig(profile=WorkloadProfile.HOT), 500)
        assert len(set(seq)) == 1

    def test_cold_sweeps_the_pool(self):
        w = cold(pool_size=64)
        seq = request_sequence(w, 64)
        # Every entry used before any is reused, so coverage is uniform, not clustered.
        assert len(set(seq)) == 64

    def test_cold_covers_pool_before_repeating(self):
        w = cold(pool_size=10)
        seq = request_sequence(w, 20)
        assert set(seq[:10]) == set(seq[10:20])

    def test_cold_spans_multiple_gts_and_iovs(self):
        seq = request_sequence(cold(), 200)
        assert len({p.gt_name for p in seq}) == 2
        assert len({p.major_iov for p in seq}) > 10

    def test_mixed_respects_the_hot_fraction(self):
        w = cold(profile=WorkloadProfile.MIXED, hot_pool_size=2, mixed_hot_fraction=0.8,
                 pool_size=32)
        seq = request_sequence(w, 1000)
        hot = set(build_hot_pool(w))
        share = sum(1 for p in seq if p in hot) / len(seq)
        assert share == pytest.approx(0.8, abs=0.02)

    def test_hot_pool_is_a_subset_of_the_wide_pool(self):
        w = cold(hot_pool_size=3)
        assert set(build_hot_pool(w)).issubset(set(build_pool(w)))


class TestWarmupIsolation:
    def test_warmup_draws_a_different_sequence_than_the_recorded_pass(self):
        # An exact replay would make the recorded pass a cache replay of its own set.
        w = cold()
        assert request_sequence(w, 100, "warmup:1:sql") != request_sequence(w, 100, "recorded:1:sql")

    def test_warmup_still_draws_from_the_same_pool(self):
        w = cold()
        assert set(request_sequence(w, 200, "warmup:1:sql")).issubset(set(build_pool(w)))

    def test_repetitions_get_distinct_streams(self):
        w = cold()
        assert request_sequence(w, 64, "recorded:1:sql") != request_sequence(w, 64, "recorded:2:sql")


class TestCacheabilityFlag:
    def test_hot_profile_is_flagged(self):
        assert WorkloadConfig(profile=WorkloadProfile.HOT).is_artificially_cacheable

    def test_wide_cold_profile_is_not_flagged(self):
        assert not cold().is_artificially_cacheable

    def test_cold_over_a_degenerate_range_is_still_flagged(self):
        w = WorkloadConfig(profile=WorkloadProfile.COLD, gt_names=("gt",),
                           major_iov_min=0, major_iov_max=0,
                           minor_iov_min=5, minor_iov_max=5, pool_size=64)
        assert w.is_artificially_cacheable

    def test_summary_exposes_the_flag(self):
        assert pool_summary(WorkloadConfig())["artificially_cacheable"] is True


class TestEdges:
    def test_zero_count(self):
        assert request_sequence(cold(), 0) == []

    def test_count_larger_than_pool(self):
        assert len(request_sequence(cold(pool_size=5), 37)) == 37


class TestWarmupResolution:
    def test_defaults_to_twenty_percent(self):
        assert BenchConfig(requests_per_endpoint=500).resolve_warmup() == 100

    def test_has_a_floor(self):
        assert BenchConfig(requests_per_endpoint=10).resolve_warmup() == 20

    def test_explicit_value_wins(self):
        assert BenchConfig(requests_per_endpoint=500, warmup_requests=7).resolve_warmup() == 7

    def test_can_be_disabled(self):
        assert BenchConfig(warmup_requests=0).resolve_warmup() == 0


class TestCacheabilityReason:
    """Two different causes need two different fixes: the operator chose the
    hot profile, or they chose cold but the database has nothing to sweep."""

    def test_hot_profile_is_told_to_switch_profile(self):
        r = WorkloadConfig(profile=WorkloadProfile.HOT).cacheability_reason()
        assert "--workload-profile cold" in r

    def test_cold_over_thin_data_is_told_to_seed_more(self):
        w = WorkloadConfig(profile=WorkloadProfile.COLD, gt_names=("gt",),
                           major_iov_min=0, major_iov_max=0,
                           minor_iov_min=0, minor_iov_max=0, pool_size=64)
        r = w.cacheability_reason()
        assert "Seed more" in r
        assert "--workload-profile cold" not in r  # they already are on cold

    def test_healthy_workload_has_no_reason(self):
        assert cold().cacheability_reason() is None

    def test_distinct_parameter_space(self):
        w = WorkloadConfig(profile=WorkloadProfile.COLD, gt_names=("a", "b"),
                           major_iov_min=0, major_iov_max=9,
                           minor_iov_min=0, minor_iov_max=0)
        assert w.distinct_parameter_space == 20
