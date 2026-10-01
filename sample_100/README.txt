sample_100 — 100 observed SWOT KaRIn crops

Shape: 138 along-track × 69 across-track
Field: ssha_filtered (metres), float32, NaN = missing
Rows: first 100 entries of the parent test_69x138 manifest
       (cycle, pass, and line_start are in manifest.csv)

Each array is a direct slice of the L3 pass
  Z:\SWOT2024\cycle_*\SWOT_L3_LR_SSH_Basic_*.nc
at that line_start. The nadir void is still in the array; the demo clears it.

From GitHub_mirror:

  python scripts\build_sample_100.py --swot-root Z:\SWOT2024
  python scripts\run_pg_demo.py

Requires numpy, netCDF4 (build only), and Pillow (demo panels).
