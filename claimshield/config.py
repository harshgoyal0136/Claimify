"""Loads configs/*.yaml once. Everything tunable lives there, not in code."""
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def cfg(name: str) -> dict:
    return yaml.safe_load((ROOT / "configs" / f"{name}.yaml").read_text())
