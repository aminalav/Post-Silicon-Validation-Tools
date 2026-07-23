const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  health: () => get("/api/health"),
  wafers: () => get("/api/wafers"),
  yieldSummary: () => get("/api/yield"),
  pareto: () => get("/api/pareto"),
  wafermap: (w) => get(`/api/wafermap/${w}`),
  schmoo: (dieId) => get(`/api/schmoo/${dieId}`),
  dies: (w) => get(`/api/dies?wafer_number=${w}`),
  registers: (dieId) => get(`/api/registers/${dieId}`),
};
