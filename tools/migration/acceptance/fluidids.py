#!/usr/bin/env python3
"""Numeric fluid IDs in NEO's Fluids.java declaration order (ported from Goal 28's fluidids.py, path removed).

Usage (from the NEO root): fluidids.py [NAME ...]
With no names prints the first entries and the count; otherwise prints `NAME id` for each (None when unknown).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

FLUIDS = common.REPO / 'src' / 'main' / 'java' / 'com' / 'hbm' / 'inventory' / 'fluid' / 'Fluids.java'


def fluid_ids(path=FLUIDS):
    text = Path(path).read_text(encoding='utf-8')
    names = re.findall(r'^\s*([A-Z0-9_]+)\s*=\s*new FluidType(?:\w+)?\("', text, re.M)
    return {n: i for i, n in enumerate(names)}


def main(argv=None):
    names = sys.argv[1:] if argv is None else argv
    ids = fluid_ids()
    if not names:
        print(list(ids)[:5], len(ids))
    for name in names:
        print(name, ids.get(name.upper()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
