from safebooks.tests.session_helpers import bind_authenticated_session

import json
import re
from html import unescape
from urllib.parse import parse_qs, urlsplit

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
        bind_authenticated_session(session)
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

    def test_new_account_defaults_to_unlocked_and_can_opt_in(self):
        account = BookkeeperAccount.objects.create(
            full_name="Opt In Tester", username="opt_in_tester", email="opt-in@example.test",
            password_hash=make_password("SafeBooks#123"), status=BookkeeperAccount.STATUS_APPROVED,
        )
        account.refresh_from_db()
        self.assertFalse(account.client_details_password_required)
        self._login_as(account)
        client = self._create_client(account)
        self.assertEqual(self.client.get(reverse("client_details", args=[client.id])).status_code, 200)
        settings = self.client.get(reverse("settings"))
        self.assertContains(settings, 'data-client-details-lock-enabled="false"')
        endpoint = reverse("api_security_client_details_access_preference")
        for password in ("", "Incorrect#123"):
            response = self.client.post(endpoint, data=json.dumps({"enabled": True, "current_password": password}), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            account.refresh_from_db()
            self.assertFalse(account.client_details_password_required)
        response = self.client.post(endpoint, data=json.dumps({"enabled": True, "current_password": "SafeBooks#123"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertTrue(account.client_details_password_required)
        self.assertContains(self.client.get(reverse("settings")), 'data-client-details-lock-enabled="true"')
        locked = self.client.get(reverse("client_details", args=[client.id]))
        self.assertEqual(locked.status_code, 302)

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

    def test_client_details_actions_keep_add_entry_without_redundant_records_link(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/client_details.html")
        self.assertNotContains(response, "clientDetailsRecordsLink")
        self.assertContains(response, 'id="editClientDetailsButton"')
        self.assertNotContains(response, 'id="generateReportActionBtn"')
        self.assertContains(response, 'id="closeClientActionBtn"')
        self.assertContains(response, f'href="{reverse("financial_records")}"')
        add_link = re.search(
            r'<a href="([^"]+)"[^>]*id="clientDetailsAddEntryLink"',
            response.content.decode(),
        )
        self.assertIsNotNone(add_link)
        target = urlsplit(unescape(add_link.group(1)))
        self.assertEqual(target.path, reverse("financial_records_client"))
        self.assertEqual(parse_qs(target.query), {
            "client_id": [str(client.id)],
            "client": [client.client_name],
            "tin": [client.tin_number],
            "trade": [client.trade_name],
            "action": ["add"],
        })

    def test_closed_client_actions_keep_reopen_without_records_or_report_button(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)
        client.remarks = Client.REMARK_CLOSED
        client.save(update_fields=["remarks"])

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "clientDetailsRecordsLink")
        self.assertNotContains(response, 'id="clientDetailsAddEntryLink"')
        self.assertNotContains(response, 'id="closeClientActionBtn"')
        self.assertContains(response, 'id="editClientDetailsButton"')
        self.assertNotContains(response, 'id="generateReportActionBtn"')
        self.assertContains(response, 'id="reopenClientActionBtn"')
        self.assertContains(response, f'href="{reverse("financial_records")}"')

    def test_client_details_keeps_key_labels_without_repeated_explanations(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("client_details", args=[client.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Record Schedule Status")
        self.assertContains(response, 'class="visually-hidden" id="clientPeriodReadinessText"')
        self.assertContains(response, 'id="clientWorkflowScheduleList" aria-label="Record schedule status" hidden')
        self.assertContains(response, "Projected Sales")
        self.assertContains(response, 'id="analyticsPredictiveSalesNote"')
        self.assertContains(response, 'for="analyticsYearFilter"')
        self.assertContains(response, 'for="analyticsHorizonFilter"')
        self.assertNotContains(response, "Checks each record frequency saved for this client.")
        self.assertNotContains(response, 'class="client-panel-defense-labels"')

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

    def test_protected_details_redirect_prepares_selected_client_prompt(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)
        detail_url = reverse("client_details", args=[client.id]) + "?year=2025&horizon=6"

        response = self.client.get(detail_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/clients.html")
        self.assertEqual(response.context["client_details_access_target"], {
            "clientId": client.id,
            "clientName": client.client_name,
            "url": detail_url,
        })
        self.assertContains(response, 'id="clientDetailsAccessTarget"')
        self.assertContains(response, "openClientAccessConfirmModal(redirectedClientDetailsTarget, redirectedClientDetailsTarget.url)")
        self.assertContains(response, 'directoryUrl.searchParams.delete("client_access_required")')
        self.assertContains(response, 'directoryUrl.searchParams.delete("next")')
        self.assertContains(response, 'addEventListener("hide.bs.modal"')
        self.assertContains(response, "if (pendingClientDetailsTarget !== target)")

    def test_normal_directory_does_not_prepare_a_password_prompt(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)

        for params in ({}, {"next": reverse("client_details", args=[client.id])}):
            with self.subTest(params=params):
                response = self.client.get(reverse("clients"), params)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.context["client_details_access_target"])
                self.assertNotContains(response, 'id="clientDetailsAccessTarget"')

    def test_disabled_lock_ignores_stale_password_prompt_parameters(self):
        account = self._create_bookkeeper(lock_enabled=False)
        self._login_as(account)
        client = self._create_client(account)

        response = self.client.get(reverse("clients"), {
            "client_access_required": "1",
            "next": reverse("client_details", args=[client.id]),
        })

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["client_details_access_target"])
        self.assertNotContains(response, 'id="clientDetailsAccessTarget"')

    def test_password_prompt_rejects_unsafe_or_non_detail_return_targets(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)
        detail_url = reverse("client_details", args=[client.id])
        invalid_targets = (
            "", "https://example.com" + detail_url, "//example.com" + detail_url,
            "https://testserver" + detail_url, "\\\\example.com" + detail_url,
            detail_url.lstrip("/"), detail_url + "#section", "/clients/not-an-id/",
            "/clients/999999/", detail_url + "../", reverse("dashboard"),
            reverse("api_client_detail", kwargs={"client_id": client.id}),
        )

        for target in invalid_targets:
            with self.subTest(target=target):
                response = self.client.get(reverse("clients"), {
                    "client_access_required": "1", "next": target,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.context["client_details_access_target"])
                self.assertNotContains(response, 'id="clientDetailsAccessTarget"')

    def test_password_prompt_does_not_expose_another_bookkeepers_client(self):
        account = self._create_bookkeeper(lock_enabled=True)
        other_account = self._create_bookkeeper(lock_enabled=False)
        foreign_client = self._create_client(other_account)
        self._login_as(account)
        detail_url = reverse("client_details", args=[foreign_client.id])

        response = self.client.get(reverse("clients"), {
            "client_access_required": "1", "next": detail_url,
        })

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["client_details_access_target"])
        self.assertNotContains(response, 'id="clientDetailsAccessTarget"')
        self.assertNotContains(response, foreign_client.client_name)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

    def test_password_prompt_escapes_client_name_as_json_data(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)
        client.client_name = '</script><script>alert("client")</script>'
        client.save(update_fields=["client_name"])

        response = self.client.get(reverse("client_details", args=[client.id]), follow=True)

        self.assertEqual(response.context["client_details_access_target"]["clientName"], client.client_name)
        self.assertContains(response, r"\u003C/script\u003E\u003Cscript\u003E")
        self.assertNotContains(response, client.client_name)

    def test_selected_client_prompt_still_requires_correct_password(self):
        account = self._create_bookkeeper(lock_enabled=True)
        self._login_as(account)
        client = self._create_client(account)
        detail_url = reverse("client_details", args=[client.id])
        response = self.client.get(detail_url, follow=True)
        target = response.context["client_details_access_target"]

        wrong_response = self.client.post(
            reverse("api_security_client_details_access_confirm"),
            data=json.dumps({"current_password": "WrongPassword#123"}),
            content_type="application/json",
        )
        self.assertEqual(wrong_response.status_code, 400)
        self.assertEqual(self.client.get(target["url"]).status_code, 302)

        correct_response = self.client.post(
            reverse("api_security_client_details_access_confirm"),
            data=json.dumps({"current_password": "SafeBooks#123"}),
            content_type="application/json",
        )
        self.assertEqual(correct_response.status_code, 200)
        detail_response = self.client.get(target["url"])
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.context["client"].id, client.id)
        self.assertEqual(self.client.get(target["url"]).status_code, 302)

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
