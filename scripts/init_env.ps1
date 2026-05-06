[CmdletBinding()]
param(
    [string]$PythonExe = "python",
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$requirementsPath = Join-Path $repoRoot "requirements.txt"

if (-not (Test-Path -LiteralPath $requirementsPath)) {
    throw "requirements.txt not found at: $requirementsPath"
}

try {
    $null = & $PythonExe --version
} catch {
    throw "Python executable '$PythonExe' is not available in PATH."
}

try {
    & $PythonExe -m pip --version | Out-Null
} catch {
    throw "pip is not available for '$PythonExe'."
}

Write-Host "Python check: OK"
Write-Host "pip check: OK"
Write-Host "Requirements file: $requirementsPath"

$imports = @("streamlit", "pydantic", "rapidfuzz", "docx", "yaml", "requests", "transformers", "sentencepiece", "torch")
$missing = @()

foreach ($moduleName in $imports) {
    $exitCode = 0
    & $PythonExe -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$moduleName') else 1)" *> $null
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $missing += $moduleName
    }
}

if ($missing.Count -eq 0) {
    Write-Host "Dependency import checks: OK"
} else {
    Write-Warning ("Missing Python modules: " + ($missing -join ", "))
    if ($Install) {
        Write-Host "Installing dependencies from requirements.txt ..."
        & $PythonExe -m pip install -r $requirementsPath
    } else {
        Write-Host "Run with -Install to install missing dependencies."
    }
}

Write-Host "Environment initialization checks complete."
