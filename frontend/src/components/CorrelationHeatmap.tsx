import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { fetchCorrelation } from "../api/client";

function heatColor(v: number): string {
  // -1 → blue, 0 → white/neutral, 1 → red
  const r = v > 0 ? Math.round(255 * v) : 0;
  const b = v < 0 ? Math.round(255 * -v) : 0;
  const g = Math.round(255 * (1 - Math.abs(v)) * 0.4);
  return `rgb(${r},${g},${b})`;
}

function textColor(v: number): string {
  return Math.abs(v) > 0.5 ? "#fff" : "#111";
}

export default function CorrelationHeatmap() {
  const { assets, lookbackYears, correlationResult, setCorrelationResult } = usePortfolioStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (assets.length < 2) { setError("Add at least 2 assets."); return; }
    setLoading(true); setError(null);
    try {
      const result = await fetchCorrelation(assets.map((a) => a.ticker), lookbackYears);
      setCorrelationResult(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to load correlation.");
    } finally {
      setLoading(false);
    }
  }

  const cr = correlationResult;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Correlation Heatmap</h2>
        <button className="btn-secondary" onClick={load} disabled={loading || assets.length < 2}>
          {loading ? "Loading…" : "Load"}
        </button>
      </div>
      <p className="constraint-hint">Pearson correlation from historical daily returns. Read-only.</p>

      {error && <div className="error-msg">{error}</div>}

      {cr && (
        <div className="heatmap-wrapper">
          <table className="heatmap-table">
            <thead>
              <tr>
                <th />
                {cr.tickers.map((t) => <th key={t} className="heatmap-header">{t}</th>)}
              </tr>
            </thead>
            <tbody>
              {cr.tickers.map((rowT, i) => (
                <tr key={rowT}>
                  <td className="heatmap-row-label">{rowT}</td>
                  {cr.matrix[i].map((v, j) => (
                    <td
                      key={j}
                      className="heatmap-cell"
                      style={{ background: heatColor(v), color: textColor(v) }}
                      title={`${rowT} / ${cr.tickers[j]}: ${v.toFixed(3)}`}
                    >
                      {v.toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="heatmap-legend">
            <span style={{ color: "rgb(0,0,255)" }}>−1 (inverse)</span>
            <span style={{ color: "#888" }}>0 (uncorrelated)</span>
            <span style={{ color: "rgb(255,0,0)" }}>+1 (perfect)</span>
          </div>
        </div>
      )}
    </div>
  );
}
