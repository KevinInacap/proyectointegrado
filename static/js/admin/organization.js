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
            const container = document.getElementById('listaCargosMantenedor');
            if (container) {
                container.setAttribute('aria-busy', 'true');
                container.innerHTML = '<div class="col-12"><div class="admin-loading" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Cargando cargos…</div></div>';
            }
            try { await cargarCatalogosOrganizacion(); }
            catch (error) {
                if (container) container.innerHTML = '<div class="col-12 text-danger py-3">No se pudieron cargar los cargos. Vuelve a abrir esta sección para intentar nuevamente.</div>';
                Swal.fire({icon: 'error', titleText: 'No fue posible cargar los cargos', text: error.message});
            } finally { if (container) container.removeAttribute('aria-busy'); }
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
                Swal.fire({icon: 'error', titleText: 'No fue posible abrir el catálogo', text: error.message});
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
            // El servidor ya confirmó la escritura. Un fallo al refrescar no debe
            // presentarse como un fallo de guardado ni inducir a crear un duplicado.
            try {
                await cargarCatalogosOrganizacion();
                await cargarUsuariosDesdeDB(false);
                const rolesActualizados = await initRolesView(false);
                if (rolesActualizados === false) throw new Error('No se pudo actualizar la lista de roles.');
                mostrarToast(`✓ ${data.message}`);
            } catch (error) {
                await Swal.fire({icon: 'warning', titleText: 'Cambio guardado', text: `${data.message} Sin embargo, no se pudieron actualizar todas las listas. Recarga la página antes de continuar.`});
            }
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
            } catch (error) { Swal.fire({icon: 'error', titleText: 'No se pudo guardar', text: error.message}); }
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
            } catch (error) { Swal.fire({icon: 'error', titleText: 'No se pudo guardar', text: error.message}); }
        }

        async function confirmarCambioEstadoCatalogo(id, items, tipo, endpoint) {
            const item = items.find(row => Number(row.id) === Number(id));
            if (!item) return;
            const accion = item.status === 'Activo' ? 'desactivar' : 'activar';
            const result = await Swal.fire({
                icon: 'question', titleText: `¿Deseas ${accion} este ${tipo}?`,
                text: `Se cambiará el estado de ${item.name}.`, showCancelButton: true,
                confirmButtonText: 'Sí, cambiar estado', cancelButtonText: 'Cancelar',
                confirmButtonColor: '#8B1D2C'
            });
            if (!result.isConfirmed) return;
            try { await enviarCatalogo(`${endpoint}/${id}/toggle-status/`, {}); }
            catch (error) { Swal.fire({icon: 'error', titleText: 'No se pudo cambiar el estado', text: error.message}); }
        }

        function alternarDelegacionCatalogo(id) {
            return confirmarCambioEstadoCatalogo(id, catalogoDelegacionesDB, 'registro', '/organization/delegations');
        }

        function alternarCargoCatalogo(id) {
            return confirmarCambioEstadoCatalogo(id, catalogoCargosDB, 'cargo', '/organization/positions');
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
                Swal.fire({icon: 'error', titleText: 'No se pudo eliminar el cargo', text: error.message});
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
            catch (error) { Swal.fire({icon: 'error', titleText: 'No se pudo eliminar la delegación', text: error.message}); }
        }

        /* ==========================================================================
           MÓDULO: DELEGACIONES MUNICIPALES (IDENTIDAD TERRITORIAL POR COLOR Y SIGLAS)
           ========================================================================== */

