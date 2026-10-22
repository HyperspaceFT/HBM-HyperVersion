"""Verify the Goal25A batch statically: the RBMK storage column (rbmk_storage: RBMKStorageBlock, RBMKStorageBlockEntity, RBMKStorageMenu,
RBMKStorageScreen), the spent fuel pool drum taking RBMK rods (MachineWasteDrumBlockEntity), the cold rod disassembly special recipe
(NtmRecipeSerializers, RBMKRodDisassemblyRecipe), the JEI rows (FuelPoolRecipeHandler, RBMKRodDisassemblyRecipeHandler, NtmJeiPlugin), the
close-out items (b) (d) (e) (f), the language entries, the imported resources and the GameTest source; with --gametest-log the GameTest log
and the (h) small-pile trajectory against tools/migration/goal25a_pile_model.py.

Read-only for both worktrees. Writes only build/migration/goal25a/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal25a/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (storage tile entity, block, container, GUI, waste drum, fuel pool rows, NEI handlers, crafting handler, recipes,
      chemical plant row, config, control packet, language) parsed at the cited lines; a moved line fails loudly.
- V2  Storage block entity, block, menu and screen against V1; the 24A-24E RBMK base files unchanged.
- V3  Waste drum against V1; FuelPoolRecipes, its JSON contract and MachineWasteDrumMenu unchanged.
- V4  Disassembly: serializer registry, the recipe against V1, the generated recipe JSON files, AnvilRecipes unchanged.
- V5  JEI rows and categories; client isolation.
- V6  Close-out (b) (d) (e) (f) and the registrations.
- V7  Language: the new English keys, zh_cn.json and zh_cn-map.json (add_zh.py's lists), nothing else changed in the three files.
- V8  Resources: the seven imports byte-equal to the original and recorded in migration/goal25a-resource-ownership.json.
- V9  Scope: every src/ and migration/ path changed since the start is in the expected set (concurrent-session records and tools/ listed).
- V10 GameTest source. V11 (--gametest-log) the GameTest log and the pile comparison. V12 (--jar) the packaged JAR; "not run" without the flag.
- V13 In-memory mutations of the NEO inputs and of the original text (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal25a_rbmk_recycling.py [--gametest-log PATH] [--jar PATH]
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
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal25a"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "783b6d137936750a8a5ef822e1b29fd1209593f7"

J = "src/main/java/com/hbm/"
BE = J + "blockentity/machine/rbmk/"
BLK = J + "blocks/machine/rbmk/"
SBE = BE + "RBMKStorageBlockEntity.java"
SBLK = BLK + "RBMKStorageBlock.java"
SMENU = J + "inventory/menus/RBMKStorageMenu.java"
SSCREEN = J + "inventory/screens/RBMKStorageScreen.java"
SER = J + "registry/NtmRecipeSerializers.java"
REC = J + "inventory/recipes/crafting/RBMKRodDisassemblyRecipe.java"
JDIS = J + "handler/jei/RBMKRodDisassemblyRecipeHandler.java"
NEW_CLASSES = [SBLK, SBE, SMENU, SSCREEN, SER, REC, JDIS]
DRUM = J + "blockentity/machine/MachineWasteDrumBlockEntity.java"
JFP = J + "handler/jei/FuelPoolRecipeHandler.java"
JEI = J + "handler/jei/NtmJeiPlugin.java"
NTM = J + "main/NuclearTechMod.java"
NMC = J + "main/NuclearTechModClient.java"
CC = J + "config/CommonConfig.java"
CHEM = J + "inventory/recipes/ChemicalPlantRecipes.java"
CTC = J + "network/toserver/CompoundTagControl.java"
CT_TYPE = BE + "RBMKColumnType.java"
NB = J + "blocks/NtmBlocks.java"
BET = J + "blockentity/NtmBlockEntityTypes.java"
MT = J + "inventory/NtmMenuTypes.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
RP = J + "datagen/NtmRecipeProvider.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
LOOTP = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
CP = J + "main/ClientProxy.java"
EDITED = [DRUM, JFP, JEI, NTM, NMC, CC, CHEM, CTC, CT_TYPE, NB, BET, MT, CTAB, RP, BSP, LOOTP, TAGP, LP, CP]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal25a-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
RECIPES = GEN + "data/hbmsntm/recipe/"
G_DIS = RECIPES + "rbmk_rod_disassembly.json"
G_STO = RECIPES + "rbmk_storage.json"
GEN_NEW = [GEN + "assets/hbmsntm/blockstates/rbmk_storage.json", GEN + "assets/hbmsntm/models/block/rbmk_storage.json", GEN + "assets/hbmsntm/models/item/rbmk_storage.json",
           GEN + "data/hbmsntm/advancement/recipes/misc/rbmk_storage.json", GEN + "data/hbmsntm/loot_table/blocks/rbmk_storage.json", G_DIS, G_STO]
GEN_CHANGED = [STAMP, EN, PICK]
RES = "src/main/resources/assets/hbmsntm/"
GT = J + "gametest/RBMKRecyclingGameTests.java"
GT_DIR = J + "gametest/"
PILE_MODEL = ROOT / "tools/migration/goal25a_pile_model.py"

# files the batch must only read, never change (byte-equal to the start; hashes from baseline.json)
UNTOUCHED = [BE + n for n in ("RBMKSlottedBaseBlockEntity.java", "RBMKBaseBlockEntity.java", "RBMKRodBlockEntity.java", "RBMKControlManualBlockEntity.java", "RBMKDials.java",
                              "IRBMKLoadable.java", "RBMKConsoleBlockEntity.java")] + [
    BLK + "RBMKBaseBlock.java", BLK + "RBMKRodBlock.java", BLK + "RBMKPipedBaseBlock.java", J + "blocks/DummyableBlock.java", J + "blockentity/ProxyComboBlockEntity.java",
    J + "inventory/recipes/FuelPoolRecipes.java", J + "inventory/menus/MachineWasteDrumMenu.java", J + "inventory/recipes/anvil/AnvilRecipes.java", J + "items/machine/RBMKRodItem.java",
    J + "items/machine/RBMKPelletItem.java", J + "handler/FuelPoolRecipeClientSync.java", J + "interfaces/IControlReceiver.java", J + "datagen/NtmItemModelProvider.java",
    J + "gametest/WasteDrumGameTests.java", J + "gametest/SmokeTestSupport.java"]
CONCURRENT = {"migration/GOAL25.md", "migration/GOAL25B.md", "migration/GOAL25C.md", "migration/GOAL25D.md", "migration/GOAL25-THREAD-PROMPTS.md"}

O = "src/main/java/com/hbm/"
O_STE = O + "tileentity/machine/rbmk/TileEntityRBMKStorage.java"
O_SBLK = O + "blocks/machine/rbmk/RBMKStorage.java"
O_ROD = O + "blocks/machine/rbmk/RBMKRod.java"
O_CON = O + "inventory/container/ContainerRBMKStorage.java"
O_GUI = O + "inventory/gui/GUIRBMKStorage.java"
O_DRUM = O + "tileentity/machine/TileEntityWasteDrum.java"
O_FPR = O + "inventory/recipes/FuelPoolRecipes.java"
O_NDIS = O + "handler/nei/RBMKRodDisassemblyHandler.java"
O_NFP = O + "handler/nei/FuelPoolHandler.java"
O_CRAFT = O + "crafting/handlers/RBMKFuelCraftingHandler.java"
O_CM = O + "main/CraftingManager.java"
O_ANV = O + "inventory/recipes/anvil/AnvilRecipes.java"
O_CHEM = O + "inventory/recipes/ChemicalPlantRecipes.java"
O_GC = O + "config/GeneralConfig.java"
O_NBT = O + "packet/toserver/NBTControlPacket.java"
O_DUMMY = O + "blocks/BlockDummyable.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"
O_FILES = dict(ste=O_STE, sblk=O_SBLK, rod=O_ROD, con=O_CON, gui=O_GUI, drum=O_DRUM, fpr=O_FPR, ndis=O_NDIS, nfp=O_NFP, craft=O_CRAFT, cm=O_CM, anv=O_ANV, chem=O_CHEM, gc=O_GC,
               nbt=O_NBT, dummy=O_DUMMY)

# V1: every cited original line, {file key: {line: needle}}; a moved or changed line fails V1
ANCHORS = {
    "ste": {18: "super(12);", 23: '"container.rbmkStorage"', 29: "worldObj.getTotalWorldTime() % 10 == 0", 31: "for(int i = 0; i < slots.length - 1; i++)",
            33: "if(slots[i] == null && slots[i + 1] != null)", 34: "slots[i] = slots[i + 1];", 35: "slots[i + 1] = null;", 40: "super.updateEntity();",
            50: "return ColumnType.STORAGE;", 55: "return itemStack.getItem() instanceof ItemRBMKRod;", 60: "return true;",
            65: "return new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};", 70: "return slots[11] == null;", 75: "slots[11] = toLoad.copy();",
            80: "return slots[0] != null;", 85: "return slots[0];", 90: "slots[0] = null;"},
    "sblk": {16: "if(meta >= this.offset)", 17: "return new TileEntityRBMKStorage();", 19: "return new TileEntityProxyCombo(true, false, false);",
             29: "BossSpawnHandler.markFBI(player);", 30: "return openInv(world, x, y, z, player);"},
    "rod": {38: "if(meta >= this.offset) return new TileEntityRBMKRod();", 39: "if(hasExtra(meta)) return new TileEntityProxyCombo().inventory();"},
    "con": {18: "for(int i = 0; i < 3; i++) {", 19: "for(int j = 0; j < 4; j++) {", 20: "this.addSlotToContainer(new Slot(tedf, i + j * 3, 32 + 32 * j, 29 + 16 * i));",
            26: "8 + j * 18, 84 + i * 18 + 20", 31: "8 + i * 18, 142 + 20", 44: "if(par2 < 12) {", 45: "this.mergeItemStack(var5, rbmk.getSizeInventory(), this.inventorySlots.size(), true)",
            48: "} else if(!this.mergeItemStack(var5, 0, 12, false)) {"},
    "gui": {16: '":textures/gui/reactors/gui_rbmk_storage.png"', 23: "this.xSize = 176;", 24: "this.ySize = 186;", 31: "6, 4210752", 32: "this.ySize - 96 + 2"},
    "drum": {104: "|| itemStack.getItem() instanceof ItemRBMKRod;", 184: "if(itemStack.getItem() instanceof ItemRBMKRod) {",
             185: "return ItemRBMKRod.getCoreHeat(itemStack) < 50 && ItemRBMKRod.getHullHeat(itemStack) < 50;", 187: "return !FuelPoolRecipes.recipes.containsKey(new ComparableStack(getStackInSlot(i)));",
             204: "if(water > 0) {", 206: "int r = 60 * 60 * 20 / water;", 212: "if(slots[i].getItem() instanceof ItemRBMKRod) {", 215: "rod.updateHeat(worldObj, slots[i], 0.025D);",
             216: "rod.provideHeat(worldObj, slots[i], 20D, 0.025D);", 218: "} else if(worldObj.rand.nextInt(r) == 0) {"},
    "fpr": {46: "for(ItemRBMKRod rod : ItemRBMKRod.craftableRods) {", 48: "ItemRBMKRod.setYield(result, 0.2 * rod.yield);",
            49: "recipes.put(new RBMKRodDisassemblyHandler.ComparableStackHeat(rod, true), result);"},
    "ndis": {15: 'super("RBMK Rod Disassembly", Blocks.crafting_table, getRecipes());', 26: "for(ItemRBMKRod rod : ItemRBMKRod.craftableRods) {",
             27: "for(int enrichment = 0; enrichment <= 4; enrichment++) {", 28: "new ItemStack(rod.pellet, 8, enrichment);", 31: "if(rod.pellet.isXenonEnabled()) {",
             32: "new ItemStack(rod.pellet, 8, enrichment + 5);", 45: "if(ItemRBMKRod.getCoreHeat(ingredient) > 50 || ItemRBMKRod.getHullHeat(ingredient) > 50) return;",
             73: "ItemRBMKRod.setYield(stack, Math.min(1 - ((double) enrichment) / 5, 0.99) * rod.yield);", 75: "ItemRBMKRod.setYield(stack, 0.2 * rod.yield);",
             77: "if(hasPoison) ItemRBMKRod.setPoison(stack, 50);", 79: "ItemRBMKRod.setCoreHeat(stack, 100);", 80: "ItemRBMKRod.setHullHeat(stack, 50);"},
    "nfp": {23: "if(ItemRBMKRod.getCoreHeat(ingredient) < 50 && ItemRBMKRod.getHullHeat(ingredient) < 50) return;",
            32: "if(ItemRBMKRod.getCoreHeat(ingredient) >= 50 || ItemRBMKRod.getHullHeat(ingredient) >= 50) return;"},
    "craft": {19: "if(!hasExactlyOneStack(inventory))", 24: "return stack.getItem() instanceof ItemRBMKRod && ((ItemRBMKRod)stack.getItem()).pellet != null &&",
              25: "ItemRBMKRod.getHullHeat(stack) < 50 && ItemRBMKRod.getCoreHeat(stack) < 50;", 45: "if(rod.pellet == null)", 48: "if(ItemRBMKRod.getEnrichment(stack) > 0.99D)",
              51: "if(ItemRBMKRod.getHullHeat(stack) < 50 && ItemRBMKRod.getCoreHeat(stack) < 50) {", 52: "ItemStack result = new ItemStack(rod.pellet, 8);",
              53: "int enrichment = 4 - MathHelper.clamp_int((int)Math.ceil(ItemRBMKRod.getEnrichment(stack) * 5 - 1), 0, 4);",
              54: "int meta = enrichment + (ItemRBMKRod.getPoisonLevel(stack) >= 0.5D ? 5 : 0);", 55: "result.setItemDamage(meta);"},
    "cm": {74: "GameRegistry.addRecipe(new RBMKFuelCraftingHandler());", 80: 'RecipeSorter.register("hbm:rbmk", RBMKFuelCraftingHandler.class',
           770: "addRecipeAuto(new ItemStack(ModBlocks.rbmk_storage, 1), new Object[] { \"C\", \"R\", \"C\", 'C', ModBlocks.crate_steel, 'R', ModBlocks.rbmk_blank });"},
    "anv": {922: "new ComparableStack(ModBlocks.rbmk_storage)", 923: "new AnvilOutput(new ItemStack(ModBlocks.rbmk_blank, 1))", 924: "new AnvilOutput(new ItemStack(ModBlocks.crate_steel, 2))",
            925: "}).setTier(4));"},
    "chem": {192: 'new GenericRecipe("chem.batteryquantum").setup(100, 100_000)', 193: "new OreDictStack(BSCCO.wireDense(), 24),", 194: "new ComparableStack(ModItems.pellet_charged, 32),",
             195: "new ComparableStack(ModItems.ingot_cft, 16))", 196: ".inputFluids(new FluidStack(Fluids.PERFLUOROMETHYL_COLD, 8_000))",
             197: "EnumBatteryPack.BATTERY_QUANTUM.ordinal()", 198: ".outputFluids(new FluidStack(Fluids.PERFLUOROMETHYL, 8_000)));"},
    "gc": {131: '"1.44_enableMachineGravity", false'},
    "nbt": {75: "TileEntity te = p.worldObj.getTileEntity(m.x, m.y, m.z);", 82: "if(te instanceof IControlReceiver) {", 86: "if(tile.hasPermission(p)) {",
            88: "tile.receiveControl(p, nbt);"},
    "dummy": {47: "public abstract class BlockDummyable extends BlockContainer", 314: "if(te instanceof ISidedInventory) {", 334: "itemstack.stackSize -= j1;"},
}

# V7: (NEO key, original key, en_US.lang line, zh_CN.lang line) for the upstream entries of add_zh.py; local and from-deferred entries
UP = [("hbmsntm.keys", "hbm.key", 1427, 1153), ("hbmsntm.keys.calc", "hbm.key.calculator", 1430, 1154), ("hbmsntm.keys.toggleBack", "hbm.key.toggleBack", 1443, 1166),
      ("hbmsntm.keys.toggleMagnet", "hbm.key.toggleMagnet", 1445, 5884), ("hbmsntm.keys.toggleHUD", "hbm.key.toggleHUD", 1444, 1167), ("hbmsntm.keys.ability", "hbm.key.ability", 1428, 5882),
      ("hbmsntm.keys.abilityAlt", "hbm.key.abilityAlt", 1429, 5883), ("hbmsntm.keys.reload", "hbm.key.reload", 1447, 1169), ("hbmsntm.keys.gunPrimary", "hbm.key.gunPrimary", 1439, 1163),
      ("hbmsntm.keys.gunSecondary", "hbm.key.gunSecondary", 1440, 1164), ("hbmsntm.keys.gunTertiary", "hbm.key.gunTertitary", 1441, 1165),
      ("effect.hbmsntm.mutation", "potion.hbm_mutation", 4954, 4262)]
STORAGE_ZH = "RBMK反应堆燃料存储柱"
LOCAL = {"block.hbmsntm.rbmk_storage": ("tile.rbmk_storage.name", 6253, 5362, "RBMK Storage Column", STORAGE_ZH),
         "container.rbmkStorage": ("container.rbmkStorage", 802, 640, "RBMK Storage Column", STORAGE_ZH),
         "jei.hbmsntm.rbmk_rod_disassembly": (None, None, None, "RBMK Rod Disassembly", "RBMK燃料棒拆解")}
FROM_DEFERRED = {"item.hbmsntm.shell_copper": ("Copper Shell", "铜壳")}
EN_NEW = [u[0] for u in UP] + list(LOCAL)
ZH_NEW = EN_NEW + list(FROM_DEFERRED)

IMPORTS = [("textures/blocks/rbmk/rbmk_storage_" + n + ".png", "textures/block/rbmk/rbmk_storage_" + n + ".png") for n in ("side", "top", "cover_top", "cover_side", "glass_top", "glass_side")] + [
    ("textures/gui/reactors/gui_rbmk_storage.png", "textures/gui/reactors/gui_rbmk_storage.png")]
IMPORT_PATHS = [RES + n for _, n in IMPORTS]

GT_MARK = "[hbm-rbmk-recycling]"
START_GAMETESTS = 204
CRAFTABLE_RODS = 31
HASH_SKIP = ("__pycache__",)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crlf(text):
    return text.replace("\n", "\r\n")


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


# ---------------------------------------------------------------- text helpers (as verify_goal24e_rbmk_console.py)

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


@functools.lru_cache(maxsize=64)
def _ops(start, live):
    s, l = lf(start).split("\n"), lf(live).split("\n")
    return [(tag, i1, i2, s[i1:i2], l[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s, l, autojunk=False).get_opcodes() if tag != "equal"]


def diff_summary(start, live):
    """(deleted start lines, inserted live lines), both stripped and without blank lines."""
    ops = _ops(start, live)
    return [x.strip() for _, _, _, s, _ in ops for x in s if x.strip()], [x.strip() for _, _, _, _, l in ops for x in l if x.strip()]


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


def _line_hit(lines, needle):
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    return hits[0]


def drop_line(text, needle):
    lines = text.split("\n")
    del lines[_line_hit(lines, needle)]
    return "\n".join(lines)


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


def eq(ck, cid, label, expected, got):
    ok = bool(expected) and expected == got
    return ck(cid, ok, label, "" if ok else first_diff(expected, got))


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
    inp.o_en_lines = lf(read_text(ORIGINAL / O_LANG / "en_US.lang")).split("\n")
    inp.o_zh_lines = lf(read_text(ORIGINAL / O_LANG / "zh_CN.lang")).split("\n")
    tree = hash_tree()
    files = {}
    load = set(NEW_CLASSES + EDITED + UNTOUCHED + [ZH, MAP, OWN, EN, STAMP, PICK, GT, J + "items/NtmItems.java"] + GEN_NEW + IMPORT_PATHS)
    load.update(p for p in tree if p.startswith(RECIPES))
    load.update(p for p in tree if p.startswith(J) and p.endswith(".java") and "/handler/jei/" not in p and "/screens/" not in p and "/render/" not in p and "/gametest/" not in p
                and (p.startswith(J + "blocks/machine/rbmk/") or p.startswith(BE) or p in (SMENU, SER, REC)))
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
    ck("V0.baseline-copies-match", not bad and len(inp.baseline["copied_scope"]) == 34 and all(p in inp.start or p not in inp.base_files for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, 34 in copied_scope) hashes to its baseline.json entry", bad)
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
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", bool(e) and bool(z) and e[0][1] == en_line and z[0][1] == zh_line, f"{okey} is at en_US.lang:{en_line} and zh_CN.lang:{zh_line}",
           (e and e[0][1], z and z[0][1]))
    for neo, (okey, en_line, zh_line, _, _) in LOCAL.items():
        if okey:
            e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
            ck(f"V1.lang-{okey}", bool(e) and bool(z) and e[0][1] == en_line and z[0][1] == zh_line, f"{okey} is at en_US.lang:{en_line} and zh_CN.lang:{zh_line}", (e, z))
    ck("V1.lang-shell", inp.o_en_lines[4510].startswith("item.shellntm.name=") and inp.o_en_lines[1645].startswith("hbmmat.copper="),
       "the composed shell_copper source (item.shellntm.name en_US.lang:4511, hbmmat.copper :1646) is at its lines")


# ---------------------------------------------------------------- V2 storage column against V1

def ocode_line(inp, key, line):
    return sq(blank_comments(inp.ol[key][line - 1]))


def v2_storage(ck, inp, st):
    be = lf(st.text(SBE))
    code = code_of(be)
    # updateEntity: the original loop (:29-37) token for token with slots[i] == null -> slots.get(i).isEmpty()
    loop = rewrite(sq("".join(inp.ol["ste"][30:37])), [lit("slots.length", "this.slots.size()"), lit("slots[i]==null", "this.slots.get(i).isEmpty()"),
                                                      lit("slots[i+1]!=null", "!this.slots.get(i+1).isEmpty()"), lit("slots[i]=slots[i+1];", "this.slots.set(i,this.slots.get(i+1));"),
                                                      lit("slots[i+1]=null;", "this.slots.set(i+1,ItemStack.EMPTY);moved=true;")])
    upd = body(be, "public void updateEntity()")
    period = rewrite(ocode_line(inp, "ste", 29), [lit("if(!worldObj.isRemote&&worldObj.getTotalWorldTime()%10==0){", "if(this.level.getGameTime()%10==0){")])
    ck("V2.compaction-period", period in upd and upd.startswith("if(this.level==null||this.level.isClientSide)return;"),
       "updateEntity is server-only and compacts when the game time % 10 == 0 (original :29)", upd[:200])
    ck("V2.compaction-loop", loop in upd, "the compaction loop equals the original :31-37 (one forward pass for i < 11, empty slot i takes slot i + 1)", first_diff(loop, upd))
    ck("V2.compaction-before-base", ordered(upd, period, loop, "if(moved)this.setChanged();", "super.updateEntity();") and upd.endswith("super.updateEntity();"),
       "compaction runs before the base update (original :40), and the BE is marked changed only when a stack moved")
    contains_all(ck, "V2.slots-and-name", "12 slots (:18), container.rbmkStorage (:23)", code, "super(NtmBlockEntityTypes.RBMK_STORAGE.get(),pos,state,12);",
                 'return"container.rbmkStorage";', "privatestaticfinalint[]SLOTS=newint[]{0,1,2,3,4,5,6,7,8,9,10,11};")
    ck("V2.console-type", body(be, "public RBMKColumnType getConsoleType()") == "returnRBMKColumnType.STORAGE;", "getConsoleType is STORAGE (:50)")
    ck("V2.can-place", body(be, "public boolean canPlaceItem(int slot, ItemStack stack)") == "returnstack.getItem()instanceofRBMKRodItem;", "canPlaceItem accepts rods only (:55)")
    ck("V2.slots-for-face", body(be, "public int[] getSlotsForFace(Direction direction)") == "returnSLOTS;", "getSlotsForFace is every slot 0..11 (:65)")
    ck("V2.can-take", body(be, "public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction)") == "returntrue;", "canTakeItemThroughFace is always true (:60)")
    ck("V2.no-place-through-face-override", "canPlaceItemThroughFace" not in code, "canPlaceItemThroughFace is MachineBaseBlockEntity's default (it asks canPlaceItem)")
    can_load = body(be, "public boolean canLoad(ItemStack toLoad)")
    ck("V2.can-load", can_load == "returnthis.slots.get(11).isEmpty()&&toLoad.getItem()instanceofRBMKRodItem;", "canLoad is slot 11 empty (:70) and the NEO-only rod guard", can_load)
    o, _, _ = method_span(be, "public boolean canLoad(ItemStack toLoad)")
    ck("V2.can-load-commented", "NEO-only" in be[max(0, o - 400):o], "the NEO-only rod guard in canLoad is commented")
    ck("V2.load", body(be, "public void load(ItemStack toLoad)") == "this.slots.set(11,toLoad.copy());this.setChanged();", "load puts a copy into slot 11 (:75)")
    ck("V2.unload", body(be, "public boolean canUnload()") == "return!this.slots.get(0).isEmpty();" and body(be, "public ItemStack provideNext()") == "returnthis.slots.get(0);"
       and body(be, "public void unload()") == "this.slots.set(0,ItemStack.EMPTY);this.setChanged();", "canUnload / provideNext / unload work on slot 0 (:80-90)")
    ck("V2.no-new-nbt", "saveAdditional" not in code and "loadAdditional" not in code, "the storage adds no NBT keys (the slotted base's item list)")

    blk = lf(st.text(SBLK))
    bcode = code_of(blk)
    ck("V2.block-switch", "returnswitch(state.getValue(TYPE)){caseCORE->newRBMKStorageBlockEntity(pos,state);caseEXTRA,DUMMY->newProxyComboBlockEntity(pos,state).inventory();};" in bcode,
       "newBlockEntity: the core gets the storage BE, every other block (EXTRA and DUMMY) an inventory-only proxy (original RBMKStorage.java:16-19, no hasExtra test unlike RBMKRod :38-39)",
       re.search(r"returnswitch\(state.getValue\(TYPE\)\)\{.*?\};", bcode) and re.search(r"returnswitch\(state.getValue\(TYPE\)\)\{.*?\};", bcode)[0])
    ck("V2.block-no-fbi", "BossSpawnHandler" not in bcode and "markFBI" not in bcode, "BossSpawnHandler.markFBI (:29) is not ported")
    contains_all(ck, "V2.block-shape", "CODEC, core-only ticker, opens the menu without an item", bcode, "publicstaticfinalMapCodec<RBMKStorageBlock>CODEC=simpleCodec(RBMKStorageBlock::new);",
                 "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;", "returnthis.standardOpenBehavior(level,pos,player);")

    menu = lf(st.text(SMENU))
    mcode = code_of(menu)
    slot = rewrite(ocode_line(inp, "con", 20), [lit("this.addSlotToContainer(newSlot(tedf,", "this.addSlot(newSlot(be,"), lit("));", ")")])
    ck("V2.menu-slots", ordered(mcode, "for(inti=0;i<3;i++){for(intj=0;j<4;j++){", slot) and slot == "this.addSlot(newSlot(be,i+j*3,32+32*j,29+16*i)",
       "the 12 column slots are i + j * 3 at (32 + 32j, 29 + 16i), i in 0..2 outside j in 0..3 (original :18-22)", slot)
    ck("V2.menu-player", "this.playerInv(inventory,8,104,162);" in mcode, "player inventory at (8, 84 + 20) and hotbar at y 142 + 20 (original :24-31)")
    ck("V2.menu-rods-only", "publicbooleanmayPlace(ItemStackstack){returnstack.getItem()instanceofRBMKRodItem;}" in mcode, "the column slots take fuel rods only (NEO-only, as the fuel channel)")
    qm = body(menu, "public ItemStack quickMoveStack(Player player, int index)")
    contains_all(ck, "V2.menu-quick-move", "quickMoveStack: column slots to the player in reverse, the player into 0..12 (original :44-50)", qm,
                 "if(index<be.getContainerSize()){if(!this.moveItemStackTo(stack,be.getContainerSize(),this.slots.size(),true))returnItemStack.EMPTY;}elseif(!this.moveItemStackTo(stack,0,be.getContainerSize(),false)){returnItemStack.EMPTY;}")

    scr = code_of(st.text(SSCREEN))
    contains_all(ck, "V2.screen", "screen: gui_rbmk_storage.png (:16), 176 x 186 (:23-24), title at y 6, inventory label at imageHeight - 96 + 2 (:31-32)", scr,
                 'withDefaultNamespace("textures/gui/reactors/gui_rbmk_storage.png")', "this.imageWidth=176;", "this.imageHeight=186;",
                 "this.imageWidth/2-this.font.width(this.title)/2,6,4210752,false", "this.playerInventoryTitle,8,this.imageHeight-96+2,4210752,false")
    unchanged = [p for p in UNTOUCHED if (p.startswith(BE) or p.startswith(BLK)) and not hashed_equal(inp, st, p)]
    ck("V2.base-unchanged", not unchanged, "RBMKSlottedBaseBlockEntity, RBMKBaseBlockEntity, RBMKBaseBlock, RBMKRodBlockEntity and the other 24A-24E RBMK files are byte-equal to the start", unchanged)


# ---------------------------------------------------------------- V3 waste drum against V1

def v3_drum(ck, inp, st):
    text = lf(st.text(DRUM))
    upd = body(text, "public void updateEntity()")
    heat = [rewrite(ocode_line(inp, "drum", n), [lit("worldObj", "this.level"), lit("slots[i]", "stack")]) for n in (215, 216)]
    ck("V3.cooling-constants", heat == ["rod.updateHeat(this.level,stack,0.025);", "rod.provideHeat(this.level,stack,20,0.025);"] and all(h in upd for h in heat),
       "a rod is cooled with updateHeat(0.025) then provideHeat(20, 0.025) (original :215-216)", (heat, upd[:400]))
    # Since review R2-F2 a rod only marks the drum dirty when its core or hull temperature actually changed this tick.
    rod_branch = ("if(stack.getItem()instanceofRBMKRodItemrod){doublecore=RBMKRodItem.getCoreHeat(stack);doublehull=RBMKRodItem.getHullHeat(stack);"
                  + "".join(heat) + "if(core!=RBMKRodItem.getCoreHeat(stack)||hull!=RBMKRodItem.getHullHeat(stack))rods=true;continue;}")
    ck("V3.rod-before-roll", ordered(upd, "if(stack.isEmpty())continue;", rod_branch, "if(this.random().nextInt(r)==0){"),
       "the rod branch comes before the decay roll and skips it (original :212-218: the roll is the else branch)", upd[:600])
    ck("V3.water-and-rate", ordered(upd, "intwater=this.countWater();if(water<=0)return;", "intr=DECAY_TICKS/water;") and "publicstaticfinalintDECAY_TICKS=72000;" in code_of(text),
       "no water does nothing; r = 72000 / water = 60 * 60 * 20 / water (original :204-206)")
    ck("V3.set-changed", upd.endswith("if(changed||(rods&&this.level.getGameTime()%20==0))this.setChanged();"), "the NEO-only setChanged: on a conversion or every 20 ticks with a rod present", upd[-120:])
    o = text.index("if(changed || (rods")
    ck("V3.set-changed-commented", "NEO-only" in text[max(0, o - 300):o], "the 20-tick setChanged is commented as NEO-only")
    place = body(text, "public boolean canPlaceItem(int slot, ItemStack stack)")
    ck("V3.can-place", place == "return!stack.isEmpty()&&(this.isKey(stack)||stack.getItem()instanceofRBMKRodItem);", "canPlaceItem: a table key or any rod (original :104)", place)
    take = body(text, "public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction)")
    gate = rewrite(ocode_line(inp, "drum", 185), [lit("ItemRBMKRod", "RBMKRodItem"), lit("itemStack", "stack")])
    ck("V3.extraction-gate", take == "if(stack.getItem()instanceofRBMKRodItem)" + gate + "return!this.isKey(this.getItem(slot));",
       "canTakeItemThroughFace: a rod only with core < 50 and hull < 50 (original :184-185), other items unchanged", first_diff("if(stack.getItem()instanceofRBMKRodItem)" + gate, take))
    ck("V3.hopper-guard", "returnthis.getItem(slot).isEmpty()&&this.canPlaceItem(slot,stack);" in code_of(text), "the NEO-only hopper guard (empty slots only) is kept")
    ck("V3.unchanged", all(hashed_equal(inp, st, p) for p in (J + "inventory/recipes/FuelPoolRecipes.java", J + "inventory/menus/MachineWasteDrumMenu.java", J + "handler/FuelPoolRecipeClientSync.java")),
       "FuelPoolRecipes (the nine ZIRNOX rows and the JSON contract), MachineWasteDrumMenu and FuelPoolRecipeClientSync are byte-equal to the start")
    start = code_of(inp.start[DRUM])
    ck("V3.isKey-countWater-unchanged", body(inp.start[DRUM], "public int countWater()") == body(text, "public int countWater()")
       and body(inp.start[DRUM], "private boolean isKey(ItemStack stack)") == body(text, "private boolean isKey(ItemStack stack)") and "DECAY_TICKS=72000" in start,
       "countWater and isKey are unchanged")


# ---------------------------------------------------------------- V4 disassembly

def v4_disassembly(ck, inp, st):
    ser = code_of(st.text(SER))
    contains_all(ck, "V4.serializer", "NtmRecipeSerializers: a deferred register on RECIPE_SERIALIZER with rbmk_rod_disassembly = SimpleCraftingRecipeSerializer(RBMKRodDisassemblyRecipe::new)", ser,
                 "DeferredRegister.create(Registries.RECIPE_SERIALIZER,NuclearTechMod.MODID)",
                 'RECIPE_SERIALIZERS.register("rbmk_rod_disassembly",()->newSimpleCraftingRecipeSerializer<>(RBMKRodDisassemblyRecipe::new));', "RECIPE_SERIALIZERS.register(eventBus);")
    ntm = code_of(st.text(NTM))
    ck("V4.registered-once", ntm.count("NtmRecipeSerializers.register(eventBus);") == 1 and ordered(ntm, "NtmMenuTypes.register(eventBus);", "NtmRecipeSerializers.register(eventBus);"),
       "NtmRecipeSerializers is registered exactly once in NuclearTechMod, after NtmMenuTypes")
    rec = lf(st.text(REC))
    m = body(rec, "public boolean matches(CraftingInput input, Level level)")
    om = rewrite(sq("".join(inp.ol["craft"][23:25])), [lit("ItemRBMKRod", "RBMKRodItem"), lit("((RBMKRodItem)stack.getItem()).pellet", "rod.pellet"),
                                                      lit("stack.getItem()instanceofRBMKRodItem&&", "stack.getItem()instanceofRBMKRodItemrod&&")])
    ck("V4.matches", m == "ItemStackstack=singleStack(input);" + om, "matches: one stack, a rod with a pellet, hull and core < 50 (original :19-25); enrichment untested", first_diff("ItemStackstack=singleStack(input);" + om, m))
    a = body(rec, "public ItemStack assemble(CraftingInput input, HolderLookup.Provider registries)")
    tbl = [lit("ItemRBMKRod", "RBMKRodItem"), lit("MathHelper.clamp_int", "Mth.clamp")]
    enrich = rewrite(ocode_line(inp, "craft", 53), tbl)
    meta = rewrite(ocode_line(inp, "craft", 54), tbl)
    gate = rewrite(ocode_line(inp, "craft", 48) + "returnItemStack.EMPTY;", tbl)
    heat = rewrite(ocode_line(inp, "craft", 51), tbl)
    want = ("ItemStackstack=singleStack(input);if(stack.getItem()instanceofRBMKRodItemrod){if(rod.pellet==null)returnItemStack.EMPTY;" + gate + heat + enrich + meta
            + "returnMetaHelper.newStack(rod.pellet,8,meta);}}returnItemStack.EMPTY;")
    ck("V4.assemble", a == want, "assemble: no pellet or enrichment > 0.99 gives nothing, else 8 pellets of META 4 - clamp(ceil(e * 5 - 1), 0, 4) + (xenon >= 0.5 ? 5 : 0) (original :45-56)", first_diff(want, a))
    ck("V4.single-stack", body(rec, "private static ItemStack singleStack(CraftingInput input)") == "ItemStackfound=ItemStack.EMPTY;for(inti=0;i<input.size();i++){ItemStackstack=input.getItem(i);if(stack.isEmpty())continue;if(!found.isEmpty())returnItemStack.EMPTY;found=stack;}returnfound;",
       "singleStack: the only non-empty stack, EMPTY for none or several (original hasExactlyOneStack / getFirstStack)")
    ck("V4.dims-serializer", body(rec, "public boolean canCraftInDimensions(int width, int height)") == "returnwidth*height>=1;"
       and body(rec, "public RecipeSerializer<?> getSerializer()") == "returnNtmRecipeSerializers.RBMK_ROD_DISASSEMBLY.get();" and "getRemainingItems" not in code_of(rec),
       "canCraftInDimensions w * h >= 1, the serializer, and the inherited getRemainingItems (the rod's crafting remainder)")
    gd = json.loads(st.text(G_DIS))
    ck("V4.generated-special", gd == {"type": "hbmsntm:rbmk_rod_disassembly", "category": "misc"}, "data/hbmsntm/recipe/rbmk_rod_disassembly.json is the special recipe type", gd)
    gs = json.loads(st.text(G_STO))
    want_s = {"type": "minecraft:crafting_shaped", "category": "misc", "key": {"C": {"item": "hbmsntm:crate_steel"}, "R": {"item": "hbmsntm:rbmk_blank"}},
              "pattern": ["C", "R", "C"], "result": {"count": 1, "id": "hbmsntm:rbmk_storage"}}
    ck("V4.generated-storage", gs == want_s, "data/hbmsntm/recipe/rbmk_storage.json is C/R/C with crate_steel / rbmk_blank -> 1 rbmk_storage (original CraftingManager.java:770)", gs)
    others = [p for p in st.tree if p.startswith(RECIPES) and p not in (G_DIS, G_STO) and not hashed_equal(inp, st, p)]
    gone = [p for p in inp.base_files if p.startswith(RECIPES) and p not in st.tree]
    ck("V4.no-other-recipe", not others and not gone, "no other generated recipe changed, appeared or vanished", (others[:5], gone[:5]))
    ck("V4.anvil-unchanged", hashed_equal(inp, st, J + "inventory/recipes/anvil/AnvilRecipes.java") and "AnvilRecipes.java:921-925" in st.text(RP),
       "AnvilRecipes.java is byte-equal to the start; the tier-4 recycling row (original :921-925) is recorded in NtmRecipeProvider as not registered")
    rp = code_of(st.text(RP))
    ck("V4.provider", 'SpecialRecipeBuilder.special(RBMKRodDisassemblyRecipe::new).save(recipeOutput,ResourceLocation.fromNamespaceAndPath("hbmsntm","rbmk_rod_disassembly"));' in rp,
       "NtmRecipeProvider saves the special recipe as hbmsntm:rbmk_rod_disassembly")


# ---------------------------------------------------------------- V5 JEI

def v5_jei(ck, inp, st):
    fp = lf(st.text(JFP))
    rows = body(fp, "public static List<FuelPoolRecipe> getRodRecipes()")
    nd = inp.ol["ndis"]
    hot = [rewrite(sq(nd[n - 1].strip()), [lit("ItemRBMKRod", "RBMKRodItem"), lit("(stack,", "(hot,")]) for n in (75, 79, 80)]
    cooled = rewrite(ocode_line(inp, "fpr", 48), [lit("ItemRBMKRod", "RBMKRodItem"), lit("(result,", "(cooled,")])
    ck("V5.fuel-pool-rows", ordered(rows, "for(RBMKRodItemrod:RBMKRodItem.CRAFTABLE_RODS){", *hot, cooled) and hot[0] == "RBMKRodItem.setYield(hot,0.2*rod.yield);",
       "one fuel-pool row per craftable rod: input ComparableStackHeat(rod, true).toStack() = yield 0.2 x, core 100, hull 50 (original :75, :79-80), output yield 0.2 x (FuelPoolRecipes :48)",
       (hot, cooled, rows[:400]))
    sr = body(fp, "public void setRecipe(IRecipeLayoutBuilder builder, FuelPoolRecipe recipe, IFocusGroup focuses)")
    ck("V5.fuel-pool-display", "ItemStack[]rod=ROD_ROWS.get(recipe);" in sr and "rod!=null?rod[0].copy():recipe.input()" in sr and "rod!=null?rod[1].copy():recipe.output()" in sr,
       "setRecipe shows the rod rows' display stacks and the table rows unchanged")
    jei = lf(st.text(JEI))
    jc = code_of(jei)
    reg = body(jei, "public void registerRecipes(IRecipeRegistration registration)") if "public void registerRecipes(IRecipeRegistration registration)" in jei else jc
    ck("V5.rows-outside-refresh", "registration.addRecipes(FuelPoolRecipeHandler.RECIPE_TYPE,FuelPoolRecipeHandler.getRodRecipes());" in reg
       and "this.displayedFuelPoolRecipes=FuelPoolRecipeHandler.getRecipes();" in reg and "getRodRecipes" not in body(jei, "private void refreshFuelPoolRecipes()"),
       "the rod rows are added on their own, outside displayedFuelPoolRecipes / knownFuelPoolRecipes, and refreshFuelPoolRecipes never touches them")
    ck("V5.disassembly-registered", jc.count("newRBMKRodDisassemblyRecipeHandler(guiHelper)") == 1
       and "registration.addRecipes(RBMKRodDisassemblyRecipeHandler.RECIPE_TYPE,RBMKRodDisassemblyRecipeHandler.getRecipes());" in reg
       and "registration.addRecipeCatalyst(net.minecraft.world.item.Items.CRAFTING_TABLE,RBMKRodDisassemblyRecipeHandler.RECIPE_TYPE);" in jc,
       "the disassembly category, its rows and the crafting table catalyst are registered once each")
    jd = lf(st.text(JDIS))
    dc = code_of(jd)
    contains_all(ck, "V5.disassembly-category", "category id hbmsntm:rbmk_rod_disassembly, title key jei.hbmsntm.rbmk_rod_disassembly, crafting table icon, gui_nei.png", dc,
                 'RecipeType.create(NuclearTechMod.MODID,"rbmk_rod_disassembly",DisassemblyRecipe.class)', 'Component.translatable("jei.hbmsntm.rbmk_rod_disassembly")',
                 "helper.createDrawableItemLike(Items.CRAFTING_TABLE)", 'withDefaultNamespace("textures/gui/jei/gui_nei.png")')
    gr = body(jd, "public static List<DisassemblyRecipe> getRecipes()")
    loop = sq(nd[26].strip())
    ck("V5.disassembly-rows", ordered(gr, "for(RBMKRodItemrod:RBMKRodItem.CRAFTABLE_RODS){", "if(rod.pellet==null)continue;", loop,
                                      "recipes.add(newDisassemblyRecipe(rodStack(rod,enrichment,false),MetaHelper.newStack(rod.pellet,8,enrichment)));", "if(rod.pellet.isXenonEnabled()){",
                                      "recipes.add(newDisassemblyRecipe(rodStack(rod,enrichment,true),MetaHelper.newStack(rod.pellet,8,enrichment+5)));"),
       "rows per rod with a pellet: e = 0..4 to META e, plus xenon rows to META e + 5 when xenon is enabled (original :26-35)", gr[:500])
    rs = body(jd, "private static ItemStack rodStack(RBMKRodItem rod, int enrichment, boolean poison)")
    y = rewrite(sq(nd[72].strip()), [lit("ItemRBMKRod", "RBMKRodItem")])
    po = rewrite(sq(nd[76].strip()), [lit("ItemRBMKRod", "RBMKRodItem"), lit("hasPoison", "poison")])
    ck("V5.disassembly-yield", rs == "ItemStackstack=newItemStack(rod);" + y + po + "returnstack;", "the input rod: yield min(1 - e / 5, 0.99) x rod yield, xenon 50 (original :73, :77), cold", first_diff("ItemStackstack=newItemStack(rod);" + y + po + "returnstack;", rs))
    rods = st.text(J + "items/NtmItems.java").count("new RBMKRodItem(") if st.has(J + "items/NtmItems.java") else None
    ck("V5.row-count", rods == CRAFTABLE_RODS, f"{CRAFTABLE_RODS} RBMKRodItem constructions feed CRAFTABLE_RODS, so {CRAFTABLE_RODS} fuel-pool rows (the GameTest log reports the live count)", rods)
    common = [p for p in NEW_CLASSES + [DRUM, CTC, NB, BET, MT, NTM, CC, CHEM] if p not in (SSCREEN, JDIS)]
    leak = {p.rsplit("/", 1)[1]: [x for x in ("net.minecraft.client", "handler.jei", "inventory.screens", "mezz.jei") if x in st.text(p)] for p in common}
    leak = {k: v for k, v in leak.items() if v}
    ck("V5.client-isolation", not leak, "no common class imports net.minecraft.client, JEI or a screen", leak)
    ck("V5.screen-registered-client", "RBMKStorageScreen" in st.text(NMC) and all("RBMKStorageScreen" not in st.text(p) for p in common),
       "RBMKStorageScreen is referenced only from NuclearTechModClient")


# ---------------------------------------------------------------- V6 close-out and registrations

def v6_closeout(ck, inp, st):
    cc = st.text(CC)
    ck("V6.b-config", '.translation("hbmsntm.configuration.enableMachineGravity")' in cc and '.define("enableMachineGravity", false)' in cc and "enableMachineGravity \"" not in cc,
       "(b) the machine gravity translation key and config key have no trailing space")
    chem = code_of(st.text(CHEM))
    m = re.search(r'this\.register\(newGenericRecipe\("chem\.batteryquantum"\).*?\)\);', chem)
    row = m[0] if m else ""
    fin = sq(blank_comments(inp.ol["chem"][195]).strip())
    fout = sq(blank_comments(inp.ol["chem"][197]).strip())
    ck("V6.d-fluids", fin in row and fout[:-2] in row and ".inputFluids(newFluidStack(Fluids.PERFLUOROMETHYL,8000))" not in row,
       "(d) chem.batteryquantum takes PERFLUOROMETHYL_COLD 8000 and gives PERFLUOROMETHYL 8000 (original :196, :198)", (fin, fout, row[:400]))
    srow = re.search(r'this\.register\(newGenericRecipe\("chem\.batteryquantum"\).*?\)\);', code_of(inp.start[CHEM]))
    ck("V6.d-rest-unchanged", bool(srow) and row.replace("PERFLUOROMETHYL_COLD,8000))", "PERFLUOROMETHYL,8000))", 1) == srow[0],
       "(d) the rest of the row (items, duration, power, outputs) is unchanged against the start")
    ctc = lf(st.text(CTC))
    ap = body(ctc, "public static void apply(Player player, CompoundTag tag, BlockPos pos)")
    guard = "if(player.level().hasChunk(pos.getX()>>4,pos.getZ()>>4)&&player.distanceToSqr(pos.getX()+0.5,pos.getY()+0.5,pos.getZ()+0.5)<=MAX_DISTANCE*MAX_DISTANCE){BlockEntitybe=player.level().getBlockEntity(pos);"
    ck("V6.e-guard", ap.startswith(guard) and ap.count("getBlockEntity") == 1, "(e) the loaded + 64-block guard comes before the only getBlockEntity", ap[:300])
    ck("V6.e-constant", "publicstaticfinaldoubleMAX_DISTANCE=64;" in code_of(ctc), "(e) MAX_DISTANCE is a named 64-block constant")
    held = "List<ItemStack>stacks=InventoryUtil.getItemsFromBothHands(player);for(ItemStackstack:stacks){if(stack.getItem()instanceofIControlReceivericr){if(icr.hasPermission(player)){icr.receiveControl(player,tag);icr.receiveControl(tag);break;}}}"
    ck("V6.e-held-unchanged", ap.endswith(held) and "if(packet.tag==null)return;context.enqueueWork(()->apply(context.player(),packet.tag,packet.pos));" in code_of(ctc),
       "(e) the held-item branch and the null-tag drop are unchanged; handleServer delegates to apply")
    ck("V6.e-be-branch", "if(beinstanceofIControlReceivericr){if(icr.hasPermission(player)){icr.receiveControl(player,tag);icr.receiveControl(tag);return;}}" in ap,
       "(e) the block-entity branch keeps the permission check and both receiveControl calls")
    ck("V6.f-comment-only", code_of(inp.start[CT_TYPE]) == code_of(st.text(CT_TYPE)) and inp.start[CT_TYPE] != st.text(CT_TYPE) and "Goal24E" in st.text(CT_TYPE),
       "(f) RBMKColumnType: only the class comment changed")
    counts = {"NtmBlocks": code_of(st.text(NB)).count('register("rbmk_storage",'), "NtmBlockEntityTypes": code_of(st.text(BET)).count('BLOCK_ENTITY_TYPES.register("rbmk_storage",'),
              "NtmMenuTypes": code_of(st.text(MT)).count('reg("rbmk_storage",RBMKStorageMenu::new)'),
              "NuclearTechModClient": code_of(st.text(NMC)).count("event.register(NtmMenuTypes.RBMK_STORAGE.get(),RBMKStorageScreen::new);"),
              "ClientProxy": code_of(st.text(CP)).count("BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_STORAGE.get(),newRenderRBMKLid<>());"),
              "NtmCreativeTabs": code_of(st.text(CTAB)).count("output.accept(NtmBlocks.RBMK_STORAGE);"),
              "loot": code_of(st.text(LOOTP)).count("this.dropSelf(NtmBlocks.RBMK_STORAGE.get());"), "pickaxe": code_of(st.text(TAGP)).count("NtmBlocks.RBMK_STORAGE.get(),"),
              "blockstate": code_of(st.text(BSP)).count("NtmBlocks.RBMK_STORAGE}")}
    ck("V6.registrations-once", all(v == 1 for v in counts.values()), "block, BE type, menu type, screen, lid BER, creative tab, loot, pickaxe tag and blockstate list each name rbmk_storage once", counts)


# ---------------------------------------------------------------- V7 language

def v7_lang(ck, inp, st):
    en, dup_en = json_pairs(st.text(EN))
    zh, dup_zh = json_pairs(st.text(ZH))
    mp = json.loads(st.text(MAP))
    s_en, s_zh, s_mp = json.loads(inp.start[EN]), json.loads(inp.start[ZH]), json.loads(inp.start[MAP])
    want_en = {k: inp.o_en[ok][0][0] for k, ok, _, _ in UP}
    want_en.update({k: v[3] for k, v in LOCAL.items()})
    lp = st.text(LP)
    bad = {k: en.get(k) for k, v in want_en.items() if en.get(k) != v or k in s_en or f'"{k}"' not in lp and k not in ("block.hbmsntm.rbmk_storage",)}
    ck("V7.en-new", not bad and "this.add(NtmBlocks.RBMK_STORAGE, \"RBMK Storage Column\");" in lp, f"the {len(want_en)} new English keys are in NtmLanguageProvider and en_us.json with the original text", bad)
    ck("V7.en-rest", {k: v for k, v in en.items() if k not in want_en} == s_en and not dup_en, "en_us.json: nothing but the new keys changed")
    if not all(k in zh for k in ZH_NEW):
        ck("V7.pending", False, "zh_cn.json does not yet carry the Goal25A keys (add_zh.py not run): pending, not failed", [k for k in ZH_NEW if k not in zh])
        return
    want_zh = {k: inp.o_zh[ok][0][0] for k, ok, _, _ in UP}
    want_zh.update({k: v[4] for k, v in LOCAL.items()})
    want_zh.update({k: v[1] for k, v in FROM_DEFERRED.items()})
    bad = {k: zh.get(k) for k, v in want_zh.items() if zh.get(k) != v}
    ck("V7.zh-new", not bad, f"zh_cn.json has the {len(want_zh)} new entries (12 upstream verbatim, 3 local, shell_copper)", bad)
    ck("V7.zh-rest", {k: v for k, v in zh.items() if k not in want_zh} == s_zh and not dup_zh and all(k not in s_zh for k in want_zh), "zh_cn.json: nothing else changed")
    ent, sent = mp["entries"], s_mp["entries"]
    bad = {}
    for k, ok, _, _ in UP:
        e = ent.get(k, {})
        if not (e.get("kind") == "upstream" and e.get("source_key") == ok and e.get("source_en") == inp.o_en[ok][0][0] and e.get("source_zh") == inp.o_zh[ok][0][0]
                and e.get("target_en") == en.get(k) and e.get("target_zh") == zh.get(k) and placeholders(e.get("source_en", "")) == placeholders(e.get("target_zh", ""))):
            bad[k] = e
    for k, v in LOCAL.items():
        e = ent.get(k, {})
        if not (e.get("kind") == "local" and e.get("reason") and e.get("target_en") == v[3] and e.get("target_zh") == v[4] and (v[0] is None or (e.get("source_key") == v[0]
                and e.get("source_en") == inp.o_en[v[0]][0][0] and e.get("source_zh") == inp.o_zh[v[0]][0][0]))):
            bad[k] = e
    for k, v in FROM_DEFERRED.items():
        e = ent.get(k, {})
        if not (sent.get(k, {}).get("kind") == "deferred" and e.get("kind") == "local" and e.get("target_en") == v[0] and e.get("target_zh") == v[1] and e.get("reason")):
            bad[k] = e
    ck("V7.map-entries", not bad, "zh_cn-map.json: 12 upstream entries with the original en/zh text at the cited lines, 3 local, shell_copper deferred -> local; placeholders preserved", dict(list(bad.items())[:3]))
    rest = {k: v for k, v in ent.items() if k not in want_zh} == {k: v for k, v in sent.items() if k not in want_zh}
    ck("V7.map-rest", rest and {k: v for k, v in mp.items() if k != "entries"} == {k: v for k, v in s_mp.items() if k != "entries"} and len(ent) == len(sent) + len(want_zh) - len(FROM_DEFERRED),
       "zh_cn-map.json: nothing else changed (15 new entries, one converted)")
    eol = [p for p in (ZH, MAP) if st.files[p].count(b"\r\n") != st.files[p].count(b"\n") or b"\r\n" not in st.files[p]]
    ck("V7.crlf", not eol, "zh_cn.json and zh_cn-map.json stay CRLF throughout", eol)


# ---------------------------------------------------------------- V8 resources

def v8_resources(ck, inp, st):
    bad = [p for p in IMPORT_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V8.byte-equal", not bad and len(IMPORT_PATHS) == 7, "the six column textures and the GUI are byte-equal (SHA-256) to the original", bad)
    if inp.own is None:
        ck("V8.ownership-pending", False, "migration/goal25a-resource-ownership.json is absent: pending")
        return
    rows = {a["target_path"]: a for a in inp.own.get("assets", [])}
    wrong = [p for p in IMPORT_PATHS if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None) or rows[p].get("source_path") != O_RES + IMPORTS[IMPORT_PATHS.index(p)][0]]
    ck("V8.ownership", not wrong and len(rows) == 7 and inp.own.get("source_commit") == ORIGINAL_HEAD, "the ownership record lists the seven imports with their source paths and hashes", wrong)


# ---------------------------------------------------------------- V9 scope

ALLOWED_MIGRATION = ("migration/goal25a-",)
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                           "migration/RESOURCE-OWNERSHIP.md", "migration/GOAL25.md", "migration/GOAL25A.md", "migration/GOAL25A-ACCEPTANCE.md", MAP}


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v9_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    # RBMKConsoleGameTests: two comments re-pointed to CompoundTagControl.apply :59-60 (review R2-F1).
    expected = set(NEW_CLASSES + EDITED + [ZH, EN, STAMP, PICK, GT, J + "gametest/RBMKConsoleGameTests.java"] + IMPORT_PATHS + GEN_NEW)
    concurrent = [p for p in changed if p in CONCURRENT and p not in ALLOWED_MIGRATION_EXACT]
    extra = [p for p in changed if p not in expected and p not in CONCURRENT and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V9.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production files incl. ClientProxy, generated outputs, imports, the GameTest, the records)", extra[:10])
    ck("V9.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V9.expected-all-changed", not never, "every expected production, resource, generated and GameTest path differs from the start", never[:5])
    ck("V9.gen-new", sorted(gen_new) == sorted(GEN_NEW), "exactly the seven new generated files appeared", sorted(set(gen_new) ^ set(GEN_NEW)))
    ck("V9.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + [GT, OWN] + IMPORT_PATHS) and all(p in inp.base_files for p in EDITED),
       "the new classes, the GameTest, the imports and the ownership record did not exist at the start; the edited files did")
    ck("V9.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED), "the RBMK base, proxy, multiblock, fuel pool, rod item, anvil and older GameTest files are byte-equal to the start",
       [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    eol = [p for p in EDITED if p in inp.start and ("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n"))]
    ck("V9.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    rest = sorted(p for p in changed if (p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT) and p != MAP)
    ck("V9.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V9.concurrent-session", True, "edited by the concurrent planning session (listed, not part of this batch): " + ", ".join(Path(p).name for p in concurrent))
    ck("V9.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V10 / V11 / V12

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")
GT_AREAS = ("storage_column", "compaction", "automation", "break_drops", "meltdown", "drum_rod_cooling", "drum_rod_rules", "disassembly", "config_and_chem", "control_guard", "pile_balance")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v10_gametest(ck, inp, st):
    ck("V10.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", other_gametests())
    ck("V10.present", st.has(GT), "RBMKRecyclingGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V10.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V10.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V10.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V10.marker", f'TAG = "{GT_MARK}"' in live and 'LOGGER.info("{} {} passed", TAG, name);' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = [n for n in tests if f'"{n}"' not in body(live, f"void {n}(GameTestHelper helper)")]
    ck("V10.report-name", not miss, "every test passes its own name to the passed helper", miss)
    ck("V10.areas", all(any(a in n for n in tests) for a in GT_AREAS), "the test names cover " + ", ".join(GT_AREAS), [a for a in GT_AREAS if not any(a in n for n in tests)])
    ck("V10.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKRecyclingGameTests references no client class")
    ck("V10.pile-method", '"[hbm-rbmk-pile]"' in live and "PILE_TICKS = 2400" in live and "pileLog(helper, grid, start[0], lastT, problems)" in live,
       "the (h) pile method of build/migration/goal25a/pile/gametest-method.java.txt is present")
    return dict(tests=sorted(tests))


def v11_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    total = other_gametests() + gametest_total([live])
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V11.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({other_gametests()} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V11.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V11.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V11.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    sys.path.insert(0, str(PILE_MODEL.parent))
    import goal25a_pile_model as model  # noqa: PLC0415 - read-only import of the stage-1 model
    rows = model.parse_log(text)
    sim = model.simulate(2400, order="rowmajor", handler="first", control_start="set", boiler_feed=0, boiler_refill=False)
    res = model.compare(sim, rows)
    worst_abs = max(((f, v["max_abs"]) for f, v in res["fields"].items()), key=lambda x: x[1])
    worst_rel = max(((f, v["max_rel"]) for f, v in res["fields"].items()), key=lambda x: x[1])
    ck("V11.pile-compare", res["ok"] and res["compared_ticks"] == 2400, f"the 2,400 logged pile ticks match the original-formula model within {res['tol']} (max abs {worst_abs}, max rel {worst_rel})",
       {k: v for k, v in res.items() if k != "fields"})
    end = sim[-1] if sim else {}
    last = rows[-1] if rows else {}
    over = [k for k in ("h00", "h10", "h20", "h01", "h11", "h21", "h02", "h12", "h22") if last.get(k, 0) > 100]
    ck("V11.pile-no-steam", rows and not over and all(last.get(b) == 0 for b in ("b10.steam", "b20.steam", "b22.steam")), "no column exceeds 100 C and no boiler makes steam at t = 2400", over)
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()),
                pile=dict(ok=res["ok"], compared_ticks=res["compared_ticks"], first_fail_t=res["first_fail_t"], failing_fields=res["failing_fields"], max_abs=worst_abs, max_rel=worst_rel,
                          model_t2400={k: end.get(k) for k in ("nu.col", "src.col", "nu.hull", "src.hull", "nu.core")},
                          log_t2400={k: last.get(k) for k in ("nu.col", "src.col", "nu.hull", "src.hull", "nu.core")},
                          console_fuel_temp_model=(end.get("nu.hull", 0) + end.get("src.hull", 0)) / 2, console_fuel_temp_log=(last.get("nu.hull", 0) + last.get("src.hull", 0)) / 2))


def v12_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    gen = GEN_NEW + [EN, PICK]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        ck("V12.classes", not missing, "the JAR has the 7 new production classes and RBMKRecyclingGameTests", missing)
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
    guarded(ck, "V2", v2_storage, inp, st)
    guarded(ck, "V3", v3_drum, inp, st)
    guarded(ck, "V4", v4_disassembly, inp, st)
    guarded(ck, "V5", v5_jei, inp, st)
    guarded(ck, "V6", v6_closeout, inp, st)
    guarded(ck, "V7", v7_lang, inp, st)
    guarded(ck, "V8", v8_resources, inp, st)
    guarded(ck, "V9", v9_scope, inp, st)
    r10 = guarded(ck, "V10", v10_gametest, inp, st)
    if facts is not None:
        facts["V10"] = r10
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


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    return [
        ("meta_4_to_3", "V4.", t(REC, "int enrichment = 4 - Mth.clamp", "int enrichment = 3 - Mth.clamp")),
        ("meta_times5_to_4", "V4.", t(REC, "getEnrichment(stack) * 5 - 1", "getEnrichment(stack) * 4 - 1")),
        ("meta_xenon_plus5_to_4", "V4.", t(REC, ">= 0.5D ? 5 : 0", ">= 0.5D ? 4 : 0")),
        ("meta_099_to_098", "V4.", t(REC, "getEnrichment(stack) > 0.99D", "getEnrichment(stack) > 0.98D")),
        ("meta_xenon_05_to_04", "V4.", t(REC, "getPoisonLevel(stack) >= 0.5D", "getPoisonLevel(stack) >= 0.4D")),
        ("matches_heat_le", "V4.", t(REC, "RBMKRodItem.getHullHeat(stack) < 50 && RBMKRodItem.getCoreHeat(stack) < 50;\n    }", "RBMKRodItem.getHullHeat(stack) <= 50 && RBMKRodItem.getCoreHeat(stack) < 50;\n    }")),
        ("compaction_period_20", "V2.", t(SBE, "getGameTime() % 10 == 0", "getGameTime() % 20 == 0")),
        ("compaction_loop_bound", "V2.", t(SBE, "i < this.slots.size() - 1", "i < this.slots.size() - 2")),
        ("compaction_after_base", "V2.", T(SBE, lambda x: rep1(rep1(x, "        super.updateEntity();\n    }", "    }"), "        if(this.level.getGameTime() % 10 == 0) {", "        super.updateEntity();\n        if(this.level.getGameTime() % 10 == 0) {"))),
        ("canload_slot_10", "V2.", t(SBE, "return this.slots.get(11).isEmpty() && toLoad", "return this.slots.get(10).isEmpty() && toLoad")),
        ("load_slot_10", "V2.", t(SBE, "this.slots.set(11, toLoad.copy());", "this.slots.set(10, toLoad.copy());")),
        ("storage_place_any", "V2.", t(SBE, "return stack.getItem() instanceof RBMKRodItem;\n    }\n\n    @Override\n    public int[] getSlotsForFace", "return true;\n    }\n\n    @Override\n    public int[] getSlotsForFace")),
        ("block_extra_only", "V2.", t(SBLK, "case EXTRA, DUMMY -> new ProxyComboBlockEntity(pos, state).inventory();", "case EXTRA -> new ProxyComboBlockEntity(pos, state).inventory();\n            default -> null;")),
        ("menu_slot_order", "V2.", t(SMENU, "new Slot(be, i + j * 3, 32 + 32 * j, 29 + 16 * i)", "new Slot(be, j + i * 4, 32 + 32 * j, 29 + 16 * i)")),
        ("screen_height", "V2.", t(SSCREEN, "this.imageHeight = 186;", "this.imageHeight = 166;")),
        ("base_file_touched", "V2.|V9.", T(BE + "RBMKSlottedBaseBlockEntity.java", lambda x: x + "\n")),
        ("drum_0025_to_005", "V3.", t(DRUM, "rod.updateHeat(this.level, stack, 0.025D);", "rod.updateHeat(this.level, stack, 0.05D);")),
        ("drum_20D_to_25D", "V3.", t(DRUM, "rod.provideHeat(this.level, stack, 20D, 0.025D);", "rod.provideHeat(this.level, stack, 25D, 0.025D);")),
        ("drum_gate_le_50", "V3.", t(DRUM, "return RBMKRodItem.getCoreHeat(stack) < 50 && RBMKRodItem.getHullHeat(stack) < 50;", "return RBMKRodItem.getCoreHeat(stack) <= 50 && RBMKRodItem.getHullHeat(stack) <= 50;")),
        ("drum_rod_branch_dropped", "V3.", T(DRUM, lambda x: rep1(x, "            if(stack.getItem() instanceof RBMKRodItem rod) {\n                double core = RBMKRodItem.getCoreHeat(stack);\n                double hull = RBMKRodItem.getHullHeat(stack);\n                rod.updateHeat(this.level, stack, 0.025D);\n                rod.provideHeat(this.level, stack, 20D, 0.025D);\n", "            if(false) {\n                double core = 0, hull = 0;\n"))),
        ("drum_rod_rolls_too", "V3.", t(DRUM, " rods = true;\n                continue;", " rods = true;")),
        ("drum_setchanged_40", "V3.", t(DRUM, "getGameTime() % 20 == 0)) this.setChanged();", "getGameTime() % 40 == 0)) this.setChanged();")),
        ("drum_place_keys_only", "V3.", t(DRUM, "(this.isKey(stack) || stack.getItem() instanceof RBMKRodItem)", "(this.isKey(stack))")),
        ("guard_removed", "V6.", t(CTC, "if(player.level().hasChunk(pos.getX() >> 4, pos.getZ() >> 4) && player.distanceToSqr(pos.getX() + 0.5D, pos.getY() + 0.5D, pos.getZ() + 0.5D) <= MAX_DISTANCE * MAX_DISTANCE) {", "if(true) {")),
        ("guard_distance_128", "V6.", t(CTC, "MAX_DISTANCE = 64D;", "MAX_DISTANCE = 128D;")),
        ("guard_not_loaded_check", "V6.", t(CTC, "if(player.level().hasChunk(pos.getX() >> 4, pos.getZ() >> 4) && player.distanceToSqr(", "if(player.distanceToSqr(")),
        ("chem_back_to_perfluoromethyl", "V6.", t(CHEM, ".inputFluids(new FluidStack(Fluids.PERFLUOROMETHYL_COLD, 8000))", ".inputFluids(new FluidStack(Fluids.PERFLUOROMETHYL, 8000))")),
        ("config_space_readded", "V6.", t(CC, '.define("enableMachineGravity", false);', '.define("enableMachineGravity ", false);')),
        ("column_type_code_changed", "V6.", t(CT_TYPE, "BLANK(0),", "BLANK(1),")),
        ("storage_registered_twice", "V6.", T(CTAB, lambda x: rep1(x, "output.accept(NtmBlocks.RBMK_STORAGE);", "output.accept(NtmBlocks.RBMK_STORAGE);\n                        output.accept(NtmBlocks.RBMK_STORAGE);"))),
        ("lid_ber_removed", "V6.", T(CP, lambda x: drop_line(x, "NtmBlockEntityTypes.RBMK_STORAGE.get(), new RenderRBMKLid"))),
        ("fuel_row_yield_1", "V5.", t(JFP, "RBMKRodItem.setYield(hot, 0.2 * rod.yield);", "RBMKRodItem.setYield(hot, 1.0 * rod.yield);")),
        ("fuel_row_hull_100", "V5.", t(JFP, "RBMKRodItem.setHullHeat(hot, 50);", "RBMKRodItem.setHullHeat(hot, 100);")),
        ("fuel_rows_in_refresh", "V5.", t(JEI, "registration.addRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, FuelPoolRecipeHandler.getRodRecipes());", "this.displayedFuelPoolRecipes.addAll(FuelPoolRecipeHandler.getRodRecipes());")),
        ("disassembly_row_bound_098", "V5.", t(JDIS, "Math.min(1 - ((double) enrichment) / 5, 0.99)", "Math.min(1 - ((double) enrichment) / 5, 0.98)")),
        ("disassembly_xenon_meta", "V5.", t(JDIS, "MetaHelper.newStack(rod.pellet, 8, enrichment + 5)", "MetaHelper.newStack(rod.pellet, 8, enrichment + 4)")),
        ("client_leak", "V5.", t(SBE, "import net.minecraft.core.BlockPos;", "import net.minecraft.core.BlockPos;\nimport net.minecraft.client.Minecraft;")),
        ("serializer_id", "V4.", t(SER, 'RECIPE_SERIALIZERS.register("rbmk_rod_disassembly"', 'RECIPE_SERIALIZERS.register("rbmk_rod_disassemble"')),
        ("serializer_registered_twice", "V4.", T(NTM, lambda x: rep1(x, "NtmRecipeSerializers.register(eventBus);", "NtmRecipeSerializers.register(eventBus);\n        NtmRecipeSerializers.register(eventBus);"))),
        ("generated_type_changed", "V4.", gen_edit(G_DIS, lambda d: d.__setitem__("type", "minecraft:crafting_special_repairitem"))),
        ("generated_storage_pattern", "V4.", gen_edit(G_STO, lambda d: d.__setitem__("pattern", ["C", "C", "R"]))),
        ("anvil_touched", "V4.|V9.", T(J + "inventory/recipes/anvil/AnvilRecipes.java", lambda x: x + "\n")),
        ("resource_byte_flip", "V8.", Bx(IMPORT_PATHS[2], flip_byte)),
        ("gui_byte_flip", "V8.", Bx(IMPORT_PATHS[6], flip_byte)),
        ("zh_value_changed", "V7.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("hbmsntm.keys.reload", "重新装弹")))),
        ("zh_other_key_changed", "V7.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("block.hbmsntm.rbmk_blank", "X")))),
        ("map_source_zh_changed", "V7.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["effect.hbmsntm.mutation"].__setitem__("source_zh", "变异X")))),
        ("en_key_missing", "V7.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.pop("hbmsntm.keys.gunTertiary")))),
        ("unrelated_migration_file", "V9.", lambda st: st.set_bytes("migration/stray.json", b"{}")),
        ("unrelated_src_file", "V9.", lambda st: st.set_bytes(J + "items/Stray.java", b"class Stray {}")),
        ("orig_compaction_line", "V1.|V2.", OE("ste", lambda x: rep1(x, "worldObj.getTotalWorldTime() % 10 == 0", "worldObj.getTotalWorldTime() % 20 == 0"))),
        ("orig_meta_line", "V1.|V4.", OE("craft", lambda x: rep1(x, "4 - MathHelper.clamp_int(", "3 - MathHelper.clamp_int("))),
        ("orig_drum_line_moved", "V1.", OE("drum", lambda x: rep1(x, "\tpublic boolean canExtractItem(int i, ItemStack itemStack, int j) {", "\n\tpublic boolean canExtractItem(int i, ItemStack itemStack, int j) {"))),
        ("gt_marker_changed", "V10.", t(GT, 'TAG = "[hbm-rbmk-recycling]"', 'TAG = "[hbm-rbmk]"'), GT),
        ("gt_batch_shared", "V10.", t(GT, 'batch = "rbmk_recycling_drum_rules"', 'batch = "rbmk_recycling_drum_cooling"'), GT),
        ("gt_deleted", "V10.|V9.", D(GT), GT),
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
    for sec in ("V11", "V12"):
        out.setdefault(sec, [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec in ("V11", "V12") and not items:
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
    if extra.get("gametest_log"):
        print("pile:", json.dumps(extra["gametest_log"]["pile"], default=str))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
