"""Description-independent schedules without editing any saved financial data."""
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from safebooks.models import FinancialRecord, FinancialRecordLine, Period
from safebooks.services import analytics_service as analytics
from safebooks.services.forecasting_service import FREQUENCY_CONFIG
from safebooks.services.tax_form_frequency_service import (
    TAX_FORM_FREQUENCIES, standard_tax_form_frequency, standard_tax_form_frequency_pattern,
)
from safebooks.tests import test_query_growth as query_fixtures


class TaxFormFrequencyTests(SimpleTestCase):
    def test_grouped_lookup_patterns_match_the_exact_metadata_and_formatting(self):
        patterns = {frequency: re.compile(standard_tax_form_frequency_pattern(frequency), re.I)
                    for frequency in ("monthly", "quarterly", "annually")}
        for code, expected in TAX_FORM_FREQUENCIES.items():
            for formatted in (code, f" BIR FORM {code.upper()} ", f"BIR Form {'-'.join(code)}"):
                matches = [frequency for frequency, pattern in patterns.items() if pattern.search(formatted)]
                self.assertEqual(matches, [expected] if expected else [], formatted)
        for unknown in ("1702Qv2099C", "1601EQ adjustment", "x1603", "", "Custom VAT fee", "BIR-FORM2551Q"):
            self.assertFalse(any(pattern.search(unknown) for pattern in patterns.values()), unknown)

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


class TaxFormWorkflowTests(TestCase):
    setUp = query_fixtures.QueryGrowthTests.setUp
    make_client = query_fixtures.QueryGrowthTests.make_client

    def record(self, ledger, year, month, lines, parent="monthly"):
        period, _ = Period.objects.get_or_create(client=ledger, year=year, month=month)
        record = FinancialRecord.objects.create(bookkeeper=self.owner, client=ledger, period=period,
                                               entry_date=date(year, month, 1), frequency=parent, total_amount=len(lines))
        FinancialRecordLine.objects.bulk_create([
            FinancialRecordLine(record=record, type_code=code, description=description,
                                coverage_frequency=coverage, amount=1, sort_order=index)
            for index, (code, description, coverage) in enumerate(lines)
        ])
        return record

    def read_counts(self, ledger, year=None):
        with patch.object(analytics, '_build_workflow_schedule_item', wraps=analytics._build_workflow_schedule_item) as builder:
            workflow = analytics._build_client_workflow_status(ledger, self.owner, date(2026, 10, 30), year_filter=year)
        return workflow, {call.kwargs['frequency']: call.kwargs['period_counts'] for call in builder.call_args_list}

    def test_monthly_entries_include_quarter_end_forms_without_requiring_monthly_sales(self):
        ledger = self.make_client()
        for month in range(1, 10):
            lines = ([('SALES', 'Sales', 'quarterly'), ('BIR Form 1601EQ', 'TW', None), ('BIR Form 2551Q', 'PQ', None)]
                     if month % 3 == 0 else [('BIR Form 0619E', 'TW', None)])
            self.record(ledger, 2026, month, lines)
        before = (list(FinancialRecord.objects.values()), list(FinancialRecordLine.objects.values()))
        workflow, counts = self.read_counts(ledger, year=2026)
        monthly = next(item for item in workflow['schedule_items'] if item['frequency'] == 'monthly')
        self.assertEqual((monthly['period_month'], monthly['status']), (10, 'missing'))
        self.assertEqual(counts['monthly'][(2026, 3)], (1, 3))
        self.assertEqual(counts['quarterly'][(2026, 3)], (1, 3))
        self.assertEqual(before, (list(FinancialRecord.objects.values()), list(FinancialRecordLine.objects.values())))
        # No Sales at all in October is needed to acknowledge a saved tax entry.
        self.record(ledger, 2026, 10, [('BIR Form 1601E', 'TW', None), ('BIR Form 1601EQ', 'TW', None)])
        self.record(ledger, 2026, 10, [('BIR Form 1701', 'AIT', None)])
        workflow, counts = self.read_counts(ledger, year=2026)
        monthly = next(item for item in workflow['schedule_items'] if item['frequency'] == 'monthly')
        self.assertEqual((monthly['period_month'], monthly['status']), (10, 'ready'))
        self.assertEqual(counts['monthly'][(2026, 10)], (2, 3), 'Mixed-frequency entries must not be double counted')

    def test_calendar_entry_presence_retains_truly_empty_months_and_quarterly_only_clients(self):
        ledger = self.make_client()
        for month in (1, 2, 3, 4, 6):
            form = 'BIR Form 2551Q' if month % 3 == 0 else 'BIR Form 0619E'
            self.record(ledger, 2026, month, [(form, 'TW', None)])
        workflow, _ = self.read_counts(ledger, year=2026)
        monthly = next(item for item in workflow['schedule_items'] if item['frequency'] == 'monthly')
        self.assertEqual((monthly['period_month'], monthly['status']), (5, 'missing'))
        quarterly_only = self.make_client()
        self.record(quarterly_only, 2026, 3, [('BIR Form 2551Q', 'PQ', None)])
        workflow, _ = self.read_counts(quarterly_only, year=2026)
        self.assertEqual({item['frequency'] for item in workflow['schedule_items']}, {'quarterly'})

    def test_selected_year_status_excludes_other_years_and_stays_inside_completed_year(self):
        ledger = self.make_client()
        self.record(ledger, 2024, 3, [('BIR Form 2551Q', 'Older incomplete history', None)])
        for month in range(1, 13):
            lines = [('SALES', 'Sales', 'monthly')]
            if month % 3 == 0:
                lines.append(('BIR Form 2551Q', 'QP', None))
            if month == 1:
                lines.append(('BIR Form 1701', 'AIT', None))
            self.record(ledger, 2025, month, lines)
        self.record(ledger, 2026, 3, [('BIR Form 1701', 'Different saved month', None)])
        self.record(ledger, 2026, 9, [('SALES', 'Sales', 'monthly')])
        before = (list(FinancialRecord.objects.values()), list(FinancialRecordLine.objects.values()))
        workflow, counts = self.read_counts(ledger, year=2025)
        schedules = {item['frequency']: item for item in workflow['schedule_items']}
        self.assertEqual(set(schedules), {'monthly', 'quarterly', 'annually'})
        self.assertTrue(all(item['period_year'] == 2025 and item['status'] == 'ready' for item in schedules.values()))
        self.assertEqual(schedules['quarterly']['period_month'], 12)
        self.assertEqual(schedules['annually']['period_month'], 1)
        self.assertTrue(all(year == 2025 for frequency_counts in counts.values() for year, month in frequency_counts))
        self.assertEqual(workflow['latest_entry_date'], '2025-12-01')
        self.assertEqual(workflow['overall_status'], 'ready')
        self.assertEqual(before, (list(FinancialRecord.objects.values()), list(FinancialRecordLine.objects.values())))
        # Switching back uses today's month, never a simulated December cutoff.
        current, _ = self.read_counts(ledger, year=2026)
        monthly = next(item for item in current['schedule_items'] if item['frequency'] == 'monthly')
        self.assertEqual((monthly['period_year'], monthly['period_month'], monthly['status']), (2026, 10, 'missing'))

    def test_selected_year_retains_real_gaps_and_handles_empty_past_and_future_years(self):
        ledger = self.make_client()
        self.record(ledger, 2025, 3, [('BIR Form 2551Q', 'QP', None)])
        self.record(ledger, 2025, 9, [('BIR Form 2551Q', 'QP', None)])
        self.record(ledger, 2026, 6, [('BIR Form 2551Q', 'Does not fill 2025', None)])
        history, _ = self.read_counts(ledger, year=2025)
        quarter, = history['schedule_items']
        self.assertEqual((quarter['period_year'], quarter['period_month'], quarter['status']), (2025, 6, 'missing'))
        self.assertEqual(quarter['entry_count'], 0)
        for year, expected in ((2023, 'missing'), (2027, 'upcoming')):
            empty, _ = self.read_counts(ledger, year=year)
            self.assertEqual(empty['overall_status'], expected)
            self.assertFalse(empty['has_any_records'])
            self.assertEqual(empty['latest_entry_date'], '')
            self.assertTrue(all(item['period_year'] == year for item in empty['schedule_items']))
        self.record(ledger, 2027, 3, [('BIR Form 2551Q', 'Future saved form', None)])
        future, _ = self.read_counts(ledger, year=2027)
        saved_quarter, = future['schedule_items']
        self.assertTrue(saved_quarter['has_record'])
        self.assertFalse(saved_quarter['is_due_now'])

    def test_mixed_entry_counts_native_tax_schedules_and_separate_amount_coverage(self):
        ledger = self.make_client()
        self.record(ledger, 2026, 9, [
            ('SALES', 'Sales', 'monthly'), ('EXPENSES', 'Expenses', 'quarterly'),
            ('BIR Form 2551Q', 'Monthly wording cannot override this form', None),
            ('BIR Form 1701Q', 'QIT', None), ('BIR Form 1701Q', 'Another saved form line', None),
            ('BIR Form 1701', 'Monthly', None),
        ])
        _, counts = self.read_counts(ledger)
        self.assertEqual(counts['monthly'][(2026, 9)], (1, 6))
        self.assertEqual(counts['quarterly'][(2026, 9)], (1, 4))
        self.assertEqual(counts['annually'][(2026, 9)], (1, 1))

    def test_completed_quarterly_form_history_no_longer_creates_false_backlog(self):
        ledger = self.make_client()
        for year in (2024, 2025, 2026):
            for month in (3, 6, 9, 12):
                if (year, month) > (2026, 9):
                    continue
                self.record(ledger, year, month, [('BIR Form 2551Q', 'QP', None), ('BIR Form 1701Q', 'QIT', None)])
        before = list(FinancialRecordLine.objects.values())
        records_before = list(FinancialRecord.objects.values())
        with patch.object(analytics, 'build_sarima_forecast') as fit:
            workflow, counts = self.read_counts(ledger)
        fit.assert_not_called()
        quarter, = workflow['schedule_items']
        self.assertEqual(quarter['frequency'], 'quarterly')
        self.assertEqual((quarter['period_year'], quarter['period_month']), (2026, 12))
        self.assertEqual(quarter['status'], 'upcoming')
        self.assertEqual(counts['quarterly'][(2025, 3)], (1, 2))
        self.assertEqual(list(FinancialRecordLine.objects.values()), before)
        self.assertEqual(list(FinancialRecord.objects.values()), records_before)

    def test_saved_anchors_versions_and_legacy_fallback_are_preserved(self):
        ledger = self.make_client()
        self.record(ledger, 2026, 10, [(' BIR FORM 1602-Q-v2018 ', 'TW', None)])
        self.record(ledger, 2026, 10, [('BIR Form 0605', 'Quarterly words do not fix an ambiguous form', None)])
        self.record(ledger, 2026, 10, [('BIR Form 1702Qv2099C', 'Unknown version', None)])
        self.record(ledger, 2026, 10, [('SALES', 'Sales', 'monthly')], parent='quarterly')
        self.record(ledger, 2026, 10, [('EXPENSES', 'Expenses', None)], parent='quarterly')
        _, counts = self.read_counts(ledger)
        self.assertEqual(counts['quarterly'][(2026, 10)], (2, 2), 'Do not shift a saved October anchor to December')
        self.assertEqual(counts['monthly'][(2026, 10)], (5, 5))
        self.assertNotIn((2026, 12), counts['quarterly'])

    def test_missing_quarter_and_other_owners_records_are_not_hidden(self):
        ledger = self.make_client()
        self.record(ledger, 2025, 3, [('BIR Form 2551Q', 'QP', None)])
        self.record(ledger, 2025, 9, [('BIR Form 2551Q', 'QP', None)])
        foreign = self.record(ledger, 2025, 6, [('BIR Form 2551Q', 'QP', None)])
        other = type(self.owner).objects.create(full_name='Synthetic Foreign', username='workflow_foreign',
                                               email='workflow-foreign@example.test', password_hash='unused', status='approved')
        FinancialRecord.objects.filter(pk=foreign.pk).update(bookkeeper=other)
        workflow, counts = self.read_counts(ledger)
        quarter, = workflow['schedule_items']
        self.assertEqual((quarter['period_year'], quarter['period_month']), (2025, 6))
        self.assertEqual(quarter['status'], 'missing')
        self.assertNotIn((2025, 6), counts['quarterly'])
