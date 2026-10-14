"""Initial synchronous work budgets; reject excess rather than return partial money."""
MAX_RECORDS = 5_000
MAX_TRANSACTION_DETAILS = 20_000
MAX_FORECAST_SERIES = 60
MAX_FORECAST_OBSERVATIONS = 240
MAX_FORECAST_HORIZON = 12
MAX_FORECAST_DISTINCT_FITS = 8
MAX_FORECAST_FIT_OBSERVATIONS = 960


class WorkloadLimitExceeded(ValueError):
    pass


def workload_error(message):
    return {"ok": False, "code": "workload_limit", "message": message, "errors": [message]}


def normalize_forecast_horizon(value):
    text = str(value).strip()
    if isinstance(value, bool) or not text.isascii() or not text.isdigit() or len(text) > 2:
        return None
    horizon = int(text)
    return horizon if 1 <= horizon <= MAX_FORECAST_HORIZON else None


def bounded_list(queryset, maximum, label):
    # Fetch one sentinel row. A separate count/check followed by an unbounded
    # fetch would still allow concurrent inserts to exceed the memory budget.
    rows = list(queryset[:maximum + 1])
    if len(rows) > maximum:
        raise WorkloadLimitExceeded(
            f"This request exceeds {maximum:,} {label}. Select one client or a narrower year/date/period range. No partial results were returned."
        )
    return rows
