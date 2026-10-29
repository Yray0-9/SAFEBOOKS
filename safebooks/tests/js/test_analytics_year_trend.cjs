/* Exercise the real SVG renderer with historical-year and rolling-month rows. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8').replace(/\r\n/g, '\n');
const extract = (source, start, end) => {
    const first = source.indexOf(start), last = source.indexOf(end, first);
    assert(first >= 0 && last > first, `Missing chart flow: ${start}`);
    return source.slice(first, last);
};
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
for (const name of ['client_details', 'analytics']) {
    const template = read(`templates/base/${name}.html`);
    const yearSelect = template.match(/<select id="analyticsYearFilter"[^>]*>([\s\S]*?)<\/select>/)[1];
    assert(!yearSelect.includes('value="all"'));
    assert(!yearSelect.includes('All Time'));
    assert(!/<option value="\d{4}"/.test(yearSelect), 'Year options must not be hard-coded');
    assert(yearSelect.includes('{% for analytics_year in analytics_years %}'));
    assert(yearSelect.includes('{% if analytics_year == analytics_current_year %} selected{% endif %}'));
    const node = () => ({attributes: {}, setAttribute(key, value) {this.attributes[key] = value;}});
    const page = {
        window: { SafeBooksTrendTooltip: { render(svg, rows, salesPoints, expensePoints) {
            page.tooltipRows = rows; page.tooltipPoints = { salesPoints, expensePoints };
        } } },
        analyticsSalesLine: node(), analyticsExpensesLine: node(),
        analyticsMonthLabels: {style: {setProperty(key, value) {this[key] = value;}}},
        analyticsTrendGrid: {}, analyticsSummaryTimeframeCaption: {}, analyticsTrendTimeframeCaption: {},
        currentClientProfile: {client_name: 'Synthetic Client'},
        document: {getElementById: () => null}, animatePolyline() {}, escapeHtml: value => String(value),
    };
    vm.createContext(page);
    page.analyticsSalesLine.closest = () => 'synthetic-svg';
    const captions = extract(template, '        const formatTrendEdgeLabel =', name === 'client_details' ? '        const getXYPoints =' : '        const syncAnalyticsUrlFromScope =');
    const geometry = extract(template, '        const getXYPoints =', '        const prefersReducedMotion =');
    const render = extract(template, '        const renderTrendGrid =', name === 'client_details' ? '        const renderPredictiveSparkline =' : '        const renderForecastSparkline =');
    vm.runInContext(captions + geometry + render + '\nthis.draw = renderTrend; this.caption = applyTimeframeCaptions; this.points = getXYPoints;', page);
    const endpoints = line => {
        const values = line.attributes.d.match(/-?\d+(?:\.\d+)?/g).map(Number);
        const result = [{x: values[0], y: values[1]}];
        for (let index = 2; index < values.length; index += 6) result.push({x: values[index + 4], y: values[index + 5]});
        return result;
    };
    const assertSharedScale = (sales, expenses) => {
        const rows = sales.map((value, index) => ({year: 2025, month: index + 1, month_label: months[index], sales: value, expenses: expenses[index]}));
        const original = JSON.stringify(rows);
        page.draw(rows);
        assert.equal(JSON.stringify(rows), original, 'Rendering must not modify amounts or payload rows');
        assert.equal(page.tooltipRows, rows, 'Tooltip uses the exact returned monthly rows');
        const labelPositions = [...page.analyticsMonthLabels.innerHTML.matchAll(/left:([\d.]+)%/g)].map(match => Number(match[1]));
        assert.equal(labelPositions.length, rows.length);
        assert.equal(page.analyticsMonthLabels.style.display, 'block', 'Override cached equal-column grids');
        for (let i = 0; i < rows.length; i++) {
            for (const pixelWidth of [300, 640, 1440]) {
                assert(Math.abs(labelPositions[i] / 100 * pixelWidth - page.tooltipPoints.salesPoints[i].x / 640 * pixelWidth) < .001,
                    `${name}: label and guide must align at every viewport width`);
            }
        }
        const low = Math.min(0, ...sales, ...expenses), high = Math.max(1, ...sales, ...expenses);
        for (const [line, amounts] of [[page.analyticsSalesLine, sales], [page.analyticsExpensesLine, expenses]]) {
            const plotted = endpoints(line);
            assert.equal(plotted.length, amounts.length);
            for (let index = 0; index < amounts.length; index++) {
                const expectedY = 206 - 190 * (amounts[index] - low) / (high - low);
                assert(Math.abs(plotted[index].y - expectedY) <= 0.006, `${name}: amount ${amounts[index]} must use the combined peso range`);
            }
        }
    };
    assertSharedScale([100000, 50000], [1000, 50000]); // Different maxima, equal second-month values.
    assertSharedScale([0, 500], [1000, 500]);          // Expenses can be higher than sales.
    assertSharedScale([100, 100, 100], [20, 20, 20]); // Constant histories.
    assertSharedScale([0, 0], [0, 0]);               // Zero remains a finite baseline.
    assertSharedScale([0.10, 0.25], [0.01, 0.25]);   // Centavo values.
    assertSharedScale([999999999999.99, 0], [1, 0]);  // Storage-limit magnitude.
    assertSharedScale([100], [10]);                  // Single-point history.
    assertSharedScale([-10, 10], [0, 5]);            // Existing negative history is not rewritten.
    const independent = page.points([10, 20], 640, 240, {left: 34, right: 18, top: 16, bottom: 34});
    assert.equal(independent[0].y, 111, 'Forecast callers without shared bounds retain their existing scale');
    assert.equal(independent[1].y, 16);
    for (const year of [2024, 2025, 2026]) {
        const rows = months.map((month_label, index) => ({year, month: index + 1, month_label, sales: (index + 1) * 100, expenses: (12 - index) * 10}));
        page.draw(rows);
        page.caption({client_name: 'Synthetic Client'}, rows);
        assert.equal(page.analyticsMonthLabels.style['--trend-month-count'], '12');
        assert.equal((page.analyticsMonthLabels.innerHTML.match(/<span\b/g) || []).length, 12);
        assert(page.analyticsMonthLabels.innerHTML.includes('>Jan</span>'));
        assert(page.analyticsMonthLabels.innerHTML.includes('>Dec</span>'));
        for (const line of [page.analyticsSalesLine, page.analyticsExpensesLine]) {
            assert.equal((line.attributes.d.match(/ C /g) || []).length, 11);
            assert(!/NaN|undefined|Infinity/.test(line.attributes.d));
        }
        assert(page.analyticsTrendTimeframeCaption.textContent.includes(`Jan ${year} to Dec ${year}`));
        assert(!page.analyticsTrendTimeframeCaption.textContent.includes('latest 6 months'));
    }
    const recent = months.slice(4, 10).map(month_label => ({year: 2026, month_label, sales: 1, expenses: 0}));
    page.draw(recent);
    assert.equal(page.analyticsMonthLabels.style['--trend-month-count'], '6');
    assert.equal((page.analyticsMonthLabels.innerHTML.match(/left:/g) || []).length, 6);
    assert.equal((page.analyticsSalesLine.attributes.d.match(/ C /g) || []).length, 5);
    page.draw([]);
    assert.equal(page.analyticsSalesLine.attributes.d, '');
    assert.equal(page.analyticsMonthLabels.innerHTML, '');
}
for (const name of ['analytics', 'client_details']) {
    assert(!read(`static/css/${name}.css`).includes('grid-template-columns: repeat(6, minmax(0, 1fr));'));
    assert(read(`static/css/${name}.css`).includes('repeat(var(--trend-month-count, 6), minmax(0, 1fr))'));
}
console.log('Analytics year-trend tests passed: shared peso scaling, equal amounts, zero/centavo/large values, unchanged forecast scaling, historical years, labels and reset.');
const tooltipCss = read('static/css/analytics_trend_tooltip.css');
assert(tooltipCss.includes('animation: analytics-tooltip-enter 140ms ease-out'));
assert(/@media \(prefers-reduced-motion: reduce\)[\s\S]*animation: none/.test(tooltipCss));
