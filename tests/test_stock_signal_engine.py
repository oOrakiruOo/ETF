from __future__ import annotations

import pandas as pd

from src.stock_signal_engine import evaluate_stock_signal_rule, evaluate_stock_signals, stock_signal_symbols


def _rule() -> dict[str, object]:
    return {
        "symbol": "9101.T",
        "company_name": "日本郵船",
        "signal_name": "NYK_SELL_OFF_REBOUND_CANDIDATE",
        "rule_label": "9101急落後リバウンド候補",
        "lookback_days": 10,
        "selloff_return_threshold_pct": -10.0,
        "expected_hold_days": 20,
        "confidence": "watch_only",
        "action": "monitor_only",
        "note": "10営業日-10%以上急落後の陽線。リバウンド候補だが、ETF主判断は上書きしない。",
    }


def _price_frame(active: bool = True) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=220)
    close = pd.Series(100.0, index=dates)
    open_ = pd.Series(100.0, index=dates)
    close.iloc[-11] = 100.0
    close.iloc[-1] = 88.0 if active else 94.0
    open_.iloc[-1] = 84.0
    frame = pd.DataFrame(
        {
            "Open": open_,
            "High": open_ + 2.0,
            "Low": open_ - 2.0,
            "Close": close,
            "Adj Close": close,
            "Volume": 1000000,
        }
    )
    return frame


def test_evaluate_stock_signal_rule_detects_nyk_selloff_rebound_candidate() -> None:
    result = evaluate_stock_signal_rule(_price_frame(active=True), _rule())

    assert result["symbol"] == "9101.T"
    assert result["signal_name"] == "NYK_SELL_OFF_REBOUND_CANDIDATE"
    assert result["status"] == "active"
    assert result["trigger_date"] == "2026-11-04"
    assert result["entry_watch_date"] == ""
    assert result["expected_hold_days"] == 20
    assert result["ten_day_return"] == -12.0
    assert result["bullish_candle"] is True
    assert result["confidence"] == "watch_only"
    assert result["action"] == "monitor_only"


def test_evaluate_stock_signal_rule_keeps_inactive_when_selloff_is_not_deep_enough() -> None:
    result = evaluate_stock_signal_rule(_price_frame(active=False), _rule())

    assert result["status"] == "inactive"
    assert result["trigger_date"] == ""
    assert result["ten_day_return"] == -6.0
    assert result["bullish_candle"] is True


def test_stock_signal_symbols_and_dataframe_output() -> None:
    config = {"rules": [_rule()]}

    assert stock_signal_symbols(config) == ["9101.T"]

    result = evaluate_stock_signals({"9101.T": _price_frame(active=True)}, config)
    assert list(result["symbol"]) == ["9101.T"]
    assert list(result["status"]) == ["active"]
