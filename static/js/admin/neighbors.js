        async function cargarVecinosDesdeDB(mostrarAviso = false, silencioError = false) {
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
                ejecutarFiltroCompletoVecinos(false);
                if (mostrarAviso) mostrarToast(`✓ ${datasetVecinos.length} vecinos cargados desde la base de datos`);
                return true;
            } catch (error) {
                console.error('Error cargando vecinos:', error);
                if (!silencioError) Swal.fire({icon: 'error', title: 'No se pudieron cargar los vecinos', text: error.message, confirmButtonColor: '#A30F32'});
                return false;
            }
        }

        function renderTablaVecinos() {
            const tbody = document.getElementById('tablaVecinosBody');
            if (!tbody) return;
            tbody.innerHTML = '';

            const totalPaginas = Math.max(1, Math.ceil(filasFiltradasVecinos.length / filasPorPagina));
            paginaActual = Math.min(Math.max(1, paginaActual), totalPaginas);
            actualizarPaginadorVecinos(totalPaginas);

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

            [['colRUT', 'col-rut'], ['colDireccion', 'col-dir'], ['colTelefono', 'col-tel'],
                ['colTerritorio', 'col-terr'], ['colEstado', 'col-est']].forEach(([id, clase]) => {
                const control = document.getElementById(id);
                if (control) toggleColumna(clase, control.checked);
            });

            document.getElementById('lblRegistrosInfo').textContent = `Mostrando ${inicio + 1} - ${Math.min(fin, filasFiltradasVecinos.length)} de ${filasFiltradasVecinos.length} registros`;
            actualizarIndicadorTablaVecinos(inicio + 1, Math.min(fin, filasFiltradasVecinos.length), filasFiltradasVecinos.length);
            actualizarIndicadoresDiscretos();
            actualizarBarraAccionesMasivas();
        }

        function togglePanelFiltros() {
            const open = document.getElementById('panelFiltrosAvanzados').classList.toggle('show');
            const button = document.getElementById('btnToggleFiltros');
            button.classList.toggle('active', open);
            button.setAttribute('aria-expanded', String(open));
        }

        function ejecutarFiltroCompletoVecinos(reiniciarPagina = true) {
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

            if (reiniciarPagina) paginaActual = 1;
            renderTablaVecinos();
        }

        function actualizarPaginadorVecinos(totalPaginas) {
            const container = document.getElementById('paginadorPills');
            if (!container) return;
            container.innerHTML = '';
            if (totalPaginas <= 1) return;
            const paginas = new Set([1, totalPaginas]);
            for (let pagina = Math.max(1, paginaActual - 2); pagina <= Math.min(totalPaginas, paginaActual + 2); pagina++) paginas.add(pagina);
            let anterior = 0;
            [...paginas].sort((a, b) => a - b).forEach(pagina => {
                if (pagina - anterior > 1) {
                    const separador = document.createElement('span');
                    separador.textContent = '…';
                    separador.setAttribute('aria-hidden', 'true');
                    container.appendChild(separador);
                }
                const boton = document.createElement('button');
                boton.type = 'button';
                boton.className = `page-pill${pagina === paginaActual ? ' active' : ''}`;
                boton.textContent = pagina;
                boton.setAttribute('aria-label', `Página ${pagina}`);
                if (pagina === paginaActual) boton.setAttribute('aria-current', 'page');
                boton.addEventListener('click', () => { paginaActual = pagina; renderTablaVecinos(); });
                container.appendChild(boton);
                anterior = pagina;
            });
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
            if (!window.XLSX) {
                Swal.fire({icon: 'error', title: 'Excel no disponible', text: 'Recarga la página e inténtalo nuevamente.'});
                return;
            }
            if (!datos.length) {
                Swal.fire({icon: 'info', title: 'Sin registros', text: 'No hay vecinos para exportar.'});
                return;
            }
            const hoja = datos.map(item => ({
                'ID': item.id, 'Nombre Completo': item.nombre, 'RUT': item.rut,
                'Dirección': item.direccion, 'Teléfono': item.telefono,
                'Territorio': item.territorio, 'Tipo Gestión': item.gestion, 'Estado': item.estado
            }));
            const ws = XLSX.utils.json_to_sheet(hoja);
            // Los datos del padrón se exportan como valores, nunca como fórmulas.
            Object.entries(ws).forEach(([address, cell]) => {
                if (address.startsWith('!') || !cell) return;
                delete cell.f;
                if (typeof cell.v === 'string') cell.t = 's';
            });
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Vecinos');
            XLSX.writeFile(wb, `${nombre}.xlsx`);
            mostrarToast('✓ Excel descargado correctamente');
        }

        function descargarPlantillaExcelVecinos() {
            const hoja = [{ 'Nombre Completo': 'Ej: Carlos Valenzuela', 'RUT': '12.345.678-5', 'Dirección': 'Av. Balmaceda 100', 'Teléfono': '+56 9 1234 5678', 'Correo electrónico': 'ejemplo@example.com', 'Territorio': 'Centro', 'Estado': 'Activo' }];
            const ws = XLSX.utils.json_to_sheet(hoja);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Plantilla');
            XLSX.writeFile(wb, 'Plantilla_Vecinos_LaSerena.xlsx');
            mostrarToast('✓ Plantilla Excel descargada');
        }

        function abrirModalImportarExcel() {
            tempImportados = [];
            document.getElementById('importWizardContent1').style.display = 'block';
            document.getElementById('importWizardContent2').style.display = 'none';
            document.getElementById('importFileInput').value = '';
            bsModalImportar.show();
        }

        let tempImportados = [];
        function procesarArchivoExcelSubido(input) {
            const file = input.files[0];
            if (!file) return;
            tempImportados = [];
            if (!window.XLSX || file.size > 5 * 1024 * 1024) {
                input.value = '';
                Swal.fire({icon: 'warning', title: 'Archivo no disponible', text: !window.XLSX ? 'La herramienta de importación aún no está disponible. Recarga la página.' : 'El archivo no puede superar 5 MB.'});
                return;
            }
            document.getElementById('lblNombreArchivoCargado').textContent = file.name;
            const reader = new FileReader();
            reader.onload = function (e) {
              try {
                const data = new Uint8Array(e.target.result);
                const wb = XLSX.read(data, { type: 'array' });
                const rows = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]]);
                if (!rows.length || rows.length > 1000) throw new Error('El archivo debe contener entre 1 y 1.000 registros.');
                tempImportados = rows.map((r, i) => ({
                    id: datasetVecinos.length + i + 1,
                    nombre: String(r['Nombre Completo'] ?? r['Nombre'] ?? '').trim(),
                    rut: String(r['RUT'] ?? r['Rut'] ?? '').trim(),
                    direccion: String(r['Dirección'] ?? '').trim(),
                    telefono: String(r['Teléfono'] ?? '').trim(),
                    email: String(r['Correo electrónico'] ?? r['Correo'] ?? '').trim(),
                    territorio: String(r['Territorio'] ?? '').trim(),
                    estado: String(r['Estado'] ?? 'Activo').trim()
                }));
                document.getElementById('lblTotalFilasCargadas').textContent = tempImportados.length;
                document.getElementById('importWizardContent1').style.display = 'none';
                document.getElementById('importWizardContent2').style.display = 'block';
              } catch (error) {
                input.value = '';
                Swal.fire({icon: 'error', title: 'No se pudo leer el archivo', text: error.message || 'Verifica el formato del archivo.'});
              }
            };
            reader.onerror = () => { input.value = ''; Swal.fire({icon: 'error', title: 'No se pudo leer el archivo', text: 'Selecciona el archivo e inténtalo nuevamente.'}); };
            reader.readAsArrayBuffer(file);
        }

        async function ejecutarImportacionFinal() {
            if (!tempImportados.length) {
                await Swal.fire({icon: 'warning', title: 'Sin registros', text: 'Selecciona un archivo con registros antes de importar.'});
                return;
            }
            if (ejecutarImportacionFinal.enCurso) return;
            ejecutarImportacionFinal.enCurso = true;
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
                    if (!response.ok || !data.success) throw new Error(data.errors ? Object.values(data.errors).join(' ') : (data.message || 'Registro rechazado.'));
                    guardados++;
                } catch (error) {
                    errores.push(`${vecino.nombre}: ${error.message}`);
                }
            }
            if (bsModalImportar) bsModalImportar.hide();
            await cargarVecinosDesdeDB(false);
            ejecutarImportacionFinal.enCurso = false;
            tempImportados = [];
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

        let fichaVecinoRequestId = 0;
        async function abrirFichaVecino(id) {
            const v = datasetVecinos.find(item => item.id === id);
            if (!v) return;
            const requestId = ++fichaVecinoRequestId;
            document.getElementById('fichaNombre').textContent = v.nombre;
            document.getElementById('fichaRut').textContent = v.rut;
            document.getElementById('fichaDireccion').textContent = v.direccion;
            document.getElementById('fichaTelefono').textContent = v.telefono;
            document.getElementById('fichaTerritorio').textContent = v.territorio;
            const status = document.getElementById('fichaEstado');
            status.textContent = v.estado;
            const timeline = document.getElementById('fichaHistorialTickets');
            if (timeline) timeline.textContent = 'Cargando historial...';
            bsModalFicha.show();
            try {
                const response = await fetch(`/api/vecinos/${id}/`, {headers: {'Accept': 'application/json'}});
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || 'No se pudo consultar el historial.');
                if (requestId !== fichaVecinoRequestId || !timeline) return;
                const history = Array.isArray(data.recent_attentions) ? data.recent_attentions : [];
                timeline.innerHTML = history.length ? history.map(item => `
                    <div class="timeline-ticket-item">
                        <span class="timeline-ticket-dot"></span>
                        <div class="d-flex justify-content-between gap-2 mb-1">
                            <strong class="text-dark small">${escapeHtml(item.code || 'Atención')}</strong>
                            <span class="text-muted small">${escapeHtml(item.date || '')}</span>
                        </div>
                        <div class="small text-secondary">${escapeHtml(item.status || 'Sin estado')}</div>
                        <p class="text-muted small m-0">${escapeHtml(item.subject || 'Sin descripción')}</p>
                    </div>`).join('') : '<p class="text-muted small mb-0">No hay atenciones registradas.</p>';
            } catch (error) {
                if (requestId === fichaVecinoRequestId && timeline) timeline.textContent = 'No se pudo cargar el historial. Inténtalo nuevamente.';
            }
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
            if ((!existente || rutVal !== String(existente.rut || '').trim()) && (!/^[0-9.kK-]+$/.test(rutVal) || (!rutSinCambios && typeof validarRutChileno === 'function' && !validarRutChileno(rutVal)))) {
                Swal.fire({
                    icon: 'error',
                    title: 'RUT inválido',
                    text: 'Revisa el número y el dígito verificador antes de continuar.'
                });
                return;
            }
            const emailVal = document.getElementById('vecinoEmail').value.trim().toLowerCase();
            if (emailVal && (!existente || emailVal !== String(existente.email || '').trim().toLowerCase()) && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
                Swal.fire({icon:'error', title:'Correo inválido', text:'Ingresa un correo electrónico válido.'});
                return;
            }

            const phone = document.getElementById('vecinoTelefono').value.trim();
            if ((!existente || nom !== String(existente.nombre || '').trim()) && (!/^[\p{L} .’'-]{2,}$/u.test(nom) || !/\p{L}/u.test(nom))) {
                Swal.fire({icon:'warning', title:'Nombre inválido', text:'Usa al menos dos caracteres con letras, espacios, puntos, apóstrofes o guiones.'});
                return;
            }
            if (phone && (!existente || phone !== String(existente.telefono || '').trim()) && (!/^\+?[0-9][0-9 () .-]*$/.test(phone) || phone.replace(/\D/g, '').length < 8 || phone.replace(/\D/g, '').length > 15)) {
                Swal.fire({icon:'warning', title:'Teléfono inválido', text:'Ingresa de 8 a 15 dígitos; puedes usar +, espacios, paréntesis y guiones.'});
                return;
            }
            if ((!existente || dir !== String(existente.direccion || '').trim()) && /[<>\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(dir)) {
                Swal.fire({icon:'warning', title:'Dirección inválida', text:'No se permiten etiquetas HTML ni caracteres de control.'});
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
                nombre: nom,
                rut: existente && rutVal === String(existente.rut || '').trim() ? rutVal : (typeof formatearRutChileno === 'function' ? formatearRutChileno(rutVal) : rutVal),
                email: emailVal,
                direccion: dir,
                telefono: phone,
                territorio: document.getElementById('vecinoTerritorio').value,
                estado: document.getElementById('vecinoEstado').value
            };

            if (guardarVecino.enCurso) return;
            guardarVecino.enCurso = true;
            const submit = e.currentTarget?.querySelector('[type="submit"]');
            if (submit) submit.disabled = true;
            try {
                const response = await fetch(id ? `/api/vecinos/${id}/` : '/api/vecinos/', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''},
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.errors ? Object.values(data.errors).join(' ') : (data.message || 'No fue posible guardar el vecino.'));
                if (bsModalVecino) bsModalVecino.hide();
                const actualizado = await cargarVecinosDesdeDB(false, true);
                if (actualizado === false) {
                    await Swal.fire({icon: 'warning', title: 'Vecino guardado', text: 'Los datos se guardaron, pero no se pudo actualizar el listado. Recarga la sección antes de continuar.', confirmButtonColor: '#A30F32'});
                    return;
                }
                mostrarToast('✓ ' + data.message);
                Swal.fire({icon: 'success', title: 'Vecino guardado', text: data.message || 'Datos del vecino guardados exitosamente.', confirmButtonColor: '#1B365D'});
            } catch (error) {
                Swal.fire({icon: 'error', title: 'No se guardó el vecino', text: error.message, confirmButtonColor: '#A30F32'});
            } finally {
                guardarVecino.enCurso = false;
                if (submit) submit.disabled = false;
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

