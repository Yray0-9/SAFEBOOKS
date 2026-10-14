from safebooks.tests.session_helpers import bind_authenticated_session

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core import mail
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount
from safebooks.services.admin_approvals_service import approve_bookkeeper
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class AdminApprovalsApiTests(TestCase):
    def _create_admin(self, suffix: str) -> AdminAccount:
        return AdminAccount.objects.create(
            full_name=f"Admin {suffix}",
            email=f"admin_{suffix}@example.com",
            password_hash="not-used-in-test",
            is_active=True,
        )

    def _login_admin(self, account: AdminAccount) -> None:
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def _create_bookkeeper(self, suffix: str, status: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"bookkeeper_{suffix}",
            email=f"bookkeeper_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=status,
        )

    def _login_bookkeeper(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def test_admin_approvals_requires_admin_authentication(self):
        response = self.client.get(
            reverse("api_admin_approvals"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Admin authentication required.")

    def test_admin_approvals_blocks_bookkeeper_session(self):
        bookkeeper = self._create_bookkeeper("bk", BookkeeperAccount.STATUS_APPROVED)
        self._login_bookkeeper(bookkeeper)

        response = self.client.get(
            reverse("api_admin_approvals"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 403)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Admin access required.")

    def test_admin_approvals_page_uses_bounded_queue_layout(self):
        admin = self._create_admin("page")
        self._login_admin(admin)

        response = self.client.get(reverse("admin_approvals"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review bookkeeper access requests and track approval outcomes.")
        self.assertContains(response, "admin-approval-queue-card")
        self.assertContains(response, "admin-approvals-table-wrap")
        self.assertContains(response, "admin-approval-pagination")
        self.assertContains(response, "approvalsPreviousPage")
        self.assertContains(response, "approvalsNextPage")
        self.assertContains(response, "Decision email preview")
        self.assertNotContains(response, "admin-card h-100")
        self.assertNotContains(response, "View details")
        self.assertNotContains(response, "Select a request to preview the decision message.")

    def test_admin_approvals_list_returns_counts_and_rows(self):
        admin = self._create_admin("list")
        self._login_admin(admin)

        pending = self._create_bookkeeper("pending", BookkeeperAccount.STATUS_PENDING)
        approved = self._create_bookkeeper("approved", BookkeeperAccount.STATUS_APPROVED)
        rejected = self._create_bookkeeper("rejected", BookkeeperAccount.STATUS_REJECTED)
        self._create_bookkeeper("suspended", BookkeeperAccount.STATUS_SUSPENDED)

        response = self.client.get(
            reverse("api_admin_approvals"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        counts = payload.get("counts", {})
        self.assertEqual(counts.get("pending"), 1)
        self.assertEqual(counts.get("approved"), 1)
        self.assertEqual(counts.get("rejected"), 1)
        self.assertEqual(payload.get("total_count"), 3)

        approvals = payload.get("approvals", [])
        approval_ids = {row.get("id") for row in approvals}
        self.assertEqual(approval_ids, {pending.id, approved.id, rejected.id})
        pending_payload = next(row for row in approvals if row.get("id") == pending.id)
        self.assertIn("email_verified", pending_payload)
        self.assertIn("google_linked", pending_payload)
        self.assertIn("notification_preview", pending_payload)

    def test_admin_approvals_list_paginates_requests(self):
        admin = self._create_admin("pagination")
        self._login_admin(admin)
        for index in range(12):
            self._create_bookkeeper(f"paged-{index:02d}", BookkeeperAccount.STATUS_APPROVED)

        first_response = self.client.get(
            reverse("api_admin_approvals"),
            {"page": 1, "page_size": 10},
            HTTP_ACCEPT="application/json",
        )
        second_response = self.client.get(
            reverse("api_admin_approvals"),
            {"page": 2, "page_size": 10},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        first_payload = first_response.json()
        second_payload = second_response.json()
        self.assertEqual(len(first_payload.get("approvals", [])), 10)
        self.assertEqual(len(second_payload.get("approvals", [])), 2)
        self.assertEqual(first_payload.get("pagination"), {
            "page": 1,
            "page_size": 10,
            "total_pages": 2,
            "total_count": 12,
            "start_index": 1,
            "end_index": 10,
            "has_previous": False,
            "has_next": True,
        })
        self.assertEqual(second_payload.get("pagination", {}).get("start_index"), 11)
        self.assertEqual(second_payload.get("pagination", {}).get("end_index"), 12)
        self.assertTrue(second_payload.get("pagination", {}).get("has_previous"))
        self.assertFalse(second_payload.get("pagination", {}).get("has_next"))

    def test_admin_approvals_pagination_uses_filtered_total_and_clamps_page(self):
        admin = self._create_admin("pagination-filter")
        self._login_admin(admin)
        for index in range(12):
            self._create_bookkeeper(f"approved-{index:02d}", BookkeeperAccount.STATUS_APPROVED)
        self._create_bookkeeper("pending-filter", BookkeeperAccount.STATUS_PENDING)

        response = self.client.get(
            reverse("api_admin_approvals"),
            {"status": "approved", "page": 99, "page_size": 10},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("total_count"), 13)
        self.assertEqual(len(payload.get("approvals", [])), 2)
        self.assertEqual(payload.get("pagination", {}).get("page"), 2)
        self.assertEqual(payload.get("pagination", {}).get("total_pages"), 2)
        self.assertEqual(payload.get("pagination", {}).get("total_count"), 12)

    def test_admin_approvals_can_approve_pending(self):
        admin = self._create_admin("approve")
        self._login_admin(admin)
        pending = self._create_bookkeeper("pending-approve", BookkeeperAccount.STATUS_PENDING)

        response = self.client.post(
            reverse("api_admin_approvals_approve", args=[pending.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        pending.refresh_from_db()
        self.assertEqual(pending.status, BookkeeperAccount.STATUS_APPROVED)
        self.assertIsNotNone(pending.approved_at)
        self.assertEqual(pending.approved_by_admin_id, admin.id)
        self.assertEqual(pending.rejection_reason, "")
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
            target_id=pending.id,
        )
        self.assertEqual(audit_log.admin_id, admin.id)
        self.assertEqual(audit_log.target_model, "BookkeeperAccount")

    def test_admin_approvals_can_approve_rejected(self):
        admin = self._create_admin("reapprove")
        self._login_admin(admin)
        rejected = self._create_bookkeeper("rejected-approve", BookkeeperAccount.STATUS_REJECTED)
        rejected.rejected_at = timezone.now()
        rejected.rejection_reason = "Incomplete details"
        rejected.save(update_fields=["rejected_at", "rejection_reason"])

        response = self.client.post(
            reverse("api_admin_approvals_approve", args=[rejected.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        rejected.refresh_from_db()
        self.assertEqual(rejected.status, BookkeeperAccount.STATUS_APPROVED)
        self.assertIsNone(rejected.rejected_at)
        self.assertEqual(rejected.rejection_reason, "")

    def test_admin_approvals_can_reject_pending_with_reason(self):
        admin = self._create_admin("reject")
        self._login_admin(admin)
        pending = self._create_bookkeeper("pending-reject", BookkeeperAccount.STATUS_PENDING)

        response = self.client.post(
            reverse("api_admin_approvals_reject", args=[pending.id]),
            data={"rejection_reason": "Missing requirements"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        pending.refresh_from_db()
        self.assertEqual(pending.status, BookkeeperAccount.STATUS_REJECTED)
        self.assertIsNotNone(pending.rejected_at)
        self.assertEqual(pending.rejection_reason, "Missing requirements")
        self.assertIsNone(pending.approved_at)
        self.assertIsNone(pending.approved_by_admin_id)
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_REJECTED,
            target_id=pending.id,
        )
        self.assertEqual(audit_log.admin_id, admin.id)
        self.assertEqual(audit_log.metadata.get("bookkeeper_email"), pending.email)
        self.assertEqual(audit_log.metadata.get("decision_note"), "Missing requirements")
        self.assertNotIn("password", audit_log.metadata)

    def test_admin_approvals_reject_requires_reason(self):
        admin = self._create_admin("reject-reason")
        self._login_admin(admin)
        pending = self._create_bookkeeper("pending-no-reason", BookkeeperAccount.STATUS_PENDING)

        response = self.client.post(
            reverse("api_admin_approvals_reject", args=[pending.id]),
            data={"rejection_reason": "   "},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Rejection reason is required.")
        pending.refresh_from_db()
        self.assertEqual(pending.status, BookkeeperAccount.STATUS_PENDING)
        self.assertFalse(AdminAuditLog.objects.filter(target_id=pending.id).exists())

    def test_admin_approvals_reject_requires_pending(self):
        admin = self._create_admin("reject-guard")
        self._login_admin(admin)
        approved = self._create_bookkeeper("approved-reject", BookkeeperAccount.STATUS_APPROVED)

        response = self.client.post(
            reverse("api_admin_approvals_reject", args=[approved.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "stale_decision")
        self.assertTrue(payload.get("refresh_required"))

    def test_repeated_approval_returns_stale_without_duplicate_audit(self):
        admin = self._create_admin("repeat-approve")
        self._login_admin(admin)
        pending = self._create_bookkeeper("repeat-approve", BookkeeperAccount.STATUS_PENDING)

        first_response = self.client.post(
            reverse("api_admin_approvals_approve", args=[pending.id]),
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("api_admin_approvals_approve", args=[pending.id]),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json().get("code"), "stale_decision")
        self.assertTrue(second_response.json().get("refresh_required"))
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
                target_id=pending.id,
            ).count(),
            1,
        )

    def test_repeated_rejection_returns_stale_without_duplicate_audit(self):
        admin = self._create_admin("repeat-reject")
        self._login_admin(admin)
        pending = self._create_bookkeeper("repeat-reject", BookkeeperAccount.STATUS_PENDING)
        request_data = {"rejection_reason": "Incomplete access requirements"}

        first_response = self.client.post(
            reverse("api_admin_approvals_reject", args=[pending.id]),
            data=request_data,
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("api_admin_approvals_reject", args=[pending.id]),
            data=request_data,
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json().get("code"), "stale_decision")
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_REJECTED,
                target_id=pending.id,
            ).count(),
            1,
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=True,
    )
    def test_approval_sends_safe_email_and_records_delivery(self):
        admin = self._create_admin("approval-email")
        self._login_admin(admin)
        pending = self._create_bookkeeper("approval-email", BookkeeperAccount.STATUS_PENDING)

        response = self.client.post(
            reverse("api_admin_approvals_approve", args=[pending.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("email_delivery", {}).get("status"), "sent")
        self.assertIn("Decision email accepted for delivery", payload.get("message", ""))
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [pending.email])
        self.assertIn("approved", sent_email.subject.lower())
        self.assertIn("sign in", sent_email.body.lower())
        self.assertNotIn(pending.password_hash, sent_email.body)
        self.assertNotIn("verification code", sent_email.body.lower())

        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
            target_id=pending.id,
        )
        delivery = audit_log.metadata.get("email_delivery", {})
        self.assertEqual(delivery.get("status"), "sent")
        self.assertEqual(delivery.get("retry_count"), 0)
        self.assertTrue(delivery.get("attempted_at"))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=True,
    )
    def test_rejection_email_includes_saved_reason_without_credentials(self):
        admin = self._create_admin("rejection-email")
        self._login_admin(admin)
        pending = self._create_bookkeeper("rejection-email", BookkeeperAccount.STATUS_PENDING)
        rejection_reason = "Identity document needs correction"

        response = self.client.post(
            reverse("api_admin_approvals_reject", args=[pending.id]),
            data={"rejection_reason": rejection_reason},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("email_delivery", {}).get("status"), "sent")
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn(rejection_reason, sent_email.body)
        self.assertIn("contact your SafeBooks system manager", sent_email.body)
        self.assertNotIn(pending.password_hash, sent_email.body)
        self.assertNotIn("verification code", sent_email.body.lower())

    @override_settings(SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=False)
    def test_disabled_decision_email_is_reported_as_skipped(self):
        admin = self._create_admin("email-skipped")
        self._login_admin(admin)
        pending = self._create_bookkeeper("email-skipped", BookkeeperAccount.STATUS_PENDING)

        response = self.client.post(
            reverse("api_admin_approvals_approve", args=[pending.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("email_delivery", {}).get("status"), "skipped")
        self.assertIn("Decision email skipped", payload.get("message", ""))
        pending.refresh_from_db()
        self.assertEqual(pending.status, BookkeeperAccount.STATUS_APPROVED)

    @override_settings(SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=True)
    @patch(
        "safebooks.services.approval_notification_service.send_mail",
        side_effect=RuntimeError("SMTP unavailable"),
    )
    def test_email_failure_does_not_undo_approval(self, mocked_send_mail):
        admin = self._create_admin("email-failed")
        self._login_admin(admin)
        pending = self._create_bookkeeper("email-failed", BookkeeperAccount.STATUS_PENDING)

        response = self.client.post(
            reverse("api_admin_approvals_approve", args=[pending.id]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("email_delivery", {}).get("status"), "failed")
        self.assertIn("Decision saved, but email delivery failed", payload.get("message", ""))
        pending.refresh_from_db()
        self.assertEqual(pending.status, BookkeeperAccount.STATUS_APPROVED)
        self.assertEqual(mocked_send_mail.call_count, 1)
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
            target_id=pending.id,
        )
        self.assertEqual(audit_log.metadata.get("email_delivery", {}).get("status"), "failed")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=True,
    )
    def test_failed_email_can_retry_once_without_repeating_decision(self):
        admin = self._create_admin("email-retry")
        self._login_admin(admin)
        pending = self._create_bookkeeper("email-retry", BookkeeperAccount.STATUS_PENDING)

        with patch(
            "safebooks.services.approval_notification_service.send_mail",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            approval_response = self.client.post(
                reverse("api_admin_approvals_approve", args=[pending.id]),
                content_type="application/json",
            )
        self.assertEqual(approval_response.status_code, 200)
        self.assertEqual(approval_response.json().get("email_delivery", {}).get("status"), "failed")

        retry_response = self.client.post(
            reverse("api_admin_approvals_retry_email", args=[pending.id]),
            content_type="application/json",
        )

        self.assertEqual(retry_response.status_code, 200)
        retry_payload = retry_response.json()
        self.assertTrue(retry_payload.get("ok"))
        self.assertEqual(retry_payload.get("email_delivery", {}).get("status"), "sent")
        self.assertEqual(retry_payload.get("email_delivery", {}).get("retry_count"), 1)
        self.assertEqual(len(mail.outbox), 1)
        pending.refresh_from_db()
        self.assertEqual(pending.status, BookkeeperAccount.STATUS_APPROVED)
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
                target_id=pending.id,
            ).count(),
            1,
        )

        repeated_retry = self.client.post(
            reverse("api_admin_approvals_retry_email", args=[pending.id]),
            content_type="application/json",
        )
        self.assertEqual(repeated_retry.status_code, 400)
        self.assertFalse(repeated_retry.json().get("ok"))
        self.assertEqual(len(mail.outbox), 1)


class AdminApprovalConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_two_admins_cannot_create_duplicate_approval_decisions(self):
        first_admin = AdminAccount.objects.create(
            full_name="First Concurrent Admin",
            email="first-concurrent-admin@example.com",
            password_hash="not-used-in-test",
            is_active=True,
        )
        second_admin = AdminAccount.objects.create(
            full_name="Second Concurrent Admin",
            email="second-concurrent-admin@example.com",
            password_hash="not-used-in-test",
            is_active=True,
        )
        pending = BookkeeperAccount.objects.create(
            full_name="Concurrent Bookkeeper",
            username="concurrent_bookkeeper",
            email="concurrent-bookkeeper@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_PENDING,
        )
        start_barrier = Barrier(2)

        def run_approval(admin_id):
            close_old_connections()
            try:
                admin = AdminAccount.objects.get(id=admin_id)
                start_barrier.wait(timeout=5)
                return approve_bookkeeper(admin, pending.id)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(run_approval, [first_admin.id, second_admin.id]))

        self.assertEqual(sum(1 for result in results if result.get("ok")), 1)
        stale_results = [result for result in results if result.get("code") == "stale_decision"]
        self.assertEqual(len(stale_results), 1)
        self.assertTrue(stale_results[0].get("refresh_required"))
        self.assertEqual(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
                target_id=pending.id,
            ).count(),
            1,
        )
