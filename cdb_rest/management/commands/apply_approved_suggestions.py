"""Executes approved DDL-class suggestions (CREATE INDEX CONCURRENTLY /
REINDEX CONCURRENTLY) against the primary.

These statements are never run synchronously from the suggestions API PATCH
request -- they can take minutes on a large table. Instead, approving one
via the API leaves it in 'approved' status, and this command (intended to be
invoked by an off-peak CronJob, per the proposal's cron.yaml pattern) applies
them and marks each 'applied'.
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections

from cdb_rest.query_optimization import apply

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Apply approved DDL-class ai_optimizer suggestions (CREATE/REINDEX CONCURRENTLY)"

    def add_arguments(self, parser):
        parser.add_argument("--db-alias", default=settings.CDB_AI_OPTIMIZER_DB_ALIAS)

    def handle(self, *args, **options):
        db_alias = options["db_alias"]

        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                "SELECT id, safe_sql FROM ai_optimizer.suggestions WHERE status = 'approved' AND safe_sql IS NOT NULL"
            )
            rows = cursor.fetchall()

        queued = [(pk, sql) for pk, sql in rows if apply.is_queued_ddl(sql)]
        applied_count = 0

        for pk, safe_sql in queued:
            self.stdout.write(f"applying suggestion id={pk}: {safe_sql}")
            if apply.apply_queued_ddl(safe_sql):
                with connections[db_alias].cursor() as cursor:
                    cursor.execute(
                        "UPDATE ai_optimizer.suggestions SET status = 'applied', applied_at = now() WHERE id = %s",
                        [pk],
                    )
                applied_count += 1
                self.stdout.write(self.style.SUCCESS(f"applied suggestion id={pk}"))
            else:
                self.stderr.write(self.style.ERROR(f"failed to apply suggestion id={pk}; left as 'approved'"))

        self.stdout.write(
            self.style.SUCCESS(f"apply_approved_suggestions: {applied_count}/{len(queued)} applied")
        )
