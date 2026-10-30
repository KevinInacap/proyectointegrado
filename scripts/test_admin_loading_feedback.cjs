const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function button() {
    return {
        disabled: false, children: [], attributes: {},
        append(child) { this.children.push(child); child.parent = this; },
        setAttribute(key, value) { this.attributes[key] = value; },
        removeAttribute(key) { delete this.attributes[key]; }
    };
}
function indicator() {
    return {
        setAttribute() {},
        remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
    };
}

async function testNavigation() {
    const source = fs.readFileSync('static/js/admin/admin-bundle.js', 'utf8');
    const start = source.indexOf('        const adminViewRequests = new Map();');
    const end = source.indexOf('        function switchView(', start);
    assert.ok(start >= 0 && end > start);
    const option = button();
    const context = vm.createContext({document: {
        getElementById: id => id === 'sub-cargos' ? option : null,
        createElement: indicator,
    }, console: {warn() {}}});
    vm.runInContext(source.slice(start, end), context);
    let resolve, calls = 0;
    const load = () => { calls++; return new Promise(done => { resolve = done; }); };
    const first = context.loadAdminView('cargos', load);
    const second = context.loadAdminView('cargos', load);
    assert.equal(first, second, 'Dos selecciones simultáneas comparten la misma consulta');
    assert.equal(option.attributes['aria-busy'], 'true');
    assert.equal(option.children.length, 1);
    await Promise.resolve();
    assert.equal(calls, 1);
    resolve();
    await first;
    await Promise.resolve();
    assert.equal(option.children.length, 0);
    assert.equal(option.attributes['aria-busy'], undefined);

    const failing = context.loadAdminView('cargos', () => Promise.reject(new Error('offline')));
    await failing.catch(() => {});
    await Promise.resolve();
    assert.equal(option.children.length, 0, 'Un fallo también retira el indicador');
    assert.equal(option.attributes['aria-busy'], undefined);
}

async function testModalTriggerAndFocus() {
    const source = fs.readFileSync('static/js/admin/form-feedback.js', 'utf8');
    const events = {};
    let shown, resolve;
    const hidden = {getClientRects: () => [], focus() { throw Error('No enfocar un panel oculto'); }};
    let focused = false;
    const visible = {getClientRects: () => [1], focus() { focused = true; }};
    const modal = {addEventListener(name, fn) { if (name === 'shown.bs.modal') shown = fn; },
        querySelectorAll: () => [hidden, visible]};
    const trigger = button();
    const document = {
        addEventListener(name, fn) { (events[name] ||= []).push(fn); },
        querySelectorAll(selector) { return selector === '.modal' ? [modal] : []; },
        querySelector: () => null, getElementById: () => null, createElement: indicator,
    };
    const window = {abrirModalRol: () => new Promise(done => { resolve = done; })};
    const context = vm.createContext({document, window, MutationObserver: class {},
        queueMicrotask() {}, requestAnimationFrame() {}});
    vm.runInContext(source, context);
    events.DOMContentLoaded[0]();
    events.click.forEach(fn => fn({target: {closest: selector => selector === 'button' ? trigger : null}}));
    const request = window.abrirModalRol('nuevo');
    assert.equal(trigger.disabled, true);
    assert.equal(trigger.attributes['aria-busy'], 'true');
    assert.equal(trigger.children.length, 1);
    resolve();
    await request;
    assert.equal(trigger.disabled, false);
    assert.equal(trigger.children.length, 0);
    assert.equal(trigger.attributes['aria-busy'], undefined);
    shown();
    assert.equal(focused, true, 'El foco entra al primer campo visible del modal');
}

function testCatalogNavigationLoading() {
    const source = fs.readFileSync('static/js/admin/form-feedback.js', 'utf8');
    const option = button();
    option.querySelector = () => option.children[0] || null;
    let busy = true, observerCallback;
    const view = {id: 'view-metas', querySelector: () => busy ? {} : null};
    const root = {closest: () => view, matches: selector => selector === '[data-catalog]',
        classList: {contains: () => false}};
    const main = {querySelectorAll: () => [root]};
    const events = {};
    const document = {
        addEventListener(name, fn) { (events[name] ||= []).push(fn); },
        querySelectorAll: () => [], querySelector: () => main,
        getElementById: id => id === 'sub-metas' ? option : null,
        createElement: indicator,
    };
    const context = vm.createContext({document, window: {},
        MutationObserver: class {constructor(callback) { observerCallback = callback; } observe() {}},
        queueMicrotask() {}, requestAnimationFrame() {}});
    vm.runInContext(source, context);
    events.DOMContentLoaded[0]();
    assert.equal(option.children.length, 1, 'Se indica una consulta iniciada antes del observador');
    assert.equal(option.attributes['aria-busy'], 'true');
    busy = false;
    observerCallback([{type: 'attributes', attributeName: 'aria-busy', target: root}]);
    assert.equal(option.children.length, 0);
    assert.equal(option.attributes['aria-busy'], undefined);
}

(async () => {
    await testNavigation();
    await testModalTriggerAndFocus();
    testCatalogNavigationLoading();
    console.log('OK: indicadores de carga reales, consultas compartidas y foco visible.');
})().catch(error => { console.error(error); process.exitCode = 1; });
