(() => {
    const config = window.SafeBooksAdminBookkeepersConfig || {};
    const urls = config.urls || {};
    const shared = window.SafeBooksShared || null;

    const bookkeepersTableBody = document.getElementById("bookkeepersTableBody");
    const bookkeepersSearchInput = document.getElementById("bookkeepersSearchInput");
    const bookkeepersSortSelect = document.getElementById("bookkeepersSortSelect");
    const bookkeepersStatusFilters = Array.from(document.querySelectorAll("[data-bookkeeper-status]"));
    const bookkeepersClientFilters = Array.from(document.querySelectorAll("[data-bookkeeper-clients]"));
    const bookkeepersCountTag = document.getElementById("bookkeepersCountTag");
    const bookkeepersRefreshButton = document.getElementById("bookkeepersRefreshButton");

    const bookkeepersTotalCount = document.getElementById("bookkeepersTotalCount");
    const bookkeepersActiveCount = document.getElementById("bookkeepersActiveCount");
    const bookkeepersDeactivatedCount = document.getElementById("bookkeepersDeactivatedCount");
    const bookkeepersDeactivationRequestCount = document.getElementById("bookkeepersDeactivationRequestCount");
    const bookkeepersApprovedCount = document.getElementById("bookkeepersApprovedCount");
    const bookkeepersDeactivatedSummary = document.getElementById("bookkeepersDeactivatedSummary");
    const bookkeepersRejectedCount = document.getElementById("bookkeepersRejectedCount");

    const bookkeepersPagination = document.getElementById("bookkeepersPagination");
    const bookkeepersPageRange = document.getElementById("bookkeepersPageRange");
    const bookkeepersPageStatus = document.getElementById("bookkeepersPageStatus");
    const bookkeepersPreviousPage = document.getElementById("bookkeepersPreviousPage");
    const bookkeepersNextPage = document.getElementById("bookkeepersNextPage");

    const bookkeepersClientsZeroToFive = document.getElementById("bookkeepersClientsZeroToFive");
    const bookkeepersClientsSixToFifteen = document.getElementById("bookkeepersClientsSixToFifteen");
    const bookkeepersClientsSixteenPlus = document.getElementById("bookkeepersClientsSixteenPlus");

    const bookkeeperActionModal = document.getElementById("bookkeeperActionModal");
    const deactivationRequestModal = document.getElementById("deactivationRequestModal");
    const bookkeeperActionModalLabel = document.getElementById("bookkeeperActionModalLabel");
    const bookkeeperActionModalMessage = document.getElementById("bookkeeperActionModalMessage");
    const bookkeeperActionModalWarning = document.getElementById("bookkeeperActionModalWarning");
    const bookkeeperActionConfirm = document.getElementById("bookkeeperActionConfirm");
    const bookkeeperActionPasswordInput = document.getElementById("bookkeeperActionPasswordInput");
    const bookkeeperActionPasswordToggle = document.getElementById("bookkeeperActionPasswordToggle");
    const bookkeeperActionPasswordFeedback = document.getElementById("bookkeeperActionPasswordFeedback");

    const uiToastContainer = document.getElementById("uiToastContainer");

    if (!bookkeepersTableBody || !bookkeepersSearchInput || !bookkeepersSortSelect) {
        return;
    }

    const updateConfirmDisabledState = () => {
        if (!bookkeeperActionConfirm) {
            return;
        }
        const val = bookkeeperActionPasswordInput ? bookkeeperActionPasswordInput.value.trim() : "";
        bookkeeperActionConfirm.disabled = val.length === 0;
    };

    const setPasswordInvalidState = (isInvalid, message = "") => {
        if (bookkeeperActionPasswordInput) {
            bookkeeperActionPasswordInput.classList.toggle("is-invalid", isInvalid);
        }
        if (bookkeeperActionPasswordFeedback) {
            if (message) {
                bookkeeperActionPasswordFeedback.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${escapeHtml(message)}`;
            } else if (!isInvalid) {
                bookkeeperActionPasswordFeedback.textContent = "Please enter your admin password.";
            }
            bookkeeperActionPasswordFeedback.classList.toggle("is-visible", isInvalid);
            bookkeeperActionPasswordFeedback.style.display = isInvalid ? "block" : "none";
        }
        const wrap = bookkeeperActionModal ? bookkeeperActionModal.querySelector(".auth-password-wrap") : null;
        if (wrap) {
            wrap.classList.remove("animate-shake");
            if (isInvalid) {
                void wrap.offsetWidth;
                wrap.classList.add("animate-shake");
                window.setTimeout(() => wrap.classList.remove("animate-shake"), 450);
            }
        }
    };

    const setModalSubmittingState = (isSubmitting, action = "") => {
        if (bookkeeperActionPasswordInput) {
            bookkeeperActionPasswordInput.disabled = isSubmitting;
        }
        if (bookkeeperActionPasswordToggle) {
            bookkeeperActionPasswordToggle.disabled = isSubmitting;
        }
        if (bookkeeperActionModal) {
            const cancelBtn = bookkeeperActionModal.querySelector('[data-bs-dismiss="modal"]');
            if (cancelBtn) {
                cancelBtn.disabled = isSubmitting;
            }
            const closeBtn = bookkeeperActionModal.querySelector(".btn-close");
            if (closeBtn) {
                closeBtn.disabled = isSubmitting;
            }
        }
        if (bookkeeperActionConfirm) {
            bookkeeperActionConfirm.disabled = isSubmitting;
            if (isSubmitting) {
                let label = "Processing...";
                if (action === "deactivate") label = "Deactivating...";
                else if (action === "reactivate") label = "Reactivating...";
                else if (action === "approve-deactivation-request") label = "Approving...";
                else if (action === "decline-deactivation-request") label = "Declining...";
                else if (action === "delete") label = "Deleting...";
                bookkeeperActionConfirm.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${label}`;
            } else {
                let label = "Confirm";
                if (action === "deactivate") label = "Deactivate";
                else if (action === "reactivate") label = "Reactivate";
                else if (action === "approve-deactivation-request") label = "Approve Request";
                else if (action === "decline-deactivation-request") label = "Decline Request";
                else if (action === "delete") label = "Delete";
                bookkeeperActionConfirm.textContent = label;
                updateConfirmDisabledState();
            }
        }
    };

    const resetPasswordToggle = () => {
        if (bookkeeperActionPasswordInput) {
            bookkeeperActionPasswordInput.type = "password";
        }
        if (bookkeeperActionPasswordToggle) {
            const icon = bookkeeperActionPasswordToggle.querySelector("i");
            if (icon) {
                icon.classList.remove("bi-eye-slash");
                icon.classList.add("bi-eye");
            }
            bookkeeperActionPasswordToggle.setAttribute("aria-label", "Show password");
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

    const showToast = (message, variantClass = "") => {
        if (!shared || typeof shared.showToast !== "function") {
            return;
        }

        shared.showToast(uiToastContainer, message, variantClass, { delay: 2800 });
    };

    const dateFormatter = new Intl.DateTimeFormat("en-PH", {
        year: "numeric",
        month: "short",
        day: "numeric",
    });

    const formatDate = (value) => {
        const parsed = new Date(String(value || ""));
        if (Number.isNaN(parsed.getTime())) {
            return "-";
        }
        return dateFormatter.format(parsed);
    };

    const resolveStatusMeta = (statusValue) => {
        const status = String(statusValue || "").toLowerCase();
        if (status === "approved") {
            return { label: "Approved", className: "approved" };
        }
        if (status === "suspended") {
            return { label: "Deactivated", className: "suspended" };
        }
        if (status === "rejected") {
            return { label: "Rejected", className: "inactive" };
        }
        if (status === "pending") {
            return { label: "Pending", className: "pending" };
        }
        return { label: "Unavailable", className: "inactive" };
    };

    const setCounts = (counts, clientSummary) => {
        const totalValue = Number.isFinite(counts.total) ? counts.total : 0;
        if (bookkeepersTotalCount) {
            bookkeepersTotalCount.textContent = String(totalValue);
        }
        if (bookkeepersActiveCount) {
            bookkeepersActiveCount.textContent = String((counts && counts.active) || 0);
        }
        if (bookkeepersDeactivatedCount) {
            bookkeepersDeactivatedCount.textContent = String((counts && counts.deactivated) || 0);
        }
        if (bookkeepersDeactivationRequestCount) {
            bookkeepersDeactivationRequestCount.textContent = String((counts && counts.deactivation_requests) || 0);
        }
        if (bookkeepersApprovedCount) {
            bookkeepersApprovedCount.textContent = String((counts && counts.active) || 0);
        }
        if (bookkeepersDeactivatedSummary) {
            bookkeepersDeactivatedSummary.textContent = String((counts && counts.deactivated) || 0);
        }
        if (bookkeepersRejectedCount) {
            bookkeepersRejectedCount.textContent = String((counts && counts.rejected) || 0);
        }

        if (bookkeepersClientsZeroToFive) {
            bookkeepersClientsZeroToFive.textContent = String((clientSummary && clientSummary.zero_to_five) || 0);
        }
        if (bookkeepersClientsSixToFifteen) {
            bookkeepersClientsSixToFifteen.textContent = String((clientSummary && clientSummary.six_to_fifteen) || 0);
        }
        if (bookkeepersClientsSixteenPlus) {
            bookkeepersClientsSixteenPlus.textContent = String((clientSummary && clientSummary.sixteen_plus) || 0);
        }
    };

    const renderEmptyRow = (message) => {
        bookkeepersTableBody.innerHTML = `
            <tr class="admin-table-empty">
                <td colspan="7">${escapeHtml(message || "No bookkeepers available yet.")}</td>
            </tr>
        `;
    };

    const buildActionButton = (label, action, bookkeeperId, enabled, extraClass) => {
        const classes = ["admin-action-btn", extraClass];
        if (enabled) {
            classes.push("is-enabled");
        }

        return `
            <button type="button" class="${classes.filter(Boolean).join(" ")}" data-action="${action}" data-bookkeeper-id="${bookkeeperId}" ${enabled ? "" : "disabled"}>
                ${escapeHtml(label)}
            </button>
        `;
    };

    const renderPagination = (pagination) => {
        const totalCount = Number(pagination && pagination.total_count) || 0;
        const page = Number(pagination && pagination.page) || 1;
        const totalPages = Number(pagination && pagination.total_pages) || 1;
        const startIndex = Number(pagination && pagination.start_index) || 0;
        const endIndex = Number(pagination && pagination.end_index) || 0;

        state.page = page;
        if (bookkeepersCountTag) {
            bookkeepersCountTag.textContent = `${totalCount} result${totalCount === 1 ? "" : "s"}`;
        }
        if (bookkeepersPagination) {
            bookkeepersPagination.hidden = totalCount === 0 || totalPages <= 1;
        }
        if (bookkeepersPageRange) {
            bookkeepersPageRange.textContent = totalCount
                ? `Showing ${startIndex}-${endIndex} of ${totalCount}`
                : "No matching bookkeepers";
        }
        if (bookkeepersPageStatus) {
            bookkeepersPageStatus.textContent = `Page ${page} of ${totalPages}`;
        }
        if (bookkeepersPreviousPage) {
            bookkeepersPreviousPage.disabled = !Boolean(pagination && pagination.has_previous);
        }
        if (bookkeepersNextPage) {
            bookkeepersNextPage.disabled = !Boolean(pagination && pagination.has_next);
        }
    };

    const buildRequestActionButton = (label, action, bookkeeperId, requestId, extraClass) => {
        const classes = ["admin-action-btn", extraClass, "is-enabled"];
        return `
            <button type="button" class="${classes.filter(Boolean).join(" ")}" data-action="${action}" data-bookkeeper-id="${bookkeeperId}" data-request-id="${requestId}">
                ${escapeHtml(label)}
            </button>
        `;
    };

    const renderDeactivationRequestMeta = (requestData) => {
        return "";
    };

    const renderBookkeepers = (bookkeepers) => {
        if (!Array.isArray(bookkeepers) || bookkeepers.length === 0) {
            renderEmptyRow("No bookkeepers available yet.");
            return;
        }

        bookkeepersTableBody.innerHTML = bookkeepers
            .map((bookkeeper) => {
                const statusMeta = resolveStatusMeta(bookkeeper.status);
                const clientsCount = Number.isFinite(bookkeeper.client_count)
                    ? bookkeeper.client_count
                    : Number(bookkeeper.client_count || 0);
                const canToggle = bookkeeper.status === "approved" || bookkeeper.status === "suspended";
                const toggleAction = bookkeeper.status === "suspended" ? "reactivate" : "deactivate";
                const toggleLabel = bookkeeper.status === "suspended" ? "Reactivate" : "Deactivate";
                const toggleClass = bookkeeper.status === "suspended" ? "reactivate" : "deactivate";
                const deactivationRequest = bookkeeper.deactivation_request || null;
                const hasPendingRequest = Boolean(deactivationRequest && deactivationRequest.id && bookkeeper.status === "approved");
                const actionButtons = hasPendingRequest
                    ? `
                        ${buildRequestActionButton("Approve", "approve-deactivation-request", bookkeeper.id, deactivationRequest.id, "deactivate")}
                        ${buildRequestActionButton("Decline", "decline-deactivation-request", bookkeeper.id, deactivationRequest.id, "reject")}
                    `
                    : buildActionButton(toggleLabel, toggleAction, bookkeeper.id, canToggle, toggleClass);

                return `
                    <tr data-bookkeeper-id="${bookkeeper.id}">
                        <td>
                            <div class="admin-row-main d-flex align-items-center gap-2 flex-wrap">
                                <span class="fw-bold text-nowrap">${escapeHtml(bookkeeper.full_name || "-")}</span>
                                ${deactivationRequest ? `
                                    <span class="badge bg-warning text-dark is-clickable admin-deactivation-trigger" data-action="view-deactivation-reason" data-bookkeeper-id="${bookkeeper.id}" style="cursor: pointer; font-size: 0.65rem; font-weight: 700; padding: 0.22rem 0.5rem; border-radius: 999px;" title="Click to view deactivation request reason">
                                        <i class="bi bi-chat-right-text-fill me-1"></i>Deactivation requested
                                    </span>
                                ` : ""}
                            </div>
                        </td>
                        <td>${escapeHtml(bookkeeper.email || "-")}</td>
                        <td>${escapeHtml(String(clientsCount))}</td>
                        <td>${escapeHtml(formatDate(bookkeeper.created_at))}</td>
                        <td>${escapeHtml(formatDate(bookkeeper.last_login))}</td>
                        <td><span class="admin-status-chip ${statusMeta.className}">${escapeHtml(statusMeta.label)}</span></td>
                        <td>
                            <div class="admin-table-actions">
                                ${actionButtons}
                            </div>
                        </td>
                    </tr>
                `;
            })
            .join("");
    };

    const buildBookkeepersUrl = () => {
        const baseUrl = String(urls.bookkeepersApi || "");
        if (!baseUrl) {
            return "";
        }

        const searchParams = new URLSearchParams();
        if (state.status && state.status !== "all") {
            searchParams.set("status", state.status);
        }
        if (state.clients) {
            searchParams.set("clients", state.clients);
        }
        if (state.search) {
            searchParams.set("search", state.search);
        }
        if (state.sort) {
            searchParams.set("sort", state.sort);
        }
        searchParams.set("page", String(state.page));
        searchParams.set("page_size", String(state.pageSize));

        return searchParams.toString() ? `${baseUrl}?${searchParams.toString()}` : baseUrl;
    };

    const buildActionUrl = (bookkeeperId, action) => {
        if (action === "decline-deactivation-request") {
            return "";
        }

        const normalizedAction = action === "approve-deactivation-request"
            ? "deactivate"
            : action;
        const baseUrl = String(urls.bookkeepersBaseApi || urls.bookkeepersApi || "");
        if (!baseUrl) {
            return "";
        }

        const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
        return `${normalizedBase}${bookkeeperId}/${normalizedAction}/`;
    };

    const buildRequestDeclineUrl = (requestId) => {
        const baseUrl = String(urls.deactivationRequestsBaseApi || "");
        if (!baseUrl) {
            return "";
        }

        const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
        return `${normalizedBase}${requestId}/decline/`;
    };

    const fetchBookkeepers = async () => {
        const url = buildBookkeepersUrl();
        if (!url) {
            renderEmptyRow("Bookkeepers API is not configured.");
            return;
        }

        renderEmptyRow("Loading bookkeepers...");

        try {
            const response = await fetch(url, {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                credentials: "same-origin",
            });

            if (response.status === 401 || response.status === 403) {
                showToast("Admin session expired. Please log in again.", "warning");
                const loginPage = String(urls.loginPage || "/login/");
                window.location.assign(loginPage);
                return;
            }

            const payload = shared && typeof shared.parseJsonSafe === "function"
                ? await shared.parseJsonSafe(response)
                : await response.json();

            if (!response.ok || !payload || !payload.ok) {
                renderEmptyRow(payload && payload.message ? payload.message : "Unable to load bookkeepers.");
                return;
            }

            bookkeepersCache = Array.isArray(payload.bookkeepers) ? payload.bookkeepers : [];
            renderBookkeepers(bookkeepersCache);
            setCounts(payload.counts || {}, payload.client_summary || {});
            renderPagination(payload.pagination || {});
        } catch (error) {
            renderEmptyRow("Unable to load bookkeepers right now.");
        }
    };

    const runBookkeeperAction = async (bookkeeperId, action, adminPassword, requestId) => {
        const url = action === "decline-deactivation-request"
            ? buildRequestDeclineUrl(requestId)
            : buildActionUrl(bookkeeperId, action);
        if (!url) {
            return { ok: false, message: "Bookkeeper action is unavailable." };
        }

        const csrfToken = shared && typeof shared.getCookieValue === "function"
            ? shared.getCookieValue("csrftoken")
            : "";

        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                    "X-CSRFToken": csrfToken,
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    admin_password: adminPassword,
                    deactivation_request_id: requestId || undefined,
                }),
            });

            const result = shared && typeof shared.parseJsonSafe === "function"
                ? await shared.parseJsonSafe(response)
                : await response.json();

            if (!response.ok || !result || !result.ok) {
                return {
                    ok: false,
                    message: result && result.message ? result.message : "Action failed.",
                    refreshRequired: Boolean(result && result.refresh_required),
                };
            }

            return {
                ok: true,
                message: result.message || "Action completed.",
            };
        } catch (error) {
            return {
                ok: false,
                message: "Unable to complete action right now.",
            };
        }
    };

    const setActiveStatusFilter = (nextStatus) => {
        state.status = nextStatus;
        bookkeepersStatusFilters.forEach((button) => {
            const statusValue = String(button.dataset.bookkeeperStatus || "all");
            const isActive = statusValue === nextStatus;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    };

    const setActiveClientFilter = (nextClients) => {
        state.clients = nextClients;
        bookkeepersClientFilters.forEach((button) => {
            const filterValue = String(button.dataset.bookkeeperClients || "");
            const isActive = filterValue === nextClients && nextClients !== "";
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    };

    let searchDebounceId = null;
    const scheduleSearch = () => {
        if (searchDebounceId) {
            window.clearTimeout(searchDebounceId);
        }
        searchDebounceId = window.setTimeout(() => {
            state.search = bookkeepersSearchInput.value.trim();
            state.page = 1;
            fetchBookkeepers();
        }, 320);
    };

    let actionModalInstance = null;
    if (bookkeeperActionModal && window.bootstrap && window.bootstrap.Modal) {
        actionModalInstance = new window.bootstrap.Modal(bookkeeperActionModal, {
            backdrop: "static",
            keyboard: false,
        });
    }

    let deactivationDetailsModalInstance = null;
    if (deactivationRequestModal && window.bootstrap && window.bootstrap.Modal) {
        deactivationDetailsModalInstance = new window.bootstrap.Modal(deactivationRequestModal);
    }

    const openDeactivationDetailsModal = (bookkeeper) => {
        if (!bookkeeper || !bookkeeper.deactivation_request || !deactivationDetailsModalInstance) {
            return;
        }

        const request = bookkeeper.deactivation_request;
        const nameField = document.getElementById("deactivationRequestModalName");
        const dateField = document.getElementById("deactivationRequestModalDate");
        const reasonField = document.getElementById("deactivationRequestModalReason");

        if (nameField) nameField.textContent = bookkeeper.full_name || "--";
        if (dateField) dateField.textContent = formatDate(request.requested_at);
        if (reasonField) reasonField.textContent = request.reason || "No reason provided.";

        const declineBtn = document.getElementById("deactivationRequestModalDeclineBtn");
        const approveBtn = document.getElementById("deactivationRequestModalApproveBtn");

        if (declineBtn) {
            declineBtn.onclick = () => {
                deactivationDetailsModalInstance.hide();
                openActionModal(bookkeeper, "decline-deactivation-request");
            };
        }

        if (approveBtn) {
            approveBtn.onclick = () => {
                deactivationDetailsModalInstance.hide();
                openActionModal(bookkeeper, "approve-deactivation-request");
            };
        }

        deactivationDetailsModalInstance.show();
    };

    const openActionModal = (bookkeeper, action) => {
        if (!bookkeeper || !actionModalInstance) {
            showToast("Action modal is not available. Refresh the page.", "warning");
            return;
        }

        const name = bookkeeper.full_name || "this bookkeeper";
        pendingAction = {
            id: bookkeeper.id,
            action,
            requestId: bookkeeper.deactivation_request && bookkeeper.deactivation_request.id
                ? bookkeeper.deactivation_request.id
                : null,
        };

        if (bookkeeperActionModalWarning) {
            bookkeeperActionModalWarning.hidden = true;
            bookkeeperActionModalWarning.textContent = "";
        }
        if (bookkeeperActionPasswordInput) {
            bookkeeperActionPasswordInput.value = "";
            bookkeeperActionPasswordInput.disabled = false;
        }
        if (bookkeeperActionPasswordToggle) {
            bookkeeperActionPasswordToggle.disabled = false;
        }
        setPasswordInvalidState(false);
        resetPasswordToggle();
        setModalSubmittingState(false, action);

        // Always keep the confirmation button primary (blue) for consistent styling across actions
        if (bookkeeperActionConfirm) {
            bookkeeperActionConfirm.classList.remove("outline");
            bookkeeperActionConfirm.classList.add("primary");
        }

        if (action === "deactivate" || action === "approve-deactivation-request") {
            const clientCount = Number(bookkeeper.client_count || 0);
            if (bookkeeperActionModalLabel) {
                bookkeeperActionModalLabel.textContent = action === "approve-deactivation-request"
                    ? "Approve deactivation request"
                    : "Deactivate bookkeeper account";
            }
            if (bookkeeperActionModalMessage) {
                bookkeeperActionModalMessage.textContent = action === "approve-deactivation-request"
                    ? `Approve ${name}'s deactivation request? This will remove workspace access until the account is reactivated.`
                    : `Deactivate ${name}? This will remove workspace access until the account is reactivated.`;
            }
            if (bookkeeperActionModalWarning) {
                bookkeeperActionModalWarning.hidden = false;
                bookkeeperActionModalWarning.textContent = clientCount > 0
                    ? `This bookkeeper currently owns ${clientCount} client${clientCount === 1 ? "" : "s"}. Client records will stay saved, but the bookkeeper cannot access them while deactivated.`
                    : "This account will lose access until reactivated.";
            }
            if (bookkeeperActionConfirm) {
                bookkeeperActionConfirm.textContent = action === "approve-deactivation-request"
                    ? "Approve Request"
                    : "Deactivate";
            }
        } else if (action === "decline-deactivation-request") {
            if (bookkeeperActionModalLabel) {
                bookkeeperActionModalLabel.textContent = "Decline deactivation request";
            }
            if (bookkeeperActionModalMessage) {
                bookkeeperActionModalMessage.textContent = `Decline ${name}'s deactivation request? The account will stay active.`;
            }
            if (bookkeeperActionModalWarning) {
                bookkeeperActionModalWarning.hidden = false;
                bookkeeperActionModalWarning.textContent = "The request will be marked reviewed and removed from the pending list.";
            }
            if (bookkeeperActionConfirm) {
                bookkeeperActionConfirm.textContent = "Decline Request";
            }
        } else if (action === "reactivate") {
            if (bookkeeperActionModalLabel) {
                bookkeeperActionModalLabel.textContent = "Reactivate bookkeeper account";
            }
            if (bookkeeperActionModalMessage) {
                bookkeeperActionModalMessage.textContent = `Reactivate ${name}? This will restore workspace access for this account.`;
            }
            if (bookkeeperActionConfirm) {
                bookkeeperActionConfirm.textContent = "Reactivate";
            }
        } else {
            if (bookkeeperActionModalLabel) {
                bookkeeperActionModalLabel.textContent = "Protected account deletion";
            }
            if (bookkeeperActionModalMessage) {
                bookkeeperActionModalMessage.textContent = `Permanently delete ${name}?`;
            }
            if (bookkeeperActionModalWarning) {
                bookkeeperActionModalWarning.hidden = false;
                bookkeeperActionModalWarning.textContent = "Permanent delete is blocked for accounts that still own clients. Use deactivate for normal access control.";
            }
            if (bookkeeperActionConfirm) {
                bookkeeperActionConfirm.textContent = "Delete";
            }
        }

        actionModalInstance.show();
        window.setTimeout(() => {
            if (bookkeeperActionPasswordInput) {
                bookkeeperActionPasswordInput.focus();
            }
        }, 100);
    };

    const state = {
        status: "all",
        clients: "",
        search: "",
        sort: "recent",
        page: 1,
        pageSize: 10,
    };

    let bookkeepersCache = [];
    let pendingAction = null;

    bookkeepersStatusFilters.forEach((button) => {
        button.addEventListener("click", () => {
            const nextStatus = String(button.dataset.bookkeeperStatus || "all");
            setActiveStatusFilter(nextStatus);
            state.page = 1;
            fetchBookkeepers();
        });
    });

    bookkeepersClientFilters.forEach((button) => {
        button.addEventListener("click", () => {
            const filterValue = String(button.dataset.bookkeeperClients || "");
            const nextValue = state.clients === filterValue ? "" : filterValue;
            setActiveClientFilter(nextValue);
            state.page = 1;
            fetchBookkeepers();
        });
    });

    bookkeepersSortSelect.addEventListener("change", () => {
        state.sort = String(bookkeepersSortSelect.value || "recent");
        state.page = 1;
        fetchBookkeepers();
    });

    if (bookkeepersPreviousPage) {
        bookkeepersPreviousPage.addEventListener("click", () => {
            if (state.page <= 1) {
                return;
            }
            state.page -= 1;
            fetchBookkeepers();
        });
    }

    if (bookkeepersNextPage) {
        bookkeepersNextPage.addEventListener("click", () => {
            state.page += 1;
            fetchBookkeepers();
        });
    }

    bookkeepersSearchInput.addEventListener("input", scheduleSearch);

    if (bookkeepersRefreshButton) {
        bookkeepersRefreshButton.addEventListener("click", () => {
            fetchBookkeepers();
        });
    }

    bookkeepersTableBody.addEventListener("click", (event) => {
        const actionButton = event.target.closest("button[data-action]");
        if (actionButton) {
            const action = String(actionButton.dataset.action || "");
            const bookkeeperId = Number(actionButton.dataset.bookkeeperId || 0);
            const selected = bookkeepersCache.find((item) => item.id === bookkeeperId) || null;
            if (!selected) {
                showToast("Unable to locate this bookkeeper.", "warning");
                return;
            }

            openActionModal(selected, action);
            return;
        }

        const deactivationTrigger = event.target.closest(".admin-deactivation-trigger");
        if (deactivationTrigger) {
            const bookkeeperId = Number(deactivationTrigger.dataset.bookkeeperId || 0);
            const selected = bookkeepersCache.find((item) => item.id === bookkeeperId) || null;
            if (selected && selected.deactivation_request) {
                openDeactivationDetailsModal(selected);
            }
        }
    });

    if (bookkeeperActionModal) {
        bookkeeperActionModal.addEventListener("shown.bs.modal", () => {
            if (bookkeeperActionPasswordInput) {
                bookkeeperActionPasswordInput.focus();
                bookkeeperActionPasswordInput.select();
            }
        });

        bookkeeperActionModal.addEventListener("hidden.bs.modal", () => {
            if (bookkeeperActionPasswordInput) {
                bookkeeperActionPasswordInput.value = "";
                bookkeeperActionPasswordInput.disabled = false;
            }
            if (bookkeeperActionPasswordToggle) {
                bookkeeperActionPasswordToggle.disabled = false;
            }
            setPasswordInvalidState(false);
            resetPasswordToggle();
            setModalSubmittingState(false, pendingAction ? pendingAction.action : "");
            pendingAction = null;
        });
    }

    if (bookkeeperActionPasswordToggle) {
        bookkeeperActionPasswordToggle.addEventListener("click", (event) => {
            event.preventDefault();
            if (!bookkeeperActionPasswordInput || bookkeeperActionPasswordToggle.disabled) {
                return;
            }
            const isPassword = bookkeeperActionPasswordInput.type === "password";
            bookkeeperActionPasswordInput.type = isPassword ? "text" : "password";

            const icon = bookkeeperActionPasswordToggle.querySelector("i");
            if (icon) {
                icon.classList.toggle("bi-eye", !isPassword);
                icon.classList.toggle("bi-eye-slash", isPassword);
            }
            bookkeeperActionPasswordToggle.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password"
            );
            bookkeeperActionPasswordInput.focus();
        });
    }

    if (bookkeeperActionPasswordInput) {
        bookkeeperActionPasswordInput.addEventListener("input", () => {
            setPasswordInvalidState(false);
            updateConfirmDisabledState();
        });

        bookkeeperActionPasswordInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                if (bookkeeperActionConfirm && !bookkeeperActionConfirm.disabled) {
                    bookkeeperActionConfirm.click();
                }
            }
        });
    }

    if (bookkeeperActionConfirm) {
        bookkeeperActionConfirm.addEventListener("click", async () => {
            if (!pendingAction) {
                return;
            }

            const { id, action, requestId } = pendingAction;
            const adminPassword = bookkeeperActionPasswordInput
                ? bookkeeperActionPasswordInput.value.trim()
                : "";

            if (!adminPassword) {
                setPasswordInvalidState(true, "Please enter your admin password.");
                if (bookkeeperActionPasswordInput) {
                    bookkeeperActionPasswordInput.focus();
                }
                return;
            }

            setModalSubmittingState(true, action);
            const result = await runBookkeeperAction(id, action, adminPassword, requestId);
            setModalSubmittingState(false, action);

            if (result.ok) {
                pendingAction = null;
                if (actionModalInstance) {
                    actionModalInstance.hide();
                }
                showToast(result.message || "Action completed.", "success");
                await fetchBookkeepers();
            } else {
                if (result.refreshRequired) {
                    if (actionModalInstance) {
                        actionModalInstance.hide();
                    }
                    showToast(result.message || "Action failed.", "warning");
                    await fetchBookkeepers();
                    return;
                }

                // In-modal error (e.g. "Admin password is incorrect.")
                // No toast on top-right: show error message and red highlight directly inside the modal
                setPasswordInvalidState(true, result.message || "Admin password is incorrect.");
                if (bookkeeperActionPasswordInput) {
                    bookkeeperActionPasswordInput.focus();
                    bookkeeperActionPasswordInput.select();
                }
            }
        });
    }

    setActiveStatusFilter("all");
    setActiveClientFilter("");
    fetchBookkeepers();
})();
