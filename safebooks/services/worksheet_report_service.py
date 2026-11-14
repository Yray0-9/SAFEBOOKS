"""Read-only worksheet comparisons over the already bounded report rows.

Amounts remain in their saved rows. Only Net Sales groups matching coverage;
no allocation, overlap inference, forecast fitting, or persistence happens here.
"""
from datetime import date
from decimal import Decimal

from .tax_form_frequency_service import standard_tax_form_frequency


_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_WIDTHS = {"monthly": 1, "quarterly": 3, "annually": 12}


def _category(row):
    """Classify by saved code for this worksheet, independent of SARIMA."""
    code = str(row.get("type_code") or "").strip().lower()
    if code in {"sales", "expenses"}:
        return code
    if standard_tax_form_frequency(code)[0] or code in {"tax", "taxes", "vat", "withholding", "wht"}:
        return "tax"
    return "custom"


def _period(index):
    year, month = divmod(index, 12)
    return f"{year:04d}-{month + 1:02d}"


def _coverage_label(start, end):
    year, month = divmod(start, 12)
    end_year, end_month = divmod(end, 12)
    if start == end:
        return f"{_MONTHS[month]} {year}"
    if year == end_year:
        return f"{_MONTHS[month]}–{_MONTHS[end_month]} {year}"
    return f"{_MONTHS[month]} {year}–{_MONTHS[end_month]} {end_year}"


def build_worksheet_net_sales(rows):
    """Calculate each disjoint comparison once, with Decimal and no extra reads.

    A broad saved coverage gathers every overlapping monthly/quarterly component,
    additively. Partial category coverage or crossing legacy anchors is withheld,
    never filled with zero. Entirely absent categories keep the existing worksheet
    sales-only/expenses-only semantics. Tax/supporting amounts are excluded.
    """
    observations = []
    for row in rows:
        category = _category(row)
        if category not in {"sales", "expenses"}:
            continue
        saved_date = date.fromisoformat(row["entry_date"])
        end = saved_date.year * 12 + saved_date.month - 1
        frequency = row.get("coverage_frequency") or row.get("frequency") or "monthly"
        width = _WIDTHS.get(frequency)
        observations.append({"category": category, "amount": Decimal(row["amount"]),
                             "start": end - (width or 1) + 1, "end": end, "supported": width is not None})

    # Intersecting coverage belongs to one comparison. Adjacent months remain
    # independent unless a saved broader amount explicitly connects them.
    groups = []
    for item in sorted(observations, key=lambda item: (item["start"], item["end"])):
        if groups and item["start"] <= groups[-1]["end"]:
            group = groups[-1]
            group["end"] = max(group["end"], item["end"])
            group["items"].append(item)
        else:
            groups.append({"start": item["start"], "end": item["end"], "items": [item]})

    periods, total, complete = {}, Decimal("0.00"), True
    for group in groups:
        start, end, items = group["start"], group["end"], group["items"]
        basis = {category: sum((item["amount"] for item in items if item["category"] == category), Decimal("0.00"))
                 for category in ("sales", "expenses")}
        reason = ""
        if not all(item["supported"] for item in items):
            reason = "Unsupported saved coverage"
        elif not any(item["start"] == start and item["end"] == end for item in items):
            reason = "Different covered periods"
        else:
            required = set(range(start, end + 1))
            for category in ("sales", "expenses"):
                category_items = [item for item in items if item["category"] == category]
                covered = {month for item in category_items for month in range(item["start"], item["end"] + 1)}
                if category_items and covered != required:
                    reason = f"Incomplete {category.capitalize()} coverage"
                    break
        net = (basis["sales"] - basis["expenses"]).quantize(Decimal("0.01")) if not reason else None
        if net is None:
            complete = False
        else:
            total += net
        metadata = {"coverage_start": _period(start), "coverage_end": _period(end),
                    "coverage_label": _coverage_label(start, end), "reason": reason,
                    "sales_basis": str(basis["sales"].quantize(Decimal("0.01"))),
                    "expenses_basis": str(basis["expenses"].quantize(Decimal("0.01")))}
        for month in {item["end"] for item in items}:
            periods[_period(month)] = {**metadata, "amount": str(net) if month == end and net is not None else None,
                                      "status": "incomplete" if reason else "calculated" if month == end else "covered"}
    return {"periods": periods, "total": str(total.quantize(Decimal("0.01"))) if groups and complete else None}
