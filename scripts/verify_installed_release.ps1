<# Usage:
    powershell -ExecutionPolicy Bypass -File .\scripts\verify_installed_release.ps1 -InstallerPath .\release\ConsensusTranslationAgent-Setup-standard.exe -InstallDir 'E:\Cn-Jp Translate\.acceptance\installed-release'
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,
    [string]$ReportDir = "E:\Cn-Jp Translate\.acceptance\installed-release",
    [switch]$KeepInstalled
)

$ErrorActionPreference = "Stop"
$AppDisplayName = [string]::Concat(
    [char]0x5171,
    [char]0x8BC6,
    [char]0x7FFB,
    [char]0x8BD1,
    " Agent"
)

function Resolve-AbsolutePath {
    param(
        [string]$PathText,
        [bool]$MustExist = $true
    )

    if ([System.IO.Path]::IsPathRooted($PathText)) {
        $path = [System.IO.Path]::GetFullPath($PathText)
    } else {
        $path = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathText))
    }
    if ($MustExist -and -not (Test-Path -LiteralPath $path)) {
        throw "Required path does not exist: $path"
    }
    return $path
}

function Quote-Argument {
    param([string]$Value)
    $escaped = $Value.Replace('"', '\"')
    return '"' + $escaped + '"'
}

function Invoke-HiddenProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$Step
    )

    $argumentLine = ($Arguments | ForEach-Object { Quote-Argument $_ }) -join " "
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $argumentLine `
        -Wait `
        -WindowStyle Hidden `
        -PassThru
    if ($process.ExitCode -ne 0) {
        throw "$Step failed with exit code $($process.ExitCode)"
    }
}

function Get-DesktopShortcutPath {
    $desktop = [Environment]::GetFolderPath('Desktop')
    return Join-Path $desktop ($AppDisplayName + ".lnk")
}

function Get-StartMenuShortcutPath {
    $programs = [Environment]::GetFolderPath('Programs')
    return Join-Path $programs ($AppDisplayName + ".lnk")
}

function Get-UninstallString {
    $roots = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }
        foreach ($item in Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue) {
            $props = Get-ItemProperty -LiteralPath $item.PSPath -ErrorAction SilentlyContinue
            if ($props.DisplayName -eq $AppDisplayName -and $props.UninstallString) {
                return [string]$props.UninstallString
            }
        }
    }
    return ""
}

$installer = Resolve-AbsolutePath -PathText $InstallerPath
$install = Resolve-AbsolutePath -PathText $InstallDir -MustExist $false
$report = Resolve-AbsolutePath -PathText $ReportDir -MustExist $false

if (-not $install.StartsWith("E:\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "InstallDir must be on E: for this acceptance run: $install"
}

New-Item -ItemType Directory -Force -Path $install | Out-Null
New-Item -ItemType Directory -Force -Path $report | Out-Null

$installLog = Join-Path $report "installer.log"
Invoke-HiddenProcess `
    -FilePath $installer `
    -Arguments @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/DIR=$install",
        "/TASKS=desktopicon",
        "/LOG=$installLog"
    ) `
    -Step "installer"

$exe = Join-Path $install "ConsensusTranslationAgent\ConsensusTranslationAgent.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Installed executable missing: $exe"
}

$runtimeRoot = Join-Path $install "runtime"
if (Test-Path -LiteralPath $runtimeRoot) {
    $cometWrapper = Join-Path $runtimeRoot "comet-score.cmd"
    if (-not (Test-Path -LiteralPath $cometWrapper)) {
        throw "Relocatable COMET wrapper missing: $cometWrapper"
    }
    $nonRelocatableLauncher = Join-Path $runtimeRoot "comet-env\Scripts\comet-score.exe"
    if (Test-Path -LiteralPath $nonRelocatableLauncher) {
        throw "Non-relocatable COMET launcher should not be installed: $nonRelocatableLauncher"
    }
}

$dataDir = Join-Path $install "data"
$diagnosticsReport = Join-Path $report "installed-diagnostics.json"
Invoke-HiddenProcess `
    -FilePath $exe `
    -Arguments @(
        "--diagnostics",
        "--diagnostics-mode",
        "installed",
        "--install-root",
        $install,
        "--data-dir",
        $dataDir,
        "--report-json",
        $diagnosticsReport
    ) `
    -Step "installed diagnostics"

$smokeDir = Join-Path $report "local-smoke"
Invoke-HiddenProcess `
    -FilePath $exe `
    -Arguments @(
        "--local-smoke",
        "--acceptance-dir",
        $smokeDir
    ) `
    -Step "installed local smoke"

$desktopShortcut = Get-DesktopShortcutPath
if (-not (Test-Path -LiteralPath $desktopShortcut)) {
    throw "Desktop shortcut missing: $desktopShortcut"
}

$startMenuShortcut = Get-StartMenuShortcutPath
if (-not (Test-Path -LiteralPath $startMenuShortcut)) {
    throw "Start menu shortcut missing: $startMenuShortcut"
}

$shell = New-Object -ComObject WScript.Shell
$desktopLink = $shell.CreateShortcut($desktopShortcut)
if ($desktopLink.TargetPath -ne $exe) {
    throw "Desktop shortcut target mismatch: $($desktopLink.TargetPath)"
}

$uninstallString = Get-UninstallString
if ([string]::IsNullOrWhiteSpace($uninstallString)) {
    throw "UninstallString not found for $AppDisplayName"
}

$uninstaller = Join-Path $install "unins000.exe"
if (-not (Test-Path -LiteralPath $uninstaller)) {
    throw "Uninstaller missing: $uninstaller"
}

$summary = [ordered]@{
    ok = $true
    installer = $installer
    install_dir = $install
    executable = $exe
    diagnostics_report = $diagnosticsReport
    local_smoke_dir = $smokeDir
    desktop_shortcut = $desktopShortcut
    start_menu_shortcut = $startMenuShortcut
    uninstall_string = $uninstallString
    kept_installed = [bool]$KeepInstalled
}
$summaryPath = Join-Path $report "installed-release-verification.json"
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

if (-not $KeepInstalled) {
    Invoke-HiddenProcess `
        -FilePath $uninstaller `
        -Arguments @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") `
        -Step "uninstaller"
}

Write-Host "installed-release-verification=ok"
Write-Host "report=$summaryPath"
