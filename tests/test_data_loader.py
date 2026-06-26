from __future__ import annotations

import pandas as pd

from src import data_loader


def _price_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Adj Close": [100.5],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2026-06-26"]),
    )


def test_load_price_data_writes_download_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(data_loader, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(data_loader.yf, "download", lambda *args, **kwargs: _price_frame())

    result = data_loader.load_price_data(["QQQ"], cache_dir="raw", refresh=True)

    assert "QQQ" in result
    status = pd.read_csv(tmp_path / data_loader.DATA_SOURCE_STATUS_PATH)
    assert status.iloc[0]["ticker"] == "QQQ"
    assert status.iloc[0]["source"] == "download"
    assert status.iloc[0]["last_date"] == "2026-06-26"


def test_load_price_data_falls_back_to_cache_on_download_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(data_loader, "PROJECT_ROOT", tmp_path)
    cache_dir = tmp_path / "raw"
    cache_dir.mkdir()
    _price_frame().to_csv(cache_dir / "QQQ_1d.csv")

    def fail_download(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(data_loader.yf, "download", fail_download)

    result = data_loader.load_price_data(["QQQ"], cache_dir="raw", refresh=True)

    assert float(result["QQQ"].iloc[-1]["Close"]) == 100.5
    status = pd.read_csv(tmp_path / data_loader.DATA_SOURCE_STATUS_PATH)
    assert status.iloc[0]["source"] == "fallback_cache"
    assert "network down" in status.iloc[0]["reason"]
