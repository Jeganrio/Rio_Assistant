#!/usr/bin/env powershell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Resolve-Path (Join-Path $scriptDir ".."))
python -m pip install -r requirements.txt
Write-Host "Installation complete!"
