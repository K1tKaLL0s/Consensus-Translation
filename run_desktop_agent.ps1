$ErrorActionPreference = "Stop"

$python = "E:\Ana\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$env:PYTHONPATH = Join-Path (Get-Location) "src"
& $python -m consensus_translation.desktop_agent_app
