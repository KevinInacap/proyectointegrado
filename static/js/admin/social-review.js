(function () {
    'use strict';

    const csrfToken = () => {
        const cookie = document.cookie.split(';').map(value => value.trim()).find(value => value.startsWith('csrftoken='));
        return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
    };
    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[character]);

    async function api(url, options = {}) {
        const response = await fetch(url, {
            credentials: 'same-origin',
            ...options,
            headers: {
                ...(options.body ? { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() } : {}),
                ...(options.headers || {}),
            },
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.success) throw new Error(data.message || `Error ${response.status}`);
        return data;
    }

    function renderNotifications(items) {
        const list = document.getElementById('adminNotifList');
        if (!list) return;
        if (!items.length) {
            list.innerHTML = '<div class="p-4 text-center text-secondary small"><i class="bi bi-bell-slash d-block fs-4 mb-2" aria-hidden="true"></i>No hay solicitudes nuevas.</div>';
            return;
        }
        list.innerHTML = items.map(item => `
            <button type="button" class="notif-item ${item.is_read ? '' : 'unread'}" data-notification-id="${Number(item.id)}" data-request-id="${Number(item.request_id)}">
                <span>${escapeHtml(item.message)}</span><small>${escapeHtml(item.created_at)} · Abrir solicitud</small>
            </button>`).join('');
        list.querySelectorAll('[data-request-id]').forEach(button => button.addEventListener('click', async () => {
            try {
                await api('/social/api/notificaciones/', { method: 'POST', body: JSON.stringify({ ids: [Number(button.dataset.notificationId)] }) });
                await loadAdminSocialNotifications();
                if (typeof window.switchView === 'function') window.switchView('solicitudes-sociales');
                const filter = document.getElementById('socialRequestStatusFilter');
                if (filter) filter.value = 'pendiente';
                await loadSocialReviewRequests();
            } catch (error) {
                if (window.Swal) Swal.fire({ icon: 'error', title: 'No se pudo abrir la solicitud', text: error.message });
            }
        }));
    }

    window.loadAdminSocialNotifications = async function () {
        try {
            const data = await api('/social/api/notificaciones/');
            const badge = document.getElementById('adminNotifBadge');
            if (badge) {
                badge.textContent = String(data.unread_count || 0);
                badge.hidden = !data.unread_count;
            }
            renderNotifications(data.notifications || []);
        } catch (error) {
            const list = document.getElementById('adminNotifList');
            if (list) list.innerHTML = '<div class="p-3 text-center text-secondary small">No fue posible cargar las notificaciones.</div>';
        }
    };

    window.marcarNotificacionesLeidas = async function () {
        try {
            await api('/social/api/notificaciones/', { method: 'POST', body: JSON.stringify({ all: true }) });
            await window.loadAdminSocialNotifications();
        } catch (error) {
            if (window.Swal) Swal.fire({ icon: 'error', title: 'No se pudo actualizar', text: error.message });
        }
    };

    function proposalMarkup(changes) {
        const entries = Object.entries(changes || {});
        if (!entries.length) return '';
        const labels = { user_name: 'Nombre', user_rut: 'RUT', contact_phone: 'Teléfono', entry_date: 'Fecha de ingreso' };
        return `<div class="social-review-proposal"><strong>Corrección propuesta</strong><br>${entries.map(([key, value]) => `${escapeHtml(labels[key] || key)}: ${escapeHtml(value)}`).join('<br>')}</div>`;
    }

    function renderRequests(items) {
        const body = document.getElementById('socialReviewRequestsBody');
        if (!body) return;
        if (!items.length) {
            body.innerHTML = '<tr><td colspan="5" class="text-center py-5 text-secondary"><i class="bi bi-check2-circle fs-3 d-block mb-2"></i>No hay solicitudes para este filtro.</td></tr>';
            return;
        }
        body.innerHTML = items.map(item => {
            const stateClass = item.status === 'pendiente' ? 'pending' : item.status === 'aprobada' ? 'approved' : 'rejected';
            const person = [item.requester_position, item.requester_delegation].filter(Boolean).map(escapeHtml).join(' · ');
            const target = item.case ? `${item.case.name} · ${item.case.rut}` : item.target_label;
            const actions = item.status === 'pendiente' ? `
                <div class="d-flex justify-content-end gap-2">
                    <button type="button" class="btn btn-sm btn-success rounded-pill" data-decision="aprobada" data-id="${Number(item.id)}"><i class="bi bi-check2 me-1"></i>Aprobar</button>
                    <button type="button" class="btn btn-sm btn-outline-danger rounded-pill" data-decision="rechazada" data-id="${Number(item.id)}"><i class="bi bi-x-lg me-1"></i>Rechazar</button>
                </div>` : `<span class="social-review-muted">${escapeHtml(item.reviewer_name || '')}${item.resolution_note ? `<br>${escapeHtml(item.resolution_note)}` : ''}</span>`;
            return `<tr>
                <td><div class="social-review-person">${escapeHtml(item.request_type_label)}</div><div class="social-review-muted">${escapeHtml(item.created_at)}</div><div class="social-review-muted">${escapeHtml(target)}</div></td>
                <td><div class="social-review-person">${escapeHtml(item.requester_name)}</div><div class="social-review-muted">${person || 'Cargo/delegación no disponible'}</div></td>
                <td><div>${escapeHtml(item.reason)}</div>${proposalMarkup(item.requested_changes)}</td>
                <td><span class="social-review-state ${stateClass}">${escapeHtml(item.status_label)}</span></td>
                <td class="text-end">${actions}</td>
            </tr>`;
        }).join('');
        body.querySelectorAll('[data-decision]').forEach(button => button.addEventListener('click', () => resolveRequest(button.dataset.id, button.dataset.decision)));
    }

    async function resolveRequest(id, decision) {
        const approved = decision === 'aprobada';
        const result = await Swal.fire({
            icon: approved ? 'question' : 'warning',
            title: approved ? '¿Aprobar la solicitud?' : '¿Rechazar la solicitud?',
            text: approved ? 'Si incluye cambios, se aplicarán al caso y quedarán auditados.' : 'La solicitud quedará cerrada sin modificar los datos del caso.',
            input: 'textarea',
            inputLabel: 'Observación para el funcionario (opcional al aprobar)',
            inputPlaceholder: 'Escribe una breve observación…',
            inputAttributes: { maxlength: 1000, 'aria-label': 'Observación de resolución' },
            showCancelButton: true,
            confirmButtonText: approved ? 'Aprobar y guardar' : 'Rechazar solicitud',
            cancelButtonText: 'Volver',
            confirmButtonColor: approved ? '#16804a' : '#a30f32',
            preConfirm: value => {
                if (!approved && !String(value || '').trim()) {
                    Swal.showValidationMessage('Indica el motivo del rechazo para que el funcionario pueda corregirlo.');
                    return false;
                }
                return value || '';
            },
        });
        if (!result.isConfirmed) return;
        try {
            const data = await api(`/social/api/solicitudes/${Number(id)}/resolver/`, {
                method: 'POST', body: JSON.stringify({ decision, resolution_note: result.value }),
            });
            await Swal.fire({ icon: 'success', title: 'Decisión registrada', text: data.message, confirmButtonColor: '#1b365d' });
            await Promise.all([loadSocialReviewRequests(), window.loadAdminSocialNotifications()]);
        } catch (error) {
            Swal.fire({ icon: 'error', title: 'No se pudo resolver', text: error.message, confirmButtonColor: '#a30f32' });
        }
    }

    window.loadSocialReviewRequests = async function () {
        const body = document.getElementById('socialReviewRequestsBody');
        if (!body) return;
        const filter = document.getElementById('socialRequestStatusFilter');
        const status = filter ? filter.value : 'pendiente';
        body.innerHTML = '<tr><td colspan="5" class="text-center py-5 text-secondary"><span class="spinner-border spinner-border-sm me-2"></span>Cargando solicitudes…</td></tr>';
        try {
            const data = await api(`/social/api/solicitudes/?status=${encodeURIComponent(status)}`);
            renderRequests(data.requests || []);
            const pending = Number(data.pending_count || 0);
            const badge = document.getElementById('socialRequestPendingBadge');
            if (badge) badge.textContent = `Pendientes: ${pending}`;
            const nav = document.getElementById('nav-btn-social-requests');
            if (nav) {
                let navCount = nav.querySelector('.admin-social-nav-count');
                if (pending && !navCount) {
                    navCount = document.createElement('span');
                    navCount.className = 'admin-social-nav-count';
                    nav.appendChild(navCount);
                }
                if (navCount) {
                    navCount.textContent = String(pending);
                    navCount.hidden = pending === 0;
                }
            }
        } catch (error) {
            body.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-danger">${escapeHtml(error.message)}</td></tr>`;
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.loadAdminSocialNotifications();
        window.setInterval(window.loadAdminSocialNotifications, 45000);
    });
})();
