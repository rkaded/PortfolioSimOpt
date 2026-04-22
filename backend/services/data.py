import os
import time
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

TIINGO_API_KEY = os.environ.get("TIINGO_API_KEY", "")
TIINGO_BASE = "https://api.tiingo.com/tiingo/daily"

# In-memory price cache: {(ticker, start_date, end_date): (fetched_at, pd.Series)}
# Reusing cached data across all endpoints prevents redundant Tiingo API calls
# and avoids rate-limit (429) errors when multiple endpoints are hit in quick succession.
_PRICE_CACHE: dict[tuple, tuple[float, pd.Series]] = {}
CACHE_TTL = 300  # seconds — prices are stale after 5 minutes


def _fetch_single_ticker(ticker: str, start: str, end: str) -> pd.Series | None:
    """Fetch one ticker from Tiingo, with a 5-minute in-memory cache."""
    cache_key = (ticker, start, end)
    now = time.monotonic()

    if cache_key in _PRICE_CACHE:
        fetched_at, series = _PRICE_CACHE[cache_key]
        if now - fetched_at < CACHE_TTL:
            logger.debug(f"Cache hit for {ticker}")
            return series

    try:
        url = f"{TIINGO_BASE}/{ticker}/prices"
        params = {"startDate": start, "endDate": end, "token": TIINGO_API_KEY}
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                df = df.set_index("date").sort_index()
                col = "adjClose" if "adjClose" in df.columns else "close"
                series = df[col]
                _PRICE_CACHE[cache_key] = (now, series)
                return series
        else:
            logger.warning(f"Tiingo {ticker}: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Tiingo fetch failed for {ticker}: {e}")

    return None

CRISIS_WINDOWS = [
    ("2020-02-01", "2020-06-30", "2020 COVID drawdown"),
]


def fetch_prices(tickers: list[str], lookback_years: int = 5) -> tuple[pd.DataFrame, dict]:
    end = datetime.today()
    start = end - timedelta(days=lookback_years * 365 + 30)

    tickers_list = [tickers] if isinstance(tickers, str) else list(tickers)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    frames = {}
    for t in tickers_list:
        series = _fetch_single_ticker(t, start_str, end_str)
        if series is not None:
            frames[t] = series

    if not frames:
        return pd.DataFrame(), {t: ["No data returned."] for t in tickers_list}

    prices = pd.DataFrame(frames).dropna(how="all")

    warnings: dict[str, list[str]] = {t: [] for t in tickers_list}

    min_required_days = lookback_years * 252 * 0.8
    actual_start = prices.index.min()
    required_start = end - timedelta(days=lookback_years * 365)

    for ticker in prices.columns:
        col = prices[ticker].dropna()
        if col.empty:
            warnings[ticker].append("No data available — ticker may be delisted or invalid.")
            continue

        if len(col) < min_required_days:
            warnings[ticker].append(
                f"Only {len(col)} trading days available (< {int(min_required_days)} required for {lookback_years}yr lookback)."
            )

        if actual_start > required_start + timedelta(days=60):
            warnings[ticker].append(
                f"Data starts {actual_start.date()} — less than {lookback_years} years of history."
            )

        for crisis_start, crisis_end, label in CRISIS_WINDOWS:
            cs = pd.Timestamp(crisis_start)
            ce = pd.Timestamp(crisis_end)
            window = col.loc[cs:ce] if cs >= col.index.min() else pd.Series(dtype=float)
            if len(window) < 20:
                warnings[ticker].append(f"Lookback window excludes {label}.")

    prices = prices.ffill().dropna(how="all")
    return prices, warnings


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns."""
    return np.log(prices / prices.shift(1)).dropna()


def compute_historical_stats(prices: pd.DataFrame) -> dict:
    """
    Returns {ticker: {return_1yr, return_3yr, return_5yr, std_5yr}} annualised.
    """
    stats = {}
    today = prices.index.max()
    for ticker in prices.columns:
        col = prices[ticker].dropna()
        if len(col) < 10:
            stats[ticker] = None
            continue

        def cagr(series, years):
            start_idx = today - pd.DateOffset(years=years)
            sub = series.loc[start_idx:]
            if len(sub) < 20:
                return None
            return float((sub.iloc[-1] / sub.iloc[0]) ** (1 / years) - 1)

        daily_ret = col.pct_change().dropna()
        std_5yr_annualised = float(daily_ret.std() * np.sqrt(252)) if len(daily_ret) >= 252 else None

        stats[ticker] = {
            "return_1yr": cagr(col, 1),
            "return_3yr": cagr(col, 3),
            "return_5yr": cagr(col, 5),
            "std_5yr": std_5yr_annualised,
        }
    return stats


def validate_expected_return(ticker: str, expected_return_pct: float, stats: dict) -> str | None:
    """
    Returns a warning string if expected_return is > 2 SD from historical distribution, else None.
    expected_return_pct: e.g. 8.0 for 8%
    """
    s = stats.get(ticker)
    if s is None or s.get("std_5yr") is None or s.get("return_5yr") is None:
        return None
    hist_mean = s["return_5yr"]
    hist_std = s["std_5yr"]
    z = (expected_return_pct / 100 - hist_mean) / hist_std if hist_std > 0 else 0
    if z > 2:
        return (
            f"Your expected return assumption ({expected_return_pct:.1f}%) is significantly higher than "
            f"historical returns for {ticker} (5yr CAGR: {hist_mean*100:.1f}%, σ: {hist_std*100:.1f}%). "
            f"The optimizer will use your input — please confirm."
        )
    return None
