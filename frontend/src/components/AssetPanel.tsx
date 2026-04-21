import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import { fetchAssets } from "../api/client";

const PCT = (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

export default function AssetPanel() {
  const { assets, setAssets, removeAsset, setDataLastUpdated, lookbackYears } = usePortfolioStore();
  const [tickerInput, setTickerInput] = useState("");
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const expectedReturns = Object.fromEntries(
    assets.filter((a) => a.expectedReturn !== "").map((a) => [a.ticker, parseFloat(a.expectedReturn)])
  );

  async function addTicker() {
    const ticker = tickerInput.trim().toUpperCase();
    if (!ticker) return;
    if (assets.find((a) => a.ticker === ticker)) {
      setError(`${ticker} already in portfolio.`);
      return;
    }
    setFetching(true);
    setError(null);
    try {
      const tickers = [...assets.map((a) => a.ticker), ticker];
      const result = await fetchAssets(tickers, lookbackYears, expectedReturns);
      const updated = tickers.map((t) => {
        const existing = assets.find((a) => a.ticker === t);
        const stats = result.stats[t] ?? null;
        // Auto-fill from 5yr CAGR if this is a new ticker with no user input yet
        const autoFill = !existing && stats?.return_5yr != null
          ? (stats.return_5yr * 100).toFixed(1)
          : null;
        return {
          ticker: t,
          expectedReturn: existing?.expectedReturn !== "" ? (existing?.expectedReturn ?? autoFill ?? "") : (autoFill ?? ""),
          stats,
          dataWarnings: result.data_warnings[t] ?? [],
          returnWarning: result.return_warnings[t] ?? null,
        };
      });
      setAssets(updated);
      setDataLastUpdated(result.data_last_updated);
      setTickerInput("");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to fetch data.");
    } finally {
      setFetching(false);
    }
  }

  function updateExpected(ticker: string, val: string) {
    usePortfolioStore.getState().updateAsset(ticker, { expectedReturn: val });
  }

  async function repull() {
    if (assets.length === 0) return;
    setFetching(true);
    setError(null);
    try {
      const tickers = assets.map((a) => a.ticker);
      const result = await fetchAssets(tickers, lookbackYears, expectedReturns);
      const updated = assets.map((a) => ({
        ...a,
        stats: result.stats[a.ticker] ?? null,
        dataWarnings: result.data_warnings[a.ticker] ?? [],
        returnWarning: result.return_warnings[a.ticker] ?? null,
      }));
      setAssets(updated);
      setDataLastUpdated(result.data_last_updated);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Re-pull failed.");
    } finally {
      setFetching(false);
    }
  }

  const { dataLastUpdated } = usePortfolioStore();

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Assets</h2>
        {dataLastUpdated && (
          <span className="freshness">
            Data as of {new Date(dataLastUpdated).toLocaleTimeString()}
            <button className="btn-ghost" onClick={repull} disabled={fetching}>
              {fetching ? "Pulling…" : "Re-pull"}
            </button>
          </span>
        )}
      </div>

      <div className="disclosure long-only">
        This tool assumes long-only positions. Short positions and derivatives are not supported.
      </div>

      <div className="add-row">
        <input
          className="ticker-input"
          placeholder="Add ticker (e.g. AAPL)"
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && addTicker()}
        />
        <button className="btn-primary" onClick={addTicker} disabled={fetching || !tickerInput.trim()}>
          {fetching ? "Loading…" : "Add"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {assets.length > 0 && (
        <table className="asset-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Exp. Return (%) <span className="col-hint">auto-filled from 5yr CAGR</span></th>
              <th>1yr Hist.</th>
              <th>3yr Hist.</th>
              <th>5yr Hist.</th>
              <th>σ (5yr)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <>
                <tr key={a.ticker}>
                  <td className="ticker-cell">{a.ticker}</td>
                  <td>
                    <input
                      type="number"
                      className="return-input"
                      placeholder="e.g. 8"
                      value={a.expectedReturn}
                      onChange={(e) => updateExpected(a.ticker, e.target.value)}
                    />
                  </td>
                  <td>{PCT(a.stats?.return_1yr ?? null)}</td>
                  <td>{PCT(a.stats?.return_3yr ?? null)}</td>
                  <td>{PCT(a.stats?.return_5yr ?? null)}</td>
                  <td>{PCT(a.stats?.std_5yr ?? null)}</td>
                  <td>
                    <button className="btn-remove" onClick={() => removeAsset(a.ticker)}>✕</button>
                  </td>
                </tr>
                {(a.dataWarnings.length > 0 || a.returnWarning) && (
                  <tr key={`${a.ticker}-warn`} className="warning-row">
                    <td colSpan={7}>
                      {a.dataWarnings.map((w, i) => (
                        <div key={i} className="warning data-warning">⚠ {w}</div>
                      ))}
                      {a.returnWarning && (
                        <div className="warning return-warning">⚠ {a.returnWarning}</div>
                      )}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      )}

      {assets.length === 0 && (
        <div className="empty-state">Add tickers to build your portfolio.</div>
      )}
    </div>
  );
}
