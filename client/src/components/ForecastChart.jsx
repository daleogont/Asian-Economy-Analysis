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

const MODEL_OPTIONS = [
  { key: "arima",         label: "ARIMA" },
  { key: "ets",           label: "ETS" },
  { key: "sarima",        label: "SARIMA" },
  { key: "prophet",       label: "Prophet" },
  { key: "ridge",         label: "Ridge" },
  { key: "random_forest", label: "Random Forest" },
  { key: "lstm",          label: "LSTM" },
  { key: "xgboost",       label: "XGBoost" },
];

const MetricTag = ({ label, value }) => (
  <span className="px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">
    {label}: {value ?? "—"}
  </span>
);

const ForecastChart = ({ ticker }) => {
  const [days, setDays] = useState(30);
  const [model, setModel] = useState("arima");
  const [data, setData] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [splitDate, setSplitDate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    axios
      .get(`/analytics/models/forecast/${ticker}?model=${model}&days=${days}&period=1y`)
      .then((res) => {
        const history  = res.data?.history ?? [];
        const forecast = res.data?.forecast ?? [];
        const hist = history.map((h) => ({
          date: h.date,
          actual: h.actual,
          predicted: null,
          upper: null,
          lower: null,
        }));
        const fcast = forecast.map((f) => ({
          date: f.date,
          actual: null,
          predicted: f.predicted,
          upper: f.upper,
          lower: f.lower,
        }));
        setData([...hist, ...fcast]);
        setSplitDate(forecast[0]?.date ?? null);
        setMetrics(res.data?.metrics ?? null);
      })
      .catch((err) => {
        setError(err.response?.data?.detail ?? "Forecast unavailable");
        setData([]);
        setMetrics(null);
      })
      .finally(() => setLoading(false));
  }, [ticker, days, model]);

  if (!ticker) return null;

  const xInterval = data.length > 0 ? Math.floor(data.length / 6) : 1;
  const modelLabel = MODEL_OPTIONS.find((m) => m.key === model)?.label ?? model;

  return (
    <div className="mt-4 bg-gray-50 rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between mb-2 gap-2">
        <h3 className="font-semibold text-gray-700">
          Forecast — {ticker}
        </h3>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700 border-none focus:outline-none focus:ring-1 focus:ring-purple-400"
          >
            {MODEL_OPTIONS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
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
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-10 text-gray-400 text-sm text-center">
          <span>Running {modelLabel} model…</span>
          {model === "lstm" && (
            <span className="mt-1 text-xs text-gray-400">
              First run may take ~45s (training); subsequent requests load instantly from cache.
            </span>
          )}
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center py-6 text-red-400 text-sm">
          {error}
        </div>
      )}
      {!loading && !error && data.length === 0 && (
        <div className="flex items-center justify-center py-10 text-gray-400 text-sm">
          No data available for {ticker}.
        </div>
      )}
      {!loading && !error && data.length > 0 && (
        <>
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

          {metrics && (
            <div className="flex flex-wrap gap-2 mt-3">
              <MetricTag label="RMSE" value={metrics.rmse} />
              <MetricTag label="MAE" value={metrics.mae} />
              <MetricTag label="Latency" value={metrics.inference_latency_ms != null ? `${metrics.inference_latency_ms}ms` : null} />
              <MetricTag label="Train time" value={metrics.train_time_s != null ? `${metrics.train_time_s}s` : null} />
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ForecastChart;
