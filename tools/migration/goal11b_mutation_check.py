"""Revert or break each Goal 11B production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
or only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy under build/migration/goal11b, and the
source tree's hashes are compared before and after the run. The language provider is mutated as text: the generated
JSON is not regenerated, so that mutation is caught by the provider-text check of section 8t.
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
WORK = ROOT / "build/migration/goal11b"
LOG = WORK / "mutation_check.log"

RECIPES = "com/hbm/inventory/recipes/RefineryRecipes.java"
REFINERY = "com/hbm/blockentity/machine/oil/MachineRefineryBlockEntity.java"
REFINERY_BLOCK = "com/hbm/blocks/machine/MachineRefineryBlock.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
TANK = "com/hbm/blockentity/machine/storage/MachineFluidTankBlockEntity.java"
TANK_BLOCK = "com/hbm/blocks/machine/MachineFluidTankBlock.java"
LANGUAGE = "com/hbm/datagen/NtmLanguageProvider.java"

SOOT = """        // As in the original: running refineries release five seconds' worth of soot once a second
        if(this.level.getGameTime() % 20 == 0) {
            PollutionHandler.incrementPollution(this.level, this.worldPosition, PollutionType.SOOT, PollutionHandler.SOOT_PER_SECOND * 5);
        }
"""
SOOT_CALL = "PollutionType.SOOT, PollutionHandler.SOOT_PER_SECOND * 5);"
PLACE_THROUGH_FACE = """    public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) {
        return false;
    }"""
EMPTY_CHECK = """        boolean empty = !this.hasExploded;
        for(FluidTank tank : this.tanks) if(tank.getFill() > 0) empty = false;
        if(empty) return;
"""
GET_DROPS = """    // Original MachineRefinery: the dropped item keeps the tanks (IPersistentNBT.getDrops)
    @Override
    protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) {
        return IPersistentNBT.getDropsFromLootParams(state, params);
    }
"""
ASS_TANK = """        // Original ass.tank (normal mode only: the expensive mode uses item_expensive, which NEO does not have)
        this.register(new GenericRecipe("ass.tank").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_FLUID_TANK.get(), 1))
                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 4)));
"""
SPEEDS = """    @Override public long getReceiverSpeed(FluidType type, int pressure) { return this.hasExploded ? 0 : (mode == 0 || mode == 1) ? Math.max(500, (tank.getMaxFill() - tank.getFill()) / 100) : 0; }
    @Override public long getProviderSpeed(FluidType type, int pressure) { return this.hasExploded ? 0 : (mode == 1 || mode == 2) ? Math.max(500, tank.getFill() / 100) : 0; }"""
# The post-Goal 11A speed lines (build/migration/goal11b/base-g11a): always max(500, ...), whatever the mode or damage.
SPEEDS_BEFORE = """    @Override public long getReceiverSpeed(FluidType type, int pressure) { return Math.max(500, (tank.getMaxFill() - tank.getFill()) / 100); }
    @Override public long getProviderSpeed(FluidType type, int pressure) { return Math.max(500, tank.getFill() / 100); }"""
TYPE_CHANGE_DESTROY = """                        // A node of the previous fluid type must not stay behind in the old network (as the barrel)
                        if(this.node != null) {
                            this.destroyNode();
                        }
"""
CHUNK_UNLOAD = """    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();
        this.destroyNode();
    }
"""
SLOT_RULES_START = "    // Slot rules as the barrel (same layout: 0/1 identifier, 2/3 containers into the tank, 4/5 containers out of it).\n"
SLOT_RULES_END = """            default -> new int[] {4};
        };
    }
"""
NOTIFY = "this.level.updateNeighbourForOutputSignal(pos.makeCompat().relative(pos.getDir().getOpposite()), this.getBlockState().getBlock());"
GUI_GATE = """        // As in the original: a broken tank opens no menu and takes no identifier until it is repaired
        if(level.getBlockEntity(corePos) instanceof MachineFluidTankBlockEntity tank && tank.hasExploded) return InteractionResult.FAIL;
"""
ANALOG = """        if(state.getValue(TYPE) == DummyBlockType.DUMMY) return 0;
        BlockPos corePos = this.findCore(level, pos);
        if(corePos == null) return 0;
        return level.getBlockEntity(corePos) instanceof MachineFluidTankBlockEntity tank ? tank.getComparatorPower() : 0;"""


def slot_rules_removed(text):
    """Removes the tank's three slot-rule overrides (canPlaceItem, canTakeItemThroughFace, getSlotsForFace) with their comment."""
    start = text.find(SLOT_RULES_START)
    end = text.find(SLOT_RULES_END, start)
    if start < 0 or text.count(SLOT_RULES_START) != 1 or end < 0:
        raise SystemExit("mutation anchor not unique for: slot rules removed")
    return text[:start] + text[end + len(SLOT_RULES_END):]


# (label, file, [(old, new), ...] or a function). Every anchor must occur exactly once; every file is compiled or read by
# verify_goal11b.py.
MUTATIONS = [
    ("HOTCRACKOIL_DS recipe keyed HOTCRACKOIL again (overwrites the cracked oil row)", RECIPES,
     [("                Fluids.HOTCRACKOIL_DS,\n", "                Fluids.HOTCRACKOIL,\n")]),
    ("MAX_SULFUR back to 100", REFINERY, [("public static final int MAX_SULFUR = 10;", "public static final int MAX_SULFUR = 100;")]),
    ("refinery soot removed", REFINERY, [(SOOT, "")]),
    ("refinery soot with the raw SOOT_PER_SECOND (no x5)", REFINERY, [(SOOT_CALL, "PollutionType.SOOT, PollutionHandler.SOOT_PER_SECOND);")]),
    ("refinery soot on every run (no % 20 gate)", REFINERY,
     [("        if(this.level.getGameTime() % 20 == 0) {\n            PollutionHandler.incrementPollution(",
       "        if(true) {\n            PollutionHandler.incrementPollution(")]),
    ("getSlotsForFace back to all 13 slots", REFINERY,
     [("        return new int[] { 11 };", "        return new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };")]),
    ("canPlaceItemThroughFace true", REFINERY, [(PLACE_THROUGH_FACE, PLACE_THROUGH_FACE.replace("return false;", "return true;"))]),
    ("canTakeItemThroughFace back to 2/4/6/8/10/11", REFINERY,
     [("        return index == 11;", "        return index == 2 || index == 4 || index == 6 || index == 8 || index == 10 || index == 11;")]),
    ("writeNBT empty check removed (empty refineries drop tagged items)", REFINERY, [(EMPTY_CHECK, "")]),
    ("refinery getDrops override removed", REFINERY_BLOCK, [(GET_DROPS, "")]),
    ("ass.tank removed", ASSEMBLY, [(ASS_TANK, "")]),
    ("ass.tank with 1 steel shell", ASSEMBLY, [("new ComparableStack(NtmItems.SHELL_STEEL.get(), 4)));", "new ComparableStack(NtmItems.SHELL_STEEL.get(), 1)));")]),
    ("ass.tank 100 ticks instead of 200", ASSEMBLY, [('new GenericRecipe("ass.tank").setup(200, 100)', 'new GenericRecipe("ass.tank").setup(100, 100)')]),
    ("tank speeds ungated (post-Goal 11A lines)", TANK, [(SPEEDS, SPEEDS_BEFORE)]),
    ("tank getDemand without the exploded check", TANK, [("        if(this.hasExploded) return 0;\n        if(this.mode == 2 || this.mode == 3) return 0;",
                                                          "        if(this.mode == 2 || this.mode == 3) return 0;")]),
    ("tank node not destroyed on a type change", TANK, [(TYPE_CHANGE_DESTROY, "")]),
    ("tank onChunkUnloaded override removed", TANK, [(CHUNK_UNLOAD, "")]),
    ("tank transferFluid without setChanged", TANK, [("        if(toTransfer > 0) this.setChanged();\n", "")]),
    ("tank useUpFluid without setChanged", TANK, [("        if(amount > 0) this.setChanged();\n", "")]),
    ("tank loadTank without setChanged", TANK, [("if(tank.loadTank(level, 2, 3, slots)) this.setChanged();", "tank.loadTank(level, 2, 3, slots);")]),
    ("tank slot rules removed", TANK, slot_rules_removed),
    ("tank repair material back to 6 NOTHING", TANK,
     [("repair.add(new TagStack(NtmTags.Items.PLATES_STEEL, 6));",
       "repair.add(new com.hbm.inventory.RecipesCommon.ComparableStack(com.hbm.items.NtmItems.NOTHING.get(), 6));")]),
    ("tank comparator signal always 0", TANK_BLOCK, [(ANALOG, "        return 0;")]),
    ("tank comparator notification back to the connection points", TANK,
     [(NOTIFY, "this.level.updateNeighbourForOutputSignal(pos.makeCompat(), this.getBlockState().getBlock());")]),
    ("broken tank GUI/identifier gate removed", TANK_BLOCK, [(GUI_GATE, "")]),
    ("overlay.repair_with removed from the language provider", LANGUAGE, [('        this.add("overlay.repair_with", "Repair with:");\n', "")]),
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
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal11b as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(WORK / "mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failures = [line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")]
    # Another exception (a crash, not an assertion) is reported as such, never as a detection.
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
    # The worlds end a failed run with "Exception in thread "main" java.lang.AssertionError: N section(s) failed"; any
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
    # The mutated copies live under build/migration/goal11b and are removed afterwards.
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
            if callable(replacements):
                text = replacements(text)
            else:
                for old, new in replacements:
                    if text.count(old) != 1:
                        raise SystemExit(f"mutation anchor not unique for: {label}: {old[:80]}")
                    text = text.replace(old, new)
            path.write_text(text, encoding="utf-8")
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
    print(f"{detected}/{len(MUTATIONS)} Goal 11B decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
