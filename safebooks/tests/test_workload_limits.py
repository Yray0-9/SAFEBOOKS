from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from safebooks.models import Client, FinancialRecord, FinancialRecordLine
from safebooks.services import analytics_service as analytics, financial_record_service as records
from safebooks.services.forecasting_service import build_sarima_forecast
from safebooks.services.workload_limits import (
    MAX_RECORDS, MAX_TRANSACTION_DETAILS, MAX_FORECAST_SERIES,
    MAX_FORECAST_OBSERVATIONS, MAX_FORECAST_HORIZON, WorkloadLimitExceeded,
)
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.tests import test_query_growth as query_fixtures
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class WorkloadLimitTests(TestCase):
    setUp = query_fixtures.QueryGrowthTests.setUp
    make_client = query_fixtures.QueryGrowthTests.make_client
    make_record = query_fixtures.QueryGrowthTests.make_record

    def login(self):
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.id
        bind_authenticated_session(session)
        session.save()

    def assert_limit(self, payload):
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "workload_limit")
        for key in ("records", "rows", "summary", "predictive_forecast"):
            self.assertNotIn(key, payload, "Never return truncated financial results")

    def test_approved_limits_and_forecast_horizon_validation(self):
        self.assertEqual((MAX_RECORDS, MAX_TRANSACTION_DETAILS, MAX_FORECAST_SERIES, MAX_FORECAST_OBSERVATIONS, MAX_FORECAST_HORIZON), (5000, 20000, 60, 240, 12))
        self.login()
        for horizon in (1, 3, 6, 12):
            self.assertEqual(self.client.get(reverse("api_analytics_summary"), {"horizon": horizon}).status_code, 200)
        for horizon in ("0", "13", "-1", "1.5", "abc", "9" * 6000, "٣"):
            with self.subTest(horizon_length=len(horizon)):
                response = self.client.get(reverse("api_analytics_summary"), {"horizon": horizon})
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("summary", response.json())

    def test_exact_record_boundary_and_one_over_are_checked_before_details(self):
        ledger = self.make_client()
        first = self.make_record(ledger)
        FinancialRecord.objects.bulk_create([
            FinancialRecord(bookkeeper=self.owner, client=ledger, period=first.period, entry_date=date(2026, 9, 4), total_amount=0)
            for _ in range(MAX_RECORDS - 1)
        ])
        allowed = records.list_records_for_client_period(self.owner, ledger.id, "all")
        self.assertTrue(allowed["ok"])
        self.assertEqual(len(allowed["records"]), MAX_RECORDS)
        FinancialRecord.objects.create(bookkeeper=self.owner, client=ledger, period=first.period, entry_date=date(2026, 9, 5), total_amount=0)
        with CaptureQueriesContext(connection) as queries:
            blocked = records.list_records_for_client_period(self.owner, ledger.id, "all")
        self.assert_limit(blocked)
        self.assertFalse(any('FROM "financial_record_lines"' in query["sql"] for query in queries))
        self.assert_limit(records.list_transactions_for_client_range(self.owner, ledger.id, "2026-01-01", "2026-12-31"))
        self.assert_limit(analytics.get_analytics_summary_for_bookkeeper(self.owner, ledger.id))

    def test_exact_detail_boundary_and_one_over_do_not_return_partial_totals(self):
        ledger = self.make_client()
        first = self.make_record(ledger)
        FinancialRecordLine.objects.bulk_create([
            FinancialRecordLine(record=first, type_code="Sales", description="Synthetic detail", amount=0, sort_order=index + 3)
            for index in range(MAX_TRANSACTION_DETAILS - 2)
        ])
        allowed = records.list_transactions_for_client_range(self.owner, ledger.id, "2026-01-01", "2026-12-31")
        self.assertTrue(allowed["ok"])
        self.assertEqual(len(allowed["rows"]), MAX_TRANSACTION_DETAILS)
        FinancialRecordLine.objects.create(record=first, type_code="Sales", description="One over", amount=0, sort_order=MAX_TRANSACTION_DETAILS + 1)
        self.assert_limit(records.list_transactions_for_client_range(self.owner, ledger.id, "2026-01-01", "2026-12-31"))
        self.assert_limit(records.list_records_for_client_period(self.owner, ledger.id, "all"))
        self.assert_limit(analytics.get_analytics_summary_for_bookkeeper(self.owner, ledger.id))
        self.assert_limit(records.get_last_record_for_client_period(self.owner, ledger.id, 10, 2026))

    def test_detail_budget_is_global_and_filters_allow_recovery(self):
        ledger = self.make_client()
        self.make_record(ledger, entry_date=date(2025, 9, 3))
        self.make_record(ledger)
        with patch.object(records, "MAX_TRANSACTION_DETAILS", 3):
            self.assert_limit(records.list_records_for_client_period(self.owner, ledger.id, "all"))
            self.assertTrue(records.list_records_for_client_period(self.owner, ledger.id, 9, 2026)["ok"])
            self.assertTrue(records.list_transactions_for_client_range(self.owner, ledger.id, "2026-01-01", "2026-12-31")["ok"])

    def test_oversized_write_is_rejected_without_saving_any_lines(self):
        ledger = self.make_client()
        payload = {"date": "2026-09-03", "line_items": [{"type_code": "Sales", "description": "Synthetic", "amount": "1.00"}] * (MAX_TRANSACTION_DETAILS + 1)}
        result = records.create_record_for_client_period(self.owner, ledger.id, payload)
        self.assertFalse(result["ok"])
        self.assertIn("20,000", result["message"])
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertFalse(FinancialRecordLine.objects.exists())

    def test_forecast_series_limit_precedes_any_model_fit_and_retains_safe_selector(self):
        ledger = self.make_client()
        self.make_record(ledger)
        with patch.object(analytics, "MAX_FORECAST_SERIES", 1), patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            payload = analytics.get_analytics_summary_for_bookkeeper(self.owner)
        self.assert_limit(payload)
        fit.assert_not_called()
        self.assertEqual(payload["available_clients"][0]["id"], ledger.id)
        self.assertNotIn("email_password", payload["available_clients"][0])

    def test_year_filtered_analytics_remains_usable_with_larger_older_workflow_history(self):
        ledger = self.make_client()
        for _ in range(3):
            self.make_record(ledger, entry_date=date(2025, 9, 3))
        self.make_record(ledger)
        with patch.object(analytics, "MAX_RECORDS", 2):
            self.assert_limit(analytics.get_analytics_summary_for_bookkeeper(self.owner, ledger.id))
            narrow = analytics.get_analytics_summary_for_bookkeeper(self.owner, ledger.id, year_filter="2026")
        self.assertTrue(narrow["ok"])
        self.assertEqual(narrow["summary"]["total_sales"], 1.0)
        self.assertTrue(narrow["client_workflow"]["has_any_records"])
        self.assertEqual(narrow["client_workflow"]["latest_entry_date"], "2026-09-03")

    def test_observation_limit_precedes_any_model_fit(self):
        ledger = self.make_client()
        self.make_record(ledger)
        self.make_record(ledger, entry_date=date(2026, 8, 3))
        with patch.object(analytics, "MAX_FORECAST_OBSERVATIONS", 1), patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            payload = analytics.get_analytics_summary_for_bookkeeper(self.owner, ledger.id)
        self.assert_limit(payload)
        fit.assert_not_called()
        with patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            with self.assertRaises(WorkloadLimitExceeded):
                build_sarima_forecast(
                    period_totals={(2000 + index // 12, index % 12 + 1): Decimal(1) for index in range(241)},
                    frequency="monthly", forecast_through=(2021, 3),
                )
        fit.assert_not_called()

    def test_far_future_forecast_does_not_silently_truncate(self):
        with self.assertRaises(WorkloadLimitExceeded), patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            build_sarima_forecast(period_totals={(2000, 1): Decimal(1)}, frequency="monthly", forecast_through=(2026, 1))
        fit.assert_not_called()

    def test_year_metadata_is_owned_private_and_does_not_load_transaction_details(self):
        ledger = self.make_client()
        self.make_record(ledger, entry_date=date(2025, 9, 3))
        self.make_record(ledger)
        self.login()
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("api_reports_print_layout"), {"client_id": ledger.id, "years_only": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["available_years"], [2026, 2025])
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("rows", response.json())
        self.assertEqual(response.json()["client"]["email_password"], "")
        self.assertFalse(any('FROM "financial_record_lines"' in query["sql"] for query in queries))
        other_owner = self.owner.__class__.objects.create(full_name="Other", username="limit_other", email="limit-other@example.com", password_hash="unused", status="approved")
        foreign = Client.objects.create(bookkeeper=other_owner, client_name="Foreign", tin_number="999999999999", location="Synthetic")
        self.assertEqual(self.client.get(reverse("api_reports_print_layout"), {"client_id": foreign.id, "years_only": "1"}).status_code, 404)

    def test_extreme_numeric_query_parameters_return_errors_not_server_exceptions(self):
        self.login()
        for name in ("client_id", "year"):
            response = self.client.get(reverse("api_analytics_summary"), {name: "9" * 6000})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(reverse("api_reports_print_layout"), {"client_id": "9" * 6000}).status_code, 400)

    def test_templates_have_accessible_workload_error_states(self):
        ledger = self.make_client()
        self.login()
        for route, args, marker in (
            ("financial_records_client", (), 'id="financialLoadError" role="alert"'),
            ("client_details", (ledger.id,), 'id="analyticsLoadError" role="alert"'),
        ):
            response = self.client.get(reverse(route, args=args))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, marker)
