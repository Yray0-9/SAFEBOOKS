(function () {
    const toDisplayText = (value, fallback = "-") => {
        const trimmedValue = String(value == null ? "" : value).trim();
        return trimmedValue ? trimmedValue : fallback;
    };

    const escapeHtml = (value) => {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    const toColumnLabel = (column) => {
        if (typeof column === "string") {
            return column;
        }

        if (column && typeof column === "object") {
            return String(column.label || column.key || "");
        }

        return "";
    };

    const currencyFormatter = new Intl.NumberFormat("en-PH", {
        style: "currency",
        currency: "PHP",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });

    const formatCurrency = (value) => {
        const parsedValue = Number.isFinite(value) ? value : 0;
        return currencyFormatter.format(parsedValue);
    };

    const parseNumericValue = (value) => {
        if (typeof value === "number" && Number.isFinite(value)) {
            return value;
        }

        const cleaned = String(value || "").replace(/[^0-9.-]/g, "");
        if (!cleaned) {
            return null;
        }

        const parsed = Number.parseFloat(cleaned);
        return Number.isFinite(parsed) ? parsed : null;
    };

    const shouldIncludeTotalsRow = (columns) => {
        if (!Array.isArray(columns) || columns.length < 2) {
            return false;
        }

        const firstLabel = String(columns[0] || "").toLowerCase();
        if (/period|month/.test(firstLabel)) {
            return true;
        }

        return columns.some((label) => /net\s*value|sales|expenses|tax/i.test(String(label || "")));
    };

    const normalizeFinancialSummaryColumns = (columns) => {
        const normalizedColumns = Array.isArray(columns) ? columns : [];
        const priority = {
            period: 0,
            sales: 1,
            expenses: 2,
            tax: 3,
            netvalue: 4,
            net_value: 4,
        };

        const toSortKey = (label) => {
            const text = String(label || "").trim();
            const compact = text.toLowerCase().replace(/[^a-z0-9]+/g, "");
            const matchedPriority = priority[compact];
            return Number.isFinite(matchedPriority) ? matchedPriority : 50;
        };

        const periodColumns = [];
        const salesColumns = [];
        const expenseColumns = [];
        const taxColumns = [];
        const otherColumns = [];
        const netColumns = [];

        normalizedColumns.forEach((column) => {
            const label = toColumnLabel(column);
            const compact = String(label || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "");

            if (!label) {
                return;
            }

            if (/^period|month$/.test(compact)) {
                periodColumns.push(column);
                return;
            }

            if (compact === "sales") {
                salesColumns.push(column);
                return;
            }

            if (compact === "expenses") {
                expenseColumns.push(column);
                return;
            }

            if (compact === "tax") {
                taxColumns.push(column);
                return;
            }

            if (compact === "netvalue" || compact === "net_value") {
                netColumns.push(column);
                return;
            }

            otherColumns.push({ column, sortKey: toSortKey(label), label: label.toLowerCase() });
        });

        otherColumns.sort((left, right) => {
            if (left.sortKey !== right.sortKey) {
                return left.sortKey - right.sortKey;
            }

            return left.label.localeCompare(right.label);
        });

        return [
            ...periodColumns,
            ...salesColumns,
            ...expenseColumns,
            ...taxColumns,
            ...otherColumns.map((entry) => entry.column),
            ...netColumns,
        ];
    };

    const buildWorksheetTable = (transactionRows, { yearFilter, classifyLine }) => {
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const supportingKeys = ["mict", "cogs_cos", "income_payments_2307", "tax_withheld"];
        const periods = new Map();
        const present = (value) => value !== null && value !== undefined && String(value).trim() !== "";
        const displayAmount = (value) => present(value) ? formatCurrency(Number(value)) : "";
        (Array.isArray(transactionRows) ? transactionRows : []).forEach((line) => {
            if (!line || typeof line !== "object") return;
            const date = String(line.entry_date || "").match(/^(\d{4})-(\d{2})-\d{2}$/);
            if (!date || Number(date[2]) < 1 || Number(date[2]) > 12 || (yearFilter !== "all" && date[1] !== yearFilter)) return;
            const key = `${date[1]}-${date[2]}`;
            if (!periods.has(key)) periods.set(key, { label: `${months[Number(date[2]) - 1]} ${date[1]}`, quarter: String(Math.ceil(Number(date[2]) / 3)), sales: 0, expenses: 0, hasSales: false, hasExpenses: false, details: [], notes: new Set() });
            const period = periods.get(key);
            const category = classifyLine(line.type_code, line.description);
            const amount = Number(line.amount || 0);
            if (category === "sales") {
                period.sales += Number.isFinite(amount) ? amount : 0;
                period.hasSales ||= present(line.amount) && Number.isFinite(amount);
            }
            if (category === "expenses") {
                period.expenses += Number.isFinite(amount) ? amount : 0;
                period.hasExpenses ||= present(line.amount) && Number.isFinite(amount);
            }
            const standard = /^(sales|expenses)$/i.test(String(line.type_code || "").trim());
            // Keep each form's saved supporting values separate. Monthly totals appear only once.
            if (category === "tax" || !standard || supportingKeys.some((key) => present(line[key]))) {
                period.details.push({
                    type_code: line.type_code || "", description: standard ? "" : line.description || "", quarter: period.quarter,
                    ...Object.fromEntries(supportingKeys.map((key) => [key, displayAmount(line[key])])),
                    tax_due: category === "tax" ? displayAmount(line.amount) : "",
                    remarks: line.remarks != null ? line.remarks : line.notes || "",
                    hasOwnRemarks: line.remarks != null,
                });
            } else if (line.notes) period.notes.add(line.notes);
        });
        const rows = [];
        const rowKinds = [];
        Array.from(periods.entries()).sort(([left], [right]) => left.localeCompare(right)).forEach(([, period]) => {
            // Align the first saved tax form with the monthly figures, without repeating those figures on later forms.
            const firstTaxIndex = period.details.findIndex((detail) => detail.tax_due !== "");
            const firstTax = firstTaxIndex >= 0 ? period.details[firstTaxIndex] : {};
            const monthRemarks = new Set(period.notes);
            if (firstTax.remarks) monthRemarks.add(firstTax.remarks);
            rows.push({ ...firstTax, period: period.label, quarter: period.quarter,
                sales: period.hasSales ? formatCurrency(period.sales) : "",
                expenses: period.hasExpenses ? formatCurrency(period.expenses) : "",
                net_value: period.hasSales || period.hasExpenses ? formatCurrency(period.sales - period.expenses) : "",
                remarks: firstTax.hasOwnRemarks ? firstTax.remarks : Array.from(monthRemarks).join("; ") });
            rowKinds.push("month");
            period.details.forEach((detail, index) => {
                if (index === firstTaxIndex) return;
                rows.push(detail);
                rowKinds.push("detail");
            });
        });
        return {
            layout: "worksheet", preserveColumnOrder: true, rowKinds,
            totalColumns: ["Sales", "Expenses", "Net Sales", "Tax Due"],
            columns: [
                { key: "type_code", label: "Type / Code" }, { key: "description", label: "Description" },
                { key: "period", label: "Period" }, { key: "quarter", label: "Quarter" },
                { key: "sales", label: "Sales" }, { key: "mict", label: "MICT" },
                { key: "expenses", label: "Expenses" }, { key: "cogs_cos", label: "COGS / COS" },
                { key: "net_value", label: "Net Sales" }, { key: "income_payments_2307", label: "Income payments (2307)" },
                { key: "tax_withheld", label: "Tax withheld" }, { key: "tax_due", label: "Tax Due" }, { key: "remarks", label: "Remarks" },
            ], rows,
        };
    };

    const buildReportSheetHtml = (options) => {
        const settings = options && typeof options === "object" ? options : {};
        const meta = settings.meta && typeof settings.meta === "object" ? settings.meta : {};
        const table = settings.table && typeof settings.table === "object" ? settings.table : {};
        const client = settings.client && typeof settings.client === "object" ? settings.client : {};

        const reportTitle = toDisplayText(settings.reportTitle, "SafeBooks Client Report Sheet");
        const printedBy = toDisplayText(settings.printedBy, "Bookkeeper User");

        const reportTypeLabel = toDisplayText(meta.reportTypeLabel, "Client Report");
        const dateRangeLabel = toDisplayText(meta.dateRangeLabel, "-");
        const generatedLabel = toDisplayText(meta.generatedLabel, "-");

        const clientName = toDisplayText(client.clientName || client.client_name, "Selected client");
        const clientTin = toDisplayText(client.tin || client.tin_number);
        const tradeName = toDisplayText(client.tradeName || client.trade_name);
        const location = toDisplayText(client.location);
        const permitNumber = toDisplayText(client.permitNumber || client.permit_number);
        const birthday = toDisplayText(client.birthday);
        const email = toDisplayText(client.email);

        const rawCustomFields = Array.isArray(client.custom_fields)
            ? client.custom_fields
            : Array.isArray(client.customFields)
                ? client.customFields
                : [];
        const customFields = rawCustomFields
            .filter((field) => field && typeof field === "object")
            // Passwords must never enter preview or print markup, even if the
            // authorized details page supplies a full client profile.
            .filter((field) => String(field.type || "").trim().toLowerCase() !== "password")
            .filter((field) => !/password|passcode|secret|recovery\s*code/i.test(String(field.label || "")))
            .map((field) => {
                return {
                    label: toDisplayText(field.label, ""),
                    value: toDisplayText(field.value, "-"),
                };
            })
            .filter((field) => field.label || field.value);

        const rawColumns = Array.isArray(table.columns) ? table.columns : [];
        const columns = rawColumns
            .map((column) => toColumnLabel(column))
            .filter((label) => Boolean(String(label || "").trim()));
        const finalColumns = columns.length ? (table.preserveColumnOrder ? columns : normalizeFinancialSummaryColumns(columns)) : ["Details"];
        const worksheet = table.layout === "worksheet";
        const worksheetMoneyColumns = new Set([
            "sales", "mict", "expenses", "cogscos", "netsales", "netvalue",
            "incomepayments2307", "taxwithheld", "taxdue",
        ]);
        const totalColumns = Array.isArray(table.totalColumns) ? new Set(table.totalColumns.map((label) => label.toLowerCase())) : null;

        const rows = Array.isArray(table.rows) ? table.rows : [];
        const minRows = Number.isFinite(table.minRows) ? table.minRows : 14;

        const includeTotals = rows.length > 0 && shouldIncludeTotalsRow(finalColumns);
        let totalsRow = null;

        if (includeTotals) {
            const totals = finalColumns.map(() => 0);
            const hasNumericValues = finalColumns.map(() => false);

            rows.forEach((row) => {
                const rowCells = Array.isArray(row)
                    ? row
                    : finalColumns.map((column) => row[column]);

                rowCells.forEach((cell, index) => {
                    if (index === 0 || (totalColumns && !totalColumns.has(finalColumns[index].toLowerCase()))) {
                        return;
                    }

                    const parsedValue = parseNumericValue(cell);
                    if (parsedValue == null) {
                        return;
                    }

                    totals[index] += parsedValue;
                    hasNumericValues[index] = true;
                });
            });

            if (hasNumericValues.some((value) => value)) {
                totalsRow = finalColumns.map((_, index) => {
                    if (index === 0) {
                        return "Total";
                    }
                    if (!hasNumericValues[index]) {
                        return "-";
                    }
                    return formatCurrency(totals[index]);
                });
            }
        }

        let finalRows = [...rows];
        if (totalsRow) {
            if (rows.length < minRows - 1) {
                const blankPaddingCount = minRows - rows.length - 1;
                for (let i = 0; i < blankPaddingCount; i++) {
                    finalRows.push(null);
                }
                finalRows.push(totalsRow);
            } else {
                finalRows.push(totalsRow);
            }
        }
        const rowCount = Math.max(minRows, finalRows.length);

        const headerMarkup = finalColumns
            .map((label) => `<th scope="col">${escapeHtml(toDisplayText(label, "VALUE"))}</th>`)
            .join("");

        let previousWorksheetQuarter = null;
        const periodColumnIndex = finalColumns.findIndex((column) => column.toLowerCase() === "period");
        const quarterColumnIndex = finalColumns.findIndex((column) => column.toLowerCase() === "quarter");
        const rowsMarkup = Array.from({ length: rowCount }, (_, rowIndex) => {
            const row = finalRows[rowIndex];
            if (!row) {
                return `
                    <tr>
                        ${finalColumns.map(() => "<td>&nbsp;</td>").join("")}
                    </tr>
                `;
            }

            const isTotalsRow = row === totalsRow;
            const rowClass = isTotalsRow ? ' class="reports-ledger-totals-row"' : worksheet && table.rowKinds && table.rowKinds[rowIndex] === "month" ? ' class="reports-worksheet-month-row"' : "";

            const rowCells = Array.isArray(row) ? row : finalColumns.map((column) => row[column]);
            let quarterGap = "";
            if (worksheet && !isTotalsRow && table.rowKinds && table.rowKinds[rowIndex] === "month"
                && periodColumnIndex >= 0 && quarterColumnIndex >= 0) {
                const year = String(rowCells[periodColumnIndex] || "").match(/\b\d{4}$/);
                const quarter = String(rowCells[quarterColumnIndex] || "");
                if (year && /^[1-4]$/.test(quarter)) {
                    const currentQuarter = `${year[0]}-${quarter}`;
                    if (previousWorksheetQuarter !== null && previousWorksheetQuarter !== currentQuarter) {
                        quarterGap = `<tr class="reports-worksheet-quarter-gap" aria-hidden="true">${finalColumns.map(() => "<td>&nbsp;</td>").join("")}</tr>`;
                    }
                    previousWorksheetQuarter = currentQuarter;
                }
            }
            const cellsMarkup = finalColumns
                .map((column, columnIndex) => {
                    // Leave zero amounts writable on the worksheet without changing data or totals.
                    const isWorksheetMoney = worksheet && worksheetMoneyColumns.has(column.toLowerCase().replace(/[^a-z0-9]/g, ""));
                    if (isWorksheetMoney && parseNumericValue(rowCells[columnIndex]) === 0) return "<td></td>";
                    return `<td>${escapeHtml(toDisplayText(rowCells[columnIndex], "-"))}</td>`;
                })
                .join("");

            return `
                ${quarterGap}
                <tr${rowClass}>
                    ${cellsMarkup}
                </tr>
            `;
        }).join("");

        const rowHint = settings.rowHint === "" ? "" : toDisplayText(settings.rowHint, "Prepared from generated report values.");

        const customRowsMarkup = customFields
            .map((field, index) => {
                if (index % 2 !== 0) {
                    return "";
                }

                const leftField = field;
                const rightField = customFields[index + 1];

                const leftLabel = escapeHtml(toDisplayText(leftField.label, ""));
                const leftValue = escapeHtml(toDisplayText(leftField.value, "-"));
                const rightLabel = rightField ? escapeHtml(toDisplayText(rightField.label, "")) : "&nbsp;";
                const rightValue = rightField ? escapeHtml(toDisplayText(rightField.value, "-")) : "&nbsp;";

                return `
                    <tr>
                        <th>${leftLabel}</th>
                        <td>${leftValue}</td>
                        <th>${rightLabel}</th>
                        <td>${rightValue}</td>
                    </tr>
                `;
            })
            .join("");

        return `
            <div class="reports-ledger-heading">
                <h3 class="reports-ledger-title">${escapeHtml(reportTitle)}</h3>
                <p class="reports-ledger-printed-by">Printed by: ${escapeHtml(printedBy)}</p>
            </div>

            <div class="reports-ledger-meta-row">
                <span class="reports-ledger-meta-pill">Type: ${escapeHtml(reportTypeLabel)}</span>
                <span class="reports-ledger-meta-pill">Range: ${escapeHtml(dateRangeLabel)}</span>
                <span class="reports-ledger-meta-pill">Generated: ${escapeHtml(generatedLabel)}</span>
            </div>

            <table class="reports-ledger-client-table" aria-label="Client details">
                <tbody>
                    <tr>
                        <th>TIN</th>
                        <td>${escapeHtml(clientTin)}</td>
                        <th>Trade Name</th>
                        <td>${escapeHtml(tradeName)}</td>
                    </tr>
                    <tr>
                        <th>Taxpayer</th>
                        <td>${escapeHtml(clientName)}</td>
                        <th>Location</th>
                        <td>${escapeHtml(location)}</td>
                    </tr>
                    <tr>
                        <th>Permit No.</th>
                        <td>${escapeHtml(permitNumber)}</td>
                        <th>Birthday</th>
                        <td>${escapeHtml(birthday)}</td>
                    </tr>
                    <tr>
                        <th>Email</th>
                        <td colspan="3">${escapeHtml(email)}</td>
                    </tr>
                    ${customRowsMarkup}
                </tbody>
            </table>

            <div class="reports-ledger-grid-wrap" tabindex="0" role="region" aria-label="Ledger columns">
                <table class="reports-ledger-grid-table${worksheet ? " reports-worksheet-table" : ""}" aria-label="Ledger entries">
                    <thead>
                        <tr>
                            ${headerMarkup}
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsMarkup}
                    </tbody>
                </table>
            </div>

            ${rowHint ? `<p class="reports-ledger-note">${escapeHtml(rowHint)}</p>` : ""}
        `;
    };

    window.SafeBooksReportsShared = {
        buildReportSheetHtml,
        normalizeFinancialSummaryColumns,
        buildWorksheetTable,
    };
})();
