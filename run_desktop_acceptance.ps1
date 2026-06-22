param(
    [string]$OutputDir = ".acceptance",
    [string]$ProjectId = "desktop-acceptance",
    [string]$ReportJson = ""
)

$ErrorActionPreference = "Stop"

function Find-Python {
    $candidates = @(
        "C:\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "E:\Ana\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return "python"
}
$python = Find-Python

$root = Get-Location
$env:PYTHONPATH = Join-Path $root "src"

if (-not $ReportJson) {
    $ReportJson = Join-Path $OutputDir "local-acceptance-report.json"
}

& $python -m consensus_translation.agent_acceptance `
    --output-dir $OutputDir `
    --project-id $ProjectId `
    --report-json $ReportJson

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
