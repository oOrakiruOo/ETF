from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.operations_engine import (
    check_artifacts,
    check_daily_artifacts,
    check_go_live_readiness,
    check_operations_status,
    check_weekly_artifacts,
)


def test_check_daily_artifacts_returns_expected_rows() -> None:
    result = check_daily_artifacts(datetime(2099, 1, 1))
    assert set(result["成果物"]) == {
        "日次レポート",
        "通知候補",
        "通知要約",
        "通知配送計画",
        "保有CSVチェック",
        "手動判断シート",
        "手動判断CSV",
        "通知アウトボックス",
        "即時通知パケット",
        "日次通知パケット",
        "記録通知パケット",
        "シグナルCSV",
    }
    assert set(result["状態"]) == {"Missing"}


def test_check_weekly_artifacts_returns_expected_rows() -> None:
    result = check_weekly_artifacts(datetime(2099, 1, 1))
    assert set(result["成果物"]) == {
        "週次PDCAレポート",
        "週次Act追跡",
        "週次フォワードリターン",
        "週次仮想売買",
        "週次見送り評価",
        "軽量履歴再生レポート",
        "履歴シグナルCSV",
        "履歴再生仮想売買",
        "履歴再生見送り評価",
        "買い価格総当たり",
        "回避方針総当たり",
    }
    assert set(result["状態"]) == {"Missing"}


def test_check_artifacts_allows_empty_files_when_configured(tmp_path) -> None:
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")
    result = check_artifacts([("空ファイル", str(empty_file), True)], datetime(2099, 1, 1))
    assert result.iloc[0]["状態"] == "OK"
    assert result.iloc[0]["サイズ"] == 0


def test_check_operations_status_marks_stale_latest_artifacts(tmp_path) -> None:
    daily_dir = tmp_path / "reports" / "daily"
    daily_dir.mkdir(parents=True)
    (daily_dir / "daily_health_2099-01-01.md").write_text("ok", encoding="utf-8")
    status = check_operations_status(datetime(2099, 1, 3), project_root=tmp_path)
    daily_health = status[status["確認項目"].eq("日次ヘルス")].iloc[0]
    assert daily_health["状態"] == "Stale"
    assert daily_health["経過日数"] == 2


def test_check_operations_status_shows_open_weekly_action_count(tmp_path) -> None:
    pdca_dir = tmp_path / "data" / "processed" / "pdca"
    pdca_dir.mkdir(parents=True)
    actions = pd.DataFrame(
        [
            {"status": "open", "action_item": "確認する"},
            {"status": "done", "action_item": "完了"},
            {"status": "closed", "action_item": "終了"},
        ]
    )
    actions.to_csv(pdca_dir / "weekly_action_items_2099-01-01.csv", index=False)

    status = check_operations_status(datetime(2099, 1, 2), project_root=tmp_path)
    weekly_actions = status[status["確認項目"].eq("週次Act追跡")].iloc[0]
    assert weekly_actions["状態"] == "OK"
    assert weekly_actions["補足"] == "未完了Act 1件"


def test_check_go_live_readiness_blocks_when_artifacts_are_missing(tmp_path) -> None:
    readiness = check_go_live_readiness(datetime(2099, 1, 2), project_root=tmp_path)
    blockers = readiness[readiness["状態"].eq("Block")]
    assert {"運用成果物", "日次ヘルス", "週次ヘルス"}.issubset(set(blockers["判定項目"]))
    assert "売買実行" in set(readiness[readiness["状態"].eq("Review")]["判定項目"])


def test_check_go_live_readiness_accepts_recent_weekly_health(tmp_path) -> None:
    daily_dir = tmp_path / "reports" / "daily"
    weekly_dir = tmp_path / "reports" / "weekly"
    notification_dir = tmp_path / "data" / "processed" / "notifications"
    decisions_dir = tmp_path / "data" / "processed" / "decisions"
    signals_dir = tmp_path / "data" / "processed" / "signals"
    pdca_dir = tmp_path / "data" / "processed" / "pdca"
    for directory in [daily_dir, weekly_dir, notification_dir, decisions_dir, signals_dir, pdca_dir]:
        directory.mkdir(parents=True)

    for name in [
        "daily_report",
        "notification_candidates",
        "notification_summary",
        "notification_delivery_plan",
        "portfolio_check",
        "manual_decision_sheet",
    ]:
        (daily_dir / f"{name}_2099-01-02.md").write_text("ok", encoding="utf-8")
    (decisions_dir / "manual_decision_sheet_2099-01-02.csv").write_text("ok", encoding="utf-8")
    (notification_dir / "notification_outbox_2099-01-02.jsonl").write_text("ok", encoding="utf-8")
    for name in [
        "notification_packets_manual_immediate",
        "notification_packets_daily_digest",
        "notification_packets_archive_only",
    ]:
        (notification_dir / f"{name}_2099-01-02.jsonl").write_text("", encoding="utf-8")
    (signals_dir / "signals_2099-01-02.csv").write_text("ok", encoding="utf-8")
    (daily_dir / "daily_health_2099-01-02.md").write_text("ok", encoding="utf-8")
    (weekly_dir / "weekly_health_2099-01-01.md").write_text("ok", encoding="utf-8")
    (weekly_dir / "weekly_report_2099-01-01.md").write_text("ok", encoding="utf-8")
    (weekly_dir / "replay_pdca_report_2099-01-01.md").write_text("ok", encoding="utf-8")
    (pdca_dir / "weekly_action_items_2099-01-01.csv").write_text("status,action_item\nopen,確認\n", encoding="utf-8")

    readiness = check_go_live_readiness(datetime(2099, 1, 2), project_root=tmp_path)
    weekly_gate = readiness[readiness["判定項目"].eq("週次ヘルス")].iloc[0]
    assert weekly_gate["状態"] == "OK"
