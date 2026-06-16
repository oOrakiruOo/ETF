# 保有CSV入力ガイド

実保有は `data/portfolio/portfolio.csv` に入力します。このファイルはGit管理外です。

## 必須列

- `ticker`: ETFティッカー。例: `QQQ`
- `quantity`: 保有数量。0より大きい数値
- `avg_price`: 平均取得単価。0より大きい数値

## 推奨列

- `theme`: テーマ名。例: `Core`, `半導体`
- `current_price`: 空でも可。日次実行時に取得価格で更新
- `stop_price`: 停止価格。未入力ならWarning
- `target_price`: 目標価格。未入力ならWarning
- `entry_date`: 取得日
- `thesis`: 保有理由
- `status`: 例: `active`

## テンプレート

```csv
ticker,theme,quantity,avg_price,current_price,market_value,weight_pct,unrealized_pnl,unrealized_pnl_pct,entry_date,thesis,stop_price,target_price,status
QQQ,Core,1,500,,,,,,2026-06-16,Core growth exposure,460,580,active
SMH,半導体,1,250,,,,,,2026-06-16,AI semiconductor momentum,225,310,active
```

## 入力後の確認

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Codex\theme-etf-rotation-system-v4-0\scripts\run_workflow.ps1 -Command portfolio-check
```

`portfolio_check_YYYY-MM-DD.md` が `確認OK` なら、日次レポートへ反映できます。
