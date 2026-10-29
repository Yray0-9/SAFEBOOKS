const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('static/js/forecast_periods.js', 'utf8'), context);
const prepare = context.window.SafeBooksForecastPeriods.prepare;
const lane = (prepared, category) => prepared.chart_series.find(item => item.category === category);
const row = (frequency, end, label, values) => ({frequency, coverage_end: end, period_label: label, ...values});
const monthly = {frequency: 'monthly', frequency_label: 'Monthly', future_projections: [
    row('monthly', '2026-11', 'Nov 2026', {expected_sales: 100, expected_expenses: null, expected_expenses_applicable: true, expenses_method: 'SARIMA'}),
    row('monthly', '2026-12', 'Dec 2026', {expected_sales: 110, expected_net: null}),
    row('monthly', '2027-01', 'Jan 2027', {expected_sales: 120, expected_net: null}),
]};
const quarterly = {frequency: 'quarterly', frequency_label: 'Quarterly', future_projections: [
    row('quarterly', '2026-12', 'Q4 2026 (Oct–Dec)', {expected_sales: 300, sales_method: 'Monthly actuals + SARIMA total',
        expected_expenses: 100, expenses_method: 'SARIMA', expected_tax: 10, tax_method: 'SARIMA', expected_net: 200}),
]};
const payload = {history_start: '2024-01', history_end: '2026-10', frequency_forecasts: [quarterly, monthly]};
const before = JSON.stringify(payload);
const result = prepare(payload);
assert.equal(result.future_projections.map(item => item.period_label).join('|'), 'Nov 2026|Dec 2026|Jan 2027');
assert.equal(result.expected_sales, 100);
assert.equal(result.sales_period_label, 'Nov 2026');
assert.equal(result.expected_expenses, 100, 'A short monthly series must not hide the valid native quarter');
assert.equal(result.expenses_period_label, 'Dec 2026 · Quarterly');
assert.equal(result.tax_period_label, 'Dec 2026 · Quarterly');
const december = result.future_projections[1];
assert.equal(december.forecast_cells.net[0].model.expected_net, 200);
assert.equal(december.forecast_cells.net[0].frequency, 'quarterly');
assert.equal(december.forecast_cells.sales.length, 1, 'Do not add a separate quarterly-sales comparison row');
assert.equal(december.forecast_cells.sales[0].model.expected_sales, 110);
assert.equal(december.forecast_cells.expenses[0].model.expected_expenses, 100);
assert.equal(december.forecast_cells.expenses[0].frequency, 'quarterly');
assert.equal(result.future_projections[2].forecast_cells.expenses[0].model.expected_expenses_applicable, false);
assert.equal(result.future_projections[0].forecast_cells.tax[0].model.expected_tax_applicable, false);
assert.equal(result.future_projections[1].expected_net, null, 'Never copy quarterly net into a monthly row');
assert.equal(result.graph_frequency_label, '', 'Different native lanes must not be given one misleading frequency');
assert.equal(result.chart_projections.length, 3, 'Keep the shared calendar timeline');
assert.equal(lane(result, 'sales').frequency, 'monthly');
assert.equal(lane(result, 'sales').rows.map(item => item.expected_sales).join('|'), '100|110|120',
    'Do not replace native Monthly Sales with a derived quarterly total');
assert.equal(lane(result, 'expenses').frequency, 'quarterly');
assert.equal(lane(result, 'expenses').rows[0].expected_expenses, 100);
assert.equal(lane(result, 'tax').rows[0].expected_tax, 10);
assert.equal(lane(result, 'net').frequency, 'quarterly');
assert.equal(lane(result, 'net').rows[0].expected_net, 200);
assert.equal(result.sparkline.join('|'), '100|110|120');
assert.equal(JSON.stringify(payload), before, 'Presentation must not mutate server predictions');
const onlyQuarter = prepare({frequency_forecasts: [quarterly]});
assert.equal(onlyQuarter.graph_frequency_label, 'Quarterly');
assert.equal(onlyQuarter.future_projections.length, 1);
assert.equal(onlyQuarter.future_projections[0].period_label, 'Dec 2026');
assert.equal(onlyQuarter.chart_projections[0].period_label, 'Dec 2026');
assert.equal(onlyQuarter.expected_expenses, 100);
assert.equal(lane(onlyQuarter, 'sales').rows.length, 0, 'Derived comparisons must not masquerade as native quarterly Sales');
const actualQuarterSales = {...quarterly, future_projections:quarterly.future_projections.map(item => ({...item,sales_method:'SARIMA'}))};
assert.equal(lane(prepare({frequency_forecasts:[actualQuarterSales]}),'sales').frequency,'quarterly',
    'Genuinely quarterly Sales must still retain their own native frequency');
const noMonths = {...monthly, future_projections: monthly.future_projections.map(item => ({...item, expected_sales: null}))};
assert.equal(prepare({frequency_forecasts: [noMonths, quarterly]}).graph_frequency_label, 'Quarterly');
const failed = prepare({has_forecast: false});
assert.equal(failed.expected_sales, undefined);
assert.equal(failed.future_projections, undefined);
assert.equal(prepare(null).has_forecast, undefined);
const legacy = {expected_sales: 10, future_projections: [{expected_sales: 10}]};
assert.equal(prepare(legacy), legacy);
assert.equal(prepare({frequency_forecasts: [{frequency: 'quarterly', future_projections: []}]}).future_projections.length, 0);
const zero = prepare({frequency_forecasts: [{frequency: 'monthly', future_projections: [row('monthly', '2026-11', 'Nov 2026', {expected_sales: 0})]}]});
assert.equal(zero.expected_sales, 0);
assert.equal(zero.has_forecast, true);
// Both native intervals must be retained in the same cell, never summed or replaced.
const mixedMonths = {...monthly, future_projections: monthly.future_projections.map(item => ({...item,
    expected_expenses: 20, expected_expenses_applicable: true, expenses_method: 'SARIMA', expected_net: 80}))};
const mixed = prepare({frequency_forecasts: [mixedMonths, quarterly]}).future_projections[1];
assert.equal(mixed.forecast_cells.expenses.length, 2);
assert.equal(mixed.forecast_cells.expenses[0].model.expected_expenses, 20);
assert.equal(mixed.forecast_cells.expenses[1].model.expected_expenses, 100);
assert.equal(mixed.forecast_cells.net.length, 2);
assert.equal(lane(prepare({frequency_forecasts:[mixedMonths,quarterly]}),'expenses').frequency,'monthly');
const zeroMonthlyExpense = {...mixedMonths, future_projections:mixedMonths.future_projections.map(item => ({...item,expected_expenses:0}))};
assert.equal(lane(prepare({frequency_forecasts:[zeroMonthlyExpense,quarterly]}),'expenses').rows[0].expected_expenses,0,
    'A genuine native zero is available, not a reason to switch to a quarterly amount');
const allMonthly = {...mixedMonths, future_projections: mixedMonths.future_projections.map(item => ({...item,
    expected_tax:10, expected_tax_applicable:true}))};
assert.equal(prepare({frequency_forecasts:[quarterly, allMonthly]}).graph_frequency_label, 'Monthly',
    'Equal category coverage must retain the familiar Monthly chart');
const moreMonthly = {...monthly, future_projections: monthly.future_projections.map(item => ({...item,
    expected_expenses:20, expected_tax:10, expected_net:80}))};
const quarterSalesOnly = {...quarterly, future_projections: quarterly.future_projections.map(item => ({...item,
    expected_expenses:null, expected_tax:null, expected_net:null}))};
assert.equal(prepare({frequency_forecasts:[quarterSalesOnly, moreMonthly]}).graph_frequency_label, 'Monthly');
const invalidQuarter = {...quarterly, future_projections: quarterly.future_projections.map(item => ({...item,
    expected_expenses:NaN, expected_tax:Infinity, expected_net:200, expected_net_unreliable:true}))};
const invalid = prepare({frequency_forecasts:[monthly, invalidQuarter]});
assert.equal(lane(invalid, 'sales').frequency, 'monthly');
assert.equal(lane(invalid, 'tax').rows.length, 0, 'Non-finite values must not manufacture a native Tax lane');
const unavailable = {...quarterly, future_projections: quarterly.future_projections.map(item => ({...item,
    expected_expenses: null, expected_expenses_applicable: true, expenses_unreliable: true,
    expected_net: null, expected_net_unreliable: true}))};
const blocked = prepare({frequency_forecasts: [monthly, unavailable]});
assert.equal(blocked.future_projections[1].forecast_cells.expenses[0].model.expected_expenses, null);
assert.equal(blocked.future_projections[1].forecast_cells.expenses[0].frequency, 'quarterly');
assert.equal(blocked.future_projections[1].forecast_cells.net[0].model.expected_net, null);
const partialTax = prepare({frequency_forecasts: [{frequency: 'quarterly', future_projections: [
    row('quarterly', '2026-12', 'Q4 2026', {expected_tax:null, expected_tax_applicable:true, tax_unreliable:true,
        tax_readiness_note:'Negative SARIMA prediction'}),
    row('quarterly', '2027-03', 'Q1 2027', {expected_tax:99, expected_tax_applicable:true, tax_readiness_note:'SARIMA'}),
]}]});
assert.equal(partialTax.expected_tax, 99);
// All Clients may combine native quarterly models with three-month monthly sums.
// Preserve the amount as a labelled comparison, never as another native forecast.
const combinedQuarter = {...quarterly, future_projections:quarterly.future_projections.map(item => ({...item,
    coverage_start:'2026-10', sales_method:'Three-month SARIMA total; SARIMA', expected_sales:800,
    expenses_method:'SARIMA; Monthly actuals + SARIMA total', expected_expenses:80,
    expected_net:720, expected_net_applicable:true, expected_net_unreliable:false,
    net_sales_basis:800, net_expenses_basis:80}))};
const combinedPayload = {frequency_forecasts:[monthly, combinedQuarter]};
const combinedBefore = JSON.stringify(combinedPayload);
const combined = prepare(combinedPayload);
const combinedDecember = combined.future_projections[1];
assert.equal(combinedDecember.forecast_cells.sales[1].comparison,true,
    'A composite method must not pass the native-quarter test');
assert.equal(combinedDecember.forecast_cells.expenses.at(-1).comparison,true);
assert.equal(combinedDecember.forecast_cells.sales[0].model.expected_sales,110);
assert.equal(combinedDecember.forecast_cells.sales[1].model.expected_sales,800);
assert.equal(combinedDecember.forecast_cells.net[0].model.expected_net,720,
    'Distinguishing comparisons must not hide the aligned quarterly net');
assert.equal(lane(combined,'sales').frequency,'monthly');
assert.equal(lane(combined,'sales').rows.map(item => item.expected_sales).join('|'),'100|110|120');
assert.notEqual(lane(combined,'expenses').frequency,'quarterly','A combined total is not a native quarterly graph point');
assert.equal(JSON.stringify(combinedPayload),combinedBefore,'No server values may be overwritten or recomputed');
for (const amount of [0,null]) {
    const fixture = {...combinedQuarter,future_projections:combinedQuarter.future_projections.map(item => ({...item,
        expected_sales:amount, expected_sales_applicable:true, sales_unreliable:amount === null,
        sales_readiness_note:amount === null ? 'Negative SARIMA prediction' : 'SARIMA'}))};
    const entry = prepare({frequency_forecasts:[monthly,fixture]}).future_projections[1].forecast_cells.sales[1];
    assert.equal(entry.comparison,true);
    assert.equal(entry.model.expected_sales,amount,'Do not hide zero or fabricate a value for a rejected comparison');
    assert.equal(entry.model.sales_unreliable,amount === null);
}
for (const method of ['Monthly total; SARIMA','SARIMA; Three-month SARIMA total',
    ' Monthly actuals + SARIMA total ; SARIMA ']) {
    const fixture = {...combinedQuarter, future_projections:combinedQuarter.future_projections.map(item => ({...item,sales_method:method}))};
    assert.equal(prepare({frequency_forecasts:[monthly,fixture]}).future_projections[1].forecast_cells.sales[1].comparison,true);
}
const nativeMethods = {...combinedQuarter, future_projections:combinedQuarter.future_projections.map(item => ({...item,
    sales_method:'SARIMA; SARIMA',expected_sales:0}))};
assert.equal(prepare({frequency_forecasts:[monthly,nativeMethods]}).future_projections[1].forecast_cells.sales[1].comparison,false);
const comparisonOnly = prepare({frequency_forecasts:[combinedQuarter]});
assert.equal(lane(comparisonOnly,'sales').rows.length,0);
assert(comparisonOnly.sales_period_label.includes('Quarter total · Includes monthly'));
const alternating = {...quarterly, future_projections:['2026-12','2027-03','2027-06'].map((end,index) =>
    row('quarterly',end,end,{expected_sales:index === 1 ? 800 : 500,
        sales_method:index === 1 ? 'SARIMA; Three-month SARIMA total' : 'SARIMA'}))};
const alternatingBefore = JSON.stringify(alternating);
const alternatingLane = lane(prepare({frequency_forecasts:[alternating]}),'sales');
assert.equal(alternatingLane.rows.map(item => item.expected_sales).join('|'),'500||500',
    'A mixed row in a native lane remains a gap, never a connecting quarter total');
assert.equal(JSON.stringify(alternating),alternatingBefore);
assert.equal(partialTax.tax_period_label, 'Mar 2027 · Quarterly');
assert.equal(partialTax.future_projections[0].forecast_cells.tax[0].model.expected_tax, null);
assert.equal(partialTax.sparkline.length, 0, 'Unknown values must not become sparkline zeroes');
const offset = prepare({frequency_forecasts: [{frequency:'quarterly', future_projections: [
    row('quarterly', '2026-11', 'Sep 2026–Nov 2026', {expected_expenses: 50, expenses_method:'SARIMA'})]}]});
assert.equal(offset.future_projections[0].period_label, 'Nov 2026', 'Never force non-calendar schedules into December');
assert.equal(offset.future_projections[0].forecast_cells.expenses[0].model.expected_expenses, 50);
// Label positioning must reflow without leaking observers/listeners on redraw.
let resizeLabels;
let disconnected = 0;
context.window.ResizeObserver = class {
    constructor(callback) {resizeLabels = callback;}
    observe() {}
    disconnect() {disconnected++;}
};
let graphRect = {left:10,width:600};
const captions = {style:{}, children:Array.from({length:3}, () => ({style:{}, getBoundingClientRect:() => ({height:18})})),
    getBoundingClientRect:() => ({left:0,width:620})};
const svgBox = {getBoundingClientRect:() => graphRect};
const align = context.window.SafeBooksForecastPeriods.alignLabels;
align(captions,svgBox,[0.1,0.5,0.9]);
assert.equal(captions.children[0].style.left,'70px');
assert.equal(captions.children[2].style.left,'550px');
assert.equal(captions.style.height,'18px');
graphRect = {left:5,width:300};
resizeLabels();
assert.equal(captions.children[2].style.left,'275px');
const narrowCaptions = {style:{},children:captions.children,
    getBoundingClientRect:() => ({left:5,width:300})};
align(narrowCaptions,svgBox,[0.13,0.55,0.967]);
const lastCaption = narrowCaptions.children[2];
assert(parseFloat(lastCaption.style.left) + parseFloat(lastCaption.style.width) / 2 <= 300,
    'Short-horizon date captions must fit the container while staying centered on their points');
align(narrowCaptions,null,[]);
align(captions,null,[]);
assert.equal(disconnected,2);
assert.equal(captions.style.height,'');
delete context.window.ResizeObserver;
let fallback;
let removed = false;
context.window.addEventListener = (name,callback) => {assert.equal(name,'resize');fallback=callback;};
context.window.removeEventListener = (name,callback) => {removed=name==='resize' && callback===fallback;};
align(captions,svgBox,[0.1,0.5,0.9]);
fallback();
align(captions,null,[]);
assert(removed,'Resize fallback must be removed when the chart is cleared');
// Execute both real template report renderers, not a duplicate formatter.
for (const name of ['client_details', 'analytics']) {
    const template = fs.readFileSync(`templates/base/${name}.html`, 'utf8');
    assert(template.includes('<th scope="col">Net Value<span class="visually-hidden">: calculated sales minus expenses for matching periods, not a separate SARIMA forecast</span></th>'));
    assert(!template.includes('<th>Projected Net Value</th>'));
    const table = {innerHTML: ''};
    const page = {predictiveForecastTableBody: table, formatCurrency: value => `PHP ${value}`,
        escapeHtml: value => String(value ?? '').replace(/[&<>"']/g, character =>
            ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'})[character])};
    vm.createContext(page);
    const start = template.indexOf('        const projectionHasValue =');
    const end = template.indexOf('        const getProjectionMethodLabel =', start);
    const renderStart = template.indexOf('        const formatForecastCell =');
    const renderEnd = template.indexOf('        const renderForecastProjectionChart =', renderStart);
    assert(start > 0 && end > start && renderStart > 0 && renderEnd > renderStart);
    vm.runInContext(template.slice(start, end) + template.slice(renderStart, renderEnd)
        + '\nthis.render = renderPredictiveForecastReport; this.cell = formatForecastCell;', page);
    page.render(result.future_projections);
    assert.equal((table.innerHTML.match(/<tr>/g) || []).length, 3);
    assert(!table.innerHTML.includes('Q4 2026'));
    assert(!page.cell(result.future_projections[0], 'tax').includes('Quarterly'));
    assert(page.cell(result.future_projections[0], 'tax').includes('N/A'));
    assert(page.cell(december, 'expenses').includes('PHP 100'));
    assert(page.cell(december, 'expenses').includes('Quarterly'));
    assert(page.cell(december, 'net').includes('PHP 200'));
    assert(!page.cell(december, 'sales').includes('PHP 300'));
    assert(page.cell(december, 'sales').includes('Monthly'), 'One-month Sales must not appear to be the quarterly Net basis');
    const comparisonCell = page.cell(combinedDecember,'sales');
    assert(comparisonCell.includes('PHP 800'),'Do not discard the valid combined quarter total');
    assert(comparisonCell.includes('Quarter total · Includes monthly'));
    assert(!comparisonCell.includes('>Quarterly<'));
    assert(comparisonCell.includes('do not add it to the monthly values'),'Explain the non-additive comparison in accessible details');
    assert(comparisonCell.includes('2026-10 to 2026-12'),'Keep the exact comparison coverage');
    assert(page.cell(combinedDecember,'net').includes('PHP 800 − PHP 80'),'Net bases remain those supplied by the service');
    assert.equal((page.cell(mixed, 'expenses').match(/analytics-forecast-interval/g) || []).length, 2);
    assert(page.cell(blocked.future_projections[1], 'expenses').includes('Cannot forecast'));
    assert(page.cell(blocked.future_projections[1], 'net').includes('Cannot calculate'));
    assert(!page.cell(blocked.future_projections[1], 'net').includes('Cannot forecast'));
    assert(page.cell(partialTax.future_projections[0], 'tax').includes('Quarterly · Negative prediction'));
    assert(page.cell(partialTax.future_projections[1], 'tax').includes('PHP 99'));
    const netModel = {...quarterly.future_projections[0], expected_net:null, expected_net_unreliable:true,
        net_readiness_note:'Expenses (monthly): Complete three-month coverage required; 3 of 24 monthly periods'};
    const incompleteNetCell = page.cell({forecast_cells:{net:[{model:netModel,frequency:'quarterly'}]}}, 'net');
    assert(incompleteNetCell.includes('Quarterly · Incomplete monthly expenses'));
    assert(!incompleteNetCell.includes('3/24'), 'Do not confuse monthly readiness with a quarterly count');
    assert(incompleteNetCell.includes('Complete three-month coverage required'), 'Preserve the full coverage reason in accessible details');
    assert(!incompleteNetCell.includes('analytics-forecast-basis'), 'Do not display a partial formula for unavailable Net Value');
    const missingSales = {...netModel,
        net_readiness_note:'Sales (monthly): Complete three-month coverage required; 5 of 24 monthly periods'};
    assert(page.cell({forecast_cells:{net:[{model:missingSales,frequency:'quarterly'}]}}, 'net')
        .includes('Incomplete monthly sales'));
    const irregularExpenses = {...netModel,
        net_readiness_note:'Expenses (monthly): Complete three-month coverage required; Review missing monthly periods'};
    assert(page.cell({forecast_cells:{net:[{model:irregularExpenses,frequency:'quarterly'}]}}, 'net')
        .includes('Quarterly · Incomplete monthly expenses'));
    const missingQuarterlyExpenses = {...netModel,
        net_readiness_note:'Expenses (quarterly): Review missing quarterly periods'};
    assert(page.cell({forecast_cells:{net:[{model:missingQuarterlyExpenses,frequency:'quarterly'}]}}, 'net')
        .includes('Quarterly · Incomplete quarterly expenses'));
    const netBasis = {...quarterly.future_projections[0], net_sales_basis:500, net_expenses_basis:300};
    assert(page.cell({forecast_cells:{net:[{model:netBasis,frequency:'quarterly'}]}}, 'net').includes('Sales PHP 500 minus expenses PHP 300'));
    assert(page.cell({forecast_cells:{net:[{model:netBasis,frequency:'quarterly'}]}}, 'net').includes('Quarterly · Calculated'));
    const coveredNet = {...netBasis, coverage_start:'2026-10', coverage_end:'2026-12'};
    const coveredCell = page.cell({forecast_cells:{net:[{model:coveredNet,frequency:'quarterly'}]}}, 'net');
    assert(coveredCell.includes('<span>Oct to Dec 2026</span><span>PHP 500 − PHP 300</span>'),
        'The actual same-period bases must be visible, not just in a hover title');
    const crossYearNet = {...coveredNet, coverage_start:'2026-11',coverage_end:'2027-01'};
    assert(page.cell({forecast_cells:{net:[{model:crossYearNet,frequency:'quarterly'}]}}, 'net')
        .includes('Nov 2026 to Jan 2027'));
    const monthlyNet = {...coveredNet,coverage_start:'2026-12',coverage_end:'2026-12'};
    assert(page.cell({forecast_cells:{net:[{model:monthlyNet,frequency:'monthly'}]}}, 'net')
        .includes('<span>Dec 2026</span>'));
    const originalBasis = JSON.stringify(coveredNet);
    page.cell({forecast_cells:{net:[{model:coveredNet,frequency:'quarterly'}]}}, 'net');
    assert.equal(JSON.stringify(coveredNet), originalBasis, 'Displaying the formula never recomputes or mutates Net Value');
    for (const amount of [0, -100]) {
        const calculated = {...netBasis, expected_net:amount};
        const cell = page.cell({forecast_cells:{net:[{model:calculated,frequency:'quarterly'}]}}, 'net');
        assert(cell.includes(`PHP ${amount}`), 'A zero or negative calculated net is valid');
        assert(!cell.includes('Cannot calculate'));
    }
    const injected = {...december, period_label: '<script>bad</script>', forecast_cells: {
        expenses: [{frequency: 'quarterly', model: {...quarterly.future_projections[0], expenses_readiness_note: '"><script>bad</script>'}}]}};
    page.render([injected]);
    assert(!table.innerHTML.includes('<script>'));
    assert(table.innerHTML.includes('&lt;script&gt;'));
    page.render([]);
    assert(!table.innerHTML.includes('PHP 200'), 'Empty/error rendering must clear earlier values');
    const element = () => ({innerHTML:'', hidden:false, attrs:{}, setAttribute(key,value){this.attrs[key]=value;}});
    const areas = element();
    for (const key of ['Grid','Bridges','Dots','Labels','Empty','Hint','SalesLine','ExpensesLine','TaxLine','NetLine']) {
        page[`analyticsForecastProjection${key}`] = element();
    }
    page.analyticsForecastProjectionTooltip = null;
    page.document = {getElementById:id => id === 'analyticsForecastProjectionAreas' ? areas : null};
    page.formatCompactCurrency = value => String(value);
    page.animatePolyline = () => {};
    page.getBezierPath = points => points.length ? 'M' + points.map(point => `${point.x},${point.y}`).join('L') : '';
    page.getAreaBezierPath = points => 'AREA ' + points.length;
    page.fillSeriesGaps = () => {throw Error('Forecast charts must not interpolate unavailable values');};
    const chartStart = template.indexOf('        const renderForecastProjectionChart =');
    const chartEnd = template.indexOf(name === 'client_details'
        ? '        const updateAnalyticsEmptyMessage =' : '        const applyRemarksMeta =', chartStart);
    vm.runInContext(template.slice(chartStart, chartEnd) + '\nthis.chart = renderForecastProjectionChart;', page);
    const chartRows = [10, null, 30, 40].map((value,index) => ({period_label:`Period ${index}`,
        expected_sales:100, expected_tax:value, expected_tax_applicable:true, tax_unreliable:value === null}));
    page.chart(chartRows);
    assert.equal((page.analyticsForecastProjectionTaxLine.attrs.d.match(/M/g) || []).length, 2,
        'The Tax line must restart after a rejected prediction');
    assert.equal((page.analyticsForecastProjectionDots.innerHTML.match(/class="analytics-forecast-projection-dot tax"/g) || []).length, 3);
    assert.equal(page.analyticsForecastProjectionBridges.innerHTML, '', 'No dashed interpolation across missing predictions');
    assert.equal((areas.innerHTML.match(/analytics-forecast-projection-area tax/g) || []).length, 1);
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('Incomplete Sales or Expenses'));
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('analytics-forecast-lane-empty expenses'));
    assert.equal((page.analyticsForecastProjectionGrid.innerHTML.match(/analytics-forecast-grid-line baseline/g) || []).length, 2,
        'Only Sales and Tax have data; unavailable lanes must not show fabricated currency scales');
    page.chart(result.chart_projections, result.chart_series);
    for (const category of ['sales','expenses','tax','net']) {
        assert(page[`analyticsForecastProjection${category[0].toUpperCase()+category.slice(1)}Line`].attrs.d.startsWith('M'),
            `${name} must plot ${category} from its own labelled native lane`);
    }
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('Sales · Monthly'));
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('Expenses · Quarterly'));
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('Tax · Quarterly'));
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('Net Value · Calculated · Quarterly'));
    assert(!page.analyticsForecastProjectionDots.innerHTML.includes('data-tooltip-value="PHP 300"'),
        'The comparison-only quarterly Sales amount must not be plotted');
    const alignedQuarterRows = [
        {...quarterly.future_projections[0], coverage_start:'2026-10', coverage_end:'2026-12'},
        {...quarterly.future_projections[0], period_label:'Mar 2027', coverage_start:'2027-01', coverage_end:'2027-03',
            expected_sales:330, expected_expenses:110, expected_tax:11, expected_net:220},
    ];
    page.chart(alignedQuarterRows);
    assert(page.analyticsForecastProjectionDots.innerHTML.includes('2026-10 to 2026-12'));
    assert(page.analyticsForecastProjectionDots.innerHTML.includes('2027-01 to 2027-03'));
    assert.equal((page.analyticsForecastProjectionDots.innerHTML.match(/class="analytics-forecast-projection-dot expenses"/g) || []).length, 2);
    assert.equal((page.analyticsForecastProjectionDots.innerHTML.match(/class="analytics-forecast-projection-dot tax"/g) || []).length, 2);
    const sixMonthlyRows = Array.from({length:6}, (_, index) => {
        const absolute = 2026 * 12 + 10 + index;
        const end = `${Math.floor(absolute / 12)}-${String(absolute % 12 + 1).padStart(2,'0')}`;
        return row('monthly', end, end, {coverage_start:end, expected_sales:100 + index * 10,
            expected_net:null, expected_net_unreliable:true, net_readiness_note:'Use a full quarterly comparison'});
    });
    const calendar = prepare({frequency_forecasts:[{...monthly, future_projections:sixMonthlyRows},
        {...quarterly, future_projections:alignedQuarterRows}]});
    page.chart(calendar.chart_projections, calendar.chart_series);
    assert.equal((page.analyticsForecastProjectionDots.innerHTML.match(/class="analytics-forecast-projection-dot sales"/g) || []).length, 6);
    assert.equal((page.analyticsForecastProjectionDots.innerHTML.match(/class="analytics-forecast-projection-dot expenses"/g) || []).length, 2);
    assert.equal((page.analyticsForecastProjectionTaxLine.attrs.d.match(/M/g) || []).length, 1,
        'Connect consecutive native quarters, not nonscheduled monthly slots');
    const quarterDots = [...page.analyticsForecastProjectionDots.innerHTML.matchAll(/class="analytics-forecast-projection-dot tax"\s+cx="([^"]+)"/g)].map(match => Number(match[1]));
    assert.equal(quarterDots.join('|'), '214.4|575.6', 'Quarter dots belong at December and March on the shared six-month calendar');
    assert(page.analyticsForecastProjectionDots.innerHTML.includes('data-tooltip-label="Sales · Monthly"'));
    assert(page.analyticsForecastProjectionDots.innerHTML.includes('2026-10 to 2026-12'));
    const missingQuarter = [alignedQuarterRows[0], {...alignedQuarterRows[1], expected_tax:null, tax_unreliable:true},
        {...alignedQuarterRows[1], period_label:'Jun 2027', coverage_start:'2027-04', coverage_end:'2027-06', expected_tax:12}];
    const rejected = prepare({frequency_forecasts:[{...quarterly, future_projections:missingQuarter}]});
    page.chart(rejected.chart_projections, rejected.chart_series);
    assert.equal((page.analyticsForecastProjectionTaxLine.attrs.d.match(/M/g) || []).length, 2,
        'A rejected scheduled quarter must break the native quarterly curve');
    page.chart([{...alignedQuarterRows[0], expected_net:null, expected_net_applicable:false, expected_net_unreliable:true}]);
    assert.equal(page.analyticsForecastProjectionNetLine.attrs.d, '', 'Unavailable calculated Net must not retain an earlier line');
    assert(page.analyticsForecastProjectionGrid.innerHTML.includes('Incomplete Sales or Expenses'));
    const escapedCoverage = [{...alignedQuarterRows[0], coverage_start:'"><script>bad</script>'}];
    page.chart(escapedCoverage);
    assert(!page.analyticsForecastProjectionDots.innerHTML.includes('<script>'));
    assert(page.analyticsForecastProjectionDots.innerHTML.includes('&lt;script&gt;'));
    page.chart([]);
    assert.equal(page.analyticsForecastProjectionTaxLine.attrs.d, '');
    assert.equal(page.analyticsForecastProjectionDots.innerHTML, '');
}
console.log('Forecast report/graph passed: native frequency per lane, unchanged Monthly Sales, scheduled quarterly points, calculated net, empty reasons, exact coverage, rejected-period gaps, zero, cleanup and immutable input.');
