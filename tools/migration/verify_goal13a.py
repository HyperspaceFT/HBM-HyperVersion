"""Goal 13A regression: the blueprint items (copying, the hover text, the model type), the blueprint booklet, the alt..circuit
assembler recipes, the isolated blueprint chest and its loot table, the meteorite treasure, the electric and heat exchanging
heater anvil entries, the electric heater (default setting, useUpHeat, the hum loop) and the concrete chain.

Three Java worlds compile real production classes against isolated stand-ins (see goal13a_regression/README.md):

* the shredder world (the Goal 4 shredder world, real Gson, production SerializableRecipe loader) runs section 8s in
  com.hbm.inventory.recipes.loader.Goal13AShredderRegression on the production ShredderRecipes against its 12f38317 copy
  (git show, package goal13a.head);
* the recipe world (the Goal 12B recipe world, real Gson, with NtmConfig.enable528()) runs sections 3 and 8c in
  com.hbm.inventory.recipes.loader.Goal13ARecipeRegression, with AssemblyMachineRecipes and ChemicalPlantRecipes at 12f38317
  (goal13a.head) for the comparisons;
* the machine world (goal13a_regression/stubs.py: the Goal 12B machine world plus the production BlueprintFolderItem,
  AssemblyMachineRecipes, ModuleMachineAssembler, MachineAssemblyMachineBlockEntity and its menu, HeaterElectricBlockEntity,
  HeaterHeatexBlockEntity and BlueprintChestFeature) runs sections 1, 2, 4, 6, 7 and 9 in
  com.hbm.blockentity.machine.Goal13ARegression, with the live AnvilRecipes against its 12f38317 copy (goal13a.head).

The Python sections read source text, the generated JSON and the original; section 8t joins the facts the Java worlds wrote into
the whole concrete chain. Every section reports "N. name: X checks passed"; a failed check prints "AssertionError in <section> ..."
and the run fails at the end. Lines starting with "info:" are observations, not checks.
"""

from pathlib import Path
import json
import math
import re
import subprocess
import sys
import uuid
import zipfile

from goal11c_regression.stubs import shredder_stubs
from goal12b_regression.stubs import GOAL12B_SOURCES
from goal13a_regression.anvil_block import without_goal13a
from goal13a_regression.stubs import GOAL13A_SOURCES, build_stubs, recipe_stubs
from verify_goal10c import Sections, jdk
from verify_goal12b import PRODUCTION as GOAL12B_PRODUCTION, RECIPE_PRODUCTION as GOAL12B_RECIPE_PRODUCTION
from verify_goal4_recipes import PRODUCTION as SHREDDER_PRODUCTION
from verify_goal3c_recipes import GSON


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal13a_regression")
FIXTURE11A = Path(__file__).with_name("goal11a_regression")
OUTPUT = ROOT / "build/migration/goal13a/regression"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
# Goal 12B, HEAD when Goal 13A started. Pinned, so a later commit of Goal 13A does not move the baseline.
BASELINE_COMMIT = "12f38317"
ANVIL = "com/hbm/inventory/recipes/anvil/AnvilRecipes.java"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
CHEM = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
# Not compiled: the datagen providers (the sections read their text and the generated JSON), the registries (NtmItems, NtmBlocks,
# NtmFeatures, NtmSoundEvents), NuclearTechModClient (the blueprint_type property), the renderers and screens.
PRODUCTION = tuple(dict.fromkeys(list(GOAL12B_PRODUCTION) + list(GOAL13A_SOURCES)))
FIXTURES = (
    "com/hbm/world/feature/Goal13AWorldGen.java",
    "com/hbm/blockentity/machine/Goal13ARegression.java",
)
FIXTURES11A = ("com/hbm/world/feature/Goal11AWorldGen.java",)
RECIPE_PRODUCTION = tuple(GOAL12B_RECIPE_PRODUCTION)
RECIPE_FIXTURE = "com/hbm/inventory/recipes/loader/Goal13ARecipeRegression.java"
SHREDDER_FIXTURE = "com/hbm/inventory/recipes/loader/Goal13AShredderRegression.java"


def baseline(path, package, target="goal13a.head"):
    """A committed production source moved to the package `target`; it still sees its own package's classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:{path}"], capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"baseline package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


def baseline_text(path):
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:{path}"], capture_output=True, check=True).stdout.decode("utf-8").replace("\r\n", "\n")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def java(path):
    """A production source under SOURCE (the mutation check points SOURCE at a mutated copy)."""
    return (SOURCE / "com/hbm" / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def original(path):
    return (ORIGINAL / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")


def line(lines, number, text):
    """Whether the original line `number` (1-based) contains `text`."""
    return 0 < number <= len(lines) and text in lines[number - 1]


def recipe(name):
    return read_json(GENERATED / f"data/hbmsntm/recipe/{name}.json")


def compact(text):
    return re.sub(r"\s+", " ", text)


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


def registered(source_text, constant):
    """The registry name NtmItems / NtmBlocks gives a constant: `CONST = ... register...("name"`."""
    match = re.search(r"\b" + constant + r"\s*=\s*[\w.]+\(\s*\"([a-z0-9_]+)\"", source_text)
    return match.group(1) if match else None


# ---- Python section 1t: blueprint items, models and registration -----------------------------------------------------------

def items_text(check):
    items = java("items/NtmItems.java")
    check('BLUEPRINTS = ITEMS.register("blueprints", () -> new BlueprintsItem(new Item.Properties()))' in items, "NtmItems registers the blueprint as hbmsntm:blueprints")
    check('BLUEPRINT_FOLDER = ITEMS.register("blueprint_folder", () -> new BlueprintFolderItem(new Item.Properties().stacksTo(1)))' in items,
          "NtmItems registers the booklet as hbmsntm:blueprint_folder with stacksTo(1) (original ItemBlueprintFolder.java:25 setMaxStackSize(1))")
    tabs = java("inventory/NtmCreativeTabs.java")
    check("addMetaItems(output, NtmItems.BLUEPRINTS.get());\n                        addMetaItems(output, NtmItems.BLUEPRINT_FOLDER.get());" in tabs,
          "the control tab lists the blueprints and then the booklet through addMetaItems (getSubItems: meta 0 and 1)")
    folder = java("items/machine/BlueprintFolderItem.java")
    check("super(properties, Type.class, false, true);" in folder, "the booklet is an EnumMultiItem with multiTexture (one texture per meta: blueprint_folder.alt/.discover/.secret)")
    client = java("main/NuclearTechModClient.java")
    check("ItemProperties.register(NtmItems.BLUEPRINTS.get(), NuclearTechMod.withDefaultNamespace(\"blueprint_type\"), (stack, level, entity, seed) -> BlueprintsItem.getModelType(stack));" in client,
          "NuclearTechModClient registers the blueprint_type property from BlueprintsItem.getModelType")
    base = read_json(GENERATED / "assets/hbmsntm/models/item/blueprints.json")
    overrides = [(o["predicate"], o["model"]) for o in base.get("overrides", [])]
    check(base.get("parent") == "minecraft:item/generated" and base.get("textures") == {"layer0": "hbmsntm:item/blueprints"}
          and overrides == [({"hbmsntm:blueprint_type": 1.0}, "hbmsntm:item/blueprints_discover"), ({"hbmsntm:blueprint_type": 2.0}, "hbmsntm:item/blueprints_secret"),
                            ({"hbmsntm:blueprint_type": 3.0}, "hbmsntm:item/blueprints_528")],
          f"models/item/blueprints.json: the blue blueprint texture and overrides blueprint_type 1/2/3 -> discover/secret/528 (original ItemBlueprints.java:45-56): {overrides}")
    for name, texture in (("blueprints_discover", "blueprints_discover"), ("blueprints_secret", "blueprints_secret"), ("blueprints_528", "blueprints_528")):
        model = read_json(GENERATED / f"assets/hbmsntm/models/item/{name}.json")
        check(model == {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/{texture}"}}, f"models/item/{name}.json is a flat item with the texture item/{texture}")
    folder_model = read_json(GENERATED / "assets/hbmsntm/models/item/blueprint_folder.json")
    check([(o["predicate"], o["model"]) for o in folder_model["overrides"]] == [({"hbmsntm:item_meta": float(i)}, f"hbmsntm:item/blueprint_folder_{i}") for i in range(3)],
          "models/item/blueprint_folder.json: item_meta 0, 1, 2 select blueprint_folder_0..2")
    for i, kind in enumerate(("alt", "discover", "secret")):
        model = read_json(GENERATED / f"assets/hbmsntm/models/item/blueprint_folder_{i}.json")
        check(model == {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/blueprint_folder.{kind}"}},
              f"models/item/blueprint_folder_{i}.json uses the texture item/blueprint_folder.{kind} (original getIconFromDamage: 1 discover, 2 secret, else the default)")
    textures = RESOURCES / "assets/hbmsntm/textures/item"
    missing = [n for n in ("blueprints", "blueprints_discover", "blueprints_secret", "blueprints_528", "blueprint_folder.alt", "blueprint_folder.discover", "blueprint_folder.secret")
               if not (textures / f"{n}.png").is_file()]
    check(not missing, f"the seven textures exist under assets/hbmsntm/textures/item: missing {missing}")
    provider = java("datagen/NtmItemModelProvider.java")
    check('blueprintOverride(builder, BlueprintsItem.MODEL_DISCOVER, "blueprints_discover");' in provider and 'blueprintOverride(builder, BlueprintsItem.MODEL_SECRET, "blueprints_secret");' in provider
          and 'blueprintOverride(builder, BlueprintsItem.MODEL_528, "blueprints_528");' in provider,
          "NtmItemModelProvider.registerBlueprints builds the three overrides from the MODEL_* constants")


# ---- Python section 3p: the registered names of the recipe items ------------------------------------------------------------

def registered_ids(check):
    items = java("items/NtmItems.java")
    blocks = java("blocks/NtmBlocks.java")
    wanted = {
        "CIRCUIT_PRINTED_BOARD": "circuit_printed_board", "CIRCUIT_ANALOG_BOARD": "circuit_analog_board", "CIRCUIT_INTEGRATED_BOARD": "circuit_integrated_board",
        "CIRCUIT_MICROCHIP": "circuit_microchip", "CIRCUIT_ATOMIC_CLOCK": "circuit_atomic_clock", "WIRE_TUNGSTEN": "wire_tungsten", "WIRE_COPPER": "wire_copper",
        "PLATE_IRON": "plate_iron", "INGOT_RUBBER": "ingot_rubber", "INGOT_NIOBIUM": "ingot_niobium", "POWDER_CS137": "powder_cs137", "POWDER_CEMENT": "powder_cement",
        "POWDER_LIMESTONE": "powder_limestone", "INGOT_ASBESTOS": "ingot_asbestos", "INGOT_FERROURANIUM": "ingot_ferrouranium", "COIL_TUNGSTEN": "coil_tungsten",
        "PIPE_STEEL": "pipe_steel", "INGOT_COPPER": "ingot_copper", "BLUEPRINTS": "blueprints", "BLUEPRINT_FOLDER": "blueprint_folder",
    }
    wrong = {c: registered(items, c) for c, n in wanted.items() if registered(items, c) != n}
    check(not wrong, "the NtmItems constants the Java worlds name resolve to the registry names the recipe checks expect (the stand-in registry derives ids from the constants): " + str(wrong))
    block_names = {"CONCRETE": "concrete", "CONCRETE_SMOOTH": "concrete_smooth", "CONCRETE_ASBESTOS": "concrete_asbestos", "DUCRETE": "ducrete", "DUCRETE_SMOOTH": "ducrete_smooth",
                   "BRICK_CONCRETE": "brick_concrete", "BLOCK_SLAG": "block_slag", "RESOURCE_LIMESTONE": "resource_limestone", "HEATER_ELECTRIC": "heater_electric", "HEATER_HEATEX": "heater_heatex"}
    wrong = {c: registered(blocks, c) for c, n in block_names.items() if registered(blocks, c) != n and registered(blocks, c) is not None}
    unresolved = [c for c in block_names if registered(blocks, c) is None]
    check(not wrong and not unresolved, f"the NtmBlocks constants resolve to the expected names: wrong {wrong}, not found {unresolved}")


# ---- Python section 4j: the blueprint chest (loot table, worldgen JSON, provider and registration text) --------------------

def chest_text(check):
    loot = read_json(GENERATED / "data/hbmsntm/loot_table/chests/blueprints.json")
    pools = loot.get("pools", [])
    pool = pools[0] if len(pools) == 1 else {}
    entries = pool.get("entries", [])
    check(loot.get("type") == "minecraft:chest" and len(pools) == 1 and pool.get("rolls") == 23.0 and pool.get("bonus_rolls") == 0.0 and len(entries) == 3,
          f"chests/blueprints.json is a chest table with one pool of 23 rolls and 3 entries: rolls {pool.get('rolls')}, entries {len(entries)}")
    summary = [(e.get("name"), e.get("functions"), e.get("weight", 1)) for e in entries]

    def meta(value):
        return [{"function": "minecraft:set_components", "components": {"hbmsntm:meta": value}}]

    check(summary == [("hbmsntm:blueprint_folder", meta(0), 10), ("hbmsntm:blueprint_folder", meta(1), 5), ("hbmsntm:blueprint_folder", meta(0), 1)]
          and all(e.get("type") == "minecraft:item" and "conditions" not in e for e in entries),
          f"its 3 entries are the booklet with META 0 / 1 / 0 and weights 10 / 5 / 1 (original ItemPoolsSingle.java:116-122; a missing weight is 1): {summary}")
    weights = {0: 11, 1: 5}
    check(sum(e.get("weight", 1) for e in entries) == 16 and weights[0] / sum(weights.values()) == 11 / 16,
          "alt : discover is 11 : 5 per draw, as the original's 10 + 1 : 5")
    # The original writes 50 random slots of the 27-slot chest, overwriting; the expected number of different slots filled is 27 * (1 - (26/27) ** 50).
    original_mean = 27 * (1 - (26 / 27) ** 50)
    check(22.5 < original_mean < 23.0 and round(original_mean) == 23 and pool.get("rolls") == round(original_mean),
          f"23 rolls = the original's expected number of booklets per chest, 27 * (1 - (26/27)^50) = {original_mean:.3f} (1.21.1 LootTable.fill never overwrites a slot, so n rolls give n booklets)")
    check(loot.get("random_sequence") == "hbmsntm:chests/blueprints", "the table has its own random sequence")
    provider = java("datagen/NtmChestLootTableProvider.java")
    check("private static final int BLUEPRINT_CHEST_ROLLS = 23;" in provider and ".setRolls(ConstantValue.exactly(BLUEPRINT_CHEST_ROLLS))" in provider,
          "NtmChestLootTableProvider: 23 constant rolls")
    order = re.findall(r"\.add\(blueprintFolder\(BlueprintFolderItem\.Type\.(\w+)\)\.setWeight\((\d+)\)\)", provider)
    check(order == [("ALT", "10"), ("DISCOVER", "5"), ("ALT", "1")], f"NtmChestLootTableProvider: the entries ALT 10, DISCOVER 5, ALT 1 in that order: {order}")
    check("LootTableSubProvider" in provider and "BlueprintChestFeature.LOOT_TABLE" in provider, "the provider writes the table under the feature's loot table key")
    generators = java("datagen/NtmDataGenerators.java")
    check("new LootTableProvider.SubProviderEntry(NtmChestLootTableProvider::new, LootContextParamSets.CHEST)" in generators
          and "List.of(blockLootTableSubProvider, chestLootTableSubProvider)" in generators, "NtmDataGenerators registers the chest sub provider with LootContextParamSets.CHEST next to the block one")
    configured = read_json(GENERATED / "data/hbmsntm/worldgen/configured_feature/blueprint_chest.json")
    placed = read_json(GENERATED / "data/hbmsntm/worldgen/placed_feature/blueprint_chest_placed.json")
    modifier = read_json(GENERATED / "data/hbmsntm/neoforge/biome_modifier/add_blueprint_chest.json")
    check(configured == {"type": "hbmsntm:blueprint_chest", "config": {}}, f"configured_feature/blueprint_chest.json: {configured}")
    check(placed == {"feature": "hbmsntm:blueprint_chest", "placement": []},
          f"placed_feature/blueprint_chest_placed.json has no placement modifiers: the feature runs once per chunk at the chunk's minimum corner, the original's i and j: {placed}")
    check(modifier == {"type": "neoforge:add_features", "biomes": "#minecraft:is_overworld", "features": "hbmsntm:blueprint_chest_placed", "step": "top_layer_modification"},
          f"biome_modifier/add_blueprint_chest.json: overworld biomes, the last decoration step (the original runs after vanilla population): {modifier}")
    features = java("world/feature/NtmFeatures.java")
    check('BLUEPRINT_CHEST = FEATURES.register("blueprint_chest", () -> new BlueprintChestFeature(NoneFeatureConfiguration.CODEC))' in features, "NtmFeatures registers hbmsntm:blueprint_chest")
    gen = java("world/gen/NtmPlacedFeatures.java")
    check(re.search(r"register\(context, BLUEPRINT_CHEST_PLACED, configuredFeatures\.getOrThrow\(NtmConfiguredFeatures\.BLUEPRINT_CHEST\), List\.of\(\)\);", gen) is not None,
          "NtmPlacedFeatures: the placed feature has an empty modifier list")
    feature = java("world/feature/BlueprintChestFeature.java")
    check("SPAWN_EXCLUSION = 100;" in feature and "GRID = 5000;" in feature and "random.nextInt(20) < 10" in feature and "cX < 16 && cZ < 16" in feature,
          "BlueprintChestFeature carries the original constants (100, 5000, nextInt(20) < 10, the 16-block window)")


# ---- Python section 5: the meteorite treasure ----------------------------------------------------------------------------

def meteorite(check):
    path = "src/generated/resources/data/hbmsntm/loot_table/blocks/block_meteor_treasure.json"
    now = read_json(GENERATED / "data/hbmsntm/loot_table/blocks/block_meteor_treasure.json")
    old = json.loads(baseline_text(path))
    pool, was = now["pools"][0], old["pools"][0]
    check(len(now["pools"]) == 1 and len(old["pools"]) == 1 and was["rolls"] == 1.0 and pool["rolls"] == {"type": "minecraft:uniform", "min": 1.0, "max": 3.0},
          f"rolls: 1 at 12f38317, now uniform 1 to 3 (original BlockMeteoriteTreasure.java:24: 1 + rand.nextInt(3)): {pool['rolls']}")
    check(pool["entries"][:-1] == was["entries"] and len(pool["entries"]) == len(was["entries"]) + 1,
          f"the {len(was['entries'])} entries of 12f38317 are unchanged in content and order and one is appended")
    added = pool["entries"][-1]
    check(added == {"type": "minecraft:item", "functions": [{"function": "minecraft:set_components", "components": {"hbmsntm:meta": 1}}], "name": "hbmsntm:blueprint_folder"}
          and added.get("weight", 1) == 1, f"the appended entry is the booklet with META 1 (discover) and the default weight 1 (original ItemPoolsSingle.java:112): {added}")
    check({k: v for k, v in now.items() if k != "pools"} == {k: v for k, v in old.items() if k != "pools"} and {k: v for k, v in pool.items() if k not in ("entries", "rolls")}
          == {k: v for k, v in was.items() if k not in ("entries", "rolls")}, "the table's type, random sequence and pool fields are unchanged")
    total = sum(e.get("weight", 1) for e in pool["entries"])
    print(f"info: meteorite treasure: {len(pool['entries'])} entries, total weight {total} (the original's table has 19 entries and weight 157), booklet {1 / total:.4f} per draw", flush=True)
    provider = java("datagen/NtmBlockLootTableProvider.java")
    body = method(provider, "private LootTable.Builder meteorTreasureDrop(Block block) {")
    check(".setRolls(UniformGenerator.between(1, 3))" in body and ".add(NtmChestLootTableProvider.blueprintFolder(BlueprintFolderItem.Type.DISCOVER).setWeight(1))" in body,
          "NtmBlockLootTableProvider.meteorTreasureDrop: rolls between(1, 3) and the DISCOVER booklet at weight 1")


# ---- Python section 6t: the anvil source ----------------------------------------------------------------------------------

def anvil_source(check):
    live = (SOURCE / ANVIL).read_text(encoding="utf-8").replace("\r\n", "\n")
    base = baseline_text(f"src/main/java/{ANVIL}")
    reverted, found = without_goal13a(live)
    check(found, "the Goal 13A block (goal13a_regression/anvil_block.py) follows the Goal 12A desh motor entry exactly once, at the end of registerConstruction")
    check(reverted == base, f"without that block AnvilRecipes is byte-identical to {BASELINE_COMMIT} (modulo line ends): no import and no earlier entry changed")


# ---- Python section 7t: the electric heater sound, description and source -----------------------------------------------------

def heater_text(check):
    events = java("registry/NtmSoundEvents.java")
    check('ELECTRIC_HUM_LOOP = reg("block.electric_hum"); // BLOCKS CATEGORY' in events, "NtmSoundEvents registers block.electric_hum as ELECTRIC_HUM_LOOP (lower case: 1.21 resource paths; the original's event is block.electricHum)")
    provider = java("datagen/NtmSoundDefinitionsProvider.java")
    check(re.search(r"this\.add\(NtmSoundEvents\.ELECTRIC_HUM_LOOP, SoundDefinition\.definition\(\)\s*\.with\(sound\(\"hbmsntm:block/electric_hum\"\)\)\s*\);", provider) is not None,
          "NtmSoundDefinitionsProvider defines ELECTRIC_HUM_LOOP with the sound hbmsntm:block/electric_hum")
    sounds = read_json(GENERATED / "assets/hbmsntm/sounds.json")
    check(sounds.get("block.electric_hum") == {"sounds": ["hbmsntm:block/electric_hum"]} and "block.electricHum" not in sounds,
          f"sounds.json has block.electric_hum -> hbmsntm:block/electric_hum: {sounds.get('block.electric_hum')}")
    check((RESOURCES / "assets/hbmsntm/sounds/block/electric_hum.ogg").is_file() and not (RESOURCES / "assets/hbmsntm/sounds/block/electricHum.ogg").exists(),
          "the sound file is sounds/block/electric_hum.ogg (no mixed-case path)")
    original_sounds = (ORIGINAL_ROOT / "src/main/resources/assets/hbm/sounds.json").read_text(encoding="utf-8").split("\n")
    check(line(original_sounds, 57, '"block.electricHum": {"category": "block", "sounds": [{"name": "block/electricHum", "stream": false}]}'),
          "original sounds.json:57: block.electricHum is block/electricHum (stream false)")
    heater = java("blockentity/machine/heater/HeaterElectricBlockEntity.java")
    check("public int setting = 0;" in heater, "HeaterElectricBlockEntity.setting defaults to 0")
    check(re.search(r"public void useUpHeat\(int heat\) \{\s*(//[^\n]*\n\s*)?if\(heat <= 0\) return;", heater) is not None, "useUpHeat returns first for a non-positive amount")
    check("AudioWrapper.getLoopedSound(NtmSoundEvents.ELECTRIC_HUM_LOOP.get(), SoundSource.BLOCKS, this, 0.25F, 7.5F, 1.0F, 20)" in heater and re.search(r"\baudioTime\b", re.sub(r"//[^\n]*", "", heater)) is None,
          "createAudioLoop: the hum at volume 0.25, range 7.5, pitch 1.0, keep-alive 20 (original TileEntityHeaterElectric.java:94), and no audioTime tail")
    heatex = java("blockentity/machine/heater/HeaterHeatexBlockEntity.java")
    check("new FluidTank(Fluids.COOLANT_HOT, 24_000)," in heatex and "new FluidTank(Fluids.COOLANT, 24_000)" in heatex and "Fluids.NONE, 24_000" not in heatex,
          "HeaterHeatexBlockEntity.tanks start as COOLANT_HOT and COOLANT (text; the machine world builds the block entity)")
    # The description keys: provider, en_us.json and zh_cn.json.
    description = "Uses energy to produce heat.$Accepts heat from the bottom with 85%% efficiency.$Can be configured with a screwdriver."
    lang = java("datagen/NtmLanguageProvider.java")
    en = read_json(GENERATED / "assets/hbmsntm/lang/en_us.json")
    zh = read_json(RESOURCES / "assets/hbmsntm/lang/zh_cn.json")
    for key in ("block.hbmsntm.heater_electric.desc", "tile.heater_electric.desc"):
        check(f'this.add("{key}", "{description}");' in lang and en.get(key) == description and key in zh and zh[key].count("$") == 2 and "85%%" in zh[key],
              f"{key} exists in NtmLanguageProvider, en_us.json (the original text, %% escaped) and zh_cn.json (two $ line breaks, the %% escape)")
    heat_lang = original_lang_line("tile.heater_electric.desc")
    check(heat_lang is not None and heat_lang == description, f"the original en_US.lang tile.heater_electric.desc is the same text (it escapes the percent sign as %% too): {heat_lang}")
    zh_original = original_lang_line("tile.heater_electric.desc", "zh_CN.lang")
    check(zh_original is not None and zh_original.replace("%", "%%") == zh["tile.heater_electric.desc"], f"zh_cn.json is the original zh_CN.lang text with the percent sign escaped: {zh_original}")


def original_lang_line(key, file="en_US.lang"):
    path = ORIGINAL_ROOT / "src/main/resources/assets/hbm/lang" / file
    for entry in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if entry.startswith(key + "="):
            return entry.split("=", 1)[1]
    return None


# ---- Python section 8t: the concrete chain -------------------------------------------------------------------------------

def concrete_text(check, shredder_facts, chem_facts):
    cement = recipe("cement_from_limestone_powder")
    check(cement.get("type") == "minecraft:crafting_shapeless" and sorted(i["item"] for i in cement.get("ingredients", [])) == ["hbmsntm:powder_limestone"] + ["minecraft:clay_ball"] * 3
          and cement.get("result") == {"count": 4, "id": "hbmsntm:powder_cement"}, f"limestone powder + 3 clay balls (shapeless) -> 4 cement powder (original PowderRecipes.java:36): {cement}")
    concrete = recipe("concrete")
    check(concrete.get("type") == "minecraft:crafting_shaped" and concrete.get("pattern") == ["CC", "CC"] and concrete.get("key") == {"C": {"item": "hbmsntm:concrete_smooth"}}
          and concrete.get("result") == {"count": 4, "id": "hbmsntm:concrete"}, f"2 x 2 smooth concrete -> 4 concrete (original CraftingManager.java:362): {concrete}")
    for name, source in (("brick_concrete_from_concrete_smooth", "hbmsntm:concrete_smooth"), ("brick_concrete_from_concrete", "hbmsntm:concrete")):
        brick = recipe(name)
        check(brick.get("type") == "minecraft:crafting_shaped" and brick.get("pattern") == [" C ", "CBC", " C "] and brick.get("key") == {"C": {"item": source}, "B": {"item": "minecraft:clay_ball"}}
              and brick.get("result") == {"count": 4, "id": "hbmsntm:brick_concrete"}, f"{name}: a cross of {source} around a clay ball -> 4 concrete bricks (original :364-365): {brick}")
    for name, folder in (("concrete", "building_blocks"), ("brick_concrete_from_concrete", "building_blocks"), ("brick_concrete_from_concrete_smooth", "building_blocks"), ("cement_from_limestone_powder", "misc")):
        advancement = read_json(GENERATED / f"data/hbmsntm/advancement/recipes/{folder}/{name}.json")
        check(advancement.get("rewards") == {"recipes": [f"hbmsntm:{name}"]}, f"the advancement for {name} unlocks the recipe")
    members = read_json(GENERATED / "data/ntm/tags/item/any_concrete.json")
    check(sorted(members["values"]) == sorted(["hbmsntm:concrete", "hbmsntm:concrete_smooth", "hbmsntm:concrete_asbestos", "hbmsntm:ducrete", "hbmsntm:ducrete_smooth"])
          and len(members["values"]) == 5 and "replace" not in members, f"#ntm:any_concrete has the five members concrete, smooth concrete, asbestos concrete, ducrete, smooth ducrete: {members}")
    provider = java("datagen/NtmItemTagProvider.java")
    body = method(provider, "protected void addTags(HolderLookup.Provider provider) {") if "protected void addTags(HolderLookup.Provider provider) {" in provider else provider
    tag_members = re.search(r"this\.tag\(ANY_CONCRETE\)\.add\((.*?)\);", body, re.S)
    listed = re.findall(r"NtmBlocks\.(\w+)\.asItem\(\)", tag_members.group(1)) if tag_members else []
    check(listed == ["CONCRETE", "CONCRETE_SMOOTH", "CONCRETE_ASBESTOS", "DUCRETE", "DUCRETE_SMOOTH"], f"NtmItemTagProvider adds the five blocks to ANY_CONCRETE: {listed}")
    check('ANY_CONCRETE = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete"))' in provider, "the tag is ntm:any_concrete")
    blocks = java("blocks/NtmBlocks.java")
    for name, strength in (("concrete", "15.0F, 140.0F"), ("concrete_smooth", "15.0F, 140.0F"), ("concrete_asbestos", "15.0F, 150.0F")):
        match = re.search(r'registerBlastInfoBlock\("' + name + r'",\s*\(\) -> new Block\(BlockBehaviour\.Properties\.of\(\)\.strength\(([^)]*)\)', blocks)
        check(match is not None and match.group(1) == strength, f"NtmBlocks.{name.upper()}: strength {strength} (original ModBlocks.java:1495-1499): {match.group(1) if match else None}")
    chemical = java("inventory/recipes/ChemicalPlantRecipes.java")
    for name in ("chem.concrete", "chem.concreteasbestos", "chem.ducrete", "chem.liquidconk"):
        start = chemical.index(f'new GenericRecipe("{name}")')
        recipe_text = chemical[start:chemical.index("));", start) + 3]
        check("new TagStack(ItemTags.SAND, 8)" in recipe_text and "Blocks.SAND" not in recipe_text, f"{name} takes 8 of #minecraft:sand (ItemTags.SAND), not the sand block (original KEY_SAND)")
    # The whole chain, joined from what the production tables produced.
    limestone = shredder_facts["limestone"][0]
    slag = shredder_facts["slag"][0]
    check(limestone == "hbmsntm:powder_limestone x4" and slag == "hbmsntm:powder_cement x4", f"the shredder gives 4 limestone powder per limestone block and 4 cement powder per slag block: {limestone}, {slag}")
    powder_id = limestone.split(" x")[0]
    cement_in = [i["item"] for i in cement["ingredients"]]
    check(powder_id in cement_in, "the limestone powder from the shredder is the cement recipe's input")
    cement_id, cement_count = cement["result"]["id"], cement["result"]["count"]
    chem_recipe = chem_facts
    inputs = chem_recipe["inputItem"]
    check(inputs[0][1] == cement_id and inputs[0][2] == 1 and inputs[1][1] == "minecraft:gravel" and inputs[1][2] == 8 and inputs[2] == ["tag", "minecraft:sand", 8]
          and chem_recipe["inputFluid"] == [["WATER", 2000]], f"chem.concrete takes the crafted cement powder (1), 8 gravel, 8 sand and 2,000 mB water: {inputs}")
    smooth_id = chem_recipe["outputItem"][0][1][0]
    smooth_count = chem_recipe["outputItem"][0][1][1]
    check(smooth_id == "hbmsntm:concrete_smooth" and smooth_count == 16 and chem_recipe["duration"] == 100 and chem_recipe["power"] == 100,
          f"it makes 16 smooth concrete in 100 ticks at 100 HE/t: {chem_recipe['outputItem']}")
    check(concrete["key"]["C"]["item"] == smooth_id and concrete["result"]["id"] == "hbmsntm:concrete" and recipe("brick_concrete_from_concrete_smooth")["key"]["C"]["item"] == smooth_id
          and recipe("brick_concrete_from_concrete")["key"]["C"]["item"] == concrete["result"]["id"],
          "the smooth concrete feeds both the concrete recipe and the brick recipe, the concrete feeds the second brick recipe")
    check(shredder_facts["concrete"][0] == "minecraft:gravel x1" and shredder_facts["concrete_smooth"][0] == "minecraft:gravel x1" and inputs[1][1] == "minecraft:gravel",
          "concrete and smooth concrete shred back to gravel, the gravel chem.concrete takes")
    per_block = int(limestone.split(" x")[1]) * cement_count
    print(f"info: one limestone block -> {limestone.split(' x')[1]} limestone powder -> {per_block} cement powder -> {per_block} chem.concrete runs -> {per_block * smooth_count} smooth concrete "
          f"-> {per_block * smooth_count * 4} concrete or {per_block * smooth_count * 4} concrete bricks (2 x 2 and cross recipes)", flush=True)


# ---- Python section 13t: the original lines the Java fixtures transcribe ------------------------------------------------------

def references(check):
    bp = original("items/machine/ItemBlueprints.java")
    check(line(bp, 47, "if(stack.hasTagCompound()) {") and line(bp, 50, "POOL_PREFIX_DISCOVER") and line(bp, 51, "POOL_PREFIX_SECRET") and line(bp, 52, "POOL_PREFIX_528") and line(bp, 55, "return this.itemIcon; // blue"),
          "original ItemBlueprints.java:45-56: the icon by prefix (discover beige, secret black, 528 grey, else blue)")
    check(line(bp, 69, "if(world.isRemote) return stack;") and line(bp, 70, "if(!stack.hasTagCompound()) return stack;") and line(bp, 74, "if(poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) return stack;")
          and line(bp, 75, "if(!player.inventory.hasItem(Items.paper)) return stack;") and line(bp, 77, "player.inventory.consumeInventoryItem(Items.paper);")
          and line(bp, 83, "if(!player.capabilities.isCreativeMode) {") and line(bp, 84, "if(stack.stackSize < stack.getMaxStackSize()) {") and line(bp, 85, "stack.stackSize++;")
          and line(bp, 89, "if(!player.inventory.addItemStackToInventory(copy)) {") and line(bp, 92, "player.dropPlayerItemWithRandomChoice(copy, false);") and line(bp, 97, "player.dropPlayerItemWithRandomChoice(copy, false);"),
          "original ItemBlueprints.java:68-101: server side only, no NBT / secret / no paper return, one paper used, stack + 1 below the maximum, else the inventory, else a dropped copy; creative drops")
    check(line(bp, 117, "if(poolName.startsWith(GenericRecipes.POOL_PREFIX_SECRET)) {") and line(bp, 118, '"Cannot be copied!"') and line(bp, 120, '"Right-click to copy (requires paper)"')
          and line(bp, 114, "if(pool == null || pool.isEmpty()) {") and line(bp, 126, "list.add(recipe.getLocalizedName());"),
          "original ItemBlueprints.java:105-129: the hover lines")
    check(line(bp, 131, "public static String grabPool(ItemStack stack) {") and line(bp, 142, 'setString("pool", pool)') and line(bp, 134, "if(!stack.hasTagCompound()) return null;"),
          "original ItemBlueprints.java:131-144: the pool key")
    folder = original("items/machine/ItemBlueprintFolder.java")
    check(line(folder, 24, "this.setHasSubtypes(true);") and line(folder, 25, "this.setMaxStackSize(1);") and line(folder, 45, "for(int i = 0; i < 2; i++) list.add(new ItemStack(item, 1, i));")
          and line(folder, 50, "if(world.isRemote) return stack;") and line(folder, 55, "stack.getItemDamage() == 0 && pool.startsWith(GenericRecipes.POOL_PREFIX_ALT)")
          and line(folder, 56, "stack.getItemDamage() == 1 && pool.startsWith(GenericRecipes.POOL_PREFIX_DISCOVER)") and line(folder, 57, "stack.getItemDamage() == 2 && pool.startsWith(GenericRecipes.POOL_PREFIX_SECRET)")
          and line(folder, 60, "if(!pools.isEmpty()) {") and line(folder, 61, "stack.stackSize--;") and line(folder, 63, "pools.get(player.getRNG().nextInt(pools.size()))")
          and line(folder, 66, "if(!player.inventory.addItemStackToInventory(blueprint))") and line(folder, 67, "player.dropPlayerItemWithRandomChoice(blueprint, false);"),
          "original ItemBlueprintFolder.java:23-71: metas 0-2, stack 1, the list shows 0 and 1, server only, the pools of the prefix, uniform draw over the pools, inventory else drop")
    world = original("lib/HbmWorldGen.java")
    check(line(world, 474, "genBlueprintChest(world, rand, i, j, 5000, 5000);") and line(world, 478, "if(Math.abs(i) < 100 && Math.abs(j) < 100) return;")
          and line(world, 479, "if(rand.nextInt(20) < 10) return;") and line(world, 481, "int cX = Math.abs(i) % boundsX;") and line(world, 482, "int cZ = Math.abs(j) % boundsZ;")
          and line(world, 484, "if(cX >= 0 && cX < 16 && cZ >= 0 && cZ < 16) {") and line(world, 485, "int x = i + 8;") and line(world, 486, "int z = j + 8;")
          and line(world, 487, "int y = world.getHeightValue(x, z) - rand.nextInt(2);") and line(world, 489, "world.setBlock(x, y, z, Blocks.chest);")
          and line(world, 491, "for(int a = x - 1; a <= x + 1; a++) for(int b = y - 1; b <= y + 1; b++) for(int c = z - 1; c <= z + 1; c++) {")
          and line(world, 492, "if(a != x || b != y || c != z) world.setBlock(a, b, c, Blocks.obsidian);") and line(world, 497, "generateChestContents(rand, ItemPool.getPool(ItemPoolsSingle.POOL_BLUEPRINTS), (TileEntityChest) tile, 50)"),
          "original HbmWorldGen.java:474-499: the spawn square, the 50% draw before the grid test, the 5000 grid with a 16-block window, the chest at i + 8 / j + 8, height - nextInt(2), the obsidian cube, 50 draws")
    pools = original("itempool/ItemPoolsSingle.java")
    check(line(pools, 112, "weighted(ModItems.blueprint_folder, 1, 1, 1, 1)") and line(pools, 118, "weighted(ModItems.blueprint_folder, 0, 1, 1, 10),")
          and line(pools, 119, "weighted(ModItems.blueprint_folder, 1, 1, 1, 5),") and line(pools, 120, "weighted(ModItems.blueprint_folder, 0, 1, 1, 1),"),
          "original ItemPoolsSingle.java:112 (meteorite treasure booklet META 1, weight 1) and :118-120 (POOL_BLUEPRINTS: META 0 weight 10, META 1 weight 5, META 0 weight 1)")
    treasure = original("blocks/generic/BlockMeteoriteTreasure.java")
    check(line(treasure, 24, "int count = 1 + world.rand.nextInt(3);") and line(treasure, 27, "for(int i = 0; i < count; i++) {"), "original BlockMeteoriteTreasure.java:24-29: 1 + nextInt(3) drops")
    heater = original("tileentity/machine/TileEntityHeaterElectric.java")
    check(line(heater, 31, "protected int setting = 0;") and line(heater, 61, "if(setting > 0 && this.power >= this.getConsumption()) {") and line(heater, 70, "if(isOn) {")
          and line(heater, 82, "} else {") and line(heater, 85, "audio.stopSound();") and line(heater, 94, "0.25F, 7.5F, 1.0F, 20)") and line(heater, 156, "this.heatEnergy += source.getHeatStored() * 0.85;")
          and line(heater, 164, "if(setting > 10)") and line(heater, 174, "return (long) (Math.pow(setting, 1.4D) * 200D);") and line(heater, 179, "return getConsumption() * 20;")
          and line(heater, 183, "return this.setting * 100;") and line(heater, 198, "this.heatEnergy = Math.max(0, this.heatEnergy - heat);"),
          "original TileEntityHeaterElectric.java: setting 0, the run test, the hum loop, 85%, the wrap, consumption, max power, heat per setting; useUpHeat has no guard (NEO's guard is GOAL13A A12)")
    heatex = original("tileentity/machine/TileEntityHeaterHeatex.java")
    check(line(heatex, 42, "this.tanks[0] = new FluidTank(Fluids.COOLANT_HOT, 24_000);") and line(heatex, 43, "this.tanks[1] = new FluidTank(Fluids.COOLANT, 24_000);"),
          "original TileEntityHeaterHeatex.java:42-43: COOLANT_HOT in, COOLANT out, 24,000 each")
    anvil = original("inventory/recipes/anvil/AnvilRecipes.java")
    check(line(anvil, 293, "new OreDictStack(ANY_PLASTIC.ingot(), 4),") and line(anvil, 294, "new OreDictStack(CU.ingot(), 8),") and line(anvil, 295, "new OreDictStack(STEEL.plate(), 8),")
          and line(anvil, 296, "new ComparableStack(ModItems.coil_tungsten, 8),") and line(anvil, 297, "EnumCircuitType.BASIC.ordinal())") and line(anvil, 298, "new ItemStack(ModBlocks.heater_electric))).setTier(3));")
          and line(anvil, 302, "new OreDictStack(RUBBER.ingot(), 4),") and line(anvil, 303, "new OreDictStack(CU.ingot(), 16),") and line(anvil, 304, "new OreDictStack(STEEL.plate(), 16),")
          and line(anvil, 305, "new OreDictStack(STEEL.pipe(), 3),") and line(anvil, 306, "new ItemStack(ModBlocks.heater_heatex))).setTier(3));"),
          "original AnvilRecipes.java:291-306: the two heater entries (tier 3)")
    assembly = original("inventory/recipes/AssemblyMachineRecipes.java")
    check(line(assembly, 126, "if(!GeneralConfig.enable528) {") and line(assembly, 137, 'new GenericRecipe("ass.analogAlt").setupNamed(200, 250)') and line(assembly, 138, 'POOL_PREFIX_ALT + ".circuit"')
          and line(assembly, 139, 'new GenericRecipe("ass.factorioChip").setupNamed(300, 20_000)') and line(assembly, 140, 'POOL_PREFIX_ALT + ".circuit"')
          and line(assembly, 141, 'new GenericRecipe("ass.atomicClockAlt").setupNamed(300, 20_000)') and line(assembly, 142, 'POOL_PREFIX_ALT + ".circuit"')
          and line(assembly, 138, "new ComparableStack(ModItems.circuit, 4, EnumCircuitType.PCB), new OreDictStack(ANY_PLASTIC.ingot(), 4), new OreDictStack(W.wireFine(), 8), new OreDictStack(NB.ingot())")
          and line(assembly, 140, "new OreDictStack(RUBBER.ingot(), 2), new OreDictStack(IRON.plate(), 4), new OreDictStack(CU.wireFine(), 8)")
          and line(assembly, 142, "new OreDictStack(ANY_PLASTIC.ingot(), 4), new ComparableStack(ModItems.circuit, 3, EnumCircuitType.CHIP), new OreDictStack(CS137.dust(), 1)"),
          "original AssemblyMachineRecipes.java:126, 137-142: the !enable528 block and the three alt..circuit recipes")
    chem = original("inventory/recipes/ChemicalPlantRecipes.java")
    check(line(chem, 140, '"chem.concrete").setup(100, 100)') and line(chem, 141, "new ComparableStack(ModItems.powder_cement, 1), new ComparableStack(Blocks.gravel, 8), new OreDictStack(KEY_SAND, 8)")
          and line(chem, 142, "new FluidStack(Fluids.WATER, 2_000)") and line(chem, 143, "new ItemStack(ModBlocks.concrete_smooth, 16)")
          and line(chem, 145, '"chem.concreteasbestos").setup(100, 100)') and line(chem, 146, "new ComparableStack(ModItems.powder_cement, 4)") and line(chem, 148, "new ItemStack(ModBlocks.concrete_asbestos, 16)")
          and line(chem, 150, '"chem.ducrete").setup(150, 100)') and line(chem, 151, "new OreDictStack(FERRO.ingot()), new OreDictStack(KEY_SAND, 8)") and line(chem, 153, "new ItemStack(ModBlocks.ducrete_smooth, 8)")
          and line(chem, 155, '"chem.liquidconk").setup(100, 100)') and line(chem, 158, "new FluidStack(Fluids.CONCRETE, 16_000)"),
          "original ChemicalPlantRecipes.java:140-158: the four concrete recipes")
    powder = original("crafting/PowderRecipes.java")
    check(line(powder, 36, "new ItemStack(ModItems.powder_cement, 4), new Object[] { LIMESTONE.dust(), Items.clay_ball, Items.clay_ball, Items.clay_ball }"),
          "original PowderRecipes.java:36: limestone dust + 3 clay balls -> 4 cement powder (shapeless)")
    crafting = original("main/CraftingManager.java")
    check(line(crafting, 362, '"CC", "CC", \'C\', ModBlocks.concrete_smooth') and line(crafting, 364, "ModBlocks.brick_concrete, 4), new Object[] { \" C \", \"CBC\", \" C \", 'C', ModBlocks.concrete_smooth, 'B', Items.clay_ball }")
          and line(crafting, 365, "ModBlocks.brick_concrete, 4), new Object[] { \" C \", \"CBC\", \" C \", 'C', ModBlocks.concrete, 'B', Items.clay_ball }"),
          "original CraftingManager.java:362-365: concrete and the two brick recipes")
    shred = original("inventory/recipes/ShredderRecipes.java")
    check(line(shred, 153, "setRecipe(ModBlocks.concrete, new ItemStack(Blocks.gravel, 1))") and line(shred, 154, "setRecipe(ModBlocks.concrete_smooth, new ItemStack(Blocks.gravel, 1))")
          and line(shred, 175, "EnumStoneType.LIMESTONE), new ItemStack(ModItems.powder_limestone, 4)") and line(shred, 210, "setRecipe(ModBlocks.block_slag, new ItemStack(ModItems.powder_cement, 4))"),
          "original ShredderRecipes.java:153-154, 175, 210: the four shredder entries")
    oredict = original("inventory/OreDictManager.java")
    check(line(oredict, 501, "ANY_CONCRETE			.any(concrete, concrete_smooth, concrete_asbestos, ducrete, ducrete_smooth);"), "original OreDictManager.java:501: ANY_CONCRETE (before the coloured concretes)")
    blocks = original("blocks/ModBlocks.java")
    check(line(blocks, 1495, 'concrete_smooth = new BlockNoSpawn(Material.rock)') and line(blocks, 1495, ".setHardness(15.0F).setResistance(140.0F)") and line(blocks, 1498, ".setHardness(15.0F).setResistance(140.0F)")
          and line(blocks, 1499, "concrete_asbestos") and line(blocks, 1499, ".setHardness(15.0F).setResistance(150.0F)"), "original ModBlocks.java:1495-1499: concrete and smooth concrete 15 / 140, asbestos concrete 15 / 150")
    en_lang = {
        "ass.analogAlt": "Simple Analog Circuit", "ass.factorioChip": "Minimalist Circuits", "ass.atomicClockAlt": "Caesium Atomic Clock", "item.blueprint_folder.name": "Blueprint Booklet",
    }
    wrong = {k: original_lang_line(k) for k, v in en_lang.items() if original_lang_line(k) != v}
    check(not wrong, f"the original en_US.lang texts of the four upstream keys: {wrong}")


# ---- main --------------------------------------------------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 13A transcript: {log}", flush=True)
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

    def refuse_shadowing(stubs, production, world):
        overlap = sorted(set(stubs) & set(production))
        if overlap:
            raise SystemExit(f"Production sources shadowed by stand-ins in the {world} world: {overlap}")

    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nbaseline: git {BASELINE_COMMIT} (package goal13a.head)\n"
                     "machine world production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))

    shredder_facts = recipe_facts = None

    # ---- Shredder world (section 8s) ----
    if only in (None, "shredder"):
        head_shredder = baseline(f"src/main/java/{SHREDDER}", "com.hbm.inventory.recipes")
        shredder_fixture = (FIXTURE / SHREDDER_FIXTURE).read_text(encoding="utf-8")
        sstubs = shredder_stubs(SOURCE, head_shredder, shredder_fixture)
        refuse_shadowing(sstubs, SHREDDER_PRODUCTION, "shredder")
        sstubs["goal13a/head/ShredderRecipes.java"] = head_shredder
        shredder = run_dir / "shredder"
        ssources, sclasses = write_sources(shredder, sstubs, [SOURCE / p for p in SHREDDER_PRODUCTION] + [FIXTURE / SHREDDER_FIXTURE])
        run("Compile the Goal 13A shredder world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                    "-cp", str(GSON), "-d", str(sclasses), f"@{ssources}"])
        config = shredder / "scratch-config"
        config.mkdir()
        shredder_facts_file = shredder / "facts.json"
        run("Run Goal 13A shredder world (section 8s)",
            [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{sclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal13AShredderRegression", str(config), str(shredder_facts_file)],
            stage_failure_ok=True)
        if shredder_facts_file.is_file():
            shredder_facts = json.loads(shredder_facts_file.read_text(encoding="utf-8"))

    # ---- Recipe world (sections 3, 8c) ----
    if only in (None, "recipe"):
        head_chem = baseline(f"src/main/java/{CHEM}", "com.hbm.inventory.recipes")
        head_assembly = baseline(f"src/main/java/{ASSEMBLY}", "com.hbm.inventory.recipes")
        recipe_fixture = (FIXTURE / RECIPE_FIXTURE).read_text(encoding="utf-8")
        rstubs = recipe_stubs(SOURCE, [recipe_fixture])
        refuse_shadowing(rstubs, RECIPE_PRODUCTION, "recipe")
        rstubs["goal13a/head/ChemicalPlantRecipes.java"] = head_chem
        rstubs["goal13a/head/AssemblyMachineRecipes.java"] = head_assembly
        recipes = run_dir / "recipes"
        rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in RECIPE_PRODUCTION] + [FIXTURE / RECIPE_FIXTURE])
        run("Compile the Goal 13A recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                  "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
        templates = recipes / "templates"
        run("Run Goal 13A recipe world (sections 3, 8c)",
            [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal13ARecipeRegression", str(templates)],
            stage_failure_ok=True)
        if (templates / "chem-concrete.json").is_file():
            recipe_facts = json.loads((templates / "chem-concrete.json").read_text(encoding="utf-8"))

    # ---- Machine world (sections 1, 2, 4, 6, 7, 9) ----
    if only in (None, "machine"):
        with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
            vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
        head_anvil = baseline(f"src/main/java/{ANVIL}", "com.hbm.inventory.recipes.anvil")
        fixture_texts = [head_anvil] + [(FIXTURE / p).read_text(encoding="utf-8") for p in FIXTURES]
        stubs = build_stubs(SOURCE, fixture_texts, vanilla_tags, NEOFORGE_SOURCES)
        refuse_shadowing(stubs, PRODUCTION, "machine")
        stubs["goal13a/head/AnvilRecipes.java"] = head_anvil
        machine = run_dir / "machine"
        sources, classes = write_sources(machine, stubs, [SOURCE / p for p in PRODUCTION] + [FIXTURE11A / p for p in FIXTURES11A] + [FIXTURE / p for p in FIXTURES])
        plastic = read_json(GENERATED / "data/ntm/tags/item/ingots_plastic.json")["values"]
        steel = read_json(GENERATED / "data/c/tags/item/plates/steel.json")["values"]
        run("Compile the Goal 13A machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn", "-d", str(classes), f"@{sources}"])
        exported = run_dir / "machine-out"
        run("Run Goal 13A machine world (sections 1, 2, 4, 6, 7, 9)",
            [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal13ARegression", ",".join(plastic), ",".join(steel), str(exported)],
            stage_failure_ok=True)

    if only is not None:
        raise SystemExit(f"--only {only}: partial run, failed stages {failed}")

    sections = Sections()
    sections.run("1t. blueprint items, models and registration", items_text)
    sections.run("3p. registered names", registered_ids)
    sections.run("4j. blueprint chest loot, worldgen and registration", chest_text)
    sections.run("5. meteorite treasure", meteorite)
    sections.run("6t. anvil source", anvil_source)
    sections.run("7t. heater sound, description and source", heater_text)
    if shredder_facts is not None and recipe_facts is not None:
        sections.run("8t. concrete chain", lambda check: concrete_text(check, shredder_facts, recipe_facts))
    else:
        print("AssertionError in 8t. concrete chain after 0 passed checks: the shredder or recipe world wrote no facts", flush=True)
        sections.failures.append("8t. concrete chain: no facts")
    sections.run("13t. original references", references)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 13A Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 13A regression failed: {failed}")


if __name__ == "__main__":
    main()
