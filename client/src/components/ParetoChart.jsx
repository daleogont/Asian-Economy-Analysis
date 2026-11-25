import React from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { paretoFront } from "../utils/pareto";

/**
 * Accuracy-vs-cost tradeoff: x = train time (log), y = RMSE (log), point
 * size = memory. The Pareto front (no other model beats a point on both
 * axes) is highlighted -- everything else is a model some other model
 * strictly dominates.
 *
 * `points`: [{ model, label, train_time_s, rmse, memory_mb }]
 */
const ParetoChart = ({ points, title = "Accuracy vs. Cost (Pareto front)" }) => {
  const safePoints = points.map((p) => ({
    ...p,
    train_time_s: Math.max(p.train_time_s, 0.001), // floor for log scale
    memory_mb: Math.max(p.memory_mb, 0.01),
  }));
  const front = new Set(paretoFront(safePoints, "train_time_s", "rmse").map((p) => p.model));

  return (
    <div>
      <h2 className="text-lg font-semibold mb-2 text-gray-700">{title}</h2>
      <p className="text-xs text-gray-500 mb-2">
        Highlighted points: no other model here is both faster to train and more accurate. Point size ~ memory.
      </p>
      <div className="w-full h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="train_time_s"
              scale="log"
              domain={["auto", "auto"]}
              name="Train time (s)"
              label={{ value: "Train time (s, log)", position: "insideBottom", offset: -8, fontSize: 12 }}
            />
            <YAxis
              type="number"
              dataKey="rmse"
              scale="log"
              domain={["auto", "auto"]}
              name="RMSE"
              label={{ value: "RMSE (log)", angle: -90, position: "insideLeft", fontSize: 12 }}
            />
            <ZAxis dataKey="memory_mb" range={[60, 400]} name="Memory (MB)" />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload;
                return (
                  <div className="bg-white border rounded shadow px-3 py-2 text-xs">
                    <div className="font-semibold">
                      {p.label} {front.has(p.model) && <span className="text-green-600">(Pareto front)</span>}
                    </div>
                    <div>train time: {p.train_time_s.toFixed(3)}s</div>
                    <div>RMSE: {p.rmse.toFixed(4)}</div>
                    <div>memory: {p.memory_mb.toFixed(2)}MB</div>
                  </div>
                );
              }}
            />
            <Scatter data={safePoints} fill="#9ca3af">
              {safePoints.map((p) => (
                <Cell key={p.model} fill={front.has(p.model) ? "#16a34a" : "#9ca3af"} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ParetoChart;
