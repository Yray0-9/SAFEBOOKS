const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const rootPath = path.resolve(__dirname, '../../..');
class Element {
    constructor() { this.children = []; this.style = {}; this.attributes = {}; this.textContent = ''; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(key, value) { this.attributes[key] = value; }
    removeAttribute(key) { delete this.attributes[key]; }
}
const context = { window: {}, Intl, document: { createElement: () => new Element(), createTextNode: text => ({ textContent: text }) } };
vm.runInNewContext(fs.readFileSync(path.join(rootPath, 'static/js/analytics_tax_breakdown.js'), 'utf8'), context);
const { prepare, render, state } = context.window.SafeBooksTaxBreakdown;
const amounts = [{ type_code: 'BIR Form 0619E', amount: .1 }, { type_code: 'BIR Form 2551Q', amount: .2 }];
assert.equal(prepare(amounts, .3).total, 30);
assert.equal(prepare(amounts, .4), null, 'Never show a chart that disagrees with recorded Tax total');
assert.equal(prepare([{ amount: -1 }], -1), null);
assert.equal(prepare([{ amount: Infinity }], 0), null);
assert.equal(prepare(undefined, 0), null, 'An old or missing response is unavailable, not no records');
assert.equal(prepare([], null), null);
const nodes = Object.fromEntries(['content', 'rows', 'ring', 'total', 'status', 'caption'].map(name => [`[data-tax-${name}]`, new Element()]));
const root = { querySelector: selector => nodes[selector] };
const payload = { summary: { total_tax: .3 }, tax_breakdown: amounts, tax_breakdown_year: 2026 };
const before = JSON.stringify(payload);
render(root, payload, '2026');
assert.equal(JSON.stringify(payload), before, 'Rendering must not modify source amounts');
assert.equal(nodes['[data-tax-rows]'].children.length, 2);
assert.equal(nodes['[data-tax-content]'].hidden, false);
assert(nodes['[data-tax-ring]'].style.background.startsWith('conic-gradient('));
assert.equal(nodes['[data-tax-rows]'].children[0].children[2].textContent, '66.7%');
assert(nodes['[data-tax-caption]'].textContent.startsWith('2026'));
render(root, { summary: { total_tax: 0 }, tax_breakdown: [{ amount: 0 }] }, '2025');
assert.equal(nodes['[data-tax-content]'].hidden, true);
assert.equal(nodes['[data-tax-rows]'].children.length, 0);
assert(nodes['[data-tax-status]'].textContent.includes('No recorded tax'));
render(root, payload, '2026');
state(root, 'Loading tax breakdown…');
assert.equal(nodes['[data-tax-rows]'].children.length, 0);
assert.equal(nodes['[data-tax-ring]'].style.background, '');
render(root, {}, '2026');
assert(nodes['[data-tax-status]'].textContent.includes('unavailable'));
const unsafe = '<img src=x onerror=alert(1)>';
render(root, { summary: { total_tax: 1 }, tax_breakdown: [{ type_code: unsafe, amount: 1 }] }, '2026');
assert.equal(nodes['[data-tax-rows]'].children[0].children[0].children[1].textContent, unsafe, 'Labels are text, never HTML');
console.log('Tax breakdown passed: cents, reconciliation, shares, safe labels, immutable input, zero/empty/loading/failure cleanup.');
