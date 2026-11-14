from safebooks.tests.session_helpers import bind_authenticated_session

import json
from datetime import date
from decimal import Decimal

from django.core import mail
from django.test import TransactionTestCase
from django.test import override_settings
from django.urls import reverse

from safebooks.models import (
    BookkeeperAccount,
    Client,
    FinancialRecord,
    FinancialRecordLine,
    Period,
)
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="SafeBooks <no-reply@safebooks.test>",
    SAFEBOOKS_CLIENT_RECORD_EMAILS_ENABLED=True,
)
class FinancialRecordsApiTests(TransactionTestCase):
    def _create_bookkeeper(self, suffix: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"fin_{suffix}",
            email=f"fin_{suffix}@example.com",
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
            tin_number=self._build_tin(f"fin-{suffix}"),
            trade_name=f"Trade {suffix}",
            location="Panabo City",
            permit_number=f"PERMIT-FIN-{suffix}",
            email=f"client-fin-{suffix}@example.com",
            remarks=Client.REMARK_ACTIVE,
        )

    def _create_record(
        self,
        *,
        bookkeeper: BookkeeperAccount,
        client: Client,
        year: int,
        month: int,
        day: int,
        amount: Decimal,
        type_code: str = "1701",
        frequency: str = FinancialRecord.FREQUENCY_MONTHLY,
    ) -> FinancialRecord:
        period, _ = Period.objects.get_or_create(client=client, year=year, month=month)
        record = FinancialRecord.objects.create(
            bookkeeper=bookkeeper,
            client=client,
            period=period,
            entry_date=date(year, month, day),
            frequency=frequency,
            notes="Existing record",
            total_amount=amount,
        )
        FinancialRecordLine.objects.create(
            record=record,
            type_code=type_code,
            description="Line item",
            amount=amount,
            sort_order=1,
        )
        return record

    def _build_create_payload(self) -> dict:
        return {
            "month": 4,
            "year": 2026,
            "date": "2026-04-15",
            "frequency": "quarterly",
            "notes": "Created via test",
            "line_items": [
                {
                    "type_code": "Sales",
                    "description": "Primary sale",
                    "amount": "1000.00",
                },
                {
                    "type_code": "1701",
                    "description": "Tax",
                    "amount": "120.00",
                },
            ],
        }

    def test_separate_coverage_survives_create_edit_copy_and_report(self):
        owner = self._create_bookkeeper("coverage")
        ledger = self._create_client(bookkeeper=owner, suffix="coverage")
        self._login_as(owner)
        url = reverse("api_financial_records", kwargs={"client_id": ledger.id})
        payload = {"date": "2026-03-31", "line_items": [
            {"type_code": "Sales", "description": "Saved sales", "amount": "75000", "coverage_frequency": "monthly"},
            {"type_code": "Expenses", "description": "Saved expenses", "amount": "5000", "coverage_frequency": "quarterly"},
            {"type_code": "BIR Form 2551Q", "description": "PQ", "amount": "500", "remarks": "Paid", "cogs_cos": "0"},
        ]}
        created = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(created.status_code, 201, created.content)
        record = created.json()["record"]
        self.assertEqual(record["total_amount"], "80500.00")
        self.assertEqual([line["coverage_frequency"] for line in record["line_items"]], ["monthly", "quarterly", None])
        self.assertIn("mixed financial entry", mail.outbox[-1].body)
        self.assertIn("Monthly", mail.outbox[-1].alternatives[0].content)
        self.assertIn("Quarterly", mail.outbox[-1].alternatives[0].content)
        detail = reverse("api_financial_record_detail", kwargs={"client_id": ledger.id, "record_id": record["id"]})
        update = {"date": record["date"], "expected_revision": record["revision"], "line_items": [
            {**line, "client_line_id": str(line["id"])} for line in record["line_items"]
        ]}
        update["line_items"][0]["coverage_frequency"] = "quarterly"
        edited = self.client.patch(detail, json.dumps(update), content_type="application/json")
        self.assertEqual(edited.status_code, 200, edited.content)
        current = edited.json()["record"]
        self.assertEqual([line["coverage_frequency"] for line in current["line_items"]], ["quarterly", "quarterly", None])
        self.assertEqual(current["total_amount"], record["total_amount"])
        copied = self.client.get(reverse("api_financial_records_last_entry", kwargs={"client_id": ledger.id}),
                                 {"year": 2026, "month": 6, "frequency": "all"}).json()["record"]
        self.assertEqual(copied["line_items"], current["line_items"])
        report = self.client.get(reverse("api_reports_print_layout"),
                                 {"client_id": ledger.id, "date_from": "2026-01-01", "date_to": "2026-12-31"}).json()
        self.assertTrue(report["ok"], report)
        self.assertEqual([line["coverage_frequency"] for line in report["rows"]], ["quarterly", "quarterly", None])
        self.assertEqual(report["rows"][2]["remarks"], "Paid")
        self.assertEqual(report["rows"][2]["cogs_cos"], "0.00")
        self.assertEqual(FinancialRecord.objects.get(pk=record["id"]).total_amount, Decimal("80500.00"))
        # A stale editor cannot overwrite the explicit per-line coverage.
        stale = self.client.patch(detail, json.dumps(update), content_type="application/json")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "stale_record")
        old_payload = {"expected_revision": current["revision"], "line_items": payload["line_items"]}
        del old_payload["line_items"][0]["coverage_frequency"]
        rejected = self.client.patch(detail, json.dumps(old_payload), content_type="application/json")
        self.assertFalse(rejected.json()["ok"])
        self.assertEqual(rejected.json()["code"], "coverage_required")

    def test_invalid_coverage_and_wrong_end_month_do_not_write(self):
        owner = self._create_bookkeeper("bad-coverage")
        ledger = self._create_client(bookkeeper=owner, suffix="bad-coverage")
        self._login_as(owner)
        url = reverse("api_financial_records", kwargs={"client_id": ledger.id})
        for coverage, month in [(True, 3), ({}, 3), ([], 3), ("weekly", 3), ("", 3),
                                ("quarterly", 2), ("quarterly", 10), ("quarterly", 11), ("annually", 3)]:
            with self.subTest(coverage=coverage, month=month):
                category = "Expenses" if month == 11 else "Sales"
                payload = {"date": f"2026-{month:02d}-01", "line_items": [
                    {"type_code": category, "description": category, "amount": "0", "coverage_frequency": coverage}
                ]}
                response = self.client.post(url, json.dumps(payload), content_type="application/json")
                self.assertFalse(response.json()["ok"], response.content)
                if coverage == "quarterly" and month in (10, 11):
                    self.assertEqual(response.json()["message"], f"{category}: For a whole quarter, set Record Date to December 2026.")
                self.assertFalse(FinancialRecord.objects.filter(client=ledger).exists())
                self.assertFalse(Period.objects.filter(client=ledger).exists())

    def test_legacy_noncalendar_coverage_is_not_retagged_by_edit(self):
        owner = self._create_bookkeeper("legacy-coverage")
        ledger = self._create_client(bookkeeper=owner, suffix="legacy-coverage")
        self._login_as(owner)
        record = self._create_record(bookkeeper=owner, client=ledger, year=2026, month=2, day=1,
                                     amount=Decimal("123.45"), type_code="Sales", frequency="quarterly")
        url = reverse("api_financial_record_detail", kwargs={"client_id": ledger.id, "record_id": record.id})
        response = self.client.patch(url, json.dumps({"expected_revision": record.updated_at.isoformat(),
            "notes": "Reviewed", "line_items": [{"type_code": "Sales", "description": "Line item", "amount": "123.45", "coverage_frequency": None}]}), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        record.refresh_from_db()
        self.assertEqual(record.frequency, "quarterly")
        self.assertIsNone(record.line_items.get().coverage_frequency)
        self.assertEqual(record.entry_date, date(2026, 2, 1))
        self.assertEqual(record.total_amount, Decimal("123.45"))

    def test_entry_remarks_create_and_edit_reach_report_without_changing_amounts(self):
        owner = self._create_bookkeeper("remarks")
        client = self._create_client(bookkeeper=owner, suffix="remarks")
        self._login_as(owner)
        payload = self._build_create_payload()
        payload["notes"] = "Pending for payment"
        url = reverse("api_financial_records", kwargs={"client_id": client.id})
        created = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(created.status_code, 201, created.content)
        saved = created.json()["record"]
        self.assertEqual(saved["notes"], "Pending for payment")
        report_url = reverse("api_reports_print_layout")
        report_params = {"client_id": client.id, "date_from": "2026-04-01", "date_to": "2026-04-30"}
        report = self.client.get(report_url, report_params)
        self.assertEqual(report.status_code, 200)
        self.assertEqual([row["notes"] for row in report.json()["rows"]], ["Pending for payment"] * 2)

        detail_url = reverse("api_financial_record_detail", kwargs={"client_id": client.id, "record_id": saved["id"]})
        for remarks in ("Paid", "Paid on April 20", ""):
            updated = self.client.put(detail_url, data=json.dumps({
                "expected_revision": saved["revision"], "notes": remarks,
            }), content_type="application/json")
            self.assertEqual(updated.status_code, 200, updated.content)
            current = updated.json()["record"]
            self.assertEqual(current["notes"], remarks)
            self.assertEqual(current["line_items"], saved["line_items"])
            self.assertEqual(current["total_amount"], saved["total_amount"])
            report = self.client.get(report_url, report_params)
            self.assertEqual(report.status_code, 200)
            self.assertEqual([row["notes"] for row in report.json()["rows"]], [remarks] * 2)
            saved = current

    def test_per_form_remarks_survive_save_copy_edit_and_report(self):
        owner = self._create_bookkeeper("form-remarks")
        client = self._create_client(bookkeeper=owner, suffix="form-remarks")
        self._login_as(owner)
        payload = self._build_create_payload()
        payload["notes"] = "Original entry note"
        payload["line_items"] = [
            {"type_code": "Sales", "description": "Sales", "amount": "1000", "remarks": None},
            {"type_code": "BIR Form 0619E", "description": "TW", "amount": "500", "remarks": "Paid", "tax_withheld": "0"},
            {"type_code": "BIR Form 2551Q", "description": "PQ", "amount": "500", "remarks": "Pending for payment"},
        ]
        url = reverse("api_financial_records", kwargs={"client_id": client.id})
        created = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(created.status_code, 201, created.content)
        saved = created.json()["record"]
        self.assertEqual(saved["total_amount"], "2000.00")
        self.assertEqual([line["remarks"] for line in saved["line_items"]], [None, "Paid", "Pending for payment"])
        copied = self.client.get(reverse("api_financial_records_last_entry", kwargs={"client_id": client.id}), {
            "month": 5, "year": 2026, "frequency": "quarterly",
        }).json()["record"]
        self.assertEqual(copied["line_items"], saved["line_items"])
        detail_url = reverse("api_financial_record_detail", kwargs={"client_id": client.id, "record_id": saved["id"]})
        lines_before = list(FinancialRecordLine.objects.filter(record_id=saved["id"]).order_by("id").values())
        old_payload = {"expected_revision": saved["revision"], "line_items": [
            {key: value for key, value in line.items() if key != "remarks"} for line in saved["line_items"]
        ]}
        rejected = self.client.put(detail_url, data=json.dumps(old_payload), content_type="application/json")
        self.assertEqual(rejected.json()["code"], "line_remarks_required")
        self.assertEqual(list(FinancialRecordLine.objects.filter(record_id=saved["id"]).order_by("id").values()), lines_before)

        payload["line_items"] = saved["line_items"]
        payload["expected_revision"] = saved["revision"]
        payload["line_items"][2]["remarks"] = "Paid on April 20"
        updated = self.client.put(detail_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(updated.status_code, 200, updated.content)
        current = updated.json()["record"]
        self.assertEqual(current["total_amount"], "2000.00")
        self.assertEqual(current["notes"], "Original entry note")
        self.assertEqual([line["remarks"] for line in current["line_items"]], [None, "Paid", "Paid on April 20"])
        self.assertEqual(current["line_items"][1]["tax_withheld"], "0.00")
        stale = self.client.put(detail_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(stale.json()["code"], "stale_record")
        report_params = {"client_id": client.id, "date_from": "2026-04-01", "date_to": "2026-04-30"}
        report = self.client.get(reverse("api_reports_print_layout"), report_params)
        self.assertEqual(report.status_code, 200)
        self.assertEqual([line["remarks"] for line in report.json()["rows"]], [None, "Paid", "Paid on April 20"])
        self.assertEqual([line["notes"] for line in report.json()["rows"]], ["Original entry note"] * 3)
        other = self._create_bookkeeper("remarks-other")
        self._login_as(other)
        self.assertEqual(self.client.get(reverse("api_reports_print_layout"), report_params).status_code, 404)
        self.assertFalse(self.client.put(detail_url, data=json.dumps({
            "expected_revision": current["revision"], "notes": "Unauthorized",
        }), content_type="application/json").json()["ok"])

    def test_legacy_form_remarks_keep_null_until_explicitly_changed(self):
        owner = self._create_bookkeeper("legacy-remarks")
        client = self._create_client(bookkeeper=owner, suffix="legacy-remarks")
        self._login_as(owner)
        record = self._create_record(bookkeeper=owner, client=client, year=2026, month=4, day=15, amount=Decimal("500"))
        url = reverse("api_financial_record_detail", kwargs={"client_id": client.id, "record_id": record.id})
        original_line = record.line_items.get()
        self.assertIsNone(original_line.remarks)
        response = self.client.put(url, data=json.dumps({
            "expected_revision": record.updated_at.isoformat(), "notes": "Legacy note retained",
        }), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        saved = response.json()["record"]
        self.assertIsNone(saved["line_items"][0]["remarks"])
        self.assertEqual(saved["line_items"][0]["id"], original_line.id)
        saved["line_items"][0]["remarks"] = ""
        response = self.client.put(url, data=json.dumps({
            "expected_revision": saved["revision"], "line_items": saved["line_items"],
        }), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["record"]["line_items"][0]["remarks"], "")
        self.assertEqual(response.json()["record"]["notes"], "Legacy note retained")
        self.assertEqual(response.json()["record"]["total_amount"], "500.00")

    def test_invalid_form_remarks_do_not_persist(self):
        owner = self._create_bookkeeper("invalid-remarks")
        client = self._create_client(bookkeeper=owner, suffix="invalid-remarks")
        self._login_as(owner)
        url = reverse("api_financial_records", kwargs={"client_id": client.id})
        for value in ("x" * 256, {"paid": True}, True, 123, "bad\x00remark"):
            with self.subTest(value_type=type(value).__name__):
                payload = self._build_create_payload()
                payload["line_items"][1]["remarks"] = value
                response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertFalse(FinancialRecord.objects.filter(client=client).exists())
                self.assertFalse(Period.objects.filter(client=client).exists())

    def test_worksheet_amounts_round_trip_without_increasing_totals(self):
        owner = self._create_bookkeeper("worksheet-owner")
        client = self._create_client(bookkeeper=owner, suffix="worksheet")
        self._login_as(owner)
        payload = self._build_create_payload()
        fields = FinancialRecordLine.WORKSHEET_AMOUNT_LABELS
        payload["line_items"][0].update(dict.fromkeys(fields, None))
        payload["line_items"][1].update(mict="", cogs_cos="9000.125", income_payments_2307="10000", tax_withheld=0)
        url = reverse("api_financial_records", kwargs={"client_id": client.id})
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        saved = response.json()["record"]
        self.assertEqual(saved["total_amount"], "1120.00")
        self.assertIsNone(saved["line_items"][1]["mict"])
        self.assertEqual(saved["line_items"][1]["cogs_cos"], "9000.12")
        self.assertEqual(saved["line_items"][1]["tax_withheld"], "0.00")
        copied = self.client.get(reverse("api_financial_records_last_entry", kwargs={"client_id": client.id}),
                                 {"month": 5, "year": 2026, "frequency": "quarterly"}).json()["record"]
        self.assertEqual(copied["line_items"], saved["line_items"])
        detail_url = reverse("api_financial_record_detail", kwargs={"client_id": client.id, "record_id": saved["id"]})
        response = self.client.put(detail_url, data=json.dumps({"expected_revision": saved["revision"], "notes": "Notes only"}), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        updated = response.json()["record"]
        self.assertEqual(updated["line_items"], saved["line_items"])
        # An older editor must reload rather than erase values it did not receive.
        old_payload = self._build_create_payload()
        old_payload["expected_revision"] = updated["revision"]
        rejected = self.client.put(detail_url, data=json.dumps(old_payload), content_type="application/json")
        self.assertFalse(rejected.json()["ok"])
        self.assertEqual(FinancialRecordLine.objects.get(record_id=saved["id"], sort_order=2).cogs_cos, Decimal("9000.12"))
        payload["expected_revision"] = updated["revision"]
        payload["line_items"][1]["cogs_cos"] = None
        response = self.client.put(detail_url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["record"]["line_items"][1]["cogs_cos"])
        self.assertEqual(response.json()["record"]["total_amount"], "1120.00")
        stale = self.client.put(detail_url, data=json.dumps(payload), content_type="application/json")
        self.assertFalse(stale.json()["ok"])
        other = self._create_bookkeeper("worksheet-other")
        self._login_as(other)
        denied = self.client.put(detail_url, data=json.dumps(payload), content_type="application/json")
        self.assertFalse(denied.json()["ok"])
        self.assertEqual(FinancialRecordLine.objects.get(record_id=saved["id"], sort_order=2).tax_withheld, Decimal("0.00"))

    def test_invalid_worksheet_amounts_do_not_create_records_or_periods(self):
        owner = self._create_bookkeeper("worksheet-invalid")
        client = self._create_client(bookkeeper=owner, suffix="worksheet-invalid")
        self._login_as(owner)
        for name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS:
            for value in ("-0.01", "NaN", "Infinity", True, {}, "1000000000000"):
                with self.subTest(field=name, value=value):
                    payload = self._build_create_payload()
                    payload["line_items"][1][name] = value
                    response = self.client.post(reverse("api_financial_records", kwargs={"client_id": client.id}),
                                                data=json.dumps(payload), content_type="application/json")
                    self.assertFalse(response.json()["ok"])
                    self.assertFalse(FinancialRecord.objects.filter(client=client).exists())
                    self.assertFalse(Period.objects.filter(client=client).exists())

    def test_financial_records_api_requires_authentication(self):
        owner = self._create_bookkeeper("auth-owner")
        client = self._create_client(bookkeeper=owner, suffix="auth-client")

        clients_response = self.client.get(
            reverse("api_financial_record_clients"),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(clients_response.status_code, 401)
        self.assertFalse(clients_response.json().get("ok"))

        records_response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(records_response.status_code, 401)
        self.assertFalse(records_response.json().get("ok"))

        create_response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 401)
        self.assertFalse(create_response.json().get("ok"))

    def test_financial_record_clients_list_is_scoped_and_includes_activity_metadata(self):
        owner = self._create_bookkeeper("owner-clients")
        other = self._create_bookkeeper("other-clients")

        owner_active = self._create_client(bookkeeper=owner, suffix="owner-active")
        owner_none = self._create_client(bookkeeper=owner, suffix="owner-none")
        other_active = self._create_client(bookkeeper=other, suffix="other-active")

        record = self._create_record(
            bookkeeper=owner,
            client=owner_active,
            year=2026,
            month=4,
            day=11,
            amount=Decimal("500.00"),
        )
        record.deadline_date = date(2026, 4, 15)
        record.save()

        self._create_record(
            bookkeeper=other,
            client=other_active,
            year=2026,
            month=4,
            day=12,
            amount=Decimal("900.00"),
        )

        self._login_as(owner)
        response = self.client.get(reverse("api_financial_record_clients"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        rows_by_id = {row["id"]: row for row in payload.get("clients", [])}
        self.assertEqual(set(rows_by_id), {owner_active.id, owner_none.id})

        self.assertEqual(rows_by_id[owner_active.id]["activity_state"], "active")
        self.assertEqual(rows_by_id[owner_active.id]["financial_record_count"], 1)
        self.assertEqual(rows_by_id[owner_active.id]["deadline_date"], "2026-04-15")
        self.assertIn("latest_record_updated_at", rows_by_id[owner_active.id])
        self.assertIn("recent_activity_at", rows_by_id[owner_active.id])
        self.assertTrue(rows_by_id[owner_active.id]["latest_record_updated_at"])
        self.assertTrue(rows_by_id[owner_active.id]["recent_activity_at"])
        self.assertTrue("days_remaining" in rows_by_id[owner_active.id])
        self.assertTrue(rows_by_id[owner_active.id]["deadline_completed"])

        self.assertEqual(rows_by_id[owner_none.id]["activity_state"], "none")
        self.assertEqual(rows_by_id[owner_none.id]["financial_record_count"], 0)
        self.assertEqual(rows_by_id[owner_none.id]["deadline_date"], "")
        self.assertFalse(rows_by_id[owner_none.id]["deadline_completed"])

    def test_financial_records_api_enforces_client_ownership_isolation(self):
        owner = self._create_bookkeeper("owner-isolation")
        other = self._create_bookkeeper("other-isolation")

        other_client = self._create_client(bookkeeper=other, suffix="other-client")
        other_record = self._create_record(
            bookkeeper=other,
            client=other_client,
            year=2026,
            month=4,
            day=14,
            amount=Decimal("750.00"),
        )

        self._login_as(owner)

        list_response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": other_client.id}),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(list_response.status_code, 404)
        self.assertEqual(list_response.json().get("message"), "Client not found.")

        create_response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": other_client.id}),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 404)
        self.assertEqual(create_response.json().get("message"), "Client not found.")

        update_response = self.client.put(
            reverse(
                "api_financial_record_detail",
                kwargs={"client_id": other_client.id, "record_id": other_record.id},
            ),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(update_response.json().get("message"), "Client not found.")

        delete_response = self.client.delete(
            reverse(
                "api_financial_record_detail",
                kwargs={"client_id": other_client.id, "record_id": other_record.id},
            ),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(delete_response.json().get("message"), "Client not found.")

    def test_financial_records_crud_success_with_line_items_and_period_cleanup(self):
        owner = self._create_bookkeeper("owner-crud")
        client = self._create_client(bookkeeper=owner, suffix="crud")
        self._login_as(owner)

        create_response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        create_payload = create_response.json()
        self.assertTrue(create_payload.get("ok"))
        self.assertEqual(create_payload.get("message"), "Financial entry added successfully.")
        self.assertEqual(create_payload["record"]["total_amount"], "1120.00")
        self.assertEqual(create_payload["record"]["line_items_count"], 2)
        self.assertEqual(create_payload["record"]["frequency"], "quarterly")

        record_id = create_payload["record"]["id"]

        list_response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            {"month": 4, "year": 2026},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(list_response.status_code, 200)
        list_payload = list_response.json()
        self.assertTrue(list_payload.get("ok"))
        self.assertEqual(len(list_payload.get("records", [])), 1)
        self.assertEqual(list_payload["summary"]["total_amount"], "1120.00")

        update_payload = {
            "expected_revision": create_payload["record"]["revision"],
            "month": 4,
            "year": 2026,
            "date": "2026-04-18",
            "frequency": "annually",
            "notes": "Updated via test",
            "line_items": [
                {
                    "type_code": "Sales",
                    "description": "Updated sale",
                    "amount": "900.00",
                },
                {
                    "type_code": "Expenses",
                    "description": "Updated expense",
                    "amount": "100.00",
                },
            ],
        }
        update_response = self.client.put(
            reverse(
                "api_financial_record_detail",
                kwargs={"client_id": client.id, "record_id": record_id},
            ),
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        update_json = update_response.json()
        self.assertTrue(update_json.get("ok"))
        self.assertEqual(update_json.get("message"), "Financial entry updated successfully.")
        self.assertEqual(update_json["record"]["total_amount"], "1000.00")
        self.assertEqual(update_json["record"]["frequency"], "annually")

        delete_response = self.client.delete(
            reverse(
                "api_financial_record_detail",
                kwargs={"client_id": client.id, "record_id": record_id},
            ),
            data=json.dumps({"expected_revision": update_json["record"]["revision"]}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(delete_response.status_code, 200)
        delete_payload = delete_response.json()
        self.assertTrue(delete_payload.get("ok"))
        self.assertEqual(delete_payload.get("message"), "Financial entry deleted successfully.")

        self.assertEqual(FinancialRecord.objects.filter(client=client).count(), 0)
        self.assertEqual(Period.objects.filter(client=client, year=2026, month=4).count(), 0)

    def test_creating_financial_record_emails_client_when_email_is_available(self):
        owner = self._create_bookkeeper("owner-email-notice")
        client = self._create_client(bookkeeper=owner, suffix="email-notice")
        self._login_as(owner)
        mail.outbox = []

        response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["client_email_notification"]["sent"], True)
        self.assertEqual(payload["client_email_notification"]["skipped"], False)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [client.email])
        self.assertIn("SafeBooks record update for April 2026", email.subject)
        self.assertIn(owner.full_name, email.body)
        self.assertIn(client.client_name, email.body)
        self.assertIn("Total recorded amount: PHP 1,120.00", email.body)
        self.assertIn("Transactions recorded: 2", email.body)

    def test_creating_financial_record_skips_client_email_when_email_is_missing(self):
        owner = self._create_bookkeeper("owner-email-skip")
        client = self._create_client(bookkeeper=owner, suffix="email-skip")
        client.email = ""
        client.save(update_fields=["email"])
        self._login_as(owner)
        mail.outbox = []

        response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["client_email_notification"]["sent"], False)
        self.assertEqual(payload["client_email_notification"]["skipped"], True)
        self.assertEqual(payload["client_email_notification"]["reason"], "Client email is not provided.")
        self.assertEqual(len(mail.outbox), 0)

    def test_creating_financial_record_skips_client_email_when_preference_is_off(self):
        owner = self._create_bookkeeper("owner-email-pref-off")
        owner.client_record_email_notifications_enabled = False
        owner.save(update_fields=["client_record_email_notifications_enabled"])
        client = self._create_client(bookkeeper=owner, suffix="email-pref-off")
        self._login_as(owner)
        mail.outbox = []

        response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(self._build_create_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["client_email_notification"]["sent"], False)
        self.assertEqual(payload["client_email_notification"]["skipped"], True)
        self.assertEqual(
            payload["client_email_notification"]["reason"],
            "Client email notifications are turned off in Settings.",
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_financial_record_deadline_date_crud(self):
        owner = self._create_bookkeeper("owner-deadline")
        client = self._create_client(bookkeeper=owner, suffix="deadline")
        self._login_as(owner)

        payload = self._build_create_payload()
        payload["month"] = 3
        payload["year"] = 2026
        payload["date"] = "2026-03-15"
        payload["deadline_date"] = "2026-04-20"

        # 1. Create March record with April deadline -> not completed yet
        create_response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        create_payload = create_response.json()
        self.assertTrue(create_payload.get("ok"))
        self.assertEqual(create_payload["record"]["deadline_date"], "2026-04-20")
        self.assertFalse(create_payload["record"]["deadline_completed"])

        record_id = create_payload["record"]["id"]

        # 2. Update to July deadline -> not completed yet
        update_payload = {
            "expected_revision": create_payload["record"]["revision"],
            "month": 3,
            "year": 2026,
            "date": "2026-03-15",
            "frequency": "quarterly",
            "deadline_date": "2026-07-25",
            "line_items": [
                {
                    "type_code": "Sales",
                    "description": "Updated sale",
                    "amount": "900.00",
                }
            ],
        }
        update_response = self.client.put(
            reverse(
                "api_financial_record_detail",
                kwargs={"client_id": client.id, "record_id": record_id},
            ),
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        update_json = update_response.json()
        self.assertTrue(update_json.get("ok"))
        self.assertEqual(update_json["record"]["deadline_date"], "2026-07-25")
        self.assertFalse(update_json["record"]["deadline_completed"])

        # 3. Create another record for July -> should mark the March deadline as completed
        july_payload = self._build_create_payload()
        july_payload["month"] = 7
        july_payload["year"] = 2026
        july_payload["date"] = "2026-07-05"

        july_response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(july_payload),
            content_type="application/json",
        )
        self.assertEqual(july_response.status_code, 201)

        # 4. Fetch March record detail and check that deadline_completed is now True!
        fetch_response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            {"month": 3, "year": 2026},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(fetch_response.status_code, 200)
        records_list = fetch_response.json().get("records", [])
        self.assertEqual(len(records_list), 1)
        self.assertTrue(records_list[0]["deadline_completed"])

        # 5. Clear deadline_date
        clear_payload = {
            "expected_revision": update_json["record"]["revision"],
            "month": 3,
            "year": 2026,
            "date": "2026-03-15",
            "frequency": "quarterly",
            "deadline_date": "",
            "line_items": [
                {
                    "type_code": "Sales",
                    "description": "Updated sale",
                    "amount": "900.00",
                }
            ],
        }
        clear_response = self.client.put(
            reverse(
                "api_financial_record_detail",
                kwargs={"client_id": client.id, "record_id": record_id},
            ),
            data=json.dumps(clear_payload),
            content_type="application/json",
        )
        self.assertEqual(clear_response.status_code, 200)
        clear_json = clear_response.json()
        self.assertTrue(clear_json.get("ok"))
        self.assertEqual(clear_json["record"]["deadline_date"], "")
        self.assertFalse(clear_json["record"]["deadline_completed"])

    def test_financial_records_line_item_validation_errors(self):
        owner = self._create_bookkeeper("owner-validation")
        client = self._create_client(bookkeeper=owner, suffix="validation")
        self._login_as(owner)

        negative_amount_payload = self._build_create_payload()
        negative_amount_payload["line_items"] = [
            {
                "type_code": "Sales",
                "description": "Negative test",
                "amount": "-1",
            }
        ]
        response_negative = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(negative_amount_payload),
            content_type="application/json",
        )
        self.assertEqual(response_negative.status_code, 400)
        self.assertEqual(
            response_negative.json().get("message"),
            "Sales: Amount cannot be negative.",
        )

        missing_items_payload = self._build_create_payload()
        missing_items_payload["line_items"] = []
        response_missing = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(missing_items_payload),
            content_type="application/json",
        )
        self.assertEqual(response_missing.status_code, 400)
        self.assertEqual(
            response_missing.json().get("message"),
            "At least one record detail is required.",
        )

    def test_financial_records_period_and_date_validation_edges(self):
        owner = self._create_bookkeeper("owner-period")
        client = self._create_client(bookkeeper=owner, suffix="period")
        self._login_as(owner)

        invalid_month_response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            {"month": 13, "year": 2026},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid_month_response.status_code, 400)
        self.assertEqual(invalid_month_response.json().get("message"), "Invalid period month.")

        invalid_year_response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            {"month": 4, "year": 1999},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(invalid_year_response.status_code, 400)
        self.assertEqual(
            invalid_year_response.json().get("message"),
            "Period year must be between 2000 and 2100.",
        )

        date_mismatch_payload = self._build_create_payload()
        date_mismatch_payload["month"] = 4
        date_mismatch_payload["year"] = 2026
        date_mismatch_payload["date"] = "2026-05-01"

        mismatch_response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(date_mismatch_payload),
            content_type="application/json",
        )
        self.assertEqual(mismatch_response.status_code, 201)
        payload = mismatch_response.json()
        self.assertTrue(payload.get("ok"))

        record_id = payload.get("record", {}).get("id")
        self.assertTrue(record_id)

        record = FinancialRecord.objects.get(id=record_id)
        self.assertEqual(record.entry_date.isoformat(), "2026-05-01")
        self.assertEqual(record.period.month, 5)
        self.assertEqual(record.period.year, 2026)

    def test_financial_records_all_periods_returns_full_client_history(self):
        owner = self._create_bookkeeper("owner-all-periods")
        client = self._create_client(bookkeeper=owner, suffix="all-periods")
        self._login_as(owner)

        self._create_record(
            bookkeeper=owner,
            client=client,
            year=2026,
            month=4,
            day=5,
            amount=Decimal("1000.00"),
            type_code="Sales",
        )
        self._create_record(
            bookkeeper=owner,
            client=client,
            year=2026,
            month=5,
            day=5,
            amount=Decimal("250.00"),
            type_code="Expenses",
        )

        response = self.client.get(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            {"month": "all", "year": "all"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["period"]["month"], "all")
        self.assertEqual(payload["period"]["month_label"], "All Periods")
        self.assertEqual(payload["summary"]["total_amount"], "1250.00")
        self.assertEqual(payload["summary"]["entry_count"], 2)
        self.assertEqual(payload["prior_frequencies"], [])
        self.assertEqual(
            [record["date"] for record in payload.get("records", [])],
            ["2026-05-05", "2026-04-05"],
        )

    def test_last_period_entry_api_uses_selected_frequency(self):
        owner = self._create_bookkeeper("owner-last-entry")
        client = self._create_client(bookkeeper=owner, suffix="last-entry")
        self._login_as(owner)

        self._create_record(
            bookkeeper=owner,
            client=client,
            year=2026,
            month=2,
            day=3,
            amount=Decimal("500.00"),
            type_code="Expenses",
            frequency=FinancialRecord.FREQUENCY_QUARTERLY,
        )
        self._create_record(
            bookkeeper=owner,
            client=client,
            year=2026,
            month=3,
            day=3,
            amount=Decimal("700.00"),
            type_code="Sales",
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
        )
        self._create_record(
            bookkeeper=owner,
            client=client,
            year=2026,
            month=4,
            day=3,
            amount=Decimal("900.00"),
            type_code="Sales",
            frequency=FinancialRecord.FREQUENCY_MONTHLY,
        )

        monthly_response = self.client.get(
            reverse("api_financial_records_last_entry", kwargs={"client_id": client.id}),
            {"month": 5, "year": 2026, "frequency": "monthly"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(monthly_response.status_code, 200)
        monthly_payload = monthly_response.json()
        self.assertTrue(monthly_payload.get("ok"))
        self.assertEqual(monthly_payload["record"]["date"], "2026-04-03")
        self.assertEqual(monthly_payload["record"]["total_amount"], "900.00")
        self.assertEqual(monthly_payload["record"]["frequency"], "monthly")

        quarterly_response = self.client.get(
            reverse("api_financial_records_last_entry", kwargs={"client_id": client.id}),
            {"month": 5, "year": 2026, "frequency": "quarterly"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(quarterly_response.status_code, 200)
        quarterly_payload = quarterly_response.json()
        self.assertTrue(quarterly_payload.get("ok"))
        self.assertEqual(quarterly_payload["record"]["date"], "2026-02-03")
        self.assertEqual(quarterly_payload["record"]["total_amount"], "500.00")
        self.assertEqual(quarterly_payload["record"]["frequency"], "quarterly")

        annual_response = self.client.get(
            reverse("api_financial_records_last_entry", kwargs={"client_id": client.id}),
            {"month": 5, "year": 2026, "frequency": "annually"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(annual_response.status_code, 200)
        annual_payload = annual_response.json()
        self.assertFalse(annual_payload.get("ok"))
        self.assertTrue(annual_payload.get("no_record"))
