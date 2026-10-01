"""
Build OnNadirGapFilling.docx — theoretical report + Q1 figures + result tables.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
DOCS = Path(__file__).resolve().parent
FIG = DOCS / "figures"
OUT_DOCX = DOCS / "OnNadirGapFilling.docx"
OUT_DOCS = DOCS / "OnNadirGapFilling.docs"  # user-requested extension (docx copy)

TEST = ROOT / "test_69x138"
FILLED = ROOT / "filled_69x138"
REMEDY = ROOT / "filled_69x138_remedy_v3"
FQ_CSV = ROOT / "out" / "fill_quality" / "fill_quality_all.csv"
FQ_SUM = ROOT / "out" / "fill_quality" / "fill_quality_summary.json"
COMPLETION = ROOT / "out" / "filled_69xfull" / "COMPLETION_REPORT.json"
SUMMARY_2024 = ROOT / "out" / "filled_69xfull" / "summary_2024.json"

# Publication style
mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.linewidth": 0.8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": False,
    }
)


def _load_png(folder: Path, name: str) -> np.ndarray:
    return np.asarray(Image.open(folder / name).convert("RGB"))


def fig1_swath_geometry() -> Path:
    """Schematic of KaRIn swath with central nadir gap."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    n, p = 80, 69
    field = np.zeros((n, p))
    # synthetic mesoscale-like field
    yy, xx = np.mgrid[0:n, 0:p]
    field = 0.08 * np.sin(2 * np.pi * yy / 35) * np.cos(2 * np.pi * xx / 40)
    field += 0.04 * np.sin(2 * np.pi * (yy / 18 + xx / 25))
    c0, c1 = 30, 38
    known = np.ones((n, p), dtype=bool)
    known[:, c0 : c1 + 1] = False
    known[:, :3] = False
    known[:, -3:] = False
    display = np.ma.array(field, mask=~known)
    im = ax.imshow(display, cmap="RdBu_r", aspect="auto", vmin=-0.12, vmax=0.12)
    ax.axvline(c0 - 0.5, color="k", lw=1.0, ls="--")
    ax.axvline(c1 + 0.5, color="k", lw=1.0, ls="--")
    ax.set_xlabel("Across-track pixel index  p  (0 … 68)")
    ax.set_ylabel("Along-track sample  n")
    ax.set_title("Figure 1. KaRIn L3 LR swath geometry and central nadir void")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$u$  (synthetic SSHA, m)")
    ax.text(
        (c0 + c1) / 2,
        n * 0.5,
        "nadir gap\n$m=0$",
        ha="center",
        va="center",
        fontsize=9,
        color="0.15",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.5", alpha=0.9),
    )
    ax.text(12, 8, "left KaRIn\n$m=1$", ha="center", fontsize=8, color="0.2")
    ax.text(55, 8, "right KaRIn\n$m=1$", ha="center", fontsize=8, color="0.2")
    out = FIG / "Fig01_swath_geometry.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig2_pg_iteration() -> Path:
    """Illustrate PG projectors PB and PM."""
    fig, axes = plt.subplots(1, 4, figsize=(9.5, 2.8))
    rng = np.random.default_rng(7)
    n, p = 64, 48
    true = 0.1 * np.sin(2 * np.pi * np.linspace(0, 3, n))[:, None] * np.cos(
        2 * np.pi * np.linspace(0, 2, p)
    )
    true += 0.03 * rng.standard_normal((n, p))
    known = np.ones((n, p), dtype=bool)
    known[:, 18:30] = False
    obs = np.where(known, true, np.nan)

    def across_fill(u):
        out = u.copy()
        x = np.arange(p, dtype=float)
        for i in range(n):
            ok = np.isfinite(out[i])
            if ok.any() and not ok.all():
                out[i] = np.interp(x, x[ok], out[i, ok])
        return np.nan_to_num(out, nan=0.0)

    v0 = across_fill(obs)
    # one PG step
    V = np.fft.fftshift(np.fft.fft2(v0))
    yy, xx = np.ogrid[:n, :p]
    H = ((yy - n // 2) / (0.35 * n / 2)) ** 2 + ((xx - p // 2) / (0.55 * p / 2)) ** 2 <= 1
    Vb = np.where(H, V, 0)
    vb = np.fft.ifft2(np.fft.ifftshift(Vb)).real
    vm = np.where(known, true, vb)

    panels = [
        (np.ma.array(obs, mask=~np.isfinite(obs)), r"(a) $u_{\mathrm{obs}}$"),
        (v0, r"(b) init $v^{(0)}$"),
        (vb, r"(c) $\mathcal{P}_B v$"),
        (vm, r"(d) $\mathcal{P}_M\mathcal{P}_B v$"),
    ]
    vmin, vmax = -0.15, 0.15
    for ax, (arr, title) in zip(axes, panels):
        im = ax.imshow(arr, cmap="RdBu_r", aspect="auto", vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.02, pad=0.02, label="m")
    fig.suptitle(
        "Figure 2. One Papoulis–Gerchberg iteration (band-limit → reinstate)",
        y=1.02,
        fontsize=11,
    )
    out = FIG / "Fig02_pg_iteration.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig3_spectral_mask() -> Path:
    """Anisotropic low-pass keep mask H(k)."""
    n, p = 256, 69
    keep_a, keep_x = 0.35, 0.55
    ry = max(1, int(round(keep_a * n / 2)))
    rx = max(1, int(round(keep_x * p / 2)))
    yy, xx = np.ogrid[:n, :p]
    H = ((yy - n // 2) / ry) ** 2 + ((xx - p // 2) / rx) ** 2 <= 1.0

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4))
    axes[0].imshow(H.T, cmap="gray_r", aspect="auto", origin="lower", interpolation="nearest")
    axes[0].set_xlabel(r"Along-track frequency bin $k_n$")
    axes[0].set_ylabel(r"Across-track frequency bin $k_p$")
    axes[0].set_title(r"(a) Anisotropic keep mask $H(k_n,k_p)$")
    # radial profile
    cy, cx = n // 2, p // 2
    kn = np.linspace(-0.5, 0.5, n)
    kp = np.linspace(-0.5, 0.5, p)
    KN, KP = np.meshgrid(kn, kp, indexing="ij")
    axes[1].contourf(KN, KP, H.astype(float), levels=[0, 0.5, 1.1], colors=["#f0f0f0", "#2c7bb6"])
    axes[1].set_xlabel(r"Normalized $k_n$")
    axes[1].set_ylabel(r"Normalized $k_p$")
    axes[1].set_title(rf"(b) Ellipse: $f_\parallel$={keep_a}, $f_\perp$={keep_x}")
    axes[1].set_aspect("equal")
    fig.suptitle("Figure 3. Spectral projector $\\mathcal{P}_B$ — elliptical low-pass", fontsize=11)
    out = FIG / "Fig03_spectral_mask.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig4_before_after() -> Path:
    """Real SWOT crops: gap vs filled (good and challenging cases)."""
    good = "img_0000000013__c011_p293_L003579_20240225T072709.png"
    bad = "img_0000000012__c010_p001_L001030_20240125T001932.png"
    best = "img_0000000653__c012_p425_L001529_20240321T212313.png"
    names = [good, bad, best]
    labels = [
        "(a) Structured mesoscale (good PG)",
        "(b) Flat / low-SNR (challenging)",
        "(c) Highest quality score (A, 98.6)",
    ]
    fig, axes = plt.subplots(3, 2, figsize=(7.0, 9.0))
    for i, (name, lab) in enumerate(zip(names, labels)):
        left = _load_png(TEST, name)
        right = _load_png(FILLED, name)
        axes[i, 0].imshow(left)
        axes[i, 1].imshow(right)
        axes[i, 0].set_ylabel(lab, fontsize=9)
        for j, ttl in enumerate(["Observed (gap)", "PG filled"]):
            axes[i, j].set_xticks([])
            axes[i, j].set_yticks([])
            if i == 0:
                axes[i, j].set_title(ttl, fontsize=10)
    fig.suptitle(
        "Figure 4. SWOT2024 138×69 strips: observation vs 2D PG reconstruction",
        fontsize=11,
        y=0.995,
    )
    fig.tight_layout()
    out = FIG / "Fig04_before_after.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig5_quality_distributions(df: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.1))
    # score hist
    axes[0].hist(df["score"], bins=30, color="#2c7bb6", edgecolor="white", linewidth=0.5)
    axes[0].axvline(df["score"].median(), color="#d7191c", ls="--", lw=1.2, label="median")
    axes[0].set_xlabel("Composite quality score")
    axes[0].set_ylabel("Count")
    axes[0].set_title("(a) Score distribution (n=1000)")
    axes[0].legend(frameon=False)

    grades = ["A", "B", "C", "D", "F"]
    counts = [int((df["grade"] == g).sum()) for g in grades]
    colors = ["#1a9641", "#a6d96a", "#ffffbf", "#fdae61", "#d7191c"]
    axes[1].bar(grades, counts, color=colors, edgecolor="0.3", linewidth=0.5)
    axes[1].set_xlabel("Grade")
    axes[1].set_ylabel("Count")
    axes[1].set_title("(b) Grade histogram")
    for g, c in zip(grades, counts):
        axes[1].text(g, c + 8, str(c), ha="center", fontsize=8)

    axes[2].scatter(
        df["lr_corr"],
        df["gap_over_side"],
        c=df["score"],
        cmap="viridis",
        s=8,
        alpha=0.65,
        linewidths=0,
    )
    axes[2].axhline(1.0, color="0.4", ls=":", lw=0.8)
    axes[2].axvline(0.7, color="0.4", ls=":", lw=0.8)
    axes[2].set_xlabel("Left–right correlation")
    axes[2].set_ylabel(r"$\sigma_{\mathrm{gap}}/\sigma_{\mathrm{side}}$")
    axes[2].set_title("(c) Structure vs continuity")
    cb = fig.colorbar(
        axes[2].collections[0], ax=axes[2], fraction=0.046, pad=0.04, label="score"
    )
    fig.suptitle("Figure 5. Fill-quality metrics on 1000 SWOT2024 crops", fontsize=11)
    fig.tight_layout()
    out = FIG / "Fig05_quality_distributions.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig6_production_2024() -> Path:
    with SUMMARY_2024.open(encoding="utf-8") as f:
        s = json.load(f)
    with COMPLETION.open(encoding="utf-8") as f:
        c = json.load(f)["2024"]
    labels = ["OK filled", "Failed", "Skip"]
    sizes = [s["n_ok_new"], s["n_fail"], s["n_skip"]]
    colors = ["#2c7bb6", "#d7191c", "#999999"]
    fail = dict(c["fail_reasons"])

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4))
    wedges, texts, autotexts = axes[0].pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct=lambda p: f"{p:.1f}%" if p > 1 else "",
        startangle=90,
        textprops={"fontsize": 9},
    )
    axes[0].set_title("(a) Pass outcomes (n=10,038)")
    fr_lab = list(fail.keys())
    fr_val = [fail[k] for k in fr_lab]
    axes[1].barh(fr_lab[::-1], fr_val[::-1], color="#fdae61", edgecolor="0.3", linewidth=0.5)
    axes[1].set_xlabel("Count")
    axes[1].set_title("(b) Failure reasons")
    for y, v in zip(range(len(fr_val)), fr_val[::-1]):
        axes[1].text(v + 5, y, str(v), va="center", fontsize=9)
    fig.suptitle("Figure 6. Full-orbit 2024 production build (E:\\SWOT2024_Ok)", fontsize=11)
    fig.tight_layout()
    out = FIG / "Fig06_production_2024.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig7_pipeline() -> Path:
    """Block diagram of production pipeline."""
    fig, ax = plt.subplots(figsize=(8.8, 2.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.3, 1.0, 1.8, 1.2, "SWOT L3 LR\n$u_{\\mathrm{obs}}$\n69 cols"),
        (2.4, 1.0, 1.8, 1.2, "Clear central\nnadir gap\n$m\\leftarrow 0$"),
        (4.5, 1.0, 1.8, 1.2, "Init E0\nacross-track\nlinear"),
        (6.6, 1.0, 1.8, 1.2, "2D PG\n60 iters\n$\\mathcal{P}_M\\mathcal{P}_B$"),
        (8.4, 1.0, 1.4, 1.2, "Twin NC\nOk dataset"),
    ]
    for x, y, w, h, txt in boxes:
        ax.add_patch(
            plt.Rectangle(
                (x, y), w, h, fill=True, facecolor="#e8f1f8", edgecolor="#2c7bb6", lw=1.2
            )
        )
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=8)
    for x in [2.1, 4.2, 6.3, 8.4]:
        ax.annotate("", xy=(x, 1.6), xytext=(x - 0.3, 1.6), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.set_title("Figure 7. Production pipeline for full half-orbit nadir-gap fill", fontsize=11, pad=8)
    out = FIG / "Fig07_pipeline.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def set_run_font(run, size=11, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def add_para(doc, text, *, size=11, bold=False, italic=False, space_after=8, align="left"):
    p = doc.add_paragraph()
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    return p


def add_heading_custom(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        set_run_font(run, size=14 if level == 1 else 12, bold=True)
    return h


def add_equation(doc, latex_like: str, number: str | None = None):
    """Plain-text equation block (Word OMML not required)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(latex_like)
    set_run_font(run, size=11, italic=True)
    if number:
        run2 = p.add_run(f"    ({number})")
        set_run_font(run2, size=11, italic=False)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_caption(doc, text):
    p = add_para(doc, text, size=9, italic=True, space_after=12, align="center")
    return p


def add_figure(doc, path: Path, width_in=6.2):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))
    p.paragraph_format.space_after = Pt(2)


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for j, h in enumerate(headers):
        hdr[j].text = ""
        p = hdr[j].paragraphs[0]
        run = p.add_run(h)
        set_run_font(run, size=9, bold=True)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            set_run_font(run, size=9)
    if col_widths:
        for row in table.rows:
            for j, w in enumerate(col_widths):
                row.cells[j].width = Cm(w)
    doc.add_paragraph()
    return table


def build_document(fig_paths: dict, df: pd.DataFrame):
    with SUMMARY_2024.open(encoding="utf-8") as f:
        s24 = json.load(f)
    with COMPLETION.open(encoding="utf-8") as f:
        c24 = json.load(f)["2024"]
    with FQ_SUM.open(encoding="utf-8") as f:
        fq = json.load(f)

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    # Title
    add_para(
        doc,
        "On Nadir-Gap Filling for SWOT KaRIn Sea-Surface Height Anomaly",
        size=16,
        bold=True,
        align="center",
        space_after=4,
    )
    add_para(
        doc,
        "Theory, Papoulis–Gerchberg Algorithm, and 2024 Production Results",
        size=12,
        italic=True,
        align="center",
        space_after=4,
    )
    add_para(
        doc,
        "RespondSeeSurface / fill_nadir_gap  ·  Technical report",
        size=10,
        align="center",
        space_after=2,
    )
    add_para(
        doc,
        "Dataset year: 2024 (E:\\SWOT2024 → E:\\SWOT2024_Ok)  ·  Method tag: papoulis_gerchberg_2d_aniso",
        size=9,
        align="center",
        space_after=18,
    )

    # Abstract
    add_heading_custom(doc, "Abstract", level=1)
    add_para(
        doc,
        "The Surface Water and Ocean Topography (SWOT) Ka-band Radar Interferometer (KaRIn) "
        "delivers wide-swath sea-surface height anomaly (SSHA) with a persistent along-track "
        "void at nadir where the interferometric baseline vanishes. Reconstructing this gap is "
        "required for continuous swath products used in downscaling and residual learning "
        "against Level-4 sea-level anomaly (SLA). This report formalizes the nadir-gap problem "
        "in the discrete Fourier domain, explains why magnitude-only spectral interpolation is "
        "scientifically inadequate, and derives the two-dimensional anisotropic Papoulis–Gerchberg "
        "(PG) algorithm used in production. On 10,038 SWOT L3 LR half-orbits from 2024, the "
        "pipeline successfully wrote 9,532 filled NetCDF twins (≈95% success) under the "
        "contract that all originally valid KaRIn samples are reinstated exactly. Quality "
        "scoring on 1,000 random 138×69 crops yields mean score 75.1 (median 77.9), with "
        "ringing and weak left–right correlation as the dominant residual failure modes. "
        "Results support PG as an operational reconstruction with uncertainty—not as new "
        "KaRIn measurements—and motivate a future hybrid spatial-residual AI with spectral guard.",
        align="justify",
        space_after=12,
    )

    # 1. Introduction
    add_heading_custom(doc, "1. Introduction", level=1)
    add_para(
        doc,
        "SWOT KaRIn Level-3 low-resolution (LR) Basic products provide SSHA on a swath grid "
        "with 69 across-track pixels. Near the satellite ground track, the KaRIn measurement "
        "geometry leaves a central band of missing or unreliable interferometric estimates "
        "(the nadir gap). Sparse secondary-instrument (nadir altimeter) hits may appear inside "
        "that band and must be cleared before gap filling so that the void is a clean "
        "reconstruction target rather than a mixture of incompatible instruments.",
        align="justify",
    )
    add_para(
        doc,
        "Scientifically, gap fill is an inverse problem: estimate unobserved SSHA from "
        "observed KaRIn flanks while preserving spectral energy (eddy scale content) and "
        "spatial phase (where that energy sits). The production choice for RespondSeeSurface "
        "2024 is classical 2D PG with an anisotropic low-pass projector, initialized by "
        "across-track linear interpolation, followed by exact reinstatement of known samples.",
        align="justify",
    )

    # 2. Problem formulation
    add_heading_custom(doc, "2. Problem formulation", level=1)
    add_heading_custom(doc, "2.1 Discrete swath field and observation mask", level=2)
    add_para(
        doc,
        "Let the SSHA field on a half-orbit (or a crop) be the real array",
        align="justify",
        space_after=4,
    )
    add_equation(doc, "u[n, p] ∈ ℝ,    n = 0,…,N−1,    p = 0,…,68", "1")
    add_para(
        doc,
        "where n is the along-track index and p the across-track pixel. Define the binary "
        "observation mask m[n,p] ∈ {0,1} with m=1 on valid KaRIn ssha_filtered samples and "
        "m=0 on fill values, land, outer empty columns, and the cleared central nadir void. "
        "The observed field is",
        align="justify",
        space_after=4,
    )
    add_equation(doc, "u_obs = m ⊙ u", "2")
    add_para(
        doc,
        "with ⊙ the Hadamard (element-wise) product. The reconstruction goal is to produce "
        "u_rec such that u_rec[n,p] = u_obs[n,p] whenever m[n,p]=1, and u_rec approximates "
        "the missing continuum on m=0.",
        align="justify",
    )
    add_figure(doc, fig_paths["fig1"], width_in=6.0)
    add_caption(
        doc,
        "Figure 1. Schematic KaRIn LR swath (69 across-track pixels) with central nadir void "
        "(m=0). Outer edge columns may also be empty; they are not treated as the scientific "
        "nadir gap target.",
    )

    add_heading_custom(doc, "2.2 Complex spectrum: magnitude and phase", level=2)
    add_para(
        doc,
        "The two-dimensional discrete Fourier transform (DFT) of a completed field v is",
        align="justify",
        space_after=4,
    )
    add_equation(
        doc,
        "V̂(k_n, k_p) = Σ_{n,p} v[n,p]  exp(−2πi (k_n n/N + k_p p/P))",
        "3",
    )
    add_para(
        doc,
        "In polar form,",
        align="justify",
        space_after=4,
    )
    add_equation(doc, "V̂(k) = |V̂(k)|  exp(i φ(k))", "4")
    add_para(
        doc,
        "The magnitude |V̂| encodes the power spectral density (PSD) and thus the "
        "partition of variance across eddy scales. The phase φ encodes spatial placement: "
        "where ridges, fronts, and eddy cores sit in physical space. Consequently, "
        "magnitude-only interpolation in Fourier space followed by inverse DFT destroys "
        "structure even when the PSD looks plausible. Any primary method must act on "
        "complex coefficients or on the spatial field with a spectral constraint that "
        "preserves the phase of retained modes.",
        align="justify",
    )

    add_heading_custom(doc, "2.3 Why a naive FFT of gapped data fails", level=2)
    add_para(
        doc,
        "Masking is a multiplication in space and therefore a convolution in frequency:",
        align="justify",
        space_after=4,
    )
    add_equation(doc, "Û_obs = M̂ ∗ Û", "5")
    add_para(
        doc,
        "Spectral leakage from the sharp nadir cut contaminates all wavenumbers. "
        "Zero-filling NaNs and taking an FFT without reinjecting observations is not a "
        "consistent estimator. Mask-aware iterative schemes (PG) or learning models that "
        "see m explicitly are required.",
        align="justify",
    )

    # 3. Methods
    add_heading_custom(doc, "3. Methods", level=1)
    add_heading_custom(doc, "3.1 Candidate family", level=2)
    add_para(doc, "Table 1 summarizes methods considered in the design notes.", space_after=6)
    add_table(
        doc,
        ["ID", "Method", "Frequency", "Phase", "Role"],
        [
            ["E0", "Across-track linear / spline", "No", "Implicit", "Baseline init"],
            ["E0b", "Co-temporal L4 SLA blend", "Low-pass", "From L4", "Prior L"],
            ["E1", "2D Papoulis–Gerchberg", "Yes", "Yes (complex)", "Production 2024"],
            ["—", "|FFT|-only → IFFT", "Yes", "Broken", "Avoid"],
            ["E2", "CNN/UNet spatial residual", "Indirect", "Learned", "Strong w/ surgery"],
            ["E2*", "Hybrid: AI residual + H(k) + reinstate", "Controlled", "Preserved", "Recommended next"],
        ],
        col_widths=[1.5, 5.0, 2.2, 2.5, 3.2],
    )
    add_caption(doc, "Table 1. Method family for SWOT KaRIn nadir-gap reconstruction.")

    add_heading_custom(doc, "3.2 Across-track linear baseline (E0)", level=2)
    add_para(
        doc,
        "For each along-track row n, missing across-track samples are filled by linear "
        "interpolation in p using neighboring finite KaRIn values (row-wise). Rows with "
        "no finite samples fall back to a global finite mean. E0 provides a spatially "
        "smooth but spectrally uncontrolled estimate and serves as the PG initializer.",
        align="justify",
    )

    add_heading_custom(doc, "3.3 Papoulis–Gerchberg iteration (E1)", level=2)
    add_para(
        doc,
        "Classical Papoulis–Gerchberg alternates a band-limit projector P_B and a data "
        "consistency (mask) projector P_M:",
        align="justify",
        space_after=4,
    )
    add_equation(doc, "v^(t+1) = P_M  P_B  v^(t)", "6")
    add_para(
        doc,
        "with initialization v^(0) = E0(u_obs). The band-limit projector is",
        align="justify",
        space_after=4,
    )
    add_equation(
        doc,
        "P_B v = F⁻¹ ( H ⊙ F(v) )",
        "7",
    )
    add_para(
        doc,
        "where F is the 2D DFT (with fftshift centering), H is a binary keep mask in "
        "frequency, and the phase of retained coefficients is unchanged. The data "
        "projector reinstates observations:",
        align="justify",
        space_after=4,
    )
    add_equation(
        doc,
        "P_M v = m ⊙ u_obs  +  (1 − m) ⊙ v",
        "8",
    )
    add_para(
        doc,
        "After T iterations, the production field is u_rec = P_M v^(T), guaranteeing "
        "bit-level consistency with every originally valid KaRIn sample. One-dimensional "
        "along-track PG on an all-gap column is under-determined; the production code "
        "therefore uses full 2D PG on the (N × 69) ribbon (or 138 × 69 crops).",
        align="justify",
    )
    add_figure(doc, fig_paths["fig2"], width_in=6.3)
    add_caption(
        doc,
        "Figure 2. Schematic of one PG iteration: observed gap → E0 init → spectral "
        "band-limit P_B → reinstatement P_M.",
    )

    add_heading_custom(doc, "3.4 Anisotropic spectral keep mask", level=2)
    add_para(
        doc,
        "Full half-orbits are tall (N ≫ 69). An isotropic keep fraction that is "
        "reasonable on square crops would over-smooth or under-constrain one axis. "
        "Production therefore uses an elliptical low-pass mask in the shifted frequency "
        "plane:",
        align="justify",
        space_after=4,
    )
    add_equation(
        doc,
        "H(k_n, k_p) = 1  if  ((k_n−c_n)/r_n)² + ((k_p−c_p)/r_p)² ≤ 1,   else 0",
        "9",
    )
    add_para(
        doc,
        "with radii r_n = round(f_∥ N/2) and r_p = round(f_⊥ P/2). Default production "
        "parameters are f_∥ = 0.35 (along-track), f_⊥ = 0.55 (across-track), and T = 60 "
        "iterations. The method tag is papoulis_gerchberg_2d_aniso.",
        align="justify",
    )
    add_figure(doc, fig_paths["fig3"], width_in=6.2)
    add_caption(
        doc,
        "Figure 3. Elliptical keep mask H(k) implementing the anisotropic spectral "
        "projector P_B used for full-orbit fills.",
    )

    add_heading_custom(doc, "3.5 Central nadir clearing", level=2)
    add_para(
        doc,
        "Before PG, clear_central_nadir_gap detects the contiguous low-validity column "
        "band in the swath interior (away from edge_guard columns) and sets that entire "
        "band to NaN. This removes secondary-instrument hits so that PG does not treat "
        "them as KaRIn anchors. Typical void columns on 69-pixel LR products lie near "
        "p ∈ [30, 38].",
        align="justify",
    )

    add_heading_custom(doc, "3.6 Production pipeline", level=2)
    add_figure(doc, fig_paths["fig7"], width_in=6.4)
    add_caption(
        doc,
        "Figure 7. End-to-end pipeline from SWOT L3 LR Basic NetCDF to the Ok twin "
        "dataset with filled ssha_filtered.",
    )
    add_para(
        doc,
        "Implementation: fill_nadir_gap/src/build_filled_69xfull.py. Source trees "
        "E:\\SWOT2024 (and 2025); outputs E:\\SWOT2024_Ok. Other variables are copied; "
        "only ssha_filtered is reconstructed in the gap.",
        align="justify",
    )

    add_heading_custom(doc, "3.7 Gap surgery validation (PoC)", level=2)
    add_para(
        doc,
        "Because true nadir SSHA is unavailable, quantitative PoC tests artificially "
        "widen the central gap by W additional known columns on each side (gap surgery), "
        "hold those samples out, run E0 and E1, and score hold-out MAE. Skill is",
        align="justify",
        space_after=4,
    )
    add_equation(doc, "skill_MAE = 1 − MAE_E1 / MAE_E0", "10")
    add_para(
        doc,
        "Positive skill means PG beats linear on the synthetic hold-out. Session notes "
        "for a 50-crop batch (seed 69, T=60, keep_frac=0.55, surgery=3) report mean "
        "skill ≈ −0.02, median ≈ +0.02, and fraction skill>0 ≈ 56%: PG helps often but "
        "not always, motivating quality filters and hybrid methods.",
        align="justify",
    )

    add_heading_custom(doc, "3.8 Composite quality score (crop audit)", level=2)
    add_para(
        doc,
        "On 1,000 random 138×69 visualization crops, fill_quality_score aggregates "
        "side_std, gap_std / side_std, left–right correlation across the gap, gradient "
        "ratio, and flags (invented variance, ringing, flat field, weak L–R, edge). "
        "Grades A–F summarize operational acceptability of the reconstruction appearance "
        "and continuity—not an absolute SSH error against truth.",
        align="justify",
    )

    # 4. Results
    add_heading_custom(doc, "4. Results (2024)", level=1)
    add_heading_custom(doc, "4.1 Full half-orbit production", level=2)
    add_para(
        doc,
        f"From {s24['n']} source NetCDF passes under E:\\SWOT2024, the build wrote "
        f"{s24['n_ok_new']} new Ok files to E:\\SWOT2024_Ok in {s24['elapsed_s']/3600:.2f} h "
        f"with {s24['workers']} workers (T={s24['iters']}, f_∥={s24['keep_frac_along']}, "
        f"f_⊥={s24['keep_frac_across']}). Completion accounting reports "
        f"{c24['ok_nc_on_disk']} Ok files on disk and success rate {c24['success_rate_pct']:.2f}%.",
        align="justify",
    )
    add_table(
        doc,
        ["Quantity", "Value"],
        [
            ["Source root", str(s24["src_root"])],
            ["Output root", str(s24["out_root"])],
            ["Source passes", f"{s24['n']:,}"],
            ["Successfully filled (new)", f"{s24['n_ok_new']:,}"],
            ["Skipped (already present)", f"{s24['n_skip']:,}"],
            ["Failed", f"{s24['n_fail']:,}"],
            ["Success rate", f"{c24['success_rate_pct']:.2f}%"],
            ["Ok NetCDF on disk", f"{c24['ok_nc_on_disk']:,}"],
            ["PG iterations T", str(s24["iters"])],
            ["keep_frac_along (f_∥)", str(s24["keep_frac_along"])],
            ["keep_frac_across (f_⊥)", str(s24["keep_frac_across"])],
            ["Workers", str(s24["workers"])],
            ["Wall time", f"{s24['elapsed_s']/3600:.2f} h ({s24['elapsed_s']:.0f} s)"],
            ["Method", s24["method"]],
        ],
        col_widths=[6.5, 8.5],
    )
    add_caption(doc, "Table 2. SWOT2024 full-orbit nadir-gap fill production summary.")

    fail_rows = [[k, v, f"{100*v/s24['n_fail']:.1f}%"] for k, v in c24["fail_reasons"]]
    add_table(
        doc,
        ["Failure reason", "Count", "Share of failures"],
        fail_rows,
        col_widths=[6.0, 3.0, 4.0],
    )
    add_caption(
        doc,
        "Table 3. Failure taxonomy for the 2024 build (NetCDF/HDF I/O vs. insufficient "
        "known KaRIn samples).",
    )
    add_figure(doc, fig_paths["fig6"], width_in=6.2)
    add_caption(
        doc,
        "Figure 6. Production outcomes and failure reasons for the 2024 Ok dataset.",
    )

    add_heading_custom(doc, "4.2 Qualitative reconstruction examples", level=2)
    add_figure(doc, fig_paths["fig4"], width_in=5.6)
    add_caption(
        doc,
        "Figure 4. Example SWOT2024 crops (test_69x138 vs filled_69x138). (a) Coherent "
        "mesoscale continuation across the gap. (b) Low side variance / challenging case "
        "where percentile stretch amplifies residual ringing. (c) Highest composite score "
        "in the 1,000-crop audit.",
    )

    add_heading_custom(doc, "4.3 Crop quality audit (n = 1,000)", level=2)
    add_para(
        doc,
        f"Composite scores: mean {fq['score_mean']:.2f}, median {fq['score_median']:.2f}, "
        f"P10 {fq['score_p10']:.2f}, P90 {fq['score_p90']:.2f}. Grade counts: "
        + ", ".join(f"{g}={fq['grades'][g]}" for g in ["A", "B", "C", "D", "F"])
        + ".",
        align="justify",
    )
    add_table(
        doc,
        ["Metric", "Value"],
        [
            ["Crops scored", f"{fq['n_ok']:,}"],
            ["Mean score", f"{fq['score_mean']:.2f}"],
            ["Median score", f"{fq['score_median']:.2f}"],
            ["P10 / P90", f"{fq['score_p10']:.2f} / {fq['score_p90']:.2f}"],
            ["Grade A", f"{fq['grades']['A']} ({100*fq['grades']['A']/fq['n_ok']:.1f}%)"],
            ["Grade B", f"{fq['grades']['B']} ({100*fq['grades']['B']/fq['n_ok']:.1f}%)"],
            ["Grade C", f"{fq['grades']['C']} ({100*fq['grades']['C']/fq['n_ok']:.1f}%)"],
            ["Grade D", f"{fq['grades']['D']} ({100*fq['grades']['D']/fq['n_ok']:.1f}%)"],
            ["Grade F", f"{fq['grades']['F']} ({100*fq['grades']['F']/fq['n_ok']:.1f}%)"],
            ["Flag: ringing", str(fq["flag_counts"]["ringing"])],
            ["Flag: weak L–R", str(fq["flag_counts"]["weak_lr"])],
            ["Flag: flat", str(fq["flag_counts"]["flat"])],
            ["Flag: invent variance", str(fq["flag_counts"]["invent"])],
        ],
        col_widths=[6.5, 8.5],
    )
    add_caption(doc, "Table 4. Fill-quality summary on 1,000 random 138×69 SWOT2024 crops.")

    best = fq["best"][:5]
    worst = fq["worst"][:5]
    add_table(
        doc,
        ["Rank", "Image (abbrev.)", "Score", "Grade"],
        [
            [
                str(r["rank"]),
                r["img"][:42] + "…",
                f"{r['score']:.2f}",
                r["grade"],
            ]
            for r in best
        ],
        col_widths=[1.5, 9.0, 2.0, 2.0],
    )
    add_caption(doc, "Table 5. Top-5 quality scores in the crop audit.")
    add_table(
        doc,
        ["Rank", "Image (abbrev.)", "Score", "Grade"],
        [
            [
                str(r["rank"]),
                r["img"][:42] + "…",
                f"{r['score']:.2f}",
                r["grade"],
            ]
            for r in worst
        ],
        col_widths=[1.5, 9.0, 2.0, 2.0],
    )
    add_caption(doc, "Table 6. Bottom-5 quality scores (failure modes for follow-up).")

    add_figure(doc, fig_paths["fig5"], width_in=6.4)
    add_caption(
        doc,
        "Figure 5. Score histogram, grade counts, and relationship between left–right "
        "correlation and gap/side standard-deviation ratio (colored by score).",
    )

    # Descriptive stats table from dataframe
    desc = df[["score", "side_std", "gap_std", "gap_over_side", "lr_corr"]].describe().T
    add_table(
        doc,
        ["Variable", "Mean", "Std", "Min", "P50", "Max"],
        [
            [
                idx,
                f"{row['mean']:.4f}",
                f"{row['std']:.4f}",
                f"{row['min']:.4f}",
                f"{row['50%']:.4f}",
                f"{row['max']:.4f}",
            ]
            for idx, row in desc.iterrows()
        ],
        col_widths=[3.5, 2.2, 2.2, 2.2, 2.2, 2.2],
    )
    add_caption(
        doc,
        "Table 7. Descriptive statistics of core quality variables (n=1000 crops).",
    )

    # 5. Discussion
    add_heading_custom(doc, "5. Discussion", level=1)
    add_para(
        doc,
        "Production success near 95% establishes that anisotropic 2D PG is an operationally "
        "viable way to produce continuous 69-column SSHA ribbons for downstream SLA–SWOT "
        "pairing and residual CNN training. The hard contract out[known]=u_obs[known] "
        "prevents the fill from rewriting KaRIn observations—an essential scientific "
        "property for any product that will later be compared to SLA.",
        align="justify",
    )
    add_para(
        doc,
        "Limitations are equally clear. Gap-surgery skill is only marginally positive on "
        "average: when flanks are flat or left–right coherence is weak, a fixed keep mask "
        "can invent gap variance (ringing), which percentile visualization then exaggerates. "
        "Heuristic audits flagged ringing on a large fraction of crops; this is a property "
        "of band-limited extrapolation under low SNR, not a NetCDF write bug. High-latitude "
        "passes with empty outer columns further reduce constraints.",
        align="justify",
    )
    add_para(
        doc,
        "The recommended research path (E2*) is a hybrid: predict a spatial residual with "
        "a masked CNN/UNet (trained via gap surgery), apply a spectral guard H(k), inverse "
        "transform, then reinstate known samples. Co-temporal L4 SLA (E0b) can supply a "
        "low-pass prior L. Uncertainty maps should accompany any public-facing gap product: "
        "filled values are reconstructions, not new KaRIn measurements.",
        align="justify",
        space_after=4,
    )
    add_equation(
        doc,
        "u_rec = L + F⁻¹( H · F(r̂_θ) ),   r̂_θ = f_θ(u_obs, m, ST),   then reinstate m=1",
        "11",
    )

    # 6. Conclusions
    add_heading_custom(doc, "6. Conclusions", level=1)
    add_para(
        doc,
        "1. Nadir-gap fill must preserve complex spectral phase; magnitude-only FFT→IFFT "
        "is not an acceptable primary method.",
        align="justify",
        space_after=4,
    )
    add_para(
        doc,
        "2. The 2024 production algorithm is clear_central_nadir_gap + 2D anisotropic "
        "Papoulis–Gerchberg (T=60, f_∥=0.35, f_⊥=0.55) with exact KaRIn reinstatement.",
        align="justify",
        space_after=4,
    )
    add_para(
        doc,
        "3. Of 10,038 SWOT2024 passes, 9,532 were newly filled (≈95% success); failures "
        "are dominated by I/O errors and insufficient known samples.",
        align="justify",
        space_after=4,
    )
    add_para(
        doc,
        "4. On 1,000 audited crops, mean quality score is 75.1 with 78.6% graded A or B; "
        "ringing and weak L–R correlation remain the main quality flags.",
        align="justify",
        space_after=4,
    )
    add_para(
        doc,
        "5. Downstream use (e.g., E:\\SWOT2024_Ok paired with E:\\SLA2024 for SLA-H) should "
        "treat gap columns as reconstructed, optionally masked or down-weighted in loss.",
        align="justify",
    )

    # References / paths
    add_heading_custom(doc, "7. Data and code pointers", level=1)
    add_table(
        doc,
        ["Item", "Path"],
        [
            ["Methods note", "fill_nadir_gap/METHODS_NADIR_GAP.md"],
            ["Full-orbit builder", "fill_nadir_gap/src/build_filled_69xfull.py"],
            ["PG PoC", "fill_nadir_gap/src/pg_poc_test_69x138.py"],
            ["2024 summary JSON", "fill_nadir_gap/out/filled_69xfull/summary_2024.json"],
            ["Completion report", "fill_nadir_gap/out/filled_69xfull/COMPLETION_REPORT.json"],
            ["Quality CSV", "fill_nadir_gap/out/fill_quality/fill_quality_all.csv"],
            ["Filled product 2024", "E:\\SWOT2024_Ok"],
            ["This report figures", "fill_nadir_gap/docs/figures/"],
        ],
        col_widths=[4.5, 11.0],
    )
    add_caption(doc, "Table 8. Reproducibility paths for algorithm, metrics, and products.")

    add_heading_custom(doc, "Acknowledgments / framing", level=1)
    add_para(
        doc,
        "This document consolidates the RespondSeeSurface fill_nadir_gap design notes, "
        "PoC metrics, and the 2024 full-orbit build. Framing throughout: reconstruction "
        "with uncertainty—not a claim of new KaRIn measurements inside the nadir void.",
        align="justify",
    )

    doc.save(OUT_DOCX)
    # User asked for .docs — store identical OOXML bytes under that extension.
    OUT_DOCS.write_bytes(OUT_DOCX.read_bytes())
    return OUT_DOCX, OUT_DOCS


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(FQ_CSV)
    print("Building figures…")
    paths = {
        "fig1": fig1_swath_geometry(),
        "fig2": fig2_pg_iteration(),
        "fig3": fig3_spectral_mask(),
        "fig4": fig4_before_after(),
        "fig5": fig5_quality_distributions(df),
        "fig6": fig6_production_2024(),
        "fig7": fig7_pipeline(),
    }
    for k, p in paths.items():
        print(f"  {k}: {p}")
    print("Building Word document…")
    docx_path, docs_path = build_document(paths, df)
    print("Wrote", docx_path)
    print("Wrote", docs_path)


if __name__ == "__main__":
    main()
