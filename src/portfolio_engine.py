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
    "currency",
    "manual_value_jpy",
    "asset_class",
    "signal_scope",
    "source_note",
]

PORTFOLIO_NUMERIC_COLUMNS = [
    "quantity",
    "avg_price",
    "current_price",
    "stop_price",
    "target_price",
    "manual_value_jpy",
]

PORTFOLIO_REQUIRED_COLUMNS = ["ticker", "quantity", "avg_price"]
ETF_MAX_WEIGHT_PCT = 10.0
THEME_MAX_WEIGHT_PCT = 15.0


def normalize_portfolio_columns(portfolio: pd.DataFrame) -> pd.DataFrame:
    normalized = portfolio.copy()
    for column in PORTFOLIO_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    return normalized.loc[:, PORTFOLIO_COLUMNS]


def load_portfolio(path: str | Path = "data/portfolio/portfolio.csv") -> pd.DataFrame:
    file_path = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not file_path.exists():
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)
    return normalize_portfolio_columns(pd.read_csv(file_path))


def validate_portfolio(portfolio: pd.DataFrame) -> pd.DataFrame:
    issues: list[dict[str, object]] = []
    if portfolio.empty:
        return pd.DataFrame(
            [{"severity": "Info", "ticker": "", "column": "", "message": "保有CSVは空です"}]
        )

    for column in PORTFOLIO_REQUIRED_COLUMNS:
        if column not in portfolio.columns:
            issues.append(
                {
                    "severity": "Error",
                    "ticker": "",
                    "column": column,
                    "message": "必須列がありません",
                }
            )
    if issues:
        return pd.DataFrame(issues)

    frame = portfolio.copy()
    frame["ticker"] = frame["ticker"].fillna("").astype(str).str.strip().str.upper()
    for row_number, row in frame.iterrows():
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            issues.append(
                {
                    "severity": "Error",
                    "ticker": "",
                    "column": "ticker",
                    "message": f"{row_number + 2}行目のtickerが空です",
                }
            )
        for column in PORTFOLIO_NUMERIC_COLUMNS:
            if column not in frame.columns:
                continue
            value = row.get(column, "")
            if pd.isna(value) or value == "":
                if column in {"stop_price", "target_price"}:
                    issues.append(
                        {
                            "severity": "Warning",
                            "ticker": ticker,
                            "column": column,
                            "message": "停止価格または目標価格が未入力です",
                        }
                    )
                continue
            numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(numeric_value):
                issues.append(
                    {
                        "severity": "Error",
                        "ticker": ticker,
                        "column": column,
                        "message": "数値として読めません",
                    }
                )
            elif column in {"quantity", "avg_price"} and float(numeric_value) <= 0:
                issues.append(
                    {
                        "severity": "Error",
                        "ticker": ticker,
                        "column": column,
                        "message": "0より大きい値が必要です",
                    }
                )

    duplicated = frame[frame["ticker"].ne("") & frame["ticker"].duplicated(keep=False)]
    for ticker in sorted(set(duplicated["ticker"].tolist())):
        issues.append(
            {
                "severity": "Warning",
                "ticker": ticker,
                "column": "ticker",
                "message": "同じtickerが複数行あります",
            }
        )

    if "weight_pct" in frame.columns:
        frame["weight_pct"] = pd.to_numeric(frame["weight_pct"], errors="coerce")
        for row in frame.to_dict("records"):
            weight_pct = row.get("weight_pct")
            if pd.notna(weight_pct) and float(weight_pct) > ETF_MAX_WEIGHT_PCT:
                issues.append(
                    {
                        "severity": "Warning",
                        "ticker": row.get("ticker", ""),
                        "column": "weight_pct",
                        "message": f"ETF単体比率が{ETF_MAX_WEIGHT_PCT:.0f}%を超えています",
                    }
                )
        if "theme" in frame.columns:
            theme_weights = frame.dropna(subset=["weight_pct"]).groupby("theme", dropna=False)["weight_pct"].sum()
            for theme, weight_pct in theme_weights.items():
                if float(weight_pct) > THEME_MAX_WEIGHT_PCT:
                    issues.append(
                        {
                            "severity": "Warning",
                            "ticker": "",
                            "column": "theme",
                            "message": f"{theme}テーマ比率が{THEME_MAX_WEIGHT_PCT:.0f}%を超えています",
                        }
                    )

    if not issues:
        issues.append(
            {
                "severity": "OK",
                "ticker": "",
                "column": "",
                "message": "保有CSVの基本チェックはOKです",
            }
        )
    return pd.DataFrame(issues)


def update_portfolio_prices(portfolio: pd.DataFrame, prices: dict[str, float]) -> pd.DataFrame:
    updated = normalize_portfolio_columns(portfolio)
    if updated.empty:
        return updated
    updated["ticker"] = updated["ticker"].fillna("").astype(str).str.strip().str.upper()
    for column in ["quantity", "avg_price", "current_price", "stop_price", "target_price"]:
        updated[column] = pd.to_numeric(updated[column], errors="coerce")
    manual_value = pd.to_numeric(updated["manual_value_jpy"], errors="coerce")
    has_manual_value = manual_value.notna() & (manual_value > 0)
    mapped_prices = updated["ticker"].map(prices)
    updated["current_price"] = mapped_prices.where(~has_manual_value, updated["current_price"])
    updated["current_price"] = updated["current_price"].fillna(mapped_prices)
    updated["market_value"] = updated["quantity"] * updated["current_price"]
    updated.loc[has_manual_value, "market_value"] = manual_value[has_manual_value]
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
