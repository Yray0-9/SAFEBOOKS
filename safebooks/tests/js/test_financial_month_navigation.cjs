const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.resolve(__dirname, '../../../templates/base/financial_records_client.html'), 'utf8').replace(/\r\n/g, '\n');
const extract = (start, end) => {
    const first = template.indexOf(start);
    const last = template.indexOf(end, first);
    assert(first >= 0 && last > first);
    return template.slice(first, last);
};
const button = () => ({ disabled: true, attributes: {}, addEventListener(type, callback) { this[type] = callback; }, setAttribute(key, value) { this.attributes[key] = value; } });
const plain = value => JSON.parse(JSON.stringify(value));
const context = {
    activeMonth: 6, activeYear: 2026, activeClientId: 1, addEntryFormDirty: false,
    currentRecordsPage: 3, expandedEntryIds: new Set([12]), MONTH_NAMES: { 1: 'January', 6: 'June', 7: 'July', 12: 'December' },
    financialPreviousMonth: button(), financialNextMonth: button(),
    financialPeriodYear: {}, financialYearSelector: button(), periodHeading: {}, periodSelector: button(),
    dateInput: { value: '2026-06-01' }, summaryCard: { hidden: false }, loads: [], messages: [],
    hasValidClientId: () => context.activeClientId > 0,
    document: { getElementById: id => id === 'addEntryDate' ? context.dateInput : null },
    getActivePeriodLabel: () => `${context.MONTH_NAMES[context.activeMonth]} ${context.activeYear}`,
    loadRecordsFromApi: async () => { context.loads.push([context.activeMonth, context.activeYear]); },
    updateDuplicateEntryWarning() {}, showToast: message => context.messages.push(message),
    financialSaveSummary: { hidden: true }, financialSaveSummaryTitle: {}, financialSaveSummaryMeta: {},
    financialSaveSummaryDismiss: button(), financialSaveSummaryTimer: null,
    timers: new Map(), timerId: 0,
    window: {
        clearTimeout: id => context.timers.delete(id),
        setTimeout: (callback, delay) => { const id = ++context.timerId; context.timers.set(id, { callback, delay }); return id; },
    },
    parseAmount: Number, formatCurrency: value => `PHP ${value}`, toDisplayText: value => String(value || ''),
    entryCoverageLabel: () => 'Monthly',
};
vm.createContext(context);
vm.runInContext(extract('        const parseIsoDateParts =', '        const normalizeFrequencyValue =') +
    extract('        const getPayloadTotal =', '        const getEntryById =') +
    extract('        const getDefaultDateForActivePeriod =', '        const syncActivePeriodToDate =') +
    extract('        const getAdjacentMonth =', '        if (financialPrevPage) {') +
    extract('        if (financialSaveSummaryDismiss && financialSaveSummary) {', '        if (addEntryForm) {') +
    '\nthis.updateNavigation = updateMonthNavigation; this.showSaved = showFinancialSaveSummary;', context);

context.updateNavigation();
assert.equal(context.financialPeriodYear.textContent, '2026');
assert.equal(context.financialYearSelector.value, '2026');
assert.equal((context.financialYearSelector.innerHTML.match(/<option /g) || []).length, 101);
assert(context.financialYearSelector.innerHTML.includes('value="2000"'));
assert(context.financialYearSelector.innerHTML.includes('value="2100"'));
assert.equal(context.financialNextMonth.attributes['aria-label'], 'Next month: July 2026');
context.financialNextMonth.click();
assert.deepEqual(context.loads, [[7, 2026]]);
assert.equal(context.periodSelector.value, '7');
assert.equal(context.periodHeading.textContent, 'July 2026 Records');
assert.equal(context.currentRecordsPage, 1);
assert.equal(context.expandedEntryIds.size, 0);
assert.equal(context.dateInput.value, '2026-07-01');
context.financialPreviousMonth.click();
assert.equal(context.activeMonth, 6);
assert.equal(context.dateInput.value, '2026-06-01');

// Calendar stepping includes empty months and safely crosses year boundaries.
context.activeMonth = 12;
context.financialNextMonth.click();
assert.deepEqual([context.activeMonth, context.activeYear, context.dateInput.value], [1, 2027, '2027-01-01']);
assert.equal(context.financialYearSelector.value, '2027');
context.financialPreviousMonth.click();
assert.deepEqual([context.activeMonth, context.activeYear], [12, 2026]);
assert.equal(context.financialYearSelector.value, '2026');

// Selecting a previous, empty year keeps the month and defaults new entries to that year.
context.financialYearSelector.change({ target: { value: '2024' } });
assert.deepEqual([context.activeMonth, context.activeYear, context.dateInput.value], [12, 2024, '2024-12-01']);
assert.deepEqual(context.loads.at(-1), [12, 2024]);
context.financialPreviousMonth.click();
assert.deepEqual([context.activeMonth, context.activeYear, context.dateInput.value], [11, 2024, '2024-11-01']);
context.financialYearSelector.change({ target: { value: '2026' } });

// A manual jump shares the read path; neither it nor stepping can rewrite a draft.
context.addEntryFormDirty = true;
context.dateInput.value = '2026-12-15';
context.periodSelector.change({ target: { value: '6' } });
assert.deepEqual([context.activeMonth, context.activeYear], [6, 2026]);
assert.equal(context.dateInput.value, '2026-12-15');
context.financialYearSelector.change({ target: { value: '2025' } });
assert.equal(context.dateInput.value, '2026-12-15', 'Year selection must preserve a dirty draft');
assert.deepEqual([context.activeMonth, context.activeYear], [6, 2025]);
context.financialYearSelector.change({ target: { value: '2026' } });
context.financialNextMonth.click();
assert.equal(context.dateInput.value, '2026-12-15');

context.periodSelector.change({ target: { value: 'all' } });
assert(context.financialPreviousMonth.disabled && context.financialNextMonth.disabled);
assert.equal(context.financialPeriodYear.textContent, '');
assert.equal(context.financialYearSelector.disabled, true);
const readCount = context.loads.length;
context.financialNextMonth.click();
context.financialYearSelector.change({ target: { value: '2024' } });
assert.equal(context.loads.length, readCount);
context.periodSelector.change({ target: { value: '1' } });
assert.equal(context.financialNextMonth.disabled, false);
assert.equal(context.financialYearSelector.disabled, false);
const beforeInvalidYears = context.loads.length;
for (const value of ['1999', '2101', '2025.5', '', 'not-a-year']) {
    context.financialYearSelector.change({ target: { value } });
    assert.equal(context.activeYear, 2026);
    assert.equal(context.financialYearSelector.value, '2026');
}
assert.equal(context.loads.length, beforeInvalidYears);
context.activeYear = 2000;
context.updateNavigation();
assert.equal(context.financialPreviousMonth.disabled, true);
context.activeYear = 2100;
context.activeMonth = 12;
context.updateNavigation();
assert.equal(context.financialNextMonth.disabled, true);
context.activeClientId = null;
context.updateNavigation();
assert(context.financialPreviousMonth.disabled && context.financialNextMonth.disabled);
assert.equal(context.financialYearSelector.disabled, true);
console.log('Month controls passed: selected month/date, dropdown, empty months, year transitions, supported limits, All Periods, and draft preservation.');

// Saved/updated banners belong to the displayed period, even if a save refresh is delayed.
context.activeClientId = 1;
context.activeMonth = 6;
context.activeYear = 2026;
context.updateNavigation();
const juneEntry = { date: '2026-06-01', line_items: [{ amount: '100' }] };
context.showSaved('add', juneEntry);
assert.equal(context.financialSaveSummary.hidden, false);
assert.equal(context.financialSaveSummaryTitle.textContent, 'Entry saved');
assert.equal(context.timers.size, 1);
assert.equal([...context.timers.values()][0].delay, 7000, 'Retain existing banner duration');
context.financialNextMonth.click();
assert.equal(context.financialSaveSummary.hidden, true);
assert.equal(context.timers.size, 0, 'Navigation cancels the old banner timer');
context.showSaved('edit', juneEntry);
assert.equal(context.financialSaveSummary.hidden, true, 'Delayed June confirmation cannot reappear in July');
const julyEntry = { date: '2026-07-01', line_items: [{ amount: '200' }] };
context.showSaved('edit', julyEntry);
assert.equal(context.financialSaveSummary.hidden, false);
assert.equal(context.financialSaveSummaryTitle.textContent, 'Entry updated');
context.showSaved('edit', juneEntry);
assert(context.financialSaveSummaryMeta.textContent.includes('2026-07-01'), 'An older confirmation cannot replace a matching newer one');
context.financialPreviousMonth.click();
assert.equal(context.financialSaveSummary.hidden, true);
context.showSaved('edit', juneEntry);
context.periodSelector.change({ target: { value: 'all' } });
assert.equal(context.financialSaveSummary.hidden, true, 'All Periods clears the old banner too');
context.showSaved('add', juneEntry);
assert.equal(context.financialSaveSummary.hidden, false, 'All Periods can confirm a newly saved entry');
context.financialSaveSummaryDismiss.click();
assert.equal(context.financialSaveSummary.hidden, true);
assert.equal(context.timers.size, 0);
context.periodSelector.change({ target: { value: '6' } });
context.showSaved('edit', juneEntry);
context.periodSelector.change({ target: { value: '7' } });
assert.equal(context.financialSaveSummary.hidden, true, 'Direct month selection clears the banner');
context.activeMonth = 6;
context.showSaved('edit', juneEntry);
context.financialYearSelector.change({ target: { value: '2027' } });
assert.equal(context.financialSaveSummary.hidden, true, 'Changing only the year also clears the banner');
context.showSaved('edit', juneEntry);
assert.equal(context.financialSaveSummary.hidden, true, 'A matching month in another year is a different period');
context.activeYear = 2026;
context.showSaved('edit', juneEntry);
[...context.timers.values()][0].callback();
assert.equal(context.financialSaveSummary.hidden, true);
assert.equal(context.timers.size, 0);
console.log('Save banners passed: Add/Edit, next/previous/dropdown/All Periods, timer cleanup, delayed refresh, year isolation, dismissal, and normal expiry.');

// Exercise the actual read loader with response bodies resolved out of order.
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const oldBody = deferred();
const firstParsing = deferred();
const read = {
    activeClientId: 1, activeMonth: 6, activeYear: 2026, recordsLoadRequestToken: 0, recordsLoadAbortController: null,
    activeRecords: [], activeSummary: null, activePriorFrequencies: new Set(), expandedEntryIds: new Set(),
    clientContext: {}, periodSelector: {}, AbortController, URLSearchParams, requests: [], renders: [], messages: [],
    hasValidClientId: () => true, setRecordsLoadingState() {}, setReusePanelVisibility() {}, updateClientContext() {},
    updateReusePanelForFrequency() {}, updateDuplicateEntryWarning() {}, redirectToLogin() {},
    buildRecordsApiUrl: () => '/api/financial-records/client/1/records/',
    document: { getElementById: () => null, querySelector: () => ({ hidden: true }) },
    setRecordsLoadFailure(message) { read.failure = message; }, showToast: message => read.messages.push(message),
    renderEntriesTable() { read.renders.push({ month: read.activeMonth, records: plain(read.activeRecords) }); },
    fetch: async (url, options) => {
        read.requests.push({ url, options });
        return { ok: true, status: 200, number: read.requests.length };
    },
    parseJsonSafe: async response => {
        if (response.number === 1) { firstParsing.resolve(); return oldBody.promise; }
        return { ok: true, client: {}, period: { month: 7, year: 2026 }, records: [{ id: 7 }], summary: {} };
    },
};
vm.createContext(read);
vm.runInContext(extract('        const loadRecordsFromApi =', '        const handleLineItemClick =') + '\nthis.load = loadRecordsFromApi;', read);
(async () => {
    const first = read.load();
    await firstParsing.promise;
    read.activeMonth = 7;
    await read.load();
    oldBody.resolve({ ok: true, period: { month: 6, year: 2026 }, records: [{ id: 6 }] });
    await first;
    assert.deepEqual(plain(read.activeRecords), [{ id: 7 }]);
    assert.equal(read.activeMonth, 7);
    assert.equal(read.renders.length, 1);
    assert.equal(read.requests[0].options.signal.aborted, true);
    assert(read.requests.every(request => request.options.method === 'GET' && !request.options.body));
    assert(read.requests[0].url.endsWith('?month=6&year=2026'));
    assert(read.requests[1].url.endsWith('?month=7&year=2026'));
    read.activeYear = 2024;
    read.parseJsonSafe = async () => ({ ok: true, period: { month: 7, year: 2024 }, records: [], summary: {} });
    await read.load();
    assert(read.requests[2].url.endsWith('?month=7&year=2024'));
    assert.equal(read.requests[2].options.method, 'GET');
    read.fetch = async () => { throw new Error('Synthetic network failure'); };
    await read.load();
    assert.equal(read.activeMonth, 7);
    assert.deepEqual(plain(read.activeRecords), []);
    assert(read.failure.includes('retry'));
    context.activeClientId = 1;
    context.activeYear = 2026;
    context.activeMonth = 7;
    context.updateNavigation();
    assert.equal(context.financialNextMonth.disabled, false, 'A failed read must leave narrowing controls usable');
    console.log('Read flow passed: GET only, rapid selection during JSON parsing, aborted/stale responses, and usable navigation after failure.');
})().catch(error => { console.error(error); process.exitCode = 1; });
