"""Reviewer UI: upload a photo → fast cards stream in → score; the deep AE card lands later
and the score + waterfall are redrawn."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # `streamlit run` from anywhere

import streamlit as st
from PIL import Image, ImageOps

from claimshield import config
from claimshield.narrative import llm, template
from claimshield.pipeline import finish, score_document, score_image, warm
from claimshield.signals.documents.fields import person_name

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


def show(res):
    cs = res.claim
    st.markdown(f"## :{BAND_COLOR[cs.band]}[{cs.band}] · {cs.overall:.2f}")
    if cs.pending_deep:
        st.info("Deep scan running… (reconstruction test; the score updates when it lands)")
    if res.quality_reasons:
        st.warning("Quality gate: " + "; ".join(res.quality_reasons))
    for r in cs.regions:
        st.markdown(f"- {r.reason}")
    st.table([{"factor": k, "contribution": f"{v:+.3f}"} for k, v in cs.waterfall])
    deep = f" · deep {res.t_deep:.1f} s" if res.t_deep is not None else ""
    st.caption(f"first card {res.t_first:.2f} s · composite {res.t_fast:.2f} s{deep}")


def narrate(claim, names=()):
    """Template first (instant); swapped for the LLM text only if it lands within 4 s."""
    text, pii = template.build(claim, names)
    box = st.empty()
    box.info(template.fill(text, pii))
    out = llm.result(llm.start(text))  # only placeholder text leaves the process
    if out:
        box.info(template.fill(out, pii))


st.set_page_config(page_title="ClaimShield", layout="wide")
st.title("ClaimShield")
for problem in st.cache_resource(warm)():  # pre-warm once per server, not per upload
    st.warning(f"Model not ready — {problem}")
up = st.file_uploader("Claim photo", type=["jpg", "jpeg", "png", "heic", "heif", "webp"])
doc = st.file_uploader("Claim document (PDF or scan)", type=["pdf", "jpg", "jpeg", "png"])

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

    st.divider()
    score = st.empty()
    with score.container():
        show(res)
    if res.deep is not None:
        res = finish(res)  # fast cards are already on screen; this only waits for the AE card
        with cards:
            card(res.claim.signals[-1])
        with score.container():
            show(res)
    narrate(res.claim)

if doc:
    left, right = st.columns([2, 3])
    cards = right.container()
    with tempfile.TemporaryDirectory() as d:  # wiped as soon as scoring ends
        p = Path(d) / f"upload{Path(doc.name).suffix.lower()}"
        p.write_bytes(doc.getvalue())

        def on_doc_card(s):
            with cards:
                card(s)

        dres = score_document(str(p), on_card=on_doc_card)
    if dres.page is not None:
        left.image(dres.page)
    left.caption(f"type: {dres.doc_type} · text from {'OCR' if dres.from_ocr else 'text layer'}")
    diff = next((s.evidence.get("diff") for s in dres.claim.signals
                 if s.name == "pdf_incremental_update" and s.evidence.get("diff")), None)
    st.divider()
    if diff:
        st.markdown("#### Version diff")
        st.table([{"earlier version": a, "final version": b} for a, b in diff])
    cs = dres.claim
    st.markdown(f"## :{BAND_COLOR[cs.band]}[{cs.band}] · {cs.overall:.2f}")
    st.table([{"factor": k, "contribution": f"{v:+.3f}"} for k, v in cs.waterfall])
    st.caption(f"document scored in {dres.t_total:.1f} s")
    narrate(cs, [n for n in (person_name(dres.text),) if n])
