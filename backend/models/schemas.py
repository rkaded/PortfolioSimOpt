from pydantic import BaseModel, Field
from typing import Optional


class AssetInput(BaseModel):
    ticker: str
    expected_return: Optional[float] = None  # annual %, e.g. 8.0


class LockedPosition(BaseModel):
    ticker: str
    weight: float = Field(..., ge=0.0, le=1.0)


class SectorCap(BaseModel):
    sector: str
    tickers: list[str]
    max_weight: float = Field(..., ge=0.0, le=1.0)


class AssetBound(BaseModel):
    ticker: str
    min_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    max_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class Constraints(BaseModel):
    locked_positions: list[LockedPosition] = []
    sector_caps: list[SectorCap] = []
    asset_bounds: list[AssetBound] = []
    esg_exclusions: list[str] = []


class OptimizeRequest(BaseModel):
    assets: list[AssetInput]
    constraints: Constraints = Constraints()
    target_return: float = Field(..., description="Annual target return, e.g. 0.08 for 8%")
    lookback_years: int = Field(default=5, ge=1, le=20)
    benchmark_ticker: str = Field(default="SPY")


class SimulationRequest(BaseModel):
    assets: list[AssetInput]
    weights: dict[str, float]
    horizon_years: int = Field(default=5, ge=1, le=30)
    lookback_years: int = Field(default=5, ge=1, le=20)
    benchmark_ticker: str = Field(default="SPY")
    n_paths: int = Field(default=10000, ge=1000, le=50000)
    seed: int = Field(default=42)


class AttributionRequest(BaseModel):
    assets: list[str]
    weights: dict[str, float]
    lookback_years: int = Field(default=5, ge=1, le=20)
