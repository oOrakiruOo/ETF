from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {file_path}")
    return data


def ensure_dir(path: str | Path) -> Path:
    directory = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def setup_logging() -> None:
    log_dir = ensure_dir("logs")
    logging.basicConfig(
        filename=log_dir / "system.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
