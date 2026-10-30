const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('static/js/admin/attentions.js', 'utf8');
const start = source.indexOf('        async function cargarTodasLasPaginasAtencion(');
const end = source.indexOf('        async function cargarCatalogosFormularioAtencion(', start);
assert.ok(start >= 0 && end > start);
const requested = [];
const records = Array.from({length: 75}, (_, i) => ({id: i + 1, name: `Tipo ${i + 1}`}));
let failSecondPage = false;
const context = vm.createContext({
    fetch: async url => {
        requested.push(url);
        const page = Number(new URL(url, 'http://localhost').searchParams.get('page'));
        if (failSecondPage && page === 2) return {ok: false};
        return {ok: true, json: async () => ({count: records.length, results: records.slice((page - 1) * 50, page * 50)})};
    },
});
vm.runInContext(source.slice(start, end), context);
(async () => {
    const result = await context.cargarTodasLasPaginasAtencion('/api/catalogs/attention-types/');
    assert.equal(result.length, 75);
    assert.equal(result[74].name, 'Tipo 75');
    assert.equal(requested.length, 2);
    failSecondPage = true;
    await assert.rejects(context.cargarTodasLasPaginasAtencion('/api/catalogs/attention-types/'), /catálogo completo/);
    console.log('OK: el formulario consulta todas las páginas del catálogo y comunica fallos.');
})().catch(error => { console.error(error); process.exitCode = 1; });
