"""Fill the 100-crop sample shipped in this mirror.

From GitHub_mirror:

  python scripts\\run_pg_demo.py

Writes sample_100/demo_summary.json and the first few before/after panels.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from nadir_pg import fill_crop, save_panel  # noqa: E402

MIRROR = _SCRIPTS.parent
SAMPLE = MIRROR / "sample_100"
MANIFEST = SAMPLE / "manifest.csv"


def load_rows(limit: int) -> list[dict]:
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if limit > 0:
        rows = rows[:limit]
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run PG nadir-gap fill on sample_100")
    ap.add_argument("--limit", type=int, default=0, help="if >0, only the first N crops")
    ap.add_argument("--panels", type=int, default=3, help="how many before/after panels to write")
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--keep-along", type=float, default=0.35)
    ap.add_argument("--keep-across", type=float, default=0.55)
    args = ap.parse_args(argv)

    rows = load_rows(args.limit)
    if not rows:
        print(f"No rows in {MANIFEST}", file=sys.stderr)
        return 1

    panel_dir = SAMPLE / "panels"
    records = []
    t0 = time.perf_counter()
    for i, row in enumerate(rows, 1):
        npy = SAMPLE / row["npy"]
        u = np.load(npy)
        filled, meta = fill_crop(
            u,
            iters=args.iters,
            keep_frac_along=args.keep_along,
            keep_frac_across=args.keep_across,
        )
        finite = u[np.isfinite(u)]
        vmin = float(np.percentile(finite, 2))
        vmax = float(np.percentile(finite, 98))
        if vmax <= vmin:
            vmax = vmin + 1e-3
        rec = {
            "index": int(row["index"]),
            "img": row["img"],
            "cycle": int(row["cycle"]),
            "pass": int(row["pass"]),
            "n_known": meta["n_known"],
            "n_gap": meta["n_gap"],
            "gap_c0": meta["gap_c0"],
            "gap_c1": meta["gap_c1"],
            "known_max_abs_delta": meta["known_max_abs_delta"],
        }
        if i <= args.panels:
            out_png = panel_dir / f"pg_{int(row['index']):03d}.png"
            save_panel(
                [
                    (u, "observed (gray = gap)"),
                    (filled, f"PG T={args.iters}"),
                ],
                out_png,
                vmin,
                vmax,
            )
            rec["panel"] = str(out_png.relative_to(MIRROR))
        records.append(rec)
        if i == 1 or i == len(rows) or i % 25 == 0:
            print(
                f"{i}/{len(rows)}  gap={meta['n_gap']}  "
                f"known_delta={meta['known_max_abs_delta']:.3e}",
                flush=True,
            )

    elapsed = time.perf_counter() - t0
    gaps = np.array([r["n_gap"] for r in records], dtype=np.float64)
    deltas = np.array([r["known_max_abs_delta"] for r in records], dtype=np.float64)
    summary = {
        "n": len(records),
        "iters": args.iters,
        "keep_frac_along": args.keep_along,
        "keep_frac_across": args.keep_across,
        "mean_n_gap": round(float(gaps.mean()), 1),
        "median_n_gap": round(float(np.median(gaps)), 1),
        "max_known_abs_delta": float(deltas.max()),
        "elapsed_s": round(elapsed, 3),
        "panels": [r["panel"] for r in records if "panel" in r],
    }
    out_json = SAMPLE / "demo_summary.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
