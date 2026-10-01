"""Revert each Goal 9B production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
is an error of this check, not a detection. The baseline (unmutated source) must pass first.
"""

from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
LOG = ROOT / "build/migration/goal9b/mutation_check.log"

ENGINE = "com/hbm/blockentity/machine/MachineSteamEngineBlockEntity.java"
BASE = "com/hbm/blockentity/machine/CondenserBaseBlockEntity.java"
CONDENSER = "com/hbm/blockentity/machine/MachineCondenserBlockEntity.java"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"

PROBES = """            for(Direction dir : Direction.values()) this.trySubscribe(tanks[0].getTankType(), this.level, this.getBlockPos().relative(dir), dir);
            for(Direction dir : Direction.values()) this.tryProvide(tanks[1].getTankType(), this.level, this.getBlockPos().relative(dir), dir);
"""
# The pre-Goal 9B NEO base class (HEAD c1ef60b4) probed its own position on every side.
OWN_POSITION = """            for(Direction dir : Direction.values()) this.trySubscribe(tanks[0].getTankType(), this.level, this.getBlockPos(), dir);
            for(Direction dir : Direction.values()) this.tryProvide(tanks[1].getTankType(), this.level, this.getBlockPos(), dir);
"""
USE = """            FT_Coolable trait = this.tanks[0].getTankType().getTrait(FT_Coolable.class);
            double eff = trait.getEfficiency(CoolingType.TURBINE) * EFFICIENCY;

            int inputOps = this.tanks[0].getFill() / trait.amountReq;
            int outputOps = (this.tanks[1].getMaxFill() - this.tanks[1].getFill()) / trait.amountProduced;
            int ops = Math.min(inputOps, outputOps);
            this.tanks[0].setFill(this.tanks[0].getFill() - ops * trait.amountReq);
            this.tanks[1].setFill(this.tanks[1].getFill() + ops * trait.amountProduced);
            this.powerBuffer += (ops * trait.heatEnergy * eff);
"""
SYNC_BEFORE = "            this.tanks[0].serialize(this.buf);\n\n" + USE
SYNC_AFTER = USE + "            this.tanks[0].serialize(this.buf);\n"
ENGINE_GEAR = """                        new ComparableStack(NtmItems.GEAR_LARGE.get(), 1, 0)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STEAM_ENGINE.asItem()))"""

# (label, file, old, new). Every revert is in a class the regression compiles; the blocks and the renderer are not.
MUTATIONS = [
    ("engine efficiency 0.85 -> 0.8", ENGINE,
     "public static final double EFFICIENCY = 0.85D;", "public static final double EFFICIENCY = 0.8D;"),
    ("spent steam tank 20 -> 200 mB", ENGINE,
     "public static final int SPENT_STEAM_CAPACITY = 20;", "public static final int SPENT_STEAM_CAPACITY = 200;"),
    ("steam tank 2,000 -> 1,000 mB", ENGINE,
     "public static final int STEAM_CAPACITY = 2_000;", "public static final int STEAM_CAPACITY = 1_000;"),
    ("ops ignore the spent steam room (ops = inputOps)", ENGINE,
     "int ops = Math.min(inputOps, outputOps);", "int ops = inputOps;"),
    ("condenser base probes its own position again (both loops)", BASE, PROBES, OWN_POSITION),
    ("acceleration clamp 40 -> 20", ENGINE,
     "Mth.clamp(this.acceleration, 0F, 40F)", "Mth.clamp(this.acceleration, 0F, 20F)"),
    ("sound pitch acceleration / 80 -> / 40", ENGINE,
     "0.5F + (this.acceleration / 80F)", "0.5F + (this.acceleration / 40F)"),
    ("port side getClockWise() -> getCounterClockWise()", ENGINE,
     "        return facing.getClockWise();\n", "        return facing.getCounterClockWise();\n"),
    ("steam engine anvil gear (gear, 1, 0) -> (gear, 1) wildcard", ANVIL,
     ENGINE_GEAR, ENGINE_GEAR.replace("GEAR_LARGE.get(), 1, 0)", "GEAR_LARGE.get(), 1)")),
    ("sync writes the steam tank after this tick's use", ENGINE, SYNC_BEFORE, SYNC_AFTER),
    ("acceleration not saved", ENGINE, '        tag.putFloat("acceleration", this.acceleration);\n', ""),
    ("condenser setChanged on conversion removed", CONDENSER, "        if(convert > 0) this.setChanged();\n", ""),
    ("steam engine anvil tier 2 -> 3", ANVIL,
     "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STEAM_ENGINE.asItem()))\n        ).setTier(2)",
     "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STEAM_ENGINE.asItem()))\n        ).setTier(3)"),
    ("power also connects up and down", ENGINE,
     "return dir != null && dir.getAxis().isHorizontal();", "return dir != null;"),
    ("condenser waterTimer 20 -> 10", BASE, "if(convert > 0) this.waterTimer = 20;", "if(convert > 0) this.waterTimer = 10;"),
    ("operate sound at the block centre instead of the corner", ENGINE,
     "this.level.playSound(null, pos.getX(), pos.getY(), pos.getZ(),",
     "this.level.playSound(null, pos.getX() + 0.5D, pos.getY() + 0.5D, pos.getZ() + 0.5D,"),
    ("client interpolation over one step instead of three", ENGINE,
     "this.turnProgress = 3;", "this.turnProgress = 1;"),
    ("powerBuffer not reset at the start of the tick", ENGINE, "            this.powerBuffer = 0;\n", ""),
]


def run(source, label, stream):
    command = [sys.executable, "-B", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal9b as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(ROOT / "build/migration/goal9b/mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failure = next((line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")), "")
    compile_error = next((line.strip() for line in output.splitlines() if "error:" in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n{failure or compile_error}\n")
    return result.returncode, failure, compile_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="source root to mutate (default src/main/java); e.g. a copy with a proposed fix, for diagnostics")
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    detected, missed, broken = 0, [], []
    # The mutated copies live under build/migration/goal9b and are removed afterwards.
    (ROOT / "build/migration/goal9b").mkdir(parents=True, exist_ok=True)
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=ROOT / "build/migration/goal9b") as temp:
        stream.write(f"source: {args.source}\n")
        code, failure, compile_error = run(args.source, "baseline", stream)
        if code:
            raise SystemExit(f"baseline regression fails ({failure or compile_error or 'nonzero exit'}); see {args.log}")
        print("baseline: passed", flush=True)
        for label, name, old, new in MUTATIONS:
            copy = Path(temp) / "java"
            if copy.exists():
                shutil.rmtree(copy)
            shutil.copytree(args.source, copy)
            path = copy / name
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"mutation anchor not unique for: {label}")
            path.write_text(text.replace(old, new), encoding="utf-8")
            code, failure, compile_error = run(copy, label, stream)
            if failure:
                detected += 1
                print(f"detected: {label} -> {failure.removeprefix('AssertionError in ')}", flush=True)
                stream.write("detected: yes\n")
            elif code:
                broken.append(label)
                print(f"ERROR (no assertion; {compile_error or 'nonzero exit'}): {label}", flush=True)
                stream.write("detected: no (did not reach an assertion)\n")
            else:
                missed.append(label)
                print(f"NOT DETECTED: {label}", flush=True)
                stream.write("detected: no\n")
    print(f"{detected}/{len(MUTATIONS)} reverted Goal 9B decisions detected by a named assertion; log {args.log}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
