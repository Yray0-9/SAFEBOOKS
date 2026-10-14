// Execute the actual shared helpers and settings handlers with synthetic browser state.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8").replace(/\r\n/g, "\n");
const extract = (source, start, end) => {
    const first = source.indexOf(start), last = source.indexOf(end, first);
    assert(first >= 0 && last > first, `Missing handler: ${start}`);
    return source.slice(first, last);
};
const classes = () => {
    const values = new Set();
    return { add: (...names) => names.forEach(n => values.add(n)), remove: (...names) => names.forEach(n => values.delete(n)),
        contains: n => values.has(n), toggle(n, value) { if (value) values.add(n); else values.delete(n); } };
};
const storage = () => {
    const values = new Map();
    return { blocked: false, getItem(key) { if (this.blocked) throw Error("Blocked"); return values.get(key) ?? null; },
        setItem(key, value) { if (this.blocked) throw Error("Blocked"); values.set(key, value); },
        removeItem(key) { if (this.blocked) throw Error("Blocked"); values.delete(key); } };
};
const browser = response => {
    const context = { URL, document: { cookie: "csrftoken=synthetic", body: { classList: classes() } }, requests: [] };
    context.window = { localStorage: storage(), sessionStorage: storage(), location: { href: "https://example.test/settings/", origin: "https://example.test" },
        matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }) };
    context.window.localStorage.setItem("user", "Synthetic label");
    context.window.sessionStorage.setItem("welcome", "1");
    context.fetch = async (url, options) => { context.requests.push({ url, options }); return typeof response === "function" ? response() : response; };
    vm.runInNewContext(read("static/js/app_shared.js"), context);
    context.shared = context.window.SafeBooksShared;
    return context;
};
const result = (status, payload) => ({ status, ok: status >= 200 && status < 300, json: async () => payload });
const options = { logoutUrl: "/api/logout/", loginUrl: "/login/", authUserKey: "user", loginWelcomeKey: "welcome" };
const settingsSource = read("static/js/settings_page.js");
const themes = extract(settingsSource, '    let pendingTheme = "light";', "    const bindThemeControls =");
const preferences = extract(settingsSource, "    const isLoginAlertsEnabled =", "    const isClientDetailsLockEnabled =");
const lockPreferences = extract(settingsSource, "    const isClientDetailsLockEnabled =", "    const setDeactivationSubmittingState =");
const settingsContext = (shared, response) => {
    const status = {}, button = {}, body = { classList: classes() };
    const context = { shared, body, appearanceSection: { querySelector: () => status }, applyThemeButton: button,
        themeButtons: [], themeSwatches: [], themeStatus: {}, messages: [], urls: { loginPage: "/login/" },
        securityLoginAlertsUrl: "/alerts/", clientRecordEmailNotificationsUrl: "/emails/",
        loginAlertsPanel: { dataset: { loginAlertsEnabled: "false" } }, loginAlertsToggle: {}, loginAlertsStatus: { classList: classes() }, loginAlertsFeedback: {},
        clientRecordEmailsPanel: { dataset: { clientRecordEmailNotificationsEnabled: "true" } }, clientRecordEmailsToggle: {},
        clientRecordEmailsStatus: { classList: classes() }, clientRecordEmailsFeedback: {},
        securityClientDetailsAccessPreferenceUrl: "/lock/", clientDetailsLockPanel: { dataset: { clientDetailsLockEnabled: "true" }, querySelectorAll: () => [] },
        clientDetailsLockToggle: { checked: false }, clientDetailsLockStatus: { classList: classes() }, clientDetailsLockFeedback: {},
        clientDetailsLockPasswordInput: { value: "Synthetic", classList: classes(), closest: () => null, focus() {} }, clientDetailsLockSaveButton: {},
        window: { location: { assign() { context.redirected = true; } } },
        setSaveButtonState: (target, enabled) => { target.disabled = !enabled; },
        resetSectionDirty: () => { button.disabled = true; }, markSectionDirty: () => { button.disabled = false; },
        setInlineStatus: (target, message) => { target.textContent = message; }, showToast: (message, variant) => { context.messages.push({ message, variant }); },
        clearInlineStatus: target => { target.textContent = ""; },
        postJson: async () => { context.posts = (context.posts || 0) + 1; return typeof response === "function" ? response() : response; },
        parseJsonSafe: async response => response.json() };
    vm.createContext(context);
    vm.runInContext(themes + preferences + lockPreferences + "\nthis.sync = syncThemeState; this.save = handleThemeSave; this.login = handleLoginAlertsToggle; this.emails = handleClientRecordEmailsToggle; this.lock = handleClientDetailsLockSave; this.choose = value => { pendingTheme = value; updateAppearanceDirtyState(); }; this.pending = () => pendingTheme;", context);
    context.status = status; context.button = button;
    return context;
};
const stripTemplate = source => source.replace(/\{%\s*(?:url|static)\b[\s\S]*?%\}/g, "/synthetic/").replace(/\{%[\s\S]*?%\}/g, "").replace(/\{\{[\s\S]*?\}\}/g, "0");

(async () => {
    for (const response of [() => { throw Error("Network failed"); }, result(403, { ok: false }), result(503, { ok: false }), result(200, { ok: false }),
        { ok: true, status: 200, json: async () => { throw Error("Bad JSON"); } }]) {
        const context = browser(response);
        await assert.rejects(context.shared.logoutCurrentUser(options), /confirm/i);
        assert.equal(context.requests.length, 1); // No automatic retry of an unknown outcome.
        assert.equal(context.window.localStorage.getItem("user"), "Synthetic label");
        assert.equal(context.window.sessionStorage.getItem("welcome"), "1");
    }
    const unavailable = browser(result(200, { ok: true }));
    await assert.rejects(unavailable.shared.logoutCurrentUser({}), /unavailable/);
    assert.equal(unavailable.requests.length, 0);
    for (const response of [result(200, { ok: true, redirect_url: "/login/" }), result(401, { ok: false })]) {
        const context = browser(response);
        assert.match(await context.shared.logoutCurrentUser(options), /\/login\/$/);
        assert.equal(context.window.localStorage.getItem("user"), null);
        assert.equal(context.window.sessionStorage.getItem("welcome"), null);
        assert.equal(context.requests[0].options.headers["X-CSRFToken"], "synthetic");
    }
    const external = browser(result(200, { ok: true, redirect_url: "https://other.test/" }));
    assert.equal(await external.shared.logoutCurrentUser(options), "/login/");
    let finish;
    const concurrent = browser(() => new Promise(resolve => { finish = resolve; }));
    const one = concurrent.shared.logoutCurrentUser(options), two = concurrent.shared.logoutCurrentUser(options);
    assert.equal(one, two);
    finish(result(200, { ok: true }));
    await one;
    assert.equal(concurrent.requests.length, 1);
    const blocked = browser(result(200, { ok: true }));
    blocked.window.localStorage.blocked = true;
    await blocked.shared.logoutCurrentUser(options);
    assert.equal(blocked.window.sessionStorage.getItem("welcome"), null);

    const themeBrowser = browser();
    const theme = settingsContext(themeBrowser.shared);
    theme.sync(); theme.choose("dark"); theme.save();
    assert.equal(theme.status.textContent, "Saved in this browser");
    assert.equal(theme.button.disabled, true);
    assert.equal(themeBrowser.shared.getThemePreference().theme, "dark");
    themeBrowser.window.localStorage.blocked = true;
    theme.choose("light"); theme.save();
    assert.equal(theme.status.textContent, "Not saved");
    assert.equal(theme.button.disabled, false);
    assert.equal(theme.pending(), "light"); // Preserve selection after a failed save.
    assert(themeBrowser.document.body.classList.contains("theme-light"));
    theme.sync();
    assert.equal(theme.status.textContent, "Browser storage unavailable");
    assert.equal(themeBrowser.shared.setThemePreference("dark", false).persisted, false);
    const following = browser();
    following.shared.setThemePreference("light", true);
    settingsContext(following.shared).sync();
    assert.equal(following.shared.getThemePreference().followSystem, true); // Reading settings is not a settings write.

    for (const response of [() => { throw Error("Lost response"); }, result(503, { ok: false }), result(200, { ok: true })]) {
        const state = settingsContext(null, response);
        await state.login(true); await state.emails(false); await state.lock();
        assert.equal(state.loginAlertsToggle.checked, false);
        assert.equal(state.clientRecordEmailsToggle.checked, true);
        assert.match(state.loginAlertsFeedback.textContent, /Not confirmed/);
        assert.match(state.clientRecordEmailsFeedback.textContent, /Not confirmed/);
        assert.equal(state.loginAlertsToggle.disabled, false);
        assert.equal(state.clientRecordEmailsToggle.disabled, false);
        assert.equal(state.clientDetailsLockToggle.checked, true);
        assert.match(state.clientDetailsLockFeedback.textContent, /not confirmed/);
        assert.equal(state.clientDetailsLockSaveButton.disabled, false);
        assert.equal(state.posts, 3);
        assert(state.messages.every(message => message.variant !== "success"));
    }
    const saved = settingsContext(null, result(200, { ok: true, login_alerts_enabled: true, client_record_email_notifications_enabled: false, client_details_password_required: false }));
    await saved.login(true); await saved.emails(false); await saved.lock();
    assert.equal(saved.loginAlertsToggle.checked, true);
    assert.equal(saved.clientRecordEmailsToggle.checked, false);
    assert.equal(saved.loginAlertsFeedback.textContent, "Updated");
    assert.equal(saved.clientDetailsLockToggle.checked, false);
    assert.equal(saved.clientDetailsLockPasswordInput.value, "");
    const rejected = settingsContext(null, result(400, { ok: false, message: "Current password is incorrect." }));
    await rejected.lock();
    assert.equal(rejected.clientDetailsLockFeedback.textContent, "Current password is incorrect.");

    for (const [file, name, end] of [
        ["templates/base/bookkeeper_base.html", "handleLogout", "            logoutActions.forEach"],
        ["templates/authentication/pending_approval.html", "handleLogout", "            logoutActions.forEach"],
        ["templates/admin_panel/partials/admin_scripts.html", "handleAdminLogout", "        adminLogoutActions.forEach"],
    ]) {
        const handler = stripTemplate(extract(read(file), `const ${name} =`, end));
        for (const confirmed of [false, true]) {
            const action = { dataset: {}, tagName: "BUTTON", setAttribute() {}, removeAttribute() {} };
            const context = { document: { getElementById: () => null }, uiToastContainer: null,
                shared: { logoutCurrentUser: async () => { if (!confirmed) throw Error("Unconfirmed"); return "/login/"; }, showToast() {} },
                window: { location: { assign() { context.redirected = true; } }, alert() {} } };
            vm.runInNewContext(handler + `\nthis.handle = ${name};`, context);
            await context.handle({ preventDefault() {}, currentTarget: action });
            assert.equal(Boolean(context.redirected), confirmed, file);
            assert.equal(action.disabled, false);
            assert.equal(action.dataset.logoutPending, "0");
        }
    }
    const badge = {}, field = {};
    const detail = { currentClientProfile: {}, document: { querySelector: selector => selector.includes("badge") ? badge : field },
        formatRemarksLabel: value => value.charAt(0).toUpperCase() + value.slice(1) };
    vm.runInNewContext(extract(read("templates/base/client_details.html"), "const updateClosedUiState =", '                const banner = document.getElementById("clientClosedNoticeBanner");') + "}; this.update = updateClosedUiState;", detail);
    for (const remark of ["new", "active", "separated", "closed"]) {
        detail.update({ remarks: remark });
        assert.equal(badge.textContent.toLowerCase(), remark);
        assert.equal(field.textContent.toLowerCase(), remark);
        assert.equal(detail.currentClientProfile.remarks, remark);
    }
    let scripts = 0;
    for (const file of ["bookkeeper_base", "settings", "clients", "client_details", "dashboard", "financial_records", "financial_records_client", "analytics"]) {
        for (const match of read(`templates/base/${file}.html`).matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
            if (!match[2].trim() || match[1].includes("application/json")) continue;
            new vm.Script(stripTemplate(match[2]), { filename: file }); scripts++;
        }
    }
    for (const file of ["templates/admin_panel/partials/admin_scripts.html", "templates/authentication/pending_approval.html", "templates/authentication/email_verification.html"]) {
        for (const match of read(file).matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
            if (!match[1].trim()) continue;
            new vm.Script(stripTemplate(match[1]), { filename: file }); scripts++;
        }
    }
    for (const name of ["app_shared", "settings_page", "profile_page", "reports_page"]) new vm.Script(read(`static/js/${name}.js`), { filename: name });
    console.log(`Settings/logout regression checks passed; ${scripts} template script blocks and 4 static scripts parsed.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
