from __future__ import annotations

import math


def _positive_return_points(value: float, max_points: int, cap: float) -> float:
    if math.isnan(value):
        return 0.0
    return min(max(value / cap, 0.0), 1.0) * max_points


def score_trend(metrics: dict[str, float]) -> float:
    score = 0.0
    price = metrics.get("price", 0.0)
    if price > metrics.get("ma_200", float("inf")):
        score += 8
    if metrics.get("ma_50", 0.0) > metrics.get("ma_200", float("inf")):
        score += 5
    if metrics.get("ma_21", 0.0) > metrics.get("ma_50", float("inf")):
        score += 5
    if metrics.get("ma_50_slope", 0.0) > 0:
        score += 4
    if metrics.get("ma_200_slope", 0.0) > 0:
        score += 3
    return score


def score_momentum(metrics: dict[str, float]) -> float:
    score = 0.0
    score += _positive_return_points(metrics.get("return_3m", 0.0), 8, 0.15)
    score += _positive_return_points(metrics.get("return_6m", 0.0), 8, 0.25)
    score += _positive_return_points(metrics.get("return_12m", 0.0), 4, 0.35)
    score += _positive_return_points(metrics.get("rs_qqq_3m", 0.0), 3, 0.08)
    score += _positive_return_points(metrics.get("rs_spy_3m", 0.0), 2, 0.08)
    return score


def score_pullback(metrics: dict[str, float]) -> float:
    score = 0.0
    rsi = metrics.get("rsi_14", 50.0)
    drawdown = metrics.get("drawdown_52w_pct", -20.0)
    price = metrics.get("price", 0.0)
    ma_21 = metrics.get("ma_21", price)
    atr = metrics.get("atr_14", 0.0)
    if 45 <= rsi <= 65:
        score += 8
    if -15 <= drawdown <= -5:
        score += 8
    if atr > 0 and abs(price - ma_21) <= 2 * atr:
        score += 4
    if rsi >= 75:
        score -= 8
    if drawdown > -3:
        score -= 5
    if metrics.get("three_day_return_pct", 0.0) >= 8:
        score -= 5
    return max(score, 0.0)


def score_liquidity(metrics: dict[str, float]) -> float:
    dollar_volume = metrics.get("price", 0.0) * metrics.get("volume_20d", 0.0)
    if dollar_volume >= 1_000_000_000:
        return 10.0
    if dollar_volume >= 250_000_000:
        return 8.0
    if dollar_volume >= 50_000_000:
        return 6.0
    if dollar_volume >= 10_000_000:
        return 4.0
    return 2.0


def score_theme(theme_score: float) -> float:
    if theme_score >= 90:
        return 20.0
    if theme_score >= 80:
        return 16.0
    if theme_score >= 70:
        return 12.0
    if theme_score >= 60:
        return 8.0
    return 4.0


def calculate_etf_score(metrics: dict[str, float], theme_score_value: float) -> dict[str, float]:
    parts = {
        "trend": score_trend(metrics),
        "momentum": score_momentum(metrics),
        "pullback": score_pullback(metrics),
        "liquidity": score_liquidity(metrics),
        "theme": score_theme(theme_score_value),
    }
    parts["total"] = round(sum(parts.values()), 2)
    return parts
