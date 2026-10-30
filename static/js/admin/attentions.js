        async function cargarAtencionesDB(silencioError = false) {
            try {
                const resp = await fetch('/api/atenciones/');
                if (!resp.ok) throw new Error('Error al consultar atenciones');
                const data = await resp.json();
                if (!data.success || !Array.isArray(data.atenciones)) throw new Error('La respuesta de atenciones no es válida.');
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
                return true;
            } catch (err) {
                console.error('Error cargando atenciones desde MySQL:', err);
                const tbody = document.getElementById('tablaAtencionesBody');
                if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">No se pudieron cargar las atenciones. Inténtalo nuevamente.</td></tr>';
                if (!silencioError && document.getElementById('view-atenciones')?.classList.contains('active') && window.Swal) {
                    Swal.fire({icon: 'error', title: 'Atenciones no disponibles', text: 'No se pudo consultar el listado. Revisa la conexión e inténtalo nuevamente.'});
                }
                return false;
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

            // También se usa dentro de atributos: deben codificarse las comillas.
            const escapeCell = escapeHtml;

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
                                ${escapeCell(stageText)}
                            </span>
                        </td>
                        <td class="py-2.5 px-1 text-center text-muted" style="font-size: 0.74rem;">
                            ${escapeCell(dateText)}
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

        async function cargarTodasLasPaginasAtencion(url) {
            const records = [];
            let page = 1;
            while (true) {
                const response = await fetch(`${url}?page_size=50&page=${page}`, {
                    credentials: 'same-origin', headers: { Accept: 'application/json' }
                });
                if (!response.ok) throw new Error('No se pudo cargar el catálogo completo.');
                const data = await response.json();
                if (!Array.isArray(data.results) || !Number.isInteger(data.count) || data.count < 0) {
                    throw new Error('El catálogo recibido no es válido.');
                }
                records.push(...data.results);
                if (records.length >= data.count) return records;
                if (!data.results.length) throw new Error('No se pudo cargar el catálogo completo.');
                page += 1;
            }
        }

        async function cargarCatalogosFormularioAtencion(forceRefresh = false) {
            if (forceRefresh) catalogsForAttentionForm = null;
            if (catalogsForAttentionForm) return catalogsForAttentionForm;
            const pending = (async () => {
                const [delegationResponse, types, subattentions] = await Promise.all([
                    fetch('/api/delegations/', { credentials: 'same-origin', headers: { Accept: 'application/json' } }),
                    cargarTodasLasPaginasAtencion('/api/catalogs/attention-types/'),
                    cargarTodasLasPaginasAtencion('/api/catalogs/subattentions/')
                ]);
                if (!delegationResponse.ok) {
                    throw new Error('No se pudieron cargar las delegaciones y catálogos autorizados. Recarga la página e inténtalo de nuevo.');
                }
                const delegationData = await delegationResponse.json();
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
                fill(typeSelect, 'Selecciona un tipo', types, record => record.name, true);
                fill(subSelect, 'Primero selecciona un tipo', subattentions, record => record.name, true);
                if (typeSelect && subSelect) {
                    subSelect.disabled = true;
                    typeSelect.onchange = () => {
                        const typeId = typeSelect.value;
                        let hasOptions = false;
                        [...subSelect.options].forEach(option => {
                            if (!option.value) return;
                            const record = subattentions.find(item => String(item.id) === option.value);
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
            catalogsForAttentionForm = pending;
            pending.catch(() => {
                if (catalogsForAttentionForm === pending) catalogsForAttentionForm = null;
            });
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
            const name = document.getElementById('txtAtencionNombre');
            const phone = document.getElementById('txtAtencionTelefono');
            if (name) name.readOnly = Boolean(vecino);
            if (phone) phone.readOnly = Boolean(vecino);
            if (!vecino) return;
            if (name) name.value = vecino.nombre || '';
            if (phone) phone.value = vecino.telefono || '';
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
            completarDatosVecinoAtencion();
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

        let guardandoAtencion = false;
        async function guardarAtencionDB() {
            if (guardandoAtencion) return;
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
            guardandoAtencion = true;
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
                const actualizado = await cargarAtencionesDB(true);
                if (actualizado === false) {
                    await Swal.fire({icon: 'warning', title: 'Atención guardada', text: 'Los datos se guardaron, pero no se pudo actualizar el listado. Recarga la sección antes de continuar.'});
                    return;
                }
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
                guardandoAtencion = false;
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
        // Normalizar antes de guardar; la salida HTML se codifica en cada renderizador.
