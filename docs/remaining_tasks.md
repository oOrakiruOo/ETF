# Remaining tasks

このファイルは、残タスクだけを短く管理するための一覧です。
詳細確認は必要になった時だけ、各ドキュメントや成果物を読みます。

## 現在地

- 全体進捗: 約99%
- 本運用前の安定化: 実装完了寄り
- PCオフ運用: GitHub Actionsで実証済み
- 日次LINE通知: schedule実行で連続成功中
- 週次PDCA: workflow_dispatch成功確認済み

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

## 残タスク

1. 次回の日次クラウド実行確認
   - `Daily ETF LINE` が成功
   - LINEが届く
   - `data_source_status.csv` がartifactに含まれる

2. 初回の週次クラウドPDCA確認
   - `Weekly ETF PDCA` の手動実行は成功済み
   - 次回schedule実行が成功
   - 週次LINE要約が届く
   - `weekly_report` と `replay_pdca_report` がartifactに含まれる

3. 1週間運用後の実データ確認
   - `守れた / 破った / 保留`
   - DEFENSE日に買い急ぎを止められたか
   - CHECK BUYが実際に判断しやすかったか

## 継続改善候補

1. 通知文の継続観察
   - 次の買い候補の表示量
   - 売却/利確確認の表現
   - 1週間使って迷いが残った箇所

2. データソース強化
   - 現在はyfinance中心
   - 次段階で代替データソースや冗長化を検討

## 100%判定

以下を満たしたら、本運用準備は100%と判定します。

1. 平日の日次LINEがクラウドから届く
2. 土曜の週次PDCA LINEがクラウドから届く
3. 1週間分の自己確認が週次PDCAに反映される
4. `scripts/check_cloud_delivery.ps1 -DownloadLatestArtifact` で日次成果物を確認できる
5. `scripts/check_cloud_delivery.ps1 -Weekly -DownloadLatestArtifact` で週次成果物を確認できる

## 当面の最優先

新機能を増やさず、クラウド実行と自己確認ログを1週間観察する。
改善は週次PDCAでまとめて入れる。
