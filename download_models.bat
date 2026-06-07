@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title ReelSage Model Downloader

rem Force UTF-8 so Chinese progress text never crashes on Windows console
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

echo Using interpreter: %PY%
echo.
"%PY%" download_models.py %*

echo.
pause
