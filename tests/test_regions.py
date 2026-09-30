import numpy as np

from claimshield.contracts import Signal
from claimshield.regions import stage1

W, H = 400, 300


def loc(value):
    h = np.zeros((H, W), np.float32)
    h[100:200, 250:350] = value
    return Signal("localizer", 0.9, 0.9, "r", {"heatmap": h, "reliability": np.ones_like(h)})


def noise_in_same_place():
    z = np.zeros((H // 32, W // 32), np.float32)
    z[3:6, 8:10] = 9.0
    return Signal("noise_residual", 0.7, 0.35, "r", {"block_z": z, "block_px": 32})


def test_two_signals_make_a_region_with_reason():
    [r] = stage1([loc(0.7), noise_in_same_place()], (W, H))
    assert r.stage == 1 and set(r.signals) == {"localizer", "noise_residual"}
    assert r.reason.startswith("Region A (") and "inpainting" in r.reason


def test_single_weak_signal_is_hidden():
    assert stage1([loc(0.6)], (W, H)) == []


def test_single_strong_signal_is_shown():
    assert len(stage1([loc(0.95)], (W, H))) == 1


def test_no_localizer_no_regions():
    assert stage1([noise_in_same_place()], (W, H)) == []
