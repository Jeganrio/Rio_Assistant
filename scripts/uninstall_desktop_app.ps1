Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "CUBY Assistant"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "CUBY Assistant.lnk"
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "CUBY Assistant.lnk"

foreach ($Path in @($DesktopShortcut, $StartMenuShortcut)) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force
        Write-Host "Removed: $Path"
    }
}

if (Test-Path -LiteralPath $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
    Write-Host "Removed: $InstallDir"
}

Write-Host "CUBY desktop launcher uninstalled. Project files were not deleted."
