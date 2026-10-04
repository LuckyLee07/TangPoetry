import test from 'node:test';
import assert from 'node:assert/strict';
import { isNarrationTrackForPoem, narrationGroups } from '../reader-narration.js';

test('audio paths must refer to the current poem in a local release', () => {
  const poem = { id: 'tang-224-lu-chai' };
  for (const prefix of ['assets/audio', 'assets/audio/xiaoxiao-poetry-v1', 'assets/volume-2/audio/xiaoxiao-poetry-v1']) {
    assert.equal(isNarrationTrackForPoem({ id: poem.id, file: `${prefix}/${poem.id}.mp3` }, poem), true);
  }
  for (const file of ['https://example.com/audio.mp3', 'assets/audio/../../secret',
    'assets/audio/xiaoxiao-poetry-v1/another-poem.mp3', 'assets/volume-2/audio/other-release/tang-224-lu-chai.mp3',
    'assets/volume-2/audio/xiaoxiao-poetry-v1/another-poem.mp3', 'assets/audio/xiaoxiao-poetry-v1/tang-224-lu-chai.mp3?remote=1']) {
    assert.equal(isNarrationTrackForPoem({ id: poem.id, file }, poem), false);
  }
  assert.equal(isNarrationTrackForPoem({ id: 'wrong', file: `assets/audio/${poem.id}.mp3` }, poem), false);
});

test('listening selection follows catalog genre order rather than object or source ID order', () => {
  const manifest = { trackOrder: ['c', 'b', 'a'], tracks: {
    a: { id: 'a', section: '乐府' }, b: { id: 'b', section: '五言绝句' }, c: { id: 'c', section: '五言绝句' },
  } };
  assert.deepEqual([...narrationGroups(manifest)].map(([section, tracks]) => [section, tracks.map(t => t.id)]),
    [['五言绝句', ['c', 'b']], ['乐府', ['a']]]);
});

// Small DOM harness for transport behavior; no browser/media internals are simulated.
async function narrationHarness(t, { deferredManifest = false, narrationOptions = {} } = {}) {
  const { setupNarration } = await import('../reader-narration.js');
  class Element extends EventTarget {
    constructor() { super(); this.dataset = {}; this.hidden = false; this.open = false; this.value = '1'; this.attributes = new Map(); }
    setAttribute(key, value) { this.attributes.set(key, String(value)); }
    getAttribute(key) { return this.attributes.get(key) ?? null; }
    removeAttribute(key) { this.attributes.delete(key); }
    showModal() { this.open = true; }
    closest() { return this; }
    replaceChildren() {}
    append() {}
    click() { this.dispatchEvent(new Event('click')); }
  }
  const selectors = ['listenPoem', 'inlineNarration', 'inlineNarrationStatus', 'narrationDialog', 'narrationAudio', 'narrationTitle', 'narrationByline', 'narrationStatus', 'narrationSpeed', 'retryNarration', 'narrationSelection'];
  const elements = Object.fromEntries(selectors.map(id => [id, new Element()]));
  const audio = elements.narrationAudio;
  audio.paused = true; audio.plays = 0; audio.currentTime = 0; audio.error = null;
  Object.defineProperty(audio, 'src', { set(value) { this.setAttribute('src', value); }, get() { return this.getAttribute('src'); } });
  audio.load = () => { audio.currentTime = 0; };
  audio.pause = () => { audio.paused = true; audio.dispatchEvent(new Event('pause')); };
  audio.play = async () => {
    if (audio.rejectNext) { audio.rejectNext = false; throw Object.assign(new Error(), { name: 'NotAllowedError' }); }
    audio.plays++; audio.paused = false; audio.dispatchEvent(new Event('play'));
  };
  const document = new EventTarget(); document.hidden = false;
  document.querySelector = selector => elements[selector.slice(1)];
  document.createElement = () => new Element();
  const poems = [{ id: 'one', title: '第一首', author: '王维' }, { id: 'two', title: '第二首', author: '李白' }];
  let current = poems[0], resolveManifest;
  const manifest = { recipe: { voiceLabel: '朗读' }, tracks: Object.fromEntries(poems.map(poem => [poem.id, { ...poem, file: `assets/audio/${poem.id}.mp3` }])) };
  const pending = new Promise(resolve => { resolveManifest = resolve; });
  const originals = Object.getOwnPropertyDescriptors(globalThis);
  const fetchURLs = [];
  Object.assign(globalThis, { document, window: new EventTarget(), Option: Element,
    fetch: async url => { fetchURLs.push(url); return { ok: true, json: () => deferredManifest ? pending : manifest }; } });
  t.after(() => {
    window.dispatchEvent(new Event('pagehide'));
    for (const key of ['document', 'window', 'Option', 'fetch']) {
      if (originals[key]) Object.defineProperty(globalThis, key, originals[key]);
      else delete globalThis[key];
    }
  });
  const reader = setupNarration(() => current, () => {}, () => {}, narrationOptions);
  reader.update();
  return { ...elements, reader, fetchURLs, audio, flush: () => new Promise(resolve => setImmediate(resolve)),
    select: index => { current = poems[index]; reader.update(); }, resolve: () => resolveManifest(manifest) };
}

test('compact listening starts, pauses and resumes without a sheet, and follows the current poem', async t => {
  const h = await narrationHarness(t);
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.narrationDialog.open, false);
  assert.equal(h.audio.paused, false);
  assert.equal(h.inlineNarration.dataset.playing, 'true');
  h.audio.currentTime = 7;
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.paused, true);
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.paused, false);
  assert.equal(h.audio.currentTime, 7);
  h.select(1);
  assert.equal(h.audio.paused, true);
  assert.equal(h.inlineNarration.dataset.playing, 'false');
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.src, './assets/audio/two.mp3');
  assert.equal(h.narrationDialog.open, false);
});

test('a page turn or second compact tap cancels preparation instead of starting stale audio', async t => {
  const h = await narrationHarness(t, { deferredManifest: true });
  h.inlineNarration.click();
  assert.equal(h.inlineNarration.getAttribute('aria-busy'), 'true');
  h.select(1);
  h.inlineNarration.click();
  h.inlineNarration.click(); // Cancel the second poem while the shared manifest is still loading.
  h.resolve(); await h.flush();
  assert.equal(h.audio.plays, 0);
  assert.equal(h.inlineNarration.getAttribute('aria-busy'), 'false');
  assert.equal(h.narrationDialog.open, false);
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.plays, 1);
  assert.equal(h.audio.src, './assets/audio/two.mp3');
});

test('compact playback errors remain inline and the same button retries', async t => {
  const h = await narrationHarness(t);
  h.audio.rejectNext = true;
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.paused, true);
  assert.equal(h.inlineNarrationStatus.hidden, false);
  assert.equal(h.narrationDialog.open, false);
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.paused, false);
  assert.equal(h.inlineNarrationStatus.hidden, true);
  assert.equal(h.narrationDialog.open, false);
});

test('unavailable second-volume narration exposes no playback control or fetch and uses its own manifest after availability changes', async t => {
  const manifestURL = './data/audio-volume-2/manifest.json';
  const h = await narrationHarness(t, { narrationOptions: { available: false, manifestURL } });
  assert.equal(h.listenPoem.hidden, true);
  assert.equal(h.inlineNarration.hidden, true);
  h.inlineNarration.click(); await h.flush();
  assert.equal(h.audio.plays, 0);
  assert.deepEqual(h.fetchURLs, []);
  h.reader.setAvailable(true);
  assert.equal(h.listenPoem.hidden, false);
  h.inlineNarration.click(); await h.flush();
  assert.deepEqual(h.fetchURLs, [manifestURL]);
  assert.equal(h.audio.plays, 1);
  h.reader.setAvailable(false);
  assert.equal(h.audio.paused, true);
  assert.equal(h.inlineNarration.hidden, true);
});
