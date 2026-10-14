"""Synthetic query budgets; never run against the user's configured database."""
from datetime import date
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.services.analytics_service import get_analytics_summary_for_bookkeeper
from safebooks.services.client_service import list_clients_for_bookkeeper
from safebooks.services.dashboard_service import get_dashboard_summary_for_bookkeeper
from safebooks.services.financial_record_service import (
    list_financial_clients_for_bookkeeper, list_records_for_client_period,
    list_transactions_for_client_range,
)


class QueryGrowthTests(TestCase):
    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(
            full_name="Query Test", username="query_test", email="query-test@example.com",
            password_hash="synthetic-unused", status=BookkeeperAccount.STATUS_APPROVED,
            client_details_password_required=False,
        )
        self.serial = 0

    def make_client(self):
        self.serial += 1
        return Client.objects.create(
            bookkeeper=self.owner, client_name=f"Query Client {self.serial}",
            tin_number=f"{self.serial:012d}", location="Synthetic location",
        )

    def make_record(self, client, *, entry_date=date(2026, 9, 3), deadline=date(2026, 10, 15)):
        period, _ = Period.objects.get_or_create(client=client, year=entry_date.year, month=entry_date.month)
        record = FinancialRecord.objects.create(
            bookkeeper=self.owner, client=client, period=period, entry_date=entry_date,
            deadline_date=deadline, total_amount=Decimal("3.00"),
        )
        # Insert out of order to prove that reusing prefetch preserves model order.
        FinancialRecordLine.objects.create(record=record, type_code="Expenses", description="Second", amount=2, sort_order=2)
        FinancialRecordLine.objects.create(record=record, type_code="Sales", description="First", amount=1, sort_order=1)
        return record

    def capture(self, operation):
        with CaptureQueriesContext(connection) as queries:
            result = operation()
        self.assertTrue(result["ok"], result.get("message"))
        return result, len(queries)

    def test_record_list_query_count_is_constant_and_totals_order_are_preserved(self):
        client = self.make_client()
        self.make_record(client)
        operation = lambda: list_records_for_client_period(self.owner, client.id, "all")
        small, before = self.capture(operation)
        for _ in range(29):
            self.make_record(client)
        large, after = self.capture(operation)
        self.assertEqual(before, after)
        self.assertLessEqual(after, 7)
        self.assertEqual(large["summary"]["total_amount"], "90.00")
        self.assertEqual(large["summary"]["line_item_count"], 60)
        self.assertEqual([line["description"] for line in large["records"][0]["line_items"]], ["First", "Second"])
        self.assertFalse(small["records"][0]["deadline_completed"])
        print(f"Record-list query budget: 1 vs 30 records = {before} vs {after} queries")

    def test_report_query_count_is_constant_and_includes_every_detail(self):
        client = self.make_client()
        self.make_record(client)
        operation = lambda: list_transactions_for_client_range(self.owner, client.id, "2026-01-01", "2026-12-31")
        _, before = self.capture(operation)
        for _ in range(29):
            self.make_record(client)
        payload, after = self.capture(operation)
        self.assertEqual(before, after)
        self.assertLessEqual(after, 4)
        self.assertEqual(payload["summary"]["total_amount"], "90.00")
        self.assertEqual(len(payload["rows"]), 60)
        self.assertEqual([row["description"] for row in payload["rows"][:2]], ["First", "Second"])
        print(f"Report query budget: 1 vs 30 records = {before} vs {after} queries")

    def test_directories_and_dashboard_do_not_query_each_deadline(self):
        self.make_record(self.make_client())
        operations = [
            lambda: get_dashboard_summary_for_bookkeeper(self.owner),
            lambda: list_financial_clients_for_bookkeeper(self.owner),
            lambda: list_clients_for_bookkeeper(self.owner),
        ]
        before = [self.capture(operation)[1] for operation in operations]
        for _ in range(29):
            self.make_record(self.make_client())
        after = [self.capture(operation)[1] for operation in operations]
        self.assertEqual(before, after)
        self.assertEqual(after, [3, 1, 1])
        print(f"Dashboard/financial-directory/client-directory: 1 vs 30 clients = {before} vs {after} queries")

    def test_deadline_completion_uses_all_owned_periods_not_only_selected_period(self):
        client = self.make_client()
        self.make_record(client)
        self.make_record(client, entry_date=date(2026, 10, 1), deadline=None)
        payload = list_records_for_client_period(self.owner, client.id, 9, 2026)
        self.assertTrue(payload["records"][0]["deadline_completed"])
        self.assertEqual(payload["summary"]["total_amount"], "3.00")

    def test_other_owners_records_cannot_complete_deadlines_or_change_directory_counts(self):
        client = self.make_client()
        self.make_record(client)
        other = BookkeeperAccount.objects.create(
            full_name="Other", username="query_other", email="query-other@example.com",
            password_hash="synthetic-unused", status=BookkeeperAccount.STATUS_APPROVED,
        )
        # Deliberately inconsistent legacy fixture: every calculation must still scope ownership.
        FinancialRecord.objects.create(
            bookkeeper=other, client=client, period=client.periods.first(),
            entry_date=date(2026, 10, 1), total_amount=99,
        )
        payload = list_records_for_client_period(self.owner, client.id, "all")
        self.assertFalse(payload["records"][0]["deadline_completed"])
        directory = list_financial_clients_for_bookkeeper(self.owner)["clients"][0]
        self.assertEqual(directory["financial_record_count"], 1)
        self.assertFalse(directory["deadline_completed"])
        dashboard = get_dashboard_summary_for_bookkeeper(self.owner)
        self.assertFalse(dashboard["recent_client_activity"][0]["deadline_completed"])

    def test_analytics_query_count_is_constant_for_record_growth(self):
        client = self.make_client()
        self.make_record(client)
        operation = lambda: get_analytics_summary_for_bookkeeper(self.owner, client.id)
        _, before = self.capture(operation)
        for _ in range(29):
            self.make_record(client)
        payload, after = self.capture(operation)
        self.assertEqual(before, after)
        self.assertLessEqual(after, 5)
        self.assertEqual(payload["summary"]["total_sales"], 30.0)
        self.assertEqual(payload["summary"]["total_expenses"], 60.0)
        print(f"Analytics query budget: 1 vs 30 records = {before} vs {after} queries")

    def test_previous_frequencies_are_distinct_without_ordering_columns(self):
        client = self.make_client()
        for day in range(1, 4):
            self.make_record(client, entry_date=date(2026, 8, day))
        payload = list_records_for_client_period(self.owner, client.id, 9, 2026)
        self.assertEqual(payload["prior_frequencies"], ["monthly"])
