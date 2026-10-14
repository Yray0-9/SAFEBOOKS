from safebooks.tests.session_helpers import bind_authenticated_session

import json

from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount, BookkeeperAuditLog, Client
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class BookkeeperAuditLogApiTests(TestCase):
    def _create_bookkeeper(self, suffix: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"bk_audit_{suffix}",
            email=f"bk_audit_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
        )

    def _login_as(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def _create_client(self, owner: BookkeeperAccount, suffix: str) -> Client:
        return Client.objects.create(
            bookkeeper=owner,
            client_name=f"Client {suffix}",
            tin_number=f"{owner.id:03d}{len(suffix):03d}789012",
            location="Panabo City",
            remarks=Client.REMARK_ACTIVE,
        )

    def test_audit_log_page_and_api_require_bookkeeper_authentication(self):
        page_response = self.client.get(reverse("bookkeeper_audit_log"))
        api_response = self.client.get(reverse("api_bookkeeper_audit_log"), HTTP_ACCEPT="application/json")

        self.assertEqual(page_response.status_code, 302)
        self.assertEqual(api_response.status_code, 401)
        self.assertFalse(api_response.json().get("ok"))

    def test_audit_log_page_renders_for_bookkeeper(self):
        owner = self._create_bookkeeper("page")
        self._login_as(owner)

        response = self.client.get(reverse("bookkeeper_audit_log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workspace activity")
        self.assertContains(response, reverse("api_bookkeeper_audit_log"))
        self.assertContains(response, f'href="{reverse("profile")}"')
        self.assertContains(response, "data-bookkeeper-logout")

    def test_audit_log_is_private_to_current_bookkeeper(self):
        owner = self._create_bookkeeper("owner")
        other = self._create_bookkeeper("other")
        owner_log = BookkeeperAuditLog.objects.create(
            bookkeeper=owner,
            action_type=BookkeeperAuditLog.ACTION_CLIENT_UPDATED,
            target_model="Client",
            target_id=10,
            message="Updated client Owner Client.",
            metadata={"client_name": "Owner Client"},
        )
        BookkeeperAuditLog.objects.create(
            bookkeeper=other,
            action_type=BookkeeperAuditLog.ACTION_CLIENT_UPDATED,
            target_model="Client",
            target_id=11,
            message="Updated client Other Client.",
            metadata={"client_name": "Other Client"},
        )
        self._login_as(owner)

        response = self.client.get(reverse("api_bookkeeper_audit_log"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("counts", {}).get("all"), 1)
        self.assertEqual([row.get("id") for row in payload.get("logs", [])], [owner_log.id])
        self.assertNotContains(response, "Other Client")

    def test_audit_log_filters_client_and_record_actions(self):
        owner = self._create_bookkeeper("filters")
        client_log = BookkeeperAuditLog.objects.create(
            bookkeeper=owner,
            action_type=BookkeeperAuditLog.ACTION_CLIENT_CREATED,
            target_model="Client",
            target_id=20,
            message="Added client Filter Client.",
            metadata={"client_name": "Filter Client"},
        )
        BookkeeperAuditLog.objects.create(
            bookkeeper=owner,
            action_type=BookkeeperAuditLog.ACTION_RECORD_CREATED,
            target_model="FinancialRecord",
            target_id=21,
            message="Added a monthly record for Filter Client.",
            metadata={"client_name": "Filter Client"},
        )
        self._login_as(owner)

        response = self.client.get(
            reverse("api_bookkeeper_audit_log"),
            {"action": "clients"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row.get("id") for row in response.json().get("logs", [])], [client_log.id])

    def test_successful_client_creation_is_recorded_without_credentials(self):
        owner = self._create_bookkeeper("client-create")
        self._login_as(owner)
        payload = {
            "client_name": "Audit Client",
            "tin_number": "901234567890",
            "location": "Tagum City",
            "email": "audit-client@example.com",
            "email_password": "must-not-be-logged",
            "orus_account": "private-orus-account",
            "orus_password": "must-not-be-logged-either",
        }

        response = self.client.post(
            reverse("api_clients"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        log = BookkeeperAuditLog.objects.get(bookkeeper=owner)
        self.assertEqual(log.action_type, BookkeeperAuditLog.ACTION_CLIENT_CREATED)
        self.assertEqual(log.metadata, {"client_name": "Audit Client"})
        serialized_log = f"{log.message} {log.metadata}"
        self.assertNotIn("must-not-be-logged", serialized_log)
        self.assertNotIn("private-orus-account", serialized_log)

    def test_successful_financial_record_creation_is_recorded(self):
        owner = self._create_bookkeeper("record-create")
        client = self._create_client(owner, "record")
        self._login_as(owner)
        payload = {
            "date": "2026-07-10",
            "frequency": "monthly",
            "notes": "Audit test",
            "line_items": [
                {"type_code": "Sales", "description": "July sales", "amount": "1250.00"},
            ],
        }

        response = self.client.post(
            reverse("api_financial_records", kwargs={"client_id": client.id}),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        log = BookkeeperAuditLog.objects.get(bookkeeper=owner)
        self.assertEqual(log.action_type, BookkeeperAuditLog.ACTION_RECORD_CREATED)
        self.assertEqual(log.metadata.get("client_name"), client.client_name)
        self.assertEqual(log.metadata.get("record_date"), "2026-07-10")
        self.assertEqual(log.metadata.get("frequency"), "monthly")

    def test_failed_write_does_not_create_audit_entry(self):
        owner = self._create_bookkeeper("failed")
        self._login_as(owner)

        response = self.client.post(
            reverse("api_clients"),
            data=json.dumps({"client_name": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(BookkeeperAuditLog.objects.filter(bookkeeper=owner).exists())
