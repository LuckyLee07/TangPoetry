import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { ReadingSession, sanitizeReadIDs, restoreReadingSequence, readingSurfaceCountsTime } from '../reader-history.js';
import { filterPoems } from '../reader-core.js';
import { sanitizeReadingScope, readingScopeLabel } from '../reader-continuity.js';
const { poems } = JSON.parse(await readFile(new URL('../data/reader/catalog.json', import.meta.url)));
const sample = (session, now, extra = {}) => session.sample({ id: 'a', section: '五言律诗', now, active: true, endVisible: true, ...extra });

test('foreground narration counts toward twenty seconds, while paused and covered playback does not', () => {
  const active = readingSurfaceCountsTime({ foreground: true, surface: 'narration', currentNarrationPlaying: true });
  const session = new ReadingSession();
  for (let t = 0; t < 20; t++) assert.equal(sample(session, t, { section: '五言绝句', active }), false);
  assert.equal(sample(session, 20, { section: '五言绝句', active }), true);
  assert.equal(readingSurfaceCountsTime({ foreground: true, surface: 'narration', currentNarrationPlaying: false }), false);
  assert.equal(readingSurfaceCountsTime({ foreground: false, surface: 'narration', currentNarrationPlaying: true }), false);
  assert.equal(readingSurfaceCountsTime({ foreground: true, surface: 'covered', currentNarrationPlaying: true }), false);
  assert.equal(readingSurfaceCountsTime({ foreground: true, surface: 'poem', currentNarrationPlaying: false }), true);
});

test('all catalog genres use 20/30/40 foreground seconds and still require the last verse', () => {
  const durations = { 五言绝句: 20, 七言绝句: 20, 五言律诗: 30, 七言律诗: 30, 五言古诗: 40, 七言古诗: 40, 乐府: 40 };
  assert.deepEqual(new Set(poems.map(p => p.section)), new Set(Object.keys(durations)));
  for (const [section, seconds] of Object.entries(durations)) {
    const session = new ReadingSession();
    for (let t = 0; t < seconds; t++) assert.equal(sample(session, t, { section }), false, section);
    assert.equal(sample(session, seconds, { section }), true, section);
    assert.equal(sample(session, seconds + 1, { section }), false, 'A visit reports completion once');
    const incomplete = new ReadingSession();
    for (let t = 0; t <= seconds + 5; t++) assert.equal(sample(incomplete, t, { section, endVisible: false }), false, section);
    assert.equal(sample(incomplete, seconds + 6, { section }), true, section);
  }
});

test('moving from an ode to a quatrain resets both elapsed time and the completion threshold', () => {
  const session = new ReadingSession();
  for (let t = 0; t <= 39; t++) assert.equal(sample(session, t, { section: '乐府' }), false);
  for (let t = 40; t < 60; t++) assert.equal(sample(session, t, { id: 'b', section: '七言绝句' }), false);
  assert.equal(sample(session, 60, { id: 'b', section: '七言绝句' }), true);
});

test('sheets, background time, unloaded neighbors and rapid paging cannot mark poems read', () => {
  const session = new ReadingSession();
  for (let t = 0; t <= 5; t++) sample(session, t);
  sample(session, 6, { active: false });
  sample(session, 3600, { active: false });
  assert.equal(sample(session, 3601), false);
  assert.equal(session.seconds, 5);
  for (let t = 3602; t < 3626; t++) assert.equal(sample(session, t), false);
  assert.equal(sample(session, 3626), true);
  const paging = new ReadingSession();
  for (let t = 0; t < 100; t++) assert.equal(sample(paging, t, { id: `poem-${t}` }), false);
  const unloaded = new ReadingSession();
  for (let t = 0; t < 30; t++) sample(unloaded, t, { active: false });
  assert.equal(unloaded.seconds, 0);
  const stalled = new ReadingSession();
  sample(stalled, 0); assert.equal(sample(stalled, 3600), false);
});

test('a manual unread correction suppresses completion for that visit but a new visit can count', () => {
  const session = new ReadingSession();
  for (let t = 0; t < 10; t++) sample(session, t);
  session.suppress('a');
  for (let t = 10; t < 40; t++) assert.equal(sample(session, t), false);
  sample(session, 40, { id: 'b' });
  for (let t = 41; t < 71; t++) assert.equal(sample(session, t), false);
  assert.equal(sample(session, 71), true);
});

test('receipts start empty on upgrade, reject corrupt IDs and compose with catalog filters', () => {
  assert.equal(sanitizeReadIDs({ position: poems[0].id }, poems).size, 0);
  assert.equal(sanitizeReadIDs(null, poems).size, 0);
  const candidates = poems.filter(p => p.author === '王维' && p.featured && p.section === '五言绝句');
  const readIDs = sanitizeReadIDs([candidates[0].id, candidates[0].id, 'missing', null], poems);
  const scope = sanitizeReadingScope({ author: '王维', category: '五言绝句', collection: 'featured', readStatus: 'read' });
  assert.deepEqual(filterPoems(poems, scope, new Set(), readIDs).map(p => p.id), [candidates[0].id]);
  assert(!filterPoems(poems, { ...scope, readStatus: 'unread' }, new Set(), readIDs).some(p => readIDs.has(p.id)));
  assert.equal(readingScopeLabel(scope), '推荐 · 已读 · 五言绝句 · 王维');
  const legacy = sanitizeReadingScope({ author: '李白', collection: 'featured' });
  assert.equal(legacy.readStatus, 'all'); assert.equal(legacy.author, '李白');
});

test('a read-filter sequence survives new receipts and restart without changing the current page', () => {
  const original = filterPoems(poems, { author: '王维', readStatus: 'unread' });
  const saved = original.map(p => p.id);
  const read = new Set([saved[0]]);
  const candidates = filterPoems(poems, { author: '王维' }, new Set(), read);
  assert.deepEqual(restoreReadingSequence(saved, candidates), original);
  assert(!filterPoems(poems, { author: '王维', readStatus: 'unread' }, new Set(), read).some(p => p.id === saved[0]));
  assert.equal(restoreReadingSequence(['invalid'], candidates), null);
});
