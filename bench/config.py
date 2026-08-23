"""Benchmark scenario configuration: endpoints, workload pool, warmup and repetitions."""

from dataclasses import dataclass, field, replace
from typing import Optional


# --- Endpoints ---


@dataclass(frozen=True)
class ReadEndpoint:
    name: str
    # relative to base_url; may contain {gt_name}/{major_iov}/{minor_iov}
    path: str
    description: str = ""


READ_ENDPOINTS = (
    ReadEndpoint(
        "sql",
        "/api/cdb_rest/payloadiovs/?gtName={gt_name}&majorIOV={major_iov}&minorIOV={minor_iov}",
        "Raw SQL LATERAL JOIN + comb_iov decimal range",
    ),
    ReadEndpoint(
        "orm_orderby",
        "/api/cdb_rest/payloadiovs_orm_orderby/?gtName={gt_name}&majorIOV={major_iov}&minorIOV={minor_iov}",
        "ORM DISTINCT ON (payload_list_id) ORDER BY -comb_iov",
    ),
    ReadEndpoint(
        "orm_max",
        "/api/cdb_rest/payloadiovs_orm_max/?gtName={gt_name}&majorIOV={major_iov}&minorIOV={minor_iov}",
        "ORM Max('comb_iov') + dynamic Q (N+1 pattern)",
    ),
)

ENDPOINTS_BY_NAME = {e.name: e for e in READ_ENDPOINTS}

DEFAULT_REQUIRED_ENDPOINTS = ("sql",)


# --- Workload ---


class WorkloadProfile:
    """How request parameters are drawn from the pool."""

    HOT = "hot"
    COLD = "cold"
    MIXED = "mixed"

    ALL = (HOT, COLD, MIXED)


@dataclass(frozen=True)
class IOVPoint:
    gt_name: str
    major_iov: int
    minor_iov: int

    def as_dict(self) -> dict:
        return {
            "gt_name": self.gt_name,
            "major_iov": self.major_iov,
            "minor_iov": self.minor_iov,
        }


@dataclass
class WorkloadConfig:
    """Parameter pool. hot = tiny pool, cold = wide sweep, mixed = both; seed makes it reproducible."""

    profile: str = WorkloadProfile.HOT
    gt_names: tuple = ("generic_gt",)
    major_iov_min: int = 0
    major_iov_max: int = 0
    minor_iov_min: int = 999999
    minor_iov_max: int = 999999
    pool_size: int = 64
    hot_pool_size: int = 1
    mixed_hot_fraction: float = 0.8  # share drawn from the hot subset when profile == mixed
    seed: int = 20260821

    def __post_init__(self):
        if self.profile not in WorkloadProfile.ALL:
            raise ValueError(
                f"workload profile must be one of {WorkloadProfile.ALL}, got {self.profile!r}"
            )
        if not self.gt_names:
            raise ValueError("workload needs at least one GlobalTag name")
        if self.major_iov_min > self.major_iov_max:
            raise ValueError("major_iov_min must be <= major_iov_max")
        if self.minor_iov_min > self.minor_iov_max:
            raise ValueError("minor_iov_min must be <= minor_iov_max")
        if self.pool_size < 1 or self.hot_pool_size < 1:
            raise ValueError("pool sizes must be >= 1")
        if not 0.0 <= self.mixed_hot_fraction <= 1.0:
            raise ValueError("mixed_hot_fraction must be in [0, 1]")

    def describe(self) -> dict:
        """Everything needed to reproduce this workload."""
        return {
            "profile": self.profile,
            "gt_names": list(self.gt_names),
            "major_iov_range": [self.major_iov_min, self.major_iov_max],
            "minor_iov_range": [self.minor_iov_min, self.minor_iov_max],
            "pool_size": self.pool_size,
            "hot_pool_size": self.hot_pool_size,
            "mixed_hot_fraction": self.mixed_hot_fraction,
            "seed": self.seed,
        }

    @property
    def distinct_parameter_space(self) -> int:
        """Distinct tuples the ranges can produce; may be far smaller than pool_size."""
        return (
            len(self.gt_names)
            * (self.major_iov_max - self.major_iov_min + 1)
            * (self.minor_iov_max - self.minor_iov_min + 1)
        )

    @property
    def is_artificially_cacheable(self) -> bool:
        """True when the pool is too small to judge cache-sensitive rules (R5, R7, R8)."""
        effective = min(
            self.distinct_parameter_space,
            self.hot_pool_size if self.profile == WorkloadProfile.HOT else self.pool_size,
        )
        return self.profile == WorkloadProfile.HOT or effective <= 4

    def cacheability_reason(self) -> Optional[str]:
        """Why the workload is unfit for cache-sensitive rules, if it is."""
        if not self.is_artificially_cacheable:
            return None
        if self.profile == WorkloadProfile.HOT:
            return ("workload profile is 'hot', which replays a tiny pool by design. "
                    "Use --workload-profile cold to judge R5/R7/R8.")
        return (
            f"profile is '{self.profile}', but the data only supports "
            f"{self.distinct_parameter_space} distinct (gt, major_iov, minor_iov) "
            "combination(s), so every request hits the same rows. Seed more "
            "PayloadIOV data across more GTs/IOVs before judging R5/R7/R8."
        )


# --- Top-level benchmark config ---


@dataclass
class BenchConfig:
    base_url: str = "http://localhost:8000"

    concurrency: int = 50
    requests_per_endpoint: int = 200
    warmup_requests: Optional[int] = None  # None => 20% of requests_per_endpoint, floor 20
    repetitions: int = 5
    request_timeout_s: float = 10.0
    auth_token: str = ""

    workload: WorkloadConfig = field(default_factory=WorkloadConfig)

    endpoint_names: tuple = tuple(e.name for e in READ_ENDPOINTS)
    required_endpoints: tuple = DEFAULT_REQUIRED_ENDPOINTS

    include_writes: bool = False
    bulk_payload_list_id: int = 0
    clone_source_gt: str = ""
    # Deleted after each repetition so repeated runs do not grow the dataset.
    clone_target_gt: str = ""
    keep_clone_artifacts: bool = False
    write_requests: int = 10

    label: str = "run"
    db_alias: str = ""
    output_dir: str = "bench/results"

    experiment_mode: str = "cumulative"  # or "independent"
    applied_suggestions: tuple = ()

    def auth_headers(self) -> dict:
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    def resolve_warmup(self) -> int:
        if self.warmup_requests is not None:
            return max(0, int(self.warmup_requests))
        return max(20, self.requests_per_endpoint // 5)

    def selected_endpoints(self) -> list:
        missing = [n for n in self.endpoint_names if n not in ENDPOINTS_BY_NAME]
        if missing:
            raise ValueError(f"unknown endpoint name(s): {missing}")
        return [ENDPOINTS_BY_NAME[n] for n in self.endpoint_names]

    def with_label(self, label: str) -> "BenchConfig":
        return replace(self, label=label)

    def describe(self) -> dict:
        return {
            "base_url": self.base_url,
            "concurrency": self.concurrency,
            "requests_per_endpoint": self.requests_per_endpoint,
            "warmup_requests": self.resolve_warmup(),
            "repetitions": self.repetitions,
            "endpoints_requested": list(self.endpoint_names),
            "required_endpoints": list(self.required_endpoints),
            "include_writes": self.include_writes,
            "keep_clone_artifacts": self.keep_clone_artifacts,
            "experiment_mode": self.experiment_mode,
            "applied_suggestions": list(self.applied_suggestions),
        }
