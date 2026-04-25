import os
import time
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import yfinance as yf
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
    ("2000-03-01", "2002-10-31", "Dot-com crash (2000–02)"),
    ("2007-10-01", "2009-03-31", "Global Financial Crisis (2007–09)"),
    ("2011-07-01", "2011-10-31", "2011 US debt-ceiling selloff"),
    ("2018-10-01", "2018-12-31", "Q4 2018 rate-hike selloff"),
    ("2020-02-01", "2020-06-30", "COVID-19 crash (2020)"),
    ("2022-01-01", "2022-12-31", "2022 rate-hike bear market"),
]


# ---------------------------------------------------------------------------
# Data sources  (priority: cache → yfinance batch → Twelve Data → Tiingo)
# ---------------------------------------------------------------------------

def _fetch_yfinance_batch(tickers: list[str], start: str, end: str) -> dict[str, pd.Series]:
    """
    Batch-download all tickers in a single yfinance call.

    yfinance fetches every ticker in one HTTP round-trip, so total time is
    roughly the same as fetching one ticker.  No API key required; prices are
    split/dividend adjusted automatically.

    Returns a dict {ticker: pd.Series} for every ticker with data.
    Tickers that return no data are omitted — callers should fall back.
    """
    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            progress=False,
            auto_adjust=True,
            threads=True,
        )
        if raw.empty:
            return {}

        # Multi-ticker download → MultiIndex columns (field, ticker).
        # Single-ticker download → flat columns (field names only).
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            # Flatten: rename the single "Close" column to the ticker symbol
            close = raw[["Close"]].rename(columns={"Close": tickers[0]})

        # yfinance returns tz-aware DatetimeIndex — strip tz for consistency
        if close.index.tz is not None:
            close.index = close.index.tz_localize(None)

        result = {}
        for ticker in close.columns:
            s = close[ticker].dropna()
            if not s.empty:
                result[str(ticker)] = s.rename(str(ticker))
        return result

    except Exception as e:
        logger.warning(f"yfinance batch failed for {tickers}: {e}")
        return {}


def _fetch_twelve_data(ticker: str, start: str, end: str) -> pd.Series | None:
    """
    Fallback: Twelve Data CSV format.
    CSV is ~5× smaller than JSON for the same data, reducing transfer time.
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
                "format":     "CSV",
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


def _fetch_single_fallback(ticker: str, start: str, end: str) -> pd.Series | None:
    """Per-ticker fallback chain when yfinance returns nothing for that ticker."""
    series = _fetch_twelve_data(ticker, start, end)
    if series is None:
        logger.info(f"Twelve Data failed for {ticker}, trying Tiingo")
        series = _fetch_tiingo(ticker, start, end)
    return series


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_prices_since(tickers: list[str], start_str: str) -> pd.DataFrame:
    """
    Fetch prices from a fixed start date to today, using the shared cache.
    Returns a raw price DataFrame with no warnings — for stress test use only.
    """
    end_str = datetime.today().strftime("%Y-%m-%d")
    now = time.monotonic()

    tickers_list = list(tickers)
    frames: dict[str, pd.Series] = {}
    to_fetch: list[str] = []

    for t in tickers_list:
        key = (t, start_str, end_str)
        if key in _PRICE_CACHE:
            fetched_at, series = _PRICE_CACHE[key]
            if now - fetched_at < CACHE_TTL:
                frames[t] = series
                continue
        to_fetch.append(t)

    if to_fetch:
        batch = _fetch_yfinance_batch(to_fetch, start_str, end_str)
        for t in list(to_fetch):
            if t in batch:
                frames[t] = batch[t]
                _PRICE_CACHE[(t, start_str, end_str)] = (now, batch[t])
                to_fetch.remove(t)

        if to_fetch:
            with ThreadPoolExecutor(max_workers=min(len(to_fetch), 8)) as pool:
                future_map = {pool.submit(_fetch_single_fallback, t, start_str, end_str): t for t in to_fetch}
                for future in as_completed(future_map):
                    t = future_map[future]
                    series = future.result()
                    if series is not None:
                        frames[t] = series
                        _PRICE_CACHE[(t, start_str, end_str)] = (now, series)

    if not frames:
        return pd.DataFrame()

    return pd.DataFrame(frames).ffill().dropna(how="all")


def fetch_prices(tickers: list[str], lookback_years: int = 5) -> tuple[pd.DataFrame, dict]:
    end   = datetime.today()
    start = end - timedelta(days=lookback_years * 365 + 30)

    tickers_list = [tickers] if isinstance(tickers, str) else list(tickers)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")
    now = time.monotonic()

    # ── Step 1: serve warm-cache hits immediately ──────────────────────────
    frames: dict[str, pd.Series] = {}
    to_fetch: list[str] = []

    for t in tickers_list:
        key = (t, start_str, end_str)
        if key in _PRICE_CACHE:
            fetched_at, series = _PRICE_CACHE[key]
            if now - fetched_at < CACHE_TTL:
                frames[t] = series
                continue
        to_fetch.append(t)

    # ── Step 2: batch-download all uncached tickers in one yfinance call ───
    if to_fetch:
        batch = _fetch_yfinance_batch(to_fetch, start_str, end_str)

        # Cache hits from batch
        for t in list(to_fetch):
            if t in batch:
                frames[t] = batch[t]
                _PRICE_CACHE[(t, start_str, end_str)] = (now, batch[t])
                to_fetch.remove(t)

        # ── Step 3: parallel fallback for any tickers yfinance missed ──────
        if to_fetch:
            logger.info(f"yfinance missed {to_fetch}, trying fallbacks in parallel")
            with ThreadPoolExecutor(max_workers=min(len(to_fetch), 8)) as pool:
                future_map = {
                    pool.submit(_fetch_single_fallback, t, start_str, end_str): t
                    for t in to_fetch
                }
                for future in as_completed(future_map):
                    t = future_map[future]
                    series = future.result()
                    if series is not None:
                        frames[t] = series
                        _PRICE_CACHE[(t, start_str, end_str)] = (now, series)

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


    prices = prices.ffill().dropna(how="all")
    return prices, warnings


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns."""
    return np.log(prices / prices.shift(1)).dropna()


def compute_stress_test(prices: pd.DataFrame, weights: dict[str, float]) -> list[dict]:
    """
    For each CRISIS_WINDOW, compute the weighted portfolio return over that period.
    Prices that don't cover the full window are included with the data that exists.
    """
    results = []
    weight_series = pd.Series(weights)

    for crisis_start, crisis_end, label in CRISIS_WINDOWS:
        cs = pd.Timestamp(crisis_start)
        ce = pd.Timestamp(crisis_end)

        available = [t for t in weight_series.index if t in prices.columns]
        if not available:
            continue

        window = prices[available].loc[cs:ce].dropna(how="all")
        if len(window) < 5:
            results.append({
                "label": label,
                "start": crisis_start,
                "end": crisis_end,
                "portfolio_return": None,
                "asset_returns": {},
                "note": "Insufficient data for this period",
            })
            continue

        # Total return for each asset over the window (first→last available price)
        first = window.iloc[0]
        last  = window.iloc[-1]
        asset_returns = ((last - first) / first).to_dict()

        # Renormalise weights to available assets
        w = weight_series.reindex(available).fillna(0.0)
        w = w / w.sum() if w.sum() > 0 else w

        portfolio_return = float((pd.Series(asset_returns) * w).sum())

        results.append({
            "label": label,
            "start": crisis_start,
            "end": crisis_end,
            "portfolio_return": round(portfolio_return, 6),
            "asset_returns": {k: round(v, 6) for k, v in asset_returns.items()},
            "note": None,
        })

    return results


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
