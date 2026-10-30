const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/admin/delegations.js', 'utf8');
const start = source.indexOf('        async function initDelegacionesView()');
const end = source.indexOf('        function renderizarDelegacionesCards(', start);
assert.ok(start >= 0 && end > start);

function node() {
    return {
        listeners: [], attributes: {}, innerHTML: '',
        addEventListener(name, handler) { this.listeners.push({name, handler}); },
        setAttribute(name, value) { this.attributes[name] = value; },
        removeAttribute(name) { delete this.attributes[name]; },
    };
}
const grid = node(), body = node(), search = node(), status = node(), size = node(), mode = node();
const nodes = {delegacionesCardsGrid: grid, tablaDelegacionesBody: body,
    buscarDelegaciones: search, estadoDelegaciones: status, tamanoPaginaDelegaciones: size,
    'view-delegaciones': {classList: {contains: () => true}}};
let resolve, reject, loads = 0, renders = 0, alerts = 0;
const context = vm.createContext({
    document: {getElementById: id => nodes[id] || null, querySelectorAll: () => [mode]},
    window: {Swal: {}}, Swal: {fire() { alerts++; }},
    console: {warn() {}}, controlesDelegacionesInicializados: false,
    vistaDelegacionesActiva: 'cards', filtroZonaActivo: 'todas',
    seleccionarVistaDelegaciones() {}, buscarDelegaciones() {}, filtrarEstadoDelegaciones() {},
    renderizarDelegacionesCards() { renders++; },
    cargarCatalogosOrganizacion() { loads++; return new Promise((ok, fail) => { resolve = ok; reject = fail; }); }
});
vm.runInContext(source.slice(start, end), context);
(async () => {
    const first = context.initDelegacionesView();
    assert.match(grid.innerHTML, /Cargando delegaciones/);
    assert.equal(grid.attributes['aria-busy'], 'true');
    resolve(); await first;
    const second = context.initDelegacionesView();
    resolve(); await second;
    assert.equal(loads, 2);
    assert.equal(renders, 2);
    for (const element of [search, status, size, mode]) assert.equal(element.listeners.length, 1);
    const third = context.initDelegacionesView();
    reject(new Error('sin conexión')); await third;
    assert.match(grid.innerHTML, /No se pudieron cargar/);
    assert.equal(grid.attributes['aria-busy'], undefined);
    assert.equal(alerts, 1);
    console.log('OK: carga de delegaciones, error visible y eventos registrados una sola vez.');
})().catch(error => { console.error(error); process.exitCode = 1; });
