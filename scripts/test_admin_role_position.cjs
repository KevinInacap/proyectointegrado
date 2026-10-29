const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/admin/roles.js', 'utf8');
const start = source.indexOf('        let solicitudCargoRol = 0;');
const end = source.indexOf('        function guardarRolSubmit(', start);
assert.ok(start >= 0 && end > start);

const elements = new Map();
const alerts = [];
const requests = [];
function element(id) {
    return {id, value: '', disabled: false, textContent: '', options: [],
        replaceChildren(option) { this.options = [option]; this.value = option.value; },
        add(option) { this.options.push(option); }, setAttribute() {}, removeAttribute() {}};
}
function get(id) { if (!elements.has(id)) elements.set(id, element(id)); return elements.get(id); }
const context = vm.createContext({
    document: {getElementById: get, querySelectorAll: () => [{value: 'usuarios.view'}]},
    Option: class {constructor(text, value) {this.text = text; this.value = String(value);}},
    datasetRoles: [{id: 7, name: 'Operador', description: 'Atención', position_id: 2,
        position_name: 'Gestor', permissions: ['usuarios.view'], is_base_role: false}],
    bsModalRol: {show() {}, hide() {}},
    renderPermisosMatrix() {}, filtrarRoles() {}, initRolesView: async () => true,
    cargarUsuariosDesdeDB: async () => {}, mostrarToast() {}, getCookie: () => 'csrf',
    Swal: {fire: async message => {alerts.push(message);}}, console,
    fetch: async (url, options) => {
        if (!options?.method) return {ok: true, json: async () => ({success: true,
            positions: [{id: 2, name: 'Gestor', status: 'Activo'}, {id: 3, name: 'Archivado', status: 'Inactivo'}]})};
        requests.push({url, payload: JSON.parse(options.body)});
        return {ok: true, json: async () => ({success: true, role: {id: 8}, message: 'Guardado'})};
    }
});
vm.runInContext(source.slice(start, end), context);
(async () => {
    await context.abrirModalRol('nuevo');
    assert.equal(get('rolFormCargo').options.length, 2, 'Solo se ofrecen cargos activos');
    get('rolFormNombre').value = 'Rol nuevo';
    get('rolFormDescripcion').value = 'Descripción';
    await context.ejecutarGuardarRol();
    assert.equal(requests.length, 0, 'Un rol sin cargo no se envía');
    assert.equal(alerts.at(-1).title, 'Campos requeridos');
    get('rolFormCargo').value = '2';
    await context.ejecutarGuardarRol();
    assert.equal(requests[0].payload.position_id, 2);
    assert.equal(requests[0].url, '/api/roles/create/');
    await context.abrirModalRol('duplicar', 7);
    assert.equal(get('rolFormId').value, '');
    assert.equal(get('rolFormCargo').value, '2');
    assert.match(get('rolFormNombre').value, /Copia/);
    await context.ejecutarGuardarRol();
    assert.equal(requests[1].payload.position_id, 2);
    assert.equal(requests[1].url, '/api/roles/create/');
    console.log('OK: rol y copia requieren cargo y envían su vínculo al servidor.');
})().catch(error => {console.error(error); process.exitCode = 1;});
