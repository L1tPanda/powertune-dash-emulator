# Build the PowerTune dash app for Windows (emulator). Output: emulator\build\release\PowertuneQMLGui.exe
# Full compiler output goes to emulator\build.log.
$qt    = "$env:USERPROFILE\Qt\5.15.2\mingw81_64"    # Qt installed with aqtinstall (see README)
$mingw = "$env:USERPROFILE\Qt\Tools\mingw810_64"
$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$log   = "$here\build.log"
New-Item -ItemType Directory -Force "$here\build" | Out-Null
# Run through cmd so compiler warnings on stderr don't abort PowerShell (5.1 treats them as errors).
$cmd = "set PATH=$qt\bin;$mingw\bin;%PATH% && cd /d `"$here\build`" && " +
       "qmake `"$here\src\PowertuneQMLGui.pro`" -spec win32-g++ CONFIG+=release && " +
       "mingw32-make -j $env:NUMBER_OF_PROCESSORS"
# No windeployqt: run-emulator.ps1 points the exe at the Qt install instead.
cmd /c "$cmd > `"$log`" 2>&1"
if ($LASTEXITCODE) { Write-Host "BUILD FAILED (exit $LASTEXITCODE) - see $log"; exit 1 }
Write-Host "Built $here\build\release\PowertuneQMLGui.exe"
