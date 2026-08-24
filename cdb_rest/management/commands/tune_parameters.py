import logging
import time

from django.core.management.base import BaseCommand

from cdb_rest.query_optimization.parameter_tuner import ParameterTuner

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Compute and store dynamic PostgreSQL parameter-tuning suggestions"

    def add_arguments(self, parser):
        parser.add_argument("--db-alias", default="read_db_1")
        parser.add_argument("--interval", type=int, default=3600)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        db_alias = options["db_alias"]
        interval = options["interval"]
        once = options["once"]

        while True:
            try:
                stored = ParameterTuner(db_alias).run()
                self.stdout.write(
                    self.style.SUCCESS(f"tuner run stored={len(stored)} suggestion(s)")
                )
            except Exception:
                logger.exception("parameter tuner run failed")
                self.stderr.write(self.style.ERROR("parameter tuner run failed"))

            if once:
                break
            time.sleep(interval)
