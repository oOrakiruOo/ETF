from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT


DAILY_HEALTH_ARTIFACTS = [
    ("日次レポート", "reports/daily/daily_report_{date}.md"),
    ("通知候補", "reports/daily/notification_candidates_{date}.md"),
    ("通知要約", "reports/daily/notification_summary_{date}.md"),
    ("保有CSVチェック", "reports/daily/portfolio_check_{date}.md"),
    ("通知アウトボックス", "data/processed/notifications/notification_outbox_{date}.jsonl"),
    ("シグナルCSV", "data/processed/signals/signals_{date}.csv"),
]

WEEKLY_HEALTH_ARTIFACTS = [
    ("週次PDCAレポート", "reports/weekly/weekly_report_{date}.md"),
    ("週次フォワードリターン", "data/processed/signals/signal_forward_returns_{date}.csv"),
    ("週次仮想売買", "data/processed/signals/virtual_trades_{date}.csv"),
    ("週次見送り評価", "data/processed/signals/avoid_outcomes_{date}.csv"),
    ("軽量履歴再生レポート", "reports/weekly/replay_pdca_report_{date}.md"),
    ("履歴シグナルCSV", "data/processed/signals/historical_signals_{date}.csv"),
    ("履歴再生仮想売買", "data/processed/signals/replay_virtual_trades_{date}.csv"),
    ("履歴再生見送り評価", "data/processed/signals/replay_avoid_outcomes_{date}.csv"),
    ("買い価格総当たり", "data/processed/signals/replay_entry_parameter_search_{date}.csv"),
    ("回避方針総当たり", "data/processed/signals/replay_avoid_policy_search_{date}.csv"),
]


def check_artifacts(
    artifacts: list[tuple[str, str]],
    report_date: datetime | None = None,
) -> pd.DataFrame:
    date = report_date or datetime.now()
    date_text = f"{date:%Y-%m-%d}"
    rows: list[dict[str, object]] = []
    for name, template in artifacts:
        relative_path = Path(template.format(date=date_text))
        path = PROJECT_ROOT / relative_path
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        rows.append(
            {
                "成果物": name,
                "状態": "OK" if exists and size > 0 else "Missing",
                "サイズ": size,
                "パス": str(path),
            }
        )
    return pd.DataFrame(rows)


def check_daily_artifacts(report_date: datetime | None = None) -> pd.DataFrame:
    return check_artifacts(DAILY_HEALTH_ARTIFACTS, report_date)


def check_weekly_artifacts(report_date: datetime | None = None) -> pd.DataFrame:
    return check_artifacts(WEEKLY_HEALTH_ARTIFACTS, report_date)
