param(
    [string]$AppPath = "app.py"
)

$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 5) {
    throw "PowerShell 5.1 or newer is required."
}

$importCheck = @'
from importlib.util import find_spec
import sys

required = ["streamlit", "pydantic", "rapidfuzz", "docx", "yaml"]
missing = [name for name in required if find_spec(name) is None]

if missing:
    raise SystemExit("Missing dependencies: " + ", ".join(missing))

print("deps-ok")
'@

$pythonCandidates = @()

try {
    $wherePython = (& where.exe python 2>$null)
    foreach ($candidate in $wherePython) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            if ($pythonCandidates -notcontains $candidate) {
                $pythonCandidates += $candidate
            }
        }
    }
} catch {
}

if ($pythonCandidates.Count -eq 0) {
    throw "Python is not available on PATH."
}

$selectedPython = $null

foreach ($candidate in $pythonCandidates) {
    if ($candidate -like "*\\WindowsApps\\python.exe") {
        continue
    }

    try {
        $pyVersion = (& $candidate --version 2>&1)
    } catch {
        continue
    }

    if ($pyVersion -notmatch "Python\s+3\.") {
        continue
    }

    try {
        $importCheckOutput = $importCheck | & $candidate - 2>&1
    } catch {
        continue
    }

    if ($LASTEXITCODE -eq 0 -and ($importCheckOutput -join "`n").Trim() -eq "deps-ok") {
        $selectedPython = $candidate
        "deps-ok"
        break
    }
}

if (-not $selectedPython) {
    throw "Dependency import check failed."
}

if (-not (Test-Path -LiteralPath $AppPath)) {
    throw "Streamlit app file not found: $AppPath"
}

& $selectedPython -m streamlit run $AppPath
