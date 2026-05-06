param(
    [string]$AppPath = "app.py"
)

$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 5) {
    throw "PowerShell 5.1 or newer is required."
}

try {
    $pyVersion = (& python --version 2>&1)
} catch {
    throw "Python is not available on PATH."
}

if ($pyVersion -notmatch "Python\s+3\.") {
    throw "Python 3 is required. Found: $pyVersion"
}

$importCheck = @'
import importlib
import sys

required = ["streamlit", "pydantic", "rapidfuzz", "docx", "yaml"]
missing = [name for name in required if importlib.util.find_spec(name) is None]

if missing:
    raise SystemExit("Missing dependencies: " + ", ".join(missing))

print("Dependency check passed.")
'@

& python -c $importCheck
if (-not $?) {
    throw "Dependency import check failed."
}

if (-not (Test-Path -LiteralPath $AppPath)) {
    throw "Streamlit app file not found: $AppPath"
}

& python -m streamlit run $AppPath
