from __future__ import annotations

import math
import logging
import warnings
from decimal import Decimal, InvalidOperation


logger = logging.getLogger(__name__)

SARIMA_ORDER = (0, 1, 0)
SARIMA_OPTIMIZER = "powell"
SARIMA_MAX_ITERATIONS = 250
FREQUENCY_CONFIG = {
    "monthly": {"interval": 1, "seasonal_period": 12, "minimum_observations": 24},
    "quarterly": {"interval": 3, "seasonal_period": 4, "minimum_observations": 8},
}


def _shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    absolute_month = (year * 12) + (month - 1) + offset
    return absolute_month // 12, (absolute_month % 12) + 1


def _period_index(period: tuple[int, int]) -> int:
    return (period[0] * 12) + period[1]


def _next_period(period: tuple[int, int], frequency: str) -> tuple[int, int]:
    year, month = period
    if frequency == "quarterly":
        return _shift_month(year, month, 3)
    if frequency == "annually":
        return _shift_month(year, month, 12)
    return _shift_month(year, month, 1)


def _future_periods(
    last_period: tuple[int, int],
    frequency: str,
    forecast_through: tuple[int, int],
) -> list[tuple[int, int]]:
    periods: list[tuple[int, int]] = []
    current = last_period
    through_index = _period_index(forecast_through)

    for _ in range(240):
        current = _next_period(current, frequency)
        if _period_index(current) > through_index:
            break
        periods.append(current)

    return periods


def _model_label(seasonal_period: int) -> str:
    return f"SARIMA (0,1,0)(0,1,0)[{seasonal_period}]"


def _base_result(
    *,
    status: str,
    frequency: str,
    periods: list[tuple[int, int]],
    scheduled_periods: list[tuple[int, int]],
    message: str,
    seasonal_period: int | None = None,
) -> dict:
    return {
        "status": status,
        "frequency": frequency,
        "model_code": "sarima" if seasonal_period else "",
        "model_label": _model_label(seasonal_period) if seasonal_period else "Forecast unavailable",
        "order": SARIMA_ORDER if seasonal_period else None,
        "seasonal_order": (0, 1, 0, seasonal_period) if seasonal_period else None,
        "seasonal_period": seasonal_period,
        "history_start": periods[0] if periods else None,
        "history_end": periods[-1] if periods else None,
        "observation_count": len(periods),
        "scheduled_periods": set(scheduled_periods),
        "forecast_by_period": {},
        "message": message,
    }


def _validate_regular_periods(periods: list[tuple[int, int]], frequency: str) -> bool:
    if len(periods) < 2:
        return True

    expected = periods[0]
    for actual in periods[1:]:
        expected = _next_period(expected, frequency)
        if actual != expected:
            return False
    return True


def _fit_sarima(values: list[float], seasonal_period: int, steps: int) -> list[float]:
    from statsmodels.tools.sm_exceptions import ConvergenceWarning
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        fitted = SARIMAX(
            values,
            order=SARIMA_ORDER,
            seasonal_order=(0, 1, 0, seasonal_period),
            trend="n",
            simple_differencing=False,
        ).fit(
            disp=False,
            method=SARIMA_OPTIMIZER,
            maxiter=SARIMA_MAX_ITERATIONS,
        )
        predicted_mean = fitted.get_forecast(steps=steps).predicted_mean

    converged = bool(getattr(fitted, "mle_retvals", {}).get("converged", True))
    convergence_warnings = [
        warning
        for warning in captured_warnings
        if issubclass(warning.category, ConvergenceWarning)
    ]
    if not converged or convergence_warnings:
        raise RuntimeError("SARIMA optimization did not converge.")

    for warning in captured_warnings:
        logger.warning(
            "SARIMA emitted %s: %s",
            warning.category.__name__,
            warning.message,
        )

    predicted_values = [float(value) for value in predicted_mean]
    if len(predicted_values) != steps:
        raise RuntimeError(
            f"SARIMA returned {len(predicted_values)} forecast values for {steps} requested steps."
        )

    return predicted_values


def build_sarima_forecast(
    *,
    period_totals: dict[tuple[int, int], Decimal],
    frequency: str,
    forecast_through: tuple[int, int],
) -> dict | None:
    periods = sorted(period_totals)
    if not periods:
        return None

    scheduled_periods = _future_periods(periods[-1], frequency, forecast_through)
    config = FREQUENCY_CONFIG.get(frequency)
    if config is None:
        return _base_result(
            status="unsupported_frequency",
            frequency=frequency,
            periods=periods,
            scheduled_periods=scheduled_periods,
            message="SARIMA forecasting has not been evaluated for this record frequency.",
        )

    seasonal_period = config["seasonal_period"]
    result = _base_result(
        status="forecast",
        frequency=frequency,
        periods=periods,
        scheduled_periods=scheduled_periods,
        message="Forecast generated from regularly spaced historical records.",
        seasonal_period=seasonal_period,
    )
    result.update({
        "minimum_observations": config["minimum_observations"],
        "remaining_observations": max(
            config["minimum_observations"] - len(periods),
            0,
        ),
    })

    if not _validate_regular_periods(periods, frequency):
        result.update({
            "status": "irregular_history",
            "message": "Historical record periods are missing or are not regularly spaced.",
        })
        return result

    if len(periods) < config["minimum_observations"]:
        result.update({
            "status": "insufficient_history",
            "message": (
                f"At least {config['minimum_observations']} consecutive "
                f"{frequency} observations are required."
            ),
        })
        return result

    values: list[float] = []
    try:
        for period in periods:
            amount = Decimal(period_totals[period])
            if not amount.is_finite():
                raise InvalidOperation
            values.append(float(amount))
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        result.update({
            "status": "invalid_series",
            "message": "Historical values cannot be processed as a financial time series.",
        })
        return result

    if not scheduled_periods:
        return result

    try:
        predicted_values = _fit_sarima(values, seasonal_period, len(scheduled_periods))
    except Exception:
        logger.exception(
            "SARIMA fitting failed for %s history with %s observations.",
            frequency,
            len(values),
        )
        result.update({
            "status": "model_error",
            "message": "The SARIMA model could not produce a forecast for this history.",
        })
        return result

    if len(predicted_values) != len(scheduled_periods):
        logger.error(
            "SARIMA returned an incomplete forecast for %s history: expected %s values, received %s.",
            frequency,
            len(scheduled_periods),
            len(predicted_values),
        )
        result.update({
            "status": "model_error",
            "message": "The SARIMA model returned an incomplete forecast.",
        })
        return result

    if any(not math.isfinite(value) or value < 0 for value in predicted_values):
        result.update({
            "status": "unreliable_result",
            "message": "The SARIMA result was negative or non-finite and was not displayed.",
        })
        return result

    result["forecast_by_period"] = {
        period: Decimal(str(value))
        for period, value in zip(scheduled_periods, predicted_values)
    }
    return result
