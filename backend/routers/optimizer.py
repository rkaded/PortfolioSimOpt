from fastapi import APIRouter, HTTPException
from services.data import fetch_prices, compute_returns
from services.optimizer import run_optimization, compute_efficient_frontier
from models.schemas import OptimizeRequest

router = APIRouter(prefix="/optimize", tags=["optimizer"])


@router.post("")
async def optimize(req: OptimizeRequest):
    all_tickers = [a.ticker for a in req.assets]
    if len(all_tickers) < 2:
        raise HTTPException(400, "At least 2 assets required.")

    expected_returns_map = {
        a.ticker: a.expected_return / 100
        for a in req.assets
        if a.expected_return is not None
    }
    missing = [a.ticker for a in req.assets if a.expected_return is None]
    if missing:
        raise HTTPException(400, f"Expected return missing for: {', '.join(missing)}")

    prices, _ = fetch_prices(all_tickers, req.lookback_years)
    available = [t for t in all_tickers if t in prices.columns]
    if len(available) < 2:
        raise HTTPException(422, "Insufficient price data for optimization.")

    returns = compute_returns(prices[available])
    mu = {t: expected_returns_map.get(t, 0.0) for t in available}

    result = run_optimization(returns, mu, req.constraints, req.target_return)
    frontier = compute_efficient_frontier(returns, mu, req.constraints)

    result["efficient_frontier"] = frontier
    return result
