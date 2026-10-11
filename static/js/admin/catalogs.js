/* Administrative catalogs. API success is an HTTP status, not a `success` flag. */
(() => {
    'use strict';
    const definitions = {
        'management-types': { title: 'tipo de gestión', columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['status', 'Estado']] },
        items: { title: 'ítem', columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['item_type', 'Tipo'], ['status', 'Estado']] },
        goals: { title: 'meta', columns: [['code', 'Código'], ['period', 'Período'], ['position', 'Cargo'], ['item', 'Ítem'], ['target_value', 'Objetivo'], ['unit_of_measure', 'Unidad'], ['weight', 'Ponderación (%)'], ['status', 'Estado']] },
        'attention-types': { title: 'tipo de atención', columns: [['code', 'Código'], ['name', 'Nombre'], ['description', 'Descripción'], ['status', 'Estado']] },
        subattentions: { title: 'subatención', columns: [['code', 'Código'], ['name', 'Nombre'], ['attention_type', 'Tipo de atención'], ['description', 'Descripción'], ['status', 'Estado']] }
    };
    const panels = [];
    const labels = { code: 'Código', name: 'Nombre', description: 'Descripción', status: 'Estado', item_type: 'Tipo de ítem', period: 'Período de medición', position: 'Cargo', item: 'Ítem', target_value: 'Valor objetivo', unit_of_measure: 'Unidad de medida', weight: 'Ponderación (%)', attention_type: 'Tipo de atención', __all__: 'Registro' };

    function element(tag, className, text) {
        const node = document.createElement(tag);
        node.className = className || '';
        if (text !== undefined) node.textContent = String(text);
        return node;
    }
    function button(text, action, className = 'btn btn-outline-secondary rounded-pill') {
        const node = element('button', className, text);
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
            const data = await request(`${endpoint(catalog)}?page=${page}&page_size=100`);
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
    function notice(panel, message, error = false) {
        panel.message.className = `alert ${error ? 'alert-danger' : 'alert-success'} mt-3`;
        panel.message.textContent = message;
        panel.message.hidden = !message;
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
            panel.refs = refs;
            syncReferenceFilters(panel, refs);
            panel.body.replaceChildren();
            data.results.forEach(record => {
                const tr = element('tr');
                definitions[panel.catalog].columns.forEach(([key]) => {
                    const value = refs[key] ? (refs[key].find(item => Number(item.id) === Number(record[key]))?.name || `ID ${record[key]}`) : record[key];
                    tr.append(element('td', 'py-3 px-3', value ?? ''));
                });
                const actions = element('td', 'py-3 px-3 text-end text-nowrap');
                const edit = button('Editar', () => editRecord(panel, record.id), 'btn btn-sm btn-outline-secondary rounded-pill me-2');
                const remove = button('Eliminar', () => deleteRecord(panel, record), 'btn btn-sm btn-outline-danger rounded-pill');
                edit.setAttribute('aria-label', `Editar ${record.name || record.code}`);
                remove.setAttribute('aria-label', `Eliminar ${record.name || record.code}`);
                actions.append(edit, remove);
                tr.append(actions);
                panel.body.append(tr);
            });
            if (!data.results.length) {
                cell.textContent = 'No hay registros para esta búsqueda.';
                panel.body.append(row);
            }
            panel.summary.textContent = `${data.count} registros · Página ${panel.page} de ${pages}`;
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
    function field(form, key, value, choices) {
        const wrap = element('div', 'mb-3');
        const label = element('label', 'form-label small fw-bold', labels[key]);
        label.htmlFor = `catalog-field-${key}`;
        const input = element(choices ? 'select' : key === 'description' ? 'textarea' : 'input', choices ? 'form-select' : 'form-control');
        input.name = key;
        input.id = label.htmlFor;
        input.required = key !== 'description';
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
        } else input.rows = 3;
        input.value = value ?? '';
        wrap.append(label, input);
        form.append(wrap);
    }
    async function editRecord(panel, id) {
        if (panel.editing) return;
        panel.editing = true;
        try {
            const [record, refs] = await Promise.all([id === undefined ? Promise.resolve({ status: 'Activo', item_type: 'Cuantitativo', unit_of_measure: 'Atenciones' }) : request(endpoint(panel.catalog, id)), references(panel.catalog)]);
            const form = element('form', 'text-start');
            form.addEventListener('submit', event => { event.preventDefault(); Swal.clickConfirm(); });
            const choices = values => values.map(value => ({ id: value, name: value }));
            const fields = panel.catalog === 'goals' ? ['code', 'period', 'position', 'item', 'target_value', 'unit_of_measure', 'weight', 'status'] : ['code', 'name', ...(panel.catalog === 'subattentions' ? ['attention_type'] : []), 'description', ...(panel.catalog === 'items' ? ['item_type'] : []), 'status'];
            fields.forEach(key => field(form, key, record[key], refs[key] || (key === 'status' ? choices(['Activo', 'Inactivo']) : key === 'item_type' ? choices(['Cuantitativo', 'Porcentual']) : undefined)));
            const errors = element('div', 'alert alert-danger');
            errors.style.whiteSpace = 'pre-line';
            errors.setAttribute('role', 'alert');
            errors.hidden = true;
            form.append(errors);
            let saving = false;
            const result = await Swal.fire({
                titleText: `${id === undefined ? 'Crear' : 'Editar'} ${definitions[panel.catalog].title}`,
                html: form, showCancelButton: true, confirmButtonText: 'Guardar', cancelButtonText: 'Cancelar', confirmButtonColor: '#1B365D', showLoaderOnConfirm: true,
                allowOutsideClick: () => !saving, allowEscapeKey: () => !saving,
                preConfirm: async () => {
                    if (saving) return false;
                    for (const input of form.elements) if (input.type === 'text') input.value = input.value.trim();
                    if (!form.reportValidity()) return false;
                    saving = true;
                    Swal.getCancelButton().disabled = true;
                    errors.hidden = true;
                    try {
                        const payload = Object.fromEntries(new FormData(form));
                        await request(endpoint(panel.catalog, id), id === undefined ? 'POST' : 'PATCH', payload);
                        return true;
                    } catch (error) {
                        errors.textContent = error.message;
                        errors.hidden = false;
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
                titleText: 'Eliminar registro', text: `¿Eliminar ${record.name || record.code}?`, icon: 'warning',
                showCancelButton: true, confirmButtonText: 'Eliminar', cancelButtonText: 'Cancelar', confirmButtonColor: '#C41230', showLoaderOnConfirm: true,
                allowOutsideClick: () => !deleting, allowEscapeKey: () => !deleting,
                preConfirm: async () => {
                    if (deleting) return false;
                    deleting = true;
                    Swal.getCancelButton().disabled = true;
                    try { await request(endpoint(panel.catalog, record.id), 'DELETE'); return true; }
                    catch (error) {
                        // SweetAlert validation accepts HTML; insert server messages as text only.
                        Swal.showValidationMessage('No se pudo eliminar.');
                        Swal.getValidationMessage().textContent = error.message;
                        return false;
                    } finally { deleting = false; Swal.getCancelButton().disabled = false; }
                }
            });
            if (result.isConfirmed) {
                notice(panel, 'Registro eliminado en el servidor.');
                await refreshRelated(panel);
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
            let page = 1;
            let count = 0;
            do {
                const data = await request(`${endpoint(panel.catalog)}?${panelQuery(panel, page, 100)}`);
                if (!Array.isArray(data.results)) throw new Error('La respuesta del listado no es válida.');
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
            const catalog = root.dataset.catalog;
            if (!definitions[catalog]) return;
            const panel = { root, catalog, page: 1, revision: 0, editing: false };
            const toolbar = element('div', 'd-flex align-items-center flex-wrap gap-2 my-3');
            panel.search = element('input', 'form-control rounded-pill w-auto');
            panel.search.type = 'search';
            panel.search.placeholder = 'Buscar por código, nombre o descripción';
            panel.search.maxLength = 150;
            panel.search.setAttribute('aria-label', `Buscar ${definitions[catalog].title} por código, nombre o descripción`);
            panel.status = element('select', 'form-select rounded-pill w-auto');
            panel.status.setAttribute('aria-label', 'Filtrar por estado');
            [['', 'Todos los estados'], ['Activo', 'Activo'], ['Inactivo', 'Inactivo']].forEach(([value, label]) => panel.status.add(new Option(label, value)));
            panel.size = element('select', 'form-select rounded-pill w-auto');
            panel.size.setAttribute('aria-label', 'Registros por página');
            [10, 20, 50].forEach(size => panel.size.append(new Option(`${size} por página`, size)));
            const filterChanged = () => { panel.page = 1; notice(panel, ''); load(panel); };
            if (catalog === 'subattentions') {
                panel.attentionType = element('select', 'form-select rounded-pill w-auto');
                panel.attentionType.setAttribute('aria-label', 'Filtrar por tipo de atención');
                panel.attentionType.append(new Option('Todos los tipos', ''));
                panel.attentionType.addEventListener('change', filterChanged);
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
            }
            let timer;
            panel.search.addEventListener('input', () => {
                // Immediately invalidate older responses during debounce.
                panel.revision += 1;
                panel.previous.disabled = panel.next.disabled = true;
                clearTimeout(timer);
                timer = setTimeout(() => { panel.page = 1; notice(panel, ''); load(panel); }, 300);
            });
            panel.size.addEventListener('change', filterChanged);
            panel.status.addEventListener('change', filterChanged);
            toolbar.append(panel.search, panel.status);
            if (panel.attentionType) toolbar.append(panel.attentionType);
            if (panel.position) toolbar.append(panel.position, panel.item);
            panel.exportButton = button('Exportar a Excel', () => exportPanel(panel), 'btn btn-outline-success rounded-pill');
            toolbar.append(panel.size, panel.exportButton, button('Recargar', () => { notice(panel, ''); load(panel); }), button(`Crear ${definitions[catalog].title}`, () => editRecord(panel), 'btn btn-primary rounded-pill'));
            panel.message = element('div');
            panel.message.hidden = true;
            panel.message.style.whiteSpace = 'pre-line';
            panel.message.setAttribute('role', 'status');
            const wrapper = element('div', 'table-responsive rounded-4 border bg-white shadow-sm');
            const table = element('table', 'table align-middle m-0');
            table.setAttribute('aria-label', `Catálogo de ${definitions[catalog].title}`);
            const head = element('thead', 'table-light');
            const heading = element('tr');
            [...definitions[catalog].columns.map(([, label]) => label), 'Acciones'].forEach(label => {
                const th = element('th', 'py-3 px-3', label);
                th.scope = 'col';
                heading.append(th);
            });
            head.append(heading);
            panel.body = element('tbody');
            table.append(head, panel.body);
            wrapper.append(table);
            const pagination = element('div', 'd-flex align-items-center flex-wrap gap-3 mt-3');
            panel.summary = element('span', 'text-muted small');
            panel.summary.setAttribute('aria-live', 'polite');
            panel.previous = button('Anterior', () => { panel.page -= 1; load(panel); });
            panel.next = button('Siguiente', () => { panel.page += 1; load(panel); });
            pagination.append(panel.summary, panel.previous, panel.next);
            root.replaceChildren(toolbar, panel.message, wrapper, pagination);
            panels.push(panel);
            load(panel);
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
