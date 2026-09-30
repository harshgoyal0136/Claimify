# ClaimShield runbook: install, download, run

Everything needed to go from a fresh clone to a rehearsed demo, in order. Where a step has a
number in brackets, e.g. (#53), that item in `docs/ISSUES.txt` explains the risk.

## 0. What runs where

| Machine | Used for | Never used for |
|---|---|---|
| **Code laptop** (the one without enough RAM/disk) | editing code, pure-logic tests | pip install, model downloads |
| **Demo laptop** (teammate's, ≥ 16 GB RAM, ≥ 30 GB free) | install, models, tests, eval, arena, bench, demo | image generation at scale |
| **HPC** (GPU, SLURM) | generating ~1,200 SD1.5 / SDXL / Flux fakes | anything at demo time |
| **Bedrock** (cloud) | narrative LLM, Nova Canvas attacks | scoring (never) |

Status when this was written: everything is code-complete but **nothing has been run with
real models**. Expect first-run fixes. Log each one in `docs/ISSUES.txt`.

---

## 1. Demo laptop setup (≈ 1–2 h, mostly downloads)

### 1.1 Prerequisites
- Windows 10/11, admin rights for winget, ≥ 16 GB RAM, ≥ 30 GB free disk, internet.
- Clone the repo and open **PowerShell in the repo root**.

### 1.2 One command
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup\setup_windows.ps1
```
In order, it:
1. installs Python 3.11, Git, Tesseract, Poppler, make, and the MSVC C++ Build Tools (≈ 7 GB, for insightface) via winget;
2. puts Tesseract on PATH (#5);
3. creates `.venv` and runs `pip install -r requirements.txt`;
4. downloads every model (§ 2) and prints a check table;
5. runs `pytest -q`.

If it stops after installing Python or the build tools, **open a new terminal** so PATH
reloads, then run the script again. It is safe to re-run.

Flags: `-SkipSystem`, `-SkipBuildTools`, `-SkipModels`, `-SkipArena` (skips the 4 GB local
inpainting model).

Doing it by hand instead:
```powershell
winget install -e --id Python.Python.3.11
winget install -e --id UB-Mannheim.TesseractOCR      # then add C:\Program Files\Tesseract-OCR to PATH
winget install -e --id oschwartz10612.Poppler        # pdftoppm must be on PATH
winget install -e --id ezwinports.make
winget install -e --id Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\setup\download_models.py
pytest -q
```
If a winget ID fails, find the right one with `winget search tesseract` (etc.).

### 1.3 Environment variables
Set these in every new PowerShell before running the app, or persist them with `setx NAME value`.
**Never commit the values.**
```powershell
.\.venv\Scripts\Activate.ps1
$env:AWS_BEARER_TOKEN_BEDROCK = "<token>"
$env:AWS_REGION               = "us-east-1"
$env:BEDROCK_TEXT_MODEL_ID    = "<claude model id enabled in the account>"
$env:BEDROCK_IMAGE_MODEL_ID   = "amazon.nova-canvas-v1:0"
$env:CLAIMSHIELD_LLM_PRIMARY  = "bedrock"          # bedrock | qwen | template
$env:QWEN_API_KEY = "<key>"; $env:QWEN_BASE_URL = "<url>"; $env:QWEN_MODEL = "<model>"   # optional fallback
$env:CLAIMSHIELD_DEVICE       = "cpu"
$env:HF_HUB_OFFLINE           = "1"                # after § 2 has finished — no network surprises
```
Without Bedrock variables the app still runs: the narrative uses the template, and the arena
falls back to local inpainting.

### 1.4 Verify
```powershell
python scripts\setup\download_models.py        # re-run = instant; prints OK/FAIL per model + tools
pytest -q                                      # everything, incl. the cv2/model tests
python scripts\smoke_bedrock.py some_photo.jpg # Bedrock text + Nova inpaint → smoke_inpaint.png
make demo                                      # opens the app in the browser
```
`pytest -q` is the first real run of Phases 3–10. Fix failures before going further.

---

## 2. Models (downloaded by `scripts/setup/download_models.py`)

| Model | Size | Lands in | Used by |
|---|---|---|---|
| CLIP ViT-L/14 (open_clip, openai) | 1.7 GB | `models/clip/` | CLIP probe, family map |
| SD1.5 VAE | 0.3 GB | `models/hf/` | AE reconstruction, fallback localizer |
| LPIPS VGG16 | 0.6 GB | torch hub cache | AE reconstruction (#64) |
| InsightFace buffalo_l | 0.3 GB | `models/insightface/` | face match (#87) |
| TruFor code + weights | 0.3 GB | `models/trufor/` | localizer (research licence; #31) |
| SD1.5 inpainting | ~4 GB | `models/hf/` | arena, when Bedrock is down |
| SDXL + Flux VAEs (`--gpu` only) | 0.5 GB | `models/hf/` | AE on GPU machines |

**Not downloaded, trained:** `models/heads/clip_probe.pkl` and `family_map.pkl` come from
`make heads` (§ 7), after the dataset exists. Until then those two cards are grey.

**If TruFor fails** (the URL or the repo layout may have changed, #31): switch to the
fallback localizer in `configs/thresholds.yaml` with `localizer: {impl: fallback, …}`. The
demo must run end-to-end on the fallback at least once anyway.

---

## 3. Benchmark and demo

1. Put the three worst-case files in `data/bench/`: `a_12mp.heic` (straight from a phone),
   `b_whatsapp.jpg` (a WhatsApp-forwarded photo), `c_screenshot.png`.
2. Machine state: plugged in, power plan *Best performance*, and Windows Defender exclusions
   on the repo and the `models` folder.
3. `make bench` writes `reports/latency_latest.md`. Target: first card p95 ≤ 2 s,
   composite ≤ 8 s. If it misses, apply the escalations in `docs/LATENCY.md`, in order.
   Try `fast_tier_workers` (#39) first.
4. `make demo`. Open the app once before presenting; that first load warms the models (#111).

---

## 4. Dataset: what people must collect (no script can)

| Folder | What | How many |
|---|---|---|
| `data/seeds/` | own photos: cars, dents, house exteriors, receipts, printed invoices, an ID-like card, teammate selfies. **Originals with EXIF.** | ~500 |
| `data/seeds/whatsapp/` | the same photos sent through WhatsApp and saved back, **same file names** | as many as possible |
| `data/wild/` | public CC0/permissive photos (people, indoor, documents, stock); licence-checked | ~1,500 |
| `data/wild/faces/` | real face crops / headshots | ~200 |
| `data/gan/` | StyleGAN2 faces + BigGAN / SG2-ADA car images, **eval only** | ~200 |
| `data/manual/firefly/`, `data/manual/midjourney/` | made by hand on the web (keep the Firefly C2PA) | 30–50 |
| `data/bench/` | the three files in § 3 | 3 |

Then, on the demo laptop:
```powershell
python scripts\gen\make_prompts.py     # data/prompts/: 200 prompts + inpaint phrases
python scripts\gen\masks.py            # data/masks/: one damage mask per seed
```

---

## 5. HPC: generate the SD1.5 / SDXL / Flux fakes

The helper `scripts/hpc/hpc.sh` runs in **Git Bash** on the laptop that has SSH access.
It needs `data/seeds`, `data/masks` and `data/prompts` (§ 4), so copy those over if they
were made on another machine.

### 5.1 One-time SSH key login (the scripts cannot type passwords or OTPs)
```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub | ssh <user>@<login-host> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
ssh -o BatchMode=yes <user>@<login-host> hostname      # must print without asking anything
```
If the cluster forces 2FA on every login, add this to `~/.ssh/config` and log in once by
hand; later connections reuse that session:
```
Host <login-host>
  ControlMaster auto
  ControlPath ~/.ssh/cm-%r@%h-%p
  ControlPersist 8h
```

### 5.2 Every session
```bash
export HPC=<user>@<login-host>
export PART=<gpu-partition>          # from `hpc.sh check` → sinfo (the column with gpu)
```

### 5.3 The steps
| Step | Command | What happens |
|---|---|---|
| Phase 1.2 check | `bash scripts/hpc/hpc.sh check` | hostname + `$SCRATCH`, `sinfo`, a 5-minute hello-world GPU job, scp round trip |
| Upload | `bash scripts/hpc/hpc.sh push` | `scripts/`, seeds, masks, prompts → `$SCRATCH/claimshield` |
| Install + weights | `bash scripts/hpc/hpc.sh setup` | on the **login node**: `.venv` + ~57 GB of weights into `$SCRATCH/models/hf` (fp16 only) |
| Submit | `bash scripts/hpc/hpc.sh submit` | `sbatch -p $PART scripts/hpc/generate.sbatch` (3 h, 1 GPU, 32 GB) |
| Watch | `bash scripts/hpc/hpc.sh status` | `squeue` + the last lines of the newest logs |
| Download | `bash scripts/hpc/hpc.sh pull` | `data/generated/{sd15,sdxl,flux}/` → laptop |

The job writes 134 images per model per attack (t2i, img2img, inpaint), ≈ 1,206 in total.
If it hits the time limit, just `submit` again: finished images are skipped. Pulling while
the job still runs is fine too; pull again at the end.

### 5.4 Things that differ per cluster
- **`$SCRATCH` not set:** `export SCRATCH=/path/to/scratch` in `~/.bashrc` on the HPC.
- **Python module:** `setup_hpc.sh` tries `module load python/3.11`. Change the name if
  `module avail python` shows another.
- **CUDA version:** run `nvidia-smi` in the hello-world log, then set
  `export CUDA_WHL=cu118` (or `cu121` / `cu124`) before `setup`.
- **Gated model** (Flux may need accepting on huggingface.co, #53): log in once on the HPC
  with `ssh $HPC` → `source $SCRATCH/claimshield/.venv/bin/activate` → `huggingface-cli login`,
  then re-run `setup`.
- **Job limits:** edit `--time`, `--mem` and `--gres` at the top of `scripts/hpc/generate.sbatch`.
- **Line endings:** `.sbatch` and `.sh` files are kept LF by `.gitattributes`. If bash on the
  HPC complains about `$'\r'`, run `dos2unix scripts/hpc/*`.

The optional live GPU worker for the demo is described in `scripts/hpc/README.md`. It is never on the critical path.

---

## 6. Build the rest of the dataset (demo laptop, CPU)
```powershell
python scripts\gen\splice.py           # 150 splices + 150 copy-moves with masks
python scripts\gen\nova_attacks.py --n 1   # CHECK the output first (mask convention, #54)
python scripts\gen\nova_attacks.py     # 150 seeds × (inpaint + variation) ≈ 300 Nova images (costs money)
python scripts\gen\invoices.py; python scripts\gen\medical.py
python scripts\gen\tamper_pdf.py       # tampered PDFs + 30 scans + data/docs/manifest.csv (needs Poppler)
python scripts\gen\manifest.py         # merge everything, assign splits
python scripts\gen\recompress.py       # q90 / q70 / q50 / dn512 of every image
python scripts\gen\manifest.py         # again, to include the variants
python scripts\eval.py --dry           # GATE 2: must print DRY OK
```

## 7. Train the heads
```powershell
make heads          # python scripts/train_heads.py → models/heads/*.pkl, prints held-out Flux AUC
```
If the held-out Flux AUC is **below 0.80**, the pre-committed rule applies: add a DINOv2 head (ARCHITECTURE I2).

## 8. Evaluate and calibrate
```powershell
make calibrate      # first time: fits sigmoids on calib → configs/calibration.yaml, then the report
make eval           # afterwards: reports/eval_latest.md + reports/heldout_table.json
python scripts\eval.py --subset 500 --signals clip_probe,localizer,c2pa   # quick in-event rerun
```
- Results are cached per image in `data/cache/eval/`. **Delete that folder after changing a
  signal's code** (#90).
- Weights are never changed automatically. The report suggests them; edit
  `configs/weights.yaml` by hand, then run `make eval` again.
- The AE signal is slow on CPU (#95). Leave it out of quick reruns.
- Check before the demo: real-wild FPR at HIGH ≤ 5 %, and no real face crop at HIGH.

## 9. Arena
```powershell
make arena          # 20 seeds × (nova, local_sd15, recompress) → reports/arena.csv
```
This also saves the pre-generated attack that the live chain shows when both Bedrock and
local inpainting fail. Run `make eval` afterwards so section 8 of the report fills in.

## 10. Demo cases (`data/cases/`)
Put one folder per claim in `data/cases/`. File roles come from the file names:

| File name | Role |
|---|---|
| `id.jpg` / `id_*.jpg` | ID document |
| `selfie*.jpg` | selfie |
| `*.pdf`, `invoice*` / `receipt*` / `medical*` / `report*` / `doc*` / `scan*` | document |
| any other image | damage photo |
| `case.json` | `{"title": "…"}` (optional) |

- `a_clean/`: a real photo + a clean invoice from `data/docs/clean/` + a matching ID and selfie.
- `b_fraud/`: a real photo with inpainted damage (from the arena or `data/generated/*/inpaint/`),
  an invoice from `data/docs/tampered/*_incremental.pdf`, and a matching ID and selfie.
- `c_synthetic/`: a Firefly JPEG with C2PA (`data/manual/firefly/`), plus an ID and a selfie
  of **different** people.

Open each case once in the app before the demo so the inbox shows its band chip. Then rehearse `docs/DEMO.md` five times: normal, Bedrock off, TruFor off (`impl: fallback`), CPU only, and a random judge photo.

---

## 11. Order of operations and gates
| # | What | Gate |
|---|---|---|
| 1 | Organiser's written ruling on pre-built code | 0 |
| 2 | § 1 demo-laptop setup, `pytest -q` green | 0 |
| 3 | § 5 HPC check (`hpc.sh check`) | 1.2 |
| 4 | § 4 collect seeds → prompts + masks → § 5 push / setup / submit | 2 (critical path) |
| 5 | while the HPC runs: § 3 bench files + `make bench` | 3/4 |
| 6 | § 6 rest of the dataset → `eval.py --dry` | 2 |
| 7 | § 7 heads → § 8 calibrate + eval | 4 (Flux AUC), 8 |
| 8 | § 9 arena → `make eval` | 9 |
| 9 | § 10 cases → rehearse ×5 → backup video | 11 |

## 12. Troubleshooting
| Symptom | Fix |
|---|---|
| `pip install` fails on insightface | build tools missing → install (§ 1.2), open a new terminal, re-run |
| OCR card grey: "OCR could not run" | Tesseract not on PATH (#5) |
| Documents: no page picture, digit_paste/scans fail | Poppler `Library\bin` not on PATH |
| CLIP / family-map cards grey: "missing … train_heads" | run `make heads` (§ 7) |
| Localizer card grey: "TruFor not installed" | re-run download_models, or `impl: fallback` (§ 2) |
| Anything tries to download during the demo | finish § 2, then `$env:HF_HUB_OFFLINE="1"` |
| Narrative never changes from the template | Bedrock variables unset or slow (> 4 s): expected fallback |
| Arena says "no attack path available" | Bedrock down and the local model missing, and no pre-generated attack yet → `make arena` |
| Scores look wrong after editing a signal | delete `data/cache/eval/` and `data/cache/clip/` (#41, #90) |
| HPC: `sbatch: invalid partition` | `hpc.sh check`, pick the GPU partition from `sinfo`, `export PART=…` |
| HPC job: `OSError … offline` for a model | that repo didn't download → `hpc.sh setup` again (gated? § 5.4) |
