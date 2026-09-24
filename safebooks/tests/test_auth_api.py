import json

from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class AuthApiTests(TestCase):
    def test_register_then_login_success_sets_session(self):
        register_payload = {
            "full_name": "Login Success User",
            "email": "login-success@example.com",
            "username": "login_success",
            "password": "SafeBooks#123",
            "confirm_password": "SafeBooks#123",
        }

        register_response = self.client.post(
            reverse("api_register"),
            data=json.dumps(register_payload),
            content_type="application/json",
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "login_success",
                "password": "SafeBooks#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 200)
        payload = login_response.json()
        self.assertTrue(payload.get("ok"))

        session = self.client.session
        self.assertIsNotNone(session.get(SESSION_BOOKKEEPER_ID_KEY))

    def test_login_invalid_credentials_returns_200_payload(self):
        account = BookkeeperAccount.objects.create(
            full_name="Invalid Login User",
            email="invalid-login@example.com",
            username="invalid_login",
            password_hash="pbkdf2_sha256$1000000$Y2mA0abcX8HnY1$hI3Y8J2wN8g7zXkQ9hP2Y6n2Q4S6D8w8rQ7fY3k8m2Q=",
        )
        account.password_hash = account.password_hash  # Keep explicit setup readable.
        account.save(update_fields=["password_hash"])

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "invalid_login",
                "password": "WrongPassword#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "Incorrect password. Please try again.")
        self.assertEqual(payload.get("field"), "password")
        self.assertEqual(payload.get("error_code"), "incorrect_password")

    def test_login_legacy_plaintext_password_hash_is_upgraded(self):
        account = BookkeeperAccount.objects.create(
            full_name="Legacy User",
            email="legacy-user@example.com",
            username="legacy_user",
            password_hash="LegacyPass#123",
        )

        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "legacy_user",
                "password": "LegacyPass#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))

        account.refresh_from_db()
        self.assertNotEqual(account.password_hash, "LegacyPass#123")
        self.assertTrue(check_password("LegacyPass#123", account.password_hash))

    def test_login_user_not_found_returns_clear_account_not_found_message(self):
        response = self.client.post(
            reverse("api_login"),
            data=json.dumps({
                "identifier": "not_existing_user",
                "password": "AnyPassword#123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("message"), "No account found with this email or username.")
        self.assertEqual(payload.get("field"), "identifier")
        self.assertEqual(payload.get("error_code"), "account_not_found")
