# Copy a dash's settings into the emulator's settings files.
# Close the emulator first. The current emulator settings are kept as *.bak.
#   .\load-dash-settings.ps1 [-ConfigDir <folder holding Power-Tune\PowerTune.conf and PowerTuneQML\PowerTuneDash.conf>]
# On the dash those are in /.config (copy them off with scp). Default: ..\dash-files\rootfs\.config
param([string]$ConfigDir = (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\dash-files\rootfs\.config"))
$src  = $ConfigDir
$sets = @(
    @{ From = "$src\Power-Tune\PowerTune.conf";        To = "$env:APPDATA\Power-Tune\PowerTune.ini" },
    @{ From = "$src\PowerTuneQML\PowerTuneDash.conf";  To = "$env:APPDATA\PowerTuneQML\PowerTuneDash.ini" }
)
if (Get-Process PowertuneQMLGui -ErrorAction SilentlyContinue) { Write-Host "Close the emulator first."; exit 1 }
foreach ($s in $sets) {
    New-Item -ItemType Directory -Force (Split-Path $s.To) | Out-Null
    if (Test-Path $s.To) { Copy-Item $s.To "$($s.To).bak" -Force }
    Copy-Item $s.From $s.To -Force
    Write-Host "loaded $($s.To)"
}
