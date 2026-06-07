from __future__ import annotations

from src.theme_engine import assess_theme_rotation_risks


def test_assess_theme_rotation_risks_flags_overheated_theme() -> None:
    theme_map = {"AI": ["SMH", "BOTZ"]}
    metrics = {
        "SMH": {
            "return_3m": 0.18,
            "return_6m": 0.30,
            "rs_qqq_3m": 0.02,
            "rs_spy_3m": 0.04,
            "rsi_14": 78.0,
            "drawdown_52w_pct": -2.0,
        },
        "BOTZ": {
            "return_3m": 0.12,
            "return_6m": 0.20,
            "rs_qqq_3m": 0.01,
            "rs_spy_3m": 0.03,
            "rsi_14": 74.0,
            "drawdown_52w_pct": -3.0,
        },
    }
    result = assess_theme_rotation_risks(theme_map, metrics, {"AI": 82.0})
    assert result[0]["リスク区分"] in {"中", "高"}
    assert "過熱" in str(result[0]["主なリスク"])
    assert "追い買い禁止" in str(result[0]["予防策"])


def test_assess_theme_rotation_risks_flags_benchmark_lag() -> None:
    theme_map = {"Energy": ["XLE", "URA"]}
    metrics = {
        "XLE": {
            "return_3m": -0.06,
            "return_6m": -0.10,
            "rs_qqq_3m": -0.08,
            "rs_spy_3m": -0.04,
            "rsi_14": 44.0,
            "drawdown_52w_pct": -18.0,
        },
        "URA": {
            "return_3m": -0.04,
            "return_6m": -0.12,
            "rs_qqq_3m": -0.06,
            "rs_spy_3m": -0.03,
            "rsi_14": 46.0,
            "drawdown_52w_pct": -20.0,
        },
    }
    result = assess_theme_rotation_risks(theme_map, metrics, {"Energy": 58.0})
    assert result[0]["リスク区分"] == "高"
    assert "相対劣後" in str(result[0]["主なリスク"])
    assert "Core優先" in str(result[0]["予防策"])


def test_assess_theme_rotation_risks_flags_missing_data() -> None:
    result = assess_theme_rotation_risks({"Space": ["ARKX"]}, {}, {})
    assert result[0]["リスクスコア"] == 100.0
    assert result[0]["リスク区分"] == "高"
    assert "データ不足" in str(result[0]["主なリスク"])
