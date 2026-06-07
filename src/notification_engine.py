from __future__ import annotations

import pandas as pd


def build_notification(
    ticker: str,
    current_price: float,
    signal: str,
    reason: str,
    action: str,
    allocation_pct: float,
    target_price: float,
    stop_price: float,
    risk_reward: float,
) -> str:
    return "\n".join(
        [
            f"ETF名: {ticker}",
            f"現在価格: {current_price:.2f}",
            f"シグナル: {signal}",
            f"理由: {reason}",
            f"推奨行動: {action}",
            f"購入割合: {allocation_pct:.0f}%",
            f"目標価格: {target_price:.2f}",
            f"停止価格: {stop_price:.2f}",
            f"リスクリワード: {risk_reward:.2f}",
        ]
    )


def classify_notification_priority(
    signal: str,
    current_price: float,
    first_buy: float,
    target_price: float,
    stop_price: float,
    etf_score: float,
    theme_score: float,
    allocation_pct: float,
    risk_reward: float,
) -> tuple[str, str]:
    buy_zone = first_buy > 0 and current_price <= first_buy * 1.01
    target_zone = target_price > 0 and current_price >= target_price
    stop_zone = stop_price > 0 and current_price <= stop_price * 1.02
    buy_signal = signal in {"強気買い候補", "買い候補"}
    score_event = etf_score >= 70 or theme_score >= 75 or etf_score < 60 or theme_score < 60

    if stop_zone:
        return "High", "停止価格接近"
    if target_zone:
        return "High", "目標価格到達"
    if buy_zone and risk_reward >= 2.0:
        return "High", "買い価格接近"
    if buy_signal and allocation_pct >= 25.0 and risk_reward >= 2.0:
        return "High", "買い候補"
    if buy_zone or buy_signal or score_event:
        return "Medium", "監視強化"
    return "Low", "参考"


def build_notification_candidates(signal_table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in signal_table.to_dict("records"):
        signal = str(row.get("判定", ""))
        etf_score = float(row.get("ETFスコア", 0.0))
        theme_score = float(row.get("テーマスコア", 0.0))
        current_price = float(row.get("現在価格", 0.0))
        first_buy = float(row.get("第1買い", 0.0))
        stop_price = float(row.get("停止価格", 0.0))
        target_price = float(row.get("保守目標", 0.0))
        reasons: list[str] = []
        action = "監視"
        allocation_pct = 0.0
        if signal in {"強気買い候補", "買い候補"}:
            reasons.append(f"{signal}に該当")
            action = "MASATO判断で買い検討"
            allocation_pct = 25.0
        if first_buy > 0 and current_price <= first_buy * 1.01:
            reasons.append("第1買い価格に接近")
            action = "第1買い条件を確認"
            allocation_pct = max(allocation_pct, 25.0)
        if target_price > 0 and current_price >= target_price:
            reasons.append("保守目標価格に到達")
            action = "利確候補として確認"
        if stop_price > 0 and current_price <= stop_price * 1.02:
            reasons.append("停止価格に接近")
            action = "リスク削減または停止を確認"
        if etf_score >= 70:
            reasons.append("ETFスコア70超え")
        if etf_score < 60:
            reasons.append("ETFスコア60割れ")
        if theme_score >= 75:
            reasons.append("テーマスコア75超え")
        if theme_score < 60:
            reasons.append("テーマスコア60割れ")
        if reasons:
            priority, category = classify_notification_priority(
                signal,
                current_price,
                first_buy,
                target_price,
                stop_price,
                etf_score,
                theme_score,
                allocation_pct,
                float(row.get("RR", 0.0)),
            )
            rows.append(
                {
                    "ETF": row.get("ETF", ""),
                    "優先度": priority,
                    "カテゴリ": category,
                    "現在価格": current_price,
                    "シグナル": signal,
                    "理由": " / ".join(reasons),
                    "推奨行動": action,
                    "購入割合": allocation_pct,
                    "目標価格": target_price,
                    "停止価格": stop_price,
                    "RR": float(row.get("RR", 0.0)),
                }
            )
    return pd.DataFrame(rows)


def build_portfolio_notification_candidates(portfolio: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if portfolio.empty or "portfolio_action" not in portfolio.columns:
        return pd.DataFrame(rows)
    for row in portfolio.to_dict("records"):
        action = str(row.get("portfolio_action", ""))
        if action in {"保有継続", ""}:
            continue
        rows.append(
            {
                "ETF": row.get("ticker", ""),
                "優先度": "High",
                "カテゴリ": "保有リスク確認",
                "現在価格": float(row.get("current_price", 0.0) or 0.0),
                "シグナル": action,
                "理由": row.get("portfolio_reason", ""),
                "推奨行動": "MASATO判断で保有方針を確認",
                "購入割合": 0.0,
                "目標価格": float(row.get("target_price", 0.0) or 0.0),
                "停止価格": float(row.get("stop_price", 0.0) or 0.0),
                "RR": 0.0,
            }
        )
    return pd.DataFrame(rows)
