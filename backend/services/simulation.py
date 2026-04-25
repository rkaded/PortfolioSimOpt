import numpy as np
import pandas as pd
from pypfopt import risk_models

# Downsampling stride — we return ~monthly chart points instead of daily.
# 21 trading days ≈ 1 calendar month.
# 5yr → 60 points, 10yr → 120 points (vs 1 260 / 2 520 daily points before).
CHART_STRIDE = 21


def run_monte_carlo(
    returns: pd.DataFrame,
    weights: dict[str, float],
    horizon_years: int = 5,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict:
    """
    Parametric Monte Carlo — fast univariate portfolio sampling.

    Key optimisation: instead of sampling from the full multivariate normal
    and then collapsing with weights (old approach), we collapse the moments
    first and sample a scalar portfolio return directly:

        port_return_t  ~  N(wᵀμ,  √(wᵀΣw))

    This is mathematically identical (linear combination of MVN is normal)
    but ~20× faster — no Cholesky decomposition, no matrix multiply, no
    batch loop needed.

    Output is downsampled to monthly intervals (~21 trading days) so the
    JSON payload and chart rendering are fast regardless of horizon.
    """
    tickers = [t for t in weights if t in returns.columns]
    w = np.array([weights[t] for t in tickers])
    ret = returns[[t for t in tickers if t in returns.columns]].dropna()

    mu_daily  = ret.mean().values
    cov_daily = (
        risk_models.CovarianceShrinkage(ret, returns_data=True, frequency=252)
        .ledoit_wolf().values / 252
    )

    # Scalar portfolio moments — collapse before sampling, not after
    port_mu    = float(w @ mu_daily)
    port_sigma = float(np.sqrt(w @ cov_daily @ w))

    trading_days = horizon_years * 252
    rng = np.random.default_rng(seed)

    # Single vectorised draw — (n_paths, trading_days) of scalars
    # Peak RAM: 1 000 × 2 520 × 8 B ≈ 20 MB even for 10-year horizon
    port_daily = rng.normal(port_mu, port_sigma, size=(n_paths, trading_days))
    cum_paths  = np.exp(np.cumsum(port_daily, axis=1))   # (n_paths, trading_days)

    # Downsample to monthly for chart output
    chart_paths = cum_paths[:, CHART_STRIDE - 1 :: CHART_STRIDE]  # (n_paths, n_months)

    p25 = np.percentile(chart_paths, 25, axis=0)
    p50 = np.percentile(chart_paths, 50, axis=0)
    p75 = np.percentile(chart_paths, 75, axis=0)

    final         = cum_paths[:, -1]
    annual_returns = final ** (1 / horizon_years) - 1

    return {
        "bearish":       p25.tolist(),
        "normal":        p50.tolist(),
        "bullish":       p75.tolist(),
        "n_months":      int(chart_paths.shape[1]),   # frontend uses this for x-axis
        "trading_days":  trading_days,                # kept for reference
        "horizon_years": horizon_years,
        "n_paths":       n_paths,
        "summary": {
            "bearish_final":          float(p25[-1]),
            "normal_final":           float(p50[-1]),
            "bullish_final":          float(p75[-1]),
            "annualised_return_p25":  float(np.percentile(annual_returns, 25)),
            "annualised_return_p50":  float(np.percentile(annual_returns, 50)),
            "annualised_return_p75":  float(np.percentile(annual_returns, 75)),
        },
    }


def run_benchmark_simulation(
    benchmark_returns: pd.Series,
    horizon_years: int = 5,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict:
    """Univariate benchmark Monte Carlo, monthly-downsampled output."""
    mu           = float(benchmark_returns.mean())
    sigma        = float(benchmark_returns.std())
    trading_days = horizon_years * 252
    rng          = np.random.default_rng(seed + 1)

    draws     = rng.normal(mu, sigma, size=(n_paths, trading_days))
    cum       = np.exp(np.cumsum(draws, axis=1))
    chart_cum = cum[:, CHART_STRIDE - 1 :: CHART_STRIDE]

    return {
        "normal":        np.percentile(chart_cum, 50, axis=0).tolist(),
        "trading_days":  trading_days,
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

    excess           = aligned["portfolio"] - aligned["benchmark"]
    tracking_error   = float(excess.std() * np.sqrt(252))
    mean_excess      = float(excess.mean() * 252)
    information_ratio = mean_excess / tracking_error if tracking_error > 0 else None

    cov  = np.cov(aligned["portfolio"], aligned["benchmark"])
    beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else None

    def max_drawdown(r):
        cum  = np.exp(np.cumsum(r))
        peak = np.maximum.accumulate(cum)
        return float(((cum - peak) / peak).min())

    return {
        "tracking_error":          tracking_error,
        "information_ratio":       information_ratio,
        "beta":                    beta,
        "max_drawdown_portfolio":  max_drawdown(aligned["portfolio"].values),
        "max_drawdown_benchmark":  max_drawdown(aligned["benchmark"].values),
    }
