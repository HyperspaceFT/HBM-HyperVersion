"""Verify the Goal25C batch statically: the RBMK autoloader (rbmk_autoloader: RBMKAutoloaderBlock, RBMKAutoloaderBlockEntity,
RBMKAutoloaderMenu, RBMKAutoloaderScreen, RenderRBMKAutoloader), its registrations, datagen, the ass.rbmkautoloader assembly row, the language
entries, the imported resources and the GameTest source; with --gametest-log the GameTest log and its logged tick numbers.

Read-only for both worktrees. Writes only build/migration/goal25c/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal25c/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (tile entity, block, container, GUI, renderer, assembly row, ModBlocks, machine base, rod, resource manager, language,
      sounds) parsed at the cited lines; a moved or changed line fails.
- V2  Block entity against V1: constants, the four stages in order, the 20-tick check, < cycle / >= cycle, delays 40, the 9..18 / 0..9
      loops, the NEO null guard and setChanged additions, sync order, NBT keys, slot rules, control clamps, ICopiable, range 12, client
      interpolation, sound parameters and tower particle tag values.
- V3  Block: AABBs, dimensions, offset, CORE vs proxy .inventory(), core-only ticker on both sides, standardOpenBehavior, strength 50 / 60.
- V4  Menu and screen: slot origins and order, take-only output, playerInv (8, 100), quickMoveStack ranges, texture, 176 x 182, button
      bounds, minus / plus through CompoundTagControl, label positions and colours.
- V5  Renderer and ResourceManager: Base, p * -4 then +4, Piston, no rotation in the block render, render box y..y+9, item transforms.
- V6  Registrations and datagen (generated blockstate, models, loot, pickaxe tag) and the ass.rbmkautoloader row (setup, items, counts).
- V7  Language: two keys in the provider and en_us.json; zh_cn.json and zh_cn-map.json (pending until written); EOL kept; nothing else.
- V8  Resources: the four imports byte-equal to the original working tree and listed in migration/goal25c-resource-ownership.json.
- V9  Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed separately).
- V10 GameTest source, and with --gametest-log the log (all N passed, every test line, the logged tick numbers re-derived).
- V11 (--jar) the packaged JAR; "not run" without the flag.
- V12 In-memory mutations of the NEO inputs and of the original text (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal25c_rbmk_autoloader.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal25c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "783b6d137936750a8a5ef822e1b29fd1209593f7"

J = "src/main/java/com/hbm/"
ABE = J + "blockentity/machine/rbmk/RBMKAutoloaderBlockEntity.java"
ABLK = J + "blocks/machine/rbmk/RBMKAutoloaderBlock.java"
AMENU = J + "inventory/menus/RBMKAutoloaderMenu.java"
ASCREEN = J + "inventory/screens/RBMKAutoloaderScreen.java"
AREND = J + "render/blockentity/RenderRBMKAutoloader.java"
NEW_CLASSES = [ABLK, ABE, AMENU, ASCREEN, AREND]
NB = J + "blocks/NtmBlocks.java"
BET = J + "blockentity/NtmBlockEntityTypes.java"
MT = J + "inventory/NtmMenuTypes.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
NMC = J + "main/NuclearTechModClient.java"
CP = J + "main/ClientProxy.java"
RM = J + "main/ResourceManager.java"
AMR = J + "inventory/recipes/AssemblyMachineRecipes.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
LOOTP = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
EDITED = [NB, BET, MT, CTAB, NMC, CP, RM, AMR, BSP, LOOTP, TAGP, LP]
SOUNDS = J + "registry/NtmSoundEvents.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal25c-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
G_BS = GEN + "assets/hbmsntm/blockstates/rbmk_autoloader.json"
G_BM = GEN + "assets/hbmsntm/models/block/rbmk_autoloader_particle.json"
G_IM = GEN + "assets/hbmsntm/models/item/rbmk_autoloader.json"
G_LOOT = GEN + "data/hbmsntm/loot_table/blocks/rbmk_autoloader.json"
GEN_NEW = [G_BS, G_BM, G_IM, G_LOOT]
RES = "src/main/resources/assets/hbmsntm/"
GT = J + "gametest/RBMKAutoloaderGameTests.java"
GT_DIR = J + "gametest/"

# files the batch must only read, never change (byte-equal to the start; hashes from baseline.json)
UNTOUCHED = [J + "blockentity/machine/rbmk/" + n for n in ("RBMKRodBlockEntity.java", "RBMKBaseBlockEntity.java", "RBMKSlottedBaseBlockEntity.java", "RBMKDials.java")] + [
    J + "blocks/machine/rbmk/RBMKBaseBlock.java", J + "blocks/DummyableBlock.java", J + "blockentity/ProxyComboBlockEntity.java", J + "blockentity/MachineBaseBlockEntity.java",
    J + "inventory/menus/MenuBase.java", J + "inventory/SlotTakeOnly.java", J + "network/toserver/CompoundTagControl.java", J + "items/machine/RBMKRodItem.java",
    J + "sound/AudioWrapper.java", J + "particle/NtmParticleTypes.java", SOUNDS, J + "gametest/SmokeTestSupport.java", J + "gametest/RBMKReactorGameTests.java",
    J + "gametest/RBMKRecyclingGameTests.java", J + "gametest/RBMKOutgasserGameTests.java", J + "gametest/RBMKConsoleGameTests.java"]

O = "src/main/java/com/hbm/"
O_FILES = dict(te=O + "tileentity/machine/rbmk/TileEntityRBMKAutoloader.java", blk=O + "blocks/machine/rbmk/RBMKAutoloader.java",
               con=O + "inventory/container/ContainerRBMKAutoloader.java", gui=O + "inventory/gui/GUIRBMKAutoloader.java",
               rend=O + "render/tileentity/RenderRBMKAutoloader.java", amr=O + "inventory/recipes/AssemblyMachineRecipes.java", mb=O + "blocks/ModBlocks.java",
               tmb=O + "tileentity/TileEntityMachineBase.java", rod=O + "tileentity/machine/rbmk/TileEntityRBMKRod.java", rm=O + "main/ResourceManager.java",
               snd="src/main/resources/assets/hbm/sounds.json")
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"

# V1: every cited original line, {file key: {line: needle}}
ANCHORS = {
    "te": {37: "public static double speed = 0.005D;", 39: "public int cycle = 50;", 44: "super(18);", 49: 'return "container.rbmkAutoloader";', 55: "if(!worldObj.isRemote) {",
           57: "if(delay > 0) delay--;", 59: "if(delay <= 0 && this.isRetracting && this.piston > 0D) {", 60: "this.piston -= this.speed;", 61: "if(this.piston <= 0) {",
           62: "this.piston = 0;", 63: "this.delay = 40;", 68: "if(isRetracting && worldObj.getTotalWorldTime() % 20 == 0 && this.hasFuel() && this.hasSpace()) {",
           70: "if(below instanceof RBMKBase) {", 71: "findCore(worldObj, xCoord, yCoord - 1, zCoord);", 73: "if(tile instanceof TileEntityRBMKRod) {",
           75: "if(rod.coldEnoughForAutoloader()) {", 76: "if(rod.slots[0] == null || (rod.slots[0] != null && rod.slots[0].getItem() instanceof ItemRBMKRod && ItemRBMKRod.getEnrichment(rod.slots[0]) * 100 < cycle)) {",
           77: "this.isRetracting = false;", 84: "if(delay <= 0 && !this.isRetracting && this.piston < 1D) {", 85: "this.piston += this.speed;", 86: "if(this.piston >= 1) {",
           87: "this.piston = 1;", 88: "this.delay = 40;", 93: "if(!isRetracting && this.piston >= 1D) {", 94: "this.piston = 1D;", 97: "if(below instanceof RBMKBase) {",
           103: "if(rod.slots[0] != null && this.hasSpace()) {", 104: "for(int i = 9; i < 18; i++) {", 105: "if(slots[i] == null) {", 106: "slots[i] = rod.slots[0].copy();",
           107: "rod.slots[0] = null;", 113: "if(rod.slots[0] == null) {", 114: "for(int i = 0; i < 9; i++) {",
           116: "if(stack != null && stack.getItem() instanceof ItemRBMKRod && ItemRBMKRod.getEnrichment(stack) * 100 >= cycle) {", 117: "rod.slots[0] = stack.copy();",
           118: "slots[i] = null;", 124: "this.isRetracting = true;", 125: "this.delay = 40;", 130: "this.networkPackNT(100);", 133: "this.lastPiston = this.renderPiston;",
           136: "this.renderPiston = this.renderPiston + ((this.syncPiston - this.renderPiston) / (double) this.turnProgress);", 137: "--this.turnProgress;",
           139: "this.renderPiston = this.syncPiston;", 142: "if(this.renderPiston > 0.01 && this.renderPiston < 0.99) {",
           144: 'getLoopedSound("hbm:door.wgh_start", xCoord, yCoord, zCoord, this.getVolume(0.75F), 25F, 1.0F, 5);', 147: "this.audioLift.updateVolume(this.getVolume(0.75F));",
           153: 'playSoundClient(xCoord, yCoord, zCoord, "hbm:door.wgh_stop", this.getVolume(2F), 1F);', 157: "if(this.renderPiston > 0.99) {", 159: 'data.setString("type", "tower");',
           160: 'data.setFloat("lift", 0F);', 161: 'data.setFloat("base", 0.25F);', 162: 'data.setFloat("max", 1.5F);', 163: 'data.setInteger("life", 70 + worldObj.rand.nextInt(30));',
           164: 'data.setDouble("posX", xCoord + 0.5 + worldObj.rand.nextGaussian() * 0.125);', 165: 'data.setDouble("posZ", zCoord + 0.5 + worldObj.rand.nextGaussian() * 0.125);',
           166: 'data.setDouble("posY", yCoord + 0.25);', 167: 'data.setBoolean("noWind", true);', 168: 'data.setFloat("alphaMod", 2F);', 169: 'data.setFloat("strafe", 0.05F);',
           170: "for(int i = 0; i < 3; i++) MainRegistry.proxy.effectNT(data);", 175: "public boolean hasFuel() {", 176: "for(int i = 0; i < 9; i++) {",
           178: "ItemRBMKRod.getEnrichment(stack) * 100 >= cycle) {", 183: "return false;", 187: "for(int i = 9; i < 18; i++) if(slots[i] == null) return true;", 188: "return false;",
           193: "super.serialize(buf);", 194: "buf.writeDouble(this.piston);", 195: "buf.writeInt(this.cycle);", 200: "super.deserialize(buf);", 201: "this.syncPiston = buf.readDouble();",
           202: "this.cycle = buf.readInt();", 204: "this.turnProgress = 2;", 209: "return stack.getItem() instanceof ItemRBMKRod && ItemRBMKRod.getEnrichment(stack) * 100 >= cycle && i < 9;",
           214: "return this.piston <= 0 ? new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17 } : new int[0];", 219: "return i >= 9;",
           225: 'piston = nbt.getDouble("piston");', 226: 'isRetracting = nbt.getBoolean("ret");', 227: 'delay = nbt.getInteger("delay");', 228: 'cycle = nbt.getInteger("cycle");',
           234: 'nbt.setDouble("piston", piston);', 235: 'nbt.setBoolean("ret", isRetracting);', 236: 'nbt.setInteger("delay", delay);', 237: 'nbt.setInteger("cycle", cycle);',
           245: "aabb = AxisAlignedBB.getBoundingBox(xCoord, yCoord, zCoord, xCoord + 1, yCoord + 9, zCoord + 1);", 252: "return 65536.0D;", 257: "return this.isUseableByPlayer(player);",
           262: 'if(data.hasKey("minus") && this.cycle > 5) this.cycle -= 5;', 263: 'if(data.hasKey("plus") && this.cycle < 95) this.cycle += 5;',
           264: "this.cycle = MathHelper.clamp_int(cycle, 5, 95);", 265: "this.markChanged();", 281: "NBTTagCompound data = new NBTTagCompound();", 282: 'data.setInteger("cycle", cycle);',
           283: "return data;", 288: 'if(nbt.hasKey("cycle")) {', 289: 'this.cycle = MathHelper.clamp_int(nbt.getInteger("cycle"), 5, 95);'},
    "blk": {18: "this.bounding.add(AxisAlignedBB.getBoundingBox(-0.125, 0, -0.125, 0.125, 4, 0.125));", 19: "this.bounding.add(AxisAlignedBB.getBoundingBox(-0.5, 4, -0.5, 0.5, 9, 0.5));",
            24: "if(meta >= 12) return new TileEntityRBMKAutoloader();", 25: "return new TileEntityProxyCombo().inventory();", 30: "return new int[] {8, 0, 0, 0, 0, 0};", 35: "return 0;",
            40: "return this.standardOpenBehavior(world, x, y, z, player, 0);"},
    "con": {18: "this.addSlots(loader, 0, 17, 18, 3, 3);", 19: "this.addTakeOnlySlots(loader, 9, 107, 18, 3, 3);", 20: "this.playerInv(invPlayer, 8, 100);", 32: "if(index <= 17) {",
            33: "if(!this.mergeItemStack(stack, 18, this.inventorySlots.size(), true)) {", 37: "if(!this.mergeItemStack(stack, 0, 9, false)) return null;"},
    "gui": {20: '":textures/gui/machine/gui_autoloader.png"', 27: "this.xSize = 176;", 28: "this.ySize = 182;",
            40: "if(guiLeft + 74 <= x && guiLeft + 74 + 12 > x && guiTop + 36 < y && guiTop + 36 + 12 >= y) {", 43: 'data.setBoolean("minus", true);',
            47: "if(guiLeft + 90 <= x && guiLeft + 90 + 12 > x && guiTop + 36 < y && guiTop + 36 + 12 >= y) {", 50: 'data.setBoolean("plus", true);',
            59: "this.xSize / 2 - this.fontRendererObj.getStringWidth(name) / 2, 6, 0xFFFFFF);", 60: '8, this.ySize - 96 + 2, 4210752);', 62: 'String percent = loader.cycle + "%";',
            63: "this.xSize / 2 - this.fontRendererObj.getStringWidth(percent) / 2, 23, 0x00FF00);", 70: "drawTexturedModalRect(guiLeft, guiTop, 0, 0, xSize, ySize);"},
    "rend": {20: "GL11.glTranslated(x + 0.5D, y, z + 0.5D);", 24: "bindTexture(ResourceManager.rbmk_autoloader_tex);", 25: 'ResourceManager.rbmk_autoloader.renderPart("Base");',
             28: "double p = (press.lastPiston + (press.renderPiston - press.lastPiston) * interp);", 29: "GL11.glTranslated(0, p * -4D, 0);", 31: "GL11.glTranslated(0, 4, 0);",
             32: 'ResourceManager.rbmk_autoloader.renderPart("Piston");', 47: "GL11.glTranslated(0, -6, 0);", 48: "GL11.glScaled(1.75, 1.75, 1.75);", 51: "GL11.glRotated(180, 0, 1, 0);",
             55: 'ResourceManager.rbmk_autoloader.renderPart("Base");', 56: 'ResourceManager.rbmk_autoloader.renderPart("Piston");'},
    "amr": {532: 'this.register(new GenericRecipe("ass.rbmkautoloader").setup(100, 100).outputItems(new ItemStack(ModBlocks.rbmk_autoloader, 1))',
            533: ".inputItems(new OreDictStack(STEEL.plateWelded(), 4), new OreDictStack(PB.plateCast(), 4), new OreDictStack(B.ingot(), 4), new ComparableStack(ModItems.motor, 3))",
            534: ".inputItemsEx(", 535: ".setPools528("},
    "mb": {2142: 'rbmk_autoloader = new RBMKAutoloader().setBlockName("rbmk_autoloader").setCreativeTab(MainRegistry.machineTab).setHardness(50.0F).setResistance(60.0F)'},
    "tmb": {81: "public boolean isUseableByPlayer(EntityPlayer player) {", 82: "if(worldObj.getTileEntity(xCoord, yCoord, zCoord) != this) {",
            86: "return player.getDistanceSq(xCoord + 0.5D, yCoord + 0.5D, zCoord + 0.5D) <= range * range;", 91: "return 12D;"},
    "rod": {94: "public boolean coldEnoughForAutoloader() {", 96: "return ItemRBMKRod.getHullHeat(slots[0]) <= 1_000;", 98: "return true;"},
    "rm": {1682: 'rbmk_autoloader = new HFRWavefrontObject(new ResourceLocation(RefStrings.MODID, "models/rbmk/autoloader.obj")).asVBO();',
           1693: 'rbmk_autoloader_tex = new ResourceLocation(RefStrings.MODID, "textures/models/machines/rbmk_autoloader.png");'},
    "snd": {94: '"door.wgh_start": {"category": "block", "sounds": [{"name": "block/door/wgh_start", "stream": false}]},',
            95: '"door.wgh_stop": {"category": "block", "sounds": [{"name": "block/door/wgh_stop", "stream": false}]},'},
}

# V7: (NEO key, original key, en_US.lang line, zh_CN.lang line)
UP = [("block.hbmsntm.rbmk_autoloader", "tile.rbmk_autoloader.name", 6212, 5920), ("container.rbmkAutoloader", "container.rbmkAutoloader", 788, 5911)]
NEW_KEYS = [u[0] for u in UP]

IMPORTS = [("models/rbmk/autoloader.obj", "models/obj/rbmk/autoloader.obj"), ("textures/models/machines/rbmk_autoloader.png", "textures/models/machines/rbmk_autoloader.png"),
           ("textures/blocks/rbmk_autoloader.png", "textures/block/rbmk/rbmk_autoloader.png"), ("textures/gui/machine/gui_autoloader.png", "textures/gui/machine/gui_autoloader.png")]
IMPORT_PATHS = [RES + n for _, n in IMPORTS]

# V6: the original ore dictionary / item of the ass.rbmkautoloader inputs -> NEO ingredient expression
RECIPE_ITEMS = {"newOreDictStack(STEEL.plateWelded(),": "NtmItems.castPlateWeldedIngredient(CastPlateItem.Type.STEEL,",
                "newOreDictStack(PB.plateCast(),": "NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD,",
                "newOreDictStack(B.ingot(),": "newComparableStack(NtmItems.INGOT_BORON.get(),", "newComparableStack(ModItems.motor,": "newComparableStack(NtmItems.MOTOR.get(),"}

GT_MARK = "[hbm-rbmk-autoloader]"
START_GAMETESTS = 224
GT_AREAS = ("autoloader_placement", "autoloader_swap_cycle", "autoloader_no_swap", "autoloader_slots", "autoloader_control", "autoloader_persistence", "autoloader_recipe")
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


# ---------------------------------------------------------------- text helpers (as verify_goal25b_rbmk_outgasser.py)

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


def match_brace(code, open_index):
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced {")


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


def method_span(text, signature):
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


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
    return [(n, needle, lines[n - 1].strip()[:120] if n <= len(lines) else None) for n, needle in expected.items() if n > len(lines) or needle not in lines[n - 1]]


def placeholders(s):
    return sorted(re.findall(r"%(?:\d+\$)?[sdf]|%%|\$", s))


def ordered(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def missing_order(code, *frags):
    """The first fragment that is not found after the previous one, or None."""
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return f
        pos = i + len(f)
    return None


def contains_all(ck, cid, label, code, *needles):
    miss = [n for n in needles if n not in code]
    return ck(cid, not miss, label, miss)


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


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


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
            try:
                inp.start[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                inp.start[rel] = None
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o = {name: lf(read_text(ORIGINAL / path)) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    tree = hash_tree()
    files = {}
    load = set(NEW_CLASSES + EDITED + UNTOUCHED + [ZH, MAP, OWN, EN, STAMP, PICK, GT] + GEN_NEW + IMPORT_PATHS)
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.o_res = {}
    for orig, neo in IMPORTS:
        f = ORIGINAL / (O_RES + orig)
        inp.o_res[RES + neo] = f.read_bytes() if f.exists() else None
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def oline(inp, key, n):
    return sq(blank_comments(inp.ol[key][n - 1]))


def olines(inp, key, first, last):
    return sq(blank_comments("\n".join(inp.ol[key][first - 1:last])))


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    scope = inp.baseline["copied_scope"]
    ck("V0.baseline-copies-match", not bad and len(scope) == len(inp.start_hash_ok) and all(p in inp.start for p in scope),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, {len(scope)} in copied_scope) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 783b6d13", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    needed = NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, PICK] + GEN_NEW
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.start-copies-of-edited", all(p in inp.start for p in EDITED + [EN, PICK, ZH, MAP]), "the start copies of every edited file exist", [p for p in EDITED + [EN, PICK, ZH, MAP] if p not in inp.start])


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", bool(e) and bool(z) and e[0][1] == en_line and z[0][1] == zh_line, f"{okey} is at en_US.lang:{en_line} and zh_CN.lang:{zh_line}",
           (e and e[0][1], z and z[0][1]))


# ---------------------------------------------------------------- V2 block entity against V1

SLOT_RW = [lit("this.speed", "SPEED"), lit("worldObj.getTotalWorldTime()", "this.level.getGameTime()"),
           lit("rod.slots[0]!=null", "!rod.slots.get(0).isEmpty()"), lit("rod.slots[0]==null", "rod.slots.get(0).isEmpty()"),
           lit("slots[i]=rod.slots[0].copy();", "slots.set(i,rod.slots.get(0).copy());"), lit("rod.slots[0]=null;", "rod.slots.set(0,ItemStack.EMPTY);"),
           lit("rod.slots[0]=stack.copy();", "rod.slots.set(0,stack.copy());"), lit("slots[i]==null", "slots.get(i).isEmpty()"),
           lit("ItemStackstack=slots[i];", "ItemStackstack=slots.get(i);"), lit("slots[i]=null;", "slots.set(i,ItemStack.EMPTY);"),
           lit("stack!=null&&", "!stack.isEmpty()&&"), lit("ItemRBMKRod", "RBMKRodItem")]


def rw(s):
    return rewrite(s, SLOT_RW)


def v2_block_entity(ck, inp, st):
    be = lf(st.text(ABE))
    code = code_of(be)
    speed = re.search(r"speed=([\d.]+);", oline(inp, "te", 37))[1]
    cycle = re.search(r"cycle=(\d+);", oline(inp, "te", 39))[1]
    size = re.search(r"super\((\d+)\);", oline(inp, "te", 44))[1]
    name = re.search(r'return("[^"]+");', oline(inp, "te", 49))[1]
    contains_all(ck, "V2.constants", f"SPEED {speed} final (:37), cycle {cycle} (:39), {size} slots (:44), {name} (:49), retracting at start, IControlReceiver + ICopiable", code,
                 f"publicstaticfinaldoubleSPEED={speed};", f"publicintcycle={cycle};", f"super(NtmBlockEntityTypes.RBMK_AUTOLOADER.get(),pos,state,{size});",
                 f"Component.translatable({name})", "privatebooleanisRetracting=true;", "privateintdelay=0;",
                 "publicclassRBMKAutoloaderBlockEntityextendsMachineBaseBlockEntityimplementsIControlReceiver,ICopiable{")
    upd = body(be, "public void updateEntity()")
    server = upd[:upd.index("}else{this.lastPiston")] if "}else{this.lastPiston" in upd else upd
    rod_cond = oline(inp, "te", 76)
    op = re.search(r"\*100(<=|<|>=|>)cycle", rod_cond)
    stages = [
        ("decrement", oline(inp, "te", 57)),
        ("retract :59-65", rw(olines(inp, "te", 59, 65))),
        ("check :68", rw(oline(inp, "te", 68))),
        ("cold :75", "if(rod!=null&&rod.coldEnoughForAutoloader()){"),
        ("rod rule :76-77", "if(loaded.isEmpty()||(loaded.getItem()instanceofRBMKRodItem&&RBMKRodItem.getEnrichment(loaded)*100" + (op[1] if op else "?") + "cycle)){"
         + oline(inp, "te", 77) if rod_cond.startswith("if(rod.slots[0]==null||") else "?"),
        ("extend :84-90", rw(olines(inp, "te", 84, 90))),
        ("full :93-94", rw(olines(inp, "te", 93, 94)) + "RBMKRodBlockEntityrod=this.getRodBelow();if(rod!=null){"),
        ("take :103-111", rw(olines(inp, "te", 103, 111))),
        ("insert :113-122", rw(olines(inp, "te", 113, 122))),
        ("done :124-125", "rod.setChanged();this.setChanged();" + olines(inp, "te", 124, 125) + "}}"),
        ("mark", "if(this.piston!=prevPiston||this.isRetracting!=prevRetracting||this.delay!=prevDelay)this.setChanged();"),
        ("sync :130", oline(inp, "te", 130)),
    ]
    miss = missing_order(server, *[f for _, f in stages])
    ck("V2.stages", miss is None, "the server update holds the original stages in order: delay--, retract (speed, <= 0 -> 0, delay 40), the 20-tick check with hasFuel / hasSpace, "
       "cold enough, empty or enrichment * 100 < cycle, extend (>= 1 -> 1, delay 40), at 1: take the old rod into the first free slot of 9..17, insert the first slot 0..8 rod with "
       "enrichment * 100 >= cycle, ret true, delay 40, the NEO setChanged additions, networkPackNT(100)", miss)
    ck("V2.check-count", server.count("%20==0") == 1 and server.count("this.delay=40;") == 3, "one 20-tick check, three delay = 40 assignments (:63, :88, :125)",
       (server.count("%20==0"), server.count("this.delay=40;")))
    getrod = body(be, "private RBMKRodBlockEntity getRodBelow()")
    ck("V2.null-guard", getrod == "BlockPosbelow=this.worldPosition.below();if(this.level.getBlockState(below).getBlock()instanceofRBMKBaseBlockbase){BlockPoscore=base.findCore(this.level,below);"
       "if(core!=null&&this.level.getBlockEntity(core)instanceofRBMKRodBlockEntityrod)returnrod;}returnnull;",
       "getRodBelow: the block directly below (:69 / :96 yCoord - 1) is an RBMK column, its core (findCore) holds a fuel channel; NEO-only null check on the core", getrod)
    ck("V2.has-fuel", body(be, "public boolean hasFuel()") == rw(olines(inp, "te", 176, 183)), "hasFuel equals :175-184 (slots 0..8, a rod with enrichment * 100 >= cycle)",
       body(be, "public boolean hasFuel()"))
    ck("V2.has-space", body(be, "public boolean hasSpace()") == rw(olines(inp, "te", 187, 188)), "hasSpace equals :186-189 (any empty slot 9..17)", body(be, "public boolean hasSpace()"))
    client = upd[upd.index("}else{this.lastPiston") + 6:] if "}else{this.lastPiston" in upd else ""
    vol, rng, pitch, keep = re.search(r"this\.getVolume\(([\d.]+)\),([\d.]+),([\d.]+),(\d+)\);", oline(inp, "te", 144)).groups()
    svol, spitch = re.search(r"this\.getVolume\(([\d.]+)\),([\d.]+)\);", oline(inp, "te", 153)).groups()
    contains_all(ck, "V2.client", f"client: interpolation over turnProgress (:133-140), lift sound between 0.01 and 0.99 with volume {vol}, range {rng}, pitch {pitch}, keep-alive {keep} (:142-148), "
                 f"stop sound volume {svol} pitch {spitch} (:149-155), the tower particles above 0.99 (:157)", client,
                 olines(inp, "te", 133, 140), oline(inp, "te", 142),
                 f"AudioWrapper.getLoopedSound(NtmSoundEvents.WGH_START.get(),SoundSource.BLOCKS,this,this.getVolume({vol}),{rng},{pitch},{keep});",
                 f"this.audioLift.updateVolume(this.getVolume({vol}));this.audioLift.keepAlive();",
                 f"NtmSoundEvents.WGH_STOP.get(),SoundSource.BLOCKS,this.getVolume({svol}),{spitch});", oline(inp, "te", 157))
    tags = []
    kinds = {"Float": "putFloat", "Integer": "putInt", "Boolean": "putBoolean"}
    for n in range(159, 170):
        m = re.search(r'data\.set(\w+)\("(\w+)",(.*)\);', oline(inp, "te", n))
        if m[1] in kinds:
            tags.append(f'data.{kinds[m[1]]}("{m[2]}",{rewrite(m[3], [lit("worldObj.rand", "this.level.random")])});')
    gx = re.search(r'"posX",xCoord(.*)\);', oline(inp, "te", 164))[1]
    gz = re.search(r'"posZ",zCoord(.*)\);', oline(inp, "te", 165))[1]
    gy = re.search(r'"posY",yCoord(.*)\);', oline(inp, "te", 166))[1]
    count = re.search(r"for\(inti=0;i<(\d+);i\+\+\)", oline(inp, "te", 170))[1]
    rng_rw = [lit("worldObj.rand", "this.level.random")]
    tags += [f"doubleposX=x{rewrite(gx, rng_rw)};", f"doubleposZ=z{rewrite(gz, rng_rw)};",
             f"for(inti=0;i<{count};i++){{ParticleUtil.addParticle(this.level,newNbtParticleOptions(NtmParticleTypes.COOLING_TOWER.get(),data),posX,y{gy},posZ,0,0,0);}}"]
    contains_all(ck, "V2.particles", f"tower particle: every tag value of :159-169 (type tower -> COOLING_TOWER), one shared position, {count} particles (:170)", client, *tags)
    ck("V2.particle-type", '"tower"' in oline(inp, "te", 159), "the original particle type is tower (CoolingTowerParticle)")
    ck("V2.sync", body(be, "public void serialize(RegistryFriendlyByteBuf buf)") == olines(inp, "te", 193, 195)
       and body(be, "public void deserialize(RegistryFriendlyByteBuf buf)") == olines(inp, "te", 200, 204),
       "serialize / deserialize equal :191-205 (super, piston as double, cycle as int; syncPiston, cycle, turnProgress 2)",
       (body(be, "public void serialize(RegistryFriendlyByteBuf buf)"), body(be, "public void deserialize(RegistryFriendlyByteBuf buf)")))
    want_place = set(rw(oline(inp, "te", 209))[len("return"):-1].split("&&"))
    got_place = body(be, "public boolean canPlaceItem(int i, ItemStack stack)")
    ck("V2.can-place", got_place.startswith("return") and set(got_place[len("return"):-1].split("&&")) == want_place, "canPlaceItem has exactly the conjuncts of :209 (rod, enrichment * 100 >= cycle, i < 9)",
       (got_place, want_place))
    face = re.search(r"returnthis\.piston(<=|<)0\?newint\[\]\{([\d,]+)\}:newint\[0\];", oline(inp, "te", 214))
    ck("V2.slots-for-face", body(be, "public int[] getSlotsForFace(Direction direction)") == f"returnthis.piston{face[1]}0?SLOTS:NO_SLOTS;"
       and f"privatestaticfinalint[]SLOTS=newint[]{{{face[2]}}};" in code and "privatestaticfinalint[]NO_SLOTS=newint[0];" in code,
       "getSlotsForFace: all 18 slots while piston <= 0, none otherwise (:212-215)", body(be, "public int[] getSlotsForFace(Direction direction)"))
    ck("V2.can-take", body(be, "public boolean canTakeItemThroughFace(int i, ItemStack stack, Direction direction)") == oline(inp, "te", 219), "canTakeItemThroughFace: i >= 9 (:217-220)",
       body(be, "public boolean canTakeItemThroughFace(int i, ItemStack stack, Direction direction)"))
    load_rw = [lit("nbt.", "tag."), lit("getInteger", "getInt"), (r"(^|;)(piston|isRetracting|delay|cycle)=", r"\1this.\2=")]
    save_rw = [lit("nbt.setDouble", "tag.putDouble"), lit("nbt.setBoolean", "tag.putBoolean"), lit("nbt.setInteger", "tag.putInt"), (r",(piston|isRetracting|delay|cycle)\);", r",this.\1);")]
    want_load = "super.loadAdditional(tag,registries);" + rewrite(olines(inp, "te", 225, 228), load_rw)
    want_save = "super.saveAdditional(tag,registries);" + rewrite(olines(inp, "te", 234, 237), save_rw)
    got_load = body(be, "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    got_save = body(be, "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    ck("V2.nbt", got_load == want_load and got_save == want_save, "NBT keys piston / ret / delay / cycle with their types (:222-238)", (got_load, want_load, got_save, want_save))
    box = re.search(r"getBoundingBox\(xCoord,yCoord,zCoord,xCoord\+(\d+),yCoord\+(\d+),zCoord\+(\d+)\);", oline(inp, "te", 245))
    ck("V2.render-box", body(be, "public AABB getRenderBoundingBox()") == f"BlockPospos=this.getBlockPos();returnnewAABB(pos.getX(),pos.getY(),pos.getZ(),pos.getX()+{box[1]},pos.getY()+{box[2]},pos.getZ()+{box[3]});",
       f"render bounding box x..x+{box[1]}, y..y+{box[2]} (:242-247)", body(be, "public AABB getRenderBoundingBox()"))
    rng12 = re.search(r"return([\d.]+);", oline(inp, "tmb", 91))[1]
    ck("V2.range", body(be, "public boolean stillValid(Player player)") == "if(this.level==null||this.level.getBlockEntity(this.worldPosition)!=this)returnfalse;returnplayer.distanceToSqr("
       f"this.worldPosition.getX()+0.5,this.worldPosition.getY()+0.5,this.worldPosition.getZ()+0.5)<={rng12}*{rng12};" and body(be, "public boolean hasPermission(Player player)") == "returnthis.stillValid(player);",
       f"stillValid / hasPermission = isUseableByPlayer: same block entity, distance squared to the centre <= {rng12} * {rng12} (TileEntityMachineBase.java:81-92, :257)",
       (body(be, "public boolean stillValid(Player player)"), body(be, "public boolean hasPermission(Player player)")))
    ctl_rw = [lit("data.hasKey", "data.contains"), lit("MathHelper.clamp_int(cycle,", "Mth.clamp(this.cycle,"), lit("this.markChanged();", "this.setChanged();")]
    ck("V2.control", body(be, "public void receiveControl(CompoundTag data)") == rewrite(olines(inp, "te", 262, 265), ctl_rw), "receiveControl equals :261-266 (minus / plus by 5, clamp 5..95)",
       body(be, "public void receiveControl(CompoundTag data)"))
    cp_rw = [lit("NBTTagCompound", "CompoundTag"), lit("setInteger", "putInt"), lit("hasKey", "contains"), lit("MathHelper.clamp_int", "Mth.clamp"), lit("getInteger", "getInt")]
    # NEO addition (review R1): pasteSettings marks the block entity after the clamped paste, inside the contains("cycle") block.
    paste = rewrite(olines(inp, "te", 288, 290), cp_rw)
    paste = paste[:-1] + "this.setChanged();}" if paste.endswith(");}") else paste
    ck("V2.copiable", body(be, "public CompoundTag getSettings(Level world, BlockPos pos)") == rewrite(olines(inp, "te", 281, 283), cp_rw)
       and body(be, "public void pasteSettings(CompoundTag nbt, int index, Level world, Player player, BlockPos pos)") == paste,
       "getSettings / pasteSettings equal :279-291 (cycle, clamped 5..95 on paste) plus the NEO setChanged after the paste (review R1)",
       (body(be, "public CompoundTag getSettings(Level world, BlockPos pos)"), body(be, "public void pasteSettings(CompoundTag nbt, int index, Level world, Player player, BlockPos pos)")))
    leaks = [p for p in (ABE, ABLK, AMENU) if re.search(r"import net\.minecraft\.client|import com\.hbm\.render\.|Minecraft\.getInstance", blank_comments(st.text(p)))]
    ck("V2.no-client-leak", not leaks, "the block entity, block and menu import no client class", leaks)
    snd = st.text(SOUNDS)
    ck("V2.sound-ids", 'WGH_START = reg("door.wgh_start")' in snd and 'WGH_STOP = reg("door.wgh_stop")' in snd and "door.wgh_start" in oline(inp, "te", 144) and "door.wgh_stop" in oline(inp, "te", 153),
       "the lift sounds are door.wgh_start / door.wgh_stop (sounds.json:94-95)")


# ---------------------------------------------------------------- V3 block

def v3_block(ck, inp, st):
    blk = lf(st.text(ABLK))
    code = code_of(blk)
    aabb_rw = [lit("AxisAlignedBB.getBoundingBox(", "newAABB(")]
    ck("V3.aabbs", ordered(code, rewrite(oline(inp, "blk", 18), aabb_rw), rewrite(oline(inp, "blk", 19), aabb_rw)), "the two bounding boxes of :18-19 (shaft 0..4, head 4..9)",
       (rewrite(oline(inp, "blk", 18), aabb_rw), rewrite(oline(inp, "blk", 19), aabb_rw)))
    ck("V3.dimensions", "publicint[]getDimensions(){" + oline(inp, "blk", 30) + "}" in code and "publicintgetOffset(){" + oline(inp, "blk", 35) + "}" in code,
       "getDimensions {8, 0, 0, 0, 0, 0} (:30) and offset 0 (:35)")
    inv = ".inventory()" if oline(inp, "blk", 25).endswith("().inventory();") else ""
    ck("V3.block-entity", body(blk, "public BlockEntity newBlockEntity(BlockPos pos, BlockState state)")
       == f"returnstate.getValue(TYPE)==DummyBlockType.CORE?newRBMKAutoloaderBlockEntity(pos,state):newProxyComboBlockEntity(pos,state){inv};" and inv,
       "the core gets the block entity, every other block an inventory-only proxy (:23-26)", body(blk, "public BlockEntity newBlockEntity(BlockPos pos, BlockState state)"))
    ck("V3.ticker", body(blk, "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type)")
       == "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};",
       "the core ticks on both sides (updateEntity has the client branch), proxies do not")
    ck("V3.open", "standardOpenBehavior" in oline(inp, "blk", 40) and body(blk, "protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit)")
       == "returnthis.standardOpenBehavior(level,pos,player);", "use opens the menu through standardOpenBehavior (:39-41)")
    hard, res = re.search(r"setHardness\(([\d.]+)\)\.setResistance\(([\d.]+)\)", oline(inp, "mb", 2142)).groups()
    nb = code_of(st.text(NB))
    want = (f'RBMK_AUTOLOADER=register("rbmk_autoloader",()->newRBMKAutoloaderBlock(BlockBehaviour.Properties.of().noOcclusion().strength({hard},{res})'
            ".sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops()));")
    ck("V3.strength", want in nb, f"NtmBlocks: hardness {hard}, resistance {res} (ModBlocks.java:2142), metal, no occlusion", want)


# ---------------------------------------------------------------- V4 menu and screen

def v4_menu_screen(ck, inp, st):
    menu = lf(st.text(AMENU))
    mc = code_of(menu)
    slot_rw = [lit("(loader,", "(be,"), lit("(invPlayer,", "(inventory,")]
    frags = [rewrite(oline(inp, "con", n), slot_rw) for n in (18, 19, 20)]
    ck("V4.slots", ordered(mc, *frags), "input 0-8 at (17, 18), take-only output 9-17 at (107, 18), player inventory at (8, 100) in this order (:18-20)", frags)
    split = re.search(r"index<=(\d+)", oline(inp, "con", 32))[1]
    to_player = re.search(r"mergeItemStack\(stack,(\d+),this\.inventorySlots\.size\(\),(true|false)\)", oline(inp, "con", 33)).groups()
    to_input = re.search(r"mergeItemStack\(stack,(\d+),(\d+),(true|false)\)", oline(inp, "con", 37)).groups()
    want = (f"if(index<={split}){{if(!this.moveItemStackTo(stack,{to_player[0]},this.slots.size(),{to_player[1]}))returnItemStack.EMPTY;}}"
            f"elseif(!this.moveItemStackTo(stack,{to_input[0]},{to_input[1]},{to_input[2]})){{returnItemStack.EMPTY;}}")
    qm = body(menu, "public ItemStack quickMoveStack(Player player, int index)")
    ck("V4.quick-move", want in qm and "if(stack.isEmpty()){slot.setByPlayer(ItemStack.EMPTY);}else{slot.setChanged();}" in qm,
       f"quickMoveStack: index <= {split} to the player ({to_player[0]}.. reversed), the player into {to_input[0]}..{to_input[1]} only (:23-48)", (want, qm))
    scr = lf(st.text(ASCREEN))
    sc = code_of(scr)
    tex = re.search(r'":(textures/[^"]+)"', oline(inp, "gui", 20))[1]
    w = re.search(r"xSize=(\d+);", oline(inp, "gui", 27))[1]
    h = re.search(r"ySize=(\d+);", oline(inp, "gui", 28))[1]
    btn_rw = [lit("guiLeft", "leftPos"), lit("guiTop", "topPos")]
    minus, plus = rewrite(oline(inp, "gui", 40), btn_rw), rewrite(oline(inp, "gui", 47), btn_rw)
    key = lambda n: re.search(r'setBoolean\("(\w+)",true\)', oline(inp, "gui", n))[1]  # noqa: E731
    send = "PacketDistributor.sendToServer(newCompoundTagControl(data,be.getBlockPos()));"
    ck("V4.buttons", ordered(sc, minus, f'data.putBoolean("{key(43)}",true);{send}', plus, f'data.putBoolean("{key(50)}",true);{send}'),
       "minus at (74, 36) and plus at (90, 36), 12 x 12 with the original's inclusive / exclusive bounds (:40, :47), keys sent through CompoundTagControl", (minus, plus))
    title_c = re.search(r",6,(0x\w+)\);", oline(inp, "gui", 59))[1]
    inv_c = re.search(r",(\d+)\);", oline(inp, "gui", 60))[1]
    pct_y, pct_c = re.search(r",(\d+),(0x\w+)\);", oline(inp, "gui", 63)).groups()
    contains_all(ck, "V4.screen", f"texture {tex} (:20), {w} x {h} (:27-28), labels: title centred at 6 in {title_c}, inventory at (8, ySize - 96 + 2), cycle % centred at {pct_y} in {pct_c} (:59-63), background blit (:70)", sc,
                 f'NuclearTechMod.withDefaultNamespace("{tex}")', f"this.imageWidth={w};", f"this.imageHeight={h};",
                 f"this.imageWidth/2-this.font.width(this.title)/2,6,{title_c},false", f"this.playerInventoryTitle,8,this.imageHeight-96+2,{inv_c},false",
                 'Stringpercent=be.cycle+"%";', f"percent,this.imageWidth/2-this.font.width(percent)/2,{pct_y},{pct_c},false",
                 "guiGraphics.blit(TEXTURE,this.leftPos,this.topPos,0,0,this.imageWidth,this.imageHeight);")


# ---------------------------------------------------------------- V5 renderer and ResourceManager

def v5_renderer(ck, inp, st):
    rend = lf(st.text(AREND))
    rb = body(rend, "public void render(RBMKAutoloaderBlockEntity be, MultiBufferSource buffer, float partialTicks)")
    down = re.search(r"glTranslated\(0,p\*(-?[\d.]+),0\);", oline(inp, "rend", 29))[1]
    up = re.search(r"glTranslated\(0,([\d.]+),0\);", oline(inp, "rend", 31))[1]
    frags = ["RenderContext.translate(0.5,0,0.5);", "bindTexture(ResourceManager.RBMK_AUTOLOADER_TEX);", 'ResourceManager.rbmk_autoloader.renderPart("Base");',
             "doublep=be.lastPiston+(be.renderPiston-be.lastPiston)*partialTicks;", f"RenderContext.translate(0,(float)(p*{down}),0);", f"RenderContext.translate(0,{up},0);",
             'ResourceManager.rbmk_autoloader.renderPart("Piston");']
    miss = missing_order(rb, *frags)
    ck("V5.render", miss is None and "mulPose" not in rb and rb.endswith('renderPart("Piston");'), f"render: centre, Base, p * {down} then +{up}, Piston, no rotation (:18-36)", (miss, rb))
    tx = re.search(r"glTranslated\(0,(-?[\d.]+),0\);", oline(inp, "rend", 47))[1]
    sc = re.search(r"glScaled\(([\d.]+),([\d.]+),([\d.]+)\);", oline(inp, "rend", 48)).groups()
    rot = re.search(r"glRotated\((\d+),0,1,0\);", oline(inp, "rend", 51))[1]
    inv = body(rend, "public void renderInventory(ItemStack stack, MultiBufferSource buffer)")
    com = body(rend, "public void renderCommon(ItemStack stack, MultiBufferSource buffer)")
    ck("V5.item", inv == f"RenderContext.translate(0,{tx},0);RenderContext.scale({sc[0]},{sc[1]},{sc[2]});"
       and ordered(com, f"RenderContext.mulPose(Axis.YP.rotationDegrees({rot}));", "RenderSystem.disableCull();", 'renderPart("Base");', 'renderPart("Piston");', "RenderSystem.enableCull();"),
       f"item: inventory translate (0, {tx}, 0) and scale {sc[0]} (:47-48), common rotate {rot} about Y, Base and Piston without culling (:50-59)", (inv, com))
    ck("V5.render-box", body(rend, "public AABB getRenderBoundingBox(RBMKAutoloaderBlockEntity be)") == "returnbe.getRenderBoundingBox();", "the BER uses the block entity's y..y+9 box")
    ck("V5.item-target", "returnNtmBlocks.RBMK_AUTOLOADER.asItem();" in body(rend, "public Item getItemForRenderer()"), "the item renderer is bound to rbmk_autoloader")
    rm = code_of(st.text(RM))
    tex = re.search(r'"(textures/[^"]+)"', oline(inp, "rm", 1693))[1]
    obj = re.search(r'"models/(rbmk/[^"]+)"', oline(inp, "rm", 1682))[1]
    smooth = ".noSmooth()" not in oline(inp, "rm", 1682)
    want = [f'RBMK_AUTOLOADER_TEX=NuclearTechMod.withDefaultNamespace("{tex}");', f'rbmk_autoloader=newHFRWavefrontObject("models/obj/{obj}"){"" if smooth else ".noSmooth()"}.asVBO();']
    contains_all(ck, "V5.resource-manager", f"ResourceManager: {tex} (:1693) and models/obj/{obj} as VBO, smoothed as the original (:1682)", rm, *want)
    for path, label in ((RM, "ResourceManager"), (AMR, "AssemblyMachineRecipes")):
        start = lf(inp.start[path]).split("\n")
        now = lf(st.text(path)).split("\n")
        removed = [l for l in difflib.ndiff(start, now) if l.startswith("- ")]
        ck(f"V5.only-added-{label}", not removed, f"{label}.java: lines only added against the start copy", removed[:3])


# ---------------------------------------------------------------- V6 registrations, datagen, recipe

def v6_registration(ck, inp, st):
    counts = {"NtmBlocks": code_of(st.text(NB)).count('register("rbmk_autoloader",'), "NtmBlockEntityTypes": code_of(st.text(BET)).count('BLOCK_ENTITY_TYPES.register("rbmk_autoloader",'),
              "NtmMenuTypes": code_of(st.text(MT)).count('reg("rbmk_autoloader",RBMKAutoloaderMenu::new)'),
              "NuclearTechModClient": code_of(st.text(NMC)).count("event.register(NtmMenuTypes.RBMK_AUTOLOADER.get(),RBMKAutoloaderScreen::new);"),
              "ClientProxy": code_of(st.text(CP)).count("BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_AUTOLOADER.get(),newRenderRBMKAutoloader());"),
              "NtmCreativeTabs": code_of(st.text(CTAB)).count("output.accept(NtmBlocks.RBMK_AUTOLOADER);"),
              "loot": code_of(st.text(LOOTP)).count("this.dropSelf(NtmBlocks.RBMK_AUTOLOADER.get());"), "pickaxe": code_of(st.text(TAGP)).count("NtmBlocks.RBMK_AUTOLOADER.get(),"),
              "blockstate": code_of(st.text(BSP)).count('this.particleOnlyBlock(NtmBlocks.RBMK_AUTOLOADER,modLoc("block/rbmk/rbmk_autoloader"));')}
    ck("V6.registrations-once", all(v == 1 for v in counts.values()), "block, BE type, menu type, screen, BER, creative tab, loot, pickaxe tag and blockstate each name rbmk_autoloader once", counts)
    ck("V6.be-type", 'BLOCK_ENTITY_TYPES.register("rbmk_autoloader",()->BlockEntityType.Builder.of(RBMKAutoloaderBlockEntity::new,NtmBlocks.RBMK_AUTOLOADER.get()).build(null));' in code_of(st.text(BET)),
       "the block entity type is built for rbmk_autoloader only")
    ck("V6.generated", json.loads(st.text(G_BS)) == {"variants": {"": {"model": "hbmsntm:block/rbmk_autoloader_particle"}}}
       and json.loads(st.text(G_BM)) == {"textures": {"particle": "hbmsntm:block/rbmk/rbmk_autoloader"}}
       and json.loads(st.text(G_IM)) == {"parent": "minecraft:builtin/entity", "gui_light": "side"},
       "generated blockstate -> particle-only block model (the block icon rbmk_autoloader), item model builtin/entity (drawn by the BER)", (st.text(G_BS), st.text(G_BM), st.text(G_IM)))
    loot = json.loads(st.text(G_LOOT))
    ck("V6.loot", [e["name"] for p in loot["pools"] for e in p["entries"]] == ["hbmsntm:rbmk_autoloader"], "the loot table drops the block itself", loot)
    ck("V6.pickaxe", json.loads(st.text(PICK))["values"].count("hbmsntm:rbmk_autoloader") == 1, "mineable/pickaxe lists rbmk_autoloader once")
    row = olines(inp, "amr", 532, 533)
    setup = re.search(r'newGenericRecipe\("([\w.]+)"\)\.(setup|setupNamed)\((\d+),(\d+)\)', row)
    out = re.search(r"\.outputItems\(newItemStack\(ModBlocks\.rbmk_autoloader,(\d+)\)\)", row)
    ins = re.findall(r"(newOreDictStack\([\w.]+\(\),|newComparableStack\(ModItems\.\w+,)(\d+)\)", row)
    want = (f'this.register(newGenericRecipe("{setup[1]}").{setup[2]}({setup[3]},{setup[4]}).outputItems(newItemStack(NtmBlocks.RBMK_AUTOLOADER.get(),{out[1]}))'
            ".inputItems(" + ",".join(RECIPE_ITEMS[k] + n + ")" for k, n in ins) + "));")
    amr = code_of(st.text(AMR))
    ck("V6.recipe", want in amr and amr.count('"ass.rbmkautoloader"') == 1 and len(ins) == 4,
       f"{setup[1]}: {setup[2]}({setup[3]}, {setup[4]}), {out[1]} rbmk_autoloader, inputs " + ", ".join(f"{k}{n}" for k, n in ins) + " (AssemblyMachineRecipes.java:532-533)", want)


# ---------------------------------------------------------------- V7 language

def v7_lang(ck, inp, st):
    en, dup_en = json_pairs(st.text(EN))
    s_en = json.loads(inp.start[EN])
    lp = st.text(LP)
    want_en = {k: inp.o_en[ok][0][0] for k, ok, _, _ in UP}
    bad = {k: en.get(k) for k, v in want_en.items() if en.get(k) != v or k in s_en}
    ck("V7.en-new", not bad and f'this.add(NtmBlocks.RBMK_AUTOLOADER, "{want_en["block.hbmsntm.rbmk_autoloader"]}");' in lp
       and f'this.add("container.rbmkAutoloader", "{want_en["container.rbmkAutoloader"]}");' in lp,
       "the two English keys are in NtmLanguageProvider and en_us.json with the original text (en_US.lang:6212, 788)", bad)
    ck("V7.en-rest", {k: v for k, v in en.items() if k not in want_en} == s_en and not dup_en, "en_us.json: nothing but the two keys changed")
    zh, dup_zh = json_pairs(st.text(ZH))
    s_zh = json.loads(inp.start[ZH])
    if not all(k in zh for k in NEW_KEYS):
        ck.pending("V7.zh-pending", "zh_cn.json does not yet carry the Goal25C keys: pending, not passed", [k for k in NEW_KEYS if k not in zh])
    else:
        want_zh = {k: inp.o_zh[ok][0][0] for k, ok, _, _ in UP}
        bad = {k: zh.get(k) for k, v in want_zh.items() if zh.get(k) != v}
        ck("V7.zh-new", not bad, "zh_cn.json has the two entries verbatim from zh_CN.lang:5920, 5911", bad)
        ck("V7.zh-rest", {k: v for k, v in zh.items() if k not in want_zh} == s_zh and not dup_zh and all(k not in s_zh for k in want_zh), "zh_cn.json: nothing else changed")
    mp = json.loads(st.text(MAP))
    s_mp = json.loads(inp.start[MAP])
    ent, sent = mp["entries"], s_mp["entries"]
    if not all(k in ent for k in NEW_KEYS):
        ck.pending("V7.map-pending", "zh_cn-map.json does not yet carry the Goal25C entries: pending, not passed", [k for k in NEW_KEYS if k not in ent])
    else:
        bad = {}
        for k, ok, _, _ in UP:
            e = ent.get(k, {})
            if not (e.get("kind") == "upstream" and e.get("source_key") == ok and e.get("source_en") == inp.o_en[ok][0][0] and e.get("source_zh") == inp.o_zh[ok][0][0]
                    and e.get("target_en") == en.get(k) and e.get("target_zh") == zh.get(k) and placeholders(e.get("source_en", "")) == placeholders(e.get("target_zh", ""))):
                bad[k] = e
        ck("V7.map-entries", not bad, "zh_cn-map.json: 2 upstream entries with the original en/zh text at the cited lines", bad)
        ck("V7.map-rest", {k: v for k, v in ent.items() if k not in NEW_KEYS} == sent and {k: v for k, v in mp.items() if k != "entries"} == {k: v for k, v in s_mp.items() if k != "entries"}
           and len(ent) == len(sent) + 2, "zh_cn-map.json: nothing else changed (2 new entries)", (len(ent), len(sent)))
    eol = []
    for p in (ZH, MAP, EN):
        s_crlf = "\r\n" in inp.start[p]
        data = st.files[p]
        if s_crlf != (b"\r\n" in data) or (s_crlf and data.count(b"\r\n") != data.count(b"\n")):
            eol.append(p)
    ck("V7.eol", not eol, "zh_cn.json, zh_cn-map.json and en_us.json keep the start copy's line-ending style", eol)


# ---------------------------------------------------------------- V8 resources

def v8_resources(ck, inp, st):
    bad = [p for p in IMPORT_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V8.byte-equal", not bad and len(IMPORT_PATHS) == 4, "the OBJ, the model texture, the block icon and the GUI are byte-equal (SHA-256) to the original working tree", bad)
    if not st.has(OWN):
        ck.pending("V8.ownership-pending", "migration/goal25c-resource-ownership.json is absent: pending, not passed")
        return
    own = json.loads(st.text(OWN))
    rows = {a["target_path"]: a for a in own.get("assets", [])}
    wrong = [p for p in IMPORT_PATHS if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None)
             or rows[p].get("source_path") != O_RES + IMPORTS[IMPORT_PATHS.index(p)][0]]
    ck("V8.ownership", not wrong and len(rows) == 4 and own.get("source_commit") == ORIGINAL_HEAD, "the ownership record lists the four imports with their source paths and hashes", wrong)


# ---------------------------------------------------------------- V9 scope

RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/GOAL25.md", "migration/GOAL25C.md",
                 "migration/GOAL25C-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal25c-",)


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v9_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_CLASSES + EDITED + [EN, STAMP, PICK, GT] + IMPORT_PATHS + GEN_NEW)
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V9.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, imports, the GameTest, the records)", extra[:10])
    ck("V9.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed]
    ck("V9.expected-all-changed", not never, "every expected production, resource, generated and GameTest path differs from the start", never[:5])
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    ck("V9.gen-new", sorted(gen_new) == sorted(GEN_NEW), "exactly the four new generated files appeared", sorted(set(gen_new) ^ set(GEN_NEW)))
    ck("V9.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + [GT] + IMPORT_PATHS) and all(p in inp.base_files for p in EDITED),
       "the new classes, the GameTest and the imports did not exist at the start; the edited files did")
    ck("V9.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED), "the RBMK base, rod, proxy, menu base, control packet, rod item, sound, particle and older GameTest files are byte-equal to the start",
       [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    eol = [p for p in EDITED if p in inp.start and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V9.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V9.records", True, "records changed (allowed, not required): " + ", ".join(rest))
    ck("V9.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V10 / V11

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*(?:@SuppressWarnings\([^)]*\)\s*)?public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v10_gametest(ck, inp, st):
    ck("V10.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", other_gametests())
    ck("V10.present", st.has(GT), "RBMKAutoloaderGameTests.java exists")
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
    ck("V10.areas", sorted(tests) == sorted(GT_AREAS), "the tests are " + ", ".join(GT_AREAS), sorted(set(tests) ^ set(GT_AREAS)))
    ck("V10.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKAutoloaderGameTests references no client class")
    ck("V10.original-constants", "ORIGINAL_SPEED = 0.005D;" in live and "ORIGINAL_DELAY = 40;" in live and "ORIGINAL_CYCLE = 50;" in live,
       "the GameTest's expected constants are the original's (speed 0.005, delay 40, cycle 50), not read from the NEO class")
    return dict(tests=sorted(tests))


def original_stroke(extend):
    """The original :59-65 / :84-90 in IEEE doubles: the number of updates of one stroke."""
    p, n = (0.0, 0) if extend else (1.0, 0)
    while True:
        n += 1
        if extend:
            p += 0.005
            if p >= 1:
                return n
        else:
            p -= 0.005
            if p <= 0:
                return n


def v10_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    total = other_gametests() + gametest_total([live])
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V10.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({other_gametests()} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V10.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V10.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V10.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    facts = {}
    m = re.search(re.escape(GT_MARK) + r" swap cycle ticks: start (\d+) full\+swap (\d+) first retraction (\d+) piston 0 (\d+) \(extend (\d+) updates, hold (\d+), retract (\d+) updates\)", text)
    ins = re.search(re.escape(GT_MARK) + r" swap cycle: rod inserted at game time (\d+), extension started at (\d+)", text)
    ext, ret = original_stroke(True), original_stroke(False)
    if m and ins:
        s, w, d, z, e, hold, r = (int(x) for x in m.groups())
        facts["ticks"] = dict(logged=m[0], inserted=int(ins[1]), extend_updates=ext, retract_updates=ret)
        ck("V10.ticks", s % 20 == 0 and s == (int(ins[1]) // 20 + 1) * 20 and w - s + 1 == ext == e and d - w == 40 == hold and z - d + 1 == ret == r,
           f"the logged ticks re-derive from the original: start on the first time % 20 == 0 after the insert, swap {ext} updates later (0.005 replayed in doubles), "
           f"hold 40, retract {ret} updates", (s, w, d, z, e, hold, r, ext, ret))
    else:
        ck("V10.ticks", False, "the swap cycle tick lines are missing from the log")
    ns = re.findall(re.escape(GT_MARK) + r" no swap (\w+): (retracted for 70 ticks \((\d+) checks\)|started at game time (\d+))", text)
    seen = {n[0]: n for n in ns}
    stays = ["CHANNEL_051", "CHANNEL_050", "HULL_1001", "OUTPUT_FULL", "INPUT_040", "INPUT_STICK", "BLANK_BELOW", "STONE_BELOW"]
    starts = ["HULL_1000", "EMPTY_CHANNEL", "CHANNEL_REMOVED"]
    ok = all(c in seen and seen[c][1].startswith("retracted") and int(seen[c][2]) >= 3 for c in stays) and all(c in seen and seen[c][3] and int(seen[c][3]) % 20 == 0 for c in starts)
    ck("V10.no-swap", ok, "every no-swap case logged: 8 stay retracted over >= 3 checks, hull 1000 / empty channel / removed channel start on a time % 20 == 0", sorted(seen))
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()), **facts)


def v11_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    gen = GEN_NEW + [EN, PICK]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        ck("V11.classes", not missing, "the JAR has the 5 new production classes and RBMKAutoloaderGameTests", missing)
        bad = [p for p in IMPORT_PATHS if p[len("src/main/resources/"):] not in names or jar.read(p[len("src/main/resources/"):]) != st.files.get(p)]
        ck("V11.resources", not bad, "the four imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V11.generated", not gbad, "the generated blockstate, models, loot, en_us.json and the pickaxe tag in the JAR are byte-equal to the tree", gbad[:5])
        ck("V11.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_block_entity, inp, st)
    guarded(ck, "V3", v3_block, inp, st)
    guarded(ck, "V4", v4_menu_screen, inp, st)
    guarded(ck, "V5", v5_renderer, inp, st)
    guarded(ck, "V6", v6_registration, inp, st)
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
        ("speed_0005_to_001", "V2.", t(ABE, "SPEED = 0.005D;", "SPEED = 0.01D;")),
        ("delay_40_to_20", "V2.", t(ABE, "this.piston = 0;\n                    this.delay = 40;", "this.piston = 0;\n                    this.delay = 20;")),
        ("lt_cycle_to_le", "V2.", t(ABE, "RBMKRodItem.getEnrichment(loaded) * 100 < cycle", "RBMKRodItem.getEnrichment(loaded) * 100 <= cycle")),
        ("ge_cycle_to_gt", "V2.", t(ABE, "if(!stack.isEmpty() && stack.getItem() instanceof RBMKRodItem && RBMKRodItem.getEnrichment(stack) * 100 >= cycle) {\n                                rod.slots.set(0",
                                     "if(!stack.isEmpty() && stack.getItem() instanceof RBMKRodItem && RBMKRodItem.getEnrichment(stack) * 100 > cycle) {\n                                rod.slots.set(0")),
        ("null_guard_removed", "V2.", t(ABE, "if(core != null && this.level.getBlockEntity(core)", "if(this.level.getBlockEntity(core)")),
        ("check_mod_20_to_10", "V2.", t(ABE, "this.level.getGameTime() % 20 == 0", "this.level.getGameTime() % 10 == 0")),
        ("output_loop_9_to_8", "V2.", t(ABE, "for(int i = 9; i < 18; i++) {\n                            if(slots.get(i).isEmpty()) {", "for(int i = 8; i < 18; i++) {\n                            if(slots.get(i).isEmpty()) {")),
        ("slots_for_face_le_to_lt", "V2.", t(ABE, "return this.piston <= 0 ? SLOTS : NO_SLOTS;", "return this.piston < 0 ? SLOTS : NO_SLOTS;")),
        ("can_take_ge9_to_gt9", "V2.", t(ABE, "return i >= 9;", "return i > 9;")),
        ("control_clamp_95_to_100", "V2.", t(ABE, "this.cycle = Mth.clamp(this.cycle, 5, 95);", "this.cycle = Mth.clamp(this.cycle, 5, 100);")),
        ("paste_clamp_5_to_0", "V2.", t(ABE, 'Mth.clamp(nbt.getInt("cycle"), 5, 95)', 'Mth.clamp(nbt.getInt("cycle"), 0, 95)')),
        ("nbt_key_ret_renamed", "V2.", t(ABE, 'tag.putBoolean("ret", this.isRetracting);', 'tag.putBoolean("retracting", this.isRetracting);')),
        ("sync_order_swapped", "V2.", t(ABE, "buf.writeDouble(this.piston);\n        buf.writeInt(this.cycle);", "buf.writeInt(this.cycle);\n        buf.writeDouble(this.piston);")),
        ("turn_progress_3", "V2.", t(ABE, "this.turnProgress = 2;", "this.turnProgress = 3;")),
        ("range_12_to_16", "V2.", t(ABE, "<= 12D * 12D", "<= 16D * 16D")),
        ("swap_set_changed_dropped", "V2.", T(ABE, lambda x: drop_line(x, "                    rod.setChanged();"))),
        ("sound_volume_075_to_1", "V2.", t(ABE, "this, this.getVolume(0.75F), 25F, 1.0F, 5);", "this, this.getVolume(1F), 25F, 1.0F, 5);")),
        ("particle_life_30_to_20", "V2.", t(ABE, "70 + this.level.random.nextInt(30)", "70 + this.level.random.nextInt(20)")),
        ("render_box_9_to_8", "V2.", t(ABE, "pos.getY() + 9", "pos.getY() + 8")),
        ("aabb_height_9_to_8", "V3.", t(ABLK, "new AABB(-0.5, 4, -0.5, 0.5, 9, 0.5)", "new AABB(-0.5, 4, -0.5, 0.5, 8, 0.5)")),
        ("dimensions_8_to_7", "V3.", t(ABLK, "new int[] {8, 0, 0, 0, 0, 0}", "new int[] {7, 0, 0, 0, 0, 0}")),
        ("proxy_without_inventory", "V3.", t(ABLK, "new ProxyComboBlockEntity(pos, state).inventory();", "new ProxyComboBlockEntity(pos, state);")),
        ("ticker_server_only", "V3.", t(ABLK, "if(state.getValue(TYPE) != DummyBlockType.CORE) return null;", "if(state.getValue(TYPE) != DummyBlockType.CORE || level.isClientSide) return null;")),
        ("strength_50_to_3", "V3.", t(NB, "new RBMKAutoloaderBlock(BlockBehaviour.Properties.of().noOcclusion().strength(50.0F, 60.0F)", "new RBMKAutoloaderBlock(BlockBehaviour.Properties.of().noOcclusion().strength(3.0F, 60.0F)")),
        ("menu_output_x_108", "V4.", t(AMENU, "this.addTakeOnlySlots(be, 9, 107, 18, 3, 3);", "this.addTakeOnlySlots(be, 9, 108, 18, 3, 3);")),
        ("menu_output_placeable", "V4.", t(AMENU, "this.addTakeOnlySlots(be, 9, 107, 18, 3, 3);", "this.addSlots(be, 9, 107, 18, 3, 3);")),
        ("quick_move_into_outputs", "V4.", t(AMENU, "!this.moveItemStackTo(stack, 0, 9, false)", "!this.moveItemStackTo(stack, 0, 18, false)")),
        ("screen_button_inclusive_right", "V4.", t(ASCREEN, "leftPos + 74 + 12 > x", "leftPos + 74 + 12 >= x")),
        ("screen_height_186", "V4.", t(ASCREEN, "this.imageHeight = 182;", "this.imageHeight = 186;")),
        ("piston_plus4_removed", "V5.", T(AREND, lambda x: drop_line(x, "RenderContext.translate(0F, 4F, 0F);"))),
        ("item_scale_175_to_2", "V5.", t(AREND, "RenderContext.scale(1.75F, 1.75F, 1.75F);", "RenderContext.scale(2F, 2F, 2F);")),
        ("render_rotation_added", "V5.", t(AREND, "RenderContext.translate(0.5F, 0F, 0.5F);", "RenderContext.translate(0.5F, 0F, 0.5F);\n        RenderContext.mulPose(Axis.YP.rotationDegrees(90F));")),
        ("obj_nosmooth", "V5.", t(RM, 'new HFRWavefrontObject("models/obj/rbmk/autoloader.obj").asVBO();', 'new HFRWavefrontObject("models/obj/rbmk/autoloader.obj").noSmooth().asVBO();')),
        ("recipe_count_4_to_3", "V6.", t(AMR, "NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD, 4),\n                        new ComparableStack(NtmItems.INGOT_BORON.get(), 4)",
                                         "NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD, 3),\n                        new ComparableStack(NtmItems.INGOT_BORON.get(), 4)")),
        ("recipe_setup_named", "V6.", t(AMR, 'new GenericRecipe("ass.rbmkautoloader").setup(100, 100)', 'new GenericRecipe("ass.rbmkautoloader").setupNamed(100, 100)')),
        ("recipe_motor_to_boron", "V6.", t(AMR, "new ComparableStack(NtmItems.INGOT_BORON.get(), 4),\n                        new ComparableStack(NtmItems.MOTOR.get(), 3)",
                                           "new ComparableStack(NtmItems.INGOT_BORON.get(), 4),\n                        new ComparableStack(NtmItems.INGOT_BORON.get(), 3)")),
        ("creative_tab_twice", "V6.", T(CTAB, lambda x: rep1(x, "output.accept(NtmBlocks.RBMK_AUTOLOADER);", "output.accept(NtmBlocks.RBMK_AUTOLOADER);\n                        output.accept(NtmBlocks.RBMK_AUTOLOADER);"))),
        ("ber_removed", "V6.", T(CP, lambda x: drop_line(x, "NtmBlockEntityTypes.RBMK_AUTOLOADER.get(), new RenderRBMKAutoloader()"))),
        ("item_model_cube", "V6.", gen_edit(G_IM, lambda d: d.__setitem__("parent", "hbmsntm:block/rbmk_autoloader_particle"))),
        ("en_value_changed", "V7.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("container.rbmkAutoloader", "RBMK Auto Loader")))),
        ("en_other_key_changed", "V7.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("block.hbmsntm.rbmk_blank", "X")))),
        ("zh_value_changed", "V7.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("block.hbmsntm.rbmk_autoloader", "RBMK自动装填机")))),
        ("map_source_zh_changed", "V7.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["container.rbmkAutoloader"].__setitem__("source_zh", "X")))),
        ("resource_byte_flip", "V8.", Bx(IMPORT_PATHS[1], flip_byte)),
        ("gui_byte_flip", "V8.", Bx(IMPORT_PATHS[3], flip_byte)),
        ("unrelated_src_file", "V9.", lambda st: st.set_bytes(J + "items/Stray.java", b"class Stray {}")),
        ("rod_file_touched", "V9.", T(J + "blockentity/machine/rbmk/RBMKRodBlockEntity.java", lambda x: x + "\n")),
        ("orig_speed_line", "V1.|V2.", OE("te", lambda x: rep1(x, "public static double speed = 0.005D;", "public static double speed = 0.01D;"))),
        ("orig_delay_line", "V1.|V2.", OE("te", lambda x: rep1(x, "\t\t\t\t\tthis.piston = 0;\n\t\t\t\t\tthis.delay = 40;", "\t\t\t\t\tthis.piston = 0;\n\t\t\t\t\tthis.delay = 60;"))),
        ("orig_line_moved", "V1.", OE("te", lambda x: rep1(x, "\tpublic static double speed = 0.005D;", "\n\tpublic static double speed = 0.005D;"))),
        ("orig_gui_height", "V1.|V4.", OE("gui", lambda x: rep1(x, "this.ySize = 182;", "this.ySize = 186;"))),
        ("orig_recipe_count", "V1.|V6.", OE("amr", lambda x: rep1(x, "new OreDictStack(B.ingot(), 4), new ComparableStack(ModItems.motor, 3))", "new OreDictStack(B.ingot(), 4), new ComparableStack(ModItems.motor, 2))"))),
        ("gt_marker_changed", "V10.", t(GT, 'TAG = "[hbm-rbmk-autoloader]"', 'TAG = "[hbm-rbmk]"'), GT),
        ("gt_batch_shared", "V10.", t(GT, 'batch = "rbmk_autoloader_slots"', 'batch = "rbmk_autoloader_control"'), GT),
        ("gt_speed_from_neo", "V10.", t(GT, "ORIGINAL_SPEED = 0.005D;", "ORIGINAL_SPEED = RBMKAutoloaderBlockEntity.SPEED;"), GT),
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
        ck = static_suite(inp2, mutated)
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
    out.setdefault("V11", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V11" and not items:
            result[sec] = dict(status="not run", checks=0, passed=0, failed=[], pending=[])
            continue
        failed = [i["id"] for i in items if i["status"] == "FAIL"]
        pending = [i["id"] for i in items if i["status"] == "PENDING"]
        status = "FAIL" if failed else "PENDING" if pending else "PASS"
        result[sec] = dict(status=status, checks=len(items), passed=sum(1 for i in items if i["status"] == "PASS"), failed=failed, pending=pending)
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
        extra["gametest_log"] = guarded(ck, "V10", v10_log, inp, st, args.gametest_log)
    else:
        ck.pending("V10.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
    if args.jar:
        extra["jar"] = guarded(ck, "V11", v11_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V12"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    production = NEW_CLASSES + EDITED + [ZH, EN, STAMP, MAP, OWN, GT]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), checks_pending=ck.pendings(), mutations_detected=len(applied) - len(undetected),
                     mutations_applied=len(applied), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), pending=ck.pendings(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.tree.get(p) for p in dict.fromkeys(production)},
        tools_status=inp.tools_status,
        start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    report["pass"] = report.pop("pass_")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] != "PASS":
            print(f"{item['status']} {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        if value.get("detected") is None:
            print(f"SKIPPED  mutation {label}: {value.get('skipped')}")
            continue
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label} (expect {value['expected_section']}): {value['failed'][:4]}"
              + (f" crashes={value['crashes']}" if value["crashes"] else "") + (f" {value['error']}" if value.get("error") else ""))
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed, {len(ck.pendings())} pending; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
