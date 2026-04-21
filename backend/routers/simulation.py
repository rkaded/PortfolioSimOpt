from fastapi import APIRouter, HTTPException
from services.data import fetch_prices, compute_returns
from services.simulation import run_monte_carlo, run_benchmark_simulation, compute_benchmark_metrics
from models.schemas import SimulationRequest

router = APIRouter(prefix="/simulate", tags=["simulation"])


@router.post("")
async def simulate(req: SimulationRequest):
    all_tickers = list(req.weights.keys())
    if not all_tickers:
        raise HTTPException(400, "No weights provided.")

    weight_sum = sum(req.weights.values())
    if abs(weight_sum - 1.0) > 0.02:
        raise HTTPException(400, f"Weights must sum to 1.0 (got {weight_sum:.4f}).")

    fetch_tickers = list(set(all_tickers + [req.benchmark_ticker]))
    prices, _ = fetch_prices(fetch_tickers, req.lookback_years)

    port_tickers = [t for t in all_tickers if t in prices.columns]
    if not port_tickers:
        raise HTTPException(422, "No price data available for portfolio assets.")

    returns = compute_returns(prices)

    port_sim = run_monte_carlo(
        returns,
        {t: req.weights[t] for t in port_tickers},
        req.horizon_years,
        req.n_paths,
        req.seed,
    )

    bench_data = {}
    benchmark_metrics = {}
    if req.benchmark_ticker in returns.columns:
        bench_sim = run_benchmark_simulation(
            returns[req.benchmark_ticker],
            req.horizon_years,
            req.n_paths,
            req.seed,
        )
        bench_data = {"benchmark_path": bench_sim["normal"]}

        port_daily = returns[port_tickers].dropna().multiply(
            [req.weights.get(t, 0) for t in port_tickers], axis=1
        ).sum(axis=1)
        benchmark_metrics = compute_benchmark_metrics(port_daily, returns[req.benchmark_ticker])

    return {
        **port_sim,
        **bench_data,
        "benchmark_metrics": benchmark_metrics,
        "disclosure": {
            "fat_tail": "Parametric simulation assumes normally distributed returns. Actual crash scenarios may be more severe.",
            "long_only": "This tool assumes long-only positions. Short positions and derivatives are not supported.",
            "not_advice": "Quantitative analysis only — not investment advice.",
        },
    }
