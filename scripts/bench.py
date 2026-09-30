"""Latency protocol (docs/LATENCY.md). Reports p95 of first card / composite / deep.
Usage: python scripts/bench.py --files data/bench --runs 20 --out reports/latency_latest.md
Implement against claimshield.pipeline.score_image(path, on_card=callback).
"""
import argparse, time, statistics, pathlib, os, sys

def p95(xs): xs = sorted(xs); return xs[int(0.95 * (len(xs) - 1))]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default="data/bench"); ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--out", default="reports/latency_latest.md"); a = ap.parse_args()
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # repo root
    from claimshield.pipeline import score_image
    rows = []
    for f in sorted(pathlib.Path(a.files).iterdir()):
        first, comp, deep = [], [], []
        for i in range(a.runs):
            # defeat the sha256 cache without touching the models: append a nonce byte
            tmp = pathlib.Path(f"{f}.{i}.bench{f.suffix}"); tmp.write_bytes(f.read_bytes() + bytes([i]))
            t0 = time.perf_counter(); tf = [None]
            def on_card(sig):
                if tf[0] is None: tf[0] = time.perf_counter() - t0
            res = score_image(str(tmp), on_card=on_card, wait_deep=True)
            first.append(tf[0]); comp.append(res.t_fast); deep.append(res.t_deep); tmp.unlink()
        deep_p95 = float("nan") if None in deep else p95(deep)  # nan until the deep tier exists
        rows.append((f.name, p95(first), statistics.mean(first), p95(comp), statistics.mean(comp), deep_p95))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as w:
        w.write("| file | first card p95 | mean | composite p95 | mean | deep p95 |\n|---|---|---|---|---|---|\n")
        for r in rows: w.write("| %s | %.2f | %.2f | %.2f | %.2f | %.2f |\n" % r)
    print(open(a.out).read())

if __name__ == "__main__": main()
