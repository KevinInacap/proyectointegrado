        let datasetVecinos = [
            { id: 1, nombre: 'Ana González Morales', rut: '12.345.678-9', direccion: 'Av. Balmaceda 120', telefono: '+56 9 8765 4321', territorio: 'Centro', gestion: 'Solicitud', estado: 'Activo' },
            { id: 2, nombre: 'Pedro Rojas Pizarro', rut: '9.876.543-2', direccion: "Calle O'Higgins 455", telefono: '+56 9 7654 3210', territorio: 'Norte', gestion: 'Reclamo', estado: 'Activo' },
            { id: 3, nombre: 'María Castillo Vergara', rut: '15.234.567-1', direccion: 'Pasaje Los Pinos 89', telefono: '+56 9 6543 2109', territorio: 'Sur', gestion: 'Consulta', estado: 'Inactivo' },
            { id: 4, nombre: 'Luis Herrera Alfaro', rut: '17.456.789-0', direccion: 'Av. El Faro 230', telefono: '+56 9 5432 1098', territorio: 'Oriente', gestion: 'Orientación', estado: 'Activo' }
        ];

        let filasFiltradasVecinos = [...datasetVecinos];
        let seleccionadosIds = new Set();
        let filasPorPagina = 10;
        let paginaActual = 1;
        let ordenAsc = true;
        let bsModalVecino, bsModalFicha, bsModalImportar, bsModalAuditoria, bsModalPerfil, chartInstance;

        /* Variables Globales de Gestión de Usuarios */
        let bsModalUsuario, bsModalEliminarUsuario, bsModalPasswordUsuario;
        let datasetUsuarios = [], filasFiltradasUsuarios = [];
        let rolesCatalog = [], delegationsCatalog = [], positionsCatalog = [];
        let filasPorPaginaUsuarios = 10, paginaActualUsuarios = 1, ordenAscUsuarios = true, campoOrdenUsuarios = 'full_name';
        let usuarioAEliminarId = null, usuarioAPasswordId = null;

        function actualizarFechaActual() {
            const elFecha = document.getElementById('currentDateDisplay');
            if (elFecha) {
                const hoy = new Date();
                const meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
                elFecha.textContent = `${hoy.getDate()} de ${meses[hoy.getMonth()]} de ${hoy.getFullYear()}`;
            }
        }

        document.addEventListener('DOMContentLoaded', function () {
            // Actualización Dinámica de Fecha Institucional respecto al día actual
            actualizarFechaActual();

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

            try { renderAtencionesChart(); } catch (e) { console.warn("Chart atenciones error:", e); }
            try { renderTablaVecinos(); } catch (e) { console.warn("Tabla vecinos error:", e); }
            try { cargarUsuariosDesdeDB(false); } catch (e) { console.warn("Cargar usuarios error:", e); }
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

        function switchView(viewName) {
            document.querySelectorAll('.maintainer-view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item-btn, .submenu-item-btn').forEach(btn => btn.classList.remove('active'));

            const targetView = document.getElementById('view-' + viewName);
            if (targetView) targetView.classList.add('active');

            if (viewName === 'dashboard') {
                document.getElementById('nav-btn-dashboard').classList.add('active');
            } else if (viewName === 'reportes') {
                document.getElementById('nav-btn-reportes').classList.add('active');
            } else {
                document.getElementById('nav-btn-mantenedores').classList.add('active');
                const subBtn = document.getElementById('sub-' + viewName);
                if (subBtn) subBtn.classList.add('active');
            }

            if (window.innerWidth < 768) {
                document.getElementById('sidebar').classList.remove('mobile-open');
                document.getElementById('sidebarOverlay').classList.remove('active');
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
                setTimeout(() => {
                    if (typeof initSpotlightEffect === 'function') initSpotlightEffect();
                    const kpiTotal = document.getElementById('kpiRepTotal');
                    if (kpiTotal && typeof animateNumberTicker === 'function') animateNumberTicker(kpiTotal, '15.842', 500);
                    const kpiRes = document.getElementById('kpiRepResolucion');
                    if (kpiRes && typeof animateNumberTicker === 'function') animateNumberTicker(kpiRes, '94.8%', 500);
                }, 50);
            }
            if (viewName === 'usuarios') cargarUsuariosDesdeDB(false);
            if (viewName === 'delegaciones') initDelegacionesView();
            if (viewName === 'roles') initRolesView(false);
        }

        function renderTablaVecinos() {
            const tbody = document.getElementById('tablaVecinosBody');
            tbody.innerHTML = '';

            const inicio = (paginaActual - 1) * filasPorPagina;
            const fin = inicio + filasPorPagina;
            const datos = filasFiltradasVecinos.slice(inicio, fin);

            if (datos.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" class="text-center py-5 text-muted">
                    <div class="empty-state-pro py-2">
                        <div class="empty-state-icon"><i class="bi bi-people"></i></div>
                        <div class="empty-state-title">No se encontraron vecinos</div>
                        <div class="empty-state-desc">No hay registros coincidentes con los filtros de búsqueda o sector aplicados.</div>
                        <button class="btn btn-sm btn-outline-primary rounded-pill px-3" onclick="limpiarFiltrosVecinos()">Restablecer Filtros</button>
                    </div>
                </td></tr>`;
                document.getElementById('lblRegistrosInfo').textContent = '0 registros';
                return;
            }

            datos.forEach((v, idx) => {
                const isSel = seleccionadosIds.has(v.id);
                const tr = document.createElement('tr');
                tr.className = 'stagger-item';
                tr.style.setProperty('--stagger-i', idx);
                if (isSel) tr.classList.add('selected-row');

                tr.innerHTML = `
                    <td class="text-center"><input type="checkbox" class="form-check-input" ${isSel ? 'checked' : ''} onchange="toggleSeleccionarFila(${v.id}, this.checked)"></td>
                    <td>${v.id}</td>
                    <td class="fw-bold"><a href="javascript:void(0)" class="text-decoration-none text-dark" onclick="abrirFichaVecino(${v.id})">${v.nombre}</a></td>
                    <td class="col-rut"><code class="text-primary fw-semibold">${v.rut}</code></td>
                    <td class="col-dir">${v.direccion}</td>
                    <td class="col-tel">${v.telefono}</td>
                    <td class="col-terr"><span class="badge bg-light text-dark border">${v.territorio}</span></td>
                    <td class="col-gest">${v.gestion}</td>
                    <td class="col-est"><span class="badge-status ${v.estado.toLowerCase()}">${v.estado}</span></td>
                    <td class="text-end">
                        <button class="btn-action-icon btn-action-view" onclick="abrirAdminDrawer('vecino', ${v.id})" title="Abrir en Panel Lateral"><i class="bi bi-layout-sidebar-inset-reverse text-primary"></i></button>
                        <button class="btn-action-icon btn-action-edit" onclick="abrirModalVecino('editar', ${v.id})" title="Editar en Modal"><i class="bi bi-pencil"></i></button>
                        <button class="btn-action-icon btn-action-delete" onclick="eliminarVecino(${v.id})" title="Eliminar"><i class="bi bi-trash"></i></button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('lblRegistrosInfo').textContent = `Mostrando ${inicio + 1} - ${Math.min(fin, filasFiltradasVecinos.length)} de ${filasFiltradasVecinos.length} registros`;
            actualizarIndicadoresDiscretos();
            actualizarBarraAccionesMasivas();
        }

        function togglePanelFiltros() {
            document.getElementById('panelFiltrosAvanzados').classList.toggle('show');
            document.getElementById('btnToggleFiltros').classList.toggle('active');
        }

        function ejecutarFiltroCompletoVecinos() {
            const texto = document.getElementById('searchVecinosInput').value.toLowerCase().trim();
            const est = document.getElementById('filtroEstadoVecino').value;
            const terr = document.getElementById('filtroTerritorioVecino').value;
            const gest = document.getElementById('filtroGestionVecino').value;

            filasFiltradasVecinos = datasetVecinos.filter(v => {
                const matchT = !texto || (v.nombre.toLowerCase().includes(texto) || v.rut.toLowerCase().includes(texto));
                const matchE = !est || v.estado === est;
                const matchTer = !terr || v.territorio.includes(terr);
                const matchG = !gest || v.gestion === gest;
                return matchT && matchE && matchTer && matchG;
            });

            const chips = document.getElementById('contenedorChipsFiltros');
            chips.innerHTML = '';
            let count = 0;
            if (est) { count++; chips.innerHTML += `<span class="filter-chip">Estado: ${est} <i class="bi bi-x-circle-fill" onclick="removerFiltro('filtroEstadoVecino')"></i></span>`; }
            if (terr) { count++; chips.innerHTML += `<span class="filter-chip">Territorio: ${terr} <i class="bi bi-x-circle-fill" onclick="removerFiltro('filtroTerritorioVecino')"></i></span>`; }
            if (gest) { count++; chips.innerHTML += `<span class="filter-chip">Gestión: ${gest} <i class="bi bi-x-circle-fill" onclick="removerFiltro('filtroGestionVecino')"></i></span>`; }

            const badge = document.getElementById('badgeFiltrosActivos');
            badge.style.display = count > 0 ? 'inline-block' : 'none';
            badge.textContent = count;

            paginaActual = 1;
            renderTablaVecinos();
        }

        function removerFiltro(id) { document.getElementById(id).value = ''; ejecutarFiltroCompletoVecinos(); }
        function limpiarFiltrosVecinos() { document.getElementById('searchVecinosInput').value = ''; document.getElementById('filtroEstadoVecino').value = ''; document.getElementById('filtroTerritorioVecino').value = ''; document.getElementById('filtroGestionVecino').value = ''; ejecutarFiltroCompletoVecinos(); }
        function filtrarSectorVecinoRapido(sector) {
            const sel = document.getElementById('filtroTerritorioVecino');
            if (sel) sel.value = sector;
            ejecutarFiltroCompletoVecinos();
            mostrarToast(sector ? `Filtrando por: ${sector}` : 'Mostrando todos los sectores');
        }

        function toggleColumna(clase, visible) {
            document.querySelectorAll('.' + clase).forEach(c => c.style.display = visible ? '' : 'none');
        }

        function ordenarTablaVecinos(col) {
            ordenAsc = !ordenAsc;
            filasFiltradasVecinos.sort((a, b) => ordenAsc ? a[col].localeCompare(b[col]) : b[col].localeCompare(a[col]));
            renderTablaVecinos();
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

        function cambiarEstadoSeleccionados() {
            datasetVecinos.forEach(v => { if (seleccionadosIds.has(v.id)) v.estado = v.estado === 'Activo' ? 'Inactivo' : 'Activo'; });
            seleccionadosIds.clear();
            ejecutarFiltroCompletoVecinos();
            mostrarToast('Estados actualizados');
        }

        function eliminarSeleccionadosMasivo() {
            if (confirm(`¿Eliminar los ${seleccionadosIds.size} seleccionados?`)) {
                datasetVecinos = datasetVecinos.filter(v => !seleccionadosIds.has(v.id));
                seleccionadosIds.clear();
                ejecutarFiltroCompletoVecinos();
                mostrarToast('Registros eliminados');
            }
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
                    rut: r['RUT'] || r['Rut'] || '11.111.111-1',
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

        function ejecutarImportacionFinal() {
            datasetVecinos = [...datasetVecinos, ...tempImportados];
            ejecutarFiltroCompletoVecinos();
            bsModalImportar.hide();
            mostrarToast(`✓ ${tempImportados.length} vecinos importados exitosamente`);
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
                    document.getElementById('vecinoNombre').value = v.nombre;
                    document.getElementById('vecinoDireccion').value = v.direccion;
                    document.getElementById('vecinoTelefono').value = v.telefono;
                    document.getElementById('vecinoTerritorio').value = v.territorio;
                    document.getElementById('vecinoEstado').value = v.estado;
                }
            }
            bsModalVecino.show();
        }

        function guardarVecino(e) {
            e.preventDefault();
            const id = document.getElementById('vecinoId').value;
            const nuevo = {
                id: id ? parseInt(id) : datasetVecinos.length + 1,
                nombre: document.getElementById('vecinoNombre').value,
                rut: document.getElementById('vecinoRut').value,
                direccion: document.getElementById('vecinoDireccion').value,
                telefono: document.getElementById('vecinoTelefono').value,
                territorio: document.getElementById('vecinoTerritorio').value,
                gestion: 'Solicitud',
                estado: document.getElementById('vecinoEstado').value
            };
            if (id) {
                const idx = datasetVecinos.findIndex(v => v.id === parseInt(id));
                if (idx !== -1) datasetVecinos[idx] = nuevo;
            } else {
                datasetVecinos.unshift(nuevo);
            }
            ejecutarFiltroCompletoVecinos();
            bsModalVecino.hide();
            mostrarToast(id ? '✓ Vecino actualizado' : '✓ Vecino registrado');
        }

        function eliminarVecino(id) {
            const v = datasetVecinos.find(item => item.id === id);
            if (v && confirm(`¿Eliminar a "${v.nombre}"?`)) {
                datasetVecinos = datasetVecinos.filter(item => item.id !== id);
                ejecutarFiltroCompletoVecinos();
                mostrarToast('✓ Vecino eliminado');
            }
        }

        function actualizarIndicadoresDiscretos() {
            const total = datasetVecinos.length;
            const activos = datasetVecinos.filter(v => v.estado === 'Activo').length;
            document.getElementById('lblTotalVecinos').textContent = total.toLocaleString('es-CL');
            document.getElementById('lblActivosVecinos').textContent = activos.toLocaleString('es-CL');
            document.getElementById('lblInactivosVecinos').textContent = (total - activos).toLocaleString('es-CL');
        }

        function cambiarFilasPorPagina(val) {
            filasPorPagina = parseInt(val);
            paginaActual = 1;
            renderTablaVecinos();
        }

        /* ==========================================================================
           LOG DE AUDITORÍA Y TRAZABILIDAD DE ACCIONES (ADMINISTRADOR)
           ========================================================================== */
        let datasetAuditLogs = [];
        let logsFiltradosAuditoria = [];

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
                    renderTablaAuditoria();
                    if (mostrarToastAviso) mostrarToast('✓ Log de auditoría actualizado.');
                }
            } catch (err) {
                console.error("Error al cargar logs de auditoría:", err);
                if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-danger"><i class="bi bi-exclamation-circle me-1"></i> No se pudo cargar el historial de auditoría.</td></tr>`;
            }
        }

        function renderTablaAuditoria() {
            const tbody = document.getElementById('tablaAuditoriaBody');
            const lblTotal = document.getElementById('lblTotalAuditLogs');
            if (!tbody) return;
            tbody.innerHTML = '';

            if (lblTotal) lblTotal.textContent = `${logsFiltradosAuditoria.length} eventos registrados`;

            if (logsFiltradosAuditoria.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> No se registran eventos con los filtros seleccionados.</td></tr>`;
                return;
            }

            logsFiltradosAuditoria.forEach(l => {
                const tr = document.createElement('tr');

                let badgeAction = '';
                const actUpper = (l.action || '').toUpperCase();
                const descLower = (l.description || '').toLowerCase();

                if (actUpper === 'CREATE') {
                    badgeAction = `<span class="badge bg-success text-white px-2 py-1"><i class="bi bi-plus-circle-fill me-1"></i> CREACIÓN</span>`;
                } else if (actUpper === 'DELETE') {
                    badgeAction = `<span class="badge bg-danger text-white px-2 py-1"><i class="bi bi-trash-fill me-1"></i> ELIMINACIÓN</span>`;
                } else if (descLower.includes('estado')) {
                    badgeAction = `<span class="badge bg-warning text-dark px-2 py-1"><i class="bi bi-toggle2-on me-1"></i> ESTADO</span>`;
                } else if (descLower.includes('contrase') || descLower.includes('clave')) {
                    badgeAction = `<span class="badge bg-info text-dark px-2 py-1"><i class="bi bi-key-fill me-1"></i> CONTRASEÑA</span>`;
                } else {
                    badgeAction = `<span class="badge bg-primary text-white px-2 py-1"><i class="bi bi-pencil-fill me-1"></i> MODIFICACIÓN</span>`;
                }

                tr.innerHTML = `
                    <td class="text-nowrap font-monospace small text-secondary" style="white-space: nowrap !important;">
                        <i class="bi bi-calendar3 me-1 text-muted"></i>${l.timestamp}
                    </td>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <div class="user-avatar-pill admin" style="width: 28px; height: 28px; font-size: 0.72rem; min-width: 28px;">
                                <i class="bi bi-person-fill"></i>
                            </div>
                            <div>
                                <span class="fw-bold text-dark d-block small">${l.admin_name}</span>
                                <small class="text-muted">@${l.admin_username}</small>
                            </div>
                        </div>
                    </td>
                    <td class="text-center">${badgeAction}</td>
                    <td>
                        <span class="fw-semibold text-dark d-block">${l.description}</span>
                    </td>
                    <td class="text-end">
                        <span class="badge bg-light text-secondary border font-monospace px-2 py-1">
                            ${l.affected_table} #${l.affected_record_id}
                        </span>
                    </td>
                `;
                tbody.appendChild(tr);
            });
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
            const savedTheme = localStorage.getItem('sgr_theme_preference');
            if (savedTheme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                document.body.setAttribute('data-theme', 'dark');
                const icon = document.getElementById('themeToggleIcon');
                if (icon) {
                    icon.classList.remove('bi-moon-stars-fill');
                    icon.classList.add('bi-sun-fill');
                }
            }
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
            centro: {
                nombre: 'Centro Histórico',
                id: 'centro',
                nombre: 'Centro Histórico',
                sector: 'Casco Colonial & Edificio Consistorial',
                direccion: 'Los Carrera #301 (Edificio Consistorial)',
                foto: '/static/img/delegacion_centro.jpg',
                badge: 'SEDE CENTRAL',
                badgeColor: '#C41230',
                badgeText: '#FFFFFF',
                espera: '6 min',
                satisfaccion: '95.0%',
                gestor: 'Alan Von Kretschmann',
                horario: '08:30 - 14:00 hrs',
                telefono: '51 220 6600'
            },
            lascompanias: {
                id: 'companias',
                nombre: 'Las Compañías',
                sector: 'Sector Norte Urbano (El Romero / Villa Los Aromos)',
                direccion: 'Esmeralda #2451 (Sector Norte)',
                foto: '/static/img/delegacion_companias.jpg',
                badge: 'DELEGACIÓN NORTE',
                badgeColor: '#1B365D',
                badgeText: '#FFFFFF',
                espera: '9 min',
                satisfaccion: '88.0%',
                gestor: 'Pablo Cuadra',
                horario: '08:30 - 14:00 hrs',
                telefono: '51 220 6700'
            },
            lapampa: {
                id: 'pampa',
                nombre: 'La Pampa',
                sector: 'Sector Sur Urbano & El Milagro',
                direccion: 'Juana Ross de Edwards #120',
                foto: '/static/img/delegacion_pampa.jpg',
                badge: 'DELEGACIÓN SUR',
                badgeColor: '#2563EB',
                badgeText: '#FFFFFF',
                espera: '7 min',
                satisfaccion: '92.0%',
                gestor: 'María Soledad Rojas',
                horario: '08:30 - 14:00 hrs',
                telefono: '51 220 6820'
            },
            laflorida: {
                id: 'antena',
                nombre: 'La Antena - La Florida',
                sector: 'Sector Oriente & Colina El Pino',
                direccion: 'Av. El Santo #1050 / 18 de Septiembre',
                foto: '/static/img/delegacion_antena.jpg',
                badge: 'DELEGACIÓN ORIENTE',
                badgeColor: '#059669',
                badgeText: '#FFFFFF',
                espera: '8 min',
                satisfaccion: '84.0%',
                gestor: 'Elizabeth Villanueva',
                horario: '08:30 - 14:00 hrs',
                telefono: '51 220 6750'
            },
            tierrasblancas: {
                id: 'costa',
                nombre: 'Avenida del Mar',
                sector: 'Borde Costero & Zona Turística',
                direccion: 'Av. Cuatro Esquinas #1500 (Borde Costero)',
                foto: '/static/img/delegacion_costa.jpg',
                badge: 'ZONA TURÍSTICA',
                badgeColor: '#0284C7',
                badgeText: '#FFFFFF',
                espera: '10 min',
                satisfaccion: '91.0%',
                gestor: 'Rodrigo Fuenzalida',
                horario: '08:30 - 14:00 hrs',
                telefono: '51 220 6900'
            },
            rural: {
                id: 'rural',
                nombre: 'Sector Rural y Caletas',
                sector: 'Valle de Elqui, Algarrobito & Caletas',
                direccion: 'Ruta 41 Km 8 (Algarrobito)',
                foto: '/static/img/delegacion_rural.jpg',
                badge: 'SEDE RURAL',
                badgeColor: '#D97706',
                badgeText: '#FFFFFF',
                espera: '5 min',
                satisfaccion: '71.4%',
                gestor: 'Manuel Barraza',
                horario: '09:00 - 13:30 hrs',
                telefono: '51 220 6950'
            }
        };

        window.currentMapSedeKey = 'centro';

        function seleccionarDelegacionMapa(key) {
            const data = delegacionesMapaData[key];
            if (!data) return;

            window.currentMapSedeKey = key;

            // Actualizar botones / pills de sedes
            document.querySelectorAll('.serena-sede-pill').forEach(p => p.classList.remove('active'));
            const pillActiva = document.getElementById(`pill-sede-${key}`);
            if (pillActiva) pillActiva.classList.add('active');

            // Actualizar pines SVG
            document.querySelectorAll('.delegation-pin-group').forEach(p => p.classList.remove('active'));
            const pinActivo = document.getElementById(`pin-${key}`);
            if (pinActivo) pinActivo.classList.add('active');

            // Actualizar panel de detalle
            const badgeEl = document.getElementById('mapFocusBadge');
            if (badgeEl) {
                badgeEl.textContent = data.badge;
                badgeEl.style.background = data.badgeColor;
                badgeEl.style.color = data.badgeText;
            }

            const titleEl = document.getElementById('mapFocusTitle');
            if (titleEl) titleEl.textContent = data.nombre;

            const sectorEl = document.getElementById('mapFocusSector');
            if (sectorEl) sectorEl.textContent = data.sector;

            const addrEl = document.getElementById('mapFocusAddress');
            if (addrEl) addrEl.innerHTML = `<i class="bi bi-geo-alt-fill text-danger me-1"></i> ${data.direccion}`;

            const waitEl = document.getElementById('mapFocusWaitTime');
            if (waitEl) waitEl.textContent = data.espera;

            const satEl = document.getElementById('mapFocusSatisfaction');
            if (satEl) satEl.innerHTML = `<i class="bi bi-star-fill text-warning me-1"></i> ${data.satisfaccion}`;

            const mgrEl = document.getElementById('mapFocusManager');
            if (mgrEl) mgrEl.textContent = data.gestor;

            const schEl = document.getElementById('mapFocusSchedule');
            if (schEl) schEl.textContent = data.horario;

            const phoneEl = document.getElementById('mapFocusPhone');
            if (phoneEl) phoneEl.innerHTML = `<i class="bi bi-telephone-fill text-primary me-1"></i> ${data.telefono}`;

            const photoEl = document.getElementById('mapFocusPhoto');
            if (photoEl && data.foto) photoEl.src = data.foto;
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

        // Catálogo de métricas por delegación para comparaciones
        const catalogoMetricasDelegaciones = {
            'centro': {
                id: 'centro',
                nombre: 'La Serena Centro (Centro Histórico)',
                sector: 'Casco Fundacional Urbano',
                atenciones: 5420,
                meta: 5000,
                cumplimiento: 108.4,
                resueltas: 5180,
                resueltasPct: 95.6,
                enProceso: 240,
                tiempoMin: 11,
                csat: 4.9,
                personal: 4,
                tramites: {
                    'Registro Social Hogares': 420,
                    'Subsidios Municipales': 260,
                    'Certif. de Residencia': 190,
                    'Permisos y Patentes': 110,
                    'Operativos Comunitarios': 85
                }
            },
            'companias': {
                id: 'companias',
                nombre: 'Norte (Las Compañías)',
                sector: 'Zona Norte del Río Elqui',
                atenciones: 4890,
                meta: 4500,
                cumplimiento: 108.6,
                resueltas: 4610,
                resueltasPct: 94.3,
                enProceso: 280,
                tiempoMin: 13,
                csat: 4.8,
                personal: 4,
                tramites: {
                    'Registro Social Hogares': 350,
                    'Subsidios Municipales': 490,
                    'Certif. de Residencia': 180,
                    'Permisos y Patentes': 130,
                    'Operativos Comunitarios': 95
                }
            },
            'pampa': {
                id: 'pampa',
                nombre: 'Sur (La Pampa / El Milagro)',
                sector: 'Zona Sur Residencial',
                atenciones: 2310,
                meta: 2200,
                cumplimiento: 105.0,
                resueltas: 2190,
                resueltasPct: 94.8,
                enProceso: 120,
                tiempoMin: 12,
                csat: 4.9,
                personal: 3,
                tramites: {
                    'Registro Social Hogares': 190,
                    'Subsidios Municipales': 240,
                    'Certif. de Residencia': 130,
                    'Permisos y Patentes': 80,
                    'Operativos Comunitarios': 65
                }
            },
            'antena': {
                id: 'antena',
                nombre: 'Oriente (San Joaquín / La Antena)',
                sector: 'Colina Oriente y Mirador',
                atenciones: 1840,
                meta: 1800,
                cumplimiento: 102.2,
                resueltas: 1750,
                resueltasPct: 95.1,
                enProceso: 90,
                tiempoMin: 10,
                csat: 4.9,
                personal: 3,
                tramites: {
                    'Registro Social Hogares': 180,
                    'Subsidios Municipales': 150,
                    'Certif. de Residencia': 95,
                    'Permisos y Patentes': 65,
                    'Operativos Comunitarios': 50
                }
            },
            'costa': {
                id: 'costa',
                nombre: 'Avenida del Mar / Costanera',
                sector: 'Borde Costero y Turístico',
                atenciones: 850,
                meta: 800,
                cumplimiento: 106.3,
                resueltas: 774,
                resueltasPct: 91.0,
                enProceso: 76,
                tiempoMin: 12,
                csat: 4.8,
                personal: 3,
                tramites: {
                    'Registro Social Hogares': 85,
                    'Subsidios Municipales': 160,
                    'Certif. de Residencia': 120,
                    'Permisos y Patentes': 45,
                    'Operativos Comunitarios': 30
                }
            },
            'rural': {
                id: 'rural',
                nombre: 'Sector Rural (Algarrobito / Lambert)',
                sector: 'Valle del Elqui Rural y Pueblos',
                atenciones: 1382,
                meta: 1400,
                cumplimiento: 98.7,
                resueltas: 1290,
                resueltasPct: 93.3,
                enProceso: 92,
                tiempoMin: 16,
                csat: 4.7,
                personal: 3,
                tramites: {
                    'Registro Social Hogares': 60,
                    'Subsidios Municipales': 130,
                    'Certif. de Residencia': 90,
                    'Permisos y Patentes': 40,
                    'Operativos Comunitarios': 35
                }
            }
        };

        // Estado del Tiempo Real (Live Mode)
        let timerLiveReportes = null;
        let esTiempoRealActivo = true;
        let segundosLive = 5;

        function initReportesCharts() {
            // Inicializar vista general por defecto
            initChartsGeneralReportes();
            iniciarTemporizadorTiempoReal();
        }

        function initChartsGeneralReportes() {
            // 1. Delegaciones Bar Chart
            const ctxDel = document.getElementById('chartReporteDelegaciones');
            if (ctxDel && !chartRepDelegacionesInstance) {
                chartRepDelegacionesInstance = new Chart(ctxDel.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: ['La Serena Centro', 'Las Compañías', 'La Pampa', 'San Joaquín', 'Sector Rural', 'Av. del Mar'],
                        datasets: [
                            {
                                label: 'Atenciones Reales',
                                data: [5420, 4890, 2310, 1840, 1382, 850],
                                backgroundColor: '#C41230',
                                borderRadius: 6
                            },
                            {
                                label: 'Meta Período',
                                data: [5000, 4500, 2200, 1800, 1400, 800],
                                backgroundColor: '#1B365D',
                                borderRadius: 6
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'top', labels: { boxWidth: 12, font: { weight: 600 } } }
                        },
                        scales: {
                            x: { grid: { display: false } },
                            y: { grid: { color: 'rgba(226, 232, 240, 0.6)' }, ticks: { stepSize: 1000 } }
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
                    data: {
                        labels: ['Presencial (Ventanilla)', 'Telefónico', 'Digital / Web', 'Operativo en Terreno'],
                        datasets: [{
                            data: [8540, 4120, 2380, 802],
                            backgroundColor: ['#1B365D', '#C41230', '#0284C7', '#16A34A'],
                            borderWidth: 2,
                            borderColor: '#FFFFFF'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { weight: 600 } } }
                        },
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
                    data: {
                        labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
                        datasets: [
                            {
                                label: 'Atenciones Registradas',
                                data: [1200, 1380, 1650, 1540, 1720, 1890, 1780, 1820, 2040],
                                borderColor: '#C41230',
                                backgroundColor: 'rgba(196, 18, 48, 0.08)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.35,
                                pointBackgroundColor: '#C41230'
                            },
                            {
                                label: 'Meta Proyectada',
                                data: [1150, 1250, 1400, 1450, 1550, 1600, 1650, 1700, 1750],
                                borderColor: '#1B365D',
                                borderDash: [5, 5],
                                borderWidth: 2,
                                fill: false,
                                pointRadius: 2
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'top', labels: { boxWidth: 12 } }
                        },
                        scales: {
                            x: { grid: { display: false } },
                            y: { grid: { color: 'rgba(226, 232, 240, 0.6)' } }
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
                    data: {
                        labels: ['Registro Social Hogares', 'Subsidios Municipales', 'Certif. de Residencia', 'Permisos y Patentes', 'Audiencia Alcaldía'],
                        datasets: [{
                            label: 'Solicitudes',
                            data: [4210, 3180, 2890, 1450, 890],
                            backgroundColor: ['#1B365D', '#C41230', '#0284C7', '#16A34A', '#F59E0B'],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { color: 'rgba(226, 232, 240, 0.6)' } },
                            y: { grid: { display: false } }
                        }
                    }
                });
            } else if (chartRepTramitesInstance) {
                chartRepTramitesInstance.resize();
            }
        }

        function cambiarSubvistaReporte(subvista) {
            subvistaReportesActiva = subvista;

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

            // Evitar comparar la misma delegación
            if (idA === idB) {
                const keys = Object.keys(catalogoMetricasDelegaciones);
                idB = keys.find(k => k !== idA) || 'companias';
                const elSelB = document.getElementById('selectCompareDelB');
                if (elSelB) elSelB.value = idB;
            }

            const delA = catalogoMetricasDelegaciones[idA] || catalogoMetricasDelegaciones['centro'];
            const delB = catalogoMetricasDelegaciones[idB] || catalogoMetricasDelegaciones['companias'];

            // Actualizar subtítulos territoriales
            const subA = document.getElementById('compareSubA');
            if (subA) subA.textContent = delA.sector;
            const subB = document.getElementById('compareSubB');
            if (subB) subB.textContent = delB.sector;

            // Renderizar Grilla de Métricas Comparativas
            const grid = document.getElementById('gridMetricas1vs1');
            if (grid) {
                const difAtenciones = delA.atenciones - delB.atenciones;
                const liderAtenciones = difAtenciones >= 0 ? delA.nombre.split(' ')[0] : delB.nombre.split(' ')[0];

                const difTiempo = delA.tiempoMin - delB.tiempoMin;
                const liderRapidez = difTiempo <= 0 ? delA.nombre.split(' ')[0] : delB.nombre.split(' ')[0];

                grid.innerHTML = `
                    <div class="col-sm-6 col-xl-3">
                        <div class="p-3 rounded-3 bg-white border shadow-sm h-100">
                            <span class="text-secondary small fw-semibold">Atenciones Totales</span>
                            <div class="d-flex align-items-center justify-content-between my-2">
                                <span class="fw-bold fs-5 text-danger">${delA.atenciones.toLocaleString('es-CL')}</span>
                                <span class="text-muted small">vs</span>
                                <span class="fw-bold fs-5 text-primary">${delB.atenciones.toLocaleString('es-CL')}</span>
                            </div>
                            <div class="small fw-semibold ${difAtenciones >= 0 ? 'text-danger' : 'text-primary'}">
                                <i class="bi bi-trophy-fill me-1"></i>Lidera: ${liderAtenciones} (${Math.abs(difAtenciones).toLocaleString('es-CL')} dif)
                            </div>
                        </div>
                    </div>

                    <div class="col-sm-6 col-xl-3">
                        <div class="p-3 rounded-3 bg-white border shadow-sm h-100">
                            <span class="text-secondary small fw-semibold">Tiempo Medio Espera</span>
                            <div class="d-flex align-items-center justify-content-between my-2">
                                <span class="fw-bold fs-5 text-danger">${delA.tiempoMin} min</span>
                                <span class="text-muted small">vs</span>
                                <span class="fw-bold fs-5 text-primary">${delB.tiempoMin} min</span>
                            </div>
                            <div class="small fw-semibold text-success">
                                <i class="bi bi-lightning-charge-fill me-1"></i>Más Rápida: ${liderRapidez} (${Math.abs(difTiempo)} min menos)
                            </div>
                        </div>
                    </div>

                    <div class="col-sm-6 col-xl-3">
                        <div class="p-3 rounded-3 bg-white border shadow-sm h-100">
                            <span class="text-secondary small fw-semibold">Cumplimiento de Meta</span>
                            <div class="d-flex align-items-center justify-content-between my-2">
                                <span class="fw-bold fs-5 text-danger">${delA.cumplimiento}%</span>
                                <span class="text-muted small">vs</span>
                                <span class="fw-bold fs-5 text-primary">${delB.cumplimiento}%</span>
                            </div>
                            <div class="small fw-semibold text-secondary">
                                Meta Trimestral: ${delA.meta.toLocaleString('es-CL')} vs ${delB.meta.toLocaleString('es-CL')}
                            </div>
                        </div>
                    </div>

                    <div class="col-sm-6 col-xl-3">
                        <div class="p-3 rounded-3 bg-white border shadow-sm h-100">
                            <span class="text-secondary small fw-semibold">Satisfacción Vecinal (CSAT)</span>
                            <div class="d-flex align-items-center justify-content-between my-2">
                                <span class="fw-bold fs-5 text-danger">★ ${delA.csat}</span>
                                <span class="text-muted small">vs</span>
                                <span class="fw-bold fs-5 text-primary">★ ${delB.csat}</span>
                            </div>
                            <div class="small fw-semibold text-warning-emphasis">
                                Resolución 1er Contacto: ${delA.resueltasPct}% vs ${delB.resueltasPct}%
                            </div>
                        </div>
                    </div>
                `;
            }

            // 1. Radar Chart Comparativo 1 vs 1 (5 ejes normalizados de 0 a 100)
            const ctxRadar = document.getElementById('chartCompareRadar');
            if (ctxRadar) {
                const normAtencA = Math.min(100, Math.round((delA.atenciones / 5500) * 100));
                const normAtencB = Math.min(100, Math.round((delB.atenciones / 5500) * 100));

                const normRapidezA = Math.max(20, Math.round(100 - (delA.tiempoMin * 4)));
                const normRapidezB = Math.max(20, Math.round(100 - (delB.tiempoMin * 4)));

                const radarData = {
                    labels: ['Volumen Demanda', 'Rapidez de Atención', 'Resolución 1er Contacto', 'Cumplimiento Metas', 'Satisfacción Vecinal'],
                    datasets: [
                        {
                            label: delA.nombre,
                            data: [normAtencA, normRapidezA, delA.resueltasPct, Math.min(100, delA.cumplimiento), delA.csat * 20],
                            backgroundColor: 'rgba(196, 18, 48, 0.25)',
                            borderColor: '#C41230',
                            borderWidth: 2.5,
                            pointBackgroundColor: '#C41230'
                        },
                        {
                            label: delB.nombre,
                            data: [normAtencB, normRapidezB, delB.resueltasPct, Math.min(100, delB.cumplimiento), delB.csat * 20],
                            backgroundColor: 'rgba(27, 54, 93, 0.25)',
                            borderColor: '#1B365D',
                            borderWidth: 2.5,
                            pointBackgroundColor: '#1B365D'
                        }
                    ]
                };

                if (chartCompareRadarInstance) {
                    chartCompareRadarInstance.data = radarData;
                    chartCompareRadarInstance.update();
                } else {
                    chartCompareRadarInstance = new Chart(ctxRadar.getContext('2d'), {
                        type: 'radar',
                        data: radarData,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'top', labels: { font: { weight: 600 } } }
                            },
                            scales: {
                                r: {
                                    suggestedMin: 20,
                                    suggestedMax: 100,
                                    ticks: { display: false },
                                    pointLabels: { font: { size: 11, weight: 600 } }
                                }
                            }
                        }
                    });
                }
            }

            // 2. Gráfico de Barras Comparativo de Trámites
            const ctxTra = document.getElementById('chartCompareTramites');
            if (ctxTra) {
                const labelsTramites = Object.keys(delA.tramites);
                const dataA = labelsTramites.map(t => delA.tramites[t] || 0);
                const dataB = labelsTramites.map(t => delB.tramites[t] || 0);

                const barData = {
                    labels: labelsTramites,
                    datasets: [
                        {
                            label: delA.nombre,
                            data: dataA,
                            backgroundColor: '#C41230',
                            borderRadius: 5
                        },
                        {
                            label: delB.nombre,
                            data: dataB,
                            backgroundColor: '#1B365D',
                            borderRadius: 5
                        }
                    ]
                };

                if (chartCompareTramitesInstance) {
                    chartCompareTramitesInstance.data = barData;
                    chartCompareTramitesInstance.update();
                } else {
                    chartCompareTramitesInstance = new Chart(ctxTra.getContext('2d'), {
                        type: 'bar',
                        data: barData,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'top', labels: { font: { weight: 600 } } }
                            },
                            scales: {
                                x: { grid: { display: false } },
                                y: { grid: { color: 'rgba(226, 232, 240, 0.6)' } }
                            }
                        }
                    });
                }
            }

            // Cuadro de Diagnóstico Ejecutivo en lenguaje simple
            const elConc = document.getElementById('conclusion1vs1');
            if (elConc) {
                let ventajaRapidez = delA.tiempoMin < delB.tiempoMin ? `${delA.nombre} registra una respuesta más expedita (${delA.tiempoMin} min vs ${delB.tiempoMin} min)` : `${delB.nombre} registra una respuesta más expedita (${delB.tiempoMin} min vs ${delA.tiempoMin} min)`;
                let ventajaVolumen = delA.atenciones > delB.atenciones ? `${delA.nombre} atiende un mayor caudal vecinal (${delA.atenciones.toLocaleString('es-CL')} solicitudes)` : `${delB.nombre} atiende un mayor caudal vecinal (${delB.atenciones.toLocaleString('es-CL')} solicitudes)`;

                elConc.innerHTML = `
                    <strong>Resumen Comparativo para la Jefatura Municipal:</strong> Al contrastar <em>${delA.nombre}</em> con <em>${delB.nombre}</em>, se observa que <strong>${ventajaRapidez}</strong>. En términos de volumen comunitario, <strong>${ventajaVolumen}</strong>. Ambas unidades mantienen niveles de satisfacción ciudadana de excelencia (★ ${delA.csat} y ★ ${delB.csat}), superando el umbral de cumplimiento municipal fijado para este período.
                `;
            }
        }

        /* ==========================================================================
           LÓGICA COMPARATIVA MULTIDELEGACIONAL (TODAS CONTRA TODAS)
           ========================================================================== */
        function initComparativaMultiCharts() {
            const dels = Object.values(catalogoMetricasDelegaciones);

            // 1. Ranking de Cumplimiento de Metas (Ordenado)
            const ctxRank = document.getElementById('chartMultiRanking');
            if (ctxRank) {
                const sortedCumpl = [...dels].sort((a, b) => b.cumplimiento - a.cumplimiento);
                const dataRank = {
                    labels: sortedCumpl.map(d => d.nombre.split(' (')[0]),
                    datasets: [{
                        label: '% Cumplimiento Meta',
                        data: sortedCumpl.map(d => d.cumplimiento),
                        backgroundColor: sortedCumpl.map(d => d.cumplimiento >= 105 ? '#16A34A' : (d.cumplimiento >= 100 ? '#0D6EFD' : '#F59E0B')),
                        borderRadius: 6
                    }]
                };

                if (chartMultiRankingInstance) {
                    chartMultiRankingInstance.data = dataRank;
                    chartMultiRankingInstance.update();
                } else {
                    chartMultiRankingInstance = new Chart(ctxRank.getContext('2d'), {
                        type: 'bar',
                        data: dataRank,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                x: { grid: { display: false } },
                                y: { suggestedMin: 80, grid: { color: 'rgba(226, 232, 240, 0.6)' }, ticks: { callback: v => v + '%' } }
                            }
                        }
                    });
                }
            }

            // 2. Tiempos de Espera Comunal Comparados (Menor a Mayor)
            const ctxTiempos = document.getElementById('chartMultiTiempos');
            if (ctxTiempos) {
                const sortedTiempos = [...dels].sort((a, b) => a.tiempoMin - b.tiempoMin);
                const dataTiempos = {
                    labels: sortedTiempos.map(d => d.nombre.split(' (')[0]),
                    datasets: [{
                        label: 'Minutos Promedio de Espera',
                        data: sortedTiempos.map(d => d.tiempoMin),
                        backgroundColor: sortedTiempos.map(d => d.tiempoMin <= 12 ? '#0284C7' : '#F97316'),
                        borderRadius: 6
                    }]
                };

                if (chartMultiTiemposInstance) {
                    chartMultiTiemposInstance.data = dataTiempos;
                    chartMultiTiemposInstance.update();
                } else {
                    chartMultiTiemposInstance = new Chart(ctxTiempos.getContext('2d'), {
                        type: 'bar',
                        data: dataTiempos,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                x: { grid: { display: false } },
                                y: { suggestedMax: 20, grid: { color: 'rgba(226, 232, 240, 0.6)' }, ticks: { callback: v => v + ' min' } }
                            }
                        }
                    });
                }
            }

            // 3. Satisfacción Vecinal por Delegación
            const ctxSat = document.getElementById('chartMultiSatisfaccion');
            if (ctxSat) {
                const dataSat = {
                    labels: dels.map(d => d.nombre.split(' (')[0]),
                    datasets: [{
                        label: 'Satisfacción Vecinal (CSAT / 5.0)',
                        data: dels.map(d => d.csat),
                        backgroundColor: '#F59E0B',
                        borderRadius: 6
                    }]
                };

                if (chartMultiSatisfaccionInstance) {
                    chartMultiSatisfaccionInstance.data = dataSat;
                    chartMultiSatisfaccionInstance.update();
                } else {
                    chartMultiSatisfaccionInstance = new Chart(ctxSat.getContext('2d'), {
                        type: 'bar',
                        data: dataSat,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: {
                                x: { grid: { display: false } },
                                y: { min: 4.0, max: 5.0, grid: { color: 'rgba(226, 232, 240, 0.6)' }, ticks: { stepSize: 0.2 } }
                            }
                        }
                    });
                }
            }
        }

        /* ==========================================================================
           SISTEMA DE TIEMPO REAL / LIVE STREAM SIMULADO
           ========================================================================== */
        function iniciarTemporizadorTiempoReal() {
            if (timerLiveReportes) clearInterval(timerLiveReportes);
            segundosLive = 5;

            timerLiveReportes = setInterval(() => {
                if (!esTiempoRealActivo) return;
                segundosLive--;
                const elSec = document.getElementById('liveCounterSec');
                if (elSec) elSec.textContent = segundosLive + 's';

                if (segundosLive <= 0) {
                    segundosLive = 5;
                    ejecutarTickTiempoReal();
                }
            }, 1000);
        }

        function toggleTiempoRealReportes() {
            esTiempoRealActivo = !esTiempoRealActivo;
            const dot = document.getElementById('liveDotIndicator');
            const txt = document.getElementById('liveTextIndicator');
            const btnTxt = document.getElementById('btnToggleLiveText');
            const btnIcon = document.getElementById('btnToggleLiveIcon');

            if (esTiempoRealActivo) {
                if (dot) dot.classList.remove('paused');
                if (txt) txt.textContent = 'Tiempo Real: ACTIVO';
                if (btnTxt) btnTxt.textContent = 'Pausar';
                if (btnIcon) {
                    btnIcon.classList.remove('bi-play-fill');
                    btnIcon.classList.add('bi-pause-fill');
                }
                mostrarToast('✓ Monitoreo en vivo activado.');
            } else {
                if (dot) dot.classList.add('paused');
                if (txt) txt.textContent = 'Tiempo Real: PAUSADO';
                if (btnTxt) btnTxt.textContent = 'Reanudar';
                if (btnIcon) {
                    btnIcon.classList.remove('bi-pause-fill');
                    btnIcon.classList.add('bi-play-fill');
                }
                mostrarToast('⏸ Monitoreo en vivo pausado.');
            }
        }

        function forzarActualizacionEnVivo() {
            segundosLive = 5;
            ejecutarTickTiempoReal();
            mostrarToast('✓ Datos sincronizados con la red comunal en tiempo real.');
        }

        function ejecutarTickTiempoReal() {
            // Incrementar contador de atenciones con un flash sutil
            const elTot = document.getElementById('kpiRepTotal');
            if (elTot) {
                let actual = parseInt(elTot.textContent.replace(/\./g, '')) || 15842;
                actual += Math.floor(Math.random() * 2) + 1;
                elTot.textContent = actual.toLocaleString('es-CL');
                elTot.style.transition = 'color 0.3s ease';
                elTot.style.color = '#16A34A';
                setTimeout(() => { elTot.style.color = 'var(--muni-navy)'; }, 600);
            }

            // Agregar evento al ticker de actividad
            const ticker = document.getElementById('liveFeedTicker');
            if (ticker) {
                const eventosEjemplo = [
                    { del: 'Las Compañías', tipo: 'danger', desc: 'Atención presencial finalizada: Registro Social de Hogares entregado' },
                    { del: 'Centro Histórico', tipo: 'primary', desc: 'Certificado de residencia emitido vía tótem digital' },
                    { del: 'La Pampa', tipo: 'success', desc: 'Solicitud de mantención de plaza asignada a inspector municipal' },
                    { del: 'San Joaquín', tipo: 'primary', desc: 'Audiencia de junta vecinal confirmada con delegado territorial' },
                    { del: 'Sector Rural', tipo: 'success', desc: 'Operativo APR: Camión aljibe abastecido en Quebrada de Talca' },
                    { del: 'Avenida del Mar', tipo: 'info', desc: 'Permiso de actividad turística verificado en terreno' }
                ];
                const ev = eventosEjemplo[Math.floor(Math.random() * eventosEjemplo.length)];
                const ahora = new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                const item = document.createElement('div');
                item.className = 'live-feed-item';
                item.innerHTML = `
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge bg-${ev.tipo}-subtle text-${ev.tipo} border" style="font-size: 0.75rem;">${ev.del}</span>
                        <span class="text-dark fw-medium">${ev.desc}</span>
                    </div>
                    <span class="text-muted small font-monospace">${ahora}</span>
                `;
                ticker.insertBefore(item, ticker.firstChild);

                // Limitar a máximo 5 items en pantalla
                if (ticker.children.length > 5) {
                    ticker.removeChild(ticker.lastChild);
                }
            }
        }

        function actualizarReportesDatos() {
            const elP = document.getElementById('filtroPeriodoReporte');
            const p = (elP && elP.value) ? elP.value : 'trimestre';
            const elD = document.getElementById('filtroDelegacionReporte');
            const d = (elD && elD.value) ? elD.value : '';
            const elC = document.getElementById('filtroCanalReporte');
            const c = (elC && elC.value) ? elC.value : '';

            let factor = 1;
            if (p === 'mes') factor = 0.35;
            if (p === 'ano') factor = 3.8;
            if (p === 'historico') factor = 7.5;
            if (d !== '') factor *= 0.45;
            if (c !== '') factor *= 0.6;

            const baseTotal = 15842;
            const totalCalc = Math.round(baseTotal * factor);
            const elTot = document.getElementById('kpiRepTotal');
            if (elTot) elTot.textContent = totalCalc.toLocaleString('es-CL');

            mostrarToast(`✓ Reportes actualizados: ${totalCalc.toLocaleString('es-CL')} registros analizados.`);
        }

        function restablecerFiltrosReportes() {
            if (document.getElementById('filtroPeriodoReporte')) document.getElementById('filtroPeriodoReporte').value = 'trimestre';
            if (document.getElementById('filtroDelegacionReporte')) document.getElementById('filtroDelegacionReporte').value = '';
            if (document.getElementById('filtroCanalReporte')) document.getElementById('filtroCanalReporte').value = '';
            actualizarReportesDatos();
            mostrarToast('✓ Filtros restablecidos a valores iniciales');
        }

        /* ==========================================================================
           EXPORTACIÓN COMPLETA A EXCEL MULTI-HOJA Y PDF OFICIAL
           ========================================================================== */
        function exportarReportesExcel() {
            if (!window.XLSX) {
                alert('La librería XLSX está cargando.');
                return;
            }

            const wb = XLSX.utils.book_new();

            // Hoja 1: Resumen Ejecutivo y KPIs
            const resumenData = [
                ["ILUSTRE MUNICIPALIDAD DE LA SERENA - GESTIÓN DE ATENCIÓN CIUDADANA (SGR)"],
                ["INFORME EJECUTIVO DE RENDIMIENTO INSTITUCIONAL Y TERRITORIAL"],
                ["Fecha de Emisión:", new Date().toLocaleString('es-CL'), "Autoridad:", "Administrador Municipal"],
                [],
                ["INDICADOR CLAVE (KPI)", "VALOR REGISTRADO", "META OFICIAL", "ESTADO"],
                ["Atenciones Totales Gestionadas", "15.842", "14.000", "+14.2% (Meta Superada)"],
                ["Resolución en 1er Contacto", "94.8%", "90.0%", "Cumplimiento Óptimo"],
                ["Tiempo Medio de Espera Vecinal", "12.4 min", "< 18 min", "-3.1 min (Optimizado)"],
                ["Satisfacción Vecinal (CSAT)", "4.85 / 5.0", "4.50 / 5.0", "Nivel Excelente (3.420 encuestas)"]
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
                ["Métrica", delA.nombre, delB.nombre, "Diferencia"],
                ["Atenciones Totales", delA.atenciones, delB.atenciones, delA.atenciones - delB.atenciones],
                ["Meta Asignada", delA.meta, delB.meta, delA.meta - delB.meta],
                ["% Cumplimiento", delA.cumplimiento + "%", delB.cumplimiento + "%", (delA.cumplimiento - delB.cumplimiento).toFixed(1) + "%"],
                ["Tiempo Espera (min)", delA.tiempoMin, delB.tiempoMin, (delA.tiempoMin - delB.tiempoMin) + " min"],
                ["Satisfacción (1 a 5)", delA.csat, delB.csat, (delA.csat - delB.csat).toFixed(2)],
                ["Dotación de Funcionarios", delA.personal, delB.personal, delA.personal - delB.personal]
            ];
            const ws3 = XLSX.utils.aoa_to_sheet(compData);
            XLSX.utils.book_append_sheet(wb, ws3, "Comparativa_1vs1");

            // Hoja 4: Canales de Atención y Ranking de Trámites
            const canalesData = [
                ["DISTRIBUCIÓN POR CANAL DE ATENCIÓN"],
                ["Canal", "Volumen Atenciones", "Porcentaje Estimado"],
                ["Presencial (Ventanilla)", 8540, "53.9%"],
                ["Telefónico", 4120, "26.0%"],
                ["Digital / Portal Vecino", 2380, "15.0%"],
                ["Operativo Móvil en Terreno", 802, "5.1%"],
                [],
                ["TOP TRÁMITES MÁS DEMANDADOS"],
                ["Trámite", "Solicitudes Registradas"],
                ["Registro Social de Hogares", 4210],
                ["Subsidios Municipales", 3180],
                ["Certificados de Residencia", 2890],
                ["Permisos y Patentes de Obras", 1450],
                ["Audiencia con Alcaldía / Jefaturas", 890]
            ];
            const ws4 = XLSX.utils.aoa_to_sheet(canalesData);
            XLSX.utils.book_append_sheet(wb, ws4, "Canales_Y_Tramites");

            XLSX.writeFile(wb, "Reporte_Estadistico_Integral_LaSerena_2026.xlsx");
            mostrarToast("✓ Archivo Excel Multi-Hoja descargado con éxito.");
        }

        function generarReportePDFOficial() {
            if (!window.jspdf) {
                alert('La librería PDF está cargando.');
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
            doc.text(`Fecha de emisión: ${new Date().toLocaleDateString('es-CL')} | Estado: Consolidado Oficial Comunal`, 14, 34);

            // Resumen de KPIs
            doc.autoTable({
                startY: 39,
                theme: 'plain',
                styles: { fontSize: 8.5, cellPadding: 2 },
                head: [['Indicador Clave', 'Valor Registrado', 'Meta Oficial', 'Cumplimiento']],
                body: [
                    ['Atenciones Totales Gestionadas', '15.842', '14.000', '113.1% (Superada)'],
                    ['Tasa de Resolución en 1er Contacto', '94.8%', '90.0%', 'Cumple con excelencia'],
                    ['Tiempo Medio de Espera Vecinal', '12.4 minutos', '< 18 minutos', 'Cumple estándar'],
                    ['Índice de Satisfacción (CSAT)', '4.85 / 5.0 (97%)', '4.50 / 5.0', 'Destacado Comunal']
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
            mostrarToast('✓ Informe PDF generado y descargado con éxito.');
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
                    u.full_name.toLowerCase().includes(query) ||
                    u.username.toLowerCase().includes(query) ||
                    u.rut.toLowerCase().includes(query) ||
                    u.email.toLowerCase().includes(query) ||
                    u.position_name.toLowerCase().includes(query);

                const matchDel = !delFiltro || String(u.delegation_id) === String(delFiltro);
                const matchRol = !rolFiltro || u.roles.some(r => String(r.id) === String(rolFiltro));
                const matchEst = !estFiltro || u.status === estFiltro;

                return matchTexto && matchDel && matchRol && matchEst;
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
                tbody.innerHTML = `<tr><td colspan="8" class="text-center py-5 text-muted">
                    <div class="empty-state-pro py-2">
                        <div class="empty-state-icon"><i class="bi bi-person-x"></i></div>
                        <div class="empty-state-title">No se encontraron funcionarios</div>
                        <div class="empty-state-desc">No hay registros coincidentes con los filtros aplicados en esta vista.</div>
                        <button class="btn btn-sm btn-outline-primary rounded-pill px-3" onclick="limpiarFiltrosUsuarios()">Restablecer Filtros</button>
                    </div>
                </td></tr>`;
                document.getElementById('lblRegistrosInfoUsuarios').textContent = '0 registros encontrados';
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
                        return `<span class="badge ${badgeCls} px-2 py-1" style="font-size: 0.78rem; font-weight: 600;">${rIcon}${r.name}</span>`;
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
                    <button class="btn btn-sm p-0 border-0" onclick="toggleEstadoUsuario(${u.id}, '${u.full_name.replace(/'/g, "\\'")}')" title="Clic para alternar estado">
                        <span class="badge ${isActivo ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-danger-subtle text-danger border border-danger-subtle'} px-2 py-1" style="font-size: 0.78rem; font-weight: 600; cursor: pointer;">
                            <i class="bi ${isActivo ? 'bi-check-circle-fill' : 'bi-x-circle-fill'} me-1"></i>${u.status}
                        </span>
                    </button>
                `;

                // Avatar con iniciales y anillo institucional
                const initials = (u.full_name || 'U').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
                const avatarRingColor = esAdmin ? '#C41230' : '#1B365D';
                const ultimaConexion = u.last_login || (idx % 2 === 0 ? 'Hoy 09:42 hrs' : 'Ayer 17:15 hrs');

                const isSelected = typeof selectedTableRows !== 'undefined' && selectedTableRows.has(u.id);
                if (isSelected) tr.classList.add('row-selected');

                tr.innerHTML = `
                    <td class="text-center" style="vertical-align: middle;">
                        <input type="checkbox" class="form-check-input check-user-row" data-id="${u.id}" ${isSelected ? 'checked' : ''} onchange="toggleFilaSeleccionada(${u.id}, this)">
                    </td>
                    <td class="text-center fw-semibold text-secondary" style="font-size: 0.85rem; vertical-align: middle;">${rowNum}</td>
                    <td style="vertical-align: middle;">
                        <div class="d-flex align-items-center gap-2">
                            <div class="user-avatar-pill ${esAdmin ? 'admin' : ''}" style="width: 36px; height: 36px; font-size: 0.82rem; border: 2px solid ${avatarRingColor}; flex-shrink: 0;">
                                ${initials}
                            </div>
                            <div>
                                <div class="d-flex align-items-center gap-1">
                                    <span class="fw-bold" style="color: var(--muni-navy); font-size: 0.88rem;">${u.full_name}</span>
                                    ${esAdmin ? '<span class="badge bg-danger-subtle text-danger border border-danger-subtle" style="font-size: 0.62rem; padding: 1px 4px;">ADMIN</span>' : ''}
                                </div>
                                <div class="text-secondary font-monospace" style="font-size: 0.74rem;">${u.rut}</div>
                            </div>
                        </div>
                    </td>
                    <td style="vertical-align: middle;">
                        <a href="mailto:${u.email}" class="text-decoration-none text-primary small fw-semibold" style="font-size: 0.82rem;">
                            <i class="bi bi-envelope text-muted me-1"></i>${u.email}
                        </a>
                    </td>
                    <td style="vertical-align: middle;">
                        <div class="fw-medium text-dark small" style="font-size: 0.83rem;">
                            <i class="bi bi-geo-alt-fill text-danger me-1"></i>${delegacionLimpia}
                        </div>
                        ${cargoLimpio ? `<div class="text-muted small" style="font-size: 0.74rem;">${cargoLimpio}</div>` : ''}
                    </td>
                    <td style="vertical-align: middle;">
                        <span class="text-secondary small font-monospace" style="font-size: 0.78rem;">
                            <i class="bi bi-clock-history me-1 text-info"></i>${ultimaConexion}
                        </span>
                    </td>
                    <td class="text-center" style="vertical-align: middle;">${statusBadge}</td>
                    <td class="text-end" style="vertical-align: middle;">
                        <div class="dropdown d-inline-block">
                            <button class="btn btn-sm btn-light border rounded-circle shadow-xs" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;" title="Acciones del usuario">
                                <i class="bi bi-three-dots-vertical text-secondary"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 rounded-4 p-2" style="min-width: 200px; font-size: 0.82rem; backdrop-filter: blur(16px);">
                                <li>
                                    <a class="dropdown-item py-2 fw-medium text-primary rounded-2" href="javascript:void(0)" onclick="abrirAdminDrawer('usuario', ${u.id})">
                                        <i class="bi bi-layout-sidebar-inset-reverse me-2"></i> Abrir en Panel Lateral
                                    </a>
                                </li>
                                <li>
                                    <a class="dropdown-item py-2 fw-medium rounded-2" href="javascript:void(0)" onclick="abrirModalUsuario('editar', ${u.id})">
                                        <i class="bi bi-pencil-square text-warning me-2"></i> Editar Privilegios
                                    </a>
                                </li>
                                <li>
                                    <a class="dropdown-item py-2 fw-medium text-primary rounded-2" href="javascript:void(0)" onclick="abrirModalPassword(${u.id}, '${u.full_name.replace(/'/g, "\\'")}')">
                                        <i class="bi bi-key-fill me-2"></i> Resetear Contraseña
                                    </a>
                                </li>
                                <li>
                                    <a class="dropdown-item py-2 fw-medium text-secondary rounded-2" href="javascript:void(0)" onclick="abrirModalUsuario('editar', ${u.id})">
                                        <i class="bi bi-building-gear me-2"></i> Reasignar Sede
                                    </a>
                                </li>
                                <li><hr class="dropdown-divider my-1"></li>
                                <li>
                                    <a class="dropdown-item py-2 fw-medium text-${isActivo ? 'danger' : 'success'} rounded-2" href="javascript:void(0)" onclick="toggleEstadoUsuario(${u.id}, '${u.full_name.replace(/'/g, "\\'")}')">
                                        <i class="bi bi-power me-2"></i> ${isActivo ? 'Desactivar Acceso' : 'Activar Acceso'}
                                    </a>
                                </li>
                            </ul>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            const total = filasFiltradasUsuarios.length;
            document.getElementById('lblRegistrosInfoUsuarios').textContent = `Mostrando ${Math.min(fin, total)} de ${total} usuarios`;
            actualizarPaginadorUsuarios(total);
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
            filasPorPaginaUsuarios = parseInt(cant);
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

            if (modo === 'nuevo') {
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
                document.getElementById('helpPasswordUsuario').textContent = "Por defecto se asigna 'MuniLaSerena2026!' si se deja en blanco.";
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
                document.getElementById('helpPasswordUsuario').textContent = "Dejar en blanco para conservar la clave actual del usuario.";

                // Marcar roles que el usuario tiene
                if (u.roles && u.roles.length > 0) {
                    const uRoleIds = u.roles.map(r => r.id);
                    document.querySelectorAll('.role-chk').forEach(chk => {
                        chk.checked = uRoleIds.includes(parseInt(chk.value));
                    });
                }
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
            const password = document.getElementById('usrPassword').value.trim();
            const status = document.getElementById('usrStatus').value;
            const delegationId = document.getElementById('usrDelegation').value || null;
            const positionId = document.getElementById('usrPosition').value || null;
            const isSuperuser = document.getElementById('usrIsSuperuser').checked;

            // Recoger roles seleccionados
            const roleIds = [];
            document.querySelectorAll('.role-chk:checked').forEach(chk => {
                roleIds.push(parseInt(chk.value));
            });

            if (!fullName || !rut || !email) {
                mostrarToast('⚠ Por favor complete todos los campos requeridos.');
                return;
            }

            const payload = {
                full_name: fullName,
                rut: rut,
                username: username,
                email: email,
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
                    mostrarToast('⚠ ' + data.message);
                    btn.disabled = false;
                    spinner.style.display = 'none';
                    icon.style.display = 'inline-block';
                    return;
                }

                mostrarToast('✓ ' + data.message);
                if (bsModalUsuario) bsModalUsuario.hide();
                cargarUsuariosDesdeDB(false);

            } catch (err) {
                console.error("Error guardando:", err);
                mostrarToast('⚠ Error al comunicarse con el servidor.');
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
                    mostrarToast('⚠ ' + data.message);
                    return;
                }

                mostrarToast('✓ ' + data.message);
                if (bsModalEliminarUsuario) bsModalEliminarUsuario.hide();
                cargarUsuariosDesdeDB(false);

            } catch (err) {
                console.error("Error eliminar:", err);
                mostrarToast('⚠ Error al eliminar usuario.');
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
                usuarioAEliminarId = null;
            }
        }

        function abrirModalPassword(id, nombre) {
            usuarioAPasswordId = id;
            document.getElementById('pwdUsuarioNombre').textContent = nombre;
            document.getElementById('pwdNuevaClave').value = '';
            if (!bsModalPasswordUsuario) {
                const el = document.getElementById('modalPasswordUsuario');
                if (el && window.bootstrap) bsModalPasswordUsuario = new bootstrap.Modal(el);
            }
            if (bsModalPasswordUsuario) bsModalPasswordUsuario.show();
        }

        async function guardarPasswordDB() {
            if (!usuarioAPasswordId) return;
            const pwd = document.getElementById('pwdNuevaClave').value.trim();
            if (!pwd || pwd.length < 6) {
                mostrarToast('⚠ La contraseña debe tener al menos 6 caracteres.');
                return;
            }

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
                    mostrarToast('⚠ ' + data.message);
                    return;
                }
                mostrarToast('✓ ' + data.message);
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
                alert('La librería XLSX está cargando, intente nuevamente en unos segundos.');
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
                alert('La librería PDF está cargando.');
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
           MÓDULO: DELEGACIONES MUNICIPALES (6 DELEGACIONES CON FOTOGRAFÍA REAL & GLASSMORPHISM)
           ========================================================================== */

        const datasetDelegacionesDetalle = {
            'centro': {
                id: 'centro',
                nombre: 'Delegación Centro Histórico',
                sector: 'Zona Urbana Central & Colonial',
                foto: '/static/img/delegacion_centro.jpg',
                direccion: 'Prat 451, Edificio Consistorial (Plaza de Armas)',
                telefono: '+56 51 220 6600',
                email: 'delegacion.centro@laserena.cl',
                horario: 'Lunes a Viernes 08:30 a 14:00 hrs',
                delegado: 'Marcelo Salazar Peña',
                cargoDelegado: 'Coordinador & Delegado Centro',
                cumplimiento: 95.0,
                statusSemaforo: 'Verde (Óptimo)',
                colorSemaforo: '#10B981',
                atencionesMes: 980,
                vecinosRegistrados: '38.400',
                tuboResueltos: '96%',
                satisfaccion: '96.2%',
                barrios: ['Plaza de Armas', 'Barrio Almagro', 'Santa Inés', 'Colina El Pino', 'Barrio Carmona', 'Zona Típica Colonial'],
                resumen: 'Comprende el casco histórico fundacional de La Serena. Concentra la atención preferencial de adultos mayores, trámites de patentes, regularizaciones patrimoniales y apoyo a juntas vecinales urbanas.',
                funcionarios: [
                    { nombre: 'Marcelo Salazar Peña', rut: '13.456.789-0', cargo: 'Coordinador General SGR & Jefatura', email: 'coordinacion.sgr@laserena.cl', rol: 'Coordinador', avatar: 'MS' },
                    { nombre: 'Camila Araya Miranda', rut: '18.345.678-K', cargo: 'Gestora Social Territorial', email: 'gestora.centro@laserena.cl', rol: 'Gestor Territorial', avatar: 'CA' },
                    { nombre: 'Valeria Cáceres Soto', rut: '16.789.012-3', cargo: 'Directora de Atención Ciudadana', email: 'auditoria.externa@laserena.cl', rol: 'Usuario de Consulta', avatar: 'VC' },
                    { nombre: 'Jorge Cortés Olivares', rut: '15.432.198-7', cargo: 'Verificador Técnico de Evidencias', email: 'verificador.centro@laserena.cl', rol: 'Verificador', avatar: 'JC' }
                ],
                metricasAtencion: [
                    { tipo: 'Registro Social de Hogares (RSH)', cantidad: 420, porcentaje: 43 },
                    { tipo: 'Orientación Legal y Social', cantidad: 260, porcentaje: 27 },
                    { tipo: 'Trámites de Permisos y Certificados', cantidad: 190, porcentaje: 19 },
                    { tipo: 'Reclamos y Solicitudes Obras', cantidad: 110, porcentaje: 11 }
                ]
            },
            'companias': {
                id: 'companias',
                nombre: 'Delegación Las Compañías',
                sector: 'Zona Norte del Río Elqui (Mayor Población)',
                foto: '/static/img/delegacion_companias.jpg',
                direccion: 'Av. Espejo del Sol 210, Las Compañías',
                telefono: '+56 51 220 6710',
                email: 'delegacion.companias@laserena.cl',
                horario: 'Lunes a Viernes 08:30 a 14:00 hrs',
                delegado: 'Gonzalo Pizarro Rojas',
                cargoDelegado: 'Delegado Municipal Las Compañías',
                cumplimiento: 88.0,
                statusSemaforo: 'Verde (Conforme)',
                colorSemaforo: '#7C3AED',
                atencionesMes: 1150,
                vecinosRegistrados: '110.000',
                tuboResueltos: '89%',
                satisfaccion: '93.5%',
                barrios: ['Compañía Alta', 'Compañía Baja', 'Villa Los Aromos', 'Parque Nevada', 'Villa El Romero', 'Las Rosas'],
                resumen: 'Es el sector con mayor volumen poblacional de La Serena. Destaca por alta demanda en operativos en terreno, postulación a subsidios habitacionales, enlace con comités de seguridad y aseo barrial.',
                funcionarios: [
                    { nombre: 'Gonzalo Pizarro Rojas', rut: '14.234.567-8', cargo: 'Delegado Municipal Las Compañías', email: 'delegado.companias@laserena.cl', rol: 'Delegado', avatar: 'GP' },
                    { nombre: 'Rodrigo Tapia Gallardo', rut: '17.892.456-3', cargo: 'Gestor Territorial Operativo', email: 'gestor.companias@laserena.cl', rol: 'Gestor Territorial', avatar: 'RT' },
                    { nombre: 'Esteban Morales Vega', rut: '15.678.901-2', cargo: 'Verificador Técnico de Operaciones', email: 'verificador@laserena.cl', rol: 'Verificador', avatar: 'EM' },
                    { nombre: 'Romina Carvajal Díaz', rut: '18.901.234-5', cargo: 'Asistente Social OO.CC.', email: 'romina.companias@laserena.cl', rol: 'Funcionario', avatar: 'RC' }
                ],
                metricasAtencion: [
                    { tipo: 'Operativos Vecinales y Terreno', cantidad: 490, porcentaje: 42 },
                    { tipo: 'Fichas RSH y Ayudas Sociales', cantidad: 350, porcentaje: 30 },
                    { tipo: 'Seguridad Ciudadana y Comités', cantidad: 180, porcentaje: 16 },
                    { tipo: 'Aseo y Retiro de Escombros', cantidad: 130, porcentaje: 12 }
                ]
            },
            'pampa': {
                id: 'pampa',
                nombre: 'Delegación La Pampa',
                sector: 'Zona Sur Urbano & El Milagro',
                foto: '/static/img/delegacion_pampa.jpg',
                direccion: 'Av. Juan Cisternas 2855, La Pampa',
                telefono: '+56 51 220 6820',
                email: 'delegacion.pampa@laserena.cl',
                horario: 'Lunes a Viernes 08:30 a 14:00 hrs',
                delegado: 'Patricia Vega Albarracín',
                cargoDelegado: 'Delegada Territorial La Pampa',
                cumplimiento: 92.0,
                statusSemaforo: 'Verde (Óptimo)',
                colorSemaforo: '#2563EB',
                atencionesMes: 640,
                vecinosRegistrados: '48.000',
                tuboResueltos: '93%',
                satisfaccion: '95.0%',
                barrios: ['La Pampa', 'San Joaquín Bajo', 'El Milagro I y II', 'Cuatro Esquinas Poniente', 'La Chimba Urbana'],
                resumen: 'Polo residencial y de servicios en continuo desarrollo al sur de la ciudad. Fuerte gestión en mantención de plazas y áreas verdes, luminarias públicas y actividades con adultos mayores.',
                funcionarios: [
                    { nombre: 'Patricia Vega Albarracín', rut: '16.123.456-7', cargo: 'Delegada Territorial La Pampa', email: 'patricia.pampa@laserena.cl', rol: 'Delegado', avatar: 'PV' },
                    { nombre: 'Kevin Encina Molina', rut: '17.234.567-9', cargo: 'Gestor de Operaciones y Cuadrilla', email: 'kevin.pampa@laserena.cl', rol: 'Gestor Territorial', avatar: 'KE' },
                    { nombre: 'Mauricio Ramos Cortés', rut: '14.890.123-4', cargo: 'Inspector Comunal de Obras', email: 'mramos@laserena.cl', rol: 'Funcionario', avatar: 'MR' }
                ],
                metricasAtencion: [
                    { tipo: 'Gestión de Parques y Áreas Verdes', cantidad: 240, porcentaje: 38 },
                    { tipo: 'Seguridad y Luminarias Públicas', cantidad: 190, porcentaje: 30 },
                    { tipo: 'Atención Social y Tercera Edad', cantidad: 130, porcentaje: 20 },
                    { tipo: 'Trámites de Tránsito y Señalética', cantidad: 80, porcentaje: 12 }
                ]
            },
            'costa': {
                id: 'costa',
                nombre: 'Delegación Avenida del Mar',
                sector: 'Borde Costero & Zona Turística',
                foto: '/static/img/delegacion_costa.jpg',
                direccion: 'Av. del Mar 1200 (Frente a Costanera)',
                telefono: '+56 51 220 6900',
                email: 'delegacion.mar@laserena.cl',
                horario: 'Lunes a Domingo 09:00 a 18:00 hrs',
                delegado: 'Christian Cerda Núñez',
                cargoDelegado: 'Encargado Territorial Borde Costero',
                cumplimiento: 91.0,
                statusSemaforo: 'Verde (Óptimo)',
                colorSemaforo: '#06B6D4',
                atencionesMes: 410,
                vecinosRegistrados: '22.000',
                tuboResueltos: '91%',
                satisfaccion: '97.0%',
                barrios: ['Avenida del Mar', 'Sector Faro Monumental', 'Playa Mansa', 'Cuatro Esquinas Playa', 'Los Nísperos Costeros'],
                resumen: 'Representa el principal polo turístico, gastronómico y hotelero comunal. Coordina fiscalización en playas, eventos estivales, ciclovías y permisos de temporada.',
                funcionarios: [
                    { nombre: 'Christian Cerda Núñez', rut: '15.345.678-2', cargo: 'Encargado Territorial Borde Costero', email: 'ccerda@laserena.cl', rol: 'Delegado', avatar: 'CC' },
                    { nombre: 'Claudia Monroy Soto', rut: '16.456.789-1', cargo: 'Coordinadora de Información Turística', email: 'cmonroy@laserena.cl', rol: 'Funcionario', avatar: 'CM' },
                    { nombre: 'Héctor Tapia Araya', rut: '13.987.654-3', cargo: 'Inspector de Borde Costero y Terreno', email: 'htapia@laserena.cl', rol: 'Verificador', avatar: 'HT' }
                ],
                metricasAtencion: [
                    { tipo: 'Permisos Precarios y Borde Costero', cantidad: 160, porcentaje: 39 },
                    { tipo: 'Fiscalización y Limpieza de Playas', cantidad: 120, porcentaje: 29 },
                    { tipo: 'Orientación al Vecino y Turista', cantidad: 85, porcentaje: 21 },
                    { tipo: 'Seguridad y Patrullaje Costero', cantidad: 45, porcentaje: 11 }
                ]
            },
            'antena': {
                id: 'antena',
                nombre: 'Delegación La Antena',
                sector: 'Colina Oriente & Mirador Cerro Grande',
                foto: '/static/img/delegacion_antena.jpg',
                direccion: 'Calle 18 de Septiembre 340, La Antena',
                telefono: '+56 51 220 6840',
                email: 'delegacion.antena@laserena.cl',
                horario: 'Lunes a Viernes 08:30 a 14:00 hrs',
                delegado: 'Arturo Godoy Rivera',
                cargoDelegado: 'Delegado Municipal La Antena / San Joaquín',
                cumplimiento: 84.0,
                statusSemaforo: 'Ámbar (Atención)',
                colorSemaforo: '#F59E0B',
                atencionesMes: 490,
                vecinosRegistrados: '32.000',
                tuboResueltos: '82%',
                satisfaccion: '91.8%',
                barrios: ['La Antena', 'La Florida', 'Población Coll', 'Mirador Cerro Grande', 'Villa Vista Hermosa'],
                resumen: 'Abarca el sector alto oriental de la comuna. Prioriza programas de pavimentación participativa, juntas de vecinos, talleres comunitarios y operativos sanitarios.',
                funcionarios: [
                    { nombre: 'Arturo Godoy Rivera', rut: '12.876.543-9', cargo: 'Delegado Municipal La Antena', email: 'agodoy@laserena.cl', rol: 'Delegado', avatar: 'AG' },
                    { nombre: 'Scarlett Williams Medalla', rut: '18.123.456-K', cargo: 'Gestora Social RSH Terreno', email: 'swilliams@laserena.cl', rol: 'Gestor Territorial', avatar: 'SW' },
                    { nombre: 'Daniela Olivares Vega', rut: '17.345.678-0', cargo: 'Atención a Organizaciones Comunitarias', email: 'dolivares@laserena.cl', rol: 'Funcionario', avatar: 'DO' }
                ],
                metricasAtencion: [
                    { tipo: 'Postulación a Fondos y Subsidios', cantidad: 180, porcentaje: 37 },
                    { tipo: 'RSH y Registro de Vecinos', cantidad: 150, porcentaje: 31 },
                    { tipo: 'Operativos Sanitarios y Desratización', cantidad: 95, porcentaje: 19 },
                    { tipo: 'Talleres Deportivos y Comunitarios', cantidad: 65, porcentaje: 13 }
                ]
            },
            'rural': {
                id: 'rural',
                nombre: 'Delegación Sector Rural',
                sector: 'Valle del Elqui Rural & Quebradas',
                foto: '/static/img/delegacion_rural.jpg',
                direccion: 'Ruta 41 Km 15, Sector Algarrobito',
                telefono: '+56 51 220 6950',
                email: 'delegacion.rural@laserena.cl',
                horario: 'Lunes a Viernes 08:30 a 14:00 hrs',
                delegado: 'Fernando Carvajal Pizarro',
                cargoDelegado: 'Delegado Municipal Sector Rural',
                cumplimiento: 71.4,
                statusSemaforo: 'Rojo (Crítica)',
                colorSemaforo: '#EF4444',
                atencionesMes: 320,
                vecinosRegistrados: '18.500',
                tuboResueltos: '71%',
                satisfaccion: '88.5%',
                barrios: ['Algarrobito', 'Altovalsol', 'El Romero Rural', 'Lambert', 'Quebrada de Talca', 'Las Rojas', 'Pelicana'],
                resumen: 'Cubre la vasta área rural y pueblos tradicionales del Valle de Elqui comunal. Atención de APR (Agua Potable Rural), caminos de tierra, crianceros y emergencias hídricas.',
                funcionarios: [
                    { nombre: 'Fernando Carvajal Pizarro', rut: '11.987.654-1', cargo: 'Delegado Municipal Sector Rural', email: 'fcarvajal@laserena.cl', rol: 'Delegado', avatar: 'FC' },
                    { nombre: 'Esteban Collao Barraza', rut: '16.543.210-8', cargo: 'Técnico de Terreno APR y Caminos', email: 'ecollao@laserena.cl', rol: 'Gestor Territorial', avatar: 'EC' },
                    { nombre: 'María Inés Alfaro', rut: '14.234.123-7', cargo: 'Enlace Fomento Productivo Rural', email: 'malfaro@laserena.cl', rol: 'Funcionario', avatar: 'MA' }
                ],
                metricasAtencion: [
                    { tipo: 'Abastecimiento APR y Camiones Aljibe', cantidad: 130, porcentaje: 41 },
                    { tipo: 'Mantención de Caminos Rurales', cantidad: 90, porcentaje: 28 },
                    { tipo: 'Fichas Sociales RSH Rural', cantidad: 60, porcentaje: 19 },
                    { tipo: 'Fomento Productivo y Crianceros', cantidad: 40, porcentaje: 12 }
                ]
            }
        };

        let delegacionSeleccionadaActiva = null;

        function initDelegacionesView() {
            const grid = document.getElementById('delegacionesCardsGrid');
            if (!grid) return;
            grid.innerHTML = '';

            Object.values(datasetDelegacionesDetalle).forEach((d, idx) => {
                const card = document.createElement('div');
                card.className = `delegacion-modular-glass-card spotlight-card stagger-item ${delegacionSeleccionadaActiva === d.id ? 'active-delegacion' : ''}`;
                card.id = `card-del-${d.id}`;
                card.style.setProperty('--stagger-i', idx);
                card.onclick = () => {
                    cerrarDrawerExpediente();
                    seleccionarDelegacion(d.id);
                };

                let badgeGlowHtml = '';
                if (d.cumplimiento >= 85) {
                    badgeGlowHtml = `<span class="badge-glow-emerald">Operativa</span>`;
                } else if (d.cumplimiento >= 75) {
                    badgeGlowHtml = `<span class="badge-glow-amber">Alta Demanda</span>`;
                } else {
                    badgeGlowHtml = `<span class="badge-glow-carmine">Contingencia</span>`;
                }

                const esperaMedia = d.id === 'rural' ? '5 min' : d.id === 'companias' ? '18 min' : d.id === 'centro' ? '12 min' : '8 min';
                const gestorTurno = d.funcionarios && d.funcionarios.length > 0 ? d.funcionarios[0].nombre : d.delegado;

                card.innerHTML = `
                    <div>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            ${badgeGlowHtml}
                            <span class="badge bg-light text-dark border px-2 py-1 shadow-xs" style="font-size: 0.74rem; font-weight: 700;">
                                <i class="bi bi-star-fill text-warning me-1"></i>${d.satisfaccion || '98.2%'}
                            </span>
                        </div>

                        <div class="mb-3">
                            <div class="text-muted text-uppercase fw-bold" style="font-size: 0.68rem; letter-spacing: 0.5px;">${d.sector}</div>
                            <h4 class="fw-bold mb-1" style="color: var(--muni-navy); font-size: 1.18rem;">${d.nombre}</h4>
                            <div class="text-secondary small text-truncate" style="font-size: 0.78rem;">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i>${d.direccion}
                            </div>
                        </div>

                        <div class="p-2 rounded-3 mb-3" style="background: rgba(27, 54, 93, 0.035); border: 1px solid rgba(226, 232, 240, 0.85);">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="text-muted small" style="font-size: 0.73rem;"><i class="bi bi-person-badge text-primary me-1"></i>Gestor Turno:</span>
                                <span class="fw-bold text-dark small" style="font-size: 0.76rem;">${gestorTurno}</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-muted small" style="font-size: 0.73rem;"><i class="bi bi-hourglass-split text-warning me-1"></i>Espera Media:</span>
                                <span class="fw-bold text-dark small font-monospace" style="font-size: 0.76rem;">${esperaMedia}</span>
                            </div>
                        </div>
                    </div>

                    <div class="d-flex align-items-center justify-content-between pt-2 border-top">
                        <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1" style="font-size: 0.72rem; font-weight: 600;">
                            ${d.casosActivos || 42} Casos Activos
                        </span>
                        <div class="btn-expediente-sede-link" title="Ver detalles de sede">
                            <span>Ver Delegación</span>
                            <i class="bi bi-arrow-right expediente-arrow"></i>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
            initSpotlightEffect();
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
                doc.text(`Horario: ${data.horario} | Contacto: ${data.email}`, 14, 45);

                const tableBody = [
                    ['Atenciones Mensuales', `${data.atencionesMes} atenciones`],
                    ['Población Territorial', `${data.vecinosRegistrados} vecinos`],
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

            // Actualizar estilo activo en las tarjetas
            document.querySelectorAll('.delegacion-card').forEach(c => c.classList.remove('active-delegacion'));
            const activeCard = document.getElementById(`card-del-${id}`);
            if (activeCard) activeCard.classList.add('active-delegacion');

            const panel = document.getElementById('panelDetalleDelegacion');
            if (!panel) return;

            // Construir Funcionarios HTML
            const funcionariosHtml = data.funcionarios.map(f => `
                <div class="col-md-6 col-lg-3">
                    <div class="p-3 rounded-3 border bg-light h-100 d-flex flex-column justify-content-between">
                        <div class="d-flex align-items-center gap-2 mb-2">
                            <div class="user-avatar-pill ${f.rol.includes('Coordinador') || f.rol.includes('Delegado') ? 'admin' : ''}" style="width:38px; height:38px; font-size:0.85rem;">
                                ${f.avatar}
                            </div>
                            <div style="min-width:0;">
                                <div class="fw-bold text-dark text-truncate" title="${f.nombre}">${f.nombre}</div>
                                <div class="text-muted small">${f.rut}</div>
                            </div>
                        </div>
                        <div>
                            <div class="small text-secondary mb-1"><strong>Cargo:</strong> ${f.cargo}</div>
                            <span class="role-badge-pill role-badge-${f.rol.toLowerCase().includes('gestor') ? 'gestor' : f.rol.toLowerCase().includes('verificador') ? 'verificador' : 'admin'} mb-2">
                                ${f.rol}
                            </span>
                            <div class="pt-2 border-top">
                                <a href="mailto:${f.email}" class="small text-decoration-none text-primary d-flex align-items-center gap-1 text-truncate">
                                    <i class="bi bi-envelope"></i> ${f.email}
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

            // Construir Barrios HTML
            const barriosHtml = data.barrios.map(b => `
                <span class="badge bg-white text-dark border px-3 py-2 rounded-pill me-1 mb-2 shadow-sm" style="font-size:0.8rem;">
                    <i class="bi bi-geo-alt-fill text-danger me-1"></i> ${b}
                </span>
            `).join('');

            // Construir Métricas de Atención
            const metricasHtml = data.metricasAtencion.map(m => `
                <div class="mb-3">
                    <div class="d-flex justify-content-between small fw-bold mb-1">
                        <span>${m.tipo}</span>
                        <span class="text-primary">${m.cantidad} (${m.porcentaje}%)</span>
                    </div>
                    <div class="progress" style="height: 7px; border-radius: 4px;">
                        <div class="progress-bar" style="width: ${m.porcentaje}%; background-color: ${data.colorSemaforo};"></div>
                    </div>
                </div>
            `).join('');

            panel.innerHTML = `
                <!-- Barra de Navegación de Delegación (Sin modales ni desenfoques) -->
                <div class="mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <button class="btn btn-sm btn-outline-primary rounded-pill px-3 py-1 fw-bold shadow-xs" onclick="document.getElementById('panelDetalleDelegacion').style.display='none'; document.getElementById('view-delegaciones').scrollIntoView({behavior: 'smooth'});">
                        <i class="bi bi-arrow-left me-1"></i> Volver a todas las delegaciones
                    </button>
                    <span class="badge bg-light text-secondary border px-3 py-1 small fw-semibold">
                        <i class="bi bi-geo-alt-fill text-danger me-1"></i> Ficha Territorial: ${data.nombre}
                    </span>
                </div>

                <!-- Encabezado con degradado Glassmorphism -->
                <div class="delegacion-detail-header">
                    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
                        <div class="d-flex align-items-center gap-3">
                            <div style="width: 52px; height: 52px; border-radius: 14px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; color: #FFF;">
                                <i class="bi bi-building-check"></i>
                            </div>
                            <div>
                                <div class="d-flex align-items-center gap-2 mb-1">
                                    <span class="badge bg-warning text-dark fw-bold rounded-pill" style="font-size:0.75rem;">DELEGACIÓN SELECCIONADA</span>
                                    <span class="badge rounded-pill" style="background: ${data.colorSemaforo}; color:#FFF; font-size:0.75rem;">${data.statusSemaforo}</span>
                                </div>
                                <h3 class="m-0 fw-bold text-white">${data.nombre}</h3>
                                <p class="text-white-50 m-0 small">${data.sector}</p>
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <button class="btn btn-outline-light btn-sm rounded-pill px-3" onclick="exportarFichaDelegacionPDF('${data.id}')">
                                <i class="bi bi-file-earmark-pdf me-1"></i> Ficha Delegación PDF
                            </button>
                        </div>
                    </div>

                    <!-- Datos de contacto y sede -->
                    <div class="row g-2 mt-3 pt-3 border-top border-white-50 text-white small">
                        <div class="col-md-4">
                            <i class="bi bi-geo-alt-fill text-warning me-1"></i> <strong>Sede:</strong> ${data.direccion}
                        </div>
                        <div class="col-md-3">
                            <i class="bi bi-telephone-fill text-info me-1"></i> <strong>Fono:</strong> ${data.telefono}
                        </div>
                        <div class="col-md-3">
                            <i class="bi bi-clock-fill text-success me-1"></i> <strong>Horario:</strong> ${data.horario}
                        </div>
                        <div class="col-md-2 text-md-end">
                            <i class="bi bi-person-fill text-warning me-1"></i> <strong>Delegado(a):</strong> ${data.delegado}
                        </div>
                    </div>
                </div>

                <div class="p-4">
                    <!-- Resumen Territorial -->
                    <div class="alert alert-light border-start border-4 mb-4 py-2 px-3 small text-secondary" style="border-left-color: ${data.colorSemaforo} !important; background: #F8FAFC;">
                        <i class="bi bi-info-circle-fill text-primary me-2"></i> ${data.resumen}
                    </div>

                    <!-- KPIs Específicos de esta Delegación -->
                    <div class="row g-3 mb-4">
                        <div class="col-sm-6 col-md-3">
                            <div class="p-3 rounded-3 border bg-light text-center">
                                <div class="text-muted small fw-semibold">Cumplimiento de Metas</div>
                                <div class="fs-3 fw-bold" style="color:${data.colorSemaforo};">${data.cumplimiento}%</div>
                                <div class="progress mt-2" style="height: 6px;">
                                    <div class="progress-bar" style="width: ${data.cumplimiento}%; background-color: ${data.colorSemaforo};"></div>
                                </div>
                            </div>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <div class="p-3 rounded-3 border bg-light text-center">
                                <div class="text-muted small fw-semibold">Atenciones del Mes</div>
                                <div class="fs-3 fw-bold text-dark">${data.atencionesMes}</div>
                                <small class="text-success fw-semibold"><i class="bi bi-arrow-up-right me-1"></i>En curso</small>
                            </div>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <div class="p-3 rounded-3 border bg-light text-center">
                                <div class="text-muted small fw-semibold">Vecinos Atendidos</div>
                                <div class="fs-3 fw-bold text-dark">${data.vecinosRegistrados}</div>
                                <small class="text-muted">Población territorial</small>
                            </div>
                        </div>
                        <div class="col-sm-6 col-md-3">
                            <div class="p-3 rounded-3 border bg-light text-center">
                                <div class="text-muted small fw-semibold">Casos Resueltos (Tubo)</div>
                                <div class="fs-3 fw-bold text-primary">${data.tuboResueltos}</div>
                                <small class="text-info fw-semibold"><i class="bi bi-shield-check me-1"></i>Satisfacción: ${data.satisfaccion}</small>
                            </div>
                        </div>
                    </div>

                    <!-- Pestaña 1: Dotación Funcionaria de esta Delegación -->
                    <div class="mb-4">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <h5 class="fw-bold m-0 text-dark">
                                <i class="bi bi-people-fill text-primary me-2"></i> Dotación Funcionaria Asignada (${data.funcionarios.length} funcionarios)
                            </h5>
                            <button class="btn btn-sm btn-outline-primary rounded-pill px-3" onclick="switchView('usuarios')">
                                <i class="bi bi-gear-fill me-1"></i> Gestionar en Usuarios
                            </button>
                        </div>
                        <div class="row g-3">
                            ${funcionariosHtml}
                        </div>
                    </div>

                    <div class="row g-4 pt-2">
                        <!-- Pestaña 2: Barrios y Unidades Vecinales -->
                        <div class="col-lg-7">
                            <h5 class="fw-bold mb-3 text-dark">
                                <i class="bi bi-map-fill text-danger me-2"></i> Barrios y Sectores Atendidos
                            </h5>
                            <div class="p-3 rounded-3 border bg-light mb-3">
                                ${barriosHtml}
                            </div>
                            <small class="text-muted">
                                * Cada sector cuenta con enlace directo con directivas de Juntas de Vecinos y clubes de adultos mayores correspondientes.
                            </small>
                        </div>

                        <!-- Pestaña 3: Desglose de Atenciones por Tipo -->
                        <div class="col-lg-5">
                            <h5 class="fw-bold mb-3 text-dark">
                                <i class="bi bi-pie-chart-fill text-success me-2"></i> Distribución de Atenciones
                            </h5>
                            <div class="p-3 rounded-3 border bg-light">
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

            mostrarToast(`✓ Datos de ${data.nombre} cargados correctamente.`);
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
            doc.text(`Teléfono: ${data.telefono} | Correo: ${data.email} | Delegado: ${data.delegado}`, 14, 44);
            doc.text(`Cumplimiento de Metas: ${data.cumplimiento}% | Atenciones del Mes: ${data.atencionesMes} | Vecinos: ${data.vecinosRegistrados}`, 14, 49);

            // Tabla de funcionarios
            const rowsStaff = data.funcionarios.map(f => [f.nombre, f.rut, f.cargo, f.rol, f.email]);
            doc.autoTable({
                head: [['Funcionario', 'RUT', 'Cargo', 'Rol', 'Correo']],
                body: rowsStaff,
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
                body: rowsMetrics,
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
                users_count: 1,
                users_sample: ['Administrador General']
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
                users_count: 2,
                users_sample: ['María López', 'Juan Pérez']
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
                users_count: 1,
                users_sample: ['Carlos Díaz']
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
                users_count: 1,
                users_sample: ['Verificador Técnico']
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
                users_count: 1,
                users_sample: ['Coordinador General']
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
                users_count: 1,
                users_sample: ['Delegado Las Compañías']
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
                users_count: 2,
                users_sample: ['Funcionario Operativo']
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
                }
                filtrarRoles();
                if (mostrarAviso) {
                    mostrarToast('✓ Base de datos sincronizada: ' + datasetRoles.length + ' roles activos.');
                }
            } catch (err) {
                console.warn("Error al cargar roles desde API (usando catálogo local):", err);
                filtrarRoles();
            }
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
                        <span class="fw-bold" style="color: var(--muni-navy); font-size: 0.94rem;">${r.name}</span>
                    </td>
                    <td class="text-secondary" style="font-size: 0.88rem;">${r.description || 'Sin descripción'}</td>
                    <td>${permsHtml}</td>
                    <td class="text-center">
                        <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 0.80rem;" title="${(r.users_sample || []).join(', ') || 'Sin funcionarios vinculados'}">
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

            datasetCatalogPermisos.forEach(mod => {
                const col = document.createElement('div');
                col.className = 'col-md-6 col-lg-4';

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
                                <input type="checkbox" name="rolPermisoCheckbox" value="${p.code}" ${isChecked ? 'checked' : ''} onchange="actualizarContadorPermisosModal()">
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
                    <div class="perm-module-card h-100 d-flex flex-column">
                        <div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom">
                            <div class="d-flex align-items-center gap-2">
                                <i class="bi ${mod.icon || 'bi-folder'} text-primary fs-5"></i>
                                <div>
                                    <h6 class="fw-bold m-0" style="font-size: 0.90rem; color: var(--muni-navy);">${mod.module_name}</h6>
                                    <span class="text-muted" style="font-size: 0.70rem;">${mod.description}</span>
                                </div>
                            </div>
                            <button type="button" class="btn btn-sm btn-link text-decoration-none p-0 fw-semibold small" onclick="toggleModuloCompleto('${mod.module_id}', this)">
                                ${allModChecked ? 'Desmarcar' : 'Todos'}
                            </button>
                        </div>
                        <div class="row g-2 flex-grow-1" id="mod-container-${mod.module_id}">
                            ${permsInputs}
                        </div>
                    </div>
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
                if (elTitle) elTitle.innerHTML = `<i class="bi bi-person-plus text-primary me-2"></i> Nuevo Rol`;
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
                if (elTitle) elTitle.innerHTML = `<i class="bi bi-pencil me-2"></i> Editar Rol: ${rol.name}`;
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

            if (!name) {
                alert('El nombre del rol es obligatorio.');
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
                } else {
                    datasetRoles.push({
                        id: Date.now(),
                        name: name,
                        description: description,
                        is_system: false,
                        permissions: checkedPerms,
                        permissions_count: checkedPerms.length,
                        users_count: 0
                    });
                }

                if (bsModalRol) bsModalRol.hide();
                filtrarRoles();
                mostrarToast(data.message || (id ? 'Rol actualizado exitosamente.' : 'Rol creado exitosamente.'));
            } catch (err) {
                console.error("Error al guardar rol:", err);
                // Fallback optimista en caso de problemas de red
                if (id) {
                    const idx = datasetRoles.findIndex(r => r.id === parseInt(id));
                    if (idx !== -1) {
                        datasetRoles[idx].name = name;
                        datasetRoles[idx].description = description;
                        datasetRoles[idx].permissions = checkedPerms;
                        datasetRoles[idx].permissions_count = checkedPerms.length;
                    }
                } else {
                    datasetRoles.push({
                        id: Date.now(),
                        name: name,
                        description: description,
                        is_system: false,
                        permissions: checkedPerms,
                        permissions_count: checkedPerms.length,
                        users_count: 0
                    });
                }
                if (bsModalRol) bsModalRol.hide();
                filtrarRoles();
                mostrarToast(id ? 'Rol actualizado correctamente.' : 'Rol creado correctamente.');
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

            const isCoreProtected = (rol.name === 'Administrador' || rol.name === 'Operador' || rol.name === 'Consultor');
            const hasUsers = (rol.users_count > 0);

            if (isCoreProtected) {
                if (elAviso) elAviso.innerHTML = `<span class="text-danger fw-bold"><i class="bi bi-shield-lock-fill"></i> ACCIÓN DENEGADA:</span> El rol <strong>"${rol.name}"</strong> es uno de los roles fundamentales del sistema y no puede eliminarse.`;
                if (elDetalle) elDetalle.className = 'alert alert-danger py-2 text-start small mb-0';
                if (btnConfirm) btnConfirm.disabled = true;
            } else if (hasUsers) {
                if (elAviso) elAviso.innerHTML = `<span class="text-warning fw-bold"><i class="bi bi-exclamation-circle-fill"></i> ADVERTENCIA:</span> Este rol tiene <strong>${rol.users_count} funcionario(s)</strong> asignado(s). Reasigne primero a estos usuarios para poder dar de baja el rol.`;
                if (elDetalle) elDetalle.className = 'alert alert-warning py-2 text-start small mb-0';
                if (btnConfirm) btnConfirm.disabled = true;
            } else {
                if (elAviso) elAviso.textContent = `Esta acción dará de baja el rol "${rol.name}" de forma permanente en la base de datos municipal.`;
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
                if (bsModalEliminarRol) bsModalEliminarRol.hide();
                filtrarRoles();
                mostrarToast(data.message || 'Rol eliminado exitosamente.');
            } catch (err) {
                console.warn("Fallo endpoint eliminar rol (fallback local):", err);
                datasetRoles = datasetRoles.filter(r => r.id !== rolEliminarId);
                if (bsModalEliminarRol) bsModalEliminarRol.hide();
                filtrarRoles();
                mostrarToast('Rol removido del panel.');
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
                if (data.success && data.role) {
                    datasetRoles.push(data.role);
                } else {
                    datasetRoles.push({
                        id: Date.now(),
                        name: `${origen.name} (Copia)`,
                        description: `Copia basada en ${origen.name}`,
                        is_system: false,
                        permissions: [...(origen.permissions || [])],
                        permissions_count: (origen.permissions || []).length,
                        users_count: 0
                    });
                }
                filtrarRoles();
                mostrarToast(`Rol duplicado como "${origen.name} (Copia)".`);
            } catch (err) {
                datasetRoles.push({
                    id: Date.now(),
                    name: `${origen.name} (Copia)`,
                    description: `Copia basada en ${origen.name}`,
                    is_system: false,
                    permissions: [...(origen.permissions || [])],
                    permissions_count: (origen.permissions || []).length,
                    users_count: 0
                });
                filtrarRoles();
                mostrarToast(`Rol duplicado como "${origen.name} (Copia)".`);
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

            if (!code || !name) {
                alert('Código y nombre de la función son requeridos.');
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
                if (data.success && data.catalog) {
                    datasetCatalogPermisos = data.catalog;
                } else {
                    const targetMod = datasetCatalogPermisos.find(m => m.module_id === moduleId) || datasetCatalogPermisos[0];
                    targetMod.permissions.push({ code, name, desc });
                }

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
                const targetMod = datasetCatalogPermisos.find(m => m.module_id === moduleId) || datasetCatalogPermisos[0];
                targetMod.permissions.push({ code, name, desc });
                if (bsModalNuevaFuncion) bsModalNuevaFuncion.hide();
                filtrarRoles();
                mostrarToast(`Nueva función "${name}" registrada.`);
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
                    <div class="fw-bold" style="font-size: 0.82rem; color: var(--muni-navy);">${r.name}</div>
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
                                <input type="checkbox" class="myadmin-toggle-switch" data-role-id="${r.id}" data-perm-code="${p.code}" ${isChecked ? 'checked' : ''}>
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
            if (!table) return;

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

            // Guardar en la base de datos para cada rol modificado
            let updatedCount = 0;
            for (const [rId, perms] of Object.entries(rolePermsMap)) {
                const role = datasetRoles.find(r => r.id === parseInt(rId));
                if (role) {
                    role.permissions = perms;
                    role.permissions_count = perms.length;
                    try {
                        await fetch(`/api/roles/${rId}/update/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken') || ''
                            },
                            body: JSON.stringify({
                                name: role.name,
                                description: role.description,
                                permissions: perms
                            })
                        });
                        updatedCount++;
                    } catch (e) {
                        console.warn("Error guardando rol en matriz:", e);
                    }
                }
            }

            if (bsModalMatrizMyAdmin) bsModalMatrizMyAdmin.hide();
            filtrarRoles();
            mostrarToast(`Matriz de permisos guardada: ${updatedCount} roles actualizados.`);
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
            const t = document.getElementById('muniToast');
            document.getElementById('toastMessage').textContent = msg;
            t.classList.add('show');
            clearTimeout(toastT);
            toastT = setTimeout(() => cerrarToast(), 3500);
        }
        function cerrarToast() { document.getElementById('muniToast').classList.remove('show'); }
