(() => {
  'use strict';
  const menu = document.querySelector('[data-account-menu]');
  if (!menu) return;
  const trigger = menu.querySelector('[data-account-toggle]');
  const panel = menu.querySelector('.account-options');
  const profile = document.getElementById('account-profile-dialog');
  const nativePopover = typeof panel.showPopover === 'function';
  let isOpen = false;
  if (!nativePopover) document.body.append(panel);

  const positionPanel = () => {
    const rect = trigger.getBoundingClientRect();
    panel.style.top = `${Math.min(rect.bottom + 8, window.innerHeight - panel.offsetHeight - 12)}px`;
    panel.style.left = `${Math.max(12, Math.min(rect.right - panel.offsetWidth, window.innerWidth - panel.offsetWidth - 12))}px`;
  };
  const sync = open => {
    isOpen = open;
    trigger.setAttribute('aria-expanded', String(open));
    panel.classList.toggle('is-open', open);
    if (open) positionPanel();
  };
  const close = (restoreFocus = false) => {
    if (nativePopover && panel.matches(':popover-open')) panel.hidePopover();
    sync(false);
    if (restoreFocus) trigger.focus();
  };
  trigger.addEventListener('click', () => {
    if (isOpen) { close(); return; }
    sync(true);
    if (nativePopover) panel.showPopover();
    positionPanel();
  });
  if (nativePopover) panel.addEventListener('toggle', event => sync(event.newState === 'open'));
  document.addEventListener('pointerdown', event => {
    if (isOpen && !menu.contains(event.target) && !panel.contains(event.target)) close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && isOpen) { event.preventDefault(); close(true); }
  });
  window.addEventListener('resize', () => { if (isOpen) positionPanel(); });
  window.addEventListener('scroll', () => { if (isOpen) close(); }, true);

  panel.querySelector('[data-account-profile-open]').addEventListener('click', () => {
    close();
    profile.showModal();
  });
  panel.querySelector('[data-account-audit]')?.addEventListener('click', () => {
    close();
    if (typeof window.abrirModalAuditoria === 'function') window.abrirModalAuditoria();
  });
  profile.addEventListener('close', () => trigger.focus());
  panel.querySelector('.account-logout').addEventListener('click', () => close());
})();

