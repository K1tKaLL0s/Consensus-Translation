$ErrorActionPreference = "Stop"

$python = "E:\Ana\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

$root = Get-Location
$env:PYTHONPATH = Join-Path $root "src"

& powershell -ExecutionPolicy Bypass -File ".\build_desktop_qt.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$version = Get-Date -Format "yyyy.MM.dd"
$releaseArgs = @(
    "-m",
    "consensus_translation.agent_release",
    "--version",
    $version,
    "--channel",
    "portable",
    "--license-profile",
    "commercial-safe"
)
$standardInstaller = Join-Path $root "release\ConsensusTranslationAgent-Setup-standard.exe"
if (Test-Path -LiteralPath $standardInstaller) {
    $releaseArgs += @("--installer-path", $standardInstaller)
}
& $python @releaseArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
