const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../../..");
const shared = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, "static/js/reports_shared.js"), "utf8"), shared);

for (const naming of ["snake", "camel"]) {
    const client = {
        client_name: '<img src=x onerror="alert(1)">',
        tin_number: "123456789000",
        custom_fields: [
            { label: "Portal PIN", value: "PrivatePINMarker", type: " Password " },
            { label: "Legacy Email Password", value: "PrivateLegacyMarker", type: "text" },
            { label: "Ledger", value: "Nonsecret custom value", type: "text" },
        ],
    };
    const keys = naming === "snake"
        ? ["email_password", "orus_password", "orus_account"]
        : ["emailPassword", "orusPassword", "orusAccount"];
    keys.forEach((key, index) => { client[key] = ["PrivateEmailMarker", "PrivateORUSMarker", "PrivateORUSAccountMarker"][index]; });
    const html = shared.window.SafeBooksReportsShared.buildReportSheetHtml({
        client,
        printedBy: "Synthetic Printer",
        includePasswords: true, // An untrusted caller cannot opt credentials into a report.
        table: { columns: ["Period", "Sales", "Expenses"], rows: [["Jan 2026", "123.45", "25.00"]] },
    });
    for (const value of ["PrivateEmailMarker", "PrivateORUSMarker", "PrivateORUSAccountMarker", "PrivatePINMarker", "PrivateLegacyMarker"]) {
        assert(!html.includes(value), "Report leaked a synthetic private value");
    }
    assert(!html.includes("Email Password"));
    assert(!html.includes("ORUS Password"));
    assert(html.includes("Nonsecret custom value"));
    assert(html.includes("Printed by: Synthetic Printer"));
    assert(html.includes("Jan 2026"));
    assert(html.includes("123.45"));
    assert(html.includes("reports-ledger-totals-row"));
    assert(!html.includes('<img src=x onerror="alert(1)">'));
    assert(html.includes("&lt;img"));
}

vm.runInNewContext(fs.readFileSync(path.join(root, "static/js/client_tax_registration.js"), "utf8"), shared);
const registration = shared.window.SafeBooksClientRegistration;
assert.equal(registration.label('vat'), 'VAT');
assert.equal(registration.label('non_vat'), 'Non-VAT');
assert.equal(registration.label(''), 'Not set');
for (const invalid of [null, undefined, true, {}, '__proto__', '<img src=x onerror=alert(1)>']) {
    const badge = registration.badge(invalid);
    assert(badge.includes('Tax registration not set'));
    assert(!badge.includes('<img') && !badge.includes('onerror'));
}
for (const value of ['vat', 'non_vat', '']) {
    assert(registration.badge(value).includes(`Tax registration: ${registration.label(value)}`));
}
for (const page of ['clients', 'client_details', 'financial_records', 'financial_records_client']) {
    const source = fs.readFileSync(path.join(root, `templates/base/${page}.html`), 'utf8');
    assert(source.includes('js/client_tax_registration.js'));
    assert(source.includes('css/client_tax_registration.css'));
    for (const match of source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
        if (!match[1].trim() || /type=["']application\/json/.test(match[0])) continue;
        new vm.Script(match[1].replace(/\{%[\s\S]*?%\}/g, '').replace(/\{\{[\s\S]*?\}\}/g, 'synthetic-value'));
    }
}
console.log('Tax registration labels, unknown values, safe badges, page wiring and script syntax passed.');

const template = fs.readFileSync(path.join(root, "templates/base/clients.html"), "utf8");
const start = template.indexOf("        const openEditModal = async");
const end = template.indexOf("        const openDeleteModal =", start);
assert(start >= 0 && end > start, "Protected edit loader missing");
const loader = template.slice(start, end) + "\nthis.testOpenEditor = openEditModal;";

const makeEditor = (response) => {
    const context = {
        clientProfileRequestToken: 0,
        editClientModal: { show() { context.shown = true; } },
        getClientDataFromRow: () => ({ clientId: 7, clientName: "Selected Client" }),
        buildClientDetailApiUrl: id => `/api/clients/${id}/`,
        showToast: () => {},
        fetch: async (url, options) => {
            assert.equal(url, "/api/clients/7/");
            assert.equal(options.method, "GET");
            assert.equal(options.credentials, "same-origin");
            return response;
        },
        parseJsonSafe: async res => res.payload,
        mapClientFromApi: client => client,
        setEditFormData: (row, client) => { context.loaded = client; },
        renderCustomFields: () => {},
        editClientCustomFields: {},
        redirectToLogin: () => { context.redirected = true; },
        openClientAccessConfirmModal: (client, url, callback) => { context.confirm = callback; },
    };
    vm.runInNewContext(loader, context);
    return context;
};

const confirmStart = template.indexOf("        const openClientAccessConfirmModal =");
const confirmEnd = template.indexOf("        const navigateToClientDetails =", confirmStart);
assert(confirmStart >= 0 && confirmEnd > confirmStart, "Password confirmation flow missing");
const confirmation = template.slice(confirmStart, confirmEnd)
    + "\nthis.openConfirmation = openClientAccessConfirmModal; this.confirmAccess = confirmClientDetailsAccess;";

const makeConfirmation = (response) => {
    const hiddenCallbacks = [];
    const context = {
        pendingClientDetailsTarget: null,
        clientDetailsVerifiedUntil: 0,
        CLIENT_DETAILS_ACCESS_CONFIRM_URL: "/api/security/client-details-access/confirm/",
        clientAccessConfirmClientName: { textContent: "" },
        clientAccessConfirmPassword: { value: "", focus() { context.focused = true; } },
        setClientAccessStatus: (message, variant) => { context.status = { message, variant }; },
        setClientAccessLoading: loading => { context.loading = loading; },
        showToast: () => {},
        getCookieValue: () => "synthetic-csrf",
        parseJsonSafe: async res => res.payload,
        redirectToLogin: () => { context.redirected = true; },
        window: { location: { assign(url) { context.destination = url; } } },
        clientAccessConfirmModalElement: {
            addEventListener(event, callback, options) {
                assert.equal(event, "hidden.bs.modal");
                assert.equal(options.once, true);
                hiddenCallbacks.push(callback);
            },
        },
        clientAccessConfirmModal: {
            show() { context.shown = true; },
            hide() {
                context.pendingClientDetailsTarget = null;
                hiddenCallbacks.splice(0).forEach(callback => callback());
            },
        },
        fetch: async (url, options) => {
            assert.equal(url, context.CLIENT_DETAILS_ACCESS_CONFIRM_URL);
            assert.equal(options.method, "POST");
            assert.equal(options.headers["X-CSRFToken"], "synthetic-csrf");
            assert.deepEqual(JSON.parse(options.body), { current_password: "SyntheticConfirmation#123", client_id: 7 });
            return response;
        },
    };
    vm.runInNewContext(confirmation, context);
    return context;
};

(async () => {
    const profile = { clientId: 7, emailPassword: "SyntheticSavedPassword", customFields: [] };
    const success = makeEditor({ status: 200, ok: true, payload: { ok: true, client: profile } });
    await success.testOpenEditor({ isConnected: true });
    assert.equal(success.loaded, profile);
    assert.equal(success.shown, true);

    const locked = makeEditor({ status: 403, ok: false, payload: { ok: false, client_access_required: true } });
    await locked.testOpenEditor({ isConnected: true });
    assert.equal(typeof locked.confirm, "function");
    assert.equal(locked.loaded, undefined);
    assert.equal(locked.shown, undefined);

    const missing = makeEditor({ status: 404, ok: false, payload: { ok: false, message: "Client not found." } });
    await missing.testOpenEditor({ isConnected: true });
    assert.equal(missing.loaded, undefined);
    assert.equal(missing.shown, undefined);

    const disconnected = makeEditor({ status: 200, ok: true, payload: { ok: true, client: profile } });
    await disconnected.testOpenEditor({ isConnected: false });
    assert.equal(disconnected.loaded, undefined);

    const expired = makeEditor({ status: 401, ok: false, payload: { ok: false } });
    await expired.testOpenEditor({ isConnected: true });
    assert.equal(expired.redirected, true);
    assert.equal(expired.loaded, undefined);

    const failure = makeEditor(null);
    failure.fetch = async () => { throw new Error("Synthetic network failure"); };
    await failure.testOpenEditor({ isConnected: true });
    assert.equal(failure.loaded, undefined);
    assert.equal(failure.shown, undefined);

    const confirmed = makeConfirmation({ status: 200, ok: true, payload: { ok: true } });
    let editorOpened = 0;
    confirmed.openConfirmation({ clientId: 7, clientName: "Selected Client" }, "", () => { editorOpened += 1; });
    assert.equal(confirmed.clientAccessConfirmPassword.value, "");
    confirmed.clientAccessConfirmPassword.value = "SyntheticConfirmation#123";
    await confirmed.confirmAccess();
    assert.equal(editorOpened, 1);
    assert.equal(confirmed.pendingClientDetailsTarget, null);
    assert.equal(confirmed.loading, false);
    assert.equal(confirmed.destination, undefined);

    const cancelled = makeConfirmation({ status: 200, ok: true, payload: { ok: true } });
    cancelled.openConfirmation({ clientId: 7 }, "/clients/7/");
    cancelled.clientAccessConfirmPassword.value = "SyntheticConfirmation#123";
    cancelled.fetch = async () => {
        cancelled.pendingClientDetailsTarget = null; // User closes the modal while the request is pending.
        return { status: 200, ok: true, payload: { ok: true } };
    };
    await cancelled.confirmAccess();
    assert.equal(cancelled.destination, undefined);

    const retry = makeConfirmation({ status: 400, ok: false, payload: { ok: false, message: "Incorrect password." } });
    retry.openConfirmation({ clientId: 7 }, "/clients/7/");
    await retry.confirmAccess();
    assert.equal(retry.focused, true);
    assert.equal(retry.status.variant, "danger");
    retry.clientAccessConfirmPassword.value = "SyntheticConfirmation#123";
    await retry.confirmAccess();
    assert.equal(retry.status.message, "Incorrect password.");
    assert.equal(retry.loading, false);
    assert.equal(retry.destination, undefined);
    assert.equal(retry.clientAccessConfirmPassword.value, "SyntheticConfirmation#123");
    console.log("Shared report privacy and protected editor component checks passed.");
})().catch(error => { console.error(error); process.exitCode = 1; });
