import { create } from "zustand";
import type { Constraints, OptimizeResult, SimulationResult, AttributionResult, CorrelationResult, AssetStats } from "../api/client";

export interface AssetRow {
  ticker: string;
  expectedReturn: string; // user input as string (pct, e.g. "8")
  stats: AssetStats | null;
  dataWarnings: string[];
  returnWarning: string | null;
}

interface PortfolioState {
  assets: AssetRow[];
  constraints: Constraints;
  targetReturn: string;
  benchmarkTicker: string;
  lookbackYears: number;
  horizonYears: number;
  dataLastUpdated: string | null;
  loading: boolean;
  optimizeResult: OptimizeResult | null;
  simulationResult: SimulationResult | null;
  attributionResult: AttributionResult | null;
  correlationResult: CorrelationResult | null;

  setAssets: (assets: AssetRow[]) => void;
  updateAsset: (ticker: string, patch: Partial<AssetRow>) => void;
  removeAsset: (ticker: string) => void;
  setConstraints: (c: Constraints) => void;
  setTargetReturn: (v: string) => void;
  setBenchmarkTicker: (v: string) => void;
  setLookbackYears: (v: number) => void;
  setHorizonYears: (v: number) => void;
  setDataLastUpdated: (v: string) => void;
  setLoading: (v: boolean) => void;
  setOptimizeResult: (v: OptimizeResult | null) => void;
  setSimulationResult: (v: SimulationResult | null) => void;
  setAttributionResult: (v: AttributionResult | null) => void;
  setCorrelationResult: (v: CorrelationResult | null) => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  assets: [],
  constraints: {
    locked_positions: [],
    sector_caps: [],
    asset_bounds: [],
    esg_exclusions: [],
  },
  targetReturn: "7",
  benchmarkTicker: "SPY",
  lookbackYears: 10,
  horizonYears: 5,
  dataLastUpdated: null,
  loading: false,
  optimizeResult: null,
  simulationResult: null,
  attributionResult: null,
  correlationResult: null,

  setAssets: (assets) => set({ assets }),
  updateAsset: (ticker, patch) =>
    set((s) => ({ assets: s.assets.map((a) => (a.ticker === ticker ? { ...a, ...patch } : a)) })),
  removeAsset: (ticker) =>
    set((s) => ({ assets: s.assets.filter((a) => a.ticker !== ticker) })),
  setConstraints: (constraints) => set({ constraints }),
  setTargetReturn: (targetReturn) => set({ targetReturn }),
  setBenchmarkTicker: (benchmarkTicker) => set({ benchmarkTicker }),
  setLookbackYears: (lookbackYears) => set({ lookbackYears }),
  setHorizonYears: (horizonYears) => set({ horizonYears }),
  setDataLastUpdated: (dataLastUpdated) => set({ dataLastUpdated }),
  setLoading: (loading) => set({ loading }),
  setOptimizeResult: (optimizeResult) => set({ optimizeResult }),
  setSimulationResult: (simulationResult) => set({ simulationResult }),
  setAttributionResult: (attributionResult) => set({ attributionResult }),
  setCorrelationResult: (correlationResult) => set({ correlationResult }),
}));
