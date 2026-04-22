import numpy as np
import pandas as pd
from pypfopt import risk_models

BATCH_SIZE = 250  # paths per batch — keeps peak RAM ~15 MB regardless of n_paths


def run_monte_carlo(
    returns: pd.DataFrame,
    weights: dict[str, float],
    horizon_years: int = 5,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict:
    """
    Parametric Monte Carlo using multivariate normal with Ledoit-Wolf covariance.
    Processes paths in batches to keep memory usage flat regardless of n_paths.

    weights: {ticker: weight}, must sum to 1.0
    Returns paths in cumulative portfolio value space (starting at 1.0).
    """
    tickers = [t for t in weights if t in returns.columns]
    w = np.array([weights[t] for t in tickers])
    ret = returns[[t for t in tickers if t in returns.columns]].dropna()

    mu_daily = ret.mean().values
    cov_daily = risk_models.CovarianceShrinkage(ret, returns_data=True, frequency=252).ledoit_wolf().values / 252

    trading_days = horizon_years * 252
    rng = np.random.default_rng(seed)

    # Process in batches: each batch is (BATCH_SIZE, trading_days, n_assets)
    # Peak per-batch RAM = 250 × 1260 days × 5 stocks × 8 B ≈ 12 MB
    cum_chunks = []
    for i in range(0, n_paths, BATCH_SIZE):
        n = min(BATCH_SIZE, n_paths - i)
        draws = rng.multivariate_normal(mu_daily, cov_daily, size=(n, trading_days))
        port_daily = draws @ w
        cum_chunks.append(np.exp(np.cumsum(port_daily, axis=1)))

    cum_paths = np.vstack(cum_chunks)  # (n_paths, trading_days)

    p25 = np.percentile(cum_paths, 25, axis=0)
    p50 = np.percentile(cum_paths, 50, axis=0)
    p75 = np.percentile(cum_paths, 75, axis=0)

    final = cum_paths[:, -1]
    annual_returns = final ** (1 / horizon_years) - 1

    return {
        "bearish": p25.tolist(),
        "normal": p50.tolist(),
        "bullish": p75.tolist(),
        "trading_days": trading_days,
        "horizon_years": horizon_years,
        "n_paths": n_paths,
        "summary": {
            "bearish_final": float(p25[-1]),
            "normal_final": float(p50[-1]),
            "bullish_final": float(p75[-1]),
            "annualised_return_p25": float(np.percentile(annual_returns, 25)),
            "annualised_return_p50": float(np.percentile(annual_returns, 50)),
            "annualised_return_p75": float(np.percentile(annual_returns, 75)),
        },
    }


def run_benchmark_simulation(
    benchmark_returns: pd.Series,
    horizon_years: int = 5,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict:
    """Single-asset Monte Carlo for benchmark overlay. Batched for memory efficiency."""
    mu = float(benchmark_returns.mean())
    sigma = float(benchmark_returns.std())
    trading_days = horizon_years * 252
    rng = np.random.default_rng(seed + 1)

    cum_chunks = []
    for i in range(0, n_paths, BATCH_SIZE):
        n = min(BATCH_SIZE, n_paths - i)
        draws = rng.normal(mu, sigma, size=(n, trading_days))
        cum_chunks.append(np.exp(np.cumsum(draws, axis=1)))

    cum = np.vstack(cum_chunks)
    return {
        "normal": np.percentile(cum, 50, axis=0).tolist(),
        "trading_days": trading_days,
    }


def compute_benchmark_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> dict:
    """
    Tracking error, information ratio, beta, max drawdown vs benchmark.
    Both series should be daily log returns aligned by date.
    """
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1, join="inner").dropna()
    aligned.columns = ["portfolio", "benchmark"]

    excess = aligned["portfolio"] - aligned["benchmark"]
    tracking_error = float(excess.std() * np.sqrt(252))
    mean_excess = float(excess.mean() * 252)
    information_ratio = mean_excess / tracking_error if tracking_error > 0 else None

    cov = np.cov(aligned["portfolio"], aligned["benchmark"])
    beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else None

    def max_drawdown(returns_series):
        cum = np.exp(np.cumsum(returns_series))
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / peak
        return float(dd.min())

    return {
        "tracking_error": tracking_error,
        "information_ratio": information_ratio,
        "beta": beta,
        "max_drawdown_portfolio": max_drawdown(aligned["portfolio"].values),
        "max_drawdown_benchmark": max_drawdown(aligned["benchmark"].values),
    }
