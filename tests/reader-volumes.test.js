import test from 'node:test';
import assert from 'node:assert/strict';
import { readerVolume, readingStorageKeys, volumeURL } from '../reader-volumes.js';
import { migrateFavorites } from '../reader-core.js';

test('first volume is the default, with every existing storage key preserved', () => {
  assert.equal(readerVolume('').id, '1');
  assert.equal(readerVolume('?volume=unknown').id, '1');
  assert.deepEqual(readingStorageKeys(readerVolume('')), { read: 'tang-read-ids-v1', sequence: 'tang-reading-sequence-v1', favorites: 'tang-favorites-v2', settings: 'tang-settings-v1', position: 'tang-position-v1', scope: 'tang-reading-scope-v1', progress: 'tang-reading-progress-v1' });
});

test('switching catalogs cannot overwrite another volume’s reading records', () => {
  const first = readerVolume(''), second = readerVolume('?volume=2');
  const firstKeys = readingStorageKeys(first), secondKeys = readingStorageKeys(second);
  const storage = new Map([[firstKeys.favorites, ['first-poem']], [firstKeys.position, 'first-poem'], [firstKeys.read, ['first-poem']]]);
  const poems = [{ id: 'second-poem', title: '诗', aliases: [] }];
  const favorites = migrateFavorites(storage.get(secondKeys.favorites), [], poems);
  favorites.add('second-poem');
  storage.set(secondKeys.favorites, [...favorites]);
  storage.set(secondKeys.position, 'second-poem');
  storage.set(secondKeys.read, ['second-poem']);
  assert.deepEqual(storage.get(firstKeys.favorites), ['first-poem']);
  assert.equal(storage.get(firstKeys.position), 'first-poem');
  assert.deepEqual(storage.get(firstKeys.read), ['first-poem']);
  assert.equal(firstKeys.settings, secondKeys.settings);
  for (const key of ['read', 'sequence', 'favorites', 'position', 'scope', 'progress']) assert.notEqual(firstKeys[key], secondKeys[key]);
  assert.equal(second.dataRoot, './data/reader-volume-2');
});

test('volume links retain unrelated query options and clear a poem from another volume', () => {
  assert.equal(volumeURL('2', 'https://example.com/index.html?paper=warm#poem=one'), 'https://example.com/index.html?paper=warm&volume=2');
  assert.equal(volumeURL('1', 'https://example.com/index.html?volume=2&paper=warm#library'), 'https://example.com/index.html?paper=warm');
});
