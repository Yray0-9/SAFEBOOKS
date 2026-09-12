(() => {
    const config = window.SafeBooksAuditLogConfig || {};
    const urls = config.urls || {};
    const shared = window.SafeBooksShared || null;
    const body = document.body;

    const tableBody = document.getElementById("auditLogTableBody");
    const searchInput = document.getElementById("auditLogSearchInput");
    const sortSelect = document.getElementById("auditLogSortSelect");
    const filterButtons = Array.from(document.querySelectorAll("[data-audit-action]"));
    const countTag = document.getElementById("auditLogCountTag");

    const paginationElement = document.getElementById("auditLogPagination");
    const pageRangeElement = document.getElementById("auditLogPageRange");
    const prevPageBtn = document.getElementById("auditLogPrevPage");
    const nextPageBtn = document.getElementById("auditLogNextPage");
    const pageNumbersElement = document.getElementById("auditLogPageNumbers");

    if (!body || !tableBody || !searchInput || !sortSelect) {
        return;
    }

    const sidebarState = shared && typeof shared.initializeSidebarBehavior === "function"
        ? shared.initializeSidebarBehavior({
            bodyElement: body,
            sidebarToggle: document.getElementById("sidebarToggle"),
            sidebarCollapseToggle: document.getElementById("sidebarCollapseToggle"),
            sidebarCollapseIcon: document.getElementById("sidebarCollapseIcon"),
            sidebarBackdrop: document.getElementById("sidebarBackdrop"),
            storageKey: String(config.sidebarStateKey || "safebooks.sidebarCollapsed"),
            desktopQuery: String(config.desktopQuery || "(min-width: 992px)"),
        })
        : { closeMobileSidebar: () => {}, restoreDesktopState: () => {} };

    const escapeHtml = (value) => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const dateTimeFormatter = new Intl.DateTimeFormat("en-PH", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });

    const formatDateTime = (value) => {
        const parsed = new Date(String(value || ""));
        return Number.isNaN(parsed.getTime()) ? "-" : dateTimeFormatter.format(parsed);
    };

    const actionClass = (actionType) => {
        const action = String(actionType || "");
        if (action.startsWith("record.")) return "records";
        if (action.startsWith("security.") || action.startsWith("settings.")) return "security";
        return "";
    };

    const renderEmpty = (message) => {
        if (paginationElement) {
            paginationElement.hidden = true;
        }
        tableBody.innerHTML = `<tr class="audit-log-empty"><td colspan="4">${escapeHtml(message)}</td></tr>`;
    };

    let currentLogs = [];
    let currentPage = 1;
    const PAGE_SIZE = 10;

    const generatePaginationPages = (currPage, totalPages) => {
        if (totalPages <= 5) {
            const pages = [];
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
            return pages;
        }

        if (currPage <= 3) {
            return [1, 2, 3, "...", totalPages];
        }

        if (currPage >= totalPages - 2) {
            return [1, "...", totalPages - 2, totalPages - 1, totalPages];
        }

        return [1, "...", currPage - 1, currPage, currPage + 1, "...", totalPages];
    };

    const scrollToCardTop = () => {
        const card = document.querySelector(".audit-log-card");
        if (card) {
            card.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

    const renderPagination = (totalCount) => {
        if (!paginationElement) return;

        if (totalCount <= 0) {
            paginationElement.hidden = true;
            return;
        }

        const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        if (totalPages <= 1) {
            paginationElement.hidden = true;
            return;
        }

        paginationElement.hidden = false;

        const startIndex = (currentPage - 1) * PAGE_SIZE + 1;
        const endIndex = Math.min(currentPage * PAGE_SIZE, totalCount);

        if (pageRangeElement) {
            pageRangeElement.textContent = `Showing ${startIndex}-${endIndex} of ${totalCount} ${totalCount === 1 ? "activity" : "activities"}`;
        }

        if (prevPageBtn) {
            prevPageBtn.disabled = currentPage <= 1;
        }

        if (nextPageBtn) {
            nextPageBtn.disabled = currentPage >= totalPages;
        }

        if (pageNumbersElement) {
            pageNumbersElement.innerHTML = "";
            const pages = generatePaginationPages(currentPage, totalPages);

            pages.forEach((p) => {
                if (p === "...") {
                    const ellipsis = document.createElement("span");
                    ellipsis.className = "audit-log-page-ellipsis";
                    ellipsis.textContent = "\u2026";
                    ellipsis.setAttribute("aria-hidden", "true");
                    pageNumbersElement.appendChild(ellipsis);
                } else {
                    const pageBtn = document.createElement("button");
                    pageBtn.type = "button";
                    pageBtn.className = `btn audit-log-page-num${p === currentPage ? " active" : ""}`;
                    pageBtn.textContent = String(p);
                    pageBtn.setAttribute("aria-label", `Page ${p}`);
                    if (p === currentPage) {
                        pageBtn.setAttribute("aria-current", "page");
                    }
                    pageBtn.addEventListener("click", () => {
                        if (currentPage !== p) {
                            currentPage = p;
                            renderPagedTable();
                            scrollToCardTop();
                        }
                    });
                    pageNumbersElement.appendChild(pageBtn);
                }
            });
        }
    };

    const renderPagedTable = () => {
        if (!Array.isArray(currentLogs) || !currentLogs.length) {
            renderEmpty("No activity matches the current filters.");
            return;
        }

        const totalCount = currentLogs.length;
        const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        const startIndex = (currentPage - 1) * PAGE_SIZE;
        const endIndex = startIndex + PAGE_SIZE;
        const pagedLogs = currentLogs.slice(startIndex, endIndex);

        tableBody.innerHTML = pagedLogs.map((log) => `
            <tr>
                <td data-label="Date and time">${escapeHtml(formatDateTime(log.created_at))}</td>
                <td data-label="Activity"><span class="audit-action-badge ${actionClass(log.action_type)}">${escapeHtml(log.action_label || "Activity")}</span></td>
                <td data-label="Client"><span class="audit-log-client">${escapeHtml(log.client_name || "-")}</span></td>
                <td data-label="Details">${escapeHtml(log.message || "-")}</td>
            </tr>
        `).join("");

        renderPagination(totalCount);
    };

    const state = { action: "all", search: "", sort: "newest" };

    const buildUrl = () => {
        const baseUrl = String(urls.auditLogApi || "");
        const params = new URLSearchParams();
        if (state.action !== "all") params.set("action", state.action);
        if (state.search) params.set("search", state.search);
        params.set("sort", state.sort);
        return `${baseUrl}?${params.toString()}`;
    };

    const fetchLogs = async () => {
        if (paginationElement) {
            paginationElement.hidden = true;
        }
        renderEmpty("Loading activity...");
        try {
            const response = await fetch(buildUrl(), {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            if (response.status === 401 || response.status === 403) {
                window.location.assign(String(urls.loginPage || "/login/"));
                return;
            }
            const payload = shared && typeof shared.parseJsonSafe === "function"
                ? await shared.parseJsonSafe(response)
                : await response.json();
            if (!response.ok || !payload || !payload.ok) {
                renderEmpty("Unable to load activity right now.");
                return;
            }
            currentLogs = Array.isArray(payload.logs) ? payload.logs : [];
            renderPagedTable();
            if (countTag) {
                const total = Number(payload.total_count) || 0;
                countTag.textContent = `${total} ${total === 1 ? "activity" : "activities"}`;
            }
        } catch (error) {
            renderEmpty("Unable to load activity right now.");
        }
    };

    const setActiveFilter = (action) => {
        state.action = action;
        filterButtons.forEach((button) => {
            const active = String(button.dataset.auditAction || "all") === action;
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    };

    let searchTimer = null;
    searchInput.addEventListener("input", () => {
        window.clearTimeout(searchTimer);
        searchTimer = window.setTimeout(() => {
            state.search = searchInput.value.trim();
            currentPage = 1;
            fetchLogs();
        }, 300);
    });

    sortSelect.addEventListener("change", () => {
        state.sort = String(sortSelect.value || "newest");
        currentPage = 1;
        fetchLogs();
    });

    filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            setActiveFilter(String(button.dataset.auditAction || "all"));
            currentPage = 1;
            fetchLogs();
        });
    });

    if (prevPageBtn) {
        prevPageBtn.addEventListener("click", () => {
            if (currentPage > 1) {
                currentPage -= 1;
                renderPagedTable();
                scrollToCardTop();
            }
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener("click", () => {
            const totalPages = Math.ceil(currentLogs.length / PAGE_SIZE) || 1;
            if (currentPage < totalPages) {
                currentPage += 1;
                renderPagedTable();
                scrollToCardTop();
            }
        });
    }

    sidebarState.restoreDesktopState();
    if (shared && typeof shared.applyStoredTheme === "function") shared.applyStoredTheme();
    window.addEventListener("resize", () => {
        sidebarState.closeMobileSidebar();
        sidebarState.restoreDesktopState();
    });
    setActiveFilter("all");
    fetchLogs();
})();
