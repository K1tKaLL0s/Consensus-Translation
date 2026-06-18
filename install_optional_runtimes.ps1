param(
    [string]$RuntimeRoot = (Join-Path $PSScriptRoot ".runtime"),
    [string]$CondaExe = "",
    [switch]$SkipTesseract,
    [switch]$SkipComet,
    [switch]$SkipCometModel
)

$ErrorActionPreference = "Stop"

function Assert-EDrivePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith("E:\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Optional runtimes must be installed on E: ($resolved)"
    }
    return $resolved
}

function Find-7Zip {
    $candidates = @(
        "C:\Program Files\7-Zip\7z.exe",
        "C:\Program Files (x86)\7-Zip\7z.exe",
        "E:\7-Zip\7z.exe",
        "E:\Tools\7-Zip\7z.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    throw "7-Zip was not found on C: or E:. Install 7-Zip before extracting Tesseract."
}

function Find-Conda {
    param([string]$Configured)

    if ($Configured) {
        if (-not (Test-Path -LiteralPath $Configured)) {
            throw "Configured Conda executable does not exist: $Configured"
        }
        return $Configured
    }
    $candidates = @(
        "C:\Users\27499\miniconda3\Scripts\conda.exe",
        "C:\Users\27499\anaconda3\Scripts\conda.exe",
        "E:\Ana\Scripts\conda.exe",
        "E:\Miniconda3\Scripts\conda.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    throw "Conda was not found on C: or E:."
}

function Download-File {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (Test-Path -LiteralPath $Destination) {
        return
    }
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Destination -TimeoutSec 900
}

$RuntimeRoot = Assert-EDrivePath $RuntimeRoot
$downloads = Join-Path $RuntimeRoot "downloads"
$tesseractRoot = Join-Path $RuntimeRoot "Tesseract-OCR"
$cometEnv = Join-Path $RuntimeRoot "comet-env"
$cometModels = Join-Path $RuntimeRoot "comet-models"
New-Item -ItemType Directory -Force -Path $RuntimeRoot, $downloads | Out-Null

if (-not $SkipTesseract) {
    $installerName = "tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    $installer = Join-Path $downloads $installerName
    Download-File `
        -Uri "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/$installerName" `
        -Destination $installer

    $sevenZip = Find-7Zip
    New-Item -ItemType Directory -Force -Path $tesseractRoot | Out-Null
    & $sevenZip x -y $installer ("-o" + $tesseractRoot) | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Tesseract archive extraction failed with exit code $LASTEXITCODE"
    }

    $tessdata = Join-Path $tesseractRoot "tessdata"
    New-Item -ItemType Directory -Force -Path $tessdata | Out-Null
    foreach ($language in @("eng", "jpn", "chi_sim", "chi_tra")) {
        Download-File `
            -Uri "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/$language.traineddata" `
            -Destination (Join-Path $tessdata "$language.traineddata")
    }

    $tesseractExe = Join-Path $tesseractRoot "tesseract.exe"
    & $tesseractExe --version
    if ($LASTEXITCODE -ne 0) {
        throw "Tesseract runtime verification failed"
    }
}

if (-not $SkipComet) {
    $conda = Find-Conda $CondaExe
    $cometPython = Join-Path $cometEnv "python.exe"
    if (-not (Test-Path -LiteralPath $cometPython)) {
        & $conda create -y -p $cometEnv python=3.11 pip
        if ($LASTEXITCODE -ne 0) {
            throw "COMET Python environment creation failed"
        }
    }

    & $cometPython -m pip install --upgrade pip
    & $cometPython -m pip install "unbabel-comet==2.2.7"
    if ($LASTEXITCODE -ne 0) {
        throw "COMET package installation failed"
    }

    $cometCommand = Join-Path $cometEnv "Scripts\comet-score.exe"
    & $cometCommand --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "COMET command verification failed"
    }

    New-Item -ItemType Directory -Force -Path $cometModels | Out-Null
    $env:HF_HOME = Join-Path $cometModels "huggingface"
    $env:TORCH_HOME = Join-Path $cometModels "torch"
    if (-not $SkipCometModel) {
        $downloadCode = @"
from comet import download_model
print(download_model("Unbabel/wmt22-comet-da", saving_directory=r"$cometModels"))
"@
        & $cometPython -c $downloadCode
        if ($LASTEXITCODE -ne 0) {
            throw "COMET model download failed"
        }
    }
}

$settings = [ordered]@{
    runtime_root = $RuntimeRoot
    tesseract_command = (Join-Path $tesseractRoot "tesseract.exe")
    ocr_language = "jpn+eng"
    comet_command = (Join-Path $cometEnv "Scripts\comet-score.exe")
    comet_model = "Unbabel/wmt22-comet-da"
    comet_model_storage_path = $cometModels
}
$settingsPath = Join-Path $RuntimeRoot "runtime-settings.json"
$settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding UTF8
Write-Output "optional-runtime-settings=$settingsPath"
