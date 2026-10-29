"""Description-independent schedules without editing any saved financial data."""
import re
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.test import SimpleTestCase

from safebooks.services import analytics_service as analytics
from safebooks.services.forecasting_service import FREQUENCY_CONFIG
from safebooks.services.tax_form_frequency_service import (
    TAX_FORM_FREQUENCIES, standard_tax_form_frequency,
)


class TaxFormFrequencyTests(SimpleTestCase):
    def line(self, code, description, frequency="monthly", coverage=None):
        return SimpleNamespace(type_code=code, description=description,
            coverage_frequency=coverage, record=SimpleNamespace(frequency=frequency))

    def test_every_offered_form_has_explicit_metadata_and_ignores_description(self):
        source = (Path(settings.BASE_DIR) / "templates/base/financial_records_client.html").read_text(encoding="utf-8")
        choices = re.findall(r'\{ code: "(BIR Form [^"]+)", desc: "([^"]+)" \}', source)
        self.assertGreater(len(choices), 60)
        for code, default_description in choices:
            recognized, expected = standard_tax_form_frequency(code)
            self.assertTrue(recognized, code)
            title_period = re.search(r"\b(monthly|quarterly|annual)\b", default_description, flags=re.I)
            if title_period:
                self.assertEqual(expected, {"monthly": "monthly", "quarterly": "quarterly", "annual": "annually"}[title_period[1].lower()], code)
            for description in (default_description, "TW", "PQ", "QR", "", "Monthly payment",
                                "Quarterly remittance", "Annual return", "2551Q 0619E 1701"):
                with self.subTest(code=code, description=description):
                    self.assertEqual(analytics._infer_tax_line_frequency(code, description), expected)
                    for parent in ("monthly", "quarterly", "annually"):
                        line = self.line(code, description, parent)
                        self.assertEqual(analytics._resolve_line_forecast_frequency(line, "tax"), expected or parent)

    def test_form_code_and_version_are_matched_exactly_with_common_formatting(self):
        for code, expected in (
            ("BIR Form 1601-EQ", "quarterly"), ("  bir FORM 0619-E  ", "monthly"),
            ("1603", "quarterly"), ("1603Q", "quarterly"),
            ("BIR Form 1602Qv2018", "quarterly"), ("1702Qv2018C", "quarterly"),
            ("1701-MS", "annually"), ("1702EXv2018C", "annually"),
            ("2000v2018", "monthly"), ("2000", None), ("2000OTv2018", None),
        ):
            with self.subTest(code=code):
                self.assertEqual(standard_tax_form_frequency(code), (True, expected))
        for unknown in ("1702Qv2099C", "1601EQ adjustment", "x1603", "", None, "Custom VAT fee"):
            self.assertEqual(standard_tax_form_frequency(unknown), (False, None))

    def test_custom_and_legacy_tax_inference_is_preserved(self):
        for code, description, parent, expected in (
            ("TAXES", "Tax payment", "quarterly", "quarterly"),
            ("Tax", "Quarterly tax", "monthly", "quarterly"),
            ("Custom tax", "Annual payment", "monthly", "annually"),
            ("Legacy withholding", "Monthly tax", "quarterly", "monthly"),
        ):
            self.assertEqual(analytics._resolve_line_forecast_frequency(self.line(code, description, parent), "tax"), expected)

    def test_explicit_amount_coverage_and_model_requirements_are_independent(self):
        for category in ("sales", "expenses"):
            self.assertEqual(analytics._resolve_line_forecast_frequency(
                self.line(category, "Annual tax", "monthly", "quarterly"), category), "quarterly")
            self.assertEqual(analytics._resolve_line_forecast_frequency(
                self.line(category, "Quarterly expense", "monthly"), category), "monthly")
        self.assertEqual(FREQUENCY_CONFIG["monthly"]["minimum_observations"], 24)
        self.assertEqual(FREQUENCY_CONFIG["quarterly"]["minimum_observations"], 8)
        self.assertNotIn("annually", FREQUENCY_CONFIG)
        self.assertEqual(set(TAX_FORM_FREQUENCIES.values()), {None, "monthly", "quarterly", "annually"})
