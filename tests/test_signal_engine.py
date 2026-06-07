from __future__ import annotations

from src.signal_engine import apply_theme_risk_overlay


def test_theme_risk_overlay_blocks_high_risk_buy_signal() -> None:
    assert apply_theme_risk_overlay("買い候補", "高", 60.0) == "見送り"
    assert apply_theme_risk_overlay("押し目待ち", "高", 60.0) == "見送り"


def test_theme_risk_overlay_softens_medium_risk_buy_signal() -> None:
    assert apply_theme_risk_overlay("強気買い候補", "中", 30.0) == "買い候補"
    assert apply_theme_risk_overlay("買い候補", "中", 45.0) == "押し目待ち"


def test_theme_risk_overlay_high_only_keeps_medium_risk_signal() -> None:
    assert apply_theme_risk_overlay("買い候補", "中", 60.0, mode="high_only") == "買い候補"


def test_theme_risk_overlay_strict_blocks_medium_risk_watch_signal() -> None:
    assert apply_theme_risk_overlay("押し目待ち", "中", 45.0, mode="strict") == "見送り"
    assert apply_theme_risk_overlay("買い候補", "中", 45.0, mode="strict") == "押し目待ち"


def test_theme_risk_overlay_keeps_low_risk_signal() -> None:
    assert apply_theme_risk_overlay("買い候補", "低", 0.0) == "買い候補"
