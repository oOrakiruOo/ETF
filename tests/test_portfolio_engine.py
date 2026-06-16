from __future__ import annotations

import pandas as pd

from src.portfolio_engine import (
    PORTFOLIO_COLUMNS,
    evaluate_portfolio_actions,
    normalize_portfolio_columns,
    update_portfolio_prices,
    validate_portfolio,
)


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


def test_update_portfolio_prices_accepts_minimal_columns() -> None:
    portfolio = pd.DataFrame([{"ticker": "qqq", "quantity": 2, "avg_price": 100.0}])
    updated = update_portfolio_prices(portfolio, {"QQQ": 125.0})
    assert list(updated.columns) == PORTFOLIO_COLUMNS
    assert float(updated.iloc[0]["current_price"]) == 125.0
    assert float(updated.iloc[0]["market_value"]) == 250.0


def test_normalize_portfolio_columns_adds_missing_optional_columns() -> None:
    portfolio = pd.DataFrame([{"ticker": "QQQ", "quantity": 1, "avg_price": 100.0}])
    normalized = normalize_portfolio_columns(portfolio)
    assert list(normalized.columns) == PORTFOLIO_COLUMNS
    assert normalized.iloc[0]["ticker"] == "QQQ"


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


def test_validate_portfolio_flags_invalid_numbers_and_duplicate_tickers() -> None:
    portfolio = pd.DataFrame(
        [
            {"ticker": "SMH", "quantity": 2, "avg_price": 100.0, "stop_price": "", "target_price": 130.0},
            {"ticker": "SMH", "quantity": "bad", "avg_price": 100.0, "stop_price": 90.0, "target_price": 130.0},
        ]
    )
    issues = validate_portfolio(portfolio)
    assert "数値として読めません" in issues["message"].tolist()
    assert "同じtickerが複数行あります" in issues["message"].tolist()
    assert "停止価格または目標価格が未入力です" in issues["message"].tolist()


def test_validate_portfolio_returns_ok_for_basic_valid_rows() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "quantity": 1,
                "avg_price": 200.0,
                "current_price": 210.0,
                "stop_price": 180.0,
                "target_price": 260.0,
            },
        ]
    )
    issues = validate_portfolio(portfolio)
    assert issues.iloc[0]["severity"] == "OK"


def test_validate_portfolio_flags_position_and_theme_concentration() -> None:
    portfolio = pd.DataFrame(
        [
            {
                "ticker": "SMH",
                "theme": "半導体",
                "quantity": 1,
                "avg_price": 100.0,
                "weight_pct": 12.0,
            },
            {
                "ticker": "SOXX",
                "theme": "半導体",
                "quantity": 1,
                "avg_price": 100.0,
                "weight_pct": 8.0,
            },
        ]
    )
    issues = validate_portfolio(portfolio)
    messages = issues["message"].tolist()
    assert "ETF単体比率が10%を超えています" in messages
    assert "半導体テーマ比率が15%を超えています" in messages
