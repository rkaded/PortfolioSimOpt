import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { runOptimize } from "../api/client";
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceDot, Label
} from "recharts";

const FMT_PCT = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(2)}%`;

export default function OptimiserPanel() {
  const {
    assets, constraints, targetReturn, benchmarkTicker, lookbackYears,
    setTargetReturn, setBenchmarkTicker, setLookbackYears,
    optimizeResult, setOptimizeResult,
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

    setRunning(true); setError(null); setOptimizeResult(null);
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
      setError(e?.response?.data?.detail ?? "Optimisation failed.");
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
      <div className="panel-header"><h2>Optimiser</h2></div>

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
            {[1, 2, 3, 5].map((y) => <option key={y} value={y}>{y}yr</option>)}
          </select>
        </label>
        <button className="btn-primary" onClick={runOpt} disabled={running || assets.length < 2}>
          {running ? "Optimising…" : "Run Optimiser"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {isInfeasible && (
        <InfeasibleCard
          bindingConstraint={optimizeResult!.binding_constraint}
          violation={optimizeResult!.violation}
          message={optimizeResult!.message}
        />
      )}

      {optimizeResult?.status === "ok" && (
        <>
          <div className="metrics-row">
            <Metric label="Expected Return" value={FMT_PCT(optimizeResult.portfolio_expected_return)} />
            <Metric label="Volatility (σ)" value={FMT_PCT(optimizeResult.portfolio_volatility)} />
            <Metric label="Sharpe Ratio" value={optimizeResult.sharpe_ratio?.toFixed(2) ?? "—"} />
          </div>

          {optimizeResult.mu_adjustments && (
            <div className="mu-adjustment-note">
              <span className="mu-adj-label">
                ⓘ Expected returns adjusted from CAGR → arithmetic mean (+σ²/2) for MVO accuracy
              </span>
              <div className="mu-adj-table">
                {Object.entries(optimizeResult.mu_adjustments)
                  .filter(([, v]: [string, any]) => v.adjustment_pct > 0.01)
                  .sort(([, a]: [string, any], [, b]: [string, any]) => b.adjustment_pct - a.adjustment_pct)
                  .map(([ticker, v]: [string, any]) => (
                    <span key={ticker} className="mu-adj-chip">
                      {ticker}: {v.input_pct.toFixed(1)}% → {v.adjusted_pct.toFixed(1)}%
                      <span className="mu-adj-bump"> (+{v.adjustment_pct.toFixed(1)}pp)</span>
                    </span>
                  ))}
              </div>
            </div>
          )}

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
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="x" name="Volatility" unit="%" type="number" domain={["auto", "auto"]}>
                    <Label value="Volatility (%)" position="insideBottom" offset={-15} fill="#64748b" />
                  </XAxis>
                  <YAxis dataKey="y" name="Return" unit="%" type="number">
                    <Label value="Expected Return (%)" angle={-90} position="insideLeft" offset={10} fill="#64748b" />
                  </YAxis>
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v) => typeof v === "number" ? `${v.toFixed(2)}%` : v} />
                  <Scatter
                    data={frontier.map((p) => ({ x: p.volatility * 100, y: p.expected_return * 100 }))}
                    fill="#2563eb"
                    opacity={0.7}
                  />
                  {currentPoint && (
                    <ReferenceDot
                      x={currentPoint.x}
                      y={currentPoint.y}
                      r={6}
                      fill="#d97706"
                      stroke="#fff"
                      strokeWidth={2}
                      label={{ value: "●", position: "top", fill: "#d97706" }}
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

const CONSTRAINT_EXPLANATIONS: Record<string, { title: string; fix: string }> = {
  target_return: {
    title: "Target return is too high",
    fix: "Lower your target return, or add higher-expected-return assets to the portfolio.",
  },
  locked_positions: {
    title: "Locked positions leave no room",
    fix: "Your locked positions sum to 100% or more. Reduce the locked weights to leave room for the optimiser.",
  },
  "locked_positions/esg_exclusions": {
    title: "All assets are locked or excluded",
    fix: "Every asset is either locked or ESG-excluded. Remove some exclusions or unlock positions.",
  },
  constraints_combination: {
    title: "Constraints conflict with each other",
    fix: "Your combination of sector caps, asset floors, and return target cannot be satisfied simultaneously. Try relaxing one constraint at a time.",
  },
};

function resolveExplanation(raw: string | undefined): { title: string; fix: string } {
  if (!raw) return { title: "No feasible solution found", fix: "Review your constraints and target return." };

  if (CONSTRAINT_EXPLANATIONS[raw]) return CONSTRAINT_EXPLANATIONS[raw];

  // Dynamic patterns
  if (raw.startsWith("sector_cap:")) {
    const sector = raw.replace("sector_cap:", "");
    return {
      title: `Sector cap too tight: ${sector}`,
      fix: `The minimum weights you've set for assets in "${sector}" exceed the sector cap. Reduce asset floor constraints or raise the sector cap.`,
    };
  }
  if (raw.startsWith("asset_bounds:")) {
    const ticker = raw.replace("asset_bounds:", "");
    return {
      title: `Asset bound conflict: ${ticker}`,
      fix: `The minimum weight for ${ticker} is set higher than its maximum weight. Fix the bounds in the Constraints panel.`,
    };
  }

  return { title: "Optimiser could not find a feasible solution", fix: "Review your constraints and target return." };
}

function InfeasibleCard({ bindingConstraint, violation, message }: {
  bindingConstraint?: string;
  violation?: number | null;
  message?: string;
}) {
  const { title, fix } = resolveExplanation(bindingConstraint);
  return (
    <div className="infeasible-box">
      <div className="infeasible-title">⚠ {title}</div>
      {violation != null && (
        <div className="infeasible-violation">
          Missed by {(violation * 100).toFixed(2)}%
        </div>
      )}
      <p className="infeasible-fix">{fix}</p>
      {message && <p className="infeasible-detail">{message}</p>}
    </div>
  );
}
