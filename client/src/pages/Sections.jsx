import React, { useEffect, useState } from "react";
import axios from "axios";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Link } from "react-router-dom";

const sectorOrder = [
  "Financials",
  "Information Technology",
  "Energy",
  "Health Care",
  "Real Estate",
  "Consumer Discretionary",
  "Consumer Staples",
  "Industrials",
  "Communication Services",
  "Materials",
  "Utilities",
];

const sectorUrlMap = {
  "Financials": "/section/financials",
  "Information Technology": "/section/information-technology",
  "Energy": "/section/energy",
  "Health Care": "/section/health-care",
  "Real Estate": "/section/real-estate",
  "Consumer Discretionary": "/section/consumer-discretionary",
  "Consumer Staples": "/section/consumer-staples",
  "Industrials": "/section/industrials",
  "Communication Services": "/section/communication-services",
  "Materials": "/section/materials",
  "Utilities": "/section/utilities",
};

const countryColors = [
  "#2563eb",
  "#22c55e",
  "#f59e42",
  "#d946ef",
  "#3b82f6",
  "#f43f5e",
  "#10b981",
  "#eab308",
  "#6366f1",
  "#14b8a6",
  "#64748b",
  "#ec4899",
  "#0ea5e9",
  "#a3e635",
  "#fb923c",
];

const countryOrder = [
  "Japan", "China", "India", "Thailand", "Singapore",
  "Indonesia", "Malaysia", "Saudi Arabia", "South Korea", "Taiwan",
  "Hong Kong", "Vietnam", "Philippines", "UAE", "Pakistan",
];

const Sections = () => {
  const [countries, setCountries] = useState([]);

  useEffect(() => {
    axios.get("/api/countries").then((res) => setCountries(res.data));
  }, []);

  const sectorCards = sectorOrder.map((sector) => {
    const data = countryOrder.map((country, idx) => {
      const countryObj = countries.find((c) => c.country === country);
      return {
        country,
        value: countryObj?.sectors?.[sector] || 0,
        color: countryColors[idx],
      };
    });

    const sectorUrl = sectorUrlMap[sector] ?? "#";
    const total = data.reduce((sum, d) => sum + d.value, 0);

    return (
      <div key={sector} className="rounded-xl shadow-lg bg-white p-6 flex flex-col">
        <Link
          to={sectorUrl}
          className="text-2xl font-bold mb-2 hover:text-blue-700 transition"
        >
          {sector}
        </Link>
        <div className="flex flex-row items-center mb-2 space-x-6">
          <span className="text-sm text-gray-500">Total companies:</span>
          <span className="font-semibold">{total || "—"}</span>
        </div>
        <div className="w-full h-44">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 12, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="country"
                fontSize={10}
                interval={0}
                angle={-30}
                textAnchor="end"
                height={48}
              />
              <YAxis hide />
              <Tooltip
                formatter={(value, _name, props) => [
                  `${value} companies`,
                  props.payload.country,
                ]}
              />
              <Bar dataKey="value">
                {data.map((entry, idx) => (
                  <Cell key={idx} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-gray-500">
          {data
            .filter((d) => d.value > 0)
            .map((c, idx) => (
              <span key={idx} className="flex items-center">
                <span
                  style={{
                    backgroundColor: c.color,
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    marginRight: 4,
                  }}
                />
                {c.country}
              </span>
            ))}
        </div>
      </div>
    );
  });

  return (
    <div className="px-8 py-8">
      <h1 className="text-3xl font-bold mb-8">Sectors Overview</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">{sectorCards}</div>
    </div>
  );
};

export default Sections;
