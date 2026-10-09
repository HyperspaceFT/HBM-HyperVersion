"""Goal 12B regression: coltan ore and its loot, the coltan shredder entries, the coltan cleaning fix and the niobium chain
recipes, the coltan deposit, the coltan compass, the steel scaffold recipe, the catalytic cracking tower (logic, multiblock,
ports, save/sync, its SerializableRecipe table and assembler recipe) and the rubber and bakelite chains.

Three Java worlds compile real production classes against isolated stand-ins (see goal12b_regression/README.md):

* the shredder world (the Goal 4 shredder world, real Gson, production SerializableRecipe loader) runs section 2 in
  com.hbm.inventory.recipes.loader.Goal12BShredderRegression on the production ShredderRecipes against its 3687da34 copy
  (git show, package goal12b.head);
* the recipe world (the Goal 11D recipe world, real Gson, plus the production CrackingRecipes) runs sections 3, 9 and 10 in
  com.hbm.inventory.recipes.loader.Goal12BRecipeRegression, with ChemicalPlantRecipes and AssemblyMachineRecipes at 3687da34
  (goal12b.head) for the comparisons;
* the machine world (goal12b_regression/stubs.py: the Goal 12A machine world plus the production cracking tower block and
  block entity, CrackingRecipes, ColtanCompassItem and ColtanDepositFeature) runs sections 4, 5, 7, 8, 9m and 11 in
  com.hbm.blockentity.machine.Goal12BRegression.

The Python sections 1, 3p, 6, 9t and 12t read source text, the generated JSON and the original. Every section reports
"N. name: X checks passed"; a failed check prints "AssertionError in <section> ..." and the run fails at the end. Lines
starting with "info:" are observations, not checks.
"""

from pathlib import Path
import json
import re
import subprocess
import sys
import uuid
import zipfile

from goal11c_regression.stubs import shredder_stubs
from goal11d_regression.stubs import SERIALIZABLE, GENERIC_RECIPES, GENERIC_RECIPE, TABLES
from goal12b_regression.stubs import CRACKING, GOAL12B_SOURCES, build_stubs, recipe_stubs
from verify_goal10c import Sections, jdk
from verify_goal12a import PRODUCTION as GOAL12A_PRODUCTION
from verify_goal4_recipes import PRODUCTION as SHREDDER_PRODUCTION
from verify_goal3c_recipes import GSON


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/main/java"
GENERATED = ROOT / "src/generated/resources"
ORIGINAL_ROOT = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
ORIGINAL = ORIGINAL_ROOT / "src/main/java/com/hbm"
FIXTURE = Path(__file__).with_name("goal12b_regression")
FIXTURE11A = Path(__file__).with_name("goal11a_regression")
FIXTURE12A = Path(__file__).with_name("goal12a_regression")
OUTPUT = ROOT / "build/migration/goal12b/regression"
NEOFORGE_SOURCES = ROOT / "build/moddev/artifacts/neoforge-21.1.228-sources.jar"
# Goal 12A, HEAD when Goal 12B started. Pinned, so a later commit of Goal 12B does not move the baseline.
BASELINE_COMMIT = "3687da34"
SHREDDER = "com/hbm/inventory/recipes/ShredderRecipes.java"
CHEM = "com/hbm/inventory/recipes/ChemicalPlantRecipes.java"
ASSEMBLY = "com/hbm/inventory/recipes/AssemblyMachineRecipes.java"
# Not compiled: the renderer and the JEI handler (client-only), the datagen providers (sections 1, 3p and 6 read the
# generated JSON), the registries, NuclearTechModClient (the compass needle property).
PRODUCTION = tuple(dict.fromkeys(list(GOAL12A_PRODUCTION) + list(GOAL12B_SOURCES)))
FIXTURES = (
    "com/hbm/blocks/machine/Goal12BBlockAccess.java",
    "com/hbm/world/feature/Goal12BWorldGen.java",
    "com/hbm/blockentity/machine/Goal12BRegression.java",
)
FIXTURES11A = ("com/hbm/blocks/Goal11ABlockAccess.java", "com/hbm/world/feature/Goal11AWorldGen.java")
FIXTURES12A = ("com/hbm/blockentity/Goal12AProxyAccess.java",)
RECIPE_PRODUCTION = (SERIALIZABLE, GENERIC_RECIPES, GENERIC_RECIPE) + TABLES + (CRACKING,)
RECIPE_FIXTURE = "com/hbm/inventory/recipes/loader/Goal12BRecipeRegression.java"
SHREDDER_FIXTURE = "com/hbm/inventory/recipes/loader/Goal12BShredderRegression.java"


def baseline(path, package, target="goal12b.head"):
    """A committed production source moved to the package `target`; it still sees its own package's classes."""
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASELINE_COMMIT}:src/main/java/{path}"], capture_output=True, check=True)
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    line = f"package {package};\n"
    if text.count(line) != 1:
        raise SystemExit(f"baseline package line not found in {path}")
    return text.replace(line, f"package {target};\nimport {package}.*;\n")


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


# ---- Python section 1: ore and loot ------------------------------------------------------------------------------------

def ore(check):
    blocks = java("blocks/NtmBlocks.java")
    decl = re.search(r'public static final DeferredBlock<Block> ORE_COLTAN = register\("ore_coltan", \(\) -> new Block\(BlockBehaviour\.Properties\.of\(\)(.*?)\)\);', blocks)
    props = decl.group(1) if decl else ""
    check(decl is not None and ".strength(15.0F, 10.0F)" in props and ".requiresCorrectToolForDrops()" in props and ".sound(SoundType.STONE)" in props,
          f"NtmBlocks.ORE_COLTAN: a plain Block, strength 15 / resistance 10, requiresCorrectToolForDrops, stone sound: {props}")
    lines = original("blocks/ModBlocks.java")
    check(line(lines, 1326, 'ore_coltan = new BlockOre(Material.rock).setBlockName("ore_coltan")') and line(lines, 1326, ".setHardness(15.0F).setResistance(10.0F)"),
          "original ModBlocks.java:1326: ore_coltan is a rock BlockOre, hardness 15, resistance 10")
    pickaxe = read_json(GENERATED / "data/minecraft/tags/block/mineable/pickaxe.json")["values"]
    # NEO defines no needs_*_tool tag at all (neither generated nor hand-written), so any pickaxe tier mines the ore.
    needs = sorted(p.relative_to(ROOT).as_posix() for root in (GENERATED, ROOT / "src/main/resources") for p in root.rglob("needs_*_tool.json"))
    tags = java("datagen/NtmBlockTagProvider.java")
    check(pickaxe.count("hbmsntm:ore_coltan") == 1 and not needs and "NEEDS_" not in tags,
          f"ore_coltan is in #minecraft:mineable/pickaxe once and no needs_*_tool tag exists or is provided ({needs}): any pickaxe tier (B3)")
    loot = read_json(GENERATED / "data/hbmsntm/loot_table/blocks/ore_coltan.json")
    pools = loot.get("pools", [])
    entries = pools[0]["entries"] if len(pools) == 1 else []
    children = entries[0].get("children", []) if len(entries) == 1 and entries[0].get("type") == "minecraft:alternatives" else []
    silk = children[0] if len(children) == 2 else {}
    drop = children[1] if len(children) == 2 else {}
    silk_ok = silk.get("name") == "hbmsntm:ore_coltan" and silk.get("conditions") == [{"condition": "minecraft:match_tool", "predicate": {"predicates": {
        "minecraft:enchantments": [{"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}]}}}]
    check(loot.get("type") == "minecraft:block" and pools and pools[0].get("rolls") == 1.0 and silk_ok,
          "loot_table/blocks/ore_coltan.json: one pool, one roll; with silk touch (level >= 1) the ore itself")
    check(drop.get("name") == "hbmsntm:fragment_coltan" and drop.get("functions") == [
        {"add": False, "count": {"type": "minecraft:uniform", "max": 1.0, "min": 1.0}, "function": "minecraft:set_count"},
        {"enchantment": "minecraft:fortune", "formula": "minecraft:ore_drops", "function": "minecraft:apply_bonus"}] and "conditions" not in drop,
          f"otherwise exactly 1 fragment_coltan with the ore_drops fortune bonus: {drop}")
    ore_lines = original("blocks/generic/BlockOre.java")
    check(line(ore_lines, 96, "if(this == ModBlocks.ore_coltan) {") and line(ore_lines, 97, "return ModItems.fragment_coltan;")
          and line(ore_lines, 135, "int mult = rand.nextInt(fortune + 2) - 1;") and line(ore_lines, 136, "return this.quantityDropped(rand) * (Math.max(mult, 0) + 1);"),
          "original BlockOre.java:96-97 (drops the fragment) and :135-136 (fortune: rand(fortune + 2) - 1, at least 0, plus 1 times), vanilla's ore_drops formula")
    provider = java("datagen/NtmBlockLootTableProvider.java")
    check("this.add(NtmBlocks.ORE_COLTAN.get(), block -> this.oreDrop(block, NtmItems.FRAGMENT_COLTAN.get()));" in provider,
          "NtmBlockLootTableProvider uses the vanilla oreDrop for the ore (the generated table above)")


# ---- Python section 3p: the niobium chain recipes ----------------------------------------------------------------------

def chain_recipes(check):
    smelt = recipe("powder_niobium_to_ingot_niobium")
    check(smelt.get("type") == "minecraft:smelting" and smelt.get("ingredient") == {"item": "hbmsntm:powder_niobium"}
          and smelt.get("result") == {"count": 1, "id": "hbmsntm:ingot_niobium"} and smelt.get("experience") == 0.7,
          f"niobium powder smelts into a niobium ingot (0.7 XP): {smelt}")
    smelting = original("crafting/SmeltingRecipes.java")
    check(line(smelting, 106, "GameRegistry.addSmelting(ModItems.powder_niobium, new ItemStack(ModItems.ingot_niobium), 1.0F);"),
          "original SmeltingRecipes.java:106: powder_niobium -> ingot_niobium")
    print("info: niobium smelting XP: NEO 0.7, original 1.0 (SmeltingRecipes.java:106; GOAL12B.md keeps NEO's value)", flush=True)
    block = recipe("block_coltan_from_9_fragment_coltan")
    check(block.get("type") == "minecraft:crafting_shaped" and block.get("pattern") == ["XXX", "XXX", "XXX"] and block.get("key") == {"X": {"item": "hbmsntm:fragment_coltan"}}
          and block.get("result") == {"count": 1, "id": "hbmsntm:block_coltan"}, f"9 coltan fragments -> 1 coltan block: {block}")
    back = recipe("fragment_coltan_from_block_coltan")
    check(back.get("type") == "minecraft:crafting_shapeless" and back.get("ingredients") == [{"item": "hbmsntm:block_coltan"}]
          and back.get("result") == {"count": 9, "id": "hbmsntm:fragment_coltan"}, f"1 coltan block -> 9 coltan fragments: {back}")
    check(line(original("crafting/MineralRecipes.java"), 47, "add1To9Pair(ModBlocks.block_coltan, ModItems.fragment_coltan);"),
          "original MineralRecipes.java:47: the coltan block pairs with the fragment (B2)")
    retired = ["block_coltan_from_9_powder_coltan", "powder_coltan_from_block_coltan"]
    check(not any((GENERATED / f"data/hbmsntm/recipe/{n}.json").exists() for n in retired)
          and not any(list(GENERATED.joinpath("data/hbmsntm/advancement/recipes").rglob(f"{n}.json")) for n in retired),
          "the two purified tantalite block recipes and their advancements are gone")
    tool = recipe("coltan_tool")
    check(tool.get("type") == "minecraft:crafting_shaped" and tool.get("pattern") == ["ACA", "CXC", "ACA"]
          and tool.get("key") == {"A": [{"item": "hbmsntm:ingot_copper"}, {"item": "minecraft:copper_ingot"}], "C": {"item": "hbmsntm:cinnabar"}, "X": {"item": "minecraft:compass"}}
          and tool.get("result") == {"count": 1, "id": "hbmsntm:coltan_tool"},
          f"coltan_tool: ACA / CXC / ACA, A either copper ingot, C cinnabar, X compass -> 1: {tool}")
    check(line(original("crafting/ToolRecipes.java"), 120, "new ItemStack(ModItems.coltan_tool, 1), new Object[] { \"ACA\", \"CXC\", \"ACA\", 'A', CU.ingot(), 'C', CINNABAR.crystal(), 'X', Items.compass }"),
          "original ToolRecipes.java:120: ACA / CXC / ACA with a copper ingot, cinnabar, a compass")
    chem = original("inventory/recipes/ChemicalPlantRecipes.java")
    check(line(chem, 312, ".inputItems(new OreDictStack(COLTAN.dust(), 2), new OreDictStack(COAL.dust()))")
          and line(chem, 313, ".inputFluids(new FluidStack(Fluids.PEROXIDE, 250), new FluidStack(Fluids.HYDROGEN, 500))")
          and line(chem, 314, ".outputItems(new ItemStack(ModItems.powder_coltan), new ItemStack(ModItems.powder_niobium), new ItemStack(ModItems.dust))")
          and line(chem, 315, ".outputFluids(new FluidStack(Fluids.WATER, 500)));") and line(chem, 311, '"chem.coltancleaning").setup(60, 100)'),
          "original ChemicalPlantRecipes.java:311-315: chem.coltancleaning as section 3 expects")
    oredict = original("inventory/OreDictManager.java")
    check(any("COLTAN" in l and "powder_coltan_ore" in l and "fragment_coltan" in l for l in oredict[390:400]),
          "original OreDictManager.java (~395): COLTAN's dust is powder_coltan_ore and its ingot the fragment")
    hazard = java("hazard/HazardRegistry.java")
    check("HazardSystem.register(item(POWDER_COLTAN_ORE), makeData(ASBESTOS, 3F));" in hazard
          and any("powder_coltan_ore" in l and "asbestos" in l.lower() and "3" in l for l in original("hazard/HazardRegistry.java")[478:486]),
          "crushed coltan ore carries asbestos 3, as the original (HazardRegistry.java:482, B6)")


# ---- Python section 6: steel scaffold ----------------------------------------------------------------------------------

def scaffold(check):
    s = recipe("steel_scaffold")
    check(s.get("type") == "minecraft:crafting_shaped" and s.get("pattern") == ["SSS", " S ", "SSS"] and s.get("key") == {"S": {"item": "hbmsntm:ingot_steel"}}
          and s.get("result") == {"count": 8, "id": "hbmsntm:steel_scaffold"}, f"steel_scaffold: SSS / ' S ' / SSS of steel ingots -> 8: {s}")
    check(line(original("main/CraftingManager.java"), 462, 'addRecipeAuto(new ItemStack(Item.getItemFromBlock(ModBlocks.steel_scaffold), 8), new Object[] { "SSS", " S ", "SSS", \'S\', STEEL.ingot() });'),
          "original CraftingManager.java:462: 7 steel ingots -> 8 steel scaffolds")
    adv = read_json(GENERATED / "data/hbmsntm/advancement/recipes/building_blocks/steel_scaffold.json")
    check(adv.get("rewards") == {"recipes": ["hbmsntm:steel_scaffold"]} and "has_steel_ingot" in adv.get("criteria", {}), "the scaffold recipe unlocks with a steel ingot")


# ---- Python section 9t: handler registration --------------------------------------------------------------------------

def registration(check):
    text = java("inventory/recipes/loader/SerializableRecipe.java")
    start = text.index("public static void registerAllHandlers() {")
    body = text[start:text.index("}", start)]
    adds = re.findall(r"recipeHandlers\.add\((.*?)\);", body)
    # Goal 13B registers ArcFurnaceRecipes directly after CrackingRecipes; one added check requires that and the comparisons below skip it.
    check(adds.count("new ArcFurnaceRecipes()") == 1 and adds.index("new ArcFurnaceRecipes()") == adds.index("new CrackingRecipes()") + 1,
          f"Goal 13B: registerAllHandlers adds one ArcFurnaceRecipes directly after CrackingRecipes: {adds}")
    adds = [a for a in adds if a != "new ArcFurnaceRecipes()"]
    check(adds.count("new CrackingRecipes()") == 1, f"registerAllHandlers adds one CrackingRecipes: {adds}")
    i = adds.index("new CrackingRecipes()")
    check(adds[i - 1] == "new CentrifugeRecipes()" and adds[i + 1] == "AssemblyMachineRecipes.INSTANCE" and all(not a.endswith(".INSTANCE") for a in adds[:i]),
          f"it is registered directly after CentrifugeRecipes and before the generic tables (AssemblyMachineRecipes.INSTANCE first): {adds}")
    check(body.index("new CrackingRecipes()") < body.index("//GENERIC"), "it sits above the //GENERIC comment")
    orig = original("inventory/recipes/loader/SerializableRecipe.java")
    check(line(orig, 59, "recipeHandlers.add(new CentrifugeRecipes());") and line(orig, 64, "recipeHandlers.add(new CrackingRecipes());"),
          "original SerializableRecipe.java:59 and :64: the original registers CrackingRecipes after CentrifugeRecipes too (with tables NEO lacks between them)")
    cracking = java("inventory/recipes/CrackingRecipes.java")
    check('writer.name("input").value(rec.getKey().getInternalName());' in cracking and "FluidType input = Fluids.fromName(obj.get(\"input\").getAsString());" in cracking,
          "CrackingRecipes writes the input by internal name and reads it with Fluids.fromName (sections 9 round trip)")


# ---- Python section 12t: the original numbers the Java fixtures transcribe ------------------------------------------------

def references(check):
    world = original("lib/HbmWorldGen.java")
    check(line(world, 153, "Random colRand = new Random(world.getSeed() + 5);") and line(world, 154, "int colX = (int) (colRand.nextGaussian() * 1500);")
          and line(world, 155, "int colZ = (int) (colRand.nextGaussian() * 1500);") and line(world, 156, "int colRange = 750;")
          and line(world, 159, "for(int k = 0; k < 2; k++) {") and line(world, 161, "for(int r = 1; r <= 5; r++) {")
          and line(world, 162, "int randPosX = i + rand.nextInt(16);") and line(world, 163, "int randPosY = rand.nextInt(25) + 15;")
          and line(world, 164, "int randPosZ = j + rand.nextInt(16);") and line(world, 166, "int range = colRange / r;")
          and line(world, 168, "if(randPosX <= colX + range && randPosX >= colX - range && randPosZ <= colZ + range && randPosZ >= colZ - range) {")
          and line(world, 169, "(new WorldGenMinable(ModBlocks.ore_coltan, 4)).generate(world, rand, randPosX, randPosY, randPosZ);"),
          "original HbmWorldGen.java:153-169: the deposit centre and tries section 4 replays")
    compass = original("items/tool/ItemColtanCompass.java")
    check(line(compass, 47, 'MainRegistry.proxy.displayTooltip(((int) vec.lengthVector()) + "m", MainRegistry.proxy.ID_COMPASS);')
          and line(compass, 56, "if(!stack.hasTagCompound()) {") and line(compass, 59, "Random colRand = new Random(world.getSeed() + 5);"),
          "original ItemColtanCompass.java:46-47 (the distance line) and :56-64 (the centre written once)")
    te = original("tileentity/machine/oil/TileEntityMachineCatalyticCracker.java")
    check(line(te, 28, "tanks[0] = new FluidTank(Fluids.BITUMEN, 4000);") and line(te, 29, "tanks[1] = new FluidTank(Fluids.STEAM, 8000);")
          and line(te, 30, "tanks[2] = new FluidTank(Fluids.OIL, 4000);") and line(te, 31, "tanks[3] = new FluidTank(Fluids.PETROLEUM, 4000);")
          and line(te, 32, "tanks[4] = new FluidTank(Fluids.SPENTSTEAM, 800);") and line(te, 45, "if(worldObj.getTotalWorldTime() % 5 == 0) crack();")
          and line(te, 47, "networkPackNT(25);") and line(te, 72, "for(int i = 0; i < 2; i++) {")
          and line(te, 73, "if(tanks[0].getFill() >= 100 && tanks[1].getFill() >= 200 && hasSpace(left, right)) {")
          and line(te, 78, "tanks[4].setFill(tanks[4].getFill() + 2);")
          and line(te, 85, "return tanks[2].getFill() + left <= tanks[2].getMaxFill() && tanks[3].getFill() + right <= tanks[3].getMaxFill() && tanks[4].getFill() + 2 <= tanks[4].getMaxFill();")
          and line(te, 98, "tanks[2].setTankType(Fluids.NONE);") and line(te, 109, 'tanks[i].readFromNBT(nbt, "tank" + i);')
          and line(te, 125, "ForgeDirection rot = dir.getRotation(ForgeDirection.UP);")
          and line(te, 128, "PortDef.make(xCoord + dir.offsetX * 3 + rot.offsetX * 1, yCoord, zCoord + dir.offsetZ * 3 + rot.offsetZ * 1, dir),")
          and line(te, 135, "PortDef.make(xCoord - dir.offsetX * 2 - rot.offsetX * 3, yCoord, zCoord - dir.offsetZ * 2 - rot.offsetZ * 3, rot.getOpposite()),")
          and line(te, 168, "return new FluidTank[] {tanks[2], tanks[3], tanks[4]};") and line(te, 173, "return new FluidTank[] {tanks[0], tanks[1]};"),
          "original TileEntityMachineCatalyticCracker.java: the tanks, the 5-tick interval, the two loops, the space test, NONE outputs, tank0..4, the ports, send/receive")
    port = original("tileentity/TilePort.java")
    check(line(port, 204, "cons[i] = new DirPos(x + dirs[i].offsetX, y + dirs[i].offsetY, z + dirs[i].offsetZ, dirs[i]);"),
          "original TilePort.java:204: a PortDef's connection is one block from the port in its direction")
    block = original("blocks/machine/MachineCatalyticCracker.java")
    check(line(block, 45, "return new int[] {0, 0, 3, 3, 2, 3};") and line(block, 50, "return 3;") and line(block, 56, "new int[]{8, -1, 3, -1, 2, 0},")
          and line(block, 57, "new int[]{13, 0, 0, 3, 2, 1},") and line(block, 58, "new int[]{14, -13, -1, 2, 1, 0},") and line(block, 59, "new int[]{3, -1, 2, 3, -1, 3}")
          and line(block, 38, "return new TileEntityProxyCombo(false, false, true);"),
          "original MachineCatalyticCracker.java: dimensions, offset 3, the four extra boxes, fluid-only proxies")
    xr = "\n".join(original("handler/MultiblockHandlerXR.java"))
    check("return new int[] { dim[0], dim[1], dim[3], dim[2], dim[5], dim[4] };" in xr and "return new int[] { dim[0], dim[1], dim[5], dim[4], dim[2], dim[3] };" in xr
          and "return new int[] { dim[0], dim[1], dim[4], dim[5], dim[3], dim[2] };" in xr and "if(dir == ForgeDirection.SOUTH) return dim;" in xr
          and "for(int a = x - rot[4]; a <= x + rot[5]; a++) {" in xr and "for(int b = y - rot[1]; b <= y + rot[0]; b++) {" in xr
          and "for(int c = z - rot[2]; c <= z + rot[3]; c++) {" in xr,
          "original MultiblockHandlerXR rotate and fill loops (section 8 transcribes them)")
    table = "\n".join(original("inventory/recipes/CrackingRecipes.java"))
    rows = re.findall(r"cracking\.put\(Fluids\.(\w+),\s*new Pair\(new FluidStack\(Fluids\.(\w+),\s*(\w+)\),\s*new FluidStack\(Fluids\.(\w+),\s*(\w+)\)\)\);", table)
    consts = dict(re.findall(r"public static final int (\w+) = (\d+);", table))
    values = [(a, b, int(consts.get(c, c)), d, int(consts.get(e, e))) for a, b, c, d, e in rows]
    expected = [("OIL", "CRACKOIL", 80, "PETROLEUM", 20), ("BITUMEN", "OIL", 80, "AROMATICS", 20), ("SMEAR", "NAPHTHA", 60, "PETROLEUM", 40),
                ("GAS", "PETROLEUM", 30, "UNSATURATEDS", 20), ("DIESEL", "KEROSENE", 40, "PETROLEUM", 30), ("DIESEL_CRACK", "KEROSENE", 40, "PETROLEUM", 30),
                ("KEROSENE", "PETROLEUM", 60, "NONE", 0), ("WOODOIL", "HEATINGOIL", 40, "AROMATICS", 10), ("XYLENE", "AROMATICS", 80, "PETROLEUM", 20),
                ("HEATINGOIL_VACUUM", "HEATINGOIL", 80, "REFORMGAS", 20), ("REFORMATE", "UNSATURATEDS", 40, "REFORMGAS", 60), ("BIOGAS", "PETROLEUM", 20, "AROMATICS", 20)]
    check(values == expected, f"original CrackingRecipes.java:41-55: the 12 defaults section 7 expects: {values}")
    refinery = original("inventory/recipes/RefineryRecipes.java")
    fluids = original("inventory/fluid/Fluids.java")
    plant = original("inventory/recipes/ChemicalPlantRecipes.java")
    check(line(refinery, 30, "crack_frac_naph = 40") and line(refinery, 31, "crack_frac_light = 30") and line(refinery, 32, "crack_frac_aroma = 15")
          and line(refinery, 33, "crack_frac_unsat = 15")
          and line(fluids, 641, "CRACKOIL.addTraits(new FT_Heatable().setEff(HeatingType.BOILER, 1.0D).setEff(HeatingType.HEATEXCHANGER, 1.0D).addStep(10, 1, HOTCRACKOIL, 1));")
          and line(plant, 214, '"chem.bakelite").setup(100, 100)') and line(plant, 215, "new FluidStack(Fluids.AROMATICS, 500") and line(plant, 215, "new FluidStack(Fluids.PETROLEUM, 500")
          and line(plant, 216, ".outputItems(new ItemStack(ModItems.ingot_bakelite)));") and line(plant, 218, '"chem.rubber").setup(100, 200)')
          and line(plant, 219, ".inputItems(new OreDictStack(S.dust()))") and line(plant, 220, "new FluidStack(Fluids.UNSATURATEDS, 500")
          and line(plant, 221, ".outputItems(new ItemStack(ModItems.ingot_rubber, 2)));"),
          "original RefineryRecipes.java:30-33 (hot cracked oil fractions), Fluids.java:641 (cracked oil heating), ChemicalPlantRecipes.java:214-221 (bakelite, rubber)")
    assembly = original("inventory/recipes/AssemblyMachineRecipes.java")
    check(line(assembly, 316, 'new GenericRecipe("ass.crackingtower").setup(200, 100).outputItems(new ItemStack(ModBlocks.machine_catalytic_cracker, 1))')
          and line(assembly, 317, ".inputItems(new ComparableStack(ModBlocks.steel_scaffold, 16), new OreDictStack(STEEL.shell(), 6), new OreDictStack(DESH.ingot(), 12), new OreDictStack(NB.ingot(), 4))"),
          "original AssemblyMachineRecipes.java:316-317: ass.crackingtower as section 10 expects")


def main():
    java_bin, javac = jdk()
    run_dir = OUTPUT / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log = run_dir / "result.log"
    print(f"Goal 12B transcript: {log}", flush=True)
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
        stream.write(f"jdk: {java_bin}\nsource: {SOURCE}\nbaseline: git {BASELINE_COMMIT} (package goal12b.head)\n"
                     "machine world production sources:\n" + "".join(f"  {source}\n" for source in PRODUCTION))

    # ---- Shredder world (section 2) ----
    head_shredder = baseline(SHREDDER, "com.hbm.inventory.recipes")
    shredder_fixture = (FIXTURE / SHREDDER_FIXTURE).read_text(encoding="utf-8")
    sstubs = shredder_stubs(SOURCE, head_shredder, shredder_fixture)
    refuse_shadowing(sstubs, SHREDDER_PRODUCTION, "shredder")
    sstubs["goal12b/head/ShredderRecipes.java"] = head_shredder
    shredder = run_dir / "shredder"
    ssources, sclasses = write_sources(shredder, sstubs, [SOURCE / p for p in SHREDDER_PRODUCTION] + [FIXTURE / SHREDDER_FIXTURE])
    run("Compile the Goal 12B shredder world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                                "-cp", str(GSON), "-d", str(sclasses), f"@{ssources}"])
    config = shredder / "scratch-config"
    config.mkdir()
    run("Run Goal 12B shredder world (section 2)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{sclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal12BShredderRegression", str(config)],
        stage_failure_ok=True)

    # ---- Recipe world (sections 3, 9, 10) ----
    head_chem = baseline(CHEM, "com.hbm.inventory.recipes")
    head_assembly = baseline(ASSEMBLY, "com.hbm.inventory.recipes")
    recipe_fixture = (FIXTURE / RECIPE_FIXTURE).read_text(encoding="utf-8")
    rstubs = recipe_stubs(SOURCE, [recipe_fixture])
    refuse_shadowing(rstubs, RECIPE_PRODUCTION, "recipe")
    rstubs["goal12b/head/ChemicalPlantRecipes.java"] = head_chem
    rstubs["goal12b/head/AssemblyMachineRecipes.java"] = head_assembly
    recipes = run_dir / "recipes"
    rsources, rclasses = write_sources(recipes, rstubs, [SOURCE / p for p in RECIPE_PRODUCTION] + [FIXTURE / RECIPE_FIXTURE])
    run("Compile the Goal 12B recipe world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn",
                                              "-cp", str(GSON), "-d", str(rclasses), f"@{rsources}"])
    run("Run Goal 12B recipe world (sections 3, 9, 10)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", f"{rclasses};{GSON}", "com.hbm.inventory.recipes.loader.Goal12BRecipeRegression",
         str(recipes / "templates")], stage_failure_ok=True)

    # ---- Machine world (sections 4, 5, 7, 8, 9m, 11) ----
    with zipfile.ZipFile(NEOFORGE_SOURCES) as jar:
        vanilla_tags = jar.read("net/minecraft/data/tags/VanillaBlockTagsProvider.java").decode("utf-8")
    fixture_texts = [(FIXTURE / p).read_text(encoding="utf-8") for p in FIXTURES]
    stubs = build_stubs(SOURCE, fixture_texts, vanilla_tags, NEOFORGE_SOURCES)
    refuse_shadowing(stubs, PRODUCTION, "machine")
    machine = run_dir / "machine"
    sources, classes = write_sources(machine, stubs, [SOURCE / p for p in PRODUCTION] + [FIXTURE11A / p for p in FIXTURES11A]
                                     + [FIXTURE12A / p for p in FIXTURES12A] + [FIXTURE / p for p in FIXTURES])
    run("Compile the Goal 12B machine world", [str(javac), "-J-Duser.language=en", "-encoding", "UTF-8", "-nowarn", "-d", str(classes), f"@{sources}"])
    run("Run Goal 12B machine world (sections 4, 5, 7, 8, 9m, 11)",
        [str(java_bin), "-Duser.language=en", "-ea", "-cp", str(classes), "com.hbm.blockentity.machine.Goal12BRegression"], stage_failure_ok=True)

    sections = Sections()
    sections.run("1. ore and loot", ore)
    sections.run("3p. niobium chain recipes", chain_recipes)
    sections.run("6. steel scaffold", scaffold)
    sections.run("9t. handler registration", registration)
    sections.run("12t. original references", references)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"== Python sections ==\nchecks: {sections.total}\nfailures: {sections.failures}\n")
    print(f"Goal 12B Python sections: {sections.total} checks passed", flush=True)
    if sections.failures:
        failed.append("Python sections")
    if failed:
        raise SystemExit(f"Goal 12B regression failed: {failed}")


if __name__ == "__main__":
    main()
