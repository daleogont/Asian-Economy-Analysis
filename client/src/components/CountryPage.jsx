import React, { useEffect, useState } from "react";
import axios from "axios";
import WeeklyReturnIndicator from "../components/WeeklyReturnIndicator";
import SummaryStats from "../components/SummaryStats";
import WeeklyReturnHistogram from "../components/WeeklyReturnHistogram";
import PriceHistoryChart from "../components/PriceHistoryChart";
import ForecastChart from "../components/ForecastChart";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

const InfoTooltip = ({ text }) => (
  <span className="ml-1 text-xs text-gray-400 cursor-pointer group relative">
    <span>?</span>
    <span className="absolute left-1/2 transform -translate-x-1/2 mt-1 w-48 bg-gray-800 text-white text-xs rounded p-2 opacity-0 group-hover:opacity-100 transition pointer-events-none z-50">
      {text}
    </span>
  </span>
);

const macroNames = {
  gdp: (
    <>
      GDP ($)
      <InfoTooltip text="Gross domestic product, billions USD. Source: World Bank (2022/2023)" />
    </>
  ),
  population: (
    <>
      Population
      <InfoTooltip text="Total population, millions. Source: World Bank (2022/2023)" />
    </>
  ),
  unemployment: (
    <>
      Unemployment (%)
      <InfoTooltip text="Unemployment rate, %" />
    </>
  ),
};

const tableTooltips = {
  "Market Cap ($)": "Total market value of the company in USD.",
  "Stock Price": "Current price of one share.",
  "Weekly Return (%)": "Percentage change in share price over the past week.",
};

const CountryPage = ({ country }) => {
  const [companies, setCompanies] = useState([]);
  const [macro, setMacro] = useState(null);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [activeTab, setActiveTab] = useState("history");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    axios.get("/api/companies")
      .then((res) => {
        const filtered = res.data.filter((c) => c.country === country);
        setCompanies(filtered);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load company data. Please try again.");
        setLoading(false);
      });
    axios
      .get(`/api/macros?country=${country}`)
      .then((res) => setMacro(res.data))
      .catch(() => setMacro(null));
  }, [country]);

  const maxWeeklyReturn =
    companies.length > 0
      ? Math.max(...companies.map((c) => c.weeklyReturn ?? -Infinity))
      : null;

  const handleRowClick = (ticker) => {
    if (selectedTicker === ticker) {
      setSelectedTicker(null);
    } else {
      setSelectedTicker(ticker);
      setActiveTab("history");
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-[40vh] text-gray-400 text-sm">
      Loading {country} data…
    </div>
  );

  if (error) return (
    <div className="flex items-center justify-center min-h-[40vh] text-red-400 text-sm">
      {error}
    </div>
  );

  if (!loading && companies.length === 0) return (
    <div className="flex items-center justify-center min-h-[40vh] text-gray-400 text-sm">
      No data available for {country}.
    </div>
  );

  return (
    <div className="px-6 py-8">
      <h1 className="text-3xl font-bold mb-4">{country}</h1>

      {/* Macro indicators */}
      {macro && (
        <div className="flex flex-wrap gap-4 mb-6">
          {Object.entries(macroNames).map(([k, label]) => (
            <div
              key={k}
              className="bg-gray-100 p-3 rounded shadow text-center min-w-[160px]"
            >
              <div className="text-gray-600 text-sm">{label}</div>
              <div className="text-xl font-semibold">
                {macro[k] !== null ? macro[k].toLocaleString() : "—"}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary Stats from analytics API */}
      <SummaryStats country={country} />

      {companies.length > 0 && (
        <WeeklyReturnHistogram
          companies={companies}
          title={`Weekly Return Distribution — ${country}`}
        />
      )}

      {/* Company table */}
      <div className="overflow-x-auto mb-4">
        <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-md text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2 text-left">Company</th>
              <th className="px-4 py-2 text-left">Sector</th>
              <th className="px-4 py-2 text-right">
                Stock Price
                <InfoTooltip text={tableTooltips["Stock Price"]} />
              </th>
              <th className="px-4 py-2 text-right">
                Weekly Return (%)
                <InfoTooltip text={tableTooltips["Weekly Return (%)"]} />
              </th>
            </tr>
          </thead>
          <tbody>
            {companies.map((c, idx) => (
              <React.Fragment key={c.ticker}>
                <tr
                  className={`cursor-pointer hover:bg-blue-50 transition ${
                    idx % 2 === 0 ? "bg-white" : "bg-gray-50"
                  } ${selectedTicker === c.ticker ? "ring-2 ring-blue-400" : ""}`}
                  onClick={() => handleRowClick(c.ticker)}
                  title="Click to view price history & forecast"
                >
                  <td className="px-4 py-2 font-medium">
                    {c.name}
                    <span className="ml-2 text-xs text-gray-400">{c.ticker}</span>
                  </td>
                  <td className="px-4 py-2">{c.sector}</td>
                  <td className="px-4 py-2 text-right">
                    {c.stockPrice?.toLocaleString() || "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <span className="flex items-center justify-end space-x-1">
                      <WeeklyReturnIndicator value={c.weeklyReturn} />
                      {c.weeklyReturn === maxWeeklyReturn && (
                        <span title="Best Weekly Return" className="ml-2 text-yellow-500">
                          🏆
                        </span>
                      )}
                    </span>
                  </td>
                </tr>

                {/* Expanded detail row */}
                {selectedTicker === c.ticker && (
                  <tr>
                    <td colSpan={4} className="px-4 py-4 bg-white border-t border-b border-blue-100">
                      <div className="flex gap-2 mb-3">
                        <button
                          onClick={() => setActiveTab("history")}
                          className={`px-3 py-1 text-sm rounded-full transition ${
                            activeTab === "history"
                              ? "bg-blue-600 text-white"
                              : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                          }`}
                        >
                          Price History
                        </button>
                        <button
                          onClick={() => setActiveTab("forecast")}
                          className={`px-3 py-1 text-sm rounded-full transition ${
                            activeTab === "forecast"
                              ? "bg-purple-600 text-white"
                              : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                          }`}
                        >
                          Forecast
                        </button>
                      </div>
                      {activeTab === "history" && (
                        <PriceHistoryChart ticker={c.ticker} />
                      )}
                      {activeTab === "forecast" && (
                        <ForecastChart ticker={c.ticker} />
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Weekly return bar chart */}
      <div className="w-full h-[320px] mt-8">
        <h2 className="text-lg font-semibold mb-2 text-gray-700">
          Weekly Returns Overview
        </h2>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={companies}
            margin={{ top: 20, right: 30, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" fontSize={12} />
            <YAxis />
            <RechartsTooltip
              formatter={(value, name) =>
                name === "weeklyReturn"
                  ? [`${value?.toFixed(2) ?? "—"}%`, "Weekly Return"]
                  : [value, name]
              }
            />
            <Bar dataKey="weeklyReturn" fill="#2563eb" name="Weekly Return (%)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default CountryPage;
