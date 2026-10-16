const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const template = fs.readFileSync(path.resolve(__dirname, "../../../templates/authentication/login.html"), "utf8");
const start = template.indexOf('            loginForm.addEventListener("submit",');
const end = template.indexOf("            if (adminTwoFactorForm)", start);
assert(start >= 0 && end > start);

const input = () => ({value: "Synthetic draft only", classList: {add() {}}, closest() {return null;}, focus() {}, select() {}});
const identifier = input(), password = input();
let handler, requests = 0;
const context = {
    redirecting: false, loginFeedback: null, csrfToken: "synthetic-only", payload: null,
    loginForm: {addEventListener(name, callback) {handler = callback;}, checkValidity() {return true;}},
    document: {getElementById(id) {return id === "login_identifier" ? identifier : password;}},
    window: {location: {search: ""}}, URLSearchParams,
    clearSkeletonState() {}, clearLoginFieldErrors() {},
    setSubmittingState(value) {context.submitting = value;},
    setFeedback(message, level) {context.feedback = {message, level};},
    showTwoFactorSection() {throw new Error("A denial cannot start 2FA");},
    finishSuccessfulLogin() {throw new Error("A denial cannot sign in");},
    async fetch() {requests++; return context.response;},
};
vm.runInNewContext(template.slice(start, end), context);
(async () => {
    for (const response of [
        {status: 429, ok: false, json: async () => ({ok: false, error_code: "login_rate_limited", message: "Please wait up to 300 seconds."})},
        {status: 503, ok: false, json: async () => ({ok: false, error_code: "login_unavailable", message: "Sign-in is temporarily unavailable."})},
        {status: 200, ok: true, json: async () => ({ok: false, field: "both", error_code: "invalid_credentials", message: "Invalid email or username, or password."})},
    ]) {
        context.response = response;
        const before = requests;
        await handler({preventDefault() {}});
        assert.equal(requests, before + 1, "Never automatically retry sign-in");
        assert.equal(context.submitting, false);
        assert.equal(identifier.value, "Synthetic draft only");
        assert.equal(password.value, "Synthetic draft only");
        assert.equal(context.feedback.level, response.status === 429 ? "warning" : "error");
    }
    console.log("Login rate-limit, unavailable-state, generic-error, and draft-preservation checks passed.");
})().catch(error => {console.error(error); process.exitCode = 1;});
