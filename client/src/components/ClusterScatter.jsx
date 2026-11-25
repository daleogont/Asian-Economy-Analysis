import React, { useEffect, useState } from "react";
import axios from "axios";
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

// Fixed palette, indexed by cluster_id -- stable across renders/countries,
// not derived from data (so a cluster's color doesn't shift as other
// clusters appear/disappear).
const CLUSTER_COLORS = [
  "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5",
];

const CentroidShape = (props) => {
  const { cx, cy, fill } = props;
  const r = 7;
  return (
    <path
      d={`M${cx},${cy - r} L${cx + r},${cy} L${cx},${cy + r} L${cx - r},${cy} Z`}
      fill={fill}
      stroke="#111827"
      strokeWidth={1.5}
    />
  );
};

/**
 * Scatter of this country's companies in the (volatility, mean weekly
 * return) feature space K-means already clusters on -- clustering itself
 * runs globally in /analytics/clusters, this just filters + colors the
 * companies that belong to `country`. Centroids (diamonds) use
 * cluster_summary's mean_return/mean_volatility, which already *is* the
 * centroid in this feature space.
 */
const ClusterScatter = ({ country, period = "1y" }) => {
  const [companies, setCompanies] = useState([]);
  const [clusterSummary, setClusterSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    axios
      .get(`/analytics/clusters?n_clusters=5&period=${period}`)
      .then((res) => {
        setCompanies((res.data?.companies ?? []).filter((c) => c.country === country));
        setClusterSummary(res.data?.cluster_summary ?? []);
      })
      .catch(() => setError("Could not load cluster data."))
      .finally(() => setLoading(false));
  }, [country, period]);

  if (loading) return <div className="text-gray-400 text-sm py-4">Computing clusters…</div>;
  if (error) return <div className="text-red-400 text-sm py-4">{error}</div>;
  if (companies.length === 0) return null;

  const activeClusterIds = new Set(companies.map((c) => c.cluster_id));
  const centroids = clusterSummary.filter(
    (c) => activeClusterIds.has(c.cluster_id) && c.mean_return != null
  );

  return (
    <div className="w-full h-[380px]">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="volatility"
            name="Volatility"
            label={{ value: "Weekly-return volatility", position: "insideBottom", offset: -5, fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="mean_weekly_return"
            name="Mean weekly return"
            label={{ value: "Mean weekly return", angle: -90, position: "insideLeft", fontSize: 12 }}
          />
          <ZAxis range={[60, 60]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload;
              if (p.isCentroid) {
                return (
                  <div className="bg-white border rounded shadow px-3 py-2 text-xs">
                    <div className="font-semibold">Cluster {p.cluster_id} centroid</div>
                    <div>size: {p.size}</div>
                    <div>dominant sector: {p.dominant_sector}</div>
                  </div>
                );
              }
              return (
                <div className="bg-white border rounded shadow px-3 py-2 text-xs">
                  <div className="font-semibold">{p.name} ({p.ticker})</div>
                  <div>sector: {p.sector}</div>
                  <div>cluster: {p.cluster_id}</div>
                  <div>mean weekly return: {(p.mean_weekly_return * 100).toFixed(2)}%</div>
                  <div>volatility: {(p.volatility * 100).toFixed(2)}%</div>
                </div>
              );
            }}
          />
          {Array.from(activeClusterIds).sort().map((cid) => (
            <Scatter
              key={cid}
              name={`Cluster ${cid}`}
              data={companies.filter((c) => c.cluster_id === cid)}
              fill={CLUSTER_COLORS[cid % CLUSTER_COLORS.length]}
            >
              {companies
                .filter((c) => c.cluster_id === cid)
                .map((c) => (
                  <Cell key={c.ticker} />
                ))}
            </Scatter>
          ))}
          <Scatter
            name="Centroids"
            data={centroids.map((c) => ({ ...c, isCentroid: true, mean_weekly_return: c.mean_return, volatility: c.mean_volatility }))}
            shape={CentroidShape}
          >
            {centroids.map((c) => (
              <Cell key={`centroid-${c.cluster_id}`} fill={CLUSTER_COLORS[c.cluster_id % CLUSTER_COLORS.length]} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ClusterScatter;
