"""Goal19A: the lying stray cog (no stand-up correction) and the pumpjack connection points, with their mutation check.

Compiles the production StrayCog in the Goal 8 world and the production MachinePumpjackBlockEntity in the Goal 11A machine
world (goal19a_cog_pumpjack_regression/stubs.py), runs both fixtures, then reverts each Goal19A decision in a temporary copy
of src/main/java and requires that the copy still compiles and that a fixture assertion fails. No Gradle task is run.
Report: build/migration/goal19a/cog-pumpjack/<run>/report.json, with the provenance package_goal17b/18b.verify_report reads
(production and fixture hashes, source stability, the javac/java commands of the baseline and of every mutation).
"""

from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile

from goal13a_regression.anvil_block import stripped_sources
from goal19a_cog_pumpjack_regression.stubs import PUMPJACK_BE, cog_stubs, pumpjack_stubs
from verify_goal8 import PRODUCTION as GOAL8_PRODUCTION, jdk
from verify_goal11a import NEOFORGE_SOURCES, PRODUCTION as GOAL11A_PRODUCTION

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
TOOLS = Path(__file__).resolve().parent
FIXTURE = TOOLS / "goal19a_cog_pumpjack_regression"
OUTPUT = ROOT / "build/migration/goal19a/cog-pumpjack"

COG = "com/hbm/entity/projectile/StrayCog.java"
COG_FIXTURES = (
    TOOLS / "goal8_regression/com/hbm/entity/projectile/Goal8CogAccess.java",
    FIXTURE / "com/hbm/entity/projectile/Goal19ACogRegression.java",
)
PUMPJACK_PRODUCTION = tuple(dict.fromkeys(list(GOAL11A_PRODUCTION) + [PUMPJACK_BE]))
PUMPJACK_FIXTURES = (FIXTURE / "com/hbm/blockentity/machine/oil/Goal19APumpjackRegression.java",)

# (label, file, old, new, expected assertion): each reverts one Goal19A decision; every one must compile and fail an assertion.
MUTATIONS = [
    ("tick stand-up correction restored", COG,
     "        // No stand-up correction: once lying (orientation >= 6) a released cog keeps falling lying, as in the original.\n",
     "        if(!this.level.isClientSide) {\n            int orientation = this.getOrientation();\n"
     "            if(orientation >= 6 && !this.inGround) {\n                this.setOrientation(orientation - 6);\n            }\n        }\n",
     "still lying (orientation 9), no stand-up"),
    ("lying re-landing no longer moved onto the hit point", COG,
     "breaking blocks.\n            this.setPos(bhr.getLocation());\n", "breaking blocks.\n",
     "re-landing moves the cog onto the hit point of the new block"),
    ("lying cog sticks on a side or bottom face", COG,
     "            this.setDeltaMovement(Vec3.ZERO);\n            return;\n", "            this.setDeltaMovement(Vec3.ZERO);\n",
     "not stuck, no stuck block"),
    ("lying cog explodes on a fast landing", COG,
     "breaking blocks.\n            this.setPos(bhr.getLocation());\n",
     "breaking blocks.\n            this.setPos(bhr.getLocation());\n"
     "            if(this.getDeltaMovement().length() >= 0.75 && !this.level.isClientSide)"
     " ExplosionVNT.createExplosion(this.level, this, this.getX(), this.getY(), this.getZ(), 3F, false);\n",
     "lying re-landing neither explodes nor breaks a block"),
    ("pumpjack getConPos entries 2-4 reverted", PUMPJACK_BE,
     "                new DirPos(pos.getX() + rot.getStepX() * 2 - dir.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 2 - dir.getStepZ() * 2, dir.getOpposite()),\n"
     "                new DirPos(pos.getX() + rot.getStepX() * 4 + dir.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 4 + dir.getStepZ() * 2, dir),\n"
     "                new DirPos(pos.getX() + rot.getStepX() * 4 - dir.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 4 - dir.getStepZ() * 2, dir.getOpposite())\n",
     "                new DirPos(pos.getX() + rot.getStepX() * 2 + dir.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 4 - dir.getStepZ() * 2, dir.getOpposite()),\n"
     "                new DirPos(pos.getX() + rot.getStepX() * 4 - dir.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 4 + dir.getStepZ() * 2, dir),\n"
     "                new DirPos(pos.getX() + rot.getStepX() * 4 - dir.getStepX() * 2, pos.getY(), pos.getZ() + rot.getStepZ() * 2 - dir.getStepZ() * 2, dir.getOpposite())\n",
     "the original getPorts list in order"),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def production_hashes():
    names = dict.fromkeys(list(GOAL8_PRODUCTION) + list(PUMPJACK_PRODUCTION))
    return {name: sha(SOURCE / name) for name in names}


def fixture_hashes():
    """The regression Java files, this driver and every tools/migration module it imported (stub worlds, earlier drivers)."""
    files = [*COG_FIXTURES, *PUMPJACK_FIXTURES, Path(__file__)]
    for module in list(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if origin and Path(origin).resolve().is_relative_to(TOOLS) and Path(origin).suffix == ".py":
            files.append(Path(origin))
    return {relative(f): sha(f) for f in sorted(set(Path(f).resolve() for f in files))}


def record(args, result):
    """A command for the report; the output keeps its tail, which holds the AssertionError and the check counts."""
    output = (result.stdout + result.stderr).strip()
    return {"command": subprocess.list2cmdline(args), "returncode": result.returncode, "output": output[-6000:]}


def command(label, args, log, commands):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    commands.append(record(args, result))
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(args)}\nreturncode: {result.returncode}\n"
                     f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n")
    return result


def world(name, source, stubs, production, fixtures, main_class, root, log, java, javac, strip=False):
    """Compile one world and run its fixture. Returns a result dict with the compile and run outcome.

    `strip` compiles AnvilRecipes without its Goal 13A block, as verify_goal11a.py does; the Goal 8 world takes it live.
    """
    overlap = sorted(set(stubs) & set(production))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
    directory = root / name
    paths = []
    for stub, content in stubs.items():
        path = directory / "stubs" / stub
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(path)
    production_paths = [source / p for p in production]
    paths.extend(stripped_sources(production_paths, directory) if strip else production_paths)
    paths.extend(fixtures)
    listing = directory / "sources.txt"
    listing.write_text("".join(f'"{Path(p).as_posix()}"\n' for p in paths), encoding="utf-8")
    classes = directory / "classes"
    classes.mkdir()
    out = {"world": name, "commands": []}
    compiled = command(f"compile {name}", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                           "-d", str(classes), f"@{listing}"], log, out["commands"])
    out["compile_exit"] = compiled.returncode
    if compiled.returncode:
        out["compile_errors"] = [line.strip() for line in compiled.stderr.splitlines() if "error:" in line][:10]
        return out
    ran = command(f"run {name}", [str(java), "-Duser.language=en", "-ea", "-cp", str(classes), main_class], log, out["commands"])
    out["run_exit"] = ran.returncode
    out["stdout"] = ran.stdout.strip().splitlines()
    assertion = next((line.strip() for line in (ran.stdout + ran.stderr).splitlines() if "AssertionError" in line), "")
    if assertion:
        out["assertion"] = assertion
    elif ran.returncode:
        out["error"] = (ran.stderr.strip().splitlines() or ["nonzero exit"])[0]
    return out


def suite(source, root, log, java, javac, vanilla_tags):
    return [
        world("cog", source, cog_stubs(source), GOAL8_PRODUCTION, COG_FIXTURES,
              "com.hbm.entity.projectile.Goal19ACogRegression", root, log, java, javac),
        world("pumpjack", source, pumpjack_stubs(source, vanilla_tags), PUMPJACK_PRODUCTION, PUMPJACK_FIXTURES,
              "com.hbm.blockentity.machine.oil.Goal19APumpjackRegression", root, log, java, javac, strip=True),
    ]


def passed(results):
    return all(r["compile_exit"] == 0 and r.get("run_exit") == 0 for r in results)


def main():
    java, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal19A cog/pumpjack transcript: {log}", flush=True)
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")

    before = production_hashes()
    report = {"source": str(SOURCE), "source_sha256": before, "baseline": suite(SOURCE, run_dir / "baseline", log, java, javac, vanilla_tags),
              "mutations": []}
    report["commands"] = [c for r in report["baseline"] for c in r["commands"]]
    for r in report["baseline"]:
        print(f"baseline {r['world']}: compile {r['compile_exit']}, run {r.get('run_exit')}", flush=True)
        for line in r.get("stdout", []):
            print(f"  {line}", flush=True)
        for key in ("compile_errors", "assertion", "error"):
            if key in r:
                print(f"  {key}: {r[key]}", file=sys.stderr, flush=True)
    ok = passed(report["baseline"])

    if ok and "--no-mutations" not in sys.argv:
        with tempfile.TemporaryDirectory() as temp:
            for index, (label, name, old, new, expected) in enumerate(MUTATIONS):
                copy = Path(temp) / "java"
                if copy.exists():
                    shutil.rmtree(copy)
                shutil.copytree(SOURCE, copy)
                path = copy / name
                text = path.read_text(encoding="utf-8")
                if text.count(old) != 1:
                    raise SystemExit(f"mutation anchor not unique for: {label}")
                path.write_text(text.replace(old, new), encoding="utf-8")
                results = suite(copy, run_dir / f"mutation-{index}", log, java, javac, vanilla_tags)
                compiled = all(r["compile_exit"] == 0 for r in results)
                # Both worlds run for every mutation; the world whose java run failed is listed last (javac, java).
                failing = [r for r in results if r.get("run_exit") not in (None, 0)]
                ordered = [r for r in results if r not in failing] + failing
                commands = [c for r in ordered for c in r["commands"]]
                assertion = next((r["assertion"] for r in failing if "assertion" in r), "")
                detected = (compiled and bool(failing) and commands[-1]["returncode"] != 0
                            and "AssertionError" in commands[-1]["output"])
                report["mutations"].append({"label": label, "production_file": "src/main/java/" + name,
                                            "expected_assertion": expected, "expected_behavior_failure": True,
                                            "commands": commands, "compiled_successfully": compiled,
                                            "behavior_mutation_detected": detected, "assertion": assertion,
                                            "assertion_matches_expected": expected in assertion,
                                            "worlds": [r["world"] for r in ordered]})
                print(f"{'detected' if detected else 'NOT DETECTED'}: {label}"
                      + (f" -> {assertion.split(':', 1)[-1].strip()}" if assertion else "")
                      + ("" if compiled else " (mutant does not compile)"), flush=True)
                ok = ok and detected
        print(f"{sum(m['behavior_mutation_detected'] for m in report['mutations'])}/{len(MUTATIONS)} mutations compiled and detected", flush=True)

    def checks(world, prefix):
        r = next(r for r in report["baseline"] if r["world"] == world)
        return next((int(line.rsplit(":", 1)[1]) for line in r.get("stdout", []) if line.startswith(prefix)), 0)

    report["cog_pumpjack_counts"] = {
        "cog_checks": checks("cog", "Goal19A cog checks:"), "pumpjack_checks": checks("pumpjack", "Goal19A pumpjack checks:"),
        "scenarios": sum(1 for r in report["baseline"] for line in r.get("stdout", []) if line.endswith(" checks passed")),
        "mutations": len(report["mutations"])}
    report["mutations_detected"] = sum(m["behavior_mutation_detected"] for m in report["mutations"])
    report["fixture_sha256"] = fixture_hashes()
    report["source_stable_after_run"] = production_hashes() == before
    ok = ok and report["source_stable_after_run"]
    report["passed"] = ok
    (run_dir / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"report: {run_dir / 'report.json'}", flush=True)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
