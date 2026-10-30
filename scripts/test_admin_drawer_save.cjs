const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = require('./admin_test_source.cjs')();
const begin = source.indexOf('        async function ejecutarGuardadoDrawer()');
const end = source.indexOf('        window.ejecutarGuardadoDrawer = ejecutarGuardadoDrawer;', begin);
assert.ok(begin >= 0 && end > begin);
async function scenario(ok, refreshOk = true) {
    const fields = {drawerInputNombre:{value:'Ana Pérez'}, drawerInputDireccion:{value:'Calle 123'}, drawerInputTelefono:{value:'12345678'}, drawerSelectTerritorio:{value:'Delegación Centro'}, drawerSelectEstado:{value:'Activo'}, btnDrawerGuardar:{disabled:false}};
    const alerts = [], requests = [];
    let closed = false, reloaded = false;
    const ctx = vm.createContext({
        drawerActivoTipo:'vecino', drawerActivoId:1,
        datasetVecinos:[{id:1, rut:'12.345.678-5'}], datasetUsuarios:[],
        document:{getElementById: id => fields[id]},
        getCookie: () => 'token', validarEmail: () => true,
        fetch: async (url, options) => {requests.push({url, body:JSON.parse(options.body)}); return {ok, json:async () => ({success:ok, message: ok ? 'Guardado' : 'Rechazado'})};},
        cerrarAdminDrawer: () => {closed = true;}, cargarVecinosDesdeDB: async () => {reloaded = true; return refreshOk;}, cargarUsuariosDesdeDB: async () => {},
        Swal:{fire:async options => {alerts.push(options);}},
    });
    vm.runInContext(source.slice(begin, end), ctx);
    await ctx.ejecutarGuardadoDrawer();
    assert.equal(requests[0].url, '/api/vecinos/1/');
    assert.equal(requests[0].body.rut, '12.345.678-5');
    assert.equal(closed, ok);
    assert.equal(reloaded, ok);
    assert.equal(alerts[0].icon, ok ? (refreshOk ? 'success' : 'warning') : 'error');
    if (ok && !refreshOk) assert.match(alerts[0].text, /se guardó.*no se pudo actualizar/i);
    assert.equal(fields.btnDrawerGuardar.disabled, false);
}
Promise.all([scenario(true), scenario(false), scenario(true, false)]).then(() => console.log('OK: edición lateral informa el resultado de guardar y recargar.')).catch(error => {console.error(error); process.exitCode = 1;});
