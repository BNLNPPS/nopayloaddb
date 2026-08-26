"""The verdict matrix -- the part that must not be gameable."""

import pytest

from bench.plan_evidence import CONFIRMED, NOT_CHECKED, REFUTED, UNVERIFIABLE, PostconditionResult
from bench.reversibility import classify
from bench.verdict import INCONCLUSIVE, REGRESSED, VERIFIED, evaluate

IMPROVED = {"status": "improved", "pct_change": -24.0}
REGRESSED_LAT = {"status": "regressed", "pct_change": 18.0}
FLAT = {"status": "within_noise", "pct_change": -1.2}
UNKNOWN_LAT = {"status": "unknown", "pct_change": None, "reason": "not enough samples"}

OK = PostconditionResult("R7", CONFIRMED, "Index Only Scan with Heap Fetches = 0.")
NO = PostconditionResult("R7", REFUTED, "Still 1380000 heap fetches; visibility map is stale.")
UNVERIF = PostconditionResult("R8", UNVERIFIABLE, "Application-layer change.")
UNCHECKED = PostconditionResult("R99", NOT_CHECKED, "No postcondition registered.")


class TestMatrix:
    @pytest.mark.parametrize("latency,mechanism,expected", [
        (IMPROVED, OK, VERIFIED),
        (IMPROVED, NO, INCONCLUSIVE),
        (IMPROVED, UNVERIF, INCONCLUSIVE),
        (IMPROVED, UNCHECKED, INCONCLUSIVE),
        (REGRESSED_LAT, OK, REGRESSED),
        (REGRESSED_LAT, NO, REGRESSED),
        (REGRESSED_LAT, UNVERIF, REGRESSED),
        (FLAT, OK, INCONCLUSIVE),
        (FLAT, NO, INCONCLUSIVE),
        (UNKNOWN_LAT, OK, INCONCLUSIVE),
    ])
    def test_verdict(self, latency, mechanism, expected):
        assert evaluate(latency, mechanism, repetitions=5).status == expected

    def test_latency_alone_can_never_verify(self):
        # This is the central invariant: correlation is not causation.
        for mechanism in (NO, UNVERIF, UNCHECKED, None):
            assert evaluate(IMPROVED, mechanism, repetitions=5).status != VERIFIED

    def test_mechanism_alone_can_never_verify(self):
        assert evaluate(FLAT, OK, repetitions=5).status != VERIFIED

    def test_no_postcondition_object_at_all(self):
        v = evaluate(IMPROVED, None, repetitions=5)
        assert v.status == INCONCLUSIVE and v.mechanism_status == NOT_CHECKED


class TestRationale:
    def test_ambiguous_improvement_is_named_as_such(self):
        v = evaluate(IMPROVED, NO, repetitions=5)
        assert "not attributable" in v.rationale

    def test_null_result_is_preserved_not_hidden(self):
        v = evaluate(FLAT, OK, repetitions=5)
        assert "null result" in v.rationale
        assert "buys nothing measurable" in v.rationale

    def test_regression_names_a_counterproductive_mechanism(self):
        assert "counterproductive" in evaluate(REGRESSED_LAT, OK, repetitions=5).rationale


class TestCaveats:
    def test_single_repetition_blocks_a_verified_verdict(self):
        v = evaluate(IMPROVED, OK, repetitions=1)
        assert v.status == INCONCLUSIVE
        assert any("noise floor" in c for c in v.caveats)

    def test_zero_repetitions(self):
        assert evaluate(IMPROVED, OK, repetitions=0).status == INCONCLUSIVE

    def test_cacheable_workload_is_flagged(self):
        v = evaluate(IMPROVED, OK, repetitions=5, workload_artificially_cacheable=True)
        assert any("cacheable" in c or "single-tuple" in c for c in v.caveats)

    def test_cumulative_experiment_is_flagged_as_marginal(self):
        v = evaluate(IMPROVED, OK, repetitions=5,
                     experiment_mode="cumulative", applied_suggestions=(1, 2, 3))
        assert any("MARGINAL" in c for c in v.caveats)

    def test_independent_mode_carries_no_marginal_caveat(self):
        v = evaluate(IMPROVED, OK, repetitions=5,
                     experiment_mode="independent", applied_suggestions=(3,))
        assert not any("MARGINAL" in c for c in v.caveats)

    def test_single_suggestion_is_not_flagged_as_cumulative(self):
        v = evaluate(IMPROVED, OK, repetitions=5,
                     experiment_mode="cumulative", applied_suggestions=(7,))
        assert not any("MARGINAL" in c for c in v.caveats)

    def test_stale_baseline_is_flagged(self):
        v = evaluate(IMPROVED, OK, repetitions=5, baseline_state_matches=False)
        assert any("different database state" in c for c in v.caveats)

    def test_matching_baseline_state_is_not_flagged(self):
        v = evaluate(IMPROVED, OK, repetitions=5, baseline_state_matches=True)
        assert not any("different database state" in c for c in v.caveats)

    def test_stats_reset_is_flagged(self):
        v = evaluate(IMPROVED, OK, repetitions=5, db_metrics={"stats_reset_detected": True})
        assert any("statistics were reset" in c for c in v.caveats)

    def test_irreversible_change_warns_about_the_next_baseline(self):
        v = evaluate(IMPROVED, OK, repetitions=5,
                     reversibility=classify('ANALYZE "PayloadIOV";'))
        assert any("irreversible" in c for c in v.caveats)

    def test_reversible_change_does_not_warn(self):
        v = evaluate(IMPROVED, OK, repetitions=5,
                     reversibility=classify("SET work_mem = '64MB';"))
        assert not any("irreversible" in c for c in v.caveats)

    def test_caveats_do_not_change_the_status_when_valid(self):
        v = evaluate(IMPROVED, OK, repetitions=5, workload_artificially_cacheable=True)
        assert v.status == VERIFIED and v.caveats


class TestSerialization:
    def test_to_dict_round_trip(self):
        d = evaluate(IMPROVED, OK, repetitions=5).to_dict()
        assert set(d) == {"status", "latency_status", "mechanism_status", "rationale", "caveats"}
