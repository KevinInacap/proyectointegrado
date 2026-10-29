// Ejecutar: node scripts/test_social_navigation.cjs
// Prueba el controlador real con entradas de historial y clics de navegación.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/js/social-navigation.js'), 'utf8');
const sections = ['casos', 'flujo', 'terreno', 'beneficios', 'informes', 'emergencias', 'redes', 'metas', 'mantenedores'];
const routes = Object.fromEntries(sections.map(section => [section, `/activities/dashboard/asistente-social/${section}/`]));

function browser(initialPath, options = {}) {
    const pageEvents = {};
    const documentEvents = {};
    const shown = [];
    const paths = [initialPath];
    let index = 0;
    let reloads = 0;
    let pushes = 0;
    let replaces = 0;
    const location = {pathname: initialPath, search: options.search || '', hash: options.hash || '', reload() {reloads++;}};
    const setPath = value => {location.pathname = value.split(/[?#]/)[0];};
    const window = {
        location,
        history: {
            pushState(_state, _title, address) {
                pushes++;
                paths.splice(index + 1);
                paths.push(address);
                index++;
                setPath(address);
            },
            replaceState(_state, _title, address) {
                replaces++;
                paths[index] = address;
                setPath(address);
            },
        },
        addEventListener(type, callback) {pageEvents[type] = callback;},
    };
    const document = {addEventListener(type, callback) {documentEvents[type] = callback;}};
    vm.runInNewContext(source, {window, document});
    const controller = window.SocialPanelNavigation.init({routes, initial: options.initial || 'casos', render: section => shown.push(section)});
    function historyStep(delta) {
        index += delta;
        setPath(paths[index]);
        pageEvents.popstate();
    }
    function click(section, overrides = {}) {
        let prevented = false;
        const link = {
            dataset: {socialPanel: section}, target: '',
            getAttribute() {return routes[section];}, hasAttribute() {return false;},
        };
        documentEvents.click({
            target: {closest() {return link;}}, button: 0, defaultPrevented: false,
            preventDefault() {prevented = true;}, ...overrides,
        });
        return prevented;
    }
    return {controller, shown, paths, location, historyStep, click, pageEvents,
        counts: () => ({pushes, replaces, reloads}), window};
}

const initial = browser('/activities/dashboard/asistente-social/');
assert.deepEqual(initial.shown, ['casos']);
assert.equal(initial.paths.length, 1, 'La URL antigua se reemplaza sin añadir una entrada extra.');
assert.equal(initial.paths[0], routes.casos);
assert.deepEqual(initial.counts(), {pushes: 0, replaces: 1, reloads: 0});

for (const section of sections) assert.equal(initial.click(section), true);
assert.equal(initial.paths.length, 9, 'Cada sección distinta añade una sola entrada.');
assert.equal(initial.location.pathname, routes.mantenedores);
initial.historyStep(-1);
assert.equal(initial.shown.at(-1), 'metas');
assert.equal(initial.counts().pushes, 8, 'Retroceder no vuelve a insertar historial.');
initial.historyStep(1);
assert.equal(initial.shown.at(-1), 'mantenedores');
assert.equal(initial.counts().pushes, 8);
initial.controller.navigate('mantenedores');
assert.equal(initial.counts().pushes, 8, 'Repetir la sección activa no duplica historial.');

const direct = browser(routes.informes, {initial: 'informes'});
assert.deepEqual(direct.shown, ['informes'], 'La dirección profunda abre su pestaña al recargar.');
assert.equal(direct.counts().replaces, 0);
assert.equal(direct.click('redes', {ctrlKey: true}), false, 'Ctrl+clic conserva abrir en otra pestaña.');
assert.equal(direct.click('redes', {button: 1}), false, 'Clic central conserva su comportamiento nativo.');
assert.equal(direct.controller.navigate('otra-cuenta'), false);
assert.equal(direct.location.pathname, routes.informes);
direct.location.pathname = '/otra-aplicacion/';
direct.pageEvents.popstate();
assert.equal(direct.counts().reloads, 1, 'Una ruta ajena se consulta al servidor.');

const alias = browser('/activities/dashboard/asistente-social/integral/', {search: '?filtro=1', hash: '#detalle'});
assert.equal(alias.paths[0], routes.casos + '?filtro=1#detalle');
assert.equal(alias.shown.at(-1), 'casos');
console.log('OK: nueve pestañas con URL propia, recarga, atrás/adelante, alias y clics modificados.');

