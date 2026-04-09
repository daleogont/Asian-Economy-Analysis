import React, { useEffect, useState } from "react";
import axios from "axios";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Link } from "react-router-dom";

const sectorColors = [
  "#2563eb", "#22c55e", "#f59e42", "#d946ef", "#3b82f6",
  "#f43f5e", "#10b981", "#eab308", "#6366f1", "#14b8a6"
];

const sectorOrder = [
  "Finance", "Technology", "Energy", "Health", "Real Estate",
  "Consumer", "Industrials", "Communication", "Materials", "Utilities"
];

const getCenteredGridClasses = (idx, total) => {
  if (total === 10 && idx === 9) return "col-span-full flex justify-center";
  return "";
};

const Countries = () => {
  const [countries, setCountries] = useState([]);

  useEffect(() => {
    axios.get("/api/countries").then(res => setCountries(res.data));
  }, []);

  return (
    <div className="px-8 py-8">
      <h1 className="text-3xl font-bold mb-8">Countries Overview</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {countries.map((country, i) => {
          const data = sectorOrder.map((sector, idx) => ({
            sector,
            value: country.sectors[sector] || 0,
            color: sectorColors[idx]
          }));

          
          const countryUrl = "/country/" + country.country.toLowerCase().replace(/ /g, "-");

          const centerClass = getCenteredGridClasses(i, countries.length);

          return (
            <div
              key={country.country}
              className={`rounded-xl shadow-lg bg-white p-6 flex flex-col ${centerClass}`}
              style={centerClass ? { gridColumn: "2 / 3" } : {}}
            >
              <Link to={countryUrl} className="text-2xl font-bold mb-2 hover:text-blue-700 transition">{country.country}</Link>
              <div className="flex flex-row items-center mb-2 space-x-6">
                <span className="text-sm text-gray-500">Total Cap:</span>
                <span className="font-semibold">{country.totalCap.toLocaleString("en-US", { maximumFractionDigits: 0 })} $</span>
                <span className={country.averageWeeklyReturn > 0 ? "text-green-600" : "text-red-600"}>
                  {country.averageWeeklyReturn > 0 ? "▲" : "▼"} {Math.abs(country.averageWeeklyReturn).toFixed(2)}%
                </span>
              </div>
              <div className="w-full h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data}
                    margin={{ top: 12, right: 8, left: 8, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="sector" fontSize={10} interval={0} angle={-30} textAnchor="end" height={48} />
                    <YAxis hide />
                    <Tooltip
                      formatter={(value) => value ? value.toLocaleString() + " $" : "-"}
                      labelFormatter={label => sectorOrder[label]}
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
                {data.map((s, idx) => (
                  <span key={idx} className="flex items-center space-x-1">
                    <span style={{
                      backgroundColor: s.color,
                      display: "inline-block",
                      width: 10,
                      height: 10,
                      borderRadius: 2,
                      marginRight: 4
                    }} />
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
