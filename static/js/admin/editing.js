        function sanitizarTexto(input) {
            return typeof input === 'string' ? input.trim() : input;
        }
        window.sanitizarTexto = sanitizarTexto;

        // 2. Validador de RUT Chileno (Algoritmo Oficial Módulo 11)
        function validarRutChileno(rutCompleto) {
            if (!rutCompleto || typeof rutCompleto !== 'string') return false;
            if (!/^(?:[0-9]{1,8}|[0-9]{1,2}(?:\.[0-9]{3}){1,2})-?[0-9kK]$/.test(rutCompleto.trim())) return false;
            let valor = rutCompleto.replace(/\./g, '').replace(/-/g, '').trim().toUpperCase();
            
            let cuerpo = valor.slice(0, -1);
            let dv = valor.slice(-1);
            
            if (!/^[0-9]+$/.test(cuerpo) || Number(cuerpo) === 0) return false;
            
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
                        <input type="text" class="form-control" id="drawerInputNombre" maxlength="150" required value="${escapeHtml(v.nombre)}" onkeypress="bloquearNumerosInput(event)">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">RUT Chileno</label>
                        <input type="text" class="form-control" id="drawerInputRut" maxlength="15" value="${escapeHtml(v.rut)}" readonly>
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Dirección</label>
                        <input type="text" class="form-control" id="drawerInputDireccion" maxlength="255" required value="${escapeHtml(v.direccion)}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Teléfono Móvil</label>
                        <input type="text" class="form-control" id="drawerInputTelefono" maxlength="20" value="${escapeHtml(v.telefono)}">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Territorio / Delegación</label>
                        <input class="form-control" id="drawerSelectTerritorio" maxlength="100" value="${escapeHtml(v.territorio)}">
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
                        <input type="text" class="form-control" id="drawerInputNombre" maxlength="150" required value="${escapeHtml(u.full_name)}" onkeypress="bloquearNumerosInput(event)">
                    </div>
                    <div class="mb-3">
                        <label class="form-label small fw-bold">Correo Institucional</label>
                        <input type="email" class="form-control" id="drawerInputEmail" maxlength="100" required value="${escapeHtml(u.email)}">
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

        async function ejecutarGuardadoDrawer() {
            if (!drawerActivoTipo || !drawerActivoId) return;
            const isNeighbor = drawerActivoTipo === 'vecino';
            const record = (isNeighbor ? datasetVecinos : datasetUsuarios).find(item => item.id === drawerActivoId);
            if (!record) return;
            const name = document.getElementById('drawerInputNombre')?.value.trim() || '';
            const status = document.getElementById('drawerSelectEstado')?.value;
            const address = document.getElementById('drawerInputDireccion')?.value.trim() || '';
            const email = document.getElementById('drawerInputEmail')?.value.trim() || '';
            if (!name || (isNeighbor && !address) || (!isNeighbor && !validarEmail(email))) {
                await Swal.fire({icon: 'warning', titleText: 'Revisa los datos', text: 'Ingresa un nombre y una dirección o correo válido, según corresponda.'});
                return;
            }
            const payload = isNeighbor ? {
                nombre: name, rut: record.rut, direccion: address,
                telefono: document.getElementById('drawerInputTelefono')?.value.trim() || '',
                territorio: document.getElementById('drawerSelectTerritorio')?.value.trim() || '', estado: status
            } : {full_name: name, email, status};
            const button = document.getElementById('btnDrawerGuardar');
            if (button?.disabled) return;
            if (button) button.disabled = true;
            try {
                const response = await fetch(isNeighbor ? `/api/vecinos/${record.id}/` : `/api/users/${record.id}/update/`, {
                    method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') || ''},
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || 'No se pudo guardar el registro.');
                cerrarAdminDrawer();
                if (isNeighbor) await cargarVecinosDesdeDB(false);
                else await cargarUsuariosDesdeDB(false);
                await Swal.fire({icon: 'success', titleText: 'Cambios guardados', text: data.message || 'El registro fue actualizado.'});
            } catch (error) {
                await Swal.fire({icon: 'error', titleText: 'No se guardaron los cambios', text: error.message || 'Comprueba la conexión y vuelve a intentarlo.'});
            } finally {
                if (button) button.disabled = false;
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



