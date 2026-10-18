# Start the PowerTune dash emulator (and optionally the fake ME442 data).
#   .\run-emulator.ps1               dash + fake ECU at idle
#   .\run-emulator.ps1 -Mode sweep   dash + RPM sweep
#   .\run-emulator.ps1 -NoData       dash only
param([ValidateSet("idle", "sweep", "drive")][string]$Mode = "idle", [switch]$NoData)

$qt   = "$env:USERPROFILE\Qt\5.15.2\mingw81_64"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe  = "$here\build\release\PowertuneQMLGui.exe"
if (-not (Test-Path $exe)) { Write-Host "Not built yet - run .\build.ps1 first"; exit 1 }

# Use the Qt install directly instead of copying its DLLs next to the exe.
$env:PATH             = "$qt\bin;$env:USERPROFILE\Qt\Tools\mingw810_64\bin;$env:PATH"
$env:QT_PLUGIN_PATH   = "$qt\plugins"
$env:QML2_IMPORT_PATH = "$qt\qml"

$dash = Start-Process $exe -WorkingDirectory "$here\build\release" -PassThru
Write-Host "Dash emulator started (pid $($dash.Id)). Data: C:\PowerTune, settings: $env:APPDATA\Power-Tune\PowerTune.ini"
if (-not $NoData) {
    Start-Sleep -Seconds 3
    try { python "$here\fake_me442.py" --mode $Mode } finally { }
}
