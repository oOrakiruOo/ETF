# Cloud operation plan

PCをオフにして日次LINE通知を送るための運用方針です。

## 結論

第一候補は GitHub Actions です。
このリポジトリには `.github/workflows/daily-line.yml` があり、すでに日次実行の土台があります。

## 現在のGitHub Actions

- 実行時刻: `cron: "55 22 * * 0-4"`
- 日本時間: 平日 07:55 頃
- 実行内容:
  - `python -m src.main daily-ops --refresh`
  - `python -m src.main line-broadcast-decision-brief`
  - 失敗時だけ短いLINE失敗通知
- 成果物:
  - `reports/daily/`
  - `data/processed/line/`
  - `data/processed/signals/`
  - `data/processed/notifications/`
  - `data/processed/decisions/`

## 必要なGitHub Secrets

- `LINE_CHANNEL_ACCESS_TOKEN`

ブロードキャスト運用では `LINE_TO_USER_ID` は不要です。
個別Pushに戻す場合だけ使います。

## PC運用との違い

| 項目 | PCタスク | GitHub Actions |
|---|---|---|
| PCオフ | 不可 | 可 |
| Windowsログオン | 必要 | 不要 |
| LINE送信 | 可 | 可 |
| 生成物の保存 | ローカル | Actions artifact |
| 手動判断CSV | ローカル編集向き | artifact確認向き |

## 注意点

- GitHub ActionsのscheduleはUTCで指定します。
- 実行時刻は数分遅れることがあります。
- 無料枠や利用条件は変わる可能性があります。
- yfinanceの取得失敗に備え、失敗時はActionsログとartifactを確認します。
- 失敗通知が届いた場合、GitHub Actionsの該当runログを確認します。

## 検証済み実行

- run: `27917326665`
- event: `workflow_dispatch`
- conclusion: `success`
- LINE送信: `line-broadcast-decision-brief`
- HTTP status: `200`
- artifact: `daily-reports`

この実行で、PCを使わずGitHub Actions上で日次生成からLINEブロードキャスト送信まで通ることを確認済みです。

## クラウド実行の確認コマンド

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" run list --workflow "Daily ETF LINE" --limit 5
& "C:\Program Files\GitHub CLI\gh.exe" run view <run_id> --log
& "C:\Program Files\GitHub CLI\gh.exe" run download <run_id> -n daily-reports -D tmp\actions-daily-reports-<run_id>
```

## 次の改善候補

1. 週次PDCAもActionsへ移す
2. Actions artifactから最新レポートを取り出す手順を追加する
