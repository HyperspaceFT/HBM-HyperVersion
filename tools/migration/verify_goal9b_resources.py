"""Audit the Goal 9B anvil entry, blocks, renderer, recipes, sounds, imported assets and bilingual text.

Default mode runs after `build.ps1 -Offline runData` and also compares the generated output with the pre-Goal 9B
stamp (build/migration/goal9b/stamp-before-g9b.json). `--source-only` skips the generated-output part, for
environments that cannot run Gradle.
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
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
GEN = ROOT / "src/generated/resources"
MAIN = ROOT / "src/main/resources"
JAVA = ROOT / "src/main/java"
OUT = ROOT / "build/migration/goal9b"
# Copy of the stamp taken before any Goal 9B source change, i.e. after Goal 9A: 3822 generated files.
BEFORE_STAMP = OUT / "stamp-before-g9b.json"
BEFORE_COUNT = 3822
# The Goal 8 commit: the last committed AnvilRecipes and generated en_us.json. Goal 9A is not committed; its only
# changes to these two files are the boiler anvil entry and the boiler description (GOAL9A.md).
BASELINE_COMMIT = "1d37f11b"
EN_US = "assets/hbmsntm/lang/en_us.json"
SOUNDS = "assets/hbmsntm/sounds.json"
PICKAXE = "data/minecraft/tags/block/mineable/pickaxe.json"
G9A_DESC = ("block.hbmsntm.heat_boiler.desc",
            "Large boiler that can boil water or heat up oil.$Requires external heat source.$Heat transfer rate: ΔT*0.1 TU/t")
EN_EXPECTED = {
    "block.hbmsntm.machine_condenser": "Steam Condenser",
    "block.hbmsntm.machine_steam_engine": "Steam Engine",
    "block.hbmsntm.machine_steam_engine.desc": "Efficiency: 85%%",
    "block.hbmsntm.reinforced_stone": "Dense Stone",
    "subtitles.block.steam_engine_operate": "Steam engine runs",
}
ZH_EXPECTED = {
    "block.hbmsntm.machine_condenser": "蒸汽冷凝器",
    "block.hbmsntm.machine_steam_engine": "蒸汽机",
    "block.hbmsntm.machine_steam_engine.desc": "效率: 85%%",
    "block.hbmsntm.reinforced_stone": "致密石头",
    "item.hbmsntm.shell_steel": "钢壳",
    "subtitles.block.steam_engine_operate": "蒸汽机运转",
}
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
ADDED = {
    "assets/hbmsntm/blockstates/machine_condenser.json", "assets/hbmsntm/blockstates/machine_steam_engine.json",
    "assets/hbmsntm/blockstates/reinforced_stone.json", "assets/hbmsntm/models/block/machine_condenser.json",
    "assets/hbmsntm/models/block/machine_steam_engine_particle.json", "assets/hbmsntm/models/block/reinforced_stone.json",
    "assets/hbmsntm/models/item/machine_condenser.json", "assets/hbmsntm/models/item/machine_steam_engine.json",
    "assets/hbmsntm/models/item/reinforced_stone.json",
    "data/hbmsntm/advancement/recipes/building_blocks/reinforced_stone.json",
    "data/hbmsntm/advancement/recipes/misc/machine_condenser.json",
    "data/hbmsntm/loot_table/blocks/machine_condenser.json", "data/hbmsntm/loot_table/blocks/machine_steam_engine.json",
    "data/hbmsntm/loot_table/blocks/reinforced_stone.json",
    "data/hbmsntm/recipe/machine_condenser.json", "data/hbmsntm/recipe/reinforced_stone.json",
}
# Generation inputs Goal 9B changes: production Java, zh_cn.json and the five imported assets.
CHANGED_INPUTS = {f"src/main/java/com/hbm/{name}.java" for name in (
    "blockentity/NtmBlockEntityTypes", "blockentity/machine/CondenserBaseBlockEntity",
    "blockentity/machine/MachineCondenserBlockEntity", "blockentity/machine/MachineSteamEngineBlockEntity",
    "blocks/NtmBlocks", "blocks/machine/MachineCondenserBlock", "blocks/machine/MachineSteamEngineBlock",
    "datagen/NtmBlockLootTableProvider", "datagen/NtmBlockStateProvider", "datagen/NtmBlockTagProvider",
    "datagen/NtmLanguageProvider", "datagen/NtmRecipeProvider", "datagen/NtmSoundDefinitionsProvider",
    "inventory/NtmCreativeTabs", "inventory/recipes/anvil/AnvilRecipes", "main/ClientProxy", "main/ResourceManager",
    "registry/NtmSoundEvents", "render/blockentity/RenderSteamEngine")} | {ZH} | {
    f"src/main/resources/assets/hbmsntm/{name}" for name in (
        "models/obj/machines/steam_engine.obj", "sounds/block/steam_engine_operate.ogg", "textures/block/condenser.png",
        "textures/block/reinforced_stone.png", "textures/models/machines/steam_engine.png")}
# Goal 10B corrects seven earlier lines in place (migration/GOAL10B.md D1: 4 tungsten bolts for the soldering station,
# original AnvilRecipes.java:387; D6: each flat stamp makes its own plate/wire/circuit stamp, original :592-598). Each
# live line must occur exactly once and its Goal 8 form not at all; they are put back before the byte comparison, so
# every other line is still compared with the Goal 8 file.
GOAL10B_LINES = (
    ("new ComparableStack(NtmItems.BOLT.get(), 4, BoltItem.Type.TUNGSTEN.meta)",
     "new ComparableStack(NtmItems.BOLT.get(), 1, BoltItem.Type.TUNGSTEN.meta)"),
    *((f"addAnvilRecipe(NtmItems.STAMP_{flat}_FLAT.get(), 1, NtmItems.STAMP_{flat}_{shape}.get(), 1, 2);",
       f"addAnvilRecipe(NtmItems.STAMP_{flat}_FLAT.get(), 1, NtmItems.STAMP_{other}_{shape}.get(), 1, 2);")
      for shape in ("PLATE", "WIRE", "CIRCUIT") for flat, other in (("TITANIUM", "STEEL"), ("STEEL", "TITANIUM"))),
)


def without_goal10b(source):
    """The source with the seven Goal 10B lines put back, and whether each live line was found once (Goal 8 form absent)."""
    found = all(source.count(new) == 1 and source.count(old) == 0 for new, old in GOAL10B_LINES)
    for new, old in GOAL10B_LINES:
        source = source.replace(new, old)
    return source, found


# The Goal 9A and Goal 9B anvil blocks as written in AnvilRecipes (comment, entry and the blank line after it).
BOILER_ENTRY = """        // Steel ingots by item: NEO has no steel ingot tag. The original has no recycling entry for the boiler.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmItems.INGOT_STEEL.get(), 4),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 16),
                        new ComparableStack(NtmItems.PLATE_POLYMER.get(), 8)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.HEAT_BOILER.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

"""
ENGINE_ENTRY = """        // The original's ComparableStack(gear_large, 1) means meta 0; NEO's two-argument form is a wildcard. No recycling entry.
        CONSTRUCTION_RECIPES.add(new AnvilConstructionRecipe(
                new AStack[] {
                        new ComparableStack(NtmBlocks.REINFORCED_STONE.asItem(), 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 12),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 2),
                        new ComparableStack(NtmItems.COIL_COPPER.get(), 4),
                        new ComparableStack(NtmItems.GEAR_LARGE.get(), 1, 0)
                },
                new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STEAM_ENGINE.asItem()))
        ).setTier(2).setOverlay(OverlayType.CONSTRUCTION));

"""
# Original metadata -> NEO facing (BlockDummyable offsets: 2 north, 3 south, 4 west, 5 east).
META_FACING = {"2": "NORTH", "3": "SOUTH", "4": "WEST", "5": "EAST"}
checks = []
skipped = []


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def compact(source):
    return re.sub(r"\s+", " ", source)


def digests(path):
    """Raw bytes plus the LF-normalised form (a Windows checkout may materialise text assets with CRLF)."""
    data = path.read_bytes()
    return {hashlib.sha256(data).hexdigest(), hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()}


def git_show(spec):
    return subprocess.run(["git", "-C", str(ROOT), "show", spec], capture_output=True, check=True).stdout


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def record(name):
    """Migration records are written by the main agent; a missing one skips its checks with a message."""
    path = ROOT / "migration" / name
    if path.is_file():
        return read(path)
    message = f"migration/{name} is missing; its checks were skipped"
    skipped.append(message)
    print("SKIPPED: " + message)
    return None


def between(source, start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


def anvil_entry():
    source = text(JAVA / "com/hbm/inventory/recipes/anvil/AnvilRecipes.java")
    # Goal 11A (migration/GOAL11A.md) appends the fluid burner block after the Goal 10C block; it must occur exactly once,
    # directly after the heating oven recycling entry and at the end of registerConstruction. It is removed first.
    source, goal11a_found = without_goal11a(source)
    check(goal11a_found, "the Goal 11A fluid burner block follows the Goal 10C block exactly once, at the end of registerConstruction")
    # Goal 10C (migration/GOAL10C.md) appends the heating oven block after the steam engine; it must occur exactly once,
    # directly after the engine entry and at the end of registerConstruction. It is removed before the unchanged checks.
    source, goal10c_found = without_goal10c(source)
    check(goal10c_found, "the Goal 10C heating oven block follows the steam engine exactly once, at the end of registerConstruction")
    body = between(source, "private static void registerConstruction() {", "private static void addAnvilRecipe(")
    starts = [m.start() for m in re.finditer(r"CONSTRUCTION_RECIPES\.add\(new AnvilConstructionRecipe\(", body)]
    last = body[starts[-1]:]
    check(not re.search(r"\badd(AnvilRecipe|RecycleRecipe)\(", last), "no helper-added construction entry follows the steam engine")
    engine = compact(last)
    for part in ("new ComparableStack(NtmBlocks.REINFORCED_STONE.asItem(), 16)", "new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 12)",
                 "new ComparableStack(NtmItems.SHELL_STEEL.get(), 2)", "new ComparableStack(NtmItems.COIL_COPPER.get(), 4)",
                 "new ComparableStack(NtmItems.GEAR_LARGE.get(), 1, 0)",
                 "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_STEAM_ENGINE.asItem()))", ".setTier(2).setOverlay(OverlayType.CONSTRUCTION)"):
        check(part in engine, f"steam engine anvil entry contains {part}")
    check(engine.count("new ComparableStack(") == 4 and engine.count("TagStack(") == 1 and "MetaHelper" not in engine,
          "steam engine anvil entry: five inputs, a plain output")
    check("NtmBlocks.HEAT_BOILER.asItem()" in compact(body[starts[-2]:starts[-1]]), "the Goal 9A boiler entry directly precedes the steam engine")
    check(source.count("NtmBlocks.MACHINE_STEAM_ENGINE") == 1, "the steam engine has no recycling entry (only the construction output)")
    # Original AnvilRecipes.java:351-358: tier 2, 16 dense stone, 12 steel plates, 2 steel shells, 4 copper coils, 1 large gear.
    original = compact(text(ORIGINAL / "src/main/java/com/hbm/inventory/recipes/anvil/AnvilRecipes.java"))
    check(re.search(r"new ComparableStack\(ModBlocks\.reinforced_stone, 16\), new OreDictStack\(STEEL\.plate\(\), 12\), "
                    r"new OreDictStack\(STEEL\.shell\(\), 2\), new ComparableStack\(ModItems\.coil_copper, 4\), "
                    r"new ComparableStack\(ModItems\.gear_large, 1\) \}, new AnvilOutput\(new ItemStack\(ModBlocks\.machine_steam_engine\)\)\)\.setTier\(2\)",
                    original) is not None,
          "the original recipe is tier 2 with 16 dense stone, 12 steel plates, 2 steel shells, 4 copper coils and 1 large gear")
    check("this.meta = 0;" in compact(between(text(ORIGINAL / "src/main/java/com/hbm/inventory/RecipesCommon.java"),
                                              "public ComparableStack(Item item) {", "}")),
          "the original one-item ComparableStack constructor means meta 0, so the gear input is meta 0")
    check(source.count(BOILER_ENTRY) == 1 and source.count(ENGINE_ENTRY) == 1 and source.index(BOILER_ENTRY) + len(BOILER_ENTRY) == source.index(ENGINE_ENTRY),
          "the boiler and steam engine entries are the exact Goal 9A and Goal 9B blocks, in that order")
    baseline = git_show(f"{BASELINE_COMMIT}:src/main/java/com/hbm/inventory/recipes/anvil/AnvilRecipes.java").decode("utf-8").replace("\r\n", "\n")
    reverted, goal10b_found = without_goal10b(source.replace(BOILER_ENTRY + ENGINE_ENTRY, ""))
    check(goal10b_found and reverted == baseline,
          f"without the two blocks AnvilRecipes is byte-identical to {BASELINE_COMMIT} "
          "(earlier entries unchanged apart from the seven Goal 10B line corrections)")


def blocks():
    registry = text(JAVA / "com/hbm/blocks/NtmBlocks.java")
    stone = next(line for line in registry.splitlines() if '"reinforced_stone"' in line)
    check("registerBlastInfoBlock(" in stone and "strength(15.0F, 100.0F)" in stone and "requiresCorrectToolForDrops()" in stone,
          "reinforced_stone: blast-info item, strength 15/100, needs the correct tool")
    original_blocks = text(ORIGINAL / "src/main/java/com/hbm/blocks/ModBlocks.java")
    check(re.search(r"reinforced_stone = new BlockGeneric\(Material\.rock\)[^;]*setHardness\(15\.0F\)\.setResistance\(100\.0F\)", original_blocks) is not None
          and "GameRegistry.registerBlock(reinforced_stone, ItemBlockBlastInfo.class" in original_blocks,
          "the original dense stone is rock (pickaxe), hardness 15, resistance 100, with the blast-info item")
    for name, cls, occluding in (("machine_steam_engine", "MachineSteamEngineBlock", False), ("machine_condenser", "MachineCondenserBlock", True)):
        line = next(line for line in registry.splitlines() if f'"{name}"' in line)
        check(f"new {cls}(" in line and "strength(0.6F, 10.0F)" in line and "requiresCorrectToolForDrops()" in line
              and ("noOcclusion()" not in line) == occluding, f"{name}: NEO machine strength 0.6/10 (original 5/10), needs the correct tool")
    tags = text(JAVA / "com/hbm/datagen/NtmBlockTagProvider.java")
    pickaxe = between(tags, "this.tag(BlockTags.MINEABLE_WITH_PICKAXE)", "this.tag(BlockTags.ANVIL)")
    for name in ("REINFORCED_STONE", "MACHINE_STEAM_ENGINE", "MACHINE_CONDENSER"):
        check(f"NtmBlocks.{name}.get()" in pickaxe, f"{name} is mineable with a pickaxe")

    engine = text(JAVA / "com/hbm/blocks/machine/MachineSteamEngineBlock.java")
    check("return new int[] { 1, 0, 5, 1, 1, 1 };" in engine and "public int getOffset() { return 1; }" in engine,
          "MachineSteamEngineBlock: dimensions {1,0,5,1,1,1}, offset 1 (MachineSteamEngine.java:37-44)")
    check("case EXTRA -> new ProxyComboBlockEntity(pos, state).power().fluid();" in engine,
          "MachineSteamEngineBlock: EXTRA proxies carry power and fluid (original TileEntityProxyCombo().power().fluid())")
    fill = between(engine, "protected void fillSpace(", "public void printHook(")
    check("BlockPos side = pos.relative(dir, offset).relative(MachineSteamEngineBlockEntity.getPortSide(dir)).above();" in fill
          and "this.makeExtra(level, side);" in fill and "this.makeExtra(level, side.relative(dir));" in fill
          and "this.makeExtra(level, side.relative(dir.getOpposite()));" in fill,
          "fillSpace makes the three upper port-side blocks (core + rot, +-dir, y+1) extras")
    original_fill = compact(text(ORIGINAL / "src/main/java/com/hbm/blocks/machine/MachineSteamEngine.java"))
    check("ForgeDirection rot = dir.getRotation(ForgeDirection.UP); this.makeExtra(world, x + rot.offsetX, y + 1, z + rot.offsetZ); "
          "this.makeExtra(world, x + rot.offsetX + dir.offsetX, y + 1, z + rot.offsetZ + dir.offsetZ); "
          "this.makeExtra(world, x + rot.offsetX - dir.offsetX, y + 1, z + rot.offsetZ - dir.offsetZ);" in original_fill,
          "the original fillSpace makes the same three blocks extras")
    be = text(JAVA / "com/hbm/blockentity/machine/MachineSteamEngineBlockEntity.java")
    check("return facing.getClockWise();" in be, "the port side is clockwise from the facing (original getRotation(UP))")
    check("this.addStandardInfo(components);" in engine, "the steam engine item shows the standard .desc tooltip")
    check(engine.count("tankLine(") == 3 and "String.format(Locale.US, \"%,d\", tank.getFill()) + \" / \"" in engine,
          "the steam engine overlay lists both tanks with grouped numbers, as MachineSteamEngine.printHook")

    condenser = text(JAVA / "com/hbm/blocks/machine/MachineCondenserBlock.java")
    check("return RenderShape.MODEL;" in condenser, "the condenser renders its block model (BaseEntityBlock defaults to INVISIBLE)")
    check("new MachineCondenserBlockEntity(pos, state)" in condenser and "tickable.updateEntity()" in condenser,
          "the condenser block creates and ticks its block entity")
    check("\": \" + tank.getFill() + \"/\" + tank.getMaxFill() + \"mB\"" in condenser, "the condenser overlay keeps the original fill/max mB format")
    base = text(JAVA / "com/hbm/blockentity/machine/CondenserBaseBlockEntity.java")
    check(base.count("this.getBlockPos().relative(dir), dir);") == 2, "the condenser base probes the neighbour on each side")

    client_only = ("com.hbm.render", "ResourceManager", "net.minecraft.client")
    for path in ("blockentity/machine/MachineSteamEngineBlockEntity.java", "blockentity/machine/MachineCondenserBlockEntity.java",
                 "blockentity/machine/CondenserBaseBlockEntity.java"):
        source = text(JAVA / "com/hbm" / path)
        check(not any(token in source for token in client_only), f"{path} has no client-only reference")


def renderer():
    source = text(JAVA / "com/hbm/render/blockentity/RenderSteamEngine.java")
    table = {"SOUTH": "90F", "EAST": "180F", "NORTH": "270F", "WEST": "0F"}
    switch = between(source, "switch(facing) {", "default -> { }")
    found = dict(re.findall(r"case (\w+) -> RenderContext\.mulPose\(Axis\.YP\.rotationDegrees\(([\d.]+F)\)\);", switch))
    check(found == table, "RenderSteamEngine: angle table SOUTH 90, EAST 180, NORTH 270, WEST 0")
    original = text(ORIGINAL / "src/main/java/com/hbm/render/tileentity/RenderSteamEngine.java")
    meta = dict(re.findall(r"case (\d): GL11\.glRotatef\((\d+), 0F, 1F, 0F\); break;", original))
    check({META_FACING[k]: f"{v}F" for k, v in meta.items()} == table, "the same table as the original RenderSteamEngine")
    check("RenderContext.translate(2.0F, 0.0F, 0.0F);\n        this.renderCommon(angle);" in source,
          "the model is shifted by (2, 0, 0) after the rotation, as the original")
    obj = text(MAIN / "assets/hbmsntm/models/obj/machines/steam_engine.obj")
    parts = set(re.findall(r"^o (\w+)$", obj, re.MULTILINE))
    rendered = set(re.findall(r'steam_engine\.renderPart\("(\w+)"\)', source))
    check(rendered == parts == {"Base", "Flywheel", "Shaft", "Transmission", "Piston"}, "every OBJ part is rendered and every rendered part exists")
    check("RenderContext.mulPose(Axis.YN.rotationDegrees(90F));\n                RenderContext.translate(0.0F, -1.5F, 0.0F);\n                RenderContext.scale(2.0F, 2.0F, 2.0F);" in source,
          "the inventory transform is the original's (-90 about Y, down 1.5, scale 2)")
    manager = text(JAVA / "com/hbm/main/ResourceManager.java")
    check('STEAM_ENGINE_TEX = NuclearTechMod.withDefaultNamespace("textures/models/machines/steam_engine.png")' in manager
          and 'steam_engine = new HFRWavefrontObject("models/obj/machines/steam_engine.obj").asVBO();' in manager,
          "ResourceManager loads the steam engine model and texture")
    proxy = text(JAVA / "com/hbm/main/ClientProxy.java")
    check("BlockEntityRenderers.register(NtmBlockEntityTypes.MACHINE_STEAM_ENGINE.get(), new RenderSteamEngine());" in proxy,
          "ClientProxy registers RenderSteamEngine (and with it the item renderer)")


def recipes_source():
    provider = compact(text(JAVA / "com/hbm/datagen/NtmRecipeProvider.java"))
    check('ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, NtmBlocks.REINFORCED_STONE.get(), 4) .pattern("FBF") .pattern("BFB") .pattern("FBF") '
          ".define('F', Items.COBBLESTONE) .define('B', Items.STONE)" in provider, "the provider defines dense stone FBF/BFB/FBF x4")
    check('ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_CONDENSER.get(), 1) .pattern("SIS") .pattern("ICI") .pattern("SIS") '
          ".define('S', NtmItems.INGOT_STEEL.get()) .define('I', NtmItems.PLATE_IRON.get()) "
          ".define('C', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.COPPER.ordinal(), NtmItems.CAST_PLATE.get()))" in provider,
          "the provider defines the condenser SIS/ICI/SIS with a copper cast plate")
    original = compact(text(ORIGINAL / "src/main/java/com/hbm/main/CraftingManager.java"))
    check('addRecipeAuto(new ItemStack(ModBlocks.reinforced_stone, 4), new Object[] { "FBF", "BFB", "FBF", \'F\', Blocks.cobblestone, \'B\', Blocks.stone });' in original,
          "the original dense stone recipe (CraftingManager.java:359)")
    check('addRecipeAuto(new ItemStack(ModBlocks.machine_condenser), new Object[] { "SIS", "ICI", "SIS", \'S\', STEEL.ingot(), \'I\', IRON.plate(), \'C\', CU.plateCast() });' in original,
          "the original condenser recipe (CraftingManager.java:842)")
    for name in ("REINFORCED_STONE", "MACHINE_STEAM_ENGINE", "MACHINE_CONDENSER"):
        check(f"output.accept(NtmBlocks.{name});" in text(JAVA / "com/hbm/inventory/NtmCreativeTabs.java"), f"{name} is in a creative tab")


def sounds_source():
    events = text(JAVA / "com/hbm/registry/NtmSoundEvents.java")
    check('STEAM_ENGINE_OPERATE = reg("block.steam_engine_operate");' in events, "the operate sound event is registered")
    definitions = compact(text(JAVA / "com/hbm/datagen/NtmSoundDefinitionsProvider.java"))
    check('this.add(NtmSoundEvents.STEAM_ENGINE_OPERATE, SoundDefinition.definition() .subtitle("subtitles.block.steam_engine_operate") '
          '.with(sound(NuclearTechMod.withDefaultNamespace("block/steam_engine_operate"))) );' in definitions, "the operate sound has a definition and subtitle")
    original = text(ORIGINAL / "src/main/resources/assets/hbm/sounds.json")
    check('"block.steamEngineOperate": {"category": "block", "sounds": [{"name": "block/steamEngineOperate", "stream": false}]}' in original,
          "the original block.steamEngineOperate is a single non-streamed block sound")


def language(review):
    provider = text(JAVA / "com/hbm/datagen/NtmLanguageProvider.java")
    for key, value in EN_EXPECTED.items():
        constant = {"block.hbmsntm.machine_condenser": "MACHINE_CONDENSER", "block.hbmsntm.machine_steam_engine": "MACHINE_STEAM_ENGINE",
                    "block.hbmsntm.reinforced_stone": "REINFORCED_STONE"}.get(key)
        line = f"this.add(NtmBlocks.{constant}, {json.dumps(value)});" if constant else f"this.add({json.dumps(key)}, {json.dumps(value)});"
        check(provider.count(line) == 1, f"NtmLanguageProvider adds {key}")
    check("this.add(NtmItems.SHELL_STEEL, \"Steel Shell\");" in provider, "the steel shell keeps its English name")
    zh = read(MAIN / "assets/hbmsntm/lang/zh_cn.json")
    for key, value in ZH_EXPECTED.items():
        check(zh.get(key) == value, f"zh_cn.json {key} = {value}")
    mapping = read(ROOT / "migration/localization/zh_cn-map.json")["entries"]
    check(sum(value["kind"] == "deferred" for value in mapping.values()) == 108, "deferred localization count is 108 (109 minus the steel shell)")
    check(mapping["item.hbmsntm.shell_steel"]["kind"] != "deferred", "the steel shell is no longer deferred")
    if review is None:
        return
    check(set(review["reviewed_keys"]) == set(ZH_EXPECTED), "the review covers exactly the six Goal 9B keys")
    for key in review["reviewed_keys"]:
        entry = review["reviewed_entries"][key]
        check(key in mapping and mapping[key] == entry and entry["target_zh"] == zh[key], f"zh_cn-map entry equals the review: {key}")
        if key in EN_EXPECTED:
            check(entry["target_en"] == EN_EXPECTED[key], f"the reviewed English is the provider text: {key}")
    lang = {"en": text(ORIGINAL / "src/main/resources/assets/hbm/lang/en_US.lang"), "zh": text(ORIGINAL / "src/main/resources/assets/hbm/lang/zh_CN.lang")}
    for key, entry in review["reviewed_entries"].items():
        if entry["kind"] == "upstream":
            check(f"{entry['source_key']}={entry['source_en']}\n" in lang["en"] and f"{entry['source_key']}={entry['source_zh']}\n" in lang["zh"],
                  f"the upstream source texts are the original lang lines: {key}")


def ownership():
    record_ = record("goal9b-resource-ownership.json")
    if record_ is None:
        return
    check(len(record_["imported_assets"]) == 5, "five imported assets are recorded")
    for asset in record_["imported_assets"]:
        target, source = ROOT / asset["target_path"], ORIGINAL / asset["source_path"]
        check(target.is_file() and source.is_file(), f"imported asset and its original exist: {asset['target_path']}")
        check(asset["target_sha256"] in digests(target), f"current NEO bytes match the record (raw or LF): {asset['target_path']}")
        check(asset["source_sha256"] in digests(source), f"original bytes match the record (raw or LF): {asset['source_path']}")
        check(asset["identical_to_source"] and bool(digests(source) & digests(target)), f"byte-identical to the original: {asset['target_path']}")
        last = subprocess.run(["git", "-C", str(ORIGINAL), "log", "-1", "--format=%H", "--", asset["source_path"]],
                              capture_output=True, text=True, check=True).stdout.strip()
        check(last == asset["source_last_commit"], f"original last commit matches the record: {asset['source_path']}")


def source_checks():
    anvil_entry()
    blocks()
    renderer()
    recipes_source()
    sounds_source()
    review = record("goal9b-localization-review.json")
    language(review)
    ownership()
    return review


def generated_checks():
    before = read(BEFORE_STAMP)
    after = read(GEN / ".migration-stamp.json")
    added = sorted(set(after["generated"]) - set(before["generated"]))
    removed = sorted(set(before["generated"]) - set(after["generated"]))
    modified = sorted(name for name in set(before["generated"]) & set(after["generated"])
                      if before["generated"][name] != after["generated"][name])
    changed_inputs = sorted(name for name in set(before["inputs"]) | set(after["inputs"])
                            if before["inputs"].get(name) != after["inputs"].get(name))
    check(len(before["generated"]) == BEFORE_COUNT, f"the before-stamp has {BEFORE_COUNT} generated files")
    check(set(added) == ADDED and not removed, "exactly the sixteen expected generated files are added, none removed")
    check(len(after["generated"]) == BEFORE_COUNT + len(ADDED), f"{BEFORE_COUNT + len(ADDED)} generated files")
    check(modified == sorted([EN_US, SOUNDS, PICKAXE]), "only en_us.json, sounds.json and the pickaxe tag are modified")
    check(set(changed_inputs) == CHANGED_INPUTS, "changed generation inputs are exactly the Goal 9B production files, zh_cn.json and the five assets")

    # en_us.json before Goal 9B is the Goal 8 file plus the Goal 9A boiler description, serialised as the provider does.
    old_bytes = git_show(f"{BASELINE_COMMIT}:src/generated/resources/{EN_US}")
    old = json.loads(old_bytes.decode("utf-8"))
    old[G9A_DESC[0]] = G9A_DESC[1]
    rebuilt = json.dumps(old, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    check(hashlib.sha256(rebuilt).hexdigest() == before["generated"][EN_US], "the before-stamp en_us.json is the Goal 8 file plus the Goal 9A description")
    new = read(GEN / EN_US)
    check(set(new) - set(old) == set(EN_EXPECTED) and not set(old) - set(new), "en_us.json gains exactly the five Goal 9B keys")
    check(all(new[key] == old[key] for key in old), "every other English value is unchanged")
    check(all(new[key] == value for key, value in EN_EXPECTED.items()), "the generated English values are the provider texts")

    for name in (SOUNDS, PICKAXE):
        base = git_show(f"{BASELINE_COMMIT}:src/generated/resources/{name}")
        check(hashlib.sha256(base).hexdigest() == before["generated"][name], f"the before-stamp {name} is the Goal 8 file")
    sounds_old, sounds_new = json.loads(git_show(f"{BASELINE_COMMIT}:src/generated/resources/{SOUNDS}")), read(GEN / SOUNDS)
    check(set(sounds_new) - set(sounds_old) == {"block.steam_engine_operate"} and all(sounds_new[k] == v for k, v in sounds_old.items()),
          "sounds.json gains only block.steam_engine_operate")
    check(sounds_new["block.steam_engine_operate"] == {"sounds": ["hbmsntm:block/steam_engine_operate"], "subtitle": "subtitles.block.steam_engine_operate"},
          "the generated sound entry plays the imported file with the subtitle")
    pick_old, pick_new = json.loads(git_show(f"{BASELINE_COMMIT}:src/generated/resources/{PICKAXE}"))["values"], read(GEN / PICKAXE)["values"]
    check([v for v in pick_new if v not in pick_old] == ["hbmsntm:reinforced_stone", "hbmsntm:machine_steam_engine", "hbmsntm:machine_condenser"]
          and [v for v in pick_new if v in pick_old] == pick_old, "the pickaxe tag gains exactly the three blocks")

    stone = read(GEN / "data/hbmsntm/recipe/reinforced_stone.json")
    check(stone["pattern"] == ["FBF", "BFB", "FBF"] and stone["key"] == {"B": {"item": "minecraft:stone"}, "F": {"item": "minecraft:cobblestone"}}
          and stone["result"] == {"count": 4, "id": "hbmsntm:reinforced_stone"}, "generated dense stone recipe")
    copper = list(re.findall(r"^\s+(\w+)\(", between(text(JAVA / "com/hbm/items/CastPlateItem.java"), "public enum Type {", ";"), re.MULTILINE)).index("COPPER")
    condenser = read(GEN / "data/hbmsntm/recipe/machine_condenser.json")
    check(condenser["pattern"] == ["SIS", "ICI", "SIS"] and condenser["key"]["S"] == {"item": "hbmsntm:ingot_steel"}
          and condenser["key"]["I"] == {"item": "hbmsntm:plate_iron"}
          and condenser["key"]["C"] == {"type": "neoforge:components", "components": {"hbmsntm:meta": copper}, "items": "hbmsntm:cast_plate"}
          and condenser["result"] == {"count": 1, "id": "hbmsntm:machine_condenser"}, f"generated condenser recipe (copper cast plate META {copper})")
    model = read(GEN / "assets/hbmsntm/models/block/machine_condenser.json")
    check(model == {"parent": "minecraft:block/cube_all", "textures": {"all": "hbmsntm:block/condenser"}}, "the condenser model uses the imported texture")
    check(read(GEN / "assets/hbmsntm/models/block/reinforced_stone.json")["textures"] == {"all": "hbmsntm:block/reinforced_stone"},
          "the dense stone model uses the imported texture")
    check(read(GEN / "assets/hbmsntm/models/item/machine_steam_engine.json")["parent"] == "minecraft:builtin/entity",
          "the steam engine item renders through the block entity renderer")
    for name in ("machine_condenser", "machine_steam_engine", "reinforced_stone"):
        loot = read(GEN / f"data/hbmsntm/loot_table/blocks/{name}.json")
        check(loot["pools"][0]["entries"] == [{"type": "minecraft:item", "name": f"hbmsntm:{name}"}], f"{name} drops itself")
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
    report.update({"checks": len(checks), "assertions": checks, "skipped": skipped,
                   "boundary": "Provider/recipe/block/renderer source, generated resources and source assets only; no Minecraft anvil, crafting, rendering or gameplay run."})
    OUT.mkdir(parents=True, exist_ok=True)
    name = "source-check.json" if args.source_only else "generated-check.json"
    (OUT / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Goal 9B resources ({report['mode']}): {len(checks)} checks passed; report {OUT / name}")


if __name__ == "__main__":
    main()
