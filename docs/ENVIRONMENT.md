# Environment — what we actually have

Read this before touching any model, API or GPU code. Everything here is a hard fact about
the machines available; design around it, not around an ideal setup.

## Machines

### 1. Developer laptop (Windows, PowerShell) — the primary machine
- Runs Claude Code, the backend, the UI and **the whole scoring pipeline on CPU**.
- If it has an NVIDIA GPU, set `CLAIMSHIELD_DEVICE=cuda`; otherwise everything runs on
  CPU and must still be usable (see per-component timings in ARCHITECTURE.md).
- **This is the demo machine.** Nothing on the critical path may depend on a network
  service other than Bedrock. Model weights live on local disk under
  `CLAIMSHIELD_MODELS_DIR`.

### 2. College HPC cluster — batch only
- **Compute nodes have no internet.** The login node does.
- Use for exactly one thing: the pre-hackathon dataset generation batch job (SDXL / SD1.5 /
  Flux fakes, ~1,500 images) and, optionally, CLIP feature extraction for the same set.
- Workflow: download weights on the login node (or laptop) → `scp` to scratch → submit
  one SLURM job → `scp` outputs back. Scripts live in `scripts/hpc/`.
- Optional live tunnel for the demo (nice-to-have, **never** critical path):
  `ssh -J <login-node> <compute-node> -L 8000:localhost:8000` with a FastAPI worker
  on the compute node (`scripts/hpc/worker.py`). Requires an `salloc` session open for the
  whole demo window. If `CLAIMSHIELD_HPC_URL` is set and reachable, the AE reconstruction
  and TruFor calls are offloaded; if not, they run locally. Health-check with a 2 s
  timeout; fail over silently.

### 3. Amazon Bedrock (us-east-1) — API, bearer token auth
Two uses:
1. **Claude Code itself** runs through Bedrock (`CLAUDE_CODE_USE_BEDROCK=1`).
2. **The product** uses Bedrock for:
   - **Amazon Nova Canvas** — `INPAINTING` task with `maskPrompt` or `maskImage`, plus
     `TEXT_IMAGE` and `IMAGE_VARIATION` for the arena's regenerate attack. This is the
     live "fabricate damage on the judge's photo" path. ~3–8 s per image, no GPU.
   - **Claude on Bedrock** — narrative writer (temperature 0) and document field
     extraction into fixed JSON.
   - Stability models on Bedrock as a second inpainting family if enabled in the account.

### 4. Qwen API — fallback LLM
- Used when Bedrock Claude is rate-limited or errors. Same prompt templates, same
  temperature 0. Configure `QWEN_API_KEY` and `QWEN_BASE_URL` (OpenAI-compatible).

### 5. Other
- ComfyUI on the laptop/HPC (existing workflows) — optional backup for attacks if Bedrock
  is unavailable during pre-build. Not used at demo time.

## Environment variables

PowerShell (developer laptop). Set these in the session before launching Claude Code or
the app. **Never commit them.** `.env.example` mirrors this list with empty values.

```powershell
# --- Claude Code via Bedrock ---
$env:AWS_BEARER_TOKEN_BEDROCK = "<token>"
$env:CLAUDE_CODE_USE_BEDROCK  = "1"
$env:AWS_REGION               = "us-east-1"
$env:AWS_DEFAULT_REGION       = "us-east-1"

# --- ClaimShield product ---
$env:CLAIMSHIELD_DEVICE       = "cpu"          # or "cuda"
$env:CLAIMSHIELD_MODELS_DIR   = "C:\claimshield\models"
$env:CLAIMSHIELD_HPC_URL      = ""             # e.g. http://localhost:8000 when tunnel is up
$env:CLAIMSHIELD_LLM_PRIMARY  = "bedrock"      # bedrock | qwen | template
$env:BEDROCK_TEXT_MODEL_ID    = "<claude model id available in the account>"
$env:BEDROCK_IMAGE_MODEL_ID   = "amazon.nova-canvas-v1:0"
$env:QWEN_API_KEY             = "<key>"
$env:QWEN_BASE_URL            = "<openai-compatible base url>"
$env:QWEN_MODEL               = "<model name>"
```

The product uses the same `AWS_BEARER_TOKEN_BEDROCK` bearer token through `boto3`
(`Authorization: Bearer` is picked up automatically by recent boto3 versions when this
variable is set; if the installed boto3 is older, `claimshield/llm/bedrock.py` injects the
header via a botocore event hook — see that file).

## Compute budget (measured targets, per image at 512–1024 px)

| Component | CPU laptop | GPU | Notes |
|---|---|---|---|
| CLIP ViT-L/14 features + probe | 1–2 s | 50–100 ms | cached by sha256 |
| TruFor | 2–4 s | 0.2 s | cap input at 1024 px |
| AE reconstruction (1 VAE, LPIPS-2, 384 px) | 5–8 s | 0.3 s | deep tier, async; 1 VAE CPU / 3 GPU |
| Mini-AE 256 px (fallback localizer) | ~2 s | 0.1 s | fast tier only when localizer=fallback |
| Local SD1.5 inpaint 384 px (arena fallback) | 20–40 s (measure; 15 steps if >60 s) | 2–4 s | needs ≥16 GB RAM |
| C2PA/EXIF/JPEG/ELA/copy-move | 0.5–2 s | — | |
| OCR per page | 1–3 s | — | |
| InsightFace | 100–300 ms | 20 ms | |
| Nova Canvas inpaint | 3–8 s | — | API |
| Narrative LLM | 1–4 s | — | API, 8 s timeout → template |

Fast tier on CPU: first card p95 ≤ 2 s, composite p95 ≤ 8 s (spec in LATENCY.md; measured
with `make bench`, not estimated). Deep tier (AE) is async and never blocks.
Machine hardening before any bench or demo: plugged in, Best performance plan, Defender
exclusions on models dir + repo, no VPN.

## Pre-hackathon batch (HPC, one job)
- ~500 authentic seeds (provided set + own phone photos of cars/property/documents).
- Real-wild eval set ≈1,700 incl. ~700 public CC0 diverse + 200 real face crops (laptop, no GPU).
- Eval-only GAN set ≈200 (StyleGAN2 faces + BigGAN/SG2-ADA cars) — never trains anything.
- ~1,500 fakes: SD1.5, SDXL, Flux (held-out), each: text-to-image of damage scenes,
  img2img of seeds, inpainting of seeds with damage masks. Plus Nova Canvas and (manual)
  Firefly/Midjourney samples generated from the laptop via API/web.
- Recompressed variants of everything at JPEG q90/70/50 and 1024→512 downscale.
- A100: SDXL ~3–5 s/img → 1–2 h total. Outputs: `data/generated/<family>/<attack>/*.jpg`
  with a `manifest.csv` (path, family, attack, seed_path, mask_path, quality).

## Network rules at demo time
- Bedrock: required for live arena + narrative. If down: arena shows pre-generated attacks
  and narrative falls back to template. Demo still runs.
- HPC tunnel: optional.
- Everything else: local.
