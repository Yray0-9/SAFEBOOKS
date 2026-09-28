import json
from datetime import date
from decimal import Decimal

from django.core import mail
from django.test import TestCase
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
class FinancialRecordsApiTests(TestCase):
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
            "Line item #1: Amount cannot be negative.",
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
            "At least one line item is required.",
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
