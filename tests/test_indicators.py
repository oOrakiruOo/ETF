from __future__ import annotations

import pandas as pd

from src.indicators import add_indicators, calculate_rsi


def test_calculate_rsi_stays_between_zero_and_hundred() -> None:
    close = pd.Series([100, 101, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 113, 114])
    rsi = calculate_rsi(close).dropna()
    assert not rsi.empty
    assert float(rsi.min()) >= 0
    assert float(rsi.max()) <= 100


def test_add_indicators_adds_expected_columns() -> None:
    dates = pd.date_range("2024-01-01", periods=260)
    frame = pd.DataFrame(
        {
            "Open": range(100, 360),
            "High": range(101, 361),
            "Low": range(99, 359),
            "Close": range(100, 360),
            "Adj Close": range(100, 360),
            "Volume": [1_000_000] * 260,
        },
        index=dates,
    )
    data = add_indicators(frame)
    assert "ma_200" in data.columns
    assert "return_12m" in data.columns
    assert "drawdown_52w_pct" in data.columns
    assert float(data.iloc[-1]["ma_200"]) > 0
