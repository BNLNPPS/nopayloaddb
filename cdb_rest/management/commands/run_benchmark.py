"""Phase 6 benchmarking harness.

    python manage.py run_benchmark --label baseline --workload-profile cold
    # approve one suggestion via /ai/suggestions/<id>/
    python manage.py run_benchmark --label after --compare-to <baseline>.json --suggestion-id 7

VERIFIED requires both a latency gain beyond the noise floor and the predicted
mechanism. A missing required endpoint aborts rather than shrinking coverage
silently, and a baseline from a different database state is flagged.
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bench import db_metrics, experiment, report as report_mod, reversibility as rev
from bench.config import (
    BenchConfig,
    DEFAULT_REQUIRED_ENDPOINTS,
    READ_ENDPOINTS,
    WorkloadConfig,
    WorkloadProfile,
)
from bench.http_worker import EndpointUnavailable
from cdb_rest.query_optimization import storage

logger = logging.getLogger(__name__)


def _csv(value):
    return tuple(v.strip() for v in value.split(",") if v.strip())


def _range(value, name):
    try:
        lo, hi = value.split(":")
        return int(lo), int(hi)
    except ValueError:
        raise CommandError(f"--{name} must look like LO:HI, got {value!r}")


class Command(BaseCommand):
    help = "Run the Phase 6 benchmarking harness against a live nopayloaddb deployment"

    def add_arguments(self, parser):
        target = parser.add_argument_group("target")
        target.add_argument("--base-url", default="http://localhost:8000")
        target.add_argument("--auth-token", default="")
        target.add_argument("--request-timeout", type=float, default=10.0)
        target.add_argument("--db-alias", default=settings.CDB_AI_OPTIMIZER_DB_ALIAS)

        load = parser.add_argument_group("load shape")
        load.add_argument("--concurrency", type=int, default=50)
        load.add_argument("--requests-per-endpoint", type=int, default=200)
        load.add_argument(
            "--repetitions", type=int, default=5,
            help="Independent measurements of this condition. Fewer than 2 leaves no "
                 "noise floor, and the verdict logic will refuse to call any difference real.")
        load.add_argument(
            "--warmup-requests", type=int, default=None,
            help="Unrecorded requests per endpoint before each repetition "
                 "(default: 20%% of --requests-per-endpoint, minimum 20). "
                 "Set 0 to disable, accepting cold-cache bias.")

        wl = parser.add_argument_group("workload")
        wl.add_argument("--workload-profile", default=WorkloadProfile.COLD,
                        choices=list(WorkloadProfile.ALL),
                        help="cold = sweep a wide GT/IOV pool (default; the only profile under "
                             "which R5/R7 can be judged). hot = replay a tiny pool. "
                             "mixed = both.")
        wl.add_argument("--gt-names", default="", help="Comma-separated; overrides discovery.")
        wl.add_argument("--major-iov-range", default="", help="LO:HI; overrides discovery.")
        wl.add_argument("--minor-iov-range", default="", help="LO:HI; overrides discovery.")
        wl.add_argument("--pool-size", type=int, default=64)
        wl.add_argument("--hot-pool-size", type=int, default=1)
        wl.add_argument("--mixed-hot-fraction", type=float, default=0.8)
        wl.add_argument("--seed", type=int, default=20260821,
                        help="Same seed + same config => same logical request sequence.")
        wl.add_argument("--no-discover-pool", action="store_true",
                        help="Skip deriving the GT/IOV pool from live data.")

        cov = parser.add_argument_group("coverage")
        cov.add_argument("--endpoints", default=",".join(e.name for e in READ_ENDPOINTS))
        cov.add_argument("--require-endpoints", default=",".join(DEFAULT_REQUIRED_ENDPOINTS),
                         help="Abort if any of these do not resolve.")
        cov.add_argument("--require-complete-coverage", action="store_true",
                         help="Abort if ANY requested endpoint is unavailable.")

        writes = parser.add_argument_group("writes (off by default -- these mutate data)")
        writes.add_argument("--include-writes", action="store_true")
        writes.add_argument("--bulk-payload-list-id", type=int, default=0)
        writes.add_argument("--clone-source-gt", default="")
        writes.add_argument("--clone-target-gt", default="")
        writes.add_argument("--write-requests", type=int, default=10)
        writes.add_argument("--keep-clone-artifacts", action="store_true",
                            help="Do NOT delete cloned GlobalTags afterwards. Off by default: "
                                 "retaining them grows the dataset every run, making database "
                                 "size a hidden variable between repetitions.")

        exp = parser.add_argument_group("experiment")
        exp.add_argument("--label", default="run")
        exp.add_argument("--output-dir", default="bench/results")
        exp.add_argument("--compare-to", default="", help="Path to a baseline report JSON.")
        exp.add_argument("--suggestion-id", type=int, default=None,
                         help="Write the verdict back onto this suggestion.")
        exp.add_argument("--rule-id", default="",
                         help="Rule whose postcondition to check. Inferred from --suggestion-id.")
        exp.add_argument("--target-relation", default="PayloadIOV")
        exp.add_argument("--experiment-mode", default="cumulative",
                         choices=["cumulative", "independent"],
                         help="cumulative = suggestions stacked in order (results are MARGINAL "
                              "effects in that order). independent = this suggestion alone "
                              "against a clean baseline.")
        exp.add_argument("--applied-suggestions", default="",
                         help="Comma-separated ids already applied, oldest first. Recorded so a "
                              "cumulative result is never mistaken for an independent one.")
        exp.add_argument("--no-persist", action="store_true",
                         help="Do not write the run into ai_optimizer.benchmark_runs.")

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        db_alias = options["db_alias"]
        storage.ensure_schema(db_alias)

        workload = self._build_workload(options, db_alias)
        config = self._build_config(options, workload, db_alias)

        self._announce(config, workload)

        try:
            report = experiment.run_condition(config, stdout=self.stdout)
        except EndpointUnavailable as exc:
            raise CommandError(str(exc))

        if options["require_complete_coverage"] and not report["coverage"]["complete"]:
            raise CommandError(
                f"Incomplete endpoint coverage: {sorted(report['coverage']['skipped'])} "
                "unavailable and --require-complete-coverage was set."
            )

        path = report_mod.save_report(report, config.output_dir, config.label)
        self.stdout.write(self.style.SUCCESS(f"\nReport written to {path}"))

        run_id = None
        if not options["no_persist"]:
            run_id = storage.record_benchmark_run(db_alias, report)
            self.stdout.write(f"Recorded as ai_optimizer.benchmark_runs id={run_id}")

        self._print_condition_summary(report)

        if not options["compare_to"]:
            self.stdout.write(
                "\nNo --compare-to given: this is a standalone condition measurement. "
                "No verdict is produced, because a verdict requires a baseline."
            )
            return

        self._compare(options, config, report, run_id, db_alias)

    # ------------------------------------------------------------------

    def _build_workload(self, options, db_alias) -> WorkloadConfig:
        kwargs = {
            "profile": options["workload_profile"],
            "pool_size": options["pool_size"],
            "hot_pool_size": options["hot_pool_size"],
            "mixed_hot_fraction": options["mixed_hot_fraction"],
            "seed": options["seed"],
        }

        discovered = {}
        if not options["no_discover_pool"]:
            discovered = db_metrics.discover_workload_bounds(db_alias)
            if discovered:
                self.stdout.write(
                    f"Discovered workload pool from live data: "
                    f"{len(discovered.get('gt_names', ()))} GT(s), "
                    f"major_iov {discovered.get('major_iov_min')}..{discovered.get('major_iov_max')}, "
                    f"minor_iov {discovered.get('minor_iov_min')}..{discovered.get('minor_iov_max')}"
                )
            else:
                self.stdout.write(self.style.WARNING(
                    "Workload discovery found no PayloadIOV data; falling back to configured "
                    "ranges. A cold profile over an empty range does not exercise real rows."
                ))
        kwargs.update(discovered)

        if options["gt_names"]:
            kwargs["gt_names"] = _csv(options["gt_names"])
        if options["major_iov_range"]:
            lo, hi = _range(options["major_iov_range"], "major-iov-range")
            kwargs["major_iov_min"], kwargs["major_iov_max"] = lo, hi
        if options["minor_iov_range"]:
            lo, hi = _range(options["minor_iov_range"], "minor-iov-range")
            kwargs["minor_iov_min"], kwargs["minor_iov_max"] = lo, hi

        kwargs.setdefault("gt_names", ("generic_gt",))

        try:
            return WorkloadConfig(**kwargs)
        except ValueError as exc:
            raise CommandError(f"invalid workload configuration: {exc}")

    def _build_config(self, options, workload, db_alias) -> BenchConfig:
        applied = tuple(int(s) for s in _csv(options["applied_suggestions"]))
        if options["suggestion_id"] and options["suggestion_id"] not in applied:
            applied = applied + (options["suggestion_id"],)

        try:
            config = BenchConfig(
                base_url=options["base_url"],
                concurrency=options["concurrency"],
                requests_per_endpoint=options["requests_per_endpoint"],
                warmup_requests=options["warmup_requests"],
                repetitions=options["repetitions"],
                request_timeout_s=options["request_timeout"],
                auth_token=options["auth_token"],
                workload=workload,
                endpoint_names=_csv(options["endpoints"]),
                required_endpoints=_csv(options["require_endpoints"]),
                include_writes=options["include_writes"],
                bulk_payload_list_id=options["bulk_payload_list_id"],
                clone_source_gt=options["clone_source_gt"],
                clone_target_gt=options["clone_target_gt"],
                keep_clone_artifacts=options["keep_clone_artifacts"],
                write_requests=options["write_requests"],
                label=options["label"],
                db_alias=db_alias,
                output_dir=options["output_dir"],
                experiment_mode=options["experiment_mode"],
                applied_suggestions=applied,
            )
            config.selected_endpoints()
        except ValueError as exc:
            raise CommandError(str(exc))
        return config

    def _announce(self, config, workload):
        self.stdout.write(
            f"Condition '{config.label}': {config.repetitions} repetition(s) x "
            f"{config.requests_per_endpoint} requests/endpoint at {config.concurrency} "
            f"concurrent clients, {config.resolve_warmup()} unrecorded warmup requests before each."
        )
        self.stdout.write(f"Workload: {workload.profile} profile, seed {workload.seed}.")
        if config.repetitions < 2:
            self.stdout.write(self.style.WARNING(
                "WARNING: fewer than 2 repetitions. There will be no noise floor, so no "
                "difference measured against this run can be called real."
            ))
        reason = workload.cacheability_reason()
        if reason:
            self.stdout.write(self.style.WARNING(
                f"WARNING: workload is effectively single-tuple -- {reason}"
            ))
        if config.resolve_warmup() == 0:
            self.stdout.write(self.style.WARNING(
                "WARNING: warmup disabled. A cold condition compared against a warm one is "
                "biased toward whichever ran second."
            ))

    def _print_condition_summary(self, report):
        self.stdout.write("\nPer-endpoint latency across repetitions:")
        for name, agg in (report.get("latency") or {}).items():
            metrics = agg.get("metrics") or {}
            p50, p95 = metrics.get("p50_ms") or {}, metrics.get("p95_ms") or {}
            if not p95.get("values"):
                self.stdout.write(f"  {name}: no successful requests")
                continue
            self.stdout.write(
                f"  {name:12s} p50 {_f(p50.get('mean'))} (sd {_f(p50.get('stdev'))})  "
                f"p95 {_f(p95.get('mean'))} (sd {_f(p95.get('stdev'))}, "
                f"{_f(p95.get('min'))}..{_f(p95.get('max'))})  "
                f"n={agg.get('repetitions')} reps, errors={agg.get('errors')}"
            )

        db = report.get("db") or {}
        ratio = db.get("windowed_hit_ratio")
        self.stdout.write(
            f"\nWindowed buffer hit ratio: "
            f"{f'{ratio * 100:.2f}%' if ratio is not None else 'n/a -- ' + str(db.get('reason'))}"
        )
        if not db.get("pg_stat_statements_available"):
            self.stdout.write(self.style.WARNING(
                "pg_stat_statements unavailable: no windowed per-fingerprint execution times."
            ))

    def _compare(self, options, config, report, run_id, db_alias):
        try:
            baseline = report_mod.validate_condition_report(
                report_mod.load_report(options["compare_to"]), options["compare_to"])
        except report_mod.NotAConditionReport as exc:
            raise CommandError(str(exc))
        except (OSError, ValueError) as exc:
            raise CommandError(f"could not read --compare-to {options['compare_to']}: {exc}")

        rule_id = options["rule_id"] or None
        suggestion = None
        if options["suggestion_id"]:
            suggestion = storage.get_suggestion(db_alias, options["suggestion_id"])
            if suggestion is None:
                raise CommandError(f"suggestion {options['suggestion_id']} not found")
            rule_id = rule_id or suggestion["rule_id"]

        reversibility = rev.classify(suggestion["safe_sql"]) if suggestion else None
        if suggestion:
            self.stdout.write(f"\nReversibility: {rev.baseline_advice(suggestion['safe_sql'])}")

        state_comparison = db_metrics.compare_db_state(
            baseline.get("db_state"), report.get("db_state")
        )

        comparison = report_mod.compare_conditions(
            baseline, report,
            rule_id=rule_id,
            primary_endpoint=(config.required_endpoints[0] if config.required_endpoints else "sql"),
            target_relation=options["target_relation"],
            db_state_comparison=state_comparison,
            reversibility=reversibility,
        )

        self.stdout.write("\n" + "=" * 78)
        self.stdout.write(report_mod.render_text(comparison))
        self.stdout.write("=" * 78)

        comparison_path = report_mod.save_report(
            comparison, config.output_dir, f"{config.label}_vs_baseline"
        )
        self.stdout.write(f"\nComparison written to {comparison_path}")

        if not suggestion:
            self.stdout.write(
                "No --suggestion-id given, so this verdict was not written back to any "
                "suggestion. The feedback loop stays open until it is."
            )
            return

        baseline_run_id, _ = storage.latest_benchmark_run(db_alias, baseline.get("label"))
        storage.mark_benchmarked(db_alias, suggestion["id"])
        evaluation_id, new_status = storage.record_suggestion_evaluation(
            db_alias, suggestion["id"], comparison,
            baseline_run_id=baseline_run_id, optimized_run_id=run_id,
        )
        self.stdout.write(self.style.SUCCESS(
            f"\nSuggestion {suggestion['id']} ({suggestion['rule_id']}) -> status "
            f"'{new_status}', evaluation id {evaluation_id}."
        ))
        self.stdout.write(
            f"  a priori rule confidence : {suggestion['confidence']}  (unchanged)\n"
            f"  empirical verdict        : {comparison['verdict']['status']}"
        )


def _f(value):
    return f"{value:.1f}ms" if isinstance(value, (int, float)) else "n/a"
