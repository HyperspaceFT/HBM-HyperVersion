"""Goal 13B regression: the silicon billet (item, recipes, press entry), the burnt electrode smelting recipes, the electrode wear component,
the arc furnace (block, multiblock, block entity, menu, recipe table) and the assembler recipes ass.chip and ass.arcfurnace, with the whole
chain sand -> arc furnace -> silicon nuggets -> silicon billet -> press -> printed silicon wafer -> ass.chip -> microchip -> soldering
station -> integrated circuit board.

Two Java worlds compile real production classes against isolated stand-ins (see goal13b_regression/README.md):

* the recipe world (the Goal 13A recipe world: the Goal 12B / 11D loader world with real Gson, the production SerializableRecipe,
  GenericRecipes, GenericRecipe and tables, plus the production ArcFurnaceRecipes and PressRecipes) runs sections 3b, 4, 6b and 7r in
  com.hbm.inventory.recipes.loader.Goal13BRecipeRegression, with AssemblyMachineRecipes and PressRecipes as they were after Goal 13A
  (build/migration/goal13b/base-g13a, package goal13b.base) for the comparisons;
* the machine world (goal13b_regression/stubs.py: the Goal 13A machine world plus the production MachineArcFurnaceBlock,
  MachineArcFurnaceBlockEntity, MachineArcFurnaceMenu, ArcElectrodeItem and ArcFurnaceRecipes) runs sections 3m, 5, 5w, 5l, 5e, 9m, 6 and
  7m in com.hbm.blockentity.machine.Goal13BRegression.

The Python sections read source text, the generated JSON and the original; section 8t joins the facts the Java worlds wrote into the whole
chain. Every section reports "N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the run fails at the end.
Lines starting with "info:" are observations, not checks.
"""

from pathlib import Path
import hashlib
import json
import re
import sys
import uuid
import zipfile

from goal13b_regression.stubs import GOAL13B_RECIPE_SOURCES, GOAL13B_SOURCES, build_stubs, recipe_stubs
from verify_goal10c import Sections, jdk
from verify_goal13a import PRODUCTION as GOAL13A_PRODUCTION, RECIPE_PRODUCTION as GOAL13A_RECIPE_PRODUCTION
from verify_goal3c_recipes import GSON
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
ORIGINAL_ASSETS = ORIGINAL_ROOT / "src/main/resources/assets/hbm"
FIXTURE = Path(__file__).with_name("goal13b_regression")
FIXTURE11A = Path(__file__).with_name("goal11a_regression")
FIXTURE12A = Path(__file__).with_name("goal12a_regression")
OUTPUT = ROOT / "build/migration/goal13b/regression"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
# The post-Goal 13A copies of the sources the Goal 13B change edits again (Goal 13A is uncommitted work on top of 12f38317, so git has no such
# state): byte copies of the Goal 13A final source tree, checked against the stamp taken after Goal 13A.
BASE_ROOT = ROOT / "build/migration/goal13b/base-g13a/java"
BEFORE_STAMP = ROOT / "build/migration/goal13b/stamp-before-g13b.json"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
PRESS = "com/hbm/inventory/recipes/PressRecipes.java"
BASE_FILES = (ASSEMBLY, PRESS)
# Not compiled: the datagen providers (the sections read their text and the generated JSON), the registries (NtmItems, NtmBlocks, NtmBlockEntityTypes,
# NtmMenuTypes, NtmCreativeTabs: text; the worlds use stand-in registries), the renderer, the screen and the JEI handler (client side; text), ClientProxy,
# CommonEvents and ResourceManager (text).
PRODUCTION = tuple(dict.fromkeys(list(GOAL13A_PRODUCTION) + list(GOAL13B_SOURCES)))
FIXTURES = (
    "com/hbm/blocks/machine/Goal13BBlockAccess.java",
    "com/hbm/blockentity/machine/Goal13BRegression.java",
)
FIXTURES11A = ("com/hbm/blocks/Goal11ABlockAccess.java",)
FIXTURES12A = ("com/hbm/blockentity/Goal12AProxyAccess.java",)
RECIPE_PRODUCTION = tuple(dict.fromkeys(list(GOAL13A_RECIPE_PRODUCTION) + list(GOAL13B_RECIPE_SOURCES)))
RECIPE_FIXTURE = "com/hbm/inventory/recipes/loader/Goal13BRecipeRegression.java"
SILICON_RECIPES = {
    "billet_silicon_from_6_nugget_silicon": "misc", "nugget_silicon_from_billet_silicon": "misc", "ingot_silicon_from_3_billet_silicon": "misc", "billet_silicon_from_2_ingot_silicon": "misc",
}
SMELTING = {
    "arc_electrode_graphite_burnt_to_ingot_graphite": ("arc_electrode_graphite_burnt", "ingot_graphite"),
    "arc_electrode_lanthanium_burnt_to_ingot_lanthanium": ("arc_electrode_lanthanium_burnt", "ingot_lanthanium"),
    "arc_electrode_desh_burnt_to_ingot_desh": ("arc_electrode_desh_burnt", "ingot_desh"),
    "arc_electrode_saturnite_burnt_to_ingot_saturnite": ("arc_electrode_saturnite_burnt", "ingot_saturnite"),
}


def base_text(path, package=None, target="goal13b.base"):
    """A post-Goal 13A production source (base-g13a), checked against the post-Goal 13A stamp; moved to the package `target` when `package` is given, so that it
    still sees its own package's classes."""
    data = (BASE_ROOT / path).read_bytes()
    stamp = json.loads(BEFORE_STAMP.read_text(encoding="utf-8"))["inputs"]
    digest = hashlib.sha256(data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")).hexdigest()
    if stamp.get("src/main/java/" + path) != digest:
        raise SystemExit(f"the post-Goal 13A copy of {path} is not the file the post-Goal 13A stamp records")
    text = data.decode("utf-8").replace("\r\n", "\n")
    if package is None:
        return text
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"base package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def java(path):
    """A production source under SOURCE (the mutation check points SOURCE at a mutated copy)."""
    return (SOURCE / "com/hbm" / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def original(path):
    return (ORIGINAL / path).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")


def original_lang_line(key, file="en_US.lang"):
    path = ORIGINAL_ASSETS / "lang" / file
    for entry in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if entry.startswith(key + "="):
            return entry.split("=", 1)[1]
    return None


def line(lines, number, text):
    """Whether the original line `number` (1-based) contains `text`."""
    return 0 < number <= len(lines) and text in lines[number - 1]


def recipe(name):
    return read_json(GENERATED / f"data/hbmsntm/recipe/{name}.json")


def registered(source_text, constant):
    """The registry name NtmItems / NtmBlocks gives a constant: `CONST = ... register...("name"`."""
    match = re.search(r"\b" + constant + r"\s*=\s*[\w.]+\(\s*\"([a-z0-9_]+)\"", source_text)
    return match.group(1) if match else None


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


def sha(data):
    return hashlib.sha256(data).hexdigest()


# ---- Python section 1t: the silicon billet --------------------------------------------------------------------------------------

def silicon_billet(check):
    items = java("items/NtmItems.java")
    check('BILLET_SILICON = ITEMS.register("billet_silicon", () -> new Item(new Item.Properties()))' in items, "NtmItems registers the plain item hbmsntm:billet_silicon")
    check(registered(items, "NUGGET_SILICON") == "nugget_silicon" and registered(items, "INGOT_SILICON") == "ingot_silicon",
          "the nugget and the ingot it converts with are hbmsntm:nugget_silicon and hbmsntm:ingot_silicon")
    tabs = java("inventory/NtmCreativeTabs.java")
    check("output.accept(NtmItems.NUGGET_SILICON.get());\n                        output.accept(NtmItems.BILLET_SILICON.get());" in tabs,
          "the parts tab lists the silicon wafer right after the silicon nugget")
    model = read_json(GENERATED / "assets/hbmsntm/models/item/billet_silicon.json")
    check(model == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/billet_silicon"}}, f"models/item/billet_silicon.json is a flat item with the texture item/billet_silicon: {model}")
    texture = RESOURCES / "assets/hbmsntm/textures/item/billet_silicon.png"
    check(texture.read_bytes() == (ORIGINAL_ASSETS / "textures/items/billet_silicon.png").read_bytes(), "textures/item/billet_silicon.png is byte-identical to the original textures/items/billet_silicon.png")
    # The four recipes of the original addBillet (MineralRecipes.java:549-563), as the generated JSON.
    six = recipe("billet_silicon_from_6_nugget_silicon")
    check(six.get("type") == "minecraft:crafting_shaped" and six.get("pattern") == ["nnn", "nnn"] and six.get("key") == {"n": {"item": "hbmsntm:nugget_silicon"}}
          and six.get("result") == {"count": 1, "id": "hbmsntm:billet_silicon"}
          and sum(row.count("n") for row in six["pattern"]) == 6,
          f"6 nuggets (3 x 2) -> 1 billet (original addBillet: \"###\", \"###\"): {six}")
    back = recipe("nugget_silicon_from_billet_silicon")
    check(back.get("type") == "minecraft:crafting_shapeless" and back.get("ingredients") == [{"item": "hbmsntm:billet_silicon"}] and back.get("result") == {"count": 6, "id": "hbmsntm:nugget_silicon"},
          f"1 billet -> 6 nuggets (original addShapelessRecipe(new ItemStack(nugget, 6), billet)): {back}")
    ingot = recipe("ingot_silicon_from_3_billet_silicon")
    check(ingot.get("type") == "minecraft:crafting_shapeless" and ingot.get("ingredients") == [{"item": "hbmsntm:billet_silicon"}] * 3 and ingot.get("result") == {"count": 2, "id": "hbmsntm:ingot_silicon"},
          f"3 billets -> 2 ingots (original addBilletToIngot: three billets, ingot x 2): {ingot}")
    billets = recipe("billet_silicon_from_2_ingot_silicon")
    check(billets.get("type") == "minecraft:crafting_shaped" and billets.get("pattern") == ["XX"] and billets.get("key") == {"X": {"item": "hbmsntm:ingot_silicon"}}
          and billets.get("result") == {"count": 3, "id": "hbmsntm:billet_silicon"},
          f"2 ingots -> 3 billets (original addRecipe(new ItemStack(billet, 3), \"##\", ingot)): {billets}")
    for name, folder in SILICON_RECIPES.items():
        advancement = read_json(GENERATED / f"data/hbmsntm/advancement/recipes/{folder}/{name}.json")
        check(advancement.get("rewards") == {"recipes": [f"hbmsntm:{name}"]}, f"the advancement for {name} unlocks the recipe")
    check(set(recipe(n)["category"] for n in SILICON_RECIPES) == {"misc"}, "the four recipes are in the misc recipe book category, as the other billets")
    # The existing billets are generated by the same helper: the silicon recipes have exactly their shape (names aside).
    zirconium = {n: recipe(n) for n in ("billet_zirconium_from_6_nugget_zirconium", "nugget_zirconium_from_billet_zirconium", "ingot_zirconium_from_3_billet_zirconium", "billet_zirconium_from_2_ingot_zirconium")
                 if (GENERATED / f"data/hbmsntm/recipe/{n}.json").is_file()}
    swapped = {n.replace("zirconium", "silicon"): json.loads(json.dumps(r).replace("zirconium", "silicon")) for n, r in zirconium.items()}
    check(len(zirconium) == 4 and all(swapped[n] == recipe(n) for n in SILICON_RECIPES), f"the silicon recipes are the zirconium billet recipes with the material swapped: {sorted(zirconium)}")
    provider = java("datagen/NtmRecipeProvider.java")
    check("addBilletRecipe(recipeOutput, NtmItems.BILLET_SILICON.get(), NtmItems.NUGGET_SILICON.get(), NtmItems.INGOT_SILICON.get());" in provider,
          "NtmRecipeProvider generates the silicon billet recipes from the silicon billet, nugget and ingot")
    lang = java("datagen/NtmLanguageProvider.java")
    en = read_json(GENERATED / "assets/hbmsntm/lang/en_us.json")
    check('this.add("item.hbmsntm.billet_silicon", "Silicon Wafer");' in lang and en.get("item.hbmsntm.billet_silicon") == "Silicon Wafer"
          and original_lang_line("item.billet_silicon.name") == "Silicon Wafer",
          "item.hbmsntm.billet_silicon is Silicon Wafer in the provider, en_us.json and the original en_US.lang")
    check('this.add(NtmItems.CIRCUIT_MICROCHIP, "Microchip");' in lang and "Microschip" not in lang and en.get("item.hbmsntm.circuit_microchip") == "Microchip"
          and original_lang_line("item.circuit.chip.name") == "Microchip",
          "the microchip is spelled Microchip in the provider and en_us.json, as in the original (B11)")


# ---- Python section 2t: the burnt electrode smelting recipes ---------------------------------------------------------------------

def smelting(check):
    for name, (burnt, ingot) in SMELTING.items():
        r = recipe(name)
        check(r.get("type") == "minecraft:smelting" and r.get("ingredient") == {"item": f"hbmsntm:{burnt}"} and r.get("result") == {"count": 1, "id": f"hbmsntm:{ingot}"}
              and r.get("experience") == 3.0 and r.get("cookingtime") == 200 and r.get("category") == "misc",
              f"{burnt} smelts into 1 {ingot}, 3.0 experience, 200 ticks (original SmeltingRecipes.java:112-115): {r}")
        advancement = read_json(GENERATED / f"data/hbmsntm/advancement/recipes/misc/{name}.json")
        check(advancement.get("rewards") == {"recipes": [f"hbmsntm:{name}"]} and f"has_{burnt}" in advancement.get("criteria", {}), f"the advancement for {name} unlocks the recipe with the burnt electrode")
    provider = java("datagen/NtmRecipeProvider.java")
    body = method(provider, "private void registerBurntElectrodeSmeltingRecipes(RecipeOutput recipeOutput) {")
    pairs = re.findall(r"addBurntElectrodeSmelting\(recipeOutput, NtmItems\.(\w+)\.get\(\), NtmItems\.(\w+)\.get\(\)\);", body)
    check(pairs == [(b.upper(), i.upper()) for b, i in SMELTING.values()], f"NtmRecipeProvider smelts the four burnt electrodes into their ingots in that order: {pairs}")
    helper = method(provider, "private void addBurntElectrodeSmelting(RecipeOutput recipeOutput, ItemLike inputItem, ItemLike outputItem) {")
    check("SimpleCookingRecipeBuilder.smelting(Ingredient.of(input), RecipeCategory.MISC, output, 3.0F, 200)" in helper, "the provider helper uses 3.0 experience and 200 ticks")
    check("registerBurntElectrodeSmeltingRecipes(recipeOutput);" in provider, "registerBurntElectrodeSmeltingRecipes is called")
    items = java("items/NtmItems.java")
    for constant in ("ARC_ELECTRODE_GRAPHITE_BURNT", "ARC_ELECTRODE_LANTHANIUM_BURNT", "ARC_ELECTRODE_DESH_BURNT", "ARC_ELECTRODE_SATURNITE_BURNT"):
        check(f'{constant} = ITEMS.register("{constant.lower()}", () -> new Item(new Item.Properties()))' in items, f"{constant} is a plain item with the default stack size (the original burnt electrode is not stack size 1)")


# ---- Python section 3p: the registered names of the items and blocks the Java worlds name ------------------------------------------

def registered_ids(check):
    items = java("items/NtmItems.java")
    blocks = java("blocks/NtmBlocks.java")
    wanted = {
        "NUGGET_SILICON": "nugget_silicon", "BILLET_SILICON": "billet_silicon", "INGOT_SILICON": "ingot_silicon", "CIRCUIT_PRINTED_SILICON_WAFER": "circuit_printed_silicon_wafer",
        "CIRCUIT_MICROCHIP": "circuit_microchip", "CIRCUIT_INTEGRATED_BOARD": "circuit_integrated_board", "CIRCUIT_PRINTED_BOARD": "circuit_printed_board",
        "CIRCUIT_ANALOG_BOARD": "circuit_analog_board", "PLATE_POLYMER": "plate_polymer", "WIRE_GOLD": "wire_gold", "WIRE_LEAD": "wire_lead", "INGOT_FIREBRICK": "ingot_firebrick",
        "POWDER_QUARTZ": "powder_quartz", "INGOT_FIBERGLASS": "ingot_fiberglass", "INGOT_ASBESTOS": "ingot_asbestos", "POWDER_ASBESTOS": "powder_asbestos", "POWDER_BORAX": "powder_borax",
        "POWDER_BORON_TINY": "powder_boron_tiny", "ARC_ELECTRODE_GRAPHITE": "arc_electrode_graphite", "ARC_ELECTRODE_LANTHANIUM": "arc_electrode_lanthanium",
        "ARC_ELECTRODE_DESH": "arc_electrode_desh", "ARC_ELECTRODE_SATURNITE": "arc_electrode_saturnite", "ARC_ELECTRODE_GRAPHITE_BURNT": "arc_electrode_graphite_burnt",
        "ARC_ELECTRODE_LANTHANIUM_BURNT": "arc_electrode_lanthanium_burnt", "ARC_ELECTRODE_DESH_BURNT": "arc_electrode_desh_burnt", "ARC_ELECTRODE_SATURNITE_BURNT": "arc_electrode_saturnite_burnt",
        "CAST_PLATE": "cast_plate", "COKE_COAL": "coke_coal", "INGOT_GRAPHITE": "ingot_graphite",
    }
    wrong = {c: registered(items, c) for c, n in wanted.items() if registered(items, c) != n}
    check(not wrong, "the NtmItems constants the Java worlds name resolve to the registry names the expected ids use (the stand-in registries derive ids from the constants): " + str(wrong))
    block_names = {"MACHINE_ARC_FURNACE": "machine_arc_furnace", "BLOCK_FIBERGLASS": "block_fiberglass", "BLOCK_ASBESTOS": "block_asbestos", "TRANSFORMER": "transformer"}
    wrong = {c: registered(blocks, c) for c, n in block_names.items() if registered(blocks, c) != n}
    check(not wrong, f"the NtmBlocks constants resolve to the expected names: {wrong}")
    check(re.search(r"CIRCUIT_PRINTED_SILICON_WAFER\s*=\s*ITEMS\.register", items) is not None and "castPlateIngredient(CastPlateItem.Type type, int count)" in items,
          "the printed silicon wafer exists and NtmItems.castPlateIngredient(type, count) builds the cast plate ingredient with the type's ordinal as the meta")


# ---- Python section 4t: electrodes, block, registration, datagen, language ---------------------------------------------------------

def furnace_text(check):
    items = java("items/NtmItems.java")
    found = re.findall(r'(ARC_ELECTRODE_[A-Z]+) = ITEMS\.register\("(arc_electrode_[a-z]+)", \(\) -> new ArcElectrodeItem\(new Item\.Properties\(\)\.stacksTo\((\d+)\), (\d+), NtmItems\.(\w+)\)\)', items)
    check([(c, n, int(s), int(m), b) for c, n, s, m, b in found] == [
        ("ARC_ELECTRODE_GRAPHITE", "arc_electrode_graphite", 1, 10, "ARC_ELECTRODE_GRAPHITE_BURNT"), ("ARC_ELECTRODE_LANTHANIUM", "arc_electrode_lanthanium", 1, 100, "ARC_ELECTRODE_LANTHANIUM_BURNT"),
        ("ARC_ELECTRODE_DESH", "arc_electrode_desh", 1, 500, "ARC_ELECTRODE_DESH_BURNT"), ("ARC_ELECTRODE_SATURNITE", "arc_electrode_saturnite", 1, 1500, "ARC_ELECTRODE_SATURNITE_BURNT")],
          f"NtmItems registers the four electrodes as ArcElectrodeItem with stack size 1, maxima 10 / 100 / 500 / 1500 and their burnt items (original ItemArcElectrode.java:14, :48-52): {found}")
    components = java("items/component/NtmDataComponents.java")
    check('ARC_ELECTRODE_DURABILITY = DATA_COMPONENT_TYPES.register("arc_electrode_durability", () -> DataComponentType.<Integer>builder().persistent(Codec.INT).networkSynchronized(ByteBufCodecs.INT).build());' in components,
          "NtmDataComponents registers arc_electrode_durability as a persistent, network-synchronised int")
    item = java("items/machine/ArcElectrodeItem.java")
    check("return durability >= getMaxDurability(stack);" in item and "stack.set(NtmDataComponents.ARC_ELECTRODE_DURABILITY, durability);" in item and "stack.getOrDefault(NtmDataComponents.ARC_ELECTRODE_DURABILITY, 0)" in item,
          "ArcElectrodeItem.damage adds one, stores it in the component and returns durability >= maximum")
    blocks = java("blocks/NtmBlocks.java")
    match = re.search(r'MACHINE_ARC_FURNACE = register\("machine_arc_furnace", \(\) -> new MachineArcFurnaceBlock\(BlockBehaviour\.Properties\.of\(\)(.*?)\)\);', blocks)
    props = match.group(1) if match else ""
    check(match is not None and ".noOcclusion()" in props and ".requiresCorrectToolForDrops()" in props and ".sound(SoundType.METAL)" in props,
          f"NtmBlocks registers hbmsntm:machine_arc_furnace as a MachineArcFurnaceBlock (no occlusion, metal, a correct tool for drops): {props}")
    lines = original("blocks/ModBlocks.java")
    check(line(lines, 1824, 'machine_arc_furnace = new MachineArcFurnaceLarge().setBlockName("machine_arc_furnace").setHardness(5.0F).setResistance(10.0F)'),
          "original ModBlocks.java:1824: the arc furnace is a MachineArcFurnaceLarge with hardness 5 and resistance 10 (NEO's block follows its other multiblock machines with 0.6 / 10, as its source comment says)")
    types = java("blockentity/NtmBlockEntityTypes.java")
    check('MACHINE_ARC_FURNACE = BLOCK_ENTITY_TYPES.register(\n            "machine_arc_furnace",\n            () -> BlockEntityType.Builder.of(\n                            MachineArcFurnaceBlockEntity::new,\n                            NtmBlocks.MACHINE_ARC_FURNACE.get())'
          in types, "NtmBlockEntityTypes registers machine_arc_furnace for the block entity and the block")
    menus = java("inventory/NtmMenuTypes.java")
    check('MACHINE_ARC_FURNACE = reg("machine_arc_furnace", MachineArcFurnaceMenu::new);' in menus, "NtmMenuTypes registers machine_arc_furnace")
    events = java("main/CommonEvents.java")
    proxy = java("main/ClientProxy.java")
    manager = java("main/ResourceManager.java")
    check("event.register(NtmMenuTypes.MACHINE_ARC_FURNACE.get(), MachineArcFurnaceScreen::new);" in events
          and "BlockEntityRenderers.register(NtmBlockEntityTypes.MACHINE_ARC_FURNACE.get(), new RenderArcFurnace());" in proxy
          and 'arc_furnace = new HFRWavefrontObject("models/obj/machines/arc_furnace.obj").asVBO();' in manager
          and 'ARC_FURNACE_TEX = NuclearTechMod.withDefaultNamespace("textures/models/machines/arc_furnace.png");' in manager,
          "the screen, the renderer, the model and its texture are registered (CommonEvents, ClientProxy, ResourceManager)")
    jei = java("handler/jei/NtmJeiPlugin.java")
    check("new ArcFurnaceRecipeHandler(guiHelper)," in jei and "registration.addRecipes(ArcFurnaceRecipeHandler.RECIPE_TYPE, ArcFurnaceRecipes.recipes);" in jei
          and "NtmBlocks.MACHINE_ARC_FURNACE.asItem()," in jei, "the JEI plugin registers the arc furnace category, its recipes and its catalyst")
    tabs = java("inventory/NtmCreativeTabs.java")
    check("output.accept(NtmBlocks.MACHINE_ARC_FURNACE);" in tabs, "the machine tab lists the arc furnace")
    handlers = java("inventory/recipes/loader/SerializableRecipe.java")
    start = handlers.index("public static void registerAllHandlers() {")
    adds = re.findall(r"recipeHandlers\.add\((.*?)\);", handlers[start:handlers.index("}", start)])
    check(adds.count("new ArcFurnaceRecipes()") == 1 and adds.index("new ArcFurnaceRecipes()") == adds.index("new CrackingRecipes()") + 1 and adds.index("new ArcFurnaceRecipes()") < adds.index("AssemblyMachineRecipes.INSTANCE"),
          f"registerAllHandlers adds ArcFurnaceRecipes right after CrackingRecipes and above the generic tables: {adds}")
    # Generated resources.
    blockstate = read_json(GENERATED / "assets/hbmsntm/blockstates/machine_arc_furnace.json")
    block_model = read_json(GENERATED / "assets/hbmsntm/models/block/machine_arc_furnace_particle.json")
    item_model = read_json(GENERATED / "assets/hbmsntm/models/item/machine_arc_furnace.json")
    check(blockstate == {"variants": {"": {"model": "hbmsntm:block/machine_arc_furnace_particle"}}} and block_model == {"textures": {"particle": "hbmsntm:block/block_steel"}}
          and item_model == {"parent": "minecraft:builtin/entity", "gui_light": "side"},
          "the block state points at a particle-only model, the item is a builtin entity (both rendered by the block entity renderer, as the other multiblock machines)")
    check((RESOURCES / "assets/hbmsntm/textures/block/block_steel.png").is_file(), "the particle texture block/block_steel exists")
    loot = read_json(GENERATED / "data/hbmsntm/loot_table/blocks/machine_arc_furnace.json")
    pool = loot["pools"][0]
    check(loot.get("type") == "minecraft:block" and len(loot["pools"]) == 1 and pool["rolls"] == 1.0 and pool["entries"] == [{"type": "minecraft:item", "name": "hbmsntm:machine_arc_furnace"}]
          and pool["conditions"] == [{"condition": "minecraft:survives_explosion"}], f"the loot table drops the arc furnace itself: {loot}")
    pickaxe = read_json(GENERATED / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    check(pickaxe.count("hbmsntm:machine_arc_furnace") == 1, "the arc furnace is in #minecraft:mineable/pickaxe once")
    # Language.
    lang = java("datagen/NtmLanguageProvider.java")
    en = read_json(GENERATED / "assets/hbmsntm/lang/en_us.json")
    check('this.add("block.hbmsntm.machine_arc_furnace", "Electric Arc Furnace");' in lang and en.get("block.hbmsntm.machine_arc_furnace") == "Electric Arc Furnace"
          and original_lang_line("tile.machine_arc_furnace.name") == "Electric Arc Furnace",
          "block.hbmsntm.machine_arc_furnace is Electric Arc Furnace (original tile.machine_arc_furnace.name)")
    check('this.add("container.machine_arc_furnace", "Arc Furnace");' in lang and en.get("container.machine_arc_furnace") == "Arc Furnace" and original_lang_line("container.machineArcFurnaceLarge") == "Arc Furnace"
          and 'Component.translatable("container.machine_arc_furnace")' in java("blockentity/machine/MachineArcFurnaceBlockEntity.java"),
          "container.machine_arc_furnace is Arc Furnace (original container.machineArcFurnaceLarge) and the block entity's default name")
    check('this.add("item.hbmsntm.arc_electrode.wear", "Wear: %s / %s");' in lang and en.get("item.hbmsntm.arc_electrode.wear") == "Wear: %s / %s"
          and '"item.hbmsntm.arc_electrode.wear", durability, this.maxDurability' in item, "the wear tooltip key exists in the provider, en_us.json and is used with the uses and the maximum")
    # The model: every part the renderer asks for exists in the imported OBJ.
    obj = (RESOURCES / "assets/hbmsntm/models/obj/machines/arc_furnace.obj").read_text(encoding="utf-8", errors="replace")
    groups = set(re.findall(r"^[og]\s+(\S+)", obj, re.M))
    needed = {"Furnace", "ContentsHot", "ContentsCold", "Lid", "Ring1", "Ring2", "Ring3", "Electrode1", "Electrode2", "Electrode3", "Electrode1Hot", "Electrode2Hot", "Electrode3Hot",
              "Electrode1Short", "Electrode2Short", "Electrode3Short", "Cable1", "Cable2", "Cable3"}
    renderer = java("render/blockentity/RenderArcFurnace.java")
    asked = set(re.findall(r'renderPart\("(\w+)"\)', renderer)) | {f"{n}{i}" for n in ("Ring", "Cable", "Electrode") for i in (1, 2, 3)} | {f"Electrode{i}{s}" for i in (1, 2, 3) for s in ("Hot", "Short")}
    check(needed <= groups and {p for p in asked if not p.startswith(("Ring", "Cable", "Electrode"))} <= groups, f"arc_furnace.obj holds the parts the renderer draws: missing {sorted(needed - groups)}")
    check('ResourceManager.arc_furnace.renderPart("Ring" + (i + 1))' in renderer and 'renderPart("Electrode" + (i + 1) + "Hot")' in renderer and 'renderPart("Electrode" + (i + 1) + "Short")' in renderer
          and 'renderPart("Cable" + (i + 1))' in renderer and "RenderContext.translate(0F, 2F * lift, 0F);" in renderer,
          "the renderer draws rings, hot / short electrodes and cables by index and lifts the lid by 2 x lid")
    # The screen.
    screen = java("inventory/screens/MachineArcFurnaceScreen.java")
    check("this.imageWidth = 176;" in screen and "this.imageHeight = 256;" in screen and "this.leftPos + 8, this.topPos + 36, 7, 70, this.be.getPower(), this.be.getMaxPower()" in screen
          and "this.leftPos + 7, this.topPos + 17, 190, 0, 18, 18" in screen and "this.topPos + 106 - p, 176, 70 - p, 7, p" in screen and "this.topPos + 106 - o, 183, 70 - o, PROGRESS_WIDTH, o" in screen
          and "PROGRESS_X = 17;" in screen and "PROGRESS_WIDTH = 7;" in screen and "PROGRESS_HEIGHT = 70;" in screen
          and "this.imageWidth / 2 - this.font.width(this.title) / 2, 6, 0xffffff" in screen and "8, this.imageHeight - 96 + 2, 4210752" in screen,
          "MachineArcFurnaceScreen: 176 x 256, the power bar (8, 36, 7 x 70) and its fill, the progress bar at x 17, the working lamp (7, 17), the white title and the inventory label of the original GUI")
    gui = (ORIGINAL / "inventory/gui/GUIMachineArcFurnaceLarge.java").read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")
    check(line(gui, 37, "this.xSize = 176;") and line(gui, 38, "this.ySize = 256;") and line(gui, 47, "guiLeft + 8, guiTop + 36, 7, 70") and line(gui, 65, "this.xSize / 2 - this.fontRendererObj.getStringWidth(name) / 2, 6, 0xffffff")
          and line(gui, 66, "8, this.ySize - 96 + 2, 4210752") and line(gui, 76, "guiLeft + 7, guiTop + 17, 190, 0, 18, 18") and line(gui, 79, "guiTop + 106 - p, 176, 70 - p, 7, p")
          and line(gui, 82, "guiLeft + 17, guiTop + 106 - o, 183, 70 - o, 7, o"), "original GUIMachineArcFurnaceLarge.java:37-38, 47, 65-66, 76, 79, 82: the numbers above")
    for name, original_name in (("assets/hbmsntm/models/obj/machines/arc_furnace.obj", "models/machines/arc_furnace.obj"), ("assets/hbmsntm/textures/models/machines/arc_furnace.png", "textures/models/machines/arc_furnace.png"),
                                ("assets/hbmsntm/textures/gui/processing/gui_arc_furnace.png", "textures/gui/processing/gui_arc_furnace.png")):
        check((RESOURCES / name).read_bytes() == (ORIGINAL_ASSETS / original_name).read_bytes(), f"{name} is byte-identical to the original {original_name}")


# ---- Python section 8t: the whole chain --------------------------------------------------------------------------------------------

def chain_text(check, recipe_facts, machine_facts):
    nugget = machine_facts["furnaceOutput"]
    check(nugget == recipe_facts["arc"][0] and machine_facts["furnaceOutputCount"] == recipe_facts["arc"][1] == 1,
          f"the arc furnace block entity and the arc furnace table agree: 1 sand -> {machine_facts['furnaceOutputCount']} x {nugget}")
    check(machine_facts["furnaceUpgrade3Nuggets"] == 16, "an upgrade-3 furnace turns 16 sand into 16 nuggets per run (the stack of 16)")
    six = recipe("billet_silicon_from_6_nugget_silicon")
    billet = six["result"]["id"]
    check(six["key"]["n"]["item"] == nugget and billet == recipe_facts["billet"] and six["result"]["count"] == 1,
          f"6 of the furnace's nuggets craft the billet the press takes: {nugget} x 6 -> {billet}")
    wafer = recipe_facts["press"]
    check(wafer == ["hbmsntm:circuit_printed_silicon_wafer", 1], f"the press makes the printed silicon wafer from the billet: {wafer}")
    inputs = recipe_facts["chipInputs"]
    check([wafer[0], 1] in inputs and recipe_facts["chip"] == ["hbmsntm:circuit_microchip", 1], f"ass.chip takes that wafer (with a polymer plate and a gold wire: {inputs}) and makes the microchip {recipe_facts['chip']}")
    check(recipe_facts["soldering"] == ["hbmsntm:circuit_integrated_board", 1], f"the soldering station makes the integrated circuit board from 4 microchips, 4 printed boards and 4 lead wires: {recipe_facts['soldering']}")
    # Every step has a survival source: the generated recipes, the press, the assemblers.
    back = recipe("nugget_silicon_from_billet_silicon")
    ingots = recipe("billet_silicon_from_2_ingot_silicon")
    check(back["result"]["count"] == 6 and ingots["result"]["count"] == 3, "the billet converts both ways with the ingot and the nugget (6 nuggets, 3 billets per 2 ingots)")
    sand = 6 * 4  # nuggets for four billets
    print(f"info: one integrated circuit board takes 4 microchips = 4 wafers = 4 billets = 24 nuggets = {sand} sand through the arc furnace "
          f"({sand // 16} runs at upgrade 3 with 16 sand, {sand} at upgrade 0 with 1)", flush=True)


# ---- Python section 13t: the original lines the Java fixtures transcribe -------------------------------------------------------------

def references(check):
    arc = original("tileentity/machine/TileEntityMachineArcFurnaceLarge.java")
    check(line(arc, 56, "public static final long maxPower = 2_500_000;") and line(arc, 80, "public int getMaxInputSize() {")
          and line(arc, 81, "return upgrade == 0 ? 1 : upgrade == 1 ? 4 : upgrade == 2 ? 8 : 16;"),
          "original TileEntityMachineArcFurnaceLarge.java:56, 80-81: maxPower 2,500,000 and the input sizes 1 / 4 / 8 / 16")
    check(line(arc, 108, "upgradeManager.checkSlots(this, slots, 4, 4);") and line(arc, 109, "this.upgrade = upgradeManager.getLevel(UpgradeType.SPEED);")
          and line(arc, 117, "this.power = Library.chargeTEFromItems(slots, 3, power, maxPower);") and line(arc, 120, "if(lid > 0) loadIngredients();")
          and line(arc, 127, "int consumption = (int) (1_000 * Math.pow(5, upgrade));"),
          "original :108-120, 127: the upgrade slot 4, the battery slot 3, loadIngredients while the lid is open, consumption 1,000 x 5^upgrade")
    check(line(arc, 129, "if(ingredients && electrodes && delay <= 0 && this.liquids.isEmpty()) {") and line(arc, 130, "if(lid > 0) {") and line(arc, 131, "lid -= 1F / (60F / (upgrade * 0.5 + 1));")
          and line(arc, 136, "if(power >= consumption) {") and line(arc, 137, "int duration = 400 / (upgrade * 2 + 1);") and line(arc, 138, "this.progress += 1F / duration;")
          and line(arc, 140, "this.power -= consumption;") and line(arc, 141, "if(this.progress >= 1F) {") and line(arc, 145, "this.delay = (int) (120 / (upgrade * 0.5 + 1));"),
          "original :129-145: the lid closes first, 400 / (2 x upgrade + 1) steps of 1 / duration, the power covers the consumption, the delay 120 / (0.5 x upgrade + 1)")
    check(line(arc, 151, "if(this.delay > 0) delay--;") and line(arc, 154, "lid += 1F / (60F / (upgrade * 0.5 + 1));") and line(arc, 159, "hasMaterial = ingredients;")
          and line(arc, 162, "this.decideElectrodeState();") and line(arc, 164, "if(!hasMaterial) hasMaterial = this.hasIngredients();") and line(arc, 187, "this.networkPackNT(150);"),
          "original :151-187: the delay runs down and the lid opens otherwise, hasMaterial, the electrode states, one sync pack of range 150 per tick")
    check(line(arc, 201, '"hbm:door.wgh_start", xCoord, yCoord, zCoord, this.getVolume(0.75F), 15F, 1.0F, 5)') and line(arc, 213, '"hbm:door.wgh_stop", this.getVolume(1), 1F)')
          and line(arc, 212, "if((lid == 1 || lid == 0) && lid != prevLid && !(this.prevLid == 0 && this.lid == 1)) {")
          and line(arc, 218, "NTMSounds.ELECTRIC_HUM_LOOP, xCoord, yCoord, zCoord, this.getVolume(1.5F), 15F, 0.75F, 5)") and line(arc, 241, 'data.setFloat("alphaMod", prevLid / lid);')
          and line(arc, 247, "this.lid < this.prevLid && this.lid > 0.5F && this.hasMaterial") and line(arc, 249, "if(worldObj.rand.nextInt(5) == 0) {") and line(arc, 255, 'flame.setInteger("maxAge", 50);'),
          "original :201-257: the client sounds, smoke and flames")
    check(line(arc, 272, "int recipeMax = this.liquidMode ? max : slots[q].getMaxStackSize() / recipe.solidOutput.stackSize;") and line(arc, 273, "max = Math.min(max, recipeMax);")
          and line(arc, 279, "int toMove = BobMathUtil.min(slots[i].getMaxStackSize() - slots[i].stackSize, slots[q].stackSize, max - slots[i].stackSize);")
          and line(arc, 291, "int toMove = Math.min(max, slots[q].stackSize);"), "original :263-301: the queue cap min(input size, max stack / output count), topping up started stacks, then the empty slots")
    check(line(arc, 307, "ModItems.arc_electrode_burnt) { this.electrodes[i] = this.ELECTRODE_DEPLETED; continue; }")
          and line(arc, 309, "if(this.isProgressing || ItemArcElectrode.getDurability(slots[i]) > 0) this.electrodes[i] = this.ELECTRODE_USED;")
          and line(arc, 310, "else this.electrodes[i] = this.ELECTRODE_FRESH;") and line(arc, 314, "this.electrodes[i] = this.ELECTRODE_NONE;"),
          "original :303-316: electrode states (burnt DEPLETED, progressing or worn USED, else FRESH, none NONE)")
    check(line(arc, 322, "ArcFurnaceRecipe recipe = ArcFurnaceRecipes.getOutput(slots[i], this.liquidMode);") and line(arc, 323, "if(recipe == null) continue;")
          and line(arc, 325, "if(!liquidMode && recipe.solidOutput != null) {") and line(arc, 326, "int amount = slots[i].stackSize;"),
          "original :318-326: process looks up the recipe of each grid stack and keeps its size")
    check(line(arc, 327, "slots[i] = recipe.solidOutput.copy();") and line(arc, 328, "slots[i].stackSize *= amount;") and line(arc, 350, "if(ItemArcElectrode.damage(slots[i])) {")
          and line(arc, 351, "slots[i] = new ItemStack(ModItems.arc_electrode_burnt, 1, slots[i].getItemDamage());"), "original :327-351: output stack x input count, every electrode damaged, burnt at the maximum")
    check(line(arc, 371, "if(slots[i] == null || slots[i].getItem() != ModItems.arc_electrode) return false;") and line(arc, 386, "if(slot < 3) return stack.getItem() == ModItems.arc_electrode;")
          and line(arc, 412, "if(slot < 3) return lid >= 1 && stack.getItem() != ModItems.arc_electrode;") and line(arc, 413, "if(slot > 4 && slot < 25) return lid > 0 && ArcFurnaceRecipes.getOutput(stack, this.liquidMode) == null;")
          and line(arc, 414, "if(slot >= 25) return ArcFurnaceRecipes.getOutput(stack, this.liquidMode) == null;"), "original :369-416: hasElectrodes and the slot rules")
    check(line(arc, 555, "PortDef.make(xCoord + dir.offsetX * 2 + rot.offsetX, yCoord, zCoord + dir.offsetZ * 2 + rot.offsetZ, dir),")
          and line(arc, 557, "PortDef.make(xCoord + rot.offsetX * 2 + dir.offsetX, yCoord, zCoord + rot.offsetZ * 2 + dir.offsetZ, rot),")
          and line(arc, 560, "PortDef.make(xCoord - rot.offsetX * 2 - dir.offsetX, yCoord, zCoord - rot.offsetZ * 2 - dir.offsetZ, rot.getOpposite())"), "original :554-561: the six ports")
    check(line(arc, 568, "super.serialize(buf);") and line(arc, 569, "buf.writeLong(power);") and line(arc, 572, "buf.writeBoolean(isProgressing);") and line(arc, 573, "buf.writeBoolean(liquidMode);")
          and line(arc, 576, "for(int i = 0; i < 3; i++) buf.writeByte(electrodes[i]);") and line(arc, 605, "if(syncLid != 0 && syncLid != 1) this.approachNum = 2;")
          and line(arc, 612, "this.power = nbt.getLong(\"power\");") and line(arc, 616, "this.delay = nbt.getInteger(\"delay\");"), "original :567-624: serialize (the liquid mode flag is not ported), the lid approach, the NBT keys")
    check(line(arc, 714, "public void provideInfo(UpgradeType type, int level, List<String> info, boolean extendedInfo) {") and line(arc, 717, '"-" + (100 - 100 / (level * 2 + 1)) + "%"')
          and line(arc, 718, '"+" + ((int) Math.pow(5, level) * 100 - 100) + "%"') and line(arc, 725, "upgrades.put(UpgradeType.SPEED, 3);"), "original :708-727: the upgrade info")
    electrode = original("items/machine/ItemArcElectrode.java")
    check(line(electrode, 14, "this.setMaxStackSize(1);") and line(electrode, 22, "public static boolean damage(ItemStack stack) {") and line(electrode, 30, "return durability >= getMaxDurability(stack);")
          and line(electrode, 40, "return getDurabilityForDisplay(stack) > 0D;") and line(electrode, 45, "return (double) getDurability(stack) / (double) getMaxDurability(stack);")
          and line(electrode, 49, "GRAPHITE(	10),") and line(electrode, 50, "LANTHANIUM(	100),") and line(electrode, 51, "DESH(		500),") and line(electrode, 52, "SATURNITE(	1500);"),
          "original ItemArcElectrode.java:14-52: stack size 1, damage, the bar, 10 / 100 / 500 / 1500")
    block = original("blocks/machine/MachineArcFurnaceLarge.java")
    check(line(block, 28, "if(meta >= 12) return new TileEntityMachineArcFurnaceLarge();") and line(block, 29, "if(meta >= 6) return new TileEntityProxyCombo().inventory().power();")
          and line(block, 35, "return new int[] {4, 0, 2, 2, 2, 2};") and line(block, 40, "return 2;") and line(block, 46, "new int[] {4, 0, 3, -2, 1, 1}") and line(block, 53, "new int[] {4, 0, 3, -2, 1, 1}")
          and line(block, 55, "ForgeDirection rot = dir.getRotation(ForgeDirection.UP);") and line(block, 59, "this.makeExtra(world, x + dir.offsetX * 2 + rot.offsetX, y, z + dir.offsetZ * 2 + rot.offsetZ);")
          and line(block, 64, "this.makeExtra(world, x - rot.offsetX * 2 - dir.offsetX, y, z - rot.offsetZ * 2 - dir.offsetZ);"), "original MachineArcFurnaceLarge.java:28-64: block entities by meta, dimensions, offset, the extra box, the six extras")
    container = original("inventory/container/ContainerMachineArcFurnaceLarge.java")
    check(line(container, 27, "this.addSlotToContainer(new SlotNonRetarded(tile, i, 62 + i * 18, 22));") and line(container, 29, "new Slot(tile, 3, 8, 108)") and line(container, 31, "new Slot(tile, 4, 152, 108)")
          and line(container, 33, "5 + j + i * 5, 44 + j * 18, 54 + i * 18") and line(container, 35, "new SlotNonRetarded(tile, i + 25, 44 + i * 18, 129)")
          and line(container, 39, "j + i * 9 + 9, 8 + j * 18, 174 + i * 18") and line(container, 44, "8 + i * 18, 232"),
          "original ContainerMachineArcFurnaceLarge.java:27-44: the slot layout (the battery and upgrade slots are plain slots upstream; NEO's menu validates them through canPlaceItem like the arc welder)")
    recipes = original("inventory/recipes/ArcFurnaceRecipes.java")
    check(line(recipes, 53, "new OreDictStack(KEY_SAND)") and line(recipes, 53, "nugget_silicon)") and line(recipes, 54, "Items.flint") and line(recipes, 54, "nugget_silicon, 4)") and line(recipes, 55, "QUARTZ.gem()")
          and line(recipes, 55, "nugget_silicon, 3)") and line(recipes, 56, "QUARTZ.dust()") and line(recipes, 57, "QUARTZ.block()") and line(recipes, 57, "nugget_silicon, 12)") and line(recipes, 58, "FIBER.ingot()")
          and line(recipes, 59, "FIBER.block()") and line(recipes, 59, "nugget_silicon, 40)") and line(recipes, 60, "ASBESTOS.ingot()") and line(recipes, 61, "ASBESTOS.dust()") and line(recipes, 62, "ASBESTOS.block()")
          and line(recipes, 62, "nugget_silicon, 40)") and line(recipes, 64, "ModBlocks.sand_mix, 1, EnumSandType.QUARTZ") and line(recipes, 65, "BORAX.dust()") and line(recipes, 65, "powder_boron_tiny, 3)"),
          "original ArcFurnaceRecipes.java:53-65: the solid defaults (sand_mix -> quartz glass at :64 is deferred)")
    check(line(recipes, 135, "public static void register(AStack input, ArcFurnaceRecipe output) {") and line(recipes, 140, "if(output.solidOutput != null) if(occupiedSolid.contains(compStack)) return;")
          and line(recipes, 143, "recipeList.add(new Pair(input, output));") and line(recipes, 147, "if(output.solidOutput != null) occupiedSolid.add(compStack);"),
          "original ArcFurnaceRecipes.java:135-150: an occupied solid input rejects the recipe, otherwise the recipe and its inputs are recorded")
    assembly = original("inventory/recipes/AssemblyMachineRecipes.java")
    check(line(assembly, 126, "if(!GeneralConfig.enable528) {") and line(assembly, 127, 'new GenericRecipe("ass.chip").setup(50, 250)') and line(assembly, 127, "EnumCircuitType.CHIP")
          and line(assembly, 128, "new ComparableStack(ModItems.plate_polymer), new ComparableStack(ModItems.circuit, 1, EnumCircuitType.SILICON), new OreDictStack(GOLD.wireFine())")
          and line(assembly, 286, 'new GenericRecipe("ass.arcfurnace").setup(200, 100)') and line(assembly, 287, "new OreDictStack(ANY_CONCRETE.any(), 12), new OreDictStack(ANY_PLASTIC.ingot(), 8), new ComparableStack(ModItems.ingot_firebrick, 16),new OreDictStack(STEEL.plateCast(), 8), new ComparableStack(ModBlocks.machine_transformer, 1), new ComparableStack(ModItems.circuit, 1, EnumCircuitType.ANALOG.ordinal())"),
          "original AssemblyMachineRecipes.java:126-128, 286-288: ass.chip inside the !enable528 block, ass.arcfurnace outside any flag")
    press = original("inventory/recipes/PressRecipes.java")
    check(line(press, 99, "makeRecipe(StampType.CIRCUIT, new OreDictStack(SI.billet()),") and line(press, 99, "EnumCircuitType.SILICON"), "original PressRecipes.java:99: the silicon billet presses to the silicon circuit with the circuit stamp")
    mineral = original("crafting/MineralRecipes.java")
    check(line(mineral, 154, "addBillet(ModItems.billet_silicon,") and line(mineral, 154, "ModItems.ingot_silicon") and line(mineral, 154, "ModItems.nugget_silicon")
          and line(mineral, 550, 'GameRegistry.addRecipe(new ItemStack(billet), new Object[] { "###", "###", \'#\', nugget });') and line(mineral, 551, "GameRegistry.addShapelessRecipe(new ItemStack(nugget, 6), new Object[] { billet });")
          and line(mineral, 561, "GameRegistry.addShapelessRecipe(new ItemStack(ingot, 2), new Object[] { billet, billet, billet });")
          and line(mineral, 562, 'GameRegistry.addRecipe(new ItemStack(billet, 3), new Object[] { "##", \'#\', ingot });'), "original MineralRecipes.java:154, 549-563: the silicon billet conversions")
    smelting_lines = original("crafting/SmeltingRecipes.java")
    check(all(line(smelting_lines, 112 + i, f"EnumElectrodeType.{t}), new ItemStack(ModItems.ingot_{m}), 3.0F);") for i, (t, m) in enumerate((("GRAPHITE", "graphite"), ("LANTHANIUM", "lanthanium"), ("DESH", "desh"), ("SATURNITE", "saturnite")))),
          "original SmeltingRecipes.java:112-115: the four burnt electrodes smelt into their ingots, 3.0 experience")
    soldering = original("inventory/recipes/SolderingRecipes.java")
    check(line(soldering, 54, "new ItemStack(ModItems.circuit, 1, EnumCircuitType.BASIC.ordinal()), 200, 250,") and line(soldering, 56, "new ComparableStack(ModItems.circuit, 4, EnumCircuitType.CHIP)")
          and line(soldering, 58, "new ComparableStack(ModItems.circuit, 4, EnumCircuitType.PCB)") and line(soldering, 60, "new OreDictStack(PB.wireFine(), 4)"),
          "original SolderingRecipes.java:54-60: 4 chips + 4 PCBs + 4 lead wire -> 1 basic circuit, 200 ticks, 250 HE/t")
    smelt = original("main/CraftingManager.java")
    check(any("arc_electrode" in text for text in smelt), "the original crafts the electrodes in CraftingManager (NEO already has the recipes, Goal 10B)")
    en = {"container.machineArcFurnaceLarge": "Arc Furnace", "tile.machine_arc_furnace.name": "Electric Arc Furnace", "item.billet_silicon.name": "Silicon Wafer", "item.circuit.chip.name": "Microchip"}
    wrong = {k: original_lang_line(k) for k, v in en.items() if original_lang_line(k) != v}
    check(not wrong, f"the original en_US.lang texts of the upstream keys: {wrong}")


# ---- main --------------------------------------------------------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 13B transcript: {log}", flush=True)
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
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nbaseline: build/migration/goal13b/base-g13a (package goal13b.base)\n"
                     "machine world production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))

    recipe_facts = machine_facts = None

    # ---- Recipe world (sections 3b, 4, 6b, 7r) ----
    if only in (None, "recipe"):
        base_assembly = base_text(ASSEMBLY, "com.hbm.inventory.recipes")
        base_press = base_text(PRESS, "com.hbm.inventory.recipes")
        recipe_fixture = (FIXTURE / RECIPE_FIXTURE).read_text(encoding="utf-8")
        rstubs = recipe_stubs(SOURCE, [recipe_fixture])
        refuse_shadowing(rstubs, RECIPE_PRODUCTION, "recipe")
        rstubs["goal13b/base/AssemblyMachineRecipes.java"] = base_text(ASSEMBLY, "com.hbm.inventory.recipes")
        rstubs["goal13b/base/PressRecipes.java"] = base_text(PRESS, "com.hbm.inventory.recipes")
        recipes = run_dir / "recipes"
        rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in RECIPE_PRODUCTION] + [FIXTURE / RECIPE_FIXTURE])
        run("Compile the Goal 13B recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                  "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
        work = recipes / "work"
        run("Run Goal 13B recipe world (sections 3b, 4, 6b, 7r)",
            [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal13BRecipeRegression", str(work)],
            stage_failure_ok=True)
        if (work / "chain.json").is_file():
            recipe_facts = json.loads((work / "chain.json").read_text(encoding="utf-8"))

    # ---- Machine world (sections 3m, 5, 5w, 5l, 5e, 9m, 6, 7m) ----
    if only in (None, "machine"):
        with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
            vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
        fixture_texts = [(FIXTURE / p).read_text(encoding="utf-8") for p in FIXTURES]
        stubs = build_stubs(SOURCE, fixture_texts, vanilla_tags, NEOFORGE_SOURCES)
        refuse_shadowing(stubs, PRODUCTION, "machine")
        machine = run_dir / "machine"
        sources, classes = write_sources(machine, stubs, [SOURCE / p for p in PRODUCTION] + [FIXTURE11A / "com/hbm/blocks/Goal11ABlockAccess.java"]
                                         + [FIXTURE12A / p for p in FIXTURES12A] + [FIXTURE / p for p in FIXTURES])
        run("Compile the Goal 13B machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn", "-d", str(classes), f"@{sources}"])
        exported = run_dir / "machine-out"
        run("Run Goal 13B machine world (sections 3m, 5, 5w, 5l, 5e, 9m, 6, 7m)",
            [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal13BRegression", str(exported)],
            stage_failure_ok=True)
        if (exported / "machine-facts.json").is_file():
            machine_facts = json.loads((exported / "machine-facts.json").read_text(encoding="utf-8"))

    if only is not None:
        raise SystemExit(f"--only {only}: partial run, failed stages {failed}")

    sections = Sections()
    sections.run("1t. silicon billet: item, recipes, language", silicon_billet)
    sections.run("2t. burnt electrode smelting", smelting)
    sections.run("3p. registered names", registered_ids)
    sections.run("4t. electrodes, arc furnace block, registration, datagen, language, GUI, model", furnace_text)
    if recipe_facts is not None and machine_facts is not None:
        sections.run("8t. chain", lambda check: chain_text(check, recipe_facts, machine_facts))
    else:
        print("AssertionError in 8t. chain after 0 passed checks: the recipe or machine world wrote no facts", flush=True)
        sections.failures.append("8t. chain: no facts")
    sections.run("13t. original references", references)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 13B Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 13B regression failed: {failed}")


if __name__ == "__main__":
    main()
