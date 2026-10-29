(function (root) {
    "use strict";
    const labelCleanups = new WeakMap();
    root.SafeBooksForecastPeriods = {
        alignLabels(labels, svg, positions) {
            if (!labels) return;
            labelCleanups.get(labels)?.();
            labelCleanups.delete(labels);
            if (!labels.style) return;
            if (!positions.length) {
                labels.style.height = "";
                return;
            }
            if (!svg?.getBoundingClientRect || !labels.getBoundingClientRect) return;
            const update = () => {
                const chart = svg.getBoundingClientRect();
                const box = labels.getBoundingClientRect();
                if (!chart.width || !box.width) return;
                labels.style.display = "block";
                labels.style.position = "relative";
                const slot = positions.length > 1
                    ? chart.width * (positions[positions.length - 1] - positions[0]) / (positions.length - 1) : chart.width;
                [...labels.children].forEach((label, index) => {
                    const center = chart.left - box.left + positions[index] * chart.width;
                    const edgeWidth = 2 * Math.max(0, Math.min(center, box.width - center));
                    label.style.position = "absolute";
                    label.style.left = `${center}px`;
                    label.style.top = "0";
                    label.style.transform = "translateX(-50%)";
                    label.style.width = `${Math.max(Math.min(slot * 0.94, 96, edgeWidth), 1)}px`;
                });
                labels.style.height = `${Math.ceil(Math.max(0, ...[...labels.children].map(label => label.getBoundingClientRect().height)))}px`;
            };
            update();
            if (typeof root.ResizeObserver === "function") {
                const observer = new root.ResizeObserver(update);
                observer.observe(svg);
                labelCleanups.set(labels, () => observer.disconnect());
            } else if (typeof root.addEventListener === "function") {
                root.addEventListener("resize", update);
                root.document?.addEventListener("shown.bs.tab", update);
                labelCleanups.set(labels, () => {
                    root.removeEventListener("resize", update);
                    root.document?.removeEventListener("shown.bs.tab", update);
                });
            }
        },
        // Presentation only. Server amounts and eligibility remain unchanged.
        prepare(value) {
            const payload = value && typeof value === "object" ? value : {};
            const groups = Array.isArray(payload.frequency_forecasts)
                ? payload.frequency_forecasts.filter(group => group && ["monthly", "quarterly"].includes(group.frequency)) : [];
            if (!groups.length) return payload;
            const rowsFor = group => Array.isArray(group.future_projections) ? group.future_projections : [];
            const hasValue = (row, category) => row[`expected_${category}`] != null
                && Number.isFinite(Number(row[`expected_${category}`]))
                && row[`expected_${category}_applicable`] !== false
                && row[category === "net" ? "expected_net_unreliable" : `${category}_unreliable`] !== true;
            const ordered = [...groups].sort((a, b) => Number(a.frequency === "quarterly") - Number(b.frequency === "quarterly"));
            const candidates = ordered.flatMap(rowsFor);
            const monthLabel = row => {
                const match = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(String(row.coverage_end || ""));
                const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                return match ? `${months[Number(match[2]) - 1]} ${match[1]}` : String(row.period_label || "");
            };
            const scheduled = (row, category) => row && (hasValue(row, category)
                || row[`expected_${category}_applicable`] === true
                || row[category === "net" ? "expected_net_unreliable" : `${category}_unreliable`] === true);
            const derivedMethods = ["Monthly total", "Monthly actuals + SARIMA total", "Three-month SARIMA total"];
            const methodsFor = (row, category) => String(row?.[`${category}_method`] || "")
                .split(";").map(method => method.trim()).filter(Boolean);
            const hasDerived = (row, category) => methodsFor(row, category).some(method => derivedMethods.includes(method));
            const nativeQuarter = (row, category) => scheduled(row, category)
                && !hasDerived(row, category);
            const combinedQuarter = (row, category) => scheduled(row, category) && hasDerived(row, category)
                && methodsFor(row, category).includes("SARIMA");
            const reportQuarter = (row, category) => nativeQuarter(row, category) || combinedQuarter(row, category);
            const months = new Map();
            for (const row of candidates) {
                const key = row.coverage_end || row.period_label;
                if (!months.has(key)) months.set(key, {});
                months.get(key)[row.frequency] = row;
            }
            const rows = [...months.entries()].sort(([a], [b]) => String(a).localeCompare(String(b)))
                .map(([, periods]) => {
                    const {monthly, quarterly} = periods;
                    const base = monthly || quarterly;
                    const cells = {};
                    for (const category of ["sales", "expenses", "tax", "net"]) {
                        const entries = [];
                        const quarterNet = category === "net" && quarterly
                            && (!monthly || ["sales", "expenses"].some(key => reportQuarter(quarterly, key)));
                        // The row is the scheduled month, not a claim that all amounts cover one month.
                        if (scheduled(monthly, category) && !(category === "net"
                            && /Use a full quarterly comparison/.test(monthly.net_readiness_note || ""))) {
                            entries.push({model: monthly, frequency: "monthly"});
                        }
                        if (category === "net" ? quarterNet : reportQuarter(quarterly, category)) {
                            entries.push({model: quarterly, frequency: "quarterly",
                                comparison: category !== "net" && combinedQuarter(quarterly, category)});
                        }
                        cells[category] = entries.length ? entries : [{model: {...base,
                            [`expected_${category}`]: null, [`expected_${category}_applicable`]: false,
                            [category === "net" ? "expected_net_unreliable" : `${category}_unreliable`]: false}, frequency: ""}];
                    }
                    return {...base, period_label: monthLabel(base), forecast_cells: cells};
                });
            // Each independent lane retains one native frequency. In particular,
            // never replace Monthly Sales with a derived three-month comparison.
            const chartSeries = ["sales", "expenses", "tax", "net"].map(category => {
                const eligible = ordered.filter(group => rowsFor(group).some(row => scheduled(row, category)
                    && !(category === "net" && /Use a full quarterly comparison/.test(row.net_readiness_note || ""))
                    && (category === "net" || group.frequency === "monthly" || nativeQuarter(row, category))));
                const group = eligible.find(item => rowsFor(item).some(row => hasValue(row, category))) || eligible[0];
                return {category, frequency: group?.frequency || "", rows: group
                    ? rowsFor(group).map(row => ({...row, period_label: monthLabel(row),
                        // Keep a gap if another row in this lane is a comparison,
                        // rather than joining native points through that total.
                        ...(category !== "net" && group.frequency === "quarterly" && !nativeQuarter(row, category)
                            ? {[`expected_${category}`]: null, [`expected_${category}_applicable`]: false} : {})})) : []};
            });
            const chartFrequencies = [...new Set(chartSeries.map(item => item.frequency).filter(Boolean))];
            const salesChart = chartSeries.find(item => item.category === "sales");
            const prepared = {...payload, future_projections: rows,
                chart_projections: rows.map(row => ({...row})),
                chart_series: chartSeries,
                graph_frequency_label: chartFrequencies.length === 1
                    ? chartFrequencies[0].charAt(0).toUpperCase() + chartFrequencies[0].slice(1) : "",
                has_forecast: candidates.some(row => ["sales", "expenses", "tax"].some(category => hasValue(row, category))),
                // Do not draw an interpolated mini-chart through rejected periods.
                sparkline: salesChart.rows.every(row => hasValue(row, 'sales'))
                    ? salesChart.rows.map(row => row.expected_sales) : [],
                next_period_label: rows[0]?.period_label || ""};
            for (const category of ["sales", "expenses", "tax"]) {
                // Prefer native predictions over derived quarterly comparisons.
                const native = candidates.filter(row => !hasDerived(row, category));
                const row = native.find(item => hasValue(item, category))
                    || native.find(item => item.frequency === "quarterly" && item[`expected_${category}_applicable`])
                    || native.find(item => item[`expected_${category}_applicable`])
                    || candidates.find(item => hasValue(item, category));
                for (const key of [`expected_${category}`, `expected_${category}_applicable`,
                    `${category}_unreliable`, `${category}_limited_data`, `${category}_readiness_note`, `${category}_method`]) {
                    prepared[key] = row ? row[key] : null;
                }
                prepared[`${category}_period_label`] = row ? monthLabel(row)
                    + (row.frequency === "quarterly" ? hasDerived(row, category)
                        ? " · Quarter total · Includes monthly" : " · Quarterly" : "") : "";
            }
            return prepared;
        },
    };
}(window));
