/* Contexto de lectura: conserva la columna y fila visibles al recorrer tablas extensas. */
(() => {
    const selector = '.maintainer-view table, #view-dashboard table';
    let activeCell = null;
    let activeHeader = null;

    function setContext(target) {
        const cell = target.closest('td, th');
        const table = cell?.closest('table');
        if (!table || !table.matches(selector) || cell === activeCell) return;
        activeCell?.classList.remove('sgr-current-cell');
        activeHeader?.classList.remove('sgr-current-column');
        activeCell = cell;
        activeCell.classList.add('sgr-current-cell');

        const headings = Array.from(table.tHead?.rows[table.tHead.rows.length - 1]?.cells || []);
        activeHeader = headings[cell.cellIndex] || null;
        activeHeader?.classList.add('sgr-current-column');
        const label = (activeHeader?.textContent || cell.dataset.label || `Columna ${cell.cellIndex + 1}`).trim().replace(/\s+/g, ' ');
        const row = cell.parentElement;
        const rowText = row.parentElement?.tagName === 'TBODY' ? `Fila ${row.sectionRowIndex + 1} · ` : '';
        let indicator = table.previousElementSibling;
        if (!indicator?.classList.contains('sgr-cell-context')) {
            indicator = document.createElement('div');
            indicator.className = 'sgr-cell-context';
            indicator.setAttribute('role', 'status');
            indicator.setAttribute('aria-live', 'polite');
            table.parentNode.insertBefore(indicator, table);
        }
        indicator.textContent = `${rowText}${label}`;
    }

    document.addEventListener('pointerover', event => {
        if (event.target instanceof Element) setContext(event.target);
    });
    document.addEventListener('focusin', event => {
        if (event.target instanceof Element) setContext(event.target);
    });
    document.addEventListener('click', event => {
        if (event.target instanceof Element) setContext(event.target);
    });
})();
