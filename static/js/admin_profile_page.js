(() => {
    const config = window.SafeBooksAdminProfileConfig || {};
    const urls = config.urls || {};
    const initialProfile = config.profile || {};
    const shared = window.SafeBooksShared || null;

    const adminIdentityForm = document.getElementById("adminIdentity");
    const adminFullNameInput = document.getElementById("adminFullName");
    const adminEmailInput = document.getElementById("adminEmail");
    const adminProfileSave = document.getElementById("adminProfileSave");
    const adminProfileReset = document.getElementById("adminProfileReset");
    const adminProfileStatus = document.getElementById("adminProfileStatus");

    const adminProfileName = document.getElementById("adminProfileName");
    const adminProfileEmail = document.getElementById("adminProfileEmail");
    const adminProfileAvatar = document.getElementById("adminProfileAvatar");
    const adminUserName = document.getElementById("adminUserName");
    const adminUserAvatar = document.getElementById("adminUserAvatar");
    const uiToastContainer = document.getElementById("uiToastContainer");

    const showToast = (message, variantClass = "") => {
        if (!shared || typeof shared.showToast !== "function") {
            return;
        }

        shared.showToast(uiToastContainer, message, variantClass, { delay: 2800 });
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

    const resolveInitials = (name) => {
        const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
        if (!parts.length) {
            return "SA";
        }
        if (parts.length === 1) {
            return parts[0].slice(0, 2).toUpperCase();
        }
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
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
            showToast("Admin session expired. Please log in again.", "warning");
            window.location.assign(String(urls.loginPage || "/login/"));
            return true;
        }
        return false;
    };

    const updateIdentityDisplay = (profile) => {
        const fullName = String(profile && profile.full_name ? profile.full_name : "").trim() || "System Admin";
        const email = String(profile && profile.email ? profile.email : "").trim();
        const initials = resolveInitials(fullName);

        if (adminProfileName) {
            adminProfileName.textContent = fullName;
        }
        if (adminProfileEmail) {
            adminProfileEmail.textContent = email;
        }
        if (adminProfileAvatar) {
            adminProfileAvatar.textContent = initials;
        }
        if (adminUserName) {
            adminUserName.textContent = fullName;
        }
        if (adminUserAvatar) {
            adminUserAvatar.textContent = initials;
        }
    };

    const setProfileStatus = (message) => {
        if (adminProfileStatus) {
            adminProfileStatus.textContent = message;
        }
    };

    let savedProfile = {
        full_name: String(initialProfile.full_name || "").trim(),
        email: String(initialProfile.email || "").trim(),
    };

    const resetProfileForm = () => {
        if (adminFullNameInput) {
            adminFullNameInput.value = savedProfile.full_name;
        }
        if (adminEmailInput) {
            adminEmailInput.value = savedProfile.email;
        }
        setProfileStatus("Saved");
    };

    const loadProfile = async () => {
        const url = String(urls.adminProfileApi || "");
        if (!url) {
            return;
        }

        try {
            const response = await fetch(url, {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                credentials: "same-origin",
            });
            if (handleAuthRedirect(response)) {
                return;
            }
            const payload = await parseJsonSafe(response);
            if (!response.ok || !payload || !payload.ok) {
                return;
            }

            if (payload.profile) {
                savedProfile = {
                    full_name: String(payload.profile.full_name || "").trim(),
                    email: String(payload.profile.email || "").trim(),
                };
                resetProfileForm();
                updateIdentityDisplay(payload.profile);
            }
        } catch (error) {
            // The form keeps its server-rendered values if the refresh request fails.
        }
    };

    if (adminIdentityForm) {
        adminIdentityForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const url = String(urls.adminProfileApi || "");
            if (!url) {
                showToast("Admin profile updates are unavailable.", "warning");
                return;
            }

            const payload = {
                full_name: adminFullNameInput ? adminFullNameInput.value.trim() : "",
                email: adminEmailInput ? adminEmailInput.value.trim() : "",
            };

            setButtonLoading(adminProfileSave, true, "Saving...");
            setProfileStatus("Saving...");

            try {
                const response = await postJson(url, payload);
                if (handleAuthRedirect(response)) {
                    return;
                }
                const result = await parseJsonSafe(response);
                if (!result || !result.ok) {
                    throw new Error(result && result.message ? result.message : "Unable to update admin profile.");
                }

                if (result.profile) {
                    savedProfile = {
                        full_name: String(result.profile.full_name || "").trim(),
                        email: String(result.profile.email || "").trim(),
                    };
                    updateIdentityDisplay(result.profile);
                }
                setProfileStatus("Saved");
                showToast(result.message || "Admin profile updated.", "success");
            } catch (error) {
                setProfileStatus("Update failed");
                showToast(error && error.message ? String(error.message) : "Unable to update admin profile.", "danger");
            } finally {
                setButtonLoading(adminProfileSave, false, "Save profile");
            }
        });
    }

    if (adminProfileReset) {
        adminProfileReset.addEventListener("click", resetProfileForm);
    }

    if (adminFullNameInput) {
        adminFullNameInput.addEventListener("input", () => setProfileStatus("Unsaved changes"));
    }
    if (adminEmailInput) {
        adminEmailInput.addEventListener("input", () => setProfileStatus("Unsaved changes"));
    }

    resetProfileForm();
    loadProfile();
})();
