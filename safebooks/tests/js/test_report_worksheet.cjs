const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
const context = { window: {}, activeClientId: 1, reportClientProfile: { client_name: 'Sample client' } };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, 'static/js/reports_shared.js'), 'utf8'), context);
const template = fs.readFileSync(path.join(root, 'templates/base/financial_records_client.html'), 'utf8');
const extract = (start, end) => template.slice(template.indexOf(start), template.indexOf(end, template.indexOf(start)));
vm.runInContext(extract('        const classifyModalReportLine =', '        const getModalReportRowYear =')
    + extract('        const buildModalReportData =', '        const buildModalLedgerSheetHtml =')
    + '\nthis.build = buildModalReportData;', context);
const shared = context.window.SafeBooksReportsShared;
const payload = { rows: [
    { entry_date: '2026-03-01', type_code: 'Sales', description: 'Taxable sales', amount: '75000' },
    { entry_date: '2026-03-02', type_code: 'Expenses', description: 'Expenses', amount: '5000' },
    { entry_date: '2026-03-02', type_code: 'Expenses', description: 'Extra expense', amount: '1000' },
    { entry_date: '2026-03-03', type_code: 'BIR Form 0605', description: 'Payment Form', amount: '500',
        mict: '0.00', cogs_cos: null, income_payments_2307: '9000', tax_withheld: '180', notes: 'Paid 500' },
    { entry_date: '2026-03-03', type_code: '2551Q', description: 'PQ', amount: '2250', cogs_cos: '12500',
        notes: '<script>bad()</script>' },
    { entry_date: '2026-04-01', type_code: 'Expenses', description: 'Expenses', amount: '100' },
    { entry_date: '2025-12-31', type_code: 'Sales', description: 'Sales', amount: '1000000' },
] };
const before = JSON.stringify(payload);
const report = context.build(payload, '2026');
assert.equal(report.rows.length, 3); // March with its first form, second form, April without a form.
assert.equal(report.rows[0].period, 'Mar 2026');
assert.match(report.rows[0].sales, /75,000\.00/);
assert.match(report.rows[0].expenses, /6,000\.00/);
assert.match(report.rows[0].net_value, /69,000\.00/);
assert.match(report.rows[2].net_value, /-.*100\.00/);
assert.equal(report.rows[0].type_code, 'BIR Form 0605');
assert.equal(report.rows[0].description, 'Payment Form');
assert.equal(report.rows[0].cogs_cos, '');
assert.match(report.rows[0].mict, /0\.00/);
assert.match(report.rows[0].income_payments_2307, /9,000\.00/);
assert.match(report.rows[0].tax_withheld, /180\.00/);
assert.match(report.rows[0].tax_due, /500\.00/);
assert.equal(report.rows[0].remarks, 'Paid 500');
assert.equal(report.rows[1].type_code, '2551Q');
assert.equal(report.rows[1].mict, '');
assert.match(report.rows[1].cogs_cos, /12,500\.00/);
assert.equal(report.rows[1].sales, undefined);
assert.equal(report.rows[1].net_value, undefined);
assert.equal(report.rows[1].period, undefined);
assert.equal(report.rows[0].quarter, '1');
assert.equal(report.rows[1].quarter, '1');
assert.equal(report.rows[2].quarter, '2');
assert.equal(report.rows[2].type_code, undefined);
assert.deepEqual(Array.from(report.rowKinds), ['month', 'detail', 'month']);
assert.equal(JSON.stringify(payload), before, 'Preview must not mutate inputs');
assert.equal(context.build(payload, '2024').rows.length, 0);
assert.equal(context.build(payload, 'all').rows[0].period, 'Dec 2025');
assert.equal(context.build(payload, '2025').rows.length, 1);

// A zero-tax form still shares the month row. Supporting-only lines must not take its place.
const supportingPayload = { rows: [
    { entry_date: '2026-06-01', type_code: 'Sales', description: 'Saved sales label', amount: '100', mict: '0', notes: 'Monthly note' },
    { entry_date: '2026-06-01', type_code: 'Expenses', description: 'Expenses', amount: '25', notes: 'Monthly note' },
    { entry_date: '2026-06-02', type_code: 'BIR Form 0619E', description: 'TW', amount: '0', tax_withheld: '0', notes: 'Form note' },
    { entry_date: '2026-06-02', type_code: 'BIR Form 0619E', description: 'Second saved form', amount: '5', notes: 'Second note' },
    { entry_date: '2026-07-01', type_code: 'BIR Form 2551Q', description: 'PQ', amount: '50', notes: 'Tax-only month' },
] };
const supportingBefore = JSON.stringify(supportingPayload);
const supportingReport = context.build(supportingPayload, '2026');
assert.equal(supportingReport.rows.length, 4);
assert.equal(supportingReport.rows[0].type_code, 'BIR Form 0619E');
assert.match(supportingReport.rows[0].tax_due, /0\.00/);
assert.match(supportingReport.rows[0].tax_withheld, /0\.00/);
assert.match(supportingReport.rows[0].net_value, /75\.00/);
assert.equal(supportingReport.rows[0].remarks, 'Monthly note; Form note');
assert.equal(supportingReport.rows[1].type_code, 'Sales');
assert.match(supportingReport.rows[1].mict, /0\.00/);
assert.equal(supportingReport.rows[1].sales, undefined);
assert.equal(supportingReport.rows[2].description, 'Second saved form');
assert.equal(supportingReport.rows[2].remarks, 'Second note');
assert.equal(supportingReport.rows[2].period, undefined);
assert.equal(supportingReport.rows[3].period, 'Jul 2026');
assert.equal(supportingReport.rows[3].description, 'PQ');
assert.equal(supportingReport.rows[3].remarks, 'Tax-only month');
assert.equal(supportingReport.rows[3].sales, '');
assert.equal(supportingReport.rows[3].expenses, '');
assert.equal(supportingReport.rows[3].net_value, '');
assert.equal(JSON.stringify(supportingPayload), supportingBefore);

const render = (data) => shared.buildReportSheetHtml({
    table: { ...data, columns: data.columns.map(c => c.label), rows: data.rows.map(r => data.columns.map(c => r[c.key])), minRows: 0 },
    rowHint: '',
});
const html = render(report);

// Saved zeros stay numeric in data and calculations, but print as truly blank worksheet cells.
const blankAndZero = context.build({ rows: [
    { entry_date: '2026-01-01', type_code: 'BIR Form 0619E', description: 'TW', amount: '500' },
    { entry_date: '2026-02-01', type_code: 'Sales', description: 'Sales', amount: '0' },
    { entry_date: '2026-02-01', type_code: 'Expenses', description: 'Expenses', amount: 0 },
    { entry_date: '2026-03-01', type_code: 'Sales', description: 'Sales', amount: '100' },
    { entry_date: '2026-04-01', type_code: 'Expenses', description: 'Expenses', amount: '25' },
] }, '2026');
assert.deepEqual([blankAndZero.rows[0].sales, blankAndZero.rows[0].expenses, blankAndZero.rows[0].net_value], ['', '', '']);
for (const key of ['sales', 'expenses', 'net_value']) assert.match(blankAndZero.rows[1][key], /0\.00/);
const zeroDataBefore = JSON.stringify(blankAndZero);
const zeroMonthMarkup = Array.from(render(blankAndZero).matchAll(/<tr class="reports-worksheet-month-row">([\s\S]*?)<\/tr>/g))[1][1];
const zeroMonthCells = Array.from(zeroMonthMarkup.matchAll(/<td>(.*?)<\/td>/g), match => match[1]);
assert.equal(zeroMonthCells[4], '');
assert.equal(zeroMonthCells[6], '');
assert.equal(zeroMonthCells[8], '');
assert.equal(JSON.stringify(blankAndZero), zeroDataBefore);
assert.equal(blankAndZero.rows[2].expenses, '');
assert.match(blankAndZero.rows[2].net_value, /100\.00/);
assert.equal(blankAndZero.rows[3].sales, '');
assert.match(blankAndZero.rows[3].net_value, /-.*25\.00/);
const blankRowMarkup = render(blankAndZero).match(/<tr class="reports-worksheet-month-row">([\s\S]*?)<\/tr>/)[1];
const blankRowCells = Array.from(blankRowMarkup.matchAll(/<td>(.*?)<\/td>/g), match => match[1]);
assert.equal(blankRowCells[3], '1');
assert.equal(blankRowCells[4], '-');
assert.equal(blankRowCells[6], '-');
assert.equal(blankRowCells[8], '-');
assert.match(blankRowCells[11], /500\.00/);
const blankFooter = render(blankAndZero).match(/<tr class="reports-ledger-totals-row">([\s\S]*?)<\/tr>/)[1];
assert.match(blankFooter, /100\.00/);
assert.match(blankFooter, /25\.00/);
assert.match(blankFooter, /75\.00/);
assert.match(blankFooter, /500\.00/);
const taxOnly = context.build({ rows: [{ entry_date: '2026-11-01', type_code: 'BIR Form 0619E', description: 'TW', amount: '500' }] }, '2026');
assert(!render(taxOnly).includes('₱0.00'));

const allZeroReport = context.build({ rows: [
    { entry_date: '2026-01-01', type_code: 'Sales', description: 'Sales', amount: '0' },
    { entry_date: '2026-01-01', type_code: 'Expenses', description: 'Expenses', amount: '0' },
    { entry_date: '2026-01-01', type_code: 'BIR Form 0619E', description: '0', amount: '0', mict: '0', cogs_cos: '0', income_payments_2307: '0', tax_withheld: '0', remarks: '0' },
] }, '2026');
const allZeroHtml = render(allZeroReport);
assert(!allZeroHtml.includes('₱0.00'));
const allZeroMonth = allZeroHtml.match(/<tr class="reports-worksheet-month-row">([\s\S]*?)<\/tr>/)[1];
const allZeroCells = Array.from(allZeroMonth.matchAll(/<td>(.*?)<\/td>/g), match => match[1]);
for (let index = 4; index <= 11; index++) assert.equal(allZeroCells[index], '', 'Every zero monetary column should print blank');
assert.equal(allZeroCells[1], '0', 'Do not suppress descriptions or remarks containing zero');
assert.equal(allZeroCells[12], '0');
assert.equal(allZeroCells[3], '1');
const allZeroFooter = allZeroHtml.match(/<tr class="reports-ledger-totals-row">([\s\S]*?)<\/tr>/)[1];
assert(!allZeroFooter.includes('0.00'));
assert(shared.buildReportSheetHtml({ table: { columns: ['Period', 'Sales'], rows: [['Jan 2026', '₱0.00']], minRows: 0 } }).includes('₱0.00'), 'Other report layouts must retain their existing zero display');

const mixedRemarks = context.build({ rows: [
    { entry_date: '2026-10-25', type_code: 'Sales', description: 'Sales', amount: '1000', notes: 'Entry note' },
    { entry_date: '2026-10-25', type_code: 'BIR Form 0619E', description: 'TW', amount: '500', remarks: 'Paid', notes: 'Entry note' },
    { entry_date: '2026-10-25', type_code: 'BIR Form 2551Q', description: 'PQ', amount: '500', remarks: 'Pending for payment', notes: 'Entry note' },
    { entry_date: '2026-10-25', type_code: 'BIR Form 0605', description: 'Payment Form', amount: '0', remarks: '', notes: 'Entry note' },
    { entry_date: '2026-10-25', type_code: 'BIR Form 1701Q', description: 'IQ', amount: '1', remarks: null, notes: 'Legacy note' },
] }, '2026');
assert.deepEqual(Array.from(mixedRemarks.rows, row => row.remarks), ['Paid', 'Pending for payment', '', 'Legacy note']);
assert.match(mixedRemarks.rows[0].sales, /1,000\.00/);
assert.equal(mixedRemarks.rows[1].period, undefined);
assert(!mixedRemarks.rows[0].remarks.includes('Pending'));
assert(render(mixedRemarks).includes('Pending for payment'));
const pendingEntryPaidForms = context.build({ rows: [
    { entry_date: '2026-10-25', type_code: 'Sales', description: 'Sales', amount: '1000', notes: 'Pending for payment' },
    ...['BIR Form 0619E', 'BIR Form 1603', 'BIR Form 1602'].map(type_code => ({
        entry_date: '2026-10-25', type_code, description: 'Tax form', amount: '500', remarks: 'Paid', notes: 'Pending for payment',
    })),
] }, '2026');
assert.deepEqual(Array.from(pendingEntryPaidForms.rows, row => row.remarks), ['Paid', 'Paid', 'Paid']);
assert(!render(pendingEntryPaidForms).includes('Pending for payment'));
mixedRemarks.rows[1].remarks = '<img src=x onerror=bad()>';
assert(!render(mixedRemarks).includes('<img src=x'));
const headers = Array.from(html.matchAll(/<th scope="col">(.*?)<\/th>/g), m => m[1]);
assert.deepEqual(headers, ['Type / Code', 'Description', 'Period', 'Quarter', 'Sales', 'MICT', 'Expenses', 'COGS / COS', 'Net Sales', 'Income payments (2307)', 'Tax withheld', 'Tax Due', 'Remarks']);
assert(!html.includes('<script>bad()'));
assert(html.includes('&lt;script&gt;'));
assert(!html.includes('Prepared from generated'));
assert(html.includes('tabindex="0" role="region"'));
const monthMarkup = html.match(/<tr class="reports-worksheet-month-row">([\s\S]*?)<\/tr>/)[1];
assert.match(monthMarkup, /BIR Form 0605/);
assert.match(monthMarkup, /Payment Form/);
assert.match(monthMarkup, /Mar 2026/);
assert.match(monthMarkup, /75,000\.00/);
assert.match(monthMarkup, /500\.00/);
const footer = html.match(/<tr class="reports-ledger-totals-row">([\s\S]*?)<\/tr>/)[1];
assert.match(footer, /75,000\.00/);
assert.match(footer, /6,100\.00/);
assert.match(footer, /68,900\.00/);
assert.match(footer, /2,750\.00/);
assert(!footer.includes('2551') && !footer.includes('9000') && !footer.includes('12,500') && !footer.includes('180.00'));
const footerCells = Array.from(footer.matchAll(/<td>(.*?)<\/td>/g), match => match[1]);
assert.equal(footerCells[3], '-', 'Quarter numbers must never be summed as money');
const empty = context.build({ rows: [] }, '2026');
assert.equal(empty.columns.length, 13);
assert(!render(empty).includes('reports-ledger-totals-row'));

const quarterSource = { rows: Array.from({ length: 12 }, (_, index) => ({
    entry_date: `2026-${String(index + 1).padStart(2, '0')}-01`, type_code: 'BIR Form 0619E',
    description: 'TW', amount: '5', remarks: 'Paid', frequency: index % 2 ? 'quarterly' : 'monthly',
})) };
quarterSource.rows.push({ entry_date: '2025-12-31', type_code: 'Sales', description: 'Sales', amount: '0' });
const quarterBefore = JSON.stringify(quarterSource);
const quarterReport = context.build(quarterSource, '2026');
assert.deepEqual(Array.from(quarterReport.rows, row => row.quarter), ['1', '1', '1', '2', '2', '2', '3', '3', '3', '4', '4', '4']);
assert.equal(context.build(quarterSource, 'all').rows[0].quarter, '4');
assert.equal(context.build(quarterSource, '2025').rows[0].period, 'Dec 2025');
assert.equal(JSON.stringify(quarterSource), quarterBefore, 'Quarter display must not rewrite dates, frequency or amounts');
assert.equal(supportingReport.rows[2].quarter, '2', 'Each additional form must show its quarter without repeating the month');

// Print receives the exact preview sheet rather than rebuilding or recalculating it.
let printed = '';
const frame = { style: {}, setAttribute() {}, remove() {}, contentWindow: { focus() {}, print() {}, document: {
    readyState: 'complete', open() {}, write(value) { printed = value; }, close() {},
} } };
const quarterReportBefore = JSON.stringify(quarterReport);
const quarterHtml = render(quarterReport);
assert.equal(JSON.stringify(quarterReport), quarterReportBefore);
assert.equal((quarterHtml.match(/class="reports-worksheet-quarter-gap"/g) || []).length, 3, 'Exactly one blank row between each represented quarter');
const gaps = Array.from(quarterHtml.matchAll(/<tr class="reports-worksheet-quarter-gap" aria-hidden="true">([\s\S]*?)<\/tr>/g));
for (const gap of gaps) {
    assert.equal((gap[1].match(/<td>&nbsp;<\/td>/g) || []).length, 13);
    assert(!gap[1].includes('₱') && !gap[1].includes('Quarter'));
}
assert.equal((html.match(/class="reports-worksheet-quarter-gap"/g) || []).length, 1, 'Insert the gap after all March forms and before April');
assert.match(html, /2551Q[\s\S]*reports-worksheet-quarter-gap[\s\S]*Apr 2026/);
const skippedQuarters = context.build({ rows: quarterSource.rows.filter(row => /2026-(01|02|10|11)-/.test(row.entry_date)) }, '2026');
assert.equal((render(skippedQuarters).match(/class="reports-worksheet-quarter-gap"/g) || []).length, 1, 'Skipped quarters still need only one gap');
const yearBoundary = context.build({ rows: [
    { entry_date: '2025-12-01', type_code: 'Sales', description: 'Sales', amount: '100' },
    { entry_date: '2026-12-01', type_code: 'Sales', description: 'Sales', amount: '200' },
] }, 'all');
assert.equal((render(yearBoundary).match(/class="reports-worksheet-quarter-gap"/g) || []).length, 1, 'The same quarter number in different years must be separated');
assert(!render(context.build(quarterSource, '2025')).includes('reports-worksheet-quarter-gap'));
assert(!render(empty).includes('reports-worksheet-quarter-gap'));
assert.equal(quarterReport.rows.length, 12, 'Spacer rows must not become transactions or affect totals');
context.modalLatestReport = quarterReport;
context.modalReportSheet = { innerHTML: quarterHtml };
context.document = { getElementById() { return null; }, createElement() { return frame; }, body: { appendChild() {} } };
context.window.setTimeout = callback => callback();
context.showToast = () => assert.fail('Printing failed');
vm.runInContext(extract('        const printModalLedgerLayout =', '        const fetchModalReportPayload =') + '\nprintModalLedgerLayout();', context);
assert(printed.includes(quarterHtml.trim()));
assert.equal((printed.match(/class="reports-worksheet-quarter-gap"/g) || []).length, 3);
assert(printed.includes('<th scope="col">Quarter</th>'));
assert(printed.includes('size: A4 landscape'));
assert(printed.includes('table-header-group'));
context.modalLatestReport = allZeroReport;
context.modalReportSheet = { innerHTML: allZeroHtml };
vm.runInContext('printModalLedgerLayout();', context);
assert(printed.includes(allZeroHtml.trim()));
assert(!printed.includes('₱0.00'));
console.log('Worksheet report passed: automatic quarters for all months and form rows, year boundaries, no quarter totals, unchanged data/frequency, blank/zero, independent remarks and matching landscape print.');
