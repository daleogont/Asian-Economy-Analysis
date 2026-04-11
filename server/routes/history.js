const express = require("express");
const router  = express.Router();
const { getTickerHistory } = require("../utils/stockQueries");

const PERIOD_DAYS = { "3m": 90, "6m": 180, "1y": 365, "2y": 730 };

router.get("/:ticker", async (req, res) => {
  const ticker = req.params.ticker.toUpperCase();
  const days   = PERIOD_DAYS[req.query.period] ?? 365;

  try {
    const rows = await getTickerHistory(ticker, days);
    if (!rows.length) return res.status(404).json({ error: "No data for ticker" });
    res.json({ ticker, period: req.query.period || "1y", data: rows });
  } catch (err) {
    console.error("history route error:", err.message);
    res.status(500).json({ error: "Failed to fetch history" });
  }
});

module.exports = router;
