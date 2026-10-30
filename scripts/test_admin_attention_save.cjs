const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/admin/attentions.js', 'utf8');
function section(start, end) {
    const a = source.indexOf(start), b = source.indexOf(end, a);
    assert.ok(a >= 0 && b > a);
    return source.slice(a, b);
}

const nodes = Object.fromEntries(Object.entries({
    atencionEditId: '', txtAtencionNombre: 'María Pérez', txtAtencionTelefono: '912345678',
    txtAtencionFecha: '2026-10-29', selAtencionDelegacion: 'Centro', selAtencionTipo: '2',
    selAtencionSubtipo: '3', selAtencionVecino: '', txtAtencionProblema: 'Solicitud',
    txtAtencionAccion: 'Orientación entregada', btnGuardarAtencionDB: '',
}).map(([key, value]) => [key, {value, disabled: false, readOnly: false}]));
let resolveSave, calls = 0;
const alerts = [];
const ctx = vm.createContext({
    document: {getElementById: id => nodes[id]},
    window: {vecinosAtencionCatalogo: [{id: 12, nombre: 'Vecina vinculada', telefono: '912345678'}]},
    Swal: {fire: async options => { alerts.push(options); }}, getCookie: () => '',
    fetch: () => { calls++; return new Promise(resolve => { resolveSave = resolve; }); },
    bsModalNuevaAtencion: {hide() {}}, cargarAtencionesDB: async () => false,
});
vm.runInContext(section('        function completarDatosVecinoAtencion()', '        async function abrirModalNuevaAtencion('), ctx);
vm.runInContext(section('        let guardandoAtencion = false;', '        function editarAtencion('), ctx);
(async () => {
    nodes.selAtencionVecino.value = '12';
    ctx.completarDatosVecinoAtencion();
    assert.equal(nodes.txtAtencionNombre.value, 'Vecina vinculada');
    assert.equal(nodes.txtAtencionNombre.readOnly, true);
    assert.equal(nodes.txtAtencionTelefono.readOnly, true);
    nodes.selAtencionVecino.value = '';
    ctx.completarDatosVecinoAtencion();
    assert.equal(nodes.txtAtencionNombre.readOnly, false);
    assert.equal(nodes.txtAtencionTelefono.readOnly, false);
    const first = ctx.guardarAtencionDB();
    await ctx.guardarAtencionDB();
    assert.equal(calls, 1, 'la acción pendiente no debe enviar solicitudes duplicadas');
    resolveSave({ok: true, json: async () => ({success: true, message: 'Guardada'})});
    await first;
    assert.equal(alerts.at(-1).icon, 'warning');
    assert.match(alerts.at(-1).text, /se guardaron.*no se pudo actualizar/i);
    assert.equal(nodes.btnGuardarAtencionDB.disabled, false);
    console.log('OK: vínculo de vecino, envío único y aviso correcto si falla la recarga.');
})().catch(error => { console.error(error); process.exitCode = 1; });
