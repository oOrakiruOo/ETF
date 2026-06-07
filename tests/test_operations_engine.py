from __future__ import annotations

from datetime import datetime

from src.operations_engine import check_daily_artifacts


def test_check_daily_artifacts_returns_expected_rows() -> None:
    result = check_daily_artifacts(datetime(2099, 1, 1))
    assert set(result["成果物"]) == {
        "日次レポート",
        "通知候補",
        "通知要約",
        "保有CSVチェック",
        "通知アウトボックス",
        "シグナルCSV",
    }
    assert set(result["状態"]) == {"Missing"}
