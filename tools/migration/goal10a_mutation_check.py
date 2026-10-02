"""Revert each Goal 10A production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
or only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy under build/migration/goal10a, and the
source tree's hashes are compared before and after the run.
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
LOG = ROOT / "build/migration/goal10a/mutation_check.log"

CRUCIBLE = "com/hbm/blockentity/machine/MachineCrucibleBlockEntity.java"
MOLD = "com/hbm/blockentity/machine/FoundryMoldBlockEntity.java"
MELT = "com/hbm/inventory/recipes/CopperCastingRecipes.java"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
SUBTYPES = "com/hbm/handler/jei/subtypes/ScrapsSubtypeInterpreter.java"
SCRAPS = "com/hbm/items/CopperScrapsItem.java"
LOADER = "com/hbm/inventory/recipes/loader/SerializableRecipe.java"

SPOUTS = """    public Direction getRecipeDirection() {
        return this.getBlockState().getValue(DummyableBlock.FACING);
    }

    public Direction getWasteDirection() {
        return this.getBlockState().getValue(DummyableBlock.FACING).getOpposite();
    }
"""
SPOUTS_SWAPPED = """    public Direction getRecipeDirection() {
        return this.getBlockState().getValue(DummyableBlock.FACING).getOpposite();
    }

    public Direction getWasteDirection() {
        return this.getBlockState().getValue(DummyableBlock.FACING);
    }
"""
SYNC_READ = """            NTMMaterial material = Mats.matById.get(buf.readInt());
            int amount = buf.readInt();
            if(material != null && amount > 0) stacks.add(new Mats.MaterialStack(material, amount));
"""
SYNC_SKIP = """            NTMMaterial material = Mats.matById.get(buf.readInt());
            if(material == null) continue;
            int amount = buf.readInt();
            if(amount > 0) stacks.add(new Mats.MaterialStack(material, amount));
"""

# (label, file, old, new). Every mutation is in a class verify_goal10a.py compiles.
MUTATIONS = [
    ("smelt routing: every melted material goes to the waste stack", CRUCIBLE,
     "addToStack(recipeMaterial ? this.recipeStack : this.wasteStack, material);", "addToStack(this.wasteStack, material);"),
    ("input maximum: capacity / number of inputs instead of required * capacity / total input", CRUCIBLE,
     "int matMaximum = (int) ((long) recipeInputRequired * CAPACITY / recipe.getInputAmount());",
     "int matMaximum = CAPACITY / recipe.input.length;"),
    ("the recipe output can no longer be put back", CRUCIBLE,
     "if(recipe != null && recipe.hasOutput(material.material)) {", "if(false && recipe.hasOutput(material.material)) {"),
    ("alloying does not subtract the inputs", CRUCIBLE,
     "            stack.amount -= recipe.getInputAmount(stack.material);\n", ""),
    ("alloying every tick instead of every recipe.frequency ticks", CRUCIBLE,
     "if(this.level.getGameTime() % recipe.frequency > 0) return;", "if(this.level.getGameTime() % 1 > 0) return;"),
    ("front and rear spouts swapped", CRUCIBLE, SPOUTS, SPOUTS_SWAPPED),
    ("the recipe stack pours every material while a recipe is selected", CRUCIBLE,
     "if(recipe == null) return this.recipeStack;", "if(true) return this.recipeStack;"),
    ("recipe names are no longer validated", CRUCIBLE,
     "        if(!NO_RECIPE.equals(selection) && !CrucibleRecipes.INSTANCE.recipeNameMap.containsKey(selection)) return;\n", ""),
    ("the Goal 5A copper save is no longer migrated", CRUCIBLE,
     "if(!tag.contains(\"was\") && tag.contains(\"copper\", Tag.TAG_INT)) {", "if(false) {"),
    ("deserialize skips the amount of an unknown material ID", CRUCIBLE, SYNC_READ, SYNC_SKIP),
    ("the sync size bound no longer rejects more than 64 entries", CRUCIBLE,
     "if(size < 0 || size > MAX_SYNC_ENTRIES) throw", "if(size < 0) throw"),
    ("the mold accepts materials without a cast plate (cobalt)", MOLD,
     "                || CopperCastingRecipes.getPlateType(offered.material) == null || !this.hasMold()",
     "                || !this.hasMold()"),
    ("a cobalt fragment melts like an ingot (72 instead of 8)", MELT,
     "entries.add(new MeltEntry(NtmItems.FRAGMENT_COBALT.get(), Mats.MAT_COBALT, NUGGET_QUANTA));",
     "entries.add(new MeltEntry(NtmItems.FRAGMENT_COBALT.get(), Mats.MAT_COBALT, INGOT_QUANTA));"),
    ("pouring 32 instead of 24 quanta per tick", MELT,
     "public static final int POUR_QUANTA = MaterialShapes.NUGGET.q(3);", "public static final int POUR_QUANTA = MaterialShapes.NUGGET.q(4);"),
    ("the shredder's cobalt fragment recipe is removed", SHREDDER,
     "        setRecipe(new ItemStack(NtmItems.FRAGMENT_COBALT.get()), new ItemStack(NtmItems.POWDER_COBALT_TINY.get(), 1));\n", ""),
    ("the scraps subtype includes the amount", SUBTYPES,
     "return contents == null ? null : contents.material.id;", "return contents == null ? null : contents.material.id + \":\" + contents.amount;"),
    ("the scraps model order puts steel first", SCRAPS,
     "List.of(Mats.MAT_TUNGSTEN, Mats.MAT_COBALT, Mats.MAT_STEEL, Mats.MAT_DURA);",
     "List.of(Mats.MAT_STEEL, Mats.MAT_TUNGSTEN, Mats.MAT_COBALT, Mats.MAT_DURA);"),
    ("CrucibleRecipes is no longer registered as a recipe handler", LOADER,
     "        recipeHandlers.add(CrucibleRecipes.INSTANCE);\n", ""),
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
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal10a as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(ROOT / "build/migration/goal10a/mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failure = next((line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")), "")
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n{failure or other}\n")
    return result.returncode, failure, other


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="source root to mutate (default src/main/java); e.g. a copy with a proposed fix, for diagnostics")
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    before = tree_hash(args.source)
    detected, missed, broken = 0, [], []
    # The mutated copies live under build/migration/goal10a and are removed afterwards.
    (ROOT / "build/migration/goal10a").mkdir(parents=True, exist_ok=True)
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=ROOT / "build/migration/goal10a") as temp:
        stream.write(f"source: {args.source}\nsource tree sha256 before: {before}\n")
        code, failure, other = run(args.source, "baseline", stream)
        if code:
            raise SystemExit(f"baseline regression fails ({failure or other or 'nonzero exit'}); see {args.log}")
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
            code, failure, other = run(copy, label, stream)
            if failure:
                detected += 1
                print(f"detected: {label} -> {failure.removeprefix('AssertionError in ')}", flush=True)
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
    print(f"{detected}/{len(MUTATIONS)} reverted Goal 10A decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
