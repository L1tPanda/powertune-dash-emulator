#!/usr/bin/env python3
"""Fake ME442 + ME13 decoder for testing PowerTune without the car.

The real dash runs ME13, which reads the ME442 off CAN and sends each value to the
PowerTune app as a UDP text packet "ident,value" to 127.0.0.1:45454. This script sends
the same packets, with the same channel numbers (taken from an strace of ME13 on the
dash, 2026-10-17), driven by a simple engine model.

  python fake_me442.py                 # idle
  python fake_me442.py --mode sweep    # RPM sweeps 900 -> 8000 -> 900, everything follows
  python fake_me442.py --mode drive    # on/off throttle, gear changes, warming up
  python fake_me442.py --set 35=900    # pin a channel (here EGT, shown as "EGT 2") to a value
  python fake_me442.py --host <dash-ip>        # feed a real dash on the bench (stop ME13 first)

Works on Windows, Linux and the dash itself (stdlib only).
"""
import argparse
import math
import random
import socket
import time

# ident: (PowerTune data source, ME442 signal) - as ME13 sends them
CHANNELS = {
    179: ("rpm", "RPM"),                    210: ("TPS", "TPS"),
    155: ("MAP", "MAP kPa"),                278: ("BoostPreskpa", "MAP - 101.3"),
    135: ("Intaketemp", "IAT"),             221: ("Watertemp", "CLT"),
    170: ("oiltemp", "Oil_T"),              169: ("oilpres", "Oil_P kPa"),
    228: ("BatteryV", "VBAT"),              100: ("FuelPress", "Fuel_Press kPa"),
    101: ("Fueltemp", "Fuel_Temp"),         916: ("AFRcyl1", "AFRCurr_1"),
    917: ("AFRcyl2", "AFRCurr_2"),          925: ("AFRLEFTBANKTARGET", "AFR_Target"),
    142: ("LAMBDA", "Lambda_Trim"),         84: ("fuelcomposition", "Fuel_Eth_Perc"),
    49: ("Flag1", "RPM_HardLimit"),         121: ("Ign", "IgnAdvAngle"),
    33: ("Dwell", "IgnDwell"),              133: ("InjDuty", "Pri_InjDuty"),
    175: ("Primaryinp", "Pri_InjPw"),       276: ("InjAngle", "Pri_InjAngle"),
    275: ("InjDuty2", "Sec_InjDuty"),       181: ("Secinjpulse", "Sec_InjPw"),
    130: ("Inj2", "Sec_InjAngle"),          21: ("BoostDuty", "Boost_Ctrl_Duty"),
    106: ("Gear", "Gear_Pos"),              201: ("targetbstlelkpa", "MAP_Target"),
    199: ("speed", "Vehicle_Speed"),        137: ("Knock", "Knock_Peak_Reading"),
    140: ("knockretardbank1", "Knock_Ign_Adv_Mod"),
    35: ("egt2", "EGT_1 (ME13 swap)"),      34: ("egt1", "EGT_2"),
    260: ("Analog0", "GPT_1"),              261: ("Analog1", "GPT_2"),
}
GEARS = [0, 120, 74, 54, 37, 28]          # km/h per 1000 rpm style ratios from the dash settings


class Engine:
    def __init__(self, mode):
        self.mode, self.t0 = mode, time.monotonic()
        self.clt, self.oilt, self.egt = 45.0, 30.0, 150.0
        self.gear, self.speed = 0, 0.0

    def step(self, dt):
        t = time.monotonic() - self.t0
        if self.mode == "sweep":
            phase = (t % 20) / 20                                   # 20 s up and back
            rpm = 900 + 7100 * (1 - abs(2 * phase - 1))
            tps = min(100, (rpm - 900) / 60)
        elif self.mode == "drive":
            cycle = t % 12
            tps = 85 if cycle < 5 else (0 if cycle < 8 else 25)
            rpm = 1500 + 5800 * (cycle / 5) if cycle < 5 else max(1500, 7300 - 1800 * (cycle - 5))
            self.gear = 1 + int(t // 12) % 5
        else:  # idle
            rpm = 950 + 60 * math.sin(t * 1.3) + random.uniform(-15, 15)
            tps = 0.0
        load = tps / 100
        mapk = 32 + 150 * load ** 1.4 if self.mode != "idle" else 32 + random.uniform(-1, 1)
        # slow warm-up and EGT following load
        self.clt += (88 - self.clt) * dt / 240
        self.oilt += (95 - self.oilt) * dt / 400
        self.egt += ((380 + 520 * load + rpm / 40) - self.egt) * dt / 4
        self.speed = rpm / 1000 * GEARS[self.gear] / 4.2 if self.gear else 0.0
        afr_tgt = 14.7 if load < 0.4 else 12.2
        afr = afr_tgt + random.uniform(-0.25, 0.25)
        pw = 1.6 + 9 * load
        return {
            179: round(rpm), 210: round(tps, 1), 155: round(mapk, 1), 278: round(mapk - 101.3, 1),
            135: round(18 + 6 * load, 1), 221: round(self.clt, 1), 170: round(self.oilt, 1),
            169: round(180 + rpm / 15), 228: round(13.8 + random.uniform(-0.1, 0.1), 1),
            100: 300 + round(random.uniform(-5, 5)), 101: 24, 916: round(afr, 2), 917: round(afr, 2),
            925: afr_tgt, 142: round(1.0 + random.uniform(-0.03, 0.03), 2), 84: 0, 49: 7250,
            121: round(13 + 22 * (rpm / 8000) - 8 * load, 1), 33: 2.8, 133: round(rpm * pw / 1200, 1),
            175: round(pw, 1), 276: 380, 275: 0, 181: 0, 130: 380, 21: round(40 * load, 1),
            106: self.gear, 201: 100 if load < 0.5 else 180, 199: round(self.speed),
            137: round(250 + 400 * load + random.uniform(0, 60)), 140: 0,
            35: round(self.egt), 34: 0, 260: 0, 261: 0,
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["idle", "sweep", "drive"], default="idle")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=45454)
    ap.add_argument("--hz", type=float, default=20)
    ap.add_argument("--set", action="append", default=[], metavar="IDENT=VALUE", help="pin a channel")
    ap.add_argument("--list", action="store_true", help="list channels and exit")
    a = ap.parse_args()
    if a.list:
        for k, (src, sig) in sorted(CHANNELS.items()):
            print(f"{k:4}  {src:18} {sig}")
        return
    pins = {int(k): float(v) for k, v in (s.split("=", 1) for s in a.set)}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Like the real ME442 with Speed Source = CAN: take vehicle speed from frame 0x340 (ME1_In_1,
    # bytes 0-1 x 0.008 km/h), which the emulator's custom firmware sends to UDP 45461.
    canin = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        canin.bind(("127.0.0.1", 45461))
        canin.setblocking(False)
    except OSError:
        canin = None
    vss, vss_time = 0.0, None
    eng, dt, n = Engine(a.mode), 1 / a.hz, 0
    print(f"sending {len(CHANNELS)} channels to {a.host}:{a.port} at {a.hz:g} Hz, mode {a.mode} (Ctrl+C to stop)")
    try:
        while True:
            vals = eng.step(dt)
            while canin:
                try:
                    ident, _, hexdata = canin.recv(64).decode().partition("#")
                except (BlockingIOError, OSError):
                    break
                if ident == "340":
                    d = bytes.fromhex(hexdata)
                    vss, vss_time = (d[0] | d[1] << 8) * 0.008, time.monotonic()
            vss_ok = vss_time is not None and time.monotonic() - vss_time < 0.5
            if vss_time is not None:            # once CAN speed has been seen, report it like the ECU does
                vals[199] = round(vss) if vss_ok else 0
            vals.update(pins)
            for ident, v in vals.items():
                sock.sendto(f"{ident},{v}".encode(), (a.host, a.port))
            n += 1
            if n % int(a.hz) == 0:
                vss_txt = ("no CAN speed yet" if vss_time is None else
                           f"VSS from 0x340 {vss:6.1f} km/h" if vss_ok else "VSS 0x340 TIMEOUT -> 0")
                print(f"\rrpm {vals[179]:5}  map {vals[155]:6}  clt {vals[221]:5}  egt {vals[35]:4}  afr {vals[916]:5}  {vss_txt}   ",
                      end="", flush=True)
            time.sleep(dt)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
