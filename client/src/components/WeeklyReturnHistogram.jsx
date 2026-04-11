import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const BUCKETS = [
  { label: "<-5%", min: -Infinity, max: -5 },
  { label: "-5 to -4", min: -5, max: -4 },
  { label: "-4 to -3", min: -4, max: -3 },
  { label: "-3 to -2", min: -3, max: -2 },
  { label: "-2 to -1", min: -2, max: -1 },
  { label: "-1 to 0",  min: -1, max:  0 },
  { label: "0 to 1",   min:  0, max:  1 },
  { label: "1 to 2",   min:  1, max:  2 },
  { label: "2 to 3",   min:  2, max:  3 },
  { label: "3 to 4",   min:  3, max:  4 },
  { label: "4 to 5",   min:  4, max:  5 },
  { label: ">5%",      min:  5, max:  Infinity },
];

const WeeklyReturnHistogram = ({ companies, title = "Weekly Return Distribution" }) => {
  const data = useMemo(() => {
    const returns = companies
      .map((c) => c.weeklyReturn)
      .filter((r) => r != null);

    if (returns.length === 0) return [];

    return BUCKETS.map((b) => ({
      label: b.label,
      count: returns.filter((r) => r >= b.min && r < b.max).length,
      positive: b.min >= 0,
    })).filter((b) => b.count > 0);
  }, [companies]);

  if (data.length === 0) return null;

  const validReturns = companies.map((c) => c.weeklyReturn).filter((r) => r != null);
  const avg = validReturns.length
    ? (validReturns.reduce((a, b) => a + b, 0) / validReturns.length).toFixed(2)
    : null;

  return (
    <div className="bg-white rounded-xl shadow p-5 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-700">{title}</h2>
        {avg !== null && (
          <span className={`text-sm font-medium ${Number(avg) >= 0 ? "text-green-600" : "text-red-500"}`}>
            Avg {Number(avg) >= 0 ? "+" : ""}{avg}% &nbsp;·&nbsp; {validReturns.length} companies
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" fontSize={10} tick={{ fill: "#6b7280" }} />
          <YAxis fontSize={10} allowDecimals={false} />
          <Tooltip
            formatter={(v) => [v, "Companies"]}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.positive ? "#16a34a" : "#dc2626"}
                fillOpacity={0.75}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default WeeklyReturnHistogram;
