# Remaining tasks

このファイルは、残タスクだけを短く管理するための一覧です。
詳細確認は必要になった時だけ、各ドキュメントや成果物を読みます。

## 現在地

- 全体進捗: 約99.95%
- 本運用前の安定化: 実装完了寄り
- PCオフ運用: GitHub Actionsで実証済み
- 日次LINE通知: schedule実行で連続成功中
- 週次PDCA: schedule実行成功確認済み
- 日次/週次artifact: 手動dispatch分の必要ファイル確認済み

## 完了済み

- 日次レポート
- 判断ブリーフ
- LINEブロードキャスト
- LINE送信ログ
- Windowsタスク運用
- GitHub ActionsによるPCオフ運用
- 週次PDCAのGitHub Actions化
- 失敗時LINE通知
- システム概要書
- ユーザー向け日次ガイド
- Codex用最短MAP
- Actions artifact確認手順の短縮
- 週次PDCAへの自己確認フィードバック追加
- LINE判断ブリーフの一言結論追加
- 価格データ取得元ステータスとキャッシュ退避を追加
- Codex軽量タスクテンプレ追加
- 日次/週次クラウドartifact確認
- LINE返信/Webhook機能の削除
- schedule専用クラウド確認コマンド
- クラウド確認の鮮度チェック

## 残タスク

1. 次回の日次クラウド実行確認
   - 手動実行は成功済み
   - `data_source_status.csv` のartifact格納は確認済み
   - schedule実行の連続成功を確認済み
   - LINE返信/Webhook削除後のworkflow_dispatch成功を確認済み
   - 判断ブリーフ送信ログHTTP 200を確認済み
   - `.\scripts\check_go_live_cloud.ps1 -ScheduleOnly -MaxAgeHours 168` で最終観察

2. 初回の週次クラウドPDCA確認
   - `Weekly ETF PDCA` の手動実行は成功済み
   - `weekly_report` と `replay_pdca_report` のartifact格納は確認済み
   - schedule実行が成功
   - 週次LINE要約送信ログを確認済み
   - LINE返信/Webhook削除後のworkflow_dispatch成功を確認済み
   - 週次LINE要約送信ログHTTP 200を確認済み
   - `.\scripts\check_go_live_cloud.ps1 -ScheduleOnly -MaxAgeHours 168` で最終観察

3. 1週間運用後の自己確認反映
   - 必要な日だけ `self-check` で手動記録
   - DEFENSE日に買い急ぎを止められたか
   - CHECK BUYが実際に判断しやすかったか

## 継続改善候補

1. 通知文の継続観察
   - 次の買い候補の表示量
   - 売却/利確確認の表現
   - 1週間使って迷いが残った箇所
   - LINE返信は使わず、通知本文だけで判断しやすいか

2. データソース強化
   - 現在はyfinance中心
   - 次段階で代替データソースや冗長化を検討

## 100%判定

以下を満たしたら、本運用準備は100%と判定します。

1. LINE返信/Webhook削除後も、平日の日次LINEがクラウドから届く（手動dispatchは確認済み、次回schedule待ち）
2. LINE返信/Webhook削除後も、土曜の週次PDCA LINEがクラウドから届く（手動dispatchは確認済み、次回schedule待ち）
3. 1週間分の自己確認が週次PDCAに反映される
4. `scripts/check_cloud_delivery.ps1 -DownloadLatestArtifact` で日次成果物を確認できる（手動実行分は確認済み）
5. `scripts/check_cloud_delivery.ps1 -Weekly -DownloadLatestArtifact` で週次成果物を確認できる（手動実行分は確認済み）

最終確認コマンド:

```powershell
.\scripts\check_go_live_cloud.ps1 -ScheduleOnly -MaxAgeHours 168
```

## 当面の最優先

新機能を増やさず、クラウド実行、LINE判断ブリーフ、自己確認ログを1週間観察する。
改善は週次PDCAでまとめて入れる。
