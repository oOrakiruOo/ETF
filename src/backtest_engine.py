from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    core_spy_weight: float = 0.30
    core_qqq_weight: float = 0.30
    satellite_weight: float = 0.25
    cash_weight: float = 0.15
    top_satellites: int = 3
    rebalance_frequency: str = "ME"
    stop_new_buy_drawdown_pct: float = -8.0
    min_satellite_score: float = 45.0
    score_profile: str = "balanced"


@dataclass(frozen=True)
class SignalExecutionConfig:
    core_spy_weight: float = 0.30
    core_qqq_weight: float = 0.30
    satellite_weight: float = 0.35
    max_positions: int = 4
    entry_multiplier: float = 1.04
    stop_multiplier: float = 0.95
    max_holding_days: int = 20


@dataclass(frozen=True)
class HybridSignalConfig:
    signal_overlay_weight: float = 0.10
    max_signal_positions: int = 2
    entry_multiplier: float = 1.02
    stop_multiplier: float = 0.95
    max_holding_days: int = 60
    candidate_policy: str = "strict_buy"
    min_etf_score: float = 70.0
    min_theme_score: float = 70.0
    min_rr: float = 2.0
    max_entry_day_loss_pct: float = -100.0
    acceleration_overlay_mode: str = "normal"
    blocked_signal_tickers: tuple[str, ...] = ()
    ticker_min_etf_scores: dict[str, float] = field(default_factory=dict)
    ticker_min_theme_scores: dict[str, float] = field(default_factory=dict)
    ticker_min_rr_values: dict[str, float] = field(default_factory=dict)


BUY_SIGNAL_LABELS = {"強気買い候補", "買い候補", "押し目待ち", "積立候補"}
WATCH_SIGNAL_LABELS = BUY_SIGNAL_LABELS | {"保有継続", "見送り"}
HARD_RISK_SIGNAL_LABELS = {"利確候補", "リスク削減", "売却候補"}


def copy_hybrid_signal_config(config: HybridSignalConfig, **overrides: object) -> HybridSignalConfig:
    values = {
        "signal_overlay_weight": config.signal_overlay_weight,
        "max_signal_positions": config.max_signal_positions,
        "entry_multiplier": config.entry_multiplier,
        "stop_multiplier": config.stop_multiplier,
        "max_holding_days": config.max_holding_days,
        "candidate_policy": config.candidate_policy,
        "min_etf_score": config.min_etf_score,
        "min_theme_score": config.min_theme_score,
        "min_rr": config.min_rr,
        "max_entry_day_loss_pct": config.max_entry_day_loss_pct,
        "acceleration_overlay_mode": config.acceleration_overlay_mode,
        "blocked_signal_tickers": config.blocked_signal_tickers,
        "ticker_min_etf_scores": dict(config.ticker_min_etf_scores),
        "ticker_min_theme_scores": dict(config.ticker_min_theme_scores),
        "ticker_min_rr_values": dict(config.ticker_min_rr_values),
    }
    values.update(overrides)
    return HybridSignalConfig(**values)


def backtest_config_from_profile(profile: dict[str, object]) -> BacktestConfig:
    return BacktestConfig(
        core_spy_weight=float(profile.get("core_spy_weight", 0.30)),
        core_qqq_weight=float(profile.get("core_qqq_weight", 0.30)),
        satellite_weight=float(profile.get("satellite_weight", 0.25)),
        cash_weight=float(profile.get("cash_weight", 0.15)),
        top_satellites=int(profile.get("top_satellites", 3)),
        rebalance_frequency=str(profile.get("rebalance_frequency", "ME")),
        stop_new_buy_drawdown_pct=float(profile.get("stop_new_buy_drawdown_pct", -8.0)),
        min_satellite_score=float(profile.get("min_satellite_score", 45.0)),
        score_profile=str(profile.get("score_profile", "balanced")),
    )


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    return float(drawdown.min() * 100)


def calculate_cumulative_return(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    return round(float((equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100), 6)


def calculate_annualized_return(equity_curve: pd.Series) -> float:
    if len(equity_curve) < 2:
        return 0.0
    years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return float(((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1) * 100)


def calculate_sharpe_ratio(returns: pd.Series) -> float:
    clean = returns.dropna()
    if clean.empty or clean.std() == 0:
        return 0.0
    return float(clean.mean() / clean.std() * np.sqrt(252))


def calculate_sortino_ratio(returns: pd.Series) -> float:
    clean = returns.dropna()
    downside = clean[clean < 0]
    if clean.empty or downside.std() == 0:
        return 0.0
    return float(clean.mean() / downside.std() * np.sqrt(252))


def calculate_calmar_ratio(equity_curve: pd.Series) -> float:
    max_drawdown = abs(calculate_max_drawdown(equity_curve))
    if max_drawdown == 0:
        return 0.0
    return calculate_annualized_return(equity_curve) / max_drawdown


def build_price_matrix(raw_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    series = {}
    for ticker, frame in raw_data.items():
        column = "Adj Close" if "Adj Close" in frame.columns else "Close"
        series[ticker] = frame[column]
    prices = pd.DataFrame(series).sort_index().ffill().dropna(how="all")
    return prices.dropna(axis=1, how="all")


def score_backtest_snapshot(indicators: pd.DataFrame, profile: str = "balanced") -> pd.Series:
    score = pd.Series(0.0, index=indicators.index)
    score += (indicators["price"] > indicators["ma_200"]).astype(float) * 8
    score += (indicators["ma_50"] > indicators["ma_200"]).astype(float) * 5
    score += (indicators["ma_21"] > indicators["ma_50"]).astype(float) * 5
    score += (indicators["ma_50_slope"] > 0).astype(float) * 4
    score += (indicators["ma_200_slope"] > 0).astype(float) * 3
    if profile == "momentum":
        score += indicators["return_1m"].clip(lower=0, upper=0.08).fillna(0) / 0.08 * 6
        score += indicators["return_3m"].clip(lower=0, upper=0.18).fillna(0) / 0.18 * 10
        score += indicators["return_6m"].clip(lower=0, upper=0.30).fillna(0) / 0.30 * 8
        score += indicators["return_12m"].clip(lower=0, upper=0.45).fillna(0) / 0.45 * 4
        score += indicators["rs_qqq_3m"].clip(lower=0, upper=0.10).fillna(0) / 0.10 * 5
        score += indicators["rs_spy_3m"].clip(lower=0, upper=0.10).fillna(0) / 0.10 * 4
    elif profile == "balanced_plus":
        score += indicators["return_1m"].clip(lower=0, upper=0.08).fillna(0) / 0.08 * 3
        score += indicators["return_3m"].clip(lower=0, upper=0.16).fillna(0) / 0.16 * 9
        score += indicators["return_6m"].clip(lower=0, upper=0.26).fillna(0) / 0.26 * 8
        score += indicators["return_12m"].clip(lower=0, upper=0.38).fillna(0) / 0.38 * 4
        score += indicators["rs_qqq_3m"].clip(lower=0, upper=0.09).fillna(0) / 0.09 * 4
        score += indicators["rs_spy_3m"].clip(lower=0, upper=0.09).fillna(0) / 0.09 * 3
    else:
        score += indicators["return_3m"].clip(lower=0, upper=0.15).fillna(0) / 0.15 * 8
        score += indicators["return_6m"].clip(lower=0, upper=0.25).fillna(0) / 0.25 * 8
        score += indicators["return_12m"].clip(lower=0, upper=0.35).fillna(0) / 0.35 * 4
        score += indicators["rs_qqq_3m"].clip(lower=0, upper=0.08).fillna(0) / 0.08 * 3
        score += indicators["rs_spy_3m"].clip(lower=0, upper=0.08).fillna(0) / 0.08 * 2
    controlled_pullback = indicators["drawdown_52w_pct"].between(-15, -5) & indicators["rsi_14"].between(45, 70)
    if profile == "momentum":
        score += controlled_pullback.astype(float) * 4
        score -= (indicators["rsi_14"] >= 82).astype(float) * 5
        score -= (indicators["three_day_return_pct"] >= 10).astype(float) * 4
    elif profile == "balanced_plus":
        score += controlled_pullback.astype(float) * 8
        score -= (indicators["rsi_14"] >= 78).astype(float) * 7
        score -= (indicators["drawdown_52w_pct"] > -2).astype(float) * 4
        score -= (indicators["three_day_return_pct"] >= 9).astype(float) * 5
    else:
        score += controlled_pullback.astype(float) * 12
        score -= (indicators["rsi_14"] >= 75).astype(float) * 8
        score -= (indicators["drawdown_52w_pct"] > -3).astype(float) * 5
        score -= (indicators["three_day_return_pct"] >= 8).astype(float) * 5
    return score.clip(lower=0)


def choose_satellites(
    scores: pd.DataFrame,
    date: pd.Timestamp,
    candidates: list[str],
    top_n: int,
    min_score: float = 45.0,
) -> list[str]:
    available = [ticker for ticker in candidates if ticker in scores.columns]
    if not available:
        return []
    snapshot = scores.loc[date, available].dropna().sort_values(ascending=False)
    return snapshot[snapshot >= min_score].head(top_n).index.tolist()


def build_score_matrix(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    profile: str = "balanced",
) -> pd.DataFrame:
    common_index = prices.dropna().index
    return pd.DataFrame(
        {ticker: score_backtest_snapshot(frame, profile=profile).reindex(common_index) for ticker, frame in indicator_frames.items()}
    )


def is_acceleration_regime(indicator_frames: dict[str, pd.DataFrame], date: pd.Timestamp) -> bool:
    if "QQQ" not in indicator_frames:
        return False
    qqq = indicator_frames["QQQ"].reindex([date], method="ffill").iloc[0]
    qqq_uptrend = (
        qqq.get("price", 0.0) > qqq.get("ma_200", float("inf"))
        and qqq.get("ma_50", 0.0) > qqq.get("ma_200", float("inf"))
        and qqq.get("ma_50_slope", 0.0) > 0
        and qqq.get("return_3m", 0.0) > 0.08
        and qqq.get("rsi_14", 50.0) < 82
    )
    leaders = []
    for ticker in ("SMH", "SOXX", "VGT", "BOTZ"):
        if ticker in indicator_frames:
            row = indicator_frames[ticker].reindex([date], method="ffill").iloc[0]
            leaders.append(float(row.get("return_3m", 0.0)))
    leader_momentum = max(leaders) if leaders else 0.0
    return bool(qqq_uptrend and leader_momentum > 0.10)


def run_rotation_backtest(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    config: BacktestConfig | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    cfg = config or BacktestConfig()
    returns = prices.pct_change().fillna(0)
    common_index = prices.dropna().index
    returns = returns.reindex(common_index).fillna(0)
    scores = build_score_matrix(
        prices,
        indicator_frames,
        profile="balanced" if cfg.score_profile == "adaptive" else cfg.score_profile,
    ).reindex(common_index)
    momentum_scores = (
        build_score_matrix(prices, indicator_frames, profile="momentum").reindex(common_index)
        if cfg.score_profile == "adaptive"
        else scores
    )
    rebalance_dates = returns.groupby(pd.Grouper(freq=cfg.rebalance_frequency)).tail(1).index
    rebalance_dates = [date for date in rebalance_dates if date >= returns.index[min(252, len(returns) - 1)]]
    weights = pd.DataFrame(0.0, index=returns.index, columns=returns.columns)
    current_weights = pd.Series(0.0, index=returns.columns)
    equity_values: list[float] = []
    equity_index: list[pd.Timestamp] = []
    trade_count = 0
    acceleration_rebalance_count = 0
    last_satellites: set[str] = set()
    equity = 1.0
    running_high = 1.0
    rebalance_set = set(rebalance_dates)
    for date, daily_returns in returns.iterrows():
        drawdown_pct = (equity / running_high - 1) * 100
        if date in rebalance_set:
            active_scores = scores
            min_score = cfg.min_satellite_score
            if cfg.score_profile == "adaptive" and is_acceleration_regime(indicator_frames, date):
                active_scores = momentum_scores
                min_score = min(cfg.min_satellite_score, 35.0)
                acceleration_rebalance_count += 1
            selected = choose_satellites(
                active_scores,
                date,
                satellite_tickers,
                cfg.top_satellites,
                min_score=min_score,
            )
            satellite_weight = cfg.satellite_weight if drawdown_pct > cfg.stop_new_buy_drawdown_pct else 0.0
            cash_weight = 1.0 - cfg.core_spy_weight - cfg.core_qqq_weight - satellite_weight
            next_weights = pd.Series(0.0, index=returns.columns)
            if "SPY" in next_weights.index:
                next_weights["SPY"] = cfg.core_spy_weight
            if "QQQ" in next_weights.index:
                next_weights["QQQ"] = cfg.core_qqq_weight
            if selected:
                per_satellite = satellite_weight / len(selected)
                for ticker in selected:
                    next_weights[ticker] = per_satellite
            if cash_weight < 0:
                next_weights *= 1 / next_weights.sum()
            new_satellites = set(selected)
            trade_count += len(new_satellites.symmetric_difference(last_satellites))
            last_satellites = new_satellites
            current_weights = next_weights
        weights.loc[date] = current_weights
        equity *= 1 + float((current_weights * daily_returns).sum())
        running_high = max(running_high, equity)
        equity_values.append(equity)
        equity_index.append(date)
    equity_curve = pd.Series(equity_values, index=equity_index, name="MASATO Rotation")
    available_satellites = [ticker for ticker in satellite_tickers if ticker in weights.columns]
    avg_selected = (weights[available_satellites].gt(0).sum(axis=1)).mean() if available_satellites else 0.0
    diagnostics = pd.DataFrame(
        {
            "trade_count": [trade_count],
            "avg_selected_satellites": [avg_selected],
            "acceleration_rebalance_count": [acceleration_rebalance_count],
        }
    )
    return equity_curve, diagnostics


def buy_and_hold_curve(prices: pd.DataFrame, weights: dict[str, float], name: str) -> pd.Series:
    available = {ticker: weight for ticker, weight in weights.items() if ticker in prices.columns}
    if not available:
        raise ValueError(f"No benchmark tickers available for {name}")
    normalized = prices[list(available)].dropna()
    returns = normalized.pct_change().fillna(0)
    weight_series = pd.Series(available)
    weight_series = weight_series / weight_series.sum()
    curve = (1 + returns.mul(weight_series, axis=1).sum(axis=1)).cumprod()
    curve.name = name
    return curve


def summarize_equity_curve(curve: pd.Series, trade_count: int = 0) -> dict[str, float]:
    returns = curve.pct_change().fillna(0)
    max_drawdown = calculate_max_drawdown(curve)
    annualized = calculate_annualized_return(curve)
    return {
        "annual_return_pct": round(annualized, 2),
        "cumulative_return_pct": round(calculate_cumulative_return(curve), 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(calculate_sharpe_ratio(returns), 2),
        "sortino_ratio": round(calculate_sortino_ratio(returns), 2),
        "calmar_ratio": round(calculate_calmar_ratio(curve), 2),
        "trade_count": float(trade_count),
    }


def build_benchmark_summary(
    strategy_curve: pd.Series,
    prices: pd.DataFrame,
    trade_count: int,
) -> pd.DataFrame:
    curves = [
        strategy_curve,
        buy_and_hold_curve(prices, {"SPY": 1.0}, "Buy & Hold SPY"),
        buy_and_hold_curve(prices, {"QQQ": 1.0}, "Buy & Hold QQQ"),
        buy_and_hold_curve(prices, {"SPY": 0.6, "IEF": 0.4}, "60/40 SPY/IEF") if "IEF" in prices.columns else buy_and_hold_curve(prices, {"SPY": 0.6}, "60/40 SPY/Cash"),
        buy_and_hold_curve(prices, {"SMH": 1.0}, "Buy & Hold SMH") if "SMH" in prices.columns else buy_and_hold_curve(prices, {"QQQ": 1.0}, "Buy & Hold SMH unavailable"),
    ]
    rows = []
    for curve in curves:
        aligned = curve.reindex(strategy_curve.index).ffill().dropna()
        summary = summarize_equity_curve(aligned, trade_count if curve.name == strategy_curve.name else 0)
        summary["strategy"] = curve.name
        rows.append(summary)
    columns = [
        "strategy",
        "annual_return_pct",
        "cumulative_return_pct",
        "max_drawdown_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "trade_count",
    ]
    return pd.DataFrame(rows).loc[:, columns]


def slice_prices_and_indicators(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    start: str,
    end: str,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    sliced_prices = prices.loc[(prices.index >= start_ts) & (prices.index <= end_ts)]
    sliced_indicators = {
        ticker: frame.loc[(frame.index >= start_ts) & (frame.index <= end_ts)]
        for ticker, frame in indicator_frames.items()
    }
    return sliced_prices, sliced_indicators


def run_regime_validation(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    config: BacktestConfig,
    regimes: list[dict[str, str]] | None = None,
) -> pd.DataFrame:
    validation_regimes = regimes or [
        {"name": "2020 コロナ後回復", "start": "2020-01-01", "end": "2020-12-31"},
        {"name": "2021 過熱相場", "start": "2021-01-01", "end": "2021-12-31"},
        {"name": "2022 金利上昇・下落", "start": "2022-01-01", "end": "2022-12-31"},
        {"name": "2023 AI初動", "start": "2023-01-01", "end": "2023-12-31"},
        {"name": "2024 AI加速", "start": "2024-01-01", "end": "2024-12-31"},
        {"name": "2025-2026 テーマ分散", "start": "2025-01-01", "end": "2026-12-31"},
    ]
    rows: list[dict[str, float | str]] = []
    for regime in validation_regimes:
        start_ts = pd.Timestamp(regime["start"])
        end_ts = pd.Timestamp(regime["end"])
        warmup_start = (start_ts - pd.DateOffset(days=420)).strftime("%Y-%m-%d")
        regime_prices, regime_indicators = slice_prices_and_indicators(
            prices,
            indicator_frames,
            warmup_start,
            regime["end"],
        )
        if len(regime_prices) < 60:
            continue
        curve, diagnostics = run_rotation_backtest(regime_prices, regime_indicators, satellite_tickers, config)
        regime_curve = curve.loc[(curve.index >= start_ts) & (curve.index <= end_ts)]
        if len(regime_curve) < 20:
            continue
        regime_curve = regime_curve / regime_curve.iloc[0]
        regime_price_window = prices.loc[(prices.index >= start_ts) & (prices.index <= end_ts)]
        trade_count = int(diagnostics.iloc[0]["trade_count"])
        strategy = summarize_equity_curve(regime_curve, trade_count)
        summary = build_benchmark_summary(regime_curve, regime_price_window, trade_count)
        spy = summary[summary["strategy"] == "Buy & Hold SPY"].iloc[0]
        qqq = summary[summary["strategy"] == "Buy & Hold QQQ"].iloc[0]
        smh = summary[summary["strategy"] == "Buy & Hold SMH"].iloc[0]
        rows.append(
            {
                "regime": regime["name"],
                "start": regime["start"],
                "end": regime["end"],
                "strategy_annual_return_pct": strategy["annual_return_pct"],
                "strategy_cumulative_return_pct": strategy["cumulative_return_pct"],
                "strategy_max_drawdown_pct": strategy["max_drawdown_pct"],
                "strategy_sharpe_ratio": strategy["sharpe_ratio"],
                "strategy_calmar_ratio": strategy["calmar_ratio"],
                "spy_annual_return_pct": float(spy["annual_return_pct"]),
                "qqq_annual_return_pct": float(qqq["annual_return_pct"]),
                "smh_annual_return_pct": float(smh["annual_return_pct"]),
                "vs_spy_pct": round(strategy["annual_return_pct"] - float(spy["annual_return_pct"]), 2),
                "vs_qqq_pct": round(strategy["annual_return_pct"] - float(qqq["annual_return_pct"]), 2),
                "vs_smh_pct": round(strategy["annual_return_pct"] - float(smh["annual_return_pct"]), 2),
                "trade_count": strategy["trade_count"],
            }
        )
    return pd.DataFrame(rows)


def build_rebalance_selection_log(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    config: BacktestConfig,
    start: str,
    end: str,
) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    warmup_start = (start_ts - pd.DateOffset(days=420)).strftime("%Y-%m-%d")
    audit_prices, audit_indicators = slice_prices_and_indicators(prices, indicator_frames, warmup_start, end)
    returns = audit_prices.pct_change().fillna(0)
    common_index = audit_prices.dropna().index
    scores = build_score_matrix(audit_prices, audit_indicators, profile=config.score_profile).reindex(common_index)
    rebalance_dates = returns.groupby(pd.Grouper(freq=config.rebalance_frequency)).tail(1).index
    rows: list[dict[str, float | str]] = []
    for date in rebalance_dates:
        if date < start_ts or date > end_ts:
            continue
        selected = choose_satellites(
            scores,
            date,
            satellite_tickers,
            config.top_satellites,
            min_score=config.min_satellite_score,
        )
        ranked = scores.loc[date, [ticker for ticker in satellite_tickers if ticker in scores.columns]].dropna()
        ranked = ranked.sort_values(ascending=False).head(8)
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "selected": ", ".join(selected) if selected else "None",
                "top_scores": " / ".join(f"{ticker}:{score:.1f}" for ticker, score in ranked.items()),
            }
        )
    return pd.DataFrame(rows)


def run_parameter_grid_search(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    satellite_weights: list[float] | None = None,
    top_satellite_counts: list[int] | None = None,
    rebalance_frequencies: list[str] | None = None,
    drawdown_stops: list[float] | None = None,
    min_scores: list[float] | None = None,
    score_profiles: list[str] | None = None,
) -> pd.DataFrame:
    weights = satellite_weights or [0.15, 0.20, 0.25, 0.30, 0.35]
    top_counts = top_satellite_counts or [1, 2, 3, 4]
    frequencies = rebalance_frequencies or ["W-FRI", "ME"]
    stops = drawdown_stops or [-5.0, -8.0, -12.0]
    score_thresholds = min_scores or [35.0, 45.0, 55.0]
    profiles = score_profiles or ["balanced"]
    rows: list[dict[str, float | int | str]] = []
    for satellite_weight in weights:
        for top_count in top_counts:
            for frequency in frequencies:
                for drawdown_stop in stops:
                    for min_score in score_thresholds:
                        for profile in profiles:
                            config = BacktestConfig(
                                satellite_weight=satellite_weight,
                                top_satellites=top_count,
                                rebalance_frequency=frequency,
                                stop_new_buy_drawdown_pct=drawdown_stop,
                                min_satellite_score=min_score,
                                score_profile=profile,
                            )
                            curve, diagnostics = run_rotation_backtest(
                                prices,
                                indicator_frames,
                                satellite_tickers,
                                config,
                            )
                            trade_count = int(diagnostics.iloc[0]["trade_count"])
                            summary = summarize_equity_curve(curve, trade_count)
                            rows.append(
                                {
                                    "satellite_weight_pct": round(satellite_weight * 100, 2),
                                    "top_satellites": top_count,
                                    "rebalance_frequency": frequency,
                                    "drawdown_stop_pct": drawdown_stop,
                                    "min_satellite_score": min_score,
                                    "score_profile": profile,
                                    **summary,
                                    "avg_selected_satellites": round(
                                        float(diagnostics.iloc[0]["avg_selected_satellites"]),
                                        2,
                                    ),
                                }
                            )
    result = pd.DataFrame(rows)
    result["risk_adjusted_rank_score"] = (
        result["annual_return_pct"]
        + result["calmar_ratio"] * 10
        + result["sharpe_ratio"] * 5
        + result["max_drawdown_pct"] * 0.25
    ).round(2)
    return result.sort_values(
        ["risk_adjusted_rank_score", "annual_return_pct", "max_drawdown_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def run_signal_execution_backtest(
    prices: pd.DataFrame,
    signal_history: pd.DataFrame,
    config: SignalExecutionConfig | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    cfg = config or SignalExecutionConfig()
    common_index = prices.dropna(how="all").index
    if common_index.empty:
        return pd.Series(dtype=float, name="MASATO Signal Execution"), pd.DataFrame()
    returns = prices.pct_change().fillna(0).reindex(common_index).fillna(0)
    signal_frame = signal_history.copy()
    buy_signals = BUY_SIGNAL_LABELS
    signals_by_date: dict[pd.Timestamp, pd.DataFrame] = {}
    if not signal_frame.empty and "snapshot" in signal_frame.columns:
        for snapshot, group in signal_frame.groupby("snapshot"):
            signals_by_date[pd.Timestamp(snapshot)] = group

    open_positions: dict[str, dict[str, object]] = {}
    trades: list[dict[str, object]] = []
    equity = 1.0
    equity_values: list[float] = []
    equity_index: list[pd.Timestamp] = []

    for date, daily_returns in returns.iterrows():
        exited: list[str] = []
        for ticker, position in list(open_positions.items()):
            if ticker not in prices.columns or pd.isna(prices.at[date, ticker]):
                continue
            price = float(prices.at[date, ticker])
            holding_days = int(position.get("holding_days", 0)) + 1
            position["holding_days"] = holding_days
            stop_price = float(position["stop_price"])
            target_price = float(position["target_price"])
            exit_reason = ""
            exit_price = price
            if price <= stop_price:
                exit_reason = "停止価格"
                exit_price = stop_price
            elif price >= target_price:
                exit_reason = "保守目標"
                exit_price = target_price
            elif holding_days >= cfg.max_holding_days:
                exit_reason = "20日保有"
            if exit_reason:
                entry_price = float(position["entry_price"])
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": date.date().isoformat(),
                        "ETF": ticker,
                        "exit_reason": exit_reason,
                        "return_pct": round((exit_price / entry_price - 1) * 100, 2),
                    }
                )
                exited.append(ticker)
        for ticker in exited:
            open_positions.pop(ticker, None)

        todays_signals = signals_by_date.get(date)
        if todays_signals is not None:
            candidates = todays_signals[todays_signals["判定"].isin(buy_signals)]
            if "ETFスコア" in candidates.columns:
                candidates = candidates.sort_values("ETFスコア", ascending=False)
            for row in candidates.to_dict("records"):
                if len(open_positions) >= cfg.max_positions:
                    break
                ticker = str(row.get("ETF", ""))
                if not ticker or ticker in open_positions or ticker not in prices.columns:
                    continue
                if pd.isna(prices.at[date, ticker]):
                    continue
                price = float(prices.at[date, ticker])
                current_price = float(row.get("現在価格", 0.0) or 0.0)
                entry_price = float(row.get("第1買い", 0.0) or 0.0) * cfg.entry_multiplier
                if current_price > 0:
                    entry_price = min(entry_price, current_price)
                stop_price = float(row.get("停止価格", 0.0) or 0.0) * cfg.stop_multiplier
                target_price = float(row.get("保守目標", 0.0) or 0.0)
                if price <= 0 or entry_price <= 0 or stop_price <= 0 or target_price <= 0:
                    continue
                if price <= entry_price:
                    if stop_price >= price:
                        stop_price = price * 0.97
                    open_positions[ticker] = {
                        "entry_date": date.date().isoformat(),
                        "entry_price": price,
                        "stop_price": stop_price,
                        "target_price": target_price,
                        "holding_days": 0,
                    }

        weights = pd.Series(0.0, index=returns.columns)
        if "SPY" in weights.index:
            weights["SPY"] = cfg.core_spy_weight
        if "QQQ" in weights.index:
            weights["QQQ"] = cfg.core_qqq_weight
        if open_positions:
            per_position = cfg.satellite_weight / max(cfg.max_positions, 1)
            for ticker in open_positions:
                if ticker in weights.index:
                    weights[ticker] = per_position
        equity *= 1 + float((weights * daily_returns).sum())
        equity_values.append(equity)
        equity_index.append(date)

    curve = pd.Series(equity_values, index=equity_index, name="MASATO Signal Execution")
    trade_returns = pd.Series([trade["return_pct"] for trade in trades], dtype=float)
    diagnostics = pd.DataFrame(
        {
            "trade_count": [len(trades)],
            "open_positions_end": [len(open_positions)],
            "avg_trade_return_pct": [round(float(trade_returns.mean()), 2) if not trade_returns.empty else 0.0],
        }
    )
    return curve, diagnostics


def run_signal_execution_grid_search(
    prices: pd.DataFrame,
    signal_history: pd.DataFrame,
    entry_multipliers: list[float] | None = None,
    stop_multipliers: list[float] | None = None,
    holding_days: list[int] | None = None,
    max_positions_list: list[int] | None = None,
) -> pd.DataFrame:
    entries = entry_multipliers or [1.02, 1.04, 1.06]
    stops = stop_multipliers or [0.95, 1.0]
    holding = holding_days or [20, 40, 60]
    positions = max_positions_list or [2, 4, 6]
    rows: list[dict[str, float | int]] = []
    for entry_multiplier in entries:
        for stop_multiplier in stops:
            for max_holding_days in holding:
                for max_positions in positions:
                    cfg = SignalExecutionConfig(
                        entry_multiplier=entry_multiplier,
                        stop_multiplier=stop_multiplier,
                        max_holding_days=max_holding_days,
                        max_positions=max_positions,
                    )
                    curve, diagnostics = run_signal_execution_backtest(prices, signal_history, cfg)
                    trade_count = int(diagnostics.iloc[0]["trade_count"]) if not diagnostics.empty else 0
                    summary = summarize_equity_curve(curve, trade_count)
                    score = (
                        summary["annual_return_pct"]
                        + summary["calmar_ratio"] * 10
                        + summary["sharpe_ratio"] * 5
                        + summary["max_drawdown_pct"] * 0.25
                    )
                    rows.append(
                        {
                            "entry_multiplier": entry_multiplier,
                            "stop_multiplier": stop_multiplier,
                            "max_holding_days": max_holding_days,
                            "max_positions": max_positions,
                            **summary,
                            "avg_trade_return_pct": float(diagnostics.iloc[0]["avg_trade_return_pct"]) if not diagnostics.empty else 0.0,
                            "risk_adjusted_rank_score": round(score, 2),
                        }
                    )
    return pd.DataFrame(rows).sort_values(
        ["risk_adjusted_rank_score", "annual_return_pct", "max_drawdown_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def filter_hybrid_signal_candidates(signals: pd.DataFrame, config: HybridSignalConfig) -> pd.DataFrame:
    if signals.empty or "判定" not in signals.columns:
        return pd.DataFrame(columns=signals.columns)
    policy = config.candidate_policy
    if policy == "strict_buy":
        candidates = signals[signals["判定"].isin(BUY_SIGNAL_LABELS)].copy()
    elif policy == "watch_and_buy":
        candidates = signals[signals["判定"].isin(WATCH_SIGNAL_LABELS)].copy()
    elif policy == "score_gate":
        candidates = signals[~signals["判定"].isin(HARD_RISK_SIGNAL_LABELS)].copy()
    elif policy == "watch_score_gate":
        candidates = signals[signals["判定"].isin(WATCH_SIGNAL_LABELS)].copy()
    else:
        raise ValueError(f"Unknown hybrid candidate policy: {policy}")

    if policy in {"score_gate", "watch_score_gate"}:
        required = {"ETFスコア", "テーマスコア", "RR"}
        if not required.issubset(candidates.columns):
            return pd.DataFrame(columns=signals.columns)
        candidates = candidates[
            (candidates["ETFスコア"].astype(float) >= config.min_etf_score)
            & (candidates["テーマスコア"].astype(float) >= config.min_theme_score)
            & (candidates["RR"].astype(float) >= config.min_rr)
        ].copy()
    if "ETF" in candidates.columns:
        blocked = set(config.blocked_signal_tickers)
        if blocked:
            candidates = candidates[~candidates["ETF"].astype(str).isin(blocked)].copy()
        if config.ticker_min_etf_scores and "ETFスコア" in candidates.columns:
            ticker_min_etf_scores = candidates["ETF"].astype(str).map(config.ticker_min_etf_scores)
            candidates = candidates[
                ticker_min_etf_scores.isna()
                | (candidates["ETFスコア"].astype(float) >= ticker_min_etf_scores)
            ].copy()
        if config.ticker_min_theme_scores and "テーマスコア" in candidates.columns:
            ticker_min_theme_scores = candidates["ETF"].astype(str).map(config.ticker_min_theme_scores)
            candidates = candidates[
                ticker_min_theme_scores.isna()
                | (candidates["テーマスコア"].astype(float) >= ticker_min_theme_scores)
            ].copy()
        if config.ticker_min_rr_values and "RR" in candidates.columns:
            ticker_min_rr_values = candidates["ETF"].astype(str).map(config.ticker_min_rr_values)
            candidates = candidates[
                ticker_min_rr_values.isna()
                | (candidates["RR"].astype(float) >= ticker_min_rr_values)
            ].copy()
    if "ETFスコア" in candidates.columns:
        candidates = candidates.sort_values("ETFスコア", ascending=False)
    return candidates


def run_hybrid_rotation_signal_backtest(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    signal_history: pd.DataFrame,
    rotation_config: BacktestConfig | None = None,
    signal_config: HybridSignalConfig | None = None,
    trade_log: list[dict[str, object]] | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    rotation_cfg = rotation_config or BacktestConfig()
    signal_cfg = signal_config or HybridSignalConfig()
    common_index = prices.dropna(how="all").index
    if common_index.empty:
        return pd.Series(dtype=float, name="MASATO Hybrid Rotation+Signal"), pd.DataFrame()

    returns = prices.pct_change().fillna(0).reindex(common_index).fillna(0)
    scores = build_score_matrix(
        prices,
        indicator_frames,
        profile="balanced" if rotation_cfg.score_profile == "adaptive" else rotation_cfg.score_profile,
    ).reindex(common_index)
    momentum_scores = (
        build_score_matrix(prices, indicator_frames, profile="momentum").reindex(common_index)
        if rotation_cfg.score_profile == "adaptive"
        else scores
    )
    rebalance_dates = returns.groupby(pd.Grouper(freq=rotation_cfg.rebalance_frequency)).tail(1).index
    rebalance_dates = [date for date in rebalance_dates if date >= returns.index[min(252, len(returns) - 1)]]
    rebalance_set = set(rebalance_dates)
    signal_frame = signal_history.copy()
    buy_signals = {"強気買い候補", "買い候補", "押し目待ち", "積立候補"}
    signals_by_date: dict[pd.Timestamp, pd.DataFrame] = {}
    if not signal_frame.empty and "snapshot" in signal_frame.columns:
        for snapshot, group in signal_frame.groupby("snapshot"):
            signals_by_date[pd.Timestamp(snapshot)] = group

    selected_rotation: list[str] = []
    last_rotation_set: set[str] = set()
    open_positions: dict[str, dict[str, object]] = {}
    trades: list[dict[str, object]] = []
    equity = 1.0
    running_high = 1.0
    equity_values: list[float] = []
    equity_index: list[pd.Timestamp] = []
    rotation_trade_count = 0
    signal_entry_count = 0
    acceleration_rebalance_count = 0
    in_acceleration_regime = False

    for date, daily_returns in returns.iterrows():
        drawdown_pct = (equity / running_high - 1) * 100
        can_add_risk = drawdown_pct > rotation_cfg.stop_new_buy_drawdown_pct
        in_acceleration_regime = is_acceleration_regime(indicator_frames, date)

        exited: list[str] = []
        for ticker, position in list(open_positions.items()):
            if ticker not in prices.columns or pd.isna(prices.at[date, ticker]):
                continue
            price = float(prices.at[date, ticker])
            holding_days = int(position.get("holding_days", 0)) + 1
            position["holding_days"] = holding_days
            stop_price = float(position["stop_price"])
            target_price = float(position["target_price"])
            exit_reason = ""
            exit_price = price
            if price <= stop_price:
                exit_reason = "停止価格"
                exit_price = stop_price
            elif price >= target_price:
                exit_reason = "保守目標"
                exit_price = target_price
            elif holding_days >= signal_cfg.max_holding_days:
                exit_reason = "期限"
            if exit_reason:
                entry_price = float(position["entry_price"])
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": date.date().isoformat(),
                        "ETF": ticker,
                        "signal": position.get("signal", ""),
                        "snapshot": position.get("snapshot", ""),
                        "etf_score": position.get("etf_score", 0.0),
                        "theme_score": position.get("theme_score", 0.0),
                        "rr": position.get("rr", 0.0),
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(exit_price, 4),
                        "exit_reason": exit_reason,
                        "return_pct": round((exit_price / entry_price - 1) * 100, 2),
                    }
                )
                exited.append(ticker)
        for ticker in exited:
            open_positions.pop(ticker, None)

        if date in rebalance_set:
            active_scores = scores
            min_score = rotation_cfg.min_satellite_score
            if rotation_cfg.score_profile == "adaptive" and in_acceleration_regime:
                active_scores = momentum_scores
                min_score = min(rotation_cfg.min_satellite_score, 35.0)
                acceleration_rebalance_count += 1
            selected_rotation = (
                choose_satellites(
                    active_scores,
                    date,
                    satellite_tickers,
                    rotation_cfg.top_satellites,
                    min_score=min_score,
                )
                if can_add_risk
                else []
            )
            new_rotation_set = set(selected_rotation)
            rotation_trade_count += len(new_rotation_set.symmetric_difference(last_rotation_set))
            last_rotation_set = new_rotation_set

        todays_signals = signals_by_date.get(date)
        allow_new_signal_entries = not (
            in_acceleration_regime and signal_cfg.acceleration_overlay_mode in {"block_new_entries", "disable_overlay"}
        )
        if can_add_risk and allow_new_signal_entries and todays_signals is not None:
            candidates = filter_hybrid_signal_candidates(todays_signals, signal_cfg)
            for row in candidates.to_dict("records"):
                if len(open_positions) >= signal_cfg.max_signal_positions:
                    break
                ticker = str(row.get("ETF", ""))
                if not ticker or ticker in open_positions or ticker not in prices.columns:
                    continue
                if pd.isna(prices.at[date, ticker]):
                    continue
                price = float(prices.at[date, ticker])
                current_price = float(row.get("現在価格", 0.0) or 0.0)
                entry_price = float(row.get("第1買い", 0.0) or 0.0) * signal_cfg.entry_multiplier
                if current_price > 0:
                    entry_price = min(entry_price, current_price)
                stop_price = float(row.get("停止価格", 0.0) or 0.0) * signal_cfg.stop_multiplier
                target_price = float(row.get("保守目標", 0.0) or 0.0)
                if price <= 0 or entry_price <= 0 or stop_price <= 0 or target_price <= 0:
                    continue
                entry_day_return_pct = float(daily_returns.get(ticker, 0.0) * 100)
                if entry_day_return_pct <= signal_cfg.max_entry_day_loss_pct:
                    continue
                if price <= entry_price:
                    if stop_price >= price:
                        stop_price = price * 0.97
                    open_positions[ticker] = {
                        "entry_date": date.date().isoformat(),
                        "entry_price": price,
                        "stop_price": stop_price,
                        "target_price": target_price,
                        "holding_days": 0,
                        "signal": str(row.get("判定", "")),
                        "snapshot": row.get("snapshot", ""),
                        "etf_score": float(row.get("ETFスコア", 0.0) or 0.0),
                        "theme_score": float(row.get("テーマスコア", 0.0) or 0.0),
                        "rr": float(row.get("RR", 0.0) or 0.0),
                    }
                    signal_entry_count += 1

        weights = pd.Series(0.0, index=returns.columns)
        if "SPY" in weights.index:
            weights["SPY"] = rotation_cfg.core_spy_weight
        if "QQQ" in weights.index:
            weights["QQQ"] = rotation_cfg.core_qqq_weight

        satellite_weight = rotation_cfg.satellite_weight if can_add_risk else 0.0
        signal_weight = min(signal_cfg.signal_overlay_weight, satellite_weight) if open_positions else 0.0
        if in_acceleration_regime and signal_cfg.acceleration_overlay_mode == "disable_overlay":
            signal_weight = 0.0
        elif in_acceleration_regime and signal_cfg.acceleration_overlay_mode == "half_overlay":
            signal_weight *= 0.5
        rotation_weight = max(0.0, satellite_weight - signal_weight)
        if selected_rotation and rotation_weight > 0:
            per_rotation = rotation_weight / len(selected_rotation)
            for ticker in selected_rotation:
                if ticker in weights.index:
                    weights[ticker] += per_rotation
        if open_positions and signal_weight > 0:
            per_signal = signal_weight / len(open_positions)
            for ticker in open_positions:
                if ticker in weights.index:
                    weights[ticker] += per_signal

        if weights.sum() > 1:
            weights = weights / weights.sum()
        equity *= 1 + float((weights * daily_returns).sum())
        running_high = max(running_high, equity)
        equity_values.append(equity)
        equity_index.append(date)

    curve = pd.Series(equity_values, index=equity_index, name="MASATO Hybrid Rotation+Signal")
    trade_returns = pd.Series([trade["return_pct"] for trade in trades], dtype=float)
    diagnostics = pd.DataFrame(
        {
            "rotation_trade_count": [rotation_trade_count],
            "signal_entry_count": [signal_entry_count],
            "signal_exit_count": [len(trades)],
            "open_signal_positions_end": [len(open_positions)],
            "avg_signal_trade_return_pct": [round(float(trade_returns.mean()), 2) if not trade_returns.empty else 0.0],
            "acceleration_rebalance_count": [acceleration_rebalance_count],
        }
    )
    if trade_log is not None:
        trade_log.extend(trades)
    return curve, diagnostics


def run_hybrid_signal_grid_search(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    signal_history: pd.DataFrame,
    rotation_config: BacktestConfig | None = None,
    overlay_weights: list[float] | None = None,
    entry_multipliers: list[float] | None = None,
    stop_multipliers: list[float] | None = None,
    holding_days: list[int] | None = None,
    max_positions_list: list[int] | None = None,
    candidate_policies: list[str] | None = None,
    min_score_thresholds: list[float] | None = None,
    min_rr_values: list[float] | None = None,
    acceleration_overlay_modes: list[str] | None = None,
) -> pd.DataFrame:
    overlays = overlay_weights or [0.05, 0.10, 0.15]
    entries = entry_multipliers or [1.02, 1.04, 1.06]
    stops = stop_multipliers or [0.95, 1.0]
    holding = holding_days or [40, 60]
    positions = max_positions_list or [2, 4]
    policies = candidate_policies or ["strict_buy", "watch_score_gate", "score_gate"]
    thresholds = min_score_thresholds or [65.0, 70.0]
    rr_values = min_rr_values or [1.5, 2.0]
    acceleration_modes = acceleration_overlay_modes or ["normal"]
    rows: list[dict[str, float | int]] = []
    for overlay_weight in overlays:
        for entry_multiplier in entries:
            for stop_multiplier in stops:
                for max_holding_days in holding:
                    for max_positions in positions:
                        for policy in policies:
                            score_threshold_loop = thresholds if "score_gate" in policy else [70.0]
                            rr_loop = rr_values if "score_gate" in policy else [2.0]
                            for min_score in score_threshold_loop:
                                for min_rr in rr_loop:
                                    for acceleration_mode in acceleration_modes:
                                        signal_cfg = HybridSignalConfig(
                                            signal_overlay_weight=overlay_weight,
                                            entry_multiplier=entry_multiplier,
                                            stop_multiplier=stop_multiplier,
                                            max_holding_days=max_holding_days,
                                            max_signal_positions=max_positions,
                                            candidate_policy=policy,
                                            min_etf_score=min_score,
                                            min_theme_score=min_score,
                                            min_rr=min_rr,
                                            acceleration_overlay_mode=acceleration_mode,
                                        )
                                        curve, diagnostics = run_hybrid_rotation_signal_backtest(
                                            prices,
                                            indicator_frames,
                                            satellite_tickers,
                                            signal_history,
                                            rotation_config,
                                            signal_cfg,
                                        )
                                        signal_exits = int(diagnostics.iloc[0]["signal_exit_count"]) if not diagnostics.empty else 0
                                        rotation_trades = int(diagnostics.iloc[0]["rotation_trade_count"]) if not diagnostics.empty else 0
                                        summary = summarize_equity_curve(curve, rotation_trades + signal_exits)
                                        score = (
                                            summary["annual_return_pct"]
                                            + summary["calmar_ratio"] * 10
                                            + summary["sharpe_ratio"] * 5
                                            + summary["max_drawdown_pct"] * 0.25
                                        )
                                        rows.append(
                                            {
                                                "candidate_policy": policy,
                                                "acceleration_overlay_mode": acceleration_mode,
                                                "signal_overlay_weight_pct": round(overlay_weight * 100, 2),
                                                "entry_multiplier": entry_multiplier,
                                                "stop_multiplier": stop_multiplier,
                                                "max_holding_days": max_holding_days,
                                                "max_signal_positions": max_positions,
                                                "min_score": min_score,
                                                "min_rr": min_rr,
                                                **summary,
                                                "rotation_trade_count": rotation_trades,
                                                "signal_entry_count": int(diagnostics.iloc[0]["signal_entry_count"]) if not diagnostics.empty else 0,
                                                "signal_exit_count": signal_exits,
                                                "avg_signal_trade_return_pct": float(diagnostics.iloc[0]["avg_signal_trade_return_pct"]) if not diagnostics.empty else 0.0,
                                                "risk_adjusted_rank_score": round(score, 2),
                                            }
                                        )
    return pd.DataFrame(rows).sort_values(
        ["risk_adjusted_rank_score", "annual_return_pct", "max_drawdown_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def run_hybrid_regime_validation(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    signal_history: pd.DataFrame,
    rotation_config: BacktestConfig,
    signal_config: HybridSignalConfig,
    regimes: list[dict[str, str]] | None = None,
) -> pd.DataFrame:
    validation_regimes = regimes or [
        {"name": "2020 コロナ後回復", "start": "2020-01-01", "end": "2020-12-31"},
        {"name": "2021 過熱相場", "start": "2021-01-01", "end": "2021-12-31"},
        {"name": "2022 金利上昇・下落", "start": "2022-01-01", "end": "2022-12-31"},
        {"name": "2023 AI初動", "start": "2023-01-01", "end": "2023-12-31"},
        {"name": "2024 AI加速", "start": "2024-01-01", "end": "2024-12-31"},
        {"name": "2025-2026 テーマ分散", "start": "2025-01-01", "end": "2026-12-31"},
    ]
    rows: list[dict[str, float | str]] = []
    signal_frame = signal_history.copy()
    if not signal_frame.empty and "snapshot" in signal_frame.columns:
        signal_frame["snapshot_ts"] = pd.to_datetime(signal_frame["snapshot"])
    for regime in validation_regimes:
        start_ts = pd.Timestamp(regime["start"])
        end_ts = pd.Timestamp(regime["end"])
        warmup_start = (start_ts - pd.DateOffset(days=420)).strftime("%Y-%m-%d")
        regime_prices, regime_indicators = slice_prices_and_indicators(
            prices,
            indicator_frames,
            warmup_start,
            regime["end"],
        )
        if len(regime_prices) < 60:
            continue
        if not signal_frame.empty and "snapshot_ts" in signal_frame.columns:
            regime_signals = signal_frame[
                (signal_frame["snapshot_ts"] >= pd.Timestamp(warmup_start))
                & (signal_frame["snapshot_ts"] <= end_ts)
            ].drop(columns=["snapshot_ts"])
        else:
            regime_signals = pd.DataFrame()

        hybrid_curve, hybrid_diag = run_hybrid_rotation_signal_backtest(
            regime_prices,
            regime_indicators,
            satellite_tickers,
            regime_signals,
            rotation_config,
            signal_config,
        )
        rotation_curve, rotation_diag = run_rotation_backtest(regime_prices, regime_indicators, satellite_tickers, rotation_config)
        regime_curve = hybrid_curve.loc[(hybrid_curve.index >= start_ts) & (hybrid_curve.index <= end_ts)]
        regime_rotation_curve = rotation_curve.loc[(rotation_curve.index >= start_ts) & (rotation_curve.index <= end_ts)]
        if len(regime_curve) < 20 or len(regime_rotation_curve) < 20:
            continue
        regime_curve = regime_curve / regime_curve.iloc[0]
        regime_rotation_curve = regime_rotation_curve / regime_rotation_curve.iloc[0]
        regime_price_window = prices.loc[(prices.index >= start_ts) & (prices.index <= end_ts)]
        signal_exits = int(hybrid_diag.iloc[0]["signal_exit_count"]) if not hybrid_diag.empty else 0
        rotation_trades = int(hybrid_diag.iloc[0]["rotation_trade_count"]) if not hybrid_diag.empty else 0
        hybrid = summarize_equity_curve(regime_curve, rotation_trades + signal_exits)
        rotation = summarize_equity_curve(regime_rotation_curve, int(rotation_diag.iloc[0]["trade_count"]))
        summary = build_benchmark_summary(regime_curve, regime_price_window, rotation_trades + signal_exits)
        spy = summary[summary["strategy"] == "Buy & Hold SPY"].iloc[0]
        qqq = summary[summary["strategy"] == "Buy & Hold QQQ"].iloc[0]
        smh = summary[summary["strategy"] == "Buy & Hold SMH"].iloc[0]
        rows.append(
            {
                "regime": regime["name"],
                "start": regime["start"],
                "end": regime["end"],
                "hybrid_annual_return_pct": hybrid["annual_return_pct"],
                "hybrid_cumulative_return_pct": hybrid["cumulative_return_pct"],
                "hybrid_max_drawdown_pct": hybrid["max_drawdown_pct"],
                "hybrid_sharpe_ratio": hybrid["sharpe_ratio"],
                "hybrid_calmar_ratio": hybrid["calmar_ratio"],
                "rotation_annual_return_pct": rotation["annual_return_pct"],
                "rotation_max_drawdown_pct": rotation["max_drawdown_pct"],
                "vs_rotation_pct": round(hybrid["annual_return_pct"] - rotation["annual_return_pct"], 2),
                "spy_annual_return_pct": float(spy["annual_return_pct"]),
                "qqq_annual_return_pct": float(qqq["annual_return_pct"]),
                "smh_annual_return_pct": float(smh["annual_return_pct"]),
                "vs_spy_pct": round(hybrid["annual_return_pct"] - float(spy["annual_return_pct"]), 2),
                "vs_qqq_pct": round(hybrid["annual_return_pct"] - float(qqq["annual_return_pct"]), 2),
                "vs_smh_pct": round(hybrid["annual_return_pct"] - float(smh["annual_return_pct"]), 2),
                "signal_entry_count": int(hybrid_diag.iloc[0]["signal_entry_count"]) if not hybrid_diag.empty else 0,
                "signal_exit_count": signal_exits,
            }
        )
    return pd.DataFrame(rows)


def run_hybrid_entry_guard_search(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    signal_history: pd.DataFrame,
    rotation_config: BacktestConfig,
    base_signal_config: HybridSignalConfig,
    max_entry_day_loss_values: list[float] | None = None,
) -> pd.DataFrame:
    loss_values = max_entry_day_loss_values or [-100.0, -5.0, -3.0, -2.0]
    rows: list[dict[str, float | int]] = []
    for max_entry_day_loss_pct in loss_values:
        cfg = copy_hybrid_signal_config(base_signal_config, max_entry_day_loss_pct=max_entry_day_loss_pct)
        curve, diagnostics = run_hybrid_rotation_signal_backtest(
            prices,
            indicator_frames,
            satellite_tickers,
            signal_history,
            rotation_config,
            cfg,
        )
        signal_exits = int(diagnostics.iloc[0]["signal_exit_count"]) if not diagnostics.empty else 0
        rotation_trades = int(diagnostics.iloc[0]["rotation_trade_count"]) if not diagnostics.empty else 0
        summary = summarize_equity_curve(curve, rotation_trades + signal_exits)
        score = (
            summary["annual_return_pct"]
            + summary["calmar_ratio"] * 10
            + summary["sharpe_ratio"] * 5
            + summary["max_drawdown_pct"] * 0.25
        )
        rows.append(
            {
                "max_entry_day_loss_pct": max_entry_day_loss_pct,
                **summary,
                "rotation_trade_count": rotation_trades,
                "signal_entry_count": int(diagnostics.iloc[0]["signal_entry_count"]) if not diagnostics.empty else 0,
                "signal_exit_count": signal_exits,
                "avg_signal_trade_return_pct": float(diagnostics.iloc[0]["avg_signal_trade_return_pct"]) if not diagnostics.empty else 0.0,
                "risk_adjusted_rank_score": round(score, 2),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["risk_adjusted_rank_score", "annual_return_pct", "max_drawdown_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def run_hybrid_acceleration_mode_search(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    signal_history: pd.DataFrame,
    rotation_config: BacktestConfig,
    base_signal_config: HybridSignalConfig,
    acceleration_modes: list[str] | None = None,
) -> pd.DataFrame:
    modes = acceleration_modes or ["normal", "disable_overlay", "half_overlay", "block_new_entries"]
    rows: list[dict[str, float | int | str]] = []
    for mode in modes:
        cfg = copy_hybrid_signal_config(base_signal_config, acceleration_overlay_mode=mode)
        curve, diagnostics = run_hybrid_rotation_signal_backtest(
            prices,
            indicator_frames,
            satellite_tickers,
            signal_history,
            rotation_config,
            cfg,
        )
        signal_exits = int(diagnostics.iloc[0]["signal_exit_count"]) if not diagnostics.empty else 0
        rotation_trades = int(diagnostics.iloc[0]["rotation_trade_count"]) if not diagnostics.empty else 0
        summary = summarize_equity_curve(curve, rotation_trades + signal_exits)
        score = (
            summary["annual_return_pct"]
            + summary["calmar_ratio"] * 10
            + summary["sharpe_ratio"] * 5
            + summary["max_drawdown_pct"] * 0.25
        )
        rows.append(
            {
                "acceleration_overlay_mode": mode,
                **summary,
                "rotation_trade_count": rotation_trades,
                "signal_entry_count": int(diagnostics.iloc[0]["signal_entry_count"]) if not diagnostics.empty else 0,
                "signal_exit_count": signal_exits,
                "avg_signal_trade_return_pct": float(diagnostics.iloc[0]["avg_signal_trade_return_pct"]) if not diagnostics.empty else 0.0,
                "risk_adjusted_rank_score": round(score, 2),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["risk_adjusted_rank_score", "annual_return_pct", "max_drawdown_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def run_hybrid_ticker_rule_search(
    prices: pd.DataFrame,
    indicator_frames: dict[str, pd.DataFrame],
    satellite_tickers: list[str],
    signal_history: pd.DataFrame,
    rotation_config: BacktestConfig,
    base_signal_config: HybridSignalConfig,
    rule_sets: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    rules = rule_sets or [
        {"rule_name": "baseline"},
        {"rule_name": "block_URA", "blocked_signal_tickers": ("URA",)},
        {"rule_name": "URA_score75_rr25", "ticker_min_etf_scores": {"URA": 75.0}, "ticker_min_rr_values": {"URA": 2.5}},
        {"rule_name": "URA_score80_rr25", "ticker_min_etf_scores": {"URA": 80.0}, "ticker_min_rr_values": {"URA": 2.5}},
        {
            "rule_name": "URA_score75_theme80_rr25",
            "ticker_min_etf_scores": {"URA": 75.0},
            "ticker_min_theme_scores": {"URA": 80.0},
            "ticker_min_rr_values": {"URA": 2.5},
        },
    ]
    rows: list[dict[str, float | int | str]] = []
    for rule in rules:
        rule_name = str(rule.get("rule_name", "unnamed_rule"))
        cfg = copy_hybrid_signal_config(
            base_signal_config,
            blocked_signal_tickers=tuple(rule.get("blocked_signal_tickers", base_signal_config.blocked_signal_tickers)),
            ticker_min_etf_scores=dict(rule.get("ticker_min_etf_scores", base_signal_config.ticker_min_etf_scores)),
            ticker_min_theme_scores=dict(rule.get("ticker_min_theme_scores", base_signal_config.ticker_min_theme_scores)),
            ticker_min_rr_values=dict(rule.get("ticker_min_rr_values", base_signal_config.ticker_min_rr_values)),
        )
        trades: list[dict[str, object]] = []
        curve, diagnostics = run_hybrid_rotation_signal_backtest(
            prices,
            indicator_frames,
            satellite_tickers,
            signal_history,
            rotation_config,
            cfg,
            trades,
        )
        signal_exits = int(diagnostics.iloc[0]["signal_exit_count"]) if not diagnostics.empty else 0
        rotation_trades = int(diagnostics.iloc[0]["rotation_trade_count"]) if not diagnostics.empty else 0
        summary = summarize_equity_curve(curve, rotation_trades + signal_exits)
        trade_frame = pd.DataFrame(trades)
        ura_trades = trade_frame[trade_frame["ETF"].eq("URA")] if not trade_frame.empty else pd.DataFrame()
        ura_return_sum = float(ura_trades["return_pct"].sum()) if not ura_trades.empty else 0.0
        score = (
            summary["annual_return_pct"]
            + summary["calmar_ratio"] * 10
            + summary["sharpe_ratio"] * 5
            + summary["max_drawdown_pct"] * 0.25
        )
        rows.append(
            {
                "rule_name": rule_name,
                "blocked_signal_tickers": ",".join(cfg.blocked_signal_tickers),
                "ticker_min_etf_scores": str(cfg.ticker_min_etf_scores),
                "ticker_min_theme_scores": str(cfg.ticker_min_theme_scores),
                "ticker_min_rr_values": str(cfg.ticker_min_rr_values),
                **summary,
                "rotation_trade_count": rotation_trades,
                "signal_entry_count": int(diagnostics.iloc[0]["signal_entry_count"]) if not diagnostics.empty else 0,
                "signal_exit_count": signal_exits,
                "avg_signal_trade_return_pct": float(diagnostics.iloc[0]["avg_signal_trade_return_pct"]) if not diagnostics.empty else 0.0,
                "ura_signal_trade_count": int(len(ura_trades)),
                "ura_total_return_pct": round(ura_return_sum, 2),
                "risk_adjusted_rank_score": round(score, 2),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["risk_adjusted_rank_score", "annual_return_pct", "max_drawdown_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def summarize_hybrid_trade_attribution(
    trades: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(
            columns=[
                "ETF",
                "trade_count",
                "win_rate_pct",
                "avg_return_pct",
                "total_return_pct",
                "best_return_pct",
                "worst_return_pct",
            ]
        )
    frame = trades.copy()
    frame["exit_ts"] = pd.to_datetime(frame["exit_date"])
    if start is not None:
        frame = frame[frame["exit_ts"] >= pd.Timestamp(start)]
    if end is not None:
        frame = frame[frame["exit_ts"] <= pd.Timestamp(end)]
    if frame.empty:
        return pd.DataFrame()
    grouped = frame.groupby("ETF")["return_pct"]
    result = pd.DataFrame(
        {
            "trade_count": grouped.count(),
            "win_rate_pct": grouped.apply(lambda returns: round(float((returns > 0).mean() * 100), 2)),
            "avg_return_pct": grouped.mean().round(2),
            "total_return_pct": grouped.sum().round(2),
            "best_return_pct": grouped.max().round(2),
            "worst_return_pct": grouped.min().round(2),
        }
    ).reset_index()
    return result.sort_values(["total_return_pct", "avg_return_pct"], ascending=[True, True]).reset_index(drop=True)
