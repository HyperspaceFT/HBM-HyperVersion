"""Revert or break each Goal 13B production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile or
only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy of the source root under
build/migration/goal13b, and the source tree's hash is compared before and after the run.

The datagen providers, NtmItems and the registries are not compiled by the regression. A mutation in a provider (the burnt electrode
experience, the silicon billet recipe) is detected through the provider text that verify_goal13b.py reads from the mutated copy (sections 1t
and 2t), not through the generated JSON, which a source copy cannot change. NtmItems is read by the stand-in builder (goal13b_regression/stubs.py
takes each electrode's stack size, maximum and burnt item from its registration), so the electrode maximum reaches the compiled item test; the
other mutations are in compiled sources.
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
WORK = ROOT / "build/migration/goal13b"
LOG = WORK / "mutation_check.log"

BE = "com/hbm/blockentity/machine/MachineArcFurnaceBlockEntity.java"
ELECTRODE = "com/hbm/items/machine/ArcElectrodeItem.java"
ARC_RECIPES = "com/hbm/inventory/recipes/ArcFurnaceRecipes.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
PRESS = "com/hbm/inventory/recipes/PressRecipes.java"
ITEMS = "com/hbm/items/NtmItems.java"
RECIPE_PROVIDER = "com/hbm/datagen/NtmRecipeProvider.java"

CHIP_BLOCK = """            // Original ass.chip (AssemblyMachineRecipes.java:127-128); circuit SILICON is the printed silicon wafer.
            // ass.chipBismoid, ass.chipQuantum and ass.atomicClock (:129-134) are deferred with their inputs (GOAL13B B4).
            this.register(new GenericRecipe("ass.chip").setup(50, 250).outputItems(new ItemStack(NtmItems.CIRCUIT_MICROCHIP.get(), 1))
                    .inputItems(new ComparableStack(NtmItems.PLATE_POLYMER.get(), 1),
                            new ComparableStack(NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 1),
                            new ComparableStack(NtmItems.WIRE_GOLD.get(), 1)));

"""
CHIP_OUTSIDE = """        this.register(new GenericRecipe("ass.chip").setup(50, 250).outputItems(new ItemStack(NtmItems.CIRCUIT_MICROCHIP.get(), 1))
                .inputItems(new ComparableStack(NtmItems.PLATE_POLYMER.get(), 1),
                        new ComparableStack(NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 1),
                        new ComparableStack(NtmItems.WIRE_GOLD.get(), 1)));

"""
ARC_COMMENT = "        // Original ass.arcfurnace (AssemblyMachineRecipes.java:286-288), registered in every mode"

# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled or read by verify_goal13b.py.
MUTATIONS = [
    ("lid closing rate 1/60 -> 1/50", BE, [("this.lid -= 1F / (60F / (this.upgrade * 0.5 + 1));", "this.lid -= 1F / (50F / (this.upgrade * 0.5 + 1));")]),
    ("processing duration 400 -> 300", BE, [("int duration = 400 / (this.upgrade * 2 + 1);", "int duration = 300 / (this.upgrade * 2 + 1);")]),
    ("delay after a run 120 -> 100", BE, [("this.delay = (int) (120 / (this.upgrade * 0.5 + 1));", "this.delay = (int) (100 / (this.upgrade * 0.5 + 1));")]),
    ("consumption base 1,000 -> 500 HE/t", BE, [("return (long) (1_000 * Math.pow(5, this.upgrade));", "return (long) (500 * Math.pow(5, this.upgrade));")]),
    ("graphite electrode maximum 10 -> 20", ITEMS,
     [("new ArcElectrodeItem(new Item.Properties().stacksTo(1), 10, NtmItems.ARC_ELECTRODE_GRAPHITE_BURNT)", "new ArcElectrodeItem(new Item.Properties().stacksTo(1), 20, NtmItems.ARC_ELECTRODE_GRAPHITE_BURNT)")]),
    ("electrode worn out at durability > maximum instead of >=", ELECTRODE, [("return durability >= getMaxDurability(stack);", "return durability > getMaxDurability(stack);")]),
    ("only the first electrode is replaced by its burnt item", BE,
     [("if(electrode.getItem() instanceof ArcElectrodeItem item && ArcElectrodeItem.damage(electrode)) {", "if(electrode.getItem() instanceof ArcElectrodeItem item && ArcElectrodeItem.damage(electrode) && i == 0) {")]),
    ("an extra proxy position flipped (rot 1 -> -1)", BE,
     [("new DirPos(core.relative(dir, 2).relative(rot, 1), dir),", "new DirPos(core.relative(dir, 2).relative(rot, -1), dir),")]),
    ("the queue cap ignores the output count", BE, [("this.slots.get(q).getMaxStackSize() / recipe.solidOutput.getCount();", "this.slots.get(q).getMaxStackSize() / 1;")]),
    ("the network sync range 150 -> 100", BE, [("this.networkPackNT(150);", "this.networkPackNT(100);")]),
    ("the lid loop volume 0.75 -> 0.5", BE, [("this.getVolume(0.75F), 15F, 1.0F, 5)", "this.getVolume(0.5F), 15F, 1.0F, 5)")]),
    ("sand default 1 -> 2 silicon nuggets", ARC_RECIPES,
     [("register(new TagStack(ItemTags.SAND),                               new ItemStack(NtmItems.NUGGET_SILICON.get()));",
       "register(new TagStack(ItemTags.SAND),                               new ItemStack(NtmItems.NUGGET_SILICON.get(), 2));")]),
    ("de-duplication removed from register", ARC_RECIPES, [("            if(occupiedSolid.contains(key(stack))) return;\n", "")]),
    ("ass.chip registered outside the !enable528 block", ASSEMBLY, [(CHIP_BLOCK, ""), (ARC_COMMENT, CHIP_OUTSIDE + ARC_COMMENT)]),
    ("ass.arcfurnace any_concrete 12 -> 10", ASSEMBLY,
     [('new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete")), 12),', 'new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete")), 10),')]),
    ("silicon billet press entry removed", PRESS,
     [("        makeRecipe(StampType.CIRCUIT, new ComparableStack(NtmItems.BILLET_SILICON.get()),        new ItemStack(NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 1));\n", "")]),
    ("burnt electrode smelting experience 3.0 -> 1.0 (provider text)", RECIPE_PROVIDER,
     [("SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, output, 3.0F, 200)", "SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, output, 1.0F, 200)")]),
    ("silicon billet recipe built from the uranium nugget (provider text)", RECIPE_PROVIDER,
     [("addBilletRecipe(recipeOutput, NtmItems.BILLET_SILICON.get(), NtmItems.NUGGET_SILICON.get(), NtmItems.INGOT_SILICON.get());",
       "addBilletRecipe(recipeOutput, NtmItems.BILLET_SILICON.get(), NtmItems.NUGGET_URANIUM.get(), NtmItems.INGOT_SILICON.get());")]),
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
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal13b as m;"
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
    # The mutated copies live under build/migration/goal13b and are removed afterwards.
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
    print(f"{detected}/{len(MUTATIONS)} Goal 13B decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
