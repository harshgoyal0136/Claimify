"""Loads configs/*.yaml once. Everything tunable lives there, not in code."""
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def cfg(name: str) -> dict:
    return yaml.safe_load((ROOT / "configs" / f"{name}.yaml").read_text(encoding="utf-8"))


def models_dir() -> Path:
    return Path(os.environ.get("CLAIMSHIELD_MODELS_DIR") or ROOT / "models")


def device() -> str:
    return os.environ.get("CLAIMSHIELD_DEVICE") or cfg("runtime")["device"]
