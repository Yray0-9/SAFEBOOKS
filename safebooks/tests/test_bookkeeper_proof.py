from io import BytesIO
import json
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection, close_old_connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.test.utils import CaptureQueriesContext
from pypdf import PdfWriter

from safebooks.models import AdminAccount, AdminAuditLog, BookkeeperAccount, BookkeeperAuditLog, BookkeeperProof
from safebooks.tests.proof_helpers import proof_image
from safebooks.tests.proof_helpers import create_test_proof
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.services.bookkeeper_proof_service import save_proof
from safebooks.services.admin_approvals_service import approve_bookkeeper
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


@override_settings(SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=False)
class BookkeeperProofTests(TestCase):
    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(full_name="Proof applicant", username="proof_applicant", email="proof@example.test", password_hash="unused", status="pending", email_verified=True)
        self.other = BookkeeperAccount.objects.create(full_name="Other applicant", username="other_applicant", email="other-proof@example.test", password_hash="unused", status="pending", email_verified=True)
        self.admin = AdminAccount.objects.create(full_name="Proof admin", email="proof-admin@example.test", password_hash="unused", is_active=True)
        self.login(self.owner)

    def login(self, account, client=None):
        client = client or self.client
        session = client.session
        session.clear()
        session[SESSION_ADMIN_ID_KEY if isinstance(account, AdminAccount) else SESSION_BOOKKEEPER_ID_KEY] = account.pk
        bind_authenticated_session(session)
        session.save()

    def upload(self, *, content=None, filename="proof.png", revision="", kind="business_permit", name="", **extra):
        return self.client.post(reverse("api_bookkeeper_proof"), {
            "document_type": kind, "document_name": name, "revision": revision,
            "document": SimpleUploadedFile(filename, proof_image() if content is None else content, content_type="application/octet-stream"), **extra,
        })

    def approve(self, revision, reviewed=True):
        return self.client.post(reverse("api_admin_approvals_approve", args=[self.owner.id]),
            data=json.dumps({"proof_revision": revision, "proof_reviewed": reviewed}), content_type="application/json")

    def test_private_upload_download_and_reviewed_approval(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        proof = response.json()["proof"]
        self.assertNotIn("content", proof)
        self.assertNotIn("/media/", proof["download_url"])
        download = self.client.get(proof["download_url"])
        self.assertEqual(download.content, proof_image())
        self.assertIn("attachment", download["Content-Disposition"])
        self.assertIn("no-store", download["Cache-Control"])
        self.assertEqual(download["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.get(reverse("api_clients")).status_code, 403)
        self.assertContains(self.client.get(reverse("pending_approval")), "Download submitted proof")
        self.assertContains(self.client.get(reverse("pending_approval")), 'download data-no-skeleton')
        self.login(self.admin)
        approvals_page = self.client.get(reverse("admin_approvals"))
        self.assertContains(approvals_page, "View proof (new tab)")
        self.assertNotContains(approvals_page, "Download proof")
        self.assertEqual(self.approve(proof["revision"]).status_code, 400, "A checkbox alone must not bypass downloading the proof")
        admin_url = reverse("api_admin_bookkeeper_proof_download", args=[self.owner.id, proof["revision"]])
        self.assertEqual(self.client.get(admin_url).status_code, 200)
        self.assertEqual(self.approve(proof["revision"], reviewed=False).status_code, 400)
        self.assertEqual(self.approve(proof["revision"]).status_code, 200)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.status, "approved")
        audit = AdminAuditLog.objects.get(action_type="bookkeeper.approved", target_id=self.owner.id)
        self.assertEqual(audit.metadata["proof_revision"], proof["revision"])
        self.assertEqual(len(audit.metadata["proof_sha256"]), 64)

    def test_no_proof_no_approval_and_existing_approved_account_keeps_access(self):
        self.login(self.admin)
        self.assertEqual(self.approve("").status_code, 400)
        self.assertFalse(AdminAuditLog.objects.filter(action_type="bookkeeper.approved").exists())
        self.owner.status = "approved"
        self.owner.save(update_fields=["status"])
        self.login(self.owner)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertEqual(self.upload().status_code, 403)

    def test_other_account_anonymous_and_unverified_cannot_read_or_submit(self):
        proof = self.upload().json()["proof"]
        admin_url = reverse("api_admin_bookkeeper_proof_download", args=[self.owner.id, proof["revision"]])
        self.login(self.other)
        self.assertEqual(self.client.get(proof["download_url"]).status_code, 404)
        self.assertEqual(self.client.get(admin_url).status_code, 403)
        self.other.email_verified = False
        self.other.save(update_fields=["email_verified"])
        self.assertEqual(self.upload().status_code, 403)
        self.assertEqual(self.client.get(proof["download_url"]).status_code, 403)
        self.assertEqual(Client().get(proof["download_url"]).status_code, 401)
        self.assertEqual(Client().post(reverse("api_bookkeeper_proof")).status_code, 401)

    def test_replacement_invalidates_old_download_and_admin_review_without_rewriting_account(self):
        original = self.upload().json()["proof"]
        admin_client = Client()
        self.login(self.admin, admin_client)
        admin_url = reverse("api_admin_bookkeeper_proof_download", args=[self.owner.id, original["revision"]])
        self.assertEqual(admin_client.get(admin_url).status_code, 200)
        self.assertEqual(self.upload().status_code, 409)
        current = self.upload(revision=original["revision"], kind="other", name="Experience letter").json()["proof"]
        self.assertNotEqual(current["revision"], original["revision"])
        self.assertEqual(BookkeeperProof.objects.count(), 1)
        self.assertEqual(self.client.get(original["download_url"]).status_code, 404)
        stale = admin_client.post(reverse("api_admin_approvals_approve", args=[self.owner.id]), data={"proof_revision": original["revision"], "proof_reviewed": True}, content_type="application/json")
        self.assertEqual(stale.status_code, 400)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.status, "pending")

    def test_review_receipt_expires_and_is_admin_session_scoped(self):
        proof = self.upload().json()["proof"]
        self.login(self.admin)
        self.client.get(reverse("api_admin_bookkeeper_proof_download", args=[self.owner.id, proof["revision"]]))
        session = self.client.session
        session["verification_proof_downloads"][str(self.owner.id)]["at"] -= 901
        session.save()
        self.assertEqual(self.approve(proof["revision"]).status_code, 400)

    def test_invalid_oversized_and_multiple_files_do_not_save(self):
        for data, filename in [(b"<script>private</script>", "proof.png"), (proof_image(), "proof.pdf"), (b"x" * (5 * 1024 * 1024 + 1), "proof.png")]:
            with self.subTest(filename=filename, size=len(data)):
                self.assertEqual(self.upload(content=data, filename=filename).status_code, 400)
        self.assertEqual(self.upload(kind="other", name="").status_code, 400)
        self.assertEqual(self.upload(name="x" * 121).status_code, 400)
        self.assertEqual(self.upload(extra_document=SimpleUploadedFile("extra.png", proof_image())).status_code, 400)
        self.assertFalse(BookkeeperProof.objects.exists())

    def test_pdf_validation_accepts_readable_and_rejects_encrypted_active_or_broken(self):
        def pdf(*, password=False, script=False):
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            if password: writer.encrypt("synthetic")
            if script: writer.add_js("app.alert('synthetic')")
            stream = BytesIO()
            writer.write(stream)
            return stream.getvalue()
        for data in [pdf(password=True), pdf(script=True), b"%PDF-1.7\nbroken"]:
            self.assertEqual(self.upload(content=data, filename="proof.pdf").status_code, 400)
        self.assertEqual(self.upload(content=pdf(), filename="proof.pdf").status_code, 200)

    def test_atomic_audit_failure_rolls_back_document_and_preserves_old_submission(self):
        original = self.upload().json()["proof"]
        with patch("safebooks.services.bookkeeper_proof_service.BookkeeperAuditLog.objects.create", side_effect=DatabaseError("synthetic")):
            response = self.upload(revision=original["revision"])
        self.assertEqual(response.status_code, 503)
        self.assertEqual(str(BookkeeperProof.objects.get(bookkeeper=self.owner).revision), original["revision"])
        self.assertEqual(BookkeeperAuditLog.objects.filter(action_type="verification.proof_submitted").count(), 1)

    def test_csrf_is_required_even_for_authenticated_pending_applicant(self):
        client = Client(enforce_csrf_checks=True)
        self.login(self.owner, client)
        response = client.post(reverse("api_bookkeeper_proof"), {"document": SimpleUploadedFile("proof.png", proof_image()), "document_type": "business_permit"})
        self.assertEqual(response.status_code, 403)

    def test_queue_uses_only_document_metadata(self):
        self.upload()
        self.login(self.admin)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("api_admin_approvals"))
        self.assertEqual(response.status_code, 200)
        row = next(row for row in response.json()["approvals"] if row["id"] == self.owner.id)
        self.assertEqual(row["proof"]["document_name"], "Business Permit")
        self.assertNotIn("content", row["proof"])
        proof_reads = [query["sql"] for query in queries if query["sql"].startswith("SELECT") and '"bookkeeper_verification_proofs"' in query["sql"]]
        self.assertEqual(len(proof_reads), 1)
        self.assertNotIn('"content"', proof_reads[0])


@skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL row locks")
@override_settings(SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED=False)
class ProofConcurrencyTests(TransactionTestCase):
    def test_replacement_cannot_race_past_reviewed_approval(self):
        owner = BookkeeperAccount.objects.create(full_name="Concurrent proof", username="concurrent_proof", email="concurrent-proof@example.test", password_hash="unused", email_verified=True, status="pending")
        admin = AdminAccount.objects.create(full_name="Concurrent reviewer", email="concurrent-reviewer@example.test", password_hash="unused", is_active=True)
        proof = create_test_proof(owner)
        original = str(proof.revision)
        barrier = Barrier(2)

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                if action == "replace":
                    result, _ = save_proof(owner.id, SimpleUploadedFile("proof.png", proof_image()), "business_permit", "", original)
                    return result
                return approve_bookkeeper(AdminAccount.objects.get(pk=admin.id), owner.id, proof_revision=original, proof_reviewed=True)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, ["replace", "approve"]))
        self.assertEqual(sum(result["ok"] for result in results), 1)
        owner.refresh_from_db()
        current = BookkeeperProof.objects.get(bookkeeper=owner)
        if owner.status == "approved":
            self.assertEqual(str(current.revision), original)
        else:
            self.assertEqual(owner.status, "pending")
            self.assertNotEqual(str(current.revision), original)
