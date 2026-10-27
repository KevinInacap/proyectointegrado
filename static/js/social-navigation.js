/* Navegación del panel social: las direcciones siguen siendo enlaces válidos sin JavaScript. */
(() => {
    'use strict';

    window.SocialPanelNavigation = {
        init({routes, initial, render}) {
            const allowed = Object.keys(routes);
            const sectionForPath = path => allowed.find(section => routes[section] === path);
            const show = section => {
                if (!allowed.includes(section)) return false;
                render(section);
                return true;
            };

            function navigate(section) {
                if (!allowed.includes(section)) return false;
                const path = routes[section];
                if (window.location.pathname !== path) {
                    window.history.pushState(null, '', path);
                }
                return show(section);
            }

            document.addEventListener('click', event => {
                const link = event.target.closest?.('a[data-social-panel]');
                if (!link || event.defaultPrevented || event.button !== 0
                    || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey
                    || link.hasAttribute('download') || link.target && link.target !== '_self') return;
                const section = link.dataset.socialPanel;
                if (!allowed.includes(section) || link.getAttribute('href') !== routes[section]) return;
                event.preventDefault();
                navigate(section);
            });

            window.addEventListener('popstate', () => {
                const section = sectionForPath(window.location.pathname);
                if (section) show(section);
                else window.location.reload();
            });

            const section = sectionForPath(window.location.pathname) || initial;
            if (allowed.includes(section)) {
                // Las entradas antiguas /asistente-social/ e /integral/ conservan su compatibilidad.
                // Reemplazar solo esta entrada evita un paso vacío al retroceder.
                if (window.location.pathname !== routes[section]) {
                    window.history.replaceState(null, '', routes[section] + window.location.search + window.location.hash);
                }
                show(section);
            }
            return {navigate};
        }
    };
})();
