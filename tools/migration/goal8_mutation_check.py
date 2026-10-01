"""Revert each Goal 8 production decision in a temporary source copy and confirm the regression detects it."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
LOG = ROOT / "build/migration/goal8/mutation_check.log"

ENGINE = "com/hbm/blockentity/machine/MachineStirlingBlockEntity.java"
COG = "com/hbm/entity/projectile/StrayCog.java"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"

# (label, file, old, new, reachable). A revert in a class the regression does not compile cannot be detected;
# it is still applied and reported, but does not fail this check.
MUTATIONS = [
    ("heat pull ratio 0.1 -> 0.25", ENGINE,
     "public static final double DIFFUSION = 0.1D;", "public static final double DIFFUSION = 0.25D;", True),
    ("overspeed limit 300 -> 600", ENGINE,
     "public static final int OVERSPEED_LIMIT = 300;", "public static final int OVERSPEED_LIMIT = 600;", True),
    ("gear meta check removed (META 1 gear accepted)", ENGINE,
     "        if(MetaHelper.getMeta(held) != 0) return false;\n", "", True),
    ("picked-up gear always gets a META component (meta 0 written)", COG,
     "if(this.getMeta() != 0) MetaHelper.setMeta(gear, this.getMeta());", "MetaHelper.setMeta(gear, this.getMeta());", True),
    ("'with gear' recycling uses the meta wildcard constructor", ANVIL,
     "new ComparableStack(NtmBlocks.MACHINE_STIRLING.asItem(), 1, 0)", "new ComparableStack(NtmBlocks.MACHINE_STIRLING.asItem(), 1)", True),
    ("drop meta ignores hasCog", ENGINE,
     "        return this.hasCog ? 0 : 1;\n", "        return 0;\n", True),
    ("east connection point moved from x+2 to x+1", ENGINE,
     "new DirPos(pos.getX() + 2, pos.getY(), pos.getZ(), Direction.EAST)", "new DirPos(pos.getX() + 1, pos.getY(), pos.getZ(), Direction.EAST)", True),
    ("gear installation no longer marks the engine for saving", ENGINE,
     "        held.shrink(1);\n        this.hasCog = true;\n        this.setChanged();\n",
     "        held.shrink(1);\n        this.hasCog = true;\n", True),
    ("overspeed warning threshold 60 -> 30", ENGINE,
     "if(this.overspeed > 60 && this.warnCooldown == 0)", "if(this.overspeed > 30 && this.warnCooldown == 0)", True),
]


def run(source, label, stream):
    command = [sys.executable, "-B", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal8 as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(ROOT / "build/migration/goal8/mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failure = next((line.strip() for line in output.splitlines() if "AssertionError" in line), "")
    if result.returncode and not failure:
        failure = next((line.strip() for line in output.splitlines() if "error:" in line), "nonzero exit")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n{failure}\n")
    return result.returncode, failure


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    detected = 0
    reachable = sum(1 for *_, expect in MUTATIONS if expect)
    missed = []
    with LOG.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory() as temp:
        code, _ = run(SOURCE, "baseline", stream)
        if code:
            raise SystemExit("baseline regression fails; see " + str(LOG))
        print("baseline: passed", flush=True)
        for label, name, old, new, expect in MUTATIONS:
            copy = Path(temp) / "java"
            if copy.exists():
                shutil.rmtree(copy)
            shutil.copytree(SOURCE, copy)
            path = copy / name
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"mutation anchor not unique for: {label}")
            path.write_text(text.replace(old, new), encoding="utf-8")
            code, failure = run(copy, label, stream)
            if code == 0:
                if expect:
                    missed.append(label)
                    print(f"NOT DETECTED: {label}", flush=True)
                else:
                    print(f"not detected (outside the regression, {name} is not compiled): {label}", flush=True)
                stream.write("detected: no\n")
            else:
                if expect:
                    detected += 1
                print(f"detected: {label} -> {failure.split(':', 1)[-1].strip()}", flush=True)
                stream.write("detected: yes\n")
    print(f"{detected}/{reachable} reverted changes in compiled classes detected; "
          f"{len(MUTATIONS) - reachable} revert(s) outside the compiled classes; log {LOG}")
    if missed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
