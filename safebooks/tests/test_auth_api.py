import json

from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY
from safebooks.tests.session_helpers import bind_authenticated_session


class PendingVerificationUiTests(TestCase):
    def sign_in(self, *, verified=True, status=BookkeeperAccount.STATUS_PENDING, google=False):
        account = BookkeeperAccount.objects.create(
            full_name="Pending Test", username="proof_ui", email="proof-ui@example.test",
            password_hash="synthetic-unused", status=status, email_verified=verified,
            google_sub="synthetic-google-proof" if google else None,
        )
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()
        return account

    def test_pending_page_offers_proof_submission_without_changing_account_on_get(self):
        account = self.sign_in()
        before = BookkeeperAccount.objects.get(pk=account.pk).__dict__.copy()
        response = self.client.get(reverse("pending_approval"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proof of bookkeeping")
        self.assertContains(response, "Business Permit")
        self.assertContains(response, "TESDA Certificate")
        self.assertContains(response, "No document has been uploaded.")
        self.assertRegex(response.content.decode(), r'id="verificationSubmitProof"[^>]*\bdisabled')
        self.assertContains(response, 'data-pending-logout', count=3)
        after = BookkeeperAccount.objects.get(pk=account.pk).__dict__.copy()
        before.pop('_state')
        after.pop('_state')
        self.assertEqual(before, after)
        self.assertEqual(self.client.get(reverse("dashboard")).url, reverse("pending_approval"))

    def test_google_pending_account_uses_the_same_page(self):
        self.sign_in(google=True)
        response = self.client.get(reverse("pending_approval"))
        self.assertContains(response, 'id="verificationProofFile"')

    def test_unverified_account_still_requires_email_verification(self):
        self.sign_in(verified=False)
        self.assertRedirects(self.client.get(reverse("pending_approval")), reverse("verify_email"), fetch_redirect_response=False)

    def test_approved_account_still_returns_to_workspace(self):
        self.sign_in(status=BookkeeperAccount.STATUS_APPROVED)
        self.assertRedirects(self.client.get(reverse("pending_approval")), reverse("dashboard"), fetch_redirect_response=False)


class AuthApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_register_then_login_success_sets_session(self):
        register_payload = {
            "full_name": "Login Success User",
            "email": "login-success@example.com",
            "username": "login_success",
            "password": "SafeBooks#123",
            "confirm_password": "SafeBooks#123",
        }

        register_response = self.client.post(
            reverse("api_register"),
            data=json.dumps(register_payload),
            content_type="application/json",
        )
        self.assertEqual(register_response.status_code, 201)
        self.assertFalse(BookkeeperAccount.objects.get(username="login_success").client_details_password_required)

        login_response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "login_success",
                "password": "SafeBooks#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 200)
        payload = login_response.json()
        self.assertTrue(payload.get("ok"))

        session = self.client.session
        self.assertIsNotNone(session.get(SESSION_BOOKKEEPER_ID_KEY))

    def test_login_invalid_credentials_returns_200_payload(self):
        account = BookkeeperAccount.objects.create(
            full_name="Invalid Login User",
            email="invalid-login@example.com",
            username="invalid_login",
            password_hash="pbkdf2_sha256$1000000$Y2mA0abcX8HnY1$hI3Y8J2wN8g7zXkQ9hP2Y6n2Q4S6D8w8rQ7fY3k8m2Q=",
        )
        account.password_hash = account.password_hash  # Keep explicit setup readable.
        account.save(update_fields=["password_hash"])

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "invalid_login",
                "password": "WrongPassword#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Incorrect password. Please try again.")
        self.assertEqual(payload.get("field"), "password")
        self.assertEqual(payload.get("error_code"), "invalid_credentials")

    def test_login_legacy_plaintext_password_hash_is_upgraded(self):
        account = BookkeeperAccount.objects.create(
            full_name="Legacy User",
            email="legacy-user@example.com",
            username="legacy_user",
            password_hash="LegacyPass#123",
        )

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "legacy_user",
                "password": "LegacyPass#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        account.refresh_from_db()
        self.assertNotEqual(account.password_hash, "LegacyPass#123")
        self.assertTrue(check_password("LegacyPass#123", account.password_hash))

    def test_login_unknown_account_points_to_identifier(self):
        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "not_existing_user",
                "password": "AnyPassword#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "No account found with that email or username.")
        self.assertEqual(payload.get("field"), "identifier")
        self.assertEqual(payload.get("error_code"), "invalid_credentials")

    def test_login_page_preserves_validation_and_password_controls(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/login.html")
        self.assertContains(response, 'novalidate data-auth-login-form')
        self.assertContains(response, 'id="loginFeedback" role="alert"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'autocomplete="username" required')
        self.assertContains(response, 'autocomplete="current-password" required')
        self.assertContains(response, 'data-password-toggle-target="login_password"')
        self.assertContains(response, "Please enter your password.")
        self.assertContains(response, "Please enter your email or username.")
