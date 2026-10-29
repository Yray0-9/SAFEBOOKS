import logging
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps

from django.db import DatabaseError, OperationalError, transaction
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.utils import timezone

from safebooks.models import BookkeeperAuditLog, Client, FinancialRecord, FinancialRecordLine, Period
from safebooks.services.bookkeeper_audit_service import record_bookkeeper_audit
from safebooks.services.client_service import serialize_client
from safebooks.services.workload_limits import (
    MAX_RECORDS, MAX_TRANSACTION_DETAILS, WorkloadLimitExceeded, bounded_list, workload_error,
)
from safebooks.validators.data_validator import decimal_field_max, model_text_errors, normalize_nonnegative_decimal


MONTH_NUMBER_TO_NAME = dict(Period.MONTH_CHOICES)
MONTH_NAME_TO_NUMBER = {label.lower(): number for number, label in Period.MONTH_CHOICES}
ALLOWED_FREQUENCIES = {
    FinancialRecord.FREQUENCY_MONTHLY,
    FinancialRecord.FREQUENCY_QUARTERLY,
    FinancialRecord.FREQUENCY_ANNUALLY,
}
logger = logging.getLogger(__name__)
MAX_MONEY_AMOUNT = decimal_field_max(FinancialRecord, "total_amount")


def _write_error(code, message):
    return {"ok": False, "code": code, "message": message, "errors": [message]}


def _financial_write(operation):
    """Commit financial state and its audit together; safely report DB failures."""
    @wraps(operation)
    def wrapped(*args, **kwargs):
        try:
            with transaction.atomic():
                return operation(*args, **kwargs)
        except DatabaseError as error:
            cause = error.__cause__
            sqlstate = getattr(cause, "sqlstate", None)
            if sqlstate in {"40001", "40P01", "55P03"} or (
                isinstance(error, OperationalError) and "locked" in str(error).lower()
            ):
                return _write_error("write_conflict", "Another operation is using these records. Reload and try again.")
            # Never log SQL, request bodies, credentials, or database exception text.
            logger.error("Financial operation could not be completed (%s).", type(error).__name__)
            # A connection failure while acknowledging COMMIT can have an unknown outcome.
            return _write_error("persistence_failed", "Unable to confirm this change. Refresh the records before trying again.")
    return wrapped


def _check_revision(record, expected_revision):
    if not isinstance(expected_revision, str) or not expected_revision:
        return _write_error("revision_required", "Refresh the records before editing or deleting this entry.")
    if expected_revision != record.updated_at.isoformat():
        return _write_error("stale_record", "This entry changed in another tab. Your draft is unchanged. Close it, reload the records, and review the latest entry.")
    return None


def _audit_record(bookkeeper, client, record, action):
    record_date = record.entry_date.isoformat()
    frequency = record.frequency or FinancialRecord.FREQUENCY_MONTHLY
    verb = {
        BookkeeperAuditLog.ACTION_RECORD_CREATED: "Added",
        BookkeeperAuditLog.ACTION_RECORD_UPDATED: "Updated",
        BookkeeperAuditLog.ACTION_RECORD_DELETED: "Deleted",
    }[action]
    record_bookkeeper_audit(
        bookkeeper, action,
        f"{verb} a financial record for {client.client_name} dated {record_date}.",
        target_model="FinancialRecord", target_id=record.id,
        metadata={"client_name": client.client_name, "client_id": client.id,
                  "record_date": record_date, "frequency": frequency},
    )


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _normalize_month(value):
    if isinstance(value, bool):
        return None, "Invalid period month."
    if value is not None and not isinstance(value, (str, int)):
        return None, "Invalid period month."
    if value in (None, ""):
        return date.today().month, None

    if isinstance(value, int):
        month = value
    else:
        cleaned_value = _normalize_text(value)
        if not cleaned_value:
            return date.today().month, None

        if cleaned_value.isascii() and cleaned_value.isdigit() and len(cleaned_value) <= 8:
            month = int(cleaned_value)
        else:
            month = MONTH_NAME_TO_NUMBER.get(cleaned_value.lower())

    if month not in MONTH_NUMBER_TO_NAME:
        return None, "Invalid period month."

    return month, None


def _normalize_year(value):
    if value in (None, ""):
        return date.today().year, None

    cleaned_value = _normalize_text(value)
    if not cleaned_value.isascii() or not cleaned_value.isdigit() or len(cleaned_value) > 4:
        return None, "Invalid period year."

    year = int(cleaned_value)
    if year < 2000 or year > 2100:
        return None, "Period year must be between 2000 and 2100."

    return year, None


def _normalize_entry_date(value):
    cleaned_value = _normalize_text(value)
    if not cleaned_value:
        return None, "Entry date is required."

    try:
        entry_date = date.fromisoformat(cleaned_value)
    except ValueError:
        return None, "Entry date must use YYYY-MM-DD format."

    if entry_date.year < 2000 or entry_date.year > 2100:
        return None, "Entry date year must be between 2000 and 2100."

    return entry_date, None


def _normalize_frequency(value):
    cleaned_value = _normalize_text(value).lower()
    if not cleaned_value:
        return FinancialRecord.FREQUENCY_MONTHLY, None

    if cleaned_value not in ALLOWED_FREQUENCIES:
        return None, "Frequency must be Monthly, Quarterly, or Annually."

    return cleaned_value, None


def _normalize_required_date(value, label: str):
    cleaned_value = _normalize_text(value)
    if not cleaned_value:
        return None, f"{label} is required."

    try:
        parsed_date = date.fromisoformat(cleaned_value)
    except ValueError:
        return None, f"{label} must use YYYY-MM-DD format."

    if parsed_date.year < 2000 or parsed_date.year > 2100:
        return None, f"{label} year must be between 2000 and 2100."

    return parsed_date, None


def _normalize_optional_date(value, label: str):
    cleaned_value = _normalize_text(value)
    if not cleaned_value:
        return None, None

    try:
        parsed_date = date.fromisoformat(cleaned_value)
    except ValueError:
        return None, f"{label} must use YYYY-MM-DD format."

    if parsed_date.year < 2000 or parsed_date.year > 2100:
        return None, f"{label} year must be between 2000 and 2100."

    return parsed_date, None


def _normalize_amount(value):
    return normalize_nonnegative_decimal(value, label="Amount", maximum=MAX_MONEY_AMOUNT, raw_maximum=False)


def _normalize_line_items(line_items):
    if not isinstance(line_items, list) or not line_items:
        return [], ["At least one record detail is required."]
    if len(line_items) > MAX_TRANSACTION_DETAILS:
        return [], ["An entry exceeds 20,000 transaction details. Split it into smaller entries; nothing was saved."]

    cleaned_line_items = []
    errors = []

    for index, line_item in enumerate(line_items, start=1):
        if not isinstance(line_item, dict):
            errors.append(f"Record detail #{index} is invalid.")
            continue

        type_code = _normalize_text(line_item.get("type_code"))
        detail_label = {"sales": "Sales", "expenses": "Expenses"}.get(type_code.lower(), f"Record detail #{index}")
        description = _normalize_text(line_item.get("description"))
        remarks = None if line_item.get("remarks") is None else _normalize_text(line_item["remarks"])
        coverage_frequency = line_item.get("coverage_frequency")
        if coverage_frequency is not None and (
            not isinstance(coverage_frequency, str) or coverage_frequency not in ALLOWED_FREQUENCIES
        ):
            errors.append(f"{detail_label}: Choose a valid covered period.")
        if coverage_frequency is not None and type_code.lower() not in {"sales", "expenses"}:
            errors.append(f"{detail_label}: Separate coverage is available for Sales and Expenses only.")
        if line_item.get("remarks") is not None and not isinstance(line_item["remarks"], str):
            errors.append(f"{detail_label}: Remarks must be text.")
        amount, amount_error = _normalize_amount(line_item.get("amount"))
        worksheet_amounts = {}
        for field_name, label in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS.items():
            value = line_item.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                worksheet_amounts[field_name] = None
                continue
            worksheet_amount, worksheet_error = normalize_nonnegative_decimal(
                value, label=label, maximum=decimal_field_max(FinancialRecordLine, field_name), raw_maximum=False,
            )
            worksheet_amounts[field_name] = worksheet_amount
            if worksheet_error:
                errors.append(f"{detail_label}: {worksheet_error}")
        client_line_id = _normalize_text(line_item.get("client_line_id") or line_item.get("line_id"))
        for text_error in model_text_errors(FinancialRecordLine, line_item, labels={"type_code": "Type/code"}):
            errors.append(f"{detail_label}: {text_error}")

        if not type_code:
            errors.append(f"{detail_label} type/code is required.")
        if not description:
            errors.append(f"{detail_label} description is required.")
        if amount_error:
            errors.append(f"{detail_label}: {amount_error}")
        if type_code and description and amount is not None:
            cleaned_line_items.append(
                {
                    "client_line_id": client_line_id,
                    "type_code": type_code,
                    "description": description,
                    "remarks": remarks,
                    "coverage_frequency": coverage_frequency,
                    "amount": amount,
                    "sort_order": index,
                    **worksheet_amounts,
                }
            )

    if not errors and _sum_line_item_amounts(cleaned_line_items) > MAX_MONEY_AMOUNT:
        errors.append(f"Entry total must be {MAX_MONEY_AMOUNT} or less.")
    return cleaned_line_items, errors


def _sum_line_item_amounts(line_items):
    total_amount = Decimal("0.00")
    for line_item in line_items:
        total_amount += line_item["amount"]
    return total_amount.quantize(Decimal("0.01"))


def _resolve_period_from_entry_date(entry_date):
    return entry_date.month, entry_date.year


def _validate_line_coverage(line_items, entry_date):
    for line in line_items:
        coverage = line.get("coverage_frequency")
        if coverage == FinancialRecord.FREQUENCY_QUARTERLY and entry_date.month % 3:
            end_month = ((entry_date.month - 1) // 3 + 1) * 3
            end_label = date(entry_date.year, end_month, 1).strftime("%B %Y")
            category = {"sales": "Sales", "expenses": "Expenses"}.get(line["type_code"].lower(), "Record detail")
            return _write_error("invalid_coverage", f"{category}: For a whole quarter, set Record Date to {end_label}.")
        if coverage == FinancialRecord.FREQUENCY_ANNUALLY and entry_date.month != 12:
            return _write_error("invalid_coverage", "For a whole year, use December as the record month.")
    return None


def _serialize_client(client: Client) -> dict:
    # Financial/report access never grants access to stored account credentials.
    summary = serialize_client(client)
    return {key: summary[key] for key in (
        "id", "client_name", "tin_number", "trade_name", "tax_registration", "location", "permit_number",
        "birthday", "email", "email_password", "orus_account", "orus_password",
        "custom_fields", "forecast_growth_percent",
    )}


def _serialize_line_item(line_item: FinancialRecordLine) -> dict:
    return {
        "id": line_item.id,
        "type_code": line_item.type_code,
        "description": line_item.description,
        "remarks": line_item.remarks,
        "coverage_frequency": line_item.coverage_frequency,
        "amount": str(line_item.amount),
        **{
            field_name: str(getattr(line_item, field_name)) if getattr(line_item, field_name) is not None else None
            for field_name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS
        },
    }


def _record_line_items(record):
    if hasattr(record, "loaded_line_items"):
        return record.loaded_line_items
    return list(record.line_items.all())


def _load_bounded_records(queryset):
    records = bounded_list(queryset, MAX_RECORDS, "records")
    if not records:
        return records
    record_map = {record.id: record for record in records}
    # A global detail budget, not a per-record prefetch limit multiplied by 5,000.
    lines = bounded_list(
        FinancialRecordLine.objects.filter(record_id__in=record_map).order_by("sort_order", "id"),
        MAX_TRANSACTION_DETAILS, "transaction details",
    )
    for record in records:
        record.loaded_line_items = []
    for line in lines:
        record_map[line.record_id].loaded_line_items.append(line)
    return records


def _serialize_record(record: FinancialRecord) -> dict:
    # Model ordering is already sort_order/id; reordering bypasses the prefetch.
    line_items = _record_line_items(record)

    deadline_completed = False
    if record.deadline_date:
        latest_entry = getattr(record, "client_latest_entry", None)
        if not hasattr(record, "client_latest_entry"):
            latest_entry = FinancialRecord.objects.filter(
                bookkeeper_id=record.bookkeeper_id, client_id=record.client_id,
            ).aggregate(latest=Max("entry_date"))["latest"]
        deadline_completed = bool(
            latest_entry and latest_entry >= record.deadline_date.replace(day=1)
        )

    return {
        "id": record.id,
        "revision": record.updated_at.isoformat(),
        "date": record.entry_date.isoformat() if record.entry_date else "",
        "frequency": record.frequency or FinancialRecord.FREQUENCY_MONTHLY,
        "notes": record.notes or "",
        "deadline_date": record.deadline_date.isoformat() if record.deadline_date else "",
        "deadline_completed": deadline_completed,
        "total_amount": str(record.total_amount or Decimal("0.00")),
        "line_items_count": len(line_items),
        "line_items": [_serialize_line_item(line_item) for line_item in line_items],
    }


def _build_summary(records):
    total_amount = Decimal("0.00")
    line_item_count = 0
    breakdown_map: dict[str, Decimal] = {}

    for record in records:
        total_amount += record.total_amount or Decimal("0.00")

        for line_item in _record_line_items(record):
            line_item_count += 1
            key = line_item.type_code or "Uncategorized"
            breakdown_map[key] = breakdown_map.get(key, Decimal("0.00")) + (line_item.amount or Decimal("0.00"))

    breakdown = [
        {
            "type_code": type_code,
            "total_amount": str(amount.quantize(Decimal("0.01"))),
        }
        for type_code, amount in breakdown_map.items()
    ]
    breakdown.sort(key=lambda item: Decimal(item["total_amount"]), reverse=True)

    return {
        "total_amount": str(total_amount.quantize(Decimal("0.01"))),
        "entry_count": len(records),
        "line_item_count": line_item_count,
        "breakdown": breakdown,
    }


def _resolve_client_for_bookkeeper(bookkeeper, client_id, *, for_update=False):
    clients = Client.objects.filter(id=client_id, bookkeeper=bookkeeper)
    if for_update:
        # All financial writers take this parent lock first, including period cleanup.
        clients = clients.select_for_update()
    client = clients.first()
    if client is None:
        return None, {
            "ok": False,
            "message": "Client not found.",
            "errors": ["Client not found."],
        }
    return client, None


def list_financial_clients_for_bookkeeper(bookkeeper) -> dict:
    latest_record_for_client = (
        FinancialRecord.objects.filter(
            bookkeeper=bookkeeper,
            client_id=OuterRef("pk"),
        )
        .order_by("-entry_date", "-id")
    )

    clients = (
        Client.objects.filter(bookkeeper=bookkeeper)
        .defer("email_password", "orus_password", "custom_fields")
        .exclude(remarks=Client.REMARK_CLOSED)
        .annotate(
            last_activity=Max("financial_records__entry_date", filter=Q(financial_records__bookkeeper=bookkeeper)),
            latest_record_updated_at=Max("financial_records__updated_at", filter=Q(financial_records__bookkeeper=bookkeeper)),
            financial_record_count=Count("financial_records", filter=Q(financial_records__bookkeeper=bookkeeper), distinct=True),
            last_deadline_date=Subquery(latest_record_for_client.values("deadline_date")[:1]),
        )
        .order_by("-created_at", "-id")
    )

    payload = []
    today = timezone.localdate()
    for client in clients:
        last_activity = client.last_activity.isoformat() if client.last_activity else ""
        activity_candidates = [
            value
            for value in (
                client.latest_record_updated_at,
                client.updated_at,
                client.created_at,
            )
            if value
        ]
        recent_activity_at = max(activity_candidates) if activity_candidates else None
        
        deadline_date = client.last_deadline_date.isoformat() if client.last_deadline_date else ""
        days_remaining = None
        deadline_completed = False
        if client.last_deadline_date:
            days_remaining = (client.last_deadline_date - today).days
            deadline_completed = bool(
                client.last_activity and client.last_activity >= client.last_deadline_date.replace(day=1)
            )

        payload.append(
            {
                "id": client.id,
                "client_name": client.client_name,
                "tin_number": client.tin_number,
                "trade_name": client.trade_name,
                "tax_registration": client.tax_registration,
                "last_activity": last_activity,
                "latest_record_updated_at": client.latest_record_updated_at.isoformat() if client.latest_record_updated_at else "",
                "recent_activity_at": recent_activity_at.isoformat() if recent_activity_at else "",
                "activity_state": "active" if last_activity else "none",
                "financial_record_count": client.financial_record_count,
                "deadline_date": deadline_date,
                "days_remaining": days_remaining,
                "deadline_completed": deadline_completed,
            }
        )

    return {
        "ok": True,
        "clients": payload,
    }


def list_records_for_client_period(bookkeeper, client_id: int, month_value=None, year_value=None) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id)
    if error_response:
        return error_response

    is_all = str(month_value).strip().lower() == "all"
    latest_entry = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client=client).aggregate(
        latest=Max("entry_date"),
    )["latest"]

    if is_all:
        records_query = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client=client)
        month = "all"
        year = "all"
    else:
        month, month_error = _normalize_month(month_value)
        if month_error:
            return {
                "ok": False,
                "message": month_error,
                "errors": [month_error],
            }

        year, year_error = _normalize_year(year_value)
        if year_error:
            return {
                "ok": False,
                "message": year_error,
                "errors": [year_error],
            }

        period = Period.objects.filter(client=client, month=month, year=year).first()
        if period is None:
            records_query = FinancialRecord.objects.none()
        else:
            records_query = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client=client, period=period)

    try:
        records = _load_bounded_records(records_query.order_by("-entry_date", "-id"))
    except WorkloadLimitExceeded as error:
        return workload_error(str(error))

    has_any_records = latest_entry is not None

    if is_all:
        prior_frequencies = []
    else:
        period_start = date(year, month, 1)
        prior_frequencies = list(
            FinancialRecord.objects.filter(
                bookkeeper=bookkeeper,
                client=client,
                entry_date__lt=period_start,
            )
            .order_by()
            .values_list("frequency", flat=True)
            .distinct()
        )

    return {
        "ok": True,
        "client": _serialize_client(client),
        "period": {
            "month": month,
            "month_label": "All Periods" if is_all else MONTH_NUMBER_TO_NAME.get(month, str(month)),
            "year": year,
        },
        "records": [_serialize_record_with_activity(record, latest_entry) for record in records],
        "summary": _build_summary(records),
        "has_any_records": has_any_records,
        "prior_frequencies": prior_frequencies,
    }


def _serialize_record_with_activity(record, latest_entry):
    record.client_latest_entry = latest_entry
    return _serialize_record(record)


def get_last_record_for_client_period(
    bookkeeper,
    client_id: int,
    month_value=None,
    year_value=None,
    frequency_value=None,
) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id)
    if error_response:
        return error_response

    month, month_error = _normalize_month(month_value)
    if month_error:
        return {
            "ok": False,
            "message": month_error,
            "errors": [month_error],
        }

    year, year_error = _normalize_year(year_value)
    if year_error:
        return {
            "ok": False,
            "message": year_error,
            "errors": [year_error],
        }

    frequency, frequency_error = (None, None) if frequency_value == "all" else _normalize_frequency(frequency_value)
    if frequency_error:
        return {
            "ok": False,
            "message": frequency_error,
            "errors": [frequency_error],
        }

    period_start = date(year, month, 1)
    record_query = (
        FinancialRecord.objects.filter(
            bookkeeper=bookkeeper,
            client=client,
            entry_date__lt=period_start,
        )
        .filter(**({"frequency": frequency} if frequency is not None else {}))
        .order_by("-entry_date", "-id")
    )
    try:
        records = _load_bounded_records(record_query[:1])
    except WorkloadLimitExceeded as error:
        return workload_error(str(error))
    record = records[0] if records else None

    if record is None or record.entry_date is None:
        message = "No previous entry found for this frequency."
        return {
            "ok": False,
            "message": message,
            "errors": [message],
            "no_record": True,
        }

    source_month = record.entry_date.month
    source_year = record.entry_date.year
    return {
        "ok": True,
        "client": _serialize_client(client),
        "source_period": {
            "month": source_month,
            "month_label": MONTH_NUMBER_TO_NAME.get(source_month, str(source_month)),
            "year": source_year,
        },
        "record": _serialize_record(record),
    }


def list_transaction_years_for_client(bookkeeper, client_id: int) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id)
    if error_response:
        return error_response
    years = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client=client).dates("entry_date", "year", order="DESC")
    return {"ok": True, "client": _serialize_client(client), "available_years": [value.year for value in years]}


def list_transactions_for_client_range(bookkeeper, client_id: int, date_from_value, date_to_value) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id)
    if error_response:
        return error_response

    date_from, date_from_error = _normalize_required_date(date_from_value, "Date From")
    if date_from_error:
        return {
            "ok": False,
            "message": date_from_error,
            "errors": [date_from_error],
        }

    date_to, date_to_error = _normalize_required_date(date_to_value, "Date To")
    if date_to_error:
        return {
            "ok": False,
            "message": date_to_error,
            "errors": [date_to_error],
        }

    if date_from > date_to:
        message = "Date From cannot be later than Date To."
        return {
            "ok": False,
            "message": message,
            "errors": [message],
        }

    try:
        records = _load_bounded_records(FinancialRecord.objects.filter(
            bookkeeper=bookkeeper,
            client=client,
            entry_date__gte=date_from,
            entry_date__lte=date_to,
        )
        .order_by("entry_date", "id"))
    except WorkloadLimitExceeded as error:
        return workload_error(str(error))

    rows = []
    total_amount = Decimal("0.00")
    line_item_count = 0

    for record in records:
        record_notes = record.notes or ""
        record_date = record.entry_date.isoformat() if record.entry_date else ""
        line_items = _record_line_items(record)
        for line_item in line_items:
            amount_value = line_item.amount or Decimal("0.00")
            total_amount += amount_value
            line_item_count += 1

            rows.append(
                {
                    "entry_date": record_date,
                    "type_code": line_item.type_code,
                    "description": line_item.description,
                    "amount": str(amount_value.quantize(Decimal("0.01"))),
                    "notes": record_notes,
                    "remarks": line_item.remarks,
                    "coverage_frequency": line_item.coverage_frequency,
                    "frequency": record.frequency,
                    **{
                        name: str(getattr(line_item, name)) if getattr(line_item, name) is not None else None
                        for name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS
                    },
                }
            )

    return {
        "ok": True,
        "client": _serialize_client(client),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "summary": {
            "entry_count": len(records),
            "line_item_count": line_item_count,
            "total_amount": str(total_amount.quantize(Decimal("0.01"))),
        },
        "rows": rows,
    }


@_financial_write
def create_record_for_client_period(bookkeeper, client_id: int, data: dict) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id, for_update=True)
    if error_response:
        return error_response

    text_errors = model_text_errors(FinancialRecord, data)
    if text_errors:
        return {"ok": False, "message": text_errors[0], "errors": text_errors}

    entry_date, entry_date_error = _normalize_entry_date(data.get("date"))
    if entry_date_error:
        return {
            "ok": False,
            "message": entry_date_error,
            "errors": [entry_date_error],
        }

    month, year = _resolve_period_from_entry_date(entry_date)

    frequency, frequency_error = _normalize_frequency(data.get("frequency"))
    if frequency_error:
        return {
            "ok": False,
            "message": frequency_error,
            "errors": [frequency_error],
        }

    deadline_date, deadline_date_error = _normalize_optional_date(data.get("deadline_date"), "Deadline Date")
    if deadline_date_error:
        return {
            "ok": False,
            "message": deadline_date_error,
            "errors": [deadline_date_error],
        }

    notes = _normalize_text(data.get("notes"))
    line_items, line_item_errors = _normalize_line_items(data.get("line_items"))
    if line_item_errors:
        return {
            "ok": False,
            "message": line_item_errors[0],
            "errors": line_item_errors,
        }

    coverage_error = _validate_line_coverage(line_items, entry_date)
    if coverage_error:
        return coverage_error

    for line_item in line_items:
        line_id = line_item.get("client_line_id") or f"line-{line_item['sort_order']}"
        line_item["client_line_id"] = line_id

    with transaction.atomic():
        period, _ = Period.objects.get_or_create(client=client, month=month, year=year)

        record = FinancialRecord.objects.create(
            bookkeeper=bookkeeper,
            client=client,
            period=period,
            entry_date=entry_date,
            frequency=frequency,
            notes=notes,
            deadline_date=deadline_date,
            total_amount=_sum_line_item_amounts(line_items),
        )

        for line_item in line_items:
            FinancialRecordLine.objects.create(
                record=record,
                type_code=line_item["type_code"],
                description=line_item["description"],
                remarks=line_item["remarks"],
                coverage_frequency=line_item["coverage_frequency"],
                amount=line_item["amount"],
                sort_order=line_item["sort_order"],
                **{name: line_item[name] for name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS},
            )

    from safebooks.services.client_service import check_and_promote_new_client
    check_and_promote_new_client(client)

    _audit_record(bookkeeper, client, record, BookkeeperAuditLog.ACTION_RECORD_CREATED)
    refreshed_record = FinancialRecord.objects.filter(id=record.id).select_related("bookkeeper", "client", "period").prefetch_related("line_items").get()
    from safebooks.services.client_notification_service import send_financial_record_created_email
    email_notification = {"sent": False, "skipped": False, "reason": "Email delivery is pending commit."}

    def notify_after_commit():
        try:
            email_notification.update(send_financial_record_created_email(refreshed_record))
        except Exception as error:
            # A notification failure must never turn a committed save into a failed save.
            logger.warning("Financial notification failed (%s).", type(error).__name__)
            email_notification.update(sent=False, skipped=False, reason="Email delivery failed.")

    transaction.on_commit(notify_after_commit)

    return {
        "ok": True,
        "message": "Financial entry added successfully.",
        "record": _serialize_record(refreshed_record),
        "client_email_notification": email_notification,
    }


@_financial_write
def update_record_for_client_period(bookkeeper, client_id: int, record_id: int, data: dict) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id, for_update=True)
    if error_response:
        return error_response

    record = (
        FinancialRecord.objects.filter(id=record_id, bookkeeper=bookkeeper, client=client)
        .select_for_update()
        .prefetch_related("line_items")
        .first()
    )
    if record is None:
        return {
            "ok": False,
            "message": "Financial record not found.",
            "errors": ["Financial record not found."],
        }

    revision_error = _check_revision(record, data.get("expected_revision"))
    if revision_error:
        return revision_error

    text_errors = model_text_errors(FinancialRecord, data)
    if text_errors:
        return {"ok": False, "message": text_errors[0], "errors": text_errors}

    entry_date_value = data.get("date", record.entry_date.isoformat())
    entry_date, entry_date_error = _normalize_entry_date(entry_date_value)
    if entry_date_error:
        return {
            "ok": False,
            "message": entry_date_error,
            "errors": [entry_date_error],
        }

    month, year = _resolve_period_from_entry_date(entry_date)

    notes = _normalize_text(data.get("notes", record.notes))

    if "deadline_date" in data:
        deadline_date, deadline_date_error = _normalize_optional_date(data.get("deadline_date"), "Deadline Date")
        if deadline_date_error:
            return {
                "ok": False,
                "message": deadline_date_error,
                "errors": [deadline_date_error],
            }
    else:
        deadline_date = record.deadline_date

    if "frequency" in data:
        frequency, frequency_error = _normalize_frequency(data.get("frequency"))
        if frequency_error:
            return {
                "ok": False,
                "message": frequency_error,
                "errors": [frequency_error],
            }
    else:
        frequency = record.frequency or FinancialRecord.FREQUENCY_MONTHLY

    if "line_items" in data:
        # An older editor must not silently discard independent form remarks.
        saved_lines = list(record.line_items.all())
        submitted = data.get("line_items")
        if any(line.coverage_frequency is not None for line in saved_lines) and isinstance(submitted, list):
            saved_coverage = {str(line.id): line.coverage_frequency for line in saved_lines}
            if any(isinstance(line, dict) and (
                "coverage_frequency" not in line or (
                    saved_coverage.get(str(line.get("client_line_id"))) is not None
                    and line.get("coverage_frequency") is None
                )
            ) for line in submitted):
                return _write_error("coverage_required", "Reload this entry before saving so each amount's covered period is kept. Your draft is unchanged.")
        if any(line.remarks is not None for line in saved_lines) and isinstance(data["line_items"], list) and any(
            isinstance(line, dict) and "remarks" not in line for line in data["line_items"]
        ):
            return _write_error("line_remarks_required", "Reload this entry before saving so its form remarks are kept. Your draft is unchanged.")
        # Older editors must reload rather than erase worksheet values they never loaded.
        has_saved_worksheet = any(
            getattr(line, name) is not None
            for line in saved_lines
            for name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS
        )
        submitted_lines = data.get("line_items")
        if has_saved_worksheet and isinstance(submitted_lines, list) and any(
            isinstance(line, dict) and any(name not in line for name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS)
            for line in submitted_lines
        ):
            return _write_error("worksheet_fields_required", "Reload this entry before saving so its worksheet amounts are kept. Your draft is unchanged.")
        line_items, line_item_errors = _normalize_line_items(data.get("line_items"))
        if line_item_errors:
            return {
                "ok": False,
                "message": line_item_errors[0],
                "errors": line_item_errors,
            }
        for line_item in line_items:
            line_id = line_item.get("client_line_id") or f"line-{line_item['sort_order']}"
            line_item["client_line_id"] = line_id
    else:
        line_items = [
            {
                "type_code": line_item.type_code,
                "description": line_item.description,
                "amount": line_item.amount,
                "sort_order": line_item.sort_order,
                "coverage_frequency": line_item.coverage_frequency,
            }
            for line_item in record.line_items.all()
        ]

    coverage_error = _validate_line_coverage(line_items, entry_date)
    if coverage_error:
        return coverage_error

    if _sum_line_item_amounts(line_items) > MAX_MONEY_AMOUNT:
        return _write_error("invalid_total", f"Entry total must be {MAX_MONEY_AMOUNT} or less.")

    with transaction.atomic():
        period, _ = Period.objects.get_or_create(client=client, month=month, year=year)

        original_revision = record.updated_at
        record.period = period
        record.entry_date = entry_date
        record.frequency = frequency
        record.notes = notes
        record.deadline_date = deadline_date
        record.total_amount = _sum_line_item_amounts(line_items)
        record.updated_at = max(timezone.now(), original_revision + timedelta(microseconds=1))
        changed = FinancialRecord.objects.filter(
            id=record.id, bookkeeper=bookkeeper, client=client, updated_at=original_revision,
        ).update(
            period=period, entry_date=entry_date, frequency=frequency, notes=notes,
            deadline_date=deadline_date, total_amount=record.total_amount, updated_at=record.updated_at,
        )
        if changed != 1:
            transaction.set_rollback(True)
            return _write_error("stale_record", "This entry changed. Your draft is unchanged; reload and review the latest entry.")

        if "line_items" in data:
            record.line_items.all().delete()
            for line_item in line_items:
                FinancialRecordLine.objects.create(
                    record=record,
                    type_code=line_item["type_code"],
                    description=line_item["description"],
                    remarks=line_item["remarks"],
                    coverage_frequency=line_item["coverage_frequency"],
                    amount=line_item["amount"],
                    sort_order=line_item["sort_order"],
                    **{name: line_item[name] for name in FinancialRecordLine.WORKSHEET_AMOUNT_LABELS},
                )

    from safebooks.services.client_service import check_and_promote_new_client
    check_and_promote_new_client(client)

    _audit_record(bookkeeper, client, record, BookkeeperAuditLog.ACTION_RECORD_UPDATED)

    refreshed_record = FinancialRecord.objects.filter(id=record.id).prefetch_related("line_items").first()

    return {
        "ok": True,
        "message": "Financial entry updated successfully.",
        "record": _serialize_record(refreshed_record),
    }


@_financial_write
def delete_record_for_client(bookkeeper, client_id: int, record_id: int, data: dict | None = None) -> dict:
    client, error_response = _resolve_client_for_bookkeeper(bookkeeper, client_id, for_update=True)
    if error_response:
        return error_response

    record = FinancialRecord.objects.select_for_update().filter(id=record_id, bookkeeper=bookkeeper, client=client).first()
    if record is None:
        return {
            "ok": False,
            "message": "Financial record not found.",
            "errors": ["Financial record not found."],
        }

    revision_error = _check_revision(record, (data or {}).get("expected_revision"))
    if revision_error:
        return revision_error

    period_id = record.period_id
    deleted_record = {
        "id": record.id,
        "date": record.entry_date.isoformat() if record.entry_date else "",
    }
    _audit_record(bookkeeper, client, record, BookkeeperAuditLog.ACTION_RECORD_DELETED)
    record.delete()

    if not FinancialRecord.objects.filter(period_id=period_id).exists():
        Period.objects.filter(id=period_id).delete()

    from safebooks.services.client_service import check_and_promote_new_client
    check_and_promote_new_client(client)

    return {
        "ok": True,
        "message": "Financial entry deleted successfully.",
        "record": deleted_record,
    }
