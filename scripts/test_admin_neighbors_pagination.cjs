const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/admin/neighbors.js'), 'utf8');
const template = fs.readFileSync(path.join(__dirname, '../templates/activities/admin/views/vecinos.html'), 'utf8');
class Element {
    constructor() { this.children = []; this.style = {setProperty() {}}; this.classList = {add(){}, remove(){}}; this.value = ''; this.checked = true; this.attributes = {}; this.textContent = ''; }
    set innerHTML(value) { this.html = value; this.children = []; }
    get innerHTML() { return this.html || ''; }
    appendChild(child) { this.children.push(child); }
    append(child) { this.appendChild(child); }
    setAttribute(key, value) { this.attributes[key] = value; }
    addEventListener(event, fn) { this[event] = fn; }
}
const ids = ['tablaVecinosBody', 'paginadorPills', 'searchVecinosInput', 'filtroEstadoVecino', 'filtroTerritorioVecino', 'contenedorChipsFiltros', 'badgeFiltrosActivos', 'lblRegistrosInfo', 'colRUT', 'colDireccion', 'colTelefono', 'colTerritorio', 'colEstado'];
const nodes = Object.fromEntries(ids.map(id => [id, new Element()]));
const columnStates = [];
const document = {getElementById: id => nodes[id] || null, createElement: () => new Element(), createTextNode: text => ({textContent:text}), querySelectorAll: selector => { const cell = new Element(); columnStates.push([selector, cell]); return [cell]; }};
const records = Array.from({length:25}, (_, i) => ({id:i+1, nombre:`Vecino ${String(i+1).padStart(2, '0')}`, rut:`${i+1}`, direccion:'Calle 1', telefono:'', territorio:i<21?'Centro':'Norte', estado:i<23?'Activo':'Inactivo'}));
const ctx = vm.createContext({document, window:{}, console, Intl, Date, datasetVecinos:records, filasFiltradasVecinos:[], seleccionadosIds:new Set(), filasPorPagina:10, paginaActual:1, ordenAsc:true, columnaOrdenVecinos:'nombre', fetch:async()=>({ok:true, json:async()=>({success:true, vecinos:records})})});
vm.runInContext(source, ctx);
ctx.actualizarIndicadoresDiscretos = () => {};
ctx.actualizarBarraAccionesMasivas = () => {};
ctx.actualizarOpcionesTerritorioVecinos = () => {};
const pages = () => nodes.paginadorPills.children.filter(item => item.click);
(async () => {
    assert.match(template, /id="searchVecinosInput"\s+oninput=/);
    ctx.ejecutarFiltroCompletoVecinos();
    assert.equal(pages().length, 3);
    assert.match(nodes.lblRegistrosInfo.textContent, /1 - 10 de 25/);
    pages()[1].click();
    assert.match(nodes.lblRegistrosInfo.textContent, /11 - 20 de 25/);
    nodes.colRUT.checked = false;
    pages()[2].click();
    assert.match(nodes.lblRegistrosInfo.textContent, /21 - 25 de 25/);
    assert.equal(columnStates.filter(([selector]) => selector === '.col-rut').at(-1)[1].style.display, 'none');
    await ctx.cargarVecinosDesdeDB();
    assert.match(nodes.lblRegistrosInfo.textContent, /21 - 25 de 25/, 'la recarga conserva la página válida');
    records.splice(20);
    await ctx.cargarVecinosDesdeDB();
    assert.match(nodes.lblRegistrosInfo.textContent, /11 - 20 de 20/, 'la página se ajusta si desaparece la última');
    nodes.searchVecinosInput.value = 'Vecino';
    nodes.filtroEstadoVecino.value = 'Activo';
    nodes.filtroTerritorioVecino.value = 'Centro';
    ctx.ejecutarFiltroCompletoVecinos();
    assert.match(nodes.lblRegistrosInfo.textContent, /1 - 10 de 20/);
    pages()[1].click();
    assert.match(nodes.lblRegistrosInfo.textContent, /11 - 20 de 20/);
    nodes.searchVecinosInput.value = 'inexistente';
    ctx.ejecutarFiltroCompletoVecinos();
    assert.equal(nodes.lblRegistrosInfo.textContent, '0 registros');
    assert.equal(pages().length, 0);
    ctx.limpiarFiltrosVecinos();
    assert.match(nodes.lblRegistrosInfo.textContent, /1 - 10 de 20/);
    console.log('OK: búsqueda, filtros, paginación, actualización y columnas de vecinos.');
})().catch(error => {console.error(error); process.exitCode = 1;});
