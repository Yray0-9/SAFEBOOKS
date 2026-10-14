const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8").replace(/\r\n/g, "\n");
const details = read("templates/base/client_details.html");
const extract = (source, start, end) => {
    const first = source.indexOf(start), last = source.indexOf(end, first);
    assert(first >= 0 && last > first, `Missing flow: ${start}`);
    return source.slice(first, last).replace(/\{%[\s\S]*?%\}/g, "/synthetic-route/");
};
for (const name of ["client_details", "analytics", "financial_records_client"]) {
    for (const match of read(`templates/base/${name}.html`).matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
        if (!/application\/json/i.test(match[1]) && match[2].trim()) new vm.Script(match[2].replace(/\{%[\s\S]*?%\}/g, "/synthetic-route/").replace(/\{\{[\s\S]*?\}\}/g, "synthetic-value"));
    }
}
const loader = extract(details, "        const fetchModalReportPayload =", "        const showReportModal =");
const events = extract(details, "        const setupModalReportEvents =", "        // Export globally");
const makeReport = () => {
    const handlers = {};
    const context = {
        CLIENT_ID: 7, REPORTS_PRINT_LAYOUT_API_URL: "/api/reports/print-layout/", URLSearchParams, AbortController,
        modalReportRequestToken: 0, modalReportAbortController: null, modalLatestReport: null, modalReportSourcePayload: null,
        modalReportLoading: { hidden: true }, modalReportError: { hidden: true }, modalReportErrorMsg: {},
        modalReportWrapper: { hidden: true }, modalPrintReportBtn: { disabled: false, addEventListener() {} },
        modalReportYearHint: {}, modalReportYearFilter: {
            value: "2026", disabled: false, replaceChildren() {}, appendChild() {},
            addEventListener: (event, handler) => { handlers.year = handler; },
        },
        document: {
            createElement: () => ({}),
            getElementById: id => id === "formattedReportModal" ? { addEventListener: (event, handler) => { handlers.close = handler; } } : null,
        },
        window: { location: { pathname: "/clients/7/", search: "", assign() {} }, setTimeout() {} },
        shared: { parseJsonSafe: async response => response.payload }, requests: [], rendered: [],
        getSelectedModalReportYear: () => context.modalReportYearFilter.value,
        populateModalReportYearOptions: payload => { context.years = payload.available_years; context.modalReportYearFilter.value = "2026"; context.modalReportYearFilter.disabled = false; },
        renderModalReportForSelectedYear: () => { context.rendered.push(context.modalReportSourcePayload); context.modalLatestReport = context.modalReportSourcePayload; },
        showReportModal() {}, printModalLedgerLayout() {},
        fetch: async (url, options) => {
            const params = new URL(url, "https://example.test").searchParams;
            context.requests.push(params);
            assert.equal(options.credentials, "same-origin");
            if (context.reply) return context.reply(params, options);
            return { status: 200, ok: true, payload: params.has("years_only") ? { ok: true, available_years: [2026, 2025] } : { ok: true, rows: [{ entry_date: `${params.get("date_from").slice(0, 4)}-09-03`, amount: "1.00" }] } };
        },
    };
    vm.createContext(context);
    vm.runInContext(loader + events + "\nthis.load = loadModalReport; setupModalReportEvents();", context);
    context.handlers = handlers;
    return context;
};

(async () => {
    const report = makeReport();
    await report.load();
    assert.equal(report.requests.length, 2);
    assert.equal(report.requests[0].get("years_only"), "1");
    assert.equal(report.requests[0].has("date_from"), false);
    assert.equal(report.requests[1].get("date_from"), "2026-01-01");
    assert.equal(report.requests[1].get("date_to"), "2026-12-31");
    assert.equal(report.modalPrintReportBtn.disabled, false);
    report.modalReportYearFilter.value = "2025";
    await report.load(false);
    assert.equal(report.requests.at(-1).get("date_from"), "2025-01-01");

    report.modalReportYearFilter.value = "all";
    report.reply = async () => ({ status: 400, ok: false, payload: { ok: false, code: "workload_limit", message: "Select a narrower year range." } });
    await report.load(false);
    assert.equal(report.requests.at(-1).get("date_from"), "2000-01-01");
    assert.equal(report.modalReportError.hidden, false);
    assert.equal(report.modalReportErrorMsg.textContent, "Select a narrower year range.");
    assert.equal(report.modalPrintReportBtn.disabled, true);
    assert.equal(report.modalLatestReport, null);
    assert.equal(report.modalReportWrapper.hidden, true);
    assert.equal(report.modalReportYearFilter.disabled, false);
    assert(!report.modalReportYearHint.textContent.includes("Loading"));
    report.reply = null;
    report.modalReportYearFilter.value = "2026";
    await report.load(false);
    assert.equal(report.modalReportError.hidden, true);
    assert.equal(report.modalPrintReportBtn.disabled, false);

    const stale = makeReport();
    let release;
    stale.reply = () => new Promise(resolve => { release = resolve; });
    const pending = stale.load(false);
    stale.reply = null;
    stale.modalReportYearFilter.value = "2025";
    await stale.load(false);
    release({ status: 200, ok: true, payload: { ok: true, rows: [{ entry_date: "2026-09-03" }] } });
    await pending;
    assert.equal(stale.rendered.length, 1);
    assert.equal(stale.rendered[0].rows[0].entry_date, "2025-09-03");

    const cancelled = makeReport();
    cancelled.reply = () => new Promise(resolve => { release = resolve; });
    const closing = cancelled.load(false);
    cancelled.handlers.close();
    release({ status: 200, ok: true, payload: { ok: true, rows: [] } });
    await closing;
    assert.equal(cancelled.rendered.length, 0);
    assert.equal(cancelled.modalPrintReportBtn.disabled, true);

    for (const name of ["analytics", "client_details"]) {
        const source = read(`templates/base/${name}.html`);
        assert(source.includes('id="analyticsLoadError" role="alert"'));
        assert(source.includes("showToast(message, \"danger\")"));
    }
    const financial = read("templates/base/financial_records_client.html");
    assert(financial.includes('id="financialLoadError" role="alert"'));
    const failure = extract(financial, "        const setRecordsLoadFailure =", "        const loadRecordsFromApi =");
    const nodes = { financialLoadError: {}, financialEmptyState: {}, periodEntriesTag: {}, summaryCard: {} };
    const context = { document: { getElementById: id => nodes[id], querySelector: () => nodes.summaryCard }, financialEmptyState: nodes.financialEmptyState, periodEntriesTag: nodes.periodEntriesTag };
    vm.runInNewContext(failure + '\nsetRecordsLoadFailure("Narrow the period.");', context);
    assert.equal(nodes.financialLoadError.textContent, "Narrow the period.");
    assert.equal(nodes.financialEmptyState.hidden, true);
    assert.equal(nodes.periodEntriesTag.textContent, "Not loaded");
    assert.equal(nodes.summaryCard.hidden, true);
    const workflowFlow = extract(details, "        const setClientWorkflowUnavailable =", "        const normalizeClientProfile =");
    const workflowNodes = {
        clientWorkflowCard: {setAttribute(name, value) {this[name] = value;}},
        clientPeriodReadinessTag: {classList: {remove() {}, add() {}}},
        clientPeriodReadinessText: {}, clientPeriodReadinessHint: {}, clientWorkflowScheduleList: {},
    };
    const workflowContext = {...workflowNodes, document: {getElementById: id => workflowNodes[id]},
        latestClientWorkflowStatus: {has_current_period_record: true}, escapeHtml: text => String(text)};
    vm.createContext(workflowContext);
    vm.runInContext(workflowFlow + '\nthis.unavailable = setClientWorkflowUnavailable; this.apply = applyClientWorkflowStatus;', workflowContext);
    workflowContext.apply({});
    assert.equal(workflowContext.latestClientWorkflowStatus, null);
    assert.equal(workflowNodes.clientPeriodReadinessTag.textContent, "Not loaded");
    assert(!workflowNodes.clientWorkflowScheduleList.innerHTML.includes("No monthly record"));
    workflowContext.unavailable(true);
    assert.equal(workflowNodes.clientWorkflowCard["aria-busy"], "true");
    assert.equal(workflowNodes.clientPeriodReadinessTag.textContent, "Checking");
    workflowContext.apply({overall_status: "ready", schedule_items: [{frequency_label: "Monthly", period_label: "Oct 2026", status: "ready", has_record: true, entry_count: 5, transaction_detail_count: 20}]});
    assert.equal(workflowNodes.clientPeriodReadinessTag.textContent, "Records ready");
    assert.equal(workflowNodes.clientWorkflowCard["aria-busy"], "false");
    console.log("Workload/report tests passed: selected-year loading, no stale or partial prints, recovery, close cancellation, accessible errors, template syntax.");
})().catch(error => { console.error(error); process.exitCode = 1; });
