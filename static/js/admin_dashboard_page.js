(() => {
    const config = window.SafeBooksAdminDashboardConfig || {};
    const urls = config.urls || {};
    const shared = window.SafeBooksShared || null;

    const totalBookkeepers = document.getElementById("adminDashboardTotalBookkeepers");
    const pendingApprovals = document.getElementById("adminDashboardPendingApprovals");
    const activeAccounts = document.getElementById("adminDashboardActiveAccounts");
    const highLoad = document.getElementById("adminDashboardHighLoad");

    const loadTableBody = document.getElementById("adminDashboardLoadTableBody");
    const needsReviewList = document.getElementById("adminDashboardNeedsReviewList");
    const needsReviewCount = document.getElementById("adminDashboardNeedsReviewCount");
    const refreshButton = document.getElementById("adminDashboardRefreshButton");

    const statusPending = document.getElementById("adminDashboardStatusPending");
    const statusApproved = document.getElementById("adminDashboardStatusApproved");
    const statusDeactivated = document.getElementById("adminDashboardStatusDeactivated");
    const statusRejected = document.getElementById("adminDashboardStatusRejected");

    const approvalNew = document.getElementById("adminDashboardApprovalNew");
    const approvalWaiting = document.getElementById("adminDashboardApprovalWaiting");
    const approvalOverdue = document.getElementById("adminDashboardApprovalOverdue");

    const adminDashboardLoadPagination = document.getElementById("adminDashboardLoadPagination");
    const adminDashboardLoadPageRange = document.getElementById("adminDashboardLoadPageRange");
    const adminDashboardLoadPageStatus = document.getElementById("adminDashboardLoadPageStatus");
    const adminDashboardLoadPreviousPage = document.getElementById("adminDashboardLoadPreviousPage");
    const adminDashboardLoadNextPage = document.getElementById("adminDashboardLoadNextPage");

    const state = {
        loadPage: 1,
        isLoadingSnapshot: false,
    };

    const uiToastContainer = document.getElementById("uiToastContainer");

    if (!totalBookkeepers || !pendingApprovals || !activeAccounts || !highLoad || !loadTableBody || !needsReviewList) {
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
        return { label: "Unknown", className: "inactive" };
    };

    const getNumber = (value) => {
        const numberValue = Number(value || 0);
        return Number.isFinite(numberValue) ? numberValue : 0;
    };

    const pluralize = (count, singular, plural) => {
        return `${count} ${count === 1 ? singular : plural || `${singular}s`}`;
    };

    const renderEmptyRow = (message) => {
        loadTableBody.innerHTML = `
            <tr class="admin-table-empty">
                <td colspan="3">${escapeHtml(message || "No load data available yet.")}</td>
            </tr>
        `;
    };

    const renderReviewEmpty = () => {
        needsReviewList.innerHTML = `
            <div class="admin-empty-state admin-review-empty">
                No admin review items right now.
            </div>
        `;
    };

    const buildReviewCard = (options) => {
        const config = options || {};
        const className = String(config.className || "pending");
        const iconClass = String(config.iconClass || "bi-info-circle");
        const title = String(config.title || "Review item");
        const meta = String(config.meta || "");
        const href = String(config.href || "#");
        const actionLabel = String(config.actionLabel || "Review");

        return `
            <a class="admin-review-card ${className}" href="${escapeHtml(href)}">
                <span class="admin-review-icon"><i class="bi ${escapeHtml(iconClass)}"></i></span>
                <span class="admin-review-copy">
                    <strong>${escapeHtml(title)}</strong>
                    <small>${escapeHtml(meta)}</small>
                </span>
                <span class="admin-review-action">${escapeHtml(actionLabel)}</span>
            </a>
        `;
    };

    const renderNeedsReview = (payload) => {
        const review = payload.needs_review || {};
        const pendingItems = Array.isArray(review.pending_approvals) ? review.pending_approvals : [];
        const deactivationRequests = Array.isArray(review.deactivation_requests) ? review.deactivation_requests : [];
        const totalAttention = getNumber(review.total_attention);

        if (needsReviewCount) {
            needsReviewCount.textContent = pluralize(totalAttention, "item");
        }

        const cards = [];

        pendingItems.slice(0, 3).forEach((item) => {
            const waitingDays = getNumber(item.waiting_days);
            const meta = waitingDays > 0
                ? `Waiting ${pluralize(waitingDays, "day")}`
                : "New access request";
            cards.push(buildReviewCard({
                className: waitingDays >= 7 ? "overdue" : "pending",
                iconClass: waitingDays >= 7 ? "bi-exclamation-triangle" : "bi-hourglass-split",
                title: item.full_name || item.email || "Pending bookkeeper",
                meta,
                href: String(urls.approvalsPage || "#"),
                actionLabel: "Open approvals",
            }));
        });

        deactivationRequests.slice(0, 4).forEach((item) => {
            const waitingDays = getNumber(item.waiting_days);
            const clientCount = getNumber(item.client_count);
            cards.push(buildReviewCard({
                className: "pending",
                iconClass: "bi-person-dash",
                title: item.full_name || item.email || "Deactivation request",
                meta: `${waitingDays > 0 ? `Waiting ${pluralize(waitingDays, "day")} - ` : ""}${pluralize(clientCount, "client")} assigned`,
                href: String(urls.bookkeepersPage || "#"),
                actionLabel: "Review request",
            }));
        });

        if (!cards.length) {
            renderReviewEmpty();
            return;
        }

        needsReviewList.innerHTML = cards.join("");
    };

    const renderLoadSnapshot = (items) => {
        if (!Array.isArray(items) || items.length === 0) {
            renderEmptyRow("No load data available yet.");
            return;
        }

        loadTableBody.innerHTML = items
            .map((item) => {
                const statusMeta = resolveStatusMeta(item.status);
                const countValue = getNumber(item.client_count);

                return `
                    <tr>
                        <td>${escapeHtml(item.full_name || "-")}</td>
                        <td><span class="admin-status-chip ${statusMeta.className}">${escapeHtml(statusMeta.label)}</span></td>
                        <td>${escapeHtml(String(countValue))}</td>
                    </tr>
                `;
            })
            .join("");
    };

    const renderLoadPagination = (pagination) => {
        const totalCount = Number(pagination && pagination.total_count) || 0;
        const page = Number(pagination && pagination.page) || 1;
        const totalPages = Number(pagination && pagination.total_pages) || 1;
        const startIndex = Number(pagination && pagination.start_index) || 0;
        const endIndex = Number(pagination && pagination.end_index) || 0;

        state.loadPage = page;

        if (adminDashboardLoadPagination) {
            adminDashboardLoadPagination.hidden = totalCount === 0 || totalPages <= 1;
        }
        if (adminDashboardLoadPageRange) {
            adminDashboardLoadPageRange.textContent = totalCount
                ? `Showing ${startIndex}-${endIndex} of ${totalCount}`
                : "No load data available";
        }
        if (adminDashboardLoadPageStatus) {
            adminDashboardLoadPageStatus.textContent = `Page ${page} of ${totalPages}`;
        }
        if (adminDashboardLoadPreviousPage) {
            adminDashboardLoadPreviousPage.disabled = !Boolean(pagination && pagination.has_previous);
        }
        if (adminDashboardLoadNextPage) {
            adminDashboardLoadNextPage.disabled = !Boolean(pagination && pagination.has_next);
        }
    };

    const setCounts = (payload) => {
        const kpis = payload.kpis || {};
        totalBookkeepers.textContent = String(getNumber(kpis.total_bookkeepers));
        pendingApprovals.textContent = String(getNumber(kpis.pending_approvals));
        activeAccounts.textContent = String(getNumber(kpis.active_accounts));
        highLoad.textContent = String(getNumber(kpis.high_client_load));

        const statusOverview = payload.status_overview || {};
        if (statusPending) {
            statusPending.textContent = String(getNumber(statusOverview.pending));
        }
        if (statusApproved) {
            statusApproved.textContent = String(getNumber(statusOverview.approved));
        }
        if (statusDeactivated) {
            statusDeactivated.textContent = String(getNumber(statusOverview.deactivated));
        }
        if (statusRejected) {
            statusRejected.textContent = String(getNumber(statusOverview.rejected));
        }

        const readiness = payload.approval_readiness || {};
        if (approvalNew) {
            approvalNew.textContent = String(getNumber(readiness.new));
        }
        if (approvalWaiting) {
            approvalWaiting.textContent = String(getNumber(readiness.waiting));
        }
        if (approvalOverdue) {
            approvalOverdue.textContent = String(getNumber(readiness.overdue));
        }
    };

    const buildSummaryUrl = (loadPage = 1) => {
        const rawUrl = String(urls.dashboardSummaryApi || "");
        if (!rawUrl) return "";
        const url = new URL(rawUrl, window.location.origin);
        url.searchParams.set("load_page", String(loadPage || 1));
        return url.toString();
    };

    const fetchDashboardSummary = async (options = {}) => {
        const shouldNotify = Boolean(options.notify);
        const isLoadPageOnly = Boolean(options.loadPageOnly);
        const targetPage = options.page !== undefined ? Number(options.page) : state.loadPage;
        const url = buildSummaryUrl(targetPage);
        if (!url) {
            renderEmptyRow("Dashboard summary API is not configured.");
            return;
        }

        if (isLoadPageOnly) {
            state.isLoadingSnapshot = true;
            if (adminDashboardLoadPreviousPage) adminDashboardLoadPreviousPage.disabled = true;
            if (adminDashboardLoadNextPage) adminDashboardLoadNextPage.disabled = true;
            renderEmptyRow("Loading bookkeeper load...");
        } else {
            renderEmptyRow("Loading summary...");
            needsReviewList.innerHTML = '<div class="admin-empty-state admin-review-empty">Loading admin review items...</div>';
        }

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
                renderEmptyRow(payload && payload.message ? payload.message : "Unable to load dashboard summary.");
                if (adminDashboardLoadPagination) {
                    adminDashboardLoadPagination.hidden = true;
                }
                return;
            }

            if (!isLoadPageOnly) {
                setCounts(payload);
                renderNeedsReview(payload);
            }
            renderLoadSnapshot(payload.load_snapshot || []);
            renderLoadPagination(payload.load_snapshot_pagination || payload.pagination || {});
            if (shouldNotify) {
                showToast("Admin dashboard updated.", "success");
            }
        } catch (error) {
            renderEmptyRow("Unable to load dashboard summary right now.");
            if (!isLoadPageOnly) {
                renderReviewEmpty();
            }
            if (adminDashboardLoadPagination) {
                adminDashboardLoadPagination.hidden = true;
            }
        } finally {
            state.isLoadingSnapshot = false;
        }
    };

    if (adminDashboardLoadPreviousPage) {
        adminDashboardLoadPreviousPage.addEventListener("click", () => {
            if (state.loadPage <= 1 || state.isLoadingSnapshot) {
                return;
            }
            fetchDashboardSummary({ loadPageOnly: true, page: state.loadPage - 1 });
        });
    }

    if (adminDashboardLoadNextPage) {
        adminDashboardLoadNextPage.addEventListener("click", () => {
            if (state.isLoadingSnapshot) {
                return;
            }
            fetchDashboardSummary({ loadPageOnly: true, page: state.loadPage + 1 });
        });
    }

    if (refreshButton) {
        refreshButton.addEventListener("click", () => {
            fetchDashboardSummary({ notify: true });
        });
    }

    fetchDashboardSummary();
})();
