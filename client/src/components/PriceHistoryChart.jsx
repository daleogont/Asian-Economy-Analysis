import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const PERIODS = ["3m", "6m", "1y", "2y"];

const PriceHistoryChart = ({ ticker }) => {
  const [period, setPeriod] = useState("1y");
  const [maWindow, setMaWindow] = useState(null);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    const w = maWindow ?? 30;
    axios
      .get(`/analytics/rolling/${ticker}?period=${period}&window=${w}`)
      .then((res) => setData(res.data.data))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [ticker, period, maWindow]);

  if (!ticker) return null;

  const maKey = `ma${maWindow ?? 30}`;
  const xInterval = data.length > 0 ? Math.floor(data.length / 6) : 1;

  return (
    <div className="mt-4 bg-gray-50 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between mb-2 gap-2">
        <h3 className="font-semibold text-gray-700">
          Price History — {ticker}
        </h3>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2 py-1 text-xs rounded transition ${
                period === p
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-600 hover:bg-gray-300"
              }`}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-gray-500">Rolling avg:</span>
        {[null, 7, 30].map((w) => (
          <button
            key={w ?? "off"}
            onClick={() => setMaWindow(w)}
            className={`px-2 py-1 text-xs rounded transition ${
              maWindow === w
                ? "bg-indigo-600 text-white"
                : "bg-gray-200 text-gray-600 hover:bg-gray-300"
            }`}
          >
            {w ? `${w}d` : "Off"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-10 text-gray-400 text-sm">
          Loading…
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" fontSize={10} interval={xInterval} />
            <YAxis fontSize={10} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="close"
              dot={false}
              stroke="#2563eb"
              strokeWidth={1.5}
              name="Close"
            />
            {maWindow && (
              <Line
                type="monotone"
                dataKey={maKey}
                dot={false}
                stroke="#f59e42"
                strokeWidth={1.5}
                name={`MA${maWindow}`}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default PriceHistoryChart;
