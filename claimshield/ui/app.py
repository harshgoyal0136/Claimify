"""Reviewer UI (walking skeleton): upload a photo → cards stream in → score + waterfall."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # `streamlit run` from anywhere

import streamlit as st
from PIL import Image, ImageOps

from claimshield import config
from claimshield.pipeline import score_image

BANDS = config.cfg("thresholds")["bands"]
BAND_COLOR = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red", "UNCERTAIN": "gray"}


def card(s):
    with st.container(border=True):
        if s.score is None:
            state = "not applicable" if not s.applicable else "abstained"
            st.markdown(f":gray[**{s.name}** · {state}]  \n:gray[{s.reason}]")
        else:
            c = "red" if s.score >= BANDS["medium_max"] else \
                "orange" if s.score >= BANDS["low_max"] else "green"
            st.markdown(f":{c}[**{s.name}** · {s.score:.2f}] · confidence {s.confidence:.2f}"
                        f"  \n{s.reason}")


st.set_page_config(page_title="ClaimShield", layout="wide")
st.title("ClaimShield")
up = st.file_uploader("Claim photo", type=["jpg", "jpeg", "png", "heic", "heif", "webp"])

if up:
    left, right = st.columns([2, 3])
    left.image(ImageOps.exif_transpose(Image.open(up)))  # PIL decodes HEIC for the browser
    cards = right.container()

    with tempfile.TemporaryDirectory() as d:  # upload wiped as soon as scoring ends
        p = Path(d) / f"upload{Path(up.name).suffix.lower()}"
        p.write_bytes(up.getvalue())

        def on_card(s):
            with cards:
                card(s)

        res = score_image(str(p), on_card=on_card)

    cs = res.claim
    st.divider()
    st.markdown(f"## :{BAND_COLOR[cs.band]}[{cs.band}] · {cs.overall:.2f}")
    if res.quality_reasons:
        st.warning("Quality gate: " + "; ".join(res.quality_reasons))
    st.table([{"factor": k, "contribution": f"{v:+.3f}"} for k, v in cs.waterfall])
    st.caption(f"first card {res.t_first:.2f} s · composite {res.t_fast:.2f} s")
