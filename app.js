import { setupReadingExtras } from './reader-extras.js?v=0.6.12';
import { setupNarration } from './reader-narration.js?v=0.6.13';
import { setupCoverAtmosphere } from './reader-cover.js?v=0.6.11';
import { parseStored, sanitizeSettings, migrateFavorites, filterPoems, initialIndex, createPoemLoader } from './reader-core.js?v=0.6.11';

import { escapeHTML, layoutReadingPage, poemMarkup, notesMarkup, directoryArtworkMarkup } from './reader-renderer.js?v=0.6.11';
import { ALL_POEMS, sanitizeReadingScope, isAllPoems, readingScopeLabel, selectionAfterScopeChange, sanitizeReadingProgress, captureParagraphProgress, restoreParagraphProgress, paragraphMetrics, isReadingSurfaceTap } from './reader-continuity.js?v=0.6.11';

import { ReadingSession, sanitizeReadIDs, restoreReadingSequence, readingSurfaceCountsTime } from './reader-history.js?v=0.6.14';

import { createReadingIdle } from './reader-controls.js?v=0.6.11';

const $ = selector => document.querySelector(selector);
const keys = { read: 'tang-read-ids-v1', sequence: 'tang-reading-sequence-v1', favorites: 'tang-favorites-v2', settings: 'tang-settings-v1', position: 'tang-position-v1', scope: 'tang-reading-scope-v1', progress: 'tang-reading-progress-v1' };
const storage = {
  read(key, fallback) { try { return parseStored(localStorage.getItem(key), fallback); } catch { return fallback; } },
  write(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { $('#storageNotice').hidden = false; $('#storageNotice').textContent = '当前浏览器无法保存记录，本次阅读仍可正常使用。'; } }
};
const pages = $('#pages');
const settings = sanitizeSettings(storage.read(keys.settings, null));
let catalogPoems = [], poems = [], favorites = new Set(), currentIndex = 0, homeVisible = true, controlsVisible = true;
let filters = { ...ALL_POEMS }, readingScope = { ...ALL_POEMS }, readingProgress = {};
let shells = [], activeIDs = new Set(), loading = false, lastSavedID = '', alignedWidth = 0;
let progressTimer, restoringProgress = false;
let readIDs = new Set();
const readSession = new ReadingSession();
const pageDetails = new WeakMap();
let extras;
let pointerHeld = false, keyboardNavigation = false;
const idleControls = createReadingIdle({
  hide: () => setControls(false),
  canHide: () => controlsVisible && !homeVisible && !document.hidden && !pointerHeld &&
    !document.querySelector('dialog[open]') && !keyboardNavigation && !window.getSelection()?.toString()
});
const narration = setupNarration(() => poems[currentIndex], openPoem, sampleRead);
setupCoverAtmosphere();

async function fetchJSON(url) {
  const response = await fetch(url, { cache: 'no-cache', signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
const loader = createPoemLoader(id => fetchJSON(`./data/reader/poems/${encodeURIComponent(id)}.json`));

function sampleRead() {
  const element = shells[currentIndex], body = element?.querySelector('.poem-body');
  const lastLine = body?.querySelector('.verse-line:last-child');
  const id = poems[currentIndex]?.id;
  const surface = homeVisible || document.querySelector('dialog[open]:not(#narrationDialog)') ? 'covered'
    : $('#narrationDialog').open ? 'narration' : 'poem';
  const countsTime = readingSurfaceCountsTime({ foreground: !document.hidden && document.hasFocus(), surface,
    currentNarrationPlaying: narration.isCurrentPlaying() });
  const active = Boolean(id && body && lastLine && countsTime && !readIDs.has(id) &&
    Math.abs(pages.scrollLeft - currentIndex * pages.clientWidth) < 2);
  const endVisible = active && lastLine.getBoundingClientRect().bottom <= body.getBoundingClientRect().bottom + 2 &&
    lastLine.getBoundingClientRect().bottom > body.getBoundingClientRect().top;
  if (readSession.sample({ id, section: poems[currentIndex]?.section, active, endVisible, now: performance.now() / 1000 })) setPoemRead(id, true, false);
}
function setPoemRead(id, value, manual = true) {
  if (!catalogPoems.some(poem => poem.id === id)) return;
  if (manual) readSession.suppress(id);
  // Apply just this change to the latest receipts, retaining changes from another tab.
  readIDs = sanitizeReadIDs(storage.read(keys.read, [...readIDs]), catalogPoems);
  if (value) readIDs.add(id); else readIDs.delete(id);
  storage.write(keys.read, [...readIDs]);
  if ($('#library').open) renderLibrary();
}
setInterval(sampleRead, 1000);
window.addEventListener('storage', event => {
  if (event.key !== keys.read || !catalogPoems.length) return;
  const next = sanitizeReadIDs(storage.read(keys.read, []), catalogPoems);
  if (readIDs.has(poems[currentIndex]?.id) && !next.has(poems[currentIndex]?.id)) readSession.suppress(poems[currentIndex]?.id);
  readIDs = next;
  if ($('#library').open) renderLibrary();
});

function applySettings() {
  rememberCurrentParagraph();
  document.body.dataset.paper = settings.paper;
  $('.reader').style.setProperty('--reader-size', `${settings.fontSize}px`);
  pages.classList.toggle('notes-off', !settings.notes);
  $('#toggleNotes').setAttribute('aria-pressed', settings.notes);
  $('#settingNotes').checked = settings.notes;
  $('#fontSize').value = settings.fontSize;
  document.querySelectorAll('[name="paper"]').forEach(input => { input.checked = input.value === settings.paper; });
  layoutMountedPages({ remember: false });
}
function changeSetting(key, value) {
  settings[key] = value;
  if (key === 'notes') {
    pages.classList.toggle('notes-off', !settings.notes);
    $('#toggleNotes').setAttribute('aria-pressed', settings.notes);
    $('#settingNotes').checked = settings.notes;
  } else applySettings();
  storage.write(keys.settings, settings);
}

function setControls(visible) {
  controlsVisible = visible;
  for (const element of [$('#topbar'), $('#bottombar')]) { element.dataset.visible = visible; element.inert = !visible; }
  $('#compactListening').hidden = visible;
  idleControls.activity();
}
function setHome(visible) {
  if (visible) saveReadingProgress();
  if (homeVisible !== visible) readSession.reset();
  homeVisible = visible;
  sampleRead();
  idleControls.activity();
  $('.reader').dataset.home = visible;
  $('#homeScreen').inert = !visible;
  $('#homeScreen').setAttribute('aria-hidden', !visible);
  $('#readingSurface').inert = visible;
  $('#readingSurface').setAttribute('aria-hidden', visible);
  if (visible) { $('#startReading').textContent = currentIndex ? '续读' : '入卷'; $('#startReading').focus(); }
}

function layoutPage(element) {
  layoutReadingPage(element, pageDetails.get(element), { width: pages.clientWidth, height: pages.clientHeight, fontSize: settings.fontSize, notesEnabled: settings.notes });
}
function layoutMountedPages({ remember = true } = {}) {
  if (remember) rememberCurrentParagraph();
  for (const element of shells) if (element.childNodes.length) layoutPage(element);
  restorePageParagraph(shells[currentIndex]);
}

function rememberCurrentParagraph() {
  const element = shells[currentIndex], body = element?.querySelector('.poem-body');
  if (!body || restoringProgress || homeVisible) return;
  const metrics = paragraphMetrics(body);
  readingProgress[element.dataset.id] = captureParagraphProgress(body.scrollTop, metrics.anchors, metrics.scrollHeight, metrics.clientHeight);
}
function saveReadingProgress() {
  clearTimeout(progressTimer);
  rememberCurrentParagraph();
  storage.write(keys.progress, readingProgress);
}
function restorePageParagraph(element) {
  const body = element?.querySelector('.poem-body'), position = readingProgress[element?.dataset.id];
  if (!body || !position) return;
  const metrics = paragraphMetrics(body);
  restoringProgress = true;
  body.scrollTop = restoreParagraphProgress(position, metrics.anchors, metrics.scrollHeight, metrics.clientHeight);
  restoringProgress = false;
}
function renderPage(element, poem, detail) {
  pageDetails.set(element, { ...detail, section: poem.section });
  element.innerHTML = poemMarkup(poem, detail);
  const image = element.querySelector('img');
  image.addEventListener('error', () => image.remove(), { once: true });
  layoutPage(element);
  restorePageParagraph(element);
  element.querySelector('.poem-body').addEventListener('scroll', () => {
    if (element !== shells[currentIndex] || homeVisible || restoringProgress) return;
    idleControls.activity();
    sampleRead();
    rememberCurrentParagraph();
    clearTimeout(progressTimer);
    progressTimer = setTimeout(saveReadingProgress, 300);
  }, { passive: true });
  extras?.update();
}
async function mountPage(index) {
  const poem = poems[index], element = shells[index];
  if (!poem || element.dataset.loaded || element.dataset.loading) return;
  element.dataset.loading = 'true';
  element.innerHTML = '<p class="page-message">展卷中…</p>';
  try {
    const detail = await loader.load(poem.id);
    if (!activeIDs.has(poem.id) || shells[index] !== element) return;
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
  narration.update();
  sampleRead();
  const poem = poems[currentIndex];
  if (!poem) return;
  $('#pageMark').textContent = `${currentIndex + 1} / ${poems.length}`;
  $('#scopeLabel').textContent = readingScopeLabel(readingScope);
  $('#scopeLabel').hidden = isAllPoems(readingScope);
  $('#leaveReadingScope').hidden = isAllPoems(readingScope);
  $('#leaveReadingScope').setAttribute('aria-label', `正在阅读${readingScopeLabel(readingScope)}，返回全库并保留当前诗`);
  $('#favoriteButton').setAttribute('aria-pressed', favorites.has(poem.id));
  $('#favoriteButton').setAttribute('aria-label', favorites.has(poem.id) ? '取消收藏此诗' : '收藏此诗');
  $('#previousPoem').disabled = currentIndex === 0;
  $('#nextPoem').disabled = currentIndex === poems.length - 1;
  $('#favoriteCount').textContent = `${favorites.size} 首 ›`;
  if (!homeVisible && poem.id !== lastSavedID) { storage.write(keys.position, poem.id); lastSavedID = poem.id; }
  if (announce) $('#readerStatus').textContent = `${poem.title}，${poem.author}。第 ${currentIndex + 1} 首，共 ${poems.length} 首。`;
  hydrateWindow();
  extras?.update();
}
function goTo(index) {
  if (!poems.length) return;
  saveReadingProgress();
  currentIndex = Math.max(0, Math.min(poems.length - 1, index));
  // Directory jumps are immediate: no traversal or loading of hundreds of intervening pages.
  alignPage();
  updateState({ announce: true });
  idleControls.activity();
}
function alignPage() {
  alignedWidth = pages.clientWidth;
  pages.scrollTo({ left: currentIndex * alignedWidth, behavior: 'instant' });
}
function enterReader(index = currentIndex) { setHome(false); setControls(true); goTo(index); pages.focus({ preventScroll: true }); }

function rebuildPages() {
  shells = poems.map(poem => { const element = document.createElement('article'); element.className = 'poem-page'; element.dataset.id = poem.id; element.setAttribute('aria-label', poem.title); return element; });
  pages.replaceChildren(...shells);
}
// A filtered directory becomes the actual previous/next/swipe sequence.
function openReadingScope(value = ALL_POEMS, selectedID = poems[currentIndex]?.id) {
  saveReadingProgress();
  let nextScope = sanitizeReadingScope(value);
  let result = filterPoems(catalogPoems, nextScope, favorites, readIDs);
  const empty = !result.length;
  if (empty) {
    nextScope = { ...ALL_POEMS }; result = catalogPoems;
  }
  const nextIndex = selectionAfterScopeChange(currentIndex, selectedID, result);
  readingScope = nextScope; poems = result; currentIndex = nextIndex;
  readSession.reset();
  storage.write(keys.sequence, readingScope.readStatus === 'all' ? null : result.map(poem => poem.id));
  filters = { ...readingScope }; $('#searchInput').value = filters.query;
  storage.write(keys.scope, readingScope);
  rebuildPages();
  enterReader(currentIndex);
  if (empty) $('#readerStatus').textContent = '这个诗集已没有诗，已回到全库。';
}
// Sharing and the daily poem can open one stable ID without inheriting stale filters.
function openPoem(id, { scope = 'all' } = {}) {
  if (!catalogPoems.some(poem => poem.id === id)) return;
  openReadingScope(scope === 'all' ? ALL_POEMS : scope, id);
}

function renderLibrary() {
  extras?.updateRecommendations();
  const list = filterPoems(catalogPoems, filters, favorites, readIDs);
  const groups = new Map();
  for (const poem of list) {
    if (!groups.has(poem.section)) groups.set(poem.section, []);
    groups.get(poem.section).push(poem);
  }
  $('#resultCount').textContent = `${list.length} 首${filters.collection === 'favorites' ? '收藏' : ''}`;
  $('#readingTotal').textContent = `已读 ${readIDs.size} / ${catalogPoems.length} 首`;
  $('#readStatusFilter').value = filters.readStatus;
  $('#recommendationHint').hidden = filters.collection !== 'featured';
  $('#recommendationHint').textContent = `先从这 ${catalogPoems.filter(poem => poem.featured).length} 首读起`;
  $('#categorySelect').value = filters.category;
  $('#authorSelect').value = filters.author;
  document.querySelectorAll('[data-collection]').forEach(button => button.setAttribute('aria-pressed', button.dataset.collection === filters.collection));
  let thumbnailIndex = 0;
  $('#poemList').innerHTML = list.length ? [...groups].map(([section, items]) => `<section class="genre-group" aria-label="${escapeHTML(section)}"><h3 class="genre-heading">${escapeHTML(section)}<span>${items.length} 首</span></h3>${items.map(poem => `<div class="poem-row-wrap"><button class="poem-row" data-id="${poem.id}" aria-current="${poem.id === poems[currentIndex]?.id}">${directoryArtworkMarkup(poem, thumbnailIndex++ < 12)}<span class="poem-row-copy"><strong>${escapeHTML(poem.title)}</strong><small>${escapeHTML(poem.author)}</small></span><em>${favorites.has(poem.id) ? '已藏' : ''}</em></button><button class="read-toggle" data-read-id="${poem.id}" aria-label="将《${escapeHTML(poem.title)}》标为${readIDs.has(poem.id) ? '未读' : '已读'}" title="标为${readIDs.has(poem.id) ? '未读' : '已读'}">${readIDs.has(poem.id) ? '✓ 已读' : '标已读'}</button></div>`).join('')}</section>`).join('')
    : `<p class="empty-state">${filters.collection === 'favorites' && !favorites.size ? '还没有收藏。<br>在喜欢的诗页轻点「藏」，留给下次重读。' : '没有找到相符的诗。<br>试试其他诗句，或切换分类。'}</p>`;
}
function openLibrary(collection) {
  if (collection) { filters = { ...ALL_POEMS, collection }; $('#searchInput').value = ''; }
  $('#libraryReadNotice').textContent = '';
  renderLibrary(); $('#library').showModal();
}
async function openNotes(id) {
  try {
    const poem = await loader.load(id);
    $('#notesTitle').textContent = poem.title;
    $('#fullNotes').innerHTML = notesMarkup(poem);
    $('#notesDialog').showModal();
  } catch { $('#readerStatus').textContent = '注释暂时无法打开，请稍后重试。'; }
}

async function init() {
  if (loading) return;
  loading = true; $('#retryCatalog').hidden = true; $('#homeStatus').textContent = '';
  try {
    const catalog = await fetchJSON('./data/reader/catalog.json');
    if (!Array.isArray(catalog.poems) || !catalog.poems.length) throw new Error('Empty catalog');
    catalogPoems = catalog.poems;
    favorites = migrateFavorites(storage.read(keys.favorites, null), storage.read('tang-favorites', []), catalogPoems);
    storage.write(keys.favorites, [...favorites]);
    readIDs = sanitizeReadIDs(storage.read(keys.read, []), catalogPoems);
    readingProgress = sanitizeReadingProgress(storage.read(keys.progress, null), catalogPoems);
    const linkedPoem = location.hash.startsWith('#p=') || location.hash.startsWith('#poem=');
    readingScope = linkedPoem ? { ...ALL_POEMS } : sanitizeReadingScope(storage.read(keys.scope, null));
    const restoredSequence = readingScope.readStatus !== 'all' && !linkedPoem
      ? restoreReadingSequence(storage.read(keys.sequence, null), filterPoems(catalogPoems, { ...readingScope, readStatus: 'all' }, favorites, readIDs)) : null;
    poems = restoredSequence || filterPoems(catalogPoems, readingScope, favorites, readIDs);
    if (!poems.length) { poems = catalogPoems; readingScope = { ...ALL_POEMS }; }
    filters = { ...readingScope }; $('#searchInput').value = filters.query;
    currentIndex = initialIndex(poems, storage.read(keys.position, ''), location.hash);
    rebuildPages();
    const themes = [...new Set(catalogPoems.map(p => p.theme))];
    const sections = [...new Set(catalogPoems.map(p => p.section))];
    $('#categorySelect').innerHTML = `<option value="all">全部分类</option><optgroup label="体裁">${sections.map(value => `<option>${escapeHTML(value)}</option>`).join('')}</optgroup><optgroup label="主题">${themes.map(value => `<option>${escapeHTML(value)}</option>`).join('')}</optgroup>`;
    const authorCounts = new Map();
    for (const poem of catalogPoems) authorCounts.set(poem.author, (authorCounts.get(poem.author) || 0) + 1);
    $('#authorSelect').innerHTML = `<option value="all">全部作者</option>${[...authorCounts].sort(([a], [b]) => a.localeCompare(b, 'zh-Hans-CN')).map(([author, count]) => `<option value="${escapeHTML(author)}">${escapeHTML(author)} · ${count} 首</option>`).join('')}`;
    $('#homeCount').textContent = `${catalogPoems.length} 首 · ${catalogPoems.filter(p => p.dedicatedArt).length} 幅画笺`;
    for (const id of ['startReading', 'homeLibrary', 'homeFeatured']) $(`#${id}`).disabled = false;
    $('#startReading').textContent = currentIndex ? '续读' : '入卷';
    if (!extras) extras = setupReadingExtras({
      getCatalog: () => catalogPoems, getCurrentPoem: () => poems[currentIndex],
      loadPoem: id => loader.load(id), openPoem: id => openPoem(id),
      showDailyRecommendation: () => filters.collection === 'featured' && !filters.query.trim()
        && filters.category === 'all' && filters.author === 'all' && filters.readStatus === 'all',
      notice: message => { $('#readerStatus').textContent = message; }
    });
    updateState();
    if (linkedPoem) {
      enterReader();
      // A shared link is an entry point. Later reloads resume the user's new position.
      history.replaceState(null, '', `${location.pathname}${location.search}`);
      storage.write(keys.scope, readingScope);
    }
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
$('#previousPoem').addEventListener('click', () => goTo(currentIndex - 1));
$('#nextPoem').addEventListener('click', () => goTo(currentIndex + 1));
$('#leaveReadingScope').addEventListener('click', () => openReadingScope(ALL_POEMS));
$('#favoriteButton').addEventListener('click', () => {
  const id = poems[currentIndex]?.id; if (!id) return;
  if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
  storage.write(keys.favorites, [...favorites]);
  const wasFavoriteScope = readingScope.collection === 'favorites';
  if (wasFavoriteScope) openReadingScope(readingScope, id);
  else updateState();
  $('#readerStatus').textContent = favorites.has(id) ? '已收藏' : wasFavoriteScope && isAllPoems(readingScope) ? '已取消收藏，当前诗集已空，已回到全库。' : '已取消收藏';
});
$('#toggleNotes').addEventListener('click', () => changeSetting('notes', !settings.notes));
$('#settingNotes').addEventListener('change', event => changeSetting('notes', event.target.checked));
$('#fontSize').addEventListener('change', event => changeSetting('fontSize', Number(event.target.value)));
for (const input of document.querySelectorAll('[name="paper"]')) input.addEventListener('change', () => changeSetting('paper', input.value));
for (const button of document.querySelectorAll('[data-close]')) button.addEventListener('click', () => $(`#${button.dataset.close}`).close());
for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
$('#searchInput').addEventListener('input', event => { filters.query = event.target.value; renderLibrary(); });
$('#categorySelect').addEventListener('change', event => { filters.category = event.target.value; renderLibrary(); });
$('#authorSelect').addEventListener('change', event => { filters.author = event.target.value; renderLibrary(); });
$('#readStatusFilter').addEventListener('change', event => { filters.readStatus = event.target.value; renderLibrary(); });
$('.collection-row').addEventListener('click', event => { const button = event.target.closest('[data-collection]'); if (button) { filters.collection = button.dataset.collection; renderLibrary(); } });
$('#poemList').addEventListener('click', event => {
  const toggle = event.target.closest('[data-read-id]');
  if (toggle) {
    const id = toggle.dataset.readId, value = !readIDs.has(id);
    const title = catalogPoems.find(poem => poem.id === id)?.title;
    setPoemRead(id, value);
    $('#libraryReadNotice').textContent = `已将《${title}》标为${value ? '已读' : '未读'}`;
    ($(`[data-read-id="${id}"]`) || $('#readStatusFilter')).focus({ preventScroll: true });
    return;
  }
  const row = event.target.closest('[data-id]');
  if (row) { $('#library').close(); openReadingScope(filters, row.dataset.id); }
});
for (const dialog of document.querySelectorAll('dialog')) {
  new MutationObserver(() => {
    sampleRead();
    if (dialog.open) setControls(true);
    else idleControls.activity();
  }).observe(dialog, { attributes: true, attributeFilter: ['open'] });
}
document.addEventListener('pointerdown', () => {
  keyboardNavigation = false;
  pointerHeld = true;
  idleControls.cancel();
}, { passive: true });
for (const event of ['pointerup', 'pointercancel']) document.addEventListener(event, () => {
  pointerHeld = false;
  idleControls.activity();
}, { passive: true });
document.addEventListener('keydown', event => {
  keyboardNavigation = true;
  if (!homeVisible && (event.key === 'Tab' || event.key === 'Escape')) setControls(true);
  else idleControls.cancel();
});
document.addEventListener('click', () => idleControls.activity());
document.addEventListener('selectionchange', () => idleControls.activity());
document.addEventListener('visibilitychange', () => {
  pointerHeld = false;
  sampleRead();
  if (document.hidden) idleControls.cancel();
  else if (!homeVisible) setControls(true);
});
window.addEventListener('blur', () => { pointerHeld = false; idleControls.cancel(); sampleRead(); });
window.addEventListener('focus', () => { idleControls.activity(); sampleRead(); });
let pointerStart, pointerCancelled = false;
pages.addEventListener('pointerdown', event => { pointerStart = { x: event.clientX, y: event.clientY }; pointerCancelled = !event.isPrimary; }, { passive: true });
pages.addEventListener('pointermove', event => {
  if (pointerStart && Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) >= 10) pointerCancelled = true;
}, { passive: true });
pages.addEventListener('pointercancel', () => { pointerCancelled = true; });
pages.addEventListener('click', event => {
  const retry = event.target.closest('[data-retry]'); if (retry) { void mountPage(Number(retry.dataset.retry)); return; }
  const notes = event.target.closest('[data-notes]'); if (notes) { void openNotes(notes.dataset.notes); return; }
  const interactive = Boolean(event.target.closest('button, a, input, select, textarea, [role="button"]'));
  if (isReadingSurfaceTap({ start: pointerStart, end: { x: event.clientX, y: event.clientY }, cancelled: pointerCancelled, interactive, selection: window.getSelection()?.toString() })) setControls(!controlsVisible);
  pointerStart = null;
});
let frame;
pages.addEventListener('scroll', () => {
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() => {
    if (homeVisible || !poems.length) return;
    if (pages.clientWidth !== alignedWidth) { alignPage(); return; }
    const index = Math.max(0, Math.min(poems.length - 1, Math.round(pages.scrollLeft / pages.clientWidth)));
    if (index !== currentIndex) { saveReadingProgress(); currentIndex = index; updateState(); idleControls.activity(); }
  });
}, { passive: true });
window.addEventListener('keydown', event => {
  if (homeVisible || document.querySelector('dialog[open]') || event.target.matches('input, select, textarea')) return;
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); goTo(currentIndex + (event.key === 'ArrowRight' ? 1 : -1)); }
  if (event.key === 'Escape') { setControls(true); $('#openLibrary').focus(); }
});
new ResizeObserver(() => { if (poems.length) { alignPage(); layoutMountedPages({ remember: false }); } }).observe(pages);
document.fonts.ready.then(layoutMountedPages);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') saveReadingProgress(); });
window.addEventListener('pagehide', saveReadingProgress);
window.addEventListener('hashchange', () => {
  if (!catalogPoems.length) return;
  if (location.hash.startsWith('#p=') || location.hash.startsWith('#poem=')) {
    openPoem(catalogPoems[initialIndex(catalogPoems, '', location.hash)].id);
    history.replaceState(null, '', `${location.pathname}${location.search}`);
  } else if (location.hash === '#library' && !$('#library').open) openLibrary('all');
});
applySettings();
void init();
