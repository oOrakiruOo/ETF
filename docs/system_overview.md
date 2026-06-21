# ETF Rotation System overview

## 目的

ETF Rotation Systemは、コア資産とサテライトETFの買い時・待機・保有確認を支援する日次判断システムです。

このシステムは売買を自動実行しません。
毎朝のデータ取得、スコア計算、リスク判定、LINE通知、週次PDCAまでを行い、最終判断と発注はユーザーが行います。

中核価値は、買い候補を探すことだけではありません。
個人投資家がやりがちな「上がったから飛びつく」「下がったから怖くなる」を抑え、必要な日は明確に「待つ」「何もしない」と伝えることです。

## 対象資産

### コア資産

長期積立や市場全体への分散投資を前提にします。

- 401k 外国株式インデックス
- NISA オルカン
- VT
- VTI
- SPY
- QQQ

コア資産は、暴落後や回復初期に分割買い候補として扱う場合があります。
ただし、DEFENSE判定中や条件が遠い場合は、無理に買いません。

### サテライト資産

テーマETFやセクターETFを対象にします。

- 半導体、AI、サイバーセキュリティ
- インフラ、ロボティクス、防衛
- エネルギー、金融、ヘルスケア、公益
- その他テーマETF

サテライトは、上昇テーマに飛びつくのではなく、スコア、ステージ、リスク、買い条件を見て慎重に扱います。

### 参考保有

個別株など、ETFシグナルでは直接買い増し判断しない保有です。

- TDK
- SOFI

参考保有は通知に表示されますが、ETF信号で買い増し判断しません。

## 日次の判断ラベル

LINE通知の最上段では、ユーザーが一瞬で行動を決められるように以下のラベルを使います。

| ラベル | 意味 | 基本行動 |
|---|---|---|
| DEFENSE | 市場リスクが高い | 新規買い禁止、ナンピン禁止、積立だけ |
| WAIT | 買い候補も売却確認もない | 何もしない |
| CHECK BUY | 買い候補がある | 手動確認 |
| CHECK SELL | 利確/売却候補がある | 保有継続、一部利確、売却可否を確認 |

優先順位は以下です。

```text
DEFENSE > CHECK SELL > CHECK BUY > WAIT
```

## 日次LINE通知の構成

通知は、専門指標よりも「今日何をするか」を先に出します。

例:

```text
ETF Rotation Daily 2026-06-22

市場スコア
32/100

🔴 DEFENSE
危険だから買わない。資金を守る日。

今日やること:
✅ 積立だけ通常ルールで継続
✅ 市場リスク対象を確認
❌ 新規買い禁止
❌ ナンピン禁止
❌ 過熱・失速銘柄の追い買い禁止
```

詳細指標は後半に回します。
ユーザーに最初に見せたいのは、RRやスコアの細部ではなく、買うか、待つか、確認するかです。

## 判定の主な材料

### 価格データ

`yfinance`からETF価格を取得し、ローカルまたはGitHub Actions上で日次処理します。

### 指標

- 移動平均
- RSI
- 乖離率
- 20日リターン
- 価格ステージ

### ETFスコア

各ETFの強さ、トレンド、リスク、買い条件をスコア化します。

### テーマスコア

ETFをテーマ別に集約し、テーマ全体の強弱や交代リスクを見ます。

### リスク判定

- 急落日ガード
- 過熱期
- 失速期
- テーマ交代リスク
- AI/半導体集中リスク
- 金利ショック、流動性ショック、急反発相場への備え

## 日次処理の流れ

```text
価格データ取得
→ 指標計算
→ ETFスコア計算
→ テーマスコア計算
→ シグナル判定
→ リスク管理
→ 日次レポート作成
→ 判断ブリーフ作成
→ LINE送信
→ 送信ログ保存
→ 手動判断CSV作成
→ GO/HOLD判定
```

主な成果物:

- `reports/daily/daily_report_YYYY-MM-DD.md`
- `reports/daily/decision_brief_YYYY-MM-DD.txt`
- `reports/daily/go_live_readiness_YYYY-MM-DD.md`
- `data/processed/decisions/manual_decision_sheet_YYYY-MM-DD.csv`
- `data/processed/line/line_delivery_log_YYYY-MM-DD.csv`

## GO/HOLD判定

GO/HOLDは、システムが「売買してよい」と命令するものではありません。
運用に必要な成果物と確認が揃っているかを見る安全ゲートです。

HOLDになる主な理由:

- 手動判断CSVが未入力
- 日次成果物が不足
- LINE設定が不足
- 週次ヘルスやPDCA確認が不足

`GO（手動確認後）` でも、実売買は自動実行しません。

## バックテストと検証

このシステムは、以下の検証を通して改善してきました。

- 10年バックテスト
- パラメータ総当たり検証
- 弱点局面分析
- 2024年AI加速局面の弱さ分析
- URA補助エントリー問題の分析
- コロナショック底打ち後の検証
- リーマンショック級局面の検証
- 30年仮想ユーザー不満シミュレーション

検証の結論は、常に「過去に合ったから未来も必ず勝てる」ではありません。
過去検証で見つけた弱点を、未来のリスク管理とPDCAに接続するために使います。

## PCオフ運用

PCを起動しなくても日次LINE通知を送るため、GitHub Actions運用を用意しています。

ワークフロー:

- `.github/workflows/daily-line.yml`

動作:

```text
平日 07:55頃
→ GitHub Actions起動
→ daily-ops --refresh
→ line-broadcast-decision-brief
→ LINE送信
→ daily-reports artifact保存
→ 失敗時だけLINE失敗通知
```

必要なGitHub Secret:

- `LINE_CHANNEL_ACCESS_TOKEN`

検証済み:

- GitHub Actions手動実行成功
- LINEブロードキャスト送信 HTTP 200
- artifact保存成功

## ローカル運用

PC上で動かす場合は、Windowsタスクスケジューラを使います。

主な確認コマンド:

```powershell
.\scripts\show_latest_status.ps1
.\scripts\check_line_delivery.ps1
.\scripts\check_cloud_delivery.ps1
```

PCタスクで自動送信する場合は、PCの電源を入れ、Windowsにログオンした状態にしておく必要があります。
PCオフ運用を優先する場合は、GitHub Actionsを使います。

## フォルダ構成

```text
config/      ETFユニバース、テーマ、リスク設定
src/         実装本体
scripts/     運用用PowerShell、Webhookサーバー
docs/        説明書、運用手順
tests/       pytest
reports/     日次・週次レポート生成物
data/        価格データ、シグナル、判断CSV
logs/        ローカルログ
tmp/         一時ファイル
```

Codex作業時は `docs/codex_context_map.md` を入口にし、重い生成物フォルダを必要以上に読まないことでトークン消費を抑えます。

## 免責

このシステムは投資助言ではありません。
売買判断の補助、記録、検証、通知を行うための研究・運用支援ツールです。
最終判断と売買実行はユーザー自身が行います。
