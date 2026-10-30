const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('templates/login.html', 'utf8');
const script = source.match(/<script>\s*(document\.addEventListener\('DOMContentLoaded'[\s\S]*?)<\/script>/);
assert.ok(script, 'Debe existir el controlador del formulario');

function setup(withSwal = false) {
    let ready, submitCount = 0, dialog;
    const elements = {};
    for (const id of ['togglePassword', 'password', 'eyeIcon', 'loginForm', 'username', 'btnSubmit', 'loginFormError']) {
        elements[id] = {
            value: '', attributes: {}, handlers: {}, hidden: true,
            addEventListener(name, handler) { this.handlers[name] = handler; },
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name]; },
            removeAttribute(name) { delete this.attributes[name]; },
            focus() { this.focused = true; },
        };
    }
    elements.password.attributes.type = 'password';
    elements.loginForm.submit = () => { submitCount++; };
    const window = withSwal ? {Swal: {fire: options => { dialog = options; return Promise.resolve(); }}} : {};
    const document = {
        addEventListener(name, handler) { if (name === 'DOMContentLoaded') ready = handler; },
        querySelectorAll() { return []; },
        getElementById(id) { return elements[id]; },
    };
    vm.runInNewContext(script[1], {window, document});
    ready();
    return {elements, submit() { elements.loginForm.handlers.submit({preventDefault() {}}); },
        clicks() { return submitCount; }, dialog() { return dialog; }};
}

const fallback = setup();
fallback.submit();
assert.equal(fallback.clicks(), 0);
assert.equal(fallback.elements.loginFormError.hidden, false);
assert.match(fallback.elements.loginFormError.textContent, /usuario.*contraseña/i);
assert.equal(fallback.elements.username.attributes['aria-invalid'], 'true');
assert.equal(fallback.elements.username.focused, true);

const validUsername = setup();
validUsername.elements.username.value = '用户';
validUsername.elements.password.value = 'una-clave';
validUsername.submit();
validUsername.submit();
assert.equal(validUsername.clicks(), 1, 'No se deben duplicar los envíos');

const validEmail = setup();
validEmail.elements.username.value = "o'connor@example.com";
validEmail.elements.password.value = 'una-clave';
validEmail.submit();
assert.equal(validEmail.clicks(), 1, 'No se debe rechazar un correo válido');

const longEmail = setup();
longEmail.elements.username.value = 'a@' + 'b'.repeat(60) + '.' + 'c'.repeat(60) + '.' + 'd'.repeat(40) + '.cl';
longEmail.elements.password.value = 'una-clave';
longEmail.submit();
assert.equal(longEmail.clicks(), 1, 'Un correo válido puede superar 150 caracteres');

const invalid = setup(true);
invalid.elements.username.value = 'nombre\u0001';
invalid.elements.password.value = 'una-clave';
invalid.submit();
assert.equal(invalid.clicks(), 0);
assert.equal(invalid.dialog().icon, 'warning');
assert.match(invalid.dialog().text, /caracteres de control/);

const toggle = setup();
toggle.elements.togglePassword.handlers.click({preventDefault() {}});
assert.equal(toggle.elements.password.attributes.type, 'text');
assert.equal(toggle.elements.togglePassword.attributes['aria-pressed'], 'true');
assert.equal(toggle.elements.togglePassword.attributes['aria-label'], 'Ocultar contraseña');
toggle.elements.togglePassword.handlers.click({preventDefault() {}});
assert.equal(toggle.elements.password.attributes.type, 'password');
assert.equal(toggle.elements.togglePassword.attributes['aria-pressed'], 'false');
console.log('OK: validación del login, controles accesibles y avisos sin SweetAlert.');
