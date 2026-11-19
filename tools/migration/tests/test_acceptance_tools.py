"""Tests of the scripted-acceptance tools: drive.py (step channel, verdicts, reports), closure.py and stations.py.

No game runs here: the executor is replaced by a thread that answers the step files.
"""
import argparse
import importlib
import json
import re
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path


ACCEPTANCE = Path(__file__).resolve().parents[1] / "acceptance"
sys.path.insert(0, str(ACCEPTANCE))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "acceptance" / "scenarios"))
common = importlib.import_module("common")
client = importlib.import_module("client")
drive = importlib.import_module("drive")
closure = importlib.import_module("closure")
stations = importlib.import_module("stations")


class FakeExecutor(threading.Thread):
    """Answers in/<seq>.json with out/<seq>.json in order, like the executor; `answer` maps a step to its result."""

    def __init__(self, directory, answer=None):
        super().__init__(daemon=True)
        self.dir = Path(directory)
        self.answer = answer or (lambda spec: dict(status="ok"))
        self.stop = False
        self.seen = []

    def run(self):
        done = [int(p.stem) for p in (self.dir / "out").glob("*.json")]
        seq = max(done + [0])
        while not self.stop:
            path = self.dir / "in" / ("%06d.json" % (seq + 1))
            if path.is_file():
                seq += 1
                spec = json.loads(path.read_text(encoding="utf-8"))
                self.seen.append(spec)
                result = dict(seq=seq, op=spec.get("op"), duration_ms=1, **self.answer(spec))
                (self.dir / "out" / path.name).write_text(json.dumps(result), encoding="utf-8")
            else:
                time.sleep(0.005)


def fake_module(ref, ids, body, capture=None):
    feature = ref.split("/")[0]
    module = types.SimpleNamespace(REF=ref, SCENARIO=dict(id=feature + ".x", feature=feature, title="t", capture=capture or {}))
    module.expectations = lambda: [dict(id=feature + "." + i, text=i) for i in ids]
    module.run = body
    return module


class DriveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def channel(self, answer=None, alive=lambda: True):
        ch = drive.Channel("c", self.dir / "c", alive=alive)
        ex = FakeExecutor(self.dir / "c", answer)
        ex.start()
        self.addCleanup(setattr, ex, "stop", True)
        return ch, ex

    def run_obj(self):
        run = drive.Run(argparse.Namespace(out=str(self.dir / "run"), run="r", argv=None, option=[]))
        run.capture = dict(drive.DEFAULT_CAPTURE)
        run.current_lang = run.capture["lang"]
        return run

    def test_channel_round_trip_and_sequence_resume(self):
        ch, ex = self.channel(lambda spec: dict(status="ok", echo=spec.get("n")))
        self.assertEqual(ch.send(dict(op="wait", n=1))["echo"], 1)
        r = ch.send(dict(op="wait", n=2))
        self.assertEqual((r["seq"], r["echo"], r["client"]), (2, 2, "c"))
        self.assertIn("wall_ms", r)
        ex.stop = True
        # a new channel on the same directory continues after the last step instead of reusing a number
        self.assertEqual(drive.Channel("c", self.dir / "c").seq, 2)

    def test_channel_reports_a_dead_client_and_a_missing_hello(self):
        ch = drive.Channel("dead", self.dir / "dead", alive=lambda: False)
        with self.assertRaises(drive.ClientGone):
            ch.hello(2)
        with self.assertRaises(drive.ClientGone):
            ch.send(dict(op="wait"), timeout=0.2)

    def test_failed_step_raises_unless_allowed(self):
        ch, _ = self.channel(lambda spec: dict(status="fail", reason="nope") if spec["op"] == "bad" else dict(status="ok"))
        ctx = drive.Context(self.run_obj(), fake_module("f/a", [], None), {"c": ch})
        with self.assertRaises(drive.StepFailed):
            ctx.step("bad")
        self.assertEqual(ctx.step("bad", allow_fail=True)["status"], "fail")
        ctx.check("f.one", True)
        with self.assertRaises(ValueError):
            ctx.review("f.one")

    def test_a_failed_step_leaves_the_undecided_expectations_not_run_with_its_reason(self):
        ch, ex = self.channel(lambda spec: dict(status="fail", reason="timeout") if spec["op"] == "shot" else dict(status="ok"))

        def body(ctx):
            ctx.check("f.first", True, "seen")
            ctx.step("shot")
            ctx.check("f.second", True)
        records = drive.run_scenarios(self.run_obj(), [fake_module("f/a", ["first", "second", "third"], body)], {"c": ch})
        verdicts = {e["id"]: (e["verdict"], e["detail"]) for e in records[0]["expectations"]}
        self.assertEqual(verdicts["f.first"], ("pass", "seen"))
        self.assertEqual(verdicts["f.second"][0], "not-run")
        self.assertIn("timeout", verdicts["f.second"][1])
        self.assertEqual(verdicts["f.third"][0], "not-run")
        # the modifiers and the held keys are released after every scenario, also after a failure
        tail = ex.seen[-1 - len(drive.HELD_KEYS):]
        self.assertEqual(tail[0], dict(op="mod", shift=False, control=False, alt=False))
        self.assertEqual([t["key"] for t in tail[1:]], list(drive.HELD_KEYS))
        self.assertTrue(all(t["op"] == "key" and t["action"] == "release" for t in tail[1:]))

    def test_a_scenario_error_or_an_undeclared_verdict_cannot_pass(self):
        ch, _ = self.channel()

        def broken(ctx):
            ctx.check("f.first", True)
            raise KeyError("missing field")
        records = drive.run_scenarios(self.run_obj(), [fake_module("f/a", ["first", "second"], broken)], {"c": ch})
        self.assertEqual([e["verdict"] for e in records[0]["expectations"]], ["pass", "not-run"])
        self.assertIn("scenario error", records[0]["error"])
        with self.assertRaises(SystemExit):
            drive.run_scenarios(self.run_obj(), [fake_module("f/b", ["one"], lambda ctx: ctx.check("f.other", True))], {"c": ch})

    def test_capture_mismatch_runs_nothing(self):
        ch, ex = self.channel()
        called = []
        module = fake_module("f/a", ["one"], lambda ctx: called.append(1), capture=dict(window=[1280, 720]))
        records = drive.run_scenarios(self.run_obj(), [module], {"c": ch})
        self.assertEqual(called, [])
        self.assertEqual(records[0]["expectations"][0]["verdict"], "not-run")
        self.assertIn("window", records[0]["expectations"][0]["detail"])

    def test_judgment_overrides_review_in_the_report_and_keeps_the_machine_verdict(self):
        run_dir = self.dir / "run"
        run_dir.mkdir()
        exp = [dict(id="f.look", text="looks right", verdict="review", detail="sheet", evidence=["s.png"]),
               dict(id="f.state", text="state", verdict="pass", detail="", evidence=[])]
        common.write_json(run_dir / "results.json", dict(
            run="run", group="solo", clients=["c"], world=dict(name="w"), total_s=1.0, capture={}, failure=None, timings={},
            step_stats=drive.step_stats([dict(op="shot", duration_ms=10, wall_ms=12), dict(op="shot", duration_ms=30, wall_ms=40, status="fail")]),
            scenarios=[dict(ref="f/a", id="f.a", title="A", duration_s=1.0, error=None, expectations=exp)]))
        drive.main(["judge", str(run_dir), "f.look", "--verdict", "pass", "--note", "arrows right"])
        judgments = common.read_json(run_dir / "judgments.json")
        self.assertEqual((judgments["f.look"]["verdict"], judgments["f.look"]["machine"]), ("pass", "review"))
        text = (run_dir / "results.md").read_text(encoding="utf-8")
        self.assertIn("通过 2 不通过 0 待人看 0", text)
        self.assertIn("reviewer: arrows right (machine: 待人看", text)
        self.assertIn("| shot | 2 | 2 | 20 | 30 | 26 | 40 |", text)
        with self.assertRaises(SystemExit):
            drive.main(["judge", str(run_dir), "f.unknown", "--verdict", "pass"])
        with self.assertRaises(SystemExit):
            drive.main(["judge", str(run_dir), "f.look", "--verdict", "review"])
        with self.assertRaises(SystemExit):
            drive.main(["judge", str(run_dir), "f.state", "--verdict", "fail"])

    def test_scenario_ids_must_match_their_directory(self):
        root = self.dir / "scenarios" / "feat"
        root.mkdir(parents=True)
        (root / "ok.py").write_text("SCENARIO = dict(id='feat.ok', feature='feat')\n"
                                    "def expectations():\n    return [dict(id='feat.a'), dict(id='feat.a')]\n", encoding="utf-8")
        (root / "bad.py").write_text("SCENARIO = dict(id='other.bad', feature='other')\n", encoding="utf-8")
        saved = drive.SCENARIOS
        drive.SCENARIOS = self.dir / "scenarios"
        try:
            with self.assertRaises(SystemExit):
                drive.load("feat/bad")
            module = drive.load("feat/ok")
            with self.assertRaises(SystemExit):
                drive.expectation_list(module)
        finally:
            drive.SCENARIOS = saved

    def test_shipped_scenarios_load_and_do_not_name_migration_records(self):
        refs = ["%s/%s" % (p.parent.name, p.stem) for p in drive.scenario_files()]
        self.assertIn("conveyor-cranes/crane_faces", refs)
        for ref in refs:
            drive.expectation_list(drive.load(ref))
            text = (drive.SCENARIOS / (ref + ".py")).read_text(encoding="utf-8")
            self.assertNotIn("migration/", text, ref)
            self.assertIsNone(re.search(r"GOAL\d|\bG-\d\d\b|\bS\d\.\d|\b31[A-F]\b", text), ref)


    def test_a_scenario_may_register_expectations_under_its_listed_features(self):
        root = self.dir / "scenarios" / "stage-one"
        root.mkdir(parents=True)
        (root / "line.py").write_text(
            "SCENARIO = dict(id='stage-one.line', feature='stage-one', features=['blast-furnace', 'press'])\n"
            "def expectations():\n    return [dict(id='stage-one.a'), dict(id='blast-furnace.b'), dict(id='press.c')]\n", encoding="utf-8")
        (root / "stray.py").write_text(
            "SCENARIO = dict(id='stage-one.stray', feature='stage-one', features=['press'])\n"
            "def expectations():\n    return [dict(id='anvil.x')]\n", encoding="utf-8")
        (root / "badlist.py").write_text("SCENARIO = dict(id='stage-one.badlist', feature='stage-one', features='press')\n", encoding="utf-8")
        saved = drive.SCENARIOS
        drive.SCENARIOS = self.dir / "scenarios"
        try:
            module = drive.load("stage-one/line")
            self.assertEqual(drive.features_of(module), ["stage-one", "blast-furnace", "press"])
            self.assertEqual([e["id"] for e in drive.expectation_list(module)], ["stage-one.a", "blast-furnace.b", "press.c"])
            with self.assertRaises(SystemExit):
                drive.expectation_list(drive.load("stage-one/stray"))
            with self.assertRaises(SystemExit):
                drive.load("stage-one/badlist")
        finally:
            drive.SCENARIOS = saved
        # a scenario without the list keeps the old rule: only its own feature
        plain = fake_module("f/a", ["one"], None)
        self.assertEqual(drive.features_of(plain), ["f"])

    def test_finished_scenarios_keep_their_verdicts_when_the_client_dies_later(self):
        ch, _ = self.channel()
        run = self.run_obj()

        def dies(ctx):
            raise drive.ClientGone("client exited")
        with self.assertRaises(drive.ClientGone):
            drive.run_scenarios(run, [fake_module("f/a", ["one"], lambda ctx: ctx.check("f.one", True)),
                                      fake_module("f/b", ["two"], dies)], {"c": ch})
        self.assertEqual([(r["ref"], [e["verdict"] for e in r["expectations"]]) for r in run.records], [("f/a", ["pass"])])

    def test_world_settings_only_given_options_reach_newworld(self):
        none = argparse.Namespace(gamemode=None, difficulty=None, seed=None, preset=None, no_cheats=False)
        self.assertEqual(drive.world_settings(none), {})
        some = argparse.Namespace(gamemode="survival", difficulty="normal", seed=7, preset="normal", no_cheats=True)
        self.assertEqual(drive.world_settings(some), dict(gamemode="survival", difficulty="normal", seed=7, preset="normal", cheats=False))
        with self.assertRaises(SystemExit):
            drive.main(["run", "--run", "x", "--preset", "flatt", "f/a"])

    def test_server_reads_go_to_the_integrated_server_or_rcon(self):
        state = dict(game_time=100, sprinting=False, frozen=True, mean_tick_ms=1.0, tick_rate=20.0)
        ch, ex = self.channel(lambda spec: dict(status="ok", messages=["1, 2, 3 has the following block data: 5L"], result=5, **state)
                              if spec["op"] == "server" else dict(status="ok"))
        ctx = drive.Context(self.run_obj(), fake_module("f/a", [], None), {"c": ch})
        r = ctx.server("data get block 1 2 3 x")
        self.assertEqual((r["result"], r["game_time"], r["frozen"]), (5, 100, True))
        self.assertEqual(ex.seen[-1], dict(op="server", command="data get block 1 2 3 x", allow_error=False))

        class FakeRcon:
            sent = []

            def command(self, c):
                FakeRcon.sent.append(c)
                return {"tick query": "The game is sprinting\nTarget tick rate: 20.0 per second.\nAverage time per tick: 0.3ms",
                        "time query gametime": "The time is 4242"}.get(c, "1, 2, 3 has the following block data: 7")

            def close(self):
                pass
        mp = drive.Context(self.run_obj(), fake_module("f/a", [], None), {"c": ch}, rcon=FakeRcon)
        r = mp.server("data get block 1 2 3 x")
        self.assertEqual((r["game_time"], r["sprinting"], r["frozen"], r["result"]), (4242, True, False, None))
        self.assertEqual(r["messages"], ["1, 2, 3 has the following block data: 7"])
        self.assertEqual(FakeRcon.sent, ["data get block 1 2 3 x", "tick query", "time query gametime"])

    def test_sprint_waits_for_the_server_state_and_measures_game_ticks(self):
        clock = dict(t=1000, sprinting=False, polls=0)

        def answer(spec):
            if spec["op"] != "server":
                return dict(status="ok")
            command = spec.get("command") or ""
            if command.startswith("tick sprint "):
                if command == "tick sprint stop":
                    clock["sprinting"] = False
                else:
                    clock["sprinting"], clock["left"] = True, int(command.split()[-1]) + 1
            elif clock["sprinting"]:
                clock["polls"] += 1
                step = min(clock["left"], 400)
                clock["t"] += step
                clock["left"] -= step
                clock["sprinting"] = clock["left"] > 0
            return dict(status="ok", messages=[], result=0, game_time=clock["t"], sprinting=clock["sprinting"], frozen=True)
        ch, _ = self.channel(answer)
        run = self.run_obj()
        ctx = drive.Context(run, fake_module("f/a", [], None), {"c": ch})
        record = ctx.sprint(1000, poll_s=0.01, timeout_s=30, label="test")
        self.assertEqual((record["advanced"], record["stopped_early"], record["timed_out"], record["label"]), (1001, False, False, "test"))
        self.assertEqual(run.sprints, [record])
        # until() stops the sprint early; a sprint that never ends fails on the wall clock
        record = ctx.sprint(100000, until=lambda c: clock["t"] > 3000, poll_s=0.01, timeout_s=30)
        self.assertTrue(record["stopped_early"])
        self.assertFalse(clock["sprinting"])
        clock["polls"] = 0
        with self.assertRaises(drive.StepFailed):
            ctx.sprint(10 ** 9, poll_s=0.01, timeout_s=0.2)
        self.assertTrue(run.sprints[-1]["timed_out"])
        self.assertFalse(clock["sprinting"])
        # a check that raises during the sprint still leaves the server not sprinting

        def broken(c):
            raise RuntimeError("check failed")
        with self.assertRaises(RuntimeError):
            ctx.sprint(100000, until=broken, poll_s=0.01, timeout_s=30)
        self.assertFalse(clock["sprinting"])
        self.assertIn("check failed", run.sprints[-1]["error"])


class ReadingTests(unittest.TestCase):
    def test_snbt_values_tanks_and_power(self):
        lib = importlib.import_module("_lib")
        data = lib.data_value('1, 2, 3 has the following block data: {id: "hbmsntm:machine_zirnox", heat: 36159, water: 32000, '
                              'water_max: 32000, water_type: 1, steam: 0, steam_max: 8000, steam_type: "SUPERHOTSTEAM", '
                              'Items: [{Slot: 8b, id: "hbmsntm:rod_zirnox", count: 1, components: {"minecraft:custom_data": {life: 102025}}}], '
                              'f: 1.5f, l: [L; 1L, 2L], s: \'it\\\'s\'}')
        self.assertEqual(data["Items"][0]["components"]["minecraft:custom_data"]["life"], 102025)
        self.assertEqual((data["f"], data["l"], data["s"]), (1.5, [1, 2], "it's"))
        self.assertEqual(lib.tanks(data), dict(water=dict(fill=32000, max=32000, type=1), steam=dict(fill=0, max=8000, type="SUPERHOTSTEAM")))
        self.assertEqual(lib.data_value("1, 2, 3拥有以下方块数据：954L"), 954)
        self.assertEqual(lib.data_value("x has the following block data: -3.5d"), -3.5)
        self.assertEqual(lib.power_of(dict(id="hbmsntm:machine_battery", power=12)), 12)
        self.assertEqual(lib.power_of(dict(id="hbmsntm:machine_stirling", powerBuffer=3, power=99)), 3)
        with self.assertRaises(KeyError):
            lib.power_of(dict(id="hbmsntm:launch_pad", power=1))

    def test_readings_use_server_data(self):
        lib = importlib.import_module("_lib")
        sent = []

        class Ctx:
            def server(self, command):
                sent.append(command)
                return dict(messages=['1, 2, 3 has the following block data: {id: "hbmsntm:machine_industrial_turbine", power: 954L, '
                                      'water: 261, water_max: 7500, water_type: 4, steam: 0, steam_max: 30000, steam_type: 3}'])
        r = lib.reading(Ctx(), (1, 2, 3))
        self.assertEqual(sent, ["data get block 1 2 3"])
        self.assertEqual((r["power"], r["named"]["input"]["fill"], r["named"]["output"]["max"]), (954, 261, 30000))


def filtered_png(path, width, height, rgba, kinds):
    """An RGBA PNG whose rows use the given filter types, encoded the way a PNG writer does."""
    import struct
    import zlib
    stride = width * 4
    rows, prev = [], bytes(stride)
    for y in range(height):
        line = rgba[y * stride:(y + 1) * stride]
        kind = kinds[y % len(kinds)]
        out = bytearray(stride)
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if kind == 0:
                pred = 0
            elif kind == 1:
                pred = a
            elif kind == 2:
                pred = b
            elif kind == 3:
                pred = (a + b) >> 1
            else:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
            out[x] = (line[x] - pred) & 255
        rows.append(bytes([kind]) + bytes(out))
        prev = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


class BaselineTests(unittest.TestCase):
    W, H = 7, 5

    def setUp(self):
        self.baseline = importlib.import_module("baseline")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.saved = self.baseline.BASELINES
        self.baseline.BASELINES = self.root / "baselines"
        self.pixels = bytes((x * 37 + y * 11 + c * 5) & 255 for y in range(self.H) for x in range(self.W) for c in range(4))

    def tearDown(self):
        self.baseline.BASELINES = self.saved
        self.tmp.cleanup()

    def run_dir(self, name, shots, clients=("solo",)):
        run = self.root / name
        common.write_json(run / "results.json", dict(clients=list(clients), scenarios=[dict(id="feat.scene", feature="feat")]))
        for (client_name, rel), (pixels, kinds) in shots.items():
            filtered_png(run / client_name / "shots" / rel, self.W, self.H, pixels, kinds)
        return run

    def test_every_png_filter_decodes_to_the_same_pixels(self):
        for kinds in ([0], [1], [2], [3], [4], [4, 3, 2, 1, 0]):
            path = self.root / ("f%s.png" % "".join(map(str, kinds)))
            filtered_png(path, self.W, self.H, self.pixels, kinds)
            w, h, bpp, data = self.baseline.pixels(path)
            self.assertEqual((w, h, bpp, bytes(data)), (self.W, self.H, 4, self.pixels), kinds)
        rgb = bytes(range(self.W * self.H * 3))
        self.baseline.write_png(self.root / "rgb.png", self.W, self.H, rgb)
        self.assertEqual(bytes(self.baseline.pixels(self.root / "rgb.png")[3]), rgb)

    def test_save_then_compare_sorts_pictures_by_state(self):
        changed = bytearray(self.pixels)
        changed[0] ^= 0x80
        changed[4] ^= 0x80
        near = bytearray(self.pixels)
        near[4 * 8] = (near[4 * 8] + 2) & 255
        first = self.run_dir("first", {
            ("solo", "feat/scene/same.png"): (self.pixels, [0]),
            ("solo", "feat/scene/refiltered.png"): (self.pixels, [0]),
            ("solo", "feat/scene/near.png"): (self.pixels, [0]),
            ("solo", "feat/scene/changed.png"): (self.pixels, [0]),
            ("solo", "feat/scene/gone.png"): (self.pixels, [0]),
        })
        self.assertEqual(self.baseline.main(["save", str(first), "--name", "b"]), 0)
        manifest = common.read_json(self.baseline.BASELINES / "b" / "manifest.json")
        self.assertEqual(manifest["pictures"]["0/feat/scene/same.png"]["scenario"], "feat.scene")
        with self.assertRaises(SystemExit):
            self.baseline.main(["save", str(first), "--name", "b"])
        # a run whose client has another name still pairs with the baseline by client position
        second = self.run_dir("second", {
            ("other", "feat/scene/same.png"): (self.pixels, [0]),
            ("other", "feat/scene/refiltered.png"): (self.pixels, [4, 1]),
            ("other", "feat/scene/near.png"): (bytes(near), [0]),
            ("other", "feat/scene/changed.png"): (bytes(changed), [0]),
            ("other", "feat/scene/added.png"): (self.pixels, [0]),
        }, clients=("other",))
        self.assertEqual(self.baseline.main(["compare", str(second), "--baseline", "b", "--threshold", "1", "--max-pixels", "1"]), 1)
        report = common.read_json(second / "baseline-compare.json")
        states = {row["key"].rsplit("/", 1)[1]: row for row in report["pictures"]}
        self.assertEqual({k: v["state"] for k, v in states.items()}, {
            "same.png": "same", "refiltered.png": "same", "near.png": "near", "changed.png": "changed", "gone.png": "missing",
            "added.png": "new"})
        self.assertEqual((states["near.png"]["pixels"], states["near.png"]["largest"]), (1, 2))
        self.assertEqual((states["changed.png"]["pixels"], states["changed.png"]["box"]), (2, [0, 0, 1, 0]))
        self.assertTrue((second / "baseline-diff" / "0" / "feat" / "scene" / "changed.png").is_file())
        self.assertIn("changed.png", (second / "baseline-compare.md").read_text(encoding="utf-8"))
        # only "new" pictures: nothing changed or missing
        third = self.run_dir("third", {("solo", "feat/scene/%s.png" % n): (self.pixels, [0]) for n in
                                       ("same", "refiltered", "near", "changed", "gone", "extra")})
        self.assertEqual(self.baseline.main(["compare", str(third), "--baseline", "b"]), 0)
        self.assertEqual(self.baseline.main(["save", str(third), "--name", "b", "--replace"]), 0)
        self.assertEqual(len(list(self.baseline.BASELINES.glob("b.old-*"))), 1)


class ClientArgvTests(unittest.TestCase):
    def test_a_second_capture_file_leaves_the_default_alone(self):
        default = argparse.Namespace(argv=None)
        other = argparse.Namespace(argv="build/migration/accept/client-argv-second.json")
        self.assertEqual((client.argv_file(default), client.cmdline_file(default)), (client.ARGV, client.CMDLINE))
        self.assertEqual(client.argv_file(other).name, "client-argv-second.json")
        self.assertEqual(client.cmdline_file(other).name, "client-argv-second.txt")


class FakeData:
    def __init__(self, files, tags=None):
        self.files = files
        self._tags = tags or {}

    def under(self, folder):
        return closure.Data.under(self, folder)

    def tags(self):
        return self._tags


def shaped(result, key):
    return dict(type="minecraft:crafting_shaped", pattern=["A"], key=dict(A=key), result=dict(id=result, count=1))


class ClosureTests(unittest.TestCase):
    def test_ingredients_tags_and_meta(self):
        tags = {"c:ingots/x": ["hbmsntm:ingot_x", "#c:ingots/y"], "c:ingots/y": ["hbmsntm:ingot_y", "#c:ingots/x"]}
        self.assertEqual(closure.resolve_tag(tags, "c:ingots/x"), {"hbmsntm:ingot_x", "hbmsntm:ingot_y"})
        self.assertEqual(closure.ingredient(tags, {"tag": "c:none"}), {"#c:none"})
        self.assertEqual(closure.ingredient(tags, {"type": "neoforge:components", "items": "hbmsntm:part_generic",
                                                   "components": {"hbmsntm:meta": 2}}), {"hbmsntm:part_generic@2"})
        self.assertEqual(closure.result_item({"id": "hbmsntm:plate", "components": {"hbmsntm:meta": 0}}), "hbmsntm:plate@0")
        found = set()
        closure.machine_outputs([["hbmsntm:ingot_a", 2, 3], ["hbmsntm:ingot_b", 1, closure.WILDCARD], "hbmsntm:c"], found)
        self.assertEqual(found, {"hbmsntm:ingot_a@3", "hbmsntm:ingot_b", "hbmsntm:c"})
        entries = []
        closure.machine_entries([["item", "hbmsntm:a", 1, 4], ["tag", "c:ingots/x", 1], ["hbmsntm:b", 2]], entries)
        self.assertEqual(entries, [{"hbmsntm:a@4"}, {"#c:ingots/x"}, {"hbmsntm:b@0"}])
        entries = []
        closure.machine_entries([["item", "hbmsntm:a", 1], ["item", "hbmsntm:c", 1, closure.WILDCARD]], entries)
        self.assertEqual(entries, [{"hbmsntm:a@0"}, {"hbmsntm:c"}])
        self.assertEqual(closure.loot_items({"pools": [{"entries": [
            {"type": "minecraft:item", "name": "hbmsntm:part", "functions": [{"function": "minecraft:set_components",
                                                                             "components": {"hbmsntm:meta": 5}}]},
            {"type": "minecraft:item", "name": "hbmsntm:plain"}]}]}), {"hbmsntm:part@5", "hbmsntm:plain"})

    def test_an_exact_variant_0_input_is_not_met_by_another_variant(self):
        files = {"hbmsntm/loot_table/chests/box.json": ({"pools": [{"entries": [
                     {"type": "minecraft:item", "name": "hbmsntm:part",
                      "functions": [{"function": "minecraft:set_components", "components": {"hbmsntm:meta": 5}}]}]}]}, "l"),
                 "hbmsntm/recipe/stamp.json": (shaped("hbmsntm:stamp_iron_wire", {"item": "minecraft:iron_ingot"}), "r1")}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name)
        (export / "_hbmAssemblyMachine.json").write_text(json.dumps({"recipes": [
            {"name": "ass.v0", "input": [["item", "hbmsntm:part", 1]], "output": ["hbmsntm:needs_v0", 1]},
            {"name": "ass.any", "input": [["item", "hbmsntm:part", 1, closure.WILDCARD]], "output": ["hbmsntm:needs_any", 1]}]}),
            encoding="utf-8")
        (export / "_hbmPress.json").write_text(json.dumps({"recipes": [
            {"input": ["item", "minecraft:iron_ingot", 1, closure.WILDCARD], "stamp": "wire", "output": ["hbmsntm:wire_iron", 8]},
            {"input": ["item", "minecraft:iron_ingot", 1, closure.WILDCARD], "stamp": "circuit", "output": ["hbmsntm:circuit_iron"]}]}),
            encoding="utf-8")
        (export / "_hbmArcFurnace.json").write_text(json.dumps({"recipes": [
            {"input": ["item", "minecraft:flint", 1, closure.WILDCARD], "solid": ["hbmsntm:nugget_silicon", 4]}]}), encoding="utf-8")
        saved = closure.MACHINES
        closure.MACHINES = {"_hbmAssemblyMachine.json": None, "_hbmPress.json": None, "_hbmArcFurnace.json": None}
        try:
            report = closure.closure(["hbmsntm:needs_v0", "hbmsntm:needs_any", "hbmsntm:wire_iron", "hbmsntm:circuit_iron",
                                      "hbmsntm:nugget_silicon"], export, data=FakeData(files))
        finally:
            closure.MACHINES = saved
        by = {t["item"]: t["obtainable"] for t in report["targets"]}
        self.assertEqual(by, {"hbmsntm:needs_v0": False, "hbmsntm:needs_any": True, "hbmsntm:wire_iron": True,
                              "hbmsntm:circuit_iron": False, "hbmsntm:nugget_silicon": True})

    def test_closure_follows_worldgen_smelting_crafting_machines_and_the_anvil(self):
        files = {
            "hbmsntm/neoforge/biome_modifier/ores.json": ({"features": "hbmsntm:ore_x_placed"}, "m"),
            "hbmsntm/worldgen/placed_feature/ore_x_placed.json": ({"feature": "hbmsntm:ore_x"}, "p"),
            "hbmsntm/worldgen/configured_feature/ore_x.json": ({"config": {"targets": [{"state": {"Name": "hbmsntm:ore_x"}}]}}, "c"),
            "hbmsntm/loot_table/blocks/ore_x.json": ({"pools": [{"entries": [{"type": "minecraft:item", "name": "hbmsntm:raw_x"}]}]}, "l"),
            "hbmsntm/recipe/ingot_x.json": ({"type": "minecraft:smelting", "ingredient": {"item": "hbmsntm:raw_x"},
                                             "result": {"id": "hbmsntm:ingot_x"}}, "r1"),
            "hbmsntm/recipe/press.json": (shaped("hbmsntm:machine_press", {"item": "hbmsntm:ingot_x"}), "r2"),
            "hbmsntm/recipe/locked.json": (shaped("hbmsntm:locked", {"item": "hbmsntm:nowhere"}), "r3"),
        }
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name) / "hbmRecipes"
        export.mkdir()
        (export / "hbmPress.json").write_text(json.dumps({"recipes": [
            {"input": ["item", "hbmsntm:ingot_x", 1], "output": ["hbmsntm:plate", 1, 0]}]}), encoding="utf-8")
        anvil = Path(tmp.name) / "anvil.json"
        anvil.write_text(json.dumps({"construction": [{"inputs": [[{"id": "hbmsntm:plate", "meta": closure.WILDCARD, "count": 2}]],
                                                       "outputs": [{"id": "hbmsntm:shell", "meta": 1, "count": 1}], "tier_lower": 1}],
                                     "smithing": []}), encoding="utf-8")
        saved = closure.MACHINES
        closure.MACHINES = {"hbmPress.json": "hbmsntm:machine_press"}
        try:
            report = closure.closure(["hbmsntm:shell@1", "hbmsntm:plate", "hbmsntm:locked", "minecraft:stick"], export, anvil,
                                     data=FakeData(files))
        finally:
            closure.MACHINES = saved
        by = {t["item"]: t for t in report["targets"]}
        self.assertTrue(by["hbmsntm:shell@1"]["obtainable"])
        lines = closure.text_chain(by["hbmsntm:shell@1"]["chain"])
        self.assertIn("anvil construction", lines[0])
        self.assertTrue(any("machine hbmPress.json" in l and "hbmsntm:machine_press" in l for l in lines))
        self.assertTrue(any("world generation, block hbmsntm:ore_x" in l for l in lines))
        self.assertTrue(by["hbmsntm:plate"]["obtainable"])
        self.assertTrue(by["minecraft:stick"]["obtainable"])
        self.assertFalse(by["hbmsntm:locked"]["obtainable"])
        self.assertEqual(by["hbmsntm:locked"]["recipes_without_sources"][0]["missing"], [["hbmsntm:nowhere"]])
        self.assertEqual((report["machine_recipe_count"], report["anvil_recipe_count"]), (1, 1))

    def test_a_machine_recipe_needs_its_machine(self):
        files = {"hbmsntm/recipe/ingot.json": ({"type": "minecraft:smelting", "ingredient": {"item": "minecraft:iron_ore"},
                                                "result": {"id": "hbmsntm:ingot_y"}}, "r")}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name)
        (export / "hbmPress.json").write_text(json.dumps([{"input": ["item", "hbmsntm:ingot_y", 1], "output": "hbmsntm:plate_y"}]),
                                              encoding="utf-8")
        saved = closure.MACHINES
        closure.MACHINES = {"hbmPress.json": "hbmsntm:machine_press"}
        try:
            report = closure.closure(["hbmsntm:plate_y"], export, data=FakeData(files))
        finally:
            closure.MACHINES = saved
        self.assertFalse(report["targets"][0]["obtainable"])


    def test_crucible_melting_alloys_and_casts_need_the_crucible_and_the_mold(self):
        files = {
            "hbmsntm/recipe/crucible.json": (shaped("hbmsntm:machine_crucible", {"item": "minecraft:bricks"}), "r1"),
            "hbmsntm/recipe/mold.json": (shaped("hbmsntm:mold_ingot", {"item": "minecraft:copper_ingot"}), "r2"),
        }
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name) / "hbmRecipes"
        export.mkdir()
        (export / "_hbmCrucible.json").write_text(json.dumps({"recipes": [
            {"name": "crucible.alloy", "input": [["Iron", 64], ["Tin", 8]], "output": [["Alloy", 72]]}]}), encoding="utf-8")
        crucible = Path(tmp.name) / "crucible.json"
        crucible.write_text(json.dumps({
            "smelting": [{"item": {"id": "minecraft:iron_ingot", "meta": 0}, "materials": [["Iron", 72]]},
                         {"item": {"id": "hbmsntm:ingot_tin", "meta": 0}, "materials": [["Tin", 72]]}],
            "casts": [{"mold": "hbmsntm:mold_ingot", "material": "Alloy", "amount": 72, "output": {"id": "hbmsntm:ingot_alloy", "meta": 0}},
                      {"mold": "hbmsntm:mold_missing", "material": "Iron", "amount": 72, "output": {"id": "hbmsntm:plate_cast", "meta": 0}}]}),
            encoding="utf-8")
        report = closure.closure(["hbmsntm:ingot_alloy", "hbmsntm:plate_cast", "material:Iron"], export, crucible=crucible,
                                 data=FakeData(dict(files, **{"hbmsntm/recipe/tin.json": (shaped("hbmsntm:ingot_tin", {"item": "minecraft:iron_nugget"}), "r3")})))
        by = {t["item"]: t for t in report["targets"]}
        # Tin melts once the crucible exists; the alloy needs both materials; the cast needs its mold
        self.assertTrue(by["material:Iron"]["obtainable"])
        self.assertTrue(by["hbmsntm:ingot_alloy"]["obtainable"])
        lines = closure.text_chain(by["hbmsntm:ingot_alloy"]["chain"])
        self.assertIn("cast cast Alloy in hbmsntm:mold_ingot", lines[0])
        self.assertTrue(any("crucible alloy _hbmCrucible.json#crucible.alloy in hbmsntm:machine_crucible" in l for l in lines))
        self.assertFalse(by["hbmsntm:plate_cast"]["obtainable"])
        self.assertEqual(report["crucible_recipe_count"], 5)

    def test_config_gates_are_read_at_their_defaults_and_code_features_place_their_blocks(self):
        files = {
            "hbmsntm/neoforge/biome_modifier/gated.json": ({"type": "hbmsntm:config_gated_add_features", "biomes": "#minecraft:is_nether",
                                                             "config": ["netherOres", "enablePu"], "features": "hbmsntm:ore_pu_placed"}, "m1"),
            "hbmsntm/neoforge/biome_modifier/plain.json": ({"type": "neoforge:add_features", "biomes": "#minecraft:is_overworld",
                                                            "features": ["hbmsntm:ore_w_placed", "hbmsntm:ore_z_placed", "hbmsntm:oil_placed"]}, "m2"),
            "hbmsntm/worldgen/placed_feature/ore_pu_placed.json": ({"feature": "hbmsntm:ore_pu"}, "p1"),
            "hbmsntm/worldgen/placed_feature/ore_w_placed.json": ({"feature": "hbmsntm:ore_w", "placement": [
                {"type": "hbmsntm:config_count", "config": "wRate"}]}, "p2"),
            "hbmsntm/worldgen/placed_feature/ore_z_placed.json": ({"feature": "hbmsntm:ore_z", "placement": [
                {"type": "hbmsntm:config_count", "config": "zRate"}]}, "p3"),
            "hbmsntm/worldgen/placed_feature/oil_placed.json": ({"feature": "hbmsntm:oil"}, "p4"),
            "hbmsntm/worldgen/configured_feature/ore_pu.json": ({"config": {"targets": [{"state": {"Name": "hbmsntm:ore_pu"}}]}}, "c1"),
            "hbmsntm/worldgen/configured_feature/ore_w.json": ({"config": {"targets": [{"state": {"Name": "hbmsntm:ore_w"}}]}}, "c2"),
            "hbmsntm/worldgen/configured_feature/ore_z.json": ({"config": {"targets": [{"state": {"Name": "hbmsntm:ore_z"}}]}}, "c3"),
            "hbmsntm/worldgen/configured_feature/oil.json": ({"type": "hbmsntm:oil_bubble", "config": {}}, "c4"),
        }
        for block in ("ore_pu", "ore_w", "ore_z", "ore_oil"):
            files["hbmsntm/loot_table/blocks/%s.json" % block] = ({"pools": [{"entries": [
                {"type": "minecraft:item", "name": "hbmsntm:" + block}]}]}, "l")
        defaults = {"netherOres": True, "enablePu": False, "wRate": 4, "zRate": 0}
        report = closure.closure(["hbmsntm:ore_pu", "hbmsntm:ore_w", "hbmsntm:ore_z", "hbmsntm:ore_oil"], None,
                                 data=FakeData(files), defaults=defaults)
        by = {t["item"]: t for t in report["targets"]}
        self.assertFalse(by["hbmsntm:ore_pu"]["obtainable"])
        self.assertEqual(by["hbmsntm:ore_pu"]["worldgen_off_by_default"][0]["gates"], [["netherOres", True], ["enablePu", False]])
        self.assertTrue(by["hbmsntm:ore_w"]["obtainable"])
        self.assertFalse(by["hbmsntm:ore_z"]["obtainable"])  # a count of 0 places nothing
        self.assertTrue(by["hbmsntm:ore_oil"]["obtainable"])
        self.assertIn("OilBubbleFeature.java:131", closure.text_chain(by["hbmsntm:ore_oil"]["chain"])[0])
        self.assertEqual(report["worldgen_off_by_default"], ["hbmsntm:ore_pu", "hbmsntm:ore_z"])
        parsed = closure.config_defaults()
        self.assertIs(parsed["enablePlutoniumNetherOre"], False)  # CommonConfig.java: the nether plutonium ore is off
        self.assertEqual(parsed["netherCoalSpawnRate"], 8)

    def test_a_stack_without_meta_is_the_default_variant(self):
        files = {"hbmsntm/recipe/bolt.json": ({"type": "minecraft:crafting_shapeless", "ingredients": [{"item": "minecraft:iron_ingot"}],
                                               "result": {"id": "hbmsntm:bolt", "count": 4}}, "r1"),
                 "hbmsntm/loot_table/chests/box.json": ({"pools": [{"entries": [{"type": "minecraft:item", "name": "hbmsntm:wire_dense"}]}]}, "l")}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name)
        (export / "_hbmArcWelder.json").write_text(json.dumps({"recipes": [
            {"inputs": [["item", "hbmsntm:bolt", 2, 30], ["item", "hbmsntm:wire_dense", 1, 7900]], "output": ["hbmsntm:motor", 1]},
            {"inputs": [["item", "hbmsntm:bolt", 2, 0]], "output": ["hbmsntm:locked", 1]}]}), encoding="utf-8")
        saved = closure.MACHINES
        closure.MACHINES = {"_hbmArcWelder.json": None}
        try:
            report = closure.closure(["hbmsntm:bolt@30", "hbmsntm:motor", "hbmsntm:locked", "hbmsntm:wire_dense@7900"], export,
                                     data=FakeData(files), defaults={})
        finally:
            closure.MACHINES = saved
        by = {t["item"]: t["obtainable"] for t in report["targets"]}
        self.assertEqual(by, {"hbmsntm:bolt@30": True, "hbmsntm:motor": True, "hbmsntm:locked": False, "hbmsntm:wire_dense@7900": True})
        self.assertEqual(closure.variant("hbmsntm:bolt"), "hbmsntm:bolt@30")
        self.assertEqual(closure.variant("hbmsntm:plate"), "hbmsntm:plate@0")

    def test_fluid_inputs_need_a_producer_and_the_machine_must_be_obtainable(self):
        files = {"hbmsntm/recipe/mixer.json": (shaped("hbmsntm:machine_mixer", {"item": "minecraft:iron_ingot"}), "r1"),
                 "hbmsntm/recipe/drum.json": (shaped("hbmsntm:machine_waste_drum", {"item": "minecraft:iron_ingot"}), "r2"),
                 "hbmsntm/recipe/hot.json": (shaped("hbmsntm:waste_hot", {"item": "minecraft:iron_ingot"}), "r3"),
                 "hbmsntm/recipe/chem.json": (shaped("hbmsntm:machine_chemical_plant", {"item": "minecraft:iron_ingot"}), "r5"),
                 "hbmsntm/recipe/compressor.json": (shaped("hbmsntm:machine_compressor", {"item": "minecraft:iron_ingot"}), "r6"),
                 "hbmsntm/recipe/rotary.json": (shaped("hbmsntm:machine_rotary_furnace", {"item": "minecraft:iron_ingot"}), "r7")}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name) / "hbmRecipes"
        export.mkdir()
        (export / "_hbmMixer.json").write_text(json.dumps({"recipes": [{"outputType": "COOLANT", "recipes": [
            {"input1": ["WATER", 1800], "solidInput": ["item", "hbmsntm:niter"]}, {"input1": ["NOWHERE", 10]}]}]}), encoding="utf-8")
        (export / "_hbmChemicalPlant.json").write_text(json.dumps({"recipes": [
            {"name": "chem.a", "inputFluid": [["COOLANT", 100]], "outputItem": [["single", ["hbmsntm:cooled", 1]]]},
            {"name": "chem.b", "inputFluid": [["PETROLEUM", 100, 1]], "outputItem": [["single", ["hbmsntm:needs_pressure", 1]]]}]}),
            encoding="utf-8")
        (export / "_hbmCompressor.json").write_text(json.dumps({"recipes": [
            {"input": ["PETROLEUM", 2000], "output": ["PETROLEUM", 2000, 1]}]}), encoding="utf-8")
        (export / "_hbmFuelpool.json").write_text(json.dumps({"recipes": [
            {"input": ["hbmsntm:waste_hot", 1, 0], "output": ["hbmsntm:waste_cold", 1, 1]}]}), encoding="utf-8")
        (export / "_hbmRotaryFurnace.json").write_text(json.dumps({"recipes": [
            {"inputs": [["item", "minecraft:iron_ingot", 1, closure.WILDCARD]], "output": ["Steel", 72], "steam": 100}]}), encoding="utf-8")
        sources = Path(tmp.name) / "sources.json"
        sources.write_text(json.dumps({"sources": [
            {"name": "pump water", "products": ["fluid:WATER"], "inputs": [], "machine": "hbmsntm:machine_pump", "neo": "Pump.java:1"},
            {"name": "niter", "products": ["hbmsntm:niter"], "inputs": [], "machine": None, "neo": "X.java:1"}]}), encoding="utf-8")
        report = closure.closure(["hbmsntm:cooled", "fluid:COOLANT", "hbmsntm:needs_pressure", "hbmsntm:waste_cold@1", "material:Steel"],
                                 export, data=FakeData(dict(files, **{"hbmsntm/recipe/pump.json": (
                                     shaped("hbmsntm:machine_pump", {"item": "minecraft:iron_ingot"}), "r4")})), sources=sources, defaults={})
        by = {t["item"]: t["obtainable"] for t in report["targets"]}
        # COOLANT from water (a pump) and niter; PETROLEUM has no producer, so neither has its pressurised form; the rotary
        # furnace needs steam, which nothing makes here
        self.assertEqual(by, {"hbmsntm:cooled": True, "fluid:COOLANT": True, "hbmsntm:needs_pressure": False,
                              "hbmsntm:waste_cold@1": True, "material:Steel": False})
        self.assertEqual(report["process_source_count"], 2)
        self.assertEqual(report["tables_without_machine"], [])
        no_pump = closure.closure(["fluid:COOLANT"], export, data=FakeData(files), sources=sources, defaults={})
        self.assertFalse(no_pump["targets"][0]["obtainable"])

    def test_the_executor_machine_export(self):
        files = {"hbmsntm/recipe/gc.json": (shaped("hbmsntm:machine_gas_centrifuge", {"item": "minecraft:iron_ingot"}), "r1"),
                 "hbmsntm/recipe/co.json": (shaped("hbmsntm:furnace_combination", {"item": "minecraft:bricks"}), "r2"),
                 "hbmsntm/recipe/rod.json": (shaped("hbmsntm:rbmk_fuel_ueu", {"item": "minecraft:iron_ingot"}), "r3"),
                 "hbmsntm/recipe/channel.json": (shaped("hbmsntm:rbmk_rod", {"item": "minecraft:iron_ingot"}), "r4")}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        machines = Path(tmp.name) / "machines.json"
        machines.write_text(json.dumps({
            "gas_centrifuge": [{"fluid": "UF6", "amount": 1200, "outputs": [{"id": "hbmsntm:nugget_u235", "meta": 0, "count": 1}],
                                "high_speed": False, "centrifuges": 4},
                               {"fluid": "PUF6", "amount": 900, "outputs": [{"id": "hbmsntm:nugget_pu239", "meta": 0, "count": 1}],
                                "high_speed": True, "centrifuges": 1}],
            "combination": [{"inputs": [{"id": "minecraft:coal", "meta": 0, "count": 1}], "output": {"id": "hbmsntm:coke_coal", "meta": 0, "count": 1},
                             "fluid": ["COALCREOSOTE", 100]}],
            "rbmk_disassembly": [{"rod": "hbmsntm:rbmk_fuel_ueu", "pellet": "hbmsntm:rbmk_pellet_ueu", "count": 8}]}), encoding="utf-8")
        sources = Path(tmp.name) / "sources.json"
        sources.write_text(json.dumps({"sources": [{"name": "uf6", "products": ["fluid:UF6", "fluid:PUF6"], "inputs": [], "neo": "x"}]}),
                           encoding="utf-8")
        report = closure.closure(["hbmsntm:nugget_u235", "hbmsntm:nugget_pu239", "hbmsntm:coke_coal", "fluid:COALCREOSOTE",
                                  "hbmsntm:rbmk_pellet_ueu@0"], None, data=FakeData(files), machines=machines, sources=sources, defaults={})
        by = {t["item"]: t["obtainable"] for t in report["targets"]}
        self.assertEqual(by, {"hbmsntm:nugget_u235": True, "hbmsntm:nugget_pu239": False, "hbmsntm:coke_coal": True,
                              "fluid:COALCREOSOTE": True, "hbmsntm:rbmk_pellet_ueu@0": True})
        self.assertEqual(report["executor_machine_recipe_count"], 4)

    def test_pooled_recipes_need_a_blueprint_and_unknown_tables_are_no_source(self):
        files = {"hbmsntm/loot_table/chests/blueprints.json": ({"pools": [{"entries": [
            {"type": "minecraft:item", "name": "hbmsntm:blueprint_folder", "functions": [{"function": "minecraft:set_components",
                                                                                       "components": {"hbmsntm:meta": 0}}]}]}]}, "l")}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        export = Path(tmp.name)
        (export / "_hbmAssemblyMachine.json").write_text(json.dumps({"recipes": [
            {"name": "ass.alt", "input": [["item", "minecraft:iron_ingot", 1]], "output": ["hbmsntm:alt_chip", 1], "blueprintpool": "alt.chips"},
            {"name": "ass.secret", "input": [["item", "minecraft:iron_ingot", 1]], "output": ["hbmsntm:secret_chip", 1], "blueprintpool": "secret.x"},
            {"name": "ass.discover", "input": [["item", "minecraft:iron_ingot", 1]], "output": ["hbmsntm:discover_chip", 1], "blueprintpool": "discover.y"}]}),
            encoding="utf-8")
        (export / "_hbmNewMachine.json").write_text(json.dumps({"recipes": [
            {"name": "new.a", "input": [["item", "minecraft:iron_ingot", 1]], "output": ["hbmsntm:from_unknown", 1]}]}), encoding="utf-8")
        saved = closure.MACHINES
        closure.MACHINES = {"_hbmAssemblyMachine.json": None}
        try:
            report = closure.closure(["hbmsntm:alt_chip", "hbmsntm:secret_chip", "hbmsntm:discover_chip", "hbmsntm:from_unknown"], export,
                                     data=FakeData(files), defaults={})
        finally:
            closure.MACHINES = saved
        by = {t["item"]: t for t in report["targets"]}
        # the chest only gives alt folders (meta 0): an alt blueprint, no discover or secret one; the new table names no machine
        self.assertEqual({k: v["obtainable"] for k, v in by.items()}, {"hbmsntm:alt_chip": True, "hbmsntm:secret_chip": False,
                                                                      "hbmsntm:discover_chip": False, "hbmsntm:from_unknown": False})
        self.assertTrue(any("open blueprint folder 0" in l for l in closure.text_chain(by["hbmsntm:alt_chip"]["chain"])))
        self.assertEqual(report["pooled_recipe_count"], 3)
        self.assertEqual(len(report["tables_without_machine"]), 1)

    def test_universal_fluid_containers_follow_the_container_traits(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        fluids = Path(tmp.name) / "Fluids.java"
        fluids.write_text("WATER = new FluidType(\"WATER\", 0x3333FF).addTraits(LIQUID);\n"
                          "PLASMA = new FluidType(\"PLASMA\", 0xFF00FF).addTraits(NOCON);\n"
                          "SAS3 = new FluidType(\"SAS3\", 0x4FFFFF);\nSAS3.addTraits(LEADCON);\n", encoding="utf-8")
        flags = closure.fluid_container_flags(fluids)
        self.assertEqual(flags, {"PLASMA": "none", "SAS3": "lead"})
        recipes = closure.container_recipes({"NONE": 0, "WATER": 1, "PLASMA": 2, "SAS3": 3}, flags)
        filled = sorted(o for r in recipes if r["name"].startswith("fill") for o in r["outputs"])
        # no container for NONE or a NOCON fluid; a LEADCON fluid only goes into the lead tank
        self.assertEqual(filled, ["hbmsntm:fluid_barrel_full@1", "hbmsntm:fluid_tank_full@1", "hbmsntm:fluid_tank_lead_full@1",
                                  "hbmsntm:fluid_tank_lead_full@3"])
        emptied = [r for r in recipes if r["name"] == "empty fluid_tank_lead of SAS3"]
        self.assertEqual((emptied[0]["inputs"], emptied[0]["outputs"]), ([{"hbmsntm:fluid_tank_lead_full@3"}], {"fluid:SAS3"}))

    def test_mainline_stages_handoffs_and_attribution(self):
        def craft(out, inp):
            return shaped(out, {"item": inp}), "r-" + out
        files = {"hbmsntm/recipe/a.json": craft("hbmsntm:a", "minecraft:iron_ingot"),
                 "hbmsntm/recipe/b.json": craft("hbmsntm:b", "hbmsntm:a"),
                 "hbmsntm/recipe/c.json": craft("hbmsntm:c", "hbmsntm:b"),
                 "hbmsntm/recipe/late.json": craft("hbmsntm:late", "hbmsntm:c"),
                 "hbmsntm/recipe/gap.json": craft("hbmsntm:gap", "hbmsntm:nowhere"),
                 "hbmsntm/recipe/fuel.json": craft("hbmsntm:fuel", "hbmsntm:nowhere")}
        targets = ["hbmsntm:a", "hbmsntm:b", "hbmsntm:c", "hbmsntm:late", "hbmsntm:gap", "hbmsntm:fuel"]
        result = closure.closure(targets, None, data=FakeData(files), defaults={})
        stages = {"1": {"title": "one", "ids": ["hbmsntm:a", "hbmsntm:late", "hbmsntm:gap"]}, "2": {"title": "two", "ids": ["hbmsntm:c"]}}
        attribution = {"hbmsntm:fuel": {"category": "special-fuels", "note": "x"}}
        m = closure.mainline(result, stages, attribution)
        self.assertEqual(m["counts"], {"obtainable": 4, "gap": 1, "outside": 1})
        items = m["items"]
        # b is no checkpoint: it goes to the earliest stage its sources allow (after a, stage 1)
        self.assertEqual((items["hbmsntm:b"]["stage"], items["hbmsntm:b"]["staged"]), (1, "earliest its sources allow"))
        # late is a stage-1 checkpoint that needs c, a stage-2 checkpoint
        self.assertEqual(items["hbmsntm:late"]["needs_stage"], 2)
        self.assertEqual(items["hbmsntm:c"]["needs_stage"], 1)
        self.assertEqual(m["stage_start_items"]["2"], [{"item": "hbmsntm:a", "from_stage": 1}, {"item": "hbmsntm:b", "from_stage": 1}])
        self.assertEqual(items["hbmsntm:fuel"]["result"], "outside")
        self.assertEqual(items["hbmsntm:gap"]["result"], "gap")
        self.assertIn("**GAP**, missing hbmsntm:nowhere", closure.summary(dict(
            mainline=m, mainline_inputs={"items": "t"}, export=None, anvil_export=None, crucible_export=None, machines_export=None,
            sources=None, export_build="b")))
        self.assertEqual(m["attribution_warnings"], [])
        stale = closure.mainline(result, stages, {"hbmsntm:a": {"category": "special-fuels"}, "hbmsntm:gone": {"category": "bismuth"}})
        self.assertEqual(stale["attribution_warnings"], ["hbmsntm:gone is attributed but not in the item list",
                                                         "hbmsntm:a is attributed outside the mainline but obtainable"])
        with self.assertRaises(SystemExit):
            closure.mainline(result, stages, {"hbmsntm:gap": {"category": "something-new"}})


class StationTests(unittest.TestCase):
    def test_sign_and_reply_helpers(self):
        command = stations.sign_command(-1, 0, 2, ["BELT MOTION", "drop iron"])
        self.assertIn("minecraft:oak_sign[rotation=8]", command)
        self.assertIn("""'"S2"','"BELT MOTION"','"drop iron"',\'""\'""", command)
        ok = dict(status="ok", messages=[dict(text='-1, -60, 0 has the following block data: {messages: [\'"S2"\']}')])
        self.assertTrue(stations.reply_has(ok, '"S2"'))
        self.assertFalse(stations.reply_has(ok, '"S20"'))
        self.assertFalse(stations.reply_has(dict(status="fail", messages=ok["messages"]), '"S2"'))

    def test_sample_stations_are_station_scenarios(self):
        module = drive.load("conveyors/stations_sample")
        self.assertTrue(module.SCENARIO["station"])
        self.assertEqual(len(module.STATIONS), 3)
        self.assertEqual([e["id"] for e in drive.expectation_list(module)], [s["id"] for s in module.STATIONS])
        for s in module.STATIONS:
            self.assertLessEqual(len(s["short"]), 3)
            self.assertTrue(all(len(line) <= 15 for line in s["short"]))


if __name__ == "__main__":
    unittest.main()
