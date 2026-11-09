#!/usr/bin/env python3
"""Minimal Source RCON client for the disposable acceptance server. Connects to 127.0.0.1 only.

Usage (from the NEO root):
  python3 -B -X utf8 tools/migration/acceptance/rcon.py "list" "time query gametime"
  python3 -B -X utf8 tools/migration/acceptance/rcon.py -f cmds.txt
Port and password come from build/migration/accept-goal29/server-session.json and rcon.password (written by
server.py start); --port overrides the port. Commands are sent one at a time, a leading "/" is dropped, blank lines and
lines starting with "#" in a command file are skipped, and every reply is printed after "> command".
The password is never printed or logged.
"""
import argparse
import socket
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

AUTH, AUTH_RESPONSE, EXEC, RESPONSE = 3, 2, 2, 0
MARKER_TYPE = 0x64
# RconClient reads one packet per read() of at most 1460 bytes; 4+4+4 header bytes and two NULs leave 1446 for the body.
MAX_BODY = 1446


def encode(request_id, kind, body):
    payload = body.encode('utf-8')
    if len(payload) > MAX_BODY:
        raise ValueError('RCON command longer than %d bytes' % MAX_BODY)
    return struct.pack('<iii', len(payload) + 10, request_id, kind) + payload + b'\x00\x00'


def decode(data):
    """Split one packet off the front of data: (request_id, kind, body, rest) or None when incomplete."""
    if len(data) < 4:
        return None
    (length,) = struct.unpack_from('<i', data, 0)
    if len(data) < 4 + length:
        return None
    request_id, kind = struct.unpack_from('<ii', data, 4)
    body = data[12:4 + length - 2].decode('utf-8', 'replace')
    return request_id, kind, body, data[4 + length:]


class Rcon:
    def __init__(self, port, password, timeout=30.0):
        self.sock = socket.create_connection((common.LOOPBACK, port), timeout=timeout)
        self.buf = b''
        self.next_id = 1
        rid = self._id()
        self.sock.sendall(encode(rid, AUTH, password))
        got_id, kind, _ = self._read()
        if got_id == -1 or got_id != rid or kind != AUTH_RESPONSE:
            raise PermissionError('RCON authentication failed')

    def _id(self):
        self.next_id += 1
        return self.next_id

    def _read(self):
        while True:
            packet = decode(self.buf)
            if packet:
                request_id, kind, body, self.buf = packet
                return request_id, kind, body
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('RCON connection closed by the server')
            self.buf += chunk

    def command(self, text):
        rid = self._id()
        self.sock.sendall(encode(rid, EXEC, text))
        first_id, _, first = self._read()
        if first_id == -1:
            raise PermissionError('RCON session is not authenticated')
        # The server writes every 4096-byte fragment before it reads again, so a marker request sent after the first
        # fragment is answered after the last one ("Unknown request 64").
        marker = self._id()
        self.sock.sendall(encode(marker, MARKER_TYPE, ''))
        parts = [first]
        while True:
            got_id, _, body = self._read()
            if got_id == marker:
                break
            parts.append(body)
        return ''.join(parts)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def session_port():
    session = common.read_json(common.SESSION)
    if not session:
        raise SystemExit('No server session in %s; start one with server.py start or pass --port.' % common.rel(common.SESSION))
    return session['rcon_port']


def read_password():
    if not common.PASSWORD.is_file():
        raise SystemExit('No RCON password file at %s; start the server with server.py.' % common.rel(common.PASSWORD))
    return common.PASSWORD.read_text(encoding='utf-8').strip()


def connect(port=None, timeout=30.0):
    return Rcon(port or session_port(), read_password(), timeout)


def load_commands(args):
    commands = list(args.commands)
    if args.file:
        for line in common.resolve(args.file).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                commands.append(line)
    return [c[1:] if c.startswith('/') else c for c in commands]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('commands', nargs='*')
    ap.add_argument('-f', '--file', help='command file, one command per line (relative to the NEO root)')
    ap.add_argument('--port', type=int)
    ap.add_argument('--wait', type=float, default=0.0, help='seconds to wait between commands')
    args = ap.parse_args(argv)
    commands = load_commands(args)
    if not commands:
        ap.error('no commands')
    rcon = connect(args.port)
    try:
        for i, command in enumerate(commands):
            if i and args.wait:
                time.sleep(args.wait)
            print('> ' + command)
            reply = rcon.command(command)
            print(reply if reply else '(no output)')
            sys.stdout.flush()
    finally:
        rcon.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
