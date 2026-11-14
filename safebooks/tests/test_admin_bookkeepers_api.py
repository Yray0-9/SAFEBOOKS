from safebooks.tests.session_helpers import bind_authenticated_session

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount, BookkeeperDeactivationRequest, Client
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class AdminBookkeepersApiTests(TestCase):
    def _create_admin(self, suffix: str) -> AdminAccount:
        return AdminAccount.objects.create(
            full_name=f"Admin {suffix}",
            email=f"admin_bookkeeper_{suffix}@example.com",
            password_hash=make_password("AdminPass#123"),
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

    def _create_bookkeeper(self, suffix: str, status: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"admin_bk_{suffix}",
            email=f"admin_bk_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=status,
        )

    def _create_client(self, bookkeeper: BookkeeperAccount, suffix: str) -> Client:
        return Client.objects.create(
            bookkeeper=bookkeeper,
            client_name=f"Client {suffix}",
            tin_number=f"900-000-{suffix[-3:].zfill(3)}",
            trade_name=f"Trade {suffix}",
            location="Davao del Norte",
        )

    def test_admin_bookkeepers_requires_admin_authentication(self):
        response = self.client.get(
            reverse("api_admin_bookkeepers"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("ok"))

    def test_admin_bookkeepers_blocks_bookkeeper_session(self):
        bookkeeper = self._create_bookkeeper("blocked", BookkeeperAccount.STATUS_APPROVED)
        self._login_bookkeeper(bookkeeper)

        response = self.client.get(
            reverse("api_admin_bookkeepers"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json().get("ok"))

    def test_admin_bookkeepers_list_includes_safe_summary_data(self):
        admin = self._create_admin("list")
        self._login_admin(admin)
        approved = self._create_bookkeeper("approved", BookkeeperAccount.STATUS_APPROVED)
        suspended = self._create_bookkeeper("suspended", BookkeeperAccount.STATUS_SUSPENDED)
        self._create_bookkeeper("pending", BookkeeperAccount.STATUS_PENDING)
        self._create_client(approved, "001")

        response = self.client.get(
            reverse("api_admin_bookkeepers"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        ids = {row.get("id") for row in payload.get("bookkeepers", [])}
        self.assertEqual(ids, {approved.id, suspended.id})
        approved_payload = next(row for row in payload["bookkeepers"] if row["id"] == approved.id)
        self.assertEqual(approved_payload.get("client_count"), 1)
        self.assertIn("created_at", approved_payload)
        self.assertIn("last_login", approved_payload)

    def test_admin_bookkeepers_list_includes_pending_deactivation_request(self):
        admin = self._create_admin("list-request")
        self._login_admin(admin)
        account = self._create_bookkeeper("requesting", BookkeeperAccount.STATUS_APPROVED)
        request_obj = BookkeeperDeactivationRequest.objects.create(
            bookkeeper=account,
            reason="Retiring account.",
        )

        response = self.client.get(
            reverse("api_admin_bookkeepers"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["counts"].get("deactivation_requests"), 1)
        account_payload = next(row for row in payload["bookkeepers"] if row["id"] == account.id)
        self.assertEqual(account_payload["deactivation_request"]["id"], request_obj.id)
        self.assertEqual(account_payload["deactivation_request"]["reason"], "Retiring account.")

    def test_admin_bookkeepers_list_paginates_filtered_directory(self):
        admin = self._create_admin("pagination")
        self._login_admin(admin)
        for index in range(12):
            self._create_bookkeeper(f"page-{index:02d}", BookkeeperAccount.STATUS_APPROVED)
        self._create_bookkeeper("pending-hidden", BookkeeperAccount.STATUS_PENDING)

        response = self.client.get(
            reverse("api_admin_bookkeepers"),
            {"page": 2, "page_size": 5, "sort": "alpha"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["bookkeepers"]), 5)
        self.assertEqual(payload["counts"]["total"], 12)
        self.assertEqual(payload["pagination"], {
            "page": 2,
            "page_size": 5,
            "total_pages": 3,
            "total_count": 12,
            "start_index": 6,
            "end_index": 10,
            "has_previous": True,
            "has_next": True,
        })

    def test_admin_bookkeepers_pagination_uses_filtered_total_and_clamps_page(self):
        admin = self._create_admin("pagination-filter")
        self._login_admin(admin)
        for index in range(3):
            self._create_bookkeeper(f"rejected-{index}", BookkeeperAccount.STATUS_REJECTED)
        for index in range(4):
            self._create_bookkeeper(f"approved-{index}", BookkeeperAccount.STATUS_APPROVED)

        response = self.client.get(
            reverse("api_admin_bookkeepers"),
            {"status": "rejected", "page": 99, "page_size": 2},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["bookkeepers"]), 1)
        self.assertTrue(all(row["status"] == BookkeeperAccount.STATUS_REJECTED for row in payload["bookkeepers"]))
        self.assertEqual(payload["pagination"]["page"], 2)
        self.assertEqual(payload["pagination"]["total_pages"], 2)
        self.assertEqual(payload["pagination"]["total_count"], 3)
        self.assertEqual(payload["counts"]["rejected"], 3)

    def test_admin_bookkeepers_page_uses_rejected_status_wording(self):
        admin = self._create_admin("status-wording")
        self._login_admin(admin)

        response = self.client.get(reverse("admin_bookkeepers"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bookkeeper-status="rejected">Rejected</button>')
        self.assertContains(response, '<span>Rejected</span>')
        self.assertNotContains(response, 'data-bookkeeper-status="inactive">Inactive</button>')

    def test_deactivate_requires_admin_password_without_bad_request(self):
        admin = self._create_admin("deactivate-password")
        self._login_admin(admin)
        account = self._create_bookkeeper("needs-password", BookkeeperAccount.STATUS_APPROVED)

        response = self.client.post(
            reverse("api_admin_bookkeepers_deactivate", args=[account.id]),
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Admin password is required.")
        account.refresh_from_db()
        self.assertEqual(account.status, BookkeeperAccount.STATUS_APPROVED)

    def test_deactivate_with_password_creates_audit_log(self):
        admin = self._create_admin("deactivate")
        self._login_admin(admin)
        account = self._create_bookkeeper("active", BookkeeperAccount.STATUS_APPROVED)
        self._create_client(account, "002")

        response = self.client.post(
            reverse("api_admin_bookkeepers_deactivate", args=[account.id]),
            data={"admin_password": "AdminPass#123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        account.refresh_from_db()
        self.assertEqual(account.status, BookkeeperAccount.STATUS_SUSPENDED)
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATED,
            target_id=account.id,
        )
        self.assertEqual(audit_log.admin_id, admin.id)
        self.assertEqual(audit_log.metadata.get("client_count"), 1)

    def test_approve_deactivation_request_deactivates_and_marks_request_reviewed(self):
        admin = self._create_admin("approve-deactivation-request")
        self._login_admin(admin)
        account = self._create_bookkeeper("request-active", BookkeeperAccount.STATUS_APPROVED)
        request_obj = BookkeeperDeactivationRequest.objects.create(
            bookkeeper=account,
            reason="Closing the bookkeeping practice.",
        )

        response = self.client.post(
            reverse("api_admin_bookkeepers_deactivate", args=[account.id]),
            data={
                "admin_password": "AdminPass#123",
                "deactivation_request_id": request_obj.id,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        account.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(account.status, BookkeeperAccount.STATUS_SUSPENDED)
        self.assertEqual(request_obj.status, BookkeeperDeactivationRequest.STATUS_APPROVED)
        self.assertEqual(request_obj.reviewed_by_admin_id, admin.id)
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATED,
            target_id=account.id,
        )
        self.assertEqual(audit_log.metadata.get("decision_note"), "Closing the bookkeeping practice.")
        self.assertNotIn("admin_password", audit_log.metadata)

    def test_decline_deactivation_request_keeps_account_active(self):
        admin = self._create_admin("decline-deactivation-request")
        self._login_admin(admin)
        account = self._create_bookkeeper("decline-active", BookkeeperAccount.STATUS_APPROVED)
        request_obj = BookkeeperDeactivationRequest.objects.create(bookkeeper=account)

        response = self.client.post(
            reverse("api_admin_bookkeepers_deactivation_request_decline", args=[request_obj.id]),
            data={
                "admin_password": "AdminPass#123",
                "admin_note": "Keep active for now.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        account.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(account.status, BookkeeperAccount.STATUS_APPROVED)
        self.assertEqual(request_obj.status, BookkeeperDeactivationRequest.STATUS_REJECTED)
        self.assertEqual(request_obj.reviewed_by_admin_id, admin.id)
        self.assertTrue(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATION_DECLINED,
                target_id=account.id,
            ).exists()
        )
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATION_DECLINED,
            target_id=account.id,
        )
        self.assertEqual(audit_log.metadata.get("decision_note"), "Keep active for now.")
        self.assertNotIn("admin_password", audit_log.metadata)

    def test_reactivate_with_password_creates_audit_log(self):
        admin = self._create_admin("reactivate")
        self._login_admin(admin)
        account = self._create_bookkeeper("suspended", BookkeeperAccount.STATUS_SUSPENDED)

        response = self.client.post(
            reverse("api_admin_bookkeepers_reactivate", args=[account.id]),
            data={"admin_password": "AdminPass#123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        account.refresh_from_db()
        self.assertEqual(account.status, BookkeeperAccount.STATUS_APPROVED)
        self.assertTrue(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_REACTIVATED,
                target_id=account.id,
            ).exists()
        )

    def test_repeated_deactivation_returns_stale_without_duplicate_audit(self):
        admin = self._create_admin("repeat-deactivate")
        self._login_admin(admin)
        account = self._create_bookkeeper("repeat-deactivate", BookkeeperAccount.STATUS_APPROVED)
        request_data = {"admin_password": "AdminPass#123"}

        first_response = self.client.post(
            reverse("api_admin_bookkeepers_deactivate", args=[account.id]),
            data=request_data,
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("api_admin_bookkeepers_deactivate", args=[account.id]),
            data=request_data,
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json().get("code"), "stale_decision")
        self.assertTrue(second_response.json().get("refresh_required"))
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATED,
                target_id=account.id,
            ).count(),
            1,
        )

    def test_repeated_deactivation_decline_returns_stale_without_duplicate_audit(self):
        admin = self._create_admin("repeat-decline")
        self._login_admin(admin)
        account = self._create_bookkeeper("repeat-decline", BookkeeperAccount.STATUS_APPROVED)
        request_obj = BookkeeperDeactivationRequest.objects.create(bookkeeper=account)
        request_data = {
            "admin_password": "AdminPass#123",
            "admin_note": "Keep this account active.",
        }

        first_response = self.client.post(
            reverse("api_admin_bookkeepers_deactivation_request_decline", args=[request_obj.id]),
            data=request_data,
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("api_admin_bookkeepers_deactivation_request_decline", args=[request_obj.id]),
            data=request_data,
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json().get("code"), "stale_decision")
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATION_DECLINED,
                target_id=account.id,
            ).count(),
            1,
        )

    def test_repeated_reactivation_returns_stale_without_duplicate_audit(self):
        admin = self._create_admin("repeat-reactivate")
        self._login_admin(admin)
        account = self._create_bookkeeper("repeat-reactivate", BookkeeperAccount.STATUS_SUSPENDED)
        request_data = {"admin_password": "AdminPass#123"}

        first_response = self.client.post(
            reverse("api_admin_bookkeepers_reactivate", args=[account.id]),
            data=request_data,
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("api_admin_bookkeepers_reactivate", args=[account.id]),
            data=request_data,
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json().get("code"), "stale_decision")
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_REACTIVATED,
                target_id=account.id,
            ).count(),
            1,
        )

    def test_delete_is_blocked_when_bookkeeper_owns_clients(self):
        admin = self._create_admin("delete-block")
        self._login_admin(admin)
        account = self._create_bookkeeper("owns-clients", BookkeeperAccount.STATUS_SUSPENDED)
        self._create_client(account, "003")

        response = self.client.post(
            reverse("api_admin_bookkeepers_delete", args=[account.id]),
            data={"admin_password": "AdminPass#123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertIn("still owns clients", payload.get("message", ""))
        self.assertTrue(BookkeeperAccount.objects.filter(id=account.id).exists())

    def test_delete_zero_client_bookkeeper_requires_password_and_audits(self):
        admin = self._create_admin("delete-zero")
        self._login_admin(admin)
        account = self._create_bookkeeper("zero-client", BookkeeperAccount.STATUS_SUSPENDED)

        response = self.client.post(
            reverse("api_admin_bookkeepers_delete", args=[account.id]),
            data={"admin_password": "AdminPass#123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertFalse(BookkeeperAccount.objects.filter(id=account.id).exists())
        self.assertTrue(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_DELETED,
                target_id=account.id,
            ).exists()
        )
