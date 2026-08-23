"""Apply approved DDL-class suggestions against the primary.

These can take minutes on a large table, so the API never runs them inline;
approving leaves them 'approved' and this command (an off-peak CronJob) applies
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
                "SELECT id, rule_id, safe_sql FROM ai_optimizer.suggestions WHERE status = 'approved'"
            )
            rows = cursor.fetchall()

        queued = [(pk, sql) for pk, _rule, sql in rows if sql and apply.is_queued_ddl(sql)]
        advisory = [(pk, rule) for pk, rule, sql in rows if not sql]
        immediate = [(pk, rule) for pk, rule, sql in rows
                     if sql and not apply.is_queued_ddl(sql)]
        applied_count = 0

        # "0/0 applied" alone cannot say which case this is, so name it.
        if not queued:
            self.stdout.write("No approved suggestions with queued DDL to apply.")
            if advisory:
                self.stdout.write(
                    "  {} approved suggestion(s) are ADVISORY (no safe_sql) and are never "
                    "auto-applied: {}".format(
                        len(advisory),
                        ", ".join(f"id={pk} ({rule})" for pk, rule in advisory))
                )
                self.stdout.write(
                    "  Approve one whose safe_sql is non-null -- for example a rule that "
                    "emits CREATE INDEX CONCURRENTLY."
                )
            if immediate:
                self.stdout.write(
                    "  {} approved suggestion(s) were applied immediately at approval time "
                    "and need no queued run: {}".format(
                        len(immediate),
                        ", ".join(f"id={pk} ({rule})" for pk, rule in immediate))
                )
            if not advisory and not immediate:
                self.stdout.write(
                    "  Nothing is in 'approved' status. PATCH a pending suggestion to "
                    "{\"status\": \"approved\"} first."
                )
            return

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
