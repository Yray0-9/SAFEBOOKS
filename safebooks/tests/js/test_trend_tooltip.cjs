const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class Element {
    constructor() { this.attributes = {}; this.children = []; this.listeners = {}; this.style = {}; this.clientWidth = 300; this.offsetWidth = 200; }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    append(...children) { children.forEach(child => { child.parent = this; this.children.push(child); }); }
    remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
    addEventListener(event, fn) { (this.listeners[event] ||= new Set()).add(fn); }
    removeEventListener(event, fn) { this.listeners[event]?.delete(fn); }
    emit(event, data = {}) { for (const fn of this.listeners[event] || []) fn(data); }
    getBoundingClientRect() { return { left: 0, width: 300 }; }
    contains(target) { return target === this || this.children.some(child => child.contains(target)); }
    focus() { doc.activeElement = this; this.emit('focus'); }
}
const root = new Element(), svg = new Element(), doc = new Element(), win = new Element();
svg.closest = () => root;
root.append(svg);
doc.createElement = () => new Element();
doc.createElementNS = () => new Element();
const context = { document: doc, window: win, Intl, WeakMap };
vm.runInNewContext(fs.readFileSync(path.resolve(__dirname, '../../../static/js/analytics_trend_tooltip.js'), 'utf8'), context);
const { render, clear } = win.SafeBooksTrendTooltip;
const rows = [{ year: 2026, month_label: 'Nov', sales: 75000.25, expenses: 0 }, { year: 2026, month_label: 'Dec', sales: 100, expenses: 20 }];
const before = JSON.stringify(rows);
const points = [{ x: 34, y: 16 }, { x: 622, y: 190 }];
render(svg, rows, points, [{ x: 34, y: 206 }, { x: 622, y: 200 }]);
let tooltip = root.children[1], overlay = svg.children[0];
const [nov, dec, guide] = overlay.children;
nov.emit('pointerenter');
assert.equal(tooltip.hidden, false);
assert.equal(tooltip.children[0].textContent, 'Nov 2026');
assert(tooltip.children[1].textContent.includes('75,000.25'));
assert(tooltip.children[2].textContent.includes('0.00'), 'Returned zero is shown exactly');
assert.equal(guide.children[1].attributes.cy, '16');
assert.equal(guide.children[2].attributes.cy, '206');
assert.equal(tooltip.style.left, '8px', 'First-month tooltip stays inside the chart');
svg.emit('pointerleave');
assert.equal(tooltip.hidden, true);
nov.focus();
nov.emit('keydown', { key: 'ArrowRight', preventDefault() {} });
assert.equal(doc.activeElement, dec);
assert.equal(tooltip.children[0].textContent, 'Dec 2026');
assert.equal(tooltip.style.left, '92px', 'Last-month tooltip stays inside the chart');
dec.emit('keydown', { key: 'Home', preventDefault() {} });
assert.equal(doc.activeElement, nov);
nov.emit('keydown', { key: 'Escape' });
assert.equal(tooltip.hidden, true);
doc.activeElement = null;
dec.emit('pointerdown', { pointerType: 'touch' });
svg.emit('pointerleave');
assert.equal(tooltip.hidden, false, 'A touch selection stays visible');
doc.emit('pointerdown', { target: new Element() });
assert.equal(tooltip.hidden, true);
assert.equal(JSON.stringify(rows), before);
render(svg, rows, points, points);
assert.equal(doc.listeners.pointerdown.size, 1, 'Rerenders replace document listeners');
assert.equal(root.children.length, 2, 'No duplicate tooltips');
render(svg, [], [], []);
assert.equal(root.children.length, 1, 'Empty/failure resets remove old month information');
assert.equal(svg.children.length, 0);
assert.equal(doc.listeners.pointerdown.size, 0);
assert.equal(win.listeners.resize.size, 0);
clear(null);
console.log('Monthly tooltip passed: exact amounts, shared plotted points, hover, keyboard, touch, bounded position, immutable rows and cleanup.');
