"""Side-by-side viewer for the 100 shipped SWOT crops.

Left: observed ssha_filtered (gray = missing, including the nadir void).
Right: 2D anisotropic Papoulis–Gerchberg fill. Known samples stay unchanged.

  python scripts\\nadir_viewer.py

Keys: Up/Down or Left/Right move, Home/End jump, Esc quits.
"""
from __future__ import annotations

import csv
import sys
import tkinter as tk
from pathlib import Path

import numpy as np
from PIL import Image, ImageTk

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from nadir_pg import CROP_H, CROP_W, PLOT_SCALE, fill_crop, to_rgb  # noqa: E402

MIRROR = _SCRIPTS.parent
SAMPLE = MIRROR / "sample_100"
MANIFEST = SAMPLE / "manifest.csv"
BG = "#121820"
PANEL = "#1a2230"
FG = "#e8e4dc"


def load_rows() -> list[dict]:
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class Viewer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SWOT Nadir Fill")
        self.configure(bg=BG)
        self.rows = load_rows()
        if not self.rows:
            raise SystemExit(f"No crops in {MANIFEST}")
        self.index = 0
        self._photos: list[ImageTk.PhotoImage] = []
        self._cache: dict[int, tuple[np.ndarray, np.ndarray, float, float]] = {}

        self.header = tk.Label(self, bg=BG, fg=FG, font=("Segoe UI", 12), anchor="w")
        self.header.pack(fill="x", padx=12, pady=(10, 4))

        body = tk.Frame(self, bg=BG)
        body.pack(padx=12, pady=4)
        self.left_title = tk.Label(body, text="Observed", bg=BG, fg=FG, font=("Segoe UI", 10))
        self.right_title = tk.Label(body, text="PG fill  T=60", bg=BG, fg=FG, font=("Segoe UI", 10))
        self.left_title.grid(row=0, column=0, sticky="w")
        self.right_title.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.left = tk.Label(body, bg=PANEL)
        self.right = tk.Label(body, bg=PANEL)
        self.left.grid(row=1, column=0)
        self.right.grid(row=1, column=1, padx=(12, 0))

        self.footer = tk.Label(
            self,
            bg=BG,
            fg="#b7b1a6",
            font=("Segoe UI", 9),
            anchor="w",
            text="Up/Down  move     Home/End  first/last     Esc  quit     gray = missing",
        )
        self.footer.pack(fill="x", padx=12, pady=(6, 10))

        self.bind("<Up>", lambda _e: self.step(-1))
        self.bind("<Left>", lambda _e: self.step(-1))
        self.bind("<Down>", lambda _e: self.step(1))
        self.bind("<Right>", lambda _e: self.step(1))
        self.bind("<Home>", lambda _e: self.jump(0))
        self.bind("<End>", lambda _e: self.jump(len(self.rows) - 1))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<MouseWheel>", self._wheel)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(30, self.show)

    def _wheel(self, event: tk.Event) -> None:
        self.step(-1 if event.delta > 0 else 1)

    def step(self, delta: int) -> None:
        self.jump((self.index + delta) % len(self.rows))

    def jump(self, index: int) -> None:
        self.index = index
        self.show()

    def _pair(self, index: int) -> tuple[np.ndarray, np.ndarray, float, float]:
        hit = self._cache.get(index)
        if hit is not None:
            return hit
        row = self.rows[index]
        observed = np.load(SAMPLE / row["npy"])
        filled, _meta = fill_crop(observed)
        finite = observed[np.isfinite(observed)]
        vmin = float(np.percentile(finite, 2)) if finite.size else -0.2
        vmax = float(np.percentile(finite, 98)) if finite.size else 0.2
        if vmax <= vmin:
            vmax = vmin + 1e-3
        hit = (observed, filled, vmin, vmax)
        self._cache[index] = hit
        return hit

    def _photo(self, field: np.ndarray, vmin: float, vmax: float) -> ImageTk.PhotoImage:
        rgb = to_rgb(field, vmin, vmax)
        image = Image.fromarray(rgb, mode="RGB").resize(
            (CROP_W * PLOT_SCALE, CROP_H * PLOT_SCALE),
            resample=Image.Resampling.NEAREST,
        )
        return ImageTk.PhotoImage(image)

    def show(self) -> None:
        row = self.rows[self.index]
        self.header.configure(text=f"{self.index + 1} / {len(self.rows)}    filling…")
        self.update_idletasks()
        observed, filled, vmin, vmax = self._pair(self.index)
        left = self._photo(observed, vmin, vmax)
        right = self._photo(filled, vmin, vmax)
        self._photos = [left, right]
        self.left.configure(image=left)
        self.right.configure(image=right)
        cycle = row.get("cycle", "")
        pas = row.get("pass", "")
        self.header.configure(
            text=(
                f"{self.index + 1} / {len(self.rows)}    "
                f"cycle {cycle}   pass {pas}    "
                f"gap pixels {row.get('n_gap', '')}"
            )
        )


def main() -> int:
    if not MANIFEST.is_file():
        print(f"Missing {MANIFEST}", file=sys.stderr)
        return 1
    Viewer().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
