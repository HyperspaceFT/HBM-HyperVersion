"""Verify the Goal26C batch statically: the three hazmat suits (HazmatArmorItem, HazmatHelmetItem on NtmArmorMaterials HAZMAT / HAZMAT_RED /
HAZMAT_GREY), the three hazmat cloths, the HazmatRegistry default rows, ArmorUtil.checkForHazmat / checkArmor / the hood SAND lines / the shared
filter-eject helper, the HAZMAT contamination branch, the client extension, recipes, the assembly row ass.hazcloth, the armor enchantability tags,
language and the 24 imported resources; the scope of the batch and the GameTest source; with --gametest-log the GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal26c/verify/report.json. No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 8954b531.
- V1  The original parsed at the cited lines (HazmatRegistry, ArmorUtil, ContaminationUtil, MainRegistry, ModItems, ArmorHazmatMask, ArmorHazmat,
      ArmorRecipes, AssemblyMachineRecipes, CraftingManager, the language files); a moved line fails.
- V2  NEO source against V1: the 14 default rows and the unchanged config contract, the materials and durability, the hood class, the shared eject
      helper, SAND lines, checkForHazmat, checkArmor slot order, the HAZMAT branch position, the enum, the callers of HAZMAT, the client boundary,
      the overlay / ModelM65 split, the files that must stay byte-equal.
- V3  Generated resources: the 14 recipe JSONs against the original rows, 15 item models, en_us.json (15 keys), the enchantable item tags.
- V4  Language: zh_cn.json and the mapping (15 upstream), CRLF, insert-only against the start copies.
- V5  Resources: the 24 imports byte-equal to the original working tree, the two renames, the ownership record, every referenced texture exists.
- V6  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch (tools/ listed separately); records not yet written are pending.
- V7  GameTest source (HazmatSuitGameTests) and with --gametest-log the log.
- V8  (--jar) the packaged JAR; "not run" without the flag.
- V9  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal26c_hazmat.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal26c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "8954b53116965d964e2becdf2cee6b985b8e3356"

J = "src/main/java/com/hbm/"
HAI = J + "items/armor/HazmatArmorItem.java"
HHI = J + "items/armor/HazmatHelmetItem.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "HazmatSuitGameTests.java"
MAT = J + "registry/NtmArmorMaterials.java"
GMI = J + "items/armor/GasMaskItem.java"
EXT = J + "render/item/GasMaskClientExtensions.java"
AU = J + "util/ArmorUtil.java"
CU = J + "util/ContaminationUtil.java"
HR = J + "handler/HazmatRegistry.java"
ITEMS = J + "items/NtmItems.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
ASM = J + "inventory/recipes/AssemblyMachineRecipes.java"
CLIENT = J + "main/NuclearTechModClient.java"
ITP = J + "datagen/NtmItemTagProvider.java"
RECP = J + "datagen/NtmRecipeProvider.java"
IMP = J + "datagen/NtmItemModelProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
MAI = J + "items/armor/ModArmorItem.java"
M65 = J + "render/model/armor/ModelM65.java"
NEW_CLASSES = [HAI, HHI, GT]
EDITED = [MAT, GMI, EXT, AU, CU, HR, ITEMS, CTAB, ASM, CLIENT, ITP, RECP, IMP, LP]
COMMON = [HAI, HHI, AU, CU, HR, ITEMS, MAT, GMI]
IGM = "src/main/java/api/hbm/item/IGasMask.java"
AREG = J + "util/ArmorRegistry.java"
FIL = J + "items/tools/GasMaskFilterItem.java"
UNCHANGED = [IGM, AREG, FIL, MAI, M65, J + "handler/ArmorModHandler.java", J + "items/armor/ArmorNo9.java", J + "lib/ModEffect.java",
             J + "hazard/type/HazardTypeAsbestos.java", J + "main/NuclearTechMod.java", J + "main/CommonEvents.java",
             GT_DIR + "GasMaskGameTests.java", GT_DIR + "RadiationControlGameTests.java", GT_DIR + "HazardGameTests.java", GT_DIR + "SmokeTestSupport.java"]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal26c-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
RES = "src/main/resources/assets/hbmsntm/"
JARRES = "src/main/resources/"
O_RES = "src/main/resources/assets/hbm/"
TAGS = GEN + "data/minecraft/tags/item/"

O = "src/main/java/com/hbm/"
O_FILES = dict(hr=O + "handler/HazmatRegistry.java", au=O + "util/ArmorUtil.java", cu=O + "util/ContaminationUtil.java", mr=O + "main/MainRegistry.java",
               mi=O + "items/ModItems.java", ahm=O + "items/armor/ArmorHazmatMask.java", ah=O + "items/armor/ArmorHazmat.java", ar=O + "crafting/ArmorRecipes.java",
               asm=O + "inventory/recipes/AssemblyMachineRecipes.java", cm=O + "main/CraftingManager.java")
O_LANG = "src/main/resources/assets/hbm/lang/"

SUIT_IDS = ["hazmat_helmet", "hazmat_plate", "hazmat_legs", "hazmat_boots", "hazmat_helmet_red", "hazmat_plate_red", "hazmat_legs_red", "hazmat_boots_red",
            "hazmat_helmet_grey", "hazmat_plate_grey", "hazmat_legs_grey", "hazmat_boots_grey"]
CLOTH_IDS = ["hazmat_cloth", "hazmat_cloth_red", "hazmat_cloth_grey"]
ITEM_IDS = CLOTH_IDS + SUIT_IDS
MASKS_26B = ["gas_mask", "gas_mask_m65", "gas_mask_mono", "gas_mask_olde", "mask_rag", "mask_piss"]

# V1: every cited original line, {file key: {line: needle}}
ANCHORS = {
    "hr": {34: "public static double helmet = 0.2D;", 35: "public static double chest = 0.4D;", 36: "public static double legs = 0.3D;", 37: "public static double boots = 0.1D;",
           49: "double iron = 0.0225D;", 50: "double gold = 0.0225D;", 56: "double hazYellow = 0.6D;", 57: "double hazRed = 1.0D;", 58: "double hazGray = 2D;",
           68: "registerHazmat(ModItems.hazmat_helmet, hazYellow * helmet);", 69: "registerHazmat(ModItems.hazmat_plate, hazYellow * chest);",
           70: "registerHazmat(ModItems.hazmat_legs, hazYellow * legs);", 71: "registerHazmat(ModItems.hazmat_boots, hazYellow * boots);",
           73: "registerHazmat(ModItems.hazmat_helmet_red, hazRed * helmet);", 74: "registerHazmat(ModItems.hazmat_plate_red, hazRed * chest);",
           75: "registerHazmat(ModItems.hazmat_legs_red, hazRed * legs);", 76: "registerHazmat(ModItems.hazmat_boots_red, hazRed * boots);",
           78: "registerHazmat(ModItems.hazmat_helmet_grey, hazGray * helmet);", 79: "registerHazmat(ModItems.hazmat_plate_grey, hazGray * chest);",
           80: "registerHazmat(ModItems.hazmat_legs_grey, hazGray * legs);", 81: "registerHazmat(ModItems.hazmat_boots_grey, hazGray * boots);",
           110: "registerHazmat(ModItems.gas_mask, 0.07);", 111: "registerHazmat(ModItems.gas_mask_m65, 0.095);",
           128: "registerHazmat(Items.iron_helmet, iron * helmet);", 129: "registerHazmat(Items.iron_chestplate, iron * chest);", 130: "registerHazmat(Items.iron_leggings, iron * legs);",
           131: "registerHazmat(Items.iron_boots, iron * boots);", 133: "registerHazmat(Items.golden_helmet, gold * helmet);", 134: "registerHazmat(Items.golden_chestplate, gold * chest);",
           135: "registerHazmat(Items.golden_leggings, gold * legs);", 136: "registerHazmat(Items.golden_boots, gold * boots);",
           209: "for(int i = 0; i < 4; i++) {", 210: "res += getResistance(player.inventory.armorInventory[i]);", 213: "if(player.isPotionActive(HbmPotion.radx))", 214: "res += 0.2F;",
           227: "initDefault();", 229: "if(!config.exists()) {", 230: "writeDefault(template);", 235: "entries.clear();", 236: "entries.putAll(conf);",
           247: "Template file, remove the underscore ('_') from the name to enable the config."},
    "au": {57: "registerHazard(ModItems.hazmat_helmet, HazardClass.SAND);", 58: "registerHazard(ModItems.hazmat_helmet_red, HazardClass.SAND);",
           59: "registerHazard(ModItems.hazmat_helmet_grey, HazardClass.SAND);", 82: "public static boolean checkArmor(EntityLivingBase entity, Item... armor) {",
           84: "for(int i = 0; i < 4; i++) {", 85: "if(!checkArmorPiece(entity, armor[i], 3 - i))", 93: "entity.getEquipmentInSlot(slot + 1).getItem() == armor;",
           122: "public static boolean checkForHazmat(EntityLivingBase player) {",
           124: "checkArmor(player, ModItems.hazmat_helmet, ModItems.hazmat_plate, ModItems.hazmat_legs, ModItems.hazmat_boots) ||",
           125: "checkArmor(player, ModItems.hazmat_helmet_red, ModItems.hazmat_plate_red, ModItems.hazmat_legs_red, ModItems.hazmat_boots_red) ||",
           126: "checkArmor(player, ModItems.hazmat_helmet_grey, ModItems.hazmat_plate_grey, ModItems.hazmat_legs_grey, ModItems.hazmat_boots_grey) ||",
           127: "checkArmor(player, ModItems.schrabidium_helmet,", 128: "checkForHaz2(player)) {", 133: "if(player.isPotionActive(HbmPotion.mutation)) return true;"},
    "cu": {39: "float koeff = 10.0F;", 40: "return (float) Math.pow(koeff, -HazmatRegistry.getResistance(player));", 267: "if(hazard == HazardType.RADIATION) {",
           269: "HbmLivingProps.setRadEnv(entity, radEnv + amount);", 272: "if(entity instanceof EntityPlayer) {", 276: "switch(cont) {",
           277: "case FARADAY:", 278: "case HAZMAT:			if(ArmorUtil.checkForHazmat(player))	return false; break;", 279: "case HAZMAT2:", 280: "case DIGAMMA:", 281: "case DIGAMMA2:",
           284: "if(player.capabilities.isCreativeMode && cont != ContaminationType.NONE && cont != ContaminationType.DIGAMMA2)", 287: "if(player.ticksExisted < 200)",
           295: "cont == ContaminationType.RAD_BYPASS ? 1 : calculateRadiationMod(entity)"},
    "mr": {132: 'aMatHaz = EnumHelper.addArmorMaterial("HBM_HAZMAT", 60, new int[] { 2, 5, 4, 1 }, 5);', 133: 'aMatHaz2 = EnumHelper.addArmorMaterial("HBM_HAZMAT2", 60, new int[] { 2, 5, 4, 1 }, 5);',
           134: 'aMatHaz3 = EnumHelper.addArmorMaterial("HBM_HAZMAT3", 60, new int[] { 2, 5, 4, 1 }, 5);', 293: "aMatHaz.customCraftingMaterial = ModItems.hazmat_cloth;",
           294: "aMatHaz2.customCraftingMaterial = ModItems.hazmat_cloth_red;", 295: "aMatHaz3.customCraftingMaterial = ModItems.hazmat_cloth_grey;"},
    "mi": {2394: 'hazmat_cloth = new Item().setUnlocalizedName("hazmat_cloth")', 2395: 'hazmat_cloth_red = new Item().setUnlocalizedName("hazmat_cloth_red")',
           2396: 'hazmat_cloth_grey = new Item().setUnlocalizedName("hazmat_cloth_grey")', 4253: "hazmat_helmet = new ArmorHazmatMask(MainRegistry.aMatHaz, 0,",
           4254: "hazmat_plate = new ArmorHazmat(MainRegistry.aMatHaz, 1,", 4255: "hazmat_legs = new ArmorHazmat(MainRegistry.aMatHaz, 2,", 4256: "hazmat_boots = new ArmorHazmat(MainRegistry.aMatHaz, 3,",
           4257: "hazmat_helmet_red = new ArmorHazmatMask(MainRegistry.aMatHaz2, 0,", 4258: "hazmat_plate_red = new ArmorHazmat(MainRegistry.aMatHaz2, 1,",
           4259: "hazmat_legs_red = new ArmorHazmat(MainRegistry.aMatHaz2, 2,", 4260: "hazmat_boots_red = new ArmorHazmat(MainRegistry.aMatHaz2, 3,",
           4261: "hazmat_helmet_grey = new ArmorHazmatMask(MainRegistry.aMatHaz3, 0,", 4263: "hazmat_plate_grey = new ArmorHazmat(MainRegistry.aMatHaz3, 1,",
           4264: "hazmat_legs_grey = new ArmorHazmat(MainRegistry.aMatHaz3, 2,", 4265: "hazmat_boots_grey = new ArmorHazmat(MainRegistry.aMatHaz3, 3,"},
    "ahm": {20: "public class ArmorHazmatMask extends ArmorHazmat implements IGasMask {", 33: "if(this == ModItems.hazmat_helmet_red || this == ModItems.hazmat_helmet_grey) {",
            40: "return null;", 45: "return new ArrayList(); // full hood has no restrictions", 50: "return ArmorUtil.getGasMaskFilter(stack);", 55: "ArmorUtil.installGasMaskFilter(stack, filter);",
            60: "ArmorUtil.damageGasMaskFilter(stack, damage);", 65: "ArmorUtil.addGasMaskTooltip(stack, player, list, ext);", 67: "super.addInformation(stack, player, list, ext);",
            71: "public boolean isFilterApplicable(", 72: "return true;", 78: "if(player.isSneaking()) {", 83: "ArmorUtil.removeFilter(stack);",
            85: "if(!player.inventory.addItemStackToInventory(filter)) {", 86: "player.dropPlayerItemWithRandomChoice(filter, true);", 89: "return stack;",
            93: "return super.onItemRightClick(stack, world, player);"},
    "ah": {18: "public class ArmorHazmat extends ArmorFSB {", 20: 'new ResourceLocation(RefStrings.MODID + ":textures/misc/overlay_hazmat.png");',
           29: "if(this != ModItems.hazmat_helmet && this != ModItems.hazmat_paa_helmet)", 35: "OpenGlHelper.glBlendFunc(770, 771, 1, 0);", 41: "-90.0D, 0.0D, 1.0D);"},
    "ar": {122: "new ItemStack(ModItems.hazmat_helmet, 1)", 123: "new ItemStack(ModItems.hazmat_plate, 1)", 124: "new ItemStack(ModItems.hazmat_legs, 1)",
           125: "new ItemStack(ModItems.hazmat_boots, 1)", 126: "new ItemStack(ModItems.hazmat_helmet_red, 1)", 127: "new ItemStack(ModItems.hazmat_plate_red, 1)",
           128: "new ItemStack(ModItems.hazmat_legs_red, 1)", 129: "new ItemStack(ModItems.hazmat_boots_red, 1)", 130: "new ItemStack(ModItems.hazmat_helmet_grey, 1)",
           131: "new ItemStack(ModItems.hazmat_plate_grey, 1)", 132: "new ItemStack(ModItems.hazmat_legs_grey, 1)", 133: "new ItemStack(ModItems.hazmat_boots_grey, 1)"},
    "asm": {118: 'this.register(new GenericRecipe("ass.hazcloth").setup(50, 100).outputItems(new ItemStack(ModItems.hazmat_cloth, 4))',
            119: ".inputItems(new OreDictStack(PB.dust(), 4), new ComparableStack(Items.string, 8)));"},
    "cm": {101: "addRecipeAuto(new ItemStack(ModItems.hazmat_cloth_red, 1), new Object[] { \"C\", \"R\", \"C\", 'C', ModItems.hazmat_cloth, 'R', REDSTONE.dust() });",
           102: "addRecipeAuto(new ItemStack(ModItems.hazmat_cloth_grey, 1), new Object[] { \" P \", \"ICI\", \" L \", 'C', ModItems.hazmat_cloth_red, 'P', IRON.plate(), 'L', PB.plate(), 'I', ANY_RUBBER.ingot() });"},
}

# V3/V4: (NEO key, original key, en_US.lang line, zh_CN.lang line)
UP = [(f"item.hbmsntm.{i}", f"item.{i}.name", en, zh) for i, en, zh in (
    ("hazmat_boots", 3029, 2593), ("hazmat_boots_grey", 3030, 2594), ("hazmat_boots_red", 3031, 2595), ("hazmat_cloth", 3032, 2596), ("hazmat_cloth_grey", 3033, 2597),
    ("hazmat_cloth_red", 3034, 2598), ("hazmat_helmet", 3036, 2600), ("hazmat_helmet_grey", 3037, 2601), ("hazmat_helmet_red", 3038, 2602), ("hazmat_legs", 3040, 2604),
    ("hazmat_legs_grey", 3041, 2605), ("hazmat_legs_red", 3042, 2606), ("hazmat_plate", 3047, 2611), ("hazmat_plate_grey", 3048, 2612), ("hazmat_plate_red", 3049, 2613))]
NEW_KEYS = [u[0] for u in UP]

RENAMES = {"textures/models/ModelHazRed.png": "textures/models/model_haz_red.png", "textures/models/ModelHazGrey.png": "textures/models/model_haz_grey.png"}
# the 24 imports (original path under assets/hbm -> NEO path under assets/hbmsntm), independent of the import script
IMPORTS = [(f"textures/items/{i}.png", f"textures/item/{i}.png") for i in ITEM_IDS] + \
          [(f"textures/armor/{n}.png", f"textures/armor/{n}.png") for n in ("hazmat_1", "hazmat_2", "hazmat_1_red", "hazmat_2_red", "hazmat_1_grey", "hazmat_2_grey")] + \
          list(RENAMES.items()) + [("textures/misc/overlay_hazmat.png", "textures/misc/overlay_hazmat.png")]
RES_PATHS = [RES + n for _, n in IMPORTS]

R = "hbmsntm:"
EXPR = {"KEY_ANYPANE": {"tag": "c:glass_panes"}, "IRON.plate()": {"item": R + "plate_iron"}, "PB.plate()": {"item": R + "plate_lead"},
        "REDSTONE.dust()": {"item": "minecraft:redstone"}, "ANY_RUBBER.ingot()": {"tag": "ntm:any_rubbers"},
        "ModItems.hazmat_cloth": {"item": R + "hazmat_cloth"}, "ModItems.hazmat_cloth_red": {"item": R + "hazmat_cloth_red"}, "ModItems.hazmat_cloth_grey": {"item": R + "hazmat_cloth_grey"}}
# (NEO recipe id, original file key, line, recipe category, advancement folder)
RECIPES = [(i, "ar", 122 + n, "equipment", "combat") for n, i in enumerate(SUIT_IDS)] + [("hazmat_cloth_red", "cm", 101, "misc", "misc"), ("hazmat_cloth_grey", "cm", 102, "misc", "misc")]
RECIPE_DIR = GEN + "data/hbmsntm/recipe/"
ADV_ROOT = GEN + "data/hbmsntm/advancement/recipes/"
ENCH_SLOT = ["head_armor", "chest_armor", "leg_armor", "foot_armor"]
ENCH_TAGS = [TAGS + f"enchantable/{s}.json" for s in ENCH_SLOT] + [TAGS + "enchantable/durability.json", TAGS + "enchantable/equippable.json"]
VANILLA_ARMOR_TAGS = [TAGS + f"{s}.json" for s in ENCH_SLOT] + [TAGS + "trimmable_armor.json"]
GEN_NEW = [f"{GEN}assets/hbmsntm/models/item/{i}.json" for i in ITEM_IDS] + [f"{RECIPE_DIR}{r[0]}.json" for r in RECIPES] + \
          [f"{ADV_ROOT}{r[4]}/{r[0]}.json" for r in RECIPES] + ENCH_TAGS
GEN_MODIFIED = [STAMP, EN]

GT_MARK = "[hbm-hazmat]"
START_GAMETESTS = 266
GT_TESTS = ("radiation_resistance", "contamination", "check_for_hazmat", "helmet_filters", "config_table", "recipes_and_durability", "enchantability")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                 "migration/GOAL26.md", "migration/GOAL26C.md", "migration/GOAL26C-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal26c-",)
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/GOAL26.md",
                    "migration/GOAL26C-ACCEPTANCE.md"]


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


# ---------------------------------------------------------------- text helpers (as verify_goal26b_gas_masks.py)

@functools.lru_cache(maxsize=512)
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


def without_method(text, signature):
    """The squashed code of text with the whole method (signature to closing brace) removed."""
    t = lf(text)
    o, c, code = method_span(t, signature)
    start = code.index(signature)
    return sq(code[:start] + code[c + 1:])


@functools.lru_cache(maxsize=256)
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
        e = re.sub(rf"\b{k}\b", f"({v!r})", e)
    if not re.fullmatch(r"[\d.+\-*/() e]+", e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))  # noqa: S307 - digits and operators only (checked above)
    except Exception:  # noqa: BLE001
        return None


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
    load = set(NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, OWN, EN, STAMP] + RES_PATHS + GEN_NEW + gen_all + VANILLA_ARMOR_TAGS + RECORDS_REQUIRED)
    # every Java source (the HAZMAT caller scan and the client-reference scan read them all)
    load |= {p for p in tree if p.startswith("src/main/java/") and p.endswith(".java")}
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

def orig_parts(inp):
    """HazmatRegistry.java:34-37 -> {helmet: 0.2, chest: 0.4, legs: 0.3, boots: 0.1}."""
    out = {}
    for n in range(34, 38):
        m = re.fullmatch(r"publicstaticdouble(\w+)=([\d.]+);", oline(inp, "hr", n))
        if m:
            out[m[1]] = float(m[2])
    return out


def orig_suits(inp):
    out = {}
    for n in range(56, 59):
        m = re.fullmatch(r"double(haz\w+)=([\d.]+);", oline(inp, "hr", n))
        if m:
            out[m[1]] = float(m[2])
    return out


def orig_table(inp):
    """The 14 rows (68-81, 110-111) and the iron / gold rows (128-136) as {item: value}, values from the original expressions."""
    parts, suits = orig_parts(inp), orig_suits(inp)
    env = dict(parts)
    env.update(suits)
    for n in (49, 50):
        m = re.fullmatch(r"double(\w+)=([\d.]+);", oline(inp, "hr", n))
        if m:
            env[m[1]] = float(m[2])
    rows, vanilla = {}, {}
    for n in list(range(68, 82)) + [110, 111]:
        m = re.fullmatch(r"HazmatRegistry\.registerHazmat\(ModItems\.(\w+),(.*)\);", oline(inp, "hr", n))
        if m:
            rows[m[1]] = num(m[2], env)
    for n in list(range(128, 132)) + list(range(133, 137)):
        m = re.fullmatch(r"HazmatRegistry\.registerHazmat\(Items\.(\w+),(.*)\);", oline(inp, "hr", n))
        if m:
            vanilla[m[1]] = num(m[2], env)
    return rows, vanilla, env


def orig_sand(inp):
    return [m[1] for m in (re.fullmatch(r"ArmorRegistry\.registerHazard\(ModItems\.(\w+),HazardClass\.SAND\);", oline(inp, "au", n)) for n in (57, 58, 59)) if m]


def orig_hazmat_sets(inp):
    """ArmorUtil.java:124-126: the three migrated full sets in argument order."""
    out = []
    for n in (124, 125, 126):
        m = re.search(r"checkArmor\(player,ModItems\.(\w+),ModItems\.(\w+),ModItems\.(\w+),ModItems\.(\w+)\)", oline(inp, "au", n))
        out.append(list(m.groups()) if m else None)
    return out


# 1.7.10 getEquipmentInSlot index -> 1.21 equipment slot (0 is the held item)
EQUIP_1710 = {4: "HEAD", 3: "CHEST", 2: "LEGS", 1: "FEET"}


def orig_check_armor_order(inp):
    """ArmorUtil.java:84-93: armor[i] is checked at slot (3 - i), read as getEquipmentInSlot(slot + 1)."""
    m1 = re.search(r"checkArmorPiece\(entity,armor\[i\],(\d+)-i\)", oline(inp, "au", 85))
    m2 = re.search(r"getEquipmentInSlot\(slot\+(\d+)\)", oline(inp, "au", 93))
    if not (m1 and m2):
        return None
    return [EQUIP_1710.get(int(m1[1]) - i + int(m2[1])) for i in range(4)]


def orig_items(inp):
    """ModItems.java:4253-4265 -> {id: (class, material, slot, texture)}."""
    out = {}
    text = olines(inp, "mi", 4253, 4265)
    for m in re.finditer(r"(\w+)=new(ArmorHazmatMask|ArmorHazmat)\(MainRegistry\.(\w+),(\d),(?:RefStrings\.MODID\+\":([\w/]+\.png)\"|\"hbm:([\w/]+\.png)\")\)", text):
        out[m[1]] = (m[2], m[3], int(m[4]), m[5] or m[6])
    return out


def orig_materials(inp):
    out = {}
    for n in (132, 133, 134):
        m = re.search(r"(aMat\w+)=EnumHelper\.addArmorMaterial\(\"(\w+)\",(\d+),newint\[\]\{([\d,]+)\},(\d+)\);", oline(inp, "mr", n))
        if m:
            out[m[1]] = dict(factor=int(m[3]), defense=[int(x) for x in m[4].split(",")], ench=int(m[5]))
    for n in (293, 294, 295):
        m = re.fullmatch(r"(\w+)\.customCraftingMaterial=ModItems\.(\w+);", oline(inp, "mr", n))
        if m and m[1] in out:
            out[m[1]]["repair"] = m[2]
    return out


def orig_m65(inp):
    return set(re.findall(r"ModItems\.(\w+)", oline(inp, "ahm", 33)))


def orig_overlay(inp):
    """ArmorHazmat.java:29: the overlay is drawn for hazmat_helmet and the PAA helmet (not migrated)."""
    return set(re.findall(r"this!=ModItems\.(\w+)", oline(inp, "ah", 29))) - {"hazmat_paa_helmet"}


def orig_switch_order(inp):
    """ContaminationUtil.java:276-288 line numbers of the switch, the HAZMAT case, the creative check and the tick check."""
    return dict(switch=276, hazmat=278, creative=284, ticks=287)


MATERIAL_CONST = {"aMatHaz": "HAZMAT", "aMatHaz2": "HAZMAT_RED", "aMatHaz3": "HAZMAT_GREY"}
MATERIAL_ID = {"aMatHaz": "hazmat", "aMatHaz2": "hazmat_red", "aMatHaz3": "hazmat_grey"}
TYPES = ["HELMET", "CHESTPLATE", "LEGGINGS", "BOOTS"]


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]) and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 8954b531", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 8954b531 (the batch is uncommitted)", inp.neo_head)
    needed = NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, EN, STAMP] + GEN_NEW + RES_PATHS
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified, unchanged-reference and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in EDITED + [ZH, MAP, EN] if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start copy of every edited file exists in baseline-files", starts)


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    parts = orig_parts(inp)
    ck("V1.parts", parts == {"helmet": 0.2, "chest": 0.4, "legs": 0.3, "boots": 0.1}, "HazmatRegistry.java:34-37 part factors 0.2 / 0.4 / 0.3 / 0.1", parts)
    rows, vanilla, env = orig_table(inp)
    ck("V1.rows", len(rows) == 14 and None not in rows.values() and len(vanilla) == 8 and None not in vanilla.values(),
       "HazmatRegistry.java:68-81,110-111 give 14 rows and :128-136 the 8 iron / gold rows, all evaluable", (rows, vanilla))
    sets = orig_hazmat_sets(inp)
    ck("V1.hazmat-sets", None not in sets and [s[0] for s in sets] == ["hazmat_helmet", "hazmat_helmet_red", "hazmat_helmet_grey"], "ArmorUtil.java:124-126 the three suit sets", sets)
    ck("V1.check-armor-order", orig_check_armor_order(inp) == ["HEAD", "CHEST", "LEGS", "FEET"], "ArmorUtil.java:82-94: armor[0..3] -> HEAD, CHEST, LEGS, FEET", orig_check_armor_order(inp))
    ck("V1.sand", orig_sand(inp) == ["hazmat_helmet", "hazmat_helmet_red", "hazmat_helmet_grey"], "ArmorUtil.java:57-59 SAND for the three hoods", orig_sand(inp))
    o = orig_switch_order(inp)
    ck("V1.hazmat-before-creative", o["switch"] < o["hazmat"] < o["creative"] < o["ticks"] and "checkForHazmat" in oline(inp, "cu", o["hazmat"])
       and "isCreativeMode" in oline(inp, "cu", o["creative"]), "ContaminationUtil.java:276-288: the HAZMAT case precedes the creative and tick exemptions")
    items = orig_items(inp)
    ck("V1.items", sorted(items) == sorted(SUIT_IDS), "ModItems.java:4253-4265 define the twelve suit pieces (class, material, slot, texture)", items)
    mats = orig_materials(inp)
    ck("V1.materials", sorted(mats) == ["aMatHaz", "aMatHaz2", "aMatHaz3"] and all("repair" in m for m in mats.values()), "MainRegistry.java:132-134,293-295 three materials with repair cloths", mats)
    ck("V1.m65-overlay", orig_m65(inp) == {"hazmat_helmet_red", "hazmat_helmet_grey"} and orig_overlay(inp) == {"hazmat_helmet"},
       "ArmorHazmatMask.java:33 ModelM65 for red and grey; ArmorHazmat.java:29 overlay for hazmat_helmet", (orig_m65(inp), orig_overlay(inp)))
    for neo, okey, en_line, zh_line in UP:
        e, z = inp.o_en.get(okey), inp.o_zh.get(okey)
        ck(f"V1.lang-{okey}", e is not None and len(e) == 1 and e[0][1] == en_line and z is not None and len(z) == 1 and z[0][1] == zh_line,
           f"{okey} once in en_US.lang:{en_line} and zh_CN.lang:{zh_line}", (e, z))


# ---------------------------------------------------------------- V2 NEO source vs original

NEO_ROW = re.compile(r"HazmatRegistry\.registerHazmat\(NtmItems\.(\w+)\.get\(\),(.*?)\);")
NEO_VROW = re.compile(r"HazmatRegistry\.registerHazmat\(Items\.(\w+),(.*?)\);")


def v2_source(ck, inp, st):
    hr, shr = st.text(HR), inp.start[HR]
    init = body(hr, "public static void initDefault()")
    sinit = body(shr, "public static void initDefault()")
    ck("V2.initdefault-start-prefix", init.startswith(sinit) and len(init) > len(sinit), "initDefault keeps its start body (part factors, iron and gold rows) and only appends",
       difflib.SequenceMatcher(None, sinit, init[:len(sinit)]).get_opcodes()[:3])
    env = {}
    for m in re.finditer(r"double(\w+)=([\d.]+);", init):
        env[m[1]] = float(m[2])
    parts = orig_parts(inp)
    ck("V2.part-factors", all(env.get(k) == v for k, v in parts.items()), "the NEO part factors equal HazmatRegistry.java:34-37", {k: env.get(k) for k in parts})
    suits = orig_suits(inp)
    ck("V2.suit-values", all(env.get(k) == v for k, v in suits.items()), "hazYellow / hazRed / hazGray equal HazmatRegistry.java:56-58", {k: env.get(k) for k in suits})
    rows, vanilla, oenv = orig_table(inp)
    neo_rows = {m[1].lower(): num(m[2], env) for m in NEO_ROW.finditer(init)}
    want = {k: v for k, v in rows.items()}
    wrong = {k: (neo_rows.get(k), v) for k, v in want.items() if neo_rows.get(k) is None or abs(neo_rows[k] - v) > 1e-12}
    extra = sorted(set(neo_rows) - set(want))
    ck("V2.default-rows", not wrong and not extra and len(neo_rows) == 14 and len(NEO_ROW.findall(init)) == 14,
       "initDefault registers exactly the 14 original rows (twelve suit pieces, gas_mask 0.07, gas_mask_m65 0.095) with their values", (wrong, extra))
    neo_v = {m[1].lower(): num(m[2], env) for m in NEO_VROW.finditer(init)}
    vw = {k: (neo_v.get(k), v) for k, v in vanilla.items() if neo_v.get(k) is None or abs(neo_v[k] - v) > 1e-12}
    ck("V2.vanilla-rows", not vw and len(neo_v) == 8, "the 8 iron / gold rows equal HazmatRegistry.java:128-136", vw)
    sigs = ["public static void registerHazmats()", "private static void writeDefault(File file)", "public static HashMap<Item, Double> readConfig(File config)",
            "public static float getResistance(Player player)", "public static double getResistance(Level level, ItemStack stack)", "public static double getCladding(Level level, ItemStack stack)",
            "private static void registerHazmat(Item item, double resistance)", "public static void addInfo(List<Component> components, Level level, ItemStack stack)"]
    changed = [s for s in sigs if body(hr, s) != body(shr, s)]
    ck("V2.config-contract", not changed and "privatestaticfinalHashMap<Item,Double>ENTRIES=newHashMap<>();" in code_of(hr),
       "registerHazmats / writeDefault / readConfig / getResistance / getCladding / addInfo are unchanged against the start (whole-table replacement, template from ENTRIES)", changed)
    ck("V2.config-orig", ordered(olines(inp, "hr", 221, 239), "initDefault();", "if(!config.exists()){writeDefault(template);}", "entries.clear();entries.putAll(conf);")
       and ordered(body(hr, "public static void registerHazmats()"), "initDefault();", "if(!config.exists()){writeDefault(template);}", "ENTRIES.clear();ENTRIES.putAll(conf);"),
       "registerHazmats has the original order: defaults, then template or whole-table replacement (HazmatRegistry.java:221-239)")
    gr = body(hr, "public static float getResistance(Player player)")
    ck("V2.get-resistance", ordered(gr, "for(inti=0;i<4;i++){", "res+=(float)getResistance(player.level(),player.getInventory().armor.get(i));", "if(player.hasEffect(ModEffect.RADX))res+=0.2;")
       and "res+=0.2" in oline(inp, "hr", 214), "getResistance sums the four armor slots and adds 0.2 for RADX (HazmatRegistry.java:209-214)")

    # materials
    mats = orig_materials(inp)
    mat = code_of(st.text(MAT))
    for oname, m in mats.items():
        d = m["defense"]
        want_m = (f'ARMOR_MATERIALS.register("{MATERIAL_ID[oname]}",()->newArmorMaterial(defense({d[3]},{d[2]},{d[1]},{d[0]}),{m["ench"]},SoundEvents.ARMOR_EQUIP_LEATHER,'
                  f'()->Ingredient.of(NtmItems.{m["repair"].upper()}.get()),List.of(newArmorMaterial.Layer(NuclearTechMod.withDefaultNamespace("{MATERIAL_ID[oname]}"))),0,0));')
        ck(f"V2.material-{MATERIAL_ID[oname]}", want_m in mat, f"{MATERIAL_CONST[oname]}: defense {d} (helmet..boots), enchantability {m['ench']}, repaired with {m['repair']}, hbmsntm:{MATERIAL_ID[oname]} "
           f"(MainRegistry.java:132-134,293-295)", want_m)
    ck("V2.defense-helper", "privatestaticEnumMap<ArmorItem.Type,Integer>defense(intboots,intleggings,intchestplate,inthelmet){" in mat
       and ordered(mat, "map.put(ArmorItem.Type.BOOTS,boots);", "map.put(ArmorItem.Type.LEGGINGS,leggings);", "map.put(ArmorItem.Type.CHESTPLATE,chestplate);", "map.put(ArmorItem.Type.HELMET,helmet);"),
       "defense(boots, leggings, chestplate, helmet) maps each argument to its own type")

    # items
    items = code_of(st.text(ITEMS))
    oitems = orig_items(inp)
    m65, overlay = orig_m65(inp), orig_overlay(inp)
    bad = {}
    for iid, (cls, omat, slot, tex) in oitems.items():
        factor = mats.get(omat, {}).get("factor")
        neo_tex = RENAMES.get(tex, tex)
        t = TYPES[slot]
        if cls == "ArmorHazmatMask":
            ov = 'NuclearTechMod.withDefaultNamespace("textures/misc/overlay_hazmat.png")' if iid in overlay else "null"
            want_i = (f'ITEMS.register("{iid}",()->newHazmatHelmetItem(NtmArmorMaterials.{MATERIAL_CONST[omat]},newItem.Properties().durability(ArmorItem.Type.{t}.getDurability({factor})),'
                      f'NuclearTechMod.withDefaultNamespace("{neo_tex}"),{"true" if iid in m65 else "false"},{ov}));')
        else:
            want_i = (f'ITEMS.register("{iid}",()->newHazmatArmorItem(NtmArmorMaterials.{MATERIAL_CONST[omat]},ArmorItem.Type.{t},newItem.Properties().durability(ArmorItem.Type.{t}.getDurability({factor})),'
                      f'NuclearTechMod.withDefaultNamespace("{neo_tex}")));')
        if want_i not in items:
            bad[iid] = want_i
    ck("V2.suit-items", not bad and len(oitems) == 12, "the twelve suit pieces: class (hood / piece), material, type, durability getDurability(60), worn texture (lowercase renames), "
       "ModelM65 only for red and grey, the overlay only for hazmat_helmet (ModItems.java:4253-4265, ArmorHazmatMask.java:33, ArmorHazmat.java:29)", bad)
    ck("V2.cloth-items", all(f'ITEMS.register("{c}",()->newItem(newItem.Properties()));' in items for c in CLOTH_IDS)
       and all(f'{c}=newItem().setUnlocalizedName("{c}")' in oline(inp, "mi", 2394 + n) for n, c in enumerate(CLOTH_IDS)), "the three cloths are plain items (ModItems.java:2394-2396)")

    # the hood and the plain piece classes
    hh, ha = st.text(HHI), st.text(HAI)
    hcode, acode = code_of(hh), code_of(ha)
    ck("V2.hood-class", "publicclassHazmatHelmetItemextendsHazmatArmorItemimplementsIGasMask{" in hcode and "super(material,ArmorItem.Type.HELMET,properties,wornTexture);" in hcode,
       "HazmatHelmetItem extends HazmatArmorItem implements IGasMask, a HELMET (ArmorHazmatMask.java:20)")
    ck("V2.piece-class", re.fullmatch(r".*publicclassHazmatArmorItemextendsModArmorItem\{publicHazmatArmorItem\(Holder<ArmorMaterial>material,ArmorItem\.Typetype,Propertiesproperties,ResourceLocationwornTexture\)\{super\(material,type,properties,wornTexture\);\}\}", acode) is not None,
       "HazmatArmorItem extends ModArmorItem with only the constructor (ArmorHazmat without the ArmorFSB set bonus, ArmorHazmat.java:18)")
    ck("V2.hood-blacklist", body(hh, "public ArrayList<HazardClass> getBlacklist(ItemStack stack, LivingEntity entity)") == "returnnewArrayList<>();" and "returnnewArrayList();" in oline(inp, "ahm", 45),
       "getBlacklist returns a new empty list (ArmorHazmatMask.java:43-46)")
    ck("V2.hood-filter-applicable", body(hh, "public boolean isFilterApplicable(ItemStack stack, LivingEntity entity, ItemStack filter)") == "returntrue;" and oline(inp, "ahm", 72) == "returntrue;",
       "isFilterApplicable always returns true (ArmorHazmatMask.java:70-73)")
    ck("V2.hood-filter-delegation", body(hh, "public ItemStack getFilter(ItemStack stack, LivingEntity entity)") == "returnArmorUtil.getGasMaskFilter(entity.level(),stack);"
       and body(hh, "public void installFilter(ItemStack stack, LivingEntity entity, ItemStack filter)") == "ArmorUtil.installGasMaskFilter(entity.level(),stack,filter);"
       and body(hh, "public void damageFilter(ItemStack stack, LivingEntity entity, int damage)") == "ArmorUtil.damageGasMaskFilter(entity.level(),stack,damage);",
       "the three filter methods delegate to ArmorUtil exactly as GasMaskItem does (ArmorHazmatMask.java:48-61)")
    gm = st.text(GMI)
    ck("V2.gasmask-delegation-same", all(body(hh, s) == body(gm, s) for s in ("public ItemStack getFilter(ItemStack stack, LivingEntity entity)",
                                                                           "public void installFilter(ItemStack stack, LivingEntity entity, ItemStack filter)",
                                                                           "public void damageFilter(ItemStack stack, LivingEntity entity, int damage)")),
       "the hood's filter methods are the gas mask's")
    ck("V2.hood-tooltip", ordered(body(hh, "public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> components, TooltipFlag flag)"),
                                  "ArmorUtil.addGasMaskTooltip(stack,context,components,flag);", "super.appendHoverText(stack,context,components,flag);"),
       "the tooltip adds the filter lines first, then super (ArmorHazmatMask.java:63-68)")
    use_sig = "public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)"
    use_want = "ItemStackstack=player.getItemInHand(hand);if(ArmorUtil.ejectGasMaskFilter(this,stack,level,player)){returnInteractionResultHolder.sidedSuccess(stack,level.isClientSide());}returnsuper.use(level,player,hand);"
    huse, guse = body(hh, use_sig), body(gm, use_sig)
    ck("V2.shared-eject", huse == use_want and guse == use_want, "HazmatHelmetItem.use and GasMaskItem.use both call ArmorUtil.ejectGasMaskFilter and fall through to super", (huse, guse))
    dup = [p for p, t in ((HHI, hh), (GMI, gm)) if re.search(r"removeFilter\(|player\.drop\(|getInventory\(\)\.add\(|isShiftKeyDown\(", code_of(t))]
    ck("V2.no-duplicated-eject", not dup, "neither item class carries its own eject body (removeFilter / drop / inventory add / sneak test)", dup)
    au = st.text(AU)
    ej = body(au, "public static boolean ejectGasMaskFilter(IGasMask mask, ItemStack stack, Level level, Player player)")
    ck("V2.eject-helper", ordered(ej, "if(!player.isShiftKeyDown())returnfalse;", "ItemStackfilter=mask.getFilter(stack,player);", "if(filter.isEmpty())returnfalse;",
                                  "if(!level.isClientSide()){", "removeFilter(stack);", "if(!player.getInventory().add(filter)){", "player.drop(filter,true,false);", "returntrue;")
       and ordered(olines(inp, "ahm", 76, 94), "if(player.isSneaking()){", "ItemStackfilter=this.getFilter(stack,player);", "if(filter!=null){", "ArmorUtil.removeFilter(stack);",
                   "if(!player.inventory.addItemStackToInventory(filter)){", "player.dropPlayerItemWithRandomChoice(filter,true);", "returnstack;", "returnsuper.onItemRightClick(stack,world,player);"),
       "ArmorUtil.ejectGasMaskFilter: sneaking + a filter -> removed, into the inventory else dropped around, change on the server only (ArmorHazmatMask.java:75-94)")
    sgm = inp.start[GMI]
    ck("V2.gasmask-only-use-changed", without_method(gm, use_sig) == without_method(sgm, use_sig), "GasMaskItem changed only in use() (blacklists, protection, overlays, tooltip unchanged)")
    ck("V2.gasmask-blacklist", body(gm, "public ArrayList<HazardClass> getBlacklist(ItemStack stack, LivingEntity entity)") == body(sgm, "public ArrayList<HazardClass> getBlacklist(ItemStack stack, LivingEntity entity)"),
       "the 26B mask blacklists are unchanged")

    # ArmorUtil register / checkArmor / checkForHazmat
    reg, sreg = body(au, "public static void register()"), body(inp.start[AU], "public static void register()")
    sand = "".join(f"ArmorRegistry.registerHazard(NtmItems.{i.upper()}.get(),HazardClass.SAND);" for i in orig_sand(inp))
    ck("V2.sand-lines", reg == sreg + sand and len(orig_sand(inp)) == 3, "register() is the start body (26B lines unchanged) plus SAND for the three hoods, in order (ArmorUtil.java:57-59)",
       reg[len(sreg):] if reg.startswith(sreg) else reg[:300])
    order = orig_check_armor_order(inp)
    ca = body(au, "public static boolean checkArmor(LivingEntity entity, Item... armor)")
    ck("V2.check-armor-order", order is not None and f"EquipmentSlot[]slots={{{','.join('EquipmentSlot.' + s for s in order)}}};" in ca
       and "for(inti=0;i<slots.length;i++){if(!checkArmorPiece(entity,armor[i],slots[i])){returnfalse;}}returntrue;" in ca,
       "checkArmor checks armor[0..3] against HEAD, CHEST, LEGS, FEET (ArmorUtil.java:82-94: slot 3 - i, getEquipmentInSlot(slot + 1))", ca)
    sets = orig_hazmat_sets(inp)
    cfh = body(au, "public static boolean checkForHazmat(LivingEntity entity)")
    want_c = "if(" + "||".join("checkArmor(entity," + ",".join(f"NtmItems.{x.upper()}.get()" for x in s) + ")" for s in sets if s) + "){returntrue;}returnentity.hasEffect(ModEffect.MUTATION);"
    ck("V2.check-for-hazmat", cfh == want_c and "HbmPotion.mutation" in oline(inp, "au", 133),
       "checkForHazmat: the three original sets in argument order or the mutation effect, no other set (ArmorUtil.java:122-135)", cfh)
    ck("V2.check-for-hazmat-not-deprecated", "@Deprecatedpublicstaticbooleancheck" not in code_of(au), "checkForHazmat carries no @Deprecated (handoff 3c)")

    # ContaminationUtil
    cu, scu = st.text(CU), inp.start[CU]
    sig = "public static void contaminate(LivingEntity entity, HazardType hazard, ContaminationType type, float amount)"
    con, scon = body(cu, sig), body(scu, sig)
    hz = "if(type==ContaminationType.HAZMAT&&ArmorUtil.checkForHazmat(player))return;"
    ck("V2.hazmat-branch-position", con == scon.replace("if(entityinstanceofPlayerplayer){", "if(entityinstanceofPlayerplayer){" + hz, 1)
       and ordered(con, "if(entityinstanceofPlayerplayer){", hz, "if((player.isCreative()||player.isSpectator())", "if(player.tickCount<200)return;"),
       "contaminate is the start body plus the HAZMAT return as the first statement of the Player block, before the creative and tick exemptions (ContaminationUtil.java:272-288)", con[:500])
    ck("V2.no-other-branches", not re.search(r"ContaminationType\.(FARADAY|HAZMAT_HEAVY|DIGAMMA)(?!_)", con) and con.count("ContaminationType.HAZMAT") == 1,
       "no FARADAY / HAZMAT_HEAVY / DIGAMMA branch is wired (handoff 5)")
    en_sig = "public enum ContaminationType"
    ck("V2.enum-unchanged", body(cu, en_sig) == body(scu, en_sig), "the ContaminationType enum is unchanged")
    ck("V2.contamination-rest", without_method(cu, sig) == without_method(scu, sig), "ContaminationUtil changed only inside contaminate()")
    callers = sorted(p for p, data in st.files.items() if p.startswith("src/main/java/") and p.endswith(".java") and p != CU and not p.startswith(GT_DIR)
                     and re.search(r"ContaminationType\.HAZMAT\b(?!_)", blank_comments(lf(data.decode("utf-8")))))
    ck("V2.no-hazmat-callers", not callers, "no production caller passes ContaminationType.HAZMAT (scan of every src/main/java file outside gametest/): " + (", ".join(callers) or "none"), callers)

    # client
    ext = code_of(st.text(EXT))
    ck("V2.client-hood-model", "if(stack.getItem()instanceofHazmatHelmetItemhood){returnhood.isM65Model()?m65(living):original;}" in ext,
       "the extension gives the hoods ModelM65 when m65Model, else the standard helmet layer (ArmorHazmatMask.java:31-41)")
    ck("V2.client-hood-overlay", "if(stack.getItem()instanceofHazmatHelmetItemhood){ResourceLocationtex=hood.getOverlay();if(tex!=null)drawOverlay(guiGraphics,tex);return;}" in ext
       and ordered(body(st.text(EXT), "private static void drawOverlay(GuiGraphics guiGraphics, ResourceLocation tex)"), "RenderSystem.disableDepthTest();", "RenderSystem.depthMask(false);",
                   "RenderSystem.blendFuncSeparate(GlStateManager.SourceFactor.SRC_ALPHA,GlStateManager.DestFactor.ONE_MINUS_SRC_ALPHA,GlStateManager.SourceFactor.ONE,GlStateManager.DestFactor.ZERO);",
                   "guiGraphics.blit(tex,0,0,-90,0.0,0.0,guiGraphics.guiWidth(),guiGraphics.guiHeight(),guiGraphics.guiWidth(),guiGraphics.guiHeight());", "RenderSystem.depthMask(true);", "RenderSystem.enableDepthTest();")
       and "OpenGlHelper.glBlendFunc(770,771,1,0);" in oline(inp, "ah", 35),
       "the hood overlay is its fixed texture through the shared full-screen draw (blend 770/771/1/0, z -90; ArmorHazmat.java:26-50)")
    ck("V2.client-m65-filter", "this.modelM65.filter.visible=!ArmorUtil.getGasMaskFilterRecursively(living.getItemBySlot(EquipmentSlot.HEAD),living).isEmpty();" in ext,
       "ModelM65's filter part follows the installed filter for the hoods too")
    cl = code_of(st.text(CLIENT))
    ck("V2.client-registration", "event.registerItem(newGasMaskClientExtensions(),NtmItems.GAS_MASK.get(),NtmItems.GAS_MASK_M65.get(),NtmItems.GAS_MASK_MONO.get(),NtmItems.GAS_MASK_OLDE.get(),"
       "NtmItems.HAZMAT_HELMET.get(),NtmItems.HAZMAT_HELMET_RED.get(),NtmItems.HAZMAT_HELMET_GREY.get());" in cl,
       "NuclearTechModClient registers the extension for the four masks and the three hoods")
    leaks = {}
    for p in COMMON:
        c = blank_comments(lf(st.text(p)))
        hits = [w for w in ("net.minecraft.client", "GasMaskClientExtensions", "ModelGasMask", "ModelM65", "IClientItemExtensions", "com.hbm.render", "com.mojang.blaze3d") if w in c]
        if hits:
            leaks[p.rsplit("/", 1)[1]] = hits
    refs = [p for p in st.files if p.startswith("src/main/java/") and p.endswith(".java") and p not in (EXT, CLIENT)
            and re.search(r"\bGasMaskClientExtensions\b", blank_comments(lf(st.text(p))))]
    ck("V2.client-boundary", not leaks and not refs, "HazmatArmorItem, HazmatHelmetItem, ArmorUtil, ContaminationUtil, HazmatRegistry, NtmItems, NtmArmorMaterials and GasMaskItem "
       "reference no client class; GasMaskClientExtensions is referenced only from NuclearTechModClient", (leaks, refs))

    unchanged = [p for p in UNCHANGED if st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.unchanged-files", not unchanged, "IGasMask, ArmorRegistry, GasMaskFilterItem, ModArmorItem, ModelM65, ArmorModHandler, ArmorNo9, ModEffect, HazardTypeAsbestos, "
       "NuclearTechMod, CommonEvents and the older GameTests are byte-equal to the start", unchanged)

    # assembly row
    asm = code_of(st.text(ASM))
    dur = onum(inp, "asm", 118, r"\.setup\((\d+),")
    pw = onum(inp, "asm", 118, r"\.setup\(\d+,(\d+)\)")
    oc = onum(inp, "asm", 118, r"hazmat_cloth,(\d+)\)\)")
    ins = re.findall(r"\((?:PB\.dust\(\)|Items\.(\w+)),(\d+)\)", oline(inp, "asm", 119))
    want_a = (f'this.register(newGenericRecipe("ass.hazcloth").setup({dur},{pw}).outputItems(newItemStack(NtmItems.HAZMAT_CLOTH.get(),{oc})).inputItems('
              f'newComparableStack(NtmItems.POWDER_LEAD.get(),{ins[0][1] if ins else "?"}),newComparableStack(net.minecraft.world.item.Items.STRING,{ins[1][1] if len(ins) > 1 else "?"})));')
    ck("V2.assembly-hazcloth", want_a in asm and len(ins) == 2 and ins[1][0] == "string", f"ass.hazcloth setup({dur}, {pw}), {oc} hazmat_cloth from 4 lead dust and 8 string (AssemblyMachineRecipes.java:118-119)", want_a)
    sasm = code_of(inp.start[ASM])
    ck("V2.assembly-filtercoal-kept", 'this.register(newGenericRecipe("ass.filtercoal")' in asm and asm.replace(want_a, "") == sasm, "AssemblyMachineRecipes changed only by the ass.hazcloth row")

    tabs = code_of(st.text(CTAB))
    ck("V2.creative-tabs", ordered(tabs, "output.accept(NtmItems.FILTER_COAL.get());", *[f"output.accept(NtmItems.{c.upper()}.get());" for c in CLOTH_IDS])
       and ordered(tabs, "output.accept(NtmItems.MASK_PISS);", *[f"output.accept(NtmItems.{x.upper()});" for x in SUIT_IDS]), "the cloths follow FILTER_COAL, the twelve pieces follow MASK_PISS (main-notes 8)")
    ck("V2.item-models", all(f"this.basicItem(NtmItems.{x.upper()}.get());" in code_of(st.text(IMP)) for x in ITEM_IDS), "NtmItemModelProvider has basicItem for the 15 items")
    itp = code_of(st.text(ITP))
    ck("V2.no9-untagged", "NtmItems.NO9" not in itp, "NtmItemTagProvider does not tag no9 (main-notes 1)")


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


def tag_values(st, path):
    return json.loads(st.text(path)).get("values") if st.has(path) else None


def v3_generated(ck, inp, st):
    for rid, key, n, cat, adv in RECIPES:
        o = parse_orig_recipe(inp, key, n)
        path = f"{RECIPE_DIR}{rid}.json"
        if not st.has(path) or o is None:
            ck(f"V3.recipe-{rid}", False, f"{rid}: recipe JSON and original row {key}:{n}", (st.has(path), o))
            continue
        data = json.loads(st.text(path))
        want_key = {k: EXPR.get(v) for k, v in o[3].items()}
        ok = data.get("type") == "minecraft:crafting_shaped" and data.get("pattern") == o[2] and data.get("key") == want_key and data.get("category") == cat and \
            data.get("result") == {"count": o[1], "id": R + o[0]} and o[0] == rid and None not in want_key.values()
        ck(f"V3.recipe-{rid}", ok, f"{rid}: shaped, pattern {o[2]}, keys mapped from the original row, result {o[1]} x {o[0]} ({O_FILES[key].rsplit('/', 1)[1]}:{n})", (data, want_key))
        ck(f"V3.advancement-{rid}", st.has(f"{ADV_ROOT}{adv}/{rid}.json"), f"{rid}: the recipe advancement exists under {adv}/")
    bad = []
    for i in ITEM_IDS:
        p = f"{GEN}assets/hbmsntm/models/item/{i}.json"
        d = json.loads(st.text(p)) if st.has(p) else None
        if d != {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/{i}"}} or not st.has(RES + f"textures/item/{i}.png"):
            bad.append(i)
    ck("V3.item-models", not bad, "15 item models: item/generated with layer0 hbmsntm:item/<id>, and the texture exists", bad)
    en = json.loads(st.text(EN))
    start_en = json.loads(inp.start[EN])
    wrong = {}
    for neo, okey, _, _ in UP:
        e = inp.o_en.get(okey)
        if not e or en.get(neo) != e[0][0]:
            wrong[neo] = (en.get(neo), e and e[0][0])
    added = sorted(set(en) - set(start_en))
    changed = [k for k in start_en if en.get(k) != start_en[k]]
    ck("V3.en-us", not wrong and added == sorted(NEW_KEYS) and not changed, "en_us.json gained exactly the 15 keys with the original English and changed nothing else",
       (wrong, sorted(set(added) ^ set(NEW_KEYS)), changed[:5]))
    # enchantability tags: slot from the original ModItems slot index for the suits, the 26B masks are heads
    oitems = orig_items(inp)
    by_slot = [[R + m for m in MASKS_26B], [], [], []]
    for iid in SUIT_IDS:
        if iid in oitems:
            by_slot[oitems[iid][2]].append(R + iid)
    every = [x for s in by_slot for x in s]
    for s, name in enumerate(ENCH_SLOT):
        vals = tag_values(st, TAGS + f"enchantable/{name}.json")
        ck(f"V3.tag-enchantable-{name}", vals is not None and sorted(vals) == sorted(by_slot[s]), f"minecraft:enchantable/{name} lists exactly its slot's items ({len(by_slot[s])})", vals)
    for name in ("durability", "equippable"):
        vals = tag_values(st, TAGS + f"enchantable/{name}.json")
        ck(f"V3.tag-enchantable-{name}", vals is not None and sorted(vals) == sorted(every) and len(every) == 18, f"minecraft:enchantable/{name} lists the 18 items", vals)
    leaked = {p: tag_values(st, p) for p in VANILLA_ARMOR_TAGS if st.has(p) and set(tag_values(st, p) or []) & set(every)}
    ck("V3.no-vanilla-armor-tags", not leaked, "none of the 18 items is in minecraft:head_armor / chest_armor / leg_armor / foot_armor / trimmable_armor (main-notes 1: no trims)", leaked)
    no9 = [p for p in ENCH_TAGS + VANILLA_ARMOR_TAGS if st.has(p) and R + "no9" in (tag_values(st, p) or [])]
    ck("V3.no9-untagged", not no9, "no9 is in no enchantable or armor tag", no9)


# ---------------------------------------------------------------- V4 language

def v4_lang(ck, inp, st):
    zt, mt = st.text(ZH), st.text(MAP)
    zh, mp = json.loads(zt), json.loads(mt)["entries"]
    z0, m0 = json.loads(inp.start[ZH]), json.loads(inp.start[MAP])["entries"]
    en = json.loads(st.text(EN))
    ck("V4.zh-insert-only", all(zh.get(k) == v for k, v in z0.items()) and sorted(set(zh) - set(z0)) == sorted(NEW_KEYS),
       "zh_cn.json keeps every start value and gained exactly the 15 keys", sorted(set(zh) - set(z0)))
    ck("V4.map-insert-only", all(mp.get(k) == v for k, v in m0.items()) and sorted(set(mp) - set(m0)) == sorted(NEW_KEYS),
       "the mapping keeps every start entry and gained exactly the 15 entries", sorted(set(mp) - set(m0)))
    bad = {}
    for neo, okey, _, _ in UP:
        e, z, row = inp.o_en.get(okey), inp.o_zh.get(okey), mp.get(neo, {})
        if not (row.get("kind") == "upstream" and row.get("source_key") == okey and e and row.get("source_en") == e[0][0] and z and row.get("source_zh") == z[0][0]
                and row.get("target_zh") == zh.get(neo) and row.get("target_en") == en.get(neo)):
            bad[neo] = (row, z and z[0][0], zh.get(neo))
    ck("V4.upstream", not bad, "15 upstream mapping entries carry the original key, English and Chinese (zh_CN.lang lines) and the current zh_cn.json / en_us.json text", bad)
    same = [neo for neo, okey, _, _ in UP if zh.get(neo) != (inp.o_zh.get(okey) or [("?",)])[0][0]]
    ck("V4.upstream-text", not same, "the 15 Chinese texts are the original zh_CN.lang text", same)
    for path, text, start in ((ZH, zt, inp.start[ZH]), (MAP, mt, inp.start[MAP])):
        crlf = "\r\n" in start
        ok = (text.count("\r\n") == text.count("\n")) if crlf else ("\r\n" not in text)
        diff = [l for l in difflib.unified_diff(lf(start).split("\n"), lf(text).split("\n"), lineterm="", n=0) if l[:1] == "-" and not l.startswith("---")]
        removed = [l for l in diff if l.strip() not in ("-", "-}", "-  }", "-},")]
        ck(f"V4.eol-{path.rsplit('/', 1)[1]}", ok, f"{path.rsplit('/', 1)[1]} keeps its start line endings ({'CRLF' if crlf else 'LF'})")
        ck(f"V4.lines-{path.rsplit('/', 1)[1]}", all(re.fullmatch(r'-\s*("[^"]*": "[^"]*"|\}),?', l) for l in diff) and len(removed) <= len(NEW_KEYS),
           f"{path.rsplit('/', 1)[1]}: no start line was rewritten beyond trailing-comma changes at the insertion points", removed[:4])


# ---------------------------------------------------------------- V5 resources

def v5_resources(ck, inp, st):
    bad = [p for p in RES_PATHS if not st.has(p) or inp.o_res.get(p) is None or sha(st.files[p]) != sha(inp.o_res[p])]
    ck("V5.byte-equal", not bad and len(RES_PATHS) == 24, "the 24 imports are byte-equal (SHA-256) to the original working tree", bad)
    old_names = [RES + o for o in RENAMES if st.has(RES + o)]
    ck("V5.renames", not old_names and all(st.has(RES + n) for n in RENAMES.values()), "the two renamed model textures exist only under their lowercase names", old_names)
    refs = []
    for p in (ITEMS, EXT, HHI):
        for m in re.finditer(r'"(textures/[\w/]+\.png)"', code_of(st.text(p))):
            if "haz" in m[1]:
                refs.append(m[1])
    miss = [r for r in refs if not st.has(RES + r)]
    ck("V5.referenced-textures", not miss and len(refs) >= 13, f"every texture the code references exists ({len(refs)} paths: worn textures, hood models, overlay)", miss)
    if not st.has(OWN):
        ck.pending("V5.ownership-pending", f"{OWN} is absent: pending, not passed")
        return
    own = json.loads(st.text(OWN))
    rows = {a["target_path"]: a for a in own.get("assets", [])}
    wrong = [p for p, (o, n) in zip(RES_PATHS, IMPORTS) if p not in rows or rows[p].get("target_sha256") != (sha(st.files[p]) if st.has(p) else None)
             or rows[p].get("source_path") != O_RES + o or rows[p].get("renamed") != (o in RENAMES)]
    ck("V5.ownership", not wrong and len(rows) == 24 and own.get("source_commit") == ORIGINAL_HEAD,
       "the ownership record lists the 24 imports with their source paths, hashes and the two renames", wrong[:5])


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
    ck("V6.gen-new", sorted(gen_new) == sorted(GEN_NEW) and len(GEN_NEW) == 49, "exactly the 49 new generated files appeared (15 item models, 14 recipes, 14 advancements, 6 enchantable tags)",
       sorted(set(gen_new) ^ set(GEN_NEW))[:6])
    gen_mod = [p for p in changed if p.startswith(GEN) and p in inp.base_files]
    ck("V6.gen-modified", set(gen_mod) <= set(GEN_MODIFIED) and EN in gen_mod, "the generated files that changed are en_us.json and the stamp", gen_mod)
    ck("V6.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES + RES_PATHS) and all(p in inp.base_files for p in EDITED),
       "the new classes and resources did not exist at the start; the edited files did")
    eol = [p for p in EDITED if inp.start.get(p) and st.has(p) and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V6.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    mixed = [p for p in NEW_CLASSES if st.has(p) and st.text(p).count("\r\n") not in (0, st.text(p).count("\n"))]
    ck("V6.new-class-eol", not mixed, "every new class has one line-ending style", mixed)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V6.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V6.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 26C: pending, not passed")
    ck("V6.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V7 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v7_gametest(ck, inp, st):
    others = gametest_total(inp.gt_other.values())
    ck("V7.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V7.present", st.has(GT), "HazmatSuitGameTests.java exists")
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
    ck("V7.no-client", not re.search(r"net\.minecraft\.client", code), "HazmatSuitGameTests references no client class")
    consts = [s for s in ("PART = { 0.2D, 0.4D, 0.3D, 0.1D }", "SUIT = { 0.6D, 1.0D, 2D }", "== 0.07D", "== 0.095D", "0.0225D * PART[i]",
                                                         "durability = { 660, 960, 900, 780 }", "defense = { 2, 5, 4, 1 }", "r.duration == 50 && r.power == 100L",
                                                         "material.enchantmentValue() == 5", "HazmatRegistry.java:34-37", "ArmorUtil.java:57-59,82-94,122-135", "ContaminationUtil.java:265-300",
                                                         "AssemblyMachineRecipes.java:118-119", "ArmorRecipes.java:122-133") if s not in live]
    ck("V7.original-constants", not consts,
       "the GameTest's expected values are the original's (parts, suit values, mask rows, iron / gold, durability, defense, ass.hazcloth, enchantability) and it cites the original lines", consts)
    ck("V7.real-items", "stand-in" not in live.lower(), "the class uses the real items (no stand-in boundary other than the FakePlayer)")
    ck("V7.explicit-player-state", "player.tickCount = 200;" in live and "player.setGameMode(GameType.SURVIVAL);" in live, "the contamination test sets tickCount and the game mode explicitly")
    ck("V7.no-live-table-write", not re.search(r"HazmatRegistry\.registerHazmats\(", code) and not re.search(r"field\.set\(|ENTRIES\.(put|clear)", code), "the GameTest never installs or edits the live HazmatRegistry table")
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
    # re-derive the logged full-set resistance and mod from the original (HazmatRegistry.java:56-58 x the four part factors; ContaminationUtil.java:39-40 10^-r)
    suits = orig_suits(inp)
    parts = orig_parts(inp)
    want = {"yellow": suits.get("hazYellow"), "red": suits.get("hazRed"), "grey": suits.get("hazGray")}
    got = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(re.escape(GT_MARK) + r" radiation_resistance: full (\w+) resistance ([\d.Ee-]+) mod ([\d.Ee-]+)", text)}
    bad = {k: (got.get(k), v) for k, v in want.items() if v is None or k not in got or abs(got[k][0] - v * sum(parts.values())) > 1e-5 or abs(got[k][1] - 10 ** -(v * sum(parts.values()))) > 10 ** -v * 1e-4}
    ck("V7.log-resistance", not bad, "the logged full-set resistance and radiation mod re-derive from the original (0.6 / 1.0 / 2.0; 10^-r)", bad)
    doses = {m[1]: float(m[2]) for m in re.finditer(re.escape(GT_MARK) + r" contamination: (.+?) -> radiation ([\d.Ee-]+) radEnv", text)}
    ck("V7.log-hazmat-blocked", all(doses.get(f"full {t}, HAZMAT") == 0.0 for t in ("yellow", "red", "grey")) and doses.get("no armor, HAZMAT") == 1.0,
       "the logged HAZMAT doses: 0 for each full set, 1.0 without armor (ContaminationUtil.java:278)", {k: v for k, v in doses.items() if "HAZMAT" in k and "without" not in k})
    return dict(all_passed=match and match[0], expected_total=total, resistance=got, doses=doses)


# ---------------------------------------------------------------- V8 jar

def v8_jar(ck, inp, st, path):
    classes_ = [p.split("/java/")[1][:-5] for p in NEW_CLASSES]
    gen = [p for p in GEN_NEW + GEN_MODIFIED if p != STAMP]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V8.classes", not missing, "the JAR has HazmatArmorItem, HazmatHelmetItem and HazmatSuitGameTests", missing)
        bad = [p for p in RES_PATHS if p[len(JARRES):] not in names or jar.read(p[len(JARRES):]) != st.files.get(p)]
        ck("V8.resources", not bad, "the 24 imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V8.generated", not gbad, "the 49 new generated files and en_us.json in the JAR are byte-equal to the tree (the stamp is not packaged)", gbad[:5])
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
    W = 'NuclearTechMod.withDefaultNamespace'
    return [
        # V2 default table and contract
        ("part_factor_legs_0_35", "V2.", t(HR, "double legs = 0.3D;", "double legs = 0.35D;")),
        ("suit_red_0_9", "V2.", t(HR, "double hazRed = 1.0D; // 90%", "double hazRed = 0.9D; // 90%")),
        ("row_dropped", "V2.", t(HR, "        HazmatRegistry.registerHazmat(NtmItems.HAZMAT_LEGS_GREY.get(), hazGray * legs);\n", "")),
        ("gas_mask_0_7", "V2.", t(HR, "registerHazmat(NtmItems.GAS_MASK.get(), 0.07);", "registerHazmat(NtmItems.GAS_MASK.get(), 0.7);")),
        ("row_wrong_part", "V2.", t(HR, "registerHazmat(NtmItems.HAZMAT_BOOTS_RED.get(), hazRed * boots);", "registerHazmat(NtmItems.HAZMAT_BOOTS_RED.get(), hazRed * helmet);")),
        ("iron_row_changed", "V2.", t(HR, "registerHazmat(Items.IRON_BOOTS, iron * boots);", "registerHazmat(Items.IRON_BOOTS, iron * legs);")),
        ("whole_table_replacement_dropped", "V2.", t(HR, "                ENTRIES.clear();\n", "")),
        ("radx_bonus_changed", "V2.", t(HR, "res += 0.2F;", "res += 0.3F;")),
        # V2 checkForHazmat / checkArmor / SAND
        ("mutation_branch_deleted", "V2.", t(AU, "return entity.hasEffect(ModEffect.MUTATION);", "return false;")),
        ("set_dropped_from_check", "V2.", t(AU, " ||\n                checkArmor(entity, NtmItems.HAZMAT_HELMET_GREY.get(), NtmItems.HAZMAT_PLATE_GREY.get(), NtmItems.HAZMAT_LEGS_GREY.get(), NtmItems.HAZMAT_BOOTS_GREY.get())", "")),
        ("check_armor_reversed", "V2.", t(AU, "EquipmentSlot.HEAD,   // 0\n                EquipmentSlot.CHEST,  // 1\n                EquipmentSlot.LEGS,   // 2\n                EquipmentSlot.FEET    // 3",
                                          "EquipmentSlot.FEET,   // 0\n                EquipmentSlot.LEGS,  // 1\n                EquipmentSlot.CHEST,   // 2\n                EquipmentSlot.HEAD    // 3")),
        ("sand_line_removed", "V2.", t(AU, "        ArmorRegistry.registerHazard(NtmItems.HAZMAT_HELMET_RED.get(), HazardClass.SAND);\n", "")),
        ("sand_gets_light", "V2.", t(AU, "registerHazard(NtmItems.HAZMAT_HELMET.get(), HazardClass.SAND);", "registerHazard(NtmItems.HAZMAT_HELMET.get(), HazardClass.SAND, HazardClass.LIGHT);")),
        # V2 contamination
        ("hazmat_after_creative", "V2.", T(CU, lambda x: rep1(rep1(x, "            if(type == ContaminationType.HAZMAT && ArmorUtil.checkForHazmat(player)) return;\n", ""),
                                                               "            if(player.tickCount < 200) return;\n        }\n\n        if(hazard",
                                                               "            if(player.tickCount < 200) return;\n            if(type == ContaminationType.HAZMAT && ArmorUtil.checkForHazmat(player)) return;\n        }\n\n        if(hazard"))),
        ("faraday_branch_added", "V2.", t(CU, "            if(type == ContaminationType.HAZMAT && ArmorUtil.checkForHazmat(player)) return;\n",
                                          "            if(type == ContaminationType.HAZMAT && ArmorUtil.checkForHazmat(player)) return;\n            if(type == ContaminationType.FARADAY && ArmorUtil.checkForHazmat(player)) return;\n")),
        ("enum_changed", "V2.", t(CU, "        HAZMAT_HEAVY,		//preventable by heavy hazmat\n", "        HAZMAT_HEAVY,		//preventable by heavy hazmat\n        HAZMAT2,\n")),
        ("hazmat_caller_added", "V2.", T(J + "util/ArmorUtil.java", lambda x: rep1(x, "    public static boolean isWearingEmptyMask(Player player) {\n",
                                                                                   "    public static void x(LivingEntity e) { ContaminationUtil.contaminate(e, ContaminationUtil.HazardType.RADIATION, ContaminationUtil.ContaminationType.HAZMAT, 1F); }\n\n    public static boolean isWearingEmptyMask(Player player) {\n"))),
        # V2 hood class
        ("hood_blacklist_not_empty", "V2.", t(HHI, "return new ArrayList<>(); // full hood has no restrictions", "return new ArrayList<>(List.of(HazardClass.GAS_BLISTERING)); // full hood has no restrictions")),
        ("hood_filter_not_applicable", "V2.", t(HHI, "    public boolean isFilterApplicable(ItemStack stack, LivingEntity entity, ItemStack filter) {\n        return true;",
                                                 "    public boolean isFilterApplicable(ItemStack stack, LivingEntity entity, ItemStack filter) {\n        return false;")),
        ("hood_duplicated_eject", "V2.", t(HHI, "        if(ArmorUtil.ejectGasMaskFilter(this, stack, level, player)) {\n            return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());\n        }",
                                           "        if(player.isShiftKeyDown() && !getFilter(stack, player).isEmpty()) {\n            ItemStack filter = getFilter(stack, player);\n            ArmorUtil.removeFilter(stack);\n"
                                           "            if(!player.getInventory().add(filter)) player.drop(filter, true, false);\n            return InteractionResultHolder.sidedSuccess(stack, level.isClientSide());\n        }")),
        ("eject_drop_without_scatter", "V2.", t(AU, "player.drop(filter, true, false);", "player.drop(filter, false, false);")),
        ("hood_client_import", "V2.", t(HHI, "import api.hbm.item.IGasMask;", "import api.hbm.item.IGasMask;\nimport net.minecraft.client.Minecraft;")),
        ("overlay_to_red_helmet", "V2.", t(ITEMS, f'{W}("textures/models/model_haz_red.png"), true, null)', f'{W}("textures/models/model_haz_red.png"), true, {W}("textures/misc/overlay_hazmat.png"))')),
        ("m65_to_yellow_helmet", "V2.", t(ITEMS, f'{W}("textures/armor/hazmat_1.png"), false, {W}', f'{W}("textures/armor/hazmat_1.png"), true, {W}')),
        ("client_hood_model_always_m65", "V2.", t(EXT, "return hood.isM65Model() ? m65(living) : original;", "return m65(living);")),
        ("client_registration_drops_hood", "V2.", t(CLIENT, "NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_HELMET_RED.get(), NtmItems.HAZMAT_HELMET_GREY.get());",
                                                    "NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_HELMET_RED.get());")),
        # V2 materials / items
        ("enchantment_5_to_9", "V2.", t(MAT, "            defense(1, 4, 5, 2),\n            5,\n            SoundEvents.ARMOR_EQUIP_LEATHER,\n            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH_RED.get()),",
                                        "            defense(1, 4, 5, 2),\n            9,\n            SoundEvents.ARMOR_EQUIP_LEATHER,\n            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH_RED.get()),")),
        ("durability_60_to_33", "V2.", t(ITEMS, "ArmorItem.Type.LEGGINGS, new Item.Properties().durability(ArmorItem.Type.LEGGINGS.getDurability(60)), " + W + '("textures/armor/hazmat_2_grey.png")',
                                         "ArmorItem.Type.LEGGINGS, new Item.Properties().durability(ArmorItem.Type.LEGGINGS.getDurability(33)), " + W + '("textures/armor/hazmat_2_grey.png")')),
        ("defense_number", "V2.", T(MAT, lambda x: x.replace("defense(1, 4, 5, 2),\n            5,\n            SoundEvents.ARMOR_EQUIP_LEATHER,\n            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH.get())",
                                                             "defense(1, 4, 5, 3),\n            5,\n            SoundEvents.ARMOR_EQUIP_LEATHER,\n            () -> Ingredient.of(NtmItems.HAZMAT_CLOTH.get())", 1))),
        ("repair_wrong_cloth", "V2.", t(MAT, "() -> Ingredient.of(NtmItems.HAZMAT_CLOTH_GREY.get()),", "() -> Ingredient.of(NtmItems.HAZMAT_CLOTH_RED.get()),")),
        ("worn_texture_swapped", "V2.", t(ITEMS, f'ArmorItem.Type.LEGGINGS.getDurability(60)), {W}("textures/armor/hazmat_2.png")', f'ArmorItem.Type.LEGGINGS.getDurability(60)), {W}("textures/armor/hazmat_1.png")')),
        ("ass_string_8_to_2", "V2.", t(ASM, "new ComparableStack(net.minecraft.world.item.Items.STRING, 8)", "new ComparableStack(net.minecraft.world.item.Items.STRING, 2)")),
        ("ass_cloth_output_4_to_1", "V2.", t(ASM, "new ItemStack(NtmItems.HAZMAT_CLOTH.get(), 4)", "new ItemStack(NtmItems.HAZMAT_CLOTH.get(), 1)")),
        ("igasmask_touched", "V2.", T(IGM, lambda x: x + "\n")),
        ("gasmask_blacklist_changed", "V2.", t(GMI, "List.of(HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA)", "List.of(HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING)")),
        # V3 generated
        ("recipe_pattern_row", "V3.", gen_edit(RECIPE_DIR + "hazmat_plate_red.json", lambda d: d.update(pattern=["E E", "EEE", "E E"]))),
        ("recipe_key_lead_to_iron", "V3.", gen_edit(RECIPE_DIR + "hazmat_cloth_grey.json", lambda d: d["key"].update(L={"item": R + "plate_iron"}))),
        ("recipe_output_2", "V3.", gen_edit(RECIPE_DIR + "hazmat_cloth_red.json", lambda d: d["result"].update(count=2))),
        ("recipe_deleted", "V3.|V6.", D(RECIPE_DIR + "hazmat_helmet_grey.json")),
        ("item_model_texture", "V3.", gen_edit(GEN + "assets/hbmsntm/models/item/hazmat_legs_red.json", lambda d: d["textures"].update(layer0="hbmsntm:item/hazmat_legs"))),
        ("enchantable_entry_removed", "V3.", gen_edit(TAGS + "enchantable/foot_armor.json", lambda d: d["values"].remove(R + "hazmat_boots_grey"))),
        ("enchantable_wrong_slot", "V3.", gen_edit(TAGS + "enchantable/chest_armor.json", lambda d: d["values"].append(R + "hazmat_legs"))),
        ("item_added_to_head_armor", "V3.", lambda st: st.set_text(TAGS + "head_armor.json", json.dumps({"values": [R + "hazmat_helmet"]}, indent=2))),
        ("language_value", "V3.", gen_edit(EN, lambda d: d.update({"item.hbmsntm.hazmat_cloth_grey": "Grey Hazmat Cloth"}))),
        # V4 language
        ("zh_upstream_text", "V4.", lang_edit("item.hbmsntm.hazmat_legs_red", "红色防辐射护腿")),
        ("zh_key_dropped", "V4.", T(ZH, lambda x: "\n".join(l for l in x.split("\n") if '"item.hbmsntm.hazmat_boots_grey"' not in l))),
        ("map_source_zh", "V4.", T(MAP, lambda x: rep1(x, '"source_zh": "铅防辐射布"', '"source_zh": "铅制防辐射布"'))),
        ("zh_crlf_lost", "V4.", lambda st: st.set_bytes(ZH, st.files[ZH].replace(b"\r\n", b"\n"))),
        # V5 resources
        ("resource_byte_flip", "V5.", lambda st: st.set_bytes(RES + "textures/armor/hazmat_2_red.png", flip_byte(st.files[RES + "textures/armor/hazmat_2_red.png"]))),
        ("rename_target_original_case", "V5.|V6.", MV(RES + "textures/models/model_haz_grey.png", RES + "textures/models/ModelHazGrey.png")),
        ("overlay_missing", "V5.|V6.", D(RES + "textures/misc/overlay_hazmat.png")),
        # V6 scope
        ("extra_production_file", "V6.", lambda st: st.set_text(J + "items/armor/ArmorFSB.java", "class ArmorFSB {}\n")),
        ("start_file_deleted", "V6.", D(J + "items/armor/ArmorNo9.java")),
        # V1 original (in memory)
        ("orig_row_line_moved", "V1.", OE("hr", lambda x: rep1(x, "\tpublic static void initDefault() {\n", "\tpublic static void initDefault() {\n\n"))),
        ("orig_suit_value", "V1.|V2.", OE("hr", lambda x: rep1(x, "double hazGray = 2D; // 99%", "double hazGray = 2.5D; // 99%"))),
        ("orig_hazmat_after_creative", "V1.", OE("cu", lambda x: rep1(x, "\t\t\tcase HAZMAT:\t\t\tif(ArmorUtil.checkForHazmat(player))\treturn false; break;\n", "\t\t\tcase HAZMAT:\t\t\tbreak;\n"))),
        ("orig_material_enchant", "V1.|V2.", OE("mr", lambda x: rep1(x, 'addArmorMaterial("HBM_HAZMAT3", 60, new int[] { 2, 5, 4, 1 }, 5);', 'addArmorMaterial("HBM_HAZMAT3", 60, new int[] { 2, 5, 4, 1 }, 9);'))),
        ("orig_recipe_row", "V1.|V3.", OE("ar", lambda x: rep1(x, 'new ItemStack(ModItems.hazmat_legs_red, 1), new Object[] { "EEE", "E E", "E E"', 'new ItemStack(ModItems.hazmat_legs_red, 1), new Object[] { "EEE", "EEE", "E E"'))),
        # V7 GameTest source and log
        ("gt_marker_changed", "V7.", t(GT, 'TAG = "[hbm-hazmat]"', 'TAG = "[hbm-hazmat-suit]"'), GT),
        ("gt_batch_shared", "V7.", t(GT, 'batch = "hazmat_enchantability"', 'batch = "hazmat_config_table"'), GT),
        ("gt_test_removed", "V7.", t(GT, "public static void helmet_filters(", "public static void helmet_filters_x("), GT),
        ("gt_constant_from_neo", "V7.", t(GT, "SUIT = { 0.6D, 1.0D, 2D }", "SUIT = { 0.6D, 1.0D, NtmArmorMaterials.HAZMAT_GREY.get().enchantmentValue() }"), GT),
        ("gt_installs_table", "V7.", t(GT, "Map<Item, Double> live = liveTable();", "HazmatRegistry.registerHazmats();\n                Map<Item, Double> live = liveTable();"), GT),
        ("gt_deleted", "V7.|V6.", D(GT), GT),
        ("log_total_changed", "V7.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 266 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", LT(lambda x: x.replace("[hbm-hazmat] contamination passed", "")), "LOG"),
        ("log_failed_line", "V7.", LT(lambda x: x + "\n[12:00:00] Test hazmatsuitgametests.enchantability failed! required tests failed: 1\n"), "LOG"),
        ("log_resistance_changed", "V7.", LT(lambda x: re.sub(r"(\[hbm-hazmat\] radiation_resistance: full red resistance )[\d.Ee-]+", r"\g<1>0.9", x)), "LOG"),
        ("log_hazmat_dose", "V7.", LT(lambda x: re.sub(r"(\[hbm-hazmat\] contamination: full grey, HAZMAT -> radiation )[\d.Ee-]+", r"\g<1>0.01", x)), "LOG"),
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
