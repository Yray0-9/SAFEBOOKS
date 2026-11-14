import json
from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.core.cache import cache
from django.test import Client as TestClient, TestCase, override_settings
from django.urls import reverse

from safebooks.models import BookkeeperAccount
from safebooks.services import auth_service
from safebooks.views import (
    SESSION_BOOKKEEPER_ID_KEY,
    SESSION_PASSWORD_RESET_AUTHORIZATION_KEY,
)


@override_settings(
    DEBUG=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "password-reset-regression-tests",
        }
    },
    SAFEBOOKS_EMAIL_VERIFICATION_CODE_TTL_MINUTES=10,
    SAFEBOOKS_EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=60,
)
class PasswordResetApiTests(TestCase):
    # Synthetic credentials and codes only; never use real accounts or email delivery.
    CODE = "123456"
    INITIAL_PASSWORD = "InitialTest#123"
    NEW_PASSWORD = "ReplacementTest#123"

    @classmethod
    def setUpTestData(cls):
        cls.account = BookkeeperAccount.objects.create(
            full_name="Password Reset Test",
            username="password_reset_test",
            email="password-reset@example.com",
            password_hash=make_password(cls.INITIAL_PASSWORD),
            email_verified=True,
            status=BookkeeperAccount.STATUS_APPROVED,
        )

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = TestClient(enforce_csrf_checks=True)
        self.client.get(reverse("login"))
        self.initial_hash = self.account.password_hash

    def _post(self, route, payload, *, client=None):
        client = client or self.client
        if settings.CSRF_COOKIE_NAME not in client.cookies:
            client.get(reverse("login"))
        return client.post(
            reverse(route),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value,
        )

    def _send(self, *, client=None, email=None):
        with patch.object(auth_service, "_generate_verification_code", return_value=self.CODE):
            return self._post(
                "api_forgot_password_send_code",
                {"email": email or self.account.email},
                client=client,
            )

    def _verify(self, *, client=None, email=None, code=None):
        return self._post(
            "api_forgot_password_verify_code",
            {"email": email or self.account.email, "code": code or self.CODE},
            client=client,
        )

    def _begin(self):
        self.assertEqual(self._send().status_code, 200)
        response = self._verify()
        self.assertEqual(response.status_code, 200)
        return response

    def _reset(self, *, client=None, email=None, new_password=None, **extra):
        password = self.NEW_PASSWORD if new_password is None else new_password
        payload = {
            "email": email or self.account.email,
            "new_password": password,
            "confirm_password": password,
        }
        payload.update(extra)
        return self._post("api_forgot_password_reset", payload, client=client)

    def _assert_password_unchanged(self):
        self.account.refresh_from_db()
        self.assertEqual(self.account.password_hash, self.initial_hash)

    def _verified_key(self):
        return auth_service._password_reset_cache_key(
            self.account.email, auth_service.PASSWORD_RESET_CACHE_VERIFIED_SUFFIX
        )

    def test_normal_recovery_allows_new_password_login_without_auto_login(self):
        self._begin()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.account.email])
        self.assertIn(self.CODE, mail.outbox[0].body)
        self.assertEqual(self._reset().status_code, 200)
        self.account.refresh_from_db()
        self.assertNotEqual(self.account.password_hash, self.initial_hash)
        self.assertTrue(check_password(self.NEW_PASSWORD, self.account.password_hash))
        self.assertNotIn(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, self.client.session)
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
        old_login = self._post(
            "api_login", {"identifier": self.account.email, "password": self.INITIAL_PASSWORD}
        )
        self.assertFalse(old_login.json()["ok"])
        new_login = self._post(
            "api_login", {"identifier": self.account.email, "password": self.NEW_PASSWORD}
        )
        self.assertTrue(new_login.json()["ok"])
        self.assertEqual(self.client.session[SESSION_BOOKKEEPER_ID_KEY], self.account.id)

    def test_unrelated_browser_cannot_use_another_browsers_verified_email(self):
        self._begin()
        self.assertEqual(self._reset(client=TestClient(enforce_csrf_checks=True)).status_code, 400)
        self._assert_password_unchanged()
        # An unauthorized attempt must not consume the legitimate browser's grant.
        self.assertEqual(self._reset().status_code, 200)

    def test_reset_without_verification_is_rejected(self):
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_service_cannot_reset_using_email_alone_after_verification(self):
        self._begin()
        result = auth_service.confirm_password_reset(
            self.account.email, self.NEW_PASSWORD, self.NEW_PASSWORD
        )
        self.assertFalse(result["ok"])
        self._assert_password_unchanged()

    def test_request_body_cannot_supply_the_server_session_proof(self):
        self._begin()
        proof = self.client.session[SESSION_PASSWORD_RESET_AUTHORIZATION_KEY]["token"]
        response = self._reset(
            client=TestClient(enforce_csrf_checks=True), reset_authorization=proof, verified=True
        )
        self.assertEqual(response.status_code, 400)
        self._assert_password_unchanged()

    def test_verification_rotates_session_and_never_returns_authorization_proof(self):
        session = self.client.session
        session["pre_reset_marker"] = True
        session.save()
        old_key = session.session_key
        response = self._begin()
        self.assertEqual(response.json(), {"ok": True, "message": "Code verified successfully."})
        session = self.client.session
        self.assertNotEqual(session.session_key, old_key)
        self.assertTrue(session["pre_reset_marker"])
        proof = session[SESSION_PASSWORD_RESET_AUTHORIZATION_KEY]["token"]
        self.assertNotIn(proof, response.content.decode())
        self.assertNotIn(proof, self.client.cookies[settings.SESSION_COOKIE_NAME].value)
        self.assertNotEqual(cache.get(self._verified_key())["authorization_digest"], proof)

    def test_verification_is_consumed_and_cannot_authorize_second_browser(self):
        self._begin()
        response = self._verify(client=TestClient(enforce_csrf_checks=True))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._reset().status_code, 200)

    def test_invalid_code_does_not_authorize_reset(self):
        self.assertEqual(self._send().status_code, 200)
        self.assertEqual(self._verify(code="000000").status_code, 400)
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_expired_code_is_rejected_at_expiration_boundary(self):
        self.assertEqual(self._send().status_code, 200)
        key = auth_service._password_reset_cache_key(self.account.email, "code")
        expires_at = cache.get(key)["expires_at"]
        with patch.object(auth_service.timezone, "now", return_value=datetime.fromtimestamp(expires_at, datetime_timezone.utc)):
            self.assertEqual(self._verify().status_code, 400)
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_code_with_missing_expiry_fails_closed(self):
        self.assertEqual(self._send().status_code, 200)
        key = auth_service._password_reset_cache_key(self.account.email, "code")
        value = cache.get(key)
        value.pop("expires_at")
        cache.set(key, value)
        self.assertEqual(self._verify().status_code, 400)
        self._assert_password_unchanged()

    def test_reset_permission_expires_after_five_minutes(self):
        self._begin()
        expires_at = cache.get(self._verified_key())["expires_at"]
        with patch.object(auth_service.timezone, "now", return_value=datetime.fromtimestamp(expires_at, datetime_timezone.utc)):
            self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_legacy_email_only_verified_flag_is_never_authorization(self):
        self._begin()
        cache.set(self._verified_key(), True, timeout=300)
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_wrong_or_missing_session_proof_is_rejected(self):
        self._begin()
        grant = dict(self.client.session[SESSION_PASSWORD_RESET_AUTHORIZATION_KEY])
        for proof in ("incorrect-proof", None, {}, ""):
            with self.subTest(proof_type=type(proof).__name__):
                session = self.client.session
                session[SESSION_PASSWORD_RESET_AUTHORIZATION_KEY] = {**grant, "token": proof}
                session.save()
                self.assertEqual(self._reset().status_code, 400)
                self._assert_password_unchanged()

    def test_malformed_cached_authorization_fails_closed(self):
        self._begin()
        grant = cache.get(self._verified_key())
        for change in (
            {"expires_at": None}, {"expires_at": "invalid"},
            {"authorization_digest": "\u2603" * 64}, {"account_id": None}, {"password_hash": None},
        ):
            with self.subTest(fields=list(change)):
                cache.set(self._verified_key(), {**grant, **change})
                self.assertEqual(self._reset().status_code, 400)
                self._assert_password_unchanged()

    def test_password_validation_errors_allow_retry_with_same_grant(self):
        self._begin()
        cases = (
            {"new_password": "", "confirm_password": ""},
            {"new_password": "weakpassword", "confirm_password": "weakpassword"},
            {"confirm_password": "MismatchTest#123"},
            {"new_password": 12345678, "confirm_password": 12345678},
            {"confirm_password": ["invalid"]},
        )
        for values in cases:
            with self.subTest(fields=list(values)):
                self.assertEqual(self._reset(**values).status_code, 400)
                self._assert_password_unchanged()
        self.assertEqual(self._reset().status_code, 200)

    def test_email_normalization_preserves_normal_recovery(self):
        email = f"  {self.account.email.upper()}  "
        self.assertEqual(self._send(email=email).status_code, 200)
        self.assertEqual(self._verify(email=email).status_code, 200)
        self.assertEqual(self._reset(email=email).status_code, 200)

    def test_grant_does_not_allow_resetting_a_different_account(self):
        other = BookkeeperAccount.objects.create(
            full_name="Other Reset Test", username="other_reset", email="other-reset@example.com",
            password_hash=self.initial_hash,
        )
        self._begin()
        self.assertEqual(self._reset(email=other.email).status_code, 400)
        other.refresh_from_db()
        self.assertEqual(other.password_hash, self.initial_hash)
        self.assertEqual(self._reset().status_code, 200)

    def test_completed_reset_cannot_be_replayed_with_old_session_cookie(self):
        self._begin()
        replay = TestClient(enforce_csrf_checks=True)
        replay.cookies = self.client.cookies.copy()
        self.assertEqual(self._reset().status_code, 200)
        self.assertEqual(self._reset(client=replay, new_password="AnotherTest#123").status_code, 400)
        self.account.refresh_from_db()
        self.assertTrue(check_password(self.NEW_PASSWORD, self.account.password_hash))

    def test_stale_cache_reads_still_allow_only_one_password_update(self):
        self._begin()
        proof = self.client.session[SESSION_PASSWORD_RESET_AUTHORIZATION_KEY]["token"]
        grant = cache.get(self._verified_key())
        # Model two requests that both read the same grant before either consumes
        # it. The database compare-and-swap must protect against replay by itself.
        with patch.object(auth_service.cache, "get", return_value=grant), patch.object(auth_service.cache, "delete"):
            first = auth_service.confirm_password_reset(
                self.account.email, self.NEW_PASSWORD, self.NEW_PASSWORD, reset_authorization=proof
            )
            second = auth_service.confirm_password_reset(
                self.account.email, "AnotherTest#123", "AnotherTest#123", reset_authorization=proof
            )
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.account.refresh_from_db()
        self.assertTrue(check_password(self.NEW_PASSWORD, self.account.password_hash))

    def test_password_changed_after_verification_cannot_be_overwritten(self):
        self._begin()
        replacement = make_password("ChangedElsewhere#123")
        BookkeeperAccount.objects.filter(pk=self.account.pk).update(password_hash=replacement)
        self.assertEqual(self._reset().status_code, 400)
        self.account.refresh_from_db()
        self.assertEqual(self.account.password_hash, replacement)

    def test_email_reassigned_after_verification_cannot_reset_replacement_account(self):
        self._begin()
        old_email = self.account.email
        BookkeeperAccount.objects.filter(pk=self.account.pk).update(email="changed-reset@example.com")
        other = BookkeeperAccount.objects.create(
            full_name="Replacement Account", username="replacement_account", email=old_email,
            password_hash=self.initial_hash,
        )
        self.assertEqual(self._reset(email=old_email).status_code, 400)
        other.refresh_from_db()
        self.assertEqual(other.password_hash, self.initial_hash)

    def test_deleted_account_after_verification_returns_controlled_error(self):
        self._begin()
        BookkeeperAccount.objects.filter(pk=self.account.pk).delete()
        self.assertEqual(self._reset().status_code, 400)

    def test_new_code_invalidates_old_grant_and_new_verification_restores_access(self):
        self._begin()
        self.assertEqual(self._send().status_code, 200)
        self.assertNotIn(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, self.client.session)
        self.assertIsNone(cache.get(self._verified_key()))
        self.assertEqual(self._reset().status_code, 400)
        self.assertEqual(self._verify().status_code, 200)
        self.assertEqual(self._reset().status_code, 200)

    def test_new_code_requested_by_other_browser_invalidates_existing_grant(self):
        self._begin()
        self.assertEqual(self._send(client=TestClient(enforce_csrf_checks=True)).status_code, 200)
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_latest_verifying_browser_gets_the_only_valid_grant(self):
        self._begin()
        other = TestClient(enforce_csrf_checks=True)
        self.assertEqual(self._send(client=other).status_code, 200)
        self.assertEqual(self._verify(client=other).status_code, 200)
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()
        self.assertEqual(self._reset(client=other).status_code, 200)

    def test_failed_reverification_clears_old_session_authorization(self):
        self._begin()
        self.assertEqual(self._verify(code="000000").status_code, 400)
        self.assertNotIn(SESSION_PASSWORD_RESET_AUTHORIZATION_KEY, self.client.session)
        self.assertEqual(self._reset().status_code, 400)

    def test_cache_loss_requires_verification_again(self):
        self._begin()
        cache.delete(self._verified_key())
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_email_failure_does_not_issue_code_or_reset_permission(self):
        with patch.object(auth_service, "send_mail", side_effect=OSError("Synthetic email failure")):
            response = self._send()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._verify().status_code, 400)
        self.assertEqual(self._reset().status_code, 400)
        self._assert_password_unchanged()

    def test_resend_cooldown_still_works(self):
        self.assertEqual(self._send().status_code, 200)
        response = self._send()
        self.assertEqual(response.status_code, 400)
        self.assertGreater(response.json()["retry_after_seconds"], 0)
        self.assertEqual(self._verify().status_code, 200)

    def test_missing_email_and_unknown_account_return_controlled_errors(self):
        for route in ("api_forgot_password_send_code", "api_forgot_password_verify_code", "api_forgot_password_reset"):
            for email in ("", "not-an-account@example.com"):
                with self.subTest(route=route, email=email):
                    self.assertEqual(self._post(route, {"email": email}).status_code, 400)

    def test_reset_endpoints_require_post_and_csrf(self):
        for route in ("api_forgot_password_send_code", "api_forgot_password_verify_code", "api_forgot_password_reset"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 405)
                response = TestClient(enforce_csrf_checks=True).post(
                    reverse(route), data="{}", content_type="application/json"
                )
                self.assertEqual(response.status_code, 403)

    def test_malformed_json_and_non_object_payloads_return_controlled_errors(self):
        for route in ("api_forgot_password_send_code", "api_forgot_password_verify_code", "api_forgot_password_reset"):
            for payload in ("{", "[]", "null"):
                with self.subTest(route=route, payload=payload):
                    response = self.client.post(
                        reverse(route), data=payload, content_type="application/json",
                        HTTP_X_CSRFTOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
                    )
                    self.assertEqual(response.status_code, 400)

    def test_reset_responses_are_not_cacheable_and_do_not_disclose_codes(self):
        sent = self._send()
        verified = self._verify()
        reset = self._reset()
        error = self._reset()
        self.assertNotIn("debug_code", sent.json())
        for response in (sent, verified, reset, error):
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertNotIn("reset_authorization", response.json())
