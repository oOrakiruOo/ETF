# LINE送信設定ガイド

このシステムはLINE Messaging APIで携帯向け要約を送信します。
LINE Notifyは2025年3月31日に終了済みのため使いません。

## 1. LINE Developersで準備する

1. LINE DevelopersでProviderを作成します。
2. Messaging APIチャネルを作成します。
3. チャネルのQRコードから、自分のLINEでBotを友だち追加します。
4. チャネルアクセストークンを発行します。
5. 送信だけならWebhookは必須ではありません。
6. LINE返信で `守れた / 破った / 保留` を記録する場合は、Webhook URLも設定します。

## 2. 必要な値

- `LINE_CHANNEL_ACCESS_TOKEN`
  - Messaging APIチャネルの長期チャネルアクセストークン
- `LINE_TO_USER_ID`
  - 送信先ユーザーID
- `LINE_CHANNEL_SECRET`
  - Webhook署名検証用のChannel secret
  - 返信記録を使う場合にクラウド環境へ設定します

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

LINE設定が済んだ後に、以下でLINE Summaryタスクも登録します。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -Force -IncludeLineSummary
```

既定では毎日 07:55 に `line-summary` を実行します。

## 6. 注意

- 実売買は自動実行しません。
- LINE送信はレポート共有だけです。
- トークンを再発行した場合は、Windowsの環境変数やタスク実行環境も更新してください。

## 7. LINE返信で自己確認を記録する

Webhookを使う場合は、`docs/line_webhook_deploy_guide.md` に従ってWebhookサーバーを公開します。

LINE DevelopersのWebhook URLには以下を設定します。

```text
https://<公開URL>/line-webhook
```

Botへ以下のように返信すると、週次PDCAの自己確認ログに反映されます。

```text
守れた
破った SOFIを見て迷った
保留
```

クラウド側では `LINE_CHANNEL_SECRET` を設定してください。
未設定でもローカル検証はできますが、本番では署名検証を有効にします。
