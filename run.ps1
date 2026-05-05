[CmdletBinding()]
param(
    [switch]$Init,
    [ValidateSet("web", "desktop", "all")]
    [string]$Mode = "all",
    [switch]$SkipInstall,
    [switch]$SkipDB
)

$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
    return Split-Path -Parent $MyInvocation.PSCommandPath
}

function Get-PythonCommand {
    param(
        [string]$ProjectRoot
    )

    $venvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    return "python"
}

function Invoke-Init {
    param(
        [string]$ProjectRoot,
        [switch]$SkipInstall,
        [switch]$SkipDB
    )

    $venvDir = Join-Path $ProjectRoot "venv"
    if (-not (Test-Path $venvDir)) {
        Write-Host "[init] Creating venv..."
        Push-Location $ProjectRoot
        try {
            python -m venv venv
        }
        finally {
            Pop-Location
        }
    }

    $pythonCmd = Get-PythonCommand -ProjectRoot $ProjectRoot

    if (-not $SkipInstall) {
        Write-Host "[init] Installing dependencies..."
        Push-Location $ProjectRoot
        try {
            & $pythonCmd -m pip install -r requirements.txt
        }
        finally {
            Pop-Location
        }
    }

    if (-not $SkipDB) {
        Write-Host "[init] Bootstrapping MySQL metadata..."
        Push-Location $ProjectRoot
        try {
            if ($pythonCmd -eq "python") {
                python -m src.tools.bootstrap_mysql
            }
            else {
                & $pythonCmd -m src.tools.bootstrap_mysql
            }
        }
        finally {
            Pop-Location
        }
    }
}

function Start-WebApps {
    param(
        [string]$ProjectRoot
    )

    $pythonCmd = Get-PythonCommand -ProjectRoot $ProjectRoot

    $apiCommand = "uvicorn src.api.main:app"
    Write-Host "[run] Starting API on http://127.0.0.1:8000"
    Write-Host ("[run] Command: {0}" -f $apiCommand)
    $apiProc = Start-Process -FilePath $pythonCmd -ArgumentList "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -WorkingDirectory $ProjectRoot -PassThru

    Write-Host "[run] Starting Streamlit on http://127.0.0.1:8501"
    $webProc = Start-Process -FilePath $pythonCmd -ArgumentList "-m", "streamlit", "run", "src/ui/web_app/streamlit_app.py" -WorkingDirectory $ProjectRoot -PassThru

    Write-Host ("[run] API PID={0}, Streamlit PID={1}" -f $apiProc.Id, $webProc.Id)
}

function Start-Desktop {
    param(
        [string]$ProjectRoot
    )

    $pythonCmd = Get-PythonCommand -ProjectRoot $ProjectRoot
    Write-Host "[run] Starting PyQt client..."
    Push-Location $ProjectRoot
    try {
        & $pythonCmd -c "from src.ui.pyqt_app.main_window import run; run()"
    }
    finally {
        Pop-Location
    }
}

$projectRoot = Get-ProjectRoot

if ($Init) {
    Invoke-Init -ProjectRoot $projectRoot -SkipInstall:$SkipInstall -SkipDB:$SkipDB
}

if ($Mode -eq "web" -or $Mode -eq "all") {
    Start-WebApps -ProjectRoot $projectRoot
}

if ($Mode -eq "desktop" -or $Mode -eq "all") {
    Start-Desktop -ProjectRoot $projectRoot
}
