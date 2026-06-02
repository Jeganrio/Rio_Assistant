param(
    [switch]$NoDeps,
    [switch]$NoDesktopShortcut,
    [switch]$NoStartMenuShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$InitDb = Join-Path $ProjectRoot "scripts\init_db.py"
$Launcher = Join-Path $ProjectRoot "desktop\cuby_desktop.py"

if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Missing desktop launcher: $Launcher"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating local virtual environment..."
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & py -3 -m venv (Join-Path $ProjectRoot "venv")
    } else {
        & python -m venv (Join-Path $ProjectRoot "venv")
    }
}

if (-not $NoDeps) {
    Write-Host "Installing desktop dependencies..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r $Requirements
    if (Test-Path -LiteralPath $InitDb) {
        & $VenvPython $InitDb
    }
}

$InstallDir = Join-Path $env:LOCALAPPDATA "CUBY Assistant"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$LauncherCmd = Join-Path $InstallDir "CUBY Assistant.cmd"
$LauncherLines = @(
    "@echo off",
    "cd /d `"$ProjectRoot`"",
    "set CUBY_CLOUD=0",
    "set SERVER_HOST=127.0.0.1",
    "call `"venv\Scripts\activate.bat`"",
    "python `"desktop\cuby_desktop.py`""
)
Set-Content -LiteralPath $LauncherCmd -Value $LauncherLines -Encoding ASCII

function New-CubyShortcut {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $LauncherCmd
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "Launch CUBY local desktop assistant"
    $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
    $Shortcut.Save()
}

if (-not $NoDesktopShortcut) {
    $DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "CUBY Assistant.lnk"
    New-CubyShortcut -Path $DesktopShortcut
    Write-Host "Desktop shortcut created: $DesktopShortcut"
}

if (-not $NoStartMenuShortcut) {
    $Programs = [Environment]::GetFolderPath("Programs")
    $StartMenuShortcut = Join-Path $Programs "CUBY Assistant.lnk"
    New-CubyShortcut -Path $StartMenuShortcut
    Write-Host "Start Menu shortcut created: $StartMenuShortcut"
}

Write-Host ""
Write-Host "CUBY desktop launcher installed."
Write-Host "Use the 'CUBY Assistant' shortcut, then press Start AI in the app."
Write-Host "Voice examples: open Spotify, close Spotify, open VS Code, close Chrome, list apps."
