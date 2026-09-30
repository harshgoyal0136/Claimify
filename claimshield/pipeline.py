"""Image lane orchestration: preprocess → fast-tier checks in parallel → cards → score.

Cards are emitted in configs/runtime.yaml `card_order` on the calling thread, so a
Streamlit callback can write to the page directly.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from . import config
from .contracts import ClaimScore, Signal
from .preprocess import prepare
from .scoring.composite import score_claim
from .signals.forensics import exif

# card group → checks. Groups not built yet (clip_probe, localizer) are simply absent.
FAST = {"forensics": [exif.run]}

_pool = ThreadPoolExecutor(max_workers=config.cfg("runtime")["fast_tier_workers"])


@dataclass
class ImageResult:
    claim: ClaimScore
    sha256: str
    quality_reasons: list[str]
    t_first: float | None
    t_fast: float
    t_deep: float | None = None   # None until the deep tier exists (Phase 5)


def _safe(fn, prep) -> Signal:
    try:
        return fn(prep)
    except Exception as e:  # one broken check must not take the demo down
        name = fn.__module__.rsplit(".", 1)[-1]
        return Signal(name, None, 0.0, f"Check could not run ({type(e).__name__}); "
                      "left out of the score.", {"error": str(e)}, abstained=True)


def score_image(path: str, on_card=None, wait_deep: bool = False) -> ImageResult:
    t0 = time.perf_counter()
    prep = prepare(path)
    order = config.cfg("runtime")["card_order"]
    futures = [_pool.submit(_safe, fn, prep) for g in order for fn in FAST.get(g, [])]

    signals, t_first = [], None
    for f in futures:
        s = f.result()
        signals.append(s)
        t_first = t_first if t_first is not None else time.perf_counter() - t0
        if on_card:
            on_card(s)

    claim = score_claim(signals, quality_flag=prep.quality_flag)
    return ImageResult(claim, prep.sha256, prep.quality_reasons, t_first,
                       time.perf_counter() - t0)
