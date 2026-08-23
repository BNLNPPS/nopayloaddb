"""Report assembly: does the comparison carry every section, with the right verdict."""

import json

import pytest

from bench.config import BenchConfig, WorkloadConfig, WorkloadProfile
from bench.latency_stats import aggregate_repetitions, summarize
from bench.plan_evidence import extract_features
from bench.report import (
    build_condition_report,
    compare_conditions,
    load_report,
    render_text,
    save_report,
)
from bench.verdict import INCONCLUSIVE, REGRESSED, VERIFIED
from tests.fixtures import plans


def condition(label, latencies_per_rep, plan, *, hit_ratio=0.95, calls=1000,
              exec_ms=100_000.0, profile=WorkloadProfile.COLD, repetitions=5,
              table_stats=None, applied=(), state_hash="abc"):
    workload = WorkloadConfig(profile=profile, major_iov_max=500, minor_iov_min=0, pool_size=64)
    config = BenchConfig(label=label, repetitions=repetitions, workload=workload,
                         applied_suggestions=applied)
    return build_condition_report(
        label=label,
        config=config,
        workload_summary={**workload.describe(), "distinct_points_wide": 64,
                          "artificially_cacheable": workload.is_artificially_cacheable},
        started_at="2026-08-21T10:00:00Z",
        finished_at="2026-08-21T10:05:00Z",
        endpoint_coverage={"requested": ["sql"], "exercised": ["sql"], "skipped": {},
                           "required": ["sql"], "complete": True},
        latency_by_endpoint={
            "sql": aggregate_repetitions([summarize(v) for v in latencies_per_rep])},
        db_metrics={
            "windowed_hit_ratio": hit_ratio, "delta_blks_hit": 9500, "delta_blks_read": 500,
            "stats_reset_detected": False, "pg_stat_statements_available": True,
            "fingerprints": {"sql": {"delta_calls": calls, "delta_exec_time_ms": exec_ms,
                                     "windowed_mean_exec_time_ms": exec_ms / calls,
                                     "usable": True}},
        },
        plan_features={"sql": extract_features(plan)},
        plan_raw={"sql": plan},
        table_stats=table_stats or {},
        db_state={"hash": state_hash, "guc": {}, "indexes": {}, "tables": {}},
        warmup_issued=200,
    )


SLOW = [[190.0], [192.0], [188.0], [191.0], [189.0]]
FAST = [[60.0], [62.0], [58.0], [61.0], [59.0]]
NOISY = [[190.0], [250.0], [130.0], [230.0], [150.0]]


class TestConditionReport:
    def test_carries_every_required_section(self):
        r = condition("baseline", SLOW, plans.INDEX_SCAN_HEAP)
        for key in ("workload", "coverage", "latency", "db", "plan", "plan_raw",
                    "table_stats", "db_state"):
            assert key in r

    def test_workload_section_is_reproducible(self):
        w = condition("baseline", SLOW, plans.INDEX_SCAN_HEAP)["workload"]
        for key in ("profile", "seed", "repetitions", "warmup_requests",
                    "requests_per_endpoint", "gt_names", "major_iov_range"):
            assert key in w

    def test_round_trips_through_disk(self, tmp_path):
        r = condition("baseline", SLOW, plans.INDEX_SCAN_HEAP)
        path = save_report(r, str(tmp_path), "baseline")
        assert load_report(path)["label"] == "baseline"

    def test_is_json_serialisable(self):
        json.dumps(condition("baseline", SLOW, plans.INDEX_SCAN_HEAP), default=str)


class TestCompareConditions:
    def test_verified_needs_both_latency_and_mechanism(self):
        c = compare_conditions(
            condition("baseline", SLOW, plans.INDEX_SCAN_HEAP),
            condition("after-r7", FAST, plans.INDEX_ONLY_SCAN_CLEAN),
            rule_id="R7")
        assert c["verdict"]["status"] == VERIFIED
        assert c["plan_evidence"]["postcondition"]["status"] == "confirmed"

    def test_improvement_without_the_mechanism_is_inconclusive(self):
        # Faster, but a stale visibility map means the index is not doing the work.
        c = compare_conditions(
            condition("baseline", SLOW, plans.INDEX_SCAN_HEAP),
            condition("after-r7", FAST, plans.INDEX_ONLY_SCAN_STALE_VM),
            rule_id="R7")
        assert c["verdict"]["status"] == INCONCLUSIVE
        assert c["plan_evidence"]["postcondition"]["status"] == "refuted"

    def test_mechanism_without_improvement_is_a_null_result(self):
        c = compare_conditions(
            condition("baseline", SLOW, plans.INDEX_SCAN_HEAP),
            condition("after-r7", SLOW, plans.INDEX_ONLY_SCAN_CLEAN),
            rule_id="R7")
        assert c["verdict"]["status"] == INCONCLUSIVE
        assert "null result" in c["verdict"]["rationale"]

    def test_noise_is_never_a_win(self):
        c = compare_conditions(
            condition("baseline", NOISY, plans.INDEX_SCAN_HEAP),
            condition("after-r7", NOISY, plans.INDEX_ONLY_SCAN_CLEAN),
            rule_id="R7")
        assert c["verdict"]["status"] == INCONCLUSIVE

    def test_regression_is_reported(self):
        c = compare_conditions(
            condition("baseline", FAST, plans.INDEX_SCAN_HEAP),
            condition("after", SLOW, plans.INDEX_ONLY_SCAN_CLEAN),
            rule_id="R7")
        assert c["verdict"]["status"] == REGRESSED

    def test_no_rule_id_means_no_postcondition(self):
        c = compare_conditions(condition("b", SLOW, plans.INDEX_SCAN_HEAP),
                               condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN))
        assert c["plan_evidence"]["postcondition"] is None
        assert c["verdict"]["status"] == INCONCLUSIVE

    def test_windowed_db_metrics_are_compared(self):
        c = compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP, hit_ratio=0.80,
                      calls=1000, exec_ms=190_000.0),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN, hit_ratio=0.99,
                      calls=1000, exec_ms=60_000.0),
            rule_id="R7")
        db = c["db_metrics"]
        assert db["windowed_hit_ratio"]["delta"] == pytest.approx(0.19)
        fp = db["fingerprints"]["sql"]
        assert fp["baseline_windowed_mean_exec_time_ms"] == 190.0
        assert fp["optimized_windowed_mean_exec_time_ms"] == 60.0
        assert fp["windowed_mean_pct_change"] < 0

    def test_detects_and_names_plan_changes(self):
        c = compare_conditions(condition("b", SLOW, plans.INDEX_SCAN_HEAP),
                               condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN),
                               rule_id="R7")
        changes = " ".join(c["plan_evidence"]["detected_changes"]["changes"])
        assert "Index Only Scan" in changes
        assert "Heap Fetches" in changes

    def test_missing_plan_degrades_gracefully(self):
        base = condition("b", SLOW, plans.INDEX_SCAN_HEAP)
        base["plan_raw"] = {}
        c = compare_conditions(base, condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN),
                               rule_id="R7")
        assert c["plan_evidence"]["detected_changes"]["available"] is False
        assert c["verdict"]["status"] == INCONCLUSIVE

    def test_stale_baseline_state_becomes_a_caveat(self):
        c = compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP, state_hash="aaa"),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN, state_hash="bbb"),
            rule_id="R7",
            db_state_comparison={"comparable": False, "differences": {"guc": {}},
                                 "reason": "changed"})
        assert any("different database state" in c2 for c2 in c["verdict"]["caveats"])

    def test_hot_workload_becomes_a_caveat(self):
        c = compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP, profile=WorkloadProfile.HOT),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN, profile=WorkloadProfile.HOT),
            rule_id="R7")
        assert any("cacheable" in x or "single-tuple" in x for x in c["verdict"]["caveats"])

    def test_cumulative_application_is_flagged(self):
        c = compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN, applied=(1, 2, 7)),
            rule_id="R7")
        assert any("MARGINAL" in x for x in c["verdict"]["caveats"])

    def test_single_repetition_cannot_verify(self):
        c = compare_conditions(
            condition("b", [[190.0]], plans.INDEX_SCAN_HEAP, repetitions=1),
            condition("a", [[60.0]], plans.INDEX_ONLY_SCAN_CLEAN, repetitions=1),
            rule_id="R7")
        assert c["verdict"]["status"] == INCONCLUSIVE

    def test_comparison_is_json_serialisable(self):
        c = compare_conditions(condition("b", SLOW, plans.INDEX_SCAN_HEAP),
                               condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN),
                               rule_id="R7")
        json.dumps(c, default=str)


class TestRenderText:
    def test_contains_every_section(self):
        text = render_text(compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN), rule_id="R7"))
        for heading in ("WORKLOAD", "LATENCY", "DATABASE", "PLAN EVIDENCE", "VERDICT"):
            assert heading in text

    def test_shows_spread_alongside_the_headline(self):
        text = render_text(compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN), rule_id="R7"))
        assert "sd " in text and ".." in text

    def test_renders_caveats(self):
        text = render_text(compare_conditions(
            condition("b", SLOW, plans.INDEX_SCAN_HEAP, profile=WorkloadProfile.HOT),
            condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN, profile=WorkloadProfile.HOT),
            rule_id="R7"))
        assert "!" in text


class TestBaselineValidation:
    """--compare-to must reject anything that cannot serve as a baseline,
    rather than degrading to a verdict that looks like a measurement."""

    def test_accepts_a_condition_report(self):
        from bench.report import validate_condition_report
        r = condition("baseline", SLOW, plans.INDEX_SCAN_HEAP)
        assert validate_condition_report(r, "x.json") is r

    def test_rejects_a_comparison_report(self):
        from bench.report import NotAConditionReport, validate_condition_report
        comparison = compare_conditions(condition("b", SLOW, plans.INDEX_SCAN_HEAP),
                                        condition("a", FAST, plans.INDEX_ONLY_SCAN_CLEAN),
                                        rule_id="R7")
        with pytest.raises(NotAConditionReport) as exc:
            validate_condition_report(comparison, "after_vs_baseline.json")
        assert "comparison report" in str(exc.value)

    def test_rejects_a_report_without_latency(self):
        from bench.report import NotAConditionReport, validate_condition_report
        r = condition("baseline", SLOW, plans.INDEX_SCAN_HEAP)
        r["latency"] = {}
        with pytest.raises(NotAConditionReport):
            validate_condition_report(r, "x.json")

    def test_rejects_a_report_without_a_repetition_count(self):
        from bench.report import NotAConditionReport, validate_condition_report
        r = condition("baseline", SLOW, plans.INDEX_SCAN_HEAP)
        r["workload"].pop("repetitions")
        with pytest.raises(NotAConditionReport) as exc:
            validate_condition_report(r, "x.json")
        assert "noise floor" in str(exc.value)
