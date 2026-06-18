# Usage:
#   powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Channel standard
#   powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Channel full -RuntimePayload 'E:\Cn-Jp Translate\.runtime'

param(
    [ValidateSet("standard", "full")]
    [string]$Channel = "standard",
    [string]$RuntimePayload,
    [string]$AppPayload = "dist\ConsensusTranslationAgent",
    [string]$OutputDir = "release",
    [string]$Version = (Get-Date -Format "yyyy.MM.dd")
)

$ErrorActionPreference = "Stop"

$root = (Get-Location).Path

function Find-InnoCompiler {
    $candidatesC = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidatesC) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $candidatesE = @(
        "E:\Cn-Jp Translate\.runtime\InnoSetup6\ISCC.exe",
        "E:\Inno Setup 6\ISCC.exe",
        "E:\Tools\Inno Setup 6\ISCC.exe",
        "E:\Antigravity\resources\app\node_modules\innosetup\bin\ISCC.exe"
    )
    foreach ($candidate in $candidatesE) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $pathCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($null -ne $pathCommand) {
        return $pathCommand.Source
    }

    return $null
}

function Resolve-InWorkspacePath {
    param(
        [string]$PathText,
        [bool]$MustExist = $true
    )

    if ([System.IO.Path]::IsPathRooted($PathText)) {
        $path = [System.IO.Path]::GetFullPath($PathText)
    } else {
        $path = [System.IO.Path]::GetFullPath((Join-Path $root $PathText))
    }
    if ($MustExist -and -not (Test-Path -LiteralPath $path)) {
        throw "Required path does not exist: $path"
    }
    return $path
}

$iscc = Find-InnoCompiler
if ($null -eq $iscc) {
    Write-Host "Inno Setup compiler ISCC.exe was not found."
    Write-Host "Search order checked C:\ first, then E:\."
    Write-Host "Install Inno Setup 6 to E:\Cn-Jp Translate\.runtime\InnoSetup6 or provide ISCC.exe on PATH."
    exit 2
}

$appPayloadPath = Resolve-InWorkspacePath -PathText $AppPayload -MustExist $true
$outputPath = Resolve-InWorkspacePath -PathText $OutputDir -MustExist $false
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

$scriptPath = Resolve-InWorkspacePath -PathText "packaging\installer\ConsensusTranslationAgent.iss" -MustExist $true
$arguments = @(
    "/Qp",
    "/DProjectRoot=$root",
    "/DAppPayload=$appPayloadPath",
    "/DOutputDir=$outputPath",
    "/DChannel=$Channel",
    "/DAppVersion=$Version"
)

if ($Channel -eq "full") {
    if ([string]::IsNullOrWhiteSpace($RuntimePayload)) {
        throw "Full installer requires -RuntimePayload"
    }
    $runtimePayloadPath = Resolve-InWorkspacePath -PathText $RuntimePayload -MustExist $true
    $arguments += "/DRuntimePayload=$runtimePayloadPath"
} elseif (-not [string]::IsNullOrWhiteSpace($RuntimePayload)) {
    $runtimePayloadPath = Resolve-InWorkspacePath -PathText $RuntimePayload -MustExist $true
    $arguments += "/DRuntimePayload=$runtimePayloadPath"
}

$arguments += $scriptPath

& $iscc @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$installerPath = Join-Path $outputPath "ConsensusTranslationAgent-Setup-$Channel.exe"
if (-not (Test-Path -LiteralPath $installerPath)) {
    throw "Installer was not produced: $installerPath"
}

Write-Host "installer=$installerPath"
Write-Host "iscc=$iscc"
