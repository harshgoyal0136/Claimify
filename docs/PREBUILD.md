# Pre-hackathon build list (v3)

**First action, before anything below: get a written answer from the organisers on
pre-existing code.** Allowed → Variant A (build all of this). Not allowed → do P0 and P1
(environment verification and data generation are not product code; the PS expects data
generation), write P2–P5 as issue-style notes in `docs/BUILD_NOTES.md`, and use
SCHEDULE_24H.md Variant B. Declare the Poincaré code as prior work even though it is no
longer used.

Each item has a "done when".

## P0 — Verify the world (~4 h)
- [ ] Bedrock bearer token: one `converse` to Claude + one Nova Canvas `INPAINTING` with
      `maskPrompt`. *Done when* `python scripts/smoke_bedrock.py photo.jpg` writes
      `smoke_inpaint.png`.
- [ ] Qwen API with the same prompt. *Done when* `scripts/smoke_qwen.py` passes.
- [ ] TruFor weights obtained; forward pass on CPU; heatmap on `data/samples/spliced.jpg`.
- [ ] **Licence check on MVSS-Net / PSCC-Net / CAT-Net** — read each LICENSE file, record
      verdict in `docs/LICENCES.md`. Pick the fallback localizer or decide on the union
      localizer. *Done when* `docs/LICENCES.md` exists with a decision.
- [ ] SD1.5 VAE loads; encode→decode→LPIPS-2 on CPU at 512 px < 15 s and at 256 px < 3 s.
- [ ] `open_clip` ViT-L/14 loads; features cached by sha256.
- [ ] `c2pa-python` reads a manually generated Firefly JPEG; prints `claim_generator`.
- [ ] `insightface buffalo_l` embeds two faces.
- [ ] **Local SD1.5 inpaint at 384 px on CPU — measure.** If > 60 s → 15 steps or img2img
      strength 0.8. Confirm laptop RAM ≥ 16 GB. Record the number in ENVIRONMENT.md.
- [ ] **Threads vs processes** timing for the fast tier on the demo laptop; winner into
      `configs/runtime.yaml`.
- [ ] `make bench` runs on the three worst-case files; `reports/latency_latest.md` written.
- [ ] Windows Defender exclusions + power plan set on the demo laptop.
- [ ] HPC: login, `salloc`, hello-world SLURM job, `scp` round-trip. Commands recorded in
      `scripts/hpc/README.md`.

## P1 — Dataset (~1.5 days)
- [ ] ~500 authentic seeds: provided set + own photos (cars, dents, house exteriors,
      receipts, printed invoices, an ID-like card, teammate selfies). Keep originals with
      EXIF **and** WhatsApp-passed copies.
- [ ] `scripts/gen/make_prompts.py` → 200 damage-scene prompts.
- [ ] `scripts/hpc/generate.py` (SLURM): SD1.5, SDXL, Flux × {t2i, img2img(seed),
      inpaint(seed, mask)} → ~1,200 images. Masks from `scripts/gen/masks.py`.
- [ ] `scripts/gen/nova_attacks.py`: Nova Canvas inpaint + variation on 150 seeds.
- [ ] 30–50 Firefly and Midjourney images generated manually.
- [ ] **Eval-only GAN set (~200)**: ~100 StyleGAN2 faces + ~100 BigGAN / SG2-ADA car-class
      images. `family=gan, split=eval_only`. **Never used to train any head.**
- [ ] `scripts/gen/recompress.py`: q90/q70/q50 + 512 px downscale for every image.
- [ ] `scripts/gen/splice.py`: splices and copy-moves on 150 seeds.
- [ ] Documents: `scripts/gen/invoices.py` (100 clean PDFs, several vendor templates),
      `scripts/gen/medical.py` (50 clean medical-report PDFs), `scripts/gen/tamper_pdf.py`
      (incremental-update edits, full rewrite in another producer, rasterize→digit-paste→
      re-PDF), plus 30 scanned versions.
- [ ] **Real-wild ≈ 1,700**: 500 own + 300 WhatsApp/screenshot variants + ~700 public
      CC0/permissive diverse (people, indoor, documents, stock-style) + **200 real face
      crops / headshots**. Licence-checked for evaluation use.
- [ ] `data/generated/manifest.csv` complete. Flux tagged `heldout=1`. GAN tagged
      `split=eval_only`. *Done when* `scripts/eval.py --dry` passes.

## P2 — Signals (~1.5 days). One file each under `claimshield/signals/`, returns `Signal`, has a test.
- [ ] `forensics/`: `c2pa.py`, `exif.py`, `jpeg_qtables.py`, `copy_move.py`,
      `noise_residual.py` — each sets `applicable=False` correctly for the wrong file type.
- [ ] `clip_probe.py`: head trained on `heldout=0`; pickled. If held-out Flux AUC < 0.80
      → add `dino_probe.py`, keep the winner.
- [ ] `localizer/base.py` (interface), `localizer/trufor.py`, `localizer/fallback.py`.
      Both produce a heatmap on CPU. Config flag `localizer: trufor|fallback`.
- [ ] `family_map.py`: hierarchical softmax on CLIP features; open-set rule; radial-tree
      JSON export for the UI.
- [ ] `regions.py`: stage 1 from localizer; stage 2 merge with AE patch map.
- [ ] `ae_reconstruction.py`: device-conditional VAE count; calibration sigmoid;
      always-on, confidence cap 0.7; patch error map.
- [ ] `documents/pdf_structure.py` (incl. previous-revision reconstruction + diff),
      `documents/ocr.py`, `documents/doc_type.py`, `documents/templates/{invoice,medical,id}.py`.
- [ ] `identity/face_match.py`.
- [ ] `claim/consistency.py` — exactly three checks.
- [ ] `scoring/composite.py` + `configs/weights.yaml` + `configs/thresholds.yaml`.
- [ ] `narrative/template.py` (primary) + `narrative/llm.py` (background, 4 s swap).

## P3 — Eval harness (~0.5 day)
- [ ] `scripts/eval.py` → `reports/eval_latest.md` with the rows in EVAL.md, including
      the eval-only GAN row and the localizer comparison. Runs on CPU in < 30 min with
      `--subset 500`.
- [ ] Real-wild FPR at HIGH with 95 % CI. Target ≤ 5 %.
- [ ] Family softmax confusion on the 200 real face crops — must be near zero.

## P4 — Arena (~0.5 day)
- [ ] `arena/attacks.py`: `inpaint_nova`, `inpaint_local_sd15`, `recompress_q70`.
      Fallback chain wired: Bedrock → local → pre-generated.
- [ ] `arena/run.py`: attack → re-score → `reports/arena.csv`.
- [ ] Held-out table JSON with SD1.5 / SDXL / Nova / Flux columns.

## P5 — App (~1 day)
- [ ] Streamlit single process; pipeline via ThreadPoolExecutor updating placeholder
      containers; cards stream in emission order; deep-tier card shows "deep scan
      running…" then updates the waterfall.
- [ ] Four tabs per ARCHITECTURE.md. Grey cards for n.a./abstained with reasons.
- [ ] SQLite audit. `make demo` pre-warms all fast-tier models.
- [ ] FastAPI + SSE **only if** everything above is done.

## P6 — Rehearsal (~0.5 day)
- [ ] Three cases: (a) clean, (b) inpainted damage + incrementally-edited invoice +
      matching ID, (c) Firefly photo with C2PA + ID/selfie mismatch.
- [ ] Rehearse DEMO.md 5×: normal, Bedrock-off, **TruFor-off (fallback localizer)**,
      CPU-only, with a judge-style random photo.
- [ ] Record a 3-minute backup video.
- [ ] README with diagram, eval table, latency table, decisions table, how to run.
