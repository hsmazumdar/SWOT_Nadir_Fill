# filled_69xfull — full half-orbit nadir-gap fill

Source NetCDFs (unchanged):
  E:\SWOT2024\cycle_*\SWOT_L3_LR_SSH_Basic_*.nc
  E:\SWOT2025\cycle_*\SWOT_L3_LR_SSH_Basic_*.nc

Output filled NetCDFs (new dataset):
  E:\SWOT2024_Ok\...
  E:\SWOT2025_Ok\...

Method (same spirit as filled_69x138):
  1. clear central KaRIn nadir gap (drop secondary-instrument hits)
  2. 2D Papoulis–Gerchberg on full (num_lines × 69)
  3. reinstate all known KaRIn samples exactly
  4. write twin NC (ssha_filtered filled; other vars copied)

Run
---
  run_build_filled_69xfull_smoke.bat          # 2+2 passes
  run_build_filled_69xfull.bat --year 2024 --workers 4
  run_build_filled_69xfull.bat --year both --workers 4

Logs: out\filled_69xfull\manifest_YYYY.csv , summary_YYYY.json

~10k passes/year × ~3–4 s ≈ several hours; use --resume to continue.
