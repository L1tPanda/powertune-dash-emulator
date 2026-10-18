# Notice: credits and no warranty

## Credits

This emulator builds and runs the PowerTune Digital dash application on Windows:
<https://github.com/PowerTuneDigital/PowerTuneDigitalOfficial>

PowerTune: Copyright (C) 2016-2018 Markus Ippy, Bastian Gschrey and contributors;
Copyright (C) 2018 PowerTuneDigital. Licensed under the GNU General Public License v3.

`patches/windows-emulator.patch` modifies PowerTune source files and is licensed GPL-3 like them
(see `LICENSE`). PowerTune's source is not included: the README explains how to get it from
PowerTune's own repository. No PowerTune or Motorsport Electronics binaries, decoders, licence files,
fonts, images or DBC files are included. The fake ECU only sends the channel numbers that
PowerTune's open-source `udpreceiver.cpp` already defines; it does not run or replace any licensed
decoder on a real dash.

Qt is used under its own licence (The Qt Company). "PowerTune" and "PowerTune Digital" are names of
PowerTune Digital; "Motorsport Electronics" and "ME442" are names of Motorsport Electronics. They are
used only to say what this works with. **This project is unofficial and is not affiliated with,
endorsed by or supported by PowerTune Digital or Motorsport Electronics.**

## No warranty - use at your own risk

This software is provided "as is", without warranty of any kind, express or implied, as set out in
sections 15 and 16 of the GPL-3 licence. The emulator and the fake ECU / GPS are for testing only:
they do not prove that a page or firmware change behaves the same on a real dash or ECU. Always test
on the real hardware, on the bench and parked first. `fake_me442.py --host` can send data to a real
dash; only do that with the car stationary and the real decoder stopped.
