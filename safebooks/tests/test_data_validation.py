"""Safe synthetic boundary tests; never run this suite against the live database."""
import json
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.db.models.query import QuerySet
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount, BookkeeperAuditLog, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.services import auth_service, client_service, financial_record_service, profile_service
from safebooks.services.admin_profile_service import update_admin_profile
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.validators.data_validator import decimal_field_max, model_text_errors, normalize_nonnegative_decimal
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


class SharedDataValidatorTests(SimpleTestCase):
    def test_money_limits_come_from_model_and_existing_rounding_is_preserved(self):
        maximum = decimal_field_max(FinancialRecord, "total_amount")
        self.assertEqual(maximum, Decimal("999999999999.99"))
        for value, expected in [(0, "0.00"), ("0", "0.00"), ("1.005", "1.00"), ("1.015", "1.02"),
                                ("999999999999.994", "999999999999.99"), ("1e-1000000", "0.00")]:
            with self.subTest(value=value):
                amount, error = normalize_nonnegative_decimal(value, label="Amount", maximum=maximum, raw_maximum=False)
                self.assertIsNone(error)
                self.assertEqual(str(amount), expected)

    def test_invalid_numbers_and_overflow_are_validation_errors_not_exceptions(self):
        for value in ("NaN", "sNaN", "Infinity", "-Infinity", float("nan"), float("inf"), "1e1000000", "-1",
                      "999999999999.995", True, False, {}, [], "1_000", "123x", "0x10", "١٢"):
            with self.subTest(value=repr(value)):
                amount, error = financial_record_service._normalize_amount(value)
                self.assertIsNone(amount)
                self.assertTrue(error)

    def test_model_text_limits_count_unicode_characters_and_never_echo_values(self):
        self.assertEqual(model_text_errors(Client, {"client_name": "界" * 160}), [])
        errors = model_text_errors(Client, {"client_name": "界" * 161, "email_password": "PrivateMarker" * 30})
        self.assertEqual(len(errors), 2)
        self.assertNotIn("PrivateMarker", str(errors))
        self.assertNotIn("界", str(errors))

    def test_invalid_text_types_and_null_characters_are_rejected(self):
        for value in ([], {}, True, "bad\x00value"):
            self.assertTrue(model_text_errors(Client, {"client_name": value}))

    def test_period_edge_values_never_raise_or_accept_boolean_months(self):
        for value in ("²²²²", "9" * 5000, [], {}, True):
            year, error = financial_record_service._normalize_year(value)
            self.assertIsNone(year)
            self.assertTrue(error)
        for value in ("²", "9" * 5000, [], {}, True, False):
            month, error = financial_record_service._normalize_month(value)
            self.assertIsNone(month)
            self.assertTrue(error)


class DataValidationApiTests(TestCase):
    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(full_name="Synthetic Owner", username="validation-owner", email="owner@example.test", password_hash="unused", status="approved", client_details_password_required=False)
        self.ledger = Client.objects.create(bookkeeper=self.owner, client_name="Original Client", tin_number="123456789000", location="Test City")
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.id
        bind_authenticated_session(session)
        session.save()
        self.clients_url = reverse("api_clients")
        self.client_url = reverse("api_client_detail", args=[self.ledger.id])
        self.records_url = reverse("api_financial_records", args=[self.ledger.id])

    def client_payload(self, **changes):
        payload = {"client_name": "Valid Client", "tin_number": "999888777000", "location": "Test City"}
        payload.update(changes)
        return payload

    def record_payload(self, **changes):
        payload = {"date": "2026-04-15", "frequency": "monthly", "line_items": [{"type_code": "Sales", "description": "Valid transaction", "amount": "100.00"}]}
        payload.update(changes)
        return payload

    def create_record(self):
        response = self.client.post(self.records_url, json.dumps(self.record_payload()), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        return response.json()["record"]

    def assert_no_financial_write(self):
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertFalse(FinancialRecordLine.objects.exists())
        self.assertFalse(Period.objects.exists())
        self.assertFalse(BookkeeperAuditLog.objects.exists())

    def test_invalid_financial_numbers_return_400_without_any_writes(self):
        for amount in ("NaN", "sNaN", "Infinity", "-Infinity", "1e1000000", "999999999999.995", "-0.01", True, [], {}, "123junk", "1_000"):
            payload = self.record_payload(line_items=[{"type_code": "Sales", "description": "Valid", "amount": amount}])
            with self.subTest(amount=amount):
                response = self.client.post(self.records_url, json.dumps(payload), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["ok"])
                self.assert_no_financial_write()

    def test_numeric_zero_and_maximum_amount_are_accepted(self):
        for amount, expected in ((0, "0.00"), ("999999999999.99", "999999999999.99")):
            payload = self.record_payload(line_items=[{"type_code": "Sales", "description": "Valid", "amount": amount}])
            response = self.client.post(self.records_url, json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["record"]["total_amount"], expected)

    def test_combined_total_overflow_is_rejected_before_creating_period(self):
        payload = self.record_payload(line_items=[
            {"type_code": "Sales", "description": "First", "amount": "999999999999.99"},
            {"type_code": "Expenses", "description": "Second", "amount": "0.01"},
        ])
        response = self.client.post(self.records_url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Entry total", response.json()["message"])
        self.assert_no_financial_write()

    def test_invalid_update_keeps_record_revision_original_lines_and_audit(self):
        record = self.create_record()
        url = reverse("api_financial_record_detail", args=[self.ledger.id, record["id"]])
        before = list(FinancialRecordLine.objects.values_list("id", "amount", "description"))
        for amount in ("NaN", "1e1000000", "1000000000000.00"):
            payload = self.record_payload(date="2026-05-20", expected_revision=record["revision"], line_items=[{"type_code": "Sales", "description": "Changed", "amount": amount}])
            response = self.client.put(url, json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            obj = FinancialRecord.objects.get(id=record["id"])
            self.assertEqual(obj.updated_at.isoformat(), record["revision"])
            self.assertEqual(list(FinancialRecordLine.objects.values_list("id", "amount", "description")), before)
            self.assertEqual(Period.objects.count(), 1)
            self.assertEqual(BookkeeperAuditLog.objects.count(), 1)

    def test_line_text_limits_and_null_characters_are_checked_before_write(self):
        for field, value in (("type_code", "X" * 81), ("description", "X" * 256), ("description", "bad\x00value")):
            line = {"type_code": "Sales", "description": "Valid", "amount": "10.00", field: value}
            response = self.client.post(self.records_url, json.dumps(self.record_payload(line_items=[line])), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assert_no_financial_write()
        payload = self.record_payload(line_items=[{"type_code": "X" * 80, "description": "X" * 255, "amount": "10.00"}])
        self.assertEqual(self.client.post(self.records_url, json.dumps(payload), content_type="application/json").status_code, 201)

    def test_all_client_varchar_limits_are_enforced_without_truncation(self):
        for field in ("client_name", "trade_name", "location", "permit_number", "email_password", "orus_account", "orus_password"):
            limit = Client._meta.get_field(field).max_length
            for method, url, tin in ((self.client.post, self.clients_url, "999888777000"), (self.client.put, self.client_url, self.ledger.tin_number)):
                with self.subTest(field=field, method=method.__name__):
                    payload = self.client_payload(tin_number=tin, **{field: "X" * (limit + 1)})
                    response = method(url, json.dumps(payload), content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(str(limit), str(response.json()["errors"]))
                    self.assertEqual(Client.objects.count(), 1)
                    self.ledger.refresh_from_db()
                    self.assertEqual(self.ledger.client_name, "Original Client")
                    self.assertFalse(BookkeeperAuditLog.objects.exists())

    def test_client_exact_limits_and_omitted_credentials_are_preserved(self):
        payload = self.client_payload(**{field: "X" * Client._meta.get_field(field).max_length for field in ("client_name", "trade_name", "location", "permit_number", "email_password", "orus_account", "orus_password")})
        response = self.client.post(self.clients_url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        saved = Client.objects.get(id=response.json()["client"]["id"])
        for field, value in payload.items():
            self.assertEqual(getattr(saved, field), value)
        update = self.client_payload(tin_number=saved.tin_number)
        self.assertEqual(self.client.put(reverse("api_client_detail", args=[saved.id]), json.dumps(update), content_type="application/json").status_code, 200)
        saved.refresh_from_db()
        self.assertEqual(saved.email_password, "X" * 255)

    def test_client_growth_percent_rejects_nonfinite_negative_and_out_of_range(self):
        for value in ("NaN", "sNaN", "Infinity", "-Infinity", "1e1000000", "100.001", "-1", True, {}):
            response = self.client.post(self.clients_url, json.dumps(self.client_payload(forecast_growth_percent=value)), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(Client.objects.count(), 1)
            self.assertFalse(BookkeeperAuditLog.objects.exists())
        for value in (0, "0", "100", "1.005"):
            percent, error = client_service._normalize_forecast_growth_percent(value)
            self.assertIsNone(error)
            self.assertTrue(percent.is_finite())

    def test_malformed_custom_fields_and_nonfinite_custom_numbers_are_rejected(self):
        for fields in (["not an object"], [{"label": {}, "value": "test"}], [{"label": "Number", "type": "number", "value": "NaN"}], [{"label": "Number", "type": "number", "value": "123x"}],
                       [{"label": "Email", "type": "email", "value": "invalid"}], [{"label": "Date", "type": "date", "value": "2026-02-30"}],
                       [{"label": "TIN", "type": "tin", "value": "bad123456789000"}]):
            response = self.client.post(self.clients_url, json.dumps(self.client_payload(custom_fields=fields)), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(Client.objects.count(), 1)
        fields, error = client_service._normalize_custom_fields([{"label": "Zero", "type": "number", "value": 0}, {"label": "Negative", "type": "number", "value": "-1.2300"}])
        self.assertIsNone(error)
        self.assertEqual([field["value"] for field in fields], ["0", "-1.2300"])

    def test_formatted_tin_is_preserved_but_letters_and_non_ascii_digits_are_rejected(self):
        for value in ("bad999888777000", "９９９８８８７７７０００", [999888777000]):
            response = self.client.post(self.clients_url, json.dumps(self.client_payload(tin_number=value)), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(Client.objects.count(), 1)
        response = self.client.post(self.clients_url, json.dumps(self.client_payload(tin_number="999-888-777-000")), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["client"]["tin_number"], "999888777000")

    def test_invalid_close_payload_or_overlong_reason_does_not_close_client(self):
        for body in ("{", "[]", json.dumps({"reason": "X" * 256}), json.dumps({"reason": {"nested": "invalid"}})):
            response = self.client.delete(self.client_url, body, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.ledger.refresh_from_db()
            self.assertNotEqual(self.ledger.remarks, Client.REMARK_CLOSED)
            self.assertFalse(BookkeeperAuditLog.objects.exists())

    def test_nonstandard_and_extreme_json_returns_400_not_500(self):
        for body in ('{"forecast_growth_percent":NaN}', '{"forecast_growth_percent":Infinity}',
                     '{"forecast_growth_percent":' + "9" * 5000 + '}', '{"field":' + '[' * 1200 + '0' + ']' * 1200 + '}'):
            response = self.client.post(self.clients_url, body, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json()["ok"])
            self.assertEqual(Client.objects.count(), 1)
            self.assertFalse(BookkeeperAuditLog.objects.exists())

    def suppress_exists(self, model, count):
        original = QuerySet.exists
        seen = 0
        def hide_precheck(queryset):
            nonlocal seen
            if queryset.model is model:
                seen += 1
                if seen <= count:
                    return False
            return original(queryset)
        return patch.object(QuerySet, "exists", new=hide_precheck)

    def test_real_database_duplicate_tin_after_precheck_returns_409_and_keeps_connection_usable(self):
        with self.suppress_exists(Client, 1):
            response = self.client.post(self.clients_url, json.dumps(self.client_payload(tin_number=self.ledger.tin_number)), content_type="application/json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["message"], "TIN already exists.")
        self.assertEqual(Client.objects.count(), 1)
        self.assertFalse(BookkeeperAuditLog.objects.exists())
        self.assertEqual(self.client.get(self.clients_url).status_code, 200)

    def test_real_database_duplicate_tin_during_edit_rolls_back_all_changed_fields(self):
        other = Client.objects.create(bookkeeper=self.owner, client_name="Other", tin_number="999888777000", location="Test City")
        payload = self.client_payload(client_name="Must not save", tin_number=other.tin_number)
        with self.suppress_exists(Client, 1):
            result = client_service.update_client_for_bookkeeper(self.owner, self.ledger.id, payload)
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "TIN already exists.")
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.client_name, "Original Client")
        self.assertEqual(self.ledger.tin_number, "123456789000")

    def test_unknown_integrity_failure_never_exposes_database_details(self):
        with patch.object(Client.objects, "create", side_effect=IntegrityError("Synthetic private DB detail")):
            response = self.client.post(self.clients_url, json.dumps(self.client_payload()), content_type="application/json")
        self.assertFalse(response.json()["ok"])
        self.assertNotIn("Synthetic private", response.content.decode())
        self.assertEqual(Client.objects.count(), 1)

    def signup_payload(self, **changes):
        payload = {"full_name": "Synthetic Signup", "email": "signup@example.test", "username": "new-signup", "password": "SyntheticSignup#2026", "confirm_password": "SyntheticSignup#2026"}
        payload.update(changes)
        return payload

    def test_registration_field_lengths_invalid_email_and_null_name_are_rejected_before_email(self):
        for field, value in (("full_name", "X" * 121), ("username", "X" * 51), ("email", "invalid"), ("full_name", None), ("username", {})):
            with patch.object(auth_service, "send_email_verification_code") as send:
                result = auth_service.register_user(self.signup_payload(**{field: value}))
            self.assertFalse(result["ok"])
            send.assert_not_called()
            self.assertEqual(BookkeeperAccount.objects.count(), 1)

    def test_real_database_registration_uniqueness_failure_is_reported_without_email(self):
        for changes, message in (({"email": self.owner.email}, "Email already exists."), ({"username": self.owner.username}, "Username already exists.")):
            with self.suppress_exists(BookkeeperAccount, 2), patch.object(auth_service, "send_email_verification_code") as send:
                result = auth_service.register_user(self.signup_payload(**changes))
            self.assertFalse(result["ok"])
            self.assertEqual(result["message"], message)
            send.assert_not_called()
            self.assertEqual(BookkeeperAccount.objects.count(), 1)

    def test_database_rejects_case_variant_account_identifiers_without_service_prechecks(self):
        for changes in ({"email": self.owner.email.upper()}, {"username": self.owner.username.upper()}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                BookkeeperAccount.objects.create(**{
                    "full_name": "Duplicate", "username": "different-owner", "email": "different@example.test",
                    "password_hash": "unused", **changes,
                })
        admin = AdminAccount.objects.create(full_name="Admin", email="admin@example.test", password_hash="unused")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AdminAccount.objects.create(full_name="Duplicate", email=admin.email.upper(), password_hash="unused")
        self.assertEqual(BookkeeperAccount.objects.count(), 1)
        self.assertEqual(AdminAccount.objects.count(), 1)

    def test_case_variant_signup_races_return_existing_errors_without_sending_email(self):
        for changes, message in (({"email": self.owner.email.upper()}, "Email already exists."),
                                 ({"username": self.owner.username.upper()}, "Username already exists.")):
            with self.suppress_exists(BookkeeperAccount, 2), patch.object(auth_service, "send_email_verification_code") as send:
                result = auth_service.register_user(self.signup_payload(**changes))
            self.assertFalse(result["ok"])
            self.assertEqual(result["message"], message)
            send.assert_not_called()
            self.assertEqual(BookkeeperAccount.objects.count(), 1)

    def test_case_variant_google_signup_race_is_reported_without_creating_account(self):
        self.owner.email = self.owner.email.upper()
        self.owner.save(update_fields=["email"])
        profile = {"google_sub": "synthetic-sub", "email": self.owner.email.lower(), "full_name": "Google"}
        with self.suppress_exists(BookkeeperAccount, 3):
            result = auth_service.complete_google_signup(profile, self.signup_payload())
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "Email already exists. Please sign in with Google instead.")
        self.assertEqual(BookkeeperAccount.objects.count(), 1)

    def test_google_signup_rejects_overlong_profile_or_username(self):
        for profile, changes in (({"google_sub": "X" * 256, "email": "google@example.test", "full_name": "Google"}, {}),
                                 ({"google_sub": "synthetic-sub", "email": "google@example.test", "full_name": "X" * 121}, {"full_name": ""}),
                                 ({"google_sub": "synthetic-sub", "email": "google@example.test", "full_name": "Google"}, {"username": "X" * 51})):
            result = auth_service.complete_google_signup(profile, self.signup_payload(**changes))
            self.assertFalse(result["ok"])
            self.assertEqual(BookkeeperAccount.objects.count(), 1)

    def test_profile_model_limits_reject_without_changes_or_email(self):
        payload = {"full_name": self.owner.full_name, "email": self.owner.email, "username": self.owner.username, "location": "Test"}
        for field in ("full_name", "username", "location"):
            data = {**payload, field: "X" * (BookkeeperAccount._meta.get_field(field).max_length + 1)}
            with patch.object(profile_service, "send_email_verification_code") as send:
                result = profile_service.update_profile_for_bookkeeper(self.owner, data)
            self.assertFalse(result["ok"])
            send.assert_not_called()
            self.owner.refresh_from_db()
            self.assertEqual(self.owner.full_name, "Synthetic Owner")

    def test_profile_uniqueness_failure_is_checked_before_sending_verification_email(self):
        other = BookkeeperAccount.objects.create(full_name="Other", username="other", email="other@example.test", password_hash="unused", status="approved")
        data = {"full_name": "Must not save", "username": self.owner.username, "email": other.email, "location": "Test"}
        with self.suppress_exists(BookkeeperAccount, 2), patch.object(profile_service, "send_email_verification_code") as send:
            result = profile_service.update_profile_for_bookkeeper(self.owner, data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "Email already exists.")
        send.assert_not_called()
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.full_name, "Synthetic Owner")
        self.assertEqual(self.owner.email, "owner@example.test")

    def test_case_variant_profile_races_roll_back_and_do_not_send_email(self):
        other = BookkeeperAccount.objects.create(full_name="Other", username="OTHER", email="OTHER@EXAMPLE.TEST", password_hash="unused", status="approved")
        for changes, message in (({"email": other.email.lower()}, "Email already exists."),
                                 ({"username": other.username.lower()}, "Username already exists.")):
            data = {"full_name": "Must not save", "username": self.owner.username, "email": self.owner.email, "location": "Changed", **changes}
            with self.suppress_exists(BookkeeperAccount, 2), patch.object(profile_service, "send_email_verification_code") as send:
                result = profile_service.update_profile_for_bookkeeper(self.owner, data)
            self.assertFalse(result["ok"])
            self.assertEqual(result["message"], message)
            send.assert_not_called()
            self.owner.refresh_from_db()
            self.assertEqual(self.owner.full_name, "Synthetic Owner")
            self.assertEqual(self.owner.username, "validation-owner")
            self.assertEqual(self.owner.email, "owner@example.test")

    def test_own_case_only_username_change_and_separate_roles_remain_supported(self):
        with patch.object(profile_service, "send_email_verification_code") as send:
            result = profile_service.update_profile_for_bookkeeper(self.owner, {
                "full_name": self.owner.full_name, "username": self.owner.username.upper(),
                "email": self.owner.email, "location": "Test",
            })
        self.assertTrue(result["ok"])
        send.assert_not_called()
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.username, "VALIDATION-OWNER")
        AdminAccount.objects.create(full_name="Separate role", email=self.owner.email, password_hash="unused")
        self.assertEqual(AdminAccount.objects.count(), 1)

    def test_profile_email_failure_restores_all_fields_in_database_and_current_object(self):
        data = {"full_name": "Must not save", "username": "changed-owner", "email": "changed@example.test", "location": "Changed"}
        with patch.object(profile_service, "send_email_verification_code", return_value={"ok": False, "message": "Synthetic delivery unavailable"}):
            result = profile_service.update_profile_for_bookkeeper(self.owner, data)
        self.assertFalse(result["ok"])
        self.assertEqual(self.owner.email, "owner@example.test")
        self.assertEqual(self.owner.full_name, "Synthetic Owner")
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.full_name, "Synthetic Owner")
        self.assertEqual(self.owner.username, "validation-owner")
        self.assertEqual(self.owner.email, "owner@example.test")

    def test_admin_profile_limits_and_real_database_conflict_do_not_change_data_or_audit(self):
        admin = AdminAccount.objects.create(full_name="Original Admin", email="admin@example.test", password_hash="unused")
        other = AdminAccount.objects.create(full_name="Other Admin", email="other-admin@example.test", password_hash="unused")
        result = update_admin_profile(admin, {"full_name": "X" * 121, "email": admin.email})
        self.assertFalse(result["ok"])
        with self.suppress_exists(AdminAccount, 1):
            result = update_admin_profile(admin, {"full_name": "Must not save", "email": other.email})
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "Email already exists.")
        admin.refresh_from_db()
        self.assertEqual(admin.full_name, "Original Admin")
        self.assertEqual(admin.email, "admin@example.test")
        self.assertFalse(AdminAuditLog.objects.exists())

    def test_admin_case_variant_profile_race_keeps_original_data_and_audit(self):
        admin = AdminAccount.objects.create(full_name="Original Admin", email="admin@example.test", password_hash="unused")
        other = AdminAccount.objects.create(full_name="Other Admin", email="OTHER-ADMIN@EXAMPLE.TEST", password_hash="unused")
        with self.suppress_exists(AdminAccount, 1):
            result = update_admin_profile(admin, {"full_name": "Must not save", "email": other.email.lower()})
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "Email already exists.")
        admin.refresh_from_db()
        self.assertEqual(admin.full_name, "Original Admin")
        self.assertEqual(admin.email, "admin@example.test")
        self.assertFalse(AdminAuditLog.objects.exists())
