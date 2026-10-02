#!/usr/bin/env python3
"""Generate Goal 10A per-material scrap textures from the upstream base texture.

Upstream ItemAutogen recolours ``textures/items/scraps.png`` at runtime for every
material with RGBMutatorInterpolatedComponentRemap(0xFFFFFF, 0x505050, light, dark).
NEO has no runtime sprite mutation, so this script applies the same per-component
formula offline and writes one texture per material. Copper keeps the Goal 5A
texture and is not generated here.

Usage:
  python tools/migration/goal10a_scrap_textures.py            # write textures
  python tools/migration/goal10a_scrap_textures.py --check    # compare only
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

NEO_ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_ROOT = NEO_ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
SOURCE = UPSTREAM_ROOT / "src/main/resources/assets/hbm/textures/items/scraps.png"
TARGET_DIR = NEO_ROOT / "src/main/resources/assets/hbmsntm/textures/item"

SOURCE_LIGHT = 0xFFFFFF
SOURCE_DARK = 0x505050

# (texture suffix, solidColorLight, solidColorDark); must match Mats.java and upstream Mats.java:104-141.
MATERIALS = [
    ("tungsten", 0x868686, 0x000000),
    ("cobalt", 0xC2D1EE, 0x353554),
    ("steel", 0xAFAFAF, 0x0F0F0F),
    ("durasteel", 0x82A59C, 0x06281E),
]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunks(data: bytes):
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG file")
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        yield kind, data[offset + 8:offset + 8 + length]
        offset += 12 + length


def decode_rgba(path: Path) -> tuple[int, int, list[list[tuple[int, int, int, int]]]]:
    data = path.read_bytes()
    width = height = None
    idat = b""
    for kind, body in _chunks(data):
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or color != 6 or interlace != 0:
                raise ValueError(f"{path}: only 8-bit non-interlaced RGBA is supported")
        elif kind == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    stride = width * 4
    rows: list[bytearray] = []
    previous = bytearray(stride)
    position = 0
    for _ in range(height):
        filter_type = raw[position]
        line = bytearray(raw[position + 1:position + 1 + stride])
        position += 1 + stride
        for i in range(stride):
            left = line[i - 4] if i >= 4 else 0
            up = previous[i]
            upper_left = previous[i - 4] if i >= 4 else 0
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
        rows.append(line)
        previous = line
    pixels = [[tuple(row[x * 4:x * 4 + 4]) for x in range(width)] for row in rows]
    return width, height, pixels


def encode_rgba(width: int, height: int, pixels) -> bytes:
    raw = b"".join(b"\x00" + bytes(c for pixel in row for c in pixel) for row in pixels)

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _java_int(value: float) -> int:
    """Java's (int) cast of a double truncates toward zero."""
    return int(value)


def shift_component(lighter: int, darker: int, bound_lighter: int, bound_darker: int, component: int) -> int:
    position = (component - bound_lighter) / (bound_darker - bound_lighter)
    return _java_int(lighter + position * (darker - lighter)) & 0xFF


def remap(pixel, light: int, dark: int):
    r, g, b, a = pixel
    channels = []
    for shift, value in ((16, r), (8, g), (0, b)):
        channels.append(shift_component((light >> shift) & 0xFF, (dark >> shift) & 0xFF,
                                        (SOURCE_LIGHT >> shift) & 0xFF, (SOURCE_DARK >> shift) & 0xFF, value))
    return channels[0], channels[1], channels[2], a


def render(light: int, dark: int) -> bytes:
    width, height, pixels = decode_rgba(SOURCE)
    return encode_rgba(width, height, [[remap(pixel, light, dark) for pixel in row] for row in pixels])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only verify that the committed textures match")
    args = parser.parse_args()
    if not SOURCE.is_file():
        print(f"missing upstream texture {SOURCE}", file=sys.stderr)
        return 2
    mismatches = 0
    for name, light, dark in MATERIALS:
        target = TARGET_DIR / f"scraps_{name}.png"
        expected = render(light, dark)
        if args.check:
            if not target.is_file() or target.read_bytes() != expected:
                print(f"MISMATCH {target.relative_to(NEO_ROOT)}")
                mismatches += 1
            else:
                print(f"OK {target.relative_to(NEO_ROOT)}")
        else:
            target.write_bytes(expected)
            print(f"wrote {target.relative_to(NEO_ROOT)}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
