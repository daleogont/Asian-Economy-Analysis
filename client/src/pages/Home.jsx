import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import WeeklyReturnHistogram from "../components/WeeklyReturnHistogram";

const countryFlags = {
  Japan: "🇯🇵",
  China: "🇨🇳",
  India: "🇮🇳",
  Thailand: "🇹🇭",
  Singapore: "🇸🇬",
  Indonesia: "🇮🇩",
  Malaysia: "🇲🇾",
  Taiwan: "🇹🇼",
  "South Korea": "🇰🇷",
  "Saudi Arabia": "🇸🇦",
  "Hong Kong": "🇭🇰",
  Vietnam: "🇻🇳",
  Philippines: "🇵🇭",
  UAE: "🇦🇪",
  Pakistan: "🇵🇰",
};

const countrySlug = (name) => name.toLowerCase().replace(/ /g, "-");

const Home = () => {
  const [companies, setCompanies] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [countries, setCountries] = useState([]);
  const [topMovers, setTopMovers] = useState([]);
  const [sectorLeaders, setSectorLeaders] = useState([]);

  useEffect(() => {
    axios.get("/api/companies").then((res) => setCompanies(res.data));
    axios.get("/api/sectors").then((res) => setSectors(res.data));
    axios.get("/api/countries").then((res) => setCountries(res.data));
    axios.get("/api/top-movers").then((res) => setTopMovers(res.data));
    axios.get("/api/sector-leaders").then((res) => setSectorLeaders(res.data));
  }, []);

  const avgWeeklyReturn =
    companies.length
      ? companies.reduce((sum, c) => sum + (c.weeklyReturn || 0), 0) /
        companies.length
      : 0;

  const topSector = sectors.reduce(
    (max, s) => (s.companyCount > (max?.companyCount || 0) ? s : max),
    null
  );

  const topCountry = countries.reduce(
    (max, c) => (c.companyCount > (max?.companyCount || 0) ? c : max),
    null
  );

  return (
    <div className="px-6 py-8">
      <h1 className="text-3xl font-bold mb-6 text-center">
        Asia Market Dashboard
      </h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <div className="bg-white rounded-xl shadow p-5 text-center">
          <div className="text-gray-500 text-sm mb-1">Total Companies</div>
          <div className="text-2xl font-bold">{companies.length}</div>
        </div>
        <div className="bg-white rounded-xl shadow p-5 text-center">
          <div className="text-gray-500 text-sm mb-1">Avg Weekly Return</div>
          <div
            className={`text-2xl font-bold ${
              avgWeeklyReturn >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {avgWeeklyReturn >= 0 ? "+" : ""}
            {avgWeeklyReturn.toFixed(2)}%
          </div>
        </div>
        <div className="bg-white rounded-xl shadow p-5 text-center">
          <div className="text-gray-500 text-sm mb-1">Top Sector</div>
          <div className="text-xl font-bold">{topSector?.name || "—"}</div>
          <div className="text-gray-400 text-sm">
            {topSector ? topSector.companyCount + " companies" : ""}
          </div>
        </div>
        <div className="bg-white rounded-xl shadow p-5 text-center">
          <div className="text-gray-500 text-sm mb-1">Largest Market</div>
          <div className="text-xl font-bold">
            {topCountry
              ? (countryFlags[topCountry.country] || "") +
                " " +
                topCountry.country
              : "—"}
          </div>
          <div className="text-gray-400 text-sm">
            {topCountry ? topCountry.companyCount + " companies" : ""}
          </div>
        </div>
      </div>

      {/* Weekly Return Histogram */}
      {companies.length > 0 && (
        <WeeklyReturnHistogram
          companies={companies}
          title="Weekly Return Distribution — All Markets"
        />
      )}

      {/* Country Grid */}
      <h2 className="text-xl font-semibold mb-4">Markets by Country</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 mb-10">
        {countries.map((c) => (
          <Link
            key={c.country}
            to={`/country/${countrySlug(c.country)}`}
            className="bg-white rounded-xl shadow hover:shadow-md transition p-4 flex flex-col items-center text-center group"
          >
            <span className="text-3xl mb-2">
              {countryFlags[c.country] || "🌏"}
            </span>
            <span className="font-semibold text-sm group-hover:text-blue-600 transition">
              {c.country}
            </span>
            <span className="text-xs text-gray-500 mt-1">
              {c.companyCount} companies
            </span>
            {c.averageWeeklyReturn != null && (
              <span
                className={`text-xs font-medium mt-1 ${
                  c.averageWeeklyReturn >= 0
                    ? "text-green-600"
                    : "text-red-500"
                }`}
              >
                {c.averageWeeklyReturn >= 0 ? "▲" : "▼"}{" "}
                {Math.abs(c.averageWeeklyReturn).toFixed(2)}%
              </span>
            )}
          </Link>
        ))}
      </div>

      {/* Tables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-lg font-semibold mb-3">Top Movers (Weekly)</h2>
          <table className="w-full bg-white border border-gray-200 rounded-xl shadow text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left">Company</th>
                <th className="px-3 py-2 text-left">Country</th>
                <th className="px-3 py-2 text-right">Return</th>
              </tr>
            </thead>
            <tbody>
              {topMovers.slice(0, 5).map((c, idx) => (
                <tr
                  key={c.ticker}
                  className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                >
                  <td className="px-3 py-2">{c.name}</td>
                  <td className="px-3 py-2 text-gray-500">
                    {countryFlags[c.country] || ""} {c.country}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-medium ${
                      c.weeklyReturn >= 0 ? "text-green-600" : "text-red-500"
                    }`}
                  >
                    {c.weeklyReturn >= 0 ? "+" : ""}
                    {c.weeklyReturn.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-3">Sector Leaders</h2>
          <table className="w-full bg-white border border-gray-200 rounded-xl shadow text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left">Sector</th>
                <th className="px-3 py-2 text-left">Company</th>
                <th className="px-3 py-2 text-right">Price</th>
              </tr>
            </thead>
            <tbody>
              {sectorLeaders.map((c, idx) => (
                <tr
                  key={c.ticker}
                  className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                >
                  <td className="px-3 py-2 text-gray-500">{c.sector}</td>
                  <td className="px-3 py-2">{c.name}</td>
                  <td className="px-3 py-2 text-right">
                    {c.stockPrice != null
                      ? Number(c.stockPrice).toLocaleString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Home;
