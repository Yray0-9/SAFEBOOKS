(() => {
    const money = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' });
    const colors = ['#2563eb', '#7c3aed', '#0d9488', '#d97706', '#db2777', '#0891b2', '#4f46e5', '#65a30d'];
    const prepare = (rows, expectedTotal) => {
        if (!Array.isArray(rows)) return null;
        const result = [];
        for (const row of rows) {
            const amount = Number(row.amount);
            if (row.amount == null || !Number.isFinite(amount) || amount < 0) return null;
            const cents = Math.round(amount * 100);
            if (cents) result.push({ label: String(row.type_code || 'Other tax'), cents });
        }
        result.sort((a, b) => b.cents - a.cents || a.label.localeCompare(b.label));
        const total = result.reduce((sum, row) => sum + row.cents, 0);
        if (expectedTotal == null || !Number.isFinite(Number(expectedTotal)) || Math.round(Number(expectedTotal) * 100) !== total) return null;
        return { rows: result, total };
    };
    const state = (root, message) => {
        if (!root) return;
        root.querySelector('[data-tax-content]').hidden = true;
        root.querySelector('[data-tax-rows]').replaceChildren();
        root.querySelector('[data-tax-ring]').style.background = '';
        root.querySelector('[data-tax-ring]').removeAttribute('aria-label');
        root.querySelector('[data-tax-total]').textContent = '';
        const status = root.querySelector('[data-tax-status]');
        status.hidden = false;
        status.textContent = message;
    };
    const render = (root, payload) => {
        if (!root) return;
        const year = payload?.tax_breakdown_year;
        root.querySelector('[data-tax-caption]').textContent = `${year || 'All recorded years'} · Recorded amounts`;
        const data = prepare(payload?.tax_breakdown, payload?.summary?.total_tax);
        if (!data) return state(root, 'Tax breakdown unavailable. Please retry.');
        if (!data.total) return state(root, 'No recorded tax amounts for this year.');
        const body = root.querySelector('[data-tax-rows]');
        body.replaceChildren();
        let end = 0;
        const segments = data.rows.map((row, index) => {
            const start = end;
            end += row.cents / data.total * 100;
            const color = colors[index % colors.length];
            const tr = document.createElement('tr');
            const label = document.createElement('th');
            label.scope = 'row';
            const dot = document.createElement('i');
            dot.className = 'analytics-tax-dot';
            dot.style.backgroundColor = color;
            dot.setAttribute('aria-hidden', 'true');
            label.append(dot, document.createTextNode(row.label));
            tr.append(label);
            for (const text of [money.format(row.cents / 100), `${(row.cents / data.total * 100).toFixed(1)}%`]) {
                const td = document.createElement('td');
                td.textContent = text;
                tr.append(td);
            }
            body.append(tr);
            return `${color} ${start}% ${end}%`;
        });
        const ring = root.querySelector('[data-tax-ring]');
        ring.style.background = `conic-gradient(${segments.join(',')})`;
        ring.setAttribute('aria-label', `Recorded tax total ${money.format(data.total / 100)}. Breakdown amounts and percentages are in the adjacent table.`);
        root.querySelector('[data-tax-total]').textContent = money.format(data.total / 100);
        root.querySelector('[data-tax-status]').hidden = true;
        root.querySelector('[data-tax-content]').hidden = false;
    };
    window.SafeBooksTaxBreakdown = { prepare, render, state };
})();
