# ClaimShield

AI-powered synthetic identity & deepfake claim detection — Adrosonic Build PS2.

**The detector that manufactures its own fraud.** A two-tier image lane (CLIP probe +
swappable forgery localizer + async diffusion-autoencoder reconstruction test), PDF
structure forensics with a version "time machine", three claim-level checks, a
hierarchical generator-family map, and a built-in red-team arena that reports detection
on a held-out generator family. Deterministic scoring; the LLM only narrates.

Start with `CLAUDE.md`, then `docs/FINAL_APPROACH.txt`. Everything else is in `docs/`.

```
make setup && make smoke && make bench && make demo
```

| Doc | What |
|---|---|
| docs/FINAL_APPROACH.txt | v3 decisions and the reasoning behind each |
| docs/PROBLEM_STATEMENT.md | rubric, condensed |
| docs/ARCHITECTURE.md | components, contracts, decisions table |
| docs/LATENCY.md | first-card ≤ 2 s / composite ≤ 8 s spec + `make bench` protocol |
| docs/ENVIRONMENT.md | laptop / HPC / Bedrock / Qwen, env vars, compute budget |
| docs/PREBUILD.md | P0–P6 with "done when" |
| docs/SCHEDULE_24H.md | hour-by-hour, Variant A/B, kill-switches |
| docs/EVAL.md | splits, metrics, published rows |
| docs/DEMO.md | 9-minute script with failure paths |
| docs/PAPERS.md | citations and exactly what each supports |
