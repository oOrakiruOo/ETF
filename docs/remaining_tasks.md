# Remaining tasks

このファイルは、残タスクだけを短く管理するための一覧です。
詳細確認は必要になった時だけ、各ドキュメントや成果物を読みます。

## 現在地

- 全体進捗: 約98%
- 本運用前の安定化: 完了寄り
- PCオフ運用: GitHub Actionsで実証済み
- 日次LINE通知: schedule実行で連続成功中

## 完了済み

- 日次レポート
- 判断ブリーフ
- LINEブロードキャスト
- LINE送信ログ
- Windowsタスク運用
- GitHub ActionsによるPCオフ運用
- 失敗時LINE通知
- システム概要書
- ユーザー向け日次ガイド
- Codex用最短MAP

## 残タスク

1. 週次PDCAのクラウド移行
   - 現在は日次LINEがActions対応済み
   - 週次レポート、週次ヘルス、replay-quickをActions化するか検討

2. Actions artifact確認手順の実運用化
   - `scripts/check_cloud_delivery.ps1 -DownloadLatestArtifact` で取得可能
   - 取得後に何を見るかをさらに短くする余地あり

3. 1週間運用後のPDCA確認
   - `守れた / 破った / 保留`
   - DEFENSE日に買い急ぎを止められたか
   - CHECK BUYが実際に判断しやすかったか

4. 通知文の微調整
   - LINE先頭の分かりやすさ
   - 次の買い候補の表示量
   - 売却/利確確認の表現

5. データソース強化
   - 現在はyfinance中心
   - 将来的に代替データソースや冗長化を検討

## 当面の最優先

1週間は大きな仕様変更を増やさず、日次通知を受けて行動できたかを観察する。
改善は週次PDCAでまとめて入れる。
