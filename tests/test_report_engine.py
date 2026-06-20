from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.report_engine import (
    build_signal_table,
    write_daily_report,
    write_decision_brief,
    write_daily_health_report,
    write_go_live_readiness_report,
    write_manual_decision_sheet,
    write_mobile_summary,
    write_notification_delivery_plan_report,
    write_notification_summary_report,
    write_portfolio_check_report,
    write_replay_pdca_report,
    write_weekly_health_report,
    write_weekly_pdca_report,
)


def test_write_daily_report_shows_compact_score_ranking(tmp_path) -> None:
    signal_table = build_signal_table(
        [
            {
                "ETF": "SMH",
                "テーマ": "半導体",
                "ETFスコア": 80.0,
                "テーマスコア": 75.0,
                "テーマリスク": "低",
                "テーマリスクスコア": 0,
                "ステージ": "ステージ3: 加速期",
                "現在価格": 100.0,
                "第1買い": 95.0,
                "第1買いまで%": -5.0,
                "第2買い": 90.0,
                "第3買い": 85.0,
                "保守目標": 115.0,
                "強気目標": 125.0,
                "停止価格": 80.0,
                "RR": 1.5,
                "判定": "買い候補",
                "テーマリスク理由": "大きな警戒なし",
                "テーマ予防策": "通常ルールで監視",
            }
        ]
    )
    output_path = write_daily_report(
        signal_table,
        {"半導体": 75.0},
        output_dir=tmp_path,
        report_date=datetime(2026, 6, 18),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "## 4. ETFスコアランキング 要約" in text
    assert "## 4b. ETFスコアランキング 詳細" in text
    summary_text = text.split("## 4b. ETFスコアランキング 詳細")[0]
    assert "テーマリスク理由" not in summary_text


def test_write_mobile_summary_outputs_phone_friendly_ranking(tmp_path) -> None:
    signal_table = build_signal_table(
        [
            {
                "ETF": "VGT",
                "テーマ": "AI",
                "ETFスコア": 84.43,
                "テーマスコア": 67.39,
                "テーマリスク": "中",
                "テーマリスクスコア": 1,
                "ステージ": "加速期",
                "現在価格": 116.74,
                "第1買い": 116.74,
                "第1買いまで%": 0.0,
                "第2買い": 110.0,
                "第3買い": 105.0,
                "保守目標": 125.0,
                "強気目標": 130.0,
                "停止価格": 108.0,
                "RR": 0.87,
                "判定": "見送り",
                "テーマリスク理由": "過熱注意",
                "テーマ予防策": "監視",
            }
        ]
    )
    output_path = write_mobile_summary(
        signal_table,
        readiness=pd.DataFrame([{"判定項目": "日次ヘルス", "状態": "OK", "理由": "OK"}]),
        manual_decision_summary=pd.DataFrame(
            [
                {
                    "対象件数": 1,
                    "判断済み件数": 1,
                    "未判断件数": 0,
                    "状態": "OK",
                }
            ]
        ),
        output_dir=tmp_path,
        report_date=datetime(2026, 6, 18),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "ETF Rotation 2026-06-18" in text
    assert "GO/HOLD: GO（手動確認後）" in text
    assert "手動判断: OK 対象1 判断済1 未判断0" in text
    assert "1. VGT ETF84.43 テーマ67.39 見送り RR0.87 リスク中" in text


def test_write_decision_brief_focuses_on_buy_timing(tmp_path) -> None:
    signal_table = build_signal_table(
        [
            {
                "ETF": "VT",
                "テーマ": "Global",
                "ETFスコア": 61.0,
                "テーマスコア": 60.0,
                "テーマリスク": "低",
                "テーマリスクスコア": 0,
                "ステージ": "ステージ4: 過熱期",
                "現在価格": 100.0,
                "第1買い": 98.0,
                "第1買いまで%": -2.0,
                "第2買い": 95.0,
                "第3買い": 90.0,
                "保守目標": 110.0,
                "強気目標": 120.0,
                "停止価格": 85.0,
                "RR": 0.8,
                "判定": "見送り",
                "テーマリスク理由": "",
                "テーマ予防策": "",
            },
            {
                "ETF": "SMH",
                "テーマ": "半導体",
                "ETFスコア": 72.0,
                "テーマスコア": 79.0,
                "テーマリスク": "低",
                "テーマリスクスコア": 0,
                "ステージ": "ステージ4: 過熱期",
                "現在価格": 200.0,
                "第1買い": 190.0,
                "第1買いまで%": -5.0,
                "第2買い": 180.0,
                "第3買い": 170.0,
                "保守目標": 230.0,
                "強気目標": 250.0,
                "停止価格": 160.0,
                "RR": 0.5,
                "判定": "利確候補",
                "テーマリスク理由": "",
                "テーマ予防策": "",
            },
        ]
    )
    output_path = write_decision_brief(
        signal_table,
        readiness=pd.DataFrame([{"判定項目": "LINE設定", "状態": "OK", "理由": "OK"}]),
        output_dir=tmp_path,
        report_date=datetime(2026, 6, 19),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "ETF Rotation Daily 2026-06-19" in text
    assert "市場スコア" in text
    assert "/100" in text
    assert "🟣 CHECK SELL" in text
    assert "今日は新規買いより、保有ETFの確認を優先。" in text
    assert "今日やること:" in text
    assert "✅ SMHの保有状況だけ確認" in text
    assert "❌ 新規買いは見送り" in text
    assert "❌ ナンピン禁止" in text
    assert "新規買い: なし" in text
    assert "コア買い: 待ち" in text
    assert "サテライト買い: 待ち" in text
    assert "利確/売却確認: あり" in text
    assert "監視候補:" in text
    assert "VT  買い条件まで中距離" in text
    assert "買いシグナル発生まで" in text
    assert "中距離（目安3〜12日）" in text
    assert "VT/VTI/SPY/QQQは待ち。" in text
    assert "テーマETFの新規買い候補なし。" in text
    assert "状態: 過熱" in text
    assert "確認: 利確候補" in text
    assert "買い増ししない。保有継続/一部利確を手動確認。" in text
    assert "※これは投資助言ではありません。" in text


def test_replay_report_action_items_use_min_score_for_hybrid_thresholds(tmp_path) -> None:
    hybrid_grid = pd.DataFrame(
        [
            {
                "candidate_policy": "watch_score_gate",
                "acceleration_overlay_mode": "normal",
                "signal_overlay_weight_pct": 15.0,
                "entry_multiplier": 1.04,
                "stop_multiplier": 0.95,
                "max_holding_days": 40,
                "max_signal_positions": 2,
                "min_score": 70.0,
                "min_rr": 1.0,
                "annual_return_pct": 17.32,
                "cumulative_return_pct": 393.72,
                "max_drawdown_pct": -19.28,
                "sharpe_ratio": 1.08,
                "trade_count": 132,
                "signal_entry_count": 4,
                "signal_exit_count": 4,
                "avg_signal_trade_return_pct": 11.24,
                "risk_adjusted_rank_score": 26.90,
            }
        ]
    )
    output_path = write_replay_pdca_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        hybrid_grid=hybrid_grid,
        output_dir=tmp_path,
        processed_output_dir=tmp_path / "processed",
        report_date=datetime(2026, 6, 7),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "ETF70+ テーマ70+ RR1.0+" in text
    assert "ETF0+ テーマ0+" not in text


def test_replay_report_action_items_show_relaxed_hybrid_tickers(tmp_path) -> None:
    hybrid_ticker_rule_results = pd.DataFrame(
        [
            {
                "rule_name": "block_URA",
                "annual_return_pct": 17.76,
                "ura_signal_trade_count": 0,
                "relaxed_signal_tickers": "SMH,SOXX",
                "relaxed_min_etf_score": 65.0,
                "relaxed_min_theme_score": 65.0,
                "relaxed_min_rr": 1.0,
            }
        ]
    )
    output_path = write_replay_pdca_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        hybrid_ticker_rule_results=hybrid_ticker_rule_results,
        output_dir=tmp_path,
        processed_output_dir=tmp_path / "processed",
        report_date=datetime(2026, 6, 7),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "限定緩和SMH,SOXX ETF65+ テーマ65+ RR1.0+" in text


def test_weekly_report_writes_action_item_tracker(tmp_path) -> None:
    report_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"
    parameter_results = pd.DataFrame(
        [
            {
                "satellite_weight_pct": 35.0,
                "top_satellites": 4,
                "drawdown_stop_pct": -15.0,
                "score_profile": "balanced",
            }
        ]
    )

    output_path = write_weekly_pdca_report(
        pd.DataFrame(),
        parameter_results,
        pd.DataFrame(),
        signal_improvement_proposals=["フォワード評価を翌週も確認"],
        output_dir=report_dir,
        processed_output_dir=processed_dir,
        report_date=datetime(2026, 6, 15),
    )

    text = output_path.read_text(encoding="utf-8")
    tracker_path = processed_dir / "weekly_action_items_2026-06-15.csv"
    tracker = pd.read_csv(tracker_path)
    assert "Act項目CSV" in text
    assert set(tracker["status"]) == {"open"}
    assert len(tracker) == 3
    assert "フォワード評価を翌週も確認" in tracker["action_item"].tolist()


def test_weekly_report_shows_manual_decision_summary(tmp_path) -> None:
    output_path = write_weekly_pdca_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        manual_decision_summary=pd.DataFrame(
            [
                {
                    "対象件数": 2,
                    "判断済み件数": 1,
                    "未判断件数": 1,
                    "buy件数": 1,
                    "sell件数": 0,
                    "hold件数": 0,
                    "watch件数": 0,
                    "約定件数": 1,
                    "一部約定件数": 0,
                    "未約定件数": 0,
                    "要確認件数": 1,
                    "状態": "要確認",
                    "理由": "未判断1件",
                }
            ]
        ),
        output_dir=tmp_path,
        processed_output_dir=tmp_path / "processed",
        report_date=datetime(2026, 6, 15),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "### 手動判断ログ" in text
    assert "buy件数" in text
    assert "要確認" in text


def test_weekly_report_shows_previous_open_action_items(tmp_path) -> None:
    report_dir = tmp_path / "reports"
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    previous = pd.DataFrame(
        [
            {
                "report_date": "2026-06-08",
                "item_id": 1,
                "status": "open",
                "source": "weekly_pdca",
                "action_item": "半導体の取り逃がしを確認",
            },
            {
                "report_date": "2026-06-08",
                "item_id": 2,
                "status": "done",
                "source": "weekly_pdca",
                "action_item": "完了済み項目",
            },
        ]
    )
    previous.to_csv(processed_dir / "weekly_action_items_2026-06-08.csv", index=False)

    output_path = write_weekly_pdca_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        signal_improvement_proposals=["次週も確認"],
        output_dir=report_dir,
        processed_output_dir=processed_dir,
        report_date=datetime(2026, 6, 15),
    )

    text = output_path.read_text(encoding="utf-8")
    assert "## 前回Act確認" in text
    assert "半導体の取り逃がしを確認" in text
    assert "完了済み項目" not in text


def test_write_portfolio_check_report_marks_errors(tmp_path) -> None:
    issues = pd.DataFrame(
        [
            {
                "severity": "Error",
                "ticker": "SMH",
                "column": "quantity",
                "message": "数値として読めません",
            }
        ]
    )
    output_path = write_portfolio_check_report(issues, output_dir=tmp_path, report_date=datetime(2026, 6, 8))
    text = output_path.read_text(encoding="utf-8")
    assert "判定: 要修正" in text
    assert "数値として読めません" in text


def test_write_notification_summary_report_lists_priority_counts(tmp_path) -> None:
    counts = pd.DataFrame([{"優先度": "High", "件数": 1}])
    summary = pd.DataFrame(
        [
            {
                "優先度": "High",
                "ETF": "SMH",
                "カテゴリ": "買い価格接近",
                "シグナル": "買い候補",
                "理由": "第1買い価格に接近",
                "推奨行動": "第1買い条件を確認",
            }
        ]
    )
    output_path = write_notification_summary_report(counts, summary, output_dir=tmp_path, report_date=datetime(2026, 6, 8))
    text = output_path.read_text(encoding="utf-8")
    assert "## 優先度別件数" in text
    assert "SMH" in text


def test_write_notification_delivery_plan_report_lists_routes(tmp_path) -> None:
    delivery_plan = pd.DataFrame(
        [
            {
                "優先度": "High",
                "ETF": "SMH",
                "配送先": "manual_immediate",
                "確認タイミング": "当日すぐ確認",
                "承認要否": "必要",
                "カテゴリ": "買い価格接近",
                "シグナル": "買い候補",
                "推奨行動": "第1買い条件を確認",
            }
        ]
    )
    output_path = write_notification_delivery_plan_report(
        delivery_plan,
        output_dir=tmp_path,
        report_date=datetime(2026, 6, 8),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "manual_immediate" in text
    assert "SMH" in text


def test_write_manual_decision_sheet_creates_csv(tmp_path) -> None:
    delivery_plan = pd.DataFrame(
        [
            {
                "優先度": "High",
                "ETF": "SMH",
                "配送先": "manual_immediate",
                "確認タイミング": "当日すぐ確認",
                "カテゴリ": "買い価格接近",
                "シグナル": "買い候補",
                "推奨行動": "第1買い条件を確認",
            }
        ]
    )
    processed_dir = tmp_path / "processed"
    output_path = write_manual_decision_sheet(
        delivery_plan,
        output_dir=tmp_path,
        processed_output_dir=processed_dir,
        report_date=datetime(2026, 6, 8),
    )
    text = output_path.read_text(encoding="utf-8")
    csv_path = processed_dir / "manual_decision_sheet_2026-06-08.csv"
    sheet = pd.read_csv(csv_path)
    assert "判断CSV" in text
    assert "入力欄" in text
    assert "GO/HOLD" in text
    assert sheet.iloc[0]["ETF"] == "SMH"
    assert "判断日" in sheet.columns
    assert "判断者" in sheet.columns
    assert "判断" in sheet.columns
    assert "実行価格" in sheet.columns
    assert "約定状態" in sheet.columns


def test_write_manual_decision_sheet_preserves_existing_inputs(tmp_path) -> None:
    delivery_plan = pd.DataFrame(
        [
            {
                "優先度": "High",
                "ETF": "SMH",
                "配送先": "manual_immediate",
                "確認タイミング": "当日すぐ確認",
                "カテゴリ": "買い価格接近",
                "シグナル": "買い候補",
                "推奨行動": "第1買い条件を確認",
            },
            {
                "優先度": "Medium",
                "ETF": "QQQ",
                "配送先": "daily_digest",
                "確認タイミング": "日次確認",
                "カテゴリ": "監視強化",
                "シグナル": "見送り",
                "推奨行動": "監視",
            },
        ]
    )
    processed_dir = tmp_path / "processed"
    write_manual_decision_sheet(
        delivery_plan.iloc[[0]],
        output_dir=tmp_path,
        processed_output_dir=processed_dir,
        report_date=datetime(2026, 6, 8),
    )
    csv_path = processed_dir / "manual_decision_sheet_2026-06-08.csv"
    existing = pd.read_csv(csv_path, dtype=str).fillna("")
    existing.loc[0, "判断"] = "watch"
    existing.loc[0, "メモ"] = "入力済み"
    existing.to_csv(csv_path, index=False)

    write_manual_decision_sheet(
        delivery_plan,
        output_dir=tmp_path,
        processed_output_dir=processed_dir,
        report_date=datetime(2026, 6, 8),
    )

    sheet = pd.read_csv(csv_path).fillna("")
    smh = sheet[sheet["ETF"].eq("SMH")].iloc[0]
    qqq = sheet[sheet["ETF"].eq("QQQ")].iloc[0]
    assert smh["判断"] == "watch"
    assert smh["メモ"] == "入力済み"
    assert qqq["判断"] == ""


def test_write_daily_health_report_marks_missing_artifacts(tmp_path) -> None:
    health = pd.DataFrame(
        [
            {
                "成果物": "日次レポート",
                "状態": "Missing",
                "サイズ": 0,
                "パス": "reports/daily/daily_report_2099-01-01.md",
            }
        ]
    )
    output_path = write_daily_health_report(health, output_dir=tmp_path, report_date=datetime(2099, 1, 1))
    text = output_path.read_text(encoding="utf-8")
    assert "判定: 要確認" in text
    assert "日次レポート" in text


def test_write_weekly_health_report_marks_missing_artifacts(tmp_path) -> None:
    health = pd.DataFrame(
        [
            {
                "成果物": "週次PDCAレポート",
                "状態": "Missing",
                "サイズ": 0,
                "パス": "reports/weekly/weekly_report_2099-01-01.md",
            }
        ]
    )
    output_path = write_weekly_health_report(health, output_dir=tmp_path, report_date=datetime(2099, 1, 1))
    text = output_path.read_text(encoding="utf-8")
    assert "判定: 要確認" in text
    assert "週次PDCAレポート" in text


def test_write_go_live_readiness_report_marks_hold_when_blocked(tmp_path) -> None:
    readiness = pd.DataFrame(
        [
            {"判定項目": "運用成果物", "状態": "Block", "理由": "不足あり"},
            {"判定項目": "売買実行", "状態": "Review", "理由": "手動判断"},
        ]
    )
    output_path = write_go_live_readiness_report(readiness, output_dir=tmp_path, report_date=datetime(2099, 1, 1))
    text = output_path.read_text(encoding="utf-8")
    assert "判定: HOLD" in text
    assert "運用成果物" in text


def test_write_go_live_readiness_report_marks_go_after_manual_review(tmp_path) -> None:
    readiness = pd.DataFrame(
        [
            {"判定項目": "運用成果物", "状態": "OK", "理由": "成果物OK"},
            {"判定項目": "売買実行", "状態": "Review", "理由": "手動判断"},
        ]
    )
    output_path = write_go_live_readiness_report(readiness, output_dir=tmp_path, report_date=datetime(2099, 1, 1))
    text = output_path.read_text(encoding="utf-8")
    assert "判定: GO（手動確認後）" in text
