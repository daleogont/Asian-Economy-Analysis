import React, { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import axios from "axios";

import Header from "./components/Header";
import Subheader from "./components/Subheader";
import Footer from "./components/Footer";
import Loader from "./components/Loader";

import Home from "./pages/Home";
import Research from "./pages/Research";

import Sections from "./pages/Sections";
import Finance from "./pages/section/Finance";
import Technology from "./pages/section/Technology";
import Energy from "./pages/section/Energy";
import Health from "./pages/section/Health";
import RealEstate from "./pages/section/RealEstate";
import Utilities from "./pages/section/Utilities";
import Industrials from "./pages/section/Industrials";
import Consumer from "./pages/section/Consumer";
import Materials from "./pages/section/Materials";
import Communication from "./pages/section/Communication";

import Countries from "./pages/Countries";
import Japan from "./pages/country/Japan";
import China from "./pages/country/China";
import India from "./pages/country/India";
import Thailand from "./pages/country/Thailand";
import Singapore from "./pages/country/Singapore";
import Indonesia from "./pages/country/Indonesia";
import Malaysia from "./pages/country/Malaysia";
import Taiwan from "./pages/country/Taiwan";
import SouthKorea from "./pages/country/SouthKorea";
import SaudiArabia from "./pages/country/SaudiArabia";

const App = () => {
  const [isServerReady, setIsServerReady] = useState(false);

  useEffect(() => {
    axios
      .get("/api/health")
      .then(() => {
        setIsServerReady(true);
      })
      .catch((err) => {
        console.error("Health check failed:", err.message);
        setTimeout(() => {
          axios
            .get("/api/health")
            .then(() => setIsServerReady(true))
            .catch(() => console.error("Health check retry failed."));
        }, 2000);
      });
  }, []);

  if (!isServerReady) {
    return <Loader />;
  }

  return (
    <div className="pt-32 pb-20">
      <Header />
      <Subheader />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/research" element={<Research />} />

        <Route path="/sections" element={<Sections />} />
        <Route path="/section/finance" element={<Finance />} />
        <Route path="/section/technology" element={<Technology />} />
        <Route path="/section/energy" element={<Energy />} />
        <Route path="/section/health" element={<Health />} />
        <Route path="/section/realestate" element={<RealEstate />} />
        <Route path="/section/utilities" element={<Utilities />} />
        <Route path="/section/industrials" element={<Industrials />} />
        <Route path="/section/consumer" element={<Consumer />} />
        <Route path="/section/materials" element={<Materials />} />
        <Route path="/section/communication" element={<Communication />} />

        <Route path="/countries" element={<Countries />} />
        <Route path="/country/japan" element={<Japan />} />
        <Route path="/country/china" element={<China />} />
        <Route path="/country/india" element={<India />} />
        <Route path="/country/thailand" element={<Thailand />} />
        <Route path="/country/singapore" element={<Singapore />} />
        <Route path="/country/indonesia" element={<Indonesia />} />
        <Route path="/country/malaysia" element={<Malaysia />} />
        <Route path="/country/taiwan" element={<Taiwan />} />
        <Route path="/country/southkorea" element={<SouthKorea />} />
        <Route path="/country/saudiarabia" element={<SaudiArabia />} />
      </Routes>

      <Footer />
    </div>
  );
};

export default App;
