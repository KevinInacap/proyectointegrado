        /* ==========================================================================
           LOG DE AUDITORÍA Y TRAZABILIDAD DE ACCIONES (ADMINISTRADOR)
           ========================================================================== */
        let datasetAuditLogs = [];
        let logsFiltradosAuditoria = [];
        let paginaAuditoria = 1;
        const filasPorPaginaAuditoria = 10;

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
                    paginaAuditoria = 1;
                    renderTablaAuditoria();
                    if (mostrarToastAviso) mostrarToast('✓ Log de auditoría actualizado.');
                }
            } catch (err) {
                console.error("Error al cargar logs de auditoría:", err);
                if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-danger"><i class="bi bi-exclamation-circle me-1"></i> No se pudo cargar el historial de auditoría.</td></tr>`;
                if (mostrarToastAviso && window.Swal) Swal.fire({icon: 'error', title: 'Auditoría no disponible', text: 'No se pudo cargar el historial. Inténtalo nuevamente.'});
            }
        }

        function renderTablaAuditoria() {
            const tbody = document.getElementById('tablaAuditoriaBody');
            const lblTotal = document.getElementById('lblTotalAuditLogs');
            const lblPagina = document.getElementById('lblPaginaAuditoria');
            const btnAnterior = document.getElementById('btnPaginaAnteriorAuditoria');
            const btnSiguiente = document.getElementById('btnPaginaSiguienteAuditoria');
            if (!tbody) return;
            tbody.innerHTML = '';
            const total = logsFiltradosAuditoria.length;
            const totalPaginas = Math.max(1, Math.ceil(total / filasPorPaginaAuditoria));
            paginaAuditoria = Math.min(Math.max(1, paginaAuditoria), totalPaginas);
            const inicio = (paginaAuditoria - 1) * filasPorPaginaAuditoria;
            if (lblTotal) lblTotal.textContent = `${total} eventos registrados`;
            if (lblPagina) lblPagina.textContent = `Página ${paginaAuditoria} de ${totalPaginas}`;
            if (btnAnterior) btnAnterior.disabled = paginaAuditoria <= 1;
            if (btnSiguiente) btnSiguiente.disabled = paginaAuditoria >= totalPaginas;
            if (!total) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted"><i class="bi bi-info-circle me-1"></i> No se registran eventos con los filtros seleccionados.</td></tr>`;
                return;
            }
            logsFiltradosAuditoria.slice(inicio, inicio + filasPorPaginaAuditoria).forEach(l => {
                const tr = document.createElement('tr');
                const actUpper = (l.action || '').toUpperCase();
                const descLower = (l.description || '').toLowerCase();
                let badgeAction = actUpper === 'CREATE'
                    ? `<span class="badge bg-success text-white px-2 py-1"><i class="bi bi-plus-circle-fill me-1"></i> CREACIÓN</span>`
                    : actUpper === 'DELETE'
                        ? `<span class="badge bg-danger text-white px-2 py-1"><i class="bi bi-trash-fill me-1"></i> ELIMINACIÓN</span>`
                        : descLower.includes('estado')
                            ? `<span class="badge bg-warning text-dark px-2 py-1"><i class="bi bi-toggle2-on me-1"></i> ESTADO</span>`
                            : descLower.includes('contrase') || descLower.includes('clave')
                                ? `<span class="badge bg-info text-dark px-2 py-1"><i class="bi bi-key-fill me-1"></i> CONTRASEÑA</span>`
                                : `<span class="badge bg-primary text-white px-2 py-1"><i class="bi bi-pencil-fill me-1"></i> MODIFICACIÓN</span>`;
                tr.innerHTML = `
                    <td class="text-nowrap font-monospace small text-secondary"><i class="bi bi-calendar3 me-1 text-muted"></i>${escapeHtml(l.timestamp)}</td>
                    <td><div class="d-flex align-items-center gap-2"><div class="user-avatar-pill admin" style="width:28px;height:28px;font-size:.72rem;min-width:28px"><i class="bi bi-person-fill"></i></div><div><span class="fw-bold text-dark d-block small">${escapeHtml(l.admin_name)}</span><small class="text-muted">@${escapeHtml(l.admin_username)}</small></div></div></td>
                    <td class="text-center">${badgeAction}</td>
                    <td><span class="fw-semibold text-dark d-block">${escapeHtml(l.description)}</span></td>
                    <td class="text-end"><span class="badge bg-light text-secondary border font-monospace px-2 py-1">${escapeHtml(l.affected_table)} #${escapeHtml(l.affected_record_id)}</span></td>`;
                tbody.appendChild(tr);
            });
        }

        function cambiarPaginaAuditoria(delta) {
            const paginas = Math.max(1, Math.ceil(logsFiltradosAuditoria.length / filasPorPaginaAuditoria));
            paginaAuditoria = Math.min(Math.max(1, paginaAuditoria + delta), paginas);
            renderTablaAuditoria();
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

            paginaAuditoria = 1;
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
            localStorage.removeItem('sgr_theme_preference');
            document.documentElement.removeAttribute('data-theme');
            document.body.removeAttribute('data-theme');
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
            centro: { nombre: 'Centro', mapa: 'Centro', sector: 'Área urbana central', badge: 'SEDE CENTRAL', badgeColor: '#C41230', monogram: 'CE', number: '01' },
            lascompanias: { id: 'companias', nombre: 'Las Compañías', mapa: 'Las Compañías', sector: 'Sector norte de la comuna', badge: 'SECTOR NORTE', badgeColor: '#6554C0', monogram: 'LC', number: '02' },
            lapampa: { id: 'pampa', nombre: 'La Pampa', mapa: 'La Pampa', sector: 'Sector sur de la comuna', badge: 'SECTOR SUR', badgeColor: '#008F8C', monogram: 'LP', number: '03' },
            laflorida: { id: 'antena', nombre: 'La Antena', mapa: 'La Antena', sector: 'Sector oriente de la comuna', badge: 'SECTOR ORIENTE', badgeColor: '#B86A08', monogram: 'LA', number: '04' },
            tierrasblancas: { id: 'costa', nombre: 'Avenida del Mar', mapa: 'Avenida del Mar', sector: 'Franja costera de la comuna', badge: 'BORDE COSTERO', badgeColor: '#1677A8', monogram: 'AM', number: '05' },
            rural: { id: 'rural', nombre: 'Rural', mapa: 'Rural', sector: 'Localidades rurales y caletas', badge: 'SECTOR RURAL', badgeColor: '#678341', monogram: 'RU', number: '06' }
        };

        window.currentMapSedeKey = 'centro';
        let mapaDelegacionesLeaflet = null;
        const datosSedesDelegaciones = {};
        const marcadoresDelegaciones = {};
        let popupDelegacion = null;

        async function inicializarMapaDelegaciones() {
            const mapElement = document.getElementById('mapaDelegacionesReal');
            const loader = document.getElementById('mapaDelegacionesLoader');
            if (!mapElement || mapaDelegacionesLeaflet) return;
            seleccionarDelegacionMapa(window.currentMapSedeKey);
            if (!window.maplibregl) {
                if (loader) loader.textContent = 'El mapa no está disponible. Puedes consultar las sedes en las fichas.';
                return;
            }
            mapaDelegacionesLeaflet = new maplibregl.Map({
                container: mapElement,
                style: 'https://tiles.openfreemap.org/styles/liberty',
                center: [-71.25, -29.91], zoom: 12,
                scrollZoom: false, attributionControl: true
            });
            mapaDelegacionesLeaflet.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
            // Los marcadores HTML quedan sobre la cartografía y no dependen del orden de sus capas.
            const resizeObserver = new ResizeObserver(() => mapaDelegacionesLeaflet.resize());
            resizeObserver.observe(mapElement);
            mapaDelegacionesLeaflet.on('remove', () => resizeObserver.disconnect());
            mapaDelegacionesLeaflet.on('error', () => {
                if (!mapaDelegacionesLeaflet.isStyleLoaded() && loader) {
                    loader.classList.remove('oculto');
                    loader.textContent = 'La cartografía está tardando en cargar. Las direcciones siguen disponibles en las fichas.';
                }
            });

            try {
                const response = await fetch('/static/data/delegaciones-la-serena.geojson', {
                    headers: { Accept: 'application/geo+json, application/json' }
                });
                if (!response.ok) throw new Error('No se pudieron consultar las sedes.');
                const geojson = await response.json();
                geojson.features.filter(feature => feature.properties.kind === 'office')
                    .forEach(feature => { datosSedesDelegaciones[feature.properties.name] = feature; });
                Object.entries(delegacionesMapaData).forEach(([key, data]) => {
                    const sede = datosSedesDelegaciones[data.mapa];
                    if (!sede) return;
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'delegation-map-pin';
                    button.style.setProperty('--delegation-color', data.badgeColor);
                    button.setAttribute('aria-label', 'Ver sede de ' + data.nombre);
                    button.setAttribute('aria-pressed', 'false');
                    button.title = data.nombre;
                    const dot = document.createElement('span');
                    dot.className = 'delegation-pin-dot';
                    dot.textContent = data.number;
                    button.appendChild(dot);
                    button.addEventListener('click', event => {
                        event.stopPropagation();
                        seleccionarDelegacionMapa(key);
                    });
                    marcadoresDelegaciones[key] = new maplibregl.Marker({ element: button, anchor: 'bottom' })
                        .setLngLat(sede.geometry.coordinates).addTo(mapaDelegacionesLeaflet);
                });
                const ready = () => {
                    if (loader) loader.classList.add('oculto');
                    seleccionarDelegacionMapa(window.currentMapSedeKey);
                };
                if (mapaDelegacionesLeaflet.loaded()) ready();
                else mapaDelegacionesLeaflet.once('load', ready);
                seleccionarDelegacionMapa(window.currentMapSedeKey);
            } catch (error) {
                if (loader) {
                    loader.classList.remove('oculto');
                    loader.textContent = 'No se pudieron cargar las sedes. Recarga la página para volver a intentarlo.';
                }
                console.error('Error al consultar sedes:', error);
            }
        }

        function seleccionarDelegacionMapa(key) {
            const data = delegacionesMapaData[key];
            if (!data) return;
            window.currentMapSedeKey = key;
            document.querySelectorAll('.serena-sede-pill').forEach(pill => {
                const selected = pill.id === 'pill-sede-' + key;
                pill.classList.toggle('active', selected);
                pill.setAttribute('aria-pressed', String(selected));
            });
            Object.entries(marcadoresDelegaciones).forEach(([markerKey, marker]) => {
                marker.getElement().classList.toggle('selected', markerKey === key);
                marker.getElement().setAttribute('aria-pressed', String(markerKey === key));
            });
            const card = document.getElementById('panelFocoTerritorial');
            if (card) card.style.setProperty('--delegation-color', data.badgeColor);
            const content = {
                mapFocusTitle: data.nombre, mapFocusSector: data.sector,
                mapFocusMonogram: data.monogram, mapFocusNumber: data.number,
                mapFocusBadge: data.badge
            };
            Object.entries(content).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) element.textContent = value;
            });
            const swatch = document.getElementById('mapFocusSwatch');
            if (swatch) swatch.style.setProperty('--delegation-color', data.badgeColor);
            const sede = datosSedesDelegaciones[data.mapa];
            const address = document.querySelector('#mapFocusAddress [data-address-value]');
            if (address) address.textContent = sede?.properties?.address || 'Consultando dirección de la sede…';
            const coordinates = document.getElementById('mapFocusCoordinates');
            if (coordinates) coordinates.textContent = sede
                ? sede.geometry.coordinates[1].toFixed(5) + ', ' + sede.geometry.coordinates[0].toFixed(5) : '—';

            if (mapaDelegacionesLeaflet && sede) {
                const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
                mapaDelegacionesLeaflet.resize();
                mapaDelegacionesLeaflet.easeTo({
                    center: sede.geometry.coordinates, zoom: 14,
                    duration: reducedMotion ? 0 : 650
                });
                if (popupDelegacion) popupDelegacion.remove();
                const popup = document.createElement('div');
                popup.className = 'delegation-map-label';
                const title = document.createElement('strong');
                title.textContent = data.nombre;
                const subtitle = document.createElement('span');
                subtitle.textContent = 'Sede municipal · ubicación de referencia';
                popup.append(title, subtitle);
                popupDelegacion = new maplibregl.Popup({ offset: 44, closeButton: false, maxWidth: '240px' })
                    .setLngLat(sede.geometry.coordinates).setDOMContent(popup).addTo(mapaDelegacionesLeaflet);
            }
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
