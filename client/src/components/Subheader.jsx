import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import logo from "../assets/logo.svg";

const sectors = [
  { label: "Financials",             path: "/section/financials" },
  { label: "Information Technology", path: "/section/information-technology" },
  { label: "Energy",                 path: "/section/energy" },
  { label: "Health Care",            path: "/section/health-care" },
  { label: "Real Estate",            path: "/section/real-estate" },
  { label: "Consumer Discretionary", path: "/section/consumer-discretionary" },
  { label: "Consumer Staples",       path: "/section/consumer-staples" },
  { label: "Industrials",            path: "/section/industrials" },
  { label: "Communication Services", path: "/section/communication-services" },
  { label: "Materials",              path: "/section/materials" },
  { label: "Utilities",              path: "/section/utilities" },
];

const countries = [
  { label: "Japan",        path: "/country/japan" },
  { label: "China",        path: "/country/china" },
  { label: "India",        path: "/country/india" },
  { label: "Thailand",     path: "/country/thailand" },
  { label: "Singapore",    path: "/country/singapore" },
  { label: "Indonesia",    path: "/country/indonesia" },
  { label: "Malaysia",     path: "/country/malaysia" },
  { label: "Taiwan",       path: "/country/taiwan" },
  { label: "South Korea",  path: "/country/south-korea" },
  { label: "Saudi Arabia", path: "/country/saudi-arabia" },
  { label: "Hong Kong",    path: "/country/hong-kong" },
  { label: "Vietnam",      path: "/country/vietnam" },
  { label: "UAE",          path: "/country/uae" },
  { label: "Pakistan",     path: "/country/pakistan" },
];

const half = Math.ceil(sectors.length / 2);
const sectorsCol1 = sectors.slice(0, half);
const sectorsCol2 = sectors.slice(half);

const countryHalf = Math.ceil(countries.length / 2);
const countriesCol1 = countries.slice(0, countryHalf);
const countriesCol2 = countries.slice(countryHalf);

const Subheader = () => {
  const [hoveredMenu, setHoveredMenu] = useState(null);
  const timeoutRef = useRef(null);

  const handleMouseEnter = (menu) => {
    clearTimeout(timeoutRef.current);
    setHoveredMenu(menu);
  };
  const handleMouseLeave = () => {
    timeoutRef.current = setTimeout(() => {
      setHoveredMenu(null);
    }, 400);
  };

  return (
    <nav className="bg-white text-black h-16 flex items-center justify-center fixed top-16 left-0 w-full z-40">
      <ul className="flex justify-center items-center space-x-6 py-2 font-medium text-lg">
        <li>
          <Link to="/">
            <img src={logo} alt="Logo" className="h-8 w-auto" />
          </Link>
        </li>

        {/* Sectors dropdown */}
        <li
          className="relative cursor-pointer pb-2"
          onMouseEnter={() => handleMouseEnter("section")}
          onMouseLeave={handleMouseLeave}
        >
          Sectors
          {hoveredMenu === "section" && (
            <div className="absolute bg-white border shadow-lg text-sm p-3 w-[480px] z-50 flex gap-2 top-full left-0">
              <div className="w-full flex flex-col">
                <Link
                  to="/sections"
                  className="font-semibold px-2 py-1 mb-1 rounded hover:bg-gray-100 text-blue-600 whitespace-nowrap"
                >
                  All sectors
                </Link>
              </div>
              <ul className="flex flex-col flex-1 pr-2 min-w-[160px]">
                {sectorsCol1.map((s) => (
                  <li key={s.path} className="hover:bg-gray-100 px-2 py-1 cursor-pointer">
                    <Link to={s.path} className="block w-full h-full whitespace-nowrap">
                      {s.label}
                    </Link>
                  </li>
                ))}
              </ul>
              <ul className="flex flex-col flex-1 pl-2 border-l min-w-[160px]">
                {sectorsCol2.map((s) => (
                  <li key={s.path} className="hover:bg-gray-100 px-2 py-1 cursor-pointer">
                    <Link to={s.path} className="block w-full h-full whitespace-nowrap">
                      {s.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </li>

        {/* Countries dropdown */}
        <li
          className="relative cursor-pointer pb-2"
          onMouseEnter={() => handleMouseEnter("country")}
          onMouseLeave={handleMouseLeave}
        >
          Countries
          {hoveredMenu === "country" && (
            <div className="absolute bg-white border shadow-lg text-sm p-3 w-64 z-50 flex gap-2 top-full left-0">
              <div className="w-full flex flex-col">
                <Link
                  to="/countries"
                  className="font-semibold px-2 py-1 mb-1 rounded hover:bg-gray-100 text-blue-600 whitespace-nowrap"
                >
                  All countries
                </Link>
              </div>
              <ul className="flex flex-col flex-1 pr-2">
                {countriesCol1.map((c) => (
                  <li key={c.path} className="hover:bg-gray-100 px-2 py-1 cursor-pointer">
                    <Link to={c.path} className="block w-full h-full whitespace-nowrap">
                      {c.label}
                    </Link>
                  </li>
                ))}
              </ul>
              <ul className="flex flex-col flex-1 pl-2 border-l">
                {countriesCol2.map((c) => (
                  <li key={c.path} className="hover:bg-gray-100 px-2 py-1 cursor-pointer">
                    <Link to={c.path} className="block w-full h-full whitespace-nowrap">
                      {c.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </li>

        <li className="hover:underline cursor-pointer">
          <Link to="/research" className="hover:text-blue-400">
            Research
          </Link>
        </li>

      </ul>
    </nav>
  );
};

export default Subheader;
