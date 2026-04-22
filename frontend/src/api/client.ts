import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000" });

export interface AssetStats {
  return_1yr: number | null;
  return_3yr: number | null;
  return_5yr: number | null;
  std_5yr: number | null;
}

export interface FetchAssetsResponse {
  tickers: string[];
  data_last_updated: string;
  lookback_years: number;
  stats: Record<string, AssetStats | null>;
  data_warnings: Record<string, string[]>;
  return_warnings: Record<string, string>;
}

export interface LockedPosition { ticker: string; weight: number }
export interface SectorCap { sector: string; tickers: string[]; max_weight: number }
export interface AssetBound { ticker: string; min_weight: number; max_weight: number }
export interface Constraints {
  locked_positions: LockedPosition[];
  sector_caps: SectorCap[];
  asset_bounds: AssetBound[];
  esg_exclusions: string[];
}

export interface OptimizeResult {
  status: "ok" | "infeasible";
  weights?: Record<string, number>;
  portfolio_volatility?: number;
  portfolio_expected_return?: number;
  sharpe_ratio?: number | null;
  efficient_frontier?: { expected_return: number; volatility: number }[];
  binding_constraint?: string;
  violation?: number;
  message?: string;
}

export interface SimulationResult {
  bearish: number[];
  normal: number[];
  bullish: number[];
  benchmark_path?: number[];
  trading_days: number;
  horizon_years: number;
  n_paths: number;
  summary: {
    bearish_final: number;
    normal_final: number;
    bullish_final: number;
    annualised_return_p25: number;
    annualised_return_p50: number;
    annualised_return_p75: number;
  };
  benchmark_metrics: {
    tracking_error: number;
    information_ratio: number | null;
    beta: number | null;
    max_drawdown_portfolio: number;
    max_drawdown_benchmark: number;
  };
  disclosure: { fat_tail: string; long_only: string; not_advice: string };
}

export interface AttributionResult {
  periods: {
    date: string;
    portfolio_return: number;
    contributions: Record<string, number>;
    top_contributors: { ticker: string; contribution: number }[];
    detractors: { ticker: string; contribution: number }[];
  }[];
  overall_summary: { ticker: string; total_contribution: number }[];
  period_type: string;
}

export interface CorrelationResult {
  tickers: string[];
  matrix: number[][];
}

export const fetchAssets = (tickers: string[], lookback_years: number, expected_returns: Record<string, number>) =>
  api.post<FetchAssetsResponse>("/assets/fetch", { tickers, lookback_years, expected_returns }).then((r) => r.data);

export const runOptimize = (
  assets: { ticker: string; expected_return: number }[],
  constraints: Constraints,
  target_return: number,
  lookback_years: number,
  benchmark_ticker: string
) =>
  api.post<OptimizeResult>("/optimize", { assets, constraints, target_return, lookback_years, benchmark_ticker }).then((r) => r.data);

export const runSimulation = (
  assets: { ticker: string; expected_return: number }[],
  weights: Record<string, number>,
  horizon_years: number,
  lookback_years: number,
  benchmark_ticker: string
) =>
  api.post<SimulationResult>("/simulate", { assets, weights, horizon_years, lookback_years, benchmark_ticker }).then((r) => r.data);

export const fetchAttribution = (assets: string[], weights: Record<string, number>, lookback_years: number) =>
  api.post<AttributionResult>("/attribution", { assets, weights, lookback_years }).then((r) => r.data);

export const fetchCorrelation = (tickers: string[], lookback_years: number) =>
  api.post<CorrelationResult>("/assets/correlation", { tickers, lookback_years }).then((r) => r.data);

export const exportAttributionCsv = (assets: string[], weights: Record<string, number>, lookback_years: number) =>
  api
    .post("/attribution/export", { assets, weights, lookback_years }, { responseType: "blob" })
    .then((r) => {
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "attribution.csv";
      a.click();
      URL.revokeObjectURL(url);
    });
