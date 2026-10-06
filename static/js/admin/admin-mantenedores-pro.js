/**
 * ==========================================================================
 * SISTEMA PRO DE MANTENEDORES & LIQUID GLASS — LA SERENA
 * Control del Drawer Lateral, Barra Flotante de Acciones y Filtros Avanzados
 * ==========================================================================
 */

let selectedTableRows = new Set();
let activeMaintainerType = 'usuarios';

// 1. CONTROL DEL DRAWER LATERAL (SLIDE-OVER PANEL)
function abrirAdminDrawer(tipo, id = null) {
    activeMaintainerType = tipo;
    const drawer = document.getElementById('adminSlideDrawer');
    const overlay = document.getElementById('adminSlideDrawerOverlay');
    const title = document.getElementById('drawerHeaderTitle');
    const subtitle = document.getElementById('drawerHeaderSubtitle');
    const icon = document.getElementById('drawerHeaderIcon');
    const body = document.getElementById('drawerBodyContent');

    if (!drawer || !overlay) return;

    // Configurar encabezado según el tipo
    if (tipo === 'usuario') {
        icon.className = 'bi bi-person-badge';
        if (id) {
            title.textContent = 'Editar Funcionario';
            subtitle.textContent = 'Actualización de cargo, delegación y rol';
            cargarFormularioUsuarioDrawer(id, body);
        } else {
            title.textContent = 'Nuevo Funcionario';
            subtitle.textContent = 'Alta de cuenta y asignación de perfil';
            cargarFormularioUsuarioDrawer(null, body);
        }
    } else if (tipo === 'vecino') {
        icon.className = 'bi bi-house-door';
        if (id) {
            title.textContent = 'Ficha del Vecino';
            subtitle.textContent = 'Historial de solicitudes y territorio';
            cargarFormularioVecinoDrawer(id, body);
        } else {
            title.textContent = 'Registrar Vecino';
            subtitle.textContent = 'Incorporación al padrón vecinal comunal';
            cargarFormularioVecinoDrawer(null, body);
        }
    } else if (tipo === 'rol') {
        icon.className = 'bi bi-shield-check';
        title.textContent = id ? 'Editar Rol Institucional' : 'Crear Nuevo Rol';
        subtitle.textContent = 'Gestión de privilegios y accesos en el sistema';
        if (typeof abrirModalRol === 'function') {
            abrirModalRol(id ? 'editar' : 'nuevo', id);
            return;
        }
    }

    drawer.classList.add('active');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function cerrarAdminDrawer() {
    const drawer = document.getElementById('adminSlideDrawer');
    const overlay = document.getElementById('adminSlideDrawerOverlay');
    if (drawer) drawer.classList.remove('active');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
}

function cargarFormularioUsuarioDrawer(id, container) {
    let u = null;
    if (id && window.datasetUsuarios) {
        u = window.datasetUsuarios.find(item => item.id == id);
    }

    const nombre = u ? u.full_name : '';
    const rut = u ? u.rut : '';
    const email = u ? u.email : '';
    const estado = u ? u.status : 'Activo';

    container.innerHTML = `
        <form id="drawerUsuarioForm" onsubmit="event.preventDefault(); guardarUsuarioDesdeDrawer(${id || 'null'});">
            <div class="mb-3">
                <label class="form-label small fw-bold text-secondary">Nombre Completo</label>
                <input type="text" class="form-control" id="drawerUserFullName" value="${nombre}" placeholder="Ej. Roberto Morales Pizarro" required>
            </div>
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <label class="form-label small fw-bold text-secondary">RUT Institucional</label>
                    <input type="text" class="form-control" id="drawerUserRut" value="${rut}" placeholder="12.345.678-9" required>
                </div>
                <div class="col-6">
                    <label class="form-label small fw-bold text-secondary">Estado</label>
                    <select class="form-select" id="drawerUserStatus">
                        <option value="Activo" ${estado === 'Activo' ? 'selected' : ''}>Activo</option>
                        <option value="Inactivo" ${estado === 'Inactivo' ? 'selected' : ''}>Inactivo</option>
                    </select>
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold text-secondary">Correo Institucional (@laserena.cl)</label>
                <input type="email" class="form-control" id="drawerUserEmail" value="${email}" placeholder="usuario@laserena.cl" required>
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold text-secondary">Delegación Asignada</label>
                <select class="form-select" id="drawerUserDelegation">
                    <option value="">Consolidado Central</option>
                    <option value="Centro Histórico">Centro Histórico</option>
                    <option value="Las Compañías">Las Compañías</option>
                    <option value="La Pampa">La Pampa</option>
                    <option value="Avenida del Mar">Avenida del Mar</option>
                    <option value="La Antena">La Antena</option>
                    <option value="Sector Rural">Sector Rural</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold text-secondary">Cargo / Función</label>
                <select class="form-select" id="drawerUserPosition">
                    <option value="Territorial OO.CC.">Territorial OO.CC.</option>
                    <option value="Gestor Social">Gestor Social</option>
                    <option value="Prevención y Seguridad">Prevención y Seguridad</option>
                    <option value="Medio Ambiente / Obras">Medio Ambiente / Obras</option>
                    <option value="Administrador General">Administrador General</option>
                </select>
            </div>
        </form>
    `;
}

function cargarFormularioVecinoDrawer(id, container) {
    let v = null;
    if (id && window.datasetVecinos) {
        v = window.datasetVecinos.find(item => item.id == id);
    }

    const nombre = v ? v.nombre : '';
    const rut = v ? v.rut : '';
    const dir = v ? v.direccion : '';
    const tel = v ? v.telefono : '';
    const terr = v ? v.territorio : 'Centro';
    const est = v ? v.estado : 'Activo';

    container.innerHTML = `
        <form id="drawerVecinoForm" onsubmit="event.preventDefault(); guardarVecinoDesdeDrawer(${id || 'null'});">
            <div class="mb-3">
                <label class="form-label small fw-bold text-secondary">Nombre del Vecino(a)</label>
                <input type="text" class="form-control" id="drawerVecinoNombre" value="${nombre}" placeholder="Nombre y Apellidos" required>
            </div>
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <label class="form-label small fw-bold text-secondary">RUT</label>
                    <input type="text" class="form-control" id="drawerVecinoRut" value="${rut}" placeholder="12.345.678-9" required>
                </div>
                <div class="col-6">
                    <label class="form-label small fw-bold text-secondary">Teléfono</label>
                    <input type="text" class="form-control" id="drawerVecinoTel" value="${tel}" placeholder="+56 9 8765 4321">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold text-secondary">Dirección / Junta de Vecinos</label>
                <input type="text" class="form-control" id="drawerVecinoDir" value="${dir}" placeholder="Calle, número, sector" required>
            </div>
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <label class="form-label small fw-bold text-secondary">Sector Comunal</label>
                    <select class="form-select" id="drawerVecinoTerr">
                        <option value="Centro" ${terr === 'Centro' ? 'selected' : ''}>La Serena Centro</option>
                        <option value="Norte" ${terr === 'Norte' ? 'selected' : ''}>Las Compañías</option>
                        <option value="Sur" ${terr === 'Sur' ? 'selected' : ''}>La Pampa</option>
                        <option value="Oriente" ${terr === 'Oriente' ? 'selected' : ''}>San Joaquín</option>
                        <option value="Rural" ${terr === 'Rural' ? 'selected' : ''}>Sector Rural</option>
                    </select>
                </div>
                <div class="col-6">
                    <label class="form-label small fw-bold text-secondary">Estado</label>
                    <select class="form-select" id="drawerVecinoEst">
                        <option value="Activo" ${est === 'Activo' ? 'selected' : ''}>Activo</option>
                        <option value="Inactivo" ${est === 'Inactivo' ? 'selected' : ''}>Inactivo</option>
                    </select>
                </div>
            </div>
        </form>
    `;
}

function ejecutarGuardadoDrawer() {
    if (activeMaintainerType === 'usuario') {
        const form = document.getElementById('drawerUsuarioForm');
        if (form && form.reportValidity()) {
            form.dispatchEvent(new Event('submit'));
        }
    } else if (activeMaintainerType === 'vecino') {
        const form = document.getElementById('drawerVecinoForm');
        if (form && form.reportValidity()) {
            form.dispatchEvent(new Event('submit'));
        }
    }
}

function guardarUsuarioDesdeDrawer(id) {
    const nombre = document.getElementById('drawerUserFullName').value;
    const rut = document.getElementById('drawerUserRut').value;
    const email = document.getElementById('drawerUserEmail').value;
    const status = document.getElementById('drawerUserStatus').value;
    const delegation = document.getElementById('drawerUserDelegation').value;
    const position = document.getElementById('drawerUserPosition').value;

    if (id && window.datasetUsuarios) {
        const u = window.datasetUsuarios.find(item => item.id == id);
        if (u) {
            u.full_name = nombre;
            u.rut = rut;
            u.email = email;
            u.status = status;
            u.delegation_name = delegation;
            u.position_name = position;
        }
    } else if (window.datasetUsuarios) {
        window.datasetUsuarios.unshift({
            id: Date.now(),
            full_name: nombre,
            rut: rut,
            email: email,
            status: status,
            delegation_name: delegation,
            position_name: position,
            roles: ['Gestor']
        });
    }

    cerrarAdminDrawer();
    if (typeof renderTablaUsuarios === 'function') renderTablaUsuarios();
    if (typeof mostrarToast === 'function') mostrarToast('Funcionario guardado correctamente');
}

function guardarVecinoDesdeDrawer(id) {
    const nombre = document.getElementById('drawerVecinoNombre').value;
    const rut = document.getElementById('drawerVecinoRut').value;
    const dir = document.getElementById('drawerVecinoDir').value;
    const tel = document.getElementById('drawerVecinoTel').value;
    const terr = document.getElementById('drawerVecinoTerr').value;
    const est = document.getElementById('drawerVecinoEst').value;

    if (id && window.datasetVecinos) {
        const v = window.datasetVecinos.find(item => item.id == id);
        if (v) {
            v.nombre = nombre;
            v.rut = rut;
            v.direccion = dir;
            v.telefono = tel;
            v.territorio = terr;
            v.estado = est;
        }
    } else if (window.datasetVecinos) {
        window.datasetVecinos.unshift({
            id: Date.now(),
            nombre: nombre,
            rut: rut,
            direccion: dir,
            telefono: tel,
            territorio: terr,
            gestion: 'Solicitud',
            estado: est
        });
    }

    cerrarAdminDrawer();
    if (typeof renderTablaVecinos === 'function') renderTablaVecinos();
    if (typeof mostrarToast === 'function') mostrarToast('Ficha de vecino actualizada');
}

// 2. CONTROL DE LA BARRA FLOTANTE DE ACCIONES POR LOTE
function actualizarBarraLotePro() {
    const bar = document.getElementById('adminFloatingActionBar');
    const badge = document.getElementById('batchCountNumber');
    if (!bar || !badge) return;

    const count = selectedTableRows.size;
    if (count > 0) {
        badge.textContent = `${count} seleccionado${count > 1 ? 's' : ''}`;
        bar.classList.add('active');
    } else {
        bar.classList.remove('active');
    }
}

function toggleFilaSeleccionada(id, checkbox) {
    if (checkbox.checked) {
        selectedTableRows.add(id);
        const tr = checkbox.closest('tr');
        if (tr) tr.classList.add('row-selected');
    } else {
        selectedTableRows.delete(id);
        const tr = checkbox.closest('tr');
        if (tr) tr.classList.remove('row-selected');
    }
    actualizarBarraLotePro();
}

function deseleccionarTodoFilas() {
    selectedTableRows.clear();
    document.querySelectorAll('.row-select-checkbox').forEach(cb => {
        cb.checked = false;
        const tr = cb.closest('tr');
        if (tr) tr.classList.remove('row-selected');
    });
    const selectAllCb = document.getElementById('checkAllVecinos');
    if (selectAllCb) selectAllCb.checked = false;
    actualizarBarraLotePro();
}

function ejecutarAccionLote(accion) {
    if (selectedTableRows.size === 0) return;

    if (accion === 'toggle-status') {
        if (window.datasetVecinos) {
            window.datasetVecinos.forEach(v => {
                if (selectedTableRows.has(v.id)) {
                    v.estado = v.estado === 'Activo' ? 'Inactivo' : 'Activo';
                }
            });
            if (typeof renderTablaVecinos === 'function') renderTablaVecinos();
        }
        if (typeof mostrarToast === 'function') mostrarToast(`Estados actualizados para ${selectedTableRows.size} registros`);
        deseleccionarTodoFilas();
    } else if (accion === 'export-excel') {
        if (typeof exportarSeleccionadosExcel === 'function') {
            exportarSeleccionadosExcel();
        }
        deseleccionarTodoFilas();
    } else if (accion === 'delete') {
        if (confirm(`¿Está seguro de eliminar los ${selectedTableRows.size} registros seleccionados? Esta acción requiere privilegios de Administrador Central.`)) {
            if (window.datasetVecinos) {
                window.datasetVecinos = window.datasetVecinos.filter(v => !selectedTableRows.has(v.id));
                if (typeof renderTablaVecinos === 'function') renderTablaVecinos();
            }
            if (typeof mostrarToast === 'function') mostrarToast(`Se eliminaron ${selectedTableRows.size} registros`);
            deseleccionarTodoFilas();
        }
    }
}

// 3. EVENTOS DE TECLADO (ACCESIBILIDAD Y AGILIDAD)
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        cerrarAdminDrawer();
        deseleccionarTodoFilas();
    }
});

// 4. FILTROS RÁPIDOS POR FACETAS (FACET PILLS) PARA USUARIOS
function filtrarUsuariosFacet(valor, btn) {
    if (btn) {
        btn.closest('.facet-pill-group').querySelectorAll('.facet-pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
    }
    const searchInput = document.getElementById('searchUsuariosInput');
    const selectEstado = document.getElementById('filtroEstadoUsuario');
    const selectRol = document.getElementById('filtroRolUsuario');
    const selectDelegacion = document.getElementById('filtroDelegacionUsuario');

    if (!valor) {
        if (selectEstado) selectEstado.value = '';
        if (selectRol) selectRol.value = '';
        if (selectDelegacion) selectDelegacion.value = '';
        if (searchInput) searchInput.value = '';
    } else if (valor === 'Activo' || valor === 'Inactivo') {
        if (selectEstado) selectEstado.value = valor;
    } else if (valor === 'admin') {
        if (searchInput) searchInput.value = 'admin';
    } else {
        if (selectDelegacion) selectDelegacion.value = valor;
    }
    if (typeof filtrarUsuarios === 'function') filtrarUsuarios();
}

function toggleSeleccionarTodosUsuarios(checked) {
    selectedTableRows.clear();
    document.querySelectorAll('.check-user-row').forEach(cb => {
        cb.checked = checked;
        const id = parseInt(cb.dataset.id);
        const tr = cb.closest('tr');
        if (checked) {
            selectedTableRows.add(id);
            if (tr) tr.classList.add('row-selected');
        } else {
            if (tr) tr.classList.remove('row-selected');
        }
    });
    actualizarBarraLotePro();
}

