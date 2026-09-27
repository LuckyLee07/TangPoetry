/** The web preview shares the native app's generated audio, with no runtime TTS. */
export function setupNarration(getPoem, openPoem) {
  const button = document.querySelector('#listenPoem');
  const dialog = document.querySelector('#narrationDialog');
  const audio = document.querySelector('#narrationAudio');
  const title = document.querySelector('#narrationTitle');
  const byline = document.querySelector('#narrationByline');
  const status = document.querySelector('#narrationStatus');
  const speed = document.querySelector('#narrationSpeed');
  const retry = document.querySelector('#retryNarration');
  const selection = document.querySelector('#narrationSelection');
  let manifestPromise, loadedID, request = 0;

  function stop() {
    request += 1;
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    loadedID = null;
  }
  function update() {
    if (loadedID && loadedID !== getPoem()?.id) stop();
    const playing = loadedID === getPoem()?.id && !audio.paused;
    button.textContent = playing ? '听着' : '听诗';
    button.setAttribute('aria-label', playing ? '打开朗读播放器，正在播放' : '朗读这首诗');
  }
  async function load() {
    const poem = getPoem();
    if (!poem) return;
    title.textContent = poem.title;
    byline.textContent = `唐 · ${poem.author}`;
    if (!dialog.open) dialog.showModal();
    if (loadedID === poem.id) return;
    stop();
    const revision = request;
    status.textContent = '正在准备朗读…';
    retry.hidden = true;
    try {
      manifestPromise ??= fetch('./data/audio/manifest.json', { signal: AbortSignal.timeout(15000) })
        .then(response => { if (!response.ok) throw new Error('audio catalog'); return response.json(); })
        .catch(error => { manifestPromise = null; throw error; });
      const manifest = await manifestPromise;
      if (request !== revision || getPoem()?.id !== poem.id) return;
      selection.replaceChildren(new Option('选择一首试听', ''));
      for (const track of Object.values(manifest.tracks)) selection.add(new Option(`${track.title} · ${track.author}`, track.id));
      const track = manifest.tracks[poem.id];
      audio.hidden = !track;
      speed.closest('label').hidden = !track;
      if (!track) {
        title.textContent = '先听五首';
        byline.textContent = '试试声音和节奏，选一首开始。';
        status.textContent = `AI 朗读 · ${manifest.recipe.voiceLabel}`;
        return;
      }
      if (track.id !== poem.id || track.file !== `assets/audio/${poem.id}.mp3`) throw new Error('audio track');
      selection.value = poem.id;
      loadedID = poem.id;
      audio.src = `./${track.file}`;
      audio.playbackRate = Number(speed.value);
      status.textContent = `AI 朗读 · ${manifest.recipe.voiceLabel}`;
    } catch {
      if (request !== revision) return;
      status.textContent = '音频暂时未能打开，请检查连接后重试。';
      retry.hidden = false;
    }
  }
  button.addEventListener('click', load);
  retry.addEventListener('click', () => { stop(); void load(); });
  speed.addEventListener('change', () => { audio.playbackRate = Number(speed.value); });
  selection.addEventListener('change', () => {
    if (!selection.value) return;
    openPoem(selection.value);
    void load();
  });
  audio.addEventListener('error', () => {
    if (!audio.getAttribute('src')) return;
    status.textContent = '音频暂时未能播放，请重试。';
    retry.hidden = false;
    update();
  });
  for (const event of ['play', 'pause', 'ended']) audio.addEventListener(event, update);
  window.addEventListener('pagehide', stop);
  return { update };
}
