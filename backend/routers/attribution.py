from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from services.data import fetch_prices
from services.attribution import compute_return_attribution
from models.schemas import AttributionRequest
import io
import csv

router = APIRouter(prefix="/attribution", tags=["attribution"])


@router.post("")
async def attribution(req: AttributionRequest):
    if not req.assets:
        raise HTTPException(400, "No assets provided.")

    prices, _ = fetch_prices(req.assets, req.lookback_years)
    available = [t for t in req.assets if t in prices.columns]
    if not available:
        raise HTTPException(422, "No price data available.")

    weights = {t: req.weights.get(t, 0.0) for t in available}
    total = sum(weights.values())
    if total > 0:
        weights = {t: w / total for t, w in weights.items()}

    return compute_return_attribution(prices[available], weights, period="M")


@router.post("/export")
async def export_attribution(req: AttributionRequest):
    prices, _ = fetch_prices(req.assets, req.lookback_years)
    available = [t for t in req.assets if t in prices.columns]
    weights = {t: req.weights.get(t, 0.0) for t in available}
    total = sum(weights.values())
    if total > 0:
        weights = {t: w / total for t, w in weights.items()}

    result = compute_return_attribution(prices[available], weights, period="M")

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["Date", "Portfolio Return"] + available
    writer.writerow(header)
    for period in result["periods"]:
        row = [period["date"], f"{period['portfolio_return']*100:.4f}%"]
        for t in available:
            c = period["contributions"].get(t, 0.0)
            row.append(f"{c*100:.4f}%")
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attribution.csv"},
    )
