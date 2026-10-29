/* Execute the shared notification helper without making application requests. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8').replace(/\r\n/g, '\n');
const shared = read('static/js/app_shared.js');
const flow = shared.slice(shared.indexOf('    const escapeHtml ='), shared.indexOf('    const confirmLogout ='));
const make = bootstrap => {
    const context = {timers: [], instances: [], document: {createElement() {
        return {attributes: {}, events: {}, classes: new Set(),
            setAttribute(key, value) {this.attributes[key] = value;},
            addEventListener(key, handler) {this.events[key] = handler;},
            remove() {this.removed = true;},
            get classList() {return {add: value => this.classes.add(value)};},
        };
    }}};
    context.window = {setTimeout: (handler, delay) => context.timers.push({handler, delay})};
    if (bootstrap) context.window.bootstrap = {Toast: class {
        constructor(element, options) {this.element = element; this.options = options; context.instances.push(this);}
        show() {this.shown = true;}
        dispose() {this.disposed = true;}
    }};
    context.container = {children: [], appendChild(element) {this.children.push(element);}};
    vm.runInNewContext(flow + '\nthis.notify = showToast;', context);
    return context;
};
for (const bootstrap of [true, false]) {
    const page = make(bootstrap);
    page.notify(null, 'No target');
    assert.equal(page.container.children.length, 0);
    for (const level of ['', 'success', 'warning', 'danger', 'info', 'safebooks-toast-welcome']) {
        page.notify(page.container, 'Synthetic <img src=x onerror=bad()> notice', level, {delay: 2400});
        const toast = page.container.children.at(-1);
        assert(toast.className.includes('safebooks-toast'));
        assert(toast.className.includes(level));
        assert(!toast.innerHTML.includes('<img'));
        assert(toast.innerHTML.includes('&lt;img'));
        assert.equal(toast.attributes.role, 'status');
        assert.equal(toast.attributes['aria-live'], 'polite');
        assert.equal(toast.attributes['aria-atomic'], 'true');
        if (bootstrap) {
            const instance = page.instances.at(-1);
            assert.equal(instance.options.delay, 2400);
            assert.equal(instance.options.autohide, true);
            assert(instance.shown);
            toast.events['hidden.bs.toast']();
        } else {
            assert(toast.classes.has('show'), 'Fallback must remain visible with Bootstrap CSS loaded');
            const timer = page.timers.at(-1);
            assert.equal(timer.delay, 2400);
            timer.handler();
        }
        assert(toast.removed);
    }
    page.notify(page.container, '');
    assert(page.container.children.at(-1).innerHTML.includes('Action completed.'));
    if (bootstrap) assert.equal(page.instances.at(-1).options.delay, 2800);
    else assert.equal(page.timers.at(-1).delay, 2800);

    const initial = page.container.children.length;
    page.notify(page.container, 'Repeated validation warning');
    const repeated = page.container.children.at(-1);
    for (let i = 0; i < 20; i++) page.notify(page.container, 'Repeated validation warning');
    assert.equal(page.container.children.length, initial + 1, 'Identical active notices must not stack');
    page.notify(page.container, 'Another warning');
    page.notify(page.container, 'Repeated validation warning', 'danger');
    assert.equal(page.container.children.length, initial + 3, 'Different messages or severity remain independent');
    if (bootstrap) repeated.events['hidden.bs.toast']();
    else page.timers.at(-3).handler();
    page.notify(page.container, 'Repeated validation warning');
    assert.equal(page.container.children.length, initial + 4, 'A later notice can show again after cleanup');
}
for (const base of ['templates/base/bookkeeper_base.html', 'templates/admin_panel/admin_base.html']) {
    const source = read(base);
    assert(source.includes('toast-container position-fixed top-0 end-0'));
    assert.equal((source.match(/id="uiToastContainer"/g) || []).length, 1);
}
for (const page of ['clients', 'financial_records', 'financial_records_client']) {
    assert(!read(`templates/base/${page}.html`).includes('{% block toast_container %}'));
}
const fallback = read('static/js/admin_settings_page.js');
assert(fallback.includes('position-fixed top-0 end-0'));
assert(!fallback.includes('position-fixed bottom-0 end-0'));
const css = read('static/css/style.css');
assert(css.includes('@media (prefers-reduced-motion: reduce) {\n    .safebooks-toast'));
assert(css.includes('animation: safebooks-toast-enter 180ms ease-out'));
assert(css.includes('max-height: calc(100dvh - 1rem)'));
assert(css.includes('overflow-y: auto'));
console.log('Toast tests passed: top-right inheritance, semantic classes, escaped messages, live regions, Bootstrap/fallback visibility, timing and cleanup.');
