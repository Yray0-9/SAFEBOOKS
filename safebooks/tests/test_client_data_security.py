from safebooks.tests.session_helpers import bind_authenticated_session

import json
import shutil
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth.hashers import make_password
from django.test import Client as TestClient, TestCase
from django.urls import reverse
from django.utils import timezone

from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY, SESSION_CLIENT_PROFILE_ACCESS_KEY


class ClientDataSecurityTests(TestCase):
    """Use synthetic client credentials, never real account data."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = BookkeeperAccount.objects.create(
            full_name="Privacy Test", username="privacy_test", email="privacy@example.com",
            password_hash=make_password("PrivacyTest#123"),
            status=BookkeeperAccount.STATUS_APPROVED, client_details_password_required=True,
        )
        cls.other = BookkeeperAccount.objects.create(
            full_name="Other Privacy Test", username="other_privacy_test", email="other-privacy@example.com",
            password_hash=cls.owner.password_hash,
            status=BookkeeperAccount.STATUS_APPROVED, client_details_password_required=True,
        )
        cls.protected = Client.objects.create(
            bookkeeper=cls.owner, client_name="Protected Client", tin_number="123456789001",
            location="Panabo", permit_number="PRIVATE-PERMIT", birthday=date(1990, 1, 1),
            email="private-client@example.com", email_password="SyntheticEmailPassword#123",
            orus_account="synthetic-orus-account", orus_password="SyntheticOrusPassword#123",
            custom_fields=[{"label": "Portal PIN", "value": "SyntheticPrivatePIN", "type": "password"}],
        )
        cls.second = Client.objects.create(
            bookkeeper=cls.owner, client_name="Second Client", tin_number="123456789002", location="Tagum",
        )
        cls.foreign = Client.objects.create(
            bookkeeper=cls.other, client_name="Foreign Client", tin_number="123456789003", location="Tagum",
            email_password="ForeignSyntheticSecret#123",
        )
        period = Period.objects.create(client=cls.protected, month=1, year=2026)
        record = FinancialRecord.objects.create(
            bookkeeper=cls.owner, client=cls.protected, period=period, entry_date=date(2026, 1, 15),
            frequency=FinancialRecord.FREQUENCY_MONTHLY, total_amount=Decimal("123.45"),
        )
        FinancialRecordLine.objects.create(
            record=record, type_code="Sales", description="Synthetic transaction", amount=Decimal("123.45"), sort_order=1,
        )

    def setUp(self):
        self._login(self.client)

    def _login(self, client, account=None):
        session = client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = (account or self.owner).id
        bind_authenticated_session(session)
        session.save()

    def _confirm(self, client_id=None, *, password="PrivacyTest#123", client=None):
        return (client or self.client).post(
            reverse("api_security_client_details_access_confirm"),
            json.dumps({"current_password": password, "client_id": client_id}),
            content_type="application/json",
        )

    def _get_profile(self, client_id=None, *, client=None):
        return (client or self.client).get(reverse("api_client_detail", args=[client_id or self.protected.id]))

    def _payload(self):
        return {
            "client_name": self.protected.client_name, "tin_number": self.protected.tin_number,
            "trade_name": self.protected.trade_name, "location": self.protected.location,
            "permit_number": self.protected.permit_number, "birthday": self.protected.birthday.isoformat(),
            "email": self.protected.email, "email_password": self.protected.email_password,
            "orus_account": self.protected.orus_account, "orus_password": self.protected.orus_password,
            "custom_fields": self.protected.custom_fields,
        }

    def _assert_private_values_absent(self, response):
        for value in (
            self.protected.email_password, self.protected.orus_password, self.protected.orus_account,
            "SyntheticPrivatePIN", self.protected.email, self.protected.permit_number,
        ):
            self.assertNotContains(response, value, status_code=response.status_code)

    def test_directory_is_redacted_even_if_caller_requests_sensitive_fields(self):
        for params in ({}, {"include_sensitive": "true", "client_id": self.protected.id}):
            response = self.client.get(reverse("api_clients"), params)
            self.assertEqual(response.status_code, 200)
            self._assert_private_values_absent(response)
            row = next(row for row in response.json()["clients"] if row["id"] == self.protected.id)
            self.assertEqual(row["email_password"], "")
            self.assertEqual(row["orus_password"], "")
            self.assertEqual(row["custom_fields"], [])
            self.assertEqual(response["Cache-Control"], "no-store")
        self.protected.refresh_from_db()
        self.assertEqual(self.protected.email_password, "SyntheticEmailPassword#123")
        self.assertEqual(self.protected.custom_fields[0]["value"], "SyntheticPrivatePIN")

    def test_full_profile_requires_password_when_lock_enabled(self):
        self.assertEqual(self._get_profile().status_code, 403)
        self.assertEqual(self._confirm(self.protected.id, password="WrongTest#123").status_code, 400)
        self.assertEqual(self._get_profile().status_code, 403)
        self.assertEqual(self._confirm(self.protected.id).status_code, 200)
        response = self._get_profile()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["client"]["email_password"], self.protected.email_password)
        self.assertEqual(response.json()["client"]["custom_fields"], self.protected.custom_fields)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_disabled_lock_allows_owner_profile_but_not_bulk_credentials(self):
        self.owner.client_details_password_required = False
        self.owner.save(update_fields=["client_details_password_required"])
        self.assertEqual(self._get_profile().status_code, 200)
        response = self.client.get(reverse("api_clients"))
        self._assert_private_values_absent(response)

    def test_foreign_profile_read_edit_and_confirmation_are_denied(self):
        for method in ("get", "put", "patch"):
            response = getattr(self.client, method)(
                reverse("api_client_detail", args=[self.foreign.id]),
                data={} if method == "get" else json.dumps(self._payload()),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 404)
            self.assertNotContains(response, self.foreign.email_password, status_code=404)
        self.assertEqual(self._confirm(self.foreign.id).status_code, 404)

    def test_full_profile_requires_login(self):
        response = self._get_profile(client=TestClient())
        self.assertEqual(response.status_code, 401)
        self._assert_private_values_absent(response)

    def test_verified_permission_is_limited_to_selected_client(self):
        self.assertEqual(self._confirm(self.protected.id).status_code, 200)
        self.assertEqual(self._get_profile(self.second.id).status_code, 403)
        self.assertEqual(self.client.get(reverse("client_details", args=[self.second.id])).status_code, 302)
        self.assertEqual(self._get_profile().status_code, 200)

    def test_legacy_unscoped_confirmation_is_bound_on_first_access(self):
        self.assertEqual(self._confirm().status_code, 200)
        self.assertEqual(self._get_profile().status_code, 200)
        self.assertEqual(self._get_profile(self.second.id).status_code, 403)

    def test_another_browser_cannot_reuse_confirmation(self):
        self.assertEqual(self._confirm(self.protected.id).status_code, 200)
        other_browser = TestClient()
        self._login(other_browser)
        self.assertEqual(self._get_profile(client=other_browser).status_code, 403)
        self.assertEqual(self._get_profile().status_code, 200)

    def test_detail_page_grants_its_edit_api_without_unlocking_other_pages(self):
        self.assertEqual(self._confirm(self.protected.id).status_code, 200)
        page = self.client.get(reverse("client_details", args=[self.protected.id]))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page["Cache-Control"], "no-store")
        self.assertEqual(self._get_profile().status_code, 200)
        payload = self._payload()
        payload["client_name"] = "Edited Securely"
        saved = self.client.put(reverse("api_client_detail", args=[self.protected.id]), json.dumps(payload), content_type="application/json")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["client"]["email_password"], self.protected.email_password)
        self.protected.refresh_from_db()
        self.assertEqual(self.protected.client_name, "Edited Securely")
        self.assertEqual(self.protected.orus_password, "SyntheticOrusPassword#123")
        self.assertEqual(self.client.get(reverse("client_details", args=[self.second.id])).status_code, 302)

    def test_returning_to_directory_revokes_full_profile_api_access(self):
        self._confirm(self.protected.id)
        self.assertEqual(self._get_profile().status_code, 200)
        self.client.get(reverse("clients"))
        self.assertEqual(self._get_profile().status_code, 403)
        self.assertNotIn(SESSION_CLIENT_PROFILE_ACCESS_KEY, self.client.session)

    def test_expired_profile_permission_is_rejected(self):
        self._confirm(self.protected.id)
        self._get_profile()
        session = self.client.session
        grant = dict(session[SESSION_CLIENT_PROFILE_ACCESS_KEY])
        grant["expires_at"] = int(timezone.now().timestamp())
        session[SESSION_CLIENT_PROFILE_ACCESS_KEY] = grant
        session.save()
        self.assertEqual(self._get_profile().status_code, 403)

    def test_changed_password_invalidates_profile_permission(self):
        self._confirm(self.protected.id)
        self._get_profile()
        BookkeeperAccount.objects.filter(pk=self.owner.pk).update(password_hash=make_password("ChangedPrivacy#123"))
        self.assertEqual(self._get_profile().status_code, 401)

    def test_changed_bookkeeper_cannot_reuse_profile_permission(self):
        self._confirm(self.protected.id)
        self._get_profile()
        self._login(self.client, self.other)
        self.assertEqual(self._get_profile(self.foreign.id).status_code, 403)

    def test_unconfirmed_update_cannot_modify_stored_credentials(self):
        payload = self._payload()
        payload["email_password"] = "UnauthorizedReplacement#123"
        response = self.client.put(reverse("api_client_detail", args=[self.protected.id]), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.protected.refresh_from_db()
        self.assertEqual(self.protected.email_password, "SyntheticEmailPassword#123")

    def test_omitted_credentials_are_preserved_and_explicit_empty_values_can_clear(self):
        self._confirm(self.protected.id)
        payload = self._payload()
        for key in ("email_password", "orus_account", "orus_password"):
            payload.pop(key)
        response = self.client.put(reverse("api_client_detail", args=[self.protected.id]), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.protected.refresh_from_db()
        self.assertEqual(self.protected.email_password, "SyntheticEmailPassword#123")
        self.assertEqual(self.protected.orus_password, "SyntheticOrusPassword#123")
        payload.update(email_password="", orus_password="", orus_account="")
        response = self.client.put(reverse("api_client_detail", args=[self.protected.id]), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.protected.refresh_from_db()
        self.assertEqual(self.protected.email_password, "")
        self.assertEqual(self.protected.orus_password, "")

    def test_financial_and_report_responses_are_redacted_without_changing_totals(self):
        requests = (
            (reverse("api_financial_records", args=[self.protected.id]), {"month": "all", "year": "all"}),
            (reverse("api_financial_records_last_entry", args=[self.protected.id]), {"month": 2, "year": 2026, "frequency": "monthly"}),
            (reverse("api_reports_print_layout"), {"client_id": self.protected.id, "date_from": "2026-01-01", "date_to": "2026-12-31"}),
        )
        self._confirm(self.protected.id)
        self._get_profile()
        for url, params in requests:
            response = self.client.get(url, params)
            self.assertEqual(response.status_code, 200)
            self._assert_private_values_absent(response)
            self.assertEqual(response.json()["client"]["email_password"], "")
        report = self.client.get(requests[-1][0], requests[-1][1]).json()
        self.assertEqual(report["summary"]["total_amount"], "123.45")
        self.assertEqual(report["summary"]["entry_count"], 1)
        self.assertEqual(report["rows"][0]["amount"], "123.45")

    def test_directory_stays_redacted_after_confirmation(self):
        self._confirm(self.protected.id)
        self._get_profile()
        self._assert_private_values_absent(self.client.get(reverse("api_clients")))

    def test_status_restore_preserves_credentials_without_returning_them(self):
        Client.objects.filter(pk=self.protected.pk).update(remarks=Client.REMARK_CLOSED)
        response = self.client.post(reverse("api_client_reopen", args=[self.protected.id]))
        self.assertEqual(response.status_code, 200)
        self._assert_private_values_absent(response)
        self.protected.refresh_from_db()
        self.assertEqual(self.protected.email_password, "SyntheticEmailPassword#123")
        self.assertEqual(self.protected.custom_fields[0]["value"], "SyntheticPrivatePIN")

    def test_create_response_redacts_credentials_but_stores_submitted_values(self):
        payload = self._payload()
        payload["tin_number"] = "123456789004"
        response = self.client.post(reverse("api_clients"), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self._assert_private_values_absent(response)
        created = Client.objects.get(pk=response.json()["client"]["id"])
        self.assertEqual(created.email_password, self.protected.email_password)
        self.assertEqual(created.custom_fields, self.protected.custom_fields)

    def test_password_confirmation_requires_csrf(self):
        client = TestClient(enforce_csrf_checks=True)
        self._login(client)
        self.assertEqual(self._confirm(self.protected.id, client=client).status_code, 403)
        self.assertEqual(self._get_profile(client=client).status_code, 403)

    def test_invalid_selected_client_and_malformed_profile_payload_are_controlled(self):
        for value in (True, "bad-id", -1):
            self.assertEqual(self._confirm(value).status_code, 400)
        self._confirm(self.protected.id)
        response = self.client.put(reverse("api_client_detail", args=[self.protected.id]), "{", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    @skipUnless(shutil.which("node"), "Node.js is required for the shared print/editor component tests.")
    def test_report_and_editor_javascript_security(self):
        script = Path(__file__).parent / "js" / "test_client_privacy.cjs"
        result = subprocess.run([shutil.which("node"), str(script)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
