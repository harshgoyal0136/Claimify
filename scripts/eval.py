"""Eval harness (docs/EVAL.md). Only --dry exists yet: validates the manifests (Gate 2).
The scoring run (9 published rows) is Phase 8.
Usage: python scripts/eval.py --dry [--manifest data/generated/manifest.csv]
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLS = ["path", "label", "family", "attack", "quality", "heldout", "split", "seed_path", "mask_path"]
ENUMS = {
    "label": {"real", "fake"},
    "family": {"real", "sd15", "sdxl", "flux", "firefly", "midjourney", "nova", "splice",
               "copymove", "inpaint", "gan"},
    "quality": {"orig", "q90", "q70", "q50", "dn512", "whatsapp"},
    "heldout": {"0", "1"},
    "split": {"train", "calib", "test", "eval_only", "wild"},
}
NEEDS_MASK = {"inpaint", "splice", "copymove"}


def check_images(rows):
    errs = []
    if not rows or list(rows[0]) != COLS:
        return [f"columns must be exactly {COLS}"]
    for i, r in enumerate(rows, 2):
        errs += [f"line {i}: {k}={r[k]!r} not in {sorted(v)}" for k, v in ENUMS.items()
                 if r[k] not in v]
        for k in ("path", "seed_path", "mask_path"):
            if r[k] and not (ROOT / r[k]).exists():
                errs.append(f"line {i}: {k} missing on disk: {r[k]}")
        if (r["label"] == "real") != (r["family"] == "real"):
            errs.append(f"line {i}: label/family disagree")
        if (r["family"] == "flux") != (r["heldout"] == "1"):
            errs.append(f"line {i}: flux ⇔ heldout=1 violated")
        if r["heldout"] == "1" and r["split"] in ("train", "calib"):
            errs.append(f"line {i}: held-out row in {r['split']}")
        if (r["family"] == "gan") != (r["split"] == "eval_only"):
            errs.append(f"line {i}: gan ⇔ eval_only violated")
        if r["attack"] in NEEDS_MASK and not r["mask_path"]:
            errs.append(f"line {i}: {r['attack']} row without mask_path")
    # a seed may feed only one of train / calib / test (held-out rows are exempt)
    splits = defaultdict(set)
    for r in rows:
        if r["seed_path"] and r["heldout"] == "0" and r["split"] in ("train", "calib", "test"):
            splits[r["seed_path"]].add(r["split"])
    errs += [f"seed {s} leaks across {sorted(v)}" for s, v in splits.items() if len(v) > 1]
    if len({r["path"] for r in rows}) != len(rows):
        errs.append("duplicate paths")
    for need in ("train", "calib", "test"):
        if not any(r["split"] == need and r["heldout"] == "0" for r in rows):
            errs.append(f"no heldout=0 rows in split={need}")
    if not any(r["heldout"] == "1" for r in rows):
        errs.append("no held-out (flux) rows")
    return errs


def check_docs(rows):
    errs = []
    for i, r in enumerate(rows, 2):
        if not (ROOT / r["path"]).exists():
            errs.append(f"docs line {i}: missing {r['path']}")
        if (r["label"] == "tampered") != (r["tamper"] != "none"):
            errs.append(f"docs line {i}: label/tamper disagree")
    return errs


def dry(manifest):
    rows = list(csv.DictReader(open(ROOT / manifest, encoding="utf-8")))
    errs = check_images(rows)
    print(f"{manifest}: {len(rows)} rows")
    for k in ("split", "family", "quality"):
        print(f"  {k}: {dict(Counter(r[k] for r in rows))}")
    docs = ROOT / "data/docs/manifest.csv"
    if docs.exists():
        drows = list(csv.DictReader(open(docs, encoding="utf-8")))
        errs += check_docs(drows)
        print(f"data/docs/manifest.csv: {len(drows)} rows, "
              f"{dict(Counter(r['tamper'] for r in drows))}")
    else:
        errs.append("data/docs/manifest.csv missing (run scripts/gen/tamper_pdf.py)")
    for e in errs[:50]:
        print("ERROR", e)
    print("DRY OK" if not errs else f"DRY FAILED: {len(errs)} problems")
    return not errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--manifest", default="data/generated/manifest.csv")
    ap.add_argument("--out", default="reports/eval_latest.md")
    ap.add_argument("--subset", type=int)
    ap.add_argument("--signals")
    a = ap.parse_args()
    if not a.dry:
        sys.exit("eval.py: only --dry exists; the scoring run is Phase 8 (not written yet).")
    sys.exit(0 if dry(a.manifest) else 1)


if __name__ == "__main__":
    main()
