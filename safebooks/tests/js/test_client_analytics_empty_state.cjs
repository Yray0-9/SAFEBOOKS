/* Run the actual template's empty-state and request handlers with synthetic data. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const template = fs.readFileSync(path.resolve(__dirname, "../../../templates/base/client_details.html"), "utf8").replace(/\r\n/g, "\n");
const extract = (start, end) => {
    const first = template.indexOf(start), last = template.indexOf(end, first);
    assert(first >= 0 && last > first, `Missing template flow: ${start}`);
    return template.slice(first, last).replace(/\{%[\s\S]*?%\}/g, "/synthetic-login/");
};
const flow = extract("        const updateAnalyticsEmptyMessage =", "        const setClientDetailsSaving =");
const payload = hasData => ({ok: true, has_data: hasData, summary: {total_sales: hasData ? 125 : 0}, monthly_trend: [], client_workflow: {}});
const makePage = () => {
    const page = {
        CLIENT_ID: 7, ANALYTICS_SUMMARY_API_URL: "/api/analytics/summary/", URLSearchParams, AbortController,
        analyticsEmptyMessage: {}, analyticsEmptyState: {hidden: true}, analyticsDataPanels: {hidden: true},
        analyticsScopeHint: {}, analyticsYearFilter: {value: "2024", disabled: false}, analyticsHorizonFilter: {value: "3"},
        analyticsTotalSalesValue: {}, analyticsTotalExpensesValue: {}, analyticsTotalTaxValue: {}, analyticsNetValueValue: {},
        currentClientProfile: {client_name: "Synthetic Client", tin_number: ""},
        analyticsRequestToken: 0, analyticsAbortController: null,
        formatCurrency: value => `PHP ${value}`, formatTin: value => value,
        renderTrend() {}, applyTimeframeCaptions() {}, applyPredictiveForecast() {},
        renderPredictiveForecastReport() {}, renderForecastProjectionChart() {},
        applyClientWorkflowStatus() {}, setClientWorkflowUnavailable() {},
        setAnalyticsLoadingState: loading => { page.loading = loading; if (loading) page.analyticsEmptyState.hidden = true; },
        error: {hidden: true}, requests: [], toasts: [], redirects: [],
        document: {getElementById: () => page.error},
        window: {location: {pathname: "/clients/7/", search: "", assign: url => page.redirects.push(url)}},
        showToast: (message, type) => page.toasts.push({message, type}),
        shared: {parseJsonSafe: async response => response.payload},
        fetch: async (url, options) => {
            page.requests.push(new URL(url, "https://example.test").searchParams);
            assert.equal(options.credentials, "same-origin");
            return page.reply ? page.reply(url, options) : {status: 200, ok: true, payload: payload(false)};
        },
    };
    vm.createContext(page);
    vm.runInContext(flow + "\nthis.load = loadAnalyticsSummaryFromApi; this.apply = applyAnalyticsPayload;", page);
    return page;
};

(async () => {
    assert(template.includes('id="analyticsEmptyMessage"'));
    assert(!template.includes("No financial records yet for this client."));
    const page = makePage();
    await page.load();
    assert.equal(page.requests[0].get("year"), "2024");
    assert.equal(page.analyticsEmptyState.hidden, false);
    assert.equal(page.analyticsDataPanels.hidden, true);
    assert(page.analyticsEmptyMessage.textContent.includes("for 2024"));
    assert(page.analyticsEmptyMessage.textContent.includes("Choose All Time or another year"));
    assert(!page.analyticsEmptyMessage.textContent.includes("no saved records"));
    assert.equal(page.analyticsYearFilter.disabled, false);

    page.analyticsYearFilter.value = "all";
    page.reply = async () => ({status: 200, ok: true, payload: payload(true)});
    await page.load();
    assert.equal(page.requests.at(-1).has("year"), false);
    assert.equal(page.analyticsEmptyState.hidden, true);
    assert.equal(page.analyticsDataPanels.hidden, false);
    assert.equal(page.analyticsTotalSalesValue.textContent, "PHP 125");

    page.reply = null;
    await page.load();
    assert.equal(page.analyticsEmptyState.hidden, false);
    assert(!page.analyticsEmptyMessage.textContent.includes("for 2024"));
    assert(!page.analyticsEmptyMessage.textContent.includes("Choose All Time"));
    assert(page.analyticsEmptyMessage.textContent.includes("Review the financial records"));
    page.analyticsYearFilter.value = "2025";
    await page.load();
    assert(page.analyticsEmptyMessage.textContent.includes("for 2025"));

    for (const status of [400, 503]) {
        page.reply = async () => ({status, ok: false, payload: {ok: false, message: "Synthetic load failure"}});
        await page.load();
        assert.equal(page.analyticsEmptyState.hidden, true);
        assert.equal(page.error.hidden, false);
        assert.equal(page.error.textContent, "Synthetic load failure");
        assert.equal(page.loading, false);
    }
    page.reply = async () => {throw new Error("Synthetic network interruption");};
    await page.load();
    assert.equal(page.analyticsEmptyState.hidden, true);
    assert.equal(page.error.hidden, false);
    assert.equal(page.loading, false);
    page.reply = null;
    await page.load();
    assert.equal(page.error.hidden, true);
    assert.equal(page.analyticsEmptyState.hidden, false);

    page.reply = async () => ({status: 401});
    await page.load();
    assert.equal(page.analyticsEmptyState.hidden, true);
    assert.equal(page.redirects.length, 1);

    const stale = makePage();
    let release;
    stale.reply = () => new Promise(resolve => {release = resolve;});
    const oldRequest = stale.load();
    stale.reply = null;
    stale.analyticsYearFilter.value = "2025";
    await stale.load();
    release({status: 200, ok: true, payload: payload(true)});
    await oldRequest;
    assert.equal(stale.analyticsEmptyState.hidden, false);
    assert(stale.analyticsEmptyMessage.textContent.includes("for 2025"));

    const delayedJson = makePage();
    delayedJson.shared.parseJsonSafe = response => response.delayed
        ? new Promise(resolve => {release = resolve;}) : Promise.resolve(response.payload);
    delayedJson.reply = async () => ({status: 200, ok: true, delayed: true});
    const parsing = delayedJson.load();
    await new Promise(resolve => setImmediate(resolve));
    delayedJson.reply = null;
    delayedJson.analyticsYearFilter.value = "2025";
    await delayedJson.load();
    release(payload(true));
    await parsing;
    assert.equal(delayedJson.analyticsEmptyState.hidden, false);
    assert(delayedJson.analyticsEmptyMessage.textContent.includes("for 2025"));

    const missingMessage = makePage();
    missingMessage.analyticsEmptyMessage = null;
    missingMessage.apply(payload(false));
    assert.equal(missingMessage.analyticsEmptyState.hidden, false);
    console.log("Client analytics empty-state tests passed: year scope, All Time, zero totals, recovery, failures, stale responses and unchanged controls.");
})().catch(error => {console.error(error); process.exitCode = 1;});
