from hashlib import sha256
import uuid

from django.db import transaction
from django.urls import reverse

from safebooks.models import BookkeeperAccount, BookkeeperAuditLog, BookkeeperProof
from safebooks.validators.bookkeeper_proof_validator import validate_proof


def proof_metadata(proof, *, admin=False):
    if proof is None:
        return None
    route = "api_admin_bookkeeper_proof_download" if admin else "api_bookkeeper_proof_download"
    args = [proof.bookkeeper_id, proof.revision] if admin else [proof.revision]
    return {
        "revision": str(proof.revision), "document_type": proof.document_type,
        "document_name": proof.document_name or proof.get_document_type_display(),
        "size": proof.size, "submitted_at": proof.submitted_at.isoformat(),
        "download_url": reverse(route, args=args),
    }


def save_proof(account_id, upload, document_type, document_name, expected_revision):
    data, media_type, name = validate_proof(upload, document_type, document_name)
    with transaction.atomic():
        account = BookkeeperAccount.objects.select_for_update().get(pk=account_id)
        if account.status != BookkeeperAccount.STATUS_PENDING or not account.email_verified:
            return {"ok": False, "message": "Proof submission is available only while your verified account is pending approval."}, 403
        proof = BookkeeperProof.objects.filter(bookkeeper=account).first()
        current_revision = str(proof.revision) if proof else ""
        if str(expected_revision or "") != current_revision:
            return {"ok": False, "message": "Your submission changed. Reload this page before replacing it."}, 409
        if proof is None:
            proof = BookkeeperProof(bookkeeper=account)
        proof.revision = uuid.uuid4()
        proof.document_type, proof.document_name = document_type, name
        proof.content, proof.media_type, proof.size = data, media_type, len(data)
        proof.sha256 = sha256(data).hexdigest()
        proof.save()
        BookkeeperAuditLog.objects.create(
            bookkeeper=account, action_type="verification.proof_submitted", target_model="BookkeeperProof",
            target_id=proof.id, message="Submitted bookkeeping verification proof.",
            metadata={"revision": str(proof.revision), "sha256": proof.sha256},
        )
    return {"ok": True, "message": "Proof submitted for admin review.", "proof": proof_metadata(proof)}, 200
