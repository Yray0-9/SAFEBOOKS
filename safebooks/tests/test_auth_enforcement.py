import json
from unittest.mock import patch

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import Client as TestClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from safebooks.models import AdminAccount, BookkeeperAccount
from safebooks.services.admin_bookkeepers_service import deactivate_bookkeeper, reactivate_bookkeeper
from safebooks.services.auth_service import authenticate_google_bookkeeper, confirm_password_reset, send_password_reset_code, verify_password_reset_code
from safebooks.services.session_security_service import account_session_auth_hash, save_account_security_change
from safebooks.views import (
    SESSION_ADMIN_AUTH_HASH_KEY, SESSION_ADMIN_ID_KEY, SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY,
    SESSION_BOOKKEEPER_AUTH_HASH_KEY, SESSION_BOOKKEEPER_ID_KEY,
    SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, SESSION_CLIENT_PROFILE_ACCESS_KEY,
    SESSION_GOOGLE_OAUTH_STATE_KEY,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthEnforcementTests(TestCase):
    """Synthetic accounts, isolated DB, and mocked OAuth; no real credentials."""

    password = "SyntheticAuth#123"

    @classmethod
    def setUpTestData(cls):
        cls.bookkeeper = BookkeeperAccount.objects.create(
            full_name="Synthetic Auth", username="synthetic_auth", email="auth-test@example.com",
            password_hash=make_password(cls.password), status=BookkeeperAccount.STATUS_APPROVED,
        )
        cls.admin = AdminAccount.objects.create(
            full_name="Synthetic Admin", email="admin-auth-test@example.com", password_hash=make_password(cls.password),
        )

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _post(self, name, payload=None, *, client=None):
        return (client or self.client).post(reverse(name), json.dumps(payload or {}), content_type="application/json")

    def _login(self, account=None, *, client=None, complete=True):
        account = account or self.bookkeeper
        response = self._post("api_login", {"identifier": account.email, "password": self.password}, client=client)
        self.assertTrue(response.json().get("ok"), response.json())
        if response.json().get("requires_two_factor") and complete:
            account.refresh_from_db()
            endpoint = "api_admin_two_factor_login_verify" if isinstance(account, AdminAccount) else "api_bookkeeper_two_factor_login_verify"
            response = self._post(endpoint, {"code": pyotp.TOTP(account.two_factor_secret).now()}, client=client)
            self.assertTrue(response.json().get("ok"), response.json())
        return response

    def _enable_direct(self, account):
        account.two_factor_enabled = True
        account.two_factor_secret = pyotp.random_base32()
        account.two_factor_confirmed_at = timezone.now()
        save_account_security_change(account, ["two_factor_enabled", "two_factor_secret", "two_factor_confirmed_at"])

    def _google_callback(self, *, client=None, next_url=""):
        browser = client or self.client
        session = browser.session
        session[SESSION_GOOGLE_OAUTH_STATE_KEY] = {"state": "synthetic-state", "next_url": next_url}
        session.save()
        with patch("safebooks.views.exchange_google_oauth_code", return_value={
            "ok": True, "profile": {"google_sub": "synthetic-google-sub", "email": self.bookkeeper.email},
        }):
            return browser.get(reverse("auth_google_callback"), {"state": "synthetic-state", "code": "synthetic-code"})

    def _assert_revoked(self, client, *, admin=False):
        endpoint = "api_admin_profile" if admin else "api_profile"
        response = client.get(reverse(endpoint))
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(SESSION_ADMIN_ID_KEY if admin else SESSION_BOOKKEEPER_ID_KEY, client.session)

    def test_google_requires_same_second_factor_and_preserves_safe_destination(self):
        self._enable_direct(self.bookkeeper)
        with patch("safebooks.services.auth_service._maybe_send_login_alert") as alert:
            response = self._google_callback(next_url=reverse("clients"))
            self.assertEqual(response["Location"], reverse("login"))
            self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
            self.assertIn(SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, self.client.session)
            self.bookkeeper.refresh_from_db()
            self.assertIsNone(self.bookkeeper.last_login)
            alert.assert_not_called()
            page = self.client.get(reverse("login"))
            self.assertTrue(page.context["pending_bookkeeper_two_factor"])
            self.assertContains(page, "const pendingBookkeeperTwoFactor = true")
            self.assertEqual(self.client.get(reverse("api_clients")).status_code, 401)
            verified = self._post("api_bookkeeper_two_factor_login_verify", {"code": pyotp.TOTP(self.bookkeeper.two_factor_secret).now()})
            self.assertTrue(verified.json()["ok"])
            self.assertEqual(verified.json()["redirect_url"], reverse("clients"))
            alert.assert_called_once()

    def test_google_without_two_factor_logs_in_normally(self):
        response = self._google_callback()
        self.assertEqual(response["Location"], reverse("dashboard"))
        self.assertEqual(self.client.get(reverse("api_profile")).status_code, 200)
        self.bookkeeper.refresh_from_db()
        self.assertIsNotNone(self.bookkeeper.last_login)

    def test_password_alone_does_not_record_login_or_send_alert(self):
        self._enable_direct(self.bookkeeper)
        with patch("safebooks.services.auth_service._maybe_send_login_alert") as alert:
            self._login(complete=False)
            self.bookkeeper.refresh_from_db()
            self.assertIsNone(self.bookkeeper.last_login)
            alert.assert_not_called()
            self._post("api_bookkeeper_two_factor_login_verify", {"code": pyotp.TOTP(self.bookkeeper.two_factor_secret).now()})
            alert.assert_called_once()

    def test_challenge_rotates_key_and_removes_existing_authentication_and_profile_grants(self):
        self._login(self.admin)
        session = self.client.session
        session[SESSION_CLIENT_PROFILE_ACCESS_KEY] = {"synthetic": True}
        session.save()
        old_key = session.session_key
        self._enable_direct(self.bookkeeper)
        self._login(complete=False)
        self.assertNotEqual(self.client.session.session_key, old_key)
        for key in (SESSION_ADMIN_ID_KEY, SESSION_ADMIN_AUTH_HASH_KEY, SESSION_BOOKKEEPER_ID_KEY,
                    SESSION_BOOKKEEPER_AUTH_HASH_KEY, SESSION_CLIENT_PROFILE_ACCESS_KEY):
            self.assertNotIn(key, self.client.session)
        self.assertEqual(self.client.get(reverse("api_admin_profile")).status_code, 401)

    def test_admin_challenge_also_removes_existing_bookkeeper_access(self):
        self._login()
        self._enable_direct(self.admin)
        self._login(self.admin, complete=False)
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
        self.assertNotIn(SESSION_BOOKKEEPER_AUTH_HASH_KEY, self.client.session)
        self.assertEqual(self.client.get(reverse("api_profile")).status_code, 401)

    def test_old_challenges_are_rejected_after_password_or_version_change(self):
        for account, challenge_key, endpoint in (
            (self.bookkeeper, SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY, "api_bookkeeper_two_factor_login_verify"),
            (self.admin, SESSION_ADMIN_TWO_FACTOR_CHALLENGE_KEY, "api_admin_two_factor_login_verify"),
        ):
            with self.subTest(role=account._meta.model_name):
                self._enable_direct(account)
                self._login(account, complete=False)
                save_account_security_change(account, [])
                response = self._post(endpoint, {"code": pyotp.TOTP(account.two_factor_secret).now()})
                self.assertFalse(response.json()["ok"])
                self.assertTrue(response.json()["restart_login"])
                self.assertNotIn(challenge_key, self.client.session)

    def test_enabled_two_factor_with_missing_secret_never_falls_back_to_password(self):
        for account in (self.bookkeeper, self.admin):
            with self.subTest(role=account._meta.model_name):
                account.two_factor_enabled = True
                save_account_security_change(account, ["two_factor_enabled"])
                response = self._post("api_login", {"identifier": account.email, "password": self.password})
                self.assertFalse(response.json()["ok"])
                self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
                self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)
        response = self._google_callback()
        self.assertIn(reverse("login"), response["Location"])
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

    def test_legacy_bookkeeper_session_is_not_silently_authorized(self):
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.bookkeeper.id
        session.save()
        self._assert_revoked(self.client)

    def test_account_id_substitution_cannot_reuse_another_accounts_proof(self):
        self._login()
        other = BookkeeperAccount.objects.create(
            full_name="Other", username="other_auth", email="other-auth@example.com",
            password_hash=self.bookkeeper.password_hash, status=BookkeeperAccount.STATUS_APPROVED,
        )
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = other.id
        session.save()
        self._assert_revoked(self.client)

    def test_session_proofs_are_never_returned_by_login_or_oauth(self):
        for account, key in ((self.bookkeeper, SESSION_BOOKKEEPER_AUTH_HASH_KEY), (self.admin, SESSION_ADMIN_AUTH_HASH_KEY)):
            response = self._login(account)
            self.assertNotContains(response, self.client.session[key])
            self.assertNotContains(response, "_auth_hash")
        response = self._google_callback()
        self.assertNotIn(self.client.session[SESSION_BOOKKEEPER_AUTH_HASH_KEY], response["Location"])

    def test_password_change_keeps_current_browser_and_revokes_other_browsers(self):
        for account, endpoint, profile, admin in (
            (self.bookkeeper, "api_security_change_password", "api_profile", False),
            (self.admin, "api_admin_security_password", "api_admin_profile", True),
        ):
            with self.subTest(role=account._meta.model_name):
                other = TestClient()
                self._login(account)
                self._login(account, client=other)
                old_key = self.client.session.session_key
                response = self._post(endpoint, {"current_password": self.password, "new_password": "ChangedSynthetic#456", "confirm_password": "ChangedSynthetic#456"})
                self.assertTrue(response.json()["ok"])
                self.assertNotEqual(self.client.session.session_key, old_key)
                self.assertEqual(self.client.get(reverse(profile)).status_code, 200)
                self._assert_revoked(other, admin=admin)
                account.refresh_from_db()
                self.assertEqual(account.session_version, 1)

    def test_failed_password_change_does_not_revoke_sessions(self):
        self._login()
        other = TestClient()
        self._login(client=other)
        response = self._post("api_security_change_password", {"current_password": "WrongSynthetic#123", "new_password": "ChangedSynthetic#456", "confirm_password": "ChangedSynthetic#456"})
        self.assertFalse(response.json()["ok"])
        self.assertEqual(other.get(reverse("api_profile")).status_code, 200)
        self.bookkeeper.refresh_from_db()
        self.assertEqual(self.bookkeeper.session_version, 0)

    def test_two_factor_enable_revokes_other_browser_but_current_setup_browser_continues(self):
        other = TestClient()
        self._login()
        self._login(client=other)
        setup = self._post("api_bookkeeper_two_factor_setup").json()
        response = self._post("api_bookkeeper_two_factor_confirm", {"code": pyotp.TOTP(setup["secret"]).now()})
        self.assertTrue(response.json()["ok"])
        self.assertEqual(self.client.get(reverse("settings")).status_code, 200)
        self._assert_revoked(other)

    def test_two_factor_disable_and_reenable_do_not_revive_old_sessions(self):
        self._enable_direct(self.bookkeeper)
        other = TestClient()
        self._login()
        self._login(client=other)
        response = self._post("api_bookkeeper_two_factor_disable", {"current_password": self.password})
        self.assertTrue(response.json()["ok"])
        self.assertEqual(self.client.get(reverse("api_profile")).status_code, 200)
        self._enable_direct(self.bookkeeper)
        self._assert_revoked(other)

    def test_admin_two_factor_enable_disable_and_recovery_regeneration_revoke_others(self):
        self._login(self.admin)
        other = TestClient()
        self._login(self.admin, client=other)
        setup = self._post("api_admin_two_factor_setup", {"current_password": self.password}).json()
        enabled = self._post("api_admin_two_factor_confirm", {"code": pyotp.TOTP(setup["secret"]).now()})
        self.assertTrue(enabled.json()["ok"])
        self._assert_revoked(other, admin=True)
        self._login(self.admin, client=other)
        regenerated = self._post("api_admin_two_factor_recovery_codes", {"current_password": self.password, "code": pyotp.TOTP(setup["secret"]).now()})
        self.assertTrue(regenerated.json()["ok"])
        self._assert_revoked(other, admin=True)
        self._login(self.admin, client=other)
        disabled = self._post("api_admin_two_factor_disable", {"current_password": self.password, "code": pyotp.TOTP(setup["secret"]).now()})
        self.assertTrue(disabled.json()["ok"])
        self.assertEqual(self.client.get(reverse("api_admin_profile")).status_code, 200)
        self._assert_revoked(other, admin=True)

    def test_password_reset_revokes_all_preexisting_browsers(self):
        self._login()
        other = TestClient()
        self._login(client=other)
        with patch("safebooks.services.auth_service.send_mail", return_value=1), patch("safebooks.services.auth_service._generate_verification_code", return_value="123456"):
            self.assertTrue(send_password_reset_code(self.bookkeeper.email)["ok"])
        authorization = verify_password_reset_code(self.bookkeeper.email, "123456")["reset_authorization"]
        result = confirm_password_reset(self.bookkeeper.email, "ChangedSynthetic#456", "ChangedSynthetic#456", reset_authorization=authorization)
        self.assertTrue(result["ok"])
        self._assert_revoked(self.client)
        self._assert_revoked(other)

    def test_deactivation_and_reactivation_do_not_restore_old_session(self):
        self._login()
        self.assertTrue(deactivate_bookkeeper(self.admin, self.bookkeeper.pk, self.password)["ok"])
        self.assertTrue(reactivate_bookkeeper(self.admin, self.bookkeeper.pk, self.password)["ok"])
        self._assert_revoked(self.client)
        self._login()
        self.assertEqual(self.client.get(reverse("api_profile")).status_code, 200)

    def test_concurrent_version_updates_from_stale_instances_are_not_lost(self):
        stale = BookkeeperAccount.objects.get(pk=self.bookkeeper.pk)
        save_account_security_change(self.bookkeeper, [])
        save_account_security_change(stale, [])
        stale.refresh_from_db()
        self.assertEqual(stale.session_version, 2)

    @override_settings(SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_MAX_ATTEMPTS=2)
    def test_two_factor_attempt_limit_survives_restarted_login_and_new_browser(self):
        self._enable_direct(self.bookkeeper)
        self._login(complete=False)
        current = pyotp.TOTP(self.bookkeeper.two_factor_secret).now()
        bad_code = "111111" if current == "000000" else "000000"
        first = self._post("api_bookkeeper_two_factor_login_verify", {"code": bad_code})
        self.assertEqual(first.json()["remaining_attempts"], 1)
        other = TestClient()
        self._login(client=other, complete=False)
        second = self._post("api_bookkeeper_two_factor_login_verify", {"code": bad_code}, client=other)
        self.assertTrue(second.json()["restart_login"])
        third = self._post("api_login", {"identifier": self.bookkeeper.email, "password": self.password})
        self.assertFalse(third.json()["ok"])
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

    def test_stale_primary_authentication_cannot_adopt_new_credentials(self):
        result = authenticate_google_bookkeeper({"google_sub": "synthetic-google-sub", "email": self.bookkeeper.email})
        save_account_security_change(self.bookkeeper, [])
        with patch("safebooks.views.login_user_or_admin", return_value=result):
            response = self._post("api_login", {"identifier": self.bookkeeper.email, "password": self.password})
        self.assertFalse(response.json()["ok"])
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

    def test_challenge_is_single_use_and_csrf_protected(self):
        self._enable_direct(self.bookkeeper)
        self._login(complete=False)
        code = pyotp.TOTP(self.bookkeeper.two_factor_secret).now()
        first = self._post("api_bookkeeper_two_factor_login_verify", {"code": code})
        self.assertTrue(first.json()["ok"])
        second = self._post("api_bookkeeper_two_factor_login_verify", {"code": code})
        self.assertFalse(second.json()["ok"])
        guarded = TestClient(enforce_csrf_checks=True)
        self.assertEqual(self._post("api_bookkeeper_two_factor_login_verify", {"code": code}, client=guarded).status_code, 403)

    def test_logout_replay_cannot_restore_access(self):
        self._login()
        cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertTrue(self._post("api_logout").json()["ok"])
        replay = TestClient()
        replay.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self._assert_revoked(replay)

    def test_direct_password_update_invalidates_existing_proof(self):
        self._login()
        BookkeeperAccount.objects.filter(pk=self.bookkeeper.pk).update(password_hash=make_password("DirectChange#456"))
        self._assert_revoked(self.client)

    def test_pending_reset_authorization_is_invalidated_by_security_version_change(self):
        with patch("safebooks.services.auth_service.send_mail", return_value=1), patch("safebooks.services.auth_service._generate_verification_code", return_value="123456"):
            self.assertTrue(send_password_reset_code(self.bookkeeper.email)["ok"])
        authorization = verify_password_reset_code(self.bookkeeper.email, "123456")["reset_authorization"]
        save_account_security_change(self.bookkeeper, [])
        result = confirm_password_reset(self.bookkeeper.email, "ChangedSynthetic#456", "ChangedSynthetic#456", reset_authorization=authorization)
        self.assertFalse(result["ok"])

    def test_two_factor_challenge_expires_and_never_creates_authentication(self):
        self._enable_direct(self.bookkeeper)
        self._login(complete=False)
        session = self.client.session
        challenge = dict(session[SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY])
        challenge["issued_at"] = int(timezone.now().timestamp()) - 301
        session[SESSION_BOOKKEEPER_TWO_FACTOR_CHALLENGE_KEY] = challenge
        session.save()
        response = self._post("api_bookkeeper_two_factor_login_verify", {"code": pyotp.TOTP(self.bookkeeper.two_factor_secret).now()})
        self.assertTrue(response.json()["restart_login"])
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

    def test_malformed_code_and_payload_are_controlled(self):
        self._enable_direct(self.bookkeeper)
        self._login(complete=False)
        malformed = self.client.post(reverse("api_bookkeeper_two_factor_login_verify"), "{", content_type="application/json")
        self.assertEqual(malformed.status_code, 400)
        for value in ("", {}, ["bad"], "invalid"):
            response = self._post("api_bookkeeper_two_factor_login_verify", {"code": value})
            self.assertFalse(response.json()["ok"])
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
