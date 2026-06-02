param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$SetupScript = Join-Path $ProjectRoot "desktop\cuby_setup.py"
$ExePath = Join-Path $ProjectRoot "dist\CUBY_Assistant_Setup.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Missing venv Python: $VenvPython. Create venv first or run scripts\install_desktop_app.ps1."
}

if (-not (Test-Path -LiteralPath $SetupScript)) {
    throw "Missing setup script: $SetupScript"
}

if ($Clean) {
    foreach ($Path in @(
        (Join-Path $ProjectRoot "build\CUBY_Assistant_Setup"),
        (Join-Path $ProjectRoot "dist\CUBY_Assistant_Setup.exe"),
        (Join-Path $ProjectRoot "CUBY_Assistant_Setup.spec")
    )) {
        if (Test-Path -LiteralPath $Path) {
            Remove-Item -LiteralPath $Path -Recurse -Force
        }
    }
}

& $VenvPython -m pip install --upgrade pyinstaller
& $VenvPython -m PyInstaller `
    --onefile `
    --noconsole `
    --name CUBY_Assistant_Setup `
    --distpath (Join-Path $ProjectRoot "dist") `
    --workpath (Join-Path $ProjectRoot "build") `
    --specpath $ProjectRoot `
    $SetupScript

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Build finished but setup EXE was not created: $ExePath"
}

Write-Host "Setup EXE created: $ExePath"
