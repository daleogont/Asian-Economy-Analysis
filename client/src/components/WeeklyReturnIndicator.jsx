// src/components/WeeklyReturnIndicator.jsx
import React from "react";
export default function WeeklyReturnIndicator({ value }) {
  if (value == null) return "-";
  const isPositive = value > 0;
  const color = isPositive ? "text-green-600" : value < 0 ? "text-red-600" : "text-gray-600";
  const arrow = isPositive ? "▲" : value < 0 ? "▼" : "";
  return (
    <span className={color + " font-bold"}>
      {value.toFixed(2)}% {arrow}
    </span>
  );
}
