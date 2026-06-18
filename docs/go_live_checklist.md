# 本運用開始チェックリスト

## 毎朝

1. `python -m src.main daily-ops` を実行
2. `reports/daily/mobile_summary_YYYY-MM-DD.txt` で携帯向け要約を確認
3. LINE設定後は `scripts/run_workflow.ps1 -Command line-check`、初回のみ `line-test`、送信時は `line-summary` を確認
4. `reports/daily/notification_delivery_plan_YYYY-MM-DD.md` で High / Medium を確認
5. `data/processed/decisions/manual_decision_sheet_YYYY-MM-DD.csv` に判断・数量・価格・メモを記録
6. `reports/daily/go_live_readiness_YYYY-MM-DD.md` の判定を確認
7. `GO（手動確認後）` でも実売買は自動実行しない。MASATOが最終判断する

判断CSVでは、`判断` は `buy` / `sell` / `hold` / `watch`、`約定状態` は `filled` / `partial` / `not_filled` を基本値として使います。
未判断や未約定が残る場合、GO/HOLD判定は `HOLD` になります。
LINE設定が未完了の場合も、GO/HOLD判定に `LINE設定: Block` が表示されます。

## 週次

1. `reports/weekly/weekly_health_YYYY-MM-DD.md` の判定が `OK`
2. `reports/weekly/weekly_report_YYYY-MM-DD.md` の「前回Act確認」と PDCA: Act を確認
3. `data/processed/pdca/weekly_action_items_YYYY-MM-DD.csv` で翌週に追う改善項目を確認
4. `reports/weekly/replay_pdca_report_YYYY-MM-DD.md` で弱点局面と見送り評価を確認
5. 完了したAct項目はCSVの `status` を `done` または `closed` に変更

## 要確認が出た場合

1. 日次が古い場合は `scripts/run_workflow.ps1 -Command daily-ops` を再実行
2. 週次が古い場合は `weekly`、必要に応じて `replay-quick` を再実行
3. タスク失敗時は Windows タスクスケジューラの `LastTaskResult` を確認
