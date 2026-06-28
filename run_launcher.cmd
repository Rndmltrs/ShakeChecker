@echo off
:: ==============================================================================
:: ShakeChecker Launcher
:: ------------------------------------------------------------------------------
:: This is the primary entry point for the ShakeChecker application.
:: 
:: This script acts as a seamless, standard bootstrapper that forwards 
:: execution to the actual PowerShell logic located in: scripts\launcher.ps1
::
:: The core launcher script handles:
::   - Python 3.11+ validation and Virtual Environment (.venv) bootstrapping
::   - Accelerated dependency installation via Astral's `uv`
::   - An interactive development menu (Run, Custom Args, Embedded Terminal)
::   - Code quality suites (ruff, mypy, pytest)
::   - Differential PyInstaller compilation to standalone .exe
::
:: It automatically detects if PowerShell 7 (pwsh) is installed and utilizes it 
:: if available, while safely bypassing local execution policies for the current
:: session only.
:: ==============================================================================
setlocal
set "PS=powershell.exe"
where pwsh >nul 2>&1 && set "PS=pwsh"
%PS% -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launcher.ps1"
