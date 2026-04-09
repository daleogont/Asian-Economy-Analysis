import React, { useState } from "react";
import { Menu, ChevronRight, ChevronDown, Home, BookOpen } from "lucide-react";
import { Link } from "react-router-dom";

const Header = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [openSubmenu, setOpenSubmenu] = useState(null);

  const sections = [
    { name: "Finance", path: "/section/finance" },
    { name: "Technology", path: "/section/technology" },
    { name: "Energy", path: "/section/energy" },
    { name: "Health", path: "/section/health" },
    { name: "Real Estate", path: "/section/realestate" },
    { name: "Utilities", path: "/section/utilities" },
    { name: "Industrials", path: "/section/industrials" },
    { name: "Consumer", path: "/section/consumer" },
    { name: "Materials", path: "/section/materials" },
    { name: "Communication", path: "/section/communication" },
  ];

  const countries = [
    { name: "Japan", path: "/country/japan" },
    { name: "China", path: "/country/china" },
    { name: "India", path: "/country/india" },
    { name: "Thailand", path: "/country/thailand" },
    { name: "Singapore", path: "/country/singapore" },
    { name: "Indonesia", path: "/country/indonesia" },
    { name: "Malaysia", path: "/country/malaysia" },
    { name: "Taiwan", path: "/country/taiwan" },
    { name: "South Korea", path: "/country/southkorea" },
    { name: "Saudi Arabia", path: "/country/saudiarabia" },
];

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const toggleSubmenu = (menu) =>
    setOpenSubmenu((prev) => (prev === menu ? null : menu));

  return (
    <>
      <header className="bg-black text-white h-16 flex items-center justify-between fixed top-0 left-0 w-full z-50 px-4">
        <button onClick={toggleSidebar}>
          <Menu className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold text-center absolute left-1/2 transform -translate-x-1/2">
          Asian Economy Analysis
        </h1>
      </header>

      {isSidebarOpen && (
        <div className="fixed top-0 left-0 h-full w-64 bg-white shadow-lg z-50 pt-16 overflow-y-auto transition-all duration-300">
          <nav className="text-black text-base font-medium px-4 space-y-2">
            <Link
              to="/"
              className="flex items-center space-x-2 hover:bg-gray-100 px-2 py-2 rounded"
              onClick={() => setIsSidebarOpen(false)}
            >
              <Home className="w-5 h-5" />
              <span>Home</span>
            </Link>

            <div>
              <button
                onClick={() => toggleSubmenu("section")}
                className="w-full flex justify-between items-center hover:bg-gray-100 px-2 py-2 rounded"
              >
                <span>Section</span>
                {openSubmenu === "section" ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
              {openSubmenu === "section" && (
                <ul className="pl-4 mt-1">
                  {sections.map((s) => (
                    <li key={s.name}>
                      <Link
                        to={s.path}
                        onClick={() => setIsSidebarOpen(false)}
                        className="block px-2 py-1 hover:bg-gray-100 rounded capitalize"
                      >
                        {s.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <button
                onClick={() => toggleSubmenu("country")}
                className="w-full flex justify-between items-center hover:bg-gray-100 px-2 py-2 rounded"
              >
                <span>Country</span>
                {openSubmenu === "country" ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
              {openSubmenu === "country" && (
                <ul className="pl-4 mt-1">
                  {countries.map((c) => (
                    <li key={c.name}>
                      <Link
                        to={c.path}
                        onClick={() => setIsSidebarOpen(false)}
                        className="block px-2 py-1 hover:bg-gray-100 rounded capitalize"
                      >
                        {c.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <Link
              to="/research"
              className="flex items-center space-x-2 hover:bg-gray-100 px-2 py-2 rounded"
              onClick={() => setIsSidebarOpen(false)}
            >
              <BookOpen className="w-5 h-5" />
              <span>Research</span>
            </Link>
          </nav>
        </div>
      )}
    </>
  );
};

export default Header;
