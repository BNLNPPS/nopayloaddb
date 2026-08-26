"""Create or upgrade the ai_optimizer schema; run once after each deploy.

The schema sits outside Django's migration history, and only the collector,
tuner and benchmark call ensure_schema() -- so after an upgrade that adds a
column the read-only suggestions API can fail on every request. Idempotent, and
issues DDL, so point --db-alias at a writable database.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from cdb_rest.query_optimization import storage


class Command(BaseCommand):
    help = "Create or upgrade the ai_optimizer schema (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument("--db-alias", default=settings.CDB_AI_OPTIMIZER_DB_ALIAS)

    def handle(self, *args, **options):
        alias = options["db_alias"]
        if alias not in settings.DATABASES:
            raise CommandError(f"unknown database alias {alias!r}")

        before = self._columns(alias)
        try:
            storage.ensure_schema(alias)
        except Exception as exc:
            raise CommandError(
                f"could not apply the ai_optimizer schema on '{alias}': {exc}\n"
                "This command issues DDL -- point --db-alias at a writable database."
            )
        after = self._columns(alias)

        added = sorted(after - before)
        self.stdout.write(self.style.SUCCESS(f"ai_optimizer schema is up to date on '{alias}'."))
        if added:
            self.stdout.write(f"  added: {', '.join(added)}")
        else:
            self.stdout.write("  no changes needed.")

    def _columns(self, alias):
        """Columns currently in the schema, for a readable diff."""
        sql = """
            SELECT table_name || '.' || column_name
            FROM information_schema.columns
            WHERE table_schema = 'ai_optimizer'
        """
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute(sql)
                return {row[0] for row in cursor.fetchall()}
        except Exception:
            return set()
