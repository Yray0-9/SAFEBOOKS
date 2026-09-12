import json

from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount, BookkeeperDeactivationRequest, Client
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class ClientDetailsAccessSecurityTests(TestCase):
    def _create_bookkeeper(self, *, lock_enabled=False) -> BookkeeperAccount:
        return BookkeeperAccount.objects.create(
            full_name="Security Tester",
            username=f"security_tester_{int(lock_enabled)}",
            email=f"security_tester_{int(lock_enabled)}@example.com",
            password_hash=make_password("SafeBooks#123"),
            status=BookkeeperAccount.STATUS_APPROVED,
            client_details_password_required=lock_enabled,
        )

    def _login_as(self, account: BookkeeperAccount) -> None:
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = account.id
        session.save()

    def _create_client(self, account: BookkeeperAccount) -> Client:
        return Client.objects.create(
            bookkeeper=account,
            client_name="Protected Client",
            tin_number="123456789000",
            trade_name="Protected Trade",
            location="Davao Del Norte",
            remarks=Client.REMARK_ACTIVE,
        )

    def test_client_details_open_when_lock_disabled(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)

    def test_client_details_page_exposes_edit_client_details_modal(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="editClientDetailsButton"')
        self.assertContains(response, 'id="editClientDetailsModal"')
        self.assertContains(response, 'id="editClientDetailsForm"')
        self.assertContains(response, 'id="editDetailsClientLocation" name="location" type="hidden"')
        self.assertContains(response, 'id="editDetailsClientLocationSelect"')
        self.assertContains(response, 'id="editDetailsClientLocationSummary"')
        self.assertContains(response, "bindLocationControls(editDetailsLocationState)")
        self.assertContains(response, "applyLocationSelection(editDetailsLocationState")
        self.assertContains(response, reverse("api_client_detail", kwargs={"client_id": client.id}))
        self.assertContains(response, "syncClientProfileUi")
        self.assertNotContains(response, "window.location.reload")

    def test_client_details_only_reminds_about_email_when_notifications_are_enabled(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client record emails will be skipped.")
        self.assertContains(response, "Add an email address only if this client should receive record updates.")
        self.assertNotContains(response, "Permit number is not provided yet.")
        self.assertNotContains(response, "ORUS account is not provided yet.")

    def test_client_details_hides_email_reminder_when_notifications_are_disabled(self):
        account = self._create_bookkeeper(lock_enabled=False)
        account.client_record_email_notifications_enabled = False
        account.save(update_fields=["client_record_email_notifications_enabled"])
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["client_record_email_notifications_enabled"])
        self.assertContains(response, 'id="clientDetailsReminder" hidden')

    def test_client_details_redirects_when_lock_enabled_without_confirmation(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("clients"), response["Location"])
        self.assertIn("client_access_required=1", response["Location"])

    def test_client_details_confirmation_rejects_wrong_password(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)

        response = self.client.post(
            reverse("api_security_client_details_access_confirm"),
            data=json.dumps({"current_password": "WrongPassword#123"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok"))

    def test_client_details_confirmation_allows_recent_access(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)

        confirm_response = self.client.post(
            reverse("api_security_client_details_access_confirm"),
            data=json.dumps({"current_password": "SafeBooks#123"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertTrue(confirm_response.json().get("ok"))

        detail_response = self.client.get(reverse("client_details", args=[client.id]))
        self.assertEqual(detail_response.status_code, 200)

    def test_client_details_confirmation_is_required_every_time(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client1 = self._create_client(account)
        client2 = Client.objects.create(
            bookkeeper=account,
            client_name="Second Client",
            tin_number="987654321000",
            trade_name="Second Trade",
            location="Davao Del Norte",
            remarks=Client.REMARK_ACTIVE,
        )

        confirm_response = self.client.post(
            reverse("api_security_client_details_access_confirm"),
            data=json.dumps({"current_password": "SafeBooks#123"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(confirm_response.status_code, 200)

        # First visit succeeds
        detail_response1 = self.client.get(reverse("client_details", args=[client1.id]))
        self.assertEqual(detail_response1.status_code, 200)

        # Subsequent visit to another client (or visiting clients page and clicking again) requires confirmation
        detail_response2 = self.client.get(reverse("client_details", args=[client2.id]))
        self.assertEqual(detail_response2.status_code, 302)
        self.assertIn("client_access_required=1", detail_response2["Location"])

    def test_preference_update_requires_password_and_can_disable_lock(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.post(
            reverse("api_security_client_details_access_preference"),
            data=json.dumps({"enabled": False, "current_password": "SafeBooks#123"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("client_details_password_required"))

        detail_response = self.client.get(reverse("client_details", args=[client.id]))
        self.assertEqual(detail_response.status_code, 200)

    def test_client_record_email_notification_preference_can_be_updated(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)

        response = self.client.post(
            reverse("api_settings_client_record_email_notifications"),
            data=json.dumps({"enabled": False}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertFalse(payload.get("client_record_email_notifications_enabled"))

        account.refresh_from_db()
        self.assertFalse(account.client_record_email_notifications_enabled)

    def test_bookkeeper_can_request_account_deactivation_with_password(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)

        response = self.client.post(
            reverse("api_settings_deactivation_request"),
            data=json.dumps({
                "current_password": "SafeBooks#123",
                "reason": "No longer managing clients.",
            }),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(
            BookkeeperDeactivationRequest.objects.filter(
                bookkeeper=account,
                status=BookkeeperDeactivationRequest.STATUS_PENDING,
            ).count(),
            1,
        )

    def test_deactivation_request_rejects_wrong_password(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)

        response = self.client.post(
            reverse("api_settings_deactivation_request"),
            data=json.dumps({"current_password": "WrongPassword#123"}),
            content_type="application/json",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok"))
        self.assertFalse(BookkeeperDeactivationRequest.objects.filter(bookkeeper=account).exists())

    def test_deactivation_request_is_not_duplicated(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)

        for _ in range(2):
            response = self.client.post(
                reverse("api_settings_deactivation_request"),
                data=json.dumps({"current_password": "SafeBooks#123"}),
                content_type="application/json",
                HTTP_ACCEPT="application/json",
            )
            self.assertIn(response.status_code, {200, 201})
            self.assertTrue(response.json().get("ok"))

        self.assertEqual(
            BookkeeperDeactivationRequest.objects.filter(
                bookkeeper=account,
                status=BookkeeperDeactivationRequest.STATUS_PENDING,
            ).count(),
            1,
        )
