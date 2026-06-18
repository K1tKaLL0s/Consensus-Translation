$ErrorActionPreference = "Stop"

$python = "E:\Ana\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$env:PYTHONPATH = Join-Path (Get-Location) "src"
& $python -m consensus_translation.agent_lexicon_migration @args
