import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { migrateFavorites, sanitizeSettings, parseStored, filterPoems, initialIndex, createPoemLoader, readingLayout } from '../reader-core.js';

const { poems } = JSON.parse(await readFile(new URL('../data/reader/catalog.json', import.meta.url)));

test('legacy aliases migrate, while duplicate titles become independent IDs', () => {
  const result = migrateFavorites(null, ['静夜思', '杂诗'], poems);
  assert(result.has('tang-233-ye-si'));
  const sameTitle = poems.filter(p => p.title === '杂诗');
  assert.equal(sameTitle.length, 3);
  sameTitle.forEach(p => assert(result.has(p.id)));
  result.delete(sameTitle[0].id);
  assert(result.has(sameTitle[1].id));
  assert.deepEqual([...migrateFavorites([], ['静夜思'], poems)], []);
  assert.deepEqual([...migrateFavorites(['missing'], [], poems)], []);
});

test('corrupt or incompatible saved state cannot break startup', () => {
  assert.equal(parseStored('{broken', null), null);
  assert.deepEqual(sanitizeSettings({ pinyin: 'false', fontSize: 999, paper: 'unknown' }), sanitizeSettings(null));
  assert.equal(sanitizeSettings({ pinyin: false }).pinyin, false);
  assert.equal(sanitizeSettings({ pinyin: true }).pinyin, false);
  assert.equal(initialIndex(poems, 'missing', '#p=NaN'), 0);
  assert.equal(initialIndex(poems, '', '#p=-12'), 0);
  assert.equal(initialIndex(poems, '', '#p=9999'), poems.length - 1);
  assert.equal(poems[initialIndex(poems, 'tang-233-ye-si')].id, 'tang-233-ye-si');
  assert.equal(poems[initialIndex(poems, '', '#p=0')].id, 'tang-001-gan-yu-qi-yi');
  assert.equal(poems[initialIndex(poems, '', '#poem=tang-233-ye-si')].id, 'tang-233-ye-si');
});

test('search finds canonical titles, aliases, authors, punctuation-free verses and traditional text', () => {
  for (const query of ['静夜思', '夜思', '床前明月光疑是地上霜', '床前 明月光', '舉頭望明月']) {
    assert(filterPoems(poems, { query }).some(p => p.id === 'tang-233-ye-si'), query);
  }
  assert(filterPoems(poems, { query: '李白' }).length > 10);
  assert.equal(filterPoems(poems, { query: '不存在的诗句xyz' }).length, 0);
  const favorites = new Set(['tang-233-ye-si']);
  assert.equal(filterPoems(poems, { collection: 'favorites' }, favorites).length, 1);
  assert.equal(filterPoems(poems, { collection: 'favorites', category: '送别' }, favorites).length, 0);
});

test('requests deduplicate, failed poems can retry, and cache remains bounded', async () => {
  let calls = 0;
  const loader = createPoemLoader(async id => { calls++; if (id === 'bad' && calls === 2) throw Error('offline'); return { id }; }, 2);
  const a = loader.load('a');
  assert.equal(a, loader.load('a'));
  await a;
  assert.equal(calls, 1);
  await assert.rejects(loader.load('bad'));
  assert.deepEqual(await loader.load('bad'), { id: 'bad' });
  await loader.load('c');
  assert.equal(loader.size, 2);
  await loader.load('a');
  assert.equal(calls, 5);
});

test('poems share reading starts by length, with readable type and scrolling for longer works', async () => {
  const load = async id => ({ ...poems.find(p => p.id === id), ...JSON.parse(await readFile(new URL(`../data/reader/poems/${id}.json`, import.meta.url))) });
  const short = await load('tang-227-xiang-si');
  const regulated = await load('tang-116-shan-ju-qiu-ming');
  const epic = await load('tang-071-chang-hen-ge');
  const a = readingLayout(short), b = readingLayout(regulated), c = readingLayout(epic);
  assert.equal(a.kind, 'five-quatrain');
  assert.equal(b.kind, 'five-regulated');
  assert.equal(c.kind, 'long');
  assert(a.fontSize > b.fontSize);
  assert(a.top > b.top);
  assert.equal(a.top, 844 * 0.45 - 70);
  assert.equal(b.top, 844 * 0.39 - 70);
  assert.equal(a.textRise, 45);
  assert.equal(a.noteGap - a.textRise - 28, 25, 'The inline note moves down independently of the poem');
  assert.equal(a.fontSize, 26);
  assert.equal(b.fontSize, 22);
  assert.equal(c.top, b.top);
  const legacyArtworkOffset = readingLayout({ ...short, textStart: 0.52 });
  assert.deepEqual(legacyArtworkOffset, a, 'Legacy artwork offsets must not move the poem');
  assert.equal(c.fitWhole, false);
  assert(c.fontSize >= 18);
  const small = readingLayout(regulated, { width: 320, height: 568 });
  assert(small.fontSize < b.fontSize);
  assert(small.fontSize >= 20);
  assert(small.top < b.top);
  assert.equal(small.top, 568 * 0.39 - 70);
  const veryShort = readingLayout(regulated, { width: 320, height: 350 });
  assert.equal(veryShort.top, 100);
  assert(veryShort.textRise < 45);
  assert.equal(veryShort.noteGap - veryShort.textRise - 28, -10);
  const atFloor = readingLayout(regulated, { width: 320, height: 300 });
  assert.equal(atFloor.top, 100);
  assert.equal(atFloor.textRise, 0);
  assert.equal(atFloor.noteGap, 18);
  const large = readingLayout(regulated, { fontSize: 30 });
  assert(large.fontSize > b.fontSize);
  const noNotes = readingLayout({ ...regulated, note: '' }, { width: 320, height: 568 });
  assert.equal(noNotes.fontSize, small.fontSize);
  assert.equal(noNotes.lineHeight, small.lineHeight);
  assert(noNotes.top >= small.top);
  assert.equal(readingLayout({ ...regulated, note: '' }, { width: 320, height: 350 }).top, veryShort.top, 'Poems with no spare height must keep their scrolling room');
  const noShortNote = readingLayout({ ...short, note: '' });
  assert.equal(noShortNote.top, a.top, 'Annotation visibility never moves the poem');
  assert(noShortNote.noNoteShift <= 60);
  assert.equal(noShortNote.baseTop, a.top);
  assert.equal(noShortNote.fontSize, a.fontSize);
  assert.equal(noShortNote.lineHeight, a.lineHeight);
  assert.deepEqual(readingLayout(short, { notesEnabled: false }), noShortNote);
  assert.deepEqual(readingLayout({ ...short, note: ' \n ' }), noShortNote);
  assert.deepEqual(readingLayout(short, { notesEnabled: true }), a, 'Showing notes preserves the original layout');
  assert.equal(readingLayout(epic, { notesEnabled: false }).noNoteShift, 0);
  const longTitle = readingLayout({ ...regulated, title: '山'.repeat(30) }, { width: 320, height: 568, fontSize: 30 });
  assert.equal(longTitle.top, small.top);
  assert(longTitle.fontSize >= 20 * 30 / 22 - 0.05);
  const longTitleWithoutNotes = readingLayout({ ...regulated, title: '山'.repeat(30), note: '' }, { width: 320, height: 568, fontSize: 30 });
  assert.equal(longTitleWithoutNotes.top, longTitle.top);
  assert.equal(longTitleWithoutNotes.fontSize, longTitle.fontSize);
});
