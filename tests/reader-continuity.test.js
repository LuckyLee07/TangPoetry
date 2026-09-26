import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { filterPoems } from '../reader-core.js';
import { ALL_POEMS, sanitizeReadingScope, isAllPoems, readingScopeLabel, selectionAfterScopeChange, sanitizeReadingProgress, captureParagraphProgress, restoreParagraphProgress, isReadingSurfaceTap } from '../reader-continuity.js';

const { poems } = JSON.parse(await readFile(new URL('../data/reader/catalog.json', import.meta.url)));

test('reading filters compose into an ordered sequence and author browsing is exact', () => {
  const scope = sanitizeReadingScope({ author: '王维', category: '五言绝句', collection: 'favorites' });
  const selected = poems.filter(poem => poem.author === '王维').slice(0, 5);
  const favorites = new Set(selected.map(poem => poem.id));
  const result = filterPoems(poems, scope, favorites);
  assert(result.length > 1);
  assert(result.every(poem => poem.author === '王维' && poem.section === '五言绝句' && favorites.has(poem.id)));
  assert.deepEqual(result, poems.filter(poem => result.includes(poem)), 'Catalog order is retained within a scope');
  assert.equal(readingScopeLabel(scope), '收藏 · 五言绝句 · 王维');
  assert.equal(isAllPoems(scope), false);
  assert.equal(isAllPoems(sanitizeReadingScope({ category: null, author: 7, collection: 'bad', query: [] })), true);
  assert.deepEqual(sanitizeReadingScope(null), ALL_POEMS);
  assert.equal(filterPoems(poems, { author: '王' }).length, 0, 'An author index uses an exact author, not a substring');
});

test('favorite removal chooses the following available poem, handles the last and empty item', () => {
  const sequence = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
  assert.equal(selectionAfterScopeChange(1, 'b', sequence), 1);
  assert.equal(selectionAfterScopeChange(1, 'b', [sequence[0], sequence[2]]), 1);
  assert.equal(selectionAfterScopeChange(2, 'c', sequence.slice(0, 2)), 1);
  assert.equal(selectionAfterScopeChange(0, 'a', []), 0);
  assert.equal(selectionAfterScopeChange(2, 'a', sequence), 0, 'Returning to all poems keeps the stable selected ID');
});

test('paragraph bookmarks survive font changes and removed anchors fall back safely', () => {
  const initial = [{ id: 'start', top: 0 }, { id: 'verse:0', top: 100 }, { id: 'verse:1', top: 140 }, { id: 'verse:2', top: 180 }];
  const saved = captureParagraphProgress(150, initial, 600, 200);
  assert.deepEqual(saved, { anchor: 'verse:1', fraction: 0.25, progress: 0.375 });
  const enlarged = [{ id: 'start', top: 0 }, { id: 'verse:0', top: 120 }, { id: 'verse:1', top: 180 }, { id: 'verse:2', top: 240 }];
  assert.equal(restoreParagraphProgress(saved, enlarged, 800, 250), 195);
  assert.equal(restoreParagraphProgress(saved, [{ id: 'start', top: 0 }], 800, 200), 225);
  assert.equal(restoreParagraphProgress(saved, enlarged, 210, 200), 10, 'Shortened content clamps the restored position');
  assert.deepEqual(captureParagraphProgress(-20, initial, 600, 200), { anchor: 'start', fraction: 0, progress: 0 });
  assert.equal(restoreParagraphProgress(null, initial, 600, 200), 0);
});

test('bookmarks reject stale IDs, arrays and corrupt values while preserving stable poem identity', () => {
  const id = poems[0].id;
  const valid = { anchor: 'verse:3', fraction: 0.5, progress: 0.3 };
  assert.deepEqual(Object.keys(sanitizeReadingProgress({ missing: valid, [id]: valid }, [...poems].reverse())), [id]);
  assert.deepEqual(sanitizeReadingProgress({ [id]: valid }, poems)[id], valid);
  for (const corrupt of [{ anchor: 'hack', fraction: 0, progress: 0 }, { anchor: 'verse:1', fraction: Infinity, progress: 0 }, null]) {
    assert.equal(Object.keys(sanitizeReadingProgress({ [id]: corrupt }, poems)).length, 0);
  }
  assert.equal(Object.keys(sanitizeReadingProgress([], poems)).length, 0);
});

test('surface taps ignore vertical drags, cancelled pointers, controls and text selection', () => {
  const tap = { start: { x: 30, y: 100 }, end: { x: 32, y: 102 } };
  assert.equal(isReadingSurfaceTap(tap), true);
  assert.equal(isReadingSurfaceTap({ ...tap, end: { x: 30, y: 180 } }), false);
  assert.equal(isReadingSurfaceTap({ ...tap, cancelled: true }), false);
  assert.equal(isReadingSurfaceTap({ ...tap, interactive: true }), false);
  assert.equal(isReadingSurfaceTap({ ...tap, selection: '空山' }), false);
  assert.equal(isReadingSurfaceTap({ ...tap, start: null }), false);
});
