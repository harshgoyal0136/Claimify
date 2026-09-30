# ClaimShield — Claude Code project instructions (v3, final approach)

You are building **ClaimShield**, an entry for the Adrosonic Build 24-hour hackathon,
Problem Statement 2: *AI-Powered Synthetic Identity & Deepfake Claim Detection System*.

Read these before doing anything non-trivial, in this order:

1. `docs/FINAL_APPROACH.txt` — the v3 decisions and why. If any other doc disagrees with
   it, FINAL_APPROACH wins.
2. `docs/PROBLEM_STATEMENT.md` — the rubric.
3. `docs/ARCHITECTURE.md` — components, contracts, the two-tier image lane.
4. `docs/ENVIRONMENT.md` — machines, keys, compute. No GPU is assumed at demo time.
5. `docs/LATENCY.md` — the spec and the measurement protocol (`make bench`).
6. `docs/PREBUILD.md`, `docs/SCHEDULE_24H.md` — what gets built when; kill-switches.
7. `docs/EVAL.md` — nothing ships without a number.
8. `docs/DEMO.md` — the 10-minute script and its failure paths.
9. `docs/PAPERS.md` — citations and exactly what each supports.

## One-paragraph pitch

Every other team ships a detector. We ship a detector **and the fraudster**. ClaimShield
scores claim evidence (photos, PDFs, scans, ID + selfie) with three orthogonal image
signals — a CLIP feature probe, a forgery localizer, and a training-free diffusion-
autoencoder reconstruction test — plus PDF structure forensics with a version "time
machine", three claim-level cross-artifact checks, and a hierarchical generator-family
map. A built-in red-team arena fabricates new fakes from real photos and reports
detection on a held-out generator family, so "generalizes to unseen fraud" is a number.

## Non-negotiable rules

- **Win by subtracting.** Six things that work. Do not add components not in
  ARCHITECTURE.md. If you think something is missing, write it in `docs/IDEAS.md` and
  move on.
- **Two-tier image lane.** Fast tier (forensics → CLIP probe → localizer) must meet the
  spec in `docs/LATENCY.md`: first card p95 ≤ 2 s, composite p95 ≤ 8 s on the worst-case
  file, on CPU. Deep tier (AE reconstruction) is async and never blocks the UI.
- **Deterministic scoring.** Composite = documented weighted function in
  `claimshield/scoring/composite.py`, weights in `configs/weights.yaml`. No conditional
  gates. An LLM never produces or adjusts a number.
- **Template narrative is primary.** It renders instantly. The LLM call runs in the
  background and replaces the text only if it returns within 4 s.
- **Every signal returns `Signal`** with `score`, `confidence`, `reason` (one adjuster
  sentence), `evidence`, and the flags `abstained` / `applicable`. "Not applicable" is
  not "abstained". No bare floats.
- **Abstain is a valid output.** Quality gate → `UNCERTAIN` band unless strong
  deterministic evidence (C2PA manifest, PDF version diff) exists.
- **Localizer is an interface** with two tested implementations (TruFor, fallback). A
  config flag switches them. The demo must run end-to-end on the fallback at least once.
- **AE reconstruction is always on** as a supporting signal (weight ≈0.20, confidence
  cap 0.7). There is no GAN gate and no GAN branch in the family tree.
- **Nothing ships without a number.** Any scorer change → `make eval` → regenerate
  `reports/eval_latest.md`. Any latency-affecting change → `make bench`.
- **Cut and stay cut:** hyperbolic head, video (except the optional final beat),
  multi-agent orchestration, shadow/lighting physics checks, Chroma feedback demo beat,
  claim-level checks beyond the three, "world model" wording.
- **PII never goes to the LLM.** Placeholders before the narrative call. Audit log stores
  SHA-256 hashes, not files. Uploads live in a temp dir wiped after scoring.

## Stack

Python 3.11, Streamlit reviewer UI (pipeline runs in-process via ThreadPoolExecutor;
FastAPI only if time allows in Variant A), PyTorch CPU wheels by default, `diffusers` for
the SD VAE, `open_clip` for CLIP ViT-L/14, TruFor + fallback localizer vendored under
`models/`, `insightface` for identity, `pytesseract` + `pikepdf` + `pdfplumber` for
documents, `c2pa-python`, `boto3` for Bedrock, `plotly` for the family map, SQLite audit.

## Working conventions

- Tests in `tests/`, run with `pytest -q`. A signal without a test is not done.
- `make bench` → `reports/latency_latest.md`. `make eval` → `reports/eval_latest.md`.
  `make demo` launches the app with all fast-tier models pre-warmed.
- One forensic check per file under `claimshield/signals/`. Keep functions small.
- Commit prefixes: `signal:`, `doc:`, `ui:`, `arena:`, `eval:`, `infra:`, `bench:`.
- When a step needs something we don't have (a weight file, a key, a licence answer),
  say so and stop. Don't stub silently.

## Environment variables

See `docs/ENVIRONMENT.md`. Never commit values. `.env.example` lists them.
