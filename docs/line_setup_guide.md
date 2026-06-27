# LINE送信設定ガイド

このシステムはLINE Messaging APIで携帯向け要約を送信します。
LINE Notifyは2025年3月31日に終了済みのため使いません。

## 1. LINE Developersで準備する

1. LINE DevelopersでProviderを作成します。
2. Messaging APIチャネルを作成します。
3. チャネルのQRコードから、自分のLINEでBotを友だち追加します。
4. チャネルアクセストークンを発行します。
5. 送信運用ではWebhookは不要です。

## 2. 必要な値

- `LINE_CHANNEL_ACCESS_TOKEN`
  - Messaging APIチャネルの長期チャネルアクセストークン
- `LINE_TO_USER_ID`
  - 送信先ユーザーID
秘密値はREADME、CSV、Gitに保存しません。

## 3. 一時設定して確認する

スケジュール送信でも使う場合は、Windowsユーザー環境変数へ保存します。

```powershell
.\scripts\set_line_environment.ps1
```

トークンは非表示入力です。保存後、新しいPowerShellを開いて確認します。

```powershell
.\scripts\run_workflow.ps1 -Command line-check
```

`LINE設定: OK` と出れば送信準備完了です。

短い疎通確認だけ行う場合は、以下を使います。

```powershell
.\scripts\run_workflow.ps1 -Command line-test
```

その場だけでテストする場合は、以下のように一時設定しても構いません。ただし、この方法だけではスケジュール実行時に値が見えない場合があります。

```powershell
$env:LINE_CHANNEL_ACCESS_TOKEN = "取得したチャネルアクセストークン"
$env:LINE_TO_USER_ID = "送信先ユーザーID"
.\scripts\run_workflow.ps1 -Command line-check
```

## 4. 手動送信する

```powershell
.\scripts\run_workflow.ps1 -Command line-summary
```

送信される本文は、直近の `reports/daily/mobile_summary_YYYY-MM-DD.txt` と同じ内容です。

`LINE_TO_USER_ID` が分からない場合で、Botの友だちが自分だけなら、ユーザーIDなしのブロードキャスト送信を使えます。

```powershell
.\scripts\run_workflow.ps1 -Command line-broadcast-test
.\scripts\run_workflow.ps1 -Command line-broadcast-summary
```

## 5. スケジュール送信を登録する

LINE設定が済んだ後に、以下でLINE送信タスクも登録します。

個別Push用の `LINE_TO_USER_ID` が未確定で、Botの友だちが自分だけなら、まずブロードキャスト版を使います。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -Force -IncludeLineSummary -UseLineBroadcast -UseDecisionBrief
```

既定では毎日 07:55 に `line-broadcast-decision-brief` を実行します。

正しい `LINE_TO_USER_ID` を取得済みで個別Pushに切り替える場合は、`-UseLineBroadcast` を外します。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -Force -IncludeLineSummary -UseDecisionBrief
```

## 6. 注意

- 実売買は自動実行しません。
- LINE送信はレポート共有だけです。
- トークンを再発行した場合は、Windowsの環境変数やタスク実行環境も更新してください。

## 7. 自己確認ログを手動で記録する

LINE返信による自動記録は使いません。
必要な場合だけ、以下で手動記録します。

```powershell
.\scripts\run_workflow.ps1 -Command self-check -Status kept
.\scripts\run_workflow.ps1 -Command self-check -Status broke -Reason "SOFIを見て迷った"
.\scripts\run_workflow.ps1 -Command self-check -Status pending -Reason "判断保留"
```
