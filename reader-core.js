export const DEFAULT_SETTINGS = Object.freeze({ pinyin: false, notes: true, fontSize: 22, paper: "warm" });

export function parseStored(value, fallback) {
  try { return value == null ? fallback : JSON.parse(value); } catch { return fallback; }
}

export function sanitizeSettings(value) {
  const input = value && typeof value === "object" ? value : {};
  return {
    // The current reading edition omits pronunciation, including older saved preferences.
    pinyin: false,
    notes: typeof input.notes === "boolean" ? input.notes : true,
    fontSize: [20, 22, 26, 30].includes(input.fontSize) ? input.fontSize : 22,
    paper: ["warm", "ivory", "sage"].includes(input.paper) ? input.paper : "warm"
  };
}

export function migrateFavorites(saved, legacy, poems) {
  const ids = new Set(poems.map(poem => poem.id));
  if (Array.isArray(saved)) return new Set(saved.filter(id => typeof id === "string" && ids.has(id)));
  const titles = new Set(Array.isArray(legacy) ? legacy : []);
  // Preserve the old visible collection, then let each stable ID be managed independently.
  return new Set(poems.filter(poem => [poem.title, ...(poem.aliases || [])].some(title => titles.has(title))).map(poem => poem.id));
}

export function normalizeSearch(value) {
  return String(value || "").normalize("NFKC").toLocaleLowerCase().replace(/\s+/g, "").replace(/[，。！？；、,.!?;·]/g, "");
}

export function filterPoems(poems, { query = "", category = "all", collection = "all" } = {}, favorites = new Set()) {
  const needle = normalizeSearch(query);
  return poems.filter(poem =>
    (collection !== "featured" || poem.featured) &&
    (collection !== "favorites" || favorites.has(poem.id)) &&
    (category === "all" || poem.theme === category || poem.section === category) &&
    (!needle || normalizeSearch(poem.searchText).includes(needle))
  );
}

export function initialIndex(poems, savedID, hash = "") {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const id = params.get("poem") || savedID;
  if (params.has("p")) {
    const value = Number(params.get("p"));
    return Number.isFinite(value) ? Math.max(0, Math.min(poems.length - 1, Math.floor(value))) : 0;
  }
  return Math.max(0, poems.findIndex(poem => poem.id === id));
}

export function createPoemLoader(fetchPoem, maxEntries = 12) {
  const cache = new Map();
  return {
    load(id) {
      if (cache.has(id)) { const value = cache.get(id); cache.delete(id); cache.set(id, value); return value; }
      const pending = Promise.resolve().then(() => fetchPoem(id)).catch(error => {
        if (cache.get(id) === pending) cache.delete(id);
        throw error;
      });
      cache.set(id, pending);
      while (cache.size > maxEntries) cache.delete(cache.keys().next().value);
      return pending;
    },
    get size() { return cache.size; }
  };
}

// Fit ordinary poems to a page; preserve a readable size and scrolling for long works.
export function readingLayout(poem, { width = 390, height = 844, fontSize = 22, notes = true } = {}) {
  const texts = poem.rubyLines.map(line => line.map(([text]) => text).join(''));
  const lengths = texts.map(text => [...text.replace(/[\p{Punctuation}\s]/gu, '')].length);
  const lineCount = lengths.length;
  const typicalLength = [...lengths].sort((a, b) => a - b)[Math.floor(lineCount / 2)] || 5;
  const five = typicalLength <= 5;
  const short = lineCount <= 4 || (/绝句/.test(poem.section) && lineCount <= 5);
  const regulated = !short && (lineCount <= 8 || (/律诗/.test(poem.section) && lineCount <= 9));
  const medium = !short && !regulated && lineCount <= 12;
  const kind = short ? (five ? 'five-quatrain' : 'seven-quatrain')
    : regulated ? (five ? 'five-regulated' : 'seven-regulated') : medium ? 'medium' : 'long';
  const baseFont = short ? (five ? 26 : 24) : regulated ? (five ? 22 : 21) : 20;
  const scale = fontSize / 22;
  const minimumFont = Math.max(18, 18 * scale);
  const preferredFont = Math.max(minimumFont, baseFont * scale);
  const lineHeight = short ? 1.95 : regulated ? (height < 620 ? 1.35 : 1.6) : medium ? 1.55 : 1.7;
  const noteHeight = Math.max(80, Math.min(86, height * 0.1));
  const bottom = notes && poem.note ? 78 + noteHeight + 16 : 84;
  const minimumTop = Math.max(108, height * 0.15);
  let top = Math.max(minimumTop, height * (short ? 0.36 : regulated ? 0.22 : 0.18));
  let fittedFont = preferredFont;
  const bodyWidth = Math.max(80, width - 80);
  const titleSize = Math.min(26, Math.max(20, baseFont + 1));
  const headingHeight = Math.ceil([...poem.title].length * titleSize * 1.1 / bodyWidth) * titleSize * 1.4 + 38;
  const estimatedHeight = size => {
    const columns = Math.max(1, Math.floor((bodyWidth - size) / size));
    const rows = lengths.reduce((total, count) => total + Math.max(1, Math.ceil(count / columns)), 0);
    return headingHeight + rows * size * lineHeight + 20;
  };
  const fitWhole = short || regulated || medium;
  if (fitWhole) {
    top = Math.max(minimumTop, Math.min(top, height - bottom - estimatedHeight(fittedFont)));
    while (fittedFont > minimumFont && estimatedHeight(fittedFont) > height - bottom - top) {
      fittedFont = Math.max(minimumFont, fittedFont - 0.5);
    }
  }
  return { kind, lineCount, fontSize: Math.round(fittedFont * 10) / 10, minimumFont, top, bottom, lineHeight, titleSize, noteHeight, fitWhole };
}
