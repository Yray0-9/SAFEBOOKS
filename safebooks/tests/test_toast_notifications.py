"""Verify rendered notification containers using isolated synthetic accounts."""
import re

from django.test import TestCase
from django.urls import reverse

from safebooks.models import AdminAccount, BookkeeperAccount, Client
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class ToastContainerTests(TestCase):
    def authenticate(self, account, key):
        self.client.cookies.clear()
        session = self.client.session
        session[key] = account.pk
        bind_authenticated_session(session)
        session.save()

    def assert_shared_top_right(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        containers = re.findall(r'<div[^>]*id="uiToastContainer"[^>]*>', html)
        self.assertEqual(len(containers), 1, "Each rendered page needs exactly one shared container")
        self.assertIn('top-0 end-0', containers[0])
        self.assertNotIn('bottom-0', containers[0])
        self.assertIn('aria-live="polite"', containers[0])
        self.assertIn('aria-atomic="true"', containers[0])

    def test_bookkeeper_pages_use_one_top_right_container(self):
        owner = BookkeeperAccount.objects.create(
            full_name="Synthetic Toast Tester", username="toast-owner", email="toast@example.test",
            password_hash="unused", status="approved", email_verified=True,
            client_details_password_required=False,
        )
        ledger = Client.objects.create(bookkeeper=owner, client_name="Toast Client", tin_number="123456789001")
        self.authenticate(owner, SESSION_BOOKKEEPER_ID_KEY)
        urls = [reverse(name) for name in ('dashboard', 'clients', 'financial_records', 'settings', 'profile', 'bookkeeper_audit_log')]
        urls += [reverse('client_details', args=[ledger.pk]), reverse('financial_records_client') + f'?client_id={ledger.pk}']
        for url in urls:
            with self.subTest(url=url):
                self.assert_shared_top_right(url)

    def test_admin_pages_use_one_top_right_container(self):
        admin = AdminAccount.objects.create(full_name="Synthetic Toast Admin", email="toast-admin@example.test", password_hash="unused")
        self.authenticate(admin, SESSION_ADMIN_ID_KEY)
        for name in ('admin_dashboard', 'admin_approvals', 'admin_bookkeepers', 'admin_audit_log', 'admin_system_settings', 'admin_profile'):
            with self.subTest(page=name):
                self.assert_shared_top_right(reverse(name))
