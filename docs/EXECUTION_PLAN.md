# Execution plan (phase-wise)

Derived from FINAL_APPROACH (wins on conflict), PREBUILD, SCHEDULE_24H, LATENCY, EVAL, DEMO.
This file adds ordering, gates and repo state. It adds no components.

**Repo state at plan time:** docs + configs + `scripts/bench.py` + `scripts/smoke_bedrock.py`
+ `scripts/hpc/generate.sbatch`. No `claimshield/` package, no tests, no data, no git.

**Ordering principle:** long-lead items first (organiser ruling, licences, weights, HPC queue),
then a *walking skeleton* that makes `make bench` and the UI run end-to-end on a trivial
pipeline, then widen signal by signal, each one landing with a test, a bench and a card in the UI.

---

## Phase 0: Gate and repo hygiene (day 0, ~2 h)

| # | Task | Done when |
|---|---|---|
| 0.1 | Get a **written** organiser ruling on pre-existing code. Allowed = Variant A; not allowed = Variant B. Declare Poincaré code as prior work either way. | Email/screenshot saved; variant recorded at the top of this file. |
| 0.2 | `git init`, `.gitignore` (`models/`, `data/`, `.env`, `*.bench.*`, `__pycache__`). | First commit `infra: scaffold`. |
| 0.3 | Fix `requirements.txt`: replace per-line `--index-url` with a top `--extra-index-url https://download.pytorch.org/whl/cpu`; **remove `geoopt`, `chromadb`** (cut features); move `fastapi/uvicorn/sse-starlette` to an optional section. | `pip install -r requirements.txt` succeeds on a clean 3.11 venv on the demo laptop. |
| 0.4 | System deps on Windows: Tesseract, Poppler (pdf2image), MSVC build tools (insightface), GNU make (`choco install make`) or document the raw commands. | `tesseract --version`, `pdftoppm -v`, `make -v` all work. |
| 0.5 | Remove the "Hyperbolic head" row from ENVIRONMENT.md compute table. | `grep -ri hyperbolic docs/ENVIRONMENT.md` empty. |

**Gate 0:** variant known, env installs clean.

---

## Phase 1: Verify the world (P0) + kick off long-lead items (~4 h + background)

Start the slow external things first, then verify locally while they run.

| # | Task | Done when |
|---|---|---|
| 1.1 | **Long-lead:** licence check MVSS-Net / PSCC-Net / CAT-Net → `docs/LICENCES.md` with fallback decision (permissive model or union localizer). | File exists with a decision. |
| 1.2 | **Long-lead:** HPC login, `salloc`, hello-world SLURM, `scp` round-trip; download SD1.5/SDXL/Flux/VAEs/CLIP/TruFor weights to `$SCRATCH` from login node. | Commands in `scripts/hpc/README.md`; weights on scratch. |
| 1.3 | Bedrock: `python scripts/smoke_bedrock.py photo.jpg`. | `smoke_inpaint.png` written. |
| 1.4 | Write `scripts/smoke_qwen.py` (same prompt, OpenAI-compatible). | Passes. |
| 1.5 | Local model smoke on CPU: TruFor heatmap; SD1.5 VAE encode→decode→LPIPS-2 (512 px < 15 s, 256 px < 3 s); open_clip ViT-L/14; c2pa on a Firefly JPEG; insightface two faces. | Each prints output; timings written into ENVIRONMENT.md. |
| 1.6 | Local SD1.5 inpaint 384 px CPU timing; confirm RAM ≥ 16 GB. | Number in ENVIRONMENT.md (15 steps / img2img 0.8 if > 60 s). |
| 1.7 | Demo laptop hardening: Defender exclusions (models dir + repo), Best performance plan. | Done once, checklist ticked. |

**Gate 1:** Bedrock + all five local models run on CPU; licence decision made. Anything
missing (weights, key, licence) → stop and record it, don't stub.

---

## Phase 2: Dataset (P1), runs in background, parallel with Phases 3–4 (~1.5 days)

Owner: arena/data. The HPC job is the critical-path item; submit it as early as possible.

| # | Task | Done when |
|---|---|---|
| 2.1 | ~500 authentic seeds (originals with EXIF **and** WhatsApp copies). | `data/seeds/` populated. |
| 2.2 | `scripts/gen/make_prompts.py` (200 prompts), `scripts/gen/masks.py`. | Prompts + masks exist. |
| 2.3 | `scripts/hpc/generate.py` + submit sbatch: SD1.5/SDXL/Flux × t2i/img2img/inpaint (~1,200). | Outputs pulled to `data/generated/`. |
| 2.4 | `scripts/gen/nova_attacks.py` (150 seeds); 30–50 manual Firefly + Midjourney. | Files + manifest rows. |
| 2.5 | Eval-only GAN set ~200 (`family=gan, split=eval_only`). | Rows tagged; never in train. |
| 2.6 | `splice.py` (150), `recompress.py` (q90/70/50, dn512). | Variants exist. |
| 2.7 | Docs: `invoices.py` (100), `medical.py` (50), `tamper_pdf.py` (incremental update, producer rewrite, digit paste), 30 scans. | Clean + tampered PDFs with labels. |
| 2.8 | Real-wild ≈1,700 incl. 200 face crops, licence-checked. | Rows with `split=wild`. |
| 2.9 | `data/bench/` three worst-case files (12 MP HEIC, WhatsApp JPEG, PNG screenshot). | Files present. |
| 2.10 | `manifest.csv` complete; Flux `heldout=1`. | `python scripts/eval.py --dry` passes (dry mode written here). |

**Gate 2:** `eval.py --dry` green. Blocks Phase 4's CLIP head training and all of Phase 8.

---

## Phase 3: Walking skeleton (~0.5 day), the most important phase

Goal: the whole shape runs end-to-end on CPU before any real model is added.

| # | Task | Done when |
|---|---|---|
| 3.1 | `claimshield/contracts.py`: `Signal`, `Region`, `ClaimScore` exactly as ARCHITECTURE.md. | Imported everywhere; no bare floats. |
| 3.2 | `claimshield/preprocess.py`: HEIC/WebP/PNG/JPEG → RGB, long side ≤ 1024, quality gate from `thresholds.yaml`, sha256 cache. | Test: tiny/blurry image sets `quality_flag`. |
| 3.3 | One real signal: `signals/forensics/exif.py`, with `applicable=False` on PNG. | Test passes. |
| 3.4 | `scoring/composite.py`: per-lane weighted mean (weights × confidence, skip n.a./abstained), `0.5*max + 0.5*mean + claim_bonus`, bands, UNCERTAIN rule, waterfall. | Tests: band edges, UNCERTAIN with/without strong evidence, n.a. excluded. |
| 3.5 | `claimshield/pipeline.py`: `score_image(path, on_card, wait_deep)` with ThreadPoolExecutor, card order from `runtime.yaml`, returns `t_fast`/`t_deep`. | `bench.py` imports and runs. |
| 3.6 | `ui/app.py`: upload → cards stream into placeholders → score. Grey cards for n.a./abstained. Uploads in temp dir, wiped after scoring. | Upload a photo, see a card and a band. |
| 3.7 | `make bench` on the three files. (bench clears the sha256 caches between runs; no nonce bytes, see ISSUES #16.) | `reports/latency_latest.md` written. |

**Gate 3:** `pytest -q` green, `make bench` report exists, UI runs. Commit `v0.1`.

---

## Phase 4: Image lane, fast tier (P2 part 1, ~1 day)

Rule: every signal = one file + one test + re-run `make bench`. Emission order forensics → CLIP → localizer.

| # | Task | Done when |
|---|---|---|
| 4.1 | Forensics: `c2pa.py` (verify signature; absence neutral), `jpeg_qtables.py` (n.a. on PNG/HEIC), `copy_move.py` (SIFT+RANSAC, draws pairs), `noise_residual.py`. | Each has a test incl. wrong-file-type n.a. |
| 4.2 | `clip_probe.py`: 224 px, logistic head trained on `heldout=0`, pickled, features cached. **Rule:** held-out Flux AUC < 0.80 → `dino_probe.py`, keep winner. | Held-out AUC recorded. |
| 4.3 | `localizer/base.py` (Protocol), `trufor.py` (768 px), `fallback.py` (per 1.1: permissive model or mini-AE 256 px ∪ noise-residual). Config flag `localizer.impl`. | Both produce heatmaps on CPU; test covers both. |
| 4.4 | `family_map.py`: hierarchical softmax on CLIP feats, tree per FINAL_APPROACH §1 (no GAN leaf), open-set < 0.60, sunburst JSON. | Flux mass lands on diffusion node. |
| 4.5 | `regions.py` stage 1: reliability-masked heatmap → components → boxes ≥ 0.5 % → per-box reason; hide single-weak-signal boxes. | Region reason strings on an inpaint sample. |
| 4.6 | `make bench`. Apply LATENCY.md escalations in order if over spec. Threads vs processes → `runtime.yaml`. | First card p95 ≤ 2 s, composite p95 ≤ 8 s. |

**Gate 4:** spec met on the demo laptop with both localizer impls. Commit `v0.3`.

---

## Phase 5: Image lane, deep tier (P2 part 2, ~0.5 day)

| # | Task | Done when |
|---|---|---|
| 5.1 | `ae_reconstruction.py`: SD1.5 VAE (3 VAEs if GPU, min-over-AEs), LPIPS-2, 384 px CPU, calibration sigmoid, always-on, confidence cap 0.7, fixed card text, patch error map. | Test: cap enforced; card text exact. |
| 5.2 | Async wiring: `pending_deep=True` → deep card "deep scan running…" → lands, waterfall recomputed. | Deep lands ≤ 30 s, never blocks fast cards. |
| 5.3 | Regions stage 2: re-score boxes with AE patch evidence. | Boxes gain `stage=2` on inpaint sample. |

**Gate 5:** bench still in spec with deep tier running concurrently.

---

## Phase 6: Document lane (P2 part 3, ~1 day; **3 h box on the diff in Variant B**)

| # | Task | Done when |
|---|---|---|
| 6.1 | `documents/pdf_structure.py`: xref count → truncate at earlier `startxref` → re-parse → text diff (version diff table); producer/creator mismatch; Creation/ModDate delta; rogue fonts on digits. | Test on `tamper_pdf.py` outputs: diff rows found. |
| 6.2 | `documents/ocr.py`: 200 dpi, `--psm 6`, per-word confidence, digit dips. | Test on a scan. |
| 6.3 | `documents/doc_type.py`: keyword rules first. | invoice/medical/ID/other on generated set. |
| 6.4 | `templates/invoice.py`, `medical.py`, `id.py`: arithmetic, tax set, date order, formats, ICD-10. All checks in code; LLM only extracts to fixed JSON if ambiguous. | Tests per template. |
| 6.5 | D3 scan path: fast tier on the scan image. | Scanned tamper flagged. |

**Gate 6:** doc P/R measurable on the generated doc set.

---

## Phase 7: Identity, claim checks, narrative (~0.5 day)

| # | Task | Done when |
|---|---|---|
| 7.1 | `identity/face_match.py`: buffalo_l, ArcFace cosine, threshold from yaml; selfie through fast tier. | Test on teammate pair (match) + mismatch pair. |
| 7.2 | `claim/consistency.py`: exactly three checks (invoice < photo date, camera model mismatch, RapidFuzz name < 85). | One test per check. |
| 7.3 | `narrative/template.py` (instant, from waterfall + reasons, PII placeholders). | Deterministic output test. |
| 7.4 | `narrative/llm.py`: Bedrock → Qwen, temp 0, background, swap only if ≤ 4 s. PII scrubbed before call. | Test: timeout → template kept; no PII in payload. |

---

## Phase 8: Eval harness + calibration (P3, ~0.5 day)

| # | Task | Done when |
|---|---|---|
| 8.1 | `scripts/eval.py`: all 9 published rows from EVAL.md incl. eval-only GAN row, TruFor vs fallback IoU, robustness row. `--subset 500` < 30 min CPU. | `reports/eval_latest.md` generated. |
| 8.2 | Calibrate sigmoids + weights on `calib` only; report on test/heldout. | Changelog note in report. |
| 8.3 | Real-wild FPR at HIGH with 95 % CI; face-crop family confusion ≈ 0. | FPR ≤ 5 %. If a face row is HIGH → raise quality-gate cap, re-run; don't touch weights. |

**Gate 8:** headline rows exist and are honest. From here on, any scorer change → `make eval`.

---

## Phase 9: Arena (P4, ~0.5 day; live attack cut in Variant B)

| # | Task | Done when |
|---|---|---|
| 9.1 | `arena/attacks.py`: `inpaint_nova`, `inpaint_local_sd15`, `recompress_q70`; chain Bedrock → local → pre-generated. | Each path tested with network on and off. |
| 9.2 | `arena/run.py` → `reports/arena.csv`; held-out table JSON (SD1.5/SDXL/Nova/Flux). | Table renders. |

---

## Phase 10: App completion (P5, ~1 day)

| # | Task | Done when |
|---|---|---|
| 10.1 | Four tabs: Images (heatmap slider, AE map, regions, family sunburst), Documents (OCR boxes, diff table, metadata), Score (gauge, waterfall, narrative, accept/reject/escalate), Arena. | DEMO.md steps 1–3 without a terminal. |
| 10.2 | SQLite audit (hashes only). Inbox with 3 cases and band chips. | Audit row per action. |
| 10.3 | `make demo` pre-warms all fast-tier models before the UI accepts uploads. | First upload after launch meets bench numbers. |
| 10.4 | FastAPI + SSE **only if** everything above is done (Variant A). | Otherwise skipped, which is fine. |

---

## Phase 11: Rehearse and freeze pre-event (P6, ~0.5 day)

| # | Task | Done when |
|---|---|---|
| 11.1 | Build cases (a) clean, (b) inpaint + incremental invoice + matching ID, (c) Firefly C2PA + ID/selfie mismatch. | All three load from inbox. |
| 11.2 | Rehearse DEMO.md 5×: normal, Bedrock-off, **TruFor-off**, CPU-only, random judge-style photo. | Each ≤ 9 min, logged. |
| 11.3 | README (diagram, eval + latency + decisions tables, run steps); `pytest -q` green; backup 3-min video. | Fresh clone + README works. |

**Gate 11 = pre-build complete.** Everything after this is SCHEDULE_24H.

---

## Phase 12: Event day

Follow `SCHEDULE_24H.md` exactly: Variant A if Gate 0 said allowed, else Variant B (which
compresses Phases 3–11 into the 24 h with its cuts applied up front). Kill-switches and the cut
list there are pre-committed; apply without discussion.

---

## Parallel tracks and critical path

```
Data owner:      P1(1.1,1.2) ─► P2 (HPC job) ─────────────────► P9 Arena
Pipeline owner:  P0 ─► P1 ─► P3 skeleton ─► P4 ─► P5 ─► P8 Eval ─┐
Floater:                      P6 Documents ─► P7 ─────────────────┤
Product owner:                P3.6 UI ──────────► P10 App ───────┴► P11 Rehearse
```
Critical path: **organiser ruling → HPC generation → CLIP head (4.2) → eval (8) → rehearsal.**
The skeleton (Phase 3) unblocks everyone else; don't let it slip past day 1.

## Top risks

| Risk | Mitigation |
|---|---|
| No written ruling before the event | Default to Variant B planning; pre-build only P0/P1. |
| TruFor weights/licence unavailable | Fallback localizer is a first-class impl (4.3), rehearsed in 11.2. |
| insightface/Tesseract/Poppler install pain on Windows | Done in 0.4, day 0, not day 5. |
| HPC queue delays | Submit in Phase 1; Nova + manual Firefly give a minimum viable fake set. |
| Held-out Flux AUC < 0.80 | Pre-committed DINOv2 swap (4.2). |
| CPU bench over spec | LATENCY.md escalations in order; kill-switch at 10 s. |
