# Methods — SWOT KaRIn nadir-gap fill

Workspace: `I:\RespondSeeSurface\fill_nadir_gap\`  
Sources on disk: `docs\DESIGN_SWOT_FFT_AI_GAPFILL_CSharp.md`, `docs\FftDesignPaper.docx`,
`docs\SWOT_Nadir-Gap_ReconstructionVer*.docx`, sibling `preprocess_swot_sla_match\`.

Scientific framing: reconstruction with uncertainty — **not** a new KaRIn measurement in the gap.

---

## 1. Problem

Swath field \(u[n,p]\) with \(p=0\ldots68\) (69 across-track pixels), \(n\) along-track.  
Mask \(m[n,p]=0\) on nadir void (and fill/land); \(m=1\) where KaRIn `ssha_filtered` is valid.

Goal: estimate \(u_{\mathrm{rec}}\) on \(m=0\), preserving **both** spectral energy (frequency)
and spatial placement (**phase**).

Complex DFT:

\[
\hat U(k)=|\hat U(k)|\,e^{i\phi(k)}
\]

Magnitude → PSD / eddy energy; phase → where that energy sits. Magnitude-only
interpolation then IFFT is **not** acceptable as a primary method.

---

## 2. Candidate methods

| # | Method | Freq | Phase | Role |
|---|--------|------|-------|------|
| E0 | Across-track linear / spline | No | Implicit | Baseline |
| E0b | Blend co-temporal L4 SLA into gap | Low-pass | From L4 | Prior / \(\mathcal{L}\) |
| E1 | **Papoulis–Gerchberg** (band-limit ↔ reinstate) | Yes | Yes (complex) | Classical PoC |
| — | \|FFT\|-only interpolate → IFFT | Yes | **Broken** | Avoid |
| E1b | Complex coeff inpainting (\|\·\| + \(\arg\)) | Yes | If loss is complex | Hard |
| E2 | CNN/UNet residual in space + mask | Indirect | Learned | Strong with gap surgery |
| **E2\*** | **Hybrid: space residual AI + \(H(k)\) + IFFT + reinstate** | Controlled | Preserved | **Recommended** |

### 2.1 Why naive FFT on gaps fails

\(u_{\mathrm{obs}}=m\odot u\) ⇒ \(\hat U_{\mathrm{obs}}=\hat M*\hat U\) (leakage).  
Do not FFT raw NaNs. Use mask-aware PG or AI that sees \(m\).

### 2.2 Papoulis–Gerchberg (E1)

\[
v^{(t+1)}=\mathcal{P}_M\,\mathcal{P}_B\,v^{(t)}
\]

- \(\mathcal{P}_B\): 2D FFT → keep band \(H(k_n,k_p)\) → IFFT (phase of kept coeffs unchanged)  
- \(\mathcal{P}_M\): replace known samples with observations  

Pure 1D along-track PG on an all-gap column fails; use **2D** on the \(138\times69\) strip
(or full pass). Init with across-track linear fill.

### 2.3 Hybrid (best overall — design paper)

\[
u_{\mathrm{rec}}
=\mathcal{L}
+\mathcal{F}^{-1}\big(H\cdot\mathcal{F}(\hat r_\theta)\big),
\quad
\hat r_\theta=f_\theta(u_{\mathrm{obs}},m,\mathrm{ST})
\]

Then reinstate \(m=1\). Prefer spatial residual AI over magnitude-only spectral heads
(design note: phase errors from coefficient-only AI).

Train with **gap surgery**: artificially widen gap on valid sides → hold-out labels →
apply to true nadir at inference.

---

## 3. Recommendation

1. **Now:** E0 vs **E1 (2D PG)** on `test_69x138` float crops (script below).  
2. **Next:** E0b SLA prior via `preprocess_swot_sla_match`.  
3. **Then:** E2\* hybrid AI + spectral guard \(H(k)\) + uncertainty.  
4. **Never** lead with magnitude-only FFT→IFFT.

Validation: gap MAE/RMSE on synthetic hold-outs, PSD ratio gate, gradient/SSIM
(phase-sensitive structure) — not PSD alone.

---

## 4. PoC script (this workspace)

```bat
cd /d I:\RespondSeeSurface\fill_nadir_gap
run_pg_poc.bat
run_pg_poc.bat --index 1 --iters 40
```

`src\pg_poc_test_69x138.py` reloads float \(138\times69\) from global SWOT via
`test_69x138\manifest.csv` (PNGs are viz-only), runs E0 + E1, optional gap-surgery
MAE, writes `out\pg_poc\`.

Global SWOT dependency: see `DEPENDENCIES.txt`.
