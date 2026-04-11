import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import { Link } from "react-router-dom";

const sectorColors = [
  "#2563eb", "#22c55e", "#f59e42", "#d946ef", "#3b82f6",
  "#f43f5e", "#10b981", "#eab308", "#6366f1", "#14b8a6", "#64748b",
];

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

const countrySlug = (name) => name.toLowerCase().replace(/ /g, "-");

const Countries = () => {
  const [countries, setCountries] = useState([]);

  useEffect(() => {
    axios.get("/api/countries").then((res) => setCountries(res.data));
  }, []);

  return (
    <div className="px-8 py-8">
      <h1 className="text-3xl font-bold mb-8">Countries Overview</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {countries.map((country) => {
          const data = sectorOrder.map((sector, idx) => ({
            sector,
            value: country.sectors?.[sector] || 0,
            color: sectorColors[idx],
          }));

          const countryUrl = `/country/${countrySlug(country.country)}`;
          const returnVal = country.averageWeeklyReturn;

          return (
            <div
              key={country.country}
              className="rounded-xl shadow-lg bg-white p-6 flex flex-col"
            >
              <Link
                to={countryUrl}
                className="text-2xl font-bold mb-2 hover:text-blue-700 transition"
              >
                {country.country}
              </Link>
              <div className="flex flex-row items-center mb-2 space-x-4 text-sm">
                <span className="text-gray-500">
                  {country.companyCount} companies
                </span>
                {returnVal != null && (
                  <span
                    className={
                      returnVal >= 0 ? "text-green-600" : "text-red-600"
                    }
                  >
                    {returnVal >= 0 ? "▲" : "▼"}{" "}
                    {Math.abs(returnVal).toFixed(2)}% avg weekly
                  </span>
                )}
              </div>
              <div className="w-full h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data}
                    margin={{ top: 8, right: 8, left: 8, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="sector"
                      fontSize={8}
                      interval={0}
                      angle={-35}
                      textAnchor="end"
                      height={56}
                    />
                    <YAxis allowDecimals={false} fontSize={10} width={20} />
                    <Tooltip
                      formatter={(value, _name, props) => [
                        `${value} companies`,
                        props.payload.sector,
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
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
                {data
                  .filter((s) => s.value > 0)
                  .map((s, idx) => (
                    <span key={idx} className="flex items-center">
                      <span
                        style={{
                          backgroundColor: s.color,
                          display: "inline-block",
                          width: 10,
                          height: 10,
                          borderRadius: 2,
                          marginRight: 4,
                        }}
                      />
                      {s.sector}
                    </span>
                  ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Countries;
