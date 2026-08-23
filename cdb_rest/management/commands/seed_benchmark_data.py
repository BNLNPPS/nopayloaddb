"""Seed enough PayloadIOV data for the benchmark to mean something.

test.py creates a single PayloadIOV, so every request hits the same row and the
cache-sensitive rules (R5, R7, R8) cannot be judged. Namespaced under --prefix;
--clean removes exactly what it created.

    python manage.py seed_benchmark_data --global-tags 3 --payload-types 8 --iovs 500
"""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from cdb_rest.models import (
    GlobalTag,
    GlobalTagStatus,
    PayloadIOV,
    PayloadList,
    PayloadListIdSequence,
    PayloadType,
)


class Command(BaseCommand):
    help = "Seed a benchmark-sized PayloadIOV dataset (additive, namespaced, reversible)"

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="bench",
                            help="Name prefix for everything created, so --clean can find it.")
        parser.add_argument("--global-tags", type=int, default=3)
        parser.add_argument("--payload-types", type=int, default=8)
        parser.add_argument("--iovs", type=int, default=500,
                            help="PayloadIOV rows per (global tag, payload type) pair.")
        parser.add_argument("--seed", type=int, default=20260821,
                            help="Makes the generated minor_iov values reproducible.")
        parser.add_argument("--batch-size", type=int, default=2000)
        parser.add_argument("--clean", action="store_true",
                            help="Delete everything under --prefix and exit.")

    def handle(self, *args, **options):
        prefix = options["prefix"]

        if options["clean"]:
            return self._clean(prefix)

        n_gts = options["global_tags"]
        n_types = options["payload_types"]
        n_iovs = options["iovs"]
        total = n_gts * n_types * n_iovs

        self.stdout.write(
            f"Seeding {n_gts} GlobalTag(s) x {n_types} PayloadType(s) x {n_iovs} IOV(s) "
            f"= {total} PayloadIOV rows under prefix '{prefix}'..."
        )

        rng = random.Random(options["seed"])
        status, _ = GlobalTagStatus.objects.get_or_create(name="unlocked")

        payload_types = [
            PayloadType.objects.get_or_create(name=f"{prefix}_type_{t}")[0]
            for t in range(n_types)
        ]

        created = 0
        for g in range(n_gts):
            gt_name = f"{prefix}_gt_{g}"
            with transaction.atomic():
                gt, made = GlobalTag.objects.get_or_create(
                    name=gt_name,
                    defaults={"status": status, "author": prefix,
                              "description": "benchmark dataset"},
                )
                if not made:
                    self.stdout.write(self.style.WARNING(
                        f"  {gt_name} already exists; skipping (use --clean first to reseed)"))
                    continue

                for t, ptype in enumerate(payload_types):
                    plist = PayloadList.objects.create(
                        id=PayloadListIdSequence.objects.create().id,
                        name=f"{prefix}_pl_{g}_{t}",
                        global_tag=gt,
                        payload_type=ptype,
                    )
                    batch = []
                    for i in range(n_iovs):
                        minor = rng.randint(0, 999_999)
                        batch.append(PayloadIOV(
                            payload_url=f"/{prefix}/g{g}/t{t}/payload_{i}.root",
                            checksum=f"{prefix}_checksum_{g}_{t}_{i}",
                            size=1024,
                            major_iov=i,
                            minor_iov=minor,
                            major_iov_end=i,
                            minor_iov_end=minor,
                            payload_list=plist,
                            # Mirrors cdb_rest.utils.compute_comb_iov.
                            comb_iov=i + minor / 1e19,
                        ))
                        if len(batch) >= options["batch_size"]:
                            PayloadIOV.objects.bulk_create(batch)
                            created += len(batch)
                            batch = []
                    if batch:
                        PayloadIOV.objects.bulk_create(batch)
                        created += len(batch)
            self.stdout.write(f"  {gt_name}: {n_types * n_iovs} IOVs")

        if created == 0:
            # "Created 0 rows" in success styling reads like the seed worked.
            self.stdout.write(self.style.ERROR(
                f"No rows created -- every GlobalTag under prefix '{prefix}' already exists."
            ))
            self.stdout.write(
                f"  Existing data was left untouched. To reseed from scratch:\n"
                f"    python manage.py seed_benchmark_data --prefix {prefix} --clean\n"
                f"  then re-run this command."
            )
            return

        self.stdout.write(self.style.SUCCESS(f"Created {created} PayloadIOV rows."))
        self.stdout.write(
            "Statistics are now stale for the new rows. Run ANALYZE before taking a "
            "baseline, or leave them stale on purpose to watch rule R6/R2 fire."
        )

    def _clean(self, prefix):
        # PayloadIOV and PayloadList cascade from GlobalTag; PayloadType is PROTECTed.
        gts = GlobalTag.objects.filter(name__startswith=f"{prefix}_")
        n_gts = gts.count()
        with transaction.atomic():
            gts.delete()
            PayloadList.objects.filter(name__startswith=f"{prefix}_").delete()
            types = PayloadType.objects.filter(name__startswith=f"{prefix}_")
            n_types = types.count()
            types.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Removed {n_gts} GlobalTag(s) and {n_types} PayloadType(s) under '{prefix}' "
            "(PayloadLists and PayloadIOVs cascaded)."))
