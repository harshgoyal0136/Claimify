# HPC batch workflow (compute nodes have no internet)

Status: Phase 1.2 NOT yet run — login host / user / partition still pending (ISSUES #48).
Replace `<user>@<host>` below with the real values and record anything that differed.

## 1.2 Connectivity check (from the laptop)
```
ssh -o BatchMode=yes <user>@<host> 'hostname; echo $SCRATCH'   # must not prompt
ssh <user>@<host> sinfo -o '%P %G %l %a'                        # find the GPU partition
ssh <user>@<host> 'mkdir -p $SCRATCH/claimshield/logs && cd $SCRATCH/claimshield &&
  sbatch -p <gpu-partition> --gres=gpu:1 --time=00:05:00 -o logs/hello-%j.out --wrap "hostname; nvidia-smi"'
ssh <user>@<host> 'cat $SCRATCH/claimshield/logs/hello-*.out'
echo roundtrip > rt.txt && scp rt.txt <user>@<host>:'$SCRATCH/claimshield/' &&
  scp <user>@<host>:'$SCRATCH/claimshield/rt.txt' rt_back.txt && diff rt.txt rt_back.txt
```
If `$SCRATCH` is not defined on this cluster, use the scratch path `sinfo`/docs give and
edit `generate.sbatch`.

## 2. Environment + weights (login node only — has internet; never on the laptop)
```
cd $SCRATCH/claimshield && python3.11 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu121   # match the node's CUDA
pip install diffusers transformers accelerate safetensors sentencepiece protobuf pillow pillow-heif
export HF_HOME=$SCRATCH/models/hf
huggingface-cli download stable-diffusion-v1-5/stable-diffusion-v1-5 --include "*.json" "*.txt" "*fp16.safetensors"
huggingface-cli download stable-diffusion-v1-5/stable-diffusion-inpainting --include "*.json" "*.txt" "*fp16.safetensors"
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --include "*.json" "*.txt" "*fp16.safetensors"
huggingface-cli download diffusers/stable-diffusion-xl-1.0-inpainting-0.1 --include "*.json" "*.txt" "*fp16.safetensors"
huggingface-cli download black-forest-labs/FLUX.1-schnell --exclude "flux1-schnell.safetensors"
```
Roughly 5 + 5 + 7 + 7 + 33 GB. Flux may need `huggingface-cli login` first (ISSUES #53).

## 3. Inputs (laptop → HPC)
```
python scripts/gen/make_prompts.py && python scripts/gen/masks.py
ssh <user>@<host> 'mkdir -p $SCRATCH/claimshield/data $SCRATCH/claimshield/logs'
scp -r scripts <user>@<host>:'$SCRATCH/claimshield/'
scp -r data/seeds data/masks data/prompts <user>@<host>:'$SCRATCH/claimshield/data/'
```

## 4. Submit, watch, pull
```
ssh <user>@<host> 'cd $SCRATCH/claimshield && sbatch -p <gpu-partition> scripts/hpc/generate.sbatch'
ssh <user>@<host> 'squeue -u $USER; tail -n 5 $SCRATCH/claimshield/logs/gen-*.out'
scp -r <user>@<host>:'$SCRATCH/claimshield/data/generated/{sd15,sdxl,flux}' data/generated/
```
Time limit hit → submit again; finished images are skipped.

## 5. After the pull (laptop / CPU)
```
python scripts/gen/splice.py && python scripts/gen/nova_attacks.py
python scripts/gen/invoices.py && python scripts/gen/medical.py && python scripts/gen/tamper_pdf.py
python scripts/gen/manifest.py && python scripts/gen/recompress.py && python scripts/gen/manifest.py
python scripts/eval.py --dry        # Gate 2
```

## Optional live worker for the demo (never critical path)
```
salloc --gres=gpu:1 --time=04:00:00
python scripts/hpc/worker.py --port 8000      # on the compute node
ssh -J <login-node> <compute-node> -L 8000:localhost:8000   # from laptop
set CLAIMSHIELD_HPC_URL=http://localhost:8000
```
