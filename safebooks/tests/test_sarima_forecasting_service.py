from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from safebooks.services.forecasting_service import _fit_sarima, build_sarima_forecast


class SarimaForecastingServiceTests(SimpleTestCase):
    @staticmethod
    def _monthly_history(count=24):
        return {
            (2024 + (index // 12), (index % 12) + 1): Decimal(1000 + (index * 25))
            for index in range(count)
        }

    @staticmethod
    def _quarterly_history():
        periods = [
            (2024, 3),
            (2024, 6),
            (2024, 9),
            (2024, 12),
            (2025, 3),
            (2025, 6),
            (2025, 9),
            (2025, 12),
        ]
        return {
            period: Decimal(5000 + (index * 100))
            for index, period in enumerate(periods)
        }

    def test_monthly_history_generates_sarima_forecast(self):
        result = build_sarima_forecast(
            period_totals=self._monthly_history(),
            frequency="monthly",
            forecast_through=(2026, 3),
        )

        self.assertEqual(result["status"], "forecast")
        self.assertEqual(result["model_label"], "SARIMA (0,1,0)(0,1,0)[12]")
        self.assertEqual(result["observation_count"], 24)
        self.assertEqual(
            set(result["forecast_by_period"]),
            {(2026, 1), (2026, 2), (2026, 3)},
        )
        self.assertTrue(all(value >= 0 for value in result["forecast_by_period"].values()))

    def test_quarterly_history_uses_quarterly_seasonality(self):
        result = build_sarima_forecast(
            period_totals=self._quarterly_history(),
            frequency="quarterly",
            forecast_through=(2026, 12),
        )

        self.assertEqual(result["status"], "forecast")
        self.assertEqual(result["model_label"], "SARIMA (0,1,0)(0,1,0)[4]")
        self.assertEqual(
            set(result["forecast_by_period"]),
            {(2026, 3), (2026, 6), (2026, 9), (2026, 12)},
        )
        self.assertEqual(result["forecast_by_period"][(2026, 3)], Decimal("5800.0"))

    def test_quarterly_history_preserves_its_three_month_anchor(self):
        periods = [
            (2024, 1),
            (2024, 4),
            (2024, 7),
            (2024, 10),
            (2025, 1),
            (2025, 4),
            (2025, 7),
            (2025, 10),
        ]
        history = {
            period: Decimal(5000 + (index * 100))
            for index, period in enumerate(periods)
        }

        result = build_sarima_forecast(
            period_totals=history,
            frequency="quarterly",
            forecast_through=(2026, 10),
        )

        self.assertEqual(result["status"], "forecast")
        self.assertEqual(
            set(result["forecast_by_period"]),
            {(2026, 1), (2026, 4), (2026, 7), (2026, 10)},
        )
        self.assertEqual(result["forecast_by_period"][(2026, 1)], Decimal("5800.0"))

    def test_monthly_history_generates_twelve_numerically_correct_steps(self):
        result = build_sarima_forecast(
            period_totals=self._monthly_history(),
            frequency="monthly",
            forecast_through=(2026, 12),
        )

        self.assertEqual(result["status"], "forecast")
        self.assertEqual(len(result["forecast_by_period"]), 12)
        self.assertEqual(
            result["forecast_by_period"][(2026, 1)].quantize(Decimal("0.01")),
            Decimal("1600.00"),
        )
        self.assertEqual(
            result["forecast_by_period"][(2026, 12)].quantize(Decimal("0.01")),
            Decimal("1875.00"),
        )

    def test_short_history_is_not_replaced_with_another_algorithm(self):
        result = build_sarima_forecast(
            period_totals=self._monthly_history(count=23),
            frequency="monthly",
            forecast_through=(2026, 3),
        )

        self.assertEqual(result["status"], "insufficient_history")
        self.assertEqual(result["forecast_by_period"], {})
        self.assertEqual(result["observation_count"], 23)
        self.assertEqual(result["minimum_observations"], 24)
        self.assertEqual(result["remaining_observations"], 1)
        self.assertIn("24", result["message"])

    def test_seven_quarterly_observations_are_insufficient(self):
        history = self._quarterly_history()
        del history[(2025, 12)]

        result = build_sarima_forecast(
            period_totals=history,
            frequency="quarterly",
            forecast_through=(2026, 12),
        )

        self.assertEqual(result["status"], "insufficient_history")
        self.assertEqual(result["minimum_observations"], 8)
        self.assertEqual(result["remaining_observations"], 1)

    def test_irregular_history_is_not_silently_imputed(self):
        history = self._monthly_history()
        del history[(2024, 8)]

        result = build_sarima_forecast(
            period_totals=history,
            frequency="monthly",
            forecast_through=(2026, 3),
        )

        self.assertEqual(result["status"], "irregular_history")
        self.assertEqual(result["forecast_by_period"], {})

    def test_annual_history_is_explicitly_unsupported(self):
        result = build_sarima_forecast(
            period_totals={(2024, 1): Decimal("1000"), (2025, 1): Decimal("1200")},
            frequency="annually",
            forecast_through=(2027, 12),
        )

        self.assertEqual(result["status"], "unsupported_frequency")
        self.assertEqual(result["forecast_by_period"], {})

    @patch(
        "safebooks.services.forecasting_service._fit_sarima",
        return_value=[100.0, 110.0, 120.0],
    )
    def test_explicit_zero_is_an_observation_not_a_missing_period(self, mock_fit):
        history = self._monthly_history()
        history[(2024, 8)] = Decimal("0")

        result = build_sarima_forecast(
            period_totals=history,
            frequency="monthly",
            forecast_through=(2026, 3),
        )

        self.assertEqual(result["status"], "forecast")
        fitted_values = mock_fit.call_args.args[0]
        self.assertIn(0.0, fitted_values)
        self.assertEqual(len(fitted_values), 24)

    def test_non_finite_historical_value_is_rejected(self):
        history = self._monthly_history()
        history[(2024, 8)] = Decimal("NaN")

        result = build_sarima_forecast(
            period_totals=history,
            frequency="monthly",
            forecast_through=(2026, 3),
        )

        self.assertEqual(result["status"], "invalid_series")
        self.assertEqual(result["forecast_by_period"], {})

    @patch("safebooks.services.forecasting_service._fit_sarima", return_value=[-1.0])
    def test_negative_projection_is_rejected(self, _mock_fit):
        result = build_sarima_forecast(
            period_totals=self._monthly_history(),
            frequency="monthly",
            forecast_through=(2026, 1),
        )

        self.assertEqual(result["status"], "unreliable_result")
        self.assertEqual(result["forecast_by_period"], {})

    def test_non_finite_projection_is_rejected(self):
        for predicted_value in (float("nan"), float("inf")):
            with self.subTest(predicted_value=predicted_value):
                with patch(
                    "safebooks.services.forecasting_service._fit_sarima",
                    return_value=[predicted_value],
                ):
                    result = build_sarima_forecast(
                        period_totals=self._monthly_history(),
                        frequency="monthly",
                        forecast_through=(2026, 1),
                    )

                self.assertEqual(result["status"], "unreliable_result")
                self.assertEqual(result["forecast_by_period"], {})

    @patch("safebooks.services.forecasting_service._fit_sarima", side_effect=ValueError("fit failed"))
    def test_model_failure_returns_controlled_status(self, _mock_fit):
        result = build_sarima_forecast(
            period_totals=self._monthly_history(),
            frequency="monthly",
            forecast_through=(2026, 1),
        )

        self.assertEqual(result["status"], "model_error")
        self.assertEqual(result["forecast_by_period"], {})

    @patch("statsmodels.tsa.statespace.sarimax.SARIMAX")
    def test_nonconverged_model_is_rejected(self, mock_sarimax):
        fitted = mock_sarimax.return_value.fit.return_value
        fitted.mle_retvals = {"converged": False}
        fitted.get_forecast.return_value.predicted_mean = [Decimal("100")]

        with self.assertRaisesRegex(RuntimeError, "did not converge"):
            _fit_sarima([1000.0] * 24, seasonal_period=12, steps=1)

    @patch(
        "safebooks.services.forecasting_service._fit_sarima",
        return_value=[100.0],
    )
    def test_incomplete_projection_is_rejected(self, _mock_fit):
        result = build_sarima_forecast(
            period_totals=self._monthly_history(),
            frequency="monthly",
            forecast_through=(2026, 3),
        )

        self.assertEqual(result["status"], "model_error")
        self.assertEqual(result["forecast_by_period"], {})
        self.assertIn("incomplete", result["message"].lower())
