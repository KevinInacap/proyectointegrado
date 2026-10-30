const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/admin/roles.js', 'utf8').replace(/\r\n/g, '\n');
function section(start, end) {
    const a = source.indexOf(start), b = source.indexOf(end, a);
    assert.ok(a >= 0 && b > a);
    return source.slice(a, b);
}

const btn = {disabled: false};
let resolve, requests = 0;
const context = vm.createContext({
    document: {getElementById: () => btn}, rolEliminarId: 12, eliminandoRol: false,
    datasetRoles: [{id: 12, name: 'Personalizado'}], bsModalEliminarRol: {hide() {}},
    getCookie: () => '', renderTarjetasPermisosRoles() {}, filtrarRoles() {}, mostrarToast() {},
    fetch() { requests++; return new Promise(done => { resolve = done; }); },
    Swal: {fire() {}}, console,
});
vm.runInContext(section('        function rolProtegido(', '        function renderTablaRoles('), context);
vm.runInContext(section('        async function ejecutarEliminarRolConfirmado(', '        // ==============================================================================\n        // DUPLICAR ROL'), context);
for (const role of [{is_system: true}, {is_base_role: true}, {is_admin_role: true},
    {name: 'Operador'}, {name: 'Consultor'}, {name: 'Verificador'}]) {
    assert.equal(context.rolProtegido(role), true);
}
assert.equal(context.rolProtegido({name: 'Personalizado'}), false);

(async () => {
    const first = context.ejecutarEliminarRolConfirmado();
    const second = context.ejecutarEliminarRolConfirmado();
    assert.equal(requests, 1, 'Dos clics no deben enviar dos bajas');
    assert.equal(btn.disabled, true);
    resolve({json: async () => ({success: true, message: 'Rol eliminado'})});
    await Promise.all([first, second]);
    assert.equal(btn.disabled, false);
    assert.equal(context.datasetRoles.length, 0);
    console.log('OK: roles protegidos y prevención de bajas duplicadas.');
})().catch(error => { console.error(error); process.exitCode = 1; });
