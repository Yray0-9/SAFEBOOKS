from safebooks.tests.session_helpers import bind_authenticated_session

import json

from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount, BookkeeperAuditLog
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class BookkeeperProfilePageTests(TestCase):
    def setUp(self):
        self.bookkeeper = BookkeeperAccount.objects.create(
            full_name="Profile Test Bookkeeper",
            username="profile_test_bookkeeper",
            email="profile-test@example.com",
            password_hash="not-used-in-test",
            status=BookkeeperAccount.STATUS_APPROVED,
            email_verified=True,
            location="Davao City",
        )

    def login_bookkeeper(self):
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.bookkeeper.id
        bind_authenticated_session(session)
        session.save()

    def test_profile_page_and_api_require_authentication(self):
        page = self.client.get(reverse("profile"))
        api = self.client.get(reverse("api_profile"), HTTP_ACCEPT="application/json")

        self.assertEqual(page.status_code, 302)
        self.assertIn(reverse("login"), page["Location"])
        self.assertEqual(api.status_code, 401)

    def test_profile_page_preserves_form_hooks_and_settings_navigation(self):
        self.login_bookkeeper()
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/profile.html")
        self.assertContains(response, "20261002-profile-mobile")
        self.assertContains(response, "dashboard-page profile-page")
        self.assertContains(response, 'data-scroll-target="#profilePersonalDetails"')
        self.assertContains(response, f'href="{reverse("settings")}"')
        self.assertContains(response, "data-profile-save disabled")
        for field_id in ("profileFullName", "profileUsername", "profileEmail", "profileLocation"):
            self.assertContains(response, f'id="{field_id}"')
            self.assertContains(response, f'for="{field_id}"')
        self.assertEqual(response.context["profile_data"]["location"], "Davao City")
        self.assertFalse(BookkeeperAuditLog.objects.filter(bookkeeper=self.bookkeeper).exists())

    def test_profile_page_renders_long_identity_values_without_changing_them(self):
        self.bookkeeper.full_name = "BookkeeperWithALongDisplayName" * 3
        self.bookkeeper.email = "bookkeeper." + "longaddress" * 3 + "@example.com"
        self.bookkeeper.save(update_fields=["full_name", "email"])
        self.login_bookkeeper()

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["profile_data"]["full_name"], self.bookkeeper.full_name)
        self.assertEqual(response.context["profile_data"]["email"], self.bookkeeper.email)
        self.bookkeeper.refresh_from_db()
        self.assertEqual(self.bookkeeper.full_name, "BookkeeperWithALongDisplayName" * 3)

    def test_profile_save_keeps_the_existing_payload_and_response(self):
        self.login_bookkeeper()
        payload = {
            "full_name": "Updated Profile Name",
            "username": self.bookkeeper.username,
            "email": self.bookkeeper.email,
            "location": "Panabo City",
        }

        response = self.client.post(
            reverse("api_profile"), data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertFalse(response.json()["requires_email_verification"])
        for field, value in payload.items():
            self.assertEqual(response.json()["user"][field], value)
        self.bookkeeper.refresh_from_db()
        self.assertEqual(self.bookkeeper.full_name, payload["full_name"])
        self.assertEqual(self.bookkeeper.location, payload["location"])
        self.assertTrue(
            BookkeeperAuditLog.objects.filter(
                bookkeeper=self.bookkeeper, action_type=BookkeeperAuditLog.ACTION_PROFILE_UPDATED
            ).exists()
        )

    def test_invalid_profile_save_preserves_saved_data(self):
        self.login_bookkeeper()
        response = self.client.post(
            reverse("api_profile"),
            data=json.dumps({"full_name": "", "username": "", "email": "invalid", "location": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.bookkeeper.refresh_from_db()
        self.assertEqual(self.bookkeeper.full_name, "Profile Test Bookkeeper")
        self.assertEqual(self.bookkeeper.email, "profile-test@example.com")
        self.assertEqual(self.bookkeeper.location, "Davao City")
