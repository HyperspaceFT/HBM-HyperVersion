#!/usr/bin/env python3
"""Commands that report every block entity in a box (ported from Goal 28's findbe.py, paths removed).

Usage (from the NEO root): findbe.py x0 x1 y0 y1 z0 z1 [--out FILE] [--tellraw]
Default output is one `execute if data block ... run data get block X Y Z id` per position, whose reply comes back over
RCON (pipe to `rcon.py -f`). --tellraw writes the Goal 28 chat form for a single-player chat or a datapack function.
Without --out the commands go to stdout.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def commands(x0, x1, y0, y1, z0, z1, tellraw=False):
    out = []
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                if tellraw:
                    out.append(f'execute if data block {x} {y} {z} id unless block {x} {y} {z} minecraft:air run tellraw @a '
                               f'["BE {x} {y} {z} ",{{"nbt":"id","block":"{x} {y} {z}"}}]')
                else:
                    out.append(f'execute if data block {x} {y} {z} id run data get block {x} {y} {z} id')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('box', nargs=6, type=int, metavar='N', help='x0 x1 y0 y1 z0 z1')
    ap.add_argument('--out')
    ap.add_argument('--tellraw', action='store_true')
    a = ap.parse_args(argv)
    text = '\n'.join(commands(*a.box, tellraw=a.tellraw)) + '\n'
    if a.out:
        out = common.resolve(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8')
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
