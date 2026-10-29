const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/admin/catalogs.js', 'utf8');
function slice(start, end) {
    const first = source.indexOf(start), last = source.indexOf(end, first);
    assert.ok(first >= 0 && last > first);
    return source.slice(first, last);
}
class Node {
    constructor(tag) { this.tag = tag; this.children = []; this.textContent = ''; this._html = ''; this.className = ''; this.style = {}; this.attributes = {}; }
    set innerHTML(value) { this._html = value; }
    get innerHTML() { return this._html; }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) { this.children = nodes; }
    setAttribute(key, value) { this.attributes[key] = value; }
    addEventListener() {}
}
const attack = '<img src=x onerror=alert(1)>';
let dialog;
const context = vm.createContext({
    document: { createElement: tag => new Node(tag) },
    definitions: {items: {title: 'ítem', columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['status', 'Estado']]}},
    request: async () => ({results: [{id: 1, code: attack, name: attack, description: attack, status: 'Activo'}], count: 1}),
    references: async () => ({}), panelQuery: () => '', endpoint: () => '/',
    syncReferenceFilters() {}, notice() {}, button: () => new Node('button'),
    Swal: {fire: async options => { dialog = options; return {isConfirmed: false}; }},
});
vm.runInContext(slice('    function escapeText(', '    function button('), context);
vm.runInContext(slice('    async function load(', '    function field('), context);
vm.runInContext(slice('    async function deleteRecord(', '    async function refreshRelated('), context);
(async () => {
    const body = new Node('tbody');
    const panel = {catalog:'items', revision:0, previous:{}, next:{}, body, root:new Node('div'), page:1, size:{value:'10'}, summary:{}};
    await context.load(panel);
    const cells = body.children[0].children;
    for (const cell of cells.slice(0, 3)) {
        assert.equal(cell.children[0].textContent, attack);
        assert.equal(cell.children[0].innerHTML, '');
    }
    assert.equal(context.element('span', '', attack).innerHTML, '');
    assert.equal(context.escapeText(attack), '&lt;img src=x onerror=alert(1)&gt;');
    await context.deleteRecord(panel, {id:1, name:attack});
    assert.equal(dialog.text.includes(attack), true);
    assert.equal(dialog.html, undefined);
    console.log('OK: datos de catálogo y confirmación se tratan como texto.');
})().catch(error => { console.error(error); process.exitCode = 1; });
