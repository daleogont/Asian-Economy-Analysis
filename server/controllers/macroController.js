const axios = require("axios");

const getMacro = async (req, res) => {
  const country = req.query.country;
  if (!country) {
    return res.status(400).json({ error: "Missing required query parameter: country" });
  }

  const COUNTRY_CODES = {
    "Japan": "JP",
    "China": "CN",
    "India": "IN",
    "Singapore": "SG",
    "Thailand": "TH",
    "Indonesia": "ID",
    "Malaysia": "MY",
    "Saudi Arabia": "SA",
    "South Korea": "KR",
    "Taiwan": "TW"
  };

  const code = COUNTRY_CODES[country];
  if (!code) {
    return res.status(400).json({ error: "Country not found" });
  }

  function findFirstValidValue(arr) {
    if (!Array.isArray(arr)) return null;
    const found = arr.find(item => item && item.value !== null && typeof item.value !== 'undefined');
    return found ? found.value : null;
  }

  try {
    const [gdpRes, popRes, unempRes] = await Promise.all([
      axios.get(`http://api.worldbank.org/v2/country/${code}/indicator/NY.GDP.MKTP.CD?format=json&per_page=10`),
      axios.get(`http://api.worldbank.org/v2/country/${code}/indicator/SP.POP.TOTL?format=json&per_page=10`),
      axios.get(`http://api.worldbank.org/v2/country/${code}/indicator/SL.UEM.TOTL.ZS?format=json&per_page=10`)
    ]);

    const gdp = findFirstValidValue(gdpRes.data[1]);
    const population = findFirstValidValue(popRes.data[1]);
    const unemployment = findFirstValidValue(unempRes.data[1]);

    res.json({
      country,
      code,
      gdp,
      population,
      unemployment
    });
  } catch (e) {
    console.error("Macro error:", e.message);
    res.status(500).json({ error: "Failed to load macro data" });
  }
};

module.exports = { getMacro };
