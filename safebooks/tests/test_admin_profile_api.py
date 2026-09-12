from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase
from django.urls import reverse

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class AdminProfileApiTests(TestCase):
    def _create_admin(self, suffix: str, password: str = "AdminPass#123") -> AdminAccount:
        return AdminAccount.objects.create(
            full_name=f"Admin {suffix}",
            email=f"admin_profile_{suffix}@example.com",
            password_hash=make_password(password),
            is_active=True,
        )

    def _login_admin(self, account: AdminAccount) -> None:
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = account.id
        session.save()

    def _login_bookkeeper(self) -> None:
        bookkeeper = BookkeeperAccount.objects.create(
            full_name="Bookkeeper Blocked",
            username="admin_profile_blocked",
            email="admin_profile_blocked@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = bookkeeper.id
        session.save()

    def test_admin_profile_requires_admin_authentication(self):
        response = self.client.get(reverse("api_admin_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json().get("ok"))

    def test_admin_profile_blocks_bookkeeper_session(self):
        self._login_bookkeeper()

        response = self.client.get(reverse("api_admin_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json().get("ok"))

    def test_admin_profile_page_renders_for_admin(self):
        admin = self._create_admin("page")
        self._login_admin(admin)

        response = self.client.get(reverse("admin_profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage your admin account identity.")
        self.assertContains(response, "Identity details")
        self.assertNotContains(response, "Password security")
        self.assertNotContains(response, "Authenticator security")
        self.assertNotContains(response, "Recent admin activity")
        self.assertNotContains(response, "Role label")
        self.assertNotContains(response, "Add a verification code from your authenticator app.")
        self.assertNotContains(response, "Preview only")
        self.assertNotContains(response, "Demo only")
        self.assertNotContains(response, "Coming soon")

    def test_admin_profile_page_requires_admin_authentication(self):
        response = self.client.get(reverse("admin_profile"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_admin_profile_page_blocks_bookkeeper_session(self):
        self._login_bookkeeper()

        response = self.client.get(reverse("admin_profile"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))

    def test_admin_profile_get_returns_profile_and_recent_activity(self):
        admin = self._create_admin("get")
        self._login_admin(admin)
        AdminAuditLog.objects.create(
            admin=admin,
            action_type=AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
            target_model="BookkeeperAccount",
            target_id=1,
            message="Approved bookkeeper access.",
            metadata={},
        )

        response = self.client.get(reverse("api_admin_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("profile", {}).get("email"), admin.email)
        self.assertEqual(len(payload.get("recent_activity", [])), 1)

    def test_admin_profile_update_validates_without_bad_request(self):
        admin = self._create_admin("validate")
        self._login_admin(admin)

        response = self.client.post(
            reverse("api_admin_profile"),
            data={"full_name": "", "email": "not-an-email"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Full name is required.")
        admin.refresh_from_db()
        self.assertEqual(admin.full_name, "Admin validate")

    def test_admin_profile_update_saves_and_audits(self):
        admin = self._create_admin("update")
        self._login_admin(admin)

        response = self.client.post(
            reverse("api_admin_profile"),
            data={
                "full_name": "Updated Admin",
                "email": "updated-admin@example.com",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        admin.refresh_from_db()
        self.assertEqual(admin.full_name, "Updated Admin")
        self.assertEqual(admin.email, "updated-admin@example.com")
        audit_log = AdminAuditLog.objects.get(
            action_type=AdminAuditLog.ACTION_ADMIN_PROFILE_UPDATED,
            target_id=admin.id,
        )
        self.assertEqual(audit_log.admin_id, admin.id)
        self.assertIn("email", audit_log.metadata.get("changed_fields", []))

    def test_admin_profile_update_rejects_duplicate_email(self):
        admin = self._create_admin("duplicate")
        other = self._create_admin("other")
        self._login_admin(admin)

        response = self.client.post(
            reverse("api_admin_profile"),
            data={
                "full_name": "Admin duplicate",
                "email": other.email,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Email already exists.")

    def test_admin_password_change_validates_current_password(self):
        admin = self._create_admin("password-current")
        original_hash = admin.password_hash
        self._login_admin(admin)

        response = self.client.post(
            reverse("api_admin_security_password"),
            data={
                "current_password": "WrongPass#123",
                "new_password": "NewPass#123",
                "confirm_password": "NewPass#123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Current password is incorrect.")
        admin.refresh_from_db()
        self.assertEqual(admin.password_hash, original_hash)

    def test_admin_password_change_enforces_requirements(self):
        admin = self._create_admin("password-rules")
        self._login_admin(admin)

        response = self.client.post(
            reverse("api_admin_security_password"),
            data={
                "current_password": "AdminPass#123",
                "new_password": "short",
                "confirm_password": "short",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Password does not meet requirements.")
        self.assertIn("At least 8 characters", payload.get("password_requirements", []))

    def test_admin_password_change_updates_hash_and_audits(self):
        admin = self._create_admin("password-update")
        self._login_admin(admin)

        response = self.client.post(
            reverse("api_admin_security_password"),
            data={
                "current_password": "AdminPass#123",
                "new_password": "NewAdmin#456",
                "confirm_password": "NewAdmin#456",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        admin.refresh_from_db()
        self.assertTrue(check_password("NewAdmin#456", admin.password_hash))
        self.assertTrue(
            AdminAuditLog.objects.filter(
                action_type=AdminAuditLog.ACTION_ADMIN_PASSWORD_CHANGED,
                target_id=admin.id,
            ).exists()
        )
