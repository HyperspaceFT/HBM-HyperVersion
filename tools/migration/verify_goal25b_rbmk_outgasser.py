"""Verify the Goal25B batch statically: the RBMK irradiation channel (rbmk_outgasser: RBMKOutgasserBlock, RBMKOutgasserBlockEntity,
RBMKOutgasserMenu, RBMKOutgasserScreen), the OUTGASSER branch of RBMKNeutronHandler, the OutgasserRecipes table and its file contract, the
client sync (OutgasserRecipeSync, OutgasserRecipesPacket, OutgasserRecipeClientSync), the JEI irradiation category, the registrations and
datagen, the language entries, the imported resources and the GameTest source; with --gametest-log the GameTest log and its logged rates.

Read-only for both worktrees. Writes only build/migration/goal25b/verify/report.json and default-table.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal25b/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (tile entity, recipes, neutron handler, container, GUI, block, crafting, anvil, language) parsed at the cited lines.
- V2  Block entity against V1: constants, efficiency, strict >, canProcess order, process, onMelt, console, NBT, sync, slots, tanks, ports.
- V3  Neutron handler: the OUTGASSER branch against the original :312-332; the rest of the code equal to the start copy.
- V4  Recipe table: the 16 default rows against V1 through the handoff's item table, the file contract, lenient file / strict snapshot,
      limits, registration; writes the expected default export to build/migration/goal25b/verify/default-table.json.
- V5  Sync and JEI; client isolation.
- V6  Menu and screen against V1.
- V7  Registrations and datagen (generated blockstate, models, loot, recipe, pickaxe tag); AnvilRecipes unchanged.
- V8  Language: 2 channel keys + 5 DODD keys in the provider, en_us.json, zh_cn.json and zh_cn-map.json; nothing else changed.
- V9  Resources: the seven imports byte-equal to the original and recorded in migration/goal25b-resource-ownership.json.
- V10 Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed).
- V11 GameTest source, and with --gametest-log the log (all N passed, every test line, the logged numbers re-derived).
- V12 (--jar) the packaged JAR; "not run" without the flag.
- V13 In-memory mutations of the NEO inputs and of the original text (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal25b_rbmk_outgasser.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import copy
import difflib
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal25b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "783b6d137936750a8a5ef822e1b29fd1209593f7"

J = "src/main/java/com/hbm/"
BE_DIR = J + "blockentity/machine/rbmk/"
BLK_DIR = J + "blocks/machine/rbmk/"
OBE = BE_DIR + "RBMKOutgasserBlockEntity.java"
OBLK = BLK_DIR + "RBMKOutgasserBlock.java"
OREC = J + "inventory/recipes/OutgasserRecipes.java"
OSYNC = J + "inventory/recipes/OutgasserRecipeSync.java"
OPKT = J + "network/toclient/OutgasserRecipesPacket.java"
OCSYNC = J + "handler/OutgasserRecipeClientSync.java"
OMENU = J + "inventory/menus/RBMKOutgasserMenu.java"
OSCREEN = J + "inventory/screens/RBMKOutgasserScreen.java"
OJEI = J + "handler/jei/IrradiationRecipeHandler.java"
NEW_CLASSES = [OBLK, OBE, OREC, OSYNC, OPKT, OCSYNC, OMENU, OSCREEN, OJEI]
HANDLER = J + "handler/neutron/RBMKNeutronHandler.java"
SER = J + "inventory/recipes/loader/SerializableRecipe.java"
NET = J + "network/NtmNetwork.java"
JEI = J + "handler/jei/NtmJeiPlugin.java"
NB = J + "blocks/NtmBlocks.java"
BET = J + "blockentity/NtmBlockEntityTypes.java"
MT = J + "inventory/NtmMenuTypes.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
NMC = J + "main/NuclearTechModClient.java"
CP = J + "main/ClientProxy.java"
RP = J + "datagen/NtmRecipeProvider.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
LOOTP = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
EDITED = [HANDLER, SER, NET, JEI, NB, BET, MT, CTAB, NMC, CP, RP, BSP, LOOTP, TAGP, LP]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal25b-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
G_REC = GEN + "data/hbmsntm/recipe/rbmk_outgasser.json"
G_BS = GEN + "assets/hbmsntm/blockstates/rbmk_outgasser.json"
G_BM = GEN + "assets/hbmsntm/models/block/rbmk_outgasser.json"
G_IM = GEN + "assets/hbmsntm/models/item/rbmk_outgasser.json"
G_LOOT = GEN + "data/hbmsntm/loot_table/blocks/rbmk_outgasser.json"
G_ADV = GEN + "data/hbmsntm/advancement/recipes/misc/rbmk_outgasser.json"
GEN_NEW = [G_BS, G_BM, G_IM, G_ADV, G_LOOT, G_REC]
RES = "src/main/resources/assets/hbmsntm/"
GT = J + "gametest/RBMKOutgasserGameTests.java"
GT_DIR = J + "gametest/"
ANVIL = J + "inventory/recipes/anvil/AnvilRecipes.java"

# files the batch must only read, never change (byte-equal to the start; hashes from baseline.json)
UNTOUCHED = [BE_DIR + n for n in ("RBMKSlottedBaseBlockEntity.java", "RBMKBaseBlockEntity.java", "RBMKRodBlockEntity.java", "RBMKDials.java", "RBMKStorageBlockEntity.java",
                                  "RBMKBoilerBlockEntity.java", "IRBMKFluxReceiver.java", "RBMKColumnType.java", "RBMKType.java")] + [
    BLK_DIR + "RBMKBaseBlock.java", BLK_DIR + "RBMKStorageBlock.java", J + "blockentity/ProxyComboBlockEntity.java", J + "config/CommonConfig.java",
    J + "inventory/fluid/tank/FluidTank.java", J + "inventory/fluid/Fluids.java", J + "inventory/recipes/FuelPoolRecipes.java", J + "handler/FuelPoolRecipeClientSync.java",
    J + "network/toclient/FuelPoolRecipesPacket.java", ANVIL, J + "datagen/NtmItemModelProvider.java", J + "gametest/SmokeTestSupport.java",
    J + "gametest/RBMKReactorGameTests.java", J + "gametest/RBMKRecyclingGameTests.java", J + "handler/neutron/NeutronHandler.java", J + "handler/neutron/NeutronStream.java"]
CONCURRENT = {"migration/GOAL25C.md", "migration/GOAL25D.md", "migration/GOAL25-THREAD-PROMPTS.md", "migration/GOAL25A.md"}

O = "src/main/java/com/hbm/"
O_TE = O + "tileentity/machine/rbmk/TileEntityRBMKOutgasser.java"
O_REC = O + "inventory/recipes/OutgasserRecipes.java"
O_NH = O + "handler/neutron/RBMKNeutronHandler.java"
O_CON = O + "inventory/container/ContainerRBMKOutgasser.java"
O_GUI = O + "inventory/gui/GUIRBMKOutgasser.java"
O_BLK = O + "blocks/machine/rbmk/RBMKOutgasser.java"
O_CM = O + "main/CraftingManager.java"
O_ANV = O + "inventory/recipes/anvil/AnvilRecipes.java"
O_PROXY = O + "tileentity/TileEntityProxyCombo.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"
O_FILES = dict(te=O_TE, rec=O_REC, nh=O_NH, con=O_CON, gui=O_GUI, blk=O_BLK, cm=O_CM, anv=O_ANV, proxy=O_PROXY)

# V1: every cited original line, {file key: {line: needle}}; a moved or changed line fails V1
ANCHORS = {
    "te": {38: "public static final int duration = 10000;", 43: "super(2);", 44: "gas = new FluidTank(Fluids.TRITIUM, 64000);", 46: "setOutputTanks(gas)",
           51: '"container.rbmkOutgasser"', 57: "if(!worldObj.isRemote) {", 59: "ports.update(", 62: "if(!canProcess()) this.progress = 0;", 65: "super.updateEntity();",
           71: "if(canProcess()) {", 73: "double efficiency = Math.min(1 - stream.fluxRatio * 0.8, 1);",
           75: "progress += stream.fluxQuantity * efficiency * RBMKDials.getOutgasserMod(worldObj);", 77: "if(progress > duration) {", 78: "process();", 79: "this.markDirty();",
           86: "if(slots[0] == null)", 87: "return false;", 89: "OutgasserRecipe output = OutgasserRecipes.getOutput(slots[0]);", 91: "if(output == null) return false;",
           92: "if(output.fusionOnly) return false;", 94: "FluidStack fluid = output.liquidOutput;", 96: "if(fluid != null) {",
           97: "if(gas.getTankType() != fluid.type && gas.getFill() > 0) return false;", 98: "gas.setTankType(fluid.type);",
           99: "if(gas.getFill() + fluid.fill > gas.getMaxFill()) return false;", 102: "ItemStack out = output.solidOutput;", 104: "if(slots[1] == null || out == null)", 105: "return true;",
           107: "return slots[1].getItem() == out.getItem() && slots[1].getItemDamage() == out.getItemDamage() && slots[1].stackSize + out.stackSize <= slots[1].getMaxStackSize();",
           112: "OutgasserRecipe output = OutgasserRecipes.getOutput(slots[0]);", 113: "this.decrStackSize(0, 1);", 114: "this.progress = 0;",
           116: "if(output.liquidOutput != null) {", 117: "gas.setFill(gas.getFill() + output.liquidOutput.fill);", 122: "if(out != null) {", 123: "if(slots[1] == null) {",
           124: "slots[1] = out.copy();", 126: "slots[1].stackSize += out.stackSize;", 134: "int count = 4 + worldObj.rand.nextInt(2);", 136: "for(int i = 0; i < count; i++) {",
           137: "spawnDebris(DebrisType.BLANK);", 140: "super.onMelt(reduce);", 145: "return RBMKNeutronHandler.RBMKType.OUTGASSER;", 150: "return ColumnType.OUTGASSER;",
           156: 'data.setInteger("gas", this.gas.getFill());', 157: 'data.setInteger("maxGas", this.gas.getMaxFill());', 158: 'data.setShort("type", (short)this.gas.getTankType().getID());',
           159: 'data.setDouble("progress", this.progress);', 167: 'this.progress = nbt.getDouble("progress");', 168: 'this.gas.readFromNBT(nbt, "gas");',
           175: 'nbt.setDouble("progress", this.progress);', 176: 'this.gas.writeToNBT(nbt, "gas");', 181: "super.serialize(buf);", 182: "this.gas.serialize(buf);",
           183: "buf.writeDouble(this.progress);", 188: "super.deserialize(buf);", 189: "this.gas.deserialize(buf);", 190: "this.progress = buf.readDouble();",
           195: "return OutgasserRecipes.getOutput(itemStack) != null && i == 0;", 200: "return i == 1;", 205: "return new int[] {0, 1};", 210: "return new FluidTank[] {gas};",
           215: "return new FluidTank[] {gas};"},
    "rec": {35: "LI.block()", 36: "LI.ingot()", 37: "LI.dust()", 38: "LI.dustTiny()", 41: "GOLD.ingot()", 42: "GOLD.nugget()", 43: "GOLD.dust()", 46: "TH232.ingot()",
            47: "TH232.nugget()", 48: "TH232.billet()", 51: "Blocks.brown_mushroom", 52: "Blocks.red_mushroom", 53: "Items.mushroom_stew", 55: "COAL.gem()", 56: "COAL.dust()",
            57: "COAL.block()", 59: "PVC.ingot()", 61: "EnumTarType.COAL)),", 62: "EnumTarType.WAX)),", 67: "ComparableStack comp = new ComparableStack(input).makeSingular();",
            69: "if(recipes.containsKey(comp)) {", 73: "String[] dictKeys = comp.getDictKeys();", 105: 'return "hbmIrradiation.json";',
            117: 'this.readAStack(obj.get("input").getAsJsonArray());', 121: 'if(obj.has("solidOutput"))', 122: 'if(obj.has("fluidOutput"))',
            125: 'if(obj.has("fusionOnly") && obj.get("fusionOnly").getAsBoolean()) or.fusionOnly();', 127: "if(solidOutput != null || fluidOutput != null) {",
            136: 'writer.name("input");', 139: "if(rec.getValue().solidOutput != null) {", 144: "if(rec.getValue().liquidOutput != null) {",
            149: 'writer.name("fusionOnly").value(rec.getValue().fusionOnly);'},
    "nh": {304: 'if(!(boolean) targetNode.data.get("hasLid"))', 305: "ChunkRadiationManager.proxy.incrementRad(", 312: "if(nodeTE instanceof IRBMKFluxReceiver) {",
           315: "if(type == RBMKType.ROD) {", 323: "} else if(type == RBMKType.OUTGASSER) {", 324: "TileEntityRBMKOutgasser outgasser = ((TileEntityRBMKOutgasser) column);",
           326: "if(outgasser.canProcess()) {", 327: "column.receiveFlux(this);", 328: "return;", 332: "} else if(type == RBMKType.CONTROL_ROD) {"},
    "con": {19: "this.addSlotToContainer(new Slot(tedf, 0, 48, 45));", 20: "this.addSlotToContainer(new SlotCraftingOutput(invPlayer.player, tedf, 1, 112, 69));",
            24: "8 + j * 18, 84 + i * 18 + 20", 29: "8 + i * 18, 142 + 20", 42: "if(par2 == 0) {", 43: "this.mergeItemStack(var5, rbmk.getSizeInventory(), this.inventorySlots.size(), true)",
            46: "} else if(!this.mergeItemStack(var5, 0, 1, false)) {"},
    "gui": {16: '":textures/gui/reactors/gui_rbmk_outgasser.png"', 23: "this.xSize = 176;", 24: "this.ySize = 186;",
            31: "rod.gas.renderTankInfo(this, mouseX, mouseY, guiLeft + 112, guiTop + 21, 16, 48);", 38: "6, 4210752", 39: "this.ySize - 96 + 2",
            48: "int progress = (int) (rod.progress * 13 / rod.duration);", 49: "drawTexturedModalRect(guiLeft + 82, guiTop + 50, 176, 0, progress, 6);",
            51: "int gas = (int) (rod.gas.getFill() * 42 / rod.gas.getMaxFill());", 52: "drawTexturedModalRect(guiLeft + 115, guiTop + 66 - gas, 188, 42 - gas, 10, gas);"},
    "blk": {15: "if(meta >= this.offset)", 16: "return new TileEntityRBMKOutgasser();", 18: "if(hasExtra(meta))", 19: "return new TileEntityProxyCombo(true, false, true);",
            21: "return null;", 26: "return openInv(world, x, y, z, player);", 31: "return this.renderIDPassive;"},
    "cm": {769: "addRecipeAuto(new ItemStack(ModBlocks.rbmk_outgasser, 1), new Object[] { \"GHG\", \"GRG\", \"GTG\", 'G', ModBlocks.steel_grate, 'H', Blocks.hopper, 'T', ModItems.tank_steel, 'R', ModBlocks.rbmk_blank });"},
    "anv": {915: "new ComparableStack(ModBlocks.rbmk_outgasser)", 916: "new AnvilOutput(new ItemStack(ModBlocks.rbmk_blank, 1))", 917: "new AnvilOutput(new ItemStack(ModBlocks.steel_grate, 6))",
            918: "new AnvilOutput(new ItemStack(ModItems.tank_steel, 1))", 919: "new AnvilOutput(new ItemStack(Blocks.hopper, 1))", 920: "}).setTier(4));"},
    "proxy": {135: "if(!fluid) return EMPTY_TANKS;", 137: "if(getCoreObject() instanceof IFluidReceiverMK2) {"},
}

# V8: (NEO key, original key, en_US.lang line, zh_CN.lang line); every entry is upstream (add_zh.py)
UP = [("block.hbmsntm.rbmk_outgasser", "tile.rbmk_outgasser.name", 6243, 5352), ("container.rbmkOutgasser", "container.rbmkOutgasser", 799, 637),
      ("tile.rbmk.dodd.progress", "tile.rbmk.dodd.progress", 6272, 5953), ("tile.rbmk.dodd.gas", "tile.rbmk.dodd.gas", 6273, 5954),
      ("tile.rbmk.dodd.gas_type", "tile.rbmk.dodd.gas_type", 6286, 5967), ("tile.rbmk.dodd.gas_p", "tile.rbmk.dodd.gas_p", 6291, 5972),
      ("tile.rbmk.dodd.gas_max", "tile.rbmk.dodd.gas_max", 6296, 5977)]
NEW_KEYS = [u[0] for u in UP]

IMPORTS = [("textures/blocks/rbmk/rbmk_outgasser_" + n + ".png", "textures/block/rbmk/rbmk_outgasser_" + n + ".png") for n in ("side", "top", "cover_top", "cover_side", "glass_top", "glass_side")] + [
    ("textures/gui/reactors/gui_rbmk_outgasser.png", "textures/gui/reactors/gui_rbmk_outgasser.png")]
IMPORT_PATHS = [RES + n for _, n in IMPORTS]

# V4: the handoff's item table (original ore dictionary / item -> NEO expression in OutgasserRecipes.registerDefaults)
INPUT_TABLE = {"LI.block()": "NtmBlocks.BLOCK_LITHIUM", "LI.ingot()": "NtmItems.LITHIUM.get()", "LI.dust()": "NtmItems.POWDER_LITHIUM.get()",
               "LI.dustTiny()": "NtmItems.POWDER_LITHIUM_TINY.get()", "GOLD.ingot()": "Items.GOLD_INGOT", "GOLD.nugget()": "Items.GOLD_NUGGET",
               "GOLD.dust()": "NtmItems.POWDER_GOLD.get()", "TH232.ingot()": "NtmItems.INGOT_TH232.get()", "TH232.nugget()": "NtmItems.NUGGET_TH232.get()",
               "TH232.billet()": "NtmItems.BILLET_TH232.get()", "COAL.gem()": "Items.COAL", "COAL.dust()": "NtmItems.POWDER_COAL.get()", "COAL.block()": "Items.COAL_BLOCK",
               "PVC.ingot()": "NtmItems.INGOT_PVC.get()", "DictFrame.fromOne(ModItems.oil_tar,EnumTarType.COAL)": "NtmItems.OIL_TAR_COAL.get()",
               "DictFrame.fromOne(ModItems.oil_tar,EnumTarType.WAX)": "NtmItems.OIL_TAR_WAX.get()"}
MUSHROOM_INPUTS = {"Blocks.brown_mushroom", "Blocks.red_mushroom", "Items.mushroom_stew"}
OUTPUT_TABLE = {"newItemStack(ModItems.ingot_au198)": ("NtmItems.INGOT_AU198.get()", 1), "newItemStack(ModItems.nugget_au198)": ("NtmItems.NUGGET_AU198.get()", 1),
                "newItemStack(ModItems.powder_au198)": ("NtmItems.POWDER_AU198.get()", 1), "newItemStack(ModItems.ingot_thorium_fuel)": ("NtmItems.INGOT_THORIUM_FUEL.get()", 1),
                "newItemStack(ModItems.nugget_thorium_fuel)": ("NtmItems.NUGGET_THORIUM_FUEL.get()", 1), "newItemStack(ModItems.billet_thorium_fuel)": ("NtmItems.BILLET_THORIUM_FUEL.get()", 1),
                "DictFrame.fromOne(ModItems.oil_tar,EnumTarType.COAL,1)": ("NtmItems.OIL_TAR_COAL.get()", 1), "DictFrame.fromOne(ModItems.oil_tar,EnumTarType.COAL,9)": ("NtmItems.OIL_TAR_COAL.get()", 9),
                "newItemStack(ModItems.ingot_c4)": ("NtmItems.INGOT_C4.get()", 1)}
ORIGINAL_ROW_LINES = [35, 36, 37, 38, 41, 42, 43, 46, 47, 48, 51, 52, 53, 55, 56, 57, 59, 61, 62]

GT_MARK = "[hbm-rbmk-outgasser]"
START_GAMETESTS = 215
HASH_SKIP = ("__pycache__",)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(text):
    return text.replace("\r\n", "\n")


def read_text(path):
    return Path(path).read_bytes().decode("utf-8")


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, cid, ok, label, detail=""):
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:1200]))
        return ok

    def failed(self):
        return [i["id"] for i in self.items if i["status"] == "FAIL"]

    def passed(self):
        return sum(1 for i in self.items if i["status"] == "PASS")


def guarded(ck, section, function, *args):
    """A crash in a section is a failing check (id <section>.crash), never an aborted run."""
    try:
        return function(ck, *args)
    except Exception as error:  # noqa: BLE001 - reported as a check
        ck(f"{section}.crash", False, f"{section} raised {type(error).__name__}", repr(error))
        return None


# ---------------------------------------------------------------- text helpers (as verify_goal25a_rbmk_recycling.py)

@functools.lru_cache(maxsize=256)
def blank_comments(text):
    """Same length as text, comments replaced by spaces (newlines kept), string and char literals untouched."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append("".join(ch if ch in "\r\n" else " " for ch in text[i:j]))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch in "\r\n" else " " for ch in text[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_delim(code, open_index, opener, closer):
    assert code[open_index] == opener
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced " + opener)


def match_brace(code, open_index):
    return match_delim(code, open_index, "{", "}")


def squash_lit(code):
    """Remove every whitespace character outside string and char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == "\\" else 1
            out.append(code[i:j + 1])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def method_span(text, signature):
    """(open_brace, close_brace, blanked code) of the unique method whose header contains signature."""
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def numnorm(code):
    """Drop the D/F suffix and the underscores of number literals outside string and char literals."""
    out, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in "\"'":
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == "\\" else 1
            out.append(code[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and code[j] not in "\"'":
                j += 1
            seg = re.sub(r"(?<![\w.])(\d[\d_]*(?:\.\d+)?)[DdFf](?!\w)", lambda m: m.group(1).replace("_", ""), code[i:j])
            out.append(re.sub(r"(?<![\w.])(\d+(?:_\d+)+)(?![\w.])", lambda m: m.group(1).replace("_", ""), seg))
            i = j
    return "".join(out)


def sq(code):
    return squash_lit(numnorm(code))


def body(text, signature):
    o, c, code = method_span(text, signature)
    return sq(code[o + 1:c])


def code_of(text):
    return sq(blank_comments(lf(text)))


def rewrite(s, table):
    for pat, rep in table:
        s = re.sub(pat, rep, s)
    return s


def lit(old, new):
    """A literal replacement rule for rewrite()."""
    return re.escape(old), new.replace("\\", "\\\\")


def json_pairs(text):
    dups = []

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(k for k in set(keys) if keys.count(k) > 1)
        return dict(pairs)
    return json.loads(text, object_pairs_hook=hook), dups


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def json_edit(text, edit):
    data = json.loads(text)
    edit(data)
    eol = "\r\n" if "\r\n" in text else "\n"
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", eol) + eol


def parse_lang(text):
    d = {}
    for i, l in enumerate(lf(text).lstrip("﻿").split("\n"), 1):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            d.setdefault(k, []).append((v.rstrip("\r"), i))
    return d


def at_lines(lines, expected):
    """expected: {line number: needle}; returns the (line, needle, actual) triples that do not hold. Lines are 1-based."""
    return [(n, needle, lines[n - 1].strip()[:120] if n <= len(lines) else None) for n, needle in expected.items() if n > len(lines) or needle not in lines[n - 1]]


def placeholders(s):
    return sorted(re.findall(r"%(?:\d+\$)?[sdf]|%%|\$", s))


class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file and sha256 of every file under src and migration."""

    def __init__(self, files, tree):
        self.files, self.tree = files, tree

    def copy(self):
        return State(dict(self.files), dict(self.tree))

    def text(self, path):
        return self.files[path].decode("utf-8")

    def has(self, path):
        return path in self.files

    def set_bytes(self, path, data):
        self.files[path] = data
        self.tree[path] = sha(data)

    def set_text(self, path, text):
        self.set_bytes(path, text.encode("utf-8"))

    def delete(self, path):
        self.files.pop(path, None)
        self.tree.pop(path, None)


class Inputs:
    pass


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root)


def hash_tree():
    hashes = {}
    for top in ("src", "migration"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def otext(path):
    return lf(read_text(ORIGINAL / path))


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


def first_diff(a, b, width=90):
    n = min(len(a), len(b))
    i = next((k for k in range(n) if a[k] != b[k]), n)
    return f"@{i}: expected ...{a[max(0, i - width):i + width]}... got ...{b[max(0, i - width):i + width]}..."


def contains_all(ck, cid, label, code, *needles):
    miss = [n for n in needles if n not in code]
    return ck(cid, not miss, label, miss)


def ordered(code, *frags):
    """True when every fragment occurs and in this order (first occurrences after the previous one)."""
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start, inp.start_hash_ok = {}, {}
    for base, _, names in os.walk(START):
        for name in names:
            f = Path(base) / name
            rel = f.relative_to(START).as_posix()
            data = f.read_bytes()
            inp.start_hash_ok[rel] = sha(data) == inp.base_files.get(rel)
            inp.start[rel] = data.decode("utf-8")
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o = {name: otext(path) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    tree = hash_tree()
    files = {}
    load = set(NEW_CLASSES + EDITED + UNTOUCHED + [ZH, MAP, OWN, EN, STAMP, PICK, GT, J + "handler/FuelPoolRecipeClientSync.java", J + "main/NuclearTechMod.java"]
               + GEN_NEW + IMPORT_PATHS)
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.own = json.loads(files[OWN].decode("utf-8")) if OWN in files else None
    inp.o_res = {}
    for orig, neo in IMPORTS:
        f = ORIGINAL / (O_RES + orig)
        inp.o_res[RES + neo] = f.read_bytes() if f.exists() else None
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.baseline["copied_scope"]) == 31 and all(p in inp.start or p not in inp.base_files for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, 31 in copied_scope) hashes to its baseline.json entry", bad)
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 783b6d13", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    needed = NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, PICK] + GEN_NEW
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.untouched-in-baseline", all(p in inp.base_files for p in UNTOUCHED), "every file the batch must leave alone exists in baseline.json", [p for p in UNTOUCHED if p not in inp.base_files])


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    rows = [n for n, l in enumerate(inp.ol["rec"], 1) if l.strip().startswith("recipes.put(") and 32 <= n <= 63]
    ck("V1.rec-row-count", rows == ORIGINAL_ROW_LINES, "registerDefaults has 19 recipes.put rows at :35-38, 41-43, 46-48, 51-53, 55-57, 59, 61-62 (3 of them mushrooms)", rows)
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", bool(e) and bool(z) and e[0][1] == en_line and z[0][1] == zh_line, f"{okey} is at en_US.lang:{en_line} and zh_CN.lang:{zh_line}",
           (e and e[0][1], z and z[0][1]))


# ---------------------------------------------------------------- V2 block entity and block against V1

def ocode_line(inp, key, line):
    return sq(blank_comments(inp.ol[key][line - 1]))


def ocode_lines(inp, key, first, last):
    return sq(blank_comments("\n".join(inp.ol[key][first - 1:last])))


def v2_block_entity(ck, inp, st):
    be = lf(st.text(OBE))
    code = code_of(be)
    contains_all(ck, "V2.constants", "DURATION 10000 (:38), two slots (:43), the TRITIUM 64000 tank (:44), container.rbmkOutgasser (:51)", code,
                 "publicstaticfinalintDURATION=" + ocode_line(inp, "te", 38).split("=")[1], "super(NtmBlockEntityTypes.RBMK_OUTGASSER.get(),pos,state,2);",
                 "publicFluidTankgas=" + rewrite(ocode_line(inp, "te", 44), [lit("gas=", "")]), 'return"container.rbmkOutgasser";')
    rf = body(be, "public void receiveFlux(NeutronStream stream)")
    want = rewrite(ocode_lines(inp, "te", 71, 81), [lit("getOutgasserMod(worldObj)", "getOutgasserMod()"), lit("progress>duration", "progress>DURATION"), lit("this.markDirty();", "this.setChanged();")])
    ck("V2.receive-flux", rf == want, "receiveFlux: canProcess gate, efficiency min(1 - ratio * 0.8, 1), progress += flux * efficiency * mod, process when progress > DURATION (original :71-81)", first_diff(want, rf))
    cp = body(be, "public boolean canProcess()")
    l = lambda n: ocode_line(inp, "te", n)  # noqa: E731
    fluid_line = rewrite(l(94), [lit("output.liquidOutput", "output.fluidOutput")])
    solid = rewrite(l(107), [lit("returnslots[1].getItem()==out.getItem()&&slots[1].getItemDamage()==out.getItemDamage()&&slots[1].stackSize+out.stackSize<=slots[1].getMaxStackSize();",
                                 "returnItemStack.isSameItemSameComponents(slot,out)&&slot.getCount()+out.getCount()<=slot.getMaxStackSize();")])
    ck("V2.can-process-order", ordered(cp, "if(input.isEmpty())returnfalse;", "OutgasserRecipeoutput=OutgasserRecipes.getOutput(input);", l(91), l(92), fluid_line, l(96), l(97), l(98), l(99),
                                        l(102), "if(slot.isEmpty()||out.isEmpty())returntrue;", solid) and cp.endswith(solid),
       "canProcess in the original order (:86-107): empty input, row, fusionOnly, other gas while not empty, setTankType BEFORE the capacity test, then the solid rules", cp[:700])
    ck("V2.can-process-side-effect-commented", "Upstream-shared side effect" in be, "the setTankType side effect is commented as upstream-shared")
    pr = body(be, "private void process()")
    want_pr = ("OutgasserRecipeoutput=OutgasserRecipes.getOutput(this.slots.get(0));this.removeItem(0,1);" + l(114)
               + rewrite(ocode_lines(inp, "te", 116, 118), [lit("output.liquidOutput", "output.fluidOutput")]) + l(120)
               + "if(!out.isEmpty()){if(this.slots.get(1).isEmpty()){this.slots.set(1,out.copy());}else{this.slots.get(1).grow(out.getCount());}}")
    ck("V2.process", pr == want_pr, "process: one input, progress 0, the gas into the tank, the solid output into slot 1 (original :112-128)", first_diff(want_pr, pr))
    om = body(be, "public void onMelt(int reduce)")
    want_om = rewrite(l(134), [lit("worldObj.rand", "this.level.random")]) + ocode_lines(inp, "te", 136, 138) + l(140)
    ck("V2.on-melt", om == want_om, "onMelt: 4 + nextInt(2) BLANK debris, then the base onMelt (original :134-140)", first_diff(want_om, om))
    upd = body(be, "public void updateEntity()")
    ck("V2.update", ordered(upd, "if(world!=null&&!world.isClientSide){", "for(DirPoscon:this.getPortConnections()){this.tryProvide(gas,world,con);}", l(62), "}super.updateEntity();")
       and upd.endswith("super.updateEntity();") and "trySubscribe" not in code,
       "updateEntity: server side the ports provide only (setOutputTanks, :46/:59-60), then !canProcess() -> progress = 0 (:62), then super.updateEntity() on both sides (:65)", upd)
    ck("V2.types", body(be, "public RBMKType getRBMKType()") == "returnRBMKType.OUTGASSER;" and body(be, "public RBMKColumnType getConsoleType()") == "returnRBMKColumnType.OUTGASSER;",
       "getRBMKType OUTGASSER (:145) and getConsoleType OUTGASSER (:150)")
    con = body(be, "public CompoundTag getNBTForConsole()")
    keys = [rewrite(l(n), [lit("data.setInteger", "data.putInt"), lit("data.setShort", "data.putShort"), lit("data.setDouble", "data.putDouble")]) for n in (156, 157, 158, 159)]
    ck("V2.console", ordered(con, "CompoundTagdata=super.getNBTForConsole();", *keys, "returndata;"), "console keys gas, maxGas, type (short), progress (double) after the base heat/maxHeat (:156-159)", con)
    load = body(be, "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    save = body(be, "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    nbt = lambda n: rewrite(l(n), [lit("nbt.setDouble", "tag.putDouble"), lit("nbt.getDouble", "tag.getDouble"), lit("(nbt,", "(tag,")])  # noqa: E731
    ck("V2.nbt", load == "super.loadAdditional(tag,registries);" + nbt(167) + nbt(168) and save == "super.saveAdditional(tag,registries);" + nbt(175) + nbt(176),
       "NBT: progress as a double and the tank under \"gas\" after super (original :167-168, :175-176)", (load, save))
    ser = body(be, "public void serialize(RegistryFriendlyByteBuf buf)")
    des = body(be, "public void deserialize(RegistryFriendlyByteBuf buf)")
    ck("V2.sync", ser == ocode_lines(inp, "te", 181, 183) and des == ocode_lines(inp, "te", 188, 190), "serialize / deserialize: super, the tank, progress (original :181-183, :188-190)", (ser, des))
    place = body(be, "public boolean canPlaceItem(int slot, ItemStack stack)")
    ck("V2.can-place", place == "if(slot!=0)returnfalse;return(this.level!=null&&this.level.isClientSide?OutgasserRecipeClientSync.getOutput(stack):OutgasserRecipes.getOutput(stack))!=null;",
       "canPlaceItem: slot 0 and a row (original :195), the client asks its synchronized table", place)
    ck("V2.slots-face", body(be, "public int[] getSlotsForFace(Direction direction)") == "returnSLOTS;" and "privatestaticfinalint[]SLOTS=newint[]{0,1};" in code
       and body(be, "public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction)") == "returnindex==1;",
       "getSlotsForFace {0, 1} (:205), canTakeItemThroughFace only slot 1 (:200)")
    tanks = "returnnewFluidTank[]{gas};"
    ck("V2.tanks", body(be, "public FluidTank[] getAllTanks()") == tanks and body(be, "public FluidTank[] getSendingTanks()") == tanks and l(210) == tanks,
       "getAllTanks / getSendingTanks {gas} (:210, :215)")
    ck("V2.implements", "classRBMKOutgasserBlockEntityextendsRBMKSlottedBaseBlockEntityimplementsIRBMKFluxReceiver,IFluidStandardSenderMK2{" in code,
       "extends the slotted base, implements IRBMKFluxReceiver and IFluidStandardSenderMK2 only (no receiver, no OC component)")
    blk = code_of(st.text(OBLK))
    ck("V2.block", "returnswitch(state.getValue(TYPE)){caseCORE->newRBMKOutgasserBlockEntity(pos,state);caseEXTRA->newProxyComboBlockEntity(pos,state).inventory().fluid();default->null;};" in blk,
       "newBlockEntity: core -> the channel, extra -> ProxyCombo inventory + fluid (original TileEntityProxyCombo(true, false, true) :18-19), dummies none (:21)")
    contains_all(ck, "V2.block-shape", "CODEC, core-only ticker, opens the GUI without an item (:26)", blk, "publicstaticfinalMapCodec<RBMKOutgasserBlock>CODEC=simpleCodec(RBMKOutgasserBlock::new);",
                 "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;", "returnthis.standardOpenBehavior(level,pos,player);")
    unchanged = [p for p in UNTOUCHED if (p.startswith(BE_DIR) or p.startswith(BLK_DIR) or "ProxyCombo" in p) and not hashed_equal(inp, st, p)]
    ck("V2.base-unchanged", not unchanged, "the RBMK base, slotted base, rod, boiler, storage, dials, type enums and ProxyComboBlockEntity are byte-equal to the start", unchanged)


# ---------------------------------------------------------------- V3 neutron handler

def outgasser_branch(inp):
    """The original :312-330 plus the following else-if head, with the NEO class names."""
    return rewrite(ocode_lines(inp, "nh", 312, 330) + "}elseif(type==RBMKType.CONTROL_ROD)", [lit("TileEntityRBMKRod", "RBMKRodBlockEntity"),
                   lit("((TileEntityRBMKOutgasser)column)", "(RBMKOutgasserBlockEntity)column"), lit("TileEntityRBMKOutgasser", "RBMKOutgasserBlockEntity")])


def v3_handler(ck, inp, st):
    live = code_of(st.text(HANDLER))
    want = outgasser_branch(inp)
    ck("V3.branch", live.count(want) == 1, "the IRBMKFluxReceiver block equals the original :312-332: ROD, then else-if OUTGASSER with the canProcess gate and receiveFlux(this); return; inside it",
       first_diff(want, live[live.find("if(nodeTEinstanceofIRBMKFluxReceiver)"):]))
    branch = re.search(r"elseif\(type==RBMKType\.OUTGASSER\)\{(.*?)\}\}elseif\(type==RBMKType\.CONTROL_ROD\)", live)
    inner = branch[1] if branch else ""
    gate_at, flux_at = inner.find("if(outgasser.canProcess()){"), inner.find("receiveFlux(this);")
    ck("V3.gate", inner.count("receiveFlux(this);return;") == 1 and 0 <= gate_at < flux_at,
       "receiveFlux(this); return; occurs once, only inside the canProcess gate; without it the loop goes on (no continue / return)", inner)
    start = code_of(inp.start[HANDLER])
    imp = "importcom.hbm.blockentity.machine.rbmk.RBMKOutgasserBlockEntity;"
    branch_neo = "}elseif(type==RBMKType.OUTGASSER){RBMKOutgasserBlockEntityoutgasser=(RBMKOutgasserBlockEntity)column;if(outgasser.canProcess()){column.receiveFlux(this);return;}"
    reduced = live.replace(imp, "", 1).replace(branch_neo, "", 1)
    ck("V3.rest-unchanged", reduced == start, "apart from the import and the OUTGASSER branch the handler's code equals the start copy (comment changes allowed)", first_diff(start, reduced))


# ---------------------------------------------------------------- V4 recipe table

def original_rows(inp):
    rows = []
    rx = re.compile(r"recipes\.put\(new(?:OreDictStack|ComparableStack)\((.+?)\),newOutgasserRecipe\((null|.+?),(null|newFluidStack\(Fluids\.(\w+),(\d+)\))\)\);$")
    for n in ORIGINAL_ROW_LINES:
        m = rx.match(ocode_line(inp, "rec", n))
        if not m:
            raise ValueError(f"original OutgasserRecipes :{n} does not parse: {ocode_line(inp, 'rec', n)}")
        rows.append(dict(line=n, input=m[1], solid=None if m[2] == "null" else m[2], fluid=m[4], amount=int(m[5]) if m[5] else None))
    return rows


def expected_calls(inp):
    calls, export = [], []
    for r in original_rows(inp):
        if r["input"] in MUSHROOM_INPUTS:
            continue
        neo_in = INPUT_TABLE[r["input"]]
        solid = OUTPUT_TABLE[r["solid"]] if r["solid"] else None
        if solid is None:
            calls.append(f"gas({neo_in},Fluids.{r['fluid']},{r['amount']})")
        elif r["fluid"] is None:
            if solid[1] != 1:
                raise ValueError("a solid-only row with count != 1")
            calls.append(f"solid({neo_in},{solid[0]})")
        else:
            calls.append(f"both({neo_in},{solid[0]},{solid[1]},Fluids.{r['fluid']},{r['amount']})")
        export.append(dict(original_line=r["line"], input=neo_in, solid_output=solid and dict(item=solid[0], count=solid[1]),
                           fluid_output=r["fluid"] and dict(fluid=r["fluid"], amount=r["amount"]), fusionOnly=False))
    return calls, export


def v4_recipes(ck, inp, st, facts=None):
    rec = lf(st.text(OREC))
    code = code_of(rec)
    calls, export = expected_calls(inp)
    reg = body(rec, "public void registerDefaults()")
    live = [c + ")" for c in reg.split(");") if c]
    ck("V4.default-rows", live == calls and len(calls) == 16, "registerDefaults: the 16 original rows in the original order (19 minus the 3 mushroom rows), each through the handoff's item table",
       first_diff("\n".join(calls), "\n".join(live)))
    helpers = [body(rec, s) for s in ("private void gas(ItemLike input, FluidType type, int amount)", "private void solid(ItemLike input, ItemLike output)",
                                      "private void both(ItemLike input, ItemLike output, int count, FluidType type, int amount)")]
    ck("V4.helpers", helpers == ["add(newOutgasserRecipe(newComparableStack(input.asItem(),1,0),ItemStack.EMPTY,newFluidStack(type,amount),false));",
                                 "add(newOutgasserRecipe(newComparableStack(input.asItem(),1,0),newItemStack(output),null,false));",
                                 "add(newOutgasserRecipe(newComparableStack(input.asItem(),1,0),newItemStack(output,count),newFluidStack(type,amount),false));"],
       "the row helpers: exact item META 0, count 1, no default row is fusionOnly", helpers)
    ck("V4.file-name", body(rec, "public String getFileName()") == 'return' + ocode_line(inp, "rec", 105)[6:], "getFileName is hbmIrradiation.json (:105)")
    rr = body(rec, "public void readRecipe(JsonElement element)")
    ck("V4.read-fields", ordered(rr, 'array(row.get("input"),"input")', 'row.has("solidOutput")', 'row.has("fluidOutput")', 'row.has("fusionOnly")&&bool(row.get("fusionOnly"))',
                                 "add(newOutgasserRecipe(input,solid,fluid,fusionOnly));"), "readRecipe reads input, solidOutput, fluidOutput, fusionOnly (original :117-125)", rr)
    wr = body(rec, "public void writeRecipe(Object value, JsonWriter writer)")
    ck("V4.write-fusion-only", ordered(wr, 'writer.name("input");', 'if(row.hasSolidOutput()){writer.name("solidOutput");', 'if(row.fluidOutput!=null){writer.name("fluidOutput");')
       and wr.endswith('}writer.name("fusionOnly").value(row.fusionOnly);'), "writeRecipe writes input, the present outputs and ALWAYS fusionOnly (original :136-149)", wr[-200:])
    ck("V4.no-output-rejected", 'if(this.solidOutput.isEmpty()&&this.fluidOutput==null)throwinvalid(' in code, "a row with neither output is rejected (the original :127 drops it)")
    stream = body(rec, "public void readRecipeStream(Reader reader)")
    snap = body(rec, "private static List<OutgasserRecipe> readSnapshot(String json, boolean lenient)")
    ck("V4.lenient-file", "List<OutgasserRecipe>replacement=readSnapshot(text.toString(),true);" in stream and "if(lenient)handler.readRecipeLenient(rows.get(i),i);elsehandler.readRecipe(rows.get(i));" in snap
       and stream.endswith("table.clear();table.addAll(replacement);"), "the config file is read leniently per row (readRecipeLenient) into a replacement that only then replaces the table", (stream[-200:], snap))
    ck("V4.strict-snapshot", body(rec, "public static List<OutgasserRecipe> readSnapshot(String json)") == "returnreadSnapshot(json,false);"
       and body(rec, "public static String writeSnapshot()") == "Stringresult=writeRows(RECIPES);readSnapshot(result);returnresult;", "sync snapshots and the writeSnapshot self-check are strict")
    contains_all(ck, "V4.limits", "limits: 4096 rows, 256 KiB, gas 1..64000, solid 1..64, input count 1", code, "publicstaticfinalintMAX_SYNC_RECIPES=4096;", "publicstaticfinalintMAX_SYNC_BYTES=256*1024;",
                 "publicstaticfinalintMAX_GAS=64000;", 'if(input.stacksize!=1)throwinvalid("input count must be 1");', "if(fluidOutput.fill<1||fluidOutput.fill>MAX_GAS)",
                 "if(solidOutput.getCount()<1||solidOutput.getCount()>64)", "if(rows.size()>MAX_SYNC_RECIPES)throwinvalid(", "if(text.length()+count>MAX_SYNC_BYTES)throwinvalid(")
    lookup = body(rec, "public static OutgasserRecipe getOutput(List<OutgasserRecipe> source, ItemStack stack)")
    ck("V4.lookup-order", ordered(lookup, "if(stack==null||stack.isEmpty())returnnull;", "recipe.inputinstanceofComparableStack&&recipe.input.matchesRecipe(stack,true)",
                                  "recipe.inputinstanceofTagStack&&recipe.input.matchesRecipe(stack,true)"), "getOutput: exact item rows before tag rows (original :67-80), count ignored", lookup)
    ser = code_of(st.text(SER))
    ck("V4.registered", ser.count("recipeHandlers.add(newOutgasserRecipes());") == 1 and "recipeHandlers.add(newFuelPoolRecipes());recipeHandlers.add(newOutgasserRecipes());" in ser,
       "OutgasserRecipes is registered once in registerAllHandlers, right after FuelPoolRecipes")
    ck("V4.template-through-base", '"_"+recipe.getFileName()' in ser and "writeTemplateFile" not in code and "readRecipeFile" not in code,
       "the _hbmIrradiation.json template and the file read go through SerializableRecipe (no override)")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "default-table.json").write_text(json.dumps(dict(source=f"{O_REC} @ {ORIGINAL_HEAD}", rows=export), indent=2) + "\n", encoding="utf-8")
    if facts is not None:
        facts["V4"] = dict(default_rows=len(export), export=(OUT / "default-table.json").relative_to(ROOT).as_posix())


# ---------------------------------------------------------------- V5 sync and JEI

def v5_sync_jei(ck, inp, st):
    net = code_of(st.text(NET))
    ck("V5.packet-registered", net.count("registrar.playToClient(OutgasserRecipesPacket.TYPE,OutgasserRecipesPacket.STREAM_CODEC,OutgasserRecipesPacket::handleCommon);") == 1
       and "playToServer(OutgasserRecipesPacket" not in net and 'PROTOCOL_VERSION="3"' in net, "the packet is registered once, clientbound, PROTOCOL_VERSION stays 3")
    pkt = code_of(st.text(OPKT))
    contains_all(ck, "V5.packet", "packet: hbmsntm:outgasser_recipes, bounded read, strict decode, client handler only on the client", pkt,
                 'newType<>(NuclearTechMod.withDefaultNamespace("outgasser_recipes"))', "buf.readByteArray(MAX_BYTES)", "OutgasserRecipes.encodeSnapshot(json);",
                 "context.enqueueWork(()->handleClient(packet));", "@OnlyIn(Dist.CLIENT)privatestaticvoidhandleClient(OutgasserRecipesPacketpacket){OutgasserRecipeClientSync.receive(packet.json());}")
    sync = code_of(st.text(OSYNC))
    ck("V5.sync", "publicstaticvoidsync(OnDatapackSyncEventevent){" in sync and "newOutgasserRecipesPacket(OutgasserRecipes.writeSnapshot())" in sync
       and "event.getRelevantPlayers().forEach(player->PacketDistributor.sendToPlayer(player,packet));" in sync, "OnDatapackSyncEvent sends the strict snapshot to the relevant players")
    fp = code_of(st.text(J + "handler/FuelPoolRecipeClientSync.java"))
    cs = code_of(st.text(OCSYNC))
    norm = (fp.replace("FuelPoolRecipes", "OutgasserRecipes").replace("FuelPoolRecipe", "OutgasserRecipe").replace("FuelPoolRecipeClientSync", "OutgasserRecipeClientSync")
            .replace("publicstaticbooleanisKey(ItemStackstack){returnOutgasserRecipes.isKey(getRecipes(),stack);}", "")
            .replace("publicstaticItemStackgetOutput(ItemStackstack)", "publicstaticOutgasserRecipegetOutput(ItemStackstack)")
            .replace('"Ignoringinvalidfuelpoolsnapshot;keepingthepredictable"', "").replace("fuelpool", "irradiationchannel"))
    norm = norm.replace('"Ignoring invalid fuel pool snapshot; keeping the previous table"', '"Ignoring invalid irradiation channel snapshot; keeping the previous table"')
    ck("V5.client-sync-shape", cs == norm, "OutgasserRecipeClientSync is FuelPoolRecipeClientSync with the names changed (strict read, refresh hook, logout clear; no isKey)", first_diff(norm, cs))
    jh = code_of(st.text(OJEI))
    contains_all(ck, "V5.jei-category", "category hbmsntm:irradiation, title = the block's description id (no new key), icon the channel, fusionOnly rows hidden", jh,
                 'RecipeType.create(NuclearTechMod.MODID,"irradiation",OutgasserRecipe.class)', "Component.translatable(NtmBlocks.RBMK_OUTGASSER.get().getDescriptionId())",
                 "helper.createDrawableItemLike(NtmBlocks.RBMK_OUTGASSER.asItem())", "for(OutgasserReciperecipe:OutgasserRecipeClientSync.getRecipes())if(!recipe.fusionOnly)rows.add(recipe);")
    jei = code_of(st.text(JEI))
    cats = re.findall(r"registration\.addRecipeCatalyst\(([^;]*?)IrradiationRecipeHandler\.RECIPE_TYPE\)", jei)
    ck("V5.jei-plugin", jei.count("newIrradiationRecipeHandler(guiHelper)") == 1 and len(cats) == 1 and cats[0] == "NtmBlocks.RBMK_OUTGASSER.asItem()," and
       "registration.addRecipes(IrradiationRecipeHandler.RECIPE_TYPE,this.displayedIrradiationRecipes);" in jei and "OutgasserRecipeClientSync.setRefresh(this::refreshIrradiationRecipes);" in jei
       and "OutgasserRecipeClientSync.setRefresh(null);" in jei, "the plugin registers the category once, its rows, one catalyst (rbmk_outgasser only) and the refresh hook", cats)
    common = [OBLK, OBE, OREC, OSYNC, OPKT, OCSYNC, OMENU, NB, BET, MT, SER, NET, HANDLER]
    leak = {p.rsplit("/", 1)[1]: [x for x in ("net.minecraft.client", "handler.jei", "inventory.screens", "mezz.jei") if x in st.text(p)] for p in common}
    leak = {k: v for k, v in leak.items() if v}
    ck("V5.client-isolation", not leak, "no common class imports net.minecraft.client, JEI or a screen", leak)
    refs = [p.rsplit("/", 1)[1] for p in common if "RBMKOutgasserScreen" in st.text(p) or "IrradiationRecipeHandler" in st.text(p)]
    ck("V5.client-refs", not refs and "RBMKOutgasserScreen" in st.text(NMC), "the screen is referenced only from NuclearTechModClient, the JEI category only from the JEI plugin", refs)
    be = code_of(st.text(OBE))
    ck("V5.lazy-client-branch", be.count("OutgasserRecipeClientSync.") == 1 and "this.level.isClientSide?OutgasserRecipeClientSync.getOutput(stack)" in be,
       "the block entity reaches OutgasserRecipeClientSync only on the client-side branch (the waste drum precedent)")


# ---------------------------------------------------------------- V6 menu and screen

def v6_menu_screen(ck, inp, st):
    menu = lf(st.text(OMENU))
    mc = code_of(menu)
    s0 = rewrite(ocode_line(inp, "con", 19), [lit("this.addSlotToContainer(newSlot(tedf,", "this.addSlot(newSlot(be,")])
    s1 = rewrite(ocode_line(inp, "con", 20), [lit("this.addSlotToContainer(newSlotCraftingOutput(invPlayer.player,tedf,", "this.addSlot(newSlotCraftingOutput(inventory.player,be,")])
    ck("V6.slots", ordered(mc, s0, s1, "this.playerInv(inventory,8,104,162);"), "slot 0 plain at (48, 45), slot 1 output-only at (112, 69), the player inventory at (8, 84 + 20) and the hotbar at 142 + 20 (original :19-29)", (s0, s1))
    qm = body(menu, "public ItemStack quickMoveStack(Player player, int index)")
    ck("V6.quick-move", "if(index<be.getContainerSize()){if(!this.moveItemStackTo(stack,be.getContainerSize(),this.slots.size(),true))returnItemStack.EMPTY;}elseif(!be.canPlaceItem(0,stack)||!this.moveItemStackTo(stack,0,1,false)){returnItemStack.EMPTY;}" in qm
       and "NEO-only" in menu, "quickMoveStack: both machine slots to the player (NEO-only, commented; the original :42-46 merges slot 1 back into slot 0), the player into slot 0 only with a row", qm)
    scr = lf(st.text(OSCREEN))
    sc = code_of(scr)
    gui = lambda n: ocode_line(inp, "gui", n)  # noqa: E731
    draw = [lit("drawTexturedModalRect(guiLeft+", "guiGraphics.blit(TEXTURE,this.leftPos+"), lit("guiTop+", "this.topPos+")]
    prog = rewrite(gui(48), [lit("rod.progress", "be.progress"), lit("rod.duration", "RBMKOutgasserBlockEntity.DURATION")])
    gas = rewrite(gui(51), [lit("(int)(rod.gas.getFill()*42/rod.gas.getMaxFill())", "be.gas.getFill()*42/be.gas.getMaxFill()")])
    tip = rewrite(gui(31), [lit("rod.gas.renderTankInfo(this,", "be.gas.renderTankTooltip(guiGraphics,"), lit("guiLeft+", "this.leftPos+"), lit("guiTop+", "this.topPos+")])
    contains_all(ck, "V6.screen", "screen: texture (:16), 176 x 186 (:23-24), progress * 13 / DURATION at (82, 50) from (176, 0) (:48-49), gas * 42 / max at (115, 66 - gas) from (188, 42 - gas) (:51-52), tank tooltip (112, 21, 16, 48) (:31), labels (:38-39)", sc,
                 'withDefaultNamespace("textures/gui/reactors/gui_rbmk_outgasser.png")', "this.imageWidth=176;", "this.imageHeight=186;", prog, rewrite(gui(49), draw), gas, rewrite(gui(52), draw), tip,
                 "this.imageWidth/2-this.font.width(this.title)/2,6,4210752,false", "this.playerInventoryTitle,8,this.imageHeight-96+2,4210752,false")


# ---------------------------------------------------------------- V7 registrations and datagen

def v7_registration(ck, inp, st):
    counts = {"NtmBlocks": code_of(st.text(NB)).count('register("rbmk_outgasser",'), "NtmBlockEntityTypes": code_of(st.text(BET)).count('BLOCK_ENTITY_TYPES.register("rbmk_outgasser",'),
              "NtmMenuTypes": code_of(st.text(MT)).count('reg("rbmk_outgasser",RBMKOutgasserMenu::new)'),
              "NuclearTechModClient": code_of(st.text(NMC)).count("event.register(NtmMenuTypes.RBMK_OUTGASSER.get(),RBMKOutgasserScreen::new);"),
              "ClientProxy": code_of(st.text(CP)).count("BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_OUTGASSER.get(),newRenderRBMKLid<>());"),
              "NtmCreativeTabs": code_of(st.text(CTAB)).count("output.accept(NtmBlocks.RBMK_OUTGASSER);"),
              "loot": code_of(st.text(LOOTP)).count("this.dropSelf(NtmBlocks.RBMK_OUTGASSER.get());"), "pickaxe": code_of(st.text(TAGP)).count("NtmBlocks.RBMK_OUTGASSER.get(),"),
              "blockstate": code_of(st.text(BSP)).count("NtmBlocks.RBMK_OUTGASSER}")}
    ck("V7.registrations-once", all(v == 1 for v in counts.values()), "block, BE type, menu type, screen, lid BER, creative tab, loot, pickaxe tag and blockstate list each name rbmk_outgasser once", counts)
    nb, ctab = code_of(st.text(NB)), code_of(st.text(CTAB))
    ck("V7.after-storage", ordered(nb, 'register("rbmk_storage",', 'register("rbmk_outgasser",') and "output.accept(NtmBlocks.RBMK_STORAGE);output.accept(NtmBlocks.RBMK_OUTGASSER);" in ctab
       and re.search(r'RBMK_STORAGE=register\("rbmk_storage",.*?\);publicstaticfinalDeferredBlock<Block>RBMK_OUTGASSER=', nb),
       "the block is declared right after RBMK_STORAGE, the creative tab entry right after rbmk_storage")
    storage = re.search(r'register\("rbmk_storage",\(\)->newRBMKStorageBlock\((.*?)\)\);', nb)
    og = re.search(r'register\("rbmk_outgasser",\(\)->newRBMKOutgasserBlock\((.*?)\)\);', nb)
    ck("V7.properties", bool(storage and og) and storage[1] == og[1], "the channel has the storage column's block properties", (storage and storage[1], og and og[1]))
    rec = json.loads(st.text(G_REC))
    want = {"type": "minecraft:crafting_shaped", "category": "misc", "key": {"G": {"item": "hbmsntm:steel_grate"}, "H": {"item": "minecraft:hopper"}, "R": {"item": "hbmsntm:rbmk_blank"},
                                                                              "T": {"item": "hbmsntm:tank_steel"}}, "pattern": ["GHG", "GRG", "GTG"], "result": {"count": 1, "id": "hbmsntm:rbmk_outgasser"}}
    cm = ocode_line(inp, "cm", 769)
    ck("V7.recipe", rec == want and all(f'"{p}"' in cm for p in want["pattern"]), "generated recipe hbmsntm:rbmk_outgasser = GHG / GRG / GTG with steel_grate, hopper, rbmk_blank, tank_steel -> 1 (CraftingManager.java:769)", rec)
    bm = json.loads(st.text(G_BM))
    ck("V7.models", json.loads(st.text(G_BS)) == {"variants": {"": {"model": "hbmsntm:block/rbmk_outgasser"}}} and bm == {"parent": "minecraft:block/cube_column", "textures": {
        "end": "hbmsntm:block/rbmk/rbmk_outgasser_top", "side": "hbmsntm:block/rbmk/rbmk_outgasser_side"}} and json.loads(st.text(G_IM)) == {"parent": "hbmsntm:block/rbmk_outgasser"},
       "generated blockstate, cube_column block model (top / side textures) and item model", bm)
    loot = json.loads(st.text(G_LOOT))
    ck("V7.loot", [e["name"] for p in loot["pools"] for e in p["entries"]] == ["hbmsntm:rbmk_outgasser"], "the loot table drops the block itself", loot)
    pick = json.loads(st.text(PICK))
    ck("V7.pickaxe", pick["values"].count("hbmsntm:rbmk_outgasser") == 1, "mineable/pickaxe lists rbmk_outgasser once")
    ck("V7.anvil-unchanged", hashed_equal(inp, st, ANVIL) and "AnvilRecipes.java:914-920" in st.text(RP),
       "AnvilRecipes.java is byte-equal to the start; the tier-4 recycling row (original :914-920) is recorded as not registered in NtmRecipeProvider")


# ---------------------------------------------------------------- V8 language

def v8_lang(ck, inp, st):
    en, dup_en = json_pairs(st.text(EN))
    zh, dup_zh = json_pairs(st.text(ZH))
    mp = json.loads(st.text(MAP))
    s_en, s_zh, s_mp = json.loads(inp.start[EN]), json.loads(inp.start[ZH]), json.loads(inp.start[MAP])
    lp = st.text(LP)
    want_en = {k: inp.o_en[ok][0][0] for k, ok, _, _ in UP}
    bad = {k: en.get(k) for k, v in want_en.items() if en.get(k) != v or k in s_en}
    in_provider = [k for k in NEW_KEYS if k != "block.hbmsntm.rbmk_outgasser" and f'this.add("{k}", "{want_en[k]}");' not in lp]
    ck("V8.en-new", not bad and not in_provider and f'this.add(NtmBlocks.RBMK_OUTGASSER, "{want_en["block.hbmsntm.rbmk_outgasser"]}");' in lp,
       f"the {len(want_en)} new English keys are in NtmLanguageProvider and en_us.json with the original text", (bad, in_provider))
    ck("V8.en-rest", {k: v for k, v in en.items() if k not in want_en} == s_en and not dup_en, "en_us.json: nothing but the new keys changed")
    if not all(k in zh for k in NEW_KEYS):
        ck("V8.pending", False, "zh_cn.json does not yet carry the Goal25B keys (add_zh.py not run): pending, not failed", [k for k in NEW_KEYS if k not in zh])
        return
    want_zh = {k: inp.o_zh[ok][0][0] for k, ok, _, _ in UP}
    bad = {k: zh.get(k) for k, v in want_zh.items() if zh.get(k) != v}
    ck("V8.zh-new", not bad, f"zh_cn.json has the {len(want_zh)} new entries verbatim from zh_CN.lang", bad)
    ck("V8.zh-rest", {k: v for k, v in zh.items() if k not in want_zh} == s_zh and not dup_zh and all(k not in s_zh for k in want_zh), "zh_cn.json: nothing else changed")
    ent, sent = mp["entries"], s_mp["entries"]
    bad = {}
    for k, ok, _, _ in UP:
        e = ent.get(k, {})
        if not (e.get("kind") == "upstream" and e.get("source_key") == ok and e.get("source_en") == inp.o_en[ok][0][0] and e.get("source_zh") == inp.o_zh[ok][0][0]
                and e.get("target_en") == en.get(k) and e.get("target_zh") == zh.get(k) and placeholders(e.get("source_en", "")) == placeholders(e.get("target_zh", ""))):
            bad[k] = e
    ck("V8.map-entries", not bad, "zh_cn-map.json: 7 upstream entries with the original en/zh text at the cited lines; placeholders preserved", dict(list(bad.items())[:3]))
    rest = {k: v for k, v in ent.items() if k not in want_zh} == sent
    ck("V8.map-rest", rest and {k: v for k, v in mp.items() if k != "entries"} == {k: v for k, v in s_mp.items() if k != "entries"} and len(ent) == len(sent) + len(want_zh),
       "zh_cn-map.json: nothing else changed (7 new entries)", (len(ent), len(sent)))
    eol = [p for p in (ZH, MAP) if st.files[p].count(b"\r\n") != st.files[p].count(b"\n") or b"\r\n" not in st.files[p]]
    ck("V8.crlf", not eol, "zh_cn.json and zh_cn-map.json stay CRLF throughout", eol)


# ---------------------------------------------------------------- V9 resources

def v9_resources(ck, inp, st):
    bad = [p for p in IMPORT_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V9.byte-equal", not bad and len(IMPORT_PATHS) == 7, "the six column textures and the GUI are byte-equal (SHA-256) to the original", bad)
    if inp.own is None:
        ck("V9.ownership-pending", False, "migration/goal25b-resource-ownership.json is absent: pending")
        return
    rows = {a["target_path"]: a for a in inp.own.get("assets", [])}
    wrong = [p for p in IMPORT_PATHS if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None) or rows[p].get("source_path") != O_RES + IMPORTS[IMPORT_PATHS.index(p)][0]]
    ck("V9.ownership", not wrong and len(rows) == 7 and inp.own.get("source_commit") == ORIGINAL_HEAD, "the ownership record lists the seven imports with their source paths and hashes", wrong)


# ---------------------------------------------------------------- V10 scope

ALLOWED_MIGRATION = ("migration/goal25b-",)
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                           "migration/RESOURCE-OWNERSHIP.md", "migration/GOAL25.md", "migration/GOAL25B.md", "migration/GOAL25B-ACCEPTANCE.md", MAP}


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v10_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    expected = set(NEW_CLASSES + EDITED + [ZH, EN, STAMP, PICK, GT] + IMPORT_PATHS + GEN_NEW)
    concurrent = [p for p in changed if p in CONCURRENT]
    extra = [p for p in changed if p not in expected and p not in CONCURRENT and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V10.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production files, generated outputs, imports, the GameTest, the records)", extra[:10])
    ck("V10.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V10.expected-all-changed", not never, "every expected production, resource, generated and GameTest path differs from the start", never[:5])
    ck("V10.gen-new", sorted(gen_new) == sorted(GEN_NEW), "exactly the six new generated files appeared", sorted(set(gen_new) ^ set(GEN_NEW)))
    ck("V10.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + [GT, OWN] + IMPORT_PATHS) and all(p in inp.base_files for p in EDITED),
       "the new classes, the GameTest, the imports and the ownership record did not exist at the start; the edited files did")
    ck("V10.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED), "the RBMK base, proxy, fluid, config, fuel pool, anvil and older GameTest files are byte-equal to the start",
       [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    eol = [p for p in EDITED if p in inp.start and ("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n"))]
    ck("V10.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    rest = sorted(p for p in changed if (p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT) and p != MAP)
    ck("V10.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V10.concurrent-session", True, "changed planning files of other batches (listed, not part of this batch): " + ", ".join(Path(p).name for p in concurrent))
    ck("V10.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V11 / V12

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*(?:@SuppressWarnings\([^)]*\)\s*)?public static void (\w+)\(GameTestHelper helper\)")
GT_AREAS = ("outgasser_column", "outgasser_flux_rates", "outgasser_can_process", "outgasser_recipe_file", "outgasser_reactor_array", "outgasser_neutron_pass",
            "outgasser_ports", "outgasser_meltdown", "outgasser_recipes")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v11_gametest(ck, inp, st):
    ck("V11.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", other_gametests())
    ck("V11.present", st.has(GT), "RBMKOutgasserGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V11.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V11.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V11.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V11.marker", f'TAG = "{GT_MARK}"' in live and 'LOGGER.info("{} {} passed", TAG, name);' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = [n for n in tests if f'"{n}"' not in body(live, f"void {n}(GameTestHelper helper)")]
    ck("V11.report-name", not miss, "every test passes its own name to the passed helper", miss)
    ck("V11.areas", sorted(tests) == sorted(GT_AREAS), "the tests are " + ", ".join(GT_AREAS), sorted(set(tests) ^ set(GT_AREAS)))
    ck("V11.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKOutgasserGameTests references no client class")
    ck("V11.temp-dir", "Files.createTempDirectory(" in live and "hbmRecipes" not in code, "the recipe-file test writes only into a fresh temporary directory")
    return dict(tests=sorted(tests))


def original_calls(flux, ratio, mod):
    """The original receiveFlux loop (:73-77) in IEEE doubles, as the GameTest's Java loop."""
    efficiency = min(1 - ratio * 0.8, 1)
    progress, calls = 0.0, 0
    while calls < 1_000_000:
        progress += flux * efficiency * mod
        calls += 1
        if progress > 10000:
            return calls
    return -1


def v11_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    total = other_gametests() + gametest_total([live])
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V11.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({other_gametests()} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V11.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V11.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V11.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    facts = {}
    m = re.search(re.escape(GT_MARK) + r" rates: lithium ratio 0 -> (\d+) calls, ratio 1 \(efficiency ([\d.Ee-]+)\) -> (\d+) calls, mod ([\d.]+) -> (\d+) calls; gold (\d+) calls; coal (\d+) calls", text)
    if m:
        eff = min(1 - 1 * 0.8, 1)
        want = (original_calls(100, 0, 1.0), repr(eff), original_calls(100, 1, 1.0), original_calls(100, 0, float(m[4])))
        got = (int(m[1]), m[2], int(m[3]), int(m[5]))
        facts["rates"] = dict(logged=m[0], rederived=want)
        ck("V11.rates", got == want and want[0] == 101 and float(m[4]) == 2.0 and want[3] == 51 and int(m[6]) == 101 and int(m[7]) == 101,
           f"the logged call counts equal the original loop re-derived in Python: ratio 0 -> {want[0]}, ratio 1 (efficiency {want[1]}) -> {want[2]}, mod 2.0 -> {want[3]}", (got, want))
    else:
        ck("V11.rates", False, "the rates line is missing from the log")
    arr = re.search(re.escape(GT_MARK) + r" array: mod ([\d.]+), compared (\d+) ticks.*?\[(t\d+ flux=.*)\]", text)
    if arr:
        samples = re.findall(r"flux=([\d.Ee-]+) dMod=([\d.Ee-]+) dUn=([\d.Ee-]+)", arr[3])
        mod = float(arr[1])
        bad = [s for s in samples if abs(float(s[1]) - float(s[0]) * 1.0 * mod) > 1e-9 * float(s[1]) or abs(float(s[2]) - float(s[0]) * min(1 - 1 * 0.8, 1) * mod) > 1e-9 * float(s[2])]
        facts["array"] = dict(compared=int(arr[2]), samples=samples)
        ck("V11.array", samples and not bad and int(arr[2]) >= 5, f"the logged array deltas re-derive as flux * min(1 - ratio * 0.8, 1) * mod with ratio 0 (moderated) and 1 (unmoderated), {arr[2]} ticks compared", bad)
    else:
        ck("V11.array", False, "the array line is missing from the log")
    ps = re.search(re.escape(GT_MARK) + r" pass, loaded channel: rear flux ([\d.]+), channel progress ([\d.Ee-]+)", text)
    want_p = 40 * min(1 - 0.6 * 0.8, 1) * 1.0
    ck("V11.pass", bool(ps) and float(ps[1]) == 0.0 and float(ps[2]) == want_p, f"the loaded channel took 40 * min(1 - 0.6 * 0.8, 1) = {want_p} and nothing passed on", ps and ps[0])
    md = re.search(re.escape(GT_MARK) + r" meltdown debris per column: (.*)", text)
    counts = [int(x) for x in re.findall(r"BLANK=(\d+)", md[1])] if md else []
    ck("V11.meltdown", len(counts) == 3 and all(c in (4, 5) for c in counts), "each melted column spawned 4 + nextInt(2) BLANK debris", md and md[1])
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()), **facts)


def v12_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    gen = GEN_NEW + [EN, PICK]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        ck("V12.classes", not missing, "the JAR has the 9 new production classes and RBMKOutgasserGameTests", missing)
        bad = [p for p in IMPORT_PATHS if p[len("src/main/resources/"):] not in names or jar.read(p[len("src/main/resources/"):]) != st.files.get(p)]
        ck("V12.resources", not bad, "the seven imported textures in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V12.generated", not gbad, "the generated recipe, loot, model, blockstate, advancement files, en_us.json and the pickaxe tag in the JAR are byte-equal to the tree", gbad[:5])
        ck("V12.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None, v1=True):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    if v1:
        guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_block_entity, inp, st)
    guarded(ck, "V3", v3_handler, inp, st)
    guarded(ck, "V4", v4_recipes, inp, st, facts)
    guarded(ck, "V5", v5_sync_jei, inp, st)
    guarded(ck, "V6", v6_menu_screen, inp, st)
    guarded(ck, "V7", v7_registration, inp, st)
    guarded(ck, "V8", v8_lang, inp, st)
    guarded(ck, "V9", v9_resources, inp, st)
    guarded(ck, "V10", v10_scope, inp, st)
    r11 = guarded(ck, "V11", v11_gametest, inp, st)
    if facts is not None:
        facts["V11"] = r11
    return ck


def T(path, fn):
    """Apply fn to the LF-normalised text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


def Bx(path, fn):
    return lambda st: st.set_bytes(path, fn(st.files[path]))


def D(path):
    return lambda st: st.delete(path)


def flip_byte(data):
    out = bytearray(data)
    out[len(out) // 2] ^= 0x01
    return bytes(out)


def gen_edit(path, edit):
    def apply(st):
        data = json.loads(st.text(path))
        edit(data)
        st.set_text(path, json.dumps(data, indent=2, ensure_ascii=False))
    return apply


def OE(name, fn):
    """Edit the original's source text in memory (never on disk): V1 and the derived checks must notice."""
    def apply(st):
        st.orig_edits[name] = fn
    return apply


def drop_line(text, needle):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    del lines[hits[0]]
    return "\n".join(lines)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    return [
        ("efficiency_08_to_07", "V2.", t(OBE, "1 - stream.fluxRatio * 0.8", "1 - stream.fluxRatio * 0.7")),
        ("strict_gt_to_ge", "V2.", t(OBE, "if(progress > DURATION)", "if(progress >= DURATION)")),
        ("duration_1000", "V2.", t(OBE, "DURATION = 10000;", "DURATION = 1000;")),
        ("tank_capacity_32000", "V2.", t(OBE, "new FluidTank(Fluids.TRITIUM, 64000)", "new FluidTank(Fluids.TRITIUM, 32000)")),
        ("mod_dropped", "V2.", t(OBE, " * efficiency * RBMKDials.getOutgasserMod();", " * efficiency;")),
        ("settanktype_after_capacity", "V2.", T(OBE, lambda x: rep1(x, "            gas.setTankType(fluid.type);\n            if(gas.getFill() + fluid.fill > gas.getMaxFill()) return false;",
                                                                 "            if(gas.getFill() + fluid.fill > gas.getMaxFill()) return false;\n            gas.setTankType(fluid.type);"))),
        ("fusion_only_ignored", "V2.", T(OBE, lambda x: drop_line(x, "if(output.fusionOnly) return false;"))),
        ("solid_count_lt", "V2.", t(OBE, "slot.getCount() + out.getCount() <= slot.getMaxStackSize()", "slot.getCount() + out.getCount() < slot.getMaxStackSize()")),
        ("on_melt_4_to_3", "V2.", t(OBE, "int count = 4 + this.level.random.nextInt(2);", "int count = 3 + this.level.random.nextInt(2);")),
        ("progress_reset_removed", "V2.", T(OBE, lambda x: drop_line(x, "if(!canProcess()) this.progress = 0;"))),
        ("ports_subscribe", "V2.", t(OBE, "this.tryProvide(gas, world, con);", "this.tryProvide(gas, world, con);\n                this.trySubscribe(gas.getTankType(), world, con);")),
        ("console_type_int", "V2.", t(OBE, 'data.putShort("type", (short)this.gas.getTankType().getID());', 'data.putInt("type", this.gas.getTankType().getID());')),
        ("nbt_key_renamed", "V2.", t(OBE, 'tag.putDouble("progress", this.progress);', 'tag.putDouble("prog", this.progress);')),
        ("extract_slot_0", "V2.", t(OBE, "return index == 1;", "return index == 0;")),
        ("extra_without_fluid", "V2.", t(OBLK, "case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory().fluid();", "case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory();")),
        ("handler_return_removed", "V3.", T(HANDLER, lambda x: rep1(x, "                        if(outgasser.canProcess()) {\n                            column.receiveFlux(this);\n                            return;",
                                                                    "                        if(outgasser.canProcess()) {\n                            column.receiveFlux(this);"))),
        ("handler_gate_removed", "V3.", T(HANDLER, lambda x: rep1(x, "                        if(outgasser.canProcess()) {\n                            column.receiveFlux(this);\n                            return;\n                        }",
                                                                  "                        column.receiveFlux(this);\n                        return;"))),
        ("handler_rod_branch_touched", "V3.", t(HANDLER, "                        if(rod.hasRod) {", "                        if(rod.hasRod || rod.heat > 0) {")),
        ("default_row_dropped", "V4.", T(OREC, lambda x: drop_line(x, "gas(NtmItems.POWDER_LITHIUM_TINY.get(), Fluids.TRITIUM, 100);"))),
        ("default_amount_10000_to_1000", "V4.", t(OREC, "gas(NtmBlocks.BLOCK_LITHIUM, Fluids.TRITIUM, 10_000);", "gas(NtmBlocks.BLOCK_LITHIUM, Fluids.TRITIUM, 1_000);")),
        ("default_row_fusion_only", "V4.", t(OREC, "add(new OutgasserRecipe(new ComparableStack(input.asItem(), 1, 0), new ItemStack(output), null, false));",
                                             "add(new OutgasserRecipe(new ComparableStack(input.asItem(), 1, 0), new ItemStack(output), null, true));")),
        ("default_coal_block_count_8", "V4.", t(OREC, "both(Items.COAL_BLOCK, NtmItems.OIL_TAR_COAL.get(), 9, Fluids.SYNGAS, 500);", "both(Items.COAL_BLOCK, NtmItems.OIL_TAR_COAL.get(), 8, Fluids.SYNGAS, 500);")),
        ("fusion_only_not_written", "V4.", t(OREC, '        writer.name("fusionOnly").value(row.fusionOnly);', '        if(row.fusionOnly) writer.name("fusionOnly").value(row.fusionOnly);')),
        ("lenient_to_strict", "V4.", t(OREC, "readSnapshot(text.toString(), true);", "readSnapshot(text.toString(), false);")),
        ("file_name_changed", "V4.", t(OREC, 'return "hbmIrradiation.json";', 'return "hbmOutgasser.json";')),
        ("max_gas_128000", "V4.", t(OREC, "MAX_GAS = 64_000;", "MAX_GAS = 128_000;")),
        ("handler_registered_twice", "V4.", T(SER, lambda x: rep1(x, "recipeHandlers.add(new OutgasserRecipes());", "recipeHandlers.add(new OutgasserRecipes());\n        recipeHandlers.add(new OutgasserRecipes());"))),
        ("packet_registered_twice", "V5.", T(NET, lambda x: rep1(x, "registrar.playToClient(OutgasserRecipesPacket.TYPE", "registrar.playToClient(OutgasserRecipesPacket.TYPE, OutgasserRecipesPacket.STREAM_CODEC, OutgasserRecipesPacket::handleCommon);\n        registrar.playToClient(OutgasserRecipesPacket.TYPE"))),
        ("jei_fusion_rows_shown", "V5.", t(OJEI, "if(!recipe.fusionOnly) rows.add(recipe);", "rows.add(recipe);")),
        ("client_leak", "V5.", t(OBE, "import net.minecraft.core.BlockPos;", "import net.minecraft.core.BlockPos;\nimport net.minecraft.client.Minecraft;")),
        ("client_sync_no_logout_clear", "V5.", t(OCSYNC, "        snapshot = null;\n        if(refresh", "        if(refresh")),
        ("slot0_x_49", "V6.", t(OMENU, "new Slot(be, 0, 48, 45)", "new Slot(be, 0, 49, 45)")),
        ("output_slot_y_70", "V6.", t(OMENU, "be, 1, 112, 69)", "be, 1, 112, 70)")),
        ("progress_width_13_to_14", "V6.", t(OSCREEN, "be.progress * 13 / RBMKOutgasserBlockEntity.DURATION", "be.progress * 14 / RBMKOutgasserBlockEntity.DURATION")),
        ("gas_height_42_to_48", "V6.", t(OSCREEN, "be.gas.getFill() * 42 / be.gas.getMaxFill()", "be.gas.getFill() * 48 / be.gas.getMaxFill()")),
        ("tooltip_rect", "V6.", t(OSCREEN, "this.topPos + 21, 16, 48", "this.topPos + 21, 16, 52")),
        ("recipe_pattern", "V7.", gen_edit(G_REC, lambda d: d.__setitem__("pattern", ["GHG", "GTG", "GRG"]))),
        ("recipe_key_hopper_chest", "V7.", gen_edit(G_REC, lambda d: d["key"].__setitem__("H", {"item": "minecraft:chest"}))),
        ("registered_twice_creative", "V7.", T(CTAB, lambda x: rep1(x, "output.accept(NtmBlocks.RBMK_OUTGASSER);", "output.accept(NtmBlocks.RBMK_OUTGASSER);\n                        output.accept(NtmBlocks.RBMK_OUTGASSER);"))),
        ("lid_ber_removed", "V7.", T(CP, lambda x: drop_line(x, "NtmBlockEntityTypes.RBMK_OUTGASSER.get(), new RenderRBMKLid"))),
        ("anvil_touched", "V7.|V10.", T(ANVIL, lambda x: x + "\n")),
        ("en_value_changed", "V8.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("container.rbmkOutgasser", "RBMK Outgasser")))),
        ("zh_value_changed", "V8.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("block.hbmsntm.rbmk_outgasser", "RBMK辐照通道")))),
        ("zh_dodd_missing", "V8.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("tile.rbmk.dodd.gas_max")))),
        ("zh_other_key_changed", "V8.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("block.hbmsntm.rbmk_blank", "X")))),
        ("map_source_zh_changed", "V8.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["container.rbmkOutgasser"].__setitem__("source_zh", "X")))),
        ("resource_byte_flip", "V9.", Bx(IMPORT_PATHS[1], flip_byte)),
        ("gui_byte_flip", "V9.", Bx(IMPORT_PATHS[6], flip_byte)),
        ("unrelated_migration_file", "V10.", lambda st: st.set_bytes("migration/stray.json", b"{}")),
        ("unrelated_src_file", "V10.", lambda st: st.set_bytes(J + "items/Stray.java", b"class Stray {}")),
        ("base_file_touched", "V2.|V10.", T(BE_DIR + "RBMKBaseBlockEntity.java", lambda x: x + "\n")),
        ("orig_efficiency_line", "V1.|V2.", OE("te", lambda x: rep1(x, "1 - stream.fluxRatio * 0.8", "1 - stream.fluxRatio * 0.7"))),
        ("orig_row_amount", "V1.|V4.", OE("rec", lambda x: rep1(x, "new FluidStack(Fluids.TRITIUM, 10_000)", "new FluidStack(Fluids.TRITIUM, 1_000)"))),
        ("orig_handler_line_moved", "V1.", OE("nh", lambda x: rep1(x, "\t\t\t\t\t} else if(type == RBMKType.OUTGASSER) {", "\n\t\t\t\t\t} else if(type == RBMKType.OUTGASSER) {"))),
        ("gt_marker_changed", "V11.", t(GT, 'TAG = "[hbm-rbmk-outgasser]"', 'TAG = "[hbm-rbmk]"'), GT),
        ("gt_batch_shared", "V11.", t(GT, 'batch = "rbmk_outgasser_pass"', 'batch = "rbmk_outgasser_ports"'), GT),
        ("gt_deleted", "V11.|V10.", D(GT), GT),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for entry in mutations():
        label, prefixes, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required is not None and not st.has(required):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        mutated = st.copy()
        mutated.orig_edits = {}
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree and not mutated.orig_edits:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error="mutation changed nothing")
            continue
        inp2 = inp
        if mutated.orig_edits:
            inp2 = copy.copy(inp)
            inp2.o, inp2.ol = dict(inp.o), dict(inp.ol)
            try:
                for name, fn in mutated.orig_edits.items():
                    inp2.o[name] = fn(inp.o[name])
                    inp2.ol[name] = inp2.o[name].split("\n")
            except (AssertionError, KeyError, ValueError) as error:
                results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
                continue
        ck = static_suite(inp2, mutated, v1=True)
        failed = ck.failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        wanted = prefixes.split("|")
        results[label] = dict(expected_section=prefixes, failed=real[:8], crashes=crashes, detected=any(f.startswith(p) for f in real for p in wanted))
    return results


def sections(ck):
    out = {}
    for item in ck.items:
        out.setdefault(item["id"].split(".")[0], []).append(item)
    out.setdefault("V12", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V12" and not items:
            result[sec] = dict(status="not run", checks=0, passed=0, failed=[])
            continue
        failed = [i["id"] for i in items if i["status"] == "FAIL"]
        result[sec] = dict(status="PASS" if not failed else "FAIL", checks=len(items), passed=len(items) - len(failed), failed=failed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    st.orig_edits = {}
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V11", v11_log, inp, st, args.gametest_log)
    else:
        ck("V11.log-not-run", True, "no --gametest-log given: the GameTest log checks were not run")
    if args.jar:
        extra["jar"] = guarded(ck, "V12", v12_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V13"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    production = NEW_CLASSES + EDITED + [ZH, EN, STAMP, MAP, OWN, GT]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(applied) - len(undetected), mutations_applied=len(applied), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.tree.get(p) for p in dict.fromkeys(production)},
        tools_status=inp.tools_status,
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    report["pass"] = report.pop("pass_")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] == "FAIL":
            print(f"FAIL {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        if value.get("detected") is None:
            print(f"SKIPPED  mutation {label}: {value.get('skipped')}")
            continue
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label} (expect {value['expected_section']}): {value['failed'][:4]}"
              + (f" crashes={value['crashes']}" if value["crashes"] else "") + (f" {value['error']}" if value.get("error") else ""))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
