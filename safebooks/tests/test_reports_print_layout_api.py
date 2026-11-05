from safebooks.tests.session_helpers import bind_authenticated_session

from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class ReportsPrintLayoutApiTests(TestCase):
    def _create_bookkeeper(self, suffix: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Reports Print {suffix}",
            username=f"reports_print_{suffix}",
            email=f"reports_print_{suffix}@example.com",
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

    def _create_client(self, *, bookkeeper: BookkeeperAccount, suffix: str) -> Client:
        return Client.objects.create(
            bookkeeper=bookkeeper,
            client_name=f"Client {suffix}",
            tin_number=self._build_tin(f"pr-{suffix}"),
            trade_name=f"Trade {suffix}",
            location="Davao City",
            permit_number=f"PERMIT-PR-{suffix}",
            email=f"client-print-{suffix}@example.com",
        )

    def _create_record_with_lines(
        self,
        *,
        bookkeeper: BookkeeperAccount,
        client: Client,
        entry_date: date,
        lines: list[tuple[str, str, Decimal]],
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
            notes="Print layout test",
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

    def test_report_returns_each_lines_worksheet_values_without_writes(self):
        owner = self._create_bookkeeper("worksheet")
        client = self._create_client(bookkeeper=owner, suffix="worksheet")
        self._login_as(owner)
        record = self._create_record_with_lines(bookkeeper=owner, client=client, entry_date=date(2026, 3, 15), lines=[
            ("Sales", "Sales", Decimal("75000")), ("Expenses", "Expenses", Decimal("5000")),
            ("BIR Form 0619E", "TW", Decimal("500")), ("BIR Form 2551Q", "PQ", Decimal("2250")),
        ])
        first, second = list(record.line_items.order_by("sort_order"))[2:]
        first.mict = Decimal("0")
        first.income_payments_2307 = Decimal("9000")
        first.tax_withheld = Decimal("180")
        first.save()
        second.cogs_cos = Decimal("12500")
        second.save()
        before = list(record.line_items.order_by("pk").values())
        response = self.client.get(reverse("api_reports_print_layout"), {
            "client_id": client.id, "date_from": "2026-01-01", "date_to": "2026-12-31",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["total_amount"], "82750.00")
        rows = payload["rows"]
        self.assertEqual(rows[2]["mict"], "0.00")
        self.assertEqual(rows[2]["income_payments_2307"], "9000.00")
        self.assertEqual(rows[2]["tax_withheld"], "180.00")
        self.assertIsNone(rows[2]["cogs_cos"])
        self.assertEqual(rows[3]["cogs_cos"], "12500.00")
        self.assertIsNone(rows[3]["mict"])
        self.assertEqual(list(record.line_items.order_by("pk").values()), before)
        record.refresh_from_db()
        self.assertEqual(record.total_amount, Decimal("82750"))
        other = self._create_bookkeeper("worksheet-other")
        self._login_as(other)
        denied = self.client.get(reverse("api_reports_print_layout"), {
            "client_id": client.id, "date_from": "2026-01-01", "date_to": "2026-12-31",
        })
        self.assertEqual(denied.status_code, 404)
        self.assertNotIn("rows", denied.json())

    def test_net_sales_matches_saved_coverage_without_writes_or_extra_history(self):
        owner = self._create_bookkeeper("net-coverage")
        client = self._create_client(bookkeeper=owner, suffix="net-coverage")
        self._login_as(owner)
        for month, amount in ((1, "122000"), (2, "128000"), (3, "137500")):
            record = self._create_record_with_lines(bookkeeper=owner, client=client, entry_date=date(2026, month, 1),
                                                    lines=[("Sales", "Sales", Decimal(amount))])
            record.line_items.update(coverage_frequency="monthly")
        expense = self._create_record_with_lines(bookkeeper=owner, client=client, entry_date=date(2026, 3, 31), lines=[
            ("Expenses", "Expenses", Decimal("290500")), ("BIR Form 2551Q", "PQ", Decimal("6006")),
        ])
        expense.line_items.filter(type_code="Expenses").update(coverage_frequency="quarterly")
        self._create_record_with_lines(bookkeeper=owner, client=client, entry_date=date(2025, 3, 1),
                                       lines=[("Sales", "Older sale", Decimal("1000000"))])
        before_records = list(FinancialRecord.objects.values())
        before_lines = list(FinancialRecordLine.objects.values())
        before_periods = list(Period.objects.values())
        response = self.client.get(reverse("api_reports_print_layout"), {
            "client_id": client.id, "date_from": "2026-01-01", "date_to": "2026-12-31",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["total_amount"], "684006.00")
        self.assertEqual(len(payload["rows"]), 5)
        net = payload["worksheet_net_sales"]
        self.assertEqual(net["periods"]["2026-03"]["amount"], "97000.00")
        self.assertEqual(net["total"], "97000.00")
        self.assertNotIn("2025-03", net["periods"])
        partial = self.client.get(reverse("api_reports_print_layout"), {
            "client_id": client.id, "date_from": "2026-03-01", "date_to": "2026-03-31",
        }).json()["worksheet_net_sales"]
        self.assertIsNone(partial["total"], "A narrowed read must not fabricate the missing January/February sales")
        self.assertEqual(list(FinancialRecord.objects.values()), before_records)
        self.assertEqual(list(FinancialRecordLine.objects.values()), before_lines)
        self.assertEqual(list(Period.objects.values()), before_periods)

    def test_report_restores_existing_header_fields_without_credentials_or_profile_grants(self):
        owner = self._create_bookkeeper("header-fields")
        owner.client_details_password_required = True
        owner.save(update_fields=["client_details_password_required"])
        self._login_as(owner)
        client = self._create_client(bookkeeper=owner, suffix="header-fields")
        client.permit_number = "00519"
        client.birthday = date(1991, 2, 3)
        client.email = "worksheet-client@example.test"
        client.email_password = "SyntheticReportEmailSecret"
        client.orus_account = "SyntheticReportOrusLogin"
        client.orus_password = "SyntheticReportOrusSecret"
        client.custom_fields = [{"label": "Portal", "type": "password", "value": "SyntheticReportCustomSecret"}]
        client.save()
        before = list(Client.objects.filter(pk=client.pk).values())
        params = {"client_id": client.id, "date_from": "2026-01-01", "date_to": "2026-12-31",
                  "include_sensitive": "true"}
        response = self.client.get(reverse("api_reports_print_layout"), params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        header = response.json()["client"]
        self.assertEqual(header["permit_number"], "00519")
        self.assertEqual(header["birthday"], "1991-02-03")
        self.assertEqual(header["email"], "worksheet-client@example.test")
        for key in ("email_password", "orus_account", "orus_password"):
            self.assertEqual(header[key], "")
            self.assertNotContains(response, getattr(client, key))
        self.assertEqual(header["custom_fields"], [])
        self.assertNotContains(response, "SyntheticReportCustomSecret")
        self.assertEqual(response.json()["rows"], [], "An empty year must still have the saved client header")
        self.assertEqual(list(Client.objects.filter(pk=client.pk).values()), before)
        # A report read must neither unlock the profile nor expand directory/entry reads.
        self.assertEqual(self.client.get(reverse("api_client_detail", args=[client.id])).status_code, 403)
        for url, query in (
            (reverse("api_clients"), {}),
            (reverse("api_financial_record_clients"), {}),
            (reverse("api_financial_records", args=[client.id]), {"month": 1, "year": 2026}),
            (reverse("api_reports_print_layout"), {"client_id": client.id, "years_only": "1"}),
        ):
            directory_response = self.client.get(url, query)
            self.assertEqual(directory_response.status_code, 200)
            for value in ("00519", "1991-02-03", "worksheet-client@example.test", "SyntheticReportEmailSecret"):
                self.assertNotContains(directory_response, value)
        other = self._create_bookkeeper("foreign-header")
        self._login_as(other)
        denied = self.client.get(reverse("api_reports_print_layout"), params)
        self.assertEqual(denied.status_code, 404)
        self.assertNotContains(denied, "worksheet-client@example.test", status_code=404)

    def test_report_missing_header_values_stay_empty(self):
        owner = self._create_bookkeeper("empty-header")
        self._login_as(owner)
        client = self._create_client(bookkeeper=owner, suffix="empty-header")
        client.permit_number = ""
        client.email = ""
        client.birthday = None
        client.save()
        response = self.client.get(reverse("api_reports_print_layout"), {
            "client_id": client.id, "date_from": "2026-01-01", "date_to": "2026-12-31",
        })
        self.assertEqual(response.status_code, 200)
        for key in ("permit_number", "birthday", "email"):
            self.assertEqual(response.json()["client"][key], "")

    def test_reports_print_layout_requires_authentication(self):
        response = self.client.get(
            reverse("api_reports_print_layout"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Authentication required.")

    def test_client_report_header_uses_authenticated_bookkeeper_name(self):
        owner = self._create_bookkeeper("header")
        self._login_as(owner)

        response = self.client.get(reverse("clients"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'printedBy: "Reports Print header"')
        self.assertNotContains(
            response,
            "Client-facing format for quick review and print handover",
        )

        shared_script_path = finders.find("js/reports_shared.js")
        self.assertIsNotNone(shared_script_path)
        shared_script = Path(shared_script_path).read_text(encoding="utf-8")
        self.assertIn("Printed by:", shared_script)
        self.assertNotIn(
            "Client-facing format for quick review and print handover",
            shared_script,
        )

    def test_report_moves_to_financial_entry_page_with_year_choices(self):
        owner = self._create_bookkeeper("year-filter")
        owner.client_details_password_required = False
        owner.save(update_fields=["client_details_password_required"])
        self._login_as(owner)
        client = self._create_client(bookkeeper=owner, suffix="year-filter")

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="generateReportActionBtn"')
        self.assertNotContains(response, 'id="formattedReportModal"')
        response = self.client.get(reverse("financial_records_client"), {"client_id": client.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="generateReportActionBtn"')
        self.assertContains(response, 'id="formattedReportModal"')
        self.assertContains(response, 'id="modalReportYearFilter"')
        self.assertContains(response, "(Current Year)")
        self.assertContains(response, "All Years")
        self.assertContains(response, "Preview and print include only")

    def test_reports_print_layout_returns_transactions_for_date_range(self):
        owner = self._create_bookkeeper("owner")
        self._login_as(owner)

        client = self._create_client(bookkeeper=owner, suffix="A")

        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(2026, 1, 15),
            lines=[
                ("Sales", "January sale", Decimal("100.00")),
                ("Expenses", "January expense", Decimal("50.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(2026, 2, 10),
            lines=[
                ("Sales", "February sale", Decimal("75.00")),
            ],
        )
        self._create_record_with_lines(
            bookkeeper=owner,
            client=client,
            entry_date=date(2025, 12, 20),
            lines=[
                ("Sales", "Previous-year sale", Decimal("500.00")),
            ],
        )

        response = self.client.get(
            reverse("api_reports_print_layout"),
            {
                "client_id": client.id,
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
            },
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        summary = payload.get("summary", {})
        self.assertEqual(summary.get("entry_count"), 1)
        self.assertEqual(summary.get("line_item_count"), 2)
        self.assertEqual(summary.get("total_amount"), "150.00")

        rows = payload.get("rows", [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["entry_date"], "2026-01-15")
        self.assertEqual(rows[0]["type_code"], "Sales")
        self.assertEqual(rows[0]["amount"], "100.00")
        self.assertEqual(rows[1]["type_code"], "Expenses")
        self.assertEqual(rows[1]["amount"], "50.00")
        self.assertNotIn("Previous-year sale", {row["description"] for row in rows})
