# LINE Webhook deploy guide

LINE返信で `守れた / 破った / 保留` を記録するための最小デプロイ手順です。

## 目的

- 日次LINE通知を見る
- LINEで `守れた`、`破った 理由`、`保留` のいずれかを返信する
- Webhookが返信を受け取り、`data/processed/pdca/self_check_log.csv` に記録する
- 週次PDCAで遵守率を確認する

## 起動コマンド

ローカル確認:

```powershell
$env:PORT="8080"
.\.venv\Scripts\python.exe scripts\line_webhook_server.py
```

Docker確認:

```powershell
docker build -t etf-line-webhook .
docker run --rm -p 8080:8080 -e PORT=8080 -e SELF_CHECK_LOG_PATH=/data/self_check_log.csv -v ${PWD}/tmp:/data etf-line-webhook
```

## エンドポイント

- ヘルスチェック: `GET /health`
- LINE Webhook: `POST /line-webhook`

LINE DevelopersのWebhook URLには、クラウドで発行されたHTTPS URLの末尾に `/line-webhook` を付けます。

例:

```text
https://example-free-cloud-app.example.com/line-webhook
```

## 環境変数

署名検証を有効にする場合:

```text
LINE_CHANNEL_SECRET
```

自己確認ログの保存先を変える場合:

```text
SELF_CHECK_LOG_PATH
```

例:

```text
SELF_CHECK_LOG_PATH=/data/self_check_log.csv
```

`LINE_CHANNEL_SECRET` を設定すると、LINEの `X-Line-Signature` が正しい場合だけ記録します。
未設定の場合は署名検証なしで受け付けます。ローカル検証以外では設定してください。

## 返信例

```text
守れた
破った SOFIを見て迷った
保留
OK
NG
pending
```

## 注意

無料クラウドの一時ファイル領域では、`self_check_log.csv` が再起動で消える場合があります。
本番では `SELF_CHECK_LOG_PATH` を永続ディスクのパスへ向けるか、外部DB、GitHub Actions artifact、Google Sheets等への保存に切り替えてください。

現時点の実装は「返信を受けて記録する最小入口」です。売買発注は行いません。
