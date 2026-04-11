import React, { useEffect, useState } from "react";
import axios from "axios";

const StatCard = ({ label, value }) => (
  <div className="bg-white rounded-lg shadow p-4 text-center min-w-[130px]">
    <div className="text-xs text-gray-500 mb-1">{label}</div>
    <div className="text-lg font-semibold">{value ?? "—"}</div>
  </div>
);

const SummaryStats = ({ country, sector }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const params = country
      ? `country=${encodeURIComponent(country)}`
      : `sector=${encodeURIComponent(sector)}`;
    axios
      .get(`/analytics/summary?${params}`)
      .then((res) => setStats(res.data))
      .catch(() => setStats(null));
  }, [country, sector]);

  if (!stats) return null;

  const fmt = (v) =>
    v != null
      ? Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })
      : "—";
  const pct = (v) => (v != null ? `${Number(v).toFixed(2)}%` : "—");

  const p = stats.price ?? {};
  const r = stats.weeklyReturn ?? {};

  return (
    <div className="mb-6">
      <h2 className="text-base font-semibold mb-3 text-gray-600">
        Market Statistics&nbsp;
        <span className="text-gray-400 font-normal text-sm">
          ({stats.companyCount} companies)
        </span>
      </h2>
      <div className="flex flex-wrap gap-3">
        <StatCard label="Avg Price" value={fmt(p.mean)} />
        <StatCard label="Median Price" value={fmt(p.median)} />
        <StatCard label="Price Std Dev" value={fmt(p.std)} />
        <StatCard label="Avg Weekly Return" value={pct(r.mean)} />
        <StatCard label="Best Weekly Return" value={pct(r.max)} />
        <StatCard label="Worst Weekly Return" value={pct(r.min)} />
      </div>
    </div>
  );
};

export default SummaryStats;
