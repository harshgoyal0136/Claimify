# HPC batch workflow (compute nodes have no internet)

Full walkthrough: `docs/RUNBOOK.md` § 5. Short version, from Git Bash on the laptop:

```bash
export HPC=<user>@<login-host> PART=<gpu-partition>
bash scripts/hpc/hpc.sh check     # Phase 1.2: ssh, sinfo, hello-world job, scp round trip
bash scripts/hpc/hpc.sh push      # scripts + data/{seeds,masks,prompts}
bash scripts/hpc/hpc.sh setup     # login node: .venv + ~57 GB weights (setup_hpc.sh)
bash scripts/hpc/hpc.sh submit    # sbatch generate.sbatch (resubmit on time-out; resumes)
bash scripts/hpc/hpc.sh status
bash scripts/hpc/hpc.sh pull      # → data/generated/{sd15,sdxl,flux}
```

Status: none of this has been run yet (login host / user pending, ISSUES #48). Record here
anything that differed on the real cluster.

## Optional live worker for the demo (never critical path)
```
salloc --gres=gpu:1 --time=04:00:00
python scripts/hpc/worker.py --port 8000      # on the compute node (worker.py not written)
ssh -J <login-node> <compute-node> -L 8000:localhost:8000   # from laptop
set CLAIMSHIELD_HPC_URL=http://localhost:8000
```
