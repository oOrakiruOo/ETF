# Codex context map

このファイルは、Codexが作業開始時に読む最短MAPです。
大量のCSVやレポートを毎回読まず、必要な入口だけ確認します。

## 目的

ETF Rotationを毎日実行し、LINEで「今日買うか、待つか、確認するか」を知らせる。
実売買は自動実行しない。最終判断はユーザーが行う。

## 重要ファイル

- `src/main.py`: コマンド入口
- `src/report_engine.py`: 日次レポート、判断ブリーフ、週次レポート
- `src/notification_engine.py`: 通知候補、配送計画
- `src/line_engine.py`: LINE送信、送信ログ
- `src/operations_engine.py`: 日次ヘルス、GO/HOLD判定
- `.github/workflows/daily-line.yml`: PCオフ運用候補のGitHub Actions
- `docs/daily_operation_runbook.md`: 日次運用手順
- `docs/go_live_checklist.md`: 本運用チェック

## 通常確認コマンド

```powershell
.\scripts\show_latest_status.ps1
.\scripts\check_line_delivery.ps1
.\.venv\Scripts\python.exe -m pytest --basetemp .\tmp\pytest
```

## 大きく読まないフォルダ

以下は生成物またはデータであり、必要時だけ読む。

- `data/raw/`
- `data/processed/`
- `reports/daily/`
- `reports/weekly/`
- `logs/`
- `tmp/`
- `.venv/`

## 現在の運用判断

- `DEFENSE`: 新規買い禁止、ナンピン禁止、積立だけ
- `WAIT`: 基本待機
- `CHECK BUY`: 買い候補を手動確認
- `CHECK SELL`: 利確/売却候補を手動確認

## Git運用

mainへ直接pushしない。
featureブランチで変更し、PRを作ってからマージする。
