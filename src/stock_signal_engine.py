from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT, ensure_dir


STOCK_SIGNAL_COLUMNS = [
    "symbol",
    "company_name",
    "signal_name",
    "rule_label",
    "status",
    "trigger_date",
    "entry_watch_date",
    "expected_hold_days",
    "ten_day_return",
    "bullish_candle",
    "close_vs_200ma",
    "confidence",
    "action",
    "note",
    "data_basis",
]


def stock_signal_symbols(config: dict[str, object]) -> list[str]:
    rules = config.get("rules", [])
    if not isinstance(rules, list):
        return []
    symbols = [str(rule.get("symbol", "")).strip() for rule in rules if isinstance(rule, dict)]
    return sorted({symbol for symbol in symbols if symbol})


def _adjusted_ohlc(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    prices = frame.copy().sort_index()
    if {"Open", "Close", "Adj Close"}.issubset(prices.columns):
        close = pd.to_numeric(prices["Close"], errors="coerce")
        adj_close = pd.to_numeric(prices["Adj Close"], errors="coerce")
        factor = (adj_close / close).replace([float("inf"), -float("inf")], pd.NA).ffill()
        adjusted = pd.DataFrame(index=prices.index)
        adjusted["open"] = pd.to_numeric(prices["Open"], errors="coerce") * factor
        adjusted["close"] = adj_close
        return adjusted.dropna(subset=["open", "close"]), "adjusted"
    if {"Open", "Close"}.issubset(prices.columns):
        adjusted = pd.DataFrame(index=prices.index)
        adjusted["open"] = pd.to_numeric(prices["Open"], errors="coerce")
        adjusted["close"] = pd.to_numeric(prices["Close"], errors="coerce")
        return adjusted.dropna(subset=["open", "close"]), "unadjusted"
    return pd.DataFrame(columns=["open", "close"]), "missing"


def _next_trading_date(index: pd.Index, position: int) -> str:
    next_position = position + 1
    if next_position >= len(index):
        return ""
    return pd.Timestamp(index[next_position]).date().isoformat()


def evaluate_stock_signal_rule(frame: pd.DataFrame, rule: dict[str, object]) -> dict[str, object]:
    adjusted, data_basis = _adjusted_ohlc(frame)
    symbol = str(rule.get("symbol", ""))
    lookback = int(rule.get("lookback_days", 10) or 10)
    threshold = float(rule.get("selloff_return_threshold_pct", -10.0) or -10.0)
    latest_position = len(adjusted) - 1
    base = {
        "symbol": symbol,
        "company_name": str(rule.get("company_name", "")),
        "signal_name": str(rule.get("signal_name", "")),
        "rule_label": str(rule.get("rule_label", "")),
        "status": "inactive",
        "trigger_date": "",
        "entry_watch_date": "",
        "expected_hold_days": int(rule.get("expected_hold_days", 20) or 20),
        "ten_day_return": None,
        "bullish_candle": False,
        "close_vs_200ma": "unknown",
        "confidence": str(rule.get("confidence", "watch_only")),
        "action": str(rule.get("action", "monitor_only")),
        "note": str(rule.get("note", "")),
        "data_basis": data_basis,
    }
    if latest_position < lookback or adjusted.empty:
        return base

    latest = adjusted.iloc[latest_position]
    past_close = float(adjusted["close"].iloc[latest_position - lookback])
    current_close = float(latest["close"])
    ten_day_return = (current_close / past_close - 1.0) * 100.0
    bullish_candle = current_close > float(latest["open"])
    ma200 = adjusted["close"].rolling(200).mean().iloc[latest_position]
    if pd.isna(ma200):
        close_vs_200ma = "unknown"
    else:
        close_vs_200ma = "above" if current_close >= float(ma200) else "below"
    active = ten_day_return <= threshold and bullish_candle
    base.update(
        {
            "status": "active" if active else "inactive",
            "trigger_date": pd.Timestamp(adjusted.index[latest_position]).date().isoformat() if active else "",
            "entry_watch_date": _next_trading_date(adjusted.index, latest_position) if active else "",
            "ten_day_return": round(ten_day_return, 2),
            "bullish_candle": bool(bullish_candle),
            "close_vs_200ma": close_vs_200ma,
        }
    )
    if data_basis == "unadjusted":
        base["note"] = f"{base['note']} 非調整値で暫定計算。"
    return base


def evaluate_stock_signals(
    price_data: dict[str, pd.DataFrame],
    config: dict[str, object],
) -> pd.DataFrame:
    rules = config.get("rules", [])
    if not isinstance(rules, list):
        return pd.DataFrame(columns=STOCK_SIGNAL_COLUMNS)
    rows = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        symbol = str(rule.get("symbol", ""))
        frame = price_data.get(symbol, pd.DataFrame())
        rows.append(evaluate_stock_signal_rule(frame, rule))
    if not rows:
        return pd.DataFrame(columns=STOCK_SIGNAL_COLUMNS)
    return pd.DataFrame(rows).loc[:, STOCK_SIGNAL_COLUMNS]


def stock_signal_metadata(config: dict[str, object]) -> list[dict[str, object]]:
    rules = config.get("rules", [])
    if not isinstance(rules, list):
        return []
    metadata = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        metadata.append(
            {
                "symbol": rule.get("symbol"),
                "signal_name": rule.get("signal_name"),
                "rule_label": rule.get("rule_label"),
                "metadata": rule.get("metadata", {}),
            }
        )
    return metadata


def write_stock_signal_outputs(
    signals: pd.DataFrame,
    config: dict[str, object],
    output_dir: str | Path = "data/processed/stock_signals",
    report_date: datetime | None = None,
) -> tuple[Path, Path]:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    csv_path = PROJECT_ROOT / directory / f"stock_signals_{date:%Y-%m-%d}.csv"
    json_path = PROJECT_ROOT / directory / f"stock_signals_{date:%Y-%m-%d}.json"
    signals.to_csv(csv_path, index=False)
    payload = {
        "report_date": f"{date:%Y-%m-%d}",
        "signals": signals.to_dict("records"),
        "metadata": stock_signal_metadata(config),
        "policy": "個別株シグナルはETF主判断を上書きしない。買い推奨、売り、空売りには使わない。",
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path
