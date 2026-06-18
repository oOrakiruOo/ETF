# Theme ETF Rotation System v4.0

MASATO Tactical ETF Engine は、Core-Satellite戦略でテーマETFの買い候補、押し目待ち、利確候補、売却候補を判定する研究用システムです。

実際の売買発注は行いません。売買提案、通知文、検証、レポート作成までを担当し、最終判断と発注はMASATOが行います。

## 構成

- `config/`: ETFユニバース、テーマ対応、リスクルール、基本設定
- `src/`: データ取得、指標、スコア、リスク、シグナル、レポート
- `data/portfolio/portfolio.csv`: 保有ETF管理CSV
- `reports/daily/`: 日次レポート出力先
- `tests/`: pytestテスト

## セットアップ

```powershell
python -m pip install -r requirements.txt
```

このPCで `python` が見つからない場合は、Codex同梱Pythonを使えます。

```powershell
& 'C:\Users\ms-it\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install -r requirements.txt
```

## 日次レポート作成

```powershell
python -m src.main --refresh
```

2回目以降はキャッシュ済みCSVを使えます。

```powershell
python -m src.main
```

## バックテストとPDCA

10年バックテストを作成します。

```powershell
python -m src.main backtest
```

標準では `config/strategy_profiles.yaml` の `current_candidate` を使います。
別プロファイルで検証する場合は `--profile` を指定します。

```powershell
python -m src.main backtest --profile baseline
python -m src.main backtest --profile aggressive_watch
```

改善パラメータの総当たり検証を行います。

```powershell
python -m src.main optimize
```

勝ち筋周辺に絞り、モメンタム重視スコアも含めて再検証します。

```powershell
python -m src.main refine
```

最良候補を相場局面別に検証します。

```powershell
python -m src.main validate
```

弱点局面でどのETFを採用していたか監査します。

```powershell
python -m src.main audit
```

## 現在の実装段階

現在は「検証エンジンとルール改善フェーズ」です。

- 完了: 日次判定、10年バックテスト、総当たり検証、局面別検証、弱点局面の採用監査
- 完了: 暫定本命ルールの固定、保有CSV評価、通知候補レポート
- 進行中: 過剰最適化を避ける検証、週次PDCAの自動レポート化
- 次の実装候補: 保有ETFの売却/停止判定強化、通知先連携

2026-06-06時点の暫定本命は `config/strategy_profiles.yaml` の `current_candidate` です。

## 保有CSVと通知候補

保有ETFは `data/portfolio/portfolio.csv` に入力します。
日次レポート実行時に現在価格、時価、比率、含み損益を更新して表示します。
入力形式は `docs/portfolio_input_guide.md` を参照してください。
日次実行前に入力漏れや数値ミスだけを確認する場合は、以下を使います。

```powershell
python -m src.main portfolio-check
```

```powershell
python -m src.main daily
```

本運用前の日次一式をまとめて作る場合は、以下を使います。実売買は自動実行せず、最後にGO/HOLD判定まで出します。
毎日の確認手順は `docs/daily_operation_runbook.md` を参照してください。

```powershell
python -m src.main daily-ops
```

Windowsタスクスケジューラから実行する場合は、PowerShellラッパーを使います。
このラッパーはプロジェクト内の仮想環境Pythonを使い、Temp権限問題を避けるため `tmp/` を一時フォルダに設定します。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command daily-ops
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command daily
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command portfolio-check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command notification-summary
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command notification-plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command notification-packets
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command decision-sheet
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command mobile-summary
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command operations-status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command go-live-check
```

週次PDCAや軽量履歴再生も同じ入口から実行できます。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command weekly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command replay-quick
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command weekly-health
```

タスクスケジューラへ日次一括運用（daily-ops）・保有CSVチェック・日次・通知要約・通知配送計画・通知送信パケット・手動判断シート・日次ヘルスチェック・運用ステータス・本運用GO/HOLD判定・週次・軽量履歴再生・週次ヘルスチェックをまとめて登録する場合は、まずドライランで内容を確認します。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -DryRun
```

問題なければ以下で登録します。既存タスクを上書きする場合は `-Force` を付けます。
登録時はノートPC運用を想定し、バッテリー中でも開始・継続できるように電源条件を外します。
また、予定時刻にPCが使えなかった場合は、利用可能になった後に開始できるようにします。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -Force
```

LINE送信タスクも登録する場合は、LINE Messaging APIの送信先を設定した後で `-IncludeLineSummary` を付けます。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\register_scheduled_tasks.ps1 -Force -IncludeLineSummary
```

`daily-ops` では、以下も同時に作成します。手動判断CSVに未判断が残る場合、GO/HOLD判定は `HOLD` になります。

- `reports/daily/daily_report_YYYY-MM-DD.md`
- `reports/daily/notification_candidates_YYYY-MM-DD.md`
- `reports/daily/notification_summary_YYYY-MM-DD.md`
- `reports/daily/notification_delivery_plan_YYYY-MM-DD.md`
- `reports/daily/manual_decision_sheet_YYYY-MM-DD.md`
- `reports/daily/daily_health_YYYY-MM-DD.md`
- `reports/daily/operations_status_YYYY-MM-DD.md`
- `reports/daily/go_live_readiness_YYYY-MM-DD.md`
- `data/processed/decisions/manual_decision_sheet_YYYY-MM-DD.csv`
- `data/processed/notifications/notification_outbox_YYYY-MM-DD.jsonl`
- `data/processed/notifications/notification_packets_manual_immediate_YYYY-MM-DD.jsonl`
- `data/processed/notifications/notification_packets_daily_digest_YYYY-MM-DD.jsonl`
- `data/processed/notifications/notification_packets_archive_only_YYYY-MM-DD.jsonl`
- `data/processed/signals/signals_YYYY-MM-DD.csv`

携帯向けの短い要約を作る場合は、以下を使います。外部送信は行いません。

```powershell
python -m src.main mobile-summary
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command mobile-summary
```

LINEへ送信する場合は、LINE DevelopersでMessaging APIチャネルを作り、以下の環境変数を設定してから実行します。秘密値はリポジトリへ保存しません。

```powershell
$env:LINE_CHANNEL_ACCESS_TOKEN = "..."
$env:LINE_TO_USER_ID = "..."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command line-summary
```

通知アウトボックスは外部送信用のJSONLです。現時点では自動送信せず、LINE/Slack/メールなどへ渡す前の安全な中間ファイルとして使います。
送信前の要約だけを確認する場合は、以下を使います。

```powershell
python -m src.main notification-summary
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command notification-summary
```

通知候補を将来のLINE/Slack/メール連携へ渡す前に、配送先の計画だけを確認する場合は、以下を使います。外部送信は行いません。

```powershell
python -m src.main notification-plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command notification-plan
```

配送先別のJSONLパケットを作る場合は、以下を使います。これも外部送信は行いません。

```powershell
python -m src.main notification-packets
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command notification-packets
```

通知計画から手動判断シートを作る場合は、以下を使います。`判断`、`数量`、`指値`、`実行価格`、`実行時刻`、`メモ` を記録し、後続PDCAの実績ログとして使います。

```powershell
python -m src.main decision-sheet
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command decision-sheet
```

日次成果物が揃ったかだけを確認する場合は、以下を使います。

```powershell
python -m src.main daily-health
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command daily-health
```

日次・週次成果物が止まっていないかをまとめて確認する場合は、以下を使います。

```powershell
python -m src.main operations-status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command operations-status
```

本運用に進む前のGO/HOLD判定を確認する場合は、以下を使います。`GO（手動確認後）` でも実売買は自動実行せず、日次レポートと通知計画を確認してから判断します。

```powershell
python -m src.main go-live-check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command go-live-check
```

週次PDCA成果物が揃ったかだけを確認する場合は、以下を使います。

```powershell
python -m src.main weekly-health
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command weekly-health
```

週次レポートでは、保存済みの日次シグナルを読み込み、1営業日後・5営業日後・20営業日後のフォワードリターンを評価します。

```powershell
python -m src.main weekly
```

週次実行では、以下も作成します。

- `reports/weekly/weekly_report_YYYY-MM-DD.md`
- `data/processed/pdca/weekly_action_items_YYYY-MM-DD.csv`
- `data/processed/signals/signal_forward_returns_YYYY-MM-DD.csv`
- `data/processed/signals/virtual_trades_YYYY-MM-DD.csv`
- `data/processed/signals/avoid_outcomes_YYYY-MM-DD.csv`

週次PDCAでは、買い系シグナルを第1買い価格・保守目標・停止価格で仮想検証します。
見送り・売却候補・リスク削減判定は、20営業日後に回避が正しかったかを記録します。
どちらも実売買ではなく、ルール改善用の検証ログです。
前回の `weekly_action_items_YYYY-MM-DD.csv` に未完了の項目がある場合は、次回の週次レポートの「前回Act確認」に表示されます。
完了した項目はCSVの `status` を `done` または `closed` に変更すると、次回レポートの未完了一覧から外れます。

過去データ上で月次シグナルを復元し、仮想売買と見送り評価をすぐ確認する場合は以下を実行します。

```powershell
python -m src.main replay
```

日常PDCAでは、重いハイブリッド総当たりを省いた軽量版を使えます。

```powershell
python -m src.main replay-quick
```

履歴再生では、以下を作成します。

- `reports/weekly/replay_pdca_report_YYYY-MM-DD.md`
- `data/processed/signals/historical_signals_YYYY-MM-DD.csv`
- `data/processed/signals/replay_virtual_trades_YYYY-MM-DD.csv`
- `data/processed/signals/replay_avoid_outcomes_YYYY-MM-DD.csv`
- `data/processed/signals/replay_entry_parameter_search_YYYY-MM-DD.csv`
- `data/processed/signals/replay_avoid_by_signal_YYYY-MM-DD.csv`
- `data/processed/signals/replay_avoid_policy_search_YYYY-MM-DD.csv`
- `data/processed/signals/signal_execution_backtest_YYYY-MM-DD.csv`
- `data/processed/signals/signal_execution_diagnostics_YYYY-MM-DD.csv`
- `data/processed/signals/signal_execution_grid_YYYY-MM-DD.csv`
- `data/processed/signals/hybrid_rotation_signal_backtest_YYYY-MM-DD.csv`
- `data/processed/signals/hybrid_theme_risk_mode_search_YYYY-MM-DD.csv`
- `data/processed/signals/theme_risk_policy_mode_search_YYYY-MM-DD.csv`

テーマ交代リスクの防御強度は `config/settings.yaml` の `theme_risk.overlay_mode` で切り替えます。

- `off`: テーマリスク抑制なし
- `high_only`: 高リスクだけ買い/押し目を止める
- `balanced`: 高リスクは停止、中リスクは一段弱める
- `strict`: 中リスクもより強く弱める

2026-06-07時点では、過剰抑制チェックの結果を受けて `high_only` を本運用前候補にしています。

日次シグナルと履歴再生の第1買い・停止価格は、`config/settings.yaml` の `trade_plan` で調整します。
2026-06-07時点では、履歴再生PDCAの買い価格候補を反映して `entry_multiplier: 1.04`、`stop_multiplier: 0.95` を使用します。

見送り・売却候補の回避成否評価は `config/settings.yaml` の `pdca.avoid_policy` で切り替えます。
2026-06-07時点では、見送りを監視扱いに寄せ、売却候補だけを主な回避評価対象にする `sell_only` を本運用前候補にしています。

- `data/processed/signals/hybrid_rotation_signal_diagnostics_YYYY-MM-DD.csv`
- `data/processed/signals/hybrid_rotation_signal_grid_YYYY-MM-DD.csv`
- `data/processed/signals/hybrid_rotation_signal_regime_validation_YYYY-MM-DD.csv`
- `data/processed/signals/hybrid_entry_guard_search_YYYY-MM-DD.csv`
- `data/processed/signals/hybrid_acceleration_mode_search_YYYY-MM-DD.csv`

`replay_entry_parameter_search` は、第1買い価格と停止価格の候補を振って、約定率・勝率・平均損益を比較します。
`replay_avoid_policy_search` は、見送り・売却候補・リスク削減をどこまで回避対象にするかを比較します。
`signal_execution_backtest` は、Coreを持ちながらSatellite枠だけを買い系シグナルで仮想運用します。
`hybrid_rotation_signal_backtest` は、月次ローテーション本体を維持しながら、Satellite枠の一部だけを買い系シグナルへ一時配分する統合検証です。
`hybrid_rotation_signal_grid` は、厳格な買い系シグナルだけでなく、ETFスコア・テーマスコア・RRで見送り候補を救う緩和ポリシーも比較します。
`replay` 内のハイブリッド総当たりは、直近PDCAで有望だった範囲を重点探索します。2024年AI加速局面の取りこぼし確認のため、2026-06-07時点では高スコア候補の `RR >= 1.0` も探索対象に含めます。
フル `replay` はハイブリッド総当たりを含むため、日常確認は `replay-quick`、本命候補の再確認は `replay` を使います。
2026-06-07の再検証では、`score >= 65` まで緩めると2024年のSMH/SOXX候補は拾えますが、最大DDが悪化したため本命候補にはせず、`score >= 70` とURA補助制限を優先します。
追加の軽量検証では、全体条件は `score >= 70 / RR >= 1.0` のまま維持し、SMH/SOXXだけ `score >= 65 / RR >= 1.0` まで限定緩和すると、最大DDを悪化させずに年率が改善しました。この限定緩和を本運用前候補として追跡します。
局面別の軽量確認では、2024年AI加速局面の現行比が `-2.88%` から `-2.39%` に改善しましたが、まだ最弱局面として残るため、完全解消ではなく段階的改善として扱います。
`hybrid_rotation_signal_regime_validation` は、ハイブリッド案を相場局面別に分解して、現行月次ローテーションとの差を確認します。
`hybrid_entry_guard_search` は、急落日に即エントリーしないガードが成績改善につながるかを確認します。
`hybrid_acceleration_mode_search` は、強い上昇トレンド局面で補助シグナルを通常運用・半減・停止する案を比較します。
この結果は次回バックテスト候補であり、即時の正式ルール変更ではありません。

## 検証

```powershell
python -m pytest
```

## 注意

- yfinanceは研究用途の初期データソースです。
- 自動発注機能は実装しません。
- ルール変更はバックテスト後に行う前提です。
