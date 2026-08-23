"""Concurrent HTTP load generation with unrecorded warmup and seeded parameters,
so no condition is measured from a cold cache. Django-free for testability."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from .config import BenchConfig
from .workload import request_sequence

logger = logging.getLogger(__name__)


def _timed_get(session, url, headers, timeout):
    start = time.perf_counter()
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        return (time.perf_counter() - start) * 1000, resp.status_code, None
    except requests.RequestException as exc:
        return (time.perf_counter() - start) * 1000, None, str(exc)


def _url_for(config: BenchConfig, endpoint, point) -> str:
    return config.base_url + endpoint.path.format(
        gt_name=point.gt_name, major_iov=point.major_iov, minor_iov=point.minor_iov
    )


class EndpointUnavailable(RuntimeError):
    """A required endpoint did not resolve; raised so coverage is never overstated."""


def probe_endpoints(config: BenchConfig) -> dict:
    """Probe every selected endpoint. Raises EndpointUnavailable if a required one
    is missing, so a commented-out route is an error rather than a silent omission."""
    probe_point = request_sequence(config.workload, 1, stream="probe")[0]
    reachable, skipped = [], {}

    with requests.Session() as session:
        for endpoint in config.selected_endpoints():
            url = _url_for(config, endpoint, probe_point)
            _, status_code, error = _timed_get(
                session, url, config.auth_headers(), config.request_timeout_s
            )
            if error is not None:
                skipped[endpoint.name] = f"unreachable: {error}"
            elif status_code == 404:
                skipped[endpoint.name] = (
                    "404 -- URL route not wired up in cdb_rest/urls.py"
                )
            elif status_code is not None and status_code >= 500:
                skipped[endpoint.name] = f"server error {status_code}"
            else:
                reachable.append(endpoint)

    missing_required = [n for n in config.required_endpoints if n in skipped]
    if missing_required:
        detail = "; ".join(f"{n}: {skipped[n]}" for n in missing_required)
        raise EndpointUnavailable(
            f"Required endpoint(s) unavailable: {detail}. "
            "Either wire up the route or drop it from --require-endpoints; "
            "the benchmark will not report coverage it does not have."
        )

    for name, reason in skipped.items():
        logger.warning("endpoint %s skipped (%s)", name, reason)

    return {"reachable": reachable, "skipped": skipped}


def warmup(config: BenchConfig, endpoints: list, repetition: int) -> int:
    """Unrecorded requests to bring caches to steady state. Results are discarded."""
    count = config.resolve_warmup()
    if count <= 0:
        return 0

    headers = config.auth_headers()
    issued = 0
    with requests.Session() as session:
        for endpoint in endpoints:
            points = request_sequence(
                config.workload, count, stream=f"warmup:{repetition}:{endpoint.name}"
            )
            with ThreadPoolExecutor(max_workers=config.concurrency) as pool:
                list(pool.map(
                    lambda p: _timed_get(
                        session, _url_for(config, endpoint, p), headers, config.request_timeout_s
                    ),
                    points,
                ))
            issued += len(points)
    return issued


def run_read_repetition(config: BenchConfig, endpoints: list, repetition: int) -> dict:
    """One recorded repetition. Submission order is reproducible for a given seed."""
    results = {}
    headers = config.auth_headers()

    with requests.Session() as session:
        for endpoint in endpoints:
            points = request_sequence(
                config.workload,
                config.requests_per_endpoint,
                stream=f"recorded:{repetition}:{endpoint.name}",
            )
            latencies, errors, status_counts = [], 0, {}

            with ThreadPoolExecutor(max_workers=config.concurrency) as pool:
                outcomes = list(pool.map(
                    lambda p: _timed_get(
                        session, _url_for(config, endpoint, p), headers, config.request_timeout_s
                    ),
                    points,
                ))

            for elapsed_ms, status_code, error in outcomes:
                key = str(status_code) if status_code is not None else "exception"
                status_counts[key] = status_counts.get(key, 0) + 1
                if error is not None or (status_code is not None and status_code >= 400):
                    # Excluded from the distribution: a fast 500 must not look like a win.
                    errors += 1
                    continue
                latencies.append(elapsed_ms)

            results[endpoint.name] = {
                "latencies_ms": latencies,
                "errors": errors,
                "requests_issued": len(points),
                "distinct_parameters": len(set(points)),
                "status_counts": status_counts,
            }

    return results


def run_write_benchmark(config: BenchConfig, repetition: int,
                        before_clone=None, after_clone=None) -> dict:
    """Off-by-default write load. The clone callbacks make it idempotent by deleting
    the target before and after, so repeated runs do not grow the dataset."""
    results = {}
    headers = {**config.auth_headers(), "Content-Type": "application/json"}

    with requests.Session() as session:
        if config.bulk_payload_list_id:
            results["bulk_piov"] = _run_bulk(config, session, headers)

        if config.clone_source_gt and config.clone_target_gt:
            results["clone_global_tag"] = _run_clone(
                config, session, headers, repetition, before_clone, after_clone
            )

    return results


def _run_bulk(config, session, headers) -> dict:
    url = config.base_url + "/api/cdb_rest/bulk_piov"
    latencies, errors = [], 0
    for _ in range(config.write_requests):
        start = time.perf_counter()
        try:
            resp = session.post(
                url,
                json={"payload_list": config.bulk_payload_list_id, "payload_iovs": []},
                headers=headers,
                timeout=config.request_timeout_s,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            if resp.status_code >= 400:
                errors += 1
                continue
        except requests.RequestException:
            errors += 1
            continue
        latencies.append(elapsed_ms)
    return {"latencies_ms": latencies, "errors": errors,
            "requests_issued": config.write_requests,
            "note": "empty payload_iovs list -- measures request/transaction overhead, "
                    "not bulk insert throughput"}


def _run_clone(config, session, headers, repetition, before_clone, after_clone) -> dict:
    # Unique per repetition so a leftover target cannot make the next one a no-op.
    target = f"{config.clone_target_gt}__bench_r{repetition}"
    if before_clone:
        before_clone(target)

    url = config.base_url + f"/api/cdb_rest/cloneGlobalTag/{config.clone_source_gt}/{target}"
    start = time.perf_counter()
    errors = 0
    try:
        resp = session.post(url, headers=headers, timeout=config.request_timeout_s)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code >= 400:
            errors = 1
    except requests.RequestException:
        elapsed_ms = (time.perf_counter() - start) * 1000
        errors = 1

    cleaned = False
    if after_clone and not config.keep_clone_artifacts:
        cleaned = bool(after_clone(target))

    return {
        "latencies_ms": [] if errors else [elapsed_ms],
        "errors": errors,
        "requests_issued": 1,
        "target_gt": target,
        "cleaned_up": cleaned,
        "note": "clone target is deleted after each repetition so repeated runs do not "
                "grow the dataset" if cleaned else
                "clone target RETAINED -- dataset size grows with every repetition",
    }
