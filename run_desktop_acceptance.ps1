param(
    [string]$OutputDir = ".acceptance",
    [string]$ProjectId = "desktop-acceptance",
    [string]$ReportJson = ""
)

$ErrorActionPreference = "Stop"

$python = "E:\Ana\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

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
