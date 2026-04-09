import React, { useEffect, useState } from "react";
import axios from "axios";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Link } from "react-router-dom";

const sectorOrder = [
  "Finance", "Technology", "Energy", "Health", "Real Estate",
  "Consumer", "Industrials", "Communication", "Materials", "Utilities"
];

const countryColors = [
  "#2563eb", 
  "#22c55e", // China
  "#f59e42", // India
  "#d946ef", // Thailand
  "#3b82f6", // Singapore
  "#f43f5e", // Indonesia
  "#10b981", // Malaysia
  "#eab308", // Saudi Arabia
  "#6366f1", // South Korea
  "#14b8a6"  // Taiwan
];

const countryOrder = [
  "Japan", "China", "India", "Thailand", "Singapore",
  "Indonesia", "Malaysia", "Saudi Arabia", "South Korea", "Taiwan"
];

const getCenteredGridClasses = (idx, total) => {
  if (total === 10 && idx === 9) return "col-span-full flex justify-center";
  return "";
};

const Sections = () => {
  const [countries, setCountries] = useState([]);

  useEffect(() => {
    axios.get("/api/countries").then(res => setCountries(res.data));
  }, []);

  const sectorCards = sectorOrder.map((sector, sectorIdx) => {
    const data = countryOrder.map((country, idx) => {
      const countryObj = countries.find((c) => c.country === country);
      return {
        country,
        value: countryObj?.sectors[sector] || 0,
        color: countryColors[idx]
      };
    });

    const sectorUrl = "/section/" + sector.toLowerCase().replace(/ /g, "");

    const total = data.reduce((sum, d) => sum + d.value, 0);

    const centerClass = getCenteredGridClasses(sectorIdx, sectorOrder.length);

    return (
      <div
        key={sector}
        className={`rounded-xl shadow-lg bg-white p-6 flex flex-col ${centerClass}`}
        style={centerClass ? { gridColumn: "2 / 3" } : {}}
      >
        <Link to={sectorUrl} className="text-2xl font-bold mb-2 hover:text-blue-700 transition">{sector}</Link>
        <div className="flex flex-row items-center mb-2 space-x-6">
          <span className="text-sm text-gray-500">Total Cap:</span>
          <span className="font-semibold">{total ? total.toLocaleString("en-US", { maximumFractionDigits: 0 }) : "-"} $</span>
        </div>
        <div className="w-full h-44">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 12, right: 8, left: 8, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="country" fontSize={10} interval={0} angle={-30} textAnchor="end" height={48} />
              <YAxis hide />
              <Tooltip
                formatter={(value) => value ? value.toLocaleString() + " $" : "-"}
                labelFormatter={label => label}
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
          {data.map((c, idx) => (
            <span key={idx} className="flex items-center space-x-1">
              <span style={{
                backgroundColor: c.color,
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: 2,
                marginRight: 4
              }} />
              {c.country}
            </span>
          ))}
        </div>
      </div>
    );
  });

  return (
    <div className="px-8 py-8">
      <h1 className="text-3xl font-bold mb-8">Sections Overview</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {sectorCards}
      </div>
    </div>
  );
};

export default Sections;
