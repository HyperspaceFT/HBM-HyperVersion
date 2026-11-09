#!/usr/bin/env python3
"""Commands that find the non-air cells of a box (ported from Goal 28's cellchk.py, coordinates and path removed).

Usage (from the NEO root): cellchk.py x0 x1 y0 y1 z0 z1 [--out FILE] [--say]
Default output is one `execute unless block X Y Z minecraft:air` per cell; over RCON each reply is "Test passed" for a
non-air cell and "Test failed" for air, in the order x, z within each y. --say writes the Goal 28 chat form
(`... run say notair X Y Z`) for a single-player chat or a datapack function.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def commands(x0, x1, y0, y1, z0, z1, say=False):
    out = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if say:
                    out.append(f'execute unless block {x} {y} {z} minecraft:air run say notair {x} {y} {z}')
                else:
                    out.append(f'execute unless block {x} {y} {z} minecraft:air')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('box', nargs=6, type=int, metavar='N', help='x0 x1 y0 y1 z0 z1')
    ap.add_argument('--out')
    ap.add_argument('--say', action='store_true')
    a = ap.parse_args(argv)
    text = '\n'.join(commands(*a.box, say=a.say)) + '\n'
    if a.out:
        out = common.resolve(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8')
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
