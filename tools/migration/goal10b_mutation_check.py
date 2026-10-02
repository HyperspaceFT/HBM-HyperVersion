"""Revert each Goal 10B production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
or only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy under build/migration/goal10b, and the
source tree's hashes are compared before and after the run.

Not listed: flipping rot in MachineArcWelderBlockEntity.getConPos. The welder's ten connections are mirror-symmetric
(rot -> -rot maps the set onto itself), so that change is behaviourally equivalent; section 6 checks the symmetry, and
the observable rot flips (the arc welder block's fillSpace and the soldering station's connections) are listed.
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
LOG = ROOT / "build/migration/goal10b/mutation_check.log"

ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
SOLDERING = "com/hbm/inventory/recipes/SolderingRecipes.java"
ARC_WELDER = "com/hbm/inventory/recipes/ArcWelderRecipes.java"
WELDER_BE = "com/hbm/blockentity/machine/MachineArcWelderBlockEntity.java"
WELDER_BLOCK = "com/hbm/blocks/machine/MachineArcWelderBlock.java"
STATION_BE = "com/hbm/blockentity/machine/MachineSolderingStationBlockEntity.java"
PROVIDER = "com/hbm/datagen/NtmRecipeProvider.java"

WELDER_PORTS = """        return new DirPos[] {
                new DirPos(x + dx, y, z + dz, dir),
                new DirPos(x + rx + dx, y, z + rz + dz, dir),
                new DirPos(x + rx * 2, y, z + rz * 2, rot),
                new DirPos(x - rx + dx, y, z - rz + dz, dir),
                new DirPos(x - rx * 2, y, z - rz * 2, rot.getOpposite()),
                new DirPos(x - dx * 2, y, z - dz * 2, dir.getOpposite()),
                new DirPos(x - dx * 2 + rx, y, z - dz * 2 + rz, dir.getOpposite()),
                new DirPos(x - dx + rx * 2, y, z - dz + rz * 2, rot),
                new DirPos(x - dx * 2 - rx, y, z - dz * 2 - rz, dir.getOpposite()),
                new DirPos(x - dx - rx * 2, y, z - dz - rz * 2, rot.getOpposite())
        };
"""
# The committed (pre-Goal 10B) two connections: core + dir and core + side, facing outward.
WELDER_PORTS_OLD = """        return new DirPos[] {
                new DirPos(x + dx, y, z + dz, dir),
                new DirPos(x + rx, y, z + rz, rot)
        };
"""
NEW_EXTRAS = """        // The other two bottom blocks also carry connections (MachineArcWelderBlockEntity.getConPos).
        this.makeExtra(level, core.relative(side.getOpposite()));
        this.makeExtra(level, core.relative(dir.getOpposite()).relative(side.getOpposite()));
"""
ELECTRODE_79 = """ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_DESH.get(), 1)
                .pattern(" A ")
                .pattern(" B ")
                .pattern(" A ")
                .define('A', NtmItems.INGOT_DESH.get())
                .define('B', NtmItems.INGOT_TUNGSTEN)"""
SOL_LIST = """        List<AStack> recipeList = new ArrayList<>();
        Collections.addAll(recipeList, ingredients);
"""


def stamp(flat, made):
    return f"addAnvilRecipe(NtmItems.STAMP_{flat}_FLAT.get(), 1, NtmItems.STAMP_{made}.get(), 1, 2);"


def stamp_pair(shape):
    """Swap one titanium/steel pair back to the committed cross-over (titanium flat -> steel stamp and vice versa)."""
    return [(stamp("TITANIUM", f"TITANIUM_{shape}"), stamp("TITANIUM", f"STEEL_{shape}")),
            (stamp("STEEL", f"STEEL_{shape}"), stamp("STEEL", f"TITANIUM_{shape}"))]


# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled or read by verify_goal10b.py.
MUTATIONS = [
    ("D1: the soldering station takes 1 tungsten bolt again", ANVIL,
     [("new ComparableStack(NtmItems.BOLT.get(), 4, BoltItem.Type.TUNGSTEN.meta)", "new ComparableStack(NtmItems.BOLT.get(), 1, BoltItem.Type.TUNGSTEN.meta)")]),
    ("D6: the plate stamp pair is crossed again", ANVIL, stamp_pair("PLATE")),
    ("D6: the wire stamp pair is crossed again", ANVIL, stamp_pair("WIRE")),
    ("D6: the circuit stamp pair is crossed again", ANVIL, stamp_pair("CIRCUIT")),
    ("D2 soldering: an unmatched non-empty slot is skipped instead of failing", SOLDERING,
     [("            if(!hasMatch) return false;\n", "            if(!hasMatch) continue;\n")]),
    ("D2 soldering: not every ingredient has to be used", SOLDERING,
     [("        return recipeList.isEmpty();\n", "        return true;\n")]),
    ("D2 soldering: an empty ingredient group accepts any slot contents", SOLDERING,
     [(SOL_LIST, "        if(ingredients.length == 0) return true;\n" + SOL_LIST)]),
    ("D2 soldering: a used ingredient is not removed (one slot could satisfy two)", SOLDERING,
     [("                    iterator.remove();\n", "")]),
    ("D2 arc welder: an unmatched non-empty slot is skipped instead of failing", ARC_WELDER,
     [("            if(!hasMatch) return false;\n", "            if(!hasMatch) continue;\n")]),
    ("D2 arc welder: not every ingredient has to be used", ARC_WELDER,
     [("        return recipeList.isEmpty();\n", "        return true;\n")]),
    ("D2 arc welder: a used ingredient is not removed", ARC_WELDER,
     [("                    iterator.remove();\n", "")]),
    ("D3: the arc welder's two committed connections instead of the ten", WELDER_BE, [(WELDER_PORTS, WELDER_PORTS_OLD)]),
    ("D3: the two new makeExtra calls are removed from MachineArcWelderBlock.fillSpace", WELDER_BLOCK, [(NEW_EXTRAS, "")]),
    ("D3: rot flipped in MachineArcWelderBlock.fillSpace (getCounterClockWise)", WELDER_BLOCK,
     [("Direction side = dir.getClockWise();", "Direction side = dir.getCounterClockWise();")]),
    ("Item routing: the core exposes every slot again", WELDER_BE,
     [("        return new int[] { 1, 3 };\n", "        return new int[] { 0, 1, 2, 3 };\n")]),
    ("Item routing: the red proxies reach the green slot", WELDER_BE,
     [("return new int[] { 0, 3 };", "return new int[] { 2, 3 };")]),
    ("Item routing: the upper blocks reach every slot", WELDER_BE,
     [("        return new int[] { };\n", "        return new int[] { 0, 1, 2, 3 };\n")]),
    ("rot flipped in the soldering station connections (getCounterClockWise)", STATION_BE,
     [("Direction rot = dir.getClockWise();", "Direction rot = dir.getCounterClockWise();")]),
    ("D4: the electrode outputs of recipes 78 and 79 are swapped back in the provider", PROVIDER,
     [("ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_SATURNITE.get(), 1)",
       "ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.ARC_ELECTRODE_DESH.get(), 1)"),
      (ELECTRODE_79, ELECTRODE_79.replace("ARC_ELECTRODE_DESH", "ARC_ELECTRODE_SATURNITE"))]),
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
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal10b as m;"
               "m.SOURCE=Path(sys.argv[2]);m.OUTPUT=Path(sys.argv[3]);m.main()",
               str(Path(__file__).parent), str(source), str(ROOT / "build/migration/goal10b/mutation-runs")]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    failures = [line.strip() for line in output.splitlines() if line.startswith("AssertionError in ")]
    other = next((line.strip() for line in output.splitlines() if line.startswith("Exception in ") or "error:" in line), "")
    stream.write(f"== {label} ==\nreturncode: {result.returncode}\n" + "\n".join(failures or [other]) + "\n")
    return result.returncode, failures, other


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE,
                        help="source root to mutate (default src/main/java); e.g. a copy with a proposed fix, for diagnostics")
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    before = tree_hash(args.source)
    detected, missed, broken = 0, [], []
    # The mutated copies live under build/migration/goal10b and are removed afterwards.
    (ROOT / "build/migration/goal10b").mkdir(parents=True, exist_ok=True)
    with args.log.open("w", encoding="utf-8") as stream, tempfile.TemporaryDirectory(dir=ROOT / "build/migration/goal10b") as temp:
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
            path.write_text(text, encoding="utf-8")
            code, failures, other = run(copy, label, stream)
            if failures:
                detected += 1
                print(f"detected: {label} -> {failures[0].removeprefix('AssertionError in ')[:220]}"
                      + (f" (+{len(failures) - 1} more sections)" if len(failures) > 1 else ""), flush=True)
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
    print(f"{detected}/{len(MUTATIONS)} reverted Goal 10B decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
