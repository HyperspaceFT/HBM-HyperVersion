"""Verify the Goal24A batch statically: the RBMK dial config section `rbmk` and the RBMKDials facade, the column base (RBMKBaseBlock, RBMKBaseBlockEntity),
the four passive columns, the lids, the deco blocks, the three debris blocks and the RBMKDebris entity, debris_fuel, ass.rbmk and the crafting rows, the screwdriver
as ToolingItem, the 24A-1 and 24A-2 close-out adaptations, language, resources, the upstream classification and the GameTest source.

Read-only for both worktrees. Writes only build/migration/goal24a/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal24a/baseline-files and baseline.json; start bytes of files that were not
copied come from `git show 1114adf5:<path>`):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (RBMKDials, TileEntityRBMKBase and its four subclasses, RBMKBase, the debris blocks, EntityRBMKDebris, ItemRBMKLid, ItemTooling, the recipe rows,
      the hazard row, the lang lines, the 24A-2 sources) parsed from the read-only worktree and asserted against the task book literals (GOAL24A.md).
- V2  CommonConfig section rbmk, NtmConfig exposure and the RBMKDials facade.
- V3  RBMKBaseBlockEntity and the four passive block entities.
- V4  RBMKBaseBlock, RBMKPassiveBlock, the debris blocks, RBMKLidItem, DyatlovItem and the deco/column registrations.
- V5  The RBMKDebris entity and the ZirnoxDebris PERMA_SCRAP change.
- V6  Registrations exactly once (blocks, block entities, entity, items, creative tabs, client registrations, OBJ entries, NtmGeometry) and client isolation.
- V7  Recipes: the seven crafting JSONs, no moderator/glass lid recipe, ass.rbmk, the other ass.* rows unchanged, AnvilRecipes unchanged.
- V8  Hazards: debris_fuel and the five removed vanilla rows.
- V9  24A-2 and 24A-1 adaptations (FT_Pheromone, FluidTrait, HazardTypeRadiation, ContaminationUtil, hold-shift hint, chloride names, turbofan redstone probe).
- V10 Screwdriver as ToolingItem.
- V11 Language (provider, en_us.json, zh_cn.json, mapping).
- V12 The 40 imported resources against the original, the git blob and migration/goal24a-resource-ownership.json.
- V13 migration/goal24a-upstream-classification.json against `git diff --name-status -M 6a11998d aee05a40f`.
- V14 Scope: the src/ and migration/ paths changed since the start (tools/ is outside the hash scope; its git status is listed for information).
- V15 GameTests (source). V16 (--gametest-log) the GameTest log; V17 (--jar) the packaged JAR; "not run" when the flag is absent.
- V18 In-memory mutations of the NEO inputs (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal24a_rbmk_core.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import collections
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal24a"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
OLD_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"
START_COMMIT = "1114adf5de758697842e1f2195c0e3928b04abbc"

J = "src/main/java/com/hbm/"
BE_DIR = J + "blockentity/machine/rbmk/"
BLK_DIR = J + "blocks/machine/rbmk/"
BASE_BE = BE_DIR + "RBMKBaseBlockEntity.java"
DIALS = BE_DIR + "RBMKDials.java"
RBMK_TYPE = BE_DIR + "RBMKType.java"
COLUMN_TYPE = BE_DIR + "RBMKColumnType.java"
BE_BLANK = BE_DIR + "RBMKBlankBlockEntity.java"
BE_ABSORBER = BE_DIR + "RBMKAbsorberBlockEntity.java"
BE_REFLECTOR = BE_DIR + "RBMKReflectorBlockEntity.java"
BE_MODERATOR = BE_DIR + "RBMKModeratorBlockEntity.java"
BASE_BLK = BLK_DIR + "RBMKBaseBlock.java"
PASSIVE_BLK = BLK_DIR + "RBMKPassiveBlock.java"
DEB_BLK = BLK_DIR + "RBMKDebrisBlock.java"
DEB_BURN = BLK_DIR + "RBMKDebrisBurningBlock.java"
DEB_RAD = BLK_DIR + "RBMKDebrisRadiatingBlock.java"
DEB_ENT = J + "entity/projectile/RBMKDebris.java"
LID_ITEM = J + "items/machine/RBMKLidItem.java"
R_LID = J + "render/blockentity/RenderRBMKLid.java"
R_DEB = J + "render/entity/projectile/RenderRBMKDebris.java"
NEW_CLASSES = [BASE_BE, DIALS, RBMK_TYPE, COLUMN_TYPE, BE_BLANK, BE_ABSORBER, BE_REFLECTOR, BE_MODERATOR, BASE_BLK, PASSIVE_BLK, DEB_BLK, DEB_BURN, DEB_RAD, DEB_ENT, LID_ITEM, R_LID, R_DEB]

CC = J + "config/CommonConfig.java"
NCFG = J + "config/NtmConfig.java"
NB = J + "blocks/NtmBlocks.java"
NBET = J + "blockentity/NtmBlockEntityTypes.java"
NET = J + "entity/NtmEntityTypes.java"
ZD = J + "entity/projectile/ZirnoxDebris.java"
NI = J + "items/NtmItems.java"
CT = J + "inventory/NtmCreativeTabs.java"
CP = J + "main/ClientProxy.java"
NMC = J + "main/NuclearTechModClient.java"
RM = J + "main/ResourceManager.java"
GEOM = J + "render/model/loader/NtmGeometry.java"
HR = J + "hazard/HazardRegistry.java"
HTR = J + "hazard/type/HazardTypeRadiation.java"
CU = J + "util/ContaminationUtil.java"
AMR = J + "inventory/recipes/AssemblyMachineRecipes.java"
ANVIL = J + "inventory/recipes/anvil/AnvilRecipes.java"
RP = J + "datagen/NtmRecipeProvider.java"
LOOT = J + "datagen/NtmBlockLootTableProvider.java"
TAG = J + "datagen/NtmBlockTagProvider.java"
MP = J + "datagen/NtmItemModelProvider.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
TI = J + "items/tools/ToolingItem.java"
DY = J + "items/tools/DyatlovItem.java"
LB = J + "blockentity/machine/LockableBaseBlockEntity.java"
TURBO = J + "blockentity/machine/MachineTurbofanBlockEntity.java"
FT_PH = J + "inventory/fluid/trait/FT_Pheromone.java"
FT_TRAIT = J + "inventory/fluid/trait/FluidTrait.java"
FLUIDTYPE = J + "inventory/fluid/FluidType.java"
TOOLTIP = J + "blocks/ITooltipProvider.java"
HGT = J + "gametest/HazardGameTests.java"
RCGT = J + "gametest/RBMKCoreGameTests.java"
GAMETEST_DIR = J + "gametest/"
DUMMYABLE = J + "blocks/DummyableBlock.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal24a-resource-ownership.json"
CLASSIFY = "migration/goal24a-upstream-classification.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
RECIPES = GEN + "data/hbmsntm/recipe/"
ADV_MISC = GEN + "data/hbmsntm/advancement/recipes/misc/"
ADV_BUILD = GEN + "data/hbmsntm/advancement/recipes/building_blocks/"
G_TAG = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
G_STATES = GEN + "assets/hbmsntm/blockstates/"
G_BMODELS = GEN + "assets/hbmsntm/models/block/"
G_IMODELS = GEN + "assets/hbmsntm/models/item/"
G_LOOTS = GEN + "data/hbmsntm/loot_table/blocks/"
RES = "src/main/resources/assets/hbmsntm/"

# the nine blocks, the four block entity types, the entity type, the three items
COLUMNS = ["rbmk_blank", "rbmk_reflector", "rbmk_absorber", "rbmk_moderator"]
DEBRIS = ["pribris", "pribris_burning", "pribris_radiating"]
DECO = ["deco_rbmk", "deco_rbmk_smooth"]
BLOCKS9 = COLUMNS + DEBRIS + DECO
ITEMS3 = ["debris_fuel", "rbmk_lid", "rbmk_lid_glass"]
RECIPE_IDS = ["rbmk_lid", "rbmk_absorber", "rbmk_reflector", "deco_rbmk", "deco_rbmk_smooth", "rbmk_blank_from_deco_rbmk", "rbmk_blank_from_deco_rbmk_smooth"]
ITEM_MODELS12 = ["debris_fuel", "rbmk_lid", "rbmk_lid_glass"] + BLOCKS9
G_BLOCKSTATES = [G_STATES + n + ".json" for n in BLOCKS9]
G_BLOCKMODELS = [G_BMODELS + n + ".json" for n in BLOCKS9]
G_ITEMMODELS = [G_IMODELS + n + ".json" for n in ITEM_MODELS12]
G_LOOTTABLES = [G_LOOTS + n + ".json" for n in BLOCKS9]
G_RECIPES = [RECIPES + n + ".json" for n in RECIPE_IDS]
G_ADVANCEMENTS = [(ADV_BUILD if n.startswith("deco_rbmk") else ADV_MISC) + n + ".json" for n in RECIPE_IDS]
GENERATED = [STAMP, EN, G_TAG] + G_BLOCKSTATES + G_BLOCKMODELS + G_ITEMMODELS + G_LOOTTABLES + G_RECIPES + G_ADVANCEMENTS

# the edited production files of the review diff (build/migration/goal24a/review-diff.patch) that are not new classes
EDITED = [NBET, TURBO, LB, TOOLTIP, NB, CC, LOOT, BSP, TAG, MP, LP, RP, NET, ZD, HR, HTR, CT, FLUIDTYPE, FT_PH, FT_TRAIT, AMR, NI, DY, TI, CP, RM, GEOM, CU]
LANG_FILES = [ZH, MAP]

# original files
O = "src/main/java/com/hbm/"
O_DIALS = O + "tileentity/machine/rbmk/RBMKDials.java"
O_BASE = O + "tileentity/machine/rbmk/TileEntityRBMKBase.java"
O_BLANK = O + "tileentity/machine/rbmk/TileEntityRBMKBlank.java"
O_ABSORBER = O + "tileentity/machine/rbmk/TileEntityRBMKAbsorber.java"
O_REFLECTOR = O + "tileentity/machine/rbmk/TileEntityRBMKReflector.java"
O_MODERATOR = O + "tileentity/machine/rbmk/TileEntityRBMKModerator.java"
O_CONSOLE = O + "tileentity/machine/rbmk/TileEntityRBMKConsole.java"
O_NEUTRON = O + "handler/neutron/RBMKNeutronHandler.java"
O_RBMKBASE = O + "blocks/machine/rbmk/RBMKBase.java"
O_DEB = O + "blocks/machine/rbmk/RBMKDebris.java"
O_BURN = O + "blocks/machine/rbmk/RBMKDebrisBurning.java"
O_RAD = O + "blocks/machine/rbmk/RBMKDebrisRadiating.java"
O_ENT = O + "entity/projectile/EntityRBMKDebris.java"
O_LID = O + "items/machine/ItemRBMKLid.java"
O_TOOLING = O + "items/tool/ItemTooling.java"
O_DEGR = O + "items/tool/ItemCraftingDegradation.java"
O_DYATLOV = O + "items/tool/ItemDyatlov.java"
O_MODITEMS = O + "items/ModItems.java"
O_MODBLOCKS = O + "blocks/ModBlocks.java"
O_CRAFT = O + "main/CraftingManager.java"
O_ASM = O + "inventory/recipes/AssemblyMachineRecipes.java"
O_HAZ = O + "hazard/HazardRegistry.java"
O_ANVIL = O + "inventory/recipes/anvil/AnvilRecipes.java"
O_CONTAM = O + "util/ContaminationUtil.java"
O_PHERO = O + "inventory/fluid/trait/FT_Pheromone.java"
O_TRAIT = O + "inventory/fluid/trait/FluidTrait.java"
O_TURBO = O + "tileentity/machine/TileEntityMachineTurbofan.java"
O_HTR = O + "hazard/type/HazardTypeRadiation.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES_DIR = "src/main/resources/assets/hbm/"

# (NEO key, original key, en_US.lang line, zh_CN.lang line, English, Chinese): the 13 upstream RBMK keys (GOAL24A 24A-5, 24A-6, 24A-8)
LANG13 = [
    ("block.hbmsntm.rbmk_blank", "tile.rbmk_blank.name", 6213, 5340, "RBMK Structural Column", "RBMK反应堆结构柱"),
    ("block.hbmsntm.rbmk_moderator", "tile.rbmk_moderator.name", 6240, 5351, "RBMK Graphite Moderator", "RBMK反应堆石墨慢化剂"),
    ("block.hbmsntm.rbmk_absorber", "tile.rbmk_absorber.name", 6211, 5339, "RBMK Boron Neutron Absorber", "RBMK反应堆硼中子吸收器"),
    ("block.hbmsntm.rbmk_reflector", "tile.rbmk_reflector.name", 6244, 5353, "RBMK Tungsten Carbide Neutron Reflector", "RBMK反应堆碳化钨中子反射器"),
    ("block.hbmsntm.deco_rbmk", "tile.deco_rbmk.name", 5478, 4716, "RBMK Deco Block", "RBMK装饰块"),
    ("block.hbmsntm.deco_rbmk_smooth", "tile.deco_rbmk_smooth.name", 5479, 4717, "Smooth RBMK Deco Block", "平滑RBMK装饰块"),
    ("block.hbmsntm.pribris", "tile.pribris.name", 6151, 5284, "RBMK Debris", "RBMK石墨式反应堆残骸"),
    ("block.hbmsntm.pribris_burning", "tile.pribris_burning.name", 6152, 5285, "Flaming RBMK Debris", "燃烧的RBMK反应堆残骸"),
    ("block.hbmsntm.pribris_radiating", "tile.pribris_radiating.name", 6154, 5287, "Smoldering RBMK Debris", "阴燃的RBMK反应堆残骸"),
    ("item.hbmsntm.rbmk_lid", "item.rbmk_lid.name", 4197, 3630, "RBMK Cover Panel", "RBMK反应堆覆盖层"),
    ("item.hbmsntm.rbmk_lid_glass", "item.rbmk_lid_glass.name", 4198, 3631, "RBMK Glass Cover Panel", "RBMK反应堆玻璃覆盖层"),
    ("item.hbmsntm.debris_fuel", "item.debris_fuel.name", 2676, 2310, "RBMK Fuel Chunk", "RBMK石墨式反应堆燃料块"),
    ("tile.rbmk.dodd.heat", "tile.rbmk.dodd.heat", 6256, 5937, "Column Heat", "温度"),
]
LANG_PHERO = [
    ("hbmfluid.trait.glyphidPheromones", "hbmfluid.trait.glyphidPheromones", 6556, 6469, "Glyphid Pheromones", "异虫信息素"),
    ("hbmfluid.trait.modifiedPheromones", "hbmfluid.trait.modifiedPheromones", 6561, 6474, "Modified Pheromones", "增强信息素"),
]
LANG_ENTITY = ("entity.hbmsntm.rbmk_debris", "RBMK Debris", "RBMK碎片")
LANG_HOLD = ("desc.misc.holdShiftMoreInfo", "Hold <%s> to display more info", "按住 <%s> 显示更多信息")
LANG_CHLORIDE = [("hbmfluid.calcium_chloride", 1462, 1179, "Calcium chloride Solution"), ("hbmfluid.potassium_chloride", 1561, 1274, "Potassium chloride Solution")]
KEYS17 = [k[0] for k in LANG13] + [LANG_ENTITY[0]] + [k[0] for k in LANG_PHERO] + [LANG_HOLD[0]]
KEYS14 = [k[0] for k in LANG13] + [LANG_ENTITY[0]]

# the 25 original dial keys and defaults in file order (RBMKDials.java:17-51)
ORIG_DIALS = [("dialSaveDials", "true"), ("dialPassiveCooling", "2.5"), ("dialPassiveCoolingInner", "0.1"), ("dialColumnHeatFlow", "0.2"), ("dialDiffusionMod", "1.0"),
              ("dialHeatProvision", "0.2"), ("dialColumnHeight", "4"), ("dialEnablePermaScrap", "true"), ("dialBoilerHeatConsumption", "0.1"), ("dialControlSpeed", "1.0"),
              ("dialReactivityMod", "1.0"), ("dialOutgasserSpeedMod", "1.0"), ("dialControlSurgeMod", "1.0"), ("dialFluxRange", "5"), ("dialReasimRange", "10"),
              ("dialReasimBoilers", "false"), ("dialReasimBoilerSpeed", "0.05"), ("dialDisableMeltdowns", "false"), ("dialEnableMeltdownOverpressure", "false"),
              ("dialModeratorEfficiency", "1.0"), ("dialAbsorberEfficiency", "1.0"), ("dialReflectorEfficiency", "1.0"), ("dialDisableDepletion", "false"),
              ("dialDisableXenon", "false"), ("dialAbsorberHeatConversion", "0.05")]
NOT_REGISTERED = ["dialSaveDials", "dialReasimBoilers", "dialReasimRange", "dialReasimBoilerSpeed"]
# the clamp of each dial in the original refresh() (:91-114): ("min", 0) = getDoubleMinimum, ("range", lo, hi) = getClampedDouble, ("irange", lo, hi, shift) = getClampedInt, ("bool",)
ORIG_CLAMP = {"dialPassiveCooling": ("min", 0.0), "dialPassiveCoolingInner": ("min", 0.0), "dialColumnHeatFlow": ("range", 0.0, 1.0), "dialDiffusionMod": ("min", 0.0),
              "dialHeatProvision": ("range", 0.0, 1.0), "dialColumnHeight": ("irange", 2, 16, -1), "dialEnablePermaScrap": ("bool",), "dialBoilerHeatConsumption": ("min", 0.0),
              "dialControlSpeed": ("min", 0.0), "dialReactivityMod": ("min", 0.0), "dialOutgasserSpeedMod": ("min", 0.0), "dialControlSurgeMod": ("min", 0.0),
              "dialFluxRange": ("irange", 1, 100, 0), "dialDisableMeltdowns": ("bool",), "dialEnableMeltdownOverpressure": ("bool",), "dialModeratorEfficiency": ("range", 0.0, 1.0),
              "dialAbsorberEfficiency": ("range", 0.0, 1.0), "dialAbsorberHeatConversion": ("range", 0.0, 1.0), "dialReflectorEfficiency": ("range", 0.0, 1.0),
              "dialDisableDepletion": ("bool",), "dialDisableXenon": ("bool",)}
NEO_DIALS = [(k, d) for k, d in ORIG_DIALS if k not in NOT_REGISTERED]
# original getter -> dial key (RBMKDials.java:157-375); the three ReaSim getters are not ported
ORIG_GETTERS = {"getPassiveCooling": "dialPassiveCooling", "getPassiveCoolingInner": "dialPassiveCoolingInner", "getColumnHeatFlow": "dialColumnHeatFlow",
                "getFuelDiffusionMod": "dialDiffusionMod", "getFuelHeatProvision": "dialHeatProvision", "getColumnHeight": "dialColumnHeight", "getPermaScrap": "dialEnablePermaScrap",
                "getBoilerHeatConsumption": "dialBoilerHeatConsumption", "getControlSpeed": "dialControlSpeed", "getReactivityMod": "dialReactivityMod",
                "getOutgasserMod": "dialOutgasserSpeedMod", "getSurgeMod": "dialControlSurgeMod", "getFluxRange": "dialFluxRange", "getMeltdownsDisabled": "dialDisableMeltdowns",
                "getOverpressure": "dialEnableMeltdownOverpressure", "getModeratorEfficiency": "dialModeratorEfficiency", "getAbsorberEfficiency": "dialAbsorberEfficiency",
                "getAbsorberHeatConversion": "dialAbsorberHeatConversion", "getReflectorEfficiency": "dialReflectorEfficiency", "getDepletion": "dialDisableDepletion",
                "getXenon": "dialDisableXenon"}
ORIG_REASIM_GETTERS = ["getReaSimRange", "getReasimBoilers", "getReaSimBoilerSpeed"]

HASH_SKIP = ("__pycache__",)
GT_MARK = "[hbm-rbmk-core]"
START_GAMETESTS = 122
# the RBMKCoreGameTests methods as read from the file when this verifier was written (the handoff gives no count)
GT_TESTS = ["rbmk_column_placement", "rbmk_passive_cooling", "rbmk_heat_flow", "rbmk_dials_defaults", "rbmk_lids_and_screwdriver", "rbmk_lid_collision", "rbmk_meltdown_blank_2x2",
            "rbmk_meltdown_lidded_column", "rbmk_pribris_burning_tick", "rbmk_pribris_radiating", "rbmk_debris_entity", "rbmk_recipes", "rbmk_debris_fuel_hazard",
            "rbmk_screwdriver_tooling", "rbmk_closeout_fluid_traits", "rbmk_closeout_pheromone_keys", "rbmk_closeout_hold_shift_hint", "rbmk_closeout_meteor_config"]


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
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:900]))
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


# ---------------------------------------------------------------- text helpers

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
    """Index of the brace closing code[open_index] == '{'; code must have its comments blanked."""
    assert code[open_index] == "{"
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
    raise ValueError("unbalanced braces")


def match_paren(code, open_index):
    assert code[open_index] == "("
    depth, j, n = 0, open_index, len(code)
    while j < n:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < n and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced parentheses")


def brace_depth(code, start, end):
    depth, j = 0, start
    while j < end:
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < end and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        depth += (c == "{") - (c == "}")
        j += 1
    return depth


def split_top(text):
    """Split on commas outside parentheses, brackets, braces and strings."""
    parts, depth, cur, j, n = [], 0, [], 0, len(text)
    while j < n:
        c = text[j]
        if c == '"':
            k = j + 1
            while k < n and text[k] != '"':
                k += 2 if text[k] == "\\" else 1
            cur.append(text[j:k + 1])
            j = k + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        j += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def method_span(text, signature):
    """(open_brace, close_brace, blanked code) of the unique method whose header contains signature."""
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def norm(code):
    return re.sub(r"\s+", " ", code).strip()


def squash(code):
    return re.sub(r"\s+", "", code)


def method_code(text, signature):
    o, c, code = method_span(text, signature)
    return norm(code[o + 1:c])


def mcode(text, signature):
    """The method body with comments removed and every whitespace character removed."""
    return squash(method_code(text, signature))


def whole(text):
    """The whole file with comments removed and every whitespace character removed."""
    return squash(blank_comments(lf(text)))


def missing(code, *needles):
    """The needles that do not occur in code (an empty list means all occur)."""
    return [n for n in needles if n not in code]


def eol_of(text):
    return "\r" if "\r\n" in text and text.count("\r\n") == text.count("\n") else ""


_OPS = {}


def non_equal_ops(start, live):
    key = (start, live)
    cached = _OPS.get(key)
    if cached is None:
        s, l = lf(start).split("\n"), lf(live).split("\n")
        cached = [(tag, i1, i2, s[i1:i2], l[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s, l, autojunk=False).get_opcodes() if tag != "equal"]
        _OPS[key] = cached
    return cached


def diff_summary(start, live):
    """(deleted start lines, inserted live lines), both stripped and without blank lines."""
    ops = non_equal_ops(start, live)
    deleted = [x.strip() for _, _, _, s, _ in ops for x in s if x.strip()]
    inserted = [x.strip() for _, _, _, _, l in ops for x in l if x.strip()]
    return deleted, inserted


def insert_only(start, live):
    ops = non_equal_ops(start, live)
    if any(tag in ("delete", "replace") for tag, _, _, _, _ in ops):
        return False, [(tag, s[:3], l[:3]) for tag, _, _, s, l in ops if tag != "insert"]
    return True, [x for _, _, _, _, l in ops for x in l]


def json_pairs(text):
    dups = []

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(k for k in set(keys) if keys.count(k) > 1)
        return dict(pairs)
    return json.loads(text, object_pairs_hook=hook), dups


def parse_lang_lines(text):
    return lf(text).lstrip("﻿").split("\n")


def lang_value(lines, number, key):
    """The value of the lang line `number` (1-based) when it carries `key`, else None."""
    row = lines[number - 1]
    return row.split("=", 1)[1].rstrip("\r") if row.startswith(key + "=") else None


def format_ok(text, data):
    plain = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return text == plain or text == crlf(plain)


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def rep_first(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


def drop_line(text, needle):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    del lines[hits[0]]
    return "\n".join(lines)


def swap_lines(text, a, b):
    lines = text.split("\n")
    ia = [i for i, l in enumerate(lines) if a in l]
    ib = [i for i, l in enumerate(lines) if b in l]
    assert len(ia) == 1 and len(ib) == 1, (a, b, ia, ib)
    lines[ia[0]], lines[ib[0]] = lines[ib[0]], lines[ia[0]]
    return "\n".join(lines)


def line_edit(text, needle, old, new):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    assert lines[hits[0]].count(old) == 1, (old, lines[hits[0]])
    lines[hits[0]] = lines[hits[0]].replace(old, new)
    return "\n".join(lines)


def json_edit(text, edit):
    data = json.loads(text)
    edit(data)
    eol = "\r\n" if "\r\n" in text else "\n"
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", eol) + eol


def java_string(literal):
    return literal.replace('\\"', '"').replace("\\\\", "\\")


def grab(code, pattern):
    """Tuple of the integer (or string) groups of the first match, None when absent."""
    m = re.search(pattern, code)
    if not m:
        return None
    return tuple(int(x) if re.fullmatch(r"-?\d+", x) else x for x in m.groups())


def png_size(data):
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def num(text):
    """A Java numeric literal (2.5D, 1.0F, 100_000L, Double.MAX_VALUE, Integer.MAX_VALUE) as float/int; the strings stay strings."""
    t = text.strip()
    if t == "Double.MAX_VALUE":
        return "DMAX"
    if t == "Integer.MAX_VALUE":
        return "IMAX"
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)[dDfF]?", t)
    return float(m[1]) if m else t


# ---------------------------------------------------------------- state and inputs

class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src and migration, the per-file references to
    the client classes and the result id of every generated crafting recipe."""

    def __init__(self, files, tree, refs, recipe_ids):
        self.files, self.tree, self.refs, self.recipe_ids = files, tree, refs, recipe_ids

    def copy(self):
        return State(dict(self.files), dict(self.tree), {k: dict(v) for k, v in self.refs.items()}, dict(self.recipe_ids))

    def text(self, path):
        return self.files[path].decode("utf-8")

    def has(self, path):
        return path in self.files

    def set_bytes(self, path, data):
        self.files[path] = data
        self.tree[path] = sha(data)
        if path.startswith(RECIPES):
            self.recipe_ids[path] = recipe_result(data.decode("utf-8", errors="replace"))

    def set_text(self, path, text):
        self.set_bytes(path, text.encode("utf-8"))

    def delete(self, path):
        self.files.pop(path, None)
        self.tree.pop(path, None)
        self.recipe_ids.pop(path, None)


class Inputs:
    pass


def recipe_result(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    result = data.get("result") if isinstance(data, dict) else None
    return result.get("id") if isinstance(result, dict) else (result if isinstance(result, str) else None)


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


REF_PATTERNS = dict(RenderRBMKLid=re.compile(r"\bRenderRBMKLid\b"), RenderRBMKDebris=re.compile(r"\bRenderRBMKDebris\b"),
                    ResourceManagerRBMK=re.compile(r"\bResourceManager\.(?:deb_(?:blank|element|fuel|rod|lid)|RBMK_DEB_\w+)\b"))


def scan_refs():
    refs = {}
    for base, dirs, names in os.walk(ROOT / "src/main/java"):
        for name in names:
            if not name.endswith(".java"):
                continue
            path = Path(base) / name
            text = blank_comments(path.read_bytes().decode("utf-8", errors="replace"))
            hit = {k: len(p.findall(text)) for k, p in REF_PATTERNS.items() if p.search(text)}
            if hit:
                refs[path.relative_to(ROOT).as_posix()] = hit
    return refs


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


def otext(path):
    return lf(read_text(ORIGINAL / path))


def start_text(path):
    """The start bytes of a scope file: the frozen copy, else the blob of the start commit (line endings as committed)."""
    copy = START / path
    if copy.exists():
        return read_text(copy)
    return git(ROOT, "show", f"{START_COMMIT}:{path}").decode("utf-8")


LOAD_TEXT = (NEW_CLASSES + [TURBO, CC, NCFG, NB, NBET, NET, ZD, NI, CT, CP, NMC, RM, GEOM, HR, HTR, CU, AMR, ANVIL, RP, LOOT, TAG, MP, BSP, LP, TI, DY, LB, FT_PH, FT_TRAIT, FLUIDTYPE,
                                                                  TOOLTIP, HGT, RCGT, DUMMYABLE, ZH, MAP, OWN, CLASSIFY, STAMP, EN, G_TAG])
START_NEEDED = [TURBO, CC, NB, NBET, NET, ZD, NI, CT, CP, RM, HR, HTR, CU, AMR, ANVIL, RP, LOOT, TAG, MP, BSP, LP, TI, DY, LB, FT_PH, FT_TRAIT, FLUIDTYPE, TOOLTIP, GEOM, HGT, ZH, MAP, EN]


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start = {p: start_text(p) for p in START_NEEDED}
    inp.start_hash_ok = {p: (START / p).exists() and sha((START / p).read_bytes()) == inp.base_files.get(p) for p in baseline["copied_scope"]}
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    try:
        inp.name_status = git(ORIGINAL, "diff", "--name-status", "-M", OLD_HEAD, ORIGINAL_HEAD).decode("utf-8").strip().split("\n")
    except Exception as error:  # noqa: BLE001
        inp.name_status = [repr(error)]
    inp.o_en_lines = parse_lang_lines(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh_lines = parse_lang_lines(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    names = dict(dials=O_DIALS, base=O_BASE, blank=O_BLANK, absorber=O_ABSORBER, reflector=O_REFLECTOR, moderator=O_MODERATOR, console=O_CONSOLE, neutron=O_NEUTRON,
                 rbmkbase=O_RBMKBASE, deb=O_DEB, burn=O_BURN, rad=O_RAD, ent=O_ENT, lid=O_LID, tooling=O_TOOLING, degr=O_DEGR, dyatlov=O_DYATLOV, moditems=O_MODITEMS,
                 modblocks=O_MODBLOCKS, craft=O_CRAFT, asm=O_ASM, haz=O_HAZ, anvil=O_ANVIL, contam=O_CONTAM, phero=O_PHERO, trait=O_TRAIT, htr=O_HTR, turbo=O_TURBO)
    inp.o = {name: otext(path) for name, path in names.items()}
    files = {}
    paths = list(dict.fromkeys(LOAD_TEXT + GENERATED))
    for path in paths:
        if (ROOT / path).exists():
            files[path] = (ROOT / path).read_bytes()
    recipe_ids = {}
    for p in sorted((ROOT / RECIPES).glob("*.json")):
        rel = p.relative_to(ROOT).as_posix()
        data = p.read_bytes()
        recipe_ids[rel] = recipe_result(data.decode("utf-8", errors="replace"))
        if rel in G_RECIPES:
            files[rel] = data
    inp.gametest_other = gametest_total(read_text(p) for p in sorted((ROOT / GAMETEST_DIR).glob("*.java")) if p.name not in ("RBMKCoreGameTests.java", "HazardGameTests.java"))
    own_path = ROOT / OWN
    inp.own = json.loads(own_path.read_text(encoding="utf-8")) if own_path.exists() else {"assets": []}
    inp.o_res, inp.o_blob = {}, {}
    for a in inp.own["assets"]:
        src = ORIGINAL / a["source_path"]
        if src.exists():
            inp.o_res[a["target_path"]] = src.read_bytes()
        if a["target_path"].endswith(".obj"):
            try:
                inp.o_blob[a["target_path"]] = git(ORIGINAL, "show", "HEAD:" + a["source_path"])
            except Exception as error:  # noqa: BLE001
                inp.o_blob[a["target_path"]] = repr(error).encode("utf-8")
    for a in inp.own["assets"]:
        if (ROOT / a["target_path"]).exists():
            files[a["target_path"]] = (ROOT / a["target_path"]).read_bytes()
    inp.reused_start = {}
    for reused in (RES + "models/obj/projectiles/deb_graphite.obj", RES + "textures/block/block_graphite.png"):
        files[reused] = (ROOT / reused).read_bytes()
        inp.reused_start[reused] = git(ROOT, "show", f"{START_COMMIT}:{reused}")
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    return inp, State(files, hash_tree(), scan_refs(), recipe_ids)


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


def jload(st, path):
    return json.loads(st.text(path))


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    ck("V0.baseline-copies-match", all(inp.start_hash_ok.values()) and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]) == 38,
       "every baseline-files copy (38 in copied_scope) hashes to its baseline.json entry", [p for p, v in inp.start_hash_ok.items() if not v])
    needed = NEW_CLASSES + EDITED + [ZH, MAP, OWN, CLASSIFY, RCGT, HGT] + GENERATED
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 1114adf5", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.start-blobs", all(p in inp.start for p in START_NEEDED), "the start text of every compared file was loaded (frozen copy or git blob of 1114adf5)")


# ---------------------------------------------------------------- V1

def parse_orig_dials(text):
    return [(m[1], m[2].strip()) for m in re.finditer(r'KEY_\w+\("(dial\w+)",\s*([^)]+)\)', blank_comments(text))]


def parse_orig_clamps(text):
    """dial key string -> clamp tuple, from the refresh() statements (RBMKDials.java:91-114)."""
    code = blank_comments(text)
    keymap = {m[1]: m[2] for m in re.finditer(r'(KEY_\w+)\("(dial\w+)"', code)}
    out = {}
    for stmt in squash(code[code.index("public static void refresh"):]).split(";"):
        m = re.search(r"gameRules\.get\(RBMKKeys\.(KEY_\w+)\)\.add\(newTuple\.Pair<>\(world,(.*)\)\)$", stmt)
        if not m:
            continue
        expr = m[2]
        if (g := re.fullmatch(r"GameRuleHelper\.getDoubleMinimum\(world,RBMKKeys\.KEY_\w+,([\d.]+)D\)", expr)):
            clamp = ("min", float(g[1]))
        elif (g := re.fullmatch(r"GameRuleHelper\.getClampedDouble\(world,RBMKKeys\.KEY_\w+,([\d.]+)D,([\d.]+)D\)", expr)):
            clamp = ("range", float(g[1]), float(g[2]))
        elif (g := re.fullmatch(r"GameRuleHelper\.getClampedInt\(world,RBMKKeys\.KEY_\w+,(\d+),(\d+)\)(-1)?", expr)):
            clamp = ("irange", int(g[1]), int(g[2]), -1 if g[3] else 0)
        elif "getGameRuleBooleanValue" in expr:
            clamp = ("bool",)
        else:
            clamp = ("?", expr)
        out[keymap[m[1]]] = clamp
    return out


def parse_orig_getters(text):
    """getter name -> (dial key, negated) from the original RBMKDials getters."""
    code = blank_comments(text)
    out = {}
    keymap = {m[1]: m[2] for m in re.finditer(r'(KEY_\w+)\("(dial\w+)"', code)}
    for name in re.findall(r"public static (?:double|int|boolean) (get\w+)\(World world\)", code):
        o = code.index(f" {name}(World world)")
        open_index = code.index("{", o)
        body = squash(code[open_index + 1:match_brace(code, open_index)])
        m = re.search(r"getGameRule\(world,RBMKKeys\.(KEY_\w+)\)", body)
        out[name] = (keymap[m[1]], body.startswith("return!")) if m else (None, False)
    return out


ORIG_CRAFT_LINES = {752: "rbmk_lid", 757: "rbmk_absorber", 758: "rbmk_reflector", 788: "deco_rbmk", 789: "deco_rbmk_smooth", 790: "rbmk_blank_from_deco_rbmk", 791: "rbmk_blank_from_deco_rbmk_smooth"}
# GOAL24A 24A-5 / CraftingManager.java:752-758 and :788-791 as literals: (output, count, pattern rows, key -> expression)
TASK_CRAFT = {
    752: ("rbmk_lid", 4, ["PPP", "CCC", "PPP"], {"P": "STEEL.plate()", "C": "ModBlocks.concrete_asbestos"}),
    753: ("rbmk_lid_glass", 4, ["LLL", "BBB", "P P"], {"P": "STEEL.plate()", "L": "ModBlocks.glass_lead", "B": "ModBlocks.glass_boron"}),
    754: ("rbmk_lid_glass", 4, ["BBB", "LLL", "P P"], {"P": "STEEL.plate()", "L": "ModBlocks.glass_lead", "B": "ModBlocks.glass_boron"}),
    756: ("rbmk_moderator", 1, [" G ", "GRG", " G "], {"G": "GRAPHITE.block()", "R": "ModBlocks.rbmk_blank"}),
    757: ("rbmk_absorber", 1, ["GGG", "GRG", "GGG"], {"G": "B.ingot()", "R": "ModBlocks.rbmk_blank"}),
    758: ("rbmk_reflector", 1, ["GGG", "GRG", "GGG"], {"G": "ModItems.neutron_reflector", "R": "ModBlocks.rbmk_blank"}),
    788: ("deco_rbmk", 8, ["R"], {"R": "ModBlocks.rbmk_blank"}),
    789: ("deco_rbmk_smooth", 1, ["R"], {"R": "ModBlocks.deco_rbmk"}),
    790: ("rbmk_blank", 1, ["RRR", "R R", "RRR"], {"R": "ModBlocks.deco_rbmk"}),
    791: ("rbmk_blank", 1, ["RRR", "R R", "RRR"], {"R": "ModBlocks.deco_rbmk_smooth"}),
}


def parse_orig_craft(text):
    lines = text.split("\n")
    out = {}
    for number in list(range(752, 759)) + list(range(788, 792)):
        m = re.match(r'\s*addRecipeAuto\(new ItemStack\((?:ModItems|ModBlocks)\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);\s*$', lines[number - 1])
        if not m:
            continue
        parts = split_top(m[3])
        rows = [p[1:-1] for p in parts if p.startswith('"')]
        rest = [p for p in parts if not p.startswith('"')]
        keys = {rest[i].strip("'"): rest[i + 1] for i in range(0, len(rest), 2)}
        out[number] = (m[1], int(m[2]), rows, keys)
    return out


def parse_orig_ass_rbmk(text):
    lines = text.split("\n")
    block = "\n".join(lines[527:531])
    m = re.search(r'new GenericRecipe\("ass\.rbmk"\)\.setup\((\d+), (\d+)\)\.outputItems\(new ItemStack\(ModBlocks\.(\w+), (\d+)\)\)\s*\.inputItems\((.*?)\)\s*\.inputItemsEx', block, re.S)
    if not m:
        return None
    inputs = [(k, e, int(n)) for k, e, n in re.findall(r"new (OreDictStack|ComparableStack)\(([\w.]+(?:\(\))?), (\d+)\)", m[5])]
    return dict(setup=(int(m[1]), int(m[2])), output=(m[3], int(m[4])), inputs=inputs, ex_line_has_pools="setPools528" in "\n".join(lines[527:532]))


def v1_original(ck, inp, st, facts=None):
    o = inp.o
    # ---- dials
    dials = parse_orig_dials(o["dials"])
    ck("V1.dials-keys", dials == ORIG_DIALS and len(dials) == 25, "RBMKDials.java:17-51 has the 25 dial keys with the task book defaults, in file order", dials)
    ck("V1.dials-not-registered", sorted(k for k, _ in ORIG_DIALS if k not in [d[0] for d in NEO_DIALS]) == sorted(NOT_REGISTERED) and len(NEO_DIALS) == 21,
       "the four dials that NEO does not register are dialSaveDials, dialReasimBoilers, dialReasimRange and dialReasimBoilerSpeed (25 - 4 = 21)")
    clamps = parse_orig_clamps(o["dials"])
    reasim = {k: clamps.pop(k, None) for k in ("dialReasimRange", "dialReasimBoilers", "dialReasimBoilerSpeed")}
    ck("V1.dials-clamps", clamps == ORIG_CLAMP and reasim == {"dialReasimRange": ("irange", 1, 100, 0), "dialReasimBoilers": ("bool",), "dialReasimBoilerSpeed": ("range", 0.0, 1.0)}, "RBMKDials.java:91-114 clamps: minimum 0 for the rates, [0,1] for the flow/provision/efficiency/heat-conversion dials, column height [2,16] - 1, flux range [1,100], booleans plain",
       {k: (clamps.get(k), ORIG_CLAMP.get(k)) for k in set(clamps) | set(ORIG_CLAMP) if clamps.get(k) != ORIG_CLAMP.get(k)})
    getters = parse_orig_getters(o["dials"])
    want = {n: (k, n in ("getDepletion", "getXenon")) for n, k in ORIG_GETTERS.items()}
    ck("V1.dials-getters", all(getters.get(n) == v for n, v in want.items()) and sorted(set(getters) - set(want)) == sorted(ORIG_REASIM_GETTERS),
       "the original getters read the expected dial; getDepletion and getXenon negate the disable dials; the only other getters are the three ReaSim ones", getters)
    # ---- TileEntityRBMKBase
    b = o["base"]
    ck("V1.base-constants", mcode(b, "public double maxHeat()") == "return1500D;" and mcode(b, "public int trackingRange()") == "return15;"
       and mcode(b, "protected void coolPassively(int neighbors)") == "this.heat-=this.passiveCooling(neighbors);if(heat<20)heat=20D;",
       "TileEntityRBMKBase: maxHeat 1500, trackingRange 15 (:82-84,:103-105), coolPassively subtracts passiveCooling and floors at 20 (:256-259)")
    ck("V1.base-passive-cooling", mcode(b, "public double passiveCooling(int neighbors)") == "doublemin=RBMKDials.getPassiveCoolingInner(worldObj);doublemax=RBMKDials.getPassiveCooling(worldObj);"
       "returnmin+(max-min)*((4-MathHelper.clamp_int(neighbors,0,4))/4D);", "passiveCooling = inner + (outer - inner) * (4 - clamp(neighbors, 0, 4)) / 4 (:91-95)")
    code = whole(b)
    ck("V1.base-neighbour-order", re.search(r"neighborDirs=newForgeDirection\[\]\{ForgeDirection\.NORTH,ForgeDirection\.EAST,ForgeDirection\.SOUTH,ForgeDirection\.WEST\};", code) is not None,
       "neighborDirs is NORTH, EAST, SOUTH, WEST (:147-152)")
    mh = mcode(b, "private void moveHeat()")
    ck("V1.base-moveheat", not missing(mh, "List<TileEntityRBMKBase>rec=newArrayList<>();rec.add(this);doubleheatTot=this.heat;", "Compat.getTileStandard(worldObj,xCoord+dir.offsetX,yCoord,zCoord+dir.offsetZ)",
                                       "intmembers=rec.size();doublestepSize=RBMKDials.getColumnHeatFlow(worldObj);if(members>1){doubletargetHeat=heatTot/(double)members;",
                                       "doubledelta=targetHeat-rbmk.heat;rbmk.heat+=delta*stepSize;", "this.markDirty();}", "coolPassively(members-1);"),
       "moveHeat (:159-234): members = self + the four same-y neighbours, target = average, each member moves delta * getColumnHeatFlow, markDirty only for members > 1, then coolPassively(members - 1)", missing(mh, "members>1"))
    ck("V1.base-update", mcode(b, "public void updateEntity()").find("moveHeat();") >= 0 and mcode(b, "public void updateEntity()").endswith("this.networkPackNT(trackingRange());}"),
       "updateEntity (server): moveHeat first, networkPackNT(trackingRange()) last (:107-123)")
    ck("V1.base-nbt-heat", 'this.heat=nbt.getDouble("heat");' in mcode(b, "public void readFromNBT(NBTTagCompound nbt)") and 'nbt.setDouble("heat",this.heat);' in mcode(b, "public void writeToNBT(NBTTagCompound nbt)")
       and "buf.writeDouble(this.heat);" in mcode(b, "public void serialize(ByteBuf buf)") and "this.heat=buf.readDouble();" in mcode(b, "public void deserialize(ByteBuf buf)"),
       "NBT key heat (double) and the heat double leads serialize/deserialize (:267-305)")
    ck("V1.base-onmelt-lid", mcode(b, "public void onMelt(int reduce)") == "standardMelt(reduce);if(this.getBlockMetadata()==RBMKBase.DIR_NORMAL_LID.ordinal()+RBMKBase.offset)spawnDebris(DebrisType.LID);",
       "onMelt: standardMelt, then a LID debris only when the core meta is DIR_NORMAL_LID (the standard lid) (:385-391)")
    ck("V1.base-standardmelt", mcode(b, "protected void standardMelt(int reduce)") == "inth=RBMKDials.getColumnHeight(worldObj);reduce=MathHelper.clamp_int(reduce,1,h);if(worldObj.rand.nextInt(3)==0)reduce++;"
       "for(inti=h;i>=0;i--){if(i<=h+1-reduce){if(reduce>1&&i==h+1-reduce){worldObj.setBlock(xCoord,yCoord+i,zCoord,ModBlocks.pribris_burning);}else{worldObj.setBlock(xCoord,yCoord+i,zCoord,ModBlocks.pribris);}}"
       "else{worldObj.setBlock(xCoord,yCoord+i,zCoord,Blocks.air);}worldObj.markBlockForUpdate(xCoord,yCoord+i,zCoord);}",
       "standardMelt (:393-416): reduce clamped to [1,h], 1/3 chance of +1, from the top down: pribris below the line, pribris_burning on it (reduce > 1), air above")
    sd = mcode(b, "protected void spawnDebris(DebrisType type)")
    ck("V1.base-spawndebris", not missing(sd, "newEntityRBMKDebris(worldObj,xCoord+0.5D,yCoord+4D,zCoord+0.5D,type)", "debris.motionX=worldObj.rand.nextGaussian()*0.25D;", "debris.motionZ=worldObj.rand.nextGaussian()*0.25D;",
                                          "debris.motionY=0.25D+worldObj.rand.nextDouble()*1.25D;", "if(type==DebrisType.LID){debris.motionX*=0.5D;debris.motionY+=0.5D;debris.motionZ*=0.5D;}"),
       "spawnDebris (:418-432): at y + 4, gaussian * 0.25 horizontally, 0.25 + nextDouble * 1.25 up; a LID halves the horizontals and adds 0.5 up")
    md = mcode(b, "public void meltdown()")
    ck("V1.base-meltdown", md.startswith("RBMKBase.dropLids=false;") and not missing(md, "getFF(xCoord,yCoord,zCoord);", "if(rbmk.xCoord<minX)minX=rbmk.xCoord;if(rbmk.xCoord>maxX)maxX=rbmk.xCoord;if(rbmk.zCoord<minZ)minZ=rbmk.zCoord;if(rbmk.zCoord>maxZ)maxZ=rbmk.zCoord;",
                                                                                   "intminDist=Math.min(distFromMinX,Math.min(distFromMaxX,Math.min(distFromMinZ,distFromMaxZ)));rbmk.onMelt(minDist+1);",
                                                                                   'data.setString("type","rbmkmush");data.setFloat("scale",smallDim);', "intsmallDim=Math.min(maxX-minX,maxZ-minZ);",
                                                                                   '"hbm:block.rbmk_explosion",50.0F,1.0F);', "RBMKBase.dropLids=true;"),
       "meltdown (:439-573): dropLids off first, flood fill, bounds, onMelt(minDist + 1), rbmkmush particle scale min(width, depth), rbmk_explosion volume 50, dropLids on at the end", missing(md, "getFF"))
    gf = mcode(b, "private void getFF(int x, int y, int z)")
    ck("V1.base-getff", gf.find("getFF(x+1,y,z);getFF(x-1,y,z);getFF(x,y,z+1);getFF(x,y,z-1);") >= 0 and "if(!columns.contains(rbmk))" in gf,
       "getFF visits x+1, x-1, z+1, z-1 at the same y and stops at a column already collected (:575-591)")
    # ---- the four passive columns
    passive = {}
    for name, key, count_expr, kinds in (("blank", "BLANK", (1, 2, "BLANK"), None), ("absorber", "ABSORBER", (1, 2, "BLANK"), "ABSORBER"), ("reflector", "REFLECTOR", (1, 2, "BLANK"), "REFLECTOR"),
                                         ("moderator", "MODERATOR", (2, 3, "GRAPHITE"), "MODERATOR")):
        c = whole(o[name])
        g = grab(c, r"intcount=(\d+)\+worldObj\.rand\.nextInt\((\d+)\);for\(inti=0;i<count;i\+\+\)\{spawnDebris\(DebrisType\.(\w+)\);\}super\.onMelt\(reduce\);")
        # nextInt(bound) with bound 2 -> count in [base, base + 1]: "1 to 2" / "2 to 3"
        passive[name] = (g[0], g[0] + g[1] - 1, g[2]) if g else None
        want_type = f"publicRBMKTypegetRBMKType(){{returnRBMKType.{kinds};}}" if kinds else None
        if kinds == "REFLECTOR":
            want_type = "publicRBMKNeutronHandler.RBMKTypegetRBMKType(){returnRBMKNeutronHandler.RBMKType.REFLECTOR;}"
        passive[name] += (f"returnColumnType.{key};" in c, (want_type in c) if want_type else "getRBMKType" not in c)
    ck("V1.passive-columns", passive == {"blank": (1, 2, "BLANK", True, True), "absorber": (1, 2, "BLANK", True, True), "reflector": (1, 2, "BLANK", True, True), "moderator": (2, 3, "GRAPHITE", True, True)},
       "TileEntityRBMKBlank/Absorber/Reflector drop 1-2 BLANK debris, TileEntityRBMKModerator 2-3 GRAPHITE; each reports its ColumnType and (but the blank) its RBMKType", passive)
    ct = re.findall(r"(\w+)\((\d+)\)", blank_comments(o["console"])[blank_comments(o["console"]).index("enum ColumnType"):][:700])
    rt = re.findall(r"^\s*(\w+),?\s*(?://.*)?$", blank_comments(o["neutron"])[blank_comments(o["neutron"]).index("enum RBMKType"):].split("}")[0].split("{", 1)[1], re.M)
    ck("V1.enums", ct[:14] == [("BLANK", "0"), ("FUEL", "10"), ("FUEL_SIM", "90"), ("CONTROL", "20"), ("CONTROL_AUTO", "30"), ("BOILER", "40"), ("MODERATOR", "50"), ("ABSORBER", "60"),
                               ("REFLECTOR", "70"), ("OUTGASSER", "80"), ("BREEDER", "100"), ("STORAGE", "110"), ("COOLER", "120"), ("HEATEX", "130")]
       and [x for x in rt if x] == ["ROD", "MODERATOR", "CONTROL_ROD", "REFLECTOR", "ABSORBER", "OUTGASSER", "OTHER"], "ColumnType has 14 members with offsets, RBMKType has seven (TileEntityRBMKConsole.java:502-523, RBMKNeutronHandler.java:28-36)", (ct[:14], rt))
    # ---- RBMKBase
    r = o["rbmkbase"]
    rc = whole(r)
    ck("V1.rbmkbase-basics", not missing(rc, "this.setHardness(3F);this.setResistance(30F);", "publicstaticbooleandropLids=true;", "publicint[]getDimensions(){returnnewint[]{3,0,0,0,0,0};}", "publicintgetOffset(){return0;}",
                                         "publicint[]getDimensions(Worldworld){returnnewint[]{RBMKDials.getColumnHeight(world),0,0,0,0,0};}", "protectedForgeDirectiongetDirModified(ForgeDirectiondir){returnDIR_NO_LID;}",
                                         "DIR_NO_LID=ForgeDirection.NORTH;", "DIR_NORMAL_LID=ForgeDirection.EAST;", "DIR_GLASS_LID=ForgeDirection.SOUTH;",
                                         "this.makeExtra(world,x,y+RBMKDials.getColumnHeight(world),z);"),
       "RBMKBase: hardness 3 / resistance 30 (:52-56), dropLids (:37), fixed {3,0,0,0,0,0} placement check and {height,0,...} fill (:96-98,:178-180), lid metas NORTH/EAST/SOUTH (:157-159), makeExtra at core + height (:168-171)", missing(rc, "dropLids=true"))
    ck("V1.rbmkbase-break-drop", not missing(mcode(r, "public void breakBlock(World world, int x, int y, int z, Block b, int i)"),
                                              "if(!world.isRemote&&dropLids){if(i==DIR_NORMAL_LID.ordinal()+offset){world.spawnEntityInWorld(newEntityItem(world,x+0.5,y+0.5+RBMKDials.getColumnHeight(world),z+0.5,newItemStack(ModItems.rbmk_lid)));}",
                                              "if(i==DIR_GLASS_LID.ordinal()+offset){world.spawnEntityInWorld(newEntityItem(world,x+0.5,y+0.5+RBMKDials.getColumnHeight(world),z+0.5,newItemStack(ModItems.rbmk_lid_glass)));}}super.breakBlock(world,x,y,z,b,i);"),
       "breakBlock (:182-196): a lid drops at core + 0.5 + height only while dropLids is true, then super.breakBlock")
    sc = mcode(r, "public boolean onScrew(World world, EntityPlayer player, int x, int y, int z, int side, float fX, float fY, float fZ, ToolType tool)")
    ck("V1.rbmkbase-onscrew", not missing(sc, "if(tool!=ToolType.SCREWDRIVER)returnfalse;", "int[]pos=this.findCore(world,x,y,z);", "if(rbmk.hasLid()&&rbmk.isLidRemovable()){", "node.removeLid();",
                                          "newEntityItem(world,pos[0]+0.5,pos[1]+0.5+RBMKDials.getColumnHeight(world),pos[2]+0.5,newItemStack(ModItems.rbmk_lid))", "newItemStack(ModItems.rbmk_lid_glass)",
                                          "rbmk.explodeOnBroken=false;world.setBlockMetadataWithNotify(pos[0],pos[1],pos[2],DIR_NO_LID.ordinal()+offset,3);rbmk.explodeOnBroken=true;}returntrue;}}}returnfalse;"),
       "onScrew (:198-239): only ToolType.SCREWDRIVER, only a lid that is present and removable, drops the lid item at core + 0.5 + height, core meta back to NO_LID, true; otherwise false")
    ck("V1.rbmkbase-collision", "if(rbmk.hasLid()){height+=0.25F;}" in mcode(r, "public AxisAlignedBB getCollisionBoundingBoxFromPool(World world, int x, int y, int z)"),
       "getCollisionBoundingBoxFromPool raises the box by 0.25 when the core has a lid (:127-148)")
    ck("V1.rbmkbase-openinv", "if(player.getHeldItem()!=null&&player.getHeldItem().getItem()instanceofItemRBMKLid){if(!rbmk.hasLid())returnfalse;}" in mcode(r, "public boolean openInv(World world, int x, int y, int z, EntityPlayer player)"),
       "openInv: a held lid is only handled by the lid item (:117-119)")
    # ---- the debris blocks
    d, bn, rd = whole(o["deb"]), whole(o["burn"]), whole(o["rad"])
    ck("V1.debris-block", "publicclassRBMKDebrisextendsBlock{publicRBMKDebris(){super(Material.iron);}" in d and "isOpaqueCube(){returnfalse;}" in d and "renderAsNormalBlock(){returnfalse;}" in d,
       "RBMKDebris is a non-opaque iron block with a custom render type")
    ck("V1.debris-burning", not missing(bn, "inttickRate(Worldworld){return100+world.rand.nextInt(20);}", "if(rand.nextInt(5)==0){", 'data.setString("type","rbmkflame");data.setInteger("maxAge",300);',
                                        "newTargetPoint(world.provider.dimensionId,x+0.5,y+1.75,z+0.5,75)", "if(rand.nextInt(10)==0&&block==Blocks.air){world.setBlock(x+dir.offsetX,y+dir.offsetY,z+dir.offsetZ,ModBlocks.gas_meltdown);}",
                                        "intchance=block==ModBlocks.foam_layer||block==ModBlocks.block_foam||block==ModBlocks.sand_boron_layer||(block==ModBlocks.sand_mix&&meta==EnumSandType.BORON.ordinal())?10:100;",
                                        "if(rand.nextInt(chance)==0){world.setBlock(x,y,z,ModBlocks.pribris);}else{world.scheduleBlockUpdate(x,y,z,this,this.tickRate(world));}",
                                        "if(world.rand.nextInt(3)==0){", "world.scheduleBlockUpdate(x,y,z,this,this.tickRate(world));}}"),
       "RBMKDebrisBurning (scheduled ticks): tickRate 100 + nextInt(20); 1/5 flame (maxAge 300, 75 blocks); 1/10 meltdown gas in an air side; foam/boron side 1/10 else 1/100 to become pribris; onBlockAdded 1/3 flame and schedules")
    ck("V1.debris-radiating", not missing(rd, "inttickRate(Worldworld){return20+world.rand.nextInt(20);}", "radiate(world,x,y,z);", "floatrads=1000000F;doublerange=100D;",
                                          "intchance=block==ModBlocks.sand_boron_layer||(block==ModBlocks.sand_mix&&m==EnumSandType.BORON.ordinal())?25:1000;",
                                          "if(meta<15){world.setBlockMetadataWithNotify(x,y,z,meta+1,2);world.scheduleBlockUpdate(x,y,z,this,this.tickRate(world));}else{world.setBlock(x,y,z,ModBlocks.pribris_burning);}",
                                          "if(res<1)res=1;floateRads=rads;eRads/=(float)res;eRads/=(float)(len*len);", "ContaminationUtil.contaminate(e,HazardType.RADIATION,ContaminationType.CREATIVE,eRads);",
                                          "if(len<5){e.attackEntityFrom(DamageSource.inFire,100);}", "res+=world.getBlock(ix,iy,iz).getExplosionResistance(null);"),
       "RBMKDebrisRadiating: tickRate 20 + nextInt(20); radiate 1,000,000 / resistance / len^2 as entity contamination (CREATIVE) within 100 blocks, fire damage 100 under 5 blocks; 1/1000 (boron 1/25) roll counts meta 0..15 then pribris_burning")
    # ---- the debris entity
    e = whole(o["ent"])
    life = dict(re.findall(r"case(\w+):return([\d*]+);", e[e.index("getLifetime"):]))
    pick = dict(re.findall(r"case(\w+):if\(player\.inventory\.addItemStackToInventory\(newItemStack\(ModItems\.(\w+)\)\)\)this\.setDead\(\);break;", e))
    size = dict((k, (a, b)) for k, a, b in re.findall(r"case(\w+):this\.setSize\(([\d.]+)F,([\d.]+)F\);break;", e))
    ck("V1.entity-lifetimes", life == {"BLANK": "3*60*20", "ELEMENT": "3*60*20", "FUEL": "10*60*20", "GRAPHITE": "15*60*20", "LID": "30*20", "ROD": "60*20"},
       "EntityRBMKDebris.getLifetime (:139-150): BLANK 3 min, ELEMENT 3 min, FUEL 10 min, GRAPHITE 15 min, LID 30 s, ROD 1 min", life)
    ck("V1.entity-pickup", pick == {"BLANK": "debris_metal", "ELEMENT": "debris_metal", "FUEL": "debris_fuel", "GRAPHITE": "debris_graphite", "LID": "rbmk_lid", "ROD": "debris_metal"},
       "interactFirst pickup map (:34-52): BLANK/ELEMENT/ROD -> debris_metal, FUEL -> debris_fuel, GRAPHITE -> debris_graphite, LID -> rbmk_lid", pick)
    ck("V1.entity-sizes", size == {"BLANK": ("0.5", "0.5"), "ELEMENT": ("1", "1"), "FUEL": ("0.25", "0.25"), "GRAPHITE": ("0.25", "0.25"), "LID": ("1", "0.5"), "ROD": ("0.75", "0.5")},
       "entity sizes (:57-67): BLANK 0.5x0.5, ELEMENT 1x1, FUEL and GRAPHITE 0.25x0.25, LID 1x0.5, ROD 0.75x0.5", size)
    ck("V1.entity-effects", not missing(e, "this.getEntityBoundingBox()" if False else "this.boundingBox.expand(2.5,2.5,2.5)", "intlevel=this.getType()==DebrisType.FUEL?9:4;", "e.addPotionEffect(newPotionEffect(HbmPotion.radiation.id,60*20,level));",
                                        "if(!RBMKDials.getPermaScrap(worldObj)&&this.ticksExisted>getLifetime()+this.getEntityId()%50)this.setDead();", 'nbt.setInteger("debtype",'),
       "FUEL/GRAPHITE debris: radiation potion level 9/4 for 60 s on living entities within 2.5 blocks (:100-107); the entity ends after its lifetime + id % 50 only when perma-scrap is off (:109-110); NBT key debtype")
    ck("V1.entity-lid-dig", not missing(e, "if(this.getType()==DebrisType.LID&&motionY>0){", "worldObj.func_147447_a(pos,next,false,false,false)", "if(rn<=1||rand.nextInt(rn)==0)worldObj.setBlockToAir(x+i,y+j,z+k);", "this.setDead();"),
       "a rising LID debris digs a 3x3x3 hole where its ray hits a block: centre and face neighbours always, edges 1/2, corners 1/3 (:72-98)")
    ck("V1.entity-enum", re.search(r"enumDebrisType\{BLANK,ELEMENT,FUEL,ROD,GRAPHITE,LID;\}", e) is not None and "motionY-=0.04D;" in e and "this.motionX*=0.85D;" in e and "this.motionY*=-0.5D;" in e and "this.rot+=10F;" in e,
       "DebrisType order BLANK, ELEMENT, FUEL, ROD, GRAPHITE, LID; gravity 0.04, ground damping 0.85 / -0.5, spin 10 per tick")
    # ---- the lid item
    li = mcode(o["lid"], "public boolean onItemUse(ItemStack stack, EntityPlayer player, World world, int x, int y, int z, int side, float fx, float fy, float fz)")
    ck("V1.lid-item", not missing(li, "if(tile.hasLid())returnfalse;", "intmeta=RBMKBase.DIR_NORMAL_LID.ordinal();", "if(this==ModItems.rbmk_lid_glass){meta=RBMKBase.DIR_GLASS_LID.ordinal();",
                                  "Blocks.glass.stepSound.getVolume()+1.0F)/2.0F,Blocks.glass.stepSound.getPitch()*0.8F", "ModBlocks.concrete_smooth.stepSound.getVolume()+1.0F)/2.0F,ModBlocks.concrete_smooth.stepSound.getPitch()*0.8F",
                                  "stack.stackSize--;returntrue;"),
       "ItemRBMKLid (:21-66): only a core without a lid; glass item -> glass lid with the glass place sound, else the concrete lid with the concrete place sound; volume (v+1)/2, pitch * 0.8; one item consumed")
    # ---- crafting rows
    rows = parse_orig_craft(o["craft"])
    bad = {n: (rows.get(n), want) for n, want in TASK_CRAFT.items() if rows.get(n) != want}
    ck("V1.craft-rows", not bad and sorted(rows) == sorted(TASK_CRAFT), "CraftingManager.java:752-758 and :788-791 are the ten task book rows (lid x4, glass lid x4 twice, moderator, absorber, reflector, deco x8, smooth, two blank rows)", bad)
    # ---- ass.rbmk
    ass = parse_orig_ass_rbmk(o["asm"])
    ck("V1.ass-rbmk", ass == dict(setup=(100, 100), output=("rbmk_blank", 1), inputs=[("ComparableStack", "ModBlocks.concrete_asbestos", 4), ("OreDictStack", "STEEL.plateCast()", 2), ("OreDictStack", "CU.plate()", 4),
                                                                                            ("OreDictStack", "RUBBER.ingot()", 2)], ex_line_has_pools=True),
       "AssemblyMachineRecipes.java:528-530: ass.rbmk 100 tick / 100 HE, concrete_asbestos x4, steel cast plate x2, copper plate x4, rubber ingot x2 -> rbmk_blank; inputItemsEx and setPools528 follow", ass)
    # ---- hazard, anvil
    hz = o["haz"].split("\n")
    ck("V1.hazard-283", hz[282].strip() == "HazardSystem.register(debris_fuel, makeData().addEntry(RADIATION, 500F).addEntry(HOT, 5F));", "HazardRegistry.java:283 is debris_fuel RADIATION 500 + HOT 5", hz[282].strip())
    an = o["anvil"]
    tiers = re.findall(r"constructionRecipes\.add\(new AnvilConstructionRecipe\(\s*new ComparableStack\(ModBlocks\.(rbmk_\w+)\), new AnvilOutput\[\] \{.*?\}\)\.setTier\((\d+)\)", an[an.index("//RBMK"):an.index("//RBMK") + 2500], re.S)
    ck("V1.anvil-rows", [t for t in tiers[:3]] == [("rbmk_moderator", "4"), ("rbmk_absorber", "4"), ("rbmk_reflector", "4")] and 868 <= an[:an.index("//RBMK")].count("\n") + 1 <= 870,
       "AnvilRecipes.java:868-882: three tier-4 recycling rows (moderator, absorber, reflector -> rbmk_blank plus graphite blocks / boron ingots / neutron reflectors); NEO registers none (V7)", tiers[:3])
    # ---- tooling, items, blocks
    tl, dg = whole(o["tooling"]), whole(o["degr"])
    ck("V1.tooling", "if(((IToolable)b).onScrew(world,player,x,y,z,side,fX,fY,fZ,this.type)){if(this.getMaxDamage()>0)stack.damageItem(1,player);returntrue;}}returnfalse;" in tl
       and "this.setMaxStackSize(1);this.setMaxDamage(durability);this.setNoRepair();" in dg, "ItemTooling.onItemUse (:30-40) damages the tool and returns true only when onScrew is true; ItemCraftingDegradation: stack size 1, max damage = durability, no repair (:12-14)")
    mi = o["moditems"].split("\n")
    ck("V1.moditems", mi[3708].strip() == 'screwdriver = new ItemTooling(ToolType.SCREWDRIVER, 100).setUnlocalizedName("screwdriver");' and mi[3709].strip() == 'screwdriver_desh = new ItemTooling(ToolType.SCREWDRIVER, 0).setUnlocalizedName("screwdriver_desh");'
       and "ItemDyatlov" in mi[3646] and 'rbmk_lid = new ItemRBMKLid().setUnlocalizedName("rbmk_lid")' in mi[3024] and 'debris_fuel = new Item().setUnlocalizedName("debris_fuel")' in mi[3365],
       "ModItems.java:3709-3710 screwdriver durability 100 / desh 0, :3647 meltdown_tool is ItemDyatlov, :3025-3026 the lids, :3366 debris_fuel", (mi[3708].strip(), mi[3709].strip()))
    mb = o["modblocks"].split("\n")
    ck("V1.modblocks", ".setHardness(5.0F).setResistance(100.0F)" in mb[1442] and ".setHardness(5.0F).setResistance(100.0F)" in mb[1443]
       and all(".setHardness(50.0F).setResistance(600.0F)" in mb[n] for n in (2145, 2146, 2147)) and all(f'new RBMK{c}().setBlockName("rbmk_{n}")' in mb[i] for c, n, i in (("Blank", "blank", 2121), ("Reflector", "reflector", 2123),
                                                                                                                                                          ("Absorber", "absorber", 2124), ("Moderator", "moderator", 2125))),
       "ModBlocks.java: deco_rbmk(_smooth) hardness 5 / resistance 100 (:1443-1444), the three pribris blocks 50 / 600 (:2146-2148), the four columns (:2122-2126)", (mb[1442].strip()[:90], mb[2145].strip()[:90]))
    # ---- language lines
    bad = {}
    for neo_key, o_key, en_line, zh_line, en, zh in LANG13 + LANG_PHERO:
        if lang_value(inp.o_en_lines, en_line, o_key) != en or lang_value(inp.o_zh_lines, zh_line, o_key) != zh:
            bad[neo_key] = (inp.o_en_lines[en_line - 1], inp.o_zh_lines[zh_line - 1])
    for key, en_line, zh_line, en in LANG_CHLORIDE:
        if lang_value(inp.o_en_lines, en_line, key) != en:
            bad[key] = inp.o_en_lines[en_line - 1]
    ck("V1.lang-lines", not bad, "the 13 RBMK keys, the two pheromone keys and the two chloride names have the expected English (and Chinese) text at their en_US.lang / zh_CN.lang lines", bad)
    # ---- 24A-2 sources
    ck("V1.closeout-sources", "I18nUtil.resolveKey(\"hbmfluid.trait.glyphidPheromones\")" in o["phero"].split("\n")[28] and "I18nUtil.resolveKey(\"hbmfluid.trait.modifiedPheromones\")" in o["phero"].split("\n")[30]
       and "if(player.capabilities.isCreativeMode && cont != ContaminationType.NONE && cont != ContaminationType.DIGAMMA2)" in o["contam"].split("\n")[283]
       and "reacher = ((EntityPlayer) target).inventory.hasItem(ModItems.reacher);" in o["htr"], "FT_Pheromone.java:29-31 keys, ContaminationUtil.java:284 creative precedence, HazardTypeRadiation inventory.hasItem(reacher)")
    trait = re.findall(r'registerTrait\("(\w+)", (\w+)\.class\);', blank_comments(o["trait"]))
    ck("V1.trait-order", [t[0] for t in trait][:6] == ["corrosive", "flammable", "combustible", "polluting", "heatable", "coolable"] and len({c for _, c in trait}) == len(trait),
       "FluidTrait.java:23-28 registers corrosive, flammable, combustible, polluting, heatable, coolable once each, in that order (no duplicate class)", trait[:8])
    if facts is not None:
        facts["V1"] = dict(dials=len(dials), clamps=clamps, craft_rows=sorted(rows), ass_rbmk=ass, passive=passive)


# ---------------------------------------------------------------- V2

FIELD_OF = {k: "DIAL_" + re.sub(r"(?<!^)(?=[A-Z])", "_", k[len("dial"):]).upper() for k, _ in NEO_DIALS}
FIELD_OF["dialEnablePermaScrap"] = "DIAL_ENABLE_PERMA_SCRAP"
FIELD_OF["dialOutgasserSpeedMod"] = "DIAL_OUTGASSER_SPEED_MOD"
FIELD_OF["dialControlSurgeMod"] = "DIAL_CONTROL_SURGE_MOD"


def config_entries(text):
    """(full path, key, field or None, call, args) of every define/defineInRange in CommonConfig, with builder.push/pop tracked."""
    code = blank_comments(lf(text))
    out, stack = [], []
    pos = code.index("CommonConfig(ModConfigSpec.Builder builder)") if "CommonConfig(ModConfigSpec.Builder builder)" in code else 0
    for m in re.finditer(r'builder\.push\("([^"]+)"\)|builder\.pop\(\)|\b(?:(\w+)\s*=\s*)?builder(?:\s*\.\s*\w+\((?:[^()"]|"[^"]*"|\([^()]*\))*\))*?\s*\.\s*(defineInRange|define)\(', code[pos:], re.S):
        if m[1]:
            stack.append(m[1])
        elif m.group(0).startswith("builder.pop"):
            stack.pop()
        else:
            open_index = pos + m.end() - 1
            args = split_top(code[open_index + 1:match_paren(code, open_index)])
            out.append((tuple(stack), java_string(args[0].strip('"')), m[2], m[3], [a for a in args[1:]]))
    return out, stack


def v2_config(ck, inp, st):
    text = st.text(CC)
    entries, final_stack = config_entries(text)
    code = whole(text)
    rbmk = [e for e in entries if e[0] == ("rbmk",)]
    ck("V2.entries-count", len(rbmk) == 21 and final_stack == [], "CommonConfig has 21 define/defineInRange entries under push(\"rbmk\") and every push is popped", (len(rbmk), final_stack))
    ck("V2.section-order", code.index('builder.push("rbmk")') > code.index('builder.push("rtg")') and code.count('builder.push("rbmk")') == 1
       and code.index('builder.push("rbmk")') < code.index('builder.push("pollution")') and code.count("builder.push(") == code.count("builder.pop()"),
       "the rbmk section is pushed once, after rtg and before the pollution (hazards) section; push and pop counts are equal")
    want = [k for k, _ in NEO_DIALS]
    # the declaration order in the file is the order of the original dials with the absorber heat conversion last (the original lists it last in RBMKDials.java:51)
    order = [e[1] for e in rbmk]
    ck("V2.keys", sorted(order) == sorted(want) and len(set(order)) == 21, "the 21 rbmk keys are exactly the original dials minus dialSaveDials, dialReasimBoilers, dialReasimRange, dialReasimBoilerSpeed", sorted(set(want) ^ set(order)))
    defaults = dict(NEO_DIALS)
    bad_default, bad_range, bad_field = {}, {}, {}
    for path, key, field, call, args in rbmk:
        if key not in defaults:
            continue
        default = args[0].strip() if defaults[key] in ("true", "false") else num(args[0])
        expected_default = defaults[key] if defaults[key] in ("true", "false") else num(defaults[key])
        if default != expected_default:
            bad_default[key] = (args[0], defaults[key])
        clamp = ORIG_CLAMP[key]
        if clamp[0] == "bool":
            got, exp = call, "define"
        elif clamp[0] == "min":
            got, exp = (call, tuple(num(a) for a in args[1:])), ("defineInRange", (0.0, "DMAX"))
        elif clamp[0] == "range":
            got, exp = (call, tuple(num(a) for a in args[1:])), ("defineInRange", (clamp[1], clamp[2]))
        else:
            got, exp = (call, tuple(num(a) for a in args[1:])), ("defineInRange", (clamp[1], clamp[2]))
        if got != exp:
            bad_range[key] = (got, exp)
        if field != FIELD_OF[key]:
            bad_field[key] = (field, FIELD_OF[key])
    ck("V2.defaults", not bad_default, "each rbmk key has the original default (RBMKDials.java:17-51): 2.5, 0.1, 0.2, 1.0, 0.2, height 4, perma scrap true, 0.1, 1.0 ..., flux 5, booleans false, absorber heat 0.05", bad_default)
    ck("V2.ranges", not bad_range, "each rbmk range equals the original clamp (:91-114): minimum 0 (Double.MAX_VALUE upper) for the rates, [0,1] for the flow/provision/efficiency/conversion dials, height [2,16], flux [1,100], booleans define", bad_range)
    ck("V2.fields", not bad_field, "each entry is assigned to its DIAL_* field", bad_field)
    declared = re.findall(r"public final (DoubleValue|IntValue|BooleanValue) (DIAL_\w+);", text)
    kind = {"min": "DoubleValue", "range": "DoubleValue", "bool": "BooleanValue", "irange": "IntValue"}
    ok_types = all(kind[ORIG_CLAMP[k][0]] == t for k, f in FIELD_OF.items() for t, n in declared if n == f)
    ck("V2.field-types", len(declared) == 21 and sorted(n for _, n in declared) == sorted(FIELD_OF.values()) and ok_types,
       "21 public final DIAL_* fields, typed Double/Int/BooleanValue like the original getter types", declared)
    bad_tr = []
    for path, key, field, call, args in rbmk:
        pattern = f'.translation("hbmsntm.configuration.{key}")'
        if pattern not in code:
            bad_tr.append(key)
    ck("V2.translations", not bad_tr and all(f'.translation("hbmsntm.configuration.{k}")' + (".defineInRange" if ORIG_CLAMP[k][0] != "bool" else ".define") + f'("{k}"' in code for k in want),
       "every rbmk key carries .translation(\"hbmsntm.configuration.<key>\") directly before its define", bad_tr)
    ck("V2.comments", all(f"{FIELD_OF[k]}=builder.comment(" in code for k in want), "every rbmk entry is declared as DIAL_* = builder.comment(...)")
    full = collections.Counter((e[0], e[1]) for e in entries)
    dups = [k for k, n in full.items() if n > 1]
    ck("V2.unique-keys", not dups, "every config path (section + key) is defined once in the whole spec, including the two explosion pushes", dups)
    meteor = sorted(e[1] for e in entries if e[1].startswith("meteor"))
    ck("V2.meteor-rename", "meteorStrikeChance" in meteor and "meteorShowerChance" in meteor and meteor.count("meteorStrikeChance") == 1 and meteor.count("meteorShowerChance") == 1
       and '.translation("hbmsntm.configuration.meteorShowerChance")' in code and code.count('.translation("hbmsntm.configuration.meteorStrikeChance")') == 1,
       "meteorStrikeChance and meteorShowerChance are each defined once and each with its own translation (main-notes 24A-2: the second define was a copy of the first key)", meteor)
    start = inp.start[CC]
    deleted, inserted = diff_summary(start, text)
    exp_deleted = ['.translation("hbmsntm.configuration.meteorStrikeChance")', '.defineInRange("meteorStrikeChance", 18000, 1, Integer.MAX_VALUE);']
    # the first define in the meteor section keeps the strike key; the line pair deleted is the second (shower) pair only
    ck("V2.diff-vs-start", len(deleted) == 2 and deleted == exp_deleted and ".translation(\"hbmsntm.configuration.meteorShowerChance\")" in inserted
       and '.defineInRange("meteorShowerChance", 18000, 1, Integer.MAX_VALUE);' in inserted, "CommonConfig vs its start copy: the only deleted lines are the second meteorStrikeChance define pair, replaced by meteorShowerChance; the rest are insertions (the rbmk fields and section)", deleted)
    ck("V2.crlf", text.count("\r\n") == text.count("\n") and text.count("\r\n") > 0 and start.count("\r\n") == start.count("\n"), "CommonConfig keeps its CRLF line endings throughout (start copy is CRLF)", (text.count("\r\n"), text.count("\n")))
    ncfg = st.text(NCFG)
    ck("V2.ntmconfig", "public static final CommonConfig COMMON;" in ncfg and "COMMON_SPEC = commonPair.getRight();" in ncfg and "container.registerConfig(ModConfig.Type.COMMON, COMMON_SPEC);" in ncfg
       and sha(ncfg.encode("utf-8")) == inp.base_files.get(NCFG), "NtmConfig exposes COMMON and registers the COMMON spec, byte-equal to the start copy (no edit needed)")
    # ---- the facade
    dials_src = st.text(DIALS)
    dcode = whole(dials_src)
    getters = dict(re.findall(r"publicstatic(?:double|int|boolean)(get\w+)\(\)\{(return[^;]*;)\}", dcode))
    want_g = {}
    for name, key in ORIG_GETTERS.items():
        expr = f"NtmConfig.COMMON.{FIELD_OF[key]}.get()"
        if name == "getColumnHeight":
            expr += "-1"
        if name in ("getDepletion", "getXenon"):
            expr = "!" + expr
        want_g[name] = f"return{expr};"
    ck("V2.facade-getters", getters == want_g, "RBMKDials has the 21 original getter names without a World argument, each reading its field; getColumnHeight is value - 1 (RBMKDials.java:96), getDepletion and getXenon negate the disable keys", {k: (getters.get(k), want_g.get(k)) for k in set(getters) | set(want_g) if getters.get(k) != want_g.get(k)})
    ck("V2.facade-shape", "publicclassRBMKDials{" in dcode and "World" not in dcode and "Level" not in dcode and "reasim" not in dcode.lower() and "savedials" not in dcode.lower(),
       "RBMKDials takes no World/Level and has no ReaSim or dialSaveDials getter")
    ck("V2.facade-reads-live", "DIAL_" in dcode and "static finalint" not in dcode and "cache" not in dcode.lower(), "the facade reads the config at call time (no cached copy)")


# ---------------------------------------------------------------- V3

def v3_block_entity(ck, inp, st):
    t = st.text(BASE_BE)
    m = lambda sig: mcode(t, sig)  # noqa: E731
    w = whole(t)
    ck("V3.constants", m("public double maxHeat()") == "return1500D;" and m("public int trackingRange()") == "return15;"
       and m("protected void coolPassively(int neighbors)") == "this.heat-=this.passiveCooling(neighbors);if(heat<20)heat=20D;",
       "RBMKBaseBlockEntity: maxHeat 1500 (original :82-84), trackingRange 15 (:103-105), coolPassively floors at 20 (:256-259)")
    ck("V3.passive-cooling", m("public double passiveCooling(int neighbors)") == "doublemin=RBMKDials.getPassiveCoolingInner();doublemax=RBMKDials.getPassiveCooling();returnmin+(max-min)*((4-Mth.clamp(neighbors,0,4))/4D);",
       "passiveCooling = inner + (outer - inner) * (4 - clamp(neighbors, 0, 4)) / 4 (original :91-95)")
    ck("V3.neighbour-order", "Direction[]neighborDirs=newDirection[]{Direction.NORTH,Direction.EAST,Direction.SOUTH,Direction.WEST};" in w,
       "neighborDirs is NORTH, EAST, SOUTH, WEST (original :147-152)")
    mh = m("private void moveHeat()")
    ck("V3.moveheat", not missing(mh, "List<RBMKBaseBlockEntity>rec=newArrayList<>();rec.add(this);doubleheatTot=this.heat;", "BlockPospos=this.worldPosition.relative(dir);",
                                  "if(this.level.isLoaded(pos)&&this.level.getBlockEntity(pos)instanceofRBMKBaseBlockEntitybase){neighborCache[index]=base;}",
                                  "intmembers=rec.size();doublestepSize=RBMKDials.getColumnHeatFlow();if(members>1){doubletargetHeat=heatTot/(double)members;",
                                  "doubledelta=targetHeat-rbmk.heat;rbmk.heat+=delta*stepSize;}this.setChanged();}coolPassively(members-1);") and mh.endswith("coolPassively(members-1);"),
       "moveHeat (original :159-234): the four same-y neighbours only when loaded, average over members, each moves delta * getColumnHeatFlow, setChanged only for members > 1, coolPassively(members - 1) last",
       missing(mh, "if(members>1){", "this.setChanged();}coolPassively(members-1);"))
    ck("V3.update", m("public void updateEntity()") == "if(this.level==null||this.level.isClientSide)return;moveHeat();this.networkPackNT(trackingRange());",
       "updateEntity runs on the server only: moveHeat first, networkPackNT(trackingRange()) last (original :107-123)")
    ck("V3.nbt-heat", m("protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)") == 'super.loadAdditional(tag,registries);this.heat=tag.getDouble("heat");'
       and m("protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)") == 'super.saveAdditional(tag,registries);tag.putDouble("heat",this.heat);',
       "persistence: NBT key heat (double), parent keys first, no other key (original :267-305)")
    ck("V3.serialize-symmetric", m("public void serialize(RegistryFriendlyByteBuf buf)") == "super.serialize(buf);buf.writeDouble(this.heat);" and m("public void deserialize(RegistryFriendlyByteBuf buf)") == "super.deserialize(buf);this.heat=buf.readDouble();",
       "serialize and deserialize both run the parent first and carry one double, heat")
    ck("V3.machine-base", "super(type,pos,state,0);" in w and m("public int[] getSlotsForFace(Direction direction)") == "returnnewint[0];"
       and m("public @Nullable AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player)") == "returnnull;",
       "MachineBaseBlockEntity size 0, empty getSlotsForFace, createMenu null (no slots or GUI for the passive columns)")
    sm = m("protected void standardMelt(int reduce)")
    ck("V3.standardmelt", sm == "inth=RBMKDials.getColumnHeight();reduce=Mth.clamp(reduce,1,h);if(level.random.nextInt(3)==0)reduce++;DummyableBlock.safeRem=true;try{for(inti=h;i>=0;i--){BlockPospos=this.worldPosition.above(i);"
       "if(i<=h+1-reduce){if(reduce>1&&i==h+1-reduce){level.setBlock(pos,NtmBlocks.PRIBRIS_BURNING.get().defaultBlockState(),3);}else{level.setBlock(pos,NtmBlocks.PRIBRIS.get().defaultBlockState(),3);}}"
       "else{level.setBlock(pos,Blocks.AIR.defaultBlockState(),3);}}}finally{DummyableBlock.safeRem=false;}",
       "standardMelt (original :393-416): reduce clamped to [1, height], 1/3 chance of +1, from the top down pribris below the line, pribris_burning on it (reduce > 1), air above; safeRem set before and cleared in a finally", sm[:200])
    md = m("public void meltdown()")
    ck("V3.meltdown-flag", md == "if(this.level==null||this.level.isClientSide)return;RBMKBaseBlock.dropLids=false;try{meltConnected();}finally{RBMKBaseBlock.dropLids=true;}",
       "meltdown (server only) sets dropLids false and restores it in a finally (original :439-573 sets it false at the start and true at the end)")
    mc = m("private void meltConnected()")
    ck("V3.meltdown-bounds", not missing(mc, "Set<RBMKBaseBlockEntity>columns=newLinkedHashSet<>();getFF(columns);",
                                         "if(p.getX()<minX)minX=p.getX();if(p.getX()>maxX)maxX=p.getX();if(p.getZ()<minZ)minZ=p.getZ();if(p.getZ()>maxZ)maxZ=p.getZ();",
                                         "intminDist=Math.min(distFromMinX,Math.min(distFromMaxX,Math.min(distFromMinZ,distFromMaxZ)));rbmk.onMelt(minDist+1);",
                                         "intdistFromMinX=p.getX()-minX;intdistFromMaxX=maxX-p.getX();intdistFromMinZ=p.getZ()-minZ;intdistFromMaxZ=maxZ-p.getZ();",
                                         "if(RBMKDials.getOverpressure())handleOverpressure();", "intsmallDim=Math.min(maxX-minX,maxZ-minZ);intavgX=minX+(maxX-minX)/2;intavgZ=minZ+(maxZ-minZ)/2;"),
       "meltdown bounds: min/max x and z over the flood fill, minDist to the nearest bound, onMelt(minDist + 1), overpressure hook, smallDim = min(width, depth) (original :445-499)")
    ck("V3.meltdown-effects", not missing(mc, 'data.putString("type","rbmkmush");data.putFloat("scale",smallDim);', "PacketDistributor.sendToPlayersNear(serverLevel,null,avgX+0.5,yCoord+1,avgZ+0.5,250,newAuxParticle(data,avgX+0.5,yCoord+1,avgZ+0.5));",
                                           "level.playSound(null,avgX+0.5,yCoord+1,avgZ+0.5,NtmSoundEvents.RBMK_EXPLOSION.get(),SoundSource.BLOCKS,50.0F,1.0F);") and "TargetPoint(worldObj.provider.dimensionId,avgX+0.5,yCoord+1,avgZ+0.5,250)" in whole(inp.o["base"])
       and '"hbm:block.rbmk_explosion",50.0F,1.0F' in whole(inp.o["base"]),
       "the rbmkmush particle has scale min(width, depth) and radius 250 around (avgX + 0.5, y + 1, avgZ + 0.5); RBMK_EXPLOSION plays at volume 50, pitch 1 (original :546-551)")
    gf = m("private void getFF(Set<RBMKBaseBlockEntity> columns)")
    ck("V3.floodfill", not missing(gf, "if(level.isLoaded(pos)&&level.getBlockEntity(pos)instanceofRBMKBaseBlockEntityrbmk&&columns.add(rbmk)){open.push(pos.west());open.push(pos.north());open.push(pos.south());open.push(pos.east());}")
       and "Deque<BlockPos>open=newArrayDeque<>();open.push(this.worldPosition);" in gf,
       "getFF visits the four horizontal neighbours of every newly collected loaded column at the same y (original :575-591: x+1, x-1, z+1, z-1)")
    om = m("public void onMelt(int reduce)")
    ck("V3.onmelt-lid", om == "LidTypelid=this.getLid();standardMelt(reduce);if(lid==LidType.STANDARD)spawnDebris(DebrisType.LID);",
       "onMelt reads the lid before standardMelt replaces the core and spawns a LID debris only for the standard lid, not for glass (original :385-391 tests DIR_NORMAL_LID)")
    sd = m("protected void spawnDebris(DebrisType type)")
    ck("V3.spawndebris", sd == "RBMKDebrisdebris=newRBMKDebris(level,worldPosition.getX()+0.5D,worldPosition.getY()+4D,worldPosition.getZ()+0.5D,type);doublemotionX=level.random.nextGaussian()*0.25D;"
       "doublemotionZ=level.random.nextGaussian()*0.25D;doublemotionY=0.25D+level.random.nextDouble()*1.25D;if(type==DebrisType.LID){motionX*=0.5D;motionY+=0.5D;motionZ*=0.5D;}"
       "debris.setDeltaMovement(motionX,motionY,motionZ);level.addFreshEntity(debris);",
       "spawnDebris (original :418-432): at y + 4, gaussian * 0.25 horizontally, 0.25 + nextDouble * 1.25 up, a LID halves the horizontals and adds 0.5 up")
    parts = {}
    for name, path, count, kind, rbmk_type, column in (("blank", BE_BLANK, "1+level.random.nextInt(2)", "BLANK", None, "BLANK"), ("absorber", BE_ABSORBER, "1+level.random.nextInt(2)", "BLANK", "ABSORBER", "ABSORBER"),
                                                       ("reflector", BE_REFLECTOR, "1+level.random.nextInt(2)", "BLANK", "REFLECTOR", "REFLECTOR"), ("moderator", BE_MODERATOR, "2+level.random.nextInt(2)", "GRAPHITE", "MODERATOR", "MODERATOR")):
        s = st.text(path)
        good = (mcode(s, "public void onMelt(int reduce)") == f"intcount={count};for(inti=0;i<count;i++){{spawnDebris(DebrisType.{kind});}}super.onMelt(reduce);"
                and mcode(s, "public RBMKColumnType getConsoleType()") == f"returnRBMKColumnType.{column};"
                and ((rbmk_type is None and "getRBMKType" not in s) or (rbmk_type and mcode(s, "public RBMKType getRBMKType()") == f"returnRBMKType.{rbmk_type};")))
        parts[name] = good
    ck("V3.subclasses", all(parts.values()) and len(parts) == 4, "blank, absorber and reflector drop 1-2 BLANK debris, the moderator 2-3 GRAPHITE (original TileEntityRBMKBlank/Absorber/Reflector/Moderator onMelt); each reports its console type and (but the blank, which keeps OTHER) its RBMKType", parts)
    ck("V3.base-types", "publicRBMKTypegetRBMKType(){returnRBMKType.OTHER;}" in w and "publicabstractRBMKColumnTypegetConsoleType();" in w and "publicbooleanisModerated(){returnfalse;}" in w,
       "the base column reports RBMKType.OTHER, is not moderated and leaves the console type abstract")
    types = squash(blank_comments(st.text(RBMK_TYPE)))
    cols = squash(blank_comments(st.text(COLUMN_TYPE)))
    ck("V3.enums", "{ROD,MODERATOR,CONTROL_ROD,REFLECTOR,ABSORBER,OUTGASSER,OTHER}" in types
       and "BLANK(0),FUEL(10),FUEL_SIM(90),CONTROL(20),CONTROL_AUTO(30),BOILER(40),MODERATOR(50),ABSORBER(60),REFLECTOR(70),OUTGASSER(80),BREEDER(100),STORAGE(110),COOLER(120),HEATEX(130);" in cols,
       "RBMKType and RBMKColumnType carry the original members, order and console offsets (RBMKNeutronHandler.java:28-36, TileEntityRBMKConsole.java:502-523)")
    ck("V3.lid-api", m("public boolean hasLid()") == "if(!isLidRemovable())returntrue;returnthis.getLid()!=LidType.NONE;" and "publicbooleanisLidRemovable(){returntrue;}" in w and "publicvoidonLidChanged(){}" in w,
       "hasLid is true for a column whose lid cannot be removed, else LID != NONE; isLidRemovable true; onLidChanged is the empty hook for Goal24C")
    ck("V3.render-box", m("public AABB getRenderBoundingBox()") == "returnnewAABB(worldPosition.getX(),worldPosition.getY(),worldPosition.getZ(),worldPosition.getX()+1,worldPosition.getY()+17,worldPosition.getZ()+1);",
       "getRenderBoundingBox reaches y + 17 (original :607-610)")
    ck("V3.no-client-imports", not re.search(r"net\.minecraft\.client|com\.hbm\.render|com\.hbm\.main\.(ClientProxy|ResourceManager)|OnlyIn|Dist\.CLIENT", t),
       "the base block entity imports no client class and uses no @OnlyIn (it runs on both logical sides)")


# ---------------------------------------------------------------- V4

def v4_blocks(ck, inp, st):
    b = st.text(BASE_BLK)
    w = whole(b)
    m = lambda sig: mcode(b, sig)  # noqa: E731
    ck("V4.base-class", "publicabstractclassRBMKBaseBlockextendsDummyableBlockimplementsIToolable,ILookOverlay{" in w and 'EnumProperty<LidType>LID=EnumProperty.create("lid",LidType.class);' in w
       and 'NONE("none"),STANDARD("standard"),GLASS("glass");' in w and "publicstaticbooleandropLids=true;" in w,
       "RBMKBaseBlock is an abstract DummyableBlock + IToolable; LID is an EnumProperty none / standard / glass (the original's NORTH / EAST / SOUTH core meta, RBMKBase.java:157-159); dropLids starts true (:37)")
    ck("V4.base-ctor", m("public RBMKBaseBlock(Properties properties)") == "super(properties.dynamicShape());this.registerDefaultState(this.defaultBlockState().setValue(LID,LidType.NONE));"
       and m("protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder)") == "super.createBlockStateDefinition(builder);builder.add(LID);",
       "the column keeps dynamicShape() (the lid collision depends on the core, not on the state) and defaults to no lid")
    ck("V4.dimensions", "publicint[]getDimensions(){returnnewint[]{RBMKDials.getColumnHeight(),0,0,0,0,0};}" in w and "publicintgetOffset(){return0;}" in w
       and m("protected Direction getDirModified(Direction dir)") == "returnDirection.NORTH;"
       and m("protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset)") == "super.fillSpace(level,pos,dir,offset);this.makeExtra(level,pos.above(RBMKDials.getColumnHeight()));",
       "getDimensions {height,0,0,0,0,0}, offset 0, fixed NORTH facing (original DIR_NO_LID, :173-176), makeExtra at core + height (:168-171)")
    ck("V4.collision", "VoxelShapeLID_SHAPE=Shapes.box(0,0,0,1,1.25,1);" in w and m("protected VoxelShape getCollisionShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context)") == "returnthis.getLid(level,pos)!=LidType.NONE?LID_SHAPE:Shapes.block();",
       "a lid raises the collision box by 0.25 (original getCollisionBoundingBoxFromPool :127-148)")
    ck("V4.get-lid", m("public LidType getLid(BlockGetter level, BlockPos pos)") == "BlockPos.MutableBlockPoscursor=pos.mutable();for(inti=0;i<=16;i++){BlockStatestate=level.getBlockState(cursor);if(state==null||state.getBlock()!=this)returnLidType.NONE;"
       "if(isCore(state))returnstate.getValue(LID);cursor.move(getPointingDirection(state).getOpposite());}returnLidType.NONE;", "getLid follows the dummies down to the core of the same block and reads its LID state, at most 17 blocks")
    ck("V4.use-item", m("protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult)") ==
       "if(stack.getItem()instanceofRBMKLidItem)returnItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;returnsuper.useItemOn(stack,state,level,pos,player,hand,hitResult);",
       "a held lid is left to RBMKLidItem.useOn (original openInv :117-119)")
    ck("V4.drop-lid", m("public static void dropLid(Level level, BlockPos core, LidType lid)") == "ItemStackstack=switch(lid){caseSTANDARD->newItemStack(NtmItems.RBMK_LID.get());caseGLASS->newItemStack(NtmItems.RBMK_LID_GLASS.get());caseNONE->ItemStack.EMPTY;};"
       "if(stack.isEmpty())return;level.addFreshEntity(newItemEntity(level,core.getX()+0.5,core.getY()+0.5+RBMKDials.getColumnHeight(),core.getZ()+0.5,stack));",
       "dropLid drops rbmk_lid / rbmk_lid_glass at core + 0.5 + height (original :188-193, :222-231)")
    ck("V4.on-remove", m("public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving)") ==
       "if(!level.isClientSide&&dropLids&&isCore(state)&&!state.is(newState.getBlock())){dropLid(level,pos,state.getValue(LID));}super.onRemove(state,level,pos,newState,isMoving);",
       "the lid drops from a removed core only on the server, only while dropLids is true and only when the block really goes away (a lid on or off is a same-block state change) (original breakBlock :182-196)")
    ck("V4.on-screw", m("public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool)") ==
       "if(tool!=ToolType.SCREWDRIVER)returnfalse;BlockPoscore=this.findCore(level,pos);if(core==null)returnfalse;if(!(level.getBlockEntity(core)instanceofRBMKBaseBlockEntityrbmk))returnfalse;"
       "if(!rbmk.hasLid()||!rbmk.isLidRemovable())returnfalse;if(!level.isClientSide){BlockStatecoreState=level.getBlockState(core);dropLid(level,core,coreState.getValue(LID));"
       "level.setBlock(core,coreState.setValue(LID,LidType.NONE),3);rbmk.onLidChanged();}returntrue;",
       "onScrew (original :198-239): only a SCREWDRIVER, only a present and removable lid; server drops the lid, sets LID NONE and calls onLidChanged; true on both sides, else false")
    # ---- client isolation of the base block
    span = method_span(b, "public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos)")
    code = blank_comments(lf(b))
    outside = code[:span[0]] + code[span[1]:]
    outside = "\n".join(l for l in outside.split("\n") if not l.startswith("import "))
    start_ann = code.rfind("@OnlyIn(Dist.CLIENT)", 0, span[0])
    ck("V4.client-isolation", start_ann >= 0 and code[start_ann:span[0]].count("{") == 0 and not re.search(r"\b(Minecraft|GuiGraphics|Font|RenderGuiEvent)\b", outside.replace("RenderGuiEvent.Pre event", "")),
       "the client classes (Minecraft, GuiGraphics, Font, RenderGuiEvent) are used only inside printHook, which carries @OnlyIn(Dist.CLIENT) (the ILookOverlay hook of the other multiblocks)", re.findall(r"\b(?:Minecraft|GuiGraphics|Font|RenderGuiEvent)\b", outside)[:5])
    ck("V4.diag-hook", '"tile.rbmk.dodd."+key' in w and 'List<String>exceptions=List.of("x","y","z","items","id","muffled");' in w and "if(mc.options.hideGui)return;" in w,
       "printHook shows the DODD overlay with tile.rbmk.dodd.<key> lines and the exception list x, y, z, items, id, muffled; hidden with the GUI (original diagnosticPrintHook :313-376)")
    # ---- passive block
    p = st.text(PASSIVE_BLK)
    pw = whole(p)
    ck("V4.passive", "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;returnthis.type.get().create(pos,state);" in pw
       and "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};" in pw
       and "publicclassRBMKPassiveBlockextendsRBMKBaseBlock{" in pw, "RBMKPassiveBlock: only the core has a block entity and a ticker (original createNewTileEntity meta >= offset)")
    # ---- registrations of the blocks (properties)
    nb = st.text(NB)
    bad = {}
    col = {"rbmk_blank": "RBMK_BLANK", "rbmk_reflector": "RBMK_REFLECTOR", "rbmk_absorber": "RBMK_ABSORBER", "rbmk_moderator": "RBMK_MODERATOR"}
    for name, const in col.items():
        line = [l for l in nb.split("\n") if f'register("{name}"' in l]
        want = f'newRBMKPassiveBlock(BlockBehaviour.Properties.of().strength(3.0F,30.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops(),NtmBlockEntityTypes.{const})'
        if len(line) != 1 or want not in squash(line[0]):
            bad[name] = line
    deb = {"pribris": "RBMKDebrisBlock", "pribris_burning": "RBMKDebrisBurningBlock", "pribris_radiating": "RBMKDebrisRadiatingBlock"}
    for name, cls in deb.items():
        line = [l for l in nb.split("\n") if f'register("{name}"' in l]
        want = f"new{cls}(BlockBehaviour.Properties.of().noOcclusion().strength(50.0F,600.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops())"
        if len(line) != 1 or want not in squash(line[0]):
            bad[name] = line
    for name in DECO:
        line = [l for l in nb.split("\n") if f'register("{name}"' in l]
        want = "newBlock(BlockBehaviour.Properties.of().strength(5.0F,100.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops())"
        if len(line) != 1 or want not in squash(line[0]):
            bad[name] = line
    ck("V4.block-properties", not bad, "ModBlocks.java: the four columns hardness 3 / resistance 30 (RBMKBase.java:52-56), the three debris blocks 50 / 600 (:2146-2148), the two deco blocks 5 / 100 (:1443-1444), all metal and needing the correct tool", bad)
    # ---- debris blocks
    db = st.text(DEB_BLK)
    ck("V4.debris-plain", "publicclassRBMKDebrisBlockextendsBlock{" in whole(db) and not re.search(r"tick|onPlace|getCollisionShape|getDrops", whole(db)), "pribris is a plain Block (the original RBMKDebris has no behaviour of its own); it drops itself through the loot table")
    bn = st.text(DEB_BURN)
    bm = lambda sig: mcode(bn, sig)  # noqa: E731
    ck("V4.burning-delay", bm("protected int tickDelay(RandomSource random)") == "return100+random.nextInt(20);", "burning debris reschedules every 100 + nextInt(20) ticks (original tickRate :21-24)")
    ck("V4.burning-effects", bm("protected static void sendFlame(Level level, double x, double y, double z)") == 'CompoundTagtag=newCompoundTag();tag.putInt("lifetime",300);ParticleUtil.addParticle(level,newNbtParticleOptions(NtmParticleTypes.RBMK_FLAME.get(),tag),x,y,z,75);'
       and "playFire" in bn, "the rbmkflame particle has lifetime 300 and range 75 (original maxAge 300, TargetPoint 75)")
    bt = bm("protected void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random)")
    ck("V4.burning-tick", bt == "if(random.nextInt(5)==0){sendFlame(level,pos.getX()+0.25+random.nextDouble()*0.5,pos.getY()+1.75,pos.getZ()+0.25+random.nextDouble()*0.5);playFire(level,pos,random);}"
       "BlockPosside=pos.relative(Direction.from3DDataValue(random.nextInt(6)));BlockStatesideState=level.getBlockState(side);if(random.nextInt(10)==0&&sideState.isAir()){level.setBlock(side,NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(),3);}"
       "intchance=sideState.is(NtmBlocks.BLOCK_FOAM.get())?10:100;if(random.nextInt(chance)==0){level.setBlock(pos,NtmBlocks.PRIBRIS.get().defaultBlockState(),3);}else{level.scheduleTick(pos,this,this.tickDelay(level.random));}",
       "burning tick (original updateTick :26-58): 1/5 flame, one random side, 1/10 meltdown gas into air, foam side 1/10 else 1/100 to become pribris, otherwise reschedule. The original also counts foam_layer, sand_boron_layer and boron sand_mix, which NEO does not have (documented deferral in the NEO comment)")
    ck("V4.burning-place", bm("protected void onPlace(BlockState state, Level level, BlockPos pos, BlockState oldState, boolean movedByPiston)") ==
       "super.onPlace(state,level,pos,oldState,movedByPiston);if(oldState.is(state.getBlock()))return;if(!level.isClientSide){if(level.random.nextInt(3)==0){sendFlame(level,pos.getX()+0.25+level.random.nextDouble()*0.5,pos.getY()+1.75,pos.getZ()+0.25+level.random.nextDouble()*0.5);}}level.scheduleTick(pos,this,this.tickDelay(level.random));",
       "onPlace (original onBlockAdded :60-74): a same-block change is no placement; 1/3 flame on the server; the first tick is scheduled")
    rd = st.text(DEB_RAD)
    rm = lambda sig: mcode(rd, sig)  # noqa: E731
    rw = whole(rd)
    ck("V4.radiating-constants", 'IntegerPropertyCOUNT=IntegerProperty.create("count",0,15);' in rw and "publicstaticfinalfloatRADS=1000000F;" in rw and "publicstaticfinaldoubleRANGE=100D;" in rw
       and rm("protected int tickDelay(RandomSource random)") == "return20+random.nextInt(20);", "radiating debris: COUNT 0..15 (original meta), 1,000,000 rads, range 100, tick every 20 + nextInt(20) (original :28-32,:80-84)")
    ck("V4.radiating-tick", rm("protected void tick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random)") == "radiate(level,pos);if(random.nextInt(5)==0){sendFlame(level,pos.getX()+random.nextDouble(),pos.getY()+1.75,pos.getZ()+random.nextDouble());playFire(level,pos,random);}"
       "BlockPosside=pos.relative(Direction.from3DDataValue(random.nextInt(6)));if(random.nextInt(10)==0&&level.getBlockState(side).isAir()){level.setBlock(side,NtmBlocks.GAS_MELTDOWN.get().defaultBlockState(),3);}"
       "intchance=1000;if(random.nextInt(chance)==0){intcount=state.getValue(COUNT);if(count<15){level.setBlock(pos,state.setValue(COUNT,count+1),2);level.scheduleTick(pos,this,this.tickDelay(level.random));}"
       "else{level.setBlock(pos,NtmBlocks.PRIBRIS_BURNING.get().defaultBlockState(),3);}}else{level.scheduleTick(pos,this,this.tickDelay(level.random));}",
       "radiating tick (original :35-78): radiate first, 1/5 flame, 1/10 gas, 1/1000 roll counts COUNT up to 15 then pribris_burning, else reschedule (the original's 1/25 boron-sand chance is deferred with the boron sand block)")
    ck("V4.radiate", rm("public static void radiate(Level level, BlockPos pos)") == "Vec3center=newVec3(pos.getX()+0.5,pos.getY()+0.5,pos.getZ()+0.5);List<LivingEntity>entities=level.getEntitiesOfClass(LivingEntity.class,newAABB(center,center).inflate(RANGE));"
       "for(LivingEntitye:entities){Vec3vec=newVec3(e.getX()-center.x,(e.getY()+e.getEyeHeight())-center.y,e.getZ()-center.z);doublelen=vec.length();vec=vec.normalize();floatres=0;"
       "for(inti=1;i<len;i++){BlockPosp=BlockPos.containing(center.x+vec.x*i,center.y+vec.y*i,center.z+vec.z*i);res+=level.getBlockState(p).getBlock().getExplosionResistance();}"
       "if(res<1)res=1;floateRads=RADS;eRads/=(float)res;eRads/=(float)(len*len);ContaminationUtil.contaminate(e,HazardType.RADIATION,ContaminationType.CREATIVE,eRads);if(len<5){e.hurt(level.damageSources().inFire(),100);}}",
       "radiate (original :80-125): every living entity within 100 blocks, resistance summed along the line to the eyes (min 1), 1e6 / res / len^2 as CREATIVE radiation contamination, fire damage 100 under 5 blocks. NEO sums getExplosionResistance() of its blocks (the 1.7.10 value is resistance / 5), the deliberate ZIRNOX precedent")
    # ---- lid item
    li = st.text(LID_ITEM)
    lw = whole(li)
    ck("V4.lid-item", mcode(li, "public InteractionResult useOn(UseOnContext context)") == "Levellevel=context.getLevel();BlockPospos=context.getClickedPos();if(!(level.getBlockState(pos).getBlock()instanceofRBMKBaseBlockrbmk))returnInteractionResult.PASS;"
       "BlockPoscore=rbmk.findCore(level,pos);if(core==null)returnInteractionResult.PASS;if(!(level.getBlockEntity(core)instanceofRBMKBaseBlockEntitytile))returnInteractionResult.PASS;if(tile.hasLid())returnInteractionResult.PASS;"
       "if(!level.isClientSide){SoundTypesound=this.lid==LidType.GLASS?SoundType.GLASS:SoundType.STONE;level.playSound(null,pos.getX()+0.5,pos.getY()+0.5,pos.getZ()+0.5,sound.getPlaceSound(),SoundSource.BLOCKS,(sound.getVolume()+1.0F)/2.0F,sound.getPitch()*0.8F);"
       "BlockStatecoreState=level.getBlockState(core);level.setBlock(core,coreState.setValue(RBMKBaseBlock.LID,this.lid),3);context.getItemInHand().shrink(1);tile.onLidChanged();}returnInteractionResult.sidedSuccess(level.isClientSide);",
       "RBMKLidItem.useOn (original ItemRBMKLid :21-66): a column without a lid only; place sound of glass or stone, volume (v + 1) / 2, pitch * 0.8; the core state takes the lid, one item consumed, onLidChanged; otherwise PASS")
    # ---- Dyatlov
    dy = st.text(DY)
    ck("V4.dyatlov", mcode(dy, "public InteractionResult useOn(UseOnContext context)").startswith("BlockPospos=context.getClickedPos();Levellevel=context.getLevel();if(!level.isClientSide){Blockblock=level.getBlockState(pos).getBlock();if(blockinstanceofRBMKBaseBlockrbmk){BlockPoscorePos=rbmk.findCore(level,pos);if(corePos!=null){BlockEntitybe=level.getBlockEntity(corePos);if(beinstanceofRBMKBaseBlockEntityrbmkBlockEntity)rbmkBlockEntity.meltdown();}}")
       and "zirnoxBlockEntity.heat=200000;" in whole(dy) and mcode(dy, "public InteractionResult useOn(UseOnContext context)").endswith("returnInteractionResult.PASS;"),
       "DyatlovItem (meltdown_tool, original ItemDyatlov :23-39): on the server a clicked RBMK column melts down its whole connected reactor; the ZIRNOX branch (heat 200000) stays; the click is not consumed")
    s = inp.start[DY]
    deleted, inserted = diff_summary(s, dy)
    ck("V4.dyatlov-diff", not deleted and any("RBMKBaseBlock" in x for x in inserted), "DyatlovItem differs from its start copy by insertions only (the RBMK branch and its imports)", deleted)


# ---------------------------------------------------------------- V5

def v5_entity(ck, inp, st):
    e = st.text(DEB_ENT)
    w = whole(e)
    m = lambda sig: mcode(e, sig)  # noqa: E731
    life = dict(re.findall(r"case(\w+)->([\d*]+);", w[w.index("getLifetime(){"):]))
    ck("V5.lifetimes", life == {"BLANK": "3*60*20", "ELEMENT": "3*60*20", "FUEL": "10*60*20", "GRAPHITE": "15*60*20", "LID": "30*20", "ROD": "60*20"}, "getLifetime (original :138-150): BLANK 3 min, ELEMENT 3 min, FUEL 10 min, GRAPHITE 15 min, LID 30 s, ROD 1 min", life)
    pick = {k: v for ks, v in re.findall(r"case([A-Z,]+)->newItemStack\(NtmItems\.(\w+)\.get\(\),1\);", w) for k in ks.split(",")}
    ck("V5.pickup", pick == {"BLANK": "DEBRIS_METAL", "ELEMENT": "DEBRIS_METAL", "ROD": "DEBRIS_METAL", "FUEL": "DEBRIS_FUEL", "GRAPHITE": "DEBRIS_GRAPHITE", "LID": "RBMK_LID"}, "pickup map (original interactFirst :34-52): BLANK/ELEMENT/ROD -> debris_metal, FUEL -> debris_fuel, GRAPHITE -> debris_graphite, LID -> rbmk_lid", pick)
    size = dict((k, (a, b)) for k, a, b in re.findall(r"case(\w+)->EntityDimensions\.scalable\(([\d.]+)F,([\d.]+)F\);", w))
    ck("V5.dimensions", size == {"BLANK": ("0.5", "0.5"), "ELEMENT": ("1", "1"), "FUEL": ("0.25", "0.25"), "GRAPHITE": ("0.25", "0.25"), "LID": ("1", "0.5"), "ROD": ("0.75", "0.5")}, "dimensions (original onUpdate :57-67): BLANK 0.5x0.5, ELEMENT 1x1, FUEL and GRAPHITE 0.25x0.25, LID 1x0.5, ROD 0.75x0.5", size)
    ck("V5.enum", "enumDebrisType{BLANK,ELEMENT,FUEL,ROD,GRAPHITE,LID;}" in w, "DebrisType order BLANK, ELEMENT, FUEL, ROD, GRAPHITE, LID (original enum)")
    ck("V5.effects", "intlvl=type==DebrisType.FUEL?9:4;" in w and "getEntitiesOfClass(LivingEntity.class,this.getBoundingBox().inflate(2.5D))" in w and "newMobEffectInstance(ModEffect.RADIATION,60*20,lvl)" in w
       and "if(type==DebrisType.FUEL||type==DebrisType.GRAPHITE){" in w, "FUEL and GRAPHITE debris give the radiation effect level 9 / 4 for 1200 ticks to living entities within 2.5 blocks (original :100-107)")
    ck("V5.perma-scrap", "if(!RBMKDials.getPermaScrap()&&this.tickCount>this.getLifetime()+this.getId()%50){this.discard();return;}" in w, "the entity ends after lifetime + id % 50 only when the perma-scrap dial is off (original :109-110)")
    ck("V5.lid-dig", "if(type==DebrisType.LID&&motion.y>0){Vec3pos=this.position();Vec3next=pos.add(motion.scale(2));" in w and "newClipContext(pos,next,ClipContext.Block.OUTLINE,ClipContext.Fluid.NONE,this)" in w
       and "ZirnoxDebris.digAround(this.level(),hit.getBlockPos(),this.random);this.discard();return;" in w, "a rising LID debris looks two motion lengths ahead and, on a block hit, digs through ZirnoxDebris.digAround (3x3x3 with the original's probabilities) and ends (original :72-98)")
    ck("V5.motion", "this.setDeltaMovement(before);" in w and "before=this.getDeltaMovement().add(0,-0.04D,0);" in w and "motion.x*0.85D,motion.y*-0.5D,motion.z*0.85D" in w and "this.rot+=10F;" in w and "mx=before.x*-0.75D" in w,
       "gravity 0.04, ground damping 0.85 horizontal / -0.5 vertical, spin 10 per tick, wall reflection -0.75 (EntityDebrisBase)")
    ck("V5.not-client", not re.search(r"net\.minecraft\.client|com\.hbm\.render|@OnlyIn", e), "the entity class imports no client class")
    pickup = m("public boolean pickUp(Predicate<ItemStack> inserter)")
    ck("V5.pickup-flow", pickup == "if(inserter.test(this.getPickupStack())){this.discard();returntrue;}returnfalse;",
       "an item is picked up only when the inventory accepts the stack; then the entity is discarded (original interactFirst: setDead after addItemStackToInventory)")
    z = st.text(ZD)
    deleted, inserted = diff_summary(inp.start[ZD], z)
    ck("V5.zirnox-diff", deleted == ["// The original reads RBMKDials.dialEnablePermaScrap, which defaults to true (RBMKDials.java:25). The RBMK dial system is",
                                     "// deferred in NEO, so debris never despawns, as with the original's default; there is no config for it.",
                                     "private static final boolean PERMA_SCRAP = true;",
                                     "if(!PERMA_SCRAP && this.tickCount > this.getLifetime() + this.getId() % 50) this.discard();"]
       and "import com.hbm.blockentity.machine.rbmk.RBMKDials;" in inserted and any("RBMKDials.getPermaScrap() && this.tickCount > this.getLifetime() + this.getId() % 50) this.discard();" in x for x in inserted)
       and len(inserted) == 4, "ZirnoxDebris differs from its start copy only by the PERMA_SCRAP constant replaced with RBMKDials.getPermaScrap() (import, comment, and the one condition)", (deleted, inserted))


# ---------------------------------------------------------------- V6

def count(text, needle):
    return lf(text).count(needle)


def tab_sections(text):
    code = lf(text)
    marks = [(m.start(), m[1]) for m in re.finditer(r"public static final Supplier<CreativeModeTab> (\w+) = CREATIVE_MODE_TABS\.register\(", code)]
    out = {}
    for n, (pos, name) in enumerate(marks):
        out[name] = code[pos:marks[n + 1][0] if n + 1 < len(marks) else len(code)]
    return out


BLOCK_CONST = {n: n.upper() for n in BLOCKS9}
BE_CLASS = {"rbmk_blank": "RBMKBlankBlockEntity", "rbmk_reflector": "RBMKReflectorBlockEntity", "rbmk_absorber": "RBMKAbsorberBlockEntity", "rbmk_moderator": "RBMKModeratorBlockEntity"}
TAB_OF = {"CONTROL": ["NtmItems.DEBRIS_FUEL", "NtmItems.RBMK_LID", "NtmItems.RBMK_LID_GLASS", "NtmItems.MELTDOWN_TOOL", "NtmItems.SCREWDRIVER", "NtmItems.SCREWDRIVER_DESH"],
          "BLOCKS": ["NtmBlocks.DECO_RBMK", "NtmBlocks.DECO_RBMK_SMOOTH"],
          "MACHINE": ["NtmBlocks.RBMK_BLANK", "NtmBlocks.RBMK_REFLECTOR", "NtmBlocks.RBMK_ABSORBER", "NtmBlocks.RBMK_MODERATOR", "NtmBlocks.PRIBRIS", "NtmBlocks.PRIBRIS_BURNING", "NtmBlocks.PRIBRIS_RADIATING"]}


def v6_registrations(ck, inp, st):
    nb = st.text(NB)
    ck("V6.blocks-once", all(count(nb, f'{BLOCK_CONST[n]} = register("{n}"') == 1 and count(nb, f'"{n}"') == 1 for n in BLOCKS9),
       "the nine blocks are registered exactly once each in NtmBlocks (name and constant)", [n for n in BLOCKS9 if count(nb, f'"{n}"') != 1])
    nbet = st.text(NBET)
    wb = whole(nbet)
    ck("V6.block-entities-once", all(count(nbet, f'BLOCK_ENTITY_TYPES.register("{n}"') == 1 and
                                     wb.count(f'{n.upper()}=BLOCK_ENTITY_TYPES.register("{n}",()->BlockEntityType.Builder.of({c}::new,NtmBlocks.{n.upper()}.get()).build(null));') == 1 for n, c in BE_CLASS.items()),
       "the four RBMK block entity types are registered once each, each for its class on its own block")
    net = st.text(NET)
    ck("V6.entity-once", count(net, 'ENTITY_TYPES.register("rbmk_debris"') == 1 and "EntityType.Builder.<RBMKDebris>of(RBMKDebris::new,MobCategory.MISC)" in whole(net) and "RBMK_DEBRIS=ENTITY_TYPES.register" in whole(net),
       "the rbmk_debris entity type is registered once (MobCategory.MISC)")
    ni = st.text(NI)
    ck("V6.items-once", all(count(ni, f'ITEMS.register("{n}"') == 1 for n in ITEMS3 + ["screwdriver", "screwdriver_desh", "meltdown_tool", "defuser"]),
       "debris_fuel, rbmk_lid, rbmk_lid_glass, both screwdrivers, meltdown_tool and defuser are registered once each in NtmItems")
    ct = st.text(CT)
    sec = tab_sections(ct)
    bad = {}
    for tab, entries in TAB_OF.items():
        for ent in entries:
            if count(sec.get(tab, ""), f"output.accept({ent});") != 1:
                bad[ent] = tab
    for ent in sum(TAB_OF.values(), []):
        if count(ct, f"output.accept({ent});") != 1:
            bad[ent] = bad.get(ent, "") + " (file-wide count != 1)"
    ck("V6.creative-tabs", not bad, "CONTROL carries debris_fuel, both lids, meltdown_tool and both screwdrivers, BLOCKS the deco blocks, MACHINE the four columns and the three debris blocks, each accepted once in the whole file", bad)
    deleted, inserted = diff_summary(inp.start[CT], ct)
    ck("V6.creative-diff", not deleted and sorted(inserted) == sorted(f"output.accept({e});" for e in ["NtmItems.DEBRIS_FUEL", "NtmItems.RBMK_LID", "NtmItems.RBMK_LID_GLASS", "NtmItems.SCREWDRIVER", "NtmItems.SCREWDRIVER_DESH"] + TAB_OF["BLOCKS"] + TAB_OF["MACHINE"]),
       "NtmCreativeTabs differs from its start copy by exactly the 14 new accept lines (meltdown_tool was already there)", (deleted, inserted))
    cp = st.text(CP)
    wc = whole(cp)
    ck("V6.client-proxy", all(wc.count(f"BlockEntityRenderers.register(NtmBlockEntityTypes.{n.upper()}.get(),newRenderRBMKLid<>());") == 1 for n in BE_CLASS)
       and wc.count("EntityRenderers.register(NtmEntityTypes.RBMK_DEBRIS.get(),RenderRBMKDebris::new);") == 1 and wc.count("RenderRBMKLid<>()") == 4,
       "ClientProxy registers RenderRBMKLid for the four RBMK block entity types and RenderRBMKDebris for the debris entity, once each")
    ck("V6.client-proxy-diff", diff_summary(inp.start[CP], cp)[0] == [] and len(diff_summary(inp.start[CP], cp)[1]) == 6, "ClientProxy differs from its start copy by exactly the six inserted lines (comment, four lid registrations, one entity renderer)", diff_summary(inp.start[CP], cp))
    rm = st.text(RM)
    wr = whole(rm)
    tex = {"RBMK_DEB_BASE_TEX": "textures/block/rbmk/rbmk_side.png", "RBMK_DEB_ELEMENT_TEX": "textures/block/rbmk/rbmk_fuel.png", "RBMK_DEB_CONTROL_TEX": "textures/block/rbmk/rbmk_control.png",
           "RBMK_DEB_BLANK_TEX": "textures/block/rbmk/rbmk_blank_side.png", "RBMK_DEB_LID_TEX": "textures/block/rbmk/rbmk_blank_cover_top.png"}
    obj = ["deb_blank", "deb_element", "deb_fuel", "deb_rod", "deb_lid"]
    ck("V6.resource-manager", all(wr.count(f'{k}=NuclearTechMod.withDefaultNamespace("{v}");') == 1 for k, v in tex.items())
       and all(wr.count(f'{n}=newHFRWavefrontObject("models/obj/projectiles/{n}.obj").asVBO();') == 1 and wr.count(f"publicstaticIModelCustom{n};") == 1 for n in obj)
       and wr.count('deb_graphite=newHFRWavefrontObject("models/obj/projectiles/deb_graphite.obj").asVBO();') == 1 and "deb_graphite" in whole(inp.start[RM]),
       "ResourceManager declares the five RBMK debris textures and the five debris OBJ models once each; deb_graphite was already there and is reused")
    rdel, rins = diff_summary(inp.start[RM], rm)
    ck("V6.resource-manager-diff", not rdel and len(rins) == 16, "ResourceManager differs from its start copy by insertions only (16 lines: comment, five textures, five model fields, five loads)", (rdel, len(rins)))
    geo = st.text(GEOM)
    wg = whole(geo)
    ck("V6.geometry", wg.count("ANVIL,RBMK_DEBRIS") == 1 and wg.count("caseRBMK_DEBRIS->newSimpleWavefrontBakedModel(newHFRWavefrontObject(\"models/obj/rbmk/debris.obj\"),textureSprite);") == 1,
       "NtmGeometry has one RBMK_DEBRIS constant and one case baking models/obj/rbmk/debris.obj", diff_summary(inp.start[GEOM], geo))
    # ---- client isolation
    refs = st.refs
    allowed = {"RenderRBMKLid": {CP, R_LID}, "RenderRBMKDebris": {CP, R_DEB}, "ResourceManagerRBMK": {R_DEB}}
    bad = {k: sorted(p for p, h in refs.items() if k in h and p not in allowed[k]) for k in allowed}
    ck("V6.client-refs", not any(bad.values()) and all(any(k in refs.get(p, {}) for p in allowed[k]) for k in allowed),
       "RenderRBMKLid and RenderRBMKDebris are referenced only from ClientProxy (and their own file); the RBMK ResourceManager fields only from RenderRBMKDebris", bad)
    deb = st.text(R_DEB)
    ck("V6.client-annotation", "@OnlyIn(Dist.CLIENT)\npublic class RenderRBMKDebris" in lf(deb), "RenderRBMKDebris is @OnlyIn(Dist.CLIENT)")
    leaks = {}
    for p in NEW_CLASSES:
        if p in (R_LID, R_DEB, BASE_BLK):
            continue
        if re.search(r"net\.minecraft\.client|com\.hbm\.render|com\.hbm\.main\.(ClientProxy|ResourceManager|NuclearTechModClient)|GuiGraphics|Minecraft\.getInstance", st.text(p)):
            leaks[p] = True
    ck("V6.no-client-leaks", not leaks, "no new common class (block entities, blocks, entity, items, dials) imports a client class; RBMKBaseBlock's client use is the @OnlyIn printHook (V4)", sorted(leaks))
    ck("V6.lid-renderer-registered-only-client", count(st.text(NMC), "RenderRBMKLid") == 0 and count(st.text(NB), "Render") == 0, "the lid renderer is not reachable from the common registries (NtmBlocks)")


# ---------------------------------------------------------------- V7

TRANSLATE = {"STEEL.plate()": ("tag", "c:plates/steel"), "ModBlocks.concrete_asbestos": ("item", "hbmsntm:concrete_asbestos"), "B.ingot()": ("item", "hbmsntm:ingot_boron"),
             "ModItems.neutron_reflector": ("item", "hbmsntm:neutron_reflector"), "ModBlocks.rbmk_blank": ("item", "hbmsntm:rbmk_blank"), "ModBlocks.deco_rbmk": ("item", "hbmsntm:deco_rbmk"),
             "ModBlocks.deco_rbmk_smooth": ("item", "hbmsntm:deco_rbmk_smooth")}
NEO_ID_OF_ROW = {752: "rbmk_lid", 757: "rbmk_absorber", 758: "rbmk_reflector", 788: "deco_rbmk", 789: "deco_rbmk_smooth", 790: "rbmk_blank_from_deco_rbmk", 791: "rbmk_blank_from_deco_rbmk_smooth"}


def v7_recipes(ck, inp, st):
    rows = parse_orig_craft(inp.o["craft"])
    bad = {}
    for number, rid in NEO_ID_OF_ROW.items():
        path = RECIPES + rid + ".json"
        if not st.has(path):
            bad[rid] = "missing"
            continue
        data = jload(st, path)
        out, cnt, pattern, keys = rows[number]
        want_keys = {k: {TRANSLATE[e][0]: TRANSLATE[e][1]} for k, e in keys.items()}
        got = (data.get("type"), data.get("pattern"), data.get("key"), data.get("result"))
        want = ("minecraft:crafting_shaped", pattern, want_keys, {"count": cnt, "id": "hbmsntm:" + out})
        if got != want:
            bad[rid] = (got, want)
    ck("V7.recipe-rows", not bad, "the seven generated crafting JSONs equal the original rows CraftingManager.java:752, :757-758 and :788-791: pattern, counts and ingredients (steel plate -> tag c:plates/steel, boron ingot, neutron reflector, concrete_asbestos, rbmk_blank, deco blocks)", bad)
    cats = {rid: jload(st, RECIPES + rid + ".json").get("category") for rid in RECIPE_IDS if st.has(RECIPES + rid + ".json")}
    ck("V7.recipe-categories", all(cats.get(r) == ("building" if r.startswith("deco_rbmk") else "misc") for r in RECIPE_IDS), "the deco recipes sit in the building category, the others in misc (RecipeCategory.BUILDING_BLOCKS / MISC)", cats)
    results = collections.Counter(v for v in st.recipe_ids.values() if v)
    ck("V7.no-moderator-glass", results.get("hbmsntm:rbmk_moderator", 0) == 0 and results.get("hbmsntm:rbmk_lid_glass", 0) == 0 and not st.has(RECIPES + "rbmk_moderator.json") and not st.has(RECIPES + "rbmk_lid_glass.json")
       and "RBMK_MODERATOR.get(),1)" not in whole(st.text(RP)) and "RBMK_LID_GLASS" not in st.text(RP),
       "no crafting recipe makes rbmk_moderator or rbmk_lid_glass (NEO has no block_graphite, glass_lead, glass_boron; original :753-754, :756 are skipped), neither as a generated file nor in NtmRecipeProvider", {k: v for k, v in results.items() if "rbmk" in k})
    ck("V7.rbmk-results", {k: n for k, n in results.items() if "rbmk" in k or "deco_rbmk" in k} == {"hbmsntm:rbmk_lid": 1, "hbmsntm:rbmk_absorber": 1, "hbmsntm:rbmk_reflector": 1, "hbmsntm:deco_rbmk": 1, "hbmsntm:deco_rbmk_smooth": 1, "hbmsntm:rbmk_blank": 2},
       "across all generated recipes exactly these RBMK results occur: lid, absorber, reflector, deco, smooth deco once each and rbmk_blank twice (from the two deco rings)", {k: n for k, n in results.items() if "rbmk" in k})
    miss = [rid for rid in RECIPE_IDS if not st.has((ADV_BUILD if rid.startswith("deco_rbmk") else ADV_MISC) + rid + ".json")
            or f"hbmsntm:{rid}" not in st.text((ADV_BUILD if rid.startswith("deco_rbmk") else ADV_MISC) + rid + ".json")]
    ck("V7.advancements", not miss and len(G_ADVANCEMENTS) == 7, "each recipe has its recipe advancement naming it", miss)
    rp = st.text(RP)
    ck("V7.provider", all(rp.count(f'ResourceLocation.fromNamespaceAndPath("hbmsntm", "{rid}")') == 1 for rid in RECIPE_IDS), "NtmRecipeProvider saves each of the seven recipes once")
    rdel, rins = diff_summary(inp.start[RP], rp)
    ck("V7.provider-diff", not rdel and len(rins) == 51, "NtmRecipeProvider differs from its start copy by insertions only (51 lines: the comment and the seven builders)", (rdel, len(rins)))
    # ---- ass.rbmk
    amr = st.text(AMR)
    ass = parse_orig_ass_rbmk(inp.o["asm"])
    chunk = lf(amr)[lf(amr).index('new GenericRecipe("ass.rbmk")'):]
    chunk = squash(blank_comments(chunk[:chunk.index(");\n") + 3]))
    want = (f'newGenericRecipe("ass.rbmk").setup({ass["setup"][0]},{ass["setup"][1]}).outputItems(newItemStack(NtmBlocks.RBMK_BLANK.get(),{ass["output"][1]}))'
            ".inputItems(newComparableStack(NtmBlocks.CONCRETE_ASBESTOS.get(),4),NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL,2),newComparableStack(NtmItems.PLATE_COPPER.get(),4),newComparableStack(NtmItems.INGOT_RUBBER.get(),2)));")
    ck("V7.ass-rbmk", chunk == want, "ass.rbmk (original AssemblyMachineRecipes.java:528-530): 100 tick / 100 HE, concrete_asbestos x4, steel cast plate x2, copper plate x4, rubber ingot x2 -> rbmk_blank; the expensive inputItemsEx branch and the 528 pools are not ported", chunk)
    ck("V7.ass-rbmk-once", count(amr, '"ass.rbmk"') == 1 and count(inp.start[AMR], '"ass.rbmk"') == 0, "ass.rbmk is registered once (absent at the start)")
    adel, ains = diff_summary(inp.start[AMR], amr)
    ck("V7.ass-others-unchanged", not adel and len(ains) == 7 and count(amr, 'new GenericRecipe("ass.') == count(inp.start[AMR], 'new GenericRecipe("ass.') + 1,
       "every other ass.* row is textually unchanged: AssemblyMachineRecipes differs from its start copy only by the 7 inserted lines of ass.rbmk and has exactly one more GenericRecipe(\"ass.", (adel, len(ains)))
    ck("V7.anvil-unchanged", st.text(ANVIL) == inp.start[ANVIL] and (not (START / ANVIL).exists() or st.files[ANVIL] == (START / ANVIL).read_bytes()),
       "AnvilRecipes.java is byte-equal to its start copy (no recycling row registered: tier-4 variants are unreachable; original :868-882)")
    ck("V7.anvil-no-rbmk", "RBMK" not in st.text(ANVIL).upper().replace("RBMKS", ""), "AnvilRecipes mentions no RBMK block")


# ---------------------------------------------------------------- V8

def v8_hazards(ck, inp, st):
    hr = st.text(HR)
    lines = [l.strip() for l in lf(hr).split("\n")]
    want = "HazardSystem.register(item(DEBRIS_FUEL), makeData().addEntry(RADIATION, 500F).addEntry(HOT, 5F)); // :283"
    ck("V8.debris-fuel", lines.count(want) == 1 and inp.o["haz"].split("\n")[282].strip() == "HazardSystem.register(debris_fuel, makeData().addEntry(RADIATION, 500F).addEntry(HOT, 5F));",
       "debris_fuel carries RADIATION 500 and HOT 5 exactly once (original HazardRegistry.java:283)", [l for l in lines if "DEBRIS_FUEL" in l])
    vanilla = ["HazardSystem.register(Items.GOLD_INGOT, makeData(BLINDING, 4F));", "HazardSystem.register(Items.BLAZE_POWDER, makeData(HOT, 4F));", "HazardSystem.register(Blocks.GREEN_WOOL, makeData(RADIATION, 150F));",
               "HazardSystem.register(Blocks.WHITE_WOOL, makeData(ASBESTOS, 5F));", "HazardSystem.register(Items.COAL, makeData(COAL, 1F));"]
    ck("V8.vanilla-rows-removed", not any(v in lines for v in vanilla) and all(v in [l.strip() for l in lf(inp.start[HR]).split("\n")] for v in vanilla),
       "the five NEO-only vanilla rows (gold ingot, blaze powder, green wool, white wool, coal) are absent now and were present at the start (user decision 2026-10-19)", [v for v in vanilla if v in lines])
    deleted, inserted = diff_summary(inp.start[HR], hr)
    code_deleted = [d for d in deleted if not d.startswith("//")]
    code_inserted = [i for i in inserted if not i.startswith("//")]
    ck("V8.diff-vs-start", code_deleted == vanilla and code_inserted == [want] and all(i.startswith("//") for i in inserted if i not in code_inserted),
       "HazardRegistry differs from its start copy only by the five removed rows, the debris_fuel row and comment lines", (code_deleted, code_inserted))


# ---------------------------------------------------------------- V9

def v9_closeout(ck, inp, st):
    ph = st.text(FT_PH)
    pdel, pins = diff_summary(inp.start[FT_PH], ph)
    ck("V9.pheromone-keys", pdel == ['info.add(ChatBuilder.start("[").nextTranslation("fluids.trait.glyphidPheromones").next("]").colorAll(ChatFormatting.AQUA).flush());',
                                     'info.add(ChatBuilder.start("[").nextTranslation("fluids.trait.modifiedPheromones").next("]").colorAll(ChatFormatting.BLUE).flush());']
       and pins == ['info.add(ChatBuilder.start("[").nextTranslation("hbmfluid.trait.glyphidPheromones").next("]").colorAll(ChatFormatting.AQUA).flush());',
                    'info.add(ChatBuilder.start("[").nextTranslation("hbmfluid.trait.modifiedPheromones").next("]").colorAll(ChatFormatting.BLUE).flush());']
       and 'I18nUtil.resolveKey("hbmfluid.trait.glyphidPheromones")' in inp.o["phero"] and 'I18nUtil.resolveKey("hbmfluid.trait.modifiedPheromones")' in inp.o["phero"],
       "FT_Pheromone only changes the two translation keys to hbmfluid.trait.glyphidPheromones / modifiedPheromones (original FT_Pheromone.java:29-31); colours and branch unchanged", (pdel, pins))
    ft = st.text(FT_TRAIT)
    names = re.findall(r'registerTrait\("(\w+)", (\w+)\.class\);', blank_comments(ft))
    snames = re.findall(r'registerTrait\("(\w+)", (\w+)\.class\);', blank_comments(inp.start[FT_TRAIT]))
    o_names = re.findall(r'registerTrait\("(\w+)", (\w+)\.class\);', blank_comments(inp.o["trait"]))
    fdel, fins = diff_summary(inp.start[FT_TRAIT], ft)
    ck("V9.fluidtrait-order", [n for n, _ in names][:6] == ["corrosive", "flammable", "combustible", "polluting", "heatable", "coolable"] == [n for n, _ in o_names][:6]
       and len({n for n, _ in names}) == len(names) and len({c for _, c in names}) == len(names) and len(names) == len(snames) - 2
       and fdel == ['registerTrait("heatable", FT_Heatable.class);', 'registerTrait("coolable", FT_Coolable.class);'] and not fins and snames[:6] == [("corrosive", "FT_Corrosive"), ("flammable", "FT_Flammable"), ("heatable", "FT_Heatable"), ("coolable", "FT_Coolable"), ("combustible", "FT_Combustible"), ("polluting", "FT_Polluting")],
       "FluidTrait: the first heatable/coolable pair (after flammable) is deleted, so corrosive, flammable, combustible, polluting, heatable, coolable come in the original order (FluidTrait.java:23-28), no name or class is registered twice", (names[:8], fdel))
    hr = st.text(HTR)
    hw = whole(hr)
    ck("V9.reacher-scan", "if(targetinstanceofPlayerplayer){for(ItemStackheld:player.getInventory().items){if(held.is(NtmItems.REACHER.get())){reacher=true;break;}}if(player.getOffhandItem().is(NtmItems.REACHER.get()))reacher=true;}" in hw
       and "contains(newItemStack" not in hw and "getInventory().armor" not in hw, "HazardTypeRadiation scans the 36 main slots and the offhand by item (original inventory.hasItem(reacher), HazardTypeRadiation); the old contains(new ItemStack) component comparison and the armor slots are gone")
    cu = st.text(CU)
    cdel, cins = diff_summary(inp.start[CU], cu)
    ck("V9.contamination-precedence", "if((player.isCreative()||player.isSpectator())&&type!=ContaminationType.NONE&&type!=ContaminationType.DIGAMMA_ROBE)return;" in whole(cu)
       and "if(player.capabilities.isCreativeMode && cont != ContaminationType.NONE && cont != ContaminationType.DIGAMMA2)" in inp.o["contam"] and len(cdel) == 1 and "player.isCreative() || player.isSpectator() && type" in cdel[0],
       "ContaminationUtil: the exemption is (creative || spectator) && type != NONE && type != DIGAMMA_ROBE (original ContaminationUtil.java:284: creative && != NONE && != DIGAMMA2); the old line only guarded the spectator", cdel)
    tt = st.text(TOOLTIP)
    ck("V9.hold-shift-hint", mcode(tt, "static Component holdShiftHint()") == 'returnComponent.translatable("desc.misc.holdShiftMoreInfo",Component.literal("LSHIFT").withStyle(ChatFormatting.YELLOW,ChatFormatting.ITALIC)).withStyle(ChatFormatting.DARK_GRAY,ChatFormatting.ITALIC);'
       and "tooltip.add(holdShiftHint());" in tt and '"Hold <"' not in tt, "ITooltipProvider.holdShiftHint(): desc.misc.holdShiftMoreInfo with a yellow italic LSHIFT argument inside dark gray italic text; addStandardInfo uses it and the hard-coded English is gone")
    ft2 = st.text(FLUIDTYPE)
    fdel2, fins2 = diff_summary(inp.start[FLUIDTYPE], ft2)
    ck("V9.fluidtype-hint", "info.add(ITooltipProvider.holdShiftHint());" in ft2 and '"Hold <"' not in ft2 and len(fins2) == 2 and "import com.hbm.blocks.ITooltipProvider;" in fins2 and len(fdel2) == 5,
       "FluidType.addInfo uses ITooltipProvider.holdShiftHint() (shift hint shown only while hidden traits exist and shift is not held); the hard-coded Hold <LSHIFT> text is gone", (fdel2, fins2))
    lp = st.text(LP)
    ldel, lins = diff_summary(inp.start[LP], lp)
    ck("V9.chloride-provider", ldel == ['this.add("hbmfluid.calcium_chloride", "Calciumchloride Solution");', 'this.add("hbmfluid.potassium_chloride", "Potassiumchloride Solution");']
       and 'this.add("hbmfluid.calcium_chloride", "Calcium chloride Solution");' in lins and 'this.add("hbmfluid.potassium_chloride", "Potassium chloride Solution");' in lins
       and lang_value(inp.o_en_lines, 1462, "hbmfluid.calcium_chloride") == "Calcium chloride Solution" and lang_value(inp.o_en_lines, 1561, "hbmfluid.potassium_chloride") == "Potassium chloride Solution",
       "NtmLanguageProvider: hbmfluid.calcium_chloride = \"Calcium chloride Solution\" and hbmfluid.potassium_chloride = \"Potassium chloride Solution\" (upstream en_US.lang:1462, :1561), replacing the two old spellings", ldel)
    m = jload(st, MAP)["entries"]
    bad = {}
    for key, ln_en, ln_zh, en in LANG_CHLORIDE:
        e = m.get(key, {})
        zh = lang_value(inp.o_zh_lines, ln_zh, key)
        if not (e.get("kind") == "upstream" and e.get("source_en") == en == e.get("target_en") and e.get("source_key") == key and e.get("source_zh") == zh == e.get("target_zh")):
            bad[key] = e
    v9_turbofan(ck, inp, st)
    ck("V9.chloride-map", not bad, "the two chloride map entries are upstream with source_en = target_en = the upstream HEAD value, Chinese unchanged", bad)


# ---------------------------------------------------------------- V10

def v10_screwdriver(ck, inp, st):
    ni = st.text(NI)
    nl = lf(ni).split("\n")
    sd = [l for l in nl if 'ITEMS.register("screwdriver"' in l]
    sdd = [l for l in nl if 'ITEMS.register("screwdriver_desh"' in l]
    ck("V10.registrations", len(sd) == 1 and len(sdd) == 1 and squash(sd[0]).endswith('ITEMS.register("screwdriver",()->newToolingItem(ToolType.SCREWDRIVER,newItem.Properties().durability(100)));')
       and squash(sdd[0]).endswith('ITEMS.register("screwdriver_desh",()->newToolingItem(ToolType.SCREWDRIVER,newItem.Properties()));'),
       "SCREWDRIVER = ToolingItem(SCREWDRIVER, durability(100)) and SCREWDRIVER_DESH = ToolingItem(SCREWDRIVER, Properties()) (original ModItems.java:3709-3710: durability 100 and 0)", (sd, sdd))
    defuser = [l for l in nl if 'ITEMS.register("defuser"' in l]
    start_def = [l for l in lf(inp.start[NI]).split("\n") if 'ITEMS.register("defuser"' in l]
    ck("V10.defuser-unchanged", defuser == start_def and len(defuser) == 1 and "ToolType.DEFUSER" in defuser[0] and "durability(100)" in defuser[0], "the DEFUSER registration line is unchanged from the start (it is now also a no-repair stack-1 tool through ToolingItem)", defuser)
    ti = st.text(TI)
    ck("V10.tooling-ctor", mcode(ti, "public ToolingItem(ToolType type, Properties properties)") == "super(properties.stacksTo(1).setNoRepair());this.type=type;type.register(newItemStack(this));",
       "ToolingItem constructor: stacksTo(1).setNoRepair() (original ItemCraftingDegradation.java:12-14), registers the tool type")
    ck("V10.tooling-use", mcode(ti, "public InteractionResult useOn(UseOnContext context)") == "Playerplayer=context.getPlayer();Levellevel=context.getLevel();BlockPosusedPos=context.getClickedPos();DirectionusedDirection=context.getClickedFace();"
       "if(player==null)returnInteractionResult.PASS;if(level.getBlockState(usedPos).getBlock()instanceofIToolabletoolableBlock&&toolableBlock.onScrew(level,player,usedPos,usedDirection,this.type)){"
       "if(this.getMaxDamage(newItemStack(this))>0){context.getItemInHand().hurtAndBreak(1,player,LivingEntity.getSlotForHand(context.getHand()));}returnInteractionResult.sidedSuccess(level.isClientSide);}returnInteractionResult.PASS;",
       "ToolingItem.useOn (original ItemTooling.java:30-40): the stack is damaged by one (slot of the used hand) and the click is consumed only when onScrew returns true, only when the tool has durability; otherwise PASS")
    lb = st.text(LB)
    ck("V10.lockable-pin", "if (stack.is(NtmItems.PIN.get()) && player.getInventory().contains(s -> s.is(NtmItems.SCREWDRIVER.get()) || s.is(NtmItems.SCREWDRIVER_DESH.get()))) {" in lf(lb)
       and "contains(new ItemStack(NtmItems.SCREWDRIVER" not in lb, "LockableBaseBlockEntity: picking with a pin requires either screwdriver by item identity (a worn screwdriver has a damage component, so the old contains(new ItemStack) comparison would miss it)")
    ldel, lins = diff_summary(inp.start[LB], lb)
    ck("V10.lockable-diff", len(ldel) == 1 and "NtmItems.SCREWDRIVER.get())" in ldel[0] and len(lins) == 3, "LockableBaseBlockEntity differs from its start copy by exactly the one pin condition (and two comment lines)", (ldel, lins))
    items = lf(inp.o["moditems"]).split("\n")
    ck("V10.original-values", 'new ItemTooling(ToolType.SCREWDRIVER, 100)' in items[3708] and 'new ItemTooling(ToolType.SCREWDRIVER, 0)' in items[3709], "the original registers the screwdriver with durability 100 and the desh screwdriver with 0 (ModItems.java:3709-3710)")
    tdel, tins = diff_summary(inp.start[TI], ti)
    ck("V10.tooling-diff", len(tdel) == 6 and len(tins) == 8, "ToolingItem differs from its start copy only in the constructor, the import and useOn", (tdel, tins))


# ---------------------------------------------------------------- V11

def add_line(key, en):
    if key.startswith("block.hbmsntm."):
        return f'this.add(NtmBlocks.{key.split(".")[-1].upper()}, "{en}");'
    if key.startswith("item.hbmsntm."):
        return f'this.add(NtmItems.{key.split(".")[-1].upper()}, "{en}");'
    return f'this.add("{key}", "{en}");'


def v11_language(ck, inp, st):
    expected_en = {k: en for k, _, _, _, en, _ in LANG13}
    expected_en.update({LANG_ENTITY[0]: LANG_ENTITY[1], LANG_HOLD[0]: LANG_HOLD[1]})
    expected_en.update({k: en for k, _, _, _, en, _ in LANG_PHERO})
    expected_zh = {k: zh for k, _, _, _, _, zh in LANG13}
    expected_zh.update({LANG_ENTITY[0]: LANG_ENTITY[2], LANG_HOLD[0]: LANG_HOLD[2]})
    expected_zh.update({k: zh for k, _, _, _, _, zh in LANG_PHERO})
    ck("V11.expected-17", len(expected_en) == 17 and sorted(expected_en) == sorted(KEYS17), "17 keys are expected: 13 upstream RBMK keys, entity.hbmsntm.rbmk_debris, the two pheromone keys and desc.misc.holdShiftMoreInfo")
    lp = lf(st.text(LP))
    lines = [add_line(k, en) for k, en in expected_en.items()]
    lines += [add_line("hbmfluid.calcium_chloride", "Calcium chloride Solution"), add_line("hbmfluid.potassium_chloride", "Potassium chloride Solution")]
    ck("V11.provider", all(lp.count(l) == 1 for l in lines), "NtmLanguageProvider adds the 17 keys and the two changed chloride names once each", [l for l in lines if lp.count(l) != 1])
    ldel, lins = diff_summary(inp.start[LP], st.text(LP))
    code_ins = sorted(x for x in lins if not x.startswith("//"))
    ck("V11.provider-diff", sorted(lines) == code_ins and len(ldel) == 2, "the provider differs from its start copy by exactly these 19 added lines (plus comments) and the 2 replaced chloride lines", (len(code_ins), ldel))
    en_text = st.text(EN)
    en, en_dups = json_pairs(en_text)
    en0, _ = json_pairs(inp.start[EN])
    zh_text = st.text(ZH)
    zh, zh_dups = json_pairs(zh_text)
    zh0, _ = json_pairs(inp.start[ZH])
    ck("V11.en-values", not en_dups and all(en.get(k) == v for k, v in expected_en.items()) and en.get("hbmfluid.calcium_chloride") == "Calcium chloride Solution" and en.get("hbmfluid.potassium_chloride") == "Potassium chloride Solution",
       "generated en_us.json has the 17 keys with the provider values and the two corrected chloride names, and no duplicate key",
       [(k, en.get(k)) for k, v in expected_en.items() if en.get(k) != v])
    gen_changed = sorted(k for k in set(en) | set(en0) if en.get(k) != en0.get(k))
    ck("V11.en-only-these", gen_changed == sorted(KEYS17 + ["hbmfluid.calcium_chloride", "hbmfluid.potassium_chloride"]) and len(en) == len(en0) + 17,
       "en_us.json changed only in the 17 new keys and the two chloride values relative to the start (generated by runData from the provider)", gen_changed[:30])
    zh_changed = sorted(k for k in set(zh) | set(zh0) if zh.get(k) != zh0.get(k))
    ck("V11.zh-values", not zh_dups and all(zh.get(k) == v for k, v in expected_zh.items()) and zh_changed == sorted(KEYS17) and len(zh) == len(zh0) + 17,
       "zh_cn.json has the 17 keys (13 upstream RBMK and 2 pheromone strings verbatim from zh_CN.lang, entity and hold-shift local) and changed in nothing else", zh_changed[:30])
    ck("V11.zh-verbatim", all(zh.get(k) == lang_value(inp.o_zh_lines, ln, ok) for k, ok, _, ln, _, _ in [(a, b, c, d, e, f) for a, b, c, d, e, f in LANG13 + LANG_PHERO]),
       "the 15 upstream Chinese values equal the zh_CN.lang lines of the original byte for byte")
    ck("V11.zh-keys-have-english", all(k in en for k in zh if k in KEYS17), "every new Chinese key has an English counterpart")
    ck("V11.placeholders", expected_en[LANG_HOLD[0]].count("%s") == 1 == zh[LANG_HOLD[0]].count("%s") and "<%s>" in zh[LANG_HOLD[0]], "the hold-shift line keeps one %s placeholder in English and Chinese")
    ck("V11.crlf", zh_text.count("\r\n") == zh_text.count("\n") > 0 and inp.start[ZH].count("\r\n") == inp.start[ZH].count("\n") and "\r\n" not in en_text and format_ok(zh_text, zh) and en_text == json.dumps(en, indent=2, ensure_ascii=False) and format_ok(st.text(MAP), json.loads(st.text(MAP)))
       and st.text(MAP).count("\r\n") == st.text(MAP).count("\n") > 0 and st.text(LP).count("\r\n") == st.text(LP).count("\n") > 0,
       "zh_cn.json, the mapping and the provider keep CRLF on every line (counted on the bytes), en_us.json stays LF, and both language files keep the standard JSON layout", (zh_text.count("\r\n"), zh_text.count("\n")))
    mp = jload(st, MAP)
    mp0 = json.loads(inp.start[MAP])
    entries, entries0 = mp["entries"], mp0["entries"]
    bad = {}
    for nkey, okey, ln_en, ln_zh, en_v, zh_v in LANG13 + LANG_PHERO:
        e = entries.get(nkey)
        want = {"kind": "upstream", "source_en": lang_value(inp.o_en_lines, ln_en, okey), "source_key": okey, "source_zh": lang_value(inp.o_zh_lines, ln_zh, okey), "target_en": en_v, "target_zh": zh_v}
        if e != want:
            bad[nkey] = (e, want)
    ck("V11.map-upstream", not bad, "the 15 upstream map entries (13 RBMK + 2 pheromone) carry the upstream key, upstream English/Chinese verbatim and the current NEO English/Chinese", bad)
    local_bad = {}
    for key, en_v, zh_v in ((LANG_ENTITY[0], LANG_ENTITY[1], LANG_ENTITY[2]), (LANG_HOLD[0], LANG_HOLD[1], LANG_HOLD[2])):
        e = entries.get(key, {})
        if not (e.get("kind") == "local" and e.get("target_en") == en_v and e.get("target_zh") == zh_v and e.get("reason") and "source_key" not in e):
            local_bad[key] = e
    ck("V11.map-local", not local_bad, "entity.hbmsntm.rbmk_debris and desc.misc.holdShiftMoreInfo are local entries with a reason and the current English/Chinese", local_bad)
    changed = sorted(k for k in set(entries) | set(entries0) if entries.get(k) != entries0.get(k))
    ck("V11.map-only-these", changed == sorted(KEYS17 + ["hbmfluid.calcium_chloride", "hbmfluid.potassium_chloride"]) and mp["source_commit"] == mp0["source_commit"] and mp["schema_version"] == mp0["schema_version"],
       "the mapping changed only in the 17 new entries and the two chloride entries; source_commit and schema_version are unchanged", changed[:30])
    kinds = collections.Counter(e["kind"] for e in entries.values())
    kinds0 = collections.Counter(e["kind"] for e in entries0.values())
    ck("V11.map-counts", kinds["upstream"] - kinds0["upstream"] == 15 and kinds["local"] - kinds0["local"] == 2 and kinds["deferred"] == kinds0["deferred"] and len(entries) == len(entries0) + 17,
       "the mapping gained 15 upstream and 2 local entries and no deferred entry (deferred stays as at the start)", (dict(kinds), dict(kinds0)))
    ck("V11.map-matches-files", all(entries[k].get("target_en") == en.get(k) and entries[k].get("target_zh") == zh.get(k) for k in KEYS17), "for the 17 keys, the mapping's target English/Chinese equal the generated en_us.json and zh_cn.json values")
    ck("V11.counts", True, f"entries: en_us.json {len(en)}, zh_cn.json {len(zh)}, mapping {len(entries)} (upstream {kinds['upstream']}, local {kinds['local']}, deferred {kinds['deferred']}); start: en {len(en0)}, zh {len(zh0)}, mapping {len(entries0)}")


# ---------------------------------------------------------------- V9 (turbofan, the 24A-1 adaptation)

def v9_turbofan(ck, inp, st):
    t = st.text(TURBO)
    s = inp.start[TURBO]
    o = inp.o["turbo"]
    live = mcode(t, "@Override public void updateEntity()")
    ck("V9.turbofan-redstone-loop", "this.redstonePowered=false;for(DirPospos:getPortProxies(this.worldPosition,this.getBlockState().getValue(DummyableBlock.FACING))){"
       "if(this.level.hasChunkAt(pos.makeCompat())&&this.level.hasNeighborSignal(pos.makeCompat())){this.redstonePowered=true;break;}}this.generate(this.redstonePowered);" in live,
       "MachineTurbofanBlockEntity.updateEntity: the loop that sets redstonePowered = true iterates getPortProxies(worldPosition, FACING), the port cells themselves (upstream aee05a40f TileEntityMachineTurbofan getConPos, used at :193-195 for isBlockIndirectlyGettingPowered)")
    ck("V9.turbofan-pipe-loop", "for(DirPospos:this.getConPos()){if(!this.level.hasChunkAt(pos.makeCompat()))continue;this.trySubscribe(previousType,this.level,pos);this.tryProvide(this.blood,this.level,pos);this.tryProvide(this.level,pos.makeCompat(),pos.getDir());}" in live,
       "the fluid and power loop (trySubscribe, tryProvide) still iterates this.getConPos(), the connection cells one block further out")
    ck("V9.turbofan-bodies-unchanged", mcode(t, "public static DirPos[] getPortProxies(BlockPos core, Direction facing)") == mcode(s, "public static DirPos[] getPortProxies(BlockPos core, Direction facing)")
       and mcode(t, "public DirPos[] getConPos()") == mcode(s, "public DirPos[] getConPos()") and mcode(t, "public static Direction getIntakeDirection(Direction facing)") == mcode(s, "public static Direction getIntakeDirection(Direction facing)"),
       "getPortProxies, getConPos and getIntakeDirection are byte-for-byte (whitespace-insensitive) equal to their bodies in git show 1114adf5:MachineTurbofanBlockEntity.java (the file is not in baseline-files)")
    pp = mcode(t, "public static DirPos[] getPortProxies(BlockPos core, Direction facing)")
    cp = mcode(t, "public DirPos[] getConPos()")
    ck("V9.turbofan-one-block", "newDirPos(core.relative(facing),facing)" in pp and "newDirPos(core.relative(facing.getOpposite()),facing.getOpposite())" in pp and "relative(proxies[i].getDir())" in cp,
       "NEO's port cells lie one block from the core (core +- facing, and the second cell one further along the intake axis) while getConPos adds one block along each port direction, like the original's old 2-block and new 1-block offsets")
    oc = mcode(o, "protected DirPos[] getConPos()")
    ow = whole(o)
    ck("V9.turbofan-original", "newDirPos(this.xCoord+rot.offsetX,this.yCoord,this.zCoord+rot.offsetZ,rot)" in oc and "this.xCoord-rot.offsetX-dir.offsetX" in oc and "offsetX*2" not in oc
       and "for(DirPospos:getConPos()){if(!Compat.isPositionLoaded(worldObj,pos.getX(),pos.getZ()))continue;if(this.worldObj.isBlockIndirectlyGettingPowered(pos.getX(),pos.getY(),pos.getZ())){redstone=true;break;}}" in ow,
       "original at aee05a40f: getConPos uses 1-block offsets (+-rot, +-rot - dir; the old HEAD used rot * 2) and is used for the isBlockIndirectlyGettingPowered probe (:193-195)")
    tdel, tins = diff_summary(s, t)
    ck("V9.turbofan-diff", tdel == ["for(DirPos pos : this.getConPos()) {"] and len(tins) == 2 and tins[1] == "for(DirPos pos : getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING))) {" and tins[0].startswith("// Upstream aee05a40f"),
       "MachineTurbofanBlockEntity differs from its start by exactly the redstone loop header (one line replaced) and one comment line", (tdel, tins))
    classify = jload(st, CLASSIFY) if st.has(CLASSIFY) else {}
    entry = [e for e in classify.get("entries", []) if e.get("path", "").endswith("TileEntityMachineTurbofan.java")]
    ck("V9.turbofan-classified", len(entry) == 1 and entry[0].get("category") == "neo-adapt-24a" and "MachineTurbofanBlockEntity.java" in entry[0].get("neo_counterpart", ""), "the classification entry of TileEntityMachineTurbofan.java is neo-adapt-24a and names MachineTurbofanBlockEntity", entry)


# ---------------------------------------------------------------- V12

def v12_resources(ck, inp, st):
    own = jload(st, OWN)
    assets = own["assets"]
    kinds = collections.Counter(a["target_path"].rsplit(".", 1)[-1] for a in assets)
    ck("V12.count", len(assets) == 40 and kinds == {"png": 34, "obj": 6} and own.get("batch") == "Goal24A" and own.get("source_commit") == ORIGINAL_HEAD,
       "the ownership record lists 40 assets (34 PNG, 6 OBJ) of batch Goal24A read from the original at aee05a40f", (len(assets), dict(kinds)))
    bad, bad_sha, bad_path, bad_png, bad_new = [], [], [], [], []
    for a in assets:
        t, s = a["target_path"], a["source_path"]
        data = st.files.get(t)
        orig = inp.o_res.get(t)
        if data is None or orig is None or data != orig:
            bad.append(t)
            continue
        if not (sha(data) == a["target_sha256"] == a["source_sha256"] and a["bytes"] == len(data)):
            bad_sha.append(t)
        if not (t == t.lower() and t.startswith(RES) and s.startswith(O_RES_DIR)):
            bad_path.append(t)
        if t.endswith(".png") and list(png_size(data) or ()) != a.get("png_size"):
            bad_png.append(t)
        if t in inp.base_files:
            bad_new.append(t)
    ck("V12.bytes-equal-original", not bad, "each of the 40 NEO files is byte-equal to the original working-tree file named by source_path", bad)
    ck("V12.record-matches", not bad_sha and not bad_path and not bad_png, "each record entry's source/target sha256 and byte count equal the file, paths are lowercase under assets/hbmsntm, PNG sizes match the header", (bad_sha, bad_path, bad_png))
    ck("V12.all-new", not bad_new and len({a["target_path"] for a in assets}) == 40, "the 40 target files did not exist at the start and are listed once each", bad_new)
    obj_bad = [t for t, blob in inp.o_blob.items() if lf(blob.decode("utf-8", errors="replace")) != lf(st.files[t].decode("utf-8", errors="replace")) or t not in st.files]
    ck("V12.obj-git-blob", len(inp.o_blob) == 6 and not obj_bad, "the six OBJ files equal the git blob of HEAD (git show HEAD:<source>) after line-ending normalization", obj_bad)
    reused_bad = []
    for neo, orig_path in ((RES + "models/obj/projectiles/deb_graphite.obj", O_RES_DIR + "models/projectiles/deb_graphite.obj"), (RES + "textures/block/block_graphite.png", O_RES_DIR + "textures/blocks/block_graphite.png")):
        same = (lambda x, y: lf(x.decode("utf-8")) == lf(y.decode("utf-8"))) if neo.endswith(".obj") else (lambda x, y: x == y)  # the OBJ blob is stored LF-normalized
        if not (neo in st.files and st.files[neo] == (ORIGINAL / orig_path).read_bytes() and same(st.files[neo], inp.reused_start.get(neo, b""))):
            reused_bad.append(neo)
    ck("V12.reused-unchanged", not reused_bad, "deb_graphite.obj and block_graphite.png are reused: byte-equal to the original working file and to the start commit's file (the OBJ blob compared after line-ending normalization), not re-imported, not changed", reused_bad)
    listed = {a["target_path"] for a in assets}
    new_res = sorted(p for p in st.tree if p.startswith("src/main/resources/") and p not in inp.base_files)
    ck("V12.no-unlisted-resource", sorted(set(new_res) - listed) == [], "every new file under src/main/resources is one of the 40 recorded assets", sorted(set(new_res) - listed))


# ---------------------------------------------------------------- V13

def v13_classification(ck, inp, st):
    c = jload(st, CLASSIFY)
    ns = [l.split("\t") for l in inp.name_status if l.strip()]
    paths = {p: k for k, p in ((x[0], x[-1]) for x in ns)}
    entries = c["entries"]
    got = {e["path"]: e["change"] for e in entries}
    kind = {"M": "modified", "A": "added", "D": "deleted"}
    ck("V13.paths", len(paths) == 26 and sorted(got) == sorted(paths) and len(entries) == 26,
       "the classification lists exactly the 26 paths of `git diff --name-status -M 6a11998d aee05a40f`", (len(paths), len(got), sorted(set(paths) ^ set(got))))
    ck("V13.kinds", all(got.get(p) == kind[k[0]] for p, k in paths.items()), "each entry's change kind matches the name-status letter (M -> modified, A -> added)", {p: (got.get(p), k) for p, k in paths.items() if got.get(p) != kind[k[0]]})
    cats = collections.Counter(e["category"] for e in entries)
    ck("V13.summary", dict(cats) == c.get("summary") and sum(cats.values()) == 26, "the summary equals the category counts of the entries (computed, not hard-coded)", (dict(cats), c.get("summary")))
    ck("V13.commits", c.get("baseline_source_commit") == OLD_HEAD and c.get("reviewed_source_commit") == ORIGINAL_HEAD and c.get("neo_commit") == START_COMMIT, "the record names the baseline 6a11998d, the reviewed original aee05a40f and the NEO start 1114adf5")
    known = set(c.get("new_categories", {})) | {"not-applicable-content", "not-migrated-other", "network-architecture", "neo-counterpart-equivalent", "neo-counterpart-deferred"}
    ck("V13.categories-known", all(e["category"] in known for e in entries) and all(e.get("decision") and e.get("evidence") or e.get("decision") for e in entries),
       "every entry has a decision and a category that is declared (new_categories) or one of the established ones", sorted({e["category"] for e in entries} - known))
    adapt = sorted(e["path"] for e in entries if e["category"] == "neo-adapt-24a")
    ck("V13.adapt-entries", any(p.endswith("TileEntityMachineTurbofan.java") for p in adapt) and any(p.endswith("en_US.lang") for p in adapt) and len(adapt) == c["summary"].get("neo-adapt-24a"),
       "the neo-adapt-24a entries are the en_US lang file (two chloride names) and TileEntityMachineTurbofan (redstone probe)", adapt)


# ---------------------------------------------------------------- V14

ALLOWED_MIGRATION = ("migration/goal24a-", "migration/GOAL24")
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md"}


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v14_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    own_assets = jload(st, OWN)["assets"]
    expected = set(NEW_CLASSES + EDITED + [RCGT, HGT, ZH, MAP, EN, LP] + [a["target_path"] for a in own_assets] + GENERATED)
    extra = [p for p in changed if p not in expected and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V14.no-extra-paths", not extra, "every changed src/ and migration/ path since the start belongs to the batch (new classes, edited production files incl. MachineTurbofanBlockEntity, language files, the 40 resources, the two GameTest files, the generated files, migration/goal24a-* and GOAL24* records and the allowed migration records)", extra)
    ck("V14.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone)
    never = [p for p in expected if p not in changed]
    ck("V14.expected-all-changed", not never, "every expected production, resource and generated path really differs from the start (nothing listed but untouched)", never)
    ck("V14.counts", len(NEW_CLASSES) == 17 and len(EDITED) == 28 and len(set(GENERATED)) == 56 and len(own_assets) == 40, "17 new production classes, 28 edited production files, 56 generated paths (stamp, en_us, tag, 9+9+12+9, 7+7), 40 resources",
       (len(NEW_CLASSES), len(EDITED), len(set(GENERATED)), len(own_assets)))
    ck("V14.new-classes-new", all(p not in inp.base_files for p in NEW_CLASSES + [RCGT]), "the 17 new classes and RBMKCoreGameTests did not exist at the start")
    rest = sorted(p for p in changed if p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT)
    ck("V14.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V14.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V15 / V16 / V17

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def v15_gametests(ck, inp, st):
    live = st.text(RCGT)
    code = blank_comments(lf(live))
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V15.rbmk-tests", sorted(tests) == sorted(GT_TESTS) and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "RBMKCoreGameTests has its @GameTest methods, each public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    missing_name = []
    for name in tests:
        try:
            body = method_code(live, f"void {name}(GameTestHelper helper)")
        except ValueError:
            missing_name.append(name)
            continue
        if f'"{name}"' not in body:
            missing_name.append(name)
    ck("V15.rbmk-report-their-name", not missing_name, "every test method passes its own name to the `[hbm-rbmk-core] <name> passed` helper", missing_name)
    marker = squash(f'LOGGER.info("{GT_MARK} {{}} passed", name);')
    ck("V15.rbmk-marker", marker in mcode(live, "private static Runnable passed(String name)") and marker in mcode(live, "private static void done(GameTestHelper helper, String name)"),
       f"both helpers (passed, done) log `{GT_MARK} <name> passed` through LOGGER")
    ck("V15.rbmk-eol", "\r" not in live, "RBMKCoreGameTests.java has LF line endings")
    ck("V15.rbmk-no-client", not re.search(r"\bRenderRBMK\w*\b|\bResourceManager\b|net\.minecraft\.client", code), "RBMKCoreGameTests references no renderer, ResourceManager or client class")
    hs, hl = blank_comments(lf(inp.start[HGT])), blank_comments(lf(st.text(HGT)))
    sn = [n for _, n in TEST_ANNOTATED.findall(hs)]
    ln = [n for _, n in TEST_ANNOTATED.findall(hl)]
    new = [n for n in ln if n not in sn]
    deleted, inserted = diff_summary(inp.start[HGT], st.text(HGT))
    ck("V15.hazard-kept-tests", all(n in ln for n in sn) and len(sn) == 15, "HazardGameTests keeps all 15 start tests", [n for n in sn if n not in ln])
    ck("V15.hazard-new-tests", len(new) >= 1 and set(new) == {"hazard_radiation_reacher_by_item", "hazard_contaminate_creative_types", "hazard_removed_vanilla_rows"},
       "HazardGameTests adds the tests " + ", ".join(new), new)
    ck("V15.hazard-deleted-lines", deleted == ['checkExact("gold_ingot", new ItemStack(Items.GOLD_INGOT), HazardRegistry.BLINDING, 4F);', 'checkExact("blaze_powder", new ItemStack(Items.BLAZE_POWDER), HazardRegistry.HOT, 4F);',
                                               'checkExact("coal", new ItemStack(Items.COAL), HazardRegistry.COAL, 1F);', 'sample(n, "green wool", new ItemStack(Items.GREEN_WOOL), HazardRegistry.RADIATION, 150F);',
                                               'sample(n, "white wool", new ItemStack(Items.WHITE_WOOL), HazardRegistry.ASBESTOS, 5F);', 'sample(n, "blaze powder", new ItemStack(Items.BLAZE_POWDER), HazardRegistry.HOT, 4F);'],
       "HazardGameTests differs from its start copy only by the six replaced vanilla samples (gold ingot, blaze powder, coal, green wool, white wool, blaze powder) and added tests, imports and comments", deleted)
    ck("V15.hazard-eol", eol_of(st.text(HGT)) == eol_of(inp.start[HGT]), "HazardGameTests keeps its start line endings")
    ck("V15.start-total", inp.gametest_other + len(sn) == START_GAMETESTS, "the other GameTest classes plus HazardGameTests at the start hold the 122 pre-batch tests", (inp.gametest_other, len(sn)))
    return dict(rbmk_tests=sorted(tests), hazard_new_tests=new, hazard_start_tests=len(sn), other_tests=inp.gametest_other)


def v16_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(RCGT))
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    hs, hl = blank_comments(lf(inp.start[HGT])), blank_comments(lf(st.text(HGT)))
    new_h = [n for _, n in TEST_ANNOTATED.findall(hl) if n not in [m for _, m in TEST_ANNOTATED.findall(hs)]]
    total = START_GAMETESTS + len(tests) + len(new_h)
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V16.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({START_GAMETESTS} + {len(tests)} RBMKCoreGameTests + {len(new_h)} new HazardGameTests)", (match and match[0], total))
    live_total = gametest_total([live, st.text(HGT)]) + inp.gametest_other
    ck("V16.annotation-total", live_total == total, "the live @GameTest( total equals 122 + new tests", (live_total, total))
    ck("V16.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V16.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    for name in new_h:
        ck(f"V16.log-{name}", f"[hbm-hazard] {name} passed" in text, f"the log has `[hbm-hazard] {name} passed`")
    ck("V16.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()))


def inner_expected(text):
    code = blank_comments(lf(text))
    anon = len(re.findall(r"new\s+[A-Z][\w.<>]*\s*\([^();{}]*\)\s*\{", code))
    nested = len(re.findall(r"^[ \t]{4,}(?:(?:public|private|protected|static|final|abstract)\s+)*(?:class|record|enum|interface)\s+\w+", code, re.M))
    return anon + nested


def v17_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + [RCGT]}
    live_en, _ = json_pairs(st.text(EN))
    live_zh, _ = json_pairs(st.text(ZH))
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        inner = {c: sorted(n for n in names if n.startswith(c + "$") and n.endswith(".class")) for c in classes}
        short = {c: (len(inner[c]), inner_expected(st.text(p))) for c, p in classes.items() if len(inner[c]) < inner_expected(st.text(p))}
        ck("V17.classes", not missing, "the JAR has the 17 new classes and RBMKCoreGameTests", missing)
        ck("V17.inner-classes", not short, "the JAR has at least as many inner/anonymous classes as the sources declare", short)
        bad = [a["target_path"] for a in jload(st, OWN)["assets"] if a["target_path"][len("src/main/resources/"):] not in names or jar.read(a["target_path"][len("src/main/resources/"):]) != st.files.get(a["target_path"])]
        ck("V17.resources", not bad, "the 40 imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in GENERATED if p != STAMP and (p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p))]
        ck("V17.generated", not gbad, "the generated blockstates, models, loot tables, pickaxe tag, en_us.json, recipes and advancements in the JAR are byte-equal to the live files", gbad)
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V17.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in KEYS17 + ["hbmfluid.calcium_chloride", "hbmfluid.potassium_chloride"] if data.get(k) != source.get(k) or k not in data}
            ck(f"V17.{Path(entry).name}", not bad, f"{entry} in the JAR carries the 17 new keys (and the two chloride names) with the values of the source file", bad)
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st, facts)
    guarded(ck, "V2", v2_config, inp, st)
    guarded(ck, "V3", v3_block_entity, inp, st)
    guarded(ck, "V4", v4_blocks, inp, st)
    guarded(ck, "V5", v5_entity, inp, st)
    guarded(ck, "V6", v6_registrations, inp, st)
    guarded(ck, "V7", v7_recipes, inp, st)
    guarded(ck, "V8", v8_hazards, inp, st)
    guarded(ck, "V9", v9_closeout, inp, st)
    guarded(ck, "V10", v10_screwdriver, inp, st)
    guarded(ck, "V11", v11_language, inp, st)
    guarded(ck, "V12", v12_resources, inp, st)
    guarded(ck, "V13", v13_classification, inp, st)
    guarded(ck, "V14", v14_scope, inp, st)
    result = guarded(ck, "V15", v15_gametests, inp, st)
    if facts is not None and result:
        facts["V15"] = result
    return ck


def T(path, fn):
    """Apply fn to the LF-normalized text and keep the file's line-ending style."""
    def apply(st):
        text = st.text(path)
        eol = "\r\n" if "\r\n" in text else "\n"
        st.set_text(path, fn(lf(text)).replace("\n", eol))
    return apply


def Bx(path, fn):
    return lambda st: st.set_bytes(path, fn(st.files[path]))


def D(path):
    return lambda st: st.delete(path)


def touch(path):
    return lambda st: st.tree.__setitem__(path, "0" * 64)


def flip_byte(data):
    out = bytearray(data)
    out[len(out) // 2] ^= 0x01
    return bytes(out)


def zh_set(key, value):
    return lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__(key, value)))


def map_set(key, field, value):
    return lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"][key].__setitem__(field, value)))


def dup_line(text, needle):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    lines.insert(hits[0] + 1, lines[hits[0]])
    return "\n".join(lines)


def insert_after(text, needle, new_line):
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    lines.insert(hits[0] + 1, new_line)
    return "\n".join(lines)


def recipe_edit(rid, edit):
    return lambda st: st.set_text(RECIPES + rid + ".json", json_edit(st.text(RECIPES + rid + ".json"), edit))


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None, check ids that must pass in the unmutated tree)."""
    cc = lambda old, new: T(CC, lambda t: rep1(t, old, new))  # noqa: E731
    be = lambda old, new: T(BASE_BE, lambda t: rep1(t, old, new))  # noqa: E731
    return [
        # V2 config and facade
        ("dial_default_2_5_to_2_0", "V2.", cc('defineInRange("dialPassiveCooling", 2.5D, 0D', 'defineInRange("dialPassiveCooling", 2.0D, 0D'), None, ()),
        ("dial_range_flow_to_2", "V2.", cc('defineInRange("dialColumnHeatFlow", 0.2D, 0D, 1D)', 'defineInRange("dialColumnHeatFlow", 0.2D, 0D, 2D)'), None, ()),
        ("dial_height_range_16_to_15", "V2.", cc('defineInRange("dialColumnHeight", 4, 2, 16)', 'defineInRange("dialColumnHeight", 4, 2, 15)'), None, ()),
        ("dial_flux_default_5_to_6", "V2.", cc('defineInRange("dialFluxRange", 5, 1, 100)', 'defineInRange("dialFluxRange", 6, 1, 100)'), None, ()),
        ("meteor_duplicate_key_restored", "V2.", cc('defineInRange("meteorShowerChance", 18000', 'defineInRange("meteorStrikeChance", 18000'), None, ()),
        ("dial_key_duplicated", "V2.", cc('define("dialDisableXenon", false)', 'define("dialDisableDepletion", false)'), None, ()),
        ("dial_translation_wrong", "V2.", cc('.translation("hbmsntm.configuration.dialFluxRange")', '.translation("hbmsntm.configuration.dialFluxRange2")'), None, ()),
        ("rbmk_section_pop_removed", "V2.", cc("        builder.pop();\n\n        /// HAZARDS ///", "\n        /// HAZARDS ///"), None, ()),
        ("rbmk_section_before_rtg", "V2.", cc('builder.push("rbmk");', 'builder.push("rtg");'), None, ()),
        ("facade_height_not_minus_one", "V2.", T(DIALS, lambda t: rep1(t, "DIAL_COLUMN_HEIGHT.get() - 1", "DIAL_COLUMN_HEIGHT.get()")), None, ()),
        ("facade_depletion_not_negated", "V2.", T(DIALS, lambda t: rep1(t, "!NtmConfig.COMMON.DIAL_DISABLE_DEPLETION.get()", "NtmConfig.COMMON.DIAL_DISABLE_DEPLETION.get()")), None, ()),
        ("facade_wrong_field", "V2.", T(DIALS, lambda t: rep1(t, "return NtmConfig.COMMON.DIAL_FLUX_RANGE.get();", "return NtmConfig.COMMON.DIAL_PASSIVE_COOLING.get().intValue();")), None, ()),
        # V3 block entity
        ("maxheat_1500_to_1000", "V3.", be("return 1500D;", "return 1000D;"), None, ()),
        ("heat_floor_20_to_0", "V3.", be("if(heat < 20) heat = 20D;", "if(heat < 0) heat = 0D;"), None, ()),
        ("tracking_range_15_to_16", "V3.", be("return 15;", "return 16;"), None, ()),
        ("passive_cooling_clamp", "V3.", be("Mth.clamp(neighbors, 0, 4)", "Mth.clamp(neighbors, 0, 5)"), None, ()),
        ("neighbour_order_swapped", "V3.", T(BASE_BE, lambda t: swap_lines(t, "Direction.EAST,", "Direction.SOUTH,")), None, ()),
        ("heat_step_0_1", "V3.", be("double stepSize = RBMKDials.getColumnHeatFlow();", "double stepSize = 0.1D;"), None, ()),
        ("setchanged_always", "V3.", be("        if(members > 1) {", "        if(members > 0) {"), None, ()),
        ("cool_passively_neighbours", "V3.", be("coolPassively(members - 1);", "coolPassively(members);"), None, ()),
        ("move_heat_ignores_loaded", "V3.", be("if(this.level.isLoaded(pos) && ", "if("), None, ()),
        ("standardmelt_finally_removed", "V3.", be("        } finally {\n            // A global flag: never leave it set, or every multiblock stops removing orphaned dummies.\n            DummyableBlock.safeRem = false;\n        }",
                                                   "        }\n        DummyableBlock.safeRem = false;"), None, ()),
        ("meltdown_finally_removed", "V3.", be("        } finally {\n            // A global flag like the original's; restored even if a block replacement throws.\n            RBMKBaseBlock.dropLids = true;\n        }",
                                               "        }\n        RBMKBaseBlock.dropLids = true;"), None, ()),
        ("meltdown_droplids_not_cleared", "V3.", be("RBMKBaseBlock.dropLids = false;\n        try {", "try {"), None, ()),
        ("standardmelt_third_chance", "V3.", be("level.random.nextInt(3) == 0", "level.random.nextInt(4) == 0"), None, ()),
        ("onmelt_mindist_plus_one_dropped", "V3.", be("rbmk.onMelt(minDist + 1);", "rbmk.onMelt(minDist);"), None, ()),
        ("lid_read_after_standardmelt", "V3.", T(BASE_BE, lambda t: swap_lines(t, "LidType lid = this.getLid();", "standardMelt(reduce);")), None, ()),
        ("lid_debris_for_glass_too", "V3.", be("if(lid == LidType.STANDARD)", "if(lid != LidType.NONE)"), None, ()),
        ("debris_spawn_y_plus_5", "V3.", be("worldPosition.getY() + 4D", "worldPosition.getY() + 5D"), None, ()),
        ("debris_lid_motion", "V3.", be("motionY += 0.5D;", "motionY += 0.4D;"), None, ()),
        ("flood_fill_one_direction_dropped", "V3.", be("                open.push(pos.east());\n", ""), None, ()),
        ("mush_scale_changed", "V3.", be('data.putFloat("scale", smallDim);', 'data.putFloat("scale", Math.max(maxX - minX, maxZ - minZ));'), None, ()),
        ("mush_radius_250_to_150", "V3.", be("avgZ + 0.5, 250,", "avgZ + 0.5, 150,"), None, ()),
        ("explosion_volume_50_to_5", "V3.", be("SoundSource.BLOCKS, 50.0F, 1.0F", "SoundSource.BLOCKS, 5.0F, 1.0F"), None, ()),
        ("nbt_heat_key_renamed", "V3.", be('tag.putDouble("heat", this.heat);', 'tag.putDouble("heat2", this.heat);'), None, ()),
        ("serialize_dropped", "V3.", be("        buf.writeDouble(this.heat);\n", ""), None, ()),
        ("slots_for_face_not_empty", "V3.", be("return new int[0];", "return new int[] {0};"), None, ()),
        ("machine_base_size_1", "V3.", be("super(type, pos, state, 0);", "super(type, pos, state, 1);"), None, ()),
        ("blank_debris_1_to_3", "V3.", T(BE_BLANK, lambda t: rep1(t, "1 + level.random.nextInt(2)", "1 + level.random.nextInt(3)")), None, ()),
        ("moderator_debris_type", "V3.", T(BE_MODERATOR, lambda t: rep1(t, "DebrisType.GRAPHITE", "DebrisType.BLANK")), None, ()),
        ("absorber_rbmk_type", "V3.", T(BE_ABSORBER, lambda t: rep1(t, "RBMKType.ABSORBER", "RBMKType.REFLECTOR")), None, ()),
        ("reflector_console_type", "V3.", T(BE_REFLECTOR, lambda t: rep1(t, "RBMKColumnType.REFLECTOR", "RBMKColumnType.ABSORBER")), None, ()),
        ("column_type_offset", "V3.", T(COLUMN_TYPE, lambda t: rep1(t, "HEATEX(130)", "HEATEX(131)")), None, ()),
        ("base_client_import", "V3.|V6.", be("import net.minecraft.world.phys.AABB;", "import net.minecraft.world.phys.AABB;\nimport net.minecraft.client.Minecraft;"), None, ()),
        # V4 blocks
        ("column_strength_3_to_4", "V4.", T(NB, lambda t: line_edit(t, 'register("rbmk_blank"', "strength(3.0F, 30.0F)", "strength(4.0F, 30.0F)")), None, ()),
        ("column_needs_no_tool", "V4.", T(NB, lambda t: line_edit(t, 'register("rbmk_moderator"', ".requiresCorrectToolForDrops()", "")), None, ()),
        ("debris_strength_50_to_51", "V4.", T(NB, lambda t: line_edit(t, 'register("pribris_burning"', "strength(50.0F, 600.0F)", "strength(51.0F, 600.0F)")), None, ()),
        ("deco_resistance_100_to_101", "V4.", T(NB, lambda t: line_edit(t, 'register("deco_rbmk"', "strength(5.0F, 100.0F)", "strength(5.0F, 101.0F)")), None, ()),
        ("dynamic_shape_removed", "V4.", T(BASE_BLK, lambda t: rep1(t, "super(properties.dynamicShape());", "super(properties);")), None, ()),
        ("lid_collision_1_25_to_1_5", "V4.", T(BASE_BLK, lambda t: rep1(t, "Shapes.box(0, 0, 0, 1, 1.25, 1)", "Shapes.box(0, 0, 0, 1, 1.5, 1)")), None, ()),
        ("lid_state_glass_renamed", "V4.", T(BASE_BLK, lambda t: rep1(t, 'GLASS("glass")', 'GLASS("glas")')), None, ()),
        ("dimension_not_height", "V4.", T(BASE_BLK, lambda t: rep1(t, "new int[] {RBMKDials.getColumnHeight(), 0, 0, 0, 0, 0}", "new int[] {3, 0, 0, 0, 0, 0}")), None, ()),
        ("make_extra_one_short", "V4.", T(BASE_BLK, lambda t: rep1(t, "pos.above(RBMKDials.getColumnHeight())", "pos.above(RBMKDials.getColumnHeight() - 1)")), None, ()),
        ("screw_any_tool", "V4.", T(BASE_BLK, lambda t: rep1(t, "if(tool != ToolType.SCREWDRIVER) return false;", "if(tool == ToolType.SCREWDRIVER) return false;")), None, ()),
        ("screw_drop_at_core_only", "V4.", T(BASE_BLK, lambda t: rep1(t, "core.getY() + 0.5 + RBMKDials.getColumnHeight()", "core.getY() + 0.5")), None, ()),
        ("screw_no_lid_state_reset", "V4.", T(BASE_BLK, lambda t: rep1(t, "coreState.setValue(LID, LidType.NONE)", "coreState")), None, ()),
        ("screw_no_on_lid_changed", "V4.", T(BASE_BLK, lambda t: rep1(t, "            rbmk.onLidChanged();\n", "")), None, ()),
        ("remove_drop_ignores_dropLids", "V4.", T(BASE_BLK, lambda t: rep1(t, "!level.isClientSide && dropLids && isCore(state)", "!level.isClientSide && isCore(state)")), None, ()),
        ("remove_drop_on_state_change", "V4.", T(BASE_BLK, lambda t: rep1(t, " && !state.is(newState.getBlock())", "")), None, ()),
        ("client_class_outside_hook", "V4.|V6.", T(BASE_BLK, lambda t: rep1(t, "public static void dropLid(Level level, BlockPos core, LidType lid) {", "public static void dropLid(Level level, BlockPos core, LidType lid) {\n        Minecraft.getInstance();")), None, ()),
        ("passive_block_entity_on_dummies", "V4.", T(PASSIVE_BLK, lambda t: rep1(t, "if(state.getValue(TYPE) != DummyBlockType.CORE) return null;\n        return this.type.get().create(pos, state);", "return this.type.get().create(pos, state);")), None, ()),
        ("burning_delay_100_to_101", "V4.", T(DEB_BURN, lambda t: rep1(t, "return 100 + random.nextInt(20);", "return 101 + random.nextInt(20);")), None, ()),
        ("burning_flame_one_in_four", "V4.", T(DEB_BURN, lambda t: rep_first(t, "if(random.nextInt(5) == 0) {", "if(random.nextInt(4) == 0) {")), None, ()),
        ("burning_gas_one_in_nine", "V4.", T(DEB_BURN, lambda t: rep1(t, "random.nextInt(10) == 0 && sideState.isAir()", "random.nextInt(9) == 0 && sideState.isAir()")), None, ()),
        ("burning_foam_chance_20", "V4.", T(DEB_BURN, lambda t: rep1(t, "BLOCK_FOAM.get()) ? 10 : 100", "BLOCK_FOAM.get()) ? 20 : 100")), None, ()),
        ("burning_out_chance", "V4.", T(DEB_BURN, lambda t: rep1(t, "? 10 : 100;", "? 10 : 99;")), None, ()),
        ("burning_flame_lifetime", "V4.", T(DEB_BURN, lambda t: rep1(t, 'tag.putInt("lifetime", 300);', 'tag.putInt("lifetime", 200);')), None, ()),
        ("burning_place_one_in_four", "V4.", T(DEB_BURN, lambda t: rep1(t, "if(level.random.nextInt(3) == 0) {", "if(level.random.nextInt(4) == 0) {")), None, ()),
        ("radiating_delay_20_to_21", "V4.", T(DEB_RAD, lambda t: rep1(t, "return 20 + random.nextInt(20);", "return 21 + random.nextInt(20);")), None, ()),
        ("radiating_roll_1000_to_999", "V4.", T(DEB_RAD, lambda t: rep1(t, "int chance = 1000;", "int chance = 999;")), None, ()),
        ("radiating_count_max_14", "V4.", T(DEB_RAD, lambda t: rep1(t, 'IntegerProperty.create("count", 0, 15)', 'IntegerProperty.create("count", 0, 14)')), None, ()),
        ("radiating_rads_1e6_to_1e5", "V4.", T(DEB_RAD, lambda t: rep1(t, "RADS = 1000000F", "RADS = 100000F")), None, ()),
        ("radiating_range_100_to_90", "V4.", T(DEB_RAD, lambda t: rep1(t, "RANGE = 100D", "RANGE = 90D")), None, ()),
        ("radiating_fire_range_5_to_6", "V4.", T(DEB_RAD, lambda t: rep1(t, "if(len < 5) {", "if(len < 6) {")), None, ()),
        ("radiating_fire_damage_100_to_10", "V4.", T(DEB_RAD, lambda t: rep1(t, "inFire(), 100)", "inFire(), 10)")), None, ()),
        ("radiating_falloff_not_squared", "V4.", T(DEB_RAD, lambda t: rep1(t, "eRads /= (float) (len * len);", "eRads /= (float) len;")), None, ()),
        ("radiating_radiation_type", "V4.", T(DEB_RAD, lambda t: rep1(t, "ContaminationType.CREATIVE, eRads", "ContaminationType.NONE, eRads")), None, ()),
        ("lid_item_pitch", "V4.", T(LID_ITEM, lambda t: rep1(t, "sound.getPitch() * 0.8F", "sound.getPitch() * 0.9F")), None, ()),
        ("lid_item_no_shrink", "V4.", T(LID_ITEM, lambda t: rep1(t, "context.getItemInHand().shrink(1);", "")), None, ()),
        ("lid_item_requires_lid", "V4.", T(LID_ITEM, lambda t: rep1(t, "if(tile.hasLid()) return InteractionResult.PASS;", "if(!tile.hasLid()) return InteractionResult.PASS;")), None, ()),
        ("lid_item_glass_sound", "V4.", T(LID_ITEM, lambda t: rep1(t, "this.lid == LidType.GLASS ? SoundType.GLASS : SoundType.STONE", "SoundType.STONE")), None, ()),
        ("dyatlov_rbmk_branch_removed", "V4.", T(DY, lambda t: rep1(t, "rbmkBlockEntity.meltdown();", "")), None, ()),
        # V5 debris entity
        ("lifetime_lid_30_to_20", "V5.", T(DEB_ENT, lambda t: rep1(t, "case LID -> 30 * 20;", "case LID -> 20 * 20;")), None, ()),
        ("lifetime_graphite_15_to_14", "V5.", T(DEB_ENT, lambda t: rep1(t, "case GRAPHITE -> 15 * 60 * 20;", "case GRAPHITE -> 14 * 60 * 20;")), None, ()),
        ("amplifier_9_to_8", "V5.", T(DEB_ENT, lambda t: rep1(t, "type == DebrisType.FUEL ? 9 : 4", "type == DebrisType.FUEL ? 8 : 4")), None, ()),
        ("amplifier_duration_halved", "V5.", T(DEB_ENT, lambda t: rep1(t, "ModEffect.RADIATION, 60 * 20, lvl", "ModEffect.RADIATION, 30 * 20, lvl")), None, ()),
        ("amplifier_range_3", "V5.", T(DEB_ENT, lambda t: rep1(t, "inflate(2.5D)", "inflate(3.0D)")), None, ()),
        ("pickup_graphite_to_metal", "V5.", T(DEB_ENT, lambda t: rep1(t, "case GRAPHITE -> new ItemStack(NtmItems.DEBRIS_GRAPHITE.get(), 1);", "case GRAPHITE -> new ItemStack(NtmItems.DEBRIS_METAL.get(), 1);")), None, ()),
        ("dimension_lid", "V5.", T(DEB_ENT, lambda t: rep1(t, "case LID -> EntityDimensions.scalable(1F, 0.5F);", "case LID -> EntityDimensions.scalable(1F, 0.6F);")), None, ()),
        ("perma_scrap_ignored", "V5.", T(DEB_ENT, lambda t: rep1(t, "!RBMKDials.getPermaScrap() && this.tickCount", "this.tickCount")), None, ()),
        ("lid_dig_removed", "V5.", T(DEB_ENT, lambda t: rep1(t, "ZirnoxDebris.digAround(this.level(), hit.getBlockPos(), this.random);", "")), None, ()),
        ("zirnox_perma_scrap_reverted", "V5.", T(ZD, lambda t: rep1(t, "!RBMKDials.getPermaScrap() && this.tickCount", "!PERMA_SCRAP && this.tickCount")), None, ()),
        ("debris_enum_order", "V5.", T(DEB_ENT, lambda t: rep1(t, "ROD,		//solid boron rod\n        GRAPHITE,	//spicy rock", "GRAPHITE,	//spicy rock\n        ROD,		//solid boron rod")), None, ()),
        # V6 registrations
        ("block_registered_twice", "V6.", T(NB, lambda t: dup_line(t, 'RBMK_BLANK = register("rbmk_blank"')), None, ()),
        ("block_entity_type_renamed", "V6.", T(NBET, lambda t: rep1(t, 'register("rbmk_absorber"', 'register("rbmk_absorber2"')), None, ()),
        ("entity_type_renamed", "V6.", T(NET, lambda t: rep1(t, 'register("rbmk_debris"', 'register("rbmk_debris2"')), None, ()),
        ("item_registered_twice", "V6.", T(NI, lambda t: dup_line(t, 'ITEMS.register("rbmk_lid_glass"')), None, ()),
        ("creative_pribris_removed", "V6.", T(CT, lambda t: drop_line(t, "output.accept(NtmBlocks.PRIBRIS_RADIATING);")), None, ()),
        ("creative_screwdriver_removed", "V6.", T(CT, lambda t: drop_line(t, "output.accept(NtmItems.SCREWDRIVER_DESH);")), None, ()),
        ("creative_deco_moved_to_machine", "V6.", T(CT, lambda t: swap_lines(t, "output.accept(NtmBlocks.DECO_RBMK);", "output.accept(NtmBlocks.RBMK_BLANK);")), None, ()),
        ("lid_renderer_removed", "V6.", T(CP, lambda t: drop_line(t, "RBMK_ABSORBER.get(), new RenderRBMKLid<>()")), None, ()),
        ("debris_renderer_removed", "V6.", T(CP, lambda t: drop_line(t, "RenderRBMKDebris::new")), None, ()),
        ("resource_texture_path", "V6.", T(RM, lambda t: rep1(t, "textures/block/rbmk/rbmk_fuel.png", "textures/block/rbmk/rbmk_fuel2.png")), None, ()),
        ("resource_model_missing", "V6.", T(RM, lambda t: drop_line(t, 'deb_rod = new HFRWavefrontObject("models/obj/projectiles/deb_rod.obj").asVBO();')), None, ()),
        ("geometry_case_removed", "V6.", T(GEOM, lambda t: drop_line(t, "case RBMK_DEBRIS ->")), None, ()),
        ("client_class_leaks_into_common", "V6.", lambda st: st.refs.__setitem__(BE_BLANK, {"RenderRBMKLid": 1}), None, ()),
        ("debris_renderer_not_client_only", "V6.", T(R_DEB, lambda t: rep1(t, "@OnlyIn(Dist.CLIENT)\npublic class", "public class")), None, ()),
        # V7 recipes
        ("recipe_key_changed", "V7.", recipe_edit("rbmk_absorber", lambda d: d["key"]["G"].__setitem__("item", "hbmsntm:ingot_lead")), None, ()),
        ("recipe_count_changed", "V7.", recipe_edit("rbmk_lid", lambda d: d["result"].__setitem__("count", 3)), None, ()),
        ("recipe_pattern_changed", "V7.", recipe_edit("rbmk_blank_from_deco_rbmk", lambda d: d.__setitem__("pattern", ["RRR", "RRR", "RRR"])), None, ()),
        ("recipe_file_removed", "V7.", D(RECIPES + "rbmk_reflector.json"), None, ()),
        ("recipe_tag_to_item", "V7.", recipe_edit("rbmk_lid", lambda d: d["key"].__setitem__("P", {"item": "hbmsntm:plate_steel"})), None, ()),
        ("moderator_recipe_added", "V7.", lambda st: st.set_text(RECIPES + "rbmk_moderator.json", json.dumps({"type": "minecraft:crafting_shaped", "result": {"count": 1, "id": "hbmsntm:rbmk_moderator"}})), None, ()),
        ("glass_lid_recipe_added", "V7.", lambda st: st.set_text(RECIPES + "rbmk_lid_glass.json", json.dumps({"type": "minecraft:crafting_shaped", "result": {"count": 4, "id": "hbmsntm:rbmk_lid_glass"}})), None, ()),
        ("anvil_row_added", "V7.", T(ANVIL, lambda t: t + "// constructionRecipes.add(new AnvilConstructionRecipe(new ComparableStack(NtmBlocks.RBMK_MODERATOR.get())))\n"), None, ()),
        ("ass_rbmk_count_4_to_3", "V7.", T(AMR, lambda t: rep1(t, "new ComparableStack(NtmBlocks.CONCRETE_ASBESTOS.get(), 4)", "new ComparableStack(NtmBlocks.CONCRETE_ASBESTOS.get(), 3)")), None, ()),
        ("ass_rbmk_setup_changed", "V7.", T(AMR, lambda t: rep1(t, 'new GenericRecipe("ass.rbmk").setup(100, 100)', 'new GenericRecipe("ass.rbmk").setup(100, 101)')), None, ()),
        ("ass_rbmk_rubber_removed", "V7.", T(AMR, lambda t: rep1(t, ",\n                        new ComparableStack(NtmItems.INGOT_RUBBER.get(), 2)", "")), None, ()),
        ("ass_other_row_changed", "V7.", T(AMR, lambda t: rep1(t, 'new GenericRecipe("ass.boytarget").setup(200, 100)', 'new GenericRecipe("ass.boytarget").setup(200, 101)')), None, ()),
        ("recipe_provider_row_removed", "V7.", T(RP, lambda t: rep1(t, '"rbmk_blank_from_deco_rbmk_smooth"', '"rbmk_blank_from_deco_rbmk_smooth2"')), None, ()),
        # V8 hazards
        ("debris_fuel_500_to_50", "V8.", T(HR, lambda t: line_edit(t, "item(DEBRIS_FUEL)", "RADIATION, 500F", "RADIATION, 50F")), None, ()),
        ("debris_fuel_hot_changed", "V8.", T(HR, lambda t: line_edit(t, "item(DEBRIS_FUEL)", "HOT, 5F", "HOT, 6F")), None, ()),
        ("vanilla_coal_restored", "V8.", T(HR, lambda t: insert_after(t, "item(DEBRIS_FUEL)", "        HazardSystem.register(Items.COAL, makeData(COAL, 1F));")), None, ()),
        ("vanilla_gold_restored", "V8.", T(HR, lambda t: insert_after(t, "item(DEBRIS_FUEL)", "        HazardSystem.register(Items.GOLD_INGOT, makeData(BLINDING, 4F));")), None, ()),
        # V9 close-out
        ("fluidtrait_duplicate_restored", "V9.", T(FT_TRAIT, lambda t: insert_after(t, 'registerTrait("flammable", FT_Flammable.class);', '        registerTrait("heatable", FT_Heatable.class);\n        registerTrait("coolable", FT_Coolable.class);')), None, ()),
        ("fluidtrait_pair_moved", "V9.", T(FT_TRAIT, lambda t: swap_lines(t, 'registerTrait("heatable", FT_Heatable.class);', 'registerTrait("polluting", FT_Polluting.class);')), None, ()),
        ("reacher_scan_reverted", "V9.", T(HTR, lambda t: re.sub(r"for \(ItemStack held.*?reacher = true;\s+break;\s+\}\s+\}\s+if \(player\.getOffhandItem\(\)\.is\(NtmItems\.REACHER\.get\(\)\)\) reacher = true;",
                                                                   "reacher = player.getInventory().contains(new ItemStack(NtmItems.REACHER.get()));", t, count=1, flags=re.S)), None, ()),
        ("reacher_offhand_dropped", "V9.", T(HTR, lambda t: rep1(t, "            if (player.getOffhandItem().is(NtmItems.REACHER.get())) reacher = true;\n", "")), None, ()),
        ("contamination_precedence_reverted", "V9.", T(CU, lambda t: rep1(t, "(player.isCreative() || player.isSpectator()) &&", "player.isCreative() || player.isSpectator() &&")), None, ()),
        ("contamination_digamma_dropped", "V9.", T(CU, lambda t: rep1(t, " && type != ContaminationType.DIGAMMA_ROBE) return;", ") return;")), None, ()),
        ("pheromone_key_reverted", "V9.", T(FT_PH, lambda t: rep1(t, "hbmfluid.trait.glyphidPheromones", "fluids.trait.glyphidPheromones")), None, ()),
        ("hold_shift_key_renamed", "V9.", T(TOOLTIP, lambda t: rep1(t, '"desc.misc.holdShiftMoreInfo"', '"desc.misc.holdShift"')), None, ()),
        ("hold_shift_hardcoded_in_fluidtype", "V9.", T(FLUIDTYPE, lambda t: rep1(t, "info.add(ITooltipProvider.holdShiftHint());", 'info.add(Component.literal("Hold <LSHIFT> to display more info"));')), None, ()),
        ("chloride_provider_reverted", "V9.|V11.", T(LP, lambda t: rep1(t, '"Calcium chloride Solution"', '"Calciumchloride Solution"')), None, ()),
        ("chloride_map_source_changed", "V9.", map_set("hbmfluid.potassium_chloride", "source_en", "Potassiumchloride Solution"), None, ()),
        ("chloride_map_target_changed", "V9.|V11.", map_set("hbmfluid.calcium_chloride", "target_en", "Calciumchloride Solution"), None, ()),
        ("turbofan_redstone_loop_back_to_conpos", "V9.", T(TURBO, lambda t: rep1(t, "for(DirPos pos : getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING))) {", "for(DirPos pos : this.getConPos()) {")), None, ()),
        ("turbofan_pipe_loop_to_ports", "V9.", T(TURBO, lambda t: rep1(t, "for(DirPos pos : this.getConPos()) {\n            if(!this.level.hasChunkAt", "for(DirPos pos : getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING))) {\n            if(!this.level.hasChunkAt")), None, ()),
        ("turbofan_conpos_body_changed", "V9.", T(TURBO, lambda t: rep1(t, ".relative(proxies[i].getDir())", ".relative(proxies[i].getDir()).relative(proxies[i].getDir())")), None, ()),
        ("turbofan_port_proxies_changed", "V9.", T(TURBO, lambda t: rep1(t, "new DirPos(core.relative(facing), facing)", "new DirPos(core.relative(facing, 2), facing)")), None, ()),
        # V10 screwdriver
        ("tooling_damage_on_failure", "V10.", T(TI, lambda t: rep1(t, "instanceof IToolable toolableBlock\n                && toolableBlock.onScrew(level, player, usedPos, usedDirection, this.type)) {",
                                                                   "instanceof IToolable toolableBlock) {\n            toolableBlock.onScrew(level, player, usedPos, usedDirection, this.type);")), None, ()),
        ("tooling_set_no_repair_removed", "V10.", T(TI, lambda t: rep1(t, "properties.stacksTo(1).setNoRepair()", "properties.stacksTo(1)")), None, ()),
        ("tooling_stack_size_removed", "V10.", T(TI, lambda t: rep1(t, "properties.stacksTo(1).setNoRepair()", "properties.setNoRepair()")), None, ()),
        ("tooling_always_success", "V10.", T(TI, lambda t: rep1(t, "return InteractionResult.PASS;\n    }\n}", "return InteractionResult.sidedSuccess(level.isClientSide);\n    }\n}")), None, ()),
        ("tooling_main_hand_slot", "V10.", T(TI, lambda t: rep1(t, "LivingEntity.getSlotForHand(context.getHand())", "EquipmentSlot.MAINHAND")), None, ()),
        ("screwdriver_durability_100_to_64", "V10.", T(NI, lambda t: line_edit(t, 'ITEMS.register("screwdriver"', "durability(100)", "durability(64)")), None, ()),
        ("screwdriver_desh_gets_durability", "V10.", T(NI, lambda t: line_edit(t, 'ITEMS.register("screwdriver_desh"', "new Item.Properties()", "new Item.Properties().durability(100)")), None, ()),
        ("screwdriver_plain_item_again", "V10.", T(NI, lambda t: line_edit(t, 'ITEMS.register("screwdriver"', "new ToolingItem(ToolType.SCREWDRIVER, new Item.Properties().durability(100))", "new Item(new Item.Properties().stacksTo(8))")), None, ()),
        ("defuser_line_changed", "V10.", T(NI, lambda t: line_edit(t, 'ITEMS.register("defuser"', "durability(100)", "durability(99)")), None, ()),
        ("lockable_pin_reverted", "V10.", T(LB, lambda t: rep1(t, "player.getInventory().contains(s -> s.is(NtmItems.SCREWDRIVER.get()) || s.is(NtmItems.SCREWDRIVER_DESH.get()))", "player.getInventory().contains(new ItemStack(NtmItems.SCREWDRIVER.get()))")), None, ()),
        # V11 language
        ("zh_value_changed", "V11.", zh_set("block.hbmsntm.rbmk_blank", "RBMK结构柱"), None, ()),
        ("zh_placeholder_dropped", "V11.", zh_set("desc.misc.holdShiftMoreInfo", "按住 <> 显示更多信息"), None, ()),
        ("zh_key_removed", "V11.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("item.hbmsntm.debris_fuel"))), None, ()),
        ("zh_stray_key_added", "V11.", zh_set("hbmsntm.stray", "x"), None, ()),
        ("zh_crlf_broken", "V11.", Bx(ZH, lambda b: b.replace(b"\r\n", b"\n", 1)), None, ()),
        ("map_crlf_broken", "V11.", Bx(MAP, lambda b: b.replace(b"\r\n", b"\n", 1)), None, ()),
        ("map_kind_flipped", "V11.", map_set("entity.hbmsntm.rbmk_debris", "kind", "upstream"), None, ()),
        ("map_target_zh_changed", "V11.", map_set("block.hbmsntm.pribris", "target_zh", "RBMK残骸"), None, ()),
        ("map_source_en_changed", "V11.", map_set("item.hbmsntm.rbmk_lid", "source_en", "RBMK Cover Plate"), None, ()),
        ("en_value_changed", "V11.", lambda st: st.set_text(EN, st.text(EN).replace('"RBMK Cover Panel"', '"RBMK Cover Plate"')), None, ()),
        ("provider_string_changed", "V11.", T(LP, lambda t: rep1(t, '"RBMK Structural Column"', '"RBMK Structural Columns"')), None, ()),
        ("map_entry_removed", "V11.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"].pop("tile.rbmk.dodd.heat"))), None, ()),
        # V12 resources
        ("png_byte_flipped", "V12.", Bx(RES + "textures/block/rbmk/rbmk_blank_side.png", flip_byte), None, ()),
        ("obj_byte_flipped", "V12.", Bx(RES + "models/obj/projectiles/deb_lid.obj", flip_byte), None, ()),
        ("debris_obj_byte_flipped", "V12.", Bx(RES + "models/obj/rbmk/debris.obj", flip_byte), None, ()),
        ("reused_graphite_obj_changed", "V12.", Bx(RES + "models/obj/projectiles/deb_graphite.obj", flip_byte), None, ()),
        ("ownership_sha_changed", "V12.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["assets"][0].__setitem__("target_sha256", "0" * 64))), None, ()),
        ("ownership_entry_removed", "V12.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["assets"].pop())), None, ()),
        ("resource_deleted", "V12.|V14.", D(RES + "textures/block/rbmk/rbmk_fuel.png"), None, ()),
        ("unlisted_resource_added", "V12.", lambda st: st.set_bytes(RES + "textures/block/rbmk/stray.png", b"x"), None, ()),
        # V13 classification
        ("classification_path_removed", "V13.", lambda st: st.set_text(CLASSIFY, json_edit(st.text(CLASSIFY), lambda d: d["entries"].pop())), None, ()),
        ("classification_summary_changed", "V13.", lambda st: st.set_text(CLASSIFY, json_edit(st.text(CLASSIFY), lambda d: d["summary"].__setitem__("not-migrated-other", d["summary"]["not-migrated-other"] + 1))), None, ()),
        ("classification_kind_changed", "V13.", lambda st: st.set_text(CLASSIFY, json_edit(st.text(CLASSIFY), lambda d: d["entries"][0].__setitem__("change", "added"))), None, ()),
        ("classification_category_unknown", "V13.", lambda st: st.set_text(CLASSIFY, json_edit(st.text(CLASSIFY), lambda d: d["entries"][0].__setitem__("category", "mystery"))), None, ()),
        # V14 scope
        ("stray_src_file_added", "V14.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}"), None, ()),
        ("unrelated_src_file_touched", "V14.", touch(J + "hazard/HazardSystem.java"), None, ()),
        ("unrelated_migration_file_added", "V14.", lambda st: st.set_bytes("migration/stray.json", b"{}"), None, ()),
        ("expected_file_reverted", "V14.", lambda st: st.tree.__setitem__(NI, st.inp_base[NI]), None, ()),
        # V15 GameTest source
        ("gt_annotation_removed", "V15.", T(RCGT, lambda t: rep_first(t, "@GameTest(", "// @GameTest(")), None, ()),
        ("gt_method_renamed", "V15.", T(RCGT, lambda t: rep1(t, "rbmk_heat_flow(GameTestHelper helper)", "rbmk_heat_flow_x(GameTestHelper helper)")), None, ()),
        ("gt_batch_dropped", "V15.", T(RCGT, lambda t: rep_first(t, "batch = BATCH, ", "")), None, ()),
        ("gt_marker_changed", "V15.", T(RCGT, lambda t: rep1(t, 'LOGGER.info("[hbm-rbmk-core] {} passed", name);\n    }\n\n    private static void done', 'LOGGER.info("[hbm-rbmk] {} passed", name);\n    }\n\n    private static void done')), None, ()),
        ("hazard_test_annotation_removed", "V15.", T(HGT, lambda t: rep1(t, "@GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)\n    public static void hazard_removed_vanilla_rows", "// @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)\n    public static void hazard_removed_vanilla_rows")), None, ()),
        ("hazard_start_test_renamed", "V15.", T(HGT, lambda t: rep1(t, "hazard_register_stacks(GameTestHelper helper)", "hazard_register_stacks_x(GameTestHelper helper)")), None, ()),
        ("hazard_sample_restored", "V15.", T(HGT, lambda t: rep_first(t, 'checkExact("cell_balefire"', 'checkExact("coal", new ItemStack(Items.COAL), HazardRegistry.COAL, 1F);\n        checkExact("cell_balefire"')), None, ()),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for label, prefixes, apply, required, requires_ok in mutations():
        if required is not None and not st.has(required):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        blocked = [c for c in requires_ok if c in base_failed]
        if blocked:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"the unmutated tree already fails {blocked}")
            continue
        mutated = st.copy()
        mutated.inp_base = inp.base_files
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
            continue
        if mutated.files == st.files and mutated.tree == st.tree and mutated.refs == st.refs:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error="mutation changed nothing")
            continue
        ck = static_suite(inp, mutated)
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
    for sec in ("V16", "V17"):
        out.setdefault(sec, [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec in ("V16", "V17") and not items:
            result[sec] = dict(status="not run", checks=0, passed=0, failed=[])
            continue
        failed = [i["id"] for i in items if i["status"] == "FAIL"]
        result[sec] = dict(status="PASS" if not failed else "FAIL", checks=len(items), passed=len(items) - len(failed), failed=failed)
    return result


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V16", v16_log, inp, st, args.gametest_log)
    if args.jar:
        extra["jar"] = guarded(ck, "V17", v17_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V18"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    production = NEW_CLASSES + EDITED + [LP, ZH, EN, STAMP, MAP, OWN, CLASSIFY, RCGT, HGT] + [a["target_path"] for a in inp.own["assets"]] + GENERATED
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
