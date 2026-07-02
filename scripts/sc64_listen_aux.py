#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import serial


def send_command(port, cmd, arg0=0, arg1=0, data=b""):
    port.write(b"CMD" + cmd.encode("ascii"))
    port.write(arg0.to_bytes(4, "big"))
    port.write(arg1.to_bytes(4, "big"))
    if data:
        port.write(data)
    port.flush()
    header = port.read(4)
    if len(header) != 4:
        raise RuntimeError("timed out waiting for command response")
    ident = header[:3]
    packet_id = header[3:4]
    length_data = port.read(4)
    if len(length_data) != 4:
        raise RuntimeError("timed out waiting for response length")
    length = int.from_bytes(length_data, "big")
    response = port.read(length) if length else b""
    if len(response) != length:
        raise RuntimeError("timed out waiting for response data")
    if ident == b"ERR":
        raise RuntimeError(f"SC64 command {cmd} returned ERR")
    if ident != b"CMP" or packet_id != cmd.encode("ascii"):
        raise RuntimeError(f"unexpected response {ident!r} {packet_id!r} for command {cmd}")
    return response


def read_exact(port, size, deadline):
    data = bytearray()
    while len(data) < size and time.monotonic() < deadline:
        chunk = port.read(size - len(data))
        if chunk:
            data.extend(chunk)
    if len(data) != size:
        return None
    return bytes(data)


def reset_link(port):
    port.dtr = True
    deadline = time.monotonic() + 2.0
    while not port.dsr and time.monotonic() < deadline:
        time.sleep(0.01)
    port.reset_input_buffer()
    port.reset_output_buffer()
    port.dtr = False
    deadline = time.monotonic() + 2.0
    while port.dsr and time.monotonic() < deadline:
        time.sleep(0.01)


def listen(args):
    events = []
    with serial.Serial(args.port, args.baud, timeout=0.05) as port:
        if args.reset_link:
            reset_link(port)
        if args.identify:
            response = send_command(port, "v")
            events.append({
                "time": round(time.monotonic(), 6),
                "ident": "CMP",
                "id": "v",
                "length": len(response),
                "data_hex": response.hex().upper(),
            })
        if args.isv_offset is not None:
            response = send_command(port, "C", 4, args.isv_offset)
            events.append({
                "time": round(time.monotonic(), 6),
                "ident": "CMP",
                "id": "C",
                "length": len(response),
                "data_hex": response.hex().upper(),
                "config": "ISV_ADDRESS",
                "isv_offset": f"0x{args.isv_offset:08X}",
            })
        deadline = time.monotonic() + args.seconds
        sync = bytearray()
        while time.monotonic() < deadline:
            byte = port.read(1)
            if not byte:
                continue
            sync.extend(byte)
            if len(sync) > 3:
                sync = sync[-3:]
            if bytes(sync) not in (b"PKT", b"CMP", b"ERR"):
                continue

            ident = bytes(sync)
            packet_id = read_exact(port, 1, deadline)
            length_bytes = read_exact(port, 4, deadline)
            if packet_id is None or length_bytes is None:
                break
            length = int.from_bytes(length_bytes, "big")
            data = read_exact(port, length, deadline) if length else b""
            if data is None:
                break

            event = {
                "time": round(time.monotonic(), 6),
                "ident": ident.decode("ascii", errors="replace"),
                "id": packet_id.decode("ascii", errors="replace"),
                "length": length,
                "data_hex": data.hex().upper(),
            }
            if ident == b"PKT" and packet_id == b"X" and len(data) == 4:
                value = int.from_bytes(data, "big")
                event["aux_word"] = f"0x{value:08X}"
                event["aux_ascii"] = data.decode("ascii", errors="replace")
            elif ident == b"PKT" and packet_id in (b"I", b"U"):
                event["text"] = data.decode("utf-8", errors="replace")
                if packet_id == b"I" and len(data) >= 4:
                    event["isv_words"] = [
                        f"0x{int.from_bytes(data[i:i + 4], 'big'):08X}"
                        for i in range(0, len(data) - (len(data) % 4), 4)
                    ]
            events.append(event)

    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--reset-link", action="store_true")
    parser.add_argument("--identify", action="store_true")
    parser.add_argument("--isv-offset", type=lambda value: int(value, 0))
    args = parser.parse_args()

    events = listen(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(events, indent=2) + "\n")
    print(json.dumps({"events": len(events), "out": args.out}, indent=2))
    for event in events[:40]:
        if "aux_word" in event:
            print(event["aux_word"], event.get("aux_ascii", ""))
        else:
            print(event["ident"], event["id"], event["length"], event["data_hex"][:64])


if __name__ == "__main__":
    main()
