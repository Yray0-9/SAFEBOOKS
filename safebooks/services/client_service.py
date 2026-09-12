from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Max
from django.utils import timezone

from safebooks.models import Client


REMARKS_SET = {Client.REMARK_NEW, Client.REMARK_ACTIVE, Client.REMARK_SEPARATED, Client.REMARK_CLOSED}


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
    cleaned_value = _normalize_text(value)
    if not cleaned_value:
        return Decimal("0.00"), None

    try:
        percent = Decimal(cleaned_value)
    except (InvalidOperation, TypeError):
        return None, "Forecast growth percent must be a valid number."

    if percent < 0:
        return None, "Forecast growth percent cannot be negative."
    if percent > Decimal("100.00"):
        return None, "Forecast growth percent must be 100 or less."

    return percent.quantize(Decimal("0.01")), None


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
            continue

        label = _normalize_text(item.get("label"))
        field_value = _normalize_text(item.get("value"))
        field_type = _normalize_text(item.get("type")).lower()
        if field_type not in allowed_types:
            field_type = "text"

        if not label and not field_value:
            continue

        if field_type == "tin" and field_value:
            tin_digits = _normalize_digits(field_value)
            if len(tin_digits) != 12:
                return None, "Custom field TIN must be 12 digits."

        cleaned_fields.append({
            "label": label or "Custom Field",
            "value": field_value,
            "type": field_type,
        })

    return cleaned_fields, None


def _serialize_client(client: Client) -> dict:
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
        "location": client.location,
        "permit_number": client.permit_number,
        "birthday": client.birthday.isoformat() if client.birthday else "",
        "email": client.email,
        "email_password": client.email_password,
        "orus_account": client.orus_account,
        "orus_password": client.orus_password,
        "custom_fields": client.custom_fields or [],
        "forecast_growth_percent": float((client.forecast_growth_percent or Decimal("0.00")).quantize(Decimal("0.01"))),
        "remarks": client.remarks,
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
    if not client_name:
        errors.append("Client name is required.")
    if not tin_number:
        errors.append("TIN is required.")
    elif len(_normalize_digits(tin_number)) != 12:
        errors.append("TIN must be 12 digits.")
    if not location:
        errors.append("Location is required.")

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


def check_and_promote_new_client(client) -> bool:
    """
    Dynamically evaluate and update the client's remarks based on their filing history:
    1. If the client is 'closed', we preserve their closed state.
    2. A client becomes 'active' if they have filed in at least two consecutive months
       OR they have filing periods in 3 or more total months.
    3. A client becomes 'separated' if they have not filed any compliance in one whole year (12 months).
    4. Otherwise, they retain their remarks or default to 'new'.
    """
    if client.remarks == Client.REMARK_CLOSED:
        return False

    periods = list(client.periods.all().order_by("year", "month"))
    
    # Check for Active promotion conditions: at least two distinct periods of filing
    should_be_active = len(periods) >= 2

    # Check for Separated condition (no filings in 12 months)
    today = date.today()
    if periods:
        last_period = periods[-1]
        months_since_last = (today.year - last_period.year) * 12 + (today.month - last_period.month)
    else:
        reg_date = client.date_registered or today
        months_since_last = (today.year - reg_date.year) * 12 + (today.month - reg_date.month)

    should_be_separated = months_since_last >= 12

    original_remarks = client.remarks

    if should_be_active:
        client.remarks = Client.REMARK_ACTIVE
    elif should_be_separated:
        client.remarks = Client.REMARK_SEPARATED
    else:
        if client.remarks not in {Client.REMARK_NEW, Client.REMARK_ACTIVE, Client.REMARK_SEPARATED}:
            client.remarks = Client.REMARK_NEW

    if client.remarks != original_remarks:
        client.save(update_fields=["remarks"])
        return True

    return False


def list_clients_for_bookkeeper(bookkeeper) -> dict:
    clients = (
        Client.objects
        .filter(bookkeeper=bookkeeper)
        .annotate(latest_record_updated_at=Max("financial_records__updated_at"))
        .order_by("client_name", "id")
    )
    for client in clients:
        check_and_promote_new_client(client)
    return {
        "ok": True,
        "clients": [_serialize_client(client) for client in clients],
    }


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
        "client": _serialize_client(client),
    }


def update_client_for_bookkeeper(bookkeeper, client_id: int, data: dict) -> dict:
    client = Client.objects.filter(id=client_id, bookkeeper=bookkeeper).first()
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
    client.email_password = payload["email_password"]
    client.orus_account = payload["orus_account"]
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

    if payload["has_remarks"]:
        if client.remarks == Client.REMARK_CLOSED and payload["remarks"] != Client.REMARK_CLOSED:
            client.remarks = Client.REMARK_NEW
            check_and_promote_new_client(client)
        else:
            client.remarks = payload["remarks"]
        update_fields.append("remarks")

    if payload["custom_fields"] is not None:
        client.custom_fields = payload["custom_fields"]
        update_fields.append("custom_fields")

    client.save(update_fields=update_fields)

    return {
        "ok": True,
        "message": "Client updated successfully.",
        "client": _serialize_client(client),
    }


def delete_client_for_bookkeeper(bookkeeper, client_id: int, reason: str = "", notes: str = "") -> dict:
    client = Client.objects.filter(id=client_id, bookkeeper=bookkeeper).first()
    if client is None:
        return {
            "ok": False,
            "message": "Client not found.",
            "errors": ["Client not found."],
        }

    clean_reason = _normalize_text(reason) or "Closed by bookkeeper"
    clean_notes = _normalize_text(notes)

    client.remarks = Client.REMARK_CLOSED
    client.closure_reason = clean_reason
    client.closure_notes = clean_notes
    client.closed_at = timezone.now()
    client.save(update_fields=["remarks", "closure_reason", "closure_notes", "closed_at", "updated_at"])

    return {
        "ok": True,
        "message": "Client closed successfully.",
        "client": _serialize_client(client),
    }


def reopen_client_for_bookkeeper(bookkeeper, client_id: int) -> dict:
    client = Client.objects.filter(id=client_id, bookkeeper=bookkeeper).first()
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
        "client": _serialize_client(client),
    }
