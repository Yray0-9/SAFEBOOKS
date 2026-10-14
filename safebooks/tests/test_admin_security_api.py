from safebooks.tests.session_helpers import bind_authenticated_session

import base64
import json

import pyotp
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import Client as TestClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount
from safebooks.services.admin_security_service import verify_admin_two_factor_login
from safebooks.views import (
    SESSION_ADMIN_AUTHENTICATED_AT_KEY,
    SESSION_ADMIN_ID_KEY,
    SESSION_ADMIN_LAST_ACTIVITY_AT_KEY,
    SESSION_ADMIN_TWO_FACTOR_SETUP_KEY,
    SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY,
    SESSION_BOOKKEEPER_ID_KEY,
)


class AdminSecurityApiTests(TestCase):
    password = "AdminPass#123"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _create_admin(self, suffix: str) -> AdminAccount:
        return AdminAccount.objects.create(
            full_name=f"Admin {suffix}",
            email=f"admin_security_{suffix}@example.com",
            password_hash=make_password(self.password),
            is_active=True,
        )

    def _login_admin_session(self, admin: AdminAccount) -> None:
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = admin.id
        bind_authenticated_session(session)
        session.save()

    def _enable_two_factor(self, admin: AdminAccount) -> tuple[str, list[str]]:
        self._login_admin_session(admin)
        setup_response = self.client.post(
            reverse("api_admin_two_factor_setup"),
            data=json.dumps({"current_password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(setup_response.status_code, 200)
        setup_payload = setup_response.json()
        self.assertTrue(setup_payload.get("ok"))
        secret = setup_payload["secret"]

        confirm_response = self.client.post(
            reverse("api_admin_two_factor_confirm"),
            data=json.dumps({"code": pyotp.TOTP(secret).now()}),
            content_type="application/json",
        )
        self.assertEqual(confirm_response.status_code, 200)
        confirm_payload = confirm_response.json()
        self.assertTrue(confirm_payload.get("ok"))
        self.assertEqual(confirm_response["Cache-Control"], "no-store")
        recovery_codes = confirm_payload.get("recovery_codes")
        self.assertIsInstance(recovery_codes, list)
        self.assertEqual(len(recovery_codes), 8)
        return secret, recovery_codes

    def _start_two_factor_login(self, admin: AdminAccount):
        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({"identifier": admin.email, "password": self.password}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertTrue(response.json().get("requires_two_factor"))
        return response

    def test_two_factor_is_disabled_by_default(self):
        admin = self._create_admin("default")
        self._login_admin_session(admin)

        response = self.client.get(reverse("api_admin_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["two_factor"]["enabled"])
        self.assertEqual(payload["two_factor"]["recovery_codes_remaining"], 0)

    def test_admin_profile_exposes_status_but_never_secret_or_recovery_hashes(self):
        admin = self._create_admin("profile")
        secret, recovery_codes = self._enable_two_factor(admin)

        response = self.client.get(reverse("api_admin_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["two_factor"]["enabled"])
        self.assertEqual(payload["two_factor"]["recovery_codes_remaining"], 8)
        response_text = response.content.decode("utf-8")
        self.assertNotIn(secret, response_text)
        for recovery_code in recovery_codes:
            self.assertNotIn(recovery_code, response_text)

    def test_setup_requires_the_current_admin_password(self):
        admin = self._create_admin("wrong-password")
        self._login_admin_session(admin)

        response = self.client.post(
            reverse("api_admin_two_factor_setup"),
            data=json.dumps({"current_password": "WrongPass#123"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("ok"))
        self.assertNotIn(SESSION_ADMIN_TWO_FACTOR_SETUP_KEY, self.client.session)

    def test_setup_returns_scannable_svg_qr_for_the_authenticator_uri(self):
        admin = self._create_admin("qr-code")
        self._login_admin_session(admin)

        response = self.client.post(
            reverse("api_admin_two_factor_setup"),
            data=json.dumps({"current_password": self.password}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertTrue(payload.get("otpauth_uri", "").startswith("otpauth://totp/"))
        qr_data_url = payload.get("qr_code_data_url", "")
        prefix = "data:image/svg+xml;base64,"
        self.assertTrue(qr_data_url.startswith(prefix))
        svg_bytes = base64.b64decode(qr_data_url[len(prefix):])
        self.assertIn(b"<svg", svg_bytes)
        self.assertIn(b"</svg>", svg_bytes)

    def test_invalid_confirmation_code_does_not_enable_two_factor(self):
        admin = self._create_admin("invalid-code")
        self._login_admin_session(admin)
        setup_response = self.client.post(
            reverse("api_admin_two_factor_setup"),
            data=json.dumps({"current_password": self.password}),
            content_type="application/json",
        )
        self.assertTrue(setup_response.json().get("ok"))

        response = self.client.post(
            reverse("api_admin_two_factor_confirm"),
            data=json.dumps({"code": "000000"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("ok"))
        admin.refresh_from_db()
        self.assertFalse(admin.two_factor_enabled)

    @override_settings(SAFEBOOKS_ADMIN_TWO_FACTOR_PENDING_TIMEOUT_SECONDS=1)
    def test_expired_setup_cannot_be_confirmed(self):
        admin = self._create_admin("expired-setup")
        self._login_admin_session(admin)
        secret = pyotp.random_base32()
        session = self.client.session
        session[SESSION_ADMIN_TWO_FACTOR_SETUP_KEY] = {
            "admin_id": admin.id,
            "secret": secret,
            "issued_at": int(timezone.now().timestamp()) - 2,
        }
        session.save()

        response = self.client.post(
            reverse("api_admin_two_factor_confirm"),
            data=json.dumps({"code": pyotp.TOTP(secret).now()}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("ok"))
        self.assertIn("expired", response.json().get("message", "").lower())
        admin.refresh_from_db()
        self.assertFalse(admin.two_factor_enabled)

    def test_admin_two_factor_endpoints_reject_bookkeeper_session(self):
        bookkeeper = BookkeeperAccount.objects.create(
            full_name="Blocked Bookkeeper",
            username="blocked_admin_security",
            email="blocked_admin_security@example.com",
            password_hash=make_password("Bookkeeper#123"),
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = bookkeeper.id
        bind_authenticated_session(session)
        session.save()

        endpoints = (
            "api_admin_two_factor_setup",
            "api_admin_two_factor_confirm",
            "api_admin_two_factor_disable",
            "api_admin_two_factor_recovery_codes",
        )
        for endpoint_name in endpoints:
            with self.subTest(endpoint=endpoint_name):
                response = self.client.post(
                    reverse(endpoint_name),
                    data=json.dumps({"current_password": "Bookkeeper#123", "code": "123456"}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 403)

    def test_enabled_two_factor_password_creates_challenge_without_admin_session(self):
        admin = self._create_admin("login")
        self._enable_two_factor(admin)
        self.client.post(reverse("api_logout"), content_type="application/json")

        password_response = self._start_two_factor_login(admin)

        self.assertEqual(password_response["Cache-Control"], "no-store")
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)
        self.assertEqual(
            self.client.session[SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY]["admin_id"],
            admin.id,
        )
        admin.refresh_from_db()
        self.assertIsNone(admin.last_login)
        self.assertFalse(
            AdminAuditLog.objects.filter(
                admin=admin,
                action_type=AdminAuditLog.ACTION_ADMIN_LOGIN,
            ).exists()
        )

    def test_authenticator_code_completes_admin_login_and_audits_method(self):
        admin = self._create_admin("totp-login")
        secret, _recovery_codes = self._enable_two_factor(admin)
        self.client.post(reverse("api_logout"), content_type="application/json")
        self._start_two_factor_login(admin)

        response = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": pyotp.TOTP(secret).now()}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        self.assertFalse(response.json().get("recovery_code_used"))
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.client.session.get(SESSION_ADMIN_ID_KEY), admin.id)
        self.assertNotIn(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, self.client.session)
        admin.refresh_from_db()
        self.assertIsNotNone(admin.last_login)
        login_audit = AdminAuditLog.objects.get(
            admin=admin,
            action_type=AdminAuditLog.ACTION_ADMIN_LOGIN,
        )
        self.assertEqual(login_audit.metadata.get("authentication_method"), "authenticator")

    def test_recovery_code_completes_login_and_is_consumed(self):
        admin = self._create_admin("recovery-login")
        _secret, recovery_codes = self._enable_two_factor(admin)
        self.client.post(reverse("api_logout"), content_type="application/json")
        self._start_two_factor_login(admin)

        response = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": recovery_codes[0]}),
            content_type="application/json",
        )

        self.assertTrue(response.json().get("ok"))
        self.assertTrue(response.json().get("recovery_code_used"))
        admin.refresh_from_db()
        self.assertEqual(len(admin.two_factor_recovery_codes), 7)
        login_audit = AdminAuditLog.objects.get(
            admin=admin,
            action_type=AdminAuditLog.ACTION_ADMIN_LOGIN,
        )
        self.assertEqual(login_audit.metadata.get("authentication_method"), "recovery_code")

    @override_settings(SAFEBOOKS_ADMIN_TWO_FACTOR_LOGIN_MAX_ATTEMPTS=2)
    def test_invalid_codes_are_limited_and_never_create_admin_session(self):
        admin = self._create_admin("attempt-limit")
        self._enable_two_factor(admin)
        self.client.post(reverse("api_logout"), content_type="application/json")
        self._start_two_factor_login(admin)

        first = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": "000000"}),
            content_type="application/json",
        )
        second = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": "000000"}),
            content_type="application/json",
        )

        self.assertFalse(first.json().get("ok"))
        self.assertEqual(first.json().get("remaining_attempts"), 1)
        self.assertFalse(second.json().get("ok"))
        self.assertTrue(second.json().get("restart_login"))
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)
        self.assertNotIn(SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, self.client.session)

    def test_expired_login_challenge_requires_password_again(self):
        admin = self._create_admin("expired-login")
        self._enable_two_factor(admin)
        self.client.post(reverse("api_logout"), content_type="application/json")
        self._start_two_factor_login(admin)
        session = self.client.session
        challenge = dict(session[SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY])
        challenge["issued_at"] = int(timezone.now().timestamp()) - 301
        session[SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY] = challenge
        session.save()

        response = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": "000000"}),
            content_type="application/json",
        )

        self.assertFalse(response.json().get("ok"))
        self.assertTrue(response.json().get("restart_login"))
        self.assertIn("expired", response.json().get("message", "").lower())
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)

    def test_two_factor_verify_without_pending_challenge_is_rejected(self):
        response = self.client.post(
            reverse("api_admin_two_factor_login_verify"),
            data=json.dumps({"code": "123456"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("ok"))
        self.assertTrue(response.json().get("restart_login"))

    def test_login_page_contains_admin_two_factor_step(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="adminTwoFactorSection"')
        self.assertContains(response, 'id="adminTwoFactorForm"')
        self.assertContains(response, reverse("api_admin_two_factor_login_verify"))

    def test_disable_two_factor_clears_secret_and_audits(self):
        admin = self._create_admin("disable")
        secret, _recovery_codes = self._enable_two_factor(admin)

        response = self.client.post(
            reverse("api_admin_two_factor_disable"),
            data=json.dumps({
                "current_password": self.password,
                "code": pyotp.TOTP(secret).now(),
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))
        admin.refresh_from_db()
        self.assertFalse(admin.two_factor_enabled)
        self.assertEqual(admin.two_factor_secret, "")
        self.assertEqual(admin.two_factor_recovery_codes, [])
        self.assertTrue(AdminAuditLog.objects.filter(
            admin=admin,
            action_type=AdminAuditLog.ACTION_ADMIN_TWO_FACTOR_DISABLED,
        ).exists())

    def test_confirmation_returns_codes_once_and_persists_only_hashes(self):
        admin = self._create_admin("recovery-storage")

        _secret, recovery_codes = self._enable_two_factor(admin)

        admin.refresh_from_db()
        stored_hashes = admin.two_factor_recovery_codes
        self.assertEqual(len(stored_hashes), 8)
        self.assertEqual(len(set(stored_hashes)), 8)
        self.assertTrue(all(len(value) == 64 for value in stored_hashes))
        for recovery_code in recovery_codes:
            self.assertNotIn(recovery_code, stored_hashes)

        profile_response = self.client.get(
            reverse("api_admin_profile"),
            HTTP_ACCEPT="application/json",
        )
        profile_text = profile_response.content.decode("utf-8")
        for recovery_code in recovery_codes:
            self.assertNotIn(recovery_code, profile_text)
        for stored_hash in stored_hashes:
            self.assertNotIn(stored_hash, profile_text)

    def test_recovery_code_can_be_consumed_only_once(self):
        admin = self._create_admin("recovery-once")
        _secret, recovery_codes = self._enable_two_factor(admin)
        recovery_code = recovery_codes[0]
        admin.refresh_from_db()

        first_result = verify_admin_two_factor_login(admin, recovery_code)
        admin.refresh_from_db()
        second_result = verify_admin_two_factor_login(admin, recovery_code)

        self.assertTrue(first_result.get("ok"))
        self.assertTrue(first_result.get("recovery_code_used"))
        self.assertEqual(len(admin.two_factor_recovery_codes), 7)
        self.assertFalse(second_result.get("ok"))

    def test_regeneration_requires_password_and_live_authenticator_code(self):
        admin = self._create_admin("recovery-guard")
        secret, _recovery_codes = self._enable_two_factor(admin)
        admin.refresh_from_db()
        original_hashes = list(admin.two_factor_recovery_codes)
        current_code = pyotp.TOTP(secret).now()
        invalid_code = "000000" if current_code != "000000" else "111111"

        wrong_password_response = self.client.post(
            reverse("api_admin_two_factor_recovery_codes"),
            data=json.dumps({
                "current_password": "WrongPass#123",
                "code": pyotp.TOTP(secret).now(),
            }),
            content_type="application/json",
        )
        wrong_code_response = self.client.post(
            reverse("api_admin_two_factor_recovery_codes"),
            data=json.dumps({
                "current_password": self.password,
                "code": invalid_code,
            }),
            content_type="application/json",
        )

        self.assertFalse(wrong_password_response.json().get("ok"))
        self.assertFalse(wrong_code_response.json().get("ok"))
        admin.refresh_from_db()
        self.assertEqual(admin.two_factor_recovery_codes, original_hashes)

    def test_regeneration_invalidates_old_codes_and_audits_without_secrets(self):
        admin = self._create_admin("recovery-replace")
        secret, old_codes = self._enable_two_factor(admin)
        admin.refresh_from_db()
        old_hashes = list(admin.two_factor_recovery_codes)

        response = self.client.post(
            reverse("api_admin_two_factor_recovery_codes"),
            data=json.dumps({
                "current_password": self.password,
                "code": pyotp.TOTP(secret).now(),
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        new_codes = payload.get("recovery_codes")
        self.assertEqual(len(new_codes), 8)
        self.assertTrue(set(old_codes).isdisjoint(new_codes))
        admin.refresh_from_db()
        self.assertNotEqual(admin.two_factor_recovery_codes, old_hashes)
        self.assertFalse(verify_admin_two_factor_login(admin, old_codes[0]).get("ok"))

        audit = AdminAuditLog.objects.get(
            admin=admin,
            action_type=AdminAuditLog.ACTION_ADMIN_TWO_FACTOR_RECOVERY_CODES_REGENERATED,
        )
        audit_text = json.dumps({"message": audit.message, "metadata": audit.metadata})
        for code in new_codes:
            self.assertNotIn(code, audit_text)

    def test_successful_admin_login_rotates_session_key(self):
        admin = self._create_admin("rotation")
        session = self.client.session
        session["pre_login_value"] = "present"
        session.save()
        old_session_key = session.session_key

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({"identifier": admin.email, "password": self.password}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old_session_key, self.client.session.session_key)
        self.assertIn(SESSION_ADMIN_AUTHENTICATED_AT_KEY, self.client.session)
        self.assertIn(SESSION_ADMIN_LAST_ACTIVITY_AT_KEY, self.client.session)

    @override_settings(SAFEBOOKS_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS=60)
    def test_expired_admin_idle_session_is_rejected(self):
        admin = self._create_admin("expired")
        now_timestamp = int(timezone.now().timestamp())
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = admin.id
        bind_authenticated_session(session)
        session[SESSION_ADMIN_AUTHENTICATED_AT_KEY] = now_timestamp - 30
        session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = now_timestamp - 61
        session.save()

        response = self.client.get(reverse("api_admin_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 401)
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)

    def test_successful_bookkeeper_login_rotates_session_key(self):
        bookkeeper = BookkeeperAccount.objects.create(
            full_name="Rotation Bookkeeper",
            username="bookkeeper_rotation",
            email="bookkeeper_rotation@example.com",
            password_hash=make_password("Bookkeeper#123"),
            email_verified=True,
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        client = TestClient()
        session = client.session
        session["pre_login_value"] = "present"
        session.save()
        old_session_key = session.session_key

        response = client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": bookkeeper.username,
                "password": "Bookkeeper#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old_session_key, client.session.session_key)
        self.assertEqual(client.session.get(SESSION_BOOKKEEPER_ID_KEY), bookkeeper.id)
