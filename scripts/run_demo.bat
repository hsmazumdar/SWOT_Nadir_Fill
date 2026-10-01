@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title SWOT Nadir Fill

set "PY="
for %%V in (Python313 Python312 Python311 Python310) do (
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\%%V\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\%%V\python.exe"
)
if not defined PY if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
if not defined PY if exist "%ProgramFiles%\Python313\python.exe" set "PY=%ProgramFiles%\Python313\python.exe"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=python"
  )
)

if not defined PY (
  echo ERROR: Python 3 was not found.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)

if not exist "%~dp0..\sample_100\manifest.csv" (
  echo ERROR: sample_100\manifest.csv is missing.
  echo Keep the sample_100 folder next to scripts.
  pause
  exit /b 1
)

"%PY%" -c "import numpy, PIL" >nul 2>&1
if errorlevel 1 (
  echo Installing numpy and Pillow ...
  "%PY%" -m pip install numpy pillow
  if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
  )
)

echo Opening the nadir-fill viewer.
echo Python: %PY%
echo.
"%PY%" "%~dp0nadir_viewer.py"
if errorlevel 1 (
  echo.
  echo The viewer exited with an error.
  pause
  exit /b 1
)
exit /b 0
