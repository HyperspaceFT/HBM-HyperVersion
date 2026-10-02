"""Goal 10C regression: the heating oven (anvil entries, removal, heat) and the electric furnace.

One Java world compiles real production classes against isolated stand-ins (goal10c_regression/stubs.py, the Goal 10B
machine world extended with a block model, smelting recipes, upgrades and the vanilla slot hooks):

* sections 1-9 run in com.hbm.blockentity.machine.Goal10CRegression: the live AnvilRecipes against the ee8f8d06 copy
  (git show, package goal10c.head), HeaterOvenBlock/AbstractHeaterBlock with a DummyableBlock stand-in carrying the
  production method bodies, HeaterOvenBlockEntity, MachineElectricFurnaceBlockEntity/Block/Menu, SlotSmeltingOutput,
  production UpgradeManagerNT, and the Goal 9B energy network, boiler and steam engine.

Section 10 is a text check of the generated resources and the registration/datagen/JEI sources, run here in Python. Every
section reports "N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the run fails at
the end.
"""

from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import uuid

from goal10c_regression.stubs import ANVIL, build_stubs
from verify_goal9b import PRODUCTION as GOAL9B_PRODUCTION


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
RESOURCES = ROOT / "src/main/resources"
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT/src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal10c_regression")
OUTPUT = ROOT / "build/migration/goal10c/regression"
# The Goal 9B commit: AnvilRecipes before Goal 10B and 10C (neither is committed). Pinned, as in the Goal 10B suite.
BASELINE_COMMIT = "ee8f8d06"
# Not compiled: MachineElectricFurnaceScreen and the JEI plugin (client-only; section 10 reads their text), the datagen
# providers (section 10 reads their text and the generated JSON), DummyableBlock (a stand-in carrying production bodies),
# HeaterOvenMenu, ILookOverlay and ITooltipProvider (stand-ins). See goal10c_regression/README.md.
PRODUCTION = tuple(dict.fromkeys(
    list(GOAL9B_PRODUCTION)
    + [
        "com/hbm/blockentity/IConditionalInvAccess.java",
        "com/hbm/blocks/DummyBlockType.java",
        "com/hbm/handler/MultiblockHandlerXR.java",
        "com/hbm/inventory/UpgradeManagerNT.java",
        "com/hbm/blocks/machine/heater/AbstractHeaterBlock.java",
        "com/hbm/blocks/machine/heater/HeaterOvenBlock.java",
        "com/hbm/blockentity/machine/heater/HeaterOvenBlockEntity.java",
        "com/hbm/blockentity/machine/MachineElectricFurnaceBlockEntity.java",
        "com/hbm/blocks/machine/MachineElectricFurnaceBlock.java",
        "com/hbm/inventory/menus/MachineElectricFurnaceMenu.java",
        "com/hbm/inventory/SlotSmeltingOutput.java",
    ]
))
FIXTURES = (
    "com/hbm/blocks/Goal10CBlockAccess.java",
    "com/hbm/blockentity/machine/Goal10CRegression.java",
)


def jdk():
    """Use JAVA_HOME, then the Windows JDK the earlier goals used, then the PATH."""
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin")
    candidates.append(Path(r"C:\Program Files\Java\jdk-21\bin"))
    for directory in candidates:
        for suffix in (".exe", ""):
            java, javac = directory / f"java{suffix}", directory / f"javac{suffix}"
            if java.is_file() and javac.is_file():
                return java, javac
    java, javac = shutil.which("java"), shutil.which("javac")
    if java and javac:
        return Path(java), Path(javac)
    raise SystemExit("Existing JDK 21 not found")


def baseline(path, package):
    """A committed production source moved to the package goal10c.head; it still sees its own package's classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:src/main/java/{path}"], capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"baseline package line not found in {path}")
    return text.replace(line, f"package goal10c.head;\nimport {package}.*;\n")


def compact(text):
    return re.sub(r"\s+", " ", text)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---- Python section 10 ----------------------------------------------------------------------------------------------

class Sections:
    def __init__(self):
        self.total = 0
        self.failures = []

    def run(self, name, body):
        passed = 0

        def check(condition, message):
            nonlocal passed
            if not condition:
                raise AssertionError(message)
            passed += 1

        try:
            body(check)
            print(f"{name}: {passed} checks passed", flush=True)
        except AssertionError as error:
            print(f"AssertionError in {name} after {passed} passed checks: {error}", flush=True)
            self.failures.append(f"{name}: {error}")
        self.total += passed


def java(path):
    """A production source under SOURCE (the mutation check points SOURCE at a mutated copy)."""
    return (SOURCE / "com/hbm" / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def enum_ordinal(source, name):
    match = re.search(r"public enum Type\b[^{]*\{(.*?);", source, re.S)
    names = re.findall(r"\b([A-Z][A-Z0-9_]*)\s*(?:\([^)]*\))?\s*(?:,|$)", re.sub(r"//[^\n]*", "", match.group(1)).strip())
    return names.index(name)


FURNACE = "hbmsntm:machine_electric_furnace"
TEXTURE = "hbmsntm:block/machine_electric_furnace_"


def static(check):
    gen = GENERATED / "assets/hbmsntm"
    # Blockstate: facing x lit, the front (north in the model) turned to the facing; unlit -> _front_off, lit -> _front_on.
    variants = read_json(gen / "blockstates/machine_electric_furnace.json")["variants"]
    rotation = {"north": None, "east": 90, "south": 180, "west": 270}
    check(sorted(variants) == sorted(f"facing={f},lit={l}" for f in rotation for l in ("false", "true")), "blockstate: 8 variants, facing x lit")
    for facing, y in rotation.items():
        for lit, model in (("false", "hbmsntm:block/machine_electric_furnace"), ("true", "hbmsntm:block/machine_electric_furnace_on")):
            v = variants[f"facing={facing},lit={lit}"]
            check(v.get("model") == model and v.get("y") == y and set(v) <= {"model", "y"},
                  f"blockstate facing={facing},lit={lit}: {model}, y {y or 0} (got {v})")
    for name, front in (("machine_electric_furnace", "front_off"), ("machine_electric_furnace_on", "front_on")):
        model = read_json(gen / f"models/block/{name}.json")
        check(model == {"parent": "minecraft:block/cube", "textures": {
            "down": TEXTURE + "bottom", "up": TEXTURE + "top", "north": TEXTURE + front, "east": TEXTURE + "side",
            "south": TEXTURE + "side", "west": TEXTURE + "side", "particle": TEXTURE + "side"}},
              f"block model {name}: cube, north = {front}, bottom/top, side elsewhere and for the particle")
    check(read_json(gen / "models/item/machine_electric_furnace.json") == {"parent": "hbmsntm:block/machine_electric_furnace"},
          "item model: the unlit block model")
    for texture in ("bottom", "top", "side", "front_off", "front_on"):
        check((RESOURCES / f"assets/hbmsntm/textures/block/machine_electric_furnace_{texture}.png").is_file(), f"texture machine_electric_furnace_{texture}.png exists")
    check((RESOURCES / "assets/hbmsntm/textures/gui/processing/gui_electric_furnace.png").is_file(), "GUI texture gui_electric_furnace.png exists")

    loot = read_json(GENERATED / "data/hbmsntm/loot_table/blocks/machine_electric_furnace.json")
    pool = loot["pools"][0]
    check(loot["type"] == "minecraft:block" and len(loot["pools"]) == 1 and pool["entries"] == [{"type": "minecraft:item", "name": FURNACE}]
          and pool["conditions"] == [{"condition": "minecraft:survives_explosion"}] and pool["rolls"] == 1.0,
          "loot table: the block drops itself (survives_explosion)")

    # Recipe: original CraftingManager.java:230, BBB/WFW/RRR with beryllium ingots, copper cast plates, a furnace, tungsten coils.
    original = compact((ORIGINAL / "main/CraftingManager.java").read_text(encoding="utf-8"))
    check("addRecipeAuto(new ItemStack(Item.getItemFromBlock(ModBlocks.machine_electric_furnace_off), 1), new Object[] { \"BBB\", \"WFW\", \"RRR\", "
          "'B', BE.ingot(), 'R', ModItems.coil_tungsten, 'W', CU.plateCast(), 'F', Item.getItemFromBlock(Blocks.furnace) });" in original,
          "original CraftingManager: BBB/WFW/RRR, B beryllium ingot, W copper cast plate, F furnace, R tungsten coil")
    copper = enum_ordinal(java("items/CastPlateItem.java"), "COPPER")
    recipe = read_json(GENERATED / "data/hbmsntm/recipe/machine_electric_furnace.json")
    check(recipe["type"] == "minecraft:crafting_shaped" and recipe["pattern"] == ["BBB", "WFW", "RRR"]
          and recipe["result"] == {"count": 1, "id": FURNACE}
          and recipe["key"] == {"B": {"item": "hbmsntm:ingot_beryllium"}, "F": {"item": "minecraft:furnace"}, "R": {"item": "hbmsntm:coil_tungsten"},
                                "W": {"type": "neoforge:components", "components": {"hbmsntm:meta": copper}, "items": "hbmsntm:cast_plate"}},
          f"generated recipe machine_electric_furnace.json: BBB/WFW/RRR, W = cast_plate with META {copper} (CastPlateItem COPPER)")
    provider = compact(java("datagen/NtmRecipeProvider.java"))
    check("ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get(), 1) .pattern(\"BBB\") .pattern(\"WFW\") .pattern(\"RRR\") "
          ".define('B', NtmItems.INGOT_BERYLLIUM.get()) .define('W', DataComponentIngredient.of(false, NtmDataComponents.META, CastPlateItem.Type.COPPER.ordinal(), NtmItems.CAST_PLATE.get())) "
          ".define('F', Items.FURNACE) .define('R', NtmItems.COIL_TUNGSTEN.get()) .unlockedBy(\"has_cast_plate\", has(NtmItems.CAST_PLATE.get())) .save(recipeOutput);" in provider,
          "NtmRecipeProvider: the furnace recipe as generated (id hbmsntm:machine_electric_furnace)")
    check(provider.count("NtmBlocks.MACHINE_ELECTRIC_FURNACE") == 1, "NtmRecipeProvider: one furnace recipe")

    pickaxe = read_json(GENERATED / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    check(pickaxe.count(FURNACE) == 1, "the pickaxe tag lists the furnace once")
    tags = java("datagen/NtmBlockTagProvider.java")
    pick = tags[tags.index("this.tag(BlockTags.MINEABLE_WITH_PICKAXE)"):]
    pick = pick[:pick.index(";")]
    check("NtmBlocks.MACHINE_ELECTRIC_FURNACE.get()" in pick, "NtmBlockTagProvider: the furnace is in the pickaxe tag")
    check("this.dropSelf(NtmBlocks.MACHINE_ELECTRIC_FURNACE.get());" in java("datagen/NtmBlockLootTableProvider.java"), "NtmBlockLootTableProvider: dropSelf")
    states = java("datagen/NtmBlockStateProvider.java")
    check("this.registerMachineElectricFurnace();" in states and 'this.electricFurnaceModel(this.name(block) + "_on", "block/machine_electric_furnace_front_on")' in states,
          "NtmBlockStateProvider: the furnace models and variants are registered")

    en = read_json(GENERATED / "assets/hbmsntm/lang/en_us.json")
    zh = read_json(RESOURCES / "assets/hbmsntm/lang/zh_cn.json")
    for key in ("block.hbmsntm.machine_electric_furnace", "container.electricFurnace"):
        check(en.get(key) == "Electric Furnace" and zh.get(key) == "电炉", f"{key}: Electric Furnace / 电炉")
    language = java("datagen/NtmLanguageProvider.java")
    check('this.add(NtmBlocks.MACHINE_ELECTRIC_FURNACE, "Electric Furnace");' in language and 'this.add("container.electricFurnace", "Electric Furnace");' in language,
          "NtmLanguageProvider: both English names")
    check('Component.translatable("container.electricFurnace")' in java("blockentity/machine/MachineElectricFurnaceBlockEntity.java"),
          "the block entity names its container container.electricFurnace (the original's key)")

    jei = compact(java("handler/jei/NtmJeiPlugin.java"))
    check("registration.addRecipeCatalyst( NtmBlocks.MACHINE_ELECTRIC_FURNACE.asItem(), mezz.jei.api.constants.RecipeTypes.SMELTING );" in jei,
          "JEI: the furnace is a catalyst for Minecraft smelting")
    check("registration.addRecipeClickArea(com.hbm.inventory.screens.MachineElectricFurnaceScreen.class, 43, 36, 28, 12, mezz.jei.api.constants.RecipeTypes.SMELTING);" in jei,
          "JEI: click area 43, 36, 28 x 12 on the furnace screen")
    check("output.accept(NtmBlocks.MACHINE_ELECTRIC_FURNACE);" in java("inventory/NtmCreativeTabs.java"), "creative tab entry")
    events = java("main/CommonEvents.java")
    screens = events[events.index("public static void registerScreens("):]
    screens = screens[:screens.index("\n    }")]
    check("event.register(NtmMenuTypes.MACHINE_ELECTRIC_FURNACE.get(), MachineElectricFurnaceScreen::new);" in screens, "screen registration in registerScreens")
    check('reg("machine_electric_furnace", MachineElectricFurnaceMenu::new)' in java("inventory/NtmMenuTypes.java"), "menu type machine_electric_furnace")
    types = compact(java("blockentity/NtmBlockEntityTypes.java"))
    check('BLOCK_ENTITY_TYPES.register( "machine_electric_furnace", () -> BlockEntityType.Builder.of( MachineElectricFurnaceBlockEntity::new, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get())' in types,
          "block entity type machine_electric_furnace")
    blocks = java("blocks/NtmBlocks.java")
    line = next((l for l in blocks.split("\n") if 'register("machine_electric_furnace"' in l), "")
    check("new MachineElectricFurnaceBlock(" in line and ".strength(5.0F, 10.0F)" in line and ".requiresCorrectToolForDrops()" in line
          and ".lightLevel(state -> state.getValue(MachineElectricFurnaceBlock.LIT) ? 15 : 0)" in line,
          "block machine_electric_furnace: hardness 5, resistance 10, needs the right tool, light 15 while lit (original 5/10, light 1.0 on)")
    check(blocks.count('"machine_electric_furnace') == 1, "one registry id (no _off/_on blocks)")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 10C transcript: {log}", flush=True)
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

    head_anvil = baseline(ANVIL, "com.hbm.inventory.recipes.anvil")
    stubs = build_stubs(SOURCE, [head_anvil])
    overlap = sorted(set(stubs) & set(PRODUCTION))
    if overlap:
        raise SystemExit(f"Production sources shadowed by stand-ins: {overlap}")
    paths = []
    for stub, content in stubs.items():
        path = run_dir / "stubs" / stub
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        paths.append(str(path))
    head = run_dir / "baseline/goal10c/head/AnvilRecipes.java"
    head.parent.mkdir(parents=True)
    head.write_text(head_anvil, encoding="utf-8")
    paths.append(str(head))
    paths.extend(str(SOURCE / source) for source in PRODUCTION)
    paths.extend(str(FIXTURE / fixture) for fixture in FIXTURES)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nanvil baseline: git {BASELINE_COMMIT}:src/main/java/{ANVIL} as goal10c.head.AnvilRecipes\n"
                     "production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))
    classes = run_dir / "classes"
    classes.mkdir()
    # An argument file keeps the command under the Windows length limit when SOURCE is a long temporary copy.
    sources = run_dir / "sources.txt"
    sources.write_text("".join(f'"{Path(path).as_posix()}"\n' for path in paths), encoding="utf-8")
    run("Compile the Goal 10C machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                "-d", str(classes), f"@{sources}"])
    # The Java sections and the Python section both run, so every failing section is reported.
    run("Run Goal 10C regression (sections 1-9)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal10CRegression"],
        stage_failure_ok=True)
    sections = Sections()
    sections.run("10. static resources and registration", static)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 10C Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 10C regression failed: {failed}")


if __name__ == "__main__":
    main()
