"""The /ai/suggestions/ REST API.

Approving an immediately-appliable safe_sql executes it and moves the suggestion
to 'applied'; DDL and advisory suggestions stay 'approved' for the off-peak job
or manual action. Raw SQL rather than models, since ai_optimizer sits outside
Django's migration history.
"""

from django.conf import settings
from django.db import connections
from django.db.utils import ProgrammingError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cdb_rest.views import WriteAuthMixin

from . import apply, storage

VALID_STATUS_FILTERS = set(storage.SUGGESTION_STATUSES)

# Only the review decision is a human PATCH; terminal states are earned by measurement.
PATCH_ALLOWED_STATUSES = {"approved", "rejected"}


def _db_alias():
    return settings.CDB_AI_OPTIMIZER_DB_ALIAS


def _schema_out_of_date(exc):
    """The ai_optimizer schema is outside Django's migration history, so a
    deploy can leave the API reading columns the database does not have yet
    (nothing applies the schema except the collector/tuner/benchmark, which
    only run on their own schedule). Turn that into an actionable 503 rather
    than an opaque 500."""
    return Response(
        {
            "detail": "The ai_optimizer schema is missing or out of date on this "
                      "database. Run `python manage.py ensure_ai_schema` against the "
                      "primary and retry.",
            "error": str(exc).strip().splitlines()[0] if str(exc).strip() else "",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


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
                   created_at, updated_at, applied_at, benchmarked_at,
                   evaluated_at, evaluation_status, empirical_pct_change,
                   latest_evaluation_id
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

        try:
            with connections[_db_alias()].cursor() as cursor:
                cursor.execute(sql, params)
                rows = [_row_to_dict(cursor, row) for row in cursor.fetchall()]
        except ProgrammingError as exc:
            return _schema_out_of_date(exc)

        return Response(rows)


class SuggestionDetailAPIView(WriteAuthMixin, APIView):
    """GET full detail including the plan tree; PATCH to approve or reject."""

    def get(self, request, pk):
        sql = """
            SELECT s.id, s.plan_id, s.parameter_name, s.queryid, s.rule_id,
                   s.category, s.priority, s.message, s.safe_sql, s.confidence,
                   s.source, s.status, s.created_at, s.updated_at, s.applied_at,
                   s.benchmarked_at, s.evaluated_at, s.evaluation_status,
                   s.empirical_pct_change, s.latest_evaluation_id,
                   p.plan_json, p.query_text, p.mean_exec_time
            FROM ai_optimizer.suggestions s
            LEFT JOIN ai_optimizer.explain_plans p ON p.id = s.plan_id
            WHERE s.id = %s
        """
        try:
            with connections[_db_alias()].cursor() as cursor:
                cursor.execute(sql, [pk])
                row = cursor.fetchone()
                if row is None:
                    return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
                result = _row_to_dict(cursor, row)

                # Measured evidence beside `confidence`, so disagreement is visible.
                cursor.execute(
                    """
                    SELECT id, evaluated_at, verdict, latency_status, mechanism_status,
                           primary_endpoint, baseline_p50_ms, baseline_p95_ms,
                           baseline_spread_ms, optimized_p50_ms, optimized_p95_ms,
                           optimized_spread_ms, pct_change_p95, noise_band_ms,
                           exceeds_noise, repetitions, warmup_requests, workload_profile,
                           experiment_mode, application_order, caveats, rationale,
                           db_metric_deltas, plan_changes, postcondition
                    FROM ai_optimizer.suggestion_evaluations
                    WHERE suggestion_id = %s
                    ORDER BY evaluated_at DESC
                    LIMIT 10
                    """,
                    [pk],
                )
                result["evaluations"] = [_row_to_dict(cursor, r) for r in cursor.fetchall()]
        except ProgrammingError as exc:
            return _schema_out_of_date(exc)

        return Response(result)

    def patch(self, request, pk):
        new_status = request.data.get("status")
        if new_status not in PATCH_ALLOWED_STATUSES:
            return Response(
                {"detail": f"status must be one of {sorted(PATCH_ALLOWED_STATUSES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        db_alias = _db_alias()
        # 'approved' is retryable after a failed apply; 'rejected' only from 'pending'.
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

        if new_status != "approved":
            return Response({"id": pk, "status": new_status})

        if not safe_sql:
            # No SQL to run, so say so rather than leave the operator at "0/0 applied".
            return Response({
                "id": pk,
                "status": "approved",
                "applied": False,
                "advisory": True,
                "detail": "Advisory suggestion: it has no safe_sql, so nothing will be "
                          "executed and apply_approved_suggestions will not pick it up. "
                          "Acting on it requires the manual change described in `message`.",
            })

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
