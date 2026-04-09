import React, { useEffect, useState } from "react";
import axios from "axios";
import WeeklyReturnIndicator from "../components/WeeklyReturnIndicator";
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
  gdp: <>GDP ($)
    <InfoTooltip text="Gross domestic product, billions USD. Source: World Bank (2022/2023)" />
  </>,
  population: <>Population
    <InfoTooltip text="Total population, millions. Source: World Bank (2022/2023)" />
  </>,
  unemployment: <>Unemployment (%)
    <InfoTooltip text="Unemployment rate, %" />
  </>
};

const tableTooltips = {
  "Market Cap ($)": "Total market value of the company in USD.",
  "Stock Price": "Current price of one share.",
  "Weekly Return (%)": "Percentage change in share price over the past week.",
};

const CountryPage = ({ country }) => {
  const [companies, setCompanies] = useState([]);
  const [macro, setMacro] = useState(null);

  useEffect(() => {
    axios.get("/api/companies")
      .then(res => {
        const filtered = res.data.filter(c => c.country === country);
        setCompanies(filtered);
      });
    axios.get(`/api/macros?country=${country}`)
      .then(res => setMacro(res.data))
      .catch(() => setMacro(null));
  }, [country]);

  const maxWeeklyReturn =
    companies.length > 0
      ? Math.max(...companies.map(c => c.weeklyReturn ?? -Infinity))
      : null;

  return (
    <div className="px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">{country}</h1>
      <div className="flex space-x-6 mb-4">
        {macro &&
          Object.entries(macroNames).map(([k, label]) =>
            <div key={k} className="bg-gray-100 p-3 rounded shadow text-center min-w-[160px]">
              <div className="text-gray-600 text-sm">{label}</div>
              <div className="text-xl font-semibold">
                {macro[k] !== null ? macro[k].toLocaleString() : "-"}
              </div>
            </div>
          )}
      </div>
      <div className="overflow-x-auto mb-8">
        <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-md text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2 text-left">Company</th>
              <th className="px-4 py-2 text-left">Sector</th>
              <th className="px-4 py-2 text-right">
                Market Cap ($)
                <InfoTooltip text={tableTooltips["Market Cap ($)"]} />
              </th>
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
              <tr key={c.ticker} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                <td className="px-4 py-2">{c.name}</td>
                <td className="px-4 py-2">{c.sector}</td>
                <td className="px-4 py-2 text-right">{c.marketCap?.toLocaleString() || "-"}</td>
                <td className="px-4 py-2 text-right">{c.stockPrice?.toLocaleString() || "-"}</td>
                <td className="px-4 py-2 text-right flex items-center justify-end space-x-1">
                  <WeeklyReturnIndicator value={c.weeklyReturn} />
                  {c.weeklyReturn === maxWeeklyReturn && (
                    <span title="Best Weekly Return" className="ml-2 text-yellow-500">🏆</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="w-full h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={companies} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" fontSize={12} />
            <YAxis />
            <RechartsTooltip
              formatter={(value, name) =>
                name === "weeklyReturn"
                  ? [`${value?.toFixed(2) ?? "-"}%`, "Weekly Return"]
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
