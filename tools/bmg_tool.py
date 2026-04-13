"""bmg_tool.py - Extract text from Animal Crossing EUR (GAFP01) BMG message files.

The EUR version stores all game text in a Nintendo BMG (Binary MeSSaGe) file
(magic: MESGbmg1) with two blocks:
  INF1 - offset table: N x 4-byte big-endian offsets into DAT1
  DAT1 - raw string data using AC's custom 1-byte charset

The encoding uses the same character map as the USA version (msg_tool.py)
with two differences:
  1. The control code escape byte is 0x80 instead of 0x7F.
  2. The control code type byte encodes the TOTAL byte count of the sequence
     (escape + type + args), so a sequence starting with 0x80 0x07 is 7 bytes
     long (escape + type + 5 arg bytes).  Minimum total size is 2 (no args).

Usage:
    python -m tools.bmg_tool unpack <msg.bin> <out.txt>
    python -m tools.bmg_tool info   <msg.bin>
"""

import argparse
import struct
import os
import sys

# Re-use the character map from msg_tool (same charset as USA)
from tools.msg_tool import CHAR_MAP

# Escape byte used in EUR BMG (0x7F in USA, 0x80 in EUR BMG)
EUR_ESCAPE = 0x80


# ── BMG parsing ───────────────────────────────────────────────────────────────

def parse_bmg(data: bytes):
    """Return (offsets, dat1_payload) from a BMG binary blob."""
    if data[0:8] != b"MESGbmg1":
        raise ValueError("Not a valid BMG file (missing MESGbmg1 magic)")

    num_blocks = struct.unpack_from(">I", data, 12)[0]

    # Walk blocks
    offset = 32  # BMG file header is 32 bytes
    inf1_offsets = None
    dat1_payload = None

    for _ in range(num_blocks):
        magic = data[offset : offset + 4]
        block_size = struct.unpack_from(">I", data, offset + 4)[0]

        if magic == b"INF1":
            num_entries = struct.unpack_from(">H", data, offset + 8)[0]
            entry_size  = struct.unpack_from(">H", data, offset + 10)[0]
            entries_start = offset + 16
            inf1_offsets = [
                struct.unpack_from(">I", data, entries_start + i * entry_size)[0]
                for i in range(num_entries)
            ]
        elif magic == b"DAT1":
            dat1_payload = data[offset + 8 : offset + block_size]

        offset += block_size

    if inf1_offsets is None or dat1_payload is None:
        raise ValueError("BMG is missing INF1 or DAT1 block")

    return inf1_offsets, dat1_payload


# ── Decoding ──────────────────────────────────────────────────────────────────

def decode_entry_eur(payload: bytes, start: int, end: int, idx: int) -> str:
    """Decode one BMG message entry to a human-readable string.

    Control code format: 0x80 <type> [args...]
    The type byte encodes the TOTAL byte count of the sequence (including the
    0x80 escape byte), so args = payload[i+2 : i+type].  Minimum size is 2.
    """
    parts = [f"[[ENTRY {idx} START]]\n"]
    i = start
    while i < end:
        byte = payload[i]
        if byte == EUR_ESCAPE:
            if i + 1 >= end:
                break
            cmd_type = payload[i + 1]
            total_size = max(cmd_type, 2)  # must consume at least escape+type
            args = payload[i + 2 : i + total_size]
            if args:
                hex_values = " ".join(f"{b:02X}" for b in args)
                parts.append(f"<<CMD{cmd_type:02X} [{hex_values}]>>")
            else:
                parts.append(f"<<CMD{cmd_type:02X}>>")
            i += total_size
        else:
            parts.append(CHAR_MAP[byte])
            i += 1
    parts.append("\n\n")
    return "".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

def decode_bmg(bmg_path: str, out_path: str):
    """Extract all messages from a BMG file to a UTF-8 text file."""
    with open(bmg_path, "rb") as f:
        data = f.read()

    offsets, dat1 = parse_bmg(data)
    n = len(offsets)

    with open(out_path, "w", encoding="utf-8") as out:
        buffer = []
        for i in range(n):
            start = offsets[i]
            end   = offsets[i + 1] if i + 1 < n else len(dat1)
            if end <= start:
                continue
            buffer.append(decode_entry_eur(dat1, start, end, i))
            if len(buffer) >= 4096:
                out.write("".join(buffer))
                buffer.clear()
        if buffer:
            out.write("".join(buffer))

    print(f"Decoded {n} entries → {out_path}")


def bmg_info(bmg_path: str):
    with open(bmg_path, "rb") as f:
        data = f.read()
    offsets, dat1 = parse_bmg(data)
    print(f"File   : {bmg_path}")
    print(f"Entries: {len(offsets)}")
    print(f"DAT1   : {len(dat1)} bytes")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract text from Animal Crossing EUR BMG message files."
    )
    parser.add_argument(
        "mode",
        choices=["unpack", "info"],
        help="'unpack' to extract text, 'info' to show statistics",
    )
    parser.add_argument("path", help="Path to msg.bin (BMG file)")
    parser.add_argument(
        "out",
        nargs="?",
        help="Output .txt path (required for 'unpack')",
    )
    args = parser.parse_args()

    if args.mode == "unpack":
        if not args.out:
            parser.error("'unpack' requires an output path")
        decode_bmg(args.path, args.out)
    elif args.mode == "info":
        bmg_info(args.path)


if __name__ == "__main__":
    main()
