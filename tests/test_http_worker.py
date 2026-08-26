"""Warmup, recording, coverage enforcement and clone cleanup, with `_timed_get`
stubbed so no server or database is needed."""

import pytest

from bench import http_worker
from bench.config import BenchConfig, WorkloadConfig, WorkloadProfile
from bench.http_worker import EndpointUnavailable


@pytest.fixture
def calls(monkeypatch):
    """Record every URL the harness requests, and control the response."""
    recorded = []
    responses = {"status": 200, "error": None, "latency": 5.0}

    def fake(session, url, headers, timeout):
        recorded.append(url)
        return responses["latency"], responses["status"], responses["error"]

    monkeypatch.setattr(http_worker, "_timed_get", fake)
    return recorded, responses


def cfg(**kw):
    base = dict(
        requests_per_endpoint=20, warmup_requests=7, concurrency=4, repetitions=2,
        endpoint_names=("sql",), required_endpoints=("sql",),
        workload=WorkloadConfig(profile=WorkloadProfile.COLD, major_iov_max=500,
                                minor_iov_min=0, pool_size=32),
    )
    base.update(kw)
    return BenchConfig(**base)


class TestProbe:
    def test_all_reachable(self, calls):
        result = http_worker.probe_endpoints(cfg(endpoint_names=("sql", "orm_max"),
                                                 required_endpoints=("sql",)))
        assert {e.name for e in result["reachable"]} == {"sql", "orm_max"}
        assert result["skipped"] == {}

    def test_required_endpoint_404_aborts_the_run(self, calls):
        _, responses = calls
        responses["status"] = 404
        with pytest.raises(EndpointUnavailable) as exc:
            http_worker.probe_endpoints(cfg())
        assert "not wired up" in str(exc.value)

    def test_optional_endpoint_404_is_reported_not_hidden(self, calls, monkeypatch):
        def fake(session, url, headers, timeout):
            return (5.0, 404, None) if "orm_max" in url else (5.0, 200, None)
        monkeypatch.setattr(http_worker, "_timed_get", fake)

        result = http_worker.probe_endpoints(
            cfg(endpoint_names=("sql", "orm_max"), required_endpoints=("sql",)))
        assert [e.name for e in result["reachable"]] == ["sql"]
        assert "orm_max" in result["skipped"]

    def test_connection_error_on_a_required_endpoint_aborts(self, calls):
        _, responses = calls
        responses["error"] = "connection refused"
        with pytest.raises(EndpointUnavailable):
            http_worker.probe_endpoints(cfg())

    def test_server_error_is_skipped(self, calls):
        _, responses = calls
        responses["status"] = 500
        with pytest.raises(EndpointUnavailable):
            http_worker.probe_endpoints(cfg())


class TestWarmup:
    def test_issues_the_configured_count_per_endpoint(self, calls):
        recorded, _ = calls
        endpoints = cfg().selected_endpoints()
        issued = http_worker.warmup(cfg(warmup_requests=7), endpoints, repetition=1)
        assert issued == 7
        assert len(recorded) == 7

    def test_scales_with_endpoint_count(self, calls):
        recorded, _ = calls
        config = cfg(endpoint_names=("sql", "orm_max"), warmup_requests=5)
        assert http_worker.warmup(config, config.selected_endpoints(), 1) == 10

    def test_can_be_disabled(self, calls):
        recorded, _ = calls
        config = cfg(warmup_requests=0)
        assert http_worker.warmup(config, config.selected_endpoints(), 1) == 0
        assert recorded == []

    def test_results_are_discarded(self, calls):
        # warmup returns only a count, so no warmup latency reaches the distribution.
        config = cfg()
        assert isinstance(http_worker.warmup(config, config.selected_endpoints(), 1), int)

    def test_default_is_twenty_percent(self, calls):
        config = cfg(requests_per_endpoint=100, warmup_requests=None)
        assert http_worker.warmup(config, config.selected_endpoints(), 1) == 20


class TestRunReadRepetition:
    def test_issues_exactly_requests_per_endpoint(self, calls):
        recorded, _ = calls
        config = cfg(requests_per_endpoint=20)
        result = http_worker.run_read_repetition(config, config.selected_endpoints(), 1)
        assert len(recorded) == 20
        assert result["sql"]["requests_issued"] == 20
        assert len(result["sql"]["latencies_ms"]) == 20

    def test_cold_workload_varies_the_parameters(self, calls):
        recorded, _ = calls
        config = cfg(requests_per_endpoint=32)
        result = http_worker.run_read_repetition(config, config.selected_endpoints(), 1)
        assert result["sql"]["distinct_parameters"] == 32
        assert len(set(recorded)) == 32

    def test_hot_workload_replays_one_url(self, calls):
        recorded, _ = calls
        config = cfg(workload=WorkloadConfig(profile=WorkloadProfile.HOT))
        http_worker.run_read_repetition(config, config.selected_endpoints(), 1)
        assert len(set(recorded)) == 1

    def test_failed_requests_are_excluded_from_the_latency_distribution(self, calls):
        # A fast 500 must never look like a performance win.
        _, responses = calls
        responses["status"] = 500
        config = cfg(requests_per_endpoint=10)
        result = http_worker.run_read_repetition(config, config.selected_endpoints(), 1)
        assert result["sql"]["errors"] == 10
        assert result["sql"]["latencies_ms"] == []

    def test_status_counts_are_reported(self, calls):
        config = cfg(requests_per_endpoint=5)
        result = http_worker.run_read_repetition(config, config.selected_endpoints(), 1)
        assert result["sql"]["status_counts"] == {"200": 5}

    def test_repetitions_use_different_request_orders(self, calls):
        recorded, _ = calls
        config = cfg(requests_per_endpoint=32)
        http_worker.run_read_repetition(config, config.selected_endpoints(), 1)
        first = list(recorded)
        recorded.clear()
        http_worker.run_read_repetition(config, config.selected_endpoints(), 2)
        assert sorted(first) == sorted(recorded)  # same pool
        assert first != recorded                  # different order


class TestCloneIdempotency:
    def test_target_is_deleted_before_and_after(self, calls):
        before, after = [], []
        config = cfg(include_writes=True, clone_source_gt="src", clone_target_gt="tgt")
        result = http_worker.run_write_benchmark(
            config, repetition=3,
            before_clone=before.append,
            after_clone=lambda name: (after.append(name), True)[1])
        clone = result["clone_global_tag"]
        assert clone["target_gt"] == "tgt__bench_r3"
        assert before == ["tgt__bench_r3"] and after == ["tgt__bench_r3"]
        assert clone["cleaned_up"] is True
        assert "do not grow the dataset" in clone["note"]

    def test_each_repetition_uses_a_distinct_target(self, calls):
        config = cfg(include_writes=True, clone_source_gt="src", clone_target_gt="tgt")
        names = {
            http_worker.run_write_benchmark(config, rep, before_clone=lambda n: None,
                                            after_clone=lambda n: True
                                            )["clone_global_tag"]["target_gt"]
            for rep in (1, 2, 3)
        }
        assert len(names) == 3

    def test_keep_artifacts_skips_cleanup_and_says_so(self, calls):
        after = []
        config = cfg(include_writes=True, clone_source_gt="src", clone_target_gt="tgt",
                     keep_clone_artifacts=True)
        result = http_worker.run_write_benchmark(
            config, 1, before_clone=lambda n: None, after_clone=lambda n: after.append(n))
        assert after == []
        assert result["clone_global_tag"]["cleaned_up"] is False
        assert "RETAINED" in result["clone_global_tag"]["note"]

    def test_failed_cleanup_is_reported_honestly(self, calls):
        config = cfg(include_writes=True, clone_source_gt="src", clone_target_gt="tgt")
        result = http_worker.run_write_benchmark(
            config, 1, before_clone=lambda n: None, after_clone=lambda n: False)
        assert result["clone_global_tag"]["cleaned_up"] is False
        assert "grows" in result["clone_global_tag"]["note"]

    def test_writes_are_off_by_default(self, calls):
        recorded, _ = calls
        assert http_worker.run_write_benchmark(cfg(), 1) == {}
        assert recorded == []
