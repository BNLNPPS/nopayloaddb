"""Concurrent HTTP load generation for the benchmark harness."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import BenchConfig, READ_ENDPOINTS

logger = logging.getLogger(__name__)


def _timed_get(session: requests.Session, url: str, headers: dict, timeout: float):
    start = time.perf_counter()
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, resp.status_code, None
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, None, str(exc)


def probe_reachable(config: BenchConfig) -> list:
    """Return the subset of READ_ENDPOINTS that don't 404 -- see module
    docstring in config.py for why this check exists."""
    reachable = []
    with requests.Session() as session:
        for endpoint in READ_ENDPOINTS:
            url = config.base_url + endpoint.path.format(
                gt_name=config.gt_name, major_iov=config.major_iov, minor_iov=config.minor_iov
            )
            _, status_code, error = _timed_get(session, url, config.auth_headers(), config.request_timeout_s)
            if error is not None:
                logger.warning("endpoint %s unreachable (%s); skipping", endpoint.name, error)
                continue
            if status_code == 404:
                logger.warning(
                    "endpoint %s returned 404 -- its URL route is likely not wired up "
                    "in cdb_rest/urls.py; skipping",
                    endpoint.name,
                )
                continue
            reachable.append(endpoint)
    return reachable


def run_read_benchmark(config: BenchConfig, endpoints: list) -> dict:
    """Fire config.requests_per_endpoint requests at each endpoint using
    config.concurrency worker threads. Returns {endpoint_name: [latency_ms, ...]}."""
    results = {}
    headers = config.auth_headers()

    with requests.Session() as session:
        for endpoint in endpoints:
            url = config.base_url + endpoint.path.format(
                gt_name=config.gt_name, major_iov=config.major_iov, minor_iov=config.minor_iov
            )
            latencies = []
            errors = 0

            with ThreadPoolExecutor(max_workers=config.concurrency) as pool:
                futures = [
                    pool.submit(_timed_get, session, url, headers, config.request_timeout_s)
                    for _ in range(config.requests_per_endpoint)
                ]
                for future in as_completed(futures):
                    elapsed_ms, status_code, error = future.result()
                    if error is not None or (status_code is not None and status_code >= 400):
                        errors += 1
                    latencies.append(elapsed_ms)

            results[endpoint.name] = {"latencies_ms": latencies, "errors": errors}

    return results


def run_write_benchmark(config: BenchConfig) -> dict:
    """Optional, off-by-default: bulk PayloadIOV creation + GlobalTag clone
    load. These mutate real data, so they only run when the operator passes
    --include-writes explicitly."""
    results = {}
    headers = {**config.auth_headers(), "Content-Type": "application/json"}

    with requests.Session() as session:
        if config.bulk_payload_list_id:
            url = config.base_url + "/api/cdb_rest/bulk_piov"
            latencies = []
            errors = 0
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
                except requests.RequestException:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    errors += 1
                latencies.append(elapsed_ms)
            results["bulk_piov"] = {"latencies_ms": latencies, "errors": errors}

        if config.clone_source_gt and config.clone_target_gt:
            url = config.base_url + f"/api/cdb_rest/cloneGlobalTag/{config.clone_source_gt}/{config.clone_target_gt}"
            start = time.perf_counter()
            try:
                resp = session.post(url, headers=headers, timeout=config.request_timeout_s)
                elapsed_ms = (time.perf_counter() - start) * 1000
                errors = 1 if resp.status_code >= 400 else 0
            except requests.RequestException:
                elapsed_ms = (time.perf_counter() - start) * 1000
                errors = 1
            results["clone_global_tag"] = {"latencies_ms": [elapsed_ms], "errors": errors}

    return results
