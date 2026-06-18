$ErrorActionPreference = "Stop"

$python = "E:\Ana\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$root = Get-Location
$env:PYTHONPATH = Join-Path $root "src"

& powershell -ExecutionPolicy Bypass -File ".\build_desktop_agent.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$version = Get-Date -Format "yyyy.MM.dd"
& $python -m consensus_translation.agent_release --version $version --channel portable
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
