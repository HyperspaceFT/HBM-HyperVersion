"""Verify the Goal25D batch statically: the RBMK crane console (rbmk_crane_console: RBMKCraneConsoleBlock, RBMKCraneConsoleBlockEntity,
RenderCraneConsole), the craneIndicator of RBMKBaseBlockEntity and the console indicator, the rbmk_tool crane branch, the five crane
KeyMappings and the proxy key reading, registrations, datagen, the language entries, the imported resources and the GameTest source; with
--gametest-log the GameTest log and its logged tick numbers.

Read-only for both worktrees. Writes only build/migration/goal25d/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal25d/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (crane tile entity, crane block, RBMK base, console, tool, keybinds, client proxy, crafting row, resource manager,
      renderer, item renderer, ModBlocks, language) parsed at the cited lines; a moved or changed line fails.
- V2  Block entity against V1: speed, the 0.04 lift, the load / unload branch, the box, the key branch (first player, not loading, truth
      tables, tilt 30), the clamps, heat / enrichment, networkPackNT(250), sync order, NBT keys, setTarget (+1, +6, max 16, height 7,
      rotation chain), findRoomExtent, cycle +90 % 360, the getColumnAtPos formula and the NEO guards, infinite render box.
- V3  Block: dimensions, offset, the second box in checkRequirement and fillSpace, core-only ticker on both sides, screwdriver, no menu,
      strength 3 / 30.
- V4  RBMK base, console, tool: craneIndicator field, decrement at the start of the server update, the byte after heat, no NBT key; the
      console indicator; the rbmk_tool crane branch with the position check, the null-checked core and ".set".
- V5  Keybinds: five KeyMappings (ids, GLFW defaults, category), registered once, getIsKeyPressed cases, no handleProps mirror line,
      HbmKeybinds otherwise equal to the start, EnumKeybind order of the start copy; ServerProxy / ClientProxy getIsKeyPressed and the
      block entity's proxy read on the client; KeybindReceiver, HbmKeybindsServer, HbmPlayerAttachments byte-equal to the start.
- V6  Renderer: part names (also present in the OBJ files), facing switch, joystick / meter / lamp / crane constants, item transforms;
      ResourceManager paths; the ClientProxy BER.
- V7  Registrations and datagen: block, BE type, creative tab after rbmk_console, BER, loot, pickaxe tag, blockstate; generated files and
      the recipe JSON against CraftingManager.java:990.
- V8  Language: six keys in the provider and en_us.json; zh_cn.json and zh_cn-map.json (pending until written); EOL kept; nothing else.
- V9  Resources: the five imports byte-equal to the original working tree and listed in migration/goal25d-resource-ownership.json.
- V10 Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed separately).
- V11 GameTest source, and with --gametest-log the log (all N passed, every test line, the logged tick numbers re-derived).
- V12 (--jar) the packaged JAR; "not run" without the flag.
- V13 In-memory mutations of the NEO inputs and of the original text (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal25d_rbmk_crane.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal25d"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "783b6d137936750a8a5ef822e1b29fd1209593f7"

J = "src/main/java/com/hbm/"
CBE = J + "blockentity/machine/rbmk/RBMKCraneConsoleBlockEntity.java"
CBLK = J + "blocks/machine/rbmk/RBMKCraneConsoleBlock.java"
CREND = J + "render/blockentity/RenderCraneConsole.java"
NEW_CLASSES = [CBLK, CBE, CREND]
BASE = J + "blockentity/machine/rbmk/RBMKBaseBlockEntity.java"
CONS = J + "blockentity/machine/rbmk/RBMKConsoleBlockEntity.java"
LOADABLE = J + "blockentity/machine/rbmk/IRBMKLoadable.java"
SLOTTED = J + "blockentity/machine/rbmk/RBMKSlottedBaseBlockEntity.java"
STORAGE = J + "blockentity/machine/rbmk/RBMKStorageBlockEntity.java"
TOOL = J + "items/tools/RBMKToolItem.java"
KB = J + "handler/HbmKeybinds.java"
RM = J + "main/ResourceManager.java"
CP = J + "main/ClientProxy.java"
SP = J + "main/ServerProxy.java"
NB = J + "blocks/NtmBlocks.java"
BET = J + "blockentity/NtmBlockEntityTypes.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
RECP = J + "datagen/NtmRecipeProvider.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
LOOTP = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
EDITED = [BASE, CONS, LOADABLE, SLOTTED, STORAGE, TOOL, KB, RM, CP, SP, NB, BET, CTAB, RECP, BSP, LOOTP, TAGP, LP]
COMMENT_ONLY = [LOADABLE, SLOTTED, STORAGE]
KBS = J + "handler/HbmKeybindsServer.java"
KR = J + "network/toserver/KeybindReceiver.java"
ATT = J + "extprop/HbmPlayerAttachments.java"
CHAIN = [KBS, KR, ATT]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal25d-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
G_BS = GEN + "assets/hbmsntm/blockstates/rbmk_crane_console.json"
G_BM = GEN + "assets/hbmsntm/models/block/rbmk_crane_console_particle.json"
G_IM = GEN + "assets/hbmsntm/models/item/rbmk_crane_console.json"
G_ADV = GEN + "data/hbmsntm/advancement/recipes/misc/rbmk_crane_console.json"
G_LOOT = GEN + "data/hbmsntm/loot_table/blocks/rbmk_crane_console.json"
G_REC = GEN + "data/hbmsntm/recipe/rbmk_crane_console.json"
GEN_NEW = [G_BS, G_BM, G_IM, G_ADV, G_LOOT, G_REC]
RES = "src/main/resources/assets/hbmsntm/"
GT = J + "gametest/RBMKCraneGameTests.java"
GT_DIR = J + "gametest/"

# files the batch must only read, never change (byte-equal to the start; hashes from baseline.json)
UNTOUCHED = CHAIN + [J + "blockentity/machine/rbmk/" + n for n in ("RBMKRodBlockEntity.java", "RBMKDials.java", "RBMKAutoloaderBlockEntity.java", "RBMKBlankBlockEntity.java")] + [
    J + "blocks/machine/rbmk/RBMKBaseBlock.java", J + "blocks/DummyableBlock.java", J + "handler/MultiblockHandlerXR.java", J + "items/machine/RBMKRodItem.java",
    J + "blockentity/LoadedBaseBlockEntity.java", J + "render/blockentity/RenderRBMKConsole.java", J + "inventory/screens/RBMKConsoleScreen.java",
    J + "main/NuclearTechMod.java", J + "gametest/SmokeTestSupport.java", J + "gametest/RBMKReactorGameTests.java", J + "gametest/RBMKRecyclingGameTests.java",
    J + "gametest/RBMKOutgasserGameTests.java", J + "gametest/RBMKConsoleGameTests.java", J + "gametest/RBMKAutoloaderGameTests.java"]

O = "src/main/java/com/hbm/"
O_FILES = dict(te=O + "tileentity/machine/rbmk/TileEntityCraneConsole.java", blk=O + "blocks/machine/rbmk/RBMKCraneConsole.java",
               base=O + "tileentity/machine/rbmk/TileEntityRBMKBase.java", cons=O + "tileentity/machine/rbmk/TileEntityRBMKConsole.java",
               tool=O + "items/tool/ItemRBMKTool.java", kb=O + "handler/HbmKeybinds.java", cp=O + "main/ClientProxy.java", cm=O + "main/CraftingManager.java",
               rm=O + "main/ResourceManager.java", rend=O + "render/tileentity/RenderCraneConsole.java", irl=O + "render/item/ItemRenderLibrary.java",
               mb=O + "blocks/ModBlocks.java")
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"

# V1: every cited original line, {file key: {line: needle}}
ANCHORS = {
    "te": {57: "private static final double speed = 0.05D;", 59: "private boolean goesDown = false;", 61: "public double progress = 1D;", 95: "TileEntityRBMKBase aboveColumn = this.getColumnAtPos();",
           96: "if(aboveColumn != null) aboveColumn.craneIndicator = 10;", 98: "if(goesDown) {", 100: "if(progress > 0) {", 101: "progress -= 0.04D;", 103: "progress = 0;",
           104: "goesDown = false;", 106: "if(aboveColumn instanceof IRBMKLoadable && this.canTargetInteract((IRBMKLoadable) aboveColumn)) {", 109: "if(this.loadedItem != null) {",
           110: "column.load(this.loadedItem);", 111: "this.loadedItem = null;", 113: "this.loadedItem = column.provideNext();", 114: "column.unload();", 117: "this.markDirty();",
           122: "} else if(progress != 1) {", 124: "progress += 0.04D;", 126: "if(progress > 1D) {", 127: "progress = 1D;",
           132: "ForgeDirection dir = ForgeDirection.getOrientation(this.getBlockMetadata() - BlockDummyable.offset);", 133: "ForgeDirection side = dir.getRotation(ForgeDirection.UP);",
           134: "double minX = xCoord + 0.5 - side.offsetX * 1.5;", 135: "double maxX = xCoord + 0.5 + side.offsetX * 1.5 + dir.offsetX * 2;",
           136: "double minZ = zCoord + 0.5 - side.offsetZ * 1.5;", 137: "double maxZ = zCoord + 0.5 + side.offsetZ * 1.5 + dir.offsetZ * 2;",
           139: "List<EntityPlayer> players = worldObj.getEntitiesWithinAABB(EntityPlayer.class, AxisAlignedBB.getBoundingBox(", 141: "yCoord,", 144: "yCoord + 2,",
           146: "tiltFront = 0;", 147: "tiltLeft = 0;", 149: "if(players.size() > 0 && !isCraneLoading()) {", 150: "EntityPlayer player = players.get(0);",
           152: "boolean up = props.getKeyPressed(EnumKeybind.CRANE_UP);", 153: "boolean down = props.getKeyPressed(EnumKeybind.CRANE_DOWN);",
           154: "boolean left = props.getKeyPressed(EnumKeybind.CRANE_LEFT);", 155: "boolean right = props.getKeyPressed(EnumKeybind.CRANE_RIGHT);",
           157: "if(up && !down) {", 158: "tiltFront = 30;", 159: "if(!worldObj.isRemote) posFront += speed;", 161: "if(!up && down) {", 162: "tiltFront = -30;",
           163: "if(!worldObj.isRemote) posFront -= speed;", 165: "if(left && !right) {", 166: "tiltLeft = 30;", 167: "if(!worldObj.isRemote) posLeft += speed;",
           169: "if(!left && right) {", 170: "tiltLeft = -30;", 171: "if(!worldObj.isRemote) posLeft -= speed;", 174: "if(props.getKeyPressed(EnumKeybind.CRANE_LOAD)) {",
           175: "goesDown = true;", 179: "posFront = MathHelper.clamp_double(posFront, -spanB, spanF);", 180: "posLeft = MathHelper.clamp_double(posLeft, -spanR, spanL);",
           184: "if(loadedItem != null && loadedItem.getItem() instanceof ItemRBMKRod) {", 185: "this.loadedHeat = ItemRBMKRod.getHullHeat(loadedItem);",
           186: "this.loadedEnrichment = ItemRBMKRod.getEnrichment(loadedItem);", 188: "this.loadedHeat = 0;", 189: "this.loadedEnrichment = 0;", 192: "networkPackNT(250);",
           205: "return this.progress != 1D;", 217: "if(this.hasItemLoaded()) {", 218: "return column.canLoad(loadedItem);", 220: "return column.canUnload();",
           227: "ForgeDirection left = dir.getRotation(ForgeDirection.DOWN);", 229: "int x = (int)Math.floor(this.centerX - dir.offsetX * this.posFront - left.offsetX * this.posLeft + 0.5D);",
           230: "int y = this.centerY - 1;", 231: "int z = (int)Math.floor(this.centerZ - dir.offsetZ * this.posFront - left.offsetZ * this.posLeft + 0.5D);",
           237: "int[] pos = ((BlockDummyable)b).findCore(worldObj, x, y, z);", 255: "buf.writeBoolean(this.setUpCrane);", 258: "buf.writeInt(this.craneRotationOffset);",
           272: "buf.writeDouble(this.loadedEnrichment);", 278: "this.setUpCrane = buf.readBoolean();", 294: "this.loadedEnrichment = buf.readDouble();",
           300: "this.centerY = y + RBMKDials.getColumnHeight(worldObj) + 1;", 303: "int girderY = centerY + 6;",
           305: "ForgeDirection dir = ForgeDirection.getOrientation(this.getBlockMetadata() - BlockDummyable.offset).getOpposite();",
           306: "this.spanF = this.findRoomExtent(x, girderY, z, dir, 16);", 307: "dir = dir.getRotation(ForgeDirection.UP);", 308: "this.spanR = this.findRoomExtent(x, girderY, z, dir, 16);",
           310: "this.spanB = this.findRoomExtent(x, girderY, z, dir, 16);", 312: "this.spanL = this.findRoomExtent(x, girderY, z, dir, 16);", 314: "this.height = 7;",
           316: "this.setUpCrane = true;", 322: "for (int i = 1; i < max; i++) {", 323: "if (!worldObj.isAirBlock(x + dir.offsetX * i, y, z + dir.offsetZ * i)) {",
           324: "return i - 1;", 328: "return max;", 332: "this.craneRotationOffset = (this.craneRotationOffset + 90) % 360;", 339: 'this.setUpCrane = nbt.getBoolean("crane");',
           350: 'this.posLeft = nbt.getDouble("posLeft");', 352: 'NBTTagCompound held = nbt.getCompoundTag("held");', 360: 'nbt.setBoolean("crane", setUpCrane);',
           371: 'nbt.setDouble("posLeft", posLeft);', 373: "if(this.loadedItem != null) {", 376: 'nbt.setTag("held", held);', 382: "return this.INFINITE_EXTENT_AABB;"},
    "blk": {20: "this.setHardness(3F);", 21: "this.setResistance(30F);", 27: "if(meta >= this.offset)", 34: "return new int[] {1, 0, 0, 0, 1, 1};", 39: "return 1;",
            44: "new int[] {1, 0, 0, 0, 1, 1},", 45: "new int[] {0, 0, 0, 1, 1, 1},",
            52: "MultiblockHandlerXR.fillSpace(world, x + dir.offsetX * o , y, z + dir.offsetZ * o, new int[] {0, 0, 0, 1, 1, 1}, this, dir);",
            58: "if(!MultiblockHandlerXR.checkSpace(world, x + dir.offsetX * o , y + dir.offsetY * o, z + dir.offsetZ * o, new int[] {0, 0, 0, 1, 1, 1}, x, y, z, dir))",
            87: "if(tool == ToolType.SCREWDRIVER) {", 88: "if(world.isRemote) return true;", 92: "tile.cycleCraneRotation();", 94: "return true;", 97: "return false;"},
    "base": {110: "if(!worldObj.isRemote) {", 112: "if(this.craneIndicator > 0) this.craneIndicator--;", 115: "moveHeat();", 293: "buf.writeDouble(this.heat);",
             296: "buf.writeByte((byte) this.craneIndicator);", 304: "this.craneIndicator = buf.readByte();"},
    "cons": {104: 'columns[index].data.setByte("indicator", (byte) rbmk.craneIndicator);'},
    "tool": {70: "if(b == ModBlocks.rbmk_crane_console && stack.hasTagCompound()) {", 74: "int[] pos = ((BlockDummyable)b).findCore(world, x, y, z);",
             77: 'int tx = stack.stackTagCompound.getInteger("posX");', 78: 'int ty = stack.stackTagCompound.getInteger("posY");', 79: 'int tz = stack.stackTagCompound.getInteger("posZ");',
             80: "console.setTarget(tx, ty, tz);", 81: 'new ChatComponentTranslation(this.getUnlocalizedName() + ".set")', 84: "return true;"},
    "kb": {53: 'craneUpKey = new KeyBinding(category + ".craneMoveUp", Keyboard.KEY_UP, category);', 54: 'craneDownKey = new KeyBinding(category + ".craneMoveDown", Keyboard.KEY_DOWN, category);',
           55: 'craneLeftKey = new KeyBinding(category + ".craneMoveLeft", Keyboard.KEY_LEFT, category);', 56: 'craneRightKey = new KeyBinding(category + ".craneMoveRight", Keyboard.KEY_RIGHT, category);',
           57: 'craneLoadKey = new KeyBinding(category + ".craneLoad", Keyboard.KEY_RETURN, category);', 74: "ClientRegistry.registerKeyBinding(craneUpKey);",
           78: "ClientRegistry.registerKeyBinding(craneLoadKey);", 205: "props.setKeyPressed(key, current);",
           # The handoff cites :218-238 for EnumKeybind; the enum is at :221-240 in aee05a40f.
           221: "public static enum EnumKeybind {", 228: "CRANE_UP,", 232: "CRANE_LOAD,", 240: "RELOAD"},
    "cp": {1973: "public boolean getIsKeyPressed(EnumKeybind key) {", 1983: "case CRANE_UP:			return HbmKeybinds.craneUpKey.getIsKeyPressed();",
           1987: "case CRANE_LOAD:		return HbmKeybinds.craneLoadKey.getIsKeyPressed();"},
    "cm": {990: 'addRecipeAuto(new ItemStack(ModBlocks.rbmk_crane_console, 1), new Object[] { "BCD", "DDD", \'B\', B.ingot(), \'D\', ModBlocks.deco_rbmk, \'C\', DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ANALOG) });'},
    "rm": {1680: 'rbmk_crane_console = new HFRWavefrontObject(new ResourceLocation(RefStrings.MODID, "models/rbmk/crane_console.obj")).asVBO();',
           1681: 'rbmk_crane = new HFRWavefrontObject(new ResourceLocation(RefStrings.MODID, "models/rbmk/crane.obj")).asVBO();',
           1691: 'rbmk_crane_console_tex = new ResourceLocation(RefStrings.MODID, "textures/models/machines/crane_console.png");',
           1692: 'rbmk_crane_tex = new ResourceLocation(RefStrings.MODID, "textures/models/machines/rbmk_crane.png");'},
    "rend": {27: "case 2: teFacing = 90; break;", 28: "case 4: teFacing = 180; break;", 29: "case 3: teFacing = 270; break;", 30: "case 5: teFacing = 0; break;",
             36: "GL11.glTranslated(0.5, 0, 0);", 40: 'renderPart("Console_Coonsole");', 43: "GL11.glTranslated(0.75, 1, 0);", 46: "GL11.glTranslated(-0.75, -1.015, 0);",
             47: 'renderPart("JoyStick");', 51: "GL11.glTranslated(0, 1.25, 0.75);", 53: "Math.sin(System.currentTimeMillis() * 0.01 % 360) * 180 / Math.PI * 0.05 + 135 - 270 * heat",
             55: 'renderPart("Meter1");', 59: "GL11.glTranslated(0, 1.25, 0.25);", 61: "Math.sin(System.currentTimeMillis() * 0.01 % 360) * 180 / Math.PI * 0.05 + 135 - 270 * enrichment",
             63: 'renderPart("Meter2");', 77: "if(console.isCraneLoading()) GL11.glColor3f(0.8F, 0.8F, 0F);", 78: "else if(console.hasItemLoaded()) GL11.glColor3f(0F, 1F, 0F);",
             79: "else GL11.glColor3f(0F, 0.1F, 0F);", 80: 'renderPart("Lamp1");', 83: "if(console.isAboveValidTarget()) GL11.glColor3f(0F, 1F, 0F);", 84: "else GL11.glColor3f(1F, 0F, 0F);",
             85: 'renderPart("Lamp2");', 98: "int height = console.height - 6;", 118: "girderSpan = console.spanF + console.spanB + 1;", 119: "GL11.glTranslated(posX + console.spanB, 0, 0);",
             123: "GL11.glTranslated(0, 0, -posZ - console.spanR);", 127: "GL11.glTranslated(posX - console.spanF, 0, 0);", 131: "GL11.glTranslated(0, 0, -posZ + console.spanL);",
             137: 'renderPart("Girder");', 142: 'renderPart("Main");', 147: 'renderPart("Tube");', 151: 'renderPart("Carriage");',
             154: "GL11.glTranslated(0, -3.25 * (1 - (console.lastProgress + (console.progress - console.lastProgress) * interp)), 0);", 155: 'renderPart("Lift");'},
    "irl": {681: "renderers.put(Item.getItemFromBlock(ModBlocks.rbmk_crane_console), new ItemRenderBase() {", 683: "GL11.glTranslated(0, -3, 0);", 684: "GL11.glScaled(3.5, 3.5, 3.5);",
            689: 'renderPart("Console_Coonsole");', 690: 'renderPart("JoyStick");', 691: 'renderPart("Meter1");', 692: 'renderPart("Meter2");'},
    "mb": {2132: 'rbmk_crane_console = new RBMKCraneConsole().setBlockName("rbmk_crane_console").setCreativeTab(MainRegistry.machineTab).setBlockTextureName(RefStrings.MODID + ":rbmk/rbmk_crane_console");'},
}

# V8: (NEO key, original key, en_US.lang line, zh_CN.lang line)
UP = [("block.hbmsntm.rbmk_crane_console", "tile.rbmk_crane_console.name", 6222, 5347), ("hbmsntm.keys.craneLoad", "hbm.key.craneLoad", 1433, 1157),
      ("hbmsntm.keys.craneMoveDown", "hbm.key.craneMoveDown", 1434, 1158), ("hbmsntm.keys.craneMoveLeft", "hbm.key.craneMoveLeft", 1435, 1159),
      ("hbmsntm.keys.craneMoveRight", "hbm.key.craneMoveRight", 1436, 1160), ("hbmsntm.keys.craneMoveUp", "hbm.key.craneMoveUp", 1437, 1161)]
NEW_KEYS = [u[0] for u in UP]

IMPORTS = [("models/rbmk/crane_console.obj", "models/obj/rbmk/crane_console.obj"), ("models/rbmk/crane.obj", "models/obj/rbmk/crane.obj"),
           ("textures/models/machines/crane_console.png", "textures/models/machines/crane_console.png"), ("textures/models/machines/rbmk_crane.png", "textures/models/machines/rbmk_crane.png"),
           ("textures/blocks/rbmk/rbmk_crane_console.png", "textures/block/rbmk/rbmk_crane_console.png")]
IMPORT_PATHS = [RES + n for _, n in IMPORTS]

# V5: original LWJGL Keyboard constant -> NEO InputConstants constant; original field -> NEO field
KEYSYM = {"KEY_UP": "KEY_UP", "KEY_DOWN": "KEY_DOWN", "KEY_LEFT": "KEY_LEFT", "KEY_RIGHT": "KEY_RIGHT", "KEY_RETURN": "KEY_RETURN"}
KEY_FIELDS = {"craneUpKey": "CRANE_UP", "craneDownKey": "CRANE_DOWN", "craneLeftKey": "CRANE_LEFT", "craneRightKey": "CRANE_RIGHT", "craneLoadKey": "CRANE_LOAD"}
# V7: the original recipe ingredients -> NEO item ids
RECIPE_ITEMS = {"B.ingot()": "hbmsntm:ingot_boron", "ModBlocks.deco_rbmk": "hbmsntm:deco_rbmk", "DictFrame.fromOne(ModItems.circuit,EnumCircuitType.ANALOG)": "hbmsntm:circuit_analog_board"}

GT_MARK = "[hbm-rbmk-crane]"
START_GAMETESTS = 231
GT_AREAS = ("crane_placement", "crane_set_target", "crane_move", "crane_load_cycle", "crane_no_interaction", "crane_indicator", "crane_keys", "crane_persistence", "crane_recipe")
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
    inp.o_lines_en = lf(read_text(ORIGINAL / O_LANG / "en_US.lang")).split("\n")
    inp.o_lines_zh = lf(read_text(ORIGINAL / O_LANG / "zh_CN.lang")).split("\n")
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


def onum(inp, key, n, pattern):
    """A number captured from an original line (after sq); a moved line gives None and the dependent check fails."""
    m = re.search(pattern, oline(inp, key, n))
    return m[1] if m else None


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
    starts = [p for p in EDITED + [EN, PICK, ZH, MAP] if p != SP]
    ck("V0.start-copies-of-edited", all(p in inp.start for p in starts) and SP in inp.base_files,
       "the start copies of every edited file exist (ServerProxy, a clean file at the start, by its baseline.json hash)", [p for p in starts if p not in inp.start])


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", e is not None and len(e) == 1 and e[0][1] == en_line and z is not None and len(z) == 1 and z[0][1] == zh_line,
           f"{okey} once in en_US.lang:{en_line} and zh_CN.lang:{zh_line}", (e, z))


# ---------------------------------------------------------------- V2 block entity against V1

DIR_RW = [lit("ForgeDirectiondir=ForgeDirection.getOrientation(this.getBlockMetadata()-BlockDummyable.offset)", "Directiondir=this.getBlockState().getValue(DummyableBlock.FACING)"),
          lit("dir.getRotation(ForgeDirection.UP)", "dir.getClockWise()"), lit("dir.getRotation(ForgeDirection.DOWN)", "dir.getCounterClockWise()"),
          lit("ForgeDirectionside=", "Directionside="), lit("ForgeDirectionleft=", "Directionleft="),
          lit("offsetX", "getStepX()"), lit("offsetZ", "getStepZ()"), lit("xCoord", "this.worldPosition.getX()"), lit("zCoord", "this.worldPosition.getZ()"),
          lit("RBMKDials.getColumnHeight(worldObj)", "RBMKDials.getColumnHeight()"), lit("this.markDirty();", "this.setChanged();"),
          lit("MathHelper.clamp_double", "Mth.clamp"), lit("ItemRBMKRod", "RBMKRodItem"), lit("loadedItem!=null&&", "!loadedItem.isEmpty()&&"),
          lit("!worldObj.isAirBlock(x+dir.getStepX()*i,y,z+dir.getStepZ()*i)", "!this.level.isEmptyBlock(newBlockPos(x+dir.getStepX()*i,y,z+dir.getStepZ()*i))")]


def rw(s):
    return rewrite(s, DIR_RW)


def v2_block_entity(ck, inp, st):
    be = lf(st.text(CBE))
    code = code_of(be)
    contains_all(ck, "V2.constants", "speed 0.05 (:57), goesDown false and progress 1 at start (:59-62), LoadedBaseBlockEntity + ITickable", code,
                 oline(inp, "te", 57), oline(inp, "te", 59), oline(inp, "te", 61), "publicclassRBMKCraneConsoleBlockEntityextendsLoadedBaseBlockEntityimplementsITickable{")
    upd = body(be, "public void updateEntity()")
    down = onum(inp, "te", 101, r"progress-=([\d.]+);")
    upstep = onum(inp, "te", 124, r"progress\+=([\d.]+);")
    lift = ("if(!this.level.isClientSide){RBMKBaseBlockEntityaboveColumn=this.getColumnAtPos();" + oline(inp, "te", 96)
            + f"if(goesDown){{if(progress>0){{progress-={down};}}else{{progress=0;goesDown=false;")
    ck("V2.lift", lift in upd and f"}}elseif(progress!=1){{progress+={upstep};if(progress>1){{progress=1;}}}}" in upd,
       f"the server lift of :94-130: indicator 10 on the column (:96), {down} per update down while > 0, then 0 and the interaction, {upstep} up clamped to 1", (lift, upd[:400]))
    ck("V2.load-branch", "if(aboveColumninstanceofIRBMKLoadablecolumn&&this.canTargetInteract(column)){if(!this.loadedItem.isEmpty()){column.load(this.loadedItem);"
       "this.loadedItem=ItemStack.EMPTY;}else{this.loadedItem=column.provideNext();column.unload();}this.setChanged();}" in upd,
       "the interaction of :106-119: loaded -> load and empty the lift, empty -> provideNext then unload, marked")
    box = rw(olines(inp, "te", 132, 137))
    ck("V2.box", box in upd and "this.worldPosition.getY(),Math.min(minZ,maxZ),Math.max(minX,maxX),this.worldPosition.getY()+" + onum(inp, "te", 144, r"yCoord\+(\d+),") + "," in upd
       and "List<Player>players=this.level.getEntitiesOfClass(Player.class,newAABB(" in upd,
       "the operator box of :132-145 (side = getRotation(UP) = clockwise, x / z per facing, y .. y + 2)", box)
    order = missing_order(upd, "tiltFront=0;tiltLeft=0;", "if(!players.isEmpty()&&!isCraneLoading()){Playerplayer=players.get(0);",
                          "booleanup=isKeyPressed(player,EnumKeybind.CRANE_UP);booleandown=isKeyPressed(player,EnumKeybind.CRANE_DOWN);"
                          "booleanleft=isKeyPressed(player,EnumKeybind.CRANE_LEFT);booleanright=isKeyPressed(player,EnumKeybind.CRANE_RIGHT);",
                          "intfront=0;if(up&&!down)front=1;if(!up&&down)front=-1;intsideways=0;if(left&&!right)sideways=1;if(!left&&right)sideways=-1;",
                          "this.moveCrane(front,sideways);", "if(isKeyPressed(player,EnumKeybind.CRANE_LOAD)){this.startLoad();}}",
                          rw(oline(inp, "te", 179)), rw(oline(inp, "te", 180)), rw(olines(inp, "te", 184, 190)), "this.networkPackNT(" + onum(inp, "te", 192, r"networkPackNT\((\d+)\)") + ");")
    ck("V2.keys-order", order is None and oline(inp, "te", 149) == "if(players.size()>0&&!isCraneLoading()){" and oline(inp, "te", 150) == "EntityPlayerplayer=players.get(0);",
       "the tick after the lift: tilt reset (:146-147), the first player only and not loading (:149-150), the truth tables of :157-172, the load key (:174-176), "
       "the clamps (:179-180), heat / enrichment of a held rod (:184-190), networkPackNT(250) (:192)", order)
    tilt = onum(inp, "te", 158, r"tiltFront=(\d+);")
    ck("V2.move", body(be, "public void moveCrane(int front, int left)") == "doubleprevFront=this.posFront;doubleprevLeft=this.posLeft;booleanserver=this.level!=null&&!this.level.isClientSide;"
       f"if(front!=0){{tiltFront={tilt}*front;if(server)posFront+=speed*front;}}if(left!=0){{tiltLeft={tilt}*left;if(server)posLeft+=speed*left;}}"
       "if(this.posFront!=prevFront||this.posLeft!=prevLeft)this.setChanged();"
       and body(be, "public void startLoad()") == "this.goesDown=" + onum(inp, "te", 175, r"goesDown=(\w+);") + ";",
       f"moveCrane: tilt {tilt} * dir on both sides, speed * dir on the server only (:157-172); startLoad sets goesDown (:175)", body(be, "public void moveCrane(int front, int left)"))
    ck("V2.key-read", body(be, "private static boolean isKeyPressed(Player player, EnumKeybind key)") == "if(!player.level().isClientSide)returnHbmPlayerAttachments.getData(player).getKeyPressed(key);"
       "returnplayer==NuclearTechMod.proxy.me()&&NuclearTechMod.proxy.getIsKeyPressed(key);",
       "keys: the server reads HbmPlayerAttachments (HbmPlayerProps :151-155), the client only the local player through the proxy", body(be, "private static boolean isKeyPressed(Player player, EnumKeybind key)"))
    col = body(be, "public RBMKBaseBlockEntity getColumnAtPos()")
    ck("V2.column-at", ordered(col, "if(this.level==null||!this.setUpCrane)returnnull;", rw(oline(inp, "te", 226)), rw(oline(inp, "te", 227)), rw(olines(inp, "te", 229, 231)),
                               "BlockPospos=newBlockPos(x,y,z);if(!this.level.isLoaded(pos))returnnull;", "if(binstanceofRBMKBaseBlockrbmk){BlockPoscore=rbmk.findCore(this.level,pos);",
                               "if(core!=null&&this.level.getBlockEntity(core)instanceofRBMKBaseBlockEntitycolumn){returncolumn;}"),
       "getColumnAtPos: the formula of :226-231 (left = getRotation(DOWN), floor(c - dir * front - left * left + 0.5), y = centerY - 1), findCore; NEO guards: unlinked, "
       "unloaded chunk, null core, block entity type", col)
    ser = body(be, "public void serialize(RegistryFriendlyByteBuf buf)")
    des = body(be, "public void deserialize(RegistryFriendlyByteBuf buf)")
    ck("V2.sync", ser == "super.serialize(buf);" + olines(inp, "te", 255, 273) and des == "super.deserialize(buf);" + olines(inp, "te", 278, 295),
       "serialize / deserialize equal :253-296 field by field after the LoadedBase prefix (setUpCrane, then 9 ints, 3 doubles, the loaded flag, 2 doubles)", (ser, des))
    st_body = body(be, "public void setTarget(int x, int y, int z)")
    ck("V2.set-target", st_body == rw(olines(inp, "te", 299, 318)), "setTarget equals :298-319 (centre + columnHeight + 1, girders + 6, F = opposite, R / B / L clockwise, max 16, height 7)",
       (st_body, rw(olines(inp, "te", 299, 318))))
    fre = body(be, "private int findRoomExtent(int x, int y, int z, Direction dir, int max)")
    ck("V2.room-extent", fre == rw(olines(inp, "te", 322, 328)), "findRoomExtent equals :321-329 (i from 1 while < max, the first non-air gives i - 1, else max)", (fre, rw(olines(inp, "te", 322, 328))))
    ck("V2.rotation", body(be, "public void cycleCraneRotation()") == oline(inp, "te", 332) + "this.setChanged();", "cycleCraneRotation: + 90 % 360 (:332), marked (NEO)")
    load_rw = [lit("nbt.", "tag."), lit("getInteger", "getInt")]
    save_rw = [lit("nbt.setBoolean", "tag.putBoolean"), lit("nbt.setInteger", "tag.putInt"), lit("nbt.setDouble", "tag.putDouble")]
    lb = body(be, "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    sb = body(be, "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    want_l = "super.loadAdditional(tag,registries);" + rewrite(olines(inp, "te", 339, 350), load_rw) + 'this.loadedItem=tag.contains("held")?ItemStack.parseOptional(registries,tag.getCompound("held")):ItemStack.EMPTY;'
    want_s = "super.saveAdditional(tag,registries);" + rewrite(olines(inp, "te", 360, 371), save_rw) + 'if(!this.loadedItem.isEmpty()){tag.put("held",this.loadedItem.save(registries));}'
    ck("V2.nbt", lb == want_l and sb == want_s, "NBT keys crane / craneRotationOffset / centerX-Z / spanF-R / height / posFront / posLeft with their types (:339-350, :360-371), held only when held (:352-353, :373-377)",
       (lb, want_l, sb, want_s))
    ck("V2.render-box", body(be, "public AABB getRenderBoundingBox()") == "returnAABB.INFINITE;" and "INFINITE_EXTENT_AABB" in oline(inp, "te", 382), "the render box is infinite (:380-383)")
    ck("V2.interact", body(be, "public boolean canTargetInteract(IRBMKLoadable column)") == olines(inp, "te", 214, 221) and body(be, "public boolean isCraneLoading()") == oline(inp, "te", 205),
       "canTargetInteract (:212-222) and isCraneLoading (:204-206) equal the original")
    leaks = [p for p in (CBE, CBLK) if re.search(r"import net\.minecraft\.client|import com\.hbm\.render\.|Minecraft\.getInstance|import com\.hbm\.handler\.HbmKeybinds;", blank_comments(st.text(p)))]
    ck("V2.no-client-leak", not leaks, "the block entity and the block import no client class (EnumKeybind is the nested enum only)", leaks)


# ---------------------------------------------------------------- V3 block

def v3_block(ck, inp, st):
    blk = lf(st.text(CBLK))
    code = code_of(blk)
    ck("V3.dimensions", "publicint[]getDimensions(){" + oline(inp, "blk", 34) + "}" in code and "publicintgetOffset(){" + oline(inp, "blk", 39) + "}" in code,
       "getDimensions {1, 0, 0, 0, 1, 1} (:34) and offset 1 (:39)")
    second = re.search(r"newint\[\]\{([\d,]+)\}", oline(inp, "blk", 45))
    ck("V3.second-box", second is not None and f"privatestaticfinalint[]EXTRA_DIMENSIONS=newint[]{{{second[1]}}};" in code
       and body(blk, "protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset)") == "if(!MultiblockHandlerXR.checkSpace(level,pos.relative(dir,offset),EXTRA_DIMENSIONS,pos,dir))returnfalse;returnsuper.checkRequirement(level,pos,dir,offset);"
       and body(blk, "protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset)") == "super.fillSpace(level,pos,dir,offset);MultiblockHandlerXR.fillSpace(level,pos.relative(dir,offset),EXTRA_DIMENSIONS,this,dir);",
       "the second box {0, 0, 0, 1, 1, 1} around the core in checkRequirement (:55-62) and fillSpace (:48-53)")
    ck("V3.block-entity", body(blk, "public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state)") == "returnstate.getValue(TYPE)==DummyBlockType.CORE?newRBMKCraneConsoleBlockEntity(pos,state):null;",
       "only the core has a block entity (:24-30)")
    ck("V3.ticker", body(blk, "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type)")
       == "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};",
       "the core ticks on both sides (updateEntity has the client branch)")
    scr = body(blk, "public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool)")
    ck("V3.screwdriver", scr == "if(tool!=ToolType.SCREWDRIVER)returnfalse;if(!level.isClientSide){BlockPoscore=this.findCore(level,pos);"
       "if(core!=null&&level.getBlockEntity(core)instanceofRBMKCraneConsoleBlockEntityconsole){console.cycleCraneRotation();}}returntrue;"
       and oline(inp, "blk", 87) == "if(tool==ToolType.SCREWDRIVER){" and oline(inp, "blk", 97) == "returnfalse;",
       "onScrew: screwdriver only, server cycles the core's rotation, true; any other tool false (:84-98); NEO null guard", scr)
    ck("V3.no-menu", "useWithoutItem" not in code and "MenuProvider" not in code and "MenuProvider" not in code_of(st.text(CBE)), "the crane console has no GUI")
    hard = onum(inp, "blk", 20, r"setHardness\(([\d.]+)\);")
    res = onum(inp, "blk", 21, r"setResistance\(([\d.]+)\);")
    m = re.search(r'RBMK_CRANE_CONSOLE=register\("rbmk_crane_console",\(\)->newRBMKCraneConsoleBlock\(BlockBehaviour\.Properties\.of\(\)\.noOcclusion\(\)\.strength\(([\d.]+),([\d.]+)\)'
                  r"\.sound\(SoundType\.METAL\)\.mapColor\(MapColor\.METAL\)\.requiresCorrectToolForDrops\(\)\)\);", code_of(st.text(NB)))
    ck("V3.strength", m is not None and hard is not None and res is not None and float(m[1]) == float(hard) and float(m[2]) == float(res),
       f"NtmBlocks: hardness {hard}, resistance {res} (RBMKCraneConsole :20-21), metal, no occlusion", m and m.groups())


# ---------------------------------------------------------------- V4 base, console, tool

def v4_base_console_tool(ck, inp, st):
    base = lf(st.text(BASE))
    bc = code_of(base)
    ck("V4.field", "publicintcraneIndicator;" in bc and "craneIndicator" not in body(base, "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)")
       and "craneIndicator" not in body(base, "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)"), "public int craneIndicator, not in the NBT")
    upd = body(base, "public void updateEntity()")
    ck("V4.decrement", upd.startswith("if(this.level==null||this.level.isClientSide)return;" + oline(inp, "base", 112) + "moveHeat();"),
       "the server update decrements the indicator first, then moves heat (:110-115)", upd[:200])
    ser = body(base, "public void serialize(RegistryFriendlyByteBuf buf)")
    des = body(base, "public void deserialize(RegistryFriendlyByteBuf buf)")
    ck("V4.sync-byte", ser == "super.serialize(buf);" + oline(inp, "base", 293) + oline(inp, "base", 296) and des == "super.deserialize(buf);this.heat=buf.readDouble();" + oline(inp, "base", 304),
       "the indicator byte follows heat in serialize / deserialize (:292-305 without the unported reasim ints)", (ser, des))
    cons = code_of(st.text(CONS))
    ck("V4.console", rewrite(oline(inp, "cons", 104), [lit("data.setByte", "data.putByte")]) in cons and cons.count('putByte("indicator"') == 1,
       "the console rescan puts the column's craneIndicator as the indicator byte (:104)")
    tool = lf(st.text(TOOL))
    use = body(tool, "public InteractionResult useOn(UseOnContext context)")
    keys = [re.search(r'getInteger\("(\w+)"\)', oline(inp, "tool", n)) for n in (77, 78, 79)]
    keys = [k[1] if k else None for k in keys]
    branch = ("if(binstanceofRBMKCraneConsoleBlockcrane&&hasPosition(stack)){if(!level.isClientSide){BlockPoscore=crane.findCore(level,pos);"
              "if(core!=null&&level.getBlockEntity(core)instanceofRBMKCraneConsoleBlockEntitybe){CompoundTagtag=TagsUtil.getCustomData(stack);"
              f'be.setTarget(tag.getInt("{keys[0]}"),tag.getInt("{keys[1]}"),tag.getInt("{keys[2]}"));'
              'if(player!=null)player.displayClientMessage(Component.translatable(this.getDescriptionId()+".set").withStyle(ChatFormatting.YELLOW),false);}}'
              "returnInteractionResult.sidedSuccess(level.isClientSide);}")
    ck("V4.tool-branch", branch in use and ".set" in oline(inp, "tool", 81) and use.index(branch) < use.index("returnInteractionResult.PASS;"),
       "rbmk_tool: on a crane console with a stored position, the core's setTarget(posX, posY, posZ) and the .set message, success (:70-85); NEO: position check, null core", branch)
    ck("V4.has-position", body(tool, "private static boolean hasPosition(ItemStack stack)") == 'CompoundTagtag=TagsUtil.getCustomData(stack);returntag.contains("posX")&&tag.contains("posY")&&tag.contains("posZ");',
       "hasPosition needs all three keys")
    bad = []
    for p in COMMENT_ONLY:
        if p in inp.start and code_of(inp.start[p]) != code_of(st.text(p)):
            bad.append(p.rsplit("/", 1)[1])
    ck("V4.comment-only", not bad, "IRBMKLoadable, RBMKSlottedBaseBlockEntity and RBMKStorageBlockEntity differ from the start in comments only", bad)


# ---------------------------------------------------------------- V5 keybinds and proxies

def v5_keybinds(ck, inp, st):
    kb = lf(st.text(KB))
    code = code_of(kb)
    start = lf(inp.start[KB])
    fields = []
    for n in range(53, 58):
        m = re.search(r'publicstaticKeyBinding(\w+)=newKeyBinding\(category\+"(\.\w+)",Keyboard\.(\w+),category\);', oline(inp, "kb", n))
        if not m:
            fields.append(None)
            continue
        fields.append((KEY_FIELDS.get(m[1]), m[2], KEYSYM.get(m[3])))
    want = [f'publicstaticfinalKeyMapping{f}=newKeyMapping(category+"{i}",InputConstants.Type.KEYSYM,InputConstants.{k},category);' for f, i, k in (x for x in fields if x)]
    ck("V5.mappings", None not in fields and len(want) == 5 and all(w in code for w in want), "five KeyMappings with the original ids and the arrow / return keys (:53-57), category hbmsntm.keys",
       [w for w in want if w not in code])
    reg = body(kb, "public static void onRegisterKeyMappings(RegisterKeyMappingsEvent event)")
    ck("V5.registered", all(reg.count(f"event.register({f});") == 1 for f in KEY_FIELDS.values()), "each crane mapping registered once (:74-78)", reg)
    cases = body(kb, "public static boolean getIsKeyPressed(EnumKeybind key)")
    ck("V5.cases", all(f"case{f}->{f}.isDown();" in cases for f in KEY_FIELDS.values()), "getIsKeyPressed reports the five mappings (ClientProxy :1983-1987)", cases)
    ck("V5.no-mirror", "HbmPlayerAttachments.setKeyPressed" not in code, "handleProps has no client attachment mirror line (review fix1 removed it)")
    added, removed = [], []
    for line in difflib.ndiff(lf(start).split("\n"), kb.split("\n")):
        if line.startswith("+ "):
            added.append(line[2:])
        elif line.startswith("- "):
            removed.append(line[2:])
    allowed = re.compile(r"^\s*$|^\s*// RBMK crane console controls: original craneUpKey \.\. craneLoadKey \(:53-57\)\.$|^\s*public static final KeyMapping CRANE_\w+ = new KeyMapping\(.*\);$"
                         r"|^\s*event\.register\(CRANE_\w+\);$|^\s*case CRANE_\w+ -> CRANE_\w+\.isDown\(\);$")
    extra = [a for a in added if not allowed.match(a)]
    ck("V5.rest-unchanged", not removed and not extra and len([a for a in added if a.strip()]) == 16,
       "HbmKeybinds equals the start copy apart from the five mappings with their comment, their registration and the five switch cases", (removed[:5], extra[:5]))
    enum_now = re.search(r"publicenumEnumKeybind\{([\w,]+)\}", code)
    enum_start = re.search(r"publicenumEnumKeybind\{([\w,]+)\}", code_of(start))
    ck("V5.enum-order", enum_now is not None and enum_start is not None and enum_now[1] == enum_start[1] and enum_now[1].split(",").index("CRANE_UP") + 1 == enum_now[1].split(",").index("CRANE_DOWN"),
       "EnumKeybind order identical to the start copy (20 values; the original order of :221-240 plus NEO's DUCK)", enum_now and enum_now[1])
    sp = code_of(st.text(SP))
    cp = code_of(st.text(CP))
    ck("V5.proxies", "publicbooleangetIsKeyPressed(HbmKeybinds.EnumKeybindkey){returnfalse;}" in sp and "@OverridepublicbooleangetIsKeyPressed(HbmKeybinds.EnumKeybindkey){returnHbmKeybinds.getIsKeyPressed(key);}" in cp
       and "publicbooleangetIsKeyPressed(EnumKeybindkey){" == oline(inp, "cp", 1973),
       "ServerProxy.getIsKeyPressed is false, ClientProxy's overrides it with HbmKeybinds.getIsKeyPressed (original ClientProxy :1973-1987)")
    same = [p for p in CHAIN if not hashed_equal(inp, st, p)]
    ck("V5.chain-unchanged", not same, "KeybindReceiver, HbmKeybindsServer and HbmPlayerAttachments are byte-equal to the start", same)


# ---------------------------------------------------------------- V6 renderer, ResourceManager, BER

def v6_renderer(ck, inp, st):
    rend = lf(st.text(CREND))
    code = code_of(rend)
    parts = []
    for n in (40, 47, 55, 63, 80, 85, 137, 142, 147, 151, 155):
        m = re.search(r'renderPart\("(\w+)"\)', inp.ol["rend"][n - 1])
        parts.append(m[1] if m else None)
    block_render = body(rend, "public void render(RBMKCraneConsoleBlockEntity console, MultiBufferSource buffer, float partialTicks)")
    missing = [p for p in parts if p is None or f'renderPart("{p}")' not in block_render]
    ck("V6.parts", not missing and len(parts) == 11, "the block renderer draws the original's eleven parts (:40-155)", missing)
    obj_names = {}
    for path in IMPORT_PATHS[:2]:
        if st.has(path):
            obj_names[path] = {l[2:].strip().lower() for l in st.files[path].decode("utf-8", "replace").split("\n") if l.startswith("o ")}
    absent = [p for p in parts if p and p.lower() not in obj_names.get(IMPORT_PATHS[0], set()) | obj_names.get(IMPORT_PATHS[1], set())]
    ck("V6.parts-in-obj", not absent, "every drawn part is an object of crane_console.obj / crane.obj (renderPart compares ignoring case)", absent)
    face = {}
    for n in (27, 28, 29, 30):
        m = re.search(r"case(\d):teFacing=(\d+);break;", oline(inp, "rend", n))
        face[m[1]] = m[2] if m else None
    meta_dir = {"2": "NORTH", "3": "SOUTH", "4": "WEST", "5": "EAST"}
    want = "".join(f"case{meta_dir[k]}->teFacing={v};" for k, v in face.items())
    ck("V6.facing", want in code, "the facing switch of :26-31 (2 north 90, 4 west 180, 3 south 270, 5 east 0)", want)
    meter = sq(ANCHORS["rend"][53]).replace("interp", "partialTicks")
    ck("V6.meters", sq(ANCHORS["rend"][53]) in oline(inp, "rend", 53) and code.count(meter.replace("heat", "heat")) == 1 and meter.replace("*heat", "*enrichment") in code
       and "RenderContext.translate(0,1.25,0.75);" in code and "RenderContext.translate(0,1.25,0.25);" in code,
       "the meter rotation formula of :53 / :61 (0.01, 0.05, 135, 270) at the original pivots (:51, :59)", meter)
    ck("V6.joystick", "RenderContext.translate(0.75,1,0);" in code and "RenderContext.translate(-0.75,-1.015,0);" in code and "RenderContext.translate(0.5,0,0);" in code,
       "joystick pivot (0.75, 1, 0) / (-0.75, -1.015, 0) and the console offset 0.5 (:36, :43, :46)")
    cols = []
    for n in (77, 78, 79, 83, 84):
        m = re.search(r"glColor3f\(([\d.]+),([\d.]+),([\d.]+)\)", oline(inp, "rend", n))
        cols.append(f"RenderContext.setColor({m[1]},{m[2]},{m[3]},1);" if m else "?")
    ck("V6.lamps", ordered(code, *cols), "lamp colours of :77-84 in order (loading yellow, loaded green, off; valid green, invalid red)", cols)
    lift = re.search(r"-([\d.]+)\*\(1-", oline(inp, "rend", 154))
    ck("V6.crane", lift is not None and f"RenderContext.translate(0,(float)(-{lift[1]}*(1-(console.lastProgress+(console.progress-console.lastProgress)*partialTicks))),0);" in code
       and oline(inp, "rend", 98) in code and "girderSpan=console.spanF+console.spanB+1;RenderContext.translate((float)(posX+console.spanB),0,0);" in code
       and "RenderContext.translate(0,0,(float)(-posZ-console.spanR));" in code and "RenderContext.translate((float)(posX-console.spanF),0,0);" in code
       and "RenderContext.translate(0,0,(float)(-posZ+console.spanL));" in code,
       "the crane: lift -3.25 * (1 - progress) (:154), height - 6 tubes (:98), the girder spans and offsets per rotation (:116-133)")
    inv = body(rend, "public void renderInventory(ItemStack stack, MultiBufferSource buffer)")
    common = body(rend, "public void renderCommon(ItemStack stack, MultiBufferSource buffer)")
    ck("V6.item", inv == "RenderContext.translate(0,-3,0);RenderContext.scale(3.5,3.5,3.5);" and oline(inp, "irl", 683) == "GL11.glTranslated(0,-3,0);" and oline(inp, "irl", 684) == "GL11.glScaled(3.5,3.5,3.5);"
       and ordered(common, 'renderPart("Console_Coonsole");', 'renderPart("JoyStick");', 'renderPart("Meter1");', 'renderPart("Meter2");'),
       "item form: translate (0, -3, 0), scale 3.5, console / joystick / meters (ItemRenderLibrary.java:681-692)", (inp, common))
    rm = code_of(st.text(RM))
    paths = [re.search(r'"(models/rbmk/[\w.]+)"', oline(inp, "rm", n)) for n in (1680, 1681)]
    texs = [re.search(r'"(textures/models/machines/[\w.]+)"', oline(inp, "rm", n)) for n in (1691, 1692)]
    ok = all(paths) and all(texs) and f'rbmk_crane_console=newHFRWavefrontObject("{paths[0][1].replace("models/", "models/obj/")}").asVBO();' in rm \
        and f'rbmk_crane=newHFRWavefrontObject("{paths[1][1].replace("models/", "models/obj/")}").asVBO();' in rm \
        and f'RBMK_CRANE_CONSOLE_TEX=NuclearTechMod.withDefaultNamespace("{texs[0][1]}");' in rm and f'RBMK_CRANE_TEX=NuclearTechMod.withDefaultNamespace("{texs[1][1]}");' in rm
    ck("V6.resource-manager", ok and rm.count("rbmk_crane_console=newHFRWavefrontObject(") == 1 and rm.count("rbmk_crane=newHFRWavefrontObject(") == 1,
       "ResourceManager loads both OBJs as VBO without noSmooth (:1680-1681) and both textures (:1691-1692) once")
    ck("V6.ber", code_of(st.text(CP)).count("BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_CRANE_CONSOLE.get(),newRenderCraneConsole());") == 1, "ClientProxy registers the BER once")


# ---------------------------------------------------------------- V7 registrations, datagen, recipe

def v7_registration(ck, inp, st):
    ctab = code_of(st.text(CTAB))
    counts = {"NtmBlocks": code_of(st.text(NB)).count('register("rbmk_crane_console",'), "NtmBlockEntityTypes": code_of(st.text(BET)).count('BLOCK_ENTITY_TYPES.register("rbmk_crane_console",'),
              "NtmCreativeTabs": ctab.count("output.accept(NtmBlocks.RBMK_CRANE_CONSOLE);"), "ClientProxy": code_of(st.text(CP)).count("RBMK_CRANE_CONSOLE.get(),newRenderCraneConsole()"),
              "loot": code_of(st.text(LOOTP)).count("this.dropSelf(NtmBlocks.RBMK_CRANE_CONSOLE.get());"), "pickaxe": code_of(st.text(TAGP)).count("NtmBlocks.RBMK_CRANE_CONSOLE.get(),"),
              "blockstate": code_of(st.text(BSP)).count('this.particleOnlyBlock(NtmBlocks.RBMK_CRANE_CONSOLE,modLoc("block/' + (onum(inp, "mb", 2132, r'MODID\+":([\w/]+)"\);') or "?") + '"));')}
    ck("V7.registrations-once", all(v == 1 for v in counts.values()), "block, BE type, creative tab, BER, loot, pickaxe tag and blockstate (icon rbmk/rbmk_crane_console, ModBlocks.java:2132) each once", counts)
    ck("V7.tab-order", "output.accept(NtmBlocks.RBMK_CONSOLE);output.accept(NtmBlocks.RBMK_CRANE_CONSOLE);" in ctab and "machineTab" in oline(inp, "mb", 2132),
       "the crane console follows rbmk_console in the machine tab (original machineTab)")
    ck("V7.be-type", 'BLOCK_ENTITY_TYPES.register("rbmk_crane_console",()->BlockEntityType.Builder.of(RBMKCraneConsoleBlockEntity::new,NtmBlocks.RBMK_CRANE_CONSOLE.get()).build(null));' in code_of(st.text(BET)),
       "the block entity type is built for rbmk_crane_console only")
    ck("V7.generated", json.loads(st.text(G_BS)) == {"variants": {"": {"model": "hbmsntm:block/rbmk_crane_console_particle"}}}
       and json.loads(st.text(G_BM)) == {"textures": {"particle": "hbmsntm:block/rbmk/rbmk_crane_console"}}
       and json.loads(st.text(G_IM)) == {"parent": "minecraft:builtin/entity", "gui_light": "side"} and st.has(G_ADV),
       "generated blockstate -> particle-only block model (the block icon), item model builtin/entity (drawn by the BER), the recipe advancement", (st.text(G_BS), st.text(G_BM), st.text(G_IM)))
    loot = json.loads(st.text(G_LOOT))
    ck("V7.loot", [e["name"] for p in loot["pools"] for e in p["entries"]] == ["hbmsntm:rbmk_crane_console"], "the loot table drops the block itself", loot)
    ck("V7.pickaxe", json.loads(st.text(PICK))["values"].count("hbmsntm:rbmk_crane_console") == 1, "mineable/pickaxe lists rbmk_crane_console once")
    row = oline(inp, "cm", 990)
    m = re.search(r'newItemStack\(ModBlocks\.rbmk_crane_console,(\d+)\),newObject\[\]\{"(\w+)","(\w+)",(.*)\}\);', row)
    keys = dict(re.findall(r"'(\w)',((?:DictFrame\.fromOne\([^)]*\))|[\w.]+(?:\(\))?)", m[4])) if m else {}
    rec = json.loads(st.text(G_REC))
    want_key = {k: {"item": RECIPE_ITEMS.get(v, "?" + v)} for k, v in keys.items()}
    ck("V7.recipe", m is not None and rec.get("type") == "minecraft:crafting_shaped" and rec.get("pattern") == [m[2], m[3]] and rec.get("key") == want_key
       and rec.get("result") == {"count": int(m[1]), "id": "hbmsntm:rbmk_crane_console"},
       f"the generated recipe equals CraftingManager.java:990 ({m and [m[2], m[3]]}, {keys}, {m and m[1]} output)", (rec, want_key))


# ---------------------------------------------------------------- V8 language

def v8_lang(ck, inp, st):
    en, dup_en = json_pairs(st.text(EN))
    s_en = json.loads(inp.start[EN])
    lp = code_of(st.text(LP))
    want_en = {k: inp.o_en[ok][0][0] for k, ok, _, _ in UP}
    bad = {k: en.get(k) for k, v in want_en.items() if en.get(k) != v or k in s_en}
    prov = [k for k, v in want_en.items() if (f'this.add(NtmBlocks.RBMK_CRANE_CONSOLE,"{v}");' if k.startswith("block.") else f'this.add("{k}","{v}");') not in lp]
    ck("V8.en-new", not bad and not prov, "the six English keys are in NtmLanguageProvider and en_us.json with the original text (en_US.lang:6222, 1433-1437)", (bad, prov))
    ck("V8.en-rest", {k: v for k, v in en.items() if k not in want_en} == s_en and not dup_en, "en_us.json: nothing but the six keys changed")
    zh, dup_zh = json_pairs(st.text(ZH))
    s_zh = json.loads(inp.start[ZH])
    if not all(k in zh for k in NEW_KEYS):
        ck.pending("V8.zh-pending", "zh_cn.json does not yet carry the Goal25D keys: pending, not passed", [k for k in NEW_KEYS if k not in zh])
    else:
        want_zh = {k: inp.o_zh[ok][0][0] for k, ok, _, _ in UP}
        bad = {k: zh.get(k) for k, v in want_zh.items() if zh.get(k) != v}
        ck("V8.zh-new", not bad, "zh_cn.json has the six entries verbatim from zh_CN.lang:5347, 1157-1161", bad)
        ck("V8.zh-rest", {k: v for k, v in zh.items() if k not in want_zh} == s_zh and not dup_zh and all(k not in s_zh for k in want_zh), "zh_cn.json: nothing else changed")
    mp = json.loads(st.text(MAP))
    s_mp = json.loads(inp.start[MAP])
    ent, sent = mp["entries"], s_mp["entries"]
    if not all(k in ent for k in NEW_KEYS):
        ck.pending("V8.map-pending", "zh_cn-map.json does not yet carry the Goal25D entries: pending, not passed", [k for k in NEW_KEYS if k not in ent])
    else:
        bad = {}
        for k, ok, _, _ in UP:
            e = ent.get(k, {})
            if not (e.get("kind") == "upstream" and e.get("source_key") == ok and e.get("source_en") == inp.o_en[ok][0][0] and e.get("source_zh") == inp.o_zh[ok][0][0]
                    and e.get("target_en") == en.get(k) and e.get("target_zh") == zh.get(k) and placeholders(e.get("source_en", "")) == placeholders(e.get("target_zh", ""))):
                bad[k] = e
        ck("V8.map-entries", not bad, "zh_cn-map.json: 6 upstream entries with the original en/zh text at the cited lines", bad)
        ck("V8.map-rest", {k: v for k, v in ent.items() if k not in NEW_KEYS} == sent and {k: v for k, v in mp.items() if k != "entries"} == {k: v for k, v in s_mp.items() if k != "entries"}
           and len(ent) == len(sent) + 6, "zh_cn-map.json: nothing else changed (6 new entries)", (len(ent), len(sent)))
    eol = []
    for p in (ZH, MAP, EN):
        s_crlf = "\r\n" in inp.start[p]
        data = st.files[p]
        if s_crlf != (b"\r\n" in data) or (s_crlf and data.count(b"\r\n") != data.count(b"\n")):
            eol.append(p)
    ck("V8.eol", not eol, "zh_cn.json, zh_cn-map.json and en_us.json keep the start copy's line-ending style", eol)


# ---------------------------------------------------------------- V9 resources

def v9_resources(ck, inp, st):
    bad = [p for p in IMPORT_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V9.byte-equal", not bad and len(IMPORT_PATHS) == 5, "the two OBJs, the two model textures and the block icon are byte-equal (SHA-256) to the original working tree", bad)
    if not st.has(OWN):
        ck.pending("V9.ownership-pending", "migration/goal25d-resource-ownership.json is absent: pending, not passed")
        return
    own = json.loads(st.text(OWN))
    rows = {a["target_path"]: a for a in own.get("assets", [])}
    wrong = [p for p in IMPORT_PATHS if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None)
             or rows[p].get("source_path") != O_RES + IMPORTS[IMPORT_PATHS.index(p)][0]]
    ck("V9.ownership", not wrong and len(rows) == 5 and own.get("source_commit") == ORIGINAL_HEAD, "the ownership record lists the five imports with their source paths and hashes", wrong)


# ---------------------------------------------------------------- V10 scope

RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md", "migration/GOAL25.md",
                 "migration/GOAL25D.md", "migration/GOAL25D-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal25d-",)


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v10_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_CLASSES + EDITED + [EN, STAMP, PICK, GT] + IMPORT_PATHS + GEN_NEW)
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V10.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, imports, the GameTest, the records)", extra[:10])
    ck("V10.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != STAMP]
    ck("V10.expected-all-changed", not never, "every expected production, resource, generated and GameTest path differs from the start", never[:5])
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    ck("V10.gen-new", sorted(gen_new) == sorted(GEN_NEW), "exactly the six new generated files appeared", sorted(set(gen_new) ^ set(GEN_NEW)))
    ck("V10.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + [GT] + IMPORT_PATHS) and all(p in inp.base_files for p in EDITED),
       "the new classes, the GameTest and the imports did not exist at the start; the edited files did")
    ck("V10.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED), "the key chain, rod, dials, DummyableBlock, multiblock handler, rod item, console renderer / screen and older GameTests are byte-equal to the start",
       [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    eol = [p for p in EDITED if p in inp.start and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V10.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V10.records", True, "records changed (allowed, not required): " + ", ".join(rest))
    ck("V10.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V11 / V12

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*(?:@SuppressWarnings\([^)]*\)\s*)?public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v11_gametest(ck, inp, st):
    ck("V11.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", other_gametests())
    ck("V11.present", st.has(GT), "RBMKCraneGameTests.java exists")
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
    ck("V11.no-client", not re.search(r"net\.minecraft\.client|HbmKeybinds\.CRANE_|import com\.hbm\.handler\.HbmKeybinds;", code), "RBMKCraneGameTests references no client class (EnumKeybind only)")
    ck("V11.original-constants", "ORIGINAL_SPEED = 0.05D;" in live and "ORIGINAL_STEP = 0.04D;" in live and "ORIGINAL_INDICATOR = 10;" in live and "ORIGINAL_MAX_SPAN = 16;" in live
       and "ORIGINAL_HEIGHT = 7;" in live and "ORIGINAL_GIRDER_OFFSET = 6;" in live,
       "the GameTest's expected constants are the original's (0.05, 0.04, 10, 16, 7, 6), not read from the NEO class")
    return dict(tests=sorted(tests))


def original_cycle():
    """TileEntityCraneConsole :98-129 in IEEE doubles: decrements from 1 while > 0, the interaction update, increments clamped to 1."""
    p, down = 1.0, 0
    while p > 0:
        p -= 0.04
        down += 1
    p, up = 0.0, 0
    while p != 1:
        p += 0.04
        if p > 1:
            p = 1.0
        up += 1
    return down, up


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
    down, up = original_cycle()
    m = re.search(re.escape(GT_MARK) + r" load cycle unload: startLoad before game time (\d+), first decrement (\d+), interaction (\d+) \(after (\d+) decrements\), progress 1 at (\d+) \((\d+) ticks up\), rod B in slot 0 at (\d+)", text)
    m2 = re.search(re.escape(GT_MARK) + r" load cycle load: first decrement (\d+), interaction (\d+), progress 1 at (\d+)", text)
    if m and m2:
        s, f, i, n, one, u, shift = (int(x) for x in m.groups())
        f2, i2, one2 = (int(x) for x in m2.groups())
        facts["load_cycle"] = dict(logged=[m[0], m2[0]], original_decrements=down, original_increments=up)
        ck("V11.ticks-load", n == down and i - f == down and one - i == up == u and i2 - f2 == down and one2 - i2 == up and 0 <= shift - i <= 10,
           f"the logged lift ticks re-derive from the original: {down} decrements of 0.04 from 1 (the interaction in the next update), {up} increments back to 1; the storage shift within 10 ticks",
           (s, f, i, n, one, u, shift, f2, i2, one2, down, up))
    else:
        ck("V11.ticks-load", False, "the load cycle tick lines are missing from the log")
    mv = re.search(re.escape(GT_MARK) + r" move: posFront ([\d.E-]+) after 20 ticks \(game time (\d+) -> (\d+)\)", text)
    keys = re.search(re.escape(GT_MARK) + r" keys: CRANE_UP pressed before game time (\d+), posFront ([\d.E-]+) at (\d+) \(20 ticks\)", text)
    p = 0.0
    for _ in range(20):
        p += 0.05
    ok = bool(mv and keys) and abs(float(mv[1]) - 1.0) < 1e-9 and float(mv[1]) == p and int(mv[3]) - int(mv[2]) == 19 and float(keys[2]) == p and int(keys[3]) - int(keys[1]) == 19
    ck("V11.ticks-move", ok, f"20 moves of 0.05 give {p!r} (within 1e-9 of 1.0) on 20 consecutive ticks, through moveCrane and through CRANE_UP", (mv and mv[0], keys and keys[0]))
    ind = re.search(re.escape(GT_MARK) + r" indicator: 10 at game time (\d+)\.\.(\d+), crane left before (\d+), 0 at (\d+); console indicator (\d+) then (\d+)", text)
    ck("V11.ticks-indicator", bool(ind) and int(ind[2]) - int(ind[1]) == 4 and int(ind[4]) - int(ind[3]) == 9 and ind[5] == "10" and ind[6] == "0",
       "the indicator stays 10 under the crane and reaches 0 ten column updates after it left (:96, :112); the console shows 10 then 0", ind and ind[0])
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()), **facts)


def v12_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    gen = GEN_NEW + [EN, PICK]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        ck("V12.classes", not missing, "the JAR has the 3 new production classes and RBMKCraneGameTests", missing)
        bad = [p for p in IMPORT_PATHS if p[len("src/main/resources/"):] not in names or jar.read(p[len("src/main/resources/"):]) != st.files.get(p)]
        ck("V12.resources", not bad, "the five imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V12.generated", not gbad, "the generated blockstate, models, advancement, loot, recipe, en_us.json and the pickaxe tag in the JAR are byte-equal to the tree", gbad[:5])
        ck("V12.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        ck("V12.en_us", "assets/hbmsntm/lang/en_us.json" in names and jar.read("assets/hbmsntm/lang/en_us.json") == st.files[EN], "en_us.json in the JAR equals the generated file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_block_entity, inp, st)
    guarded(ck, "V3", v3_block, inp, st)
    guarded(ck, "V4", v4_base_console_tool, inp, st)
    guarded(ck, "V5", v5_keybinds, inp, st)
    guarded(ck, "V6", v6_renderer, inp, st)
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
        ("speed_005_to_004", "V2.", t(CBE, "private static final double speed = 0.05D;", "private static final double speed = 0.04D;")),
        ("lift_down_004_to_005", "V2.", t(CBE, "progress -= 0.04D;", "progress -= 0.05D;")),
        ("lift_up_004_to_005", "V2.", t(CBE, "progress += 0.04D;", "progress += 0.05D;")),
        ("center_y_plus1_to_plus2", "V2.", t(CBE, "RBMKDials.getColumnHeight() + 1;", "RBMKDials.getColumnHeight() + 2;")),
        ("girder_plus6_to_plus5", "V2.", t(CBE, "int girderY = centerY + 6;", "int girderY = centerY + 5;")),
        ("room_max_16_to_15", "V2.", t(CBE, "this.spanF = this.findRoomExtent(x, girderY, z, dir, 16);", "this.spanF = this.findRoomExtent(x, girderY, z, dir, 15);")),
        ("room_i_minus_1_to_i", "V2.", t(CBE, "return i - 1;", "return i;")),
        ("height_7_to_6", "V2.", t(CBE, "this.height = 7;", "this.height = 6;")),
        ("rotation_chain_ccw", "V2.", t(CBE, "        dir = dir.getClockWise();\n        this.spanR", "        dir = dir.getCounterClockWise();\n        this.spanR")),
        ("find_core_null_guard_removed", "V2.", t(CBE, "if(core != null && this.level.getBlockEntity(core) instanceof RBMKBaseBlockEntity column)", "if(this.level.getBlockEntity(core) instanceof RBMKBaseBlockEntity column)")),
        ("unlinked_guard_removed", "V2.", t(CBE, "if(this.level == null || !this.setUpCrane) return null;", "if(this.level == null) return null;")),
        ("loaded_guard_removed", "V2.", T(CBE, lambda x: drop_line(x, "if(!this.level.isLoaded(pos)) return null;"))),
        ("clamp_bounds_swapped", "V2.", t(CBE, "posFront = Mth.clamp(posFront, -spanB, spanF);", "posFront = Mth.clamp(posFront, -spanF, spanB);")),
        ("network_250_to_50", "V2.", t(CBE, "this.networkPackNT(250);", "this.networkPackNT(50);")),
        ("box_height_2_to_3", "V2.", t(CBE, "this.worldPosition.getY() + 2,", "this.worldPosition.getY() + 3,")),
        ("keys_while_loading", "V2.", t(CBE, "if(!players.isEmpty() && !isCraneLoading()) {", "if(!players.isEmpty()) {")),
        ("tilt_30_to_45", "V2.", t(CBE, "tiltFront = 30 * front;", "tiltFront = 45 * front;")),
        ("sync_order_swapped", "V2.", t(CBE, "buf.writeInt(this.spanF);\n            buf.writeInt(this.spanB);", "buf.writeInt(this.spanB);\n            buf.writeInt(this.spanF);")),
        ("nbt_key_posfront_renamed", "V2.", t(CBE, 'tag.putDouble("posFront", posFront);', 'tag.putDouble("posfront", posFront);')),
        ("held_saved_always", "V2.", t(CBE, "if(!this.loadedItem.isEmpty()) {\n            tag.put(\"held\"", "if(true) {\n            tag.put(\"held\"")),
        ("indicator_10_to_5", "V2.", t(CBE, "aboveColumn.craneIndicator = 10;", "aboveColumn.craneIndicator = 5;")),
        ("render_box_finite", "V2.", t(CBE, "return AABB.INFINITE;", "return new AABB(this.worldPosition);")),
        ("client_key_any_player", "V2.", t(CBE, "return player == NuclearTechMod.proxy.me() && NuclearTechMod.proxy.getIsKeyPressed(key);", "return NuclearTechMod.proxy.getIsKeyPressed(key);")),
        ("dimensions_changed", "V3.", t(CBLK, "return new int[] {1, 0, 0, 0, 1, 1};", "return new int[] {1, 0, 0, 0, 2, 1};")),
        ("second_box_dropped", "V3.", T(CBLK, lambda x: drop_line(x, "MultiblockHandlerXR.fillSpace(level, pos.relative(dir, offset), EXTRA_DIMENSIONS, this, dir);"))),
        ("screwdriver_any_tool", "V3.", t(CBLK, "if(tool != ToolType.SCREWDRIVER) return false;", "")),
        ("strength_3_to_5", "V3.", t(NB, "new RBMKCraneConsoleBlock(BlockBehaviour.Properties.of().noOcclusion().strength(3.0F, 30.0F)", "new RBMKCraneConsoleBlock(BlockBehaviour.Properties.of().noOcclusion().strength(5.0F, 30.0F)")),
        ("decrement_removed", "V4.", T(BASE, lambda x: drop_line(x, "if(this.craneIndicator > 0) this.craneIndicator--;"))),
        ("sync_byte_before_heat", "V4.", t(BASE, "buf.writeDouble(this.heat);\n        buf.writeByte((byte) this.craneIndicator);", "buf.writeByte((byte) this.craneIndicator);\n        buf.writeDouble(this.heat);")),
        ("indicator_saved", "V4.", t(BASE, 'tag.putDouble("heat", this.heat);', 'tag.putDouble("heat", this.heat);\n        tag.putInt("craneIndicator", this.craneIndicator);')),
        ("console_indicator_zero", "V4.", t(CONS, '(byte) rbmk.craneIndicator);', '(byte) 0);')),
        ("tool_without_has_position", "V4.", t(TOOL, "b instanceof RBMKCraneConsoleBlock crane && hasPosition(stack)", "b instanceof RBMKCraneConsoleBlock crane")),
        ("storage_code_changed", "V4.", t(STORAGE, "return this.slots.get(11).isEmpty() && toLoad.getItem() instanceof RBMKRodItem;", "return this.slots.get(11).isEmpty();")),
        ("enum_order_swapped", "V5.", t(KB, "        CRANE_UP,\n        CRANE_DOWN,", "        CRANE_DOWN,\n        CRANE_UP,")),
        ("keymapping_default_w", "V5.", t(KB, "InputConstants.Type.KEYSYM, InputConstants.KEY_UP, category);", "InputConstants.Type.KEYSYM, InputConstants.KEY_W, category);")),
        ("keymapping_not_registered", "V5.", T(KB, lambda x: drop_line(x, "event.register(CRANE_LOAD);"))),
        ("mirror_line_back", "V5.", t(KB, "                clientKeysPressed[key.ordinal()] = current;\n", "                clientKeysPressed[key.ordinal()] = current;\n                HbmPlayerAttachments.setKeyPressed(player, key, current);\n")),
        ("existing_mapping_changed", "V5.", t(KB, "InputConstants.Type.KEYSYM, InputConstants.KEY_N, category);", "InputConstants.Type.KEYSYM, InputConstants.KEY_M, category);")),
        ("server_proxy_true", "V5.", t(SP, "public boolean getIsKeyPressed(HbmKeybinds.EnumKeybind key) {\n        return false;", "public boolean getIsKeyPressed(HbmKeybinds.EnumKeybind key) {\n        return true;")),
        ("receiver_touched", "V5.|V10.", T(KR, lambda x: x + "\n")),
        ("lift_325_to_3", "V6.", t(CREND, "-3.25D * (1 -", "-3D * (1 -")),
        ("lamp_colour_changed", "V6.", t(CREND, "RenderContext.setColor(0.8F, 0.8F, 0F, 1F);", "RenderContext.setColor(0.8F, 0.8F, 0.2F, 1F);")),
        ("facing_switch_swapped", "V6.", t(CREND, "case WEST -> teFacing = 180;", "case WEST -> teFacing = 0;")),
        ("part_name_typo_fixed", "V6.", t(CREND, 'ResourceManager.rbmk_crane_console.renderPart("Console_Coonsole");\n\n        RenderContext.pushPose();', 'ResourceManager.rbmk_crane_console.renderPart("Console_Console");\n\n        RenderContext.pushPose();')),
        ("item_scale_35_to_3", "V6.", t(CREND, "RenderContext.scale(3.5F, 3.5F, 3.5F);", "RenderContext.scale(3F, 3F, 3F);")),
        ("ber_removed", "V6.|V7.", T(CP, lambda x: drop_line(x, "NtmBlockEntityTypes.RBMK_CRANE_CONSOLE.get(), new RenderCraneConsole()"))),
        ("recipe_pattern_changed", "V7.", gen_edit(G_REC, lambda d: d.__setitem__("pattern", ["BDC", "DDD"]))),
        ("recipe_count_2", "V7.", gen_edit(G_REC, lambda d: d["result"].__setitem__("count", 2))),
        ("creative_tab_moved", "V7.", t(CTAB, "output.accept(NtmBlocks.RBMK_CONSOLE);\n                        output.accept(NtmBlocks.RBMK_CRANE_CONSOLE);", "output.accept(NtmBlocks.RBMK_CRANE_CONSOLE);\n                        output.accept(NtmBlocks.RBMK_CONSOLE);")),
        ("item_model_cube", "V7.", gen_edit(G_IM, lambda d: d.__setitem__("parent", "hbmsntm:block/rbmk_crane_console_particle"))),
        ("en_value_changed", "V8.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("hbmsntm.keys.craneLoad", "Load Crane")))),
        ("en_other_key_changed", "V8.", lambda st: st.set_text(EN, json_edit(st.text(EN), lambda d: d.__setitem__("block.hbmsntm.rbmk_blank", "X")))),
        ("zh_value_changed", "V8.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("hbmsntm.keys.craneMoveUp", "向上移动起重机")))),
        ("map_source_zh_changed", "V8.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["block.hbmsntm.rbmk_crane_console"].__setitem__("source_zh", "X")))),
        ("resource_byte_flip", "V9.", Bx(IMPORT_PATHS[2], flip_byte)),
        ("obj_byte_flip", "V9.", Bx(IMPORT_PATHS[1], flip_byte)),
        ("unrelated_src_file", "V10.", lambda st: st.set_bytes(J + "items/Stray.java", b"class Stray {}")),
        ("rod_file_touched", "V10.", T(J + "blockentity/machine/rbmk/RBMKRodBlockEntity.java", lambda x: x + "\n")),
        ("orig_speed_line", "V1.|V2.", OE("te", lambda x: rep1(x, "private static final double speed = 0.05D;", "private static final double speed = 0.1D;"))),
        ("orig_step_line", "V1.|V2.", OE("te", lambda x: rep1(x, "progress -= 0.04D;", "progress -= 0.02D;"))),
        ("orig_line_moved", "V1.", OE("te", lambda x: rep1(x, "\tprivate static final double speed = 0.05D;", "\n\tprivate static final double speed = 0.05D;"))),
        ("orig_height_line", "V1.|V2.", OE("te", lambda x: rep1(x, "this.height = 7;", "this.height = 8;"))),
        ("orig_recipe_row", "V1.|V7.", OE("cm", lambda x: rep1(x, '"BCD", "DDD", \'B\', B.ingot()', '"BDC", "DDD", \'B\', B.ingot()'))),
        ("orig_hardness", "V1.|V3.", OE("blk", lambda x: rep1(x, "this.setHardness(3F);", "this.setHardness(4F);"))),
        ("gt_marker_changed", "V11.", t(GT, 'TAG = "[hbm-rbmk-crane]"', 'TAG = "[hbm-rbmk]"'), GT),
        ("gt_batch_shared", "V11.", t(GT, 'batch = "rbmk_crane_recipe"', 'batch = "rbmk_crane_keys"'), GT),
        ("gt_speed_from_neo", "V11.", t(GT, "ORIGINAL_SPEED = 0.05D;", "ORIGINAL_SPEED = 0.04D;"), GT),
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
    out.setdefault("V12", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V12" and not items:
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
        extra["gametest_log"] = guarded(ck, "V11", v11_log, inp, st, args.gametest_log)
    else:
        ck.pending("V11.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
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
