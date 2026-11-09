#!/usr/bin/env python3
"""Compare a mod JAR's resources with src/generated/resources and src/main/resources (ported from Goal 28's gencmp.py).

Usage (from the NEO root): gencmp.py [JAR]   (default build/libs/hbmsntm-198A.jar)
Prints, per resource root, how many files it has and which ones exist in the JAR with different bytes.
"""
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def compare(jar):
    with zipfile.ZipFile(jar) as z:
        names = set(z.namelist())
        result = {}
        for label, base in (('generated', common.REPO / 'src/generated/resources'), ('main', common.REPO / 'src/main/resources')):
            diff, n = [], 0
            for d, _, files in os.walk(base):
                for f in files:
                    p = Path(d) / f
                    name = p.relative_to(base).as_posix()
                    n += 1
                    if name in names and z.read(name) != p.read_bytes():
                        diff.append(name)
            result[label] = (n, sorted(diff))
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    jar = common.resolve(args[0]) if args else common.REPO / 'build/libs/hbmsntm-198A.jar'
    for label, (n, diff) in compare(jar).items():
        print(label, 'files', n, 'differ', len(diff), diff[:10])
    return 0


if __name__ == '__main__':
    sys.exit(main())
