"""Revert each Goal 7B production change in a temporary source copy and confirm the regression detects it."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
LOG = ROOT / "build/migration/goal7b/mutation_check.log"

BARREL = "com/hbm/blockentity/machine/storage/BarrelBlockEntity.java"
OVEN = "com/hbm/blockentity/machine/MachineFurnaceCombinationBlockEntity.java"
BURNER = "com/hbm/blockentity/machine/MachineWoodBurnerBlockEntity.java"

OVEN_24 = """        DirPos[] positions = new DirPos[24];
        int i = 0;
        for(Direction dir : Direction.Plane.HORIZONTAL) {
            Direction rot = dir.getClockWise();
            for(int y = 0; y <= 1; y++) {
                for(int j = -1; j <= 1; j++) {
                    positions[i++] = new DirPos(pos.getX() + dir.getStepX() * 2 + rot.getStepX() * j, pos.getY() + y,
                            pos.getZ() + dir.getStepZ() * 2 + rot.getStepZ() * j, dir);
                }
            }
        }
        return positions;"""
OVEN_4 = """        return new DirPos[] {
                new DirPos(pos.getX() + 2, pos.getY(), pos.getZ(), Direction.EAST),
                new DirPos(pos.getX() - 2, pos.getY(), pos.getZ(), Direction.WEST),
                new DirPos(pos.getX(), pos.getY(), pos.getZ() + 2, Direction.SOUTH),
                new DirPos(pos.getX(), pos.getY(), pos.getZ() - 2, Direction.NORTH)
        };"""

MUTATIONS = [
    ("barrel container transfers mark saving", BARREL,
     "        if(loaded || unloaded) {\n            this.setChanged();\n        }\n", ""),
    ("barrel network drain marks saving", BARREL,
     "        if(amount > 0) this.setChanged();\n", ""),
    ("barrel buffer mode is LOW priority", BARREL,
     "this.mode == 1 ? ConnectionPriority.LOW : ConnectionPriority.NORMAL", "ConnectionPriority.NORMAL"),
    ("oven pipe drain marks saving", OVEN,
     "        if(amount > 0) this.setChanged();\n", ""),
    ("oven offers 24 connection points", OVEN, OVEN_24, OVEN_4),
    ("burner piped fill marks saving", BURNER,
     "        if(remainder < amount) this.setChanged();\n", ""),
    ("burner first fluid port faces backwards", BURNER,
     "new DirPos(base.getX(), base.getY(), base.getZ(), facing.getOpposite())",
     "new DirPos(base.getX(), base.getY(), base.getZ(), side.getOpposite())"),
    ("burner core accepts pipes only from the back", BURNER,
     "        return dir == facing.getOpposite();\n    }\n\n    @Override\n    public long transferFluid",
     "        return dir == facing.getOpposite() || dir == facing.getClockWise().getOpposite();\n    }\n\n    @Override\n    public long transferFluid"),
]


def run(source, label, stream):
    command = [sys.executable, "-B", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal7b as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(ROOT / "build/migration/goal7b/mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    failure = next((line.strip() for line in (result.stdout + result.stderr).splitlines() if "AssertionError" in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n{failure}\n")
    return result.returncode, failure


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    detected = 0
    with LOG.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory() as temp:
        code, _ = run(SOURCE, "baseline", stream)
        if code:
            raise SystemExit("baseline regression fails; see " + str(LOG))
        print("baseline: passed", flush=True)
        for label, name, old, new in MUTATIONS:
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
                print(f"NOT DETECTED: {label}", flush=True)
            else:
                detected += 1
                print(f"detected: {label} -> {failure.split(':', 1)[-1].strip()}", flush=True)
    print(f"{detected}/{len(MUTATIONS)} reverted changes detected; log {LOG}")
    if detected != len(MUTATIONS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
