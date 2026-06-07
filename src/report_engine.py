from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .utils import PROJECT_ROOT, ensure_dir


DISPLAY_COLUMNS = [
    "ETF",
    "テーマ",
    "ETFスコア",
    "テーマスコア",
    "テーマリスク",
    "テーマリスクスコア",
    "ステージ",
    "現在価格",
    "第1買い",
    "第1買いまで%",
    "第2買い",
    "第3買い",
    "保守目標",
    "強気目標",
    "停止価格",
    "RR",
    "判定",
    "テーマリスク理由",
    "テーマ予防策",
]


def build_signal_table(rows: list[dict[str, object]]) -> pd.DataFrame:
    table = pd.DataFrame(rows)
    if table.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    return table.loc[:, DISPLAY_COLUMNS].sort_values(["ETFスコア", "テーマスコア"], ascending=False)


def write_daily_report(
    signal_table: pd.DataFrame,
    theme_scores: dict[str, float],
    allocation_text: str = "Core 60% / Satellite 25% / Cash 15%",
    portfolio: pd.DataFrame | None = None,
    theme_risk_table: pd.DataFrame | None = None,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"daily_report_{date:%Y-%m-%d}.md"
    buy_candidates = signal_table[signal_table["判定"].isin(["強気買い候補", "買い候補"])]
    watch = signal_table[signal_table["判定"].eq("押し目待ち")]
    profit = signal_table[signal_table["判定"].eq("利確候補")]
    sell = signal_table[signal_table["判定"].eq("売却候補")]
    theme_ranking = pd.DataFrame(
        [{"テーマ": theme, "テーマスコア": score} for theme, score in theme_scores.items()]
    ).sort_values("テーマスコア", ascending=False)
    portfolio_table = "保有なし"
    if portfolio is not None and not portfolio.empty:
        visible_columns = [
            "ticker",
            "theme",
            "quantity",
            "avg_price",
            "current_price",
            "market_value",
            "weight_pct",
            "unrealized_pnl_pct",
            "stop_price",
            "target_price",
            "status",
            "portfolio_action",
            "portfolio_reason",
        ]
        existing_columns = [column for column in visible_columns if column in portfolio.columns]
        portfolio_table = portfolio.loc[:, existing_columns].to_markdown(index=False)
    theme_risk_text = "評価なし"
    if theme_risk_table is not None and not theme_risk_table.empty:
        risk_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"theme_rotation_risks_{date:%Y-%m-%d}.csv"
        risk_path.parent.mkdir(parents=True, exist_ok=True)
        theme_risk_table.to_csv(risk_path, index=False)
        theme_risk_text = theme_risk_table.head(15).to_markdown(index=False)
    content = [
        f"# daily_report {date:%Y-%m-%d}",
        "",
        "## 1. 今日の市場ステージ",
        "自動判定の初期版です。QQQ/SPYと対象ETFの相対強度をもとに、個別ETFのステージを確認してください。",
        "",
        "## 2. Core/Satellite/Cash推奨比率",
        f"{allocation_text} を現在の検証済み候補として使います。ドローダウン条件に達した場合はSatelliteを縮小します。",
        "",
        "## 3. テーマスコアランキング",
        theme_ranking.to_markdown(index=False),
        "",
        "## 4. ETFスコアランキング",
        signal_table.to_markdown(index=False),
        "",
        "## 5. 買い候補",
        buy_candidates.to_markdown(index=False) if not buy_candidates.empty else "該当なし",
        "",
        "## 6. 押し目待ち",
        watch.to_markdown(index=False) if not watch.empty else "該当なし",
        "",
        "## 7. 利確候補",
        profit.to_markdown(index=False) if not profit.empty else "該当なし",
        "",
        "## 8. 売却候補",
        sell.to_markdown(index=False) if not sell.empty else "該当なし",
        "",
        "## 9. 保有ETF評価",
        portfolio_table,
        "",
        "## 10. テーマ交代リスクと予防策",
        theme_risk_text,
        "",
        "## 11-13. 価格差・目標価格・RR・今日やること",
        "上表の第1買いまで%、保守目標、強気目標、停止価格、RRを確認し、条件到達時のみMASATOが最終判断します。",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_signal_snapshot(
    signal_table: pd.DataFrame,
    output_dir: str | Path = "data/processed/signals",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"signals_{date:%Y-%m-%d}.csv"
    signal_table.to_csv(output_path, index=False)
    return output_path


def write_notification_report(
    notifications: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"notification_candidates_{date:%Y-%m-%d}.md"
    if notifications.empty:
        notification_text = "通知候補なし"
    else:
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        sorted_notifications = notifications.copy()
        sorted_notifications["_priority_rank"] = sorted_notifications["優先度"].map(priority_order).fillna(9)
        sorted_notifications = sorted_notifications.sort_values(["_priority_rank", "ETF"]).drop(columns=["_priority_rank"])
        sections = []
        for priority, title in [("High", "High: 今日すぐ確認"), ("Medium", "Medium: 監視強化"), ("Low", "Low: 参考")]:
            subset = sorted_notifications[sorted_notifications["優先度"].eq(priority)]
            sections.extend(
                [
                    f"## {title}",
                    subset.to_markdown(index=False) if not subset.empty else "該当なし",
                    "",
                ]
            )
        notification_text = "\n".join(sections).strip()
    content = [
        f"# 通知候補 {date:%Y-%m-%d}",
        "",
        "実売買発注は行いません。MASATOの最終判断用アラート候補です。",
        "",
        notification_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_notification_summary_report(
    priority_counts: pd.DataFrame,
    notification_summary: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"notification_summary_{date:%Y-%m-%d}.md"
    counts_text = priority_counts.to_markdown(index=False) if not priority_counts.empty else "通知候補なし"
    summary_text = notification_summary.to_markdown(index=False) if not notification_summary.empty else "通知候補なし"
    content = [
        f"# notification_summary {date:%Y-%m-%d}",
        "",
        "通知アウトボックスを送信前に確認するための要約です。外部送信は行いません。",
        "",
        "## 優先度別件数",
        counts_text,
        "",
        "## 送信前確認リスト",
        summary_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_portfolio_check_report(
    issues: pd.DataFrame,
    output_dir: str | Path = "reports/daily",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"portfolio_check_{date:%Y-%m-%d}.md"
    if issues.empty:
        issues_text = "評価なし"
    else:
        issues_text = issues.to_markdown(index=False)
    has_error = not issues.empty and issues["severity"].eq("Error").any()
    status_text = "要修正" if has_error else "確認OK"
    content = [
        f"# portfolio_check {date:%Y-%m-%d}",
        "",
        f"判定: {status_text}",
        "",
        "日次レポート前に、保有CSVの入力漏れや数値ミスを確認します。",
        "",
        issues_text,
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_weekly_pdca_report(
    backtest_summary: pd.DataFrame,
    parameter_results: pd.DataFrame,
    regime_validation: pd.DataFrame,
    signal_history: pd.DataFrame | None = None,
    signal_accuracy: pd.DataFrame | None = None,
    evaluated_signals: pd.DataFrame | None = None,
    signal_improvement_proposals: list[str] | None = None,
    virtual_trades: pd.DataFrame | None = None,
    virtual_trade_summary: pd.DataFrame | None = None,
    avoid_outcomes: pd.DataFrame | None = None,
    avoid_summary: pd.DataFrame | None = None,
    avoid_policy_name: str = "current_all_avoid",
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"weekly_report_{date:%Y-%m-%d}.md"
    if evaluated_signals is not None and not evaluated_signals.empty:
        evaluated_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"signal_forward_returns_{date:%Y-%m-%d}.csv"
        evaluated_path.parent.mkdir(parents=True, exist_ok=True)
        evaluated_signals.to_csv(evaluated_path, index=False)
    if virtual_trades is not None:
        virtual_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"virtual_trades_{date:%Y-%m-%d}.csv"
        virtual_path.parent.mkdir(parents=True, exist_ok=True)
        virtual_trades.to_csv(virtual_path, index=False)
    if avoid_outcomes is not None:
        avoid_path = PROJECT_ROOT / "data" / "processed" / "signals" / f"avoid_outcomes_{date:%Y-%m-%d}.csv"
        avoid_path.parent.mkdir(parents=True, exist_ok=True)
        avoid_outcomes.to_csv(avoid_path, index=False)
    best_parameters = parameter_results.head(5) if not parameter_results.empty else pd.DataFrame()
    weak_regimes = (
        regime_validation.sort_values("vs_qqq_pct").head(3)
        if not regime_validation.empty and "vs_qqq_pct" in regime_validation.columns
        else pd.DataFrame()
    )
    action_items = []
    signal_text = "シグナル履歴なし"
    if signal_history is not None and not signal_history.empty:
        signal_counts = signal_history["判定"].value_counts().reset_index()
        signal_counts.columns = ["判定", "件数"]
        signal_text = signal_counts.to_markdown(index=False)
    accuracy_text = "判定精度データなし"
    if signal_accuracy is not None and not signal_accuracy.empty:
        accuracy_text = signal_accuracy.to_markdown(index=False)
    virtual_summary_text = "仮想売買ログなし"
    virtual_detail_text = "仮想売買ログなし"
    if virtual_trade_summary is not None and not virtual_trade_summary.empty:
        virtual_summary_text = virtual_trade_summary.to_markdown(index=False)
    if virtual_trades is not None and not virtual_trades.empty:
        virtual_detail_text = virtual_trades.tail(20).to_markdown(index=False)
    avoid_summary_text = "見送り評価ログなし"
    avoid_detail_text = "見送り評価ログなし"
    if avoid_summary is not None and not avoid_summary.empty:
        avoid_summary_text = avoid_summary.to_markdown(index=False)
    if avoid_outcomes is not None and not avoid_outcomes.empty:
        avoid_detail_text = avoid_outcomes.tail(20).to_markdown(index=False)
    if not best_parameters.empty:
        best = best_parameters.iloc[0]
        action_items.append(
            f"暫定候補は {best.get('score_profile', 'balanced')} / Satellite {float(best['satellite_weight_pct']):.0f}% / "
            f"上位{int(best['top_satellites'])} / DD停止 {float(best['drawdown_stop_pct']):.0f}%"
        )
    if not weak_regimes.empty:
        action_items.append("弱点局面のETF採用ログを確認し、半導体/AIの取り逃がし原因を継続監査")
    if backtest_summary.empty:
        action_items.append("バックテストサマリー未作成。`python -m src.main backtest` を実行")
    if signal_improvement_proposals:
        action_items.extend(signal_improvement_proposals)
    content = [
        f"# weekly_report {date:%Y-%m-%d}",
        "",
        "## 1. 今週の判定精度",
        "売買実績CSV未連携のため損益精度は未評価です。現段階ではシグナル分布を記録します。",
        "",
        signal_text,
        "",
        "### フォワードリターン評価",
        accuracy_text,
        "",
        "### 仮想売買ログ",
        virtual_summary_text,
        "",
        virtual_detail_text,
        "",
        "### 見送り・リスク削減の評価",
        f"現在の回避評価方針: `{avoid_policy_name}`",
        "",
        avoid_summary_text,
        "",
        avoid_detail_text,
        "",
        "## 2. ベンチマーク比較",
        backtest_summary.to_markdown(index=False) if not backtest_summary.empty else "バックテストサマリーなし",
        "",
        "## 3. 保有ETFの評価",
        "日次レポートの保有ETF評価セクションを参照してください。",
        "",
        "## 4. 来週の買い候補",
        "日次レポートの買い候補・押し目待ちを優先確認してください。",
        "",
        "## 5. 来週の売却候補",
        "日次レポートの売却候補と通知候補を優先確認してください。",
        "",
        "## 6. 改善提案",
        best_parameters.to_markdown(index=False) if not best_parameters.empty else "改善パラメータ結果なし",
        "",
        "## 7. バックテスト更新",
        "最新の10年バックテスト、総当たり、局面別検証を反映済みです。",
        "",
        "## PDCA: Act",
        *[f"- {item}" for item in action_items],
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_replay_pdca_report(
    signal_history: pd.DataFrame,
    signal_accuracy: pd.DataFrame,
    virtual_trades: pd.DataFrame,
    virtual_trade_summary: pd.DataFrame,
    avoid_outcomes: pd.DataFrame,
    avoid_summary: pd.DataFrame,
    entry_parameter_results: pd.DataFrame | None = None,
    avoid_by_signal: pd.DataFrame | None = None,
    avoid_policy_results: pd.DataFrame | None = None,
    signal_execution_summary: pd.DataFrame | None = None,
    signal_execution_diagnostics: pd.DataFrame | None = None,
    signal_execution_grid: pd.DataFrame | None = None,
    hybrid_summary: pd.DataFrame | None = None,
    hybrid_diagnostics: pd.DataFrame | None = None,
    hybrid_grid: pd.DataFrame | None = None,
    hybrid_regime_validation: pd.DataFrame | None = None,
    hybrid_entry_guard_results: pd.DataFrame | None = None,
    hybrid_acceleration_mode_results: pd.DataFrame | None = None,
    hybrid_ticker_rule_results: pd.DataFrame | None = None,
    hybrid_theme_risk_mode_results: pd.DataFrame | None = None,
    theme_risk_overlay_comparison: pd.DataFrame | None = None,
    relaxed_theme_risk_overlay_comparison: pd.DataFrame | None = None,
    theme_risk_policy_mode_results: pd.DataFrame | None = None,
    theme_risk_overlay_blocks: pd.DataFrame | None = None,
    relaxed_theme_risk_overlay_blocks: pd.DataFrame | None = None,
    hybrid_trade_log: pd.DataFrame | None = None,
    hybrid_attribution_2024: pd.DataFrame | None = None,
    trade_plan_multipliers: dict[str, float] | None = None,
    avoid_policy_name: str = "current_all_avoid",
    output_dir: str | Path = "reports/weekly",
    processed_output_dir: str | Path | None = None,
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    output_path = PROJECT_ROOT / directory / f"replay_pdca_report_{date:%Y-%m-%d}.md"
    processed_dir = ensure_dir(processed_output_dir or "data/processed/signals")
    signal_path = processed_dir / f"historical_signals_{date:%Y-%m-%d}.csv"
    forward_path = processed_dir / f"replay_signal_accuracy_{date:%Y-%m-%d}.csv"
    virtual_path = processed_dir / f"replay_virtual_trades_{date:%Y-%m-%d}.csv"
    avoid_path = processed_dir / f"replay_avoid_outcomes_{date:%Y-%m-%d}.csv"
    entry_search_path = processed_dir / f"replay_entry_parameter_search_{date:%Y-%m-%d}.csv"
    avoid_by_signal_path = processed_dir / f"replay_avoid_by_signal_{date:%Y-%m-%d}.csv"
    avoid_policy_path = processed_dir / f"replay_avoid_policy_search_{date:%Y-%m-%d}.csv"
    signal_execution_path = processed_dir / f"signal_execution_backtest_{date:%Y-%m-%d}.csv"
    signal_execution_diag_path = processed_dir / f"signal_execution_diagnostics_{date:%Y-%m-%d}.csv"
    signal_execution_grid_path = processed_dir / f"signal_execution_grid_{date:%Y-%m-%d}.csv"
    hybrid_path = processed_dir / f"hybrid_rotation_signal_backtest_{date:%Y-%m-%d}.csv"
    hybrid_diag_path = processed_dir / f"hybrid_rotation_signal_diagnostics_{date:%Y-%m-%d}.csv"
    hybrid_grid_path = processed_dir / f"hybrid_rotation_signal_grid_{date:%Y-%m-%d}.csv"
    hybrid_regime_path = processed_dir / f"hybrid_rotation_signal_regime_validation_{date:%Y-%m-%d}.csv"
    hybrid_entry_guard_path = processed_dir / f"hybrid_entry_guard_search_{date:%Y-%m-%d}.csv"
    hybrid_acceleration_mode_path = processed_dir / f"hybrid_acceleration_mode_search_{date:%Y-%m-%d}.csv"
    hybrid_ticker_rule_path = processed_dir / f"hybrid_ticker_rule_search_{date:%Y-%m-%d}.csv"
    hybrid_theme_risk_mode_path = processed_dir / f"hybrid_theme_risk_mode_search_{date:%Y-%m-%d}.csv"
    theme_risk_overlay_path = processed_dir / f"theme_risk_overlay_comparison_{date:%Y-%m-%d}.csv"
    relaxed_theme_risk_overlay_path = processed_dir / f"relaxed_theme_risk_overlay_comparison_{date:%Y-%m-%d}.csv"
    theme_risk_policy_mode_path = processed_dir / f"theme_risk_policy_mode_search_{date:%Y-%m-%d}.csv"
    theme_risk_blocks_path = processed_dir / f"theme_risk_overlay_blocks_{date:%Y-%m-%d}.csv"
    relaxed_theme_risk_blocks_path = processed_dir / f"relaxed_theme_risk_overlay_blocks_{date:%Y-%m-%d}.csv"
    hybrid_trade_log_path = processed_dir / f"hybrid_trade_log_{date:%Y-%m-%d}.csv"
    hybrid_attribution_2024_path = processed_dir / f"hybrid_attribution_2024_{date:%Y-%m-%d}.csv"
    signal_history.to_csv(signal_path, index=False)
    signal_accuracy.to_csv(forward_path, index=False)
    virtual_trades.to_csv(virtual_path, index=False)
    avoid_outcomes.to_csv(avoid_path, index=False)
    if entry_parameter_results is not None:
        entry_parameter_results.to_csv(entry_search_path, index=False)
    if avoid_by_signal is not None:
        avoid_by_signal.to_csv(avoid_by_signal_path, index=False)
    if avoid_policy_results is not None:
        avoid_policy_results.to_csv(avoid_policy_path, index=False)
    if signal_execution_summary is not None:
        signal_execution_summary.to_csv(signal_execution_path, index=False)
    if signal_execution_diagnostics is not None:
        signal_execution_diagnostics.to_csv(signal_execution_diag_path, index=False)
    if signal_execution_grid is not None:
        signal_execution_grid.to_csv(signal_execution_grid_path, index=False)
    if hybrid_summary is not None:
        hybrid_summary.to_csv(hybrid_path, index=False)
    if hybrid_diagnostics is not None:
        hybrid_diagnostics.to_csv(hybrid_diag_path, index=False)
    if hybrid_grid is not None:
        hybrid_grid.to_csv(hybrid_grid_path, index=False)
    if hybrid_regime_validation is not None:
        hybrid_regime_validation.to_csv(hybrid_regime_path, index=False)
    if hybrid_entry_guard_results is not None:
        hybrid_entry_guard_results.to_csv(hybrid_entry_guard_path, index=False)
    if hybrid_acceleration_mode_results is not None:
        hybrid_acceleration_mode_results.to_csv(hybrid_acceleration_mode_path, index=False)
    if hybrid_ticker_rule_results is not None:
        hybrid_ticker_rule_results.to_csv(hybrid_ticker_rule_path, index=False)
    if hybrid_theme_risk_mode_results is not None:
        hybrid_theme_risk_mode_results.to_csv(hybrid_theme_risk_mode_path, index=False)
    if theme_risk_overlay_comparison is not None:
        theme_risk_overlay_comparison.to_csv(theme_risk_overlay_path, index=False)
    if relaxed_theme_risk_overlay_comparison is not None:
        relaxed_theme_risk_overlay_comparison.to_csv(relaxed_theme_risk_overlay_path, index=False)
    if theme_risk_policy_mode_results is not None:
        theme_risk_policy_mode_results.to_csv(theme_risk_policy_mode_path, index=False)
    if theme_risk_overlay_blocks is not None:
        theme_risk_overlay_blocks.to_csv(theme_risk_blocks_path, index=False)
    if relaxed_theme_risk_overlay_blocks is not None:
        relaxed_theme_risk_overlay_blocks.to_csv(relaxed_theme_risk_blocks_path, index=False)
    if hybrid_trade_log is not None:
        hybrid_trade_log.to_csv(hybrid_trade_log_path, index=False)
    if hybrid_attribution_2024 is not None:
        hybrid_attribution_2024.to_csv(hybrid_attribution_2024_path, index=False)

    trade_plan_settings = trade_plan_multipliers or {
        "entry_multiplier": 1.0,
        "stop_multiplier": 1.0,
        "target_multiplier": 1.0,
    }
    trade_plan_settings_text = "\n".join(
        [
            f"- 第1買い倍率: x{float(trade_plan_settings.get('entry_multiplier', 1.0)):.2f}",
            f"- 停止価格倍率: x{float(trade_plan_settings.get('stop_multiplier', 1.0)):.2f}",
            f"- 目標価格倍率: x{float(trade_plan_settings.get('target_multiplier', 1.0)):.2f}",
            "- 買い価格・停止価格の総当たりは、上記設定反映後の価格に対する追加検証倍率です。",
        ]
    )

    signal_counts = "履歴シグナルなし"
    theme_risk_signal_counts = "テーマリスク列なし"
    if not signal_history.empty:
        counts = signal_history["判定"].value_counts().reset_index()
        counts.columns = ["判定", "件数"]
        signal_counts = counts.to_markdown(index=False)
        if {"テーマリスク", "判定"}.issubset(signal_history.columns):
            risk_counts = (
                signal_history.groupby(["テーマリスク", "判定"])
                .size()
                .reset_index(name="件数")
                .sort_values(["テーマリスク", "件数"], ascending=[True, False])
            )
            theme_risk_signal_counts = risk_counts.to_markdown(index=False)
    action_items: list[str] = []
    if not virtual_trade_summary.empty:
        summary_row = virtual_trade_summary.iloc[0]
        filled = float(summary_row.get("約定件数", 0.0) or 0.0)
        total = float(summary_row.get("対象件数", 0.0) or 0.0)
        average_return = summary_row.get("平均損益%", None)
        fill_rate = filled / total * 100 if total > 0 else 0.0
        if pd.notna(average_return) and float(average_return) < 0:
            action_items.append("買い系シグナルの仮想損益がマイナス。第1買い条件、停止価格、目標価格を次回パラメータ検証で再調整")
        if total > 0 and fill_rate < 40:
            action_items.append("第1買い未到達が多い。押し目待ち価格が深すぎないか、約定率とリスクのバランスを検証")
    if not avoid_summary.empty:
        avoid_row = avoid_summary.iloc[0]
        accuracy = avoid_row.get("正解率", None)
        average_avoid_return = avoid_row.get("平均20日後リターン%", None)
        if pd.notna(accuracy) and float(accuracy) < 50:
            action_items.append("見送り・売却候補の正解率が50%未満。上昇局面では売却候補を即売りではなく監視/リスク削減に弱める案を検証")
        if pd.notna(average_avoid_return) and float(average_avoid_return) > 0:
            action_items.append("回避後の平均リターンがプラス。過熱控除とテーマスコア60割れの売却判定が強すぎないか確認")
    if not action_items:
        action_items.append("履歴再生では大きな偏りなし。日次シグナル蓄積と週次評価を継続")
    if entry_parameter_results is not None and not entry_parameter_results.empty:
        best = entry_parameter_results.iloc[0]
        action_items.append(
            f"買い価格追加検証候補: 第1買いx{float(best['entry_multiplier']):.2f} / 停止価格x{float(best['stop_multiplier']):.2f} を次回バックテスト候補に追加"
        )
    if avoid_policy_results is not None and not avoid_policy_results.empty:
        best_policy = avoid_policy_results.iloc[0]
        action_items.append(f"回避方針候補: {best_policy['policy']} を売却/見送りルール検証候補に追加")
    if signal_execution_summary is not None and not signal_execution_summary.empty:
        signal_row = signal_execution_summary[signal_execution_summary["strategy"].eq("MASATO Signal Execution")]
        if not signal_row.empty:
            signal_annual = float(signal_row.iloc[0]["annual_return_pct"])
            action_items.append(f"シグナル実行BT: 年率{signal_annual:.2f}% を確認。月次ローテーション本体との統合可否を次回検証")
    if signal_execution_grid is not None and not signal_execution_grid.empty:
        best_signal = signal_execution_grid.iloc[0]
        action_items.append(
            f"補助シグナル候補: entry x{float(best_signal['entry_multiplier']):.2f} / stop x{float(best_signal['stop_multiplier']):.2f} / 保有{int(best_signal['max_holding_days'])}日 / {int(best_signal['max_positions'])}枠"
        )
    if hybrid_summary is not None and not hybrid_summary.empty:
        hybrid_row = hybrid_summary[hybrid_summary["strategy"].eq("MASATO Hybrid Rotation+Signal")]
        if not hybrid_row.empty:
            hybrid_annual = float(hybrid_row.iloc[0]["annual_return_pct"])
            action_items.append(f"ハイブリッドBT: 年率{hybrid_annual:.2f}% を確認。現行月次ローテーションとの優劣を比較")
    if hybrid_grid is not None and not hybrid_grid.empty:
        best_hybrid = hybrid_grid.iloc[0]
        min_etf_score = best_hybrid.get("min_etf_score", best_hybrid.get("min_score", 0.0))
        min_theme_score = best_hybrid.get("min_theme_score", best_hybrid.get("min_score", 0.0))
        action_items.append(
            f"ハイブリッド候補: {best_hybrid.get('candidate_policy', 'strict_buy')} / 加速局面{best_hybrid.get('acceleration_overlay_mode', 'normal')} / 補助枠{float(best_hybrid['signal_overlay_weight_pct']):.0f}% / entry x{float(best_hybrid['entry_multiplier']):.2f} / stop x{float(best_hybrid['stop_multiplier']):.2f} / 保有{int(best_hybrid['max_holding_days'])}日 / {int(best_hybrid['max_signal_positions'])}枠 / ETF{float(min_etf_score):.0f}+ テーマ{float(min_theme_score):.0f}+ RR{float(best_hybrid.get('min_rr', 0.0)):.1f}+"
        )
    if hybrid_regime_validation is not None and not hybrid_regime_validation.empty:
        weak_hybrid = hybrid_regime_validation.sort_values("vs_rotation_pct").head(1).iloc[0]
        action_items.append(
            f"ハイブリッド局面別: 最弱局面は{weak_hybrid['regime']}、現行比{float(weak_hybrid['vs_rotation_pct']):.2f}%"
        )
    if hybrid_entry_guard_results is not None and not hybrid_entry_guard_results.empty:
        best_guard = hybrid_entry_guard_results.iloc[0]
        best_guard_loss = float(best_guard["max_entry_day_loss_pct"])
        if best_guard_loss <= -99:
            action_items.append("急落日ガード: 成績改善なし。現時点では採用不要")
        else:
            action_items.append(f"急落日ガード候補: 当日下落{best_guard_loss:.0f}%以下の即エントリー禁止")
    if hybrid_acceleration_mode_results is not None and not hybrid_acceleration_mode_results.empty:
        best_acceleration_mode = hybrid_acceleration_mode_results.iloc[0]
        action_items.append(
            f"加速局面モード候補: {best_acceleration_mode['acceleration_overlay_mode']} / 年率{float(best_acceleration_mode['annual_return_pct']):.2f}%"
        )
    if hybrid_ticker_rule_results is not None and not hybrid_ticker_rule_results.empty:
        best_ticker_rule = hybrid_ticker_rule_results.iloc[0]
        relaxed_tickers = str(best_ticker_rule.get("relaxed_signal_tickers", "") or "")
        relaxed_text = ""
        if relaxed_tickers:
            relaxed_text = (
                f" / 限定緩和{relaxed_tickers} "
                f"ETF{float(best_ticker_rule.get('relaxed_min_etf_score', 0.0)):.0f}+"
                f" テーマ{float(best_ticker_rule.get('relaxed_min_theme_score', 0.0)):.0f}+"
                f" RR{float(best_ticker_rule.get('relaxed_min_rr', 0.0)):.1f}+"
            )
        action_items.append(
            f"ハイブリッドETF別制限候補: {best_ticker_rule['rule_name']} / 年率{float(best_ticker_rule['annual_return_pct']):.2f}% / URA補助{int(best_ticker_rule['ura_signal_trade_count'])}件{relaxed_text}"
        )
    if hybrid_theme_risk_mode_results is not None and not hybrid_theme_risk_mode_results.empty:
        best_hybrid_theme_risk_mode = hybrid_theme_risk_mode_results.iloc[0]
        action_items.append(
            f"ハイブリッド本体テーマリスクモード候補: {best_hybrid_theme_risk_mode['theme_risk_mode']} / 年率{float(best_hybrid_theme_risk_mode['annual_return_pct']):.2f}% / DD{float(best_hybrid_theme_risk_mode['max_drawdown_pct']):.2f}%"
        )
    if theme_risk_overlay_comparison is not None and not theme_risk_overlay_comparison.empty:
        buy_row = theme_risk_overlay_comparison[theme_risk_overlay_comparison["指標"].eq("買い系シグナル数")]
        return_row = theme_risk_overlay_comparison[theme_risk_overlay_comparison["指標"].eq("仮想売買 平均リターン%")]
        if not buy_row.empty and not return_row.empty:
            action_items.append(
                f"テーマリスク抑制: 買い系{int(buy_row.iloc[0]['リスク抑制なし'])}件→{int(buy_row.iloc[0]['リスク抑制あり'])}件 / 仮想平均{float(return_row.iloc[0]['リスク抑制あり']):.2f}%"
            )
    if relaxed_theme_risk_overlay_comparison is not None and not relaxed_theme_risk_overlay_comparison.empty:
        relaxed_buy_row = relaxed_theme_risk_overlay_comparison[
            relaxed_theme_risk_overlay_comparison["指標"].eq("買い系シグナル数")
        ]
        if not relaxed_buy_row.empty:
            action_items.append(
                f"緩和条件ストレス: 買い系{int(relaxed_buy_row.iloc[0]['リスク抑制なし'])}件→{int(relaxed_buy_row.iloc[0]['リスク抑制あり'])}件"
            )
    if theme_risk_policy_mode_results is not None and not theme_risk_policy_mode_results.empty:
        best_theme_risk_mode = theme_risk_policy_mode_results.iloc[0]
        action_items.append(
            f"テーマリスク防御モード候補: {best_theme_risk_mode['mode']} / 仮想平均{float(best_theme_risk_mode['仮想売買 平均リターン%']):.2f}% / ブロック{int(best_theme_risk_mode['ブロック/弱化件数'])}件"
        )
    if relaxed_theme_risk_overlay_blocks is not None and not relaxed_theme_risk_overlay_blocks.empty:
        action_items.append(f"緩和条件でテーマリスク抑制が{len(relaxed_theme_risk_overlay_blocks)}件の判定を弱めた")
    if hybrid_attribution_2024 is not None and not hybrid_attribution_2024.empty:
        worst_etf = hybrid_attribution_2024.iloc[0]
        action_items.append(
            f"2024補助ETF要因: 最弱は{worst_etf['ETF']}、合計{float(worst_etf['total_return_pct']):.2f}%"
        )

    content = [
        f"# 履歴再生PDCA {date:%Y-%m-%d}",
        "",
        "過去データ上で日次判定を月次復元し、仮想売買と見送り評価を再計算します。実売買発注は行いません。",
        "",
        "## 売買計画設定",
        trade_plan_settings_text,
        "",
        "## 回避評価方針",
        f"- 現在の回避評価方針: `{avoid_policy_name}`",
        "- `sell_only` の場合、見送りは監視扱いに寄せ、売却候補だけを回避成否評価の主対象にします。",
        "",
        "## シグナル分布",
        signal_counts,
        "",
        "## テーマリスク別シグナル分布",
        theme_risk_signal_counts,
        "",
        "## テーマリスク抑制 有無比較",
        theme_risk_overlay_comparison.to_markdown(index=False)
        if theme_risk_overlay_comparison is not None and not theme_risk_overlay_comparison.empty
        else "評価なし",
        "",
        "## 緩和条件ストレス テーマリスク抑制比較",
        relaxed_theme_risk_overlay_comparison.to_markdown(index=False)
        if relaxed_theme_risk_overlay_comparison is not None and not relaxed_theme_risk_overlay_comparison.empty
        else "評価なし",
        "",
        "## テーマリスク防御モード 総当たり",
        theme_risk_policy_mode_results.to_markdown(index=False)
        if theme_risk_policy_mode_results is not None and not theme_risk_policy_mode_results.empty
        else "評価なし",
        "",
        "## テーマリスク抑制 ブロック監査",
        theme_risk_overlay_blocks.head(20).to_markdown(index=False)
        if theme_risk_overlay_blocks is not None and not theme_risk_overlay_blocks.empty
        else "通常条件ではブロックなし",
        "",
        "## 緩和条件ストレス ブロック監査",
        relaxed_theme_risk_overlay_blocks.head(20).to_markdown(index=False)
        if relaxed_theme_risk_overlay_blocks is not None and not relaxed_theme_risk_overlay_blocks.empty
        else "緩和条件でもブロックなし",
        "",
        "## フォワードリターン評価",
        signal_accuracy.to_markdown(index=False) if not signal_accuracy.empty else "評価なし",
        "",
        "## 仮想売買サマリー",
        virtual_trade_summary.to_markdown(index=False) if not virtual_trade_summary.empty else "評価なし",
        "",
        "## 見送り・リスク削減サマリー",
        avoid_summary.to_markdown(index=False) if not avoid_summary.empty else "評価なし",
        "",
        "## 買い価格・停止価格 総当たり",
        entry_parameter_results.head(10).to_markdown(index=False)
        if entry_parameter_results is not None and not entry_parameter_results.empty
        else "評価なし",
        "",
        "## 見送り・売却候補 判定別評価",
        avoid_by_signal.to_markdown(index=False) if avoid_by_signal is not None and not avoid_by_signal.empty else "評価なし",
        "",
        "## 回避方針 総当たり",
        avoid_policy_results.to_markdown(index=False)
        if avoid_policy_results is not None and not avoid_policy_results.empty
        else "評価なし",
        "",
        "## シグナル実行バックテスト",
        signal_execution_summary.to_markdown(index=False)
        if signal_execution_summary is not None and not signal_execution_summary.empty
        else "評価なし",
        "",
        "## シグナル実行 診断",
        signal_execution_diagnostics.to_markdown(index=False)
        if signal_execution_diagnostics is not None and not signal_execution_diagnostics.empty
        else "診断なし",
        "",
        "## シグナル実行 総当たり",
        signal_execution_grid.head(10).to_markdown(index=False)
        if signal_execution_grid is not None and not signal_execution_grid.empty
        else "評価なし",
        "",
        "## ハイブリッド 月次ローテーション+補助シグナル",
        hybrid_summary.to_markdown(index=False)
        if hybrid_summary is not None and not hybrid_summary.empty
        else "評価なし",
        "",
        "## ハイブリッド 診断",
        hybrid_diagnostics.to_markdown(index=False)
        if hybrid_diagnostics is not None and not hybrid_diagnostics.empty
        else "診断なし",
        "",
        "## ハイブリッド 総当たり",
        hybrid_grid.head(10).to_markdown(index=False)
        if hybrid_grid is not None and not hybrid_grid.empty
        else "評価なし",
        "",
        "## ハイブリッド 局面別検証",
        hybrid_regime_validation.to_markdown(index=False)
        if hybrid_regime_validation is not None and not hybrid_regime_validation.empty
        else "評価なし",
        "",
        "## ハイブリッド 急落日ガード検証",
        hybrid_entry_guard_results.to_markdown(index=False)
        if hybrid_entry_guard_results is not None and not hybrid_entry_guard_results.empty
        else "評価なし",
        "",
        "## ハイブリッド 加速局面モード検証",
        hybrid_acceleration_mode_results.to_markdown(index=False)
        if hybrid_acceleration_mode_results is not None and not hybrid_acceleration_mode_results.empty
        else "評価なし",
        "",
        "## ハイブリッド ETF別補助エントリー制限検証",
        hybrid_ticker_rule_results.to_markdown(index=False)
        if hybrid_ticker_rule_results is not None and not hybrid_ticker_rule_results.empty
        else "評価なし",
        "",
        "## ハイブリッド テーマリスクモード検証",
        hybrid_theme_risk_mode_results.to_markdown(index=False)
        if hybrid_theme_risk_mode_results is not None and not hybrid_theme_risk_mode_results.empty
        else "評価なし",
        "",
        "## ハイブリッド 2024 ETF別要因",
        hybrid_attribution_2024.to_markdown(index=False)
        if hybrid_attribution_2024 is not None and not hybrid_attribution_2024.empty
        else "評価なし",
        "",
        "## ハイブリッド 取引ログ",
        hybrid_trade_log.to_markdown(index=False)
        if hybrid_trade_log is not None and not hybrid_trade_log.empty
        else "ログなし",
        "",
        "## 仮想売買ログ 直近20件",
        virtual_trades.tail(20).to_markdown(index=False) if not virtual_trades.empty else "ログなし",
        "",
        "## 見送り評価ログ 直近20件",
        avoid_outcomes.tail(20).to_markdown(index=False) if not avoid_outcomes.empty else "ログなし",
        "",
        "## PDCA: Act",
        *[f"- {item}" for item in action_items],
        "",
        "## 出力ファイル",
        f"- 履歴シグナルCSV: `{signal_path}`",
        f"- 判定精度CSV: `{forward_path}`",
        f"- 仮想売買CSV: `{virtual_path}`",
        f"- 見送り評価CSV: `{avoid_path}`",
        f"- 買い価格総当たりCSV: `{entry_search_path}`",
        f"- 見送り判定別CSV: `{avoid_by_signal_path}`",
        f"- 回避方針総当たりCSV: `{avoid_policy_path}`",
        f"- シグナル実行BT CSV: `{signal_execution_path}`",
        f"- シグナル実行診断CSV: `{signal_execution_diag_path}`",
        f"- シグナル実行総当たりCSV: `{signal_execution_grid_path}`",
        f"- ハイブリッドBT CSV: `{hybrid_path}`",
        f"- ハイブリッド診断CSV: `{hybrid_diag_path}`",
        f"- ハイブリッド総当たりCSV: `{hybrid_grid_path}`",
        f"- ハイブリッド局面別CSV: `{hybrid_regime_path}`",
        f"- ハイブリッド急落日ガードCSV: `{hybrid_entry_guard_path}`",
        f"- ハイブリッド加速局面モードCSV: `{hybrid_acceleration_mode_path}`",
        f"- ハイブリッドETF別補助制限CSV: `{hybrid_ticker_rule_path}`",
        f"- ハイブリッドテーマリスクモードCSV: `{hybrid_theme_risk_mode_path}`",
        f"- テーマリスク抑制比較CSV: `{theme_risk_overlay_path}`",
        f"- 緩和条件テーマリスク抑制比較CSV: `{relaxed_theme_risk_overlay_path}`",
        f"- テーマリスク防御モード総当たりCSV: `{theme_risk_policy_mode_path}`",
        f"- テーマリスク抑制ブロック監査CSV: `{theme_risk_blocks_path}`",
        f"- 緩和条件テーマリスク抑制ブロック監査CSV: `{relaxed_theme_risk_blocks_path}`",
        f"- ハイブリッド取引ログCSV: `{hybrid_trade_log_path}`",
        f"- ハイブリッド2024 ETF別要因CSV: `{hybrid_attribution_2024_path}`",
    ]
    output_path.write_text("\n".join(content), encoding="utf-8")
    return output_path


def write_backtest_report(
    summary: pd.DataFrame,
    diagnostics: pd.DataFrame,
    strategy_curve: pd.Series,
    config_label: str = "default",
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"backtest_report_{date:%Y-%m-%d}.md"
    summary_csv = PROJECT_ROOT / "data" / "backtest" / f"backtest_summary_{date:%Y-%m-%d}.csv"
    curve_csv = PROJECT_ROOT / "data" / "backtest" / f"equity_curve_{date:%Y-%m-%d}.csv"
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_csv, index=False)
    strategy_curve.to_frame("equity").to_csv(curve_csv)
    best_benchmark = summary[summary["strategy"] != "MASATO Rotation"].sort_values(
        "annual_return_pct",
        ascending=False,
    ).head(1)
    masato = summary[summary["strategy"] == "MASATO Rotation"].iloc[0]
    benchmark_text = "比較対象なし"
    if not best_benchmark.empty:
        best = best_benchmark.iloc[0]
        diff = float(masato["annual_return_pct"]) - float(best["annual_return_pct"])
        benchmark_text = (
            f"最強ベンチマークは {best['strategy']}。"
            f"年率差は {diff:.2f}% です。"
        )
    pdca_actions = []
    if float(masato["max_drawdown_pct"]) <= -12:
        pdca_actions.append("DDが大きいため、Satellite比率またはDD停止条件の再検証")
    if not best_benchmark.empty and float(masato["annual_return_pct"]) < float(best_benchmark.iloc[0]["annual_return_pct"]):
        pdca_actions.append("ベンチマーク未達のため、テーマ選定スコアとリバランス頻度の再検証")
    if not pdca_actions:
        pdca_actions.append("現行ルールを維持し、候補ETFの拡張だけを次回検証")
    content = [
        f"# 10年バックテストレポート {date:%Y-%m-%d}",
        "",
        "## 検証ルール",
        f"- 使用プロファイル: {config_label}",
        "- 実売買発注なし。研究用シミュレーションです。",
        "",
        "## ベンチマーク比較",
        summary.to_markdown(index=False),
        "",
        "## 判定",
        benchmark_text,
        "",
        "## 診断",
        diagnostics.to_markdown(index=False),
        "",
        "## PDCA: Check",
        f"- 年率リターン: {float(masato['annual_return_pct']):.2f}%",
        f"- 累積リターン: {float(masato['cumulative_return_pct']):.2f}%",
        f"- 最大DD: {float(masato['max_drawdown_pct']):.2f}%",
        f"- シャープレシオ: {float(masato['sharpe_ratio']):.2f}",
        "",
        "## PDCA: Act",
        *[f"- {item}" for item in pdca_actions],
        "",
        "## 出力ファイル",
        f"- サマリーCSV: `{summary_csv}`",
        f"- エクイティカーブCSV: `{curve_csv}`",
    ]
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def write_parameter_search_report(
    grid_results: pd.DataFrame,
    baseline_summary: pd.DataFrame,
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"parameter_search_report_{date:%Y-%m-%d}.md"
    csv_path = PROJECT_ROOT / "data" / "backtest" / f"parameter_search_{date:%Y-%m-%d}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    grid_results.to_csv(csv_path, index=False)
    top_results = grid_results.head(10)
    best = grid_results.iloc[0]
    baseline = baseline_summary[baseline_summary["strategy"] == "MASATO Rotation"].iloc[0]
    annual_diff = float(best["annual_return_pct"]) - float(baseline["annual_return_pct"])
    dd_diff = float(best["max_drawdown_pct"]) - float(baseline["max_drawdown_pct"])
    calmar_diff = float(best["calmar_ratio"]) - float(baseline["calmar_ratio"])
    recommended_actions = [
        (
            f"Satellite比率を {float(best['satellite_weight_pct']):.0f}%、"
            f"上位ETF数を {int(best['top_satellites'])}、"
            f"リバランスを {best['rebalance_frequency']}、"
            f"DD停止を {float(best['drawdown_stop_pct']):.0f}%、"
            f"最低スコアを {float(best['min_satellite_score']):.0f}、"
            f"スコアを {best.get('score_profile', 'balanced')} にしたルールを候補にする"
        )
    ]
    if annual_diff > 0 and dd_diff >= -3:
        recommended_actions.append("リターン改善があり、DD悪化も限定的なので次回はこの候補を詳細バックテスト")
    elif annual_diff > 0:
        recommended_actions.append("リターンは改善。ただしDD悪化を許容できるか、保有上限と停止条件を追加検証")
    else:
        recommended_actions.append("現行ルールから大きく変えず、ETFユニバースやスコア重みの改善を優先")
    content = [
        f"# 改善パラメータ総当たりPDCA {date:%Y-%m-%d}",
        "",
        "## Plan",
        "- Satellite比率、上位ETF数、リバランス頻度、DD停止ライン、最低スコアを総当たり検証",
        "- 評価は年率リターンだけでなく、最大DD、Sharpe、Calmarを含める",
        "- 実売買発注なし。研究用検証です。",
        "",
        "## Do",
        f"- 検証本数: {len(grid_results)}",
        "- ベースライン: Core SPY 30% / QQQ 30% / Satellite 25% / Cash 15%、月次、上位3ETF、DD -8%",
        "",
        "## Check: 上位10設定",
        top_results.to_markdown(index=False),
        "",
        "## Check: ベースラインとの差",
        f"- ベースライン年率: {float(baseline['annual_return_pct']):.2f}%",
        f"- 最良設定年率: {float(best['annual_return_pct']):.2f}%",
        f"- 年率差: {annual_diff:.2f}%",
        f"- ベースライン最大DD: {float(baseline['max_drawdown_pct']):.2f}%",
        f"- 最良設定最大DD: {float(best['max_drawdown_pct']):.2f}%",
        f"- DD差: {dd_diff:.2f}%",
        f"- Calmar差: {calmar_diff:.2f}",
        "",
        "## Act",
        *[f"- {item}" for item in recommended_actions],
        "",
        "## 出力ファイル",
        f"- 総当たりCSV: `{csv_path}`",
    ]
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def write_regime_validation_report(
    validation: pd.DataFrame,
    config_label: str,
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"regime_validation_report_{date:%Y-%m-%d}.md"
    csv_path = PROJECT_ROOT / "data" / "backtest" / f"regime_validation_{date:%Y-%m-%d}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    validation.to_csv(csv_path, index=False)
    wins_spy = int((validation["vs_spy_pct"] > 0).sum()) if not validation.empty else 0
    wins_qqq = int((validation["vs_qqq_pct"] > 0).sum()) if not validation.empty else 0
    wins_smh = int((validation["vs_smh_pct"] > 0).sum()) if not validation.empty else 0
    weak_rows = validation.sort_values("vs_qqq_pct").head(2) if not validation.empty else pd.DataFrame()
    act_items = []
    if wins_qqq < max(1, len(validation) // 2):
        act_items.append("QQQに負ける局面が多いため、AI/半導体の加速期はモメンタム重みを強める別モードを検証")
    if not weak_rows.empty:
        weak_names = "、".join(str(item) for item in weak_rows["regime"].tolist())
        act_items.append(f"弱点局面は {weak_names}。この期間の採用ETFと停止条件を重点確認")
    if wins_spy >= max(1, len(validation) - 1):
        act_items.append("SPY比較では安定しているため、Core-Satelliteの守り方針は維持")
    if not act_items:
        act_items.append("局面別でも大きな弱点は限定的。次はスコア重みの改善へ進む")
    content = [
        f"# 局面別検証PDCA {date:%Y-%m-%d}",
        "",
        "## Plan",
        f"- 検証対象: {config_label}",
        "- 10年全体の最良設定が、各相場局面でも安定しているか確認",
        "",
        "## Do",
        validation.to_markdown(index=False) if not validation.empty else "検証対象データなし",
        "",
        "## Check",
        f"- SPYに勝った局面数: {wins_spy}/{len(validation)}",
        f"- QQQに勝った局面数: {wins_qqq}/{len(validation)}",
        f"- SMHに勝った局面数: {wins_smh}/{len(validation)}",
        "",
        "## Act",
        *[f"- {item}" for item in act_items],
        "",
        "## 出力ファイル",
        f"- 局面別CSV: `{csv_path}`",
    ]
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path


def write_selection_audit_report(
    audits: dict[str, pd.DataFrame],
    output_dir: str | Path = "reports/weekly",
    report_date: datetime | None = None,
) -> Path:
    date = report_date or datetime.now()
    directory = ensure_dir(output_dir)
    report_path = PROJECT_ROOT / directory / f"selection_audit_report_{date:%Y-%m-%d}.md"
    output_folder = PROJECT_ROOT / "data" / "backtest"
    output_folder.mkdir(parents=True, exist_ok=True)
    content = [
        f"# 弱点局面ETF採用監査 {date:%Y-%m-%d}",
        "",
        "## 目的",
        "- 2020回復局面と2023 AI初動で、どのETFを選んでいたか確認",
        "- QQQ/SMHに負けた原因が、採用遅れか、分散しすぎか、DD停止かを切り分ける",
    ]
    for name, audit in audits.items():
        csv_path = output_folder / f"selection_audit_{name}_{date:%Y-%m-%d}.csv"
        audit.to_csv(csv_path, index=False)
        content.extend(
            [
                "",
                f"## {name}",
                audit.to_markdown(index=False) if not audit.empty else "採用ログなし",
                "",
                f"CSV: `{csv_path}`",
            ]
        )
    content.extend(
        [
            "",
            "## Act",
            "- SMH/SOXXが上位にいるのに採用比率が薄い場合は、半導体テーマの上限を別枠で検証",
            "- SMH/SOXXが上位に出ていない場合は、モメンタム重みと相対強度重みを強めるスコア版を検証",
            "- Noneが多い場合は、最低スコア45またはDD停止条件が厳しすぎる可能性を検証",
        ]
    )
    report_path.write_text("\n".join(content), encoding="utf-8")
    return report_path
