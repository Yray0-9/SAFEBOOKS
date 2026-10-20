const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const template = fs.readFileSync(path.resolve(__dirname, "../../../templates/authentication/login.html"), "utf8");
const start = template.indexOf('            loginForm.addEventListener("submit",');
const end = template.indexOf("            if (adminTwoFactorForm)", start);
const clearStart = template.indexOf("            const clearLoginFieldErrors =");
const clearEnd = template.indexOf("            const setupLoginInputListeners =", clearStart);
assert(start >= 0 && end > start && clearStart >= 0 && clearEnd > clearStart);

const classes = () => ({values: new Set(), add(value) {this.values.add(value);}, remove(value) {this.values.delete(value);}});
const passwordField = {classList: classes()};
const input = () => ({
    value: "Synthetic draft only", classList: classes(),
    closest() {return this === password ? passwordField : null;},
    focus() {assert(!this.disabled, "Focus must wait until the field is enabled"); this.focused = true;},
    select() {assert(!this.disabled); this.selected = true;},
});
const identifier = input(), password = input();
let handler, requests = 0;
const context = {
    redirecting: false, loginFeedback: null, csrfToken: "synthetic-only", payload: null,
    valid: true,
    loginForm: {
        addEventListener(name, callback) {handler = callback;},
        checkValidity() {return context.valid;}, reportValidity() {context.reportedValidity = true;},
    },
    document: {getElementById(id) {return id === "login_identifier" ? identifier : password;}},
    window: {location: {search: ""}}, URLSearchParams,
    clearSkeletonState() {},
    setSubmittingState(value) {
        context.submitting = value;
        identifier.disabled = password.disabled = value;
    },
    setFeedback(message, level) {context.feedback = {message, level};},
    showTwoFactorSection(role, message) {context.twoFactor = {role, message};},
    finishSuccessfulLogin(result) {context.signedIn = result;},
    async fetch(url, options) {
        requests++;
        context.lastPayload = JSON.parse(options.body);
        if (context.networkError) throw new Error("Synthetic network interruption");
        return context.response;
    },
};
vm.runInNewContext(template.slice(clearStart, clearEnd) + template.slice(start, end), context);
(async () => {
    for (const [identifierValue, passwordValue, message, focus] of [
        ["", "", "Please enter your email or username and password.", identifier],
        ["synthetic@example.test", "", "Please enter your password.", password],
        ["", "Synthetic draft only", "Please enter your email or username.", identifier],
        ["   ", "Synthetic draft only", "Please enter your email or username.", identifier],
        ["   ", "", "Please enter your email or username and password.", identifier],
    ]) {
        identifier.value = identifierValue;
        password.value = passwordValue;
        identifier.focused = password.focused = false;
        const before = requests;
        await handler({preventDefault() {}});
        assert.equal(requests, before, "Missing fields must not send a login request");
        assert.equal(context.feedback.message, message);
        assert.equal(context.feedback.level, "error");
        assert.equal(identifier.classList.values.has("is-invalid"), !identifierValue.trim());
        assert.equal(password.classList.values.has("is-invalid"), !passwordValue);
        assert.equal(passwordField.classList.values.has("is-invalid"), !passwordValue);
        assert.equal(focus.focused, true);
        assert.equal(identifier.value, identifierValue);
        assert.equal(password.value, passwordValue);
    }

    identifier.value = password.value = "Synthetic draft only";
    context.valid = false;
    const beforeInvalid = requests;
    await handler({preventDefault() {}});
    assert.equal(requests, beforeInvalid);
    assert.equal(context.reportedValidity, true);
    assert.equal(context.feedback.message, "Please check the highlighted sign-in fields.");
    context.valid = true;

    for (const [response, expectedField] of [
        [{status: 429, ok: false, json: async () => ({ok: false, error_code: "login_rate_limited", message: "Please wait up to 300 seconds."})}, ""],
        [{status: 503, ok: false, json: async () => ({ok: false, error_code: "login_unavailable", message: "Sign-in is temporarily unavailable."})}, ""],
        [{status: 200, ok: true, json: async () => ({ok: false, field: "password", error_code: "invalid_credentials", message: "Incorrect password. Please try again."})}, "password"],
        [{status: 200, ok: true, json: async () => ({ok: false, field: "identifier", error_code: "invalid_credentials", message: "No account found with that email or username."})}, "identifier"],
    ]) {
        context.response = response;
        identifier.focused = password.focused = false;
        identifier.selected = password.selected = false;
        const before = requests;
        await handler({preventDefault() {}});
        assert.equal(requests, before + 1, "Never automatically retry sign-in");
        assert.equal(context.submitting, false);
        assert.equal(identifier.value, "Synthetic draft only");
        assert.equal(password.value, "Synthetic draft only");
        assert.equal(context.feedback.level, response.status === 429 ? "warning" : "error");
        assert.equal(context.signedIn, undefined);
        assert.equal(context.twoFactor, undefined);
        assert.equal(identifier.classList.values.has("is-invalid"), expectedField === "identifier");
        assert.equal(password.classList.values.has("is-invalid"), expectedField === "password");
        assert.equal(passwordField.classList.values.has("is-invalid"), expectedField === "password");
        assert.equal(identifier.focused, expectedField === "identifier");
        assert.equal(password.focused, expectedField === "password");
        assert.equal(identifier.selected, expectedField === "identifier");
        assert.equal(password.selected, expectedField === "password");
        assert.equal(context.feedback.message, (await response.json()).message);
    }

    for (const [identifierValue, expectedField, message] of [
        ["synthetic@example.test", "password", "Incorrect password. Please try again."],
        ["unknown@example.test", "identifier", "No account found with that email or username."],
        ["unknown-username", "identifier", "No account found with that email or username."],
        ["admin@example.test", "password", "Incorrect password. Please try again."],
    ]) {
        identifier.value = identifierValue;
        identifier.focused = password.focused = false;
        identifier.selected = password.selected = false;
        context.response = {status: 200, ok: true, json: async () => ({ok: false, field: expectedField, error_code: "invalid_credentials", message})};
        const before = requests;
        await handler({preventDefault() {}});
        assert.equal(requests, before + 1);
        assert.equal(identifier.value, identifierValue);
        assert.equal(identifier.classList.values.has("is-invalid"), expectedField === "identifier");
        assert.equal(identifier.focused, expectedField === "identifier");
        assert.equal(password.classList.values.has("is-invalid"), expectedField === "password");
        assert.equal(passwordField.classList.values.has("is-invalid"), expectedField === "password");
        assert.equal(password.focused, expectedField === "password");
        assert.equal(password.selected, expectedField === "password");
        assert.equal(context.feedback.message, message);
    }

    // Correcting a blank field must clear its earlier red border even when
    // the next, fully populated attempt still fails authentication.
    identifier.value = "";
    await handler({preventDefault() {}});
    assert.equal(identifier.classList.values.has("is-invalid"), true);
    identifier.value = "synthetic@example.test";
    await handler({preventDefault() {}});
    assert.equal(identifier.classList.values.has("is-invalid"), false);
    assert.equal(password.classList.values.has("is-invalid"), true);

    password.value = "";
    await handler({preventDefault() {}});
    assert.equal(passwordField.classList.values.has("is-invalid"), true);
    password.value = "Synthetic draft only";
    context.response = {status: 200, ok: true, json: async () => ({ok: false, field: "identifier", error_code: "invalid_credentials", message: "No account found with that email or username."})};
    await handler({preventDefault() {}});
    assert.equal(identifier.classList.values.has("is-invalid"), true);
    assert.equal(password.classList.values.has("is-invalid"), false);
    assert.equal(passwordField.classList.values.has("is-invalid"), false);

    identifier.value = "  synthetic@example.test  ";
    password.value = "   ";
    await handler({preventDefault() {}});
    assert.equal(context.lastPayload.identifier, "synthetic@example.test");
    assert.equal(context.lastPayload.password, "   ", "Never trim or change a submitted password");

    identifier.value = password.value = "Synthetic draft only";
    context.response = {status: 200, ok: true, json: async () => ({ok: true, requires_two_factor: true, role: "bookkeeper", message: "Enter your code."})};
    await handler({preventDefault() {}});
    assert.equal(context.twoFactor.role, "bookkeeper");
    assert.equal(context.signedIn, undefined);

    context.response = {status: 200, ok: true, json: async () => ({ok: true, redirect_url: "/dashboard/"})};
    await handler({preventDefault() {}});
    assert.equal(context.signedIn.redirect_url, "/dashboard/");

    context.networkError = true;
    const beforeNetwork = requests;
    await handler({preventDefault() {}});
    assert.equal(requests, beforeNetwork + 1);
    assert.equal(context.submitting, false);
    assert.equal(identifier.value, "Synthetic draft only");
    assert.equal(password.value, "Synthetic draft only");
    assert.equal(context.feedback.level, "error");
    console.log("Login field-specific errors, missing-field, focus, throttling, draft, 2FA, success, and network-failure checks passed.");
})().catch(error => {console.error(error); process.exitCode = 1;});
