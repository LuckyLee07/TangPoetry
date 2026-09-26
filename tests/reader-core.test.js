import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { migrateFavorites, sanitizeSettings, parseStored, filterPoems, initialIndex, createPoemLoader } from '../reader-core.js';

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
  assert.equal(initialIndex(poems, 'missing', '#p=NaN'), 0);
  assert.equal(initialIndex(poems, '', '#p=-12'), 0);
  assert.equal(initialIndex(poems, '', '#p=9999'), poems.length - 1);
  assert.equal(poems[initialIndex(poems, 'tang-233-ye-si')].id, 'tang-233-ye-si');
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
