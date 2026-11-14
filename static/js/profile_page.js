(function () {
    const config = window.SafeBooksProfileConfig || {};
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

    const profileDisplayName = document.getElementById("profileDisplayName");
    const profileDisplayEmail = document.getElementById("profileDisplayEmail");
    const profileAvatar = document.getElementById("profileAvatar");
    const profileSections = Array.from(document.querySelectorAll("[data-profile-section]"));
    const profileForm = document.getElementById("profilePersonalDetails");
    const profileFullNameInput = document.getElementById("profileFullName");
    const profileUsernameInput = document.getElementById("profileUsername");
    const profileEmailInput = document.getElementById("profileEmail");
    const profileLocationInput = document.getElementById("profileLocation");
    const profileSaveButton = profileForm ? profileForm.querySelector("[data-profile-save]") : null;
    const profileStatus = profileForm ? profileForm.querySelector("[data-profile-status]") : null;
    const profileData = config.profile || {};
    const profileApiUrl = String(urls.profileApi || "");
    const verifyEmailPage = String(urls.verifyEmailPage || "");

    const scrollTargets = Array.from(document.querySelectorAll("[data-scroll-target]"));
    if (!body || !uiToastContainer) {
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
            throw new Error("Logout is unavailable. Reload this page and try again.");
        }

        return shared.logoutCurrentUser({
            logoutUrl: String(urls.logoutApi || ""),
            loginUrl: String(urls.loginPage || "/login/"),
            authUserKey: AUTH_USER_KEY,
            loginWelcomeKey: LOGIN_WELCOME_KEY,
        });
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

    const getAuthUser = () => {
        if (!AUTH_USER_KEY) {
            return null;
        }

        try {
            const rawValue = window.localStorage.getItem(AUTH_USER_KEY) || "";
            if (!rawValue) {
                return null;
            }

            const parsedValue = JSON.parse(rawValue);
            if (!parsedValue || typeof parsedValue !== "object") {
                return null;
            }

            return parsedValue;
        } catch (error) {
            return null;
        }
    };

    const hydrateProfileIdentity = () => {
        const authUser = getAuthUser();
        const profileName = profileData && profileData.full_name ? String(profileData.full_name).trim() : "";
        const profileEmail = profileData && profileData.email ? String(profileData.email).trim() : "";
        const displayName = profileName
            || (authUser && authUser.full_name ? String(authUser.full_name).trim() : "")
            || String(config.defaultName || "Bookkeeper User");
        const displayEmail = profileEmail
            || (authUser && authUser.email ? String(authUser.email).trim() : "")
            || "name@company.com";
        const initials = resolveInitials(displayName, String(config.defaultInitials || "SB"));

        if (profileDisplayName) {
            profileDisplayName.textContent = displayName;
        }

        if (profileDisplayEmail) {
            profileDisplayEmail.textContent = displayEmail;
        }

        if (profileAvatar) {
            profileAvatar.textContent = initials;
        }
    };

    const markSectionDirty = (section) => {
        if (!section) {
            return;
        }

        const saveButton = section.querySelector("[data-profile-save]");
        const status = section.querySelector("[data-profile-status]");
        if (saveButton) {
            saveButton.disabled = false;
        }
        if (status) {
            status.textContent = "Unsaved changes";
        }
    };

    const resetSectionDirty = (section) => {
        if (!section) {
            return;
        }

        const saveButton = section.querySelector("[data-profile-save]");
        const status = section.querySelector("[data-profile-status]");
        if (saveButton) {
            saveButton.disabled = true;
        }
        if (status) {
            status.textContent = "Saved";
        }
    };

    const setProfileStatus = (message) => {
        if (!profileStatus) {
            return;
        }

        profileStatus.textContent = message;
    };

    const setSaveButtonLoading = (isLoading) => {
        if (!profileSaveButton) {
            return;
        }

        if (!profileSaveButton.dataset.defaultLabel) {
            profileSaveButton.dataset.defaultLabel = profileSaveButton.textContent || "";
        }

        profileSaveButton.disabled = isLoading;
        profileSaveButton.textContent = isLoading
            ? "Saving..."
            : profileSaveButton.dataset.defaultLabel;
    };

    const setInputValue = (inputElement, value) => {
        if (!inputElement) {
            return;
        }

        inputElement.value = String(value || "").trim();
    };

    const updateStoredAuthUser = (nextUser) => {
        if (!AUTH_USER_KEY) {
            return;
        }

        try {
            const currentUser = getAuthUser() || {};
            const mergedUser = {
                ...currentUser,
                ...nextUser,
            };
            window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(mergedUser));
        } catch (error) {
            // Ignore storage failures to keep UI responsive.
        }
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

    const hydrateProfileForm = () => {
        const authUser = getAuthUser() || {};
        const resolveValue = (value, fallback) => {
            const primaryValue = String(value || "").trim();
            if (primaryValue) {
                return primaryValue;
            }
            return String(fallback || "").trim();
        };

        setInputValue(profileFullNameInput, resolveValue(profileData.full_name, authUser.full_name));
        setInputValue(profileUsernameInput, resolveValue(profileData.username, authUser.username));
        setInputValue(profileEmailInput, resolveValue(profileData.email, authUser.email));
        setInputValue(profileLocationInput, resolveValue(profileData.location, authUser.location));

    };

    const handleProfileSave = async (section) => {
        if (!profileApiUrl || !profileForm) {
            showToast("Profile updates are unavailable.", "warning");
            return;
        }

        const payload = {
            full_name: profileFullNameInput ? profileFullNameInput.value.trim() : "",
            username: profileUsernameInput ? profileUsernameInput.value.trim() : "",
            email: profileEmailInput ? profileEmailInput.value.trim() : "",
            location: profileLocationInput ? profileLocationInput.value.trim() : "",
        };

        setSaveButtonLoading(true);
        setProfileStatus("Saving...");

        try {
            const response = await postJson(profileApiUrl, payload);
            if (response.status === 401) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }

            const result = await parseJsonSafe(response);
            if (!response.ok || !result || !result.ok) {
                const message = result && result.message
                    ? String(result.message)
                    : "Unable to update profile.";
                throw new Error(message);
            }

            if (result.user && typeof result.user === "object") {
                updateStoredAuthUser(result.user);
                profileData.full_name = result.user.full_name || "";
                profileData.username = result.user.username || "";
                profileData.email = result.user.email || "";
                profileData.location = result.user.location || "";
            }

            resetSectionDirty(section);
            setProfileStatus("Saved");
            hydrateProfileIdentity();
            hydrateHeaderUser();
            showToast(result.message || "Profile updated.", "success");

            if (result.requires_email_verification && verifyEmailPage) {
                showToast("Verify your new email to continue.", "warning");
                window.setTimeout(() => {
                    window.location.assign(verifyEmailPage);
                }, 800);
            }
        } catch (error) {
            setProfileStatus("Update failed");
            showToast(error && error.message ? String(error.message) : "Unable to update profile.", "danger");
        } finally {
            setSaveButtonLoading(false);
        }
    };

    const bindSectionInputs = () => {
        profileSections.forEach((section) => {
            const inputs = Array.from(section.querySelectorAll("input, select, textarea"));
            inputs.forEach((input) => {
                input.addEventListener("input", () => {
                    markSectionDirty(section);
                });
                input.addEventListener("change", () => {
                    markSectionDirty(section);
                });
            });

            const saveButton = section.querySelector("[data-profile-save]");
            if (!saveButton) {
                return;
            }

            saveButton.addEventListener("click", () => {
                if (section instanceof HTMLFormElement && !section.checkValidity()) {
                    section.reportValidity();
                    return;
                }

                handleProfileSave(section);
            });
        });
    };

    const bindScrollTargets = () => {
        scrollTargets.forEach((button) => {
            button.addEventListener("click", () => {
                const targetSelector = String(button.dataset.scrollTarget || "").trim();
                if (!targetSelector) {
                    return;
                }

                const target = document.querySelector(targetSelector);
                if (!target) {
                    return;
                }

                target.scrollIntoView({ behavior: "smooth", block: "start" });
                if (target.hasAttribute("tabindex")) {
                    target.focus({ preventScroll: true });
                }
            });
        });
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
                } catch (error) {
                    showToast(error.message || "Logout was not confirmed. Please retry.", "danger");
                } finally {
                    dashboardLogoutAction.disabled = false;
                }
            });
        }
    };

    const initializeProfilePage = () => {
        sidebarState.restoreDesktopState();
        hydrateHeaderUser();

        if (shared && typeof shared.applyStoredTheme === "function") {
            shared.applyStoredTheme();
        }

        hydrateProfileIdentity();
        hydrateProfileForm();
        bindSectionInputs();
        bindScrollTargets();
        bindHeaderActions();

        window.addEventListener("resize", () => {
            sidebarState.closeMobileSidebar();
            sidebarState.restoreDesktopState();
        });
    };

    initializeProfilePage();
})();
