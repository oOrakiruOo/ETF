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


def check_daily_artifacts(report_date: datetime | None = None) -> pd.DataFrame:
    date = report_date or datetime.now()
    date_text = f"{date:%Y-%m-%d}"
    rows: list[dict[str, object]] = []
    for name, template in DAILY_HEALTH_ARTIFACTS:
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
