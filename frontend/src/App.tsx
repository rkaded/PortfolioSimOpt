import { useState } from "react";
import AssetPanel from "./components/AssetPanel";
import ConstraintPanel from "./components/ConstraintPanel";
import OptimizerPanel from "./components/OptimizerPanel";
import SimulationChart from "./components/SimulationChart";
import CorrelationHeatmap from "./components/CorrelationHeatmap";
import AttributionPanel from "./components/AttributionPanel";
import StressPanel from "./components/StressPanel";
import { usePortfolioStore } from "./store/portfolio";
import "./App.css";

type Tab = "assets" | "constraints" | "optimizer" | "simulation" | "stress" | "correlation" | "attribution";

const TABS: { id: Tab; label: string }[] = [
  { id: "assets",      label: "Assets" },
  { id: "optimizer",   label: "Optimiser" },
  { id: "simulation",  label: "Simulation" },
  { id: "stress",      label: "Stress Test" },
  { id: "correlation", label: "Correlation" },
  { id: "attribution", label: "Attribution" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("assets");
  const { clearPortfolio, assets } = usePortfolioStore();

  function handleClear() {
    if (confirm("Clear all assets and constraints? This cannot be undone.")) {
      clearPortfolio();
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="logo">Folio</span>
          {assets.length > 0 && (
            <span className="save-indicator">
              <span className="save-dot" />
              {assets.length} asset{assets.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="header-right">
          {assets.length > 0 && (
            <button className="btn-ghost-sm" onClick={handleClear}>Clear</button>
          )}
        </div>
      </header>

      <nav className="tab-nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {tab === "assets" && <AssetPanel />}
        {tab === "constraints" && <ConstraintPanel />}
        {tab === "optimizer" && <OptimizerPanel />}
        {tab === "simulation" && <SimulationChart />}
        {tab === "correlation" && <CorrelationHeatmap />}
        {tab === "stress"      && <StressPanel />}
        {tab === "attribution" && <AttributionPanel />}
      </main>

      <footer className="app-footer">
        Quantitative analysis only — not investment advice.
      </footer>
    </div>
  );
}
