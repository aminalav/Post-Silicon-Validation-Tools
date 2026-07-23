import React, { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { api } from "./api.js";

// Discrete colors for wafer-map bins.
const BIN_COLOR = { 1: "#22c55e", 2: "#ef4444", 4: "#f59e0b" };
const BIN_NAME = { 1: "Pass", 2: "Functional fail", 4: "Edge/parametric" };

export default function App() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);
  const [pareto, setPareto] = useState([]);
  const [wafers, setWafers] = useState([]);
  const [wafer, setWafer] = useState(null);
  const [wmap, setWmap] = useState(null);
  const [dies, setDies] = useState([]);
  const [die, setDie] = useState(null);
  const [schmoo, setSchmoo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.health(), api.yieldSummary(), api.pareto(), api.wafers()])
      .then(([h, s, p, w]) => {
        setHealth(h);
        setSummary(s);
        setPareto(p);
        setWafers(w);
        if (w.length) setWafer(w[0].wafer_number);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (wafer == null) return;
    api.wafermap(wafer).then(setWmap).catch((e) => setError(String(e)));
    api.dies(wafer).then((d) => {
      setDies(d);
      if (d.length) setDie(d[0].die_id);
    });
  }, [wafer]);

  useEffect(() => {
    if (!die) return;
    api.schmoo(die).then(setSchmoo).catch(() => setSchmoo(null));
  }, [die]);

  return (
    <>
      <header>
        <h1>Silicon Engineering Platform</h1>
        {health && <span className="badge">core: {health.core_backend}</span>}
        <span className="badge">post-silicon validation analytics</span>
      </header>

      {error && <p className="error" style={{ padding: "0 32px" }}>API error: {error} — is the backend running on :8000?</p>}

      <main>
        <section className="panel">
          <h2>Yield summary</h2>
          {summary && (
            <>
              <div className="kpis">
                <div className="kpi"><div className="num">{summary.total_dies}</div><div className="label">Total dies</div></div>
                <div className="kpi"><div className="num">{summary.overall_yield_pct}%</div><div className="label">Overall yield</div></div>
                <div className="kpi"><div className="num">{summary.passed}</div><div className="label">Passing</div></div>
              </div>
              <table style={{ marginTop: 16 }}>
                <thead><tr><th>Wafer</th><th>Total</th><th>Passed</th><th>Yield %</th></tr></thead>
                <tbody>
                  {summary.per_wafer.map((w) => (
                    <tr key={w.wafer_number}><td>{w.wafer_number}</td><td>{w.total}</td><td>{w.passed}</td><td>{w.yield_pct}</td></tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>

        <section className="panel">
          <h2>Failure Pareto</h2>
          {pareto.length > 0 && (
            <Plot
              data={[
                { type: "bar", x: pareto.map((p) => p.test_name), y: pareto.map((p) => p.fail_count), marker: { color: "#38bdf8" }, name: "Fails" },
                { type: "scatter", x: pareto.map((p) => p.test_name), y: pareto.map((p) => p.cum_pct), yaxis: "y2", line: { color: "#f59e0b" }, name: "Cum %" },
              ]}
              layout={plotLayout({ height: 300, yaxis2: { overlaying: "y", side: "right", range: [0, 100] } })}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </section>

        <section className="panel">
          <h2>Wafer map</h2>
          <select value={wafer ?? ""} onChange={(e) => setWafer(Number(e.target.value))}>
            {wafers.map((w) => <option key={w.wafer_number} value={w.wafer_number}>Wafer {w.wafer_number}</option>)}
          </select>
          {wmap && (
            <Plot
              data={[{
                type: "scatter", mode: "markers",
                x: wmap.dies.map((d) => d.x), y: wmap.dies.map((d) => d.y),
                marker: {
                  size: 16, symbol: "square",
                  color: wmap.dies.map((d) => BIN_COLOR[d.final_bin] || "#64748b"),
                },
                text: wmap.dies.map((d) => `(${d.x},${d.y}) ${BIN_NAME[d.final_bin] || "bin " + d.final_bin}`),
                hoverinfo: "text",
              }]}
              layout={plotLayout({ height: 320, yaxis: { scaleanchor: "x" } })}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </section>

        <section className="panel">
          <h2>Schmoo plot (voltage × frequency)</h2>
          <select value={die ?? ""} onChange={(e) => setDie(e.target.value)}>
            {dies.map((d) => <option key={d.die_id} value={d.die_id}>{d.die_id}</option>)}
          </select>
          {schmoo && schmoo.x_vals.length > 0 && (
            <Plot
              data={[{
                type: "heatmap", z: schmoo.z, x: schmoo.x_vals, y: schmoo.y_vals,
                colorscale: [[0, "#ef4444"], [1, "#22c55e"]], showscale: false,
              }]}
              layout={plotLayout({ height: 320, xaxis: { title: "voltage (V)" }, yaxis: { title: "frequency (GHz)" } })}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </section>
      </main>
    </>
  );
}

function plotLayout(extra) {
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#e2e8f0", size: 11 },
    margin: { t: 10, r: 40, b: 60, l: 50 },
    showlegend: false,
    ...extra,
  };
}
