        let datasetVecinos = [];
        window.datasetVecinos = datasetVecinos;

        let filasFiltradasVecinos = [...datasetVecinos];
        let seleccionadosIds = new Set();
        let filasPorPagina = 10;
        let paginaActual = 1;
        let ordenAsc = true;
        let columnaOrdenVecinos = 'nombre';
        let bsModalVecino, bsModalFicha, bsModalImportar, bsModalAuditoria, chartInstance;

        /* Variables Globales de Gestión de Usuarios y Atenciones */
        let bsModalUsuario, bsModalEliminarUsuario, bsModalPasswordUsuario;
        let bsModalNuevaAtencion, bsModalExpedienteAtencion;
        let datasetAtenciones = [];
        let filasPorPaginaAtenciones = 10, paginaActualAtenciones = 1;
        let controlesPaginacionAtencionesInicializados = false;
        window.datasetAtenciones = datasetAtenciones;
        let datasetUsuarios = [], filasFiltradasUsuarios = [];
        window.datasetUsuarios = datasetUsuarios;
        let rolesCatalog = [], delegationsCatalog = [], positionsCatalog = [];
        let filasPorPaginaUsuarios = 10, paginaActualUsuarios = 1, ordenAscUsuarios = true, campoOrdenUsuarios = 'full_name';
        let usuarioAEliminarId = null, usuarioAPasswordId = null;

        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, char => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            })[char]);
        }

        let calFechaActual = new Date();
        let calFechaHoy = new Date();
        let calFechaSeleccionada = new Date(calFechaHoy.getFullYear(), calFechaHoy.getMonth(), calFechaHoy.getDate());
        let calCompromisos = [];
        let calAgendaRequestId = 0;

        function fechaCalendarioISO(fecha) {
            const year = fecha.getFullYear();
            const month = String(fecha.getMonth() + 1).padStart(2, '0');
            const day = String(fecha.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        function renderCompromisosFechaSeleccionada() {
            const lista = document.getElementById('listaAgendaMunicipal');
            if (!lista) return;
            lista.replaceChildren();
            const fecha = fechaCalendarioISO(calFechaSeleccionada);
            const items = calCompromisos.filter(item => item.fecha === fecha);
            if (!items.length) {
                const empty = document.createElement('span');
                empty.className = 'text-muted';
                empty.textContent = 'Sin compromisos registrados para este día.';
                lista.appendChild(empty);
                return;
            }
            items.forEach(item => {
                const card = document.createElement('div');
                card.className = 'border rounded-2 p-2 mb-2';
                const title = document.createElement('strong');
                title.className = 'd-block';
                title.textContent = item.descripcion;
                const detail = document.createElement('span');
                detail.className = 'text-muted';
                detail.textContent = [item.estado, item.area, item.territorio, item.delegacion].filter(Boolean).join(' · ');
                card.append(title, detail);
                lista.appendChild(card);
            });
        }

        async function cargarAgendaMunicipal() {
            const badge = document.getElementById('lblEstadoAtencionCalendario');
            if (!badge) return;
            const requestId = ++calAgendaRequestId;
            const desde = new Date(calFechaActual.getFullYear(), calFechaActual.getMonth(), 1);
            const hasta = new Date(calFechaActual.getFullYear(), calFechaActual.getMonth() + 1, 0);
            badge.textContent = 'Consultando compromisos…';
            try {
                const query = new URLSearchParams({ desde: fechaCalendarioISO(desde), hasta: fechaCalendarioISO(hasta) });
                const response = await fetch(`/api/agenda/?${query.toString()}`, {
                    credentials: 'same-origin',
                    headers: { Accept: 'application/json' }
                });
                if (!response.ok) throw new Error('No fue posible consultar la agenda.');
                const payload = await response.json();
                if (requestId !== calAgendaRequestId) return;
                calCompromisos = Array.isArray(payload.results) ? payload.results : [];
                badge.textContent = `${calCompromisos.length} compromiso${calCompromisos.length === 1 ? '' : 's'} este mes`;
                renderCompromisosFechaSeleccionada();
            } catch (error) {
                if (requestId !== calAgendaRequestId) return;
                calCompromisos = [];
                badge.textContent = 'Agenda no disponible';
                renderCompromisosFechaSeleccionada();
                console.warn('No se pudo cargar la agenda municipal:', error);
            }
        }


        function actualizarFechaActual() {
            const elFecha = document.getElementById('currentDateDisplay');
            if (elFecha) {
                const hoy = new Date();
                const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
                elFecha.textContent = `${hoy.getDate()} de ${meses[hoy.getMonth()]} de ${hoy.getFullYear()}`;
            }
        }

        function renderCalendarioMunicipal() {
            const lblBadgeHoy = document.getElementById('lblDiaHoyTexto');
            const lblMesAno = document.getElementById('lblMesAnoCalendario');
            const gridDias = document.getElementById('gridDiasCalendario');
            const lblFechaSeleccionada = document.getElementById('lblFechaSeleccionadaCalendario');
            if (!gridDias) return;

            const diasSemana = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
            const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

            // 1. Mostrar la fecha REAL de hoy en el badge superior
            if (lblBadgeHoy) {
                const diaNom = diasSemana[calFechaHoy.getDay()];
                const mesNom = meses[calFechaHoy.getMonth()];
                lblBadgeHoy.textContent = `${diaNom}, ${calFechaHoy.getDate()} de ${mesNom}`;
            }

            // 2. Mes y Año del calendario mostrado
            const ano = calFechaActual.getFullYear();
            const mes = calFechaActual.getMonth();
            if (lblMesAno) {
                lblMesAno.innerHTML = `<i class="bi bi-calendar3 text-primary me-1"></i> ${meses[mes]} ${ano}`;
            }
            if (lblFechaSeleccionada) {
                const fecha = calFechaSeleccionada;
                lblFechaSeleccionada.textContent = `Fecha seleccionada: ${fecha.getDate()} de ${meses[fecha.getMonth()]} de ${fecha.getFullYear()}`;
            }

            // 3. Generar la cuadrícula del mes
            const primerDiaMes = new Date(ano, mes, 1);
            const ultimoDiaMes = new Date(ano, mes + 1, 0);
            const totalDiasMes = ultimoDiaMes.getDate();

            // Lunes = 0, ..., Domingo = 6
            let primerDiaSemana = primerDiaMes.getDay() - 1;
            if (primerDiaSemana === -1) primerDiaSemana = 6;

            const ultimoDiaMesAnterior = new Date(ano, mes, 0).getDate();
            let html = '';

            for (let i = primerDiaSemana - 1; i >= 0; i--) {
                const d = ultimoDiaMesAnterior - i;
                const fecha = new Date(ano, mes - 1, d);
                const selected = fecha.getTime() === calFechaSeleccionada.getTime();
                html += `<button type="button" class="dia-calendario-item dia-calendario-adyacente${selected ? ' seleccionado' : ''}" aria-label="${d} de ${meses[fecha.getMonth()]} de ${fecha.getFullYear()}" aria-pressed="${selected}" onclick="seleccionarDiaCalendario(${d}, ${mes - 1}, ${ano})">${d}</button>`;
            }

            const esMesActual = (calFechaHoy.getFullYear() === ano && calFechaHoy.getMonth() === mes);
            const diaHoyNum = calFechaHoy.getDate();

            for (let d = 1; d <= totalDiasMes; d++) {
                const esHoy = esMesActual && (d === diaHoyNum);
                const fechaDia = new Date(ano, mes, d);
                const esFinDeSemana = (fechaDia.getDay() === 0 || fechaDia.getDay() === 6);
                const selected = fechaDia.getTime() === calFechaSeleccionada.getTime();
                const classes = ['dia-calendario-item', esFinDeSemana ? 'fin-de-semana' : '', esHoy ? 'hoy-destacado' : '', selected ? 'seleccionado' : ''].filter(Boolean).join(' ');
                html += `<button type="button" class="${classes}" aria-label="${d} de ${meses[mes]} de ${ano}${esHoy ? ', hoy' : ''}" aria-pressed="${selected}" title="${d} de ${meses[mes]} de ${ano}" onclick="seleccionarDiaCalendario(${d}, ${mes}, ${ano})">${d}</button>`;
            }

            const celdasUsadas = primerDiaSemana + totalDiasMes;
            const celdasRestantes = (7 - (celdasUsadas % 7)) % 7;
            for (let d = 1; d <= celdasRestantes; d++) {
                const fecha = new Date(ano, mes + 1, d);
                const selected = fecha.getTime() === calFechaSeleccionada.getTime();
                html += `<button type="button" class="dia-calendario-item dia-calendario-adyacente${selected ? ' seleccionado' : ''}" aria-label="${d} de ${meses[fecha.getMonth()]} de ${fecha.getFullYear()}" aria-pressed="${selected}" onclick="seleccionarDiaCalendario(${d}, ${mes + 1}, ${ano})">${d}</button>`;
            }

            gridDias.innerHTML = html;
            renderCompromisosFechaSeleccionada();
            cargarAgendaMunicipal();
        }

        function cambiarMesCalendario(delta) {
            calFechaActual = new Date(calFechaActual.getFullYear(), calFechaActual.getMonth() + delta, 1);
            renderCalendarioMunicipal();
        }

        function seleccionarDiaCalendario(dia, mes, ano) {
            calFechaSeleccionada = new Date(ano, mes, dia);
            calFechaActual = new Date(ano, mes, 1);
            renderCalendarioMunicipal();
        }

        document.addEventListener('DOMContentLoaded', function () {
            // Actualización Dinámica de Fecha Institucional respecto al día actual
            actualizarFechaActual();
            try { renderCalendarioMunicipal(); } catch (e) { console.warn("Calendario error:", e); }
            inicializarMapaDelegaciones();

            const elVec = document.getElementById('modalVecino');
            if (elVec && window.bootstrap) bsModalVecino = new bootstrap.Modal(elVec);
            const elFic = document.getElementById('modalFichaVecino');
            if (elFic && window.bootstrap) bsModalFicha = new bootstrap.Modal(elFic);
            const elImp = document.getElementById('modalImportarExcel');
            if (elImp && window.bootstrap) bsModalImportar = new bootstrap.Modal(elImp);
            const elAud = document.getElementById('modalAuditoria');
            if (elAud && window.bootstrap) bsModalAuditoria = new bootstrap.Modal(elAud);
            // Cargar tema institucional guardado (Modo Oscuro / Claro)
            aplicarTemaGuardado();

            /* Modales de Gestión de Usuarios */
            const elModalUsr = document.getElementById('modalUsuario');
            if (elModalUsr && window.bootstrap) bsModalUsuario = new bootstrap.Modal(elModalUsr);
            const elModalDel = document.getElementById('modalEliminarUsuario');
            if (elModalDel && window.bootstrap) bsModalEliminarUsuario = new bootstrap.Modal(elModalDel);
            const elModalPwd = document.getElementById('modalPasswordUsuario');
            if (elModalPwd && window.bootstrap) bsModalPasswordUsuario = new bootstrap.Modal(elModalPwd);

            /* Modales de Gestión de Roles (MyAdmin Power) */
            const elModalRol = document.getElementById('modalRol');
            if (elModalRol && window.bootstrap) bsModalRol = new bootstrap.Modal(elModalRol);
            const elModalDelRol = document.getElementById('modalEliminarRol');
            if (elModalDelRol && window.bootstrap) bsModalEliminarRol = new bootstrap.Modal(elModalDelRol);
            const elModalMatriz = document.getElementById('modalMatrizMyAdmin');
            if (elModalMatriz && window.bootstrap) bsModalMatrizMyAdmin = new bootstrap.Modal(elModalMatriz);
            const elModalNuevaFunc = document.getElementById('modalNuevaFuncion');
            if (elModalNuevaFunc && window.bootstrap) bsModalNuevaFuncion = new bootstrap.Modal(elModalNuevaFunc);
            const elModalVerPerms = document.getElementById('modalVerPermisosRol');
            if (elModalVerPerms && window.bootstrap) bsModalVerPermisosRol = new bootstrap.Modal(elModalVerPerms);
            
            /* Modales de Gestión de Atenciones Ciudadanas */
            const elModalNuevaAt = document.getElementById('modalNuevaAtencion');
            if (elModalNuevaAt && window.bootstrap) bsModalNuevaAtencion = new bootstrap.Modal(elModalNuevaAt);
            const elModalExpAt = document.getElementById('modalExpedienteAtencion');
            if (elModalExpAt && window.bootstrap) bsModalExpedienteAtencion = new bootstrap.Modal(elModalExpAt);

            try { renderAtencionesChart(); } catch (e) { console.warn("Chart atenciones error:", e); }
            try { cargarVecinosDesdeDB(false); } catch (e) { console.warn("Tabla vecinos error:", e); }
            try { cargarUsuariosDesdeDB(false); } catch (e) { console.warn("Cargar usuarios error:", e); }
            try { cargarAtencionesDB(); } catch (e) { console.warn("Cargar atenciones error:", e); }
            try { initDelegacionesView(); } catch (e) { console.warn("Delegaciones init error:", e); }
            try { initRolesView(false); } catch (e) { console.warn("Roles init error:", e); }

            // Inicializar motor de micro-interacciones (Spotlight, Sliding Pill, Number Tickers)
            try {
                setTimeout(() => {
                    if (typeof updatePillSlider === 'function') updatePillSlider();
                    if (typeof initSpotlightEffect === 'function') initSpotlightEffect();
                    const numEls = document.querySelectorAll('.sgr-kpi-number');
                    if (numEls && numEls[0] && typeof animateNumberTicker === 'function') {
                        animateNumberTicker(numEls[0], '3.421', 500);
                    }
                }, 120);
                window.addEventListener('resize', () => {
                    if (typeof updatePillSlider === 'function') updatePillSlider();
                });
            } catch (e) { console.warn("Micro-interactions init error:", e); }
        });

        /* Ajuste universal de modales: todo el contenido queda visible sin scroll. */
        function ajustarModalAlViewport(modal) {
            if (!modal || !modal.classList.contains('show')) return;
            if (modal.id === 'modalCatalogosOrganizacion' && window.innerWidth < 992) return;
            const dialog = modal.querySelector('.modal-dialog');
            const content = modal.querySelector('.modal-content');
            if (!dialog || !content) return;

            modal.classList.add('modal-fit-viewport');
            content.style.transform = 'none';
            dialog.style.height = 'auto';
            dialog.style.setProperty('align-items', 'flex-start', 'important');
            dialog.style.setProperty('min-height', '0', 'important');
            dialog.style.setProperty('margin-top', '12px', 'important');
            dialog.style.setProperty('margin-bottom', '12px', 'important');

            requestAnimationFrame(() => {
                const availableHeight = Math.max(280, window.innerHeight - 24);
                const availableWidth = Math.max(280, window.innerWidth - 24);
                const naturalHeight = content.scrollHeight;
                const naturalWidth = content.offsetWidth;
                const scale = Math.min(1, availableHeight / naturalHeight, availableWidth / naturalWidth);

                content.style.transformOrigin = 'top center';
                content.style.transform = `scale(${scale})`;
                dialog.style.height = `${Math.ceil(naturalHeight * scale)}px`;
            });
        }

        document.addEventListener('shown.bs.modal', event => ajustarModalAlViewport(event.target));
        document.addEventListener('hidden.bs.modal', event => {
            const dialog = event.target.querySelector('.modal-dialog');
            const content = event.target.querySelector('.modal-content');
            if (content) content.style.transform = '';
            if (dialog) {
                dialog.style.height = '';
                dialog.style.removeProperty('align-items');
                dialog.style.removeProperty('min-height');
                dialog.style.removeProperty('margin-top');
                dialog.style.removeProperty('margin-bottom');
            }
            event.target.classList.remove('modal-fit-viewport');
        });
        document.addEventListener('toggle', event => {
            const section = event.target;
            if (!(section instanceof HTMLDetailsElement) || !section.closest('#modalRol')) return;

            if (section.open) {
                section.closest('#contenedorModulosPermisos')
                    ?.querySelectorAll('details[open]')
                    .forEach(other => { if (other !== section) other.open = false; });
            }
            requestAnimationFrame(() => ajustarModalAlViewport(document.getElementById('modalRol')));
        }, true);
        window.addEventListener('resize', () => {
            document.querySelectorAll('.modal.show').forEach(ajustarModalAlViewport);
        });

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('mobile-open');
            document.getElementById('sidebarOverlay').classList.toggle('active');
        }

        function toggleSubmenu(id) {
            const sub = document.getElementById(id);
            const chevron = document.getElementById('submenu-chevron');
            if (sub.style.display === 'none' || sub.style.display === '') {
                sub.style.display = 'block';
                chevron.style.transform = 'rotate(0deg)';
            } else {
                sub.style.display = 'none';
                chevron.style.transform = 'rotate(-90deg)';
            }
        }

        const adminReportViews = new Set(['general', '1vs1', 'multi']);

        function adminRouteUrl(viewName, reportView = 'general') {
            const base = document.body.dataset.adminBase;
            if (viewName === 'dashboard') return base;
            return base + viewName + '/' + (viewName === 'reportes' ? reportView + '/' : '');
        }

        function currentAdminRoute() {
            const base = document.body.dataset.adminBase;
            const parts = window.location.pathname.startsWith(base)
                ? window.location.pathname.slice(base.length).split('/').filter(Boolean)
                : [];
            return { viewName: parts[0] || 'dashboard', reportView: parts[1] || 'general' };
        }

        // El indicador acompaña la petición real; no retrasa el cambio de vista.
        const adminViewRequests = new Map();
        function loadAdminView(viewName, load) {
            if (adminViewRequests.has(viewName)) return adminViewRequests.get(viewName);
            const option = document.getElementById('sub-' + viewName)
                || document.getElementById('nav-btn-' + viewName);
            let indicator = null;
            if (option) {
                indicator = document.createElement('span');
                indicator.className = 'admin-option-loading';
                indicator.setAttribute('aria-hidden', 'true');
                option.append(indicator);
                option.setAttribute('aria-busy', 'true');
            }
            const request = Promise.resolve().then(load);
            adminViewRequests.set(viewName, request);
            const finish = () => {
                if (adminViewRequests.get(viewName) !== request) return;
                adminViewRequests.delete(viewName);
                indicator?.remove();
                option?.removeAttribute('aria-busy');
            };
            request.then(finish, error => { finish(); console.warn('No se pudo preparar la vista:', error); });
            return request;
        }

        function switchView(viewName, updateUrl = true, reportView = 'general') {
            const targetView = document.getElementById('view-' + viewName);
            if (!targetView || !targetView.classList.contains('maintainer-view')) return;
            if (viewName === 'reportes' && !adminReportViews.has(reportView)) return;
            if (viewName !== 'usuarios' && typeof selectedTableRows !== 'undefined') {
                selectedTableRows.clear();
                actualizarBarraUsuariosLote();
            }
            document.querySelectorAll('.maintainer-view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item-btn, .submenu-item-btn').forEach(btn => btn.classList.remove('active'));

            targetView.classList.add('active');

            if (viewName === 'dashboard') {
                document.getElementById('nav-btn-dashboard').classList.add('active');
            } else if (viewName === 'reportes') {
                document.getElementById('nav-btn-reportes').classList.add('active');
            } else if (viewName === 'solicitudes-sociales') {
                document.getElementById('nav-btn-social-requests')?.classList.add('active');
            } else {
                document.getElementById('nav-btn-mantenedores').classList.add('active');
                const subBtn = document.getElementById('sub-' + viewName);
                if (subBtn) subBtn.classList.add('active');
            }

            if (window.innerWidth < 768) {
                document.getElementById('sidebar').classList.remove('mobile-open');
                document.getElementById('sidebarOverlay').classList.remove('active');
            }
            if (updateUrl) {
                const url = adminRouteUrl(viewName, reportView);
                if (window.location.pathname !== url) window.history.pushState(null, '', url);
            }

            if (viewName === 'dashboard') {
                if (chartInstance) chartInstance.resize();
                setTimeout(() => {
                    if (typeof updatePillSlider === 'function') updatePillSlider();
                    if (typeof initSpotlightEffect === 'function') initSpotlightEffect();
                }, 50);
            }
            if (viewName === 'reportes') {
                initReportesCharts();
                cambiarSubvistaReporte(reportView, false);
                setTimeout(() => {
                    if (typeof initSpotlightEffect === 'function') initSpotlightEffect();
                    // Los indicadores se cargan desde la API del módulo, no desde cifras de demostración.
                }, 50);
            }
            const loaders = {
                usuarios: () => cargarUsuariosDesdeDB(false),
                vecinos: () => cargarVecinosDesdeDB(false),
                delegaciones: () => initDelegacionesView(),
                cargos: () => initCargosView(),
                roles: () => initRolesView(false),
                atenciones: () => cargarAtencionesDB(),
                'solicitudes-sociales': () => window.loadSocialReviewRequests?.()
            };
            if (loaders[viewName]) loadAdminView(viewName, loaders[viewName]);
        }

        document.addEventListener('DOMContentLoaded', () => {
            const route = currentAdminRoute();
            switchView(route.viewName, false, route.reportView);
        });
        window.addEventListener('popstate', () => {
            const route = currentAdminRoute();
            switchView(route.viewName, false, route.reportView);
        });

