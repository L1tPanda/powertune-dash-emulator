# PowerTune dash emulator (Windows)

Runs the real [PowerTune Digital](https://github.com/PowerTuneDigital/PowerTuneDigitalOfficial) dash app
on a Windows PC, fed by a fake Motorsport Electronics ME442 and a fake GPS, so pages and firmware
changes can be tested without the car. Unofficial; not affiliated with PowerTune Digital or
Motorsport Electronics. GPL-3, like the PowerTune source it patches.

```
.\run-emulator.ps1                 # dash + fake ECU at idle   (Ctrl+C stops the data; close the window to quit)
.\run-emulator.ps1 -Mode sweep     # RPM sweeps 900-8000, everything follows
.\run-emulator.ps1 -Mode drive     # throttle on/off, gear changes
.\run-emulator.ps1 -NoData         # dash only
.\build.ps1                        # rebuild after changing anything in src\  (log: build.log)
.\load-dash-settings.ps1           # load a dash's settings into the emulator (close the emulator first)
python fake_me442.py --list        # channel numbers; --set 35=900 pins one (35 = EGT 1)
python fake_gps.py                 # fake GPS module (NMEA to UDP 45455); --speed 87 or --nofix
python can_monitor.py              # show CAN frames the emulator sends (custom firmware: 0x340 + 0x6A0)
# fake_me442.py also acts as the ME442's speed input: it reads 0x340 (UDP 45461) and reports
# "VSS from 0x340", or "TIMEOUT" if no frame for 0.5 s
```

`tools/me442_monitor.py` runs on the real dash (or any Linux box with SocketCAN) and decodes the
ME442's AFR / lambda / EGT frames straight off `can0`.

## Setting it up from scratch

1. **Qt 5.15.2 + MinGW 8.1** for your user (about 3 GB, no admin):
   ```
   pip install --user aqtinstall
   python -m aqt install-qt windows desktop 5.15.2 win64_mingw81 -m qtcharts qtvirtualkeyboard --outputdir $env:USERPROFILE\Qt
   python -m aqt install-tool windows desktop tools_mingw qt.tools.win64_mingw810 --outputdir $env:USERPROFILE\Qt
   ```
2. **PowerTune source** into `src\` (the same commit the dash ran), then this repo's emulator patch:
   ```
   git clone https://github.com/PowerTuneDigital/PowerTuneDigitalOfficial.git src
   git -C src checkout 5380ce2
   git -C src apply ..\patches\windows-emulator.patch
   ```
   For the GPS / CAN emulation also apply the custom-firmware patches (separate repo), which carry
   the Windows-only UDP hooks.
3. **Data folder** `C:\PowerTune` = the dash's `/home/pi`: copy `UserDashboards`, `Logo`, and the dash's
   fonts (`/usr/share/fonts/PowertuneDigital` -> `C:\PowerTune\fonts`) off your dash. Then link
   `C:\home\pi` to it, so `file:///home/pi/...` paths in pages and settings work:
   `New-Item -ItemType Junction -Path C:\home\pi -Target C:\PowerTune` (create `C:\home` first).
4. **Settings**: copy `/.config/Power-Tune/PowerTune.conf` and `/.config/PowerTuneQML/PowerTuneDash.conf`
   off the dash and run `.\load-dash-settings.ps1 -ConfigDir <that folder>`. Run it from your own
   terminal, not from a sandboxed tool, or the app may not see the files.
5. `.\build.ps1`, then `.\run-emulator.ps1`.

## How it fits together

| Piece | Where |
|---|---|
| Qt 5.15.2 + MinGW 8.1 (user install) | `%USERPROFILE%\Qt` |
| App source (PowerTune, commit `5380ce2`, patched) | `src\` (not in this repo) |
| Data folder (dash `/home/pi`) | `C:\PowerTune` - pages, images, fonts, tracks |
| `C:\home\pi` | link to `C:\PowerTune` |
| Settings (dash `/.config/*.conf`) | `%APPDATA%\Power-Tune\PowerTune.ini`, `%APPDATA%\PowerTuneQML\PowerTuneDash.ini` |

The fake ECU sends what PowerTune's ME13 decoder sends on the dash: UDP text `ident,value` to port 45454.

## Emulator-only changes to the source (`patches/windows-emulator.patch`, marked `EMULATOR`)

- `main.cpp`: on Windows, store settings as .ini (like the dash), load fonts from `C:\PowerTune\fonts`,
  and log which settings file was read to `C:\PowerTune\emulator.log`.
- `main.qml`: on Windows, open at 800x480 instead of filling the screen.
- `appsettings.cpp`: on Windows, read `PowerTuneDash.ini` (speed source, speed correction, ...) instead
  of the registry. Without this the emulator ignores "Main speed source = GPS" and shows speed 0.

All are Windows-only, so they don't affect a dash build.

## Notes

- Load pages the same way as on the dash: double-tap - Clear - Import - pick - Load - Save.
- `connectECUAtStartup=false` means *do* connect at startup (the setting is stored inverted).
- If the emulator shows PowerTune's stock cluster and readings stay at 0, it is on default settings:
  close it and run `.\load-dash-settings.ps1`. `C:\PowerTune\emulator.log` shows which settings file
  was read and how many entries it had.
- Text-label font sizes are points; with the dash's screen settings 1 pt = 1.97 px.
- If the dash has pressure units set to imperial (`unitSelector2=1`), MAP/boost/oil/fuel pressure show in psi.
