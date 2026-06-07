from __future__ import annotations

import pandas as pd

from src.portfolio_engine import evaluate_portfolio_actions, update_portfolio_prices


def test_update_portfolio_prices_calculates_weights_and_pnl() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "ticker": "SMH",
                "theme": "半導体",
                "quantity": 2,
                "avg_price": 100.0,
                "current_price": 100.0,
            },
            {
                "ticker": "QQQ",
                "theme": "Core",
                "quantity": 1,
                "avg_price": 200.0,
                "current_price": 200.0,
            },
        ]
    )
    updated = update_portfolio_prices(portfolio, {"SMH": 120.0, "QQQ": 180.0})
    assert round(float(updated["market_value"].sum()), 2) == 420.0
    assert round(float(updated.loc[updated["ticker"] == "SMH", "unrealized_pnl_pct"].iloc[0]), 2) == 20.0
    assert round(float(updated["weight_pct"].sum()), 2) == 100.0


def test_evaluate_portfolio_actions_flags_stop_and_profit() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "ticker": "SMH",
                "avg_price": 100.0,
                "current_price": 80.0,
                "unrealized_pnl_pct": -20.0,
                "stop_price": 82.0,
                "target_price": 130.0,
            },
            {
                "ticker": "QQQ",
                "avg_price": 100.0,
                "current_price": 125.0,
                "unrealized_pnl_pct": 25.0,
                "stop_price": 90.0,
                "target_price": 140.0,
            },
        ]
    )
    evaluated = evaluate_portfolio_actions(portfolio)
    assert evaluated.loc[evaluated["ticker"] == "SMH", "portfolio_action"].iloc[0] == "損失確認"
    assert evaluated.loc[evaluated["ticker"] == "QQQ", "portfolio_action"].iloc[0] == "部分利確確認"
