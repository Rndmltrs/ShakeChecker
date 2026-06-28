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
:: Architecture Philosophy:
:: Rather than distributing compiled PyInstaller `.exe` files (which are highly
:: prone to false-positive Antivirus blocks and registry pollution), this project
:: utilizes a source-based PowerShell bootstrapper. This guarantees open-source
:: transparency and achieves 100% Antivirus compliance natively.
:: 
:: It keeps your host machine clean by sandboxing all executable dependencies 
:: strictly into a local `.venv` folder, preventing System PATH or Registry 
:: pollution. (Note: Like all modern package managers, `uv` will safely cache 
:: downloaded wheels in your `AppData\Local` folder for future speedups).
::
:: It automatically detects if PowerShell 7 (pwsh) is installed and utilizes it 
:: if available, while safely bypassing local execution policies for the current
:: session only.
:: ==============================================================================
setlocal
set "PS=powershell.exe"
where pwsh >nul 2>&1 && set "PS=pwsh"
%PS% -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launcher.ps1"
