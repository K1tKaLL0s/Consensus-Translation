$ErrorActionPreference = "Stop"

$python = "E:\Ana\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$root = Get-Location
$env:PYTHONPATH = Join-Path $root "src"

& $python -m consensus_translation.agent_packaging
if ($LASTEXITCODE -ne 0) {
    Write-Host "Install desktop packaging dependencies with:"
    Write-Host "  $python -m pip install -r requirements-desktop.txt"
    exit $LASTEXITCODE
}

& $python -m PyInstaller "packaging\desktop_agent.spec" --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Desktop build complete: dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe"
