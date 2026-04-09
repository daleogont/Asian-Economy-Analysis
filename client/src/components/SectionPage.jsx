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
    <span className="absolute left-1/2 transform -translate-x-1/2 mt-1 w-40 bg-gray-800 text-white text-xs rounded p-2 opacity-0 group-hover:opacity-100 transition pointer-events-none z-50">
      {text}
    </span>
  </span>
);

const tableTooltips = {
  "Market Cap ($)": "Total market value of the company in USD.",
  "Stock Price": "Current price of one share.",
  "Weekly Return (%)": "Percentage change in share price over the past week.",
};

const SectionPage = ({ sector }) => {
  const [companies, setCompanies] = useState([]);

  useEffect(() => {
    axios.get("/api/companies")
      .then(res => {
        const filtered = res.data
          .filter(c => c.sector === sector)
          .sort((a, b) => (b.marketCap ?? 0) - (a.marketCap ?? 0));
        setCompanies(filtered);
      });
  }, [sector]);

  const maxWeeklyReturn =
    companies.length > 0
      ? Math.max(...companies.map(c => c.weeklyReturn ?? -Infinity))
      : null;

  const leader = companies[0];

  const chartData = companies.map(c => ({
    ...c,
    marketCapBln: c.marketCap ? c.marketCap / 1_000_000_000 : 0,
  }));

  return (
    <div className="px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">{sector}</h1>

      {leader && (
        <div className="mb-4 flex items-center space-x-4">
          <span className="font-semibold">
            Sector leader: {leader.name}
          </span>
          <span className="text-gray-500 text-sm">
            (Market Cap: {leader.marketCap ? leader.marketCap.toLocaleString() : "-"} $)
          </span>
        </div>
      )}

      <div className="overflow-x-auto mb-8">
        <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-md text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2 text-left">Company</th>
              <th className="px-4 py-2 text-left">Country</th>
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
                <td className="px-4 py-2">{c.country}</td>
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
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" fontSize={12} />
            <YAxis tickFormatter={v => `${v}B`} />
            <RechartsTooltip
              formatter={(value, name) =>
                name === "marketCapBln"
                  ? [`${value.toFixed(1)}B $`, "Market Cap"]
                  : [value, name]
              }
            />
            <Bar dataKey="marketCapBln" fill="#6366f1" name="Market Cap (bln $)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SectionPage;
