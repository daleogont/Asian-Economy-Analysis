const express = require("express");
const router  = express.Router();
const pool    = require("../utils/db");

router.get("/:ticker", async (req, res) => {
  const ticker = req.params.ticker.toUpperCase();

  try {
    const { rows } = await pool.query(
      `SELECT ticker, pe_ratio, eps, dividend_yield, beta, market_cap, fetched_at
       FROM fundamentals
       WHERE ticker = $1`,
      [ticker]
    );
    if (!rows.length) return res.status(404).json({ error: "No fundamentals for ticker" });
    res.json(rows[0]);
  } catch (err) {
    console.error("fundamentals route error:", err.message);
    res.status(500).json({ error: "Failed to fetch fundamentals" });
  }
});

module.exports = router;
