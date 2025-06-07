const express = require("express");
const cors = require("cors");
const path = require("path");
const fs   = require("fs");

const cachePath = path.join(__dirname, "../data/cache.json");

const companiesRouter     = require("./routes/companies");
const sectorsRouter       = require("./routes/sectors");
const countriesRouter     = require("./routes/countries");
const macroRouter         = require("./routes/macro");
const healthRouter        = require("./routes/health");

const topMoversRouter       = require("./routes/topMovers");
const sectorLeadersRouter   = require("./routes/sectorLeaders");
const marketOverviewRouter  = require("./routes/marketOverview");

const app = express();
const PORT = require("./config").PORT || 4000;

app.use(cors());
app.use(express.json());

app.use("/api/companies", companiesRouter);
app.use("/api/sectors",   sectorsRouter);
app.use("/api/countries", countriesRouter);
app.use("/api/macros",    macroRouter);
app.use("/api/top-movers",       topMoversRouter);
app.use("/api/sector-leaders",   sectorLeadersRouter);
app.use("/api/market-overview",  marketOverviewRouter);


app.get("/", (req, res) => {
  res.send("Asian Economy Analysis API is running.");
});
app.use("/api/health", healthRouter);

app.use((err, req, res, next) => {
  console.error("Server error:", err);
  res.status(500).json({ error: "Server error" });
});

app.listen(PORT, () => {
  console.log(`✅ Сервер запущено на порту ${PORT}`);
});

process.on("SIGINT", () => {
  console.log("\nОтримано SIGINT — очищуємо cache.json…");
  try {
    if (fs.existsSync(cachePath)) {
      fs.writeFileSync(cachePath, "{}");
      console.log("✅ Файл cache.json очищено ({}).");
    }
  } catch (err) {
    console.error("❌ Не вдалося очистити cache.json:", err.message);
  }
  process.exit();
});
