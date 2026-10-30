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
        let controlesDelegacionesInicializados = false;

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
            if (!controlesDelegacionesInicializados) {
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
                controlesDelegacionesInicializados = true;
            }
            seleccionarVistaDelegaciones(vistaDelegacionesActiva);
            const grid = document.getElementById('delegacionesCardsGrid');
            const table = document.getElementById('tablaDelegacionesBody');
            if (grid) {
                grid.setAttribute('aria-busy', 'true');
                grid.innerHTML = '<div class="admin-loading" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Cargando delegaciones…</div>';
            }
            if (table) table.innerHTML = '<tr><td colspan="8"><div class="admin-loading" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Cargando delegaciones…</div></td></tr>';
            try {
                await cargarCatalogosOrganizacion();
                renderizarDelegacionesCards(filtroZonaActivo);
            } catch (error) {
                console.warn('No fue posible sincronizar las fichas territoriales:', error);
                if (grid) grid.innerHTML = '<p class="text-danger">No se pudieron cargar las delegaciones. Vuelve a abrir esta sección para intentar nuevamente.</p>';
                if (table) table.innerHTML = '<tr><td colspan="8" class="text-danger text-center py-3">No se pudieron cargar las delegaciones.</td></tr>';
                if (document.getElementById('view-delegaciones')?.classList.contains('active') && window.Swal) {
                    Swal.fire({icon: 'error', titleText: 'Delegaciones no disponibles', text: error.message});
                }
            } finally { if (grid) grid.removeAttribute('aria-busy'); }
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
                                ${escapeHtml(d.sector)}
                            </div>
                            <h4 class="fw-bold mb-1" style="color: var(--muni-navy); font-size: 1.25rem;">
                                ${escapeHtml(d.nombre)}
                            </h4>
                            <div class="text-secondary small text-truncate mb-3" style="font-size: 0.82rem;">
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i>${escapeHtml(d.direccion)}
                            </div>

                            <!-- Cápsula de Gestor y Horario (Vidrio Esmerilado) -->
                            <div class="p-2 px-3 rounded-3 mb-2" style="background: rgba(27, 54, 93, 0.04); border: 1px solid rgba(226, 232, 240, 0.9);">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <span class="text-muted small" style="font-size: 0.74rem;">
                                        <i class="bi bi-person-badge text-primary me-1"></i>Encargado:
                                    </span>
                                    <span class="fw-bold text-dark small" style="font-size: 0.78rem;">${escapeHtml(d.delegado || 'No registrado')}</span>
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
                                <i class="bi bi-clock text-muted me-1"></i>${escapeHtml(d.horario || 'Horario no registrado')}
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

        function seleccionarDelegacion(id) {
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
                                    ${escapeHtml(f.avatar)}
                                </div>
                                <div style="min-width:0;">
                                    <div class="fw-bold text-truncate" style="color: var(--muni-navy); font-size: 0.92rem;" title="${escapeHtml(f.nombre)}">${escapeHtml(f.nombre)}</div>
                                </div>
                            </div>
                            <div class="small text-secondary mb-2"><strong>Cargo:</strong> ${escapeHtml(f.cargo)}</div>
                            <span class="role-badge-pill role-badge-${f.rol.toLowerCase().includes('gestor') ? 'gestor' : f.rol.toLowerCase().includes('verificador') ? 'verificador' : 'admin'} mb-2">
                                ${escapeHtml(f.rol)}
                            </span>
                        </div>
                    </div>
                </div>
            `).join('') : '<div class="col-12"><p class="text-secondary small mb-0">No hay funcionarios registrados para esta delegación.</p></div>';

            // Construir Barrios HTML
            const barriosHtml = data.barrios.length ? data.barrios.map(b => `
                <span class="badge bg-white text-dark border px-3 py-2 rounded-pill me-1 mb-2 shadow-xs" style="font-size:0.82rem; font-weight:600;">
                    <i class="bi bi-geo-alt-fill text-danger me-1"></i> ${escapeHtml(b)}
                </span>
            `).join('') : '<span class="text-secondary small">Sin sectores descriptivos registrados.</span>';

            // Construir Métricas de Atención
            const metricasHtml = data.metricasAtencion.length ? data.metricasAtencion.map(m => `
                <div class="mb-3">
                    <div class="d-flex justify-content-between small fw-bold mb-1">
                        <span style="color: var(--muni-navy);">${escapeHtml(m.tipo)}</span>
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
                        <i class="bi bi-geo-alt-fill text-danger me-1"></i> Ficha Territorial Oficial: ${escapeHtml(data.nombre)}
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
                                        Sede municipal: ${escapeHtml(data.dbStatus || 'Sin estado')}
                                    </span>
                                    <span class="badge rounded-pill px-3 py-1 fw-bold text-white shadow-xs" style="background: ${data.colorSemaforo}; font-size: 0.72rem;">
                                        <i class="bi bi-circle-fill me-1" style="font-size: 0.55rem;"></i>${escapeHtml(data.statusSemaforo)}
                                    </span>
                                    <span class="badge bg-white text-dark border px-2 py-1 rounded-pill small fw-bold">
                                        <i class="bi bi-star-fill text-warning me-1"></i>${escapeHtml(data.satisfaccion)} Satisfacción
                                    </span>
                                </div>
                                <h2 class="m-0 fw-bold" style="color: var(--muni-navy); font-size: 1.85rem; letter-spacing: -0.3px;">
                                    ${escapeHtml(data.nombre)}
                                </h2>
                                <p class="text-secondary m-0 fw-semibold" style="font-size: 0.95rem;">
                                    ${escapeHtml(data.sector)} • Cobertura Comunal La Serena
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
                                <i class="bi bi-geo-alt-fill text-danger me-1"></i> <strong>Sede:</strong> ${escapeHtml(data.direccion)}
                            </div>
                            <div class="col-md-3">
                                <i class="bi bi-telephone-fill text-primary me-1"></i> <strong>Fono:</strong> ${escapeHtml(data.telefono)}
                            </div>
                            <div class="col-md-2">
                                <i class="bi bi-clock-fill text-success me-1"></i> <strong>Horario:</strong> ${escapeHtml(data.horario)}
                            </div>
                            <div class="col-md-3 text-md-end">
                                <i class="bi bi-person-badge-fill text-warning me-1"></i> <strong>Delegado(a):</strong> ${escapeHtml(data.delegado)}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="p-4 pt-1">
                    <!-- Resumen Territorial Municipal -->
                    <div class="alert alert-light border-start border-4 mb-4 py-3 px-4 text-secondary shadow-xs" style="border-left-color: ${data.colorSemaforo} !important; background: rgba(255, 255, 255, 0.9); border-radius: 12px; font-size: 0.92rem; line-height: 1.5;">
                        <i class="bi bi-info-circle-fill text-primary me-2 fs-6"></i> ${escapeHtml(data.resumen)}
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
                                <small class="text-info fw-bold"><i class="bi bi-shield-check me-1"></i>Satisfacción: ${escapeHtml(data.satisfaccion)}</small>
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
                                Los sectores registrados se muestran cuando hay información disponible.
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
            if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && panel.animate) {
                panel.animate([{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }],
                    { duration: 180, easing: 'ease-out' });
            }

            // Desplazamiento suave al panel de detalle
            setTimeout(() => {
                panel.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
            }, 100);

            mostrarToast(`✓ Ficha territorial de ${escapeHtml(data.nombre)} cargada correctamente.`);
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

