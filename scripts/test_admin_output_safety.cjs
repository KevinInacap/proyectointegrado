const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function between(source, start, end) {
    const a = source.indexOf(start), b = source.indexOf(end, a);
    assert.ok(a >= 0 && b > a, `No se encontró ${start}`);
    return source.slice(a, b);
}

const common = fs.readFileSync('static/js/admin/admin-bundle.js', 'utf8');
const attentions = fs.readFileSync('static/js/admin/attentions.js', 'utf8');
const reports = fs.readFileSync('static/js/admin/reports.js', 'utf8');
const tbody = {innerHTML: ''};
let exported;
const context = vm.createContext({
    document: {
        getElementById: id => id === 'tablaAtencionesBody' ? tbody : null,
        createElement: () => ({click() {}})
    },
    filasPorPaginaAtenciones: 10, paginaActualAtenciones: 1,
    logsFiltradosAuditoria: [{timestamp: 'hoy', admin_name: '=1+1', admin_username: 'x";=2',
        action: 'EDIT', description: '  @formula', affected_table: 'vecino', affected_record_id: 1}],
    Blob: class { constructor(parts) { exported = parts.join(''); } },
    URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}},
    mostrarToast() {}
});
vm.runInContext(between(common, '        function escapeHtml(', '        let calFechaActual'), context);
vm.runInContext(between(attentions, '        function renderTablaAtenciones(', '        let catalogsForAttentionForm'), context);
vm.runInContext(between(reports, '        function exportarExcelAuditoria(', '        function exportarGraficoPNG'), context);
context.renderTablaAtenciones([{id: 1, delegation: '" onmouseover="alert(1)', date: '<img src=x>', stage: '<script>', contact_name: '<b>Persona</b>'}]);
assert.ok(tbody.innerHTML.includes('title="&quot; onmouseover=&quot;alert(1)"'));
assert.ok(!tbody.innerHTML.includes('<img src=x>'));
assert.ok(!tbody.innerHTML.includes('<script>'));
context.exportarExcelAuditoria();
assert.ok(exported.includes('"\'=1+1"'));
assert.ok(exported.includes('"x"";=2"'));
assert.ok(exported.includes('"\'  @formula"'));
console.log('OK: datos de atención codificados y CSV de auditoría protegido.');
