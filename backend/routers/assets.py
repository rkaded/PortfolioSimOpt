from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.data import fetch_prices, compute_returns, compute_historical_stats, validate_expected_return
from services.attribution import compute_correlation_matrix
from models.schemas import AssetInput
from datetime import datetime

router = APIRouter(prefix="/assets", tags=["assets"])


class FetchRequest(BaseModel):
    tickers: list[str]
    lookback_years: int = 5
    expected_returns: dict[str, float] = {}


@router.post("/fetch")
async def fetch_assets(req: FetchRequest):
    if not req.tickers:
        raise HTTPException(400, "At least one ticker required.")
    if len(req.tickers) > 30:
        raise HTTPException(400, "Maximum 30 tickers per request.")

    prices, data_warnings = fetch_prices(req.tickers, req.lookback_years)
    if prices.empty:
        raise HTTPException(422, "No price data returned. Check ticker symbols.")

    stats = compute_historical_stats(prices)

    return_warnings: dict[str, str | None] = {}
    for ticker, er in req.expected_returns.items():
        return_warnings[ticker] = validate_expected_return(ticker, er, stats)

    return {
        "tickers": list(prices.columns),
        "data_last_updated": datetime.now().isoformat(),
        "lookback_years": req.lookback_years,
        "stats": stats,
        "data_warnings": data_warnings,
        "return_warnings": {k: v for k, v in return_warnings.items() if v},
    }


class CorrelationRequest(BaseModel):
    tickers: list[str]
    lookback_years: int = 5


@router.post("/correlation")
async def get_correlation(req: CorrelationRequest):
    prices, _ = fetch_prices(req.tickers, req.lookback_years)
    if prices.empty:
        raise HTTPException(422, "No price data available.")
    returns = compute_returns(prices)
    return compute_correlation_matrix(returns[req.tickers] if all(t in returns.columns for t in req.tickers) else returns)
