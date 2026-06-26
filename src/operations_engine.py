from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .line_engine import check_line_settings
from .pdca_engine import summarize_manual_decisions
from .utils import PROJECT_ROOT


ArtifactSpec = tuple[str, str] | tuple[str, str, bool]

DAILY_HEALTH_ARTIFACTS = [
    ("日次レポート", "reports/daily/daily_report_{date}.md"),
    ("携帯向け要約", "reports/daily/mobile_summary_{date}.txt"),
    ("通知候補", "reports/daily/notification_candidates_{date}.md"),
    ("通知要約", "reports/daily/notification_summary_{date}.md"),
    ("通知配送計画", "reports/daily/notification_delivery_plan_{date}.md"),
    ("保有CSVチェック", "reports/daily/portfolio_check_{date}.md"),
    ("手動判断シート", "reports/daily/manual_decision_sheet_{date}.md"),
    ("手動判断CSV", "data/processed/decisions/manual_decision_sheet_{date}.csv"),
    ("通知アウトボックス", "data/processed/notifications/notification_outbox_{date}.jsonl"),
    ("即時通知パケット", "data/processed/notifications/notification_packets_manual_immediate_{date}.jsonl", True),
    ("日次通知パケット", "data/processed/notifications/notification_packets_daily_digest_{date}.jsonl", True),
    ("記録通知パケット", "data/processed/notifications/notification_packets_archive_only_{date}.jsonl", True),
    ("シグナルCSV", "data/processed/signals/signals_{date}.csv"),
    ("データ取得元ステータス", "data/processed/data_source_status.csv"),
]

WEEKLY_HEALTH_ARTIFACTS = [
    ("週次PDCAレポート", "reports/weekly/weekly_report_{date}.md"),
    ("週次Act追跡", "data/processed/pdca/weekly_action_items_{date}.csv"),
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

OPERATIONS_STATUS_ARTIFACTS = [
    ("日次ヘルス", "reports/daily", "daily_health_*.md", 1, False),
    ("日次レポート", "reports/daily", "daily_report_*.md", 1, False),
    ("通知配送計画", "reports/daily", "notification_delivery_plan_*.md", 1, False),
    ("手動判断シート", "reports/daily", "manual_decision_sheet_*.md", 1, False),
    ("日次通知パケット", "data/processed/notifications", "notification_packets_daily_digest_*.jsonl", 1, True),
    ("週次ヘルス", "reports/weekly", "weekly_health_*.md", 8, False),
    ("週次PDCAレポート", "reports/weekly", "weekly_report_*.md", 8, False),
    ("週次Act追跡", "data/processed/pdca", "weekly_action_items_*.csv", 8, False),
    ("軽量履歴再生レポート", "reports/weekly", "replay_pdca_report_*.md", 8, False),
]


def check_artifacts(
    artifacts: list[ArtifactSpec],
    report_date: datetime | None = None,
    project_root: Path = PROJECT_ROOT,
) -> pd.DataFrame:
    date = report_date or datetime.now()
    date_text = f"{date:%Y-%m-%d}"
    rows: list[dict[str, object]] = []
    for artifact in artifacts:
        name, template = artifact[:2]
        allow_empty = bool(artifact[2]) if len(artifact) > 2 else False
        relative_path = Path(template.format(date=date_text))
        path = relative_path if relative_path.is_absolute() else project_root / relative_path
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        ok = exists and (size > 0 or allow_empty)
        rows.append(
            {
                "成果物": name,
                "状態": "OK" if ok else "Missing",
                "サイズ": size,
                "パス": str(path),
            }
        )
    return pd.DataFrame(rows)


def check_daily_artifacts(report_date: datetime | None = None, project_root: Path = PROJECT_ROOT) -> pd.DataFrame:
    return check_artifacts(DAILY_HEALTH_ARTIFACTS, report_date, project_root)


def check_weekly_artifacts(report_date: datetime | None = None, project_root: Path = PROJECT_ROOT) -> pd.DataFrame:
    return check_artifacts(WEEKLY_HEALTH_ARTIFACTS, report_date, project_root)


def _date_from_stem(path: Path) -> datetime | None:
    try:
        return datetime.strptime(path.stem[-10:], "%Y-%m-%d")
    except ValueError:
        return None


def _weekly_action_note(path: Path) -> str:
    try:
        actions = pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return "Act追跡CSVを読めません"
    if actions.empty or "status" not in actions.columns:
        return "未完了Act 0件"
    open_count = int((~actions["status"].astype(str).str.lower().isin(["done", "closed"])).sum())
    return f"未完了Act {open_count}件"


def _latest_dated_file(project_root: Path, folder: str, pattern: str) -> Path | None:
    directory = project_root / folder
    paths = sorted(directory.glob(pattern)) if directory.exists() else []
    dated_paths = [(path_date, path) for path in paths if (path_date := _date_from_stem(path)) is not None]
    if not dated_paths:
        return None
    return max(dated_paths, key=lambda item: item[0])[1]


def _manual_decision_gate(project_root: Path, date: datetime) -> dict[str, str]:
    path = project_root / "data" / "processed" / "decisions" / f"manual_decision_sheet_{date:%Y-%m-%d}.csv"
    if not path.exists():
        return {"判定項目": "手動判断ログ", "状態": "Block", "理由": "当日の手動判断CSVなし"}
    try:
        decisions = pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return {"判定項目": "手動判断ログ", "状態": "Block", "理由": "手動判断CSVを読めません"}
    summary = summarize_manual_decisions(decisions).iloc[0]
    needs_review = int(summary.get("要確認件数", 0) or 0)
    if needs_review:
        return {"判定項目": "手動判断ログ", "状態": "Block", "理由": str(summary.get("理由", "手動判断に要確認あり"))}
    return {"判定項目": "手動判断ログ", "状態": "OK", "理由": str(summary.get("理由", "確認漏れなし"))}


def _line_settings_gate() -> dict[str, str]:
    settings = check_line_settings()
    missing = [name for name, exists in settings.items() if not exists]
    if missing:
        return {"判定項目": "LINE設定", "状態": "Block", "理由": f"未設定: {', '.join(missing)}"}
    return {"判定項目": "LINE設定", "状態": "OK", "理由": "携帯通知の送信設定あり"}


def check_go_live_readiness(
    report_date: datetime | None = None,
    project_root: Path = PROJECT_ROOT,
) -> pd.DataFrame:
    date = report_date or datetime.now()
    operation_status = check_operations_status(date, project_root)
    daily_health = check_daily_artifacts(date, project_root)
    latest_action_path = _latest_dated_file(project_root, "data/processed/pdca", "weekly_action_items_*.csv")
    action_note = _weekly_action_note(latest_action_path) if latest_action_path is not None else "週次Act追跡なし"
    weekly_status = operation_status[operation_status["確認項目"].eq("週次ヘルス")]
    weekly_ok = not weekly_status.empty and weekly_status["状態"].eq("OK").all()

    gates = [
        {
            "判定項目": "運用成果物",
            "状態": "OK" if not operation_status.empty and operation_status["状態"].eq("OK").all() else "Block",
            "理由": "日次・週次の最新成果物が揃っているか",
        },
        {
            "判定項目": "日次ヘルス",
            "状態": "OK" if not daily_health.empty and daily_health["状態"].eq("OK").all() else "Block",
            "理由": "当日の日次成果物が全て揃っているか",
        },
        {
            "判定項目": "週次ヘルス",
            "状態": "OK" if weekly_ok else "Block",
            "理由": "直近8日以内の週次ヘルスがOKか",
        },
        {
            "判定項目": "週次Act",
            "状態": "Review",
            "理由": action_note,
        },
        _manual_decision_gate(project_root, date),
        _line_settings_gate(),
        {
            "判定項目": "売買実行",
            "状態": "Review",
            "理由": "実売買は自動実行せず、通知計画と日次レポートを確認してMASATOが最終判断",
        },
    ]
    return pd.DataFrame(gates)


def check_operations_status(
    report_date: datetime | None = None,
    project_root: Path = PROJECT_ROOT,
) -> pd.DataFrame:
    date = report_date or datetime.now()
    rows: list[dict[str, object]] = []
    for name, folder, pattern, max_age_days, allow_empty in OPERATIONS_STATUS_ARTIFACTS:
        directory = project_root / folder
        paths = sorted(directory.glob(pattern)) if directory.exists() else []
        dated_paths = [(path_date, path) for path in paths if (path_date := _date_from_stem(path)) is not None]
        if not dated_paths:
            rows.append(
                {
                    "確認項目": name,
                    "状態": "Missing",
                    "最新日": "",
                    "経過日数": "",
                    "サイズ": 0,
                    "パス": str(directory / pattern),
                    "補足": "",
                }
            )
            continue
        latest_date, latest_path = max(dated_paths, key=lambda item: item[0])
        age_days = (date.date() - latest_date.date()).days
        size = latest_path.stat().st_size
        fresh = age_days <= int(max_age_days)
        has_content = size > 0 or bool(allow_empty)
        note = _weekly_action_note(latest_path) if name == "週次Act追跡" and latest_path.exists() else ""
        rows.append(
            {
                "確認項目": name,
                "状態": "OK" if fresh and has_content else "Stale",
                "最新日": f"{latest_date:%Y-%m-%d}",
                "経過日数": age_days,
                "サイズ": size,
                "パス": str(latest_path),
                "補足": note,
            }
        )
    return pd.DataFrame(rows)
