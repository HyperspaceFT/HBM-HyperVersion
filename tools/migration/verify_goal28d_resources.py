"""Verify the Goal28D batch statically: the vacuum refinery, the rotary furnace, the mustard willow, the oily scraps, the acidizer wax rows, the
assembly and anvil rows of the original 4f5924e2b against NEO's constants and tables, the generated JSON, the language files, the ownership record, the
GameTest source and, with --gametest-log, the GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal28d/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD 4f5924e2b with a clean status, every file read below present.
- V1  The original at the cited lines: TileEntityMachineVacuumDistill.java:36-51,155-174; VacuumRefineryRecipes.java:19-41; MachineVacuumDistill.java:52-53;
      TileEntityMachineRotaryFurnace.java:58,67-82,174-223; RotaryFurnaceRecipes.java:39-54; MachineRotaryFurnace.java:38-39; BlockNTMFlower.java:135-203;
      BlockTallPlant.java:150-160,225-284,343-350; OilSpot.java:55-70; ShredderRecipes.java:302-307; CrystallizerRecipes.java:108-109,212-214,324-349;
      AssemblyMachineRecipes.java:81-82,129-130,327-328; AnvilRecipes.java:60-70,322-331; FuelHandler.java:17-27; MixerRecipes.java:63; FractionRecipes.java:38;
      OutgasserRecipes.java:62. A moved line fails.
- V2  NEO source against the original: fractions, power and input constants, tanks, rotary rows (the recorded omissions are the three iron fragment steel rows,
      the weapon steel row and the titanium row), the crop growth conditions, the oil spot odds, the shredder rows (stone_porous has no NEO block), the cadmium,
      arsenic and wax rows, the three assembly rows, the saturnite anvil upgrades and the rotary furnace construction row.
- V3  Generated JSON: the willow loot table, blockstates and models, the machine loot tables, the bismoid nugget tag.
- V4  Language: en_us and zh_cn values of the 28D keys against the original English and Chinese and the reviewed mapping.
- V5  migration/goal28d-resource-ownership.json: the imported files' SHA-256 in NEO and in the original.
- V6  GameTest source: the test names, one batch each, the original numbers asserted. V7 (--gametest-log) the log. V8 (--jar) the JAR.
- V9  In-memory mutations of the NEO inputs and the original text (never written); each must make a check of the named section fail.

python -B -X utf8 tools/migration/verify_goal28d_resources.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
OUT = ROOT / "build/migration/goal28d/verify"
ORIGINAL_HEAD = "4f5924e2b9e1e49cee61787674d2658acb3d559b"

O = "src/main/java/com/hbm/"
OR = "src/main/resources/assets/hbm/"
J = "src/main/java/com/hbm/"
GEN = "src/generated/resources/"
GT = J + "gametest/ResourceCompletionGameTests.java"
OWNERSHIP = "migration/goal28d-resource-ownership.json"
ZHMAP = "migration/localization/zh_cn-map.json"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
EN = GEN + "assets/hbmsntm/lang/en_us.json"

ORIG_FILES = dict(
    tevd=O + "tileentity/machine/oil/TileEntityMachineVacuumDistill.java", vrr=O + "inventory/recipes/VacuumRefineryRecipes.java",
    mvd=O + "blocks/machine/MachineVacuumDistill.java", terf=O + "tileentity/machine/TileEntityMachineRotaryFurnace.java",
    rfr=O + "inventory/recipes/RotaryFurnaceRecipes.java", mrf=O + "blocks/machine/MachineRotaryFurnace.java", flower=O + "blocks/generic/BlockNTMFlower.java",
    tall=O + "blocks/generic/BlockTallPlant.java", oil=O + "world/feature/OilSpot.java", shred=O + "inventory/recipes/ShredderRecipes.java",
    cryst=O + "inventory/recipes/CrystallizerRecipes.java", amr=O + "inventory/recipes/AssemblyMachineRecipes.java", anvil=O + "inventory/recipes/anvil/AnvilRecipes.java",
    fuel=O + "handler/FuelHandler.java", mixer=O + "inventory/recipes/MixerRecipes.java", frac=O + "inventory/recipes/FractionRecipes.java",
    outg=O + "inventory/recipes/OutgasserRecipes.java", en=OR + "lang/en_US.lang", zh=OR + "lang/zh_CN.lang")
NEO_FILES = dict(
    vrr=J + "inventory/recipes/VacuumRefineryRecipes.java", vbe=J + "blockentity/machine/oil/MachineVacuumDistillBlockEntity.java",
    vblock=J + "blocks/machine/MachineVacuumDistillBlock.java", rbe=J + "blockentity/machine/MachineRotaryFurnaceBlockEntity.java",
    rblock=J + "blocks/machine/MachineRotaryFurnaceBlock.java", rfr=J + "inventory/recipes/RotaryFurnaceRecipes.java", willow=J + "blocks/generic/MustardWillowBlock.java",
    oil=J + "world/feature/OilSpot.java", shred=J + "inventory/recipes/ShredderRecipes.java", cryst=J + "inventory/recipes/CrystallizerRecipes.java",
    amr=J + "inventory/recipes/AssemblyMachineRecipes.java", anvil=J + "inventory/recipes/anvil/AnvilRecipes.java", items=J + "items/NtmItems.java",
    gt=GT, loot=GEN + "data/hbmsntm/loot_table/blocks/plant_mustard_willow.json", blockstate=GEN + "assets/hbmsntm/blockstates/plant_mustard_willow.json",
    bismoid=GEN + "data/ntm/tags/item/nuggets_bismoid.json", enjson=EN, zhjson=ZH, zhmap=ZHMAP, ownership=OWNERSHIP,
    tagprov=J + "datagen/NtmItemTagProvider.java")
MACHINE_LOOT = [GEN + "data/hbmsntm/loot_table/blocks/machine_vacuum_distill.json", GEN + "data/hbmsntm/loot_table/blocks/machine_rotary_furnace.json"]
WILLOW_MODELS = [GEN + f"assets/hbmsntm/models/block/plant_mustard_willow_{n}.json"
                 for n in ("cd0", "cd1", "cd2_lower", "cd2_upper", "cd3_lower", "cd3_upper", "cd4_lower", "cd4_upper")]

GT_MARK = "[hbm-28d]"
START_GAMETESTS = 338
GT_TESTS = ("vacuum_refinery_process", "vacuum_refinery_gates", "vacuum_refinery_save_pressure", "rotary_furnace_table", "rotary_furnace_saturnite", "rotary_solid_fuel_item",
            "rotary_furnace_steel_and_fuel", "rotary_furnace_limits", "rotary_furnace_pour", "rotary_furnace_save", "mustard_willow_growth", "mustard_willow_break_and_loot",
            "oil_spot_willows", "scrap_and_solvent_rows", "crystallizer_cadmium_arsenic", "crystallizer_wax", "assembly_and_anvil_rows", "items_and_tags")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(text):
    return re.sub(r"\s+", " ", text)


def lf(text):
    return text.replace("\r\n", "\n")


def code(text):
    """Java text without // and /* */ comments (the checked files hold no // inside string literals)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:1500]))
        return ok

    def pending(self, cid, label, detail=""):
        self.items.append(dict(id=cid, status="PENDING", label=label, detail=str(detail)[:600]))

    def failed(self):
        return [i["id"] for i in self.items if i["status"] == "FAIL"]

    def passed(self):
        return sum(1 for i in self.items if i["status"] == "PASS")

    def pendings(self):
        return [i["id"] for i in self.items if i["status"] == "PENDING"]


def guarded(ck, section, function, *args):
    """A crash in a section is a failing check (id <section>.crash), never an aborted run."""
    try:
        return function(ck, *args)
    except Exception as error:  # noqa: BLE001 - reported as a check
        ck(f"{section}.crash", False, f"{section} raised {type(error).__name__}", repr(error))
        return None


class State:
    """The text of every input: NEO files under their path, the original under 'o:<key>' ; mutations edit a copy."""

    def __init__(self):
        self.text = {}
        self.raw = {}
        self.log = None
        self.git = {}

    def copy(self):
        other = State()
        other.text, other.raw, other.log, other.git = dict(self.text), self.raw, self.log, self.git
        return other


def read_text(path):
    try:
        return lf(Path(path).read_bytes().decode("utf-8", errors="replace"))
    except OSError:
        return None


def collect():
    st = State()
    for key, rel in ORIG_FILES.items():
        st.text["o:" + key] = read_text(ORIGINAL / rel)
    for key, rel in NEO_FILES.items():
        st.text[key] = read_text(ROOT / rel)
    for rel in MACHINE_LOOT + WILLOW_MODELS:
        st.text[rel] = read_text(ROOT / rel)
    run = lambda *a: subprocess.run(["git", "-C", str(ORIGINAL), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    st.git = dict(head=run("rev-parse", "HEAD"), status=run("status", "--porcelain"))
    return st


def rep1(text, old, new):
    assert text.count(old) == 1, f"{old[:70]!r} found {text.count(old)} times"
    return text.replace(old, new)


def statement(text, name):
    """The register statement of a GenericRecipe, from its register call to the first semicolon."""
    start = text.find(f'new GenericRecipe("{name}")')
    if start < 0:
        return None
    start = text.rfind("this.register(", 0, start)
    return norm(text[start:text.index(";", start) + 1])


def has(ck, cid, label, text, *snippets):
    """Every snippet occurs in the whitespace-normalised text."""
    if text is None:
        return ck(cid, False, label, "text missing")
    t = norm(text)
    missing = [s for s in snippets if norm(s) not in t]
    return ck(cid, not missing, label, f"missing {missing}")


def anchor(ck, cid, st, key, first, last, *snippets):
    """Each snippet sits within the cited original lines."""
    text = st.text.get("o:" + key)
    if text is None:
        return ck(cid, False, f"{ORIG_FILES[key]}:{first}-{last}", "file missing")
    window = norm("\n".join(text.split("\n")[first - 1:last]))
    missing = [s for s in snippets if norm(s) not in window]
    return ck(cid, not missing, f"{ORIG_FILES[key].rsplit('/', 1)[-1]}:{first}-{last} holds {len(snippets)} expected fragment(s)", f"missing {missing} in {window[:300]}")


# ---------------------------------------------------------------- the expected tables (derived from the original text in V1, compared with NEO in V2)

# original rotary furnace rows NEO registers: (material, ingot quanta, duration, steam, fluid, fluid amount, original tokens, NEO tokens)
ROT_ROWS = [
    ("MAT_STEEL", 1, 100, 100, None, 0, ["IRON.ingot()", "COAL.gem()"], ["Items.IRON_INGOT", "Items.COAL"]),
    ("MAT_STEEL", 1, 100, 100, None, 0, ["IRON.ingot()", "ANY_COKE.gem()"], ["Items.IRON_INGOT", "coke"]),
    ("MAT_DESH", 1, 100, 200, "LIGHTOIL", 100, ["powder_desh_ready"], ["POWDER_DESH_READY.get()"]),
    ("MAT_GUNMETAL", 4, 200, 100, None, 0, ["CU.ingot(), 3", "AL.ingot(), 1"], ["copper", "INGOT_ALUMINIUM.get(), 1"]),
    ("MAT_SATURN", 2, 200, 400, "REFORMGAS", 250, ["DURA.dust(), 4", "CU.dust()"], ["POWDER_DURA_STEEL.get(), 4", "POWDER_COPPER.get()"]),
    ("MAT_SATURN", 4, 200, 300, "REFORMGAS", 250, ["DURA.dust(), 4", "CU.dust()", "BORAX.dust()"], ["POWDER_DURA_STEEL.get(), 4", "POWDER_COPPER.get()", "POWDER_BORAX.get()"]),
    ("MAT_ALUMINIUM", 2, 100, 400, "SODIUM_ALUMINATE", 150, [], []),
    ("MAT_ALUMINIUM", 3, 40, 200, "SODIUM_ALUMINATE", 150, ["powder_flux, 2"], ["POWDER_FLUX.get(), 2"]),
]
ROT_OMITTED = [("MAT_STEEL", 2, 200, 25), ("MAT_STEEL", 3, 200, 25), ("MAT_STEEL", 4, 400, 25), ("MAT_WEAPONSTEEL", 1, 200, 400), ("MAT_TITANIUM", 4, 40, 100)]

# shredder: original block -> NEO block
SHRED = [("dirt_dead", "DIRT_DEAD"), ("dirt_oily", "DIRT_OILY"), ("sand_dirty", "SAND_OILY"), ("sand_dirty_red", "SAND_RED_OILY"), ("stone_cracked", "STONE_CRACKED")]

# NEO key -> (original key, kind of the original text)
LANG = {"block.hbmsntm.machine_vacuum_distill": "tile.machine_vacuum_distill.name", "block.hbmsntm.machine_rotary_furnace": "tile.machine_rotary_furnace.name",
        "block.hbmsntm.plant_mustard_willow": "tile.plant_flower.cd0.name", "block.hbmsntm.plant_mustard_willow.mature": "tile.plant_tall.cd4.name",
        "item.hbmsntm.plant_item_mustardwillow": "item.plant_item.mustardwillow.name", "item.hbmsntm.scrap_oil": "item.scrap_oil.name", "item.hbmsntm.plate_mixed": "item.plate_mixed.name",
        "item.hbmsntm.oil_tar_wax": "item.oil_tar.wax.name", "container.vacuumDistill": "container.vacuumDistill", "container.machineRotaryFurnace": "container.machineRotaryFurnace"}


def v0_inputs(ck, st):
    ck("V0.original_head", st.git.get("head") == ORIGINAL_HEAD, "the original is at 4f5924e2b", st.git.get("head"))
    ck("V0.original_clean", st.git.get("status") == "", "the original worktree is clean", st.git.get("status", "")[:300])
    missing = [k for k, v in st.text.items() if v is None]
    ck("V0.files", not missing, "every input file is present", missing[:10])


def v1_original(ck, st):
    anchor(ck, "V1.vac_power", st, "tevd", 36, 36, "maxPower = 1_000_000")
    anchor(ck, "V1.vac_tanks", st, "tevd", 46, 52, "new FluidTank(Fluids.OIL, 64_000).withPressure(2)", "new FluidTank(Fluids.HEAVYOIL_VACUUM, 24_000)", "new FluidTank(Fluids.REFORMATE, 24_000)",
           "new FluidTank(Fluids.LIGHTOIL_VACUUM, 24_000)", "new FluidTank(Fluids.SOURGAS, 24_000)")
    anchor(ck, "V1.vac_refine", st, "tevd", 155, 174, "tanks[i].setTankType(Fluids.NONE)", "if(power < 10_000) return;", "if(tanks[0].getFill() < 100) return;",
           "tanks[i + 1].getFill() + stacks[i].fill > tanks[i + 1].getMaxFill()", "power -= 10_000;", "tanks[0].setFill(tanks[0].getFill() - 100);")
    anchor(ck, "V1.vac_recipes", st, "vrr", 19, 41, "vac_frac_heavy = 40", "vac_frac_reform = 25", "vac_frac_light = 20", "vac_frac_sour = 15",
           "recipes.put(Fluids.OIL, new VacuumRefineryRecipe(", "recipes.put(Fluids.OIL_DS, new VacuumRefineryRecipe(", "new FluidStack(Fluids.SOURGAS, vac_frac_sour)", "new FluidStack(Fluids.REFORMGAS, vac_frac_sour)")
    anchor(ck, "V1.vac_dims", st, "mvd", 52, 53, "return new int[] {8, 0, 1, 1, 1, 1};")
    anchor(ck, "V1.rot_consts", st, "terf", 58, 58, "maxOutput = MaterialShapes.BLOCK.q(16)")
    anchor(ck, "V1.rot_burn", st, "terf", 67, 82, ".setCokeTimeMod(1.25)", ".setRocketTimeMod(1.5)", ".setSolidTimeMod(1.5)", ".setSolidHeatMod(1.5)", "new FluidTank(Fluids.NONE, 16_000)", "new FluidTank(Fluids.STEAM, 12_000)",
           "new FluidTank(Fluids.SPENTSTEAM, 120)")
    anchor(ck, "V1.rot_tick", st, "terf", 174, 223, "burnModule.getBurnTime(slots[4]) / 2", "float steamUseMult = (float)(10 * Math.log10(processSpeed) + 1);", "this.progress += processSpeed / recipe.duration;",
           "tanks[1].setFill((int) (tanks[1].getFill() - recipe.steam * steamUseMult));", "steamUsed += recipe.steam * steamUseMult;", "int steamReturn = this.steamUsed / 100;")
    anchor(ck, "V1.rot_dims", st, "mrf", 38, 39, "return new int[] {4, 0, 1, 1, 2, 2};")
    rows = [m for m in re.finditer(r"recipes\.add\(new RotaryFurnaceRecipe\(new MaterialStack\((MAT_\w+), INGOT\.q\((\d+)\)\), (\d+), (\d+)", st.text["o:rfr"])]
    ck("V1.rot_row_count", len(rows) == len(ROT_ROWS) + len(ROT_OMITTED), "the original has 13 default rotary furnace rows (8 ported, 5 recorded omissions)", len(rows))
    got = [(m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))) for m in rows]
    ck("V1.rot_omitted", all(o in got for o in ROT_OMITTED), "the five recorded omissions exist in the original", [o for o in ROT_OMITTED if o not in got])
    for index, (mat, q, dur, steam, fluid, amount, otokens, _) in enumerate(ROT_ROWS):
        lines = [ln for ln in st.text["o:rfr"].split("\n") if f"MaterialStack({mat}, INGOT.q({q})), {dur}, {steam}" in ln.replace("\t", " ")]
        ok = len(lines) >= 1 and any(
            (fluid is None or f"new FluidStack(Fluids.{fluid}, {amount})" in ln) and all(t in ln for t in otokens) for ln in lines)
        ck(f"V1.rot_row{index}", ok, f"original rotary furnace row {index}: {mat} {q} ingots {dur} ticks {steam} steam {fluid} {amount} {otokens}", lines)
    anchor(ck, "V1.flower_water", st, "flower", 140, 150, "cadmium willows can only grow with water", "meta == EnumFlowerType.CD0.ordinal() || meta == EnumFlowerType.CD1.ordinal()",
           "world.getBlock(x + 1, y - 1, z).getMaterial() != Material.water", "world.getBlock(x, y - 1, z - 1).getMaterial() != Material.water")
    anchor(ck, "V1.flower_air", st, "flower", 152, 154, "meta == EnumFlowerType.WEED.ordinal() || meta == EnumFlowerType.CD1.ordinal()", "return world.isAirBlock(x, y + 1, z);")
    anchor(ck, "V1.flower_chance", st, "flower", 160, 168, "rand.nextFloat() < 0.33F")
    anchor(ck, "V1.flower_grow", st, "flower", 189, 203, "EnumFlowerType.CD1.ordinal()", "EnumTallFlower.CD2.ordinal() + 8")
    anchor(ck, "V1.tall_reset", st, "tall", 150, 160, "ownMeta < 8", "EnumFlowerType.CD0.ordinal()")
    anchor(ck, "V1.tall_water", st, "tall", 228, 247, "rec == EnumTallFlower.CD2.ordinal() || rec == EnumTallFlower.CD3.ordinal()", "world.getBlock(x + 1, y0 - 1, z).getMaterial() != Material.water",
           "return onTop == ModBlocks.dirt_dead || onTop == ModBlocks.dirt_oily;", "return rec != EnumTallFlower.CD4.ordinal()")
    anchor(ck, "V1.tall_chance", st, "tall", 254, 257, "meta == EnumTallFlower.CD3.ordinal()", "rand.nextFloat() < 0.33F")
    anchor(ck, "V1.tall_grow", st, "tall", 269, 284, "world.setBlock(x, y - 1, z, Blocks.dirt);", "world.setBlock(x, y - 2, z, Blocks.dirt);")
    anchor(ck, "V1.tall_loot", st, "tall", 343, 350, "metadata == EnumTallFlower.CD4.ordinal() + 8", "3 + world.rand.nextInt(4)")
    anchor(ck, "V1.oil_spot", st, "oil", 59, 68, "world.rand.nextInt(10) == 0 ? ModBlocks.dirt_oily : ModBlocks.dirt_dead", "addWillows && world.rand.nextInt(50) == 0", "EnumFlowerType.CD0.ordinal()")
    anchor(ck, "V1.shredder", st, "shred", 302, 307, *[f"ShredderRecipes.setRecipe(ModBlocks.{o}, new ItemStack(ModItems.scrap_oil, 1));" for o, _ in SHRED], "ModBlocks.stone_porous")
    anchor(ck, "V1.cadmium", st, "cryst", 108, 108, "EnumPlantType.MUSTARDWILLOW", "new CrystallizerRecipe(new ItemStack(ModItems.powder_cadmium), 100).setReq(10)", "new FluidStack(Fluids.RADIOSOLVENT, 250)")
    anchor(ck, "V1.arsenic", st, "cryst", 109, 109, "ModItems.scrap_oil", "new ItemStack(ModItems.nugget_arsenic), 100).prod(0.3F).setReq(16)", "new FluidStack(Fluids.RADIOSOLVENT, 100)")
    for line, tar, acid in ((212, "CRUDE", 250), (213, "CRACK", 100), (214, "PARAFFIN", 100)):
        anchor(ck, f"V1.wax_{tar.lower()}", st, "cryst", line, line, f"EnumTarType.{tar}", "EnumTarType.WAX), 20)", f"new FluidStack(Fluids.CHLORINE, {acid})")
    anchor(ck, "V1.cryst_class", st, "cryst", 324, 349, "public float productivity = 0F;", "this.acidAmount = 500;")
    anchor(ck, "V1.platemixed", st, "amr", 81, 82, 'new GenericRecipe("ass.platemixed").setup(50, 100).outputItems(new ItemStack(ModItems.plate_mixed, 4))',
           "new OreDictStack(CU.plate(), 2), new ComparableStack(ModItems.neutron_reflector, 1), new OreDictStack(BIGMT.plate(), 1)")
    anchor(ck, "V1.chipbismoid", st, "amr", 129, 130, 'new GenericRecipe("ass.chipBismoid").setup(100, 1_500)', "EnumCircuitType.CHIP_BISMOID", "new ComparableStack(ModItems.plate_polymer, 2)",
           "new ComparableStack(ModItems.circuit, 2, EnumCircuitType.SILICON)", "new OreDictStack(ANY_BISMOID.nugget())", "new OreDictStack(GOLD.wireFine(), 2)")
    anchor(ck, "V1.vacrefinery", st, "amr", 327, 328, 'new GenericRecipe("ass.vaccumrefinery").setup(200, 100)', "new ItemStack(ModBlocks.machine_vacuum_distill, 1)", "new OreDictStack(STEEL.plateCast(), 16)",
           "new OreDictStack(CU.plate(), 16)", "new OreDictStack(ANY_RESISTANTALLOY.ingot(), 4)", "new ComparableStack(ModItems.sphere_steel, 1)", "new OreDictStack(STEEL.pipe(), 12)",
           "new ComparableStack(ModItems.motor_desh, 3)", "new ComparableStack(ModItems.circuit, 4, EnumCircuitType.CHIP_BISMOID)")
    anchor(ck, "V1.anvil_upgrade", st, "anvil", 60, 70, "Block[] anvils = new Block[]{ModBlocks.anvil_iron, ModBlocks.anvil_lead};", "ModBlocks.anvil_saturnite, 1), new ComparableStack(anvil), new OreDictStack(BIGMT.ingot(), 10)")
    anchor(ck, "V1.anvil_furnace", st, "anvil", 325, 331, "new ComparableStack(Blocks.stonebrick, 8)", "new ComparableStack(ModItems.ingot_firebrick, 16)", "new OreDictStack(IRON.ingot(), 4)",
           "new OreDictStack(CU.plate(), 8)", "new AnvilOutput(new ItemStack(ModBlocks.machine_rotary_furnace))).setTier(2)")
    anchor(ck, "V1.fuel", st, "fuel", 17, 28, "int single = 200;", "ModItems.solid_fuel))\t\t\t\t\t\treturn single * 16;".replace("\t", " "), "ModItems.rocket_fuel))\t\t\t\t\t\treturn single * 32;".replace("\t", " "))
    anchor(ck, "V1.mixer", st, "mixer", 63, 63, "register(Fluids.RADIOSOLVENT, new MixerRecipe(1000, 50).setStack1(new FluidStack(Fluids.REFORMGAS, 750)).setStack2(new FluidStack(Fluids.CHLORINE, 250)));")
    anchor(ck, "V1.fraction", st, "frac", 38, 38, "Fluids.LIGHTOIL_VACUUM", "new FluidStack(Fluids.KEROSENE, 70)", "new FluidStack(Fluids.REFORMGAS, 30)")
    anchor(ck, "V1.outgasser", st, "outg", 62, 62, "EnumTarType.WAX", "new OutgasserRecipe(null, new FluidStack(Fluids.RADIOSOLVENT, 100))")


def v2_neo(ck, st):
    vrr = code(st.text["vrr"])
    for name, value in (("heavy", 40), ("reform", 25), ("light", 20), ("sour", 15)):
        has(ck, f"V2.vac_frac_{name}", f"vac_frac_{name} = {value} (VacuumRefineryRecipes.java:19-22)", vrr, f"vac_frac_{name} = {value};")
    has(ck, "V2.vac_oil_row", "the oil row: heavy, reformate, light, sour gas (:25-30)", vrr, "recipes.put(Fluids.OIL, new VacuumRefineryRecipe( new FluidStack(Fluids.HEAVYOIL_VACUUM, vac_frac_heavy), "
        "new FluidStack(Fluids.REFORMATE, vac_frac_reform), new FluidStack(Fluids.LIGHTOIL_VACUUM, vac_frac_light), new FluidStack(Fluids.SOURGAS, vac_frac_sour)));")
    has(ck, "V2.vac_ds_row", "the desulfurized oil row ends in reformgas (:31-35)", vrr, "recipes.put(Fluids.OIL_DS, new VacuumRefineryRecipe( new FluidStack(Fluids.HEAVYOIL_VACUUM, vac_frac_heavy), "
        "new FluidStack(Fluids.REFORMATE, vac_frac_reform), new FluidStack(Fluids.LIGHTOIL_VACUUM, vac_frac_light), new FluidStack(Fluids.REFORMGAS, vac_frac_sour)));")
    has(ck, "V2.vac_file", "the table sits in hbmVacuumRefinery.json (deviation recorded: the original file is hbmVacRefinery.json)", vrr, 'getFileName() { return "hbmVacuumRefinery.json"; }')
    vbe = code(st.text["vbe"])
    has(ck, "V2.vac_consts", "maximum power 1,000,000, 10,000 per operation, 100 mB per operation", vbe, "MAX_POWER = 1_000_000L;", "POWER_PER_OPERATION = 10_000;", "INPUT_PER_OPERATION = 100;")
    has(ck, "V2.vac_tanks", "oil 64,000 at pressure 2, four outputs of 24,000", vbe, "new FluidTank(Fluids.OIL, 64_000).withPressure(2)", "new FluidTank(Fluids.HEAVYOIL_VACUUM, 24_000)", "new FluidTank(Fluids.REFORMATE, 24_000)",
        "new FluidTank(Fluids.LIGHTOIL_VACUUM, 24_000)", "new FluidTank(Fluids.SOURGAS, 24_000)")
    has(ck, "V2.vac_dims", "the vacuum refinery block is 8 up and 1 around, offset 1", code(st.text["vblock"]), "return new int[] {8, 0, 1, 1, 1, 1};", "getOffset() { return 1; }")
    rbe = code(st.text["rbe"])
    has(ck, "V2.rot_consts", "MAX_OUTPUT is BLOCK.q(16), coke x1.25, rocket and solid x1.5, solid heat x1.5, tanks 16,000 / 12,000 / 120", rbe, "MAX_OUTPUT = MaterialShapes.BLOCK.q(16);", ".setCokeTimeMod(1.25)",
        ".setRocketTimeMod(1.5)", ".setSolidTimeMod(1.5)", ".setSolidHeatMod(1.5)", "new FluidTank(Fluids.NONE, 16_000)", "new FluidTank(Fluids.STEAM, 12_000)", "new FluidTank(Fluids.SPENTSTEAM, 120)")
    has(ck, "V2.rot_pour", "the pour point is rot * 2.875, y + 1.25", rbe, "getStepX() * 2.875D", "getY() + 1.25D", "getStepZ() * 2.875D")
    has(ck, "V2.rot_dims", "the rotary furnace block is {4, 0, 1, 1, 2, 2}, offset 1", code(st.text["rblock"]), "return new int[] {4, 0, 1, 1, 2, 2};", "getOffset() { return 1; }")
    rfr = code(st.text["rfr"])
    neo_rows = [norm(m.group(0)) for m in re.finditer(r"recipes\.add\(new RotaryFurnaceRecipe\(new MaterialStack\(Mats\..*?\)\);", rfr, flags=re.S)]
    ck("V2.rot_row_count", len(neo_rows) == len(ROT_ROWS), "NEO registers exactly the eight ported rows", len(neo_rows))
    for index, (mat, q, dur, steam, fluid, amount, _, tokens) in enumerate(ROT_ROWS):
        head = f"new MaterialStack(Mats.{mat}, MaterialShapes.INGOT.q({q})), {dur}, {steam}"
        hit = [r for r in neo_rows if head in r and (fluid is None or f"new FluidStack(Fluids.{fluid}, {amount})" in r) and all(t in r for t in tokens)]
        ck(f"V2.rot_row{index}", len(hit) >= 1 and neo_rows.index(hit[0]) == index, f"NEO rotary furnace row {index} equals the original: {mat} {q} ingots {dur} ticks {steam} steam", hit)
    willow = code(st.text["willow"])
    has(ck, "V2.willow_water", "the willow needs water next to the block below (BlockNTMFlower.java:142-150)", willow, "BlockPos soil = lower.below();", "Direction.Plane.HORIZONTAL",
        "level.getFluidState(soil.relative(direction)).is(FluidTags.WATER)", "if(!hasWater(level, lower)) return false;")
    has(ck, "V2.willow_stages", "age 1 needs air above, age 3 dead or oily soil, age 4 does not grow", willow, "if(age >= 4) return false;", "if(age == 1) return level.isEmptyBlock(lower.above());",
        "if(age == 3) {", "soil.is(NtmBlocks.DIRT_DEAD.get()) || soil.is(NtmBlocks.DIRT_OILY.get())")
    has(ck, "V2.willow_chance", "chance 0.33 below age 3, certain at age 3, random tick one in three", willow, "if(state.getValue(AGE) == 3) return true;", "random.nextFloat() < 0.33F", "random.nextInt(3) == 0")
    has(ck, "V2.willow_grow", "age 0 grows one block, ages 1 and 2 two blocks, the mature step turns the soil into dirt", willow, "if(age == 0) {", "level.setBlock(lower.above(), lowerState.setValue(HALF, DoubleBlockHalf.UPPER), Block.UPDATE_CLIENTS);",
        "if(age == 3) { level.setBlock(lower.below(), Blocks.DIRT.defaultBlockState(), 3); }")
    has(ck, "V2.willow_reset", "a lower half that lost its upper half returns to the sapling (BlockTallPlant.java:150-160)", willow, "state.getValue(AGE) >= 2", "level.setBlock(pos, this.defaultBlockState(), 3);")
    oil = code(st.text["oil"])
    has(ck, "V2.oil_spot", "grass or dirt becomes dead soil, one in ten oily; with addWillows one in 50 places a sapling", oil, "random.nextInt(10) == 0 ? NtmBlocks.DIRT_OILY.get().defaultBlockState() : NtmBlocks.DIRT_DEAD.get().defaultBlockState()",
        "addWillows && random.nextInt(50) == 0", "NtmBlocks.PLANT_MUSTARD_WILLOW.get().defaultBlockState()")
    shred = code(st.text["shred"])
    for _, neo in SHRED:
        has(ck, f"V2.shred_{neo.lower()}", f"NtmBlocks.{neo} shreds to one scrap_oil", shred, f"registerIfAbsent(new ItemStack(NtmBlocks.{neo}.get()), new ItemStack(NtmItems.SCRAP_OIL.get(), 1));")
    cryst = code(st.text["cryst"])
    has(ck, "V2.cadmium", "cadmium: 10 willow leaves + 250 mB radiosolvent -> powder_cadmium, 100 ticks, productivity 0 (CrystallizerRecipes.java:108,328)", cryst,
        "new ComparableStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 10), new FluidStack(Fluids.RADIOSOLVENT, 250), new ItemStack(NtmItems.POWDER_CADMIUM.get()), 100, 0F)")
    has(ck, "V2.arsenic", "arsenic: 16 scraps + 100 mB radiosolvent -> nugget_arsenic, 100 ticks, productivity 0.3 (:109)", cryst,
        "new ComparableStack(NtmItems.SCRAP_OIL.get(), 16), new FluidStack(Fluids.RADIOSOLVENT, 100), new ItemStack(NtmItems.NUGGET_ARSENIC.get()), 100, 0.3F)")
    for tar, acid in (("CRUDE", 250), ("CRACK", 100), ("PARAFFIN", 100)):
        has(ck, f"V2.wax_{tar.lower()}", f"oil_tar_{tar.lower()} + {acid} mB chlorine -> oil_tar_wax, 20 ticks, productivity 0 (:212-214)", cryst,
            f"new ComparableStack(NtmItems.OIL_TAR_{tar}.get(), 1), new FluidStack(Fluids.CHLORINE, {acid}), new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, 0F)")
    amr = code(st.text["amr"])
    plate = statement(amr, "ass.platemixed")
    ck("V2.platemixed_present", plate is not None, "ass.platemixed is registered (AssemblyMachineRecipes.java:81-82)", "row missing")
    has(ck, "V2.platemixed", "ass.platemixed: 50 ticks, 100 HE/t, 2 copper plates + neutron reflector + saturnite plate -> 4 mixed plates", plate,
        'new GenericRecipe("ass.platemixed").setup(50, 100)', "new ItemStack(NtmItems.PLATE_MIXED.get(), 4)", "new ComparableStack(NtmItems.PLATE_COPPER.get(), 2)", "new ComparableStack(NtmItems.NEUTRON_REFLECTOR.get(), 1)",
        "new ComparableStack(NtmItems.PLATE_SATURNITE.get(), 1)")
    vac = statement(amr, "ass.vaccumrefinery")
    ck("V2.vacrefinery_present", vac is not None, "ass.vaccumrefinery is registered (:327-328)", "row missing")
    has(ck, "V2.vacrefinery", "ass.vaccumrefinery: 200 ticks, 100 HE/t, normal inputs with four circuits (decision: stays as the original)", vac, 'new GenericRecipe("ass.vaccumrefinery").setup(200, 100)',
        "new ItemStack(NtmBlocks.MACHINE_VACUUM_DISTILL.get(), 1)", "castPlateIngredient(CastPlateItem.Type.STEEL, 16)", "new ComparableStack(NtmItems.PLATE_COPPER.get(), 16)",
        '"ingots_resistant_alloy")), 4)', "new ComparableStack(NtmItems.SPHERE_STEEL.get(), 1)", "new ComparableStack(NtmItems.PIPE_STEEL.get(), 12)", "new ComparableStack(NtmItems.MOTOR_DESH.get(), 3)",
        "new ComparableStack(NtmItems.CIRCUIT_VERSATILE_INTEGRATED.get(), 4)")
    chip = statement(amr, "ass.chipBismoid")
    ck("V2.chip_present", chip is not None, "ass.chipBismoid is registered (:129-130)", "row missing")
    has(ck, "V2.chipbismoid", "ass.chipBismoid: 100 ticks, 1,500 HE/t, polymer plates 2, silicon wafers 2, a bismoid nugget, gold wires 2 -> versatile integrated circuit", chip,
        'new GenericRecipe("ass.chipBismoid").setup(100, 1_500)', "new ItemStack(NtmItems.CIRCUIT_VERSATILE_INTEGRATED.get(), 1)", "new ComparableStack(NtmItems.PLATE_POLYMER.get(), 2)",
        "new ComparableStack(NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 2)", '"nuggets_bismoid")), 1)', "new ComparableStack(NtmItems.WIRE_GOLD.get(), 2)")
    start = amr.find('new GenericRecipe("ass.chipBismoid")')
    guard_at = amr.rfind("if(!NtmConfig.enable528()) {", 0, start) if start > 0 else -1
    segment = amr[guard_at:start] if guard_at >= 0 else ""
    ck("V2.chip_in_no528", guard_at >= 0 and segment.count("{") > segment.count("}"), "ass.chipBismoid sits inside the !enable528 block (AssemblyMachineRecipes.java:128)", "no open !enable528 block before the row")
    anvil = code(st.text["anvil"])
    for base in ("IRON", "LEAD"):
        has(ck, f"V2.anvil_{base.lower()}", f"the {base.lower()} anvil + 10 saturnite ingots -> saturnite anvil", anvil, f"addUpgrade(NTMAnvilBlock.Variant.{base}, NTMAnvilBlock.Variant.SATURNITE, NtmItems.INGOT_SATURNITE.get(), 10);")
    has(ck, "V2.anvil_furnace", "the rotary furnace construction row: stone bricks 8, firebrick 16, iron ingot 4, copper plate 8, tier 2", anvil, "new ComparableStack(Blocks.STONE_BRICKS, 8)",
        "new ComparableStack(NtmItems.INGOT_FIREBRICK.get(), 16)", "new ComparableStack(Items.IRON_INGOT, 4)", "new ComparableStack(NtmItems.PLATE_COPPER.get(), 8)", "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_ROTARY_FURNACE.asItem())) ).setTier(2)")
    items = code(st.text["items"])
    ck("V2.solid_fuel", bool(re.search(r"SOLID_FUEL\b[^;]*FuelItem[^;]*3[_ ]?200", items)) or "3_200" in items or "3200" in items, "solid_fuel burns 3,200 ticks (FuelHandler.java:21 single * 16)", "no 3200 burn time near SOLID_FUEL")
    ck("V2.rocket_fuel", bool(re.search(r"ROCKET_FUEL\b[^;]*6[_ ]?400", items)), "rocket_fuel burns 6,400 ticks (FuelHandler.java:27 single * 32)", "no 6400 burn time near ROCKET_FUEL")


def v3_generated(ck, st):
    try:
        loot = json.loads(st.text["loot"])
    except (TypeError, ValueError) as error:
        ck("V3.loot_json", False, "the willow loot table parses", repr(error))
        return
    pools = loot.get("pools", [])
    ck("V3.loot_pools", len(pools) == 2, "two pools: the sapling for every half, the leaves for the mature upper half", len(pools))
    if len(pools) == 2:
        ck("V3.loot_sapling", pools[0]["entries"][0]["name"] == "hbmsntm:plant_mustard_willow" and not pools[0].get("conditions"), "pool 0 drops the sapling unconditionally", pools[0])
        cond = pools[1].get("conditions", [{}])[0]
        count = pools[1]["entries"][0]["functions"][0]["count"]
        ck("V3.loot_leaves", pools[1]["entries"][0]["name"] == "hbmsntm:plant_item_mustardwillow" and cond.get("properties") == {"age": "4", "half": "upper"} and
           count.get("min") == 3.0 and count.get("max") == 6.0, "pool 1 drops 3-6 leaves for age 4 upper (BlockTallPlant.java:343-350: 3 + nextInt(4))", pools[1])
    try:
        states = json.loads(st.text["blockstate"])["variants"]
    except (TypeError, ValueError) as error:
        ck("V3.blockstate", False, "the willow blockstate parses", repr(error))
        return
    wanted = {f"age={a},half={h}" for a in range(5) for h in ("lower", "upper")}
    ck("V3.blockstate", set(states) == wanted, "the willow blockstate covers the ten states", sorted(set(states) ^ wanted))
    models = {v["model"].rsplit("/", 1)[-1] for v in states.values()}
    ck("V3.models", all(st.text.get(GEN + f"assets/hbmsntm/models/block/{m}.json") for m in models), "every model the blockstate names exists", sorted(models))
    ck("V3.machine_loot", all(st.text.get(p) for p in MACHINE_LOOT), "both machines have a loot table", MACHINE_LOOT)
    try:
        members = json.loads(st.text["bismoid"]).get("values", [])
    except (TypeError, ValueError) as error:
        ck("V3.bismoid_tag", False, "data/ntm/tags/item/nuggets_bismoid.json parses (run runData after the datagen change)", repr(error))
        return
    ck("V3.bismoid_tag", sorted(members) == ["hbmsntm:nugget_arsenic", "hbmsntm:nugget_bismuth"], "#ntm:nuggets_bismoid holds the bismuth and arsenic nuggets (OreDictManager ANY_BISMOID)", members)


def v4_language(ck, st):
    en = json.loads(st.text["enjson"]) if st.text["enjson"] else {}
    zh = json.loads(st.text["zhjson"]) if st.text["zhjson"] else {}
    mapping = json.loads(st.text["zhmap"])["entries"] if st.text["zhmap"] else {}

    def lang_value(text, key):
        m = re.search(r"^" + re.escape(key) + r"=(.*)$", text or "", flags=re.M)
        return m.group(1).rstrip("\r") if m else None

    for neo, orig in LANG.items():
        oe, oz = lang_value(st.text["o:en"], orig), lang_value(st.text["o:zh"], orig)
        ck(f"V4.original_{neo}", oe is not None and oz is not None, f"the original has {orig} in English and Chinese", (oe, oz))
        ck(f"V4.en_{neo}", en.get(neo) == oe, f"en_us {neo} equals the original English", (en.get(neo), oe))
        ck(f"V4.zh_{neo}", zh.get(neo) == oz and oz is not None, f"zh_cn {neo} equals the original Chinese", (zh.get(neo), oz))
        entry = mapping.get(neo)
        ck(f"V4.map_{neo}", bool(entry) and entry.get("kind") == "upstream" and entry.get("source_key") == orig and entry.get("target_zh") == zh.get(neo) and entry.get("source_en") == oe,
           f"the reviewed mapping records {neo} as upstream {orig}", entry)


def v5_ownership(ck, st):
    data = json.loads(st.text["ownership"]) if st.text["ownership"] else {}
    ck("V5.source_commit", data.get("source_commit") == ORIGINAL_HEAD, "the record names the original HEAD", data.get("source_commit"))
    assets = data.get("imported_assets", [])
    ck("V5.count", len(assets) >= 10, "the record lists the imported files", len(assets))
    bad = []
    for entry in assets:
        target, source = ROOT / entry["target_path"], ORIGINAL / entry["source_path"]
        try:
            ok = sha(target.read_bytes()) == entry["target_sha256"] and sha(source.read_bytes()) == entry["source_sha256"] and entry["target_sha256"] == entry["source_sha256"]
        except OSError:
            ok = False
        if not ok:
            bad.append(entry["target_path"])
    ck("V5.hashes", not bad, "every imported file's SHA-256 equals the record in NEO and in the original", bad[:8])


def v6_gametest(ck, st):
    text = st.text["gt"] or ""
    names = re.findall(r"public static void (\w+)\(GameTestHelper", text)
    ck("V6.names", tuple(names) == GT_TESTS, "the 18 tests in order", names)
    batches = re.findall(r'batch = "(\w+)"', text)
    ck("V6.batches", len(batches) == len(set(batches)) == len(names), "one batch per test", batches)
    ck("V6.markers", all(re.search(r'"\{\} \{\} passed", TAG, "' + n + '"', text) for n in names), "every test logs its passed line", "")
    has(ck, "V6.numbers", "the numbers of the original are asserted", text, "{ 40, 25, 20, 15 }", "10_000", "== 65", "== 134", "2.875", "MAX_OUTPUT", "leaves >= 3 && leaves <= 6", "0.3F", "ass.chipBismoid", "1_500", "ass.platemixed")
    has(ck, "V6.productivity", "the cadmium and wax rows are asserted at productivity 0", text, "cadmium.productivity == 0F", "wax.productivity == 0F")
    has(ck, "V6.real_fuel", "the solid fuel is the real item with 3,200 ticks", text, "solid_fuel burns", "3_200")


def v7_log(ck, st):
    log = st.log
    total = re.findall(r"All (\d+) required tests passed", log)
    ck("V7.total", len(total) == 1 and int(total[0]) == START_GAMETESTS + len(GT_TESTS), f"the log ends with all {START_GAMETESTS + len(GT_TESTS)} required tests passed", total)
    for n in GT_TESTS:
        ck(f"V7.{n}", f"{GT_MARK} {n} passed" in log, f"the log holds {n} passed", "")
    ck("V7.no_failure", "required tests failed" not in log and not re.search(r"LogTestReporter\]: \w+ failed", log), "the log holds no failed test", "")


def v8_jar(ck, st, path):
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        ck("V8.class", "com/hbm/gametest/ResourceCompletionGameTests.class" in names and "com/hbm/world/feature/OilSpot.class" in names, "the JAR has the test class and OilSpot", "")
        bad = []
        for rel in [GEN + "data/hbmsntm/loot_table/blocks/plant_mustard_willow.json", GEN + "assets/hbmsntm/blockstates/plant_mustard_willow.json", GEN + "data/ntm/tags/item/nuggets_bismoid.json", EN, ZH]:
            inner = rel[len(GEN):] if rel.startswith(GEN) else rel[len("src/main/resources/"):]
            if inner not in names or jar.read(inner) != (ROOT / rel).read_bytes():
                bad.append(inner)
        ck("V8.resources", not bad, "the generated willow files, the bismoid tag and both language files are in the JAR with the tree's bytes", bad)
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


def static_suite(st):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, st)
    guarded(ck, "V1", v1_original, st)
    guarded(ck, "V2", v2_neo, st)
    guarded(ck, "V3", v3_generated, st)
    guarded(ck, "V4", v4_language, st)
    guarded(ck, "V5", v5_ownership, st)
    guarded(ck, "V6", v6_gametest, st)
    if st.log is not None:
        guarded(ck, "V7", v7_log, st)
    return ck


def T(key, fn):
    def apply(st):
        st.text[key] = fn(st.text[key])
    return apply


def cut_statement(name):
    def fn(text):
        start = text.rfind("this.register(", 0, text.index(f'new GenericRecipe("{name}")'))
        return text[:start] + text[text.index(";", start) + 1:]
    return fn


def mutations():
    return [
        # the five required mutations
        ("vac_fraction_changed", "V2.", T("vrr", lambda x: rep1(x, "vac_frac_light = 20;", "vac_frac_light = 21;"))),
        ("saturnite_steam_changed", "V2.", T("rfr", lambda x: rep1(x, "MaterialShapes.INGOT.q(2)), 200, 400, new FluidStack(Fluids.REFORMGAS, 250)", "MaterialShapes.INGOT.q(2)), 200, 399, new FluidStack(Fluids.REFORMGAS, 250)"))),
        ("willow_water_condition_removed", "V2.", T("willow", lambda x: rep1(x, "if(!hasWater(level, lower)) return false;", ""))),
        ("cadmium_count_changed", "V2.", T("cryst", lambda x: rep1(x, "new ComparableStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 10)", "new ComparableStack(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 11)"))),
        ("platemixed_row_deleted", "V2.", T("amr", cut_statement("ass.platemixed"))),
        # NEO inputs
        ("vac_power_changed", "V2.", T("vbe", lambda x: rep1(x, "POWER_PER_OPERATION = 10_000;", "POWER_PER_OPERATION = 12_000;"))),
        ("vac_pressure_removed", "V2.", T("vbe", lambda x: rep1(x, "new FluidTank(Fluids.OIL, 64_000).withPressure(2)", "new FluidTank(Fluids.OIL, 64_000)"))),
        ("rotary_spent_steam_tank", "V2.", T("rbe", lambda x: rep1(x, "new FluidTank(Fluids.SPENTSTEAM, 120)", "new FluidTank(Fluids.SPENTSTEAM, 1_200)"))),
        ("rotary_max_output", "V2.", T("rbe", lambda x: rep1(x, "MAX_OUTPUT = MaterialShapes.BLOCK.q(16);", "MAX_OUTPUT = MaterialShapes.BLOCK.q(8);"))),
        ("rotary_pour_offset", "V2.", T("rbe", lambda x: x.replace("2.875D", "2.5D", 1))),
        ("rotary_row_dropped", "V2.", T("rfr", lambda x: rep1(x, "MaterialShapes.INGOT.q(4)), 200, 300,", "MaterialShapes.INGOT.q(4)), 200, 301,"))),
        ("willow_chance_changed", "V2.", T("willow", lambda x: rep1(x, "random.nextFloat() < 0.33F", "random.nextFloat() < 0.5F"))),
        ("willow_soil_to_dirt_removed", "V2.", T("willow", lambda x: rep1(x, "level.setBlock(lower.below(), Blocks.DIRT.defaultBlockState(), 3);", ""))),
        ("oil_spot_willow_odds", "V2.", T("oil", lambda x: rep1(x, "random.nextInt(50) == 0", "random.nextInt(40) == 0"))),
        ("shredder_row_dropped", "V2.", T("shred", lambda x: rep1(x, "registerIfAbsent(new ItemStack(NtmBlocks.STONE_CRACKED.get()), new ItemStack(NtmItems.SCRAP_OIL.get(), 1));", ""))),
        ("arsenic_count_changed", "V2.", T("cryst", lambda x: rep1(x, "new ComparableStack(NtmItems.SCRAP_OIL.get(), 16)", "new ComparableStack(NtmItems.SCRAP_OIL.get(), 15)"))),
        ("wax_duration_changed", "V2.", T("cryst", lambda x: rep1(x, "new FluidStack(Fluids.CHLORINE, 250), new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, 0F", "new FluidStack(Fluids.CHLORINE, 250), new ItemStack(NtmItems.OIL_TAR_WAX.get()), 21, 0F"))),
        ("wax_productivity_default", "V2.", T("cryst", lambda x: rep1(x, "new FluidStack(Fluids.CHLORINE, 100), new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, 0F)", "new FluidStack(Fluids.CHLORINE, 100), new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, DEFAULT_PRODUCTIVITY)") if x.count("new FluidStack(Fluids.CHLORINE, 100), new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, 0F)") == 1 else x.replace("new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, 0F)", "new ItemStack(NtmItems.OIL_TAR_WAX.get()), 20, DEFAULT_PRODUCTIVITY)", 1))),
        ("chip_bismoid_power", "V2.", T("amr", lambda x: rep1(x, 'new GenericRecipe("ass.chipBismoid").setup(100, 1_500)', 'new GenericRecipe("ass.chipBismoid").setup(100, 1_400)'))),
        ("chip_bismoid_row_deleted", "V2.", T("amr", cut_statement("ass.chipBismoid"))),
        ("vacrefinery_circuits", "V2.", T("amr", lambda x: rep1(x, "new ComparableStack(NtmItems.CIRCUIT_VERSATILE_INTEGRATED.get(), 4)));", "new ComparableStack(NtmItems.CIRCUIT_VERSATILE_INTEGRATED.get(), 3)));"))),
        ("anvil_upgrade_ingots", "V2.", T("anvil", lambda x: rep1(x, "addUpgrade(NTMAnvilBlock.Variant.LEAD, NTMAnvilBlock.Variant.SATURNITE, NtmItems.INGOT_SATURNITE.get(), 10);", "addUpgrade(NTMAnvilBlock.Variant.LEAD, NTMAnvilBlock.Variant.SATURNITE, NtmItems.INGOT_SATURNITE.get(), 9);"))),
        ("anvil_furnace_tier", "V2.", T("anvil", lambda x: rep1(x, "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_ROTARY_FURNACE.asItem()))\n        ).setTier(2)", "new AnvilOutput(new ItemStack(NtmBlocks.MACHINE_ROTARY_FURNACE.asItem()))\n        ).setTier(3)"))),
        # generated JSON, language, ownership
        ("loot_leaf_max", "V3.", T("loot", lambda x: rep1(x, '"max": 6.0', '"max": 7.0'))),
        ("blockstate_state_dropped", "V3.", T("blockstate", lambda x: rep1(x, '"age=4,half=upper"', '"age=4,half=other"'))),
        ("bismoid_tag_member", "V3.", T("bismoid", lambda x: x.replace('"hbmsntm:nugget_arsenic"', '"hbmsntm:nugget_lead"') if x and "nugget_arsenic" in x else (_ for _ in ()).throw(AssertionError("tag file empty")))),
        ("zh_text_changed", "V4.", T("zhjson", lambda x: rep1(x, '"block.hbmsntm.machine_vacuum_distill": "真空炼油厂"', '"block.hbmsntm.machine_vacuum_distill": "真空炼油器"'))),
        ("en_text_changed", "V4.", T("enjson", lambda x: rep1(x, '"item.hbmsntm.scrap_oil": "Oily Scraps"', '"item.hbmsntm.scrap_oil": "Oily Scrap"'))),
        ("ownership_hash", "V5.", T("ownership", lambda x: x.replace('"target_sha256": "d7ca1241', '"target_sha256": "e7ca1241', 1))),
        # original text
        ("orig_line_moved", "V1.", T("o:cryst", lambda x: "\n" + x)),
        ("orig_fraction", "V1.", T("o:vrr", lambda x: rep1(x, "vac_frac_sour = 15;", "vac_frac_sour = 16;"))),
        ("orig_saturnite_steam", "V1.", T("o:rfr", lambda x: rep1(x, "INGOT.q(2)), 200, 400, new FluidStack(Fluids.REFORMGAS, 250)", "INGOT.q(2)), 200, 401, new FluidStack(Fluids.REFORMGAS, 250)"))),
        ("orig_flower_water", "V1.", T("o:flower", lambda x: rep1(x, "cadmium willows can only grow with water", "cadmium willows can grow anywhere"))),
        ("orig_cadmium_prod", "V1.", T("o:cryst", lambda x: rep1(x, "new CrystallizerRecipe(new ItemStack(ModItems.powder_cadmium), 100).setReq(10)", "new CrystallizerRecipe(new ItemStack(ModItems.powder_cadmium), 100).prod(0.05F).setReq(10)"))),
        ("orig_platemixed", "V1.", T("o:amr", lambda x: rep1(x, 'new GenericRecipe("ass.platemixed").setup(50, 100)', 'new GenericRecipe("ass.platemixed").setup(51, 100)'))),
        # GameTest source and log
        ("gt_batch_shared", "V6.", T("gt", lambda x: rep1(x, 'batch = "hbm28d_vacuum_gates"', 'batch = "hbm28d_vacuum_process"'))),
        ("gt_test_dropped", "V6.", T("gt", lambda x: rep1(x, "public static void crystallizer_wax(", "public static void crystallizer_wax_x("))),
        ("gt_fraction_changed", "V6.", T("gt", lambda x: x.replace("{ 40, 25, 20, 15 }", "{ 40, 25, 20, 16 }"))),
        ("gt_productivity_relaxed", "V6.", T("gt", lambda x: rep1(x, "cadmium.productivity == 0F", "cadmium.productivity >= 0F"))),
        ("log_total_changed", "V7.", T("log", lambda x: re.sub(r"All \d+ required tests passed", "All 338 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", T("log", lambda x: x.replace(f"{GT_MARK} oil_spot_willows passed", "")), "LOG"),
        ("log_failed_line", "V7.", T("log", lambda x: x + "\n[12:00:00] [Server thread/ERROR] [minecraft/LogTestReporter]: crystallizer_wax failed at 1, -60, 1! x\n"), "LOG"),
    ]


def mutate_all(st, base_failed):
    results = {}
    for entry in mutations():
        label, prefix, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required == "LOG" and st.log is None:
            results[label] = dict(expected_section=prefix, failed=[], detected=None, skipped="no --gametest-log")
            continue
        mutated = st.copy()
        try:
            if required == "LOG":
                mutated.text["log"] = mutated.log
                apply(mutated)
                mutated.log = mutated.text.pop("log")
            else:
                apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError, AttributeError) as error:
            results[label] = dict(expected_section=prefix, failed=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.text == st.text and mutated.log == st.log:
            results[label] = dict(expected_section=prefix, failed=[], detected=False, error="mutation changed nothing")
            continue
        ck = static_suite(mutated)
        real = [f for f in ck.failed() if f not in base_failed]
        results[label] = dict(expected_section=prefix, failed=real[:8], detected=any(f.startswith(prefix) for f in real))
    return results


def sections(ck):
    out = {}
    for item in ck.items:
        out.setdefault(item["id"].split(".")[0], []).append(item)
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        failed = [i["id"] for i in items if i["status"] == "FAIL"]
        result[sec] = dict(status="FAIL" if failed else "PASS", checks=len(items), passed=sum(1 for i in items if i["status"] == "PASS"), failed=failed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    st = collect()
    if args.gametest_log:
        st.log = Path(args.gametest_log).read_text(encoding="utf-8", errors="replace")
    ck = static_suite(st)
    base_failed = set(ck.failed())
    extra = {}
    if args.jar:
        extra["jar"] = guarded(ck, "V8", v8_jar, st, args.jar)
    muts = mutate_all(st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V9"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    report = dict(command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]), summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(applied) - len(undetected),
                                                                                       mutations_applied=len(applied), mutations_total=len(muts), mutations_skipped=skipped),
                  sections=secs, failed=ck.failed(), undetected_mutations=undetected, checks=ck.items, mutations=muts, extra=extra, original_head=ORIGINAL_HEAD)
    report["pass"] = not ck.failed() and not undetected
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] != "PASS":
            print(f"{item['status']} {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        if value.get("detected") is None:
            print(f"SKIPPED  mutation {label}: {value.get('skipped')}")
            continue
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label} (expect {value['expected_section']}): {value['failed'][:4]}" + (f" {value['error']}" if value.get("error") else ""))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
