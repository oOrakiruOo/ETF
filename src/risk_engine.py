from __future__ import annotations


def adjusted_trade_price(value: float, multiplier: float) -> float:
    return value * multiplier if multiplier > 0 else value


def calculate_trade_plan(
    metrics: dict[str, float],
    entry_multiplier: float = 1.0,
    stop_multiplier: float = 1.0,
    target_multiplier: float = 1.0,
) -> dict[str, float]:
    price = metrics["price"]
    high_52w = metrics.get("high_52w", price)
    ma_21 = metrics.get("ma_21", price)
    ma_50 = metrics.get("ma_50", price)
    atr = metrics.get("atr_14", 0.0)
    first_buy = min(high_52w * 0.95, ma_21, price - atr if atr > 0 else price * 0.95)
    second_buy = min(high_52w * 0.90, ma_50, price - 2 * atr if atr > 0 else price * 0.90)
    third_buy = min(high_52w * 0.85, ma_50 * 0.98, price - 3 * atr if atr > 0 else price * 0.85)
    stop_price = min(metrics.get("ma_200", price * 0.9), third_buy * 0.95)
    first_buy = min(adjusted_trade_price(first_buy, entry_multiplier), price)
    stop_price = adjusted_trade_price(stop_price, stop_multiplier)
    if stop_price >= first_buy:
        stop_price = first_buy * 0.97
    conservative_target = adjusted_trade_price(high_52w * 1.10, target_multiplier)
    aggressive_target = adjusted_trade_price(high_52w * 1.20, target_multiplier)
    risk = max(first_buy - stop_price, 0.01)
    reward = max(conservative_target - first_buy, 0.0)
    rr = reward / risk
    return {
        "current_price": round(price, 2),
        "first_buy": round(first_buy, 2),
        "first_buy_gap_pct": round((first_buy / price - 1) * 100, 2),
        "second_buy": round(second_buy, 2),
        "third_buy": round(third_buy, 2),
        "conservative_target": round(conservative_target, 2),
        "aggressive_target": round(aggressive_target, 2),
        "upside_pct": round((conservative_target / price - 1) * 100, 2),
        "stop_price": round(stop_price, 2),
        "risk_reward": round(rr, 2),
    }


def portfolio_action_by_drawdown(drawdown_pct: float) -> str:
    if drawdown_pct <= -15:
        return "Satellite大幅縮小、Core中心へ戻す"
    if drawdown_pct <= -12:
        return "Satellite半分削減"
    if drawdown_pct <= -8:
        return "新規買い停止"
    return "通常運用"
