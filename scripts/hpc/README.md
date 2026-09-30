# HPC batch workflow (compute nodes have no internet)

1. On the login node (has internet):
   pip download / huggingface-cli download the weights into $SCRATCH/models
   (SD1.5, SDXL, Flux, VAEs, CLIP ViT-L/14, TruFor).
2. Copy seeds + prompts:  scp -r data/seeds data/prompts <login>:$SCRATCH/claimshield/
3. Submit:  sbatch scripts/hpc/generate.sbatch   (edit partition/GPU/time first)
4. Pull results:  scp -r <login>:$SCRATCH/claimshield/generated data/
5. Optional live worker for the demo (never critical path):
   salloc --gres=gpu:1 --time=04:00:00
   python scripts/hpc/worker.py --port 8000      # on the compute node
   ssh -J <login-node> <compute-node> -L 8000:localhost:8000   # from laptop
   set CLAIMSHIELD_HPC_URL=http://localhost:8000
