"""
Tests for geometric → arithmetic expected-return adjustment.

Core identity:  arithmetic_μ = geometric_μ + σ² / 2
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest
from services.optimizer import geometric_to_arithmetic


# ── helpers ────────────────────────────────────────────────────────────────

def make_returns(vol_annual: float, n: int = 1260, seed: int = 0) -> pd.Series:
    """Synthetic daily return series with a controlled annualised volatility."""
    rng = np.random.default_rng(seed)
    daily_vol = vol_annual / np.sqrt(252)
    return pd.Series(rng.normal(0, daily_vol, n))


# ── unit tests: geometric_to_arithmetic ───────────────────────────────────

def test_formula_low_vol():
    """20 % vol → adjustment ≈ σ²/2 = 0.02 (2 pp)."""
    vol = 0.20
    returns = pd.DataFrame({"A": make_returns(vol)})
    mu_geo  = pd.Series({"A": 0.10})

    mu_arith, adj = geometric_to_arithmetic(mu_geo, returns)

    expected_bump = 0.5 * vol ** 2          # = 0.02
    actual_bump   = float(mu_arith["A"] - mu_geo["A"])

    assert abs(actual_bump - expected_bump) < 0.005, (
        f"Low-vol bump {actual_bump:.4f} too far from expected {expected_bump:.4f}"
    )
    assert adj["A"]["adjustment_pct"] == round(actual_bump * 100, 3)


def test_formula_high_vol():
    """40 % vol (NVDA-like) → adjustment ≈ 0.08 (8 pp). Gap is significant."""
    vol = 0.40
    returns = pd.DataFrame({"NVDA": make_returns(vol)})
    mu_geo  = pd.Series({"NVDA": 0.10})

    mu_arith, adj = geometric_to_arithmetic(mu_geo, returns)

    expected_bump = 0.5 * vol ** 2          # = 0.08
    actual_bump   = float(mu_arith["NVDA"] - mu_geo["NVDA"])

    assert abs(actual_bump - expected_bump) < 0.010, (
        f"High-vol bump {actual_bump:.4f} too far from expected {expected_bump:.4f}"
    )


def test_zero_vol_no_adjustment():
    """Constant returns → zero variance → no adjustment."""
    returns = pd.DataFrame({"BOND": pd.Series([0.0001] * 500)})
    mu_geo  = pd.Series({"BOND": 0.05})

    mu_arith, adj = geometric_to_arithmetic(mu_geo, returns)

    assert abs(float(mu_arith["BOND"]) - 0.05) < 1e-6, "Zero-vol asset must not be adjusted"
    assert adj["BOND"]["adjustment_pct"] == pytest.approx(0.0, abs=1e-4)


def test_arithmetic_always_gte_geometric():
    """Arithmetic mean ≥ geometric mean for any non-negative variance."""
    for i, vol in enumerate([0.05, 0.15, 0.25, 0.40, 0.60]):
        returns = pd.DataFrame({"X": make_returns(vol, seed=i + 1)})
        mu_geo  = pd.Series({"X": 0.08})
        mu_arith, _ = geometric_to_arithmetic(mu_geo, returns)
        assert float(mu_arith["X"]) >= float(mu_geo["X"]) - 1e-9, (
            f"Arithmetic mean < geometric at vol={vol}"
        )


def test_multi_ticker():
    """Each ticker gets its own σ²/2, independent of the others."""
    returns = pd.DataFrame({
        "LOW_VOL":  make_returns(0.10, seed=1),
        "HIGH_VOL": make_returns(0.50, seed=2),
    })
    mu_geo = pd.Series({"LOW_VOL": 0.06, "HIGH_VOL": 0.06})

    mu_arith, adj = geometric_to_arithmetic(mu_geo, returns)

    low_bump  = adj["LOW_VOL"]["adjustment_pct"]
    high_bump = adj["HIGH_VOL"]["adjustment_pct"]

    assert high_bump > low_bump, "Higher-vol asset must receive a larger bump"
    assert low_bump  > 0
    assert high_bump > 0


def test_adj_map_fields():
    """adj_map must contain input_pct, adjusted_pct, adjustment_pct for every ticker."""
    returns = pd.DataFrame({"A": make_returns(0.20), "B": make_returns(0.30)})
    mu_geo  = pd.Series({"A": 0.08, "B": 0.12})

    _, adj = geometric_to_arithmetic(mu_geo, returns)

    for ticker in ["A", "B"]:
        assert "input_pct"      in adj[ticker]
        assert "adjusted_pct"   in adj[ticker]
        assert "adjustment_pct" in adj[ticker]
        assert adj[ticker]["adjusted_pct"] == pytest.approx(
            adj[ticker]["input_pct"] + adj[ticker]["adjustment_pct"], abs=0.001
        )


# ── integration: optimizer uses arithmetic mu, not geometric ──────────────

def test_optimizer_uses_arithmetic_mu():
    """
    Key behavioural test: set the target return strictly above all geometric
    means but within the arithmetic reach of the high-vol asset.

    Asset A: vol=10%, geometric μ=8%  → arithmetic μ ≈ 8.5%
    Asset B: vol=40%, geometric μ=8%  → arithmetic μ ≈ 16%

    target = 10%  (above both geometric means → infeasible without adjustment,
                   reachable via B's arithmetic μ → feasible with adjustment)

    If the optimizer returns "ok" it must be using arithmetic mu.
    If it returned "infeasible" we'd know it's incorrectly using geometric mu.
    """
    from services.optimizer import run_optimization
    from models.schemas import Constraints

    rng = np.random.default_rng(99)
    n   = 1260

    low_vol_daily  = 0.10 / np.sqrt(252)   # A: ~10% annualised vol
    high_vol_daily = 0.40 / np.sqrt(252)   # B: ~40% annualised vol

    returns = pd.DataFrame({
        "A": rng.normal(0, low_vol_daily,  n),
        "B": rng.normal(0, high_vol_daily, n),
    })

    mu_inputs   = {"A": 0.08, "B": 0.08}   # equal geometric returns (8%)
    constraints = Constraints()
    target      = 0.10                      # 10%: above geometric, within B's arithmetic

    result = run_optimization(returns, mu_inputs, constraints, target)

    # Must be feasible — only possible if arithmetic mu is used
    assert result["status"] == "ok", (
        "Target=10% is above both geometric means (8%) but within B's arithmetic "
        f"mu (~16%). Getting 'infeasible' means geometric mu is being used. Got: {result}"
    )

    # B must carry meaningful weight to hit 10%: theory gives w_B ≈ 20%
    # (w_B×16% + w_A×8.5% = 10% → w_B ≈ 20%). Tolerance: >12%.
    assert result["weights"]["B"] > 0.12, (
        f"Expected B to carry >12% weight to hit 10% target via its arithmetic mu, "
        f"got {result['weights']['B']:.2%}"
    )

    # Sanity check: adj_map is present and B's bump is larger than A's
    assert "mu_adjustments" in result
    assert result["mu_adjustments"]["B"]["adjustment_pct"] > result["mu_adjustments"]["A"]["adjustment_pct"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
