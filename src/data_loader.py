from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from .utils import PROJECT_ROOT


REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DATA_SOURCE_STATUS_PATH = "data/processed/data_source_status.csv"


def _read_cached_price(cache_path: Path) -> pd.DataFrame:
    return pd.read_csv(cache_path, index_col=0, parse_dates=True)


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame.loc[:, [column for column in REQUIRED_COLUMNS if column in frame.columns]]


def _write_data_source_status(rows: list[dict[str, str]], output_path: str | Path = DATA_SOURCE_STATUS_PATH) -> Path:
    path = PROJECT_ROOT / output_path
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def load_price_data(
    tickers: list[str],
    period: str = "10y",
    interval: str = "1d",
    cache_dir: str | Path = "data/raw",
    refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    cache_root = PROJECT_ROOT / cache_dir if not Path(cache_dir).is_absolute() else Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}
    source_rows: list[dict[str, str]] = []
    for ticker in tickers:
        cache_path = cache_root / f"{ticker}_{interval}.csv"
        source = "cache"
        reason = ""
        if cache_path.exists() and not refresh:
            frame = _read_cached_price(cache_path)
        else:
            try:
                frame = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
                frame = _normalize_price_frame(frame)
                if frame.empty:
                    raise ValueError("download returned empty data")
                frame.to_csv(cache_path)
                source = "download"
            except Exception as exc:
                if not cache_path.exists():
                    raise ValueError(f"No price data loaded for {ticker}") from exc
                frame = _read_cached_price(cache_path)
                source = "fallback_cache"
                reason = str(exc)
        if frame.empty:
            raise ValueError(f"No price data loaded for {ticker}")
        source_rows.append(
            {
                "ticker": ticker,
                "source": source,
                "rows": str(len(frame)),
                "last_date": str(frame.sort_index().index[-1].date()),
                "reason": reason,
            }
        )
        results[ticker] = frame.sort_index()
    _write_data_source_status(source_rows)
    return results


def flatten_universe(universe: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for bucket in ("core", "satellite"):
        for item in universe.get(bucket, []):
            entries.append({**item, "bucket": bucket})
    return entries
