"""Revert each Goal 9A production decision in a temporary source copy and confirm the regression detects it.

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
LOG = ROOT / "build/migration/goal9a/mutation_check.log"

ABSTRACT = "com/hbm/blockentity/machine/boiler/AbstractBoilerBlockEntity.java"
HEAT = "com/hbm/blockentity/machine/boiler/MachineHeatBoilerBlockEntity.java"
INDUSTRIAL = "com/hbm/blockentity/machine/boiler/MachineIndustrialBoilerBlockEntity.java"
BARREL = "com/hbm/blockentity/machine/storage/BarrelBlockEntity.java"
REGISTRY = "com/hbm/inventory/FluidContainerRegistry.java"
LOADER = "com/hbm/inventory/fluid/tank/FluidLoaderStandard.java"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"

BARREL_RULES = """            case 2 -> {
                int content = FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType());
                yield content > 0 && content <= this.tank.getMaxFill();
            }
            case 4 -> {
                ItemStack full = FluidContainerRegistry.getFullContainer(stack, this.tank.getTankType());
                yield !full.isEmpty() && FluidContainerRegistry.getFluidContent(full, this.tank.getTankType()) <= this.tank.getMaxFill();
            }
"""
# The pre-Goal 9A NEO rules (HEAD c1ef60b4): empty containers in slot 2, full ones in slot 4, no capacity check.
OLD_BARREL_RULES = """            case 2 -> !FluidContainerRegistry.getFullContainer(stack, this.tank.getTankType()).isEmpty();
            case 4 -> FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType()) > 0;
"""

# (label, file, old, new). Every revert is in a class the regression compiles; the block and renderers are not.
MUTATIONS = [
    ("heat pull ratio DIFFUSION 0.1 -> 0.2", ABSTRACT,
     "protected static final double DIFFUSION = 0.1D;", "protected static final double DIFFUSION = 0.2D;"),
    ("heat boiler cap 3,200,000 -> 12,800,000 (the earlier shared cap)", HEAT,
     "public static final int MAX_HEAT = 3_200_000;", "public static final int MAX_HEAT = 12_800_000;"),
    ("industrial boiler cap 12,800,000 -> 3,200,000", INDUSTRIAL,
     "        return 12_800_000;\n", "        return 3_200_000;\n"),
    ("explosion threshold outputOps == 0 -> outputOps <= 1", ABSTRACT,
     "} else if(outputOps == 0 && this.canExplode()) {", "} else if(outputOps <= 1 && this.canExplode()) {"),
    ("exploded refund removed (always the normal drop)", HEAT,
     "if(!this.hasExploded) return null;", "if(true) return null;"),
    ("trySetInputType accepts any fluid", ABSTRACT,
     "        if(!type.hasTrait(FT_Heatable.class) || type.getTrait(FT_Heatable.class).getEfficiency(FT_Heatable.HeatingType.BOILER) <= 0) return false;\n", ""),
    ("barrel slot rules swapped back to the pre-Goal 9A NEO rules", BARREL, BARREL_RULES, OLD_BARREL_RULES),
    ("water bucket content 1000 -> 250", REGISTRY,
     "new ItemStack(Items.BUCKET), Fluids.WATER, 1000));", "new ItemStack(Items.BUCKET), Fluids.WATER, 250));"),
    ("water bottle content 250 -> 1000", REGISTRY,
     "new ItemStack(Items.GLASS_BOTTLE), Fluids.WATER, 250));", "new ItemStack(Items.GLASS_BOTTLE), Fluids.WATER, 1000));"),
    ("side port axis getClockWise() -> facing (the earlier NEO axis)", HEAT,
     "        return facing.getClockWise();\n", "        return facing;\n"),
    ("diff == 0 decays again (the earlier NEO edge)", ABSTRACT,
     "            if(diff == 0) return;\n", ""),
    ("matchesComponents disabled (META-only matching for the water bottle)", REGISTRY,
     "    private static boolean matchesComponents(ItemStack registered, ItemStack stack) {\n",
     "    private static boolean matchesComponents(ItemStack registered, ItemStack stack) {\n        if(true) return true;\n"),
    ("removeContainerIdentity not called (emptied bottle keeps PotionContents)", LOADER,
     "        FluidContainerRegistry.removeContainerIdentity(input, result);\n", ""),
    ("safeRem not set during the explosion", HEAT,
     "        DummyableBlock.safeRem = true;\n        try {\n", "        try {\n"),
    ("explode() clears the heat again (the earlier NEO behaviour)", ABSTRACT,
     "        this.hasExploded = true;\n        this.isOn = false;\n", "        this.hasExploded = true;\n        this.isOn = false;\n        this.heat = 0;\n"),
    ("explosion entity range mod 3 -> 2", HEAT, "withRangeMod(3F)", "withRangeMod(2F)"),
    ("explosion clears y+1..y+3 instead of y+2..y+3", HEAT,
     "for(int y = 2; y <= 3; y++)", "for(int y = 1; y <= 3; y++)"),
    ("boiler anvil recipe tier 2 -> 3", ANVIL,
     "new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))\n        ).setTier(2)",
     "new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))\n        ).setTier(3)"),
]


def run(source, label, stream):
    command = [sys.executable, "-B", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal9a as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(ROOT / "build/migration/goal9a/mutation-runs")]
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
    # The mutated copies live under build/migration/goal9a and are removed afterwards.
    (ROOT / "build/migration/goal9a").mkdir(parents=True, exist_ok=True)
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=ROOT / "build/migration/goal9a") as temp:
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
    print(f"{detected}/{len(MUTATIONS)} reverted Goal 9A decisions detected by a named assertion; log {args.log}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
