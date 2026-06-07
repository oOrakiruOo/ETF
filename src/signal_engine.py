from __future__ import annotations


def decide_signal(
    etf_score: float,
    theme_score: float,
    stage: str,
    metrics: dict[str, float],
    trade_plan: dict[str, float],
) -> str:
    price = metrics.get("price", 0.0)
    ma_200 = metrics.get("ma_200", 0.0)
    ma_50_slope = metrics.get("ma_50_slope", 0.0)
    rsi = metrics.get("rsi_14", 50.0)
    drawdown = metrics.get("drawdown_52w_pct", -20.0)
    rr = trade_plan.get("risk_reward", 0.0)
    if (
        etf_score >= 70
        and theme_score >= 70
        and ("ステージ2" in stage or "ステージ3" in stage)
        and price > ma_200
        and ma_50_slope > 0
        and rsi < 75
        and -15 <= drawdown <= -5
        and rr >= 2.0
    ):
        return "買い候補"
    if etf_score >= 75 and theme_score >= 75 and rsi < 70 and rr >= 2.5:
        return "強気買い候補"
    if rsi >= 80 or metrics.get("three_day_return_pct", 0.0) >= 8:
        return "利確候補"
    if price < ma_200 or etf_score < 60 or theme_score < 60:
        return "売却候補"
    if etf_score < 65 or theme_score < 65 or rsi >= 75 or drawdown > -3 or rr < 1.5:
        return "見送り"
    if price > ma_200 and ma_50_slope > 0:
        return "押し目待ち"
    return "保有継続"


def apply_theme_risk_overlay(signal: str, risk_bucket: str, risk_score: float, mode: str = "balanced") -> str:
    if mode == "off":
        return signal
    buy_signals = {"強気買い候補", "買い候補", "積立候補"}
    if risk_bucket == "高" and signal in buy_signals:
        return "見送り"
    if risk_bucket == "高" and signal == "押し目待ち":
        return "見送り"
    if mode == "high_only":
        return signal
    if risk_bucket == "中" and mode == "strict" and signal == "押し目待ち" and risk_score >= 45:
        return "見送り"
    if risk_bucket == "中" and mode == "strict" and signal in buy_signals:
        return "押し目待ち"
    if risk_bucket == "中" and signal == "強気買い候補":
        return "買い候補"
    if risk_bucket == "中" and signal == "買い候補" and risk_score >= 45:
        return "押し目待ち"
    return signal
