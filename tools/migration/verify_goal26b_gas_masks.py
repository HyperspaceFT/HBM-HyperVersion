"""Verify the Goal26B batch statically: the NEO armor foundation (NtmArmorMaterials.RAGS), the four gas masks (GasMaskItem), the two rag masks
(ModArmorItem), the five filters (GasMaskFilterItem), the rags (RagItem), their client models and helmet overlay, recipes, sound, language and
the 34 imported resources; the scope of the batch and the GameTest source; with --gametest-log the GameTest log; with --jar the packaged JAR.

Read-only for both worktrees. Writes only build/migration/goal26b/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 8954b531.
- V1  The original parsed at the cited lines (ArmorUtil, ArmorGasMask, ItemFilter, ItemRag, ModItemsArmor, ModArmor, the recipes, the assembly row,
      NTMSounds, sounds.json, the two models, the language files); a moved line fails.
- V2  NEO source against V1: hazard registrations, blacklists, durability, the armor material, worn textures, the overlay frame formula and
      prefixes, both models' box data and render scales, the client boundary, the server guards, the files that must stay byte-equal.
- V3  Generated resources: the 14 recipe JSONs against the original rows, 15 item models, sounds.json, en_us.json (18 keys), ass.filtercoal.
- V4  Language: zh_cn.json and the mapping (16 upstream + 2 local), CRLF, insert-only against the start copies.
- V5  Resources: the 34 imports byte-equal to the original working tree, the four renames, the ownership record, every referenced texture exists.
- V6  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch (tools/ listed separately).
- V7  GameTest source (GasMaskGameTests) and with --gametest-log the log.
- V8  (--jar) the packaged JAR; "not run" without the flag.
- V9  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal26b_gas_masks.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal26b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "8954b53116965d964e2becdf2cee6b985b8e3356"

J = "src/main/java/com/hbm/"
MAT = J + "registry/NtmArmorMaterials.java"
GMI = J + "items/armor/GasMaskItem.java"
MAI = J + "items/armor/ModArmorItem.java"
FIL = J + "items/tools/GasMaskFilterItem.java"
RAGI = J + "items/special/RagItem.java"
MGM = J + "render/model/armor/ModelGasMask.java"
M65 = J + "render/model/armor/ModelM65.java"
EXT = J + "render/item/GasMaskClientExtensions.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "GasMaskGameTests.java"
MOD = J + "main/NuclearTechMod.java"
CLIENT = J + "main/NuclearTechModClient.java"
AU = J + "util/ArmorUtil.java"
ITEMS = J + "items/NtmItems.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
ASM = J + "inventory/recipes/AssemblyMachineRecipes.java"
SND = J + "registry/NtmSoundEvents.java"
SNDP = J + "datagen/NtmSoundDefinitionsProvider.java"
IMP = J + "datagen/NtmItemModelProvider.java"
RECP = J + "datagen/NtmRecipeProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
NEW_CLASSES = [MAT, GMI, MAI, FIL, RAGI, MGM, M65, EXT, GT]
EDITED = [MOD, CLIENT, AU, ITEMS, CTAB, ASM, SND, SNDP, IMP, RECP, LP]
COMMON = [GMI, MAI, FIL, RAGI, AU, ITEMS, MAT]
UNCHANGED = ["src/main/java/api/hbm/item/IGasMask.java", J + "util/ArmorRegistry.java", J + "handler/HazmatRegistry.java", J + "handler/ArmorModHandler.java",
             J + "items/armor/ArmorNo9.java", J + "hazard/type/HazardTypeAsbestos.java", J + "hazard/type/HazardTypeCoal.java", J + "blocks/gas/GasMonoxideBlock.java",
             J + "blocks/gas/GasRadonBlock.java", J + "hazard/HazardRegistry.java", GT_DIR + "RadiationControlGameTests.java", GT_DIR + "HazardGameTests.java",
             GT_DIR + "SmokeTestSupport.java", GT_DIR + "SmokeGameTests.java"]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal26b-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
SOUNDS = GEN + "assets/hbmsntm/sounds.json"
RES = "src/main/resources/assets/hbmsntm/"
JARRES = "src/main/resources/"
O_RES = "src/main/resources/assets/hbm/"

O = "src/main/java/com/hbm/"
O_FILES = dict(au=O + "util/ArmorUtil.java", gm=O + "items/armor/ArmorGasMask.java", filt=O + "items/tool/ItemFilter.java", rag=O + "items/special/ItemRag.java",
               mia=O + "items/ModItemsArmor.java", mi=O + "items/ModItems.java", ma=O + "items/armor/ModArmor.java", ar=O + "crafting/ArmorRecipes.java",
               cr=O + "crafting/ConsumableRecipes.java", asm=O + "inventory/recipes/AssemblyMachineRecipes.java", cm=O + "main/CraftingManager.java",
               sm=O + "crafting/SmeltingRecipes.java", snd=O + "main/NTMSounds.java", mgm=O + "render/model/ModelGasMask.java", m65=O + "render/model/ModelM65.java",
               sj="src/main/resources/assets/hbm/sounds.json")
O_LANG = "src/main/resources/assets/hbm/lang/"

# V1: every cited original line, {file key: {line: needle}}
ANCHORS = {
    "au": {39: "registerHazard(ModItems.gas_mask_filter,", 40: "registerHazard(ModItems.gas_mask_filter_mono,", 41: "registerHazard(ModItems.gas_mask_filter_combo,",
           42: "registerHazard(ModItems.gas_mask_filter_rag,", 43: "registerHazard(ModItems.gas_mask_filter_piss,", 45: "registerHazard(ModItems.gas_mask,",
           46: "registerHazard(ModItems.gas_mask_m65,", 47: "registerHazard(ModItems.mask_rag,", 48: "registerHazard(ModItems.mask_piss,",
           248: 'FILTERK_KEY = "hfrFilter"', 347: "filter.setItemDamage(filter.getItemDamage() + damage);", 349: "if(filter.getItemDamage() > filter.getMaxDamage())",
           363: 'list.add(EnumChatFormatting.RED + "No filter installed!");', 364: "return;", 367: 'list.add(EnumChatFormatting.GOLD + "Installed filter:");',
           374: "if(max > 0) {", 375: 'append = " (" + ((max - meta) * 100 / max) + "%)";', 379: 'list.add("  " + filter.getDisplayName() + append);',
           381: "ForgeEventFactory.onItemTooltip(filter, player, lore, ext);", 382: 'lore.forEach(x -> list.add(EnumChatFormatting.YELLOW + "  " + x));'},
    "gm": {42: "overlay_goggles_0.png", 47: "overlay_goggles_5.png", 51: "overlay_gasmask_0.png", 56: "overlay_gasmask_5.png", 60: "super(ArmorMaterial.IRON, 0, 0);",
           67: "if(this == ModItems.gas_mask) {", 76: "if(this == ModItems.gas_mask_m65 || this == ModItems.gas_mask_olde || this == ModItems.gas_mask_mono) {",
           91: "if(stack.getItem() == ModItems.gas_mask) {", 92: 'return "hbm:textures/models/GasMask.png";', 94: "if(stack.getItem() == ModItems.gas_mask_m65) {",
           95: 'return "hbm:textures/models/ModelM65.png";', 97: "if(stack.getItem() == ModItems.gas_mask_olde) {", 98: 'return "hbm:textures/armor/mask_olde.png";',
           100: "if(stack.getItem() == ModItems.gas_mask_mono) {", 101: 'return "hbm:textures/models/ModelM65Mono.png";',
           112: "if(this == ModItems.goggles || this == ModItems.gas_mask_m65) {", 113: "int index = (int) ((double) stack.getItemDamage() / (double) stack.getMaxDamage() * 6D);",
           114: "tex = this.googleBlur[Math.min(index, 5)];", 117: "if(this == ModItems.gas_mask) {", 118: "* 6D);", 119: "tex = this.maskBlur[Math.min(index, 5)];",
           130: "OpenGlHelper.glBlendFunc(770, 771, 1, 0);", 136: "-90.0D, 0.0D, 1.0D);",
           150: "if(this == ModItems.gas_mask_mono) {", 151: "HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA", 153: "{HazardClass.GAS_BLISTERING}",
           175: "ArmorUtil.addGasMaskTooltip(stack, player, list, ext);", 180: 'list.add(EnumChatFormatting.RED + I18nUtil.resolveKey("hazard.neverProtects"));',
           183: 'list.add(EnumChatFormatting.DARK_RED + " -" + I18nUtil.resolveKey(clazz.lang));', 189: "public boolean isFilterApplicable(", 190: "return true;",
           196: "if(player.isSneaking()) {", 198: "ItemStack filter = this.getFilter(stack, player);", 201: "ArmorUtil.removeFilter(stack);",
           203: "if(!player.inventory.addItemStackToInventory(filter)) {", 204: "player.dropPlayerItemWithRandomChoice(filter, true);", 207: "return stack;",
           211: "return super.onItemRightClick(stack, world, player);"},
    "filt": {17: "this.setMaxDamage(20000);", 18: "this.setCreativeTab(MainRegistry.consumableTab);", 19: "this.setMaxStackSize(1);",
             25: "ItemStack helmet = player.inventory.armorItemInSlot(3);", 27: "if(helmet == null)", 30: "if(!(helmet.getItem() instanceof IGasMask)) {",
             32: "if(ArmorModHandler.hasMods(helmet)) {", 35: "if(mods[ArmorModHandler.helmet_only] != null) {", 38: "ItemStack ret = installFilterOn(mask, stack, world, player);",
             39: "ArmorModHandler.applyMod(helmet, mask);", 45: "return installFilterOn(helmet, stack, world, player);", 50: "if(!(helmet.getItem() instanceof IGasMask)) {",
             55: "if(!mask.isFilterApplicable(helmet, player, filter))", 58: "ItemStack copy = filter.copy();", 59: "ItemStack current = ArmorUtil.getGasMaskFilter(helmet);",
             62: "filter = current;", 64: "filter.stackSize = 0;", 67: "ArmorUtil.installGasMaskFilter(helmet, copy);",
             69: "world.playSoundAtEntity(player, NTMSounds.FILTER_SCREW, 1.0F, 1.0F);"},
    "rag": {20: "if(entityItem != null && !entityItem.worldObj.isRemote) {", 23: "getMaterial() == Material.water) {",
            25: "entityItem.setEntityItemStack(new ItemStack(ModItems.rag_damp, stack.stackSize));", 26: "return true;", 34: "stack.stackSize--;",
            35: "player.inventory.addItemStackToInventory(new ItemStack(ModItems.rag_piss));", 41: 'I18nUtil.resolveKeyArray("item.rag.desc");'},
    "mia": {22: 'EnumHelper.addArmorMaterial("HBM_RAGS", 150, new int[] { 1, 1, 1, 1 }, 0);', 23: "aMatRags.customCraftingMaterial = ModItems.rag;",
            27: 'gas_mask = new ArmorGasMask().setUnlocalizedName("gas_mask").setMaxStackSize(1)', 28: 'gas_mask_m65 = new ArmorGasMask().setUnlocalizedName("gas_mask_m65").setMaxStackSize(1)',
            29: 'gas_mask_mono = new ArmorGasMask().setUnlocalizedName("gas_mask_mono").setMaxStackSize(1)', 30: 'gas_mask_olde = new ArmorGasMask().setUnlocalizedName("gas_mask_olde").setMaxStackSize(1)',
            31: 'mask_rag = new ModArmor(aMatRags, 0).setUnlocalizedName("mask_rag").setMaxStackSize(1)', 32: 'mask_piss = new ModArmor(aMatRags, 0).setUnlocalizedName("mask_piss").setMaxStackSize(1)'},
    "mi": {2398: 'rag = new ItemRag().setUnlocalizedName("rag")', 2399: 'rag_damp = new Item().setUnlocalizedName("rag_damp")', 2400: 'rag_piss = new Item().setUnlocalizedName("rag_piss")',
           2401: 'filter_coal = new Item().setUnlocalizedName("filter_coal")', 2838: 'gas_mask_filter = new ItemFilter()', 2839: 'gas_mask_filter_mono = new ItemFilter()',
           2840: 'gas_mask_filter_combo = new ItemFilter()', 2841: 'gas_mask_filter_rag = new ItemFilter()', 2842: 'gas_mask_filter_piss = new ItemFilter()'},
    "ma": {66: "if(stack.getItem().equals(ModItems.mask_rag)) {", 67: 'return (RefStrings.MODID + ":textures/armor/rag_damp.png");',
           69: "if(stack.getItem().equals(ModItems.mask_piss)) {", 70: 'return (RefStrings.MODID + ":textures/armor/rag_piss.png");'},
    "ar": {154: "new ItemStack(ModItems.gas_mask, 1)", 155: "new ItemStack(ModItems.gas_mask_m65, 1)", 156: "new ItemStack(ModItems.gas_mask_olde, 1)",
           157: "new ItemStack(ModItems.gas_mask_mono, 1)", 160: "new ItemStack(ModItems.mask_rag, 1)", 161: "new ItemStack(ModItems.mask_piss, 1)"},
    "cr": {217: "new ItemStack(ModItems.gas_mask_filter, 1)", 218: "new ItemStack(ModItems.gas_mask_filter_mono, 1)", 219: "new ItemStack(ModItems.gas_mask_filter_combo, 1)",
           220: "new ItemStack(ModItems.gas_mask_filter_rag, 1)", 221: "new ItemStack(ModItems.gas_mask_filter_piss, 1)"},
    "asm": {122: 'this.register(new GenericRecipe("ass.filtercoal").setup(50, 100).outputItems(new ItemStack(ModItems.filter_coal, 1))',
            123: ".inputItems(new OreDictStack(COAL.dust(), 4), new ComparableStack(Items.string, 2), new ComparableStack(Items.paper, 1)));"},
    "cm": {839: "addRecipeAuto(new ItemStack(ModItems.rag, 4), new Object[] { \"SW\", \"WS\", 'S', Items.string, 'W', Blocks.wool });"},
    "sm": {118: "GameRegistry.addSmelting(ModItems.rag_damp, new ItemStack(ModItems.rag), 0.1F);", 119: "GameRegistry.addSmelting(ModItems.rag_piss, new ItemStack(ModItems.rag), 0.1F);"},
    "snd": {137: 'public static final String FILTER_SCREW = "hbm:item.gasmaskScrew";'},
    "sj": {114: '"item.gasmaskScrew": {"category": "player", "sounds": [{"name": "tool/gasmaskScrew", "stream": false}]},'},
    "mgm": {27: "this.textureWidth = 64;", 28: "this.textureHeight = 32;", 99: "GL11.glScalef(1.5F / f6, 1.5F / f6, 1.5F / f6);", 100: "GL11.glTranslatef(0.0F, 16.0F * scaleFactor, 0.0F);",
            103: "GL11.glScalef(1.15F, 1.15F, 1.15F);", 105: "this.mask.render(scaleFactor);"},
    "m65": {25: "this.textureWidth = 32;", 26: "this.textureHeight = 32;", 28: "float yOffset = 0.5F;", 134: "double d = 1D / 16D * 18D;", 138: "double d = 1D / 16D * 18D;",
            142: "GL11.glScaled(1.01D, 1.01D, 1.01D);", 144: "ArmorUtil.getGasMaskFilterRecursively(((EntityLivingBase)entity).getEquipmentInSlot(4), (EntityLivingBase)entity) != null)",
            145: "this.filter.render(scaleFactor);"},
}

# V3/V4: (NEO key, original key, en_US.lang line, zh_CN.lang line)
UP = [("item.hbmsntm.filter_coal", "item.filter_coal.name", 2809, 2431), ("item.hbmsntm.gas_mask", "item.gas_mask.name", 2886, 2506),
      ("item.hbmsntm.gas_mask_filter", "item.gas_mask_filter.name", 2887, 2507), ("item.hbmsntm.gas_mask_filter_combo", "item.gas_mask_filter_combo.name", 2888, 2508),
      ("item.hbmsntm.gas_mask_filter_mono", "item.gas_mask_filter_mono.name", 2889, 2509), ("item.hbmsntm.gas_mask_filter_piss", "item.gas_mask_filter_piss.name", 2890, 2510),
      ("item.hbmsntm.gas_mask_filter_rag", "item.gas_mask_filter_rag.name", 2891, 2511), ("item.hbmsntm.gas_mask_m65", "item.gas_mask_m65.name", 2892, 2512),
      ("item.hbmsntm.gas_mask_mono", "item.gas_mask_mono.name", 2893, 2513), ("item.hbmsntm.gas_mask_olde", "item.gas_mask_olde.name", 2894, 2514),
      ("item.hbmsntm.mask_piss", "item.mask_piss.name", 3308, 2844), ("item.hbmsntm.mask_rag", "item.mask_rag.name", 3309, 2845),
      ("item.hbmsntm.rag", "item.rag.name", 4159, 3595), ("item.hbmsntm.rag.desc", "item.rag.desc", 4160, 6065), ("item.hbmsntm.rag_damp", "item.rag_damp.name", 4161, 3596),
      ("item.hbmsntm.rag_piss", "item.rag_piss.name", 4162, 3597)]
# local keys: (NEO key, original ArmorUtil.java line with the hard-coded English)
LOCAL = [("hazard.no_filter", 363), ("hazard.filter_installed", 367)]
NEW_KEYS = [u[0] for u in UP] + [k for k, _ in LOCAL]

ITEM_IDS = ["gas_mask", "gas_mask_m65", "gas_mask_mono", "gas_mask_olde", "mask_rag", "mask_piss", "gas_mask_filter", "gas_mask_filter_mono", "gas_mask_filter_combo",
            "gas_mask_filter_rag", "gas_mask_filter_piss", "filter_coal", "rag", "rag_damp", "rag_piss"]
MASK_TYPE = {"GAS_MASK": "gas_mask", "M65": "gas_mask_m65", "MONO": "gas_mask_mono", "OLDE": "gas_mask_olde"}
RENAMES = {"textures/models/GasMask.png": "textures/models/gas_mask.png", "textures/models/ModelM65.png": "textures/models/model_m65.png",
           "textures/models/ModelM65Mono.png": "textures/models/model_m65_mono.png", "sounds/tool/gasmaskScrew.ogg": "sounds/tool/gasmask_screw.ogg"}
# the 34 imports (original path under assets/hbm -> NEO path under assets/hbmsntm), independent of the import script
IMPORTS = [(f"textures/items/{i}.png", f"textures/item/{i}.png") for i in ITEM_IDS] + [(o, n) for o, n in RENAMES.items() if o.startswith("textures")] + \
          [(f"textures/armor/{n}.png", f"textures/armor/{n}.png") for n in ("mask_olde", "rag_damp", "rag_piss")] + \
          [(f"textures/misc/overlay_{k}_{i}.png", f"textures/misc/overlay_{k}_{i}.png") for k in ("gasmask", "goggles") for i in range(6)] + \
          [("sounds/tool/gasmaskScrew.ogg", "sounds/tool/gasmask_screw.ogg")]
RES_PATHS = [RES + n for _, n in IMPORTS]

R = "hbmsntm:"
EXPR = {"KEY_ANYPANE": {"tag": "c:glass_panes"}, "STEEL.plate()": {"tag": "c:plates/steel"}, "IRON.plate()": {"item": R + "plate_iron"},
        "ANY_RUBBER.ingot()": {"tag": "ntm:any_rubbers"}, "Items.leather": {"item": "minecraft:leather"}, "IRON.ingot()": {"tag": "c:ingots/iron"},
        "ModItems.rag_damp": {"item": R + "rag_damp"}, "ModItems.rag_piss": {"item": R + "rag_piss"}, "ModItems.filter_coal": {"item": R + "filter_coal"},
        "ZR.nugget()": {"item": R + "nugget_zirconium"}, "ZR.ingot()": {"item": R + "ingot_zirconium"}, "ModItems.catalyst_clay": {"item": R + "catalyst_clay"},
        "ModItems.gas_mask_filter": {"item": R + "gas_mask_filter"}, "Items.string": {"item": "minecraft:string"}, "Blocks.wool": {"tag": "minecraft:wool"}}
# (NEO recipe id, original file key, line, advancement folder)
RECIPES = [("gas_mask", "ar", 154, "combat"), ("gas_mask_m65", "ar", 155, "combat"), ("gas_mask_olde", "ar", 156, "combat"), ("gas_mask_mono", "ar", 157, "combat"),
           ("mask_rag", "ar", 160, "combat"), ("mask_piss", "ar", 161, "combat"), ("gas_mask_filter", "cr", 217, "combat"), ("gas_mask_filter_mono", "cr", 218, "combat"),
           ("gas_mask_filter_combo", "cr", 219, "combat"), ("gas_mask_filter_rag", "cr", 220, "combat"), ("gas_mask_filter_piss", "cr", 221, "combat"), ("rag", "cm", 839, "misc")]
SMELT = [("rag_from_smelting_rag_damp", 118), ("rag_from_smelting_rag_piss", 119)]
RECIPE_DIR = GEN + "data/hbmsntm/recipe/"
ADV_ROOT = GEN + "data/hbmsntm/advancement/recipes/"
GEN_NEW = [f"{GEN}assets/hbmsntm/models/item/{i}.json" for i in ITEM_IDS] + [f"{RECIPE_DIR}{r[0]}.json" for r in RECIPES] + [f"{RECIPE_DIR}{s[0]}.json" for s in SMELT] + \
          [f"{ADV_ROOT}{r[3]}/{r[0]}.json" for r in RECIPES] + [f"{ADV_ROOT}misc/{s[0]}.json" for s in SMELT]
GEN_MODIFIED = [STAMP, SOUNDS, EN]

GT_MARK = "[hbm-gas-mask]"
START_GAMETESTS = 257
GT_TESTS = ("protection_classes", "hazards", "filter_use", "mask_sneak_remove", "filter_wear", "filter_persistence", "rags", "recipes", "items_and_durability")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                 "migration/GOAL26.md", "migration/GOAL26B.md", "migration/GOAL26B-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal26b-",)


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


# ---------------------------------------------------------------- text helpers (as verify_goal26a_radiation_control.py)

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
    o, c, code = method_span(lf(text), signature)
    return sq(code[o + 1:c])


@functools.lru_cache(maxsize=128)
def code_cached(text):
    return sq(blank_comments(text))


def code_of(text):
    return code_cached(lf(text))


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def parse_lang(text):
    d = {}
    for i, l in enumerate(lf(text).lstrip("﻿").split("\n"), 1):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            d.setdefault(k, []).append((v.rstrip("\r"), i))
    return d


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:120] if n <= len(lines) else None) for n, needle in expected.items() if n > len(lines) or needle not in lines[n - 1]]


def ordered(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def missing_order(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return f
        pos = i + len(f)
    return None


def num(expr, env=None):
    """Evaluate a numeric Java expression (suffixes already dropped by sq) with the given names; None if it does not evaluate."""
    e = expr
    for k, v in (env or {}).items():
        e = re.sub(rf"\b{k}\b", f"({v})", e)
    if not re.fullmatch(r"[\d.+\-*/() ]+", e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))  # noqa: S307 - digits and operators only (checked above)
    except Exception:  # noqa: BLE001
        return None


def nums(args, env=None):
    return [num(a, env) for a in args.split(",")]


def close(a, b):
    return len(a) == len(b) and all(x is not None and y is not None and abs(x - y) < 1e-6 for x, y in zip(a, b))


class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src and migration, the GameTest log."""

    def __init__(self, files, tree, log_text=None):
        self.files, self.tree, self.log_text = files, tree, log_text
        self.orig_edits = {}

    def copy(self):
        return State(dict(self.files), dict(self.tree), self.log_text)

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
    try:
        inp.neo_head = git(ROOT, "rev-parse", "HEAD").decode("utf-8").strip()
    except Exception as error:  # noqa: BLE001
        inp.neo_head = repr(error)
    inp.o = {name: lf(read_text(ORIGINAL / path)) for name, path in O_FILES.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    tree = hash_tree()
    files = {}
    gen_all = [p for p in tree if p.startswith(GEN) and p not in inp.base_files]
    load = set(NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, OWN, EN, STAMP, SOUNDS] + RES_PATHS + GEN_NEW + gen_all)
    load |= {RES + f"textures/item/{i}.png" for i in ITEM_IDS}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.o_res = {}
    for orig, neo in IMPORTS:
        f = ORIGINAL / (O_RES + orig)
        inp.o_res[RES + neo] = f.read_bytes() if f.exists() else None
    inp.gt_other = {p.name: read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name}
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, tree)


def oline(inp, key, n):
    return sq(blank_comments(inp.ol[key][n - 1]))


def olines(inp, key, first, last):
    return sq(blank_comments("\n".join(inp.ol[key][first - 1:last])))


def onum(inp, key, n, pattern):
    m = re.search(pattern, oline(inp, key, n))
    return m[1] if m else None


# ---------------------------------------------------------------- original parsers

HAZ_ORIG = re.compile(r"ArmorRegistry\.registerHazard\(ModItems\.(\w+),(.*)\);")
HAZ_NEO = re.compile(r"ArmorRegistry\.registerHazard\(NtmItems\.(\w+)\.get\(\),(.*?)\);")


def classes(text):
    return [c.replace("HazardClass.", "") for c in text.split(",")]


def orig_hazards(inp):
    out = []
    for n in list(range(39, 44)) + list(range(45, 49)):
        m = HAZ_ORIG.search(oline(inp, "au", n))
        out.append((m[1], classes(m[2])) if m else (None, n))
    return out


def orig_blacklists(inp):
    """{original item: [classes]}: mono from :150-151, every other ArmorGasMask from :153."""
    mono_item = onum(inp, "gm", 150, r"this==ModItems\.(\w+)\)")
    mono = re.search(r"newHazardClass\[\]\{([^}]*)\}", oline(inp, "gm", 151))
    other = re.search(r"newHazardClass\[\]\{([^}]*)\}", oline(inp, "gm", 153))
    return mono_item, classes(mono[1]) if mono else None, classes(other[1]) if other else None


def orig_textures(inp):
    out = {}
    for n in (91, 94, 97, 100):
        item = onum(inp, "gm", n, r"stack\.getItem\(\)==ModItems\.(\w+)\)")
        path = onum(inp, "gm", n + 1, r'return"hbm:([^"]+)";')
        out[item] = path
    return out


def orig_overlays(inp):
    """{item: frame prefix} from the arrays (:41-57) and the item checks (:112-119)."""
    google = re.findall(r"textures/misc/(overlay_\w+_)(\d)\.png", olines(inp, "gm", 41, 48))
    mask = re.findall(r"textures/misc/(overlay_\w+_)(\d)\.png", olines(inp, "gm", 50, 57))
    out = {}
    items = re.findall(r"ModItems\.(\w+)", oline(inp, "gm", 112))
    if "googleBlur" in oline(inp, "gm", 114):
        for i in items:
            out[i] = (google[0][0] if google else None, len(google))
    m = onum(inp, "gm", 117, r"this==ModItems\.(\w+)\)")
    if "maskBlur" in oline(inp, "gm", 119):
        out[m] = (mask[0][0] if mask else None, len(mask))
    factor = onum(inp, "gm", 113, r"\*(\d+)\);")
    factor2 = onum(inp, "gm", 118, r"\*(\d+)\);")
    cap = onum(inp, "gm", 114, r"Math\.min\(index,(\d+)\)")
    cap2 = onum(inp, "gm", 119, r"Math\.min\(index,(\d+)\)")
    return out, (factor, factor2), (cap, cap2)


def orig_parts(inp, key):
    """[(parent, u, v, box[6], pivot[3], rot[3])] in source order, plus mirror-after-addBox flags and the texture size."""
    code = sq(blank_comments(inp.o[key]))
    env = {}
    y = re.search(r"floatyOffset=([\d.]+);", code)
    if y:
        env["yOffset"] = y[1]
    uv, box, piv, rot, parent, order, pos_box, pos_mirror = {}, {}, {}, {}, {}, [], {}, {}
    for m in re.finditer(r"(?:this\.|ModelRenderer)?(\w+)=newModelRenderer\(this,(\d+),(\d+)\);", code):
        uv[m[1]] = (int(m[2]), int(m[3]))
    for m in re.finditer(r"(?:this\.)?(\w+)\.addBox\(([^)]*)\);", code):
        box[m[1]] = nums(m[2], env)
        pos_box[m[1]] = m.start()
        order.append(m[1])
    for m in re.finditer(r"(?:this\.)?(\w+)\.setRotationPoint\(([^)]*)\);", code):
        piv[m[1]] = nums(m[2], env)
    for m in re.finditer(r"setRotation\((?:this\.)?(\w+),([^)]*)\);", code):
        rot[m[1]] = nums(m[2], env)
    for m in re.finditer(r"convertToChild\(this\.(\w+),(?:this\.)?(\w+)\);", code):
        parent[m[2]] = m[1]
    for m in re.finditer(r"(?:this\.)?(\w+)\.mirror=true;", code):
        pos_mirror[m[1]] = m.start()
    parts = [(parent.get(n), *uv.get(n, (None, None)), box.get(n), piv.get(n), rot.get(n)) for n in order]
    mirror_after = all(n in pos_mirror and pos_mirror[n] > pos_box[n] for n in order)
    tw = re.search(r"this\.textureWidth=(\d+);", code)
    th = re.search(r"this\.textureHeight=(\d+);", code)
    sizes = set(re.findall(r"\.setTextureSize\((\d+),(\d+)\);", code))
    return parts, mirror_after, (int(tw[1]) if tw else None, int(th[1]) if th else None), sizes


def render_ops(code, env):
    """[(op, [x, y, z])] for every scale / translate call in the render body, in source order."""
    ops = []
    for m in re.finditer(r"(?:GL11\.glScale[fd]|poseStack\.scale)\(([^;]*)\);|(?:GL11\.glTranslatef|poseStack\.translate)\(([^;]*)\);", code):
        if m[1] is not None:
            ops.append(("scale", nums(m[1], env)))
        else:
            ops.append(("translate", nums(m[2], env)))
    return ops


def orig_render(inp, key):
    sig = "public void render(Entity entity, float limbSwing, float limbSwingAmount, float ageInTicks, float netHeadYaw, float headPitch, float scaleFactor)"
    b = body(inp.o[key], sig)
    env = {"scaleFactor": "1/16"}
    f6 = re.search(r"floatf6=([\d.]+);", b)
    if f6:
        env["f6"] = f6[1]
    d = re.search(r"doubled=([\d./*]+);", b)
    if d:
        env["d"] = d[1]
    return render_ops(b, env)


NEO_PART = re.compile(r'(\w+)\.addOrReplaceChild\("(\w+)",CubeListBuilder\.create\(\)\.texOffs\((\d+),(\d+)\)((?:\.\w+\(\))*)\.addBox\(([^)]*)\),PartPose\.offsetAndRotation\(([^)]*)\)\);')


def neo_parts(text):
    code = code_of(text)
    env = {}
    y = re.search(r"Y_OFFSET=([\d.]+);", code)
    if y:
        env["Y_OFFSET"] = y[1]
    parts, extras = [], []
    for m in NEO_PART.finditer(code):
        a = nums(m[7], env)
        parts.append((m[1], int(m[3]), int(m[4]), nums(m[6], env), a[:3], a[3:]))
        if m[5]:
            extras.append((m[2], m[5]))
    size = re.search(r"LayerDefinition\.create\(mesh,(\d+),(\d+)\)", code)
    return parts, extras, (int(size[1]), int(size[2])) if size else None, code


def neo_render(text):
    b = body(text, "public void renderToBuffer(PoseStack poseStack, VertexConsumer buffer, int packedLight, int packedOverlay, int color)")
    env = {}
    f6 = re.search(r"floatf6=([\d.]+);", b)
    if f6:
        env["f6"] = f6[1]
    d = re.search(r"floatd=([\d./*]+);", b)
    if d:
        env["d"] = d[1]
    return render_ops(b, env), b


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == inp.baseline.get("copied_scope_count", len(inp.baseline["copied_scope"])) and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 8954b531", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 8954b531 (the batch is uncommitted)", inp.neo_head)
    needed = NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, EN, STAMP, SOUNDS] + GEN_NEW + RES_PATHS
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified, unchanged-reference and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in EDITED + [ZH, MAP, EN, SOUNDS] if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start copy of every edited file exists in baseline-files", starts)


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    haz = orig_hazards(inp)
    ck("V1.hazard-lines", all(h[0] for h in haz) and len(haz) == 9, "ArmorUtil.java:39-48 hold nine registerHazard lines (39-43, 45-48)", haz)
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", e is not None and len(e) == 1 and e[0][1] == en_line and z is not None and len(z) == 1 and z[0][1] == zh_line,
           f"{okey} once in en_US.lang:{en_line} and zh_CN.lang:{zh_line}", (e, z))
    for key in ("mgm", "m65"):
        parts, mirror_after, size, sizes = orig_parts(inp, key)
        want = 6 if key == "mgm" else 10
        ok = len(parts) == want and all(p[0] and p[1] is not None and p[3] and None not in p[3] and p[4] and None not in p[4] and p[5] and None not in p[5] for p in parts)
        ck(f"V1.{key}-parts", ok, f"{O_FILES[key].rsplit('/', 1)[1]}: {want} boxes parsed (texOffs, addBox, setRotationPoint, setRotation, parent)", parts)
        ck(f"V1.{key}-mirror-after-addbox", mirror_after, "every `.mirror = true` comes after its addBox (no box is mirrored in 1.7.10)")
        ck(f"V1.{key}-texture-size", sizes == {(str(size[0]), str(size[1]))}, f"texture size {size} on the model and every part", sizes)
    gops = orig_render(inp, "mgm")
    mops = orig_render(inp, "m65")
    ck("V1.render-ops", len(gops) == 3 and len(mops) == 5, "the two render bodies hold 3 (gas mask) and 5 (M65) scale / translate calls", (gops, mops))


# ---------------------------------------------------------------- V2 NEO source vs original

def v2_source(ck, inp, st):
    au = st.text(AU)
    reg = body(au, "public static void register()")
    ck("V2.diamond-line-first", reg.startswith("ArmorRegistry.registerHazard(Items.DIAMOND_HELMET,HazardClass.PARTICLE_COARSE,HazardClass.GAS_LUNG);"),
       "ArmorUtil.register still starts with the diamond helmet line (PARTICLE_COARSE, GAS_LUNG)")
    neo = [(m[1].lower(), classes(m[2])) for m in HAZ_NEO.finditer(reg)]
    ck("V2.hazard-registrations", neo == orig_hazards(inp), "the nine registerHazard lines match ArmorUtil.java:39-48 (items, classes and order)", (neo, orig_hazards(inp)))

    gm = st.text(GMI)
    gcode = code_of(gm)
    types = {m[1]: dict(tex=m[2], m65=m[3] == "true", prefix=None if m[4] == "null" else m[4].strip('"'), half=m[5] == "true")
             for m in re.finditer(r'(\w+)\("([^"]+)",(true|false),("[^"]*"|null),(true|false)\)[,;]', gcode)}
    items = code_of(st.text(ITEMS))
    reg_types = dict(re.findall(r'ITEMS\.register\("(\w+)",\(\)->newGasMaskItem\(GasMaskItem\.MaskType\.(\w+),', items))
    ck("V2.mask-types", reg_types == {v: k for k, v in MASK_TYPE.items()} and set(types) == set(MASK_TYPE), "the four GasMaskItem registrations use their own MaskType", (reg_types, list(types)))
    mono_item, mono, other = orig_blacklists(inp)
    bl = body(gm, "public ArrayList<HazardClass> getBlacklist(ItemStack stack, LivingEntity entity)")
    mb = re.fullmatch(r"if\(maskType\.halfMask\)\{returnnewArrayList<>\(List\.of\(([^)]*)\)\);\}else\{returnnewArrayList<>\(List\.of\(([^)]*)\)\);\}", bl)
    halves = [MASK_TYPE[k] for k, v in types.items() if v["half"]]
    ck("V2.blacklists", bool(mb) and classes(mb[1]) == mono and classes(mb[2]) == other and halves == [mono_item],
       f"getBlacklist: {mono_item} -> {mono}, the others -> {other}, a new list per call (ArmorGasMask.java:147-155)", (bl, halves))
    ck("V2.filter-applicable", body(gm, "public boolean isFilterApplicable(ItemStack stack, LivingEntity entity, ItemStack filter)") == "returntrue;",
       "isFilterApplicable always returns true (ArmorGasMask.java:189-191)")
    ck("V2.mask-material", "super(ArmorMaterials.IRON,ArmorItem.Type.HELMET,properties);" in gcode and onum(inp, "gm", 60, r"super\(ArmorMaterial\.(\w+),") == "IRON",
       "GasMaskItem is an IRON helmet (ArmorGasMask.java:60)")
    tex = orig_textures(inp)
    wrong = {i: (types.get(k, {}).get("tex"), tex.get(i)) for k, i in MASK_TYPE.items() if types.get(k, {}).get("tex") != RENAMES.get(tex.get(i), tex.get(i))}
    ck("V2.worn-textures", not wrong and "returnmaskType.texture;" in body(gm, "public ResourceLocation getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, ArmorMaterial.Layer layer, boolean innerModel)")
       and "this.texture=NuclearTechMod.withDefaultNamespace(texture);" in gcode, "the worn textures are ArmorGasMask.java:91-102 with the four lowercase renames", wrong)
    over, factors, caps = orig_overlays(inp)
    want_prefix = {i: p for i, (p, n) in over.items() if i in MASK_TYPE.values()}
    neo_prefix = {MASK_TYPE[k]: v["prefix"] for k, v in types.items() if v["prefix"]}
    ck("V2.overlay-prefix", neo_prefix == want_prefix and all(n == 6 for _, n in over.values()),
       "the overlay frames: gas_mask -> overlay_gasmask_, gas_mask_m65 -> overlay_goggles_, the others none (ArmorGasMask.java:41-57,112-119)", (neo_prefix, want_prefix))
    ck("V2.m65-model", {MASK_TYPE[k] for k, v in types.items() if v["m65"]} == set(re.findall(r"ModItems\.(\w+)", oline(inp, "gm", 76)))
       and {MASK_TYPE[k] for k, v in types.items() if not v["m65"]} == {onum(inp, "gm", 67, r"this==ModItems\.(\w+)\)")},
       "gas_mask uses ModelGasMask, the other three ModelM65 (ArmorGasMask.java:64-86)", types)
    ext = st.text(EXT)
    ov = body(ext, "public void renderHelmetOverlay(ItemStack stack, Player player, GuiGraphics guiGraphics, DeltaTracker deltaTracker)")
    fr = body(ext, "private static ResourceLocation[] frames(String prefix)")
    f = factors[0]
    ck("V2.overlay-formula", factors[0] == factors[1] and caps[0] == caps[1] and f is not None and
       f"intindex=(int)((double)stack.getDamageValue()/(double)stack.getMaxDamage()*{f});" in ov and f"[Math.min(index,{caps[0]})]" in ov,
       f"the frame index is min((int)(damage / max * {f}), {caps[0]}) of the mask's own damage (ArmorGasMask.java:113-119)", ov[:400])
    ck("V2.overlay-frames", 'newResourceLocation[6];' in fr and '"textures/misc/"+prefix+i+".png"' in fr, "six frames hbmsntm:textures/misc/<prefix><0..5>.png")
    ck("V2.overlay-state", ordered(ov, "RenderSystem.disableDepthTest();", "RenderSystem.depthMask(false);", "RenderSystem.enableBlend();",
                                   "RenderSystem.blendFuncSeparate(GlStateManager.SourceFactor.SRC_ALPHA,GlStateManager.DestFactor.ONE_MINUS_SRC_ALPHA,GlStateManager.SourceFactor.ONE,GlStateManager.DestFactor.ZERO);",
                                   "guiGraphics.setColor(1.0,1.0,1.0,1.0);", "guiGraphics.blit(tex,0,0,-90,0.0,0.0,guiGraphics.guiWidth(),guiGraphics.guiHeight(),guiGraphics.guiWidth(),guiGraphics.guiHeight());",
                                   "RenderSystem.depthMask(true);", "RenderSystem.enableDepthTest();")
       and "if(prefix==null)return;" in ov, "the overlay: depth test and mask off, blend 770/771/1/0, colour 1, full-screen quad at z -90 with UV 0..1, state restored (ArmorGasMask.java:125-144)")

    # durability, stack sizes, armor material
    rags_f = onum(inp, "mia", 22, r'"HBM_RAGS",(\d+),')
    defense = onum(inp, "mia", 22, r"newint\[\]\{([\d,]+)\}")
    ench = onum(inp, "mia", 22, r"\},(\d+)\);")
    fmax = onum(inp, "filt", 17, r"setMaxDamage\((\d+)\);")
    for i, mt in MASK_TYPE.items():
        ck(f"V2.durability-{mt}", f'ITEMS.register("{mt}",()->newGasMaskItem(GasMaskItem.MaskType.{i},newItem.Properties().durability(ArmorItem.Type.HELMET.getDurability(15))));' in items,
           f"{mt}: durability HELMET.getDurability(15) (1.7.10 ArmorMaterial.IRON factor 15 -> 165)")
    for rid, tex_ in (("mask_rag", "rag_damp"), ("mask_piss", "rag_piss")):
        ok = f'ITEMS.register("{rid}",()->newModArmorItem(NtmArmorMaterials.RAGS,ArmorItem.Type.HELMET,newItem.Properties().durability(ArmorItem.Type.HELMET.getDurability({rags_f})),NuclearTechMod.withDefaultNamespace("textures/armor/{tex_}.png")));' in items
        otex = re.search(r'":textures/armor/(\w+)\.png"', oline(inp, "ma", 67 if rid == "mask_rag" else 70))
        ck(f"V2.rag-mask-{rid}", ok and otex and otex[1] == tex_, f"{rid}: RAGS helmet, durability HELMET.getDurability({rags_f}), worn texture textures/armor/{tex_}.png (ModItemsArmor.java:22,31-32, ModArmor.java:66-71)")
    ck("V2.mod-armor-texture", "returnwornTexture;" in body(st.text(MAI), "public ResourceLocation getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, ArmorMaterial.Layer layer, boolean innerModel)"),
       "ModArmorItem.getArmorTexture returns its fixed texture")
    fil_ok = all(f'ITEMS.register("{x}",()->newGasMaskFilterItem(newItem.Properties().durability({fmax})));' in items for x in ITEM_IDS[6:11])
    ck("V2.filter-durability", fil_ok and fmax == "20000", f"the five filters: GasMaskFilterItem with durability {fmax} (ItemFilter.java:17; durability implies stack 1, :19)")
    plain = all(f'ITEMS.register("{x}",()->newItem(newItem.Properties()));' in items for x in ("rag_damp", "rag_piss", "filter_coal")) and \
        'ITEMS.register("rag",()->newRagItem(newItem.Properties()));' in items
    ck("V2.plain-items", plain, "rag is a RagItem, rag_damp / rag_piss / filter_coal are plain items with default stacks (ModItems.java:2398-2401)")
    mat = code_of(st.text(MAT))
    d = defense.split(",") if defense else []
    ck("V2.rags-material", f"ARMOR_MATERIALS.register(\"rags\",()->newArmorMaterial(defense({','.join(d)}),{ench},SoundEvents.ARMOR_EQUIP_LEATHER,()->Ingredient.of(NtmItems.RAG.get()),List.of(newArmorMaterial.Layer(NuclearTechMod.withDefaultNamespace(\"rags\"))),0,0));" in mat
       and "DeferredRegister.create(Registries.ARMOR_MATERIAL,NuclearTechMod.MODID)" in mat and len(d) == 4 and "customCraftingMaterial=ModItems.rag;" in oline(inp, "mia", 23),
       f"RAGS: defense {d}, enchantability {ench}, repaired with rag, toughness 0, knockback 0, in the ARMOR_MATERIAL registry as hbmsntm:rags (ModItemsArmor.java:22-23)")
    mod = code_of(st.text(MOD))
    ck("V2.material-registered", ordered(mod, "NtmArmorMaterials.register(eventBus);", "NtmItems.register(eventBus);"), "NuclearTechMod registers NtmArmorMaterials before NtmItems")

    # models
    for key, path in (("mgm", MGM), ("m65", M65)):
        oparts, _, osize, _ = orig_parts(inp, key)
        nparts, extras, nsize, ncode = neo_parts(st.text(path))
        diff = [(i, o, n) for i, (o, n) in enumerate(zip(oparts, nparts)) if o[0] != n[0] or o[1:3] != n[1:3] or not close(o[3], n[3]) or not close(o[4], n[4]) or not close(o[5], n[5])]
        ck(f"V2.{key}-boxes", len(oparts) == len(nparts) and not diff, f"{path.rsplit('/', 1)[1]}: every box equals the original (parent, texOffs, addBox, pivot, rotation; {len(oparts)} boxes)", (len(oparts), len(nparts), diff[:3]))
        ck(f"V2.{key}-no-mirror", not extras and "mirror" not in ncode, "no cube is mirrored (the original sets mirror after addBox)", extras)
        ck(f"V2.{key}-texture-size", nsize == osize, f"LayerDefinition texture size {nsize}, original {osize}")
        nops, rb = neo_render(st.text(path))
        oops = orig_render(inp, key)
        ok = len(nops) == len(oops) and all(a[0] == b[0] and close(a[1], b[1]) for a, b in zip(nops, oops))
        ck(f"V2.{key}-render-scales", ok, "the render scale / translate sequence equals the original (child 0.75 + 1 block, adult " + ("1.15" if key == "mgm" else "18/16, then 1.01") + ")", (oops, nops))
        ck(f"V2.{key}-render-head-only", ordered(rb, "poseStack.pushPose();", "this.head.render(poseStack,buffer,packedLight,packedOverlay,color);", "poseStack.popPose();")
           and not re.search(r"this\.(body|hat|rightArm|leftArm|rightLeg|leftLeg)\.render", rb), "only the head subtree (mask / filter) is rendered, between push and pop")
    ec = code_of(ext)
    ck("V2.m65-filter-visible", "this.modelM65.filter.visible=!ArmorUtil.getGasMaskFilterRecursively(living.getItemBySlot(EquipmentSlot.HEAD),living).isEmpty();" in ec,
       "the M65 filter part is shown only with a filter (ModelM65.java:144-145)")
    cl = code_of(st.text(CLIENT))
    ck("V2.client-registration", "event.registerItem(newGasMaskClientExtensions(),NtmItems.GAS_MASK.get(),NtmItems.GAS_MASK_M65.get(),NtmItems.GAS_MASK_MONO.get(),NtmItems.GAS_MASK_OLDE.get());" in cl
       and "event.registerLayerDefinition(ModelGasMask.LAYER,ModelGasMask::createLayer);" in cl and "event.registerLayerDefinition(ModelM65.LAYER,ModelM65::createLayer);" in cl,
       "NuclearTechModClient registers the extension for the four masks and both layer definitions")

    # client boundary
    leaks = {}
    for p in COMMON:
        c = blank_comments(lf(st.text(p)))
        hits = [w for w in ("net.minecraft.client", "GasMaskClientExtensions", "ModelGasMask", "ModelM65", "initializeClient", "IClientItemExtensions", "com.hbm.render") if w in c]
        if hits:
            leaks[p.rsplit("/", 1)[1]] = hits
    refs = [p for p in st.files if p.startswith("src/main/java/") and p not in (MGM, M65, EXT, CLIENT) and re.search(r"\b(GasMaskClientExtensions|ModelGasMask|ModelM65)\b", blank_comments(lf(st.text(p))))]
    ck("V2.client-boundary", not leaks and not refs, "GasMaskItem, ModArmorItem, GasMaskFilterItem, RagItem, ArmorUtil, NtmItems and NtmArmorMaterials reference no client class; "
       "the models and the extension are referenced only from NuclearTechModClient", (leaks, refs))

    # server guards and use orders
    fil = st.text(FIL)
    use = body(fil, "public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)")
    inst = body(fil, "private ItemStack installFilterOn(ItemStack helmet, ItemStack filter, Level level, Player player)")
    ck("V2.filter-use-order", ordered(use, "ItemStackhelmet=player.getItemBySlot(EquipmentSlot.HEAD);", "if(helmet.isEmpty())returnInteractionResultHolder.pass(stack);",
                                      "if(!(helmet.getItem()instanceofIGasMask)&&ArmorModHandler.hasMods(helmet)){", "ArmorModHandler.pryMods(level,helmet)[ArmorModHandler.HELMET_ONLY]",
                                      "installFilterOn(mask,stack,level,player);", "ArmorModHandler.applyMod(level,helmet,mask);", "installFilterOn(helmet,stack,level,player)"),
       "GasMaskFilterItem.use follows ItemFilter.java:22-46 (empty head, mod mask then applyMod, else the helmet)", missing_order(use, "helmet.isEmpty()", "hasMods", "pryMods", "installFilterOn(mask", "applyMod", "installFilterOn(helmet"))
    ck("V2.filter-install-order", ordered(inst, "if(!(helmet.getItem()instanceofIGasMaskmask))returnnull;", "if(!mask.isFilterApplicable(helmet,player,filter))returnnull;",
                                          "ItemStackcopy=filter.copy();", "ItemStackcurrent=ArmorUtil.getGasMaskFilter(level,helmet);", "ArmorUtil.installGasMaskFilter(level,helmet,copy);",
                                          "level.playSound(null,player.getX(),player.getY(),player.getZ(),NtmSoundEvents.GASMASK_SCREW.get(),SoundSource.PLAYERS,1,1);"),
       "installFilterOn follows ItemFilter.java:48-71 (IGasMask, applicable, copy, current, install, screw sound volume 1 pitch 1)")
    ck("V2.filter-server-guard", ordered(inst, "if(level.isClientSide())returnfilter;", "ArmorUtil.installGasMaskFilter(") and "level.isClientSide()?peekHelmetMod(level,helmet):ArmorModHandler.pryMods(level,helmet)" in use
       and ordered(use, "if(!level.isClientSide()&&mask.getItem()instanceofItemArmorMod){", "ArmorModHandler.applyMod(level,helmet,mask);"),
       "the filter use path changes the mask, the mods and plays the sound only under !level.isClientSide()")
    guse = body(gm, "public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)")
    ck("V2.mask-use", ordered(guse, "if(player.isShiftKeyDown()){", "ItemStackfilter=this.getFilter(stack,player);", "if(!filter.isEmpty()){", "if(!level.isClientSide()){",
                              "ArmorUtil.removeFilter(stack);", "if(!player.getInventory().add(filter)){", "player.drop(filter,true,false);", "returnInteractionResultHolder.sidedSuccess(stack,level.isClientSide());",
                              "returnsuper.use(level,player,hand);"),
       "GasMaskItem.use follows ArmorGasMask.java:193-212 (sneak + filter: remove, inventory else drop around, no equip; otherwise super) with the change under !isClientSide")
    rag = st.text(RAGI)
    reu = body(rag, "public boolean onEntityItemUpdate(ItemStack stack, ItemEntity entity)")
    ruse = body(rag, "public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)")
    ck("V2.rag", ordered(reu, "!entity.level().isClientSide()&&entity.level().getFluidState(entity.blockPosition()).is(FluidTags.WATER)", "entity.setItem(newItemStack(NtmItems.RAG_DAMP.get(),stack.getCount()));", "returntrue;")
       and ordered(ruse, "if(!level.isClientSide()){", "stack.consume(1,player);", "ItemStackpiss=newItemStack(NtmItems.RAG_PISS.get());", "player.getInventory().add(piss)")
       and 'I18nUtil.resolveKeyArray("item.hbmsntm.rag.desc")' in code_of(rag) and 'resolveKeyArray("item.rag.desc")' in oline(inp, "rag", 41),
       "RagItem: server-side water -> rag_damp of the same count; right click one fewer rag and one rag_piss (ItemRag.java:17-38)")

    # tooltip helper (ArmorUtil.java:355-383)
    tt = body(au, "public static void addGasMaskTooltip(ItemStack mask, Item.TooltipContext context, List<Component> list, TooltipFlag flag)")
    ck("V2.tooltip", ordered(tt, 'list.add(Component.translatable("hazard.no_filter").withStyle(ChatFormatting.RED));return;', 'list.add(Component.translatable("hazard.filter_installed").withStyle(ChatFormatting.GOLD));',
                             "if(max>0){", 'append=" ("+((max-meta)*100/max)+"%)";', 'list.add(Component.literal("  ").append(filter.getHoverName()).append(append).withStyle(ChatFormatting.GRAY));',
                             "filter.getItem().appendHoverText(filter,context,lore,flag);", "EventHooks.onItemTooltip(filter,null,lore,flag,context);",
                             'lore.forEach(x->list.add(Component.literal("  ").append(x).withStyle(ChatFormatting.YELLOW)));'),
       "addGasMaskTooltip follows ArmorUtil.java:355-383 (no filter -> red and stop; gold header; name + (max - damage) * 100 / max %; the filter's own lines yellow)")

    # ArmorUtil: only additions; the start methods unchanged
    start_au = inp.start.get(AU)
    sigs = ["public static void installGasMaskFilter(Level level, ItemStack mask, ItemStack filter)", "public static void removeFilter(ItemStack mask)",
            "public static ItemStack getGasMaskFilterRecursively(ItemStack mask, LivingEntity entity)", "public static void damageGasMaskFilter(LivingEntity entity, int damage)",
            "public static void damageGasMaskFilter(Level level, ItemStack mask, int damage)", "public static boolean isWearingEmptyMask(Player player)"]
    changed = [s for s in sigs if body(au, s) != body(start_au, s)]
    ck("V2.armorutil-start-methods", not changed and 'publicstaticfinalStringFILTER_KEY="hfr_Filter";' in code_of(au) and 'publicstaticfinalStringFILTER_KEY="hfr_Filter";' in code_of(start_au),
       "the start filter methods of ArmorUtil are unchanged and the key is still hfr_Filter", changed)
    gget = body(au, "public static ItemStack getGasMaskFilter(HolderLookup.Provider registries, ItemStack mask)")
    sget = body(start_au, "public static ItemStack getGasMaskFilter(Level level, ItemStack mask)")
    ck("V2.armorutil-overload", body(au, "public static ItemStack getGasMaskFilter(Level level, ItemStack mask)") == "returngetGasMaskFilter(level.registryAccess(),mask);"
       and gget == sget.replace("ItemStack.parse(level.registryAccess(),attach)", "ItemStack.parse(registries,attach)"),
       "getGasMaskFilter(Level, ...) delegates to the new registries overload, whose body is the start body with the registries argument")

    unchanged = [p for p in UNCHANGED if st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.unchanged-files", not unchanged, "IGasMask, ArmorRegistry, HazmatRegistry, ArmorModHandler, ArmorNo9, the hazard types, the gas blocks and the older GameTests are byte-equal to the start", unchanged)

    asm = code_of(st.text(ASM))
    dur = onum(inp, "asm", 122, r"\.setup\((\d+),")
    pw = onum(inp, "asm", 122, r"\.setup\(\d+,(\d+)\)")
    ins = re.findall(r"\((?:COAL\.dust\(\)|Items\.(\w+)),(\d+)\)", oline(inp, "asm", 123))
    want = f'this.register(newGenericRecipe("ass.filtercoal").setup({dur},{pw}).outputItems(newItemStack(NtmItems.FILTER_COAL.get(),1)).inputItems(newComparableStack(NtmItems.POWDER_COAL.get(),{ins[0][1] if ins else "?"}),newComparableStack(net.minecraft.world.item.Items.STRING,{ins[1][1] if len(ins) > 1 else "?"}),newComparableStack(net.minecraft.world.item.Items.PAPER,{ins[2][1] if len(ins) > 2 else "?"})));'
    ck("V2.assembly-filtercoal", want in asm and len(ins) == 3, f"ass.filtercoal setup({dur}, {pw}), 1 filter_coal from 4 coal dust, 2 string, 1 paper (AssemblyMachineRecipes.java:122-123)", want)
    ck("V2.sound-event", 'GASMASK_SCREW=reg("item.gasmask_screw");' in code_of(st.text(SND)) and 'this.add(NtmSoundEvents.GASMASK_SCREW,SoundDefinition.definition().with(sound("hbmsntm:tool/gasmask_screw")));' in code_of(st.text(SNDP))
       and "item.gasmaskScrew" in oline(inp, "snd", 137), "item.gasmask_screw -> hbmsntm:tool/gasmask_screw (NTMSounds.java:137, sounds.json:114, lowercase rename)")
    tabs = code_of(st.text(CTAB))
    ck("V2.creative-tabs", ordered(tabs, "output.accept(NtmItems.RAG.get());", "output.accept(NtmItems.RAG_DAMP.get());", "output.accept(NtmItems.RAG_PISS.get());", "output.accept(NtmItems.FILTER_COAL.get());")
       and ordered(tabs, *[f"output.accept(NtmItems.{x.upper()});" for x in ITEM_IDS[:11]]), "the creative tabs list the 15 items (main-notes 6)")
    ck("V2.item-models", all(f"this.basicItem(NtmItems.{x.upper()}.get());" in code_of(st.text(IMP)) for x in ITEM_IDS), "NtmItemModelProvider has basicItem for the 15 items")


# ---------------------------------------------------------------- V3 generated

def parse_orig_recipe(inp, key, n):
    line = oline(inp, key, n)
    m = re.search(r"addRecipeAuto\(newItemStack\(ModItems\.(\w+),(\d+)\),newObject\[\]\{(.*)\}\);", line)
    if not m:
        return None
    args = m[3]
    cut = args.index(",'")
    patterns = re.findall(r'"([^"]*)"', args[:cut])
    parts = re.split(r"'(\w)',", args[cut + 1:])
    keys = {parts[j]: parts[j + 1].rstrip(",") for j in range(1, len(parts), 2)}
    return m[1], int(m[2]), patterns, keys


def v3_generated(ck, inp, st):
    for rid, key, n, adv in RECIPES:
        o = parse_orig_recipe(inp, key, n)
        path = f"{RECIPE_DIR}{rid}.json"
        if not st.has(path) or o is None:
            ck(f"V3.recipe-{rid}", False, f"{rid}: recipe JSON and original row {key}:{n}", (st.has(path), o))
            continue
        data = json.loads(st.text(path))
        want_key = {k: EXPR.get(v) for k, v in o[3].items()}
        ok = data.get("type") == "minecraft:crafting_shaped" and data.get("pattern") == o[2] and data.get("key") == want_key and \
            data.get("result") == {"count": o[1], "id": R + o[0]} and o[0] == rid and None not in want_key.values()
        ck(f"V3.recipe-{rid}", ok, f"{rid}: shaped, pattern {o[2]}, keys mapped from the original row, result {o[1]} x {o[0]} ({O_FILES[key].rsplit('/', 1)[1]}:{n})", (data, want_key))
        ck(f"V3.advancement-{rid}", st.has(f"{ADV_ROOT}{adv}/{rid}.json"), f"{rid}: the recipe advancement exists under {adv}/")
    for rid, n in SMELT:
        m = re.search(r"addSmelting\(ModItems\.(\w+),newItemStack\(ModItems\.(\w+)\),([\d.]+)\);", oline(inp, "sm", n))
        path = f"{RECIPE_DIR}{rid}.json"
        data = json.loads(st.text(path)) if st.has(path) else {}
        ok = bool(m) and data.get("type") == "minecraft:smelting" and data.get("ingredient") == {"item": R + m[1]} and data.get("result") == {"count": 1, "id": R + m[2]} \
            and abs(data.get("experience", -1) - float(m[3])) < 1e-9 and data.get("cookingtime") == 200
        ck(f"V3.smelting-{rid}", ok, f"{rid}: smelting {m[1] if m else '?'} -> {m[2] if m else '?'}, {m[3] if m else '?'} xp, 200 ticks (SmeltingRecipes.java:{n})", data)
        ck(f"V3.advancement-{rid}", st.has(f"{ADV_ROOT}misc/{rid}.json"), f"{rid}: the recipe advancement exists under misc/")
    bad = []
    for i in ITEM_IDS:
        p = f"{GEN}assets/hbmsntm/models/item/{i}.json"
        d = json.loads(st.text(p)) if st.has(p) else None
        if d != {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/{i}"}} or not st.has(RES + f"textures/item/{i}.png"):
            bad.append(i)
    ck("V3.item-models", not bad, "15 item models: item/generated with layer0 hbmsntm:item/<id>, and the texture exists", bad)
    sounds = json.loads(st.text(SOUNDS))
    oname = re.search(r'"name":"([^"]+)"', oline(inp, "sj", 114))
    want = "hbmsntm:" + RENAMES.get("sounds/" + (oname[1] if oname else "") + ".ogg", "?")[len("sounds/"):-len(".ogg")]
    ck("V3.sounds-json", sounds.get("item.gasmask_screw") == {"sounds": [want]} and st.has(RES + "sounds/tool/gasmask_screw.ogg"),
       f"sounds.json: item.gasmask_screw -> {want} (sounds.json:114 tool/gasmaskScrew, renamed) and the ogg exists", sounds.get("item.gasmask_screw"))
    en = json.loads(st.text(EN))
    start_en = json.loads(inp.start[EN])
    wrong = {}
    for neo, okey, _, _ in UP:
        e = inp.o_en.get(okey)
        if not e or en.get(neo) != e[0][0]:
            wrong[neo] = (en.get(neo), e and e[0][0])
    for neo, n in LOCAL:
        lit = re.search(r'"([^"]+)"\);', oline(inp, "au", n))
        if not lit or en.get(neo) != lit[1]:
            wrong[neo] = (en.get(neo), lit and lit[1])
    added = sorted(set(en) - set(start_en))
    changed = [k for k in start_en if en.get(k) != start_en[k]]
    ck("V3.en-us", not wrong and added == sorted(NEW_KEYS) and not changed, "en_us.json gained exactly the 18 keys with the original English (16 lang lines, 2 ArmorUtil literals) and changed nothing else",
       (wrong, sorted(set(added) ^ set(NEW_KEYS)), changed[:5]))


# ---------------------------------------------------------------- V4 language

def v4_lang(ck, inp, st):
    zt, mt = st.text(ZH), st.text(MAP)
    zh, mp = json.loads(zt), json.loads(mt)["entries"]
    z0, m0 = json.loads(inp.start[ZH]), json.loads(inp.start[MAP])["entries"]
    ck("V4.zh-insert-only", all(zh.get(k) == v for k, v in z0.items()) and sorted(set(zh) - set(z0)) == sorted(NEW_KEYS),
       "zh_cn.json keeps every start value and gained exactly the 18 keys", sorted(set(zh) - set(z0)))
    ck("V4.map-insert-only", all(mp.get(k) == v for k, v in m0.items()) and sorted(set(mp) - set(m0)) == sorted(NEW_KEYS),
       "the mapping keeps every start entry and gained exactly the 18 entries", sorted(set(mp) - set(m0)))
    bad = {}
    for neo, okey, _, _ in UP:
        e, z, row = inp.o_en.get(okey), inp.o_zh.get(okey), mp.get(neo, {})
        if not (row.get("kind") == "upstream" and row.get("source_key") == okey and e and row.get("source_en") == e[0][0] and z and row.get("source_zh") == z[0][0]
                and row.get("target_zh") == zh.get(neo) and row.get("target_en") == json.loads(st.text(EN)).get(neo)):
            bad[neo] = (row, z and z[0][0], zh.get(neo))
    ck("V4.upstream", not bad, "16 upstream mapping entries carry the original key, English and Chinese (zh_CN.lang lines) and the current zh_cn.json / en_us.json text", bad)
    same = [neo for neo, okey, _, _ in UP if zh.get(neo) != (inp.o_zh.get(okey) or [("?",)])[0][0]]
    ck("V4.upstream-text", not same, "the 16 upstream Chinese texts are the original zh_CN.lang text", same)
    loc = {k: mp.get(k, {}) for k, _ in LOCAL}
    ck("V4.local", all(r.get("kind") == "local" and r.get("target_zh") == zh.get(k) and zh.get(k) for k, r in loc.items()), "the two hazard.* keys are local entries with their zh_cn.json text", loc)
    for path, text, start in ((ZH, zt, inp.start[ZH]), (MAP, mt, inp.start[MAP])):
        crlf = "\r\n" in start
        ok = (text.count("\r\n") == text.count("\n")) if crlf else ("\r\n" not in text)
        diff = [l for l in difflib.unified_diff(lf(start).split("\n"), lf(text).split("\n"), lineterm="", n=0) if l[:1] == "-" and not l.startswith("---")]
        removed = [l for l in diff if l.strip() not in ("-", "-}", "-  }", "-},")]
        ck(f"V4.eol-{path.rsplit('/', 1)[1]}", ok, f"{path.rsplit('/', 1)[1]} keeps its start line endings ({'CRLF' if crlf else 'LF'})")
        ck(f"V4.lines-{path.rsplit('/', 1)[1]}", all(re.fullmatch(r'-\s*("[^"]*": "[^"]*"|\}),?', l) for l in diff) and len(removed) <= len(NEW_KEYS),
           f"{path.rsplit('/', 1)[1]}: no start line was rewritten beyond trailing-comma changes at the insertion points", removed[:4])
    pl = [k for k in NEW_KEYS if sorted(re.findall(r"%(?:\d+\$)?[sdf]|%%", zh.get(k, ""))) != sorted(re.findall(r"%(?:\d+\$)?[sdf]|%%", json.loads(st.text(EN)).get(k, "")))
          or zh.get(k, "").count("$") != json.loads(st.text(EN)).get(k, "").count("$")]
    ck("V4.placeholders", not pl, "the Chinese keeps the English placeholders and $ line breaks", pl)


# ---------------------------------------------------------------- V5 resources

def v5_resources(ck, inp, st):
    bad = [p for p in RES_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V5.byte-equal", not bad and len(RES_PATHS) == 34, "the 34 imports are byte-equal (SHA-256) to the original working tree", bad)
    old_names = [RES + o for o in RENAMES if st.has(RES + o)]
    ck("V5.renames", not old_names and all(st.has(RES + n) for n in RENAMES.values()), "the four renamed files exist only under their lowercase names", old_names)
    refs = []
    for p in (GMI, ITEMS, EXT):
        for m in re.finditer(r'"(textures/[\w/]+\.png)"', code_of(st.text(p))):
            refs.append(m[1])
    refs += [f"textures/misc/overlay_{k}_{i}.png" for k in ("gasmask", "goggles") for i in range(6)]
    miss = [r for r in refs if not st.has(RES + r)]
    ck("V5.referenced-textures", not miss and len(refs) >= 18, f"every texture the code references exists ({len(refs)} paths: worn textures, rag masks, overlay frames)", miss)
    if not st.has(OWN):
        ck.pending("V5.ownership-pending", "migration/goal26b-resource-ownership.json is absent: pending, not passed")
        return
    own = json.loads(st.text(OWN))
    rows = {a["target_path"]: a for a in own.get("assets", [])}
    wrong = [p for p, (o, n) in zip(RES_PATHS, IMPORTS) if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None)
             or rows[p].get("source_path") != O_RES + o or rows[p].get("renamed") != (o in RENAMES)]
    ck("V5.ownership", not wrong and len(rows) == 34 and own.get("source_commit") == ORIGINAL_HEAD,
       "the ownership record lists the 34 imports with their source paths, hashes and the four renames", wrong[:5])


# ---------------------------------------------------------------- V6 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v6_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    expected = set(NEW_CLASSES + EDITED + GEN_MODIFIED + RES_PATHS + GEN_NEW)
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V6.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, resources, the GameTest, the records)", extra[:10])
    ck("V6.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != STAMP]
    ck("V6.expected-all-changed", not never, "every expected production, resource, generated and GameTest path differs from the start", never[:5])
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    ck("V6.gen-new", sorted(gen_new) == sorted(GEN_NEW) and len(GEN_NEW) == 43, "exactly the 43 new generated files appeared (15 item models, 14 recipes, 14 advancements)", sorted(set(gen_new) ^ set(GEN_NEW))[:6])
    gen_mod = [p for p in changed if p.startswith(GEN) and p in inp.base_files]
    ck("V6.gen-modified", set(gen_mod) <= set(GEN_MODIFIED) and {SOUNDS, EN} <= set(gen_mod), "the generated files that changed are sounds.json, en_us.json and the stamp", gen_mod)
    ck("V6.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + RES_PATHS) and all(p in inp.base_files for p in EDITED),
       "the new classes and resources did not exist at the start; the edited files did")
    eol = [p for p in EDITED if inp.start.get(p) and st.has(p) and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V6.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    mixed = [p for p in NEW_CLASSES if st.has(p) and st.text(p).count("\r\n") not in (0, st.text(p).count("\n"))]
    ck("V6.new-class-eol", not mixed, "every new class has one line-ending style", mixed)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V6.records", True, "records changed (allowed, not required): " + ", ".join(rest))
    ck("V6.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V7 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v7_gametest(ck, inp, st):
    others = gametest_total(inp.gt_other.values())
    ck("V7.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V7.present", st.has(GT), "GasMaskGameTests.java exists")
    if not st.has(GT):
        return dict(tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V7.tests", len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "every @GameTest is public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = [(re.search(r'batch\s*=\s*"([^"]+)"', a) or [None, None])[1] for a in tests.values()]
    ck("V7.own-batch", None not in batches and len(set(batches)) == len(batches), "every test has its own batch", batches)
    ck("V7.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "@GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false)")
    ck("V7.marker", f'TAG = "{GT_MARK}"' in live and 'LOGGER.info("{} {} passed", TAG, name);' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = [n for n in tests if f'"{n}"' not in body(live, f"void {n}(GameTestHelper helper)")]
    ck("V7.report-name", not miss, "every test passes its own name to the passed helper", miss)
    ck("V7.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V7.no-client", not re.search(r"net\.minecraft\.client", code), "GasMaskGameTests references no client class")
    ck("V7.original-constants", all(s in live for s in ("stack.getMaxDamage() == 20000", "stack.getMaxDamage() == 165", "stack.getMaxDamage() == 1650", "endsWith(\" (93%)\")",
                                                         "recipe.getExperience() == 0.1F", "r.duration == 50 && r.power == 100L", "armor(stack) == 2D", "armor(stack) == 1D", "ArmorUtil.java:39-48", "ItemFilter.java:16-72",
                                                         "ArmorGasMask.java:59-61,88-104,147-155,189-191,193-212", "AssemblyMachineRecipes.java:122-123")),
       "the GameTest's expected values are the original's (20,000 filter, 165 / 1,650 durability, 0.1 xp, ass.filtercoal 50 / 100) and it cites the original lines")
    ck("V7.real-items", "stand-in" not in lf(live).lower().replace("no stand-in item is used", ""), "the class uses the real items (no stand-in boundary other than the FakePlayer)")
    total = others + len(tests)
    if st.log_text is None:
        ck.pending("V7.log-not-run", "no --gametest-log given: the GameTest log checks were not run")
        return dict(tests=sorted(tests))
    return dict(tests=sorted(tests), log=v7_log(ck, inp, st, tests, total))


def v7_log(ck, inp, st, tests, total):
    text = st.log_text
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V7.log-all-passed", bool(match) and int(match[1]) == total, f"the log says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)}, counted from @GameTest)", (match and match[0], total))
    ck("V7.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed|failed at", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V7.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V7.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    facts = {}
    prot = dict(re.findall(re.escape(GT_MARK) + r" (hbmsntm:\w+(?: \+ hbmsntm:\w+| without a filter)): \[([^\]]*)\]", text))
    facts["protection"] = prot
    # re-derive the worn protection from the original: mask classes (ArmorUtil.java:45-48) + filter classes (:39-43) minus the blacklist (ArmorGasMask.java:147-155)
    haz = {i: set(c) for i, c in orig_hazards(inp) if i}
    mono_item, mono, other = orig_blacklists(inp)
    want = {}
    for mask, filt in (("gas_mask", None), ("gas_mask", "gas_mask_filter"), ("gas_mask", "gas_mask_filter_combo"), ("gas_mask_m65", None), ("gas_mask_m65", "gas_mask_filter"),
                       ("gas_mask_mono", None), ("gas_mask_mono", "gas_mask_filter"), ("gas_mask_mono", "gas_mask_filter_mono"), ("gas_mask_olde", None),
                       ("gas_mask_olde", "gas_mask_filter_rag"), ("gas_mask_olde", "gas_mask_filter_piss"), ("mask_rag", None), ("mask_piss", None)):
        s = set(haz.get(mask, set()))
        if filt:
            s |= haz.get(filt, set()) - set(mono if mask == mono_item else other or [])
        want[f"hbmsntm:{mask}" + (f" + hbmsntm:{filt}" if filt else " without a filter")] = s
    got = {k: set(x.strip() for x in v.split(",") if x.strip()) for k, v in prot.items()}
    wrong = {k: (sorted(got.get(k, [])), sorted(v)) for k, v in want.items() if got.get(k) != v}
    ck("V7.log-protection", not wrong and len(got) >= len(want), "every logged worn-protection set re-derives from the original registrations and blacklists", wrong)
    ck("V7.log-rag-waterlogged", f"{GT_MARK} rags: in a waterlogged slab the rag became 5 hbmsntm:rag_damp" in text, "the waterlogged rag result is recorded (NEO-only, main-notes 11)")
    return dict(all_passed=match and match[0], expected_total=total, facts=facts)


# ---------------------------------------------------------------- V8 jar

def v8_jar(ck, inp, st, path):
    classes_ = [p.split("/java/")[1][:-5] for p in NEW_CLASSES]
    gen = [p for p in GEN_NEW + GEN_MODIFIED if p != STAMP]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V8.classes", not missing, "the JAR has the eight new production classes and GasMaskGameTests", missing)
        bad = [p for p in RES_PATHS if p[len(JARRES):] not in names or jar.read(p[len(JARRES):]) != st.files.get(p)]
        ck("V8.resources", not bad, "the 34 imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V8.generated", not gbad, "the 43 new generated files, sounds.json and en_us.json in the JAR are byte-equal to the tree (the stamp is not packaged)", gbad[:5])
        ck("V8.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        ck("V8.en_us", "assets/hbmsntm/lang/en_us.json" in names and jar.read("assets/hbmsntm/lang/en_us.json") == st.files[EN], "en_us.json in the JAR equals the generated file")
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), note="the JAR checks establish packaged names and bytes, not runtime behaviour")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_source, inp, st)
    guarded(ck, "V3", v3_generated, inp, st)
    guarded(ck, "V4", v4_lang, inp, st)
    guarded(ck, "V5", v5_resources, inp, st)
    guarded(ck, "V6", v6_scope, inp, st)
    r7 = guarded(ck, "V7", v7_gametest, inp, st)
    if facts is not None:
        facts["V7"] = r7
    return ck


def T(path, fn):
    """Apply fn to the LF-normalised text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


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


def LT(fn):
    def apply(st):
        st.log_text = fn(st.log_text)
    return apply


def MV(old, new):
    def apply(st):
        data = st.files[old]
        st.delete(old)
        st.set_bytes(new, data)
    return apply


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None; the string 'LOG' requires a GameTest log)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    lang_edit = lambda key, value: T(ZH, lambda x: rep1(x, f'"{key}": "{json.loads(x)[key]}"', f'"{key}": "{value}"'))  # noqa: E731
    return [
        ("filter_classes_changed", "V2.", t(AU, "registerHazard(NtmItems.GAS_MASK_FILTER_MONO.get(), HazardClass.PARTICLE_COARSE, HazardClass.GAS_MONOXIDE);",
                                            "registerHazard(NtmItems.GAS_MASK_FILTER_MONO.get(), HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_MONOXIDE);")),
        ("mask_own_class_dropped", "V2.", t(AU, "registerHazard(NtmItems.GAS_MASK.get(), HazardClass.SAND, HazardClass.LIGHT);", "registerHazard(NtmItems.GAS_MASK.get(), HazardClass.SAND);")),
        ("diamond_line_dropped", "V2.", t(AU, "ArmorRegistry.registerHazard(Items.DIAMOND_HELMET, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);\n", "")),
        ("mono_blacklist_without_bacteria", "V2.", t(GMI, "List.of(HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA)", "List.of(HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING)")),
        ("filter_max_damage_2000", "V2.", t(ITEMS, 'register("gas_mask_filter_rag", () -> new GasMaskFilterItem(new Item.Properties().durability(20000)))',
                                            'register("gas_mask_filter_rag", () -> new GasMaskFilterItem(new Item.Properties().durability(2000)))')),
        ("mask_durability_16", "V2.", t(ITEMS, "new GasMaskItem(GasMaskItem.MaskType.M65, new Item.Properties().durability(ArmorItem.Type.HELMET.getDurability(15)))",
                                        "new GasMaskItem(GasMaskItem.MaskType.M65, new Item.Properties().durability(ArmorItem.Type.HELMET.getDurability(16)))")),
        ("rags_factor_15", "V2.", t(ITEMS, 'register("mask_piss", () -> new ModArmorItem(NtmArmorMaterials.RAGS, ArmorItem.Type.HELMET, new Item.Properties().durability(ArmorItem.Type.HELMET.getDurability(150))',
                                    'register("mask_piss", () -> new ModArmorItem(NtmArmorMaterials.RAGS, ArmorItem.Type.HELMET, new Item.Properties().durability(ArmorItem.Type.HELMET.getDurability(15))')),
        ("rags_defense_2", "V2.", t(MAT, "defense(1, 1, 1, 1)", "defense(1, 1, 1, 2)")),
        ("overlay_min_removed", "V2.", t(EXT, "[Math.min(index, 5)]", "[index]")),
        ("overlay_factor_5", "V2.", t(EXT, "(double) stack.getMaxDamage() * 6D)", "(double) stack.getMaxDamage() * 5D)")),
        ("overlay_prefix_swapped", "V2.", T(GMI, lambda x: rep1(rep1(x, '"overlay_gasmask_", false)', '"OVERLAY_TMP", false)'), '"overlay_goggles_", false)', '"overlay_gasmask_", false)').replace('"OVERLAY_TMP"', '"overlay_goggles_"'))),
        ("overlay_z_changed", "V2.", t(EXT, "guiGraphics.blit(tex, 0, 0, -90,", "guiGraphics.blit(tex, 0, 0, 0,")),
        ("box_size_changed", "V2.", t(MGM, "texOffs(0, 0).addBox(0F, 0F, 0F, 8, 8, 3)", "texOffs(0, 0).addBox(0F, 0F, 0F, 8, 8, 4)")),
        ("texoffs_changed", "V2.", t(M65, "texOffs(18, 21)", "texOffs(18, 22)")),
        ("rotation_changed", "V2.", t(M65, "-0.4799655F, 0F, 0F", "-0.48F, 0F, 0F")),
        ("pivot_changed", "V2.", t(MGM, "-0.5333334F - 4", "-0.5F - 4")),
        ("filter_part_moved_to_mask", "V2.", t(M65, 'filter.addOrReplaceChild("filter2"', 'mask.addOrReplaceChild("filter2"')),
        ("render_scale_changed", "V2.", t(MGM, "poseStack.scale(1.15F, 1.15F, 1.15F);", "poseStack.scale(1.2F, 1.2F, 1.2F);")),
        ("m65_inner_scale_dropped", "V2.", t(M65, "poseStack.scale(1.01F, 1.01F, 1.01F);\n", "")),
        ("mirror_added", "V2.", t(MGM, "texOffs(22, 0).addBox(0F, 0F, 0F, 2, 2, 1),\n                PartPose.offsetAndRotation(1F", "texOffs(22, 0).mirror().addBox(0F, 0F, 0F, 2, 2, 1),\n                PartPose.offsetAndRotation(1F")),
        ("texture_size_changed", "V2.", t(M65, "LayerDefinition.create(mesh, 32, 32)", "LayerDefinition.create(mesh, 64, 32)")),
        ("worn_texture_changed", "V2.", t(GMI, 'OLDE("textures/armor/mask_olde.png"', 'OLDE("textures/models/model_m65.png"')),
        ("rag_mask_texture_swapped", "V2.", t(ITEMS, 'withDefaultNamespace("textures/armor/rag_piss.png")', 'withDefaultNamespace("textures/armor/rag_damp.png")')),
        ("client_extension_in_item", "V2.", t(GMI, "import api.hbm.item.IGasMask;", "import api.hbm.item.IGasMask;\nimport com.hbm.render.item.GasMaskClientExtensions;")),
        ("client_import_in_rag", "V2.", t(RAGI, "import net.minecraft.ChatFormatting;", "import net.minecraft.ChatFormatting;\nimport net.minecraft.client.Minecraft;")),
        ("filter_server_guard_removed", "V2.", t(FIL, "        if(level.isClientSide()) return filter;\n", "")),
        ("mask_use_server_guard_removed", "V2.", t(GMI, "if(!level.isClientSide()) {\n                    ArmorUtil.removeFilter(stack);", "if(true) {\n                    ArmorUtil.removeFilter(stack);")),
        ("filter_sound_volume", "V2.", t(FIL, "SoundSource.PLAYERS, 1F, 1F);", "SoundSource.PLAYERS, 0.5F, 1F);")),
        ("mask_drop_without_scatter", "V2.", t(GMI, "player.drop(filter, true, false);", "player.drop(filter, false, false);")),
        ("filter_key_changed", "V2.", t(AU, 'FILTER_KEY = "hfr_Filter";', 'FILTER_KEY = "hfrFilter";')),
        ("tooltip_percent_changed", "V2.", t(AU, "((max - meta) * 100 / max)", "(meta * 100 / max)")),
        ("igasmask_touched", "V2.", T("src/main/java/api/hbm/item/IGasMask.java", lambda x: x + "\n")),
        ("ass_duration_100", "V2.", t(ASM, 'new GenericRecipe("ass.filtercoal").setup(50, 100)', 'new GenericRecipe("ass.filtercoal").setup(100, 100)')),
        ("material_registered_late", "V2.", T(MOD, lambda x: rep1(rep1(x, "        NtmArmorMaterials.register(eventBus);\n", ""), "        NtmBlocks.register(eventBus);\n", "        NtmBlocks.register(eventBus);\n        NtmArmorMaterials.register(eventBus);\n"))),
        # V3 generated
        ("recipe_deleted", "V3.|V6.", D(RECIPE_DIR + "gas_mask.json")),
        ("recipe_key_nugget_to_ingot", "V3.", gen_edit(RECIPE_DIR + "gas_mask_filter_mono.json", lambda d: d["key"]["Z"].update(item=R + "ingot_zirconium"))),
        ("rag_output_2", "V3.", gen_edit(RECIPE_DIR + "rag.json", lambda d: d["result"].update(count=2))),
        ("rag_wool_white_only", "V3.", gen_edit(RECIPE_DIR + "rag.json", lambda d: d["key"].update(W={"item": "minecraft:white_wool"}))),
        ("smelting_xp_0_7", "V3.", gen_edit(RECIPE_DIR + "rag_from_smelting_rag_piss.json", lambda d: d.update(experience=0.7))),
        ("recipe_pattern_changed", "V3.", gen_edit(RECIPE_DIR + "gas_mask_mono.json", lambda d: d.update(pattern=["PPP", "PPP", " F "]))),
        ("item_model_texture", "V3.", gen_edit(GEN + "assets/hbmsntm/models/item/rag_piss.json", lambda d: d["textures"].update(layer0="hbmsntm:item/rag"))),
        ("sound_path_original_case", "V3.", gen_edit(SOUNDS, lambda d: d["item.gasmask_screw"].update(sounds=["hbmsntm:tool/gasmaskScrew"]))),
        ("language_value", "V3.", gen_edit(EN, lambda d: d.update({"item.hbmsntm.gas_mask_mono": "Half Gas Mask"}))),
        # V4 language
        ("zh_upstream_text", "V4.", lang_edit("item.hbmsntm.rag_damp", "潮湿的布")),
        ("zh_key_dropped", "V4.", T(ZH, lambda x: "\n".join(l for l in x.split("\n") if '"hazard.filter_installed"' not in l))),
        ("map_source_zh", "V4.", T(MAP, lambda x: rep1(x, '"source_zh": "活性炭过滤器"', '"source_zh": "活性碳过滤器"'))),
        ("zh_crlf_lost", "V4.", lambda st: st.set_bytes(ZH, st.files[ZH].replace(b"\r\n", b"\n"))),
        # V5 resources
        ("resource_byte_flip", "V5.", lambda st: st.set_bytes(RES + "textures/misc/overlay_goggles_3.png", flip_byte(st.files[RES + "textures/misc/overlay_goggles_3.png"]))),
        ("rename_target_original_case", "V5.|V6.", MV(RES + "textures/models/model_m65.png", RES + "textures/models/ModelM65.png")),
        ("sound_renamed_back", "V3.|V5.", MV(RES + "sounds/tool/gasmask_screw.ogg", RES + "sounds/tool/gasmaskScrew.ogg")),
        # V6 scope
        ("extra_production_file", "V6.", lambda st: st.set_text(J + "items/armor/ArmorHazmat.java", "class ArmorHazmat {}\n")),
        ("start_file_deleted", "V6.", D(J + "items/armor/ArmorNo9.java")),
        # V1 original (in memory)
        ("orig_filter_line_moved", "V1.", OE("au", lambda x: rep1(x, "\tpublic static void register() {\n", "\tpublic static void register() {\n\n"))),
        ("orig_blacklist_changed", "V1.|V2.", OE("gm", lambda x: rep1(x, "HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA", "HazardClass.GAS_LUNG, HazardClass.BACTERIA"))),
        ("orig_box_changed", "V1.|V2.", OE("m65", lambda x: rep1(x, "nose.addBox(0F, 0F, 0F, 3, 3, 1);", "nose.addBox(0F, 0F, 0F, 3, 3, 2);"))),
        ("orig_scale_changed", "V1.|V2.", OE("mgm", lambda x: rep1(x, "GL11.glScalef(1.15F, 1.15F, 1.15F);", "GL11.glScalef(1.1F, 1.1F, 1.1F);"))),
        ("orig_smelting_xp", "V1.|V3.", OE("sm", lambda x: rep1(x, "GameRegistry.addSmelting(ModItems.rag_damp, new ItemStack(ModItems.rag), 0.1F);", "GameRegistry.addSmelting(ModItems.rag_damp, new ItemStack(ModItems.rag), 0.2F);"))),
        # V7 GameTest source and log
        ("gt_marker_changed", "V7.", t(GT, 'TAG = "[hbm-gas-mask]"', 'TAG = "[hbm-gasmask]"'), GT),
        ("gt_batch_shared", "V7.", t(GT, 'batch = "gasmask_rags"', 'batch = "gasmask_recipes"'), GT),
        ("gt_test_removed", "V7.", t(GT, "public static void filter_wear(", "public static void filter_wear_x("), GT),
        ("gt_constant_from_neo", "V7.", t(GT, "stack.getMaxDamage() == 20000", "stack.getMaxDamage() == NtmItems.GAS_MASK_FILTER.get().getDefaultInstance().getMaxDamage()"), GT),
        ("gt_deleted", "V7.|V6.", D(GT), GT),
        ("log_total_changed", "V7.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 265 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", LT(lambda x: x.replace("[hbm-gas-mask] hazards passed", "")), "LOG"),
        ("log_failed_line", "V7.", LT(lambda x: x + "\n[12:00:00] Test gasmaskgametests.rags failed! required tests failed: 1\n"), "LOG"),
        ("log_protection_changed", "V7.", LT(lambda x: x.replace("hbmsntm:gas_mask_mono + hbmsntm:gas_mask_filter: [PARTICLE_COARSE, PARTICLE_FINE]",
                                                                  "hbmsntm:gas_mask_mono + hbmsntm:gas_mask_filter: [PARTICLE_COARSE, PARTICLE_FINE, GAS_LUNG]")), "LOG"),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for entry in mutations():
        label, prefixes, apply = entry[0], entry[1], entry[2]
        required = entry[3] if len(entry) > 3 else None
        if required == "LOG":
            if st.log_text is None:
                results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped="no --gametest-log")
                continue
        elif required is not None and not st.has(required):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree and mutated.log_text == st.log_text and not mutated.orig_edits:
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
        if mutated.files.get(GT) != st.files.get(GT):
            inp2 = copy.copy(inp2)
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
    out.setdefault("V8", [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec == "V8" and not items:
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
    if args.gametest_log:
        st.log_text = Path(args.gametest_log).read_text(encoding="utf-8", errors="replace")
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        v7 = facts.get("V7") or {}
        log = dict(v7.get("log") or {})
        log["log"] = str(args.gametest_log)
        log["log_sha256"] = sha(Path(args.gametest_log).read_bytes())
        extra["gametest_log"] = log
    if args.jar:
        extra["jar"] = guarded(ck, "V8", v8_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V9"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    changed, _ = changed_paths(inp, st)
    production = [p for p in changed if p.startswith("src/") and not p.startswith(GEN) and p not in RES_PATHS] + [ZH, MAP]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), checks_pending=ck.pendings(), mutations_detected=len(applied) - len(undetected),
                     mutations_applied=len(applied), mutations_total=len(muts), mutations_skipped=skipped),
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
