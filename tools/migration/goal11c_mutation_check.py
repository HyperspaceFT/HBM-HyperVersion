"""Revert or break each Goal 11C production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
or only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java and src/main/resources are never edited: every Java mutation is applied to a fresh copy of the
source root under build/migration/goal11c, the one resource mutation (chem.desh in zh_cn.json) to a copy of zh_cn.json in
a temporary resource root that verify_goal11c.py reads instead, and the source tree's hashes (src/main/java and
zh_cn.json) are compared before and after the run.
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
RESOURCES = ROOT / "src/main/resources"
ZH = "assets/hbmsntm/lang/zh_cn.json"
WORK = ROOT / "build/migration/goal11c"
LOG = WORK / "mutation_check.log"

ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
CHEM_RECIPES = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
PLANT = "com/hbm/blockentity/machine/MachineChemicalPlantBlockEntity.java"
MODULE = "com/hbm/module/machine/ModuleMachineChemicalPlant.java"
MENU = "com/hbm/inventory/menus/MachineChemicalPlantMenu.java"

ASS_CHEMPLANT = """        // Original ass.chemplant (normal mode only: the expensive mode uses item_expensive, which NEO does not have).
        // NEO has no steel ingot or copper pipe tag, so the plain items stand in for the ore dictionary entries.
        this.register(new GenericRecipe("ass.chemplant").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_CHEMICAL_PLANT.get(), 1))
                .inputItems(new ComparableStack(NtmItems.INGOT_STEEL.get(), 8),
                        new ComparableStack(NtmItems.PIPE_COPPER.get(), 2),
                        new ComparableStack(NtmItems.PLATE_POLYMER.get(), 16),
                        new ComparableStack(NtmItems.MOTOR.get(), 2),
                        new ComparableStack(NtmItems.COIL_TUNGSTEN.get(), 2),
                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1)));
"""
SELECTION = """                // As the assembler: only a known recipe, and a pooled one only with its blueprint installed ("null" clears)
                if(!"null".equals(selection)) {
                    GenericRecipe recipe = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get(selection);
                    if(recipe == null || (recipe.isPooled() && !recipe.isPartOfPool(BlueprintsItem.grabPool(this.slots.get(1))))) return;
                }
"""
MODULE_UPDATE = """    @Override
    public void update(double speed, double power, boolean extraCondition, ItemStack blueprint) {
        // Original ModuleMachineBase.update: a pooled recipe is dropped as soon as its blueprint is missing
        GenericRecipe selected = this.getRecipe();
        if(selected != null && selected.isPooled() && !selected.isPartOfPool(BlueprintsItem.grabPool(blueprint))) {
            this.recipe = "null";
            this.progress = 0D;
            this.didProcess = false;
            this.markDirty = true;
            return;
        }
        super.update(speed, power, extraCondition, blueprint);
    }

"""
CONTAINERS = """            // As in the original, all three container slots load whatever recipe is selected
            this.inputTanks[0].loadTank(this.level, 10, 13, this.slots);
            this.inputTanks[1].loadTank(this.level, 11, 14, this.slots);
            this.inputTanks[2].loadTank(this.level, 12, 15, this.slots);
"""
# The post-Goal 11B lines (build/migration/goal11c/base-g11b): only with a selected recipe, only as many tanks as it has fluids.
CONTAINERS_BEFORE = """            if(recipe != null && recipe.inputFluid != null) {
                for(int i = 0; i < Math.min(3, recipe.inputFluid.length); i++) {
                    this.inputTanks[i].loadTank(this.level, 10 + i, 13 + i, this.slots);
                }
            }
"""
SHREDDER_CHUNK = """        // Original: the chunk that a normally mined rare earth ore drops
        registerIfAbsent(new ItemStack(NtmItems.RARE_EARTH_ORE_CHUNK.get()), new ItemStack(NtmItems.POWDER_DESH_MIX.get(), 1));
"""
QUICK_MOVE = "    public ItemStack quickMoveStack(Player player, int index) {"


def quick_move_to_super(text):
    """quickMoveStack back to the generic MenuBase routing (the post-Goal 11B body: return super.quickMoveStack)."""
    start = text.find(QUICK_MOVE)
    if start < 0 or text.count(QUICK_MOVE) != 1:
        raise SystemExit("mutation anchor not unique for: quickMoveStack back to super")
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            break
        i += 1
    return text[:start] + QUICK_MOVE + "\n        return super.quickMoveStack(player, index);\n    }" + text[i + 1:]


# (label, file, [(old, new), ...] or a function). Every anchor must occur exactly once; every Java file is compiled by
# verify_goal11c.py; a file under assets/ is a resource of the temporary resource root.
MUTATIONS = [
    ("ass.chemplant removed", ASSEMBLY, [(ASS_CHEMPLANT, "")]),
    ("ass.chemplant with 8 polymer plates instead of 16", ASSEMBLY,
     [("new ComparableStack(NtmItems.PLATE_POLYMER.get(), 16),", "new ComparableStack(NtmItems.PLATE_POLYMER.get(), 8),")]),
    ("ass.chemplant made pooled", ASSEMBLY,
     [('new GenericRecipe("ass.chemplant").setup(200, 100)', 'new GenericRecipe("ass.chemplant").setup(200, 100).setPools("alt..chemplant")')]),
    ("selection check removed (any name accepted)", PLANT, [(SELECTION, "")]),
    ("per-tick pool check removed (module update override)", MODULE, [(MODULE_UPDATE, "")]),
    ("chem.polymer back to 500 mB petroleum gas", CHEM_RECIPES, [("new FluidStack(Fluids.PETROLEUM, 1_000)", "new FluidStack(Fluids.PETROLEUM, 500)")]),
    ("chem.polymer back to 1 polymer ingot", CHEM_RECIPES,
     [("new ItemStack(NtmItems.INGOT_POLYMER.get(), 4)", "new ItemStack(NtmItems.INGOT_POLYMER.get(), 1)")]),
    ("rare earth ore chunk shredder entry removed", SHREDDER, [(SHREDDER_CHUNK, "")]),
    ("canTakeItemThroughFace back to 7-9", PLANT,
     [("return (index >= 7 && index <= 9) || this.chemicalModule.isSlotClogged(index);", "return index >= 7 && index <= 9;")]),
    ("quickMoveStack back to super (MenuBase routing)", MENU, quick_move_to_super),
    ("container slots conditional again (post-Goal 11B lines)", PLANT, [(CONTAINERS, CONTAINERS_BEFORE)]),
    ("chem.desh Chinese back to 戴斯合金生产", ZH, [('"chem.desh": "Desh生产",', '"chem.desh": "戴斯合金生产",')]),
]


def tree_hash(root, extra=()):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    for path in extra:
        digest.update(path.name.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run(source, resources, label, stream):
    command = [sys.executable, "-B", "-X", "utf8", "-c",
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal11c as m;"
               "m.SOURCE=Path(sys.argv[2]);m.RESOURCES=Path(sys.argv[3]);m.OUTPUT=Path(sys.argv[4]);m.main()",
               str(Path(__file__).parent), str(source), str(resources), str(WORK / "mutation-runs")]
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
    zh = RESOURCES / ZH
    before = tree_hash(args.source, [zh])
    detected, missed, broken = 0, [], []
    WORK.mkdir(parents=True, exist_ok=True)
    # The mutated copies live under build/migration/goal11c and are removed afterwards.
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=WORK) as temp:
        stream.write(f"source: {args.source}\nsource tree sha256 before (with zh_cn.json): {before}\n")
        resources = Path(temp) / "resources"
        (resources / ZH).parent.mkdir(parents=True)
        shutil.copyfile(zh, resources / ZH)
        code, failures, other = run(args.source, resources, "baseline", stream)
        if code or failures:
            raise SystemExit(f"baseline regression fails ({failures or other or 'nonzero exit'}); see {args.log}")
        print("baseline: passed", flush=True)
        for label, name, replacements in MUTATIONS:
            copy = Path(temp) / "java"
            if copy.exists():
                shutil.rmtree(copy)
            shutil.copytree(args.source, copy)
            shutil.copyfile(zh, resources / ZH)
            path = (resources if name.startswith("assets/") else copy) / name
            text = path.read_text(encoding="utf-8")
            if callable(replacements):
                text = replacements(text)
            else:
                for old, new in replacements:
                    if text.count(old) != 1:
                        raise SystemExit(f"mutation anchor not unique for: {label}: {old[:80]}")
                    text = text.replace(old, new)
            path.write_text(text, encoding="utf-8", newline="")
            code, failures, other = run(copy, resources, label, stream)
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
        after = tree_hash(args.source, [zh])
        stream.write(f"source tree sha256 after (with zh_cn.json): {after}\n")
    print(f"{detected}/{len(MUTATIONS)} Goal 11C decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
