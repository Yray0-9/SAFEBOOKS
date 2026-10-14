"""Synthetic dense-query, safe-failure and request-local forecast regressions."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount, FinancialRecord, FinancialRecordLine, Period
from safebooks.services import analytics_service as analytics
from safebooks.services.workload_limits import WorkloadLimitExceeded
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.tests import test_query_growth as query_fixtures
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class AnalyticsResilienceTests(TestCase):
    setUp = query_fixtures.QueryGrowthTests.setUp
    make_client = query_fixtures.QueryGrowthTests.make_client

    def authenticate(self):
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.id
        bind_authenticated_session(session)
        session.save()

    def test_dense_permitted_history_completes_under_postgres_query_timeout(self):
        ledger = self.make_client()
        period = Period.objects.create(client=ledger, year=2026, month=10)
        records = FinancialRecord.objects.bulk_create([
            FinancialRecord(bookkeeper=self.owner, client=ledger, period=period,
                            entry_date=date(2026, 10, 1), total_amount=4)
            for _ in range(5000)
        ])
        FinancialRecordLine.objects.bulk_create([
            FinancialRecordLine(record=record, type_code="Sales", description="Synthetic dense detail", amount=1, sort_order=index)
            for record in records for index in range(4)
        ])
        if connection.vendor == "postgresql":
            # Local to this test transaction, never a production setting.
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5s'")
        with patch.object(analytics.timezone, "localdate", return_value=date(2026, 10, 12)):
            payload = analytics.get_analytics_summary_for_bookkeeper(self.owner, ledger.id, year_filter="2026")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["total_sales"], 20000.0)
        self.assertEqual(payload["client_workflow"]["current_period_entry_count"], 5000)
        self.assertEqual(payload["client_workflow"]["current_period_transaction_detail_count"], 20000)
        self.assertTrue(payload["client_workflow"]["has_current_period_record"])

    def test_workflow_latest_tie_break_ignores_later_backdated_insert_and_foreign_owner(self):
        ledger = self.make_client()
        period = Period.objects.create(client=ledger, year=2026, month=10)
        for entry_date, frequency in ((date(2026, 10, 10), "monthly"), (date(2026, 10, 10), "quarterly"), (date(2026, 10, 1), "monthly")):
            FinancialRecord.objects.create(bookkeeper=self.owner, client=ledger, period=period, entry_date=entry_date, frequency=frequency)
        other = BookkeeperAccount.objects.create(full_name="Synthetic Foreign", username="resilience_foreign", email="foreign@example.test", password_hash="unused", status="approved")
        FinancialRecord.objects.create(bookkeeper=other, client=ledger, period=period, entry_date=date(2026, 10, 11), frequency="annually")
        workflow = analytics._build_client_workflow_status(ledger, self.owner, date(2026, 10, 12))
        self.assertEqual(workflow["latest_entry_date"], "2026-10-10")
        self.assertEqual(workflow["latest_period_label"], analytics._format_period_label(2026, 10, "quarterly"))
        self.assertEqual({item["frequency"] for item in workflow["schedule_items"]}, {"monthly", "quarterly"})

    def test_database_failure_is_safe_json_503_without_partial_data_or_private_logs(self):
        self.authenticate()
        with patch("safebooks.views.get_analytics_summary_for_bookkeeper", side_effect=OperationalError("SyntheticPrivateConnectionMarker")), self.assertLogs("safebooks.views", level="WARNING") as logs:
            response = self.client.get(reverse("api_analytics_summary"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "analytics_unavailable")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("SyntheticPrivateConnectionMarker", response.content.decode() + " ".join(logs.output))
        self.assertFalse(any(key in response.json() for key in ("summary", "client_workflow", "predictive_forecast")))

    def test_unauthenticated_request_cannot_reach_analytics(self):
        with patch("safebooks.views.get_analytics_summary_for_bookkeeper") as service:
            self.assertEqual(self.client.get(reverse("api_analytics_summary")).status_code, 401)
        service.assert_not_called()

    def test_combined_fit_limit_api_retains_owned_selector_without_partial_money(self):
        for index in range(9):
            ledger = self.make_client()
            periods = Period.objects.bulk_create([Period(client=ledger, year=2024 + month // 12, month=month % 12 + 1) for month in range(24)])
            records = FinancialRecord.objects.bulk_create([FinancialRecord(bookkeeper=self.owner, client=ledger, period=period,
                entry_date=date(period.year, period.month, 1), total_amount=index + 1) for period in periods])
            FinancialRecordLine.objects.bulk_create([FinancialRecordLine(record=record, type_code="Sales", description="Synthetic", amount=index + 1) for record in records])
        self.authenticate()
        with patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            response = self.client.get(reverse("api_analytics_summary"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "workload_limit")
        self.assertEqual(len(response.json()["available_clients"]), 9)
        self.assertFalse(any(key in response.json() for key in ("summary", "client_workflow", "predictive_forecast")))
        self.assertNotIn("email_password", response.content.decode())
        fit.assert_not_called()


class ForecastWorkBudgetTests(SimpleTestCase):
    def lines(self, clients, observations, *, identical=False):
        result = []
        for client_id in range(1, clients + 1):
            for index in range(observations):
                year, month = 2006 + index // 12, index % 12 + 1
                record = SimpleNamespace(client_id=client_id, period_id=index + 1, frequency="monthly", entry_date=date(year, month, 1),
                                         period=SimpleNamespace(year=year, month=month))
                result.append(SimpleNamespace(record=record, type_code="Sales", description="Synthetic", amount=Decimal(100 if identical else client_id * 100)))
        return result

    def fit(self, values, seasonal_period, steps):
        return [values[-1]] * steps

    def test_identical_histories_fit_once_and_retain_all_client_contributions(self):
        with patch("safebooks.services.forecasting_service._fit_sarima", side_effect=self.fit) as fit:
            result = analytics._build_predictive_forecast(lines=self.lines(20, 240, identical=True), forecast_horizon=12)
        self.assertEqual(fit.call_count, 1)
        self.assertTrue(result["has_forecast"])
        self.assertEqual(result["expected_sales"], 2000.0)

    def test_eight_distinct_fits_allowed_nine_rejected_before_any_fit(self):
        with patch("safebooks.services.forecasting_service._fit_sarima", side_effect=self.fit) as fit:
            self.assertTrue(analytics._build_predictive_forecast(lines=self.lines(8, 24))["has_forecast"])
        self.assertEqual(fit.call_count, 8)
        with patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            with self.assertRaises(WorkloadLimitExceeded):
                analytics._build_predictive_forecast(lines=self.lines(9, 24))
        fit.assert_not_called()

    def test_combined_observation_boundary_allowed_and_over_rejected(self):
        with patch("safebooks.services.forecasting_service._fit_sarima", side_effect=self.fit) as fit:
            self.assertTrue(analytics._build_predictive_forecast(lines=self.lines(4, 240))["has_forecast"])
        self.assertEqual(fit.call_count, 4)
        with patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            with self.assertRaises(WorkloadLimitExceeded):
                analytics._build_predictive_forecast(lines=self.lines(5, 200))
        fit.assert_not_called()

    def test_insufficient_histories_do_not_consume_fit_budget(self):
        with patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            result = analytics._build_predictive_forecast(lines=self.lines(20, 1))
        self.assertFalse(result["has_forecast"])
        fit.assert_not_called()

    def test_cached_models_are_independent_and_cache_is_not_shared_between_requests(self):
        totals = {(2024 + index // 12, index % 12 + 1): Decimal(100) for index in range(24)}
        arguments = dict(category="sales", frequency="monthly", group_key="sales", period_totals=totals, forecast_through=(2026, 3))
        with patch("safebooks.services.forecasting_service._fit_sarima", side_effect=self.fit) as fit:
            cache = {}
            first = analytics._build_group_forecast_model(client_id=1, fit_cache=cache, **arguments)
            first["forecast_by_period"][(2026, 1)] = Decimal(999)
            second = analytics._build_group_forecast_model(client_id=2, fit_cache=cache, **arguments)
            self.assertEqual(second["client_id"], 2)
            self.assertEqual(second["forecast_by_period"][(2026, 1)], Decimal(100))
            self.assertEqual(first["client_id"], 1)
            analytics._build_group_forecast_model(client_id=3, fit_cache={}, **arguments)
        self.assertEqual(fit.call_count, 2)
