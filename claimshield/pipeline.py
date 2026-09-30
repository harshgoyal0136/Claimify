"""Image lane orchestration: preprocess → fast-tier checks in parallel → cards → score.

Cards are emitted in configs/runtime.yaml `card_order` on the calling thread, so a
Streamlit callback can write to the page directly. The deep tier (AE reconstruction) starts
at the same time on its own executor and never blocks the fast cards: score_image returns
with pending_deep=True and finish() folds the AE signal in once it lands.
"""
from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace

from . import config
from .contracts import ClaimScore, Signal
from .preprocess import prepare
from .regions import stage1, stage2
from .scoring.composite import score_claim
from .signals import ae_reconstruction, clip_probe, family_map, localizer
from .signals.forensics import c2pa, copy_move, exif, jpeg_qtables, noise_residual

# card group → checks, emitted in runtime.yaml card_order.
FAST = {
    "forensics": [c2pa.run, exif.run, jpeg_qtables.run, copy_move.run, noise_residual.run],
    "clip_probe": [clip_probe.run, family_map.run],
    "localizer": [localizer.run],
}

_pool = ThreadPoolExecutor(max_workers=config.cfg("runtime")["fast_tier_workers"])
_deep_pool = ThreadPoolExecutor(max_workers=1)  # one AE job at a time; never shares the fast pool


@dataclass
class ImageResult:
    claim: ClaimScore
    sha256: str
    quality_reasons: list[str]
    t_first: float | None
    t_fast: float
    t_deep: float | None = None   # set by finish() when the deep tier lands
    deep: Future | None = None    # pending (Signal, landed_at) AE job; None when done/disabled
    quality_flag: bool = False
    t0: float = 0.0


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
    R = config.cfg("runtime")
    deep = _deep_pool.submit(lambda: (_safe(ae_reconstruction.run, prep), time.perf_counter())
                             ) if R["deep_tier_enabled"] else None
    order = R["card_order"]
    futures = [_pool.submit(_safe, fn, prep) for g in order for fn in FAST.get(g, [])]

    signals, t_first = [], None
    for f in futures:
        s = f.result()
        signals.append(s)
        t_first = t_first if t_first is not None else time.perf_counter() - t0
        if on_card:
            on_card(s)

    claim = score_claim(signals, quality_flag=prep.quality_flag,
                        regions=stage1(signals, prep.rgb.size), pending_deep=deep is not None)
    res = ImageResult(claim, prep.sha256, prep.quality_reasons, t_first,
                      time.perf_counter() - t0, deep=deep, quality_flag=prep.quality_flag, t0=t0)
    return finish(res) if wait_deep else res


def finish(res: ImageResult) -> ImageResult:
    """Block until the deep tier lands, then re-score (waterfall recomputed, regions stage 2)."""
    if res.deep is None:
        return res
    ae, landed = res.deep.result()
    c = res.claim
    claim = score_claim(c.signals + [ae], quality_flag=res.quality_flag,
                        regions=stage2(c.regions, ae))
    return replace(res, claim=claim, t_deep=landed - res.t0, deep=None)


def warm() -> list[str]:
    """Load every model (fast tier + AE) up front (`make demo`). Returns problems, never raises:
    a missing model shows up as a grey card instead of blocking the app."""
    problems = []
    for mod in (clip_probe, family_map, localizer, ae_reconstruction):
        try:
            mod.warm()
        except Exception as e:
            problems.append(f"{mod.__name__.rsplit('.', 1)[-1]}: {e}")
    return problems
