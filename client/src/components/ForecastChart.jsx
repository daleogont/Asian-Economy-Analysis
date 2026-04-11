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
  ReferenceLine,
} from "recharts";

const DAYS_OPTIONS = [7, 14, 30, 60];

const ForecastChart = ({ ticker }) => {
  const [days, setDays] = useState(30);
  const [data, setData] = useState([]);
  const [splitDate, setSplitDate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    axios
      .get(`/analytics/forecast/${ticker}?days=${days}&period=1y`)
      .then((res) => {
        const hist = res.data.history.map((h) => ({
          date: h.date,
          actual: h.actual,
          predicted: null,
          upper: null,
          lower: null,
        }));
        const fcast = res.data.forecast.map((f) => ({
          date: f.date,
          actual: null,
          predicted: f.predicted,
          upper: f.upper,
          lower: f.lower,
        }));
        setData([...hist, ...fcast]);
        setSplitDate(res.data.forecast[0]?.date ?? null);
      })
      .catch((err) => {
        setError(err.response?.data?.detail ?? "Forecast unavailable");
        setData([]);
      })
      .finally(() => setLoading(false));
  }, [ticker, days]);

  if (!ticker) return null;

  const xInterval = data.length > 0 ? Math.floor(data.length / 6) : 1;

  return (
    <div className="mt-4 bg-gray-50 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between mb-2 gap-2">
        <h3 className="font-semibold text-gray-700">
          ARIMA(1,1,1) Forecast — {ticker}
        </h3>
        <div className="flex gap-1">
          {DAYS_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-2 py-1 text-xs rounded transition ${
                days === d
                  ? "bg-purple-600 text-white"
                  : "bg-gray-200 text-gray-600 hover:bg-gray-300"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-10 text-gray-400 text-sm">
          Running ARIMA model…
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center py-6 text-red-400 text-sm">
          {error}
        </div>
      )}
      {!loading && !error && (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" fontSize={10} interval={xInterval} />
            <YAxis fontSize={10} />
            <Tooltip
              formatter={(v, name) =>
                v != null ? [Number(v).toFixed(4), name] : [null, name]
              }
            />
            <Legend />
            {splitDate && (
              <ReferenceLine
                x={splitDate}
                stroke="#9333ea"
                strokeDasharray="4 2"
                label={{ value: "Forecast start", position: "insideTopRight", fontSize: 10, fill: "#9333ea" }}
              />
            )}
            <Line
              type="monotone"
              dataKey="actual"
              dot={false}
              stroke="#2563eb"
              strokeWidth={1.5}
              name="Actual"
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="predicted"
              dot={false}
              stroke="#9333ea"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              name="Forecast"
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="upper"
              dot={false}
              stroke="#c084fc"
              strokeWidth={1}
              strokeDasharray="3 2"
              name="Upper 95% CI"
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="lower"
              dot={false}
              stroke="#c084fc"
              strokeWidth={1}
              strokeDasharray="3 2"
              name="Lower 95% CI"
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default ForecastChart;
