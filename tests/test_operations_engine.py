from __future__ import annotations

from datetime import datetime

from src.operations_engine import check_artifacts, check_daily_artifacts, check_operations_status, check_weekly_artifacts


def test_check_daily_artifacts_returns_expected_rows() -> None:
    result = check_daily_artifacts(datetime(2099, 1, 1))
    assert set(result["成果物"]) == {
        "日次レポート",
        "通知候補",
        "通知要約",
        "通知配送計画",
        "保有CSVチェック",
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
