# Latency spec and measurement protocol

A judge watching cards stream for 8 s sees a working system. A judge watching a spinner
for 5 s sees a broken one. Perceived latency is the **first card**, not the composite.

## Spec (CPU, demo laptop, no GPU assumed)
| Metric | Target |
|---|---|
| First signal card rendered | p95 ≤ 2.0 s from upload complete |
| Fast-tier composite (all fast cards + score) | p95 ≤ 8.0 s on the worst-case file |
| Deep tier (AE) | never blocks UI; lands ≤ 30 s |
| Cold start | all fast-tier models pre-warmed at launch; app up ≥ 10 min before slot |

## Worst-case files (`data/bench/`)
- `a_12mp.heic` — 4000×3000 HEIC straight from a phone.
- `b_whatsapp.jpg` — WhatsApp-forwarded JPEG, q≈60, 1600 px.
- `c_screenshot.png` — ~200 KB PNG screenshot (no EXIF, no JPEG tables).

## Protocol — `make bench`
- 20 runs per file, warm cache **disabled** for the file itself (fresh sha256 each run,
  models warm), UI open.
- Record per run: t_first_card, t_composite, t_deep, per-signal durations.
- Report **p95** and mean. Write `reports/latency_latest.md`.
- Run once during pre-build on the actual demo laptop, once at hour 0 of the event, and
  after any change to the fast tier. Put the hour-0 numbers on the architecture slide.

## Machine state before every bench and before the demo
- Plugged in; Windows power plan = Best performance.
- Windows Defender exclusion on `CLAIMSHIELD_MODELS_DIR` **and** the repo (Defender
  scans `.pth/.bin/.onnx` on open; this alone can add 10–30 s to model load).
- No VPN; no browser tabs beyond the app; notifications off.
- `CLAIMSHIELD_DEVICE=cpu` unless a local NVIDIA GPU is verified.

## Parallelism
Default: `ThreadPoolExecutor` in one process (torch releases the GIL). During pre-build
run the bench once with threads and once with processes; keep the winner in
`configs/runtime.yaml`. On a 4–6 core laptop, three competing processes are often slower
than sequential.

## Escalations if the spec fails (apply in order, re-bench after each)
1. Localizer input 768 → 512 px.
2. CLIP input 336 → 224 px (default is already 224).
3. Copy-move moves from fast tier to deep tier.
4. HEIC decode starts in its own thread before upload completes.
5. Noise-residual block size doubled.

## Event kill-switch
Fast-tier p95 > 10 s after the hour-3 fixes → apply escalations 1–3 without discussion.
