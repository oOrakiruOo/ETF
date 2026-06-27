# 本運用開始チェックリスト

## 毎朝

1. GitHub Actionsの `Daily ETF LINE` が平日朝に動く
2. LINE通知の `結論:` と `今日やること:` だけを先に見る
3. `DEFENSE` / `WAIT` の日は新規買い・ナンピンをしない
4. `CHECK BUY` でも即買いせず、価格と保有比率を手動確認する
5. `CHECK SELL` は買い増しではなく保有確認として扱う
6. 必要なら `self-check` で `守れた` / `破った 理由` / `保留` を手動記録する
7. 実売買は自動実行しない。MASATOが最終判断する

## 初回LINE自動送信後

1. `scripts/check_cloud_delivery.ps1 -DownloadLatestArtifact` を実行
2. `Daily ETF LINE` の最新runが `success` であることを確認
3. LINE本文の最上段で、今日の行動が一瞬で分かるか確認
4. 今日が `DEFENSE` の場合は、新規買い・ナンピンをしないことを優先
5. 必要なら `self-check` で `守れた` / `破った 理由` / `保留` のいずれかを記録
6. `[check-these-first]` に出る判断ブリーフ、日次レポート、LINE送信ログ、手動判断CSVを確認

判断CSVでは、`判断` は `buy` / `sell` / `hold` / `watch`、`約定状態` は `filled` / `partial` / `not_filled` を基本値として使います。
未判断や未約定が残る場合、GO/HOLD判定は `HOLD` になります。
LINE設定が未完了の場合も、GO/HOLD判定に `LINE設定: Block` が表示されます。

本運用前の最終リハーサルだけ行う場合は、`scripts/run_final_rehearsal.ps1` を実行します。LINEの実送信は行いません。
正式版のLINEブロードキャストまで確認する場合だけ、`scripts/run_final_rehearsal.ps1 -SendLine` を実行します。
個別Push送信を確認する場合は、正しいユーザーIDが保存された後に `scripts/run_final_rehearsal.ps1 -SendLine -UsePush` を使います。

## 週次

1. GitHub Actionsの `Weekly ETF PDCA` が土曜朝に動く
2. `scripts/check_cloud_delivery.ps1 -Weekly -DownloadLatestArtifact` を実行
3. `weekly_report` の「自己確認ログ」で遵守率、破った日、保留日を確認
4. `weekly_report` の `PDCA: Act` と「前回Act確認」を確認
5. `replay_pdca_report` で弱点局面と見送り評価を確認
6. 完了したAct項目はCSVの `status` を `done` または `closed` に変更

## 自己確認ログ

LINE返信による自動記録は使いません。
必要な場合だけ、以下のように手動で記録します。

```powershell
.\scripts\run_workflow.ps1 -Command self-check -Status kept
.\scripts\run_workflow.ps1 -Command self-check -Status broke -Reason "SOFIを見て買いたくなった"
.\scripts\run_workflow.ps1 -Command self-check -Status pending -Reason "判断保留"
```

## 要確認が出た場合

1. 日次が古い場合は `scripts/run_workflow.ps1 -Command daily-ops` を再実行
2. 週次が古い場合は `weekly`、必要に応じて `replay-quick` を再実行
3. タスク失敗時は Windows タスクスケジューラの `LastTaskResult` を確認
4. 自己確認ログが必要な場合は `self-check` を手動実行
