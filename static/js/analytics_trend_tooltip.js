(() => {
    const instances = new WeakMap();
    const currency = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' });
    const svgNode = (tag, attrs) => {
        const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
        return node;
    };
    const clear = svg => {
        instances.get(svg)?.();
        instances.delete(svg);
    };
    const render = (svg, rows, salesPoints, expensePoints) => {
        if (!svg) return;
        clear(svg);
        if (!rows.length) return;
        const root = svg.closest('.analytics-trend-chart');
        if (!root) return;
        const tooltip = document.createElement('div');
        tooltip.className = 'analytics-month-tooltip';
        tooltip.hidden = true;
        tooltip.setAttribute('role', 'tooltip');
        const title = document.createElement('strong');
        const sales = document.createElement('span');
        const expenses = document.createElement('span');
        tooltip.append(title, sales, expenses);
        root.append(tooltip);
        const overlay = svgNode('g', { class: 'analytics-month-interaction' });
        const guide = svgNode('g', { 'aria-hidden': 'true', 'pointer-events': 'none', visibility: 'hidden' });
        const rule = svgNode('line', { y1: 16, y2: 206, class: 'analytics-month-rule' });
        const salesDot = svgNode('circle', { r: 4, fill: '#2366dd', stroke: '#fff', 'stroke-width': 2 });
        const expensesDot = svgNode('circle', { r: 4, fill: '#e48a2d', stroke: '#fff', 'stroke-width': 2 });
        guide.append(rule, salesDot, expensesDot);
        const targets = [];
        let pinned = false;
        const hide = () => {
            tooltip.hidden = true;
            guide.setAttribute('visibility', 'hidden');
            pinned = false;
        };
        const show = index => {
            const row = rows[index];
            const point = salesPoints[index];
            const expensePoint = expensePoints[index];
            const month = `${row.month_label || row.month || ''} ${row.year || ''}`.trim();
            title.textContent = month;
            sales.textContent = `Sales: ${currency.format(Number(row.sales || 0))}`;
            expenses.textContent = `Expenses: ${currency.format(Number(row.expenses || 0))}`;
            rule.setAttribute('x1', point.x);
            rule.setAttribute('x2', point.x);
            for (const [dot, xy] of [[salesDot, point], [expensesDot, expensePoint]]) {
                dot.setAttribute('cx', xy.x);
                dot.setAttribute('cy', xy.y);
            }
            guide.setAttribute('visibility', 'visible');
            tooltip.hidden = false;
            const bounds = svg.getBoundingClientRect();
            const container = root.getBoundingClientRect();
            const x = bounds.left - container.left + point.x / 640 * bounds.width;
            tooltip.style.left = `${Math.max(8, Math.min(x - tooltip.offsetWidth / 2, root.clientWidth - tooltip.offsetWidth - 8))}px`;
            targets.forEach((target, i) => target.setAttribute('tabindex', i === index ? '0' : '-1'));
        };
        rows.forEach((row, index) => {
            const x = salesPoints[index].x;
            const left = index ? (salesPoints[index - 1].x + x) / 2 : 0;
            const right = index < rows.length - 1 ? (x + salesPoints[index + 1].x) / 2 : 640;
            const target = svgNode('rect', {
                x: left, y: 0, width: right - left, height: 240, fill: 'transparent',
                class: 'analytics-month-target', role: 'button', tabindex: index ? -1 : 0,
                'aria-label': `${row.month_label || row.month || ''} ${row.year || ''}. Sales ${currency.format(Number(row.sales || 0))}. Expenses ${currency.format(Number(row.expenses || 0))}.`,
            });
            target.addEventListener('pointerenter', () => show(index));
            target.addEventListener('pointerdown', event => { pinned = event.pointerType === 'touch'; show(index); });
            target.addEventListener('click', () => show(index));
            target.addEventListener('focus', () => show(index));
            target.addEventListener('keydown', event => {
                if (event.key === 'Escape') { hide(); return; }
                if (['Enter', ' '].includes(event.key)) { event.preventDefault(); show(index); return; }
                const next = event.key === 'Home' ? 0 : event.key === 'End' ? rows.length - 1
                    : event.key === 'ArrowLeft' ? Math.max(0, index - 1)
                    : event.key === 'ArrowRight' ? Math.min(rows.length - 1, index + 1) : null;
                if (next != null) { event.preventDefault(); targets[next].focus(); }
            });
            targets.push(target);
            overlay.append(target);
        });
        overlay.append(guide);
        svg.append(overlay);
        // Interactive month targets must remain exposed to assistive technology.
        svg.setAttribute('role', 'group');
        const leave = () => { if (!pinned && !targets.includes(document.activeElement)) hide(); };
        const blur = event => { if (!targets.includes(event.relatedTarget)) hide(); };
        const outside = event => { if (!root.contains(event.target)) hide(); };
        svg.addEventListener('pointerleave', leave);
        svg.addEventListener('focusout', blur);
        document.addEventListener('pointerdown', outside);
        window.addEventListener('resize', hide);
        instances.set(svg, () => {
            svg.removeEventListener('pointerleave', leave);
            svg.removeEventListener('focusout', blur);
            document.removeEventListener('pointerdown', outside);
            window.removeEventListener('resize', hide);
            overlay.remove();
            tooltip.remove();
        });
    };
    window.SafeBooksTrendTooltip = { render, clear };
})();
