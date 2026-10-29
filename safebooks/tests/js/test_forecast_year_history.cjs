/* Run both real template forecast handlers without browser or financial writes. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
for (const name of ['client_details', 'analytics']) {
    const source = fs.readFileSync(path.join(root, `templates/base/${name}.html`), 'utf8').replace(/\r\n/g, '\n');
    assert(source.includes('id="analyticsPredictiveHistory"'));
    assert(!source.includes('forecast_period_controls.html'));
    assert(!source.includes('analyticsForecastMonthly'));
    assert(!source.includes('analyticsForecastQuarterly'));
    const start = source.indexOf('        const formatForecastHistory =');
    const end = source.indexOf('        const predictiveForecastTableBody =', start);
    assert(start > 0 && end > start);
    const page = {
        analyticsPredictivePeriod: {}, analyticsPredictiveHistory: {},
        analyticsPredictiveSalesValue: {}, analyticsPredictiveExpensesValue: {}, analyticsPredictiveTaxValue: {},
        analyticsPredictiveSalesNote: {}, analyticsPredictiveExpensesNote: {}, analyticsPredictiveTaxNote: {},
        analyticsPredictivePlaceholder: {}, formatCurrency: value => `PHP ${value}`,
        formatProjectionCurrency: (model, key) => model[key] == null ? 'Cannot forecast' : `PHP ${model[key]}`,
        projectionHasValue: (model, key) => model[`${key}_applicable`] !== false && model[key] != null,
        getProjectionMethodLabel: () => 'SARIMA', renderPredictiveSparkline() {},
    };
    vm.createContext(page);
    vm.runInContext(source.slice(start, end) + '\nthis.format = formatForecastHistory; this.apply = applyPredictiveForecast;', page);
    const model = {has_forecast: true, history_start: '2024-01', history_end: '2026-10', history_cutoff_year: 2026,
        next_period_label: 'Nov 2026', frequency_label: 'Monthly', expected_sales: 1340, expected_expenses: 134, expected_tax: 13.4};
    const original = JSON.stringify(model);
    page.apply(model);
    assert.equal(page.analyticsPredictiveHistory.textContent, 'History: Jan 2024 to Oct 2026');
    assert.equal(page.analyticsPredictiveHistory.hidden, false);
    assert.equal(page.analyticsPredictivePeriod.textContent, 'Next period: Nov 2026 • Monthly');
    assert.equal(page.analyticsPredictiveSalesValue.textContent, 'PHP 1340');
    assert.equal(JSON.stringify(model), original, 'Display must not mutate forecasting data');
    page.apply({...model, sales_period_label: 'Nov 2026', expenses_period_label: 'Dec 2026 · Quarterly',
        expected_expenses: null, expenses_readiness_note: 'Review missing quarterly periods'});
    assert.equal(page.analyticsPredictiveSalesNote.textContent, 'Nov 2026');
    assert.equal(page.analyticsPredictiveExpensesNote.textContent, 'Dec 2026 · Quarterly · Review record periods');
    page.apply({...model, coverage_note: 'Quarterly', sparkline: [1340]});
    assert.equal(page.analyticsPredictivePlaceholder.textContent, 'One forecast period available.');
    page.apply({has_forecast: false, coverage_note: 'Quarterly', sparkline: []});
    assert.equal(page.analyticsPredictivePlaceholder.textContent, 'More complete history is needed.');
    page.apply({...model, history_end: '2025-12', history_cutoff_year: 2025, next_period_label: 'Jan 2026'});
    assert(page.analyticsPredictiveHistory.textContent.includes('Dec 2025'));
    assert(!page.analyticsPredictiveHistory.textContent.includes('Oct 2026'));
    page.apply({history_cutoff_year: 2023, has_forecast: false});
    assert.equal(page.analyticsPredictiveHistory.textContent, 'No history through 2023.');
    assert.equal(page.analyticsPredictiveSalesValue.textContent, 'PHP --');
    page.apply({has_forecast: false});
    assert.equal(page.analyticsPredictiveHistory.textContent, '');
    assert.equal(page.analyticsPredictiveHistory.hidden, true, 'Failures and old payloads must not retain stale history');
    assert.equal(page.format({history_start: '<script>', history_end: '2026-99', history_cutoff_year: '<script>'}), '');
    assert.equal(page.format({history_start: '2024-01', history_end: '2025-12'}), 'History: Jan 2024 to Dec 2025');
    // Parse the complete template's inline JavaScript after neutralizing Django tags.
    for (const match of source.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
        if (/application\/json|src\s*=/.test(match[1])) continue;
        const code = match[2].replace(/\{\{[\s\S]*?\}\}/g, '0').replace(/\{%[\s\S]*?%\}/g, '');
        new vm.Script(code, {filename: `${name}.html`});
    }
}
console.log('Forecast history UI tests passed: both templates, year cutoff, forecasts, missing history, legacy/failure cleanup and complete script syntax.');
