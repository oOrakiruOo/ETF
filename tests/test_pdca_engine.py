from __future__ import annotations

import pandas as pd

from src.pdca_engine import (
    calculate_forward_return,
    evaluate_avoid_outcomes,
    evaluate_virtual_trades,
    propose_signal_improvements,
    run_avoid_policy_search,
    run_entry_parameter_search,
    summarize_avoid_outcomes_by_signal,
    summarize_avoid_outcomes,
    summarize_signal_accuracy,
    summarize_virtual_trades,
)


def test_calculate_forward_return_uses_future_index_position() -> None:
    close = pd.Series(
        [100.0, 105.0, 110.0],
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05"]),
    )
    assert calculate_forward_return(close, pd.Timestamp("2026-01-01"), 2) == 10.0


def test_summarize_signal_accuracy_groups_by_signal() -> None:
    evaluated = pd.DataFrame(
        [
            {"判定": "見送り", "1d_return_pct": -1.0},
            {"判定": "見送り", "1d_return_pct": 2.0},
            {"判定": "買い候補", "1d_return_pct": 3.0},
        ]
    )
    summary = summarize_signal_accuracy(evaluated)
    assert set(summary["判定"]) == {"見送り", "買い候補"}


def test_propose_signal_improvements_flags_weak_buy_signals() -> None:
    signal_accuracy = pd.DataFrame(
        [
            {
                "判定": "買い候補",
                "件数": 4,
                "5d_return_pct_勝率": 25.0,
                "20d_return_pct_平均": -1.2,
            },
            {
                "判定": "見送り",
                "件数": 4,
                "20d_return_pct_平均": 1.8,
            },
        ]
    )
    proposals = propose_signal_improvements(signal_accuracy)
    joined = " ".join(proposals)
    assert "最低ETFスコア" in joined
    assert "第1買い価格" in joined
    assert "過熱控除" in joined


def test_evaluate_virtual_trades_records_stop_loss(monkeypatch) -> None:
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": "2026-01-01",
                "ETF": "SMH",
                "判定": "買い候補",
                "第1買い": 100.0,
                "保守目標": 120.0,
                "停止価格": 95.0,
            }
        ]
    )
    ohlc = pd.DataFrame(
        {
            "High": [102.0, 101.0],
            "Low": [99.0, 94.0],
            "Close": [100.0, 96.0],
        },
        index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
    )
    monkeypatch.setattr("src.pdca_engine.load_cached_ohlc", lambda ticker: ohlc)
    trades = evaluate_virtual_trades(signal_history)
    assert len(trades) == 1
    assert trades.iloc[0]["status"] == "約定"
    assert trades.iloc[0]["exit_reason"] == "停止価格"
    assert trades.iloc[0]["return_pct"] == -5.0


def test_summarize_virtual_trades_counts_filled_and_unfilled() -> None:
    trades = pd.DataFrame(
        [
            {"status": "約定", "exit_reason": "保守目標", "return_pct": 10.0},
            {"status": "約定", "exit_reason": "停止価格", "return_pct": -4.0},
            {"status": "未約定", "exit_reason": "第1買い未到達", "return_pct": None},
        ]
    )
    summary = summarize_virtual_trades(trades)
    assert summary.iloc[0]["対象件数"] == 3
    assert summary.iloc[0]["約定件数"] == 2
    assert summary.iloc[0]["未約定件数"] == 1
    assert summary.iloc[0]["勝率"] == 50.0


def test_evaluate_avoid_outcomes_marks_decline_as_correct(monkeypatch) -> None:
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": "2026-01-01",
                "ETF": "SMH",
                "判定": "見送り",
            }
        ]
    )
    close = pd.Series(
        [100.0, 98.0, 95.0],
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05"]),
    )
    monkeypatch.setattr("src.pdca_engine.load_cached_close", lambda ticker: close)
    outcomes = evaluate_avoid_outcomes(signal_history, horizon_days=2)
    assert outcomes.iloc[0]["20d_return_pct"] == -5.0
    assert bool(outcomes.iloc[0]["is_correct"]) is True


def test_summarize_avoid_outcomes_counts_missed_upside() -> None:
    outcomes = pd.DataFrame(
        [
            {"is_correct": True, "20d_return_pct": -2.0},
            {"is_correct": False, "20d_return_pct": 3.0},
            {"is_correct": None, "20d_return_pct": None},
        ]
    )
    summary = summarize_avoid_outcomes(outcomes)
    assert summary.iloc[0]["対象件数"] == 3
    assert summary.iloc[0]["評価済み件数"] == 2
    assert summary.iloc[0]["正解率"] == 50.0
    assert summary.iloc[0]["回避後上昇件数"] == 1


def test_run_entry_parameter_search_ranks_trade_settings(monkeypatch) -> None:
    signal_history = pd.DataFrame(
        [
            {
                "snapshot": "2026-01-01",
                "ETF": "SMH",
                "判定": "買い候補",
                "現在価格": 105.0,
                "第1買い": 100.0,
                "保守目標": 110.0,
                "停止価格": 95.0,
            }
        ]
    )
    ohlc = pd.DataFrame(
        {
            "High": [106.0, 111.0],
            "Low": [101.0, 104.0],
            "Close": [105.0, 110.0],
        },
        index=pd.to_datetime(["2026-01-02", "2026-01-05"]),
    )
    monkeypatch.setattr("src.pdca_engine.load_cached_ohlc", lambda ticker: ohlc)
    result = run_entry_parameter_search(
        signal_history,
        entry_multipliers=[1.0, 1.04],
        stop_multipliers=[1.0],
    )
    assert len(result) == 2
    assert result.iloc[0]["entry_multiplier"] == 1.04
    assert result.iloc[0]["約定件数"] == 1


def test_summarize_avoid_outcomes_by_signal_groups_results() -> None:
    outcomes = pd.DataFrame(
        [
            {"判定": "見送り", "is_correct": True, "20d_return_pct": -1.0},
            {"判定": "見送り", "is_correct": False, "20d_return_pct": 2.0},
            {"判定": "売却候補", "is_correct": False, "20d_return_pct": 3.0},
        ]
    )
    summary = summarize_avoid_outcomes_by_signal(outcomes)
    assert set(summary["判定"]) == {"見送り", "売却候補"}
    sell_row = summary[summary["判定"].eq("売却候補")].iloc[0]
    assert sell_row["正解率"] == 0.0


def test_run_avoid_policy_search_returns_ranked_policies() -> None:
    outcomes = pd.DataFrame(
        [
            {"判定": "見送り", "is_correct": True, "20d_return_pct": -1.0},
            {"判定": "売却候補", "is_correct": False, "20d_return_pct": 4.0},
            {"判定": "売却候補", "is_correct": False, "20d_return_pct": 2.0},
        ]
    )
    result = run_avoid_policy_search(outcomes)
    assert set(result["policy"]) == {"current_all_avoid", "sell_only", "avoid_only", "no_sell_candidate_avoid"}
    assert result.iloc[0]["policy"] in {"avoid_only", "no_sell_candidate_avoid"}
