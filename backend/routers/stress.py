from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.data import compute_stress_test, CRISIS_WINDOWS
import yfinance as yf
import pandas as pd
from datetime import datetime

router = APIRouter(prefix="/stress-test", tags=["stress"])

# Earliest crisis window start — fetch from here regardless of portfolio lookback
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

    end_str = datetime.today().strftime("%Y-%m-%d")
    try:
        raw = yf.download(
            req.tickers,
            start=_STRESS_START,
            end=end_str,
            progress=False,
            auto_adjust=True,
            threads=True,
        )
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch price data: {e}")

    if raw.empty:
        raise HTTPException(422, "No price data available for the provided tickers.")

    # Normalise to DataFrame of Close prices regardless of single/multi ticker
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw.iloc[:, 0]
    else:
        prices = raw[["Close"]] if "Close" in raw.columns else raw

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=req.tickers[0])

    # Keep only tickers that have at least some data
    available = [t for t in req.tickers if t in prices.columns and prices[t].notna().any()]
    if not available:
        raise HTTPException(422, "No usable price data for the provided tickers.")

    results = compute_stress_test(prices[available], req.weights)
    return {"periods": results}
