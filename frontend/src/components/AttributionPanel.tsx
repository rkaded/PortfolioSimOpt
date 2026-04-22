import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { fetchAttribution, exportAttributionCsv } from "../api/client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from "recharts";

const COLORS = ["#4f8ef7", "#4caf50", "#f7c94f", "#f7794f", "#a78bfa", "#fb7185", "#34d399", "#f59e0b"];

export default function AttributionPanel() {
  const { assets, optimizeResult, lookbackYears, attributionResult, setAttributionResult } = usePortfolioStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const weights = optimizeResult?.status === "ok" ? optimizeResult.weights! : null;

  async function load() {
    if (!weights) { setError("Run optimiser first to get weights."); return; }
    setLoading(true); setError(null);
    try {
      const result = await fetchAttribution(assets.map((a) => a.ticker), weights, lookbackYears);
      setAttributionResult(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Attribution failed.");
    } finally {
      setLoading(false);
    }
  }

  async function doExport() {
    if (!weights) return;
    setExporting(true);
    try {
      await exportAttributionCsv(assets.map((a) => a.ticker), weights, lookbackYears);
    } catch (e: any) {
      setError("Export failed.");
    } finally {
      setExporting(false);
    }
  }

  const attr = attributionResult;
  const tickers = assets.map((a) => a.ticker);

  const periodChartData = attr?.periods.slice(-12).map((p) => {
    const entry: Record<string, any> = { date: p.date };
    for (const t of tickers) {
      entry[t] = parseFloat(((p.contributions[t] ?? 0) * 100).toFixed(3));
    }
    return entry;
  }) ?? [];

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Return Attribution</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-secondary" onClick={load} disabled={loading || !weights}>
            {loading ? "Loading…" : "Load"}
          </button>
          {attr && (
            <button className="btn-ghost" onClick={doExport} disabled={exporting}>
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
          )}
        </div>
      </div>
      <p className="constraint-hint">
        Return contribution analysis: weight × return per period. Monthly breakdown.
      </p>

      {error && <div className="error-msg">{error}</div>}

      {attr && (
        <>
          <div className="attr-overall">
            <h3>Overall Contribution (full period)</h3>
            <div className="weights-bars">
              {attr.overall_summary.map((s, i) => (
                <div key={s.ticker} className="weight-bar-row">
                  <span className="weight-ticker">{s.ticker}</span>
                  <div className="weight-bar-track">
                    <div
                      className="weight-bar-fill"
                      style={{
                        width: `${Math.abs(s.total_contribution) * 200}%`,
                        background: s.total_contribution >= 0 ? COLORS[i % COLORS.length] : "#f7794f",
                      }}
                    />
                  </div>
                  <span className="weight-pct">
                    {s.total_contribution >= 0 ? "+" : ""}{(s.total_contribution * 100).toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="attr-chart">
            <h3>Monthly Attribution (last 12 months)</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={periodChartData} margin={{ top: 10, right: 10, bottom: 30, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" interval={0} />
                <YAxis tickFormatter={(v) => `${v.toFixed(1)}%`} />
                <Tooltip formatter={(v) => typeof v === "number" ? `${v.toFixed(3)}%` : v} />
                <Legend />
                {tickers.map((t, i) => (
                  <Bar key={t} dataKey={t} stackId="a" fill={COLORS[i % COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
