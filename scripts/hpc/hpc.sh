#!/bin/bash
# Laptop-side HPC helper. Run in Git Bash from the repo root:
#   export HPC=<user>@<login-host> PART=<gpu-partition>
#   bash scripts/hpc/hpc.sh check     # Phase 1.2: ssh, sinfo, hello-world job, scp round trip
#   bash scripts/hpc/hpc.sh push      # scripts + seeds + masks + prompts → $SCRATCH/claimshield
#   bash scripts/hpc/hpc.sh setup     # venv + ~57 GB of weights, on the login node
#   bash scripts/hpc/hpc.sh submit    # sbatch the generation job
#   bash scripts/hpc/hpc.sh status    # queue + last log lines
#   bash scripts/hpc/hpc.sh pull      # generated images → data/generated/
# Needs key login (no password prompt): see docs/RUNBOOK.md § 5.1.
set -euo pipefail
: "${HPC:?export HPC=<user>@<login-host>}"
R='$SCRATCH/claimshield'   # single-quoted: expanded on the HPC, not here
run() { ssh -o BatchMode=yes "$HPC" "$@"; }
# scp (SFTP mode in new OpenSSH) does not expand $SCRATCH → resolve the absolute path once
abs() { echo "$(run 'echo $SCRATCH')/claimshield"; }

case "${1:-}" in
check)
    run 'hostname; echo "SCRATCH=$SCRATCH"'
    run "sinfo -o '%P %G %l %a %D'"
    : "${PART:?export PART=<gpu-partition> (pick one with a gpu in the GRES column above)}"
    run "mkdir -p $R/logs && cd $R && sbatch -p $PART --gres=gpu:1 --time=00:05:00 -o logs/hello-%j.out --wrap 'hostname; nvidia-smi'"
    echo "wait ~1 min, then: bash scripts/hpc/hpc.sh status"
    A=$(abs); echo roundtrip-$$ > rt.txt
    scp -q rt.txt "$HPC:$A/rt.txt" && scp -q "$HPC:$A/rt.txt" rt_back.txt
    diff rt.txt rt_back.txt && echo "scp round trip OK"
    rm -f rt.txt rt_back.txt ;;
push)
    for d in data/seeds data/masks data/prompts; do [ -d "$d" ] || { echo "missing $d (RUNBOOK § 4)"; exit 1; }; done
    run "mkdir -p $R/data $R/logs"
    A=$(abs)
    scp -rq scripts "$HPC:$A/"
    scp -rq data/seeds data/masks data/prompts "$HPC:$A/data/"
    echo "pushed" ;;
setup)
    # a gated model needs a one-time `huggingface-cli login` ON the HPC (the token is never
    # passed on the command line: it would show in `ps` on a shared login node)
    run "cd $R && CUDA_WHL=${CUDA_WHL:-cu121} bash scripts/hpc/setup_hpc.sh" ;;
submit)
    : "${PART:?export PART=<gpu-partition>}"
    run "cd $R && sbatch -p $PART scripts/hpc/generate.sbatch" ;;
status)
    run 'squeue -u $USER'
    run "cd $R/logs && for f in \$(ls -t | head -2); do echo \"== \$f\"; tail -n 5 \$f; done" ;;
pull)
    mkdir -p data/generated
    A=$(abs)
    for fam in sd15 sdxl flux; do scp -rq "$HPC:$A/data/generated/$fam" data/generated/ || echo "no $fam yet"; done
    ls data/generated ;;
*)
    sed -n '2,12p' "$0"; exit 1 ;;
esac
