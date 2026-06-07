from __future__ import annotations

from src.risk_engine import calculate_trade_plan, portfolio_action_by_drawdown


def test_calculate_trade_plan_has_expected_fields() -> None:
    plan = calculate_trade_plan(
        {
            "price": 100.0,
            "high_52w": 110.0,
            "ma_21": 96.0,
            "ma_50": 90.0,
            "ma_200": 80.0,
            "atr_14": 4.0,
        }
    )
    assert plan["first_buy"] <= 100
    assert plan["second_buy"] <= plan["first_buy"]
    assert plan["third_buy"] <= plan["second_buy"]
    assert plan["risk_reward"] > 0


def test_portfolio_action_by_drawdown() -> None:
    assert portfolio_action_by_drawdown(-7) == "通常運用"
    assert portfolio_action_by_drawdown(-8) == "新規買い停止"
    assert portfolio_action_by_drawdown(-12) == "Satellite半分削減"
    assert portfolio_action_by_drawdown(-15) == "Satellite大幅縮小、Core中心へ戻す"
