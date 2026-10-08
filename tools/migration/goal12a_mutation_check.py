"""Revert or break each Goal 12A production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile or
only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy of the source root under
build/migration/goal12a, and the source tree's hash is compared before and after the run.
"""

from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
WORK = ROOT / "build/migration/goal12a"
LOG = WORK / "mutation_check.log"

BOILER = "com/hbm/blocks/machine/MachineIndustrialBoiler.java"
PUMP_BE = "com/hbm/blockentity/machine/MachinePumpElectricBlockEntity.java"
SOLDERING = "com/hbm/inventory/recipes/SolderingRecipes.java"

SCAN = """            for(int dx = -1; dx <= 1; dx++) {
                for(int dy = 0; dy <= 4; dy++) {
                    for(int dz = -1; dz <= 1; dz++) {"""
SCAN_BEFORE = """            for(int dx = -2; dx <= 2; dx++) {
                for(int dy = -1; dy <= 5; dy++) {
                    for(int dz = -2; dz <= 2; dz++) {"""
CON_POS = """        return new DirPos[] {
                new DirPos(pos.offset(0, 0, -2), Direction.NORTH),
                new DirPos(pos.offset(2, 0, 0), Direction.EAST),
                new DirPos(pos.offset(0, 0, 2), Direction.SOUTH),
                new DirPos(pos.offset(-2, 0, 0), Direction.WEST)
        };"""
# The same four ports turned with the block's facing (north-facing pumps keep the original layout).
CON_POS_ROTATED = """        Direction facing = this.getBlockState().getValue(com.hbm.blocks.DummyableBlock.FACING);
        Direction rot = facing.getClockWise();
        return new DirPos[] {
                new DirPos(pos.relative(facing, 2), facing),
                new DirPos(pos.relative(rot, 2), rot),
                new DirPos(pos.relative(facing.getOpposite(), 2), facing.getOpposite()),
                new DirPos(pos.relative(rot.getOpposite(), 2), rot.getOpposite())
        };"""
READ = "        new SolderingRecipe(output, duration, consumption, fluid, toppings, pcb, solder);\n    }\n\n    @Override\n    public void writeRecipe("

# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled by verify_goal12a.py.
MUTATIONS = [
    ("boiler fillSpace without the proxy above the core (core.above(4))", BOILER, [("        this.makeExtra(level, core.above(4));\n", "")]),
    ("boiler EXTRA back to .fluid().heatSource()", BOILER,
     [("case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid();", "case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid().heatSource();")]),
    ("boiler removal scan back to -2..2 x -1..5 x -2..2", BOILER, [(SCAN, SCAN_BEFORE)]),
    ("destroyBoiler falls back to pos when no core is found", BOILER, [("        if(center == null) {\n            return;\n        }", "        if(center == null) {\n            center = pos;\n        }")]),
    ("pump GROUND_HEIGHT 71", PUMP_BE, [("public static final int GROUND_HEIGHT = 70;", "public static final int GROUND_HEIGHT = 71;")]),
    ("pump first-layer full-solid test removed", PUMP_BE,
     [("                    if(y == -1 && !state.isRedstoneConductor(this.level, pos)) return false; // first layer has to be full solid\n", "")]),
    ("pump ground threshold > instead of >=", PUMP_BE, [("return validCount >= invalidCount;", "return validCount > invalidCount;")]),
    ("pump operation -500 HE / +5,000 mB", PUMP_BE,
     [("        this.power -= 1_000;\n", "        this.power -= 500;\n"),
      ("Math.min(this.water.getFill() + ELECTRIC_SPEED, this.water.getMaxFill())", "Math.min(this.water.getFill() + ELECTRIC_SPEED / 2, this.water.getMaxFill())")]),
    ("pump getConPos rotated by the facing", PUMP_BE, [(CON_POS, CON_POS_ROTATED)]),
    ("SolderingRecipes.readRecipe adds the recipe again", SOLDERING,
     [(READ, READ.replace("        new SolderingRecipe(", "        recipes.add(new SolderingRecipe(").replace("solder);\n    }", "solder));\n    }", 1))]),
]


def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run(source, label, stream):
    command = [sys.executable, "-B", "-X", "utf8", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal12a as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(WORK / "mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failures = [line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")]
    # Another exception (a crash, not an assertion) is reported as such, never as a detection.
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
    # The machine world ends a failed run with "Exception in thread "main" java.lang.AssertionError: N section(s) failed"; any
    # other exception next to a detection is a crash of another section and is reported with it.
    crash = next((line.strip() for line in output.splitlines()
                  if line.startswith("Exception in ") and "java.lang.AssertionError" not in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n" + "\n".join(failures or [other]) + "\n")
    if crash and failures:
        stream.write(f"also crashed: {crash}\n")
    stream.flush()
    return result.returncode, failures, (crash if failures else other)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="source root to mutate (default src/main/java); e.g. a copy with a proposed fix, for diagnostics")
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    before = tree_hash(args.source)
    detected, missed, broken = 0, [], []
    WORK.mkdir(parents=True, exist_ok=True)
    # The mutated copies live under build/migration/goal12a and are removed afterwards.
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=WORK) as temp:
        stream.write(f"source: {args.source}\nsource tree sha256 before: {before}\n")
        code, failures, other = run(args.source, "baseline", stream)
        if code or failures:
            raise SystemExit(f"baseline regression fails ({failures or other or 'nonzero exit'}); see {args.log}")
        print("baseline: passed", flush=True)
        for label, name, replacements in MUTATIONS:
            copy = Path(temp) / "java"
            if copy.exists():
                shutil.rmtree(copy)
            shutil.copytree(args.source, copy)
            path = copy / name
            text = path.read_text(encoding="utf-8")
            for old, new in replacements:
                if text.count(old) != 1:
                    raise SystemExit(f"mutation anchor not unique for: {label}: {old[:80]}")
                text = text.replace(old, new)
            path.write_text(text, encoding="utf-8", newline="")
            code, failures, other = run(copy, label, stream)
            if failures:
                detected += 1
                print(f"detected: {label} -> {failures[0].removeprefix('AssertionError in ')[:220]}"
                      + (f" (+{len(failures) - 1} more sections)" if len(failures) > 1 else "")
                      + (f" [also crashed: {other[:120]}]" if other else ""), flush=True)
                stream.write("detected: yes\n")
            elif code:
                broken.append(label)
                print(f"ERROR (no assertion; {other or 'nonzero exit'}): {label}", flush=True)
                stream.write("detected: no (did not reach an assertion)\n")
            else:
                missed.append(label)
                print(f"NOT DETECTED: {label}", flush=True)
                stream.write("detected: no\n")
        after = tree_hash(args.source)
        stream.write(f"source tree sha256 after: {after}\n")
    print(f"{detected}/{len(MUTATIONS)} Goal 12A decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
