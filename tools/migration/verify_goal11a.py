"""Goal 11A regression: the derrick (connections, recipes, drill depth), the oil bubble (placement, replacement, trial
chamber avoidance, drain), oil rock, the fluid burner and the fluid names.

Two Java worlds compile real production classes against isolated stand-ins (see goal11a_regression/README.md):

* the machine world (goal11a_regression/stubs.py: the Goal 10C machine world extended with a block identity model, world
  generation and the fuels) runs sections 1, 3-5, 7, 9 and 10 in com.hbm.blockentity.machine.Goal11ARegression: the
  production MachineOilWellBlockEntity/Block, OilDrillBaseBlockEntity, MachineFrackingTowerBlockEntity,
  HeaterOilburnerBlockEntity/Block and OilBubbleFeature with the Goal 10C energy/fluid/heat network, boiler, steam engine
  and heaters, and the live AnvilRecipes against the 8a209c35 copy (git show, package goal11a.head). Section 4 runs the
  feature in a model of Minecraft's WorldGenRegion; the members of #hbmsntm:oil_bubble_avoid are read from the tag file;
* the recipe world (the Goal 3C loader world with real Gson and the production cast plate ingredient) runs section 2 on
  the production AssemblyMachineRecipes against its 8a209c35 copy and exports the two recipes through the production
  writer to build/migration/goal11a/recipe-reference/.

Sections 3b, 6 and 8 are text checks of the generated resources, the datagen providers and the original, run here in
Python. Every section reports "N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the
run fails at the end.
"""

from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

from goal11a_regression.stubs import GOAL11A_SOURCES, build_stubs, recipe_stubs
from goal13a_regression.anvil_block import stripped_sources
from verify_goal10c import PRODUCTION as GOAL10C_PRODUCTION, Sections, jdk
from verify_goal3c_recipes import GSON, PRODUCTION as RECIPE_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
ORIGINAL_LANG = ORIGINAL_ROOT / "src/main/resources/assets/hbm/lang"
FIXTURE = Path(__file__).with_name("goal11a_regression")
OUTPUT = ROOT / "build/migration/goal11a/regression"
# Written only for a run on the real production source (not for mutated copies).
RECIPE_REFERENCE = ROOT / "build/migration/goal11a/recipe-reference"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
AVOID_TAG = RESOURCES / "data/hbmsntm/tags/worldgen/structure/oil_bubble_avoid.json"
# The Goal 10A-10C commit: HEAD when Goal 11A started. Pinned, so a later commit of Goal 11A does not move the baseline.
BASELINE_COMMIT = "8a209c35"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
# Not compiled: the datagen providers, NtmPlacedFeatures and the language provider (sections 3b, 6 and 8 read their text
# and the generated JSON), MachineCrucibleBlockEntity (its heat pull is copied onto a probe, see stubs.crucible_probe).
PRODUCTION = tuple(dict.fromkeys(list(GOAL10C_PRODUCTION) + list(GOAL11A_SOURCES) + ["api/hbm/block/IToolable.java"]))
FIXTURES = (
    "com/hbm/blocks/Goal11ABlockAccess.java",
    "com/hbm/blockentity/Goal11AProxyAccess.java",
    "com/hbm/blockentity/machine/heater/Goal11AHeaterAccess.java",
    "com/hbm/world/feature/Goal11AWorldGen.java",
    "com/hbm/blockentity/machine/Goal11ARegression.java",
)
RECIPE_FIXTURE = "com/hbm/inventory/recipes/loader/Goal11ARecipeRegression.java"


def baseline(path, package, target):
    """A committed production source moved to the package `target`; it still sees its own package's classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:src/main/java/{path}"], capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"baseline package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


def compact(text):
    return re.sub(r"\s+", " ", text)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def java(path):
    """A production source under SOURCE (the mutation check points SOURCE at a mutated copy)."""
    return (SOURCE / "com/hbm" / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def original(path):
    return (ORIGINAL / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def method(text, signature):
    start = text.find(signature)
    if start < 0 or text.find(signature, start + 1) >= 0:
        raise AssertionError(f"not found once: {signature}")
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
        i += 1


def lang(path):
    """An original .lang file: key=value lines, the first occurrence of a key wins."""
    entries = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            entries.setdefault(key.strip(), value)
    return entries


# ---- Python section 3b: placed feature --------------------------------------------------------------------------------

def placed_feature(check):
    bubble = original("world/gen/terrain/MapGenBubble.java")
    check("public int minY = 15;" in bubble and "public int rangeY = 25;" in bubble and "int yCoord = rand.nextInt(rangeY) + minY;" in bubble,
          "original MapGenBubble.java:27-28,59: centre Y = 15 + nextInt(25), i.e. 15..39 above the bedrock floor at Y 0")
    check("double radius = rand.nextInt(maxSize - minSize) + minSize;" in bubble and "double radiusSqr = (radius * radius) / 2;" in bubble
          and "double rSqr = x * x + z * z + y * y * 3;" in bubble and "if(rSqr < radiusSqr) {" in bubble,
          "original MapGenBubble.java:62-80: radius nextInt(max - min) + min, x^2 + z^2 + 3y^2 < r^2 / 2 (doubles)")
    world = original("lib/HbmWorld.java")
    check("oilBubble.setSize(8, 16);" in world and "oilBubble.block = ModBlocks.ore_oil;" in world and "public Block replace = Blocks.stone;" in bubble,
          "original HbmWorld.java:71-73: oil bubbles of radius 8..15 replacing stone")
    placed = read_json(GENERATED / "data/hbmsntm/worldgen/placed_feature/oil_bubble_placed.json")
    expected = {"feature": "hbmsntm:oil_bubble", "placement": [
        {"type": "minecraft:in_square"},
        {"type": "minecraft:height_range", "height": {"type": "minecraft:uniform", "min_inclusive": {"above_bottom": 15},
                                                       "max_inclusive": {"above_bottom": 39}}}]}
    check(placed == expected, f"generated oil_bubble_placed.json: in_square, then uniform height above_bottom 15..39: {placed}")
    provider = compact(java("world/gen/NtmPlacedFeatures.java"))
    line = re.search(r"register\(context, OIL_BUBBLE_PLACED, (.*?)\);", provider)
    check(line is not None and line.group(1) == "configuredFeatures.getOrThrow(NtmConfiguredFeatures.OIL_BUBBLE), List.of(InSquarePlacement.spread(), "
          "HeightRangePlacement.uniform(VerticalAnchor.aboveBottom(15), VerticalAnchor.aboveBottom(39)))",
          f"NtmPlacedFeatures (the datagen source): in_square and aboveBottom(15)..aboveBottom(39): {line.group(1) if line else None}")
    feature = java("world/feature/OilBubbleFeature.java")
    spawn = compact(method(feature, "private void spawnOil(WorldGenLevel level, int x, int y, int z, int radius) {"))
    check("is(BlockTags.BASE_STONE_OVERWORLD)" in spawn and "Blocks.STONE" not in spawn,
          "OilBubbleFeature.spawnOil replaces #minecraft:base_stone_overworld (not only Blocks.STONE)")
    place = compact(method(feature, "public boolean place(FeaturePlaceContext<NoneFeatureConfiguration> context) {"))
    check(place.index("random.nextInt(BUBBLE_RADIUS_VARIATION)") < place.index("if(touchesAvoidedStructure(level, origin, radius)) { return false; }")
          < place.index("spawnOil(level,") < place.index("addSurfaceSpot(level, random,"),
          "place(): spawn roll, radius roll, then the avoidance check before any block is written")
    tag = read_json(AVOID_TAG)
    check(tag == {"replace": False, "values": ["minecraft:trial_chambers"]},
          f"data/hbmsntm/tags/worldgen/structure/oil_bubble_avoid.json: replace false, exactly minecraft:trial_chambers: {tag}")
    tags = java("inventory/NtmTags.java")
    check(re.search(r'OIL_BUBBLE_AVOID\s*=\s*TagKey\.create\(Registries\.STRUCTURE,\s*NuclearTechMod\.withDefaultNamespace\("oil_bubble_avoid"\)\)', tags) is not None,
          "NtmTags.Structures.OIL_BUBBLE_AVOID names hbmsntm:oil_bubble_avoid (the tag file above)")


# ---- Python section 6: oil rock ------------------------------------------------------------------------------------------

def ore(check):
    blocks = original("blocks/ModBlocks.java")
    check(re.search(r'ore_oil = new BlockOre\(Material\.rock\)\.setBlockName\("ore_oil"\)[^;]*\.setHardness\(5\.0F\)\.setResistance\(10\.0F\)', blocks)
          and re.search(r'ore_oil_empty = new BlockGeneric\(Material\.rock\)\.setBlockName\("ore_oil_empty"\)[^;]*\.setHardness\(5\.0F\)\.setResistance\(10\.0F\)', blocks),
          "original ModBlocks.java:1326-1327: ore_oil and ore_oil_empty hardness 5, resistance 10")
    block_ore = original("blocks/generic/BlockOre.java")
    check("if(this == ModBlocks.ore_oil) return false;" in block_ore and "if(this == ModBlocks.ore_oil) return ModItems.oil_tar;" in block_ore
          and "rand.nextInt(fortune + 2) - 1" in block_ore,
          "original BlockOre.java:46-48, :105, :132-139: no silk touch for ore_oil, it drops oil tar, fortune multiplies the drop")
    neo = java("blocks/NtmBlocks.java")
    for name in ("ore_oil", "ore_oil_empty"):
        line = re.search(rf'register\("{name}", \(\) -> new Block\(BlockBehaviour\.Properties\.of\(\)([^;]*)\)\)\);', neo)
        check(line is not None and ".strength(5.0F).explosionResistance(10.0F)" in line.group(1),
              f"NtmBlocks {name}: strength 5, explosion resistance 10 ({line.group(1) if line else None})")
        # A text check: the Block properties are not evaluated (NtmBlocks is not compiled; the stand-in blocks are only identities).
        # The original's Material.rock is a material that needs a tool, so oil rock drops nothing broken by hand; in 1.21 that
        # is requiresCorrectToolForDrops together with the pickaxe tag below (no needs_*_tool tag: any pickaxe, as in 1.7.10).
        check(line is not None and ".requiresCorrectToolForDrops()" in line.group(1),
              f"NtmBlocks {name}: requiresCorrectToolForDrops (original Material.rock: drops only with a pickaxe; text check) ({line.group(1) if line else None})")
    loot = read_json(GENERATED / "data/hbmsntm/loot_table/blocks/ore_oil.json")
    pools = loot.get("pools", [])
    entry = pools[0]["entries"][0] if len(pools) == 1 and len(pools[0].get("entries", [])) == 1 else {}
    check(loot.get("type") == "minecraft:block" and len(pools) == 1 and pools[0].get("rolls") == 1.0 and "conditions" not in pools[0]
          and entry.get("type") == "minecraft:item" and entry.get("name") == "hbmsntm:oil_tar_crude" and "conditions" not in entry
          and entry.get("functions") == [{"enchantment": "minecraft:fortune", "formula": "minecraft:ore_drops", "function": "minecraft:apply_bonus"},
                                         {"function": "minecraft:explosion_decay"}],
          f"generated ore_oil loot: one pool, one oil_tar_crude entry with fortune ore_drops and explosion decay, no silk-touch branch: {loot}")
    provider = java("datagen/NtmBlockLootTableProvider.java")
    check("this.add(NtmBlocks.ORE_OIL.get(), block -> this.oreDropNoSilk(block, NtmItems.OIL_TAR_CRUDE.get()));" in provider
          and "this.dropSelf(NtmBlocks.ORE_OIL.get());" not in provider,
          "NtmBlockLootTableProvider (the datagen source): ore_oil uses oreDropNoSilk with crude oil tar")
    body = compact(method(provider, "private LootTable.Builder oreDropNoSilk(Block block, Item item) {"))
    check("createSilkTouchDispatchTable" not in body and "this.applyExplosionDecay(block, LootItem.lootTableItem(item)" in body
          and "ApplyBonusCount.addOreBonusCount(" in body and "Enchantments.FORTUNE" in body and "ConstantValue.exactly(1)" in body,
          "oreDropNoSilk: one roll, ore-drop fortune bonus, explosion decay, no silk-touch dispatch")
    pick = read_json(GENERATED / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    check("hbmsntm:ore_oil" in pick and "hbmsntm:ore_oil_empty" in pick, "#minecraft:mineable/pickaxe still holds ore_oil and ore_oil_empty")
    tiers = sorted(path.relative_to(ROOT).as_posix() for root in (GENERATED, RESOURCES) for path in (root / "data/minecraft/tags/block").glob("needs_*.json")
                   if "hbmsntm:ore_oil" in path.read_text(encoding="utf-8"))
    check(not tiers, f"no needs_*_tool tag holds ore_oil or ore_oil_empty (any pickaxe works, as the original): {tiers}")
    # Drill depth sources (section 5 runs them): the pumpjack inherits the derrick's depth, the fracking tower overrides it.
    drill = original("tileentity/machine/oil/TileEntityOilDrillBase.java")
    check(compact(method(drill, "public int getDrillDepth() {")) == "public int getDrillDepth() { return 5; }"
          and compact(method(original("tileentity/machine/oil/TileEntityMachineFrackingTower.java"), "public int getDrillDepth() {")) == "public int getDrillDepth() { return 0; }",
          "original drill depths: TileEntityOilDrillBase 5, TileEntityMachineFrackingTower 0 (from the bedrock floor at Y 0)")
    pump = java("blockentity/machine/oil/MachinePumpjackBlockEntity.java")
    check("getDrillDepth" not in pump, "the pumpjack does not override getDrillDepth (world bottom + 5, as the derrick)")


# ---- Python section 8: fluid names -----------------------------------------------------------------------------------------

def fluid_names(check):
    fluids = java("inventory/fluid/Fluids.java")
    names = re.findall(r'new FluidType\((?:\d+,\s*)?"([A-Z][A-Z_0-9]*)"', fluids)
    check(len(names) == len(set(names)) == 156, f"Fluids.java declares 156 named fluid types (both constructor forms): {len(names)}")
    unlocalized = java("inventory/fluid/FluidType.java")
    check(unlocalized.count('this.unlocalized = "hbmfluid." + name.toLowerCase(Locale.US);') == 3,
          "FluidType: every constructor path names its key hbmfluid.<name lower case>")
    keys = {"hbmfluid." + name.lower() for name in names}
    provider = java("datagen/NtmLanguageProvider.java")
    provided = dict(re.findall(r'this\.add\("(hbmfluid\.[a-z0-9_]+)", "((?:[^"\\]|\\.)*)"\);', provider))
    en = read_json(GENERATED / "assets/hbmsntm/lang/en_us.json")
    zh = read_json(RESOURCES / "assets/hbmsntm/lang/zh_cn.json")
    missing = sorted(key for key in keys if key not in provided)
    check(not missing, f"every fluid key has an English entry in NtmLanguageProvider (the datagen source): missing {missing[:6]}")
    check(all(key in en and key in zh for key in keys), f"every fluid key exists in en_us.json and zh_cn.json: "
          f"{sorted(k for k in keys if k not in en or k not in zh)[:6]}")
    check(all(en[key] == provided[key] for key in keys), "generated en_us.json fluid names equal the provider's")
    orphans = sorted(key for key in provided if key not in keys)
    check(orphans == ["hbmfluid.cold_perfluoromethyl", "hbmfluid.hydrazine", "hbmfluid.schrabidic_acid"],
          f"exactly three language keys no fluid uses (recorded, not removed): {orphans}")
    check(sorted(k for k in zh if k.startswith("hbmfluid.") and k not in keys) == orphans, "zh_cn.json has the same three orphan fluid keys")
    renamed = ["oil", "hotoil", "heavyoil", "smear", "heatingoil", "reclaimed", "lightoil", "helium3", "crackoil", "coaloil", "hotcrackoil",
               "naphtha_crack", "lightoil_crack", "heavyoil_vacuum", "lightoil_vacuum", "heatingoil_vacuum", "helium4", "oil_ds", "hotoil_ds",
               "crackoil_ds", "hotcrackoil_ds", "naphtha_ds", "lightoil_ds", "dhc"]
    check(len(renamed) == 24 and all("hbmfluid." + name in keys for name in renamed), "the 24 Goal 11A keys are fluid keys")
    en_original, zh_original = lang(ORIGINAL_LANG / "en_US.lang"), lang(ORIGINAL_LANG / "zh_CN.lang")
    wrong = [name for name in renamed if en["hbmfluid." + name] != en_original.get("hbmfluid." + name)]
    check(not wrong, f"the 24 English names equal the original en_US.lang: {wrong}")
    wrong = [name for name in renamed if zh["hbmfluid." + name] != zh_original.get("hbmfluid." + name)]
    check(not wrong, f"the 24 Chinese names equal the original zh_CN.lang: {wrong}")
    check(en["hbmfluid.oil"] == "Crude Oil" and zh["hbmfluid.oil"] == "原油" and en["hbmfluid.dhc"] == "Deuterated Hydrocarbon" and zh["hbmfluid.dhc"] == "氘代烃",
          "hbmfluid.oil = Crude Oil / 原油, hbmfluid.dhc = Deuterated Hydrocarbon / 氘代烃")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 11A transcript: {log}", flush=True)
    failed = []

    def run(label, command, stage_failure_ok=False):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"== {label} ==\ncommand: {subprocess.list2cmdline(command)}\n"
                         f"returncode: {result.returncode}\nstdout:\n{result.stdout}\n"
                         f"stderr:\n{result.stderr}\n")
        if result.stdout.strip():
            print(result.stdout.strip(), flush=True)
        if result.returncode:
            print(f"{label}: failed; see {log}", file=sys.stderr, flush=True)
            print(result.stderr, file=sys.stderr, flush=True)
            if not stage_failure_ok:
                raise SystemExit(result.returncode)
            failed.append(label)
            return
        print(f"{label}: passed", flush=True)

    def write_sources(root, stubs, extra):
        paths = []
        for stub, content in stubs.items():
            path = root / "stubs" / stub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(str(path))
        paths.extend(str(p) for p in extra)
        sources = root / "sources.txt"
        # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
        sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        return sources, classes

    # ---- Machine world (sections 1, 3-5, 7, 9, 10) ----
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
    head_anvil = baseline(ANVIL, "com.hbm.inventory.recipes.anvil", "goal11a.head")
    stubs = build_stubs(SOURCE, [head_anvil], vanilla_tags)
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
    stubs["goal11a/head/AnvilRecipes.java"] = head_anvil
    machine = run_dir / "machine"
    sources, classes = write_sources(machine, stubs, stripped_sources([SOURCE / p for p in PRODUCTION], machine) + [FIXTURE / p for p in FIXTURES])  # Goal 13A: without its anvil block
    avoid = read_json(AVOID_TAG)["values"]
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nanvil baseline: git {BASELINE_COMMIT}:src/main/java/{ANVIL} as goal11a.head.AnvilRecipes\n"
                     f"#hbmsntm:oil_bubble_avoid values: {avoid}\nproduction sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))
    run("Compile the Goal 11A machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                               "-d", str(classes), f"@{sources}"])
    # Every section runs, so every failing section is reported.
    run("Run Goal 11A machine world (sections 1, 3-5, 7, 9, 10)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal11ARegression", ",".join(avoid)],
        stage_failure_ok=True)

    # ---- Recipe world (section 2) ----
    head_assembly = baseline(ASSEMBLY, "com.hbm.inventory.recipes", "goal11a.head")
    rstubs = recipe_stubs(SOURCE, head_assembly)
    rstubs = {name: text for name, text in rstubs.items() if name not in RECIPE_PRODUCTION}
    rstubs["goal11a/head/AssemblyMachineRecipes.java"] = head_assembly
    recipes = run_dir / "recipes"
    rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in RECIPE_PRODUCTION] + [FIXTURE / RECIPE_FIXTURE])
    run("Compile the Goal 11A recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                              "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
    exported = run_dir / "recipe-reference"
    run("Run Goal 11A recipe world (section 2)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal11ARecipeRegression", str(exported)],
        stage_failure_ok=True)
    if SOURCE == ROOT / "src/main/java" and "Run Goal 11A recipe world (section 2)" not in failed:
        RECIPE_REFERENCE.mkdir(parents=True, exist_ok=True)
        for file in sorted(exported.glob("*.recipe.json")):
            shutil.copyfile(file, RECIPE_REFERENCE / file.name)
            print(f"recipe reference: {(RECIPE_REFERENCE / file.name).relative_to(ROOT)}", flush=True)

    sections = Sections()
    sections.run("3b. bubble placement: placed feature and sources", placed_feature)
    sections.run("6. oil rock", ore)
    sections.run("8. fluid names", fluid_names)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 11A Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 11A regression failed: {failed}")


if __name__ == "__main__":
    main()
