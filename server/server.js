require("dotenv").config();
const express = require("express");
const cors    = require("cors");

const companiesRouter    = require("./routes/companies");
const sectorsRouter      = require("./routes/sectors");
const countriesRouter    = require("./routes/countries");
const macroRouter        = require("./routes/macro");
const healthRouter       = require("./routes/health");
const topMoversRouter    = require("./routes/topMovers");
const sectorLeadersRouter  = require("./routes/sectorLeaders");
const marketOverviewRouter = require("./routes/marketOverview");

const { prewarmCache }   = require("./utils/dataService");
const companies          = require("../data/realCompanies.json");

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

app.get("/", (req, res) => res.send("Asian Economy Analysis API is running."));

app.use((err, req, res, next) => {
  console.error("Server error:", err);
  res.status(500).json({ error: "Server error" });
});

app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
  // Pre-warm runs in background — server is already accepting requests
  prewarmCache(companies).catch(console.error);
});
