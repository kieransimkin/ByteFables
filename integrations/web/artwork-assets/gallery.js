/* Local, non-module viewer: no JSON fetch; file:// access depends on browser policy. */
(() => {
  'use strict';
  const rows = window.BYTEFABLES_ASSETS;
  const status = document.getElementById('status');
  if (!Array.isArray(rows) || rows.length > 8192) {
    status.textContent = 'Invalid or missing local asset inventory.';
    return;
  }
  const byId = id => document.getElementById(id);
  const controls = ['query', 'family', 'palette', 'size'].map(byId);
  for (const field of ['family', 'palette']) {
    for (const value of [...new Set(rows.map(r => r[field]))].sort()) {
      const option = document.createElement('option');
      option.value = value; option.textContent = value; byId(field).append(option);
    }
  }
  // No automatic resampling or choosing a different size than the selector.
  const available = [...new Set(rows.flatMap(r => r.sizes))].sort((a, b) => a - b);
  if (!available.includes(Number(byId('size').value))) byId('size').value = String(available.at(-1));
  let page = 0;
  const pageSize = 48;
  const validPath = path => typeof path === 'string' && /^assets\/[a-z]+-(?:neon|pastel|mono)-c[1-8]\/[0-9a-f]{64}\/(?:16|32|64|128|icon)\.(?:png|webp|ico)$/.test(path);
  function element(tag, className, text) {
    const node = document.createElement(tag); if (className) node.className = className;
    if (text !== undefined) node.textContent = text; return node;
  }
  function render() {
    const query = byId('query').value.trim().toLowerCase();
    const family = byId('family').value, palette = byId('palette').value;
    const size = Number(byId('size').value);
    const selected = rows.filter(r => r.digest.includes(query) && (!family || r.family === family) &&
      (!palette || r.palette === palette) && r.sizes.includes(size));
    const pages = Math.max(1, Math.ceil(selected.length / pageSize));
    page = Math.min(page, pages - 1);
    const grid = byId('grid'); grid.replaceChildren();
    for (const row of selected.slice(page * pageSize, (page + 1) * pageSize)) {
      const files = row.files.filter(f => validPath(f.file) &&
        (f.format === 'ico' || f.frames.length === 1 && f.frames[0].size === size));
      const png = files.find(f => f.format === 'png');
      if (!png) continue;
      const card = element('article');
      card.append(element('h2', null, `${row.family} · ${row.palette}`));
      card.append(element('p', 'meta', `${size} × ${size} native pixels · complexity ${row.complexity}`));
      const preview = element('div', 'preview'), img = element('img');
      img.src = png.file; img.width = size; img.height = size; img.loading = 'lazy';
      img.alt = `${row.family} ${row.palette} public identity ${row.digest}`;
      preview.append(img); card.append(preview, element('code', 'digest', row.digest));
      const links = element('div', 'links');
      for (const file of files) {
        const link = element('a', null, file.format.toUpperCase()); link.href = file.file;
        link.download = file.format === 'ico' ? `${row.digest}-native.ico` : `${row.digest}-${size}.${file.format}`; links.append(link);
      }
      card.append(links); grid.append(card);
    }
    status.textContent = `${selected.length} matching identities/styles at ${size}px. Images are shown at their native size.`;
    byId('position').textContent = `Page ${page + 1} of ${pages}`;
    byId('previous').disabled = page === 0; byId('next').disabled = page + 1 === pages;
  }
  byId('filters').addEventListener('submit', e => e.preventDefault());
  controls.forEach(control => control.addEventListener('input', () => { page = 0; render(); }));
  byId('previous').addEventListener('click', () => { page--; render(); });
  byId('next').addEventListener('click', () => { page++; render(); });
  render();
})();
