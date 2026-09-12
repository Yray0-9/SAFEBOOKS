(function () {
    const config = window.SafeBooksSettingsConfig || {};
    const urls = config.urls || {};
    const shared = window.SafeBooksShared || null;

    const AUTH_USER_KEY = String(config.authUserKey || "safebooks.authUser");
    const LOGIN_WELCOME_KEY = String(config.loginWelcomeKey || "safebooks.loginWelcome");
    const SIDEBAR_STATE_KEY = String(config.sidebarStateKey || "safebooks.sidebarCollapsed");
    const DESKTOP_QUERY = String(config.desktopQuery || "(min-width: 992px)");

    const body = document.body;
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarCollapseToggle = document.getElementById("sidebarCollapseToggle");
    const sidebarCollapseIcon = document.getElementById("sidebarCollapseIcon");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");

    const dashboardUserAvatar = document.getElementById("dashboardUserAvatar");
    const dashboardUserName = document.getElementById("dashboardUserName");
    const dashboardProfileAction = document.getElementById("dashboardProfileAction");
    const dashboardLogoutAction = document.getElementById("dashboardLogoutAction");

    const uiToastContainer = document.getElementById("uiToastContainer");

    const themeButtons = Array.from(document.querySelectorAll("[data-theme-value]"));
    const themeSwatches = Array.from(document.querySelectorAll("[data-theme-swatch]"));
    const themeStatus = document.getElementById("settingsThemeStatus");
    const applyThemeButton = document.getElementById("settingsApplyThemeButton");
    const appearanceSection = document.getElementById("settingsAppearance");

    const settingsSections = Array.from(document.querySelectorAll("[data-settings-section]"));
    const settingsNavLinks = Array.from(document.querySelectorAll(".settings-nav-link"));

    const securityChangePasswordUrl = String(urls.securityChangePasswordApi || "");
    const securityLoginAlertsUrl = String(urls.securityLoginAlertsApi || "");
    const clientRecordEmailNotificationsUrl = String(urls.clientRecordEmailNotificationsApi || "");
    const securityClientDetailsAccessPreferenceUrl = String(urls.securityClientDetailsAccessPreferenceApi || "");
    const deactivationRequestUrl = String(urls.deactivationRequestApi || "");
    const twoFactorSetupUrl = String(urls.twoFactorSetupApi || "");
    const twoFactorConfirmUrl = String(urls.twoFactorConfirmApi || "");
    const twoFactorDisableUrl = String(urls.twoFactorDisableApi || "");

    const changePasswordForm = document.getElementById("settingsChangePasswordForm");
    const changePasswordStatus = document.getElementById("settingsChangePasswordStatus");
    const changePasswordButton = document.getElementById("settingsChangePasswordButton");
    const changePasswordModalElement = document.getElementById("settingsChangePasswordModal");
    const currentPasswordInput = document.getElementById("settingsCurrentPassword");
    const newPasswordInput = document.getElementById("settingsNewPassword");
    const confirmPasswordInput = document.getElementById("settingsConfirmPassword");
    const passwordRulesContainer = document.getElementById("settingsPasswordRules");
    const loginAlertsPanel = document.getElementById("settingsLoginAlertsPanel");
    const loginAlertsToggle = document.getElementById("settingsLoginAlertsToggle");
    const loginAlertsStatus = document.getElementById("settingsLoginAlertsStatus");
    const loginAlertsFeedback = document.getElementById("settingsLoginAlertsFeedback");
    const clientRecordEmailsPanel = document.getElementById("settingsNotifications");
    const clientRecordEmailsToggle = document.getElementById("settingsClientRecordEmailsToggle");
    const clientRecordEmailsStatus = document.getElementById("settingsClientRecordEmailsStatus");
    const clientRecordEmailsFeedback = document.getElementById("settingsClientRecordEmailsFeedback");
    const clientDetailsLockPanel = document.getElementById("settingsClientDetailsLockPanel");
    const clientDetailsLockToggle = document.getElementById("settingsClientDetailsLockToggle");
    const clientDetailsLockStatus = document.getElementById("settingsClientDetailsLockStatus");
    const clientDetailsLockFeedback = document.getElementById("settingsClientDetailsLockFeedback");
    const clientDetailsLockPasswordInput = document.getElementById("settingsClientDetailsLockPassword");
    const clientDetailsLockSaveButton = document.getElementById("settingsClientDetailsLockSaveButton");
    const deactivationRequestForm = document.getElementById("settingsDeactivationRequestForm");
    const deactivationRequestModalElement = document.getElementById("settingsDeactivationRequestModal");
    const deactivationRequestStatus = document.getElementById("settingsDeactivationRequestStatus");
    const deactivationRequestButton = document.getElementById("settingsDeactivationRequestButton");
    const deactivationReasonInput = document.getElementById("settingsDeactivationReason");
    const deactivationPasswordInput = document.getElementById("settingsDeactivationPassword");
    const openDeactivationRequestButton = document.getElementById("settingsOpenDeactivationRequestModal");
    const deactivationRequestHint = document.getElementById("settingsDeactivationRequestHint");
    const twoFactorPanel = document.getElementById("settingsTwoFactorPanel");
    const twoFactorStatus = document.getElementById("settingsTwoFactorStatus");
    const twoFactorOpenBtn = document.getElementById("settingsOpenTwoFactorModal");
    const twoFactorOpenDisableBtn = document.getElementById("settingsOpenDisableTwoFactorModal");
    const twoFactorModalElement = document.getElementById("settingsTwoFactorModal");
    const twoFactorQrContainer = document.getElementById("settingsTwoFactorQrContainer");
    const twoFactorQrImage = document.getElementById("settingsTwoFactorQrImage");
    const twoFactorQrSpinner = document.getElementById("settingsTwoFactorQrSpinner");
    const twoFactorKeyInput = document.getElementById("settingsTwoFactorKeyPreview");
    const twoFactorCopyBtn = document.getElementById("settingsTwoFactorCopyBtn");
    const twoFactorCodeInput = document.getElementById("settingsTwoFactorCodePreview");
    const twoFactorSubmitBtn = document.getElementById("settingsTwoFactorSubmitBtn");
    const twoFactorModalFeedback = document.getElementById("settingsTwoFactorModalFeedback");

    const twoFactorDisableModalElement = document.getElementById("settingsDisableTwoFactorModal");
    const twoFactorDisableForm = document.getElementById("settingsDisableTwoFactorForm");
    const twoFactorDisablePasswordInput = document.getElementById("settingsDisableTwoFactorPassword");
    const twoFactorDisableSubmitBtn = document.getElementById("settingsDisableTwoFactorSubmitBtn");
    const twoFactorDisableFeedback = document.getElementById("settingsDisableTwoFactorFeedback");

    if (!body || !uiToastContainer || !settingsSections.length) {
        return;
    }

    window.setTimeout(() => {
        if (body.classList.contains("skeleton-active") && !body.classList.contains("skeleton-loaded")) {
            body.classList.remove("skeleton-active");
            body.classList.add("skeleton-loaded");
        }
    }, 1800);

    const sidebarState = shared && typeof shared.initializeSidebarBehavior === "function"
        ? shared.initializeSidebarBehavior({
            bodyElement: body,
            sidebarToggle,
            sidebarCollapseToggle,
            sidebarCollapseIcon,
            sidebarBackdrop,
            storageKey: SIDEBAR_STATE_KEY,
            desktopQuery: DESKTOP_QUERY,
        })
        : {
            closeMobileSidebar: () => {},
            restoreDesktopState: () => {},
        };

    const showToast = (message, variantClass = "") => {
        if (!shared || typeof shared.showToast !== "function") {
            return;
        }

        shared.showToast(uiToastContainer, message, variantClass, {
            delay: 2800,
        });
    };

    const parseJsonSafe = (response) => {
        if (shared && typeof shared.parseJsonSafe === "function") {
            return shared.parseJsonSafe(response);
        }

        return response
            .json()
            .catch(() => null);
    };

    const getCookieValue = (cookieName) => {
        if (shared && typeof shared.getCookieValue === "function") {
            return shared.getCookieValue(cookieName);
        }

        return "";
    };

    const hydrateHeaderUser = () => {
        if (!shared || typeof shared.hydrateHeaderUser !== "function") {
            return;
        }

        shared.hydrateHeaderUser({
            avatarElement: dashboardUserAvatar,
            nameElement: dashboardUserName,
            authUserKey: AUTH_USER_KEY,
            defaultName: String(config.defaultName || "Bookkeeper User"),
            defaultInitials: String(config.defaultInitials || "SB"),
        });
    };

    const logoutCurrentUser = async () => {
        if (!shared || typeof shared.logoutCurrentUser !== "function") {
            return String(urls.loginPage || "/login/");
        }

        return shared.logoutCurrentUser({
            logoutUrl: String(urls.logoutApi || ""),
            loginUrl: String(urls.loginPage || "/login/"),
            authUserKey: AUTH_USER_KEY,
            loginWelcomeKey: LOGIN_WELCOME_KEY,
        });
    };

    const setSaveButtonState = (saveButton, isEnabled) => {
        if (!saveButton) {
            return;
        }

        saveButton.disabled = !isEnabled;
        if (saveButton.hasAttribute("aria-disabled")) {
            saveButton.setAttribute("aria-disabled", String(!isEnabled));
        }
    };

    const markSectionDirty = (section) => {
        if (!section) {
            return;
        }

        const saveButton = section.querySelector("[data-settings-save]");
        const status = section.querySelector("[data-settings-status]");
        if (saveButton) {
            setSaveButtonState(saveButton, true);
        }
        if (status) {
            status.textContent = "Unsaved changes";
        }
    };

    const resetSectionDirty = (section) => {
        if (!section) {
            return;
        }

        const saveButton = section.querySelector("[data-settings-save]");
        const status = section.querySelector("[data-settings-status]");
        if (saveButton) {
            setSaveButtonState(saveButton, false);
        }
        if (status) {
            status.textContent = "Saved";
        }
    };

    const setInlineStatus = (element, message, variant) => {
        if (!element) {
            return;
        }

        element.textContent = message;
        element.classList.remove("is-success", "is-warning", "is-danger");
        if (variant) {
            element.classList.add(`is-${variant}`);
        }
    };

    const clearInlineStatus = (element) => {
        if (!element) {
            return;
        }

        element.textContent = "";
        element.classList.remove("is-success", "is-warning", "is-danger");
    };

    const setButtonLoading = (button, isLoading, loadingLabel) => {
        if (!button) {
            return;
        }

        if (!button.dataset.defaultLabel) {
            button.dataset.defaultLabel = button.textContent || "";
        }

        if (isLoading) {
            button.dataset.wasDisabled = button.disabled ? "true" : "false";
            if (button.hasAttribute("aria-disabled")) {
                button.dataset.wasAriaDisabled = button.getAttribute("aria-disabled") || "false";
                button.setAttribute("aria-disabled", "true");
            }
            button.disabled = true;
        } else {
            const wasDisabled = button.dataset.wasDisabled === "true";
            if (button.hasAttribute("aria-disabled") && button.dataset.wasAriaDisabled) {
                button.setAttribute("aria-disabled", button.dataset.wasAriaDisabled);
            }
            button.disabled = wasDisabled;
            delete button.dataset.wasDisabled;
            delete button.dataset.wasAriaDisabled;
        }

        button.textContent = isLoading
            ? String(loadingLabel || "Working...")
            : button.dataset.defaultLabel;
    };

    const postJson = async (url, payload) => {
        const csrfToken = getCookieValue("csrftoken");
        const headers = {
            Accept: "application/json",
            "Content-Type": "application/json",
        };
        if (csrfToken) {
            headers["X-CSRFToken"] = csrfToken;
        }

        return fetch(url, {
            method: "POST",
            headers,
            credentials: "same-origin",
            body: JSON.stringify(payload || {}),
        });
    };

    const getModalInstance = (element) => {
        if (!element || !window.bootstrap || !window.bootstrap.Modal) {
            return null;
        }

        if (typeof window.bootstrap.Modal.getOrCreateInstance === "function") {
            return window.bootstrap.Modal.getOrCreateInstance(element);
        }

        return new window.bootstrap.Modal(element);
    };

    let changePasswordModal = null;
    let deactivationRequestModal = null;
    let twoFactorModal = null;
    let twoFactorDisableModal = null;

    const getPasswordRequirementState = () => {
        const currentValue = currentPasswordInput ? currentPasswordInput.value : "";
        const newValue = newPasswordInput ? newPasswordInput.value : "";
        const confirmValue = confirmPasswordInput ? confirmPasswordInput.value : "";

        const state = {
            length: newValue.length >= 8,
            uppercase: /[A-Z]/.test(newValue),
            lowercase: /[a-z]/.test(newValue),
            number: /\d/.test(newValue),
            symbol: /[^A-Za-z0-9]/.test(newValue),
            match: Boolean(newValue) && newValue === confirmValue,
            hasCurrent: Boolean(currentValue),
            hasConfirm: Boolean(confirmValue),
        };

        state.isDifferent = !currentValue || !newValue || currentValue !== newValue;
        state.isValid = state.length && state.uppercase && state.lowercase
            && state.number && state.symbol && state.match;

        return state;
    };

    const updatePasswordRequirementsUi = () => {
        const state = getPasswordRequirementState();

        if (passwordRulesContainer) {
            const ruleElements = passwordRulesContainer.querySelectorAll("[data-rule]");
            ruleElements.forEach((ruleElement) => {
                const ruleName = ruleElement.getAttribute("data-rule");
                const isValid = Boolean(ruleName && state[ruleName]);
                ruleElement.classList.toggle("is-valid", isValid);
            });
        }

        return state;
    };

    const bindPasswordToggles = () => {
        document.querySelectorAll("[data-password-toggle-target]").forEach((toggleButton) => {
            toggleButton.addEventListener("click", () => {
                const targetId = toggleButton.getAttribute("data-password-toggle-target");
                const inputElement = targetId ? document.getElementById(targetId) : null;
                if (!(inputElement instanceof HTMLInputElement)) {
                    return;
                }

                const shouldShow = inputElement.type === "password";
                inputElement.type = shouldShow ? "text" : "password";

                const iconElement = toggleButton.querySelector("i");
                if (iconElement) {
                    iconElement.classList.toggle("bi-eye", !shouldShow);
                    iconElement.classList.toggle("bi-eye-slash", shouldShow);
                }

                toggleButton.setAttribute("aria-label", shouldShow ? "Hide password" : "Show password");
            });
        });
    };

    const bindSectionInputs = () => {
        settingsSections.forEach((section) => {
            const inputs = Array.from(section.querySelectorAll("input, select, textarea"));
            inputs.forEach((input) => {
                input.addEventListener("input", () => markSectionDirty(section));
                input.addEventListener("change", () => markSectionDirty(section));
            });

            const saveButton = section.querySelector("[data-settings-save]");
            if (!saveButton) {
                return;
            }

            if (saveButton.hasAttribute("data-theme-save")
                || saveButton.hasAttribute("data-settings-defaults-save")) {
                return;
            }

            saveButton.addEventListener("click", () => {
                if (section instanceof HTMLFormElement && !section.checkValidity()) {
                    section.reportValidity();
                    return;
                }

                resetSectionDirty(section);
                showToast("Settings saved.", "success");
            });
        });
    };

    let pendingTheme = "light";
    let storedTheme = "light";

    const getStoredThemeState = () => {
        if (shared && typeof shared.getThemePreference === "function") {
            const preference = shared.getThemePreference();
            return {
                theme: preference.theme || "light",
                followSystem: Boolean(preference.followSystem),
            };
        }

        return {
            theme: "light",
            followSystem: false,
        };
    };

    const resolveThemeFromBody = () => {
        if (!body) {
            return "light";
        }

        return body.classList.contains("theme-dark") ? "dark" : "light";
    };

    const applyThemeStateToUI = (themeValue) => {
        themeButtons.forEach((button) => {
            const value = String(button.dataset.themeValue || "light");
            const isActive = value === themeValue;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", String(isActive));
        });

        themeSwatches.forEach((swatch) => {
            const value = String(swatch.dataset.themeSwatch || "").trim();
            swatch.classList.toggle("is-active", value === themeValue);
        });

        if (themeStatus) {
            themeStatus.textContent = `Theme set to ${themeValue === "dark" ? "Dark" : "Light"}.`;
        }
    };

    const updateAppearanceDirtyState = () => {
        if (!appearanceSection) {
            return;
        }

        if (pendingTheme === storedTheme) {
            resetSectionDirty(appearanceSection);
        } else {
            markSectionDirty(appearanceSection);
        }
    };

    const syncThemeState = () => {
        const storedState = getStoredThemeState();
        storedTheme = storedState.theme || "light";

        if (storedState.followSystem) {
            const resolvedTheme = resolveThemeFromBody();
            storedTheme = resolvedTheme;
            if (shared && typeof shared.setThemePreference === "function") {
                shared.setThemePreference(resolvedTheme, false);
            }
        }

        pendingTheme = storedTheme;
        applyThemeStateToUI(pendingTheme);
        updateAppearanceDirtyState();
    };

    const handleThemeSave = () => {
        if (shared && typeof shared.setThemePreference === "function") {
            shared.setThemePreference(pendingTheme, false);
        }
        showToast("Theme updated.", "success");
        syncThemeState();
    };

    const bindThemeControls = () => {
        const setPendingTheme = (nextValue) => {
            const value = String(nextValue || "light");
            pendingTheme = value === "dark" ? "dark" : "light";
            applyThemeStateToUI(pendingTheme);
            updateAppearanceDirtyState();
        };

        themeButtons.forEach((button) => {
            button.addEventListener("click", () => {
                setPendingTheme(button.dataset.themeValue || "light");
            });
        });

        themeSwatches.forEach((swatch) => {
            swatch.addEventListener("click", () => {
                setPendingTheme(swatch.dataset.themeSwatch || "light");
            });
        });

        if (applyThemeButton) {
            applyThemeButton.addEventListener("click", () => {
                handleThemeSave();
            });
        }
    };

    const isLoginAlertsEnabled = () => {
        if (!loginAlertsPanel) {
            return false;
        }

        return String(loginAlertsPanel.dataset.loginAlertsEnabled || "false") === "true";
    };

    const updateLoginAlertsUiState = (isEnabled) => {
        if (loginAlertsPanel) {
            loginAlertsPanel.dataset.loginAlertsEnabled = isEnabled ? "true" : "false";
        }

        if (loginAlertsStatus) {
            loginAlertsStatus.textContent = isEnabled ? "On" : "Off";
            loginAlertsStatus.classList.toggle("is-enabled", isEnabled);
        }

        if (loginAlertsToggle) {
            loginAlertsToggle.checked = isEnabled;
        }
    };

    const setLoginAlertsLoading = (isLoading) => {
        if (loginAlertsToggle) {
            loginAlertsToggle.disabled = isLoading;
        }
    };

    const handleLoginAlertsToggle = async (nextValue) => {
        if (!securityLoginAlertsUrl) {
            showToast("Login alerts are unavailable.", "warning");
            updateLoginAlertsUiState(isLoginAlertsEnabled());
            return;
        }

        const previousValue = isLoginAlertsEnabled();
        setLoginAlertsLoading(true);
        setInlineStatus(loginAlertsFeedback, "Saving...", "warning");

        try {
            const response = await postJson(securityLoginAlertsUrl, {
                enabled: Boolean(nextValue),
            });

            if (response.status === 401) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }

            const result = await parseJsonSafe(response);
            if (!response.ok || !result || !result.ok) {
                const message = result && result.message
                    ? String(result.message)
                    : "Unable to update login alerts.";
                throw new Error(message);
            }

            updateLoginAlertsUiState(Boolean(result.login_alerts_enabled));
            setInlineStatus(loginAlertsFeedback, "Updated", "success");
            showToast("Login alerts updated.", "success");
        } catch (error) {
            updateLoginAlertsUiState(previousValue);
            setInlineStatus(loginAlertsFeedback, "Update failed", "danger");
            showToast(error && error.message ? String(error.message) : "Unable to update login alerts.", "danger");
        } finally {
            setLoginAlertsLoading(false);
        }
    };

    const isClientRecordEmailsEnabled = () => {
        if (!clientRecordEmailsPanel) {
            return true;
        }

        return String(clientRecordEmailsPanel.dataset.clientRecordEmailNotificationsEnabled || "true") === "true";
    };

    const updateClientRecordEmailsUiState = (isEnabled) => {
        if (clientRecordEmailsPanel) {
            clientRecordEmailsPanel.dataset.clientRecordEmailNotificationsEnabled = isEnabled ? "true" : "false";
        }

        if (clientRecordEmailsStatus) {
            clientRecordEmailsStatus.textContent = isEnabled ? "On" : "Off";
            clientRecordEmailsStatus.classList.toggle("is-enabled", isEnabled);
        }

        if (clientRecordEmailsToggle) {
            clientRecordEmailsToggle.checked = isEnabled;
        }
    };

    const setClientRecordEmailsLoading = (isLoading) => {
        if (clientRecordEmailsToggle) {
            clientRecordEmailsToggle.disabled = isLoading;
        }
    };

    const handleClientRecordEmailsToggle = async (nextValue) => {
        if (!clientRecordEmailNotificationsUrl) {
            showToast("Client email notification settings are unavailable.", "warning");
            updateClientRecordEmailsUiState(isClientRecordEmailsEnabled());
            return;
        }

        const previousValue = isClientRecordEmailsEnabled();
        setClientRecordEmailsLoading(true);
        setInlineStatus(clientRecordEmailsFeedback, "Saving...", "warning");

        try {
            const response = await postJson(clientRecordEmailNotificationsUrl, {
                enabled: Boolean(nextValue),
            });

            if (response.status === 401) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }

            const result = await parseJsonSafe(response);
            if (!response.ok || !result || !result.ok) {
                const message = result && result.message
                    ? String(result.message)
                    : "Unable to update client email notifications.";
                throw new Error(message);
            }

            updateClientRecordEmailsUiState(Boolean(result.client_record_email_notifications_enabled));
            setInlineStatus(clientRecordEmailsFeedback, "Updated", "success");
            showToast("Client email notification setting updated.", "success");
        } catch (error) {
            updateClientRecordEmailsUiState(previousValue);
            setInlineStatus(clientRecordEmailsFeedback, "Update failed", "danger");
            showToast(error && error.message ? String(error.message) : "Unable to update client email notifications.", "danger");
        } finally {
            setClientRecordEmailsLoading(false);
        }
    };

    const isClientDetailsLockEnabled = () => {
        if (!clientDetailsLockPanel) {
            return false;
        }

        return String(clientDetailsLockPanel.dataset.clientDetailsLockEnabled || "false") === "true";
    };

    const updateClientDetailsLockUiState = (isEnabled) => {
        if (clientDetailsLockPanel) {
            clientDetailsLockPanel.dataset.clientDetailsLockEnabled = isEnabled ? "true" : "false";
        }

        if (clientDetailsLockStatus) {
            clientDetailsLockStatus.textContent = isEnabled ? "On" : "Off";
            clientDetailsLockStatus.classList.toggle("is-enabled", isEnabled);
        }

        if (clientDetailsLockToggle) {
            clientDetailsLockToggle.checked = isEnabled;
        }
    };

    const setClientDetailsLockLoading = (isLoading) => {
        if (clientDetailsLockToggle) {
            clientDetailsLockToggle.disabled = isLoading;
        }
        if (clientDetailsLockPasswordInput) {
            clientDetailsLockPasswordInput.disabled = isLoading;
            const parentField = clientDetailsLockPasswordInput.closest(".auth-password-field");
            if (parentField) {
                parentField.classList.toggle("is-disabled", isLoading);
            }
        }
        if (clientDetailsLockSaveButton) {
            clientDetailsLockSaveButton.disabled = isLoading;
        }
        if (clientDetailsLockPanel) {
            clientDetailsLockPanel.querySelectorAll(".auth-password-toggle").forEach((toggleBtn) => {
                toggleBtn.disabled = isLoading;
            });
        }
    };

    const handleClientDetailsLockSave = async () => {
        if (!securityClientDetailsAccessPreferenceUrl) {
            showToast("Client details lock settings are unavailable.", "warning");
            updateClientDetailsLockUiState(isClientDetailsLockEnabled());
            return;
        }

        const currentPassword = clientDetailsLockPasswordInput ? clientDetailsLockPasswordInput.value : "";
        if (!currentPassword) {
            setInlineStatus(clientDetailsLockFeedback, "Current password is required.", "danger");
            showToast("Enter your current password to save this setting.", "warning");
            if (clientDetailsLockPasswordInput) {
                clientDetailsLockPasswordInput.focus();
            }
            return;
        }

        const previousValue = isClientDetailsLockEnabled();
        const nextValue = clientDetailsLockToggle ? clientDetailsLockToggle.checked : previousValue;
        setClientDetailsLockLoading(true);
        setInlineStatus(clientDetailsLockFeedback, "Saving...", "warning");

        try {
            const response = await postJson(securityClientDetailsAccessPreferenceUrl, {
                enabled: Boolean(nextValue),
                current_password: currentPassword,
            });

            if (response.status === 401) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }

            const result = await parseJsonSafe(response);
            if (!response.ok || !result || !result.ok) {
                const message = result && result.message
                    ? String(result.message)
                    : "Unable to update client details lock.";
                throw new Error(message);
            }

            updateClientDetailsLockUiState(Boolean(result.client_details_password_required));
            if (clientDetailsLockPasswordInput) {
                clientDetailsLockPasswordInput.value = "";
            }
            setInlineStatus(clientDetailsLockFeedback, "Updated", "success");
            showToast("Client details lock updated.", "success");
        } catch (error) {
            updateClientDetailsLockUiState(previousValue);
            setInlineStatus(clientDetailsLockFeedback, "Update failed", "danger");
            showToast(error && error.message ? String(error.message) : "Unable to update client details lock.", "danger");
        } finally {
            setClientDetailsLockLoading(false);
        }
    };

    const setDeactivationSubmittingState = (isSubmitting) => {
        [deactivationReasonInput, deactivationPasswordInput].forEach((input) => {
            if (!input) {
                return;
            }
            input.disabled = isSubmitting;
            const parentField = input.closest(".auth-password-field");
            if (parentField) {
                parentField.classList.toggle("is-disabled", isSubmitting);
            }
        });

        if (deactivationRequestModalElement) {
            deactivationRequestModalElement.querySelectorAll(".auth-password-toggle").forEach((toggleBtn) => {
                toggleBtn.disabled = isSubmitting;
            });

            const cancelBtn = deactivationRequestModalElement.querySelector('[data-bs-dismiss="modal"]');
            if (cancelBtn) {
                cancelBtn.disabled = isSubmitting;
            }

            const closeBtn = deactivationRequestModalElement.querySelector(".btn-close");
            if (closeBtn) {
                closeBtn.disabled = isSubmitting;
                closeBtn.style.pointerEvents = isSubmitting ? "none" : "";
            }
        }
    };

    const resetDeactivationRequestInputs = () => {
        setDeactivationSubmittingState(false);
        if (deactivationReasonInput) {
            deactivationReasonInput.value = "";
        }
        if (deactivationPasswordInput) {
            deactivationPasswordInput.value = "";
        }
        clearInlineStatus(deactivationRequestStatus);
    };

    const markDeactivationRequestPending = () => {
        if (openDeactivationRequestButton) {
            openDeactivationRequestButton.textContent = "Request Pending";
            openDeactivationRequestButton.disabled = true;
            openDeactivationRequestButton.setAttribute("aria-disabled", "true");
            openDeactivationRequestButton.removeAttribute("data-bs-toggle");
            openDeactivationRequestButton.removeAttribute("data-bs-target");
        }
        if (deactivationRequestHint) {
            deactivationRequestHint.textContent = "Request pending admin review.";
        }
    };

    const handleDeactivationRequestSubmit = async () => {
        if (!deactivationRequestUrl || !deactivationRequestForm) {
            showToast("Deactivation requests are unavailable.", "warning");
            return;
        }

        const currentPassword = deactivationPasswordInput ? deactivationPasswordInput.value : "";
        if (!currentPassword) {
            setInlineStatus(deactivationRequestStatus, "Current password is required.", "danger");
            showToast("Enter your current password to submit this request.", "warning");
            if (deactivationPasswordInput) {
                deactivationPasswordInput.focus();
            }
            return;
        }

        setButtonLoading(deactivationRequestButton, true, "Submitting...");
        setInlineStatus(deactivationRequestStatus, "Submitting request...", "warning");
        setDeactivationSubmittingState(true);
        let submitted = false;

        try {
            const response = await postJson(deactivationRequestUrl, {
                current_password: currentPassword,
                reason: deactivationReasonInput ? deactivationReasonInput.value : "",
            });

            if (response.status === 401) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }

            const result = await parseJsonSafe(response);
            if (!response.ok || !result || !result.ok) {
                const message = result && result.message
                    ? String(result.message)
                    : "Unable to submit deactivation request.";
                throw new Error(message);
            }

            setInlineStatus(deactivationRequestStatus, "Request submitted", "success");
            submitted = true;
            markDeactivationRequestPending();
            showToast(result.message || "Deactivation request submitted.", "success");
            window.setTimeout(() => {
                if (deactivationRequestModal) {
                    deactivationRequestModal.hide();
                }
            }, 450);
        } catch (error) {
            setInlineStatus(deactivationRequestStatus, "Request failed", "danger");
            showToast(error && error.message ? String(error.message) : "Unable to submit deactivation request.", "danger");
        } finally {
            setButtonLoading(deactivationRequestButton, false);
            if (!submitted) {
                setDeactivationSubmittingState(false);
            }
        }
    };

    const setChangePasswordSubmittingState = (isSubmitting) => {
        [currentPasswordInput, newPasswordInput, confirmPasswordInput].forEach((input) => {
            if (!input) {
                return;
            }
            input.disabled = isSubmitting;
            const parentField = input.closest(".auth-password-field");
            if (parentField) {
                parentField.classList.toggle("is-disabled", isSubmitting);
            }
        });

        if (changePasswordModalElement) {
            changePasswordModalElement.querySelectorAll(".auth-password-toggle").forEach((toggleBtn) => {
                toggleBtn.disabled = isSubmitting;
            });

            const cancelBtn = changePasswordModalElement.querySelector('[data-bs-dismiss="modal"]');
            if (cancelBtn) {
                cancelBtn.disabled = isSubmitting;
            }

            const closeBtn = changePasswordModalElement.querySelector(".btn-close");
            if (closeBtn) {
                closeBtn.disabled = isSubmitting;
                closeBtn.style.pointerEvents = isSubmitting ? "none" : "";
            }
        }
    };

    const resetChangePasswordInputs = () => {
        setChangePasswordSubmittingState(false);
        [currentPasswordInput, newPasswordInput, confirmPasswordInput].forEach((input) => {
            if (input) {
                input.value = "";
            }
        });
        updatePasswordRequirementsUi();
    };

    const handleChangePassword = async () => {
        if (!securityChangePasswordUrl || !changePasswordForm) {
            showToast("Password updates are unavailable.", "warning");
            return;
        }

        const requirementState = updatePasswordRequirementsUi();
        if (!requirementState.hasCurrent) {
            setInlineStatus(changePasswordStatus, "Current password is required.", "danger");
            showToast("Current password is required.", "warning");
            return;
        }

        if (!requirementState.hasConfirm) {
            setInlineStatus(changePasswordStatus, "Confirm your new password.", "danger");
            showToast("Confirm your new password.", "warning");
            return;
        }

        if (!requirementState.match) {
            setInlineStatus(changePasswordStatus, "Passwords do not match.", "danger");
            showToast("Passwords do not match.", "warning");
            return;
        }

        if (!requirementState.isDifferent) {
            setInlineStatus(changePasswordStatus, "New password must be different.", "danger");
            showToast("New password must be different from the current password.", "warning");
            return;
        }

        if (!requirementState.isValid) {
            setInlineStatus(changePasswordStatus, "Password requirements not met.", "danger");
            showToast("Password requirements not met.", "warning");
            return;
        }

        if (!changePasswordForm.checkValidity()) {
            changePasswordForm.reportValidity();
            return;
        }

        const payload = {
            current_password: currentPasswordInput ? currentPasswordInput.value : "",
            new_password: newPasswordInput ? newPasswordInput.value : "",
            confirm_password: confirmPasswordInput ? confirmPasswordInput.value : "",
        };

        setButtonLoading(changePasswordButton, true, "Updating...");
        setInlineStatus(changePasswordStatus, "Saving...", "success");
        setChangePasswordSubmittingState(true);

        try {
            const response = await postJson(securityChangePasswordUrl, payload);
            if (response.status === 401) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }

            const result = await parseJsonSafe(response);
            if (!response.ok || !result || !result.ok) {
                const message = result && result.message
                    ? String(result.message)
                    : "Unable to update password.";
                throw new Error(message);
            }

            resetChangePasswordInputs();
            setInlineStatus(changePasswordStatus, "Updated", "success");
            showToast(result.message || "Password updated successfully.", "success");
            if (changePasswordModal) {
                changePasswordModal.hide();
            }
        } catch (error) {
            setInlineStatus(changePasswordStatus, "Update failed", "danger");
            showToast(error && error.message ? String(error.message) : "Unable to update password.", "danger");
        } finally {
            setButtonLoading(changePasswordButton, false);
            setChangePasswordSubmittingState(false);
        }
    };

    const bindSecurityActions = () => {
        bindPasswordToggles();

        if (changePasswordModalElement) {
            changePasswordModal = getModalInstance(changePasswordModalElement);
            changePasswordModalElement.addEventListener("shown.bs.modal", () => {
                if (currentPasswordInput) {
                    currentPasswordInput.focus();
                }
                clearInlineStatus(changePasswordStatus);
                updatePasswordRequirementsUi();
            });
            changePasswordModalElement.addEventListener("hidden.bs.modal", () => {
                resetChangePasswordInputs();
                clearInlineStatus(changePasswordStatus);
            });
        }

        if (changePasswordForm) {
            changePasswordForm.addEventListener("submit", (event) => {
                event.preventDefault();
                handleChangePassword();
            });
        }

        [currentPasswordInput, newPasswordInput, confirmPasswordInput].forEach((input) => {
            if (!input) {
                return;
            }
            input.addEventListener("input", () => {
                updatePasswordRequirementsUi();
                clearInlineStatus(changePasswordStatus);
            });
        });

        if (loginAlertsToggle) {
            loginAlertsToggle.addEventListener("change", () => {
                handleLoginAlertsToggle(loginAlertsToggle.checked);
            });
        }

        if (clientRecordEmailsToggle) {
            clientRecordEmailsToggle.addEventListener("change", () => {
                handleClientRecordEmailsToggle(clientRecordEmailsToggle.checked);
            });
        }

        if (clientDetailsLockToggle) {
            clientDetailsLockToggle.addEventListener("change", () => {
                clearInlineStatus(clientDetailsLockFeedback);
            });
        }

        if (clientDetailsLockPasswordInput) {
            clientDetailsLockPasswordInput.addEventListener("input", () => {
                clearInlineStatus(clientDetailsLockFeedback);
            });
        }

        if (clientDetailsLockSaveButton) {
            clientDetailsLockSaveButton.addEventListener("click", () => {
                handleClientDetailsLockSave();
            });
        }

        if (deactivationRequestModalElement) {
            deactivationRequestModal = getModalInstance(deactivationRequestModalElement);
            deactivationRequestModalElement.addEventListener("shown.bs.modal", () => {
                if (deactivationPasswordInput) {
                    deactivationPasswordInput.focus();
                }
                clearInlineStatus(deactivationRequestStatus);
            });
            deactivationRequestModalElement.addEventListener("hidden.bs.modal", () => {
                resetDeactivationRequestInputs();
            });
        }

        if (deactivationRequestForm) {
            deactivationRequestForm.addEventListener("submit", (event) => {
                event.preventDefault();
                handleDeactivationRequestSubmit();
            });
        }

        [deactivationReasonInput, deactivationPasswordInput].forEach((input) => {
            if (!input) {
                return;
            }
            input.addEventListener("input", () => {
                clearInlineStatus(deactivationRequestStatus);
            });
        });

        let isTwoFactorActive = Boolean(config.twoFactorEnabled);

        const updateTwoFactorUiState = (enabled) => {
            isTwoFactorActive = Boolean(enabled);
            if (twoFactorStatus) {
                twoFactorStatus.textContent = isTwoFactorActive ? "Enabled" : "Disabled";
                twoFactorStatus.classList.toggle("is-enabled", isTwoFactorActive);
                twoFactorStatus.classList.toggle("is-neutral", !isTwoFactorActive);
            }
            if (twoFactorOpenBtn) {
                twoFactorOpenBtn.classList.toggle("d-none", isTwoFactorActive);
            }
            if (twoFactorOpenDisableBtn) {
                twoFactorOpenDisableBtn.classList.toggle("d-none", !isTwoFactorActive);
            }
        };

        const fetchTwoFactorSetupData = async () => {
            if (!twoFactorSetupUrl) {
                return;
            }
            if (twoFactorModalFeedback) {
                twoFactorModalFeedback.classList.add("d-none");
                twoFactorModalFeedback.textContent = "";
            }
            if (twoFactorQrImage) {
                twoFactorQrImage.classList.add("d-none");
                twoFactorQrImage.src = "";
            }
            if (twoFactorQrSpinner) {
                twoFactorQrSpinner.classList.remove("d-none");
            }
            if (twoFactorKeyInput) {
                twoFactorKeyInput.value = "Generating key...";
            }
            if (twoFactorCodeInput) {
                twoFactorCodeInput.value = "";
                twoFactorCodeInput.disabled = false;
            }
            if (twoFactorSubmitBtn) {
                twoFactorSubmitBtn.disabled = false;
            }

            try {
                const response = await postJson(twoFactorSetupUrl, {});
                const result = await parseJsonSafe(response);

                if (!response.ok || !result || !result.ok) {
                    const message = result && result.message ? result.message : "Unable to generate 2FA setup key.";
                    if (twoFactorModalFeedback) {
                        twoFactorModalFeedback.textContent = message;
                        twoFactorModalFeedback.classList.remove("d-none");
                    }
                    if (twoFactorKeyInput) {
                        twoFactorKeyInput.value = "";
                    }
                    if (twoFactorQrSpinner) {
                        twoFactorQrSpinner.classList.add("d-none");
                    }
                    return;
                }

                if (twoFactorKeyInput) {
                    twoFactorKeyInput.value = result.secret || "";
                }

                if (result.qr_code_data_url && twoFactorQrImage) {
                    twoFactorQrImage.src = result.qr_code_data_url;
                    twoFactorQrImage.classList.remove("d-none");
                    if (twoFactorQrSpinner) {
                        twoFactorQrSpinner.classList.add("d-none");
                    }
                } else if (twoFactorQrSpinner) {
                    twoFactorQrSpinner.classList.add("d-none");
                }

                if (twoFactorCodeInput) {
                    window.setTimeout(() => twoFactorCodeInput.focus(), 250);
                }
            } catch (err) {
                if (twoFactorModalFeedback) {
                    twoFactorModalFeedback.textContent = "Network error. Please try again.";
                    twoFactorModalFeedback.classList.remove("d-none");
                }
                if (twoFactorQrSpinner) {
                    twoFactorQrSpinner.classList.add("d-none");
                }
            }
        };

        const bindTwoFactorActions = () => {
            if (twoFactorModalElement) {
                twoFactorModal = getModalInstance(twoFactorModalElement);
                twoFactorModalElement.addEventListener("show.bs.modal", () => {
                    fetchTwoFactorSetupData();
                });
                twoFactorModalElement.addEventListener("hidden.bs.modal", () => {
                    if (twoFactorCodeInput) {
                        twoFactorCodeInput.value = "";
                    }
                    if (twoFactorModalFeedback) {
                        twoFactorModalFeedback.classList.add("d-none");
                        twoFactorModalFeedback.textContent = "";
                    }
                });
            }

            if (twoFactorDisableModalElement) {
                twoFactorDisableModal = getModalInstance(twoFactorDisableModalElement);
                twoFactorDisableModalElement.addEventListener("hidden.bs.modal", () => {
                    if (twoFactorDisableForm) {
                        twoFactorDisableForm.reset();
                    }
                    if (twoFactorDisableFeedback) {
                        twoFactorDisableFeedback.classList.add("d-none");
                        twoFactorDisableFeedback.textContent = "";
                    }
                });
            }

            if (twoFactorCopyBtn && twoFactorKeyInput) {
                twoFactorCopyBtn.addEventListener("click", async () => {
                    const keyValue = String(twoFactorKeyInput.value || "").trim();
                    if (!keyValue || keyValue === "Generating key...") {
                        return;
                    }

                    try {
                        if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
                            await navigator.clipboard.writeText(keyValue);
                        } else {
                            twoFactorKeyInput.select();
                            document.execCommand("copy");
                        }

                        const originalHtml = twoFactorCopyBtn.innerHTML;
                        twoFactorCopyBtn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
                        twoFactorCopyBtn.classList.add("is-copied");

                        showToast("Setup key copied to clipboard.", "success");

                        window.setTimeout(() => {
                            twoFactorCopyBtn.innerHTML = originalHtml;
                            twoFactorCopyBtn.classList.remove("is-copied");
                        }, 2000);
                    } catch {
                        showToast("Could not copy automatically. Please copy the key manually.", "warning");
                    }
                });
            }

            const handleEnableSubmit = async () => {
                const enteredCode = twoFactorCodeInput ? String(twoFactorCodeInput.value || "").trim().replace(/\D+/g, "") : "";
                if (!enteredCode || enteredCode.length !== 6) {
                    if (twoFactorModalFeedback) {
                        twoFactorModalFeedback.textContent = "Please enter the 6-digit verification code from your authenticator app.";
                        twoFactorModalFeedback.classList.remove("d-none");
                    }
                    if (twoFactorCodeInput) {
                        twoFactorCodeInput.focus();
                    }
                    return;
                }

                if (twoFactorModalFeedback) {
                    twoFactorModalFeedback.classList.add("d-none");
                    twoFactorModalFeedback.textContent = "";
                }

                const originalBtnHtml = twoFactorSubmitBtn ? twoFactorSubmitBtn.innerHTML : "";
                if (twoFactorSubmitBtn) {
                    twoFactorSubmitBtn.disabled = true;
                    twoFactorSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Verifying...';
                }
                if (twoFactorCodeInput) {
                    twoFactorCodeInput.disabled = true;
                }

                try {
                    const response = await postJson(twoFactorConfirmUrl, { code: enteredCode });
                    const result = await parseJsonSafe(response);

                    if (!response.ok || !result || !result.ok) {
                        const message = result && result.message ? result.message : "Invalid verification code. Please check your app and try again.";
                        if (twoFactorModalFeedback) {
                            twoFactorModalFeedback.textContent = message;
                            twoFactorModalFeedback.classList.remove("d-none");
                        }
                        if (twoFactorCodeInput) {
                            twoFactorCodeInput.disabled = false;
                            twoFactorCodeInput.select();
                            twoFactorCodeInput.focus();
                        }
                        if (twoFactorSubmitBtn) {
                            twoFactorSubmitBtn.disabled = false;
                            twoFactorSubmitBtn.innerHTML = originalBtnHtml;
                        }
                        return;
                    }

                    updateTwoFactorUiState(true);
                    showToast(result.message || "Two-factor authentication enabled successfully.", "success");

                    if (twoFactorModal) {
                        twoFactorModal.hide();
                    }
                } catch (err) {
                    if (twoFactorModalFeedback) {
                        twoFactorModalFeedback.textContent = "Something went wrong. Please try again.";
                        twoFactorModalFeedback.classList.remove("d-none");
                    }
                    if (twoFactorCodeInput) {
                        twoFactorCodeInput.disabled = false;
                    }
                    if (twoFactorSubmitBtn) {
                        twoFactorSubmitBtn.disabled = false;
                        twoFactorSubmitBtn.innerHTML = originalBtnHtml;
                    }
                }
            };

            if (twoFactorSubmitBtn) {
                twoFactorSubmitBtn.addEventListener("click", handleEnableSubmit);
            }

            if (twoFactorCodeInput) {
                twoFactorCodeInput.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        handleEnableSubmit();
                    }
                });
            }

            // Disable 2FA flow
            if (twoFactorDisableForm) {
                twoFactorDisableForm.addEventListener("submit", async (e) => {
                    e.preventDefault();

                    const currentPassword = twoFactorDisablePasswordInput ? twoFactorDisablePasswordInput.value : "";
                    if (!currentPassword) {
                        if (twoFactorDisableFeedback) {
                            twoFactorDisableFeedback.textContent = "Current password is required.";
                            twoFactorDisableFeedback.classList.remove("d-none");
                        }
                        if (twoFactorDisablePasswordInput) {
                            twoFactorDisablePasswordInput.focus();
                        }
                        return;
                    }

                    if (twoFactorDisableFeedback) {
                        twoFactorDisableFeedback.classList.add("d-none");
                        twoFactorDisableFeedback.textContent = "";
                    }

                    const originalDisableHtml = twoFactorDisableSubmitBtn ? twoFactorDisableSubmitBtn.innerHTML : "";
                    if (twoFactorDisableSubmitBtn) {
                        twoFactorDisableSubmitBtn.disabled = true;
                        twoFactorDisableSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Turning off...';
                    }
                    if (twoFactorDisablePasswordInput) {
                        twoFactorDisablePasswordInput.disabled = true;
                    }

                    try {
                        const response = await postJson(twoFactorDisableUrl, { current_password: currentPassword });
                        const result = await parseJsonSafe(response);

                        if (!response.ok || !result || !result.ok) {
                            const message = result && result.message ? result.message : "Current password is incorrect.";
                            if (twoFactorDisableFeedback) {
                                twoFactorDisableFeedback.textContent = message;
                                twoFactorDisableFeedback.classList.remove("d-none");
                            }
                            if (twoFactorDisablePasswordInput) {
                                twoFactorDisablePasswordInput.disabled = false;
                                twoFactorDisablePasswordInput.select();
                                twoFactorDisablePasswordInput.focus();
                            }
                            if (twoFactorDisableSubmitBtn) {
                                twoFactorDisableSubmitBtn.disabled = false;
                                twoFactorDisableSubmitBtn.innerHTML = originalDisableHtml;
                            }
                            return;
                        }

                        updateTwoFactorUiState(false);
                        showToast(result.message || "Two-factor authentication disabled successfully.", "success");

                        if (twoFactorDisableModal) {
                            twoFactorDisableModal.hide();
                        }
                    } catch (err) {
                        if (twoFactorDisableFeedback) {
                            twoFactorDisableFeedback.textContent = "Something went wrong. Please try again.";
                            twoFactorDisableFeedback.classList.remove("d-none");
                        }
                        if (twoFactorDisablePasswordInput) {
                            twoFactorDisablePasswordInput.disabled = false;
                        }
                        if (twoFactorDisableSubmitBtn) {
                            twoFactorDisableSubmitBtn.disabled = false;
                            twoFactorDisableSubmitBtn.innerHTML = originalDisableHtml;
                        }
                    }
                });
            }
        };

        bindTwoFactorActions();
        updateTwoFactorUiState(isTwoFactorActive);

        updateLoginAlertsUiState(isLoginAlertsEnabled());
        updateClientRecordEmailsUiState(isClientRecordEmailsEnabled());
        updateClientDetailsLockUiState(isClientDetailsLockEnabled());
        clearInlineStatus(changePasswordStatus);
        clearInlineStatus(loginAlertsFeedback);
        clearInlineStatus(clientRecordEmailsFeedback);
        clearInlineStatus(clientDetailsLockFeedback);
        clearInlineStatus(deactivationRequestStatus);
        updatePasswordRequirementsUi();
    };

    const bindSettingsScrollSpy = () => {
        if (!settingsNavLinks.length || !settingsSections.length) {
            return;
        }

        const sectionById = settingsSections
            .filter((section) => Boolean(section.id))
            .map((section) => ({
                id: section.id,
                element: section,
            }));

        if (!sectionById.length) {
            return;
        }

        const navById = new Map(
            settingsNavLinks
                .map((link) => {
                    const href = String(link.getAttribute("href") || "").trim();
                    if (!href.startsWith("#")) {
                        return null;
                    }
                    return [href.slice(1), link];
                })
                .filter(Boolean)
        );

        const setActiveLink = (targetId) => {
            settingsNavLinks.forEach((link) => {
                const href = String(link.getAttribute("href") || "").trim();
                const linkTarget = href.startsWith("#") ? href.slice(1) : "";
                const isActive = linkTarget === targetId;
                link.classList.toggle("is-active", isActive);
                if (isActive) {
                    link.setAttribute("aria-current", "true");
                } else {
                    link.removeAttribute("aria-current");
                }
            });
        };

        let pendingAnimationFrame = null;
        const scrollOffset = 160;

        const updateActiveFromScroll = () => {
            const scrollPosition = window.scrollY + scrollOffset;
            let activeId = sectionById[0].id;

            sectionById.forEach((section) => {
                if (section.element.offsetTop <= scrollPosition) {
                    activeId = section.id;
                }
            });

            setActiveLink(activeId);
        };

        const scheduleScrollUpdate = () => {
            if (pendingAnimationFrame) {
                return;
            }
            pendingAnimationFrame = window.requestAnimationFrame(() => {
                pendingAnimationFrame = null;
                updateActiveFromScroll();
            });
        };

        settingsNavLinks.forEach((link) => {
            link.addEventListener("click", () => {
                const href = String(link.getAttribute("href") || "").trim();
                const targetId = href.startsWith("#") ? href.slice(1) : "";
                if (targetId && navById.has(targetId)) {
                    setActiveLink(targetId);
                }
            });
        });

        window.addEventListener("scroll", scheduleScrollUpdate, { passive: true });
        window.addEventListener("resize", scheduleScrollUpdate);
        updateActiveFromScroll();
    };

    const bindHeaderActions = () => {
        if (dashboardProfileAction) {
            dashboardProfileAction.addEventListener("click", () => {
                window.location.assign(String(urls.profilePage || "/profile/"));
            });
        }

        if (dashboardLogoutAction) {
            dashboardLogoutAction.addEventListener("click", async () => {
                dashboardLogoutAction.disabled = true;

                try {
                    const redirectUrl = await logoutCurrentUser();
                    showToast("Logging out...", "success");
                    window.location.assign(redirectUrl);
                } finally {
                    dashboardLogoutAction.disabled = false;
                }
            });
        }
    };

    const initializeSettingsPage = () => {
        sidebarState.restoreDesktopState();
        hydrateHeaderUser();

        if (shared && typeof shared.applyStoredTheme === "function") {
            shared.applyStoredTheme();
        }

        bindSectionInputs();
        bindThemeControls();
        bindSecurityActions();
        bindSettingsScrollSpy();
        bindHeaderActions();
        syncThemeState();
        window.addEventListener("resize", () => {
            sidebarState.closeMobileSidebar();
            sidebarState.restoreDesktopState();
        });
    };

    initializeSettingsPage();
})();
