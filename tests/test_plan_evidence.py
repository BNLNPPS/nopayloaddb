"""Plan-feature extraction and the per-rule mechanism postconditions."""

import pytest

from bench.plan_evidence import (
    CONFIRMED,
    NOT_CHECKED,
    REFUTED,
    UNVERIFIABLE,
    MechanismContext,
    check_postcondition,
    extract_features,
    register_postcondition,
    registered_rules,
)
from tests.fixtures import plans


def feats(plan):
    return extract_features(plan)


class TestExtractFeatures:
    def test_rejects_garbage(self):
        with pytest.raises(ValueError):
            extract_features({"not": "a plan"})

    def test_accepts_list_and_dict_wrappers(self):
        assert extract_features(plans.QUICKSORT).sort_methods == ["quicksort"]
        assert extract_features(plans.QUICKSORT[0]).sort_methods == ["quicksort"]

    def test_finds_scan_types_per_relation(self):
        f = feats(plans.SEQ_SCAN_STALE_STATS)
        assert f.scans_on("PayloadIOV") == {"Seq Scan"}
        assert f.scans_on("GlobalTag") == {"Index Scan"}

    def test_finds_heap_fetches(self):
        assert feats(plans.INDEX_ONLY_SCAN_CLEAN).heap_fetches_by_relation["PayloadIOV"] == 0
        assert feats(plans.INDEX_ONLY_SCAN_STALE_VM).heap_fetches_by_relation["PayloadIOV"] == 1380000

    def test_finds_hash_batches_and_sort_methods(self):
        assert feats(plans.HASH_JOIN_SPILL).max_hash_batches == 8
        assert feats(plans.EXTERNAL_MERGE_SORT).has_external_sort() is True
        assert feats(plans.QUICKSORT).has_external_sort() is False

    def test_estimate_deviation_captures_the_worst_node(self):
        # 94 estimated vs 1.4M actual is roughly 4 orders of magnitude.
        assert feats(plans.SEQ_SCAN_STALE_STATS).worst_estimate_deviation() == pytest.approx(4.17, abs=0.05)
        assert feats(plans.INDEX_SCAN_FRESH_STATS).worst_estimate_deviation() < 0.1

    def test_sums_buffer_blocks_across_the_tree(self):
        assert feats(plans.SEQ_SCAN_STALE_STATS).shared_read_blocks == 48002


class TestR1:
    def test_confirmed_when_seq_scan_becomes_index_scan(self):
        r = check_postcondition("R1", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.INDEX_SCAN_FRESH_STATS))
        assert r.status == CONFIRMED and r.holds is True

    def test_refuted_when_seq_scan_remains(self):
        r = check_postcondition("R1", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.SEQ_SCAN_STALE_STATS))
        assert r.status == REFUTED


class TestR2:
    def test_confirmed_when_estimates_converge(self):
        r = check_postcondition("R2", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.INDEX_SCAN_FRESH_STATS))
        assert r.status == CONFIRMED

    def test_refuted_when_estimates_stay_wrong(self):
        r = check_postcondition("R2", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.SEQ_SCAN_STALE_STATS))
        assert r.status == REFUTED


class TestR3:
    def test_confirmed_when_batches_reach_one(self):
        r = check_postcondition("R3", feats(plans.HASH_JOIN_SPILL),
                                feats(plans.HASH_JOIN_IN_MEMORY))
        assert r.status == CONFIRMED
        assert r.evidence["before_hash_batches"] == 8

    def test_refuted_when_it_still_spills(self):
        r = check_postcondition("R3", feats(plans.HASH_JOIN_SPILL), feats(plans.HASH_JOIN_SPILL))
        assert r.status == REFUTED

    def test_unverifiable_when_baseline_never_spilled(self):
        r = check_postcondition("R3", feats(plans.HASH_JOIN_IN_MEMORY),
                                feats(plans.HASH_JOIN_IN_MEMORY))
        assert r.status == UNVERIFIABLE


class TestR4:
    def test_confirmed_on_external_merge_to_quicksort(self):
        r = check_postcondition("R4", feats(plans.EXTERNAL_MERGE_SORT), feats(plans.QUICKSORT))
        assert r.status == CONFIRMED

    def test_refuted_when_still_external(self):
        r = check_postcondition("R4", feats(plans.EXTERNAL_MERGE_SORT),
                                feats(plans.EXTERNAL_MERGE_SORT))
        assert r.status == REFUTED

    def test_unverifiable_without_a_baseline_sort(self):
        r = check_postcondition("R4", feats(plans.QUICKSORT), feats(plans.QUICKSORT))
        assert r.status == UNVERIFIABLE


class TestR5:
    def test_confirmed_on_windowed_hit_ratio_gain(self):
        ctx = MechanismContext(baseline_hit_ratio=0.88, optimized_hit_ratio=0.97)
        r = check_postcondition("R5", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.INDEX_SCAN_FRESH_STATS), ctx)
        assert r.status == CONFIRMED

    def test_confirmed_on_block_read_drop_alone(self):
        r = check_postcondition("R5", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.INDEX_ONLY_SCAN_CLEAN))
        assert r.status == CONFIRMED

    def test_refuted_when_nothing_moved(self):
        ctx = MechanismContext(baseline_hit_ratio=0.90, optimized_hit_ratio=0.9005)
        r = check_postcondition("R5", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.SEQ_SCAN_STALE_STATS), ctx)
        assert r.status == REFUTED


class TestR6:
    def test_confirmed_when_covering_index_used_again(self):
        r = check_postcondition("R6", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.INDEX_SCAN_FRESH_STATS))
        assert r.status == CONFIRMED

    def test_refuted_when_still_seq_scanning(self):
        r = check_postcondition("R6", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.SEQ_SCAN_STALE_STATS))
        assert r.status == REFUTED

    def test_unverifiable_when_baseline_already_used_the_index(self):
        r = check_postcondition("R6", feats(plans.INDEX_SCAN_FRESH_STATS),
                                feats(plans.INDEX_SCAN_FRESH_STATS))
        assert r.status == UNVERIFIABLE


class TestR7:
    def test_confirmed_on_index_only_scan_with_no_heap_fetches(self):
        r = check_postcondition("R7", feats(plans.INDEX_SCAN_HEAP),
                                feats(plans.INDEX_ONLY_SCAN_CLEAN))
        assert r.status == CONFIRMED
        assert r.evidence["after_heap_fetches"] == 0

    def test_refuted_when_index_only_scan_still_hits_the_heap(self):
        # Index-only scans skip the heap only for all-visible pages; a stale VM gains nothing.
        r = check_postcondition("R7", feats(plans.INDEX_SCAN_HEAP),
                                feats(plans.INDEX_ONLY_SCAN_STALE_VM))
        assert r.status == REFUTED
        assert "visibility map" in r.detail.lower()

    def test_refuted_when_it_never_became_index_only(self):
        r = check_postcondition("R7", feats(plans.INDEX_SCAN_HEAP), feats(plans.INDEX_SCAN_HEAP))
        assert r.status == REFUTED

    def test_unverifiable_when_baseline_was_not_an_index_scan(self):
        r = check_postcondition("R7", feats(plans.SEQ_SCAN_STALE_STATS),
                                feats(plans.INDEX_ONLY_SCAN_CLEAN))
        assert r.status == UNVERIFIABLE


class TestR11:
    def test_confirmed_when_dead_tuples_drop_and_vacuum_advanced(self):
        ctx = MechanismContext(
            table_stats_before={"PayloadIOV": {"n_dead_tup": 900000, "last_autovacuum": "2026-08-20T01:00:00Z"}},
            table_stats_after={"PayloadIOV": {"n_dead_tup": 1200, "last_autovacuum": "2026-08-21T01:00:00Z"}},
        )
        assert check_postcondition("R11", None, None, ctx).status == CONFIRMED

    def test_refuted_when_dead_tuples_drop_but_nothing_vacuumed(self):
        # Cannot be attributed to the suggestion.
        ctx = MechanismContext(
            table_stats_before={"PayloadIOV": {"n_dead_tup": 900000, "last_autovacuum": "2026-08-20T01:00:00Z"}},
            table_stats_after={"PayloadIOV": {"n_dead_tup": 1200, "last_autovacuum": "2026-08-20T01:00:00Z"}},
        )
        assert check_postcondition("R11", None, None, ctx).status == REFUTED

    def test_refuted_when_dead_tuples_did_not_fall(self):
        ctx = MechanismContext(
            table_stats_before={"PayloadIOV": {"n_dead_tup": 1000, "last_autovacuum": "a"}},
            table_stats_after={"PayloadIOV": {"n_dead_tup": 5000, "last_autovacuum": "b"}},
        )
        assert check_postcondition("R11", None, None, ctx).status == REFUTED

    def test_unverifiable_without_table_stats(self):
        assert check_postcondition("R11", None, None, MechanismContext()).status == UNVERIFIABLE


class TestUnverifiableRules:
    @pytest.mark.parametrize("rule_id", ["R8", "R9", "R12", "R13"])
    def test_out_of_band_rules_never_silently_pass(self, rule_id):
        r = check_postcondition(rule_id, feats(plans.INDEX_SCAN_HEAP),
                                feats(plans.INDEX_ONLY_SCAN_CLEAN))
        assert r.status == UNVERIFIABLE
        assert r.holds is None and r.checked is False


class TestRegistry:
    def test_unknown_rule_is_not_checked(self):
        r = check_postcondition("R99", feats(plans.INDEX_SCAN_HEAP), feats(plans.INDEX_SCAN_HEAP))
        assert r.status == NOT_CHECKED

    def test_missing_plans_are_unverifiable_not_confirmed(self):
        assert check_postcondition("R7", None, feats(plans.INDEX_ONLY_SCAN_CLEAN)).status == UNVERIFIABLE

    def test_new_rules_can_be_registered(self):
        from bench.plan_evidence import PostconditionResult

        @register_postcondition("R42")
        def _r42(before, after, ctx):
            return PostconditionResult("R42", CONFIRMED, "custom check")

        assert "R42" in registered_rules()
        assert check_postcondition("R42", feats(plans.QUICKSORT), feats(plans.QUICKSORT)).status == CONFIRMED

    def test_all_thirteen_rules_have_a_defined_outcome(self):
        expected = {f"R{i}" for i in range(1, 14)}
        assert expected.issubset(set(registered_rules()))
