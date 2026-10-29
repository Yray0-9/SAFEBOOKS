(function () {
    const parseJsonSafe = async (response) => {
        try {
            return await response.json();
        } catch (error) {
            return null;
        }
    };

    const getCookieValue = (cookieName) => {
        const source = document.cookie || "";
        const parts = source.split(";");

        for (const part of parts) {
            const trimmed = part.trim();
            if (!trimmed.startsWith(`${cookieName}=`)) {
                continue;
            }
            return decodeURIComponent(trimmed.substring(cookieName.length + 1));
        }

        return "";
    };

    const getStoredAuthUser = (authUserKey) => {
        try {
            const rawValue = window.localStorage.getItem(authUserKey) || "";
            if (!rawValue) {
                return null;
            }

            const parsedValue = JSON.parse(rawValue);
            if (!parsedValue || typeof parsedValue !== "object") {
                return null;
            }

            return parsedValue;
        } catch (storageError) {
            return null;
        }
    };

    const isGenericBookkeeperName = (value) => {
        return String(value || "").trim().toLowerCase() === "bookkeeper user";
    };

    const resolveDisplayName = (user, fallbackName = "Bookkeeper User") => {
        const fullName = user && typeof user.full_name === "string" ? user.full_name.trim() : "";
        if (fullName && !(isGenericBookkeeperName(fullName) && !isGenericBookkeeperName(fallbackName))) {
            return fullName;
        }

        const username = user && typeof user.username === "string" ? user.username.trim() : "";
        if (username) {
            return username;
        }

        const email = user && typeof user.email === "string" ? user.email.trim() : "";
        if (email && email.includes("@")) {
            return email.split("@")[0];
        }

        return fallbackName;
    };

    const resolveInitials = (name, fallbackInitials = "SB") => {
        const nameParts = String(name || "").trim().split(/\s+/).filter(Boolean);

        if (!nameParts.length) {
            return fallbackInitials;
        }

        if (nameParts.length === 1) {
            return nameParts[0].slice(0, 2).toUpperCase();
        }

        return `${nameParts[0][0]}${nameParts[1][0]}`.toUpperCase();
    };

    const hydrateHeaderUser = (options) => {
        const config = options || {};
        const authUserKey = String(config.authUserKey || "").trim();
        const defaultName = String(config.defaultName || "Bookkeeper User");
        const defaultInitials = String(config.defaultInitials || "SB");
        const nameElement = config.nameElement || null;
        const avatarElement = config.avatarElement || null;

        if (!authUserKey) {
            if (nameElement) {
                nameElement.textContent = defaultName;
            }
            if (avatarElement) {
                avatarElement.textContent = defaultInitials;
            }
            return;
        }

        const user = getStoredAuthUser(authUserKey);
        const displayName = resolveDisplayName(user, defaultName);

        if (nameElement) {
            nameElement.textContent = displayName;
        }

        if (avatarElement) {
            avatarElement.textContent = resolveInitials(displayName, defaultInitials);
        }
    };

    const escapeHtml = (value) => {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    const activeToasts = new WeakMap();
    const showToast = (toastContainer, message, variantClass = "", options = {}) => {
        if (!toastContainer) {
            return;
        }

        const text = String(message || "Action completed.");
        const key = JSON.stringify([variantClass, text]);
        let notifications = activeToasts.get(toastContainer);
        if (!notifications) {
            notifications = new Map();
            activeToasts.set(toastContainer, notifications);
        }
        // Repeated validation clicks must not stack the same notice or restart its timer.
        if (notifications.has(key)) return;
        const delay = Number.isFinite(options.delay) ? options.delay : 2800;
        const toastElement = document.createElement("div");
        toastElement.className = `toast safebooks-toast ${variantClass}`.trim();
        toastElement.setAttribute("role", "status");
        toastElement.setAttribute("aria-live", "polite");
        toastElement.setAttribute("aria-atomic", "true");
        toastElement.innerHTML = `<div class="toast-body">${escapeHtml(text)}</div>`;
        notifications.set(key, toastElement);
        const removeToast = () => {
            notifications.delete(key);
            toastElement.remove();
        };
        toastContainer.appendChild(toastElement);

        if (window.bootstrap && window.bootstrap.Toast) {
            toastElement.addEventListener("hidden.bs.toast", () => {
                removeToast();
                toastInstance.dispose();
            });

            const toastInstance = new window.bootstrap.Toast(toastElement, {
                delay,
                autohide: true,
            });
            toastInstance.show();
            return;
        }

        // Bootstrap's CSS hides .toast without .show, even if its JS failed.
        toastElement.classList.add("show");
        window.setTimeout(removeToast, delay);
    };

    const confirmLogout = async (options) => {
        const config = options || {};
        const logoutUrl = String(config.logoutUrl || "").trim();
        let redirectUrl = String(config.loginUrl || "").trim() || "/login/";

        const csrfToken = getCookieValue("csrftoken");
        const headers = {};
        if (csrfToken) {
            headers["X-CSRFToken"] = csrfToken;
        }

        if (!logoutUrl) {
            throw new Error("Logout is unavailable. Reload this page and try again.");
        }
        let response;
        try {
            response = await fetch(logoutUrl, {
                method: "POST",
                headers,
                credentials: "same-origin",
            });
        } catch (requestError) {
            throw new Error("Unable to confirm logout. Check your connection and retry; your session may still be active.");
        }
        const payload = await parseJsonSafe(response);
        const alreadySignedOut = response.status === 401 && payload && payload.ok === false;
        if (!alreadySignedOut && (!response.ok || !payload || payload.ok !== true)) {
            throw new Error("Logout was not confirmed. Reload this page and try again; your session may still be active.");
        }
        if (!alreadySignedOut && typeof payload.redirect_url === "string" && payload.redirect_url.trim()) {
            try {
                const destination = new URL(payload.redirect_url, window.location.href);
                if (destination.origin === window.location.origin) redirectUrl = destination.href;
            } catch (error) {
                // Logout succeeded; a malformed destination cannot undo it.
            }
        }

        try {
            if (config.authUserKey) {
                window.localStorage.removeItem(config.authUserKey);
            }
        } catch (storageError) {
            // Server logout is confirmed even when browser storage is blocked.
        }
        try {
            if (config.loginWelcomeKey) window.sessionStorage.removeItem(config.loginWelcomeKey);
        } catch (storageError) {
            // Independent cleanup: one blocked store must not skip the other.
        }

        return redirectUrl;
    };

    let pendingLogout = null;
    const logoutCurrentUser = (options) => {
        if (!pendingLogout) {
            pendingLogout = confirmLogout(options).finally(() => { pendingLogout = null; });
        }
        return pendingLogout;
    };

    const THEME_STORAGE_KEY = "safebooks.ui.theme";
    const THEME_FOLLOW_KEY = "safebooks.ui.followSystem";
    const VALID_THEMES = new Set(["light", "dark"]);
    let systemThemeMedia = null;
    let systemThemeListener = null;

    const normalizeTheme = (value) => {
        return VALID_THEMES.has(value) ? value : "light";
    };

    const readThemePreference = () => {
        let theme = "light";
        let followSystem = false;
        let storageAvailable = true;

        try {
            const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
            const storedFollow = window.localStorage.getItem(THEME_FOLLOW_KEY);
            theme = normalizeTheme(String(storedTheme || "light"));
            followSystem = storedFollow === "1";
        } catch (error) {
            theme = "light";
            followSystem = false;
            storageAvailable = false;
        }

        return { theme, followSystem, storageAvailable };
    };

    const resolveSystemTheme = () => {
        if (!window.matchMedia) {
            return "light";
        }

        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    };

    const applyThemeClass = (themeValue) => {
        const theme = normalizeTheme(themeValue);
        const pageBody = document.body;
        if (!pageBody) {
            return theme;
        }

        pageBody.classList.remove("theme-light", "theme-dark");
        pageBody.classList.add(`theme-${theme}`);
        return theme;
    };

    const syncSystemThemeListener = (enabled) => {
        if (!window.matchMedia) {
            return;
        }

        if (!systemThemeMedia) {
            systemThemeMedia = window.matchMedia("(prefers-color-scheme: dark)");
        }

        if (enabled && !systemThemeListener) {
            systemThemeListener = (event) => {
                applyThemeClass(event.matches ? "dark" : "light");
            };
            systemThemeMedia.addEventListener("change", systemThemeListener);
        } else if (!enabled && systemThemeListener) {
            systemThemeMedia.removeEventListener("change", systemThemeListener);
            systemThemeListener = null;
        }
    };

    const applyStoredTheme = () => {
        const preference = readThemePreference();
        const resolvedTheme = preference.followSystem ? resolveSystemTheme() : preference.theme;
        applyThemeClass(resolvedTheme);
        syncSystemThemeListener(preference.followSystem);
        return {
            theme: resolvedTheme,
            followSystem: preference.followSystem,
        };
    };

    const setThemePreference = (themeValue, followSystemValue) => {
        const theme = normalizeTheme(themeValue);
        const followSystem = Boolean(followSystemValue);

        let persisted = false;
        try {
            window.localStorage.setItem(THEME_STORAGE_KEY, theme);
            window.localStorage.setItem(THEME_FOLLOW_KEY, followSystem ? "1" : "0");
            persisted = window.localStorage.getItem(THEME_STORAGE_KEY) === theme
                && window.localStorage.getItem(THEME_FOLLOW_KEY) === (followSystem ? "1" : "0");
        } catch (error) {
            // Apply a temporary theme, but never claim this preference was saved.
        }

        const resolvedTheme = followSystem ? resolveSystemTheme() : theme;
        applyThemeClass(resolvedTheme);
        syncSystemThemeListener(followSystem);
        return { theme: resolvedTheme, followSystem, persisted };
    };

    const getThemePreference = () => {
        return readThemePreference();
    };

    const initializeSidebarBehavior = (options = {}) => {
        const bodyElement = options.bodyElement || document.body;
        const sidebarToggle = options.sidebarToggle || null;
        const sidebarCollapseToggle = options.sidebarCollapseToggle || null;
        const sidebarCollapseIcon = options.sidebarCollapseIcon || null;
        const sidebarBackdrop = options.sidebarBackdrop || null;
        const storageKey = String(options.storageKey || "safebooks.sidebarCollapsed").trim() || "safebooks.sidebarCollapsed";
        const desktopQuery = String(options.desktopQuery || "(min-width: 992px)").trim() || "(min-width: 992px)";

        const noopState = {
            closeMobileSidebar: () => {},
            restoreDesktopState: () => {},
            toggleSidebarCollapsed: () => {},
        };

        if (!bodyElement) {
            return noopState;
        }

        const isDesktop = () => window.matchMedia(desktopQuery).matches;

        const closeMobileSidebar = () => {
            bodyElement.classList.remove("sidebar-open");
        };

        const syncSidebarCollapseUI = () => {
            const isCollapsed = bodyElement.classList.contains("sidebar-collapsed");

            if (sidebarCollapseToggle) {
                sidebarCollapseToggle.setAttribute("aria-expanded", String(!isCollapsed));
                sidebarCollapseToggle.setAttribute("aria-label", isCollapsed ? "Expand sidebar" : "Collapse sidebar");
            }

            if (sidebarCollapseIcon) {
                sidebarCollapseIcon.classList.toggle("bi-layout-sidebar-inset", !isCollapsed);
                sidebarCollapseIcon.classList.toggle("bi-layout-sidebar-inset-reverse", isCollapsed);
            }
        };

        const persistCollapsedState = (collapsed) => {
            try {
                window.localStorage.setItem(storageKey, collapsed ? "1" : "0");
            } catch (error) {
                // Ignore storage access issues and keep interaction responsive.
            }
        };

        const getStoredCollapsedState = () => {
            try {
                return window.localStorage.getItem(storageKey) === "1";
            } catch (error) {
                return false;
            }
        };

        const setSidebarCollapsed = (collapsed, persistState = true) => {
            if (!isDesktop()) {
                bodyElement.classList.remove("sidebar-collapsed");
                syncSidebarCollapseUI();
                return;
            }

            bodyElement.classList.toggle("sidebar-collapsed", collapsed);
            syncSidebarCollapseUI();

            if (persistState) {
                persistCollapsedState(collapsed);
            }
        };

        const toggleSidebarCollapsed = () => {
            const shouldCollapse = !bodyElement.classList.contains("sidebar-collapsed");
            setSidebarCollapsed(shouldCollapse, true);
        };

        const restoreDesktopState = () => {
            if (isDesktop()) {
                setSidebarCollapsed(getStoredCollapsedState(), false);
            } else {
                bodyElement.classList.remove("sidebar-collapsed");
                syncSidebarCollapseUI();
            }
        };

        restoreDesktopState();

        if (sidebarToggle) {
            sidebarToggle.addEventListener("click", (event) => {
                event.preventDefault();

                if (isDesktop()) {
                    toggleSidebarCollapsed();
                    return;
                }

                bodyElement.classList.toggle("sidebar-open");
            });
        }

        if (sidebarCollapseToggle) {
            sidebarCollapseToggle.addEventListener("click", (event) => {
                event.preventDefault();
                toggleSidebarCollapsed();
            });
        }

        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener("click", closeMobileSidebar);
        }

        return {
            closeMobileSidebar,
            restoreDesktopState,
            toggleSidebarCollapsed,
        };
    };

    const showConfirmDiscard = () => {
        return new Promise((resolve) => {
            const modalId = "safebooks-confirm-discard-modal";
            let modalEl = document.getElementById(modalId);
            if (modalEl) {
                modalEl.remove();
            }

            modalEl = document.createElement("div");
            modalEl.id = modalId;
            modalEl.className = "modal fade client-manage-modal";
            modalEl.setAttribute("tabindex", "-1");
            modalEl.setAttribute("aria-hidden", "true");
            modalEl.setAttribute("data-bs-backdrop", "static");
            modalEl.setAttribute("data-bs-keyboard", "false");
            modalEl.style.zIndex = "1405";

            modalEl.innerHTML = `
                <div class="modal-dialog modal-dialog-centered" style="max-width: 440px;">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h2 class="modal-title h5">Unsaved Changes</h2>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-0" style="font-size: 0.95rem; color: var(--color-text-muted);">You have unsaved changes. Are you sure you want to discard them?</p>
                        </div>
                        <div class="modal-footer" style="border-top: none; padding: 0.5rem 1rem 1rem; display: flex; gap: 0.75rem; justify-content: flex-end;">
                            <button type="button" class="btn dashboard-action-btn outline" id="confirmDiscardKeepBtn" data-bs-dismiss="modal">Keep Editing</button>
                            <button type="button" class="btn dashboard-action-btn primary" id="confirmDiscardBtn" style="background-color: #dc3545; border-color: #dc3545; color: #fff;">Discard</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modalEl);

            const modalInstance = new window.bootstrap.Modal(modalEl, {
                backdrop: "static",
                keyboard: false
            });

            let resolved = false;

            const handleResolve = (value) => {
                if (resolved) return;
                resolved = true;
                resolve(value);
                modalInstance.hide();
            };

            const discardBtn = modalEl.querySelector("#confirmDiscardBtn");
            const keepBtn = modalEl.querySelector("#confirmDiscardKeepBtn");
            const closeBtn = modalEl.querySelector(".btn-close");

            discardBtn.addEventListener("click", () => handleResolve(true));
            keepBtn.addEventListener("click", () => handleResolve(false));
            closeBtn.addEventListener("click", () => handleResolve(false));

            modalEl.addEventListener("show.bs.modal", () => {
                window.setTimeout(() => {
                    const backdrops = document.querySelectorAll(".modal-backdrop");
                    if (backdrops.length > 1) {
                        const lastBackdrop = backdrops[backdrops.length - 1];
                        lastBackdrop.style.zIndex = "1400";
                    }
                }, 0);
            });

            modalEl.addEventListener("hidden.bs.modal", () => {
                handleResolve(false);
                modalEl.remove();
            });

            modalInstance.show();
        });
    };

    applyStoredTheme();

    window.SafeBooksShared = {
        parseJsonSafe,
        getCookieValue,
        hydrateHeaderUser,
        showToast,
        logoutCurrentUser,
        applyStoredTheme,
        setThemePreference,
        getThemePreference,
        initializeSidebarBehavior,
        showConfirmDiscard,
    };
})();
