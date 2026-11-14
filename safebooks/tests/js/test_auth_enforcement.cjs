const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const template = fs.readFileSync(path.resolve(__dirname, "../../../templates/authentication/login.html"), "utf8");
const start = template.indexOf("            const configureTwoFactorView =");
const end = template.indexOf("            const clearSkeletonState =", start);
assert(start >= 0 && end > start);
const code = template.slice(start, end) + "\nthis.showTwoFactor = showTwoFactorSection;";

const element = () => ({
    textContent: "", placeholder: "", value: "SyntheticOldCode", attributes: {},
    classList: { values: new Set(), add(value) { this.values.add(value); }, remove(value) { this.values.delete(value); } },
    setAttribute(key, value) { this.attributes[key] = value; },
    focus() { this.focused = true; },
});
const context = {
    currentTwoFactorRole: "bookkeeper",
    twoFactorTitle: element(), twoFactorSubtitle: element(), twoFactorLabel: element(), twoFactorGuidance: element(),
    adminTwoFactorInput: element(), loginFormSection: element(), forgotPasswordSection: element(), adminTwoFactorSection: element(),
    adminTwoFactorForm: { reset() { context.adminTwoFactorInput.value = ""; } },
    setAdminTwoFactorFeedback(message, level) { context.feedback = { message, level }; },
    window: { setTimeout(callback) { callback(); } },
};
vm.runInNewContext(code, context);
for (const role of ["bookkeeper", "admin", "bookkeeper"]) {
    context.adminTwoFactorInput.value = "SyntheticOldCode";
    context.adminTwoFactorSection.classList.add("d-none");
    context.showTwoFactor(role, "Synthetic verification guidance");
    assert.equal(context.currentTwoFactorRole, role);
    assert(context.loginFormSection.classList.values.has("d-none"));
    assert(context.forgotPasswordSection.classList.values.has("d-none"));
    assert(!context.adminTwoFactorSection.classList.values.has("d-none"));
    assert.equal(context.adminTwoFactorInput.value, "");
    assert.equal(context.adminTwoFactorInput.attributes.maxlength, role === "admin" ? "14" : "6");
    assert.equal(context.adminTwoFactorInput.focused, true);
    assert.equal(context.feedback.level, "warning");
}
console.log("Shared password/Google authenticator screen component checks passed.");
