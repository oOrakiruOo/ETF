# 日次運用メモ

## 1. 日次一括生成

```powershell
python -m src.main daily-ops
```

作成された日次レポート、通知配送計画、手動判断CSV、GO/HOLD判定を確認します。実売買は自動実行しません。

## 2. 手動判断CSV

`data/processed/decisions/manual_decision_sheet_YYYY-MM-DD.csv` を開き、各行の `判断` を埋めます。

- 買う: `buy`
- 売る: `sell`
- 保有継続: `hold`
- 監視のみ: `watch`

約定した場合だけ、`数量`, `指値`, `実行価格`, `実行時刻`, `約定状態`, `メモ` を入力します。

## 3. GO/HOLD確認

`reports/daily/go_live_readiness_YYYY-MM-DD.md` を確認します。

- `GO（手動確認後）`: 運用成果物と判断CSVは確認済み。最終判断はMASATOが行う
- `HOLD`: 未判断、未約定、成果物不足を先に解消する

## 4. 週次Act

`data/processed/pdca/weekly_action_items_YYYY-MM-DD.csv` の `open` 項目を確認します。完了した項目は `done` または `closed` に変更します。
