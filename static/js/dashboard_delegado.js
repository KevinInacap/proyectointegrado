(() => {
  'use strict';

  const app = document.getElementById('delegado-app');
  if (!app) return;

  const form = document.getElementById('delegado-attention-form');
  const modalNode = document.getElementById('attentionModal');
  const type = document.getElementById('field-type');
  const subtype = document.getElementById('field-subtype');
  const save = document.getElementById('delegado-save');
  const date = document.getElementById('field-date');
  const summary = document.getElementById('form-error-summary');
  const announcement = document.getElementById('delegado-announcement');
  const menuButton = document.querySelector('.mobile-menu');
  const sidebar = document.getElementById('delegado-sidebar');
  const sidebarBackdrop = document.getElementById('sidebar-backdrop');
  const neighborSelect = document.getElementById('field-neighbor');
  const neighborSearch = document.getElementById('neighbor-search');
  const neighborLookup = document.getElementById('neighbor-rut-lookup');
  const initialNeighbor = JSON.parse(document.getElementById('delegado-selected-neighbor')?.textContent || 'null');
  let selectedNeighbor = null;
  let neighborSearchVersion = 0;
  let applicantMode = 'pending';
  let resolvedRut = '';
  let previousContact = null;
  let createCode = '';
  const statusLabels = {
    Pending: 'Pendiente', Approved: 'Aprobada', Rejected: 'Rechazada',
    'Requires correction': 'Requiere corrección',
  };
  let editingId = null;
  let legacyType = false;
  let saving = false;
  let allowModalClose = false;
  let initialSnapshot = '';

  const announce = message => { if (announcement) announcement.textContent = message; };
  const createElement = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = String(text ?? '');
    if (className) element.className = className;
    return element;
  };

  // SweetAlert remains inside the Bootstrap modal while editing, so both
  // dialogs share the same focus boundary. The fallback keeps actions usable
  // when the external alert library cannot be downloaded.
  const popup = options => {
    if (window.Swal) {
      return window.Swal.fire({
        confirmButtonColor: getComputedStyle(app).getPropertyValue('--crimson').trim() || '#c41230', cancelButtonColor: '#6b5e61',
        confirmButtonText: 'Entendido', cancelButtonText: 'Cancelar',
        reverseButtons: true, heightAuto: false,
        target: document.querySelector('#attentionModal.show, #neighborModal.show') || document.body,
        ...options,
      });
    }
    return new Promise(resolve => {
      const dialog = createElement('dialog', undefined, 'delegado-native-dialog');
      const heading = createElement('h2', options.titleText || options.title || 'Información');
      heading.id = 'delegado-native-dialog-title';
      dialog.setAttribute('aria-labelledby', heading.id);
      dialog.append(heading);
      if (options.text) dialog.append(createElement('p', options.text));
      if (options.html instanceof HTMLElement) dialog.append(options.html);
      const actions = createElement('div', undefined, 'native-dialog-actions');
      const confirm = createElement('button', options.confirmButtonText || 'Entendido', 'delegado-primary');
      confirm.type = 'button';
      let confirmed = false;
      confirm.addEventListener('click', () => { confirmed = true; dialog.close(); });
      if (options.showCancelButton) {
        const cancel = createElement('button', options.cancelButtonText || 'Cancelar', 'delegado-secondary');
        cancel.type = 'button';
        cancel.addEventListener('click', () => dialog.close());
        actions.append(cancel);
      }
      actions.append(confirm);
      dialog.append(actions);
      (document.querySelector('#attentionModal.show, #neighborModal.show') || document.body).append(dialog);
      dialog.addEventListener('close', () => {
        dialog.remove();
        resolve({ isConfirmed: confirmed, isDismissed: !confirmed });
      }, { once: true });
      dialog.showModal();
      if (options.showCancelButton) actions.firstElementChild.focus();
    });
  };
  const notify = (icon, title, text) => popup({ icon, title, text });
  const detailUrl = id => `${app.dataset.detailBase}${encodeURIComponent(id)}/`;
  const csrf = () => document.querySelector('#delegado-csrf [name=csrfmiddlewaretoken], #delegado-attention-form [name=csrfmiddlewaretoken], #delegado-neighbor-form [name=csrfmiddlewaretoken]')?.value || '';

  const request = async (url, options = {}) => {
    let response;
    try {
      response = await fetch(url, {
        credentials: 'same-origin', ...options,
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), ...options.headers },
      });
    } catch {
      throw new Error('No pudimos conectar con el servidor. Comprueba tu conexión. Si estabas guardando, revisa el listado antes de volver a intentarlo.');
    }
    let data;
    try { data = await response.json(); }
    catch {
      if (response.status === 403) throw new Error('La sesión o el permiso no permiten esta operación. Actualiza la página y vuelve a intentarlo.');
      throw new Error('No se recibió una respuesta válida. Tu sesión puede haber finalizado; actualiza la página para comprobarlo.');
    }
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      throw new Error('El servidor devolvió una respuesta inesperada. Actualiza la página antes de volver a intentarlo.');
    }
    if (!response.ok || !data.success) throw new Error(typeof data.message === 'string' && data.message ? data.message : 'La operación no pudo completarse.');
    return data;
  };

  const setMenu = (open, restoreFocus = false) => {
    app.classList.toggle('menu-open', open);
    menuButton?.setAttribute('aria-expanded', String(open));
    if (sidebarBackdrop) sidebarBackdrop.hidden = !open;
    if (!open) document.body.style.overflow = '';
    if (window.matchMedia('(max-width: 760px)').matches) {
      document.body.style.overflow = open ? 'hidden' : '';
      if (open) sidebar.querySelector('a,button')?.focus();
      else if (restoreFocus) menuButton?.focus();
    }
  };
  menuButton?.addEventListener('click', () => setMenu(!app.classList.contains('menu-open')));
  document.querySelector('.sidebar-close')?.addEventListener('click', () => setMenu(false, true));
  sidebarBackdrop?.addEventListener('click', () => setMenu(false, true));
  document.addEventListener('keydown', event => {
    if (!app.classList.contains('menu-open')) return;
    if (event.key === 'Escape') { event.preventDefault(); setMenu(false, true); }
    if (event.key === 'Tab' && window.matchMedia('(max-width: 760px)').matches) {
      const targets = Array.from(sidebar.querySelectorAll('a[href],button:not([disabled])')).filter(element => element.getClientRects().length);
      const first = targets[0];
      const last = targets[targets.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
  });
  window.matchMedia('(max-width: 760px)').addEventListener('change', () => setMenu(false));

  const navLinks = [...document.querySelectorAll('.primary-nav .nav-link')];
  navLinks.forEach(link => link.addEventListener('click', () => setMenu(false)));

  const validRut = value => {
    const clean = value.replace(/[.\s-]/g, '').toUpperCase();
    if (!/^\d+[\dK]$/.test(clean)) return false;
    let sum = 0, factor = 2;
    for (const digit of clean.slice(0, -1).split('').reverse()) {
      sum += Number(digit) * factor;
      factor = factor === 7 ? 2 : factor + 1;
    }
    const result = 11 - sum % 11;
    return clean.slice(-1) === (result === 11 ? '0' : result === 10 ? 'K' : String(result));
  };
  const normalizeRut = value => String(value || '').replace(/[.\s-]/g, '').toUpperCase();
  const neighborMode = () => applicantMode;
  const syncNeighborMode = (mode = 'pending') => {
    if (!form) return;
    applicantMode = mode;
    document.getElementById('neighbor-registration').hidden = mode !== 'new';
    form.elements.contact_name.readOnly = mode !== 'new';
    form.elements.contact_phone.readOnly = mode !== 'new';
    for (const name of ['neighbor_rut', 'neighbor_address', 'neighbor_email']) form.elements[name].disabled = mode !== 'new';
    document.getElementById('neighbor-mode-help').textContent = mode === 'new'
      ? 'Este RUT no está en el padrón de tu delegación. Completa nombre y dirección; al guardar se registrarán el vecino y su atención juntos.'
      : mode === 'existing' ? 'Vecino identificado. Completa la atención; sus datos personales se mantienen desde su ficha en Vecinos.'
      : mode === 'blocked' ? 'El vecino está inactivo. Revisa o reactiva su ficha en Vecinos antes de registrar la atención.'
      : 'Consulta primero el RUT. Si no está registrado se habilitará su ficha, sin perder la atención que estás completando.';
    save.disabled = saving || !['existing', 'new'].includes(mode);
    const link = document.getElementById('neighbor-record-link');
    link.hidden = !selectedNeighbor;
    if (selectedNeighbor) {
      const url = new URL(app.dataset.neighborPageUrl, location.origin);
      url.searchParams.set('q', selectedNeighbor.rut);
      link.href = url.href;
    }
  };
  const selectNeighbor = neighbor => {
    selectedNeighbor = neighbor || null;
    neighborSelect.value = neighbor ? String(neighbor.id) : '';
    form.elements.contact_name.value = neighbor?.nombre || '';
    form.elements.contact_phone.value = neighbor?.telefono || '';
    resolvedRut = normalizeRut(neighbor?.rut);
    if (neighbor) neighborSearch.value = neighbor.rut;
    syncNeighborMode(neighbor ? (neighbor.estado === 'Activo' ? 'existing' : 'blocked') : 'pending');
    document.getElementById('neighbor-search-status').textContent = neighbor
      ? `${neighbor.nombre} · ${neighbor.rut} · ${neighbor.estado === 'Activo' ? 'Vecino registrado' : 'Ficha inactiva'}`
      : 'Ingresa el RUT para buscar al vecino antes de completar la atención.';
  };
  const loadNeighbors = async () => {
    if (!form || saving || neighborLookup.disabled) return;
    const rut = neighborSearch.value.trim();
    if (!validRut(rut)) {
      fieldError('neighbor', 'Ingresa un RUT válido y revisa su dígito verificador.');
      neighborSearch.focus();
      return;
    }
    const restorePreviousContact = previousContact && neighborMode() !== 'new';
    clearErrors();
    const version = ++neighborSearchVersion;
    const status = document.getElementById('neighbor-search-status');
    status.textContent = 'Consultando el RUT en el padrón de tu delegación…';
    neighborLookup.disabled = true;
    neighborLookup.textContent = 'Consultando…';
    save.disabled = true;
    const url = new URL(app.dataset.neighborsUrl, location.origin);
    url.searchParams.set('rut', rut);
    try {
      const data = await request(url);
      if (version !== neighborSearchVersion) return;
      const neighbor = data.paginated_vecinos.find(item => normalizeRut(item.rut) === normalizeRut(rut));
      if (neighbor) selectNeighbor(neighbor);
      else {
        selectedNeighbor = null;
        neighborSelect.value = '';
        resolvedRut = normalizeRut(rut);
        form.elements.neighbor_rut.value = rut;
        syncNeighborMode('new');
        if (restorePreviousContact) {
          form.elements.contact_name.value = previousContact.name;
          form.elements.contact_phone.value = previousContact.phone;
        }
        status.textContent = 'RUT sin ficha en tu delegación. Completa la ficha del nuevo vecino a continuación.';
        form.elements.contact_name.focus();
      }
    } catch (error) {
      if (version === neighborSearchVersion) { syncNeighborMode('pending'); status.textContent = error.message; }
    } finally {
      if (version === neighborSearchVersion) {
        neighborLookup.disabled = false;
        neighborLookup.textContent = 'Consultar RUT';
      }
    }
  };
  neighborLookup?.addEventListener('click', loadNeighbors);
  neighborSearch?.addEventListener('input', () => {
    if (resolvedRut && normalizeRut(neighborSearch.value) === resolvedRut && ['existing', 'new', 'blocked'].includes(neighborMode())) return;
    ++neighborSearchVersion;
    selectNeighbor(null);
    form.elements.neighbor_rut.value = '';
    form.elements.neighbor_address.value = '';
    form.elements.neighbor_email.value = '';
    neighborLookup.disabled = false;
    neighborLookup.textContent = 'Consultar RUT';
  });
  neighborSearch?.addEventListener('change', () => { if (validRut(neighborSearch.value.trim())) loadNeighbors(); });
  neighborSearch?.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); loadNeighbors(); } });

  const refreshSubtypes = () => {
    if (!type || !subtype) return;
    let visible = 0;
    for (const option of subtype.options) {
      if (!option.value) continue;
      option.hidden = option.dataset.type !== type.value;
      option.disabled = option.hidden;
      if (!option.hidden) visible += 1;
    }
    if (!Array.from(subtype.options).some(option => option.value === subtype.value && !option.hidden && !option.disabled)) subtype.value = '';
    subtype.options[0].textContent = type.value ? (visible ? 'Selecciona una subatención' : 'No hay subatenciones activas') : 'Selecciona primero el tipo';
  };
  type?.addEventListener('change', refreshSubtypes);
  const fieldMap = { neighbor: 'neighbor-search', rut: 'field-rut', address: 'field-address', email: 'field-email', contact: 'field-contact', phone: 'field-phone', date: 'field-date', type: 'field-type', subtype: 'field-subtype', problem: 'field-problem', action: 'field-action' };
  const clearErrors = () => {
    if (summary) { summary.hidden = true; summary.textContent = ''; }
    Object.keys(fieldMap).forEach(key => {
      const field = document.getElementById(fieldMap[key]);
      field?.removeAttribute('aria-invalid');
      field?.classList.remove('is-invalid');
      const error = document.getElementById(`error-${key}`);
      if (error) error.textContent = '';
    });
  };
  const fieldError = (key, message) => {
    const field = document.getElementById(fieldMap[key]);
    field?.setAttribute('aria-invalid', 'true');
    field?.classList.add('is-invalid');
    const error = document.getElementById(`error-${key}`);
    if (error) error.textContent = message;
  };
  const showSummary = message => {
    if (summary) { summary.hidden = false; summary.textContent = message; }
    announce(message);
  };
  const snapshot = () => form ? JSON.stringify([...form.elements].filter(element => element.name && element.name !== 'csrfmiddlewaretoken').map(element => [element.name, ['checkbox', 'radio'].includes(element.type) ? element.checked : element.value])) : '';
  const hasChanges = () => Boolean(form && initialSnapshot && snapshot() !== initialSnapshot);
  const resetForm = () => {
    if (!form) return;
    form.reset();
    clearErrors();
    editingId = null;
    createCode = `DEL-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    ++neighborSearchVersion;
    previousContact = null;
    selectNeighbor(null);
    neighborLookup.disabled = false;
    neighborLookup.textContent = 'Consultar RUT';
    if (initialNeighbor?.estado === 'Activo') selectNeighbor(initialNeighbor);
    legacyType = false;
    allowModalClose = false;
    date.value = date.max;
    document.getElementById('attentionModalTitle').textContent = 'Nueva atención';
    document.getElementById('legacy-type-note').hidden = true;
    save.textContent = 'Guardar atención';
    type.required = true;
    subtype.required = true;
    refreshSubtypes();
    initialSnapshot = snapshot();
  };
  modalNode?.addEventListener('show.bs.modal', event => {
    if (event.relatedTarget?.dataset.action === 'create') resetForm();
  });
  modalNode?.addEventListener('shown.bs.modal', () => {
    initialSnapshot = snapshot();
    (neighborMode() === 'new' ? document.getElementById('field-contact') : neighborSearch)?.focus();
  });
  modalNode?.addEventListener('hide.bs.modal', async event => {
    if (allowModalClose) return;
    if (saving) { event.preventDefault(); return; }
    if (!hasChanges()) return;
    event.preventDefault();
    const answer = await popup({ title: '¿Descartar los cambios?', text: 'Los datos que modificaste en este formulario todavía no se han guardado.', icon: 'warning', showCancelButton: true, confirmButtonText: 'Descartar cambios', cancelButtonText: 'Seguir editando', focusCancel: true });
    if (answer.isConfirmed) {
      allowModalClose = true;
      window.bootstrap.Modal.getOrCreateInstance(modalNode).hide();
    }
  });
  modalNode?.addEventListener('hidden.bs.modal', () => { allowModalClose = false; initialSnapshot = ''; });

  const validateForm = () => {
    clearErrors();
    const errors = [];
    const fail = (key, message) => { fieldError(key, message); errors.push(key); };
    if (!['existing', 'new'].includes(neighborMode()) || resolvedRut !== normalizeRut(neighborSearch.value)) fail('neighbor', 'Consulta primero el RUT del solicitante.');
    if (neighborMode() === 'existing' && !selectedNeighbor) fail('neighbor', 'Consulta el RUT para identificar al vecino registrado.');
    if (neighborMode() === 'new') {
      if (!validRut(form.elements.neighbor_rut.value.trim())) fail('rut', 'Revisa el RUT y su dígito verificador.');
      if (!form.elements.neighbor_address.value.trim()) fail('address', 'Escribe la dirección del vecino.');
      if (form.elements.neighbor_email.validity.typeMismatch) fail('email', 'Revisa el correo del vecino.');
    }
    if (!form.elements.contact_name.value.trim()) fail('contact', 'Escribe el nombre del solicitante.');
    const phone = form.elements.contact_phone.value.trim();
    const digits = phone.replace(/\D/g, '');
    if (neighborMode() !== 'existing' && phone && (!/^\+?[\d\s()-]+$/.test(phone) || digits.length < 7 || digits.length > 15)) fail('phone', 'Usa entre 7 y 15 dígitos, con +, espacios o guiones si los necesitas.');
    if (!date.value || date.validity.badInput) fail('date', 'Selecciona una fecha válida.');
    else if (date.value > date.max) fail('date', 'La fecha de atención no puede ser futura.');
    const keepLegacy = editingId && legacyType && !type.value && !subtype.value;
    if (!keepLegacy) {
      if (!type.value) fail('type', 'Selecciona el tipo de atención.');
      if (!subtype.value) fail('subtype', 'Selecciona la subatención.');
      else if (subtype.selectedOptions[0]?.dataset.type !== type.value) fail('subtype', 'La subatención debe corresponder al tipo seleccionado.');
    }
    if (!form.elements.problem_description.value.trim()) fail('problem', 'Describe la solicitud recibida.');
    if (!form.elements.executed_action.value.trim()) fail('action', 'Describe la acción realizada o la derivación.');
    if (errors.length) showSummary('Revisa los campos señalados antes de guardar la atención.');
    return errors;
  };
  form?.addEventListener('input', event => {
    const key = Object.keys(fieldMap).find(name => fieldMap[name] === event.target.id);
    if (key) {
      event.target.removeAttribute('aria-invalid');
      event.target.classList.remove('is-invalid');
      document.getElementById(`error-${key}`).textContent = '';
    }
  });

  const showDetail = attention => {
    const content = createElement('div', undefined, 'attention-detail');
    const list = document.createElement('dl');
    const entries = [
      ['Solicitante', attention.contact_name || 'Sin nombre'],
      ['Padrón de vecinos', attention.neighbor ? `Registrado · ${attention.neighbor.rut}` : 'Solicitante sin ficha vinculada'],
      ['Teléfono', attention.contact_phone || 'Sin teléfono'],
      ['Fecha', attention.date],
      ['Estado', statusLabels[attention.validation_status] || attention.validation_status],
      ['Delegación', attention.delegation],
      ['Tipo', attention.attention_type || 'Clasificación anterior'],
      ['Subatención', attention.subattention_type || 'Sin subatención'],
    ];
    if (attention.social_case_id) entries.push(['Caso social', `#${attention.social_case_id}`]);
    entries.forEach(([label, value]) => list.append(createElement('dt', label), createElement('dd', value)));
    content.append(list, createElement('h3', 'Solicitud del vecino'), createElement('p', attention.problem_description), createElement('h3', 'Acción realizada o derivación'), createElement('p', attention.executed_action));
    if (attention.observation) content.append(createElement('h3', 'Observaciones de revisión'), createElement('p', attention.observation));
    return popup({ titleText: attention.activity_code, html: content, width: 620, confirmButtonText: 'Cerrar ficha' });
  };

  document.querySelector('.delegado-table')?.addEventListener('click', async event => {
    const button = event.target.closest('button[data-action]');
    if (!button || button.disabled) return;
    const id = button.dataset.id;
    if (button.dataset.action !== 'view' && button.closest('tr')?.dataset.socialCase) {
      await notify('info', 'Caso social vinculado', 'Esta atención se gestiona desde el caso social.');
      return;
    }
    if (button.dataset.action === 'delete') {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      try {
        const { atencion } = await request(detailUrl(id));
        const identity = atencion.neighbor ? `RUT ${atencion.neighbor.rut}` : 'sin ficha vinculada';
        const answer = await popup({ title: 'Dar de baja la atención', text: `¿Dar de baja ${atencion.activity_code} de ${atencion.contact_name} (${identity})? Se conservarán la ficha del vecino y la auditoría.`, icon: 'warning', showCancelButton: true, confirmButtonText: 'Sí, dar de baja', focusCancel: true });
        if (!answer.isConfirmed) return;
        const result = await request(detailUrl(id), { method: 'DELETE' });
        await notify('success', 'Atención dada de baja', result.message);
        window.location.reload();
      } catch (error) { await notify('error', 'No se pudo dar de baja', error.message); }
      finally { button.disabled = false; button.removeAttribute('aria-busy'); }
      return;
    }
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    try {
      const result = await request(detailUrl(id));
      const attention = result.atencion;
      if (button.dataset.action === 'view') { await showDetail(attention); return; }
      if (attention.social_case_id) { await notify('info', 'Caso social vinculado', 'Esta atención se gestiona desde el caso social.'); return; }
      if (!form || !window.bootstrap) { await notify('error', 'Formulario no disponible', 'Actualiza la página para cargar el formulario de atención.'); return; }
      resetForm();
      editingId = id;
      if (attention.neighbor) {
        selectNeighbor(attention.neighbor);
      } else {
        previousContact = { name: attention.contact_name || '', phone: attention.contact_phone || '' };
        document.getElementById('neighbor-search-status').textContent = 'Esta atención no tiene una ficha vinculada. Consulta el RUT para identificar o registrar al solicitante antes de guardar.';
      }
      document.getElementById('attentionModalTitle').textContent = `Editar ${attention.activity_code}`;
      save.textContent = 'Guardar cambios';
      if (!attention.neighbor) {
        form.elements.contact_name.value = previousContact.name;
        form.elements.contact_phone.value = previousContact.phone;
      }
      form.elements.activity_date.value = attention.activity_date_iso || '';
      form.elements.problem_description.value = attention.problem_description || '';
      form.elements.executed_action.value = attention.executed_action || '';
      form.elements.is_collective_agenda.checked = attention.stage === 2;
      type.value = attention.attention_type_id ? String(attention.attention_type_id) : '';
      refreshSubtypes();
      subtype.value = attention.subattention_id ? String(attention.subattention_id) : '';
      if (!type.value || !subtype.value) {
        legacyType = true;
        type.value = '';
        refreshSubtypes();
        type.required = false;
        subtype.required = false;
        document.getElementById('legacy-type-note').hidden = false;
      }
      window.bootstrap.Modal.getOrCreateInstance(modalNode).show();
    } catch (error) { await notify('error', 'No se pudo abrir la atención', error.message); }
    finally { button.disabled = false; button.removeAttribute('aria-busy'); }
  });

  const hideEditor = () => new Promise(resolve => {
    if (!modalNode?.classList.contains('show')) { resolve(); return; }
    modalNode.addEventListener('hidden.bs.modal', resolve, { once: true });
    allowModalClose = true;
    window.bootstrap.Modal.getOrCreateInstance(modalNode).hide();
  });
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (saving) return;
    const errors = validateForm();
    if (errors.length) {
      await notify('warning', 'Revisa los datos de la atención', 'Completa o corrige los campos señalados en el formulario.');
      document.getElementById(fieldMap[errors[0]])?.focus();
      return;
    }
    const payload = {
      contact_name: form.elements.contact_name.value.trim(),
      contact_phone: form.elements.contact_phone.value.trim(),
      activity_date: form.elements.activity_date.value,
      problem_description: form.elements.problem_description.value.trim(),
      executed_action: form.elements.executed_action.value.trim(),
      is_collective_agenda: form.elements.is_collective_agenda.checked,
    };
    if (neighborMode() === 'existing') payload.neighbor_id = selectedNeighbor.id;
    if (neighborMode() === 'new') payload.new_neighbor = {
      nombre: payload.contact_name, telefono: payload.contact_phone,
      rut: form.elements.neighbor_rut.value.trim(), direccion: form.elements.neighbor_address.value.trim(),
      email: form.elements.neighbor_email.value.trim(),
    };
    // This identifier is context for the API, never authorization. The server
    // independently resolves and checks the authenticated user's delegation.
    if (!editingId) { payload.delegation = app.dataset.delegation; payload.activity_code = createCode; }
    if (type.value && subtype.value) {
      payload.attention_type_id = Number(type.value);
      payload.subattention_id = Number(subtype.value);
    }
    saving = true;
    save.disabled = true;
    neighborSearch.disabled = true;
    neighborLookup.disabled = true;
    save.setAttribute('aria-busy', 'true');
    const originalLabel = save.textContent;
    save.textContent = 'Guardando…';
    try {
      const result = await request(editingId ? detailUrl(editingId) : app.dataset.listUrl,
        { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      await hideEditor();
      await notify('success', editingId ? 'Cambios guardados' : 'Atención registrada', result.message);
      if (app.dataset.section === 'inicio') window.location.assign(app.dataset.attentionsUrl);
      else window.location.reload();
    } catch (error) {
      showSummary(error.message);
      await notify('error', 'No se pudo guardar', error.message);
      summary?.focus();
    } finally {
      saving = false;
      neighborSearch.disabled = false;
      neighborLookup.disabled = false;
      syncNeighborMode(neighborMode());
      save.removeAttribute('aria-busy');
      save.textContent = originalLabel;
    }
  });

  const registryForm = document.getElementById('delegado-neighbor-form');
  const registryModal = document.getElementById('neighborModal');
  const registrySave = document.getElementById('registry-save');
  const registryErrors = document.getElementById('neighbor-form-errors');
  let registryId = null, registrySaving = false, allowRegistryClose = false, registryInitial = '', registryOriginalRut = '';
  const registrySnapshot = () => registryForm ? JSON.stringify([...registryForm.elements].filter(field => field.name && field.name !== 'csrfmiddlewaretoken').map(field => [field.name, field.value])) : '';
  const registryHasChanges = () => Boolean(registryInitial && registrySnapshot() !== registryInitial);
  const neighborUrl = id => `${app.dataset.neighborsUrl}${encodeURIComponent(id)}/`;
  const showNeighbor = async result => {
    const neighbor = result.vecino;
    const content = createElement('div', undefined, 'attention-detail');
    const list = createElement('dl');
    for (const [label, value] of [['Nombre', neighbor.nombre], ['RUT', neighbor.rut], ['Teléfono', neighbor.telefono || 'Sin teléfono'], ['Correo', neighbor.email || 'Sin correo'], ['Dirección', neighbor.direccion || 'Sin dirección'], ['Estado', neighbor.estado]]) {
      list.append(createElement('dt', label), createElement('dd', value));
    }
    content.append(list, createElement('h3', 'Historial vinculado'), createElement('p', `${result.attention_count} atenciones · ${result.followup_count} en seguimiento.`));
    for (const attention of result.recent_attentions) content.append(createElement('p', `${attention.date} · ${attention.code} · ${attention.status}\n${attention.subject}`));
    const link = createElement('a', 'Ver sus atenciones', 'delegado-secondary');
    const url = new URL(app.dataset.attentionsUrl, location.origin);
    url.searchParams.set('vecino', neighbor.id);
    link.href = url.href;
    content.append(link);
    await popup({titleText:'Ficha del vecino',html:content,width:650,confirmButtonText:'Cerrar ficha'});
  };
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-neighbor-action]');
    if (!button || button.disabled) return;
    const action = button.dataset.neighborAction;
    const id = button.dataset.id;
    button.disabled = true;
    try {
      if (action === 'delete') {
        const detail = await request(neighborUrl(id));
        const answer = await popup({title:'Dar de baja al vecino',text:`¿Dar de baja la ficha de ${detail.vecino.nombre} (RUT ${detail.vecino.rut})? Sus atenciones y la auditoría se conservarán. Los vecinos con un caso social activo se gestionan desde su ficha social.`,icon:'warning',showCancelButton:true,confirmButtonText:'Sí, dar de baja',focusCancel:true});
        if (!answer.isConfirmed) return;
        const result = await request(neighborUrl(id), {method:'DELETE'});
        await notify('success','Vecino dado de baja',result.message);
        window.location.reload();
        return;
      }
      const result = action === 'create' ? null : await request(neighborUrl(id));
      if (action === 'view') { await showNeighbor(result); return; }
      if (!registryForm || !window.bootstrap) throw new Error('No se pudo cargar el formulario de vecinos. Actualiza la página.');
      registryForm.reset();
      registryErrors.hidden = true;
      registryId = action === 'edit' ? id : null;
      registryOriginalRut = result?.vecino.rut || '';
      document.getElementById('neighborModalTitle').textContent = registryId ? 'Editar vecino' : 'Registrar vecino';
      document.getElementById('neighbor-social-note').hidden = !result?.managed_social_case;
      for (const name of ['nombre','rut','telefono','email','direccion','estado']) {
        const field = registryForm.elements[name];
        if (result) field.value = result.vecino[name] || '';
        field.readOnly = Boolean(result?.managed_social_case && ['nombre','rut','telefono'].includes(name));
        if (name === 'estado') field.disabled = Boolean(result?.managed_social_case);
      }
      allowRegistryClose = false;
      registryInitial = registrySnapshot();
      window.bootstrap.Modal.getOrCreateInstance(registryModal).show();
    } catch (error) { await notify('error','No se pudo completar la operación',error.message); }
    finally { button.disabled = false; }
  });
  registryModal?.addEventListener('shown.bs.modal', () => registryForm.querySelector('input:not([readonly]):not([type=hidden])')?.focus());
  registryModal?.addEventListener('hide.bs.modal', async event => {
    if (allowRegistryClose) return;
    if (registrySaving) { event.preventDefault(); return; }
    if (!registryHasChanges()) return;
    event.preventDefault();
    const result = await popup({title:'¿Descartar los cambios del vecino?',text:'Los cambios todavía no se han guardado.',icon:'warning',showCancelButton:true,confirmButtonText:'Descartar cambios',cancelButtonText:'Seguir editando',focusCancel:true});
    if (result.isConfirmed) { allowRegistryClose = true; window.bootstrap.Modal.getOrCreateInstance(registryModal).hide(); }
  });
  registryForm?.addEventListener('submit', async event => {
    event.preventDefault();
    if (registrySaving) return;
    registryErrors.hidden = true;
    const unchangedRut = registryId && registryForm.elements.rut.value.trim() === registryOriginalRut;
    if (!registryForm.checkValidity() || (!unchangedRut && !validRut(registryForm.elements.rut.value.trim()))) {
      registryErrors.textContent = 'Completa nombre, RUT válido y dirección. Revisa el formato del correo si lo ingresaste.';
      registryErrors.hidden = false;
      registryErrors.focus();
      return;
    }
    const payload = Object.fromEntries(['nombre','rut','telefono','email','direccion','estado'].map(name => [name,registryForm.elements[name].value.trim()]));
    registrySaving = true;
    registrySave.disabled = true;
    registrySave.textContent = 'Guardando…';
    try {
      const result = await request(registryId ? neighborUrl(registryId) : app.dataset.neighborsUrl,{method:registryId?'PUT':'POST',body:JSON.stringify(payload)});
      allowRegistryClose = true;
      const hidden = new Promise(resolve => registryModal.addEventListener('hidden.bs.modal',resolve,{once:true}));
      window.bootstrap.Modal.getOrCreateInstance(registryModal).hide();
      await hidden;
      await notify('success',registryId?'Vecino actualizado':'Vecino registrado',result.message);
      if (!registryId) window.location.assign(`${app.dataset.neighborPageUrl}?q=${encodeURIComponent(result.vecino.rut)}`);
      else window.location.reload();
    } catch (error) {
      registryErrors.textContent = error.message;
      registryErrors.hidden = false;
      registryErrors.focus();
    } finally { registrySaving = false; registrySave.disabled = false; registrySave.textContent = 'Guardar vecino'; }
  });
  if (new URLSearchParams(location.search).get('nueva') === '1' && initialNeighbor?.estado === 'Activo' && form && window.bootstrap) {
    resetForm();
    window.bootstrap.Modal.getOrCreateInstance(modalNode).show();
    const currentUrl = new URL(location.href);
    currentUrl.searchParams.delete('nueva');
    history.replaceState(null, '', currentUrl);
  }

  document.querySelector('[data-action="logout"]')?.addEventListener('click', async event => {
    event.preventDefault();
    const link = event.currentTarget;
    const answer = await popup({ title: '¿Cerrar sesión?', text: hasChanges() || registryHasChanges() ? 'Los cambios del formulario que no guardaste se perderán.' : 'Podrás volver a ingresar con tu cuenta institucional.', icon: 'question', showCancelButton: true, confirmButtonText: 'Cerrar sesión', focusCancel: true });
    if (answer.isConfirmed) window.location.assign(link.href);
  });

  document.getElementById('export-page')?.addEventListener('click', async () => {
    const rows = [...document.querySelectorAll('.delegado-table tbody tr')].filter(row => row.querySelector('time'));
    if (!rows.length) return;
    const answer = await popup({ title: 'Exportar esta página', text: `Se descargarán ${rows.length} registros visibles de tu delegación, con los filtros actuales. Las otras páginas no se incluyen.`, icon: 'info', showCancelButton: true, confirmButtonText: 'Descargar CSV' });
    if (!answer.isConfirmed) return;
    // Prefix formula-leading values before quoting them so untrusted names or
    // subjects cannot become spreadsheet formulas when opening the CSV.
    const csvCell = value => {
      let text = String(value ?? '').trim();
      if (/^[=+@\-\t\r]/.test(text)) text = `'${text}`;
      return `"${text.replace(/"/g, '""')}"`;
    };
    const records = [['Fecha', 'Código', 'Solicitante', 'Asunto', 'Estado']];
    rows.forEach(row => {
      const cells = row.querySelectorAll('td');
      const subject = cells[2].querySelector('.subject-copy');
      records.push([row.querySelector('time').dateTime, cells[0].querySelector('small').textContent, cells[1].textContent, subject?.getAttribute('title') || subject?.textContent, cells[3].textContent]);
    });
    const csv = '\uFEFF' + records.map(record => record.map(csvCell).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const download = document.createElement('a');
    const code = (app.dataset.delegationCode || 'delegacion').replace(/[^a-zA-Z0-9_-]/g, '-');
    download.href = url;
    download.download = `atenciones-${code}-pagina-${document.querySelector('.current-page')?.textContent.trim() || '1'}.csv`;
    document.body.append(download);
    download.click();
    download.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    announce('Se ha preparado la descarga de la página visible de atenciones.');
  });
})();
