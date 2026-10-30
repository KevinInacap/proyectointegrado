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

        const cambiosEstadoUsuariosEnCurso = new Set();
        async function toggleEstadoUsuario(id) {
            id = Number(id);
            const user = datasetUsuarios.find(item => Number(item.id) === id);
            if (!user || cambiosEstadoUsuariosEnCurso.has(id)) return;
            cambiosEstadoUsuariosEnCurso.add(id);
            try {
                const desiredStatus = user.status === 'Activo' ? 'Inactivo' : 'Activo';
                const action = desiredStatus === 'Inactivo' ? 'desactivar' : 'activar';
                const result = await Swal.fire({
                    icon: 'warning', titleText: `¿Deseas ${action} esta cuenta?`,
                    text: `Se cambiará el acceso de ${user.full_name}.`, showCancelButton: true,
                    confirmButtonText: 'Sí, cambiar estado', cancelButtonText: 'Cancelar', confirmButtonColor: '#8B1D2C'
                });
                if (!result.isConfirmed) return;
                const res = await fetch(`/api/users/${id}/toggle-status/`, {
                    method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''},
                    body: JSON.stringify({status: desiredStatus})
                });
                const data = await res.json();
                if (!res.ok || !data.success) throw new Error(data.message || 'No se pudo cambiar el estado.');
                await cargarUsuariosDesdeDB(false);
                await Swal.fire({icon: 'success', titleText: 'Estado actualizado', text: data.message});
            } catch (err) {
                await Swal.fire({icon: 'error', titleText: 'No se pudo cambiar el estado', text: err.message || 'Comprueba la conexión y vuelve a intentarlo.'});
            } finally {
                cambiosEstadoUsuariosEnCurso.delete(id);
            }
        }

        async function eliminarUsuario(id) {
            const u = datasetUsuarios.find(item => item.id === id);
            const nombre = u ? u.full_name : 'este funcionario';

            const result = await Swal.fire({
                title: '¿Eliminar funcionario definitivamente?',
                text: `Se eliminarán permanentemente la cuenta y el perfil de "${nombre}". Esta acción no se puede deshacer.`,
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

