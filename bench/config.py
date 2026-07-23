"""Benchmark scenario configuration (proposal Phase 6).

Endpoint list intentionally checks reachability before load-testing: the
two ORM comparison endpoints (payloadiovs_orm_orderby, payloadiovs_orm_max)
have view classes in cdb_rest/views.py but their URL routes are currently
commented out in cdb_rest/urls.py. Rather than silently reporting all-error
results for routes that were never wired up, the harness probes each
endpoint first and skips (with a clear warning) any that 404.
"""

from dataclasses import dataclass, field


@dataclass
class ReadEndpoint:
    name: str
    path: str  # relative to base_url, may contain {gt_name}/{major_iov}/{minor_iov}


READ_ENDPOINTS = [
    ReadEndpoint("sql", "/api/cdb_rest/payloadiovs/?gtName={gt_name}&majorIOV={major_iov}&minorIOV={minor_iov}"),
    ReadEndpoint("orm_orderby", "/api/cdb_rest/payloadiovs_orm_orderby/?gtName={gt_name}&majorIOV={major_iov}&minorIOV={minor_iov}"),
    ReadEndpoint("orm_max", "/api/cdb_rest/payloadiovs_orm_max/?gtName={gt_name}&majorIOV={major_iov}&minorIOV={minor_iov}"),
]


@dataclass
class BenchConfig:
    base_url: str = "http://localhost:8000"
    gt_name: str = "generic_gt"
    major_iov: int = 0
    minor_iov: int = 999999
    concurrency: int = 50
    requests_per_endpoint: int = 200
    request_timeout_s: float = 10.0
    auth_token: str = ""

    include_writes: bool = False
    bulk_payload_list_id: int = 0
    clone_source_gt: str = ""
    clone_target_gt: str = ""
    write_requests: int = 10

    label: str = "run"
    db_alias: str = ""  # resolved to settings.CDB_AI_OPTIMIZER_DB_ALIAS if unset
    output_dir: str = "bench/results"

    def auth_headers(self) -> dict:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}
