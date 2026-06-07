from __future__ import annotations

from src.etf_score_engine import calculate_etf_score, score_pullback, score_theme, score_trend


def sample_metrics() -> dict[str, float]:
    return {
        "price": 100.0,
        "ma_21": 98.0,
        "ma_50": 95.0,
        "ma_200": 80.0,
        "ma_50_slope": 0.03,
        "ma_200_slope": 0.02,
        "return_3m": 0.12,
        "return_6m": 0.20,
        "return_12m": 0.30,
        "rs_qqq_3m": 0.04,
        "rs_spy_3m": 0.05,
        "rsi_14": 58.0,
        "drawdown_52w_pct": -10.0,
        "atr_14": 3.0,
        "three_day_return_pct": 2.0,
        "volume_20d": 3_000_000.0,
    }


def test_score_trend_full_points_for_uptrend() -> None:
    assert score_trend(sample_metrics()) == 25


def test_score_pullback_rewards_controlled_pullback() -> None:
    assert score_pullback(sample_metrics()) >= 16


def test_score_theme_thresholds() -> None:
    assert score_theme(90) == 20
    assert score_theme(70) == 12
    assert score_theme(50) == 4


def test_calculate_etf_score_returns_total() -> None:
    score = calculate_etf_score(sample_metrics(), 80)
    assert score["total"] > 70
