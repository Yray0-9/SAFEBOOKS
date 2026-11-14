"""Synthetic regressions for last-used-client validation and ownership."""
import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from safebooks.models import BookkeeperAccount, Client
from safebooks.models.workspace_defaults_model import WorkspaceDefaults
from safebooks.services.settings_service import _normalize_last_client_id
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class LastClientIdValidationTests(SimpleTestCase):
    def test_rejects_malformed_and_out_of_range_ids(self):
        values = {
            "superscript": "²", "unicode_digits": "１２３", "decimal": "1.0",
            "float": 1.0, "true": True, "false": False, "list": [1], "object": {},
            "zero": 0, "negative": -1, "whitespace": " ", "null_character": "1\x00",
            "overflow_string": str(2**63), "overflow_integer": 2**63,
            "very_long": "9" * 5000, "very_large_integer": 2**20000,
        }
        for label, value in values.items():
            with self.subTest(case=label):
                self.assertEqual(_normalize_last_client_id(value), (None, "Last used client must be a valid id."))

    def test_preserves_integer_strings_padding_and_database_boundary(self):
        for value, expected in ((1, 1), (" 001 ", 1), ("0" * 5000 + "1", 1), (str(2**63 - 1), 2**63 - 1)):
            with self.subTest(expected=expected):
                self.assertEqual(_normalize_last_client_id(value), (expected, None))

    def test_preserves_existing_clear_values(self):
        for value in (None, "", "all", "null"):
            with self.subTest(value=value):
                self.assertEqual(_normalize_last_client_id(value), (None, None))


class WorkspaceDefaultsApiTests(TestCase):
    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(
            full_name="Synthetic Defaults Owner", username="defaults_owner",
            email="defaults-owner@example.test", password_hash="unused",
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        self.other = BookkeeperAccount.objects.create(
            full_name="Synthetic Other Owner", username="defaults_other",
            email="defaults-other@example.test", password_hash="unused",
            status=BookkeeperAccount.STATUS_APPROVED,
        )
        self.ledger = Client.objects.create(bookkeeper=self.owner, client_name="Synthetic Owned Client", tin_number="000000008001", location="Synthetic Location")
        self.foreign = Client.objects.create(bookkeeper=self.other, client_name="Synthetic Foreign Client", tin_number="000000008002", location="Synthetic Location")
        self.defaults = WorkspaceDefaults.objects.create(bookkeeper=self.owner, last_client=self.ledger)
        self.other_defaults = WorkspaceDefaults.objects.create(bookkeeper=self.other, last_client=self.foreign)
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.pk
        bind_authenticated_session(session)
        session.save()
        self.url = reverse("api_workspace_defaults")

    def post(self, payload):
        return self.client.post(self.url, json.dumps(payload), content_type="application/json")

    def test_invalid_id_returns_safe_400_without_client_lookup_or_partial_update(self):
        values = {"superscript": "²", "overflow": str(2**63), "long": "9" * 5000, "float": 1.0, "bool": True, "list": [1]}
        for label, value in values.items():
            with self.subTest(case=label), patch("safebooks.services.settings_service.Client.objects.filter") as lookup:
                response = self.post({"last_client_id": value, "default_report_range": "30"})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"ok": False, "message": "Last used client must be a valid id.", "errors": ["Last used client must be a valid id."]})
                lookup.assert_not_called()
                self.defaults.refresh_from_db()
                self.assertEqual(self.defaults.last_client_id, self.ledger.pk)
                self.assertEqual(self.defaults.default_report_range, "ytd")

    def test_valid_owned_id_keeps_success_envelope(self):
        response = self.post({"last_client_id": f" 00{self.ledger.pk} "})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["defaults"]["last_client_id"], self.ledger.pk)
        self.assertEqual(self.client.get(self.url).json()["defaults"]["last_client_id"], self.ledger.pk)

    def test_foreign_missing_and_maximum_ids_are_rejected_without_changing_defaults(self):
        for value in (self.foreign.pk, 999999999, 2**63 - 1):
            with self.subTest(value=value):
                response = self.post({"last_client_id": value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["message"], "Last used client was not found.")
                self.assertNotIn(self.foreign.client_name, response.content.decode())
                self.defaults.refresh_from_db()
                self.other_defaults.refresh_from_db()
                self.assertEqual(self.defaults.last_client_id, self.ledger.pk)
                self.assertEqual(self.other_defaults.last_client_id, self.foreign.pk)

    def test_clear_values_and_unrelated_preferences_still_save(self):
        for value in (None, "", "all", "null"):
            with self.subTest(value=value):
                self.defaults.last_client = self.ledger
                self.defaults.save(update_fields=["last_client"])
                response = self.post({"last_client_id": value, "default_report_range": "30"})
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.json()["defaults"]["last_client_id"])
                self.defaults.refresh_from_db()
                self.assertIsNone(self.defaults.last_client_id)
                self.assertEqual(self.defaults.default_report_range, "30")

    def test_requires_authentication_and_rejects_invalid_json(self):
        self.assertEqual(self.client.post(self.url, "{", content_type="application/json").status_code, 400)
        self.client.logout()
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(self.url, HTTP_ACCEPT="application/json").status_code, 401)
