#!/usr/bin/env python3
"""Summarise /loot test drops from chat (ported from Goal 28's sumloot.py; the chat file is now an argument).

Usage (from the NEO root): sumloot.py CHAT_FILE [--layout 3,3,1,1]
CHAT_FILE holds chat lines (chat.py output, or a client log): a "[Dev] <name>", "[Server] <name>" or "[Rcon] <name>"
header from `say`, then the
drop lines. Drops are read from the Chinese message (掉落了N个[物品]) and the English one (Dropped N [item]). --layout
groups each block's drops in order; the default matches Goal 28: pickaxe x3, Fortune III x3, Silk Touch x1, stick x1.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

HEADER = re.compile(r'\[(?:Dev|Server|Rcon)\] (\S+)')
DROP = [re.compile(r'掉落了(\d+)个\[(.+?)\]'), re.compile(r'Dropped (\d+) \[(.+?)\]')]
LABELS = ('pick', 'F3', 'silk', 'stick')


def parse(lines):
    rows, cur = {}, None
    for line in lines:
        m = HEADER.search(line)
        if m:
            cur = m.group(1)
            rows[cur] = []
            continue
        for rx in DROP:
            m = rx.search(line)
            if m and cur:
                rows[cur].append((int(m.group(1)), m.group(2)))
                break
        else:
            if cur and ('掉落' in line or 'Dropped' in line):
                rows[cur].append((0, line[-30:]))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('chat')
    ap.add_argument('--layout', default='3,3,1,1')
    a = ap.parse_args(argv)
    sizes = [int(n) for n in a.layout.split(',')]
    lines = common.resolve(a.chat).read_text(encoding='utf-8', errors='replace').splitlines()
    sys.stdout.reconfigure(encoding='utf-8')
    for block, drops in parse(lines).items():
        parts, i = [], 0
        for label, size in zip(LABELS + tuple('g%d' % k for k in range(4, len(sizes))), sizes):
            parts.append('%s: %s' % (label, ' '.join('%d%s' % d for d in drops[i:i + size])))
            i += size
        print(block, '| ' + ' | '.join(parts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
