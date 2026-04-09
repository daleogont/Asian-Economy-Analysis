import React, { useEffect, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { useNavigate } from "react-router-dom";

const geoUrl = "/asia10.json";


const countryColors = [
  "#3b82f6", "#10b981", "#eab308", "#6366f1", "#14b8a6",
  "#f43f5e", "#2563eb", "#d946ef", "#22c55e", "#f59e42"
];

const AsiaMap = () => {
  const [countryData, setCountryData] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("/api/countries")
      .then((res) => res.json())
      .then((data) => setCountryData(data))
      .catch((err) => console.error("Error fetching countries:", err));
  }, []);

  const capByCountry = {};
  countryData.forEach((c) => {
    capByCountry[c.country] = c.totalCap;
  });

  return (
    <div className="w-full flex flex-col items-center">
      <h2 className="text-2xl font-bold mb-4">Asia Market Map</h2>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          center: [100, 30], // centered on Asia
          scale: 330,
        }}
        width={800}
        height={400}
      >
        <Geographies geography={geoUrl}>
          {({ geographies }) =>
            geographies.map((geo, idx) => {
              const countryName = geo.properties.name;
              const cap = capByCountry[countryName] || 0;
              const fill = countryColors[idx % countryColors.length];

              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  children={<title>{countryName}</title>}
                  onClick={() => {
                    if (cap) {
                      const slug = countryName.toLowerCase().replace(/ /g, "");
                      navigate(`/country/${slug}`);
                    }
                  }}
                  style={{
                    default: {
                      fill: fill,
                      outline: "none",
                      opacity: cap ? 1 : 0.4,
                      cursor: cap ? "pointer" : "not-allowed",
                    },
                    hover: {
                      fill: "#2563eb",
                      opacity: 1,
                      outline: "none",
                    },
                    pressed: {
                      fill: "#1d4ed8",
                      outline: "none",
                    },
                  }}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>

      <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-3 w-full max-w-2xl">
        {countryData.map((c, i) => (
          <div
            key={c.country}
            className="flex flex-col items-center bg-gray-50 rounded p-2 shadow text-xs"
          >
            <div
              className="w-4 h-4 rounded mb-1"
              style={{ backgroundColor: countryColors[i % countryColors.length] }}
            ></div>
            <span className="font-bold">{c.country}</span>
            <span className="text-gray-500">
              Cap: {c.totalCap.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AsiaMap;
