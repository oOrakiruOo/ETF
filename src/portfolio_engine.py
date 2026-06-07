from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT


PORTFOLIO_COLUMNS = [
    "ticker",
    "theme",
    "quantity",
    "avg_price",
    "current_price",
    "market_value",
    "weight_pct",
    "unrealized_pnl",
    "unrealized_pnl_pct",
    "entry_date",
    "thesis",
    "stop_price",
    "target_price",
    "status",
]


def load_portfolio(path: str | Path = "data/portfolio/portfolio.csv") -> pd.DataFrame:
    file_path = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not file_path.exists():
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)
    return pd.read_csv(file_path)


def update_portfolio_prices(portfolio: pd.DataFrame, prices: dict[str, float]) -> pd.DataFrame:
    updated = portfolio.copy()
    if updated.empty:
        return updated
    updated["current_price"] = updated["ticker"].map(prices).fillna(updated["current_price"])
    updated["market_value"] = updated["quantity"] * updated["current_price"]
    total_value = updated["market_value"].sum()
    updated["weight_pct"] = updated["market_value"] / total_value * 100 if total_value else 0
    updated["unrealized_pnl"] = (updated["current_price"] - updated["avg_price"]) * updated["quantity"]
    updated["unrealized_pnl_pct"] = (updated["current_price"] / updated["avg_price"] - 1) * 100
    return updated


def evaluate_portfolio_actions(portfolio: pd.DataFrame) -> pd.DataFrame:
    evaluated = portfolio.copy()
    if evaluated.empty:
        return evaluated
    actions: list[str] = []
    reasons: list[str] = []
    for row in evaluated.to_dict("records"):
        current_price = float(row.get("current_price", 0.0) or 0.0)
        avg_price = float(row.get("avg_price", 0.0) or 0.0)
        stop_price = float(row.get("stop_price", 0.0) or 0.0)
        target_price = float(row.get("target_price", 0.0) or 0.0)
        pnl_pct = float(row.get("unrealized_pnl_pct", 0.0) or 0.0)
        row_reasons: list[str] = []
        action = "保有継続"
        if stop_price > 0 and current_price <= stop_price:
            action = "停止/売却確認"
            row_reasons.append("停止価格以下")
        elif stop_price > 0 and current_price <= stop_price * 1.03:
            action = "リスク削減確認"
            row_reasons.append("停止価格3%以内")
        if target_price > 0 and current_price >= target_price:
            action = "利確確認"
            row_reasons.append("目標価格到達")
        elif pnl_pct >= 20:
            action = "部分利確確認"
            row_reasons.append("含み益20%以上")
        if avg_price > 0 and current_price <= avg_price * 0.92:
            action = "損失確認"
            row_reasons.append("平均取得単価から-8%以上")
        actions.append(action)
        reasons.append(" / ".join(row_reasons) if row_reasons else "通常監視")
    evaluated["portfolio_action"] = actions
    evaluated["portfolio_reason"] = reasons
    return evaluated
