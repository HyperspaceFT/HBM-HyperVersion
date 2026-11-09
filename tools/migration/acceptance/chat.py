#!/usr/bin/env python3
"""Print the [CHAT] lines of a client log (dedicated servers have none: use RCON replies and the server log).

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/chat.py --client alice -n 20
  python3 -B -X utf8 tools/migration/acceptance/chat.py build/migration/accept-goal29/clients/bob/logs/latest.log
  python3 -B -X utf8 tools/migration/acceptance/chat.py --client alice --grep joined --since "12:30:00"
A log path is relative to the NEO root; .gz logs are read too. --server prints the server's lines instead, from the
Gradle-output log of the open server.py session (or the newest server-*.log), filtered by --grep.
"""
import argparse
import gzip
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TIME = re.compile(r'^\[(?:\d\d\w{3}\d{4} )?(\d\d:\d\d:\d\d)')


def read_lines(path):
    path = Path(path)
    data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return data.decode('utf-8', 'replace').splitlines()


def chat_lines(lines, since=None, grep=None, chat_only=True):
    pattern = re.compile(grep) if grep else None
    out = []
    for line in lines:
        if since:
            stamp = TIME.match(line)
            if stamp and stamp.group(1) < since:
                continue
        if chat_only:
            if '[CHAT] ' not in line:
                continue
            stamp = TIME.match(line)
            text = line.split('[CHAT] ', 1)[1]
            line = ('[%s] ' % stamp.group(1) if stamp else '') + text
        if pattern and not pattern.search(line):
            continue
        out.append(line)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log', nargs='?')
    ap.add_argument('--client', help='client name under build/migration/accept-goal29/clients/')
    ap.add_argument('--server', action='store_true', help='the server session log, all lines (use --grep)')
    ap.add_argument('-n', type=int, default=0, help='last N lines only')
    ap.add_argument('--grep')
    ap.add_argument('--since', help='HH:MM:SS; skip earlier lines')
    args = ap.parse_args(argv)
    if sum(bool(x) for x in (args.log, args.client, args.server)) != 1:
        ap.error('give one of: a log path, --client NAME, --server')
    if args.client:
        path = common.CLIENTS / args.client / 'logs' / 'latest.log'
    elif args.server:
        session = common.read_json(common.SESSION)
        if session:
            path = Path(session['log'])
        else:
            logs = sorted((p for p in (common.STATE / 'logs').glob('server-*.log') if not p.name.endswith('-latest.log')),
                          key=lambda p: p.stat().st_mtime)
            if not logs:
                ap.error('no server log under build/migration/accept-goal29/logs/')
            path = logs[-1]
    else:
        path = common.resolve(args.log)
    lines = chat_lines(read_lines(path), args.since, args.grep, chat_only=not args.server)
    if args.n:
        lines = lines[-args.n:]
    sys.stdout.reconfigure(encoding='utf-8')
    for line in lines:
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
