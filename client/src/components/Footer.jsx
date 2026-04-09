import React from "react";
import { FaGithub } from "react-icons/fa";

const Footer = () => {
  return (
    <footer className="bg-black text-white py-4 px-6 flex justify-center items-center space-x-4 fixed bottom-0 left-0 w-full z-50">
      <a
        href="https://github.com/daleogont/Asian-Economy-Analysis"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center space-x-2 hover:text-gray-300"
      >
        <FaGithub className="text-2xl" />
        <span>GitHub</span>
      </a>
    </footer>
  );
};

export default Footer;
