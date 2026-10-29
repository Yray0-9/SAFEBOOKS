from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re

from django.db.models import Count, F, Max, Window
from django.db.models.functions import Coalesce, RowNumber
from django.utils import timezone

from safebooks.models import Client, FinancialRecord, FinancialRecordLine
from safebooks.services.forecasting_service import (
    build_sarima_forecast, requires_sarima_fit, FORECAST_READY_STATUSES, rejected_prediction_note,
)
from safebooks.services.forecast_period_service import build_frequency_forecasts
from safebooks.services.tax_form_frequency_service import standard_tax_form_frequency
from safebooks.services.workload_limits import (
    MAX_RECORDS, MAX_TRANSACTION_DETAILS, MAX_FORECAST_SERIES, MAX_FORECAST_OBSERVATIONS,
    MAX_FORECAST_DISTINCT_FITS, MAX_FORECAST_FIT_OBSERVATIONS,
    WorkloadLimitExceeded, bounded_list, normalize_forecast_horizon, workload_error,
)


TAX_TYPE_CODES = {
    "1701",
    "1701a",
    "1702",
    "2550m",
    "2550q",
    "2551m",
    "2551q",
    "0619e",
    "0619f",
    "1601c",
    "1601eq",
    "1701q",
    "2370",
}

TAX_ANNUAL_FORM_CODES = {
    "1701",
    "1701a",
    "1702",
}

TAX_QUARTERLY_FORM_CODES = {
    "1701q",
    "1702q",
    "2550q",
    "2551q",
    "1601eq",
}

TAX_MONTHLY_FORM_CODES = {
    "0619e",
    "0619f",
    "1601c",
    "2550m",
    "2551m",
}

TAX_CODE_PATTERN = re.compile(r"^\d{4}[a-z]{0,2}$", re.IGNORECASE)

TAX_KEYWORDS = (
    "tax",
    "taxes",
    "vat",
    "withholding",
    "wht",
    "percentage tax",
    "income tax",
)

EXPENSE_KEYWORDS = (
    "expense",
    "expenses",
    "cost",
    "fee",
    "professional fee",
    "rent",
    "utility",
    "utilities",
    "salary",
    "payroll",
    "supplies",
    "fuel",
    "transport",
    "allowance",
    "purchase",
    "materials",
)

SALES_KEYWORDS = (
    "sale",
    "sales",
    "revenue",
    "income",
    "service",
    "collection",
)


def _normalize_search_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def _normalize_type_code_label(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_type_code_key(value: str) -> str:
    return _normalize_type_code_label(value).lower()


NORMALIZED_TAX_KEYWORDS = tuple(_normalize_search_text(keyword) for keyword in TAX_KEYWORDS)
NORMALIZED_EXPENSE_KEYWORDS = tuple(_normalize_search_text(keyword) for keyword in EXPENSE_KEYWORDS)
NORMALIZED_SALES_KEYWORDS = tuple(_normalize_search_text(keyword) for keyword in SALES_KEYWORDS)



def _contains_keyword(normalized_text: str, normalized_keyword: str) -> bool:
    if not normalized_keyword:
        return False
    return f" {normalized_keyword} " in f" {normalized_text} "

REMARK_TO_LABEL = {
    Client.REMARK_NEW: "New",
    Client.REMARK_ACTIVE: "Active",
    Client.REMARK_SEPARATED: "Separated",
    Client.REMARK_CLOSED: "Closed",
}

REMARK_TO_TITLE = {
    Client.REMARK_NEW: "New Client",
    Client.REMARK_ACTIVE: "Active Client",
    Client.REMARK_SEPARATED: "Separated Client",
    Client.REMARK_CLOSED: "Closed Client",
}

REMARK_TO_DESCRIPTION = {
    Client.REMARK_NEW: "This client is newly registered and is in their first bookkeeping month.",
    Client.REMARK_ACTIVE: "This client actively pays and files their compliance regularly.",
    Client.REMARK_SEPARATED: "This client did not file/pay compliance for the year and is separated for the new bookkeeping year.",
    Client.REMARK_CLOSED: "This client has closed their business.",
}

ALL_CLIENTS_REMARK_DESCRIPTIONS = {
    Client.REMARK_NEW: "Most clients are newly registered in their onboarding phase.",
    Client.REMARK_ACTIVE: "Most clients actively pay and file their compliance regularly.",
    Client.REMARK_SEPARATED: "Multiple clients are separated due to missing filing activity for the year.",
    Client.REMARK_CLOSED: "Some clients have closed their business.",
}

MONTH_SHORT_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

FREQUENCY_LABELS = {
    FinancialRecord.FREQUENCY_MONTHLY: "Monthly",
    FinancialRecord.FREQUENCY_QUARTERLY: "Quarterly",
    FinancialRecord.FREQUENCY_ANNUALLY: "Annually",
}

FREQUENCY_INTERVALS = {
    FinancialRecord.FREQUENCY_MONTHLY: 1,
    FinancialRecord.FREQUENCY_QUARTERLY: 3,
    FinancialRecord.FREQUENCY_ANNUALLY: 12,
}

FORECAST_CATEGORIES = ("sales", "expenses", "tax")
FORECAST_METHOD_LABEL = "SARIMA"
FORECAST_LIMITED_DATA_MESSAGE = "Forecasts are shown only for complete monthly or quarterly histories that meet the SARIMA minimum-history requirement."
FORECAST_MIXED_FREQUENCY = "mixed"


def _to_money_number(value: Decimal) -> float:
    return float((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _format_percent(value: Decimal) -> str:
    normalized = (value or Decimal("0.00")).quantize(Decimal("0.01"))
    percent_text = f"{normalized:.2f}"
    return percent_text.rstrip("0").rstrip(".")


def _empty_bucket() -> dict:
    return {
        "sales": Decimal("0.00"),
        "expenses": Decimal("0.00"),
        "tax": Decimal("0.00"),
    }


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    absolute_month = (year * 12) + (month - 1) + offset
    shifted_year = absolute_month // 12
    shifted_month = (absolute_month % 12) + 1
    return shifted_year, shifted_month


def _recent_month_slots(reference_date: date, count: int = 6) -> list[tuple[int, int, str]]:
    slots: list[tuple[int, int, str]] = []
    starting_offset = -(count - 1)

    for index in range(count):
        year, month = _shift_month(reference_date.year, reference_date.month, starting_offset + index)
        slots.append((year, month, MONTH_SHORT_NAMES.get(month, str(month))))

    return slots


def _classify_line_item(type_code: str, description: str) -> str:
    normalized_type_code = str(type_code or "").strip().lower()
    normalized_type_text = _normalize_search_text(type_code)
    searchable_text = _normalize_search_text(f"{type_code or ''} {description or ''}")

    if normalized_type_code.startswith("bir form"):
        return "tax"
    if normalized_type_code in TAX_TYPE_CODES:
        return "tax"
    if TAX_CODE_PATTERN.match(normalized_type_code):
        return "tax"
    if any(_contains_keyword(normalized_type_text, keyword) for keyword in NORMALIZED_TAX_KEYWORDS):
        return "tax"
    if any(_contains_keyword(normalized_type_text, keyword) for keyword in NORMALIZED_EXPENSE_KEYWORDS):
        return "expenses"
    if any(_contains_keyword(normalized_type_text, keyword) for keyword in NORMALIZED_SALES_KEYWORDS):
        return "sales"
    if any(_contains_keyword(searchable_text, keyword) for keyword in NORMALIZED_TAX_KEYWORDS):
        return "tax"
    if any(_contains_keyword(searchable_text, keyword) for keyword in NORMALIZED_EXPENSE_KEYWORDS):
        return "expenses"
    if any(_contains_keyword(searchable_text, keyword) for keyword in NORMALIZED_SALES_KEYWORDS):
        return "sales"

    return "sales"


def _contains_tax_form_code(raw_text: str, form_code: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(form_code.lower())}(?:v\d+)?(?![a-z0-9])"
    return re.search(pattern, raw_text) is not None


def _infer_tax_line_frequency(type_code: str, description: str) -> str | None:
    recognized, frequency = standard_tax_form_frequency(type_code)
    if recognized:
        # Form metadata wins over editable wording. Known ambiguous forms use
        # the saved parent fallback rather than acquiring a schedule from text.
        return frequency

    # Preserve the legacy inference path for custom/unlisted tax details.
    raw_text = f"{type_code or ''} {description or ''}".lower()
    searchable_text = _normalize_search_text(raw_text)

    if any(_contains_keyword(searchable_text, keyword) for keyword in ("annual", "annually", "yearly")):
        return FinancialRecord.FREQUENCY_ANNUALLY
    if any(_contains_keyword(searchable_text, keyword) for keyword in ("quarterly", "quarter")):
        return FinancialRecord.FREQUENCY_QUARTERLY
    if any(_contains_keyword(searchable_text, keyword) for keyword in ("monthly", "month")):
        return FinancialRecord.FREQUENCY_MONTHLY

    if any(_contains_tax_form_code(raw_text, form_code) for form_code in TAX_QUARTERLY_FORM_CODES):
        return FinancialRecord.FREQUENCY_QUARTERLY
    if any(_contains_tax_form_code(raw_text, form_code) for form_code in TAX_MONTHLY_FORM_CODES):
        return FinancialRecord.FREQUENCY_MONTHLY
    if any(_contains_tax_form_code(raw_text, form_code) for form_code in TAX_ANNUAL_FORM_CODES):
        return FinancialRecord.FREQUENCY_ANNUALLY

    return None


def _resolve_line_forecast_frequency(line: FinancialRecordLine, category: str) -> str:
    if category in {"sales", "expenses"} and getattr(line, "coverage_frequency", None):
        return line.coverage_frequency
    if category == "tax":
        inferred_frequency = _infer_tax_line_frequency(line.type_code, line.description)
        if inferred_frequency:
            return inferred_frequency

    return _normalize_frequency(line.record.frequency)


def _resolve_all_clients_remarks(clients: list[Client]) -> str:
    remark_counts = {
        Client.REMARK_NEW: 0,
        Client.REMARK_ACTIVE: 0,
        Client.REMARK_SEPARATED: 0,
    }

    for client in clients:
        if client.remarks == Client.REMARK_CLOSED:
            continue
        level = client.remarks if client.remarks in remark_counts else Client.REMARK_NEW
        remark_counts[level] += 1

    if remark_counts[Client.REMARK_SEPARATED] > 0:
        return Client.REMARK_SEPARATED
    if remark_counts[Client.REMARK_ACTIVE] > 0:
        return Client.REMARK_ACTIVE
    return Client.REMARK_NEW


def _build_remarks_insight(scope_client: Client | None, all_clients: list[Client]) -> dict:
    if scope_client is not None:
        level = scope_client.remarks if scope_client.remarks in REMARK_TO_TITLE else Client.REMARK_NEW
        return {
            "level": level,
            "title": REMARK_TO_TITLE[level],
            "description": REMARK_TO_DESCRIPTION[level],
        }

    level = _resolve_all_clients_remarks(all_clients)
    return {
        "level": level,
        "title": REMARK_TO_TITLE[level],
        "description": ALL_CLIENTS_REMARK_DESCRIPTIONS[level],
    }


def _build_forecast_from_monthly_net(monthly_net_values: list[Decimal]) -> dict:
    if not monthly_net_values:
        return {
            "trend": "Stable",
            "description": "Forecast is unavailable until enough historical entries exist.",
            "sparkline": [],
        }

    if len(monthly_net_values) < 4:
        trend = "Stable"
    else:
        midpoint = len(monthly_net_values) // 2
        older_half = monthly_net_values[:midpoint]
        newer_half = monthly_net_values[midpoint:]

        older_average = sum(older_half, Decimal("0.00")) / Decimal(len(older_half) or 1)
        newer_average = sum(newer_half, Decimal("0.00")) / Decimal(len(newer_half) or 1)

        baseline = abs(older_average) if older_average != 0 else Decimal("1.00")
        change_ratio = (newer_average - older_average) / baseline

        if change_ratio > Decimal("0.08"):
            trend = "Increasing"
        elif change_ratio < Decimal("-0.08"):
            trend = "Decreasing"
        else:
            trend = "Stable"

    description_by_trend = {
        "Increasing": "Recent movement suggests a positive upward pattern.",
        "Decreasing": "Recent movement suggests a weakening pattern that needs attention.",
        "Stable": "Recent movement suggests a stable financial pattern.",
    }

    min_net_value = min(monthly_net_values)
    if min_net_value < 0:
        sparkline_values = [value - min_net_value for value in monthly_net_values]
    else:
        sparkline_values = list(monthly_net_values)

    return {
        "trend": trend,
        "description": description_by_trend[trend],
        "sparkline": [_to_money_number(value) for value in sparkline_values],
    }


def _weighted_average(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0.00")

    weights = [Decimal(index + 1) for index in range(len(values))]
    weight_total = sum(weights, Decimal("0.00"))
    if weight_total == 0:
        return Decimal("0.00")

    weighted_sum = sum(
        (value or Decimal("0.00")) * weight
        for value, weight in zip(values, weights)
    )

    return weighted_sum / weight_total

def _frequency_interval_months(frequency: str) -> int:
    return FREQUENCY_INTERVALS.get(frequency, 1)


def _frequency_label(frequency: str) -> str:
    return FREQUENCY_LABELS.get(frequency, "Monthly")


def _format_period_label(year: int, month: int, frequency: str) -> str:
    month_label = MONTH_SHORT_NAMES.get(month, str(month))
    if frequency == FinancialRecord.FREQUENCY_QUARTERLY:
        quarter = ((month - 1) // 3) + 1
        return f"{month_label} {year} (Q{quarter})"
    if frequency == FinancialRecord.FREQUENCY_ANNUALLY:
        return f"{month_label} {year} (Annual)"
    return f"{month_label} {year}"


def _workflow_frequency_order(frequency: str) -> int:
    order = {
        FinancialRecord.FREQUENCY_MONTHLY: 0,
        FinancialRecord.FREQUENCY_QUARTERLY: 1,
        FinancialRecord.FREQUENCY_ANNUALLY: 2,
    }
    return order.get(frequency, 99)


def _period_index(year: int, month: int) -> int:
    return (year * 12) + month


def _quarter_end_month(month: int) -> int:
    return (((month - 1) // 3) + 1) * 3


def _find_next_quarterly_workflow_period(
    recorded_periods: set[tuple[int, int]],
    reference_date: date,
) -> tuple[int, int, bool]:
    ordered_periods = sorted(recorded_periods)
    earliest_year, earliest_month = ordered_periods[0]
    current_index = _period_index(reference_date.year, reference_date.month)

    expected_year = earliest_year
    expected_month = _quarter_end_month(earliest_month)

    while _period_index(expected_year, expected_month) <= current_index:
        if (expected_year, expected_month) not in recorded_periods:
            return expected_year, expected_month, True
        expected_year, expected_month = _shift_month(expected_year, expected_month, 3)

    return expected_year, expected_month, False


def _find_next_workflow_period(
    frequency: str,
    recorded_periods: set[tuple[int, int]],
    reference_date: date,
) -> tuple[int, int, bool]:
    normalized_frequency = _normalize_frequency(frequency)
    if not recorded_periods:
        return reference_date.year, reference_date.month, True

    if normalized_frequency == FinancialRecord.FREQUENCY_QUARTERLY:
        return _find_next_quarterly_workflow_period(recorded_periods, reference_date)

    interval = _frequency_interval_months(normalized_frequency)
    ordered_periods = sorted(recorded_periods)
    current_key = (reference_date.year, reference_date.month)
    current_index = _period_index(*current_key)
    earliest_year, earliest_month = ordered_periods[0]
    latest_year, latest_month = ordered_periods[-1]

    next_year, next_month = _shift_month(earliest_year, earliest_month, interval)
    while _period_index(next_year, next_month) <= current_index:
        if (next_year, next_month) not in recorded_periods:
            return next_year, next_month, True
        next_year, next_month = _shift_month(next_year, next_month, interval)

    if current_key in recorded_periods:
        return reference_date.year, reference_date.month, True

    if _period_index(latest_year, latest_month) >= current_index:
        return latest_year, latest_month, True

    next_year, next_month = _shift_month(latest_year, latest_month, interval)
    return next_year, next_month, _period_index(next_year, next_month) <= current_index


def _resolve_workflow_period(
    frequency: str,
    latest_record: _WorkflowRecord | None,
    reference_date: date,
    has_current_year_annual_record: bool = False,
) -> tuple[int, int, bool]:
    normalized_frequency = _normalize_frequency(frequency)

    if normalized_frequency == FinancialRecord.FREQUENCY_MONTHLY:
        return reference_date.year, reference_date.month, True

    if normalized_frequency == FinancialRecord.FREQUENCY_QUARTERLY:
        quarter_end_month = (((reference_date.month - 1) // 3) + 1) * 3
        return reference_date.year, quarter_end_month, reference_date.month == quarter_end_month

    if normalized_frequency == FinancialRecord.FREQUENCY_ANNUALLY:
        anchor_month = latest_record.period.month if latest_record and latest_record.period_id else reference_date.month
        if has_current_year_annual_record and reference_date.month > anchor_month:
            return reference_date.year + 1, anchor_month, False
        return reference_date.year, anchor_month, reference_date.month >= anchor_month

    return reference_date.year, reference_date.month, True


def _build_workflow_schedule_item(
    *,
    bookkeeper,
    client: Client,
    frequency: str,
    latest_record: _WorkflowRecord | None,
    recorded_periods: set[tuple[int, int]] | None,
    period_counts: dict[tuple[int, int], tuple[int, int]],
    reference_date: date,
) -> dict:
    normalized_frequency = _normalize_frequency(frequency)
    has_current_year_annual_record = False
    if normalized_frequency == FinancialRecord.FREQUENCY_ANNUALLY and latest_record and latest_record.period_id:
        has_current_year_annual_record = (reference_date.year, latest_record.period.month) in (recorded_periods or set())

    safe_recorded_periods = recorded_periods or set()
    if safe_recorded_periods:
        target_year, target_month, is_due_now = _find_next_workflow_period(
            normalized_frequency,
            safe_recorded_periods,
            reference_date,
        )
    else:
        target_year, target_month, is_due_now = _resolve_workflow_period(
            normalized_frequency,
            latest_record,
            reference_date,
            has_current_year_annual_record,
        )
    entry_count, detail_count = period_counts.get((target_year, target_month), (0, 0))
    has_record = entry_count > 0
    status = "ready" if has_record else ("missing" if is_due_now else "upcoming")

    return {
        "frequency": normalized_frequency,
        "frequency_label": _frequency_label(normalized_frequency),
        "period_label": _format_period_label(target_year, target_month, normalized_frequency),
        "period_year": target_year,
        "period_month": target_month,
        "is_due_now": is_due_now,
        "status": status,
        "has_record": has_record,
        "entry_count": entry_count,
        "transaction_detail_count": detail_count,
        "latest_period_label": _format_period_label(
            latest_record.period.year,
            latest_record.period.month,
            normalized_frequency,
        ) if latest_record and latest_record.period_id else "",
    }


@dataclass(frozen=True)
class _WorkflowPeriod:
    year: int
    month: int


@dataclass(frozen=True)
class _WorkflowRecord:
    frequency: str
    period_id: int
    period: _WorkflowPeriod
    entry_date: date
    workflow_entry_count: int
    workflow_detail_count: int


def _build_client_workflow_status(client: Client | None, bookkeeper, reference_date: date) -> dict | None:
    if client is None:
        return None

    scoped = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client=client).annotate(
        workflow_frequency=Coalesce("line_items__coverage_frequency", "frequency"),
    )
    # Workflow needs frequency/period counts and the latest date, not every raw
    # record. This keeps a narrow analytics year usable with a large older history.
    groups = bounded_list(
        scoped.values("workflow_frequency", "period_id", "period__year", "period__month")
        .annotate(
            workflow_entry_count=Count("id", distinct=True),
            workflow_detail_count=Count("line_items"),
            workflow_entry_date=Max("entry_date"),
        ).order_by("-period__year", "-period__month", "-workflow_entry_date"),
        MAX_RECORDS, "workflow periods",
    )
    for item in groups:
        item["frequency"] = item["workflow_frequency"]
    # One latest entry per period/coverage, without a correlated query per detail.
    # Joined duplicates share an entry ID; RowNumber retains date/ID tie-breaking.
    latest_rows = bounded_list(
        scoped.filter(period_id__in={item["period_id"] for item in groups})
        .annotate(workflow_rank=Window(
            expression=RowNumber(), partition_by=[F("period_id"), F("workflow_frequency")],
            order_by=[F("entry_date").desc(), F("id").desc()],
        )).filter(workflow_rank=1).order_by().values("period_id", "workflow_frequency", "id"),
        MAX_RECORDS, "workflow periods",
    )
    latest_ids = {(item["period_id"], item["workflow_frequency"]): item["id"] for item in latest_rows}
    groups.sort(key=lambda item: (
        item["period__year"], item["period__month"], item["workflow_entry_date"],
        latest_ids.get((item["period_id"], item["frequency"]), 0),
    ), reverse=True)
    client_records = [
        _WorkflowRecord(
            frequency=item["frequency"], period_id=item["period_id"],
            period=_WorkflowPeriod(item["period__year"], item["period__month"]),
            entry_date=item["workflow_entry_date"], workflow_entry_count=item["workflow_entry_count"],
            workflow_detail_count=item["workflow_detail_count"],
        ) for item in groups
    ]
    latest_record = client_records[0] if client_records else None

    latest_by_frequency: dict[str, _WorkflowRecord | None] = {}
    periods_by_frequency: dict[str, set[tuple[int, int]]] = defaultdict(set)
    counts_by_frequency = defaultdict(dict)
    for record in client_records:
        normalized_frequency = _normalize_frequency(record.frequency)
        if record.period_id:
            period_key = (record.period.year, record.period.month)
            periods_by_frequency[normalized_frequency].add(period_key)
            entries, details = counts_by_frequency[normalized_frequency].get(period_key, (0, 0))
            counts_by_frequency[normalized_frequency][period_key] = (entries + record.workflow_entry_count, details + record.workflow_detail_count)
        if normalized_frequency not in latest_by_frequency:
            latest_by_frequency[normalized_frequency] = record

    if not latest_by_frequency:
        latest_by_frequency[FinancialRecord.FREQUENCY_MONTHLY] = None

    schedule_items = [
        _build_workflow_schedule_item(
            bookkeeper=bookkeeper,
            client=client,
            frequency=frequency,
            latest_record=frequency_latest_record,
            recorded_periods=periods_by_frequency.get(frequency, set()),
            period_counts=counts_by_frequency.get(frequency, {}),
            reference_date=reference_date,
        )
        for frequency, frequency_latest_record in sorted(
            latest_by_frequency.items(),
            key=lambda item: _workflow_frequency_order(item[0]),
        )
    ]
    missing_items = [item for item in schedule_items if item["status"] == "missing"]
    ready_items = [item for item in schedule_items if item["status"] == "ready"]
    primary_item = missing_items[0] if missing_items else (ready_items[0] if ready_items else schedule_items[0])
    overall_status = "missing" if missing_items else ("ready" if ready_items and len(ready_items) == len(schedule_items) else "upcoming")

    latest_period_label = ""
    if latest_record and latest_record.period_id:
        latest_period_label = _format_period_label(
            latest_record.period.year,
            latest_record.period.month,
            latest_record.frequency,
        )

    return {
        "period_label": primary_item["period_label"],
        "period_year": primary_item["period_year"],
        "period_month": primary_item["period_month"],
        "frequency": primary_item["frequency"],
        "frequency_label": primary_item["frequency_label"],
        "schedule_label": "Mixed" if len(schedule_items) > 1 else primary_item["frequency_label"],
        "overall_status": overall_status,
        "schedule_items": schedule_items,
        "has_current_period_record": primary_item["has_record"],
        "current_period_entry_count": primary_item["entry_count"],
        "current_period_transaction_detail_count": primary_item["transaction_detail_count"],
        "has_any_records": latest_record is not None,
        "latest_entry_date": latest_record.entry_date.isoformat() if latest_record else "",
        "latest_period_label": latest_period_label,
        "email_available": bool(str(client.email or "").strip()),
        "permit_number_available": bool(str(client.permit_number or "").strip()),
        "orus_account_available": bool(str(client.orus_account or "").strip()),
        "report_ready": latest_record is not None,
    }


def _build_period_slots(
    reference_year: int,
    reference_month: int,
    frequency: str,
    count: int = 6,
) -> list[tuple[int, int, str]]:
    interval = _frequency_interval_months(frequency)
    slots: list[tuple[int, int, str]] = []
    starting_offset = -(count - 1) * interval

    for index in range(count):
        year, month = _shift_month(reference_year, reference_month, starting_offset + (index * interval))
        slots.append((year, month, _format_period_label(year, month, frequency)))

    return slots


def _build_monthly_projection_slots(
    reference_year: int,
    reference_month: int,
    count: int,
) -> list[tuple[int, int, str]]:
    slots: list[tuple[int, int, str]] = []
    horizon = max(int(count or 0), 1)

    for step in range(1, horizon + 1):
        year, month = _shift_month(reference_year, reference_month, step)
        slots.append((year, month, _format_period_label(year, month, FinancialRecord.FREQUENCY_MONTHLY)))

    return slots


def _period_key_for_line(line: FinancialRecordLine) -> tuple[int, int]:
    record = line.record
    if record.period_id:
        return record.period.year, record.period.month
    return record.entry_date.year, record.entry_date.month


def _normalize_frequency(value: str) -> str:
    return value if value in FREQUENCY_INTERVALS else FinancialRecord.FREQUENCY_MONTHLY


def _build_group_forecast_model(
    *,
    client_id: int,
    category: str,
    frequency: str,
    group_key: str,
    period_totals: dict[tuple[int, int], Decimal],
    forecast_through: tuple[int, int],
    fit_cache: dict | None = None,
) -> dict | None:
    key = (_normalize_frequency(frequency), tuple(sorted(period_totals.items())), forecast_through)
    if fit_cache is None or key not in fit_cache:
        model = build_sarima_forecast(
            period_totals=period_totals,
            frequency=_normalize_frequency(frequency),
            forecast_through=forecast_through,
        )
        if fit_cache is not None:
            fit_cache[key] = deepcopy(model)
    else:
        # Pure request-local reuse; each client's model metadata remains separate.
        model = deepcopy(fit_cache[key])
    if model is None:
        return None

    model.update({
        "client_id": client_id,
        "category": category,
        "group_key": group_key,
        "frequency": _normalize_frequency(frequency),
        "data_points": model["observation_count"],
        "uses_limited_data": model["status"] == "insufficient_history",
    })

    return model


def _project_group_value(
    model: dict,
    target_year: int,
    target_month: int,
) -> tuple[bool, Decimal | None, bool]:
    period_key = (target_year, target_month)
    if period_key not in model["scheduled_periods"]:
        return False, None, False
    if model["status"] not in FORECAST_READY_STATUSES:
        return True, None, True
    value = model["forecast_by_period"].get(period_key)
    return True, value, value is None


def _money_or_none(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return _to_money_number(value.quantize(Decimal("0.01")))


def _forecast_readiness_note(models: list[dict], period: tuple[int, int] | None = None) -> str:
    if not models:
        return "Not scheduled this period"

    unavailable_notes: list[str] = []
    for model in models:
        status = model.get("status")
        frequency = str(model.get("frequency") or "record").lower()
        if period is not None and rejected_prediction_note(model, period):
            unavailable_notes.append(rejected_prediction_note(model, period))
            continue
        if status in FORECAST_READY_STATUSES and (period is None or period in model['forecast_by_period']):
            continue
        if status == "insufficient_history":
            available = int(model.get("observation_count") or 0)
            required = int(model.get("minimum_observations") or 0)
            unavailable_notes.append(
                f"{available} of {required} {frequency} periods"
            )
        elif status == "irregular_history":
            unavailable_notes.append(f"Review missing {frequency} periods")
        elif status == "unsupported_frequency":
            unavailable_notes.append(f"{frequency.capitalize()} forecast unavailable")
        else:
            unavailable_notes.append("Forecast unavailable for this history")

    if not unavailable_notes:
        return FORECAST_METHOD_LABEL
    return "; ".join(dict.fromkeys(unavailable_notes))


def _resolve_forecast_context(bookkeeper, scope_client: Client | None, reference_date) -> tuple[str, int, int, int]:
    """Returns (frequency, reference_year, reference_month, period_count).
    period_count spans from the earliest record to the latest so the
    forecast can consider every available data point.
    """
    record_query = FinancialRecord.objects.filter(bookkeeper=bookkeeper)
    if scope_client is not None:
        record_query = record_query.filter(client=scope_client)

    latest_record = (
        record_query
        .select_related("period")
        .order_by("-entry_date", "-id")
        .first()
    )

    earliest_record = (
        record_query
        .select_related("period")
        .order_by("entry_date", "id")
        .first()
    )

    if scope_client is None:
        frequency = FinancialRecord.FREQUENCY_MONTHLY
    else:
        frequency = latest_record.frequency if latest_record else FinancialRecord.FREQUENCY_MONTHLY

    if latest_record and latest_record.period_id:
        reference_year = latest_record.period.year
        reference_month = latest_record.period.month
    elif latest_record:
        reference_year = latest_record.entry_date.year
        reference_month = latest_record.entry_date.month
    else:
        reference_year = reference_date.year
        reference_month = reference_date.month

    # Calculate how many periods span from earliest to latest
    if earliest_record and latest_record:
        if earliest_record.period_id:
            early_y, early_m = earliest_record.period.year, earliest_record.period.month
        else:
            early_y, early_m = earliest_record.entry_date.year, earliest_record.entry_date.month
        interval = _frequency_interval_months(frequency)
        total_months = (reference_year - early_y) * 12 + (reference_month - early_m)
        period_count = max((total_months // interval) + 1, 6)
    else:
        period_count = 6

    return frequency, reference_year, reference_month, period_count


def _build_predictive_forecast(
    *,
    lines: list[FinancialRecordLine],
    forecast_horizon: int = 3,
    reference_date: date | None = None,
) -> dict:
    safe_horizon = max(int(forecast_horizon or 3), 1)
    fallback_reference_date = reference_date or timezone.localdate()

    grouped_totals: dict[tuple[int, str, str, str], dict[tuple[int, int], Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0.00"))
    )
    actual_totals_by_period: dict[tuple[int, int], dict[str, Decimal]] = defaultdict(_empty_bucket)
    latest_period_key: tuple[int, int] | None = None
    prepared_lines: list[dict] = []

    for line in lines:
        record = line.record
        if not record:
            continue

        period_key = _period_key_for_line(line)
        if latest_period_key is None or period_key > latest_period_key:
            latest_period_key = period_key
        amount = line.amount or Decimal("0.00")
        category = _classify_line_item(line.type_code, line.description)
        frequency = _resolve_line_forecast_frequency(line, category)

        prepared_lines.append({
            "client_id": record.client_id,
            "period_key": period_key,
            "amount": amount,
            "category": category,
            "frequency": frequency,
        })
        actual_totals_by_period[period_key][category] += amount

    for item in prepared_lines:
        category = item["category"]
        frequency = item["frequency"]
        group_key = category
        grouped_totals[(
            item["client_id"],
            category,
            frequency,
            group_key,
        )][item["period_key"]] += item["amount"]

    if len(grouped_totals) > MAX_FORECAST_SERIES:
        raise WorkloadLimitExceeded("This forecast exceeds 60 series. Select one client or a narrower year range. No partial results were returned.")
    if any(len(totals) > MAX_FORECAST_OBSERVATIONS for totals in grouped_totals.values()):
        raise WorkloadLimitExceeded("This forecast exceeds 240 observations per series. Select a narrower year range. No historical values were truncated.")

    if latest_period_key is None:
        reference_year = fallback_reference_date.year
        reference_month = fallback_reference_date.month
        next_year, next_month = _shift_month(reference_year, reference_month, 1)
        return {
            "has_forecast": False,
            "frequency": FinancialRecord.FREQUENCY_MONTHLY,
            "frequency_label": _frequency_label(FinancialRecord.FREQUENCY_MONTHLY),
            "period_count": 0,
            "data_points": 0,
            "next_period_label": _format_period_label(next_year, next_month, FinancialRecord.FREQUENCY_MONTHLY),
            "message": "Forecast is unavailable until enough historical entries exist.",
            "sparkline": [],
        }

    reference_year, reference_month = latest_period_key
    projection_slots = _build_monthly_projection_slots(reference_year, reference_month, safe_horizon)
    forecast_through = (projection_slots[-1][0], projection_slots[-1][1])
    distinct_histories = {
        (key[2], tuple(sorted(totals.items()))) for key, totals in grouped_totals.items()
        if requires_sarima_fit(period_totals=totals, frequency=key[2], forecast_through=forecast_through)
    }
    if len(distinct_histories) > MAX_FORECAST_DISTINCT_FITS or sum(len(history) for _, history in distinct_histories) > MAX_FORECAST_FIT_OBSERVATIONS:
        raise WorkloadLimitExceeded(
            "This forecast exceeds the combined limit of 8 distinct fits or 960 observations across those fits. "
            "Select one client or a narrower year range. No partial results were returned."
        )

    models_by_category: dict[str, list[dict]] = {category: [] for category in FORECAST_CATEGORIES}
    frequencies = set()
    limited_data_used = False
    fit_cache = {}

    for (client_id, category, frequency, group_key), period_totals in grouped_totals.items():
        model = _build_group_forecast_model(
            client_id=client_id,
            category=category,
            frequency=frequency,
            group_key=group_key,
            period_totals=period_totals,
            forecast_through=forecast_through,
            fit_cache=fit_cache,
        )
        if model is None:
            continue

        models_by_category[category].append(model)
        frequencies.add(frequency)
        limited_data_used = limited_data_used or model["uses_limited_data"]

    frequency_forecasts = build_frequency_forecasts(
        models_by_category=models_by_category, grouped_totals=grouped_totals,
        projection_slots=projection_slots, readiness=_forecast_readiness_note,
    )
    monthly_net = {
        row['coverage_end']: row for section in frequency_forecasts if section['frequency'] == 'monthly'
        for row in section['future_projections']
    }
    future_projections: list[dict] = []
    for target_year, target_month, target_label in projection_slots:
        category_totals: dict[str, Decimal] = {}
        category_applicability: dict[str, bool] = {}
        category_has_values: dict[str, bool] = {}
        category_limited_data: dict[str, bool] = {}
        category_unreliable: dict[str, bool] = {}
        category_readiness_notes: dict[str, str] = {}

        for category in FORECAST_CATEGORIES:
            projected_total = Decimal("0.00")
            is_applicable = False
            scheduled_model_count = 0
            projected_model_count = 0
            uses_limited_data = False
            has_unreliable_projection = False
            scheduled_models: list[dict] = []

            for model in models_by_category[category]:
                is_scheduled, projected_value, is_unreliable = _project_group_value(
                    model,
                    target_year,
                    target_month,
                )
                if not is_scheduled:
                    continue

                is_applicable = True
                scheduled_model_count += 1
                scheduled_models.append(model)
                uses_limited_data = uses_limited_data or model["uses_limited_data"]
                has_unreliable_projection = has_unreliable_projection or is_unreliable
                if projected_value is None:
                    has_unreliable_projection = True
                    continue

                projected_model_count += 1
                projected_total += projected_value

            has_value = (
                scheduled_model_count > 0
                and projected_model_count == scheduled_model_count
                and not has_unreliable_projection
            )
            category_totals[category] = projected_total
            category_applicability[category] = is_applicable
            category_has_values[category] = has_value
            category_limited_data[category] = uses_limited_data
            category_unreliable[category] = has_unreliable_projection
            category_readiness_notes[category] = _forecast_readiness_note(scheduled_models, (target_year, target_month))

        # Compatibility rows retain category fields but never compare different
        # coverage lengths. The separate period views carry aligned quarterly net.
        aligned = monthly_net.get('%04d-%02d' % (target_year, target_month))
        aligned_net = aligned.get('expected_net') if aligned else None
        net_has_value = aligned_net is not None
        net_unreliable = not net_has_value

        future_projections.append({
            "period_label": target_label,
            "expected_sales": _money_or_none(category_totals["sales"] if category_has_values["sales"] else None),
            "expected_expenses": _money_or_none(category_totals["expenses"] if category_has_values["expenses"] else None),
            "expected_tax": _money_or_none(category_totals["tax"] if category_has_values["tax"] else None),
            "expected_sales_applicable": category_applicability["sales"],
            "expected_expenses_applicable": category_applicability["expenses"],
            "expected_tax_applicable": category_applicability["tax"],
            "sales_method": FORECAST_METHOD_LABEL if category_applicability["sales"] else "Not scheduled",
            "expenses_method": FORECAST_METHOD_LABEL if category_applicability["expenses"] else "Not scheduled",
            "tax_method": FORECAST_METHOD_LABEL if category_applicability["tax"] else "Not scheduled",
            "sales_limited_data": category_limited_data["sales"],
            "expenses_limited_data": category_limited_data["expenses"],
            "tax_limited_data": category_limited_data["tax"],
            "sales_unreliable": category_unreliable["sales"],
            "expenses_unreliable": category_unreliable["expenses"],
            "tax_unreliable": category_unreliable["tax"],
            "sales_readiness_note": category_readiness_notes["sales"],
            "expenses_readiness_note": category_readiness_notes["expenses"],
            "tax_readiness_note": category_readiness_notes["tax"],
            "expected_net_applicable": net_has_value,
            "expected_net_unreliable": net_unreliable,
            "expected_net": aligned_net,
            "net_readiness_note": aligned.get('net_readiness_note', '') if aligned else 'Use the quarterly comparison',
        })

    first_projection = future_projections[0] if future_projections else {}
    frequency_value = next(iter(frequencies)) if len(frequencies) == 1 else FORECAST_MIXED_FREQUENCY
    frequency_label = _frequency_label(frequency_value) if len(frequencies) == 1 else "Mixed Schedule"
    data_points = max(
        (model["data_points"] for category_models in models_by_category.values() for model in category_models),
        default=0,
    )
    basis = (
        "Forecast calculated using separate frequency-aware SARIMA (0,1,0)(0,1,0)s models for each client and financial category."
    )
    if limited_data_used:
        basis = f"{basis} {FORECAST_LIMITED_DATA_MESSAGE}"

    sparkline_values = []
    for period_key in sorted(actual_totals_by_period)[-6:]:
        totals = actual_totals_by_period[period_key]
        sparkline_values.append(totals["sales"] - totals["expenses"])
    sparkline_values.extend(
        Decimal(str(row["expected_net"]))
        for row in future_projections
        if row.get("expected_net") is not None
    )

    return {
        "has_forecast": any(
            row.get("expected_sales") is not None
            or row.get("expected_expenses") is not None
            or row.get("expected_tax") is not None
            for row in future_projections
        ),
        "frequency": frequency_value,
        "frequency_label": frequency_label,
        "period_count": data_points,
        "data_points": data_points,
        "next_period_label": first_projection.get("period_label", ""),
        "expected_sales": first_projection.get("expected_sales"),
        "expected_expenses": first_projection.get("expected_expenses"),
        "expected_tax": first_projection.get("expected_tax"),
        "expected_sales_applicable": first_projection.get("expected_sales_applicable", False),
        "expected_expenses_applicable": first_projection.get("expected_expenses_applicable", False),
        "expected_tax_applicable": first_projection.get("expected_tax_applicable", False),
        "sales_method": first_projection.get("sales_method", "Not scheduled"),
        "expenses_method": first_projection.get("expenses_method", "Not scheduled"),
        "tax_method": first_projection.get("tax_method", "Not scheduled"),
        "sales_limited_data": first_projection.get("sales_limited_data", False),
        "expenses_limited_data": first_projection.get("expenses_limited_data", False),
        "tax_limited_data": first_projection.get("tax_limited_data", False),
        "sales_unreliable": first_projection.get("sales_unreliable", False),
        "expenses_unreliable": first_projection.get("expenses_unreliable", False),
        "tax_unreliable": first_projection.get("tax_unreliable", False),
        "sales_readiness_note": first_projection.get("sales_readiness_note", "Needs historical data"),
        "expenses_readiness_note": first_projection.get("expenses_readiness_note", "Needs historical data"),
        "tax_readiness_note": first_projection.get("tax_readiness_note", "Needs historical data"),
        "expected_net_applicable": first_projection.get("expected_net_applicable", False),
        "expected_net_unreliable": first_projection.get("expected_net_unreliable", False),
        "expected_net": first_projection.get("expected_net"),
        "basis": basis,
        "future_projections": future_projections,
        "frequency_forecasts": frequency_forecasts,
        "sparkline": [_to_money_number(value) for value in sparkline_values],
    }


def get_analytics_year_options(bookkeeper, client_id: int | None = None) -> dict:
    """Read lightweight, owner-scoped period years without loading records/lines."""
    current_year = timezone.localdate().year
    records = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client__bookkeeper=bookkeeper)
    if client_id is not None:
        records = records.filter(client_id=client_id)
    recorded_years = records.order_by().values_list("period__year", flat=True).distinct()
    return {
        "analytics_years": sorted({current_year, *recorded_years}, reverse=True),
        "analytics_current_year": current_year,
    }


def get_analytics_summary_for_bookkeeper(
    bookkeeper,
    client_id: int | None = None,
    year_filter: str | None = None,
    horizon: int = 3,
) -> dict:
    from safebooks.services.client_service import resolve_client_remarks, with_status_activity
    horizon = normalize_forecast_horizon(horizon)
    if horizon is None:
        return {"ok": False, "message": "Forecast horizon must be between 1 and 12 months.", "errors": ["Forecast horizon must be between 1 and 12 months."]}
    today = timezone.localdate()
    all_clients = list(
        with_status_activity(Client.objects.filter(bookkeeper=bookkeeper), today=today)
        .defer("email_password", "orus_password", "custom_fields")
        .order_by("client_name", "id")
    )
    for client in all_clients:
        client.remarks = resolve_client_remarks(client, today=today)

    available_clients = [
        {
            "id": client.id,
            "client_name": client.client_name,
            "tin_number": client.tin_number,
            "trade_name": client.trade_name,
        }
        for client in all_clients
    ]

    def limit_response(error):
        # Directory-safe metadata lets the browser narrow a failed All Clients
        # request. Never attach partial summaries, histories, or forecasts.
        return {**workload_error(str(error)), "available_clients": available_clients}

    scope_client = None
    if client_id is not None:
        scope_client = next((client for client in all_clients if client.id == client_id), None)
        if scope_client is None:
            return {
                "ok": False,
                "message": "Client not found.",
                "errors": ["Client not found."],
            }

    recent_slots = _recent_month_slots(today, count=6)
    # An explicit year is a calendar-year view, not today's rolling window.
    month_slots = (
        [(int(year_filter), month, MONTH_SHORT_NAMES[month]) for month in range(1, 13)]
        if year_filter and year_filter.isdigit() else recent_slots
    )
    slot_keys = [(year, month) for year, month, _ in month_slots]
    recent_net_totals = {(year, month): Decimal("0.00") for year, month, _ in recent_slots}

    base_lines_query = FinancialRecordLine.objects.filter(
        record__bookkeeper=bookkeeper,
        record__client__bookkeeper=bookkeeper,
    )
    if scope_client is not None:
        base_lines_query = base_lines_query.filter(record__client=scope_client)
        
    selected_year = int(year_filter) if year_filter and year_filter.isdigit() else None
    if selected_year is not None:
        # Train on earlier years too, but never use later-year observations to
        # forecast an earlier selection. Descriptive totals stay year-specific.
        base_lines_query = base_lines_query.filter(record__period__year__lte=selected_year)

    record_scope = FinancialRecord.objects.filter(bookkeeper=bookkeeper, client__bookkeeper=bookkeeper)
    if scope_client is not None:
        record_scope = record_scope.filter(client=scope_client)
    if selected_year is not None:
        record_scope = record_scope.filter(period__year__lte=selected_year)
    try:
        bounded_list(record_scope.values_list("pk", flat=True), MAX_RECORDS, "records")
        history_lines = bounded_list(
            base_lines_query.select_related("record", "record__period").defer("record__notes"),
            MAX_TRANSACTION_DETAILS, "transaction details",
        )
        if len({line.record_id for line in history_lines}) > MAX_RECORDS:
            raise WorkloadLimitExceeded("This request exceeds 5,000 records. Select one client or a narrower year range. No partial results were returned.")
    except WorkloadLimitExceeded as error:
        return limit_response(error)

    all_lines = (
        [line for line in history_lines if line.record.period.year == selected_year]
        if selected_year is not None else history_lines
    )
    recent_lines = [line for line in all_lines if (line.record.period.year, line.record.period.month) in slot_keys]

    monthly_totals = {key: _empty_bucket() for key in slot_keys}
    monthly_type_totals = {key: defaultdict(lambda: Decimal("0.00")) for key in slot_keys}
    monthly_net_totals = {key: Decimal("0.00") for key in slot_keys}
    grand_totals = _empty_bucket()
    total_net_value = Decimal("0.00")
    client_sales_totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    type_label_map: dict[str, str] = {}
    type_category_map: dict[str, str] = {}
    tax_type_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    tax_type_labels: dict[str, str] = {}

    for line in all_lines:
        amount = line.amount or Decimal("0.00")
        category = _classify_line_item(line.type_code, line.description)
        grand_totals[category] += amount
        if category == "tax":
            tax_key = _normalize_type_code_key(line.type_code) or "other-tax"
            tax_type_totals[tax_key] += amount
            tax_type_labels.setdefault(tax_key, _normalize_type_code_label(line.type_code) or "Other tax")
        # Keep the existing legacy forecast's six-month input independent of
        # the chart window. SARIMA uses the separately bounded history below.
        period_key = (line.record.period.year, line.record.period.month)
        if period_key in recent_net_totals:
            if category == "sales":
                recent_net_totals[period_key] += amount
            elif category == "expenses":
                recent_net_totals[period_key] -= amount

        if category == "sales":
            client_sales_totals[line.record.client_id] += amount

    for line in recent_lines:
        amount = line.amount or Decimal("0.00")
        category = _classify_line_item(line.type_code, line.description)
        month_key = (line.record.period.year, line.record.period.month)

        if month_key in monthly_totals:
            monthly_totals[month_key][category] += amount

            type_label = _normalize_type_code_label(line.type_code)
            if type_label:
                type_key = _normalize_type_code_key(line.type_code)
                monthly_type_totals[month_key][type_key] += amount
                if type_key not in type_label_map:
                    type_label_map[type_key] = type_label
                if type_key not in type_category_map:
                    type_category_map[type_key] = category



    for month_key, totals in monthly_totals.items():
        monthly_net_totals[month_key] = totals["sales"] - totals["expenses"]

    total_net_value = grand_totals["sales"] - grand_totals["expenses"]

    category_priority = {
        "sales": 1,
        "expenses": 2,
        "tax": 3,
    }
    type_pairs = sorted(
        type_label_map.items(),
        key=lambda item: (
            category_priority.get(type_category_map.get(item[0], "sales"), 1),
            item[1].lower()
        )
    )
    type_columns = [label for _, label in type_pairs]

    monthly_trend = []
    for year, month, month_label in month_slots:
        totals = monthly_totals[(year, month)]
        net_value = monthly_net_totals[(year, month)]

        type_breakdown = {
            label: _to_money_number(monthly_type_totals[(year, month)].get(type_key, Decimal("0.00")))
            for type_key, label in type_pairs
        }

        monthly_trend.append(
            {
                "year": year,
                "month": month,
                "month_label": month_label,
                "sales": _to_money_number(totals["sales"]),
                "expenses": _to_money_number(totals["expenses"]),
                "tax": _to_money_number(totals["tax"]),
                "net_value": _to_money_number(net_value),
                "type_breakdown": type_breakdown,
            }
        )

    summary = {
        "total_sales": _to_money_number(grand_totals["sales"]),
        "total_expenses": _to_money_number(grand_totals["expenses"]),
        "total_tax": _to_money_number(grand_totals["tax"]),
        "net_value": _to_money_number(total_net_value),
    }

    comparison = []
    if scope_client is None:
        for client in all_clients:
            total_sales = client_sales_totals.get(client.id, Decimal("0.00"))
            if total_sales <= 0:
                continue

            level = client.remarks if client.remarks in REMARK_TO_LABEL else Client.REMARK_NEW
            comparison.append(
                {
                    "client_id": client.id,
                    "client_name": client.client_name,
                    "total_sales": _to_money_number(total_sales),
                    "remarks": level,
                    "remarks_label": REMARK_TO_LABEL[level],
                }
            )

        comparison.sort(key=lambda item: item["total_sales"], reverse=True)

    has_data = any(value > 0 for value in summary.values())

    remarks_insight = _build_remarks_insight(scope_client, all_clients)
    forecast = _build_forecast_from_monthly_net(list(recent_net_totals.values()) if has_data else [])
    try:
        predictive_forecast = _build_predictive_forecast(
            lines=history_lines, forecast_horizon=horizon, reference_date=today,
        )
        history_periods = {(line.record.period.year, line.record.period.month) for line in history_lines}
        predictive_forecast.update({
            "history_start": "%04d-%02d" % min(history_periods) if history_periods else None,
            "history_end": "%04d-%02d" % max(history_periods) if history_periods else None,
            "history_cutoff_year": selected_year,
        })
        client_workflow = _build_client_workflow_status(scope_client, bookkeeper, today)
    except WorkloadLimitExceeded as error:
        return limit_response(error)

    return {
        "ok": True,
        "scope": {
            "is_all": scope_client is None,
            "client_id": scope_client.id if scope_client is not None else None,
            "client_name": scope_client.client_name if scope_client is not None else "All Clients",
            "client_tin": scope_client.tin_number if scope_client is not None else "",
            "client_trade_name": scope_client.trade_name if scope_client is not None else "",
        },
        "available_clients": available_clients,
        "type_columns": type_columns,
        "has_data": has_data,
        "summary": summary,
        "tax_breakdown": [
            {"type_code": tax_type_labels[key], "amount": _to_money_number(amount)}
            for key, amount in sorted(tax_type_totals.items(), key=lambda item: (-item[1], tax_type_labels[item[0]].lower()))
        ],
        "tax_breakdown_year": selected_year,
        "client_workflow": client_workflow,
        "monthly_trend": monthly_trend,
        "remarks_insight": remarks_insight,
        "forecast": forecast,
        "predictive_forecast": predictive_forecast,
        "comparison": comparison,
    }
