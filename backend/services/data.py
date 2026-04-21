import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

CRISIS_WINDOWS = [
    ("2008-09-01", "2009-06-30", "2008-09 financial crisis"),
    ("2020-02-01", "2020-06-30", "2020 COVID drawdown"),
]


def fetch_prices(tickers: list[str], lookback_years: int = 5) -> tuple[pd.DataFrame, dict]:
    """
    Fetch adjusted close prices for tickers. Returns (prices_df, warnings_dict).
    prices_df: daily adjusted closes, columns = tickers
    warnings_dict: {ticker: [warning strings]}
    """
    end = datetime.today()
    start = end - timedelta(days=lookback_years * 365 + 30)

    tickers_list = [tickers] if isinstance(tickers, str) else list(tickers)

    raw = yf.download(
        tickers_list,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="ticker",
    )

    # Normalize to a simple {ticker: close_series} DataFrame regardless of yfinance version
    frames = {}
    for t in tickers_list:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                # multi-ticker: columns are (ticker, field) or (field, ticker)
                if t in raw.columns.get_level_values(0):
                    col = raw[t]["Close"] if "Close" in raw[t].columns else raw[t].iloc[:, 0]
                elif t in raw.columns.get_level_values(1):
                    col = raw.xs(t, axis=1, level=1)["Close"]
                else:
                    continue
            else:
                # single-ticker: flat columns
                col = raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0]
            frames[t] = col
        except Exception:
            continue

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
