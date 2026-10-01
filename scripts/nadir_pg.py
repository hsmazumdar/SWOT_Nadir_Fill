"""2D Papoulis–Gerchberg fill for a SWOT KaRIn nadir-gap crop.

Self-contained copy of the crop pipeline in fill_nadir_gap/src:
clear the central nadir void, seed with across-track linear interpolation,
then band-limit with an anisotropic FFT keep-mask and reinstate every
observed sample.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

CROP_H = 138
CROP_W = 69
PLOT_SCALE = 4


def central_nadir_gap_columns(
    known: np.ndarray,
    *,
    col_frac_thresh: float = 0.5,
    edge_guard: int = 10,
) -> tuple[int, int] | None:
    """Inclusive column range of the mid-swath nadir void, or None."""
    col_f = known.mean(axis=0)
    gap = np.where(col_f < col_frac_thresh)[0]
    mid = gap[(gap >= edge_guard) & (gap <= known.shape[1] - 1 - edge_guard)]
    if mid.size == 0:
        return None
    return int(mid.min()), int(mid.max())


def clear_central_nadir_gap(
    u: np.ndarray,
    *,
    col_frac_thresh: float = 0.5,
    edge_guard: int = 10,
) -> tuple[np.ndarray, dict]:
    """Set the central nadir column band to NaN (drop secondary-instrument hits)."""
    out = np.array(u, dtype=np.float64, copy=True)
    known = np.isfinite(out)
    bounds = central_nadir_gap_columns(
        known, col_frac_thresh=col_frac_thresh, edge_guard=edge_guard
    )
    meta = {"gap_cleared": False, "gap_c0": "", "gap_c1": "", "n_cleared": 0}
    if bounds is None:
        return out, meta
    c0, c1 = bounds
    band = out[:, c0 : c1 + 1]
    n_cleared = int(np.isfinite(band).sum())
    out[:, c0 : c1 + 1] = np.nan
    meta.update(
        {"gap_cleared": True, "gap_c0": c0, "gap_c1": c1, "n_cleared": n_cleared}
    )
    return out, meta


def across_track_linear_fill(u: np.ndarray) -> np.ndarray:
    """Per along-track row, interpolate NaNs across the pixel index."""
    out = u.copy()
    x = np.arange(out.shape[1], dtype=np.float64)
    for i in range(out.shape[0]):
        row = out[i]
        ok = np.isfinite(row)
        if ok.sum() == 0 or ok.all():
            continue
        out[i] = np.interp(x, x[ok], row[ok])
    still = ~np.isfinite(out)
    if np.any(still):
        fill_val = np.nanmean(out)
        if not np.isfinite(fill_val):
            fill_val = 0.0
        out = np.where(still, fill_val, out)
    return out


def lowpass_keep_mask(
    shape: tuple[int, int],
    keep_frac_along: float,
    keep_frac_across: float,
) -> np.ndarray:
    """Elliptical FFT low-pass. Fractions are of the Nyquist radius on each axis."""
    n, p = shape
    ry = max(1, int(round(keep_frac_along * n / 2.0)))
    rx = max(1, int(round(keep_frac_across * p / 2.0)))
    yy, xx = np.ogrid[:n, :p]
    cy, cx = n // 2, p // 2
    return ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0


def papoulis_gerchberg(
    u_obs: np.ndarray,
    known: np.ndarray,
    *,
    iters: int = 60,
    keep_frac_along: float = 0.35,
    keep_frac_across: float = 0.55,
) -> np.ndarray:
    """Band-limit (complex FFT, phase kept) then reinstate observations."""
    v = across_track_linear_fill(u_obs)
    if np.any(known & ~np.isfinite(u_obs)):
        raise ValueError("known mask points must be finite in u_obs")
    obs = np.where(known, u_obs, 0.0)
    H = lowpass_keep_mask(v.shape, keep_frac_along, keep_frac_across)
    for _ in range(iters):
        V = np.fft.fftshift(np.fft.fft2(v))
        V = np.where(H, V, 0.0)
        v = np.fft.ifft2(np.fft.ifftshift(V)).real
        v = np.where(known, obs, v)
    return v


def fill_crop(
    u: np.ndarray,
    *,
    iters: int = 60,
    keep_frac_along: float = 0.35,
    keep_frac_across: float = 0.55,
) -> tuple[np.ndarray, dict]:
    u2, gap_meta = clear_central_nadir_gap(u)
    known = np.isfinite(u2)
    if int(known.sum()) < 50:
        raise RuntimeError(f"too few known samples: {int(known.sum())}")
    filled = papoulis_gerchberg(
        u2,
        known,
        iters=iters,
        keep_frac_along=keep_frac_along,
        keep_frac_across=keep_frac_across,
    )
    filled = np.where(known, u2, filled)
    meta = {
        **gap_meta,
        "n_known": int(known.sum()),
        "n_gap": int((~known).sum()),
        "iters": iters,
        "keep_frac_along": keep_frac_along,
        "keep_frac_across": keep_frac_across,
        "known_max_abs_delta": float(np.max(np.abs(filled[known] - u2[known]))),
    }
    return filled, meta


def to_rgb(u: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    span = max(vmax - vmin, 1e-6)
    x = np.clip(np.nan_to_num((u - vmin) / span, nan=0.5), 0.0, 1.0)
    r = np.where(x < 0.5, 2 * x, 1.0)
    g = np.where(x < 0.5, 2 * x, 2 * (1.0 - x))
    b = np.where(x < 0.5, 1.0, 2 * (1.0 - x))
    rgb = (np.stack([r, g, b], axis=-1) * 255.0).astype(np.uint8)
    rgb[~np.isfinite(u)] = (200, 200, 200)
    return rgb


def save_panel(
    tiles: list[tuple[np.ndarray, str]],
    out_path: Path,
    vmin: float,
    vmax: float,
) -> None:
    images = []
    for arr, _lab in tiles:
        rgb = to_rgb(arr, vmin, vmax)
        images.append(
            Image.fromarray(rgb, mode="RGB").resize(
                (CROP_W * PLOT_SCALE, CROP_H * PLOT_SCALE),
                resample=Image.Resampling.NEAREST,
            )
        )
    w, h = images[0].size
    pad = 8
    label_h = 28
    canvas = Image.new(
        "RGB",
        (w * len(images) + pad * (len(images) + 1), h + pad * 2 + label_h),
        (244, 241, 234),
    )
    draw = ImageDraw.Draw(canvas)
    for i, (im, (_arr, lab)) in enumerate(zip(images, tiles)):
        x = pad + i * (w + pad)
        draw.text((x, 6), lab, fill=(20, 20, 20))
        canvas.paste(im, (x, pad + label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
