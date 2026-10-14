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
const validator = {};
vm.runInNewContext(dateValidation + payloadValidation + "\nthis.validate = validateEntryPayload;", validator);
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

const makeContext = (response) => {
    const listeners = {};
    const modalListeners = {};
    const nodes = {
        editEntryId: { value: "7" }, editEntryRevision: { value: "old-revision" },
        editEntryDate: { value: "2026-04-15" }, editEntryNotes: { value: "Unsaved draft" },
        editEntryFrequency: { value: "monthly" }, editEntryStatus: { hidden: true },
        deleteEntryStatus: { hidden: true }, addEntryDate: { value: "2026-04-15" },
        addEntryNotes: { value: "Unsaved new draft" }, addEntryFrequency: { value: "monthly" },
    };
    const form = (name) => ({
        addEventListener: (type, callback) => { listeners[`${name}:${type}`] = callback; },
        checkValidity: () => true, reportValidity() {},
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
        getEntryLineItems: entry => entry.line_items || [], resetLineItemsBody() {}, updateDuplicateEntryWarning() {},
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
            addEventListener(event, callback) {
                (modalListeners[`${type}:${event}`] ||= []).push(callback);
            },
        };
    }
    context.addEntryModal = { hide() { assert.equal(context.isAddSubmitting, false); context.addHidden = true; } };
    context.editEntryModal = { hide() { assert.equal(context.isEditSubmitting, false); context.editHidden = true; } };
    context.deleteEntryModal = { hide() { assert.equal(context.isDeleteSubmitting, false); context.deleteHidden = true; } };
    vm.createContext(context);
    vm.runInContext(formFunctions + feedback + submits + closing + "\nthis.populate = populateEditForm; this.build = buildPayloadFromForm;", context);
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
    assert.equal(editor.build("add").expected_revision, undefined);

    for (const type of ["add", "edit", "delete"]) {
        const saved = makeContext(successResponse);
        await saved.submit(type);
        assert.equal(saved.requests.length, 1);
        const options = saved.requests[0].options;
        assert.equal(options.headers["X-CSRFToken"], "synthetic-csrf");
        assert.equal(options.credentials, "same-origin");
        assert.equal(options.headers["Content-Type"], "application/json");
        assert.equal(JSON.parse(options.body).expected_revision, type === "add" ? undefined : "old-revision");
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
