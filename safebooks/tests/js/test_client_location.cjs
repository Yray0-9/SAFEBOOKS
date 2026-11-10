const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.resolve(__dirname, "../../../templates/base/partials/client_location_selector_script.html"), "utf8");
const makeControl = () => ({
    value: "", options: [], attributes: {}, listeners: {},
    set innerHTML(value) { this.options = []; this.value = ""; },
    appendChild(option) { this.options.push(option); if (option.selected) this.value = option.value; },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    setCustomValidity(message) { this.validationMessage = message; },
    addEventListener(event, callback) { this.listeners[event] = callback; },
});
const context = {
    AbortController,
    document: {createElement: () => ({})},
    window: {setTimeout, clearTimeout},
    fetch: async url => {
        if (context.failRequests) throw new Error("Synthetic location service failure");
        const data = url.endsWith("/provinces")
            ? [{code: "province", name: "New Province"}]
            : url.endsWith("/cities-municipalities")
                ? [{code: "city", name: "New City"}]
                : [{code: "barangay", name: "New Barangay"}];
        return {ok: true, json: async () => ({data})};
    },
};
vm.createContext(context);
vm.runInContext(source + "\nthis.create = createLocationState; this.apply = applyLocationSelection; this.bind = bindLocationControls; this.change = handleLocationSelectChange; this.sync = syncLocationState; this.clearCache = () => locationApiCache.clear();", context);
const settle = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
const makeState = () => context.create({
    hiddenInput: {value: ""}, select: makeControl(), summary: {dataset: {}, hidden: true},
});

(async () => {
    const state = makeState();
    context.bind(state);
    await settle();
    const original = "Original Province, Original City, Original Barangay";
    context.apply(state, original);
    context.sync(state);
    assert.equal(state.hiddenInput.value, original, "Untouched saved locations must be retained");

    state.select.value = "province";
    context.change(state);
    assert.equal(state.hiddenInput.value, "", "A new selection must stop submitting the old address");
    assert(state.select.validationMessage, "A partial location must block saving");
    await settle();
    state.select.value = "city";
    context.change(state);
    await settle();
    assert.equal(state.hiddenInput.value, "");
    state.select.value = "barangay";
    context.change(state);
    context.sync(state);
    const updated = "New Province, New City, New Barangay";
    assert.equal(state.hiddenInput.value, updated);
    assert.equal(state.summary.textContent, updated);
    assert.equal(state.select.validationMessage, "");
    context.apply(state, updated);
    context.sync(state);
    assert.equal(state.hiddenInput.value, updated, "Reopening must retain the confirmed address");

    state.select.value = "province";
    context.change(state);
    await settle();
    context.apply(state, updated);
    assert.equal(state.hiddenInput.value, updated, "Cancelling a partial replacement must allow restoring the saved address");

    context.clearCache();
    context.failRequests = true;
    const offlineState = makeState();
    context.apply(offlineState, original);
    await settle();
    context.sync(offlineState);
    assert.equal(offlineState.hiddenInput.value, original, "Service failure must preserve a saved location");
    assert.equal(offlineState.summary.dataset.locationStatus, "error");
    console.log("Location regression passed for saved addresses, complete replacements, partial validation, reopening, cancelled edits and service failure.");
})().catch(error => { console.error(error); process.exitCode = 1; });
