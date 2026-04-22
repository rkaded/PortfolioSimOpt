import numpy as np
import pandas as pd


def compute_return_attribution(
    prices: pd.DataFrame,
    weights: dict[str, float],
    period: str = "M",
) -> dict:
    """
    Return contribution analysis: contribution_i,t = weight_i * return_i,t
    period: 'D' daily, 'W' weekly, 'M' monthly
    Returns period-level attribution and summary of top/bottom contributors.
    """
    tickers = [t for t in weights if t in prices.columns]
    w = np.array([weights[t] for t in tickers])

    p = prices[tickers].dropna()
    periodic = p.resample("ME").last().pct_change().dropna()

    contributions = periodic.multiply(w, axis=1)
    portfolio_return = contributions.sum(axis=1)

    periods_list = []
    for date, row in contributions.iterrows():
        port_ret = float(portfolio_return[date])
        asset_contribs = {t: float(row[t]) for t in tickers}
        sorted_contribs = sorted(asset_contribs.items(), key=lambda x: x[1], reverse=True)
        periods_list.append({
            "date": date.strftime("%Y-%m-%d"),
            "portfolio_return": port_ret,
            "contributions": asset_contribs,
            "top_contributors": [{"ticker": t, "contribution": c} for t, c in sorted_contribs[:3] if c > 0],
            "detractors": [{"ticker": t, "contribution": c} for t, c in sorted_contribs[::-1][:3] if c < 0],
        })

    total_contrib = contributions.sum(axis=0)
    overall_summary = sorted(
        [{"ticker": t, "total_contribution": float(total_contrib[t])} for t in tickers],
        key=lambda x: x["total_contribution"],
        reverse=True,
    )

    return {
        "periods": periods_list,
        "overall_summary": overall_summary,
        "period_type": period,
    }


def compute_correlation_matrix(returns: pd.DataFrame) -> dict:
    """
    Returns correlation matrix as {tickers: [...], matrix: [[...]]}.
    Uses Pearson correlation from Ledoit-Wolf covariance.
    """
    from pypfopt import risk_models

    ret = returns.dropna()
    tickers = list(ret.columns)

    try:
        cov = risk_models.CovarianceShrinkage(ret, returns_data=True).ledoit_wolf()
        std = np.sqrt(np.diag(cov.values))
        corr_matrix = cov.values / np.outer(std, std)
        np.fill_diagonal(corr_matrix, 1.0)
    except Exception:
        corr_matrix = ret.corr().values

    return {
        "tickers": tickers,
        "matrix": np.round(corr_matrix, 4).tolist(),
    }
