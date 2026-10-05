"""Audit the Goal 10B source decisions, the generated electrode recipes and the bilingual names of the soldering chain.

Default mode runs after `build.ps1 -Offline runData` and also compares the generated output with the pre-Goal 10B
stamp (build/migration/goal10b/stamp-before-g10b.json). `--source-only` skips the generated-output comparison.
Expected values are read from the original at 608fec4 (read-only) where the decision restores original behaviour.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from goal10c_regression.anvil_block import without_goal10c
from goal11a_regression.anvil_block import without_goal11a

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
JAVA = ROOT / "src/main/java/com/hbm"
OUT = ROOT / "build/migration/goal10b"
# Copy of the stamp taken before any Goal 10B source change, i.e. after Goal 10A: 3843 generated files.
BEFORE_STAMP = OUT / "stamp-before-g10b.json"
BEFORE_COUNT = 3843
# The Goal 9B commit (HEAD when Goal 10B was delivered). Goal 10A did not touch the generated recipes or these production
# files, so this is their pre-Goal 10B text. Pinned, so a later commit of Goal 10A/10B does not move the baseline.
BASELINE_COMMIT = "ee8f8d06"
RECIPES = ("data/hbmsntm/recipe/78.json", "data/hbmsntm/recipe/79.json")
CHANGED_INPUTS = {f"src/main/java/com/hbm/{name}.java" for name in (
    "inventory/recipes/anvil/AnvilRecipes", "inventory/recipes/SolderingRecipes", "inventory/recipes/ArcWelderRecipes",
    "blockentity/machine/MachineArcWelderBlockEntity", "blocks/machine/MachineArcWelderBlock", "datagen/NtmRecipeProvider")}
# The chain's player-facing names: the two machines, their containers, the eight electrode items (NtmItems registers
# four electrodes and their burnt forms), the analog board, the template, the tier-I upgrades and the welded plates.
NAMES = ["block.hbmsntm.machine_soldering_station", "block.hbmsntm.machine_arc_welder", "container.machine_soldering_station",
         "container.machine_arc_welder", "item.hbmsntm.circuit_analog_board", "item.hbmsntm.upgrade_template"] + [
    f"item.hbmsntm.arc_electrode_{kind}{burnt}" for kind in ("graphite", "lanthanium", "desh", "saturnite") for burnt in ("", "_burnt")] + [
    f"item.hbmsntm.upgrade_{kind}_1" for kind in ("speed", "effect", "power", "fortune", "afterburn")] + [
    "item.hbmsntm.cast_plate_welded", "item.hbmsntm.cast_plate_welded.steel"]
CJK = re.compile(r"[一-鿿]")
checks = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def compact(source):
    return re.sub(r"\s+", " ", source)


def digests(path):
    data = path.read_bytes()
    return {hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()}


def git_show(spec):
    return subprocess.run(["git", "-C", str(ROOT), "show", spec], capture_output=True, check=True).stdout


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def between(source, start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


def method(source, signature):
    """One method's text, from its signature to the matching closing brace."""
    start = source.index(signature)
    depth, i = 0, source.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(source[i], 0)
        if depth == 0:
            return source[start:i + 1]
        i += 1


def anvil():
    source = text(JAVA / "inventory/recipes/anvil/AnvilRecipes.java")
    original = compact(text(ORIGINAL / "inventory/recipes/anvil/AnvilRecipes.java"))
    # D1. Original AnvilRecipes.java:383-389.
    check("new OreDictStack(STEEL.plateCast(), 2), new ComparableStack(ModItems.coil_copper, 4), new OreDictStack(W.bolt(), 4), "
          "new ComparableStack(ModItems.circuit, 2, EnumCircuitType.VACUUM_TUBE.ordinal()) }, "
          "new AnvilOutput(new ItemStack(ModBlocks.machine_soldering_station))).setTier(2)" in original,
          "original: the soldering station takes 2 steel cast plates, 4 copper coils, 4 tungsten bolts and 2 vacuum tubes at tier 2")
    station = compact(between(source, "new ComparableStack(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 2),", ".setTier(2).setOverlay(OverlayType.CONSTRUCTION));"))
    check(station == "new ComparableStack(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 2), new ComparableStack(NtmItems.COIL_COPPER.get(), 4), "
          "NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 2), new ComparableStack(NtmItems.BOLT.get(), 4, BoltItem.Type.TUNGSTEN.meta) }, "
          "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_SOLDERING_STATION.asItem())) )",
          f"D1: NEO's soldering station entry: 2 tubes, 4 coils, 2 steel cast plates, 4 tungsten bolts (got {station})")
    check(source.count("BoltItem.Type.TUNGSTEN.meta") == 1, "the tungsten bolt appears once in AnvilRecipes")
    # D6. Original AnvilRecipes.java:592-598.
    for shape in ("plate", "wire", "circuit"):
        for metal in ("steel", "titanium"):
            check(f"new ComparableStack(ModItems.stamp_{metal}_flat, 1),new AnvilOutput(new ItemStack(ModItems.stamp_{metal}_{shape}))).setTier(2)" in original,
                  f"original: the {metal} flat stamp makes the {metal} {shape} stamp at tier 2")
            own = f"addAnvilRecipe(NtmItems.STAMP_{metal.upper()}_FLAT.get(), 1, NtmItems.STAMP_{metal.upper()}_{shape.upper()}.get(), 1, 2);"
            other = "TITANIUM" if metal == "steel" else "STEEL"
            crossed = f"addAnvilRecipe(NtmItems.STAMP_{metal.upper()}_FLAT.get(), 1, NtmItems.STAMP_{other}_{shape.upper()}.get(), 1, 2);"
            check(source.count(own) == 1 and crossed not in source, f"D6: NEO: {own}")
    head = git_show(f"{BASELINE_COMMIT}:src/main/java/com/hbm/inventory/recipes/anvil/AnvilRecipes.java").decode("utf-8").replace("\r\n", "\n")
    # Goal 11A (migration/GOAL11A.md) appends the fluid burner block after the Goal 10C block; it must occur exactly once,
    # directly after the heating oven recycling entry and at the end of registerConstruction. It is removed first.
    source, goal11a_found = without_goal11a(source)
    check(goal11a_found, "the Goal 11A fluid burner block follows the Goal 10C block exactly once, at the end of registerConstruction")
    # Goal 10C (migration/GOAL10C.md) appends the heating oven block after the steam engine; it must occur exactly once
    # there, and is removed before the unchanged line comparison.
    source, goal10c_found = without_goal10c(source)
    check(goal10c_found, "the Goal 10C heating oven block follows the steam engine exactly once, at the end of registerConstruction")
    lines = [(a, b) for a, b in zip(head.split("\n"), source.split("\n")) if a != b]
    check(len(head.split("\n")) == len(source.split("\n")) and len(lines) == 7,
          f"AnvilRecipes differs from {BASELINE_COMMIT} in exactly seven lines, at the same places ({len(lines)})")


MATCHER = """List<AStack> recipeList = new ArrayList<>(); Collections.addAll(recipeList, {ingredients}); for(ItemStack inputStack : {stacks}) {{ \
if(inputStack == null || inputStack.isEmpty()) continue; boolean hasMatch = false; Iterator<AStack> iterator = recipeList.iterator(); \
while(iterator.hasNext()) {{ AStack recipeStack = iterator.next(); \
if(recipeStack.matchesRecipe(inputStack, true) && inputStack.getCount() >= recipeStack.stacksize) {{ hasMatch = true; iterator.remove(); break; }} }} \
if(!hasMatch) return false; }} return recipeList.isEmpty(); }}"""


def matchers():
    original = compact(text(ORIGINAL / "inventory/recipes/loader/SerializableRecipe.java"))
    check("if(inputStack != null) { boolean hasMatch = false; Iterator<AStack> iterator = recipeList.iterator(); while(iterator.hasNext()) { "
          "AStack recipeStack = iterator.next(); if(recipeStack.matchesRecipe(inputStack, true) && inputStack.stackSize >= recipeStack.stacksize) { "
          "hasMatch = true; recipeList.remove(recipeStack); break; } } if(!hasMatch) { return false; } } } return recipeList.isEmpty();" in original,
          "original SerializableRecipe.matchesIngredients: every non-null slot uses up a matching ingredient, otherwise false; all must be used")
    arc_original = compact(text(ORIGINAL / "inventory/recipes/ArcWelderRecipes.java"))
    check("if(!hasMatch) { continue outer; } } } if(recipeList.isEmpty()) return recipe;" in arc_original,
          "original ArcWelderRecipes.getRecipe: an unmatched slot rejects the recipe; every ingredient must be used")
    for path, stacks, ingredients in (("inventory/recipes/SolderingRecipes.java", "stacks", "ingredients"),
                                      ("inventory/recipes/ArcWelderRecipes.java", "slots", "ingredientsIn")):
        source = text(JAVA / path)
        body = compact(method(source, "public static boolean matchesIngredients("))
        check(body.endswith(compact(MATCHER.format(stacks=stacks, ingredients=ingredients))) and "return true" not in body,
              f"D2: {path} matchesIngredients follows the original rule")
    soldering = compact(text(JAVA / "inventory/recipes/SolderingRecipes.java"))
    check("matchesIngredients(new ItemStack[] { inputs[0], inputs[1], inputs[2] }, recipe.toppings) && matchesIngredients(new ItemStack[] { inputs[3], inputs[4] }, recipe.pcb) "
          "&& matchesIngredients(new ItemStack[] { inputs[5] }, recipe.solder)) { return recipe; }" in soldering,
          "SolderingRecipes.getRecipe checks toppings 0-2, PCB 3-4 and solder 5 and returns the first match")
    station = compact(text(JAVA / "blockentity/machine/MachineSolderingStationBlockEntity.java"))
    check(station.count("SolderingRecipes.matchesIngredients(") == 3, "the soldering station's canProcess re-checks the three groups with the same matcher")


def connections():
    original_welder = compact(text(ORIGINAL / "tileentity/machine/TileEntityMachineArcWelder.java"))
    ports = ("PortDef.make(xCoord, yCoord, zCoord, dir), "
             "PortDef.make(xCoord + rot.offsetX, yCoord, zCoord + rot.offsetZ, dir, rot), "
             "PortDef.make(xCoord - rot.offsetX, yCoord, zCoord - rot.offsetZ, dir, rot.getOpposite()), "
             "PortDef.make(xCoord - dir.offsetX, yCoord, zCoord - dir.offsetZ, dir.getOpposite()), "
             "PortDef.make(xCoord - dir.offsetX + rot.offsetX, yCoord, zCoord - dir.offsetZ + rot.offsetZ, dir.getOpposite(), rot), "
             "PortDef.make(xCoord - dir.offsetX - rot.offsetX, yCoord, zCoord - dir.offsetZ - rot.offsetZ, dir.getOpposite(), rot.getOpposite()), }")
    check(ports in original_welder and "ForgeDirection rot = dir.getRotation(ForgeDirection.UP);" in original_welder,
          "original TileEntityMachineArcWelder.getPorts: six PortDefs on the bottom layer, rot = dir.getRotation(UP)")
    shapes = compact(text(ORIGINAL / "tileentity/TilePortShapes.java"))
    check("PortDef.make(x, y, z, dir, rot.getOpposite()), PortDef.make(x + rot.offsetX, y, z + rot.offsetZ, dir, rot), "
          "PortDef.make(x - dir.offsetX, y, z - dir.offsetZ, dir.getOpposite(), rot.getOpposite()), "
          "PortDef.make(x - dir.offsetX + rot.offsetX, y, z - dir.offsetZ + rot.offsetZ, dir.getOpposite(), rot), }" in shapes,
          "original TilePortShapes.solderer: four PortDefs with two connections each")
    port = compact(text(ORIGINAL / "tileentity/TilePort.java"))
    check("cons[i] = new DirPos(x + dirs[i].offsetX, y + dirs[i].offsetY, z + dirs[i].offsetZ, dirs[i]);" in port,
          "original PortDef.make: one connection per direction at the port plus that direction")
    # MultiblockHandlerXR.rotate: the same index permutation per facing in both repositories.
    pattern = r"return new int\[\] \{ dim\[(\d)\], dim\[(\d)\], dim\[(\d)\], dim\[(\d)\], dim\[(\d)\], dim\[(\d)\] \};"
    neo = re.findall(pattern, compact(text(JAVA / "handler/MultiblockHandlerXR.java")))
    old = re.findall(pattern, compact(text(ORIGINAL / "handler/MultiblockHandlerXR.java")))
    check(len(neo) == 3 and neo == old, f"MultiblockHandlerXR.rotate permutes the dimensions identically in both repositories ({neo})")
    for path, dims in (("blocks/machine/MachineArcWelder.java", "{1, 0, 1, 0, 1, 1}"), ("blocks/machine/MachineSolderingStation.java", "{0, 0, 1, 0, 1, 0}")):
        check(f"return new int[] {dims};" in compact(text(ORIGINAL / path)), f"original {path} dimensions {dims}")
    check("public int[] getDimensions() { return new int[] { 1, 0, 1, 0, 1, 1 }; }" in compact(text(JAVA / "blocks/machine/MachineArcWelderBlock.java"))
          and "public int[] getDimensions() { return new int[] {0, 0, 1, 0, 1, 0}; }" in compact(text(JAVA / "blocks/machine/MachineSolderingStationBlock.java")),
          "NEO uses the same dimensions for both blocks")
    welder = text(JAVA / "blockentity/machine/MachineArcWelderBlockEntity.java")
    conpos = compact(method(welder, "public DirPos[] getConPos() {"))
    check("Direction rot = dir.getClockWise();" in conpos and conpos.count("new DirPos(") == 10,
          "D3: the arc welder's getConPos returns ten connections with rot = getClockWise()")
    block = compact(method(text(JAVA / "blocks/machine/MachineArcWelderBlock.java"), "protected void fillSpace("))
    extras = re.findall(r"this\.makeExtra\(level, ([^;]+)\);", block)
    check(len(extras) == 9 and "core.relative(side.getOpposite())" in extras and "core.relative(dir.getOpposite()).relative(side.getOpposite())" in extras
          and "Direction side = dir.getClockWise();" in block,
          f"D3: fillSpace makes nine EXTRA blocks, including the two new bottom -side blocks ({extras})")
    for path in ("blockentity/machine/MachineSolderingStationBlockEntity.java", "blocks/machine/MachineSolderingStationBlock.java"):
        head = git_show(f"{BASELINE_COMMIT}:src/main/java/com/hbm/{path}").decode("utf-8").replace("\r\n", "\n")
        check(text(JAVA / path) == head, f"{path} is unchanged by Goal 10B")


def electrodes():
    original = compact(text(ORIGINAL / "main/CraftingManager.java"))
    expected = {"77": ("ARC_ELECTRODE_DESH", "INGOT_DESH", "INGOT_TITANIUM", "DESH", "TI"),
                "78": ("ARC_ELECTRODE_SATURNITE", "INGOT_SATURNITE", "INGOT_NIOBIUM", "BIGMT", "NB"),
                "79": ("ARC_ELECTRODE_DESH", "INGOT_DESH", "INGOT_TUNGSTEN", "DESH", "W")}
    provider = text(JAVA / "datagen/NtmRecipeProvider.java")
    for rid, (output, a, b, ingot, other) in expected.items():
        kind = output.removeprefix("ARC_ELECTRODE_")
        check(f"EnumElectrodeType.{kind}), new Object[] {{ \"C\", \"T\", \"C\", 'C', {ingot}.ingot(), 'T', {other}.ingot() }}" in original,
              f"original CraftingManager: {ingot} + {other} -> {kind} electrode")
        block = compact(provider[:provider.index(f'ResourceLocation.fromNamespaceAndPath("hbmsntm", "{rid}"));')].rsplit("ShapedRecipeBuilder.shaped(", 1)[1])
        check(block.startswith(f"RecipeCategory.MISC, NtmItems.{output}.get(), 1)") and f".define('A', NtmItems.{a}.get())" in block
              and f".define('B', NtmItems.{b})" in block, f"D4: provider recipe \"{rid}\": {a} / {b} -> {output}")
        data = read(GEN / f"data/hbmsntm/recipe/{rid}.json")
        check(data["result"] == {"count": 1, "id": "hbmsntm:" + output.lower()}
              and data["key"] == {"A": {"item": "hbmsntm:" + a.lower()}, "B": {"item": "hbmsntm:" + b.lower()}}
              and data["pattern"] == [" A ", " B ", " A "], f"generated recipe/{rid}.json: {a} / {b} -> {output.lower()}")


def language():
    en = read(GEN / "assets/hbmsntm/lang/en_us.json")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    for key in NAMES:
        check(en.get(key) and zh.get(key) and CJK.search(zh[key]) and zh[key].count("%s") == en[key].count("%s"),
              f"{key}: English {en.get(key)!r} and Chinese {zh.get(key)!r}")
        entry = mapping.get(key)
        check(entry is not None and entry["kind"] != "deferred" and entry["target_en"] == en[key] and entry["target_zh"] == zh[key],
              f"zh_cn-map entry for {key} matches en_us.json and zh_cn.json")
    welded = [key for key in en if key.startswith("item.hbmsntm.cast_plate_welded.")]
    check(welded and all(CJK.search(zh.get(key, "")) for key in welded), f"every welded plate name has Chinese ({len(welded)} keys)")


def source_checks():
    anvil()
    matchers()
    connections()
    electrodes()
    language()


def generated_checks():
    before = read(BEFORE_STAMP)
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"]) if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"]) if before["inputs"].get(name) != after["inputs"].get(name))
    check(len(before["generated"]) == BEFORE_COUNT and len(after["generated"]) == BEFORE_COUNT, f"{BEFORE_COUNT} generated files before and after")
    check(not added and not removed, "no generated file added or removed")
    check(modified == list(RECIPES), f"only recipe/78.json and recipe/79.json are modified: {modified}")
    check(not any("/advancement/" in name for name in modified), "no recipe advancement changes")
    check(set(changed_inputs) == CHANGED_INPUTS, f"changed generation inputs are exactly the six Goal 10B files: {sorted(set(changed_inputs) ^ CHANGED_INPUTS)}")
    for name in modified:
        check(after["generated"][name] in digests(GEN / name), f"the stamp records the current bytes of {name}")
        old_bytes = git_show(f"{BASELINE_COMMIT}:src/generated/resources/{name}")
        check(hashlib.sha256(old_bytes).hexdigest() == before["generated"][name], f"the before-stamp {name} is the {BASELINE_COMMIT} file")
    old78, old79 = (json.loads(git_show(f"{BASELINE_COMMIT}:src/generated/resources/{name}")) for name in RECIPES)
    check(old78["result"]["id"] == "hbmsntm:arc_electrode_desh" and old79["result"]["id"] == "hbmsntm:arc_electrode_saturnite",
          "before Goal 10B, 78 made the desh and 79 the saturnite electrode (the crossed outputs D4 corrects)")
    new78, new79 = (read(GEN / name) for name in RECIPES)
    check({k: v for k, v in old78.items() if k != "result"} == {k: v for k, v in new78.items() if k != "result"}
          and {k: v for k, v in old79.items() if k != "result"} == {k: v for k, v in new79.items() if k != "result"},
          "78 and 79 keep their pattern, keys and category; only the result changes")
    lang = "assets/hbmsntm/lang/en_us.json"
    check(before["generated"][lang] == after["generated"][lang], "en_us.json is unchanged by Goal 10B (no language key changes)")
    return {"baseline": str(BEFORE_STAMP.relative_to(ROOT).as_posix()), "generated_added": added, "generated_modified": modified,
            "generated_removed": removed, "changed_inputs": changed_inputs, "generated_count": len(after["generated"])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", help="skip checks that need a fresh runData")
    args = parser.parse_args()
    source_checks()
    report = {"mode": "source-only" if args.source_only else "full"}
    if not args.source_only:
        report.update(generated_checks())
    report.update({"checks": len(checks), "assertions": checks,
                   "boundary": "Source text, the original's text, generated recipes and language files only; "
                               "no Minecraft recipe loading, JEI display, rendering or gameplay run."})
    OUT.mkdir(parents=True, exist_ok=True)
    name = "source-check.json" if args.source_only else "generated-check.json"
    (OUT / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 10B resources ({report['mode']}): {len(checks)} checks passed; report {OUT / name}")


if __name__ == "__main__":
    main()
