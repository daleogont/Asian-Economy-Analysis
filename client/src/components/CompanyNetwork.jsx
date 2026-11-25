import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { forceCenter, forceLink, forceManyBody, forceSimulation } from "d3-force";

const WIDTH = 640;
const HEIGHT = 420;
const TICKS = 300; // run the simulation to convergence synchronously, once

// Fixed palette keyed by sector name (sorted, so the same sector always
// gets the same color across countries/renders) rather than by array
// index, which would shift as different sectors appear per country.
const SECTOR_PALETTE = [
  "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5", "#0d9488",
];

function layout(nodes, edges) {
  // Deterministic starting positions (a circle by index) instead of
  // d3-force's default random jitter, so re-fetching the same data always
  // produces the same layout -- forceLink/forceManyBody/forceCenter don't
  // call Math.random() during ticking, so determinism holds from here on.
  const n = nodes.length;
  const simNodes = nodes.map((node, i) => ({
    ...node,
    x: WIDTH / 2 + 150 * Math.cos((2 * Math.PI * i) / n),
    y: HEIGHT / 2 + 150 * Math.sin((2 * Math.PI * i) / n),
  }));
  const simLinks = edges.map((e) => ({ ...e, source: e.source, target: e.target }));

  const sim = forceSimulation(simNodes)
    .force("link", forceLink(simLinks).id((d) => d.ticker).distance((d) => 40 + d.distance * 120))
    .force("charge", forceManyBody().strength(-60))
    .force("center", forceCenter(WIDTH / 2, HEIGHT / 2))
    .stop();

  for (let i = 0; i < TICKS; i++) sim.tick();

  return { nodes: simNodes, links: simLinks };
}

/**
 * Minimum-spanning-tree node-link graph over the correlation-distance
 * matrix for one country. Plain SVG, no canvas/WebGL dependency -- d3-force
 * only supplies the layout math, never touches the DOM itself.
 */
const CompanyNetwork = ({ country, period = "1y" }) => {
  const [raw, setRaw] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hovered, setHovered] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    axios
      .get(`/analytics/network?country=${country}&period=${period}`)
      .then((res) => setRaw(res.data))
      .catch(() => setError("Could not load the company network."))
      .finally(() => setLoading(false));
  }, [country, period]);

  const sectors = useMemo(
    () => Array.from(new Set((raw?.nodes ?? []).map((n) => n.sector))).sort(),
    [raw]
  );
  const sectorColor = (sector) => SECTOR_PALETTE[sectors.indexOf(sector) % SECTOR_PALETTE.length];

  const { nodes, links } = useMemo(() => {
    if (!raw?.nodes?.length) return { nodes: [], links: [] };
    return layout(raw.nodes, raw.edges ?? []);
  }, [raw]);

  if (loading) return <div className="text-gray-400 text-sm py-4">Building network…</div>;
  if (error) return <div className="text-red-400 text-sm py-4">{error}</div>;
  if (nodes.length === 0) return null;

  const maxDist = Math.max(...links.map((l) => l.distance), 1e-6);

  return (
    <div>
      <svg width={WIDTH} height={HEIGHT} className="bg-white border border-gray-100 rounded">
        {links.map((l, i) => {
          const source = typeof l.source === "object" ? l.source : nodes.find((n) => n.ticker === l.source);
          const target = typeof l.target === "object" ? l.target : nodes.find((n) => n.ticker === l.target);
          if (!source || !target) return null;
          // Thicker = closer (lower distance), matching "edge thickness ~ closeness".
          const strokeWidth = 0.5 + 2.5 * (1 - l.distance / maxDist);
          return (
            <line
              key={i}
              x1={source.x} y1={source.y} x2={target.x} y2={target.y}
              stroke="#9ca3af" strokeWidth={strokeWidth}
            />
          );
        })}
        {nodes.map((n) => (
          <g key={n.ticker} onMouseEnter={() => setHovered(n)} onMouseLeave={() => setHovered(null)}>
            <circle cx={n.x} cy={n.y} r={7} fill={sectorColor(n.sector)} stroke="#111827" strokeWidth={0.75} />
          </g>
        ))}
      </svg>

      {hovered && (
        <div className="text-xs text-gray-700 mt-1">
          <span className="font-semibold">{hovered.name}</span> ({hovered.ticker}) — {hovered.sector}
        </div>
      )}

      <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-600">
        {sectors.map((s) => (
          <span key={s} className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: sectorColor(s) }} />
            {s}
          </span>
        ))}
      </div>
    </div>
  );
};

export default CompanyNetwork;
