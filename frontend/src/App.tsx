import { useState } from "react";
import AssetPanel from "./components/AssetPanel";
import ConstraintPanel from "./components/ConstraintPanel";
import OptimizerPanel from "./components/OptimizerPanel";
import SimulationChart from "./components/SimulationChart";
import CorrelationHeatmap from "./components/CorrelationHeatmap";
import AttributionPanel from "./components/AttributionPanel";
import "./App.css";

type Tab = "assets" | "constraints" | "optimizer" | "simulation" | "correlation" | "attribution";

const TABS: { id: Tab; label: string }[] = [
  { id: "assets", label: "Assets" },
  { id: "constraints", label: "Constraints" },
  { id: "optimizer", label: "Optimiser" },
  { id: "simulation", label: "Simulation" },
  { id: "correlation", label: "Correlation" },
  { id: "attribution", label: "Attribution" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("assets");

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="logo">Folio</span>
          <span className="version">v1.0 · Private Banking</span>
        </div>
        <div className="not-advice-banner">
          Quantitative analysis only — not investment advice.
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
        {tab === "attribution" && <AttributionPanel />}
      </main>
    </div>
  );
}
