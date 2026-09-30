# 24-hour schedule (v3)

Principle: **working end-to-end by hour 7, undeniable by hour 24.** Floor first (real-photo
FPR, documents, demo path), then arena, identity, regions, family map. Every block ends
with a commit; scorer changes end with `make eval`; fast-tier changes end with `make bench`.

## Variant A — pre-built (P0–P6 done)

| Hour | Block | Done when |
|---|---|---|
| 0–1 | `make bench` on the demo laptop; fix machine state (Defender, power plan); record numbers for the slide. Bedrock smoke. Open the 3 cases. | First card p95 ≤ 2 s, composite p95 ≤ 8 s recorded. |
| 1–3 | **Sample-data pass.** Every organiser image/doc through the pipeline. Fix real-photo false positives FIRST. Re-calibrate thresholds if needed. `make eval`. | FPR on organiser authentic set ≤ 5 %; report updated. |
| 3–5 | **Document hardening** incl. medical template on organiser docs: OCR quirks, schema misses, producer strings. | Every organiser document yields ≥ 1 meaningful reason or a clean "no issues". |
| 5–7 | **UI demo path only**: Images → Documents → Score; streaming order; heatmap slider; diff table; waterfall; grey n.a. cards. Kill anything flaky. | DEMO.md steps 1–3 run without touching a terminal. |
| 7–8 | **CHECKPOINT.** Full DEMO.md rehearsal. Commit `v0.9`. | A judge could be walked through it now. |
| 8–10 | **Arena**: Bedrock live attack + local SD1.5 inpaint fallback, each tested 3×. Held-out table on the Arena tab. | Judge-photo flow works 3× via Bedrock and 1× via local. |
| 10–12 | **Identity lane** in UI; case (c) mismatch + selfie synthetic check. | Case (c) shows the mismatch. |
| 12–13 | Rest / rotate. One person runs a smoke loop. | — |
| 13–15 | **Regions** two-stage polish + **family map** radial tree with the Flux → diffusion-node beat. | Regions list reads cleanly; Flux lands on the diffusion node. |
| 15–17 | Robustness row (q90/70/50, 512 px) + abstain beat (tiny blurry photo → UNCERTAIN) + n.a. card wording pass. | Table matches `reports/eval_latest.md`. |
| 17–19 | **Final eval**: real-wild FPR with CI, held-out row, eval-only GAN row, localizer comparison, latency table. | `reports/eval_latest.md` + `latency_latest.md` final. |
| 19–21 | Code quality: README (diagram, eval + latency tables, decisions), docstrings, `pytest -q` green, `.env.example`. Slides (5 max). Optional video keyframe beat **only if all green**. | Fresh clone + README works. |
| 21–23 | Two rehearsals: Bedrock-off, TruFor-off. Each ≤ 9 min. | Both under time. |
| 23–24 | Freeze. Backup video. Charge. Pre-load cases. Nothing new. | — |

## Variant B — only P0 + P1 pre-built
Not viable at v2 scope for 2 people. Cuts, in order, applied up front:
1. PDF time machine **timeboxed to 3 h** (hours 5–8). Not working by the box → metadata
   story (producer mismatch, ModDate delta, fonts, arithmetic).
2. Single-process Streamlit, no FastAPI/SSE.
3. Arena live attack cut; held-out table computed during the event from pre-generated data.
4. Identity lane in the last 2 hours only.
5. Deep tier cut; mini-AE 256 px is the AE signal.

| Hour | Block |
|---|---|
| 0–1 | Scaffold, `Signal`/`Region`/`ClaimScore`, composite skeleton, weights.yaml, bench harness. |
| 1–3 | Forensics (C2PA, EXIF, JPEG, copy-move, noise residual) + tests. First cards exist. |
| 3–5 | CLIP probe head trained on generated set; localizer (TruFor **and** fallback wired). |
| 5–8 | Documents: PDF structure (3 h box), OCR, invoice + medical templates. |
| 8–10 | Streamlit UI: streaming cards → score tab → template narrative. **Checkpoint: end-to-end.** |
| 10–12 | `scripts/eval.py`; first `eval_latest.md`; real-photo FPR fix pass. |
| 12–13 | Rest. |
| 13–15 | Regions stage 1 + family map + mini-AE signal. |
| 15–17 | Held-out table from pre-generated data; robustness row; abstain band. |
| 17–19 | Three cases; UI polish; `make bench`. |
| 19–21 | README, tests, slides. |
| 21–22 | Identity lane (2 h box). |
| 22–24 | Rehearsals (normal + TruFor-off), backup video, freeze. |

Keep always: localizer + CLIP probe + forensics + document lane + deterministic scorer
+ 3-tab UI + abstain band + honest eval table.

## Kill-switches (pre-committed — apply without discussion)
- Fast-tier p95 > 10 s after hour-3 fixes → localizer 512 px, CLIP 224 px, copy-move to deep.
- Bedrock **and** local inpaint dead → pre-generated attack, one honest sentence, move on.
- Any organiser document type yields zero cards → keyword rule, never a live scorer change.
- Any real-wild face row scores HIGH → raise quality-gate cap on faces, re-run FPR; do
  not touch weights live.
- Any component not in DEMO.md breaks after hour 20 → disable it, don't fix it.

## Cut list (if behind, in order)
1. Video keyframe beat. 2. Family-map animation (keep static tree). 3. Regions stage 2
(keep stage 1). 4. Multiple VAEs (keep one). 5. Medical template (keep invoice).
Never cut: waterfall, abstain band, PDF diff (or its metadata fallback), C2PA, identity
match, eval table, bench numbers.

## Roles
- **Pipeline owner**: signals, scorer, eval, bench.
- **Product owner**: UI, cases, slides, rehearsal timing; owns DEMO.md.
- **Arena/data owner** (3+): attacks, Bedrock, fallbacks, robustness.
- **Floater** (4): documents, README, tests.
