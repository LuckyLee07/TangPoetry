export const READER_VOLUMES = Object.freeze([
  Object.freeze({ id: '1', label: '第一卷', subtitle: '唐诗三百首 · 孙洙选本', dataRoot: './data/reader', audioManifest: './data/audio/manifest.json' }),
  Object.freeze({ id: '2', label: '第二卷', subtitle: '撷英与补选 · 第二卷', dataRoot: './data/reader-volume-2', audioManifest: './data/audio-volume-2/manifest.json' })
]);

export function readerVolume(search = '') {
  const selected = new URLSearchParams(search).get('volume');
  return READER_VOLUMES.find(volume => volume.id === selected) || READER_VOLUMES[0];
}

export function readingStorageKeys(volume) {
  const keys = { read: 'tang-read-ids-v1', sequence: 'tang-reading-sequence-v1', favorites: 'tang-favorites-v2', settings: 'tang-settings-v1', position: 'tang-position-v1', scope: 'tang-reading-scope-v1', progress: 'tang-reading-progress-v1' };
  if (volume.id !== '1') {
    for (const key of Object.keys(keys)) if (key !== 'settings') keys[key] += `-volume-${volume.id}`;
  }
  return keys;
}

export function volumeURL(id, href) {
  const url = new URL(href);
  if (id === '1') url.searchParams.delete('volume');
  else url.searchParams.set('volume', id);
  url.hash = '';
  return url.href;
}
