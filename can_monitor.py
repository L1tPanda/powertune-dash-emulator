#!/usr/bin/env python3
"""Show the CAN frames the emulator would put on can0 (candump style), decoding the GPS frame.

The emulator build sends each outgoing frame as text "ID#DATAHEX" to UDP 127.0.0.1:45460.

  python can_monitor.py
"""
import socket, time


def decode_6a0(d):
    speed = (d[0] | d[1] << 8) / 100
    return (f"GPS speed {speed:6.2f} km/h  UTC {d[2]:02d}:{d[3]:02d}:{d[4]:02d}.{d[5]:02d}  "
            f"fix {'yes' if d[6] else 'NO '}  sats {d[7]}")


def decode_340(d):
    return f"ME442 Vehicle_Speed {(d[0] | d[1] << 8) * 0.008:7.2f} km/h"


DECODERS = {"6A0": decode_6a0, "340": decode_340}


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 45460))
    print("listening for emulator CAN output on UDP 45460 (Ctrl+C to stop)")
    count, t0 = 0, time.monotonic()
    try:
        while True:
            text = sock.recv(256).decode(errors="replace").strip()
            ident, _, hexdata = text.partition("#")
            data = bytes.fromhex(hexdata)
            count += 1
            rate = count / max(time.monotonic() - t0, 1e-6)
            spaced = " ".join(f"{b:02X}" for b in data)
            extra = DECODERS[ident](data) if ident in DECODERS and len(data) == 8 else ""
            print(f"can0  {ident:>3}   [{len(data)}]  {spaced:<23}   {extra}   ({rate:4.1f}/s)")
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
