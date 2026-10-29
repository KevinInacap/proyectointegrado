const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = require('./admin_test_source.cjs')();
function section(start, end) {
    const first = source.indexOf(start), last = source.indexOf(end, first);
    assert.ok(first >= 0 && last > first);
    return source.slice(first, last);
}
const attack = '<img src=x onerror=alert(1)>';
const panel = {style:{}, innerHTML:'', animate() { throw new Error('Debe respetar movimiento reducido'); }, scrollIntoView() {}};
const context = vm.createContext({
    document: {querySelectorAll: () => [], getElementById: id => id === 'panelDetalleDelegacion' ? panel : null},
    window: {matchMedia: () => ({matches:true})},
    datasetDelegacionesDetalle: {centro:{id:'centro', dbStatus:'Activo', nombre:attack, sector:attack, direccion:attack, telefono:attack, horario:attack, delegado:attack, resumen:attack, statusSemaforo:'Sin medición', colorSemaforo:'#64748B', satisfaccion:'Sin datos', cumplimiento:null, atencionesMes:null, vecinosRegistrados:null, funcionarios:[{nombre:attack, cargo:attack, rol:attack, avatar:attack}], barrios:[attack], metricasAtencion:[]}},
    mostrarToast() {}, setTimeout() {},
});
vm.runInContext(section('        function escapeHtml(', '        let calFechaActual'), context);
vm.runInContext(section('        function seleccionarDelegacion(id)', '        function exportarFichaDelegacionPDF'), context);
context.seleccionarDelegacion('centro');
assert.equal(panel.innerHTML.includes(attack), false);
assert.equal(panel.innerHTML.includes('&lt;img src=x onerror=alert(1)&gt;'), true);
assert.equal(panel.style.display, 'block');
console.log('OK: ficha de delegación escapa datos y respeta movimiento reducido.');
