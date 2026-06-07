from __future__ import annotations

import numpy as np


def normalize_return(value: float, low: float = -0.15, high: float = 0.25) -> float:
    clipped = min(max(value, low), high)
    return (clipped - low) / (high - low)


def calculate_theme_scores(
    theme_map: dict[str, list[str]],
    metrics_by_ticker: dict[str, dict[str, float]],
    macro_score: float = 10.0,
    news_score: float = 6.0,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for theme, tickers in theme_map.items():
        theme_metrics = [metrics_by_ticker[ticker] for ticker in tickers if ticker in metrics_by_ticker]
        if not theme_metrics:
            scores[theme] = 0.0
            continue
        momentum = np.nanmean([normalize_return(item.get("return_3m", 0.0)) for item in theme_metrics]) * 30
        relative = np.nanmean(
            [
                normalize_return(item.get("rs_qqq_3m", 0.0), -0.1, 0.15)
                + normalize_return(item.get("rs_spy_3m", 0.0), -0.1, 0.15)
                for item in theme_metrics
            ]
        ) / 2 * 20
        volume = np.nanmean([min(max((item.get("volume_change_pct", 0.0) + 50) / 100, 0), 1) for item in theme_metrics]) * 15
        overheating_penalty = np.nanmean([8 if item.get("rsi_14", 50.0) >= 75 else 0 for item in theme_metrics])
        pullback_expectation = max(0.0, 10.0 - overheating_penalty)
        scores[theme] = round(float(momentum + relative + volume + macro_score + news_score + pullback_expectation), 2)
    return scores


def classify_theme_stage(metrics: dict[str, float], theme_score: float) -> str:
    price = metrics.get("price", 0.0)
    ma_50 = metrics.get("ma_50", 0.0)
    ma_200 = metrics.get("ma_200", 0.0)
    rsi = metrics.get("rsi_14", 50.0)
    drawdown = metrics.get("drawdown_52w_pct", -20.0)
    rs_qqq = metrics.get("rs_qqq_3m", 0.0)
    rs_spy = metrics.get("rs_spy_3m", 0.0)
    if price < ma_50 or theme_score < 60:
        return "ステージ5: 失速期"
    if rsi >= 75 or drawdown > -3:
        return "ステージ4: 過熱期"
    if price > ma_50 > ma_200 and rs_qqq > 0 and rs_spy > 0:
        return "ステージ3: 加速期"
    if price > ma_200 and metrics.get("ma_50_slope", 0.0) > 0:
        return "ステージ2: 初動期"
    return "ステージ1: 構想期"


def assess_theme_rotation_risks(
    theme_map: dict[str, list[str]],
    metrics_by_ticker: dict[str, dict[str, float]],
    theme_scores: dict[str, float],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for theme, tickers in theme_map.items():
        theme_metrics = [metrics_by_ticker[ticker] for ticker in tickers if ticker in metrics_by_ticker]
        if not theme_metrics:
            rows.append(
                {
                    "テーマ": theme,
                    "テーマスコア": round(float(theme_scores.get(theme, 0.0)), 2),
                    "リスクスコア": 100.0,
                    "リスク区分": "高",
                    "主なリスク": "評価データ不足",
                    "予防策": "新規採用停止。価格データと関連ETFを追加してから再評価",
                }
            )
            continue

        score = float(theme_scores.get(theme, 0.0))
        avg_return_3m = float(np.nanmean([item.get("return_3m", 0.0) for item in theme_metrics]) * 100)
        avg_return_6m = float(np.nanmean([item.get("return_6m", 0.0) for item in theme_metrics]) * 100)
        avg_rs_qqq = float(np.nanmean([item.get("rs_qqq_3m", 0.0) for item in theme_metrics]) * 100)
        avg_rs_spy = float(np.nanmean([item.get("rs_spy_3m", 0.0) for item in theme_metrics]) * 100)
        avg_rsi = float(np.nanmean([item.get("rsi_14", 50.0) for item in theme_metrics]))
        avg_drawdown = float(np.nanmean([item.get("drawdown_52w_pct", -20.0) for item in theme_metrics]))
        positive_rs_count = sum(
            1
            for item in theme_metrics
            if item.get("rs_qqq_3m", 0.0) > 0 and item.get("rs_spy_3m", 0.0) > 0
        )
        breadth_pct = positive_rs_count / len(theme_metrics) * 100

        risk_score = 0.0
        reasons: list[str] = []
        prevention: list[str] = []
        if len(theme_metrics) < 2:
            risk_score += 20
            reasons.append("関連ETFが少なくテーマ判定が狭い")
            prevention.append("1ETF集中を避け、テーマ上限を低めにする")
        if score >= 75 and avg_rsi >= 70:
            risk_score += 20
            reasons.append("高スコアだがRSIが高く過熱寄り")
            prevention.append("追い買い禁止。押し目条件とRRを厳格化")
        if score >= 70 and avg_drawdown > -5:
            risk_score += 15
            reasons.append("52週高値圏で高値掴みリスク")
            prevention.append("第1買いを5%以上の押し目まで待つ")
        if avg_rs_qqq < 0 and avg_rs_spy < 0:
            risk_score += 25
            reasons.append("QQQ/SPYに相対劣後")
            prevention.append("補助枠を停止しCore優先へ戻す")
        elif avg_rs_qqq < 0 or avg_rs_spy < 0:
            risk_score += 15
            reasons.append("片側ベンチマークに相対劣後")
            prevention.append("新規比率を半分に落として監視")
        if avg_return_3m < 0 and avg_return_6m < 0:
            risk_score += 20
            reasons.append("3か月/6か月モメンタムが失速")
            prevention.append("ステージ5扱いで新規買い停止")
        if breadth_pct < 50:
            risk_score += 15
            reasons.append("テーマ内の相対強度が広がっていない")
            prevention.append("テーマ全体ではなく上位ETFだけに限定")

        risk_score = round(min(risk_score, 100.0), 2)
        if risk_score >= 60:
            bucket = "高"
        elif risk_score >= 30:
            bucket = "中"
        else:
            bucket = "低"
        rows.append(
            {
                "テーマ": theme,
                "テーマスコア": round(score, 2),
                "リスクスコア": risk_score,
                "リスク区分": bucket,
                "3か月平均%": round(avg_return_3m, 2),
                "6か月平均%": round(avg_return_6m, 2),
                "QQQ相対%": round(avg_rs_qqq, 2),
                "SPY相対%": round(avg_rs_spy, 2),
                "平均RSI": round(avg_rsi, 2),
                "52週高値乖離%": round(avg_drawdown, 2),
                "相対強度の広がり%": round(breadth_pct, 2),
                "主なリスク": " / ".join(reasons) if reasons else "大きな警戒なし",
                "予防策": " / ".join(prevention) if prevention else "通常ルールで監視",
            }
        )
    return sorted(rows, key=lambda row: (float(row["リスクスコア"]), -float(row["テーマスコア"])), reverse=True)
