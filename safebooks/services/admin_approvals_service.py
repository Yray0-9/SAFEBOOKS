from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from safebooks.models import AdminAuditLog, BookkeeperAccount
from safebooks.services.bookkeeper_proof_service import proof_metadata
from safebooks.services.approval_notification_service import (
    DELIVERY_FAILED,
    format_decision_result_message,
    save_delivery_outcome,
    send_approval_decision_email,
)


VALID_APPROVAL_STATUSES = {
    BookkeeperAccount.STATUS_PENDING,
    BookkeeperAccount.STATUS_APPROVED,
    BookkeeperAccount.STATUS_REJECTED,
}

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


def _normalize_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized


def _normalize_positive_int(value, default: int, maximum: int | None = None) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = default

    normalized = max(1, normalized)
    if maximum is not None:
        normalized = min(normalized, maximum)
    return normalized


def _serialize_approval(account: BookkeeperAccount, email_delivery: dict | None = None) -> dict:
    approved_by = account.approved_by_admin
    status = account.status or BookkeeperAccount.STATUS_PENDING
    google_linked = bool((account.google_sub or "").strip())
    notification_preview = ""
    if status == BookkeeperAccount.STATUS_APPROVED:
        notification_preview = "Approved account: the bookkeeper can now access the SafeBooks workspace."
    elif status == BookkeeperAccount.STATUS_REJECTED:
        notification_preview = "Rejected account: the bookkeeper should review the saved reason before requesting access again."
    elif status == BookkeeperAccount.STATUS_PENDING:
        notification_preview = "Pending account: no decision notification has been sent yet."

    return {
        "id": account.id,
        "full_name": account.full_name,
        "email": account.email,
        "username": account.username,
        "status": status,
        "email_verified": bool(account.email_verified),
        "google_linked": google_linked,
        "created_at": account.created_at.isoformat() if account.created_at else "",
        "approved_at": account.approved_at.isoformat() if account.approved_at else "",
        "rejected_at": account.rejected_at.isoformat() if account.rejected_at else "",
        "rejection_reason": account.rejection_reason or "",
        "approved_by": approved_by.full_name if approved_by else "",
        "last_login": account.last_login.isoformat() if account.last_login else "",
        "notification_preview": notification_preview,
        "email_delivery": email_delivery or {},
        "proof": proof_metadata(getattr(account, "verification_proof", None), admin=True),
    }


def _create_approval_audit_log(
    admin_account,
    account: BookkeeperAccount,
    action_type: str,
    message: str,
    decision_note: str = "",
) -> AdminAuditLog:
    return AdminAuditLog.objects.create(
        admin=admin_account,
        action_type=action_type,
        target_model="BookkeeperAccount",
        target_id=account.id,
        message=message,
        metadata={
            "bookkeeper_id": account.id,
            "bookkeeper_name": account.full_name,
            "bookkeeper_email": account.email,
            "status": account.status,
            "decision_note": str(decision_note or "").strip()[:255],
        },
    )


def _email_delivery_from_log(audit_log: AdminAuditLog | None) -> dict:
    if audit_log is None:
        return {}
    metadata = audit_log.metadata if isinstance(audit_log.metadata, dict) else {}
    delivery = metadata.get("email_delivery")
    return dict(delivery) if isinstance(delivery, dict) else {}


def _latest_delivery_by_bookkeeper(bookkeeper_ids: list[int]) -> dict[int, dict]:
    if not bookkeeper_ids:
        return {}

    delivery_by_bookkeeper = {}
    decision_logs = (
        AdminAuditLog.objects
        .filter(
            target_model="BookkeeperAccount",
            target_id__in=bookkeeper_ids,
            action_type__in={
                AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
                AdminAuditLog.ACTION_BOOKKEEPER_REJECTED,
            },
        )
        .order_by("target_id", "-created_at", "-id")
    )
    for audit_log in decision_logs:
        if audit_log.target_id not in delivery_by_bookkeeper:
            delivery_by_bookkeeper[audit_log.target_id] = _email_delivery_from_log(audit_log)
    return delivery_by_bookkeeper


def _stale_approval_result(account: BookkeeperAccount, message: str) -> dict:
    return {
        "ok": False,
        "code": "stale_decision",
        "refresh_required": True,
        "message": message,
        "approval": _serialize_approval(account),
    }


def list_admin_approvals(
    admin_account,
    status: str | None,
    search: str | None,
    sort: str | None,
    page=None,
    page_size=None,
) -> dict:
    status_value = _normalize_status(status)
    search_value = str(search or "").strip()
    sort_value = _normalize_status(sort) or "newest"

    queryset = BookkeeperAccount.objects.select_related("approved_by_admin", "verification_proof").defer("verification_proof__content")

    if status_value in VALID_APPROVAL_STATUSES:
        queryset = queryset.filter(status=status_value)
    else:
        queryset = queryset.filter(status__in=VALID_APPROVAL_STATUSES)

    if search_value:
        queryset = queryset.filter(
            Q(full_name__icontains=search_value)
            | Q(email__icontains=search_value)
            | Q(username__icontains=search_value)
        )

    if sort_value == "oldest":
        queryset = queryset.order_by("created_at", "id")
    elif sort_value == "status":
        queryset = queryset.order_by("status", "-created_at", "-id")
    else:
        queryset = queryset.order_by("-created_at", "-id")

    pending_count = BookkeeperAccount.objects.filter(status=BookkeeperAccount.STATUS_PENDING).count()
    approved_count = BookkeeperAccount.objects.filter(status=BookkeeperAccount.STATUS_APPROVED).count()
    rejected_count = BookkeeperAccount.objects.filter(status=BookkeeperAccount.STATUS_REJECTED).count()
    today = timezone.localdate()
    approved_today = BookkeeperAccount.objects.filter(
        status=BookkeeperAccount.STATUS_APPROVED,
        approved_at__date=today,
    ).count()
    rejected_today = BookkeeperAccount.objects.filter(
        status=BookkeeperAccount.STATUS_REJECTED,
        rejected_at__date=today,
    ).count()

    normalized_page_size = _normalize_positive_int(page_size, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    paginator = Paginator(queryset, normalized_page_size)
    page_object = paginator.get_page(_normalize_positive_int(page, 1))
    accounts = list(page_object.object_list)
    delivery_by_bookkeeper = _latest_delivery_by_bookkeeper([account.id for account in accounts])
    approvals = [
        _serialize_approval(account, delivery_by_bookkeeper.get(account.id, {}))
        for account in accounts
    ]

    return {
        "ok": True,
        "counts": {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "approved_today": approved_today,
            "rejected_today": rejected_today,
        },
        "total_count": pending_count + approved_count + rejected_count,
        "pagination": {
            "page": page_object.number,
            "page_size": normalized_page_size,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "start_index": page_object.start_index() if paginator.count else 0,
            "end_index": page_object.end_index() if paginator.count else 0,
            "has_previous": page_object.has_previous(),
            "has_next": page_object.has_next(),
        },
        "approvals": approvals,
    }


def approve_bookkeeper(admin_account, bookkeeper_id: int, *, proof_revision=None, proof_reviewed=False) -> dict:
    with transaction.atomic():
        account = (
            BookkeeperAccount.objects
            .select_for_update()
            .filter(id=bookkeeper_id)
            .first()
        )
        if account is None:
            return {
                "ok": False,
                "message": "Bookkeeper not found.",
            }

        if account.status == BookkeeperAccount.STATUS_APPROVED:
            return _stale_approval_result(
                account,
                "This access request was already approved. The approval list has been refreshed.",
            )

        if account.status not in {BookkeeperAccount.STATUS_PENDING, BookkeeperAccount.STATUS_REJECTED}:
            return _stale_approval_result(
                account,
                "This account was updated by another admin and can no longer be approved from this request.",
            )

        proof = getattr(account, "verification_proof", None)
        if not account.email_verified or proof is None or proof_reviewed is not True or str(proof.revision) != str(proof_revision):
            return {
                "ok": False, "code": "proof_review_required", "refresh_required": True,
                "message": "View the current proof, then confirm your review before approving.",
            }

        account.status = BookkeeperAccount.STATUS_APPROVED
        account.approved_at = timezone.now()
        account.approved_by_admin = admin_account
        account.rejected_at = None
        account.rejection_reason = ""
        account.save(update_fields=[
            "status",
            "approved_at",
            "approved_by_admin",
            "rejected_at",
            "rejection_reason",
        ])
        audit_log = _create_approval_audit_log(
            admin_account,
            account,
            AdminAuditLog.ACTION_BOOKKEEPER_APPROVED,
            f"Approved bookkeeper access for {account.full_name}.",
        )
        audit_log.metadata.update({"proof_revision": str(proof.revision), "proof_sha256": proof.sha256})
        audit_log.save(update_fields=["metadata"])

    delivery = send_approval_decision_email(account, AdminAuditLog.ACTION_BOOKKEEPER_APPROVED)
    saved_delivery = save_delivery_outcome(audit_log, delivery)
    base_message = "Account approved. The bookkeeper can now access the workspace."
    return {
        "ok": True,
        "message": format_decision_result_message(base_message, saved_delivery),
        "email_delivery": saved_delivery,
        "approval": _serialize_approval(account, saved_delivery),
    }


def reject_bookkeeper(admin_account, bookkeeper_id: int, rejection_reason: str | None = None) -> dict:
    clean_reason = str(rejection_reason or "").strip()

    with transaction.atomic():
        account = (
            BookkeeperAccount.objects
            .select_for_update()
            .filter(id=bookkeeper_id)
            .first()
        )
        if account is None:
            return {
                "ok": False,
                "message": "Bookkeeper not found.",
            }

        if account.status != BookkeeperAccount.STATUS_PENDING:
            return _stale_approval_result(
                account,
                "This access request was already reviewed by another admin. The approval list has been refreshed.",
            )

        if not clean_reason:
            return {
                "ok": False,
                "message": "Rejection reason is required.",
            }

        account.status = BookkeeperAccount.STATUS_REJECTED
        account.rejected_at = timezone.now()
        account.rejection_reason = clean_reason
        account.approved_at = None
        account.approved_by_admin = None
        account.save(update_fields=[
            "status",
            "rejected_at",
            "rejection_reason",
            "approved_at",
            "approved_by_admin",
        ])
        audit_log = _create_approval_audit_log(
            admin_account,
            account,
            AdminAuditLog.ACTION_BOOKKEEPER_REJECTED,
            f"Rejected bookkeeper access for {account.full_name}.",
            clean_reason,
        )

    delivery = send_approval_decision_email(account, AdminAuditLog.ACTION_BOOKKEEPER_REJECTED)
    saved_delivery = save_delivery_outcome(audit_log, delivery)
    base_message = "Account rejected. The reason was saved for review history."
    return {
        "ok": True,
        "message": format_decision_result_message(base_message, saved_delivery),
        "email_delivery": saved_delivery,
        "approval": _serialize_approval(account, saved_delivery),
    }


def retry_approval_decision_email(admin_account, bookkeeper_id: int) -> dict:
    with transaction.atomic():
        account = BookkeeperAccount.objects.select_for_update().filter(id=bookkeeper_id).first()
        if account is None:
            return {"ok": False, "message": "Bookkeeper not found."}

        if account.status == BookkeeperAccount.STATUS_APPROVED:
            action_type = AdminAuditLog.ACTION_BOOKKEEPER_APPROVED
        elif account.status == BookkeeperAccount.STATUS_REJECTED:
            action_type = AdminAuditLog.ACTION_BOOKKEEPER_REJECTED
        else:
            return {
                "ok": False,
                "message": "Decision email retry is available only for approved or rejected accounts.",
            }

        audit_log = (
            AdminAuditLog.objects
            .select_for_update()
            .filter(
                target_model="BookkeeperAccount",
                target_id=account.id,
                action_type=action_type,
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if audit_log is None:
            return {"ok": False, "message": "No decision email record is available to retry."}

        previous_delivery = _email_delivery_from_log(audit_log)
        if previous_delivery.get("status") != DELIVERY_FAILED:
            return {"ok": False, "message": "Retry is available only after a failed decision email."}

    delivery = send_approval_decision_email(account, action_type)
    saved_delivery = save_delivery_outcome(audit_log, delivery, is_retry=True)
    if saved_delivery.get("status") == DELIVERY_FAILED:
        message = "Decision unchanged. Email retry failed. You can try again later."
    else:
        message = format_decision_result_message("Decision unchanged.", saved_delivery)

    return {
        "ok": True,
        "message": message,
        "email_delivery": saved_delivery,
        "approval": _serialize_approval(account, saved_delivery),
    }
