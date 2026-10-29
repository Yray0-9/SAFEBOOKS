from datetime import date
from decimal import Decimal
from functools import wraps

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Max, Q
from django.utils import timezone

from safebooks.models import Client
from safebooks.validators.data_validator import model_text_errors, normalize_nonnegative_decimal, parse_finite_decimal, text_value_error, valid_formatted_tin


REMARKS_SET = {Client.REMARK_NEW, Client.REMARK_ACTIVE, Client.REMARK_SEPARATED, Client.REMARK_CLOSED}


def _client_write(operation):
    @wraps(operation)
    def wrapped(bookkeeper, *args, **kwargs):
        try:
            with transaction.atomic():
                return operation(bookkeeper, *args, **kwargs)
        except IntegrityError:
            # Check only after the failed savepoint has rolled back. Never expose DB details.
            data = kwargs.get("data") or next((value for value in args if isinstance(value, dict)), {})
            tin = _normalize_digits(data.get("tin_number") or data.get("tin"))
            message = "TIN already exists." if tin and Client.objects.filter(tin_number__iexact=tin).exists() else "Unable to save the client. Refresh and try again."
            return {"ok": False, "message": message, "errors": [message]}
    return wrapped


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _normalize_digits(value) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def _normalize_optional_date(value):
    cleaned_value = _normalize_text(value)
    if not cleaned_value:
        return None, None

    try:
        return date.fromisoformat(cleaned_value), None
    except ValueError:
        return None, "Birthday must use YYYY-MM-DD format."


def _normalize_forecast_growth_percent(value):
    return normalize_nonnegative_decimal(value, label="Forecast growth percent", maximum=Decimal("100"), optional=True)


def _normalize_remarks(value) -> str:
    cleaned_value = _normalize_text(value).lower()
    if cleaned_value in REMARKS_SET:
        return cleaned_value
    return Client.REMARK_NEW


def _normalize_custom_fields(value):
    if value is None:
        return None, None

    if not isinstance(value, list):
        return None, "Custom fields must be a list."

    allowed_types = {"text", "email", "password", "number", "date", "tin"}
    cleaned_fields = []
    for item in value:
        if not isinstance(item, dict):
            return None, "Each custom field must be an object."

        for key in ("label", "value", "type"):
            error = text_value_error(item.get(key), f"Custom field {key}")
            if error:
                return None, error

        label = _normalize_text(item.get("label"))
        field_value = str(item.get("value") if item.get("value") is not None else "").strip()
        field_type = _normalize_text(item.get("type")).lower()
        if field_type not in allowed_types:
            field_type = "text"

        if not label and not field_value:
            continue

        if field_type == "number" and field_value:
            _, error = parse_finite_decimal(item.get("value"), label="Custom field number")
            if error:
                return None, error
        if field_type == "email" and field_value:
            try:
                validate_email(field_value)
            except ValidationError:
                return None, "Custom field email format is invalid."
        if field_type == "date" and field_value:
            try:
                date.fromisoformat(field_value)
            except ValueError:
                return None, "Custom field date must use YYYY-MM-DD format."

        if field_type == "tin" and field_value:
            if not valid_formatted_tin(field_value):
                return None, "Custom field TIN must be 12 digits."

        cleaned_fields.append({
            "label": label or "Custom Field",
            "value": field_value,
            "type": field_type,
        })

    return cleaned_fields, None


def serialize_client(client: Client, *, include_sensitive: bool = False) -> dict:
    """Default to directory-safe data; full profiles require view authorization."""
    latest_record_updated_at = getattr(client, "latest_record_updated_at", None)
    activity_candidates = [
        value
        for value in (
            latest_record_updated_at,
            client.updated_at,
            client.created_at,
        )
        if value
    ]
    recent_activity_at = max(activity_candidates) if activity_candidates else None

    return {
        "id": client.id,
        "client_name": client.client_name,
        "tin_number": client.tin_number,
        "trade_name": client.trade_name,
        "tax_registration": client.tax_registration,
        "location": client.location,
        "permit_number": client.permit_number if include_sensitive else "",
        "birthday": client.birthday.isoformat() if include_sensitive and client.birthday else "",
        "email": client.email if include_sensitive else "",
        "email_password": client.email_password if include_sensitive else "",
        "orus_account": client.orus_account if include_sensitive else "",
        "orus_password": client.orus_password if include_sensitive else "",
        "custom_fields": (client.custom_fields or []) if include_sensitive else [],
        "forecast_growth_percent": float((client.forecast_growth_percent or Decimal("0.00")).quantize(Decimal("0.01"))),
        "remarks": resolve_client_remarks(client),
        "closure_reason": client.closure_reason or "",
        "closure_notes": client.closure_notes or "",
        "closed_at": client.closed_at.isoformat() if client.closed_at else "",
        "date_registered": client.date_registered.isoformat() if client.date_registered else "",
        "created_at": client.created_at.isoformat() if client.created_at else "",
        "updated_at": client.updated_at.isoformat() if client.updated_at else "",
        "latest_record_updated_at": latest_record_updated_at.isoformat() if latest_record_updated_at else "",
        "recent_activity_at": recent_activity_at.isoformat() if recent_activity_at else "",
    }


def _build_clean_payload(data: dict):
    client_name = _normalize_text(data.get("client_name"))
    tin_number = _normalize_text(data.get("tin_number") or data.get("tin"))
    tin_digits = _normalize_digits(tin_number)
    if tin_digits:
        tin_number = tin_digits
    trade_name = _normalize_text(data.get("trade_name"))
    location = _normalize_text(data.get("location"))
    permit_number = _normalize_text(data.get("permit_number"))
    email = _normalize_text(data.get("email"))
    email_password = _normalize_text(data.get("email_password"))
    orus_account = _normalize_text(data.get("orus_account"))
    orus_password = _normalize_text(data.get("orus_password"))

    birthday_value, birthday_error = _normalize_optional_date(data.get("birthday"))
    forecast_growth_percent, growth_error = _normalize_forecast_growth_percent(data.get("forecast_growth_percent"))
    custom_fields, custom_fields_error = _normalize_custom_fields(data.get("custom_fields"))

    errors = []
    tax_registration = data.get("tax_registration", "")
    if not isinstance(tax_registration, str) or tax_registration not in {value for value, _ in Client.TAX_REGISTRATION_CHOICES}:
        errors.append("Tax registration must be VAT, Non-VAT, or Not set.")
    if not client_name:
        errors.append("Client name is required.")
    if not tin_number:
        errors.append("TIN is required.")
    elif not valid_formatted_tin(data.get("tin_number") or data.get("tin")):
        errors.append("TIN must be 12 digits.")
    if not location:
        errors.append("Location is required.")

    errors.extend(model_text_errors(Client, data))

    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Email format is invalid.")

    if birthday_error:
        errors.append(birthday_error)
    if growth_error:
        errors.append(growth_error)
    if custom_fields_error:
        errors.append(custom_fields_error)

    raw_remarks = data.get("remarks")
    has_remarks = raw_remarks is not None and str(raw_remarks).strip() != ""
    remarks = _normalize_remarks(raw_remarks) if has_remarks else Client.REMARK_NEW

    return {
        "client_name": client_name,
        "tin_number": tin_number,
        "trade_name": trade_name,
        "tax_registration": tax_registration,
        "location": location,
        "permit_number": permit_number,
        "birthday": birthday_value,
        "email": email,
        "email_password": email_password,
        "orus_account": orus_account,
        "orus_password": orus_password,
        "custom_fields": custom_fields,
        "forecast_growth_percent": forecast_growth_percent,
        "remarks": remarks,
        "has_remarks": has_remarks,
    }, errors


def with_status_activity(queryset, *, today=None):
    today = today or timezone.localdate()
    recorded = Q(financial_records__bookkeeper_id=F("bookkeeper_id"), financial_records__entry_date__lte=today)
    return queryset.annotate(
        status_last_entry=Max("financial_records__entry_date", filter=recorded),
        status_recorded_periods=Count("financial_records__period", filter=recorded, distinct=True),
    )


def resolve_client_remarks(client, *, today=None):
    """Read-only status: closed wins, then 12-month inactivity, then two recorded periods.

    Empty/future periods do not prove filing. Where no automatic threshold applies,
    retain the existing manual remark rather than silently redefining that setting.
    """
    if client.remarks == Client.REMARK_CLOSED:
        return Client.REMARK_CLOSED
    today = today or timezone.localdate()
    if hasattr(client, "status_last_entry") and hasattr(client, "status_recorded_periods"):
        last_entry = client.status_last_entry
        recorded_periods = client.status_recorded_periods
    else:
        activity = client.financial_records.filter(bookkeeper_id=client.bookkeeper_id, entry_date__lte=today).aggregate(
            last_entry=Max("entry_date"), recorded_periods=Count("period", distinct=True),
        )
        last_entry = activity["last_entry"]
        recorded_periods = activity["recorded_periods"]
    reference_date = last_entry or client.date_registered or today
    months_inactive = (today.year - reference_date.year) * 12 + today.month - reference_date.month
    if months_inactive >= 12:
        return Client.REMARK_SEPARATED
    if recorded_periods >= 2:
        return Client.REMARK_ACTIVE
    return client.remarks if client.remarks in REMARKS_SET else Client.REMARK_NEW


def check_and_promote_new_client(client) -> bool:
    """Persist only from an owned, locked client write or its financial transaction."""
    resolved = resolve_client_remarks(client)
    if resolved != client.remarks:
        client.remarks = resolved
        client.save(update_fields=["remarks"])
        return True
    return False


def list_clients_for_bookkeeper(bookkeeper) -> dict:
    clients = (
        with_status_activity(Client.objects.filter(bookkeeper=bookkeeper))
        .defer("email_password", "orus_password", "custom_fields")
        .annotate(latest_record_updated_at=Max("financial_records__updated_at"))
        .order_by("client_name", "id")
    )
    return {
        "ok": True,
        "clients": [serialize_client(client) for client in clients],
    }


def get_client_for_bookkeeper(bookkeeper, client_id: int) -> dict:
    client = Client.objects.filter(id=client_id, bookkeeper=bookkeeper).first()
    if client is None:
        return {"ok": False, "message": "Client not found.", "errors": ["Client not found."]}
    return {"ok": True, "client": serialize_client(client, include_sensitive=True)}


@_client_write
def create_client_for_bookkeeper(bookkeeper, data: dict) -> dict:
    payload, errors = _build_clean_payload(data)

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
        }

    if Client.objects.filter(tin_number__iexact=payload["tin_number"]).exists():
        return {
            "ok": False,
            "message": "TIN already exists.",
            "errors": ["TIN already exists."],
        }

    client = Client.objects.create(
        bookkeeper=bookkeeper,
        client_name=payload["client_name"],
        tin_number=payload["tin_number"],
        trade_name=payload["trade_name"],
        tax_registration=payload["tax_registration"],
        location=payload["location"],
        permit_number=payload["permit_number"],
        birthday=payload["birthday"],
        email=payload["email"],
        email_password=payload["email_password"],
        orus_account=payload["orus_account"],
        orus_password=payload["orus_password"],
        custom_fields=payload["custom_fields"] or [],
        forecast_growth_percent=payload["forecast_growth_percent"],
        remarks=payload["remarks"] if payload["has_remarks"] else Client.REMARK_NEW,
    )

    return {
        "ok": True,
        "message": "Client added successfully.",
        "client": serialize_client(client),
    }


@_client_write
def update_client_for_bookkeeper(bookkeeper, client_id: int, data: dict, *, include_sensitive: bool = False) -> dict:
    client = Client.objects.select_for_update().filter(id=client_id, bookkeeper=bookkeeper).first()
    if client is None:
        return {
            "ok": False,
            "message": "Client not found.",
            "errors": ["Client not found."],
        }

    payload, errors = _build_clean_payload(data)

    if errors:
        return {
            "ok": False,
            "message": errors[0],
            "errors": errors,
        }

    if Client.objects.filter(tin_number__iexact=payload["tin_number"]).exclude(id=client.id).exists():
        return {
            "ok": False,
            "message": "TIN already exists.",
            "errors": ["TIN already exists."],
        }

    client.client_name = payload["client_name"]
    client.tin_number = payload["tin_number"]
    client.trade_name = payload["trade_name"]
    client.location = payload["location"]
    client.permit_number = payload["permit_number"]
    client.birthday = payload["birthday"]
    client.email = payload["email"]
    # An omitted credential means keep the saved value; an explicit empty string
    # still lets an authorized full-profile form clear it deliberately.
    if "email_password" in data:
        client.email_password = payload["email_password"]
    if "orus_account" in data:
        client.orus_account = payload["orus_account"]
    if "orus_password" in data:
        client.orus_password = payload["orus_password"]
    client.forecast_growth_percent = payload["forecast_growth_percent"]
    
    update_fields = [
        "client_name",
        "tin_number",
        "trade_name",
        "location",
        "permit_number",
        "birthday",
        "email",
        "email_password",
        "orus_account",
        "orus_password",
        "forecast_growth_percent",
        "updated_at",
    ]

    if "tax_registration" in data:
        client.tax_registration = payload["tax_registration"]
        update_fields.append("tax_registration")

    if payload["has_remarks"]:
        if client.remarks == Client.REMARK_CLOSED and payload["remarks"] != Client.REMARK_CLOSED:
            client.remarks = Client.REMARK_NEW
        else:
            client.remarks = payload["remarks"]
        update_fields.append("remarks")

    if payload["custom_fields"] is not None:
        client.custom_fields = payload["custom_fields"]
        update_fields.append("custom_fields")

    client.save(update_fields=update_fields)
    check_and_promote_new_client(client)

    return {
        "ok": True,
        "message": "Client updated successfully.",
        "client": serialize_client(client, include_sensitive=include_sensitive),
    }


@_client_write
def delete_client_for_bookkeeper(bookkeeper, client_id: int, reason: str = "", notes: str = "") -> dict:
    client = Client.objects.select_for_update().filter(id=client_id, bookkeeper=bookkeeper).first()
    if client is None:
        return {
            "ok": False,
            "message": "Client not found.",
            "errors": ["Client not found."],
        }

    clean_reason = _normalize_text(reason) or "Closed by bookkeeper"
    clean_notes = _normalize_text(notes)
    errors = model_text_errors(Client, {"closure_reason": reason, "closure_notes": notes})
    if errors:
        return {"ok": False, "message": errors[0], "errors": errors}

    client.remarks = Client.REMARK_CLOSED
    client.closure_reason = clean_reason
    client.closure_notes = clean_notes
    client.closed_at = timezone.now()
    client.save(update_fields=["remarks", "closure_reason", "closure_notes", "closed_at", "updated_at"])

    return {
        "ok": True,
        "message": "Client closed successfully.",
        "client": serialize_client(client),
    }


@_client_write
def reopen_client_for_bookkeeper(bookkeeper, client_id: int) -> dict:
    client = Client.objects.select_for_update().filter(id=client_id, bookkeeper=bookkeeper).first()
    if client is None:
        return {
            "ok": False,
            "message": "Client not found.",
            "errors": ["Client not found."],
        }

    client.remarks = Client.REMARK_NEW
    client.closure_reason = ""
    client.closure_notes = ""
    client.closed_at = None
    client.save(update_fields=["remarks", "closure_reason", "closure_notes", "closed_at", "updated_at"])
    check_and_promote_new_client(client)

    return {
        "ok": True,
        "message": "Client reopened successfully.",
        "client": serialize_client(client),
    }
