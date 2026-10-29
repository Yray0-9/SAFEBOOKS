"""Synthetic regressions for year-scoped totals and multi-year SARIMA history."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from safebooks.models import Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.services import analytics_service as analytics
from safebooks.services.forecasting_service import FREQUENCY_CONFIG
from safebooks.tests import test_analytics_summary_api as fixtures


class ForecastYearHistoryTests(TestCase):
    _create_bookkeeper = fixtures.AnalyticsSummaryApiTests._create_bookkeeper
    _login_as = fixtures.AnalyticsSummaryApiTests._login_as
    _build_tin = fixtures.AnalyticsSummaryApiTests._build_tin
    _create_client = fixtures.AnalyticsSummaryApiTests._create_client
    _create_record_with_lines = fixtures.AnalyticsSummaryApiTests._create_record_with_lines

    def setUp(self):
        self.clock = patch.object(analytics.timezone, "localdate", return_value=date(2026, 10, 22))
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.owner = self._create_bookkeeper("history-owner")
        self.ledger = self._create_client(bookkeeper=self.owner, suffix="history-owner", remarks=Client.REMARK_ACTIVE)
        self._login_as(self.owner)

    def record(self, year, month, lines, frequency="monthly", **kwargs):
        return self._create_record_with_lines(
            bookkeeper=kwargs.get("bookkeeper", self.owner), client=kwargs.get("client", self.ledger),
            entry_date=date(year, month, 1), lines=lines, frequency=frequency,
        )

    def monthly_history(self, *, categories=True, months=34):
        for index in range(months):
            year, zero_month = divmod(2024 * 12 + index, 12)
            lines = [("SALES", "Synthetic sales", Decimal(1000 + index * 10))]
            if categories:
                lines += [("EXPENSES", "Synthetic expenses", Decimal(100 + index)),
                          ("0619E", "Synthetic monthly tax", Decimal(10) + Decimal(index) / 10)]
            self.record(year, zero_month + 1, lines)

    def read(self, year="2026", horizon=3, client=None):
        query = {"client_id": (client or self.ledger).id, "horizon": horizon}
        if year is not None:
            query["year"] = year
        response = self.client.get(reverse("api_analytics_summary"), query, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["ok"])
        return response.json()

    def snapshot(self):
        return {
            "clients": list(Client.objects.values()),
            "periods": list(Period.objects.values()),
            "records": list(FinancialRecord.objects.values()),
            "lines": list(FinancialRecordLine.objects.values()),
        }

    def test_current_year_uses_34_months_but_totals_and_chart_only_use_2026(self):
        self.monthly_history()
        before = self.snapshot()
        payload = self.read()
        forecast = payload["predictive_forecast"]
        self.assertTrue(forecast["has_forecast"])
        self.assertEqual((forecast["history_start"], forecast["history_end"], forecast["history_cutoff_year"]), ("2024-01", "2026-10", 2026))
        self.assertEqual(forecast["data_points"], 34)
        self.assertEqual(forecast["expected_sales"], 1340.0)
        self.assertEqual(forecast["expected_expenses"], 134.0)
        self.assertEqual(forecast["expected_tax"], 13.4)
        self.assertEqual(forecast["expected_net"], 1206.0)
        self.assertEqual([row["period_label"] for row in forecast["future_projections"]], ["Nov 2026", "Dec 2026", "Jan 2027"])
        self.assertEqual(payload["summary"], {"total_sales": 12850.0, "total_expenses": 1285.0, "total_tax": 128.5, "net_value": 11565.0})
        self.assertEqual([(row["year"], row["month"]) for row in payload["monthly_trend"]], [(2026, m) for m in range(1, 13)])
        self.assertEqual(payload["monthly_trend"][-1]["sales"], 0.0)
        self.assertEqual(before, self.snapshot(), "Analytics reads must not rewrite historical records")

    def test_past_year_forecast_cannot_see_later_year_values(self):
        self.monthly_history()
        later = FinancialRecordLine.objects.filter(record__period__year=2026)
        later.update(amount=Decimal("999999.99"))  # Synthetic future-year outliers.
        before = self.snapshot()
        payload = self.read("2025")
        forecast = payload["predictive_forecast"]
        self.assertTrue(forecast["has_forecast"])
        self.assertEqual((forecast["history_start"], forecast["history_end"], forecast["history_cutoff_year"]), ("2024-01", "2025-12", 2025))
        self.assertEqual(forecast["data_points"], 24)
        self.assertEqual(forecast["expected_sales"], 1240.0)
        self.assertEqual([row["period_label"] for row in forecast["future_projections"]], ["Jan 2026", "Feb 2026", "Mar 2026"])
        self.assertEqual(payload["summary"]["total_sales"], sum(1000 + i * 10 for i in range(12, 24)))
        self.assertEqual(before, self.snapshot())

    def test_earliest_year_still_requires_24_periods_even_when_later_data_exists(self):
        self.monthly_history()
        with patch("safebooks.services.forecasting_service._fit_sarima") as fit:
            forecast = self.read("2024")["predictive_forecast"]
        self.assertFalse(forecast["has_forecast"])
        self.assertEqual(forecast["history_end"], "2024-12")
        self.assertEqual(forecast["sales_readiness_note"], "12 of 24 monthly periods")
        self.assertEqual(FREQUENCY_CONFIG["monthly"]["minimum_observations"], 24)
        self.assertEqual(FREQUENCY_CONFIG["quarterly"]["minimum_observations"], 8)
        fit.assert_not_called()

    def test_three_six_and_twelve_month_horizons_share_the_same_full_history(self):
        self.monthly_history(categories=False)
        for horizon in (3, 6, 12):
            with self.subTest(horizon=horizon):
                forecast = self.read(horizon=horizon)["predictive_forecast"]
                self.assertTrue(forecast["has_forecast"])
                self.assertEqual(forecast["data_points"], 34)
                self.assertEqual(len(forecast["future_projections"]), horizon)
                self.assertEqual(forecast["future_projections"][0]["period_label"], "Nov 2026")

    def test_monthly_sales_and_quarterly_expenses_and_tax_keep_separate_schedules(self):
        self.monthly_history(categories=False)
        for index in range(11):
            year, zero_month = divmod(2024 * 12 + 2 + index * 3, 12)
            self.record(year, zero_month + 1, [("EXPENSES", "Quarterly expense", Decimal(200 + index * 5))], "quarterly")
            # A known quarterly tax form determines its own forecast frequency;
            # the parent record's saved frequency is not rewritten.
            self.record(year, zero_month + 1, [("2551Q", "Synthetic tax entry", Decimal(20 + index))], "monthly")
        before = self.snapshot()
        forecast = self.read()["predictive_forecast"]
        november, december, january = forecast["future_projections"]
        self.assertEqual(forecast["frequency"], "mixed")
        self.assertFalse(november["expected_expenses_applicable"])
        self.assertFalse(november["expected_tax_applicable"])
        self.assertEqual(november["expenses_readiness_note"], "Not scheduled this period")
        self.assertEqual(december["expected_expenses"], 255.0)
        self.assertEqual(december["expected_tax"], 31.0)
        self.assertFalse(january["expected_expenses_applicable"])
        self.assertEqual(before, self.snapshot())

    def test_sparse_monthly_expenses_are_not_retagged_or_replaced_by_quarterly_values(self):
        self.monthly_history(categories=False)
        for month in (8, 9, 10):
            self.record(2026, month, [("EXPENSES", "Monthly expense", Decimal(10))])
        before = self.snapshot()
        forecast = self.read()["predictive_forecast"]
        self.assertTrue(forecast["has_forecast"], "Sales remain eligible independently")
        self.assertIsNone(forecast["expected_expenses"])
        self.assertEqual(forecast["expenses_readiness_note"], "3 of 24 monthly periods")
        self.assertIsNone(forecast["expected_net"], "Missing required expenses must not become zero")
        self.assertEqual(before, self.snapshot())

    def test_missing_expense_month_is_not_imputed_and_explicit_zero_is_counted(self):
        self.monthly_history()
        FinancialRecordLine.objects.filter(type_code="EXPENSES", record__period__year=2025, record__period__month=6).delete()
        FinancialRecordLine.objects.filter(type_code="SALES", record__period__year=2025, record__period__month=6).update(amount=0)
        before = self.snapshot()
        forecast = self.read()["predictive_forecast"]
        self.assertIsNotNone(forecast["expected_sales"])
        self.assertEqual(forecast["data_points"], 34)
        self.assertIsNone(forecast["expected_expenses"])
        self.assertEqual(forecast["expenses_readiness_note"], "Review missing monthly periods")
        self.assertEqual(before, self.snapshot())

    def test_multiple_entries_in_a_month_do_not_increase_observation_count(self):
        self.monthly_history(categories=False)
        self.record(2026, 10, [("SALES", "Additional sale in the same month", Decimal(7))])
        forecast = self.read()["predictive_forecast"]
        self.assertTrue(forecast["has_forecast"])
        self.assertEqual(forecast["data_points"], 34)
        self.assertEqual(FinancialRecord.objects.count(), 35)

    def test_explicit_categories_and_tax_form_frequency_do_not_rewrite_records(self):
        record = self.record(2026, 10, [("EXPENSES", "It's TAXES", Decimal(100)),
                                       ("2551Q", "Synthetic tax entry", Decimal(10))])
        expense, tax = record.line_items.all()
        self.assertEqual(analytics._classify_line_item(expense.type_code, expense.description), "expenses")
        self.assertEqual(analytics._classify_line_item(tax.type_code, tax.description), "tax")
        self.assertEqual(analytics._resolve_line_forecast_frequency(expense, "expenses"), "monthly")
        self.assertEqual(analytics._resolve_line_forecast_frequency(tax, "tax"), "quarterly")
        self.assertEqual(analytics._classify_line_item("SALES", "Tax-related customer note"), "sales")
        self.assertEqual(analytics._classify_line_item("TAXES", "Expense-related note"), "tax")
        before = self.snapshot()
        self.read()
        self.assertEqual(before, self.snapshot())

    def test_annual_expenses_remain_unsupported_instead_of_becoming_monthly(self):
        self.monthly_history(categories=False)
        for year in (2024, 2025, 2026):
            self.record(year, 1, [("EXPENSES", "Annual expense", Decimal(1000))], "annually")
        before = self.snapshot()
        forecast = self.read()["predictive_forecast"]
        self.assertTrue(forecast["has_forecast"])
        january = forecast["future_projections"][-1]
        self.assertTrue(january["expected_expenses_applicable"])
        self.assertIsNone(january["expected_expenses"])
        self.assertEqual(january["expenses_readiness_note"], "Annually forecast unavailable")
        self.assertIsNone(january["expected_net"])
        self.assertEqual(before, self.snapshot())

    def test_forecast_history_excludes_siblings_and_foreign_or_mismatched_owners(self):
        self.monthly_history(categories=False)
        sibling = self._create_client(bookkeeper=self.owner, suffix="sibling-history", remarks=Client.REMARK_NEW)
        foreign_owner = self._create_bookkeeper("foreign-history")
        foreign = self._create_client(bookkeeper=foreign_owner, suffix="foreign-history", remarks=Client.REMARK_NEW)
        for client, owner in ((sibling, self.owner), (foreign, foreign_owner), (self.ledger, foreign_owner), (foreign, self.owner)):
            self.record(2022, 1, [("SALES", "Excluded synthetic outlier", Decimal(999999))], client=client, bookkeeper=owner)
        forecast = self.read()["predictive_forecast"]
        self.assertEqual(forecast["history_start"], "2024-01")
        self.assertEqual(forecast["expected_sales"], 1340.0)
        denied = self.client.get(reverse("api_analytics_summary"), {"client_id": foreign.id, "year": "2026"})
        self.assertEqual(denied.status_code, 404)
        all_clients = self.client.get(reverse("api_analytics_summary"), {"year": "2026"}).json()
        self.assertTrue(all_clients["ok"])
        self.assertEqual(all_clients["predictive_forecast"]["history_start"], "2022-01")
        self.assertEqual(all_clients["summary"]["total_sales"], 12850.0)

    def test_full_training_history_is_bounded_before_any_fit_or_partial_response(self):
        self.monthly_history()
        for name, limit in (("MAX_RECORDS", 33), ("MAX_TRANSACTION_DETAILS", 101), ("MAX_FORECAST_OBSERVATIONS", 33), ("MAX_FORECAST_DISTINCT_FITS", 2)):
            with self.subTest(budget=name), patch.object(analytics, name, limit), patch("safebooks.services.forecasting_service._fit_sarima") as fit:
                response = self.client.get(reverse("api_analytics_summary"), {"client_id": self.ledger.id, "year": "2026"})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "workload_limit")
                self.assertNotIn("summary", response.json())
                self.assertNotIn("predictive_forecast", response.json())
                fit.assert_not_called()

    def test_empty_selected_year_retains_earlier_forecast_and_no_year_keeps_full_history(self):
        self.monthly_history(categories=False, months=24)
        payload = self.read()
        self.assertFalse(payload["has_data"])
        self.assertTrue(payload["predictive_forecast"]["has_forecast"])
        self.assertEqual(payload["predictive_forecast"]["history_end"], "2025-12")
        self.assertTrue(all(row["sales"] == 0 for row in payload["monthly_trend"]))
        full = self.read(None)
        self.assertIsNone(full["predictive_forecast"]["history_cutoff_year"])
        self.assertEqual(full["predictive_forecast"]["data_points"], 24)
        empty = self.read("2023")
        self.assertIsNone(empty["predictive_forecast"]["history_start"])
        self.assertIsNone(empty["predictive_forecast"]["history_end"])
        self.assertFalse(empty["predictive_forecast"]["has_forecast"])

    def test_history_caption_is_present_in_the_client_template(self):
        response = self.client.get(reverse("client_details", args=[self.ledger.id]))
        self.assertContains(response, 'id="analyticsPredictiveHistory"')
        self.assertContains(response, 'id="analyticsDashboardEmptyNotice"')
