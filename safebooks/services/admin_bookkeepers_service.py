from django.contrib.auth.hashers import check_password, make_password
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.utils import timezone

from safebooks.models import AdminAuditLog, BookkeeperAccount, BookkeeperDeactivationRequest
from safebooks.services.session_security_service import save_account_security_change


STATUS_FILTER_MAP = {
    "approved": BookkeeperAccount.STATUS_APPROVED,
    "deactivated": BookkeeperAccount.STATUS_SUSPENDED,
    "rejected": BookkeeperAccount.STATUS_REJECTED,
    "inactive": BookkeeperAccount.STATUS_REJECTED,
}

SORT_OPTIONS = {"recent", "alpha", "clients"}
CLIENT_FILTERS = {"0-15", "16+"}
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50


def _normalize_value(value: str) -> str:
    return str(value or "").strip().lower()


def _normalize_positive_int(value, default: int, maximum: int | None = None) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return default
    if resolved < 1:
        return default
    return min(resolved, maximum) if maximum else resolved


def _looks_like_supported_hash(password_hash: str) -> bool:
    normalized_hash = str(password_hash or "")
    return normalized_hash.startswith("pbkdf2_") or normalized_hash.startswith("argon2")


def _verify_admin_password(admin_account, password: str) -> tuple[bool, str]:
    clean_password = str(password or "")
    if not clean_password:
        return False, "Admin password is required."

    stored_password_hash = str(getattr(admin_account, "password_hash", "") or "")
    if check_password(clean_password, stored_password_hash):
        return True, ""

    if stored_password_hash and not _looks_like_supported_hash(stored_password_hash):
        if clean_password == stored_password_hash:
            admin_account.password_hash = make_password(clean_password)
            admin_account.save(update_fields=["password_hash"])
            return True, ""

    return False, "Admin password is incorrect."


def _create_bookkeeper_audit_log(
    admin_account,
    account: BookkeeperAccount,
    action_type: str,
    message: str,
    client_count: int,
    decision_note: str = "",
) -> None:
    AdminAuditLog.objects.create(
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
            "client_count": client_count,
            "decision_note": str(decision_note or "").strip()[:255],
        },
    )


def _stale_bookkeeper_result(account: BookkeeperAccount, message: str) -> dict:
    return {
        "ok": False,
        "code": "stale_decision",
        "refresh_required": True,
        "message": message,
        "bookkeeper": _serialize_bookkeeper(account),
    }


def _serialize_bookkeeper(account: BookkeeperAccount, client_count: int | None = None) -> dict:
    resolved_count = client_count if client_count is not None else account.clients.count()
    pending_request = getattr(account, "pending_deactivation_request", None)
    if pending_request is None:
        pending_request = (
            account.deactivation_requests
            .filter(status=BookkeeperDeactivationRequest.STATUS_PENDING)
            .order_by("-requested_at", "-id")
            .first()
        )

    return {
        "id": account.id,
        "full_name": account.full_name,
        "email": account.email,
        "username": account.username,
        "status": account.status or BookkeeperAccount.STATUS_PENDING,
        "created_at": account.created_at.isoformat() if account.created_at else "",
        "last_login": account.last_login.isoformat() if account.last_login else "",
        "client_count": resolved_count,
        "deactivation_request": {
            "id": pending_request.id,
            "reason": pending_request.reason,
            "status": pending_request.status,
            "requested_at": pending_request.requested_at.isoformat() if pending_request.requested_at else "",
        } if pending_request else None,
    }


def list_admin_bookkeepers(
    admin_account,
    status: str | None,
    search: str | None,
    sort: str | None,
    clients: str | None,
    page=None,
    page_size=None,
) -> dict:
    status_value = _normalize_value(status)
    search_value = str(search or "").strip()
    sort_value = _normalize_value(sort) or "recent"
    clients_value = str(clients or "").strip()

    directory_queryset = BookkeeperAccount.objects.exclude(status=BookkeeperAccount.STATUS_PENDING)
    list_queryset = directory_queryset.annotate(client_count=Count("clients", distinct=True))

    if status_value in STATUS_FILTER_MAP:
        list_queryset = list_queryset.filter(status=STATUS_FILTER_MAP[status_value])

    if search_value:
        list_queryset = list_queryset.filter(
            Q(full_name__icontains=search_value)
            | Q(email__icontains=search_value)
            | Q(username__icontains=search_value)
        )

    if clients_value in CLIENT_FILTERS:
        if clients_value == "0-15":
            list_queryset = list_queryset.filter(client_count__lte=15)
        else:
            list_queryset = list_queryset.filter(client_count__gte=16)

    if sort_value == "alpha":
        list_queryset = list_queryset.order_by(Lower("full_name"), "id")
    elif sort_value == "clients":
        list_queryset = list_queryset.order_by("-client_count", Lower("full_name"), "id")
    else:
        list_queryset = list_queryset.order_by("-created_at", "-id")

    approved_count = directory_queryset.filter(status=BookkeeperAccount.STATUS_APPROVED).count()
    deactivated_count = directory_queryset.filter(status=BookkeeperAccount.STATUS_SUSPENDED).count()
    inactive_count = directory_queryset.filter(status=BookkeeperAccount.STATUS_REJECTED).count()
    total_count = approved_count + deactivated_count + inactive_count

    client_queryset = directory_queryset.annotate(client_count=Count("clients", distinct=True))
    client_zero_to_five = client_queryset.filter(client_count__lte=5).count()
    client_six_to_fifteen = client_queryset.filter(client_count__gte=6, client_count__lte=15).count()
    client_sixteen_plus = client_queryset.filter(client_count__gte=16).count()

    resolved_page_size = _normalize_positive_int(page_size, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    paginator = Paginator(list_queryset, resolved_page_size)
    page_obj = paginator.get_page(_normalize_positive_int(page, 1))

    bookkeepers = [
        _serialize_bookkeeper(account, getattr(account, "client_count", 0))
        for account in page_obj.object_list
    ]
    pending_deactivation_requests = BookkeeperDeactivationRequest.objects.filter(
        status=BookkeeperDeactivationRequest.STATUS_PENDING,
        bookkeeper__status=BookkeeperAccount.STATUS_APPROVED,
    ).count()

    return {
        "ok": True,
        "counts": {
            "total": total_count,
            "active": approved_count,
            "deactivated": deactivated_count,
            "rejected": inactive_count,
            "deactivation_requests": pending_deactivation_requests,
        },
        "client_summary": {
            "zero_to_five": client_zero_to_five,
            "six_to_fifteen": client_six_to_fifteen,
            "sixteen_plus": client_sixteen_plus,
        },
        "bookkeepers": bookkeepers,
        "pagination": {
            "page": page_obj.number,
            "page_size": resolved_page_size,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "start_index": page_obj.start_index() if paginator.count else 0,
            "end_index": page_obj.end_index() if paginator.count else 0,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
        },
    }


def deactivate_bookkeeper(admin_account, bookkeeper_id: int, admin_password: str | None = None, request_id: int | None = None) -> dict:
    with transaction.atomic():
        account = BookkeeperAccount.objects.select_for_update().filter(id=bookkeeper_id).first()
        if account is None:
            return {"ok": False, "message": "Bookkeeper not found."}

        password_ok, password_message = _verify_admin_password(admin_account, admin_password or "")
        if not password_ok:
            return {"ok": False, "message": password_message}

        client_count = account.clients.count()
        if account.status == BookkeeperAccount.STATUS_SUSPENDED:
            return _stale_bookkeeper_result(
                account,
                "This account was already deactivated by another admin. The bookkeeper list has been refreshed.",
            )

        if account.status != BookkeeperAccount.STATUS_APPROVED:
            return _stale_bookkeeper_result(
                account,
                "This account was updated by another admin and is no longer available for deactivation.",
            )

        deactivation_request = None
        if request_id:
            deactivation_request = (
                BookkeeperDeactivationRequest.objects
                .select_for_update()
                .filter(id=request_id, bookkeeper=account)
                .first()
            )
            if (
                deactivation_request is None
                or deactivation_request.status != BookkeeperDeactivationRequest.STATUS_PENDING
            ):
                return _stale_bookkeeper_result(
                    account,
                    "This deactivation request was already reviewed. The bookkeeper list has been refreshed.",
                )

        account.status = BookkeeperAccount.STATUS_SUSPENDED
        save_account_security_change(account, ["status"])
        if deactivation_request is not None:
            deactivation_request.status = BookkeeperDeactivationRequest.STATUS_APPROVED
            deactivation_request.reviewed_at = timezone.now()
            deactivation_request.reviewed_by_admin = admin_account
            deactivation_request.admin_note = "Approved by admin."
            deactivation_request.save(update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by_admin",
                "admin_note",
            ])
        _create_bookkeeper_audit_log(
            admin_account,
            account,
            AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATED,
            f"Deactivated bookkeeper account for {account.full_name}.",
            client_count,
            deactivation_request.reason if deactivation_request is not None else "",
        )

    return {
        "ok": True,
        "message": "Account deactivated. The bookkeeper cannot access the workspace until reactivated.",
        "bookkeeper": _serialize_bookkeeper(account, client_count),
    }


def decline_deactivation_request(admin_account, request_id: int, admin_password: str | None = None, admin_note: str | None = None) -> dict:
    bookkeeper_id = (
        BookkeeperDeactivationRequest.objects
        .filter(id=request_id)
        .values_list("bookkeeper_id", flat=True)
        .first()
    )
    if bookkeeper_id is None:
        return {"ok": False, "message": "Deactivation request not found."}
    clean_note = str(admin_note or "").strip()[:255] or "Declined by admin."

    with transaction.atomic():
        account = BookkeeperAccount.objects.select_for_update().filter(id=bookkeeper_id).first()
        if account is None:
            return {"ok": False, "message": "Bookkeeper not found."}

        request_obj = (
            BookkeeperDeactivationRequest.objects
            .select_for_update()
            .filter(id=request_id, bookkeeper=account)
            .first()
        )
        if request_obj is None:
            return _stale_bookkeeper_result(
                account,
                "This deactivation request is no longer available. The bookkeeper list has been refreshed.",
            )

        password_ok, password_message = _verify_admin_password(admin_account, admin_password or "")
        if not password_ok:
            return {"ok": False, "message": password_message}

        if request_obj.status != BookkeeperDeactivationRequest.STATUS_PENDING:
            return _stale_bookkeeper_result(
                account,
                "This deactivation request was already reviewed by another admin. The bookkeeper list has been refreshed.",
            )

        request_obj.status = BookkeeperDeactivationRequest.STATUS_REJECTED
        request_obj.reviewed_at = timezone.now()
        request_obj.reviewed_by_admin = admin_account
        request_obj.admin_note = clean_note
        request_obj.save(update_fields=[
            "status",
            "reviewed_at",
            "reviewed_by_admin",
            "admin_note",
        ])
        _create_bookkeeper_audit_log(
            admin_account,
            account,
            AdminAuditLog.ACTION_BOOKKEEPER_DEACTIVATION_DECLINED,
            f"Declined deactivation request for {account.full_name}.",
            account.clients.count(),
            clean_note,
        )

    return {
        "ok": True,
        "message": "Deactivation request declined. The bookkeeper account stays active.",
        "bookkeeper": _serialize_bookkeeper(account),
    }


def reactivate_bookkeeper(admin_account, bookkeeper_id: int, admin_password: str | None = None) -> dict:
    with transaction.atomic():
        account = BookkeeperAccount.objects.select_for_update().filter(id=bookkeeper_id).first()
        if account is None:
            return {"ok": False, "message": "Bookkeeper not found."}

        password_ok, password_message = _verify_admin_password(admin_account, admin_password or "")
        if not password_ok:
            return {"ok": False, "message": password_message}

        client_count = account.clients.count()
        if account.status == BookkeeperAccount.STATUS_APPROVED:
            return _stale_bookkeeper_result(
                account,
                "This account was already reactivated by another admin. The bookkeeper list has been refreshed.",
            )

        if account.status != BookkeeperAccount.STATUS_SUSPENDED:
            return _stale_bookkeeper_result(
                account,
                "This account was updated by another admin and can no longer be reactivated.",
            )

        account.status = BookkeeperAccount.STATUS_APPROVED
        save_account_security_change(account, ["status"])
        _create_bookkeeper_audit_log(
            admin_account,
            account,
            AdminAuditLog.ACTION_BOOKKEEPER_REACTIVATED,
            f"Reactivated bookkeeper account for {account.full_name}.",
            client_count,
        )

    return {
        "ok": True,
        "message": "Account reactivated. The bookkeeper can access the workspace again.",
        "bookkeeper": _serialize_bookkeeper(account, client_count),
    }


def delete_bookkeeper_account(admin_account, bookkeeper_id: int, admin_password: str | None = None) -> dict:
    with transaction.atomic():
        account = BookkeeperAccount.objects.select_for_update().filter(id=bookkeeper_id).first()
        if account is None:
            return {"ok": False, "message": "Bookkeeper not found."}

        password_ok, password_message = _verify_admin_password(admin_account, admin_password or "")
        if not password_ok:
            return {"ok": False, "message": password_message}

        client_count = account.clients.count()
        if client_count > 0:
            return {
                "ok": False,
                "message": "Permanent delete is blocked while this bookkeeper still owns clients. Deactivate the account instead.",
            }

        account_name = account.full_name
        account_email = account.email
        _create_bookkeeper_audit_log(
            admin_account,
            account,
            AdminAuditLog.ACTION_BOOKKEEPER_DELETED,
            f"Permanently deleted bookkeeper account for {account_name}.",
            client_count,
        )
        account.delete()

    return {
        "ok": True,
        "message": "Bookkeeper permanently deleted.",
        "bookkeeper_id": bookkeeper_id,
        "bookkeeper_email": account_email,
    }
