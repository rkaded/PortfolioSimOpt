import { useState } from "react";
import { usePortfolioStore } from "../store/portfolio";
import type { Constraints } from "../api/client";

export default function ConstraintPanel() {
  const { assets, constraints, setConstraints } = usePortfolioStore();
  const tickers = assets.map((a) => a.ticker);

  const [newEsg, setNewEsg] = useState("");
  const [newLockedTicker, setNewLockedTicker] = useState("");
  const [newLockedWeight, setNewLockedWeight] = useState("");
  const [newBoundTicker, setNewBoundTicker] = useState("");
  const [newBoundMin, setNewBoundMin] = useState("");
  const [newBoundMax, setNewBoundMax] = useState("");
  const [newSectorName, setNewSectorName] = useState("");
  const [newSectorMax, setNewSectorMax] = useState("");
  const [newSectorTickers, setNewSectorTickers] = useState<string[]>([]);

  function update(patch: Partial<Constraints>) {
    setConstraints({ ...constraints, ...patch });
  }

  function addLocked() {
    const t = newLockedTicker.toUpperCase().trim();
    const w = parseFloat(newLockedWeight) / 100;
    if (!t || isNaN(w) || w <= 0 || w > 1) return;
    update({ locked_positions: [...constraints.locked_positions.filter((l) => l.ticker !== t), { ticker: t, weight: w }] });
    setNewLockedTicker(""); setNewLockedWeight("");
  }

  function removeLocked(ticker: string) {
    update({ locked_positions: constraints.locked_positions.filter((l) => l.ticker !== ticker) });
  }

  function addBound() {
    const t = newBoundTicker.toUpperCase().trim();
    const mn = newBoundMin === "" ? 0 : parseFloat(newBoundMin) / 100;
    const mx = newBoundMax === "" ? 1 : parseFloat(newBoundMax) / 100;
    if (!t) return;
    update({ asset_bounds: [...constraints.asset_bounds.filter((b) => b.ticker !== t), { ticker: t, min_weight: mn, max_weight: mx }] });
    setNewBoundTicker(""); setNewBoundMin(""); setNewBoundMax("");
  }

  function removeBound(ticker: string) {
    update({ asset_bounds: constraints.asset_bounds.filter((b) => b.ticker !== ticker) });
  }

  function addSector() {
    const name = newSectorName.trim();
    const max = parseFloat(newSectorMax) / 100;
    if (!name || isNaN(max) || newSectorTickers.length === 0) return;
    update({ sector_caps: [...constraints.sector_caps.filter((s) => s.sector !== name), { sector: name, tickers: newSectorTickers, max_weight: max }] });
    setNewSectorName(""); setNewSectorMax(""); setNewSectorTickers([]);
  }

  function removeSector(sector: string) {
    update({ sector_caps: constraints.sector_caps.filter((s) => s.sector !== sector) });
  }

  function addEsg() {
    const t = newEsg.toUpperCase().trim();
    if (!t || constraints.esg_exclusions.includes(t)) return;
    update({ esg_exclusions: [...constraints.esg_exclusions, t] });
    setNewEsg("");
  }

  function removeEsg(t: string) {
    update({ esg_exclusions: constraints.esg_exclusions.filter((e) => e !== t) });
  }

  function toggleSectorTicker(t: string) {
    setNewSectorTickers((prev) => prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]);
  }

  return (
    <div className="panel">
      <div className="panel-header"><h2>Constraints</h2></div>

      {/* Locked Positions */}
      <section className="constraint-section">
        <h3>Locked Positions</h3>
        <p className="constraint-hint">Fixed-weight assets removed from optimisation.</p>
        <div className="constraint-row">
          <input placeholder="Ticker" value={newLockedTicker} onChange={(e) => setNewLockedTicker(e.target.value.toUpperCase())} className="small-input" />
          <input placeholder="Weight %" type="number" min="0" max="100" value={newLockedWeight} onChange={(e) => setNewLockedWeight(e.target.value)} className="small-input" />
          <button className="btn-secondary" onClick={addLocked}>Add</button>
        </div>
        {constraints.locked_positions.map((lp) => (
          <div key={lp.ticker} className="tag">
            {lp.ticker} @ {(lp.weight * 100).toFixed(1)}%
            <button onClick={() => removeLocked(lp.ticker)}>✕</button>
          </div>
        ))}
      </section>

      {/* Asset Bounds */}
      <section className="constraint-section">
        <h3>Asset Floor / Ceiling</h3>
        <div className="constraint-row">
          <input placeholder="Ticker" value={newBoundTicker} onChange={(e) => setNewBoundTicker(e.target.value.toUpperCase())} className="small-input" />
          <input placeholder="Min %" type="number" min="0" max="100" value={newBoundMin} onChange={(e) => setNewBoundMin(e.target.value)} className="small-input" />
          <input placeholder="Max %" type="number" min="0" max="100" value={newBoundMax} onChange={(e) => setNewBoundMax(e.target.value)} className="small-input" />
          <button className="btn-secondary" onClick={addBound}>Add</button>
        </div>
        {constraints.asset_bounds.map((ab) => (
          <div key={ab.ticker} className="tag">
            {ab.ticker} [{(ab.min_weight * 100).toFixed(0)}%–{(ab.max_weight * 100).toFixed(0)}%]
            <button onClick={() => removeBound(ab.ticker)}>✕</button>
          </div>
        ))}
      </section>

      {/* Sector Caps */}
      <section className="constraint-section">
        <h3>Sector Concentration Caps</h3>
        <div className="constraint-row">
          <input placeholder="Sector name" value={newSectorName} onChange={(e) => setNewSectorName(e.target.value)} className="small-input" />
          <input placeholder="Max %" type="number" min="0" max="100" value={newSectorMax} onChange={(e) => setNewSectorMax(e.target.value)} className="small-input" />
        </div>
        {tickers.length > 0 && (
          <div className="ticker-select-row">
            {tickers.map((t) => (
              <label key={t} className={`ticker-checkbox ${newSectorTickers.includes(t) ? "selected" : ""}`}>
                <input type="checkbox" checked={newSectorTickers.includes(t)} onChange={() => toggleSectorTicker(t)} />
                {t}
              </label>
            ))}
          </div>
        )}
        <button className="btn-secondary" onClick={addSector} disabled={!newSectorName || !newSectorMax || newSectorTickers.length === 0}>
          Add Sector Cap
        </button>
        {constraints.sector_caps.map((sc) => (
          <div key={sc.sector} className="tag">
            {sc.sector} ≤ {(sc.max_weight * 100).toFixed(0)}% ({sc.tickers.join(", ")})
            <button onClick={() => removeSector(sc.sector)}>✕</button>
          </div>
        ))}
      </section>

      {/* ESG Exclusions */}
      <section className="constraint-section">
        <h3>ESG Exclusions</h3>
        <div className="constraint-row">
          <input placeholder="Ticker to exclude" value={newEsg} onChange={(e) => setNewEsg(e.target.value.toUpperCase())} className="small-input"
            onKeyDown={(e) => e.key === "Enter" && addEsg()} />
          <button className="btn-secondary" onClick={addEsg}>Exclude</button>
        </div>
        {constraints.esg_exclusions.map((t) => (
          <div key={t} className="tag esg-tag">{t}<button onClick={() => removeEsg(t)}>✕</button></div>
        ))}
      </section>
    </div>
  );
}
