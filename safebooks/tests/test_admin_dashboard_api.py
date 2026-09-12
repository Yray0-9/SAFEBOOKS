from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from safebooks.models import AdminAccount, BookkeeperAccount, BookkeeperDeactivationRequest, Client
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class AdminDashboardApiTests(TestCase):
    def _create_admin(self) -> AdminAccount:
        return AdminAccount.objects.create(
            full_name="System Admin",
            email="system-admin@example.com",
            password_hash="not-used-in-test",
            is_active=True,
        )

    def _login_admin(self, account: AdminAccount) -> None:
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = account.id
        session.save()

    def _create_bookkeeper(self, suffix: str, status: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"bookkeeper_{suffix}",
            email=f"bookkeeper_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=status,
        )

    def test_admin_dashboard_requires_admin_authentication(self):
        response = self.client.get(reverse("api_admin_dashboard_summary"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Admin authentication required.")

    def test_admin_dashboard_blocks_bookkeeper_session(self):
        bookkeeper = self._create_bookkeeper("blocked", BookkeeperAccount.STATUS_APPROVED)
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = bookkeeper.id
        session.save()

        response = self.client.get(reverse("api_admin_dashboard_summary"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Admin access required.")

    def test_admin_dashboard_page_uses_even_quick_action_tiles(self):
        admin = self._create_admin()
        self._login_admin(admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage bookkeepers, approvals, and high-level account status.")
        self.assertContains(response, "Quick Actions")
        self.assertContains(response, "Review approvals")
        self.assertContains(response, "Manage bookkeepers")
        self.assertContains(response, "View audit log")
        self.assertNotContains(response, "admin-action-tile primary")
        self.assertContains(response, "Pending access and deactivation decisions.")
        self.assertContains(response, ">Rejected<")
        self.assertNotContains(response, "Inactive / rejected")

    def test_admin_dashboard_returns_action_center_review_data(self):
        admin = self._create_admin()
        self._login_admin(admin)

        pending = self._create_bookkeeper("pending", BookkeeperAccount.STATUS_PENDING)
        BookkeeperAccount.objects.filter(id=pending.id).update(created_at=timezone.now() - timedelta(days=8))
        pending.refresh_from_db()

        approved = self._create_bookkeeper("approved", BookkeeperAccount.STATUS_APPROVED)
        suspended = self._create_bookkeeper("suspended", BookkeeperAccount.STATUS_SUSPENDED)
        rejected = self._create_bookkeeper("rejected", BookkeeperAccount.STATUS_REJECTED)
        deactivation_request = BookkeeperDeactivationRequest.objects.create(
            bookkeeper=approved,
            reason="Leaving the practice",
        )

        for index in range(2):
            Client.objects.create(
                bookkeeper=suspended,
                client_name=f"Suspended Client {index}",
                tin_number=f"999-000-00{index}-000",
                location="Davao del Norte",
            )

        response = self.client.get(reverse("api_admin_dashboard_summary"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        self.assertEqual(payload["kpis"]["pending_approvals"], 1)
        self.assertEqual(payload["kpis"]["active_accounts"], 1)
        self.assertEqual(payload["kpis"]["total_bookkeepers"], 4)
        self.assertEqual(payload["status_overview"]["deactivated"], 1)
        self.assertEqual(payload["status_overview"]["rejected"], 1)
        self.assertNotIn("inactive", payload["status_overview"])
        self.assertEqual(payload["approval_readiness"]["overdue"], 1)

        needs_review = payload.get("needs_review", {})
        self.assertEqual(needs_review.get("total_attention"), 2)

        pending_reviews = needs_review.get("pending_approvals", [])
        self.assertEqual(len(pending_reviews), 1)
        self.assertEqual(pending_reviews[0]["id"], pending.id)
        self.assertGreaterEqual(pending_reviews[0]["waiting_days"], 8)

        self.assertNotIn("inactive_accounts", needs_review)
        self.assertNotIn("high_load_accounts", needs_review)

        deactivation_reviews = needs_review.get("deactivation_requests", [])
        self.assertEqual(len(deactivation_reviews), 1)
        self.assertEqual(deactivation_reviews[0]["id"], deactivation_request.id)
        self.assertEqual(deactivation_reviews[0]["bookkeeper_id"], approved.id)
        self.assertEqual(deactivation_reviews[0]["client_count"], 0)

        load_ids = {item["id"] for item in payload.get("load_snapshot", [])}
        self.assertIn(approved.id, load_ids)

    def test_non_actionable_statuses_do_not_increase_needs_review(self):
        admin = self._create_admin()
        self._login_admin(admin)
        self._create_bookkeeper("approved-only", BookkeeperAccount.STATUS_APPROVED)
        self._create_bookkeeper("suspended-only", BookkeeperAccount.STATUS_SUSPENDED)
        self._create_bookkeeper("rejected-only", BookkeeperAccount.STATUS_REJECTED)

        response = self.client.get(reverse("api_admin_dashboard_summary"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["kpis"]["total_bookkeepers"], 3)
        self.assertEqual(payload["needs_review"]["total_attention"], 0)
        self.assertEqual(payload["needs_review"]["pending_approvals"], [])
        self.assertEqual(payload["needs_review"]["deactivation_requests"], [])

    @patch("safebooks.services.admin_dashboard_service.HIGH_LOAD_THRESHOLD", 2)
    def test_high_load_kpi_counts_active_accounts_only(self):
        admin = self._create_admin()
        self._login_admin(admin)
        active = self._create_bookkeeper("active-load", BookkeeperAccount.STATUS_APPROVED)
        deactivated = self._create_bookkeeper("deactivated-load", BookkeeperAccount.STATUS_SUSPENDED)

        for account, tin_prefix in ((active, "101"), (deactivated, "202")):
            for index in range(2):
                Client.objects.create(
                    bookkeeper=account,
                    client_name=f"{account.full_name} Client {index}",
                    tin_number=f"{tin_prefix}-000-00{index}-000",
                    location="Davao del Norte",
                )

        response = self.client.get(reverse("api_admin_dashboard_summary"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["kpis"]["high_client_load"], 1)

        load_ids = {item["id"] for item in payload["load_snapshot"]}
        self.assertIn(active.id, load_ids)
        self.assertIn(deactivated.id, load_ids)

    def test_load_snapshot_pagination_and_navigation(self):
        admin = self._create_admin()
        self._login_admin(admin)

        # Create 7 approved bookkeepers with distinct client counts
        accounts = []
        for i in range(7):
            acc = self._create_bookkeeper(f"page-test-{i:02d}", BookkeeperAccount.STATUS_APPROVED)
            accounts.append(acc)
            for c_idx in range(i):
                Client.objects.create(
                    bookkeeper=acc,
                    client_name=f"Client {c_idx} of {acc.full_name}",
                    tin_number=f"888-000-{i:02d}{c_idx:02d}-000",
                    location="Davao del Norte",
                )

        # 1. Page 1 (default page_size=5)
        response = self.client.get(reverse("api_admin_dashboard_summary"), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])

        self.assertIn("load_snapshot_pagination", payload)
        pagination = payload["load_snapshot_pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 5)
        self.assertEqual(pagination["total_count"], 7)
        self.assertEqual(pagination["total_pages"], 2)
        self.assertEqual(pagination["start_index"], 1)
        self.assertEqual(pagination["end_index"], 5)
        self.assertFalse(pagination["has_previous"])
        self.assertTrue(pagination["has_next"])
        self.assertEqual(len(payload["load_snapshot"]), 5)

        # First item should have the highest client count (6 clients)
        self.assertEqual(payload["load_snapshot"][0]["id"], accounts[6].id)
        self.assertEqual(payload["load_snapshot"][0]["client_count"], 6)

        # 2. Page 2
        response_p2 = self.client.get(
            f"{reverse('api_admin_dashboard_summary')}?load_page=2&load_page_size=5",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response_p2.status_code, 200)
        payload_p2 = response_p2.json()
        self.assertTrue(payload_p2["ok"])

        pagination_p2 = payload_p2["load_snapshot_pagination"]
        self.assertEqual(pagination_p2["page"], 2)
        self.assertEqual(pagination_p2["page_size"], 5)
        self.assertEqual(pagination_p2["total_count"], 7)
        self.assertEqual(pagination_p2["total_pages"], 2)
        self.assertEqual(pagination_p2["start_index"], 6)
        self.assertEqual(pagination_p2["end_index"], 7)
        self.assertTrue(pagination_p2["has_previous"])
        self.assertFalse(pagination_p2["has_next"])
        self.assertEqual(len(payload_p2["load_snapshot"]), 2)

