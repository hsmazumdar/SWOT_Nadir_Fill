@echo off
setlocal
rem Refresh GitHub_mirror from fill_nadir_gap\docs (+ key method/result files).
set "MIRROR=%~dp0.."
for %%I in ("%MIRROR%") do set "MIRROR=%%~fI"
set "ROOT=%MIRROR%\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "DOCS=%ROOT%\docs"

if not exist "%DOCS%\OnNadirGapFilling.docx" (
  echo ERROR: missing "%DOCS%\OnNadirGapFilling.docx"
  echo Run: python "%DOCS%\build_OnNadirGapFilling_report.py"
  exit /b 1
)

mkdir "%MIRROR%\figures" 2>nul
mkdir "%MIRROR%\methods" 2>nul
mkdir "%MIRROR%\results" 2>nul
mkdir "%MIRROR%\scripts" 2>nul

copy /Y "%DOCS%\OnNadirGapFilling.docx" "%MIRROR%\OnNadirGapFilling.docx" >nul
copy /Y "%DOCS%\figures\*.png" "%MIRROR%\figures\" >nul
copy /Y "%DOCS%\build_OnNadirGapFilling_report.py" "%MIRROR%\scripts\build_OnNadirGapFilling_report.py" >nul
if exist "%ROOT%\METHODS_NADIR_GAP.md" copy /Y "%ROOT%\METHODS_NADIR_GAP.md" "%MIRROR%\methods\METHODS_NADIR_GAP.md" >nul
if exist "%ROOT%\FILLED_69XFULL.md" copy /Y "%ROOT%\FILLED_69XFULL.md" "%MIRROR%\methods\FILLED_69XFULL.md" >nul
if exist "%ROOT%\out\filled_69xfull\summary_2024.json" copy /Y "%ROOT%\out\filled_69xfull\summary_2024.json" "%MIRROR%\results\summary_2024.json" >nul
if exist "%ROOT%\out\filled_69xfull\COMPLETION_REPORT.json" copy /Y "%ROOT%\out\filled_69xfull\COMPLETION_REPORT.json" "%MIRROR%\results\COMPLETION_REPORT.json" >nul
if exist "%ROOT%\out\fill_quality\fill_quality_summary.json" copy /Y "%ROOT%\out\fill_quality\fill_quality_summary.json" "%MIRROR%\results\fill_quality_summary.json" >nul

echo Synced GitHub_mirror from docs:
echo   %MIRROR%
dir /b "%MIRROR%\OnNadirGapFilling.docx"
dir /b "%MIRROR%\figures\*.png"
exit /b 0
