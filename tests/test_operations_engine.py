from __future__ import annotations

from datetime import datetime

from src.operations_engine import check_daily_artifacts, check_weekly_artifacts


def test_check_daily_artifacts_returns_expected_rows() -> None:
    result = check_daily_artifacts(datetime(2099, 1, 1))
    assert set(result["成果物"]) == {
        "日次レポート",
        "通知候補",
        "通知要約",
        "通知配送計画",
        "保有CSVチェック",
        "通知アウトボックス",
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
