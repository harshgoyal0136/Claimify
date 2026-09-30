#!/bin/bash
#SBATCH --job-name=claimshield-gen
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=logs/gen-%j.out
# Set the partition at submit time: sbatch -p <gpu-partition> scripts/hpc/generate.sbatch
# Resumable: if the time limit hits, submit again; finished images are skipped.
set -euo pipefail
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HOME=$SCRATCH/models/hf
cd $SCRATCH/claimshield
source .venv/bin/activate
nvidia-smi
python scripts/hpc/generate.py --models sd15,sdxl,flux --n 134
