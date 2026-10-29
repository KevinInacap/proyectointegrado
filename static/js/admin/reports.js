        async function generarInformeEjecutivoPDF() {
            try {
                await cargarCatalogosOrganizacion();
                if (!window.jspdf) throw new Error('La librería PDF todavía no está disponible.');
                const doc = new window.jspdf.jsPDF();
                doc.setFontSize(15);
                doc.text('Resumen de delegaciones municipales', 14, 20);
                doc.setFontSize(9);
                doc.text('Datos registrados al ' + new Date().toLocaleDateString('es-CL'), 14, 28);
                doc.autoTable({startY: 35, head: [['Delegación', 'Estado', 'Funcionarios', 'Atenciones del mes', 'Cumplimiento']],
                    body: catalogoDelegacionesDB.map(item => [item.name, item.status, item.users_count,
                        item.monthly_activities ?? 'Sin datos', item.compliance_percentage == null ? 'Sin medición' : item.compliance_percentage + '%'])});
                doc.save('Resumen_delegaciones.pdf');
            } catch (error) { Swal.fire({icon:'error', titleText:'No se pudo generar el PDF', text:error.message}); }
        }

        function abrirModalAuditoria() {
            if (!bsModalAuditoria) {
                const el = document.getElementById('modalAuditoria');
                if (el && window.bootstrap) bsModalAuditoria = new bootstrap.Modal(el);
            }
            if (bsModalAuditoria) bsModalAuditoria.show();
            cargarLogsAuditoriaDB();
        }

        function exportarExcelAuditoria() {
            if (!logsFiltradosAuditoria.length) {
                mostrarToast('No hay registros de auditoría para exportar.');
                return;
            }
            let csv = "Fecha y Hora;Administrador Responsable;Usuario;Acción;Descripción de Modificación;Tabla Afectada;ID Registro\n";
            const csvCell = value => {
                let text = String(value ?? '');
                // Las hojas de cálculo interpretan fórmulas incluso con espacios iniciales.
                if (/^[\s\u0000-\u001f]*[=+\-@]/.test(text)) text = "'" + text;
                return '"' + text.replace(/"/g, '""') + '"';
            };
            logsFiltradosAuditoria.forEach(l => {
                csv += [l.timestamp, l.admin_name, l.admin_username, l.action, l.description,
                    l.affected_table, l.affected_record_id].map(csvCell).join(';') + '\n';
            });
            const blob = new Blob(["\uFEFF" + csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Log_Auditoria_Municipal_LaSerena_${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            mostrarToast('✓ Log de auditoría exportado en CSV/Excel.');
        }

        function exportarGraficoPNG() {
            if (!chartInstance) return;
            const a = document.createElement('a');
            a.href = chartInstance.toBase64Image();
            a.download = 'Grafico_Atenciones_LaSerena.png';
            a.click();
            mostrarToast('✓ Gráfico exportado');
        }

        /* ==========================================================================
           MÓDULO DE REPORTES Y ESTADÍSTICAS INSTITUCIONALES (OFICIAL LA SERENA)
           Con Comparativas 1vs1, Multidelegacional y Monitoreo en Tiempo Real
           ========================================================================== */
        let chartRepDelegacionesInstance = null;
        let chartRepCanalesInstance = null;
        let chartRepEvolucionInstance = null;
        let chartRepTramitesInstance = null;

        // Instancias para comparativa 1 vs 1 y Multi
        let chartCompareRadarInstance = null;
        let chartCompareTramitesInstance = null;
        let chartMultiRankingInstance = null;
        let chartMultiTiemposInstance = null;
        let chartMultiSatisfaccionInstance = null;

        // Subvista activa ('general', '1vs1', 'multi')
        let subvistaReportesActiva = 'general';

        // Catálogo territorial de referencia; no contiene métricas inventadas.
        const catalogoMetricasDelegaciones = {
            centro: { nombre: 'Centro Histórico', sector: 'Área central' },
            companias: { nombre: 'Las Compañías', sector: 'Sector norte' },
            pampa: { nombre: 'La Pampa', sector: 'Sector sur' },
            antena: { nombre: 'La Antena / San Joaquín', sector: 'Sector oriente' },
            costa: { nombre: 'Avenida del Mar', sector: 'Borde costero' },
            rural: { nombre: 'Sector Rural', sector: 'Localidades rurales' }
        };

        // Estado del Tiempo Real (Live Mode)
        let timerLiveReportes = null;
        let esTiempoRealActivo = false;
        let segundosLive = 5;

        function initReportesCharts() {
            // Inicializar vista general por defecto
            initChartsGeneralReportes();
            iniciarTemporizadorTiempoReal();
        }

        function initChartsGeneralReportes() {
            const emptyData = { labels: [], datasets: [] };
            // 1. Delegaciones Bar Chart
            const ctxDel = document.getElementById('chartReporteDelegaciones');
            if (ctxDel && !chartRepDelegacionesInstance) {
                chartRepDelegacionesInstance = new Chart(ctxDel.getContext('2d'), {
                    type: 'bar',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false }, y: { display: false }
                        }
                    }
                });
            } else if (chartRepDelegacionesInstance) {
                chartRepDelegacionesInstance.resize();
            }

            // 2. Canales Doughnut Chart
            const ctxCan = document.getElementById('chartReporteCanales');
            if (ctxCan && !chartRepCanalesInstance) {
                chartRepCanalesInstance = new Chart(ctxCan.getContext('2d'), {
                    type: 'doughnut',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        cutout: '65%'
                    }
                });
            } else if (chartRepCanalesInstance) {
                chartRepCanalesInstance.resize();
            }

            // 3. Evolución Line Chart
            const ctxEvo = document.getElementById('chartReporteEvolucion');
            if (ctxEvo && !chartRepEvolucionInstance) {
                chartRepEvolucionInstance = new Chart(ctxEvo.getContext('2d'), {
                    type: 'line',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false }, y: { display: false }
                        }
                    }
                });
            } else if (chartRepEvolucionInstance) {
                chartRepEvolucionInstance.resize();
            }

            // 4. Trámites Horizontal Bar Chart
            const ctxTra = document.getElementById('chartReporteTramites');
            if (ctxTra && !chartRepTramitesInstance) {
                chartRepTramitesInstance = new Chart(ctxTra.getContext('2d'), {
                    type: 'bar',
                    indexAxis: 'y',
                    data: emptyData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: false } },
                        scales: {
                            x: { display: false }, y: { display: false }
                        }
                    }
                });
            } else if (chartRepTramitesInstance) {
                chartRepTramitesInstance.resize();
            }
        }

        function cambiarSubvistaReporte(subvista, updateUrl = true) {
            if (!adminReportViews.has(subvista)) return;
            subvistaReportesActiva = subvista;
            if (updateUrl) {
                const url = adminRouteUrl('reportes', subvista);
                if (window.location.pathname !== url) window.history.pushState(null, '', url);
            }

            // Actualizar botones de pestañas
            const btnGen = document.getElementById('tabReporteGeneral');
            const btn1v1 = document.getElementById('tabReporte1vs1');
            const btnMul = document.getElementById('tabReporteMulti');

            const vGen = document.getElementById('subvistaReporteGeneral');
            const v1v1 = document.getElementById('subvistaReporte1vs1');
            const vMul = document.getElementById('subvistaReporteMulti');

            // Reset tab styles
            [btnGen, btn1v1, btnMul].forEach(b => {
                if (b) {
                    b.className = 'btn btn-sm border-0 fw-semibold text-secondary px-3 py-2';
                    b.style.background = 'transparent';
                    b.style.color = '#64748B';
                    b.classList.remove('shadow-sm');
                }
            });

            // Hide all views
            if (vGen) vGen.classList.remove('active');
            if (v1v1) v1v1.classList.remove('active');
            if (vMul) vMul.classList.remove('active');

            if (subvista === 'general') {
                if (btnGen) {
                    btnGen.className = 'btn btn-sm btn-white border-0 fw-bold px-3 py-2 shadow-sm';
                    btnGen.style.background = '#FFFFFF';
                    btnGen.style.color = 'var(--muni-navy)';
                }
                if (vGen) vGen.classList.add('active');
                initChartsGeneralReportes();
            } else if (subvista === '1vs1') {
                if (btn1v1) {
                    btn1v1.className = 'btn btn-sm btn-white border-0 fw-bold px-3 py-2 shadow-sm';
                    btn1v1.style.background = '#FFFFFF';
                    btn1v1.style.color = 'var(--muni-red)';
                }
                if (v1v1) v1v1.classList.add('active');
                actualizarComparativa1vs1();
            } else if (subvista === 'multi') {
                if (btnMul) {
                    btnMul.className = 'btn btn-sm btn-white border-0 fw-bold px-3 py-2 shadow-sm';
                    btnMul.style.background = '#FFFFFF';
                    btnMul.style.color = '#16A34A';
                }
                if (vMul) vMul.classList.add('active');
                initComparativaMultiCharts();
            }
        }

        /* ==========================================================================
           LÓGICA COMPARATIVA 1 VS 1 (FRENTE A FRENTE)
           ========================================================================== */
        function actualizarComparativa1vs1() {
            const elSelA = document.getElementById('selectCompareDelA');
            const idA = (elSelA && elSelA.value) ? elSelA.value : 'centro';
            const elSelBInit = document.getElementById('selectCompareDelB');
            let idB = (elSelBInit && elSelBInit.value) ? elSelBInit.value : 'companias';

            const delA = catalogoMetricasDelegaciones[idA] || catalogoMetricasDelegaciones['centro'];
            const delB = catalogoMetricasDelegaciones[idB] || catalogoMetricasDelegaciones['companias'];

            // Actualizar subtítulos territoriales
            const subA = document.getElementById('compareSubA');
            if (subA) subA.textContent = delA.sector;
            const subB = document.getElementById('compareSubB');
            if (subB) subB.textContent = delB.sector;

            const grid = document.getElementById('gridMetricas1vs1');
            const elConc = document.getElementById('conclusion1vs1');
            if (grid) grid.innerHTML = `<div class="col-12"><div class="dashboard-empty-state p-4 text-center"><strong>${delA.nombre} y ${delB.nombre}</strong><p class="mb-0 mt-1">La comparación aparecerá cuando exista una consulta conectada a registros reales de atención.</p></div></div>`;
            ['chartCompareRadar', 'chartCompareTramites'].forEach(id => {
                const canvas = document.getElementById(id);
                if (canvas && canvas.closest('.card')) canvas.closest('.card').classList.add('d-none');
            });
            if (elConc) elConc.textContent = 'Sin una fuente de reportes conectada, no es posible calcular diferencias ni emitir conclusiones.';
        }

        /* ==========================================================================
           LÓGICA COMPARATIVA MULTIDELEGACIONAL (TODAS CONTRA TODAS)
           ========================================================================== */
        function initComparativaMultiCharts() {
            document.querySelectorAll('#subvistaReporteMulti canvas').forEach(canvas => {
                const card = canvas.closest('.card');
                if (card) card.classList.add('d-none');
            });
        }

        /* ==========================================================================
           SISTEMA DE TIEMPO REAL / LIVE STREAM SIMULADO
           ========================================================================== */
        function iniciarTemporizadorTiempoReal() {
            if (timerLiveReportes) clearInterval(timerLiveReportes);
            const elSec = document.getElementById('liveCounterSec');
            if (elSec) elSec.textContent = 'Pausado';
            const dot = document.getElementById('liveDotIndicator');
            const txt = document.getElementById('liveTextIndicator');
            const btnTxt = document.getElementById('btnToggleLiveText');
            const btnIcon = document.getElementById('btnToggleLiveIcon');
            if (dot) dot.classList.add('paused');
            if (txt) txt.textContent = 'Sin conexión en vivo';
            if (btnTxt) btnTxt.textContent = 'API pendiente';
            if (btnIcon) {
                btnIcon.classList.remove('bi-pause-fill');
                btnIcon.classList.add('bi-plug-fill');
            }
        }

        function toggleTiempoRealReportes() {
            esTiempoRealActivo = false;
            const dot = document.getElementById('liveDotIndicator');
            const txt = document.getElementById('liveTextIndicator');
            const btnTxt = document.getElementById('btnToggleLiveText');
            const btnIcon = document.getElementById('btnToggleLiveIcon');

            if (dot) dot.classList.add('paused');
            if (txt) txt.textContent = 'Sin conexión en vivo';
            if (btnTxt) btnTxt.textContent = 'Disponible al conectar API';
            if (btnIcon) {
                btnIcon.classList.remove('bi-pause-fill');
                btnIcon.classList.add('bi-plug-fill');
            }
            const btn = document.getElementById('btnToggleLiveReportes');
            if (btn) btn.disabled = true;
            mostrarToast('La actualización en vivo se habilitará cuando exista una API de reportes conectada.');
        }

        function forzarActualizacionEnVivo() {
            mostrarToast('Aún no hay una API de reportes conectada para actualizar estos resultados.');
        }

        function ejecutarTickTiempoReal() {
            actualizarReportesDatos();
        }

        function actualizarReportesDatos() {
            const elP = document.getElementById('filtroPeriodoReporte');
            const p = (elP && elP.value) ? elP.value : 'trimestre';
            const elD = document.getElementById('filtroDelegacionReporte');
            const d = (elD && elD.value) ? elD.value : '';
            const elC = document.getElementById('filtroCanalReporte');
            const c = (elC && elC.value) ? elC.value : '';

            const params = new URLSearchParams({ period: p });
            if (d) params.set('delegation', d);
            if (c) params.set('channel', c);
            mostrarToast('Los filtros se habilitarán cuando el módulo tenga su consulta de reportes conectada a datos reales.');
        }

        function restablecerFiltrosReportes() {
            if (document.getElementById('filtroPeriodoReporte')) document.getElementById('filtroPeriodoReporte').value = 'trimestre';
            if (document.getElementById('filtroDelegacionReporte')) document.getElementById('filtroDelegacionReporte').value = '';
            if (document.getElementById('filtroCanalReporte')) document.getElementById('filtroCanalReporte').value = '';
            mostrarToast('Filtros restablecidos. Los datos se consultarán al conectar la API de reportes.');
        }

        /* ==========================================================================
           EXPORTACIÓN COMPLETA A EXCEL MULTI-HOJA Y PDF OFICIAL
           ========================================================================== */
        function exportarReportesExcel() {
            if (!window.XLSX) {
                Swal.fire('La librería XLSX está cargando.');
                return;
            }

            const wb = XLSX.utils.book_new();

            // Hoja 1: Resumen Ejecutivo y KPIs
            const resumenData = [
                ["ILUSTRE MUNICIPALIDAD DE LA SERENA - GESTIÓN DE ATENCIÓN CIUDADANA (SGR)"],
                ["INFORME EJECUTIVO DE RENDIMIENTO INSTITUCIONAL Y TERRITORIAL"],
                ["Fecha de Emisión:", new Date().toLocaleString('es-CL')],
                [],
                ["Indicadores", "Estado"],
                ["Atenciones", "Los valores se incorporarán al conectar la consulta a la base de datos."],
                ["Tiempo de espera y satisfacción", "No hay datos suficientes registrados para calcularlos."]
            ];
            const ws1 = XLSX.utils.aoa_to_sheet(resumenData);
            XLSX.utils.book_append_sheet(wb, ws1, "Resumen_Ejecutivo");

            // Hoja 2: Rendimiento por Delegación
            const table = document.getElementById('tablaReportesDelegaciones');
            if (table) {
                const ws2 = XLSX.utils.table_to_sheet(table);
                XLSX.utils.book_append_sheet(wb, ws2, "Todas_Las_Delegaciones");
            }

            // Hoja 3: Comparativa 1 vs 1 Activa
            const elCompA = document.getElementById('selectCompareDelA');
            const idA = (elCompA && elCompA.value) ? elCompA.value : 'centro';
            const elCompB = document.getElementById('selectCompareDelB');
            const idB = (elCompB && elCompB.value) ? elCompB.value : 'companias';
            const delA = catalogoMetricasDelegaciones[idA] || catalogoMetricasDelegaciones['centro'];
            const delB = catalogoMetricasDelegaciones[idB] || catalogoMetricasDelegaciones['companias'];

            const compData = [
                ["COMPARATIVA FRENTE A FRENTE (1 VS 1)"],
                ["Métrica", delA.nombre, delB.nombre, "Estado"],
                ["Atenciones, metas, tiempos, satisfacción y dotación", "No disponible", "No disponible", "API de reportes pendiente"]
            ];
            const ws3 = XLSX.utils.aoa_to_sheet(compData);
            XLSX.utils.book_append_sheet(wb, ws3, "Comparativa_1vs1");

            // Hoja 4: Canales de Atención y Ranking de Trámites
            const canalesData = [
                ["DISTRIBUCIÓN POR CANAL DE ATENCIÓN"],
                ["Canal", "Volumen Atenciones", "Porcentaje"],
                ["No disponible", "—", "—"],
                [],
                ["TOP TRÁMITES MÁS DEMANDADOS"],
                ["Trámite", "Solicitudes Registradas"],
                ["No disponible", "—"]
            ];
            const ws4 = XLSX.utils.aoa_to_sheet(canalesData);
            XLSX.utils.book_append_sheet(wb, ws4, "Canales_Y_Tramites");

            XLSX.writeFile(wb, "Reporte_Estadistico_Integral_LaSerena_2026.xlsx");
            mostrarToast("✓ Archivo Excel Multi-Hoja descargado con éxito.");
        }

        function generarReportePDFOficial() {
            if (!window.jspdf) {
                Swal.fire('La librería PDF está cargando.');
                return;
            }
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'letter' });

            // Banda superior Roja La Serena (#C41230) y Azul Marino (#1B365D)
            doc.setFillColor(196, 18, 48);
            doc.rect(0, 0, 216, 16, 'F');
            doc.setFillColor(27, 54, 93);
            doc.rect(0, 16, 216, 3, 'F');

            // Encabezado
            doc.setTextColor(255, 255, 255);
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(11);
            doc.text('ILUSTRE MUNICIPALIDAD DE LA SERENA — GESTIÓN DE ATENCIÓN CIUDADANA', 14, 11);

            // Título Principal
            doc.setTextColor(27, 54, 93);
            doc.setFontSize(15);
            doc.setFont('helvetica', 'bold');
            doc.text('INFORME ESTADÍSTICO DE GESTIÓN MUNICIPAL Y TERRITORIAL', 14, 28);

            doc.setFontSize(8.5);
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(90, 100, 120);
            doc.text(`Fecha de emisión: ${new Date().toLocaleDateString('es-CL')} | Borrador con datos disponibles en la base`, 14, 34);

            // Resumen de KPIs
            doc.autoTable({
                startY: 39,
                theme: 'plain',
                styles: { fontSize: 8.5, cellPadding: 2 },
                head: [['Indicador Clave', 'Estado']],
                body: [
                    ['Métricas de gestión', 'Aún no existe conexión de consulta para este reporte.'],
                    ['Tiempo de espera y satisfacción', 'No hay registros suficientes para calcular estos indicadores.']
                ],
                headStyles: { fillColor: [244, 248, 252], textColor: [27, 54, 93], fontStyle: 'bold' }
            });

            // Tabla de Delegaciones
            doc.autoTable({
                startY: doc.lastAutoTable.finalY + 6,
                html: '#tablaReportesDelegaciones',
                theme: 'striped',
                headStyles: { fillColor: [27, 54, 93], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 8 },
                styles: { fontSize: 7.5, cellPadding: 2 },
                alternateRowStyles: { fillColor: [248, 250, 252] }
            });

            // Pie y Firma
            const finalY = doc.lastAutoTable.finalY + 22;
            doc.setDrawColor(200, 200, 200);
            doc.line(20, finalY, 80, finalY);
            doc.line(135, finalY, 195, finalY);

            doc.setFontSize(8);
            doc.setTextColor(80, 80, 80);
            doc.text('Administrador Municipal', 50, finalY + 5, { align: 'center' });
            doc.text('Ilustre Municipalidad de La Serena', 50, finalY + 9, { align: 'center' });

            doc.text('Director(a) de Atención Ciudadana', 165, finalY + 5, { align: 'center' });
            doc.text('Secretaría Comunal de Planificación', 165, finalY + 9, { align: 'center' });

            doc.save('Informe_Gestion_Atencion_Ciudadana_LaSerena.pdf');
            mostrarToast('Informe PDF de estado generado. Las métricas se incluirán al conectar el módulo a datos verificables.');
        }

        function renderAtencionesChart() {
            const ctx = document.getElementById('atencionesChart');
            if (!ctx) return;
            const chartCtx = ctx.getContext('2d');

            const gBlue = chartCtx.createLinearGradient(0, 0, 0, 240);
            gBlue.addColorStop(0, 'rgba(13, 110, 253, 0.28)');
            gBlue.addColorStop(1, 'rgba(13, 110, 253, 0.00)');

            const gGreen = chartCtx.createLinearGradient(0, 0, 0, 240);
            gGreen.addColorStop(0, 'rgba(22, 163, 74, 0.22)');
            gGreen.addColorStop(1, 'rgba(22, 163, 74, 0.00)');

            const gPurple = chartCtx.createLinearGradient(0, 0, 0, 240);
            gPurple.addColorStop(0, 'rgba(124, 58, 237, 0.20)');
            gPurple.addColorStop(1, 'rgba(124, 58, 237, 0.00)');

            chartInstance = new Chart(chartCtx, {
                type: 'line',
                data: {
                    labels: ['Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
                    datasets: [
                        { label: 'Presencial', data: [500, 610, 720, 680, 620, 750], borderColor: '#0D6EFD', backgroundColor: gBlue, borderWidth: 2.5, fill: true, tension: 0.38, pointRadius: 4, pointBackgroundColor: '#0D6EFD' },
                        { label: 'Telefónica', data: [290, 380, 480, 410, 400, 540], borderColor: '#16A34A', backgroundColor: gGreen, borderWidth: 2.5, fill: true, tension: 0.38, pointRadius: 4, pointBackgroundColor: '#16A34A' },
                        { label: 'Online', data: [130, 190, 270, 210, 195, 280], borderColor: '#7C3AED', backgroundColor: gPurple, borderWidth: 2.5, fill: true, tension: 0.38, pointRadius: 4, pointBackgroundColor: '#7C3AED' }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#64748B' } },
                        y: { min: 0, max: 1000, ticks: { stepSize: 250, color: '#64748B' }, grid: { color: 'rgba(226, 232, 240, 0.6)' } }
                    }
                }
            });
        }

        /* ==========================================================================
           MÓDULO PROFESIONAL DE GESTIÓN DE USUARIOS Y ACCESOS (ADMINISTRADOR)
           Conectado a APIs Django / Base de Datos Municipal (SQLite & AWS Compatible)
           ========================================================================== */

