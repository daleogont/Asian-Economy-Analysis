// Persistent cache with 12h TTL. Falls back to seed.json for uncached tickers.
const path = require("path");
const fs   = require("fs");

const CACHE_FILE   = path.join(__dirname, "../../data/cache.json");
const SEED_FILE    = path.join(__dirname, "../../data/seed.json");
const CACHE_TTL_MS = 12 * 60 * 60 * 1000;

const store = new Map();

// Load live cache
try {
  const raw = JSON.parse(fs.readFileSync(CACHE_FILE, "utf-8"));
  const now = Date.now();
  let loaded = 0;
  for (const [ticker, entry] of Object.entries(raw)) {
    if (entry?.cachedAt && (now - entry.cachedAt) < CACHE_TTL_MS) {
      store.set(ticker, entry);
      loaded++;
    }
  }
  if (loaded > 0) console.log(`📦 Loaded ${loaded} live tickers from cache`);
} catch { /* no cache file yet */ }

// Load seed as fallback for anything not in live cache
let seedCount = 0;
try {
  const seed = JSON.parse(fs.readFileSync(SEED_FILE, "utf-8"));
  for (const [ticker, entry] of Object.entries(seed)) {
    if (!store.has(ticker)) {
      store.set(ticker, { ...entry, isSeed: true });
      seedCount++;
    }
  }
  if (seedCount > 0) console.log(`🌱 Using seed data for ${seedCount} tickers`);
} catch { /* no seed file */ }

// Debounced disk write — skips seed entries
let _saveTimer = null;
function scheduleSave() {
  if (_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(() => {
    try {
      const obj = {};
      for (const [k, v] of store) if (!v.isSeed) obj[k] = v;
      fs.writeFileSync(CACHE_FILE, JSON.stringify(obj, null, 2));
    } catch (e) {
      console.error("Cache save failed:", e.message);
    }
  }, 2000);
}

const getCache  = ()             => store;
const getCached = (ticker)       => store.get(ticker) ?? null;
const setCached = (ticker, data) => {
  store.set(ticker, { ...data, cachedAt: Date.now(), isSeed: false });
  scheduleSave();
};
const cacheSize = () => store.size;

module.exports = { getCache, getCached, setCached, cacheSize };
