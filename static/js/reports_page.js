(function () {
    const config = window.SafeBooksReportsConfig || {};
    const urls = config.urls || {};
    const shared = window.SafeBooksShared || null;
    const reportsShared = window.SafeBooksReportsShared || null;

    const REPORT_TYPE_META = {
        financial_summary: {
            label: "Financial Summary Report",
            hint: "Sales, expenses, taxes, and monthly trend overview for the selected scope.",
            icon: "bi-cash-stack",
        },
        compliance_snapshot: {
            label: "Compliance Status Snapshot",
            hint: "Compliance distribution and client filing posture for the selected scope.",
            icon: "bi-patch-check",
        },
        client_remarks_overview: {
            label: "Client Remarks Overview",
            hint: "Status-remarks distribution and client behavior visibility for the selected scope.",
            icon: "bi-shield-check",
        },
    };

    const COMPLIANCE_LABELS = {
        filed: "Filed",
        pending: "Pending",
        late: "Late",
    };

    const REMARK_LABELS = {
        new: "New",
        active: "Active",
        separated: "Separated",
        closed: "Closed",
    };

    const AUTH_USER_KEY = String(config.authUserKey || "safebooks.authUser");
    const LOGIN_WELCOME_KEY = String(config.loginWelcomeKey || "safebooks.loginWelcome");
    const SIDEBAR_STATE_KEY = String(config.sidebarStateKey || "safebooks.sidebarCollapsed");
    const DESKTOP_QUERY = String(config.desktopQuery || "(min-width: 992px)");
    const HISTORY_STORAGE_KEY = "safebooks.reportsHistory";
    const MAX_HISTORY_ITEMS = 8;
    const FORCE_SCOPE_PARAM = "force_scope";
    const PENDING_LAST_CLIENT_KEY = "safebooks.pendingLastClientId";
    const DEFAULT_REPORT_TYPE = "financial_summary";
    const DEFAULT_REPORT_RANGE = "ytd";
    const DEFAULT_CLIENT_SCOPE = "all";
    const VALID_REPORT_RANGES = new Set(["ytd", "30", "90", "custom"]);

    const body = document.body;
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarCollapseToggle = document.getElementById("sidebarCollapseToggle");
    const sidebarCollapseIcon = document.getElementById("sidebarCollapseIcon");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");

    const dashboardUserAvatar = document.getElementById("dashboardUserAvatar");
    const dashboardUserName = document.getElementById("dashboardUserName");
    const dashboardProfileAction = document.getElementById("dashboardProfileAction");
    const dashboardLogoutAction = document.getElementById("dashboardLogoutAction");
    const plannedFeatureButtons = Array.from(document.querySelectorAll(".dashboard-nav-item[data-planned-feature]"));

    const reportsFilterForm = document.getElementById("reportsFilterForm");
    const reportsTypeSelect = document.getElementById("reportsTypeSelect");
    const reportsClientSelect = document.getElementById("reportsClientSelect");
    const reportsClientSearchInput = document.getElementById("reportsClientSearchInput");
    const reportsDateFrom = document.getElementById("reportsDateFrom");
    const reportsDateTo = document.getElementById("reportsDateTo");

    const reportsGenerateButton = document.getElementById("reportsGenerateButton");
    const reportsPreviewButton = document.getElementById("reportsPreviewButton");
    const reportsDownloadButton = document.getElementById("reportsDownloadButton");
    const reportsPrintButton = document.getElementById("reportsPrintButton");
    const reportsResetButton = document.getElementById("reportsResetButton");
    const reportsRetryButton = document.getElementById("reportsRetryButton");
    const reportsEmptyAdjustButton = document.getElementById("reportsEmptyAdjustButton");

    const reportsFilterStatus = document.getElementById("reportsFilterStatus");
    const reportsGenerationTag = document.getElementById("reportsGenerationTag");

    const reportsFeedbackCard = document.getElementById("reportsFeedbackCard");
    const reportsLoadingState = document.getElementById("reportsLoadingState");
    const reportsErrorState = document.getElementById("reportsErrorState");
    const reportsErrorText = document.getElementById("reportsErrorText");
    const reportsEmptyState = document.getElementById("reportsEmptyState");

    const reportsPreviewArea = document.getElementById("reportsPreviewArea");
    const reportsSummaryCards = document.getElementById("reportsSummaryCards");
    const reportsPreviewTitle = document.getElementById("reportsPreviewTitle");
    const reportsPreviewHint = document.getElementById("reportsPreviewHint");
    const reportsPreviewMetaTag = document.getElementById("reportsPreviewMetaTag");
    const reportsPreviewMeta = document.getElementById("reportsPreviewMeta");
    const reportsPreviewHead = document.getElementById("reportsPreviewHead");
    const reportsPreviewBody = document.getElementById("reportsPreviewBody");
    const reportsPreviewTable = document.getElementById("reportsPreviewTable");
    const reportsPreviewTableWrap = document.getElementById("reportsPreviewTableWrap");
    const reportsPreviewTableEmpty = document.getElementById("reportsPreviewTableEmpty");

    const reportsLedgerCard = document.getElementById("reportsLedgerCard");
    const reportsLedgerHint = document.getElementById("reportsLedgerHint");
    const reportsLedgerMetaTag = document.getElementById("reportsLedgerMetaTag");
    const reportsLedgerWrapper = document.getElementById("reportsLedgerWrapper");
    const reportsLedgerSheet = document.getElementById("reportsLedgerSheet");
    const reportsLedgerEmpty = document.getElementById("reportsLedgerEmpty");
    const reportsLedgerEmptyText = document.getElementById("reportsLedgerEmptyText");

    const reportsHistoryList = document.getElementById("reportsHistoryList");
    const reportsHistoryCountTag = document.getElementById("reportsHistoryCountTag");
    const reportsHistoryEmpty = document.getElementById("reportsHistoryEmpty");

    const uiToastContainer = document.getElementById("uiToastContainer");
    const workspaceDefaultsUrl = String(urls.workspaceDefaultsApi || "");

    if (
        !body
        || !reportsFilterForm
        || !reportsTypeSelect
        || !reportsClientSelect
        || !reportsDateFrom
        || !reportsDateTo
        || !reportsGenerateButton
        || !reportsPreviewButton
        || !reportsPrintButton
        || !reportsResetButton
        || !reportsFeedbackCard
        || !reportsLoadingState
        || !reportsErrorState
        || !reportsEmptyState
        || !reportsPreviewArea
        || !reportsSummaryCards
        || !reportsPreviewTitle
        || !reportsPreviewHint
        || !reportsPreviewMetaTag
        || !reportsPreviewMeta
        || !reportsPreviewHead
        || !reportsPreviewBody
        || !reportsPreviewTable
        || !reportsPreviewTableWrap
        || !reportsPreviewTableEmpty
        || !reportsLedgerCard
        || !reportsLedgerHint
        || !reportsLedgerMetaTag
        || !reportsLedgerWrapper
        || !reportsLedgerSheet
        || !reportsLedgerEmpty
        || !reportsLedgerEmptyText
        || !reportsHistoryList
        || !reportsHistoryCountTag
        || !reportsHistoryEmpty
        || !reportsGenerationTag
    ) {
        return;
    }

    window.setTimeout(() => {
        if (body.classList.contains("skeleton-active") && !body.classList.contains("skeleton-loaded")) {
            body.classList.remove("skeleton-active");
            body.classList.add("skeleton-loaded");
        }
    }, 1800);

    const currencyFormatter = new Intl.NumberFormat("en-PH", {
        style: "currency",
        currency: "PHP",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });

    const numberFormatter = new Intl.NumberFormat("en-PH", {
        maximumFractionDigits: 0,
    });

    const displayDateFormatter = new Intl.DateTimeFormat("en-PH", {
        year: "numeric",
        month: "short",
        day: "numeric",
    });

    const displayDateTimeFormatter = new Intl.DateTimeFormat("en-PH", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });

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
            return String(urls.loginPage || "/login/");
        }

        return shared.logoutCurrentUser({
            logoutUrl: String(urls.logoutApi || ""),
            loginUrl: String(urls.loginPage || "/login/"),
            authUserKey: AUTH_USER_KEY,
            loginWelcomeKey: LOGIN_WELCOME_KEY,
        });
    };

    const formatTin = (value) => {
        const digits = String(value || "").replace(/\D+/g, "").slice(0, 12);
        if (!digits) {
            return "";
        }
        const groups = digits.match(/.{1,3}/g) || [];
        return groups.join("-");
    };

    const escapeHtml = (value) => {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    const safeNumber = (value) => {
        const parsed = Number(value || 0);
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const toDateInputValue = (value) => {
        if (!(value instanceof Date) || Number.isNaN(value.getTime())) {
            return "";
        }

        const year = value.getFullYear();
        const month = String(value.getMonth() + 1).padStart(2, "0");
        const day = String(value.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    };

    const parseDateInput = (value) => {
        const cleaned = String(value || "").trim();
        if (!/^\d{4}-\d{2}-\d{2}$/.test(cleaned)) {
            return null;
        }

        const parsed = new Date(`${cleaned}T00:00:00`);
        if (Number.isNaN(parsed.getTime())) {
            return null;
        }

        return parsed;
    };

    const formatCurrency = (value) => currencyFormatter.format(safeNumber(value));

    const formatCount = (value) => numberFormatter.format(safeNumber(value));

    const formatIsoDateForDisplay = (isoDate) => {
        const parsed = parseDateInput(isoDate);
        if (!parsed) {
            return "-";
        }
        return displayDateFormatter.format(parsed);
    };

    const formatGeneratedDateTime = (isoValue) => {
        const parsed = new Date(String(isoValue || ""));
        if (Number.isNaN(parsed.getTime())) {
            return "-";
        }
        return displayDateTimeFormatter.format(parsed);
    };

    const getDefaultDateRange = () => {
        const today = new Date();
        const rangeStart = new Date(today.getFullYear(), 0, 1);
        return {
            dateFrom: toDateInputValue(rangeStart),
            dateTo: toDateInputValue(today),
        };
    };

    const getRelativeDateRange = (days) => {
        const totalDays = Number(days || 0);
        if (!Number.isFinite(totalDays) || totalDays <= 0) {
            return { dateFrom: "", dateTo: "" };
        }

        const today = new Date();
        const rangeStart = new Date(today);
        rangeStart.setDate(today.getDate() - (totalDays - 1));

        return {
            dateFrom: toDateInputValue(rangeStart),
            dateTo: toDateInputValue(today),
        };
    };

    const getDateRangeFromPreset = (rangeKey) => {
        const normalized = String(rangeKey || "").trim();
        if (normalized === "30") {
            return getRelativeDateRange(30);
        }
        if (normalized === "90") {
            return getRelativeDateRange(90);
        }
        if (normalized === "ytd") {
            return getDefaultDateRange();
        }

        return { dateFrom: "", dateTo: "" };
    };

    const normalizeReportType = (value) => {
        const normalized = String(value || "").trim();
        return REPORT_TYPE_META[normalized] ? normalized : DEFAULT_REPORT_TYPE;
    };

    const normalizeReportRange = (value) => {
        const normalized = String(value || "").trim();
        return VALID_REPORT_RANGES.has(normalized) ? normalized : DEFAULT_REPORT_RANGE;
    };

    const normalizeClientScope = (value) => {
        const normalized = String(value || "").trim();
        return normalized === "last" ? "last" : DEFAULT_CLIENT_SCOPE;
    };

    const applyDefaultsToFilters = (defaults) => {
        const safeDefaults = defaults && typeof defaults === "object" ? defaults : {};

        const defaultReportType = normalizeReportType(safeDefaults.default_report_type);
        const defaultReportRange = normalizeReportRange(safeDefaults.default_report_range);
        const defaultClientScope = normalizeClientScope(safeDefaults.default_client_scope);

        reportsTypeSelect.value = defaultReportType;

        if (defaultReportRange === "custom") {
            const customFrom = String(safeDefaults.default_report_range_from || "").trim();
            const customTo = String(safeDefaults.default_report_range_to || "").trim();
            reportsDateFrom.value = parseDateInput(customFrom) ? customFrom : "";
            reportsDateTo.value = parseDateInput(customTo) ? customTo : "";
        } else {
            const dateRange = getDateRangeFromPreset(defaultReportRange);
            reportsDateFrom.value = dateRange.dateFrom || "";
            reportsDateTo.value = dateRange.dateTo || "";
        }

        let targetClientValue = "all";
        if (defaultClientScope === "last") {
            const lastClientId = safeNumber(safeDefaults.last_client_id);
            if (Number.isFinite(lastClientId) && lastClientId > 0) {
                targetClientValue = String(lastClientId);
            }
        }

        const optionExists = Array.from(reportsClientSelect.options)
            .some((optionItem) => optionItem.value === targetClientValue);
        reportsClientSelect.value = optionExists ? targetClientValue : "all";
    };

    const toReportTypeLabel = (reportType) => {
        const normalized = String(reportType || "").trim();
        return REPORT_TYPE_META[normalized] ? REPORT_TYPE_META[normalized].label : "Report";
    };

    const toReportTypeHint = (reportType) => {
        const normalized = String(reportType || "").trim();
        return REPORT_TYPE_META[normalized] ? REPORT_TYPE_META[normalized].hint : "Generated report preview.";
    };

    const toRemarkLabel = (remarksValue) => {
        const key = String(remarksValue || "").toLowerCase();
        return REMARK_LABELS[key] || "New";
    };

    const toComplianceLabel = (complianceValue) => {
        const key = String(complianceValue || "").toLowerCase();
        return COMPLIANCE_LABELS[key] || "Pending";
    };

    const buildScopeLabel = (selectedClientId, fallbackLabel = "All clients") => {
        if (!Number.isFinite(selectedClientId) || selectedClientId <= 0) {
            return fallbackLabel;
        }

        const matchedClient = availableClients.find((client) => {
            return safeNumber(client.id) === selectedClientId;
        });

        if (!matchedClient) {
            return fallbackLabel;
        }

        const clientName = String(matchedClient.client_name || "Client");
        const clientTin = String(matchedClient.tin_number || "").trim();
        if (!clientTin) {
            return clientName;
        }
        return `${clientName} (TIN: ${clientTin})`;
    };

    const toDisplayText = (value, fallback = "-") => {
        const cleaned = String(value == null ? "" : value).trim();
        return cleaned || fallback;
    };

    const toLedgerHeaderLabel = (labelValue) => {
        const cleanedLabel = String(labelValue || "")
            .replace(/_/g, " ")
            .replace(/\s+/g, " ")
            .trim();

        return cleanedLabel ? cleanedLabel.toUpperCase() : "VALUE";
    };

    const formatClientBirthday = (isoDateValue) => {
        const parsedFromInput = parseDateInput(isoDateValue);
        if (parsedFromInput) {
            return displayDateFormatter.format(parsedFromInput);
        }

        const parsedDate = new Date(String(isoDateValue || ""));
        if (Number.isNaN(parsedDate.getTime())) {
            return "-";
        }

        return displayDateFormatter.format(parsedDate);
    };

    const isClientScopedReport = (report) => {
        const clientId = safeNumber(report && report.clientId);
        return Number.isFinite(clientId) && clientId > 0;
    };

    const getClientForReport = (report) => {
        if (!isClientScopedReport(report)) {
            return null;
        }

        const clientId = safeNumber(report.clientId);
        return availableClients.find((client) => safeNumber(client.id) === clientId) || null;
    };

    const buildLedgerColumnSchema = (report) => {
        const reportColumns = Array.isArray(report && report.columns) ? report.columns : [];

        const periodColumn = reportColumns.find((column) => {
            const key = String(column && column.key || "").toLowerCase();
            const label = String(column && column.label || "").toLowerCase();

            return key.includes("period")
                || key.includes("date")
                || key.includes("month")
                || label.includes("period")
                || label.includes("date")
                || label.includes("month");
        }) || null;

        const ignoredColumnKeys = new Set([
            "client_name",
            "tin_number",
            "trade_name",
            "location",
            "permit_number",
            "birthday",
            "email",
        ]);

        let dataColumns = reportColumns
            .filter((column) => {
                const columnKey = String(column && column.key || "").toLowerCase();
                if (periodColumn && columnKey === String(periodColumn.key || "").toLowerCase()) {
                    return false;
                }
                return !ignoredColumnKeys.has(columnKey);
            });

        if (!dataColumns.length) {
            dataColumns = reportColumns
                .filter((column) => {
                    if (!periodColumn) {
                        return true;
                    }

                    return String(column && column.key || "").toLowerCase() !== String(periodColumn.key || "").toLowerCase();
                });
        }

        if (!dataColumns.length) {
            dataColumns = [{ key: "__detail__", label: "Details", synthetic: true }];
        }

        return {
            periodColumn,
            dataColumns,
        };
    };

    const buildLedgerRowCells = (report, periodColumn, dataColumns) => {
        const rows = Array.isArray(report && report.rows) ? report.rows : [];
        const periodKey = periodColumn ? String(periodColumn.key || "") : "";

        return rows.map((row, rowIndex) => {
            const safeRow = row && typeof row === "object" ? row : {};

            let periodValue = periodKey ? safeRow[periodKey] : "";
            if (!String(periodValue || "").trim()) {
                periodValue = safeRow.current_period || safeRow.last_entry_date || `Line ${rowIndex + 1}`;
            }

            const cells = dataColumns.map((column) => {
                if (column && column.synthetic) {
                    const syntheticValue = Object.keys(safeRow)
                        .filter((key) => key !== periodKey)
                        .map((key) => toDisplayText(safeRow[key], ""))
                        .find((value) => Boolean(value));

                    return toDisplayText(syntheticValue);
                }

                return toDisplayText(safeRow[column.key]);
            });

            return {
                period: toDisplayText(periodValue, `Line ${rowIndex + 1}`),
                cells,
            };
        });
    };

    const buildPrintLayoutDefinition = (report) => {
        if (!report || report.reportType !== "financial_summary") {
            return null;
        }
        const reportColumns = Array.isArray(report && report.columns) ? report.columns : [];
        const columnMeta = reportColumns
            .map((column) => {
                return {
                    key: String(column && column.key || ""),
                    label: toDisplayText(column && (column.label || column.key), "Value"),
                };
            })
            .filter((column) => Boolean(column.label));

        const columns = columnMeta.length
            ? columnMeta.map((column) => column.label)
            : ["Details"];

        const rows = Array.isArray(report && report.rows) ? report.rows : [];
        const formattedRows = rows.map((row) => {
            const safeRow = row && typeof row === "object" ? row : {};
            if (!columnMeta.length) {
                return [toDisplayText(row)];
            }

            return columnMeta.map((column) => toDisplayText(safeRow[column.key]));
        });

        const rowCount = formattedRows.length;
        const rowHint = rowCount
            ? "Prepared from generated report values."
            : "No rows matched the selected date range. Blank lines are available for manual notes.";

        const orderedColumns = window.SafeBooksReportsShared && typeof window.SafeBooksReportsShared.normalizeFinancialSummaryColumns === "function"
            ? window.SafeBooksReportsShared.normalizeFinancialSummaryColumns(columns)
            : columns;

        return {
            columns: orderedColumns,
            rows: formattedRows,
            rowCount,
            rowHint,
            reportTitle: "SafeBooks Client Report Sheet",
            minRows: 14,
        };
    };

    const setFilterStatus = (message) => {
        reportsFilterStatus.textContent = String(message || "");
    };

    const setGenerationTag = (message) => {
        reportsGenerationTag.textContent = String(message || "");
    };

    const setFeedbackState = (state, errorMessage = "") => {
        const normalized = String(state || "empty").toLowerCase();

        if (normalized === "ready") {
            reportsFeedbackCard.hidden = true;
            return;
        }

        reportsFeedbackCard.hidden = false;
        reportsLoadingState.hidden = normalized !== "loading";
        reportsErrorState.hidden = normalized !== "error";
        reportsEmptyState.hidden = normalized !== "empty";

        if (normalized === "error" && reportsErrorText) {
            reportsErrorText.textContent = errorMessage || "Unable to generate report with the current filters.";
        }
    };

    const setActionLoadingState = (isLoading) => {
        const loading = Boolean(isLoading);
        reportsGenerateButton.disabled = loading;
        reportsPreviewButton.disabled = loading;
        reportsResetButton.disabled = loading;

        if (!latestGeneratedReport) {
            if (reportsDownloadButton) {
                reportsDownloadButton.disabled = true;
            }
            reportsPrintButton.disabled = true;
        } else {
            if (reportsDownloadButton) {
                reportsDownloadButton.disabled = loading || !latestGeneratedReport.rows.length;
            }
            reportsPrintButton.disabled = loading
                || latestGeneratedReport.reportType !== "financial_summary"
                || !isClientScopedReport(latestGeneratedReport)
                || !latestGeneratedReport.printLayout;
        }
    };

    const togglePreviewTableEmptyState = (hasRows) => {
        const shouldShowRows = Boolean(hasRows);
        reportsPreviewTableWrap.hidden = !shouldShowRows;
        reportsPreviewTableEmpty.hidden = shouldShowRows;
    };

    const toCsvCell = (value) => {
        const raw = String(value == null ? "" : value);
        if (!/[\",\r\n]/.test(raw)) {
            return raw;
        }
        return `"${raw.replace(/"/g, '""')}"`;
    };

    const downloadCsv = (report) => {
        if (!report || !Array.isArray(report.columns) || !Array.isArray(report.rows) || !report.columns.length) {
            showToast("Generate a report first before downloading.", "warning");
            return;
        }

        const header = report.columns.map((column) => toCsvCell(column.label)).join(",");
        const bodyRows = report.rows.map((row) => {
            return report.columns
                .map((column) => toCsvCell(row[column.key]))
                .join(",");
        });

        const csvContent = [header, ...bodyRows].join("\r\n");
        const csvBlob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const objectUrl = window.URL.createObjectURL(csvBlob);

        const stamp = toDateInputValue(new Date()).replace(/-/g, "");
        const reportTypeToken = String(report.reportType || "report").replace(/[^a-z0-9_]+/gi, "_").toLowerCase();
        const fileName = `${reportTypeToken}_${report.dateFrom || "from"}_${report.dateTo || "to"}_${stamp}.csv`;

        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = fileName;
        anchor.rel = "noopener";

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        window.setTimeout(() => {
            window.URL.revokeObjectURL(objectUrl);
        }, 200);
    };

    const readHistoryItems = () => {
        try {
            const rawValue = window.sessionStorage.getItem(HISTORY_STORAGE_KEY) || "";
            if (!rawValue) {
                return [];
            }

            const parsedValue = JSON.parse(rawValue);
            if (!Array.isArray(parsedValue)) {
                return [];
            }

            return parsedValue.filter((item) => item && typeof item === "object");
        } catch (error) {
            return [];
        }
    };

    const writeHistoryItems = (historyItems) => {
        try {
            window.sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(historyItems));
        } catch (error) {
            // Ignore storage failures to keep report generation usable.
        }
    };

    const renderHistoryItems = (historyItems) => {
        const items = Array.isArray(historyItems) ? historyItems : [];
        reportsHistoryCountTag.textContent = `${items.length} item${items.length === 1 ? "" : "s"}`;

        if (!items.length) {
            reportsHistoryList.innerHTML = "";
            reportsHistoryEmpty.hidden = false;
            return;
        }

        reportsHistoryEmpty.hidden = true;
        reportsHistoryList.innerHTML = items
            .map((item) => {
                const generatedLabel = formatGeneratedDateTime(item.generatedAt);
                const rowCountLabel = `${formatCount(item.rowCount)} row${safeNumber(item.rowCount) === 1 ? "" : "s"}`;
                return `
                    <li class="reports-history-item">
                        <div class="reports-history-meta">
                            <strong>${escapeHtml(item.reportLabel || "Report")}</strong>
                            <p>${escapeHtml(item.scopeLabel || "All clients")} | ${escapeHtml(item.dateFrom || "-")} to ${escapeHtml(item.dateTo || "-")} | ${escapeHtml(rowCountLabel)} | ${escapeHtml(generatedLabel)}</p>
                        </div>
                        <div class="reports-history-actions">
                            <button type="button" class="btn dashboard-action-btn outline reports-history-apply-btn" data-history-id="${escapeHtml(item.id || "")}">
                                Apply & Regenerate
                            </button>
                        </div>
                    </li>
                `;
            })
            .join("");
    };

    const appendHistoryItem = (report) => {
        if (!report) {
            return;
        }

        const historyItems = readHistoryItems();
        const nextItem = {
            id: `${Date.now()}_${Math.round(Math.random() * 100000)}`,
            reportType: report.reportType,
            reportLabel: report.reportLabel,
            clientId: report.clientId,
            scopeLabel: report.scopeLabel,
            dateFrom: report.dateFrom,
            dateTo: report.dateTo,
            generatedAt: report.generatedAt,
            rowCount: report.rows.length,
        };

        const updatedItems = [nextItem, ...historyItems].slice(0, MAX_HISTORY_ITEMS);
        writeHistoryItems(updatedItems);
        renderHistoryItems(updatedItems);
    };

    const applyHistoryFilterItem = (historyItem) => {
        if (!historyItem || typeof historyItem !== "object") {
            return;
        }

        const reportType = String(historyItem.reportType || "");
        if (REPORT_TYPE_META[reportType]) {
            reportsTypeSelect.value = reportType;
        }

        if (String(historyItem.clientId || "all") === "all" || !Number.isFinite(safeNumber(historyItem.clientId))) {
            reportsClientSelect.value = "all";
        } else {
            const targetValue = String(historyItem.clientId);
            const optionExists = Array.from(reportsClientSelect.options).some((optionItem) => optionItem.value === targetValue);
            reportsClientSelect.value = optionExists ? targetValue : "all";
        }

        const dateFromValue = String(historyItem.dateFrom || "").trim();
        const dateToValue = String(historyItem.dateTo || "").trim();

        if (parseDateInput(dateFromValue)) {
            reportsDateFrom.value = dateFromValue;
        }
        if (parseDateInput(dateToValue)) {
            reportsDateTo.value = dateToValue;
        }
    };

    const collectFilters = () => {
        const reportType = String(reportsTypeSelect.value || "").trim();
        const selectedClientValue = String(reportsClientSelect.value || "all").trim();
        const clientId = selectedClientValue === "all"
            ? null
            : safeNumber(selectedClientValue);

        return {
            reportType,
            clientId: Number.isFinite(clientId) && clientId > 0 ? clientId : null,
            dateFrom: String(reportsDateFrom.value || "").trim(),
            dateTo: String(reportsDateTo.value || "").trim(),
        };
    };

    const validateFilters = (filters) => {
        if (!filters || !REPORT_TYPE_META[filters.reportType]) {
            return "Please select a valid report type.";
        }

        const parsedFrom = parseDateInput(filters.dateFrom);
        const parsedTo = parseDateInput(filters.dateTo);

        if (!parsedFrom || !parsedTo) {
            return "Please provide a valid date range.";
        }

        if (parsedFrom.getTime() > parsedTo.getTime()) {
            return "Date From cannot be later than Date To.";
        }

        return "";
    };

    const isIsoDateWithinRange = (isoDate, filters) => {
        if (!isoDate) {
            return true;
        }

        const rowDate = parseDateInput(isoDate);
        const rangeFrom = parseDateInput(filters.dateFrom);
        const rangeTo = parseDateInput(filters.dateTo);

        if (!rowDate || !rangeFrom || !rangeTo) {
            return true;
        }

        const rowTime = rowDate.getTime();
        return rowTime >= rangeFrom.getTime() && rowTime <= rangeTo.getTime();
    };

    const isTrendMonthWithinRange = (yearValue, monthValue, filters) => {
        const year = safeNumber(yearValue);
        const month = safeNumber(monthValue);
        const rangeFrom = parseDateInput(filters.dateFrom);
        const rangeTo = parseDateInput(filters.dateTo);

        if (!year || !month || !rangeFrom || !rangeTo) {
            return true;
        }

        const monthStart = new Date(year, month - 1, 1);
        const monthEnd = new Date(year, month, 0, 23, 59, 59, 999);
        return monthEnd.getTime() >= rangeFrom.getTime() && monthStart.getTime() <= rangeTo.getTime();
    };

    const filterActivityRows = (rows, filters) => {
        const sourceRows = Array.isArray(rows) ? rows : [];
        return sourceRows.filter((row) => {
            const rowClientId = safeNumber(row.client_id);
            if (Number.isFinite(filters.clientId) && filters.clientId > 0 && rowClientId !== filters.clientId) {
                return false;
            }

            return isIsoDateWithinRange(row.last_entry_date, filters);
        });
    };

    const renderSummaryCards = (cards) => {
        const safeCards = Array.isArray(cards) ? cards : [];
        reportsSummaryCards.innerHTML = safeCards
            .map((card, index) => {
                const delayValue = (0.16 + (index * 0.03)).toFixed(2);
                const iconClass = String(card.icon || "bi-file-earmark-bar-graph");
                return `
                    <div class="col-sm-6 col-xl-3">
                        <article class="dashboard-stat-card dashboard-fade-up reports-stat-card" style="--delay: ${delayValue}s;">
                            <div class="stat-icon"><i class="bi ${escapeHtml(iconClass)}"></i></div>
                            <div>
                                <p class="stat-label">${escapeHtml(card.label || "Metric")}</p>
                                <h3>${escapeHtml(card.value || "0")}</h3>
                                <p class="stat-note">${escapeHtml(card.note || "")}</p>
                            </div>
                        </article>
                    </div>
                `;
            })
            .join("");
    };

    const renderPreviewRows = (columns, rows) => {
        const safeColumns = Array.isArray(columns) ? columns : [];
        const safeRows = Array.isArray(rows) ? rows : [];

        reportsPreviewHead.innerHTML = `
            <tr>
                ${safeColumns.map((column) => `<th>${escapeHtml(column.label || "")}</th>`).join("")}
            </tr>
        `;

        reportsPreviewBody.innerHTML = safeRows
            .map((row) => {
                return `
                    <tr>
                        ${safeColumns.map((column) => `<td>${escapeHtml(row[column.key])}</td>`).join("")}
                    </tr>
                `;
            })
            .join("");

        togglePreviewTableEmptyState(safeRows.length > 0);
    };

    const renderPreviewMeta = (report) => {
        reportsPreviewMeta.innerHTML = `
            <span class="reports-preview-chip"><i class="bi bi-file-earmark-text"></i>${escapeHtml(report.reportLabel)}</span>
            <span class="reports-preview-chip"><i class="bi bi-people"></i>${escapeHtml(report.scopeLabel)}</span>
            <span class="reports-preview-chip"><i class="bi bi-calendar-range"></i>${escapeHtml(report.dateFrom)} to ${escapeHtml(report.dateTo)}</span>
            <span class="reports-preview-chip"><i class="bi bi-clock"></i>${escapeHtml(formatGeneratedDateTime(report.generatedAt))}</span>
        `;
    };

    const buildLedgerSheetHtml = (report) => {
        if (!reportsShared || typeof reportsShared.buildReportSheetHtml !== "function") {
            return "";
        }

        const client = getClientForReport(report);
        const clientName = toDisplayText(client && client.client_name ? client.client_name : report.scopeLabel, "Selected client");
        const clientTin = toDisplayText(client && formatTin(client.tin_number));
        const tradeName = toDisplayText(client && client.trade_name);
        const location = toDisplayText(client && client.location);
        const permitNumber = toDisplayText(client && client.permit_number);
        const birthday = client && client.birthday ? formatClientBirthday(client.birthday) : "-";
        const email = toDisplayText(client && client.email);
        const emailPassword = toDisplayText(client && client.email_password);
        const orusAccount = toDisplayText(client && client.orus_account);
        const orusPassword = toDisplayText(client && client.orus_password);
        const customFields = client && Array.isArray(client.custom_fields) ? client.custom_fields : [];

        const reportTypeLabel = toDisplayText(report.reportLabel, "Client Report");
        const generatedLabel = formatGeneratedDateTime(report.generatedAt);
        const dateRangeLabel = `${toDisplayText(report.dateFrom)} to ${toDisplayText(report.dateTo)}`;

        const printLayout = report && report.printLayout ? report.printLayout : null;
        const usePrintLayout = Boolean(printLayout && Array.isArray(printLayout.columns));

        let columns = [];
        let rows = [];
        let rowHint = "";
        let minRows = 14;
        let reportTitle = "SafeBooks Client Report Sheet";

        if (usePrintLayout) {
            columns = printLayout.columns;
            rows = printLayout.rows || [];
            rowHint = toDisplayText(printLayout.rowHint, "Prepared from generated report values.");
            minRows = Number.isFinite(printLayout.minRows) ? printLayout.minRows : minRows;
            reportTitle = toDisplayText(printLayout.reportTitle, reportTitle);
        } else {
            const schema = buildLedgerColumnSchema(report);
            const periodLabel = toLedgerHeaderLabel(
                schema.periodColumn
                    ? schema.periodColumn.label || schema.periodColumn.key
                    : "Period"
            );

            const ledgerRows = buildLedgerRowCells(report, schema.periodColumn, schema.dataColumns);
            columns = [
                periodLabel,
                ...schema.dataColumns.map((column) => toLedgerHeaderLabel(column.label || column.key)),
            ];
            rows = ledgerRows.map((row) => [row.period, ...row.cells]);
            rowHint = ledgerRows.length
                ? "Prepared from generated report values."
                : "No rows matched the selected date range. Blank lines are available for manual notes.";
        }

        return reportsShared.buildReportSheetHtml({
            reportTitle,
            printedBy: String(config.defaultName || "Bookkeeper User"),
            meta: {
                reportTypeLabel,
                dateRangeLabel,
                generatedLabel,
            },
            client: {
                clientName,
                tin: clientTin,
                tradeName,
                location,
                permitNumber,
                birthday,
                email,
                emailPassword,
                orusAccount,
                orusPassword,
                customFields,
            },
            table: {
                columns,
                rows,
                minRows,
            },
            rowHint,
        });
    };

    const renderLedgerPreview = (report) => {
        if (!report) {
            return;
        }

        if (report.reportType !== "financial_summary") {
            reportsLedgerCard.hidden = true;
            reportsPrintButton.disabled = true;
            return;
        }

        reportsLedgerCard.hidden = false;

        if (!isClientScopedReport(report)) {
            reportsLedgerWrapper.hidden = true;
            reportsLedgerEmpty.hidden = false;
            if (reportsLedgerEmptyText) {
                reportsLedgerEmptyText.textContent = "Select one client and generate a report to see this print format.";
            }
            reportsLedgerSheet.innerHTML = "";
            reportsLedgerHint.textContent = "This familiar format appears when one client is selected.";
            reportsLedgerMetaTag.textContent = "Client scope required";
            reportsPrintButton.disabled = true;
            return;
        }

        const printLayout = report.printLayout || null;
        if (!printLayout) {
            reportsLedgerWrapper.hidden = true;
            reportsLedgerEmpty.hidden = false;
            if (reportsLedgerEmptyText) {
                reportsLedgerEmptyText.textContent = report.printLayoutError
                    ? String(report.printLayoutError)
                    : "Client report layout is not available yet. Generate the report again.";
            }
            reportsLedgerHint.textContent = "Client report sheet uses the generated report data.";
            reportsLedgerMetaTag.textContent = "Print layout unavailable";
            reportsLedgerSheet.innerHTML = "";
            reportsPrintButton.disabled = true;
            return;
        }

        reportsLedgerWrapper.hidden = false;
        reportsLedgerEmpty.hidden = true;
        reportsLedgerHint.textContent = "Client report sheet for the selected client and date range.";
        const rowCountLabel = `${formatCount(printLayout.rowCount || 0)} row${printLayout.rowCount === 1 ? "" : "s"}`;
        reportsLedgerMetaTag.textContent = `${toDisplayText(report.scopeLabel, "Selected client")} | ${rowCountLabel}`;
        reportsLedgerSheet.innerHTML = buildLedgerSheetHtml(report);
        reportsPrintButton.disabled = false;
    };

    const clearLedgerPreview = () => {
        reportsLedgerCard.hidden = true;
        reportsLedgerWrapper.hidden = false;
        reportsLedgerEmpty.hidden = true;
        reportsLedgerSheet.innerHTML = "";
        if (reportsLedgerEmptyText) {
            reportsLedgerEmptyText.textContent = "Select one client and generate a report to see this print format.";
        }
        reportsLedgerHint.textContent = "Familiar paper-style format for review and future printing.";
        reportsLedgerMetaTag.textContent = "Print-ready";
        reportsPrintButton.disabled = true;
    };

    const buildLedgerPrintDocumentHtml = (report, sheetMarkup) => {
        const reportLabel = toDisplayText(report && report.reportLabel, "Client Report");

        return `
            <!doctype html>
            <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <title>${escapeHtml(reportLabel)} - Print</title>
                    <style>
                        @page {
                            size: A4 portrait;
                            margin: 10mm;
                        }

                        * {
                            box-sizing: border-box;
                        }

                        html,
                        body {
                            margin: 0;
                            padding: 0;
                            background: #ffffff;
                            color: #1f3f74;
                            font-family: Arial, "Helvetica Neue", sans-serif;
                        }

                        .reports-print-root {
                            width: 100%;
                        }

                        .reports-ledger-sheet {
                            border: 1px solid #c7d8f6;
                            padding: 8px;
                            width: 100%;
                        }

                        .reports-ledger-heading {
                            display: flex;
                            align-items: baseline;
                            justify-content: space-between;
                            gap: 16px;
                        }

                        .reports-ledger-title {
                            margin: 0;
                            color: #183365;
                            font-size: 13px;
                            font-weight: 700;
                            text-transform: uppercase;
                            letter-spacing: 0.04em;
                        }

                        .reports-ledger-printed-by {
                            margin: 0;
                            color: #607ca9;
                            font-size: 10px;
                            font-weight: 700;
                            text-align: right;
                            white-space: nowrap;
                        }

                        .reports-ledger-meta-row {
                            margin: 6px 0;
                        }

                        .reports-ledger-meta-pill {
                            display: inline-block;
                            border: 1px solid #d8e4f8;
                            border-radius: 999px;
                            padding: 2px 8px;
                            margin-right: 4px;
                            margin-bottom: 4px;
                            background: #f8fbff;
                            color: #3f5e92;
                            font-size: 10px;
                            font-weight: 700;
                        }

                        .reports-ledger-client-table,
                        .reports-ledger-grid-table {
                            width: 100%;
                            border-collapse: collapse;
                            table-layout: fixed;
                        }

                        .reports-ledger-client-table th,
                        .reports-ledger-client-table td,
                        .reports-ledger-grid-table th,
                        .reports-ledger-grid-table td {
                            border: 1px solid #ccd9f0;
                            padding: 4px 6px;
                            color: #1f3f74;
                            font-size: 10px;
                        }

                        .reports-ledger-client-table th,
                        .reports-ledger-grid-table th {
                            background: #f7fafe;
                            color: #4d6896;
                            text-transform: uppercase;
                            letter-spacing: 0.04em;
                            font-weight: 700;
                        }

                        .reports-ledger-grid-wrap {
                            margin-top: 8px;
                        }

                        .reports-ledger-grid-table td {
                            height: 24px;
                            font-weight: 700;
                        }

                        .reports-ledger-note {
                            margin-top: 6px;
                            color: #607ca9;
                            font-size: 10px;
                            font-weight: 700;
                        }
                    </style>
                </head>
                <body>
                    <main class="reports-print-root">${sheetMarkup}</main>
                </body>
            </html>
        `;
    };

    const printLedgerLayout = () => {
        if (!latestGeneratedReport) {
            showToast("Generate a report before printing.", "warning");
            return;
        }

        if (latestGeneratedReport.reportType !== "financial_summary") {
            showToast("Print layout is only available for Financial Summary reports.", "warning");
            return;
        }

        if (!isClientScopedReport(latestGeneratedReport)) {
            showToast("Select one client to use this print-friendly format.", "warning");
            return;
        }

        if (!latestGeneratedReport.printLayout) {
            showToast("Print layout is not available yet. Generate the report again.", "warning");
            return;
        }

        const sheetMarkup = String(reportsLedgerSheet.innerHTML || "").trim();
        if (!sheetMarkup) {
            showToast("Print layout is not ready yet. Generate the report again.", "warning");
            return;
        }

        const documentMarkup = buildLedgerPrintDocumentHtml(latestGeneratedReport, sheetMarkup);
        const existingFrame = document.getElementById("reportsPrintFrame");
        if (existingFrame) {
            existingFrame.remove();
        }

        const printFrame = document.createElement("iframe");
        printFrame.id = "reportsPrintFrame";
        printFrame.setAttribute("title", "Reports Print Layout");
        printFrame.setAttribute("aria-hidden", "true");
        printFrame.style.position = "fixed";
        printFrame.style.right = "0";
        printFrame.style.bottom = "0";
        printFrame.style.width = "0";
        printFrame.style.height = "0";
        printFrame.style.border = "0";
        printFrame.style.opacity = "0";
        printFrame.style.pointerEvents = "none";
        document.body.appendChild(printFrame);

        const frameWindow = printFrame.contentWindow;
        const frameDocument = frameWindow ? frameWindow.document : null;
        if (!frameDocument) {
            showToast("Print preview could not be prepared. Please try again.", "warning");
            printFrame.remove();
            return;
        }

        try {
            frameDocument.open();
            frameDocument.write(documentMarkup);
            frameDocument.close();
        } catch (error) {
            showToast("Print preview could not be prepared. Please try again.", "warning");
            printFrame.remove();
            return;
        }

        const triggerPrint = () => {
            frameWindow.focus();
            frameWindow.print();
            window.setTimeout(() => {
                printFrame.remove();
            }, 800);
        };

        if (frameDocument.readyState === "complete") {
            window.setTimeout(triggerPrint, 60);
        } else {
            printFrame.addEventListener("load", () => {
                window.setTimeout(triggerPrint, 60);
            }, { once: true });
        }
    };

    const renderGeneratedReport = (report) => {
        latestGeneratedReport = report;
        reportsPreviewArea.hidden = false;
        renderSummaryCards(report.summaryCards);
        renderPreviewRows(report.columns, report.rows);
        renderPreviewMeta(report);
        renderLedgerPreview(report);

        reportsPreviewTitle.textContent = report.reportLabel;
        reportsPreviewHint.textContent = report.hint;
        reportsPreviewMetaTag.textContent = `${formatCount(report.rows.length)} row${report.rows.length === 1 ? "" : "s"}`;

        setGenerationTag(`Generated ${formatGeneratedDateTime(report.generatedAt)}`);
        setFilterStatus(`${report.reportLabel} generated successfully.`);
        if (reportsDownloadButton) {
            reportsDownloadButton.disabled = report.rows.length === 0;
        }
        reportsPrintButton.disabled = report.reportType !== "financial_summary" || !isClientScopedReport(report) || !report.printLayout;

        if (report.printLayoutError) {
            showToast(report.printLayoutError, "warning");
        }

        setFeedbackState("ready");
    };

    const clearGeneratedPreview = () => {
        latestGeneratedReport = null;
        reportsPreviewArea.hidden = true;
        reportsSummaryCards.innerHTML = "";
        reportsPreviewHead.innerHTML = "";
        reportsPreviewBody.innerHTML = "";
        reportsPreviewMeta.innerHTML = "";
        clearLedgerPreview();
        setGenerationTag("Not generated");
        if (reportsDownloadButton) {
            reportsDownloadButton.disabled = true;
        }
        reportsPrintButton.disabled = true;
    };

    const syncUrlFromFilters = (filters, options = {}) => {
        if (!window.history || typeof window.history.replaceState !== "function") {
            return;
        }

        const forceScope = Boolean(options.forceScope);
        const nextUrl = new URL(window.location.href);
        nextUrl.searchParams.set("report_type", filters.reportType);
        nextUrl.searchParams.set("date_from", filters.dateFrom);
        nextUrl.searchParams.set("date_to", filters.dateTo);

        if (Number.isFinite(filters.clientId) && filters.clientId > 0) {
            nextUrl.searchParams.set("client_id", String(filters.clientId));
        } else {
            nextUrl.searchParams.delete("client_id");
        }

        if (forceScope) {
            nextUrl.searchParams.set(FORCE_SCOPE_PARAM, "1");
        } else {
            nextUrl.searchParams.delete(FORCE_SCOPE_PARAM);
        }

        window.history.replaceState({}, "", `${nextUrl.pathname}${nextUrl.search}`);
    };

    const buildAnalyticsSummaryUrl = (clientId) => {
        const baseUrl = String(urls.analyticsSummaryApi || "");
        if (!baseUrl) {
            return "";
        }

        if (!Number.isFinite(clientId) || clientId <= 0) {
            return baseUrl;
        }

        const query = new URLSearchParams();
        query.set("client_id", String(clientId));
        return `${baseUrl}?${query.toString()}`;
    };

    const buildPrintLayoutUrl = (filters) => {
        const baseUrl = String(urls.reportsPrintLayoutApi || "");
        if (!baseUrl) {
            return "";
        }

        const query = new URLSearchParams();
        query.set("client_id", String(filters.clientId));
        query.set("date_from", String(filters.dateFrom || ""));
        query.set("date_to", String(filters.dateTo || ""));
        return `${baseUrl}?${query.toString()}`;
    };

    const redirectToLogin = () => {
        const nextPath = encodeURIComponent(window.location.pathname + window.location.search);
        const loginUrl = String(urls.loginPage || "/login/");
        window.location.assign(`${loginUrl}?next=${nextPath}`);
    };

    const fetchJsonOrThrow = async (url, signal, fallbackErrorMessage) => {
        if (!url) {
            throw new Error(fallbackErrorMessage || "Required API URL is missing.");
        }

        const response = await fetch(url, {
            method: "GET",
            headers: {
                Accept: "application/json",
            },
            credentials: "same-origin",
            signal,
        });

        if (response.status === 401) {
            redirectToLogin();
            throw new Error("Authentication required.");
        }

        const payload = await parseJsonSafe(response);
        if (!response.ok || !payload || !payload.ok) {
            const message = payload && payload.message
                ? String(payload.message)
                : String(fallbackErrorMessage || "Request failed.");
            throw new Error(message);
        }

        return payload;
    };

    const readPendingLastClientId = () => {
        try {
            const rawValue = window.localStorage.getItem(PENDING_LAST_CLIENT_KEY) || "";
            if (!rawValue) {
                return null;
            }

            const parsedValue = Number.parseInt(rawValue, 10);
            if (!Number.isFinite(parsedValue) || parsedValue <= 0) {
                return null;
            }

            return parsedValue;
        } catch (error) {
            return null;
        }
    };

    const storePendingLastClientId = (clientId) => {
        try {
            window.localStorage.setItem(PENDING_LAST_CLIENT_KEY, String(clientId));
        } catch (error) {
            // Ignore storage errors to keep reports responsive.
        }
    };

    const clearPendingLastClientId = () => {
        try {
            window.localStorage.removeItem(PENDING_LAST_CLIENT_KEY);
        } catch (error) {
            // Ignore storage errors to keep reports responsive.
        }
    };

    const sendLastUsedClient = async (clientId) => {
        if (!workspaceDefaultsUrl) {
            return false;
        }

        const csrfToken = getCookieValue("csrftoken");
        const headers = {
            Accept: "application/json",
            "Content-Type": "application/json",
        };
        if (csrfToken) {
            headers["X-CSRFToken"] = csrfToken;
        }

        try {
            const response = await fetch(workspaceDefaultsUrl, {
                method: "POST",
                headers,
                credentials: "same-origin",
                keepalive: true,
                body: JSON.stringify({
                    last_client_id: clientId,
                }),
            });

            return response.ok;
        } catch (error) {
            return false;
        }
    };

    const syncPendingLastClient = async () => {
        const pendingId = readPendingLastClientId();
        if (!pendingId) {
            return null;
        }

        const success = await sendLastUsedClient(pendingId);
        if (success) {
            clearPendingLastClientId();
        }

        return pendingId;
    };

    const fetchWorkspaceDefaults = async () => {
        if (!workspaceDefaultsUrl) {
            return null;
        }

        try {
            const response = await fetch(workspaceDefaultsUrl, {
                method: "GET",
                headers: {
                    Accept: "application/json",
                },
                credentials: "same-origin",
            });

            if (response.status === 401) {
                redirectToLogin();
                return null;
            }

            const payload = await parseJsonSafe(response);
            if (!response.ok || !payload || !payload.ok) {
                throw new Error(payload && payload.message ? String(payload.message) : "Unable to load workspace defaults.");
            }

            return payload.defaults || null;
        } catch (error) {
            showToast("Workspace defaults could not be loaded. Using standard defaults.", "warning");
            return null;
        }
    };

    const updateLastUsedClient = async (clientId) => {
        const safeClientId = safeNumber(clientId);
        if (!Number.isFinite(safeClientId) || safeClientId <= 0) {
            return;
        }

        if (workspaceDefaults && typeof workspaceDefaults === "object") {
            workspaceDefaults.last_client_id = safeClientId;
        }

        storePendingLastClientId(safeClientId);
        const success = await sendLastUsedClient(safeClientId);
        if (success) {
            clearPendingLastClientId();
        }
    };

    const buildFinancialSummaryReport = (payload, filters) => {
        const summary = payload && payload.summary ? payload.summary : {};
        const trendRows = Array.isArray(payload && payload.monthly_trend)
            ? payload.monthly_trend.filter((row) => isTrendMonthWithinRange(row.year, row.month, filters))
            : [];

        const rawTypeColumns = Array.isArray(payload && payload.type_columns)
            ? payload.type_columns.filter((value) => String(value || "").trim())
            : [];
        const typeColumns = window.SafeBooksReportsShared && typeof window.SafeBooksReportsShared.normalizeFinancialSummaryColumns === "function"
            ? window.SafeBooksReportsShared.normalizeFinancialSummaryColumns(rawTypeColumns)
            : rawTypeColumns;
        const typeColumnMeta = typeColumns.map((label, index) => ({
            key: `type_${index}`,
            label: String(label),
        }));
        const useTypeColumns = typeColumnMeta.length > 0;

        const getTypeAmount = (typeBreakdown, label) => {
            const normalizedLabel = String(label || "").trim().toLowerCase();
            if (!normalizedLabel) {
                return 0;
            }

            const directMatch = typeBreakdown && Object.prototype.hasOwnProperty.call(typeBreakdown, label)
                ? Number(typeBreakdown[label] || 0)
                : null;
            if (Number.isFinite(directMatch)) {
                return directMatch;
            }

            const fallbackKey = Object.keys(typeBreakdown || {}).find((key) => String(key || "").trim().toLowerCase() === normalizedLabel);
            return Number(typeBreakdown && fallbackKey ? typeBreakdown[fallbackKey] : 0);
        };

        const scope = payload && payload.scope ? payload.scope : {};
        const scopeLabel = Number.isFinite(filters.clientId) && filters.clientId > 0
            ? buildScopeLabel(filters.clientId, String(scope.client_name || "Selected client"))
            : "All clients";

        const rows = trendRows.map((row) => {
            const periodLabel = `${row.month_label || row.month || "-"} ${row.year || ""}`.trim();
            const typeBreakdown = row && row.type_breakdown ? row.type_breakdown : {};
            const salesValue = useTypeColumns
                ? getTypeAmount(typeBreakdown, "Sales")
                : Number(row.sales || 0);
            const expensesValue = useTypeColumns
                ? getTypeAmount(typeBreakdown, "Expenses")
                : Number(row.expenses || 0);
            const netValue = salesValue - expensesValue;
            if (!useTypeColumns) {
                return {
                    period: periodLabel,
                    sales: formatCurrency(salesValue),
                    expenses: formatCurrency(expensesValue),
                    tax: formatCurrency(row.tax),
                    net_value: formatCurrency(netValue),
                };
            }

            const typeValues = {};
            typeColumnMeta.forEach((column) => {
                typeValues[column.key] = formatCurrency(typeBreakdown[column.label]);
            });

            return {
                period: periodLabel,
                ...typeValues,
                net_value: formatCurrency(netValue),
            };
        });

        return {
            reportType: filters.reportType,
            reportLabel: toReportTypeLabel(filters.reportType),
            hint: toReportTypeHint(filters.reportType),
            dateFrom: filters.dateFrom,
            dateTo: filters.dateTo,
            generatedAt: new Date().toISOString(),
            clientId: Number.isFinite(filters.clientId) && filters.clientId > 0 ? filters.clientId : "all",
            scopeLabel,
            summaryCards: [
                {
                    label: "Total Sales",
                    value: formatCurrency(summary.total_sales),
                    note: "For selected scope",
                    icon: "bi-cash-stack",
                },
                {
                    label: "Total Expenses",
                    value: formatCurrency(summary.total_expenses),
                    note: "For selected scope",
                    icon: "bi-wallet2",
                },
                {
                    label: "Total Tax",
                    value: formatCurrency(summary.total_tax),
                    note: "For selected scope",
                    icon: "bi-receipt",
                },
                {
                    label: "Net Value",
                    value: formatCurrency(summary.net_value),
                    note: "Sales minus expenses",
                    icon: "bi-graph-up-arrow",
                },
            ],
            columns: useTypeColumns
                ? [
                    { key: "period", label: "Period" },
                    ...typeColumnMeta,
                    { key: "net_value", label: "Net Value" },
                ]
                : [
                    { key: "period", label: "Period" },
                    { key: "sales", label: "Sales" },
                    { key: "expenses", label: "Expenses" },
                    { key: "tax", label: "Tax" },
                    { key: "net_value", label: "Net Value" },
                ],
            rows,
        };
    };

    const buildComplianceSnapshotReport = (payload, filters) => {
        const activityRows = filterActivityRows(payload && payload.recent_client_activity, filters);

        const filedCount = activityRows.filter((row) => String(row.compliance || "").toLowerCase() === "filed").length;
        const pendingCount = activityRows.filter((row) => String(row.compliance || "").toLowerCase() === "pending").length;
        const lateCount = activityRows.filter((row) => String(row.compliance || "").toLowerCase() === "late").length;

        const scopeLabel = Number.isFinite(filters.clientId) && filters.clientId > 0
            ? buildScopeLabel(filters.clientId, "Selected client")
            : "All clients";

        const rows = activityRows.map((row) => {
            return {
                client_name: String(row.client_name || "Client"),
                tin_number: row.tin_number ? formatTin(row.tin_number) : "-",
                compliance: toComplianceLabel(row.compliance),
                last_entry_date: formatIsoDateForDisplay(row.last_entry_date),
                current_period: String(row.current_period || "-"),
                remarks: toRemarkLabel(row.remarks),
            };
        });

        return {
            reportType: filters.reportType,
            reportLabel: toReportTypeLabel(filters.reportType),
            hint: toReportTypeHint(filters.reportType),
            dateFrom: filters.dateFrom,
            dateTo: filters.dateTo,
            generatedAt: new Date().toISOString(),
            clientId: Number.isFinite(filters.clientId) && filters.clientId > 0 ? filters.clientId : "all",
            scopeLabel,
            summaryCards: [
                {
                    label: "Filed",
                    value: formatCount(filedCount),
                    note: "Clients marked filed",
                    icon: "bi-patch-check",
                },
                {
                    label: "Pending",
                    value: formatCount(pendingCount),
                    note: "Requires follow-up",
                    icon: "bi-hourglass-split",
                },
                {
                    label: "Late",
                    value: formatCount(lateCount),
                    note: "No recent submission",
                    icon: "bi-clock-history",
                },
                {
                    label: "Needs Attention",
                    value: formatCount(pendingCount + lateCount),
                    note: "Pending and late combined",
                    icon: "bi-exclamation-triangle",
                },
            ],
            columns: [
                { key: "client_name", label: "Client Name" },
                { key: "tin_number", label: "TIN" },
                { key: "compliance", label: "Compliance" },
                { key: "last_entry_date", label: "Last Entry Date" },
                { key: "current_period", label: "Current Period" },
                { key: "remarks", label: "Remarks" },
            ],
            rows,
        };
    };

    const buildClientRemarksOverviewReport = (payload, filters) => {
        const activityRows = filterActivityRows(payload && payload.recent_client_activity, filters);

        const newCount = activityRows.filter((row) => String(row.remarks || "").toLowerCase() === "new").length;
        const activeCount = activityRows.filter((row) => String(row.remarks || "").toLowerCase() === "active").length;
        const separatedCount = activityRows.filter((row) => String(row.remarks || "").toLowerCase() === "separated").length;
        const closedCount = activityRows.filter((row) => String(row.remarks || "").toLowerCase() === "closed").length;

        const totalRows = activityRows.length;

        const scopeLabel = Number.isFinite(filters.clientId) && filters.clientId > 0
            ? buildScopeLabel(filters.clientId, "Selected client")
            : "All clients";

        const rows = activityRows
            .slice()
            .sort((a, b) => {
                const remarksOrder = {
                    new: 0,
                    active: 1,
                    separated: 2,
                    closed: 3,
                };
                const aRemarks = String(a.remarks || "new").toLowerCase();
                const bRemarks = String(b.remarks || "new").toLowerCase();
                const aOrder = Object.prototype.hasOwnProperty.call(remarksOrder, aRemarks) ? remarksOrder[aRemarks] : 1;
                const bOrder = Object.prototype.hasOwnProperty.call(remarksOrder, bRemarks) ? remarksOrder[bRemarks] : 1;
                if (aOrder !== bOrder) {
                    return aOrder - bOrder;
                }

                const aName = String(a.client_name || "").toLowerCase();
                const bName = String(b.client_name || "").toLowerCase();
                return aName.localeCompare(bName);
            })
            .map((row) => {
                return {
                    client_name: String(row.client_name || "Client"),
                    tin_number: row.tin_number ? formatTin(row.tin_number) : "-",
                    remarks: toRemarkLabel(row.remarks),
                    compliance: toComplianceLabel(row.compliance),
                    last_entry_date: formatIsoDateForDisplay(row.last_entry_date),
                    current_period: String(row.current_period || "-"),
                };
            });

        return {
            reportType: filters.reportType,
            reportLabel: toReportTypeLabel(filters.reportType),
            hint: toReportTypeHint(filters.reportType),
            dateFrom: filters.dateFrom,
            dateTo: filters.dateTo,
            generatedAt: new Date().toISOString(),
            clientId: Number.isFinite(filters.clientId) && filters.clientId > 0 ? filters.clientId : "all",
            scopeLabel,
            summaryCards: [
                {
                    label: "New",
                    value: formatCount(newCount),
                    note: "Newly onboarded clients",
                    icon: "bi-star",
                },
                {
                    label: "Active",
                    value: formatCount(activeCount),
                    note: "Regular filing activity",
                    icon: "bi-shield-check",
                },
                {
                    label: "Separated",
                    value: formatCount(separatedCount),
                    note: "No current year activity",
                    icon: "bi-shield",
                },
                {
                    label: "Closed",
                    value: formatCount(closedCount),
                    note: "Business closed",
                    icon: "bi-shield-slash",
                },
            ],
            columns: [
                { key: "client_name", label: "Client Name" },
                { key: "tin_number", label: "TIN" },
                { key: "remarks", label: "Remarks" },
                { key: "compliance", label: "Compliance" },
                { key: "last_entry_date", label: "Last Entry Date" },
                { key: "current_period", label: "Current Period" },
            ],
            rows,
        };
    };

    let activeDropdownFocusIndex = -1;

    const renderCustomDropdown = (query) => {
        const dropdown = document.getElementById("reportsCustomDropdown");
        if (!dropdown) return;

        dropdown.innerHTML = "";
        activeDropdownFocusIndex = -1;

        const cleanQuery = String(query || "").trim().toLowerCase();
        let filtered = [];

        if (!cleanQuery) {
            filtered = availableClients;
        } else {
            const cleanDigits = cleanQuery.replace(/\D+/g, "");
            filtered = availableClients.filter((client) => {
                const nameMatch = String(client.client_name || "").toLowerCase().includes(cleanQuery);
                const tinMatch = cleanDigits && String(client.tin_number || "").replace(/\D+/g, "").includes(cleanDigits);
                return nameMatch || tinMatch;
            });
        }

        const currentSelectedValue = reportsClientSelect ? reportsClientSelect.value : "all";

        // "All Clients" Option
        const allItem = document.createElement("div");
        allItem.className = "reports-custom-dropdown-item";
        allItem.dataset.id = "all";
        if (currentSelectedValue === "all") {
            allItem.classList.add("is-active");
        }
        allItem.innerHTML = `<span>All Clients</span><span class="item-tin">Reset filter</span>`;
        dropdown.appendChild(allItem);

        filtered.forEach((client) => {
            if (client.remarks === "closed") {
                return;
            }
            const item = document.createElement("div");
            item.className = "reports-custom-dropdown-item";
            item.dataset.id = String(client.id);
            if (String(client.id) === currentSelectedValue) {
                item.classList.add("is-active");
            }
            const clientName = String(client.client_name || "Client");
            const clientTin = String(client.tin_number || "").trim();
            item.innerHTML = `<span>${escapeHtml(clientName)}</span>${clientTin ? `<span class="item-tin">TIN: ${formatTin(clientTin)}</span>` : ""}`;
            dropdown.appendChild(item);
        });

        if (filtered.length === 0 && cleanQuery) {
            const emptyItem = document.createElement("div");
            emptyItem.className = "reports-custom-dropdown-empty";
            emptyItem.textContent = "No matching clients found";
            dropdown.appendChild(emptyItem);
        }

        // Click Events
        const items = dropdown.querySelectorAll(".reports-custom-dropdown-item");
        items.forEach((item) => {
            item.addEventListener("click", () => {
                const selectedVal = item.dataset.id;
                if (reportsClientSelect) {
                    reportsClientSelect.value = selectedVal;
                    reportsClientSelect.dispatchEvent(new Event("change"));
                }
                hideCustomDropdown();
            });
        });
    };

    const showCustomDropdown = () => {
        const dropdown = document.getElementById("reportsCustomDropdown");
        const toggleIcon = document.getElementById("reportsDropdownToggleIcon");
        if (!dropdown) return;

        renderCustomDropdown(reportsClientSearchInput ? reportsClientSearchInput.value : "");
        dropdown.style.display = "block";
        
        if (toggleIcon) {
            toggleIcon.style.transform = "translateY(-50%) rotate(180deg)";
        }
    };

    const hideCustomDropdown = () => {
        const dropdown = document.getElementById("reportsCustomDropdown");
        const toggleIcon = document.getElementById("reportsDropdownToggleIcon");
        if (dropdown) {
            dropdown.style.display = "none";
        }
        if (toggleIcon) {
            toggleIcon.style.transform = "translateY(-50%)";
        }
        activeDropdownFocusIndex = -1;
    };

    const updateDropdownFocus = (items) => {
        items.forEach((item, idx) => {
            if (idx === activeDropdownFocusIndex) {
                item.classList.add("is-focused");
                item.scrollIntoView({ block: "nearest" });
            } else {
                item.classList.remove("is-focused");
            }
        });
    };

    const syncSearchInputForClientId = (clientId) => {
        if (!reportsClientSearchInput) {
            return;
        }

        const matchedClient = availableClients.find((c) => String(c.id) === String(clientId));
        reportsClientSearchInput.value = matchedClient && matchedClient.tin_number
            ? formatTin(matchedClient.tin_number)
            : "";
    };

    const loadOptionsAndClients = async () => {
        reportsClientSelect.disabled = true;

        try {
            const result = await fetchJsonOrThrow(
                String(urls.clientsApi || ""),
                undefined,
                "Unable to load clients list."
            );

            availableClients = Array.isArray(result.clients)
                ? result.clients.map((client) => ({
                    id: safeNumber(client.id),
                    client_name: String(client.client_name || "Client"),
                    tin_number: String(client.tin_number || ""),
                    trade_name: String(client.trade_name || ""),
                    location: String(client.location || ""),
                    permit_number: String(client.permit_number || ""),
                    birthday: String(client.birthday || ""),
                    email: String(client.email || ""),
                    email_password: String(client.email_password || ""),
                    orus_account: String(client.orus_account || ""),
                    orus_password: String(client.orus_password || ""),
                    custom_fields: Array.isArray(client.custom_fields) ? client.custom_fields : [],
                    remarks: String(client.remarks || "new"),
                }))
                : [];
        } catch (error) {
            availableClients = [];
            showToast("Clients list could not be loaded. All-clients scope is still available.", "warning");
        }

        reportsClientSelect.innerHTML = "";

        const allOption = document.createElement("option");
        allOption.value = "all";
        allOption.textContent = "All clients";
        reportsClientSelect.appendChild(allOption);

        availableClients.forEach((client) => {
            if (client.remarks === "closed") {
                return; // EXCLUDE closed clients from reports page scope select!
            }
            const optionElement = document.createElement("option");
            optionElement.value = String(client.id);
            const tin = String(client.tin_number || "").trim();
            optionElement.textContent = tin
                ? `${client.client_name} (TIN: ${formatTin(tin)})`
                : client.client_name;
            reportsClientSelect.appendChild(optionElement);
        });

        reportsClientSelect.disabled = false;
        renderCustomDropdown("");
    };

    const applyInitialFilterValues = (defaults) => {
        applyDefaultsToFilters(defaults);

        const queryParams = new URLSearchParams(window.location.search);
        const forceScopeValue = String(queryParams.get(FORCE_SCOPE_PARAM) || "")
            .trim()
            .toLowerCase();
        const shouldRespectUrl = forceScopeValue === "1"
            || forceScopeValue === "true"
            || forceScopeValue === "yes";
        if (!shouldRespectUrl) {
            const defaultsFilters = collectFilters();
            syncUrlFromFilters(defaultsFilters, { forceScope: false });
            return;
        }
        const initialReportType = String(queryParams.get("report_type") || "").trim();
        const initialClientId = String(queryParams.get("client_id") || "").trim();
        const initialDateFrom = String(queryParams.get("date_from") || "").trim();
        const initialDateTo = String(queryParams.get("date_to") || "").trim();

        if (REPORT_TYPE_META[initialReportType]) {
            reportsTypeSelect.value = initialReportType;
        }

        if (parseDateInput(initialDateFrom)) {
            reportsDateFrom.value = initialDateFrom;
        }

        if (parseDateInput(initialDateTo)) {
            reportsDateTo.value = initialDateTo;
        }

        if (initialClientId) {
            const optionExists = Array.from(reportsClientSelect.options)
                .some((optionItem) => optionItem.value === initialClientId);
            if (optionExists) {
                reportsClientSelect.value = initialClientId;
            }
        }
        syncSearchInputForClientId(reportsClientSelect.value);
    };

    const shouldAutoGenerate = () => {
        const queryParams = new URLSearchParams(window.location.search);
        const autoValue = String(queryParams.get("auto_generate") || "").trim().toLowerCase();
        return autoValue === "1" || autoValue === "true" || autoValue === "yes";
    };

    const runReportGeneration = async (options = {}) => {
        const focusAfterGenerate = Boolean(options.focusAfterGenerate);
        const filters = collectFilters();
        const validationMessage = validateFilters(filters);

        if (validationMessage) {
            setFeedbackState("error", validationMessage);
            setFilterStatus(validationMessage);
            showToast(validationMessage, "warning");
            return;
        }

        const requestToken = ++generationRequestToken;
        if (generationAbortController) {
            generationAbortController.abort();
        }
        generationAbortController = new AbortController();

        setActionLoadingState(true);
        setFeedbackState("loading");
        setFilterStatus("Generating report...");

        try {
            let generatedReport = null;

            if (filters.reportType === "financial_summary") {
                const analyticsPayload = await fetchJsonOrThrow(
                    buildAnalyticsSummaryUrl(filters.clientId),
                    generationAbortController.signal,
                    "Unable to load analytics data for financial summary."
                );
                if (requestToken !== generationRequestToken) {
                    return;
                }
                generatedReport = buildFinancialSummaryReport(analyticsPayload, filters);
            } else if (filters.reportType === "compliance_snapshot") {
                const dashboardPayload = await fetchJsonOrThrow(
                    String(urls.dashboardSummaryApi || ""),
                    generationAbortController.signal,
                    "Unable to load compliance snapshot data."
                );
                if (requestToken !== generationRequestToken) {
                    return;
                }
                generatedReport = buildComplianceSnapshotReport(dashboardPayload, filters);
            } else if (filters.reportType === "client_remarks_overview") {
                const dashboardPayload = await fetchJsonOrThrow(
                    String(urls.dashboardSummaryApi || ""),
                    generationAbortController.signal,
                    "Unable to load remarks overview data."
                );
                if (requestToken !== generationRequestToken) {
                    return;
                }
                generatedReport = buildClientRemarksOverviewReport(dashboardPayload, filters);
            } else {
                throw new Error("Unsupported report type selected.");
            }

            if (!generatedReport) {
                throw new Error("Report generation returned no payload.");
            }

            generatedReport.printLayout = null;
            generatedReport.printLayoutError = "";

            if (Number.isFinite(filters.clientId) && filters.clientId > 0) {
                generatedReport.printLayout = buildPrintLayoutDefinition(generatedReport);
            }

            renderGeneratedReport(generatedReport);
            appendHistoryItem(generatedReport);
            syncUrlFromFilters(filters, { forceScope: false });

            if (generatedReport.rows.length === 0) {
                setFilterStatus("Report generated, but no rows matched this date range.");
                showToast("Report generated with no matching rows. Try widening the date range.", "info");
            } else {
                showToast(`${generatedReport.reportLabel} generated successfully.`, "success");
            }

            if (focusAfterGenerate) {
                reportsPreviewArea.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        } catch (error) {
            if (error && error.name === "AbortError") {
                return;
            }

            if (requestToken !== generationRequestToken) {
                return;
            }

            const fallbackMessage = "Unable to generate report right now. Please try again.";
            const errorMessage = error && error.message ? String(error.message) : fallbackMessage;

            setFeedbackState("error", errorMessage);
            setFilterStatus(errorMessage);
            showToast(errorMessage, "danger");
        } finally {
            if (requestToken === generationRequestToken) {
                setActionLoadingState(false);
            }
        }
    };

    const previewLatestReport = () => {
        if (!latestGeneratedReport) {
            runReportGeneration({ focusAfterGenerate: true });
            return;
        }

        reportsPreviewArea.hidden = false;
        reportsPreviewArea.scrollIntoView({ behavior: "smooth", block: "start" });
        reportsPreviewTable.focus({ preventScroll: true });
    };

    const resetReportFiltersAndState = () => {
        applyDefaultsToFilters(workspaceDefaults);

        clearGeneratedPreview();
        setFeedbackState("empty");
        setFilterStatus("Filters reset. Select Generate to build a new report.");

        const filters = collectFilters();
        syncUrlFromFilters(filters, { forceScope: false });
    };

    const bindCoreEvents = () => {
        reportsFilterForm.addEventListener("submit", (event) => {
            event.preventDefault();
            runReportGeneration({ focusAfterGenerate: false });
        });

        reportsPreviewButton.addEventListener("click", () => {
            previewLatestReport();
        });

        if (reportsDownloadButton) {
            reportsDownloadButton.addEventListener("click", () => {
                if (!latestGeneratedReport) {
                    showToast("Generate a report before downloading.", "warning");
                    return;
                }
                downloadCsv(latestGeneratedReport);
                showToast("CSV download started.", "success");
            });
        }

        reportsPrintButton.addEventListener("click", () => {
            printLedgerLayout();
        });

        reportsResetButton.addEventListener("click", () => {
            resetReportFiltersAndState();
        });

        if (reportsRetryButton) {
            reportsRetryButton.addEventListener("click", () => {
                runReportGeneration({ focusAfterGenerate: false });
            });
        }

        if (reportsEmptyAdjustButton) {
            reportsEmptyAdjustButton.addEventListener("click", () => {
                reportsTypeSelect.focus();
                reportsFilterForm.scrollIntoView({ behavior: "smooth", block: "center" });
            });
        }

        if (reportsTypeSelect) {
            reportsTypeSelect.addEventListener("change", () => {
                const selectedType = String(reportsTypeSelect.value || "").trim();
                setFilterStatus(`${toReportTypeLabel(selectedType)} selected. Ready to generate.`);
            });
        }

        if (reportsClientSelect) {
            reportsClientSelect.addEventListener("change", () => {
                const selectedValue = String(reportsClientSelect.value || "").trim();
                const clientId = selectedValue === "all" ? null : safeNumber(selectedValue);
                if (Number.isFinite(clientId) && clientId > 0) {
                    updateLastUsedClient(clientId);
                }
                syncSearchInputForClientId(selectedValue);
            });
        }

        if (reportsClientSearchInput) {
            reportsClientSearchInput.addEventListener("focus", () => {
                showCustomDropdown();
            });

            reportsClientSearchInput.addEventListener("input", () => {
                showCustomDropdown();
            });

            reportsClientSearchInput.addEventListener("keydown", (event) => {
                const dropdown = document.getElementById("reportsCustomDropdown");
                if (dropdown && dropdown.style.display === "block") {
                    const items = Array.from(dropdown.querySelectorAll(".reports-custom-dropdown-item"));
                    if (items.length > 0) {
                        if (event.key === "ArrowDown") {
                            event.preventDefault();
                            activeDropdownFocusIndex = (activeDropdownFocusIndex + 1) % items.length;
                            updateDropdownFocus(items);
                            return;
                        }
                        if (event.key === "ArrowUp") {
                            event.preventDefault();
                            activeDropdownFocusIndex = (activeDropdownFocusIndex - 1 + items.length) % items.length;
                            updateDropdownFocus(items);
                            return;
                        }
                        if (event.key === "Enter") {
                            if (activeDropdownFocusIndex >= 0 && activeDropdownFocusIndex < items.length) {
                                event.preventDefault();
                                items[activeDropdownFocusIndex].click();
                                return;
                            }
                        }
                        if (event.key === "Escape") {
                            event.preventDefault();
                            hideCustomDropdown();
                            return;
                        }
                    }
                }
            });
        }

        const toggleIcon = document.getElementById("reportsDropdownToggleIcon");
        if (toggleIcon) {
            toggleIcon.addEventListener("click", (event) => {
                event.stopPropagation();
                const dropdown = document.getElementById("reportsCustomDropdown");
                if (dropdown && dropdown.style.display === "block") {
                    hideCustomDropdown();
                } else {
                    if (reportsClientSearchInput) {
                        reportsClientSearchInput.focus();
                    }
                    showCustomDropdown();
                }
            });
        }

        document.addEventListener("click", (event) => {
            const searchWrap = document.querySelector(".reports-tin-search-input-wrap");
            if (searchWrap && !searchWrap.contains(event.target)) {
                hideCustomDropdown();
            }
        });

        reportsHistoryList.addEventListener("click", (event) => {
            const trigger = event.target.closest("button[data-history-id]");
            if (!trigger) {
                return;
            }

            const targetId = String(trigger.dataset.historyId || "").trim();
            if (!targetId) {
                return;
            }

            const matchedItem = readHistoryItems().find((item) => String(item.id || "") === targetId);
            if (!matchedItem) {
                return;
            }

            applyHistoryFilterItem(matchedItem);
            runReportGeneration({ focusAfterGenerate: true });
        });

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

        plannedFeatureButtons.forEach((buttonElement) => {
            buttonElement.addEventListener("click", (event) => {
                event.preventDefault();
                const featureLabel = String(buttonElement.dataset.plannedFeature || "This feature").trim();
                showToast(`${featureLabel} is planned and will be available soon.`);
            });
        });

        window.addEventListener("resize", () => {
            sidebarState.closeMobileSidebar();
            sidebarState.restoreDesktopState();
        });
    };

    let availableClients = [];
    let workspaceDefaults = null;
    let latestGeneratedReport = null;
    let generationRequestToken = 0;
    let generationAbortController = null;

    const initializeReportsPage = async () => {
        sidebarState.restoreDesktopState();
        hydrateHeaderUser();

        clearGeneratedPreview();
        setFeedbackState("empty");
        setFilterStatus("Set filters then select Generate to prepare your report.");
        setActionLoadingState(false);

        renderHistoryItems(readHistoryItems());

        await loadOptionsAndClients();
        workspaceDefaults = await fetchWorkspaceDefaults();
        const pendingClientId = await syncPendingLastClient();
        if (pendingClientId && workspaceDefaults && typeof workspaceDefaults === "object") {
            workspaceDefaults.last_client_id = pendingClientId;
        }
        applyInitialFilterValues(workspaceDefaults);

        const initialFilters = collectFilters();
        if (Number.isFinite(initialFilters.clientId) && initialFilters.clientId > 0) {
            updateLastUsedClient(initialFilters.clientId);
        }

        bindCoreEvents();

        if (shouldAutoGenerate()) {
            runReportGeneration({ focusAfterGenerate: true });
        }
    };

    initializeReportsPage();
})();
