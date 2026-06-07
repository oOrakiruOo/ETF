from __future__ import annotations

import pandas as pd

from src.report_engine import write_notification_report
from src.notification_engine import (
    build_notification_candidates,
    build_portfolio_notification_candidates,
    classify_notification_priority,
)


def test_build_notification_candidates_flags_buy_and_score_events() -> None:
    table = pd.DataFrame(
        [
            {
                "ETF": "SMH",
                "判定": "買い候補",
                "ETFスコア": 72.0,
                "テーマスコア": 80.0,
                "現在価格": 100.0,
                "第1買い": 101.0,
                "保守目標": 120.0,
                "停止価格": 90.0,
                "RR": 2.2,
            }
        ]
    )
    result = build_notification_candidates(table)
    assert len(result) == 1
    assert result.iloc[0]["ETF"] == "SMH"
    assert "買い候補" in result.iloc[0]["理由"]
    assert result.iloc[0]["優先度"] == "High"
    assert result.iloc[0]["カテゴリ"] == "買い価格接近"


def test_build_portfolio_notification_candidates_flags_non_hold_actions() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "ticker": "SMH",
                "current_price": 80.0,
                "portfolio_action": "停止/売却確認",
                "portfolio_reason": "停止価格以下",
                "target_price": 120.0,
                "stop_price": 82.0,
            }
        ]
    )
    result = build_portfolio_notification_candidates(portfolio)
    assert len(result) == 1
    assert result.iloc[0]["シグナル"] == "停止/売却確認"
    assert result.iloc[0]["優先度"] == "High"


def test_classify_notification_priority_marks_score_only_as_medium() -> None:
    priority, category = classify_notification_priority(
        signal="見送り",
        current_price=100.0,
        first_buy=90.0,
        target_price=120.0,
        stop_price=80.0,
        etf_score=72.0,
        theme_score=65.0,
        allocation_pct=0.0,
        risk_reward=1.0,
    )
    assert priority == "Medium"
    assert category == "監視強化"


def test_write_notification_report_groups_by_priority(tmp_path) -> None:
    notifications = pd.DataFrame(
        [
            {
                "ETF": "AAA",
                "優先度": "Medium",
                "カテゴリ": "監視強化",
                "現在価格": 100.0,
                "シグナル": "見送り",
                "理由": "ETFスコア70超え",
                "推奨行動": "監視",
                "購入割合": 0.0,
                "目標価格": 120.0,
                "停止価格": 90.0,
                "RR": 1.0,
            },
            {
                "ETF": "BBB",
                "優先度": "High",
                "カテゴリ": "停止価格接近",
                "現在価格": 80.0,
                "シグナル": "売却候補",
                "理由": "停止価格に接近",
                "推奨行動": "リスク削減",
                "購入割合": 0.0,
                "目標価格": 100.0,
                "停止価格": 82.0,
                "RR": 0.5,
            },
        ]
    )
    path = write_notification_report(notifications, output_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "## High: 今日すぐ確認" in text
    assert "## Medium: 監視強化" in text
    assert text.index("BBB") < text.index("AAA")
