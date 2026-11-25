import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import ParetoChart from "../components/ParetoChart";

const MODEL_OPTIONS = [
  { key: "arima",         label: "ARIMA",         defaultOn: true },
  { key: "ets",           label: "ETS",           defaultOn: true },
  { key: "sarima",        label: "SARIMA",        defaultOn: true },
  { key: "prophet",       label: "Prophet",       defaultOn: true },
  { key: "ridge",         label: "Ridge",         defaultOn: true },
  { key: "random_forest", label: "Random Forest", defaultOn: true },
  { key: "xgboost",       label: "XGBoost",       defaultOn: true },
  { key: "naive",         label: "Naive (random walk)", defaultOn: true },
  { key: "lstm",          label: "LSTM",          defaultOn: false }, // off by default: slow
];

const PERIODS = ["1y", "2y", "5y"];

const fmt = (v, digits = 4) => (v == null ? "—" : Number(v).toFixed(digits));

// Rank 1 (best) -> green, higher rank -> red. Domain depends on how many
// models were actually run, so it's computed per-render, not fixed.
const rankColor = (rank, maxRank) => {
  if (rank == null || maxRank <= 1) return "#f3f4f6";
  const t = (rank - 1) / (maxRank - 1); // 0 = best, 1 = worst
  const r = Math.round(220 - t * 60 + t * 95);
  const g = Math.round(220 - t * 120);
  const b = Math.round(220 - t * 120);
  return `rgb(${Math.min(255, r)}, ${Math.max(0, g)}, ${Math.max(0, b)})`;
};

function boxStats(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const q = (p) => {
    const idx = (sorted.length - 1) * p;
    const lo = Math.floor(idx), hi = Math.ceil(idx);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  };
  return { min: sorted[0], q1: q(0.25), median: q(0.5), q3: q(0.75), max: sorted[sorted.length - 1] };
}

const Boxplot = ({ data }) => {
  // data: [{ label, stats: {min,q1,median,q3,max} | null }]
  const allVals = data.flatMap((d) => (d.stats ? [d.stats.min, d.stats.max] : []));
  if (allVals.length === 0) return <div className="text-gray-400 text-sm">No data to plot.</div>;
  const lo = Math.min(...allVals), hi = Math.max(...allVals);
  const span = hi - lo || 1;
  const toX = (v) => 8 + ((v - lo) / span) * 584;
  const rowH = 34;

  return (
    <svg width={640} height={data.length * rowH + 20}>
      {data.map((d, i) => {
        const y = i * rowH + 18;
        if (!d.stats) {
          return (
            <text key={d.label} x={8} y={y + 4} fontSize={11} fill="#9ca3af">
              {d.label}: no data
            </text>
          );
        }
        const { min, q1, median, q3, max } = d.stats;
        return (
          <g key={d.label}>
            <text x={8} y={y - 10} fontSize={11} fill="#374151">{d.label}</text>
            <line x1={toX(min)} y1={y} x2={toX(q1)} y2={y} stroke="#6b7280" />
            <line x1={toX(q3)} y1={y} x2={toX(max)} y2={y} stroke="#6b7280" />
            <rect x={toX(q1)} y={y - 7} width={Math.max(toX(q3) - toX(q1), 1)} height={14} fill="#bfdbfe" stroke="#2563eb" />
            <line x1={toX(median)} y1={y - 7} x2={toX(median)} y2={y + 7} stroke="#1d4ed8" strokeWidth={2} />
          </g>
        );
      })}
    </svg>
  );
};

const BatchBenchmark = () => {
  const [companies, setCompanies] = useState([]);
  const [mode, setMode] = useState("country");
  const [country, setCountry] = useState("");
  const [sector, setSector] = useState("");
  const [selectedModels, setSelectedModels] = useState(
    new Set(MODEL_OPTIONS.filter((m) => m.defaultOn).map((m) => m.key))
  );
  const [horizon, setHorizon] = useState(30);
  const [period, setPeriod] = useState("1y");
  const [stats, setStats] = useState(false);

  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    axios.get("/api/companies").then((res) => setCompanies(res.data ?? [])).catch(() => {});
  }, []);

  const countries = useMemo(
    () => Array.from(new Set(companies.map((c) => c.country))).sort(),
    [companies]
  );
  const sectors = useMemo(
    () => Array.from(new Set(companies.map((c) => c.sector))).sort(),
    [companies]
  );

  useEffect(() => {
    if (countries.length && !country) setCountry(countries[0]);
    if (sectors.length && !sector) setSector(sectors[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countries, sectors]);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const toggleModel = (key) => {
    setSelectedModels((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const pollStatus = (id) => {
    pollRef.current = setInterval(() => {
      axios.get(`/analytics/batch-benchmark/${id}/status`).then((res) => {
        setStatus(res.data.status);
        setProgress(res.data.progress);
        if (res.data.status === "SUCCESS" || res.data.status === "FAILURE") {
          clearInterval(pollRef.current);
          if (res.data.status === "SUCCESS") {
            axios.get(`/analytics/batch-benchmark/${id}/results`).then((r) => setResult(r.data.result));
          } else {
            setError("Batch benchmark failed.");
          }
        }
      }).catch(() => {});
    }, 2000);
  };

  const run = () => {
    setError(null);
    setResult(null);
    setProgress(null);
    setStatus("queued");

    const body = {
      models: Array.from(selectedModels),
      horizon: Number(horizon),
      period,
      stats,
      ...(mode === "country" ? { country } : { sector }),
    };

    axios.post("/analytics/batch-benchmark", body)
      .then((res) => {
        setTaskId(res.data.task_id);
        pollStatus(res.data.task_id);
      })
      .catch((err) => setError(err.response?.data?.detail ?? "Failed to start benchmark."));
  };

  const running = status && status !== "SUCCESS" && status !== "FAILURE";

  const modelRows = result
    ? Object.entries(result.model_summary)
        .map(([model, s]) => ({ model, label: MODEL_OPTIONS.find((m) => m.key === model)?.label ?? model, ...s }))
        .sort((a, b) => (a.mean_rmse_pct ?? Infinity) - (b.mean_rmse_pct ?? Infinity))
    : [];

  const nonZeroErrorRows = result
    ? result.rows.filter((r) => !result.zero_error_tickers.includes(r.ticker))
    : [];

  const boxplotData = result
    ? result.models.map((m) => ({
        label: MODEL_OPTIONS.find((o) => o.key === m)?.label ?? m,
        stats: boxStats(nonZeroErrorRows.filter((r) => r.model === m && r.rmse_pct != null).map((r) => r.rmse_pct)),
      }))
    : [];

  const paretoPoints = result
    ? result.models.map((m) => {
        const modelRows2 = nonZeroErrorRows.filter((r) => r.model === m && r.rmse != null);
        const mean = (key) => modelRows2.reduce((s, r) => s + r[key], 0) / (modelRows2.length || 1);
        return {
          model: m,
          label: MODEL_OPTIONS.find((o) => o.key === m)?.label ?? m,
          train_time_s: mean("train_time_s"),
          rmse: mean("rmse"),
          memory_mb: mean("memory_mb"),
        };
      }).filter((p) => !Number.isNaN(p.rmse) && p.rmse > 0)
    : [];

  return (
    <div className="px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">Batch Benchmark</h1>
      <p className="text-gray-500 mb-6">
        Run many tickers x many models through the same single-holdout benchmark, in the background.
      </p>

      <div className="bg-white rounded-xl shadow p-5 mb-8 space-y-4">
        <div className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Select by</label>
            <div className="flex gap-1">
              {["country", "sector"].map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`px-3 py-1.5 text-sm rounded capitalize transition ${
                    mode === m ? "bg-purple-600 text-white" : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
          {mode === "country" ? (
            <div>
              <label className="block text-xs text-gray-500 mb-1">Country</label>
              <select value={country} onChange={(e) => setCountry(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
                {countries.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-xs text-gray-500 mb-1">Sector</label>
              <select value={sector} onChange={(e) => setSector(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
                {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Horizon (days)</label>
            <input
              type="number" min={7} max={90} value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm w-24"
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
                    period === p ? "bg-purple-600 text-white" : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-1.5 text-sm text-gray-600 pb-1.5">
            <input type="checkbox" checked={stats} onChange={(e) => setStats(e.target.checked)} />
            Friedman + Wilcoxon-Holm
          </label>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">Models</label>
          <div className="flex gap-3 flex-wrap text-sm">
            {MODEL_OPTIONS.map((m) => (
              <label key={m.key} className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={selectedModels.has(m.key)}
                  onChange={() => toggleModel(m.key)}
                />
                {m.label}
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={run}
          disabled={running || selectedModels.size === 0}
          className="px-5 py-1.5 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {running ? "Running…" : "Run Batch Benchmark"}
        </button>

        {error && <div className="text-sm text-red-500">{error}</div>}

        {running && (
          <div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all"
                style={{ width: progress ? `${(100 * progress.done) / progress.total}%` : "5%" }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {progress ? `${progress.done} / ${progress.total} pairs done` : `status: ${status}`}
              {taskId && <span className="ml-2 text-gray-400">task: {taskId}</span>}
            </div>
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-10">
          {result.zero_error_tickers.length > 0 && (
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-3">
              Excluded from the charts below (every model scored ~0 RMSE — likely flat/degenerate price
              data, not a genuinely easy forecast): {result.zero_error_tickers.join(", ")}
            </div>
          )}

          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-700">Summary</h2>
            <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-sm text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Model</th>
                  <th className="px-4 py-2 text-right">Mean RMSE%</th>
                  <th className="px-4 py-2 text-right">Std RMSE%</th>
                  <th className="px-4 py-2 text-right">Best-model count</th>
                </tr>
              </thead>
              <tbody>
                {modelRows.map((r, i) => (
                  <tr key={r.model} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="px-4 py-2 font-medium">{r.label}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.mean_rmse_pct, 2)}%</td>
                    <td className="px-4 py-2 text-right">{fmt(r.std_rmse_pct, 2)}%</td>
                    <td className="px-4 py-2 text-right">{r.best_model_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-700">Rank Heatmap (model x ticker)</h2>
            <div className="overflow-x-auto">
              <table className="border-collapse text-xs">
                <thead>
                  <tr>
                    <th className="p-1"></th>
                    {result.tickers.map((t) => (
                      <th key={t} className="p-1 font-normal text-gray-500 whitespace-nowrap" style={{ writingMode: "vertical-rl" }}>
                        {t}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.models.map((m) => (
                    <tr key={m}>
                      <th className="p-1 text-right font-normal text-gray-500 whitespace-nowrap">
                        {MODEL_OPTIONS.find((o) => o.key === m)?.label ?? m}
                      </th>
                      {result.tickers.map((t) => {
                        const rank = result.rank_table[t]?.[m];
                        return (
                          <td
                            key={t}
                            title={rank != null ? `rank ${rank}/${result.models.length}` : "no result"}
                            className="w-6 h-6 text-center border border-gray-100"
                            style={{ backgroundColor: rankColor(rank, result.models.length) }}
                          />
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-2 text-gray-700">RMSE% distribution per model</h2>
            <Boxplot data={boxplotData} />
          </div>

          {paretoPoints.length >= 2 && <ParetoChart points={paretoPoints} title="Accuracy vs. Cost (aggregated, Pareto front)" />}

          {result.stats && (
            <div>
              <h2 className="text-lg font-semibold mb-2 text-gray-700">Friedman + Wilcoxon-Holm</h2>
              {result.stats.note ? (
                <div className="text-sm text-gray-500">{result.stats.note}</div>
              ) : (
                <>
                  <div className="text-sm text-gray-700 mb-2">
                    Friedman: statistic={fmt(result.stats.friedman.statistic, 3)}, p={fmt(result.stats.friedman.p_value, 4)}
                    {" "}(n={result.stats.complete_tickers.length} tickers with every model scored)
                  </div>
                  <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-sm text-sm">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-4 py-2 text-left">Model A</th>
                        <th className="px-4 py-2 text-left">Model B</th>
                        <th className="px-4 py-2 text-right">p-value</th>
                        <th className="px-4 py-2 text-right">p-value (Holm)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.stats.pairwise_wilcoxon_holm.map((p, i) => (
                        <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                          <td className="px-4 py-2">{p.model_a}</td>
                          <td className="px-4 py-2">{p.model_b}</td>
                          <td className="px-4 py-2 text-right">{fmt(p.p_value, 4)}</td>
                          <td className="px-4 py-2 text-right font-medium">{fmt(p.p_value_holm, 4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BatchBenchmark;
