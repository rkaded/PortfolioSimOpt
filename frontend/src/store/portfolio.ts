import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Constraints, OptimizeResult, SimulationResult, AttributionResult, CorrelationResult, AssetStats } from "../api/client";

export interface AssetRow {
  ticker: string;
  expectedReturn: string;
  stats: AssetStats | null;
  dataWarnings: string[];
  returnWarning: string | null;
}

interface PortfolioState {
  // --- persisted inputs ---
  assets: AssetRow[];
  constraints: Constraints;
  targetReturn: string;
  benchmarkTicker: string;
  lookbackYears: number;
  horizonYears: number;

  // --- session-only ---
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
  clearPortfolio: () => void;
}

const EMPTY_CONSTRAINTS: Constraints = {
  locked_positions: [],
  sector_caps: [],
  asset_bounds: [],
  esg_exclusions: [],
};

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set) => ({
      assets: [],
      constraints: EMPTY_CONSTRAINTS,
      targetReturn: "7",
      benchmarkTicker: "SPY",
      lookbackYears: 5,
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
      clearPortfolio: () =>
        set({
          assets: [],
          constraints: EMPTY_CONSTRAINTS,
          targetReturn: "7",
          benchmarkTicker: "SPY",
          lookbackYears: 5,
          horizonYears: 5,
          optimizeResult: null,
          simulationResult: null,
          attributionResult: null,
          correlationResult: null,
        }),
    }),
    {
      name: "folio-portfolio",
      // Only persist the user's inputs — never persist derived/session state
      partialize: (s) => ({
        assets: s.assets.map((a) => ({
          ticker: a.ticker,
          expectedReturn: a.expectedReturn,
          // Drop fetched data — re-fetched on load
          stats: null,
          dataWarnings: [],
          returnWarning: null,
        })),
        constraints: s.constraints,
        targetReturn: s.targetReturn,
        benchmarkTicker: s.benchmarkTicker,
        lookbackYears: s.lookbackYears,
        horizonYears: s.horizonYears,
      }),
    }
  )
);
