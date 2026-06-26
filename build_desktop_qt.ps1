$ErrorActionPreference = "Stop"

$root = Get-Location
$srcPath = Join-Path $root "src"
$qtPackages = Join-Path $root ".runtime\python-packages-qt"
$pyInstallerCache = Join-Path $root ".runtime\pyinstaller-cache"
New-Item -ItemType Directory -Force -Path $pyInstallerCache | Out-Null
$env:PYINSTALLER_CONFIG_DIR = $pyInstallerCache

$pythonPathItems = @($srcPath)
if (Test-Path -LiteralPath $qtPackages) {
    $pythonPathItems += $qtPackages
}
$env:PYTHONPATH = ($pythonPathItems -join [System.IO.Path]::PathSeparator)

$pythonCandidates = @(
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "E:\Ana\python.exe",
    "python"
)

function Test-PythonCandidate {
    param([string]$Candidate)

    if ($Candidate -eq "python") {
        $command = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $command) {
            return $false
        }
    } elseif (-not (Test-Path -LiteralPath $Candidate)) {
        return $false
    }

    $probe = "import importlib.util, sys; missing=[name for name in ('PyInstaller','PySide6') if importlib.util.find_spec(name) is None]; print(';'.join(missing)); sys.exit(1 if missing else 0)"
    & $Candidate -c $probe *> $null
    return $LASTEXITCODE -eq 0
}

$python = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-PythonCandidate -Candidate $candidate) {
        $python = $candidate
        break
    }
}

if ($null -eq $python) {
    Write-Host "Qt desktop packaging dependencies are missing."
    Write-Host "Install PyInstaller and PySide6, for example:"
    Write-Host "  E:\Ana\python.exe -m pip install -r requirements-desktop.txt"
    Write-Host "  E:\Ana\python.exe -m pip install -r requirements-qt.txt --target .runtime\python-packages-qt"
    exit 2
}

if ($python -eq "python") {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $pythonExePath = $pythonCommand.Source
} else {
    $pythonExePath = $python
}
$pythonRoot = Split-Path -Parent $pythonExePath
$pythonLibraryBin = Join-Path $pythonRoot "Library\bin"
if (Test-Path -LiteralPath $pythonLibraryBin) {
    $env:PATH = $pythonLibraryBin + [System.IO.Path]::PathSeparator + $env:PATH
}

& $python -m consensus_translation.agent_packaging --variant qt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Install Qt desktop packaging dependencies with:"
    Write-Host "  $python -m pip install -r requirements-desktop.txt"
    Write-Host "  $python -m pip install -r requirements-qt.txt --target .runtime\python-packages-qt"
    exit $LASTEXITCODE
}

& $python -m PyInstaller "packaging\desktop_agent_qt.spec" --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Qt desktop build complete: dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe"
