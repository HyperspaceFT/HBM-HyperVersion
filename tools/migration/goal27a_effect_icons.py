#!/usr/bin/env python3
"""Crop the Goal 27A mob effect icons from the upstream potion icon atlas.

Upstream HbmPotion (potion/HbmPotion.java:49-62, 88, 95-99) draws its icon from
``textures/gui/potions.png`` (256x256) as an 18x18 tile at (x * 18, 198 + y * 18). The lead, phosphorus,
radiation and taint icons NEO already ships are pixel-identical to the unscaled tiles (0,0), (1,0), (6,0)
and (1,1); the missing seven are cropped the same way, without scaling, and written as 8-bit RGBA PNG.

--check also re-verifies the four existing icons against their tiles by decoded pixels (they are palette
PNGs, so a byte comparison would not apply) and never rewrites them.

Usage:
  python tools/migration/goal27a_effect_icons.py            # write the seven new icons
  python tools/migration/goal27a_effect_icons.py --check    # compare only
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

NEO_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_ROOT = NEO_ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ATLAS = UPSTREAM_ROOT / "src/main/resources/assets/hbm/textures/gui/potions.png"
TARGET_DIR = NEO_ROOT / "src/main/resources/assets/hbmsntm/textures/mob_effect"

TILE = 18
ORIGIN_Y = 198  # HbmPotion draws row y at 198 + y * 18

# registerPotion(..., x, y) indices from HbmPotion.java:49-62.
NEW_ICONS = {
    "mutation": (2, 0),
    "bang": (3, 0),
    "radx": (5, 0),
    "radaway": (7, 0),
    "stability": (2, 1),
    "potionsickness": (3, 1),
    "death": (4, 1),
}
# Icons NEO already ships (Goal 5A / 6); verified, never rewritten.
EXISTING_ICONS = {
    "taint": (0, 0),
    "radiation": (1, 0),
    "lead": (6, 0),
    "phosphorus": (1, 1),
}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode(path: Path):
    """Decode a non-interlaced 8-bit PNG of any colour type into (width, height, RGBA rows)."""
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path}: not a PNG file")
    position = len(PNG_SIGNATURE)
    idat = b""
    palette = transparency = None
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or interlace != 0:
                raise ValueError(f"{path}: only 8-bit non-interlaced PNG is supported")
        elif kind == b"PLTE":
            palette = body
        elif kind == b"tRNS":
            transparency = body
        elif kind == b"IDAT":
            idat += body
    bpp = {6: 4, 2: 3, 3: 1, 4: 2, 0: 1}[ctype]
    stride = width * bpp
    raw = zlib.decompress(idat)
    previous = bytearray(stride)
    cursor = 0
    lines = []
    for _ in range(height):
        filter_type = raw[cursor]
        line = bytearray(raw[cursor + 1:cursor + 1 + stride])
        cursor += 1 + stride
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up = previous[i]
            upper_left = previous[i - bpp] if i >= bpp else 0
            if filter_type == 1:
                line[i] = (line[i] + left) & 0xFF
            elif filter_type == 2:
                line[i] = (line[i] + up) & 0xFF
            elif filter_type == 3:
                line[i] = (line[i] + ((left + up) >> 1)) & 0xFF
            elif filter_type == 4:
                p = left + up - upper_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upper_left)
                predictor = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
                line[i] = (line[i] + predictor) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"{path}: unknown PNG filter {filter_type}")
        lines.append(line)
        previous = line
    rows = []
    for line in lines:
        row = []
        for x in range(width):
            if ctype == 6:
                row.append(tuple(line[x * 4:x * 4 + 4]))
            elif ctype == 2:
                row.append(tuple(line[x * 3:x * 3 + 3]) + (255,))
            elif ctype == 0:
                row.append((line[x],) * 3 + (255,))
            elif ctype == 4:
                row.append((line[x * 2],) * 3 + (line[x * 2 + 1],))
            else:
                index = line[x]
                alpha = transparency[index] if transparency and index < len(transparency) else 255
                row.append(tuple(palette[index * 3:index * 3 + 3]) + (alpha,))
        rows.append(row)
    return width, height, rows


def encode_rgba(width: int, height: int, pixels) -> bytes:
    raw = b"".join(b"\x00" + bytes(c for pixel in row for c in pixel) for row in pixels)

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def tile(atlas_rows, x: int, y: int):
    return [row[x * TILE:(x + 1) * TILE] for row in atlas_rows[ORIGIN_Y + y * TILE:ORIGIN_Y + (y + 1) * TILE]]


def rel(path: Path) -> str:
    return path.relative_to(NEO_ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only verify that the committed icons match")
    args = parser.parse_args()
    if not ATLAS.is_file():
        print(f"missing upstream atlas {ATLAS}", file=sys.stderr)
        return 2
    width, height, atlas_rows = decode(ATLAS)
    if (width, height) != (256, 256):
        print(f"unexpected atlas size {width}x{height}", file=sys.stderr)
        return 2

    mismatches = 0
    # Existing icons first: they are the precedent for cropping the unscaled tile.
    for name, (x, y) in EXISTING_ICONS.items():
        target = TARGET_DIR / f"{name}.png"
        if not target.is_file():
            print(f"MISSING {rel(target)}")
            mismatches += 1
            continue
        icon_width, icon_height, icon_rows = decode(target)
        if (icon_width, icon_height) == (TILE, TILE) and icon_rows == tile(atlas_rows, x, y):
            print(f"OK {rel(target)} (pixels equal tile {x},{y})")
        else:
            print(f"MISMATCH {rel(target)} (tile {x},{y})")
            mismatches += 1
    if mismatches:
        print("existing icons do not match their tiles; the crop precedent fails, stopping", file=sys.stderr)
        return 3

    for name, (x, y) in NEW_ICONS.items():
        target = TARGET_DIR / f"{name}.png"
        expected = encode_rgba(TILE, TILE, tile(atlas_rows, x, y))
        if args.check:
            if not target.is_file():
                print(f"MISSING {rel(target)}")
                mismatches += 1
            elif target.read_bytes() != expected:
                print(f"MISMATCH {rel(target)}")
                mismatches += 1
            else:
                print(f"OK {rel(target)}")
        else:
            target.write_bytes(expected)
            print(f"wrote {rel(target)}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
