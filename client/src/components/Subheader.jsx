import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import logo from "../assets/logo.svg";

const sectionOrder = [
  "finance", "technology", "energy", "health", "realestate",
  "consumer", "industrials", "communication", "materials", "utilities"
];
const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);

const countryCol1 = ["japan", "china", "india", "thailand", "singapore"];
const countryCol2 = ["indonesia", "malaysia", "saudiarabia", "southkorea", "taiwan"];

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

        <li
          className="relative cursor-pointer"
          onMouseEnter={() => handleMouseEnter("section")}
          onMouseLeave={handleMouseLeave}
        >
          Section
          {hoveredMenu === "section" && (
            <div className="absolute bg-white border mt-2 shadow-md text-sm p-2 w-80 z-50 flex">
              <div className="w-full flex flex-col">
                <Link
                  to="/sections"
                  className="font-semibold px-2 py-1 mb-1 rounded hover:bg-gray-100 text-blue-600"
                >
                  All sections
                </Link>
              </div>
              <ul className="flex flex-col flex-1 pr-2">
                {sectionOrder.slice(0, 5).map((s) => (
                  <li key={s} className="hover:bg-gray-100 px-2 py-1 cursor-pointer">
                    <Link to={`/section/${s}`} className="block w-full h-full capitalize">
                      {capitalize(s)}
                    </Link>
                  </li>
                ))}
              </ul>
              <ul className="flex flex-col flex-1 pl-2 border-l">
                {sectionOrder.slice(5).map((s) => (
                  <li key={s} className="hover:bg-gray-100 px-2 py-1 cursor-pointer">
                    <Link to={`/section/${s}`} className="block w-full h-full capitalize">
                      {capitalize(s)}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </li>

        <li
          className="relative cursor-pointer"
          onMouseEnter={() => handleMouseEnter("country")}
          onMouseLeave={handleMouseLeave}
        >
          Country
          {hoveredMenu === "country" && (
            <div className="absolute bg-white border mt-2 shadow-md text-sm p-2 w-80 z-50 flex">
              <div className="w-full flex flex-col">
                <Link
                  to="/countries"
                  className="font-semibold px-2 py-1 mb-1 rounded hover:bg-gray-100 text-blue-600"
                >
                  All countries
                </Link>
              </div>
              <ul className="flex flex-col flex-1 pr-2">
                {countryCol1.map((c) => (
                  <li key={c} className="hover:bg-gray-100 px-2 py-1 cursor-pointer capitalize">
                    <Link to={`/country/${c}`} className="block w-full h-full">
                      {c}
                    </Link>
                  </li>
                ))}
              </ul>
              <ul className="flex flex-col flex-1 pl-2 border-l">
                {countryCol2.map((c) => (
                  <li key={c} className="hover:bg-gray-100 px-2 py-1 cursor-pointer capitalize">
                    <Link to={`/country/${c}`} className="block w-full h-full">
                      {c}
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
