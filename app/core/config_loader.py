from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


def _resolve_paths(config: dict[str, Any]) -> dict[str, Any]:
    cfg = deepcopy(config)
    for section, key in (
        ("model", "path"),
        ("app", "save_dir"),
        ("app", "database_path"),
        ("database", "path"),
    ):
        value = cfg.get(section, {}).get(key)
        if value:
            path = Path(value)
            if not path.is_absolute():
                cfg[section][key] = str((PROJECT_ROOT / path).resolve())
    return cfg


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return _resolve_paths(yaml.safe_load(f) or {})


def export_config(config: dict[str, Any], path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
