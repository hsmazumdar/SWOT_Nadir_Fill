"""Cut sample_100 from SWOT L3 passes.

Reads ssha_filtered[line_start : line_start+138, :] for the first 100 rows
of ../test_69x138/manifest.csv. Default root is Z:\\SWOT2024.

  python scripts\\build_sample_100.py
  python scripts\\build_sample_100.py --swot-root Z:\\SWOT2024
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

import numpy as np
from netCDF4 import Dataset

MIRROR = Path(__file__).resolve().parents[1]
ROOT = MIRROR.parent
MANIFEST = ROOT / "test_69x138" / "manifest.csv"
OUT = MIRROR / "sample_100"
N = 100
CROP_H = 138
FILL = -2147483647
FILL2 = -2147483648
FIELD = "ssha_filtered"


def decode_ssha(raw) -> np.ndarray:
    a = np.array(raw, dtype=np.float64, copy=True)
    if isinstance(raw, np.ma.MaskedArray):
        a = np.ma.filled(raw, np.nan).astype(np.float64)
    fill_scaled = float(FILL) * 0.0001
    bad = (
        ~np.isfinite(a)
        | np.isclose(a, fill_scaled, rtol=0, atol=1e-3)
        | (a == FILL)
        | (a == FILL2)
        | (np.abs(a) > 100.0)
    )
    return np.where(bad, np.nan, a).astype(np.float32)


def resolve_nc(source_nc: str, swot_root: Path) -> Path:
    name = Path(source_nc).name
    cycle = Path(source_nc).parent.name
    return swot_root / cycle / name


def read_crop(path: Path, line_start: int) -> np.ndarray:
    with Dataset(str(path), "r") as ds:
        var = ds.variables[FIELD]
        try:
            var.set_auto_scale(True)
        except Exception:
            pass
        raw = var[line_start : line_start + CROP_H, :]
    crop = decode_ssha(raw)
    if crop.shape != (CROP_H, 69):
        raise RuntimeError(f"unexpected crop shape {crop.shape} from {path.name}")
    return crop


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Slice 100 ssha_filtered crops into sample_100")
    ap.add_argument("--swot-root", type=Path, default=Path(r"Z:\SWOT2024"))
    ap.add_argument("--n", type=int, default=N)
    args = ap.parse_args(argv)

    if not MANIFEST.is_file():
        print(f"Missing manifest: {MANIFEST}", file=sys.stderr)
        return 1
    if not args.swot_root.is_dir():
        print(f"SWOT root not ready: {args.swot_root}", file=sys.stderr)
        return 1

    with MANIFEST.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))[: args.n]

    missing = [r["img"] for r in rows if not resolve_nc(r["source_nc"], args.swot_root).is_file()]
    if missing:
        print(
            f"{len(missing)}/{len(rows)} source passes are not in {args.swot_root} yet",
            file=sys.stderr,
        )
        print(f"first missing: {missing[0]}", file=sys.stderr)
        return 1

    crop_dir = OUT / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    out_rows = []
    for i, row in enumerate(rows, 1):
        src = resolve_nc(row["source_nc"], args.swot_root)
        crop = read_crop(src, int(row["line_start"]))
        rel = f"crops/{Path(row['img']).stem}.npy"
        np.save(crop_dir / f"{Path(row['img']).stem}.npy", crop)
        out_rows.append(
            {
                "img": row["img"],
                "index": row["index"],
                "cycle": row["cycle"],
                "pass": row["pass"],
                "line_start": row["line_start"],
                "line_end": row["line_end"],
                "npy": rel,
                "field": FIELD,
                "finite_frac": f"{float(np.isfinite(crop).mean()):.4f}",
                "n_gap": int(np.isnan(crop).sum()),
                "source_name": src.name,
            }
        )
        if i == 1 or i == len(rows) or i % 25 == 0:
            print(f"{i}/{len(rows)}  {src.name}  gap={out_rows[-1]['n_gap']}", flush=True)

    man_path = OUT / "manifest.csv"
    with man_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {len(out_rows)} crops -> {crop_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
