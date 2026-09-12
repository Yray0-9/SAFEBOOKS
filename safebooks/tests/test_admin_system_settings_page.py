from django.test import TestCase
from django.urls import reverse

from safebooks.models import AdminAccount, BookkeeperAccount
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class AdminSystemSettingsPageTests(TestCase):
    def _create_admin(self) -> AdminAccount:
        return AdminAccount.objects.create(
            full_name="System Admin",
            email="system-rules-admin@example.com",
            password_hash="not-used-in-test",
            is_active=True,
        )

    def _login_admin(self, account: AdminAccount) -> None:
        session = self.client.session
        session[SESSION_ADMIN_ID_KEY] = account.id
        session.save()

    def _login_bookkeeper(self) -> None:
        bookkeeper = BookkeeperAccount.objects.create(
            full_name="Bookkeeper Blocked",
            username="system_rules_blocked",
            email="system_rules_blocked@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = bookkeeper.id
        session.save()

    def test_system_settings_requires_admin_authentication(self):
        response = self.client.get(reverse("admin_system_settings"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_system_settings_blocks_bookkeeper_session(self):
        self._login_bookkeeper()

        response = self.client.get(reverse("admin_system_settings"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))

    def test_system_settings_page_renders_successfully(self):
        admin = self._create_admin()
        self._login_admin(admin)

        response = self.client.get(reverse("admin_system_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Settings")
        self.assertContains(response, "Appearance")
        self.assertContains(response, 'id="adminSettingsAppearance"')
        self.assertContains(response, "Notifications & Mailer")
        self.assertContains(response, "Security")
        self.assertContains(response, "Account Password")
        self.assertContains(response, "Two-factor authentication")
        self.assertContains(response, 'id="adminSettingsSecurity"')
        self.assertContains(response, 'id="adminPasswordChangeBtn"')
        self.assertContains(response, 'id="adminTwoFactorAction"')
        self.assertNotContains(response, "General & Regional")
        self.assertNotContains(response, "Security & Sessions")
        self.assertNotContains(response, "System & Maintenance")
        self.assertNotContains(response, "Bookkeeper Governance")
        self.assertNotContains(response, "System Announcements")
        self.assertNotContains(response, "Data & Export")
