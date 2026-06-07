from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calculate_atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = frame["High"] - frame["Low"]
    high_close = (frame["High"] - frame["Close"].shift()).abs()
    low_close = (frame["Low"] - frame["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def add_indicators(
    frame: pd.DataFrame,
    qqq_close: pd.Series | None = None,
    spy_close: pd.Series | None = None,
) -> pd.DataFrame:
    data = frame.copy()
    close = data["Adj Close"] if "Adj Close" in data.columns else data["Close"]
    data["price"] = close
    for window in (21, 50, 100, 200):
        data[f"ma_{window}"] = close.rolling(window).mean()
    data["ma_50_slope"] = data["ma_50"].diff(10) / data["ma_50"].shift(10)
    data["ma_200_slope"] = data["ma_200"].diff(20) / data["ma_200"].shift(20)
    data["return_1m"] = close.pct_change(21)
    data["return_3m"] = close.pct_change(63)
    data["return_6m"] = close.pct_change(126)
    data["return_12m"] = close.pct_change(252)
    data["rsi_14"] = calculate_rsi(close)
    data["atr_14"] = calculate_atr(data)
    data["high_52w"] = close.rolling(252).max()
    data["low_52w"] = close.rolling(252).min()
    data["drawdown_52w_pct"] = (close / data["high_52w"] - 1) * 100
    data["drawdown_20d_pct"] = (close / close.rolling(20).max() - 1) * 100
    data["drawdown_50d_pct"] = (close / close.rolling(50).max() - 1) * 100
    data["volume_20d"] = data["Volume"].rolling(20).mean()
    data["volume_change_pct"] = (data["Volume"] / data["volume_20d"] - 1) * 100
    data["up_volume_20d"] = data["Volume"].where(close.diff() > 0, 0).rolling(20).mean()
    data["down_volume_20d"] = data["Volume"].where(close.diff() < 0, 0).rolling(20).mean()
    data["three_day_return_pct"] = close.pct_change(3) * 100
    if qqq_close is not None:
        aligned = qqq_close.reindex(data.index).ffill()
        data["rs_qqq_3m"] = close.pct_change(63) - aligned.pct_change(63)
    else:
        data["rs_qqq_3m"] = np.nan
    if spy_close is not None:
        aligned = spy_close.reindex(data.index).ffill()
        data["rs_spy_3m"] = close.pct_change(63) - aligned.pct_change(63)
    else:
        data["rs_spy_3m"] = np.nan
    return data


def latest_metrics(frame: pd.DataFrame) -> dict[str, float]:
    row = frame.dropna(subset=["price"]).iloc[-1]
    return {key: float(value) for key, value in row.items() if isinstance(value, (int, float, np.floating))}
