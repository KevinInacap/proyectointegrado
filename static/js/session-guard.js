/* Revalida historial y pestañas sin conservar identidades o claves en storage. */
(() => {
    'use strict';
    const script = document.currentScript;
    const expectedFingerprint = script?.dataset.sessionFingerprint || '';
    const sessionUrl = script?.dataset.sessionUrl;
    const root = document.documentElement;
    const originalVisibility = root.style.visibility;
    let verification = null;
    let leaving = false;

    const hide = () => { root.style.visibility = 'hidden'; };
    const show = () => { root.style.visibility = originalVisibility; };

    async function verifyCurrentSession() {
        if (leaving || document.visibilityState === 'hidden' || verification || !sessionUrl) return;
        hide();
        verification = (async () => {
            try {
                const response = await fetch(sessionUrl, {
                    credentials: 'same-origin', cache: 'no-store',
                    headers: {'Accept': 'application/json'}
                });
                if (!response.ok) throw new Error('No se pudo verificar la sesión.');
                const state = await response.json();
                if (leaving || document.visibilityState === 'hidden') return;
                if (state.fingerprint !== expectedFingerprint) {
                    // El servidor elige el panel correspondiente a la cuenta vigente.
                    window.location.replace(state.redirect_url);
                    return;
                }
                show();
            } catch (_) {
                // No mostrar una copia privada si la sesión no puede verificarse.
                if (!leaving && document.visibilityState !== 'hidden') window.location.reload();
            } finally {
                verification = null;
            }
        })();
        await verification;
    }

    window.addEventListener('pagehide', () => {
        leaving = true;
        hide();
        document.querySelectorAll('input[type="password"]').forEach(input => { input.value = ''; });
    });
    window.addEventListener('pageshow', event => {
        const navigation = window.performance?.getEntriesByType('navigation')[0];
        if (event.persisted || navigation?.type === 'back_forward') {
            leaving = true;
            hide();
            window.location.reload();
            return;
        }
        leaving = false;
        if (!verification) show();
    });
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') hide();
        else verifyCurrentSession();
    });
    window.addEventListener('focus', verifyCurrentSession);
})();
