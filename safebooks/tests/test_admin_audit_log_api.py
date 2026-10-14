from safebooks.tests.session_helpers import bind_authenticated_session

import json
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class AdminAuditLogApiTests(TestCase):
    def _create_admin(self, suffix: str) -> AdminAccount:
        return AdminAccount.objects.create(
            full_name=f"Admin {suffix}",
            email=f"admin_audit_{suffix}@example.com",
            password_hash="not-used-in-test",
            is_active=True,
        )

    def _login_admin(self, account: AdminAccount) -> None:
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def _login_bookkeeper(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def _create_bookkeeper(self, suffix: str, status: str = BookkeeperAccount.STATUS_APPROVED) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"admin_audit_bk_{suffix}",
            email=f"admin_audit_bk_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=status,
        )

    def _create_log(self, admin: AdminAccount, action_type: str, suffix: str) -> AdminAuditLog:
        return AdminAuditLog.objects.create(
            admin=admin,
            action_type=action_type,
            target_model="BookkeeperAccount",
            target_id=100 + len(suffix),
            message=f"{suffix} action for Bookkeeper {suffix}.",
            metadata={
                "bookkeeper_name": f"Bookkeeper {suffix}",
                "bookkeeper_email": f"bookkeeper_{suffix}@example.com",
                "status": BookkeeperAccount.STATUS_APPROVED,
            },
        )

    def test_admin_audit_log_requires_admin_authentication(self):
        response = self.client.get(reverse("api_admin_audit_log"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("ok"))

    def test_admin_audit_log_blocks_bookkeeper_session(self):
        bookkeeper = self._create_bookkeeper("blocked")
        self._login_bookkeeper(bookkeeper)

        response = self.client.get(reverse("api_admin_audit_log"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json().get("ok"))

    def test_admin_audit_log_page_requires_admin_and_renders(self):
        admin = self._create_admin("page")
        self._login_admin(admin)

        response = self.client.get(reverse("admin_audit_log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit Log")
        self.assertContains(response, 'id="auditLogDateFromInput"')
        self.assertContains(response, 'id="auditLogDateToInput"')
        self.assertContains(response, 'id="auditLogPreviousPage"')

    def test_admin_audit_log_returns_serialized_logs_and_counts(self):
        admin = self._create_admin("list")
        self._login_admin(admin)
        approved_log = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, "Approved")
        self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATED, "Deactivated")

        response = self.client.get(reverse("api_admin_audit_log"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("total_count"), 2)
        self.assertEqual(payload.get("counts", {}).get("approvals"), 1)
        self.assertEqual(payload.get("counts", {}).get("access"), 1)
        log_payload = next(row for row in payload.get("logs", []) if row.get("id") == approved_log.id)
        self.assertEqual(log_payload.get("action_label"), "Approved bookkeeper")
        self.assertEqual(log_payload.get("target_name"), "Bookkeeper Approved")
        self.assertEqual(log_payload.get("admin_name"), admin.full_name)

    def test_admin_audit_log_filters_by_action_group(self):
        admin = self._create_admin("filter")
        self._login_admin(admin)
        approval_log = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, "Approval")
        self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATED, "Access")

        response = self.client.get(
            reverse("api_admin_audit_log"),
            {"action": "approvals"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        logs = response.json().get("logs", [])
        self.assertEqual([row.get("id") for row in logs], [approval_log.id])

    def test_admin_audit_log_searches_message_and_admin(self):
        admin = self._create_admin("search")
        self._login_admin(admin)
        target_log = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_REJECTED, "Needle")
        self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, "Other")

        response = self.client.get(
            reverse("api_admin_audit_log"),
            {"search": "Needle"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        logs = response.json().get("logs", [])
        self.assertEqual([row.get("id") for row in logs], [target_log.id])

    def test_admin_audit_log_sort_oldest(self):
        admin = self._create_admin("sort")
        self._login_admin(admin)
        older = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, "Older")
        newer = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_REACTIVATED, "Newer")
        AdminAuditLog.objects.filter(id=older.id).update(created_at=timezone.now() - timedelta(days=2))
        AdminAuditLog.objects.filter(id=newer.id).update(created_at=timezone.now() - timedelta(days=1))

        response = self.client.get(
            reverse("api_admin_audit_log"),
            {"sort": "oldest"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        logs = response.json().get("logs", [])
        self.assertEqual([row.get("id") for row in logs[:2]], [older.id, newer.id])

    def test_successful_admin_login_and_logout_are_audited_once(self):
        admin = self._create_admin("auth-events")
        admin.password_hash = make_password("AdminPass#123")
        admin.save(update_fields=["password_hash"])

        login_response = self.client.post(
            reverse("api_login"),
            data=json.dumps({"identifier": admin.email, "password": "AdminPass#123"}),
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json().get("ok"))
        login_logs = AdminAuditLog.objects.filter(action_type=AdminAuditLog.ACTION_ADMIN_LOGIN)
        self.assertEqual(login_logs.count(), 1)
        self.assertEqual(login_logs.get().admin_id, admin.id)

        logout_response = self.client.post(reverse("api_logout"), content_type="application/json")

        self.assertEqual(logout_response.status_code, 200)
        logout_logs = AdminAuditLog.objects.filter(action_type=AdminAuditLog.ACTION_ADMIN_LOGOUT)
        self.assertEqual(logout_logs.count(), 1)
        self.assertEqual(logout_logs.get().admin_id, admin.id)
        serialized_metadata = json.dumps(list(AdminAuditLog.objects.values_list("metadata", flat=True)))
        self.assertNotIn("AdminPass#123", serialized_metadata)

        repeated_logout = self.client.post(reverse("api_logout"), content_type="application/json")
        self.assertEqual(repeated_logout.status_code, 401)
        self.assertEqual(logout_logs.count(), 1)

    def test_failed_admin_login_does_not_create_audit_entry(self):
        admin = self._create_admin("failed-auth")
        admin.password_hash = make_password("AdminPass#123")
        admin.save(update_fields=["password_hash"])

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({"identifier": admin.email, "password": "WrongPass#123"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("ok"))
        self.assertFalse(AdminAuditLog.objects.exists())

    def test_admin_audit_log_paginates_filtered_results_stably(self):
        admin = self._create_admin("pagination")
        self._login_admin(admin)
        created_logs = [
            self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, f"Page {index:02d}")
            for index in range(25)
        ]

        response = self.client.get(
            reverse("api_admin_audit_log"),
            {"page": 2, "page_size": 10},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_size"], 10)
        self.assertEqual(payload["total_pages"], 3)
        self.assertTrue(payload["has_previous"])
        self.assertTrue(payload["has_next"])
        expected_ids = [log.id for log in reversed(created_logs)][10:20]
        self.assertEqual([row["id"] for row in payload["logs"]], expected_ids)

    def test_admin_audit_log_uses_ten_rows_per_page_by_default(self):
        admin = self._create_admin("default-pagination")
        self._login_admin(admin)
        for index in range(11):
            self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, f"Default {index:02d}")

        first_response = self.client.get(reverse("api_admin_audit_log"), HTTP_ACCEPT="application/json")
        second_response = self.client.get(
            reverse("api_admin_audit_log"),
            {"page": 2},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        first_payload = first_response.json()
        self.assertEqual(first_payload["page_size"], 10)
        self.assertEqual(first_payload["shown_count"], 10)
        self.assertEqual(first_payload["total_count"], 11)
        self.assertEqual(first_payload["total_pages"], 2)
        self.assertTrue(first_payload["has_next"])

        self.assertEqual(second_response.status_code, 200)
        second_payload = second_response.json()
        self.assertEqual(second_payload["page"], 2)
        self.assertEqual(second_payload["shown_count"], 1)
        self.assertTrue(second_payload["has_previous"])
        self.assertFalse(second_payload["has_next"])

    def test_admin_audit_log_filters_by_inclusive_date_range(self):
        admin = self._create_admin("date-range")
        self._login_admin(admin)
        older = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED, "Old date")
        today_log = self._create_log(admin, AdminAuditLog.ACTION_BOOKKEEPER_REJECTED, "Today date")
        AdminAuditLog.objects.filter(id=older.id).update(created_at=timezone.now() - timedelta(days=3))
        today = timezone.localdate().isoformat()

        response = self.client.get(
            reverse("api_admin_audit_log"),
            {"date_from": today, "date_to": today},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual([row["id"] for row in payload["logs"]], [today_log.id])

    def test_admin_audit_log_rejects_reversed_date_range(self):
        admin = self._create_admin("invalid-date-range")
        self._login_admin(admin)

        response = self.client.get(
            reverse("api_admin_audit_log"),
            {"date_from": "2026-07-13", "date_to": "2026-07-12"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok"))
