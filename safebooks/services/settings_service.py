from datetime import date

from safebooks.models import Client
from safebooks.models.workspace_defaults_model import WorkspaceDefaults
from safebooks.validators.data_validator import normalize_positive_id


DEFAULT_CLIENT_SCOPES = {
    WorkspaceDefaults.SCOPE_ALL,
    WorkspaceDefaults.SCOPE_LAST,
}
DEFAULT_REPORT_TYPES = {
    WorkspaceDefaults.REPORT_TYPE_FINANCIAL,
    WorkspaceDefaults.REPORT_TYPE_COMPLIANCE,
    WorkspaceDefaults.REPORT_TYPE_REMARKS,
}
DEFAULT_REPORT_RANGES = {
    WorkspaceDefaults.REPORT_RANGE_YTD,
    WorkspaceDefaults.REPORT_RANGE_30,
    WorkspaceDefaults.REPORT_RANGE_90,
    WorkspaceDefaults.REPORT_RANGE_CUSTOM,
}


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _serialize_defaults(defaults: WorkspaceDefaults) -> dict:
    return {
        "default_client_scope": defaults.default_client_scope,
        "default_report_type": defaults.default_report_type,
        "default_report_range": defaults.default_report_range,
        "default_report_range_from": defaults.default_report_range_from.isoformat()
        if defaults.default_report_range_from
        else "",
        "default_report_range_to": defaults.default_report_range_to.isoformat()
        if defaults.default_report_range_to
        else "",
        "last_client_id": defaults.last_client_id,
    }


def get_workspace_defaults_for_bookkeeper(bookkeeper) -> dict:
    defaults, _ = WorkspaceDefaults.objects.get_or_create(bookkeeper=bookkeeper)
    return {
        "ok": True,
        "defaults": _serialize_defaults(defaults),
    }


def _normalize_last_client_id(value):
    if value in (None, "", "all", "null"):
        return None, None

    return normalize_positive_id(value, label="Last used client")


def _normalize_optional_date(value, label: str):
    cleaned_value = _normalize_text(value)
    if not cleaned_value:
        return None, None

    try:
        return date.fromisoformat(cleaned_value), None
    except ValueError:
        return None, f"{label} must use YYYY-MM-DD format."


def update_workspace_defaults_for_bookkeeper(bookkeeper, data: dict) -> dict:
    if not isinstance(data, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    defaults, _ = WorkspaceDefaults.objects.get_or_create(bookkeeper=bookkeeper)

    errors: list[str] = []
    update_fields: list[str] = []

    if "default_client_scope" in data:
        scope = _normalize_text(data.get("default_client_scope")).lower()
        if scope not in DEFAULT_CLIENT_SCOPES:
            errors.append("Default client scope is invalid.")
        else:
            defaults.default_client_scope = scope
            update_fields.append("default_client_scope")

    if "default_report_type" in data:
        report_type = _normalize_text(data.get("default_report_type"))
        if report_type not in DEFAULT_REPORT_TYPES:
            errors.append("Default report type is invalid.")
        else:
            defaults.default_report_type = report_type
            update_fields.append("default_report_type")

    report_range_value = defaults.default_report_range
    if "default_report_range" in data:
        report_range = _normalize_text(data.get("default_report_range"))
        if report_range not in DEFAULT_REPORT_RANGES:
            errors.append("Default report date range is invalid.")
        else:
            report_range_value = report_range
            defaults.default_report_range = report_range
            update_fields.append("default_report_range")

    range_from_value = defaults.default_report_range_from
    if "default_report_range_from" in data:
        range_from_value, range_from_error = _normalize_optional_date(
            data.get("default_report_range_from"),
            "Custom range start",
        )
        if range_from_error:
            errors.append(range_from_error)
        else:
            defaults.default_report_range_from = range_from_value
            update_fields.append("default_report_range_from")

    range_to_value = defaults.default_report_range_to
    if "default_report_range_to" in data:
        range_to_value, range_to_error = _normalize_optional_date(
            data.get("default_report_range_to"),
            "Custom range end",
        )
        if range_to_error:
            errors.append(range_to_error)
        else:
            defaults.default_report_range_to = range_to_value
            update_fields.append("default_report_range_to")

    if "last_client_id" in data:
        last_client_id, last_client_error = _normalize_last_client_id(data.get("last_client_id"))
        if last_client_error:
            errors.append(last_client_error)
        else:
            if last_client_id is None:
                defaults.last_client = None
                update_fields.append("last_client")
            else:
                client = Client.objects.filter(id=last_client_id, bookkeeper=bookkeeper).first()
                if client is None:
                    errors.append("Last used client was not found.")
                else:
                    defaults.last_client = client
                    update_fields.append("last_client")

    if report_range_value == WorkspaceDefaults.REPORT_RANGE_CUSTOM:
        if not range_from_value or not range_to_value:
            errors.append("Custom range requires both start and end dates.")
        elif range_from_value > range_to_value:
            errors.append("Custom range start must be on or before the end date.")

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
        }

    if update_fields:
        update_fields.append("updated_at")
        defaults.save(update_fields=update_fields)

    return {
        "ok": True,
        "message": "Workspace defaults updated.",
        "defaults": _serialize_defaults(defaults),
    }


def _normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None

    cleaned = str(value).strip().lower()
    if cleaned in {"true", "1", "yes", "on"}:
        return True
    if cleaned in {"false", "0", "no", "off"}:
        return False
    return None


def update_client_record_email_notifications_preference(bookkeeper, data: dict) -> dict:
    if not isinstance(data, dict):
        return {
            "ok": False,
            "message": "Invalid request payload.",
            "errors": ["Invalid request payload."],
        }

    enabled_value = _normalize_bool(data.get("enabled"))
    if enabled_value is None:
        return {
            "ok": False,
            "message": "Client email notification setting is required.",
            "errors": ["Client email notification setting is required."],
        }

    bookkeeper.client_record_email_notifications_enabled = enabled_value
    bookkeeper.save(update_fields=["client_record_email_notifications_enabled"])

    return {
        "ok": True,
        "message": "Client email notification preference updated.",
        "client_record_email_notifications_enabled": enabled_value,
    }
