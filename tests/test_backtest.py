from __future__ import annotations

import pandas as pd

from src.backtest_engine import (
    BacktestConfig,
    HybridSignalConfig,
    SignalExecutionConfig,
    backtest_config_from_profile,
    build_benchmark_summary,
    calculate_cumulative_return,
    calculate_max_drawdown,
    choose_satellites,
    copy_hybrid_signal_config,
    filter_hybrid_signal_candidates,
    is_acceleration_regime,
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
    score_backtest_snapshot,
    summarize_hybrid_trade_attribution,
)


def test_calculate_cumulative_return() -> None:
    curve = pd.Series([100, 110, 121])
    assert calculate_cumulative_return(curve) == 21.0


def test_calculate_max_drawdown() -> None:
    curve = pd.Series([100, 120, 90, 130])
    assert round(calculate_max_drawdown(curve), 2) == -25.0


def test_backtest_config_from_profile_uses_yaml_values() -> None:
    config = backtest_config_from_profile(
        {
            "satellite_weight": 0.35,
            "top_satellites": 4,
            "rebalance_frequency": "ME",
            "stop_new_buy_drawdown_pct": -15.0,
            "min_satellite_score": 45.0,
            "score_profile": "balanced",
        }
    )
    assert config.satellite_weight == 0.35
    assert config.top_satellites == 4
    assert config.stop_new_buy_drawdown_pct == -15.0


def test_choose_satellites_takes_top_scores() -> None:
    date = pd.Timestamp("2024-01-31")
    scores = pd.DataFrame({"A": [50], "B": [80], "C": [70]}, index=[date])
    assert choose_satellites(scores, date, ["A", "B", "C"], top_n=2) == ["B", "C"]


def test_is_acceleration_regime_detects_qqq_and_leader_strength() -> None:
    date = pd.Timestamp("2024-01-31")
    frames = {
        "QQQ": pd.DataFrame(
            {
                "price": [120.0],
                "ma_50": [110.0],
                "ma_200": [100.0],
                "ma_50_slope": [0.03],
                "return_3m": [0.12],
                "rsi_14": [68.0],
            },
            index=[date],
        ),
        "SMH": pd.DataFrame({"return_3m": [0.18]}, index=[date]),
    }
    assert is_acceleration_regime(frames, date)


def test_balanced_plus_scores_leader_momentum_above_balanced() -> None:
    dates = pd.date_range("2024-01-01", periods=3)
    indicators = pd.DataFrame(
        {
            "price": [120.0, 121.0, 122.0],
            "ma_21": [115.0, 116.0, 117.0],
            "ma_50": [110.0, 111.0, 112.0],
            "ma_200": [100.0, 100.5, 101.0],
            "ma_50_slope": [0.03, 0.03, 0.03],
            "ma_200_slope": [0.02, 0.02, 0.02],
            "return_1m": [0.07, 0.07, 0.07],
            "return_3m": [0.14, 0.14, 0.14],
            "return_6m": [0.22, 0.22, 0.22],
            "return_12m": [0.32, 0.32, 0.32],
            "rs_qqq_3m": [0.07, 0.07, 0.07],
            "rs_spy_3m": [0.08, 0.08, 0.08],
            "drawdown_52w_pct": [-3.5, -3.5, -3.5],
            "rsi_14": [64.0, 64.0, 64.0],
            "three_day_return_pct": [3.0, 3.0, 3.0],
        },
        index=dates,
    )
    balanced = score_backtest_snapshot(indicators, profile="balanced").iloc[-1]
    balanced_plus = score_backtest_snapshot(indicators, profile="balanced_plus").iloc[-1]
    assert balanced_plus > balanced


def test_run_rotation_backtest_returns_curve_and_summary() -> None:
    dates = pd.date_range("2020-01-01", periods=420, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100 + index * 0.1 for index in range(420)],
            "QQQ": [100 + index * 0.12 for index in range(420)],
            "SMH": [100 + index * 0.2 for index in range(420)],
            "XLU": [100 + index * 0.03 for index in range(420)],
        },
        index=dates,
    )

    def indicators_for(ticker: str) -> pd.DataFrame:
        price = prices[ticker]
        return pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )

    frames = {ticker: indicators_for(ticker) for ticker in prices.columns}
    curve, diagnostics = run_rotation_backtest(
        prices,
        frames,
        ["SMH", "XLU"],
        BacktestConfig(rebalance_frequency="ME"),
    )
    summary = build_benchmark_summary(curve, prices, int(diagnostics.iloc[0]["trade_count"]))
    assert not curve.empty
    assert "MASATO Rotation" in summary["strategy"].tolist()


def test_run_parameter_grid_search_sorts_results() -> None:
    dates = pd.date_range("2020-01-01", periods=420, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100 + index * 0.1 for index in range(420)],
            "QQQ": [100 + index * 0.12 for index in range(420)],
            "SMH": [100 + index * 0.2 for index in range(420)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    result = run_parameter_grid_search(
        prices,
        frames,
        ["SMH"],
        satellite_weights=[0.15, 0.25],
        top_satellite_counts=[1],
        rebalance_frequencies=["ME"],
        drawdown_stops=[-8.0],
        min_scores=[35.0],
    )
    assert len(result) == 2
    assert result.iloc[0]["risk_adjusted_rank_score"] >= result.iloc[1]["risk_adjusted_rank_score"]


def test_run_regime_validation_returns_comparison_rows() -> None:
    dates = pd.date_range("2020-01-01", periods=520, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100 + index * 0.1 for index in range(520)],
            "QQQ": [100 + index * 0.12 for index in range(520)],
            "SMH": [100 + index * 0.2 for index in range(520)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    result = run_regime_validation(
        prices,
        frames,
        ["SMH"],
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        regimes=[{"name": "sample", "start": "2020-01-01", "end": "2021-12-31"}],
    )
    assert result.iloc[0]["regime"] == "sample"
    assert "vs_qqq_pct" in result.columns


def test_run_signal_execution_backtest_uses_buy_signals() -> None:
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.1 for index in range(30)],
            "QQQ": [100.0 + index * 0.1 for index in range(30)],
            "SMH": [100.0 + index * 0.5 for index in range(30)],
        },
        index=dates,
    )
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": dates[1].date().isoformat(),
                "ETF": "SMH",
                "判定": "買い候補",
                "ETFスコア": 80.0,
                "現在価格": 101.0,
                "第1買い": 101.0,
                "保守目標": 105.0,
                "停止価格": 95.0,
            }
        ]
    )
    curve, diagnostics = run_signal_execution_backtest(
        prices,
        signal_history,
        SignalExecutionConfig(entry_multiplier=1.0, stop_multiplier=1.0, max_holding_days=20),
    )
    assert not curve.empty
    assert int(diagnostics.iloc[0]["trade_count"]) >= 1


def test_run_signal_execution_grid_search_returns_ranked_rows() -> None:
    dates = pd.date_range("2026-01-01", periods=35, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.1 for index in range(35)],
            "QQQ": [100.0 + index * 0.1 for index in range(35)],
            "SMH": [100.0 + index * 0.4 for index in range(35)],
        },
        index=dates,
    )
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": dates[1].date().isoformat(),
                "ETF": "SMH",
                "判定": "買い候補",
                "ETFスコア": 80.0,
                "現在価格": 100.4,
                "第1買い": 100.4,
                "保守目標": 104.0,
                "停止価格": 95.0,
            }
        ]
    )
    result = run_signal_execution_grid_search(
        prices,
        signal_history,
        entry_multipliers=[1.0],
        stop_multipliers=[1.0],
        holding_days=[20],
        max_positions_list=[2, 4],
    )
    assert len(result) == 2
    assert "risk_adjusted_rank_score" in result.columns


def test_run_hybrid_rotation_signal_backtest_keeps_rotation_and_adds_signals() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(320)],
            "QQQ": [100.0 + index * 0.10 for index in range(320)],
            "SMH": [100.0 + index * 0.25 for index in range(320)],
            "XLU": [100.0 + index * 0.03 for index in range(320)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "買い候補",
                "ETFスコア": 80.0,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    trade_log: list[dict[str, object]] = []
    curve, diagnostics = run_hybrid_rotation_signal_backtest(
        prices,
        frames,
        ["SMH", "XLU"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=2),
        HybridSignalConfig(signal_overlay_weight=0.10, entry_multiplier=1.0, max_holding_days=30),
        trade_log,
    )
    assert not curve.empty
    assert int(diagnostics.iloc[0]["rotation_trade_count"]) > 0
    assert int(diagnostics.iloc[0]["signal_entry_count"]) >= 1
    assert trade_log
    assert trade_log[0]["ETF"] == "SMH"


def test_run_hybrid_signal_grid_search_returns_ranked_rows() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(320)],
            "QQQ": [100.0 + index * 0.10 for index in range(320)],
            "SMH": [100.0 + index * 0.25 for index in range(320)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "買い候補",
                "ETFスコア": 80.0,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    result = run_hybrid_signal_grid_search(
        prices,
        frames,
        ["SMH"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        overlay_weights=[0.05, 0.10],
        entry_multipliers=[1.0],
        stop_multipliers=[1.0],
        holding_days=[30],
        max_positions_list=[2],
        candidate_policies=["strict_buy"],
        acceleration_overlay_modes=["normal"],
    )
    assert len(result) == 2
    assert "risk_adjusted_rank_score" in result.columns


def test_hybrid_score_gate_can_use_high_score_watch_signals() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(320)],
            "QQQ": [100.0 + index * 0.10 for index in range(320)],
            "SMH": [100.0 + index * 0.25 for index in range(320)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "見送り",
                "ETFスコア": 72.0,
                "テーマスコア": 72.0,
                "RR": 2.1,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    curve, diagnostics = run_hybrid_rotation_signal_backtest(
        prices,
        frames,
        ["SMH"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        HybridSignalConfig(
            signal_overlay_weight=0.10,
            entry_multiplier=1.0,
            max_holding_days=30,
            candidate_policy="watch_score_gate",
            min_etf_score=70.0,
            min_theme_score=70.0,
            min_rr=2.0,
        ),
    )
    assert not curve.empty
    assert int(diagnostics.iloc[0]["signal_entry_count"]) >= 1


def test_hybrid_acceleration_mode_blocks_new_signal_entries() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(320)],
            "QQQ": [100.0 + index * 0.20 for index in range(320)],
            "SMH": [100.0 + index * 0.35 for index in range(320)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 60.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "見送り",
                "ETFスコア": 72.0,
                "テーマスコア": 72.0,
                "RR": 2.1,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    curve, diagnostics = run_hybrid_rotation_signal_backtest(
        prices,
        frames,
        ["SMH"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        HybridSignalConfig(
            candidate_policy="watch_score_gate",
            acceleration_overlay_mode="block_new_entries",
            entry_multiplier=1.0,
        ),
    )
    assert not curve.empty
    assert int(diagnostics.iloc[0]["signal_entry_count"]) == 0


def test_run_hybrid_regime_validation_returns_regime_rows() -> None:
    dates = pd.date_range("2023-01-01", periods=520, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(520)],
            "QQQ": [100.0 + index * 0.10 for index in range(520)],
            "SMH": [100.0 + index * 0.25 for index in range(520)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[300]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "見送り",
                "ETFスコア": 72.0,
                "テーマスコア": 72.0,
                "RR": 2.1,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    result = run_hybrid_regime_validation(
        prices,
        frames,
        ["SMH"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        HybridSignalConfig(candidate_policy="watch_score_gate", min_etf_score=70.0, min_theme_score=70.0),
        regimes=[{"name": "sample", "start": "2024-01-01", "end": "2024-12-31"}],
    )
    assert result.iloc[0]["regime"] == "sample"
    assert "vs_rotation_pct" in result.columns
    assert "signal_entry_count" in result.columns


def test_hybrid_entry_guard_search_returns_guard_rows() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    smh_prices = [100.0 + index * 0.20 for index in range(320)]
    smh_prices[260] = smh_prices[259] * 0.95
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(320)],
            "QQQ": [100.0 + index * 0.10 for index in range(320)],
            "SMH": smh_prices,
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "見送り",
                "ETFスコア": 72.0,
                "テーマスコア": 72.0,
                "RR": 2.1,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    result = run_hybrid_entry_guard_search(
        prices,
        frames,
        ["SMH"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        HybridSignalConfig(candidate_policy="watch_score_gate", entry_multiplier=1.0),
        max_entry_day_loss_values=[-100.0, -3.0],
    )
    assert len(result) == 2
    assert "max_entry_day_loss_pct" in result.columns


def test_hybrid_acceleration_mode_search_returns_mode_rows() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.08 for index in range(320)],
            "QQQ": [100.0 + index * 0.20 for index in range(320)],
            "SMH": [100.0 + index * 0.35 for index in range(320)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 60.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "SMH",
                "判定": "見送り",
                "ETFスコア": 72.0,
                "テーマスコア": 72.0,
                "RR": 2.1,
                "現在価格": float(prices.at[signal_date, "SMH"]),
                "第1買い": float(prices.at[signal_date, "SMH"]),
                "保守目標": float(prices.at[signal_date, "SMH"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "SMH"]) * 0.95,
            }
        ]
    )
    result = run_hybrid_acceleration_mode_search(
        prices,
        frames,
        ["SMH"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        HybridSignalConfig(candidate_policy="watch_score_gate", entry_multiplier=1.0),
        acceleration_modes=["normal", "block_new_entries"],
    )
    assert len(result) == 2
    assert "acceleration_overlay_mode" in result.columns


def test_summarize_hybrid_trade_attribution_sorts_weakest_etf_first() -> None:
    trades = pd.DataFrame(
        [
            {"ETF": "SMH", "exit_date": "2024-08-05", "return_pct": -12.0},
            {"ETF": "SOXX", "exit_date": "2024-08-05", "return_pct": -8.0},
            {"ETF": "URA", "exit_date": "2025-01-05", "return_pct": 9.0},
        ]
    )
    result = summarize_hybrid_trade_attribution(trades, "2024-01-01", "2024-12-31")
    assert result.iloc[0]["ETF"] == "SMH"
    assert result.iloc[0]["total_return_pct"] == -12.0
    assert len(result) == 2


def test_filter_hybrid_signal_candidates_applies_ticker_specific_gates() -> None:
    signals = pd.DataFrame(
        [
            {"ETF": "URA", "判定": "押し目待ち", "ETFスコア": 72.0, "テーマスコア": 78.0, "RR": 2.2},
            {"ETF": "SMH", "判定": "押し目待ち", "ETFスコア": 74.0, "テーマスコア": 78.0, "RR": 2.2},
        ]
    )
    result = filter_hybrid_signal_candidates(
        signals,
        HybridSignalConfig(
            candidate_policy="watch_score_gate",
            min_etf_score=65.0,
            min_theme_score=65.0,
            min_rr=2.0,
            ticker_min_etf_scores={"URA": 75.0},
        ),
    )
    assert result["ETF"].tolist() == ["SMH"]


def test_filter_hybrid_signal_candidates_can_relax_rr_for_high_score_watch_signals() -> None:
    signals = pd.DataFrame(
        [
            {"ETF": "SMH", "判定": "見送り", "ETFスコア": 86.0, "テーマスコア": 72.0, "RR": 1.1},
            {"ETF": "SOXX", "判定": "見送り", "ETFスコア": 84.0, "テーマスコア": 72.0, "RR": 0.8},
            {"ETF": "URA", "判定": "見送り", "ETFスコア": 69.0, "テーマスコア": 76.0, "RR": 1.4},
        ]
    )
    result = filter_hybrid_signal_candidates(
        signals,
        HybridSignalConfig(
            candidate_policy="watch_score_gate",
            min_etf_score=70.0,
            min_theme_score=70.0,
            min_rr=1.0,
        ),
    )
    assert result["ETF"].tolist() == ["SMH"]


def test_filter_hybrid_signal_candidates_relaxes_only_configured_tickers() -> None:
    signals = pd.DataFrame(
        [
            {"ETF": "SMH", "判定": "見送り", "ETFスコア": 85.0, "テーマスコア": 66.0, "RR": 1.2},
            {"ETF": "BOTZ", "判定": "見送り", "ETFスコア": 85.0, "テーマスコア": 66.0, "RR": 1.2},
            {"ETF": "URA", "判定": "見送り", "ETFスコア": 73.0, "テーマスコア": 75.0, "RR": 1.1},
        ]
    )
    result = filter_hybrid_signal_candidates(
        signals,
        HybridSignalConfig(
            candidate_policy="watch_score_gate",
            min_etf_score=70.0,
            min_theme_score=70.0,
            min_rr=1.0,
            relaxed_signal_tickers=("SMH", "SOXX"),
            relaxed_min_etf_score=65.0,
            relaxed_min_theme_score=65.0,
            relaxed_min_rr=1.0,
            ticker_min_etf_scores={"URA": 75.0},
            ticker_min_rr_values={"URA": 2.5},
        ),
    )
    assert result["ETF"].tolist() == ["SMH"]


def test_copy_hybrid_signal_config_preserves_relaxed_signal_tickers() -> None:
    config = HybridSignalConfig(
        candidate_policy="watch_score_gate",
        relaxed_signal_tickers=("SMH", "SOXX"),
        relaxed_min_etf_score=65.0,
        relaxed_min_theme_score=65.0,
        relaxed_min_rr=1.0,
    )
    copied = copy_hybrid_signal_config(config, max_entry_day_loss_pct=-3.0)
    assert copied.relaxed_signal_tickers == ("SMH", "SOXX")
    assert copied.relaxed_min_etf_score == 65.0
    assert copied.relaxed_min_theme_score == 65.0
    assert copied.relaxed_min_rr == 1.0
    assert copied.max_entry_day_loss_pct == -3.0


def test_hybrid_ticker_rule_search_can_block_ura_overlay() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": [100.0 + index * 0.05 for index in range(320)],
            "QQQ": [100.0 + index * 0.06 for index in range(320)],
            "URA": [100.0 + index * 0.08 for index in range(320)],
        },
        index=dates,
    )
    frames = {}
    for ticker in prices.columns:
        price = prices[ticker]
        frames[ticker] = pd.DataFrame(
            {
                "price": price,
                "ma_21": price.rolling(21).mean(),
                "ma_50": price.rolling(50).mean(),
                "ma_200": price.rolling(200).mean(),
                "ma_50_slope": price.pct_change(10).fillna(0),
                "ma_200_slope": price.pct_change(20).fillna(0),
                "return_3m": price.pct_change(63).fillna(0),
                "return_6m": price.pct_change(126).fillna(0),
                "return_12m": price.pct_change(252).fillna(0),
                "rs_qqq_3m": price.pct_change(63).fillna(0),
                "rs_spy_3m": price.pct_change(63).fillna(0),
                "drawdown_52w_pct": -8.0,
                "rsi_14": 55.0,
                "three_day_return_pct": price.pct_change(3).fillna(0) * 100,
            },
            index=dates,
        )
    signal_date = dates[260]
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": signal_date.date().isoformat(),
                "ETF": "URA",
                "判定": "押し目待ち",
                "ETFスコア": 72.0,
                "テーマスコア": 72.0,
                "RR": 2.1,
                "現在価格": float(prices.at[signal_date, "URA"]),
                "第1買い": float(prices.at[signal_date, "URA"]),
                "保守目標": float(prices.at[signal_date, "URA"]) * 1.08,
                "停止価格": float(prices.at[signal_date, "URA"]) * 0.95,
            }
        ]
    )
    result = run_hybrid_ticker_rule_search(
        prices,
        frames,
        ["URA"],
        signal_history,
        BacktestConfig(rebalance_frequency="ME", satellite_weight=0.35, top_satellites=1),
        HybridSignalConfig(
            candidate_policy="watch_score_gate",
            entry_multiplier=1.0,
            min_etf_score=65.0,
            max_holding_days=20,
        ),
        rule_sets=[
            {"rule_name": "baseline"},
            {"rule_name": "block_URA", "blocked_signal_tickers": ("URA",)},
        ],
    )
    baseline = result[result["rule_name"].eq("baseline")].iloc[0]
    blocked = result[result["rule_name"].eq("block_URA")].iloc[0]
    assert int(baseline["ura_signal_trade_count"]) >= 1
    assert int(blocked["ura_signal_trade_count"]) == 0
