"""Tax composition is descriptive, year-scoped, and independent of forecasts."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from safebooks.models import Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.tests import test_analytics_summary_api as fixtures


class AnalyticsTaxBreakdownTests(TestCase):
    _create_bookkeeper = fixtures.AnalyticsSummaryApiTests._create_bookkeeper
    _login_as = fixtures.AnalyticsSummaryApiTests._login_as
    _build_tin = fixtures.AnalyticsSummaryApiTests._build_tin
    _create_client = fixtures.AnalyticsSummaryApiTests._create_client
    _create_record_with_lines = fixtures.AnalyticsSummaryApiTests._create_record_with_lines

    def setUp(self):
        self.owner = self._create_bookkeeper("tax-chart-owner")
        self.other = self._create_bookkeeper("tax-chart-other")
        self.ledger = self._create_client(bookkeeper=self.owner, suffix="tax-chart", remarks=Client.REMARK_ACTIVE)
        self.second = self._create_client(bookkeeper=self.owner, suffix="tax-chart-second", remarks=Client.REMARK_ACTIVE)
        self.private = self._create_client(bookkeeper=self.other, suffix="tax-chart-private", remarks=Client.REMARK_ACTIVE)
        self._login_as(self.owner)
        self.record(self.ledger, 2026, 1, [("BIR Form 0619E", "TW", Decimal("100.10")),
            ("Sales", "Sales", Decimal("75000")), ("Expenses", "Expenses", Decimal("5000"))])
        self.record(self.ledger, 2026, 3, [("BIR Form 0619E", "TW", Decimal("20.20")),
            ("BIR Form 2551Q", "PQ", Decimal("300")), ("Other", "income tax", Decimal("10"))])
        self.record(self.ledger, 2025, 1, [("BIR Form 0619E", "TW", Decimal("900"))])
        self.record(self.second, 2026, 1, [("BIR Form 0619E", "TW", Decimal("50"))])
        self.record(self.private, 2026, 1, [("BIR Form 0619E", "TW", Decimal("99999"))])
        # Supporting worksheet values must never increase the chart or Tax total.
        FinancialRecordLine.objects.filter(record__client=self.ledger).update(tax_withheld=Decimal("123"), mict=Decimal("456"))

    def record(self, client, year, month, lines):
        return self._create_record_with_lines(bookkeeper=client.bookkeeper, client=client,
            entry_date=date(year, month, 1), lines=lines)

    def read(self, client=None, year="2026"):
        query = {}
        if client is not None:
            query["client_id"] = client.id
        if year is not None:
            query["year"] = year
        return self.client.get(reverse("api_analytics_summary"), query, HTTP_ACCEPT="application/json")

    def test_selected_year_matches_tax_total_without_writes(self):
        before = {m.__name__: list(m.objects.values()) for m in (FinancialRecord, FinancialRecordLine, Period)}
        response = self.read(self.ledger)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tax_breakdown_year"], 2026)
        self.assertEqual(payload["tax_breakdown"], [
            {"type_code": "BIR Form 2551Q", "amount": 300.0},
            {"type_code": "BIR Form 0619E", "amount": 120.3},
            {"type_code": "Other", "amount": 10.0},
        ])
        self.assertEqual(sum(Decimal(str(r["amount"])) for r in payload["tax_breakdown"]), Decimal(str(payload["summary"]["total_tax"])))
        self.assertEqual(before, {m.__name__: list(m.objects.values()) for m in (FinancialRecord, FinancialRecordLine, Period)})
        self.assertContains(self.client.get(reverse("client_details", args=[self.ledger.id])), 'id="analyticsTaxBreakdown"')

    def test_all_clients_and_legacy_no_year_keep_existing_scope(self):
        payload = self.read().json()
        self.assertEqual(payload["summary"]["total_tax"], 480.3)
        self.assertEqual(payload["tax_breakdown"][1]["amount"], 170.3)
        legacy = self.read(self.ledger, year=None).json()
        self.assertIsNone(legacy["tax_breakdown_year"])
        self.assertEqual(legacy["summary"]["total_tax"], 1330.3)
        self.assertEqual(legacy["tax_breakdown"][0]["amount"], 1020.3)

    def test_empty_year_and_explicit_zero(self):
        payload = self.read(self.ledger, year="2024").json()
        self.assertEqual(payload["tax_breakdown"], [])
        self.record(self.ledger, 2024, 1, [("BIR Form 0619E", "TW", Decimal("0"))])
        payload = self.read(self.ledger, year="2024").json()
        self.assertEqual(payload["tax_breakdown"], [{"type_code": "BIR Form 0619E", "amount": 0.0}])

    def test_other_owner_scope_is_rejected(self):
        response = self.read(self.private)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("tax_breakdown", response.json())
