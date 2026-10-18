#!/usr/bin/env python3
"""Live AFR / lambda / EGT monitor for the Motorsport Electronics ME442.

Runs on the PowerTune dash (or any Linux box with SocketCAN) and decodes
0x301 and 0x307 straight off the bus, independent of the PowerTune UI.

No third-party packages needed: it uses the stdlib SocketCAN socket.
If cantools is installed and --dbc is given, the frames are decoded with
the DBC instead, so you can cross-check the hard-coded scaling.

  python3 me442_monitor.py                    # live from can0
  python3 me442_monitor.py -i can1            # other interface
  python3 me442_monitor.py --dbc ME1_4.dbc    # decode with cantools
  python3 me442_monitor.py --replay log.txt   # replay a candump / candump -L log
  python3 me442_monitor.py --selftest         # check decoding, no bus needed
"""
import argparse
import re
import socket
import struct
import sys
import time

ID_AFR = 0x301
ID_EGT = 0x307
STOICH = 14.7          # petrol; change for E85 etc. Only used for the lambda column.
STALE_S = 1.0          # warn if a message hasn't been seen for this long


def decode_301(d):
    return {
        "AFR1": d[2] * 0.05 + 7.5,
        "AFR2": d[3] * 0.05 + 7.5,
        "AFR_Target": d[6] * 0.05 + 7.5,
        "Lambda_Trim": (d[4] | d[5] << 8) * 0.01,
    }


def decode_307(d):
    return {
        "EGT1": (d[0] | d[1] << 8) * 0.1,
        "EGT2": (d[2] | d[3] << 8) * 0.1,
    }


BUILTIN = {ID_AFR: decode_301, ID_EGT: decode_307}


def make_decoder(dbc_path):
    if not dbc_path:
        return lambda cid, data: BUILTIN[cid](data)
    try:
        import cantools
    except ImportError:
        sys.exit("--dbc needs cantools (pip install cantools)")
    db = cantools.database.load_file(dbc_path)
    return lambda cid, data: db.decode_message(cid, bytes(data), decode_choices=False)


# ---------------------------------------------------------------- sources

def socketcan_frames(iface):
    if not hasattr(socket, "AF_CAN"):
        sys.exit("SocketCAN not available here (Linux only). Use --replay or --selftest.")
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    # Kernel-side filter: only 0x301 and 0x307, standard IDs.
    mask = socket.CAN_SFF_MASK | socket.CAN_EFF_FLAG | socket.CAN_RTR_FLAG
    flt = struct.pack("=IIII", ID_AFR, mask, ID_EGT, mask)
    s.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER, flt)
    s.bind((iface,))
    s.settimeout(STALE_S)
    while True:
        try:
            frame = s.recv(16)
        except socket.timeout:
            yield None, None
            continue
        cid, dlc, data = struct.unpack("=IB3x8s", frame)
        yield cid & socket.CAN_SFF_MASK, data[:dlc]


# "can0  301   [8]  00 00 8C ..."  or  "(1697.12) can0 301#00008C..."
RE_PLAIN = re.compile(r"\b([0-9A-Fa-f]{3,8})\s+\[(\d)\]\s+((?:[0-9A-Fa-f]{2}\s*)*)")
RE_LOG = re.compile(r"\b([0-9A-Fa-f]{3,8})#([0-9A-Fa-f]*)")


def replay_frames(lines):
    for line in lines:
        m = RE_LOG.search(line)
        if m:
            cid, data = int(m.group(1), 16), bytes.fromhex(m.group(2))
        else:
            m = RE_PLAIN.search(line)
            if not m:
                continue
            cid = int(m.group(1), 16)
            data = bytes.fromhex(m.group(3).replace(" ", ""))[: int(m.group(2))]
        if cid in BUILTIN:
            yield cid, data


# ---------------------------------------------------------------- output

def fmt(vals, last_seen, now):
    def age_flag(cid):
        t = last_seen.get(cid)
        if t is None:
            return " (no 0x%03X yet)" % cid
        return " (STALE 0x%03X)" % cid if now - t > STALE_S else ""

    parts = []
    if "AFR1" in vals or "AFRCurr_1" in vals:
        afr = vals.get("AFR1", vals.get("AFRCurr_1"))
        parts.append("AFR1 %5.2f  lam %.3f" % (afr, afr / STOICH))
        tgt = vals.get("AFR_Target")
        if tgt is not None:
            parts.append("tgt %5.2f" % tgt)
        trim = vals.get("Lambda_Trim")
        if trim is not None:
            parts.append("trim %.2f" % trim)
    parts.append(age_flag(ID_AFR).strip() or "")
    egt = vals.get("EGT1", vals.get("EGT_1"))
    if egt is not None:
        parts.append("EGT1 %6.1fC" % egt)
        egt2 = vals.get("EGT2", vals.get("EGT_2"))
        if egt2:
            parts.append("EGT2 %6.1fC" % egt2)
    parts.append(age_flag(ID_EGT).strip() or "")
    return "  ".join(p for p in parts if p)


def run(frames, decode, live):
    vals, last_seen, raw = {}, {}, {}
    for cid, data in frames:
        now = time.monotonic()
        if cid is not None:
            vals.update(decode(cid, data))
            last_seen[cid] = now
            raw[cid] = data.hex(" ").upper()
        line = fmt(vals, last_seen, now)
        if live:
            sys.stdout.write("\r\033[K" + line)
            sys.stdout.flush()
        else:
            print("%03X [%s]  ->  %s" % (cid, raw[cid], line))
    if live:
        print()


def selftest():
    # Examples from the handoff: AFR byte 0x8C -> 14.5, EGT 30 22 -> 875.2 °C.
    a = decode_301(bytes([0, 0, 0x8C, 0, 0, 0, 0x8C, 0]))
    e = decode_307(bytes([0x30, 0x22, 0, 0, 0, 0, 0, 0]))
    assert abs(a["AFR1"] - 14.5) < 1e-9, a
    assert abs(a["AFR_Target"] - 14.5) < 1e-9, a
    assert abs(e["EGT1"] - 875.2) < 1e-9, e
    log = [
        "  can0  301   [8]  00 00 8C 00 64 00 8C 00",
        "(1697000000.123456) can0 307#3022000000000000",
        "  can0  300   [8]  11 22 33 44 55 66 77 88",   # ignored
    ]
    got = list(replay_frames(log))
    assert [c for c, _ in got] == [ID_AFR, ID_EGT], got
    assert abs(decode_301(got[0][1])["Lambda_Trim"] - 1.00) < 1e-9
    print("selftest OK: AFR 0x8C -> %.2f, EGT 30 22 -> %.1f C, trim 64 00 -> %.2f"
          % (a["AFR1"], e["EGT1"], decode_301(got[0][1])["Lambda_Trim"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--iface", default="can0")
    ap.add_argument("--dbc", help="decode with cantools from this DBC instead of built-in scaling")
    ap.add_argument("--replay", help="candump / candump -L text log to decode instead of the live bus")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    decode = make_decoder(args.dbc)
    try:
        if args.replay:
            with open(args.replay) as f:
                run(replay_frames(f), decode, live=False)
        else:
            run(socketcan_frames(args.iface), decode, live=True)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
