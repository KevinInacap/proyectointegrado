/* Mejora progresiva: el servidor conserva la validación y el formulario sin JS. */
(() => {
    'use strict';
    document.querySelectorAll('[data-password-target]').forEach(button => {
        button.addEventListener('click', () => {
            const input = document.getElementById(button.dataset.passwordTarget);
            const visible = input.type === 'password';
            input.type = visible ? 'text' : 'password';
            button.textContent = visible ? 'Ocultar' : 'Mostrar';
            button.setAttribute('aria-pressed', String(visible));
            button.setAttribute('aria-label', `${visible ? 'Ocultar' : 'Mostrar'} ${input.labels[0].textContent.toLowerCase()}`);
        });
    });
    const code = document.getElementById('code');
    if (code) {
        const group = document.createElement('div');
        group.className = 'otp-cells';
        group.setAttribute('role', 'group');
        group.setAttribute('aria-label', 'Código de seis dígitos');
        const cells = Array.from({length: 6}, (_, index) => {
            const input = document.createElement('input');
            input.type = 'text';
            input.inputMode = 'numeric';
            input.autocomplete = index === 0 ? 'one-time-code' : 'off';
            input.maxLength = 6; // Permite autocompletar el código completo desde móvil.
            input.pattern = '[0-9]';
            input.required = true;
            input.id = `code-digit-${index + 1}`;
            input.setAttribute('aria-label', `Dígito ${index + 1} de 6`);
            group.append(input);
            return input;
        });
        const sync = () => { code.value = cells.map(input => input.value).join(''); };
        const distribute = (text, start) => {
            const digits = text.replace(/\D/g, '').slice(0, 6);
            const offset = digits.length === 6 ? 0 : start;
            for (let i = offset; i < 6; i++) cells[i].value = digits[i - offset] || '';
            sync();
            cells[Math.min(offset + digits.length, 5)].focus();
        };
        cells.forEach((input, index) => {
            input.addEventListener('paste', event => {
                event.preventDefault();
                distribute(event.clipboardData.getData('text'), index);
            });
            input.addEventListener('input', () => {
                if (input.value.length > 1) return distribute(input.value, index);
                input.value = input.value.replace(/\D/g, '');
                sync();
                if (input.value && index < 5) cells[index + 1].focus();
            });
            input.addEventListener('keydown', event => {
                if (event.key === 'ArrowLeft' || (event.key === 'Backspace' && !input.value)) {
                    if (index > 0) cells[index - 1].focus();
                } else if (event.key === 'ArrowRight' && index < 5) cells[index + 1].focus();
            });
        });
        code.before(group);
        document.querySelector('label[for="code"]').htmlFor = cells[0].id;
        code.type = 'hidden';
        code.required = false;
    }
    const resend = document.getElementById('resend-code');
    if (resend) {
        const requested = Number(document.querySelector('[data-requested-at]').dataset.requestedAt) * 1000;
        const update = () => {
            const remaining = Math.max(0, Math.ceil((requested + 45000 - Date.now()) / 1000));
            resend.disabled = remaining > 0;
            document.getElementById('resend-status').textContent = remaining ? `Podrás reenviar el código en ${remaining} segundos.` : 'Ya puedes solicitar otro código.';
            if (!remaining) clearInterval(timer);
        };
        const timer = setInterval(update, 1000);
        update();
    }
    const alert = document.querySelector('[data-recovery-message]');
    if (alert && window.Swal) Swal.fire({icon: alert.dataset.recoveryMessage, text: alert.textContent.trim(), confirmButtonText: 'Entendido', confirmButtonColor: '#a31332'});
    document.querySelectorAll('form').forEach(form => {
        form.noValidate = true;
        let submitting = false;
        form.addEventListener('submit', event => {
            if (submitting) { event.preventDefault(); return; }
            const invalid = [...form.elements].find(input => input.willValidate && !input.checkValidity());
            if (invalid) {
                event.preventDefault();
                if (window.Swal) Swal.fire({
                    icon: 'warning', title: 'Revisa los datos',
                    text: invalid.validationMessage || 'Completa los datos requeridos antes de continuar.',
                    confirmButtonColor: '#a31332'
                });
                else form.reportValidity();
                invalid.focus();
                return;
            }
            const password = form.querySelector('[name="new_password"]');
            if (password && password.value !== form.querySelector('[name="confirm_password"]').value) {
                event.preventDefault();
                if (window.Swal) Swal.fire({icon: 'error', text: 'Las contraseñas no coinciden.', confirmButtonColor: '#a31332'});
                return;
            }
            submitting = true;
            form.querySelectorAll('[type="submit"]').forEach(button => { button.disabled = true; button.setAttribute('aria-busy', 'true'); });
        });
    });
})();
