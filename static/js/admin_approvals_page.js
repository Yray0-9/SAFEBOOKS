(() => {
    const config = window.SafeBooksAdminApprovalsConfig || {};
    const urls = config.urls || {};
    const shared = window.SafeBooksShared || null;

    const approvalsTableBody = document.getElementById("approvalsTableBody");
    const approvalsSearchInput = document.getElementById("approvalsSearchInput");
    const approvalsSortSelect = document.getElementById("approvalsSortSelect");
    const approvalsStatusFilters = Array.from(document.querySelectorAll("[data-approval-status]"));
    const approvalsCountTag = document.getElementById("approvalsCountTag");
    const approvalsRefreshButton = document.getElementById("approvalsRefreshButton");
    const approvalsPagination = document.getElementById("approvalsPagination");
    const approvalsPageRange = document.getElementById("approvalsPageRange");
    const approvalsPageStatus = document.getElementById("approvalsPageStatus");
    const approvalsPreviousPage = document.getElementById("approvalsPreviousPage");
    const approvalsNextPage = document.getElementById("approvalsNextPage");

    const approvalsPendingCount = document.getElementById("approvalsPendingCount");
    const approvalsApprovedCount = document.getElementById("approvalsApprovedCount");
    const approvalsRejectedCount = document.getElementById("approvalsRejectedCount");
    const approvalsApprovedToday = document.getElementById("approvalsApprovedToday");
    const approvalsRejectedToday = document.getElementById("approvalsRejectedToday");

    const approvalsActionModal = document.getElementById("approvalsActionModal");
    const approvalDetailsModal = document.getElementById("approvalDetailsModal");
    const approvalsActionModalLabel = document.getElementById("approvalsActionModalLabel");
    const approvalsActionModalMessage = document.getElementById("approvalsActionModalMessage");
    const approvalsActionConfirm = document.getElementById("approvalsActionConfirm");
    const approvalsActionReasonWrap = document.getElementById("approvalsActionReasonWrap");
    const approvalsActionReasonInput = document.getElementById("approvalsActionReasonInput");

    const approvalDetailEmpty = document.getElementById("approvalDetailEmpty");
    const approvalDetailPanel = document.getElementById("approvalDetailPanel");
    const approvalDetailInitials = document.getElementById("approvalDetailInitials");
    const approvalDetailName = document.getElementById("approvalDetailName");
    const approvalDetailEmail = document.getElementById("approvalDetailEmail");
    const approvalDetailUsername = document.getElementById("approvalDetailUsername");
    const approvalDetailDate = document.getElementById("approvalDetailDate");
    const approvalDetailStatus = document.getElementById("approvalDetailStatus");
    const approvalDetailVerified = document.getElementById("approvalDetailVerified");
    const approvalDetailGoogle = document.getElementById("approvalDetailGoogle");
    const approvalDetailLastLogin = document.getElementById("approvalDetailLastLogin");
    const approvalDetailApprovedBy = document.getElementById("approvalDetailApprovedBy");
    const approvalDetailReasonRow = document.getElementById("approvalDetailReasonRow");
    const approvalDetailReason = document.getElementById("approvalDetailReason");
    const approvalNotificationPreview = document.getElementById("approvalNotificationPreview");
    const approvalNotificationText = document.getElementById("approvalNotificationText");
    const approvalEmailDeliveryRow = document.getElementById("approvalEmailDeliveryRow");
    const approvalEmailDeliveryStatus = document.getElementById("approvalEmailDeliveryStatus");
    const approvalEmailRetryButton = document.getElementById("approvalEmailRetryButton");
    const proofSummary = document.getElementById("approvalProofSummary");
    const proofDownload = document.getElementById("approvalProofDownload");
    const proofReviewWrap = document.getElementById("approvalProofReviewWrap");
    const proofReviewed = document.getElementById("approvalProofReviewed");

    const uiToastContainer = document.getElementById("uiToastContainer");

    if (!approvalsTableBody || !approvalsSearchInput || !approvalsSortSelect || !approvalsStatusFilters.length) {
        return;
    }

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

    const getInitials = (name, fallback) => {
        const source = String(name || fallback || "").trim();
        if (!source) {
            return "--";
        }

        const parts = source.split(/\s+/).filter(Boolean);
        if (parts.length === 1) {
            return parts[0].slice(0, 2).toUpperCase();
        }
        return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase();
    };

    const setChip = (element, label, className) => {
        if (!element) {
            return;
        }
        element.textContent = label;
        element.className = `admin-status-chip ${className}`;
    };

    const resolveStatusMeta = (statusValue) => {
        const status = String(statusValue || "").toLowerCase();
        if (status === "pending") {
            return { label: "Pending", className: "pending" };
        }
        if (status === "approved") {
            return { label: "Approved", className: "approved" };
        }
        if (status === "rejected") {
            return { label: "Rejected", className: "rejected" };
        }
        if (status === "suspended") {
            return { label: "Suspended", className: "suspended" };
        }
        return { label: "Inactive", className: "inactive" };
    };

    const setDetailState = (approval) => {
        const proof = approval && approval.proof;
        if (proofSummary) proofSummary.textContent = proof
            ? `${proof.document_name} · Submitted ${formatDate(proof.submitted_at)}`
            : approval ? "No proof submitted." : "Select a request.";
        if (proofDownload) {
            proofDownload.hidden = !proof;
            if (proof) proofDownload.href = proof.download_url;
            else proofDownload.removeAttribute("href");
        }
        if (!approval) {
            if (approvalDetailEmpty) {
                approvalDetailEmpty.hidden = false;
            }
            if (approvalDetailPanel) {
                approvalDetailPanel.hidden = true;
            }
            if (approvalNotificationPreview) {
                approvalNotificationPreview.hidden = true;
            }
            if (approvalEmailDeliveryRow) {
                approvalEmailDeliveryRow.hidden = true;
            }
            if (approvalEmailDeliveryStatus) {
                setChip(approvalEmailDeliveryStatus, "Not sent", "inactive");
            }
            if (approvalEmailRetryButton) {
                approvalEmailRetryButton.hidden = true;
            }
            return;
        }

        const statusMeta = resolveStatusMeta(approval.status);
        if (approvalDetailEmpty) {
            approvalDetailEmpty.hidden = true;
        }
        if (approvalDetailPanel) {
            approvalDetailPanel.hidden = false;
        }
        if (approvalDetailInitials) {
            approvalDetailInitials.textContent = getInitials(approval.full_name, approval.email);
        }
        if (approvalDetailName) {
            approvalDetailName.textContent = approval.full_name || "-";
        }
        if (approvalDetailEmail) {
            approvalDetailEmail.textContent = approval.email || "-";
        }
        if (approvalDetailUsername) {
            approvalDetailUsername.textContent = approval.username || "-";
        }
        if (approvalDetailDate) {
            approvalDetailDate.textContent = formatDate(approval.created_at);
        }
        setChip(approvalDetailStatus, statusMeta.label, statusMeta.className);

        if (approvalDetailVerified) {
            const verified = Boolean(approval.email_verified);
            setChip(approvalDetailVerified, verified ? "Email verified" : "Email unverified", verified ? "approved" : "pending");
        }
        if (approvalDetailGoogle) {
            const linked = Boolean(approval.google_linked);
            setChip(approvalDetailGoogle, linked ? "Google linked" : "Manual account", linked ? "approved" : "inactive");
        }
        if (approvalDetailLastLogin) {
            approvalDetailLastLogin.textContent = approval.last_login ? formatDate(approval.last_login) : "Never";
        }
        if (approvalDetailApprovedBy) {
            approvalDetailApprovedBy.textContent = approval.approved_by || "-";
        }
        if (approvalDetailReasonRow && approvalDetailReason) {
            const reason = String(approval.rejection_reason || "").trim();
            approvalDetailReasonRow.hidden = !reason;
            approvalDetailReason.textContent = reason || "-";
        }
        if (approvalNotificationPreview) {
            approvalNotificationPreview.hidden = false;
        }
        if (approvalNotificationText) {
            approvalNotificationText.textContent = approval.notification_preview || "No notification prepared.";
        }

        const accountStatus = String(approval.status || "").toLowerCase();
        const delivery = approval.email_delivery || {};
        const rawDeliveryStatus = String(delivery.status || "").toLowerCase();
        const deliveryStatus = accountStatus === "pending"
            ? "not_sent"
            : (rawDeliveryStatus || (accountStatus === "approved" || accountStatus === "rejected" ? "sent" : "not_sent"));
        if (approvalEmailDeliveryRow) {
            approvalEmailDeliveryRow.hidden = false;
        }
        if (approvalEmailDeliveryStatus) {
            const deliveryMeta = {
                sent: { label: "Sent", className: "approved" },
                skipped: { label: "Skipped", className: "suspended" },
                failed: { label: "Failed", className: "rejected" },
            }[deliveryStatus] || { label: "Not sent", className: "inactive" };
            setChip(approvalEmailDeliveryStatus, deliveryMeta.label, deliveryMeta.className);
            approvalEmailDeliveryStatus.title = delivery.reason || deliveryMeta.label;
        }
        if (approvalEmailRetryButton) {
            approvalEmailRetryButton.hidden = rawDeliveryStatus !== "failed";
            approvalEmailRetryButton.dataset.approvalId = String(approval.id || "");
        }
    };

    const setCounts = (counts, total) => {
        const totalValue = Number.isFinite(total) ? total : 0;

        const approvalsTotalCount = document.getElementById("approvalsTotalCount");
        if (approvalsTotalCount) {
            approvalsTotalCount.textContent = String(totalValue);
        }

        if (approvalsPendingCount) {
            approvalsPendingCount.textContent = String((counts && counts.pending) || 0);
        }
        const summaryPendingCount = document.getElementById("summaryPendingCount");
        if (summaryPendingCount) {
            summaryPendingCount.textContent = String((counts && counts.pending) || 0);
        }

        if (approvalsApprovedCount) {
            approvalsApprovedCount.textContent = String((counts && counts.approved) || 0);
        }
        if (approvalsRejectedCount) {
            approvalsRejectedCount.textContent = String((counts && counts.rejected) || 0);
        }
        if (approvalsApprovedToday) {
            approvalsApprovedToday.textContent = String((counts && counts.approved_today) || 0);
        }
        if (approvalsRejectedToday) {
            approvalsRejectedToday.textContent = String((counts && counts.rejected_today) || 0);
        }
    };

    const renderPagination = (pagination) => {
        const totalCount = Number(pagination && pagination.total_count) || 0;
        const page = Number(pagination && pagination.page) || 1;
        const totalPages = Number(pagination && pagination.total_pages) || 1;
        const startIndex = Number(pagination && pagination.start_index) || 0;
        const endIndex = Number(pagination && pagination.end_index) || 0;

        state.page = page;
        if (approvalsCountTag) {
            approvalsCountTag.textContent = `${totalCount} request${totalCount === 1 ? "" : "s"}`;
        }
        if (approvalsPagination) {
            approvalsPagination.hidden = totalCount === 0 || totalPages <= 1;
        }
        if (approvalsPageRange) {
            approvalsPageRange.textContent = totalCount
                ? `Showing ${startIndex}-${endIndex} of ${totalCount}`
                : "No matching requests";
        }
        if (approvalsPageStatus) {
            approvalsPageStatus.textContent = `Page ${page} of ${totalPages}`;
        }
        if (approvalsPreviousPage) {
            approvalsPreviousPage.disabled = !Boolean(pagination && pagination.has_previous);
        }
        if (approvalsNextPage) {
            approvalsNextPage.disabled = !Boolean(pagination && pagination.has_next);
        }
    };

    const renderEmptyRow = (message) => {
        approvalsTableBody.innerHTML = `
            <tr class="admin-table-empty">
                <td colspan="4">${escapeHtml(message || "No approval requests yet.")}</td>
            </tr>
        `;
    };

    const renderApprovals = (approvals) => {
        if (!Array.isArray(approvals) || approvals.length === 0) {
            renderEmptyRow("No approval requests yet.");
            setDetailState(null);
            return;
        }

        approvalsTableBody.innerHTML = approvals
            .map((approval) => {
                const statusMeta = resolveStatusMeta(approval.status);

                return `
                    <tr data-approval-id="${approval.id}" tabindex="0" style="cursor: pointer;" aria-label="Select approval request for ${escapeHtml(approval.full_name || approval.email || "bookkeeper")}">
                        <td title="${escapeHtml(approval.full_name || "-")}">${escapeHtml(approval.full_name || "-")}</td>
                        <td title="${escapeHtml(approval.email || "-")}">${escapeHtml(approval.email || "-")}</td>
                        <td>${escapeHtml(formatDate(approval.created_at))}</td>
                        <td><span class="admin-status-chip ${statusMeta.className}">${escapeHtml(statusMeta.label)}</span></td>
                    </tr>
                `;
            })
            .join("");
    };

    const getApprovalById = (approvalId) => {
        return approvalsCache.find((item) => item.id === approvalId) || null;
    };

    let actionModalInstance = null;
    if (approvalsActionModal && window.bootstrap && window.bootstrap.Modal) {
        actionModalInstance = new window.bootstrap.Modal(approvalsActionModal, {
            backdrop: "static",
            keyboard: false,
        });
    }

    const openActionModal = (approval, action) => {
        if (!approval || !actionModalInstance) {
            showToast("Action modal is not available. Refresh the page.", "warning");
            return;
        }

        const name = approval.full_name || "this bookkeeper";
        pendingAction = {
            id: approval.id,
            action,
            proofRevision: approval.proof && approval.proof.revision,
        };
        if (proofReviewed) proofReviewed.checked = false;
        if (proofReviewWrap) proofReviewWrap.hidden = action !== "approve";

        if (approvalsActionReasonInput) {
            approvalsActionReasonInput.value = "";
            approvalsActionReasonInput.classList.remove("is-invalid");
        }

        if (action === "approve") {
            if (approvalsActionModalLabel) {
                approvalsActionModalLabel.textContent = "Approve bookkeeper account";
            }
            if (approvalsActionModalMessage) {
                approvalsActionModalMessage.textContent = `Approve ${name}? This will allow the bookkeeper to access the SafeBooks workspace.`;
            }
            if (approvalsActionReasonWrap) {
                approvalsActionReasonWrap.hidden = true;
            }
            if (approvalsActionConfirm) {
                approvalsActionConfirm.textContent = "Approve";
                approvalsActionConfirm.classList.remove("outline");
                approvalsActionConfirm.classList.add("primary");
            }
        } else {
            if (approvalsActionModalLabel) {
                approvalsActionModalLabel.textContent = "Reject bookkeeper account";
            }
            if (approvalsActionModalMessage) {
                approvalsActionModalMessage.textContent = `Reject ${name}? Add a clear reason before confirming this decision.`;
            }
            if (approvalsActionReasonWrap) {
                approvalsActionReasonWrap.hidden = false;
            }
            if (approvalsActionConfirm) {
                approvalsActionConfirm.textContent = "Reject";
                approvalsActionConfirm.classList.remove("primary");
                approvalsActionConfirm.classList.add("outline");
            }
        }

        actionModalInstance.show();
    };

    const buildApprovalsUrl = () => {
        const baseUrl = String(urls.approvalsApi || "");
        if (!baseUrl) {
            return "";
        }

        const searchParams = new URLSearchParams();
        if (state.status !== "all") {
            searchParams.set("status", state.status);
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

    const buildActionUrl = (approvalId, action) => {
        const baseUrl = String(urls.approvalsBaseApi || urls.approvalsApi || "");
        if (!baseUrl) {
            return "";
        }

        const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
        return `${normalizedBase}${approvalId}/${action}/`;
    };

    const fetchApprovals = async () => {
        const url = buildApprovalsUrl();
        if (!url) {
            renderEmptyRow("Approvals API is not configured.");
            return;
        }

        renderEmptyRow("Loading approvals...");

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
                renderEmptyRow(payload && payload.message ? payload.message : "Unable to load approvals.");
                return;
            }

            approvalsCache = Array.isArray(payload.approvals) ? payload.approvals : [];
            renderApprovals(approvalsCache);
            setCounts(payload.counts, payload.total_count);
            renderPagination(payload.pagination || {});

            if (approvalsCache.length > 0 && !selectedApprovalId) {
                selectedApprovalId = approvalsCache[0].id;
                setDetailState(approvalsCache[0]);
            }

            if (selectedApprovalId) {
                const selected = approvalsCache.find((item) => item.id === selectedApprovalId) || null;
                setDetailState(selected);
                if (!selected) {
                    selectedApprovalId = null;
                }
            }
            markSelectedRow();
        } catch (error) {
            renderEmptyRow("Unable to load approvals right now.");
        }
    };

    const runApprovalAction = async (approvalId, action, rejectionReason = "", proofRevision = null) => {
        const url = buildActionUrl(approvalId, action);
        if (!url) {
            showToast("Approval action is unavailable.", "warning");
            return false;
        }

        let payload = {};
        if (action === "reject") {
            payload = { rejection_reason: rejectionReason };
        } else if (action === "approve") {
            payload = { proof_revision: proofRevision, proof_reviewed: Boolean(proofReviewed && proofReviewed.checked) };
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
                body: JSON.stringify(payload),
            });

            const result = shared && typeof shared.parseJsonSafe === "function"
                ? await shared.parseJsonSafe(response)
                : await response.json();

            if (!response.ok || !result || !result.ok) {
                showToast(result && result.message ? result.message : "Action failed.", "warning");
                if (result && result.refresh_required) {
                    await fetchApprovals();
                    return true;
                }
                return false;
            }

            showToast(result.message || "Action completed.", "success");
            await fetchApprovals();
            return true;
        } catch (error) {
            showToast("Unable to complete action right now.", "warning");
            return false;
        }
    };

    const retryDecisionEmail = async (approvalId) => {
        const url = buildActionUrl(approvalId, "retry-email");
        if (!url) {
            showToast("Email retry is unavailable.", "warning");
            return;
        }

        const csrfToken = shared && typeof shared.getCookieValue === "function"
            ? shared.getCookieValue("csrftoken")
            : "";

        if (approvalEmailRetryButton) {
            approvalEmailRetryButton.disabled = true;
        }
        try {
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "X-CSRFToken": csrfToken,
                },
                credentials: "same-origin",
            });
            const result = shared && typeof shared.parseJsonSafe === "function"
                ? await shared.parseJsonSafe(response)
                : await response.json();

            if (!response.ok || !result || !result.ok) {
                showToast(result && result.message ? result.message : "Unable to retry decision email.", "warning");
                return;
            }

            showToast(result.message || "Decision email retry completed.", result.email_delivery && result.email_delivery.status === "sent" ? "success" : "warning");
            await fetchApprovals();
        } catch (error) {
            showToast("Unable to retry decision email right now.", "warning");
        } finally {
            if (approvalEmailRetryButton) {
                approvalEmailRetryButton.disabled = false;
            }
        }
    };

    const markSelectedRow = () => {
        approvalsTableBody.querySelectorAll("tr[data-approval-id]").forEach((row) => {
            const rowId = Number(row.dataset.approvalId || 0);
            row.classList.toggle("is-selected", Boolean(selectedApprovalId && rowId === selectedApprovalId));
        });
    };

    let detailsModalInstance = null;
    if (approvalDetailsModal && window.bootstrap && window.bootstrap.Modal) {
        detailsModalInstance = new window.bootstrap.Modal(approvalDetailsModal);
    }

    const openApprovalDetails = (approval) => {
        if (!approval || !detailsModalInstance) {
            return;
        }

        setDetailState(approval);

        const approveBtn = document.getElementById("approvalDetailApproveBtn");
        const rejectBtn = document.getElementById("approvalDetailRejectBtn");

        if (approveBtn) {
            const canApprove = Boolean(approval.email_verified && approval.proof && (approval.status === "pending" || approval.status === "rejected"));
            approveBtn.disabled = !canApprove;
            approveBtn.onclick = () => {
                detailsModalInstance.hide();
                openActionModal(approval, "approve");
            };
        }

        if (rejectBtn) {
            const canReject = approval.status === "pending";
            rejectBtn.disabled = !canReject;
            rejectBtn.onclick = () => {
                detailsModalInstance.hide();
                openActionModal(approval, "reject");
            };
        }

        detailsModalInstance.show();
    };

    const selectApprovalRow = (approvalId) => {
        const selected = getApprovalById(approvalId);
        if (!selected) {
            return;
        }

        selectedApprovalId = approvalId;
        setDetailState(selected);
        markSelectedRow();
        openApprovalDetails(selected);
    };

    const setActiveFilter = (nextStatus) => {
        state.status = nextStatus;
        approvalsStatusFilters.forEach((button) => {
            const statusValue = String(button.dataset.approvalStatus || "all");
            const isActive = statusValue === nextStatus;
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
            state.search = approvalsSearchInput.value.trim();
            state.page = 1;
            selectedApprovalId = null;
            fetchApprovals();
        }, 320);
    };

    const state = {
        status: "all",
        search: "",
        sort: "newest",
        page: 1,
        pageSize: 10,
    };

    let approvalsCache = [];
    let selectedApprovalId = null;
    let pendingAction = null;

    approvalsStatusFilters.forEach((button) => {
        button.addEventListener("click", () => {
            const nextStatus = String(button.dataset.approvalStatus || "all");
            setActiveFilter(nextStatus);
            state.page = 1;
            selectedApprovalId = null;
            fetchApprovals();
        });
    });

    approvalsSortSelect.addEventListener("change", () => {
        state.sort = String(approvalsSortSelect.value || "newest");
        state.page = 1;
        selectedApprovalId = null;
        fetchApprovals();
    });

    approvalsSearchInput.addEventListener("input", scheduleSearch);

    if (approvalsRefreshButton) {
        approvalsRefreshButton.addEventListener("click", () => {
            fetchApprovals();
        });
    }

    if (approvalsPreviousPage) {
        approvalsPreviousPage.addEventListener("click", () => {
            if (state.page <= 1) {
                return;
            }
            state.page -= 1;
            selectedApprovalId = null;
            fetchApprovals();
        });
    }

    if (approvalsNextPage) {
        approvalsNextPage.addEventListener("click", () => {
            state.page += 1;
            selectedApprovalId = null;
            fetchApprovals();
        });
    }

    approvalsTableBody.addEventListener("click", (event) => {
        const row = event.target.closest("tr[data-approval-id]");
        if (row) {
            const approvalId = Number(row.dataset.approvalId || 0);
            selectApprovalRow(approvalId);
        }
    });

    approvalsTableBody.addEventListener("keydown", (event) => {
        const row = event.target.closest("tr[data-approval-id]");
        if (!row || !["Enter", " "].includes(event.key)) {
            return;
        }

        event.preventDefault();
        const approvalId = Number(row.dataset.approvalId || 0);
        if (approvalId) {
            selectApprovalRow(approvalId);
        }
    });

    if (approvalsActionConfirm) {
        approvalsActionConfirm.addEventListener("click", async () => {
            if (!pendingAction) {
                return;
            }

            const { id, action, proofRevision } = pendingAction;
            if (action === "approve" && (!proofReviewed || !proofReviewed.checked)) {
                showToast("Download and review the proof, then confirm your review.", "warning");
                if (proofReviewed) proofReviewed.focus();
                return;
            }
            const rejectionReason = approvalsActionReasonInput
                ? approvalsActionReasonInput.value.trim()
                : "";

            if (action === "reject" && !rejectionReason) {
                if (approvalsActionReasonInput) {
                    approvalsActionReasonInput.classList.add("is-invalid");
                    approvalsActionReasonInput.focus();
                }
                showToast("Add a rejection reason before confirming.", "warning");
                return;
            }

            approvalsActionConfirm.disabled = true;
            const completed = await runApprovalAction(id, action, rejectionReason, proofRevision);
            approvalsActionConfirm.disabled = false;

            if (completed) {
                pendingAction = null;
            }

            if (completed && actionModalInstance) {
                actionModalInstance.hide();
            }
        });
    }

    if (approvalsActionReasonInput) {
        approvalsActionReasonInput.addEventListener("input", () => {
            approvalsActionReasonInput.classList.remove("is-invalid");
        });
    }

    if (approvalEmailRetryButton) {
        approvalEmailRetryButton.addEventListener("click", () => {
            const approvalId = Number(approvalEmailRetryButton.dataset.approvalId || selectedApprovalId || 0);
            if (approvalId) {
                retryDecisionEmail(approvalId);
            }
        });
    }

    setActiveFilter("all");
    fetchApprovals();
})();
