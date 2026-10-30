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
    mostrarToast() {}, setTimeout() { return 1; }, clearTimeout() {},
});
vm.runInContext(section('        function escapeHtml(', '        let calFechaActual'), context);
vm.runInContext(section('        let animacionFichaDelegacion', '        function exportarFichaDelegacionPDF'), context);
context.seleccionarDelegacion('centro');
assert.equal(panel.innerHTML.includes(attack), false);
assert.equal(panel.innerHTML.includes('&lt;img src=x onerror=alert(1)&gt;'), true);
assert.equal(panel.style.display, 'block');
const motions = [];
let cancelled = 0;
context.window.matchMedia = () => ({matches:false});
panel.animate = (frames, options) => { motions.push({frames, options}); return {cancel() { cancelled++; }}; };
context.seleccionarDelegacion('centro');
assert.equal(motions.length, 1);
assert.equal(motions[0].options.duration, 650, 'la ficha debe aparecer con una transición suave y visible');
context.seleccionarDelegacion('centro');
assert.equal(cancelled, 1, 'una selección repetida cancela la animación anterior');
context.window.matchMedia = () => ({matches:true});
context.seleccionarDelegacion('centro');
assert.equal(motions.length, 2, 'movimiento reducido no debe iniciar animaciones');
assert.equal(cancelled, 2, 'movimiento reducido cancela la transición en curso');
console.log('OK: ficha de delegación escapa datos, anima la selección y respeta movimiento reducido.');
