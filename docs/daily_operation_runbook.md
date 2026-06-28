# 日次運用メモ

## 1. 基本運用

基本はGitHub ActionsでPCを起動せずに日次LINEを送ります。
毎朝は、LINE通知の最上段だけを先に見ます。

- `DEFENSE`: 積立だけ。新規買いとナンピンはしない
- `WAIT`: 何もしない。候補だけ監視
- `CHECK BUY`: 候補を手動確認
- `CHECK SELL`: 保有の利確/売却候補だけ確認

最新状態だけをまとめて見る場合は、以下を使います。

```powershell
.\scripts\show_latest_status.ps1
```

この表示には、LINE正式版ブロードキャストの次回実行予定も含まれます。

## 2. クラウド実行確認

日次と週次をまとめて確認する場合は、以下を使います。

```powershell
.\scripts\check_go_live_cloud.ps1
```

成果物までまとめて確認する場合は、以下を使います。

```powershell
.\scripts\check_go_live_cloud.ps1 -DownloadArtifacts
```

自動scheduleだけを確認する場合は、以下を使います。

```powershell
.\scripts\check_go_live_cloud.ps1 -ScheduleOnly
```

古い成功runを除外して確認する場合は、以下を使います。

```powershell
.\scripts\check_go_live_cloud.ps1 -ScheduleOnly -MaxAgeHours 168
```

GitHub Actionsの最新結果を確認する場合は、以下を使います。

```powershell
.\scripts\check_cloud_delivery.ps1
```

成功していない場合に止めたい確認では、以下を使います。

```powershell
.\scripts\check_cloud_delivery.ps1 -RequireSuccess
```

成果物まで確認する場合は、以下を使います。

```powershell
.\scripts\check_cloud_delivery.ps1 -DownloadLatestArtifact
```

`Daily ETF LINE` が `success` で、LINEに判断ブリーフが届いていれば日次運用は完了です。
週次PDCAを確認する場合は、以下を使います。

```powershell
.\scripts\check_cloud_delivery.ps1 -Weekly -RequireSuccess
```

## 3. PCから手動実行する場合

クラウド実行が失敗した日や、手元で再生成したい日だけ使います。

```powershell
python -m src.main daily-ops
```

作成された日次レポート、通知配送計画、手動判断CSV、GO/HOLD判定を確認します。実売買は自動実行しません。

LINE設定後は、以下の順で確認します。

```powershell
.\scripts\run_workflow.ps1 -Command line-check
.\scripts\run_workflow.ps1 -Command line-test
.\scripts\run_workflow.ps1 -Command line-broadcast-decision-brief
```

`line-test` は短い疎通確認、`line-broadcast-decision-brief` は当日の正式版ブロードキャスト送信です。

PCタスクで自動LINE送信した場合の確認は、以下を使います。

```powershell
.\scripts\check_line_delivery.ps1
```

`line-delivery` に当日の送信履歴が出れば、送信処理は成功しています。

Windowsタスクは予備運用です。
PCタスクで自動送信する日は、PCの電源を入れ、Windowsにログオンした状態にしておきます。

## 4. 手動判断CSV

`data/processed/decisions/manual_decision_sheet_YYYY-MM-DD.csv` を開き、各行の `判断` を埋めます。

- 買う: `buy`
- 売る: `sell`
- 保有継続: `hold`
- 監視のみ: `watch`

約定した場合だけ、`数量`, `指値`, `実行価格`, `実行時刻`, `約定状態`, `メモ` を入力します。

## 5. GO/HOLD確認

`reports/daily/go_live_readiness_YYYY-MM-DD.md` を確認します。

- `GO（手動確認後）`: 運用成果物と判断CSVは確認済み。最終判断はMASATOが行う
- `HOLD`: 未判断、未約定、成果物不足を先に解消する

## 6. 週次Act

`data/processed/pdca/weekly_action_items_YYYY-MM-DD.csv` の `open` 項目を確認します。完了した項目は `done` または `closed` に変更します。
