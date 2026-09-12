with open("templates/base/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix header
header_target_start = """{% extends 'base/bookkeeper_base.html' %}
{% load static %}"""

header_new = """{% extends 'base/bookkeeper_base.html' %}
{% load static %}

{% block page_title %}Dashboard{% endblock %}
{% block page_heading %}Dashboard{% endblock %}
{% block page_subtitle %}
<p class="dashboard-page-subtitle">Bookkeeper workspace for client records and follow-ups</p>
{% endblock %}
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/clients.css' %}?v=1.0">
<link rel="stylesheet" href="{% static 'css/dashboard.css' %}?v=1.0">
{% endblock %}
{% block topbar_meta %}
<div class="dashboard-utility-strip" aria-label="Dashboard context">
    <span class="dashboard-utility-item"><i class="bi bi-calendar3"></i> Period: <strong id="dashboardCurrentPeriod">Loading...</strong></span>
    <span class="dashboard-utility-item"><i class="bi bi-clock"></i> Updated: <strong id="dashboardLastUpdated">Loading...</strong></span>
</div>
{% endblock %}"""

if "</div>\n{% endblock %}\n\n{% block skeleton %}" in content[:150]:
    # Fix the missing header lines
    split_idx = content.find("{% block skeleton %}")
    content = header_new + "\n\n" + content[split_idx:]
    print("Fixed header block!")

# 2. Add client work queue pagination HTML
queue_table_target = """                <div class="table-responsive" id="clientTableWrap">
                    <table class="table table-hover align-middle dashboard-table mb-0" id="clientTable">
                        <thead>
                            <tr>
                                <th class="client-name-cell">Client Name</th>
                                <th class="client-tin-cell">TIN</th>
                                <th>Last Entry Date</th>
                                <th>Last Period</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="clientTableBody"></tbody>
                    </table>
                </div>"""

queue_pagination_html = """                <div class="table-responsive" id="clientTableWrap">
                    <table class="table table-hover align-middle dashboard-table mb-0" id="clientTable">
                        <thead>
                            <tr>
                                <th class="client-name-cell">Client Name</th>
                                <th class="client-tin-cell">TIN</th>
                                <th>Last Entry Date</th>
                                <th>Last Period</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="clientTableBody"></tbody>
                    </table>
                </div>

                <nav class="clients-pagination" id="clientWorkQueuePagination" aria-label="Client work queue pagination" hidden>
                    <span class="clients-pagination-range" id="clientWorkQueuePageRange">Showing 1-10 of 0 Clients</span>
                    <div class="clients-pagination-controls">
                        <button type="button" class="btn clients-page-button" id="clientWorkQueuePrevPage" aria-label="Previous page">
                            <i class="bi bi-chevron-left" aria-hidden="true"></i>
                            <span>Previous</span>
                        </button>
                        <div class="clients-page-numbers" id="clientWorkQueuePageNumbers"></div>
                        <button type="button" class="btn clients-page-button" id="clientWorkQueueNextPage" aria-label="Next page">
                            <span>Next</span>
                            <i class="bi bi-chevron-right" aria-hidden="true"></i>
                        </button>
                    </div>
                </nav>"""

if queue_table_target in content:
    content = content.replace(queue_table_target, queue_pagination_html, 1)
    print("Added Client Work Queue pagination HTML!")
else:
    print("Queue table target not found directly!")

# 3. Add Recent Entries pagination HTML
recent_table_target = """                <div class="table-responsive" id="recentEntriesWrap">
                    <table class="table table-hover align-middle dashboard-table mb-0" id="recentEntriesTable">
                        <thead>
                            <tr>
                                <th>Client Name</th>
                                <th>Entry Date</th>
                                <th>Total Amount</th>
                            </tr>
                        </thead>
                        <tbody id="recentEntriesBody"></tbody>
                    </table>
                </div>"""

recent_pagination_html = """                <div class="table-responsive" id="recentEntriesWrap">
                    <table class="table table-hover align-middle dashboard-table mb-0" id="recentEntriesTable">
                        <thead>
                            <tr>
                                <th>Client Name</th>
                                <th>Entry Date</th>
                                <th>Total Amount</th>
                            </tr>
                        </thead>
                        <tbody id="recentEntriesBody"></tbody>
                    </table>
                </div>

                <nav class="clients-pagination" id="recentEntriesPagination" aria-label="Recent entries pagination" hidden>
                    <span class="clients-pagination-range" id="recentEntriesPageRange">Showing 1-5 of 0 Entries</span>
                    <div class="clients-pagination-controls">
                        <button type="button" class="btn clients-page-button" id="recentEntriesPrevPage" aria-label="Previous page">
                            <i class="bi bi-chevron-left" aria-hidden="true"></i>
                            <span>Previous</span>
                        </button>
                        <div class="clients-page-numbers" id="recentEntriesPageNumbers"></div>
                        <button type="button" class="btn clients-page-button" id="recentEntriesNextPage" aria-label="Next page">
                            <span>Next</span>
                            <i class="bi bi-chevron-right" aria-hidden="true"></i>
                        </button>
                    </div>
                </nav>"""

if recent_table_target in content:
    content = content.replace(recent_table_target, recent_pagination_html, 1)
    print("Added Recent Entries pagination HTML!")
else:
    print("Recent table target not found directly!")

# 4. Add DOM variables in JS
dom_target = """        const clientActivityEmpty = document.getElementById("clientActivityEmpty");



        const recentEntriesWrap = document.getElementById("recentEntriesWrap");
        const recentEntriesBody = document.getElementById("recentEntriesBody");
        const recentEntriesEmpty = document.getElementById("recentEntriesEmpty");
        const recentEntriesCountTag = document.getElementById("recentEntriesCountTag");"""

dom_replacement = """        const clientActivityEmpty = document.getElementById("clientActivityEmpty");
        const clientWorkQueuePagination = document.getElementById("clientWorkQueuePagination");
        const clientWorkQueuePageRange = document.getElementById("clientWorkQueuePageRange");
        const clientWorkQueuePrevPage = document.getElementById("clientWorkQueuePrevPage");
        const clientWorkQueueNextPage = document.getElementById("clientWorkQueueNextPage");
        const clientWorkQueuePageNumbers = document.getElementById("clientWorkQueuePageNumbers");
        let currentClientWorkQueuePage = 1;
        const CLIENT_WORK_QUEUE_PAGE_SIZE = 10;

        const recentEntriesWrap = document.getElementById("recentEntriesWrap");
        const recentEntriesBody = document.getElementById("recentEntriesBody");
        const recentEntriesEmpty = document.getElementById("recentEntriesEmpty");
        const recentEntriesCountTag = document.getElementById("recentEntriesCountTag");
        const recentEntriesPagination = document.getElementById("recentEntriesPagination");
        const recentEntriesPageRange = document.getElementById("recentEntriesPageRange");
        const recentEntriesPrevPage = document.getElementById("recentEntriesPrevPage");
        const recentEntriesNextPage = document.getElementById("recentEntriesNextPage");
        const recentEntriesPageNumbers = document.getElementById("recentEntriesPageNumbers");
        let currentRecentEntriesPage = 1;
        const RECENT_ENTRIES_PAGE_SIZE = 5;"""

if dom_target in content:
    content = content.replace(dom_target, dom_replacement, 1)
    print("Updated DOM variables in JS!")
else:
    print("DOM target not found directly!")

# 5. Add pagination helper functions and updated table renderers
js_render_target = """        const renderClientTableRows = (rows) => {
            if (!clientTableBody) {
                return;
            }

            clientTableBody.innerHTML = rows
                .map((row) => {
                    const statusMeta = STATUS_META[row.status] || STATUS_META["needs-attention"];
                    const rowClientId = Number.isFinite(row.clientId) ? row.clientId : "";
                    const tinRaw = row.tinRaw || normalizeDigits(row.tin);
                    const tinDisplay = formatTin(tinRaw) || row.tin;

                    let deadlineBadge = "";
                    if (row.daysRemaining !== null) {
                        if (row.deadlineCompleted) {
                            deadlineBadge = `<span class="badge bg-success dashboard-status-extra"><i class="bi bi-check-circle-fill me-1"></i>Completed</span>`;
                        } else {
                            const diffDays = row.daysRemaining;
                            if (diffDays < 0) {
                                deadlineBadge = `<span class="badge bg-danger dashboard-status-extra"><i class="bi bi-exclamation-octagon-fill me-1"></i>Overdue (${Math.abs(diffDays)}d)</span>`;
                            } else if (diffDays <= 5) {
                                deadlineBadge = `<span class="badge bg-warning text-dark dashboard-status-extra"><i class="bi bi-clock-fill me-1"></i>${diffDays}d left</span>`;
                            } else {
                                deadlineBadge = `<span class="badge bg-secondary dashboard-status-extra"><i class="bi bi-calendar-event me-1"></i>Deadline: ${row.deadlineDate}</span>`;
                            }
                        }
                    }

                    return `
                        <tr class="dashboard-client-row" data-client-id="${escapeHtml(String(rowClientId))}" data-client-name="${escapeHtml(row.clientName)}" data-tin="${escapeHtml(tinDisplay)}" data-tin-raw="${escapeHtml(tinRaw)}" data-trade="${escapeHtml(row.tradeName)}" data-remarks="${escapeHtml(row.remarks)}" tabindex="0" role="button" aria-label="View details for ${escapeHtml(row.clientName)}">
                            <td class="client-name-cell">${escapeHtml(row.clientName)}</td>
                            <td class="client-tin-cell">${escapeHtml(tinDisplay)}</td>
                            <td>${escapeHtml(formatEntryDate(row.lastEntryDate))}</td>
                            <td>${escapeHtml(row.currentPeriod)}</td>
                            <td>
                                <span class="status-badge ${statusMeta.badgeClass}">${statusMeta.label}</span>
                                ${deadlineBadge}
                            </td>
                        </tr>
                    `;
                })
                .join("");

            if (clientTableBody) {
                clientTableBody.classList.add("is-filtering");
                window.clearTimeout(filterTransitionTimer);
                filterTransitionTimer = window.setTimeout(() => {
                    clientTableBody.classList.remove("is-filtering");
                }, 170);
            }

            const hasRows = rows.length > 0;
            if (clientTableWrap) {
                clientTableWrap.hidden = !hasRows;
            }
            if (clientActivityEmpty) {
                clientActivityEmpty.hidden = hasRows;
            }
        };

        const sortClientActivity = (rows, sortBy) => {
            const safeRows = Array.isArray(rows) ? [...rows] : [];
            if (sortBy === "name-asc") {
                safeRows.sort((a, b) => normalize(a.clientName).localeCompare(normalize(b.clientName)));
            } else if (sortBy === "name-desc") {
                safeRows.sort((a, b) => normalize(b.clientName).localeCompare(normalize(a.clientName)));
            } else if (sortBy === "oldest") {
                safeRows.sort((a, b) => {
                    const aId = Number(a.clientId || 0);
                    const bId = Number(b.clientId || 0);
                    return aId - bId;
                });
            } else if (sortBy === "recent-activity") {
                safeRows.sort((a, b) => {
                    const aActivityTime = toTimestamp(a && (a.recentActivityAt || a.lastEntryDate));
                    const bActivityTime = toTimestamp(b && (b.recentActivityAt || b.lastEntryDate));
                    if (aActivityTime !== bActivityTime) {
                        return bActivityTime - aActivityTime;
                    }

                    const aId = Number(a.clientId || 0);
                    const bId = Number(b.clientId || 0);
                    return bId - aId;
                });
            } else {
                // "newest"
                safeRows.sort((a, b) => {
                    const aId = Number(a.clientId || 0);
                    const bId = Number(b.clientId || 0);
                    return bId - aId;
                });
            }
            return safeRows;
        };

        const applyClientFilters = () => {
            const query = normalize(clientTableSearch ? clientTableSearch.value : "");
            const queryDigits = normalizeDigits(query);
            const statusFilter = normalize(getActiveClientFilter());
            const sortBy = clientSortSelect ? clientSortSelect.value : "recent-activity";

            let filteredRows = CLIENT_ACTIVITY_DATA.filter((row) => {
                const tinDigits = normalizeDigits(row.tinRaw || row.tin);
                const matchesTin = queryDigits ? tinDigits.includes(queryDigits) : false;
                const matchesQuery = !query || normalize(row.clientName).includes(query) || matchesTin;
                const matchesStatus = statusFilter === "all" || normalize(row.status) === statusFilter;
                return matchesQuery && matchesStatus;
            });

            filteredRows = sortClientActivity(filteredRows, sortBy);

            renderClientTableRows(filteredRows);
            updateClientFilterSummary(statusFilter, filteredRows.length);
        };

        const renderRecentEntries = () => {
            if (!recentEntriesBody) {
                return;
            }

            const entriesToShow = [...RECENT_ENTRIES_DATA]
                .sort((a, b) => normalize(b.entryDate).localeCompare(normalize(a.entryDate)))
                .slice(0, 5);

            recentEntriesBody.innerHTML = entriesToShow
                .map((entry) => {
                    return `
                        <tr>
                            <td>${escapeHtml(entry.clientName)}</td>
                            <td>${escapeHtml(formatEntryDate(entry.entryDate))}</td>
                            <td>${escapeHtml(formatCurrency(entry.totalAmount))}</td>
                        </tr>
                    `;
                })
                .join("");

            if (recentEntriesCountTag) {
                recentEntriesCountTag.textContent = `${entriesToShow.length} ${entriesToShow.length === 1 ? "Entry" : "Entries"}`;
            }

            const hasEntries = entriesToShow.length > 0;
            if (recentEntriesWrap) {
                recentEntriesWrap.hidden = !hasEntries;
            }
            if (recentEntriesEmpty) {
                recentEntriesEmpty.hidden = hasEntries;
            }
        };"""

js_render_replacement = """        const generatePaginationPages = (currPage, totalPages) => {
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

        const scrollToClientWorkQueueTop = () => {
            const card = document.querySelector("#clientTableWrap") ? document.querySelector("#clientTableWrap").closest(".dashboard-card") : null;
            if (card) {
                card.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        };

        const scrollToRecentEntriesTop = () => {
            const card = document.querySelector("#recentEntriesWrap") ? document.querySelector("#recentEntriesWrap").closest(".dashboard-card") : null;
            if (card) {
                card.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        };

        const renderClientWorkQueuePagination = (totalCount) => {
            if (!clientWorkQueuePagination) {
                return;
            }

            if (totalCount <= 0) {
                clientWorkQueuePagination.hidden = true;
                return;
            }

            const totalPages = Math.ceil(totalCount / CLIENT_WORK_QUEUE_PAGE_SIZE) || 1;
            if (currentClientWorkQueuePage > totalPages) {
                currentClientWorkQueuePage = totalPages;
            }
            if (currentClientWorkQueuePage < 1) {
                currentClientWorkQueuePage = 1;
            }

            if (totalPages <= 1) {
                clientWorkQueuePagination.hidden = true;
                return;
            }

            clientWorkQueuePagination.hidden = false;

            const startIndex = (currentClientWorkQueuePage - 1) * CLIENT_WORK_QUEUE_PAGE_SIZE + 1;
            const endIndex = Math.min(currentClientWorkQueuePage * CLIENT_WORK_QUEUE_PAGE_SIZE, totalCount);

            if (clientWorkQueuePageRange) {
                clientWorkQueuePageRange.textContent = `Showing ${startIndex}-${endIndex} of ${totalCount} ${totalCount === 1 ? "Client" : "Clients"}`;
            }

            if (clientWorkQueuePrevPage) {
                clientWorkQueuePrevPage.disabled = currentClientWorkQueuePage <= 1;
            }

            if (clientWorkQueueNextPage) {
                clientWorkQueueNextPage.disabled = currentClientWorkQueuePage >= totalPages;
            }

            if (clientWorkQueuePageNumbers) {
                clientWorkQueuePageNumbers.innerHTML = "";
                const pages = generatePaginationPages(currentClientWorkQueuePage, totalPages);

                pages.forEach((p) => {
                    if (p === "...") {
                        const ellipsis = document.createElement("span");
                        ellipsis.className = "clients-page-ellipsis";
                        ellipsis.textContent = "\\u2026";
                        ellipsis.setAttribute("aria-hidden", "true");
                        clientWorkQueuePageNumbers.appendChild(ellipsis);
                    } else {
                        const pageBtn = document.createElement("button");
                        pageBtn.type = "button";
                        pageBtn.className = `btn clients-page-num${p === currentClientWorkQueuePage ? " active" : ""}`;
                        pageBtn.textContent = String(p);
                        pageBtn.setAttribute("aria-label", `Page ${p}`);
                        if (p === currentClientWorkQueuePage) {
                            pageBtn.setAttribute("aria-current", "page");
                        }
                        pageBtn.addEventListener("click", () => {
                            if (currentClientWorkQueuePage !== p) {
                                currentClientWorkQueuePage = p;
                                applyClientFilters(false);
                                scrollToClientWorkQueueTop();
                            }
                        });
                        clientWorkQueuePageNumbers.appendChild(pageBtn);
                    }
                });
            }
        };

        const renderRecentEntriesPagination = (totalCount) => {
            if (!recentEntriesPagination) {
                return;
            }

            if (totalCount <= 0) {
                recentEntriesPagination.hidden = true;
                return;
            }

            const totalPages = Math.ceil(totalCount / RECENT_ENTRIES_PAGE_SIZE) || 1;
            if (currentRecentEntriesPage > totalPages) {
                currentRecentEntriesPage = totalPages;
            }
            if (currentRecentEntriesPage < 1) {
                currentRecentEntriesPage = 1;
            }

            if (totalPages <= 1) {
                recentEntriesPagination.hidden = true;
                return;
            }

            recentEntriesPagination.hidden = false;

            const startIndex = (currentRecentEntriesPage - 1) * RECENT_ENTRIES_PAGE_SIZE + 1;
            const endIndex = Math.min(currentRecentEntriesPage * RECENT_ENTRIES_PAGE_SIZE, totalCount);

            if (recentEntriesPageRange) {
                recentEntriesPageRange.textContent = `Showing ${startIndex}-${endIndex} of ${totalCount} ${totalCount === 1 ? "Entry" : "Entries"}`;
            }

            if (recentEntriesPrevPage) {
                recentEntriesPrevPage.disabled = currentRecentEntriesPage <= 1;
            }

            if (recentEntriesNextPage) {
                recentEntriesNextPage.disabled = currentRecentEntriesPage >= totalPages;
            }

            if (recentEntriesPageNumbers) {
                recentEntriesPageNumbers.innerHTML = "";
                const pages = generatePaginationPages(currentRecentEntriesPage, totalPages);

                pages.forEach((p) => {
                    if (p === "...") {
                        const ellipsis = document.createElement("span");
                        ellipsis.className = "clients-page-ellipsis";
                        ellipsis.textContent = "\\u2026";
                        ellipsis.setAttribute("aria-hidden", "true");
                        recentEntriesPageNumbers.appendChild(ellipsis);
                    } else {
                        const pageBtn = document.createElement("button");
                        pageBtn.type = "button";
                        pageBtn.className = `btn clients-page-num${p === currentRecentEntriesPage ? " active" : ""}`;
                        pageBtn.textContent = String(p);
                        pageBtn.setAttribute("aria-label", `Page ${p}`);
                        if (p === currentRecentEntriesPage) {
                            pageBtn.setAttribute("aria-current", "page");
                        }
                        pageBtn.addEventListener("click", () => {
                            if (currentRecentEntriesPage !== p) {
                                currentRecentEntriesPage = p;
                                renderRecentEntries();
                                scrollToRecentEntriesTop();
                            }
                        });
                        recentEntriesPageNumbers.appendChild(pageBtn);
                    }
                });
            }
        };

        const renderClientTableRows = (rows, totalCount = rows.length) => {
            if (!clientTableBody) {
                return;
            }

            clientTableBody.innerHTML = rows
                .map((row) => {
                    const statusMeta = STATUS_META[row.status] || STATUS_META["needs-attention"];
                    const rowClientId = Number.isFinite(row.clientId) ? row.clientId : "";
                    const tinRaw = row.tinRaw || normalizeDigits(row.tin);
                    const tinDisplay = formatTin(tinRaw) || row.tin;

                    let deadlineBadge = "";
                    if (row.daysRemaining !== null) {
                        if (row.deadlineCompleted) {
                            deadlineBadge = `<span class="badge bg-success dashboard-status-extra"><i class="bi bi-check-circle-fill me-1"></i>Completed</span>`;
                        } else {
                            const diffDays = row.daysRemaining;
                            if (diffDays < 0) {
                                deadlineBadge = `<span class="badge bg-danger dashboard-status-extra"><i class="bi bi-exclamation-octagon-fill me-1"></i>Overdue (${Math.abs(diffDays)}d)</span>`;
                            } else if (diffDays <= 5) {
                                deadlineBadge = `<span class="badge bg-warning text-dark dashboard-status-extra"><i class="bi bi-clock-fill me-1"></i>${diffDays}d left</span>`;
                            } else {
                                deadlineBadge = `<span class="badge bg-secondary dashboard-status-extra"><i class="bi bi-calendar-event me-1"></i>Deadline: ${row.deadlineDate}</span>`;
                            }
                        }
                    }

                    return `
                        <tr class="dashboard-client-row" data-client-id="${escapeHtml(String(rowClientId))}" data-client-name="${escapeHtml(row.clientName)}" data-tin="${escapeHtml(tinDisplay)}" data-tin-raw="${escapeHtml(tinRaw)}" data-trade="${escapeHtml(row.tradeName)}" data-remarks="${escapeHtml(row.remarks)}" tabindex="0" role="button" aria-label="View details for ${escapeHtml(row.clientName)}">
                            <td class="client-name-cell">${escapeHtml(row.clientName)}</td>
                            <td class="client-tin-cell">${escapeHtml(tinDisplay)}</td>
                            <td>${escapeHtml(formatEntryDate(row.lastEntryDate))}</td>
                            <td>${escapeHtml(row.currentPeriod)}</td>
                            <td>
                                <span class="status-badge ${statusMeta.badgeClass}">${statusMeta.label}</span>
                                ${deadlineBadge}
                            </td>
                        </tr>
                    `;
                })
                .join("");

            if (clientTableBody) {
                clientTableBody.classList.add("is-filtering");
                window.clearTimeout(filterTransitionTimer);
                filterTransitionTimer = window.setTimeout(() => {
                    clientTableBody.classList.remove("is-filtering");
                }, 170);
            }

            const hasRows = totalCount > 0;
            if (clientTableWrap) {
                clientTableWrap.hidden = !hasRows;
            }
            if (clientActivityEmpty) {
                clientActivityEmpty.hidden = hasRows;
            }
        };

        const sortClientActivity = (rows, sortBy) => {
            const safeRows = Array.isArray(rows) ? [...rows] : [];
            if (sortBy === "name-asc") {
                safeRows.sort((a, b) => normalize(a.clientName).localeCompare(normalize(b.clientName)));
            } else if (sortBy === "name-desc") {
                safeRows.sort((a, b) => normalize(b.clientName).localeCompare(normalize(a.clientName)));
            } else if (sortBy === "oldest") {
                safeRows.sort((a, b) => {
                    const aId = Number(a.clientId || 0);
                    const bId = Number(b.clientId || 0);
                    return aId - bId;
                });
            } else if (sortBy === "recent-activity") {
                safeRows.sort((a, b) => {
                    const aActivityTime = toTimestamp(a && (a.recentActivityAt || a.lastEntryDate));
                    const bActivityTime = toTimestamp(b && (b.recentActivityAt || b.lastEntryDate));
                    if (aActivityTime !== bActivityTime) {
                        return bActivityTime - aActivityTime;
                    }

                    const aId = Number(a.clientId || 0);
                    const bId = Number(b.clientId || 0);
                    return bId - aId;
                });
            } else {
                // "newest"
                safeRows.sort((a, b) => {
                    const aId = Number(a.clientId || 0);
                    const bId = Number(b.clientId || 0);
                    return bId - aId;
                });
            }
            return safeRows;
        };

        const applyClientFilters = (resetPage = true) => {
            if (resetPage) {
                currentClientWorkQueuePage = 1;
            }

            const query = normalize(clientTableSearch ? clientTableSearch.value : "");
            const queryDigits = normalizeDigits(query);
            const statusFilter = normalize(getActiveClientFilter());
            const sortBy = clientSortSelect ? clientSortSelect.value : "recent-activity";

            let filteredRows = CLIENT_ACTIVITY_DATA.filter((row) => {
                const tinDigits = normalizeDigits(row.tinRaw || row.tin);
                const matchesTin = queryDigits ? tinDigits.includes(queryDigits) : false;
                const matchesQuery = !query || normalize(row.clientName).includes(query) || matchesTin;
                const matchesStatus = statusFilter === "all" || normalize(row.status) === statusFilter;
                return matchesQuery && matchesStatus;
            });

            filteredRows = sortClientActivity(filteredRows, sortBy);

            const totalMatching = filteredRows.length;
            const totalPages = Math.ceil(totalMatching / CLIENT_WORK_QUEUE_PAGE_SIZE) || 1;
            if (currentClientWorkQueuePage > totalPages) {
                currentClientWorkQueuePage = totalPages;
            }
            if (currentClientWorkQueuePage < 1) {
                currentClientWorkQueuePage = 1;
            }

            const startIndex = (currentClientWorkQueuePage - 1) * CLIENT_WORK_QUEUE_PAGE_SIZE;
            const endIndex = startIndex + CLIENT_WORK_QUEUE_PAGE_SIZE;
            const pagedRows = filteredRows.slice(startIndex, endIndex);

            renderClientTableRows(pagedRows, totalMatching);
            updateClientFilterSummary(statusFilter, totalMatching);
            renderClientWorkQueuePagination(totalMatching);
        };

        const renderRecentEntries = () => {
            if (!recentEntriesBody) {
                return;
            }

            const allEntries = [...RECENT_ENTRIES_DATA]
                .sort((a, b) => normalize(b.entryDate).localeCompare(normalize(a.entryDate)));

            const totalMatching = allEntries.length;
            const totalPages = Math.ceil(totalMatching / RECENT_ENTRIES_PAGE_SIZE) || 1;
            if (currentRecentEntriesPage > totalPages) {
                currentRecentEntriesPage = totalPages;
            }
            if (currentRecentEntriesPage < 1) {
                currentRecentEntriesPage = 1;
            }

            const startIndex = (currentRecentEntriesPage - 1) * RECENT_ENTRIES_PAGE_SIZE;
            const endIndex = startIndex + RECENT_ENTRIES_PAGE_SIZE;
            const entriesToShow = allEntries.slice(startIndex, endIndex);

            recentEntriesBody.innerHTML = entriesToShow
                .map((entry) => {
                    return `
                        <tr>
                            <td>${escapeHtml(entry.clientName)}</td>
                            <td>${escapeHtml(formatEntryDate(entry.entryDate))}</td>
                            <td>${escapeHtml(formatCurrency(entry.totalAmount))}</td>
                        </tr>
                    `;
                })
                .join("");

            if (recentEntriesCountTag) {
                recentEntriesCountTag.textContent = `${totalMatching} ${totalMatching === 1 ? "Entry" : "Entries"}`;
            }

            const hasEntries = totalMatching > 0;
            if (recentEntriesWrap) {
                recentEntriesWrap.hidden = !hasEntries;
            }
            if (recentEntriesEmpty) {
                recentEntriesEmpty.hidden = hasEntries;
            }

            renderRecentEntriesPagination(totalMatching);
        };"""

if js_render_target in content:
    content = content.replace(js_render_target, js_render_replacement, 1)
    print("Updated table render and filter logic in JS!")
else:
    print("JS render target not found directly!")

# 6. Update event listeners in JS
listener_target = """        if (clientTableSearch) {
            bindTinInput(clientTableSearch, true);
            clientTableSearch.addEventListener("input", applyClientFilters);
        }

        clientFilterChips.forEach((chip) => {
            chip.addEventListener("click", () => {
                setActiveClientFilter(chip.dataset.filter || "all");
                applyClientFilters();
            });
        });

        if (clientFiltersReset) {
            clientFiltersReset.addEventListener("click", () => {
                if (clientTableSearch) {
                    clientTableSearch.value = "";
                }
                if (clientSortSelect) {
                    clientSortSelect.value = "newest";
                }
                setActiveClientFilter("all");
                applyClientFilters();
            });
        }

        if (clientSortSelect) {
            clientSortSelect.addEventListener("change", applyClientFilters);
        }"""

listener_replacement = """        if (clientTableSearch) {
            bindTinInput(clientTableSearch, true);
            clientTableSearch.addEventListener("input", () => {
                applyClientFilters(true);
            });
        }

        clientFilterChips.forEach((chip) => {
            chip.addEventListener("click", () => {
                setActiveClientFilter(chip.dataset.filter || "all");
                applyClientFilters(true);
            });
        });

        if (clientFiltersReset) {
            clientFiltersReset.addEventListener("click", () => {
                if (clientTableSearch) {
                    clientTableSearch.value = "";
                }
                if (clientSortSelect) {
                    clientSortSelect.value = "recent-activity";
                }
                setActiveClientFilter("all");
                applyClientFilters(true);
            });
        }

        if (clientSortSelect) {
            clientSortSelect.addEventListener("change", () => {
                applyClientFilters(true);
            });
        }

        if (clientWorkQueuePrevPage) {
            clientWorkQueuePrevPage.addEventListener("click", () => {
                if (currentClientWorkQueuePage > 1) {
                    currentClientWorkQueuePage -= 1;
                    applyClientFilters(false);
                    scrollToClientWorkQueueTop();
                }
            });
        }

        if (clientWorkQueueNextPage) {
            clientWorkQueueNextPage.addEventListener("click", () => {
                const query = normalize(clientTableSearch ? clientTableSearch.value : "");
                const queryDigits = normalizeDigits(query);
                const statusFilter = normalize(getActiveClientFilter());
                const matchingCount = CLIENT_ACTIVITY_DATA.filter((row) => {
                    const tinDigits = normalizeDigits(row.tinRaw || row.tin);
                    const matchesTin = queryDigits ? tinDigits.includes(queryDigits) : false;
                    const matchesQuery = !query || normalize(row.clientName).includes(query) || matchesTin;
                    const matchesStatus = statusFilter === "all" || normalize(row.status) === statusFilter;
                    return matchesQuery && matchesStatus;
                }).length;
                const totalPages = Math.ceil(matchingCount / CLIENT_WORK_QUEUE_PAGE_SIZE) || 1;
                if (currentClientWorkQueuePage < totalPages) {
                    currentClientWorkQueuePage += 1;
                    applyClientFilters(false);
                    scrollToClientWorkQueueTop();
                }
            });
        }

        if (recentEntriesPrevPage) {
            recentEntriesPrevPage.addEventListener("click", () => {
                if (currentRecentEntriesPage > 1) {
                    currentRecentEntriesPage -= 1;
                    renderRecentEntries();
                    scrollToRecentEntriesTop();
                }
            });
        }

        if (recentEntriesNextPage) {
            recentEntriesNextPage.addEventListener("click", () => {
                const totalPages = Math.ceil(RECENT_ENTRIES_DATA.length / RECENT_ENTRIES_PAGE_SIZE) || 1;
                if (currentRecentEntriesPage < totalPages) {
                    currentRecentEntriesPage += 1;
                    renderRecentEntries();
                    scrollToRecentEntriesTop();
                }
            });
        }"""

if listener_target in content:
    content = content.replace(listener_target, listener_replacement, 1)
    print("Updated event listeners in JS!")
else:
    print("Listener target not found directly!")

with open("templates/base/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Saved templates/base/dashboard.html successfully!")
