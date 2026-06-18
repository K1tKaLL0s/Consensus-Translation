[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$RuntimeRoot = (Join-Path $PSScriptRoot ".runtime"),
    [switch]$DownloadTesseract,
    [switch]$DownloadComet,
    [switch]$DownloadModel,
    [string]$OfflineCache = "",
    [switch]$InstalledMode,
    [string]$CondaExe = ""
)

# Usage: .\install_optional_runtimes.ps1 -RuntimeRoot 'E:\Cn-Jp Translate\.runtime' -DownloadTesseract -DownloadComet -DownloadModel -OfflineCache 'E:\cache' -InstalledMode -WhatIf

$ErrorActionPreference = "Stop"

$RuntimeManifest = [ordered]@{
    tesseract_version = "5.5.0.20241111"
    ocr_languages = @("eng", "jpn", "chi_sim", "chi_tra")
    comet_package = "unbabel-comet==2.2.7"
    comet_model = "Unbabel/wmt22-comet-da"
    downloads = @(
        [ordered]@{
            id = "tesseract-installer"
            uri = "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
            filename = "tesseract-ocr-w64-setup-5.5.0.20241111.exe"
            expected_size = 21381872
            expected_sha256 = "F3FC4236425B690C8BE756F35793F77394EE004BE0A6460A440C754D892F68BC"
            target_subdir = "downloads"
        },
        [ordered]@{
            id = "tessdata-eng"
            uri = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata"
            filename = "eng.traineddata"
            expected_size = 4113088
            expected_sha256 = "7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2"
            target_subdir = "Tesseract-OCR\tessdata"
        },
        [ordered]@{
            id = "tessdata-jpn"
            uri = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/jpn.traineddata"
            filename = "jpn.traineddata"
            expected_size = 2471260
            expected_sha256 = "1F5DE9236D2E85F5FDF4B3C500F2D4926F8D9449F28F5394472D9E8D83B91B4D"
            target_subdir = "Tesseract-OCR\tessdata"
        },
        [ordered]@{
            id = "tessdata-chi_sim"
            uri = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/chi_sim.traineddata"
            filename = "chi_sim.traineddata"
            expected_size = 2469156
            expected_sha256 = "A5FCB6F0DB1E1D6D8522F39DB4E848F05984669172E584E8D76B6B3141E1F730"
            target_subdir = "Tesseract-OCR\tessdata"
        },
        [ordered]@{
            id = "tessdata-chi_tra"
            uri = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/chi_tra.traineddata"
            filename = "chi_tra.traineddata"
            expected_size = 2366642
            expected_sha256 = "529C5B5797D64B126065CD55F2BB4C7FD7B15790798091B1FF259941A829330B"
            target_subdir = "Tesseract-OCR\tessdata"
        }
    )
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function Assert-DevelopmentRuntimeRoot {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = Resolve-FullPath $Path
    if (-not $resolved.StartsWith("E:\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Development optional runtimes must be installed on E drive: $resolved"
    }
    return $resolved
}

function Resolve-RuntimeRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][bool]$AllowAnyDrive
    )

    if ($AllowAnyDrive) {
        return Resolve-FullPath $Path
    }
    return Assert-DevelopmentRuntimeRoot $Path
}

function Test-VerifiedFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int64]$ExpectedSize,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -ne $ExpectedSize) {
        return $false
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    return $hash.Equals($ExpectedSha256, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-OfflineCacheCandidate {
    param(
        [Parameter(Mandatory = $true)][string]$FileName,
        [Parameter(Mandatory = $true)][string]$TargetSubdir
    )

    if (-not $OfflineCache) {
        return ""
    }
    $direct = Join-Path $OfflineCache $FileName
    if (Test-Path -LiteralPath $direct) {
        return $direct
    }
    $nested = Join-Path (Join-Path $OfflineCache $TargetSubdir) $FileName
    if (Test-Path -LiteralPath $nested) {
        return $nested
    }
    return ""
}

function Download-VerifiedFile {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Download,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (Test-VerifiedFile -Path $Destination -ExpectedSize $Download.expected_size -ExpectedSha256 $Download.expected_sha256) {
        return $Destination
    }

    $destinationDir = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    $partial = "$Destination.partial"
    if (Test-Path -LiteralPath $partial) {
        Remove-Item -LiteralPath $partial -Force
    }

    $cache = Get-OfflineCacheCandidate -FileName $Download.filename -TargetSubdir $Download.target_subdir
    if ($cache) {
        Copy-Item -LiteralPath $cache -Destination $partial -Force
    } else {
        Invoke-WebRequest -UseBasicParsing -Uri $Download.uri -OutFile $partial -TimeoutSec 900
    }

    if (-not (Test-VerifiedFile -Path $partial -ExpectedSize $Download.expected_size -ExpectedSha256 $Download.expected_sha256)) {
        throw "Downloaded file failed SHA256/size verification: $($Download.id)"
    }
    Move-Item -LiteralPath $partial -Destination $Destination -Force
    return $Destination
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

function Convert-ToRuntimeSettingPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$InstallRoot = ""
    )

    $full = Resolve-FullPath $Path
    if ($InstallRoot) {
        $base = (Resolve-FullPath $InstallRoot).TrimEnd("\", "/")
        $prefix = "$base\"
        if ($full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $full.Substring($prefix.Length).Replace("\", "/")
        }
    }
    return $full
}

function Write-RuntimeSettings {
    param(
        [Parameter(Mandatory = $true)][string]$RuntimeRoot,
        [string]$InstallRoot = ""
    )

    $settings = [ordered]@{
        runtime_root = Convert-ToRuntimeSettingPath -Path $RuntimeRoot -InstallRoot $InstallRoot
        tesseract_command = Convert-ToRuntimeSettingPath -Path (Join-Path $RuntimeRoot "Tesseract-OCR\tesseract.exe") -InstallRoot $InstallRoot
        ocr_language = "eng+jpn+chi_sim+chi_tra"
        comet_command = Convert-ToRuntimeSettingPath -Path (Join-Path $RuntimeRoot "comet-env\Scripts\comet-score.exe") -InstallRoot $InstallRoot
        comet_model = $RuntimeManifest.comet_model
        comet_model_storage_path = Convert-ToRuntimeSettingPath -Path (Join-Path $RuntimeRoot "comet-models") -InstallRoot $InstallRoot
    }
    $settingsPath = Join-Path $RuntimeRoot "runtime-settings.json"
    $settings | ConvertTo-Json | Set-Content -LiteralPath $settingsPath -Encoding UTF8
    Write-Output "optional-runtime-settings=$settingsPath"
}

$noExplicitDownloadSwitch = -not (
    $PSBoundParameters.ContainsKey("DownloadTesseract") -or
    $PSBoundParameters.ContainsKey("DownloadComet") -or
    $PSBoundParameters.ContainsKey("DownloadModel")
)
$shouldDownloadTesseract = if ($noExplicitDownloadSwitch) { $true } else { [bool]$DownloadTesseract }
$shouldDownloadComet = if ($noExplicitDownloadSwitch) { $true } else { [bool]$DownloadComet }
$shouldDownloadModel = if ($noExplicitDownloadSwitch) { $true } else { [bool]$DownloadModel }

$RuntimeRoot = Resolve-RuntimeRoot -Path $RuntimeRoot -AllowAnyDrive ([bool]$InstalledMode)
$downloadsRoot = Join-Path $RuntimeRoot "downloads"
$tesseractRoot = Join-Path $RuntimeRoot "Tesseract-OCR"
$cometEnv = Join-Path $RuntimeRoot "comet-env"
$cometModels = Join-Path $RuntimeRoot "comet-models"
$installRoot = if ($InstalledMode) { Split-Path -Parent $RuntimeRoot } else { "" }

if ($WhatIfPreference) {
    Write-Output "whatif-runtime-root=$RuntimeRoot"
    Write-Output "whatif-download-tesseract=$shouldDownloadTesseract"
    Write-Output "whatif-download-comet=$shouldDownloadComet"
    Write-Output "whatif-download-model=$shouldDownloadModel"
    return
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot, $downloadsRoot | Out-Null

if ($shouldDownloadTesseract) {
    $installerDownload = $RuntimeManifest.downloads | Where-Object { $_.id -eq "tesseract-installer" } | Select-Object -First 1
    $installer = Join-Path $downloadsRoot $installerDownload.filename
    Download-VerifiedFile -Download $installerDownload -Destination $installer | Out-Null

    $sevenZip = Find-7Zip
    New-Item -ItemType Directory -Force -Path $tesseractRoot | Out-Null
    & $sevenZip x -y $installer ("-o" + $tesseractRoot) | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Tesseract archive extraction failed with exit code $LASTEXITCODE"
    }

    foreach ($download in ($RuntimeManifest.downloads | Where-Object { $_.id -like "tessdata-*" })) {
        $destination = Join-Path (Join-Path $RuntimeRoot $download.target_subdir) $download.filename
        Download-VerifiedFile -Download $download -Destination $destination | Out-Null
    }

    $tesseractExe = Join-Path $tesseractRoot "tesseract.exe"
    if (Test-Path -LiteralPath $tesseractExe) {
        & $tesseractExe --version
        if ($LASTEXITCODE -ne 0) {
            throw "Tesseract runtime verification failed"
        }
    }
}

if ($shouldDownloadComet) {
    $conda = Find-Conda $CondaExe
    $cometPython = Join-Path $cometEnv "python.exe"
    if (-not (Test-Path -LiteralPath $cometPython)) {
        & $conda create -y -p $cometEnv python=3.11 pip
        if ($LASTEXITCODE -ne 0) {
            throw "COMET Python environment creation failed"
        }
    }

    & $cometPython -m pip install --upgrade pip
    & $cometPython -m pip install $RuntimeManifest.comet_package
    if ($LASTEXITCODE -ne 0) {
        throw "COMET package installation failed"
    }

    $cometCommand = Join-Path $cometEnv "Scripts\comet-score.exe"
    & $cometCommand --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "COMET command verification failed"
    }
}

if ($shouldDownloadModel) {
    New-Item -ItemType Directory -Force -Path $cometModels | Out-Null
    $env:HF_HOME = Join-Path $cometModels "huggingface"
    $env:TORCH_HOME = Join-Path $cometModels "torch"
    $cometPython = Join-Path $cometEnv "python.exe"
    if (-not (Test-Path -LiteralPath $cometPython)) {
        throw "COMET Python is missing; run with -DownloadComet before -DownloadModel"
    }
    $downloadCode = @"
from comet import download_model
print(download_model("$($RuntimeManifest.comet_model)", saving_directory=r"$cometModels"))
"@
    & $cometPython -c $downloadCode
    if ($LASTEXITCODE -ne 0) {
        throw "COMET model download failed"
    }
}

Write-RuntimeSettings -RuntimeRoot $RuntimeRoot -InstallRoot $installRoot
