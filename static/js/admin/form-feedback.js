/* Shared form feedback and motion. Loaded after the admin feature modules. */
(() => {
    'use strict';
    const humanNames = new Set(['vecinoNombre', 'usrFullName', 'txtAtencionNombre', 'catalogoDelegacionEncargado', 'drawerInputNombre']);
    const phones = new Set(['vecinoTelefono', 'txtAtencionTelefono', 'catalogoDelegacionTelefono', 'drawerInputTelefono']);
    const labels = new Set(['rolFormNombre', 'catalogoCargoNombre', 'catalogoDelegacionNombre', 'catalogoDelegacionAmbito']);
    const neighborFields = {vecinoNombre: 'nombre', vecinoRut: 'rut', vecinoEmail: 'email', vecinoDireccion: 'direccion', vecinoTelefono: 'telefono'};
    const busy = new Set();
    function errorFor(input) {
        const value = input.value || '', text = value.trim();
        if (input.required && !text) return 'Este campo es obligatorio.';
        if (!text || input.type === 'password') return input.maxLength > 0 && value.length > input.maxLength ? `Admite hasta ${input.maxLength} caracteres.` : '';
        if (input.maxLength > 0 && value.length > input.maxLength) return `Admite hasta ${input.maxLength} caracteres.`;
        const field = neighborFields[input.id];
        if (field) {
            const id = document.getElementById('vecinoId')?.value;
            const existing = id && window.datasetVecinos?.find(item => String(item.id) === String(id));
            if (existing && text === String(existing[field] || '').trim()) return '';
        }
        if (/[<>\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text)) return 'No se permiten etiquetas HTML ni caracteres de control.';
        if (humanNames.has(input.id) && (text.length < 2 || !/^[\p{L} .’'-]+$/u.test(text))) return 'Ingresa un nombre con letras, espacios, apóstrofes o guiones.';
        if (labels.has(input.id) && (text.length < 2 || !/\p{L}/u.test(text))) return 'Ingresa un nombre descriptivo.';
        if (phones.has(input.id) && (!/^\+?[0-9][0-9 () .-]*$/.test(text) || text.replace(/\D/g, '').length < 8 || text.replace(/\D/g, '').length > 15)) return 'Ingresa de 8 a 15 dígitos; puedes usar +, espacios y guiones.';
        if (input.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) return 'Ingresa un correo electrónico válido.';
        return input.checkValidity() ? '' : input.validationMessage;
    }
    function validate(root) {
        if (!root) return true;
        for (const input of root.querySelectorAll('input, select, textarea')) {
            if (input.disabled || input.readOnly || ['hidden', 'checkbox', 'radio', 'file', 'button', 'submit'].includes(input.type)) continue;
            const message = errorFor(input);
            input.setAttribute('aria-invalid', message ? 'true' : 'false');
            if (message) {
                const label = input.labels?.[0]?.textContent.trim() || input.getAttribute('aria-label') || input.placeholder || 'Campo del formulario';
                Swal.fire({icon: 'warning', titleText: 'Revisa el formulario', text: `${label}: ${message}`, confirmButtonText: 'Corregir', returnFocus: false}).then(() => input.focus());
                return false;
            }
        }
        return true;
    }
    const transitions = new WeakMap();
    function animate(node) {
        if (!node || !node.animate || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
        // Cancel only our own transition, never unrelated animations on the element.
        transitions.get(node)?.cancel();
        transitions.set(node, node.animate(
            [{opacity: 0.45, transform: 'translateY(10px)'}, {opacity: 1, transform: 'translateY(0)'}],
            {duration: 360, easing: 'cubic-bezier(.22, 1, .36, 1)'}
        ));
    }
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('form').forEach(form => { form.noValidate = true; });
        // Patterns containing unescaped hyphens differ across browser versions.
        document.querySelectorAll('#formCatalogoDelegacion [pattern]').forEach(input => input.removeAttribute('pattern'));
        document.addEventListener('submit', event => {
            if (!validate(event.target)) { event.preventDefault(); event.stopImmediatePropagation(); }
        }, true);
        const actions = {
            guardarVecino: 'formVecino', guardarUsuarioDB: 'formUsuarioDB',
            guardarDelegacionCatalogo: 'formCatalogoDelegacion', guardarCargoCatalogo: 'formCatalogoCargo',
            ejecutarGuardarRol: 'formRol', ejecutarGuardarNuevaFuncion: 'formNuevaFuncion',
            guardarAtencionDB: 'formAtencionDB', guardarPasswordDB: 'modalPasswordUsuario'
        };
        for (const [name, id] of Object.entries(actions)) {
            const original = window[name];
            if (typeof original !== 'function') continue;
            window[name] = async function (...args) {
                args[0]?.preventDefault?.();
                const root = document.getElementById(id);
                if (busy.has(name) || !validate(root)) return;
                busy.add(name);
                const buttons = root ? [...root.querySelectorAll('button[type=submit], .modal-footer button:not([data-bs-dismiss])')].filter(button => !button.disabled) : [];
                buttons.forEach(button => { button.disabled = true; });
                root?.setAttribute('aria-busy', 'true');
                try { return await original.apply(this, args); }
                finally {
                    busy.delete(name);
                    buttons.forEach(button => { button.disabled = false; });
                    root?.removeAttribute('aria-busy');
                }
            };
        }
        // Los formularios que necesitan catálogos señalan la espera en el
        // botón que los abrió, únicamente mientras la solicitud está activa.
        let openingTrigger = null;
        document.addEventListener('click', event => {
            const button = event.target.closest?.('button');
            if (!button) return;
            openingTrigger = button;
            queueMicrotask(() => { if (openingTrigger === button) openingTrigger = null; });
        }, true);
        for (const name of ['abrirCatalogosOrganizacion', 'abrirModalNuevaAtencion', 'abrirModalRol']) {
            const original = window[name];
            if (typeof original !== 'function') continue;
            window[name] = async function (...args) {
                const button = openingTrigger;
                let indicator = null;
                if (button && !button.disabled) {
                    indicator = document.createElement('span');
                    indicator.className = 'admin-option-loading admin-button-loading';
                    indicator.setAttribute('aria-hidden', 'true');
                    button.append(indicator);
                    button.disabled = true;
                    button.setAttribute('aria-busy', 'true');
                }
                try { return await original.apply(this, args); }
                finally {
                    if (indicator) {
                        indicator.remove();
                        button.disabled = false;
                        button.removeAttribute('aria-busy');
                    }
                }
            };
        }
        const pending = new Set();
        const pagers = new Set(['paginadorPills', 'paginadorPillsUsuarios', 'paginadorPillsRoles']);
        function labelPages(container) {
            container.querySelectorAll('button.page-pill').forEach(button => {
                button.setAttribute('aria-label', `Página ${button.textContent.trim()}`);
                if (button.classList.contains('active')) button.setAttribute('aria-current', 'page');
                else button.removeAttribute('aria-current');
            });
        }
        function syncCatalogNav(root) {
            const view = root.closest('.maintainer-view');
            if (!view?.id?.startsWith('view-')) return;
            const option = document.getElementById('sub-' + view.id.slice(5));
            if (!option) return;
            const loading = Boolean(view.querySelector('[data-catalog][aria-busy="true"]'));
            let indicator = option.querySelector('.admin-catalog-option-loading');
            if (loading && !indicator) {
                indicator = document.createElement('span');
                indicator.className = 'admin-option-loading admin-catalog-option-loading';
                indicator.setAttribute('aria-hidden', 'true');
                option.append(indicator);
            }
            if (!loading) indicator?.remove();
            if (loading) option.setAttribute('aria-busy', 'true');
            else option.removeAttribute('aria-busy');
        }
        // Some renderers replace all pagination buttons after activation. Restore
        // keyboard focus to the selected replacement, without moving other focus.
        document.addEventListener('click', event => {
            const button = event.target.closest?.('button.page-pill');
            const container = button?.parentElement;
            if (!container || !pagers.has(container.id) || document.activeElement !== button) return;
            queueMicrotask(() => {
                if (!button.isConnected && document.activeElement === document.body) {
                    container.querySelector('button.page-pill.active')?.focus();
                }
            });
        }, true);
        let frame;
        const observer = new MutationObserver(records => {
            for (const record of records) {
                if (record.type === 'attributes' && record.target.classList.contains('maintainer-view') && record.target.classList.contains('active')) pending.add(record.target);
                if (record.type === 'attributes' && record.attributeName === 'aria-busy' && record.target.matches?.('[data-catalog]')) syncCatalogNav(record.target);
                if (record.type === 'childList') {
                    const table = record.target.closest?.('tbody');
                    if (table) pending.add(table.closest('.table-responsive') || table);
                    // Card-based views also replace their results on filtering or pagination.
                    if (record.target.matches?.('#listaCargosMantenedor, #delegacionesCardsGrid, #roleCardsLive')) pending.add(record.target);
                    if (pagers.has(record.target.id)) labelPages(record.target);
                }
            }
            if (!frame && pending.size) frame = requestAnimationFrame(() => {
                pending.forEach(animate); pending.clear(); frame = null;
            });
        });
        const main = document.querySelector('.content-body');
        if (main) {
            observer.observe(main, {subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'aria-busy']});
            main.querySelectorAll('[data-catalog][aria-busy="true"]').forEach(syncCatalogNav);
        }
        pagers.forEach(id => { const pager = document.getElementById(id); if (pager) labelPages(pager); });
        document.querySelectorAll('.modal').forEach(modal => modal.addEventListener('shown.bs.modal', () => {
            // Los catálogos usan pestañas: nunca enfocar el formulario oculto.
            const fields = modal.querySelectorAll('input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])');
            [...fields].find(field => field.getClientRects().length > 0)?.focus();
        }));
    });
})();
