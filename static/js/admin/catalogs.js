/* Administrative catalogs. API success is an HTTP status, not a `success` flag. */
(() => {
    'use strict';
    const definitions = {
        'management-types': {
            title: 'tipo de gestión',
            icon: 'bi-kanban-fill',
            columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['status', 'Estado']],
            colWidths: ['16%', '28%', '32%', '10%', '14%']
        },
        items: {
            title: 'ítem',
            icon: 'bi-list-check',
            columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['item_type', 'Tipo'], ['status', 'Estado']],
            colWidths: ['14%', '24%', '28%', '11%', '9%', '14%']
        },
        goals: {
            title: 'meta',
            icon: 'bi-bullseye',
            columns: [['code', 'Código'], ['period', 'Período'], ['position', 'Cargo'], ['item', 'Ítem'], ['target_value', 'Objetivo'], ['unit_of_measure', 'Unidad'], ['weight', 'Pond.'], ['status', 'Estado']],
            colWidths: ['11%', '12%', '14%', '15%', '10%', '10%', '7%', '9%', '12%']
        },
        'attention-types': {
            title: 'tipo de atención',
            icon: 'bi-tags-fill',
            columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['status', 'Estado']],
            colWidths: ['16%', '28%', '32%', '10%', '14%']
        },
        subattentions: {
            title: 'subatención',
            icon: 'bi-tag-fill',
            columns: [['code', 'Código'], ['name', 'Nombre'], ['attention_type', 'Tipo de atención'], ['description', 'Descripción'], ['status', 'Estado']],
            colWidths: ['14%', '22%', '20%', '22%', '10%', '12%']
        }
    };
    const panels = [];
    const labels = { code: 'Código', name: 'Nombre', description: 'Descripción', status: 'Estado', item_type: 'Tipo de ítem', period: 'Período de medición', position: 'Cargo', item: 'Ítem', target_value: 'Valor objetivo', unit_of_measure: 'Unidad de medida', weight: 'Ponderación (%)', attention_type: 'Tipo de atención', __all__: 'Registro' };

    function element(tag, className, text, isHtml = false) {
        const node = document.createElement(tag);
        node.className = className || '';
        if (text !== undefined) {
            if (isHtml || (typeof text === 'string' && text.includes('<'))) {
                node.innerHTML = String(text);
            } else {
                node.textContent = String(text);
            }
        }
        return node;
    }
    function button(text, action, className = 'btn btn-outline-secondary btn-sm', isHtml = false) {
        const node = element('button', className, text, isHtml);
        node.type = 'button';
        node.addEventListener('click', action);
        return node;
    }
    function csrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input && input.value) return input.value;
        const cookie = document.cookie.split('; ').find(value => value.startsWith('csrftoken='));
        return cookie ? decodeURIComponent(cookie.slice(10)) : '';
    }
    function errorText(data, status) {
        let message = data.error || (status === 403 ? 'Acceso denegado o sesión vencida. Recargue la página e ingrese con una cuenta administradora.' : `No se pudo completar la solicitud (HTTP ${status}).`);
        if (data.details) {
            if (typeof data.details === 'object') {
                message += '\n' + Object.entries(data.details).map(([field, errors]) => {
                    const values = Array.isArray(errors) ? errors : [errors];
                    return `${labels[field] || field}: ${values.map(value => typeof value === 'object' ? value.message || JSON.stringify(value) : value).join(' ')}`;
                }).join('\n');
            } else message += '\n' + data.details;
        }
        return message;
    }
    async function request(url, method = 'GET', payload) {
        const headers = { Accept: 'application/json' };
        if (method !== 'GET') {
            const token = csrfToken();
            if (!token) throw new Error('No se encontró el token de seguridad. Recargue la página antes de guardar.');
            headers['X-CSRFToken'] = token;
        }
        if (payload !== undefined) headers['Content-Type'] = 'application/json';
        let response;
        try {
            response = await fetch(url, { method, headers, credentials: 'same-origin', body: payload === undefined ? undefined : JSON.stringify(payload) });
        } catch (_) {
            throw new Error('No se pudo contactar al servidor. Si estaba guardando, recargue el listado para verificar el resultado antes de reintentar.');
        }
        if (response.status === 204 && response.ok) return null;
        let data;
        try { data = await response.json(); } catch (_) {
            throw new Error(response.status === 403 ? errorText({}, 403) : 'El servidor no devolvió JSON válido. Recargue el listado para verificar el resultado y compruebe su sesión.');
        }
        if (!response.ok) throw new Error(errorText(data || {}, response.status));
        if (response.redirected) throw new Error('La sesión cambió. Recargue la página.');
        return data;
    }
    const endpoint = (catalog, id) => `/api/catalogs/${catalog}/${id === undefined ? '' : `${id}/`}`;
    async function all(catalog) {
        const rows = [];
        let page = 1;
        while (true) {
            const data = await request(`${endpoint(catalog)}?page=${page}&page_size=50`);
            if (!Array.isArray(data.results)) throw new Error('Respuesta de catálogo no válida.');
            rows.push(...data.results);
            if (rows.length >= data.count || !data.results.length) return rows;
            page += 1;
        }
    }
    async function references(catalog) {
        if (catalog === 'subattentions') return { attention_type: await all('attention-types') };
        if (catalog === 'goals') {
            const [items, positions, periods] = await Promise.all([all('items'), request('/organization/positions/'), request('/api/catalogs/periods/')]);
            if (!Array.isArray(positions.positions)) throw new Error('No se pudieron cargar los cargos.');
            if (!Array.isArray(periods.results)) throw new Error('No se pudieron cargar los períodos.');
            return { item: items, position: positions.positions, period: periods.results };
        }
        return {};
    }

    const prefixMap = {
        'goals': 'MET',
        'management-types': 'GES',
        'subattentions': 'SUB',
        'items': 'ITM',
        'attention-types': 'TIP'
    };

    function generateCode(catalog, existingRows = []) {
        const prefix = prefixMap[catalog] || 'CAT';
        let maxSeq = existingRows.length;
        existingRows.forEach(row => {
            if (row && row.code) {
                const nums = String(row.code).match(/\d+/g);
                if (nums && nums.length > 0) {
                    const n = parseInt(nums[0], 10);
                    if (!isNaN(n) && n > maxSeq) maxSeq = n;
                }
            }
        });
        const seq = String(maxSeq + 1).padStart(3, '0');
        const salt = Math.random().toString(36).substring(2, 5).toUpperCase();
        return `${prefix}-${seq}-${salt}`;
    }

    function notice(panel, message, error = false) {
        panel.message.className = `alert ${error ? 'alert-danger' : 'alert-success'} mt-3`;
        panel.message.textContent = message;
        panel.message.hidden = !message;
        if (error && window.Swal) {
            Swal.fire({
                icon: 'error',
                titleText: 'No se pudo completar la acción',
                text: message,
                confirmButtonColor: '#8B1D2C'
            });
        }
    }

    function panelQuery(panel, page, pageSize) {
        const query = new URLSearchParams({ page, page_size: pageSize, search: panel.search.value.trim() });
        if (panel.status.value) query.set('status', panel.status.value);
        if (panel.catalog === 'subattentions' && panel.attentionType.value) query.set('attention_type', panel.attentionType.value);
        if (panel.catalog === 'goals') {
            if (panel.position.value) query.set('position', panel.position.value);
            if (panel.item.value) query.set('item', panel.item.value);
        }
        return query;
    }

    function updateReferenceFilter(select, placeholder, rows, selected = '') {
        select.replaceChildren(new Option(placeholder, ''));
        rows.forEach(row => select.add(new Option(row.name, row.id)));
        if ([...select.options].some(option => option.value === selected)) select.value = selected;
    }

    function syncReferenceFilters(panel, refs) {
        if (panel.catalog === 'subattentions' && refs.attention_type) {
            const current = panel.attentionType.value;
            updateReferenceFilter(panel.attentionType, 'Todos los tipos', refs.attention_type, current);
        }
        if (panel.catalog === 'goals') {
            if (refs.position) updateReferenceFilter(panel.position, 'Todos los cargos', refs.position, panel.position.value);
            if (refs.item) updateReferenceFilter(panel.item, 'Todos los ítems', refs.item, panel.item.value);
        }
    }

    async function load(panel) {
        const revision = ++panel.revision;
        panel.previous.disabled = panel.next.disabled = true;
        panel.body.replaceChildren();
        const row = element('tr');
        const cell = element('td', 'p-3 text-muted', 'Cargando…');
        cell.colSpan = definitions[panel.catalog].columns.length + 1;
        row.append(cell);
        panel.body.append(row);
        panel.root.setAttribute('aria-busy', 'true');
        try {
            const query = panelQuery(panel, panel.page, panel.size.value);
            const [data, refs] = await Promise.all([request(`${endpoint(panel.catalog)}?${query}`), references(panel.catalog)]);
            if (revision !== panel.revision) return;
            if (!Array.isArray(data.results)) throw new Error('Respuesta de catálogo no válida.');
            const pages = Math.max(1, Math.ceil(data.count / Number(panel.size.value)));
            if (panel.page > pages) { panel.page = pages; return load(panel); }
            panel.lastResults = data.results;
            panel.refs = refs;
            syncReferenceFilters(panel, refs);
            panel.body.replaceChildren();
            data.results.forEach(record => {
                const tr = element('tr');
                tr.style.fontSize = '0.84rem';
                definitions[panel.catalog].columns.forEach(([key]) => {
                    const rawValue = record[key];
                    const value = refs[key] ? (refs[key].find(item => Number(item.id) === Number(rawValue))?.name || `ID ${rawValue}`) : rawValue;
                    const td = element('td', 'py-2.5 px-2');
                    if (key === 'code') {
                        td.innerHTML = `<span class="badge bg-light text-dark border font-monospace px-2 py-1" style="font-size: 0.78rem; letter-spacing: 0.5px; white-space: nowrap;">${record.code}</span>`;
                    } else if (key === 'status') {
                        td.className = 'py-2.5 px-2 text-center';
                        const isActivo = record.status === 'Activo';
                        td.innerHTML = `<span class="badge rounded-pill fw-bold border ${isActivo ? 'bg-success-subtle text-success border-success-subtle' : 'bg-secondary-subtle text-secondary border-secondary-subtle'}" style="font-size: 0.72rem; padding: 4px 8px;">${record.status}</span>`;
                    } else if (key === 'name') {
                        td.innerHTML = `<span class="fw-semibold text-dark d-block text-truncate" title="${value ?? ''}">${value ?? ''}</span>`;
                    } else if (key === 'description') {
                        td.innerHTML = `<span class="text-muted d-block text-truncate" style="font-size: 0.78rem;" title="${value || 'Sin descripción'}">${value || '—'}</span>`;
                    } else if (key === 'target_value' || key === 'weight') {
                        td.className = 'py-2.5 px-2 text-center';
                        td.innerHTML = `<span class="font-monospace fw-semibold" style="font-size: 0.80rem;">${value ?? '—'}</span>`;
                    } else {
                        td.innerHTML = `<span class="d-block text-truncate" title="${value ?? ''}">${value ?? ''}</span>`;
                    }
                    tr.append(td);
                });
                const actions = element('td', 'py-2.5 px-2 text-center text-nowrap');
                const actionsWrap = element('div', 'd-inline-flex align-items-center gap-1 justify-content-center');
                const view = button('Ver', () => viewRecord(panel, record.id), 'btn btn-sm btn-outline-secondary catalog-action-btn');
                view.setAttribute('aria-label', `Consultar ${record.name || record.code}`);
                view.title = 'Ver detalle';
                const edit = button('Editar', () => editRecord(panel, record.id), 'btn btn-sm btn-outline-primary catalog-action-btn');
                edit.setAttribute('aria-label', `Editar ${record.name || record.code}`);
                edit.title = 'Editar registro';
                const remove = button('Baja', () => deleteRecord(panel, record), 'btn btn-sm btn-outline-danger catalog-action-btn');
                remove.setAttribute('aria-label', `Eliminar ${record.name || record.code}`);
                remove.title = 'Dar de baja';
                actionsWrap.append(view, edit, remove);
                actions.append(actionsWrap);
                tr.append(actions);
                panel.body.append(tr);
            });
            if (!data.results.length) {
                cell.textContent = 'No hay registros para esta búsqueda.';
                panel.body.append(row);
            }
            panel.summary.textContent = `Mostrando ${data.results.length} de ${data.count} registros · Página ${panel.page} de ${pages}`;
            panel.previous.disabled = panel.page <= 1;
            panel.next.disabled = panel.page >= pages;
        } catch (error) {
            if (revision !== panel.revision) return;
            panel.body.replaceChildren();
            panel.summary.textContent = 'Listado no disponible';
            notice(panel, error.message + ' Use Recargar para reintentar.', true);
        } finally {
            if (revision === panel.revision) panel.root.setAttribute('aria-busy', 'false');
        }
    }

    function field(form, key, value, choices, isGrid = true) {
        const wrapClass = isGrid
            ? (key === 'description' ? 'col-12 mb-2' : 'col-12 col-md-6 mb-2')
            : 'mb-3';
        const wrap = element('div', wrapClass);
        const label = element('label', 'form-label small fw-bold', labels[key]);
        label.htmlFor = `catalog-field-${key}`;
        if (key === 'code') {
            const badge = element('span', 'badge bg-secondary ms-2', 'Bloqueado');
            badge.style.fontSize = '0.68rem';
            label.append(badge);
        }
        const input = element(choices ? 'select' : key === 'description' ? 'textarea' : 'input', choices ? 'form-select' : 'form-control');
        input.name = key;
        input.id = label.htmlFor;
        input.required = key !== 'description';
        if (key === 'code') {
            input.readOnly = true;
            input.className += ' swal-code-readonly';
            input.title = 'Código generado automáticamente por el sistema (inmutable)';
        }
        if (choices) {
            input.append(new Option('Seleccione…', ''));
            choices.forEach(choice => input.append(new Option(choice.name, choice.id)));
        } else if (['target_value', 'weight'].includes(key)) {
            input.type = 'number';
            input.min = '0.01';
            input.step = '0.01';
            if (key === 'weight') input.max = '100';
            if (key === 'target_value') input.max = '99999999.99';
        } else if (key !== 'description') {
            input.type = 'text';
            input.maxLength = key === 'name' ? 120 : 30;
        } else {
            input.rows = 2;
            input.maxLength = 500;
            input.setAttribute('maxlength', '500');
        }
        input.value = value ?? '';
        wrap.append(label, input);
        form.append(wrap);
    }

    async function viewRecord(panel, id) {
        try {
            const [record, refs] = await Promise.all([request(endpoint(panel.catalog, id)), references(panel.catalog)]);
            const details = element('dl', 'text-start m-0');
            definitions[panel.catalog].columns.forEach(([key, label]) => {
                const reference = refs[key]?.find(item => Number(item.id) === Number(record[key]));
                details.append(element('dt', 'small text-muted mt-2 fw-bold', label), element('dd', 'mb-2 text-dark', reference?.name || record[key] || 'Sin información'));
            });
            const def = definitions[panel.catalog];
            const iconClass = def?.icon || 'bi-info-circle-fill';
            const viewTitleHtml = `
                <div class="swal-muni-header-wrap">
                    <div class="swal-muni-icon-box">
                        <i class="bi ${iconClass}"></i>
                    </div>
                    <div class="swal-muni-title-box">
                        <h4 class="swal-muni-title">Consulta de ${def.title}</h4>
                        <p class="swal-muni-subtitle">Detalle del registro en catálogo institucional SGR La Serena</p>
                    </div>
                </div>
            `;
            await Swal.fire({
                title: viewTitleHtml,
                html: details,
                showCloseButton: true,
                customClass: {
                    popup: 'swal2-catalog-modal',
                    htmlContainer: 'swal2-catalog-container',
                    title: 'swal2-catalog-title',
                    confirmButton: 'btn btn-outline-muni-red rounded-pill px-4 py-2 fw-semibold',
                    actions: 'swal2-catalog-actions',
                    closeButton: 'swal2-catalog-close'
                },
                buttonsStyling: false,
                confirmButtonText: 'Cerrar'
            });
        } catch (error) { await Swal.fire({icon: 'error', titleText: 'No se pudo consultar', text: error.message, confirmButtonColor: '#8B1D2C'}); }
    }

    async function editRecord(panel, id) {
        if (panel.editing) return;
        panel.editing = true;
        try {
            const autoCode = id === undefined ? generateCode(panel.catalog, panel.lastResults || []) : '';
            const [record, refs] = await Promise.all([
                id === undefined
                    ? Promise.resolve({ code: autoCode, status: 'Activo', item_type: 'Cuantitativo', unit_of_measure: 'Atenciones' })
                    : request(endpoint(panel.catalog, id)),
                references(panel.catalog)
            ]);
            const isGoal = panel.catalog === 'goals';
            const form = element('form', 'text-start row g-2 swal-grid-form');
            form.noValidate = true;
            form.addEventListener('submit', event => { event.preventDefault(); Swal.clickConfirm(); });
            const choices = values => values.map(value => ({ id: value, name: value }));
            const fields = isGoal
                ? ['code', 'period', 'position', 'item', 'target_value', 'unit_of_measure', 'weight', 'status']
                : ['code', 'name', ...(panel.catalog === 'subattentions' ? ['attention_type'] : []), 'description', ...(panel.catalog === 'items' ? ['item_type'] : []), 'status'];
            fields.forEach(key => field(form, key, record[key], refs[key] || (key === 'status' ? choices(['Activo', 'Inactivo']) : key === 'item_type' ? choices(['Cuantitativo', 'Porcentual']) : undefined), true));
            let saving = false;
            const def = definitions[panel.catalog];
            const actionText = id === undefined ? 'Crear' : 'Editar';
            const catalogLabel = def.title;
            const fullTitle = `${actionText} ${catalogLabel}`;
            const iconClass = def?.icon || 'bi-tag-fill';
            const headerHtml = `
                <div class="swal-muni-header-wrap">
                    <div class="swal-muni-icon-box">
                        <i class="bi ${iconClass}"></i>
                    </div>
                    <div class="swal-muni-title-box">
                        <h4 class="swal-muni-title">${fullTitle}</h4>
                        <p class="swal-muni-subtitle">Catálogo oficial de gestión y atención ciudadana SGR La Serena</p>
                    </div>
                </div>
            `;
            const result = await Swal.fire({
                title: headerHtml,
                html: form,
                width: isGoal ? '820px' : '700px',
                showCloseButton: true,
                customClass: {
                    popup: 'swal2-catalog-modal',
                    htmlContainer: 'swal2-catalog-container',
                    title: 'swal2-catalog-title',
                    confirmButton: 'btn btn-muni-red rounded-pill px-4 py-2 fw-semibold',
                    cancelButton: 'btn btn-outline-muni-red rounded-pill px-4 py-2 fw-semibold',
                    actions: 'swal2-catalog-actions',
                    closeButton: 'swal2-catalog-close'
                },
                buttonsStyling: false,
                showCancelButton: true,
                confirmButtonText: '<i class="bi bi-database-check me-1"></i> Guardar',
                cancelButtonText: 'Cancelar',
                showLoaderOnConfirm: true,
                allowOutsideClick: () => !saving,
                allowEscapeKey: () => !saving,
                preConfirm: async () => {
                    if (saving) return false;
                    for (const input of form.elements) if (input.type === 'text') input.value = input.value.trim();
                    const invalid = [...form.elements].find(input => !input.checkValidity());
                    if (invalid) {
                        const label = invalid.labels?.[0]?.textContent?.trim() || labels[invalid.name] || 'dato requerido';
                        Swal.showValidationMessage(`Revisa ${label}: ${invalid.validationMessage}`);
                        invalid.focus();
                        return false;
                    }
                    saving = true;
                    Swal.getCancelButton().disabled = true;
                    try {
                        const payload = Object.fromEntries(new FormData(form));
                        await request(endpoint(panel.catalog, id), id === undefined ? 'POST' : 'PATCH', payload);
                        return true;
                    } catch (error) {
                        Swal.showValidationMessage(error.message);
                        return false;
                    } finally {
                        saving = false;
                        Swal.getCancelButton().disabled = false;
                    }
                }
            });
            if (result.isConfirmed) {
                notice(panel, 'Registro guardado en el servidor.');
                await refreshRelated(panel);
                Swal.fire({
                    icon: 'success',
                    titleText: 'Registro guardado',
                    text: 'El registro se guardó exitosamente en la base de datos.',
                    confirmButtonColor: '#C41230'
                });
            }
        } catch (error) { notice(panel, error.message, true); }
        finally { panel.editing = false; }
    }
    async function deleteRecord(panel, record) {
        if (panel.editing) return;
        panel.editing = true;
        try {
            let deleting = false;
            const result = await Swal.fire({
                title: `
                    <div class="swal-muni-header-wrap">
                        <div class="swal-muni-icon-box">
                            <i class="bi bi-exclamation-triangle-fill text-warning"></i>
                        </div>
                        <div class="swal-muni-title-box">
                            <h4 class="swal-muni-title">Confirmar baja de registro</h4>
                            <p class="swal-muni-subtitle">Esta acción modificará la disponibilidad en el catálogo</p>
                        </div>
                    </div>
                `,
                html: `<p class="my-3 text-secondary" style="font-size: 0.95rem;">¿Estás seguro de dar de baja <strong>${record.name || record.code}</strong>?</p>`,
                showCancelButton: true,
                confirmButtonText: '<i class="bi bi-trash3-fill me-1"></i> Dar de baja',
                cancelButtonText: 'Cancelar',
                customClass: {
                    popup: 'swal2-catalog-modal',
                    htmlContainer: 'swal2-catalog-container',
                    title: 'swal2-catalog-title',
                    confirmButton: 'btn btn-danger rounded-pill px-4 py-2 fw-semibold',
                    cancelButton: 'btn btn-outline-secondary rounded-pill px-4 py-2 fw-semibold',
                    actions: 'swal2-catalog-actions',
                    closeButton: 'swal2-catalog-close'
                },
                buttonsStyling: false,
                showLoaderOnConfirm: true,
                allowOutsideClick: () => !deleting,
                allowEscapeKey: () => !deleting,
                preConfirm: async () => {
                    if (deleting) return false;
                    deleting = true;
                    Swal.getCancelButton().disabled = true;
                    try {
                        await request(endpoint(panel.catalog, record.id), 'DELETE');
                        return true;
                    } catch (error) {
                        Swal.showValidationMessage('No se pudo dar de baja: ' + error.message);
                        return false;
                    } finally {
                        deleting = false;
                        Swal.getCancelButton().disabled = false;
                    }
                }
            });
            if (result.isConfirmed) {
                notice(panel, 'Registro dado de baja correctamente.');
                await refreshRelated(panel);
                Swal.fire({
                    title: `
                        <div class="swal-muni-header-wrap">
                            <div class="swal-muni-icon-box">
                                <i class="bi bi-check-circle-fill text-warning"></i>
                            </div>
                            <div class="swal-muni-title-box">
                                <h4 class="swal-muni-title">Registro dado de baja</h4>
                                <p class="swal-muni-subtitle">Catálogo institucional SGR La Serena</p>
                            </div>
                        </div>
                    `,
                    html: '<p class="my-3 text-success fw-semibold">El registro fue actualizado en la base de datos.</p>',
                    confirmButtonText: 'Aceptar',
                    customClass: {
                        popup: 'swal2-catalog-modal',
                        htmlContainer: 'swal2-catalog-container',
                        title: 'swal2-catalog-title',
                        confirmButton: 'btn btn-muni-red rounded-pill px-4 py-2 fw-semibold',
                        actions: 'swal2-catalog-actions'
                    },
                    buttonsStyling: false
                });
            }
        } catch (error) { notice(panel, error.message, true); }
        finally { panel.editing = false; }
    }
    async function exportPanel(panel) {
        if (panel.exporting) return;
        if (!window.XLSX) { notice(panel, 'La herramienta de Excel no está disponible. Recarga el panel e inténtalo de nuevo.', true); return; }
        panel.exporting = true;
        panel.exportButton.disabled = true;
        notice(panel, 'Preparando el Excel con todas las páginas que cumplen los filtros…');
        try {
            const rows = [];
            const filterSnapshot = panelQuery(panel, 1, 100);
            let page = 1;
            let count = 0;
            do {
                filterSnapshot.set('page', page);
                const data = await request(`${endpoint(panel.catalog)}?${filterSnapshot}`);
                if (!Array.isArray(data.results)) throw new Error('La respuesta del listado no es válida.');
                if (!data.results.length && rows.length < data.count) throw new Error('El listado cambió durante la exportación. Recarga y vuelve a intentar.');
                count = data.count;
                data.results.forEach(record => {
                    const row = {};
                    definitions[panel.catalog].columns.forEach(([key, label]) => {
                        const reference = panel.refs?.[key]?.find(item => Number(item.id) === Number(record[key]));
                        row[label] = reference ? reference.name : (record[key] ?? '');
                    });
                    rows.push(row);
                });
                page += 1;
            } while (rows.length < count);
            if (!rows.length) { notice(panel, 'No hay registros que coincidan con los filtros.', true); return; }
            const worksheet = XLSX.utils.json_to_sheet(rows);
            const workbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(workbook, worksheet, definitions[panel.catalog].title.slice(0, 31));
            const date = new Date().toISOString().slice(0, 10);
            XLSX.writeFile(workbook, `${panel.catalog.replace(/[^a-z0-9-]/gi, '_')}_${date}.xlsx`);
            notice(panel, `Excel descargado: ${rows.length} registro(s), aplicando los filtros actuales.`);
        } catch (error) {
            notice(panel, `No se pudo exportar: ${error.message}`, true);
        } finally {
            panel.exporting = false;
            panel.exportButton.disabled = false;
        }
    }
    async function refreshRelated(panel) {
        const related = panels.filter(other => other === panel || (panel.catalog === 'items' && other.catalog === 'goals') || (panel.catalog === 'attention-types' && other.catalog === 'subattentions'));
        await Promise.all(related.map(other => load(other)));
    }
    function init() {
        document.querySelectorAll('[data-catalog]').forEach(root => {
            if (root.dataset.catalogReady === 'true') return;
            root.dataset.catalogReady = 'true';
            const catalog = root.dataset.catalog;
            if (!definitions[catalog]) return;
            const panel = { root, catalog, page: 1, revision: 0, editing: false };

            const toolbar = element('div', 'd-flex justify-content-between align-items-center flex-wrap gap-2 mb-3');
            const filterGroup = element('div', 'd-flex align-items-center flex-wrap gap-2 flex-grow-1');
            const actionGroup = element('div', 'd-flex align-items-center gap-2');

            panel.search = element('input', 'form-control rounded-pill');
            panel.search.style.minWidth = '240px';
            panel.search.style.maxWidth = '340px';
            panel.search.type = 'search';
            panel.search.placeholder = 'Buscar por código o nombre...';
            panel.search.maxLength = 150;
            panel.search.setAttribute('aria-label', `Buscar ${definitions[catalog].title}`);

            panel.status = element('select', 'form-select rounded-pill w-auto');
            panel.status.setAttribute('aria-label', 'Filtrar por estado');
            [['', 'Todos los estados'], ['Activo', 'Activo'], ['Inactivo', 'Inactivo']].forEach(([value, label]) => panel.status.add(new Option(label, value)));

            panel.size = element('select', 'form-select rounded-pill w-auto');
            panel.size.setAttribute('aria-label', 'Registros por página');
            [10, 20, 30, 40, 50].forEach(size => panel.size.append(new Option(`${size} por página`, size)));

            const filterChanged = () => { panel.page = 1; notice(panel, ''); load(panel); };
            if (catalog === 'subattentions') {
                panel.attentionType = element('select', 'form-select rounded-pill w-auto');
                panel.attentionType.setAttribute('aria-label', 'Filtrar por tipo de atención');
                panel.attentionType.append(new Option('Todos los tipos', ''));
                panel.attentionType.addEventListener('change', filterChanged);
                filterGroup.append(panel.attentionType);
            }
            if (catalog === 'goals') {
                panel.position = element('select', 'form-select rounded-pill w-auto');
                panel.item = element('select', 'form-select rounded-pill w-auto');
                panel.position.setAttribute('aria-label', 'Filtrar por cargo');
                panel.item.setAttribute('aria-label', 'Filtrar por ítem');
                panel.position.append(new Option('Todos los cargos', ''));
                panel.item.append(new Option('Todos los ítems', ''));
                panel.position.addEventListener('change', filterChanged);
                panel.item.addEventListener('change', filterChanged);
                filterGroup.append(panel.position, panel.item);
            }

            let timer;
            panel.search.addEventListener('input', () => {
                panel.revision += 1;
                panel.previous.disabled = panel.next.disabled = true;
                clearTimeout(timer);
                timer = setTimeout(() => { panel.page = 1; notice(panel, ''); load(panel); }, 300);
            });
            panel.size.addEventListener('change', filterChanged);
            panel.status.addEventListener('change', filterChanged);

            filterGroup.prepend(panel.search, panel.status);
            filterGroup.append(panel.size);

            panel.exportButton = button('<i class="bi bi-file-earmark-excel me-1 text-success"></i> Exportar a Excel', () => exportPanel(panel), 'btn btn-outline-secondary rounded-pill px-3 py-1 fw-bold small');
            const reloadBtn = button('<i class="bi bi-arrow-clockwise me-1"></i> Recargar', () => { notice(panel, ''); load(panel); }, 'btn btn-outline-secondary rounded-pill px-3 py-1 fw-bold small');
            const createBtn = button('<i class="bi bi-plus-lg me-1"></i> Crear ' + definitions[catalog].title, () => editRecord(panel), 'liquid-glass-btn-primary');

            actionGroup.append(panel.exportButton, reloadBtn, createBtn);
            toolbar.append(filterGroup, actionGroup);

            panel.message = element('div');
            panel.message.hidden = true;
            panel.message.style.whiteSpace = 'pre-line';
            panel.message.setAttribute('role', 'status');

            const wrapper = element('div', 'table-responsive rounded-4 border bg-white shadow-sm mb-3');
            wrapper.style.overflowX = 'auto';
            const table = element('table', 'table align-middle m-0 catalog-fixed-table');
            table.setAttribute('aria-label', `Catálogo de ${definitions[catalog].title}`);
            table.style.tableLayout = 'fixed';
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';

            const colgroup = element('colgroup');
            const colWidths = definitions[catalog].colWidths || [];
            colWidths.forEach(width => {
                const col = element('col');
                col.style.width = width;
                colgroup.append(col);
            });
            table.append(colgroup);

            const head = element('thead');
            head.style.background = 'rgba(241, 245, 249, 0.95)';
            head.style.borderBottom = '2px solid #CBD5E1';
            const heading = element('tr');
            heading.style.fontSize = '0.76rem';
            heading.style.fontWeight = '800';
            heading.style.color = '#1E293B';
            heading.style.textTransform = 'uppercase';
            heading.style.letterSpacing = '0.03em';

            [...definitions[catalog].columns.map(([, label]) => label), 'Acciones'].forEach(label => {
                const isCenter = ['Estado', 'Acciones', 'Pond.'].includes(label);
                const th = element('th', `py-2.5 px-2 ${isCenter ? 'text-center' : ''}`, label);
                th.scope = 'col';
                heading.append(th);
            });
            head.append(heading);

            panel.body = element('tbody');
            table.append(head, panel.body);
            wrapper.append(table);

            const pagination = element('div', 'd-flex justify-content-between align-items-center flex-wrap gap-2 mt-3 pt-2 border-top');
            panel.summary = element('span', 'text-muted small');
            panel.summary.setAttribute('aria-live', 'polite');
            const pageGroup = element('div', 'btn-group');
            pageGroup.setAttribute('aria-label', 'Páginas');
            panel.previous = button('Anterior', () => { panel.page -= 1; load(panel); }, 'btn btn-outline-secondary btn-sm');
            panel.next = button('Siguiente', () => { panel.page += 1; load(panel); }, 'btn btn-outline-secondary btn-sm');
            pageGroup.append(panel.previous, panel.next);
            pagination.append(panel.summary, pageGroup);

            root.replaceChildren(toolbar, panel.message, wrapper, pagination);
            panels.push(panel);
            load(panel);
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
