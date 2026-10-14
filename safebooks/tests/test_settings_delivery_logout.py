"""Synthetic regression tests: no live email, user database, or browser session."""
import json
from pathlib import Path
import shutil
import subprocess
from datetime import date
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from django.db import DatabaseError
from django.test import Client as TestClient, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from safebooks.models import AdminAccount, BookkeeperAccount, BookkeeperAuditLog, Client, FinancialRecord, Period
from safebooks.services import auth_service, client_service
from safebooks.services.approval_notification_service import send_approval_decision_email
from safebooks.services.client_notification_service import send_financial_record_created_email
from safebooks.services.email_delivery_service import email_count_confirmed
from safebooks.services.feedback_service import submit_bookkeeper_feedback
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class SettingsDeliveryLogoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = BookkeeperAccount.objects.create(full_name="Synthetic Owner", username="settings-owner", email="owner@example.test", password_hash=make_password("SyntheticSettings#2026"), status="approved", client_details_password_required=False)
        self.ledger = Client.objects.create(bookkeeper=self.owner, client_name="Synthetic Client", tin_number="123456789000", location="Test City", email="client@example.test")
        self.authenticate(self.owner)

    def authenticate(self, account):
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY if isinstance(account, AdminAccount) else SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def record(self, entry_date=date(2026, 9, 15)):
        period, _ = Period.objects.get_or_create(client=self.ledger, year=entry_date.year, month=entry_date.month)
        return FinancialRecord.objects.create(bookkeeper=self.owner, client=self.ledger, period=period, entry_date=entry_date, total_amount="100.00")

    def test_delivery_counts_require_positive_integer_acknowledgement(self):
        for value in (0, -1, None, False, True, "1", {}):
            self.assertFalse(email_count_confirmed(value))
        self.assertTrue(email_count_confirmed(1))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    def test_client_notification_zero_or_exception_does_not_report_sent_or_log_private_details(self):
        record = self.record()
        with patch("safebooks.services.client_notification_service.send_mail", return_value=0):
            result = send_financial_record_created_email(record)
        self.assertFalse(result["sent"])
        self.assertFalse(result["skipped"])
        with patch("safebooks.services.client_notification_service.send_mail", side_effect=RuntimeError("SyntheticPrivateSMTPMarker")), self.assertLogs("safebooks.services.client_notification_service", level="WARNING") as logs:
            result = send_financial_record_created_email(record)
        self.assertFalse(result["sent"])
        self.assertNotIn("SyntheticPrivateSMTPMarker", " ".join(logs.output))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_local_preview_backend_skips_client_and_approval_inbox_delivery(self):
        with patch("safebooks.services.client_notification_service.send_mail") as client_mail:
            result = send_financial_record_created_email(self.record())
        self.assertFalse(result["sent"])
        self.assertTrue(result["skipped"])
        client_mail.assert_not_called()
        with patch("safebooks.services.approval_notification_service.send_mail") as approval_mail:
            result = send_approval_decision_email(self.owner, "bookkeeper.approved")
        self.assertEqual(result["status"], "skipped")
        approval_mail.assert_not_called()

    def test_zero_count_verification_and_reset_do_not_issue_codes_or_start_cooldown(self):
        self.owner.email_verified = False
        self.owner.save(update_fields=["email_verified"])
        with patch.object(auth_service, "send_mail", return_value=0):
            self.assertFalse(auth_service.send_email_verification_code(self.owner)["ok"])
            self.assertFalse(auth_service.send_password_reset_code(self.owner.email)["ok"])
        self.assertIsNone(cache.get(auth_service._email_verification_cache_key(self.owner.id, "code")))
        self.assertIsNone(cache.get(auth_service._email_verification_cache_key(self.owner.id, "sent")))
        self.assertIsNone(cache.get(auth_service._password_reset_cache_key(self.owner.email, "code")))
        self.assertIsNone(cache.get(auth_service._password_reset_cache_key(self.owner.email, "sent")))

    def test_login_alert_zero_or_failure_is_logged_without_preventing_login(self):
        self.owner.login_alerts_enabled = True
        with patch.object(auth_service, "send_mail", return_value=0), self.assertLogs("safebooks.services.auth_service", level="WARNING"):
            auth_service.complete_bookkeeper_login(self.owner)
        self.owner.refresh_from_db()
        self.assertIsNotNone(self.owner.last_login)
        self.owner.login_alerts_enabled = True
        with patch.object(auth_service, "send_mail", side_effect=RuntimeError("SyntheticPrivateSMTPMarker")), self.assertLogs("safebooks.services.auth_service", level="WARNING") as logs:
            auth_service.complete_bookkeeper_login(self.owner)
        self.assertNotIn("SyntheticPrivateSMTPMarker", " ".join(logs.output))

    @override_settings(SAFEBOOKS_FEEDBACK_ENABLED=True, SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL="developer@example.test", SAFEBOOKS_FEEDBACK_RATE_LIMIT_COUNT=10)
    def test_feedback_does_not_claim_inbox_delivery_for_preview_or_unacknowledged_email(self):
        data = {"category": "suggestion", "message": "Synthetic feedback for isolated testing", "page_path": "/settings/"}
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"), patch("safebooks.services.feedback_service.send_mail") as sender:
            self.assertFalse(submit_bookkeeper_feedback(self.owner, data)["ok"])
        sender.assert_not_called()
        for count in (0, None):
            with patch("safebooks.services.feedback_service.send_mail", return_value=count):
                self.assertFalse(submit_bookkeeper_feedback(self.owner, data)["ok"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", SAFEBOOKS_CLIENT_RECORD_EMAILS_ENABLED=False)
    def test_settings_render_saved_preferences_and_environment_delivery_limits_without_javascript(self):
        self.owner.login_alerts_enabled = True
        self.owner.client_record_email_notifications_enabled = False
        self.owner.save(update_fields=["login_alerts_enabled", "client_record_email_notifications_enabled"])
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emails will not reach inboxes.")
        self.assertContains(response, "disabled for this environment")
        self.assertContains(response, "not synced across devices")
        self.assertContains(response, 'id="settingsLoginAlertsStatus">On</span>')
        self.assertContains(response, 'id="settingsClientRecordEmailsStatus">Off</span>')
        self.assertContains(response, 'id="settingsLoginAlertsToggle" aria-label="Enable login alert emails" checked')

    def test_preference_and_audit_roll_back_together_on_audit_failure(self):
        for route, field in (("api_security_login_alerts", "login_alerts_enabled"), ("api_settings_client_record_email_notifications", "client_record_email_notifications_enabled"),
            ("api_security_client_details_access_preference", "client_details_password_required")):
            self.owner.refresh_from_db()
            previous = getattr(self.owner, field)
            with patch("safebooks.views.record_bookkeeper_audit", side_effect=DatabaseError("SyntheticPrivateDBMarker")):
                response = self.client.post(reverse(route), json.dumps({"enabled": not previous, "current_password": "SyntheticSettings#2026"}), content_type="application/json")
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("SyntheticPrivateDBMarker", response.content.decode())
            self.owner.refresh_from_db()
            self.assertEqual(getattr(self.owner, field), previous)
            self.assertFalse(BookkeeperAuditLog.objects.exists())

    def test_preference_success_and_invalid_input_preserve_ownership_and_audit(self):
        other = BookkeeperAccount.objects.create(full_name="Other", username="other", email="other@example.test", password_hash="unused", status="approved")
        for route in ("api_security_login_alerts", "api_settings_client_record_email_notifications"):
            response = self.client.post(reverse(route), json.dumps({"enabled": False}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
            response = self.client.post(reverse(route), json.dumps({"enabled": {}}), content_type="application/json")
            self.assertEqual(response.status_code, 400)
        other.refresh_from_db()
        self.assertFalse(other.login_alerts_enabled)
        self.assertTrue(other.client_record_email_notifications_enabled)
        self.assertEqual(BookkeeperAuditLog.objects.count(), 2)

    def test_logout_clears_session_even_when_admin_audit_fails(self):
        self.client.session.flush()
        self.client = TestClient()
        admin = AdminAccount.objects.create(full_name="Admin", email="admin@example.test", password_hash="unused")
        self.authenticate(admin)
        old_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        with patch("safebooks.views.record_admin_auth_event", side_effect=DatabaseError("SyntheticPrivateDBMarker")):
            response = self.client.post(reverse("api_logout"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        replay = TestClient()
        replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assertEqual(replay.get(reverse("api_admin_profile")).status_code, 401)

    def test_logout_storage_failure_reports_unconfirmed_result_and_csrf_is_required(self):
        engine = __import__(settings.SESSION_ENGINE, fromlist=["SessionStore"])
        with patch.object(engine.SessionStore, "flush", side_effect=DatabaseError("SyntheticPrivateDBMarker")):
            response = self.client.post(reverse("api_logout"))
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ok"])
        self.assertNotIn("SyntheticPrivateDBMarker", response.content.decode())
        guarded = TestClient(enforce_csrf_checks=True)
        guarded.cookies[settings.SESSION_COOKIE_NAME] = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(guarded.post(reverse("api_logout")).status_code, 403)


class ClientStatusTests(TestCase):
    today = date(2026, 10, 11)

    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(full_name="Synthetic Owner", username="status-owner", email="status@example.test", password_hash="unused", status="approved", client_details_password_required=False)
        self.ledger = Client.objects.create(bookkeeper=self.owner, client_name="Synthetic Client", tin_number="123456789000", location="Test City")
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.id
        bind_authenticated_session(session)
        session.save()
        self.clock = patch("safebooks.services.client_service.timezone.localdate", return_value=self.today)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def record(self, entry_date, **changes):
        period, _ = Period.objects.get_or_create(client=self.ledger, year=entry_date.year, month=entry_date.month)
        return FinancialRecord.objects.create(**{"bookkeeper": self.owner, "client": self.ledger, "period": period, "entry_date": entry_date, "total_amount": "100.00", **changes})

    def test_empty_and_future_periods_and_future_records_do_not_promote_client(self):
        Period.objects.create(client=self.ledger, year=2026, month=8)
        Period.objects.create(client=self.ledger, year=2026, month=9)
        self.record(date(2026, 11, 1))
        self.record(date(2026, 12, 1))
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "new")

    def test_two_past_recorded_periods_promote_but_duplicate_entries_in_one_period_do_not(self):
        self.record(date(2026, 9, 1))
        self.record(date(2026, 9, 15))
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "new")
        self.record(date(2026, 10, 1))
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "active")

    def test_twelve_month_inactivity_takes_priority_over_historical_active_periods(self):
        self.record(date(2025, 8, 1))
        self.record(date(2025, 10, 1))
        self.ledger.remarks = "active"
        self.ledger.save(update_fields=["remarks"])
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "separated")
        self.record(date(2026, 12, 1))
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "separated")

    def test_calendar_month_threshold_registration_fallback_and_manual_remarks_are_preserved(self):
        Client.objects.filter(pk=self.ledger.pk).update(date_registered=date(2025, 11, 1), remarks="active")
        self.ledger.refresh_from_db()
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "active")
        Client.objects.filter(pk=self.ledger.pk).update(date_registered=date(2025, 10, 31))
        self.ledger.refresh_from_db()
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "separated")

    def test_closed_clients_never_auto_reopen_and_foreign_owner_records_do_not_count(self):
        self.record(date(2026, 9, 1))
        self.record(date(2026, 10, 1))
        self.ledger.remarks = "closed"
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "closed")
        self.ledger.remarks = "new"
        other = BookkeeperAccount.objects.create(full_name="Other", username="other", email="other@example.test", password_hash="unused")
        FinancialRecord.objects.filter(client=self.ledger).update(bookkeeper=other)
        self.assertEqual(client_service.resolve_client_remarks(self.ledger), "new")
        self.assertEqual(client_service.list_clients_for_bookkeeper(self.owner)["clients"][0]["remarks"], "new")

    def test_directory_dashboard_analytics_and_detail_reads_show_same_status_without_saving_client(self):
        self.record(date(2025, 8, 1))
        self.record(date(2025, 10, 1))
        before = list(Client.objects.values())
        response = self.client.get(reverse("api_clients"))
        self.assertEqual(response.json()["clients"][0]["remarks"], "separated")
        self.assertEqual(list(Client.objects.values()), before)
        response = self.client.get(reverse("api_dashboard_summary"))
        self.assertEqual(response.json()["remarks_summary"]["separated"], 1)
        self.assertEqual(list(Client.objects.values()), before)
        response = self.client.get(reverse("api_analytics_summary"), {"client_id": self.ledger.id})
        self.assertEqual(response.json()["remarks_insight"]["level"], "separated")
        response = self.client.get(reverse("client_details", args=[self.ledger.id]))
        self.assertEqual(response.context["client"].remarks, "separated")
        self.assertEqual(list(Client.objects.values()), before)

    def test_owned_explicit_client_and_financial_writes_persist_status_without_bulk_changes(self):
        self.record(date(2025, 8, 1))
        self.record(date(2025, 10, 1))
        data = {"client_name": self.ledger.client_name, "tin_number": self.ledger.tin_number, "location": self.ledger.location}
        result = client_service.update_client_for_bookkeeper(self.owner, self.ledger.id, data)
        self.assertTrue(result["ok"])
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.remarks, "separated")
        result = client_service.delete_client_for_bookkeeper(self.owner, self.ledger.id)
        self.assertEqual(result["client"]["remarks"], "closed")
        result = client_service.reopen_client_for_bookkeeper(self.owner, self.ledger.id)
        self.assertEqual(result["client"]["remarks"], "separated")
        response = self.client.post(reverse("api_financial_records", args=[self.ledger.id]), json.dumps({"date": "2026-10-01", "frequency": "monthly", "line_items": [{"type_code": "Sales", "description": "Synthetic", "amount": "100.00"}]}), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.remarks, "active")

    def test_financial_edit_and_delete_recalculate_status_within_the_record_write(self):
        self.record(date(2025, 8, 1))
        self.record(date(2025, 10, 1))
        self.ledger.remarks = "active"
        self.ledger.save(update_fields=["remarks"])
        future = self.record(date(2026, 12, 1))
        route = reverse("api_financial_record_detail", args=[self.ledger.id, future.id])
        payload = {"date": "2026-10-01", "frequency": "monthly", "expected_revision": future.updated_at.isoformat(),
            "line_items": [{"type_code": "Sales", "description": "Synthetic", "amount": "100.00"}]}
        response = self.client.put(route, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.remarks, "active")
        response = self.client.delete(route, json.dumps({"expected_revision": response.json()["record"]["revision"]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.remarks, "separated")
        self.assertEqual(BookkeeperAuditLog.objects.count(), 2)


class SettingsBrowserHandlerTests(SimpleTestCase):
    @skipUnless(shutil.which("node"), "Node.js is required for browser-handler regression checks.")
    def test_settings_logout_and_status_browser_handlers(self):
        script = Path(__file__).parent / "js" / "test_settings_logout.cjs"
        result = subprocess.run([shutil.which("node"), str(script)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
