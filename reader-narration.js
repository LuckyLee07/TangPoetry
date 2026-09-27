import { createNarrationAutoplay } from './reader-controls.js?v=0.6.4';

/** The web preview shares the native app's generated audio, with no runtime TTS. */
export function isNarrationTrackForPoem(track, poem) {
  if (!track || track.id !== poem.id || !/^[a-z0-9-]+$/.test(poem.id)) return false;
  return track.file === `assets/audio/${poem.id}.mp3` ||
    (/^assets\/audio\/xiaoxiao-poetry-v\d+\/[a-z0-9-]+\.mp3$/.test(track.file) &&
      track.file.endsWith(`/${poem.id}.mp3`));
}

export function narrationGroups(manifest) {
  const groups = new Map();
  for (const id of manifest.trackOrder ?? Object.keys(manifest.tracks)) {
    const track = manifest.tracks[id];
    if (!track) continue;
    const genre = track.section ?? '诗词';
    if (!groups.has(genre)) groups.set(genre, []);
    groups.get(genre).push(track);
  }
  return groups;
}

export function setupNarration(getPoem, openPoem) {
  const button = document.querySelector('#listenPoem');
  const inlineButton = document.querySelector('#inlineNarration');
  const inlineStatus = document.querySelector('#inlineNarrationStatus');
  const dialog = document.querySelector('#narrationDialog');
  const audio = document.querySelector('#narrationAudio');
  const title = document.querySelector('#narrationTitle');
  const byline = document.querySelector('#narrationByline');
  const status = document.querySelector('#narrationStatus');
  const speed = document.querySelector('#narrationSpeed');
  const retry = document.querySelector('#retryNarration');
  const selection = document.querySelector('#narrationSelection');
  let manifestPromise, loadedID, loadingID, request = 0, inlineStarting = false;
  const autoplay = createNarrationAutoplay(audio, {
    canPlay: () => dialog.open && !document.hidden && loadedID === getPoem()?.id,
    blocked: () => { status.textContent = '浏览器暂未允许自动播放，请轻点播放器的播放键。'; }
  });

  function inlineNotice(message = '') {
    inlineStatus.textContent = message;
    inlineStatus.hidden = !message;
  }
  function stop() {
    request += 1;
    loadedID = loadingID = null;
    inlineStarting = false;
    autoplay.cancel();
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    inlineNotice();
  }
  function update() {
    if ((loadedID && loadedID !== getPoem()?.id) || (loadingID && loadingID !== getPoem()?.id)) stop();
    const playing = loadedID === getPoem()?.id && !audio.paused;
    const preparing = Boolean(loadingID || inlineStarting);
    button.textContent = playing ? '听着' : '听诗';
    button.setAttribute('aria-label', playing ? '打开朗读播放器，正在播放' : '朗读这首诗');
    inlineButton.dataset.playing = String(playing);
    inlineButton.setAttribute('aria-busy', preparing);
    inlineButton.setAttribute('aria-label', preparing ? '取消准备朗读' : playing ? '暂停朗读' : '直接朗读这首诗');
  }
  async function load({ present = true } = {}) {
    const poem = getPoem();
    if (!poem) return;
    title.textContent = poem.title;
    byline.textContent = `唐 · ${poem.author}`;
    if (present && !dialog.open) dialog.showModal();
    inlineNotice();
    if (loadedID === poem.id && !audio.error) {
      if (present) autoplay.start();
      return request;
    }
    stop();
    loadingID = poem.id;
    update();
    const revision = request;
    status.textContent = '正在准备朗读…';
    retry.hidden = true;
    try {
      manifestPromise ??= fetch('./data/audio/manifest.json', { signal: AbortSignal.timeout(15000) })
        .then(response => { if (!response.ok) throw new Error('audio catalog'); return response.json(); })
        .catch(error => { manifestPromise = null; throw error; });
      const manifest = await manifestPromise;
      if (request !== revision || getPoem()?.id !== poem.id) return;
      selection.replaceChildren(new Option('选择一首诗', ''));
      for (const [genre, tracks] of narrationGroups(manifest)) {
        const group = document.createElement('optgroup');
        group.label = genre;
        for (const track of tracks) group.append(new Option(`${track.title} · ${track.author}`, track.id));
        selection.append(group);
      }
      const track = manifest.tracks[poem.id];
      audio.hidden = !track;
      speed.closest('label').hidden = !track;
      if (!track) {
        title.textContent = '选一首听诗';
        byline.textContent = '这首音频暂不可用，可以先听其他诗。';
        status.textContent = `AI 朗读 · ${manifest.recipe.voiceLabel}`;
        if (!present) inlineNotice('这首音频暂不可用，可以先听其他诗。');
        return;
      }
      if (!isNarrationTrackForPoem(track, poem)) throw new Error('audio track');
      selection.value = poem.id;
      loadedID = poem.id;
      audio.src = `./${track.file}`;
      audio.playbackRate = Number(speed.value);
      status.textContent = `AI 朗读 · ${manifest.recipe.voiceLabel}`;
      if (present) autoplay.start();
      return revision;
    } catch {
      if (request !== revision) return;
      status.textContent = '音频暂时未能打开，请检查连接后重试。';
      retry.hidden = false;
      if (!present) inlineNotice('暂时无法朗读，请轻点重试。');
    } finally {
      if (request === revision) { loadingID = null; update(); }
    }
  }
  async function toggleInline() {
    if (loadingID || inlineStarting) { stop(); update(); return; }
    if (loadedID === getPoem()?.id && !audio.paused) { audio.pause(); update(); return; }
    // A loaded/paused track plays in the click handler, preserving browser activation.
    const revision = loadedID === getPoem()?.id && !audio.error ? request : await load({ present: false });
    if (revision === undefined || request !== revision || loadedID !== getPoem()?.id || document.hidden) return;
    autoplay.cancel();
    inlineNotice();
    inlineStarting = true;
    update();
    try {
      if (audio.ended) audio.currentTime = 0;
      await audio.play();
    } catch (error) {
      if (request === revision && error.name !== 'AbortError') inlineNotice('暂未开始播放，请再轻点一次。');
    } finally {
      if (request === revision) { inlineStarting = false; update(); }
    }
  }
  function cancelPending() {
    request++;
    autoplay.cancel();
    loadingID = null;
    if (inlineStarting) audio.pause();
    inlineStarting = false;
    update();
  }
  button.addEventListener('click', () => { void load(); });
  inlineButton.addEventListener('click', () => { void toggleInline(); });
  retry.addEventListener('click', () => { stop(); void load(); });
  speed.addEventListener('change', () => { audio.playbackRate = Number(speed.value); });
  selection.addEventListener('change', () => {
    if (!selection.value) return;
    openPoem(selection.value);
    void load();
  });
  dialog.addEventListener('close', cancelPending);
  document.addEventListener('visibilitychange', () => { if (document.hidden) cancelPending(); });
  audio.addEventListener('pointerdown', autoplay.cancel);
  audio.addEventListener('keydown', autoplay.cancel);
  for (const event of ['play', 'pause']) audio.addEventListener(event, autoplay.manualTransport);
  audio.addEventListener('error', () => {
    autoplay.cancel();
    if (!audio.getAttribute('src')) return;
    status.textContent = '音频暂时未能播放，请重试。';
    retry.hidden = false;
    inlineNotice('暂时无法朗读，请轻点重试。');
    update();
  });
  for (const event of ['play', 'pause', 'ended']) audio.addEventListener(event, update);
  window.addEventListener('pagehide', stop);
  return { update };
}
