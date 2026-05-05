param(
    [string]$ExePath = "dist/CnJpTranslateDesktop.exe",
    [int]$WaitSeconds = 2
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$targetPath = Join-Path $ProjectRoot $ExePath

if (-not (Test-Path -LiteralPath $targetPath)) {
    throw "EXE not found: $targetPath"
}

$process = Start-Process -FilePath $targetPath -PassThru
Start-Sleep -Seconds $WaitSeconds

if ($process.HasExited -and $process.ExitCode -ne 0) {
    throw "EXE exited with code $($process.ExitCode)"
}

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
}
"Smoke test passed"
