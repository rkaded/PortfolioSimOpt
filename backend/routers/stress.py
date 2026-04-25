from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.data import fetch_prices, compute_stress_test

router = APIRouter(prefix="/stress-test", tags=["stress"])


class StressRequest(BaseModel):
    tickers: list[str]
    weights: dict[str, float]
    lookback_years: int = 10


@router.post("")
async def stress_test(req: StressRequest):
    if not req.tickers:
        raise HTTPException(400, "At least one ticker required.")
    if not req.weights:
        raise HTTPException(400, "Weights are required.")

    # Fetch enough history to cover all crisis windows (earliest is 2000)
    prices, _ = fetch_prices(req.tickers, lookback_years=max(req.lookback_years, 25))
    available = [t for t in req.tickers if t in prices.columns]
    if not available:
        raise HTTPException(422, "No price data available for the provided tickers.")

    results = compute_stress_test(prices[available], req.weights)
    return {"periods": results}
