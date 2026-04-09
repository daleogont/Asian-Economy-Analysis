const express = require("express");
const router  = express.Router();
const { getCache } = require("../utils/cacheStore");

router.get("/", (req, res) => {
  const cache = getCache();
  let live = 0, seed = 0, yahoo = 0, twelve = 0, stale = 0;

  for (const [, entry] of cache) {
    if (entry.isSeed)          { seed++;   continue; }
    if (entry.source === "twelve") twelve++;
    else                           yahoo++;
    if (entry.cachedAt && Date.now() - entry.cachedAt > 12 * 60 * 60 * 1000) stale++;
    else live++;
  }

  res.json({
    status: "ok",
    cache: { total: cache.size, live, seed, stale, bySource: { yahoo, twelve } },
  });
});

module.exports = router;
