import React, { useMemo, useState } from "react";
import ParetoChart from "../components/ParetoChart";

const MODELS = [
  { key: "arima",         label: "ARIMA" },
  { key: "ets",           label: "ETS" },
  { key: "sarima",        label: "SARIMA" },
  { key: "prophet",       label: "Prophet" },
  { key: "ridge",         label: "Ridge" },
  { key: "random_forest", label: "Random Forest" },
  { key: "xgboost",       label: "XGBoost" },
  { key: "lstm",          label: "LSTM" },
];

const PERIODS = ["1y", "2y", "5y"];

const COLUMNS = [
  { key: "model",                 label: "Model" },
  { key: "rmse",                  label: "RMSE" },
  { key: "mae",                   label: "MAE" },
  { key: "inference_latency_ms",  label: "Latency (ms)" },
  { key: "train_time_s",          label: "Train Time (s)" },
  {
    key: "memory_mb",
    label: "Python peak memory (tracemalloc)",
    tooltip: "Peak Python-level allocation during fit+predict, via tracemalloc. Does not count native "
      + "C/C++ allocations (PyTorch, XGBoost, scikit-learn internals) -- see Process RSS for those.",
  },
  {
    key: "rss_mb",
    label: "Process RSS (MB)",
    tooltip: "Whole-process memory delta during fit+predict (includes native allocations tracemalloc can't see). Coarser, but complete.",
  },
  { key: "cache",                 label: "Cache" },
];

const fmt = (v, digits = 4) => (v == null ? "—" : Number(v).toFixed(digits));

const ModelComparison = () => {
  const [ticker, setTicker] = useState("9988.HK");
  const [period, setPeriod] = useState("1y");
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(false);
  const [sortBy, setSortBy] = useState("rmse");
  const [sortDir, setSortDir] = useState("asc");

  const runBenchmark = () => {
    if (!ticker || running) return;

    setRunning(true);
    const initial = {};
    MODELS.forEach((m) => {
      initial[m.key] = { status: "loading" };
    });
    setResults(initial);

    const requests = MODELS.map(({ key: model }) =>
      fetch(`/analytics/models/forecast/${ticker}?model=${model}&days=30&period=${period}`)
        .then(async (res) => {
          const cache = res.headers.get("x-cache");
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            setResults((prev) => ({
              ...prev,
              [model]: { status: "error", error: data.detail ?? "Request failed" },
            }));
            return;
          }
          setResults((prev) => ({
            ...prev,
            [model]: { status: "done", metrics: data.metrics ?? {}, cache },
          }));
        })
        .catch((err) => {
          setResults((prev) => ({
            ...prev,
            [model]: { status: "error", error: err.message ?? "Network error" },
          }));
        })
    );

    Promise.all(requests).then(() => setRunning(false));
  };

  const rows = useMemo(
    () =>
      MODELS.map(({ key, label }) => ({
        model: key,
        label,
        ...(results[key] ?? { status: "idle" }),
      })),
    [results]
  );

  const readyRows = rows.filter((r) => r.status === "done" && r.metrics?.rmse != null);
  const notReadyRows = rows.filter((r) => !(r.status === "done" && r.metrics?.rmse != null));

  const rmseRanked = [...readyRows].sort((a, b) => a.metrics.rmse - b.metrics.rmse);
  const showRanking = rmseRanked.length >= 5;
  const topModels = showRanking ? new Set(rmseRanked.slice(0, 3).map((r) => r.model)) : new Set();
  const bottomModels = showRanking ? new Set(rmseRanked.slice(-2).map((r) => r.model)) : new Set();

  const handleSort = (key) => {
    if (key === sortBy) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("asc");
    }
  };

  const sortedReadyRows = useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1;
    return [...readyRows].sort((a, b) => {
      if (sortBy === "model") return dir * a.label.localeCompare(b.label);
      if (sortBy === "cache") return dir * String(a.cache ?? "").localeCompare(String(b.cache ?? ""));
      return dir * ((a.metrics[sortBy] ?? 0) - (b.metrics[sortBy] ?? 0));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyRows, sortBy, sortDir]);

  const displayRows = [...sortedReadyRows, ...notReadyRows];

  const summary = readyRows.length
    ? {
        bestAccuracy: readyRows.reduce((a, b) => (b.metrics.rmse < a.metrics.rmse ? b : a)),
        fastest: readyRows.reduce((a, b) =>
          b.metrics.inference_latency_ms < a.metrics.inference_latency_ms ? b : a
        ),
        lowestMemory: readyRows.reduce((a, b) => (b.metrics.memory_mb < a.metrics.memory_mb ? b : a)),
      }
    : null;

  const lstmLoading = results.lstm?.status === "loading";

  return (
    <div className="px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">Model Comparison</h1>
      <p className="text-gray-500 mb-6">
        Benchmark all 8 forecasting models side-by-side on accuracy, latency, and memory.
      </p>

      <div className="bg-white rounded-xl shadow p-5 mb-8 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ticker</label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="9988.HK"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-40 focus:outline-none focus:ring-1 focus:ring-purple-400"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Period</label>
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-sm rounded transition ${
                  period === p
                    ? "bg-purple-600 text-white"
                    : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={runBenchmark}
          disabled={running || !ticker}
          className="px-5 py-1.5 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {running ? "Running…" : "Run Benchmark"}
        </button>
        {lstmLoading && (
          <span className="text-xs text-gray-400">
            LSTM is training (~45s on first run) — other rows will finish first.
          </span>
        )}
      </div>

      {Object.keys(results).length > 0 && (
        <div className="overflow-x-auto mb-6">
          <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-md text-sm">
            <thead className="bg-gray-100">
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    title={col.tooltip}
                    className="px-4 py-2 text-left cursor-pointer select-none hover:bg-gray-200 transition whitespace-nowrap"
                  >
                    {col.label}
                    {sortBy === col.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, idx) => {
                const borderClass = topModels.has(row.model)
                  ? "border-l-4 border-l-green-400"
                  : bottomModels.has(row.model)
                  ? "border-l-4 border-l-red-400"
                  : "border-l-4 border-l-transparent";
                return (
                  <tr
                    key={row.model}
                    className={`${idx % 2 === 0 ? "bg-white" : "bg-gray-50"} ${borderClass}`}
                  >
                    <td className="px-4 py-2 font-medium">{row.label}</td>
                    {row.status === "loading" && (
                      <td colSpan={6} className="px-4 py-2 text-gray-400 text-xs">
                        Running…
                      </td>
                    )}
                    {row.status === "error" && (
                      <td colSpan={6} className="px-4 py-2 text-red-500 text-xs">
                        {row.error}
                      </td>
                    )}
                    {row.status === "idle" && (
                      <td colSpan={6} className="px-4 py-2 text-gray-300 text-xs">
                        —
                      </td>
                    )}
                    {row.status === "done" && (
                      <>
                        <td className="px-4 py-2">{fmt(row.metrics.rmse)}</td>
                        <td className="px-4 py-2">{fmt(row.metrics.mae)}</td>
                        <td className="px-4 py-2">{fmt(row.metrics.inference_latency_ms, 1)}</td>
                        <td className="px-4 py-2">{fmt(row.metrics.train_time_s)}</td>
                        <td className="px-4 py-2">{fmt(row.metrics.memory_mb, 2)}</td>
                        <td className="px-4 py-2">{fmt(row.metrics.rss_mb, 2)}</td>
                      </>
                    )}
                    {row.status === "done" && (
                      <td className="px-4 py-2">
                        {row.cache ? (
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${
                              row.cache === "HIT"
                                ? "bg-green-100 text-green-700"
                                : "bg-gray-200 text-gray-600"
                            }`}
                          >
                            {row.cache}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-300">—</span>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {summary && (
        <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 space-y-1">
          <div>
            Best accuracy: <strong>{summary.bestAccuracy.label}</strong> (RMSE{" "}
            {fmt(summary.bestAccuracy.metrics.rmse)})
          </div>
          <div>
            Fastest inference: <strong>{summary.fastest.label}</strong> (
            {fmt(summary.fastest.metrics.inference_latency_ms, 1)}ms)
          </div>
          <div>
            Lowest memory: <strong>{summary.lowestMemory.label}</strong> (
            {fmt(summary.lowestMemory.metrics.memory_mb, 2)}MB)
          </div>
        </div>
      )}

      {readyRows.length >= 2 && (
        <div className="mt-8">
          <ParetoChart
            points={readyRows.map((r) => ({
              model: r.model,
              label: r.label,
              train_time_s: r.metrics.train_time_s,
              rmse: r.metrics.rmse,
              memory_mb: r.metrics.memory_mb,
            }))}
          />
        </div>
      )}
    </div>
  );
};

export default ModelComparison;
