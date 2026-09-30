"""SD1.5 VAE encode→decode, shared by the fallback localizer (mini-AE, 256 px) and the
deep-tier AE reconstruction signal. Generated / inpainted pixels reconstruct with LOWER
error than camera pixels (AEROBLADE, Ricker et al. CVPR 2024).
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from .. import config


@lru_cache(maxsize=1)
def load():
    from diffusers import AutoencoderKL

    local = config.models_dir() / "vae" / "sd15"
    if local.exists():
        vae = AutoencoderKL.from_pretrained(str(local))
    else:
        c = config.cfg("runtime")["vae"]
        vae = AutoencoderKL.from_pretrained(c["hf_id"], subfolder=c["subfolder"],
                                            cache_dir=str(config.models_dir() / "hf"))
    return vae.to(config.device()).eval()


def reconstruct(rgb, px: int):
    """(x, x_hat) as 1×3×H×W tensors in [-1, 1], long side = px, sides multiple of 8."""
    import torch

    s = px / max(rgb.size)
    W, H = (max(8, round(d * s / 8) * 8) for d in rgb.size)
    x = torch.from_numpy(np.asarray(rgb.resize((W, H)), np.float32) / 127.5 - 1)
    x = x.permute(2, 0, 1)[None].to(config.device())
    vae = load()
    with torch.inference_mode():
        y = vae.decode(vae.encode(x).latent_dist.mode()).sample
    return x, y


def low_error_map(rgb, px: int = 256) -> np.ndarray:
    """H×W map in [0, 1] at rgb size: 1 where reconstruction error is unusually LOW."""
    x, y = reconstruct(rgb, px)
    err = (x - y).abs().mean(1)[0].float().cpu().numpy()
    le = np.log(cv2.GaussianBlur(err, (0, 0), 3) + 1e-4)
    med = np.median(le)
    mad = max(1.4826 * np.median(np.abs(le - med)), 1e-3)
    # ponytail: z=2.5 below median → 0.5; calibrate against inpaint masks (localizer IoU row).
    m = np.clip((med - le) / mad / 5, 0, 1).astype(np.float32)
    return cv2.resize(m, rgb.size)
