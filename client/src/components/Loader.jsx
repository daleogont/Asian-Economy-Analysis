import React from "react";

const Loader = () => {
  return (
    <div className="fixed inset-0 bg-white flex items-center justify-center z-50">
      <div className="flex flex-col items-center">
        <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        <span className="mt-4 text-gray-600">Loading, please wait...</span>
      </div>
    </div>
  );
};

export default Loader;