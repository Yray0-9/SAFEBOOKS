import json
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from safebooks.models import BookkeeperAccount
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


@override_settings(
    SAFEBOOKS_FEEDBACK_ENABLED=True,
    SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL="developer@example.com",
    SAFEBOOKS_FEEDBACK_EMAIL_TIMEOUT_SECONDS=2,
    SAFEBOOKS_FEEDBACK_RATE_LIMIT_COUNT=5,
    SAFEBOOKS_FEEDBACK_RATE_LIMIT_WINDOW_SECONDS=600,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="SafeBooks <no-reply@example.com>",
)
class FeedbackApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.bookkeeper = BookkeeperAccount.objects.create(
            full_name="Beta Bookkeeper",
            username="beta_bookkeeper",
            email="beta@example.com",
            password_hash=make_password("BetaPass#123"),
            email_verified=True,
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        self._login_bookkeeper(self.bookkeeper)

    def tearDown(self):
        cache.clear()

    def _login_bookkeeper(self, account):
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        session.save()

    def _payload(self, **overrides):
        payload = {
            "category": "suggestion",
            "message": "Please make the reports filter easier to understand.",
            "page_title": "Reports",
            "page_path": "/reports/",
        }
        payload.update(overrides)
        return payload

    def _post(self, payload=None):
        return self.client.post(
            reverse("api_submit_feedback"),
            data=json.dumps(self._payload() if payload is None else payload),
            content_type="application/json",
        )

    def test_approved_bookkeeper_can_send_feedback_to_configured_recipient(self):
        response = self._post({
            **self._payload(),
            "full_name": "Forged User",
            "email": "forged@example.com",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["developer@example.com"])
        self.assertEqual(sent_email.from_email, "SafeBooks <no-reply@example.com>")
        self.assertIn("Beta Bookkeeper", sent_email.subject)
        self.assertIn("Submitted by: Beta Bookkeeper", sent_email.body)
        self.assertIn("Username: beta_bookkeeper", sent_email.body)
        self.assertIn("Registered email: beta@example.com", sent_email.body)
        self.assertNotIn("Forged User", sent_email.body)
        self.assertNotIn("forged@example.com", sent_email.body)

    def test_page_context_discards_query_string_and_fragment(self):
        response = self._post(self._payload(page_path="/clients/14/?search=secret#section"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("Path: /clients/14/", mail.outbox[0].body)
        self.assertNotIn("search=secret", mail.outbox[0].body)
        self.assertNotIn("#section", mail.outbox[0].body)

    def test_anonymous_submission_is_rejected(self):
        self.client.post(reverse("api_logout"), content_type="application/json")

        response = self._post()

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(len(mail.outbox), 0)

    def test_pending_and_suspended_bookkeepers_are_rejected(self):
        for status in (BookkeeperAccount.STATUS_PENDING, BookkeeperAccount.STATUS_SUSPENDED):
            with self.subTest(status=status):
                cache.clear()
                self.bookkeeper.status = status
                self.bookkeeper.save(update_fields=["status"])
                self._login_bookkeeper(self.bookkeeper)

                response = self._post()

                self.assertEqual(response.status_code, 403)
                self.assertFalse(response.json().get("ok"))

    def test_invalid_category_message_and_page_context_are_rejected(self):
        cases = (
            (self._payload(category="other"), "invalid_category"),
            (self._payload(message="short"), "invalid_message"),
            (self._payload(message="x" * 2001), "invalid_message"),
            (self._payload(page_path="https://example.com/reports/"), "invalid_page_context"),
        )

        for payload, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                response = self._post(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json().get("code"), expected_code)

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SAFEBOOKS_FEEDBACK_ENABLED=False)
    def test_disabled_feature_rejects_submission_and_hides_widget(self):
        api_response = self._post()
        page_response = self.client.get(reverse("dashboard"))

        self.assertEqual(api_response.status_code, 403)
        self.assertEqual(api_response.json().get("code"), "feature_unavailable")
        self.assertNotContains(page_response, 'id="bookkeeperFeedbackWidget"')

    @override_settings(SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL="")
    def test_missing_recipient_rejects_submission_and_hides_widget(self):
        api_response = self._post()
        page_response = self.client.get(reverse("dashboard"))

        self.assertEqual(api_response.status_code, 403)
        self.assertEqual(api_response.json().get("code"), "feature_unavailable")
        self.assertNotContains(page_response, 'id="bookkeeperFeedbackWidget"')

    def test_enabled_feature_renders_clear_bookkeeper_widget(self):
        response = self.client.get(reverse("dashboard"))
        page_html = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="bookkeeperFeedbackWidget"')
        self.assertContains(response, 'id="bookkeeperFeedbackTrigger"')
        self.assertContains(response, "Send Feedback")
        self.assertContains(response, "Send Feedback to the Developer")
        self.assertContains(response, reverse("api_submit_feedback"))
        self.assertLess(
            page_html.index('id="bookkeeperFeedbackTrigger"'),
            page_html.index("data-bookkeeper-logout"),
        )

    @patch("safebooks.services.feedback_service.send_mail", side_effect=RuntimeError("SMTP unavailable"))
    def test_email_failure_returns_retryable_error_without_echoing_message(self, _send_mail):
        private_message = "This message should never be returned in an API error."

        response = self._post(self._payload(message=private_message))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json().get("code"), "delivery_failed")
        self.assertNotIn(private_message, response.content.decode("utf-8"))

    @patch("safebooks.services.feedback_service.send_mail", return_value=0)
    def test_zero_delivery_count_is_treated_as_failure(self, _send_mail):
        response = self._post()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json().get("code"), "delivery_failed")

    @override_settings(SAFEBOOKS_FEEDBACK_RATE_LIMIT_COUNT=2)
    @patch("safebooks.services.feedback_service.send_mail", return_value=1)
    def test_rate_limit_rejects_excess_submissions(self, _send_mail):
        first = self._post()
        second = self._post(self._payload(message="A second useful feedback message for testing."))
        third = self._post(self._payload(message="A third useful feedback message for testing."))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.json().get("code"), "rate_limited")

    def test_csrf_protection_is_required(self):
        csrf_client = Client(enforce_csrf_checks=True)
        session = csrf_client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.bookkeeper.id
        session.save()

        response = csrf_client.post(
            reverse("api_submit_feedback"),
            data=json.dumps(self._payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
