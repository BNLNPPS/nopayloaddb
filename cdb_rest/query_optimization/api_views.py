"""The /ai/suggestions/ REST API (proposal Section 7.6).

Every suggestion -- whether from the rule engine, the LLM layer, or the
dynamic tuner -- moves through the same pending -> approved/rejected state
machine. Approving a suggestion with immediately-appliable safe_sql executes
it right away and transitions it to 'applied'; DDL-class safe_sql
(CREATE INDEX CONCURRENTLY / REINDEX CONCURRENTLY) and advisory-only
suggestions (no safe_sql, or CREATE TEMP TABLE) stay 'approved' -- the
former picked up by the apply_approved_suggestions off-peak job, the latter
requiring manual operator action.

This module intentionally uses raw SQL against the ai_optimizer schema
(like cdb_rest/views.py's PayloadIOVsSQLListAPIView) rather than Django
models: ai_optimizer is explicitly outside Django's migration history
(see storage.py), so there's nothing to declare a model against.
"""

from django.conf import settings
from django.db import connections

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cdb_rest.views import WriteAuthMixin

from . import apply

VALID_STATUS_FILTERS = {"pending", "approved", "rejected", "applied"}
PATCH_ALLOWED_STATUSES = {"approved", "rejected"}


def _db_alias():
    return settings.CDB_AI_OPTIMIZER_DB_ALIAS


def _row_to_dict(cursor, row):
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


class SuggestionListAPIView(WriteAuthMixin, APIView):
    """GET /ai/suggestions/?status=pending_review&category=WORK_MEM"""

    def get(self, request):
        status_filter = request.GET.get("status")
        category_filter = request.GET.get("category")

        if status_filter and status_filter not in VALID_STATUS_FILTERS:
            return Response(
                {"detail": f"status must be one of {sorted(VALID_STATUS_FILTERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sql = """
            SELECT id, plan_id, parameter_name, queryid, rule_id, category,
                   priority, message, safe_sql, confidence, source, status,
                   created_at, updated_at, applied_at
            FROM ai_optimizer.suggestions
            WHERE 1 = 1
        """
        params = []
        if status_filter:
            sql += " AND status = %s"
            params.append(status_filter)
        if category_filter:
            sql += " AND category = %s"
            params.append(category_filter)
        sql += " ORDER BY created_at DESC LIMIT 200"

        with connections[_db_alias()].cursor() as cursor:
            cursor.execute(sql, params)
            rows = [_row_to_dict(cursor, row) for row in cursor.fetchall()]

        return Response(rows)


class SuggestionDetailAPIView(WriteAuthMixin, APIView):
    """GET full detail (including the annotated plan tree, if any).
    PATCH {"status": "approved" | "rejected"} to review a pending suggestion."""

    def get(self, request, pk):
        sql = """
            SELECT s.id, s.plan_id, s.parameter_name, s.queryid, s.rule_id,
                   s.category, s.priority, s.message, s.safe_sql, s.confidence,
                   s.source, s.status, s.created_at, s.updated_at, s.applied_at,
                   p.plan_json, p.query_text, p.mean_exec_time
            FROM ai_optimizer.suggestions s
            LEFT JOIN ai_optimizer.explain_plans p ON p.id = s.plan_id
            WHERE s.id = %s
        """
        with connections[_db_alias()].cursor() as cursor:
            cursor.execute(sql, [pk])
            row = cursor.fetchone()
            if row is None:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            result = _row_to_dict(cursor, row)

        return Response(result)

    def patch(self, request, pk):
        new_status = request.data.get("status")
        if new_status not in PATCH_ALLOWED_STATUSES:
            return Response(
                {"detail": f"status must be one of {sorted(PATCH_ALLOWED_STATUSES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        db_alias = _db_alias()
        # 'approved' is reachable from 'pending' (the normal path) or from
        # 'approved' itself (retrying a suggestion whose apply previously
        # failed, per the 502 response below). 'rejected' is only reachable
        # from 'pending' -- there's no take-back for an already-approved item
        # through this endpoint.
        allowed_from = {"pending"} if new_status == "rejected" else {"pending", "approved"}

        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                "SELECT status, safe_sql FROM ai_optimizer.suggestions WHERE id = %s",
                [pk],
            )
            row = cursor.fetchone()
            if row is None:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            current_status, safe_sql = row

            if current_status not in allowed_from:
                return Response(
                    {"detail": f"Suggestion is '{current_status}'; cannot transition to '{new_status}'."},
                    status=status.HTTP_409_CONFLICT,
                )

            cursor.execute(
                "UPDATE ai_optimizer.suggestions SET status = %s, updated_at = now() WHERE id = %s",
                [new_status, pk],
            )

        if new_status != "approved" or not safe_sql:
            return Response({"id": pk, "status": new_status})

        if apply.is_queued_ddl(safe_sql):
            return Response(
                {
                    "id": pk,
                    "status": "approved",
                    "applied": False,
                    "detail": "DDL queued for the next off-peak apply_approved_suggestions run.",
                }
            )

        if apply.is_advisory_only(safe_sql):
            return Response(
                {
                    "id": pk,
                    "status": "approved",
                    "applied": False,
                    "detail": "Advisory-only suggestion; requires manual operator action.",
                }
            )

        applied = apply.apply_safe_sql(safe_sql)
        if applied:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    "UPDATE ai_optimizer.suggestions SET status = 'applied', applied_at = now() WHERE id = %s",
                    [pk],
                )
            return Response({"id": pk, "status": "applied", "applied": True})

        return Response(
            {
                "id": pk,
                "status": "approved",
                "applied": False,
                "detail": "Approved, but applying safe_sql failed -- see server logs. "
                "Still 'approved', not 'applied'; safe to retry the PATCH.",
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
