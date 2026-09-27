// New read receipts never infer completion from older bookmarks or saved positions.
export function sanitizeReadIDs(value, poems) {
  const valid = new Set(poems.map(poem => poem.id));
  return new Set(Array.isArray(value) ? value.filter(id => typeof id === 'string' && valid.has(id)) : []);
}

export function requiredReadingSeconds(section) {
  if (section === '五言绝句' || section === '七言绝句') return 10;
  if (section === '五言律诗' || section === '七言律诗') return 20;
  return 30;
}

export class ReadingSession {
  constructor() { this.reset(); }
  reset() { this.id = null; this.seconds = 0; this.sawEnd = false; this.last = null; this.active = false; this.suppressed = false; this.completed = false; }
  suppress(id) { if (this.id === id) this.suppressed = true; }
  sample({ id, section, active, endVisible, now }) {
    if (id !== this.id) { this.reset(); this.id = id; }
    const requiredSeconds = requiredReadingSeconds(section);
    if (active && this.active && this.last !== null) this.seconds = Math.min(requiredSeconds, this.seconds + Math.max(0, Math.min(2, now - this.last)));
    this.last = now;
    this.active = active;
    this.sawEnd ||= active && endVisible;
    if (!id || !active || this.suppressed || this.completed || this.seconds < requiredSeconds || !this.sawEnd) return false;
    this.completed = true;
    return true;
  }
}

// Freeze the membership of a read/unread reading session; the directory stays live.
export function restoreReadingSequence(savedIDs, candidates) {
  if (!Array.isArray(savedIDs)) return null;
  const ids = new Set(savedIDs.filter(id => typeof id === 'string'));
  const result = candidates.filter(poem => ids.has(poem.id));
  return result.length ? result : null;
}
