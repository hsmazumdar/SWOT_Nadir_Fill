# GitHub_mirror — supporting package for OnNadirGapFilling.docx

This directory is a **publishable subset** of `fill_nadir_gap` for the nadir-gap
filling technical report. It is safe to push to a public/private GitHub repo.

## Sync

After regenerating `../docs/OnNadirGapFilling.docx`:

```bat
scripts\sync_from_docs.bat
```

## Init a standalone repo (optional)

```bat
cd /d D:\RespondSeeSurface\fill_nadir_gap\GitHub_mirror
git init
git add .
git commit -m "Add OnNadirGapFilling report mirror (docx, figures, 2024 results)"
```

Do not commit SWOT NetCDF or Ok trees into this folder.
