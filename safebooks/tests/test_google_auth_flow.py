import json

from django.contrib.auth.hashers import check_password
from django.test import TestCase, override_settings
from django.urls import reverse

from safebooks.models import BookkeeperAccount
from safebooks.services.auth_service import authenticate_google_bookkeeper
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY, SESSION_GOOGLE_SIGNUP_PROFILE_KEY


class GoogleAuthFlowTests(TestCase):
    @override_settings(SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID="", SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_google_start_redirects_with_message_when_not_configured(self):
        response = self.client.get(reverse("auth_google_start"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertIn("auth_message=", response["Location"])

    def test_complete_google_signup_creates_pending_account_with_local_password(self):
        session = self.client.session
        session[SESSION_GOOGLE_SIGNUP_PROFILE_KEY] = {
            "google_sub": "google-sub-123",
            "email": "new-google@example.com",
            "full_name": "New Google User",
        }
        session.save()

        response = self.client.post(
            reverse("api_google_complete_signup"),
            data=json.dumps({
                "full_name": "New Google User",
                "username": "new_google_user",
                "password": "SafeBooks#123",
                "confirm_password": "SafeBooks#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("redirect_url"), reverse("pending_approval"))

        account = BookkeeperAccount.objects.get(email="new-google@example.com")
        self.assertEqual(account.google_sub, "google-sub-123")
        self.assertTrue(account.email_verified)
        self.assertEqual(account.status, BookkeeperAccount.STATUS_PENDING)
        self.assertTrue(check_password("SafeBooks#123", account.password_hash))

        session = self.client.session
        self.assertEqual(session.get(SESSION_BOOKKEEPER_ID_KEY), account.id)
        self.assertNotIn(SESSION_GOOGLE_SIGNUP_PROFILE_KEY, session)

    def test_complete_google_signup_validation_does_not_log_bad_request(self):
        session = self.client.session
        session[SESSION_GOOGLE_SIGNUP_PROFILE_KEY] = {
            "google_sub": "google-sub-validation",
            "email": "google-validation@example.com",
            "full_name": "Google Validation User",
        }
        session.save()

        response = self.client.post(
            reverse("api_google_complete_signup"),
            data=json.dumps({
                "full_name": "Google Validation User",
                "username": "",
                "password": "",
                "confirm_password": "",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertIn("Username is required.", payload.get("errors", []))
        self.assertFalse(BookkeeperAccount.objects.filter(email="google-validation@example.com").exists())

    def test_google_auth_links_existing_verified_email(self):
        account = BookkeeperAccount.objects.create(
            full_name="Existing User",
            email="existing-google@example.com",
            username="existing_google",
            password_hash="unused",
            status=BookkeeperAccount.STATUS_APPROVED,
            email_verified=True,
        )

        result = authenticate_google_bookkeeper({
            "google_sub": "existing-google-sub",
            "email": "existing-google@example.com",
            "full_name": "Existing User",
        })

        self.assertTrue(result.get("ok"))
        self.assertFalse(result.get("requires_signup_completion", False))
        account.refresh_from_db()
        self.assertEqual(account.google_sub, "existing-google-sub")
        # Linking and the primary factor alone are not a completed sign-in.
        self.assertIsNone(account.last_login)
