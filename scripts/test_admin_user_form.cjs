// Prueba las funciones reales del formulario sin servicios ni paquetes externos.
// Ejecutar: node scripts/test_admin_user_form.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = require('./admin_test_source.cjs')();
function section(start, end) {
    const first = source.indexOf(start);
    const last = source.indexOf(end, first);
    assert.ok(first >= 0 && last > first, `No se encontró la función: ${start}`);
    return source.slice(first, last);
}

function form() {
    const elements = new Map();
    const alerts = [];
    const requests = [];
    function element() {
        return {value: '', checked: false, style: {}, appendChild() {}};
    }
    const context = vm.createContext({
        console,
        datasetUsuarios: [{
            id: 1, full_name: 'Persona Histórica', rut: '12.345.678-9',
            username: 'legacy-person', email: 'legacy-person@example.test',
            status: 'Activo', delegation_id: 1, position_id: 1,
            roles: [], is_staff: true, is_superuser: false,
        }],
        rolesCatalog: [], positionsCatalog: [], delegationsCatalog: [],
        bsModalUsuario: {show() {}, hide() {}},
        cargoPrevioEnModalUsuario: '',
        document: {
            getElementById(id) {
                if (!elements.has(id)) elements.set(id, element());
                return elements.get(id);
            },
            createElement: element,
            querySelectorAll: () => [],
        },
        window: {},
        Swal: {fire: message => alerts.push(message)},
        mostrarToast() {}, cargarUsuariosDesdeDB() {},
        getCookie: () => 'csrf-test',
        fetch: async (url, options) => {
            requests.push({url, payload: JSON.parse(options.body)});
            return {ok: true, json: async () => ({success: true, message: 'Guardado'})};
        },
    });
    vm.runInContext([
        section('function normalizarNombreRolCargo(', 'function confirmarEliminarUsuario('),
        section('function validarRutChileno(', '// 4. Bloqueo de números'),
    ].join('\n'), context);
    return {context, elements, alerts, requests};
}

(async () => {
    let f = form();
    f.context.abrirModalUsuario('editar', 1);
    assert.equal(f.elements.get('usrIsSuperuser').checked, false, 'Staff no debe activar superusuario');
    f.elements.get('usrPosition').value = '2';
    await f.context.guardarUsuarioDB();
    assert.equal(f.requests.length, 1, 'Editar cargo con RUT histórico debe enviar la solicitud');
    assert.equal(f.requests[0].payload.rut, '12.345.678-9');
    assert.equal(f.requests[0].payload.position_id, 2);
    assert.ok(!('is_superuser' in f.requests[0].payload));
    assert.ok(!('is_staff' in f.requests[0].payload), 'La edición debe preservar los flags técnicos');

    f = form();
    f.context.abrirModalUsuario('editar', 1);
    f.elements.get('usrRut').value = '12345678-9';
    await f.context.guardarUsuarioDB();
    assert.equal(f.requests[0].payload.rut, '12.345.678-9', 'Cambiar puntos no cambia la identidad histórica');

    f = form();
    f.context.abrirModalUsuario('editar', 1);
    f.elements.get('usrRut').value = '12.345.678-0';
    await f.context.guardarUsuarioDB();
    assert.equal(f.requests.length, 0);
    assert.equal(f.alerts[0].title, 'RUT inválido');

    f = form();
    f.context.abrirModalUsuario('editar', 1);
    f.context.datasetUsuarios.push({id: 2, rut: '10.000.013-K'});
    f.elements.get('usrRut').value = '10000013-k';
    await f.context.guardarUsuarioDB();
    assert.equal(f.requests.length, 0);
    assert.equal(f.alerts[0].title, 'RUT duplicado');

    f = form();
    f.context.abrirModalUsuario('editar', 1);
    f.elements.get('usrRut').value = '10000013-k';
    f.elements.get('usrIsSuperuser').checked = true;
    await f.context.guardarUsuarioDB();
    assert.equal(f.requests[0].payload.rut, '10.000.013-K');
    assert.equal(f.requests[0].payload.is_superuser, true, 'Solo un cambio explícito debe enviar superusuario');
    assert.ok(!('is_staff' in f.requests[0].payload));

    f = form();
    f.context.datasetUsuarios[0].is_superuser = true;
    f.context.abrirModalUsuario('editar', 1);
    assert.equal(f.elements.get('usrIsSuperuser').checked, true);
    await f.context.guardarUsuarioDB();
    assert.ok(!('is_superuser' in f.requests[0].payload));

    f = form();
    f.context.abrirModalUsuario('nuevo');
    for (const [id, value] of Object.entries({
        usrFullName: 'Nueva Persona', usrRut: '10000013-k', usrUsername: 'new-person',
        usrEmail: 'new-person@example.test', usrPassword: 'Safe!TestPass2026',
    })) f.elements.get(id).value = value;
    await f.context.guardarUsuarioDB();
    assert.equal(f.requests.length, 1);
    assert.equal(f.requests[0].payload.is_superuser, false);
    assert.equal(f.requests[0].payload.is_staff, false);

    for (const [rut, valid] of [
        ['12.345.678-5', true], ['123456785', true], ['10000013-k', true],
        ['1-9', true], ['0-0', false], ['12.345.678-9', false],
        ['abc12345678-5', false], ['12..345678-5', false],
    ]) assert.equal(f.context.validarRutChileno(rut), valid, `Validación de ${rut}`);
    console.log('OK: formulario de funcionarios, RUT histórico/nuevo/duplicado y privilegios técnicos.');
})().catch(error => {console.error(error); process.exitCode = 1;});
