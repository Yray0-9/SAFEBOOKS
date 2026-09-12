(() => {
    const navLinks = Array.from(document.querySelectorAll(".settings-nav-link"));
    const saveButtons = Array.from(document.querySelectorAll(".btn-save-settings"));
    const resetButtons = Array.from(document.querySelectorAll(".btn-reset-settings"));
    const toastContainer = document.getElementById("uiToastContainer") || document.querySelector(".toast-container");
    const shared = window.SafeBooksShared || null;

    // ── Security config (moved from admin profile) ──────────────────────────
    const securityConfig = window.SafeBooksAdminSettingsConfig || {};
    const securityUrls = securityConfig.urls || {};

    // ── Toast feedback helper ──────────────────────────────────────────────
    const showNotification = (message, level = "info") => {
        if (shared && typeof shared.showToast === "function") {
            shared.showToast(toastContainer, message, level);
            return;
        }

        // Fallback UI toast if SafeBooksShared is not present
        const toast = document.createElement("div");
        toast.className = `alert alert-${level === "success" ? "success" : "primary"} position-fixed bottom-0 end-0 m-3 shadow-lg`;
        toast.style.zIndex = "9999";
        toast.style.borderRadius = "12px";
        toast.style.fontSize = "0.88rem";
        toast.style.fontWeight = "600";
        toast.innerHTML = `<i class="bi bi-${level === "success" ? "check-circle-fill" : "info-circle-fill"} me-2"></i>${message}`;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 2800);
    };

    // ── Save buttons interaction (UI simulation mode) ─────────────────────
    saveButtons.forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const originalText = btn.innerHTML;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Saving...`;
            btn.disabled = true;

            setTimeout(() => {
                btn.innerHTML = `<i class="bi bi-check2 me-1"></i> Saved!`;
                showNotification("System settings preview saved locally (UI Preview Mode).", "success");

                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }, 1500);
            }, 500);
        });
    });

    // ── Smooth scroll & active navigation ─────────────────────────────────
    if (!navLinks.length) {
        return;
    }

    const sections = navLinks
        .map((link) => {
            const target = String(link.getAttribute("href") || "").trim();
            if (!target.startsWith("#")) {
                return null;
            }

            const element = document.querySelector(target);
            if (!element) {
                return null;
            }

            return { link, element };
        })
        .filter(Boolean);

    if (!sections.length) {
        return;
    }

    const setActiveLink = (activeLink) => {
        navLinks.forEach((link) => {
            const isActive = link === activeLink;
            link.classList.toggle("is-active", isActive);
            if (isActive) {
                link.setAttribute("aria-current", "true");
            } else {
                link.removeAttribute("aria-current");
            }
        });
    };

    const resolveScrollOffset = () => {
        const layout = document.querySelector(".admin-settings-layout, .settings-layout");
        if (!layout) {
            return 160;
        }

        const rawValue = getComputedStyle(layout)
            .getPropertyValue("--settings-sticky-offset")
            .trim();
        if (!rawValue) {
            return 160;
        }

        const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
        if (rawValue.endsWith("rem")) {
            return (parseFloat(rawValue) || 0) * rootFontSize + 16;
        }

        if (rawValue.endsWith("px")) {
            return (parseFloat(rawValue) || 0) + 16;
        }

        const numericValue = parseFloat(rawValue);
        return Number.isFinite(numericValue) ? numericValue + 16 : 160;
    };

    let scrollOffset = resolveScrollOffset();
    let rafPending = false;

    const updateActiveFromScroll = () => {
        const scrollPosition = window.scrollY + scrollOffset;
        let activeLink = sections[0].link;

        sections.forEach((section) => {
            if (section.element.offsetTop <= scrollPosition) {
                activeLink = section.link;
            }
        });

        setActiveLink(activeLink);
    };

    const scheduleUpdate = () => {
        if (rafPending) {
            return;
        }

        rafPending = true;
        window.requestAnimationFrame(() => {
            rafPending = false;
            updateActiveFromScroll();
        });
    };

    navLinks.forEach((link) => {
        link.addEventListener("click", (e) => {
            const targetId = String(link.getAttribute("href") || "").trim();
            if (targetId.startsWith("#")) {
                const targetEl = document.querySelector(targetId);
                if (targetEl) {
                    e.preventDefault();
                    window.scrollTo({
                        top: targetEl.offsetTop - scrollOffset + 10,
                        behavior: "smooth",
                    });
                    setActiveLink(link);
                }
            }
        });
    });

    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", () => {
        scrollOffset = resolveScrollOffset();
        scheduleUpdate();
    });
    scrollOffset = resolveScrollOffset();
    updateActiveFromScroll();

    // =====================================================================
    //  APPEARANCE & THEME ENGINE
    // =====================================================================

    const themeButtons = Array.from(document.querySelectorAll("[data-theme-value]"));
    const themeSwatches = Array.from(document.querySelectorAll("[data-theme-swatch]"));
    const applyThemeBtn = document.getElementById("adminApplyThemeBtn");
    const swatchCheckLight = document.getElementById("adminSwatchCheckLight");
    const swatchCheckDark = document.getElementById("adminSwatchCheckDark");

    const getStoredThemeState = () => {
        if (shared && typeof shared.getThemePreference === "function") {
            const pref = shared.getThemePreference();
            return pref.theme === "dark" ? "dark" : "light";
        }
        try {
            const stored = window.localStorage.getItem("safebooks.ui.theme");
            if (stored === "dark" || stored === "light") return stored;
            return document.body.classList.contains("theme-dark") ? "dark" : "light";
        } catch {
            return document.body.classList.contains("theme-dark") ? "dark" : "light";
        }
    };

    let storedTheme = getStoredThemeState();
    let pendingTheme = storedTheme;

    const updateThemeUiSelection = (selectedTheme) => {
        const normalized = selectedTheme === "dark" ? "dark" : "light";
        themeButtons.forEach((btn) => {
            const val = btn.getAttribute("data-theme-value");
            const isActive = val === normalized;
            btn.classList.toggle("is-active", isActive);
            btn.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        themeSwatches.forEach((swatch) => {
            const swatchVal = swatch.getAttribute("data-theme-swatch");
            const isSwatchActive = swatchVal === normalized;
            swatch.classList.toggle("is-active", isSwatchActive);
        });

        if (swatchCheckLight) {
            swatchCheckLight.classList.toggle("d-none", normalized !== "light");
        }
        if (swatchCheckDark) {
            swatchCheckDark.classList.toggle("d-none", normalized !== "dark");
        }

        // Enable or disable Apply Theme button based on whether a new theme is selected
        if (applyThemeBtn) {
            const hasChange = normalized !== storedTheme;
            applyThemeBtn.disabled = !hasChange;
            if (hasChange) {
                applyThemeBtn.removeAttribute("aria-disabled");
            } else {
                applyThemeBtn.setAttribute("aria-disabled", "true");
            }
        }
    };

    const selectPendingTheme = (themeValue) => {
        const normalized = themeValue === "dark" ? "dark" : "light";
        pendingTheme = normalized;
        updateThemeUiSelection(pendingTheme);
    };

    const applyThemeChanges = () => {
        if (pendingTheme === storedTheme && applyThemeBtn && applyThemeBtn.disabled) {
            return;
        }

        const targetTheme = pendingTheme === "dark" ? "dark" : "light";
        const originalText = applyThemeBtn ? applyThemeBtn.innerHTML : "Apply Theme";

        if (applyThemeBtn) {
            applyThemeBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Applying...`;
            applyThemeBtn.disabled = true;
            applyThemeBtn.setAttribute("aria-disabled", "true");
        }

        if (shared && typeof shared.setThemePreference === "function") {
            shared.setThemePreference(targetTheme, false);
        } else {
            document.body.classList.remove("theme-light", "theme-dark");
            document.body.classList.add(`theme-${targetTheme}`);
            try {
                window.localStorage.setItem("safebooks.ui.theme", targetTheme);
                window.localStorage.setItem("safebooks.ui.followSystem", "0");
            } catch {}
        }

        storedTheme = targetTheme;
        pendingTheme = targetTheme;

        setTimeout(() => {
            if (applyThemeBtn) {
                applyThemeBtn.innerHTML = `<i class="bi bi-check2 me-1"></i> Applied!`;
            }

            const label = targetTheme === "dark" ? "Dark Mode" : "Light Mode";
            showNotification(`Theme successfully switched to ${label}.`, "success");

            setTimeout(() => {
                if (applyThemeBtn) {
                    applyThemeBtn.innerHTML = originalText;
                    applyThemeBtn.disabled = true;
                    applyThemeBtn.setAttribute("aria-disabled", "true");
                }
            }, 1200);
        }, 300);
    };

    themeButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const val = btn.getAttribute("data-theme-value");
            if (val) selectPendingTheme(val);
        });
    });

    themeSwatches.forEach((swatch) => {
        swatch.addEventListener("click", () => {
            const val = swatch.getAttribute("data-theme-swatch");
            if (val) selectPendingTheme(val);
        });
        swatch.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                const val = swatch.getAttribute("data-theme-swatch");
                if (val) selectPendingTheme(val);
            }
        });
    });

    if (applyThemeBtn) {
        applyThemeBtn.addEventListener("click", (e) => {
            e.preventDefault();
            applyThemeChanges();
        });
    }

    // Initialize UI selection on load
    updateThemeUiSelection(storedTheme);

    // =====================================================================
    //  PASSWORD SECURITY & AUTHENTICATOR SECURITY
    //  (migrated from admin_profile_page.js)
    // =====================================================================

    const adminPasswordChangeBtn = document.getElementById("adminPasswordChangeBtn");
    const adminPasswordChangeModalElement = document.getElementById("adminPasswordChangeModal");
    const adminPasswordChangeForm = document.getElementById("adminPasswordChangeForm");
    const adminCurrentPassword = document.getElementById("adminCurrentPassword");
    const adminNewPassword = document.getElementById("adminNewPassword");
    const adminConfirmPassword = document.getElementById("adminConfirmPassword");
    const adminPasswordSave = document.getElementById("adminPasswordSave");
    const adminPasswordFeedback = document.getElementById("adminPasswordFeedback");

    const adminTwoFactorStatus = document.getElementById("adminTwoFactorStatus");
    const adminTwoFactorTitle = document.getElementById("adminTwoFactorTitle");
    const adminTwoFactorDescription = document.getElementById("adminTwoFactorDescription");
    const adminTwoFactorAction = document.getElementById("adminTwoFactorAction");
    const adminTwoFactorRecoveryAction = document.getElementById("adminTwoFactorRecoveryAction");
    const adminTwoFactorSetupModalElement = document.getElementById("adminTwoFactorSetupModal");
    const adminTwoFactorSetupForm = document.getElementById("adminTwoFactorSetupForm");
    const adminTwoFactorPasswordStep = document.getElementById("adminTwoFactorPasswordStep");
    const adminTwoFactorCodeStep = document.getElementById("adminTwoFactorCodeStep");
    const adminTwoFactorCurrentPassword = document.getElementById("adminTwoFactorCurrentPassword");
    const adminTwoFactorQrPanel = document.getElementById("adminTwoFactorQrPanel");
    const adminTwoFactorQrCode = document.getElementById("adminTwoFactorQrCode");
    const adminTwoFactorSetupKey = document.getElementById("adminTwoFactorSetupKey");
    const adminTwoFactorCopyKey = document.getElementById("adminTwoFactorCopyKey");
    const adminTwoFactorCode = document.getElementById("adminTwoFactorCode");
    const adminTwoFactorSetupFeedback = document.getElementById("adminTwoFactorSetupFeedback");
    const adminTwoFactorBegin = document.getElementById("adminTwoFactorBegin");
    const adminTwoFactorConfirm = document.getElementById("adminTwoFactorConfirm");
    const adminRecoveryCodesModalElement = document.getElementById("adminRecoveryCodesModal");
    const adminRecoveryCodeList = document.getElementById("adminRecoveryCodeList");
    const adminRecoveryCodesFeedback = document.getElementById("adminRecoveryCodesFeedback");
    const adminRecoveryCodesCopy = document.getElementById("adminRecoveryCodesCopy");
    const adminRecoveryCodesPrint = document.getElementById("adminRecoveryCodesPrint");
    const adminRecoveryCodesDone = document.getElementById("adminRecoveryCodesDone");
    const adminRecoveryRegenerateModalElement = document.getElementById("adminRecoveryRegenerateModal");
    const adminRecoveryRegenerateForm = document.getElementById("adminRecoveryRegenerateForm");
    const adminRecoveryRegeneratePassword = document.getElementById("adminRecoveryRegeneratePassword");
    const adminRecoveryRegenerateCode = document.getElementById("adminRecoveryRegenerateCode");
    const adminRecoveryRegenerateFeedback = document.getElementById("adminRecoveryRegenerateFeedback");
    const adminRecoveryRegenerateButton = document.getElementById("adminRecoveryRegenerate");
    const adminTwoFactorDisableModalElement = document.getElementById("adminTwoFactorDisableModal");
    const adminTwoFactorDisableForm = document.getElementById("adminTwoFactorDisableForm");
    const adminTwoFactorDisablePassword = document.getElementById("adminTwoFactorDisablePassword");
    const adminTwoFactorDisableCode = document.getElementById("adminTwoFactorDisableCode");
    const adminTwoFactorDisableFeedback = document.getElementById("adminTwoFactorDisableFeedback");
    const adminTwoFactorDisableButton = document.getElementById("adminTwoFactorDisable");

    const passwordModal = adminPasswordChangeModalElement && window.bootstrap
        ? window.bootstrap.Modal.getOrCreateInstance(adminPasswordChangeModalElement)
        : null;
    const setupModal = adminTwoFactorSetupModalElement && window.bootstrap
        ? window.bootstrap.Modal.getOrCreateInstance(adminTwoFactorSetupModalElement)
        : null;
    const recoveryCodesModal = adminRecoveryCodesModalElement && window.bootstrap
        ? window.bootstrap.Modal.getOrCreateInstance(adminRecoveryCodesModalElement)
        : null;
    const recoveryRegenerateModal = adminRecoveryRegenerateModalElement && window.bootstrap
        ? window.bootstrap.Modal.getOrCreateInstance(adminRecoveryRegenerateModalElement)
        : null;
    const disableModal = adminTwoFactorDisableModalElement && window.bootstrap
        ? window.bootstrap.Modal.getOrCreateInstance(adminTwoFactorDisableModalElement)
        : null;

    const escapeHtml = (value) => {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    const parseJsonSafe = async (response) => {
        if (shared && typeof shared.parseJsonSafe === "function") {
            return shared.parseJsonSafe(response);
        }
        try {
            return await response.json();
        } catch (error) {
            return null;
        }
    };

    const getCookieValue = (name) => {
        if (shared && typeof shared.getCookieValue === "function") {
            return shared.getCookieValue(name);
        }
        return "";
    };

    const setButtonLoading = (button, isLoading, loadingText) => {
        if (!button) {
            return;
        }
        if (!button.dataset.defaultLabel) {
            button.dataset.defaultLabel = button.textContent || "";
        }
        button.disabled = isLoading;
        button.textContent = isLoading ? loadingText : button.dataset.defaultLabel;
    };

    const postJson = async (url, payload) => {
        const csrfToken = getCookieValue("csrftoken");
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                "X-CSRFToken": csrfToken,
            },
            credentials: "same-origin",
            body: JSON.stringify(payload || {}),
        });
    };

    const handleAuthRedirect = (response) => {
        if (response.status === 401 || response.status === 403) {
            showNotification("Admin session expired. Please log in again.", "warning");
            window.location.assign(String(securityUrls.loginPage || "/login/"));
            return true;
        }
        return false;
    };

    const setPasswordStatus = (message) => {
        if (adminPasswordStatus) {
            adminPasswordStatus.textContent = message;
        }
    };

    const setSecurityFeedback = (element, message, isSuccess = false) => {
        if (!element) {
            return;
        }
        element.textContent = String(message || "");
        element.classList.toggle("is-success", Boolean(isSuccess));
    };

    let twoFactorEnabled = false;
    let recoveryCodesRemaining = 0;
    let visibleRecoveryCodes = [];
    let pendingRecoveryCodes = [];

    const renderTwoFactorStatus = (status) => {
        twoFactorEnabled = Boolean(status && status.enabled);
        recoveryCodesRemaining = Number.isFinite(Number(status && status.recovery_codes_remaining))
            ? Math.max(0, Number(status.recovery_codes_remaining))
            : 0;
        if (adminTwoFactorStatus) {
            adminTwoFactorStatus.textContent = twoFactorEnabled ? "Enabled" : "Not enabled";
            adminTwoFactorStatus.classList.remove("is-loading");
            adminTwoFactorStatus.classList.toggle("is-enabled", twoFactorEnabled);
        }
        if (adminTwoFactorTitle) {
            adminTwoFactorTitle.textContent = twoFactorEnabled
                ? "Authenticator connected"
                : "Two-factor authentication";
        }
        if (adminTwoFactorDescription) {
            adminTwoFactorDescription.textContent = twoFactorEnabled
                ? `${recoveryCodesRemaining} recovery ${recoveryCodesRemaining === 1 ? "code" : "codes"} available.`
                : "Password-only admin access is currently active.";
        }
        if (adminTwoFactorRecoveryAction) {
            adminTwoFactorRecoveryAction.classList.toggle("d-none", !twoFactorEnabled);
            adminTwoFactorRecoveryAction.disabled = !twoFactorEnabled;
        }
        if (adminTwoFactorAction) {
            adminTwoFactorAction.disabled = false;
            adminTwoFactorAction.textContent = twoFactorEnabled ? "Disable 2FA" : "Enable 2FA";
        }
    };

    const resetPasswordVisibility = (scope = document) => {
        if (!scope) return;
        const toggleButtons = scope.querySelectorAll ? scope.querySelectorAll("[data-password-toggle-target]") : [];
        toggleButtons.forEach((toggleButton) => {
            const targetId = toggleButton.getAttribute("data-password-toggle-target");
            const inputElement = targetId ? document.getElementById(targetId) : null;
            if (inputElement instanceof HTMLInputElement) {
                inputElement.type = "password";
            }
            const iconElement = toggleButton.querySelector("i");
            if (iconElement) {
                iconElement.classList.remove("bi-eye-slash");
                iconElement.classList.add("bi-eye");
            }
            toggleButton.setAttribute("aria-label", "Show password");
        });
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

    const resetPasswordModal = () => {
        if (adminPasswordChangeForm) {
            adminPasswordChangeForm.reset();
        }
        if (adminPasswordChangeModalElement) {
            resetPasswordVisibility(adminPasswordChangeModalElement);
        }
        if (adminPasswordSave) {
            setButtonLoading(adminPasswordSave, false, "Update password");
        }
        const inputs = [adminCurrentPassword, adminNewPassword, adminConfirmPassword].filter(Boolean);
        inputs.forEach((input) => { input.disabled = false; });
        setSecurityFeedback(adminPasswordFeedback, "");
    };

    const resetSetupModal = () => {
        if (adminTwoFactorSetupForm) {
            adminTwoFactorSetupForm.reset();
        }
        if (adminTwoFactorSetupModalElement) {
            resetPasswordVisibility(adminTwoFactorSetupModalElement);
        }
        if (adminTwoFactorSetupKey) {
            adminTwoFactorSetupKey.value = "";
        }
        if (adminTwoFactorQrCode) {
            adminTwoFactorQrCode.removeAttribute("src");
        }
        if (adminTwoFactorQrPanel) {
            adminTwoFactorQrPanel.classList.add("d-none");
        }
        if (adminTwoFactorPasswordStep) {
            adminTwoFactorPasswordStep.classList.remove("d-none");
        }
        if (adminTwoFactorCodeStep) {
            adminTwoFactorCodeStep.classList.add("d-none");
        }
        if (adminTwoFactorBegin) {
            adminTwoFactorBegin.classList.remove("d-none");
            setButtonLoading(adminTwoFactorBegin, false, "Continue");
        }
        if (adminTwoFactorConfirm) {
            adminTwoFactorConfirm.classList.add("d-none");
            setButtonLoading(adminTwoFactorConfirm, false, "Enable 2FA");
        }
        setSecurityFeedback(adminTwoFactorSetupFeedback, "");
    };

    const resetDisableModal = () => {
        if (adminTwoFactorDisableForm) {
            adminTwoFactorDisableForm.reset();
        }
        if (adminTwoFactorDisableModalElement) {
            resetPasswordVisibility(adminTwoFactorDisableModalElement);
        }
        if (adminTwoFactorDisableButton) {
            setButtonLoading(adminTwoFactorDisableButton, false, "Disable 2FA");
        }
        setSecurityFeedback(adminTwoFactorDisableFeedback, "");
    };

    const resetRecoveryRegenerateModal = () => {
        if (adminRecoveryRegenerateForm) {
            adminRecoveryRegenerateForm.reset();
        }
        if (adminRecoveryRegenerateModalElement) {
            resetPasswordVisibility(adminRecoveryRegenerateModalElement);
        }
        if (adminRecoveryRegenerateButton) {
            setButtonLoading(adminRecoveryRegenerateButton, false, "Create new codes");
        }
        setSecurityFeedback(adminRecoveryRegenerateFeedback, "");
    };

    const clearVisibleRecoveryCodes = () => {
        visibleRecoveryCodes = [];
        if (adminRecoveryCodeList) {
            adminRecoveryCodeList.replaceChildren();
        }
        setSecurityFeedback(adminRecoveryCodesFeedback, "");
    };

    const showRecoveryCodes = (codes) => {
        visibleRecoveryCodes = Array.isArray(codes)
            ? codes.map((code) => String(code || "").trim()).filter(Boolean)
            : [];
        if (!visibleRecoveryCodes.length || !adminRecoveryCodeList) {
            showNotification("Recovery codes could not be displayed. Create a new set before login enforcement is enabled.", "danger");
            return;
        }

        adminRecoveryCodeList.replaceChildren(...visibleRecoveryCodes.map((code) => {
            const codeElement = document.createElement("code");
            codeElement.className = "profile-recovery-code";
            codeElement.textContent = code;
            return codeElement;
        }));
        setSecurityFeedback(adminRecoveryCodesFeedback, "These codes are visible only during this step.", true);
        if (recoveryCodesModal) {
            recoveryCodesModal.show();
        }
    };

    const queueRecoveryCodes = (codes, sourceModal) => {
        pendingRecoveryCodes = Array.isArray(codes) ? [...codes] : [];
        if (sourceModal) {
            sourceModal.hide();
            return;
        }
        const codesToShow = [...pendingRecoveryCodes];
        pendingRecoveryCodes = [];
        showRecoveryCodes(codesToShow);
    };

    const printRecoveryCodes = () => {
        if (!visibleRecoveryCodes.length) {
            return false;
        }
        const printWindow = window.open("", "_blank", "width=720,height=720");
        if (!printWindow) {
            return false;
        }
        printWindow.opener = null;
        const codeMarkup = visibleRecoveryCodes
            .map((code) => `<li>${escapeHtml(code)}</li>`)
            .join("");
        printWindow.document.write(`<!doctype html>
            <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <title>SafeBooks recovery codes</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; color: #142c57; }
                        h1 { font-size: 24px; margin-bottom: 8px; }
                        p { color: #536b94; line-height: 1.5; }
                        ul { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 0; list-style: none; }
                        li { border: 1px solid #c9d9f5; padding: 12px; font-family: Consolas, monospace; font-weight: 700; text-align: center; }
                    </style>
                </head>
                <body>
                    <h1>SafeBooks admin recovery codes</h1>
                    <p>Each code works once. Store this page privately and mark codes as they are used.</p>
                    <ul>${codeMarkup}</ul>
                </body>
            </html>`);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        return true;
    };

    // ── Load 2FA status from the profile API ──────────────────────────────
    const loadSecurityStatus = async () => {
        const url = String(securityUrls.adminProfileApi || "");
        if (!url) {
            return;
        }

        try {
            const response = await fetch(url, {
                method: "GET",
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            if (handleAuthRedirect(response)) {
                return;
            }
            const payload = await parseJsonSafe(response);
            if (!response.ok || !payload || !payload.ok) {
                return;
            }

            renderTwoFactorStatus(payload.two_factor || {});
        } catch (error) {
            // Status stays in "Checking..." if the request fails.
        }
    };

    // ── Password modal & change submission ──────────────────────────────
    if (adminPasswordChangeBtn) {
        adminPasswordChangeBtn.addEventListener("click", () => {
            resetPasswordModal();
            if (passwordModal) {
                passwordModal.show();
            }
        });
    }

    const handlePasswordSubmit = async (event) => {
        if (event) {
            event.preventDefault();
        }
        const url = String(securityUrls.adminPasswordApi || "");
        if (!url) {
            showNotification("Password updates are unavailable.", "warning");
            return;
        }

        const currentPassword = adminCurrentPassword ? adminCurrentPassword.value : "";
        const newPassword = adminNewPassword ? adminNewPassword.value : "";
        const confirmPassword = adminConfirmPassword ? adminConfirmPassword.value : "";

        if (!currentPassword) {
            setSecurityFeedback(adminPasswordFeedback, "Enter your current password.");
            if (adminCurrentPassword) {
                adminCurrentPassword.focus();
            }
            return;
        }
        if (!newPassword) {
            setSecurityFeedback(adminPasswordFeedback, "Enter your new password.");
            if (adminNewPassword) {
                adminNewPassword.focus();
            }
            return;
        }
        if (!confirmPassword) {
            setSecurityFeedback(adminPasswordFeedback, "Confirm your new password.");
            if (adminConfirmPassword) {
                adminConfirmPassword.focus();
            }
            return;
        }
        if (newPassword !== confirmPassword) {
            setSecurityFeedback(adminPasswordFeedback, "New passwords do not match.");
            if (adminConfirmPassword) {
                adminConfirmPassword.focus();
            }
            return;
        }

        const payload = {
            current_password: currentPassword,
            new_password: newPassword,
            confirm_password: confirmPassword,
        };

        setButtonLoading(adminPasswordSave, true, "Updating...");
        setSecurityFeedback(adminPasswordFeedback, "");

        const inputs = [adminCurrentPassword, adminNewPassword, adminConfirmPassword].filter(Boolean);
        const toggles = adminPasswordChangeForm ? adminPasswordChangeForm.querySelectorAll("[data-password-toggle-target]") : [];
        inputs.forEach((input) => { input.disabled = true; });
        toggles.forEach((tgl) => { tgl.disabled = true; });

        try {
            const response = await postJson(url, payload);
            if (handleAuthRedirect(response)) {
                return;
            }
            const result = await parseJsonSafe(response);
            if (!result || !result.ok) {
                throw new Error(result && result.message ? result.message : "Unable to update admin password.");
            }

            if (passwordModal) {
                passwordModal.hide();
            }
            showNotification(result.message || "Admin password updated.", "success");
        } catch (error) {
            setSecurityFeedback(
                adminPasswordFeedback,
                error && error.message ? String(error.message) : "Unable to update admin password.",
            );
        } finally {
            inputs.forEach((input) => { input.disabled = false; });
            toggles.forEach((tgl) => { tgl.disabled = false; });
            setButtonLoading(adminPasswordSave, false, "Update password");
        }
    };

    if (adminPasswordSave) {
        adminPasswordSave.addEventListener("click", handlePasswordSubmit);
    }
    if (adminPasswordChangeForm) {
        adminPasswordChangeForm.addEventListener("submit", handlePasswordSubmit);
    }

    // ── 2FA action buttons ────────────────────────────────────────────────
    if (adminTwoFactorAction) {
        adminTwoFactorAction.addEventListener("click", () => {
            if (twoFactorEnabled) {
                resetDisableModal();
                if (disableModal) {
                    disableModal.show();
                }
                return;
            }

            resetSetupModal();
            if (setupModal) {
                setupModal.show();
            }
        });
    }

    if (adminTwoFactorRecoveryAction) {
        adminTwoFactorRecoveryAction.addEventListener("click", () => {
            if (!twoFactorEnabled) {
                return;
            }
            resetRecoveryRegenerateModal();
            if (recoveryRegenerateModal) {
                recoveryRegenerateModal.show();
            }
        });
    }

    // ── 2FA setup flow ────────────────────────────────────────────────────
    if (adminTwoFactorBegin) {
        adminTwoFactorBegin.addEventListener("click", async () => {
            const currentPassword = adminTwoFactorCurrentPassword
                ? adminTwoFactorCurrentPassword.value
                : "";
            if (!currentPassword) {
                setSecurityFeedback(adminTwoFactorSetupFeedback, "Enter your current password.");
                if (adminTwoFactorCurrentPassword) {
                    adminTwoFactorCurrentPassword.focus();
                }
                return;
            }

            setButtonLoading(adminTwoFactorBegin, true, "Checking...");
            setSecurityFeedback(adminTwoFactorSetupFeedback, "");

            const beginInputs = [adminTwoFactorCurrentPassword].filter(Boolean);
            const beginToggles = adminTwoFactorPasswordStep ? adminTwoFactorPasswordStep.querySelectorAll("[data-password-toggle-target]") : [];
            beginInputs.forEach((input) => { input.disabled = true; });
            beginToggles.forEach((tgl) => { tgl.disabled = true; });

            try {
                const response = await postJson(String(securityUrls.adminTwoFactorSetupApi || ""), {
                    current_password: currentPassword,
                });
                if (handleAuthRedirect(response)) {
                    return;
                }
                const result = await parseJsonSafe(response);
                if (!result || !result.ok) {
                    throw new Error(result && result.message ? result.message : "Unable to start authenticator setup.");
                }

                if (adminTwoFactorSetupKey) {
                    adminTwoFactorSetupKey.value = String(result.secret || "");
                }
                const qrCodeDataUrl = String(result.qr_code_data_url || "");
                if (adminTwoFactorQrCode && qrCodeDataUrl.startsWith("data:image/svg+xml;base64,")) {
                    adminTwoFactorQrCode.src = qrCodeDataUrl;
                    if (adminTwoFactorQrPanel) {
                        adminTwoFactorQrPanel.classList.remove("d-none");
                    }
                }
                if (adminTwoFactorPasswordStep) {
                    adminTwoFactorPasswordStep.classList.add("d-none");
                }
                if (adminTwoFactorCodeStep) {
                    adminTwoFactorCodeStep.classList.remove("d-none");
                }
                adminTwoFactorBegin.classList.add("d-none");
                if (adminTwoFactorConfirm) {
                    adminTwoFactorConfirm.classList.remove("d-none");
                }
                setSecurityFeedback(
                    adminTwoFactorSetupFeedback,
                    "Setup key ready. Enter the six-digit code shown in your authenticator app.",
                    true,
                );
                if (adminTwoFactorCode) {
                    adminTwoFactorCode.focus();
                }
            } catch (error) {
                setSecurityFeedback(
                    adminTwoFactorSetupFeedback,
                    error && error.message ? String(error.message) : "Unable to start authenticator setup.",
                );
            } finally {
                beginInputs.forEach((input) => { input.disabled = false; });
                beginToggles.forEach((tgl) => { tgl.disabled = false; });
                setButtonLoading(adminTwoFactorBegin, false, "Continue");
            }
        });
    }

    if (adminTwoFactorConfirm) {
        adminTwoFactorConfirm.addEventListener("click", async () => {
            const code = adminTwoFactorCode ? adminTwoFactorCode.value.trim() : "";
            if (!/^\d{6}$/.test(code)) {
                setSecurityFeedback(adminTwoFactorSetupFeedback, "Enter the six-digit authenticator code.");
                if (adminTwoFactorCode) {
                    adminTwoFactorCode.focus();
                }
                return;
            }

            setButtonLoading(adminTwoFactorConfirm, true, "Enabling...");
            setSecurityFeedback(adminTwoFactorSetupFeedback, "");

            const confirmInputs = [adminTwoFactorCode].filter(Boolean);
            confirmInputs.forEach((input) => { input.disabled = true; });

            try {
                const response = await postJson(String(securityUrls.adminTwoFactorConfirmApi || ""), { code });
                if (handleAuthRedirect(response)) {
                    return;
                }
                const result = await parseJsonSafe(response);
                if (!result || !result.ok) {
                    throw new Error(result && result.message ? result.message : "Unable to enable two-factor authentication.");
                }

                const recoveryCodes = Array.isArray(result.recovery_codes)
                    ? result.recovery_codes
                    : [];
                renderTwoFactorStatus(result.two_factor || {
                    enabled: true,
                    recovery_codes_remaining: recoveryCodes.length,
                });
                showNotification(result.message || "Two-factor authentication enabled.", "success");
                queueRecoveryCodes(recoveryCodes, setupModal);
            } catch (error) {
                setSecurityFeedback(
                    adminTwoFactorSetupFeedback,
                    error && error.message ? String(error.message) : "Unable to enable two-factor authentication.",
                );
            } finally {
                confirmInputs.forEach((input) => { input.disabled = false; });
                setButtonLoading(adminTwoFactorConfirm, false, "Enable 2FA");
            }
        });
    }

    // ── Recovery code regeneration ────────────────────────────────────────
    if (adminRecoveryRegenerateButton) {
        adminRecoveryRegenerateButton.addEventListener("click", async () => {
            const currentPassword = adminRecoveryRegeneratePassword
                ? adminRecoveryRegeneratePassword.value
                : "";
            const code = adminRecoveryRegenerateCode ? adminRecoveryRegenerateCode.value.trim() : "";
            if (!currentPassword) {
                setSecurityFeedback(adminRecoveryRegenerateFeedback, "Enter your current password.");
                if (adminRecoveryRegeneratePassword) {
                    adminRecoveryRegeneratePassword.focus();
                }
                return;
            }
            if (!/^\d{6}$/.test(code)) {
                setSecurityFeedback(adminRecoveryRegenerateFeedback, "Enter the six-digit authenticator code.");
                if (adminRecoveryRegenerateCode) {
                    adminRecoveryRegenerateCode.focus();
                }
                return;
            }

            setButtonLoading(adminRecoveryRegenerateButton, true, "Creating...");
            setSecurityFeedback(adminRecoveryRegenerateFeedback, "");

            const regenInputs = [adminRecoveryRegeneratePassword, adminRecoveryRegenerateCode].filter(Boolean);
            const regenToggles = document.querySelectorAll("#adminRecoveryRegenerateModal [data-password-toggle-target]");
            regenInputs.forEach((input) => { input.disabled = true; });
            regenToggles.forEach((tgl) => { tgl.disabled = true; });

            try {
                const response = await postJson(String(securityUrls.adminTwoFactorRecoveryCodesApi || ""), {
                    current_password: currentPassword,
                    code,
                });
                if (handleAuthRedirect(response)) {
                    return;
                }
                const result = await parseJsonSafe(response);
                if (!result || !result.ok) {
                    throw new Error(result && result.message ? result.message : "Unable to create recovery codes.");
                }

                const recoveryCodes = Array.isArray(result.recovery_codes)
                    ? result.recovery_codes
                    : [];
                renderTwoFactorStatus(result.two_factor || {
                    enabled: true,
                    recovery_codes_remaining: recoveryCodes.length,
                });
                showNotification(result.message || "New recovery codes created.", "success");
                queueRecoveryCodes(recoveryCodes, recoveryRegenerateModal);
            } catch (error) {
                setSecurityFeedback(
                    adminRecoveryRegenerateFeedback,
                    error && error.message ? String(error.message) : "Unable to create recovery codes.",
                );
            } finally {
                regenInputs.forEach((input) => { input.disabled = false; });
                regenToggles.forEach((tgl) => { tgl.disabled = false; });
                setButtonLoading(adminRecoveryRegenerateButton, false, "Create new codes");
            }
        });
    }

    // ── 2FA disable flow ──────────────────────────────────────────────────
    if (adminTwoFactorDisableButton) {
        adminTwoFactorDisableButton.addEventListener("click", async () => {
            const currentPassword = adminTwoFactorDisablePassword
                ? adminTwoFactorDisablePassword.value
                : "";
            const code = adminTwoFactorDisableCode ? adminTwoFactorDisableCode.value.trim() : "";
            if (!currentPassword) {
                setSecurityFeedback(adminTwoFactorDisableFeedback, "Enter your current password.");
                if (adminTwoFactorDisablePassword) {
                    adminTwoFactorDisablePassword.focus();
                }
                return;
            }
            const validVerificationCode = /^(?:\d{6}|[A-F0-9]{4}(?:-?[A-F0-9]{4}){2})$/i.test(
                code.replace(/\s/g, ""),
            );
            if (!validVerificationCode) {
                setSecurityFeedback(adminTwoFactorDisableFeedback, "Enter a valid authenticator or recovery code.");
                if (adminTwoFactorDisableCode) {
                    adminTwoFactorDisableCode.focus();
                }
                return;
            }

            setButtonLoading(adminTwoFactorDisableButton, true, "Disabling...");
            setSecurityFeedback(adminTwoFactorDisableFeedback, "");

            const disableInputs = [adminTwoFactorDisablePassword, adminTwoFactorDisableCode].filter(Boolean);
            const disableToggles = document.querySelectorAll("#adminTwoFactorDisableModal [data-password-toggle-target]");
            disableInputs.forEach((input) => { input.disabled = true; });
            disableToggles.forEach((tgl) => { tgl.disabled = true; });

            try {
                const response = await postJson(String(securityUrls.adminTwoFactorDisableApi || ""), {
                    current_password: currentPassword,
                    code,
                });
                if (handleAuthRedirect(response)) {
                    return;
                }
                const result = await parseJsonSafe(response);
                if (!result || !result.ok) {
                    throw new Error(result && result.message ? result.message : "Unable to disable two-factor authentication.");
                }

                renderTwoFactorStatus(result.two_factor || { enabled: false });
                if (disableModal) {
                    disableModal.hide();
                }
                showNotification(result.message || "Two-factor authentication disabled.", "success");
                await loadSecurityStatus();
            } catch (error) {
                setSecurityFeedback(
                    adminTwoFactorDisableFeedback,
                    error && error.message ? String(error.message) : "Unable to disable two-factor authentication.",
                );
            } finally {
                disableInputs.forEach((input) => { input.disabled = false; });
                disableToggles.forEach((tgl) => { tgl.disabled = false; });
                setButtonLoading(adminTwoFactorDisableButton, false, "Disable 2FA");
            }
        });
    }

    // ── Input masking for code fields ─────────────────────────────────────
    [adminTwoFactorCode, adminRecoveryRegenerateCode].filter(Boolean).forEach((input) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/\D/g, "").slice(0, 6);
        });
    });

    if (adminTwoFactorDisableCode) {
        adminTwoFactorDisableCode.addEventListener("input", () => {
            adminTwoFactorDisableCode.value = adminTwoFactorDisableCode.value
                .replace(/[^A-Fa-f0-9-]/g, "")
                .slice(0, 14)
                .toUpperCase();
        });
    }

    // ── Copy setup key ────────────────────────────────────────────────────
    if (adminTwoFactorCopyKey) {
        adminTwoFactorCopyKey.addEventListener("click", async () => {
            const setupKey = adminTwoFactorSetupKey ? adminTwoFactorSetupKey.value : "";
            if (!setupKey) {
                return;
            }
            try {
                await navigator.clipboard.writeText(setupKey);
                setSecurityFeedback(adminTwoFactorSetupFeedback, "Setup key copied.", true);
            } catch (error) {
                if (adminTwoFactorSetupKey) {
                    adminTwoFactorSetupKey.select();
                }
                setSecurityFeedback(adminTwoFactorSetupFeedback, "Select and copy the setup key.");
            }
        });
    }

    // ── Recovery codes copy & print ───────────────────────────────────────
    if (adminRecoveryCodesCopy) {
        adminRecoveryCodesCopy.addEventListener("click", async () => {
            if (!visibleRecoveryCodes.length) {
                return;
            }
            try {
                await navigator.clipboard.writeText(visibleRecoveryCodes.join("\n"));
                setSecurityFeedback(adminRecoveryCodesFeedback, "Recovery codes copied.", true);
            } catch (error) {
                setSecurityFeedback(adminRecoveryCodesFeedback, "Copy was blocked. Select the codes manually.");
            }
        });
    }

    if (adminRecoveryCodesPrint) {
        adminRecoveryCodesPrint.addEventListener("click", () => {
            if (!printRecoveryCodes()) {
                setSecurityFeedback(adminRecoveryCodesFeedback, "Print window was blocked. Copy the codes instead.");
            }
        });
    }

    if (adminRecoveryCodesDone) {
        adminRecoveryCodesDone.addEventListener("click", () => {
            if (recoveryCodesModal) {
                recoveryCodesModal.hide();
            }
        });
    }

    // ── Modal reset listeners ─────────────────────────────────────────────
    if (adminTwoFactorSetupModalElement) {
        adminTwoFactorSetupModalElement.addEventListener("hidden.bs.modal", () => {
            resetSetupModal();
            if (pendingRecoveryCodes.length) {
                const codesToShow = [...pendingRecoveryCodes];
                pendingRecoveryCodes = [];
                showRecoveryCodes(codesToShow);
            }
        });
    }
    if (adminRecoveryRegenerateModalElement) {
        adminRecoveryRegenerateModalElement.addEventListener("hidden.bs.modal", () => {
            resetRecoveryRegenerateModal();
            if (pendingRecoveryCodes.length) {
                const codesToShow = [...pendingRecoveryCodes];
                pendingRecoveryCodes = [];
                showRecoveryCodes(codesToShow);
            }
        });
    }
    if (adminRecoveryCodesModalElement) {
        adminRecoveryCodesModalElement.addEventListener("hidden.bs.modal", async () => {
            clearVisibleRecoveryCodes();
            await loadSecurityStatus();
        });
    }
    if (adminPasswordChangeModalElement) {
        adminPasswordChangeModalElement.addEventListener("hidden.bs.modal", resetPasswordModal);
    }
    if (adminTwoFactorDisableModalElement) {
        adminTwoFactorDisableModalElement.addEventListener("hidden.bs.modal", resetDisableModal);
    }

    // ── Initialize ────────────────────────────────────────────────────────
    bindPasswordToggles();
    renderTwoFactorStatus({ enabled: false });
    loadSecurityStatus();
})();
