const $ = id => document.getElementById(id);
const embeddedElement = document.getElementById('auditionData');
const embedded = embeddedElement ? JSON.parse(embeddedElement.textContent) : null;
const rootURL = new URL(embedded ? './' : '../', import.meta.url);
const localURL = path => new URL(path, rootURL).href;
const state = { poems: [], filtered: [], tracks: {}, current: null, sequence: 0, manifestMessage: '', audioKey: '' };
const detailCache = new Map();
const validID = id => typeof id === 'string' && /^[a-z0-9][a-z0-9-]*$/.test(id);
const ready = poem => Boolean(poem && Object.hasOwn(state.tracks, poem.id));
const durationText = seconds => {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return '';
  return `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}`;
};

async function json(path) {
  if (embedded) {
    if (path === 'data/reader-volume-2/catalog.json') return embedded.catalog;
    if (path === 'output/audio-azure-volume-2/manifest.json') return embedded.manifest;
    const identity = path.match(/^data\/reader-volume-2\/poems\/([a-z0-9-]+)\.json$/)?.[1];
    if (identity && embedded.details[identity]) return embedded.details[identity];
    throw new Error('离线包内没有这份资料');
  }
  const response = await fetch(localURL(path), { cache: 'no-store' });
  if (!response.ok) {
    const error = new Error(`资料载入失败（${response.status}）`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function stopAudio() {
  const audio = $('audio');
  audio.pause();
  audio.removeAttribute('src');
  audio.load();
  audio.hidden = true;
  state.audioKey = '';
  $('speed').disabled = true;
}

function updateAudio() {
  const poem = state.current;
  if (!ready(poem)) {
    stopAudio();
    $('trackStatus').textContent = poem ? '本首等待生成朗读音轨。生成后请刷新清单。' : '请选择诗篇。';
    return;
  }
  const track = state.tracks[poem.id];
  const key = `${poem.id}:${track.sha256 || ''}`;
  const audio = $('audio');
  if (state.audioKey !== key) {
    stopAudio();
    // Staging records contain release paths; audition always reads the local generated MP3.
    audio.src = localURL(embedded
      ? embedded.audioFiles[poem.id]
      : `output/audio-azure-volume-2/audio/${encodeURIComponent(poem.id)}.mp3`);
    audio.playbackRate = Number($('speed').value);
    state.audioKey = key;
  }
  audio.hidden = false;
  audio.setAttribute('aria-label', `${poem.title}朗读`);
  $('speed').disabled = false;
  const duration = durationText(track.duration);
  $('trackStatus').textContent = `已生成 · ${duration ? `时长 ${duration} · ` : ''}点击播放试听`;
}

function navigation() {
  const index = state.filtered.findIndex(poem => poem.id === state.current?.id);
  $('previous').disabled = index <= 0;
  $('next').disabled = index < 0 || index >= state.filtered.length - 1;
  $('position').textContent = index < 0 ? '' : `${index + 1} / ${state.filtered.length}`;
}

function renderList() {
  const fragment = document.createDocumentFragment();
  for (const poem of state.filtered) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'audio-item';
    button.dataset.ready = String(ready(poem));
    button.setAttribute('aria-current', String(poem.id === state.current?.id));
    const copy = document.createElement('span');
    const title = document.createElement('span');
    title.className = 'audio-item-title';
    title.textContent = poem.title;
    const meta = document.createElement('span');
    meta.className = 'audio-item-meta';
    meta.textContent = `${poem.author} · ${poem.genre || poem.section}`;
    const badge = document.createElement('span');
    badge.className = 'audio-item-status';
    badge.textContent = ready(poem) ? '可试听' : '等待生成';
    copy.append(title, meta);
    button.append(copy, badge);
    button.addEventListener('click', () => show(poem));
    fragment.append(button);
  }
  $('items').replaceChildren(fragment);
  const readyCount = state.filtered.filter(ready).length;
  $('resultCount').textContent = state.filtered.length
    ? `${state.filtered.length} 首 · ${readyCount} 首可试听`
    : ($('scope').value === 'ready' && !$('search').value.trim() ? '尚无已生成音轨。' : '没有匹配的诗篇。');
  navigation();
}

async function show(poem) {
  const sequence = ++state.sequence;
  state.current = poem;
  $('poemTitle').textContent = poem.title;
  $('poemIndex').textContent = `第二卷 · ${String(poem.order).padStart(3, '0')}`;
  $('poemMeta').textContent = `${poem.dynasty} · ${poem.author} · ${poem.genre || poem.section}`;
  $('poemText').textContent = '载入诗文…';
  $('poem').setAttribute('aria-busy', 'true');
  document.title = `${poem.title} · 第二卷朗读试听`;
  history.replaceState(null, '', `#${encodeURIComponent(poem.id)}`);
  renderList();
  updateAudio();
  try {
    let detail = detailCache.get(poem.id);
    if (!detail) {
      detail = await json(`data/reader-volume-2/poems/${encodeURIComponent(poem.id)}.json`);
      detailCache.set(poem.id, detail);
    }
    if (sequence !== state.sequence) return;
    const lines = Array.isArray(detail.rubyLines)
      ? detail.rubyLines.map(line => line.map(token => token[0]).join('')).join('\n')
      : (detail.readingText || detail.text || '');
    $('poemText').textContent = lines || '暂无诗文。';
  } catch {
    if (sequence !== state.sequence) return;
    $('poemText').textContent = '诗文载入失败，请重新选择本首。';
  } finally {
    if (sequence === state.sequence) $('poem').setAttribute('aria-busy', 'false');
  }
}

function filter() {
  const query = $('search').value.trim().toLocaleLowerCase();
  state.filtered = state.poems.filter(poem => {
    if ($('scope').value === 'ready' && !ready(poem)) return false;
    const text = `${poem.title} ${poem.author} ${(poem.aliases || []).join(' ')} ${poem.searchText || ''}`.toLocaleLowerCase();
    return !query || text.includes(query);
  });
  if (!state.filtered.length) {
    ++state.sequence;
    state.current = null;
    stopAudio();
    $('poem').setAttribute('aria-busy', 'false');
    $('poemIndex').textContent = '';
    $('poemTitle').textContent = '请选择诗篇';
    $('poemMeta').textContent = '';
    $('poemText').textContent = $('scope').value === 'ready' ? '生成音轨后，刷新清单即可开始试听。' : '可以搜索诗题、作者或诗句。';
    $('trackStatus').textContent = '暂无匹配的音轨。';
    renderList();
    return;
  }
  if (!state.filtered.some(poem => poem.id === state.current?.id)) show(state.filtered[0]);
  else renderList();
}

async function refresh() {
  $('refresh').disabled = true;
  try {
    const manifest = await json('output/audio-azure-volume-2/manifest.json');
    if (manifest.volume !== 'volume-2' || !manifest.tracks || Array.isArray(manifest.tracks) || typeof manifest.tracks !== 'object') {
      throw new Error('音轨清单格式不符');
    }
    state.tracks = {};
    for (const poem of state.poems) {
      const track = manifest.tracks[poem.id];
      if (track && typeof track === 'object' && track.id === poem.id) state.tracks[poem.id] = track;
    }
    const count = Object.keys(state.tracks).length;
    state.manifestMessage = count
      ? `${count} / ${state.poems.length} 首已生成 · ${embedded ? '离线试听包' : '晓晓诗歌朗读'}`
      : `0 / ${state.poems.length} 首已生成 · 等待生成朗读音轨`;
  } catch (error) {
    state.tracks = {};
    state.manifestMessage = error.status === 404
      ? `0 / ${state.poems.length} 首已生成 · 等待生成朗读音轨`
      : '音轨清单载入失败，请刷新重试。';
  } finally {
    $('generationStatus').textContent = state.manifestMessage;
    $('refresh').disabled = false;
    filter();
    updateAudio();
  }
}

function turn(offset) {
  const index = state.filtered.findIndex(poem => poem.id === state.current?.id);
  const poem = state.filtered[index + offset];
  if (poem) show(poem);
}

$('search').addEventListener('input', filter);
$('scope').addEventListener('change', filter);
$('refresh').addEventListener('click', refresh);
$('previous').addEventListener('click', () => turn(-1));
$('next').addEventListener('click', () => turn(1));
$('speed').addEventListener('change', () => { $('audio').playbackRate = Number($('speed').value); });
$('audio').addEventListener('error', () => {
  if (!state.audioKey) return;
  state.audioKey = '';
  $('speed').disabled = true;
  $('trackStatus').textContent = embedded
    ? '音轨暂时无法播放，请重新选择本首，并确认离线包的 audio 目录完整。'
    : '音轨暂时无法播放，请刷新清单后重试。';
});
window.addEventListener('pagehide', () => $('audio').pause());

$('refresh').hidden = Boolean(embedded);

try {
  const catalog = await json('data/reader-volume-2/catalog.json');
  if (catalog.volume !== 'volume-2' || !Array.isArray(catalog.poems)) throw new Error('目录格式不符');
  state.poems = catalog.poems.filter(poem => validID(poem.id)).sort((a, b) => a.order - b.order);
  if (!state.poems.length) throw new Error('目录为空');
  state.filtered = state.poems;
  let selectedID = '';
  try { selectedID = decodeURIComponent(location.hash.slice(1)); } catch {}
  await show(state.poems.find(poem => poem.id === selectedID) || state.poems[0]);
  await refresh();
} catch {
  stopAudio();
  $('generationStatus').textContent = embedded
    ? '离线资料载入失败，请重新完整解压试听包。'
    : location.protocol === 'file:'
      ? '请通过本地 HTTP 服务打开此页，以载入目录与音轨。'
      : '第二卷目录载入失败，请刷新页面重试。';
  $('resultCount').textContent = '目录未载入。';
  $('poemTitle').textContent = '资料尚未就绪';
  $('poem').setAttribute('aria-busy', 'false');
  $('trackStatus').textContent = '等待目录和音轨资料。';
}
