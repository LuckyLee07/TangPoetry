// Optional features stay out of the poem's typography and reading position.
export function dailyPoem(poems, date = new Date()) {
  if (!poems.length || !Number.isFinite(date.getTime())) return null;
  const day = Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86400000);
  const ordered = [...poems].sort((a, b) => a.order - b.order);
  return ordered[((day * 73 + 17) % ordered.length + ordered.length) % ordered.length];
}

export function wrapCardText(text, measure, width) {
  const lines = []; let current = '';
  for (const character of [...text]) {
    const trial = current + character;
    if (current && measure(trial) > width) {
      const characters = [...current];
      if (/\p{Punctuation}/u.test(character) && characters.length > 1) {
        const last = characters.pop(); lines.push(characters.join('')); current = last + character;
      } else { lines.push(current); current = character; }
    } else current = trial;
  }
  if (current) lines.push(current);
  return lines;
}

export async function makePoemCard(poem, detail) {
  await document.fonts.ready;
  const image = new Image(); image.src = `./${poem.image}`; await image.decode();
  const canvas = document.createElement('canvas'); canvas.width = 1080;
  let ctx = canvas.getContext('2d');
  const family = '"Songti SC", "STSong", "Noto Serif SC", serif';
  ctx.font = `64px ${family}`;
  const titleLines = wrapCardText(poem.title, text => ctx.measureText(text).width, 880);
  const sourceLines = detail.rubyLines.map(line => line.map(([text]) => text).join(''));
  const size = sourceLines.length > 12 ? 48 : Math.max(...sourceLines.map(text => [...text].length)) <= 6 ? 72 : 64;
  ctx.font = `${size}px ${family}`;
  const lines = sourceLines.flatMap(line => wrapCardText(line, text => ctx.measureText(text).width, 872));
  const start = 740 + titleLines.length * 86 + 114, leading = size * 1.75;
  canvas.height = Math.ceil(Math.max(1620, start + lines.length * leading + 160));
  ctx = canvas.getContext('2d');
  ctx.fillStyle = '#f6f1e6'; ctx.fillRect(0, 0, 1080, canvas.height);
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, 1080, 740); ctx.clip();
  ctx.drawImage(image, 0, 0, 1080, image.naturalHeight / image.naturalWidth * 1080);
  const gradient = ctx.createLinearGradient(0, 530, 0, 740);
  gradient.addColorStop(0, '#f6f1e600'); gradient.addColorStop(1, '#f6f1e6');
  ctx.fillStyle = gradient; ctx.fillRect(0, 530, 1080, 210); ctx.restore();
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  ctx.fillStyle = '#302b23'; ctx.font = `64px ${family}`;
  titleLines.forEach((line, index) => ctx.fillText(line, 540, 740 + index * 86));
  ctx.fillStyle = '#716b5c'; ctx.font = '30px sans-serif';
  ctx.fillText(`${poem.dynasty || '唐'} · ${poem.author}`, 540, 740 + titleLines.length * 86 + 12);
  ctx.fillStyle = '#302b23'; ctx.font = `${size}px ${family}`;
  lines.forEach((line, index) => ctx.fillText(line, 540, start + index * leading));
  ctx.strokeStyle = '#716b5c40'; ctx.beginPath(); ctx.moveTo(440, canvas.height - 112); ctx.lineTo(640, canvas.height - 112); ctx.stroke();
  ctx.fillStyle = '#716b5c'; ctx.font = '25px sans-serif'; ctx.fillText('唐诗画笺 · 一页一诗', 540, canvas.height - 84);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  if (!blob) throw new Error('Unable to render card');
  return blob;
}

const motions = { 'tang-232-chun-xiao': 'petals', 'tang-244-jiang-xue': 'snow', 'tang-225-zhu-li-guan': 'leaves' };

export function setupReadingExtras({ getCatalog, getCurrentPoem, loadPoem, openPoem, showDailyRecommendation, notice, getCoverPoemID = () => 'tang-157-feng-yu', motionAvailable = true }) {
  const $ = selector => document.querySelector(selector);
  const cover = document.createElement('button'); cover.className = 'cover-poem'; cover.id = 'coverPoem';
  $('.home-meta').before(cover);
  const daily = document.createElement('button'); daily.className = 'daily-poem'; daily.id = 'dailyPoem';
  $('#poemList').before(daily);
  const setPoemButton = (button, poem, captionText, onOpen) => {
    button.replaceChildren();
    const caption = document.createElement('small'); caption.textContent = captionText;
    const title = document.createElement('span'); title.textContent = `${poem.title} · ${poem.author}`;
    button.append(caption, title);
    button.setAttribute('aria-label', `${captionText}，${poem.title}，${poem.author}`);
    button.onclick = () => onOpen(poem.id);
  };
  const updateCover = () => {
    const poem = getCatalog().find(poem => poem.id === getCoverPoemID());
    cover.hidden = !poem;
    if (poem) setPoemButton(cover, poem, '画中诗', openPoem);
  };
  const updateDaily = () => {
    const poem = dailyPoem(getCatalog());
    daily.hidden = !poem || !showDailyRecommendation();
    if (poem) {
      setPoemButton(daily, poem, '每日一首', id => { $('#library').close(); openPoem(id); });
    }
  };
  const motionRow = document.createElement('label'); motionRow.className = 'setting-row';
  const motionLabel = document.createElement('span'); motionLabel.textContent = '画境微动';
  const motionSwitch = document.createElement('input'); motionSwitch.type = 'checkbox'; motionSwitch.id = 'settingMotion'; motionSwitch.setAttribute('role', 'switch');
  try { motionSwitch.checked = localStorage.getItem('tang-gentle-motion-v1') === 'true'; } catch {}
  motionRow.append(motionLabel, motionSwitch);
  const motionHelp = document.createElement('p'); motionHelp.className = 'extras-hint'; motionHelp.id = 'motionHint'; motionSwitch.setAttribute('aria-describedby', motionHelp.id);
  const save = document.createElement('button'); save.id = 'savePoemCard'; save.className = 'setting-row setting-link'; save.textContent = '保存或分享当前诗笺';
  $('#settings .about').before(save);
  if (motionAvailable) $('#settings .about').before(motionRow, motionHelp);
  const dialog = document.createElement('dialog'); dialog.id = 'cardDialog'; dialog.className = 'sheet card-sheet'; dialog.setAttribute('aria-labelledby', 'cardTitle');
  dialog.innerHTML = '<div class="sheet-header"><h2 id="cardTitle">诗笺预览</h2><button class="icon-button" aria-label="关闭诗笺预览">×</button></div><p class="card-status" role="status"></p><div class="card-preview"></div><div class="card-actions"><a class="text-pill" hidden>下载诗笺</a><button class="text-pill" hidden>分享诗笺</button></div>';
  document.body.append(dialog);
  let objectURL, cardFile, generation = 0;
  dialog.querySelector('.icon-button').onclick = () => dialog.close();
  dialog.addEventListener('close', () => {
    generation++; dialog.querySelector('.card-preview').replaceChildren();
    if (objectURL) URL.revokeObjectURL(objectURL); objectURL = null; cardFile = null;
    $('#openSettings').focus();
  });
  dialog.querySelector('.card-actions button').onclick = async () => {
    if (!cardFile) return;
    try { await navigator.share({ files: [cardFile], title: '唐诗画笺' }); }
    catch (error) { if (error.name !== 'AbortError') dialog.querySelector('.card-status').textContent = '暂时无法分享，可以先下载诗笺。'; }
  };
  save.onclick = async () => {
    const poem = getCurrentPoem(); if (!poem) return;
    $('#settings').close(); dialog.showModal();
    const request = ++generation;
    const status = dialog.querySelector('.card-status'), download = dialog.querySelector('a'), share = dialog.querySelector('.card-actions button');
    download.hidden = true; share.hidden = true; status.textContent = '正在制作完整诗笺…';
    try {
      const detail = await loadPoem(poem.id), blob = await makePoemCard(poem, detail);
      if (request !== generation || !dialog.open) return;
      objectURL = URL.createObjectURL(blob);
      const image = new Image(); image.src = objectURL; image.alt = `${poem.title}，${poem.author}的完整诗笺分享图`;
      dialog.querySelector('.card-preview').replaceChildren(image);
      download.href = objectURL; download.download = `${poem.title}-${poem.author}.png`; download.hidden = false;
      cardFile = new File([blob], `${poem.title}.png`, { type: 'image/png' });
      share.hidden = !(navigator.canShare?.({ files: [cardFile] }));
      status.textContent = detail.rubyLines.length > 12 ? '全诗已制成长图，可上下查看。' : '诗笺已生成，可下载保存或分享。';
    } catch { if (request === generation) status.textContent = '诗笺暂未生成，请关闭后重试。'; }
  };
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  function updateMotion() {
    motionHelp.textContent = reduced.matches ? '系统已开启减少动态效果，画境保持静止。' : '《春晓》《江雪》《竹里馆》轻动效试点，默认关闭。';
    const enabled = motionAvailable && motionSwitch.checked && !reduced.matches && !document.hidden && $('.reader').dataset.home === 'false' && !document.querySelector('dialog[open]');
    const id = getCurrentPoem()?.id;
    document.querySelectorAll('.poem-page').forEach(page => {
      const style = enabled && page.dataset.id === id ? motions[id] : null;
      const old = page.querySelector('.gentle-motion');
      if (!style) { old?.remove(); return; }
      if (old) return;
      const overlay = document.createElement('div'); overlay.className = `gentle-motion ${style}`; overlay.setAttribute('aria-hidden', 'true');
      for (let i = 0; i < (style === 'snow' ? 12 : 5); i++) {
        const particle = document.createElement('i');
        particle.style.setProperty('--x', `${13 + i % 7 * 11.5}%`); particle.style.setProperty('--duration', `${20 + i % 5 * 3}s`); particle.style.setProperty('--delay', `${-i * 4.34}s`);
        overlay.append(particle);
      }
      page.append(overlay);
    });
  }
  motionSwitch.onchange = () => {
    try { localStorage.setItem('tang-gentle-motion-v1', String(motionSwitch.checked)); }
    catch { notice('当前浏览器无法保存微动偏好，本次仍可使用。'); }
    updateMotion();
  };
  reduced.addEventListener('change', updateMotion);
  document.addEventListener('visibilitychange', () => { updateDaily(); updateMotion(); });
  document.querySelectorAll('dialog').forEach(item => new MutationObserver(updateMotion).observe(item, { attributes: true, attributeFilter: ['open'] }));
  new MutationObserver(updateMotion).observe($('.reader'), { attributes: true, attributeFilter: ['data-home'] });
  setInterval(updateDaily, 60000);
  updateCover(); updateDaily(); updateMotion();
  return { update: () => { updateCover(); updateDaily(); updateMotion(); }, updateRecommendations: updateDaily };
}
