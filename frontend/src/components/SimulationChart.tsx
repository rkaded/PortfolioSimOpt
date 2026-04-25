import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { runSimulation } from "../api/client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine
} from "recharts";

const PCT = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(2)}%`;

const FMT = (v: number) => `${((v - 1) * 100).toFixed(1)}%`;

// ── Tooltip-on-hover for jargon terms ────────────────────────────────────────
const METRIC_TOOLTIPS: Record<string, string> = {
  "Tracking Error":
    "How much your portfolio's daily returns deviate from the benchmark, annualised. Lower means the portfolio moves more like the benchmark.",
  "Information Ratio":
    "Excess return earned per unit of tracking risk taken versus the benchmark. Above 0.5 is generally considered good; negative means the portfolio underperformed.",
  "Beta":
    "Sensitivity to benchmark movements. Beta 1.0 = moves in lockstep with the benchmark; 0.5 = half the swings; >1.0 = amplified moves.",
  "Max Drawdown (Portfolio)":
    "The largest peak-to-trough percentage loss your portfolio experienced in the historical lookback period.",
  "Max Drawdown (Benchmark)":
    "The largest peak-to-trough percentage loss the benchmark experienced over the same period.",
};

function InfoIcon({ label }: { label: string }) {
  const tip = METRIC_TOOLTIPS[label];
  if (!tip) return null;
  return (
    <span className="info-tooltip">
      <span className="info-icon">ⓘ</span>
      <span className="tooltip-bubble">{tip}</span>
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">
        {label}
        <InfoIcon label={label} />
      </div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

export default function SimulationChart() {
  const {
    assets, optimizeResult, lookbackYears, benchmarkTicker,
    horizonYears, setHorizonYears, simulationResult, setSimulationResult,
  } = usePortfolioStore();

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const weights = optimizeResult?.status === "ok" ? optimizeResult.weights! : null;

  async function simulate() {
    if (!weights) { setError("Run optimiser first."); return; }
    setRunning(true); setError(null); setSimulationResult(null);
    try {
      const result = await runSimulation(
        assets.map((a) => ({ ticker: a.ticker, expected_return: parseFloat(a.expectedReturn) })),
        weights,
        horizonYears,
        lookbackYears,
        benchmarkTicker
      );
      setSimulationResult(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Simulation failed.");
    } finally {
      setRunning(false);
    }
  }

  const sim = simulationResult;

  // Backend returns monthly-sampled points (1 per ~21 trading days)
  // so index i = month i+1, year = (i+1)/12
  const chartData = sim
    ? sim.bullish.map((_, i) => ({
        month: i + 1,
        year:  parseFloat(((i + 1) / 12).toFixed(3)),
        bullish:   sim.bullish[i],
        normal:    sim.normal[i],
        bearish:   sim.bearish[i],
        benchmark: sim.benchmark_path?.[i],
      }))
    : [];

  const bm = sim?.benchmark_metrics;

  return (
    <div className="panel">
      <div className="panel-header"><h2>Monte Carlo Simulation</h2></div>

      <div className="sim-controls">
        <label>
          Horizon (years)
          <select value={horizonYears} onChange={(e) => setHorizonYears(Number(e.target.value))}>
            {[1, 2, 3, 5, 7, 10].map((y) => <option key={y} value={y}>{y}yr</option>)}
          </select>
        </label>
        <button className="btn-primary" onClick={simulate} disabled={running || !weights}>
          {running ? "Simulating…" : "Run Simulation"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {sim && (
        <>
          <div className="methodology-note">
            Scenarios: Bullish = 75th pct | Normal = 50th pct (median) | Bearish = 25th pct
            &nbsp;·&nbsp; 1,000 paths &nbsp;·&nbsp; Parametric normal with Ledoit-Wolf covariance
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="year" unit="yr" type="number" domain={[0, horizonYears]} tickCount={horizonYears + 1} />
              <YAxis tickFormatter={(v) => `${((v - 1) * 100).toFixed(0)}%`} />
              <Tooltip
                formatter={(v, name) => [typeof v === "number" ? FMT(v) : v, name]}
                labelFormatter={(l) => `Year ${l}`}
              />
              <Legend />
              <ReferenceLine y={1} stroke="#cbd5e1" strokeDasharray="4 2" />
              <Line type="monotone" dataKey="bullish" stroke="#16a34a" dot={false} name="Bullish (75th pct)" strokeWidth={2} />
              <Line type="monotone" dataKey="normal"  stroke="#2563eb" dot={false} name="Normal (50th pct)"  strokeWidth={2} />
              <Line type="monotone" dataKey="bearish" stroke="#dc2626" dot={false} name="Bearish (25th pct)" strokeWidth={2} />
              {sim.benchmark_path && (
                <Line type="monotone" dataKey="benchmark" stroke="#94a3b8" dot={false} strokeDasharray="5 3" name={`${benchmarkTicker} (median)`} strokeWidth={1.5} />
              )}
            </LineChart>
          </ResponsiveContainer>

          <div className="fat-tail-disclosure">
            ⚠ {sim.disclosure.fat_tail}
          </div>

          {bm && Object.keys(bm).length > 0 && (
            <div className="bm-metrics">
              <h3>vs {benchmarkTicker}</h3>
              <div className="metrics-row">
                <Metric label="Tracking Error"           value={PCT(bm.tracking_error)} />
                <Metric label="Information Ratio"        value={bm.information_ratio?.toFixed(2) ?? "—"} />
                <Metric label="Beta"                     value={bm.beta?.toFixed(2) ?? "—"} />
                <Metric label="Max Drawdown (Portfolio)" value={PCT(bm.max_drawdown_portfolio)} />
                <Metric label="Max Drawdown (Benchmark)" value={PCT(bm.max_drawdown_benchmark)} />
              </div>
            </div>
          )}

          <div className="scenario-summary">
            <h3>
              Scenario Outcomes ({horizonYears}yr horizon)
              <span className="scenario-subtitle">— growth of $1.00 invested today</span>
            </h3>
            <table className="asset-table">
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>
                    Grows to
                    <span className="col-hint"> (per $1 invested)</span>
                  </th>
                  <th>Ann. Return</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Bullish (75th pct)</td>
                  <td className="scenario-value bullish">${sim.summary.bullish_final.toFixed(2)}</td>
                  <td>{PCT(sim.summary.annualised_return_p75)}</td>
                </tr>
                <tr>
                  <td>Normal (50th pct)</td>
                  <td className="scenario-value normal">${sim.summary.normal_final.toFixed(2)}</td>
                  <td>{PCT(sim.summary.annualised_return_p50)}</td>
                </tr>
                <tr>
                  <td>Bearish (25th pct)</td>
                  <td className="scenario-value bearish">${sim.summary.bearish_final.toFixed(2)}</td>
                  <td>{PCT(sim.summary.annualised_return_p25)}</td>
                </tr>
                {sim.benchmark_path && (() => {
                  const bmFinal = sim.benchmark_path[sim.benchmark_path.length - 1];
                  const bmAnn   = Math.pow(bmFinal, 1 / horizonYears) - 1;
                  return (
                    <tr className="benchmark-row">
                      <td>{benchmarkTicker} (median)</td>
                      <td className="scenario-value benchmark">${bmFinal.toFixed(2)}</td>
                      <td>{PCT(bmAnn)}</td>
                    </tr>
                  );
                })()}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="disclosure not-advice">
        Quantitative analysis only — not investment advice.
      </div>
    </div>
  );
}
