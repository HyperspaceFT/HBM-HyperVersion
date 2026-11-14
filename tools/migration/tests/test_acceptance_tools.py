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


class ClientArgvTests(unittest.TestCase):
    def test_a_second_capture_file_leaves_the_default_alone(self):
        default = argparse.Namespace(argv=None)
        other = argparse.Namespace(argv="build/migration/accept-goal29/client-argv-g31e.json")
        self.assertEqual((client.argv_file(default), client.cmdline_file(default)), (client.ARGV, client.CMDLINE))
        self.assertEqual(client.argv_file(other).name, "client-argv-g31e.json")
        self.assertEqual(client.cmdline_file(other).name, "client-argv-g31e.txt")


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
        closure.MACHINES = {}
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
