(function (global) {
    "use strict";
    const normalize = value => value === "vat" || value === "non_vat" ? value : "";
    const label = value => ({ vat: "VAT", non_vat: "Non-VAT", "": "Not set" })[normalize(value)];
    const badge = value => {
        const key = normalize(value);
        const text = key ? label(key) : "Tax registration not set";
        return `<span class="client-tax-registration${key ? " is-" + key.replace("_", "-") : " is-not-set"}" aria-label="Tax registration: ${label(key)}" title="Tax registration: ${label(key)}">${text}</span>`;
    };
    global.SafeBooksClientRegistration = { normalize, label, badge };
})(window);
