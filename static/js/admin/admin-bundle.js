        let datasetVecinos = [];
        window.datasetVecinos = datasetVecinos;

        let filasFiltradasVecinos = [...datasetVecinos];
        let seleccionadosIds = new Set();
        let filasPorPagina = 10;
        let paginaActual = 1;
        let ordenAsc = true;
        let columnaOrdenVecinos = 'nombre';
        let bsModalVecino, bsModalFicha, bsModalImportar, bsModalAuditoria, bsModalPerfil, chartInstance;

        /* Variables Globales de Gestión de Usuarios y Atenciones */
        let bsModalUsuario, bsModalEliminarUsuario, bsModalPasswordUsuario;
        let bsModalNuevaAtencion, bsModalExpedienteAtencion;
        let datasetAtenciones = [], atencionSeleccionadaId = null;
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
            const elPerfil = document.getElementById('modalPerfilUsuario');
            if (elPerfil && window.bootstrap) bsModalPerfil = new bootstrap.Modal(elPerfil);

            // Cargar foto de perfil persistente si existe
            cargarFotoPerfilGuardada();

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
            if (viewName === 'usuarios') cargarUsuariosDesdeDB(false);
            if (viewName === 'vecinos') cargarVecinosDesdeDB(false);
            if (viewName === 'delegaciones') initDelegacionesView();
            if (viewName === 'cargos') initCargosView();
            if (viewName === 'roles') initRolesView(false);
            if (viewName === 'solicitudes-sociales' && typeof window.loadSocialReviewRequests === 'function') window.loadSocialReviewRequests();
            if (viewName === 'atenciones') cargarAtencionesDB();
        }

        document.addEventListener('DOMContentLoaded', () => {
            const route = currentAdminRoute();
            switchView(route.viewName, false, route.reportView);
        });
        window.addEventListener('popstate', () => {
            const route = currentAdminRoute();
            switchView(route.viewName, false, route.reportView);
        });

        async function cargarVecinosDesdeDB(mostrarAviso = false) {
            try {
                const response = await fetch('/api/vecinos/');
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || 'No fue posible consultar vecinos.');
                datasetVecinos = data.vecinos || [];
                window.datasetVecinos = datasetVecinos;
                seleccionadosIds.clear();
                const updated = document.getElementById('vecinosUltimaActualizacion');
                if (updated) updated.textContent = `Actualizado ${new Intl.DateTimeFormat('es-CL', {hour:'2-digit', minute:'2-digit'}).format(new Date())}`;
                actualizarOpcionesTerritorioVecinos();
                actualizarIndicadoresDiscretos();
                ejecutarFiltroCompletoVecinos();
                if (mostrarAviso) mostrarToast(`✓ ${datasetVecinos.length} vecinos cargados desde la base de datos`);
            } catch (error) {
                console.error('Error cargando vecinos:', error);
                Swal.fire({icon: 'error', title: 'No se pudieron cargar los vecinos', text: error.message, confirmButtonColor: '#A30F32'});
            }
        }

        function renderTablaVecinos() {
            const tbody = document.getElementById('tablaVecinosBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            const inicio = (paginaActual - 1) * filasPorPagina;
            const fin = inicio + filasPorPagina;
            const datos = filasFiltradasVecinos.slice(inicio, fin);

            if (datos.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="text-center py-5 text-muted">
                    <div class="empty-state-pro py-2">
                        <div class="empty-state-icon"><i class="bi bi-people"></i></div>
                        <div class="empty-state-title">No se encontraron vecinos</div>
                        <div class="empty-state-desc">No hay registros que coincidan con la búsqueda o los filtros aplicados.</div>
                        <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3" onclick="limpiarFiltrosVecinos()">Restablecer Filtros</button>
                    </div>
                </td></tr>`;
                document.getElementById('lblRegistrosInfo').textContent = '0 registros';
                actualizarIndicadorTablaVecinos(0, 0, 0);
                return;
            }

            const escapar = valor => String(valor ?? '').replace(/[&<>"']/g, caracter => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[caracter]));
            datos.forEach((v, idx) => {
                const isSel = seleccionadosIds.has(v.id);
                const tr = document.createElement('tr');
                tr.className = 'stagger-item';
                tr.style.setProperty('--stagger-i', idx);
                if (isSel) tr.classList.add('selected-row');

                tr.innerHTML = `
                    <td class="text-center"><input type="checkbox" class="form-check-input" ${isSel ? 'checked' : ''} onchange="toggleSeleccionarFila(${v.id}, this.checked)"></td>
                    <td>${inicio + idx + 1}</td>
                    <td class="fw-semibold"><button type="button" class="vecino-name-link" onclick="abrirFichaVecino(${Number(v.id)})">${escapar(v.nombre)}</button></td>
                    <td class="col-rut"><code>${escapar(v.rut)}</code></td>
                    <td class="col-dir">${escapar(v.direccion)}</td>
                    <td class="col-tel">${escapar(v.telefono)}</td>
                    <td class="col-terr"><span class="vecino-territory-label">${escapar(v.territorio)}</span></td>
                    <td class="col-est"><span class="badge-status ${v.estado === 'Activo' ? 'activo' : 'inactivo'}">${escapar(v.estado)}</span></td>
                    <td class="vecinos-row-actions">
                        <button type="button" class="vecino-action-link" onclick="abrirFichaVecino(${Number(v.id)})">Ficha</button>
                        <button type="button" class="vecino-action-link" onclick="abrirModalVecino('editar', ${Number(v.id)})">Editar</button>
                        <button type="button" class="vecino-action-link vecino-action-danger" onclick="eliminarVecino(${Number(v.id)})">Baja</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('lblRegistrosInfo').textContent = `Mostrando ${inicio + 1} - ${Math.min(fin, filasFiltradasVecinos.length)} de ${filasFiltradasVecinos.length} registros`;
            actualizarIndicadorTablaVecinos(inicio + 1, Math.min(fin, filasFiltradasVecinos.length), filasFiltradasVecinos.length);
            actualizarIndicadoresDiscretos();
            actualizarBarraAccionesMasivas();
        }

        function togglePanelFiltros() {
            document.getElementById('panelFiltrosAvanzados').classList.toggle('show');
            document.getElementById('btnToggleFiltros').classList.toggle('active');
        }

        function ejecutarFiltroCompletoVecinos() {
            const texto = (document.getElementById('searchVecinosInput')?.value || '').toLocaleLowerCase('es').trim();
            const est = document.getElementById('filtroEstadoVecino')?.value || '';
            const terr = document.getElementById('filtroTerritorioVecino')?.value || '';

            filasFiltradasVecinos = datasetVecinos.filter(v => {
                const campos = [v.nombre, v.rut, v.direccion, v.telefono, v.territorio].map(valor => String(valor || '').toLocaleLowerCase('es'));
                const matchT = !texto || campos.some(valor => valor.includes(texto));
                const matchE = !est || v.estado === est;
                const matchTer = !terr || v.territorio === terr;
                return matchT && matchE && matchTer;
            });
            const normalizar = valor => String(valor ?? '').toLocaleLowerCase('es');
            filasFiltradasVecinos.sort((a, b) => ordenAsc
                ? normalizar(a[columnaOrdenVecinos]).localeCompare(normalizar(b[columnaOrdenVecinos]), 'es', {numeric:true})
                : normalizar(b[columnaOrdenVecinos]).localeCompare(normalizar(a[columnaOrdenVecinos]), 'es', {numeric:true}));

            const chips = document.getElementById('contenedorChipsFiltros');
            chips.innerHTML = '';
            let count = 0;
            const agregarChip = (etiqueta, valor, controlId) => {
                const chip = document.createElement('span');
                chip.className = 'filter-chip';
                chip.append(document.createTextNode(`${etiqueta}: ${valor} `));
                const quitar = document.createElement('button');
                quitar.type = 'button';
                quitar.setAttribute('aria-label', `Quitar filtro ${etiqueta}`);
                quitar.textContent = '×';
                quitar.addEventListener('click', () => removerFiltro(controlId));
                chip.appendChild(quitar);
                chips.appendChild(chip);
            };
            if (est) { count++; agregarChip('Estado', est, 'filtroEstadoVecino'); }
            if (terr) { count++; agregarChip('Territorio', terr, 'filtroTerritorioVecino'); }

            const badge = document.getElementById('badgeFiltrosActivos');
            badge.style.display = count > 0 ? 'inline-block' : 'none';
            badge.textContent = count;

            paginaActual = 1;
            renderTablaVecinos();
        }

        function removerFiltro(id) { const control = document.getElementById(id); if (control) control.value = ''; ejecutarFiltroCompletoVecinos(); }
        function limpiarFiltrosVecinos() { ['searchVecinosInput','filtroEstadoVecino','filtroTerritorioVecino'].forEach(id => { const control = document.getElementById(id); if (control) control.value = ''; }); ejecutarFiltroCompletoVecinos(); }
        function toggleColumna(clase, visible) {
            document.querySelectorAll('.' + clase).forEach(c => c.style.display = visible ? '' : 'none');
        }

        function ordenarTablaVecinos(col) {
            if (!['nombre', 'rut', 'territorio', 'estado'].includes(col)) return;
            ordenAsc = columnaOrdenVecinos === col ? !ordenAsc : true;
            columnaOrdenVecinos = col;
            const normalizar = valor => String(valor ?? '').toLocaleLowerCase('es');
            filasFiltradasVecinos.sort((a, b) => ordenAsc ? normalizar(a[col]).localeCompare(normalizar(b[col]), 'es', {numeric:true}) : normalizar(b[col]).localeCompare(normalizar(a[col]), 'es', {numeric:true}));
            document.querySelectorAll('#tablaVecinos thead [data-sort-column]').forEach(th => {
                th.setAttribute('aria-sort', th.dataset.sortColumn === col ? (ordenAsc ? 'ascending' : 'descending') : 'none');
            });
            renderTablaVecinos();
        }

        function actualizarOpcionesTerritorioVecinos() {
            const select = document.getElementById('filtroTerritorioVecino');
            if (!select) return;
            const seleccionado = select.value;
            const defaultTerritorios = [
                'Delegación Avenida del Mar',
                'Delegación Centro Histórico',
                'Delegación Las Compañías',
                'Delegación La Pampa',
                'Delegación La Antena',
                'Delegación Sector Rural'
            ];
            const dataTerritorios = datasetVecinos.map(v => String(v.territorio || '').trim()).filter(Boolean);
            const territorios = [...new Set([...defaultTerritorios, ...dataTerritorios])].sort((a,b) => a.localeCompare(b, 'es'));
            select.innerHTML = '<option value="">Todos los territorios</option>' + territorios.map(nombre => `<option value="${nombre.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}">${nombre.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}</option>`).join('');
            if (territorios.includes(seleccionado)) select.value = seleccionado;
        }

        function actualizarIndicadorTablaVecinos(desde, hasta, total) {
            const orden = document.getElementById('vecinosOrdenActual');
            const filas = document.getElementById('vecinosFilasActuales');
            if (orden) orden.textContent = `Orden: ${({nombre:'Nombre',rut:'RUT',territorio:'Territorio',estado:'Estado'}[columnaOrdenVecinos] || 'Nombre')} · ${ordenAsc ? 'A–Z' : 'Z–A'}`;
            if (filas) filas.textContent = total ? `Filas ${desde}–${hasta} de ${total}` : '0 resultados';
        }

        function toggleSeleccionarTodosVecinos(checked) {
            if (checked) filasFiltradasVecinos.forEach(v => seleccionadosIds.add(v.id));
            else seleccionadosIds.clear();
            renderTablaVecinos();
        }

        function toggleSeleccionarFila(id, checked) {
            if (checked) seleccionadosIds.add(id);
            else seleccionadosIds.delete(id);
            actualizarBarraAccionesMasivas();
        }

        function actualizarBarraAccionesMasivas() {
            const bar = document.getElementById('bulkActionsBar');
            const total = seleccionadosIds.size;
            if (total > 0) {
                bar.classList.add('show');
                document.getElementById('bulkCountText').textContent = `${total} seleccionado${total > 1 ? 's' : ''}`;
            } else {
                bar.classList.remove('show');
            }
        }

        async function cambiarEstadoSeleccionados() {
            const seleccionados = datasetVecinos.filter(v => seleccionadosIds.has(v.id));
            try {
                for (const vecino of seleccionados) {
                    const payload = {...vecino, estado: vecino.estado === 'Activo' ? 'Inactivo' : 'Activo'};
                    delete payload.id;
                    delete payload.gestion;
                    const response = await fetch(`/api/vecinos/${vecino.id}/`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''},
                        body: JSON.stringify(payload)
                    });
                    const data = await response.json();
                    if (!response.ok || !data.success) throw new Error(data.message || `No se pudo actualizar a ${vecino.nombre}.`);
                }
                seleccionadosIds.clear();
                await cargarVecinosDesdeDB(false);
                mostrarToast('✓ Estados actualizados en la base de datos');
            } catch (error) {
                Swal.fire({icon: 'error', title: 'Actualización incompleta', text: error.message, confirmButtonColor: '#A30F32'});
                await cargarVecinosDesdeDB(false);
            }
        }

        function eliminarSeleccionadosMasivo() {
            Swal.fire({
                title: '¿Estás seguro?',
                text: `¿Eliminar los ${seleccionadosIds.size} seleccionados?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Eliminar',
                cancelButtonText: 'Cancelar'
            }).then(async (result) => {
                if (result.isConfirmed) {
                    try {
                        for (const id of [...seleccionadosIds]) {
                            const response = await fetch(`/api/vecinos/${id}/`, {method: 'DELETE', headers: {'X-CSRFToken': getCookie('csrftoken') || ''}});
                            const data = await response.json();
                            if (!response.ok || !data.success) throw new Error(data.message || `No se pudo dar de baja el registro ${id}.`);
                        }
                        seleccionadosIds.clear();
                        await cargarVecinosDesdeDB(false);
                        mostrarToast('✓ Registros dados de baja en la base de datos');
                    } catch (error) {
                        Swal.fire({icon: 'error', title: 'Baja incompleta', text: error.message, confirmButtonColor: '#A30F32'});
                        await cargarVecinosDesdeDB(false);
                    }
                }
            });
        }

        function exportarSeleccionadosExcel() {
            const sel = datasetVecinos.filter(v => seleccionadosIds.has(v.id));
            generarExcelDesdeArray(sel, 'Vecinos_Seleccionados');
        }

        function exportarExcelRealVecinos() {
            mostrarToast('Descargando Excel...');
            generarExcelDesdeArray(filasFiltradasVecinos, 'Vecinos_La_Serena');
        }

        function generarExcelDesdeArray(datos, nombre) {
            const hoja = datos.map(item => ({
                'ID': item.id, 'Nombre Completo': item.nombre, 'RUT': item.rut,
                'Dirección': item.direccion, 'Teléfono': item.telefono,
                'Territorio': item.territorio, 'Tipo Gestión': item.gestion, 'Estado': item.estado
            }));
            const ws = XLSX.utils.json_to_sheet(hoja);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Vecinos');
            XLSX.writeFile(wb, `${nombre}.xlsx`);
            mostrarToast('✓ Excel descargado correctamente');
        }

        function descargarPlantillaExcelVecinos() {
            const hoja = [{ 'Nombre Completo': 'Ej: Carlos Valenzuela', 'RUT': '12.345.678-9', 'Dirección': 'Av. Balmaceda 100', 'Teléfono': '+56 9 1234 5678', 'Territorio': 'Centro', 'Tipo Gestión': 'Solicitud', 'Estado': 'Activo' }];
            const ws = XLSX.utils.json_to_sheet(hoja);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Plantilla');
            XLSX.writeFile(wb, 'Plantilla_Vecinos_LaSerena.xlsx');
            mostrarToast('✓ Plantilla Excel descargada');
        }

        function abrirModalImportarExcel() {
            document.getElementById('importWizardContent1').style.display = 'block';
            document.getElementById('importWizardContent2').style.display = 'none';
            document.getElementById('importFileInput').value = '';
            bsModalImportar.show();
        }

        let tempImportados = [];
        function procesarArchivoExcelSubido(input) {
            const file = input.files[0];
            if (!file) return;
            document.getElementById('lblNombreArchivoCargado').textContent = file.name;
            const reader = new FileReader();
            reader.onload = function (e) {
                const data = new Uint8Array(e.target.result);
                const wb = XLSX.read(data, { type: 'array' });
                const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]]);
                tempImportados = rows.map((r, i) => ({
                    id: datasetVecinos.length + i + 1,
                    nombre: r['Nombre Completo'] || r['Nombre'] || 'Vecino Importado',
                    rut: r['RUT'] || r['Rut'] || '',
                    direccion: r['Dirección'] || 'La Serena',
                    telefono: r['Teléfono'] || '+56 9 0000 0000',
                    territorio: r['Territorio'] || 'Centro',
                    gestion: r['Tipo Gestión'] || 'Solicitud',
                    estado: r['Estado'] || 'Activo'
                }));
                document.getElementById('lblTotalFilasCargadas').textContent = tempImportados.length;
                document.getElementById('importWizardContent1').style.display = 'none';
                document.getElementById('importWizardContent2').style.display = 'block';
            };
            reader.readAsArrayBuffer(file);
        }

        async function ejecutarImportacionFinal() {
            let guardados = 0;
            const errores = [];
            for (const vecino of tempImportados) {
                const payload = {...vecino};
                delete payload.id;
                delete payload.gestion;
                try {
                    const response = await fetch('/api/vecinos/', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''},
                        body: JSON.stringify(payload)
                    });
                    const data = await response.json();
                    if (!response.ok || !data.success) throw new Error(data.message || 'Registro rechazado.');
                    guardados++;
                } catch (error) {
                    errores.push(`${vecino.nombre}: ${error.message}`);
                }
            }
            if (bsModalImportar) bsModalImportar.hide();
            await cargarVecinosDesdeDB(false);
            if (errores.length) {
                Swal.fire({icon: 'warning', title: `${guardados} registros importados`, text: `${errores.length} filas fueron rechazadas. ${errores.slice(0, 3).join(' | ')}`, confirmButtonColor: '#A30F32'});
            } else {
                mostrarToast(`✓ ${guardados} vecinos importados en la base de datos`);
            }
        }

        function exportarPDFInstitucionalVecinos() {
            mostrarToast('Generando PDF oficial...');
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF('landscape');
            doc.setFillColor(27, 54, 93);
            doc.rect(0, 0, 297, 22, 'F');
            doc.setTextColor(255, 255, 255);
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA', 14, 11);
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            doc.text('Sistema Municipal | Gestión de Atención Ciudadana — Reporte Oficial de Vecinos', 14, 17);

            const cols = ['#', 'Nombre', 'RUT', 'Dirección', 'Teléfono', 'Territorio', 'Gestión', 'Estado'];
            const rows = filasFiltradasVecinos.map(v => [v.id, v.nombre, v.rut, v.direccion, v.telefono, v.territorio, v.gestion, v.estado]);

            doc.autoTable({
                startY: 28, head: [cols], body: rows,
                headStyles: { fillColor: [196, 18, 48], textColor: 255, fontStyle: 'bold' },
                styles: { fontSize: 8.5 }
            });

            doc.save('Reporte_Vecinos_LaSerena.pdf');
            mostrarToast('✓ PDF descargado');
        }

        function abrirFichaVecino(id) {
            const v = datasetVecinos.find(item => item.id === id);
            if (!v) return;
            document.getElementById('fichaNombre').textContent = v.nombre;
            document.getElementById('fichaRut').textContent = v.rut;
            document.getElementById('fichaDireccion').textContent = v.direccion;
            document.getElementById('fichaTelefono').textContent = v.telefono;
            document.getElementById('fichaTerritorio').textContent = v.territorio;
            document.getElementById('fichaEstado').innerHTML = `<span class="badge-status ${v.estado.toLowerCase()}">${v.estado}</span>`;

            // Generar Historial Cronológico de Trámites y Reclamaciones
            const timelineEl = document.getElementById('fichaHistorialTickets');
            if (timelineEl) {
                timelineEl.innerHTML = `
                    <div class="timeline-ticket-item">
                        <span class="timeline-ticket-dot" style="border-color: #10B981;"></span>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong class="text-dark small">Subsidio Agua Potable y Alcantarillado (SAP)</strong>
                            <span class="text-muted" style="font-size: 0.72rem;">24 Sep 2026</span>
                        </div>
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size:0.7rem;">Resuelto</span>
                            <span class="text-secondary small" style="font-size:0.75rem;"><i class="bi bi-person-workspace text-primary me-1"></i> Canal: Presencial (${v.territorio})</span>
                        </div>
                        <p class="text-muted small m-0" style="font-size:0.74rem;">Ficha RSH validada con 40% de vulnerabilidad. Beneficio otorgado por 3 años.</p>
                    </div>
                    <div class="timeline-ticket-item">
                        <span class="timeline-ticket-dot" style="border-color: #D97706;"></span>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong class="text-dark small">Reclamo Alumbrado Público y Luminarias</strong>
                            <span class="text-muted" style="font-size: 0.72rem;">12 Sep 2026</span>
                        </div>
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle" style="font-size:0.7rem;">En Curso</span>
                            <span class="text-secondary small" style="font-size:0.75rem;"><i class="bi bi-telephone-fill text-info me-1"></i> Canal: Telefónico (Mesa Central 1400)</span>
                        </div>
                        <p class="text-muted small m-0" style="font-size:0.74rem;">Derivado a Dirección de Alumbrado Comunal. Cuadrilla programada para inspección.</p>
                    </div>
                    <div class="timeline-ticket-item">
                        <span class="timeline-ticket-dot" style="border-color: #0284C7;"></span>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong class="text-dark small">Certificado de Residencia y Audiencia Delegado</strong>
                            <span class="text-muted" style="font-size: 0.72rem;">28 Ago 2026</span>
                        </div>
                        <div class="d-flex align-items-center gap-2 mb-1">
                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle" style="font-size:0.7rem;">Completado</span>
                            <span class="text-secondary small" style="font-size:0.75rem;"><i class="bi bi-laptop text-success me-1"></i> Canal: Portal Web Vecino</span>
                        </div>
                        <p class="text-muted small m-0" style="font-size:0.74rem;">Certificado digital firmado con código QR municipal y remitido al correo.</p>
                    </div>
                `;
            }

            bsModalFicha.show();
        }

        function exportarFichaIndividualPDF() {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            doc.setFillColor(27, 54, 93);
            doc.rect(0, 0, 210, 22, 'F');
            doc.setTextColor(255, 255, 255);
            doc.setFontSize(13);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA', 14, 14);
            doc.autoTable({
                startY: 32,
                body: [
                    ['Nombre:', document.getElementById('fichaNombre').textContent],
                    ['RUT:', document.getElementById('fichaRut').textContent],
                    ['Dirección:', document.getElementById('fichaDireccion').textContent],
                    ['Teléfono:', document.getElementById('fichaTelefono').textContent]
                ]
            });
            doc.save('Ficha_Vecino.pdf');
            mostrarToast('✓ Ficha individual exportada en PDF');
        }

        function abrirModalVecino(modo, id = null) {
            document.getElementById('formVecino').reset();
            document.getElementById('modalVecinoTitle').textContent = modo === 'editar' ? 'Editar Vecino' : 'Registrar Nuevo Vecino';
            document.getElementById('vecinoId').value = id || '';
            if (modo === 'editar') {
                const v = datasetVecinos.find(item => item.id === id);
                if (v) {
                    document.getElementById('vecinoRut').value = v.rut;
                    document.getElementById('vecinoEmail').value = v.email || '';
                    document.getElementById('vecinoNombre').value = v.nombre;
                    document.getElementById('vecinoDireccion').value = v.direccion;
                    document.getElementById('vecinoTelefono').value = v.telefono;
                    document.getElementById('vecinoTerritorio').value = v.territorio;
                    document.getElementById('vecinoEstado').value = v.estado;
                }
            }
            bsModalVecino.show();
        }

        async function guardarVecino(e) {
            e.preventDefault();
            const id = document.getElementById('vecinoId').value;
            const nom = document.getElementById('vecinoNombre').value.trim();
            const rutVal = document.getElementById('vecinoRut').value.trim();
            const dir = document.getElementById('vecinoDireccion').value.trim();

            if (!nom || !rutVal || !dir) {
                Swal.fire({ icon: 'warning', title: 'Campos requeridos', text: 'Nombre, RUT y Dirección son obligatorios y no pueden estar vacíos.' });
                return;
            }

            const existente = id ? datasetVecinos.find(item => String(item.id) === String(id)) : null;
            const normalizarRut = valor => String(valor || '').replace(/[^0-9kK]/g, '').toUpperCase();
            const rutSinCambios = !!existente && normalizarRut(rutVal) === normalizarRut(existente.rut);
            if (!rutSinCambios && typeof validarRutChileno === 'function' && !validarRutChileno(rutVal)) {
                Swal.fire({
                    icon: 'error',
                    title: 'RUT inválido',
                    text: 'Revisa el número y el dígito verificador antes de continuar.'
                });
                return;
            }
            const emailVal = document.getElementById('vecinoEmail').value.trim().toLowerCase();
            if (emailVal && !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(emailVal)) {
                Swal.fire({icon:'error', title:'Correo inválido', text:'Ingresa un correo electrónico válido.'});
                return;
            }
            const duplicadoRut = datasetVecinos.some(item => String(item.id) !== String(id) && normalizarRut(item.rut) === normalizarRut(rutVal));
            if (duplicadoRut) {
                Swal.fire({icon:'error', title:'RUT duplicado', text:'Ya existe un vecino registrado con ese RUT.'});
                return;
            }
            const duplicadoEmail = emailVal && datasetVecinos.some(item => String(item.id) !== String(id) && String(item.email || '').trim().toLowerCase() === emailVal);
            if (duplicadoEmail) {
                Swal.fire({icon:'error', title:'Correo duplicado', text:'Ya existe un vecino registrado con ese correo electrónico.'});
                return;
            }

            const payload = {
                nombre: typeof sanitizarTexto === 'function' ? sanitizarTexto(nom) : nom,
                rut: typeof formatearRutChileno === 'function' ? formatearRutChileno(rutVal) : rutVal,
                email: emailVal,
                direccion: typeof sanitizarTexto === 'function' ? sanitizarTexto(dir) : dir,
                telefono: document.getElementById('vecinoTelefono').value.trim(),
                territorio: document.getElementById('vecinoTerritorio').value,
                estado: document.getElementById('vecinoEstado').value
            };

            try {
                const response = await fetch(id ? `/api/vecinos/${id}/` : '/api/vecinos/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''},
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || 'No fue posible guardar el vecino.');
                if (bsModalVecino) bsModalVecino.hide();
                await cargarVecinosDesdeDB(false);
                mostrarToast('✓ ' + data.message);
                Swal.fire({icon: 'success', title: 'Vecino guardado', text: data.message || 'Datos del vecino guardados exitosamente.', confirmButtonColor: '#1B365D'});
            } catch (error) {
                Swal.fire({icon: 'error', title: 'No se guardó el vecino', text: error.message, confirmButtonColor: '#A30F32'});
            }
        }

        function eliminarVecino(id) {
            const v = datasetVecinos.find(item => item.id === id);
            if (v) Swal.fire({title: "¿Dar de baja al vecino?", text: `Se conservará la auditoría de "${v.nombre}".`, icon: "warning", showCancelButton: true, confirmButtonText: "Dar de baja", cancelButtonText: "Cancelar", confirmButtonColor: '#A30F32'}).then(async (res) => {
                if (!res.isConfirmed) return;
                try {
                    const response = await fetch(`/api/vecinos/${id}/`, {method: 'DELETE', headers: {'X-CSRFToken': getCookie('csrftoken') || ''}});
                    const data = await response.json();
                    if (!response.ok || !data.success) throw new Error(data.message || 'No fue posible eliminar el vecino.');
                    await cargarVecinosDesdeDB(false);
                    mostrarToast('✓ ' + data.message);
                    Swal.fire({icon: 'success', title: 'Vecino dado de baja', text: data.message || 'El vecino ha sido dado de baja correctamente.', confirmButtonColor: '#1B365D'});
                } catch (error) {
                    Swal.fire({icon: 'error', title: 'No se eliminó el vecino', text: error.message, confirmButtonColor: '#A30F32'});
                }
            });
        }

        function actualizarIndicadoresDiscretos() {
            const total = datasetVecinos.length;
            const activos = datasetVecinos.filter(v => v.estado === 'Activo').length;
            document.getElementById('lblTotalVecinos').textContent = total.toLocaleString('es-CL');
            document.getElementById('lblActivosVecinos').textContent = activos.toLocaleString('es-CL');
            document.getElementById('lblInactivosVecinos').textContent = (total - activos).toLocaleString('es-CL');
        }

        function cambiarFilasPorPagina(val) {
            filasPorPagina = Math.min(50, Math.max(10, parseInt(val, 10) || 10));
            paginaActual = 1;
            renderTablaVecinos();
        }

        /* ==========================================================================
           LOG DE AUDITORÍA Y TRAZABILIDAD DE ACCIONES (ADMINISTRADOR)
           ========================================================================== */
        let datasetAuditLogs = [];
        let logsFiltradosAuditoria = [];
        let paginaAuditoria = 1;
        const filasPorPaginaAuditoria = 10;

        async function cargarLogsAuditoriaDB(mostrarToastAviso = false) {
            const tbody = document.getElementById('tablaAuditoriaBody');
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted"><div class="spinner-border spinner-border-sm text-primary me-2"></div>Cargando registro de auditoría...</td></tr>`;
            }
            try {
                const res = await fetch('/api/audit-logs/');
                const data = await res.json();
                if (data.success && data.logs) {
                    datasetAuditLogs = data.logs;
                    logsFiltradosAuditoria = [...datasetAuditLogs];
                    paginaAuditoria = 1;
                    renderTablaAuditoria();
                    if (mostrarToastAviso) mostrarToast('✓ Log de auditoría actualizado.');
                }
            } catch (err) {
                console.error("Error al cargar logs de auditoría:", err);
                if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-danger"><i class="bi bi-exclamation-circle me-1"></i> No se pudo cargar el historial de auditoría.</td></tr>`;
                if (mostrarToastAviso && window.Swal) Swal.fire({icon: 'error', title: 'Auditoría no disponible', text: 'No se pudo cargar el historial. Inténtalo nuevamente.'});
            }
        }

        function renderTablaAuditoria() {
            const tbody = document.getElementById('tablaAuditoriaBody');
            const lblTotal = document.getElementById('lblTotalAuditLogs');
            const lblPagina = document.getElementById('lblPaginaAuditoria');
            const btnAnterior = document.getElementById('btnPaginaAnteriorAuditoria');
            const btnSiguiente = document.getElementById('btnPaginaSiguienteAuditoria');
            if (!tbody) return;
            tbody.innerHTML = '';
            const total = logsFiltradosAuditoria.length;
            const totalPaginas = Math.max(1, Math.ceil(total / filasPorPaginaAuditoria));
            paginaAuditoria = Math.min(Math.max(1, paginaAuditoria), totalPaginas);
            const inicio = (paginaAuditoria - 1) * filasPorPaginaAuditoria;
            if (lblTotal) lblTotal.textContent = `${total} eventos registrados`;
            if (lblPagina) lblPagina.textContent = `Página ${paginaAuditoria} de ${totalPaginas}`;
            if (btnAnterior) btnAnterior.disabled = paginaAuditoria <= 1;
            if (btnSiguiente) btnSiguiente.disabled = paginaAuditoria >= totalPaginas;
            if (!total) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> No se registran eventos con los filtros seleccionados.</td></tr>`;
                return;
            }
            logsFiltradosAuditoria.slice(inicio, inicio + filasPorPaginaAuditoria).forEach(l => {
                const tr = document.createElement('tr');
                const actUpper = (l.action || '').toUpperCase();
                const descLower = (l.description || '').toLowerCase();
                let badgeAction = actUpper === 'CREATE'
                    ? `<span class="badge bg-success text-white px-2 py-1"><i class="bi bi-plus-circle-fill me-1"></i> CREACIÓN</span>`
                    : actUpper === 'DELETE'
                        ? `<span class="badge bg-danger text-white px-2 py-1"><i class="bi bi-trash-fill me-1"></i> ELIMINACIÓN</span>`
                        : descLower.includes('estado')
                            ? `<span class="badge bg-warning text-dark px-2 py-1"><i class="bi bi-toggle2-on me-1"></i> ESTADO</span>`
                            : descLower.includes('contrase') || descLower.includes('clave')
                                ? `<span class="badge bg-info text-dark px-2 py-1"><i class="bi bi-key-fill me-1"></i> CONTRASEÑA</span>`
                                : `<span class="badge bg-primary text-white px-2 py-1"><i class="bi bi-pencil-fill me-1"></i> MODIFICACIÓN</span>`;
                tr.innerHTML = `
                    <td class="text-nowrap font-monospace small text-secondary"><i class="bi bi-calendar3 me-1 text-muted"></i>${escapeHtml(l.timestamp)}</td>
                    <td><div class="d-flex align-items-center gap-2"><div class="user-avatar-pill admin" style="width:28px;height:28px;font-size:.72rem;min-width:28px"><i class="bi bi-person-fill"></i></div><div><span class="fw-bold text-dark d-block small">${escapeHtml(l.admin_name)}</span><small class="text-muted">@${escapeHtml(l.admin_username)}</small></div></div></td>
                    <td class="text-center">${badgeAction}</td>
                    <td><span class="fw-semibold text-dark d-block">${escapeHtml(l.description)}</span></td>
                    <td class="text-end"><span class="badge bg-light text-secondary border font-monospace px-2 py-1">${escapeHtml(l.affected_table)} #${escapeHtml(l.affected_record_id)}</span></td>`;
                tbody.appendChild(tr);
            });
        }

        function cambiarPaginaAuditoria(delta) {
            const paginas = Math.max(1, Math.ceil(logsFiltradosAuditoria.length / filasPorPaginaAuditoria));
            paginaAuditoria = Math.min(Math.max(1, paginaAuditoria + delta), paginas);
            renderTablaAuditoria();
        }

        function filtrarLogsAuditoria() {
            const elSearchInput = document.getElementById('searchAuditLogInput');
            const query = (elSearchInput && elSearchInput.value ? elSearchInput.value : '').toLowerCase().trim();
            const elAccionInput = document.getElementById('filtroAccionAuditLog');
            const accion = (elAccionInput && elAccionInput.value ? elAccionInput.value : '');

            logsFiltradosAuditoria = datasetAuditLogs.filter(l => {
                const matchQ = !query ||
                    (l.description && l.description.toLowerCase().includes(query)) ||
                    (l.admin_name && l.admin_name.toLowerCase().includes(query)) ||
                    (l.admin_username && l.admin_username.toLowerCase().includes(query)) ||
                    (l.affected_table && l.affected_table.toLowerCase().includes(query)) ||
                    (l.timestamp && l.timestamp.includes(query));

                let matchA = true;
                if (accion === 'CREATE') matchA = l.action === 'CREATE';
                else if (accion === 'DELETE') matchA = l.action === 'DELETE';
                else if (accion === 'STATUS') matchA = (l.description || '').toLowerCase().includes('estado');
                else if (accion === 'PASSWORD') matchA = (l.description || '').toLowerCase().includes('contrase') || (l.description || '').toLowerCase().includes('clave');
                else if (accion === 'UPDATE') matchA = l.action === 'UPDATE' && !(l.description || '').toLowerCase().includes('estado') && !(l.description || '').toLowerCase().includes('contrase');

                return matchQ && matchA;
            });

            paginaAuditoria = 1;
            renderTablaAuditoria();
        }

        /* ==========================================================================
           GESTIÓN DE PERFIL INSTITUCIONAL (ACTUALIZACIÓN DE FOTO Y PERSISTENCIA)
           ========================================================================== */
        let fotoPerfilTemporal = null;

        function abrirModalPerfil() {
            if (!bsModalPerfil) {
                const el = document.getElementById('modalPerfilUsuario');
                if (el && window.bootstrap) bsModalPerfil = new bootstrap.Modal(el);
            }
            // Sincronizar foto actual con el preview del modal
            const avatarActual = document.querySelector('.user-avatar-img');
            const previewModal = document.getElementById('perfilModalAvatarPreview');
            if (avatarActual && previewModal) {
                previewModal.src = avatarActual.src;
            }
            fotoPerfilTemporal = null;
            if (bsModalPerfil) bsModalPerfil.show();
        }

        function manejarCambioFotoPerfil(event) {
            const file = event.target.files[0];
            if (!file) return;
            if (!file.type.startsWith('image/')) {
                mostrarToast('Por favor seleccione un archivo de imagen válido (JPG, PNG o WEBP).');
                return;
            }
            if (file.size > 3 * 1024 * 1024) {
                mostrarToast('La imagen es demasiado grande. El límite institucional es de 3 MB.');
                return;
            }
            const reader = new FileReader();
            reader.onload = function (e) {
                fotoPerfilTemporal = e.target.result;
                const previewModal = document.getElementById('perfilModalAvatarPreview');
                if (previewModal) previewModal.src = fotoPerfilTemporal;
                mostrarToast('Vista previa cargada. Haga clic en "Guardar Nueva Foto" para confirmar.');
            };
            reader.readAsDataURL(file);
        }

        function guardarFotoPerfil() {
            if (!fotoPerfilTemporal) {
                mostrarToast('No ha seleccionado ninguna imagen nueva para guardar.');
                return;
            }
            try {
                localStorage.setItem('sgr_admin_avatar_custom', fotoPerfilTemporal);
                // Actualizar todas las fotos de avatar en el encabezado y navegación
                document.querySelectorAll('.user-avatar-img').forEach(img => {
                    img.src = fotoPerfilTemporal;
                });
                mostrarToast('✓ Foto de perfil institucional actualizada y guardada con éxito.');
                if (bsModalPerfil) bsModalPerfil.hide();
            } catch (err) {
                console.error('Error guardando en localStorage:', err);
                mostrarToast('Aviso: La foto se actualizó en la sesión actual.');
                document.querySelectorAll('.user-avatar-img').forEach(img => {
                    img.src = fotoPerfilTemporal;
                });
                if (bsModalPerfil) bsModalPerfil.hide();
            }
        }

        function restablecerFotoPerfil() {
            const defaultAvatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80";
            localStorage.removeItem('sgr_admin_avatar_custom');
            document.querySelectorAll('.user-avatar-img').forEach(img => {
                img.src = defaultAvatar;
            });
            const previewModal = document.getElementById('perfilModalAvatarPreview');
            if (previewModal) previewModal.src = defaultAvatar;
            fotoPerfilTemporal = null;
            mostrarToast('Foto de perfil restablecida al avatar municipal oficial.');
        }

        function cargarFotoPerfilGuardada() {
            const avatarGuardado = localStorage.getItem('sgr_admin_avatar_custom');
            if (avatarGuardado) {
                document.querySelectorAll('.user-avatar-img').forEach(img => {
                    img.src = avatarGuardado;
                });
            }
        }

        /* ==========================================================================
           1. CONTROL DE MODO OSCURO / DARK LIQUID GLASS
           ========================================================================== */
        function toggleDarkMode() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme') || (document.body.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('sgr_theme_preference', newTheme);

            const icon = document.getElementById('themeToggleIcon');
            if (icon) {
                if (newTheme === 'dark') {
                    icon.classList.remove('bi-moon-stars-fill');
                    icon.classList.add('bi-sun-fill');
                } else {
                    icon.classList.remove('bi-sun-fill');
                    icon.classList.add('bi-moon-stars-fill');
                }
            }
            mostrarToast(newTheme === 'dark' ? 'Modo Nocturno Cívico activado' : 'Modo Luminoso activado');
        }

        function aplicarTemaGuardado() {
            localStorage.removeItem('sgr_theme_preference');
            document.documentElement.removeAttribute('data-theme');
            document.body.removeAttribute('data-theme');
        }

        /* ==========================================================================
           2. NOTIFICACIONES ADMINISTRATIVAS & SEGURIDAD DE PERSONAL
           ========================================================================== */
        function marcarNotificacionesLeidas() {
            const items = document.querySelectorAll('#adminNotifList .notif-item');
            items.forEach(it => it.classList.remove('unread'));
            const badge = document.getElementById('adminNotifBadge');
            if (badge) {
                badge.style.display = 'none';
            }
            triggerBellRing();
            mostrarToast('✓ Alertas de seguridad marcadas como revisadas.');
        }

        /* ==========================================================================
           MICRO-INTERACCIONES: SPOTLIGHT, SLIDING PILL, NUMBER TICKER & BELL RING
           ========================================================================== */
        function initSpotlightEffect() {
            document.querySelectorAll('.spotlight-card').forEach(card => {
                if (card.dataset.spotlightBound) return;
                card.dataset.spotlightBound = "true";
                card.addEventListener('mousemove', e => {
                    const rect = card.getBoundingClientRect();
                    card.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
                    card.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
                });
            });
        }

        function updatePillSlider() {
            const group = document.querySelector('.pill-capsule-group');
            const activeBtn = group ? group.querySelector('.pill-capsule-btn.active') : null;
            const glider = document.getElementById('pillSliderGlider');
            if (!group || !activeBtn || !glider) return;
            const groupRect = group.getBoundingClientRect();
            const btnRect = activeBtn.getBoundingClientRect();
            const offsetLeft = btnRect.left - groupRect.left;
            glider.style.width = `${btnRect.width}px`;
            glider.style.transform = `translateX(${offsetLeft}px)`;
        }

        function animateNumberTicker(el, rawTarget, duration = 400) {
            if (!el) return;
            const strTarget = String(rawTarget).trim();
            const hasPercent = strTarget.includes('%');
            const cleanNumStr = strTarget.replace('%', '').replace(/\./g, '').replace(',', '.');
            const targetVal = parseFloat(cleanNumStr);
            if (isNaN(targetVal)) {
                el.textContent = strTarget;
                return;
            }

            const startTime = performance.now();
            const startVal = 0;
            const isDecimal = strTarget.includes(',') || (strTarget.includes('.') && !strTarget.includes('000') && targetVal < 100);

            function step(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const ease = 1 - Math.pow(1 - progress, 3);
                const currentVal = startVal + (targetVal - startVal) * ease;

                if (hasPercent) {
                    el.textContent = `${currentVal.toFixed(1)}%`;
                } else if (isDecimal) {
                    el.textContent = currentVal.toFixed(1).replace('.', ',');
                } else {
                    el.textContent = Math.round(currentVal).toLocaleString('es-CL');
                }

                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    el.textContent = strTarget;
                }
            }
            requestAnimationFrame(step);
        }

        function triggerBellRing() {
            const bell = document.querySelector('.btn-notification .bi-bell');
            if (!bell) return;
            bell.classList.remove('bell-ringing');
            void bell.offsetWidth;
            bell.classList.add('bell-ringing');
            setTimeout(() => bell.classList.remove('bell-ringing'), 900);
        }

        /* ==========================================================================
           3. FILTRO DE RANGO TEMPORAL EN VIVO (HOY / SEMANA / MES / AÑO)
           ========================================================================== */
        const datasetRangos = {
            hoy: {
                total: '142',
                trend: '+6% vs ayer',
                desc: 'Atenciones registradas en el día en curso en dependencias municipales.',
                resueltas: '92.4% Resueltas',
                presencial: 58,
                telefonica: 30,
                online: 12,
                chartLabels: ['08:30', '10:00', '11:30', '13:00', '14:30', '16:00'],
                dataPresencial: [15, 28, 38, 25, 20, 16],
                dataTelefonica: [8, 14, 18, 12, 10, 8],
                dataOnline: [3, 6, 8, 5, 4, 3]
            },
            semana: {
                total: '840',
                trend: '+11% vs sem anterior',
                desc: 'Atenciones acumuladas en los últimos 7 días operativos.',
                resueltas: '93.7% Resueltas',
                presencial: 55,
                telefonica: 31,
                online: 14,
                chartLabels: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
                dataPresencial: [140, 165, 180, 170, 155, 30],
                dataTelefonica: [80, 95, 100, 90, 85, 10],
                dataOnline: [35, 42, 48, 40, 38, 5]
            },
            mes: {
                total: '3.421',
                trend: '+18% vs mes anterior',
                desc: 'Atenciones registradas en la red de delegaciones municipales y canales digitales.',
                resueltas: '94.8% Resueltas',
                presencial: 54,
                telefonica: 32,
                online: 14,
                chartLabels: ['Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
                dataPresencial: [500, 610, 710, 680, 620, 750],
                dataTelefonica: [300, 380, 480, 420, 410, 520],
                dataOnline: [150, 200, 260, 220, 215, 276]
            },
            anio: {
                total: '28.940',
                trend: '+14% anual',
                desc: 'Total histórico consolidado de la gestión ciudadana 2026.',
                resueltas: '96.1% Resueltas',
                presencial: 52,
                telefonica: 33,
                online: 15,
                chartLabels: ['2021', '2022', '2023', '2024', '2025', '2026 (Proy.)'],
                dataPresencial: [3800, 4200, 4900, 5300, 6100, 6800],
                dataTelefonica: [2200, 2500, 2900, 3200, 3700, 4100],
                dataOnline: [800, 1100, 1400, 1700, 2100, 2400]
            }
        };

        function cambiarRangoTemporal(rango) {
            const data = datasetRangos[rango];
            if (!data) return;

            // Actualizar botones de filtro
            ['hoy', 'semana', 'mes', 'anio'].forEach(r => {
                const btn = document.getElementById(`btnRango${r.charAt(0).toUpperCase() + r.slice(1)}`);
                if (btn) {
                    if (r === rango) btn.classList.add('active');
                    else btn.classList.remove('active');
                }
            });

            updatePillSlider();

            // Actualizar Tarjeta Rectora (Flagship) con animación Number Ticker
            const numEl = document.querySelector('.flagship-metric-number');
            if (numEl) animateNumberTicker(numEl, data.total, 450);

            const trendEl = document.querySelector('.flagship-trend-chip');
            if (trendEl) trendEl.innerHTML = `<i class="bi bi-graph-up-arrow"></i> ${data.trend}`;

            const descEl = document.querySelector('.flagship-desc');
            if (descEl) descEl.textContent = data.desc;

            const headerRes = document.querySelector('.channel-dist-header .text-primary');
            if (headerRes) headerRes.textContent = data.resueltas;

            const segPre = document.querySelector('.ch-segment.ch-presencial');
            if (segPre) segPre.style.width = `${data.presencial}%`;
            const segTel = document.querySelector('.ch-segment.ch-telefonica');
            if (segTel) segTel.style.width = `${data.telefonica}%`;
            const segOnl = document.querySelector('.ch-segment.ch-online');
            if (segOnl) segOnl.style.width = `${data.online}%`;

            // Actualizar Gráfico Chart.js con animación fluida
            if (chartInstance) {
                chartInstance.options.animation = {
                    duration: 650,
                    easing: 'easeOutQuart'
                };
                chartInstance.data.labels = data.chartLabels;
                chartInstance.data.datasets[0].data = data.dataPresencial;
                chartInstance.data.datasets[1].data = data.dataTelefonica;
                chartInstance.data.datasets[2].data = data.dataOnline;
                chartInstance.update();
            }

            mostrarToast(`Vista actualizada: Rango temporal '${rango.toUpperCase()}'`);
        }

        /* ==========================================================================
           4. SELECCIÓN DE DELEGACIÓN EN EL MAPA COMUNAL INTERACTIVO
           ========================================================================== */
        const delegacionesMapaData = {
            centro: { nombre: 'Centro', mapa: 'Centro', sector: 'Área urbana central', badge: 'SEDE CENTRAL', badgeColor: '#C41230', monogram: 'CE', number: '01' },
            lascompanias: { id: 'companias', nombre: 'Las Compañías', mapa: 'Las Compañías', sector: 'Sector norte de la comuna', badge: 'SECTOR NORTE', badgeColor: '#6554C0', monogram: 'LC', number: '02' },
            lapampa: { id: 'pampa', nombre: 'La Pampa', mapa: 'La Pampa', sector: 'Sector sur de la comuna', badge: 'SECTOR SUR', badgeColor: '#008F8C', monogram: 'LP', number: '03' },
            laflorida: { id: 'antena', nombre: 'La Antena', mapa: 'La Antena', sector: 'Sector oriente de la comuna', badge: 'SECTOR ORIENTE', badgeColor: '#B86A08', monogram: 'LA', number: '04' },
            tierrasblancas: { id: 'costa', nombre: 'Avenida del Mar', mapa: 'Avenida del Mar', sector: 'Franja costera de la comuna', badge: 'BORDE COSTERO', badgeColor: '#1677A8', monogram: 'AM', number: '05' },
            rural: { id: 'rural', nombre: 'Rural', mapa: 'Rural', sector: 'Localidades rurales y caletas', badge: 'SECTOR RURAL', badgeColor: '#678341', monogram: 'RU', number: '06' }
        };

        window.currentMapSedeKey = 'centro';
        let mapaDelegacionesLeaflet = null;
        const datosSedesDelegaciones = {};
        const marcadoresDelegaciones = {};
        let popupDelegacion = null;

        async function inicializarMapaDelegaciones() {
            const mapElement = document.getElementById('mapaDelegacionesReal');
            const loader = document.getElementById('mapaDelegacionesLoader');
            if (!mapElement || mapaDelegacionesLeaflet) return;
            seleccionarDelegacionMapa(window.currentMapSedeKey);
            if (!window.maplibregl) {
                if (loader) loader.textContent = 'El mapa no está disponible. Puedes consultar las sedes en las fichas.';
                return;
            }
            mapaDelegacionesLeaflet = new maplibregl.Map({
                container: mapElement,
                style: 'https://tiles.openfreemap.org/styles/liberty',
                center: [-71.25, -29.91], zoom: 12,
                scrollZoom: false, attributionControl: true
            });
            mapaDelegacionesLeaflet.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
            // Los marcadores HTML quedan sobre la cartografía y no dependen del orden de sus capas.
            const resizeObserver = new ResizeObserver(() => mapaDelegacionesLeaflet.resize());
            resizeObserver.observe(mapElement);
            mapaDelegacionesLeaflet.on('remove', () => resizeObserver.disconnect());
            mapaDelegacionesLeaflet.on('error', () => {
                if (!mapaDelegacionesLeaflet.isStyleLoaded() && loader) {
                    loader.classList.remove('oculto');
                    loader.textContent = 'La cartografía está tardando en cargar. Las direcciones siguen disponibles en las fichas.';
                }
            });

            try {
                const response = await fetch('/static/data/delegaciones-la-serena.geojson', {
                    headers: { Accept: 'application/geo+json, application/json' }
                });
                if (!response.ok) throw new Error('No se pudieron consultar las sedes.');
                const geojson = await response.json();
                geojson.features.filter(feature => feature.properties.kind === 'office')
                    .forEach(feature => { datosSedesDelegaciones[feature.properties.name] = feature; });
                Object.entries(delegacionesMapaData).forEach(([key, data]) => {
                    const sede = datosSedesDelegaciones[data.mapa];
                    if (!sede) return;
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'delegation-map-pin';
                    button.style.setProperty('--delegation-color', data.badgeColor);
                    button.setAttribute('aria-label', 'Ver sede de ' + data.nombre);
                    button.setAttribute('aria-pressed', 'false');
                    button.title = data.nombre;
                    const dot = document.createElement('span');
                    dot.className = 'delegation-pin-dot';
                    dot.textContent = data.number;
                    button.appendChild(dot);
                    button.addEventListener('click', event => {
                        event.stopPropagation();
                        seleccionarDelegacionMapa(key);
                    });
                    marcadoresDelegaciones[key] = new maplibregl.Marker({ element: button, anchor: 'bottom' })
                        .setLngLat(sede.geometry.coordinates).addTo(mapaDelegacionesLeaflet);
                });
                const ready = () => {
                    if (loader) loader.classList.add('oculto');
                    seleccionarDelegacionMapa(window.currentMapSedeKey);
                };
                if (mapaDelegacionesLeaflet.loaded()) ready();
                else mapaDelegacionesLeaflet.once('load', ready);
                seleccionarDelegacionMapa(window.currentMapSedeKey);
            } catch (error) {
                if (loader) {
                    loader.classList.remove('oculto');
                    loader.textContent = 'No se pudieron cargar las sedes. Recarga la página para volver a intentarlo.';
                }
                console.error('Error al consultar sedes:', error);
            }
        }

        function seleccionarDelegacionMapa(key) {
            const data = delegacionesMapaData[key];
            if (!data) return;
            window.currentMapSedeKey = key;
            document.querySelectorAll('.serena-sede-pill').forEach(pill => {
                const selected = pill.id === 'pill-sede-' + key;
                pill.classList.toggle('active', selected);
                pill.setAttribute('aria-pressed', String(selected));
            });
            Object.entries(marcadoresDelegaciones).forEach(([markerKey, marker]) => {
                marker.getElement().classList.toggle('selected', markerKey === key);
                marker.getElement().setAttribute('aria-pressed', String(markerKey === key));
            });
            const card = document.getElementById('panelFocoTerritorial');
            if (card) card.style.setProperty('--delegation-color', data.badgeColor);
            const content = {
                mapFocusTitle: data.nombre, mapFocusSector: data.sector,
                mapFocusMonogram: data.monogram, mapFocusNumber: data.number,
                mapFocusBadge: data.badge
            };
            Object.entries(content).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) element.textContent = value;
            });
            const swatch = document.getElementById('mapFocusSwatch');
            if (swatch) swatch.style.setProperty('--delegation-color', data.badgeColor);
            const sede = datosSedesDelegaciones[data.mapa];
            const address = document.querySelector('#mapFocusAddress [data-address-value]');
            if (address) address.textContent = sede?.properties?.address || 'Consultando dirección de la sede…';
            const coordinates = document.getElementById('mapFocusCoordinates');
            if (coordinates) coordinates.textContent = sede
                ? sede.geometry.coordinates[1].toFixed(5) + ', ' + sede.geometry.coordinates[0].toFixed(5) : '—';

            if (mapaDelegacionesLeaflet && sede) {
                const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
                mapaDelegacionesLeaflet.resize();
                mapaDelegacionesLeaflet.easeTo({
                    center: sede.geometry.coordinates, zoom: 14,
                    duration: reducedMotion ? 0 : 650
                });
                if (popupDelegacion) popupDelegacion.remove();
                const popup = document.createElement('div');
                popup.className = 'delegation-map-label';
                const title = document.createElement('strong');
                title.textContent = data.nombre;
                const subtitle = document.createElement('span');
                subtitle.textContent = 'Sede municipal · ubicación de referencia';
                popup.append(title, subtitle);
                popupDelegacion = new maplibregl.Popup({ offset: 44, closeButton: false, maxWidth: '240px' })
                    .setLngLat(sede.geometry.coordinates).setDOMContent(popup).addTo(mapaDelegacionesLeaflet);
            }
        }

        function irADetalleDelegacionDesdeMapa() {
            const mapKeyToDelId = {
                centro: 'centro',
                lascompanias: 'companias',
                lapampa: 'pampa',
                laflorida: 'antena',
                tierrasblancas: 'costa',
                rural: 'rural'
            };
            const targetId = mapKeyToDelId[window.currentMapSedeKey || 'centro'] || 'centro';
            switchView('delegaciones');
            setTimeout(() => {
                if (typeof seleccionarDelegacion === 'function') {
                    seleccionarDelegacion(targetId);
                }
                const detailEl = document.getElementById('panelDetalleDelegacion');
                if (detailEl) detailEl.scrollIntoView({ behavior: 'smooth' });
            }, 120);
        }

        /* ==========================================================================
           5. GENERADOR DE INFORME EJECUTIVO EN PDF OFICIAL (JSPDF + AUTOTABLE)
           ========================================================================== */
        function generarInformeEjecutivoPDF() {
            try {
                if (!window.jspdf || !window.jspdf.jsPDF) {
                    mostrarToast('Error: Librería jsPDF no disponible.');
                    return;
                }
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF({
                    orientation: 'portrait',
                    unit: 'mm',
                    format: 'a4'
                });

                const elDate = document.getElementById('currentDateDisplay');
                const fechaActual = (elDate && elDate.textContent) ? elDate.textContent : 'Octubre 2026';

                // 1. Membrete Institucional Oficial
                doc.setFillColor(27, 54, 93); // Azul Marino Serena
                doc.rect(0, 0, 210, 24, 'F');

                doc.setFillColor(196, 18, 48); // Rojo Colonial
                doc.rect(0, 24, 210, 3, 'F');

                doc.setTextColor(255, 255, 255);
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(14);
                doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA', 14, 12);

                doc.setFont('helvetica', 'normal');
                doc.setFontSize(9);
                doc.text('DIRECCIÓN DE ATENCIÓN CIUDADANA — SISTEMA DE GESTIÓN REGIONAL (SGR)', 14, 18);

                // 2. Título del Documento
                doc.setTextColor(27, 54, 93);
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(16);
                doc.text('INFORME EJECUTIVO DE GESTIÓN Y RENDICIÓN MUNICIPAL', 14, 38);

                doc.setTextColor(100, 116, 139);
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(9);
                doc.text(`Fecha de Emisión: ${fechaActual} | Generado por: Administrador Municipal`, 14, 44);

                // 3. Resumen Ejecutivo (KPIs Clave)
                doc.setDrawColor(226, 232, 240);
                doc.setFillColor(248, 250, 252);
                doc.roundedRect(14, 50, 182, 28, 3, 3, 'FD');

                doc.setTextColor(27, 54, 93);
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(10);
                doc.text('CONSOLIDADO DE METAS & COBERTURA COMUNAL', 20, 58);

                doc.setFontSize(9);
                doc.setFont('helvetica', 'normal');
                doc.setTextColor(51, 65, 85);
                doc.text('• Padrón Activo de Vecinos: 12.458 inscritos (+12% semestral)', 20, 65);
                doc.text('• Atenciones Realizadas (Mes Activo): 3.421 trámites y solicitudes', 20, 71);
                doc.text('• Cobertura Territorial: 6 de 6 Delegaciones operativas al 100%', 110, 65);
                doc.text('• Cumplimiento Promedio de Metas: 87.0% (Meta esperada: 85%)', 110, 71);

                // 4. Tabla de Delegaciones (AutoTable)
                const tablaDelegacionesData = [
                    ['La Serena Centro', 'Los Carrera #301', '1.450', '6 min', '98.4%', 'Operativa'],
                    ['Las Compañías', 'Esmeralda #2451', '1.120', '9 min', '94.2%', 'Operativa'],
                    ['La Pampa', 'Juana Ross #120', '890', '7 min', '96.8%', 'Operativa'],
                    ['La Florida', 'Av. El Santo #1050', '670', '8 min', '95.1%', 'Operativa'],
                    ['Tierras Blancas', 'Calle Linares #890', '540', '11 min', '93.0%', 'Operativa'],
                    ['Sector Rural', 'Ruta 41 Km 8', '320', '5 min', '99.1%', 'Operativa']
                ];

                doc.autoTable({
                    startY: 85,
                    head: [['Delegación Municipal', 'Ubicación Sede', 'Atenciones', 'T. Espera', 'Satisfacción', 'Estado']],
                    body: tablaDelegacionesData,
                    theme: 'striped',
                    headStyles: {
                        fillColor: [27, 54, 93],
                        textColor: [255, 255, 255],
                        fontStyle: 'bold',
                        fontSize: 8.5
                    },
                    bodyStyles: {
                        fontSize: 8,
                        textColor: [30, 41, 59]
                    },
                    margin: { left: 14, right: 14 }
                });

                // 5. Tabla de Canales de Atención
                const finalY = doc.lastAutoTable.finalY + 10;
                doc.setTextColor(27, 54, 93);
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(11);
                doc.text('DISTRIBUCIÓN Y RESOLUCIÓN POR CANAL CIUDADANO', 14, finalY);

                const canalesData = [
                    ['Canal Presencial (Módulos)', '1.847', '54%', '95.2%'],
                    ['Canal Telefónico (Call Center 800)', '1.095', '32%', '93.8%'],
                    ['Canal Online / Portal Vecino', '479', '14%', '96.4%']
                ];

                doc.autoTable({
                    startY: finalY + 4,
                    head: [['Canal de Contacto', 'Total Casos', 'Participación', 'Tasa Resolución']],
                    body: canalesData,
                    theme: 'grid',
                    headStyles: {
                        fillColor: [196, 18, 48],
                        textColor: [255, 255, 255],
                        fontStyle: 'bold',
                        fontSize: 8.5
                    },
                    bodyStyles: {
                        fontSize: 8
                    },
                    margin: { left: 14, right: 14 }
                });

                // 6. Pie de Página y Firma Digital Institucional
                const footerY = doc.lastAutoTable.finalY + 16;
                doc.setDrawColor(203, 213, 225);
                doc.line(14, footerY, 196, footerY);

                doc.setFontSize(8);
                doc.setFont('helvetica', 'normal');
                doc.setTextColor(148, 163, 184);
                doc.text('Documento oficial generado automáticamente por el Sistema de Gestión Ciudadana SGR v1.0.', 14, footerY + 6);
                doc.text('Firma Digital: 8a7f9c2d-muni-laserena-valida | Ilustre Municipalidad de La Serena', 14, footerY + 11);

                // Guardar PDF
                doc.save(`Informe_Ejecutivo_Municipal_LaSerena_${new Date().toISOString().slice(0, 10)}.pdf`);
                mostrarToast('✓ Informe Ejecutivo Municipal descargado en PDF con éxito.');
            } catch (err) {
                console.error('Error generando PDF:', err);
                mostrarToast('Ocurrió un error al compilar el documento PDF.');
            }
        }

        function abrirModalAuditoria() {
            if (!bsModalAuditoria) {
                const el = document.getElementById('modalAuditoria');
                if (el && window.bootstrap) bsModalAuditoria = new bootstrap.Modal(el);
            }
            if (bsModalAuditoria) bsModalAuditoria.show();
            cargarLogsAuditoriaDB();
        }

        function exportarExcelAuditoria() {
            if (!logsFiltradosAuditoria.length) {
                mostrarToast('No hay registros de auditoría para exportar.');
                return;
            }
            let csv = "Fecha y Hora;Administrador Responsable;Usuario;Acción;Descripción de Modificación;Tabla Afectada;ID Registro\n";
            logsFiltradosAuditoria.forEach(l => {
                csv += `"${l.timestamp}";"${l.admin_name}";"${l.admin_username}";"${l.action}";"${l.description.replace(/"/g, '""')}";"${l.affected_table}";"${l.affected_record_id}"\n`;
            });
            const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Log_Auditoria_Municipal_LaSerena_${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            mostrarToast('✓ Log de auditoría exportado en CSV/Excel.');
        }

        function exportarGraficoPNG() {
            if (!chartInstance) return;
            const a = document.createElement('a');
            a.href = chartInstance.toBase64Image();
            a.download = 'Grafico_Atenciones_LaSerena.png';
            a.click();
            mostrarToast('✓ Gráfico exportado');
        }

        /* ==========================================================================
           MÓDULO DE REPORTES Y ESTADÍSTICAS INSTITUCIONALES (OFICIAL LA SERENA)
           Con Comparativas 1vs1, Multidelegacional y Monitoreo en Tiempo Real
           ========================================================================== */
        let chartRepDelegacionesInstance = null;
        let chartRepCanalesInstance = null;
        let chartRepEvolucionInstance = null;
        let chartRepTramitesInstance = null;

        // Instancias para comparativa 1 vs 1 y Multi
        let chartCompareRadarInstance = null;
        let chartCompareTramitesInstance = null;
        let chartMultiRankingInstance = null;
        let chartMultiTiemposInstance = null;
        let chartMultiSatisfaccionInstance = null;

        // Subvista activa ('general', '1vs1', 'multi')
        let subvistaReportesActiva = 'general';

        // Catálogo territorial de referencia; no contiene métricas inventadas.
        const catalogoMetricasDelegaciones = {
            centro: { nombre: 'Centro Histórico', sector: 'Área central' },
            companias: { nombre: 'Las Compañías', sector: 'Sector norte' },
            pampa: { nombre: 'La Pampa', sector: 'Sector sur' },
            antena: { nombre: 'La Antena / San Joaquín', sector: 'Sector oriente' },
            costa: { nombre: 'Avenida del Mar', sector: 'Borde costero' },
            rural: { nombre: 'Sector Rural', sector: 'Localidades rurales' }
        };

        // Estado del Tiempo Real (Live Mode)
        let timerLiveReportes = null;
        let esTiempoRealActivo = false;
        let segundosLive = 5;

        function initReportesCharts() {
            // Inicializar vista general por defecto
            initChartsGeneralReportes();
            iniciarTemporizadorTiempoReal();
        }

        function initChartsGeneralReportes() {
            const emptyData = { labels: [], datasets: [] };
            // 1. Delegaciones Bar Chart
            const ctxDel = document.getElementById('chartReporteDelegaciones');
            if (ctxDel && !chartRepDelegacionesInstance) {
                chartRepDelegacionesInstance = new Chart(ctxDel.getContext('2d'), {
                    type: 'bar',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false }, y: { display: false }
                        }
                    }
                });
            } else if (chartRepDelegacionesInstance) {
                chartRepDelegacionesInstance.resize();
            }

            // 2. Canales Doughnut Chart
            const ctxCan = document.getElementById('chartReporteCanales');
            if (ctxCan && !chartRepCanalesInstance) {
                chartRepCanalesInstance = new Chart(ctxCan.getContext('2d'), {
                    type: 'doughnut',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        cutout: '65%'
                    }
                });
            } else if (chartRepCanalesInstance) {
                chartRepCanalesInstance.resize();
            }

            // 3. Evolución Line Chart
            const ctxEvo = document.getElementById('chartReporteEvolucion');
            if (ctxEvo && !chartRepEvolucionInstance) {
                chartRepEvolucionInstance = new Chart(ctxEvo.getContext('2d'), {
                    type: 'line',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false }, y: { display: false }
                        }
                    }
                });
            } else if (chartRepEvolucionInstance) {
                chartRepEvolucionInstance.resize();
            }

            // 4. Trámites Horizontal Bar Chart
            const ctxTra = document.getElementById('chartReporteTramites');
            if (ctxTra && !chartRepTramitesInstance) {
                chartRepTramitesInstance = new Chart(ctxTra.getContext('2d'), {
                    type: 'bar',
                    indexAxis: 'y',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false }, y: { display: false }
                        }
                    }
                });
            } else if (chartRepTramitesInstance) {
                chartRepTramitesInstance.resize();
            }
        }

        function cambiarSubvistaReporte(subvista, updateUrl = true) {
            if (!adminReportViews.has(subvista)) return;
            subvistaReportesActiva = subvista;
            if (updateUrl) {
                const url = adminRouteUrl('reportes', subvista);
                if (window.location.pathname !== url) window.history.pushState(null, '', url);
            }

            // Actualizar botones de pestañas
            const btnGen = document.getElementById('tabReporteGeneral');
            const btn1v1 = document.getElementById('tabReporte1vs1');
            const btnMul = document.getElementById('tabReporteMulti');

            const vGen = document.getElementById('subvistaReporteGeneral');
            const v1v1 = document.getElementById('subvistaReporte1vs1');
            const vMul = document.getElementById('subvistaReporteMulti');

            // Reset tab styles
            [btnGen, btn1v1, btnMul].forEach(b => {
                if (b) {
                    b.className = 'btn btn-sm border-0 fw-semibold text-secondary px-3 py-2';
                    b.style.background = 'transparent';
                    b.style.color = '#64748B';
                    b.classList.remove('shadow-sm');
                }
            });

            // Hide all views
            if (vGen) vGen.classList.remove('active');
            if (v1v1) v1v1.classList.remove('active');
            if (vMul) vMul.classList.remove('active');

            if (subvista === 'general') {
                if (btnGen) {
                    btnGen.className = 'btn btn-sm btn-white border-0 fw-bold px-3 py-2 shadow-sm';
                    btnGen.style.background = '#FFFFFF';
                    btnGen.style.color = 'var(--muni-navy)';
                }
                if (vGen) vGen.classList.add('active');
                initChartsGeneralReportes();
            } else if (subvista === '1vs1') {
                if (btn1v1) {
                    btn1v1.className = 'btn btn-sm btn-white border-0 fw-bold px-3 py-2 shadow-sm';
                    btn1v1.style.background = '#FFFFFF';
                    btn1v1.style.color = 'var(--muni-red)';
                }
                if (v1v1) v1v1.classList.add('active');
                actualizarComparativa1vs1();
            } else if (subvista === 'multi') {
                if (btnMul) {
                    btnMul.className = 'btn btn-sm btn-white border-0 fw-bold px-3 py-2 shadow-sm';
                    btnMul.style.background = '#FFFFFF';
                    btnMul.style.color = '#16A34A';
                }
                if (vMul) vMul.classList.add('active');
                initComparativaMultiCharts();
            }
        }

        /* ==========================================================================
           LÓGICA COMPARATIVA 1 VS 1 (FRENTE A FRENTE)
           ========================================================================== */
        function actualizarComparativa1vs1() {
            const elSelA = document.getElementById('selectCompareDelA');
            const idA = (elSelA && elSelA.value) ? elSelA.value : 'centro';
            const elSelBInit = document.getElementById('selectCompareDelB');
            let idB = (elSelBInit && elSelBInit.value) ? elSelBInit.value : 'companias';

            const delA = catalogoMetricasDelegaciones[idA] || catalogoMetricasDelegaciones['centro'];
            const delB = catalogoMetricasDelegaciones[idB] || catalogoMetricasDelegaciones['companias'];

            // Actualizar subtítulos territoriales
            const subA = document.getElementById('compareSubA');
            if (subA) subA.textContent = delA.sector;
            const subB = document.getElementById('compareSubB');
            if (subB) subB.textContent = delB.sector;

            const grid = document.getElementById('gridMetricas1vs1');
            const elConc = document.getElementById('conclusion1vs1');
            if (grid) grid.innerHTML = `<div class="col-12"><div class="dashboard-empty-state p-4 text-center"><strong>${delA.nombre} y ${delB.nombre}</strong><p class="mb-0 mt-1">La comparación aparecerá cuando exista una consulta conectada a registros reales de atención.</p></div></div>`;
            ['chartCompareRadar', 'chartCompareTramites'].forEach(id => {
                const canvas = document.getElementById(id);
                if (canvas && canvas.closest('.card')) canvas.closest('.card').classList.add('d-none');
            });
            if (elConc) elConc.textContent = 'Sin una fuente de reportes conectada, no es posible calcular diferencias ni emitir conclusiones.';
        }

        /* ==========================================================================
           LÓGICA COMPARATIVA MULTIDELEGACIONAL (TODAS CONTRA TODAS)
           ========================================================================== */
        function initComparativaMultiCharts() {
            document.querySelectorAll('#subvistaReporteMulti canvas').forEach(canvas => {
                const card = canvas.closest('.card');
                if (card) card.classList.add('d-none');
            });
        }

        /* ==========================================================================
           SISTEMA DE TIEMPO REAL / LIVE STREAM SIMULADO
           ========================================================================== */
        function iniciarTemporizadorTiempoReal() {
            if (timerLiveReportes) clearInterval(timerLiveReportes);
            const elSec = document.getElementById('liveCounterSec');
            if (elSec) elSec.textContent = 'Pausado';
            const dot = document.getElementById('liveDotIndicator');
            const txt = document.getElementById('liveTextIndicator');
            const btnTxt = document.getElementById('btnToggleLiveText');
            const btnIcon = document.getElementById('btnToggleLiveIcon');
            if (dot) dot.classList.add('paused');
            if (txt) txt.textContent = 'Sin conexión en vivo';
            if (btnTxt) btnTxt.textContent = 'API pendiente';
            if (btnIcon) {
                btnIcon.classList.remove('bi-pause-fill');
                btnIcon.classList.add('bi-plug-fill');
            }
        }

        function toggleTiempoRealReportes() {
            esTiempoRealActivo = false;
            const dot = document.getElementById('liveDotIndicator');
            const txt = document.getElementById('liveTextIndicator');
            const btnTxt = document.getElementById('btnToggleLiveText');
            const btnIcon = document.getElementById('btnToggleLiveIcon');

            if (dot) dot.classList.add('paused');
            if (txt) txt.textContent = 'Sin conexión en vivo';
            if (btnTxt) btnTxt.textContent = 'Disponible al conectar API';
            if (btnIcon) {
                btnIcon.classList.remove('bi-pause-fill');
                btnIcon.classList.add('bi-plug-fill');
            }
            const btn = document.getElementById('btnToggleLiveReportes');
            if (btn) btn.disabled = true;
            mostrarToast('La actualización en vivo se habilitará cuando exista una API de reportes conectada.');
        }

        function forzarActualizacionEnVivo() {
            mostrarToast('Aún no hay una API de reportes conectada para actualizar estos resultados.');
        }

        function ejecutarTickTiempoReal() {
            actualizarReportesDatos();
        }

        function actualizarReportesDatos() {
            const elP = document.getElementById('filtroPeriodoReporte');
            const p = (elP && elP.value) ? elP.value : 'trimestre';
            const elD = document.getElementById('filtroDelegacionReporte');
            const d = (elD && elD.value) ? elD.value : '';
            const elC = document.getElementById('filtroCanalReporte');
            const c = (elC && elC.value) ? elC.value : '';

            const params = new URLSearchParams({ period: p });
            if (d) params.set('delegation', d);
            if (c) params.set('channel', c);
            mostrarToast('Los filtros se habilitarán cuando el módulo tenga su consulta de reportes conectada a datos reales.');
        }

        function restablecerFiltrosReportes() {
            if (document.getElementById('filtroPeriodoReporte')) document.getElementById('filtroPeriodoReporte').value = 'trimestre';
            if (document.getElementById('filtroDelegacionReporte')) document.getElementById('filtroDelegacionReporte').value = '';
            if (document.getElementById('filtroCanalReporte')) document.getElementById('filtroCanalReporte').value = '';
            mostrarToast('Filtros restablecidos. Los datos se consultarán al conectar la API de reportes.');
        }

        /* ==========================================================================
           EXPORTACIÓN COMPLETA A EXCEL MULTI-HOJA Y PDF OFICIAL
           ========================================================================== */
        function exportarReportesExcel() {
            if (!window.XLSX) {
                Swal.fire('La librería XLSX está cargando.');
                return;
            }

            const wb = XLSX.utils.book_new();

            // Hoja 1: Resumen Ejecutivo y KPIs
            const resumenData = [
                ["ILUSTRE MUNICIPALIDAD DE LA SERENA - GESTIÓN DE ATENCIÓN CIUDADANA (SGR)"],
                ["INFORME EJECUTIVO DE RENDIMIENTO INSTITUCIONAL Y TERRITORIAL"],
                ["Fecha de Emisión:", new Date().toLocaleString('es-CL')],
                [],
                ["Indicadores", "Estado"],
                ["Atenciones", "Los valores se incorporarán al conectar la consulta a la base de datos."],
                ["Tiempo de espera y satisfacción", "No hay datos suficientes registrados para calcularlos."]
            ];
            const ws1 = XLSX.utils.aoa_to_sheet(resumenData);
            XLSX.utils.book_append_sheet(wb, ws1, "Resumen_Ejecutivo");

            // Hoja 2: Rendimiento por Delegación
            const table = document.getElementById('tablaReportesDelegaciones');
            if (table) {
                const ws2 = XLSX.utils.table_to_sheet(table);
                XLSX.utils.book_append_sheet(wb, ws2, "Todas_Las_Delegaciones");
            }

            // Hoja 3: Comparativa 1 vs 1 Activa
            const elCompA = document.getElementById('selectCompareDelA');
            const idA = (elCompA && elCompA.value) ? elCompA.value : 'centro';
            const elCompB = document.getElementById('selectCompareDelB');
            const idB = (elCompB && elCompB.value) ? elCompB.value : 'companias';
            const delA = catalogoMetricasDelegaciones[idA] || catalogoMetricasDelegaciones['centro'];
            const delB = catalogoMetricasDelegaciones[idB] || catalogoMetricasDelegaciones['companias'];

            const compData = [
                ["COMPARATIVA FRENTE A FRENTE (1 VS 1)"],
                ["Métrica", delA.nombre, delB.nombre, "Estado"],
                ["Atenciones, metas, tiempos, satisfacción y dotación", "No disponible", "No disponible", "API de reportes pendiente"]
            ];
            const ws3 = XLSX.utils.aoa_to_sheet(compData);
            XLSX.utils.book_append_sheet(wb, ws3, "Comparativa_1vs1");

            // Hoja 4: Canales de Atención y Ranking de Trámites
            const canalesData = [
                ["DISTRIBUCIÓN POR CANAL DE ATENCIÓN"],
                ["Canal", "Volumen Atenciones", "Porcentaje"],
                ["No disponible", "—", "—"],
                [],
                ["TOP TRÁMITES MÁS DEMANDADOS"],
                ["Trámite", "Solicitudes Registradas"],
                ["No disponible", "—"]
            ];
            const ws4 = XLSX.utils.aoa_to_sheet(canalesData);
            XLSX.utils.book_append_sheet(wb, ws4, "Canales_Y_Tramites");

            XLSX.writeFile(wb, "Reporte_Estadistico_Integral_LaSerena_2026.xlsx");
            mostrarToast("✓ Archivo Excel Multi-Hoja descargado con éxito.");
        }

        function generarReportePDFOficial() {
            if (!window.jspdf) {
                Swal.fire('La librería PDF está cargando.');
                return;
            }
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'letter' });

            // Banda superior Roja La Serena (#C41230) y Azul Marino (#1B365D)
            doc.setFillColor(196, 18, 48);
            doc.rect(0, 0, 216, 16, 'F');
            doc.setFillColor(27, 54, 93);
            doc.rect(0, 16, 216, 3, 'F');

            // Encabezado
            doc.setTextColor(255, 255, 255);
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(11);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA — GESTIÓN DE ATENCIÓN CIUDADANA', 14, 11);

            // Título Principal
            doc.setTextColor(27, 54, 93);
            doc.setFontSize(15);
            doc.setFont('helvetica', 'bold');
            doc.text('INFORME ESTADÍSTICO DE GESTIÓN MUNICIPAL Y TERRITORIAL', 14, 28);

            doc.setFontSize(8.5);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(90, 100, 120);
            doc.text(`Fecha de emisión: ${new Date().toLocaleDateString('es-CL')} | Borrador con datos disponibles en la base`, 14, 34);

            // Resumen de KPIs
            doc.autoTable({
                startY: 39,
                theme: 'plain',
                styles: { fontSize: 8.5, cellPadding: 2 },
                head: [['Indicador Clave', 'Estado']],
                body: [
                    ['Métricas de gestión', 'Aún no existe conexión de consulta para este reporte.'],
                    ['Tiempo de espera y satisfacción', 'No hay registros suficientes para calcular estos indicadores.']
                ],
                headStyles: { fillColor: [244, 248, 252], textColor: [27, 54, 93], fontStyle: 'bold' }
            });

            // Tabla de Delegaciones
            doc.autoTable({
                startY: doc.lastAutoTable.finalY + 6,
                html: '#tablaReportesDelegaciones',
                theme: 'striped',
                headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 8 },
                styles: { fontSize: 7.5, cellPadding: 2 },
                alternateRowStyles: { fillColor: [248, 250, 252] }
            });

            // Pie y Firma
            const finalY = doc.lastAutoTable.finalY + 22;
            doc.setDrawColor(200, 200, 200);
            doc.line(20, finalY, 80, finalY);
            doc.line(135, finalY, 195, finalY);

            doc.setFontSize(8);
            doc.setTextColor(80, 80, 80);
            doc.text('Administrador Municipal', 50, finalY + 5, { align: 'center' });
            doc.text('Ilustre Municipalidad de La Serena', 50, finalY + 9, { align: 'center' });

            doc.text('Director(a) de Atención Ciudadana', 165, finalY + 5, { align: 'center' });
            doc.text('Secretaría Comunal de Planificación', 165, finalY + 9, { align: 'center' });

            doc.save('Informe_Gestion_Atencion_Ciudadana_LaSerena.pdf');
            mostrarToast('Informe PDF de estado generado. Las métricas se incluirán al conectar el módulo a datos verificables.');
        }

        function renderAtencionesChart() {
            const ctx = document.getElementById('atencionesChart');
            if (!ctx) return;
            const chartCtx = ctx.getContext('2d');

            const gBlue = chartCtx.createLinearGradient(0, 0, 0, 240);
            gBlue.addColorStop(0, 'rgba(13, 110, 253, 0.28)');
            gBlue.addColorStop(1, 'rgba(13, 110, 253, 0.00)');

            const gGreen = chartCtx.createLinearGradient(0, 0, 0, 240);
            gGreen.addColorStop(0, 'rgba(22, 163, 74, 0.22)');
            gGreen.addColorStop(1, 'rgba(22, 163, 74, 0.00)');

            const gPurple = chartCtx.createLinearGradient(0, 0, 0, 240);
            gPurple.addColorStop(0, 'rgba(124, 58, 237, 0.20)');
            gPurple.addColorStop(1, 'rgba(124, 58, 237, 0.00)');

            chartInstance = new Chart(chartCtx, {
                type: 'line',
                data: {
                    labels: ['Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
                    datasets: [
                        { label: 'Presencial', data: [500, 610, 720, 680, 620, 750], borderColor: '#0D6EFD', backgroundColor: gBlue, borderWidth: 2.5, fill: true, tension: 0.38, pointRadius: 4, pointBackgroundColor: '#0D6EFD' },
                        { label: 'Telefónica', data: [290, 380, 480, 410, 400, 540], borderColor: '#16A34A', backgroundColor: gGreen, borderWidth: 2.5, fill: true, tension: 0.38, pointRadius: 4, pointBackgroundColor: '#16A34A' },
                        { label: 'Online', data: [130, 190, 270, 210, 195, 280], borderColor: '#7C3AED', backgroundColor: gPurple, borderWidth: 2.5, fill: true, tension: 0.38, pointRadius: 4, pointBackgroundColor: '#7C3AED' }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#64748B' } },
                        y: { min: 0, max: 1000, ticks: { stepSize: 250, color: '#64748B' }, grid: { color: 'rgba(226, 232, 240, 0.6)' } }
                    }
                }
            });
        }

        /* ==========================================================================
           MÓDULO PROFESIONAL DE GESTIÓN DE USUARIOS Y ACCESOS (ADMINISTRADOR)
           Conectado a APIs Django / Base de Datos Municipal (SQLite & AWS Compatible)
           ========================================================================== */

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        async function cargarUsuariosDesdeDB(mostrarAviso = false) {
            try {
                const res = await fetch('/api/users/');
                const data = await res.json();
                if (!data.success) throw new Error(data.message || 'Error al consultar base de datos');

                datasetUsuarios = data.users || [];
                window.datasetUsuarios = datasetUsuarios;
                rolesCatalog = data.roles || [];
                delegationsCatalog = data.delegations || [];
                positionsCatalog = data.positions || [];

                // Actualizar contadores KPI
                if (data.summary) {
                    const elTot = document.getElementById('lblTotalUsuarios');
                    if (elTot) elTot.textContent = data.summary.total;
                    const elAct = document.getElementById('lblActivosUsuarios');
                    if (elAct) elAct.textContent = data.summary.activos;
                    const elIna = document.getElementById('lblInactivosUsuarios');
                    if (elIna) elIna.textContent = data.summary.inactivos;
                    const elAdm = document.getElementById('lblAdminsUsuarios');
                    if (elAdm) elAdm.textContent = data.summary.admins;

                    const elPorc = document.getElementById('lblPorcActivos');
                    if (elPorc && data.summary.total > 0) {
                        const pct = Math.round((data.summary.activos / data.summary.total) * 100);
                        elPorc.textContent = `${pct}% de dotación habilitada`;
                    }
                }

                // Poblar Select de Filtros si no tienen opciones
                const selectDel = document.getElementById('filtroDelegacionUsuario');
                if (selectDel && selectDel.options.length <= 1) {
                    delegationsCatalog.forEach(d => {
                        const opt = document.createElement('option');
                        opt.value = d.id;
                        opt.textContent = d.name;
                        selectDel.appendChild(opt);
                    });
                }

                const selectRol = document.getElementById('filtroRolUsuario');
                if (selectRol && selectRol.options.length <= 1) {
                    rolesCatalog.forEach(r => {
                        const opt = document.createElement('option');
                        opt.value = r.id;
                        opt.textContent = r.name;
                        selectRol.appendChild(opt);
                    });
                }

                filtrarUsuarios();

                if (mostrarAviso) {
                    mostrarToast('✓ Base de datos sincronizada: ' + datasetUsuarios.length + ' usuarios cargados.');
                }
            } catch (err) {
                console.error("Error al cargar usuarios:", err);
                mostrarToast('⚠ Error al conectar con la base de datos: ' + err.message);
            }
        }
        window.cargarUsuariosDesdeDB = cargarUsuariosDesdeDB;

        let filtroFacetUsuarioActual = '';

        function filtrarUsuariosFacet(filtro, btn) {
            filtroFacetUsuarioActual = filtro;
            document.querySelectorAll('.usuario-filter-pill').forEach(p => p.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filtrarUsuarios();
        }

        function filtrarUsuarios() {
            const elSearchU = document.getElementById('searchUsuariosInput');
            const query = (elSearchU && elSearchU.value ? elSearchU.value : '').toLowerCase().trim();
            const elDelU = document.getElementById('filtroDelegacionUsuario');
            const delFiltro = (elDelU && elDelU.value) ? elDelU.value : '';
            const elRolU = document.getElementById('filtroRolUsuario');
            const rolFiltro = (elRolU && elRolU.value) ? elRolU.value : '';
            const elEstU = document.getElementById('filtroEstadoUsuario');
            const estFiltro = (elEstU && elEstU.value) ? elEstU.value : '';

            filasFiltradasUsuarios = datasetUsuarios.filter(u => {
                const matchTexto = !query ||
                    (u.full_name || '').toLowerCase().includes(query) ||
                    (u.username || '').toLowerCase().includes(query) ||
                    (u.rut || '').toLowerCase().includes(query) ||
                    (u.email || '').toLowerCase().includes(query) ||
                    (u.position_name || '').toLowerCase().includes(query);

                const matchDel = !delFiltro || String(u.delegation_id) === String(delFiltro);
                const matchRol = !rolFiltro || (u.roles || []).some(r => String(r.id) === String(rolFiltro));
                const matchEst = !estFiltro || u.status === estFiltro;

                // Filtro por Facet Pills
                let matchFacet = true;
                if (filtroFacetUsuarioActual === 'Activo') {
                    matchFacet = u.status === 'Activo';
                } else if (filtroFacetUsuarioActual === 'Inactivo') {
                    matchFacet = u.status === 'Inactivo';
                } else if (filtroFacetUsuarioActual === 'admin') {
                    matchFacet = u.is_superuser || (u.roles || []).some(r => r.name.toLowerCase().includes('admin'));
                } else if (filtroFacetUsuarioActual === 'gestor') {
                    matchFacet = (u.roles || []).some(r => r.name.toLowerCase().includes('gestor'));
                } else if (filtroFacetUsuarioActual === 'verificador') {
                    matchFacet = (u.roles || []).some(r => r.name.toLowerCase().includes('verificador'));
                } else if (filtroFacetUsuarioActual === 'Centro Histórico') {
                    matchFacet = (u.delegation_name || '').toLowerCase().includes('centro');
                } else if (filtroFacetUsuarioActual === 'Las Compañías') {
                    matchFacet = (u.delegation_name || '').toLowerCase().includes('compañ');
                } else if (filtroFacetUsuarioActual === 'Pampa') {
                    matchFacet = (u.delegation_name || '').toLowerCase().includes('pampa');
                } else if (filtroFacetUsuarioActual === 'Rural') {
                    matchFacet = (u.delegation_name || '').toLowerCase().includes('rural');
                }

                return matchTexto && matchDel && matchRol && matchEst && matchFacet;
            });

            // Aplicar orden
            aplicarOrdenUsuarios();
            paginaActualUsuarios = 1;
            renderTablaUsuarios();
        }

        function limpiarFiltrosUsuarios() {
            if (document.getElementById('searchUsuariosInput')) document.getElementById('searchUsuariosInput').value = '';
            if (document.getElementById('filtroDelegacionUsuario')) document.getElementById('filtroDelegacionUsuario').value = '';
            if (document.getElementById('filtroRolUsuario')) document.getElementById('filtroRolUsuario').value = '';
            if (document.getElementById('filtroEstadoUsuario')) document.getElementById('filtroEstadoUsuario').value = '';
            filtroFacetUsuarioActual = '';
            document.querySelectorAll('.usuario-filter-pill').forEach((p, idx) => {
                if (idx === 0) p.classList.add('active');
                else p.classList.remove('active');
            });
            filtrarUsuarios();
        }

        function ordenarUsuarios(campo) {
            if (campoOrdenUsuarios === campo) {
                ordenAscUsuarios = !ordenAscUsuarios;
            } else {
                campoOrdenUsuarios = campo;
                ordenAscUsuarios = true;
            }
            aplicarOrdenUsuarios();
            document.querySelectorAll('#tablaUsuarios thead [data-sort-column]').forEach(th => {
                th.setAttribute('aria-sort', th.dataset.sortColumn === campo ? (ordenAscUsuarios ? 'ascending' : 'descending') : 'none');
            });
            renderTablaUsuarios();
        }

        function aplicarOrdenUsuarios() {
            filasFiltradasUsuarios.sort((a, b) => {
                let valA = a[campoOrdenUsuarios] || '';
                let valB = b[campoOrdenUsuarios] || '';
                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();

                if (valA < valB) return ordenAscUsuarios ? -1 : 1;
                if (valA > valB) return ordenAscUsuarios ? 1 : -1;
                return 0;
            });
        }

        function renderTablaUsuarios() {
            const tbody = document.getElementById('tablaUsuariosBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            const inicio = (paginaActualUsuarios - 1) * filasPorPaginaUsuarios;
            const fin = inicio + filasPorPaginaUsuarios;
            const datos = filasFiltradasUsuarios.slice(inicio, fin);

            if (datos.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">
                    <div class="empty-state-pro py-2">
                        <div class="empty-state-icon"><i class="bi bi-person-x"></i></div>
                        <div class="empty-state-title">No se encontraron funcionarios</div>
                        <div class="empty-state-desc">No hay registros coincidentes con los filtros aplicados en esta vista.</div>
                        <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3" onclick="limpiarFiltrosUsuarios()">Restablecer Filtros</button>
                    </div>
                </td></tr>`;
                const lblInfo = document.getElementById('lblRegistrosInfoUsuarios');
                if (lblInfo) lblInfo.textContent = '0 registros encontrados';
                actualizarIndicadorTablaUsuarios(0, 0, 0);
                actualizarPaginadorUsuarios(0);
                return;
            }

            datos.forEach((u, idx) => {
                const tr = document.createElement('tr');
                tr.className = 'stagger-item';
                tr.style.setProperty('--stagger-i', idx);
                const rowNum = inicio + idx + 1;
                const esAdmin = u.is_superuser || (u.roles || []).some(r => r.name.toLowerCase().includes('admin'));

                // Badges de Roles
                let rolesHtml = '';
                if (u.roles && u.roles.length > 0) {
                    rolesHtml = u.roles.map(r => {
                        const rLower = r.name.toLowerCase();
                        let badgeCls = 'bg-light text-dark border';
                        let rIcon = '';
                        if (rLower.includes('admin')) {
                            badgeCls = 'bg-danger-subtle text-danger border border-danger-subtle';
                            rIcon = '<i class="bi bi-shield-fill me-1"></i>';
                        } else if (rLower.includes('verificador')) {
                            badgeCls = 'bg-info-subtle text-info-emphasis border border-info-subtle';
                            rIcon = '<i class="bi bi-check-circle me-1"></i>';
                        } else if (rLower.includes('gestor') || rLower.includes('funcionario')) {
                            badgeCls = 'bg-success-subtle text-success border border-success-subtle';
                            rIcon = '<i class="bi bi-person me-1"></i>';
                        } else if (rLower.includes('coord') || rLower.includes('delegado')) {
                            badgeCls = 'bg-primary-subtle text-primary border border-primary-subtle';
                            rIcon = '<i class="bi bi-diagram-3 me-1"></i>';
                        }
                        return `<span class="badge ${badgeCls} px-2 py-1" style="font-size: 0.78rem; font-weight: 600;">${rIcon}${escapeHtml(r.name)}</span>`;
                    }).join(' ');
                } else {
                    rolesHtml = `<span class="text-muted small">Sin rol</span>`;
                }

                // Delegación y Cargo limpios
                let delegacionLimpia = (u.delegation_name || 'Sin delegación').replace(/^Delegación\s+/i, '');
                let cargoLimpio = u.position_name || '';

                // Estado interactivo
                const isActivo = u.status === 'Activo';
                const statusBadge = `
                    <button class="btn btn-sm p-0 border-0" onclick="toggleEstadoUsuario(${u.id})" title="Clic para alternar estado">
                        <span class="badge ${isActivo ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-danger-subtle text-danger border border-danger-subtle'} px-3 py-1 rounded-pill" style="font-size: 0.80rem; font-weight: 700; cursor: pointer;">
                            <i class="bi ${isActivo ? 'bi-check-circle-fill' : 'bi-x-circle-fill'} me-1"></i>${u.status}
                        </span>
                    </button>
                `;

                // Avatar con iniciales y anillo institucional
                const initials = (u.full_name || 'U').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
                const avatarRingColor = esAdmin ? 'var(--muni-red)' : 'var(--muni-navy)';
                const isSelected = typeof selectedTableRows !== 'undefined' && selectedTableRows.has(u.id);
                if (isSelected) tr.classList.add('row-selected');

                tr.innerHTML = `
                    <td class="text-center" style="vertical-align: middle;">
                        <input type="checkbox" class="form-check-input check-user-row" data-id="${u.id}" ${isSelected ? 'checked' : ''} onchange="toggleFilaSeleccionada(${u.id}, this)">
                    </td>
                    <td class="text-center fw-semibold text-secondary" style="font-size: 0.85rem; vertical-align: middle;">${rowNum}</td>
                    <td style="vertical-align: middle; cursor: pointer;" onclick="seleccionarUsuarioDetalle('${u.id}')">
                        <div class="d-flex align-items-center gap-2">
                            <div class="user-avatar-pill ${esAdmin ? 'admin' : ''}" style="width: 38px; height: 38px; font-size: 0.85rem; font-weight: 800; border: 2px solid ${avatarRingColor}; flex-shrink: 0; background: ${esAdmin ? 'var(--muni-red)' : 'var(--muni-navy)'}; color: #FFF;">
                                ${escapeHtml(initials)}
                            </div>
                            <div style="min-width: 0;">
                                <div class="d-flex align-items-center gap-1">
                                    <span class="fw-bold text-truncate" style="color: var(--muni-navy); font-size: 0.90rem;">${escapeHtml(u.full_name)}</span>
                                    ${esAdmin ? '<span class="badge rounded-pill px-2 py-0 text-white fw-bold" style="background: var(--muni-red); font-size: 0.65rem;">ADMIN</span>' : ''}
                                </div>
                                <div class="text-secondary small d-flex align-items-center gap-1 font-monospace" style="font-size: 0.74rem;">
                                    <span>${escapeHtml(u.rut || 'RUT no reg.')}</span>
                                    <span>•</span>
                                    <a href="mailto:${escapeHtml(u.email)}" class="text-primary text-decoration-none text-truncate" style="max-width: 170px;" onclick="event.stopPropagation();" title="${escapeHtml(u.email)}">
                                        ${escapeHtml(u.email)}
                                    </a>
                                </div>
                            </div>
                        </div>
                    </td>
                    <td style="vertical-align: middle;">
                        <div class="fw-bold small" style="font-size: 0.85rem; color: var(--muni-navy);">
                            <i class="bi bi-geo-alt-fill text-danger me-1"></i>${escapeHtml(delegacionLimpia)}
                        </div>
                        ${cargoLimpio ? `<div class="text-muted small text-truncate" style="font-size: 0.75rem; max-width: 180px;">${escapeHtml(cargoLimpio)}</div>` : ''}
                    </td>
                    <td style="vertical-align: middle;">
                        <div class="d-flex flex-wrap gap-1">
                            ${rolesHtml}
                        </div>
                    </td>
                    <td class="text-center" style="vertical-align: middle;">${statusBadge}</td>
                    <td class="text-end" style="vertical-align: middle; padding-right: 1rem;">
                        <div class="d-flex align-items-center justify-content-end gap-1">
                            <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 py-1 fw-bold shadow-xs d-flex align-items-center gap-1" onclick="seleccionarUsuarioDetalle('${u.id}')" title="Ver ficha técnica del funcionario" style="font-size: 0.78rem;">
                                <i class="bi bi-person-vcard"></i> Ficha
                            </button>
                            <div class="dropdown d-inline-block">
                                <button class="btn btn-sm btn-light border rounded-circle shadow-xs" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;" title="Todas las acciones">
                                    <i class="bi bi-three-dots-vertical text-secondary"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end shadow-lg border p-2" style="min-width: 210px; font-size: 0.84rem; background: #FFFFFF !important; z-index: 1080;">
                                    <li>
                                        <a class="dropdown-item py-2 fw-semibold text-danger rounded-2 d-flex align-items-center gap-2" href="javascript:void(0)" onclick="seleccionarUsuarioDetalle('${u.id}')">
                                            <i class="bi bi-person-lines-fill text-danger"></i> Ver Ficha Completa
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item py-2 fw-semibold text-dark rounded-2 d-flex align-items-center gap-2" href="javascript:void(0)" onclick="abrirModalUsuario('editar', ${u.id})">
                                            <i class="bi bi-pencil-square text-warning"></i> Editar Funcionario
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item py-2 fw-semibold text-dark rounded-2 d-flex align-items-center gap-2" href="javascript:void(0)" onclick="abrirModalPassword(${u.id})">
                                            <i class="bi bi-key-fill text-info"></i> Resetear Contraseña
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item py-2 fw-semibold text-dark rounded-2 d-flex align-items-center gap-2" href="javascript:void(0)" onclick="exportarFichaUsuarioPDF(${u.id})">
                                            <i class="bi bi-file-earmark-pdf-fill text-danger"></i> Credencial PDF
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item py-2 fw-semibold text-${isActivo ? 'danger' : 'success'} rounded-2 d-flex align-items-center gap-2" href="javascript:void(0)" onclick="toggleEstadoUsuario(${u.id})">
                                            <i class="bi bi-power"></i> ${isActivo ? 'Desactivar Acceso' : 'Activar Acceso'}
                                        </a>
                                    </li>
                                    <li><hr class="dropdown-divider my-1"></li>
                                    <li>
                                        <a class="dropdown-item py-2 fw-semibold text-danger rounded-2 d-flex align-items-center gap-2" href="javascript:void(0)" onclick="eliminarUsuario(${u.id})">
                                            <i class="bi bi-trash3 text-danger"></i> Eliminar Funcionario
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            const total = filasFiltradasUsuarios.length;
            const lblInfo = document.getElementById('lblRegistrosInfoUsuarios');
            if (lblInfo) lblInfo.textContent = `Mostrando ${Math.min(fin, total)} de ${total} funcionarios`;
            actualizarIndicadorTablaUsuarios(inicio + 1, Math.min(fin, total), total);
            actualizarPaginadorUsuarios(total);
        }

        function actualizarIndicadorTablaUsuarios(desde, hasta, total) {
            const orden = document.getElementById('usuariosOrdenActual');
            const filas = document.getElementById('usuariosFilasActuales');
            const nombres = {full_name:'Nombre', delegation_name:'Delegación y cargo', status:'Estado'};
            if (orden) orden.textContent = `Orden: ${nombres[campoOrdenUsuarios] || 'Nombre'} · ${ordenAscUsuarios ? 'A–Z' : 'Z–A'}`;
            if (filas) filas.textContent = total ? `Filas ${desde}–${hasta} de ${total}` : '0 resultados';
        }

        function cerrarFichaUsuario() {
            const panel = document.getElementById('panelDetalleUsuario');
            if (panel) panel.style.display = 'none';
        }

        function seleccionarUsuarioDetalle(id) {
            const u = datasetUsuarios.find(x => String(x.id) === String(id));
            if (!u) {
                mostrarToast('⚠ No se encontró la información del funcionario seleccionado.');
                return;
            }

            const panel = document.getElementById('panelDetalleUsuario');
            if (!panel) return;

            const esAdmin = u.is_superuser || (u.roles || []).some(r => r.name.toLowerCase().includes('admin'));
            const initials = (u.full_name || 'U').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
            const avatarColor = esAdmin ? 'var(--muni-red)' : 'var(--muni-navy)';
            const isActivo = u.status === 'Activo';

            // Roles badges
            let rolesHtml = '';
            if (u.roles && u.roles.length > 0) {
                rolesHtml = u.roles.map(r => `
                    <span class="badge bg-white text-dark border px-3 py-2 rounded-pill shadow-xs me-1 mb-1 fw-bold" style="font-size: 0.82rem;">
                        <i class="bi bi-shield-check text-primary me-1"></i>${escapeHtml(r.name)}
                    </span>
                `).join(' ');
            } else {
                rolesHtml = '<span class="text-muted small">Sin rol asignado</span>';
            }

            panel.innerHTML = `
                <div class="usuario-detail-glass-card">
                    <!-- Barra de Navegación Rápida -->
                    <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3 pb-2 border-bottom">
                        <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 py-1 fw-bold shadow-xs d-flex align-items-center gap-2"
                            onclick="cerrarFichaUsuario()">
                            <i class="bi bi-x-lg"></i> Cerrar Ficha del Funcionario
                        </button>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill px-3 py-1 text-white fw-bold shadow-xs" style="background: ${isActivo ? 'var(--status-success)' : 'var(--muni-red)'}; font-size: 0.75rem;">
                                <i class="bi ${isActivo ? 'bi-check-circle-fill' : 'bi-x-circle-fill'} me-1"></i>${u.status}
                            </span>
                            <span class="badge bg-white text-secondary border px-3 py-1 rounded-pill small fw-bold shadow-xs">
                                Ficha de Funcionario #${u.id}
                            </span>
                        </div>
                    </div>

                    <div class="row g-4 align-items-center">
                        <div class="col-lg-7">
                            <div class="d-flex align-items-center gap-3">
                                <div style="width: 72px; height: 72px; border-radius: 20px; background: ${avatarColor}; color: #FFF; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 800; box-shadow: 0 8px 24px rgba(27,54,93,0.18); flex-shrink: 0;">
                                    ${escapeHtml(initials)}
                                </div>
                                <div>
                                    <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                                        <h3 class="m-0 fw-bold" style="color: var(--muni-navy); font-size: 1.55rem; letter-spacing: -0.2px;">
                                            ${escapeHtml(u.full_name)}
                                        </h3>
                                        ${esAdmin ? '<span class="badge rounded-pill px-2 py-1 text-white fw-bold" style="background: var(--muni-red); font-size: 0.70rem;">ADMINISTRADOR</span>' : ''}
                                    </div>
                                    <div class="text-secondary small font-monospace fw-semibold" style="font-size: 0.85rem;">
                                        RUT: ${escapeHtml(u.rut || 'Sin RUT')} • Usuario: @${escapeHtml(u.username)}
                                    </div>
                                </div>
                            </div>

                            <div class="row g-3 mt-3 pt-3 border-top text-dark" style="font-size: 0.88rem;">
                                <div class="col-sm-6">
                                    <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.70rem;">Correo Institucional</div>
                                    <a href="mailto:${escapeHtml(u.email)}" class="text-decoration-none text-primary fw-bold d-flex align-items-center gap-1 mt-1">
                                        <i class="bi bi-envelope-fill text-muted"></i> ${escapeHtml(u.email)}
                                    </a>
                                </div>
                                <div class="col-sm-6">
                                    <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.70rem;">Delegación Asignada</div>
                                    <div class="fw-bold mt-1" style="color: var(--muni-navy);">
                                        <i class="bi bi-geo-alt-fill text-danger me-1"></i> ${escapeHtml(u.delegation_name || 'Sin Sede Asignada')}
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.70rem;">Cargo Funcionario</div>
                                    <div class="fw-semibold mt-1 text-dark">
                                        <i class="bi bi-briefcase-fill text-secondary me-1"></i> ${escapeHtml(u.position_name || 'Personal Municipal')}
                                    </div>
                                </div>
                                <div class="col-sm-6">
                                    <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.70rem;">Último acceso registrado</div>
                                    <div class="fw-semibold mt-1 text-secondary font-monospace">
                                        <i class="bi bi-clock-history text-info me-1"></i> ${u.last_login ? escapeHtml(u.last_login) : 'Sin ingreso registrado'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="col-lg-5">
                            <div class="p-3 rounded-4 bg-white border shadow-xs mb-3">
                                <div class="text-muted small fw-bold text-uppercase mb-2" style="font-size: 0.72rem; letter-spacing: 0.04em;">
                                    Roles y Perfiles de Acceso
                                </div>
                                <div>
                                    ${rolesHtml}
                                </div>
                            </div>

                            <div class="d-flex align-items-center gap-2 flex-wrap">
                                <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 py-2 fw-bold shadow-xs" onclick="abrirModalPassword(${u.id})">
                                    <i class="bi bi-key-fill me-1"></i> Resetear Contraseña
                                </button>
                                <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 py-2 fw-bold shadow-xs" onclick="abrirModalUsuario('editar', ${u.id})">
                                    <i class="bi bi-pencil-square me-1"></i> Editar Datos
                                </button>
                                <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 py-2 fw-bold shadow-xs" onclick="toggleEstadoUsuario(${u.id})">
                                    <i class="bi bi-power me-1"></i> ${isActivo ? 'Desactivar Cuenta' : 'Activar Cuenta'}
                                </button>
                                <button class="btn-exportar-pdf-oficial" onclick="exportarFichaUsuarioPDF(${u.id})" style="font-size: 0.78rem; padding: 0.40rem 1rem;">
                                    <i class="bi bi-file-earmark-pdf-fill"></i> Credencial PDF
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            panel.style.display = 'block';
            setTimeout(() => {
                panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 60);

            mostrarToast(`✓ Ficha de ${u.full_name} desplegada correctamente.`);
        }

        function exportarFichaUsuarioPDF(id) {
            const u = datasetUsuarios.find(x => String(x.id) === String(id));
            if (!u || !window.jspdf) return;

            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();

            // Membrete Oficial
            doc.setFillColor(27, 54, 93);
            doc.rect(0, 0, 210, 24, 'F');
            doc.setFillColor(196, 18, 48);
            doc.rect(0, 24, 210, 2.5, 'F');

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13);
            doc.setTextColor(255, 255, 255);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA', 14, 11);
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            doc.text('Dirección de Gestión Territorial y Participación Ciudadana', 14, 18);

            doc.setTextColor(27, 54, 93);
            doc.setFontSize(15);
            doc.setFont('helvetica', 'bold');
            doc.text('CREDENCIAL Y EXPEDIENTE DE FUNCIONARIO MUNICIPAL', 14, 38);

            doc.setFontSize(10);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(71, 85, 105);
            doc.text(`Identificador de Cuenta: #${u.id} | Fecha de Emisión: ${new Date().toLocaleDateString('es-CL')}`, 14, 45);

            const tableBody = [
                ['Nombre Completo', u.full_name || 'N/A'],
                ['RUT Institucional', u.rut || 'N/A'],
                ['Nombre de Usuario', u.username || 'N/A'],
                ['Correo Electrónico', u.email || 'N/A'],
                ['Sede / Delegación', u.delegation_name || 'Sin Asignación'],
                ['Cargo Oficial', u.position_name || 'Personal Municipal'],
                ['Roles y Privilegios', (u.roles || []).map(r => r.name).join(', ') || 'Sin Rol'],
                ['Estado de Cuenta', u.status || 'Activo'],
                ['Último Acceso Registrado', u.last_login || 'N/A']
            ];

            doc.autoTable({
                head: [['Parámetro Institucional', 'Información Oficial']],
                body: tableBody,
                startY: 52,
                theme: 'grid',
                headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold' }
            });

            doc.save(`Credencial_Funcionario_${u.id}_${new Date().toISOString().slice(0, 10)}.pdf`);
            mostrarToast('✓ Credencial de funcionario descargada en PDF.');
        }

        function actualizarPaginadorUsuarios(total) {
            const totalPaginas = Math.ceil(total / filasPorPaginaUsuarios) || 1;
            const contenedor = document.getElementById('paginadorPillsUsuarios');
            if (!contenedor) return;
            contenedor.innerHTML = '';

            for (let i = 1; i <= totalPaginas; i++) {
                const btn = document.createElement('button');
                btn.className = `page-pill ${i === paginaActualUsuarios ? 'active' : ''}`;
                btn.textContent = i;
                btn.onclick = () => {
                    paginaActualUsuarios = i;
                    renderTablaUsuarios();
                };
                contenedor.appendChild(btn);
            }
        }

        function cambiarFilasPorPaginaUsuarios(cant) {
            filasPorPaginaUsuarios = Math.min(50, Math.max(10, parseInt(cant, 10) || 10));
            paginaActualUsuarios = 1;
            renderTablaUsuarios();
        }

        async function toggleEstadoUsuario(id, nombre) {
            try {
                const res = await fetch(`/api/users/${id}/toggle-status/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    }
                });
                const data = await res.json();
                if (!data.success) {
                    mostrarToast('⚠ ' + data.message);
                    return;
                }
                mostrarToast('✓ ' + data.message);
                cargarUsuariosDesdeDB(false);
            } catch (err) {
                console.error("Error toggle:", err);
                mostrarToast('⚠ Error al cambiar estado del usuario.');
            }
        }

        async function eliminarUsuario(id) {
            const u = datasetUsuarios.find(item => item.id === id);
            const nombre = u ? u.full_name : 'este funcionario';

            const result = await Swal.fire({
                title: '¿Eliminar Funcionario?',
                text: `¿Estás seguro de que deseas dar de baja a "${nombre}"? Esta acción desactivará su cuenta institucional.`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#B80003',
                cancelButtonColor: '#6c757d',
                confirmButtonText: '<i class="bi bi-trash3-fill me-1"></i> Sí, eliminar',
                cancelButtonText: 'Cancelar'
            });

            if (!result.isConfirmed) return;

            try {
                const res = await fetch(`/api/users/${id}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken') || '',
                        'Content-Type': 'application/json'
                    }
                });
                const data = await res.json();
                if (!data.success) {
                    Swal.fire({
                        title: 'No se pudo eliminar',
                        text: data.message || 'Error al eliminar usuario.',
                        icon: 'error',
                        confirmButtonColor: '#B80003'
                    });
                    return;
                }
                Swal.fire({
                    title: 'Usuario Eliminado',
                    text: data.message || 'El funcionario ha sido dado de baja exitosamente.',
                    icon: 'success',
                    confirmButtonColor: '#B80003'
                });
                cargarUsuariosDesdeDB(false);
            } catch (err) {
                console.error("Error al eliminar usuario:", err);
                Swal.fire({
                    title: 'Error de Servidor',
                    text: 'Ocurrió un error al procesar la solicitud de baja.',
                    icon: 'error',
                    confirmButtonColor: '#B80003'
                });
            }
        }

        let cargoPrevioEnModalUsuario = '';

        function normalizarNombreRolCargo(value) {
            return String(value || '').trim().toLocaleLowerCase('es-CL')
                .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        }

        function nombreRolBaseCargo(positionName) {
            const normalized = normalizarNombreRolCargo(positionName);
            if (!normalized) return '';
            return ['administrador general', 'superadministrador', 'super administrador'].includes(normalized)
                ? 'Administrador'
                : String(positionName).trim();
        }

        function buscarCheckboxRol(nombre) {
            const target = normalizarNombreRolCargo(nombre);
            const role = rolesCatalog.find(item => normalizarNombreRolCargo(item.name) === target);
            return role ? document.getElementById(`chkRole_${role.id}`) : null;
        }

        function sincronizarRolBaseCargo(cargoAnterior, cargoActual) {
            const anterior = nombreRolBaseCargo(cargoAnterior);
            const actual = nombreRolBaseCargo(cargoActual);
            if (anterior && normalizarNombreRolCargo(anterior) !== normalizarNombreRolCargo(actual)) {
                const previousCheckbox = buscarCheckboxRol(anterior);
                if (previousCheckbox) {
                    previousCheckbox.checked = false;
                    previousCheckbox.disabled = false;
                    previousCheckbox.title = '';
                }
            }
            if (actual) {
                const currentCheckbox = buscarCheckboxRol(actual);
                if (currentCheckbox) {
                    currentCheckbox.checked = true;
                    currentCheckbox.disabled = true;
                    currentCheckbox.title = 'Rol base asignado por el cargo';
                }
            }
        }

        function abrirModalUsuario(modo, id = null) {
            const elCont = document.getElementById('rolesCheckboxesContainer');
            elCont.innerHTML = '';

            // Renderizar Checkboxes de Roles desde catálogo DB
            rolesCatalog.forEach(r => {
                const div = document.createElement('div');
                div.className = 'form-check form-check-inline me-3 mb-1';
                div.innerHTML = `
                    <input class="form-check-input role-chk" type="checkbox" value="${r.id}" id="chkRole_${r.id}">
                    <label class="form-check-label small fw-semibold" for="chkRole_${r.id}">${r.name}</label>
                `;
                elCont.appendChild(div);
            });

            // Llenar Selects de Delegación y Cargo
            const selDel = document.getElementById('usrDelegation');
            selDel.innerHTML = '<option value="">Sin delegación específica</option>';
            delegationsCatalog.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = d.name;
                selDel.appendChild(opt);
            });

            const selPos = document.getElementById('usrPosition');
            selPos.innerHTML = '<option value="">Sin cargo específico</option>';
            positionsCatalog.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                selPos.appendChild(opt);
            });
            selPos.onchange = () => {
                const cargoActual = positionsCatalog.find(p => String(p.id) === selPos.value)?.name || '';
                sincronizarRolBaseCargo(cargoPrevioEnModalUsuario, cargoActual);
                cargoPrevioEnModalUsuario = cargoActual;
            };

            if (modo === 'nuevo') {
                cargoPrevioEnModalUsuario = '';
                document.getElementById('modalUsuarioTitle').textContent = 'Registrar Nuevo Funcionario';
                document.getElementById('usuarioEditId').value = '';
                document.getElementById('usrFullName').value = '';
                document.getElementById('usrRut').value = '';
                document.getElementById('usrUsername').value = '';
                document.getElementById('usrUsername').disabled = false;
                document.getElementById('usrEmail').value = '';
                document.getElementById('usrPassword').value = '';
                document.getElementById('usrStatus').value = 'Activo';
                document.getElementById('usrIsSuperuser').checked = false;
                document.getElementById('lblPasswordUsuario').innerHTML = 'Contraseña de Acceso <span class="text-danger">*</span>';
                document.getElementById('usrPassword').placeholder = 'Mínimo 8 caracteres';
                document.getElementById('helpPasswordUsuario').textContent = 'Obligatoria al crear. Usa 8+ caracteres, mayúscula, minúscula, número y símbolo.';
            } else {
                const u = datasetUsuarios.find(x => x.id === id);
                if (!u) return;
                document.getElementById('modalUsuarioTitle').textContent = 'Editar Funcionario: ' + u.full_name;
                document.getElementById('usuarioEditId').value = u.id;
                document.getElementById('usrFullName').value = u.full_name;
                document.getElementById('usrRut').value = u.rut;
                document.getElementById('usrUsername').value = u.username;
                document.getElementById('usrUsername').disabled = true; // El username no debe modificarse
                document.getElementById('usrEmail').value = u.email;
                document.getElementById('usrPassword').value = '';
                document.getElementById('usrStatus').value = u.status;
                document.getElementById('usrDelegation').value = u.delegation_id || '';
                document.getElementById('usrPosition').value = u.position_id || '';
                document.getElementById('usrIsSuperuser').checked = u.is_superuser || u.is_staff;
                document.getElementById('lblPasswordUsuario').innerHTML = 'Cambiar Contraseña (Opcional)';
                document.getElementById('usrPassword').placeholder = 'Nueva contraseña (opcional)';
                document.getElementById('helpPasswordUsuario').textContent = 'Déjala en blanco para conservar la clave actual; si la cambias, usa 8+ caracteres, mayúscula, minúscula, número y símbolo.';

                // Marcar roles que el usuario tiene
                if (u.roles && u.roles.length > 0) {
                    const uRoleIds = u.roles.map(r => r.id);
                    document.querySelectorAll('.role-chk').forEach(chk => {
                        chk.checked = uRoleIds.includes(parseInt(chk.value));
                    });
                }
                cargoPrevioEnModalUsuario = positionsCatalog.find(
                    p => String(p.id) === String(u.position_id || '')
                )?.name || '';
                sincronizarRolBaseCargo('', cargoPrevioEnModalUsuario);
            }

            if (!bsModalUsuario) {
                const el = document.getElementById('modalUsuario');
                if (el && window.bootstrap) bsModalUsuario = new bootstrap.Modal(el);
            }
            if (bsModalUsuario) bsModalUsuario.show();
        }

        async function guardarUsuarioDB() {
            const editId = document.getElementById('usuarioEditId').value;
            const fullName = document.getElementById('usrFullName').value.trim();
            const rut = document.getElementById('usrRut').value.trim();
            const username = document.getElementById('usrUsername').value.trim();
            const email = document.getElementById('usrEmail').value.trim();
            const password = document.getElementById('usrPassword').value;
            const status = document.getElementById('usrStatus').value;
            const delegationId = document.getElementById('usrDelegation').value || null;
            const positionId = document.getElementById('usrPosition').value || null;
            const isSuperuser = document.getElementById('usrIsSuperuser').checked;

            // Recoger roles seleccionados
            const roleIds = [];
            document.querySelectorAll('.role-chk:checked').forEach(chk => {
                roleIds.push(parseInt(chk.value));
            });

            if (!fullName || !rut || !username || !email) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Campos requeridos',
                    text: 'Nombre, RUT, usuario y correo son obligatorios y no pueden quedar en blanco.'
                });
                return;
            }

            if (!editId && !password) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Contraseña obligatoria',
                    text: 'Asigna una contraseña inicial segura para la nueva cuenta.'
                });
                return;
            }

            if (typeof validarRutChileno === 'function' && !validarRutChileno(rut)) {
                Swal.fire({
                    icon: 'error',
                    title: 'RUT inválido',
                    text: 'Revisa el número y el dígito verificador antes de continuar.'
                });
                return;
            }

            if (typeof validarEmail === 'function' && !validarEmail(email)) {
                Swal.fire({
                    icon: 'error',
                    title: 'Correo Inválido',
                    text: `El correo "${email}" no tiene un formato válido (debe contener @ y un dominio como .cl o .com).`
                });
                return;
            }

            const payload = {
                full_name: typeof sanitizarTexto === 'function' ? sanitizarTexto(fullName) : fullName,
                rut: typeof formatearRutChileno === 'function' ? formatearRutChileno(rut) : rut,
                username: username,
                email: email.trim().toLowerCase(),
                password: password,
                status: status,
                delegation_id: delegationId ? parseInt(delegationId) : null,
                position_id: positionId ? parseInt(positionId) : null,
                role_ids: roleIds,
                is_staff: isSuperuser,
                is_superuser: isSuperuser
            };

            const btn = document.getElementById('btnGuardarUsuarioDB');
            const spinner = document.getElementById('spinnerGuardarUsuario');
            const icon = document.getElementById('iconGuardarUsuario');
            btn.disabled = true;
            spinner.style.display = 'inline-block';
            icon.style.display = 'none';

            const url = editId ? `/api/users/${editId}/update/` : '/api/users/create/';

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (!data.success) {
                    Swal.fire({
                        icon: 'error',
                        title: 'No se pudo guardar el usuario',
                        text: data.message || 'Revisa los datos ingresados e inténtalo nuevamente.',
                        confirmButtonColor: '#A30F32'
                    });
                    btn.disabled = false;
                    spinner.style.display = 'none';
                    icon.style.display = 'inline-block';
                    return;
                }

                mostrarToast('✓ ' + data.message);
                if (bsModalUsuario) bsModalUsuario.hide();
                cargarUsuariosDesdeDB(false);
                Swal.fire({
                    icon: 'success',
                    title: 'Funcionario guardado',
                    text: data.message || 'El funcionario ha sido guardado exitosamente en la base de datos.',
                    confirmButtonColor: '#1B365D'
                });

            } catch (err) {
                console.error("Error guardando:", err);
                Swal.fire({
                    icon: 'error',
                    title: 'No hay conexión con el servidor',
                    text: 'No fue posible guardar el usuario. Comprueba la conexión e inténtalo otra vez.',
                    confirmButtonColor: '#A30F32'
                });
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
                icon.style.display = 'inline-block';
            }
        }

        function confirmarEliminarUsuario(id, nombre, rut) {
            usuarioAEliminarId = id;
            document.getElementById('delUsuarioNombre').textContent = nombre;
            document.getElementById('delUsuarioRut').textContent = rut;
            if (!bsModalEliminarUsuario) {
                const el = document.getElementById('modalEliminarUsuario');
                if (el && window.bootstrap) bsModalEliminarUsuario = new bootstrap.Modal(el);
            }
            if (bsModalEliminarUsuario) bsModalEliminarUsuario.show();
        }

        async function ejecutarEliminarUsuarioDB() {
            if (!usuarioAEliminarId) return;
            const btn = document.getElementById('btnConfirmarEliminarUsuario');
            const spinner = document.getElementById('spinnerEliminarUsuario');
            btn.disabled = true;
            spinner.style.display = 'inline-block';

            try {
                const res = await fetch(`/api/users/${usuarioAEliminarId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    }
                });
                const data = await res.json();

                if (!data.success) {
                    if (bsModalEliminarUsuario) bsModalEliminarUsuario.hide();
                    Swal.fire({
                        icon: 'error',
                        title: 'Acceso Denegado',
                        text: data.message || 'No se pudo eliminar el funcionario.',
                        confirmButtonColor: '#A30F32'
                    });
                    return;
                }

                if (bsModalEliminarUsuario) bsModalEliminarUsuario.hide();
                mostrarToast('✓ ' + data.message);
                cargarUsuariosDesdeDB(false);
                Swal.fire({
                    icon: 'success',
                    title: 'Funcionario Eliminado',
                    text: data.message || 'El funcionario ha sido eliminado exitosamente.',
                    confirmButtonColor: '#1B365D'
                });

            } catch (err) {
                console.error("Error eliminar:", err);
                if (bsModalEliminarUsuario) bsModalEliminarUsuario.hide();
                Swal.fire({
                    icon: 'error',
                    title: 'Error al eliminar',
                    text: 'No fue posible completar la eliminación en el servidor.',
                    confirmButtonColor: '#A30F32'
                });
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
                usuarioAEliminarId = null;
            }
        }

        function abrirModalPassword(id) {
            usuarioAPasswordId = id;
            const account = datasetUsuarios.find(user => user.id === id);
            document.getElementById('pwdUsuarioNombre').textContent = account?.full_name || 'Funcionario';
            const passwordInput = document.getElementById('pwdNuevaClave');
            const passwordError = document.getElementById('pwdErrorClave');
            passwordInput.value = '';
            if (passwordError) {
                passwordError.textContent = '';
                passwordError.hidden = true;
            }
            if (!bsModalPasswordUsuario) {
                const el = document.getElementById('modalPasswordUsuario');
                if (el && window.bootstrap) bsModalPasswordUsuario = new bootstrap.Modal(el);
            }
            if (bsModalPasswordUsuario) bsModalPasswordUsuario.show();
        }

        async function guardarPasswordDB() {
            if (!usuarioAPasswordId) return;
            const input = document.getElementById('pwdNuevaClave');
            const pwd = input.value;
            const feedback = document.getElementById('pwdErrorClave');
            const issues = [];
            if (pwd.length < 8) issues.push('al menos 8 caracteres');
            if (!/\p{Lu}/u.test(pwd)) issues.push('una mayúscula');
            if (!/\p{Ll}/u.test(pwd)) issues.push('una minúscula');
            if (!/\p{Nd}/u.test(pwd)) issues.push('un número');
            if (!/[^\p{L}\p{N}\s]/u.test(pwd)) issues.push('un símbolo');
            if (issues.length) {
                const message = `La contraseña debe incluir ${issues.join(', ')}.`;
                if (feedback) {
                    feedback.textContent = message;
                    feedback.hidden = false;
                } else mostrarToast('⚠ ' + message);
                input.focus();
                return;
            }
            if (feedback) { feedback.textContent = ''; feedback.hidden = true; }

            try {
                const res = await fetch(`/api/users/${usuarioAPasswordId}/reset-password/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify({ password: pwd })
                });
                const data = await res.json();
                if (!data.success) {
                    const details = Array.isArray(data.details) ? data.details.join(' ') : '';
                    const message = [data.message, details].filter(Boolean).join(' ');
                    if (feedback) {
                        feedback.textContent = message;
                        feedback.hidden = false;
                    } else mostrarToast('⚠ ' + message);
                    return;
                }
                let loginGuidance = 'Para entrar, debe usar el RUT o el correo registrado (el nombre de usuario no sirve como identificador de acceso).';
                if (data.account_status !== 'Activo' || !data.is_active) {
                    loginGuidance += ' La cuenta está inactiva: primero actívala desde Editar funcionario.';
                } else if (!data.has_active_role) {
                    loginGuidance += ' La cuenta no tiene un rol activo asignado; asígnale uno antes de intentar ingresar.';
                }
                if (window.Swal) {
                    await Swal.fire({icon:'success', title:'Contraseña actualizada', text:`${data.message} ${loginGuidance}`, confirmButtonColor:'#1B365D'});
                } else mostrarToast('✓ ' + data.message);
                input.value = '';
                if (bsModalPasswordUsuario) bsModalPasswordUsuario.hide();
            } catch (err) {
                console.error("Error password:", err);
                mostrarToast('⚠ Error al restablecer contraseña.');
            }
        }

        function togglePasswordVisibility(inputId, btn) {
            const input = document.getElementById(inputId);
            if (!input) return;
            const icon = btn.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                if (icon) {
                    icon.classList.remove('bi-eye');
                    icon.classList.add('bi-eye-slash');
                }
            } else {
                input.type = 'password';
                if (icon) {
                    icon.classList.remove('bi-eye-slash');
                    icon.classList.add('bi-eye');
                }
            }
        }

        function formatearRutInput(input) {
            let valor = input.value.replace(/[^0-9kK]/g, '');
            if (valor.length <= 1) return;
            const cuerpo = valor.slice(0, -1);
            const dv = valor.slice(-1).toUpperCase();
            let resultado = '';
            let contador = 0;
            for (let i = cuerpo.length - 1; i >= 0; i--) {
                resultado = cuerpo[i] + resultado;
                contador++;
                if (contador === 3 && i !== 0) {
                    resultado = '.' + resultado;
                    contador = 0;
                }
            }
            input.value = resultado + '-' + dv;
        }

        function exportarExcelUsuarios() {
            if (!window.XLSX) {
                Swal.fire('La librería XLSX está cargando, intente nuevamente en unos segundos.');
                return;
            }
            const dataToExport = filasFiltradasUsuarios.map(u => ({
                'ID': u.id,
                'Funcionario': u.full_name,
                'Usuario': u.username,
                'RUT': u.rut,
                'Correo Institucional': u.email,
                'Delegación': u.delegation_name,
                'Cargo': u.position_name,
                'Roles': u.roles_str,
                'Estado': u.status,
                'Es Administrador': u.is_superuser ? 'SÍ' : 'NO',
                'Fecha Registro': u.created_at
            }));

            const ws = XLSX.utils.json_to_sheet(dataToExport);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Usuarios SGR');
            XLSX.writeFile(wb, 'Usuarios_SGR_Municipalidad_La_Serena.xlsx');
            mostrarToast('✓ Archivo Excel generado y descargado con éxito.');
        }

        function exportarPDFUsuarios() {
            if (!window.jspdf) {
                Swal.fire('La librería PDF está cargando.');
                return;
            }
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF('landscape');

            doc.setFillColor(27, 54, 93);
            doc.rect(0, 0, 297, 24, 'F');
            doc.setFillColor(196, 18, 48);
            doc.rect(0, 24, 297, 2.5, 'F');

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(14);
            doc.setTextColor(255, 255, 255);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA', 14, 12);
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            doc.text('Sistema Municipal de Gestión de Atención Ciudadana (SGR) — Catastro Institucional de Usuarios', 14, 18);

            const hoy = new Date().toLocaleDateString('es-CL');
            doc.text(`Fecha de Emisión: ${hoy}`, 280, 18, { align: 'right' });

            const rows = filasFiltradasUsuarios.map((u, i) => [
                i + 1,
                u.full_name,
                u.rut,
                u.email,
                u.delegation_name,
                u.position_name,
                u.roles_str,
                u.status
            ]);

            doc.autoTable({
                head: [['#', 'Funcionario', 'RUT', 'Correo', 'Delegación', 'Cargo', 'Roles', 'Estado']],
                body: rows,
                startY: 32,
                theme: 'striped',
                headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold' },
                styles: { fontSize: 8, cellPadding: 2.5 },
                columnStyles: {
                    0: { cellWidth: 10 },
                    1: { cellWidth: 45 },
                    2: { cellWidth: 26 },
                    3: { cellWidth: 45 },
                    4: { cellWidth: 38 },
                    5: { cellWidth: 35 },
                    6: { cellWidth: 50 },
                    7: { cellWidth: 22 }
                }
            });

            doc.save('Nomina_Usuarios_SGR_La_Serena.pdf');
            mostrarToast('✓ Nómina de usuarios en PDF generada con éxito.');
        }

        /* ==========================================================================
           CATÁLOGOS DE ORGANIZACIÓN (DELEGACIONES Y CARGOS EN BASE DE DATOS)
           ========================================================================== */

        let catalogoDelegacionesDB = [];
        let catalogoCargosDB = [];
        let catalogosOrganizacionInicializados = false;
        let formularioOrganizacionCerradoInicializado = false;
        let paginaActualCargos = 1;
        let filasPorPaginaCargos = 10;
        let controlesPaginacionCargosInicializados = false;

        function escaparHtmlCatalogo(valor) {
            const div = document.createElement('div');
            div.textContent = valor == null ? '' : String(valor);
            return div.innerHTML;
        }

        async function cargarCatalogosOrganizacion() {
            const [resDelegaciones, resCargos] = await Promise.all([
                fetch('/organization/delegations/'),
                fetch('/organization/positions/')
            ]);
            const [delegaciones, cargos] = await Promise.all([resDelegaciones.json(), resCargos.json()]);
            if (!resDelegaciones.ok || !delegaciones.success) throw new Error(delegaciones.message || 'No fue posible cargar las delegaciones.');
            if (!resCargos.ok || !cargos.success) throw new Error(cargos.message || 'No fue posible cargar los cargos.');
            catalogoDelegacionesDB = delegaciones.delegations || [];
            catalogoCargosDB = cargos.positions || [];
            sincronizarDelegacionesVisualesDesdeDB();
            actualizarKpisDelegacionesReales();
            renderCatalogosOrganizacion();
            renderCargosMantenedor();
            if (document.getElementById('delegacionesCardsGrid')) renderizarDelegacionesCards(filtroZonaActivo);
        }

        function actualizarKpisDelegacionesReales() {
            const active = catalogoDelegacionesDB.filter(item => item.status === 'Activo');
            const measured = active.filter(item => item.compliance_percentage != null);
            const average = measured.length ? measured.reduce((sum, item) => sum + Number(item.compliance_percentage), 0) / measured.length : null;
            const neighbors = active.reduce((sum, item) => sum + Number(item.registered_neighbors || 0), 0);
            const staff = active.reduce((sum, item) => sum + Number(item.users_count || 0), 0);
            const setText = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
            setText('kpiDelegacionesActivas', `${active.length} de ${catalogoDelegacionesDB.length}`);
            setText('kpiDelegacionesEstado', active.length === catalogoDelegacionesDB.length ? '100% Operativas' : `${catalogoDelegacionesDB.length - active.length} sede(s) inactiva(s)`);
            setText('kpiDelegacionesCumplimiento', average == null ? 'Sin medición' : `${average.toFixed(1)}%`);
            setText('kpiDelegacionesVecinos', neighbors.toLocaleString('es-CL'));
            setText('kpiDelegacionesFuncionarios', `${staff} Funcionario${staff === 1 ? '' : 's'}`);
            setText('kpiDelegacionesFuncionariosDetalle', `Distribuidos en ${active.length} sede${active.length === 1 ? '' : 's'} activa${active.length === 1 ? '' : 's'}`);
        }

        function tarjetaCatalogo(item, tipo) {
            const activo = item.status === 'Activo';
            const detalle = tipo === 'delegacion' ? item.scope : (item.description || 'Sin descripción registrada');
            const editar = tipo === 'delegacion' ? `editarDelegacionCatalogo(${item.id})` : `editarCargoCatalogo(${item.id})`;
            const alternar = tipo === 'delegacion' ? `alternarDelegacionCatalogo(${item.id})` : `alternarCargoCatalogo(${item.id})`;
            const borrarBtn = tipo === 'cargo' ? `<button class="btn btn-outline-danger" type="button" onclick="eliminarCargoCatalogo(${item.id})" title="Eliminar cargo"><i class="bi bi-trash3"></i></button>` : `<button class="btn btn-outline-danger" type="button" onclick="eliminarDelegacionCatalogo(${item.id})" title="Eliminar delegación"><i class="bi bi-trash3"></i></button>`;
            return `<div class="col-md-6" style="min-width:0"><article class="bg-white border rounded-4 p-3 shadow-sm h-100 overflow-hidden" style="min-width:0">
                <div class="d-flex justify-content-between gap-2" style="min-width:0"><div class="flex-grow-1" style="min-width:0"><div class="fw-bold text-dark text-truncate">${escaparHtmlCatalogo(item.name)}</div><div class="small text-muted text-truncate">${tipo === 'delegacion' ? escaparHtmlCatalogo(item.code || '') + ' · ' : ''}${escaparHtmlCatalogo(detalle)}</div></div><span class="badge ${activo ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'} align-self-start flex-shrink-0">${item.status}</span></div>
                <div class="d-flex justify-content-between align-items-center mt-2"><small class="text-muted"><i class="bi bi-people me-1"></i>${item.users_count} usuario(s)</small><div class="btn-group btn-group-sm"><button class="btn btn-outline-muni-red" type="button" onclick="${editar}" title="Editar"><i class="bi bi-pencil"></i></button><button class="btn btn-outline-muni-red" type="button" onclick="${alternar}" title="${activo ? 'Desactivar' : 'Activar'}"><i class="bi bi-${activo ? 'pause-circle' : 'play-circle'}"></i></button>${borrarBtn}</div></div>
            </article></div>`;
        }

        function renderCatalogosOrganizacion() {
            const delegaciones = document.getElementById('listaCatalogoDelegaciones');
            const cargos = document.getElementById('listaCatalogoCargos');
            if (delegaciones) delegaciones.innerHTML = catalogoDelegacionesDB.map(i => tarjetaCatalogo(i, 'delegacion')).join('') || '<p class="text-muted">No hay delegaciones registradas.</p>';
            if (cargos) cargos.innerHTML = catalogoCargosDB.map(i => tarjetaCatalogo(i, 'cargo')).join('') || '<p class="text-muted">No hay cargos registrados.</p>';
        }

        async function initCargosView() {
            if (!controlesPaginacionCargosInicializados) {
                const pageSize = document.getElementById('tamanoPaginaCargos');
                const previous = document.getElementById('paginaAnteriorCargos');
                const next = document.getElementById('paginaSiguienteCargos');
                pageSize?.addEventListener('change', () => {
                    filasPorPaginaCargos = Math.min(50, Math.max(10, Number(pageSize.value) || 10));
                    paginaActualCargos = 1;
                    renderCargosMantenedor();
                });
                previous?.addEventListener('click', () => { paginaActualCargos = Math.max(1, paginaActualCargos - 1); renderCargosMantenedor(); });
                next?.addEventListener('click', () => { paginaActualCargos += 1; renderCargosMantenedor(); });
                controlesPaginacionCargosInicializados = true;
            }
            try { await cargarCatalogosOrganizacion(); }
            catch (error) { Swal.fire('No fue posible cargar los cargos', error.message, 'error'); }
        }

        function renderCargosMantenedor() {
            const container = document.getElementById('listaCargosMantenedor');
            if (!container) return;
            const active = catalogoCargosDB.filter(item => item.status === 'Activo');
            const assignments = catalogoCargosDB.reduce((sum, item) => sum + Number(item.users_count || 0), 0);
            const setText = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
            setText('kpiCargosTotal', catalogoCargosDB.length);
            setText('kpiCargosActivos', active.length);
            setText('kpiCargosAsignaciones', assignments);
            const pages = Math.max(1, Math.ceil(catalogoCargosDB.length / filasPorPaginaCargos));
            paginaActualCargos = Math.min(paginaActualCargos, pages);
            const start = catalogoCargosDB.length ? (paginaActualCargos - 1) * filasPorPaginaCargos + 1 : 0;
            const end = Math.min(catalogoCargosDB.length, paginaActualCargos * filasPorPaginaCargos);
            setText('paginacionInfoCargos', `Mostrando ${start}-${end} de ${catalogoCargosDB.length} · Página ${paginaActualCargos} de ${pages}`);
            const previous = document.getElementById('paginaAnteriorCargos');
            const next = document.getElementById('paginaSiguienteCargos');
            if (previous) previous.disabled = paginaActualCargos <= 1;
            if (next) next.disabled = paginaActualCargos >= pages;
            container.innerHTML = catalogoCargosDB.slice(start ? start - 1 : 0, end).map(item => {
                const activo = item.status === 'Activo';
                return `<div class="col-md-6 col-xl-4"><article class="bg-white border rounded-4 p-3 shadow-sm h-100 overflow-hidden">
                    <div class="d-flex justify-content-between gap-3 align-items-start"><div style="min-width:0"><h5 class="fw-bold mb-1 text-truncate" style="color:var(--muni-navy)">${escaparHtmlCatalogo(item.name)}</h5><p class="small text-muted mb-0">${escaparHtmlCatalogo(item.description || 'Sin descripción registrada')}</p></div><span class="badge ${activo ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'}">${item.status}</span></div>
                    <div class="d-flex justify-content-between align-items-center mt-3 pt-2 border-top"><small class="text-muted"><i class="bi bi-people-fill me-1"></i>${item.users_count} funcionario(s)</small><div class="btn-group btn-group-sm"><button class="btn btn-outline-muni-red" onclick="editarCargoDesdeVista(${item.id})"><i class="bi bi-pencil me-1"></i>Editar</button><button class="btn btn-outline-muni-red" onclick="alternarCargoCatalogo(${item.id})" title="${activo ? 'Inactivar' : 'Activar'}"><i class="bi bi-${activo ? 'pause-circle' : 'play-circle'}"></i></button><button class="btn btn-outline-muni-red text-danger" onclick="eliminarCargoCatalogo(${item.id})" title="Eliminar cargo"><i class="bi bi-trash3"></i></button></div></div>
                </article></div>`;
            }).join('') || '<div class="col-12 text-center text-muted py-4">No hay cargos registrados.</div>';
        }

        async function editarCargoDesdeVista(id) {
            await abrirCatalogosOrganizacion('cargos');
            editarCargoCatalogo(id);
        }

        async function abrirCatalogosOrganizacion(pestaña = 'delegaciones') {
            const modalEl = document.getElementById('modalCatalogosOrganizacion');
            if (!modalEl) return;
            if (!catalogosOrganizacionInicializados) {
                document.getElementById('formCatalogoDelegacion')?.addEventListener('submit', guardarDelegacionCatalogo);
                document.getElementById('formCatalogoCargo')?.addEventListener('submit', guardarCargoCatalogo);
                catalogosOrganizacionInicializados = true;
            }
            if (!formularioOrganizacionCerradoInicializado) {
                modalEl.addEventListener('hidden.bs.modal', () => {
                    limpiarFormDelegacion();
                    limpiarFormCargo();
                });
                formularioOrganizacionCerradoInicializado = true;
            }
            try {
                limpiarFormDelegacion();
                limpiarFormCargo();
                await cargarCatalogosOrganizacion();
                const esCargos = pestaña === 'cargos';
                const panelDelegaciones = document.getElementById('panelCatalogoDelegaciones');
                const panelCargos = document.getElementById('panelCatalogoCargos');
                panelDelegaciones?.classList.toggle('show', !esCargos);
                panelDelegaciones?.classList.toggle('active', !esCargos);
                panelCargos?.classList.toggle('show', esCargos);
                panelCargos?.classList.toggle('active', esCargos);
                const title = document.getElementById('tituloCatalogoOrganizacion');
                const subtitle = document.getElementById('subtituloCatalogoOrganizacion');
                if (title) title.innerHTML = esCargos
                    ? '<i class="bi bi-person-workspace me-2 text-warning"></i>Gestión de cargos'
                    : '<i class="bi bi-buildings-fill me-2 text-warning"></i>Delegaciones municipales';
                if (subtitle) subtitle.textContent = esCargos
                    ? 'Cargos institucionales disponibles para la asignación de funcionarios.'
                    : 'Sedes, cobertura y datos de contacto guardados en la base de datos.';
                const delegationList = document.getElementById('delegacionesListaDetalles');
                if (delegationList) delegationList.open = window.innerWidth >= 992;
                bootstrap.Modal.getOrCreateInstance(modalEl).show();
            } catch (error) {
                Swal.fire('No fue posible abrir el catálogo', error.message, 'error');
            }
        }

        function limpiarFormDelegacion() {
            const form = document.getElementById('formCatalogoDelegacion');
            form?.reset();
            form?.querySelectorAll('input, textarea, select').forEach(field => field.setCustomValidity(''));
            document.getElementById('catalogoDelegacionId').value = '';
            document.getElementById('tituloFormDelegacion').textContent = 'Nueva delegación';
        }

        function limpiarFormCargo() {
            document.getElementById('formCatalogoCargo')?.reset();
            document.getElementById('catalogoCargoId').value = '';
            document.getElementById('tituloFormCargo').textContent = 'Nuevo cargo';
        }

        function editarDelegacionCatalogo(id) {
            const item = catalogoDelegacionesDB.find(i => i.id === id); if (!item) return;
            const extras = document.getElementById('delegacionExtraFields');
            if (extras) extras.open = true;
            document.getElementById('catalogoDelegacionId').value = item.id;
            document.getElementById('catalogoDelegacionNombre').value = item.name;
            document.getElementById('catalogoDelegacionCodigo').value = item.code || '';
            document.getElementById('catalogoDelegacionComuna').value = item.commune || 'La Serena';
            document.getElementById('catalogoDelegacionAmbito').value = item.scope;
            document.getElementById('catalogoDelegacionEstado').value = item.status;
            document.getElementById('catalogoDelegacionDireccion').value = item.address || '';
            document.getElementById('catalogoDelegacionTelefono').value = item.phone || '';
            document.getElementById('catalogoDelegacionCorreo').value = item.email || '';
            document.getElementById('catalogoDelegacionHorario').value = item.schedule || '';
            document.getElementById('catalogoDelegacionEncargado').value = item.manager_name || '';
            document.getElementById('catalogoDelegacionFoto').value = item.photo_url || '';
            document.getElementById('catalogoDelegacionDescripcion').value = item.description || '';
            document.getElementById('tituloFormDelegacion').textContent = 'Editar delegación';
        }

        function editarCargoCatalogo(id) {
            const item = catalogoCargosDB.find(i => i.id === id); if (!item) return;
            document.getElementById('catalogoCargoId').value = item.id;
            document.getElementById('catalogoCargoNombre').value = item.name;
            document.getElementById('catalogoCargoDescripcion').value = item.description || '';
            document.getElementById('catalogoCargoEstado').value = item.status;
            document.getElementById('tituloFormCargo').textContent = 'Editar cargo';
        }

        async function enviarCatalogo(url, payload) {
            const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''}, body: JSON.stringify(payload)});
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.message || 'No fue posible guardar el cambio.');
            await cargarCatalogosOrganizacion();
            await cargarUsuariosDesdeDB(false);
            mostrarToast(`✓ ${data.message}`);
        }

        async function guardarDelegacionCatalogo(event) {
            event.preventDefault();
            const form = document.getElementById('formCatalogoDelegacion');
            ['catalogoDelegacionNombre', 'catalogoDelegacionAmbito', 'catalogoDelegacionComuna'].forEach(id => {
                const field = document.getElementById(id);
                field.setCustomValidity(field.value.trim() ? '' : 'Este campo es obligatorio y no puede contener solo espacios.');
            });
            const photo = document.getElementById('catalogoDelegacionFoto');
            const photoValue = photo.value.trim();
            photo.setCustomValidity(!photoValue || /^(?:\/static\/(?!.*\.\.)[A-Za-z0-9_./-]+|https?:\/\/[^\s"'<>]+)$/i.test(photoValue)
                ? '' : 'Usa una ruta /static/ segura o una dirección URL http(s).');
            if (!form.reportValidity()) return;
            const id = document.getElementById('catalogoDelegacionId').value;
            try {
                await enviarCatalogo(id ? `/organization/delegations/${id}/update/` : '/organization/delegations/', {
                    name: document.getElementById('catalogoDelegacionNombre').value.trim(),
                    code: document.getElementById('catalogoDelegacionCodigo').value.trim(),
                    commune: document.getElementById('catalogoDelegacionComuna').value.trim(),
                    scope: document.getElementById('catalogoDelegacionAmbito').value.trim(),
                    status: document.getElementById('catalogoDelegacionEstado').value,
                    address: document.getElementById('catalogoDelegacionDireccion').value.trim(),
                    phone: document.getElementById('catalogoDelegacionTelefono').value.trim(),
                    email: document.getElementById('catalogoDelegacionCorreo').value.trim(),
                    schedule: document.getElementById('catalogoDelegacionHorario').value.trim(),
                    manager_name: document.getElementById('catalogoDelegacionEncargado').value.trim(),
                    photo_url: document.getElementById('catalogoDelegacionFoto').value.trim(),
                    description: document.getElementById('catalogoDelegacionDescripcion').value.trim()
                });
                limpiarFormDelegacion();
            } catch (error) { Swal.fire('No se pudo guardar', error.message, 'error'); }
        }

        async function guardarCargoCatalogo(event) {
            event.preventDefault();
            const id = document.getElementById('catalogoCargoId').value;
            if (!document.getElementById('catalogoCargoNombre').value.trim()) {
                Swal.fire({icon: 'warning', title: 'Nombre requerido', text: 'Indica el nombre del cargo antes de guardar.'});
                return;
            }
            try {
                await enviarCatalogo(id ? `/organization/positions/${id}/update/` : '/organization/positions/', {name: document.getElementById('catalogoCargoNombre').value.trim(), description: document.getElementById('catalogoCargoDescripcion').value.trim(), status: document.getElementById('catalogoCargoEstado').value});
                limpiarFormCargo();
            } catch (error) { Swal.fire('No se pudo guardar', error.message, 'error'); }
        }

        async function alternarDelegacionCatalogo(id) {
            try { await enviarCatalogo(`/organization/delegations/${id}/toggle-status/`, {}); } catch (error) { Swal.fire('No se pudo cambiar el estado', error.message, 'error'); }
        }

        async function alternarCargoCatalogo(id) {
            try { await enviarCatalogo(`/organization/positions/${id}/toggle-status/`, {}); } catch (error) { Swal.fire('No se pudo cambiar el estado', error.message, 'error'); }
        }

        async function eliminarCargoCatalogo(id) {
            const item = catalogoCargosDB.find(i => i.id === id);
            const nombre = item ? item.name : 'este cargo';
            if (item && item.users_count > 0) {
                Swal.fire({
                    icon: 'warning',
                    title: 'No se puede eliminar el cargo',
                    text: `El cargo "${nombre}" tiene ${item.users_count} funcionario(s) asignado(s). Para eliminarlo, primero debes reasignar a esos funcionarios en el mantenedor de Usuarios.`,
                    confirmButtonColor: '#B80003'
                });
                return;
            }
            const result = await Swal.fire({
                title: '¿Eliminar cargo institucional?',
                text: `¿Estás seguro de que deseas eliminar permanentemente el cargo "${nombre}"?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#B80003',
                cancelButtonColor: '#6c757d',
                confirmButtonText: '<i class="bi bi-trash3-fill me-1"></i> Sí, eliminar',
                cancelButtonText: 'Cancelar'
            });
            if (!result.isConfirmed) return;
            try {
                await enviarCatalogo(`/organization/positions/${id}/delete/`, {});
            } catch (error) {
                Swal.fire('No se pudo eliminar el cargo', error.message, 'error');
            }
        }

        async function eliminarDelegacionCatalogo(id) {
            const item = catalogoDelegacionesDB.find(row => Number(row.id) === Number(id));
            if (!item) return;
            if (item.users_count > 0) {
                Swal.fire({icon:'warning', title:'No se puede eliminar la delegación', text:'Reasigna los funcionarios antes de eliminarla.'});
                return;
            }
            const result = await Swal.fire({
                title: '¿Eliminar delegación?',
                text: `La delegación "${item.name}" se eliminará si no tiene atenciones, casos ni compromisos vinculados.`,
                icon: 'warning', showCancelButton: true, confirmButtonText: 'Eliminar', cancelButtonText: 'Cancelar',
                confirmButtonColor: '#B80003'
            });
            if (!result.isConfirmed) return;
            try { await enviarCatalogo(`/organization/delegations/${id}/delete/`, {}); }
            catch (error) { Swal.fire('No se pudo eliminar la delegación', error.message, 'error'); }
        }

        /* ==========================================================================
           MÓDULO: DELEGACIONES MUNICIPALES (IDENTIDAD TERRITORIAL POR COLOR Y SIGLAS)
           ========================================================================== */

        const datasetDelegacionesDetalle = {
            centro: {
                id: 'centro', nombre: 'Delegación Centro Histórico', sector: 'Zona urbana central',
                foto: '/static/img/delegacion_centro.jpg', direccion: 'Dirección no registrada',
                telefono: 'No registrado', email: '', horario: 'Horario no registrado', delegado: 'No asignado',
                cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                barrios: [], resumen: 'Área de referencia cartográfica. Información operativa pendiente de registros verificados.',
                funcionarios: [], metricasAtencion: []
            },
            companias: {
                id: 'companias', nombre: 'Delegación Las Compañías', sector: 'Sector norte',
                foto: '/static/img/delegacion_companias.jpg', direccion: 'Dirección no registrada',
                telefono: 'No registrado', email: '', horario: 'Horario no registrado', delegado: 'No asignado',
                cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                barrios: [], resumen: 'Área de referencia cartográfica. Información operativa pendiente de registros verificados.',
                funcionarios: [], metricasAtencion: []
            },
            pampa: {
                id: 'pampa', nombre: 'Delegación La Pampa', sector: 'Sector sur',
                foto: '/static/img/delegacion_pampa.jpg', direccion: 'Dirección no registrada',
                telefono: 'No registrado', email: '', horario: 'Horario no registrado', delegado: 'No asignado',
                cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                barrios: [], resumen: 'Área de referencia cartográfica. Información operativa pendiente de registros verificados.',
                funcionarios: [], metricasAtencion: []
            },
            costa: {
                id: 'costa', nombre: 'Delegación Avenida del Mar', sector: 'Borde costero',
                foto: '/static/img/delegacion_costa.jpg', direccion: 'Dirección no registrada',
                telefono: 'No registrado', email: '', horario: 'Horario no registrado', delegado: 'No asignado',
                cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                barrios: [], resumen: 'Área de referencia cartográfica. Información operativa pendiente de registros verificados.',
                funcionarios: [], metricasAtencion: []
            },
            antena: {
                id: 'antena', nombre: 'Delegación La Antena', sector: 'Sector oriente',
                foto: '/static/img/delegacion_antena.jpg', direccion: 'Dirección no registrada',
                telefono: 'No registrado', email: '', horario: 'Horario no registrado', delegado: 'No asignado',
                cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                barrios: [], resumen: 'Área de referencia cartográfica. Información operativa pendiente de registros verificados.',
                funcionarios: [], metricasAtencion: []
            },
            rural: {
                id: 'rural', nombre: 'Delegación Sector Rural', sector: 'Localidades rurales',
                foto: '/static/img/delegacion_rural.jpg', direccion: 'Dirección no registrada',
                telefono: 'No registrado', email: '', horario: 'Horario no registrado', delegado: 'No asignado',
                cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                barrios: [], resumen: 'Área de referencia cartográfica. Información operativa pendiente de registros verificados.',
                funcionarios: [], metricasAtencion: []
            }
        };

        function claveVisualDelegacion(item) {
            const texto = `${item.name} ${item.scope}`.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
            if (texto.includes('compania')) return 'companias';
            if (texto.includes('centro')) return 'centro';
            if (texto.includes('pampa')) return 'pampa';
            if (texto.includes('avenida del mar') || texto.includes('borde costero') || texto.includes('costa')) return 'costa';
            if (texto.includes('antena')) return 'antena';
            if (texto.includes('rural')) return 'rural';
            return `db-${item.id}`;
        }

        const identidadVisualDelegacion = {
            centro: { color: '#C41230', sigla: 'CH', numero: '01' },
            companias: { color: '#6554C0', sigla: 'LC', numero: '02' },
            pampa: { color: '#008F8C', sigla: 'LP', numero: '03' },
            antena: { color: '#B86A08', sigla: 'LA', numero: '04' },
            costa: { color: '#1677A8', sigla: 'AM', numero: '05' },
            rural: { color: '#678341', sigla: 'SR', numero: '06' }
        };

        function sincronizarDelegacionesVisualesDesdeDB() {
            if (typeof datasetDelegacionesDetalle === 'undefined') return;
            Object.values(datasetDelegacionesDetalle).forEach(item => {
                item.dbId = null;
                item.dbStatus = 'Inactivo';
            });
            catalogoDelegacionesDB.forEach(item => {
                const key = claveVisualDelegacion(item);
                const base = datasetDelegacionesDetalle[key] || {
                    id: key, nombre: item.name, sector: item.scope,
                    direccion: 'Dirección no registrada',
                    telefono: 'No registrado', email: 'No registrado', horario: 'Horario no registrado',
                    delegado: 'Encargado por asignar', cargoDelegado: 'Delegado Municipal',
                    cumplimiento: null, statusSemaforo: 'Sin medición', colorSemaforo: '#64748B',
                    atencionesMes: null, vecinosRegistrados: null, tuboResueltos: 'Sin datos', satisfaccion: 'Sin medición',
                    barrios: [], resumen: 'Sin descripción territorial registrada.', funcionarios: [], metricasAtencion: []
                };
                Object.assign(base, {
                    dbId: item.id, dbStatus: item.status, nombre: item.name, sector: item.scope,
                    codigo: item.code || '', comuna: item.commune || 'La Serena',
                    direccion: item.address || 'Dirección no registrada', telefono: item.phone || 'No registrado',
                    email: item.email || 'No registrado', horario: item.schedule || 'Horario no registrado',
                    delegado: item.manager_name || 'Encargado por asignar',
                    ...identidadVisualDelegacion[key],
                    resumen: item.description || base.resumen || 'Sin descripción territorial registrada.',
                    atencionesMes: item.monthly_activities,
                    vecinosRegistrados: item.registered_neighbors == null ? null : String(item.registered_neighbors),
                    tuboResueltos: item.resolution_rate == null ? 'Sin datos' : `${item.resolution_rate}%`,
                    cumplimiento: item.compliance_percentage,
                    satisfaccion: item.satisfaction_percentage == null ? 'Sin medición' : `${item.satisfaction_percentage}%`,
                    funcionariosDB: item.users_count,
                    funcionarios: (item.staff || []).map(person => ({
                        nombre: person.name, cargo: person.position,
                        rol: person.role,
                        avatar: person.name.split(/\s+/).slice(0, 2).map(part => part[0] || '').join('').toUpperCase()
                    }))
                });
                if (item.compliance_percentage == null) {
                    base.statusSemaforo = 'Sin medición vigente'; base.colorSemaforo = '#64748B';
                } else if (item.compliance_percentage >= 85) {
                    base.statusSemaforo = 'Verde (Conforme)'; base.colorSemaforo = '#10B981';
                } else if (item.compliance_percentage >= 60) {
                    base.statusSemaforo = 'Ámbar (Atención)'; base.colorSemaforo = '#F59E0B';
                } else {
                    base.statusSemaforo = 'Rojo (Crítico)'; base.colorSemaforo = '#EF4444';
                }
                datasetDelegacionesDetalle[key] = base;
            });
        }

        let delegacionSeleccionadaActiva = null;
        let filtroZonaActivo = 'todas';
        let filtroEstadoDelegacion = '';
        let busquedaDelegacion = '';
        let paginaActualDelegaciones = 1;
        let filasPorPaginaDelegaciones = 10;
        let vistaDelegacionesActiva = 'cards';

        function normalizarBusquedaDelegacion(value) {
            return String(value || '').trim().toLocaleLowerCase('es-CL').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        }

        function delegacionCoincideConSector(item) {
            if (filtroZonaActivo === 'todas') return true;
            const key = claveVisualDelegacion(item);
            if (filtroZonaActivo === 'urbano') return ['centro', 'companias', 'pampa', 'antena'].includes(key);
            if (filtroZonaActivo === 'costa') return key === 'costa';
            if (filtroZonaActivo === 'rural') return key === 'rural';
            return false;
        }

        function delegacionesFiltradas() {
            const query = normalizarBusquedaDelegacion(busquedaDelegacion);
            return Object.values(datasetDelegacionesDetalle).filter(item => {
                if (item.dbId == null) return false;
                if (filtroEstadoDelegacion && item.dbStatus !== filtroEstadoDelegacion) return false;
                if (!delegacionCoincideConSector({ name: item.nombre, scope: item.sector })) return false;
                const searchable = normalizarBusquedaDelegacion([
                    item.codigo, item.nombre, item.comuna, item.sector, item.direccion, item.email, item.telefono, item.delegado, item.dbStatus
                ].join(' '));
                return !query || searchable.includes(query);
            });
        }

        function actualizarPaginacionDelegaciones(total, pages) {
            const start = total ? (paginaActualDelegaciones - 1) * filasPorPaginaDelegaciones + 1 : 0;
            const end = Math.min(total, paginaActualDelegaciones * filasPorPaginaDelegaciones);
            const summary = document.getElementById('resumenDelegaciones');
            const pageInfo = document.getElementById('paginacionInfoDelegaciones');
            const previous = document.getElementById('paginaAnteriorDelegaciones');
            const next = document.getElementById('paginaSiguienteDelegaciones');
            if (summary) summary.textContent = `${total} delegación(es)`;
            if (pageInfo) pageInfo.textContent = `Mostrando ${start}-${end} de ${total} · Página ${paginaActualDelegaciones} de ${pages}`;
            if (previous) previous.disabled = paginaActualDelegaciones <= 1;
            if (next) next.disabled = paginaActualDelegaciones >= pages;
        }

        function buscarDelegaciones() {
            busquedaDelegacion = document.getElementById('buscarDelegaciones')?.value || '';
            paginaActualDelegaciones = 1;
            renderizarDelegacionesCards(filtroZonaActivo);
        }

        function filtrarEstadoDelegaciones() {
            filtroEstadoDelegacion = document.getElementById('estadoDelegaciones')?.value || '';
            paginaActualDelegaciones = 1;
            renderizarDelegacionesCards(filtroZonaActivo);
        }

        function cambiarPaginaDelegaciones(delta) {
            const pages = Math.max(1, Math.ceil(delegacionesFiltradas().length / filasPorPaginaDelegaciones));
            paginaActualDelegaciones = Math.min(pages, Math.max(1, paginaActualDelegaciones + delta));
            renderizarDelegacionesCards(filtroZonaActivo);
        }

        function exportarDelegacionesExcel() {
            if (!window.XLSX) {
                Swal.fire({ icon: 'error', title: 'Excel no disponible', text: 'Recarga el panel e inténtalo nuevamente.' });
                return;
            }
            const rows = catalogoDelegacionesDB.filter(item => {
                if (filtroEstadoDelegacion && item.status !== filtroEstadoDelegacion) return false;
                if (!delegacionCoincideConSector(item)) return false;
                const query = normalizarBusquedaDelegacion(busquedaDelegacion);
                const searchable = normalizarBusquedaDelegacion([
                    item.code, item.name, item.commune, item.scope, item.address, item.phone, item.email, item.manager_name, item.status
                ].join(' '));
                return !query || searchable.includes(query);
            }).map(item => ({
                'Código': item.code || '',
                'Nombre': item.name,
                'Comuna': item.commune || 'La Serena',
                'Sector': item.scope,
                'Dirección': item.address || '',
                'Teléfono': item.phone || '',
                'Correo de contacto': item.email || '',
                'Encargado': item.manager_name || '',
                'Horario': item.schedule || '',
                'Funcionarios activos': item.users_count ?? 0,
                'Estado': item.status,
            }));
            if (!rows.length) {
                Swal.fire({ icon: 'info', title: 'Sin resultados', text: 'No hay delegaciones que coincidan con los filtros.' });
                return;
            }
            const worksheet = XLSX.utils.json_to_sheet(rows);
            const workbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(workbook, worksheet, 'Delegaciones');
            XLSX.writeFile(workbook, `Delegaciones_La_Serena_${new Date().toISOString().slice(0, 10)}.xlsx`);
        }

        function filtrarDelegacionesPorSector(zona) {
            filtroZonaActivo = zona;
            paginaActualDelegaciones = 1;
            document.querySelectorAll('.delegacion-filter-pill').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById(`btn-filtro-${zona}`);
            if (activeBtn) activeBtn.classList.add('active');
            renderizarDelegacionesCards(zona);
        }

        function seleccionarVistaDelegaciones(vista) {
            const esCards = (vista === 'cards');
            vistaDelegacionesActiva = esCards ? 'cards' : 'tabla';
            window.vistaDelegacionesActiva = vistaDelegacionesActiva;
            const cards = document.getElementById('delegacionesCardsGrid');
            const table = document.getElementById('delegacionesTablaVista');
            const label = document.getElementById('etiquetaVistaDelegaciones');
            const selectorBtn = document.getElementById('selectorVistaDelegaciones');

            if (cards) {
                if (esCards) {
                    cards.removeAttribute('hidden');
                    cards.classList.remove('vista-oculta');
                    cards.style.setProperty('display', 'grid', 'important');
                } else {
                    cards.setAttribute('hidden', '');
                    cards.classList.add('vista-oculta');
                    cards.style.setProperty('display', 'none', 'important');
                }
            }
            if (table) {
                if (!esCards) {
                    table.removeAttribute('hidden');
                    table.classList.remove('vista-oculta');
                    table.style.setProperty('display', 'block', 'important');
                } else {
                    table.setAttribute('hidden', '');
                    table.classList.add('vista-oculta');
                    table.style.setProperty('display', 'none', 'important');
                }
            }
            if (label) {
                label.textContent = esCards ? 'Tarjeta' : 'Lista';
            }
            if (selectorBtn) {
                const icon = selectorBtn.querySelector('i');
                if (icon) {
                    icon.className = esCards ? 'bi bi-grid-3x3-gap me-1' : 'bi bi-list-ul me-1';
                }
            }
            document.querySelectorAll('[data-vista-delegaciones]').forEach(option => {
                const target = option.dataset.vistaDelegaciones;
                const active = (target === 'cards' && esCards) || ((target === 'tabla' || target === 'lista') && !esCards);
                option.classList.toggle('active', active);
                option.setAttribute('aria-pressed', String(active));
            });
        }
        window.seleccionarVistaDelegaciones = seleccionarVistaDelegaciones;

        async function initDelegacionesView() {
            document.getElementById('buscarDelegaciones')?.addEventListener('input', buscarDelegaciones);
            document.getElementById('estadoDelegaciones')?.addEventListener('change', filtrarEstadoDelegaciones);
            document.getElementById('tamanoPaginaDelegaciones')?.addEventListener('change', event => {
                filasPorPaginaDelegaciones = Math.min(50, Math.max(10, Number(event.target.value) || 10));
                paginaActualDelegaciones = 1;
                renderizarDelegacionesCards(filtroZonaActivo);
            });
            document.querySelectorAll('[data-vista-delegaciones]').forEach(option => {
                option.addEventListener('click', () => seleccionarVistaDelegaciones(option.dataset.vistaDelegaciones));
            });
            seleccionarVistaDelegaciones(vistaDelegacionesActiva);
            try { await cargarCatalogosOrganizacion(); }
            catch (error) { console.warn('No fue posible sincronizar las fichas territoriales:', error); }
            renderizarDelegacionesCards(filtroZonaActivo);
        }

        function renderizarDelegacionesCards(filtro = 'todas') {
            const grid = document.getElementById('delegacionesCardsGrid');
            if (!grid) return;
            seleccionarVistaDelegaciones(vistaDelegacionesActiva);
            grid.innerHTML = '';

            const filtered = delegacionesFiltradas();
            const pages = Math.max(1, Math.ceil(filtered.length / filasPorPaginaDelegaciones));
            if (paginaActualDelegaciones > pages) paginaActualDelegaciones = pages;
            actualizarPaginacionDelegaciones(filtered.length, pages);
            const items = filtered.slice((paginaActualDelegaciones - 1) * filasPorPaginaDelegaciones, paginaActualDelegaciones * filasPorPaginaDelegaciones);
            const tableBody = document.getElementById('tablaDelegacionesBody');
            if (tableBody) {
                tableBody.replaceChildren();
                if (!items.length) {
                    const row = tableBody.insertRow();
                    const cell = row.insertCell();
                    cell.colSpan = 8;
                    cell.className = 'text-center py-5 text-muted';
                    cell.innerHTML = '<i class="bi bi-buildings fs-2 d-block mb-2 text-secondary"></i>No hay delegaciones para los filtros actuales.';
                } else {
                    items.forEach(item => {
                        const row = tableBody.insertRow();
                        row.className = `delegacion-table-row ${delegacionSeleccionadaActiva === item.id ? 'table-row-selected' : ''}`;
                        row.id = `row-del-${item.id}`;
                        row.onclick = (e) => {
                            if (e.target.closest('button') || e.target.closest('a')) return;
                            seleccionarDelegacion(item.id);
                        };

                        const isActivo = item.dbStatus === 'Activo';
                        const statusBadge = isActivo
                            ? `<span class="badge rounded-pill bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-check-circle-fill me-1"></i>Activa</span>`
                            : `<span class="badge rounded-pill bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1"><i class="bi bi-x-circle-fill me-1"></i>Inactiva</span>`;
                        const dotacionCount = item.funcionariosDB ?? (item.funcionarios ? item.funcionarios.length : 0);

                        row.innerHTML = `
                            <td>
                                <span class="badge bg-light text-dark border fw-bold px-2 py-1" style="font-size: 0.76rem;">${escaparHtmlCatalogo(item.codigo || '—')}</span>
                            </td>
                            <td>
                                <div class="d-flex align-items-center gap-2">
                                    <div class="delegacion-list-avatar" style="--del-color: ${item.color || '#1B365D'};">
                                        ${item.sigla || 'DM'}
                                    </div>
                                    <div>
                                        <div class="fw-bold delegacion-list-title" onclick="seleccionarDelegacion('${item.id}')">${escaparHtmlCatalogo(item.nombre)}</div>
                                        <div class="small text-muted" style="font-size: 0.76rem;">${escaparHtmlCatalogo(item.comuna || 'La Serena')}</div>
                                    </div>
                                </div>
                            </td>
                            <td>
                                <span class="badge bg-white text-secondary border px-2 py-1 rounded-pill small fw-semibold">
                                    <i class="bi bi-geo-alt-fill text-danger me-1"></i>${escaparHtmlCatalogo(item.sector || 'Sin sector')}
                                </span>
                            </td>
                            <td>
                                <div class="small text-dark fw-medium text-truncate" style="max-width: 220px;" title="${escaparHtmlCatalogo(item.direccion || '')}">
                                    <i class="bi bi-geo-alt text-muted me-1"></i>${escaparHtmlCatalogo(item.direccion || 'Sin dirección')}
                                </div>
                                ${item.telefono && item.telefono !== 'No registrado' ? `<div class="small text-muted" style="font-size: 0.75rem;"><i class="bi bi-telephone text-primary me-1"></i>${escaparHtmlCatalogo(item.telefono)}</div>` : ''}
                            </td>
                            <td>
                                <div class="small fw-semibold text-dark">
                                    <i class="bi bi-person-badge text-secondary me-1"></i>${escaparHtmlCatalogo(item.delegado || 'No registrado')}
                                </div>
                            </td>
                            <td class="text-center">
                                <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-2 py-1 fw-bold" style="font-size: 0.76rem;">
                                    <i class="bi bi-people-fill me-1"></i>${dotacionCount}
                                </span>
                            </td>
                            <td class="text-center">
                                ${statusBadge}
                            </td>
                            <td class="text-end">
                                <div class="d-inline-flex align-items-center gap-1 justify-content-end">
                                    <button type="button" class="btn btn-ver-ficha-tecnica-table shadow-xs" onclick="event.stopPropagation(); seleccionarDelegacion('${item.id}')" title="Ver ficha técnica territorial">
                                        <i class="bi bi-card-text me-1"></i><span>Ficha Técnica</span>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill px-2 py-1" onclick="event.stopPropagation(); abrirCatalogosOrganizacion('delegaciones').then(() => editarDelegacionCatalogo(${item.dbId}))" title="Editar delegación">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <button type="button" class="btn btn-sm btn-outline-${isActivo ? 'danger' : 'success'} rounded-pill px-2 py-1" onclick="event.stopPropagation(); alternarDelegacionCatalogo(${item.dbId})" title="${isActivo ? 'Inactivar sede' : 'Activar sede'}">
                                        <i class="bi bi-${isActivo ? 'slash-circle' : 'check2-circle'}"></i>
                                    </button>
                                </div>
                            </td>
                        `;
                    });
                }
            }
            if (!items.length) {
                grid.innerHTML = '<div class="col-12 text-center text-muted py-4">No hay delegaciones que coincidan con estos filtros.</div>';
                return;
            }

            items.forEach((d, idx) => {
                const card = document.createElement('div');
                card.className = `delegacion-modular-glass-card spotlight-card ${delegacionSeleccionadaActiva === d.id ? 'active-delegacion' : ''}`;
                card.id = `card-del-${d.id}`;
                card.onclick = () => {
                    seleccionarDelegacion(d.id);
                };

                let statusBadgeBg = 'rgba(5, 150, 105, 0.90)';
                let statusLabel = 'Estado sin datos';
                if (d.dbStatus === 'Inactivo') {
                    statusBadgeBg = 'rgba(71, 85, 105, 0.90)';
                    statusLabel = 'Inactiva';
                } else if (d.cumplimiento == null) {
                    statusBadgeBg = 'rgba(71, 85, 105, 0.90)';
                    statusLabel = 'Sin medición vigente';
                } else if (d.cumplimiento >= 85) {
                    statusBadgeBg = 'rgba(5, 150, 105, 0.90)';
                    statusLabel = 'Operativa 100%';
                } else if (d.cumplimiento >= 75) {
                    statusBadgeBg = 'rgba(217, 119, 6, 0.90)';
                    statusLabel = 'Alta Demanda';
                } else {
                    statusBadgeBg = 'rgba(220, 38, 38, 0.90)';
                    statusLabel = 'Atención Especial';
                }

                card.innerHTML = `
                    <div>
                        <div class="delegacion-card-identity" style="--delegation-color:${d.color || '#1B365D'}">
                            <span class="delegacion-card-monogram">${d.sigla || 'DM'}</span>
                            <span class="delegacion-card-number">${d.numero || '00'}</span>
                            <span class="delegacion-card-status-pill" style="background: ${statusBadgeBg};">
                                <i class="bi bi-circle-fill me-1" style="font-size: 0.55rem;"></i> ${statusLabel}
                            </span>
                            <span class="delegacion-card-score-pill">
                                <i class="bi bi-activity me-1"></i>${d.satisfaccion || 'Sin medición'}
                            </span>
                        </div>

                        <!-- Contenido Principal -->
                        <div class="p-3 pb-2">
                            <div class="text-muted text-uppercase fw-bold mb-1" style="font-size: 0.70rem; letter-spacing: 0.05em;">
                                ${d.sector}
                            </div>
                            <h4 class="fw-bold mb-1" style="color: var(--muni-navy); font-size: 1.25rem;">
                                ${d.nombre}
                            </h4>
                            <div class="text-secondary small text-truncate mb-3" style="font-size: 0.82rem;">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i>${d.direccion}
                            </div>

                            <!-- Cápsula de Gestor y Horario (Vidrio Esmerilado) -->
                            <div class="p-2 px-3 rounded-3 mb-2" style="background: rgba(27, 54, 93, 0.04); border: 1px solid rgba(226, 232, 240, 0.9);">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <span class="text-muted small" style="font-size: 0.74rem;">
                                        <i class="bi bi-person-badge text-primary me-1"></i>Encargado:
                                    </span>
                                    <span class="fw-bold text-dark small" style="font-size: 0.78rem;">${d.delegado || 'No registrado'}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Pie de la Tarjeta Reestructurado y Elegante -->
                    <div class="p-3 pt-0 mt-auto">
                        <div class="d-flex align-items-center justify-content-between pt-2 pb-2 mb-2 border-top">
                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1" style="font-size: 0.74rem; font-weight: 700;">
                                <i class="bi bi-folder2-open me-1"></i> ${d.atencionesMes == null ? 'Sin registros' : `${d.atencionesMes} atenciones mes`}
                            </span>
                            <span class="text-secondary small fw-semibold" style="font-size: 0.74rem;">
                                <i class="bi bi-clock text-muted me-1"></i>${d.horario && d.horario !== 'Horario no registrado' ? d.horario : '08:30 - 14:00'}
                            </span>
                        </div>
                        
                        <div class="d-flex align-items-center gap-2">
                            <button type="button" class="btn btn-ver-ficha-tecnica flex-grow-1" onclick="event.stopPropagation(); seleccionarDelegacion('${d.id}')" title="Ver ficha técnica territorial">
                                <i class="bi bi-card-text me-1"></i>
                                <span>Ver Ficha Técnica</span>
                                <i class="bi bi-arrow-right ms-auto"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-secondary btn-card-action" onclick="event.stopPropagation(); abrirCatalogosOrganizacion('delegaciones').then(() => editarDelegacionCatalogo(${d.dbId}))" title="Editar delegación">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-${d.dbStatus === 'Activo' ? 'danger' : 'success'} btn-card-action" onclick="event.stopPropagation(); alternarDelegacionCatalogo(${d.dbId})" title="${d.dbStatus === 'Activo' ? 'Inactivar sede' : 'Activar sede'}">
                                <i class="bi bi-${d.dbStatus === 'Activo' ? 'slash-circle' : 'check2-circle'}"></i>
                            </button>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
            if (typeof initSpotlightEffect === 'function') initSpotlightEffect();
        }

        function abrirDrawerExpediente(id) {
            cerrarDrawerExpediente();
            seleccionarDelegacion(id);
        }

        function cerrarDrawerExpediente() {
            const drawer = document.getElementById('drawerExpedienteSede');
            const overlay = document.getElementById('drawerBackdropOverlay');
            if (drawer) drawer.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
        }

        function exportarExpedienteSedePDF(id) {
            const data = datasetDelegacionesDetalle[id];
            if (!data) return;
            try {
                if (typeof window.jspdf === 'undefined') throw new Error("Librería jsPDF no disponible");
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

                // Franja Institucional
                doc.setFillColor(196, 18, 48);
                doc.rect(0, 0, 210, 8, 'F');
                doc.setFillColor(27, 54, 93);
                doc.rect(0, 8, 210, 16, 'F');

                doc.setFont("helvetica", "bold");
                doc.setFontSize(14);
                doc.setTextColor(255, 255, 255);
                doc.text("ILUSTRE MUNICIPALIDAD DE LA SERENA", 14, 18);

                doc.setFontSize(12);
                doc.setTextColor(27, 54, 93);
                doc.text(`EXPEDIENTE DE SEDE MUNICIPAL: ${data.nombre.toUpperCase()}`, 14, 34);

                doc.setFont("helvetica", "normal");
                doc.setFontSize(9);
                doc.setTextColor(91, 107, 130);
                doc.text(`Sector: ${data.sector} | Dirección: ${data.direccion}`, 14, 40);
                doc.text(`Horario: ${data.horario} | Encargado: ${data.delegado}`, 14, 45);

                const tableBody = [
                    ['Atenciones Mensuales', data.atencionesMes == null ? 'Sin datos' : `${data.atencionesMes} atenciones`],
                    ['Población Territorial', data.vecinosRegistrados == null ? 'Sin datos' : `${data.vecinosRegistrados} vecinos`],
                    ['Tasa de Resolución', data.tuboResueltos],
                    ['Satisfacción Vecinal', data.satisfaccion],
                    ['Dotación Funcionarios', `${data.funcionarios.length} funcionarios asignados`]
                ];

                doc.autoTable({
                    head: [['Indicador Operativo', 'Métrica Oficial']],
                    body: tableBody,
                    startY: 50,
                    theme: 'grid',
                    headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold' }
                });

                doc.save(`Expediente_${data.id}_La_Serena_${new Date().toISOString().slice(0, 10)}.pdf`);
                mostrarToast('✓ Expediente de delegación descargado en PDF.');
            } catch (err) {
                console.error("Error al exportar PDF de sede:", err);
                mostrarToast('⚠ Error al generar PDF: ' + err.message);
            }
        }

        function seleccionarDelegacion(id) {
            cerrarDrawerExpediente();
            if (typeof cerrarAdminDrawer === 'function') cerrarAdminDrawer();
            delegacionSeleccionadaActiva = id;
            const data = datasetDelegacionesDetalle[id];
            if (!data) return;

            // Actualizar estilo activo en las tarjetas modulares
            document.querySelectorAll('.delegacion-modular-glass-card').forEach(c => c.classList.remove('active-delegacion'));
            const activeCard = document.getElementById(`card-del-${id}`);
            if (activeCard) activeCard.classList.add('active-delegacion');

            // Actualizar estilo activo en filas de tabla modo lista
            document.querySelectorAll('.delegacion-table-row').forEach(r => r.classList.remove('table-row-selected'));
            const activeRow = document.getElementById(`row-del-${id}`);
            if (activeRow) activeRow.classList.add('table-row-selected');

            const panel = document.getElementById('panelDetalleDelegacion');
            if (!panel) return;

            // Construir Funcionarios HTML con tarjetas Liquid Glass legibles
            const funcionariosHtml = data.funcionarios.length ? data.funcionarios.map(f => `
                <div class="col-md-6 col-lg-3">
                    <div class="delegacion-funcionario-glass-card">
                        <div>
                            <div class="d-flex align-items-center gap-2 mb-2">
                                <div class="user-avatar-pill ${f.rol.includes('Coordinador') || f.rol.includes('Delegado') ? 'admin' : ''}" style="width:42px; height:42px; font-size:0.9rem; font-weight:800; background: var(--muni-navy); color:#FFF;">
                                    ${f.avatar}
                                </div>
                                <div style="min-width:0;">
                                    <div class="fw-bold text-truncate" style="color: var(--muni-navy); font-size: 0.92rem;" title="${f.nombre}">${f.nombre}</div>
                                </div>
                            </div>
                            <div class="small text-secondary mb-2"><strong>Cargo:</strong> ${f.cargo}</div>
                            <span class="role-badge-pill role-badge-${f.rol.toLowerCase().includes('gestor') ? 'gestor' : f.rol.toLowerCase().includes('verificador') ? 'verificador' : 'admin'} mb-2">
                                ${f.rol}
                            </span>
                        </div>
                    </div>
                </div>
            `).join('') : '<div class="col-12"><p class="text-secondary small mb-0">No hay funcionarios registrados para esta delegación.</p></div>';

            // Construir Barrios HTML
            const barriosHtml = data.barrios.length ? data.barrios.map(b => `
                <span class="badge bg-white text-dark border px-3 py-2 rounded-pill me-1 mb-2 shadow-xs" style="font-size:0.82rem; font-weight:600;">
                    <i class="bi bi-geo-alt-fill text-danger me-1"></i> ${b}
                </span>
            `).join('') : '<span class="text-secondary small">Sin sectores descriptivos registrados.</span>';

            // Construir Métricas de Atención
            const metricasHtml = data.metricasAtencion.length ? data.metricasAtencion.map(m => `
                <div class="mb-3">
                    <div class="d-flex justify-content-between small fw-bold mb-1">
                        <span style="color: var(--muni-navy);">${m.tipo}</span>
                        <span class="text-primary fw-bold">${m.cantidad} (${m.porcentaje}%)</span>
                    </div>
                    <div class="progress" style="height: 8px; border-radius: 6px; background: rgba(226, 232, 240, 0.8);">
                        <div class="progress-bar" style="width: ${m.porcentaje}%; background-color: ${data.colorSemaforo}; border-radius: 6px;"></div>
                    </div>
                </div>
            `).join('') : '<p class="text-secondary small mb-0">Sin métricas verificadas disponibles.</p>';

            panel.innerHTML = `
                <!-- Barra de Navegación Rápida -->
                <div class="mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 py-1 fw-bold shadow-xs d-flex align-items-center gap-2" onclick="document.getElementById('panelDetalleDelegacion').style.display='none'; document.getElementById('view-delegaciones').scrollIntoView({behavior: 'smooth'});">
                        <i class="bi bi-arrow-left"></i> Volver a todas las delegaciones
                    </button>
                    <span class="badge bg-white text-secondary border px-3 py-2 rounded-pill small fw-bold shadow-xs">
                        <i class="bi bi-geo-alt-fill text-danger me-1"></i> Ficha Territorial Oficial: ${data.nombre}
                    </span>
                </div>

                <!-- Ficha territorial con el color y las siglas de la delegación -->
                <div class="delegacion-detail-hero-banner delegation-color-hero" style="--delegation-color:${data.color || '#1B365D'}">
                    <div class="delegacion-detail-monogram" aria-hidden="true">${data.sigla || 'DM'}</div>
                    <div class="delegacion-detail-hero-glass-card">
                        <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-2">
                            <div>
                                <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
                                    <span class="badge rounded-pill px-3 py-1 text-uppercase fw-bold" style="background: var(--muni-navy); color: #FFF; font-size: 0.72rem; letter-spacing: 0.05em;">
                                        Sede Municipal Activa
                                    </span>
                                    <span class="badge rounded-pill px-3 py-1 fw-bold text-white shadow-xs" style="background: ${data.colorSemaforo}; font-size: 0.72rem;">
                                        <i class="bi bi-circle-fill me-1" style="font-size: 0.55rem;"></i>${data.statusSemaforo}
                                    </span>
                                    <span class="badge bg-white text-dark border px-2 py-1 rounded-pill small fw-bold">
                                        <i class="bi bi-star-fill text-warning me-1"></i>${data.satisfaccion} Satisfacción
                                    </span>
                                </div>
                                <h2 class="m-0 fw-bold" style="color: var(--muni-navy); font-size: 1.85rem; letter-spacing: -0.3px;">
                                    ${data.nombre}
                                </h2>
                                <p class="text-secondary m-0 fw-semibold" style="font-size: 0.95rem;">
                                    ${data.sector} • Cobertura Comunal La Serena
                                </p>
                            </div>
                            
                            <div class="d-flex align-items-center gap-2">
                                <button class="btn-exportar-pdf-oficial" onclick="exportarFichaDelegacionPDF('${data.id}')" title="Descargar Ficha en PDF">
                                    <i class="bi bi-file-earmark-pdf-fill"></i> Descargar Ficha PDF
                                </button>
                            </div>
                        </div>

                        <!-- Datos Institucionales de la Delegación -->
                        <div class="row g-2 mt-3 pt-3 border-top text-dark small" style="border-color: rgba(226, 232, 240, 0.9) !important; font-size: 0.88rem;">
                            <div class="col-md-4">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i> <strong>Sede:</strong> ${data.direccion}
                            </div>
                            <div class="col-md-3">
                                <i class="bi bi-telephone-fill text-primary me-1"></i> <strong>Fono:</strong> ${data.telefono}
                            </div>
                            <div class="col-md-2">
                                <i class="bi bi-clock-fill text-success me-1"></i> <strong>Horario:</strong> ${data.horario}
                            </div>
                            <div class="col-md-3 text-md-end">
                                <i class="bi bi-person-badge-fill text-warning me-1"></i> <strong>Delegado(a):</strong> ${data.delegado}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="p-4 pt-1">
                    <!-- Resumen Territorial Municipal -->
                    <div class="alert alert-light border-start border-4 mb-4 py-3 px-4 text-secondary shadow-xs" style="border-left-color: ${data.colorSemaforo} !important; background: rgba(255, 255, 255, 0.9); border-radius: 12px; font-size: 0.92rem; line-height: 1.5;">
                        <i class="bi bi-info-circle-fill text-primary me-2 fs-6"></i> ${data.resumen}
                    </div>

                    <!-- KPIs Específicos de esta Delegación en Cápsulas Liquid Glass -->
                    <div class="row g-3 mb-4">
                        <div class="col-sm-6 col-md-3">
                            <div class="delegacion-detail-kpi-card">
                                <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.04em;">Cumplimiento Operativo</div>
                                <div class="fs-3 fw-bold my-1" style="color: ${data.colorSemaforo};">${data.cumplimiento == null ? 'Sin datos' : `${data.cumplimiento}%`}</div>
                                <div class="progress" style="height: 6px; border-radius: 4px; background: rgba(226, 232, 240, 0.8);">
                                    <div class="progress-bar" style="width: ${data.cumplimiento || 0}%; background-color: ${data.colorSemaforo}; border-radius: 4px;"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <div class="delegacion-detail-kpi-card">
                                <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.04em;">Atenciones del Mes</div>
                                <div class="fs-3 fw-bold my-1" style="color: var(--muni-navy);">${data.atencionesMes == null ? 'Sin datos' : data.atencionesMes}</div>
                                <small class="text-muted fw-semibold">${data.atencionesMes == null ? 'Sin registros verificados' : 'Registros disponibles'}</small>
                            </div>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <div class="delegacion-detail-kpi-card">
                                <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.04em;">Vecinos Atendidos</div>
                                <div class="fs-3 fw-bold my-1" style="color: var(--muni-navy);">${data.vecinosRegistrados == null ? 'Sin datos' : data.vecinosRegistrados}</div>
                                <small class="text-muted fw-semibold">Población territorial</small>
                            </div>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <div class="delegacion-detail-kpi-card">
                                <div class="text-muted small fw-bold text-uppercase" style="font-size: 0.72rem; letter-spacing: 0.04em;">Casos Resueltos</div>
                                <div class="fs-3 fw-bold my-1 text-primary">${data.tuboResueltos || 'Sin datos'}</div>
                                <small class="text-info fw-bold"><i class="bi bi-shield-check me-1"></i>Satisfacción: ${data.satisfaccion}</small>
                            </div>
                        </div>
                    </div>

                    <!-- Dotación Funcionaria de esta Delegación -->
                    <div class="mb-4">
                        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
                            <h5 class="fw-bold m-0" style="color: var(--muni-navy);">
                                <i class="bi bi-people-fill text-primary me-2"></i> Dotación Funcionaria Asignada (${data.funcionarios.length} funcionarios)
                            </h5>
                            <button class="btn btn-sm btn-outline-muni-red rounded-pill px-3 fw-bold" onclick="switchView('usuarios')">
                                <i class="bi bi-gear-fill me-1"></i> Administrar en Usuarios
                            </button>
                        </div>
                        <div class="row g-3">
                            ${funcionariosHtml}
                        </div>
                    </div>

                    <div class="row g-4 pt-2">
                        <!-- Barrios y Unidades Vecinales -->
                        <div class="col-lg-7">
                            <h5 class="fw-bold mb-3" style="color: var(--muni-navy);">
                                <i class="bi bi-map-fill text-danger me-2"></i> Barrios y Sectores Atendidos
                            </h5>
                            <div class="p-3 rounded-4 border bg-white mb-2 shadow-xs">
                                ${barriosHtml}
                            </div>
                            <small class="text-muted">
                                * Cada sector cuenta con enlace territorial directo con directivas de Juntas de Vecinos y clubes de personas mayores.
                            </small>
                        </div>

                        <!-- Desglose de Atenciones por Tipo -->
                        <div class="col-lg-5">
                            <h5 class="fw-bold mb-3" style="color: var(--muni-navy);">
                                <i class="bi bi-pie-chart-fill text-success me-2"></i> Distribución de Atenciones
                            </h5>
                            <div class="p-3 rounded-4 border bg-white shadow-xs">
                                ${metricasHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            panel.style.display = 'block';

            // Desplazamiento suave al panel de detalle
            setTimeout(() => {
                panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);

            mostrarToast(`✓ Ficha territorial de ${data.nombre} cargada correctamente.`);
        }

        function exportarFichaDelegacionPDF(id) {
            const data = datasetDelegacionesDetalle[id];
            if (!data || !window.jspdf) return;

            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();

            // Membrete Oficial
            doc.setFillColor(27, 54, 93);
            doc.rect(0, 0, 210, 22, 'F');
            doc.setFillColor(196, 18, 48);
            doc.rect(0, 22, 210, 2, 'F');

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13);
            doc.setTextColor(255, 255, 255);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA', 14, 11);
            doc.setFontSize(8.5);
            doc.setFont('helvetica', 'normal');
            doc.text(`Ficha Territorial Oficial · ${data.nombre}`, 14, 17);

            const hoy = new Date().toLocaleDateString('es-CL');
            doc.text(`Fecha: ${hoy}`, 196, 17, { align: 'right' });

            doc.setTextColor(27, 54, 93);
            doc.setFontSize(14);
            doc.setFont('helvetica', 'bold');
            doc.text(data.nombre, 14, 33);

            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(60, 60, 60);
            doc.text(`Sector: ${data.sector} | Sede: ${data.direccion}`, 14, 39);
            doc.text(`Teléfono: ${data.telefono} | Correo: ${data.email || 'No registrado'} | Encargado: ${data.delegado}`, 14, 44);
            doc.text(`Cumplimiento de Metas: ${data.cumplimiento == null ? 'Sin datos' : `${data.cumplimiento}%`} | Atenciones del Mes: ${data.atencionesMes ?? 'Sin datos'} | Vecinos: ${data.vecinosRegistrados ?? 'Sin datos'}`, 14, 49);

            // Tabla de funcionarios
            const rowsStaff = data.funcionarios.map(f => [f.nombre, f.cargo, f.rol]);
            doc.autoTable({
                head: [['Funcionario', 'Cargo', 'Rol']],
                body: rowsStaff.length ? rowsStaff : [['Sin datos registrados', '—', '—']],
                startY: 55,
                theme: 'striped',
                headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold' },
                styles: { fontSize: 8 }
            });

            // Tabla de barrios y desglose
            const finalY = doc.lastAutoTable.finalY + 8;
            doc.setFontSize(11);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(27, 54, 93);
            doc.text('Desglose de Atenciones por Área:', 14, finalY);

            const rowsMetrics = data.metricasAtencion.map(m => [m.tipo, m.cantidad, m.porcentaje + '%']);
            doc.autoTable({
                head: [['Tipo de Atención', 'Cantidad Atendida', 'Porcentaje']],
                body: rowsMetrics.length ? rowsMetrics : [['Sin métricas verificadas', '—', '—']],
                startY: finalY + 4,
                theme: 'plain',
                headStyles: { fillColor: [196, 18, 48], textColor: [255, 255, 255], fontStyle: 'bold' },
                styles: { fontSize: 8 }
            });

            doc.save(`Ficha_${data.id}_La_Serena.pdf`);
            mostrarToast(`✓ Ficha PDF de ${data.nombre} generada y descargada.`);
        }

        // ==============================================================================
        // MÓDULO ROLES Y MATRIZ DE PERMISOS (LIQUID GLASS & MYADMIN POWER)
        // ==============================================================================

        let datasetRoles = [
            {
                id: 4,
                name: 'Administrador',
                description: 'Acceso total al sistema',
                is_system: true,
                permissions: [
                    'delegaciones.view', 'delegaciones.create', 'delegaciones.edit', 'delegaciones.delete',
                    'usuarios.view', 'usuarios.create', 'usuarios.edit', 'usuarios.toggle_status', 'usuarios.reset_password', 'usuarios.delete',
                    'roles.view', 'roles.create', 'roles.edit', 'roles.delete', 'roles.manage_features',
                    'metas.view', 'metas.create', 'metas.edit', 'metas.delete',
                    'tipo_atencion.view', 'tipo_atencion.create', 'tipo_atencion.edit', 'tipo_atencion.delete',
                    'atenciones.view', 'atenciones.create', 'atenciones.edit', 'atenciones.validate', 'atenciones.reject', 'atenciones.export',
                    'vecinos.view', 'vecinos.create', 'vecinos.edit', 'vecinos.social_aid', 'vecinos.delete', 'vecinos.export',
                    'reportes.view', 'reportes.export_excel', 'reportes.export_pdf',
                    'auditoria.view', 'auditoria.config'
                ],
                permissions_count: 40,
                users_count: 0,
                users_sample: []
            },
            {
                id: 9,
                name: 'Operador',
                description: 'Gestión de atenciones',
                is_system: true,
                permissions: [
                    'atenciones.view', 'atenciones.create', 'atenciones.edit', 'atenciones.export',
                    'vecinos.view', 'vecinos.create', 'vecinos.edit', 'vecinos.social_aid',
                    'tipo_atencion.view', 'delegaciones.view', 'reportes.view'
                ],
                permissions_count: 11,
                users_count: 0,
                users_sample: []
            },
            {
                id: 10,
                name: 'Consultor',
                description: 'Solo lectura',
                is_system: true,
                permissions: [
                    'atenciones.view', 'vecinos.view', 'delegaciones.view',
                    'metas.view', 'tipo_atencion.view', 'reportes.view'
                ],
                permissions_count: 6,
                users_count: 0,
                users_sample: []
            },
            {
                id: 3,
                name: 'Verificador',
                description: 'Revisión técnica, validación formal y auditoría de evidencias.',
                is_system: true,
                permissions: [
                    'atenciones.view', 'atenciones.validate', 'atenciones.reject', 'atenciones.export',
                    'tipo_atencion.view', 'delegaciones.view', 'vecinos.view', 'reportes.view'
                ],
                permissions_count: 8,
                users_count: 0,
                users_sample: []
            },
            {
                id: 5,
                name: 'Coordinador',
                description: 'Supervisión institucional, metas y reportes consolidados comunales.',
                is_system: true,
                permissions: [
                    'metas.view', 'metas.create', 'metas.edit', 'atenciones.view', 'atenciones.export',
                    'vecinos.view', 'delegaciones.view', 'reportes.view', 'reportes.export_excel', 'reportes.export_pdf', 'auditoria.view'
                ],
                permissions_count: 11,
                users_count: 0,
                users_sample: []
            },
            {
                id: 6,
                name: 'Delegado',
                description: 'Jefatura de delegación y gestión del tubo de trabajo territorial.',
                is_system: true,
                permissions: [
                    'delegaciones.view', 'delegaciones.edit', 'usuarios.view',
                    'atenciones.view', 'atenciones.create', 'atenciones.edit', 'atenciones.export',
                    'vecinos.view', 'vecinos.create', 'vecinos.edit', 'reportes.view'
                ],
                permissions_count: 11,
                users_count: 0,
                users_sample: []
            },
            {
                id: 7,
                name: 'Funcionario',
                description: 'Registro operativo de actividades, atenciones, compromisos y evidencias.',
                is_system: true,
                permissions: [
                    'atenciones.view', 'atenciones.create', 'atenciones.edit',
                    'vecinos.view', 'vecinos.create', 'tipo_atencion.view', 'delegaciones.view'
                ],
                permissions_count: 7,
                users_count: 0,
                users_sample: []
            },
            {
                id: 2,
                name: 'Gestor Territorial',
                description: 'Atención ciudadana en terreno y agenda colectiva.',
                is_system: true,
                permissions: [
                    'atenciones.view', 'atenciones.create', 'atenciones.edit',
                    'vecinos.view', 'vecinos.create', 'vecinos.edit', 'vecinos.social_aid',
                    'delegaciones.view'
                ],
                permissions_count: 8,
                users_count: 0,
                users_sample: []
            }
        ];

        let datasetCatalogPermisos = [
            {
                module_id: 'delegaciones',
                module_name: 'Delegaciones Municipales',
                icon: 'bi-building',
                description: 'Gestión de recintos y ámbito territorial comunal',
                permissions: [
                    { code: 'delegaciones.view', name: 'Ver Delegaciones', desc: 'Consultar información y listado de delegaciones' },
                    { code: 'delegaciones.create', name: 'Crear Delegación', desc: 'Registrar nuevas unidades territoriales' },
                    { code: 'delegaciones.edit', name: 'Editar Delegación', desc: 'Modificar dirección, ámbito y datos' },
                    { code: 'delegaciones.delete', name: 'Inactivar / Borrar', desc: 'Suspender o dar de baja una delegación' }
                ]
            },
            {
                module_id: 'usuarios',
                module_name: 'Gestión de Usuarios y Personal',
                icon: 'bi-people',
                description: 'Control de cuentas de funcionarios municipales y perfiles',
                permissions: [
                    { code: 'usuarios.view', name: 'Ver Funcionarios', desc: 'Listar funcionarios y consultar perfiles' },
                    { code: 'usuarios.create', name: 'Crear Funcionarios', desc: 'Registrar nuevas cuentas de usuario' },
                    { code: 'usuarios.edit', name: 'Modificar Cuentas', desc: 'Editar datos, delegación, cargo y roles' },
                    { code: 'usuarios.toggle_status', name: 'Activar/Desactivar', desc: 'Habilitar o suspender acceso al sistema' },
                    { code: 'usuarios.reset_password', name: 'Resetear Contraseñas', desc: 'Asignar nueva contraseña de acceso' },
                    { code: 'usuarios.delete', name: 'Eliminar Usuarios', desc: 'Borrado lógico o permanente de cuentas' }
                ]
            },
            {
                module_id: 'roles',
                module_name: 'Roles y Matriz de Permisos',
                icon: 'bi-shield-check',
                description: 'Gestión de perfiles y asignación de permisos del sistema',
                permissions: [
                    { code: 'roles.view', name: 'Ver Roles y Privilegios', desc: 'Visualizar roles configurados y permisos' },
                    { code: 'roles.create', name: 'Crear Nuevos Roles', desc: 'Definir nuevos perfiles con permisos personalizados' },
                    { code: 'roles.edit', name: 'Editar Matriz y Permisos', desc: 'Modificar asignación de privilegios a roles' },
                    { code: 'roles.delete', name: 'Eliminar Roles', desc: 'Dar de baja roles no protegidos' },
                    { code: 'roles.manage_features', name: 'Administrar Funciones', desc: 'Registrar nuevas funciones y privilegios al sistema' }
                ]
            },
            {
                module_id: 'metas',
                module_name: 'Metas e Indicadores SGR',
                icon: 'bi-bullseye',
                description: 'Medición de metas de atención ciudadana y desempeño',
                permissions: [
                    { code: 'metas.view', name: 'Ver Metas e Indicadores', desc: 'Consultar cumplimiento y metas asignadas' },
                    { code: 'metas.create', name: 'Crear Metas Mensuales', desc: 'Definir nuevas metas territoriales' },
                    { code: 'metas.edit', name: 'Actualizar Indicadores', desc: 'Registrar avances y mediciones diarias' },
                    { code: 'metas.delete', name: 'Anular Metas', desc: 'Eliminar o recalibrar metas fijadas' }
                ]
            },
            {
                module_id: 'tipo_atencion',
                module_name: 'Catálogo de Atención Municipal',
                icon: 'bi-tags',
                description: 'Tipos de atención, sub-atenciones y servicios',
                permissions: [
                    { code: 'tipo_atencion.view', name: 'Ver Catálogo de Servicios', desc: 'Consultar tipos y sub-tipos vigentes' },
                    { code: 'tipo_atencion.create', name: 'Agregar Nuevos Servicios', desc: 'Crear tipos y sub-atenciones' },
                    { code: 'tipo_atencion.edit', name: 'Editar Servicios', desc: 'Modificar descripciones y clasificaciones' },
                    { code: 'tipo_atencion.delete', name: 'Desactivar Servicios', desc: 'Inactivar servicios obsoletos' }
                ]
            },
            {
                module_id: 'atenciones',
                module_name: 'Atenciones y Trámites Ciudadanos',
                icon: 'bi-headset',
                description: 'Registro operativo, tickets y atención en terreno',
                permissions: [
                    { code: 'atenciones.view', name: 'Ver Registro de Atenciones', desc: 'Consultar bitácora general de atenciones' },
                    { code: 'atenciones.create', name: 'Registrar Nueva Atención', desc: 'Ingresar solicitud ciudadana o trámite' },
                    { code: 'atenciones.edit', name: 'Editar Atenciones', desc: 'Modificar estado, evidencia y notas' },
                    { code: 'atenciones.validate', name: 'Validar / Aprobar', desc: 'Rol Verificador: autorizar atenciones con evidencia' },
                    { code: 'atenciones.reject', name: 'Observar / Rechazar', desc: 'Devolver trámites incompletos o sin respaldo' },
                    { code: 'atenciones.export', name: 'Exportar Registros', desc: 'Descargar atenciones en Excel y PDF' }
                ]
            },
            {
                module_id: 'vecinos',
                module_name: 'Vecinos y Casos Sociales',
                icon: 'bi-person-vcard',
                description: 'Padrón de vecinos, ayudas sociales y compromisos',
                permissions: [
                    { code: 'vecinos.view', name: 'Ver Padrón de Vecinos', desc: 'Consultar ficha de vecinos y antecedentes' },
                    { code: 'vecinos.create', name: 'Registrar Nuevo Vecino', desc: 'Ingresar vecino con RUT y domicilio' },
                    { code: 'vecinos.edit', name: 'Modificar Datos de Vecinos', desc: 'Actualizar teléfono, dirección y sector' },
                    { code: 'vecinos.social_aid', name: 'Gestionar Casos Sociales', desc: 'Vincular subsidios, ayudas y asistencias' },
                    { code: 'vecinos.delete', name: 'Eliminar Vecino', desc: 'Dar de baja registros duplicados o erróneos' },
                    { code: 'vecinos.export', name: 'Exportar Padrón Comunal', desc: 'Descarga oficial de registros a Excel' }
                ]
            },
            {
                module_id: 'reportes',
                module_name: 'Reportes y Estadísticas Oficiales',
                icon: 'bi-bar-chart-line',
                description: 'Generación de informes gerenciales e indicadores',
                permissions: [
                    { code: 'reportes.view', name: 'Visualizar Dashboard y Métricas', desc: 'Acceso a gráficos y tableros interactivos' },
                    { code: 'reportes.export_excel', name: 'Descargar Excel Oficial', desc: 'Generación de planillas consolidadas' },
                    { code: 'reportes.export_pdf', name: 'Generar PDF Institucional', desc: 'Informes formales con timbre municipal' }
                ]
            },
            {
                module_id: 'auditoria',
                module_name: 'Auditoría Transversal y Sistema',
                icon: 'bi-clock-history',
                description: 'Trazabilidad de cambios, seguridad y administración',
                permissions: [
                    { code: 'auditoria.view', name: 'Ver Log de Auditoría', desc: 'Rastrear quién, cuándo y qué se modificó' },
                    { code: 'auditoria.config', name: 'Parámetros del Sistema', desc: 'Configuración global y seguridad avanzada' }
                ]
            }
        ];

        let filasFiltradasRoles = [];
        let paginaActualRoles = 1;
        let filasPorPaginaRoles = 10;
        let rolEliminarId = null;
        let verPermisosExtendidos = false;

        async function initRolesView(mostrarAviso = false) {
            try {
                const res = await fetch('/api/roles/');
                if (!res.ok) throw new Error(`No se pudieron consultar los roles (HTTP ${res.status}).`);
                const data = await res.json();
                if (data.success && data.roles) {
                    datasetRoles = data.roles;
                    if (data.catalog) datasetCatalogPermisos = data.catalog;

                    // Orden prioritario idéntico al PDF:
                    // 1: Administrador ("Acceso total al sistema")
                    // 2: Operador ("Gestión de atenciones")
                    // 3: Consultor ("Solo lectura")
                    const priorityNames = ['Administrador', 'Operador', 'Consultor', 'Verificador', 'Coordinador', 'Delegado', 'Funcionario', 'Gestor Territorial'];
                    datasetRoles.sort((a, b) => {
                        const idxA = priorityNames.indexOf(a.name);
                        const idxB = priorityNames.indexOf(b.name);
                        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                        if (idxA !== -1) return -1;
                        if (idxB !== -1) return 1;
                        return a.name.localeCompare(b.name);
                    });
                    renderTarjetasPermisosRoles(datasetRoles);

                    // Actualizar contadores KPI
                    if (data.summary) {
                        const elTot = document.getElementById('lblTotalRoles');
                        if (elTot) elTot.textContent = data.summary.total_roles;
                        const elSis = document.getElementById('lblRolesSistema');
                        if (elSis) elSis.textContent = data.summary.system_roles;
                        const elPer = document.getElementById('lblTotalPermisos');
                        if (elPer) elPer.textContent = data.summary.total_permissions_available;
                    }
                    const totalUsersCovered = datasetRoles.reduce((acc, r) => acc + (r.users_count || 0), 0);
                    const elUsr = document.getElementById('lblUsuariosRoles');
                    if (elUsr) elUsr.textContent = totalUsersCovered;
                } else throw new Error(data.message || 'Respuesta inválida al consultar los roles.');
                filtrarRoles();
                if (mostrarAviso) {
                    mostrarToast('✓ Base de datos sincronizada: ' + datasetRoles.length + ' roles activos.');
                }
            } catch (err) {
                console.warn("Error al cargar roles desde API (usando catálogo local):", err);
                const grid = document.getElementById('roleCardsLive');
                if (grid) {
                    grid.innerHTML = '<p class="text-danger mb-0">No se pudieron cargar los permisos guardados. Recarga esta sección para intentarlo de nuevo.</p>';
                    grid.dataset.ready = 'true';
                }
                filtrarRoles();
            }
        }

        function renderTarjetasPermisosRoles(roles) {
            const grid = document.getElementById('roleCardsLive');
            if (!grid) return;
            const permisos = [
                ['lectura', 'Lectura'], ['edicion', 'Edición'],
                ['derivacion', 'Derivación'], ['cierre', 'Cierre']
            ];
            const colores = ['#C41230', '#6554C0', '#008F8C', '#1677A8', '#E28C20', '#678341'];
            const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            })[char]);

            if (!roles.length) {
                grid.innerHTML = '<p class="text-secondary mb-0">No hay roles activos registrados.</p>';
                grid.dataset.ready = 'true';
                return;
            }

            grid.innerHTML = roles.map((role, index) => {
                const color = colores[index % colores.length];
                const description = role.description && role.description !== 'Sin descripción'
                    ? role.description : 'Sin descripción registrada.';
                const assigned = new Set((role.permissions || []).map(permission => String(permission).toLowerCase()));
                const adminRole = role.is_admin_role === true || String(role.name).trim().toLocaleLowerCase() === 'administrador';
                const controls = permisos.map(([code, label]) => `
                    <div class="role-perm-pill-toggle">
                        <span>${label}</span>
                        <label class="perm-mini-switch">
                            <input type="checkbox" data-role-name="${escapeHtml(role.name)}" data-permission="${code}"
                                aria-label="${label} para ${escapeHtml(role.name)}" ${adminRole || assigned.has(code) ? 'checked' : ''}
                                ${adminRole ? 'disabled title="El rol Administrador conserva acceso integral"' : ''}>
                            <span class="perm-mini-slider"></span>
                        </label>
                    </div>`).join('');
                return `
                    <article class="role-profile-card" style="--role-card-accent:${color}; border-top:3px solid ${color};">
                        <div class="d-flex align-items-center justify-content-between gap-2 mb-2">
                            <div class="d-flex align-items-center gap-2 min-w-0">
                                <div class="role-card-icon" style="color:${color};background:${color}18"><i class="bi ${role.is_system ? 'bi-shield-lock-fill' : 'bi-person-badge-fill'}"></i></div>
                                <div class="min-w-0"><h5 class="role-card-title">${escapeHtml(role.name)}</h5>
                                    <span class="text-muted role-card-kind">${role.is_system ? 'Rol de sistema' : 'Rol personalizado'}</span></div>
                            </div>
                            <span class="badge bg-light text-secondary rounded-pill role-card-users">${Number(role.users_count) || 0} usuarios</span>
                        </div>
                        <p class="role-card-description">${escapeHtml(description)}</p>
                        <div class="role-perm-matrix-bar">${controls}</div>
                    </article>`;
            }).join('');

            grid.querySelectorAll('input[data-role-name]').forEach(input => {
                input.addEventListener('change', () => toggleRolPermisoCard(input.dataset.roleName, input.dataset.permission, input));
            });
            grid.dataset.ready = 'true';
        }
        function filtrarRoles() {
            const elSearchR = document.getElementById('searchRolesInput');
            const query = (elSearchR && elSearchR.value ? elSearchR.value : '').toLowerCase().trim();
            const elTipoR = document.getElementById('filtroTipoRol');
            const tipoFiltro = (elTipoR && elTipoR.value) ? elTipoR.value : '';
            const elModR = document.getElementById('filtroModuloRol');
            const modFiltro = (elModR && elModR.value) ? elModR.value : '';

            filasFiltradasRoles = datasetRoles.filter(r => {
                const matchTexto = !query ||
                    r.name.toLowerCase().includes(query) ||
                    r.description.toLowerCase().includes(query) ||
                    (r.permissions && r.permissions.some(p => p.toLowerCase().includes(query)));

                const matchTipo = !tipoFiltro ||
                    (tipoFiltro === 'sistema' && r.is_system) ||
                    (tipoFiltro === 'personalizado' && !r.is_system);

                const matchModulo = !modFiltro ||
                    (r.permissions && r.permissions.some(p => p.startsWith(modFiltro + '.')));

                return matchTexto && matchTipo && matchModulo;
            });

            paginaActualRoles = 1;
            renderTablaRoles();
        }

        function limpiarFiltrosRoles() {
            const elSearch = document.getElementById('searchRolesInput');
            if (elSearch) elSearch.value = '';
            const elTipo = document.getElementById('filtroTipoRol');
            if (elTipo) elTipo.value = '';
            const elMod = document.getElementById('filtroModuloRol');
            if (elMod) elMod.value = '';
            filtrarRoles();
        }

        function toggleDetallePermisos(btn) {
            verPermisosExtendidos = !verPermisosExtendidos;
            const lbl = document.getElementById('lblToggleDetallePermisos');
            if (lbl) {
                lbl.textContent = verPermisosExtendidos ? 'Vista Compacta (PDF)' : 'Ver Permisos Detallados';
            }
            renderTablaRoles();
        }

        function renderTablaRoles() {
            const tbody = document.getElementById('tablaRolesBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            const totalLabel = document.getElementById('lblTotalRoles');
            if (totalLabel) totalLabel.textContent = String(datasetRoles.length);

            const total = filasFiltradasRoles.length;
            const inicio = (paginaActualRoles - 1) * filasPorPaginaRoles;
            const fin = inicio + filasPorPaginaRoles;
            const datos = filasFiltradasRoles.slice(inicio, fin);

            if (datos.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center py-4 text-muted">
                            <i class="bi bi-shield-x fs-3 d-block mb-1 text-secondary"></i>
                            No se encontraron roles que coincidan con la búsqueda.
                        </td>
                    </tr>`;
                const info = document.getElementById('lblRegistrosInfoRoles');
                if (info) info.textContent = '0 registros encontrados';
                actualizarPaginadorRoles(0);
                return;
            }

            datos.forEach((r, idx) => {
                const tr = document.createElement('tr');
                const rowNum = inicio + idx + 1;

                // Generar resumen sobrio y profesional de permisos
                const perms = r.permissions || [];
                const totalPermsCount = perms.length;
                let permsHtml = '';

                if (r.name === 'Administrador' || totalPermsCount >= 38) {
                    permsHtml = `<span class="badge bg-light text-dark border px-2 py-1 fw-semibold" style="font-size: 0.80rem;">Acceso Total (${totalPermsCount} funciones)</span>`;
                } else {
                    permsHtml = `<span class="badge bg-light text-secondary border px-2 py-1 fw-semibold" style="font-size: 0.80rem;">${totalPermsCount} funciones autorizadas</span>`;
                }
                permsHtml += ` <a href="javascript:void(0)" class="ms-2 text-primary text-decoration-none fw-semibold small" onclick="abrirModalVerPermisos(${r.id})" title="Ver detalle de permisos">Ver detalle</a>`;

                // Botones de acción fieles al PDF (Lápiz editar y Basurero borrar) + Duplicar
                const isCoreProtected = (r.name === 'Administrador' || r.name === 'Operador' || r.name === 'Consultor');
                const btnDelete = `<button class="btn-action-icon btn-action-delete" onclick="abrirModalEliminarRol(${r.id})" title="${isCoreProtected ? 'Rol del sistema protegido' : 'Eliminar este rol'}">
                    <i class="bi bi-trash" style="color: ${isCoreProtected ? '#94A3B8' : '#DC2626'};"></i>
                </button>`;

                tr.innerHTML = `
                    <td class="text-center fw-semibold text-secondary" style="font-size: 0.90rem;">${rowNum}</td>
                    <td>
                        <span class="fw-bold" style="color: var(--muni-navy); font-size: 0.94rem;">${escapeHtml(r.name)}</span>
                    </td>
                    <td class="text-secondary" style="font-size: 0.88rem;">${escapeHtml(r.description || 'Sin descripción')}<small class="d-block mt-1">Estado: Activo · Alcance: ${r.is_admin_role ? 'Comunal' : 'Delegación asignada'}</small></td>
                    <td>${permsHtml}</td>
                    <td class="text-center">
                        <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 0.80rem;" title="${escapeHtml((r.users_sample || []).join(', ') || 'Sin funcionarios vinculados')}">
                            ${r.users_count || 0}
                        </span>
                    </td>
                    <td class="text-end">
                        <div class="d-inline-flex align-items-center gap-1">
                            <button class="btn-action-icon btn-action-edit" onclick="abrirModalRol('editar', ${r.id})" title="Editar rol y permisos">
                                <i class="bi bi-pencil" style="color: #1B365D;"></i>
                            </button>
                            <button class="btn-action-icon" style="color: #64748B;" onclick="duplicarRol(${r.id})" title="Duplicar rol">
                                <i class="bi bi-copy"></i>
                            </button>
                            ${btnDelete}
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Actualizar info de registros y paginador
            const info = document.getElementById('lblRegistrosInfoRoles');
            if (info) info.textContent = `${inicio + 1}-${Math.min(fin, total)} de ${total} roles`;
            actualizarPaginadorRoles(total);
        }

        function cambiarFilasPorPaginaRoles(val) {
            filasPorPaginaRoles = parseInt(val) || 10;
            paginaActualRoles = 1;
            renderTablaRoles();
        }

        function actualizarPaginadorRoles(total) {
            const container = document.getElementById('paginadorPillsRoles');
            if (!container) return;
            container.innerHTML = '';
            const totalPaginas = Math.ceil(total / filasPorPaginaRoles);
            if (totalPaginas <= 1) return;

            for (let i = 1; i <= totalPaginas; i++) {
                const btn = document.createElement('button');
                btn.className = `page-pill ${i === paginaActualRoles ? 'active' : ''}`;
                btn.textContent = i;
                btn.onclick = () => {
                    paginaActualRoles = i;
                    renderTablaRoles();
                };
                container.appendChild(btn);
            }
        }

        // ==============================================================================
        // MATRIZ DE PERMISOS EN EL MODAL DE CREACIÓN / EDICIÓN
        // ==============================================================================

        function renderPermisosMatrix(selectedPerms = []) {
            const container = document.getElementById('contenedorModulosPermisos');
            if (!container) return;
            container.innerHTML = '';

            const selectedSet = new Set(selectedPerms || []);

            datasetCatalogPermisos.forEach((mod, moduleIndex) => {
                const col = document.createElement('div');
                col.className = 'col-12';

                // Checkbox items
                let permsInputs = '';
                let modTotalCount = mod.permissions.length;
                let modCheckedCount = 0;

                mod.permissions.forEach(p => {
                    const isChecked = selectedSet.has(p.code);
                    if (isChecked) modCheckedCount++;
                    permsInputs += `
                        <div class="col-12">
                            <label class="perm-checkbox-item">
                                <input type="checkbox" name="rolPermisoCheckbox" data-module="${mod.module_id}" value="${p.code}" ${isChecked ? 'checked' : ''} onchange="actualizarContadorPermisosModal()">
                                <div>
                                    <div class="fw-bold" style="font-size: 0.82rem; color: var(--muni-navy);">${p.name}</div>
                                    <div class="text-muted" style="font-size: 0.72rem; line-height: 1.2;">${p.desc}</div>
                                </div>
                            </label>
                        </div>
                    `;
                });

                const allModChecked = (modCheckedCount === modTotalCount && modTotalCount > 0);

                col.innerHTML = `
                    <details class="perm-module-card role-permission-accordion">
                        <summary class="d-flex align-items-center justify-content-between gap-3">
                            <div class="d-flex align-items-center gap-2 flex-grow-1" style="min-width:0">
                                <i class="bi ${mod.icon || 'bi-folder'} text-primary fs-5"></i>
                                <div style="min-width:0">
                                    <h6 class="fw-bold m-0" style="font-size: 0.90rem; color: var(--muni-navy);">${mod.module_name}</h6>
                                    <span class="text-muted text-truncate d-block" style="font-size: 0.70rem;">${mod.description}</span>
                                </div>
                            </div>
                            <span class="badge bg-light text-primary border flex-shrink-0" id="count-module-${mod.module_id}">${modCheckedCount}/${modTotalCount}</span>
                            <button type="button" class="btn btn-sm btn-outline-muni-red rounded-pill px-2 flex-shrink-0" onclick="event.preventDefault(); event.stopPropagation(); toggleModuloCompleto('${mod.module_id}', this)">
                                ${allModChecked ? 'Desmarcar' : 'Todos'}
                            </button>
                            <i class="bi bi-chevron-down permission-chevron flex-shrink-0"></i>
                        </summary>
                        <div class="row g-2 pt-3 mt-2 border-top" id="mod-container-${mod.module_id}">
                            ${permsInputs}
                        </div>
                    </details>
                `;
                container.appendChild(col);
            });

            actualizarContadorPermisosModal();
        }

        function toggleModuloCompleto(moduleId, btn) {
            const container = document.getElementById(`mod-container-${moduleId}`);
            if (!container) return;
            const checkboxes = container.querySelectorAll('input[type="checkbox"]');
            const shouldCheck = btn.textContent.trim() === 'Todos';
            checkboxes.forEach(cb => cb.checked = shouldCheck);
            btn.textContent = shouldCheck ? 'Desmarcar' : 'Todos';
            actualizarContadorPermisosModal();
        }

        function actualizarContadorPermisosModal() {
            const checkboxes = document.querySelectorAll('input[name="rolPermisoCheckbox"]:checked');
            const allCheckboxes = document.querySelectorAll('input[name="rolPermisoCheckbox"]');
            const count = checkboxes.length;
            const total = allCheckboxes.length || 40;
            const lbl = document.getElementById('lblModalPermsCount');
            datasetCatalogPermisos.forEach(mod => {
                const selected = document.querySelectorAll(`input[name="rolPermisoCheckbox"][data-module="${mod.module_id}"]:checked`).length;
                const moduleCount = document.getElementById(`count-module-${mod.module_id}`);
                if (moduleCount) moduleCount.textContent = `${selected}/${mod.permissions.length}`;
            });
            if (lbl) {
                lbl.textContent = `${count} de ${total} permisos seleccionados`;
                if (count === total) {
                    lbl.className = 'badge bg-danger text-white border px-3 py-2 fs-7 fw-bold';
                    lbl.innerHTML = `<i class="bi bi-shield-fill-check me-1"></i> Acceso Total (${count}/${total})`;
                } else {
                    lbl.className = 'badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-2 fs-7 fw-bold';
                }
            }
        }

        function aplicarPlantillaPermisos(tipo) {
            const allCbs = document.querySelectorAll('input[name="rolPermisoCheckbox"]');
            if (tipo === 'admin') {
                allCbs.forEach(cb => cb.checked = true);
                mostrarToast('Plantilla Administrador aplicada.');
            } else if (tipo === 'operador') {
                allCbs.forEach(cb => {
                    const v = cb.value;
                    cb.checked = v.startsWith('atenciones.') || v.startsWith('vecinos.') || v.startsWith('tipo_atencion.view') || v.startsWith('delegaciones.view') || v.startsWith('reportes.view');
                });
                mostrarToast('Plantilla Operador aplicada.');
            } else if (tipo === 'consultor') {
                allCbs.forEach(cb => {
                    cb.checked = cb.value.endsWith('.view');
                });
                mostrarToast('Plantilla Solo Lectura aplicada.');
            }
            actualizarContadorPermisosModal();
        }

        function invertirSeleccionPermisos() {
            const allCbs = document.querySelectorAll('input[name="rolPermisoCheckbox"]');
            allCbs.forEach(cb => cb.checked = !cb.checked);
            actualizarContadorPermisosModal();
            mostrarToast('Selección invertida.');
        }

        function desmarcarTodosPermisos() {
            const allCbs = document.querySelectorAll('input[name="rolPermisoCheckbox"]');
            allCbs.forEach(cb => cb.checked = false);
            actualizarContadorPermisosModal();
            mostrarToast('Permisos desmarcados.');
        }

        function abrirModalRol(modo, rolId = null) {
            const elId = document.getElementById('rolFormId');
            const elNom = document.getElementById('rolFormNombre');
            const elDesc = document.getElementById('rolFormDescripcion');
            const elTitle = document.getElementById('modalRolTitle');

            if (modo === 'nuevo') {
                if (elId) elId.value = '';
                if (elNom) { elNom.value = ''; elNom.disabled = false; }
                if (elDesc) elDesc.value = '';
                if (elTitle) elTitle.innerHTML = `<i class="bi bi-person-plus-fill text-warning me-2"></i> Nuevo Rol`;
                // Por defecto plantilla operador para roles nuevos
                renderPermisosMatrix([
                    'atenciones.view', 'atenciones.create', 'atenciones.edit',
                    'vecinos.view', 'vecinos.create', 'reportes.view'
                ]);
            } else {
                const rol = datasetRoles.find(r => r.id === rolId);
                if (!rol) return;
                if (elId) elId.value = rol.id;
                if (elNom) {
                    elNom.value = rol.name;
                    elNom.disabled = rol.is_system && (rol.name === 'Administrador' || rol.name === 'Operador' || rol.name === 'Consultor');
                }
                if (elDesc) elDesc.value = rol.description || '';
                if (elTitle) elTitle.innerHTML = `<i class="bi bi-pencil-square text-warning me-2"></i> Editar Rol: ${rol.name}`;
                renderPermisosMatrix(rol.permissions || []);
            }

            if (bsModalRol) bsModalRol.show();
        }

        async function ejecutarGuardarRol() {
            const elId = document.getElementById('rolFormId');
            const id = elId ? elId.value : '';
            const elNom = document.getElementById('rolFormNombre');
            const name = (elNom && elNom.value) ? elNom.value.trim() : '';
            const elDesc = document.getElementById('rolFormDescripcion');
            const description = (elDesc && elDesc.value) ? elDesc.value.trim() : '';

            if (!name || !description) {
                Swal.fire({icon: 'warning', title: 'Campos requeridos', text: 'Indica el nombre y la descripción del rol.'});
                return;
            }

            const checkedPerms = [];
            document.querySelectorAll('input[name="rolPermisoCheckbox"]:checked').forEach(cb => {
                checkedPerms.push(cb.value);
            });

            const payload = {
                name: name,
                description: description,
                permissions: checkedPerms,
                is_system: false
            };

            const url = id ? `/api/roles/${id}/update/` : '/api/roles/create/';
            const method = 'POST';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (!data.success) throw new Error(data.message || 'Error al procesar la solicitud');

                if (id) {
                    const idx = datasetRoles.findIndex(r => r.id === parseInt(id));
                    if (idx !== -1) {
                        datasetRoles[idx].name = name;
                        datasetRoles[idx].description = description;
                        datasetRoles[idx].permissions = checkedPerms;
                        datasetRoles[idx].permissions_count = checkedPerms.length;
                    }
                } else if (data.role) {
                    datasetRoles.push(data.role);
                }

                renderTarjetasPermisosRoles(datasetRoles);
                if (bsModalRol) bsModalRol.hide();
                filtrarRoles();
                mostrarToast(data.message || (id ? 'Rol actualizado exitosamente.' : 'Rol creado exitosamente.'));
            } catch (err) {
                console.error("Error al guardar rol:", err);
                Swal.fire({icon: 'error', title: 'No se guardó el rol', text: err.message || 'No fue posible guardar los cambios en la base de datos.', confirmButtonColor: '#A30F32'});
            }
        }

        function guardarRolSubmit(e) {
            e.preventDefault();
            ejecutarGuardarRol();
        }

        // ==============================================================================
        // ELIMINACIÓN DE ROL
        // ==============================================================================

        function abrirModalEliminarRol(rolId) {
            const rol = datasetRoles.find(r => r.id === rolId);
            if (!rol) return;
            rolEliminarId = rolId;

            const elNombre = document.getElementById('lblEliminarRolNombre');
            const elAviso = document.getElementById('lblEliminarRolAviso');
            const elDetalle = document.getElementById('boxEliminarRolDetalle');
            const btnConfirm = document.getElementById('btnConfirmarEliminarRol');

            if (elNombre) elNombre.textContent = `¿Eliminar el rol "${rol.name}"?`;

            const isCoreProtected = rol.is_system || rol.name === 'Administrador';
            const hasUsers = (rol.users_count > 0);

            if (isCoreProtected) {
                if (elAviso) elAviso.textContent = `El rol de sistema "${rol.name}" está protegido y no puede darse de baja.`;
                if (elDetalle) elDetalle.className = 'alert alert-danger py-2 text-start small mb-0';
                if (btnConfirm) btnConfirm.disabled = true;
            } else if (hasUsers) {
                if (elAviso) elAviso.textContent = `Este rol tiene ${rol.users_count} funcionario(s) asignado(s). Reasigna primero a esas personas.`;
                if (elDetalle) elDetalle.className = 'alert alert-warning py-2 text-start small mb-0';
                if (btnConfirm) btnConfirm.disabled = true;
            } else {
                if (elAviso) elAviso.textContent = `El rol "${rol.name}" dejará de mostrarse y de otorgar permisos; se conservará su registro de auditoría.`;
                if (elDetalle) elDetalle.className = 'alert alert-secondary py-2 text-start small mb-0';
                if (btnConfirm) btnConfirm.disabled = false;
            }

            if (bsModalEliminarRol) bsModalEliminarRol.show();
        }

        async function ejecutarEliminarRolConfirmado() {
            if (!rolEliminarId) return;

            try {
                const res = await fetch(`/api/roles/${rolEliminarId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    }
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.message || 'Error al eliminar el rol');

                datasetRoles = datasetRoles.filter(r => r.id !== rolEliminarId);
                renderTarjetasPermisosRoles(datasetRoles);
                if (bsModalEliminarRol) bsModalEliminarRol.hide();
                filtrarRoles();
                mostrarToast(data.message || 'Rol eliminado exitosamente.');
            } catch (err) {
                console.warn("No se pudo eliminar el rol:", err);
                Swal.fire({icon: 'error', title: 'No se eliminó el rol', text: err.message || 'La base de datos rechazó la operación.', confirmButtonColor: '#A30F32'});
            }
        }

        // ==============================================================================
        // DUPLICAR ROL
        // ==============================================================================

        async function duplicarRol(rolId) {
            const origen = datasetRoles.find(r => r.id === rolId);
            if (!origen) return;

            try {
                const res = await fetch(`/api/roles/${rolId}/duplicate/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify({ name: `${origen.name} (Copia)` })
                });
                const data = await res.json();
                if (!data.success || !data.role) throw new Error(data.message || 'La base de datos no confirmó la duplicación.');
                datasetRoles.push(data.role);
                renderTarjetasPermisosRoles(datasetRoles);
                filtrarRoles();
                mostrarToast(`Rol duplicado como "${origen.name} (Copia)".`);
            } catch (err) {
                Swal.fire({icon: 'error', title: 'No se duplicó el rol', text: err.message || 'No fue posible guardar la copia en la base de datos.', confirmButtonColor: '#A30F32'});
            }
        }

        // ==============================================================================
        // VER FICHA DE PRIVILEGIOS DE UN ROL
        // ==============================================================================

        function abrirModalVerPermisos(rolId) {
            const rol = datasetRoles.find(r => r.id === rolId);
            if (!rol) return;

            const elNombre = document.getElementById('lblVerRolNombre');
            const elDesc = document.getElementById('lblVerRolDesc');
            const elNivel = document.getElementById('lblVerRolNivel');
            const elTotal = document.getElementById('lblVerRolTotalPerms');
            const elUsrInfo = document.getElementById('lblVerRolUsuariosInfo');
            const container = document.getElementById('contenedorFichaPermisosDetalle');

            if (elNombre) elNombre.textContent = rol.name;
            if (elDesc) elDesc.textContent = rol.description || 'Sin descripción';
            if (elNivel) {
                elNivel.textContent = rol.is_system ? 'Rol de Sistema (Protegido)' : 'Rol Personalizado';
                elNivel.className = rol.is_system ? 'badge bg-danger mb-1' : 'badge bg-info mb-1';
            }
            if (elTotal) elTotal.textContent = rol.permissions_count || 0;
            if (elUsrInfo) {
                const sample = (rol.users_sample || []).join(', ');
                elUsrInfo.textContent = `${rol.users_count || 0} funcionarios asignados ${sample ? `(${sample})` : ''}`;
            }

            if (container) {
                container.innerHTML = '';
                const permsSet = new Set(rol.permissions || []);

                datasetCatalogPermisos.forEach(mod => {
                    const modPerms = mod.permissions || [];
                    const authorizedPerms = modPerms.filter(p => permsSet.has(p.code));

                    const card = document.createElement('div');
                    card.className = 'card border-0 shadow-sm rounded-3 p-3 bg-white mb-2';

                    let permsListHtml = '';
                    modPerms.forEach(p => {
                        const isGranted = permsSet.has(p.code);
                        permsListHtml += `
                            <div class="col-md-6">
                                <div class="d-flex align-items-center gap-2 p-1 rounded" style="background: ${isGranted ? '#F0FDF4' : '#F8FAFC'}; font-size: 0.80rem;">
                                    <i class="bi ${isGranted ? 'bi-check-circle-fill text-success' : 'bi-x-circle text-muted'}"></i>
                                    <span class="${isGranted ? 'fw-bold text-dark' : 'text-muted text-decoration-line-through'}">${p.name}</span>
                                </div>
                            </div>
                        `;
                    });

                    card.innerHTML = `
                        <div class="d-flex align-items-center justify-content-between mb-2 pb-2 border-bottom">
                            <div class="d-flex align-items-center gap-2">
                                <i class="bi ${mod.icon || 'bi-folder'} text-primary"></i>
                                <strong style="color: var(--muni-navy); font-size: 0.88rem;">${mod.module_name}</strong>
                            </div>
                            <span class="badge ${authorizedPerms.length > 0 ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-light text-muted border'}">
                                ${authorizedPerms.length} / ${modPerms.length} activos
                            </span>
                        </div>
                        <div class="row g-1">
                            ${permsListHtml}
                        </div>
                    `;
                    container.appendChild(card);
                });
            }

            if (bsModalVerPermisosRol) bsModalVerPermisosRol.show();
        }

        // ==============================================================================
        // AGREGAR NUEVA FUNCIÓN DINÁMICA AL SISTEMA (MYADMIN POWER)
        // ==============================================================================

        function abrirModalNuevaFuncion() {
            const form = document.getElementById('formNuevaFuncion');
            if (form) form.reset();
            if (bsModalNuevaFuncion) bsModalNuevaFuncion.show();
        }

        async function ejecutarGuardarNuevaFuncion() {
            const elMod = document.getElementById('nuevaFuncionModulo');
            const moduleId = elMod ? elMod.value : '';
            const elCode = document.getElementById('nuevaFuncionCodigo');
            const code = (elCode && elCode.value) ? elCode.value.trim() : '';
            const elName = document.getElementById('nuevaFuncionNombre');
            const name = (elName && elName.value) ? elName.value.trim() : '';
            const elDesc = document.getElementById('nuevaFuncionDesc');
            const desc = (elDesc && elDesc.value) ? elDesc.value.trim() : '';

            if (!moduleId || !code || !name) {
                Swal.fire({icon: 'warning', title: 'Campos requeridos', text: 'Selecciona el módulo e indica el código y nombre de la función.'});
                return;
            }

            try {
                const res = await fetch('/api/roles/permissions/add-custom/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify({ module_id: moduleId, code, name, desc })
                });
                const data = await res.json();
                if (!res.ok || data.success !== true || !Array.isArray(data.catalog)) {
                    throw new Error(data.message || 'El servidor no confirmó el guardado.');
                }
                datasetCatalogPermisos = data.catalog;

                // Darle automáticamente la nueva función al Administrador
                const adminRol = datasetRoles.find(r => r.name === 'Administrador');
                if (adminRol && !adminRol.permissions.includes(code)) {
                    adminRol.permissions.push(code);
                    adminRol.permissions_count = adminRol.permissions.length;
                }

                if (bsModalNuevaFuncion) bsModalNuevaFuncion.hide();
                filtrarRoles();
                mostrarToast(`Nueva función "${name}" agregada exitosamente.`);
            } catch (err) {
                Swal.fire({icon: 'error', title: 'No se guardó la función', text: err.message || 'Comprueba tu conexión e inténtalo otra vez.'});
            }
        }

        function guardarNuevaFuncionSubmit(e) {
            e.preventDefault();
            ejecutarGuardarNuevaFuncion();
        }

        // ==============================================================================
        // MATRIZ TRANSVERSAL GLOBAL (PHP-MYADMIN STYLE)
        // ==============================================================================

        function abrirModalMatrizMyAdmin() {
            const thead = document.getElementById('tablaMatrizTransversalHead');
            const tbody = document.getElementById('tablaMatrizTransversalBody');
            if (!thead || !tbody) return;

            // Encabezados con todos los roles activos
            let headHtml = `
                <tr>
                    <th class="sticky-col" style="min-width: 250px;">Módulo / Privilegio</th>
            `;
            datasetRoles.forEach(r => {
                headHtml += `<th style="min-width: 130px;">
                    <div class="fw-bold" style="font-size: 0.82rem; color: var(--muni-navy);">${escapeHtml(r.name)}</div>
                    <span class="text-muted" style="font-size: 0.68rem;">${r.permissions_count || 0} perms</span>
                </th>`;
            });
            headHtml += `</tr>`;
            thead.innerHTML = headHtml;

            // Filas con todos los permisos agrupados por módulo
            let bodyHtml = '';
            datasetCatalogPermisos.forEach(mod => {
                bodyHtml += `
                    <tr style="background: rgba(241, 245, 249, 0.95); font-weight: bold;">
                        <td class="sticky-col" style="background: #E2E8F0;" colspan="${datasetRoles.length + 1}">
                            <i class="bi ${mod.icon || 'bi-folder'} text-primary me-2"></i> ${mod.module_name}
                        </td>
                    </tr>
                `;

                (mod.permissions || []).forEach(p => {
                    bodyHtml += `
                        <tr>
                            <td class="sticky-col">
                                <div class="fw-bold text-dark" style="font-size: 0.80rem;">${p.name}</div>
                                <code style="font-size: 0.70rem; color: var(--muni-text-sec);">${p.code}</code>
                            </td>
                    `;

                    datasetRoles.forEach(r => {
                        const isChecked = (r.permissions || []).includes(p.code);
                        bodyHtml += `
                            <td>
                                <input type="checkbox" class="myadmin-toggle-switch" data-role-id="${r.id}" data-perm-code="${escapeHtml(p.code)}" aria-label="${escapeHtml(p.name)} para ${escapeHtml(r.name)}" ${isChecked ? 'checked' : ''} ${r.is_system || r.is_admin_role ? 'disabled title="Rol de sistema protegido; usa sus controles generales habilitados"' : ''}>
                            </td>
                        `;
                    });

                    bodyHtml += `</tr>`;
                });
            });

            tbody.innerHTML = bodyHtml;
            if (bsModalMatrizMyAdmin) bsModalMatrizMyAdmin.show();
        }

        async function guardarMatrizTransversalGlobal() {
            const table = document.getElementById('tablaMatrizTransversal');
            if (!table || table.dataset.saving === 'true') return;

            const checkboxes = table.querySelectorAll('input.myadmin-toggle-switch');
            const rolePermsMap = {};

            checkboxes.forEach(cb => {
                const roleId = parseInt(cb.getAttribute('data-role-id'));
                const permCode = cb.getAttribute('data-perm-code');
                if (!rolePermsMap[roleId]) rolePermsMap[roleId] = [];
                if (cb.checked) {
                    rolePermsMap[roleId].push(permCode);
                }
            });

            table.dataset.saving = 'true';
            const failures = [];
            // Cada respuesta debe confirmar persistencia antes de actualizar la vista.
            let updatedCount = 0;
            for (const [rId, perms] of Object.entries(rolePermsMap)) {
                const role = datasetRoles.find(r => r.id === parseInt(rId));
                if (role && !role.is_system && !role.is_admin_role) {
                    const displayed = new Set([...checkboxes].filter(cb => Number(cb.dataset.roleId) === Number(rId)).map(cb => cb.dataset.permCode));
                    const complete = [...new Set([...perms, ...(role.permissions || []).filter(code => !displayed.has(code))])];
                    if (JSON.stringify([...complete].sort()) === JSON.stringify([...(role.permissions || [])].sort())) continue;
                    try {
                        const response = await fetch(`/api/roles/${rId}/update/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken') || ''
                            },
                            body: JSON.stringify({
                                name: role.name,
                                description: role.description,
                                permissions: complete
                            })
                        });
                        const data = await response.json();
                        if (!response.ok || data.success !== true) throw new Error(data.message || 'Guardado rechazado.');
                        updatedCount++;
                    } catch (e) {
                        failures.push(`${role.name}: ${e.message}`);
                    }
                }
            }

            table.dataset.saving = 'false';
            await initRolesView(false);
            if (failures.length) {
                Swal.fire({icon: 'error', title: 'Hay cambios sin guardar', text: `${updatedCount} roles guardados. ${failures.join(' ')}`});
                abrirModalMatrizMyAdmin();
            } else {
                if (bsModalMatrizMyAdmin) bsModalMatrizMyAdmin.hide();
                mostrarToast(updatedCount ? `Matriz guardada: ${updatedCount} roles actualizados.` : 'No hay cambios pendientes.');
            }
        }

        // ==============================================================================
        // EXPORTACIÓN DE ROLES (EXCEL & PDF OFICIAL LA SERENA)
        // ==============================================================================

        function exportarExcelRoles() {
            try {
                if (typeof XLSX === 'undefined') throw new Error("Librería SheetJS no disponible");

                const rows = filasFiltradasRoles.map((r, i) => ({
                    '#': i + 1,
                    'Nombre del Rol': r.name,
                    'Descripción Institucional': r.description || '',
                    'Tipo': r.is_system ? 'Sistema (Protegido)' : 'Personalizado',
                    'Funcionarios Asignados': r.users_count || 0,
                    'Total Privilegios': r.permissions_count || 0,
                    'Privilegios y Funciones Autorizadas': (r.permissions || []).join(', ')
                }));

                const ws = XLSX.utils.json_to_sheet(rows);
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, "Roles_SGR");
                XLSX.writeFile(wb, `Roles_Matriz_Permisos_La_Serena_${new Date().toISOString().slice(0, 10)}.xlsx`);
                mostrarToast('✓ Planilla Excel de roles descargada.');
            } catch (err) {
                console.error("Error al exportar Excel de roles:", err);
                mostrarToast('⚠ Error al generar Excel: ' + err.message);
            }
        }

        function exportarPDFRoles() {
            try {
                if (typeof window.jspdf === 'undefined') throw new Error("Librería jsPDF no disponible");
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });

                // Franja Institucional Roja
                doc.setFillColor(196, 18, 48);
                doc.rect(0, 0, 297, 8, 'F');

                // Encabezado
                doc.setFont("helvetica", "bold");
                doc.setFontSize(16);
                doc.setTextColor(27, 54, 93);
                doc.text("ILUSTRE MUNICIPALIDAD DE LA SERENA", 14, 20);

                doc.setFontSize(11);
                doc.setFont("helvetica", "normal");
                doc.setTextColor(91, 107, 130);
                doc.text("Sistema Municipal de Atención Ciudadana (SGR) — Matriz Institucional de Roles y Permisos", 14, 26);

                doc.setFontSize(9);
                doc.text(`Fecha de emisión: ${new Date().toLocaleDateString('es-CL')} | Total Roles: ${filasFiltradasRoles.length}`, 14, 32);

                const tableBody = filasFiltradasRoles.map((r, i) => [
                    i + 1,
                    r.name,
                    r.description || '',
                    r.is_system ? 'Sistema' : 'Personalizado',
                    r.users_count || 0,
                    r.permissions_count || 0,
                    (r.permissions || []).slice(0, 5).join(', ') + (r.permissions && r.permissions.length > 5 ? ` (+${r.permissions.length - 5} más)` : '')
                ]);

                doc.autoTable({
                    head: [['#', 'Nombre del Rol', 'Descripción', 'Tipo', 'Usuarios', 'Permisos', 'Módulos y Funciones Clave']],
                    body: tableBody,
                    startY: 36,
                    theme: 'grid',
                    headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
                    bodyStyles: { fontSize: 8, textColor: [23, 53, 107] },
                    alternateRowStyles: { fillColor: [248, 250, 252] },
                    columnStyles: {
                        0: { cellWidth: 10, halign: 'center' },
                        1: { cellWidth: 38, fontStyle: 'bold' },
                        2: { cellWidth: 55 },
                        3: { cellWidth: 26, halign: 'center' },
                        4: { cellWidth: 18, halign: 'center' },
                        5: { cellWidth: 18, halign: 'center' },
                        6: { cellWidth: 'auto' }
                    }
                });

                doc.save(`Matriz_Roles_Permisos_La_Serena_${new Date().toISOString().slice(0, 10)}.pdf`);
                mostrarToast('✓ Informe PDF de roles descargado con éxito.');
            } catch (err) {
                console.error("Error al exportar PDF de roles:", err);
                mostrarToast('⚠ Error al generar PDF: ' + err.message);
            }
        }

        let toastT;
        function mostrarToast(msg) {
            let iconType = 'success';
            if (msg.includes('⚠') || msg.toLowerCase().includes('error')) {
                iconType = 'error';
            } else if (msg.includes('Info') || msg.includes('Cargando') || msg.includes('Descargando') || msg.includes('Generando')) {
                iconType = 'info';
            } else if (msg.includes('⏸') || msg.includes('Aviso')) {
                iconType = 'warning';
            }
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 3500,
                    timerProgressBar: true,
                    icon: iconType,
                    title: msg.replace(/✓ |⚠ |⏸ /g, '')
                });
            } else {
                console.log('[Toast]:', msg);
            }
        }
        function cerrarToast() { }

        /* ==========================================================================
           MÓDULO: ATENCIONES CIUDADANAS Y CASOS SOCIALES (PERSISTENCIA MYSQL REAL)
           ========================================================================== */
        async function cargarAtencionesDB() {
            try {
                const resp = await fetch('/api/atenciones/');
                if (!resp.ok) throw new Error('Error al consultar atenciones');
                const data = await resp.json();
                if (data.success && Array.isArray(data.atenciones)) {
                    datasetAtenciones = data.atenciones;
                    window.datasetAtenciones = datasetAtenciones;
                    if (!controlesPaginacionAtencionesInicializados) {
                        const size = document.getElementById('tamanoPaginaAtenciones');
                        size?.addEventListener('change', () => {
                            filasPorPaginaAtenciones = Math.min(50, Math.max(10, Number(size.value) || 10));
                            paginaActualAtenciones = 1;
                            filtrarAtenciones();
                        });
                        document.getElementById('paginaAnteriorAtenciones')?.addEventListener('click', () => {
                            paginaActualAtenciones = Math.max(1, paginaActualAtenciones - 1);
                            filtrarAtenciones(false);
                        });
                        document.getElementById('paginaSiguienteAtenciones')?.addEventListener('click', () => {
                            paginaActualAtenciones += 1;
                            filtrarAtenciones(false);
                        });
                        controlesPaginacionAtencionesInicializados = true;
                    }
                    renderTablaAtenciones(datasetAtenciones);
                }
            } catch (err) {
                console.error('Error cargando atenciones desde MySQL:', err);
                const tbody = document.getElementById('tablaAtencionesBody');
                if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">No se pudieron cargar las atenciones. Inténtalo nuevamente.</td></tr>';
                if (document.getElementById('view-atenciones')?.classList.contains('active') && window.Swal) {
                    Swal.fire({icon: 'error', title: 'Atenciones no disponibles', text: 'No se pudo consultar el listado. Revisa la conexión e inténtalo nuevamente.'});
                }
            }
        }

        function renderTablaAtenciones(items) {
            const tbody = document.getElementById('tablaAtencionesBody');
            const totalLbl = document.getElementById('lblTotalAtenciones');
            if (!tbody) return;

            if (totalLbl) totalLbl.textContent = items.length;
            const pages = Math.max(1, Math.ceil(items.length / filasPorPaginaAtenciones));
            paginaActualAtenciones = Math.min(paginaActualAtenciones, pages);
            const start = items.length ? (paginaActualAtenciones - 1) * filasPorPaginaAtenciones + 1 : 0;
            const end = Math.min(items.length, paginaActualAtenciones * filasPorPaginaAtenciones);
            const info = document.getElementById('paginacionInfoAtenciones');
            const previous = document.getElementById('paginaAnteriorAtenciones');
            const next = document.getElementById('paginaSiguienteAtenciones');
            if (info) info.textContent = `Mostrando ${start}-${end} de ${items.length} · Página ${paginaActualAtenciones} de ${pages}`;
            if (previous) previous.disabled = paginaActualAtenciones <= 1;
            if (next) next.disabled = paginaActualAtenciones >= pages;

            if (items.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-4 text-muted">
                            <i class="bi bi-inbox fs-2 d-block mb-1 text-secondary"></i>
                            No se encontraron atenciones ciudadanas registradas.
                        </td>
                    </tr>`;
                return;
            }

            const escapeCell = (value) => {
                const span = document.createElement('span');
                span.textContent = value == null ? '' : String(value);
                return span.innerHTML;
            };

            const visibleItems = items.slice(start - 1, end);
            tbody.innerHTML = visibleItems.map((a) => {
                const badgeClass = a.status === 'Approved' ? 'bg-success-subtle text-success border-success-subtle' :
                                   ['Rejected', 'Requires correction'].includes(a.status) ? 'bg-danger-subtle text-danger border-danger-subtle' :
                                   'bg-warning-subtle text-warning-emphasis border-warning-subtle';
                const statusName = a.status === 'Approved' ? 'Aprobada' :
                                   a.status === 'Rejected' ? 'Rechazada' :
                                   a.status === 'Requires correction' ? 'Req. Corrección' : 'En Revisión';
                const stageText = a.stage ? `Etapa ${a.stage} de 3` : 'Etapa 1 de 3';
                const dateText = a.date || 'Sin fecha';
                const linkedCase = Boolean(a.social_case_id);

                return `
                    <tr style="border-bottom: 1px solid #E2E8F0;">
                        <td class="py-2.5 px-2 text-truncate">
                            <span class="badge bg-light text-dark border px-1.5 py-1 font-monospace fw-bold" style="font-size: 0.74rem;">
                                ${escapeCell(a.evidence_code || ('ACT-' + String(a.id).padStart(4, '0')))}
                            </span>
                        </td>
                        <td class="py-2.5 px-2">
                            <div class="text-truncate" style="min-width: 0;">
                                <strong class="d-block text-truncate" style="color: #0F172A; font-size: 0.82rem;">${escapeCell(a.contact_name || 'Sin nombre')}</strong>
                                <span class="d-block text-muted text-truncate" style="font-size: 0.70rem;">${escapeCell(a.contact_phone || 'Sin teléfono')}</span>
                            </div>
                        </td>
                        <td class="py-2.5 px-2 text-truncate">
                            <span class="fw-semibold text-dark text-truncate d-block" style="font-size: 0.78rem;" title="${escapeCell(a.delegation || 'Sin delegación')}">
                                ${escapeCell((a.delegation || 'Sin delegación').replace('Delegación ', ''))}
                            </span>
                        </td>
                        <td class="py-2.5 px-2 text-truncate">
                            <span class="fw-semibold text-dark d-block text-truncate" style="font-size: 0.80rem;">${escapeCell(a.attention_type || a.service || a.title || 'Atención')}</span>
                            <span class="d-block text-muted text-truncate" style="font-size: 0.70rem;">${escapeCell(a.subattention_type || a.description || 'Sin subatención')}</span>
                            ${linkedCase ? `<span class="badge bg-info-subtle text-info-emphasis border border-info-subtle mt-1">Caso social #${escapeCell(a.social_case_id)}</span>` : ''}
                        </td>
                        <td class="py-2.5 px-1 text-center text-truncate">
                            <span class="badge rounded-pill bg-primary-subtle text-primary border border-primary-subtle fw-bold" style="font-size: 0.70rem; padding: 3px 6px;">
                                ${stageText}
                            </span>
                        </td>
                        <td class="py-2.5 px-1 text-center text-muted" style="font-size: 0.74rem;">
                            ${dateText}
                        </td>
                        <td class="py-2.5 px-2 text-center text-truncate">
                            <span class="badge rounded-pill fw-bold border ${badgeClass}" style="font-size: 0.72rem; padding: 4px 8px;">
                                ${statusName}
                            </span>
                        </td>
                        <td class="py-2.5 px-1 text-center text-nowrap atencion-row-actions">
                            <div class="d-inline-flex align-items-center justify-content-center gap-1 flex-nowrap">
                                <button class="btn btn-sm catalog-action-btn btn-action-ver" onclick="verExpedienteAtencion(${Number(a.id)})" title="Ver detalle">Ver</button>
                                ${linkedCase ? '<span class="small text-muted" title="Este registro se gestiona como caso social">Gestión social</span>' : `
                                <button class="btn btn-sm catalog-action-btn btn-action-editar" onclick="editarAtencion(${Number(a.id)})" title="Editar registro">Editar</button>
                                <button class="btn btn-sm catalog-action-btn btn-action-baja" onclick="eliminarAtencion(${Number(a.id)})" title="Dar de baja">Baja</button>`}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        let catalogsForAttentionForm = null;

        async function cargarCatalogosFormularioAtencion(forceRefresh = false) {
            if (forceRefresh) catalogsForAttentionForm = null;
            if (catalogsForAttentionForm) return catalogsForAttentionForm;
            catalogsForAttentionForm = (async () => {
                const [delegationResponse, typeResponse, subResponse] = await Promise.all([
                    fetch('/api/delegations/', { credentials: 'same-origin', headers: { Accept: 'application/json' } }),
                    fetch('/api/catalogs/attention-types/?page_size=50', { credentials: 'same-origin', headers: { Accept: 'application/json' } }),
                    fetch('/api/catalogs/subattentions/?page_size=50', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
                ]);
                if (!delegationResponse.ok || !typeResponse.ok || !subResponse.ok) {
                    catalogsForAttentionForm = null;
                    throw new Error('No se pudieron cargar las delegaciones y catálogos autorizados. Recarga la página e inténtalo de nuevo.');
                }
                const [delegationData, typeData, subData] = await Promise.all([
                    delegationResponse.json(), typeResponse.json(), subResponse.json()
                ]);
                const delegationSelect = document.getElementById('selAtencionDelegacion');
                const typeSelect = document.getElementById('selAtencionTipo');
                const subSelect = document.getElementById('selAtencionSubtipo');
                const fill = (select, placeholder, records, label, filterActive = false) => {
                    if (!select) return;
                    select.replaceChildren(new Option(placeholder, ''));
                    records.filter(record => !filterActive || record.status === 'Activo').forEach(record => {
                        select.add(new Option(label(record), record.id));
                    });
                };
                fill(delegationSelect, 'Selecciona una delegación', delegationData.delegations || [], record => record.name, true);
                fill(typeSelect, 'Selecciona un tipo', typeData.results || [], record => record.name, true);
                fill(subSelect, 'Primero selecciona un tipo', subData.results || [], record => record.name, true);
                if (typeSelect && subSelect) {
                    subSelect.disabled = true;
                    typeSelect.onchange = () => {
                        const typeId = typeSelect.value;
                        let hasOptions = false;
                        [...subSelect.options].forEach(option => {
                            if (!option.value) return;
                            const record = (subData.results || []).find(item => String(item.id) === option.value);
                            const matches = Boolean(typeId) && record && String(record.attention_type) === typeId && record.status === 'Activo';
                            option.hidden = !matches;
                            option.disabled = !matches;
                            hasOptions ||= Boolean(matches);
                        });
                        subSelect.value = '';
                        subSelect.options[0].textContent = !typeId ? 'Primero selecciona un tipo' : (hasOptions ? 'Selecciona una subatención' : 'No hay subatenciones activas');
                        subSelect.disabled = !hasOptions;
                    };
                }
            })();
            return catalogsForAttentionForm;
        }

        async function cargarVecinosSelectorAtencion() {
            const select = document.getElementById('selAtencionVecino');
            if (!select) return;
            const response = await fetch('/api/vecinos/');
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.message || 'No se pudo cargar el catálogo de vecinos.');
            const selected = select.value;
            window.vecinosAtencionCatalogo = data.vecinos || [];
            select.innerHTML = '<option value="">Contacto sin ficha de vecino</option>' +
                window.vecinosAtencionCatalogo.map(vecino => `<option value="${Number(vecino.id)}">${escapeHtml(vecino.nombre)} · ${escapeHtml(vecino.rut)}</option>`).join('');
            if (selected) select.value = selected;
        }

        function completarDatosVecinoAtencion() {
            const select = document.getElementById('selAtencionVecino');
            const vecino = (window.vecinosAtencionCatalogo || []).find(row => Number(row.id) === Number(select?.value));
            if (!vecino) return;
            document.getElementById('txtAtencionNombre').value = vecino.nombre || '';
            document.getElementById('txtAtencionTelefono').value = vecino.telefono || '';
        }

        async function abrirModalNuevaAtencion(editId = null) {
            if (editId && datasetAtenciones.some(item => Number(item.id) === Number(editId) && item.social_case_id)) {
                Swal.fire({ icon: 'info', title: 'Caso social vinculado', text: 'Edita esta atención desde la gestión del caso social.' });
                return;
            }
            const form = document.getElementById('formAtencionDB');
            if (form) form.reset();
            const editInput = document.getElementById('atencionEditId');
            if (editInput) editInput.value = editId || '';
            const dateInput = document.getElementById('txtAtencionFecha');
            if (dateInput) {
                const today = new Date();
                dateInput.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
            }
            try {
                await Promise.all([cargarCatalogosFormularioAtencion(true), cargarVecinosSelectorAtencion()]);
            } catch (error) {
                if (window.Swal) Swal.fire({ icon: 'error', title: 'No se pudo preparar el formulario', text: error.message });
                return;
            }
            const title = document.getElementById('modalAtencionTitle');
            const saveButton = document.getElementById('btnGuardarAtencionDB');
            const info = document.getElementById('atencionResponsableInfo');
            if (editId) {
                const record = datasetAtenciones.find(item => Number(item.id) === Number(editId));
                if (!record) {
                    Swal.fire({ icon: 'error', title: 'Registro no disponible', text: 'Actualiza el listado e inténtalo nuevamente.' });
                    return;
                }
                document.getElementById('txtAtencionNombre').value = record.contact_name || '';
                document.getElementById('txtAtencionTelefono').value = record.contact_phone || '';
                document.getElementById('selAtencionVecino').value = record.neighbor_id || '';
                if (dateInput) dateInput.value = record.activity_date_iso || '';
                document.getElementById('selAtencionDelegacion').value = record.delegation || '';
                document.getElementById('selAtencionTipo').value = record.attention_type_id || '';
                document.getElementById('selAtencionTipo').dispatchEvent(new Event('change'));
                document.getElementById('selAtencionSubtipo').value = record.subattention_id || '';
                document.getElementById('txtAtencionProblema').value = record.problem_description || record.title || '';
                document.getElementById('txtAtencionAccion').value = record.executed_action || record.description || '';
                if (title) title.textContent = 'Editar Atención Ciudadana';
                if (saveButton) saveButton.innerHTML = '<i class="bi bi-check-lg me-1"></i> Guardar cambios';
                if (info) info.textContent = `Registro ${record.activity_code || record.id}. El estado de revisión lo mantiene el Verificador Técnico.`;
            } else {
                if (title) title.textContent = 'Registrar Nueva Atención Ciudadana';
                if (saveButton) saveButton.innerHTML = '<i class="bi bi-check-lg me-1"></i> Guardar Atención';
                if (info) info.textContent = 'El usuario y la fecha se registrarán automáticamente.';
            }
            if (bsModalNuevaAtencion) {
                bsModalNuevaAtencion.show();
            } else {
                const el = document.getElementById('modalNuevaAtencion');
                if (el && window.bootstrap) {
                    bsModalNuevaAtencion = new bootstrap.Modal(el);
                    bsModalNuevaAtencion.show();
                }
            }
        }

        async function guardarAtencionDB() {
            const editId = document.getElementById('atencionEditId')?.value;
            const contact_name = document.getElementById('txtAtencionNombre')?.value?.trim();
            const contact_phone = document.getElementById('txtAtencionTelefono')?.value?.trim();
            const activity_date = document.getElementById('txtAtencionFecha')?.value;
            const delegation = document.getElementById('selAtencionDelegacion')?.value;
            const attention_type_id = document.getElementById('selAtencionTipo')?.value;
            const subattention_id = document.getElementById('selAtencionSubtipo')?.value;
            const neighbor_id = document.getElementById('selAtencionVecino')?.value || '';
            const title = document.getElementById('txtAtencionProblema')?.value?.trim();
            const description = document.getElementById('txtAtencionAccion')?.value?.trim();

            if (!contact_name || !delegation || !activity_date || !attention_type_id || !subattention_id || !title || !description) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Campos requeridos',
                    text: 'Completa solicitante, delegación, fecha, tipo, subatención, descripción y acción realizada.'
                });
                return;
            }

            const btn = document.getElementById('btnGuardarAtencionDB');
            if (btn) btn.disabled = true;

            try {
                const resp = await fetch(editId ? `/api/atenciones/${encodeURIComponent(editId)}/` : '/api/atenciones/', {
                    method: editId ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify({
                        problem_description: title,
                        executed_action: description,
                        delegation: delegation,
                        contact_name: contact_name,
                        contact_phone: contact_phone,
                        activity_date: activity_date,
                        attention_type_id: attention_type_id,
                        subattention_id: subattention_id,
                        neighbor_id: neighbor_id
                    })
                });

                const data = await resp.json();
                if (!resp.ok || !data.success) {
                    throw new Error(data.message || 'No se pudo guardar la atención.');
                }
                if (bsModalNuevaAtencion) bsModalNuevaAtencion.hide();
                await cargarAtencionesDB();
                Swal.fire({
                    icon: 'success',
                    title: editId ? 'Cambios guardados' : 'Atención registrada',
                    text: data.message || 'La atención quedó registrada correctamente.',
                    timer: 2500,
                    showConfirmButton: false
                });
            } catch (err) {
                Swal.fire({
                    icon: 'error',
                    title: 'Error de red',
                    text: err.message
                });
            } finally {
                if (btn) btn.disabled = false;
            }
        }

        function editarAtencion(id) {
            abrirModalNuevaAtencion(id);
        }

        async function eliminarAtencion(id) {
            const record = datasetAtenciones.find(item => Number(item.id) === Number(id));
            if (!record) return;
            if (record.social_case_id) {
                Swal.fire({ icon: 'info', title: 'Caso social vinculado', text: 'Da de baja este registro desde la gestión del caso social.' });
                return;
            }
            const result = await Swal.fire({
                title: 'Dar de baja esta atención',
                text: `El registro ${record.activity_code || record.id} dejará de aparecer en el listado y conservará su trazabilidad.`,
                icon: 'warning', showCancelButton: true, confirmButtonText: 'Dar de baja',
                cancelButtonText: 'Cancelar', confirmButtonColor: '#C41230'
            });
            if (!result.isConfirmed) return;
            try {
                const response = await fetch(`/api/atenciones/${encodeURIComponent(id)}/`, {
                    method: 'DELETE', headers: { 'X-CSRFToken': getCookie('csrftoken') || '' }
                });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || 'No fue posible dar de baja la atención.');
                await cargarAtencionesDB();
                Swal.fire({ icon: 'success', title: 'Registro actualizado', text: data.message, confirmButtonColor: '#1B365D' });
            } catch (error) {
                Swal.fire({ icon: 'error', title: 'No se pudo dar de baja', text: error.message, confirmButtonColor: '#C41230' });
            }
        }

        function verExpedienteAtencion(id) {
            const a = datasetAtenciones.find(item => item.id === id);
            if (!a) {
                Swal.fire({ icon: 'info', title: 'Atención no encontrada' });
                return;
            }

            atencionSeleccionadaId = id;
            const elCod = document.getElementById('lblExpedienteCodigo');
            const elVec = document.getElementById('lblExpedienteVecino');
            const elCont = document.getElementById('lblExpedienteContacto');
            const elDel = document.getElementById('lblExpedienteDelegacion');
            const elBadge = document.getElementById('lblExpedienteBadgeEstado');
            const elProb = document.getElementById('lblExpedienteProblema');
            const elAcc = document.getElementById('lblExpedienteAccion');
            const elObs = document.getElementById('lblExpedienteObservacion');

            if (elCod) elCod.textContent = `Expediente: ${a.evidence_code || ('EVI-2026-' + a.id)}${a.social_case_id ? ` · Caso social #${a.social_case_id}` : ''}`;
            if (elVec) elVec.textContent = a.contact_name || 'Ciudadano Municipal';
            if (elCont) elCont.textContent = a.contact_phone ? `Contacto: ${a.contact_phone}` : 'Sin teléfono registrado';
            if (elDel) elDel.textContent = a.delegation || 'Delegación La Serena';
            
            if (elBadge) {
                const badgeClass = a.status === 'Approved' ? 'bg-success text-white' :
                                   ['Rejected', 'Requires correction'].includes(a.status) ? 'bg-danger text-white' : 'bg-warning text-dark';
                const statusName = a.status === 'Approved' ? 'Aprobada' :
                                   a.status === 'Rejected' ? 'Rechazada' :
                                   a.status === 'Requires correction' ? 'Req. Corrección' : 'En Revisión';
                elBadge.className = `badge rounded-pill mt-1 ${badgeClass}`;
                elBadge.textContent = statusName;
            }

            if (elProb) elProb.textContent = a.title || a.service || 'Requerimiento registrado en ventanilla territorial.';
            if (elAcc) elAcc.textContent = a.description || 'Gestión técnica y derivación comunal.';
            if (elObs) elObs.textContent = a.verifier_notes || 'Verificación conforme a reglas de negocio RN-012.';

            if (bsModalExpedienteAtencion) {
                bsModalExpedienteAtencion.show();
            } else {
                const el = document.getElementById('modalExpedienteAtencion');
                if (el && window.bootstrap) {
                    bsModalExpedienteAtencion = new bootstrap.Modal(el);
                    bsModalExpedienteAtencion.show();
                }
            }
        }

        async function cambiarEstadoAtencionRapido(newStatus) {
            if (!atencionSeleccionadaId) return;
            if (datasetAtenciones.some(item => item.id === atencionSeleccionadaId && item.social_case_id)) {
                Swal.fire({ icon: 'info', title: 'Caso social vinculado', text: 'Revisa esta solicitud desde Solicitudes sociales.' });
                return;
            }

            try {
                const resp = await fetch(`/api/atenciones/${atencionSeleccionadaId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify({ status: newStatus })
                });

                const data = await resp.json();
                if (data.success) {
                    const item = datasetAtenciones.find(it => it.id === atencionSeleccionadaId);
                    if (item) item.status = newStatus;
                    renderTablaAtenciones(datasetAtenciones);

                    const elBadge = document.getElementById('lblExpedienteBadgeEstado');
                    if (elBadge) {
                        const badgeClass = newStatus === 'Approved' ? 'bg-success text-white' :
                                           newStatus === 'Requires correction' ? 'bg-danger text-white' : 'bg-warning text-dark';
                        const statusName = newStatus === 'Approved' ? 'Aprobada' :
                                           newStatus === 'Requires correction' ? 'Req. Corrección' : 'En Revisión';
                        elBadge.className = `badge rounded-pill mt-1 ${badgeClass}`;
                        elBadge.textContent = statusName;
                    }

                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 2500,
                        icon: 'success',
                        title: `Estado actualizado a "${newStatus}" en la base de datos.`
                    });
                }
            } catch (err) {
                Swal.fire({ icon: 'error', title: 'Error al cambiar estado', text: err.message });
            }
        }

        function filtrarAtenciones(resetPage = true) {
            if (resetPage) paginaActualAtenciones = 1;
            const query = (document.getElementById('txtBuscarAtencion')?.value || '').toLowerCase().trim();
            const delegacion = (document.getElementById('selFiltroDelegacionAtencion')?.value || '').trim();
            const validacion = (document.getElementById('selFiltroValidacionAtencion')?.value || '').trim();

            const filtradas = datasetAtenciones.filter(a => {
                const matchTexto = !query ||
                    (a.contact_name && a.contact_name.toLowerCase().includes(query)) ||
                    (a.evidence_code && a.evidence_code.toLowerCase().includes(query)) ||
                    (a.title && a.title.toLowerCase().includes(query)) ||
                    (a.description && a.description.toLowerCase().includes(query));

                const matchDelegacion = !delegacion || (a.delegation && a.delegation.includes(delegacion));
                const matchValidacion = !validacion || (a.status === validacion);

                return matchTexto && matchDelegacion && matchValidacion;
            });

            renderTablaAtenciones(filtradas);
        }

        function exportarAtencionesExcel() {
            if (!datasetAtenciones || datasetAtenciones.length === 0) {
                Swal.fire({ icon: 'info', title: 'No hay datos para exportar' });
                return;
            }

            const rows = datasetAtenciones.map(a => ({
                'Código Evidencia': a.evidence_code || a.id,
                'Vecino / RUT': a.contact_name || '',
                'Teléfono': a.contact_phone || '',
                'Delegación': a.delegation || '',
                'Servicio / Requerimiento': a.title || a.service || '',
                'Acción Ejecutada': a.description || '',
                'Etapa': a.stage ? `Etapa ${a.stage}` : 'Etapa 1',
                'Fecha': a.date || '',
                'Estado Validación': a.status === 'Approved' ? 'Aprobada' : a.status === 'Requires correction' ? 'Req. Corrección' : 'En Revisión'
            }));

            const ws = XLSX.utils.json_to_sheet(rows);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, "Atenciones");
            XLSX.writeFile(wb, `Atenciones_Ciudadanas_LaSerena_${new Date().toISOString().slice(0, 10)}.xlsx`);
            mostrarToast("✓ Bitácora de atenciones exportada en Excel");
        }

        /* ==========================================================================
           MÓDULO: GESTIÓN INTERACTIVA DE PERMISOS DE ROLES (TARJETAS + MYSQL)
           ========================================================================== */
        async function toggleRolPermisoCard(rolName, permiso, switchEl) {
            const activo = switchEl.checked;
            switchEl.disabled = true;
            switchEl.closest('.role-perm-pill-toggle')?.setAttribute('aria-busy', 'true');
            try {
                const resp = await fetch('/api/roles/toggle-permiso/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify({ rol_name: rolName, permiso: permiso, enabled: activo })
                });

                const data = await resp.json();
                if (!resp.ok || data.success !== true) {
                    throw new Error(data.message || 'No se pudo guardar el permiso.');
                }
                await initRolesView(false);
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 2500,
                    icon: 'success',
                    title: data.message || `Permiso de ${permiso.toUpperCase()} ${activo ? 'activado' : 'desactivado'}`
                });
            } catch (err) {
                switchEl.checked = !activo;
                Swal.fire({
                    icon: 'error',
                    title: 'No se guardó el permiso',
                    text: err.message || 'Revisa tu conexión e inténtalo nuevamente.'
                });
            } finally {
                switchEl.disabled = false;
                switchEl.closest('.role-perm-pill-toggle')?.removeAttribute('aria-busy');
            }
        }

        /* ==========================================================================
           MÓDULO: SEGURIDAD, VALIDACIONES INSTITUCIONALES Y ANTI-INYECCIÓN
           ========================================================================== */

        // 1. Sanitizador universal contra XSS y ataques de inyección de código
        function sanitizarTexto(input) {
            if (typeof input !== 'string') return input;
            return input
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#x27;')
                .replace(/\//g, '&#x2F;')
                .trim();
        }
        window.sanitizarTexto = sanitizarTexto;

        // 2. Validador de RUT Chileno (Algoritmo Oficial Módulo 11)
        function validarRutChileno(rutCompleto) {
            if (!rutCompleto || typeof rutCompleto !== 'string') return false;
            let valor = rutCompleto.replace(/\./g, '').replace(/-/g, '').trim().toUpperCase();
            if (valor.length < 8 || valor.length > 9) return false;
            
            let cuerpo = valor.slice(0, -1);
            let dv = valor.slice(-1);
            
            if (!/^\d+$/.test(cuerpo)) return false;
            
            let suma = 0;
            let multiplo = 2;
            for (let i = cuerpo.length - 1; i >= 0; i--) {
                suma += parseInt(cuerpo.charAt(i), 10) * multiplo;
                multiplo = (multiplo === 7) ? 2 : multiplo + 1;
            }
            
            let dvEsperado = 11 - (suma % 11);
            let dvCalculado = (dvEsperado === 11) ? '0' : (dvEsperado === 10) ? 'K' : String(dvEsperado);
            
            return dv === dvCalculado;
        }
        window.validarRutChileno = validarRutChileno;

        // Formateador automático de RUT chileno (ej: 12.345.678-9)
        function formatearRutChileno(rut) {
            if (!rut) return '';
            let valor = rut.replace(/[^0-9kK]/g, '').toUpperCase();
            if (valor.length <= 1) return valor;
            let cuerpo = valor.slice(0, -1);
            let dv = valor.slice(-1);
            let formateado = '';
            while (cuerpo.length > 3) {
                formateado = '.' + cuerpo.slice(-3) + formateado;
                cuerpo = cuerpo.slice(0, -3);
            }
            return cuerpo + formateado + '-' + dv;
        }
        window.formatearRutChileno = formatearRutChileno;

        // 3. Validador de Correo Electrónico Institucional y General
        function validarEmail(email) {
            if (!email || typeof email !== 'string') return false;
            const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
            return regex.test(email.trim());
        }
        window.validarEmail = validarEmail;

        // 4. Bloqueo de números en campos de texto (Nombres, Apellidos, Títulos)
        function bloquearNumerosInput(e) {
            if (e.key && e.key.length === 1 && /[0-9]/.test(e.key)) {
                e.preventDefault();
                return false;
            }
        }
        window.bloquearNumerosInput = bloquearNumerosInput;

        // 5. Drawer Lateral de Edición Rápida (drawer_editor.html)
        let drawerActivoTipo = null;
        let drawerActivoId = null;

        function abrirAdminDrawer(tipo, id) {
            drawerActivoTipo = tipo;
            drawerActivoId = id;
            const drawer = document.getElementById('adminSlideDrawer');
            const overlay = document.getElementById('adminSlideDrawerOverlay');
            const titleEl = document.getElementById('drawerHeaderTitle');
            const subEl = document.getElementById('drawerHeaderSubtitle');
            const bodyEl = document.getElementById('drawerBodyContent');
            if (!drawer || !bodyEl) return;

            if (tipo === 'vecino') {
                const v = datasetVecinos.find(item => item.id === id);
                if (!v) return;
                if (titleEl) titleEl.textContent = 'Editar Vecino: ' + v.nombre;
                if (subEl) subEl.textContent = `RUT: ${v.rut} • Sede: ${v.territorio}`;
                bodyEl.innerHTML = `
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Nombre Completo</label>
                        <input type="text" class="form-control" id="drawerInputNombre" value="${v.nombre}" onkeypress="bloquearNumerosInput(event)">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">RUT Chileno</label>
                        <input type="text" class="form-control" id="drawerInputRut" value="${v.rut}" readonly>
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Dirección</label>
                        <input type="text" class="form-control" id="drawerInputDireccion" value="${v.direccion}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Teléfono Móvil</label>
                        <input type="text" class="form-control" id="drawerInputTelefono" value="${v.telefono}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Territorio / Delegación</label>
                        <select class="form-select" id="drawerSelectTerritorio">
                            <option value="Centro" ${v.territorio === 'Centro' ? 'selected' : ''}>Centro Histórico</option>
                            <option value="Norte" ${v.territorio === 'Norte' ? 'selected' : ''}>Las Compañías</option>
                            <option value="Sur" ${v.territorio === 'Sur' ? 'selected' : ''}>La Pampa</option>
                            <option value="Oriente" ${v.territorio === 'Oriente' ? 'selected' : ''}>La Antena - La Florida</option>
                            <option value="Costa" ${v.territorio === 'Costa' ? 'selected' : ''}>Avenida del Mar</option>
                            <option value="Rural" ${v.territorio === 'Rural' ? 'selected' : ''}>Sector Rural</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Estado</label>
                        <select class="form-select" id="drawerSelectEstado">
                            <option value="Activo" ${v.estado === 'Activo' ? 'selected' : ''}>Activo</option>
                            <option value="Inactivo" ${v.estado === 'Inactivo' ? 'selected' : ''}>Inactivo</option>
                        </select>
                    </div>
                `;
            } else if (tipo === 'usuario') {
                const u = datasetUsuarios.find(item => item.id === id);
                if (!u) return;
                if (titleEl) titleEl.textContent = 'Editar Funcionario: ' + u.full_name;
                if (subEl) subEl.textContent = `Cuenta institucional: ${u.email}`;
                bodyEl.innerHTML = `
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Nombre Funcionario</label>
                        <input type="text" class="form-control" id="drawerInputNombre" value="${u.full_name}" onkeypress="bloquearNumerosInput(event)">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Correo Institucional</label>
                        <input type="email" class="form-control" id="drawerInputEmail" value="${u.email}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Estado del Funcionario</label>
                        <select class="form-select" id="drawerSelectEstado">
                            <option value="Activo" ${u.status === 'Activo' ? 'selected' : ''}>Activo</option>
                            <option value="Inactivo" ${u.status === 'Inactivo' ? 'selected' : ''}>Inactivo</option>
                        </select>
                    </div>
                `;
            } else {
                bodyEl.innerHTML = `<p class="text-muted text-center py-4">Seleccione un registro para editar en el panel lateral.</p>`;
            }

            drawer.classList.add('open');
            if (overlay) overlay.classList.add('active');
        }
        window.abrirAdminDrawer = abrirAdminDrawer;

        function cerrarAdminDrawer() {
            const drawer = document.getElementById('adminSlideDrawer');
            const overlay = document.getElementById('adminSlideDrawerOverlay');
            if (drawer) drawer.classList.remove('open');
            if (overlay) overlay.classList.remove('active');
            drawerActivoTipo = null;
            drawerActivoId = null;
        }
        window.cerrarAdminDrawer = cerrarAdminDrawer;

        function ejecutarGuardadoDrawer() {
            if (!drawerActivoTipo || !drawerActivoId) {
                cerrarAdminDrawer();
                return;
            }

            if (drawerActivoTipo === 'vecino') {
                const v = datasetVecinos.find(item => item.id === drawerActivoId);
                if (v) {
                    const nuevoNombre = document.getElementById('drawerInputNombre')?.value?.trim();
                    const nuevaDir = document.getElementById('drawerInputDireccion')?.value?.trim();
                    const nuevoTel = document.getElementById('drawerInputTelefono')?.value?.trim();
                    const nuevoTer = document.getElementById('drawerSelectTerritorio')?.value;
                    const nuevoEst = document.getElementById('drawerSelectEstado')?.value;

                    if (!nuevoNombre || !nuevaDir) {
                        Swal.fire({ icon: 'warning', title: 'Campos requeridos', text: 'El nombre y la dirección son obligatorios y no pueden quedar vacíos.' });
                        return;
                    }

                    v.nombre = sanitizarTexto(nuevoNombre);
                    v.direccion = sanitizarTexto(nuevaDir);
                    v.telefono = sanitizarTexto(nuevoTel);
                    v.territorio = nuevoTer;
                    v.estado = nuevoEst;

                    ejecutarFiltroCompletoVecinos();
                    cerrarAdminDrawer();
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: '✓ Vecino actualizado desde el panel lateral',
                        showConfirmButton: false,
                        timer: 2000
                    });
                }
            } else if (drawerActivoTipo === 'usuario') {
                const u = datasetUsuarios.find(item => item.id === drawerActivoId);
                if (u) {
                    const nuevoNombre = document.getElementById('drawerInputNombre')?.value?.trim();
                    const nuevoEmail = document.getElementById('drawerInputEmail')?.value?.trim();
                    const nuevoEst = document.getElementById('drawerSelectEstado')?.value;

                    if (!validarEmail(nuevoEmail)) {
                        Swal.fire({ icon: 'warning', title: 'Correo Inválido', text: 'Por favor ingrese un formato de correo válido.' });
                        return;
                    }

                    fetch(`/api/users/${u.id}/update/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken') || ''
                        },
                        body: JSON.stringify({
                            full_name: sanitizarTexto(nuevoNombre),
                            email: nuevoEmail,
                            status: nuevoEst
                        })
                    }).then(r => r.json()).then(data => {
                        if (data.success) {
                            cerrarAdminDrawer();
                            cargarUsuariosDesdeDB(false);
                            Swal.fire({
                                toast: true,
                                position: 'top-end',
                                icon: 'success',
                                title: '✓ Funcionario actualizado en tiempo real en la BD',
                                showConfirmButton: false,
                                timer: 2500
                            });
                        } else {
                            Swal.fire({ icon: 'error', title: 'Error', text: data.message });
                        }
                    });
                }
            }
        }
        window.ejecutarGuardadoDrawer = ejecutarGuardadoDrawer;

        // Selección de usuarios: las acciones deben persistir en la API.
        const selectedTableRows = new Set();
        function actualizarBarraUsuariosLote() {
            const bar = document.getElementById('adminFloatingActionBar');
            const badge = document.getElementById('batchCountNumber');
            if (!bar) return;
            if (badge) badge.textContent = `${selectedTableRows.size} seleccionado${selectedTableRows.size === 1 ? '' : 's'}`;
            bar.classList.toggle('active', selectedTableRows.size > 0 && !!document.querySelector('#view-usuarios.active'));
        }
        function toggleFilaSeleccionada(id, checkbox) {
            if (checkbox.checked) selectedTableRows.add(Number(id));
            else selectedTableRows.delete(Number(id));
            checkbox.closest('tr')?.classList.toggle('row-selected', checkbox.checked);
            const all = [...document.querySelectorAll('#view-usuarios .check-user-row')];
            const head = document.getElementById('checkAllUsuarios');
            if (head) head.checked = all.length > 0 && all.every(item => item.checked);
            actualizarBarraUsuariosLote();
        }
        window.toggleFilaSeleccionada = toggleFilaSeleccionada;
        function toggleSeleccionarTodosUsuarios(checked) {
            document.querySelectorAll('#view-usuarios .check-user-row').forEach(box => {
                box.checked = checked;
                toggleFilaSeleccionada(Number(box.dataset.id), box);
            });
        }
        window.toggleSeleccionarTodosUsuarios = toggleSeleccionarTodosUsuarios;

        async function ejecutarLoteUsuarios(accion) {
            const ids = [...selectedTableRows];
            if (!ids.length) return;
            if (accion === 'export-excel') {
                if (typeof XLSX === 'undefined') {
                    Swal.fire({icon: 'error', text: 'No está disponible la exportación Excel.'});
                    return;
                }
                const rows = datasetUsuarios.filter(u => selectedTableRows.has(u.id)).map(u => ({
                    'Nombre': u.full_name, 'RUT': u.rut, 'Correo': u.email,
                    'Delegación': u.delegation_name || '', 'Cargo': u.position_name || '',
                    'Rol': (u.roles || []).map(r => r.name).join(', '), 'Estado': u.status
                }));
                const workbook = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(rows), 'Usuarios');
                XLSX.writeFile(workbook, 'Usuarios_seleccionados.xlsx');
                return;
            }
            if (accion !== 'toggle-status' && accion !== 'delete') return;
            const deleting = accion === 'delete';
            const choice = await Swal.fire({
                icon: 'warning', title: deleting ? 'Dar de baja usuarios' : 'Cambiar estado de usuarios',
                text: `${ids.length} cuenta${ids.length === 1 ? '' : 's'} seleccionada${ids.length === 1 ? '' : 's'}. ${deleting ? 'La baja conserva la auditoría.' : 'El cambio se guardará de inmediato.'}`,
                showCancelButton: true, confirmButtonText: deleting ? 'Dar de baja' : 'Cambiar estado', cancelButtonText: 'Cancelar',
                confirmButtonColor: '#A30F32'
            });
            if (!choice.isConfirmed) return;
            let updated = 0;
            const errors = [];
            for (const id of ids) {
                try {
                    const response = await fetch(`/api/users/${id}/${deleting ? 'delete' : 'toggle-status'}/`, {
                        method: 'POST', headers: {'X-CSRFToken': getCookie('csrftoken') || ''}
                    });
                    const result = await response.json();
                    if (!response.ok || !result.success) throw new Error(result.message || `No se pudo modificar la cuenta ${id}.`);
                    updated++;
                } catch (error) {
                    errors.push(`${id}: ${error.message}`);
                }
            }
            selectedTableRows.clear();
            actualizarBarraUsuariosLote();
            await cargarUsuariosDesdeDB(false);
            if (errors.length) {
                Swal.fire({icon: 'warning', title: `${updated} de ${ids.length} cuentas actualizadas`, text: errors.slice(0, 3).join(' · ')});
            } else {
                mostrarToast(`✓ ${updated} cuenta${updated === 1 ? '' : 's'} actualizada${updated === 1 ? '' : 's'} en la base de datos`);
            }
        }

        // 6. Barra Flotante de Acciones en Lote (floating_batch_bar.html)
        function actualizarBarraLoteUI() {
            const bar = document.getElementById('adminFloatingActionBar');
            const badge = document.getElementById('batchCountNumber');
            if (!bar) return;
            const cant = seleccionadosIds ? seleccionadosIds.size : 0;
            if (cant > 0) {
                if (badge) badge.textContent = `${cant} seleccionado${cant > 1 ? 's' : ''}`;
                bar.classList.add('visible');
            } else {
                bar.classList.remove('visible');
            }
        }
        window.actualizarBarraLoteUI = actualizarBarraLoteUI;

        function deseleccionarTodoFilas() {
            if (document.querySelector('#view-usuarios.active')) {
                selectedTableRows.clear();
                document.querySelectorAll('#view-usuarios .check-user-row').forEach(box => {
                    box.checked = false;
                    box.closest('tr')?.classList.remove('row-selected');
                });
                const head = document.getElementById('checkAllUsuarios');
                if (head) head.checked = false;
                actualizarBarraUsuariosLote();
                return;
            }
            if (seleccionadosIds) seleccionadosIds.clear();
            const checkHeader = document.getElementById('checkAllVecinos');
            if (checkHeader) checkHeader.checked = false;
            document.querySelectorAll('.fila-check').forEach(chk => { chk.checked = false; });
            actualizarBarraLoteUI();
            mostrarToast('✓ Selección desmarcada');
        }
        window.deseleccionarTodoFilas = deseleccionarTodoFilas;

        function ejecutarAccionLote(accion) {
            if (document.querySelector('#view-usuarios.active')) {
                ejecutarLoteUsuarios(accion);
                return;
            }
            if (!seleccionadosIds || seleccionadosIds.size === 0) {
                Swal.fire({ icon: 'info', title: 'Sin selección', text: 'No hay filas seleccionadas.' });
                return;
            }

            if (accion === 'toggle-status') {
                cambiarEstadoSeleccionados();
            } else if (accion === 'export-excel') {
                exportarSeleccionadosExcel();
            } else if (accion === 'delete') {
                eliminarSeleccionadosMasivo();
            }
        }
        window.ejecutarAccionLote = ejecutarAccionLote;

        // CRUD de ítems, metas, tipos y subatenciones: catalogs.js

        // Tipos de gestión persistidos mediante catalogs.js.

        // 9. Enlace automático de validaciones institucionales y eventos al cargar el documento
        document.addEventListener('DOMContentLoaded', function() {
            // A. Campos donde NO se permite escribir números (Nombres, Apellidos, Cargos)
            const camposSinNumeros = ['usrFullName', 'vecinoNombre', 'txtAtencionNombre', 'modalRolNombre'];
            camposSinNumeros.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('keypress', bloquearNumerosInput);
                    el.addEventListener('input', function() {
                        this.value = this.value.replace(/[0-9]/g, '');
                    });
                }
            });

            // B. Campos de RUT chileno: formateo automático con puntos y guion al desenfocar o escribir
            const camposRut = ['usrRut', 'vecinoRut'];
            camposRut.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('blur', function() {
                        if (this.value) {
                            this.value = formatearRutChileno(this.value);
                        }
                    });
                }
            });

            // C. Monitorear selección de checkboxes de vecinos para mostrar/ocultar barra flotante de lote
            const checkHeader = document.getElementById('checkAllVecinos');
            if (checkHeader) {
                checkHeader.addEventListener('change', function() {
                    setTimeout(actualizarBarraLoteUI, 50);
                });
            }

            document.addEventListener('change', function(e) {
                if (e.target && e.target.classList.contains('fila-check')) {
                    actualizarBarraLoteUI();
                }
            });
        });



