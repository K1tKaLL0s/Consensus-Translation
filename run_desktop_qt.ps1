[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfiguredPython = 'E:\Ana\python.exe'

function Resolve-SourcePython {
    if (Test-Path -LiteralPath $ConfiguredPython) {
        return (Resolve-Path -LiteralPath $ConfiguredPython).Path
    }

    $cCandidates = @(
        'C:\Python313\python.exe',
        'C:\Python312\python.exe',
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe"
    )
    foreach ($candidate in $cCandidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $eCandidates = @(
        'E:\Ana\python.exe',
        'E:\Python313\python.exe',
        'E:\Python312\python.exe'
    )
    foreach ($candidate in $eCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw 'No Python interpreter found. Install Python on C:\ or E:\, or restore E:\Ana\python.exe.'
}

$Python = Resolve-SourcePython
$SourcePath = Join-Path $ProjectRoot 'src'
$QtPackagePath = Join-Path $ProjectRoot '.runtime\python-packages-qt'
$PythonPathEntries = @($SourcePath)
if (Test-Path -LiteralPath $QtPackagePath) {
    $PythonPathEntries += $QtPackagePath
}
if ($env:PYTHONPATH) {
    $PythonPathEntries += $env:PYTHONPATH
}
$env:PYTHONPATH = $PythonPathEntries -join [System.IO.Path]::PathSeparator

& $Python -m consensus_translation.desktop_qt.application @AppArgs
exit $LASTEXITCODE
