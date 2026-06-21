from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.report_engine import write_notification_report
from src.notification_engine import (
    build_notification_candidates,
    build_portfolio_notification_candidates,
    classify_notification_priority,
    count_notification_priorities,
    load_notification_outbox,
    notification_delivery_plan,
    notification_payloads,
    summarize_notification_payloads,
    write_delivery_packets,
    write_notification_outbox,
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


def test_build_notification_candidates_prioritizes_sell_action_over_buy_zone() -> None:
    table = pd.DataFrame(
        [
            {
                "ETF": "GRID",
                "判定": "売却候補",
                "ETFスコア": 74.0,
                "テーマスコア": 53.0,
                "現在価格": 100.0,
                "第1買い": 101.0,
                "保守目標": 120.0,
                "停止価格": 80.0,
                "RR": 0.8,
            }
        ]
    )
    result = build_notification_candidates(table)

    assert len(result) == 1
    assert result.iloc[0]["シグナル"] == "売却候補"
    assert result.iloc[0]["推奨行動"] == "新規買いせず保有継続可否を確認"
    assert result.iloc[0]["購入割合"] == 0.0


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


def test_write_notification_outbox_exports_jsonl(tmp_path) -> None:
    notifications = pd.DataFrame(
        [
            {
                "ETF": "SMH",
                "優先度": "High",
                "カテゴリ": "買い価格接近",
                "現在価格": 100.0,
                "シグナル": "買い候補",
                "理由": "第1買い価格に接近",
                "推奨行動": "第1買い条件を確認",
                "購入割合": 25.0,
                "目標価格": 120.0,
                "停止価格": 90.0,
                "RR": 2.2,
            }
        ]
    )
    path = write_notification_outbox(notifications, output_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert '"ticker": "SMH"' in text
    assert '"priority": "High"' in text
    assert '"category": "買い価格接近"' in text


def test_notification_payloads_returns_empty_for_no_candidates() -> None:
    assert notification_payloads(pd.DataFrame()) == []


def test_load_and_summarize_notification_outbox(tmp_path) -> None:
    notifications = pd.DataFrame(
        [
            {
                "ETF": "BBB",
                "優先度": "Medium",
                "カテゴリ": "監視強化",
                "現在価格": 100.0,
                "シグナル": "見送り",
                "理由": "ETFスコア70超え",
                "推奨行動": "監視",
                "目標価格": 120.0,
                "停止価格": 90.0,
                "RR": 1.0,
            },
            {
                "ETF": "AAA",
                "優先度": "High",
                "カテゴリ": "停止価格接近",
                "現在価格": 80.0,
                "シグナル": "売却候補",
                "理由": "停止価格に接近",
                "推奨行動": "リスク削減",
                "目標価格": 100.0,
                "停止価格": 82.0,
                "RR": 0.5,
            },
        ]
    )
    path = write_notification_outbox(notifications, output_dir=tmp_path)
    payloads = load_notification_outbox(path)
    counts = count_notification_priorities(payloads)
    summary = summarize_notification_payloads(payloads)
    assert counts.set_index("優先度").loc["High", "件数"] == 1
    assert counts.set_index("優先度").loc["Medium", "件数"] == 1
    assert summary.iloc[0]["ETF"] == "AAA"


def test_notification_delivery_plan_routes_by_priority() -> None:
    payloads = [
        {"ticker": "AAA", "priority": "High", "category": "停止価格接近", "signal": "売却候補", "action": "確認"},
        {"ticker": "BBB", "priority": "Medium", "category": "監視強化", "signal": "見送り", "action": "監視"},
        {"ticker": "CCC", "priority": "Low", "category": "参考", "signal": "押し目待ち", "action": "記録"},
    ]
    plan = notification_delivery_plan(payloads)
    by_ticker = plan.set_index("ETF")
    assert by_ticker.loc["AAA", "配送先"] == "manual_immediate"
    assert by_ticker.loc["BBB", "配送先"] == "daily_digest"
    assert by_ticker.loc["CCC", "配送先"] == "archive_only"
    assert by_ticker.loc["AAA", "承認要否"] == "必要"
    assert by_ticker.loc["CCC", "承認要否"] == "不要"


def test_write_delivery_packets_splits_by_delivery_target(tmp_path) -> None:
    payloads = [
        {
            "ticker": "AAA",
            "priority": "High",
            "category": "停止価格接近",
            "signal": "売却候補",
            "reason": "停止価格に接近",
            "action": "確認",
            "current_price": 80.0,
            "target_price": 100.0,
            "stop_price": 82.0,
            "risk_reward": 0.5,
        },
        {
            "ticker": "BBB",
            "priority": "Medium",
            "category": "監視強化",
            "signal": "見送り",
            "reason": "ETFスコア70超え",
            "action": "監視",
            "current_price": 100.0,
            "target_price": 120.0,
            "stop_price": 90.0,
            "risk_reward": 1.0,
        },
    ]
    paths = write_delivery_packets(payloads, output_dir=tmp_path, report_date=datetime(2026, 6, 8))
    by_name = {path.name: path for path in paths}
    immediate = by_name["notification_packets_manual_immediate_2026-06-08.jsonl"]
    digest = by_name["notification_packets_daily_digest_2026-06-08.jsonl"]
    archive = by_name["notification_packets_archive_only_2026-06-08.jsonl"]
    assert '"ticker": "AAA"' in immediate.read_text(encoding="utf-8")
    assert '"ticker": "BBB"' in digest.read_text(encoding="utf-8")
    assert archive.read_text(encoding="utf-8") == ""
