import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.exceptions import OptimizationError
from models.schemas import Constraints


class InfeasibleError(Exception):
    def __init__(self, message: str, binding_constraint: str, violation: float | None = None):
        super().__init__(message)
        self.binding_constraint = binding_constraint
        self.violation = violation


def build_optimizer(
    returns: pd.DataFrame,
    mu: pd.Series,
    constraints: Constraints,
    target_return: float,
) -> tuple[EfficientFrontier, list[str], np.ndarray]:
    """
    Returns (ef, free_tickers, locked_weights_array).
    Preprocesses locked positions, builds EF on free assets.
    """
    all_tickers = list(returns.columns)
    excluded = set(constraints.esg_exclusions)
    locked_map = {lp.ticker: lp.weight for lp in constraints.locked_positions}

    free_tickers = [
        t for t in all_tickers
        if t not in locked_map and t not in excluded
    ]

    if not free_tickers:
        raise InfeasibleError(
            "All assets are locked or excluded — nothing to optimise.",
            binding_constraint="locked_positions/esg_exclusions",
        )

    locked_total = sum(locked_map.get(t, 0) for t in all_tickers if t in locked_map)
    if locked_total >= 1.0:
        raise InfeasibleError(
            f"Locked positions sum to {locked_total*100:.1f}% ≥ 100% — no allocation remaining for free assets.",
            binding_constraint="locked_positions",
            violation=locked_total - 1.0,
        )

    residual = 1.0 - locked_total
    free_returns = returns[free_tickers].dropna()
    free_mu = mu[free_tickers] * residual

    cov_full = risk_models.CovarianceShrinkage(free_returns, returns_data=True).ledoit_wolf()
    cov_scaled = cov_full * (residual ** 2)

    lower_bounds = {}
    upper_bounds = {}
    for ab in constraints.asset_bounds:
        if ab.ticker in free_tickers:
            lower_bounds[ab.ticker] = ab.min_weight * residual
            upper_bounds[ab.ticker] = ab.max_weight * residual

    weight_bounds = [
        (lower_bounds.get(t, 0.0), upper_bounds.get(t, 1.0))
        for t in free_tickers
    ]

    ef = EfficientFrontier(free_mu, cov_scaled, weight_bounds=weight_bounds)

    for sc in constraints.sector_caps:
        sector_free = [t for t in sc.tickers if t in free_tickers]
        if sector_free:
            sector_max = sc.max_weight * residual
            ef.add_constraint(lambda w, tickers=sector_free, mx=sector_max: sum(w[free_tickers.index(t)] for t in tickers) <= mx)

    return ef, free_tickers, locked_map, residual


def run_optimization(
    returns: pd.DataFrame,
    mu_inputs: dict[str, float],
    constraints: Constraints,
    target_return: float,
) -> dict:
    """
    Run MVO. Returns dict with weights, risk metrics, and infeasibility details if applicable.
    mu_inputs: {ticker: annual_return_decimal}, e.g. {"AAPL": 0.08}
    target_return: annual, e.g. 0.08
    """
    mu_series = pd.Series(mu_inputs, index=returns.columns).reindex(returns.columns).fillna(0.0)

    try:
        ef, free_tickers, locked_map, residual = build_optimizer(returns, mu_series, constraints, target_return)
        adjusted_target = target_return * residual if residual < 1.0 else target_return

        try:
            ef.efficient_return(adjusted_target)
        except (OptimizationError, ValueError) as oe:
            _diagnose_infeasibility(constraints, free_tickers, mu_series, target_return, residual, str(oe))

        raw_weights = ef.clean_weights()
        perf = ef.portfolio_performance(verbose=False)

        final_weights = {}
        for t, w in locked_map.items():
            final_weights[t] = w
        for t in free_tickers:
            final_weights[t] = raw_weights.get(t, 0.0)

        weight_sum = sum(final_weights.values())
        if abs(weight_sum - 1.0) > 0.01:
            final_weights = {t: v / weight_sum for t, v in final_weights.items()}

        return {
            "status": "ok",
            "weights": final_weights,
            "portfolio_volatility": float(perf[1]),
            "portfolio_expected_return": float(perf[0]) / residual if residual < 1.0 else float(perf[0]),
            "sharpe_ratio": float(perf[2]) if perf[2] is not None else None,
        }

    except InfeasibleError as ie:
        return {
            "status": "infeasible",
            "binding_constraint": ie.binding_constraint,
            "violation": ie.violation,
            "message": str(ie),
        }


def _diagnose_infeasibility(constraints, free_tickers, mu_series, target_return, residual, opt_msg):
    max_achievable = float(mu_series[free_tickers].mean()) if free_tickers else 0.0
    if "lower than the maximum" in opt_msg or target_return * residual > max_achievable:
        violation = target_return * residual - max_achievable
        raise InfeasibleError(
            f"Target return {target_return*100:.1f}% is not achievable given current constraints. "
            f"Maximum achievable expected return is ~{max_achievable/residual*100:.1f}%.",
            binding_constraint="target_return",
            violation=violation,
        )

    for ab in constraints.asset_bounds:
        if ab.ticker in free_tickers and ab.min_weight > ab.max_weight:
            raise InfeasibleError(
                f"Asset bound infeasible for {ab.ticker}: min {ab.min_weight*100:.0f}% > max {ab.max_weight*100:.0f}%.",
                binding_constraint=f"asset_bounds:{ab.ticker}",
            )

    for sc in constraints.sector_caps:
        sector_free = [t for t in sc.tickers if t in free_tickers]
        if sector_free:
            min_sector = sum(
                next((ab.min_weight for ab in constraints.asset_bounds if ab.ticker == t), 0.0)
                for t in sector_free
            )
            if min_sector > sc.max_weight:
                raise InfeasibleError(
                    f"Sector '{sc.sector}' minimum weights ({min_sector*100:.0f}%) exceed sector cap ({sc.max_weight*100:.0f}%). "
                    f"Reduce asset floor constraints or raise the sector cap.",
                    binding_constraint=f"sector_cap:{sc.sector}",
                    violation=min_sector - sc.max_weight,
                )

    raise InfeasibleError(
        f"Optimizer could not find a feasible solution. {opt_msg}",
        binding_constraint="constraints_combination",
    )


def compute_efficient_frontier(
    returns: pd.DataFrame,
    mu_inputs: dict[str, float],
    constraints: Constraints,
    n_points: int = 50,
) -> list[dict]:
    """Returns list of {expected_return, volatility} points on the efficient frontier."""
    mu_series = pd.Series(mu_inputs, index=returns.columns).reindex(returns.columns).fillna(0.0)

    try:
        _, free_tickers, locked_map, residual = build_optimizer(returns, mu_series, constraints, 0.0)
    except InfeasibleError:
        return []

    free_returns = returns[free_tickers].dropna()
    free_mu = mu_series[free_tickers] * residual
    cov = risk_models.CovarianceShrinkage(free_returns, returns_data=True).ledoit_wolf() * (residual ** 2)

    mu_min = float(free_mu.min())
    mu_max = float(free_mu.max())
    targets = np.linspace(mu_min * 1.01, mu_max * 0.99, n_points)

    points = []
    for t in targets:
        try:
            ef = EfficientFrontier(free_mu, cov)
            ef.efficient_return(t)
            perf = ef.portfolio_performance(verbose=False)
            points.append({"expected_return": float(perf[0]) / residual, "volatility": float(perf[1])})
        except Exception:
            continue

    return points
