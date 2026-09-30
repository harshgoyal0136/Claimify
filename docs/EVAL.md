# Evaluation harness (v3)

25 % of the score is accuracy on sample data and judges upload their own images. Numbers
must be honest, reproducible and split the way a sceptical judge would split them.

## Splits (`data/generated/manifest.csv`)
Columns: `path, label (real|fake), family (real|sd15|sdxl|flux|firefly|midjourney|nova|splice|copymove|inpaint|gan), attack, quality (orig|q90|q70|q50|dn512|whatsapp), heldout (0|1), split (train|calib|test|eval_only|wild), seed_path, mask_path`.

- **calib**: `heldout=0, quality=orig` → per-signal sigmoids and composite weights.
- **test-seen**: `heldout=0`, all qualities, seeds disjoint from calib.
- **test-heldout**: `heldout=1` (Flux). Never touched by calibration or head training.
- **eval_only-gan**: ~200 GAN images. Never trains anything. Publishes the AE blind spot.
- **real-wild**: ≈1,700 authentic incl. 200 face crops. FPR only.
- **docs**: clean vs tampered PDFs and scans, by tamper method and doc type.
- **bench**: three worst-case files (see LATENCY.md).

## Metrics
Per signal and composite: AUC, AP, **TPR @ 1 % FPR**, TPR @ 5 % FPR.
FPR on real-wild at HIGH (target ≤ 5 %, report **95 % CI**) and at MEDIUM.
Abstain rate on real-wild and on `dn512` / `q50`.
Localization IoU vs `mask_path` on inpaint/splice rows, reliability-masked, **TruFor vs
fallback**.
Family map: leaf accuracy on seen families; **diffusion-node probability mass on Flux**;
confusion on real face crops (must be ≈ 0).
Documents: document-level P/R; field-level precision of flagged fields; by doc type.
Identity: match accuracy on teammate pairs + public pairs.
Latency: from `reports/latency_latest.md`.

## Published rows (`reports/eval_latest.md`)
Headline (3):
1. Composite AUC / TPR@1%FPR — test-seen vs **test-heldout (Flux)**.
2. Real-wild FPR at HIGH, n ≥ 1,500, 95 % CI.
3. Document tamper P/R.

Supporting:
4. Signal × family heatmap **including the eval-only GAN row** (AE column ≈ 0.5 there;
   composite row shows the other signals cover it).
5. Localizer comparison: TruFor vs fallback IoU.
6. Family map: leaf accuracy (seen) + diffusion-node mass (Flux) + real-face confusion.
7. Signal × quality robustness (orig, q90, q70, q50, dn512, whatsapp).
8. Arena attack × signal (`reports/arena.csv`) with SD1.5 / SDXL / Nova / Flux columns.
9. Latency table (first card, composite, deep; p95).

No gating ablation — there is no gate.

## Rules
- Calibrate on calib only. Any threshold change after seeing organiser samples → re-run
  everything, note it in the report changelog.
- Report held-out and GAN rows as they are.
- Never delete manifest rows to improve a number.
- `--subset 500` must finish on CPU in < 30 min so it can re-run during the event.

## Commands
```
make eval                                   # full run
python scripts/eval.py --subset 500 --signals clip_probe,localizer,c2pa
python scripts/eval.py --dry                # validate manifest only
make bench                                  # latency protocol
```
