require("dotenv").config();
const express = require("express");
const cors    = require("cors");
const path    = require("path");

const companiesRouter    = require("./routes/companies");
const sectorsRouter      = require("./routes/sectors");
const countriesRouter    = require("./routes/countries");
const macroRouter        = require("./routes/macro");
const healthRouter       = require("./routes/health");
const topMoversRouter    = require("./routes/topMovers");
const sectorLeadersRouter  = require("./routes/sectorLeaders");
const marketOverviewRouter = require("./routes/marketOverview");
const historyRouter        = require("./routes/history");

const cron               = require("node-cron");
const { prewarmCache }   = require("./utils/dataService");
const { runDeltaFetch }  = require("./utils/deltaFetch");

const app  = express();
const PORT = require("./config").PORT || 4000;

app.use(cors());
app.use(express.json());

app.use("/api/companies",        companiesRouter);
app.use("/api/sectors",          sectorsRouter);
app.use("/api/countries",        countriesRouter);
app.use("/api/macros",           macroRouter);
app.use("/api/top-movers",       topMoversRouter);
app.use("/api/sector-leaders",   sectorLeadersRouter);
app.use("/api/market-overview",  marketOverviewRouter);
app.use("/api/health",           healthRouter);
app.use("/api/history",          historyRouter);

// Serve React build in production
if (process.env.NODE_ENV === "production") {
  const build = path.join(__dirname, "../client/build");
  app.use(express.static(build));
  app.get(/(.*)/, (req, res) => res.sendFile(path.join(build, "index.html")));
} else {
  app.get("/", (req, res) => res.send("Asian Economy Analysis API is running."));
}

app.use((err, req, res, next) => {
  console.error("Server error:", err);
  res.status(500).json({ error: "Server error" });
});

app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
  prewarmCache().catch(console.error);
  runDeltaFetch().catch(console.error);

  // Auto-refresh prices every day at 23:30 UTC
  cron.schedule("30 23 * * *", () => {
    console.log("🕐 Cron: starting daily delta fetch...");
    runDeltaFetch().catch(console.error);
  });
  console.log("⏰ Daily price refresh scheduled at 23:30 UTC");
});
