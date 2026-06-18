from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from .backtest_engine import (
    BacktestConfig,
    HybridSignalConfig,
    SignalExecutionConfig,
    backtest_config_from_profile,
    build_rebalance_selection_log,
    build_benchmark_summary,
    build_price_matrix,
    copy_hybrid_signal_config,
    run_hybrid_acceleration_mode_search,
    run_hybrid_entry_guard_search,
    run_hybrid_regime_validation,
    run_hybrid_rotation_signal_backtest,
    run_hybrid_signal_grid_search,
    run_hybrid_ticker_rule_search,
    run_parameter_grid_search,
    run_regime_validation,
    run_rotation_backtest,
    run_signal_execution_backtest,
    run_signal_execution_grid_search,
    summarize_hybrid_trade_attribution,
)
from .data_loader import flatten_universe, load_price_data
from .etf_score_engine import calculate_etf_score
from .indicators import add_indicators, latest_metrics
from .line_engine import check_line_settings, send_line_broadcast_message, send_line_push_message
from .notification_engine import (
    build_notification_candidates,
    build_portfolio_notification_candidates,
    count_notification_priorities,
    load_notification_outbox,
    notification_delivery_plan,
    summarize_notification_payloads,
    write_delivery_packets,
    write_notification_outbox,
)
from .operations_engine import (
    check_daily_artifacts,
    check_go_live_readiness,
    check_operations_status,
    check_weekly_artifacts,
)
from .pdca_engine import (
    AVOID_POLICY_SIGNALS,
    evaluate_avoid_outcomes,
    evaluate_avoid_outcomes_for_signals,
    evaluate_signal_history,
    evaluate_virtual_trades,
    propose_signal_improvements,
    run_entry_parameter_search,
    run_avoid_policy_search,
    summarize_avoid_outcomes_by_signal,
    summarize_avoid_outcomes,
    summarize_manual_decisions,
    summarize_signal_accuracy,
    summarize_virtual_trades,
)
from .portfolio_engine import evaluate_portfolio_actions, load_portfolio, update_portfolio_prices, validate_portfolio
from .report_engine import (
    build_signal_table,
    write_backtest_report,
    write_daily_report,
    write_decision_brief,
    write_go_live_readiness_report,
    write_manual_decision_sheet,
    write_mobile_summary,
    write_daily_health_report,
    write_notification_delivery_plan_report,
    write_notification_report,
    write_notification_summary_report,
    write_operations_status_report,
    write_portfolio_check_report,
    write_parameter_search_report,
    write_regime_validation_report,
    write_replay_pdca_report,
    write_selection_audit_report,
    write_signal_snapshot,
    write_weekly_health_report,
    write_weekly_pdca_report,
)
from .risk_engine import calculate_trade_plan
from .signal_engine import apply_theme_risk_overlay, decide_signal
from .theme_engine import assess_theme_rotation_risks, calculate_theme_scores, classify_theme_stage
from .utils import PROJECT_ROOT, load_yaml, setup_logging


DEFAULT_STRATEGY_PROFILE = "current_candidate"


def theme_risk_overlay_mode_from_settings(settings: dict[str, object]) -> str:
    theme_risk_settings = settings.get("theme_risk", {})
    if not isinstance(theme_risk_settings, dict):
        return "balanced"
    return str(theme_risk_settings.get("overlay_mode", "balanced"))


def trade_plan_multipliers_from_settings(settings: dict[str, object]) -> dict[str, float]:
    trade_plan_settings = settings.get("trade_plan", {})
    if not isinstance(trade_plan_settings, dict):
        return {"entry_multiplier": 1.0, "stop_multiplier": 1.0, "target_multiplier": 1.0}
    return {
        "entry_multiplier": float(trade_plan_settings.get("entry_multiplier", 1.0) or 1.0),
        "stop_multiplier": float(trade_plan_settings.get("stop_multiplier", 1.0) or 1.0),
        "target_multiplier": float(trade_plan_settings.get("target_multiplier", 1.0) or 1.0),
    }


def avoid_policy_name_from_settings(settings: dict[str, object]) -> str:
    pdca_settings = settings.get("pdca", {})
    if not isinstance(pdca_settings, dict):
        return "current_all_avoid"
    policy_name = str(pdca_settings.get("avoid_policy", "current_all_avoid"))
    return policy_name if policy_name in AVOID_POLICY_SIGNALS else "current_all_avoid"


def avoid_signals_from_settings(settings: dict[str, object]) -> set[str]:
    return AVOID_POLICY_SIGNALS[avoid_policy_name_from_settings(settings)]


def load_strategy_config(profile_name: str = DEFAULT_STRATEGY_PROFILE) -> tuple[BacktestConfig, str]:
    profiles = load_yaml("config/strategy_profiles.yaml").get("profiles", {})
    if not isinstance(profiles, dict) or profile_name not in profiles:
        available = ", ".join(sorted(str(name) for name in profiles)) if isinstance(profiles, dict) else "なし"
        raise ValueError(f"Unknown strategy profile: {profile_name}. available: {available}")
    profile = profiles[profile_name]
    if not isinstance(profile, dict):
        raise ValueError(f"Strategy profile must be a mapping: {profile_name}")
    config = backtest_config_from_profile(profile)
    description = str(profile.get("description", profile_name))
    return config, description


def allocation_text_from_config(config: BacktestConfig) -> str:
    core_pct = (config.core_spy_weight + config.core_qqq_weight) * 100
    satellite_pct = config.satellite_weight * 100
    cash_pct = max(0.0, 100 - core_pct - satellite_pct)
    return f"Core {core_pct:.0f}% / Satellite {satellite_pct:.0f}% / Cash {cash_pct:.0f}%"


def run_daily(refresh: bool = False, profile_name: str = DEFAULT_STRATEGY_PROFILE) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = load_yaml("config/settings.yaml")
    universe = load_yaml("config/etf_universe.yaml")
    theme_map_config = load_yaml("config/theme_map.yaml")
    theme_risk_mode = theme_risk_overlay_mode_from_settings(settings)
    trade_plan_multipliers = trade_plan_multipliers_from_settings(settings)
    strategy_config, _description = load_strategy_config(profile_name)
    entries = flatten_universe(universe)
    tickers = sorted({entry["ticker"] for entry in entries} | {"SPY", "QQQ"})
    period = str(settings["data"].get("period", "10y"))
    interval = str(settings["data"].get("interval", "1d"))
    logger.info("Loading price data for %s", ", ".join(tickers))
    raw_data = load_price_data(tickers, period=period, interval=interval, refresh=refresh)
    qqq_close = raw_data["QQQ"]["Adj Close"]
    spy_close = raw_data["SPY"]["Adj Close"]
    enriched = {
        ticker: add_indicators(frame, qqq_close=qqq_close, spy_close=spy_close)
        for ticker, frame in raw_data.items()
    }
    metrics_by_ticker = {ticker: latest_metrics(frame) for ticker, frame in enriched.items()}
    theme_scores = calculate_theme_scores(theme_map_config["themes"], metrics_by_ticker)
    theme_risk_table = pd.DataFrame(
        assess_theme_rotation_risks(theme_map_config["themes"], metrics_by_ticker, theme_scores)
    )
    theme_risks = {
        str(row["テーマ"]): row
        for row in theme_risk_table.to_dict("records")
    }
    rows: list[dict[str, object]] = []
    for entry in entries:
        ticker = entry["ticker"]
        theme = entry["theme"]
        metrics = metrics_by_ticker[ticker]
        theme_score = theme_scores.get(theme, 60.0)
        score_parts = calculate_etf_score(metrics, theme_score)
        stage = classify_theme_stage(metrics, theme_score)
        trade_plan = calculate_trade_plan(metrics, **trade_plan_multipliers)
        signal = decide_signal(score_parts["total"], theme_score, stage, metrics, trade_plan)
        theme_risk = theme_risks.get(theme, {})
        risk_bucket = str(theme_risk.get("リスク区分", "低"))
        risk_score = float(theme_risk.get("リスクスコア", 0.0) or 0.0)
        signal = apply_theme_risk_overlay(signal, risk_bucket, risk_score, theme_risk_mode)
        rows.append(
            {
                "ETF": ticker,
                "テーマ": theme,
                "ETFスコア": score_parts["total"],
                "テーマスコア": round(theme_score, 2),
                "テーマリスク": risk_bucket,
                "テーマリスクスコア": risk_score,
                "テーマリスク理由": theme_risk.get("主なリスク", ""),
                "テーマ予防策": theme_risk.get("予防策", ""),
                "ステージ": stage,
                "現在価格": trade_plan["current_price"],
                "第1買い": trade_plan["first_buy"],
                "第1買いまで%": trade_plan["first_buy_gap_pct"],
                "第2買い": trade_plan["second_buy"],
                "第3買い": trade_plan["third_buy"],
                "保守目標": trade_plan["conservative_target"],
                "強気目標": trade_plan["aggressive_target"],
                "停止価格": trade_plan["stop_price"],
                "RR": trade_plan["risk_reward"],
                "判定": signal,
            }
        )
    table = build_signal_table(rows)
    current_prices = {ticker: metrics["price"] for ticker, metrics in metrics_by_ticker.items() if "price" in metrics}
    portfolio = evaluate_portfolio_actions(update_portfolio_prices(load_portfolio(), current_prices))
    output_path = write_daily_report(
        table,
        theme_scores,
        allocation_text_from_config(strategy_config),
        portfolio=portfolio,
        theme_risk_table=theme_risk_table,
    )
    notifications = pd.concat(
        [build_notification_candidates(table), build_portfolio_notification_candidates(portfolio)],
        ignore_index=True,
    )
    notification_path = write_notification_report(notifications)
    notification_outbox_path = write_notification_outbox(notifications)
    signal_snapshot_path = write_signal_snapshot(table)
    logger.info("Daily report written: %s", output_path)
    logger.info("Notification candidates written: %s", notification_path)
    logger.info("Notification outbox written: %s", notification_outbox_path)
    logger.info("Signal snapshot written: %s", signal_snapshot_path)
    print(f"日次レポートを作成しました: {output_path}")
    print(f"通知候補を作成しました: {notification_path}")
    print(f"通知アウトボックスを作成しました: {notification_outbox_path}")
    print(f"シグナル履歴を保存しました: {signal_snapshot_path}")


def numeric_metrics_from_row(row: pd.Series) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key, value in row.items():
        if pd.isna(value):
            continue
        try:
            metrics[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return metrics


def metrics_at_date(frame: pd.DataFrame, snapshot_date: pd.Timestamp) -> dict[str, float]:
    available = frame.loc[frame.index <= snapshot_date].dropna(subset=["price"])
    if available.empty:
        return {}
    return numeric_metrics_from_row(available.iloc[-1])


def build_signal_rows_for_metrics(
    entries: list[dict[str, str]],
    theme_map_config: dict[str, object],
    metrics_by_ticker: dict[str, dict[str, float]],
    apply_theme_risk: bool = True,
    theme_risk_mode: str = "balanced",
    trade_plan_multipliers: dict[str, float] | None = None,
) -> list[dict[str, object]]:
    trade_plan_multipliers = trade_plan_multipliers or {}
    themes = theme_map_config["themes"]
    if not isinstance(themes, dict):
        raise ValueError("theme_map.yaml themes must be a mapping")
    theme_scores = calculate_theme_scores(themes, metrics_by_ticker)
    theme_risk_table = pd.DataFrame(assess_theme_rotation_risks(themes, metrics_by_ticker, theme_scores))
    theme_risks = {str(row["テーマ"]): row for row in theme_risk_table.to_dict("records")}
    rows: list[dict[str, object]] = []
    for entry in entries:
        ticker = entry["ticker"]
        theme = entry["theme"]
        metrics = metrics_by_ticker.get(ticker, {})
        if not metrics:
            continue
        theme_score = theme_scores.get(theme, 60.0)
        score_parts = calculate_etf_score(metrics, theme_score)
        stage = classify_theme_stage(metrics, theme_score)
        trade_plan = calculate_trade_plan(metrics, **trade_plan_multipliers)
        signal = decide_signal(score_parts["total"], theme_score, stage, metrics, trade_plan)
        theme_risk = theme_risks.get(theme, {})
        risk_bucket = str(theme_risk.get("リスク区分", "低"))
        risk_score = float(theme_risk.get("リスクスコア", 0.0) or 0.0)
        if apply_theme_risk:
            signal = apply_theme_risk_overlay(signal, risk_bucket, risk_score, theme_risk_mode)
        rows.append(
            {
                "ETF": ticker,
                "テーマ": theme,
                "ETFスコア": score_parts["total"],
                "テーマスコア": round(theme_score, 2),
                "テーマリスク": risk_bucket,
                "テーマリスクスコア": risk_score,
                "テーマリスク理由": theme_risk.get("主なリスク", ""),
                "テーマ予防策": theme_risk.get("予防策", ""),
                "ステージ": stage,
                "現在価格": trade_plan["current_price"],
                "第1買い": trade_plan["first_buy"],
                "第1買いまで%": trade_plan["first_buy_gap_pct"],
                "第2買い": trade_plan["second_buy"],
                "第3買い": trade_plan["third_buy"],
                "保守目標": trade_plan["conservative_target"],
                "強気目標": trade_plan["aggressive_target"],
                "停止価格": trade_plan["stop_price"],
                "RR": trade_plan["risk_reward"],
                "判定": signal,
            }
        )
    return rows


def replay_snapshot_dates(prices: pd.DataFrame, start: str = "2020-01-01", max_forward_days: int = 20) -> list[pd.Timestamp]:
    usable = prices.dropna(how="all")
    usable = usable.loc[usable.index >= pd.Timestamp(start)]
    if len(usable) <= max_forward_days:
        return []
    usable = usable.iloc[:-max_forward_days]
    return [pd.Timestamp(index) for index in usable.resample("ME").last().dropna(how="all").index]


def build_historical_signal_history(
    entries: list[dict[str, str]],
    theme_map_config: dict[str, object],
    enriched: dict[str, pd.DataFrame],
    snapshot_dates: list[pd.Timestamp],
    apply_theme_risk: bool = True,
    theme_risk_mode: str = "balanced",
    trade_plan_multipliers: dict[str, float] | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for snapshot_date in snapshot_dates:
        metrics_by_ticker = {
            ticker: metrics
            for ticker, metrics in (
                (ticker, metrics_at_date(frame, snapshot_date))
                for ticker, frame in enriched.items()
            )
            if metrics
        }
        rows = build_signal_rows_for_metrics(
            entries,
            theme_map_config,
            metrics_by_ticker,
            apply_theme_risk,
            theme_risk_mode,
            trade_plan_multipliers,
        )
        if not rows:
            continue
        frame = build_signal_table(rows)
        frame.insert(0, "snapshot", snapshot_date.date().isoformat())
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def summarize_theme_risk_overlay_effect(
    baseline_history: pd.DataFrame,
    overlay_history: pd.DataFrame,
    baseline_forward: pd.DataFrame,
    overlay_forward: pd.DataFrame,
    baseline_virtual_summary: pd.DataFrame,
    overlay_virtual_summary: pd.DataFrame,
) -> pd.DataFrame:
    buy_signals = {"強気買い候補", "買い候補", "積立候補"}
    watch_signals = {"押し目待ち"}
    defensive_signals = {"見送り", "売却候補", "リスク削減"}

    def count_signals(frame: pd.DataFrame, labels: set[str]) -> int:
        if frame.empty or "判定" not in frame.columns:
            return 0
        return int(frame["判定"].isin(labels).sum())

    def forward_buy_average(frame: pd.DataFrame) -> float:
        if frame.empty or "判定" not in frame.columns or "20d_return_pct" not in frame.columns:
            return 0.0
        subset = frame[frame["判定"].isin(buy_signals | watch_signals)]
        if subset.empty:
            return 0.0
        return round(float(pd.to_numeric(subset["20d_return_pct"], errors="coerce").mean()), 2)

    def virtual_metric(frame: pd.DataFrame, column: str, fallback_column: str | None = None) -> float:
        if frame.empty or column not in frame.columns:
            if fallback_column is None or fallback_column not in frame.columns:
                return 0.0
            column = fallback_column
        value = frame.iloc[0].get(column, 0.0)
        return round(float(value), 2) if pd.notna(value) else 0.0

    metrics = [
        (
            "買い系シグナル数",
            count_signals(baseline_history, buy_signals),
            count_signals(overlay_history, buy_signals),
        ),
        (
            "押し目待ち数",
            count_signals(baseline_history, watch_signals),
            count_signals(overlay_history, watch_signals),
        ),
        (
            "見送り/売却系シグナル数",
            count_signals(baseline_history, defensive_signals),
            count_signals(overlay_history, defensive_signals),
        ),
        (
            "買い/押し目20日平均%",
            forward_buy_average(baseline_forward),
            forward_buy_average(overlay_forward),
        ),
        (
            "仮想売買 約定件数",
            virtual_metric(baseline_virtual_summary, "約定件数"),
            virtual_metric(overlay_virtual_summary, "約定件数"),
        ),
        (
            "仮想売買 平均リターン%",
            virtual_metric(baseline_virtual_summary, "平均リターン%", "平均損益%"),
            virtual_metric(overlay_virtual_summary, "平均リターン%", "平均損益%"),
        ),
    ]
    return pd.DataFrame(
        [
            {
                "指標": name,
                "リスク抑制なし": baseline,
                "リスク抑制あり": overlay,
                "差分": round(float(overlay) - float(baseline), 2),
            }
            for name, baseline, overlay in metrics
        ]
    )


def summarize_theme_risk_overlay_blocks(
    baseline_history: pd.DataFrame,
    overlay_history: pd.DataFrame,
) -> pd.DataFrame:
    if baseline_history.empty or overlay_history.empty:
        return pd.DataFrame(
            columns=[
                "snapshot",
                "ETF",
                "テーマ",
                "抑制なし判定",
                "抑制あり判定",
                "テーマリスク",
                "テーマリスクスコア",
                "テーマリスク理由",
                "テーマ予防策",
            ]
        )
    required = {"snapshot", "ETF", "判定"}
    if not required.issubset(baseline_history.columns) or not required.issubset(overlay_history.columns):
        return pd.DataFrame()
    baseline = baseline_history.copy()
    overlay = overlay_history.copy()
    merged = baseline.merge(
        overlay,
        on=["snapshot", "ETF"],
        suffixes=("_なし", "_あり"),
    )
    changed = merged[merged["判定_なし"].ne(merged["判定_あり"])].copy()
    if changed.empty:
        return pd.DataFrame(
            columns=[
                "snapshot",
                "ETF",
                "テーマ",
                "抑制なし判定",
                "抑制あり判定",
                "テーマリスク",
                "テーマリスクスコア",
                "テーマリスク理由",
                "テーマ予防策",
            ]
        )
    def pick_column(frame: pd.DataFrame, preferred: str, fallback: object = "") -> object:
        if preferred in frame.columns:
            return frame[preferred]
        base_name = preferred.removesuffix("_あり")
        if base_name in frame.columns:
            return frame[base_name]
        return fallback

    return changed.assign(
        テーマ=pick_column(changed, "テーマ_あり", changed.get("テーマ_なし", "")),
        抑制なし判定=changed["判定_なし"],
        抑制あり判定=changed["判定_あり"],
        テーマリスク=pick_column(changed, "テーマリスク_あり"),
        テーマリスクスコア=pick_column(changed, "テーマリスクスコア_あり", 0.0),
        テーマリスク理由=pick_column(changed, "テーマリスク理由_あり"),
        テーマ予防策=pick_column(changed, "テーマ予防策_あり"),
    ).loc[
        :,
        [
            "snapshot",
            "ETF",
            "テーマ",
            "抑制なし判定",
            "抑制あり判定",
            "テーマリスク",
            "テーマリスクスコア",
            "テーマリスク理由",
            "テーマ予防策",
        ],
    ]


def apply_relaxed_theme_entry_policy(
    signal_history: pd.DataFrame,
    apply_theme_risk: bool = True,
    theme_risk_mode: str = "balanced",
) -> pd.DataFrame:
    if signal_history.empty:
        return signal_history.copy()
    frame = signal_history.copy()
    for index, row in frame.iterrows():
        etf_score = float(row.get("ETFスコア", 0.0) or 0.0)
        theme_score = float(row.get("テーマスコア", 0.0) or 0.0)
        rr = float(row.get("RR", 0.0) or 0.0)
        risk_bucket = str(row.get("テーマリスク", "低"))
        risk_score = float(row.get("テーマリスクスコア", 0.0) or 0.0)
        current_signal = str(row.get("判定", ""))
        relaxed_signal = current_signal
        if etf_score < 40 or theme_score < 35:
            relaxed_signal = "売却候補"
        elif etf_score >= 70 and theme_score >= 40 and rr >= 1.2:
            relaxed_signal = "買い候補"
        elif etf_score >= 60 and theme_score >= 35 and rr >= 1.2:
            relaxed_signal = "押し目待ち"
        if apply_theme_risk:
            relaxed_signal = apply_theme_risk_overlay(relaxed_signal, risk_bucket, risk_score, theme_risk_mode)
        frame.at[index, "判定"] = relaxed_signal
    return frame


def apply_theme_risk_overlay_to_signal_history(
    signal_history: pd.DataFrame,
    apply_theme_risk: bool = True,
    theme_risk_mode: str = "balanced",
) -> pd.DataFrame:
    if signal_history.empty:
        return signal_history.copy()
    frame = signal_history.copy()
    if not apply_theme_risk:
        return frame
    for index, row in frame.iterrows():
        signal = str(row.get("判定", ""))
        risk_bucket = str(row.get("テーマリスク", "低"))
        risk_score = float(row.get("テーマリスクスコア", 0.0) or 0.0)
        frame.at[index, "判定"] = apply_theme_risk_overlay(signal, risk_bucket, risk_score, theme_risk_mode)
    return frame


def run_theme_risk_policy_mode_search(signal_history: pd.DataFrame) -> pd.DataFrame:
    if signal_history.empty:
        return pd.DataFrame()
    mode_histories: dict[str, pd.DataFrame] = {
        "off": apply_relaxed_theme_entry_policy(signal_history, apply_theme_risk=False)
    }
    for mode in ["high_only", "balanced", "strict"]:
        mode_histories[mode] = apply_relaxed_theme_entry_policy(
            signal_history,
            apply_theme_risk=True,
            theme_risk_mode=mode,
        )
    baseline = mode_histories["off"]
    baseline_evaluated = evaluate_signal_history(baseline)
    baseline_virtual_summary = summarize_virtual_trades(evaluate_virtual_trades(baseline))
    rows: list[dict[str, object]] = []
    for mode, history in mode_histories.items():
        evaluated = evaluate_signal_history(history)
        virtual_summary = summarize_virtual_trades(evaluate_virtual_trades(history))
        comparison = summarize_theme_risk_overlay_effect(
            baseline,
            history,
            baseline_evaluated,
            evaluated,
            baseline_virtual_summary,
            virtual_summary,
        )
        blocks = summarize_theme_risk_overlay_blocks(baseline, history)

        def comparison_value(metric_name: str, column: str) -> float:
            if comparison.empty:
                return 0.0
            matches = comparison[comparison["指標"].eq(metric_name)]
            if matches.empty:
                return 0.0
            return float(matches.iloc[0][column])

        rows.append(
            {
                "mode": mode,
                "買い系シグナル数": int(comparison_value("買い系シグナル数", "リスク抑制あり")),
                "押し目待ち数": int(comparison_value("押し目待ち数", "リスク抑制あり")),
                "見送り/売却系シグナル数": int(comparison_value("見送り/売却系シグナル数", "リスク抑制あり")),
                "買い/押し目20日平均%": comparison_value("買い/押し目20日平均%", "リスク抑制あり"),
                "仮想売買 約定件数": int(comparison_value("仮想売買 約定件数", "リスク抑制あり")),
                "仮想売買 平均リターン%": comparison_value("仮想売買 平均リターン%", "リスク抑制あり"),
                "ブロック/弱化件数": len(blocks),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["仮想売買 平均リターン%", "買い/押し目20日平均%", "ブロック/弱化件数"],
        ascending=[False, False, True],
    )


def run_theme_risk_hybrid_mode_search(
    prices: pd.DataFrame,
    enriched: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    baseline_signal_history: pd.DataFrame,
    strategy_config: BacktestConfig,
    signal_config: HybridSignalConfig,
) -> pd.DataFrame:
    if baseline_signal_history.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for mode in ["off", "high_only", "balanced", "strict"]:
        mode_signal_history = apply_theme_risk_overlay_to_signal_history(
            baseline_signal_history,
            apply_theme_risk=mode != "off",
            theme_risk_mode=mode,
        )
        curve, diagnostics = run_hybrid_rotation_signal_backtest(
            prices,
            enriched,
            satellite_tickers,
            mode_signal_history,
            strategy_config,
            signal_config,
        )
        trade_count = 0
        signal_entry_count = 0
        if not diagnostics.empty:
            trade_count = int(diagnostics.iloc[0]["rotation_trade_count"]) + int(diagnostics.iloc[0]["signal_exit_count"])
            signal_entry_count = int(diagnostics.iloc[0]["signal_entry_count"])
        summary = build_benchmark_summary(curve, prices, trade_count)
        strategy_row = summary[summary["strategy"].eq("MASATO Hybrid Rotation+Signal")]
        if strategy_row.empty:
            continue
        row = strategy_row.iloc[0].to_dict()
        row["theme_risk_mode"] = mode
        row["signal_entry_count"] = signal_entry_count
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    mode_priority = {"balanced": 0, "high_only": 1, "off": 2, "strict": 3}
    result["_mode_priority"] = result["theme_risk_mode"].map(mode_priority).fillna(99)
    return result.sort_values(
        ["annual_return_pct", "max_drawdown_pct", "sharpe_ratio", "_mode_priority"],
        ascending=[False, False, False, True],
    ).drop(columns=["_mode_priority"])


def run_backtest(refresh: bool = False, profile_name: str = DEFAULT_STRATEGY_PROFILE) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = load_yaml("config/settings.yaml")
    universe = load_yaml("config/etf_universe.yaml")
    entries = flatten_universe(universe)
    satellite_tickers = [entry["ticker"] for entry in entries if entry["bucket"] == "satellite"]
    tickers = sorted({entry["ticker"] for entry in entries} | {"SPY", "QQQ", "IEF"})
    period = str(settings["data"].get("period", "10y"))
    interval = str(settings["data"].get("interval", "1d"))
    logger.info("Loading backtest data for %s", ", ".join(tickers))
    raw_data = load_price_data(tickers, period=period, interval=interval, refresh=refresh)
    prices = build_price_matrix(raw_data)
    qqq_close = raw_data["QQQ"]["Adj Close"]
    spy_close = raw_data["SPY"]["Adj Close"]
    enriched = {
        ticker: add_indicators(frame, qqq_close=qqq_close, spy_close=spy_close)
        for ticker, frame in raw_data.items()
    }
    strategy_config, description = load_strategy_config(profile_name)
    strategy_curve, diagnostics = run_rotation_backtest(prices, enriched, satellite_tickers, strategy_config)
    trade_count = int(diagnostics.iloc[0]["trade_count"])
    summary = build_benchmark_summary(strategy_curve, prices, trade_count)
    output_path = write_backtest_report(summary, diagnostics, strategy_curve, f"{profile_name}: {description}")
    logger.info("Backtest report written: %s", output_path)
    print(f"10年バックテストレポートを作成しました: {output_path}")


def prepare_backtest_inputs(refresh: bool = False) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[str]]:
    settings = load_yaml("config/settings.yaml")
    universe = load_yaml("config/etf_universe.yaml")
    entries = flatten_universe(universe)
    satellite_tickers = [entry["ticker"] for entry in entries if entry["bucket"] == "satellite"]
    tickers = sorted({entry["ticker"] for entry in entries} | {"SPY", "QQQ", "IEF"})
    period = str(settings["data"].get("period", "10y"))
    interval = str(settings["data"].get("interval", "1d"))
    raw_data = load_price_data(tickers, period=period, interval=interval, refresh=refresh)
    prices = build_price_matrix(raw_data)
    qqq_close = raw_data["QQQ"]["Adj Close"]
    spy_close = raw_data["SPY"]["Adj Close"]
    enriched = {
        ticker: add_indicators(frame, qqq_close=qqq_close, spy_close=spy_close)
        for ticker, frame in raw_data.items()
    }
    return prices, enriched, satellite_tickers


def run_optimize(refresh: bool = False) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Preparing parameter grid search")
    prices, enriched, satellite_tickers = prepare_backtest_inputs(refresh=refresh)
    baseline_curve, baseline_diagnostics = run_rotation_backtest(prices, enriched, satellite_tickers)
    baseline_trade_count = int(baseline_diagnostics.iloc[0]["trade_count"])
    baseline_summary = build_benchmark_summary(baseline_curve, prices, baseline_trade_count)
    grid_results = run_parameter_grid_search(prices, enriched, satellite_tickers)
    output_path = write_parameter_search_report(grid_results, baseline_summary)
    logger.info("Parameter search report written: %s", output_path)
    print(f"改善パラメータ総当たりPDCAレポートを作成しました: {output_path}")


def run_refine(refresh: bool = False) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Preparing focused parameter refinement")
    prices, enriched, satellite_tickers = prepare_backtest_inputs(refresh=refresh)
    baseline_curve, baseline_diagnostics = run_rotation_backtest(prices, enriched, satellite_tickers)
    baseline_trade_count = int(baseline_diagnostics.iloc[0]["trade_count"])
    baseline_summary = build_benchmark_summary(baseline_curve, prices, baseline_trade_count)
    grid_results = run_parameter_grid_search(
        prices,
        enriched,
        satellite_tickers,
        satellite_weights=[0.30, 0.35, 0.40],
        top_satellite_counts=[3, 4],
        rebalance_frequencies=["ME"],
        drawdown_stops=[-12.0, -15.0],
        min_scores=[25.0, 35.0, 45.0],
        score_profiles=["balanced", "balanced_plus", "momentum", "adaptive"],
    )
    output_path = write_parameter_search_report(grid_results, baseline_summary)
    logger.info("Focused parameter refinement report written: %s", output_path)
    print(f"モメンタム重視を含む再検証PDCAレポートを作成しました: {output_path}")


def run_validate(refresh: bool = False, profile_name: str = DEFAULT_STRATEGY_PROFILE) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Preparing regime validation")
    prices, enriched, satellite_tickers = prepare_backtest_inputs(refresh=refresh)
    strategy_config, description = load_strategy_config(profile_name)
    validation = run_regime_validation(prices, enriched, satellite_tickers, strategy_config)
    label = f"{profile_name}: {description}"
    output_path = write_regime_validation_report(validation, label)
    logger.info("Regime validation report written: %s", output_path)
    print(f"局面別検証PDCAレポートを作成しました: {output_path}")


def run_audit(refresh: bool = False, profile_name: str = DEFAULT_STRATEGY_PROFILE) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Preparing weak-regime selection audit")
    prices, enriched, satellite_tickers = prepare_backtest_inputs(refresh=refresh)
    strategy_config, _description = load_strategy_config(profile_name)
    audits = {
        "2020_recovery": build_rebalance_selection_log(
            prices,
            enriched,
            satellite_tickers,
            strategy_config,
            "2020-01-01",
            "2020-12-31",
        ),
        "2023_ai_start": build_rebalance_selection_log(
            prices,
            enriched,
            satellite_tickers,
            strategy_config,
            "2023-01-01",
            "2023-12-31",
        ),
    }
    output_path = write_selection_audit_report(audits)
    logger.info("Selection audit report written: %s", output_path)
    print(f"弱点局面ETF採用監査レポートを作成しました: {output_path}")


def latest_csv(pattern: str) -> pd.DataFrame:
    paths = sorted((PROJECT_ROOT / "data" / "backtest").glob(pattern))
    if not paths:
        return pd.DataFrame()
    return pd.read_csv(paths[-1])


def load_recent_signal_history(limit: int = 7) -> pd.DataFrame:
    paths = sorted((PROJECT_ROOT / "data" / "processed" / "signals").glob("signals_*.csv"))
    if not paths:
        return pd.DataFrame()
    frames = []
    for path in paths[-limit:]:
        frame = pd.read_csv(path)
        frame.insert(0, "snapshot", path.stem.replace("signals_", ""))
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_recent_manual_decisions(limit: int = 7) -> pd.DataFrame:
    paths = sorted((PROJECT_ROOT / "data" / "processed" / "decisions").glob("manual_decision_sheet_*.csv"))
    if not paths:
        return pd.DataFrame()
    frames = []
    for path in paths[-limit:]:
        frame = pd.read_csv(path)
        frame.insert(0, "snapshot", path.stem.replace("manual_decision_sheet_", ""))
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def run_weekly() -> None:
    setup_logging()
    settings = load_yaml("config/settings.yaml")
    avoid_policy_name = avoid_policy_name_from_settings(settings)
    avoid_signals = avoid_signals_from_settings(settings)
    backtest_summary = latest_csv("backtest_summary_*.csv")
    parameter_results = latest_csv("parameter_search_*.csv")
    regime_validation = latest_csv("regime_validation_*.csv")
    signal_history = load_recent_signal_history()
    evaluated_signals = evaluate_signal_history(signal_history)
    signal_accuracy = summarize_signal_accuracy(evaluated_signals)
    signal_improvement_proposals = propose_signal_improvements(signal_accuracy)
    virtual_trades = evaluate_virtual_trades(signal_history)
    virtual_trade_summary = summarize_virtual_trades(virtual_trades)
    avoid_outcomes = evaluate_avoid_outcomes_for_signals(signal_history, avoid_signals)
    avoid_summary = summarize_avoid_outcomes(avoid_outcomes)
    manual_decisions = load_recent_manual_decisions()
    manual_decision_summary = summarize_manual_decisions(manual_decisions)
    output_path = write_weekly_pdca_report(
        backtest_summary,
        parameter_results,
        regime_validation,
        signal_history,
        signal_accuracy,
        evaluated_signals,
        signal_improvement_proposals,
        virtual_trades,
        virtual_trade_summary,
        avoid_outcomes,
        avoid_summary,
        avoid_policy_name,
        manual_decision_summary=manual_decision_summary,
    )
    logging.getLogger(__name__).info("Weekly report written: %s", output_path)
    print(f"週次PDCAレポートを作成しました: {output_path}")


def run_portfolio_check() -> None:
    setup_logging()
    portfolio = load_portfolio()
    issues = validate_portfolio(portfolio)
    output_path = write_portfolio_check_report(issues)
    logging.getLogger(__name__).info("Portfolio check report written: %s", output_path)
    print(f"保有CSVチェックレポートを作成しました: {output_path}")


def run_notification_summary() -> None:
    setup_logging()
    outbox_files = sorted((PROJECT_ROOT / "data" / "processed" / "notifications").glob("notification_outbox_*.jsonl"))
    if not outbox_files:
        raise FileNotFoundError("通知アウトボックスがありません。先に daily を実行してください。")
    latest_outbox = outbox_files[-1]
    payloads = load_notification_outbox(latest_outbox)
    priority_counts = count_notification_priorities(payloads)
    notification_summary = summarize_notification_payloads(payloads)
    output_path = write_notification_summary_report(priority_counts, notification_summary)
    logging.getLogger(__name__).info("Notification summary report written: %s", output_path)
    print(f"通知要約レポートを作成しました: {output_path}")


def run_notification_plan() -> None:
    setup_logging()
    outbox_files = sorted((PROJECT_ROOT / "data" / "processed" / "notifications").glob("notification_outbox_*.jsonl"))
    if not outbox_files:
        raise FileNotFoundError("通知アウトボックスがありません。先に daily を実行してください。")
    latest_outbox = outbox_files[-1]
    payloads = load_notification_outbox(latest_outbox)
    delivery_plan = notification_delivery_plan(payloads)
    output_path = write_notification_delivery_plan_report(delivery_plan)
    logging.getLogger(__name__).info("Notification delivery plan written: %s", output_path)
    print(f"通知配送計画レポートを作成しました: {output_path}")


def run_notification_packets() -> None:
    setup_logging()
    outbox_files = sorted((PROJECT_ROOT / "data" / "processed" / "notifications").glob("notification_outbox_*.jsonl"))
    if not outbox_files:
        raise FileNotFoundError("通知アウトボックスがありません。先に daily を実行してください。")
    latest_outbox = outbox_files[-1]
    payloads = load_notification_outbox(latest_outbox)
    output_paths = write_delivery_packets(payloads)
    logging.getLogger(__name__).info("Notification packets written: %s", output_paths)
    print("通知送信パケットを作成しました:")
    for output_path in output_paths:
        print(f"- {output_path}")


def run_daily_health() -> None:
    setup_logging()
    health = check_daily_artifacts()
    output_path = write_daily_health_report(health)
    logging.getLogger(__name__).info("Daily health report written: %s", output_path)
    print(f"日次ヘルスチェックレポートを作成しました: {output_path}")


def run_weekly_health() -> None:
    setup_logging()
    health = check_weekly_artifacts()
    output_path = write_weekly_health_report(health)
    logging.getLogger(__name__).info("Weekly health report written: %s", output_path)
    print(f"週次ヘルスチェックレポートを作成しました: {output_path}")


def run_operations_status() -> None:
    setup_logging()
    status = check_operations_status()
    output_path = write_operations_status_report(status)
    logging.getLogger(__name__).info("Operations status report written: %s", output_path)
    print(f"運用ステータスレポートを作成しました: {output_path}")


def run_go_live_check() -> None:
    setup_logging()
    readiness = check_go_live_readiness()
    output_path = write_go_live_readiness_report(readiness)
    logging.getLogger(__name__).info("Go-live readiness report written: %s", output_path)
    print(f"本運用GO/HOLD判定レポートを作成しました: {output_path}")


def run_decision_sheet() -> None:
    setup_logging()
    outbox_files = sorted((PROJECT_ROOT / "data" / "processed" / "notifications").glob("notification_outbox_*.jsonl"))
    if not outbox_files:
        raise FileNotFoundError("通知アウトボックスがありません。先に daily を実行してください。")
    payloads = load_notification_outbox(outbox_files[-1])
    delivery_plan = notification_delivery_plan(payloads)
    output_path = write_manual_decision_sheet(delivery_plan)
    logging.getLogger(__name__).info("Manual decision sheet written: %s", output_path)
    print(f"手動判断シートを作成しました: {output_path}")


def _latest_signals_path() -> tuple[datetime, str]:
    signals_dir = PROJECT_ROOT / "data" / "processed" / "signals"
    paths = sorted(signals_dir.glob("signals_*.csv"))
    if not paths:
        raise FileNotFoundError("シグナルCSVがありません。先に daily または daily-ops を実行してください。")
    latest = paths[-1]
    try:
        report_date = datetime.strptime(latest.stem.replace("signals_", ""), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"シグナルCSVの日付を読めません: {latest}") from exc
    return report_date, str(latest)


def _write_latest_mobile_summary() -> str:
    report_date, signals_path = _latest_signals_path()
    signal_table = pd.read_csv(signals_path)
    readiness = check_go_live_readiness(report_date)
    decision_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "decisions"
        / f"manual_decision_sheet_{report_date:%Y-%m-%d}.csv"
    )
    manual_summary = pd.DataFrame()
    if decision_path.exists():
        manual_summary = summarize_manual_decisions(pd.read_csv(decision_path))
    output_path = write_mobile_summary(
        signal_table,
        readiness=readiness,
        manual_decision_summary=manual_summary,
        report_date=report_date,
    )
    return str(output_path)


def _load_latest_signal_context() -> tuple[datetime, pd.DataFrame, pd.DataFrame]:
    report_date, signals_path = _latest_signals_path()
    signal_table = pd.read_csv(signals_path)
    readiness = check_go_live_readiness(report_date)
    return report_date, signal_table, readiness


def _write_latest_decision_brief() -> str:
    report_date, signal_table, readiness = _load_latest_signal_context()
    output_path = write_decision_brief(signal_table, readiness=readiness, report_date=report_date)
    return str(output_path)


def run_mobile_summary() -> None:
    setup_logging()
    output_path = _write_latest_mobile_summary()
    logging.getLogger(__name__).info("Mobile summary written: %s", output_path)
    print(f"携帯向け要約を作成しました: {output_path}")


def run_decision_brief() -> None:
    setup_logging()
    output_path = _write_latest_decision_brief()
    logging.getLogger(__name__).info("Decision brief written: %s", output_path)
    print(f"買い判断ブリーフを作成しました: {output_path}")


def run_line_summary() -> None:
    setup_logging()
    output_path = _write_latest_mobile_summary()
    text = Path(output_path).read_text(encoding="utf-8")
    status = send_line_push_message(text)
    logging.getLogger(__name__).info("LINE summary sent: %s status=%s", output_path, status)
    print(f"LINEへ携帯向け要約を送信しました: {output_path}")


def run_line_decision_brief() -> None:
    setup_logging()
    output_path = _write_latest_decision_brief()
    text = Path(output_path).read_text(encoding="utf-8")
    status = send_line_push_message(text)
    logging.getLogger(__name__).info("LINE decision brief sent: %s status=%s", output_path, status)
    print(f"LINEへ買い判断ブリーフを送信しました: {output_path}")


def run_line_broadcast_summary() -> None:
    setup_logging()
    output_path = _write_latest_mobile_summary()
    text = Path(output_path).read_text(encoding="utf-8")
    status = send_line_broadcast_message(text)
    logging.getLogger(__name__).info("LINE broadcast summary sent: %s status=%s", output_path, status)
    print(f"LINEへ携帯向け要約をブロードキャスト送信しました: {output_path}")


def run_line_broadcast_decision_brief() -> None:
    setup_logging()
    output_path = _write_latest_decision_brief()
    text = Path(output_path).read_text(encoding="utf-8")
    status = send_line_broadcast_message(text)
    logging.getLogger(__name__).info("LINE broadcast decision brief sent: %s status=%s", output_path, status)
    print(f"LINEへ買い判断ブリーフをブロードキャスト送信しました: {output_path}")


def run_line_test() -> None:
    setup_logging()
    message = "ETF Rotation LINE test: OK"
    status = send_line_push_message(message)
    logging.getLogger(__name__).info("LINE test sent: status=%s", status)
    print("LINEへテストメッセージを送信しました。")


def run_line_broadcast_test() -> None:
    setup_logging()
    message = "ETF Rotation LINE broadcast test: OK"
    status = send_line_broadcast_message(message)
    logging.getLogger(__name__).info("LINE broadcast test sent: status=%s", status)
    print("LINEへブロードキャストのテストメッセージを送信しました。")


def run_line_check() -> None:
    setup_logging()
    settings = check_line_settings()
    missing = [name for name, exists in settings.items() if not exists]
    if missing:
        print(f"LINE設定: 未設定あり ({', '.join(missing)})")
        return
    print("LINE設定: OK")


def run_daily_operations(refresh: bool = False, profile_name: str = DEFAULT_STRATEGY_PROFILE) -> None:
    run_portfolio_check()
    run_daily(refresh=refresh, profile_name=profile_name)
    run_mobile_summary()
    run_notification_summary()
    run_notification_plan()
    run_notification_packets()
    run_decision_sheet()
    run_daily_health()
    run_operations_status()
    run_go_live_check()


def run_replay(refresh: bool = False) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = load_yaml("config/settings.yaml")
    universe = load_yaml("config/etf_universe.yaml")
    theme_map_config = load_yaml("config/theme_map.yaml")
    theme_risk_mode = theme_risk_overlay_mode_from_settings(settings)
    trade_plan_multipliers = trade_plan_multipliers_from_settings(settings)
    avoid_policy_name = avoid_policy_name_from_settings(settings)
    avoid_signals = avoid_signals_from_settings(settings)
    entries = flatten_universe(universe)
    satellite_tickers = [entry["ticker"] for entry in entries if entry["bucket"] == "satellite"]
    tickers = sorted({entry["ticker"] for entry in entries} | {"SPY", "QQQ"})
    period = str(settings["data"].get("period", "10y"))
    interval = str(settings["data"].get("interval", "1d"))
    logger.info("Loading replay data for %s", ", ".join(tickers))
    raw_data = load_price_data(tickers, period=period, interval=interval, refresh=refresh)
    qqq_close = raw_data["QQQ"]["Adj Close"]
    spy_close = raw_data["SPY"]["Adj Close"]
    enriched = {
        ticker: add_indicators(frame, qqq_close=qqq_close, spy_close=spy_close)
        for ticker, frame in raw_data.items()
    }
    prices = build_price_matrix(raw_data)
    snapshot_dates = replay_snapshot_dates(prices)
    signal_history = build_historical_signal_history(
        entries,
        theme_map_config,
        enriched,
        snapshot_dates,
        theme_risk_mode=theme_risk_mode,
        trade_plan_multipliers=trade_plan_multipliers,
    )
    baseline_signal_history = build_historical_signal_history(
        entries,
        theme_map_config,
        enriched,
        snapshot_dates,
        apply_theme_risk=False,
        trade_plan_multipliers=trade_plan_multipliers,
    )
    logger.info("Replay signal histories built: overlay=%s baseline=%s", len(signal_history), len(baseline_signal_history))
    evaluated_signals = evaluate_signal_history(signal_history)
    baseline_evaluated_signals = evaluate_signal_history(baseline_signal_history)
    signal_accuracy = summarize_signal_accuracy(evaluated_signals)
    virtual_trades = evaluate_virtual_trades(signal_history)
    baseline_virtual_trades = evaluate_virtual_trades(baseline_signal_history)
    virtual_trade_summary = summarize_virtual_trades(virtual_trades)
    baseline_virtual_trade_summary = summarize_virtual_trades(baseline_virtual_trades)
    theme_risk_overlay_comparison = summarize_theme_risk_overlay_effect(
        baseline_signal_history,
        signal_history,
        baseline_evaluated_signals,
        evaluated_signals,
        baseline_virtual_trade_summary,
        virtual_trade_summary,
    )
    theme_risk_overlay_blocks = summarize_theme_risk_overlay_blocks(baseline_signal_history, signal_history)
    relaxed_baseline_signal_history = apply_relaxed_theme_entry_policy(baseline_signal_history, apply_theme_risk=False)
    relaxed_overlay_signal_history = apply_relaxed_theme_entry_policy(baseline_signal_history, apply_theme_risk=True)
    relaxed_baseline_evaluated = evaluate_signal_history(relaxed_baseline_signal_history)
    relaxed_overlay_evaluated = evaluate_signal_history(relaxed_overlay_signal_history)
    relaxed_baseline_virtual_summary = summarize_virtual_trades(evaluate_virtual_trades(relaxed_baseline_signal_history))
    relaxed_overlay_virtual_summary = summarize_virtual_trades(evaluate_virtual_trades(relaxed_overlay_signal_history))
    relaxed_theme_risk_overlay_comparison = summarize_theme_risk_overlay_effect(
        relaxed_baseline_signal_history,
        relaxed_overlay_signal_history,
        relaxed_baseline_evaluated,
        relaxed_overlay_evaluated,
        relaxed_baseline_virtual_summary,
        relaxed_overlay_virtual_summary,
    )
    relaxed_theme_risk_overlay_blocks = summarize_theme_risk_overlay_blocks(
        relaxed_baseline_signal_history,
        relaxed_overlay_signal_history,
    )
    theme_risk_policy_mode_results = run_theme_risk_policy_mode_search(baseline_signal_history)
    all_avoid_outcomes = evaluate_avoid_outcomes(signal_history)
    avoid_outcomes = evaluate_avoid_outcomes_for_signals(signal_history, avoid_signals)
    avoid_summary = summarize_avoid_outcomes(avoid_outcomes)
    entry_parameter_results = run_entry_parameter_search(signal_history)
    avoid_by_signal = summarize_avoid_outcomes_by_signal(avoid_outcomes)
    avoid_policy_results = run_avoid_policy_search(all_avoid_outcomes)
    logger.info("Replay PDCA base evaluations complete")
    strategy_config, _description = load_strategy_config(DEFAULT_STRATEGY_PROFILE)
    signal_curve, signal_diagnostics = run_signal_execution_backtest(
        prices,
        signal_history,
        SignalExecutionConfig(entry_multiplier=1.04, stop_multiplier=0.95),
    )
    signal_execution_summary = build_benchmark_summary(
        signal_curve,
        prices,
        int(signal_diagnostics.iloc[0]["trade_count"]) if not signal_diagnostics.empty else 0,
    )
    signal_execution_grid = run_signal_execution_grid_search(prices, signal_history)
    logger.info("Replay signal execution checks complete")
    hybrid_curve, hybrid_diagnostics = run_hybrid_rotation_signal_backtest(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        HybridSignalConfig(signal_overlay_weight=0.10, entry_multiplier=1.02, stop_multiplier=0.95),
    )
    hybrid_trade_count = 0
    if not hybrid_diagnostics.empty:
        hybrid_trade_count = int(hybrid_diagnostics.iloc[0]["rotation_trade_count"]) + int(
            hybrid_diagnostics.iloc[0]["signal_exit_count"]
        )
    hybrid_summary = build_benchmark_summary(hybrid_curve, prices, hybrid_trade_count)
    logger.info("Replay hybrid base backtest complete")
    hybrid_grid = run_hybrid_signal_grid_search(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        overlay_weights=[0.10, 0.15],
        entry_multipliers=[1.04, 1.06],
        stop_multipliers=[0.95],
        holding_days=[40, 60],
        max_positions_list=[2],
        candidate_policies=["watch_score_gate", "score_gate"],
        min_score_thresholds=[65.0, 70.0],
        min_rr_values=[1.0, 1.5, 2.0],
        acceleration_overlay_modes=["normal"],
    )
    logger.info("Replay hybrid grid search complete")
    hybrid_rule_search_config = HybridSignalConfig(
        signal_overlay_weight=0.15,
        entry_multiplier=1.04,
        stop_multiplier=0.95,
        max_holding_days=40,
        max_signal_positions=2,
        candidate_policy="watch_score_gate",
        min_etf_score=70.0,
        min_theme_score=70.0,
        min_rr=1.0,
        acceleration_overlay_mode="normal",
        relaxed_signal_tickers=("SMH", "SOXX"),
        relaxed_min_etf_score=65.0,
        relaxed_min_theme_score=65.0,
        relaxed_min_rr=1.0,
    )
    hybrid_regime_config = copy_hybrid_signal_config(
        hybrid_rule_search_config,
        max_entry_day_loss_pct=-3.0,
        ticker_min_etf_scores={"URA": 75.0},
        ticker_min_rr_values={"URA": 2.5},
    )
    hybrid_ticker_rule_config = copy_hybrid_signal_config(
        hybrid_rule_search_config,
        max_entry_day_loss_pct=-3.0,
    )
    hybrid_trade_log_records: list[dict[str, object]] = []
    run_hybrid_rotation_signal_backtest(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        hybrid_regime_config,
        hybrid_trade_log_records,
    )
    hybrid_trade_log = pd.DataFrame(hybrid_trade_log_records)
    hybrid_attribution_2024 = summarize_hybrid_trade_attribution(hybrid_trade_log, "2024-01-01", "2024-12-31")
    hybrid_regime_validation = run_hybrid_regime_validation(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        hybrid_regime_config,
    )
    hybrid_entry_guard_results = run_hybrid_entry_guard_search(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        hybrid_regime_config,
    )
    hybrid_acceleration_mode_results = run_hybrid_acceleration_mode_search(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        hybrid_regime_config,
    )
    hybrid_ticker_rule_results = run_hybrid_ticker_rule_search(
        prices,
        enriched,
        satellite_tickers,
        signal_history,
        strategy_config,
        hybrid_ticker_rule_config,
    )
    hybrid_theme_risk_mode_results = run_theme_risk_hybrid_mode_search(
        prices,
        enriched,
        satellite_tickers,
        baseline_signal_history,
        strategy_config,
        hybrid_regime_config,
    )
    logger.info("Replay hybrid follow-up checks complete")
    output_path = write_replay_pdca_report(
        signal_history,
        signal_accuracy,
        virtual_trades,
        virtual_trade_summary,
        avoid_outcomes,
        avoid_summary,
        entry_parameter_results,
        avoid_by_signal,
        avoid_policy_results,
        signal_execution_summary,
        signal_diagnostics,
        signal_execution_grid,
        hybrid_summary,
        hybrid_diagnostics,
        hybrid_grid,
        hybrid_regime_validation,
        hybrid_entry_guard_results,
        hybrid_acceleration_mode_results,
        hybrid_ticker_rule_results,
        hybrid_theme_risk_mode_results,
        theme_risk_overlay_comparison,
        relaxed_theme_risk_overlay_comparison,
        theme_risk_policy_mode_results,
        theme_risk_overlay_blocks,
        relaxed_theme_risk_overlay_blocks,
        hybrid_trade_log,
        hybrid_attribution_2024,
        trade_plan_multipliers,
        avoid_policy_name,
    )
    logger.info("Replay PDCA report written: %s", output_path)
    print(f"履歴再生PDCAレポートを作成しました: {output_path}")


def run_replay_quick(refresh: bool = False) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = load_yaml("config/settings.yaml")
    universe = load_yaml("config/etf_universe.yaml")
    theme_map_config = load_yaml("config/theme_map.yaml")
    theme_risk_mode = theme_risk_overlay_mode_from_settings(settings)
    trade_plan_multipliers = trade_plan_multipliers_from_settings(settings)
    avoid_policy_name = avoid_policy_name_from_settings(settings)
    avoid_signals = avoid_signals_from_settings(settings)
    entries = flatten_universe(universe)
    tickers = sorted({entry["ticker"] for entry in entries} | {"SPY", "QQQ"})
    period = str(settings["data"].get("period", "10y"))
    interval = str(settings["data"].get("interval", "1d"))
    logger.info("Loading quick replay data for %s", ", ".join(tickers))
    raw_data = load_price_data(tickers, period=period, interval=interval, refresh=refresh)
    qqq_close = raw_data["QQQ"]["Adj Close"]
    spy_close = raw_data["SPY"]["Adj Close"]
    enriched = {
        ticker: add_indicators(frame, qqq_close=qqq_close, spy_close=spy_close)
        for ticker, frame in raw_data.items()
    }
    prices = build_price_matrix(raw_data)
    snapshot_dates = replay_snapshot_dates(prices)
    signal_history = build_historical_signal_history(
        entries,
        theme_map_config,
        enriched,
        snapshot_dates,
        theme_risk_mode=theme_risk_mode,
        trade_plan_multipliers=trade_plan_multipliers,
    )
    baseline_signal_history = build_historical_signal_history(
        entries,
        theme_map_config,
        enriched,
        snapshot_dates,
        apply_theme_risk=False,
        trade_plan_multipliers=trade_plan_multipliers,
    )
    evaluated_signals = evaluate_signal_history(signal_history)
    baseline_evaluated_signals = evaluate_signal_history(baseline_signal_history)
    signal_accuracy = summarize_signal_accuracy(evaluated_signals)
    virtual_trades = evaluate_virtual_trades(signal_history)
    baseline_virtual_trades = evaluate_virtual_trades(baseline_signal_history)
    virtual_trade_summary = summarize_virtual_trades(virtual_trades)
    baseline_virtual_trade_summary = summarize_virtual_trades(baseline_virtual_trades)
    theme_risk_overlay_comparison = summarize_theme_risk_overlay_effect(
        baseline_signal_history,
        signal_history,
        baseline_evaluated_signals,
        evaluated_signals,
        baseline_virtual_trade_summary,
        virtual_trade_summary,
    )
    theme_risk_overlay_blocks = summarize_theme_risk_overlay_blocks(baseline_signal_history, signal_history)
    relaxed_baseline_signal_history = apply_relaxed_theme_entry_policy(baseline_signal_history, apply_theme_risk=False)
    relaxed_overlay_signal_history = apply_relaxed_theme_entry_policy(baseline_signal_history, apply_theme_risk=True)
    relaxed_baseline_evaluated = evaluate_signal_history(relaxed_baseline_signal_history)
    relaxed_overlay_evaluated = evaluate_signal_history(relaxed_overlay_signal_history)
    relaxed_baseline_virtual_summary = summarize_virtual_trades(evaluate_virtual_trades(relaxed_baseline_signal_history))
    relaxed_overlay_virtual_summary = summarize_virtual_trades(evaluate_virtual_trades(relaxed_overlay_signal_history))
    relaxed_theme_risk_overlay_comparison = summarize_theme_risk_overlay_effect(
        relaxed_baseline_signal_history,
        relaxed_overlay_signal_history,
        relaxed_baseline_evaluated,
        relaxed_overlay_evaluated,
        relaxed_baseline_virtual_summary,
        relaxed_overlay_virtual_summary,
    )
    relaxed_theme_risk_overlay_blocks = summarize_theme_risk_overlay_blocks(
        relaxed_baseline_signal_history,
        relaxed_overlay_signal_history,
    )
    theme_risk_policy_mode_results = run_theme_risk_policy_mode_search(baseline_signal_history)
    all_avoid_outcomes = evaluate_avoid_outcomes(signal_history)
    avoid_outcomes = evaluate_avoid_outcomes_for_signals(signal_history, avoid_signals)
    avoid_summary = summarize_avoid_outcomes(avoid_outcomes)
    entry_parameter_results = run_entry_parameter_search(signal_history)
    avoid_by_signal = summarize_avoid_outcomes_by_signal(avoid_outcomes)
    avoid_policy_results = run_avoid_policy_search(all_avoid_outcomes)
    output_path = write_replay_pdca_report(
        signal_history,
        signal_accuracy,
        virtual_trades,
        virtual_trade_summary,
        avoid_outcomes,
        avoid_summary,
        entry_parameter_results,
        avoid_by_signal,
        avoid_policy_results,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        theme_risk_overlay_comparison,
        relaxed_theme_risk_overlay_comparison,
        theme_risk_policy_mode_results,
        theme_risk_overlay_blocks,
        relaxed_theme_risk_overlay_blocks,
        None,
        None,
        trade_plan_multipliers,
        avoid_policy_name,
    )
    logger.info("Quick replay PDCA report written: %s", output_path)
    print(f"軽量履歴再生PDCAレポートを作成しました: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MASATO Tactical ETF Engine")
    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "daily",
            "daily-ops",
            "backtest",
            "optimize",
            "refine",
            "validate",
            "audit",
            "weekly",
            "portfolio-check",
            "notification-summary",
            "notification-plan",
            "notification-packets",
            "daily-health",
            "weekly-health",
            "operations-status",
            "go-live-check",
            "decision-sheet",
            "mobile-summary",
            "decision-brief",
            "line-check",
            "line-test",
            "line-broadcast-test",
            "line-summary",
            "line-broadcast-summary",
            "line-decision-brief",
            "line-broadcast-decision-brief",
            "replay",
            "replay-quick",
        ],
        default="daily",
    )
    parser.add_argument("--refresh", action="store_true", help="価格データを再取得します")
    parser.add_argument("--profile", default=DEFAULT_STRATEGY_PROFILE, help="strategy_profiles.yamlのプロファイル名")
    args = parser.parse_args()
    if args.command == "refine":
        run_refine(refresh=args.refresh)
    elif args.command == "daily-ops":
        run_daily_operations(refresh=args.refresh, profile_name=args.profile)
    elif args.command == "replay":
        run_replay(refresh=args.refresh)
    elif args.command == "replay-quick":
        run_replay_quick(refresh=args.refresh)
    elif args.command == "weekly":
        run_weekly()
    elif args.command == "portfolio-check":
        run_portfolio_check()
    elif args.command == "notification-summary":
        run_notification_summary()
    elif args.command == "notification-plan":
        run_notification_plan()
    elif args.command == "notification-packets":
        run_notification_packets()
    elif args.command == "daily-health":
        run_daily_health()
    elif args.command == "weekly-health":
        run_weekly_health()
    elif args.command == "operations-status":
        run_operations_status()
    elif args.command == "go-live-check":
        run_go_live_check()
    elif args.command == "decision-sheet":
        run_decision_sheet()
    elif args.command == "mobile-summary":
        run_mobile_summary()
    elif args.command == "decision-brief":
        run_decision_brief()
    elif args.command == "line-check":
        run_line_check()
    elif args.command == "line-test":
        run_line_test()
    elif args.command == "line-broadcast-test":
        run_line_broadcast_test()
    elif args.command == "line-summary":
        run_line_summary()
    elif args.command == "line-broadcast-summary":
        run_line_broadcast_summary()
    elif args.command == "line-decision-brief":
        run_line_decision_brief()
    elif args.command == "line-broadcast-decision-brief":
        run_line_broadcast_decision_brief()
    elif args.command == "audit":
        run_audit(refresh=args.refresh, profile_name=args.profile)
    elif args.command == "validate":
        run_validate(refresh=args.refresh, profile_name=args.profile)
    elif args.command == "optimize":
        run_optimize(refresh=args.refresh)
    elif args.command == "backtest":
        run_backtest(refresh=args.refresh, profile_name=args.profile)
    else:
        run_daily(refresh=args.refresh, profile_name=args.profile)


if __name__ == "__main__":
    main()
