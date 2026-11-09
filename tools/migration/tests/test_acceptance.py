import hashlib
import importlib
import socket
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ACCEPTANCE = Path(__file__).resolve().parents[1] / "acceptance"
sys.path.insert(0, str(ACCEPTANCE))
common = importlib.import_module("common")
rcon = importlib.import_module("rcon")
server = importlib.import_module("server")
client = importlib.import_module("client")
chat = importlib.import_module("chat")


def java_offline_uuid(name):
    # UUID.nameUUIDFromBytes: MD5, then version 3 in byte 6 and the IETF variant in byte 8.
    b = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode("utf-8")).digest())
    b[6] = (b[6] & 0x0F) | 0x30
    b[8] = (b[8] & 0x3F) | 0x80
    h = b.hex()
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:])


class FakeRcon(threading.Thread):
    """Answers like RconClient: one packet per read, replies split at 4096 bytes, unknown types echoed."""

    def __init__(self, password, reply):
        super().__init__(daemon=True)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.password, self.reply = password, reply
        self.received = []

    def send(self, conn, rid, kind, body):
        data = body.encode("utf-8")
        conn.sendall(struct.pack("<iii", len(data) + 10, rid, kind) + data + b"\x00\x00")

    def run(self):
        conn, _ = self.sock.accept()
        with conn:
            while True:
                head = conn.recv(4)
                if len(head) < 4:
                    return
                (length,) = struct.unpack("<i", head)
                body = b""
                while len(body) < length:
                    body += conn.recv(length - len(body))
                rid, kind = struct.unpack_from("<ii", body)
                text = body[8:-2].decode("utf-8")
                self.received.append((kind, text))
                if kind == 3:
                    self.send(conn, rid if text == self.password else -1, 2, "")
                elif kind == 2:
                    whole = self.reply.encode("utf-8")
                    for start in range(0, len(whole), 4096):
                        self.send(conn, rid, 0, whole[start:start + 4096].decode("utf-8"))
                else:
                    self.send(conn, rid, 0, "Unknown request %x" % kind)


class AcceptanceToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_offline_uuid_matches_java(self):
        for name in ("alice", "bob", "Player123"):
            self.assertEqual(common.offline_uuid(name), java_offline_uuid(name))
        self.assertEqual(server.ops_entries(["alice"])[0]["uuid"], java_offline_uuid("alice"))

    def test_rcon_packet_round_trip_and_limit(self):
        packet = rcon.encode(7, rcon.EXEC, "list")
        self.assertEqual(rcon.decode(packet + b"rest"), (7, rcon.EXEC, "list", b"rest"))
        self.assertIsNone(rcon.decode(packet[:-1]))
        with self.assertRaises(ValueError):
            rcon.encode(1, rcon.EXEC, "x" * (rcon.MAX_BODY + 1))

    def test_rcon_joins_fragmented_reply(self):
        reply = "".join("line %05d\n" % i for i in range(1000))  # 11,000 bytes = three fragments
        fake = FakeRcon("secret", reply)
        fake.start()
        conn = rcon.Rcon(fake.port, "secret", timeout=10)
        try:
            self.assertEqual(conn.command("help"), reply)
        finally:
            conn.close()
        self.assertEqual([k for k, _ in fake.received], [3, 2, rcon.MARKER_TYPE])

    def test_rcon_bad_password(self):
        fake = FakeRcon("secret", "")
        fake.start()
        with self.assertRaises(PermissionError):
            rcon.Rcon(fake.port, "wrong", timeout=10)

    def test_rcon_command_file(self):
        f = self.root / "cmds.txt"
        f.write_text("# comment\n/list\n\n  say hi  \n", encoding="utf-8")
        args = type("A", (), {"commands": ["/seed"], "file": str(f)})()
        self.assertEqual(rcon.load_commands(args), ["seed", "list", "say hi"])

    def test_properties_rewrite_keeps_other_lines(self):
        p = self.root / "server.properties"
        p.write_text("#comment\nmotd=old\nlevel-name=world\npvp=true\n", encoding="utf-8")
        server.write_properties(p, {"level-name": "accept-goal29-x", "enable-rcon": "true"})
        self.assertEqual(p.read_text(encoding="utf-8"),
                         "#comment\nmotd=old\nlevel-name=accept-goal29-x\npvp=true\nenable-rcon=true\n")

    def test_backup_restore_round_trip(self):
        run = self.root / "run"
        (run / "config" / "sub").mkdir(parents=True)
        (run / "server.properties").write_bytes(b"a=1\r\n")
        (run / "config" / "sub" / "x.toml").write_bytes(b"x")
        dest = self.root / "backup"
        manifest = server.backup(run, dest)
        self.assertIsNone(manifest["eula.txt"])
        self.assertIn("config/sub/x.toml", manifest)
        (run / "server.properties").write_bytes(b"rcon.password=p\n")
        (run / "config" / "sub" / "x.toml").unlink()
        (run / "config" / "new.bak").write_bytes(b"n")
        (run / "usernamecache.json").write_bytes(b"{}")
        report = server.restore(run, dest)
        self.assertTrue(report["ok"])
        self.assertEqual((run / "server.properties").read_bytes(), b"a=1\r\n")
        self.assertEqual((run / "config" / "sub" / "x.toml").read_bytes(), b"x")
        self.assertFalse((run / "config" / "new.bak").exists())
        self.assertFalse((run / "usernamecache.json").exists())
        self.assertEqual(report["removed_new_config_files"], ["config/new.bak"])

    def test_delete_world_only_for_registered_worlds(self):
        saved = common.WORLDS, common.SESSION
        common.WORLDS, common.SESSION = self.root / "worlds.json", self.root / "session.json"
        self.addCleanup(lambda: setattr(common, "WORLDS", saved[0]) or setattr(common, "SESSION", saved[1]))
        (self.root / "run" / "accept-goal29-mine").mkdir(parents=True)
        (self.root / "run" / "accept-goal29-other").mkdir(parents=True)
        server.register_world(self.root / "run" / "accept-goal29-mine", "mine")
        args = type("A", (), {"root": str(self.root)})
        args.tag = "other"
        with self.assertRaises(SystemExit):
            server.cmd_delete_world(args)
        self.assertTrue((self.root / "run" / "accept-goal29-other").is_dir())
        args.tag = "mine"
        self.assertEqual(server.cmd_delete_world(args), 0)
        self.assertFalse((self.root / "run" / "accept-goal29-mine").exists())
        with self.assertRaises(SystemExit):
            server.cmd_delete_world(args)

    def _isolate_state(self):
        saved = {k: getattr(common, k) for k in ("STATE", "SESSION", "PASSWORD", "WORLDS")}
        common.STATE = self.root / "state"
        common.SESSION, common.PASSWORD, common.WORLDS = (common.STATE / n for n in ("s.json", "pw", "w.json"))
        common.STATE.mkdir()
        self.addCleanup(lambda: [setattr(common, k, v) for k, v in saved.items()])

    def test_restore_mismatch_keeps_session(self):
        self._isolate_state()
        run = self.root / "run"
        run.mkdir()
        (run / "ops.json").write_text("[]", encoding="utf-8")
        dest = self.root / "backup"
        server.backup(run, dest)
        (run / "ops.json").write_text("[{}]", encoding="utf-8")
        (dest / "files" / "ops.json").write_text("changed backup copy", encoding="utf-8")  # restore cannot match
        session = dict(run=str(run), backup=str(dest), tag="t", started="x")
        common.write_json(common.SESSION, session)
        common.PASSWORD.write_text("pw", encoding="utf-8")
        report = server.finish(session, {})
        self.assertEqual(report["mismatched"], ["ops.json"])
        self.assertTrue(common.SESSION.exists())
        self.assertTrue(common.PASSWORD.exists())

    def test_restore_leaves_symlinked_config_files(self):
        run = self.root / "run"
        (run / "config").mkdir(parents=True)
        target = self.root / "elsewhere.toml"
        target.write_text("keep", encoding="utf-8")
        dest = self.root / "backup"
        server.backup(run, dest)
        (run / "config" / "link.toml").symlink_to(target)
        report = server.restore(run, dest)
        self.assertTrue((run / "config" / "link.toml").is_symlink())
        self.assertEqual(target.read_text(encoding="utf-8"), "keep")
        self.assertEqual(report["removed_new_config_files"], [])

    def test_capture_refuses_a_session_of_another_checkout(self):
        self._isolate_state()
        common.write_json(common.SESSION, dict(run=str(self.root / "old-27d" / "run"), tag="old"))
        args = type("A", (), {"without_session": False, "timeout": 1, "wait_title": False})()
        with self.assertRaises(SystemExit) as caught:
            client.cmd_capture(args)
        self.assertIn("not with --root", str(caught.exception))

    def test_client_program_args_and_options(self):
        src = self.root / "clientRunProgramArgs.txt"
        src.write_text("# Main Class\nMain\n\n--launchTarget\nforgeclientdev\n--gameDir\n.\n", encoding="utf-8")
        text = client.program_args(src, self.root / "c" / "alice", "alice", ["--quickPlayMultiplayer", "127.0.0.1:25565"])
        lines = text.splitlines()
        self.assertEqual(lines[lines.index("--gameDir") + 1], str(self.root / "c" / "alice"))
        self.assertEqual(lines[-4:], ["--username", "alice", "--quickPlayMultiplayer", "127.0.0.1:25565"])
        opts = self.root / "options.txt"
        opts.write_text("lang:en_us\nfov:0.0\n", encoding="utf-8")
        client.write_options(opts, dict(client.BASE_OPTIONS, lang="zh_cn"))
        values = dict(l.split(":", 1) for l in opts.read_text(encoding="utf-8").splitlines())
        self.assertEqual(values["lang"], "zh_cn")
        self.assertEqual(values["fov"], "0.0")
        self.assertEqual(values["onboardAccessibility"], "false")
        self.assertEqual(values["pauseOnLostFocus"], "false")
        with self.assertRaises(SystemExit):
            client.name_ok("a b")

    def test_chat_lines(self):
        lines = ["[08Nov2026 14:18:58.575] [Render thread/INFO] [x/]: [System] [CHAT] Loaded world",
                 "[14:20:00] [Render thread/INFO] [minecraft/ChatComponent]: [CHAT] bob joined the game",
                 "[14:21:00] [Server thread/INFO] other line"]
        self.assertEqual(chat.chat_lines(lines), ["[14:18:58] Loaded world", "[14:20:00] bob joined the game"])
        self.assertEqual(chat.chat_lines(lines, since="14:19:00"), ["[14:20:00] bob joined the game"])
        self.assertEqual(chat.chat_lines(lines, grep="Loaded"), ["[14:18:58] Loaded world"])


if __name__ == "__main__":
    unittest.main()
