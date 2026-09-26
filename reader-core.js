export const DEFAULT_SETTINGS = Object.freeze({ pinyin: true, notes: true, fontSize: 22, paper: "warm" });

export function parseStored(value, fallback) {
  try { return value == null ? fallback : JSON.parse(value); } catch { return fallback; }
}

export function sanitizeSettings(value) {
  const input = value && typeof value === "object" ? value : {};
  return {
    pinyin: typeof input.pinyin === "boolean" ? input.pinyin : true,
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
