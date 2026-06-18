# LINE送信設定ガイド

このシステムはLINE Messaging APIで携帯向け要約を送信します。
LINE Notifyは2025年3月31日に終了済みのため使いません。

## 1. LINE Developersで準備する

1. LINE DevelopersでProviderを作成します。
2. Messaging APIチャネルを作成します。
3. チャネルのQRコードから、自分のLINEでBotを友だち追加します。
4. チャネルアクセストークンを発行します。
5. Webhookや応答メッセージは、初期テストでは必須ではありません。

## 2. 必要な値

- `LINE_CHANNEL_ACCESS_TOKEN`
  - Messaging APIチャネルの長期チャネルアクセストークン
- `LINE_TO_USER_ID`
  - 送信先ユーザーID

秘密値はREADME、CSV、Gitに保存しません。

## 3. 一時設定して確認する

```powershell
$env:LINE_CHANNEL_ACCESS_TOKEN = "取得したチャネルアクセストークン"
$env:LINE_TO_USER_ID = "送信先ユーザーID"
.\scripts\run_workflow.ps1 -Command line-check
```

`LINE設定: OK` と出れば送信準備完了です。

## 4. 手動送信する

```powershell
.\scripts\run_workflow.ps1 -Command line-summary
```

送信される本文は、直近の `reports/daily/mobile_summary_YYYY-MM-DD.txt` と同じ内容です。

## 5. スケジュール送信を登録する

LINE設定が済んだ後に、以下でLINE Summaryタスクも登録します。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -Force -IncludeLineSummary
```

既定では毎日 07:55 に `line-summary` を実行します。

## 6. 注意

- 実売買は自動実行しません。
- LINE送信はレポート共有だけです。
- トークンを再発行した場合は、Windowsの環境変数やタスク実行環境も更新してください。
