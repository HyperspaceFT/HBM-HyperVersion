"""Shared paths and helpers for the Goal 29 acceptance tools (Mac, loopback only).

Every tool keeps its state under build/migration/accept-goal29/ of the NEO checkout that holds this file; nothing here
writes into the repository's tracked tree. Python standard library only.
"""
import datetime
import hashlib
import json
import os
import socket
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
STATE = REPO / 'build' / 'migration' / 'accept-goal29'
SESSION = STATE / 'server-session.json'
PASSWORD = STATE / 'rcon.password'
WORLDS = STATE / 'worlds.json'
CLIENTS = STATE / 'clients'
WORLD_PREFIX = 'accept-goal29-'
LOOPBACK = '127.0.0.1'
BUILD_SH = REPO / 'tools' / 'migration' / 'build.sh'
GRADLE_USER_HOME = REPO / '.gradle' / 'user-home'


def now_tag():
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def offline_uuid(name):
    """UUID.nameUUIDFromBytes(("OfflinePlayer:" + name).getBytes(UTF_8)): MD5 with the version 3 and variant bits set."""
    return str(uuid.UUID(bytes=hashlib.md5(('OfflinePlayer:' + name).encode('utf-8')).digest(), version=3))


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((LOOPBACK, port))
        except OSError:
            return False
    return True


def pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def rel(path):
    """Repository-relative path for messages and records, absolute when outside the repository."""
    path = Path(path).resolve()
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def resolve(path):
    """Paths on the command line are relative to the repository root, not the shell's directory."""
    path = Path(path)
    return path if path.is_absolute() else REPO / path
