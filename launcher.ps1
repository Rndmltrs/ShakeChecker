# ==============================================================================
# ShakeChecker Development Launcher
# ------------------------------------------------------------------------------
# This script initializes the development environment for ShakeChecker, a
# real‑time Pokémon catch‑probability overlay. It validates Python, activates
# the virtual environment, ensures dependencies are installed, and provides a
# menu for running the app, testing, linting, and building the executable.
# ==============================================================================

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONPYCACHEPREFIX = Join-Path $PSScriptRoot ".pycache"

# ==============================================================================
# ENVIRONMENT BOOTSTRAP
# ==============================================================================
function Invoke-Bootstrap {
    Write-Host "`n  Checking Python..." -ForegroundColor DarkGray

    try {
        $pyVer = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ([version]$pyVer -lt [version]"3.11") {
            Write-Host "`n  Python $pyVer found, but version 3.11+ is required." -ForegroundColor Red
            Pause
            return $false
        }
        Write-Host "  Python $pyVer — OK" -ForegroundColor Green
    }
    catch {
        Write-Host "`n  Python not found in PATH." -ForegroundColor Red
        Pause
        return $false
    }

    if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
        Write-Host "`n  No virtual environment found. A clean installation is required." -ForegroundColor Cyan
        $confirm = Read-Host "  Do you want to create a virtual environment now? (Y/N)"
        if ($confirm -notmatch '^[Yy]') {
            Write-Host "`n  Installation aborted." -ForegroundColor Red
            Pause
            return $false
        }
        Write-Host "`n  Creating virtual environment..." -ForegroundColor Yellow
        try {
            python -m venv .venv
            Write-Host "  Virtual environment created." -ForegroundColor Green
        }
        catch {
            Write-Host "`n  Failed to create virtual environment." -ForegroundColor Red
            Pause
            return $false
        }
    }

    . ".\.venv\Scripts\Activate.ps1"

    $depsCheck = & python -c "import cv2" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n  Missing dependencies detected." -ForegroundColor Cyan
        Write-Host "  Calculating download size..." -ForegroundColor DarkGray
        
        $outFile = Join-Path $env:TEMP "pip_report_$([guid]::NewGuid()).json"
        Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m pip install --dry-run --report - -q -e `".[dev]`"" -WindowStyle Hidden -RedirectStandardOutput $outFile -RedirectStandardError $outFile -Wait
        
        $sizeStr = "unknown size"
        $totalPkgs = 0
        if (Test-Path $outFile) {
            try {
                $jsonStr = Get-Content $outFile -Raw
                if ($jsonStr) {
                    $report = $jsonStr | ConvertFrom-Json
                    if ($report.install) { $totalPkgs = $report.install.Count }
                    $bytes = 0
                    foreach ($pkg in $report.install) {
                        if ($pkg.download_info -and $pkg.download_info.archive_info -and $pkg.download_info.archive_info.size) {
                            $bytes += $pkg.download_info.archive_info.size
                        }
                    }
                    if ($bytes -gt 0) {
                        $mb = [math]::Round($bytes / 1MB, 2)
                        $sizeStr = "~$mb MB"
                    }
                }
            } catch { }
            Remove-Item $outFile -Force -ErrorAction SilentlyContinue
        }

        $confirm = Read-Host "  Do you want to install them now? ($sizeStr) (Y/N)"
        if ($confirm -notmatch '^[Yy]') {
            Write-Host "`n  Installation aborted." -ForegroundColor Red
            Pause
            return $false
        }
        Write-Host ""
        
        try {
            $installLog = Join-Path $env:TEMP "pip_install_$([guid]::NewGuid()).log"
            $procInstall = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m pip install -e `".[dev]`"" -WindowStyle Hidden -RedirectStandardOutput $installLog -RedirectStandardError $installLog -PassThru
            
            $spinners = @('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')
            $i = 0
            try { [Console]::CursorVisible = $false } catch {}
            
            while (-not $procInstall.HasExited) {
                $pctText = ""
                if ($totalPkgs -gt 0 -and (Test-Path $installLog)) {
                    $lines = Get-Content $installLog -ErrorAction SilentlyContinue
                    $collected = @($lines -match '^(Collecting|Requirement already satisfied|Processing|Downloading|Installing collected packages)').Count
                    # Rough heuristic: double the packages because it collects then installs. 
                    $progress = [math]::Min(100, [math]::Floor(($collected / ($totalPkgs * 2)) * 100))
                    if ($progress -gt 99) { $progress = 99 } # hold at 99 until process exits
                    $pctText = " [$progress%]"
                }

                Write-Host "`r  $($spinners[$i]) Installing dependencies$pctText...                " -NoNewline -ForegroundColor Yellow
                $i = ($i + 1) % $spinners.Length
                Start-Sleep -Milliseconds 80
            }
            Write-Host "`r                                                                      `r" -NoNewline
            try { [Console]::CursorVisible = $true } catch {}
            
            if ($procInstall.ExitCode -eq 0) {
                Write-Host "  Dependencies installed. [100%]" -ForegroundColor Green
            } else {
                Write-Host "  Dependency installation failed." -ForegroundColor Red
                Get-Content $installLog | Write-Host -ForegroundColor DarkGray
                Pause
                return $false
            }
            Remove-Item $installLog -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "`n  Dependency installation failed." -ForegroundColor Red
            Pause
            return $false
        }
    }
    else {
        Write-Host "  Dependencies — OK" -ForegroundColor Green
    }

    return $true
}

$ErrorActionPreference = "Continue"
$ready = Invoke-Bootstrap
$ErrorActionPreference = "Stop"
if (-not $ready) { return }

# ==============================================================================
# HEADER
# ==============================================================================
function Show-Header {
    Clear-Host
    Write-Host ""
    Write-Host "    ███████╗██╗  ██╗ █████╗ ██╗  ██╗███████╗ " -ForegroundColor Red
    Write-Host "    ██╔════╝██║  ██║██╔══██╗██║ ██╔╝██╔════╝ " -ForegroundColor Red
    Write-Host "    ███████╗███████║███████║█████═╝ █████╗   " -ForegroundColor Red
    Write-Host "    ╚════██║██╔══██║██╔══██║██╔═██╗ ██╔══╝   " -ForegroundColor DarkGray
    Write-Host "    ███████║██║  ██║██║  ██║██║  ██╗███████╗ " -ForegroundColor White
    Write-Host "    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ " -ForegroundColor White
    Write-Host "          C H E C K E R   V 1 . 2 . 0        " -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "    [Environment: Active]" -ForegroundColor Green
    Write-Host "    ----------------------------------------" -ForegroundColor DarkGray
}

# ==============================================================================
# RUN PYTHON APPLICATION
# ==============================================================================
function Invoke-PythonApp {
    param([string]$ArgsString = "")

    Write-Host "`n  Application running. Press 'q' to terminate.`n" -ForegroundColor DarkGray
    $proc = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "src\app.py $ArgsString" -PassThru -NoNewWindow

    while (-not $proc.HasExited) {
        $key = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        if ($key.Character -eq 'q' -or $key.Character -eq 'Q') {
            Write-Host "`n  Terminating..." -ForegroundColor Yellow
            $proc.Kill()
            break
        }
    }

    Write-Host "`n  Application closed." -ForegroundColor DarkGray
    Pause
}

# ==============================================================================
# GENERIC TASK RUNNER
# ==============================================================================
function Invoke-Task {
    param(
        [string]$Title,
        [scriptblock]$Command
    )

    Write-Host "`n  [>] $Title" -ForegroundColor Magenta
    Write-Host "    $($Command.ToString().Trim())`n" -ForegroundColor DarkGray

    try {
        & $Command
    }
    catch {
        Write-Host "  Task failed." -ForegroundColor Red
    }
}

# ==============================================================================
# MENU
# ==============================================================================
function Show-Menu {
    Show-Header
    Write-Host "  [1] Start Application" -ForegroundColor White
    Write-Host "  [2] Advanced Run (Custom Arguments)" -ForegroundColor Cyan
    Write-Host "  [3] Embedded Terminal" -ForegroundColor White
    Write-Host "  [4] Ruff (Check --fix & Format)" -ForegroundColor Gray
    Write-Host "  [5] mypy" -ForegroundColor Gray
    Write-Host "  [6] pytest" -ForegroundColor Gray
    Write-Host "  [7] Build Application" -ForegroundColor Gray
    Write-Host "  [8] Clean Environment" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [Q] Quit" -ForegroundColor DarkRed
    Write-Host "    ----------------------------------------" -ForegroundColor DarkGray
}

# ==============================================================================
# TERMINAL MODE
# ==============================================================================
function Invoke-Terminal {
    $historyFile = Join-Path $PSScriptRoot "logs/launcher_history.log"
    $cmdHistory = @{}
    $seq = 0

    if (Test-Path $historyFile) {
        foreach ($line in Get-Content $historyFile) {
            if ($line -match '^(.+)\|(\d+)\|(\d+)$') {
                $cmdHistory[$matches[1]] = @{ Count = [int]$matches[2]; Seq = [int]$matches[3] }
                if ([int]$matches[3] -gt $seq) { $seq = [int]$matches[3] }
            }
        }
    }

    while ($true) {
        Clear-Host
        Write-Host "    [ TERMINAL MODE ]" -ForegroundColor Cyan
        Write-Host "    Type 'q' to return | 'h' for history" -ForegroundColor DarkGray
        Write-Host "    ----------------------------------------" -ForegroundColor DarkGray

        $top = $cmdHistory.GetEnumerator() | Sort-Object { $_.Value.Count } -Descending | Select-Object -First 5
        $map = @{}
        $i = 1
        foreach ($c in $top) {
            $lines = $c.Name.Split("`n")
            $firstLine = $lines[0]
            $indicator = if ($lines.Count -gt 1) { "(Multi-line)" } else { "" }
            Write-Host "      [$i] $firstLine$indicator" -ForegroundColor Gray
            $map["$i"] = $c.Name
            $i++
        }

        Write-Host "  ❯ " -NoNewline -ForegroundColor Gray
        Write-Host "(.venv)" -NoNewline -ForegroundColor Green

        # Read first line
        $input = Read-Host " "

        # Capture additional pasted lines (if any)
        while ($Host.UI.RawUI.KeyAvailable) {
            $extra = [Console]::In.ReadLine()
            if ($extra -ne $null) {
                $input += "`n$extra"
            }
        }

        if ([string]::IsNullOrWhiteSpace($input)) { continue }
        if ($input -eq 'q') { break }

        if ($input -eq 'h') {
            Write-Host "`n  Command History" -ForegroundColor Cyan
            $all = $cmdHistory.GetEnumerator() | Sort-Object { $_.Value.Count } -Descending
            $hmap = @{}
            $j = 1
            foreach ($c in $all) {
                $lines = $c.Name.Split("`n")
                $firstLine = $lines[0]
                $indicator = if ($lines.Count -gt 1) { " ↵" } else { "" }
                Write-Host "    [$j] $firstLine$indicator (used $($c.Value.Count) times)" -ForegroundColor Gray
                $hmap["$j"] = $c.Name
                $j++
            }
            $sel = Read-Host "  Select number"
            if ($hmap.ContainsKey($sel)) {
                $input = $hmap[$sel]
            }
            else { continue }
        }
        elseif ($map.ContainsKey($input)) {
            $input = $map[$input]
        }

        $cmd = $input.Trim()
        $seq++
        if (-not $cmdHistory.ContainsKey($cmd)) {
            $cmdHistory[$cmd] = @{ Count = 0; Seq = $seq }
        }
        $cmdHistory[$cmd].Count++
        $cmdHistory[$cmd].Seq = $seq

        if ($cmdHistory.Count -gt 100) {
            $old = $cmdHistory.GetEnumerator() | Sort-Object { $_.Value.Seq } | Select-Object -First ($cmdHistory.Count - 100)
            foreach ($e in $old) { $cmdHistory.Remove($e.Name) }
        }

        $cmdHistory.GetEnumerator() |
        ForEach-Object { "$($_.Name)|$($_.Value.Count)|$($_.Value.Seq)" } |
        Set-Content $historyFile

        try { Invoke-Expression $cmd } catch { Write-Host $_ -ForegroundColor Red }
        Write-Host "`n  (press Enter to continue)" -ForegroundColor DarkGray
        [void][System.Console]::ReadLine()
    }
}

# ==============================================================================
# MAIN LOOP
# ==============================================================================
while ($true) {
    Show-Menu
    $choice = Read-Host "  Select an option"

    switch ($choice) {
        '1' { Invoke-PythonApp }
        '2' {
            Clear-Host
            Write-Host "`n  Advanced Run Mode" -ForegroundColor Cyan
            Write-Host "  ----------------------------------------" -ForegroundColor DarkGray
            Write-Host "  --species <Name>"
            Write-Host "  --status <Status>"
            Write-Host "  --rate <Number>"
            Write-Host "  --image <Path>"
            Write-Host "  --list-windows"
            Write-Host ""
            $args = Read-Host "  Enter arguments"
            if ($args) { Invoke-PythonApp -ArgsString $args }
        }
        '3' {
            Invoke-Terminal 
        }
        '4' {
            Clear-Host
            Invoke-Task "Ruff Check" { ruff check --fix . }
            Invoke-Task "Ruff Format" { ruff format . }
            Pause
        }
        '5' {
            Clear-Host
            Invoke-Task "mypy" { mypy . }
            Pause
        }
        '6' {
            Clear-Host
            Invoke-Task "pytest" { pytest }
            Pause
        }
        '7' {
            Clear-Host
            Write-Host "`n  Build Application" -ForegroundColor Cyan
            Write-Host "  ----------------------------------------" -ForegroundColor DarkGray

            $exe = "dist\ShakeChecker\ShakeChecker.exe"
            $needs = $true

            if (Test-Path $exe) {
                $exeTime = (Get-Item $exe).LastWriteTime
                $paths = @("src", "assets", "calibration.toml", "pyproject.toml", "ShakeChecker.spec")

                foreach ($p in $paths) {
                    if (Test-Path $p) {
                        $changed = Get-ChildItem $p -Recurse -File |
                        Where-Object { $_.LastWriteTime -gt $exeTime -and $_.Extension -ne '.pyc' -and $_.FullName -notmatch '__pycache__' }
                        if ($changed) {
                            $needs = $true
                            break
                        }
                        else { $needs = $false }
                    }
                }
            }

            if (-not $needs) {
                Write-Host "  No changes detected. Build is up to date." -ForegroundColor Green
                Write-Host "  Output: dist/ShakeChecker/" -ForegroundColor Yellow
                Pause
                continue
            }

            Write-Host "`n  Running PyInstaller..." -ForegroundColor Magenta
            try {
                if (Test-Path ".\.venv\Scripts\pyinstaller.exe") {
                    & ".\.venv\Scripts\pyinstaller.exe" --noconfirm ShakeChecker.spec
                }
                else {
                    pyinstaller --noconfirm ShakeChecker.spec
                }
                Write-Host "`n  Build complete!" -ForegroundColor Green
                Write-Host "  Output: dist/ShakeChecker/" -ForegroundColor Yellow
            }
            catch {
                Write-Host "  Build failed." -ForegroundColor Red
            }
            Pause
        }
        '8' {
            Clear-Host
            Write-Host "`n  Cleaning environment..." -ForegroundColor Cyan
            $targets = @("build", "dist", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".pycache")
            foreach ($t in $targets) {
                if (Test-Path $t) {
                    Write-Host "  Removing $t..." -ForegroundColor Gray
                    Remove-Item -Recurse -Force $t
                }
            }
            Write-Host "  Done.`n" -ForegroundColor Green
            Pause
        }
        'q' { exit }
        'Q' { exit }
        default {
            Write-Host "  Invalid option." -ForegroundColor Red
            Start-Sleep -Milliseconds 600
        }
    }
}
