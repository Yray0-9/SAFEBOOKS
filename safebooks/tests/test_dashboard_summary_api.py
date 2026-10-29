from safebooks.tests.session_helpers import bind_authenticated_session

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class DashboardSummaryApiTests(TestCase):
    def test_explicit_amount_coverage_controls_reminders_without_retagging_entry(self):
        owner = self._create_bookkeeper("coverage-reminder")
        ledger = self._create_client(bookkeeper=owner, tin_suffix="coverage-reminder", remarks=Client.REMARK_ACTIVE)
        self._login_as(owner)
        record = self._create_record(bookkeeper=owner, client=ledger, entry_date=date(2026, 3, 31), amount=Decimal("75000"))
        line = record.line_items.get()
        line.type_code = "Sales"
        line.description = "Sales"
        line.coverage_frequency = "quarterly"
        line.save()
        with patch("safebooks.services.dashboard_service.timezone.localdate", return_value=date(2026, 5, 1)):
            response = self.client.get(reverse("api_dashboard_summary"))
        self.assertEqual(response.status_code, 200, response.content)
        row = next(item for item in response.json()["recent_client_activity"] if item["client_id"] == ledger.id)
        self.assertEqual(row["status"], "updated")
        record.refresh_from_db()
        self.assertEqual(record.frequency, "monthly", "Reads must not rewrite the compatibility field")
        FinancialRecordLine.objects.create(record=record, type_code="Expenses", description="Expenses", amount=0, coverage_frequency="monthly")
        with patch("safebooks.services.dashboard_service.timezone.localdate", return_value=date(2026, 5, 1)):
            response = self.client.get(reverse("api_dashboard_summary"))
        row = next(item for item in response.json()["recent_client_activity"] if item["client_id"] == ledger.id)
        self.assertEqual(row["status"], "needs-attention", "A monthly component keeps monthly reminders")

    def _create_bookkeeper(self, suffix: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"bookkeeper_{suffix}",
            email=f"bookkeeper_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
        )

    def _login_as(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def _build_tin(self, token: str) -> str:
        digits = "".join(char for char in str(token or "") if char.isdigit())
        if digits:
            seed = int(digits)
        else:
            seed = sum(ord(char) for char in str(token or ""))
        return f"{seed:012d}"

    def _create_client(self, *, bookkeeper: BookkeeperAccount, tin_suffix: str, remarks: str) -> Client:
        return Client.objects.create(
            bookkeeper=bookkeeper,
            client_name=f"Client {tin_suffix}",
            tin_number=self._build_tin(tin_suffix),
            trade_name=f"Trade {tin_suffix}",
            location="Panabo City",
            permit_number=f"PERMIT-{tin_suffix}",
            email=f"client-{tin_suffix}@example.com",
            remarks=remarks,
        )

    def _create_record(
        self,
        *,
        bookkeeper: BookkeeperAccount,
        client: Client,
        entry_date: date,
        amount: Decimal,
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
            notes="Test note",
            total_amount=amount,
        )
        FinancialRecordLine.objects.create(
            record=record,
            type_code="1701",
            description="Income Tax",
            amount=amount,
            sort_order=1,
        )
        return record

    def test_dashboard_summary_requires_authentication(self):
        response = self.client.get(
            reverse("api_dashboard_summary"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Authentication required.")

    def test_dashboard_summary_returns_expected_metrics_and_summaries(self):
        today = timezone.localdate()
        previous_year = today.year if today.month > 1 else today.year - 1
        previous_month = today.month - 1 if today.month > 1 else 12

        owner = self._create_bookkeeper("owner-metrics")
        self._login_as(owner)

        client_updated = self._create_client(
            bookkeeper=owner,
            tin_suffix="updated",
            remarks=Client.REMARK_NEW,
        )
        client_pending = self._create_client(
            bookkeeper=owner,
            tin_suffix="pending",
            remarks=Client.REMARK_SEPARATED,
        )
        client_late = self._create_client(
            bookkeeper=owner,
            tin_suffix="late",
            remarks=Client.REMARK_CLOSED,
        )

        self._create_record(
            bookkeeper=owner,
            client=client_updated,
            entry_date=today,
            amount=Decimal("1200.00"),
        )
        self._create_record(
            bookkeeper=owner,
            client=client_pending,
            entry_date=date(previous_year, previous_month, 1),
            amount=Decimal("800.00"),
        )

        response = self.client.get(reverse("api_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload.get("ok"))

        self.assertEqual(payload["metrics"]["total_clients"], 3)
        self.assertEqual(payload["metrics"]["total_entries_this_month"], 1)
        self.assertEqual(payload["metrics"]["pending_compliance"], 1)
        self.assertEqual(payload["metrics"]["new_clients"], 1)

        self.assertEqual(payload["remarks_summary"]["new"], 1)
        self.assertEqual(payload["remarks_summary"]["active"], 0)
        self.assertEqual(payload["remarks_summary"]["separated"], 1)
        self.assertEqual(payload["remarks_summary"]["closed"], 1)

        self.assertEqual(payload["compliance_summary"]["filed"]["count"], 1)
        self.assertEqual(payload["compliance_summary"]["pending"]["count"], 1)
        self.assertEqual(payload["compliance_summary"]["late"]["count"], 0)
        self.assertEqual(payload["compliance_summary"]["filed"]["percentage"], 50)
        self.assertEqual(payload["compliance_summary"]["pending"]["percentage"], 50)
        self.assertEqual(payload["compliance_summary"]["late"]["percentage"], 0)

        activity_by_client_id = {
            row["client_id"]: row
            for row in payload.get("recent_client_activity", [])
        }
        self.assertEqual(activity_by_client_id[client_updated.id]["status"], "updated")
        self.assertEqual(activity_by_client_id[client_updated.id]["compliance"], "filed")
        self.assertIn("recent_activity_at", activity_by_client_id[client_updated.id])
        self.assertTrue(activity_by_client_id[client_updated.id]["recent_activity_at"])
        self.assertEqual(activity_by_client_id[client_pending.id]["status"], "needs-attention")
        self.assertEqual(activity_by_client_id[client_pending.id]["compliance"], "pending")
        self.assertNotIn(client_late.id, activity_by_client_id)

    def test_dashboard_summary_is_scoped_to_logged_in_bookkeeper(self):
        today = timezone.localdate()

        owner = self._create_bookkeeper("owner-scope")
        other = self._create_bookkeeper("other-scope")

        owner_client = self._create_client(
            bookkeeper=owner,
            tin_suffix="owner-visible",
            remarks=Client.REMARK_NEW,
        )
        other_client = self._create_client(
            bookkeeper=other,
            tin_suffix="other-hidden",
            remarks=Client.REMARK_CLOSED,
        )

        self._create_record(
            bookkeeper=owner,
            client=owner_client,
            entry_date=today,
            amount=Decimal("300.00"),
        )
        self._create_record(
            bookkeeper=other,
            client=other_client,
            entry_date=today,
            amount=Decimal("999.00"),
        )

        self._login_as(owner)
        response = self.client.get(reverse("api_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["metrics"]["total_clients"], 1)
        self.assertEqual(payload["metrics"]["total_entries_this_month"], 1)
        self.assertEqual(payload["metrics"]["new_clients"], 1)

        activity_client_ids = {row["client_id"] for row in payload.get("recent_client_activity", [])}
        self.assertEqual(activity_client_ids, {owner_client.id})

        recent_entry_client_ids = {row["client_id"] for row in payload.get("recent_entries", [])}
        self.assertEqual(recent_entry_client_ids, {owner_client.id})

    def test_dashboard_summary_recent_entries_are_limited_and_sorted_desc(self):
        today = timezone.localdate()

        owner = self._create_bookkeeper("owner-recent")
        self._login_as(owner)
        client = self._create_client(
            bookkeeper=owner,
            tin_suffix="recent-client",
            remarks=Client.REMARK_ACTIVE,
        )

        for day in range(1, 8):
            self._create_record(
                bookkeeper=owner,
                client=client,
                entry_date=date(today.year, today.month, day),
                amount=Decimal("100.00") + Decimal(day),
            )

        response = self.client.get(reverse("api_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        recent_entries = payload.get("recent_entries", [])
        self.assertEqual(len(recent_entries), 5)

        recent_dates = [row["entry_date"] for row in recent_entries]
        expected_dates = [
            date(today.year, today.month, day).isoformat()
            for day in range(7, 2, -1)
        ]
        self.assertEqual(recent_dates, expected_dates)

    def test_dashboard_summary_includes_deadline_metrics_and_days_remaining(self):
        today = timezone.localdate()
        owner = self._create_bookkeeper("owner-deadline-dash")
        self._login_as(owner)
        client = self._create_client(
            bookkeeper=owner,
            tin_suffix="deadline-client",
            remarks=Client.REMARK_ACTIVE,
        )

        record = self._create_record(
            bookkeeper=owner,
            client=client,
            entry_date=today,
            amount=Decimal("150.00"),
        )
        # Set deadline date to next month -> not completed yet
        next_month_date = date(today.year, today.month + 1, 5) if today.month < 12 else date(today.year + 1, 1, 5)
        record.deadline_date = next_month_date
        record.save()

        # Before making next month's entry -> deadline_completed is False
        response = self.client.get(reverse("api_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        activity = payload.get("recent_client_activity", [])
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0]["deadline_date"], record.deadline_date.isoformat())
        self.assertFalse(activity[0]["deadline_completed"])

        # Set deadline date to current month -> should be completed immediately because of the current month record!
        record.deadline_date = today
        record.save()

        response2 = self.client.get(reverse("api_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response2.status_code, 200)
        payload2 = response2.json()
        activity2 = payload2.get("recent_client_activity", [])
        self.assertTrue(activity2[0]["deadline_completed"])

    def test_dashboard_summary_keeps_quarterly_clients_out_of_attention_until_next_cycle(self):
        today = timezone.localdate()
        entry_month = today.month - 2
        entry_year = today.year
        if entry_month <= 0:
            entry_month += 12
            entry_year -= 1

        owner = self._create_bookkeeper("owner-quarterly")
        self._login_as(owner)
        client = self._create_client(
            bookkeeper=owner,
            tin_suffix="quarterly-client",
            remarks=Client.REMARK_ACTIVE,
        )

        record = self._create_record(
            bookkeeper=owner,
            client=client,
            entry_date=date(entry_year, entry_month, 1),
            amount=Decimal("500.00"),
        )
        record.frequency = FinancialRecord.FREQUENCY_QUARTERLY
        record.deadline_date = None
        record.save(update_fields=["frequency", "deadline_date"])

        response = self.client.get(reverse("api_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        activity = payload.get("recent_client_activity", [])
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0]["client_id"], client.id)
        self.assertEqual(activity[0]["status"], "updated")
        self.assertEqual(activity[0]["compliance"], "filed")
        self.assertEqual(payload["metrics"]["pending_compliance"], 0)
