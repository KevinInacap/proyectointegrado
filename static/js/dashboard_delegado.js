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
  let editingId = null;
  let legacyType = false;

  const notify = (icon, title, message) => {
    if (window.Swal) return Swal.fire({ icon, title, text: message, confirmButtonColor: '#8b1d2c' });
    window.alert(`${title}: ${message}`);
    return Promise.resolve();
  };
  const detailUrl = id => `${app.dataset.detailBase}${encodeURIComponent(id)}/`;
  const csrf = () => document.querySelector('#delegado-csrf [name=csrfmiddlewaretoken], #delegado-attention-form [name=csrfmiddlewaretoken]')?.value || '';
  const request = async (url, options = {}) => {
    let response;
    try {
      response = await fetch(url, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        ...options,
      });
    } catch {
      throw new Error('No pudimos conectar con el servidor. Comprueba tu conexión e inténtalo otra vez.');
    }
    let data;
    try { data = await response.json(); } catch { throw new Error('El servidor devolvió una respuesta inesperada.'); }
    if (!response.ok || !data.success) throw new Error(data.message || 'La operación no pudo completarse.');
    return data;
  };
  const refreshSubtypes = () => {
    if (!type || !subtype) return;
    const selected = subtype.value;
    let visible = 0;
    for (const option of subtype.options) {
      if (!option.value) continue;
      option.hidden = option.dataset.type !== type.value;
      option.disabled = option.hidden;
      if (!option.hidden) visible++;
    }
    if (!Array.from(subtype.options).some(option => option.value === selected && !option.hidden)) subtype.value = '';
    subtype.options[0].textContent = type.value ? (visible ? 'Selecciona una sub atención' : 'No hay sub atenciones activas') : 'Selecciona primero el tipo';
  };
  type?.addEventListener('change', refreshSubtypes);

  const resetForm = () => {
    if (!form) return;
    form.reset();
    editingId = null;
    legacyType = false;
    date.value = date.max;
    document.getElementById('attentionModalTitle').textContent = 'Nueva atención';
    save.textContent = 'Guardar atención';
    type.required = true;
    subtype.required = true;
    refreshSubtypes();
  };
  modalNode?.addEventListener('show.bs.modal', event => {
    if (event.relatedTarget?.dataset.action === 'create') resetForm();
  });

  const navLinks = [...document.querySelectorAll('.delegado-shell .primary-nav .nav-link')];
  const syncNavigation = () => {
    const current = navLinks.find(link => link.getAttribute('href') === location.hash) || navLinks[0];
    navLinks.forEach(link => {
      link.classList.toggle('is-current', link === current);
      if (link === current) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  };
  window.addEventListener('hashchange', syncNavigation);
  syncNavigation();

  document.querySelector('.delegado-table')?.addEventListener('click', async event => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const id = button.dataset.id;
    if (button.dataset.action !== 'view' && button.closest('tr')?.dataset.socialCase) {
      await notify('info', 'Caso social vinculado', 'Esta atención se gestiona desde el caso social.');
      return;
    }
    if (button.dataset.action === 'delete') {
      const confirmed = window.Swal
        ? (await Swal.fire({ title: 'Dar de baja la atención', text: `¿Quieres dar de baja ${button.dataset.code}? El registro seguirá en la auditoría.`, icon: 'warning', showCancelButton: true, confirmButtonText: 'Sí, dar de baja', cancelButtonText: 'Cancelar', confirmButtonColor: '#8b1d2c' })).isConfirmed
        : window.confirm(`¿Dar de baja ${button.dataset.code}?`);
      if (!confirmed) return;
      try {
        const result = await request(detailUrl(id), { method: 'DELETE' });
        await notify('success', 'Atención dada de baja', result.message);
        window.location.reload();
      } catch (error) { await notify('error', 'No se pudo dar de baja', error.message); }
      return;
    }
    try {
      const result = await request(detailUrl(id));
      const attention = result.atencion;
      if (button.dataset.action === 'view') {
        await notify('info', attention.activity_code, `${attention.social_case_id ? `Caso social #${attention.social_case_id}\n` : ''}Solicitante: ${attention.contact_name}\nFecha: ${attention.date}\nEstado: ${attention.validation_status}\nSolicitud: ${attention.problem_description}\nAcción: ${attention.executed_action}`);
        return;
      }
      if (attention.social_case_id) {
        await notify('info', 'Caso social vinculado', 'Esta atención se gestiona desde el caso social.');
        return;
      }
      if (!form || !window.bootstrap) return;
      resetForm();
      editingId = id;
      document.getElementById('attentionModalTitle').textContent = `Editar ${attention.activity_code}`;
      save.textContent = 'Guardar cambios';
      form.elements.contact_name.value = attention.contact_name || '';
      form.elements.contact_phone.value = attention.contact_phone || '';
      form.elements.activity_date.value = attention.activity_date_iso || '';
      form.elements.problem_description.value = attention.problem_description || '';
      form.elements.executed_action.value = attention.executed_action || '';
      form.elements.is_collective_agenda.checked = attention.stage === 2;
      if (attention.attention_type_id && attention.subattention_id) {
        type.value = String(attention.attention_type_id);
        refreshSubtypes();
        subtype.value = String(attention.subattention_id);
      } else {
        legacyType = true;
        type.required = false;
        subtype.required = false;
      }
      bootstrap.Modal.getOrCreateInstance(modalNode).show();
    } catch (error) { await notify('error', 'No se pudo abrir la atención', error.message); }
  });

  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.checkValidity()) {
      await notify('warning', 'Faltan datos', 'Completa los campos obligatorios antes de guardar.');
      form.querySelector(':invalid')?.focus();
      return;
    }
    if ((!type.value || !subtype.value) && !(editingId && legacyType)) {
      await notify('warning', 'Clasificación incompleta', 'Selecciona el tipo y la sub atención.');
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
    if (!editingId) payload.delegation = app.dataset.delegation;
    if (type.value && subtype.value) {
      payload.attention_type_id = Number(type.value);
      payload.subattention_id = Number(subtype.value);
    }
    save.disabled = true;
    try {
      const result = await request(editingId ? detailUrl(editingId) : app.dataset.listUrl,
        { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      bootstrap.Modal.getOrCreateInstance(modalNode).hide();
      await notify('success', editingId ? 'Cambios guardados' : 'Atención registrada', result.message);
      window.location.reload();
    } catch (error) { await notify('error', 'No se pudo guardar', error.message); }
    finally { save.disabled = false; }
  });
})();
