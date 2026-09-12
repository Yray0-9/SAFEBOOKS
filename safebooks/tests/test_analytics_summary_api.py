from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class AnalyticsSummaryApiTests(TestCase):
    def _create_bookkeeper(self, suffix: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"analytics_{suffix}",
            email=f"analytics_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
            client_details_password_required=False,
        )

    def _login_as(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        session.save()

    def _build_tin(self, token: str) -> str:
        digits = "".join(char for char in str(token or "") if char.isdigit())
        if digits:
            seed = int(digits)
        else:
            seed = sum(ord(char) for char in str(token or ""))
        return f"{seed:012d}"

    def _create_client(self, *, bookkeeper: BookkeeperAccount, suffix: str, remarks: str) -> Client:
        return Client.objects.create(
            bookkeeper=bookkeeper,
            client_name=f"Client {suffix}",
            tin_number=self._build_tin(f"an-{suffix}"),
            trade_name=f"Trade {suffix}",
            location="Panabo",
            permit_number=f"PERMIT-AN-{suffix}",
            email=f"client-analytics-{suffix}@example.com",
            remarks=remarks,
        )

    def _create_record_with_lines(
        self,
        *,
        bookkeeper: BookkeeperAccount,
        client: Client,
        entry_date: date,
        lines: list[tuple[str, str, Decimal]],
        frequency: str | None = None,
    ) -> FinancialRecord:
        period, _ = Period.objects.get_or_create(
            client=client,
            year=entry_date.year,
            month=entry_date.month,
        )

        record = FinancialRecord.objects.create(
            bookkeeper=bookkeeper,
            client=client,
            period=period,
            entry_date=entry_date,
            frequency=frequency or FinancialRecord.FREQUENCY_MONTHLY,
            notes="Analytics test",
            total_amount=sum((amount for _, _, amount in lines), Decimal("0.00")),
        )

        for index, (type_code, description, amount) in enumerate(lines, start=1):
            FinancialRecordLine.objects.create(
                record=record,
                type_code=type_code,
                description=description,
                amount=amount,
                sort_order=index,
            )

        return record

    def test_analytics_summary_requires_authentication(self):
        response = self.client.get(
            reverse("api_analytics_summary"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Authentication required.")

    def test_client_details_forecasting_card_names_sarima(self):
        owner = self._create_bookkeeper("owner-client-details-sarima")
        self._login_as(owner)
        client = self._create_client(bookkeeper=owner, suffix="client-details-sarima", remarks=Client.REMARK_ACTIVE)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generated using Seasonal ARIMA")
        self.assertNotContains(response, "Weighted Moving Average")

    def test_client_details_starts_in_neutral_analytics_loading_state(self):
        owner = self._create_bookkeeper("owner-client-details-loading")
        self._login_as(owner)
        client = self._create_client(bookkeeper=owner, suffix="client-details-loading", remarks=Client.REMARK_ACTIVE)

        response = self.client.get(reverse("client_details", args=[client.id]))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="analyticsLoadingState"')
        self.assertContains(response, "Loading client records...")
        self.assertContains(response, 'id="analyticsDataPanels" class="tab-content client-analytics-panels" hidden')
        self.assertContains(response, "Checking current period...")
        self.assertNotIn(
            "bindForecastLegendHighlight();\n            applyAnalyticsFallbackState();",
            html,
        )

    def test_analytics_summary_all_clients_returns_expected_values(self):
        today = timezone.localdate()
        previous_year = today.year if today.month > 1 else today.year - 1
        previous_month = today.month - 1 if today.month > 1 else 12

        owner = self._create_bookkeeper("owner-all")
        self._login_as(owner)

        client_a = self._create_client(bookkeeper=owner, suffix="A", remarks=Client.REMARK_NEW)
        client_b = self._create_client(bookkeeper=owner, suffix="B", remarks=Client.REMARK_CLOSED)

        self._create_record_with_lines(
            bookkeeper=owner,
            client=client_a,
            entry_date=today,
            lines=[
                ("Sales", "Sales collection", Decimal("1000.00")),
                ("Expenses", "Office expense", Decimal("300.00")),
                ("1701", "Income tax", Decimal("100.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client_b,
            entry_date=date(previous_year, previous_month, 1),
            lines=[
                ("Sales", "Service income", Decimal("500.00")),
                ("Expenses", "Transport expense", Decimal("200.00")),
                ("2550M", "VAT", Decimal("50.00")),
            ],
        )

        response = self.client.get(reverse("api_analytics_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("scope", {}).get("is_all"))
        self.assertEqual(payload.get("scope", {}).get("client_id"), None)

        self.assertEqual(payload["summary"]["total_sales"], 1500.0)
        self.assertEqual(payload["summary"]["total_expenses"], 500.0)
        self.assertEqual(payload["summary"]["total_tax"], 150.0)
        self.assertEqual(payload["summary"]["net_value"], 1000.0)

        self.assertEqual(payload["remarks_insight"]["level"], Client.REMARK_NEW)
        self.assertTrue(payload["has_data"])
        self.assertEqual(len(payload.get("monthly_trend", [])), 6)

        comparison = payload.get("comparison", [])
        self.assertEqual(len(comparison), 2)
        self.assertEqual(comparison[0]["client_id"], client_a.id)
        self.assertEqual(comparison[0]["remarks_label"], "New")
        self.assertEqual(comparison[0]["total_sales"], 1000.0)

        available_clients = payload.get("available_clients", [])
        available_client_ids = {row["id"] for row in available_clients}
        self.assertEqual(available_client_ids, {client_a.id, client_b.id})
        available_client_tins = {row["tin_number"] for row in available_clients}
        self.assertEqual(available_client_tins, {client_a.tin_number, client_b.tin_number})
        available_client_trades = {row["trade_name"] for row in available_clients}
        self.assertEqual(available_client_trades, {client_a.trade_name, client_b.trade_name})

    def test_analytics_summary_client_scope_and_ownership_isolation(self):
        today = timezone.localdate()

        owner = self._create_bookkeeper("owner-scope")
        other = self._create_bookkeeper("other-scope")

        owner_client = self._create_client(bookkeeper=owner, suffix="owner", remarks=Client.REMARK_ACTIVE)
        other_client = self._create_client(bookkeeper=other, suffix="other", remarks=Client.REMARK_CLOSED)

        self._create_record_with_lines(
            bookkeeper=owner,
            client=owner_client,
            entry_date=today,
            lines=[
                ("Sales", "Sales income", Decimal("700.00")),
                ("Expenses", "Operations expense", Decimal("250.00")),
                ("1701", "Tax", Decimal("70.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=other,
            client=other_client,
            entry_date=today,
            lines=[
                ("Sales", "Other sales", Decimal("900.00")),
                ("Expenses", "Other expense", Decimal("200.00")),
                ("1701", "Other tax", Decimal("90.00")),
            ],
        )

        self._login_as(owner)

        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": owner_client.id},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertFalse(payload["scope"]["is_all"])
        self.assertEqual(payload["scope"]["client_id"], owner_client.id)
        self.assertEqual(payload["scope"]["client_tin"], owner_client.tin_number)
        self.assertEqual(payload["scope"]["client_trade_name"], owner_client.trade_name)
        self.assertEqual(payload["summary"]["total_sales"], 700.0)
        self.assertEqual(payload["summary"]["total_expenses"], 250.0)
        self.assertEqual(payload["summary"]["total_tax"], 70.0)
        self.assertEqual(payload["summary"]["net_value"], 450.0)
        self.assertEqual(payload["client_workflow"]["period_label"], today.strftime("%b %Y"))
        self.assertEqual(payload["client_workflow"]["frequency"], FinancialRecord.FREQUENCY_MONTHLY)
        self.assertEqual(payload["client_workflow"]["frequency_label"], "Monthly")
        self.assertTrue(payload["client_workflow"]["has_current_period_record"])
        self.assertEqual(payload["client_workflow"]["current_period_entry_count"], 1)
        self.assertEqual(payload["client_workflow"]["current_period_transaction_detail_count"], 3)
        self.assertTrue(payload["client_workflow"]["report_ready"])
        self.assertEqual(payload["client_workflow"]["overall_status"], "ready")
        self.assertEqual(len(payload["client_workflow"]["schedule_items"]), 1)
        self.assertEqual(payload["client_workflow"]["schedule_items"][0]["status"], "ready")

        forbidden_response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": other_client.id},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(forbidden_response.status_code, 404)
        forbidden_payload = forbidden_response.json()
        self.assertFalse(forbidden_payload.get("ok"))
        self.assertEqual(forbidden_payload.get("message"), "Client not found.")

    def test_analytics_summary_client_with_no_records_returns_empty_payload(self):
        owner = self._create_bookkeeper("owner-empty")
        empty_client = self._create_client(bookkeeper=owner, suffix="empty", remarks=Client.REMARK_CLOSED)

        self._login_as(owner)
        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": empty_client.id},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertFalse(payload["scope"]["is_all"])
        self.assertEqual(payload["scope"]["client_id"], empty_client.id)
        self.assertEqual(payload["scope"]["client_tin"], empty_client.tin_number)
        self.assertEqual(payload["scope"]["client_trade_name"], empty_client.trade_name)
        self.assertFalse(payload["has_data"])
        self.assertEqual(payload["summary"]["total_sales"], 0.0)
        self.assertEqual(payload["summary"]["total_expenses"], 0.0)
        self.assertEqual(payload["summary"]["total_tax"], 0.0)
        self.assertEqual(payload["summary"]["net_value"], 0.0)
        self.assertEqual(payload["client_workflow"]["period_label"], timezone.localdate().strftime("%b %Y"))
        self.assertEqual(payload["client_workflow"]["frequency"], FinancialRecord.FREQUENCY_MONTHLY)
        self.assertFalse(payload["client_workflow"]["has_current_period_record"])
        self.assertEqual(payload["client_workflow"]["current_period_entry_count"], 0)
        self.assertEqual(payload["client_workflow"]["current_period_transaction_detail_count"], 0)
        self.assertFalse(payload["client_workflow"]["report_ready"])
        self.assertEqual(payload["client_workflow"]["overall_status"], "missing")
        self.assertEqual(len(payload["client_workflow"]["schedule_items"]), 1)
        self.assertEqual(payload["client_workflow"]["schedule_items"][0]["status"], "missing")
        self.assertEqual(payload["comparison"], [])
        self.assertEqual(payload["forecast"]["sparkline"], [])
        self.assertEqual(len(payload.get("monthly_trend", [])), 6)

    def test_client_workflow_uses_quarterly_schedule_when_latest_record_is_quarterly(self):
        today = timezone.localdate()
        current_quarter_end_month = (((today.month - 1) // 3) + 1) * 3
        previous_quarter_end_month = current_quarter_end_month - 3
        previous_quarter_year = today.year
        if previous_quarter_end_month <= 0:
            previous_quarter_end_month += 12
            previous_quarter_year -= 1

        owner = self._create_bookkeeper("owner-quarterly-workflow")
        client = self._create_client(
            bookkeeper=owner,
            suffix="quarterly-workflow",
            remarks=Client.REMARK_ACTIVE,
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(previous_quarter_year, previous_quarter_end_month, 1),
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
            lines=[
                ("Expenses", "Quarterly expense", Decimal("4200.00")),
                ("2551Q", "Quarterly tax", Decimal("800.00")),
            ],
        )

        self._login_as(owner)
        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        workflow = response.json()["client_workflow"]
        self.assertEqual(workflow["frequency"], FinancialRecord.FREQUENCY_QUARTERLY)
        self.assertEqual(workflow["frequency_label"], "Quarterly")
        self.assertEqual(workflow["period_month"], current_quarter_end_month)
        self.assertEqual(workflow["period_year"], today.year)
        self.assertIn("(Q", workflow["period_label"])
        self.assertFalse(workflow["has_current_period_record"])
        self.assertEqual(workflow["current_period_entry_count"], 0)
        expected_status = "missing" if today.month == current_quarter_end_month else "upcoming"
        self.assertEqual(workflow["overall_status"], expected_status)
        self.assertEqual(len(workflow["schedule_items"]), 1)
        self.assertEqual(workflow["schedule_items"][0]["status"], expected_status)

    def test_client_workflow_marks_current_quarter_ready_when_quarterly_record_exists(self):
        today = timezone.localdate()
        current_quarter_end_month = (((today.month - 1) // 3) + 1) * 3

        owner = self._create_bookkeeper("owner-quarter-ready")
        client = self._create_client(
            bookkeeper=owner,
            suffix="quarter-ready",
            remarks=Client.REMARK_ACTIVE,
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(today.year, current_quarter_end_month, 1),
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
            lines=[
                ("Expenses", "Quarterly expense", Decimal("4200.00")),
                ("2551Q", "Quarterly tax", Decimal("800.00")),
            ],
        )

        self._login_as(owner)
        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        workflow = response.json()["client_workflow"]
        self.assertEqual(workflow["frequency"], FinancialRecord.FREQUENCY_QUARTERLY)
        self.assertEqual(workflow["period_month"], current_quarter_end_month)
        self.assertTrue(workflow["has_current_period_record"])
        self.assertEqual(workflow["current_period_entry_count"], 1)
        self.assertEqual(workflow["current_period_transaction_detail_count"], 2)
        self.assertEqual(workflow["overall_status"], "ready")
        self.assertEqual(workflow["schedule_items"][0]["status"], "ready")

    def test_client_workflow_tracks_monthly_and_quarterly_records_separately(self):
        today = timezone.localdate()
        current_quarter_end_month = (((today.month - 1) // 3) + 1) * 3
        previous_quarter_end_month = current_quarter_end_month - 3
        previous_quarter_year = today.year
        if previous_quarter_end_month <= 0:
            previous_quarter_end_month += 12
            previous_quarter_year -= 1

        owner = self._create_bookkeeper("owner-mixed-workflow")
        client = self._create_client(
            bookkeeper=owner,
            suffix="mixed-workflow",
            remarks=Client.REMARK_ACTIVE,
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(today.year, today.month, 1),
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
            lines=[
                ("Sales", "Monthly sales", Decimal("9000.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(previous_quarter_year, previous_quarter_end_month, 1),
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
            lines=[
                ("Expenses", "Quarterly expense", Decimal("4200.00")),
                ("2551Q", "Quarterly tax", Decimal("800.00")),
            ],
        )

        self._login_as(owner)
        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        workflow = response.json()["client_workflow"]
        items_by_frequency = {
            item["frequency"]: item
            for item in workflow["schedule_items"]
        }

        self.assertEqual(len(items_by_frequency), 2)
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_MONTHLY]["status"], "ready")
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_MONTHLY]["period_month"], today.month)
        expected_quarterly_status = "missing" if today.month == current_quarter_end_month else "upcoming"
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_QUARTERLY]["status"], expected_quarterly_status)
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_QUARTERLY]["period_month"], current_quarter_end_month)

    def test_client_workflow_uses_next_missing_period_after_saved_history(self):
        owner = self._create_bookkeeper("owner-backlog-workflow")
        client = self._create_client(
            bookkeeper=owner,
            suffix="backlog-workflow",
            remarks=Client.REMARK_NEW,
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(2026, 1, 1),
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
            lines=[
                ("Sales", "January monthly sales", Decimal("700.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(2026, 1, 1),
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
            lines=[
                ("2551Q", "January quarterly tax", Decimal("200.00")),
            ],
        )

        self._login_as(owner)
        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        workflow = response.json()["client_workflow"]
        items_by_frequency = {
            item["frequency"]: item
            for item in workflow["schedule_items"]
        }

        self.assertEqual(workflow["overall_status"], "missing")
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_MONTHLY]["period_year"], 2026)
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_MONTHLY]["period_month"], 2)
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_MONTHLY]["status"], "missing")
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_QUARTERLY]["period_year"], 2026)
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_QUARTERLY]["period_month"], 3)
        self.assertEqual(items_by_frequency[FinancialRecord.FREQUENCY_QUARTERLY]["status"], "missing")

    def test_analytics_summary_includes_historical_totals_and_numeric_tax_codes(self):
        today = timezone.localdate()
        history_year = today.year if today.month > 8 else today.year - 1
        history_month = today.month - 8 if today.month > 8 else today.month + 4

        owner = self._create_bookkeeper("owner-history")
        self._login_as(owner)

        client = self._create_client(bookkeeper=owner, suffix="history", remarks=Client.REMARK_ACTIVE)

        # Older record should still contribute to totals, even if it is outside the 6-month trend window.
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(history_year, history_month, 1),
            lines=[
                ("Sales", "Legacy sale", Decimal("100.00")),
                ("1701Q", "Quarterly return", Decimal("40.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=today,
            lines=[
                ("Sales", "Current sale", Decimal("60.00")),
                ("Expenses", "Current expense", Decimal("10.00")),
            ],
        )

        response = self.client.get(reverse("api_analytics_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["summary"]["total_sales"], 160.0)
        self.assertEqual(payload["summary"]["total_tax"], 40.0)
        self.assertEqual(payload["summary"]["net_value"], 150.0)

        monthly_trend = payload.get("monthly_trend", [])
        trend_sales_sum = sum(float(row.get("sales", 0.0)) for row in monthly_trend)
        trend_tax_sum = sum(float(row.get("tax", 0.0)) for row in monthly_trend)
        self.assertEqual(trend_sales_sum, 60.0)
        self.assertEqual(trend_tax_sum, 0.0)

    def test_analytics_predictive_forecast_respects_mixed_frequencies(self):
        today = timezone.localdate()
        forecast_year = today.year

        owner = self._create_bookkeeper("owner-mixed-forecast")
        self._login_as(owner)

        client = self._create_client(bookkeeper=owner, suffix="mixed-forecast", remarks=Client.REMARK_NEW)

        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(forecast_year, 4, 1),
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
            lines=[("Sales", "Monthly sale Apr", Decimal("100.00"))],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(forecast_year, 5, 1),
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
            lines=[("Sales", "Monthly sale May", Decimal("200.00"))],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(forecast_year, 6, 1),
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
            lines=[("Sales", "Monthly sale Jun", Decimal("300.00"))],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(forecast_year, 3, 1),
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
            lines=[("Expenses", "Quarterly expense Mar", Decimal("120.00"))],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(forecast_year, 6, 1),
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
            lines=[
                ("Expenses", "Quarterly expense Jun", Decimal("50.00")),
                ("BIR Form 2551Qv2018", "Quarterly Percentage Tax Return", Decimal("10.00")),
                ("BIR Form 1701", "Annual Income Tax Return", Decimal("1000.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(forecast_year, 1, 1),
            frequency=FinancialRecord.FREQUENCY_ANNUALLY,
            lines=[("Expenses", "Annual permit expense", Decimal("1200.00"))],
        )

        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        forecast = payload.get("predictive_forecast", {})
        self.assertFalse(forecast.get("has_forecast"))
        self.assertEqual(forecast.get("frequency"), "mixed")
        self.assertEqual(forecast.get("frequency_label"), "Mixed Schedule")
        self.assertEqual(forecast.get("next_period_label"), f"Jul {forecast_year}")
        self.assertIn("SARIMA", forecast.get("basis", ""))
        self.assertIn("minimum-history requirement", forecast.get("basis", ""))

        projections = forecast.get("future_projections", [])
        self.assertEqual(len(projections), 3)

        self.assertEqual(projections[0]["period_label"], f"Jul {forecast_year}")
        self.assertIsNone(projections[0]["expected_sales"])
        self.assertIsNone(projections[0]["expected_expenses"])
        self.assertIsNone(projections[0]["expected_tax"])
        self.assertFalse(projections[0]["expected_expenses_applicable"])
        self.assertFalse(projections[0]["expected_tax_applicable"])
        self.assertTrue(projections[0]["sales_unreliable"])
        self.assertEqual(projections[0]["sales_readiness_note"], "3 of 24 monthly records")
        self.assertEqual(projections[0]["expenses_readiness_note"], "Not scheduled this period")
        self.assertEqual(projections[0]["tax_readiness_note"], "Not scheduled this period")
        self.assertIsNone(projections[0]["expected_net"])

        self.assertEqual(projections[1]["period_label"], f"Aug {forecast_year}")
        self.assertIsNone(projections[1]["expected_sales"])
        self.assertIsNone(projections[1]["expected_expenses"])
        self.assertIsNone(projections[1]["expected_tax"])
        self.assertIsNone(projections[1]["expected_net"])

        self.assertEqual(projections[2]["period_label"], f"Sep {forecast_year}")
        self.assertIsNone(projections[2]["expected_sales"])
        self.assertIsNone(projections[2]["expected_expenses"])
        self.assertTrue(projections[2]["expected_expenses_applicable"])
        self.assertTrue(projections[2]["expenses_unreliable"])
        self.assertIsNone(projections[2]["expected_tax"])
        self.assertEqual(projections[2]["tax_method"], "SARIMA")
        self.assertTrue(projections[2]["tax_limited_data"])
        self.assertFalse(projections[2]["expected_net_applicable"])
        self.assertTrue(projections[2]["expected_net_unreliable"])
        self.assertIsNone(projections[2]["expected_net"])

    def test_analytics_summary_exposes_tin_for_disambiguation_and_scope(self):
        today = timezone.localdate()

        owner = self._create_bookkeeper("owner-tin")
        self._login_as(owner)

        same_tin_a = self._build_tin("same-001")
        same_tin_b = self._build_tin("same-002")

        client_a = Client.objects.create(
            bookkeeper=owner,
            client_name="Same Name Client",
            tin_number=same_tin_a,
            trade_name="Trade A",
            location="Panabo",
            permit_number="PERMIT-SAME-001",
            email="same-a@example.com",
            remarks=Client.REMARK_NEW,
        )
        client_b = Client.objects.create(
            bookkeeper=owner,
            client_name="Same Name Client",
            tin_number=same_tin_b,
            trade_name="Trade B",
            location="Panabo",
            permit_number="PERMIT-SAME-002",
            email="same-b@example.com",
            remarks=Client.REMARK_ACTIVE,
        )

        self._create_record_with_lines(
            bookkeeper=owner,
            client=client_a,
            entry_date=today,
            lines=[("Sales", "Client A sale", Decimal("150.00"))],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client_b,
            entry_date=today,
            lines=[("Sales", "Client B sale", Decimal("250.00"))],
        )

        all_clients_response = self.client.get(reverse("api_analytics_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(all_clients_response.status_code, 200)
        all_clients_payload = all_clients_response.json()

        available_clients = all_clients_payload.get("available_clients", [])
        same_name_rows = [
            row
            for row in available_clients
            if row.get("client_name") == "Same Name Client"
        ]
        self.assertEqual(len(same_name_rows), 2)
        self.assertEqual(
            {row.get("tin_number") for row in same_name_rows},
            {same_tin_a, same_tin_b},
        )

        scoped_response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client_b.id},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(scoped_response.status_code, 200)
        scoped_payload = scoped_response.json()

        self.assertEqual(scoped_payload["scope"]["client_id"], client_b.id)
        self.assertEqual(scoped_payload["scope"]["client_tin"], same_tin_b)

    def test_analytics_sarima_forecasting_logic(self):
        today = timezone.localdate()

        owner = self._create_bookkeeper("owner-sarima")
        self._login_as(owner)

        client = self._create_client(bookkeeper=owner, suffix="sarima", remarks=Client.REMARK_ACTIVE)

        end_index = (today.year * 12) + (today.month - 1)
        start_index = end_index - 23
        for index in range(24):
            month_index = start_index + index
            entry_date = date(month_index // 12, (month_index % 12) + 1, 1)
            self._create_record_with_lines(
                bookkeeper=owner,
                client=client,
                entry_date=entry_date,
                frequency=FinancialRecord.FREQUENCY_MONTHLY,
                lines=[
                    ("Sales", f"Sales {index + 1}", Decimal(100 + (index * 10))),
                    ("Expenses", f"Expense {index + 1}", Decimal(10 + index)),
                    ("2550M", f"Monthly VAT Tax {index + 1}", Decimal("5.0") + (Decimal("0.5") * index)),
                ],
            )

        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        forecast = payload.get("predictive_forecast", {})
        self.assertTrue(forecast.get("has_forecast"))
        self.assertEqual(forecast.get("frequency"), FinancialRecord.FREQUENCY_MONTHLY)
        self.assertEqual(forecast.get("data_points"), 24)

        self.assertIn("SARIMA (0,1,0)(0,1,0)", forecast.get("basis", ""))
        self.assertEqual(forecast.get("sales_method"), "SARIMA")

        self.assertEqual(forecast.get("expected_sales"), 340.0)
        self.assertEqual(forecast.get("expected_expenses"), 34.0)
        self.assertEqual(forecast.get("expected_tax"), 17.0)
        self.assertEqual(forecast.get("expected_net"), 306.0)

        # Assert 3 future projections
        projections = forecast.get("future_projections", [])
        self.assertEqual(len(projections), 3)

        self.assertEqual(projections[0]["expected_sales"], 340.0)
        self.assertEqual(projections[0]["expected_expenses"], 34.0)
        self.assertEqual(projections[0]["expected_tax"], 17.0)
        self.assertEqual(projections[0]["expected_net"], 306.0)

        self.assertEqual(projections[1]["expected_sales"], 350.0)
        self.assertEqual(projections[1]["expected_expenses"], 35.0)
        self.assertEqual(projections[1]["expected_tax"], 17.5)
        self.assertEqual(projections[1]["expected_net"], 315.0)

        self.assertEqual(projections[2]["expected_sales"], 360.0)
        self.assertEqual(projections[2]["expected_expenses"], 36.0)
        self.assertEqual(projections[2]["expected_tax"], 18.0)
        self.assertEqual(projections[2]["expected_net"], 324.0)

    def test_sarima_keeps_recorded_expense_frequency_and_generic_taxes_label(self):
        owner = self._create_bookkeeper("owner-sarima-quarterly")
        self._login_as(owner)
        client = self._create_client(
            bookkeeper=owner,
            suffix="sarima-quarterly",
            remarks=Client.REMARK_ACTIVE,
        )

        for index in range(24):
            month_index = (2024 * 12) + index
            entry_date = date(month_index // 12, (month_index % 12) + 1, 1)
            self._create_record_with_lines(
                bookkeeper=owner,
                client=client,
                entry_date=entry_date,
                frequency=FinancialRecord.FREQUENCY_MONTHLY,
                lines=[("SALES", "Recorded sales", Decimal(1000 + (index * 10)))],
            )

        quarter_dates = [
            date(year, month, 1)
            for year in (2024, 2025)
            for month in (3, 6, 9, 12)
        ]
        for index, entry_date in enumerate(quarter_dates):
            expense_frequency = (
                FinancialRecord.FREQUENCY_MONTHLY
                if entry_date == date(2024, 12, 1)
                else FinancialRecord.FREQUENCY_QUARTERLY
            )
            self._create_record_with_lines(
                bookkeeper=owner,
                client=client,
                entry_date=entry_date,
                frequency=expense_frequency,
                lines=[(
                    "EXPENSES",
                    "It's TAXES" if entry_date == date(2024, 12, 1) else "Recorded expenses",
                    Decimal(100 + (index * 10)),
                )],
            )
            self._create_record_with_lines(
                bookkeeper=owner,
                client=client,
                entry_date=entry_date,
                frequency=FinancialRecord.FREQUENCY_QUARTERLY,
                lines=[("TAXES", "Recorded taxes", Decimal(10 + index))],
            )

        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["summary"]["total_tax"], 108.0)
        forecast = payload["predictive_forecast"]
        projections = forecast["future_projections"]

        self.assertTrue(forecast["has_forecast"])
        self.assertEqual(projections[0]["period_label"], "Jan 2026")
        self.assertTrue(projections[0]["expected_expenses_applicable"])
        self.assertIsNone(projections[0]["expected_expenses"])
        self.assertTrue(projections[0]["expenses_unreliable"])
        self.assertFalse(projections[0]["expected_tax_applicable"])
        self.assertEqual(
            projections[0]["expenses_readiness_note"],
            "1 of 24 monthly records",
        )

        self.assertEqual(projections[2]["period_label"], "Mar 2026")
        self.assertTrue(projections[2]["expected_expenses_applicable"])
        self.assertIsNone(projections[2]["expected_expenses"])
        self.assertTrue(projections[2]["expenses_unreliable"])
        self.assertEqual(
            projections[2]["expenses_readiness_note"],
            "Review missing quarterly periods; 1 of 24 monthly records",
        )
        self.assertTrue(projections[2]["expected_tax_applicable"])
        self.assertIsNotNone(projections[2]["expected_tax"])
        self.assertEqual(projections[2]["tax_readiness_note"], "SARIMA")

    def test_sarima_api_preserves_quarterly_series_anchor(self):
        owner = self._create_bookkeeper("owner-sarima-anchor")
        self._login_as(owner)
        client = self._create_client(
            bookkeeper=owner,
            suffix="sarima-anchor",
            remarks=Client.REMARK_ACTIVE,
        )

        quarter_dates = [
            date(year, month, 1)
            for year in (2024, 2025)
            for month in (1, 4, 7, 10)
        ]
        for index, entry_date in enumerate(quarter_dates):
            self._create_record_with_lines(
                bookkeeper=owner,
                client=client,
                entry_date=entry_date,
                frequency=FinancialRecord.FREQUENCY_QUARTERLY,
                lines=[(
                    "EXPENSES",
                    "Quarterly expense",
                    Decimal(100 + (index * 10)),
                )],
            )

        response = self.client.get(
            reverse("api_analytics_summary"),
            {"client_id": client.id, "horizon": 3},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)

        forecast = response.json()["predictive_forecast"]
        projections = forecast["future_projections"]
        self.assertTrue(forecast["has_forecast"])
        self.assertEqual(
            [row["period_label"] for row in projections],
            ["Nov 2025", "Dec 2025", "Jan 2026"],
        )
        self.assertFalse(projections[0]["expected_expenses_applicable"])
        self.assertFalse(projections[1]["expected_expenses_applicable"])
        self.assertTrue(projections[2]["expected_expenses_applicable"])
        self.assertEqual(projections[2]["expected_expenses"], 180.0)
        self.assertEqual(projections[2]["expenses_readiness_note"], "SARIMA")

