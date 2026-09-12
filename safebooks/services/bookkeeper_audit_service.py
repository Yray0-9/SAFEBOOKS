from django.db.models import Q

from safebooks.models import BookkeeperAuditLog


ACTION_LABELS = {
    BookkeeperAuditLog.ACTION_CLIENT_CREATED: "Added client",
    BookkeeperAuditLog.ACTION_CLIENT_UPDATED: "Updated client",
    BookkeeperAuditLog.ACTION_CLIENT_CLOSED: "Closed client",
    BookkeeperAuditLog.ACTION_RECORD_CREATED: "Added financial record",
    BookkeeperAuditLog.ACTION_RECORD_UPDATED: "Updated financial record",
    BookkeeperAuditLog.ACTION_RECORD_DELETED: "Deleted financial record",
    BookkeeperAuditLog.ACTION_PROFILE_UPDATED: "Updated profile",
    BookkeeperAuditLog.ACTION_PASSWORD_CHANGED: "Changed password",
    BookkeeperAuditLog.ACTION_LOGIN_ALERTS_CHANGED: "Changed login alerts",
    BookkeeperAuditLog.ACTION_CLIENT_DETAILS_LOCK_CHANGED: "Changed client details lock",
    BookkeeperAuditLog.ACTION_CLIENT_EMAILS_CHANGED: "Changed client record emails",
    BookkeeperAuditLog.ACTION_DEACTIVATION_REQUESTED: "Requested account deactivation",
    BookkeeperAuditLog.ACTION_TWO_FACTOR_ENABLED: "Enabled two-factor authentication",
    BookkeeperAuditLog.ACTION_TWO_FACTOR_DISABLED: "Disabled two-factor authentication",
}

ACTION_GROUPS = {
    "clients": {
        BookkeeperAuditLog.ACTION_CLIENT_CREATED,
        BookkeeperAuditLog.ACTION_CLIENT_UPDATED,
        BookkeeperAuditLog.ACTION_CLIENT_CLOSED,
    },
    "records": {
        BookkeeperAuditLog.ACTION_RECORD_CREATED,
        BookkeeperAuditLog.ACTION_RECORD_UPDATED,
        BookkeeperAuditLog.ACTION_RECORD_DELETED,
    },
    "account": {
        BookkeeperAuditLog.ACTION_PROFILE_UPDATED,
        BookkeeperAuditLog.ACTION_DEACTIVATION_REQUESTED,
    },
    "security": {
        BookkeeperAuditLog.ACTION_PASSWORD_CHANGED,
        BookkeeperAuditLog.ACTION_LOGIN_ALERTS_CHANGED,
        BookkeeperAuditLog.ACTION_CLIENT_DETAILS_LOCK_CHANGED,
        BookkeeperAuditLog.ACTION_CLIENT_EMAILS_CHANGED,
        BookkeeperAuditLog.ACTION_TWO_FACTOR_ENABLED,
        BookkeeperAuditLog.ACTION_TWO_FACTOR_DISABLED,
    },
}


def record_bookkeeper_audit(
    bookkeeper,
    action_type: str,
    message: str,
    *,
    target_model: str = "",
    target_id: int | None = None,
    metadata: dict | None = None,
) -> BookkeeperAuditLog:
    """Record a successful business action without storing secret field values."""
    safe_metadata = metadata if isinstance(metadata, dict) else {}
    return BookkeeperAuditLog.objects.create(
        bookkeeper=bookkeeper,
        action_type=action_type,
        target_model=str(target_model or "")[:80],
        target_id=target_id,
        message=str(message or "Activity recorded.")[:255],
        metadata=safe_metadata,
    )


def _normalize_value(value: str | None) -> str:
    return str(value or "").strip().lower()


def _apply_action_filter(queryset, action_filter: str):
    normalized = _normalize_value(action_filter)
    if not normalized or normalized == "all":
        return queryset
    if normalized in ACTION_GROUPS:
        return queryset.filter(action_type__in=ACTION_GROUPS[normalized])
    if normalized in ACTION_LABELS:
        return queryset.filter(action_type=normalized)
    return queryset


def _serialize_audit_log(log: BookkeeperAuditLog) -> dict:
    metadata = log.metadata if isinstance(log.metadata, dict) else {}
    return {
        "id": log.id,
        "action_type": log.action_type,
        "action_label": ACTION_LABELS.get(log.action_type, log.action_type.replace(".", " ").title()),
        "target_model": log.target_model,
        "target_id": log.target_id,
        "client_name": str(metadata.get("client_name") or "").strip(),
        "record_date": str(metadata.get("record_date") or "").strip(),
        "frequency": str(metadata.get("frequency") or "").strip(),
        "message": log.message,
        "created_at": log.created_at.isoformat() if log.created_at else "",
    }


def list_bookkeeper_audit_logs(bookkeeper, action: str | None, search: str | None, sort: str | None) -> dict:
    search_value = str(search or "").strip()
    sort_value = _normalize_value(sort) or "newest"
    owner_logs = BookkeeperAuditLog.objects.filter(bookkeeper=bookkeeper)
    queryset = _apply_action_filter(owner_logs, action or "")

    if search_value:
        queryset = queryset.filter(
            Q(message__icontains=search_value)
            | Q(action_type__icontains=search_value)
            | Q(target_model__icontains=search_value)
        )

    if sort_value == "oldest":
        queryset = queryset.order_by("created_at", "id")
    else:
        queryset = queryset.order_by("-created_at", "-id")

    logs = list(queryset[:500])
    return {
        "ok": True,
        "total_count": queryset.count(),
        "shown_count": len(logs),
        "counts": {
            "all": owner_logs.count(),
            "clients": owner_logs.filter(action_type__in=ACTION_GROUPS["clients"]).count(),
            "records": owner_logs.filter(action_type__in=ACTION_GROUPS["records"]).count(),
            "account": owner_logs.filter(action_type__in=ACTION_GROUPS["account"]).count(),
            "security": owner_logs.filter(action_type__in=ACTION_GROUPS["security"]).count(),
        },
        "logs": [_serialize_audit_log(log) for log in logs],
    }
