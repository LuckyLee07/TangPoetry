import { parseStored, sanitizeSettings, migrateFavorites, filterPoems, initialIndex, createPoemLoader, readingLayout } from './reader-core.js?v=0.3.6';

const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const keys = { favorites: 'tang-favorites-v2', settings: 'tang-settings-v1', position: 'tang-position-v1' };
const storage = {
  read(key, fallback) { try { return parseStored(localStorage.getItem(key), fallback); } catch { return fallback; } },
  write(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { $('#storageNotice').hidden = false; $('#storageNotice').textContent = '当前浏览器无法保存记录，本次阅读仍可正常使用。'; } }
};
const pages = $('#pages');
const settings = sanitizeSettings(storage.read(keys.settings, null));
let poems = [], favorites = new Set(), currentIndex = 0, homeVisible = true, controlsVisible = true;
let filters = { query: '', collection: 'all', category: 'all' };
let shells = [], activeIDs = new Set(), loading = false, lastSavedID = '', alignedWidth = 0;
const pageDetails = new WeakMap();

async function fetchJSON(url) {
  const response = await fetch(url, { cache: 'no-cache', signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
const loader = createPoemLoader(id => fetchJSON(`./data/reader/poems/${encodeURIComponent(id)}.json`));

function applySettings() {
  document.body.dataset.paper = settings.paper;
  $('.reader').style.setProperty('--reader-size', `${settings.fontSize}px`);
  pages.classList.toggle('notes-off', !settings.notes);
  $('#toggleNotes').setAttribute('aria-pressed', settings.notes);
  $('#settingNotes').checked = settings.notes;
  $('#fontSize').value = settings.fontSize;
  document.querySelectorAll('[name="paper"]').forEach(input => { input.checked = input.value === settings.paper; });
  layoutMountedPages();
}
function changeSetting(key, value) { settings[key] = value; applySettings(); storage.write(keys.settings, settings); }

function setControls(visible) {
  controlsVisible = visible;
  for (const element of [$('#topbar'), $('#bottombar')]) { element.dataset.visible = visible; element.inert = !visible; }
  $('#revealControls').hidden = visible;
}
function setHome(visible) {
  homeVisible = visible;
  $('.reader').dataset.home = visible;
  $('#homeScreen').inert = !visible;
  $('#homeScreen').setAttribute('aria-hidden', !visible);
  $('#readingSurface').inert = visible;
  $('#readingSurface').setAttribute('aria-hidden', visible);
  if (visible) { $('#startReading').textContent = currentIndex ? '续读' : '入卷'; $('#startReading').focus(); }
}

function verses(lines) {
  return lines.map(line => {
    const text = line.map(([character]) => character).join('');
    const characters = [...text];
    const lastCharacter = characters.findLastIndex(character => !/\p{Punctuation}/u.test(character));
    const cells = [];
    for (const [index, character] of characters.entries()) {
      if (index > lastCharacter && cells.length) cells.at(-1).marks += character;
      else cells.push({ character, marks: '' });
    }
    const endSpace = Math.max(1, [...(cells.at(-1)?.marks || '')].length);
    return `<div class="verse-line" role="group" style="--end-space:${endSpace}em" aria-label="${escapeHTML(text)}">${cells.map(cell => `<span class="verse-cell" aria-hidden="true">${escapeHTML(cell.character)}${cell.marks ? `<span class="verse-punctuation">${escapeHTML(cell.marks)}</span>` : ''}</span>`).join('')}</div>`;
  }).join('');
}
function layoutPage(element) {
  const detail = pageDetails.get(element);
  if (!detail || !element.querySelector('.poem-body')) return;
  const layout = readingLayout(detail, { width: pages.clientWidth, height: pages.clientHeight, fontSize: settings.fontSize });
  element.dataset.layout = layout.kind;
  for (const [name, value] of Object.entries({ 'poem-top': layout.top, 'poem-bottom': layout.bottom, 'poem-size': layout.fontSize, 'title-size': layout.titleSize, 'note-gap': layout.noteGap })) {
    element.style.setProperty(`--${name}`, `${value}px`);
  }
  element.style.setProperty('--verse-leading', layout.lineHeight);
  // Account for actual fonts, title wrapping and browser scrollbar width after the estimate.
  const body = element.querySelector('.poem-body');
  const text = element.querySelector('.poem-text');
  let size = layout.fontSize;
  // Keep the existing type size while the poem moves and the note gains breathing room.
  while (layout.fitWhole && size > layout.minimumFont && text.scrollHeight > body.clientHeight - layout.textRise - 21) {
    size = Math.max(layout.minimumFont, size - 0.5);
    element.style.setProperty('--poem-size', `${size}px`);
  }
}
function layoutMountedPages() {
  for (const element of shells) if (element.childNodes.length) layoutPage(element);
}
function renderPage(element, poem, detail) {
  pageDetails.set(element, { ...detail, section: poem.section, textStart: poem.textStart });
  element.innerHTML = `<figure class="scene" aria-hidden="true"><img src="./${escapeHTML(poem.image)}" alt="" decoding="async" /></figure>
    <div class="book-ribbon">${escapeHTML(poem.section)}</div>
    <div class="poem-body" tabindex="0" aria-label="${escapeHTML(poem.title)}全文"><div class="poem-text"><h2 class="poem-title">${escapeHTML(poem.title)}</h2><p class="poem-author">唐 · ${escapeHTML(poem.author)}</p><div class="poem-lines">${verses(detail.rubyLines)}</div></div>
    ${detail.note ? `<section class="note"><h3>${escapeHTML(detail.noteTitle)}</h3><p>${escapeHTML(detail.note)}</p><button class="note-more" data-notes="${poem.id}" aria-label="查看${escapeHTML(poem.title)}的完整诗意和注释">展开</button></section>` : ''}</div>`;
  const image = element.querySelector('img');
  image.addEventListener('error', () => image.remove(), { once: true });
  layoutPage(element);
}
async function mountPage(index) {
  const poem = poems[index], element = shells[index];
  if (!poem || element.dataset.loaded || element.dataset.loading) return;
  element.dataset.loading = 'true';
  element.innerHTML = '<p class="page-message">展卷中…</p>';
  try {
    const detail = await loader.load(poem.id);
    if (!activeIDs.has(poem.id)) return;
    renderPage(element, poem, detail);
    element.dataset.loaded = 'true';
  } catch {
    if (activeIDs.has(poem.id)) element.innerHTML = `<div class="page-message">这一页暂时未能打开。<br><button data-retry="${index}">重试此页</button></div>`;
  } finally { delete element.dataset.loading; }
}
function hydrateWindow() {
  activeIDs = new Set(poems.slice(Math.max(0, currentIndex - 1), currentIndex + 2).map(p => p.id));
  shells.forEach((element, index) => {
    const current = index === currentIndex;
    element.inert = !current;
    element.setAttribute('aria-hidden', !current);
    if (activeIDs.has(poems[index].id)) { void mountPage(index); }
    else if (element.childNodes.length) { element.replaceChildren(); pageDetails.delete(element); delete element.dataset.loaded; }
  });
}
function updateState({ announce = false } = {}) {
  const poem = poems[currentIndex];
  if (!poem) return;
  $('#pageMark').textContent = `${currentIndex + 1} / ${poems.length}`;
  $('#favoriteButton').setAttribute('aria-pressed', favorites.has(poem.id));
  $('#favoriteButton').setAttribute('aria-label', favorites.has(poem.id) ? '取消收藏此诗' : '收藏此诗');
  $('#previousPoem').disabled = currentIndex === 0;
  $('#nextPoem').disabled = currentIndex === poems.length - 1;
  $('#favoriteCount').textContent = `${favorites.size} 首 ›`;
  if (!homeVisible && poem.id !== lastSavedID) { storage.write(keys.position, poem.id); lastSavedID = poem.id; }
  if (announce) $('#readerStatus').textContent = `${poem.title}，${poem.author}。第 ${currentIndex + 1} 首，共 ${poems.length} 首。`;
  hydrateWindow();
}
function goTo(index) {
  if (!poems.length) return;
  currentIndex = Math.max(0, Math.min(poems.length - 1, index));
  // Directory jumps are immediate: no traversal or loading of hundreds of intervening pages.
  alignPage();
  updateState({ announce: true });
}
function alignPage() {
  alignedWidth = pages.clientWidth;
  pages.scrollTo({ left: currentIndex * alignedWidth, behavior: 'instant' });
}
function enterReader(index = currentIndex) { setHome(false); setControls(true); goTo(index); pages.focus({ preventScroll: true }); }

function renderLibrary() {
  const list = filterPoems(poems, filters, favorites);
  const groups = new Map();
  for (const poem of list) {
    if (!groups.has(poem.section)) groups.set(poem.section, []);
    groups.get(poem.section).push(poem);
  }
  $('#resultCount').textContent = `${list.length} 首${filters.collection === 'favorites' ? '收藏' : ''}`;
  $('#categorySelect').value = filters.category;
  document.querySelectorAll('[data-collection]').forEach(button => button.setAttribute('aria-pressed', button.dataset.collection === filters.collection));
  $('#poemList').innerHTML = list.length ? [...groups].map(([section, items]) => `<section class="genre-group" aria-label="${escapeHTML(section)}"><h3 class="genre-heading">${escapeHTML(section)}<span>${items.length} 首</span></h3>${items.map(poem => `<button class="poem-row" data-id="${poem.id}" aria-current="${poem.id === poems[currentIndex]?.id}"><img class="poem-thumb" src="./${escapeHTML(poem.thumbnail)}" alt="" loading="lazy" decoding="async" /><span class="poem-row-copy"><strong>${escapeHTML(poem.title)}</strong><small>${escapeHTML(poem.author)}</small></span><em>${favorites.has(poem.id) ? '已藏' : poem.featured ? '精选' : ''}</em></button>`).join('')}</section>`).join('')
    : `<p class="empty-state">${filters.collection === 'favorites' && !favorites.size ? '还没有收藏。<br>在喜欢的诗页轻点「藏」，留给下次重读。' : '没有找到相符的诗。<br>试试其他诗句，或切换分类。'}</p>`;
}
function openLibrary(collection) {
  if (collection) { filters = { query: '', category: 'all', collection }; $('#searchInput').value = ''; }
  renderLibrary(); $('#library').showModal();
}
async function openNotes(id) {
  try {
    const poem = await loader.load(id);
    $('#fullNotes').innerHTML = `<h3>${escapeHTML(poem.title)}</h3><p>${escapeHTML(poem.note)}</p>${poem.notes.length ? `<ul>${poem.notes.map(note => `<li>${escapeHTML(note)}</li>`).join('')}</ul>` : ''}`;
    $('#notesDialog').showModal();
  } catch { $('#readerStatus').textContent = '注释暂时无法打开，请稍后重试。'; }
}

async function init() {
  if (loading) return;
  loading = true; $('#retryCatalog').hidden = true; $('#homeStatus').textContent = '';
  try {
    const catalog = await fetchJSON('./data/reader/catalog.json');
    if (!Array.isArray(catalog.poems) || !catalog.poems.length) throw new Error('Empty catalog');
    poems = catalog.poems;
    favorites = migrateFavorites(storage.read(keys.favorites, null), storage.read('tang-favorites', []), poems);
    storage.write(keys.favorites, [...favorites]);
    currentIndex = initialIndex(poems, storage.read(keys.position, ''), location.hash);
    shells = poems.map(poem => { const element = document.createElement('article'); element.className = 'poem-page'; element.dataset.id = poem.id; element.setAttribute('aria-label', poem.title); return element; });
    pages.replaceChildren(...shells);
    const themes = [...new Set(poems.map(p => p.theme))];
    const sections = [...new Set(poems.map(p => p.section))];
    $('#categorySelect').innerHTML = `<option value="all">全部分类</option><optgroup label="体裁">${sections.map(value => `<option>${escapeHTML(value)}</option>`).join('')}</optgroup><optgroup label="主题">${themes.map(value => `<option>${escapeHTML(value)}</option>`).join('')}</optgroup>`;
    $('#homeCount').textContent = `${poems.length} 首 · ${poems.filter(p => p.dedicatedArt).length} 幅画笺`;
    for (const id of ['startReading', 'homeLibrary', 'homeFeatured']) $(`#${id}`).disabled = false;
    $('#startReading').textContent = currentIndex ? '续读' : '入卷';
    updateState();
    if (location.hash.startsWith('#p=') || location.hash.startsWith('#poem=')) enterReader();
    if (location.hash === '#library') openLibrary('all');
  } catch {
    $('#homeCount').textContent = '诗库暂未打开';
    $('#homeStatus').textContent = '请检查连接后重试。'; $('#retryCatalog').hidden = false;
  } finally { loading = false; }
}

$('#startReading').addEventListener('click', () => enterReader());
$('#backHome').addEventListener('click', () => setHome(true));
$('#homeLibrary').addEventListener('click', () => openLibrary('all'));
$('#homeFeatured').addEventListener('click', () => openLibrary('featured'));
$('#openLibrary').addEventListener('click', () => openLibrary());
$('#retryCatalog').addEventListener('click', init);
$('#openSettings').addEventListener('click', () => { applySettings(); $('#settings').showModal(); });
$('#manageFavorites').addEventListener('click', () => { $('#settings').close(); openLibrary('favorites'); });
$('#revealControls').addEventListener('click', () => { setControls(true); $('#openLibrary').focus(); });
$('#previousPoem').addEventListener('click', () => goTo(currentIndex - 1));
$('#nextPoem').addEventListener('click', () => goTo(currentIndex + 1));
$('#favoriteButton').addEventListener('click', () => {
  const id = poems[currentIndex]?.id; if (!id) return;
  if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
  storage.write(keys.favorites, [...favorites]); updateState();
  $('#readerStatus').textContent = favorites.has(id) ? '已收藏' : '已取消收藏';
});
$('#toggleNotes').addEventListener('click', () => changeSetting('notes', !settings.notes));
$('#settingNotes').addEventListener('change', event => changeSetting('notes', event.target.checked));
$('#fontSize').addEventListener('change', event => changeSetting('fontSize', Number(event.target.value)));
for (const input of document.querySelectorAll('[name="paper"]')) input.addEventListener('change', () => changeSetting('paper', input.value));
for (const button of document.querySelectorAll('[data-close]')) button.addEventListener('click', () => $(`#${button.dataset.close}`).close());
for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
$('#searchInput').addEventListener('input', event => { filters.query = event.target.value; renderLibrary(); });
$('#categorySelect').addEventListener('change', event => { filters.category = event.target.value; renderLibrary(); });
$('.collection-row').addEventListener('click', event => { const button = event.target.closest('[data-collection]'); if (button) { filters.collection = button.dataset.collection; renderLibrary(); } });
$('#poemList').addEventListener('click', event => { const row = event.target.closest('[data-id]'); if (row) { $('#library').close(); enterReader(poems.findIndex(poem => poem.id === row.dataset.id)); } });
let pointerStart;
pages.addEventListener('pointerdown', event => { pointerStart = [event.clientX, event.clientY]; });
pages.addEventListener('click', event => {
  const retry = event.target.closest('[data-retry]'); if (retry) { void mountPage(Number(retry.dataset.retry)); return; }
  const notes = event.target.closest('[data-notes]'); if (notes) { void openNotes(notes.dataset.notes); return; }
  if (event.target.closest('button') || window.getSelection()?.toString()) return;
  if (!pointerStart || Math.hypot(event.clientX - pointerStart[0], event.clientY - pointerStart[1]) < 10) setControls(!controlsVisible);
});
let frame;
pages.addEventListener('scroll', () => {
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() => {
    if (homeVisible || !poems.length) return;
    if (pages.clientWidth !== alignedWidth) { alignPage(); return; }
    const index = Math.max(0, Math.min(poems.length - 1, Math.round(pages.scrollLeft / pages.clientWidth)));
    if (index !== currentIndex) { currentIndex = index; updateState(); }
  });
}, { passive: true });
window.addEventListener('keydown', event => {
  if (homeVisible || document.querySelector('dialog[open]') || event.target.matches('input, select, textarea')) return;
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); goTo(currentIndex + (event.key === 'ArrowRight' ? 1 : -1)); }
  if (event.key === 'Escape') { setControls(true); $('#openLibrary').focus(); }
});
new ResizeObserver(() => { if (poems.length) { alignPage(); layoutMountedPages(); } }).observe(pages);
document.fonts.ready.then(layoutMountedPages);
applySettings();
void init();
