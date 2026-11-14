"""Synthetic financial writes: atomicity, stale tabs, and isolated worker contention."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.db import DatabaseError, OperationalError, close_old_connections, connection, transaction
from django.db.models.query import QuerySet
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse

from safebooks.models import BookkeeperAccount, BookkeeperAuditLog, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.services import financial_record_service as service
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SAFEBOOKS_CLIENT_RECORD_EMAILS_ENABLED=True)
class FinancialReliabilityTests(TransactionTestCase):
    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(
            full_name="Synthetic Bookkeeper", username="reliability", email="reliability@example.test",
            password_hash="synthetic-unused", status=BookkeeperAccount.STATUS_APPROVED,
        )
        self.ledger = Client.objects.create(
            bookkeeper=self.owner, client_name="Synthetic Client", tin_number="123456789000",
            location="Test City", remarks=Client.REMARK_NEW, email="client@example.test",
        )
        self.list_url = reverse("api_financial_records", args=[self.ledger.id])
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.id
        bind_authenticated_session(session)
        session.save()
        mail.outbox = []

    def payload(self, **changes):
        data = {"date": "2026-04-15", "frequency": "monthly", "notes": "Synthetic note",
                "line_items": [{"type_code": "Sales", "description": "First", "amount": "123.456"},
                               {"type_code": "Expenses", "description": "Second", "amount": "10.00"}]}
        data.update(changes)
        return data

    def create(self, **changes):
        response = self.client.post(self.list_url, json.dumps(self.payload(**changes)), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        return response.json()["record"]

    def detail_url(self, record):
        return reverse("api_financial_record_detail", args=[self.ledger.id, record["id"]])

    def update(self, record, **changes):
        payload = {"expected_revision": record["revision"], **changes}
        return self.client.patch(self.detail_url(record), json.dumps(payload), content_type="application/json")

    def delete(self, record):
        return self.client.delete(self.detail_url(record), json.dumps({"expected_revision": record["revision"]}), content_type="application/json")

    def snapshot(self, record):
        obj = FinancialRecord.objects.get(id=record["id"])
        return (obj.period_id, obj.entry_date, obj.frequency, obj.notes, obj.deadline_date, obj.total_amount, obj.updated_at,
                list(obj.line_items.values_list("id", "type_code", "description", "amount", "sort_order")),
                list(Period.objects.filter(client=self.ledger).values_list("id", "year", "month")),
                BookkeeperAuditLog.objects.filter(bookkeeper=self.owner).count())

    def test_create_and_update_preserve_decimal_totals_order_and_audit(self):
        record = self.create()
        self.assertEqual(record["total_amount"], "133.46")
        self.assertEqual([line["description"] for line in record["line_items"]], ["First", "Second"])
        response = self.update(record, notes="Changed", line_items=[
            {"type_code": "Sales", "description": "Replacement", "amount": "0.105"},
            {"type_code": "Expenses", "description": "Next", "amount": "1.995"},
        ])
        self.assertEqual(response.status_code, 200)
        updated = response.json()["record"]
        self.assertEqual(updated["total_amount"], "2.10")
        self.assertNotEqual(updated["revision"], record["revision"])
        self.assertEqual([line["description"] for line in updated["line_items"]], ["Replacement", "Next"])
        self.assertEqual(BookkeeperAuditLog.objects.filter(bookkeeper=self.owner).count(), 2)

    def test_successful_crud_has_exactly_one_audit_per_operation(self):
        record = self.create()
        updated = self.update(record, notes="One change").json()["record"]
        self.assertEqual(self.delete(updated).status_code, 200)
        self.assertEqual(list(BookkeeperAuditLog.objects.order_by("id").values_list("action_type", flat=True)),
                         ["record.created", "record.updated", "record.deleted"])
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertFalse(FinancialRecordLine.objects.exists())
        self.assertFalse(Period.objects.exists())

    def test_two_loaded_tabs_cannot_overwrite_or_delete_newer_entry(self):
        old = self.create()
        self.assertEqual(self.update(old, notes="Winning tab").status_code, 200)
        before = self.snapshot(old)
        for response in (self.update(old, notes="Stale tab"), self.delete(old)):
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["code"], "stale_record")
            self.assertEqual(self.snapshot(old), before)

    def test_missing_or_invalid_revision_is_rejected_without_changes(self):
        record = self.create()
        before = self.snapshot(record)
        for revision in (None, "", 1, {}, "made-up-revision"):
            with self.subTest(revision=revision):
                data = {"notes": "Must not save", "expected_revision": revision}
                for method in (self.client.put, self.client.patch, self.client.delete):
                    response = method(self.detail_url(record), json.dumps(data), content_type="application/json")
                    self.assertEqual(response.status_code, 409)
                    self.assertEqual(self.snapshot(record), before)
        response = self.client.delete(self.detail_url(record))
        self.assertEqual(response.status_code, 409)

    def test_record_deleted_in_another_tab_is_not_recreated(self):
        record = self.create()
        self.assertEqual(self.delete(record).status_code, 200)
        for response in (self.update(record, notes="Late edit"), self.delete(record)):
            self.assertEqual(response.status_code, 404)
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertEqual(BookkeeperAuditLog.objects.count(), 2)

    def test_patch_keeps_existing_lines_deadline_and_frequency(self):
        record = self.create(deadline_date="2026-05-20", frequency="quarterly")
        old_ids = [line["id"] for line in record["line_items"]]
        updated = self.update(record, notes="Only notes").json()["record"]
        self.assertEqual([line["id"] for line in updated["line_items"]], old_ids)
        self.assertEqual(updated["deadline_date"], "2026-05-20")
        self.assertEqual(updated["frequency"], "quarterly")
        self.assertEqual(updated["total_amount"], "133.46")

    def test_page_renders_accessible_feedback_and_list_returns_current_revision(self):
        record = self.create()
        page = self.client.get(reverse("financial_records_client"), {"client_id": self.ledger.id})
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, "base/financial_records_client.html")
        self.assertContains(page, 'id="editEntryRevision" name="expected_revision"')
        self.assertContains(page, 'id="editEntryStatus" role="alert" hidden')
        self.assertContains(page, 'id="deleteEntryStatus" role="alert" hidden')
        response = self.client.get(self.list_url, {"month": 4, "year": 2026})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["records"][0]["revision"], record["revision"])
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_revision_advances_even_if_clock_moves_back(self):
        record = self.create()
        obj = FinancialRecord.objects.get(id=record["id"])
        with patch.object(service.timezone, "now", return_value=obj.updated_at - timedelta(days=1)):
            response = self.update(record, notes="Clock changed")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()["record"]["revision"], record["revision"])
        self.assertEqual(self.update(record, notes="Stale").status_code, 409)

    def test_create_line_failure_rolls_back_period_record_lines_and_email(self):
        original = FinancialRecordLine.objects.create
        calls = 0
        def fail_second_line(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise DatabaseError("Synthetic internal detail must not be returned")
            return original(**kwargs)
        with patch.object(FinancialRecordLine.objects, "create", side_effect=fail_second_line):
            response = self.client.post(self.list_url, json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Synthetic internal", response.content.decode())
        for model in (FinancialRecord, FinancialRecordLine, Period, BookkeeperAuditLog):
            self.assertFalse(model.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_create_audit_failure_rolls_back_client_promotion_and_all_financial_data(self):
        self.create(date="2026-03-10")
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.remarks, Client.REMARK_NEW)
        previous = (FinancialRecord.objects.count(), Period.objects.count(), BookkeeperAuditLog.objects.count(), len(mail.outbox))
        with patch.object(service, "record_bookkeeper_audit", side_effect=DatabaseError("Synthetic audit outage")):
            response = self.client.post(self.list_url, json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 503)
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.remarks, Client.REMARK_NEW)
        self.assertEqual((FinancialRecord.objects.count(), Period.objects.count(), BookkeeperAuditLog.objects.count(), len(mail.outbox)), previous)

    def test_status_failure_rolls_back_financial_create(self):
        with patch("safebooks.services.client_service.check_and_promote_new_client", side_effect=DatabaseError("Status outage")):
            result = service.create_record_for_client_period(self.owner, self.ledger.id, self.payload())
        self.assertFalse(result["ok"])
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertFalse(Period.objects.exists())
        self.assertFalse(BookkeeperAuditLog.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_update_audit_or_line_failure_restores_original_snapshot(self):
        record = self.create()
        before = self.snapshot(record)
        payload = self.payload(date="2026-05-10", expected_revision=record["revision"])
        for target in ("safebooks.services.financial_record_service.record_bookkeeper_audit",
                       "safebooks.services.financial_record_service.FinancialRecordLine.objects.create"):
            with self.subTest(target=target), patch(target, side_effect=DatabaseError("Synthetic update outage")):
                result = service.update_record_for_client_period(self.owner, self.ledger.id, record["id"], payload)
            self.assertFalse(result["ok"])
            self.assertEqual(self.snapshot(record), before)

    def test_delete_audit_or_cleanup_failure_restores_record_lines_period_and_audit(self):
        record = self.create()
        before = self.snapshot(record)
        original_delete = QuerySet.delete
        def fail_period_cleanup(queryset):
            if queryset.model is Period:
                raise DatabaseError("Synthetic cleanup outage")
            return original_delete(queryset)
        with patch.object(QuerySet, "delete", new=fail_period_cleanup):
            response = self.delete(record)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.snapshot(record), before)
        with patch.object(service, "record_bookkeeper_audit", side_effect=DatabaseError("Synthetic audit outage")):
            response = self.delete(record)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.snapshot(record), before)

    def test_delete_keeps_period_and_other_records_when_not_empty(self):
        first = self.create()
        second = self.create(date="2026-04-20")
        self.assertEqual(self.delete(first).status_code, 200)
        self.assertTrue(FinancialRecord.objects.filter(id=second["id"]).exists())
        self.assertEqual(Period.objects.count(), 1)
        self.assertEqual(FinancialRecordLine.objects.count(), 2)

    def test_failed_compare_and_swap_does_not_leave_target_period_or_lines(self):
        record = self.create()
        before = self.snapshot(record)
        original = QuerySet.update
        def no_record_updated(queryset, **kwargs):
            return 0 if queryset.model is FinancialRecord else original(queryset, **kwargs)
        with patch.object(QuerySet, "update", new=no_record_updated):
            response = self.update(record, date="2026-05-10", notes="Lost race")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.snapshot(record), before)

    def test_email_is_sent_only_after_outer_commit_and_is_cancelled_on_rollback(self):
        with transaction.atomic():
            result = service.create_record_for_client_period(self.owner, self.ledger.id, self.payload())
            self.assertEqual(mail.outbox, [])
            self.assertIn("pending", result["client_email_notification"]["reason"])
        self.assertTrue(result["client_email_notification"]["sent"])
        self.assertEqual(len(mail.outbox), 1)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                service.create_record_for_client_period(self.owner, self.ledger.id, self.payload(date="2026-06-10"))
                raise RuntimeError("Synthetic outer rollback")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(FinancialRecord.objects.count(), 1)
        self.assertEqual(BookkeeperAuditLog.objects.count(), 1)

    def test_unexpected_email_exception_does_not_report_a_committed_save_as_failed(self):
        with patch("safebooks.services.client_notification_service.send_financial_record_created_email", side_effect=RuntimeError("Synthetic email failure")):
            response = self.client.post(self.list_url, json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["client_email_notification"]["reason"], "Email delivery failed.")
        self.assertEqual(FinancialRecord.objects.count(), 1)
        self.assertEqual(BookkeeperAuditLog.objects.count(), 1)
        self.assertNotIn("Synthetic email failure", response.content.decode())

    def test_zero_email_acknowledgement_does_not_report_sent_or_undo_committed_record(self):
        with patch("safebooks.services.client_notification_service.send_mail", return_value=0):
            response = self.client.post(self.list_url, json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()["client_email_notification"]["sent"])
        self.assertFalse(response.json()["client_email_notification"]["skipped"])
        self.assertEqual(FinancialRecord.objects.count(), 1)
        self.assertEqual(BookkeeperAuditLog.objects.count(), 1)

    def test_database_lock_is_a_safe_conflict_not_partial_save(self):
        with patch.object(FinancialRecordLine.objects, "create", side_effect=OperationalError("database table is locked")):
            response = self.client.post(self.list_url, json.dumps(self.payload()), content_type="application/json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "write_conflict")
        self.assertFalse(FinancialRecord.objects.exists())
        self.assertFalse(Period.objects.exists())
        self.assertFalse(BookkeeperAuditLog.objects.exists())

    def test_commit_failure_rolls_back_and_does_not_send_notification(self):
        with patch.object(connection, "commit", side_effect=DatabaseError("Synthetic commit failure")):
            result = service.create_record_for_client_period(self.owner, self.ledger.id, self.payload())
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "persistence_failed")
        for model in (FinancialRecord, FinancialRecordLine, Period, BookkeeperAuditLog):
            self.assertFalse(model.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_invalid_delete_payload_does_not_mutate_or_audit(self):
        record = self.create()
        before = self.snapshot(record)
        response = self.client.delete(self.detail_url(record), "{", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.snapshot(record), before)

    def test_service_writes_enforce_bookkeeper_and_client_ownership(self):
        record = self.create()
        other = BookkeeperAccount.objects.create(full_name="Other", username="other", email="other@example.test", password_hash="unused", status="approved")
        before = self.snapshot(record)
        for result in (
            service.create_record_for_client_period(other, self.ledger.id, self.payload()),
            service.update_record_for_client_period(other, self.ledger.id, record["id"], {"expected_revision": record["revision"]}),
            service.delete_record_for_client(other, self.ledger.id, record["id"], {"expected_revision": record["revision"]}),
        ):
            self.assertFalse(result["ok"])
            self.assertEqual(result["message"], "Client not found.")
        self.assertEqual(self.snapshot(record), before)

    def test_record_cannot_be_updated_or_deleted_under_a_different_owned_client(self):
        record = self.create()
        other_client = Client.objects.create(bookkeeper=self.owner, client_name="Other ledger", tin_number="999888777000", location="Test City")
        url = reverse("api_financial_record_detail", args=[other_client.id, record["id"]])
        before = self.snapshot(record)
        for method in (self.client.patch, self.client.delete):
            response = method(url, json.dumps({"expected_revision": record["revision"], "notes": "Wrong ledger"}), content_type="application/json")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(self.snapshot(record), before)

    def test_audit_does_not_store_notes_line_descriptions_or_client_credentials(self):
        self.ledger.email_password = "SyntheticPrivateMarker"
        self.ledger.save(update_fields=["email_password"])
        record = self.create(notes="SyntheticPrivateNotes")
        log = BookkeeperAuditLog.objects.get(target_id=record["id"], action_type="record.created")
        serialized = json.dumps(log.metadata) + log.message
        for marker in ("SyntheticPrivateMarker", "SyntheticPrivateNotes", "First", "Second"):
            self.assertNotIn(marker, serialized)

    def run_workers(self, *operations):
        barrier = threading.Barrier(len(operations))
        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(run, operations))

    def test_simultaneous_edits_never_mix_lines_totals_or_duplicate_audits(self):
        record = self.create()
        def edit(amount):
            return lambda: service.update_record_for_client_period(self.owner, self.ledger.id, record["id"], {
                "expected_revision": record["revision"], "notes": f"Worker {amount}",
                "line_items": [{"type_code": "Sales", "description": "Worker", "amount": amount}],
            })
        results = self.run_workers(edit("200.00"), edit("300.00"))
        winners = [result for result in results if result["ok"]]
        self.assertLessEqual(len(winners), 1)
        for loser in (result for result in results if not result["ok"]):
            self.assertIn(loser["code"], {"stale_record", "write_conflict"})
        obj = FinancialRecord.objects.get(id=record["id"])
        self.assertEqual(obj.total_amount, sum(obj.line_items.values_list("amount", flat=True), Decimal("0.00")))
        self.assertEqual(BookkeeperAuditLog.objects.count(), 1 + len(winners))
        if winners:
            self.assertEqual(str(obj.total_amount), winners[0]["record"]["total_amount"])

    def test_simultaneous_create_and_cleanup_cannot_delete_a_new_record(self):
        old = self.create()
        results = self.run_workers(
            lambda: service.delete_record_for_client(self.owner, self.ledger.id, old["id"], {"expected_revision": old["revision"]}),
            lambda: service.create_record_for_client_period(self.owner, self.ledger.id, self.payload(date="2026-04-20")),
        )
        for result in results:
            if not result["ok"]:
                self.assertEqual(result["code"], "write_conflict")
        if results[1]["ok"]:
            self.assertTrue(FinancialRecord.objects.filter(id=results[1]["record"]["id"]).exists())
        self.assertEqual(FinancialRecord.objects.count(), 1 - int(results[0]["ok"]) + int(results[1]["ok"]))
        self.assertEqual(BookkeeperAuditLog.objects.count(), 1 + sum(int(result["ok"]) for result in results))
        for obj in FinancialRecord.objects.all():
            self.assertTrue(Period.objects.filter(id=obj.period_id).exists())
            self.assertEqual(obj.total_amount, sum(obj.line_items.values_list("amount", flat=True), Decimal("0.00")))

    @skipUnlessDBFeature("has_select_for_update")
    def test_row_lock_database_serializes_same_client_creates(self):
        results = self.run_workers(*(
            lambda: service.create_record_for_client_period(self.owner, self.ledger.id, self.payload()) for _ in range(2)
        ))
        self.assertTrue(all(result["ok"] for result in results))
        self.assertEqual(FinancialRecord.objects.count(), 2)
        self.assertEqual(Period.objects.count(), 1)
        self.assertEqual(BookkeeperAuditLog.objects.count(), 2)
