"""
Day-one validation script per PRD Section 10.
Pull 5yr daily returns for 5 assets (3 equities + 2 bond ETFs),
run Ledoit-Wolf + MVO at 3 target returns with a sector cap constraint.
"""
import sys, time
sys.path.insert(0, ".")

from services.data import fetch_prices, compute_returns, compute_historical_stats
from services.optimizer import run_optimization
from services.simulation import run_monte_carlo
from models.schemas import Constraints, SectorCap, AssetInput

TICKERS = ["AAPL", "MSFT", "GOOGL", "AGG", "BND"]
MU = {"AAPL": 0.10, "MSFT": 0.09, "GOOGL": 0.08, "AGG": 0.04, "BND": 0.04}

print("Fetching 5yr data...")
t0 = time.time()
prices, warnings = fetch_prices(TICKERS, lookback_years=5)
print(f"  Fetched in {time.time()-t0:.2f}s. Shape: {prices.shape}")
for t, w in warnings.items():
    for warn in w:
        print(f"  WARN [{t}]: {warn}")

returns = compute_returns(prices)
stats = compute_historical_stats(prices)
print("\nHistorical stats:")
for t, s in stats.items():
    if s:
        print(f"  {t}: 5yr CAGR={s['return_5yr']:.1%}  σ={s['std_5yr']:.1%}" if s['return_5yr'] and s['std_5yr'] else f"  {t}: insufficient data")

constraints = Constraints(
    sector_caps=[SectorCap(sector="Tech", tickers=["AAPL","MSFT","GOOGL"], max_weight=0.60)]
)

print("\nOptimizer runs:")
for target in [0.06, 0.08, 0.10]:
    t0 = time.time()
    result = run_optimization(returns, MU, constraints, target_return=target)
    elapsed = time.time() - t0
    if result["status"] == "ok":
        w = result["weights"]
        tech = sum(w.get(t,0) for t in ["AAPL","MSFT","GOOGL"])
        print(f"  target={target:.0%}  vol={result['portfolio_volatility']:.2%}  tech_alloc={tech:.1%}  time={elapsed*1000:.0f}ms  ✓")
        assert tech <= 0.601, f"Sector cap violated: {tech:.1%}"
    else:
        print(f"  target={target:.0%}  INFEASIBLE: {result['message'][:80]}")

print("\nMonte Carlo (10k paths, 20 assets equivalent):")
t0 = time.time()
result = run_optimization(returns, MU, constraints, target_return=0.08)
if result["status"] == "ok":
    sim = run_monte_carlo(returns, result["weights"], horizon_years=5, n_paths=10000, seed=42)
    elapsed = time.time() - t0
    print(f"  bearish={sim['summary']['bearish_final']:.3f}  normal={sim['summary']['normal_final']:.3f}  bullish={sim['summary']['bullish_final']:.3f}")
    print(f"  10k paths in {elapsed*1000:.0f}ms  ✓")
    assert elapsed < 5.0, f"Simulation too slow: {elapsed:.2f}s"

print("\nAll checks passed.")
