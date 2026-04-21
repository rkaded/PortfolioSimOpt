import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { runOptimize } from "../api/client";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceDot, Label
} from "recharts";

const FMT_PCT = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(2)}%`;

export default function OptimizerPanel() {
  const {
    assets, constraints, targetReturn, benchmarkTicker, lookbackYears,
    setTargetReturn, setBenchmarkTicker, setLookbackYears,
    optimizeResult, setOptimizeResult, setLoading,
  } = usePortfolioStore();

  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function runOpt() {
    const missing = assets.filter((a) => a.expectedReturn === "");
    if (missing.length > 0) {
      setError(`Set expected return for: ${missing.map((a) => a.ticker).join(", ")}`);
      return;
    }
    if (assets.length < 2) { setError("Add at least 2 assets."); return; }
    const tr = parseFloat(targetReturn) / 100;
    if (isNaN(tr)) { setError("Invalid target return."); return; }

    setRunning(true); setError(null);
    try {
      const result = await runOptimize(
        assets.map((a) => ({ ticker: a.ticker, expected_return: parseFloat(a.expectedReturn) })),
        constraints,
        tr,
        lookbackYears,
        benchmarkTicker
      );
      setOptimizeResult(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Optimization failed.");
    } finally {
      setRunning(false);
    }
  }

  const isInfeasible = optimizeResult?.status === "infeasible";
  const frontier = optimizeResult?.efficient_frontier ?? [];
  const currentPoint = optimizeResult?.status === "ok"
    ? { x: (optimizeResult.portfolio_volatility ?? 0) * 100, y: (optimizeResult.portfolio_expected_return ?? 0) * 100 }
    : null;

  return (
    <div className="panel">
      <div className="panel-header"><h2>Optimizer</h2></div>

      <div className="opt-controls">
        <label>
          Target Return (%)
          <input type="number" value={targetReturn} onChange={(e) => setTargetReturn(e.target.value)} className="small-input" />
        </label>
        <label>
          Benchmark
          <input value={benchmarkTicker} onChange={(e) => setBenchmarkTicker(e.target.value.toUpperCase())} className="small-input" />
        </label>
        <label>
          Lookback (years)
          <select value={lookbackYears} onChange={(e) => setLookbackYears(Number(e.target.value))}>
            {[1, 2, 3, 5, 7, 10].map((y) => <option key={y} value={y}>{y}yr</option>)}
          </select>
        </label>
        <button className="btn-primary" onClick={runOpt} disabled={running || assets.length < 2}>
          {running ? "Optimizing…" : "Run Optimizer"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {isInfeasible && (
        <div className="infeasible-box">
          <strong>Optimizer Infeasible</strong>
          <p>{optimizeResult!.message}</p>
          <p className="binding">
            Binding constraint: <code>{optimizeResult!.binding_constraint}</code>
            {optimizeResult!.violation != null && ` (by ${(optimizeResult!.violation * 100).toFixed(2)}%)`}
          </p>
          <p className="relax-hint">Relax the binding constraint above to find a feasible solution.</p>
        </div>
      )}

      {optimizeResult?.status === "ok" && (
        <>
          <div className="metrics-row">
            <Metric label="Expected Return" value={FMT_PCT(optimizeResult.portfolio_expected_return)} />
            <Metric label="Volatility (σ)" value={FMT_PCT(optimizeResult.portfolio_volatility)} />
            <Metric label="Sharpe Ratio" value={optimizeResult.sharpe_ratio?.toFixed(2) ?? "—"} />
          </div>

          <div className="weights-section">
            <h3>Optimal Weights</h3>
            <div className="weights-bars">
              {Object.entries(optimizeResult.weights!)
                .sort((a, b) => b[1] - a[1])
                .map(([ticker, w]) => (
                  <div key={ticker} className="weight-bar-row">
                    <span className="weight-ticker">{ticker}</span>
                    <div className="weight-bar-track">
                      <div className="weight-bar-fill" style={{ width: `${w * 100}%` }} />
                    </div>
                    <span className="weight-pct">{(w * 100).toFixed(1)}%</span>
                  </div>
                ))}
            </div>
          </div>

          {frontier.length > 0 && (
            <div className="frontier-section">
              <h3>Efficient Frontier</h3>
              <ResponsiveContainer width="100%" height={240}>
                <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                  <XAxis dataKey="x" name="Volatility" unit="%" type="number" domain={["auto", "auto"]}>
                    <Label value="Volatility (%)" position="insideBottom" offset={-15} fill="#888" />
                  </XAxis>
                  <YAxis dataKey="y" name="Return" unit="%" type="number">
                    <Label value="Expected Return (%)" angle={-90} position="insideLeft" offset={10} fill="#888" />
                  </YAxis>
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v: number) => `${v.toFixed(2)}%`} />
                  <Scatter
                    data={frontier.map((p) => ({ x: p.volatility * 100, y: p.expected_return * 100 }))}
                    fill="#4f8ef7"
                    opacity={0.7}
                  />
                  {currentPoint && (
                    <ReferenceDot
                      x={currentPoint.x}
                      y={currentPoint.y}
                      r={6}
                      fill="#f7c94f"
                      stroke="#fff"
                      strokeWidth={2}
                      label={{ value: "●", position: "top", fill: "#f7c94f" }}
                    />
                  )}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      <div className="disclosure not-advice">
        Quantitative analysis only — not investment advice.
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}
