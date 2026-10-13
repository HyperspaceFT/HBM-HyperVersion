"""Revert or break each Goal 11A production decision in a temporary source copy and confirm the regression detects it.

A mutation counts as detected only when the regression reports an AssertionError; a mutation that does not compile
or only raises another exception is an error of this check, not a detection. The baseline (unmutated source) must pass
first. src/main/java is never edited: every mutation is applied to a fresh copy under build/migration/goal11a, and the
source tree's hashes are compared before and after the run. The datagen providers are mutated as text: the generated
JSON is not regenerated, so those mutations are caught by the provider-text checks of sections 3b, 6 and 8.
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
WORK = ROOT / "build/migration/goal11a"
LOG = WORK / "mutation_check.log"

DERRICK = "com/hbm/blockentity/machine/oil/MachineOilWellBlockEntity.java"
DRILL_BASE = "com/hbm/blockentity/machine/oil/OilDrillBaseBlockEntity.java"
FRACKING = "com/hbm/blockentity/machine/oil/MachineFrackingTowerBlockEntity.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
PLACED = "com/hbm/world/gen/NtmPlacedFeatures.java"
BUBBLE = "com/hbm/world/feature/OilBubbleFeature.java"
LOOT = "com/hbm/datagen/NtmBlockLootTableProvider.java"
LANGUAGE = "com/hbm/datagen/NtmLanguageProvider.java"
BURNER = "com/hbm/blockentity/machine/heater/HeaterOilburnerBlockEntity.java"
BURNER_BLOCK = "com/hbm/blocks/machine/heater/HeaterOilburnerBlock.java"
BLOCKS = "com/hbm/blocks/NtmBlocks.java"

AVOID_CALL = """        if(touchesAvoidedStructure(level, origin, radius)) {
            return false;
        }
"""
ORE_LOOT = "        this.add(NtmBlocks.ORE_OIL.get(), block -> this.oreDropNoSilk(block, NtmItems.OIL_TAR_CRUDE.get()));\n"
NO_SILK = """    private LootTable.Builder oreDropNoSilk(Block block, Item item) {
        return LootTable.lootTable()"""
POLLUTION_AMOUNT = "(float) Math.ceil(entry.getValue() * amount * 100F) / 100F"
# The review-fix mutations: where TileEntityHeaterOilburner clears shouldCool (inside the flammable branch, whatever toBurn is)
# and the end of pasteSettings.
KEEP_HEAT = """                }

                // As in the original, a burner that is on with a flammable type keeps its heat even while the tank is empty
                shouldCool = false;
"""
PASTE_END = """        if(tag.contains("isOn")) this.isOn = tag.getBoolean("isOn");
        this.setChanged();
"""
RECEIVE_TOGGLE = """        if(tag.contains("toggle")) {
            this.isOn = !this.isOn;
        }
"""

# (label, file, [(old, new), ...]). Every anchor must occur exactly once; every file is compiled or read by verify_goal11a.py.
MUTATIONS = [
    ("derrick +Z connection back to the corner (1,0,1)", DERRICK,
     [("new DirPos(pos.offset(0, 0, 1), Direction.SOUTH)", "new DirPos(pos.offset(1, 0, 1), Direction.SOUTH)")]),
    ("derrick -Z connection back to the corner (1,0,-1)", DERRICK,
     [("new DirPos(pos.offset(0, 0, -1), Direction.NORTH)", "new DirPos(pos.offset(1, 0, -1), Direction.NORTH)")]),
    ("derrick connection below the core removed", DERRICK,
     [("new DirPos(pos.offset(0, 0, -1), Direction.NORTH),\n                new DirPos(pos.offset(0, -1, 0), Direction.DOWN)\n",
       "new DirPos(pos.offset(0, 0, -1), Direction.NORTH)\n")]),
    ("titanium drill recipe 200 ticks instead of 100", ASSEMBLY,
     [('new GenericRecipe("ass.drill_titanium").setup(100, 100)', 'new GenericRecipe("ass.drill_titanium").setup(200, 100)')]),
    ("derrick recipe with 1 copper cast plate instead of 2", ASSEMBLY,
     [("castPlateIngredient(CastPlateItem.Type.COPPER, 2),", "castPlateIngredient(CastPlateItem.Type.COPPER, 1),")]),
    ("bubble placement back to absolute Y 0..24", PLACED,
     [("HeightRangePlacement.uniform(VerticalAnchor.aboveBottom(15), VerticalAnchor.aboveBottom(39))",
       "HeightRangePlacement.uniform(VerticalAnchor.absolute(0), VerticalAnchor.absolute(24))")]),
    ("bubble radius back to 10..16", BUBBLE,
     [("private static final int BUBBLE_MIN_RADIUS = 8;", "private static final int BUBBLE_MIN_RADIUS = 10;"),
      ("private static final int BUBBLE_RADIUS_VARIATION = 8;", "private static final int BUBBLE_RADIUS_VARIATION = 7;")]),
    ("bubble replaces only Blocks.STONE again", BUBBLE,
     [("if(level.getBlockState(pos).is(BlockTags.BASE_STONE_OVERWORLD)) {", "if(level.getBlockState(pos).is(Blocks.STONE)) {")]),
    ("trial chamber avoidance call removed", BUBBLE, [(AVOID_CALL, "")]),
    ("avoidance reads only the origin chunk", BUBBLE,
     [("int minChunkX = SectionPos.blockToSectionCoord(origin.getX() - radius);", "int minChunkX = SectionPos.blockToSectionCoord(origin.getX());"),
      ("int maxChunkX = SectionPos.blockToSectionCoord(origin.getX() + radius - 1);", "int maxChunkX = SectionPos.blockToSectionCoord(origin.getX());"),
      ("int minChunkZ = SectionPos.blockToSectionCoord(origin.getZ() - radius);", "int minChunkZ = SectionPos.blockToSectionCoord(origin.getZ());"),
      ("int maxChunkZ = SectionPos.blockToSectionCoord(origin.getZ() + radius - 1);", "int maxChunkZ = SectionPos.blockToSectionCoord(origin.getZ());")]),
    ("derrick drill depth back to absolute Y 6", DRILL_BASE,
     [("        return this.getMinBuildHeight() + 5;\n", "        return 6;\n")]),
    ("fracking tower drill depth back to absolute Y 0", FRACKING,
     [("        return this.getMinBuildHeight();\n", "        return 0;\n")]),
    ("ore_oil loot back to dropSelf", LOOT, [(ORE_LOOT, "        this.dropSelf(NtmBlocks.ORE_OIL.get());\n")]),
    ("ore_oil loot with a silk-touch dispatch", LOOT,
     [(NO_SILK, "    private LootTable.Builder oreDropNoSilk(Block block, Item item) {\n"
                "        return this.createSilkTouchDispatchTable(block, LootItem.lootTableItem(item));\n    }\n\n"
                "    private LootTable.Builder oreDropNoSilkUnused(Block block, Item item) {\n        return LootTable.lootTable()")]),
    ("burner top extra takes fluid instead of giving heat", BURNER_BLOCK,
     [("? new ProxyComboBlockEntity(pos, state).heatSource()", "? new ProxyComboBlockEntity(pos, state).fluid()")]),
    ("burner on by default", BURNER, [("public boolean isOn = false;", "public boolean isOn = true;")]),
    ("burner MAX_SETTING back to 100", BURNER, [("public static final int MAX_SETTING = 10;", "public static final int MAX_SETTING = 100;")]),
    ("hand drill accepted by the burner again", BURNER_BLOCK,
     [("if(tool != ToolType.SCREWDRIVER) {", "if(tool != ToolType.SCREWDRIVER && tool != ToolType.HAND_DRILL) {")]),
    ("receiveControl \"setting\" restored", BURNER,
     [(RECEIVE_TOGGLE, RECEIVE_TOGGLE + '        if(tag.contains("setting")) {\n'
                                        '            this.setting = Math.clamp(tag.getInt("setting"), 1, MAX_SETTING);\n        }\n')]),
    ("burner load without the setting clamp", BURNER,
     [('\n        this.setting = Math.clamp(tag.getInt("setting"), 1, MAX_SETTING);\n', '\n        this.setting = tag.getInt("setting");\n')]),
    ("burner pollution with the raw trait value", BURNER, [(POLLUTION_AMOUNT, "entry.getValue()")]),
    ("burner pollution not scaled by the amount burned (Goal 19A reverse)", BURNER,
     [(POLLUTION_AMOUNT, "(float) Math.ceil(entry.getValue() * 100F) / 100F")]),
    ("burner pollution scaled by the mB burned without the x5", BURNER, [("this.pollute(this.tank.getTankType(), toBurn * 5);", "this.pollute(this.tank.getTankType(), toBurn);")]),
    ("burner transferFluid without setChanged", BURNER, [("        if(remainder < amount) this.setChanged();\n", "")]),
    ("bubble shape back to the integer r^2 / 2 test (odd radii lose a shell)", BUBBLE,
     [("if(distSq * 2 < r2) {", "if(distSq < r2 / 2) {")]),
    ("ore_oil without requiresCorrectToolForDrops (drops by hand)", BLOCKS,
     [('register("ore_oil", () -> new Block(BlockBehaviour.Properties.of().strength(5.0F).explosionResistance(10.0F).requiresCorrectToolForDrops()',
       'register("ore_oil", () -> new Block(BlockBehaviour.Properties.of().strength(5.0F).explosionResistance(10.0F)')]),
    ("burner shouldCool = false back inside toBurn > 0 (an empty burner cools)", BURNER,
     [(KEEP_HEAT, "                    shouldCool = false;\n                }\n")]),
    ("pasteSettings without setChanged", BURNER, [(PASTE_END, '        if(tag.contains("isOn")) this.isOn = tag.getBoolean("isOn");\n')]),
    ("one fluid key reverted in the language provider (hbmfluid.oil -> hbmfluid.oil_crude)", LANGUAGE,
     [('this.add("hbmfluid.oil", "Crude Oil");', 'this.add("hbmfluid.oil_crude", "Crude Oil");')]),
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
               "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import verify_goal11a as m;"
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
    # The mutated copies live under build/migration/goal11a and are removed afterwards.
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
    print(f"{detected}/{len(MUTATIONS)} Goal 11A decisions detected by a named assertion; log {args.log}")
    if after != before:
        raise SystemExit(f"the source tree changed during the mutation check: {before} -> {after}")
    print(f"source tree unchanged: sha256 {after}")
    if missed or broken:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
