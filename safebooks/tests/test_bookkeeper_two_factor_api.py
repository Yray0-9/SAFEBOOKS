import base64
import json
import pyotp
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from safebooks.models import BookkeeperAccount, BookkeeperAuditLog
from safebooks.views import (
    SESSION_BOOKKEEPER_ID_KEY,
    SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY,
    SESSION_BOOKKEEPER_TWO_FACTOR_SETUP_KEY,
)


class BookkeeperTwoFactorApiTests(TestCase):
    password = "SecurePassword#123"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _create_bookkeeper(self, suffix: str = "1", two_factor: bool = False, secret: str = "") -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Bookkeeper {suffix}",
            username=f"bookkeeper_{suffix}",
            email=f"bookkeeper_{suffix}@example.com",
            password_hash=make_password(self.password),
            status=BookkeeperAccount.STATUS_APPROVED,
            email_verified=True,
            two_factor_enabled=two_factor,
            two_factor_secret=secret,
            two_factor_confirmed_at=timezone.now() if two_factor else None,
        )

    def _login_bookkeeper_session(self, bookkeeper: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = bookkeeper.id
        session.save()

    def test_default_two_factor_is_disabled(self):
        bookkeeper = self._create_bookkeeper("default")
        self.assertFalse(bookkeeper.two_factor_enabled)
        self.assertEqual(bookkeeper.two_factor_secret, "")
        self.assertIsNone(bookkeeper.two_factor_confirmed_at)

        self._login_bookkeeper_session(bookkeeper)
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context.get("two_factor_enabled"))

    def test_setup_requires_authentication(self):
        response = self.client.post(reverse("api_bookkeeper_two_factor_setup"))
        self.assertEqual(response.status_code, 401)
        payload = response.json()
        self.assertFalse(payload.get("ok"))

    def test_setup_generates_secret_uri_and_svg_qr(self):
        bookkeeper = self._create_bookkeeper("setup")
        self._login_bookkeeper_session(bookkeeper)

        response = self.client.post(reverse("api_bookkeeper_two_factor_setup"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("secret"))
        self.assertIn("otpauth://totp/", payload.get("provisioning_uri"))
        self.assertTrue(payload.get("qr_code_data_url").startswith("data:image/svg+xml;base64,"))

        # Check SVG QR code decodes properly
        raw_b64 = payload["qr_code_data_url"].split(",", 1)[1]
        decoded_svg = base64.b64decode(raw_b64).decode("utf-8")
        self.assertIn("<svg", decoded_svg)

        # Confirm bookkeeper in DB is not enabled yet
        bookkeeper.refresh_from_db()
        self.assertFalse(bookkeeper.two_factor_enabled)

    def test_confirm_requires_prior_setup(self):
        bookkeeper = self._create_bookkeeper("confirm_no_setup")
        self._login_bookkeeper_session(bookkeeper)

        response = self.client.post(
            reverse("api_bookkeeper_two_factor_confirm"),
            data=json.dumps({"code": "123456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertIn("expired", payload.get("message", "").lower())

    def test_confirm_rejects_invalid_code(self):
        bookkeeper = self._create_bookkeeper("confirm_invalid")
        self._login_bookkeeper_session(bookkeeper)

        # Call setup first
        setup_resp = self.client.post(reverse("api_bookkeeper_two_factor_setup"))
        self.assertEqual(setup_resp.status_code, 200)

        # Confirm with wrong code
        response = self.client.post(
            reverse("api_bookkeeper_two_factor_confirm"),
            data=json.dumps({"code": "000000"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertIn("invalid", payload.get("message", "").lower())

        bookkeeper.refresh_from_db()
        self.assertFalse(bookkeeper.two_factor_enabled)

    def test_confirm_activates_two_factor_and_records_audit(self):
        bookkeeper = self._create_bookkeeper("confirm_valid")
        self._login_bookkeeper_session(bookkeeper)

        setup_resp = self.client.post(reverse("api_bookkeeper_two_factor_setup"))
        secret = setup_resp.json()["secret"]

        valid_code = pyotp.TOTP(secret).now()
        response = self.client.post(
            reverse("api_bookkeeper_two_factor_confirm"),
            data=json.dumps({"code": valid_code}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("two_factor_enabled"))

        bookkeeper.refresh_from_db()
        self.assertTrue(bookkeeper.two_factor_enabled)
        self.assertEqual(bookkeeper.two_factor_secret, secret)
        self.assertIsNotNone(bookkeeper.two_factor_confirmed_at)

        # Verify audit log was recorded
        audit = BookkeeperAuditLog.objects.filter(
            bookkeeper=bookkeeper,
            action_type=BookkeeperAuditLog.ACTION_TWO_FACTOR_ENABLED,
        ).first()
        self.assertIsNotNone(audit)

    def test_disable_requires_password_verification(self):
        secret = pyotp.random_base32()
        bookkeeper = self._create_bookkeeper("disable", two_factor=True, secret=secret)
        self._login_bookkeeper_session(bookkeeper)

        # Try wrong password
        response = self.client.post(
            reverse("api_bookkeeper_two_factor_disable"),
            data=json.dumps({"current_password": "WrongPassword#999"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertIn("password", payload.get("message", "").lower())

        # Bookkeeper still enabled
        bookkeeper.refresh_from_db()
        self.assertTrue(bookkeeper.two_factor_enabled)

        # Provide correct password
        response = self.client.post(
            reverse("api_bookkeeper_two_factor_disable"),
            data=json.dumps({"current_password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertFalse(payload.get("two_factor_enabled"))

        bookkeeper.refresh_from_db()
        self.assertFalse(bookkeeper.two_factor_enabled)
        self.assertEqual(bookkeeper.two_factor_secret, "")
        self.assertIsNone(bookkeeper.two_factor_confirmed_at)

        # Verify audit log
        audit = BookkeeperAuditLog.objects.filter(
            bookkeeper=bookkeeper,
            action_type=BookkeeperAuditLog.ACTION_TWO_FACTOR_DISABLED,
        ).first()
        self.assertIsNotNone(audit)

    def test_login_flow_with_two_factor_enabled(self):
        secret = pyotp.random_base32()
        bookkeeper = self._create_bookkeeper("login_2fa", two_factor=True, secret=secret)

        # Step 1: Initial login attempt with username and password
        login_response = self.client.post(
            reverse("api_login"),
            data=json.dumps({"identifier": bookkeeper.username, "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        login_payload = login_response.json()
        self.assertTrue(login_payload.get("ok"))
        self.assertTrue(login_payload.get("requires_two_factor"))
        self.assertEqual(login_payload.get("role"), "bookkeeper")

        # Session should have challenge, not authenticated bookkeeper id
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
        self.assertIn(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, self.client.session)

        # Step 2: Verification with invalid code
        verify_fail = self.client.post(
            reverse("api_bookkeeper_two_factor_login_verify"),
            data=json.dumps({"code": "000000"}),
            content_type="application/json",
        )
        self.assertEqual(verify_fail.status_code, 200)
        self.assertFalse(verify_fail.json().get("ok"))
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

        # Step 3: Verification with valid code
        valid_code = pyotp.TOTP(secret).now()
        verify_success = self.client.post(
            reverse("api_bookkeeper_two_factor_login_verify"),
            data=json.dumps({"code": valid_code}),
            content_type="application/json",
        )
        self.assertEqual(verify_success.status_code, 200)
        success_payload = verify_success.json()
        self.assertTrue(success_payload.get("ok"))
        self.assertEqual(success_payload.get("redirect_url"), reverse("dashboard"))

        # Bookkeeper is now authenticated
        self.assertEqual(self.client.session.get(SESSION_BOOKKEEPER_ID_KEY), bookkeeper.id)
        self.assertNotIn(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, self.client.session)

    def test_login_flow_via_delegated_admin_verify_route(self):
        """Test fallback delegation if client posts to api_admin_two_factor_login_verify with a bookkeeper challenge."""
        secret = pyotp.random_base32()
        bookkeeper = self._create_bookkeeper("delegation", two_factor=True, secret=secret)

        self.client.post(
            reverse("api_login"),
            data=json.dumps({"identifier": bookkeeper.email, "password": self.password}),
            content_type="application/json",
        )

        valid_code = pyotp.TOTP(secret).now()
        response = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": valid_code}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertEqual(self.client.session.get(SESSION_BOOKKEEPER_ID_KEY), bookkeeper.id)
