// Reading state is keyed by the edition's stable poem IDs, never its current sort order.
export const ALL_POEMS = Object.freeze({ query: '', collection: 'all', category: 'all', author: 'all' });

export function sanitizeReadingScope(value) {
  const input = value && typeof value === 'object' ? value : {};
  return {
    query: typeof input.query === 'string' ? input.query.trim().slice(0, 200) : '',
    collection: ['all', 'featured', 'favorites'].includes(input.collection) ? input.collection : 'all',
    category: typeof input.category === 'string' && input.category ? input.category : 'all',
    author: typeof input.author === 'string' && input.author ? input.author : 'all'
  };
}

export function isAllPoems(scope) {
  return scope.collection === 'all' && scope.category === 'all' && scope.author === 'all' && !scope.query;
}

export function readingScopeLabel(scope) {
  const labels = [];
  if (scope.collection === 'favorites') labels.push('收藏');
  if (scope.collection === 'featured') labels.push('精选');
  if (scope.category !== 'all') labels.push(scope.category);
  if (scope.author !== 'all') labels.push(scope.author);
  if (scope.query) labels.push('搜索结果');
  return labels.join(' · ') || '全库';
}

export function selectionAfterScopeChange(previousIndex, selectedID, poems) {
  const matching = poems.findIndex(poem => poem.id === selectedID);
  return matching >= 0 ? matching : Math.max(0, Math.min(poems.length - 1, previousIndex));
}

const bounded = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

export function sanitizeReadingProgress(value, poems) {
  const validIDs = new Set(poems.map(poem => poem.id));
  const result = Object.create(null);
  if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
  for (const [id, position] of Object.entries(value)) {
    if (!validIDs.has(id) || !position || typeof position !== 'object') continue;
    if (!/^(start|verse:\d+|note)$/.test(position.anchor) || !Number.isFinite(position.fraction) || !Number.isFinite(position.progress)) continue;
    result[id] = { anchor: position.anchor, fraction: bounded(position.fraction, 0, 1), progress: bounded(position.progress, 0, 1) };
  }
  return result;
}

// An anchor plus a fraction of its paragraph survives font, viewport and note changes.
// Overall progress is only a fallback if a later content correction removes the anchor.
export function captureParagraphProgress(scrollTop, anchors, scrollHeight, clientHeight) {
  const maximum = Math.max(0, scrollHeight - clientHeight);
  const top = bounded(scrollTop, 0, maximum);
  if (top < 1 || !anchors.length) return { anchor: 'start', fraction: 0, progress: 0 };
  let index = 0;
  for (let next = 1; next < anchors.length && anchors[next].top <= top; next++) index = next;
  const anchor = anchors[index];
  const end = anchors[index + 1]?.top ?? scrollHeight;
  return { anchor: anchor.id, fraction: bounded((top - anchor.top) / Math.max(1, end - anchor.top), 0, 1), progress: top / Math.max(1, maximum) };
}

export function restoreParagraphProgress(position, anchors, scrollHeight, clientHeight) {
  if (!position) return 0;
  const maximum = Math.max(0, scrollHeight - clientHeight);
  const index = anchors.findIndex(anchor => anchor.id === position.anchor);
  if (index < 0) return maximum * position.progress;
  const start = anchors[index].top;
  const end = anchors[index + 1]?.top ?? scrollHeight;
  return bounded(start + position.fraction * Math.max(1, end - start), 0, maximum);
}

export function paragraphMetrics(body) {
  const bodyTop = body.getBoundingClientRect().top;
  const topOf = element => element.getBoundingClientRect().top - bodyTop + body.scrollTop;
  const anchors = [{ id: 'start', top: 0 }];
  body.querySelectorAll('.verse-line').forEach((line, index) => anchors.push({ id: `verse:${index}`, top: topOf(line) }));
  const note = body.querySelector('.note');
  if (note && note.getClientRects().length) anchors.push({ id: 'note', top: topOf(note) });
  return { anchors, scrollHeight: body.scrollHeight, clientHeight: body.clientHeight };
}

export function isReadingSurfaceTap({ start, end, cancelled = false, selection = '', interactive = false }) {
  return !cancelled && !interactive && !selection && Boolean(start) && Math.hypot(end.x - start.x, end.y - start.y) < 10;
}
