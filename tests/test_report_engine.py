from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.report_engine import write_portfolio_check_report, write_replay_pdca_report


def test_replay_report_action_items_use_min_score_for_hybrid_thresholds(tmp_path) -> None:
    hybrid_grid = pd.DataFrame(
        [
            {
                "candidate_policy": "watch_score_gate",
                "acceleration_overlay_mode": "normal",
                "signal_overlay_weight_pct": 15.0,
                "entry_multiplier": 1.04,
                "stop_multiplier": 0.95,
                "max_holding_days": 40,
                "max_signal_positions": 2,
                "min_score": 70.0,
                "min_rr": 1.0,
                "annual_return_pct": 17.32,
                "cumulative_return_pct": 393.72,
                "max_drawdown_pct": -19.28,
                "sharpe_ratio": 1.08,
                "trade_count": 132,
                "signal_entry_count": 4,
                "signal_exit_count": 4,
                "avg_signal_trade_return_pct": 11.24,
                "risk_adjusted_rank_score": 26.90,
            }
        ]
    )
    output_path = write_replay_pdca_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        hybrid_grid=hybrid_grid,
        output_dir=tmp_path,
        processed_output_dir=tmp_path / "processed",
        report_date=datetime(2026, 6, 7),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "ETF70+ テーマ70+ RR1.0+" in text
    assert "ETF0+ テーマ0+" not in text


def test_replay_report_action_items_show_relaxed_hybrid_tickers(tmp_path) -> None:
    hybrid_ticker_rule_results = pd.DataFrame(
        [
            {
                "rule_name": "block_URA",
                "annual_return_pct": 17.76,
                "ura_signal_trade_count": 0,
                "relaxed_signal_tickers": "SMH,SOXX",
                "relaxed_min_etf_score": 65.0,
                "relaxed_min_theme_score": 65.0,
                "relaxed_min_rr": 1.0,
            }
        ]
    )
    output_path = write_replay_pdca_report(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        hybrid_ticker_rule_results=hybrid_ticker_rule_results,
        output_dir=tmp_path,
        processed_output_dir=tmp_path / "processed",
        report_date=datetime(2026, 6, 7),
    )
    text = output_path.read_text(encoding="utf-8")
    assert "限定緩和SMH,SOXX ETF65+ テーマ65+ RR1.0+" in text


def test_write_portfolio_check_report_marks_errors(tmp_path) -> None:
    issues = pd.DataFrame(
        [
            {
                "severity": "Error",
                "ticker": "SMH",
                "column": "quantity",
                "message": "数値として読めません",
            }
        ]
    )
    output_path = write_portfolio_check_report(issues, output_dir=tmp_path, report_date=datetime(2026, 6, 8))
    text = output_path.read_text(encoding="utf-8")
    assert "判定: 要修正" in text
    assert "数値として読めません" in text
