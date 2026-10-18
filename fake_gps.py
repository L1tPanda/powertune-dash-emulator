#!/usr/bin/env python3
"""Fake GPS module for the dash emulator.

Sends NMEA $GPRMC + $GPGGA sentences (what the dash's u-blox module outputs) at 10 Hz to
UDP 127.0.0.1:45455, where the emulator build of PowerTune feeds them into the same
GPS::ProcessMessage() the serial port uses.

  python fake_gps.py                 # speed cycles 0 -> 120 -> 0 km/h over 30 s
  python fake_gps.py --speed 87.4    # hold a fixed speed
  python fake_gps.py --nofix         # no satellite fix (RMC status V)
"""
import argparse, math, socket, time
from datetime import datetime, timezone

KMH_PER_KNOT = 1.852


def nmea(body):
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return f"${body}*{cs:02X}\r\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--speed", type=float, help="fixed speed in km/h")
    ap.add_argument("--nofix", action="store_true")
    ap.add_argument("--hz", type=float, default=10)
    ap.add_argument("--port", type=int, default=45455)
    a = ap.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0, n = time.monotonic(), 0
    lat, lon = "5130.000", "00007.500"           # somewhere in London, ddmm.mmm
    print(f"fake GPS -> 127.0.0.1:{a.port} at {a.hz:g} Hz (Ctrl+C to stop)")
    try:
        while True:
            t = time.monotonic() - t0
            kmh = a.speed if a.speed is not None else 60 - 60 * math.cos(2 * math.pi * t / 30)
            now = datetime.now(timezone.utc)
            hms = now.strftime("%H%M%S") + f".{now.microsecond // 10000:02d}"
            status, quality, sats = ("V", 0, 3) if a.nofix else ("A", 1, 9)
            rmc = nmea(f"GPRMC,{hms},{status},{lat},N,{lon},W,{kmh / KMH_PER_KNOT:.2f},90.0,{now:%d%m%y},,,A")
            gga = nmea(f"GPGGA,{hms},{lat},N,{lon},W,{quality},{sats:02d},0.9,35.0,M,47.0,M,,")
            sock.sendto((gga + rmc).encode(), ("127.0.0.1", a.port))
            n += 1
            if n % int(a.hz) == 0:
                print(f"\rspeed {kmh:6.1f} km/h  time {hms} UTC  fix {status}  sats {sats}   ", end="", flush=True)
            time.sleep(1 / a.hz)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
