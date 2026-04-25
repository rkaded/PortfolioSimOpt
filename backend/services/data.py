import os
import time
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")
TIINGO_API_KEY  = os.environ.get("TIINGO_API_KEY", "")
TIINGO_BASE     = "https://api.tiingo.com/tiingo/daily"

# Persistent HTTP client — reuses TCP/TLS connections across requests,
# eliminating per-request SSL handshake overhead (~200-400 ms each).
_HTTP = httpx.Client(timeout=15, limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))

# In-memory price cache: {(ticker, start, end): (fetched_at, pd.Series)}
# Shared across all endpoints — prevents redundant API calls within a session.
_PRICE_CACHE: dict[tuple, tuple[float, pd.Series]] = {}
CACHE_TTL = 300  # 5 minutes

CRISIS_WINDOWS = [
    ("2020-02-01", "2020-06-30", "2020 COVID drawdown"),
]


# ---------------------------------------------------------------------------
# Data sources  (priority: cache → Twelve Data → Tiingo fallback)
# ---------------------------------------------------------------------------

def _fetch_twelve_data(ticker: str, start: str, end: str) -> pd.Series | None:
    """
    Fetch daily close prices from Twelve Data using CSV format.
    CSV is ~5× smaller than JSON for the same data, reducing transfer time.
    Uses the shared persistent HTTP client to avoid per-request SSL handshakes.
    """
    if not TWELVE_DATA_KEY:
        return None

    try:
        resp = _HTTP.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol":     ticker,
                "interval":   "1day",
                "start_date": start,
                "end_date":   end,
                "format":     "CSV",          # much smaller payload than JSON
                "delimiter":  ";",
                "apikey":     TWELVE_DATA_KEY,
            },
        )

        text = resp.text.strip()
        if not text or "error" in text.lower()[:30]:
            logger.warning(f"Twelve Data {ticker}: {text[:120]}")
            return None

        df = pd.read_csv(StringIO(text), sep=";", parse_dates=["datetime"])
        if "datetime" not in df.columns or "close" not in df.columns:
            logger.warning(f"Twelve Data {ticker}: unexpected columns {df.columns.tolist()}")
            return None

        return df.set_index("datetime")["close"].rename(ticker).sort_index()

    except Exception as e:
        logger.warning(f"Twelve Data fetch failed for {ticker}: {e}")
        return None


def _fetch_tiingo(ticker: str, start: str, end: str) -> pd.Series | None:
    """Fallback: Tiingo (free tier: 50 req/hour, 1 000 req/day)."""
    if not TIINGO_API_KEY:
        return None
    try:
        resp = _HTTP.get(
            f"{TIINGO_BASE}/{ticker}/prices",
            params={"startDate": start, "endDate": end, "token": TIINGO_API_KEY},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                df = df.set_index("date").sort_index()
                col = "adjClose" if "adjClose" in df.columns else "close"
                return df[col].rename(ticker)
        else:
            logger.warning(f"Tiingo {ticker}: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"Tiingo fetch failed for {ticker}: {e}")
    return None


def _fetch_single_ticker(ticker: str, start: str, end: str) -> pd.Series | None:
    """
    Fetch price series for one ticker, with 5-minute in-memory cache.
    Source order: cache → Twelve Data → Tiingo.
    """
    cache_key = (ticker, start, end)
    now = time.monotonic()

    if cache_key in _PRICE_CACHE:
        fetched_at, series = _PRICE_CACHE[cache_key]
        if now - fetched_at < CACHE_TTL:
            return series

    series = _fetch_twelve_data(ticker, start, end)

    if series is None:
        logger.info(f"Twelve Data failed for {ticker}, trying Tiingo fallback")
        series = _fetch_tiingo(ticker, start, end)

    if series is not None:
        _PRICE_CACHE[cache_key] = (now, series)

    return series


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_prices(tickers: list[str], lookback_years: int = 5) -> tuple[pd.DataFrame, dict]:
    end   = datetime.today()
    start = end - timedelta(days=lookback_years * 365 + 30)

    tickers_list = [tickers] if isinstance(tickers, str) else list(tickers)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")

    # Fetch all tickers in parallel — total time ≈ slowest single ticker
    # rather than sum of all ticker fetch times.
    frames: dict[str, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=min(len(tickers_list), 8)) as pool:
        future_to_ticker = {
            pool.submit(_fetch_single_ticker, t, start_str, end_str): t
            for t in tickers_list
        }
        for future in as_completed(future_to_ticker):
            t = future_to_ticker[future]
            series = future.result()
            if series is not None:
                frames[t] = series

    if not frames:
        return pd.DataFrame(), {t: ["No data returned."] for t in tickers_list}

    prices = pd.DataFrame(frames).dropna(how="all")

    warnings: dict[str, list[str]] = {t: [] for t in tickers_list}

    min_required_days = lookback_years * 252 * 0.8
    actual_start      = prices.index.min()
    required_start    = end - timedelta(days=lookback_years * 365)

    for ticker in prices.columns:
        col = prices[ticker].dropna()
        if col.empty:
            warnings[ticker].append("No data available — ticker may be delisted or invalid.")
            continue

        if len(col) < min_required_days:
            warnings[ticker].append(
                f"Only {len(col)} trading days available "
                f"(< {int(min_required_days)} required for {lookback_years}yr lookback)."
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
            "std_5yr":    std_5yr_annualised,
        }
    return stats


def validate_expected_return(ticker: str, expected_return_pct: float, stats: dict) -> str | None:
    s = stats.get(ticker)
    if s is None or s.get("std_5yr") is None or s.get("return_5yr") is None:
        return None
    hist_mean = s["return_5yr"]
    hist_std  = s["std_5yr"]
    z = (expected_return_pct / 100 - hist_mean) / hist_std if hist_std > 0 else 0
    if z > 2:
        return (
            f"Your expected return assumption ({expected_return_pct:.1f}%) is significantly higher than "
            f"historical returns for {ticker} (5yr CAGR: {hist_mean*100:.1f}%, σ: {hist_std*100:.1f}%). "
            f"The optimizer will use your input — please confirm."
        )
    return None
