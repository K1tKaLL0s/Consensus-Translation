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
$installerCandidates = @(
    (Join-Path $root "release\ConsensusTranslationAgent-Setup-standard.exe"),
    (Join-Path $root "release\ConsensusTranslationAgent-Setup-full.exe")
)
foreach ($installer in $installerCandidates) {
    if (Test-Path -LiteralPath $installer) {
        $releaseArgs += @("--installer-path", $installer)
    }
}
& $python @releaseArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
