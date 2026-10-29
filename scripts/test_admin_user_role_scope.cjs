const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/admin/users-form.js', 'utf8');
const start = source.indexOf('        function actualizarRolesSegunCargo(');
const end = source.indexOf('        function abrirModalUsuario(', start);
assert.ok(start >= 0 && end > start);
function checkbox(value, checked) {
    const label = {textContent: ''};
    return {value, checked, title: '', parentElement: {hidden: false, querySelector: () => label}, label};
}
const checks = [checkbox('1', true), checkbox('2', true), checkbox('3', false)];
const help = {};
const context = vm.createContext({
    rolesCatalog: [
        {id: 1, name: 'Base', position_id: 10},
        {id: 2, name: 'Histórico', position_id: 20},
        {id: 3, name: 'Otro', position_id: 20}
    ],
    document: {querySelectorAll: () => checks, getElementById: () => help}
});
vm.runInContext(source.slice(start, end), context);
context.actualizarRolesSegunCargo('10', true);
assert.equal(checks[0].parentElement.hidden, false);
assert.equal(checks[1].checked, true);
assert.equal(checks[1].parentElement.hidden, false);
assert.match(checks[1].label.textContent, /histórico/);
assert.equal(checks[2].parentElement.hidden, true);
context.actualizarRolesSegunCargo('20');
assert.equal(checks[0].checked, false);
assert.equal(checks[0].parentElement.hidden, true);
assert.equal(checks[1].parentElement.hidden, false);
console.log('OK: los roles se filtran por cargo y los históricos se conservan al editar.');
