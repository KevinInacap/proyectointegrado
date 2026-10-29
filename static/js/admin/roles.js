        let datasetRoles = [];

        let datasetCatalogPermisos = [];

        let filasFiltradasRoles = [];
        let paginaActualRoles = 1;
        let filasPorPaginaRoles = 10;
        let rolEliminarId = null;
        let verPermisosExtendidos = false;
        let solicitudRolesActual = 0;

        async function initRolesView(mostrarAviso = false) {
            const solicitud = ++solicitudRolesActual;
            const grid = document.getElementById('roleCardsLive');
            const newButton = document.getElementById('btnNuevoRol');
            const table = document.getElementById('tablaRolesBody');
            if (newButton) newButton.disabled = true;
            if (grid) {
                grid.setAttribute('aria-busy', 'true');
                grid.innerHTML = '<div class="admin-loading" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Cargando roles y permisos…</div>';
            }
            if (table) table.innerHTML = '<tr><td colspan="6"><div class="admin-loading" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Cargando roles…</div></td></tr>';
            try {
                const res = await fetch('/api/roles/');
                if (!res.ok) throw new Error(`No se pudieron consultar los roles (HTTP ${res.status}).`);
                const data = await res.json();
                if (solicitud !== solicitudRolesActual) return false;
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
                if (newButton) newButton.disabled = false;
                if (mostrarAviso) {
                    mostrarToast('✓ Base de datos sincronizada: ' + datasetRoles.length + ' roles activos.');
                }
                return true;
            } catch (err) {
                if (solicitud !== solicitudRolesActual) return false;
                console.warn("Error al cargar roles desde API (usando catálogo local):", err);
                const grid = document.getElementById('roleCardsLive');
                if (grid) {
                    grid.innerHTML = '<p class="text-danger mb-0">No se pudieron cargar los permisos guardados. Recarga esta sección para intentarlo de nuevo.</p>';
                    grid.dataset.ready = 'true';
                }
                if (table) table.innerHTML = '<tr><td colspan="6" class="text-danger text-center py-3">No se pudieron cargar los roles. Vuelve a abrir esta sección para intentarlo nuevamente.</td></tr>';
                return false;
            } finally {
                if (grid && solicitud === solicitudRolesActual) grid.removeAttribute('aria-busy');
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
                                    <span class="text-muted role-card-kind">${escapeHtml(role.position_name || 'Cargo pendiente de asignación')}</span></div>
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
                    <td class="text-secondary" style="font-size: 0.88rem;">${escapeHtml(r.description || 'Sin descripción')}<small class="d-block mt-1">Cargo: ${escapeHtml(r.position_name || 'Pendiente de asignación')} · Alcance: ${r.is_admin_role ? 'Comunal' : 'Delegación asignada'}</small></td>
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
                                <input type="checkbox" name="rolPermisoCheckbox" data-module="${moduleIndex}" value="${escapeHtml(p.code)}" ${isChecked ? 'checked' : ''} onchange="actualizarContadorPermisosModal()">
                                <div>
                                    <div class="fw-bold" style="font-size: 0.82rem; color: var(--muni-navy);">${escapeHtml(p.name)}</div>
                                    <div class="text-muted" style="font-size: 0.72rem; line-height: 1.2;">${escapeHtml(p.desc || '')}</div>
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
                                <i class="bi ${escapeHtml(mod.icon || 'bi-folder')} text-primary fs-5"></i>
                                <div style="min-width:0">
                                    <h6 class="fw-bold m-0" style="font-size: 0.90rem; color: var(--muni-navy);">${escapeHtml(mod.module_name)}</h6>
                                    <span class="text-muted text-truncate d-block" style="font-size: 0.70rem;">${escapeHtml(mod.description || '')}</span>
                                </div>
                            </div>
                            <span class="badge bg-light text-primary border flex-shrink-0" id="count-module-${moduleIndex}">${modCheckedCount}/${modTotalCount}</span>
                            <button type="button" class="btn btn-sm btn-outline-muni-red rounded-pill px-2 flex-shrink-0" onclick="event.preventDefault(); event.stopPropagation(); toggleModuloCompleto(${moduleIndex}, this)">
                                ${allModChecked ? 'Desmarcar' : 'Todos'}
                            </button>
                            <i class="bi bi-chevron-down permission-chevron flex-shrink-0"></i>
                        </summary>
                        <div class="row g-2 pt-3 mt-2 border-top" id="mod-container-${moduleIndex}">
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
            datasetCatalogPermisos.forEach((mod, moduleIndex) => {
                const selected = document.querySelectorAll(`input[name="rolPermisoCheckbox"][data-module="${moduleIndex}"]:checked`).length;
                const moduleCount = document.getElementById(`count-module-${moduleIndex}`);
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

        let solicitudCargoRol = 0;
        async function abrirModalRol(modo, rolId = null) {
            const elId = document.getElementById('rolFormId');
            const elNom = document.getElementById('rolFormNombre');
            const elDesc = document.getElementById('rolFormDescripcion');
            const elTitle = document.getElementById('modalRolTitle');
            const elCargo = document.getElementById('rolFormCargo');
            const elSave = document.getElementById('btnGuardarRol');
            const rol = modo === 'nuevo' ? null : datasetRoles.find(r => r.id === rolId);
            if (modo !== 'nuevo' && !rol) return;
            const editar = modo === 'editar';

            if (modo === 'nuevo') {
                if (elId) elId.value = '';
                if (elNom) { elNom.value = ''; elNom.disabled = false; }
                if (elDesc) elDesc.value = '';
                if (elTitle) elTitle.innerHTML = `<i class="bi bi-person-plus-fill text-warning me-2"></i> Nuevo Rol`;
                // Un rol nuevo no recibe permisos hasta que se seleccionen explícitamente.
                renderPermisosMatrix([]);
            } else {
                if (elId) elId.value = editar ? rol.id : '';
                if (elNom) {
                    elNom.value = editar ? rol.name : `${rol.name.slice(0, 42)} (Copia)`;
                    elNom.disabled = editar && !!rol.is_system;
                }
                if (elDesc) elDesc.value = rol.description || '';
                if (elTitle) elTitle.textContent = `${editar ? 'Editar' : 'Duplicar'} rol: ${rol.name}`;
                renderPermisosMatrix(rol.permissions || []);
            }
            const solicitud = ++solicitudCargoRol;
            elCargo.replaceChildren(new Option('Cargando cargos…', ''));
            elCargo.disabled = true;
            elCargo.setAttribute('aria-busy', 'true');
            if (elSave) elSave.disabled = true;
            if (bsModalRol) bsModalRol.show();
            try {
                const response = await fetch('/organization/positions/', {credentials: 'same-origin'});
                const data = await response.json();
                if (!response.ok || !data.success || !Array.isArray(data.positions)) throw new Error(data.message || 'No fue posible cargar los cargos.');
                if (solicitud !== solicitudCargoRol) return;
                elCargo.replaceChildren(new Option('Selecciona un cargo', ''));
                data.positions.filter(item => item.status === 'Activo' || (editar && String(item.id) === String(rol?.position_id)))
                    .forEach(item => elCargo.add(new Option(item.name + (item.status !== 'Activo' ? ' (inactivo)' : ''), item.id)));
                if (rol?.position_id) elCargo.value = String(rol.position_id);
                elCargo.disabled = editar && !!rol?.is_base_role && !!rol?.position_id;
                if (!elCargo.options.length || elCargo.options.length === 1) {
                    Swal.fire({icon: 'info', titleText: 'No hay cargos disponibles', text: 'Crea primero un cargo activo y luego configura sus permisos.'});
                }
                if (elSave) elSave.disabled = false;
            } catch (error) {
                if (solicitud !== solicitudCargoRol) return;
                elCargo.replaceChildren(new Option('No se pudieron cargar los cargos', ''));
                Swal.fire({icon: 'error', titleText: 'Cargos no disponibles', text: error.message});
            } finally {
                if (solicitud === solicitudCargoRol) elCargo.removeAttribute('aria-busy');
            }
        }

        async function ejecutarGuardarRol() {
            const elId = document.getElementById('rolFormId');
            const id = elId ? elId.value : '';
            const elNom = document.getElementById('rolFormNombre');
            const name = (elNom && elNom.value) ? elNom.value.trim() : '';
            const elDesc = document.getElementById('rolFormDescripcion');
            const description = (elDesc && elDesc.value) ? elDesc.value.trim() : '';
            const positionId = document.getElementById('rolFormCargo')?.value;

            if (!name || !description || !positionId) {
                Swal.fire({icon: 'warning', title: 'Campos requeridos', text: 'Selecciona un cargo e indica el nombre y la descripción del rol.'});
                return;
            }

            const checkedPerms = [];
            document.querySelectorAll('input[name="rolPermisoCheckbox"]:checked').forEach(cb => {
                checkedPerms.push(cb.value);
            });

            const payload = {
                name: name,
                description: description,
                position_id: Number(positionId),
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
                if (!res.ok || !data.success) throw new Error(data.message || 'Error al procesar la solicitud');

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

                if (bsModalRol) bsModalRol.hide();
                filtrarRoles();
                // La escritura ya se confirmó; distinguir errores al refrescar.
                try {
                    const rolesActualizados = await initRolesView(false);
                    await cargarUsuariosDesdeDB(false);
                    if (rolesActualizados === false) throw new Error('No se pudo actualizar la lista de roles.');
                    mostrarToast(data.message || (id ? 'Rol actualizado exitosamente.' : 'Rol creado exitosamente.'));
                } catch (refreshError) {
                    await Swal.fire({icon: 'warning', titleText: 'Rol guardado', text: 'El rol se guardó, pero no se pudieron actualizar todas las listas. Recarga la página antes de continuar.'});
                }
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
            await abrirModalRol('duplicar', rolId);
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
                                    <span class="${isGranted ? 'fw-bold text-dark' : 'text-muted text-decoration-line-through'}">${escapeHtml(p.name)}</span>
                                </div>
                            </div>
                        `;
                    });

                    card.innerHTML = `
                        <div class="d-flex align-items-center justify-content-between mb-2 pb-2 border-bottom">
                            <div class="d-flex align-items-center gap-2">
                                <i class="bi ${escapeHtml(mod.icon || 'bi-folder')} text-primary"></i>
                                <strong style="color: var(--muni-navy); font-size: 0.88rem;">${escapeHtml(mod.module_name)}</strong>
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
                            <i class="bi ${escapeHtml(mod.icon || 'bi-folder')} text-primary me-2"></i> ${escapeHtml(mod.module_name)}
                        </td>
                    </tr>
                `;

                (mod.permissions || []).forEach(p => {
                    bodyHtml += `
                        <tr>
                            <td class="sticky-col">
                                <div class="fw-bold text-dark" style="font-size: 0.80rem;">${escapeHtml(p.name)}</div>
                                <code style="font-size: 0.70rem; color: var(--muni-text-sec);">${escapeHtml(p.code)}</code>
                            </td>
                    `;

                    datasetRoles.forEach(r => {
                        const isChecked = (r.permissions || []).includes(p.code);
                        bodyHtml += `
                            <td>
                                <input type="checkbox" class="myadmin-toggle-switch" data-role-id="${r.id}" data-perm-code="${escapeHtml(p.code)}" aria-label="${escapeHtml(p.name)} para ${escapeHtml(r.name)}" ${isChecked ? 'checked' : ''} ${r.is_admin_role || ['Administrador', 'SuperAdministrador'].includes(r.name) ? 'disabled title="Rol de sistema protegido; usa sus controles generales habilitados"' : ''}>
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
                if (role && !role.is_admin_role && !['Administrador', 'SuperAdministrador'].includes(role.name)) {
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

                const textoExcel = value => {
                    const text = String(value ?? '');
                    return /^[\s\u0000-\u001f]*[=+@-]/.test(text) ? `'${text}` : text;
                };
                const rows = filasFiltradasRoles.map((r, i) => ({
                    '#': i + 1,
                    'Nombre del Rol': textoExcel(r.name),
                    'Cargo asociado': textoExcel(r.position_name || 'Pendiente de asignación'),
                    'Descripción Institucional': textoExcel(r.description),
                    'Tipo': r.is_system ? 'Sistema (Protegido)' : 'Personalizado',
                    'Funcionarios Asignados': r.users_count || 0,
                    'Total Privilegios': r.permissions_count || 0,
                    'Privilegios y Funciones Autorizadas': textoExcel((r.permissions || []).join(', '))
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
                    titleText: msg.replace(/✓ |⚠ |⏸ /g, '')
                });
            } else {
                console.log('[Toast]:', msg);
            }
        }
        function cerrarToast() { }

        /* ==========================================================================
           MÓDULO: ATENCIONES CIUDADANAS Y CASOS SOCIALES (PERSISTENCIA MYSQL REAL)
           ========================================================================== */
