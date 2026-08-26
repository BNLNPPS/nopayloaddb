"""Phase 6 benchmarking harness entry point.

Typical workflow for verifying one AI-generated suggestion actually helped:

    python manage.py run_benchmark --label baseline
    # ... approve exactly one suggestion via /ai/suggestions/<id>/ ...
    python manage.py run_benchmark --label after-r7 --compare-to bench/results/<baseline file>.json

The comparison printed at the end is the real answer to "is this query more
optimized than before" -- not the rule engine's static confidence score.
"""

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.core.management.base import BaseCommand

from bench.config import BenchConfig, READ_ENDPOINTS
from bench.db_metrics import capture_buffer_hit_ratio, fingerprint_stats
from bench.http_worker import probe_reachable, run_read_benchmark, run_write_benchmark
from bench.latency_stats import summarize
from bench.report import diff_reports, load_report, save_report
from cdb_rest.query_optimization import storage

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Phase 6 benchmarking harness against a live nopayloaddb deployment"

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://localhost:8000")
        parser.add_argument("--gt-name", default="generic_gt")
        parser.add_argument("--major-iov", type=int, default=0)
        parser.add_argument("--minor-iov", type=int, default=999999)
        parser.add_argument("--concurrency", type=int, default=50)
        parser.add_argument("--requests-per-endpoint", type=int, default=200)
        parser.add_argument("--request-timeout", type=float, default=10.0)
        parser.add_argument("--auth-token", default="")

        parser.add_argument("--include-writes", action="store_true")
        parser.add_argument("--bulk-payload-list-id", type=int, default=0)
        parser.add_argument("--clone-source-gt", default="")
        parser.add_argument("--clone-target-gt", default="")
        parser.add_argument("--write-requests", type=int, default=10)

        parser.add_argument("--label", default="run")
        parser.add_argument("--db-alias", default=settings.CDB_AI_OPTIMIZER_DB_ALIAS)
        parser.add_argument("--output-dir", default="bench/results")
        parser.add_argument("--compare-to", default="")

    def handle(self, *args, **options):
        config = BenchConfig(
            base_url=options["base_url"],
            gt_name=options["gt_name"],
            major_iov=options["major_iov"],
            minor_iov=options["minor_iov"],
            concurrency=options["concurrency"],
            requests_per_endpoint=options["requests_per_endpoint"],
            request_timeout_s=options["request_timeout"],
            auth_token=options["auth_token"],
            include_writes=options["include_writes"],
            bulk_payload_list_id=options["bulk_payload_list_id"],
            clone_source_gt=options["clone_source_gt"],
            clone_target_gt=options["clone_target_gt"],
            write_requests=options["write_requests"],
            label=options["label"],
            db_alias=options["db_alias"],
            output_dir=options["output_dir"],
        )

        storage.ensure_schema(config.db_alias)

        started_at = datetime.now(timezone.utc)
        buffer_hit_ratio_start = capture_buffer_hit_ratio(config.db_alias)

        reachable = probe_reachable(config)
        if not reachable:
            self.stderr.write(self.style.ERROR(
                "No read endpoints reachable -- is the server running at "
                f"{config.base_url}? Aborting."
            ))
            return
        skipped = {e.name for e in READ_ENDPOINTS} - {e.name for e in reachable}
        if skipped:
            self.stdout.write(self.style.WARNING(
                f"Skipping unreachable/disabled endpoints: {sorted(skipped)}"
            ))

        self.stdout.write(f"Running read benchmark ({config.concurrency} concurrent clients)...")
        http_raw = run_read_benchmark(config, reachable)

        if config.include_writes:
            self.stdout.write("Running write benchmark (--include-writes)...")
            http_raw.update(run_write_benchmark(config))

        http_summary = {
            name: summarize(data["latencies_ms"], data["errors"]) for name, data in http_raw.items()
        }

        finished_at = datetime.now(timezone.utc)
        buffer_hit_ratio_end = capture_buffer_hit_ratio(config.db_alias)
        fp_stats = fingerprint_stats(config.db_alias, started_at, finished_at)

        report = {
            "label": config.label,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "config": {
                "base_url": config.base_url,
                "gt_name": config.gt_name,
                "concurrency": config.concurrency,
                "requests_per_endpoint": config.requests_per_endpoint,
                "include_writes": config.include_writes,
            },
            "http": http_summary,
            "db": {
                "buffer_hit_ratio_start": buffer_hit_ratio_start,
                "buffer_hit_ratio_end": buffer_hit_ratio_end,
                "fingerprints": fp_stats,
            },
        }

        path = save_report(report, config.output_dir, config.label)
        self.stdout.write(self.style.SUCCESS(f"Report written to {path}"))

        for name, s in http_summary.items():
            self.stdout.write(
                f"  {name}: p50={s['p50_ms']:.1f}ms p95={s['p95_ms']:.1f}ms "
                f"p99={s['p99_ms']:.1f}ms errors={s['errors']}/{s['count']}"
                if s["count"] else f"  {name}: no successful requests"
            )

        if options["compare_to"]:
            baseline = load_report(options["compare_to"])
            diff = diff_reports(baseline, report)
            self.stdout.write("\nComparison vs baseline (negative = faster than before):")
            for name, metrics in diff["http"].items():
                p95 = metrics["p95_ms"]
                if p95["pct_change"] is None:
                    continue
                self.stdout.write(
                    f"  {name}: p95 {p95['before']:.1f}ms -> {p95['after']:.1f}ms "
                    f"({p95['pct_change']:+.1f}%)"
                )
