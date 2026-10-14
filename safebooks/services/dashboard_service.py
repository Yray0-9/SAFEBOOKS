from decimal import Decimal

from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.utils import timezone

from safebooks.models import Client, FinancialRecord, Period


MONTH_NUMBER_TO_NAME = dict(Period.MONTH_CHOICES)
FREQUENCY_INTERVALS = {
    FinancialRecord.FREQUENCY_MONTHLY: 1,
    FinancialRecord.FREQUENCY_QUARTERLY: 3,
    FinancialRecord.FREQUENCY_ANNUALLY: 12,
}


def _month_label(month_number: int) -> str:
    return MONTH_NUMBER_TO_NAME.get(month_number, str(month_number))


def _period_label(month_number: int, year_number: int) -> str:
    return f"{_month_label(month_number)} {year_number}"


def _serialize_recent_entry(record: FinancialRecord) -> dict:
    return {
        "client_id": record.client_id,
        "client_name": record.client.client_name,
        "tin_number": record.client.tin_number,
        "trade_name": record.client.trade_name,
        "entry_date": record.entry_date.isoformat() if record.entry_date else "",
        "period": _period_label(record.period.month, record.period.year),
        "total_amount": str(record.total_amount or Decimal("0.00")),
    }


def _months_between(start_date, end_date) -> int:
    if not start_date or not end_date:
        return 0
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    return max(months, 0)


def _is_due_for_frequency(last_entry_date, frequency: str, reference_date) -> bool:
    interval = FREQUENCY_INTERVALS.get(frequency, 1)
    months_passed = _months_between(last_entry_date, reference_date)

    if frequency == FinancialRecord.FREQUENCY_QUARTERLY:
        return months_passed > interval

    return months_passed >= interval


def _build_client_activity_payload(client, current_period_label: str, reference_date) -> dict:
    has_entries = (client.record_count or 0) > 0
    has_current_period_entries = (client.current_period_entries or 0) > 0
    frequency = client.last_frequency or FinancialRecord.FREQUENCY_MONTHLY
    deadline_date = getattr(client, "last_deadline_date", None)
    if deadline_date:
        is_due = has_entries and reference_date >= deadline_date
    else:
        is_due = has_entries and _is_due_for_frequency(client.last_entry_date, frequency, reference_date)

    if has_current_period_entries:
        status = "updated"
        compliance = "filed"
    elif has_entries and is_due:
        status = "needs-attention"
        compliance = "pending"
    elif has_entries:
        status = "updated"
        compliance = "filed"
    else:
        status = "no-entries"
        compliance = "late"

    last_entry_date = client.last_entry_date.isoformat() if client.last_entry_date else ""
    activity_candidates = [
        value
        for value in (
            getattr(client, "latest_record_updated_at", None),
            getattr(client, "updated_at", None),
            getattr(client, "created_at", None),
        )
        if value
    ]
    recent_activity_at = max(activity_candidates) if activity_candidates else None

    if client.last_period_month and client.last_period_year:
        current_period = _period_label(client.last_period_month, client.last_period_year)
    else:
        current_period = current_period_label

    remarks = client.remarks or Client.REMARK_NEW
    if remarks not in {Client.REMARK_NEW, Client.REMARK_ACTIVE, Client.REMARK_SEPARATED, Client.REMARK_CLOSED}:
        remarks = Client.REMARK_NEW

    deadline_date = deadline_date.isoformat() if deadline_date else ""
    days_remaining = None
    deadline_completed = False
    if getattr(client, "last_deadline_date", None):
        days_remaining = (client.last_deadline_date - reference_date).days
        deadline_completed = bool(
            client.last_entry_date and client.last_entry_date >= client.last_deadline_date.replace(day=1)
        )

    return {
        "client_id": client.id,
        "client_name": client.client_name,
        "tin_number": client.tin_number,
        "trade_name": client.trade_name,
        "last_entry_date": last_entry_date,
        "recent_activity_at": recent_activity_at.isoformat() if recent_activity_at else "",
        "current_period": current_period,
        "status": status,
        "remarks": remarks,
        "compliance": compliance,
        "deadline_date": deadline_date,
        "days_remaining": days_remaining,
        "deadline_completed": deadline_completed,
    }


def _calculate_percentage(value: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((value / total) * 100)


def get_dashboard_summary_for_bookkeeper(bookkeeper) -> dict:
    today = timezone.localdate()
    current_year = today.year
    current_month = today.month
    current_period_label = _period_label(current_month, current_year)

    from safebooks.services.client_service import resolve_client_remarks, with_status_activity

    latest_record_for_client = (
        FinancialRecord.objects.filter(
            bookkeeper=bookkeeper,
            client_id=OuterRef("pk"),
        )
        .order_by("-entry_date", "-id")
    )

    clients = list(
        with_status_activity(Client.objects.filter(bookkeeper=bookkeeper), today=today)
        .defer("email_password", "orus_password", "custom_fields")
        .annotate(
            record_count=Count(
                "financial_records",
                filter=Q(financial_records__bookkeeper=bookkeeper),
                distinct=True,
            ),
            current_period_entries=Count(
                "financial_records",
                filter=Q(
                    financial_records__bookkeeper=bookkeeper,
                    financial_records__period__month=current_month,
                    financial_records__period__year=current_year,
                ),
                distinct=True,
            ),
            last_entry_date=Subquery(latest_record_for_client.values("entry_date")[:1]),
            last_period_month=Subquery(latest_record_for_client.values("period__month")[:1]),
            last_period_year=Subquery(latest_record_for_client.values("period__year")[:1]),
            last_frequency=Subquery(latest_record_for_client.values("frequency")[:1]),
            last_deadline_date=Subquery(latest_record_for_client.values("deadline_date")[:1]),
            latest_record_updated_at=Max(
                "financial_records__updated_at",
                filter=Q(financial_records__bookkeeper=bookkeeper),
            ),
        )
        .order_by("-created_at", "-id")
    )
    for client in clients:
        client.remarks = resolve_client_remarks(client, today=today)

    recent_client_activity = [
        _build_client_activity_payload(client, current_period_label, today)
        for client in clients if client.remarks != Client.REMARK_CLOSED
    ]

    recent_entries = list(
        FinancialRecord.objects.filter(bookkeeper=bookkeeper)
        .select_related("client", "period")
        .order_by("-entry_date", "-id")[:5]
    )

    recent_entries_payload = [_serialize_recent_entry(record) for record in recent_entries]

    total_clients = len(clients)
    total_active_clients = len(recent_client_activity)
    total_entries_this_month = FinancialRecord.objects.filter(
        bookkeeper=bookkeeper,
        period__month=current_month,
        period__year=current_year,
    ).count()

    remark_new_count = sum(1 for client in clients if client.remarks == Client.REMARK_NEW)
    remark_active_count = sum(1 for client in clients if client.remarks == Client.REMARK_ACTIVE)
    remark_separated_count = sum(1 for client in clients if client.remarks == Client.REMARK_SEPARATED)
    remark_closed_count = sum(1 for client in clients if client.remarks == Client.REMARK_CLOSED)

    filed_count = sum(1 for row in recent_client_activity if row["compliance"] == "filed")
    pending_count = sum(1 for row in recent_client_activity if row["compliance"] == "pending")
    late_count = sum(1 for row in recent_client_activity if row["compliance"] == "late")

    pending_compliance_count = pending_count + late_count

    return {
        "ok": True,
        "current_period_label": current_period_label,
        "metrics": {
            "total_clients": total_clients,
            "total_entries_this_month": total_entries_this_month,
            "pending_compliance": pending_compliance_count,
            "new_clients": remark_new_count,
        },
        "remarks_summary": {
            "new": remark_new_count,
            "active": remark_active_count,
            "separated": remark_separated_count,
            "closed": remark_closed_count,
        },
        "compliance_summary": {
            "filed": {
                "count": filed_count,
                "percentage": _calculate_percentage(filed_count, total_active_clients),
            },
            "pending": {
                "count": pending_count,
                "percentage": _calculate_percentage(pending_count, total_active_clients),
            },
            "late": {
                "count": late_count,
                "percentage": _calculate_percentage(late_count, total_active_clients),
            },
        },
        "recent_client_activity": recent_client_activity,
        "recent_entries": recent_entries_payload,
    }
