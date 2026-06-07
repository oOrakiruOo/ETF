from __future__ import annotations

import pandas as pd

from src.main import (
    apply_relaxed_theme_entry_policy,
    apply_theme_risk_overlay_to_signal_history,
    build_signal_rows_for_metrics,
    run_theme_risk_policy_mode_search,
    summarize_theme_risk_overlay_blocks,
    summarize_theme_risk_overlay_effect,
)


def test_build_signal_rows_includes_theme_rotation_risk_columns() -> None:
    entries = [{"ticker": "XLE", "theme": "エネルギー", "bucket": "satellite"}]
    theme_map = {"themes": {"エネルギー": ["XLE"]}}
    metrics_by_ticker = {
        "XLE": {
            "price": 100.0,
            "ma_21": 98.0,
            "ma_50": 96.0,
            "ma_200": 90.0,
            "ma_50_slope": 0.02,
            "ma_200_slope": 0.01,
            "return_3m": -0.04,
            "return_6m": -0.08,
            "return_12m": 0.05,
            "rs_qqq_3m": -0.08,
            "rs_spy_3m": -0.04,
            "rsi_14": 48.0,
            "drawdown_52w_pct": -8.0,
            "atr_14": 2.0,
            "three_day_return_pct": 0.5,
            "volume_change_pct": 0.0,
        }
    }
    rows = build_signal_rows_for_metrics(entries, theme_map, metrics_by_ticker)
    assert len(rows) == 1
    assert rows[0]["テーマリスク"] == "高"
    assert rows[0]["テーマリスクスコア"] >= 60
    assert "相対劣後" in str(rows[0]["テーマリスク理由"])
    assert "Core優先" in str(rows[0]["テーマ予防策"])


def test_summarize_theme_risk_overlay_effect_compares_signal_counts() -> None:
    baseline = pd.DataFrame(
        [
            {"判定": "買い候補"},
            {"判定": "押し目待ち"},
            {"判定": "見送り"},
        ]
    )
    overlay = pd.DataFrame(
        [
            {"判定": "見送り"},
            {"判定": "押し目待ち"},
            {"判定": "見送り"},
        ]
    )
    baseline_forward = pd.DataFrame(
        [
            {"判定": "買い候補", "20d_return_pct": 5.0},
            {"判定": "押し目待ち", "20d_return_pct": 1.0},
        ]
    )
    overlay_forward = pd.DataFrame([{"判定": "押し目待ち", "20d_return_pct": 1.0}])
    baseline_virtual = pd.DataFrame([{"約定件数": 2, "平均リターン%": 3.0}])
    overlay_virtual = pd.DataFrame([{"約定件数": 1, "平均リターン%": 1.0}])
    result = summarize_theme_risk_overlay_effect(
        baseline,
        overlay,
        baseline_forward,
        overlay_forward,
        baseline_virtual,
        overlay_virtual,
    )
    buy_row = result[result["指標"].eq("買い系シグナル数")].iloc[0]
    assert buy_row["リスク抑制なし"] == 1
    assert buy_row["リスク抑制あり"] == 0
    assert buy_row["差分"] == -1


def test_apply_relaxed_theme_entry_policy_blocks_high_risk_candidate() -> None:
    history = pd.DataFrame(
        [
            {
                "ETF": "XLE",
                "判定": "見送り",
                "ETFスコア": 78.0,
                "テーマスコア": 62.0,
                "RR": 1.4,
                "テーマリスク": "高",
                "テーマリスクスコア": 60.0,
            }
        ]
    )
    baseline = apply_relaxed_theme_entry_policy(history, apply_theme_risk=False)
    overlay = apply_relaxed_theme_entry_policy(history, apply_theme_risk=True)
    assert baseline.iloc[0]["判定"] == "買い候補"
    assert overlay.iloc[0]["判定"] == "見送り"


def test_run_theme_risk_policy_mode_search_returns_modes() -> None:
    history = pd.DataFrame(
        [
            {
                "snapshot": "2024-01-31",
                "ETF": "XLE",
                "判定": "見送り",
                "ETFスコア": 78.0,
                "テーマスコア": 62.0,
                "RR": 1.4,
                "テーマリスク": "高",
                "テーマリスクスコア": 60.0,
            },
            {
                "snapshot": "2024-02-29",
                "ETF": "SMH",
                "判定": "見送り",
                "ETFスコア": 72.0,
                "テーマスコア": 68.0,
                "RR": 1.3,
                "テーマリスク": "中",
                "テーマリスクスコア": 45.0,
            },
        ]
    )
    result = run_theme_risk_policy_mode_search(history)
    assert set(result["mode"]) == {"off", "high_only", "balanced", "strict"}
    strict = result[result["mode"].eq("strict")].iloc[0]
    assert strict["ブロック/弱化件数"] >= 1


def test_apply_theme_risk_overlay_to_signal_history_replays_mode() -> None:
    history = pd.DataFrame(
        [
            {
                "ETF": "XLE",
                "判定": "買い候補",
                "テーマリスク": "中",
                "テーマリスクスコア": 45.0,
            },
            {
                "ETF": "SMH",
                "判定": "買い候補",
                "テーマリスク": "高",
                "テーマリスクスコア": 60.0,
            },
        ]
    )
    high_only = apply_theme_risk_overlay_to_signal_history(history, theme_risk_mode="high_only")
    strict = apply_theme_risk_overlay_to_signal_history(history, theme_risk_mode="strict")
    assert high_only.iloc[0]["判定"] == "買い候補"
    assert high_only.iloc[1]["判定"] == "見送り"
    assert strict.iloc[0]["判定"] == "押し目待ち"


def test_summarize_theme_risk_overlay_blocks_lists_changed_signals() -> None:
    baseline = pd.DataFrame(
        [
            {
                "snapshot": "2024-01-31",
                "ETF": "XLE",
                "テーマ": "エネルギー",
                "判定": "買い候補",
            }
        ]
    )
    overlay = pd.DataFrame(
        [
            {
                "snapshot": "2024-01-31",
                "ETF": "XLE",
                "テーマ": "エネルギー",
                "判定": "見送り",
                "テーマリスク": "高",
                "テーマリスクスコア": 60.0,
                "テーマリスク理由": "QQQ/SPYに相対劣後",
                "テーマ予防策": "補助枠を停止しCore優先へ戻す",
            }
        ]
    )
    result = summarize_theme_risk_overlay_blocks(baseline, overlay)
    assert len(result) == 1
    assert result.iloc[0]["抑制なし判定"] == "買い候補"
    assert result.iloc[0]["抑制あり判定"] == "見送り"
    assert result.iloc[0]["テーマリスク"] == "高"
