import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { runStressTest, type StressPeriod } from "../api/client";

const FMT_PCT = (v: number | null) =>
  v == null ? "N/A" : `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;

function severity(r: number | null): string {
  if (r == null) return "stress-neutral";
  if (r <= -0.3) return "stress-severe";
  if (r <= -0.1) return "stress-bad";
  if (r < 0)     return "stress-mild";
  return "stress-positive";
}

export default function StressPanel() {
  const { assets, optimizeResult } = usePortfolioStore();
  const [periods, setPeriods] = useState<StressPeriod[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const weights = optimizeResult?.status === "ok" ? optimizeResult.weights : null;

  async function run() {
    if (!weights) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runStressTest(
        assets.map((a) => a.ticker),
        weights,
      );
      setPeriods(result.periods);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Stress test failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header"><h2>Historical Stress Test</h2></div>

      <p className="stress-description">
        Shows how your optimised portfolio would have performed during major historical
        market crises. Results use actual price data — not simulation.
      </p>

      {!weights && (
        <div className="info-msg">
          Run the Optimiser first to get portfolio weights, then stress-test them here.
        </div>
      )}

      {weights && (
        <div className="stress-controls">
          <div className="stress-weights-summary">
            {Object.entries(weights)
              .filter(([, w]) => w > 0.001)
              .sort(([, a], [, b]) => b - a)
              .map(([t, w]) => (
                <span key={t} className="weight-chip">{t} {(w * 100).toFixed(1)}%</span>
              ))}
          </div>
          <button className="btn-primary" onClick={run} disabled={loading}>
            {loading ? "Running…" : "Run Stress Test"}
          </button>
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      {periods && (
        <div className="stress-grid">
          {periods.map((p) => (
            <div key={p.label} className={`stress-card ${severity(p.portfolio_return)}`}>
              <div className="stress-card-header">
                <span className="stress-label">{p.label}</span>
                <span className="stress-date">{p.start} → {p.end}</span>
              </div>
              <div className="stress-return">{FMT_PCT(p.portfolio_return)}</div>
              {p.note && <div className="stress-note">{p.note}</div>}
              {!p.note && p.asset_returns && (
                <div className="stress-breakdown">
                  {Object.entries(p.asset_returns)
                    .sort(([, a], [, b]) => a - b)
                    .map(([t, r]) => (
                      <span key={t} className={`stress-asset-chip ${r < 0 ? "neg" : "pos"}`}>
                        {t} {FMT_PCT(r)}
                      </span>
                    ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="disclosure not-advice">
        Historical performance does not predict future results. Returns assume static weights
        with no rebalancing. Assets listed in the portfolio may have no data for older periods.
      </div>
    </div>
  );
}
