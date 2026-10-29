const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../../..");
const template = fs.readFileSync(path.join(root, "templates/base/financial_records_client.html"), "utf8").replace(/\r\n/g, "\n");
const extract = (start, end) => {
    const first = template.indexOf(start);
    const last = template.indexOf(end, first);
    assert(first >= 0 && last > first, `Missing financial flow: ${start}`);
    return template.slice(first, last);
};
const formFunctions = extract("        const populateEditForm =", "        const parseIsoDateParts =");
const feedback = extract("        const showMutationFailure =", "        const resolveClientIdFromTin =");
const submits = extract('        if (addEntryForm) {\n            addEntryForm.addEventListener("submit"',
    '        if (addEntryForm) {\n            addEntryForm.addEventListener("input"');
const closing = extract('        if (addEntryModalElement) {\n            addEntryModalElement.addEventListener("show.bs.modal", () => {\n                addEntryFormDirty = false;',
    "        if (dashboardProfileAction) {");
const dateValidation = extract("        const parseIsoDateParts =", "        const normalizeFrequencyValue =");
const payloadValidation = extract("        const validateEntryPayload =", "        const setFormSubmitState =");
const worksheetHelpers = extract("        const WORKSHEET_AMOUNT_FIELDS =", "        const suggestLineDescription =");
const coverageContext = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'static/js/financial_coverage.js'), 'utf8'), coverageContext);
const validator = { window: coverageContext.window };
vm.runInNewContext(worksheetHelpers + dateValidation + payloadValidation + "\nthis.validate = validateEntryPayload;", validator);
const amountPayload = amount => ({ date: "2026-04-15", frequency: "monthly", line_items: [{ type_code: "Sales", description: "Draft sale", amount }] });
for (const amount of [0, "0", "0.00", "100.25", "1e2", ".5"]) {
    assert.equal(validator.validate(amountPayload(amount)), "", `Valid financial amount rejected: ${amount}`);
}
for (const amount of ["NaN", "Infinity", "1e1000000", "10junk", "0x10", "1_000", "-1", "", {}, true]) {
    assert.notEqual(validator.validate(amountPayload(amount)), "", "Invalid financial amount passed browser validation");
}

// Syntax-check the complete page script, not only the extracted handlers.
for (const match of template.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
    if (!match[1].trim()) continue;
    new vm.Script(match[1].replace(/\{%[\s\S]*?%\}/g, "/synthetic-route/").replace(/\{\{[\s\S]*?\}\}/g, "synthetic-value"));
}
assert(template.includes('id="editEntryRevision" name="expected_revision"'));
assert(template.includes('id="editEntryStatus" role="alert" hidden'));
assert(template.includes('id="deleteEntryStatus" role="alert" hidden'));

// Run the real selection handler: no tax title may be inserted, and saved labels stay intact.
const manualDescription = (value = '') => {
    const context = {
        descriptionInput: { value, dataset: {}, readOnly: true }, customWrapper: { hidden: true },
        customCodeInput: { value: '', required: false, focus() {} },
        codeSelect: { addEventListener(name, handler) { context.change = handler; } },
    };
    vm.runInNewContext(extract("        const suggestLineDescription =", "        const createLineItemRow =") +
        extract('            codeSelect.addEventListener("change",', '            descriptionInput.addEventListener("input",'), context);
    context.choose = code => context.change({ target: { value: code } });
    return context;
};
const offeredCodes = [...template.matchAll(/\{ code: "(BIR Form [^"]+)"/g)].map(match => match[1]);
assert(offeredCodes.length > 60);
const firstTax = manualDescription();
for (const code of offeredCodes) {
    firstTax.choose(code);
    assert.equal(firstTax.descriptionInput.value, '', `Selecting ${code} must leave Description blank`);
    assert.equal(firstTax.descriptionInput.readOnly, false);
}
firstTax.descriptionInput.value = 'TW';
firstTax.choose('BIR Form 1601EQ');
assert.equal(firstTax.descriptionInput.value, 'TW');
firstTax.choose('Others');
assert.equal(firstTax.descriptionInput.value, 'TW', 'Switching to custom must preserve the typed label');
firstTax.choose('BIR Form 2551Q');
assert.equal(firstTax.descriptionInput.value, 'TW');
for (const saved of ['PQ', 'QR', 'A previously saved long description']) {
    const existing = manualDescription(saved);
    existing.choose('BIR Form 2551Q');
    assert.equal(existing.descriptionInput.value, saved, 'Edit and Copy Previous must preserve saved descriptions');
}
const secondTax = manualDescription();
secondTax.choose('BIR Form 0619E');
assert.equal(secondTax.descriptionInput.value, '');
assert.equal(firstTax.descriptionInput.value, 'TW', 'Rows must remain independent');
console.log('Manual tax descriptions passed: every form starts blank, typed/edit/copied labels stay intact, custom switching and independent rows.');

// Exercise the actual ready-field adapter against the unchanged line-item contract.
const readyFields = Object.fromEntries(['addSalesAmount', 'addExpensesAmount', 'editSalesAmount', 'editExpensesAmount', 'addSalesCoverage', 'addExpensesCoverage', 'editSalesCoverage', 'editExpensesCoverage'].map(id => [id, { id, value: '', dataset: {}, setCustomValidity(message) { this.validationMessage = message; }, setAttribute(key, value) { this[key] = value; } }]));
const readyContext = {
    window: coverageContext.window, escapeHtml: value => String(value),
    document: { getElementById: id => readyFields[id] },
    lineItemCounter: 0,
    addLineItemsBody: { rows: [] },
    editLineItemsBody: { rows: [] },
    BIR_FORMS_LIST: [{ code: 'BIR Form 2551Q' }, { code: 'BIR Form 1701Q' }],
    getLineItemRows: body => body.rows,
};
vm.createContext(readyContext);
vm.runInContext(
    worksheetHelpers + extract("        const suggestLineDescription =", "        const createLineItemRow =") +
    extract("        const getReadyAmountKey =", "        const resetLineItemsBody =") +
    extract("        const isBlankLineItemRow =", "        const removeLineItemRow =") +
    extract("        const collectLineItems =", "        const buildBreakdownByType =") +
    "\nthis.resetReady = resetReadyAddAmounts; this.collect = collectLineItems; this.syncRow = syncLineItemRequirements;",
    readyContext
);
const plain = value => JSON.parse(JSON.stringify(value));
const detailRow = (code = "", description = "", amount = "", custom = "", remarks = "") => {
    const fields = {
        '.financial-line-code-select': { value: code },
        '.financial-line-code-custom-input': { value: custom },
        '.financial-line-description-input': { value: description, dataset: {} },
        '.financial-line-amount-input': { value: amount },
        '.financial-line-remarks-input': { value: remarks },
        '.financial-line-coverage-select': { value: '', dataset: {}, closest: () => ({ hidden: true }) },
    };
    const classes = new Set();
    return { dataset: { lineItemId: 'detail-1' }, classes, classList: { toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); } }, querySelector: selector => fields[selector] };
};
readyContext.resetReady([]);
readyContext.addLineItemsBody.rows = [detailRow()];
readyContext.syncRow(readyContext.addLineItemsBody.rows[0]);
assert.equal(readyContext.addLineItemsBody.rows[0].querySelector('.financial-line-description-input').required, false);
assert.deepEqual(plain(readyContext.collect(readyContext.addLineItemsBody)), []);
readyFields.addSalesAmount.value = '0';
let readyPayload = plain(readyContext.collect(readyContext.addLineItemsBody));
assert.equal(readyPayload.length, 1, 'Blank Expenses must not create a zero observation');
assert.equal(readyPayload[0].type_code, 'SALES');
assert.equal(readyPayload[0].description, 'Sales');
assert.equal(validator.validate({ date: '2026-04-15', line_items: readyPayload }), '');

const copySource = [
    { id: 21, type_code: 'Sales', description: 'Original sales description', amount: '100.25' },
    { id: 22, type_code: 'EXPENSES', description: 'Original expense description', amount: '25.50' },
    { id: 23, type_code: 'EXPENSES', description: 'Additional expense', amount: '3.00' },
    { id: 24, type_code: 'BIR Form 2551Q', description: 'Tax form description', amount: '5.00' },
];
const originalCopy = JSON.stringify(copySource);
const remainingDetails = readyContext.resetReady(copySource);
assert.deepEqual(plain(remainingDetails), copySource.slice(2), 'Extra lines must not be merged or dropped');
readyContext.addLineItemsBody.rows = remainingDetails.map(line => {
    const row = detailRow(line.type_code.startsWith('BIR') ? line.type_code : 'Others', line.description, line.amount, line.type_code);
    row.dataset.lineItemId = String(line.id);
    readyContext.syncRow(row);
    return row;
});
readyPayload = plain(readyContext.collect(readyContext.addLineItemsBody));
assert.deepEqual(readyPayload.map(({ type_code, description, amount }) => ({ type_code, description, amount })), copySource.map(({ type_code, description, amount }) => ({ type_code, description, amount })));
assert.equal(JSON.stringify(copySource), originalCopy, 'Copying must not mutate source history');
assert.equal(readyFields.addSalesAmount.dataset.lineItemId, '21');
assert.equal(readyFields.addExpensesAmount.dataset.lineItemId, '22');
assert.equal(validator.validate({ date: '2026-04-15', line_items: readyPayload }), '');

const editRows = { rows: [detailRow('Others', 'Original edit description', '2.50', 'Sales')] };
assert.deepEqual(plain(readyContext.collect(editRows)), [{ client_line_id: 'detail-1', type_code: 'Sales', description: 'Original edit description', amount: '2.50', coverage_frequency: null, remarks: '', mict: null, cogs_cos: null, income_payments_2307: null, tax_withheld: null }]);
readyContext.resetReady([]);
assert.equal(readyFields.addSalesAmount.value, '');
assert.equal(readyFields.addExpensesAmount.value, '');
readyContext.addLineItemsBody.rows = [detailRow('BIR Form 2551Q', 'Existing tax description', '5.00')];
readyContext.syncRow(readyContext.addLineItemsBody.rows[0]);
assert.equal(readyContext.addLineItemsBody.rows[0].querySelector('.financial-line-description-input').required, true);
assert.equal(readyContext.collect(readyContext.addLineItemsBody).length, 1, 'Tax-only entries must not acquire Sales or Expenses');
console.log('Ready Sales/Expenses adapter passed: blank/zero, tax-only, copy preservation, duplicate lines and reset.');

const worksheetRow = detailRow('BIR Form 2551Q', 'PQ', '25.00');
const worksheetInputs = { mict: { value: '' }, cogs_cos: { value: '1000.50' }, income_payments_2307: { value: '5000' }, tax_withheld: { value: '0' } };
worksheetRow.nextElementSibling = {
    classList: { contains: name => name === 'financial-worksheet-row' },
    querySelector: selector => worksheetInputs[selector.match(/data-worksheet-field="([^"]+)"/)[1]],
};
readyContext.addLineItemsBody.rows = [worksheetRow];
const worksheetPayload = plain(readyContext.collect(readyContext.addLineItemsBody));
assert.equal(worksheetPayload[0].amount, '25.00');
assert.equal(worksheetPayload[0].mict, null);
assert.equal(worksheetPayload[0].cogs_cos, '1000.50');
assert.equal(worksheetPayload[0].tax_withheld, '0');
assert.equal(validator.validate({ date: '2026-04-15', line_items: worksheetPayload }), '');
for (const invalid of ['-1', 'Infinity', 'NaN', {}, true]) {
    assert.notEqual(validator.validate({ date: '2026-04-15', line_items: [{ type_code: 'BIR Form 2551Q', description: 'PQ', amount: '25', cogs_cos: invalid }] }), '');
}
const supportedStandard = [{ type_code: 'SALES', description: 'Original', amount: '10.00', cogs_cos: '0.00' }];
assert.equal(readyContext.resetReady(supportedStandard).length, 1, 'A line with worksheet data must remain intact instead of losing its supporting values');
console.log('Worksheet adapter passed: per-row values, null versus zero, validation, unchanged base amount, and copying without loss.');

readyContext.resetReady([]);
const paidRow = detailRow('BIR Form 2551Q', 'PQ', '5', '', 'Paid');
const pendingRow = detailRow('BIR Form 1701Q', 'IQ', '10', '', 'Pending for payment');
readyContext.addLineItemsBody.rows = [paidRow, pendingRow];
let formRemarksPayload = plain(readyContext.collect(readyContext.addLineItemsBody));
assert.deepEqual(formRemarksPayload.map(line => line.remarks), ['Paid', 'Pending for payment']);
assert.equal(validator.validate({ date: '2026-04-15', line_items: formRemarksPayload }), '');
assert.deepEqual(formRemarksPayload.map(line => line.remarks), ['Paid', 'Pending for payment']);
paidRow.dataset.remarksIsLegacy = 'true';
assert.equal(readyContext.collect(readyContext.addLineItemsBody)[0].remarks, 'Paid', 'Typed form remarks must not depend on receiving an input event');
paidRow.querySelector('.financial-line-remarks-input').value = '';
assert.equal(readyContext.collect(readyContext.addLineItemsBody)[0].remarks, null);
paidRow.dataset.remarksIsLegacy = 'false';
assert.equal(readyContext.collect(readyContext.addLineItemsBody)[0].remarks, '');
for (const invalid of [true, {}, 'x'.repeat(256)]) {
    assert.notEqual(validator.validate({ date: '2026-04-15', line_items: [{ type_code: 'BIR Form 2551Q', description: 'PQ', amount: '5', remarks: invalid }] }), '');
}
readyContext.addLineItemsBody.rows = [detailRow('', '', '', '', 'Paid')];
assert.equal(readyContext.collect(readyContext.addLineItemsBody).length, 1, 'Remarks-only detail must be validated instead of silently discarded');
const inheritedRow = detailRow('BIR Form 2551Q', 'PQ', '500', '', 'Pending for payment');
inheritedRow.dataset.remarksIsLegacy = 'true';
inheritedRow.dataset.legacyRemarkValue = 'Pending for payment';
readyContext.addLineItemsBody.rows = [inheritedRow];
assert.equal(plain(readyContext.collect(readyContext.addLineItemsBody))[0].remarks, null, 'Showing a legacy fallback must not silently backfill a form remark');
inheritedRow.querySelector('.financial-line-remarks-input').value = 'Paid';
assert.equal(plain(readyContext.collect(readyContext.addLineItemsBody))[0].remarks, 'Paid', 'Changed remarks must be collected even without an input event');
inheritedRow.querySelector('.financial-line-remarks-input').value = '';
assert.equal(plain(readyContext.collect(readyContext.addLineItemsBody))[0].remarks, '', 'Clearing a displayed fallback suppresses entry-note fallback');
console.log('Form remarks adapter passed: independent remarks, legacy null versus explicit blank, validation and remarks-only drafts.');

const editSource = [
    { id: 51, type_code: 'BIR Form 2551Q', description: 'PQ', amount: '5.00' },
    { id: 52, type_code: 'Expenses', description: 'Saved expense label', amount: '25.00' },
    { id: 53, type_code: 'Sales', description: 'Saved sales label', amount: '100.00' },
    { id: 54, type_code: 'Expenses', description: 'Separate expense label', amount: '3.00', tax_withheld: '0.00' },
];
const editBefore = JSON.stringify(editSource);
const editDetails = readyContext.resetReady(editSource.map((line, index) => ({ ...line, _sourceOrder: index })), 'edit');
readyContext.editLineItemsBody.rows = editDetails.map(line => {
    const row = detailRow(line.type_code.startsWith('BIR') ? line.type_code : 'Others', line.description, line.amount, line.type_code);
    row.dataset.lineItemId = String(line.id);
    row.dataset.sourceOrder = String(line._sourceOrder);
    row.nextElementSibling = { classList: { contains: () => true }, querySelector: selector => ({ value: line[selector.match(/data-worksheet-field="([^"]+)"/)[1]] ?? '' }) };
    readyContext.syncRow(row);
    return row;
});
let edited = plain(readyContext.collect(readyContext.editLineItemsBody));
assert.deepEqual(edited.map(({ type_code, description, amount }) => ({ type_code, description, amount })), editSource.map(({ type_code, description, amount }) => ({ type_code, description, amount })), 'Opening and saving must retain line order and descriptions');
assert.equal(edited[3].tax_withheld, '0.00');
assert.equal(JSON.stringify(editSource), editBefore);
assert.equal(readyFields.editSalesAmount.value, '100.00');
assert.equal(readyFields.editExpensesAmount.value, '25.00');
assert.equal(readyContext.editLineItemsBody.rows[0].classes.has('financial-non-tax-detail-row'), false);
assert.equal(readyContext.editLineItemsBody.rows[1].classes.has('financial-non-tax-detail-row'), true);
readyFields.editSalesAmount.value = '120.00';
edited = plain(readyContext.collect(readyContext.editLineItemsBody));
assert.equal(edited[2].amount, '120.00');
assert.equal(edited[2].description, 'Saved sales label');
assert.equal(validator.validate({ date: '2026-04-15', line_items: edited }), '');
readyFields.editExpensesAmount.value = '';
assert.deepEqual(plain(readyContext.collect(readyContext.editLineItemsBody)).map(line => line.client_line_id), ['51', '53', '54'], 'Clearing the ready field must not remove a separate expense line');
readyFields.editExpensesAmount.value = '0';
assert.equal(plain(readyContext.collect(readyContext.editLineItemsBody))[1].amount, '0');
readyContext.resetReady([], 'edit');
readyContext.editLineItemsBody.rows = [detailRow()];
assert.deepEqual(plain(readyContext.collect(readyContext.editLineItemsBody)), []);
const customRow = detailRow('Others', '', '7.00', 'Custom code');
readyContext.syncRow(customRow);
assert.equal(customRow.classes.has('financial-non-tax-detail-row'), true);
assert.equal(customRow.querySelector('.financial-line-description-input').value, 'Custom code');
customRow.querySelector('.financial-line-code-custom-input').value = 'Updated custom code';
readyContext.syncRow(customRow);
assert.equal(customRow.querySelector('.financial-line-description-input').value, 'Updated custom code');
const editMarkup = template.slice(template.indexOf('id="editEntryModal"'), template.indexOf('id="deleteEntryModal"'));
assert(editMarkup.includes('id="editSalesAmount"') && editMarkup.includes('id="editExpensesAmount"'));
assert(!editMarkup.includes('Common details') && !editMarkup.includes('data-detail-template'));
readyContext.resetReady([
    { id: 91, type_code: 'Sales', description: 'Sales', amount: '75000', coverage_frequency: 'monthly' },
    { id: 92, type_code: 'Expenses', description: 'Expenses', amount: '5000', coverage_frequency: 'quarterly' },
], 'edit');
readyContext.editLineItemsBody.rows = [detailRow()];
assert.deepEqual(plain(readyContext.collect(readyContext.editLineItemsBody)).map(line => line.coverage_frequency), ['monthly', 'quarterly']);
readyFields.editSalesCoverage.value = 'quarterly';
assert.deepEqual(plain(readyContext.collect(readyContext.editLineItemsBody)).map(line => line.coverage_frequency), ['quarterly', 'quarterly']);
assert.equal(readyFields.editExpensesAmount.value, '5000');
readyContext.resetReady([{ id: 93, type_code: 'Sales', description: 'Legacy', amount: '10' }], 'edit');
assert.equal(plain(readyContext.collect(readyContext.editLineItemsBody))[0].coverage_frequency, null);
assert(!template.includes('>Record Frequency</label>'));
const coverage = coverageContext.window.SafeBooksCoverage;
assert.equal(coverage.label('quarterly', '2026-03-31'), 'January–March 2026');
assert.equal(coverage.label('monthly', '2026-03-31'), 'March 2026 only');
assert.equal(coverage.label('quarterly', '2026-06-30'), 'April–June 2026');
const newChoices = coverage.options('2026-12-31', '', String);
assert(newChoices.includes('value="monthly"') && newChoices.includes('value="quarterly"'));
assert(!newChoices.includes('value="annually"') && !newChoices.includes('January–December'));
assert(!coverage.options('2026-12-31', 'monthly', String).includes('value="annually"'));
assert(coverage.options('2026-12-31', 'annually', String).includes('value="annually"'), 'Keep untouched legacy annual coverage available');
assert(coverage.options('2026-12-31', '', String, 'annually').includes('value="annually"'), 'Keep an explicitly saved annual value available during edit');
for (let month = 1; month <= 12; month++) {
    const date = `2026-${String(month).padStart(2, '0')}-01`;
    const choices = coverage.options(date, '', String);
    assert(choices.includes('value="monthly"'));
    assert.equal(choices.includes('value="quarterly"'), month % 3 === 0, 'Only quarter-ending months offer a new quarterly choice');
}
assert(!coverage.options('', '', String).includes('value="quarterly"'));
assert(!coverage.options('2026-13-01', '', String).includes('value="quarterly"'));
assert(coverage.options('2026-11-01', '', String, '', 'quarterly').includes('value="quarterly" disabled'), 'Keep a selected draft quarter visible and blocked after a date change');
assert(coverage.options('2026-11-01', '', String, 'quarterly').includes('value="quarterly" disabled'), 'Keep loaded explicit quarterly coverage without silently converting it');
const legacyQuarter = coverage.options('2026-10-25', 'quarterly', String);
assert(legacyQuarter.includes('August–October 2026 (saved)'));
assert(!legacyQuarter.includes('value="quarterly"'), 'An untouched legacy anchor is retained through its saved fallback, not a new calendar quarter');
const labelsContext = {};
vm.runInNewContext(extract('        const formatFrequencyLabel =', '        const getActiveMonthLabel =') +
    extract('        const getReadyAmountKey =', '        const isListedTaxForm =') +
    extract('        const entryCoverageLabel =', '        const getPayloadTotal =') + '\nthis.label = entryCoverageLabel;', labelsContext);
assert.equal(labelsContext.label({ frequency: 'monthly', line_items: [{ type_code: 'BIR Form 1603', amount: '500' }] }), '', 'Tax-only entries have no Sales/Expenses coverage label');
assert.equal(labelsContext.label({ frequency: 'quarterly', line_items: [{ type_code: 'Other fee', amount: '10' }] }), '');
assert.equal(labelsContext.label({ frequency: 'quarterly', line_items: [{ type_code: 'Sales', coverage_frequency: 'monthly', amount: '0' }] }), 'Monthly');
assert.equal(labelsContext.label({ frequency: 'monthly', line_items: [{ type_code: 'Expenses', coverage_frequency: 'quarterly', amount: '500' }] }), 'Quarterly');
assert.equal(labelsContext.label({ line_items: [{ type_code: 'Sales', coverage_frequency: 'monthly' }, { type_code: 'Expenses', coverage_frequency: 'quarterly' }] }), 'Mixed coverage');
assert(!template.includes('Tax forms / details'));
// Coverage belongs to each amount, not the whole entry. Exercise the real
// expanded-detail renderer with monthly Sales and quarterly Expenses together.
const detailContext = {
    window: coverageContext.window,
    getEntryLineItems: entry => entry.line_items || [],
    escapeHtml: text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;'),
    toDisplayText: value => value || '',
    parseAmount: Number,
    formatCurrency: value => `PHP ${value.toFixed(2)}`,
    isListedTaxForm: code => code.startsWith('BIR Form'),
};
vm.runInNewContext(worksheetHelpers +
    extract('        const getReadyAmountKey =', '        const isListedTaxForm =') +
    extract('        const renderEntryDetailsTable =', '        const toggleEntryExpansion =') +
    '\nthis.render = renderEntryDetailsTable;', detailContext);
const detailEntry = { date: '2026-12-01', frequency: 'monthly', line_items: [
    { type_code: 'Sales', amount: '75000', coverage_frequency: 'monthly' },
    { type_code: 'Expenses', amount: '50000', coverage_frequency: 'quarterly' },
] };
const detailRows = detailContext.render(detailEntry).match(/<tr>[\s\S]*?<\/tr>/g);
assert(detailRows[1].includes('Sales') && detailRows[1].includes('December 2026 only'));
assert(detailRows[2].includes('Expenses') && detailRows[2].includes('October–December 2026'));
const taxOnlyDetails = detailContext.render({ ...detailEntry, line_items: [
    { type_code: 'BIR Form 1603', description: 'QR', amount: '500' },
] });
assert(!taxOnlyDetails.includes('December 2026'), 'Do not assign Sales/Expenses coverage to a tax form');
assert(!template.includes('<th>Coverage</th>'));
assert(!template.includes('data-label="Coverage"'));
assert(!template.includes('<span>Coverage:</span>'));
assert(template.includes('<td colspan="4">'));
for (const mode of ['add', 'edit']) {
    assert(template.includes(`type="hidden" id="${mode}EntryNotes" name="notes"`));
    assert(!template.includes(`for="${mode}EntryNotes"`));
    assert(!template.includes(`id="${mode}EntryRemarksSuggestions"`));
}
assert(template.includes('id="taxFormRemarksSuggestions"'));

assert.equal(coverage.validate('quarterly', '2026-03-31'), '');
assert.notEqual(coverage.validate('quarterly', '2026-02-28'), '');
assert.notEqual(coverage.validate('annually', '2026-03-31'), '');
assert.equal(coverage.validate(null, '2026-02-28'), '', 'Legacy noncalendar coverage must stay unchanged');
assert.equal(coverage.validate('quarterly', '2026-11-01'), 'For October–December 2026, set Record Date to December 2026.');
const coverageFeedback = { id: 'addSalesCoverageFeedback', hidden: true, textContent: '' };
readyFields.addSalesCoverageFeedback = coverageFeedback;
readyContext.addLineItemsBody.rows = [];
readyFields.addEntryDate = { value: '2026-11-01' };
readyFields.addSalesAmount.value = '75000';
readyFields.addSalesCoverage.value = 'quarterly';
readyContext.resetCoverage = (date, amount, frequency) => {
    readyFields.addEntryDate.value = date;
    readyFields.addSalesAmount.value = amount;
    readyFields.addSalesCoverage.value = frequency;
    vm.runInContext('refreshCoverageChoices("add");', readyContext);
};
readyContext.resetCoverage('2026-11-01', '75000', 'quarterly');
assert.equal(coverageFeedback.hidden, false);
assert(coverageFeedback.textContent.includes('December 2026'));
assert.equal(readyFields.addSalesCoverage['aria-invalid'], 'true');
assert.equal(readyFields.addSalesAmount.value, '75000', 'Validation must preserve the amount');
readyContext.resetCoverage('2026-12-01', '75000', 'quarterly');
assert.equal(coverageFeedback.hidden, true);
assert.equal(readyFields.addSalesCoverage.validationMessage, '');
readyContext.resetCoverage('2026-11-01', '75000', 'monthly');
assert.equal(coverageFeedback.hidden, true);
readyContext.resetCoverage('2026-11-01', '', 'quarterly');
assert.equal(coverageFeedback.hidden, true, 'Unused category must not block tax-only entries');
const invalidQuarter = amountPayload('75000');
invalidQuarter.date = '2026-11-01';
invalidQuarter.line_items[0].coverage_frequency = 'quarterly';
assert(validator.validate(invalidQuarter).startsWith('Sales: For October'));
assert(!template.includes('Line item #'));
for (const invalid of [true, {}, [], 'weekly', '']) assert.notEqual(coverage.validate(invalid, '2026-03-31'), '');
console.log('Edit adapter passed: matching ready fields, exact saved labels/order, separate duplicate lines, worksheet zero, blank/zero edits, and tax-only descriptions.');

const makeContext = (response) => {
    const listeners = {};
    const modalListeners = {};
    const nodes = {
        editEntryId: { value: "7" }, editEntryRevision: { value: "old-revision" },
        editEntryDate: { value: "2026-04-15", dataset: { originalDate: "2026-04-15" } }, editEntryNotes: { value: "Unsaved draft" },
        editEntryPeriodChange: { hidden: true }, editEntryPeriodChangeLabel: { textContent: '' },
        editEntryConfirmPeriodChange: { checked: false, disabled: true, required: false, dataset: {}, focus() { this.focused = true; } },
        editEntryFrequency: { value: "monthly" }, editEntryStatus: { hidden: true },
        deleteEntryStatus: { hidden: true }, addEntryDate: { value: "2026-04-15" },
        addEntryNotes: { value: "Unsaved new draft" }, addEntryFrequency: { value: "monthly" },
    };
    const form = (name) => ({
        addEventListener: (type, callback) => { listeners[`${name}:${type}`] = callback; },
        checkValidity: () => true, reportValidity() { this.reportedInvalid = true; },
    });
    const context = {
        document: { getElementById: name => nodes[name] || null },
        addEntryForm: form("add"), editEntryForm: form("edit"), confirmDeleteEntryBtn: form("delete"),
        addLineItemsBody: {}, editLineItemsBody: {}, activeMonth: 4, activeYear: 2026,
        activeClientId: 5, isAddSubmitting: false, isEditSubmitting: false, isDeleteSubmitting: false,
        pendingDeleteEntryId: 7, pendingDeleteRevision: "old-revision", addEntryFormDirty: true, editEntryFormDirty: true,
        hasValidClientId: () => true, validateEntryPayload: () => "", getCookieValue: () => "synthetic-csrf",
        buildRecordsApiUrl: id => `/api/financial-records/client/${id}/records/`,
        buildRecordDetailApiUrl: (client, id) => `/api/financial-records/client/${client}/records/${id}/`,
        collectLineItems: () => [{ type_code: "Sales", description: "Draft sale", amount: "100.00" }],
        getEntryLineItems: entry => entry.line_items || [], resetLineItemsBody() {}, updateDuplicateEntryWarning() {}, refreshCoverageChoices() {},
        parseJsonSafe: async res => res.payload,
        setFormSubmitState: (target, busy) => { target.busy = busy; },
        syncActivePeriodToDate: () => false, getActivePeriodLabel: () => "April 2026", showFinancialSaveSummary() {},
        loadRecordsFromApi: async () => { context.reloads = (context.reloads || 0) + 1; },
        showToast: message => { context.messages.push(message); }, messages: [], requests: [],
        redirectToLogin: () => { context.redirected = true; },
        shared: { showConfirmDiscard: async () => false },
        fetch: async (url, options) => {
            context.requests.push({ url, options });
            if (typeof response === "function") return response();
            return response;
        },
    };
    for (const type of ["add", "edit", "delete"]) {
        context[`${type}EntryModalElement`] = {
            querySelector() { return null; },
            addEventListener(event, callback) {
                (modalListeners[`${type}:${event}`] ||= []).push(callback);
            },
        };
    }
    context.addEntryModal = { hide() { assert.equal(context.isAddSubmitting, false); context.addHidden = true; } };
    context.editEntryModal = { hide() { assert.equal(context.isEditSubmitting, false); context.editHidden = true; } };
    context.deleteEntryModal = { hide() { assert.equal(context.isDeleteSubmitting, false); context.deleteHidden = true; } };
    vm.createContext(context);
    vm.runInContext(extract("        const MONTH_NAMES =", "        const BIR_FORMS_LIST =") + dateValidation +
        extract("        const getSourcePeriodLabel =", "        const handleReuseLastPeriod =") +
        formFunctions + feedback + submits + closing + "\nthis.populate = populateEditForm; this.build = buildPayloadFromForm; this.syncMove = syncEditPeriodChange; this.resetMove = resetEditPeriodChange;", context);
    context.nodes = nodes;
    context.submit = type => listeners[`${type}:${type === "delete" ? "click" : "submit"}`]({ preventDefault() {} });
    context.close = (type, eventName = "hide.bs.modal") => {
        const event = { prevented: false, preventDefault() { this.prevented = true; } };
        (modalListeners[`${type}:${eventName}`] || []).forEach(callback => callback(event));
        return event;
    };
    return context;
};

const successResponse = { status: 200, ok: true, payload: { ok: true, message: "Saved", record: { revision: "new-revision" } } };

(async () => {
    const editor = makeContext(successResponse);
    editor.populate({ id: 7, revision: "selected-revision", date: "2026-04-15", notes: "Selected", frequency: "quarterly" });
    assert.equal(editor.nodes.editEntryRevision.value, "selected-revision");
    assert.equal(editor.build("edit").expected_revision, "selected-revision");
    assert.equal(editor.build("edit").notes, "Selected");
    assert.equal(editor.build("add").expected_revision, undefined);

    for (const destination of ['2026-07-25', '2025-10-25']) {
        const move = makeContext(successResponse);
        move.populate({ id: 7, revision: 'loaded-revision', date: '2026-10-25', notes: 'Keep this draft' });
        move.nodes.editEntryDate.value = destination;
        await move.submit('edit');
        assert.equal(move.requests.length, 0, 'Changing month/year must not write before acknowledgement');
        assert.equal(move.nodes.editEntryConfirmPeriodChange.focused, true);
        assert.equal(move.nodes.editEntryPeriodChange.hidden, false);
        assert(move.nodes.editEntryPeriodChangeLabel.textContent.includes('October 2026'));
        assert.equal(move.nodes.editEntryNotes.value, 'Keep this draft');
        move.nodes.editEntryConfirmPeriodChange.checked = true;
        await move.submit('edit');
        assert.equal(move.requests.length, 1);
        assert.equal(move.requests[0].options.method, 'PUT', 'A deliberate move updates the same entry, never copies');
        assert.equal(JSON.parse(move.requests[0].options.body).date, destination);
        assert.equal(JSON.parse(move.requests[0].options.body).expected_revision, 'loaded-revision');
    }
    const changedDestination = makeContext(successResponse);
    changedDestination.nodes.editEntryDate.value = '2026-07-25';
    changedDestination.syncMove();
    changedDestination.nodes.editEntryConfirmPeriodChange.checked = true;
    changedDestination.nodes.editEntryDate.value = '2026-08-25';
    await changedDestination.submit('edit');
    assert.equal(changedDestination.requests.length, 0, 'Acknowledgement belongs only to its destination month');
    assert.equal(changedDestination.nodes.editEntryConfirmPeriodChange.checked, false);
    changedDestination.nodes.editEntryDate.value = '2026-04-28';
    changedDestination.syncMove();
    assert.equal(changedDestination.nodes.editEntryPeriodChange.hidden, true);
    assert.equal(changedDestination.nodes.editEntryConfirmPeriodChange.disabled, true);
    await changedDestination.submit('edit');
    assert.equal(changedDestination.requests.length, 1, 'A day correction within the same month needs no move acknowledgement');
    changedDestination.populate({ id: 8, revision: 'another-revision', date: '2026-09-15' });
    assert.equal(changedDestination.nodes.editEntryConfirmPeriodChange.checked, false);
    assert.equal(changedDestination.nodes.editEntryPeriodChange.hidden, true);
    const failedMove = makeContext(() => { throw new Error('Synthetic unknown outcome'); });
    failedMove.nodes.editEntryDate.value = '2026-07-25';
    failedMove.syncMove();
    failedMove.nodes.editEntryConfirmPeriodChange.checked = true;
    await failedMove.submit('edit');
    assert.equal(failedMove.requests.length, 1);
    assert.equal(failedMove.editHidden, undefined);
    assert.equal(failedMove.nodes.editEntryDate.value, '2026-07-25');
    assert.equal(failedMove.nodes.editEntryNotes.value, 'Unsaved draft');
    console.log('Edit month/year guard passed: explicit move, same-month correction, changed destination, reopen, failed-write draft, and no copy/retry.');

    for (const type of ['add', 'edit']) {
        const line = { type_code: 'BIR Form 2551Q', description: 'PQ', amount: '5.00', remarks: 'Paid' };
        for (const savedLines of [undefined, [{ ...line, remarks: null }], [{ ...line, remarks: 'Pending for payment' }], [null]]) {
            const unconfirmed = makeContext({ status: 200, ok: true, payload: { ok: true, record: { revision: 'new-revision', line_items: savedLines } } });
            unconfirmed.collectLineItems = () => [{ ...line }];
            await unconfirmed.submit(type);
            assert.equal(unconfirmed[`${type}Hidden`], undefined, 'Unconfirmed form remarks must not close/reset the draft');
            assert.equal(unconfirmed.reloads, undefined);
            assert.equal(unconfirmed.requests.length, 1, 'Never retry an acknowledged write automatically');
            assert(unconfirmed.messages.at(-1).includes('form remarks were not confirmed'));
            assert.equal(unconfirmed[`${type}EntryFormDirty`], true);
        }
        const confirmed = makeContext({ status: 200, ok: true, payload: { ok: true, record: { revision: 'new-revision', line_items: [{ ...line }] } } });
        confirmed.collectLineItems = () => [{ ...line }];
        await confirmed.submit(type);
        assert.equal(confirmed[`${type}Hidden`], true);
        assert.equal(confirmed.reloads, 1);
    }

    for (const type of ['add', 'edit']) {
        const line = { type_code: 'Sales', description: 'Sales', amount: '75000', coverage_frequency: 'quarterly' };
        for (const savedLines of [undefined, [{ ...line, coverage_frequency: null }], [{ ...line, coverage_frequency: 'monthly' }]]) {
            const unconfirmed = makeContext({ status: 200, ok: true, payload: { ok: true, record: { line_items: savedLines } } });
            unconfirmed.collectLineItems = () => [{ ...line }];
            await unconfirmed.submit(type);
            assert.equal(unconfirmed[`${type}Hidden`], undefined);
            assert.equal(unconfirmed.requests.length, 1);
            assert.equal(unconfirmed.reloads, undefined);
            assert(unconfirmed.messages.at(-1).includes('covered periods were not confirmed'));
        }
        const confirmed = makeContext({ status: 200, ok: true, payload: { ok: true, record: { line_items: [{ ...line }] } } });
        confirmed.collectLineItems = () => [{ ...line }];
        await confirmed.submit(type);
        assert.equal(confirmed[`${type}Hidden`], true);
    }

    for (const type of ["add", "edit", "delete"]) {
        const saved = makeContext(successResponse);
        await saved.submit(type);
        assert.equal(saved.requests.length, 1);
        const options = saved.requests[0].options;
        assert.equal(options.headers["X-CSRFToken"], "synthetic-csrf");
        assert.equal(options.credentials, "same-origin");
        assert.equal(options.headers["Content-Type"], "application/json");
        assert.equal(JSON.parse(options.body).expected_revision, type === "add" ? undefined : "old-revision");
        if (type !== "delete") {
            assert.equal(JSON.parse(options.body).notes, type === "add" ? "Unsaved new draft" : "Unsaved draft");
        }
        assert.equal(saved[`${type}Hidden`], true);
        assert.equal(saved.reloads, 1);
        assert.equal(saved[`is${type[0].toUpperCase() + type.slice(1)}Submitting`], false);

        const conflict = makeContext({ status: 409, ok: false, payload: { ok: false, code: "stale_record", message: "Review the latest entry." } });
        await conflict.submit(type);
        assert.equal(conflict[`${type}Hidden`], undefined);
        assert.equal(conflict.reloads, undefined);
        assert.equal(conflict.nodes.editEntryNotes.value, "Unsaved draft");
        assert.equal(conflict.nodes.editEntryRevision.value, "old-revision");
        if (type !== "add") {
            assert.equal(conflict.nodes[`${type}EntryStatus`].hidden, false);
            assert.equal(conflict.nodes[`${type}EntryStatus`].textContent, "Review the latest entry.");
        }

        const network = makeContext(() => { throw new Error("Synthetic network interruption"); });
        await network.submit(type);
        assert.equal(network.requests.length, 1); // Never auto-retry a write with an unknown outcome.
        assert.equal(network[`${type}Hidden`], undefined);
        assert.equal(network.reloads, undefined);
        assert(network.messages.at(-1).includes("may have"));
        assert.equal(network.nodes.editEntryNotes.value, "Unsaved draft");
        assert.equal(network[`is${type[0].toUpperCase() + type.slice(1)}Submitting`], false);

        const signedOut = makeContext({ status: 401, ok: false });
        await signedOut.submit(type);
        assert.equal(signedOut.redirected, true);
        assert.equal(signedOut[`${type}Hidden`], undefined);

        let resolve;
        const pending = makeContext(() => new Promise(done => { resolve = done; }));
        const inFlight = pending.submit(type);
        assert.equal(pending.close(type).prevented, true, "An in-flight write allowed the modal to reset/close");
        await pending.submit(type);
        assert.equal(pending.requests.length, 1, "Repeated click sent a duplicate mutation");
        resolve(successResponse);
        await inFlight;
        assert.equal(pending[`${type}Hidden`], true);
    }
    const cancelled = makeContext(successResponse);
    assert.equal(cancelled.close("edit").prevented, true);
    await Promise.resolve();
    assert.equal(cancelled.editHidden, undefined);
    assert.equal(cancelled.editEntryFormDirty, true);
    assert.equal(cancelled.nodes.editEntryNotes.value, "Unsaved draft");
    cancelled.editEntryFormDirty = false;
    assert.equal(cancelled.close("edit").prevented, false);
    cancelled.close("delete", "hidden.bs.modal");
    assert.equal(cancelled.pendingDeleteEntryId, null);
    assert.equal(cancelled.pendingDeleteRevision, "");
    assert.equal(cancelled.nodes.deleteEntryStatus.hidden, true);
    console.log("Financial modal revision, success, conflict, network, authentication, duplicate-click, and cancel/close tests passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
