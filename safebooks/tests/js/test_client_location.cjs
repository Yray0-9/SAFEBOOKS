const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.resolve(__dirname, "../../../templates/base/partials/client_location_selector_script.html"), "utf8");
const control = () => ({
    id: "location", value: "", attributes: {}, listeners: {}, children: [],
    classList: {add() {}, remove() {}},
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    setCustomValidity(value) { this.validationMessage = value; },
    addEventListener(key, callback) { this.listeners[key] = callback; },
    append(...nodes) { this.children.push(...nodes); },
    replaceChildren() { this.children = []; },
    dispatchEvent(event) { this.listeners[event.type]?.(event); },
    click() { this.listeners.click(); },
    scrollIntoView() {},
});
const region = "Region XI (Davao Region)";
const province = "Davao del Norte";
const city = "City of Tagum";
const ncr = "National Capital Region (NCR)";
const data = {
    "/regions": [{code:"1100000000", name:region}, {code:"1300000000", name:ncr}],
    "/regions/1100000000/provinces": [{code:"1102300000", name:province, region}],
    "/regions/1100000000/cities-municipalities": [
        {code:"1102319000", name:city, type:"CC", region, province},
        {code:"1102301000", name:"Asuncion", type:"Mun", region, province},
    ],
    "/regions/1100000000/barangays": [
        {code:"1102319001", name:"Apokon", province, city_municipality:city},
        {code:"1102301001", name:"Apokon", province, city_municipality:"Asuncion"},
    ],
};
const results = control();
const requests = [];
const context = {
    AbortController, Event,
    document: {getElementById: () => results, createElement: control},
    window: {setTimeout, clearTimeout},
    fetch: async (url) => {
        const endpoint = new URL(url).pathname.replace("/api/v2", "");
        requests.push(endpoint);
        return {ok: endpoint !== context.failedPath, json: async () => ({data: data[endpoint]})};
    },
};
vm.createContext(context);
vm.runInContext(source + "\nthis.api = {createLocationState, applyLocationSelection, bindLocationControls, resetLocationState, searchLocations};", context);

(async () => {
    const {createLocationState, applyLocationSelection, bindLocationControls, resetLocationState, searchLocations} = context.api;
    const select = control();
    const hiddenInput = {value:""};
    const summary = {dataset:{}};
    const state = createLocationState({select, hiddenInput, summary});
    bindLocationControls(state);
    const saved = "Older Province, Older City, Older Barangay";
    applyLocationSelection(state, saved);
    assert.equal(hiddenInput.value, saved);
    assert.equal(requests.length, 0);

    context.failedPath = "/regions/1100000000/barangays";
    const partial = await searchLocations("apokon");
    assert.equal(partial.incomplete, true);
    assert.equal(partial.items.length, 0);
    assert.equal(hiddenInput.value, saved);

    context.failedPath = null;
    const locations = await searchLocations("apok tagum");
    assert.equal(locations.incomplete, false);
    assert.equal(locations.items[0].city.code, "1102319000");
    assert.equal(locations.items[0].province.code, "1102300000");
    assert.equal(locations.items[0].region.code, "1100000000");
    const duplicateMatches = await searchLocations("apokon");
    assert.equal(duplicateMatches.items.length, 2);
    assert.match(locations.items[0].hierarchy, /Tagum.*Davao del Norte.*Region XI/);
    assert.equal((await searchLocations("national capital")).items.length, 0);
    assert(requests.every(endpoint => endpoint === "/regions" || endpoint.startsWith("/regions/1100000000/")));
    assert.equal((await searchLocations("davao del nor")).items[0].level, "Province");
    assert.equal((await searchLocations("asunc")).items[0].level, "Municipality");
    assert.equal((await searchLocations("region xi davao")).items[0].level, "Region");
    assert.equal((await searchLocations("unmatched")).items.length, 0);

    select.value = "apok tagum";
    select.listeners.input();
    assert.equal(hiddenInput.value, "");
    assert.match(select.validationMessage, /Choose a location/);
    assert.equal(select.attributes["aria-busy"], "true");
    await new Promise(resolve => setTimeout(resolve, 300));
    assert.equal(results.children.length, 1);
    const key = (value) => select.listeners.keydown({key:value, preventDefault() {}, stopPropagation() {}});
    key("ArrowDown");
    key("Enter");
    assert.equal(hiddenInput.value, province + ", " + city + ", Apokon");
    assert.equal(state.selection.barangay.code, "1102319001");
    assert.equal(select.validationMessage, "");
    select.value = "other";
    select.listeners.input();
    key("Escape");
    assert.equal(hiddenInput.value, province + ", " + city + ", Apokon");

    resetLocationState(state);
    assert.equal(hiddenInput.value, "");
    assert.equal(results.hidden, true);
    console.log("Location selector passed hierarchy, duplicate names, retry, saved values, keyboard selection, and reset.");
})().catch(error => { console.error(error); process.exitCode = 1; });
