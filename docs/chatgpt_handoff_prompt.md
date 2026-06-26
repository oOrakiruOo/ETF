# ChatGPT handoff prompt

PC版ChatGPTでこのシステムについて相談する時は、下のプロンプトを貼り付けます。
Codex側で大量のファイルを読ませず、ChatGPTに方針整理や文章改善を任せるためのものです。

```text
あなたはETF Rotation Systemのレビュー補助です。

このシステムは、コア資産とサテライトETFの買い時・待機・保有確認を支援する日次判断システムです。
売買は自動実行しません。最終判断はユーザーが行います。

中核価値は「買い候補を探す」ことだけではなく、
個人投資家がやりがちな飛びつき買い・ナンピン・焦り売買を抑えることです。
特にDEFENSEの日に「何もしない」と言えることを重視しています。

対象:
- コア: 401k外国株式インデックス、NISAオルカン、VT、VTI、SPY、QQQ
- サテライト: 半導体、AI、サイバー、インフラ、防衛、エネルギー、金融、ヘルスケアなどのETF
- 参考保有: TDK、SOFI。ETF信号だけでは買い増ししない

LINE通知の行動ラベル:
- DEFENSE: 新規買い禁止、ナンピン禁止、積立だけ
- WAIT: 何もしない
- CHECK BUY: 買い候補を手動確認。即買いではない
- CHECK SELL: 利確/売却候補を確認。買い増しではない

現在の運用:
- GitHub ActionsでPCオフ運用済み
- 平日07:55頃に daily-ops --refresh と line-broadcast-decision-brief を実行
- LINE送信HTTP 200確認済み
- schedule実行も複数日成功
- 失敗時LINE通知あり

主なドキュメント:
- docs/system_overview.md: 全体像
- docs/user_daily_guide.md: 毎朝の使い方
- docs/cloud_operation_plan.md: PCオフ運用
- docs/remaining_tasks.md: 残タスク

相談したいこと:
1. このシステムがユーザーの目的「コア資産を守りつつ、サテライトETFで無理なく上乗せを狙う」に沿っているか
2. LINE通知文が意思決定支援として分かりやすいか
3. 商品化を考えた時に、表に出すべき情報と隠すべき指標は何か
4. DEFENSE/WAIT/CHECK BUY/CHECK SELLの表現改善案
5. 1週間運用後のPDCAで見るべき指標

投資助言ではなく、意思決定支援UI・運用設計・文章設計の観点でレビューしてください。
```
 
## Codexへの戻し方

ChatGPTで得た改善案は、以下の形でCodexへ渡すとトークン消費を抑えられます。

```text
今回の作業範囲は1点だけ。
対象ファイル:
docs/user_daily_guide.md

目的:
DEFENSEの日の説明を、よりユーザーが行動しやすい表現に直す。

制約:
- コードは変更しない
- 他ファイルは変更しない
- 変更後にpytestは不要
- 最後に差分概要だけ報告
```
