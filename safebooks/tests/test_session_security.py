import json

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client as TestClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from safebooks.models import AdminAccount, BookkeeperAccount
from safebooks.views import (
    SESSION_ADMIN_AUTHENTICATED_AT_KEY,
    SESSION_ADMIN_ID_KEY,
    SESSION_ADMIN_LAST_ACTIVITY_AT_KEY,
    SESSION_BOOKKEEPER_ID_KEY,
)


class SessionSecurityTests(TestCase):
    def _create_admin(self, suffix: str = "session") -> AdminAccount:
        return AdminAccount.objects.create(
            full_name="Session Admin",
            email=f"session-admin-{suffix}@example.com",
            password_hash=make_password("AdminPass#123"),
            is_active=True,
        )

    def _create_bookkeeper(self) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name="Session Bookkeeper",
            username="session_bookkeeper",
            email="session-bookkeeper@example.com",
            password_hash=make_password("BookkeeperPass#123"),
            email_verified=True,
            status=BookkeeperAccount.STATUS_APPROVED,
        )

    def test_admin_login_rotates_key_and_sets_security_timestamps(self):
        admin = self._create_admin()
        session = self.client.session
        session["pre_login_marker"] = True
        session.save()
        old_key = session.session_key

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": admin.email,
                "password": "AdminPass#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old_key, self.client.session.session_key)
        self.assertEqual(self.client.session.get(SESSION_ADMIN_ID_KEY), admin.id)
        self.assertIn(SESSION_ADMIN_AUTHENTICATED_AT_KEY, self.client.session)
        self.assertIn(SESSION_ADMIN_LAST_ACTIVITY_AT_KEY, self.client.session)
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

    def test_bookkeeper_login_rotates_key_without_admin_security_state(self):
        bookkeeper = self._create_bookkeeper()
        client = TestClient()
        session = client.session
        session[SESSION_ADMIN_ID_KEY] = 999
        session[SESSION_ADMIN_AUTHENTICATED_AT_KEY] = 1
        session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = 1
        session.save()
        old_key = session.session_key

        response = client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": bookkeeper.username,
                "password": "BookkeeperPass#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old_key, client.session.session_key)
        self.assertEqual(client.session.get(SESSION_BOOKKEEPER_ID_KEY), bookkeeper.id)
        self.assertNotIn(SESSION_ADMIN_ID_KEY, client.session)
        self.assertNotIn(SESSION_ADMIN_AUTHENTICATED_AT_KEY, client.session)
        self.assertNotIn(SESSION_ADMIN_LAST_ACTIVITY_AT_KEY, client.session)

    def test_bookkeeper_login_session_expires_when_browser_closes(self):
        bookkeeper = self._create_bookkeeper()

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": bookkeeper.username,
                "password": "BookkeeperPass#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        session_cookie = self.client.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertEqual(session_cookie["max-age"], "")
        self.assertEqual(session_cookie["expires"], "")

    def test_existing_bookkeeper_session_is_converted_to_browser_session(self):
        bookkeeper = self._create_bookkeeper()
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = bookkeeper.id
        session.set_expiry(60 * 60 * 24)
        session.save()

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        session_cookie = self.client.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertEqual(session_cookie["max-age"], "")
        self.assertEqual(session_cookie["expires"], "")

    @override_settings(SAFEBOOKS_ADMIN_SESSION_IDLE_TIMEOUT_SECONDS=60)
    def test_admin_session_expires_after_idle_timeout(self):
        admin = self._create_admin("idle")
        now_timestamp = int(timezone.now().timestamp())
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = admin.id
        session[SESSION_ADMIN_AUTHENTICATED_AT_KEY] = now_timestamp - 30
        session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = now_timestamp - 61
        session.save()

        response = self.client.get(
            reverse("api_admin_profile"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)

    @override_settings(SAFEBOOKS_ADMIN_SESSION_MAX_AGE_SECONDS=60)
    def test_admin_session_expires_at_absolute_limit_despite_recent_activity(self):
        admin = self._create_admin("absolute")
        now_timestamp = int(timezone.now().timestamp())
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = admin.id
        session[SESSION_ADMIN_AUTHENTICATED_AT_KEY] = now_timestamp - 61
        session[SESSION_ADMIN_LAST_ACTIVITY_AT_KEY] = now_timestamp - 1
        session.save()

        response = self.client.get(
            reverse("api_admin_profile"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)

    def test_existing_admin_session_is_bootstrapped_without_forced_logout(self):
        admin = self._create_admin("legacy")
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = admin.id
        session.save()

        response = self.client.get(
            reverse("api_admin_profile"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(SESSION_ADMIN_AUTHENTICATED_AT_KEY, self.client.session)
        self.assertIn(SESSION_ADMIN_LAST_ACTIVITY_AT_KEY, self.client.session)
