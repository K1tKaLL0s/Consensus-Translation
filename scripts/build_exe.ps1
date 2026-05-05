param(
    [string]$ExeName = "CnJpTranslateDesktop",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if ($Clean) {
    foreach ($path in @("build", "dist", "$ExeName.spec")) {
        $target = Join-Path $ProjectRoot $path
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
    }
}

$iconPath = Join-Path $ProjectRoot "assets/icons/app_placeholder.ico"
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Missing icon: $iconPath"
}

$mainPath = Join-Path $ProjectRoot "src/ui/pyqt_app/main_window.py"
if (-not (Test-Path -LiteralPath $mainPath)) {
    throw "Missing entrypoint: $mainPath"
}

& python -m PyInstaller --noconfirm --onefile --windowed --name $ExeName --icon $iconPath $mainPath

$exePath = Join-Path $ProjectRoot "dist/$ExeName.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Build output missing: $exePath"
}

"EXE built: $exePath"
