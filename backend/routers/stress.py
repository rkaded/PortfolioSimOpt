from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.data import fetch_prices_since, compute_stress_test, CRISIS_WINDOWS

router = APIRouter(prefix="/stress-test", tags=["stress"])

_STRESS_START = min(w[0] for w in CRISIS_WINDOWS)


class StressRequest(BaseModel):
    tickers: list[str]
    weights: dict[str, float]


@router.post("")
async def stress_test(req: StressRequest):
    if not req.tickers:
        raise HTTPException(400, "At least one ticker required.")
    if not req.weights:
        raise HTTPException(400, "Weights are required.")

    prices = fetch_prices_since(req.tickers, _STRESS_START)

    available = [t for t in req.tickers if t in prices.columns and prices[t].notna().any()]
    if not available:
        raise HTTPException(422, "No price data available for the provided tickers.")

    results = compute_stress_test(prices[available], req.weights)
    return {"periods": results}
