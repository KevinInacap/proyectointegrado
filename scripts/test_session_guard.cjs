// Escenarios del guard real: restauración del historial y cambio de sesión en otra pestaña.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/js/session-guard.js'), 'utf8');

function browser({navigationType = 'navigate', fingerprint = 'same-session', serverFingerprint = fingerprint, offline = false} = {}) {
    const events = {window: {}, document: {}};
    const root = {style: {visibility: ''}};
    const passwords = [{value: 'temporary-test-value'}];
    const requests = [];
    const actions = [];
    const document = {
        currentScript: {dataset: {sessionFingerprint: fingerprint, sessionUrl: '/session-state/'}},
        documentElement: root, visibilityState: 'visible',
        querySelectorAll: () => passwords,
        addEventListener: (name, handler) => { events.document[name] = handler; },
    };
    const window = {
        performance: {getEntriesByType: () => [{type: navigationType}]},
        location: {reload: () => actions.push('reload'), replace: url => actions.push(url)},
        addEventListener: (name, handler) => { events.window[name] = handler; },
    };
    vm.runInNewContext(source, {
        window, document,
        fetch: async (url, options) => {
            requests.push({url, options});
            if (offline) throw new Error('offline');
            return {ok: true, json: async () => ({fingerprint: serverFingerprint, redirect_url: '/current-dashboard/'})};
        },
    });
    return {root, passwords, document, events, requests, actions};
}

async function visibleAgain(page) {
    page.document.visibilityState = 'hidden';
    page.events.document.visibilitychange();
    assert.equal(page.root.style.visibility, 'hidden');
    page.document.visibilityState = 'visible';
    page.events.document.visibilitychange();
    await new Promise(resolve => setImmediate(resolve));
}

(async () => {
    const normal = browser();
    normal.events.window.pageshow({persisted: false});
    assert.equal(normal.root.style.visibility, '');
    assert.deepEqual(normal.actions, []);
    normal.events.window.pagehide();
    assert.equal(normal.root.style.visibility, 'hidden');
    assert.equal(normal.passwords[0].value, '');
    normal.events.window.pageshow({persisted: true});
    assert.deepEqual(normal.actions, ['reload']);
    assert.equal(normal.root.style.visibility, 'hidden');

    const history = browser({navigationType: 'back_forward'});
    history.events.window.pageshow({persisted: false});
    assert.deepEqual(history.actions, ['reload']);

    const current = browser();
    await visibleAgain(current);
    assert.equal(current.root.style.visibility, '');
    assert.deepEqual(current.actions, []);
    assert.equal(current.requests[0].options.cache, 'no-store');
    assert.equal(current.requests[0].options.credentials, 'same-origin');

    const windowChanged = browser({serverFingerprint: 'another-session'});
    await windowChanged.events.window.focus();
    assert.deepEqual(windowChanged.actions, ['/current-dashboard/']);

    const leaving = browser();
    const pendingVerification = leaving.events.window.focus();
    leaving.events.window.pagehide();
    await pendingVerification;
    assert.equal(leaving.root.style.visibility, 'hidden');
    assert.deepEqual(leaving.actions, []);

    const changed = browser({serverFingerprint: 'another-session'});
    await visibleAgain(changed);
    assert.equal(changed.root.style.visibility, 'hidden');
    assert.deepEqual(changed.actions, ['/current-dashboard/']);

    const expired = browser({serverFingerprint: ''});
    await visibleAgain(expired);
    assert.equal(expired.root.style.visibility, 'hidden');
    assert.deepEqual(expired.actions, ['/current-dashboard/']);

    const offline = browser({offline: true});
    await visibleAgain(offline);
    assert.equal(offline.root.style.visibility, 'hidden');
    assert.deepEqual(offline.actions, ['reload']);
    console.log('OK: historial/BFCache, credenciales de formulario, pestaña vigente, sesión distinta/expirada y fallo de red.');
})().catch(error => { console.error(error); process.exitCode = 1; });
