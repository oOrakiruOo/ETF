from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT, ensure_dir


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


def notification_payloads(notifications: pd.DataFrame, created_at: datetime | None = None) -> list[dict[str, object]]:
    if notifications.empty:
        return []
    timestamp = (created_at or datetime.now()).isoformat(timespec="seconds")
    payloads: list[dict[str, object]] = []
    for row in notifications.to_dict("records"):
        payloads.append(
            {
                "created_at": timestamp,
                "ticker": row.get("ETF", ""),
                "priority": row.get("優先度", ""),
                "category": row.get("カテゴリ", ""),
                "signal": row.get("シグナル", ""),
                "reason": row.get("理由", ""),
                "action": row.get("推奨行動", ""),
                "current_price": row.get("現在価格", 0.0),
                "target_price": row.get("目標価格", 0.0),
                "stop_price": row.get("停止価格", 0.0),
                "risk_reward": row.get("RR", 0.0),
            }
        )
    return payloads


def write_notification_outbox(
    notifications: pd.DataFrame,
    output_dir: str | Path = "data/processed/notifications",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"notification_outbox_{date:%Y-%m-%d}.jsonl"
    payloads = notification_payloads(notifications, created_at=date)
    lines = [json.dumps(payload, ensure_ascii=False) for payload in payloads]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def load_notification_outbox(path: str | Path) -> list[dict[str, object]]:
    file_path = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not file_path.exists():
        return []
    payloads: list[dict[str, object]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payloads.append(json.loads(line))
    return payloads


def summarize_notification_payloads(payloads: list[dict[str, object]], top_n: int = 10) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    sorted_payloads = sorted(
        payloads,
        key=lambda payload: (
            priority_order.get(str(payload.get("priority", "")), 9),
            str(payload.get("ticker", "")),
        ),
    )
    for payload in sorted_payloads[:top_n]:
        rows.append(
            {
                "優先度": payload.get("priority", ""),
                "ETF": payload.get("ticker", ""),
                "カテゴリ": payload.get("category", ""),
                "シグナル": payload.get("signal", ""),
                "理由": payload.get("reason", ""),
                "推奨行動": payload.get("action", ""),
            }
        )
    return pd.DataFrame(rows)


def notification_delivery_plan(payloads: list[dict[str, object]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for payload in payloads:
        priority = str(payload.get("priority", ""))
        if priority == "High":
            channel = "manual_immediate"
            timing = "当日すぐ確認"
            requires_approval = True
        elif priority == "Medium":
            channel = "daily_digest"
            timing = "日次確認"
            requires_approval = True
        else:
            channel = "archive_only"
            timing = "記録のみ"
            requires_approval = False
        rows.append(
            {
                "優先度": priority,
                "ETF": payload.get("ticker", ""),
                "配送先": channel,
                "確認タイミング": timing,
                "承認要否": "必要" if requires_approval else "不要",
                "カテゴリ": payload.get("category", ""),
                "シグナル": payload.get("signal", ""),
                "推奨行動": payload.get("action", ""),
            }
        )
    return pd.DataFrame(rows)


def count_notification_priorities(payloads: list[dict[str, object]]) -> pd.DataFrame:
    counts: dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
    for payload in payloads:
        priority = str(payload.get("priority", ""))
        counts[priority] = counts.get(priority, 0) + 1
    return pd.DataFrame([{"優先度": priority, "件数": count} for priority, count in counts.items() if count > 0])
