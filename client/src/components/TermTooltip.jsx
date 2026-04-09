import React from "react";
export default function TermTooltip({ term, description }) {
  return (
    <span className="relative group cursor-pointer ml-1">
      <span className="inline-block text-xs bg-blue-200 text-blue-800 rounded-full px-1">?</span>
      <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 bg-white border text-black text-xs px-2 py-1 rounded shadow-lg hidden group-hover:block z-50 whitespace-nowrap">
        <strong>{term}:</strong> {description}
      </span>
    </span>
  );
}
