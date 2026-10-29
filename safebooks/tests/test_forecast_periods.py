"""Period-alignment regression tests, using only disposable synthetic records."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from safebooks.services import forecasting_service
from safebooks.services import analytics_service as analytics
from safebooks.services.forecast_period_service import build_frequency_forecasts
from safebooks.tests.test_forecast_year_history import ForecastYearHistoryTests as Fixtures


class ForecastPeriodTests(TestCase):
    _create_bookkeeper = Fixtures._create_bookkeeper
    _login_as = Fixtures._login_as
    _build_tin = Fixtures._build_tin
    _create_client = Fixtures._create_client
    _create_record_with_lines = Fixtures._create_record_with_lines
    setUp = Fixtures.setUp
    record = Fixtures.record
    monthly_history = Fixtures.monthly_history
    read = Fixtures.read
    snapshot = Fixtures.snapshot

    def test_line_coverage_keeps_monthly_sales_and_quarterly_expenses_separate(self):
        from safebooks.models import FinancialRecordLine
        for index in range(24):
            year, zero_month = divmod(2024 * 12 + index, 12)
            month = zero_month + 1
            lines = [("SALES", "Sales", Decimal(1000 + index * 10))]
            if month % 3 == 0:
                lines.append(("EXPENSES", "Expenses", Decimal(200 + index)))
            record = self.record(year, month, lines, "monthly")
            for line in record.line_items.all():
                line.coverage_frequency = "monthly" if line.type_code == "SALES" else "quarterly"
                line.save(update_fields=["coverage_frequency"])
        before = self.snapshot()
        with patch.object(analytics, 'build_sarima_forecast', wraps=analytics.build_sarima_forecast) as builder:
            payload = self.read(year="2025", horizon=3)
        histories = {call.kwargs['frequency']: call.kwargs['period_totals'] for call in builder.call_args_list}
        self.assertEqual(len(histories['monthly']), 24)
        self.assertEqual(len(histories['quarterly']), 8)
        self.assertEqual(set(month for year, month in histories['quarterly']), {3, 6, 9, 12})
        sections = {item['frequency']: item for item in payload['predictive_forecast']['frequency_forecasts']}
        self.assertIsNotNone(sections['monthly']['future_projections'][0]['expected_sales'])
        self.assertIsNotNone(sections['quarterly']['future_projections'][0]['expected_expenses'])
        quarter = sections['quarterly']['future_projections'][0]
        self.assertAlmostEqual(quarter['expected_net'], quarter['expected_sales'] - quarter['expected_expenses'], places=2)
        with patch.object(analytics, '_build_workflow_schedule_item', wraps=analytics._build_workflow_schedule_item) as schedule_builder:
            workflow = analytics._build_client_workflow_status(self.ledger, self.owner, date(2025, 12, 15))
        counts = {call.kwargs['frequency']: call.kwargs['period_counts'] for call in schedule_builder.call_args_list}
        self.assertEqual(counts['monthly'][(2025, 12)], (1, 1))
        self.assertEqual(counts['quarterly'][(2025, 12)], (1, 1))
        schedules = {item['frequency']: item for item in workflow['schedule_items']}
        self.assertEqual(set(schedules), {'monthly', 'quarterly'})
        self.assertEqual(schedules['monthly']['entry_count'], 1)
        self.assertEqual(schedules['monthly']['transaction_detail_count'], 1)
        self.assertEqual(schedules['quarterly']['period_month'], 3)
        self.assertEqual(schedules['quarterly']['entry_count'], 0)
        self.assertEqual(before, self.snapshot(), 'Reads must never rewrite coverage or financial data')
        # Removing one synthetic quarter must retain the original eight-quarter minimum.
        FinancialRecordLine.objects.filter(record__period__year=2024, record__period__month=3, type_code='EXPENSES').delete()
        with patch.object(analytics, 'build_sarima_forecast', wraps=analytics.build_sarima_forecast) as builder:
            payload = self.read(year="2025", horizon=3)
        quarter_section = next(section for section in payload['predictive_forecast']['frequency_forecasts'] if section['frequency'] == 'quarterly')
        self.assertIsNone(quarter_section['future_projections'][0]['expected_expenses'])

    def quarterly_history(self, *, missing=None, start_month=3):
        for index in range(11):
            year, zero_month = divmod(2024 * 12 + start_month - 1 + index * 3, 12)
            if (year, zero_month + 1) == missing:
                continue
            self.record(year, zero_month + 1,
                [('EXPENSES', 'Quarterly expense', Decimal(200 + index * 5)),
                 ('2551Q', 'Quarterly tax', Decimal(20 + index))], 'quarterly')

    def sections(self, horizon=3):
        return {item['frequency']: item for item in self.read(horizon=horizon)['predictive_forecast']['frequency_forecasts']}

    def test_monthly_sales_and_quarterly_expense_net_use_whole_quarter_without_more_fits(self):
        self.monthly_history(categories=False)
        self.quarterly_history()
        before = self.snapshot()
        with patch.object(forecasting_service, '_fit_sarima', wraps=forecasting_service._fit_sarima) as fit:
            sections = self.sections()
        self.assertEqual(fit.call_count, 3, 'Period views must reuse native fits')
        monthly = sections['monthly']['future_projections']
        self.assertEqual([row['period_label'] for row in monthly], ['Nov 2026', 'Dec 2026', 'Jan 2027'])
        self.assertTrue(all(row['expected_expenses'] is None for row in monthly))
        self.assertTrue(all(row['expected_net'] is None for row in monthly))
        quarter, = sections['quarterly']['future_projections']
        self.assertEqual(quarter['period_label'], 'Q4 2026 (Oct–Dec)')
        self.assertEqual((quarter['coverage_start'], quarter['coverage_end']), ('2026-10', '2026-12'))
        self.assertEqual(quarter['expected_sales'], 4020.0)  # Oct actual + Nov/Dec forecasts.
        self.assertEqual(quarter['expected_expenses'], 255.0)
        self.assertEqual(quarter['expected_tax'], 31.0)
        self.assertEqual(quarter['expected_net'], 3765.0)  # Tax is separate, as before.
        self.assertNotEqual(quarter['expected_net'], monthly[1]['expected_sales'] - quarter['expected_expenses'],
            'Never subtract full-quarter Expenses from December-only Sales')
        self.assertIn('actuals', quarter['sales_method'])
        self.assertEqual(before, self.snapshot())

    def test_short_monthly_components_do_not_hide_valid_quarterly_predictions(self):
        self.monthly_history(categories=False)
        self.quarterly_history()
        for month in (8, 9, 10):
            self.record(2026, month, [('EXPENSES', 'Monthly expense', Decimal(10)),
                                      ('0619E', 'Monthly tax', Decimal(2))])
        sections = self.sections()
        monthly = sections['monthly']['future_projections'][0]
        self.assertIsNone(monthly['expected_expenses'])
        self.assertEqual(monthly['expenses_readiness_note'], '3 of 24 monthly periods')
        quarterly = sections['quarterly']['future_projections'][0]
        self.assertEqual(quarterly['expected_expenses'], 255.0)
        self.assertEqual(quarterly['expected_tax'], 31.0)
        self.assertIsNone(quarterly['expected_net'], 'Never omit the required monthly expense component')
        self.assertIn('Expenses (monthly)', quarterly['net_readiness_note'])
        self.assertIn('3 of 24 monthly periods', quarterly['net_readiness_note'])
        self.assertIsNone(quarterly['net_expenses_basis'], 'Never expose a partial total as the full Net Value basis')

    def test_mixed_frequency_net_includes_all_recorded_components_when_complete(self):
        self.monthly_history()
        self.quarterly_history()
        before = self.snapshot()
        with patch.object(forecasting_service, '_fit_sarima', wraps=forecasting_service._fit_sarima) as fit:
            row = self.sections()['quarterly']['future_projections'][0]
        self.assertEqual(fit.call_count, 5, 'Combining components must not fit another model')
        self.assertEqual(row['expected_expenses'], 255.0, 'Native quarterly expense predictions remain independent')
        self.assertEqual(row['net_sales_basis'], 4020.0)
        self.assertEqual(row['net_expenses_basis'], 657.0)  # 133 actual + 134/135 monthly forecasts + 255 quarterly.
        self.assertEqual(row['expected_net'], 3363.0)
        self.assertIn('all recorded frequency components', row['net_readiness_note'])
        self.assertEqual(before, self.snapshot())

    def test_invalid_quarterly_tax_does_not_hide_later_valid_tax_or_block_net(self):
        self.monthly_history(categories=False)
        self.quarterly_history()
        before = self.snapshot()
        original_fit = forecasting_service._fit_sarima
        def fit(values, seasonal_period, steps):
            if seasonal_period == 4 and values[0] == 20:
                return [-5.0] + [99.0] * (steps - 1)
            return original_fit(values, seasonal_period, steps)
        with patch.object(forecasting_service, '_fit_sarima', side_effect=fit) as fitted:
            forecast = self.read(horizon=6)['predictive_forecast']
        self.assertEqual(fitted.call_count, 3)
        quarter = next(item for item in forecast['frequency_forecasts'] if item['frequency'] == 'quarterly')
        december, march = quarter['future_projections']
        self.assertIsNone(december['expected_tax'])
        self.assertEqual(december['tax_readiness_note'], 'Negative SARIMA prediction')
        self.assertEqual(december['expected_net'], 3765.0, 'Tax is not deducted from Net Value')
        self.assertEqual(march['expected_tax'], 99.0)
        self.assertEqual(march['tax_readiness_note'], 'SARIMA')
        compatibility = {row['period_label']: row for row in forecast['future_projections']}
        self.assertIsNone(compatibility['Dec 2026']['expected_tax'])
        self.assertEqual(compatibility['Mar 2027']['expected_tax'], 99.0)
        self.assertEqual(before, self.snapshot())

    def test_tax_labels_and_every_bir_choice_are_tax_but_keep_frequency_requirements(self):
        import re
        from pathlib import Path
        from types import SimpleNamespace
        from django.conf import settings
        source = (Path(settings.BASE_DIR) / 'templates/base/financial_records_client.html').read_text(encoding='utf-8')
        choices = re.findall(r'\{ code: "(BIR Form [^"]+)", desc: "([^"]+)" \}', source)
        self.assertGreater(len(choices), 20)
        for code, description in [('tax', 'sales adjustment'), ('TAXES', 'expense payment'), *choices]:
            with self.subTest(code=code):
                self.assertEqual(analytics._classify_line_item(code, description), 'tax')
        for frequency in ('monthly', 'quarterly', 'annually'):
            line = SimpleNamespace(type_code='TAXES', description='Tax payment', record=SimpleNamespace(frequency=frequency))
            self.assertEqual(analytics._resolve_line_forecast_frequency(line, 'tax'), frequency)

    def test_editing_listed_form_descriptions_cannot_retag_forecast_histories(self):
        from safebooks.models import FinancialRecordLine
        for index in range(24):
            year, zero_month = divmod(2024 * 12 + index, 12)
            month = zero_month + 1
            lines = [('Sales', 'Sales', Decimal(1000 + index * 10)),
                     ('BIR Form 0619E', 'TW', Decimal(2))]
            if month % 3 == 0:
                lines += [('Expenses', 'Expenses', Decimal(200 + index)),
                          ('BIR Form 1603', 'QR', Decimal(20)),
                          ('BIR Form 1601FQ', 'QR', Decimal(30)),
                          ('BIR Form 1602Qv2018', 'TW', Decimal(40)),
                          ('BIR Form 1702Qv2018C', 'PQ', Decimal(50))]
            if month == 12:
                lines += [('BIR Form 1702EXv2018C', 'Annual tax', Decimal(70))]
            record = self.record(year, month, lines)
            record.line_items.filter(type_code='Sales').update(coverage_frequency='monthly')
            record.line_items.filter(type_code='Expenses').update(coverage_frequency='quarterly')
        before_read = self.snapshot()
        with patch.object(analytics, 'build_sarima_forecast', wraps=analytics.build_sarima_forecast) as builder:
            original = self.read(year='2025', horizon=3)
        self.assertEqual(before_read, self.snapshot(), 'Forecast reads must not rewrite descriptions or frequencies')
        calls = [(call.kwargs['frequency'], len(call.kwargs['period_totals'])) for call in builder.call_args_list]
        self.assertEqual(sorted(calls), [('annually', 2), ('monthly', 24), ('monthly', 24), ('quarterly', 8), ('quarterly', 8)])
        # Deliberately edit only disposable test descriptions, as a bookkeeper can.
        FinancialRecordLine.objects.filter(type_code='BIR Form 0619E').update(description='Annual quarterly payment')
        FinancialRecordLine.objects.filter(type_code__in=['BIR Form 1603', 'BIR Form 1601FQ', 'BIR Form 1602Qv2018', 'BIR Form 1702Qv2018C']).update(description='Monthly payment')
        FinancialRecordLine.objects.filter(type_code='BIR Form 1702EXv2018C').update(description='TW')
        after_edit = self.snapshot()
        edited = self.read(year='2025', horizon=3)
        self.assertEqual(original['predictive_forecast'], edited['predictive_forecast'])
        self.assertEqual(after_edit, self.snapshot(), 'Only the explicit synthetic edits may change saved values')
        sections = {g['frequency']: g for g in edited['predictive_forecast']['frequency_forecasts']}
        self.assertTrue(all(row['expected_tax'] is not None for row in sections['monthly']['future_projections']))
        self.assertIsNotNone(sections['quarterly']['future_projections'][0]['expected_tax'])

    def test_worksheet_tax_schedule_keeps_valid_quarters_and_rejects_gapped_months(self):
        for index in range(36):
            year, zero_month = divmod(2024 * 12 + index, 12)
            month = zero_month + 1
            lines = [('Sales', 'Sales', Decimal(1000 + index * 10))]
            if month % 3:
                lines += [('BIR Form 0619E', 'TW', Decimal(50))]
            else:
                lines += [('Expenses', 'Expenses', Decimal(200 + index)),
                          ('BIR Form 1601EQ', 'TW', Decimal(100)),
                          ('BIR Form 2551Q', 'PQ', Decimal(200))]
            record = self.record(year, month, lines, 'monthly')
            record.line_items.filter(type_code='Sales').update(coverage_frequency='monthly')
            record.line_items.filter(type_code='Expenses').update(coverage_frequency='quarterly')
        before = self.snapshot()
        with patch.object(forecasting_service, '_fit_sarima', wraps=forecasting_service._fit_sarima) as fit:
            payload = self.read(year='2026', horizon=3)
        self.assertEqual(fit.call_count, 3, 'Gapped monthly Tax must not fit or consume extra fit work')
        sections = {g['frequency']: g for g in payload['predictive_forecast']['frequency_forecasts']}
        monthly = sections['monthly']['future_projections']
        self.assertTrue(all(row['expected_tax'] is None for row in monthly))
        self.assertIn('Review missing monthly periods', monthly[0]['tax_readiness_note'])
        quarter = sections['quarterly']['future_projections'][0]
        self.assertEqual(quarter['coverage_end'], '2027-03')
        self.assertEqual(quarter['expected_tax'], 300.0)
        self.assertIsNotNone(quarter['expected_expenses'])
        self.assertIsNotNone(quarter['expected_net'])
        self.assertEqual(before, self.snapshot())

    def test_net_may_be_negative_but_does_not_deduct_tax(self):
        for index in range(24):
            year, month = divmod(2024 * 12 + index, 12)
            self.record(year, month + 1, [('SALES', 'Sales', Decimal(100)),
                ('EXPENSES', 'Expenses', Decimal(200)), ('TAXES', 'Monthly tax', Decimal(25))])
        row = self.sections()['monthly']['future_projections'][0]
        self.assertEqual(row['expected_net'], -100.0)

    def test_quarterly_gaps_remain_quarterly_warnings_not_monthly_minimums(self):
        self.monthly_history(categories=False)
        self.quarterly_history(missing=(2024, 12))
        before = self.snapshot()
        row = self.sections()['quarterly']['future_projections'][0]
        self.assertIsNone(row['expected_expenses'])
        self.assertEqual(row['expenses_readiness_note'], 'Review missing quarterly periods')
        self.assertIsNone(row['expected_net'])
        self.assertEqual(before, self.snapshot())

    def test_monthly_only_keeps_values_and_one_month_net(self):
        self.monthly_history()
        sections = self.sections()
        self.assertEqual(set(sections), {'monthly'})
        row = sections['monthly']['future_projections'][0]
        self.assertEqual((row['expected_sales'], row['expected_expenses'], row['expected_net']), (1340.0, 134.0, 1206.0))

    def test_net_is_derived_from_matching_bases_not_fitted_as_a_category(self):
        self.monthly_history()
        self.quarterly_history()
        before = self.snapshot()
        with patch.object(analytics, '_build_group_forecast_model', wraps=analytics._build_group_forecast_model) as build:
            sections = self.sections(horizon=6)
        self.assertEqual({call.kwargs['category'] for call in build.call_args_list}, {'sales', 'expenses', 'tax'})
        for section in sections.values():
            for row in section['future_projections']:
                if row['expected_net'] is None:
                    continue
                sales = Decimal(str(row['net_sales_basis']))
                expenses = Decimal(str(row['net_expenses_basis']))
                self.assertEqual(Decimal(str(row['expected_net'])), sales - expenses)
        self.assertTrue(any(row['expected_net'] is not None for row in sections['quarterly']['future_projections']))
        self.assertEqual(before, self.snapshot())

    def test_enough_quarterly_points_with_gap_or_extra_off_cycle_period_stay_ineligible(self):
        self.monthly_history(categories=False)
        self.quarterly_history(missing=(2024, 12))
        self.record(2024, 12, [('EXPENSES', 'Monthly expense', Decimal(200))], 'monthly')
        self.record(2024, 12, [('TAXES', 'Quarterly tax', Decimal(20))], 'quarterly')
        self.record(2025, 1, [('TAXES', 'Quarterly tax', Decimal(21))], 'quarterly')
        before = self.snapshot()
        with patch.object(forecasting_service, '_fit_sarima', wraps=forecasting_service._fit_sarima) as fit:
            quarter = self.sections()['quarterly']['future_projections'][0]
        self.assertEqual(fit.call_count, 1, 'Only complete monthly sales may fit, regardless of quarterly point count')
        self.assertIsNone(quarter['expected_expenses'])
        self.assertIsNone(quarter['expected_tax'])
        self.assertIsNone(quarter['expected_net'])
        self.assertEqual(quarter['expenses_readiness_note'], 'Review missing quarterly periods')
        self.assertEqual(quarter['tax_readiness_note'], 'Review missing quarterly periods')
        self.assertEqual(before, self.snapshot(), 'Never retag monthly entries or discard off-cycle entries to force a fit')

    def test_missing_expense_history_is_not_assumed_to_be_zero(self):
        self.monthly_history(categories=False)
        row = self.sections()['monthly']['future_projections'][0]
        self.assertIsNone(row['expected_net'])
        self.assertIn('history required', row['net_readiness_note'])

    def test_quarterly_only_has_no_monthly_rows_and_uses_eight_quarter_minimum(self):
        for index in range(8):
            year, month0 = divmod(2024 * 12 + 2 + index * 3, 12)
            self.record(year, month0 + 1, [('SALES', 'Quarterly sales', Decimal(1000 + index * 10)),
                                          ('EXPENSES', 'Quarterly expense', Decimal(100 + index))], 'quarterly')
        sections = self.sections()
        self.assertEqual(set(sections), {'quarterly'})
        row = sections['quarterly']['future_projections'][0]
        self.assertEqual((row['expected_sales'], row['expected_expenses'], row['expected_net']), (1080.0, 108.0, 972.0))

    def test_horizon_is_calendar_months_and_crosses_year_without_changing_frequency(self):
        self.monthly_history(categories=False)
        self.quarterly_history()
        for horizon, count in ((3, 1), (6, 2), (12, 4)):
            with self.subTest(horizon=horizon):
                sections = self.sections(horizon)
                self.assertEqual(len(sections['monthly']['future_projections']), horizon)
                quarters = sections['quarterly']['future_projections']
                self.assertEqual(len(quarters), count)
                if count > 1:
                    self.assertEqual(quarters[1]['period_label'], 'Q1 2027 (Jan–Mar)')
                    self.assertEqual(quarters[1]['sales_method'], 'Three-month SARIMA total')

    def test_non_calendar_quarter_anchor_is_preserved(self):
        self.monthly_history(categories=False)
        self.quarterly_history(start_month=2)
        row = self.sections()['quarterly']['future_projections'][0]
        self.assertEqual((row['coverage_start'], row['coverage_end']), ('2026-09', '2026-11'))
        self.assertEqual(row['expected_sales'], 3990.0)
        self.assertEqual(row['expected_net'], 3735.0)

    def test_annual_history_stays_unsupported_and_does_not_create_monthly_net(self):
        self.monthly_history(categories=False)
        self.record(2026, 1, [('EXPENSES', 'Annual expense', Decimal(100))], 'annually')
        sections = self.sections()
        self.assertIn('Annual forecasting remains unsupported', sections['monthly']['coverage_note'])
        self.assertTrue(all(row['expected_net'] is None for row in sections['monthly']['future_projections']))

    def test_empty_calendar_horizon_explains_no_quarter_end_instead_of_fabricating_rows(self):
        self.monthly_history(categories=False)
        self.quarterly_history()
        section = self.sections(horizon=1)['quarterly']
        self.assertEqual(section['future_projections'], [])
        self.assertIn('longer horizon', section['coverage_note'])


class ForecastCoverageTests(SimpleTestCase):
    def test_all_clients_combined_methods_preserve_amounts_and_aligned_net_without_fitting(self):
        from copy import deepcopy
        months = [(2027, month) for month in (1, 2, 3)]
        models = {'sales': [], 'expenses': [], 'tax': []}
        totals = {}
        # Already-fitted synthetic models: this tests assembly, not SARIMA eligibility.
        for category, monthly_value, quarterly_value in [('sales', 100, 500), ('expenses', 10, 50), ('tax', 1, 5)]:
            for client, frequency, values in [
                (1, 'monthly', {period: Decimal(monthly_value) for period in months}),
                (2, 'quarterly', {months[-1]: Decimal(quarterly_value)}),
            ]:
                models[category].append({'client_id': client, 'frequency': frequency, 'status': 'forecast',
                    'scheduled_periods': set(values), 'forecast_by_period': values})
                totals[(client, category, frequency, category)] = {}
        before = deepcopy((models, totals))
        with patch.object(forecasting_service, '_fit_sarima') as fit:
            sections = build_frequency_forecasts(models_by_category=models, grouped_totals=totals,
                projection_slots=[(*period, '') for period in months], readiness=lambda _: 'SARIMA')
        fit.assert_not_called()
        monthly, quarterly = sections
        self.assertEqual(monthly['future_projections'][0]['expected_sales'], 100.0)
        quarter, = quarterly['future_projections']
        self.assertEqual((quarter['expected_sales'], quarter['expected_expenses'], quarter['expected_tax']), (800.0, 80.0, 8.0))
        self.assertEqual(quarter['sales_method'], 'Three-month SARIMA total; SARIMA')
        self.assertEqual((quarter['net_sales_basis'], quarter['net_expenses_basis'], quarter['expected_net']), (800.0, 80.0, 720.0))
        self.assertEqual((models, totals), before)

    def test_net_equals_the_displayed_two_decimal_bases(self):
        end = (2026, 1)
        models = {'sales': [], 'expenses': [], 'tax': []}
        totals = {}
        for category, value in [('sales', '100.006'), ('expenses', '50.004')]:
            models[category].append({'client_id': 1, 'frequency': 'monthly', 'status': 'forecast',
                'scheduled_periods': {end}, 'forecast_by_period': {end: Decimal(value)}})
            totals[(1, category, 'monthly', category)] = {}
        sections = build_frequency_forecasts(models_by_category=models, grouped_totals=totals,
            projection_slots=[(2026, 1, '')], readiness=lambda models: 'SARIMA')
        row = sections[0]['future_projections'][0]
        self.assertEqual((row['net_sales_basis'], row['net_expenses_basis'], row['expected_net']), (100.01, 50.0, 50.01))

    def build(self, *, missing_actual=False, missing_expense=False, offset_quarter=False):
        models = {'sales': [], 'expenses': [], 'tax': []}
        totals = {}
        months = [(2026, month) for month in (1, 2, 3)]
        for client in (1, 2):
            values = {period: Decimal(100 * client) for period in months}
            models['sales'].append({'client_id': client, 'frequency': 'monthly', 'status': 'forecast',
                'scheduled_periods': set(months), 'forecast_by_period': values})
            totals[(client, 'sales', 'monthly', 'sales')] = {} if missing_actual else {(2025, 12): Decimal(100 * client)}
            if client == 2 and missing_expense:
                continue
            end = (2026, 2) if client == 2 and offset_quarter else (2026, 3)
            models['expenses'].append({'client_id': client, 'frequency': 'quarterly', 'status': 'forecast',
                'scheduled_periods': {end}, 'forecast_by_period': {end: Decimal(50 + client)}})
            totals[(client, 'expenses', 'quarterly', 'expenses')] = {(2025, 12): Decimal(50)}
        result = build_frequency_forecasts(models_by_category=models, grouped_totals=totals,
            projection_slots=[(2026, month, '') for month in (1, 2, 3)], readiness=lambda values: 'SARIMA')
        return next(section for section in result if section['frequency'] == 'quarterly')

    def test_all_clients_net_requires_complete_coverage_for_every_client(self):
        row = self.build()['future_projections'][0]
        self.assertEqual((row['expected_sales'], row['expected_expenses'], row['expected_net']), (900.0, 103.0, 797.0))
        incomplete = self.build(missing_expense=True)['future_projections'][0]
        self.assertIsNone(incomplete['expected_net'])
        self.assertIn('history required', incomplete['net_readiness_note'])

    def test_different_quarter_anchors_are_not_combined_into_a_partial_total(self):
        rows = self.build(offset_quarter=True)['future_projections']
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['expected_expenses'] is None for row in rows))
        self.assertTrue(all(row['expected_net'] is None for row in rows))

    def test_missing_actual_month_cannot_be_replaced_by_zero_in_cross_year_quarter(self):
        rows = self.build(missing_actual=True, offset_quarter=True)['future_projections']
        february = next(row for row in rows if row['coverage_end'] == '2026-02')
        self.assertEqual(february['coverage_start'], '2025-12')
        self.assertIsNone(february['expected_sales'])
        self.assertIsNone(february['expected_net'])
