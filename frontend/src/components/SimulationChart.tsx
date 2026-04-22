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

export default function SimulationChart() {
  const {
    assets, optimizeResult, lookbackYears, benchmarkTicker,
    horizonYears, setHorizonYears, simulationResult, setSimulationResult,
  } = usePortfolioStore();

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const weights = optimizeResult?.status === "ok" ? optimizeResult.weights! : null;

  async function simulate() {
    if (!weights) { setError("Run optimizer first."); return; }
    setRunning(true); setError(null);
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

  const chartData = sim
    ? sim.bullish.map((_, i) => {
        const year = ((i + 1) / 252).toFixed(2);
        return {
          day: i + 1,
          year: parseFloat(year),
          bullish: sim.bullish[i],
          normal: sim.normal[i],
          bearish: sim.bearish[i],
          benchmark: sim.benchmark_path?.[i],
        };
      }).filter((_, i) => i % 5 === 0)
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
            &nbsp;·&nbsp; 10,000 paths &nbsp;·&nbsp; Parametric multivariate normal with Ledoit-Wolf covariance
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="year" unit="yr" type="number" domain={[0, horizonYears]} tickCount={horizonYears + 1} />
              <YAxis tickFormatter={(v) => `${((v - 1) * 100).toFixed(0)}%`} />
              <Tooltip
                formatter={(v, name) => [typeof v === "number" ? FMT(v) : v, name]}
                labelFormatter={(l) => `Year ${l}`}
              />
              <Legend />
              <ReferenceLine y={1} stroke="#555" strokeDasharray="4 2" />
              <Line type="monotone" dataKey="bullish" stroke="#4caf50" dot={false} name="Bullish (75th pct)" strokeWidth={2} />
              <Line type="monotone" dataKey="normal" stroke="#4f8ef7" dot={false} name="Normal (50th pct)" strokeWidth={2} />
              <Line type="monotone" dataKey="bearish" stroke="#f7794f" dot={false} name="Bearish (25th pct)" strokeWidth={2} />
              {sim.benchmark_path && (
                <Line type="monotone" dataKey="benchmark" stroke="#aaa" dot={false} strokeDasharray="5 3" name={`${benchmarkTicker} (median)`} strokeWidth={1.5} />
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
                <Metric label="Tracking Error" value={PCT(bm.tracking_error)} />
                <Metric label="Information Ratio" value={bm.information_ratio?.toFixed(2) ?? "—"} />
                <Metric label="Beta" value={bm.beta?.toFixed(2) ?? "—"} />
                <Metric label="Max Drawdown (Portfolio)" value={PCT(bm.max_drawdown_portfolio)} />
                <Metric label="Max Drawdown (Benchmark)" value={PCT(bm.max_drawdown_benchmark)} />
              </div>
            </div>
          )}

          <div className="scenario-summary">
            <h3>Scenario Outcomes ({horizonYears}yr horizon)</h3>
            <table className="asset-table">
              <thead>
                <tr>
                  <th>Scenario</th><th>Final Value</th><th>Ann. Return</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Bullish (75th pct)</td>
                  <td>${sim.summary.bullish_final.toFixed(2)}</td>
                  <td>{PCT(sim.summary.annualised_return_p75)}</td>
                </tr>
                <tr>
                  <td>Normal (50th pct)</td>
                  <td>${sim.summary.normal_final.toFixed(2)}</td>
                  <td>{PCT(sim.summary.annualised_return_p50)}</td>
                </tr>
                <tr>
                  <td>Bearish (25th pct)</td>
                  <td>${sim.summary.bearish_final.toFixed(2)}</td>
                  <td>{PCT(sim.summary.annualised_return_p25)}</td>
                </tr>
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}
