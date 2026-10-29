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
                const cargo = positionsCatalog.find(item => normalizarNombreRolCargo(item.name) === normalizarNombreRolCargo(cargoAnterior));
                const previousCheckbox = cargo?.base_role_id ? document.getElementById(`chkRole_${cargo.base_role_id}`) : buscarCheckboxRol(anterior);
                if (previousCheckbox) {
                    previousCheckbox.checked = false;
                    previousCheckbox.disabled = false;
                    previousCheckbox.title = '';
                }
            }
            if (actual) {
                const cargo = positionsCatalog.find(item => normalizarNombreRolCargo(item.name) === normalizarNombreRolCargo(cargoActual));
                const currentCheckbox = cargo?.base_role_id ? document.getElementById(`chkRole_${cargo.base_role_id}`) : buscarCheckboxRol(actual);
                if (currentCheckbox) {
                    currentCheckbox.checked = true;
                    currentCheckbox.disabled = true;
                    currentCheckbox.title = 'Rol base asignado por el cargo';
                }
            }
        }

        function actualizarRolesSegunCargo(positionId, conservarHistoricos = false) {
            document.querySelectorAll('.role-chk').forEach(chk => {
                const role = rolesCatalog.find(item => String(item.id) === String(chk.value));
                const coincide = Boolean(positionId) && String(role?.position_id || '') === String(positionId);
                const historico = !coincide && conservarHistoricos && chk.checked;
                if (!coincide && !historico) chk.checked = false;
                if (chk.parentElement) chk.parentElement.hidden = !coincide && !historico;
                chk.title = historico ? 'Asignación histórica conservada para revisión.' : '';
                const label = chk.parentElement?.querySelector('label');
                if (label && role) label.textContent = role.name + (historico ? ' (histórico)' : '');
            });
            const help = document.getElementById('usrCargoRoleHelp');
            if (help) help.textContent = positionId
                ? 'El cargo asigna su rol base automáticamente. Los roles históricos se conservan mientras no cambies el cargo.'
                : 'Selecciona un cargo para ver sus roles.';
        }

        function abrirModalUsuario(modo, id = null) {
            const elCont = document.getElementById('rolesCheckboxesContainer');
            elCont.innerHTML = '';

            // Renderizar Checkboxes de Roles desde catálogo DB
            rolesCatalog.forEach(r => {
                const div = document.createElement('div');
                div.className = 'form-check form-check-inline me-3 mb-1';
                const input = document.createElement('input');
                input.className = 'form-check-input role-chk';
                input.type = 'checkbox'; input.value = String(r.id); input.id = `chkRole_${r.id}`;
                const label = document.createElement('label');
                label.className = 'form-check-label small fw-semibold'; label.htmlFor = input.id;
                label.textContent = r.name;
                div.appendChild(input); div.appendChild(label);
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
                actualizarRolesSegunCargo(selPos.value);
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
                document.getElementById('usrIsSuperuser').checked = !!u.is_superuser;
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
            actualizarRolesSegunCargo(selPos.value, modo !== 'nuevo');

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

            const existente = editId ? datasetUsuarios.find(u => String(u.id) === String(editId)) : null;
            const normalizarRut = valor => String(valor || '').trim().replace(/[.-]/g, '').toUpperCase();
            const rutSinCambios = !!existente && normalizarRut(rut) === normalizarRut(existente.rut);
            if (!rutSinCambios && typeof validarRutChileno === 'function' && !validarRutChileno(rut)) {
                Swal.fire({
                    icon: 'error',
                    title: 'RUT inválido',
                    text: 'Revisa el número y el dígito verificador antes de continuar.'
                });
                return;
            }

            if (!rutSinCambios && datasetUsuarios.some(u => String(u.id) !== String(editId) && normalizarRut(u.rut) === normalizarRut(rut))) {
                Swal.fire({icon: 'error', title: 'RUT duplicado', text: 'Ya existe un funcionario registrado con ese RUT.'});
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
                rut: rutSinCambios ? existente.rut : (typeof formatearRutChileno === 'function' ? formatearRutChileno(rut) : rut),
                username: username,
                email: email.trim().toLowerCase(),
                password: password,
                status: status,
                delegation_id: delegationId ? parseInt(delegationId) : null,
                position_id: positionId ? parseInt(positionId) : null,
                role_ids: roleIds
            };
            // Editar cargo o roles conserva los permisos técnicos por separado.
            // El interruptor representa solo superusuario, nunca el flag staff.
            if (!editId) {
                payload.is_staff = isSuperuser;
                payload.is_superuser = isSuperuser;
            } else if (existente && isSuperuser !== !!existente.is_superuser) {
                payload.is_superuser = isSuperuser;
            }

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
            if (!filasFiltradasUsuarios.length) {
                Swal.fire({ icon: 'info', title: 'Sin funcionarios para exportar', text: 'No hay registros con los filtros actuales.' });
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
            if (!filasFiltradasUsuarios.length) {
                Swal.fire({ icon: 'info', title: 'Sin funcionarios para exportar', text: 'No hay registros con los filtros actuales.' });
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

