from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.data import compute_stress_test

router = APIRouter(prefix="/stress-test", tags=["stress"])


class StressRequest(BaseModel):
    tickers: list[str]
    weights: dict[str, float]


@router.post("")
async def stress_test(req: StressRequest):
    if not req.tickers:
        raise HTTPException(400, "At least one ticker required.")
    if not req.weights:
        raise HTTPException(400, "Weights are required.")

    results = compute_stress_test(req.tickers, req.weights)
    return {"periods": results}
