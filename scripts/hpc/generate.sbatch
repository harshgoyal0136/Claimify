#!/bin/bash
#SBATCH --job-name=claimshield-gen
#SBATCH --gres=gpu:1
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HOME=$SCRATCH/models/hf
cd $SCRATCH/claimshield
python generate.py --models sd15,sdxl,flux --seeds data/seeds --prompts data/prompts/prompts.txt \
  --out generated --n_t2i 400 --n_img2img 400 --n_inpaint 400 --heldout flux
