"""End-to-end without model weights: missing models become grey cards, never a crash."""
import numpy as np
from PIL import Image

from claimshield import pipeline


def test_cards_stream_in_order_and_missing_models_abstain(tmp_path):
    p = tmp_path / "x.jpg"
    Image.fromarray(np.random.default_rng(0).integers(0, 255, (600, 800, 3), np.uint8)).save(p)
    seen = []
    res = pipeline.score_image(str(p), on_card=lambda s: seen.append(s.name))

    order = [fn.__module__.rsplit(".", 1)[-1] for g in ("forensics", "clip_probe", "localizer")
             for fn in pipeline.FAST[g]]
    assert seen == order
    assert res.claim.band in ("LOW", "MEDIUM", "HIGH", "UNCERTAIN")
    assert res.t_first <= res.t_fast
    for s in res.claim.signals:
        assert s.score is not None or s.reason  # grey cards always explain themselves
