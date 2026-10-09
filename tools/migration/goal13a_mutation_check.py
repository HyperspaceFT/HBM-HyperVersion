"""Revert or break each Goal 13A production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile or
only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy of the source root under
build/migration/goal13a, and the source tree's hash is compared before and after the run.

The datagen providers are not compiled by the regression. A mutation in a provider (the chest loot weights, the meteorite rolls,
the any_concrete members) is detected through the provider text that verify_goal13a.py reads from the mutated copy (sections 4j, 5
and 8t), not through the generated JSON, which a source copy cannot change; NtmBlocks (the concrete strength) is detected the same way.
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
WORK = ROOT / "build/migration/goal13a"
LOG = WORK / "mutation_check.log"

BLUEPRINTS = "com/hbm/items/machine/BlueprintsItem.java"
FOLDER = "com/hbm/items/machine/BlueprintFolderItem.java"
CHEST = "com/hbm/world/feature/BlueprintChestFeature.java"
LOOT = "com/hbm/datagen/NtmChestLootTableProvider.java"
METEOR = "com/hbm/datagen/NtmBlockLootTableProvider.java"
TAGS = "com/hbm/datagen/NtmItemTagProvider.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
MODULE = "com/hbm/module/machine/ModuleMachineAssembler.java"
HEATER = "com/hbm/blockentity/machine/heater/HeaterElectricBlockEntity.java"
HEATEX = "com/hbm/blockentity/machine/heater/HeaterHeatexBlockEntity.java"
BLOCKS = "com/hbm/blocks/NtmBlocks.java"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
CHEM = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"

# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled or read by verify_goal13a.py.
MUTATIONS = [
    ("blueprint copy does not consume the paper", BLUEPRINTS, [("                slot.shrink(1);\n", "")]),
    ("secret blueprints can be copied", BLUEPRINTS,
     [("        if(poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) return InteractionResultHolder.pass(stack);\n", "")]),
    ("booklet draw not uniform (the last pool is unreachable)", FOLDER,
     [("pools.get(player.getRandom().nextInt(pools.size()))", "pools.get(player.getRandom().nextInt(Math.max(1, pools.size() - 1)))")]),
    ("booklet is used up when no pool exists", FOLDER,
     [("        if(pools.isEmpty()) return InteractionResultHolder.pass(stack);\n", "        if(pools.isEmpty()) { stack.shrink(1); return InteractionResultHolder.pass(stack); }\n")]),
    ("blueprint chest grid 5000 -> 4000", CHEST, [("private static final int GRID = 5000;", "private static final int GRID = 4000;")]),
    ("blueprint chest 50% draw removed", CHEST, [("        if(random.nextInt(20) < 10) return false;\n", "")]),
    ("blueprint chest height draw nextInt(2) -> nextInt(1)", CHEST, [("- random.nextInt(2);", "- random.nextInt(1);")]),
    ("blueprint chest loot weight 10 -> 9 (provider text)", LOOT,
     [(".add(blueprintFolder(BlueprintFolderItem.Type.ALT).setWeight(10))", ".add(blueprintFolder(BlueprintFolderItem.Type.ALT).setWeight(9))")]),
    ("meteorite treasure rolls 1-3 -> 1-2 (provider text)", METEOR, [(".setRolls(UniformGenerator.between(1, 3))", ".setRolls(UniformGenerator.between(1, 2))")]),
    ("alt..circuit block registered in 528 mode instead (!enable528 inverted)", ASSEMBLY, [("if(!NtmConfig.enable528()) {", "if(NtmConfig.enable528()) {")]),
    ("assembler no longer drops a pooled recipe without its blueprint", MODULE,
     [("selected.isPooled() && !selected.isPartOfPool(BlueprintsItem.grabPool(blueprint))", "selected.isPooled() && false")]),
    ("electric heater default setting back to 1", HEATER, [("public int setting = 0;", "public int setting = 1;")]),
    ("electric heater useUpHeat guard removed", HEATER, [("        if(heat <= 0) return;\n", "")]),
    ("electric heater hum volume 0.25 -> 0.5", HEATER, [("this, 0.25F, 7.5F, 1.0F, 20)", "this, 0.5F, 7.5F, 1.0F, 20)")]),
    ("heat exchanging heater starts with NONE again", HEATEX, [("new FluidTank(Fluids.COOLANT_HOT, 24_000),", "new FluidTank(Fluids.NONE, 24_000),")]),
    ("heat exchanging heater anvil copper 16 -> 8", ANVIL, [("new ComparableStack(Items.COPPER_INGOT, 16),", "new ComparableStack(Items.COPPER_INGOT, 8),")]),
    ("any_concrete member dropped (provider text)", TAGS, [("                NtmBlocks.DUCRETE.asItem(),\n                NtmBlocks.DUCRETE_SMOOTH.asItem()\n", "                NtmBlocks.DUCRETE.asItem()\n")]),
    ("concrete strength 15 -> 5 (NtmBlocks text)", BLOCKS,
     [('registerBlastInfoBlock("concrete",             () -> new Block(BlockBehaviour.Properties.of().strength(15.0F, 140.0F)',
       'registerBlastInfoBlock("concrete",             () -> new Block(BlockBehaviour.Properties.of().strength(5.0F, 140.0F)')]),
    ("shredder limestone block 4 -> 3 limestone powder", SHREDDER,
     [("new ItemStack(NtmBlocks.RESOURCE_LIMESTONE.get()), new ItemStack(NtmItems.POWDER_LIMESTONE.get(), 4)", "new ItemStack(NtmBlocks.RESOURCE_LIMESTONE.get()), new ItemStack(NtmItems.POWDER_LIMESTONE.get(), 3)")]),
    ("chem.concreteasbestos takes the sand block again", CHEM,
     [("new ComparableStack(NtmItems.INGOT_ASBESTOS.get(), 4), new TagStack(ItemTags.SAND, 8)", "new ComparableStack(NtmItems.INGOT_ASBESTOS.get(), 4), new ComparableStack(Blocks.SAND, 8)")]),
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
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal13a as m;"
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
    # The mutated copies live under build/migration/goal13a and are removed afterwards.
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
    print(f"{detected}/{len(MUTATIONS)} Goal 13A decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
