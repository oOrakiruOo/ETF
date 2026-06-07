from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from .utils import PROJECT_ROOT, ensure_dir


REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def load_price_data(
    tickers: list[str],
    period: str = "10y",
    interval: str = "1d",
    cache_dir: str | Path = "data/raw",
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    ensure_dir(cache_dir)
    results: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        cache_path = PROJECT_ROOT / cache_dir / f"{ticker}_{interval}.csv"
        if cache_path.exists() and not refresh:
            frame = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        else:
            frame = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
            if isinstance(frame.columns, pd.MultiIndex):
                frame.columns = frame.columns.get_level_values(0)
            frame = frame.loc[:, [column for column in REQUIRED_COLUMNS if column in frame.columns]]
            frame.to_csv(cache_path)
        if frame.empty:
            raise ValueError(f"No price data loaded for {ticker}")
        results[ticker] = frame.sort_index()
    return results


def flatten_universe(universe: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for bucket in ("core", "satellite"):
        for item in universe.get(bucket, []):
            entries.append({**item, "bucket": bucket})
    return entries
