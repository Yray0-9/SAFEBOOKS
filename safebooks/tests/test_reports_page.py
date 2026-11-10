from safebooks.tests.session_helpers import bind_authenticated_session

from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class ReportsPageTests(TestCase):
    def _create_bookkeeper(self, suffix: str) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name=f"Reports User {suffix}",
            username=f"reports_user_{suffix}",
            email=f"reports_user_{suffix}@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
        )

    def _login_as(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        bind_authenticated_session(session)
        session.save()

    def test_reports_page_requires_authentication(self):
        response = self.client.get(reverse("reports"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertIn("next=", response.url)

    def test_authenticated_bookkeeper_can_reach_live_reports_from_dashboard(self):
        account = self._create_bookkeeper("active")
        self._login_as(account)

        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, f'href="{reverse("reports")}"')

        response = self.client.get(reverse("reports"))
        self.assertTemplateUsed(response, "base/reports.html")
        self.assertContains(response, "Client status overview")
        self.assertContains(response, "Print / Save PDF")
        self.assertNotContains(response, "clientRecordsSummaryPreview")
