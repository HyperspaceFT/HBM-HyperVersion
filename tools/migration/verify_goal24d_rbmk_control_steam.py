"""Verify the Goal24D batch statically: the RBMK control rods (rbmk_control, rbmk_control_mod, rbmk_control_auto: RBMKControlBlockEntity, RBMKControlManualBlockEntity,
RBMKControlAutoBlockEntity, blocks, menus, screens, RenderRBMKControl), the CONTROL_ROD branch of the neutron handler, the steam channel (rbmk_boiler), the fluid heater
(rbmk_heater), the cooler (rbmk_cooler), the loader (rbmk_loader), the fluid ports and the overpressure meltdown branch of RBMKBaseBlockEntity, the vent particle, the six
recipes, the datagen outputs, the 59 new language keys, the imported resources and the GameTest source.

Read-only for both worktrees. Writes only build/migration/goal24d/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal24d/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (control rods, steam channel, heater, cooler, blocks, ports, overpressure, neutron branch, GUIs, particle, recipes, anvil rows, language, resources)
      parsed from the read-only worktree at the cited lines; a moved line fails loudly.
- V2  The control rods against V1 (block entities, neutron handler branch).
- V3  The steam side against V1 (boiler, heater, cooler, loader, fluid ports, overpressure hook).
- V4  Blocks, menus, screens, renderers, particle, registrations, creative tab, client isolation.
- V5  Recipes: the six generated recipes, nothing else.
- V6  Datagen outputs: blockstates, models, item models, loot tables, pickaxe tag.
- V7  Language: the 59 new keys in the provider, en_us.json, zh_cn.json and zh_cn-map.json.
- V8  Resources: the imported files against the original and migration/goal24d-resource-ownership.json.
- V9  Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed separately).
- V10 GameTest source. V11 (--gametest-log) the GameTest log. V12 (--jar) the packaged JAR; "not run" when the flag is absent.
- V13 In-memory mutations of the NEO inputs and of the original text (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal24d_rbmk_control_steam.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import collections
import copy
from concurrent.futures import ThreadPoolExecutor
import difflib
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal24d"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "1114adf5de758697842e1f2195c0e3928b04abbc"

J = "src/main/java/com/hbm/"
BE = J + "blockentity/machine/rbmk/"
BLK = J + "blocks/machine/rbmk/"
CTL = BE + "RBMKControlBlockEntity.java"
MAN = BE + "RBMKControlManualBlockEntity.java"
AUT = BE + "RBMKControlAutoBlockEntity.java"
BOI = BE + "RBMKBoilerBlockEntity.java"
HEA = BE + "RBMKHeaterBlockEntity.java"
COO = BE + "RBMKCoolerBlockEntity.java"
BASEBE = BE + "RBMKBaseBlockEntity.java"
SLOT = BE + "RBMKSlottedBaseBlockEntity.java"
DIALS = BE + "RBMKDials.java"
PIPED = BLK + "RBMKPipedBaseBlock.java"
CBLK = BLK + "RBMKControlBlock.java"
ABLK = BLK + "RBMKControlAutoBlock.java"
BOIBLK = BLK + "RBMKBoilerBlock.java"
HEABLK = BLK + "RBMKHeaterBlock.java"
COOBLK = BLK + "RBMKCoolerBlock.java"
LOADBLK = BLK + "RBMKLoaderBlock.java"
BASEBLK = BLK + "RBMKBaseBlock.java"
RODBLK = BLK + "RBMKRodBlock.java"
CMENU = J + "inventory/menus/RBMKControlMenu.java"
AMENU = J + "inventory/menus/RBMKControlAutoMenu.java"
BMENU = J + "inventory/menus/RBMKBoilerMenu.java"
HMENU = J + "inventory/menus/RBMKHeaterMenu.java"
CSCREEN = J + "inventory/screens/RBMKControlScreen.java"
ASCREEN = J + "inventory/screens/RBMKControlAutoScreen.java"
BSCREEN = J + "inventory/screens/RBMKBoilerScreen.java"
HSCREEN = J + "inventory/screens/RBMKHeaterScreen.java"
RPIPED = J + "render/blockentity/RenderRBMKPiped.java"
RCONTROL = J + "render/blockentity/RenderRBMKControl.java"
RLID = J + "render/blockentity/RenderRBMKLid.java"
PARTICLE = J + "particle/RBMKSteamParticle.java"
RNH = J + "handler/neutron/RBMKNeutronHandler.java"
NB = J + "blocks/NtmBlocks.java"
BET = J + "blockentity/NtmBlockEntityTypes.java"
MT = J + "inventory/NtmMenuTypes.java"
CT = J + "inventory/NtmCreativeTabs.java"
NMC = J + "main/NuclearTechModClient.java"
CP = J + "main/ClientProxy.java"
RM = J + "main/ResourceManager.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
IMP = J + "datagen/NtmItemModelProvider.java"
LOOT = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
RP = J + "datagen/NtmRecipeProvider.java"
NITEMS = J + "items/NtmItems.java"
NTAGS = J + "inventory/NtmTags.java"
ITAGP = J + "datagen/NtmItemTagProvider.java"
ANVIL = J + "inventory/recipes/anvil/AnvilRecipes.java"
FLUIDTANK = J + "inventory/fluid/tank/FluidTank.java"
GT = J + "gametest/RBMKControlSteamGameTests.java"
GT_DIR = J + "gametest/"
SOUNDS = J + "registry/NtmSoundEvents.java"
AUXP = J + "network/toclient/AuxParticle.java"
NEW_CLASSES_A = [CTL, MAN, AUT, PIPED, CBLK, ABLK, CMENU, AMENU, CSCREEN, ASCREEN, RPIPED, RCONTROL]
NEW_CLASSES_B = [BOI, HEA, COO, BOIBLK, HEABLK, COOBLK, LOADBLK, BMENU, HMENU, BSCREEN, HSCREEN, PARTICLE]
NEW_CLASSES = NEW_CLASSES_A + NEW_CLASSES_B
EDITED = [RNH, BASEBLK, BASEBE, NB, BET, MT, CT, NMC, CP, RM, BSP, LOOT, TAGP, LP, RP]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal24d-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
G_STATE = GEN + "assets/hbmsntm/blockstates/"
G_BMODEL = GEN + "assets/hbmsntm/models/block/"
G_IMODEL = GEN + "assets/hbmsntm/models/item/"
G_LOOT = GEN + "data/hbmsntm/loot_table/blocks/"
RECIPES = GEN + "data/hbmsntm/recipe/"
ADV = GEN + "data/hbmsntm/advancement/recipes/"
RES = "src/main/resources/assets/hbmsntm/"
TEX = RES + "textures/block/"
OBJDIR = RES + "models/obj/rbmk/"
GUITEX = RES + "textures/gui/reactors/"

O = "src/main/java/com/hbm/"
O_TE = O + "tileentity/machine/rbmk/"
O_CTL = O_TE + "TileEntityRBMKControl.java"
O_MAN = O_TE + "TileEntityRBMKControlManual.java"
O_AUT = O_TE + "TileEntityRBMKControlAuto.java"
O_BOI = O_TE + "TileEntityRBMKBoiler.java"
O_HEA = O_TE + "TileEntityRBMKHeater.java"
O_COO = O_TE + "TileEntityRBMKCooler.java"
O_BASE = O_TE + "TileEntityRBMKBase.java"
O_B = O + "blocks/machine/rbmk/"
O_RCTL = O_B + "RBMKControl.java"
O_RAUTO = O_B + "RBMKControlAuto.java"
O_RPIPED = O_B + "RBMKPipedBase.java"
O_RBOI = O_B + "RBMKBoiler.java"
O_RHEA = O_B + "RBMKHeater.java"
O_RCOO = O_B + "RBMKCooler.java"
O_RLOAD = O_B + "RBMKLoader.java"
O_RBASE = O_B + "RBMKBase.java"
O_GCTL = O + "inventory/gui/GUIRBMKControl.java"
O_GAUT = O + "inventory/gui/GUIRBMKControlAuto.java"
O_GBOI = O + "inventory/gui/GUIRBMKBoiler.java"
O_GHEA = O + "inventory/gui/GUIRBMKHeater.java"
O_PART = O + "particle/ParticleRBMKSteam.java"
O_RNH = O + "handler/neutron/RBMKNeutronHandler.java"
O_CM = O + "main/CraftingManager.java"
O_AR = O + "inventory/recipes/anvil/AnvilRecipes.java"
O_MB = O + "blocks/ModBlocks.java"
O_CPROXY = O + "main/ClientProxy.java"
O_FT = O + "inventory/fluid/tank/FluidTank.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"

GT_MARK = "[hbm-rbmk-cs]"
START_GAMETESTS = 175
HASH_SKIP = ("__pycache__",)
START_EN_KEYS, START_ZH_KEYS, START_MAP_KEYS = 2614, 2507, 2614
NEW_EN_KEYS, NEW_ZH_KEYS, NEW_MAP_KEYS = 2673, 2566, 2673

# (NEO key, original key, English, Chinese, en_US.lang line, zh_CN.lang line); text as the two handoffs give it, compared with the lang files in V1
UP_A = [
    ("block.hbmsntm.rbmk_control", "tile.rbmk_control.name", "RBMK Control Rods", "RBMK反应堆控制棒", 6217, 5344),
    ("block.hbmsntm.rbmk_control_mod", "tile.rbmk_control_mod.name", "RBMK Moderated Control Rods", "RBMK反应堆慢化控制棒", 6219, 5346),
    ("block.hbmsntm.rbmk_control_auto", "tile.rbmk_control_auto.name", "RBMK Automatic Control Rods", "RBMK反应堆自动控制棒", 6218, 5345),
    ("container.rbmkControl", "container.rbmkControl", "RBMK Control Rods", "RBMK石墨式反应堆控制棒", 790, 634),
    ("container.rbmkControlAuto", "container.rbmkControlAuto", "RBMK Automatic Control Rods", "RBMK石墨式反应堆自动控制棒", 791, 635),
    ("rbmk.control.level", "rbmk.control.level", "%s", "%s", 5007, 4303),
    ("rbmk.control.red", "rbmk.control.red", "§cRed Group", "§c红色组", 5008, 4304),
    ("rbmk.control.yellow", "rbmk.control.yellow", "§eYellow Group", "§e黄色组", 5009, 4305),
    ("rbmk.control.green", "rbmk.control.green", "§aGreen Group", "§a绿色组", 5010, 4306),
    ("rbmk.control.blue", "rbmk.control.blue", "§1Blue Group", "§1蓝色组", 5011, 4307),
    ("rbmk.control.purple", "rbmk.control.purple", "§5Purple Group", "§5紫色组", 5012, 4308),
    ("tile.rbmk.dodd.level", "tile.rbmk.dodd.level", "Level", "控制棒深度", 6259, 5940),
    ("tile.rbmk.dodd.targetLevel", "tile.rbmk.dodd.targetLevel", "Target Level", "目标深度", 6260, 5941),
    ("tile.rbmk.dodd.startingLevel", "tile.rbmk.dodd.startingLevel", "Starting Level", "起始深度", 6261, 5942),
    ("tile.rbmk.dodd.mult", "tile.rbmk.dodd.mult", "Mult", "倍数", 6262, 5943),
    ("tile.rbmk.dodd.color", "tile.rbmk.dodd.color", "Color", "颜色", 6263, 5944),
    ("tile.rbmk.dodd.levelLower", "tile.rbmk.dodd.levelLower", "Level Lower", "深度下限", 6264, 5945),
    ("tile.rbmk.dodd.levelUpper", "tile.rbmk.dodd.levelUpper", "Level Upper", "深度上限", 6265, 5946),
    ("tile.rbmk.dodd.heatLower", "tile.rbmk.dodd.heatLower", "Heat Lower", "温度下限", 6266, 5947),
    ("tile.rbmk.dodd.heatUpper", "tile.rbmk.dodd.heatUpper", "Heat Upper", "温度上限", 6267, 5948),
    ("tile.rbmk.dodd.function", "tile.rbmk.dodd.function", "Function", "函数类型", 6268, 5949)]
UP_B = [
    ("block.hbmsntm.rbmk_boiler", "tile.rbmk_boiler.name", "RBMK Steam Channel", "RBMK反应堆蒸汽管道", 6214, 5341),
    ("block.hbmsntm.rbmk_heater", "tile.rbmk_heater.name", "RBMK Fluid Heater", "RBMK流体加热器", 6231, 5348),
    ("block.hbmsntm.rbmk_cooler", "tile.rbmk_cooler.name", "RBMK Cooler", "RBMK冷却器", 6216, 5343),
    ("block.hbmsntm.rbmk_loader", "tile.rbmk_loader.name", "RBMK Steam Connector", "RBMK反应堆蒸汽导出器", 6238, 5349),
    ("block.hbmsntm.rbmk_loader.desc", "tile.rbmk_loader.desc",
     "Allows RBMKs to have both water and steam connections at the bottom$Place one water pipe below the RBMK column, then the connector,$then connect the steam duct to the connector.",
     "让RBMK反应堆在底部同时拥有水接口和蒸汽接口$在RBMK蒸汽管道下方放置水管道，再在下面放置蒸汽导出器$最后将管道连接至蒸汽导出器即可", 6239, 5350),
    ("container.rbmkBoiler", "container.rbmkBoiler", "RBMK Steam Channel", "RBMK石墨式反应堆蒸汽管道", 789, 633),
    ("container.rbmkHeater", "container.rbmkHeater", "RBMK Fluid Heater", "RBMK流体加热器", 794, 636),
    ("rbmk.boiler.water", "rbmk.boiler.water", "Feedwater: %s / %s", "供水速率: %s / %s", 4997, 4293),
    ("rbmk.boiler.steam", "rbmk.boiler.steam", "Steam: %s / %s", "蒸汽产生速率: %s / %s", 4998, 4294),
    ("rbmk.boiler.type", "rbmk.boiler.type", "Compressor: %s", "蒸汽压缩等级: %s", 4999, 4295),
    ("tile.rbmk.dodd.feed", "tile.rbmk.dodd.feed", "Feed", "工质储量", 6276, 5957),
    ("tile.rbmk.dodd.feed_max", "tile.rbmk.dodd.feed_max", "Feed Max Amount", "工质最大储量", 6293, 5974),
    ("tile.rbmk.dodd.feed_type", "tile.rbmk.dodd.feed_type", "Feed Type(ID)", "工质种类(ID)", 6283, 5964),
    ("tile.rbmk.dodd.feed_p", "tile.rbmk.dodd.feed_p", "Feed Pressure", "工质压力", 6288, 5969),
    ("tile.rbmk.dodd.steam", "tile.rbmk.dodd.steam", "Steam", "蒸汽储量", 6277, 5958),
    ("tile.rbmk.dodd.steam_max", "tile.rbmk.dodd.steam_max", "Steam Max Amount", "蒸汽最大储量", 6294, 5975),
    ("tile.rbmk.dodd.steam_type", "tile.rbmk.dodd.steam_type", "Steam Type(ID)", "蒸汽种类(ID)", 6284, 5965),
    ("tile.rbmk.dodd.steam_p", "tile.rbmk.dodd.steam_p", "Steam Pressure", "蒸汽压力", 6289, 5970),
    ("tile.rbmk.dodd.t0", "tile.rbmk.dodd.t0", "Cold PFM Amount", "冷四氟甲烷储量", 6303, 6261),
    ("tile.rbmk.dodd.t0_max", "tile.rbmk.dodd.t0_max", "Cold PFM Capacity", "冷四氟甲烷容量", 6304, 6262),
    ("tile.rbmk.dodd.t0_type", "tile.rbmk.dodd.t0_type", "Cold PFM Type", "冷四氟甲烷种类", 6305, 6263),
    ("tile.rbmk.dodd.t0_p", "tile.rbmk.dodd.t0_p", "Cold PFM Pressure", "冷四氟甲烷压力", 6306, 6264),
    ("tile.rbmk.dodd.t1", "tile.rbmk.dodd.t1", "PFM Amount", "四氟甲烷储量", 6307, 6265),
    ("tile.rbmk.dodd.t1_max", "tile.rbmk.dodd.t1_max", "PFM Capacity", "四氟甲烷容量", 6308, 6266),
    ("tile.rbmk.dodd.t1_type", "tile.rbmk.dodd.t1_type", "PFM Type", "四氟甲烷种类", 6309, 6267),
    ("tile.rbmk.dodd.t1_p", "tile.rbmk.dodd.t1_p", "PFM Pressure", "四氟甲烷压力", 6310, 6268)]
LOCAL_A = {
    "container.rbmkControlAuto.function": ("Function: %s", "函数：%s"),
    "container.rbmkControlAuto.linear": ("Linear", "线性"),
    "container.rbmkControlAuto.quadUp": ("Quadratic", "二次"),
    "container.rbmkControlAuto.quadDown": ("Inverse Quadratic", "反二次"),
    "container.rbmkControlAuto.selectLinear": ("Select linear interpolation", "选择线性插值"),
    "container.rbmkControlAuto.selectQuadUp": ("Select quadratic interpolation", "选择二次插值"),
    "container.rbmkControlAuto.selectQuadDown": ("Select inverse quadratic interpolation", "选择反二次插值"),
    "container.rbmkControlAuto.levelUpper": ("Level at max heat$Should be smaller than level at min heat", "最高温度时的控制棒抽出量$应小于最低温度时的控制棒抽出量"),
    "container.rbmkControlAuto.levelLower": ("Level at min heat$Should be larger than level at max heat", "最低温度时的控制棒抽出量$应大于最高温度时的控制棒抽出量"),
    "container.rbmkControlAuto.heatUpper": ("Max heat$Must be larger than min heat", "最高温度$必须大于最低温度"),
    "container.rbmkControlAuto.heatLower": ("Min heat$Must be smaller than max heat", "最低温度$必须小于最高温度"),
    "container.rbmkControlAuto.save": ("Save parameters", "保存参数")}
UP_ALL = UP_A + UP_B
UP_EXPECT = {u[0]: (u[2], u[3]) for u in UP_ALL}
NEW_KEYS = sorted(list(UP_EXPECT) + list(LOCAL_A))

# imported resources: (original path under assets/hbm, NEO path under assets/hbmsntm)
CTL_TEX = [(f"textures/blocks/rbmk/{n}_{p}.png", f"textures/block/rbmk/{n}_{p}.png") for n in ("rbmk_control", "rbmk_control_mod", "rbmk_control_auto") for p in ("side", "top", "pipe_side", "pipe_top")]
HEAD_TEX = [(f"textures/blocks/rbmk/{n}.png", f"textures/block/rbmk/{n}.png") for n in ("rbmk_control_auto", "rbmk_control_red", "rbmk_control_yellow", "rbmk_control_green", "rbmk_control_blue", "rbmk_control_purple")]
IMPORTS_A = CTL_TEX + HEAD_TEX + [("models/rbmk/rbmk_rods.obj", "models/obj/rbmk/rbmk_rods.obj"),
                                  ("textures/gui/reactors/gui_rbmk_control.png", "textures/gui/reactors/gui_rbmk_control.png"),
                                  ("textures/gui/reactors/gui_rbmk_control_auto.png", "textures/gui/reactors/gui_rbmk_control_auto.png")]
STEAM_TEX = [(f"textures/blocks/rbmk/{n}_{p}.png", f"textures/block/rbmk/{n}_{p}.png")
             for n, parts in (("rbmk_boiler", ("side", "top", "cover_side", "cover_top", "glass_side", "glass_top", "pipe_side", "pipe_top")),
                              ("rbmk_heater", ("side", "top", "cover_side", "cover_top", "glass_side", "glass_top", "pipe_side", "pipe_top")),
                              ("rbmk_cooler", ("side", "top", "cover_side", "cover_top", "glass_side", "glass_top"))) for p in parts]
IMPORTS_B = STEAM_TEX + [("textures/blocks/rbmk_loader.png", "textures/block/rbmk_loader.png"),
                         ("textures/gui/reactors/gui_rbmk_boiler.png", "textures/gui/reactors/gui_rbmk_boiler.png"),
                         ("textures/gui/reactors/gui_rbmk_heater.png", "textures/gui/reactors/gui_rbmk_heater.png")]
IMPORTS = IMPORTS_A + IMPORTS_B
PARTICLE_ORIG = "textures/particle/rbmk_jet_steam.png"
PARTICLE_NEO = RES + "textures/particle_no_sheet/rbmk_jet_steam.png"
REASIM_NOT_IMPORTED = [f"textures/blocks/rbmk/{n}.png" for n in (
    "rbmk_control_reasim_auto_bottom", "rbmk_control_reasim_auto_pipe_side", "rbmk_control_reasim_auto_pipe_top", "rbmk_control_reasim_auto_side", "rbmk_control_reasim_auto_top",
    "rbmk_control_reasim_bottom", "rbmk_control_reasim_pipe_side", "rbmk_control_reasim_pipe_top", "rbmk_control_reasim_side", "rbmk_control_reasim_top")]
NOT_IMPORTED_A = ["textures/blocks/rbmk/rbmk_control.png", "textures/blocks/rbmk/rbmk_control_base.png"] + REASIM_NOT_IMPORTED


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


# ---------------------------------------------------------------- text helpers

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


def match_paren(code, open_index):
    return match_delim(code, open_index, "(", ")")


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
    return squash_lit(blank_comments(lf(text)))


def rewrite(s, table):
    for pat, rep in table:
        s = re.sub(pat, rep, s)
    return s


def lit(old, new):
    """A literal replacement rule for rewrite()."""
    return re.escape(old), new.replace("\\", "\\\\")


def cut(s, start, end, repl=""):
    """Remove the first occurrence of start ... end (end included) from a squashed string; ValueError when absent."""
    i = s.index(start)
    j = s.index(end, i + len(start)) + len(end)
    return s[:i] + repl + s[j:]


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


def format_ok(text, data):
    plain = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return text == plain or text == crlf(plain)


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def rep_first(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


def _line_hit(lines, needle):
    hits = [i for i, l in enumerate(lines) if needle in l]
    assert len(hits) == 1, (needle, len(hits))
    return hits[0]


def drop_line(text, needle):
    lines = text.split("\n")
    del lines[_line_hit(lines, needle)]
    return "\n".join(lines)


def dup_line(text, needle):
    lines = text.split("\n")
    i = _line_hit(lines, needle)
    lines.insert(i + 1, lines[i])
    return "\n".join(lines)


def swap_lines(text, a, b):
    lines = text.split("\n")
    ia, ib = _line_hit(lines, a), _line_hit(lines, b)
    lines[ia], lines[ib] = lines[ib], lines[ia]
    return "\n".join(lines)


def insert_after(text, needle, new_line):
    lines = text.split("\n")
    lines.insert(_line_hit(lines, needle) + 1, new_line)
    return "\n".join(lines)


def line_edit(text, needle, old, new):
    lines = text.split("\n")
    i = _line_hit(lines, needle)
    assert lines[i].count(old) == 1, (old, lines[i])
    lines[i] = lines[i].replace(old, new)
    return "\n".join(lines)


def json_edit(text, edit):
    data = json.loads(text)
    edit(data)
    eol = "\r\n" if "\r\n" in text else "\n"
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", eol) + eol


def png_size(data):
    return list(struct.unpack(">II", data[16:24])) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


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


# ---------------------------------------------------------------- state and inputs

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


STAMP_TEXT_EXT = {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml", "txt", "vsh", "xml", "yaml", "yml"}
STAMP_BUILD_INPUTS = ["build.gradle", "gradle.properties", "settings.gradle", "gradle/migration-resources.gradle", "gradle/wrapper/gradle-wrapper.properties", "gradle.lockfile"]


def stamp_hash(path):
    """gradle/migration-resources.gradle hashFile: text extensions are UTF-8 decoded with CRLF and CR turned into LF; a malformed text file keeps its raw bytes."""
    data = Path(path).read_bytes()
    if Path(path).suffix[1:].lower() in STAMP_TEXT_EXT:
        try:
            data = data.decode("utf-8").replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10)).encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def stamp_hashes():
    """({input path: hash}, {generated path: hash}) of the working tree under the rule the migration stamp uses."""
    inputs = {}
    for top in ("src/main/java", "src/main/resources"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                inputs[path.relative_to(ROOT).as_posix()] = stamp_hash(path)
    for rel in STAMP_BUILD_INPUTS:
        if (ROOT / rel).is_file():
            inputs[rel] = stamp_hash(ROOT / rel)
    generated = {}
    for base, dirs, names in os.walk(ROOT / "src/generated/resources"):
        dirs[:] = [d for d in dirs if d != ".cache"]
        for name in names:
            path = Path(base) / name
            rel = path.relative_to(ROOT / "src/generated/resources").as_posix()
            if rel != ".migration-stamp.json":
                generated[rel] = stamp_hash(path)
    return inputs, generated


def otext(path):
    return lf(read_text(ORIGINAL / path))


def need_ov(inp):
    if inp.ov is None:
        raise RuntimeError("the original could not be parsed (V1): " + str(inp.ov_error))
    return inp.ov


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
            inp.start[rel] = data.decode("utf-8")
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    names = dict(ctl=O_CTL, man=O_MAN, aut=O_AUT, boi=O_BOI, hea=O_HEA, coo=O_COO, base=O_BASE, rctl=O_RCTL, rauto=O_RAUTO, rpiped=O_RPIPED, rboi=O_RBOI, rhea=O_RHEA, rcoo=O_RCOO,
                 rload=O_RLOAD, rbase=O_RBASE, gctl=O_GCTL, gaut=O_GAUT, gboi=O_GBOI, ghea=O_GHEA, part=O_PART, rnh=O_RNH, cm=O_CM, ar=O_AR, mb=O_MB, cproxy=O_CPROXY, ft=O_FT)
    inp.o = {name: otext(path) for name, path in names.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    tree = hash_tree()
    files = {}
    load = set(NEW_CLASSES + EDITED + [BE + "RBMKType.java", SLOT, DIALS, RODBLK, RLID, ZH, MAP, OWN, EN, STAMP, PICK, ANVIL, IMP, FLUIDTANK,
                                       J + "gametest/RBMKReactorGameTests.java", J + "blocks/machine/rbmk/RBMKPassiveBlock.java", SOUNDS, AUXP, NITEMS, NTAGS, ITAGP])
    for p in tree:
        if p not in inp.base_files and (p.startswith(GEN) or p.startswith(GT_DIR)):
            load.add(p)
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    for _, neo in IMPORTS:
        if (ROOT / (RES + neo)).exists():
            files[RES + neo] = (ROOT / (RES + neo)).read_bytes()
    if (ROOT / PARTICLE_NEO).exists():
        files[PARTICLE_NEO] = (ROOT / PARTICLE_NEO).read_bytes()
    for base_dir in (G_STATE, G_BMODEL, G_IMODEL, G_LOOT):
        for n in ("rbmk_control", "rbmk_control_mod", "rbmk_control_auto", "rbmk_boiler", "rbmk_heater", "rbmk_cooler", "rbmk_loader", "rbmk_blank"):
            f = ROOT / (base_dir + n + ".json")
            if f.exists():
                files[base_dir + n + ".json"] = f.read_bytes()
    for n in ("rbmk_control", "rbmk_control_mod", "rbmk_control_auto", "rbmk_loader", "rbmk_boiler", "rbmk_heater", "rbmk_cooler"):
        for p in (RECIPES + n + ".json", ADV + "misc/" + n + ".json"):
            if (ROOT / p).exists():
                files[p] = (ROOT / p).read_bytes()
    inp.stamp_now, inp.gen_now = stamp_hashes()
    inp.own = json.loads(files[OWN].decode("utf-8")) if OWN in files else {"assets": [], "not_imported": []}
    inp.o_res = {}
    for orig, neo in IMPORTS:
        f = ORIGINAL / (O_RES + orig)
        if f.exists():
            inp.o_res[RES + neo] = f.read_bytes()
    f = ORIGINAL / (O_RES + PARTICLE_ORIG)
    inp.o_particle = f.read_bytes() if f.exists() else None
    inp.o_blob = {}
    for orig, neo in IMPORTS:
        if orig.endswith(".obj"):
            try:
                inp.o_blob[RES + neo] = git(ORIGINAL, "show", "HEAD:" + O_RES + orig)
            except Exception:  # noqa: BLE001 - reported by V8
                inp.o_blob[RES + neo] = None
    inp.o_not_imported = {n: (ORIGINAL / (O_RES + n)).exists() for n in NOT_IMPORTED_A}

    def last_commit(pair):
        return git(ORIGINAL, "log", "-1", "--format=%H", "--", O_RES + pair[0]).decode("utf-8").strip()
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            inp.last_commit = dict(zip((RES + n for _, n in IMPORTS), pool.map(last_commit, IMPORTS)))
    except Exception as error:  # noqa: BLE001
        inp.last_commit = {"error": repr(error)}
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    try:
        inp.ov, inp.ov_error = parse_original(inp), None
    except Exception as error:  # noqa: BLE001
        inp.ov, inp.ov_error = None, repr(error)
    return inp, State(files, tree)


def first_diff(a, b, width=90):
    n = min(len(a), len(b))
    i = next((k for k in range(n) if a[k] != b[k]), n)
    return f"@{i}: expected ...{a[max(0, i - width):i + width]}... got ...{b[max(0, i - width):i + width]}..."


def eq(ck, cid, label, expected, got):
    """Compare two squashed code strings; the failure detail shows the first difference."""
    ok = bool(expected) and expected == got
    return ck(cid, ok, label, "" if ok else first_diff(expected, got))


def contains_all(ck, cid, label, code, *needles):
    miss = [n for n in needles if n not in code]
    return ck(cid, not miss, label, miss)


# ---------------------------------------------------------------- the original: signatures parsed once, anchors checked in V1

# key -> (inputs key, exact method header in the original)
ORIG_SIGS = {
    "ctl.update": ("ctl", "public void updateEntity()"),
    "ctl.lid": ("ctl", "public boolean isLidRemovable()"),
    "ctl.type": ("ctl", "public RBMKType getRBMKType()"),
    "ctl.serialize": ("ctl", "public void serialize(ByteBuf buf)"),
    "ctl.deserialize": ("ctl", "public void deserialize(ByteBuf buf)"),
    "man.deserialize": ("man", "public void deserialize(ByteBuf buf)"),
    "man.type": ("man", "public ColumnType getConsoleType()"),
    "aut.type": ("aut", "public ColumnType getConsoleType()"),
    "rnh.run": ("rnh", "public void runStreamInteraction(World worldObj, StreamWorld streamWorld)"),
    "boi.type": ("boi", "public ColumnType getConsoleType()"),
    "boi.getAll": ("boi", "public FluidTank[] getAllTanks()"),
    "boi.getSending": ("boi", "public FluidTank[] getSendingTanks()"),
    "boi.getReceiving": ("boi", "public FluidTank[] getReceivingTanks()"),
    "hea.type": ("hea", "public ColumnType getConsoleType()"),
    "hea.getAll": ("hea", "public FluidTank[] getAllTanks()"),
    "hea.getSending": ("hea", "public FluidTank[] getSendingTanks()"),
    "hea.getReceiving": ("hea", "public FluidTank[] getReceivingTanks()"),
    "hea.info": ("hea", "public String[] getFunctionInfo()"),
    "coo.type": ("coo", "public ColumnType getConsoleType()"),
    "coo.getAll": ("coo", "public FluidTank[] getAllTanks()"),
    "coo.getReceiving": ("coo", "public FluidTank[] getReceivingTanks()"),
    "coo.getSending": ("coo", "public FluidTank[] getSendingTanks()"),
    "ctl.setTarget": ("ctl", "public void setTarget(double target)"),
    "ctl.getMult": ("ctl", "public double getMult()"),
    "ctl.track": ("ctl", "public int trackingRange()"),
    "ctl.read": ("ctl", "public void readFromNBT(NBTTagCompound nbt)"),
    "ctl.write": ("ctl", "public void writeToNBT(NBTTagCompound nbt)"),
    "ctl.onMelt": ("ctl", "public void onMelt(int reduce)"),
    "ctl.console": ("ctl", "public NBTTagCompound getNBTForConsole()"),
    "ctl.info": ("ctl", "public String[] getFunctionInfo()"),
    "ctl.ror": ("ctl", "public String provideRORValue(String name)"),
    "man.setTarget": ("man", "public void setTarget(double target)"),
    "man.getMult": ("man", "public double getMult()"),
    "man.perm": ("man", "public boolean hasPermission(EntityPlayer player)"),
    "man.receive": ("man", "public void receiveControl(EntityPlayer player, NBTTagCompound data)"),
    "man.read": ("man", "public void readFromNBT(NBTTagCompound nbt)"),
    "man.write": ("man", "public void writeToNBT(NBTTagCompound nbt)"),
    "man.serialize": ("man", "public void serialize(ByteBuf buf)"),
    "man.console": ("man", "public NBTTagCompound getNBTForConsole()"),
    "man.getSettings": ("man", "public NBTTagCompound getSettings(World world, int x, int y, int z)"),
    "man.paste": ("man", "public void pasteSettings(NBTTagCompound nbt, int index, World world, EntityPlayer player, int x, int y, int z)"),
    "man.info": ("man", "public String[] getFunctionInfo()"),
    "man.run": ("man", "public String runRORFunction(String name, String[] params)"),
    "aut.update": ("aut", "public void updateEntity()"),
    "aut.perm": ("aut", "public boolean hasPermission(EntityPlayer player)"),
    "aut.read": ("aut", "public void readFromNBT(NBTTagCompound nbt)"),
    "aut.write": ("aut", "public void writeToNBT(NBTTagCompound nbt)"),
    "aut.serialize": ("aut", "public void serialize(ByteBuf buf)"),
    "aut.deserialize": ("aut", "public void deserialize(ByteBuf buf)"),
    "aut.receive": ("aut", "public void receiveControl(EntityPlayer player, NBTTagCompound data)"),
    "aut.getSettings": ("aut", "public NBTTagCompound getSettings(World world, int x, int y, int z)"),
    "aut.paste": ("aut", "public void pasteSettings(NBTTagCompound nbt, int index, World world, EntityPlayer player, int x, int y, int z)"),
    "boi.update": ("boi", "public void updateEntity()"),
    "boi.heat": ("boi", "public static double getHeatFromSteam(FluidType type)"),
    "boi.factor": ("boi", "public static double getFactorFromSteam(FluidType type)"),
    "boi.read": ("boi", "public void readFromNBT(NBTTagCompound nbt)"),
    "boi.write": ("boi", "public void writeToNBT(NBTTagCompound nbt)"),
    "boi.serialize": ("boi", "public void serialize(ByteBuf buf)"),
    "boi.deserialize": ("boi", "public void deserialize(ByteBuf buf)"),
    "boi.perm": ("boi", "public boolean hasPermission(EntityPlayer player)"),
    "boi.receive": ("boi", "public void receiveControl(EntityPlayer player, NBTTagCompound data)"),
    "boi.cycle": ("boi", "public void cyceCompressor()"),
    "boi.onMelt": ("boi", "public void onMelt(int reduce)"),
    "boi.console": ("boi", "public NBTTagCompound getNBTForConsole()"),
    "boi.info": ("boi", "public String[] getFunctionInfo()"),
    "boi.ror": ("boi", "public String provideRORValue(String name)"),
    "hea.update": ("hea", "public void updateEntity()"),
    "hea.read": ("hea", "public void readFromNBT(NBTTagCompound nbt)"),
    "hea.write": ("hea", "public void writeToNBT(NBTTagCompound nbt)"),
    "hea.serialize": ("hea", "public void serialize(ByteBuf buf)"),
    "hea.deserialize": ("hea", "public void deserialize(ByteBuf buf)"),
    "hea.onMelt": ("hea", "public void onMelt(int reduce)"),
    "hea.console": ("hea", "public NBTTagCompound getNBTForConsole()"),
    "hea.ror": ("hea", "public String provideRORValue(String name)"),
    "coo.update": ("coo", "public void updateEntity()"),
    "coo.read": ("coo", "public void readFromNBT(NBTTagCompound nbt)"),
    "coo.write": ("coo", "public void writeToNBT(NBTTagCompound nbt)"),
    "coo.serialize": ("coo", "public void serialize(ByteBuf buf)"),
    "coo.deserialize": ("coo", "public void deserialize(ByteBuf buf)"),
    "base.meltdown": ("base", "public void meltdown()"),
    "base.portsNo": ("base", "public PortDef[] getPortsNoLoader()"),
    "base.portsClose": ("base", "public PortDef[] getPortsCloseLoader()"),
    "base.portsClassic": ("base", "public PortDef[] getPortsClassicLoader()"),
    "rctl.create": ("rctl", "public TileEntity createNewTileEntity(World world, int meta)"),
    "rload.canConnect": ("rload", "public boolean canConnect(FluidType type, IBlockAccess world, int x, int y, int z, ForgeDirection dir)"),
    "ft.setType": ("ft", "public void setTankType(FluidType type)"),
}


def parse_original(inp):
    """The squashed bodies of the original methods the checks compare against. A header that moved or vanished raises here and fails V0."""
    ov = SimpleNamespace(b={})
    for key, (src, sig) in ORIG_SIGS.items():
        try:
            ov.b[key] = body(inp.o[src], sig)
        except ValueError as error:
            raise ValueError(f"{key}: {error}") from error
    return ov


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) >= 40 and len(inp.baseline["copied_scope"]) == 40 and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, 40 in copied_scope) hashes to its baseline.json entry", bad)
    needed = NEW_CLASSES + EDITED + [ZH, MAP, OWN, EN, STAMP, DIALS, PICK]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 1114adf5", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.original-parsed", inp.ov is not None, "the original sources were parsed at the cited headers", inp.ov_error)


# ---------------------------------------------------------------- V1

def parse_cm_row(line):
    """(result block name, count, pattern rows, {key char: expression}) of one addRecipeAuto row of CraftingManager."""
    m = re.search(r"addRecipeAuto\(new ItemStack\(ModBlocks\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);", line)
    if not m:
        raise ValueError("not a recipe row: " + line.strip()[:80])
    parts, depth, cur = [], 0, ""
    for ch in m[3]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    pattern = [p.strip('"') for p in parts if p.startswith('"')]
    rest = [p for p in parts if not p.startswith('"')]
    keys = {rest[i].strip("'"): rest[i + 1] for i in range(0, len(rest), 2)}
    return m[1], int(m[2]), pattern, keys


def parse_anvil_rows(text, first, last):
    """{ModBlocks input name: (tier, [(output expression, count)])} of the constructionRecipes.add rows between two 1-based lines."""
    seg = "\n".join(text.split("\n")[first - 1:last])
    rows = {}
    for chunk in seg.split("constructionRecipes.add(")[1:]:
        m = re.search(r"new ComparableStack\(ModBlocks\.(\w+)\)", chunk)
        if not m:
            continue
        tier = re.search(r"setTier\((\d+)\)", chunk)
        outs = re.findall(r"new AnvilOutput\(new ItemStack\(([\w.]+), (\d+)(?:, ([\w.() ]+?))?\)\)", chunk)
        rows[m[1]] = (int(tier[1]) if tier else None, [(o[0] + (":" + o[2] if o[2] else ""), int(o[1])) for o in outs])
    return rows


def v1_original(ck, inp, st):
    ov = need_ov(inp)
    L = inp.ol
    # ---- TileEntityRBMKControl.java
    t = L["ctl"]
    m = at_lines(t, {29: "public double lastLevel;", 30: "public double level;", 31: "public static final double speed = 0.00277D;", 32: "public double targetLevel;", 40: "super(0);", 60: "public boolean isLidRemovable() {",
                     61: "return false;", 78: "if(worldObj.isRemote) {", 79: "this.lastLevel = this.level;", 83: "this.hasPower = true;", 92: "this.lastLevel = this.level;", 94: "if(this.hasPower) {", 95: "if(level < targetLevel) {",
                     96: "level += speed * RBMKDials.getControlSpeed(worldObj);", 97: "if(level > targetLevel) level = targetLevel;", 100: "if(level > targetLevel) {", 101: "level -= speed * RBMKDials.getControlSpeed(worldObj);",
                     102: "if(level < targetLevel) level = targetLevel;", 111: "super.updateEntity();", 114: "public void setTarget(double target) {", 115: "this.targetLevel = target;", 118: "public double getMult() {",
                     119: "return this.level;", 123: "public int trackingRange() {", 124: "return 100;"})
    order = [78, 83, 92, 95, 100, 111]
    ck("V1.control-tick", not m and order == sorted(order), "TileEntityRBMKControl.java:29-125: speed 0.00277D, client copies lastLevel only, server hasPower := true then lastLevel = level, level += speed * getControlSpeed with clamp to the target "
       "(both directions, :95-103), then super tick; setTarget; getMult = level; isLidRemovable false (:59-62); trackingRange 100", m)
    m = at_lines(t, {131: 'this.level = nbt.getDouble("level");', 132: 'this.targetLevel = nbt.getDouble("targetLevel");', 139: 'nbt.setDouble("level", this.level);', 140: 'nbt.setDouble("targetLevel", this.targetLevel);',
                     146: "buf.writeDouble(this.level);", 147: "buf.writeDouble(this.targetLevel);", 148: "buf.writeLong(this.power);", 149: "buf.writeBoolean(this.hasPower);", 155: "this.level = buf.readDouble();",
                     156: "this.targetLevel = buf.readDouble();"})
    ck("V1.control-nbt-sync", not m, "TileEntityRBMKControl.java:127-159: NBT keys level and targetLevel; serialize level, targetLevel, then power and hasPower (the ReaSim part)", m)
    m = at_lines(t, {170: "if(this.isModerated()) {", 172: "int count = 2 + worldObj.rand.nextInt(2);", 175: "spawnDebris(DebrisType.GRAPHITE);", 179: "int count = 2 + worldObj.rand.nextInt(2);", 182: "spawnDebris(DebrisType.ROD);",
                     185: "this.standardMelt(reduce);", 190: "return RBMKType.CONTROL_ROD;", 195: "NBTTagCompound data = new NBTTagCompound();", 196: 'data.setDouble("level", this.level);', 197: 'data.setDouble("targetLevel", this.targetLevel);'})
    order = [170, 175, 182, 185]
    ck("V1.control-melt-console", not m and order == sorted(order) and "super.onMelt" not in ov.b["ctl.onMelt"] and "super.getNBTForConsole" not in ov.b["ctl.console"],
       "TileEntityRBMKControl.java:167-199 onMelt: GRAPHITE 2 + rand(2) when moderated, then ROD 2 + rand(2), then standardMelt, the base onMelt (lid debris) is not called; type CONTROL_ROD; "
       "getNBTForConsole builds a new compound with level and targetLevel only", m)
    m = at_lines(t, {249: 'PREFIX_VALUE + "extraction"', 255: 'if((PREFIX_VALUE + "extraction").equals(name))'})
    ck("V1.control-ror", not m and "return \"\" + (int) (this.level * 100);" in t[254], "TileEntityRBMKControl.java:246-257 RoR value extraction = (int) (level * 100)", m)
    # ---- TileEntityRBMKControlManual.java
    t = L["man"]
    m = at_lines(t, {28: "public RBMKColor color;", 29: "public double startingLevel;", 37: 'return "container.rbmkControl";', 42: "return ((RBMKControl)this.getBlockType()).moderated;", 47: "this.targetLevel = target;",
                     48: "this.startingLevel = this.level;", 54: "double surge = 0;", 56: "if(this.targetLevel < this.startingLevel && Math.abs(this.level - this.targetLevel) > 0.01D) {",
                     57: "surge = Math.sin(Math.pow((1D - this.level), 15) * Math.PI) * (this.startingLevel - this.targetLevel) * RBMKDials.getSurgeMod(worldObj);", 61: "return this.level + surge;",
                     66: "Vec3.createVectorHelper(xCoord - player.posX, yCoord - player.posY, zCoord - player.posZ).lengthVector() < 20;"})
    ck("V1.manual-surge-target", not m, "TileEntityRBMKControlManual.java:28-67: color and startingLevel fields, container.rbmkControl, moderated from the block, setTarget sets target and startingLevel = level, getMult adds "
       "sin(pow(1 - level, 15) * PI) * (startingLevel - target) * getSurgeMod when target < startingLevel and |level - target| > 0.01, hasPermission measures from the block corner (< 20)", m)
    m = at_lines(t, {72: 'if(data.hasKey("level")) {', 73: 'this.setTarget(data.getDouble("level"));', 76: 'if(data.hasKey("color")) {', 77: 'int c = Math.abs(data.getInteger("color")) % RBMKColor.values().length;',
                     79: "RBMKColor newCol = RBMKColor.values()[c];", 81: "if(newCol == this.color) {", 82: "this.color = null;", 84: "this.color = newCol;", 88: "this.markDirty();"})
    ck("V1.manual-receive", not m and "Math.abs(data.getDouble" not in ov.b["man.receive"] and "clamp" not in ov.b["man.receive"].lower(),
       "TileEntityRBMKControlManual.java:69-89 receiveControl: `level` goes unvalidated into setTarget (no clamp), `color` is abs(int) % 5 and the same colour toggles to null, then markDirty", m)
    m = at_lines(t, {95: 'if(nbt.hasKey("startingLevel"))', 96: 'this.startingLevel = nbt.getDouble("startingLevel");', 98: 'if(nbt.hasKey("color"))', 99: 'this.color = RBMKColor.values()[nbt.getInteger("color")];', 101: "this.color = null;",
                     108: 'nbt.setDouble("startingLevel", this.startingLevel);', 109: 'nbt.setDouble("mult", this.getMult());', 111: "if(color != null)", 112: 'nbt.setInteger("color", color.ordinal());',
                     118: "buf.writeDouble(this.startingLevel);", 120: "buf.writeInt(this.color.ordinal());", 122: "buf.writeInt(-1);", 128: "this.startingLevel = buf.readDouble();",
                     130: "this.color = RBMKColor.values()[MathHelper.clamp_int(color, 0, RBMKColor.values().length)];", 131: "if(color == -1) this.color = null;"})
    ck("V1.manual-nbt-sync", not m, "TileEntityRBMKControlManual.java:91-132: NBT startingLevel, color (ordinal, absent = null) and the written `mult`; serialize startingLevel then the colour ordinal or -1", m)
    m = at_lines(t, {134: "public static enum RBMKColor {", 135: "RED,", 136: "YELLOW,", 137: "GREEN,", 138: "BLUE,", 139: "PURPLE", 144: "return ColumnType.CONTROL;", 152: 'data.setShort("color", (short)this.color.ordinal());',
                     154: 'data.setShort("color", (short)-1);', 189: 'if(color != null) data.setInteger("color", color.ordinal());', 196: "color = EnumUtil.grabEnumSafely(RBMKColor.class, nbt.getInteger(\"color\"));", 198: "color = null;", 200: "this.markChanged();"})
    ck("V1.manual-enum-copy-console", not m, "TileEntityRBMKControlManual.java:134-201: RBMKColor RED, YELLOW, GREEN, BLUE, PURPLE; console type CONTROL with super data plus short color (-1 when null); ICopiable getSettings writes color when "
       "set, pasteSettings reads it with grabEnumSafely or null and marks changed", m)
    m = at_lines(t, {206: 'PREFIX_VALUE + "extraction"', 207: 'PREFIX_FUNCTION + "setrods" + NAME_SEPARATOR + "percent"', 208: 'PREFIX_FUNCTION + "extendrods" + NAME_SEPARATOR + "percent"', 215: 'if((PREFIX_FUNCTION + "setrods").equals(name) && params.length > 0) {',
                     216: "int percent = IRORInteractive.parseInt(params[0], 0, 100);", 217: "this.setTarget(percent / 100D);", 222: 'if((PREFIX_FUNCTION + "extendrods").equals(name) && params.length > 0) {',
                     223: "int percent = IRORInteractive.parseInt(params[0], -100, 100);", 224: "this.setTarget(MathHelper.clamp_double(this.targetLevel + percent / 100D, 0D, 1D));"})
    ck("V1.manual-ror", not m, "TileEntityRBMKControlManual.java:203-230 RoR: extraction value, setrods percent 0..100 -> setTarget(p / 100), extendrods percent -100..100 -> setTarget(clamp(target + p / 100, 0, 1)), both mark dirty", m)
    # ---- TileEntityRBMKControlAuto.java
    t = L["aut"]
    m = at_lines(t, {23: "public RBMKFunction function = RBMKFunction.LINEAR;", 24: "public double levelLower;", 25: "public double levelUpper;", 26: "public double heatLower;", 27: "public double heatUpper;",
                     31: 'return "container.rbmkControlAuto";', 36: "Vec3.createVectorHelper(xCoord - player.posX, yCoord - player.posY, zCoord - player.posZ).lengthVector() < 20;",
                     42: "if(!worldObj.isRemote) {", 46: "double lowerBound = Math.min(this.heatLower, this.heatUpper);", 47: "double upperBound = Math.max(this.heatLower, this.heatUpper);",
                     49: "if(this.heat < lowerBound) {", 50: "fauxLevel = this.levelLower;", 52: "} else if(this.heat > upperBound) {", 53: "fauxLevel = this.levelUpper;", 57: "switch(this.function) {",
                     61: "fauxLevel = (this.heat - this.heatLower) * ((this.levelUpper - this.levelLower) / (this.heatUpper - this.heatLower)) + this.levelLower;",
                     66: "fauxLevel = Math.pow((this.heat - this.heatLower) / (this.heatUpper - this.heatLower), 2) * (this.levelUpper - this.levelLower) + this.levelLower;",
                     70: "fauxLevel = Math.pow((this.heat - this.heatUpper) / (this.heatLower - this.heatUpper), 2) * (this.levelLower - this.levelUpper) + this.levelUpper;",
                     75: "this.targetLevel = fauxLevel * 0.01D;", 76: "this.targetLevel = MathHelper.clamp_double(this.targetLevel, 0D, 1D);", 79: "super.updateEntity();"})
    order = [42, 46, 49, 52, 57, 75, 76, 79]
    ck("V1.auto-functions", not m and order == sorted(order), "TileEntityRBMKControlAuto.java:39-80: server only, before the parent tick: bounds = min/max of the heats, heat < lower -> levelLower, heat > upper -> levelUpper, else LINEAR, QUAD_UP and QUAD_DOWN "
       "as written, target = clamp(faux * 0.01, 0, 1), then super.updateEntity()", m)
    m = at_lines(t, {86: 'this.levelLower = nbt.getDouble("levelLower");', 89: 'this.heatUpper = nbt.getDouble("heatUpper");', 91: 'if(nbt.hasKey("function"))', 92: 'this.function = RBMKFunction.values()[nbt.getInteger("function")];', 94: "this.function = null;",
                     101: 'nbt.setDouble("levelLower", levelLower);', 104: 'nbt.setDouble("heatUpper", heatUpper);', 106: "if(function != null)", 107: 'nbt.setInteger("function", function.ordinal());', 113: "buf.writeDouble(this.levelLower);",
                     116: "buf.writeDouble(this.heatUpper);", 117: "if(function != null) buf.writeInt(function.ordinal());", 127: "this.function = RBMKFunction.values()[buf.readInt()];"})
    ck("V1.auto-nbt-sync", not m, "TileEntityRBMKControlAuto.java:82-128: NBT four doubles and `function` (absent = null, written only when non-null); serialize writes the function only when non-null while deserialize always reads it (desync)", m)
    m = at_lines(t, {133: 'if(data.hasKey("function")) {', 134: 'int c = Math.abs(data.getInteger("function")) % RBMKColor.values().length;', 135: "this.function = RBMKFunction.values()[c];",
                     139: 'this.levelLower = data.getDouble("levelLower");', 140: 'this.levelUpper = data.getDouble("levelUpper");', 141: 'this.heatLower = data.getDouble("heatLower");', 142: 'this.heatUpper = data.getDouble("heatUpper");',
                     145: "this.markDirty();", 148: "public static enum RBMKFunction {", 149: "LINEAR,", 150: "QUAD_UP,", 151: "QUAD_DOWN", 156: "return ColumnType.CONTROL_AUTO;"})
    ck("V1.auto-receive", not m, "TileEntityRBMKControlAuto.java:130-156 receiveControl: `function` = abs(int) % RBMKColor.values().length (5, so 3 and 4 index past the three functions: ArrayIndexOutOfBounds on the original server), else the four "
       "doubles unvalidated; RBMKFunction LINEAR, QUAD_UP, QUAD_DOWN; console type CONTROL_AUTO", m)
    m = at_lines(t, {173: 'data.setDouble("levelLower", levelLower);', 176: 'data.setDouble("heatUpper", heatUpper);', 177: 'data.setInteger("function", function.ordinal());', 183: 'if(nbt.hasKey("levelLower")) levelLower = nbt.getDouble("levelLower");',
                     186: 'if(nbt.hasKey("heatUpper")) heatUpper = nbt.getDouble("heatUpper");', 187: 'if(nbt.hasKey("function")) function = EnumUtil.grabEnumSafely(RBMKFunction.class, nbt.getInteger("function"));'})
    ck("V1.auto-copy", not m and "markChanged" not in ov.b["aut.paste"] and "markDirty" not in ov.b["aut.paste"], "TileEntityRBMKControlAuto.java:170-188 ICopiable: getSettings writes the four doubles and the function ordinal (NPE when null), pasteSettings reads each key "
       "when present and does not mark the tile", m)
    # ---- the six blocks
    b = L["rctl"]
    m = at_lines(b, {16: "public class RBMKControl extends RBMKPipedBase {", 18: "public boolean moderated = false;", 43: "if(meta >= this.offset) return new TileEntityRBMKControlManual();",
                     44: "if(meta >= this.extra) return new TileEntityProxyCombo();", 50: "return openInv(world, x, y, z, player);"})
    b2 = L["rauto"]
    m += at_lines(b2, {15: "public class RBMKControlAuto extends RBMKPipedBase {", 36: "if(meta >= this.offset) return new TileEntityRBMKControlAuto();", 37: "return null;", 42: "return openInv(world, x, y, z, player);"})
    b3 = L["rpiped"]
    m += at_lines(b3, {8: "public abstract class RBMKPipedBase extends RBMKBase {", 19: 'this.pipeTextureTop = reg.registerIcon(this.getTextureName() + "_pipe_top");', 20: 'this.pipeTextureSide = reg.registerIcon(this.getTextureName() + "_pipe_side");',
                       26: "if(renderPipes) return side == 0 || side == 1 ? pipeTextureTop : pipeTextureSide;", 32: "return this.renderIDControl;"})
    ck("V1.blocks-control", not m and "isOpaqueCube" not in inp.o["rctl"] + inp.o["rauto"] + inp.o["rpiped"] and "new TileEntityProxyCombo(" in b[43] + b[42] and "false" not in b[43] and "(false" not in b[42],
       "RBMKControl.java: moderated flag, core = TileEntityRBMKControlManual and the extra cell = a plain TileEntityProxyCombo (no flags); RBMKControlAuto.java: core only, no extra cell; RBMKPipedBase.java: <name>_pipe_top/_pipe_side icons, "
       "pipe faces when renderPipes, control render type; no block overrides isOpaqueCube; both rods open the GUI through openInv", m)
    m = at_lines(L["rboi"], {10: "public class RBMKBoiler extends RBMKPipedBase {", 15: "if(meta >= this.offset)", 16: "return new TileEntityRBMKBoiler();", 18: "if(hasExtra(meta))", 19: "return new TileEntityProxyCombo(false, false, true);", 26: "return openInv(world, x, y, z, player);"})
    m += at_lines(L["rhea"], {10: "public class RBMKHeater extends RBMKPipedBase {", 16: "return new TileEntityRBMKHeater();", 19: "return new TileEntityProxyCombo(false, false, true);", 26: "return openInv(world, x, y, z, player);"})
    m += at_lines(L["rcoo"], {9: "public class RBMKCooler extends RBMKBase {", 13: "if(meta >= this.offset) return new TileEntityRBMKCooler();", 14: "if(hasExtra(meta)) return new TileEntityProxyCombo().fluid();", 20: "return this.renderIDPassive;"})
    ck("V1.blocks-steam", not m and "onBlockActivated" not in inp.o["rcoo"], "RBMKBoiler / RBMKHeater: core tile entity and an extra cell TileEntityProxyCombo(false, false, true) (fluid proxy), they open the GUI; RBMKCooler extends RBMKBase "
       "(not piped, passive render), extra cell TileEntityProxyCombo().fluid(), no onBlockActivated", m)
    m = at_lines(L["rload"], {19: "public class RBMKLoader extends BlockGeneric implements IFluidConnectorBlockMK2, ITooltipProvider {", 21: "public RBMKLoader(Material material) {", 27: "if(dir == ForgeDirection.UP) return type.hasTrait(FT_Heatable.class);",
                             28: "return type.hasTrait(FT_Coolable.class) || type == Fluids.PERFLUOROMETHYL;", 33: "this.addStandardInfo(stack, player, list, ext);"})
    ck("V1.loader", not m and "createNewTileEntity" not in inp.o["rload"], "RBMKLoader.java:19-34: a plain block (no tile entity) that connects UP when the fluid is FT_Heatable, otherwise when it is FT_Coolable or PERFLUOROMETHYL, with the standard tooltip", m)
    mb = L["mb"]
    m = at_lines(mb, {2117: "rbmk_control = new RBMKControl(false).setBlockName(\"rbmk_control\")", 2118: "rbmk_control_mod = new RBMKControl(true).setBlockName(\"rbmk_control_mod\")", 2119: "rbmk_control_auto = new RBMKControlAuto().setBlockName(\"rbmk_control_auto\")",
                      2123: "rbmk_boiler = new RBMKBoiler().setBlockName(\"rbmk_boiler\")", 2129: "rbmk_cooler = new RBMKCooler().setBlockName(\"rbmk_cooler\")", 2130: "rbmk_heater = new RBMKHeater().setBlockName(\"rbmk_heater\")",
                      2143: "rbmk_loader = new RBMKLoader(Material.iron).setBlockName(\"rbmk_loader\").setCreativeTab(MainRegistry.machineTab).setHardness(50.0F).setResistance(60.0F)",
                      3111: "GameRegistry.registerBlock(rbmk_control,", 3112: "GameRegistry.registerBlock(rbmk_control_mod,", 3113: "GameRegistry.registerBlock(rbmk_control_auto,", 3116: "GameRegistry.registerBlock(rbmk_blank,",
                      3117: "GameRegistry.registerBlock(rbmk_boiler,", 3118: "GameRegistry.registerBlock(rbmk_reflector,", 3120: "GameRegistry.registerBlock(rbmk_moderator,", 3123: "GameRegistry.registerBlock(rbmk_cooler,",
                      3124: "GameRegistry.registerBlock(rbmk_heater,", 3137: "register(rbmk_loader);"})
    ck("V1.registration-order", not m, "ModBlocks.java:2117-2143 / :3111-3137: the registry order blank, boiler, reflector, absorber, moderator, outgasser, storage, cooler, heater and rbmk_loader; control rods rbmk_control, rbmk_control_mod, rbmk_control_auto "
       "after the ReaSim rods; rbmk_loader is Material.iron with hardness 50 and resistance 60", m)
    # ---- TileEntityRBMKBoiler.java
    t = L["boi"]
    m = at_lines(t, {44: "public FluidTank feed;", 45: "public FluidTank steam;", 46: "protected int consumption;", 47: "protected int output;", 48: "protected int ventDelay;", 53: "super(0);", 55: "feed = new FluidTank(Fluids.WATER, 10000);",
                     56: "steam = new FluidTank(Fluids.STEAM, 1000000);", 63: 'return "container.rbmkBoiler";', 71: "ports.update(worldObj.getBlock(xCoord, yCoord - 2, zCoord) == ModBlocks.rbmk_loader ? this.getPortsClassicLoader() :",
                     72: "worldObj.getBlock(xCoord, yCoord - 1, zCoord) == ModBlocks.rbmk_loader ? this.getPortsCloseLoader() : this.getPortsNoLoader());", 74: "this.consumption = 0;", 75: "this.output = 0;", 76: "if(this.ventDelay > 0) this.ventDelay--;",
                     78: "double heatCap = this.getHeatFromSteam(steam.getTankType());", 79: "double heatProvided = this.heat - heatCap;", 81: "if(heatProvided > 0) {", 82: "double HEAT_PER_MB_WATER = RBMKDials.getBoilerHeatConsumption(worldObj);",
                     83: "double steamFactor = getFactorFromSteam(steam.getTankType());", 87: "if(steam.getTankType() == Fluids.ULTRAHOTSTEAM) {", 88: "steamProduced = (int)Math.floor((heatProvided / HEAT_PER_MB_WATER) * 100D / steamFactor);",
                     89: "waterUsed = (int)Math.floor(steamProduced / 100D * steamFactor);", 91: "if(feed.getFill() < waterUsed) {", 92: "steamProduced = (int)Math.floor(feed.getFill() * 100D / steamFactor);",
                     93: "waterUsed = (int)Math.floor(steamProduced / 100D * steamFactor);", 96: "waterUsed = (int)Math.floor(heatProvided / HEAT_PER_MB_WATER);", 97: "waterUsed = Math.min(waterUsed, feed.getFill());",
                     98: "steamProduced = (int)Math.floor((waterUsed * 100D) / steamFactor);", 101: "this.consumption = waterUsed;", 102: "this.output = steamProduced;", 104: "feed.setFill(feed.getFill() - waterUsed);",
                     105: "steam.setFill(steam.getFill() + steamProduced);", 107: "if(steam.getFill() > steam.getMaxFill()) {", 108: "steam.setFill(steam.getMaxFill());", 110: "if(ventDelay <= 0) {", 112: 'data.setString("type", "rbmksteam");',
                     113: "xCoord + 0.25 + worldObj.rand.nextInt(2) * 0.5, yCoord + RBMKDials.getColumnHeight(worldObj), zCoord + 0.25 + worldObj.rand.nextInt(2) * 0.5), new TargetPoint(worldObj.provider.dimensionId, xCoord + 0.5, yCoord + 1, zCoord + 0.5, 100));",
                     115: "this.ventDelay = 20 + worldObj.rand.nextInt(10);", 116: 'this.worldObj.playSoundEffect(xCoord, yCoord + RBMKDials.getColumnHeight(worldObj), zCoord, "hbm:block.steamEngineOperate", 2F, 1F + worldObj.rand.nextFloat() * 0.25F);',
                     120: "this.heat -= waterUsed * HEAT_PER_MB_WATER;", 124: "super.updateEntity();"})
    order = [71, 74, 76, 78, 81, 101, 104, 105, 107, 115, 120, 124]
    ck("V1.boiler-tick", not m and order == sorted(order), "TileEntityRBMKBoiler.java:44-125: tanks WATER 10,000 / STEAM 1,000,000; ports from the loader layout, consumption = output = 0, ventDelay--, heatCap by grade, heatProvided = heat - heatCap; ULTRAHOTSTEAM branch "
       "floor((hp / HPMW) * 100 / f), floor(sp / 100 * f), feed shortage recompute; other branch floor(hp / HPMW), min(wu, feed), floor(wu * 100 / f); feed/steam update, steam clamp with the vent block (rbmksteam particle at x + 0.25 + rand(2) * 0.5, "
       "y + columnHeight, range 100, ventDelay 20 + rand(10), hbm:block.steamEngineOperate volume 2 pitch 1 + rand * 0.25), heat -= wu * HPMW, then super tick", m)
    m = at_lines(t, {128: "if(type == Fluids.STEAM) return 100D;", 129: "if(type == Fluids.HOTSTEAM) return 300D;", 130: "if(type == Fluids.SUPERHOTSTEAM) return 450D;", 131: "if(type == Fluids.ULTRAHOTSTEAM) return 600D;", 132: "return 0D;",
                     136: "if(type == Fluids.STEAM) return 1D;", 137: "if(type == Fluids.HOTSTEAM) return 10D;", 138: "if(type == Fluids.SUPERHOTSTEAM) return 100D;", 139: "if(type == Fluids.ULTRAHOTSTEAM) return 1000D;", 140: "return 0D;"})
    ck("V1.boiler-tables", not m, "TileEntityRBMKBoiler.java:127-141: heat from steam 100 / 300 / 450 / 600 and the factor 1 / 10 / 100 / 1000 for STEAM / HOTSTEAM / SUPERHOTSTEAM / ULTRAHOTSTEAM, else 0", m)
    m = at_lines(t, {147: 'feed.readFromNBT(nbt, "feed");', 148: 'steam.readFromNBT(nbt, "steam");', 155: 'feed.writeToNBT(nbt, "feed");', 156: 'steam.writeToNBT(nbt, "steam");', 162: "steam.serialize(buf);", 163: "feed.serialize(buf);",
                     169: "this.steam.deserialize(buf);", 170: "this.feed.deserialize(buf);", 175: "Vec3.createVectorHelper(xCoord - player.posX, yCoord - player.posY, zCoord - player.posZ).lengthVector() < 20;", 181: 'if(data.hasKey("compression")) {', 182: "this.cyceCompressor();"})
    ck("V1.boiler-nbt-control", not m, "TileEntityRBMKBoiler.java:143-184: NBT feed and steam through the tanks, serialize steam THEN feed, hasPermission < 20 from the block corner, receiveControl `compression` -> cyceCompressor", m)
    m = at_lines(t, {186: "public void cyceCompressor() {", 188: "if(this.heat > 50 && this.feed.getFill() > 0) return;", 190: "FluidType type = steam.getTankType();",
                     191: "if(type == Fluids.STEAM) {			steam.setTankType(Fluids.HOTSTEAM);			steam.setFill(steam.getFill() / 10); }", 192: "if(type == Fluids.HOTSTEAM) {		steam.setTankType(Fluids.SUPERHOTSTEAM);	steam.setFill(steam.getFill() / 10); }",
                     193: "if(type == Fluids.SUPERHOTSTEAM) {	steam.setTankType(Fluids.ULTRAHOTSTEAM);	steam.setFill(steam.getFill() / 10); }", 194: "if(type == Fluids.ULTRAHOTSTEAM) {	steam.setTankType(Fluids.STEAM);			steam.setFill(Math.min(steam.getFill() * 1000, steam.getMaxFill())); }",
                     196: "this.markDirty();"})
    ft = L["ft"]
    zeroes = "this.type=type;this.setFill(0);" in ov.b["ft.setType"] or "this.type = type;" in "".join(ft)
    ck("V1.boiler-compressor", not m and "this.setFill(0);" in "".join(ft[61:68]) and zeroes,
       "TileEntityRBMKBoiler.java:186-197 cyceCompressor (spelling kept): refused when heat > 50 and the feed tank is not empty, the type is captured once, four sequential ifs STEAM -> HOTSTEAM, HOTSTEAM -> SUPERHOTSTEAM, SUPERHOTSTEAM -> ULTRAHOTSTEAM "
       "(fill / 10) and ULTRAHOTSTEAM -> STEAM (min(fill * 1000, max)), each calls setTankType BEFORE setFill(getFill() ...) and FluidTank.setTankType (:62-68) zeroes the fill on a type change, so every accepted step empties the steam tank", m)
    m = at_lines(t, {202: "int count = 1 + worldObj.rand.nextInt(2);", 205: "spawnDebris(DebrisType.BLANK);", 208: "if(RBMKDials.getOverpressure(worldObj) && ports.outPorts != null) {", 209: "for(TilePort port : ports.outPorts) if(port != null) for(DirPos con : port.connections) {",
                     210: "FluidNode node = (FluidNode) UniNodespace.getNode(worldObj, con.getX(), con.getY(), con.getZ(), steam.getTankType().getNetworkProvider());", 211: "if(node != null && node.hasValidNet()) {", 212: "this.pipes.add(node.net);",
                     217: "super.onMelt(reduce);", 222: "return ColumnType.BOILER;", 228: 'data.setInteger("water", this.feed.getFill());', 229: 'data.setInteger("maxWater", this.feed.getMaxFill());', 230: 'data.setInteger("steam", this.steam.getFill());',
                     231: 'data.setInteger("maxSteam", this.steam.getMaxFill());', 232: 'data.setShort("type", (short)this.steam.getTankType().getID());', 238: "return new FluidTank[] {feed, steam};", 243: "return new FluidTank[] {steam};", 248: "return new FluidTank[] {feed};",
                     333: 'PREFIX_VALUE + "feed"', 334: 'PREFIX_VALUE + "steam"', 335: 'PREFIX_VALUE + "consumption"', 341: 'return "" + this.feed.getFill();', 342: 'return "" + this.steam.getFill();', 343: 'return "" + this.consumption;'})
    order = [202, 205, 208, 212, 217]
    ck("V1.boiler-melt-console-ror", not m and order == sorted(order) and "super.getNBTForConsole" not in ov.b["boi.console"], "TileEntityRBMKBoiler.java:199-248, :330-345: onMelt BLANK debris 1 + rand(2), then (overpressure dial and out ports) the nets of the steam provider "
       "nodes at every out-port connection join the pipe set, then super.onMelt; console BOILER water/maxWater/steam/maxSteam ints and short type; tanks {feed, steam}, sending {steam}, receiving {feed}; RoR feed / steam / consumption", m)
    # ---- TileEntityRBMKBase.java: overpressure and ports
    t = L["base"]
    m = at_lines(t, {434: "public static HashSet<TileEntityRBMKBase> columns = new HashSet<>();", 435: "public static HashSet<FluidNetMK2> pipes = new HashSet<>();", 443: "columns.clear();", 444: "pipes.clear();", 474: "rbmk.onMelt(minDist + 1);",
                     501: "if(RBMKDials.getOverpressure(worldObj) && !pipes.isEmpty()) {", 502: "HashSet<FluidNode> pipeBlocks = new HashSet<>();", 503: "HashSet<IFluidReceiverMK2> pipeReceivers = new HashSet<>();", 507: "pipeBlocks.addAll(x.links);",
                     508: "pipeReceivers.addAll(x.receiverEntries);", 511: "int count = 0;", 512: "int max = Math.min(pipeBlocks.size() / 5, 100);", 516: "while(itPipes.hasNext() && count < max) {", 518: "for (BlockPos pos : node.positions) {",
                     520: "if (worldObj.getTileEntity(x, y ,z) != null) {", 521: "worldObj.setBlock(x, y, z, Blocks.air);", 524: "count++;", 527: "while(itReceivers.hasNext()) {", 529: "if(con instanceof TileEntity) {", 531: "if(con instanceof IOverpressurable) {",
                     532: "((IOverpressurable) con).explode(worldObj, tile.xCoord, tile.yCoord, tile.zCoord);", 534: "worldObj.setBlock(tile.xCoord, tile.yCoord, tile.zCoord, Blocks.air);",
                     535: "worldObj.newExplosion(null, tile.xCoord + 0.5, tile.yCoord + 0.5, tile.zCoord + 0.5, 5F, false, false);", 541: "int smallDim = Math.min(maxX - minX, maxZ - minZ);"})
    order = [443, 474, 477, 501, 512, 516, 527, 535, 541]
    ck("V1.base-overpressure", not m and order == sorted(order), "TileEntityRBMKBase.java:434-539: pipes collected during onMelt (before), cleared at the start, the overpressure branch AFTER the corium/pribris step: union of links and receiverEntries, "
       "max = min(links / 5, 100), the first `max` link nodes lose the blocks that have a tile entity, EVERY receiver that is a tile entity explodes (IOverpressurable.explode, else air + newExplosion 5F, no fire, no terrain damage)", m)
    m = at_lines(t, {612: "protected PortDef[] portShapeNoLoader;", 616: "PortDef.make(xCoord, yCoord + RBMKDials.getColumnHeight(worldObj), zCoord, Library.POS_Y),", 617: "PortDef.make(xCoord, yCoord, zCoord, Library.NEG_Y),",
                     627: "PortDef.make(xCoord, yCoord + RBMKDials.getColumnHeight(worldObj), zCoord, Library.POS_Y),", 628: "PortDef.make(xCoord, yCoord - 1, zCoord, ForgeDirection.VALID_DIRECTIONS),",
                     638: "PortDef.make(xCoord, yCoord + RBMKDials.getColumnHeight(worldObj), zCoord, Library.POS_Y),", 639: "PortDef.make(xCoord, yCoord, zCoord, Library.NEG_Y),", 640: "PortDef.make(xCoord, yCoord - 2, zCoord, ForgeDirection.VALID_DIRECTIONS),"})
    ck("V1.base-ports", not m, "TileEntityRBMKBase.java:612-644 port layouts: no loader = top (y + columnHeight, UP) and (y, DOWN); close loader = top and the six directions at (y - 1); classic loader = top, (y, DOWN) and the six directions at (y - 2)", m)
    # ---- RBMKNeutronHandler.java: the CONTROL_ROD branch and the tail
    t = L["rnh"]
    m = at_lines(t, {252: "NeutronNode node = streamWorld.getNode(pos);", 332: "} else if(type == RBMKType.CONTROL_ROD) {", 333: "TileEntityRBMKControl rod = (TileEntityRBMKControl) nodeTE;", 335: "if(rod.level > 0.0D) {", 337: "this.fluxQuantity *= rod.getMult();",
                     338: "continue;", 340: "return;", 341: "} else if(type == RBMKType.REFLECTOR) {", 377: "RBMKType lastNodeType = (RBMKType) lastNode.data.get(\"type\");", 379: "if(lastNodeType == RBMKType.CONTROL_ROD) {",
                     380: "TileEntityRBMKControl rod = (TileEntityRBMKControl) lastNode.tile;", 381: "if(rod.getMult() > 0.0D) {", 382: "this.fluxQuantity *= rod.getMult();",
                     383: "BlockPos posAfter = new BlockPos(lastNode.tile.xCoord + this.vector.xCoord, lastNode.tile.yCoord, lastNode.tile.zCoord + this.vector.zCoord);", 387: "if(NeutronNodeWorld.getNode(worldObj, pos) == null) {", 388: "TileEntity te = blockPosToTE(worldObj, posAfter);",
                     390: "RBMKNeutronNode nodeAfter = makeNode(NeutronNodeWorld.getOrAddWorld(worldObj), (TileEntityRBMKBase) te);", 391: "NeutronNodeWorld.getOrAddWorld(worldObj).addNode(nodeAfter);", 393: "irradiateFromFlux(posAfter); // I'm so mad about this..."})
    order = [307, 312, 332, 341, 357]
    ck("V1.neutron-control", not m and order == [307, 312, 332, 341, 357], "RBMKNeutronHandler.java:332-340: CONTROL_ROD branch after the flux-receiver block and before REFLECTOR: level > 0 -> flux *= getMult() and continue, else return; "
       ":377-397 the tail: last node CONTROL_ROD with getMult() > 0 multiplies the flux and the #1933 check `NeutronNodeWorld.getNode(worldObj, pos) == null` tests the stream ORIGIN pos (:252), not posAfter", m)
    # ---- GUIs
    t = L["gctl"]
    m = at_lines(t, {28: "this.xSize = 176;", 29: "this.ySize = 186;", 21: "gui_rbmk_control.png", 36: "guiLeft + 71, guiTop + 29, 16, 56, mouseX, mouseY, new String[]{ (int)(rod.level * 100) + \"%\" }", 50: "if(guiLeft + 118 <= x && guiLeft + 118 + 30 > x && guiTop + 26 + k * 11 < y && guiTop + 26 + 10 + k * 11 >= y) {",
                     54: 'data.setDouble("level", 1.0D - (k * 0.25D));', 59: "if(guiLeft + 28 <= x && guiLeft + 28 + 12 > x && guiTop + 26 + k * 11 < y && guiTop + 26 + 10 + k * 11 >= y) {", 63: 'data.setInteger("color", k);', 73: "this.xSize / 2 - this.fontRendererObj.getStringWidth(name) / 2, 6, 4210752",
                     74: "8, this.ySize - 96 + 2, 4210752", 83: "int height = (int)(56 * (1D - rod.level));", 86: "drawTexturedModalRect(guiLeft + 75, guiTop + 29, 176, 56 - height, 8, height);", 91: "drawTexturedModalRect(guiLeft + 28, guiTop + 26 + color * 11, 184, color * 10, 12, 10);"})
    ck("V1.gui-control", not m, "GUIRBMKControl.java: 176 x 186, tooltip (71, 29, 16, 56) of (int)(level * 100) + \"%\", five level buttons x 118..148 / y 26 + k * 11 sending `level` 1 - 0.25k, five colour buttons x 28..40 sending `color` k, rod bar (75, 29) from (176, 56 - h) "
       "with h = (int)(56 * (1 - level)), selected colour (28, 26 + c * 11) from (184, c * 10) 12 x 10, labels at y 6 and ySize - 96 + 2", m)
    t = L["gaut"]
    m = at_lines(t, {25: "gui_rbmk_control_auto.png", 36: "this.xSize = 176;", 37: "this.ySize = 186;", 45: "new GuiTextField(this.fontRendererObj, guiLeft + 30, guiTop + 27 + 11 * i, 26, 6);", 48: "setEnableBackgroundDrawing(false);", 51: "setMaxStringLength(3);",
                     53: "setMaxStringLength(4);", 56: "this.fields[0].setText(String.valueOf((int)rod.levelUpper));", 57: "this.fields[1].setText(String.valueOf((int)rod.levelLower));", 58: "this.fields[2].setText(String.valueOf((int)rod.heatUpper));",
                     59: "this.fields[3].setText(String.valueOf((int)rod.heatLower));", 66: "guiLeft + 124, guiTop + 29, 16, 56", 80: "guiLeft + 58, guiTop + 26, 28, 19", 81: "guiLeft + 61, guiTop + 48, 22, 10", 82: "guiLeft + 61, guiTop + 59, 22, 10", 83: "guiLeft + 61, guiTop + 70, 22, 10",
                     85: "guiLeft + 28, guiTop + 26, 30, 10", 86: "guiLeft + 28, guiTop + 37, 30, 10", 87: "guiLeft + 28, guiTop + 48, 30, 10", 88: "guiLeft + 28, guiTop + 59, 30, 10", 89: "guiLeft + 28, guiTop + 70, 30, 10",
                     100: "if(guiLeft + 28 <= x && guiLeft + 28 + 30 > x && guiTop + 70 < y && guiTop + 70 +10 >= y) {", 109: "double clamp = k < 2 ? 100 : 9999;", 111: "if(NumberUtils.isNumber(fields[k].getText())) {",
                     112: "int j = (int)MathHelper.clamp_double(Double.parseDouble(fields[k].getText()), 0, clamp);", 116: 'fields[k].setText("0");', 120: 'data.setDouble("levelUpper", vals[0]);', 121: 'data.setDouble("levelLower", vals[1]);',
                     122: 'data.setDouble("heatUpper", vals[2]);', 123: 'data.setDouble("heatLower", vals[3]);', 131: "if(guiLeft + 61 <= x && guiLeft + 61 + 22 > x && guiTop + 48 + k * 11 < y && guiTop + 48 + 10 + k * 11 >= y) {",
                     135: 'data.setInteger("function", k);', 155: "int height = (int)(56 * (1D - rod.level));", 158: "drawTexturedModalRect(guiLeft + 124, guiTop + 29, 176, 56 - height, 8, height);", 160: "int f = rod.function.ordinal();",
                     161: "drawTexturedModalRect(guiLeft + 59, guiTop + 27, 184, f * 19, 26, 19);"})
    ck("V1.gui-control-auto", not m, "GUIRBMKControlAuto.java: 176 x 186, four text fields at (30, 27 + 11i, 26 x 6) with max length 3, 3, 4, 4 holding levelUpper, levelLower, heatUpper, heatLower, tooltips at (124, 29, 16, 56), (58, 26, 28, 19), (61, 48 / 59 / 70, 22, 10), "
       "(28, 26 / 37 / 48 / 59 / 70, 30, 10), save button (28, 70, 30 x 10) clamping 0..100 and 0..9999 and sending four doubles, function buttons (61, 48 + 11k, 22 x 10) sending `function` k, level bar (124, 29), function icon (59, 27) from (184, f * 19) 26 x 19", m)
    t = L["gboi"]
    m = at_lines(t, {22: "gui_rbmk_boiler.png", 29: "this.xSize = 176;", 30: "this.ySize = 186;", 37: "guiLeft + 126, guiTop + 24, 16, 56", 38: "guiLeft + 89, guiTop + 39, 8, 28", 45: "if(guiLeft + 33 <= x && guiLeft + 33 + 20 > x && guiTop + 21 < y && guiTop + 21 + 64 >= y) {",
                     49: 'data.setBoolean("compression", true);', 68: "int i = boiler.feed.getFill() * 58 / boiler.feed.getMaxFill();", 69: "drawTexturedModalRect(guiLeft + 126, guiTop + 82 - i, 176, 58 - i, 14, i);", 71: "int j = boiler.steam.getFill() * 22 / boiler.steam.getMaxFill();",
                     73: "if(j > 0) j++;", 74: "if(j > 22) j++;", 76: "drawTexturedModalRect(guiLeft + 91, guiTop + 65 - j, 190, 24 - j, 4, j);", 79: "194, 0, 14, 58);", 80: "208, 0, 14, 58);", 81: "222, 0, 14, 58);", 82: "236, 0, 14, 58);"})
    ck("V1.gui-boiler", not m, "GUIRBMKBoiler.java: 176 x 186, feed tooltip (126, 24, 16, 56), steam tooltip (89, 39, 8, 28), compression button x 33..53 / y 21..85 sending `compression` true, feed bar i = fill * 58 / max at (126, 82 - i) from (176, 58 - i) 14 x i, "
       "steam bar j = fill * 22 / max with j++ when > 0 and again when > 22 at (91, 65 - j) from (190, 24 - j) 4 x j, type icon (36, 24) 14 x 58 from u 194 / 208 / 222 / 236", m)
    t = L["ghea"]
    m = at_lines(t, {16: "gui_rbmk_heater.png", 23: "this.xSize = 176;", 24: "this.ySize = 186;", 31: "guiLeft + 68, guiTop + 24, 16, 58", 32: "guiLeft + 126, guiTop + 24, 16, 58", 49: "rod.feed.renderTank(guiLeft + 68, guiTop + 82, this.zLevel, 14, 58);",
                     50: "rod.steam.renderTank(guiLeft + 126, guiTop + 82, this.zLevel, 14, 58);", 54: "drawTexturedModalRect(guiLeft + 72, guiTop + 72, 176, 0, 10, 10);", 55: "drawTexturedModalRect(guiLeft + 130, guiTop + 72, 186, 0, 10, 10);"})
    ck("V1.gui-heater", not m, "GUIRBMKHeater.java: 176 x 186, feed tank (68, 24, 16 x 58), steam tank (126, 24, 16 x 58), renderTank 14 x 58 at y + 82, icons (72, 72) from (176, 0) and (130, 72) from (186, 0), both 10 x 10", m)
    # ---- TileEntityRBMKHeater.java
    t = L["hea"]
    m = at_lines(t, {34: "public FluidTank feed;", 35: "public FluidTank steam;", 40: "super(1);", 41: "this.feed = new FluidTank(Fluids.COOLANT, 16_000);", 42: "this.steam = new FluidTank(Fluids.COOLANT_HOT, 16_000);", 49: 'return "container.rbmkHeater";',
                     57: "ports.update(worldObj.getBlock(xCoord, yCoord - 2, zCoord) == ModBlocks.rbmk_loader ? this.getPortsClassicLoader() :", 60: "if(this.heat <= 50 || this.feed.getFill() <= 0) feed.setType(0, slots);", 62: "if(feed.getTankType().hasTrait(FT_Heatable.class)) {",
                     64: "HeatingStep step = trait.getFirstStep();", 65: "steam.setTankType(step.typeProduced);", 66: "double tempRange = this.heat - steam.getTankType().temperature;", 67: "double eff = trait.getEfficiency(HeatingType.HEATEXCHANGER);",
                     69: "if(tempRange > 0 && eff > 0) {", 70: "double TU_PER_DEGREE = 2_000D * eff;", 71: "int inputOps = feed.getFill() / step.amountReq;", 72: "int outputOps = (steam.getMaxFill() - steam.getFill()) / step.amountProduced;",
                     73: "int tempOps = (int) Math.floor((tempRange * TU_PER_DEGREE) / step.heatReq);", 74: "int ops = Math.min(inputOps, Math.min(outputOps, tempOps));", 76: "feed.setFill(feed.getFill() - step.amountReq * ops);", 77: "steam.setFill(steam.getFill() + step.amountProduced * ops);",
                     78: "this.heat -= (step.heatReq * ops / TU_PER_DEGREE) * trait.getEfficiency(HeatingType.HEATEXCHANGER);", 81: "if(eff <= 0) {", 82: "feed.setTankType(Fluids.NONE);", 83: "steam.setTankType(Fluids.NONE);", 86: "} else {",
                     87: "feed.setTankType(Fluids.NONE);", 88: "steam.setTankType(Fluids.NONE);", 92: "super.updateEntity();"})
    order = [57, 60, 62, 69, 76, 77, 78, 81, 86, 92]
    ck("V1.heater-tick", not m and order == sorted(order), "TileEntityRBMKHeater.java:34-93: one slot, COOLANT 16,000 / COOLANT_HOT 16,000, ports, the feed type follows slot 0 when heat <= 50 or the feed is empty, a heatable feed picks the first step, "
       "tempRange = heat - hot temperature, TU_PER_DEGREE = 2000 * efficiency, ops = min(feed / amountReq, free / amountProduced, floor(tempRange * TU / heatReq)), heat -= (heatReq * ops / TU) * efficiency, both tanks NONE for efficiency <= 0 or no FT_Heatable", m)
    m = at_lines(t, {99: 'feed.readFromNBT(nbt, "feed");', 100: 'steam.readFromNBT(nbt, "steam");', 107: 'feed.writeToNBT(nbt, "feed");', 108: 'steam.writeToNBT(nbt, "steam");', 114: "this.feed.serialize(buf);", 115: "this.steam.serialize(buf);", 128: "int count = 1 + worldObj.rand.nextInt(2);",
                     131: "spawnDebris(DebrisType.BLANK);", 134: "super.onMelt(reduce);", 139: "return ColumnType.HEATEX;", 145: 'data.setInteger("water", this.feed.getFill());', 148: 'data.setInteger("maxSteam", this.steam.getMaxFill());', 149: 'data.setShort("type", (short)this.feed.getTankType().getID());',
                     150: 'data.setShort("hottype", (short)this.steam.getTankType().getID());', 244: 'PREFIX_VALUE + "in"', 245: 'PREFIX_VALUE + "out"', 251: 'return "" + this.feed.getFill();', 252: 'return "" + this.steam.getFill();'})
    ck("V1.heater-nbt-melt-console", not m and "super.getNBTForConsole" not in ov.b["hea.console"], "TileEntityRBMKHeater.java:95-152: NBT feed and steam, serialize feed THEN steam, onMelt BLANK 1 + rand(2) then super.onMelt, console HEATEX water/maxWater/steam/maxSteam ints and shorts type (feed) and hottype (steam); RoR in / out", m)
    # ---- TileEntityRBMKCooler.java
    t = L["coo"]
    m = at_lines(t, {25: "protected int timer = 0;", 27: "protected TileEntityRBMKBase[] neighborCache = new TileEntityRBMKBase[25];", 35: "this.tanks[0] = new FluidTank(Fluids.PERFLUOROMETHYL_COLD, 4_000);", 36: "this.tanks[1] = new FluidTank(Fluids.PERFLUOROMETHYL, 4_000);",
                     46: "ports.update(worldObj.getBlock(xCoord, yCoord - 2, zCoord) == ModBlocks.rbmk_loader ? this.getPortsClassicLoader() :", 49: "if(timer <= 0) {", 50: "timer = 60;", 52: "for(int i = 0; i < 25; i++) {", 53: "int x = xCoord - 2 + i / 5;", 54: "int z = zCoord - 2 + i % 5;",
                     55: "TileEntity tile = Compat.getTileStandard(worldObj, x, yCoord, z);", 64: "timer--;", 67: "if(tanks[0].getFill() >= 50 && tanks[1].getMaxFill() - tanks[1].getFill() >= 50) {", 68: "tanks[0].setFill(tanks[0].getFill() - 50);",
                     69: "tanks[1].setFill(tanks[1].getFill() + 50);", 73: "neighbor.heat -= 200;", 74: "if(neighbor.heat < 20) neighbor.heat = 20;", 80: "super.updateEntity();", 87: 'tanks[0].readFromNBT(nbt, "t0");', 88: 'tanks[1].readFromNBT(nbt, "t1");',
                     95: 'tanks[0].writeToNBT(nbt, "t0");', 96: 'tanks[1].writeToNBT(nbt, "t1");', 102: "this.tanks[0].serialize(buf);", 103: "this.tanks[1].serialize(buf);", 113: "return ColumnType.COOLER;", 116: "return new FluidTank[] {tanks[0]};", 117: "return new FluidTank[] {tanks[1]};"})
    order = [46, 49, 52, 64, 67, 73, 74, 80]
    ck("V1.cooler", not m and order == sorted(order) and "getNBTForConsole" not in inp.o["coo"], "TileEntityRBMKCooler.java:25-117: tanks PERFLUOROMETHYL_COLD 4,000 and PERFLUOROMETHYL 4,000, a 60-tick timer, the 5 x 5 scan x - 2 + i / 5, z - 2 + i % 5 at the cooler's y (including itself), "
       "when t0 >= 50 and t1 has 50 free: move 50 mB and every cached neighbour loses 200 heat down to 20; NBT t0 / t1; console COOLER with no own getNBTForConsole; receiving {t0}, sending {t1}", m)
    # ---- ParticleRBMKSteam.java, ClientProxy
    t = L["part"]
    m = at_lines(t, {22: "textures/particle/rbmk_jet_steam.png", 28: "this.particleMaxAge = 10;", 29: "this.particleAlpha = 0.25F;", 30: "this.particleScale = 4F;", 53: "if(this.particleAge > this.particleMaxAge)", 54: "this.particleAge = this.particleMaxAge;",
                     56: "int texIndex = (int) (((double) this.particleAge / (double) this.particleMaxAge) * 20) % 20 - 1;", 57: "float f0 = 1F / 20F;", 67: "tess.setBrightness(240);", 50: "GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE);", 49: "GL11.glDepthMask(false);",
                     83: "tess.addVertexWithUV(this.particleScale * -0.25 - 0.9375, -0.25, 0, uMax, vMax);", 84: "tess.addVertexWithUV(this.particleScale * -0.25 - 0.9375, this.particleScale - 0.25, 0, uMax, vMin);",
                     85: "tess.addVertexWithUV(this.particleScale * 0.25 - 0.9375, this.particleScale - 0.25, 0, uMin, vMin);", 86: "tess.addVertexWithUV(this.particleScale * 0.25 - 0.9375, -0.25, 0, uMin, vMax);"})
    cp = inp.ol["cproxy"]
    m += at_lines(cp, {1718: 'if("rbmksteam".equals(type)) {', 1719: "Minecraft.getMinecraft().effectRenderer.addEffect(new ParticleRBMKSteam(man, world, x, y, z));"})
    ck("V1.particle", not m, "ParticleRBMKSteam.java:20-100: max age 10, alpha 0.25, scale 4, additive blending (SRC_ALPHA, ONE) without depth write, full brightness 240, a 20-frame strip with the frame index floor(age / maxAge * 20) % 20 - 1, quad from "
       "scale * -0.25 - 0.9375 to scale * 0.25 - 0.9375 and y -0.25 to scale - 0.25 with uMax at the left edge; ClientProxy.java:1718-1720 spawns it for the `rbmksteam` effect type", m)
    # ---- recipes and anvil rows
    cm = L["cm"]
    m = at_lines(cm, {759: "if(!GeneralConfig.enable528) {", 763: "} else {", 771: "ModBlocks.rbmk_loader", 987: "if(!GeneralConfig.enable528) {", 996: "}"})
    rows = {}
    for n in (760, 761, 762, 771, 993, 994, 995):
        rows[n] = parse_cm_row(cm[n - 1])
    want = {760: ("rbmk_control", 1, [" B ", "GRG", " B "], {"G": "GRAPHITE.ingot()", "B": "ModItems.motor", "R": "ModBlocks.rbmk_absorber"}),
            761: ("rbmk_control_mod", 1, ["BGB", "GRG", "BGB"], {"G": "GRAPHITE.block()", "R": "ModBlocks.rbmk_control", "B": "ModItems.nugget_bismuth"}),
            762: ("rbmk_control_auto", 1, ["C", "R", "D"], {"C": "DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ADVANCED)", "R": "ModBlocks.rbmk_control", "D": "ModItems.crt_display"}),
            771: ("rbmk_loader", 1, ["SCS", "CBC", "SCS"], {"S": "STEEL.plate()", "C": "CU.ingot()", "B": "ModItems.tank_steel"}),
            993: ("rbmk_boiler", 1, ["CPC", "CRC", "CPC"], {"C": "CU.pipe()", "P": "CU.shell()", "R": "ModBlocks.rbmk_blank"}),
            994: ("rbmk_heater", 1, ["CIC", "PRP", "CIC"], {"C": "CU.pipe()", "P": "STEEL.shell()", "R": "ModBlocks.rbmk_blank", "I": "ANY_PLASTIC.ingot()"}),
            995: ("rbmk_cooler", 1, ["IGI", "GCG", "IGI"], {"C": "ModBlocks.rbmk_blank", "I": "ModItems.plate_polymer", "G": "ModBlocks.steel_grate"})}
    ck("V1.recipe-rows", not m and rows == want and all("}" != x.strip() for x in cm[987:992]) and all("}" != x.strip() and "else" not in x for x in cm[759:762]),
       "CraftingManager.java: :760 rbmk_control, :761 rbmk_control_mod (GRAPHITE.block()), :762 rbmk_control_auto inside the !enable528 branch opened at :759; :771 rbmk_loader outside it; :993-995 rbmk_boiler, rbmk_heater, rbmk_cooler inside the "
       "!enable528 branch opened at :987; shapes and ingredients as the six builders must carry them", (m, {k: v for k, v in rows.items() if v != want[k]}))
    inp.recipe_rows = rows
    ar = parse_anvil_rows(inp.o["ar"], 868, 953)
    five = {k: ar.get(k) for k in ("rbmk_control", "rbmk_control_mod", "rbmk_control_auto", "rbmk_boiler", "rbmk_cooler")}
    ok = all(v is not None and v[0] == 4 and v[1] for v in five.values()) and "rbmk_heater" not in inp.o["ar"] and "rbmk_loader" not in inp.o["ar"]
    anvil_lines = at_lines(L["ar"], {885: "new ComparableStack(ModBlocks.rbmk_control)", 889: "}).setTier(4));", 891: "new ComparableStack(ModBlocks.rbmk_control_mod)", 895: "}).setTier(4));", 897: "new ComparableStack(ModBlocks.rbmk_control_auto)",
                                     901: "}).setTier(4));", 927: "if(!GeneralConfig.enable528) {", 941: "new ComparableStack(ModBlocks.rbmk_boiler)", 945: "}).setTier(4));", 947: "new ComparableStack(ModBlocks.rbmk_cooler)", 951: "}).setTier(4));"})
    ck("V1.anvil-rows", ok and not anvil_lines,
       "AnvilRecipes.java:868-953: rbmk_control, rbmk_control_mod, rbmk_control_auto (:884-901) and rbmk_boiler, rbmk_cooler (:940-951) are tier-4 RECYCLING rows (a column in, its parts out); there is no row for rbmk_heater or rbmk_loader", five)
    inp.anvil_rows = five
    # ---- language
    en, zh = inp.o_en, inp.o_zh
    bad = []
    for neo, orig, e, z, le, lz in UP_ALL:
        if not (len(en.get(orig, [])) == 1 and len(zh.get(orig, [])) == 1 and en[orig][0][0] == e and zh[orig][0][0] == z and (en[orig][0][1], zh[orig][0][1]) == (le, lz)):
            bad.append((orig, en.get(orig), zh.get(orig)))
    ck("V1.lang", not bad and len(UP_ALL) == 47 and len(set(u[0] for u in UP_ALL)) == 47, "the 47 upstream keys of both handoffs (21 control, 26 steam) sit once each at the cited en_US.lang / zh_CN.lang lines with the handoffs' texts", bad[:3])
    # ---- resources
    ck("V1.resources", len(inp.o_res) == len(IMPORTS) and inp.o_particle is not None and all(inp.o_not_imported.values()) and len(IMPORTS_A) == 21 and len(IMPORTS_B) == 25,
       "the 46 files to import (21 control, 25 steam), the particle texture and the files to leave out (rbmk_control.png, rbmk_control_base.png, the ten ReaSim control textures) exist in the original",
       [k for k, v in inp.o_not_imported.items() if not v] + [k for _, k in IMPORTS if RES + k not in inp.o_res])


# ---------------------------------------------------------------- V2 control rods against V1

# 1.7.10 -> 1.21.1 renames applied to the squashed original before the per-method rules below
RC = [
    (r"TileEntityRBMKControlManual", "RBMKControlManualBlockEntity"), (r"TileEntityRBMKControlAuto", "RBMKControlAutoBlockEntity"), (r"TileEntityRBMKControl", "RBMKControlBlockEntity"),
    (r"TileEntityRBMKBoiler", "RBMKBoilerBlockEntity"), (r"TileEntityRBMKHeater", "RBMKHeaterBlockEntity"), (r"TileEntityRBMKCooler", "RBMKCoolerBlockEntity"), (r"TileEntityRBMKBase", "RBMKBaseBlockEntity"),
    (r"TileEntity", "BlockEntity"), (r"NBTTagCompound", "CompoundTag"), (r"MathHelper\.clamp_(?:double|int)", "Mth.clamp"),
    (r"super\.readFromNBT\(nbt\);", "super.loadAdditional(tag,registries);"), (r"super\.writeToNBT\(nbt\);", "super.saveAdditional(tag,registries);"), (r"(?<![\w.])nbt\.", "tag."),
    (r"\.setDouble\(", ".putDouble("), (r"\.setInteger\(", ".putInt("), (r"\.getInteger\(", ".getInt("), (r"\.hasKey\(", ".contains("), (r"\.setShort\(", ".putShort("), (r"\.setBoolean\(", ".putBoolean("),
    (r"\.setString\(", ".putString("), (r"RBMKDials\.(\w+)\(worldObj\)", r"RBMKDials.\1()"),
]
NEO_SIG = {
    "update": "public void updateEntity()", "lid": "public boolean isLidRemovable()", "type": "public RBMKType getRBMKType()", "setTarget": "public void setTarget(double target)", "getMult": "public double getMult()",
    "track": "public int trackingRange()", "read": "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)", "write": "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)",
    "serialize": "public void serialize(RegistryFriendlyByteBuf buf)", "deserialize": "public void deserialize(RegistryFriendlyByteBuf buf)", "onMelt": "public void onMelt(int reduce)",
    "console": "public CompoundTag getNBTForConsole()", "info": "public String[] getFunctionInfo()", "ror": "public String provideRORValue(String name)", "run": "public String runRORFunction(String name, String[] params)",
    "perm": "public boolean hasPermission(Player player)", "receive": "public void receiveControl(CompoundTag data)", "getSettings": "public CompoundTag getSettings(Level world, BlockPos pos)",
    "paste": "public void pasteSettings(CompoundTag nbt, int index, Level world, Player player, BlockPos pos)", "ctype": "public RBMKColumnType getConsoleType()",
}


def neo_body(st, path, key):
    return body(st.text(path), NEO_SIG[key])


def ob(inp, key, rules=(), extra=()):
    """The squashed original body of key with the renames of RC (plus the given extra rules before them) applied."""
    return rewrite(need_ov(inp).b[key], list(extra) + RC + list(rules))


def cmp_group(ck, cid, label, inp, st, path, items):
    """items: (original key, NEO key, prefix, extra rules before RC, rules after RC). All must be equal."""
    bad = {}
    for okey, nkey, prefix, pre, post in items:
        try:
            a, b = prefix + ob(inp, okey, post, pre), neo_body(st, path, nkey)
        except ValueError as error:
            bad[nkey] = repr(error)
            continue
        if not a or a != b:
            bad[nkey] = first_diff(a, b)
    return ck(cid, not bad, label, bad)


def piece(s, start, end=None):
    i = s.index(start)
    return s[i:] if end is None else s[i:s.index(end, i)]


def v2_control(ck, inp, st):
    ov = need_ov(inp)
    txt = {p: lf(st.text(p)) for p in (CTL, MAN, AUT)}
    code = {p: code_of(t) for p, t in txt.items()}
    iso = [p for p in txt if re.search(r"net\.minecraft\.client|com\.hbm\.render|inventory\.screens", txt[p])]
    ck("V2.classes", all(st.has(p) for p in (CTL, MAN, AUT)) and "abstractclassRBMKControlBlockEntityextendsRBMKSlottedBaseBlockEntityimplementsIRORValueProvider{" in code[CTL]
       and "super(type,pos,state,0);" in code[CTL] and "classRBMKControlManualBlockEntityextendsRBMKControlBlockEntityimplementsIControlReceiver,ICopiable,IRORInteractive{" in code[MAN]
       and "classRBMKControlAutoBlockEntityextendsRBMKControlBlockEntityimplementsIControlReceiver,ICopiable{" in code[AUT] and not iso
       and not any("IRBMKFluxReceiver" in c for c in code.values()) and not any("IEnergyReceiverMK2" in c for c in code.values()),
       "RBMKControlBlockEntity is abstract over the zero-slot slotted base (original SlottedBase(0)) with RoR values; the manual rod is IControlReceiver + ICopiable + IRORInteractive, the auto rod IControlReceiver + ICopiable; none is an "
       "IRBMKFluxReceiver (the CONTROL_ROD branch must stay reachable, as in the original), none a ReaSim energy receiver, none imports a client or render class", iso)
    # ---- the shared control block entity
    speed = re.search(r"speed = ([0-9.]+)D;", inp.o["ctl"])
    fields = [f"publicdoublelastLevel;", "publicdoublelevel;", f"publicstaticfinaldoublespeed={speed[1]}D;", "publicdoubletargetLevel;"] if speed else ["?"]
    ck("V2.control-fields", all(f in code[CTL] for f in fields) and speed is not None and speed[1] == "0.00277", f"RBMKControlBlockEntity has lastLevel, level, targetLevel and speed = {speed and speed[1]} (TileEntityRBMKControl.java:29-32)", [f for f in fields if f not in code[CTL]])
    o_update = ov.b["ctl.update"]
    step = rewrite(piece(o_update, "if(level<targetLevel){", "if(this.isPowered()&&level!=lastLevel)"), RC)
    client = rewrite(o_update[:o_update.index("}else{")], [lit("if(worldObj.isRemote){", "if(world.isClientSide){")])
    want = "Levelworld=this.getLevel();if(world==null)return;" + client + "}else{this.lastLevel=this.level;" + step + "if(level!=lastLevel)this.setChanged();}super.updateEntity();"
    got = neo_body(st, CTL, "update")
    ok_pre = "this.lastLevel=this.level;if(this.hasPower){" + piece(o_update, "if(level<targetLevel){", "if(this.isPowered()&&level!=lastLevel)").replace("(worldObj)", "(worldObj)") in o_update
    eq(ck, "V2.control-tick", "RBMKControlBlockEntity.updateEntity equals the original :76-112: the client only copies lastLevel = level, the server sets lastLevel = level, moves the level by speed * getControlSpeed() towards the target with the clamp in both "
       "directions (:95-103) and calls the parent tick last; NEO additionally marks the chunk when the level moved", want if ok_pre else "", got)
    cmp_group(ck, "V2.control-methods", "setTarget, getMult (= level), isLidRemovable (false), trackingRange (100) and getRBMKType (CONTROL_ROD) equal the original bodies (:59-62, :114-125, :188-191)", inp, st, CTL,
              [("ctl.setTarget", "setTarget", "", (), ()), ("ctl.getMult", "getMult", "", (), ()), ("ctl.lid", "lid", "", (), ()), ("ctl.track", "track", "", (), ()), ("ctl.type", "type", "", (), ())])
    cmp_group(ck, "V2.control-nbt", "load/saveAdditional equal the original read/writeToNBT (keys level and targetLevel, :127-141)", inp, st, CTL, [("ctl.read", "read", "", (), ()), ("ctl.write", "write", "", (), ())])
    drop = lambda s: s.replace("buf.writeLong(this.power);buf.writeBoolean(this.hasPower);", "").replace("this.power=buf.readLong();this.hasPower=buf.readBoolean();", "")  # noqa: E731
    bad = {}
    for okey, nkey in (("ctl.serialize", "serialize"), ("ctl.deserialize", "deserialize")):
        a, b = drop(ob(inp, okey)), neo_body(st, CTL, nkey)
        if not a or a != b or ("power" in b):
            bad[nkey] = first_diff(a, b)
    ck("V2.control-sync", not bad, "serialize/deserialize equal the original (:143-159) without power and hasPower (the ReaSim part): level then targetLevel, symmetric", bad)
    melt_a = "Levelworld=this.getLevel();" + ob(inp, "ctl.onMelt", extra=[(r"worldObj\.rand\.", "world.random.")])
    eq(ck, "V2.control-melt", "onMelt equals the original :167-186: GRAPHITE 2 + rand(2) when moderated, ROD 2 + rand(2), standardMelt; no super.onMelt (no lid debris)", melt_a, neo_body(st, CTL, "onMelt"))
    cons = ob(inp, "ctl.console").replace("CompoundTagdata=newCompoundTag();", "CompoundTagdata=super.getNBTForConsole();")
    eq(ck, "V2.control-console", "getNBTForConsole is the original's level / targetLevel on top of the NEO base data (24C convention: super + keys)", cons, neo_body(st, CTL, "console"))
    cmp_group(ck, "V2.control-ror", "getFunctionInfo and provideRORValue equal the original (value `extraction` = (int)(level * 100), :246-257)", inp, st, CTL, [("ctl.info", "info", "", (), ()), ("ctl.ror", "ror", "", (), ())])
    # ---- manual rod
    cmp_group(ck, "V2.manual-surge", "setTarget and getMult of the manual rod equal the original token for token (:46-62: sin(pow(1 - level, 15) * PI) * (startingLevel - target) * getSurgeMod when target < startingLevel and |level - target| > 0.01)",
              inp, st, MAN, [("man.setTarget", "setTarget", "", (), ()), ("man.getMult", "getMult", "", (), ())])
    perm_pre = [lit("returnVec3.createVectorHelper(xCoord-player.posX,yCoord-player.posY,zCoord-player.posZ).lengthVector()<20;",
                    "BlockPospos=this.getBlockPos();returnnewVec3(pos.getX()-player.getX(),pos.getY()-player.getY(),pos.getZ()-player.getZ()).length()<20;")]
    cmp_group(ck, "V2.permission", "hasPermission of both rods measures the block corner (:64-67 and :34-37), < 20", inp, st, MAN, [("man.perm", "perm", "", (), perm_pre)])
    cmp_group(ck, "V2.permission-auto", "the automatic rod's hasPermission equals the original", inp, st, AUT, [("aut.perm", "perm", "", (), perm_pre)])
    recv = neo_body(st, MAN, "receive")
    o_recv = ov.b["man.receive"]
    toggle = rewrite(piece(o_recv, "RBMKColornewCol="), RC)
    toggle = toggle.replace("this.markDirty();", "this.setChanged();")
    want_color = 'if(data.contains("color")){intc=Math.abs(data.getInt("color")%RBMKColor.values().length);' + toggle
    ck("V2.manual-receive", 'if(data.contains("level")){doubletarget=data.getDouble("level");if(Double.isFinite(target)&&target>=0&&target<=1){this.setTarget(target);}}' in recv and want_color in recv and recv.endswith("this.setChanged();")
       and recv.index('contains("level")') < recv.index('contains("color")'),
       "the manual rod's receiveControl: `level` goes to setTarget only when finite and 0 <= v <= 1 (NEO-only validation; original :72-74 unvalidated), `color` is |v % 5| (same index as the original's abs(v) % 5 except Integer.MIN_VALUE) with the original's toggle "
       "to null for the same colour (:76-86), then setChanged (original markDirty)", (recv, want_color))
    nb_pre = piece(ob(inp, "man.read"), 'if(tag.contains("startingLevel"))', 'if(tag.contains("color"))')
    rd = neo_body(st, MAN, "read")
    wr_a, wr_b = ob(inp, "man.write"), neo_body(st, MAN, "write")
    ck("V2.manual-nbt", rd == "super.loadAdditional(tag,registries);" + nb_pre + 'if(tag.contains("color"))this.color=colorOf(tag.getInt("color"));elsethis.color=null;' and wr_a == wr_b and "return index>=0".replace(" ", "") in squash_lit(blank_comments(txt[MAN]))
       and "index<RBMKColor.values().length?RBMKColor.values()[index]:null" in code[MAN],
       "NBT of the manual rod: startingLevel when present, colour by ordinal (absent = null; NEO reads an out-of-range saved value as null instead of throwing), save writes startingLevel, `mult` = getMult() and the colour when set (:91-113)", (rd, wr_a == wr_b))
    ser_a, ser_b = ob(inp, "man.serialize"), neo_body(st, MAN, "serialize")
    de = neo_body(st, MAN, "deserialize")
    ck("V2.manual-sync", ser_a == ser_b and de == "super.deserialize(buf);this.startingLevel=buf.readDouble();this.color=colorOf(buf.readInt());" and "buf.writeInt(-1);" in ser_b,
       "serialize equals the original (startingLevel, colour ordinal or -1); deserialize reads startingLevel then the colour through the safe lookup (-1 or out of range = null; the original clamps to [0, 5] which throws for 5, :125-132)", (ser_a == ser_b, de))
    enum_a = "publicenumRBMKColor{" + ",".join(re.findall(r"\b([A-Z]+)\b", re.search(r"enum RBMKColor \{(.*?)\}", inp.o["man"], re.S)[1])) + "}"
    ck("V2.manual-enum", enum_a == "publicenumRBMKColor{RED,YELLOW,GREEN,BLUE,PURPLE}" and enum_a in code[MAN], "the public nested RBMKColor enum keeps the original order RED, YELLOW, GREEN, BLUE, PURPLE (:134-140; the colour index of the GUI and the packet)")
    cmp_group(ck, "V2.manual-console", "getNBTForConsole adds the short colour (ordinal or -1) to the base data; ICopiable getSettings equals the original (:147-157, :186-191)", inp, st, MAN,
              [("man.console", "console", "", [], [lit("CompoundTagdata=super.getNBTForConsole();", "CompoundTagdata=super.getNBTForConsole();")]), ("man.getSettings", "getSettings", "", (), ())])
    paste_a = rewrite(ob(inp, "man.paste").replace("this.markChanged();", "this.setChanged();"), [(r"(?<![\w.])tag\.", "nbt.")])
    eq(ck, "V2.manual-paste", "pasteSettings equals the original (:193-201: colour by grabEnumSafely or null) with markChanged -> setChanged", paste_a, neo_body(st, MAN, "paste"))
    cmp_group(ck, "V2.manual-ror", "getFunctionInfo and runRORFunction equal the original (:203-230: setrods 0..100, extendrods -100..100 clamped to [0, 1], markDirty -> setChanged)", inp, st, MAN,
              [("man.info", "info", "", (), []), ("man.run", "run", "", (), [lit("this.markDirty();", "this.setChanged();")])])
    ck("V2.manual-type", neo_body(st, MAN, "ctype") == "returnRBMKColumnType.CONTROL;" and ov.b["man.type"] == "returnColumnType.CONTROL;" and 'return"container.rbmkControl";' in code[MAN] and "instanceofRBMKControlBlockcontrol&&control.moderated" in code[MAN],
       "the manual rod reports console type CONTROL, container.rbmkControl and takes moderated from its block (:36-43, :143-145)")
    # ---- automatic rod
    upd = "Levelworld=this.getLevel();if(world==null)return;" + ob(inp, "aut.update", extra=[lit("if(!worldObj.isRemote){", "if(!world.isClientSide){")])
    eq(ck, "V2.auto-functions", "RBMKControlAutoBlockEntity.updateEntity equals the original :39-80 token for token: bounds min/max, heat < lower -> levelLower, heat > upper -> levelUpper, LINEAR / QUAD_UP / QUAD_DOWN, "
       "target = clamp(faux * 0.01, 0, 1), all BEFORE the parent tick", upd, neo_body(st, AUT, "update"))
    ca = code[AUT]
    lin = re.search(r"fauxLevel = (.*?);\s+break;", inp.o["aut"], re.S)
    ck("V2.auto-function-null", 'this.function=functionOf(tag.contains("function")?tag.getInt("function"):0);' in ca and "returnindex>=0&&index<RBMKFunction.values().length?RBMKFunction.values()[index]:RBMKFunction.LINEAR;" in ca
       and 'tag.putInt("function",function.ordinal());' in ca and "if(function!=null)" not in ca and "buf.writeInt(function.ordinal());" in ca and "this.function=functionOf(buf.readInt());" in ca and lin is not None
       and "publicRBMKFunctionfunction=RBMKFunction.LINEAR;" in ca,
       "the function is never null: a missing or out-of-range saved/sent value reads as LINEAR (the original reads null and throws in the next tick's switch, :91-94), and it is always written and sent (the original writes it only when non-null while "
       "deserialize always reads it, :106-117, :127)", ())
    nb = piece(ob(inp, "aut.read"), "this.levelLower=", "if(tag.contains(\"function\"))")
    rd = neo_body(st, AUT, "read")
    wr = ob(inp, "aut.write").replace('if(function!=null)tag.putInt("function",function.ordinal());', 'tag.putInt("function",function.ordinal());')
    ser = ob(inp, "aut.serialize").replace("if(function!=null)buf.writeInt(function.ordinal());", "buf.writeInt(function.ordinal());")
    dsr = ob(inp, "aut.deserialize").replace("this.function=RBMKFunction.values()[buf.readInt()];", "this.function=functionOf(buf.readInt());")
    ck("V2.auto-nbt-sync", rd == "super.loadAdditional(tag,registries);" + nb + 'this.function=functionOf(tag.contains("function")?tag.getInt("function"):0);' and wr == neo_body(st, AUT, "write") and ser == neo_body(st, AUT, "serialize") and dsr == neo_body(st, AUT, "deserialize"),
       "NBT keys levelLower, levelUpper, heatLower, heatUpper, function and serialize/deserialize of the four doubles then the function equal the original (:82-128) apart from the never-null function", (first_diff(rd, nb)))
    ro = neo_body(st, AUT, "receive")
    gui = re.search(r"double clamp = k < 2 \? (\d+) : (\d+);", inp.o["gaut"])
    lim_l, lim_h = (gui[1], gui[2]) if gui else ("?", "?")
    want_recv = ('if(data.contains("function")){intc=Math.abs(data.getInt("function")%RBMKColor.values().length);if(c<RBMKFunction.values().length)this.function=RBMKFunction.values()[c];}else{'
                 'doublelevelLower=data.getDouble("levelLower");doublelevelUpper=data.getDouble("levelUpper");doubleheatLower=data.getDouble("heatLower");doubleheatUpper=data.getDouble("heatUpper");'
                 f"if(inRange(levelLower,{lim_l})&&inRange(levelUpper,{lim_l})&&inRange(heatLower,{lim_h})&&inRange(heatUpper,{lim_h}))" + "{this.levelLower=levelLower;this.levelUpper=levelUpper;this.heatLower=heatLower;this.heatUpper=heatUpper;}}this.setChanged();")
    ck("V2.auto-receive", ro == want_recv and "returnDouble.isFinite(value)&&value>=0D&&value<=max;" in ca and "if(c<RBMKFunction.values().length)" in ro and lim_l == "100" and lim_h == "9999" and "Math.abs(data.getInteger(\"function\"))%" in ov.b["aut.receive"].replace("getInteger", "getInteger"),
       f"the automatic rod's receiveControl: `function` = |v % 5| (the original's RBMKColor modulus) accepted only below the three functions (3 and 4 crash the original server, :133-135), else the four doubles accepted as a whole only when finite and within 0..{lim_l} / 0..{lim_h} "
       "(the ranges GUIRBMKControlAuto :109-116 clamps to), setChanged", first_diff(want_recv, ro))
    gs = ob(inp, "aut.getSettings")
    ps = rewrite(ob(inp, "aut.paste"), [(r"(?<![\w.])tag\.", "nbt.")]) + "this.setChanged();"
    ck("V2.auto-copy", gs == neo_body(st, AUT, "getSettings") and ps == neo_body(st, AUT, "paste"), "ICopiable of the automatic rod equals the original (:170-188: four doubles + function ordinal; paste each key when present with the safe enum lookup) plus setChanged on paste (the original does not mark the tile)",
       (first_diff(gs, neo_body(st, AUT, "getSettings")), first_diff(ps, neo_body(st, AUT, "paste"))))
    ck("V2.auto-type", neo_body(st, AUT, "ctype") == "returnRBMKColumnType.CONTROL_AUTO;" and ov.b["aut.type"] == "returnColumnType.CONTROL_AUTO;" and 'return"container.rbmkControlAuto";' in ca
       and "publicenumRBMKFunction{LINEAR,QUAD_UP,QUAD_DOWN}" in ca and "publicdoublelevelLower;" in ca and "publicdoubleheatUpper;" in ca,
       "the automatic rod reports console type CONTROL_AUTO, container.rbmkControlAuto and has the public nested RBMKFunction LINEAR, QUAD_UP, QUAD_DOWN (:148-157)")


def v2_neutron(ck, inp, st):
    ov = need_ov(inp)
    live, start = lf(st.text(RNH)), lf(inp.start[RNH])
    sig_o, sig_n = "public void runStreamInteraction(World worldObj, StreamWorld streamWorld)", "public void runStreamInteraction(Level level, StreamWorld streamWorld)"
    o_run = rewrite(ov.b["rnh.run"], RC + [(r"worldObj", "level")])
    n_run = body(live, sig_n)
    o_branch = piece(o_run, "elseif(type==RBMKType.CONTROL_ROD){", "elseif(type==RBMKType.REFLECTOR){")
    n_branch = piece(n_run, "elseif(type==RBMKType.CONTROL_ROD){", "elseif(type==RBMKType.REFLECTOR){")
    eq(ck, "V2.neutron-branch", "RBMKNeutronHandler: the CONTROL_ROD branch equals the original :332-340 (level > 0 -> flux *= getMult() and continue, else return) and sits between the flux-receiver block and REFLECTOR", o_branch, n_branch)
    order = [n_run.index("type==RBMKType.MODERATOR||nodeTE.isModerated()"), n_run.index("nodeTEinstanceofIRBMKFluxReceiver"), n_run.index("elseif(type==RBMKType.CONTROL_ROD)"), n_run.index("elseif(type==RBMKType.REFLECTOR)"), n_run.index("elseif(type==RBMKType.ABSORBER)")]
    ck("V2.neutron-order", order == sorted(order), "the branch order is MODERATOR / isModerated -> IRBMKFluxReceiver -> CONTROL_ROD -> REFLECTOR -> ABSORBER (original :307, :312, :332, :341, :357)", order)
    o_tail = piece(o_run, "RBMKTypelastNodeType=")
    o_tail = rewrite(o_tail, [lit('RBMKTypelastNodeType=(RBMKType)lastNode.data.get("type");', "RBMKTypelastNodeType=((RBMKNeutronNode)lastNode).getRBMKType();"),
                              lit("BlockPosposAfter=newBlockPos(lastNode.tile.xCoord+this.vector.xCoord,lastNode.tile.yCoord,lastNode.tile.zCoord+this.vector.zCoord);",
                                  "BlockPoslastPos=lastNode.tile.getBlockPos();BlockPosposAfter=BlockPos.containing(lastPos.getX()+this.vector.xCoord,lastPos.getY(),lastPos.getZ()+this.vector.zCoord);"),
                              lit("this.vector.xCoord", "this.vector.x"), lit("this.vector.zCoord", "this.vector.z"),
                              lit("if(teinstanceofRBMKBaseBlockEntity){RBMKNeutronNodenodeAfter=makeNode(NeutronNodeWorld.getOrAddWorld(level),(RBMKBaseBlockEntity)te);NeutronNodeWorld.getOrAddWorld(level).addNode(nodeAfter);}",
                                  "if(teinstanceofRBMKBaseBlockEntityrbmk){StreamWorldworld=NeutronNodeWorld.getOrAddWorld(level);RBMKNeutronNodenodeAfter=makeNode(world,rbmk);world.addNode(nodeAfter);}")])
    n_tail = piece(n_run, "RBMKTypelastNodeType=")
    eq(ck, "V2.neutron-tail", "the tail equals the original :377-397: a CONTROL_ROD last node with getMult() > 0 multiplies the flux, posAfter = last node + vector (same y), and the #1933 test `NeutronNodeWorld.getNode(level, pos) == null` still checks the stream "
       "ORIGIN pos (upstream-shared, practically dead), then makeNode + addNode or irradiateFromFlux(posAfter)", o_tail, n_tail)
    ck("V2.neutron-pos-origin", "BlockPospos=origin.tile.getBlockPos();" in n_run and "if(NeutronNodeWorld.getNode(level,pos)==null)" in n_run and "getNode(level,posAfter)" not in n_run and "BlockPospos=newBlockPos(origin.tile)" in ov.b["rnh.run"],
       "the #1933 check keeps `pos`, the stream origin position (original :252 / :387), not posAfter")
    # nothing else changed: both files without the run method body, imports of the new class removed
    def rest(text):
        code = code_of(text)
        o, c, blanked = method_span(text, sig_n)
        inner = squash_lit(blanked[o + 1:c])
        return code.replace(inner, "", 1)
    start_run = body(start, sig_n)
    sa = rest(start).replace("importcom.hbm.blockentity.machine.rbmk.RBMKControlBlockEntity;", "")
    sb = rest(live).replace("importcom.hbm.blockentity.machine.rbmk.RBMKControlBlockEntity;", "")
    live_stripped = n_run.replace(n_branch, "").replace(n_tail, "")
    start_stripped = start_run
    ck("V2.neutron-nothing-else", sa == sb and live_stripped == start_stripped and "importcom.hbm.blockentity.machine.rbmk.RBMKControlBlockEntity;" in code_of(live),
       "RBMKNeutronHandler differs from the start copy only by the import, the CONTROL_ROD branch, the tail block and comments: with both removed the whole file (and the run method) equals the start", (first_diff(sa, sb), first_diff(start_stripped, live_stripped)))
    ck("V2.neutron-edited", not hashed_equal(inp, st, RNH) and lf(st.text(RNH)) != lf(inp.start[RNH]), "RBMKNeutronHandler differs from the start copy")


# ---------------------------------------------------------------- V3 steam channel, heater, cooler, loader and the base column against V1

NEO_SIG.update({
    "heat": "public static double getHeatFromSteam(FluidType type)", "factor": "public static double getFactorFromSteam(FluidType type)", "cycle": "public void cyceCompressor()",
    "collect": "protected void collectOverpressurePipes(Set<FluidNetMK2> pipes)", "getAll": "public FluidTank[] getAllTanks()", "getSending": "public FluidTank[] getSendingTanks()",
    "getReceiving": "public FluidTank[] getReceivingTanks()", "ports": "protected List<DirPos> getPortConnections()", "handleOP": "private void handleOverpressure(Set<FluidNetMK2> pipes)",
    "melt": "private void meltConnected()", "canConnect": "public boolean canConnect(FluidType type, BlockGetter level, BlockPos pos, Direction dir)", "setTankType": "public void setTankType(FluidType type)",
})

PRE_RAND = [(r"worldObj\.rand\.", "getLevel().random.")]
NBT_ARG = [(r"\(nbt,", "(tag,")]
TANKS_B = [(r"tanks\[0\]", "t0"), (r"tanks\[1\]", "t1")]


def cs(st, path):
    """The squashed, number-normalised code of a NEO file (comments blanked)."""
    return sq(blank_comments(lf(st.text(path))))


def tank_decls(text):
    return [(m[1], m[2], m[3], m[4].replace("_", "")) for m in re.finditer(r"(?:this\.)?(\w+)(?:\[(\d)\])? = new FluidTank\(Fluids\.(\w+), ([\d_]+)\);", text)]


def parse_ports(text):
    out = {}
    for name in ("getPortsNoLoader", "getPortsCloseLoader", "getPortsClassicLoader"):
        m = re.search(r"public PortDef\[\] " + name + r"\(\) \{.*?new PortDef\[\] \{(.*?)\};", text, re.S)
        out[name] = re.findall(r"PortDef\.make\(xCoord, (yCoord(?: [+-] [\w.()]+)?), zCoord, ([\w.]+)\)", m[1]) if m else None
    return out


def v3_steam(ck, inp, st):
    ov = need_ov(inp)
    code = {p: cs(st, p) for p in (BOI, HEA, COO)}
    iso = [p for p in code if re.search(r"net\.minecraft\.client|com\.hbm\.render|inventory\.screens", lf(st.text(p)))]
    # ---- classes, tanks, fields
    t_boi, t_hea, t_coo = (tank_decls(inp.o[k]) for k in ("boi", "hea", "coo"))
    want_b = "".join(f"publicFluidTank{n}=newFluidTank(Fluids.{f},{a});" for n, _, f, a in t_boi)
    want_h = "".join(f"publicFluidTank{n}=newFluidTank(Fluids.{f},{a});" for n, _, f, a in t_hea)
    want_c = "".join(f"publicfinalFluidTankt{i}=newFluidTank(Fluids.{f},{a});" for _, i, f, a in t_coo)
    slots = {k: re.search(r"super\((\d*)\);", inp.o[k]) for k in ("boi", "hea", "coo")}
    nbc = re.search(r"neighborCache = new TileEntityRBMKBase\[(\d+)\]", inp.o["coo"])
    ck("V3.classes", len(t_boi) == 2 and len(t_hea) == 2 and len(t_coo) == 2 and all(slots.values()) and nbc is not None and slots["boi"][1] == "0" and slots["hea"][1] == "1" and slots["coo"][1] == ""
       and "publicclassRBMKBoilerBlockEntityextendsRBMKSlottedBaseBlockEntityimplementsIControlReceiver,IFluidStandardTransceiverMK2,IRORValueProvider{" in code[BOI]
       and "publicclassRBMKHeaterBlockEntityextendsRBMKSlottedBaseBlockEntityimplementsIFluidStandardTransceiverMK2,IRORValueProvider{" in code[HEA]
       and "publicclassRBMKCoolerBlockEntityextendsRBMKBaseBlockEntityimplementsIFluidStandardTransceiverMK2{" in code[COO]
       and "super(NtmBlockEntityTypes.RBMK_BOILER.get(),pos,state,0);" in code[BOI] and "super(NtmBlockEntityTypes.RBMK_HEATER.get(),pos,state,1);" in code[HEA] and "super(NtmBlockEntityTypes.RBMK_COOLER.get(),pos,state);" in code[COO]
       and want_b in code[BOI] and want_h in code[HEA] and want_c in code[COO] and "protectedintconsumption;protectedintoutput;protectedintventDelay;" in code[BOI]
       and "protectedinttimer=0;" in code[COO] and f"protectedRBMKBaseBlockEntity[]coolerCache=newRBMKBaseBlockEntity[{nbc[1]}];" in code[COO] and not iso
       and 'return"container.rbmkBoiler";' in code[BOI] and 'return"container.rbmkHeater";' in code[HEA],
       "boiler (SlottedBase(0): WATER 10,000 + STEAM 1,000,000), heater (SlottedBase(1): COOLANT 16,000 + COOLANT_HOT 16,000) and cooler (plain base: PERFLUOROMETHYL_COLD 4,000 + PERFLUOROMETHYL 4,000, timer, 25-entry cache) have "
       "the original's tanks, slots, fields and container names (TileEntityRBMKBoiler.java:44-63, Heater :34-49, Cooler :25-36) and import no client class", (want_b, want_h, want_c, iso))
    # ---- boiler tick
    o_up = ov.b["boi.update"]
    n_up = neo_body(st, BOI, "update")
    vent_a, vent_b = "if(ventDelay<=0){", "}}this.heat-=waterUsed*HEAT_PER_MB_WATER;"
    try:
        oi, oj = o_up.index(vent_a) + len(vent_a), o_up.index(vent_b)
        ni, nj = n_up.index(vent_a) + len(vent_a), n_up.index(vent_b)
        o_vent, n_vent = o_up[oi:oj], n_up[ni:nj]
        o_tick, n_tick = o_up[:oi] + "VENT" + o_up[oj:], n_up[:ni] + "VENT" + n_up[nj:]
    except ValueError as error:
        o_vent = n_vent = o_tick = n_tick = ""
        ck("V3.boiler-tick-shape", False, "the vent block anchors exist in both updateEntity bodies", repr(error))
    o_tick = rewrite(o_tick, [lit("this.getHeatFromSteam(", "getHeatFromSteam(")] + RC)
    o_tick = piece(o_tick, "this.consumption=0;")
    pre = "Levelworld=this.getLevel();if(world!=null&&!world.isClientSide){for(DirPoscon:this.getPortConnections()){this.trySubscribe(feed.getTankType(),world,con);this.tryProvide(steam,world,con);}"
    tail_o = "this.heat-=waterUsed*HEAT_PER_MB_WATER;}}super.updateEntity();"
    tail_n = "this.heat-=waterUsed*HEAT_PER_MB_WATER;if(waterUsed!=0||steamProduced!=0)this.setChanged();}}super.updateEntity();"
    want_tick = pre + o_tick.replace(tail_o, tail_n) if tail_o in o_tick else ""
    eq(ck, "V3.boiler-tick", "RBMKBoilerBlockEntity.updateEntity equals the original :66-125 outside the vent block: renewed subscribe(feed type) / provide(steam) on every port connection instead of ports.update (:71-72), consumption = output = 0, "
       "ventDelay--, heatCap = getHeatFromSteam(steam type), heatProvided = heat - heatCap, the ULTRAHOTSTEAM branch floor((hp / HPMW) * 100 / f) / floor(sp / 100 * f) with the feed shortage recompute, the other branch floor(hp / HPMW) capped "
       "by the feed and floor(wu * 100 / f), the feed / steam update, the steam clamp, heat -= wu * HPMW, the parent tick last; NEO only marks the chunk dirty when something was produced", want_tick, n_tick)
    ot = blank_comments(inp.o["boi"])
    mt = re.search(r'data\.setString\("type", "(\w+)"\);', ot)
    mp = re.search(r"xCoord \+ ([0-9.]+) \+ worldObj\.rand\.nextInt\((\d+)\) \* ([0-9.]+), yCoord \+ RBMKDials\.getColumnHeight\(worldObj\), zCoord \+ ([0-9.]+) \+ worldObj\.rand\.nextInt\((\d+)\) \* ([0-9.]+)\), "
                   r"new TargetPoint\(worldObj\.provider\.dimensionId, xCoord \+ 0\.5, yCoord \+ 1, zCoord \+ 0\.5, (\d+)\)", ot)
    md = re.search(r"this\.ventDelay = (\d+) \+ worldObj\.rand\.nextInt\((\d+)\);", ot)
    ms = re.search(r'playSoundEffect\(xCoord, yCoord \+ RBMKDials\.getColumnHeight\(worldObj\), zCoord, "hbm:([\w.]+)", (\d+)F, (\d+)F \+ worldObj\.rand\.nextFloat\(\) \* ([0-9.]+)F\);', ot)
    parsed = bool(mt and mp and md and ms) and mp[1] == mp[4] and mp[2] == mp[5] and mp[3] == mp[6]
    vent_want = ""
    if parsed:
        vent_want = sq(f'BlockPospos=this.getBlockPos();inth=RBMKDials.getColumnHeight();CompoundTagdata=newCompoundTag();data.putString("type","{mt[1]}");doublepx=pos.getX()+{mp[1]}+world.random.nextInt({mp[2]})*{mp[3]};'
                       f'doublepz=pos.getZ()+{mp[4]}+world.random.nextInt({mp[5]})*{mp[6]};if(worldinstanceofServerLevelserverLevel){{PacketDistributor.sendToPlayersNear(serverLevel,null,pos.getX()+0.5,pos.getY()+1,pos.getZ()+0.5,{mp[7]},'
                       f'newAuxParticle(data,px,pos.getY()+h,pz));}}this.ventDelay={md[1]}+world.random.nextInt({md[2]});world.playSound(null,pos.getX(),pos.getY()+h,pos.getZ(),NtmSoundEvents.STEAM_ENGINE_OPERATE.get(),SoundSource.BLOCKS,'
                       f'{ms[2]},{ms[3]}+world.random.nextFloat()*{ms[4]});')
    snake = re.sub(r"([A-Z])", lambda m: "_" + m[1].lower(), ms[1]) if ms else ""
    sounds = code_of(st.text(SOUNDS)) if st.has(SOUNDS) else ""
    auxp = code_of(st.text(AUXP)) if st.has(AUXP) else ""
    ok_snd = bool(snake) and f'STEAM_ENGINE_OPERATE=reg("{snake}");' in sounds
    ck("V3.boiler-vent", parsed and ok_snd and vent_want == n_vent and "if(RBMKDials.getColumnHeight" not in n_vent and "recordAuxParticle(CompoundTagnbt,doublex,doubley,doublez)" in auxp
       and mt[1] == "rbmksteam" and mp[7] == "100" and (md[1], md[2]) == ("20", "10") and (ms[2], ms[3], ms[4]) == ("2", "1", "0.25") and ms[1] == "block.steamEngineOperate",
       "the vent block (steam above the tank maximum, only when ventDelay <= 0) equals the original :110-117: effect type `rbmksteam` at x/z + 0.25 + rand(2) * 0.5 and y + column height, sent to every player within 100 blocks of "
       "(x + 0.5, y + 1, z + 0.5) (original TargetPoint 100 plus the local effectNT call), ventDelay = 20 + rand(10), then the sound block.steamEngineOperate (NEO block.steam_engine_operate) at (x, y + column height, z), "
       "volume 2, pitch 1 + rand * 0.25", (first_diff(vent_want, n_vent), parsed, ok_snd))
    cmp_group(ck, "V3.boiler-tables", "getHeatFromSteam (100 / 300 / 450 / 600) and getFactorFromSteam (1 / 10 / 100 / 1000) for STEAM / HOTSTEAM / SUPERHOTSTEAM / ULTRAHOTSTEAM, else 0, equal the original (:127-141)", inp, st, BOI,
              [("boi.heat", "heat", "", (), ()), ("boi.factor", "factor", "", (), ())])
    cmp_group(ck, "V3.boiler-nbt-sync", "load/saveAdditional keys feed and steam, serialize steam THEN feed and deserialize steam THEN feed equal the original (:143-171)", inp, st, BOI,
              [("boi.read", "read", "", (), NBT_ARG), ("boi.write", "write", "", (), NBT_ARG), ("boi.serialize", "serialize", "", (), ()), ("boi.deserialize", "deserialize", "", (), ())])
    perm_pre = [lit("returnVec3.createVectorHelper(xCoord-player.posX,yCoord-player.posY,zCoord-player.posZ).lengthVector()<20;",
                    "BlockPospos=this.getBlockPos();returnnewVec3(pos.getX()-player.getX(),pos.getY()-player.getY(),pos.getZ()-player.getZ()).length()<20;")]
    cmp_group(ck, "V3.boiler-control", "hasPermission measures the block corner (< 20) and receiveControl `compression` calls cyceCompressor, as the original (:173-184)", inp, st, BOI,
              [("boi.perm", "perm", "", (), perm_pre), ("boi.receive", "receive", "", (), [])])
    # ---- the compressor: the tank is emptied by every accepted step
    o_cy, n_cy = ov.b["boi.cycle"], neo_body(st, BOI, "cycle")
    want_cy = rewrite(o_cy, RC).replace("this.markDirty();", "this.setChanged();")
    head = "if(this.heat>50&&this.feed.getFill()>0)return;FluidTypetype=steam.getTankType();"
    steps = re.findall(r"if\(type==Fluids\.(\w+)\)\{steam\.setTankType\(Fluids\.(\w+)\);steam\.setFill\((.*?)\);\}", n_cy)
    want_steps = [("STEAM", "HOTSTEAM", "steam.getFill()/10"), ("HOTSTEAM", "SUPERHOTSTEAM", "steam.getFill()/10"), ("SUPERHOTSTEAM", "ULTRAHOTSTEAM", "steam.getFill()/10"),
                  ("ULTRAHOTSTEAM", "STEAM", "Math.min(steam.getFill()*1000,steam.getMaxFill())")]
    settype_o, settype_n = ov.b["ft.setType"], neo_body(st, FLUIDTANK, "setTankType") if st.has(FLUIDTANK) else ""
    zeroed = "this.type=type;this.setFill(0);" in settype_o and "this.type=type;this.setFill(0);" in settype_n and "if(this.type==type)return;" in settype_n
    ck("V3.boiler-compressor", n_cy == want_cy and n_cy.startswith(head) and steps == want_steps and zeroed
       and all(c.index(f"steam.setTankType(Fluids.{b});") < c.index("steam.setFill(") for c, (_, b, _) in zip(n_cy.split("if(type==Fluids.")[1:], want_steps))
       and "getFill()" not in n_cy[:n_cy.index("if(type==Fluids.STEAM)")].replace("this.feed.getFill()>0", "") and n_cy.endswith("this.setChanged();"),
       "cyceCompressor (spelling kept) has the original's statement order (:186-197): refused when heat > 50 with feedwater left, the type captured ONCE, then four sequential ifs STEAM -> HOTSTEAM, HOTSTEAM -> SUPERHOTSTEAM, "
       "SUPERHOTSTEAM -> ULTRAHOTSTEAM (fill / 10) and ULTRAHOTSTEAM -> STEAM (min(fill * 1000, max)), each calling setTankType BEFORE setFill(getFill() ...) with no fill captured before it; FluidTank.setTankType (original :62-68, NEO :64-70) "
       "zeroes the fill on a type change, so every accepted step empties the steam tank and the divisions never take effect (upstream behaviour kept)", (first_diff(want_cy, n_cy), steps, zeroed))
    # ---- melt, console, tanks, RoR
    o_melt = cut(ob(inp, "boi.onMelt", extra=PRE_RAND), "if(RBMKDials.getOverpressure()&&ports.outPorts!=null){", "super.onMelt(reduce);", "super.onMelt(reduce);")
    eq(ck, "V3.boiler-melt", "onMelt equals the original :199-218 without the overpressure block: BLANK debris 1 + rand(2), then super.onMelt", o_melt, neo_body(st, BOI, "onMelt"))
    om = ov.b["boi.onMelt"]
    want_col = ("Levelworld=this.getLevel();for(DirPoscon:this.getPortConnections()){if(UniNodespace.getNode(world,con.makeCompat(),steam.getTankType().getNetworkProvider())instanceofFluidNodenode&&node.hasValidNet()){pipes.add(node.net);}}")
    ck("V3.boiler-collect", neo_body(st, BOI, "collect") == want_col and "for(TilePortport:ports.outPorts)if(port!=null)for(DirPoscon:port.connections){" in om
       and "FluidNodenode=(FluidNode)UniNodespace.getNode(worldObj,con.getX(),con.getY(),con.getZ(),steam.getTankType().getNetworkProvider());if(node!=null&&node.hasValidNet()){this.pipes.add(node.net);}" in om
       and "ports.setInputTanks(feed)" not in om and "ModulePortManFluidAdaptive(this).setInputTanks(feed).setOutputTanks(steam)" in sq(blank_comments(inp.o["boi"])),
       "the boiler adds the networks of its steam provider nodes at every connection of its (output) ports, only when the node has a valid net (original onMelt :208-215, run when the overpressure dial is on); NEO "
       "asks every port connection of the column (the original's out ports carry exactly those connections: V3.base-ports)", first_diff(want_col, neo_body(st, BOI, "collect")))
    cons = ob(inp, "boi.console", [lit("CompoundTagdata=newCompoundTag();", "CompoundTagdata=super.getNBTForConsole();")])
    eq(ck, "V3.boiler-console", "getNBTForConsole writes water, maxWater, steam, maxSteam (ints) and the steam type id (short) on top of the NEO base data (original :225-234 builds only these keys; 24C convention)", cons, neo_body(st, BOI, "console"))
    cmp_group(ck, "V3.boiler-tanks-ror", "console type BOILER, tanks {feed, steam}, sending {steam}, receiving {feed} and the RoR values feed / steam / consumption equal the original (:220-248, :330-345)", inp, st, BOI,
              [("boi.type", "ctype", "", (), [lit("ColumnType.", "RBMKColumnType.")]), ("boi.getAll", "getAll", "", (), ()), ("boi.getSending", "getSending", "", (), ()), ("boi.getReceiving", "getReceiving", "", (), ()),
               ("boi.info", "info", "", (), []), ("boi.ror", "ror", "", (), [])])
    # ---- heater
    o_h = ov.b["hea.update"]
    h_rules = [lit("feed.setType(0,slots);", "{if(feed.setType(0,slots))this.setChanged();}"),
               lit("*trait.getEfficiency(HeatingType.HEATEXCHANGER);}if(eff<=0)", "*trait.getEfficiency(HeatingType.HEATEXCHANGER);if(ops!=0)this.setChanged();}if(eff<=0)")]
    try:
        want_h_up = pre + rewrite(piece(o_h, "if(this.heat<=50||this.feed.getFill()<=0)"), h_rules + RC)
    except ValueError:
        want_h_up = ""
    eq(ck, "V3.heater-tick", "RBMKHeaterBlockEntity.updateEntity equals the original :52-93: renewed port subscribe(feed type) / provide(steam), the feed type follows slot 0 while heat <= 50 or the feed is empty, a heatable feed takes its first "
       "heating step and sets the hot type, tempRange = heat - hot temperature, ops = min(feed / amountReq, free / amountProduced, floor(tempRange * TU_PER_DEGREE / heatReq)), both tanks move, heat -= (heatReq * ops / TU_PER_DEGREE) * efficiency, "
       "both tanks NONE for efficiency <= 0 or no FT_Heatable, the parent tick last; NEO only marks the chunk dirty on a change", want_h_up, neo_body(st, HEA, "update"))
    tu = re.search(r"double TU_PER_DEGREE = ([\d_]+)D \* eff;", inp.o["hea"])
    ck("V3.heater-tu", tu is not None and tu[1].replace("_", "") == "2000" and f"doubleTU_PER_DEGREE={tu[1].replace('_', '')}*eff;" in neo_body(st, HEA, "update") and "inttempOps=(int)Math.floor((tempRange*TU_PER_DEGREE)/step.heatReq);" in neo_body(st, HEA, "update"),
       "TU_PER_DEGREE = 2000 * efficiency (original :70, 1 mB of water absorbing 200 TU and 0.1 degrees from a column) and tempOps = floor(tempRange * TU_PER_DEGREE / heatReq)", tu and tu[1])
    cmp_group(ck, "V3.heater-nbt-sync", "load/saveAdditional keys feed and steam, serialize and deserialize feed THEN steam equal the original (:95-123)", inp, st, HEA,
              [("hea.read", "read", "", (), NBT_ARG), ("hea.write", "write", "", (), NBT_ARG), ("hea.serialize", "serialize", "", (), ()), ("hea.deserialize", "deserialize", "", (), ())])
    cmp_group(ck, "V3.heater-melt", "onMelt equals the original :125-135: BLANK debris 1 + rand(2), then super.onMelt", inp, st, HEA, [("hea.onMelt", "onMelt", "", PRE_RAND, ())])
    cons = ob(inp, "hea.console", [lit("CompoundTagdata=newCompoundTag();", "CompoundTagdata=super.getNBTForConsole();")])
    eq(ck, "V3.heater-console", "getNBTForConsole writes water, maxWater, steam, maxSteam and the shorts type (feed) and hottype (steam) on top of the NEO base data (original :142-152)", cons, neo_body(st, HEA, "console"))
    cmp_group(ck, "V3.heater-tanks-ror", "console type HEATEX, tanks {feed, steam}, sending {steam}, receiving {feed} and the RoR values in / out equal the original", inp, st, HEA,
              [("hea.type", "ctype", "", (), [lit("ColumnType.", "RBMKColumnType.")]), ("hea.getAll", "getAll", "", (), ()), ("hea.getSending", "getSending", "", (), ()), ("hea.getReceiving", "getReceiving", "", (), ()),
               ("hea.info", "info", "", (), []), ("hea.ror", "ror", "", (), [])])
    # ---- cooler
    scan_o = "TileEntitytile=Compat.getTileStandard(worldObj,x,yCoord,z);if(tileinstanceofTileEntityRBMKBase){neighborCache[i]=(TileEntityRBMKBase)tile;}else{neighborCache[i]=null;}"
    scan_n = "BlockPospos=newBlockPos(x,this.worldPosition.getY(),z);if(world.isLoaded(pos)&&world.getBlockEntity(pos)instanceofRBMKBaseBlockEntityrbmk){coolerCache[i]=rbmk;}else{coolerCache[i]=null;}"
    c_pre = [lit("intx=xCoord-2+i/5;intz=zCoord-2+i%5;", "intx=this.worldPosition.getX()-2+i/5;intz=this.worldPosition.getZ()-2+i%5;"), lit(scan_o, scan_n), lit("neighborCache", "coolerCache")] + TANKS_B
    c_post = [lit("if(neighbor!=null){", "if(neighbor!=null&&!neighbor.isRemoved()){"), lit("neighbor.heat=20;}}}}super.updateEntity();", "neighbor.heat=20;}}this.setChanged();}}super.updateEntity();")]
    pre_c = "Levelworld=this.getLevel();if(world!=null&&!world.isClientSide){for(DirPoscon:this.getPortConnections()){this.trySubscribe(t0.getTankType(),world,con);this.tryProvide(t1,world,con);}"
    try:
        want_c_up = pre_c + piece(ob(inp, "coo.update", c_post, c_pre), "if(timer<=0){")
    except ValueError:
        want_c_up = ""
    eq(ck, "V3.cooler-tick", "RBMKCoolerBlockEntity.updateEntity equals the original :41-81: renewed port subscribe(t0 type) / provide(t1), a 60-tick timer (rescan at 0), the 5 x 5 scan x - 2 + i / 5, z - 2 + i % 5 at the cooler's own y "
       "without loading chunks, and when t0 holds >= 50 and t1 has 50 free: move 50 mB and every cached column loses 200 heat down to a floor of 20, the parent tick last; NEO skips a column removed since the last scan and marks the chunk dirty",
       want_c_up, neo_body(st, COO, "update"))
    cmp_group(ck, "V3.cooler-nbt-sync", "load/saveAdditional keys t0 and t1 and serialize / deserialize t0 THEN t1 equal the original (:85-108)", inp, st, COO,
              [("coo.read", "read", "", TANKS_B + NBT_ARG, ()), ("coo.write", "write", "", TANKS_B + NBT_ARG, ()), ("coo.serialize", "serialize", "", TANKS_B, ()), ("coo.deserialize", "deserialize", "", TANKS_B, ())])
    cmp_group(ck, "V3.cooler-tanks", "console type COOLER, tanks {t0, t1}, receiving {t0}, sending {t1} equal the original (:113-117); the cooler has no own getNBTForConsole and no GUI", inp, st, COO,
              [("coo.type", "ctype", "", (), [lit("ColumnType.", "RBMKColumnType.")]), ("coo.getReceiving", "getReceiving", "", TANKS_B, ()), ("coo.getSending", "getSending", "", TANKS_B, ())])
    ck("V3.cooler-all-tanks", ov.b["coo.getAll"] == "returntanks;" and neo_body(st, COO, "getAll") == "returnnewFluidTank[]{t0,t1};" and "getNBTForConsole" not in code[COO] and "createMenu" not in code[COO],
       "getAllTanks returns both tanks in order (original returns the tanks array, NEO an array {t0, t1}); the cooler has no console data of its own and no menu", (ov.b["coo.getAll"], neo_body(st, COO, "getAll")))
    # ---- fluids only through the renewed subscribe/provide of the column ports
    wired = all(code[p].count("this.trySubscribe(") == 1 and code[p].count("this.tryProvide(") == 1 and code[p].count("this.getPortConnections()") == (2 if p == BOI else 1) for p in (BOI, HEA, COO))
    bad = [p for p in code if re.search(r"UniNodespace\.createNode|TilePort|ModulePortMan|PortDef", code[p])]
    ck("V3.fluid-wiring", wired and not bad, "each of boiler, heater and cooler connects fluids only through one renewed trySubscribe(input type) / tryProvide(output tank) loop over getPortConnections (boiler's second use is the overpressure hook), "
       "with no port node of its own", (wired, bad))


def v3_loader_base(ck, inp, st):
    ov = need_ov(inp)
    # ---- loader
    want = rewrite(ov.b["rload.canConnect"], [lit("ForgeDirection.UP", "Direction.UP")])
    eq(ck, "V3.loader-connect", "RBMKLoaderBlock.canConnect equals the original RBMKLoader :26-29: the face UP takes a fluid with FT_Heatable, every other face a fluid with FT_Coolable or PERFLUOROMETHYL", want, neo_body(st, LOADBLK, "canConnect"))
    lcode = code_of(st.text(LOADBLK))
    ck("V3.loader-plain", "publicclassRBMKLoaderBlockextendsBlockimplementsIFluidConnectorBlockMK2,ITooltipProvider{" in lcode and "BlockEntity" not in lcode and "EntityBlock" not in lcode and "this.addStandardInfo(components);" in lcode
       and "createNewTileEntity" not in inp.o["rload"], "RBMKLoaderBlock is a plain block (no block entity, as the original has no createNewTileEntity) with the standard tooltip and the fluid-connector interface")
    # ---- ports
    layouts = parse_ports(inp.o["base"])
    top = ("yCoord + RBMKDials.getColumnHeight(worldObj)", "Library.POS_Y")
    want_layouts = {"getPortsNoLoader": [top, ("yCoord", "Library.NEG_Y")], "getPortsCloseLoader": [top, ("yCoord - 1", "ForgeDirection.VALID_DIRECTIONS")],
                    "getPortsClassicLoader": [top, ("yCoord", "Library.NEG_Y"), ("yCoord - 2", "ForgeDirection.VALID_DIRECTIONS")]}
    close_off, classic_off = "1", "2"
    got = neo_body(st, BASEBE, "ports")
    want_ports = (f"inth=RBMKDials.getColumnHeight();BlockPoscore=this.worldPosition;List<DirPos>cons=newArrayList<>();cons.add(newDirPos(core.above(h+1),Direction.UP));BlockPosloader=null;"
                  f"if(level.getBlockState(core.below({classic_off})).is(NtmBlocks.RBMK_LOADER.get())){{cons.add(newDirPos(core.below(),Direction.DOWN));loader=core.below({classic_off});}}"
                  f"elseif(level.getBlockState(core.below()).is(NtmBlocks.RBMK_LOADER.get())){{loader=core.below();}}else{{cons.add(newDirPos(core.below(),Direction.DOWN));}}"
                  "if(loader!=null){for(Directiondir:Direction.values()){BlockPospos=loader.relative(dir);"
                  "if(pos.getX()==core.getX()&&pos.getZ()==core.getZ()&&pos.getY()>=core.getY()&&pos.getY()<=core.getY()+h)continue;cons.add(newDirPos(pos,dir));}}returncons;")
    boi_order = sq(blank_comments(inp.o["boi"]))
    order_ok = boi_order.index("getBlock(xCoord,yCoord-2,zCoord)==ModBlocks.rbmk_loader?this.getPortsClassicLoader():") < boi_order.index("getBlock(xCoord,yCoord-1,zCoord)==ModBlocks.rbmk_loader?this.getPortsCloseLoader():this.getPortsNoLoader()")
    ck("V3.base-ports", layouts == want_layouts and "POS_Y=ForgeDirection.UP;" in sq(blank_comments(otext("src/main/java/com/hbm/lib/Library.java"))) and "NEG_Y=ForgeDirection.DOWN;" in sq(blank_comments(otext("src/main/java/com/hbm/lib/Library.java")))
       and order_ok and got == want_ports,
       "getPortConnections reproduces the three original layouts (:612-644, picked as :71-72: a loader two blocks below = classic, one block below = close, else none): always the connection above the top segment (UP at y + column height + 1); "
       "no loader or classic: the connection below the core (DOWN at y - 1); close or classic: all six directions around the loader (y - 1 or y - 2, in DOWN, UP, N, S, W, E order); NEO only drops the close loader's UP connection that lies "
       "inside the column itself", (layouts, order_ok, first_diff(want_ports, got)))
    # ---- overpressure
    o_melt = ov.b["base.meltdown"]
    region = piece(o_melt, "HashSet<FluidNode>pipeBlocks=", "intsmallDim=")
    region = region[:-1] if region.endswith("}") else region + "?"
    ops_pre = [lit(sq("HashSet<FluidNode> pipeBlocks = new HashSet<>(); HashSet<IFluidReceiverMK2> pipeReceivers = new HashSet<>();"), sq("Set<FluidNode> pipeBlocks = new LinkedHashSet<>(); Set<IFluidReceiverMK2> pipeReceivers = new LinkedHashSet<>();")),
               lit("pipeReceivers.addAll(x.receiverEntries);", "pipeReceivers.addAll(x.receiverEntries.keySet());"),
               lit("for(BlockPospos:node.positions){intx=pos.getX(),y=pos.getY(),z=pos.getZ();if(worldObj.getTileEntity(x,y,z)!=null){worldObj.setBlock(x,y,z,Blocks.air);}}",
                   "for(BlockPospos:node.positions){if(level.getBlockEntity(pos)!=null){level.setBlock(pos,Blocks.AIR.defaultBlockState(),3);}}"),
               lit(sq("if(con instanceof TileEntity) { TileEntity tile = (TileEntity) con; if(con instanceof IOverpressurable) { ((IOverpressurable) con).explode(worldObj, tile.xCoord, tile.yCoord, tile.zCoord); } else { "
                      "worldObj.setBlock(tile.xCoord, tile.yCoord, tile.zCoord, Blocks.air); worldObj.newExplosion(null, tile.xCoord + 0.5, tile.yCoord + 0.5, tile.zCoord + 0.5, 5F, false, false); } }"),
                   sq("if(con instanceof BlockEntity tile) { BlockPos pos = tile.getBlockPos(); if(con instanceof IOverpressurable overpressurable) { overpressurable.explode(level, pos); } else { "
                      "level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3); level.explode(null, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, 5F, false, Level.ExplosionInteraction.NONE); } }"))]
    want_op = rewrite(region, ops_pre + RC)
    n_op = neo_body(st, BASEBE, "handleOP")
    eq(ck, "V3.base-overpressure", "handleOverpressure equals the original meltdown tail :501-538: the union of the nets' links and receiver entries, max = min(links / 5, 100), the first `max` link nodes lose every block that has a block entity "
       "(air), then EVERY receiver that is a block entity goes: IOverpressurable.explode, else air plus an explosion of power 5 at the block centre with no fire and no block damage; NEO uses insertion-ordered sets and the map's key set", want_op, n_op)
    n_melt = neo_body(st, BASEBE, "melt")
    idx = []
    for needle in ("Set<FluidNetMK2>pipes=newLinkedHashSet<>();", "if(RBMKDials.getOverpressure())rbmk.collectOverpressurePipes(pipes);rbmk.onMelt(minDist+1);", "rbmkinstanceofRBMKRodBlockEntity&&level.getBlockState(rbmk.getBlockPos()).is(NtmBlocks.CORIUM_BLOCK.get())",
                   "if(RBMKDials.getOverpressure()&&!pipes.isEmpty())handleOverpressure(pipes);", "intsmallDim="):
        idx.append(n_melt.find(needle))
    o_idx = [o_melt.find(x) for x in ("rbmk.onMelt(minDist+1);", "rbmkinstanceofTileEntityRBMKRod&&worldObj.getBlock(rbmk.xCoord,rbmk.yCoord,rbmk.zCoord)==ModBlocks.corium_block", "if(RBMKDials.getOverpressure(worldObj)&&!pipes.isEmpty()){", "intsmallDim=")]
    ck("V3.base-meltdown-order", all(i >= 0 for i in idx) and idx[0] < idx[1] < idx[2] < idx[3] < idx[4] and all(i >= 0 for i in o_idx) and o_idx == sorted(o_idx) and "columns.clear();pipes.clear();getFF(" in o_melt,
       "the meltdown collects the pipe networks per melting column right before its onMelt (the original's boiler does so inside onMelt, :208-215, before the column is replaced), then the pribris step (:477-498), then handles the overpressure "
       "only when nets were collected (:501), then the mushroom bounds (:541); the set is created fresh for each meltdown (original clears its static set, :443-444)", (idx, o_idx))
    # ---- nothing else changed in the base column
    live, start = lf(st.text(BASEBE)), lf(inp.start[BASEBE])
    strip_imports = lambda s: re.sub(r"import[\w.]+;", "", s)  # noqa: E731
    cl, cst = strip_imports(code_of(live)), strip_imports(code_of(start))
    ports_sig, hook_sig, op_sig = NEO_SIG["ports"], "protected void collectOverpressurePipes(Set<FluidNetMK2> pipes)", NEO_SIG["handleOP"]
    methods = {}
    for key, sig in (("ports", ports_sig), ("hook", hook_sig), ("handle", op_sig)):
        o, c, blanked = method_span(live, sig)
        methods[key] = squash_lit(blanked[blanked.rfind(chr(10), 0, blanked.index(sig)) + 1:c + 1])
    try:
        stripped = cl
        for key in ("ports", "handle"):
            stripped = stripped.replace(methods[key], "", 1)
        stripped = stripped.replace(methods["hook"], "protectedvoidhandleOverpressure(){}", 1)
        stripped = stripped.replace("Set<FluidNetMK2>pipes=newLinkedHashSet<>();", "", 1).replace("if(RBMKDials.getOverpressure())rbmk.collectOverpressurePipes(pipes);", "", 1)
        stripped = stripped.replace("if(RBMKDials.getOverpressure()&&!pipes.isEmpty())handleOverpressure(pipes);", "if(RBMKDials.getOverpressure())handleOverpressure();", 1)
        same = stripped == cst
    except (ValueError, KeyError):
        same = False
    ck("V3.base-nothing-else", same and not hashed_equal(inp, st, BASEBE),
       "RBMKBaseBlockEntity differs from the start copy only by the new imports, the pipes set, the collect call before onMelt, the overpressure call with its argument, the collect hook (replacing the empty handleOverpressure stub), handleOverpressure "
       "and getPortConnections: with those removed the whole file equals the start", (first_diff(stripped, cst) if not same else ""))


# ---------------------------------------------------------------- V4 blocks, registrations, menus, screens, renderers, particle

BLOCK_NAMES = ["rbmk_rod", "rbmk_rod_mod", "rbmk_control", "rbmk_control_mod", "rbmk_control_auto", "rbmk_blank", "rbmk_boiler", "rbmk_reflector", "rbmk_absorber", "rbmk_moderator", "rbmk_cooler", "rbmk_heater", "rbmk_loader"]
NEW_BLOCKS = {"rbmk_control": ("RBMKControlBlock", ",false"), "rbmk_control_mod": ("RBMKControlBlock", ",true"), "rbmk_control_auto": ("RBMKControlAutoBlock", ""), "rbmk_boiler": ("RBMKBoilerBlock", ""),
              "rbmk_cooler": ("RBMKCoolerBlock", ""), "rbmk_heater": ("RBMKHeaterBlock", ""), "rbmk_loader": ("RBMKLoaderBlock", "")}
CLIENT_ONLY = r"net\.minecraft\.client|com\.hbm\.render|inventory\.screens|RBMK\w*Screen|RenderRBMK\w*|RBMKSteamParticle|NuclearTechModClient|ClientProxy"


def strip_block(code, header_re):
    """Remove every `header { ... }` block (header matched by header_re) from comment-blanked code."""
    while True:
        m = re.search(header_re, code)
        if not m:
            return code
        code = code[:m.start()] + code[match_brace(code, code.index("{", m.start())) + 1:]


def split_args(s):
    parts, depth, cur = [], 0, ""
    for ch in s:
        depth += ch in "([{"
        depth -= ch in ")]}"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return parts + [cur.strip()]


GUI_PAT = re.compile(
    r"drawCustomInfoStat\(mouseX, mouseY, guiLeft \+ (?P<ta>\d+), guiTop \+ (?P<tb>\d+), (?P<tc>\d+), (?P<td>\d+), mouseX, mouseY"
    r"|\w+\.(?P<tn>feed|steam)\.renderTankInfo\(this, mouseX, mouseY, guiLeft \+ (?P<ia>\d+), guiTop \+ (?P<ib>\d+), (?P<ic>\d+), (?P<id>\d+)\);"
    r"|\w+\.(?P<rn>feed|steam)\.renderTank\(guiLeft \+ (?P<ra>\d+), guiTop \+ (?P<rb>\d+), this\.zLevel, (?P<rc>\d+), (?P<rd>\d+)\);"
    r"|if\((?P<cond>guiLeft[^{\n]*?)\) \{"
    r"|data\.set(?P<dt>Double|Integer|Boolean)\(\"(?P<dk>\w+)\", (?P<dv>[^;]*)\);"
    r"|(?:if\(type == Fluids\.(?P<ft>\w+)\) )?drawTexturedModalRect\((?P<bl>[^;]*)\);")
GUI_REN = [(r"\bguiLeft\b", "this.leftPos"), (r"\bguiTop\b", "this.topPos"), (r"\bxSize\b", "this.imageWidth"), (r"\bySize\b", "this.imageHeight")]
GUI_PUT = {"Double": "Double", "Integer": "Int", "Boolean": "Boolean"}


def gui_fragments(text):
    """The NEO statements (squashed) that the original GUI's drawing, tooltip and click statements map to, in source order. The ReaSim power widget is dropped."""
    code = strip_block(blank_comments(text), r"if\s*\(\s*rod\.isPowered\(\)\s*\)\s*\{")
    frags = []
    for m in GUI_PAT.finditer(code):
        g = m.groupdict()
        if g["ta"]:
            frags.append(sq(f"this.drawCustomInfoStat(guiGraphics,mouseX,mouseY,this.leftPos+{g['ta']},this.topPos+{g['tb']},{g['tc']},{g['td']},mouseX,mouseY,"))
        elif g["tn"]:
            frags.append(sq(f"be.{g['tn']}.renderTankTooltip(guiGraphics,mouseX,mouseY,this.leftPos+{g['ia']},this.topPos+{g['ib']},{g['ic']},{g['id']});"))
        elif g["rn"]:
            frags.append(sq(f"be.{g['rn']}.renderTank(this.leftPos+{g['ra']},this.topPos+{g['rb']},0,{g['rc']},{g['rd']});"))
        elif g["cond"]:
            frags.append(sq("if(" + rewrite(g["cond"], [(r"\bguiLeft\b", "leftPos"), (r"\bguiTop\b", "topPos")]) + "){"))
        elif g["dt"]:
            frags.append(sq(f'data.put{GUI_PUT[g["dt"]]}("{g["dk"]}",{g["dv"]});'))
        else:
            args = rewrite(g["bl"], GUI_REN)
            frags.append(sq((f"if(type==Fluids.{g['ft']})" if g["ft"] else "") + "guiGraphics.blit(TEXTURE," + args + ");"))
    return frags


def ordered_missing(code, frags):
    """The fragments not found in code at or after the end of the previous one."""
    pos, missing = 0, []
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            missing.append(f)
        else:
            pos = i + len(f)
    return missing


def gui_check(ck, cid, label, inp, st, okey, path, extra=()):
    o = inp.o[okey]
    oc = blank_comments(o)
    frags = gui_fragments(o)
    code = cs(st, path)
    size = re.search(r"this\.xSize = (\d+);\s*this\.ySize = (\d+);", oc)
    tex = re.search(r"textures/gui/reactors/(\w+\.png)", oc)
    lt = re.search(r"drawString\(name, this\.xSize / 2 - this\.fontRendererObj\.getStringWidth\(name\) / 2, (\d+), (\d+)\)", oc)
    li = re.search(r'drawString\(I18n\.format\("container\.inventory"\), (\d+), this\.ySize - (\d+) \+ (\d+), (\d+)\)', oc)
    obj = lambda s: rewrite(s, [(r"\b(?:rod|boiler)\.", "be.")])  # noqa: E731
    stat = [sq(f"int{m[1]}={obj(m[2])};") for m in re.finditer(r"int (\w+) = ([^;]*(?:rod|boiler)\.[^;]*);", oc)]
    stat += [sq(f"if({m[1]}>{m[2]}){m[1]}++;") for m in re.finditer(r"if\((\w) > (\d+)\) \w\+\+;", oc)]
    ok = bool(frags and size and tex and lt and li)
    miss, lab = [], ""
    if ok:
        want_lab = sq(f"guiGraphics.drawString(this.font,this.title,this.imageWidth/2-this.font.width(this.title)/2,{lt[1]},{lt[2]},false);guiGraphics.drawString(this.font,this.playerInventoryTitle,{li[1]},this.imageHeight-{li[2]}+{li[3]},{li[4]},false);")
        miss = ordered_missing(code, frags) + [x for x in stat + list(extra) if x not in code]
        miss += [x for x in (sq(f"this.imageWidth={size[1]};this.imageHeight={size[2]};"), want_lab, sq(f'NuclearTechMod.withDefaultNamespace("textures/gui/reactors/{tex[1]}")')) if x not in code]
    ck(cid, ok and not miss and len(frags) >= 4, label, (miss, ok, len(frags)))
    return frags


def v4_registrations(ck, inp, st):
    ov = need_ov(inp)
    nb, ct, bet, mt, nmc, cp = (cs(st, p) for p in (NB, CT, BET, MT, NMC, CP))
    mb = lf(inp.o["mb"])
    o_line = {}
    for i, line in enumerate(mb.split("\n"), 1):
        m = re.match(r"\s*(?:GameRegistry\.registerBlock\((\w+),|register\((\w+)\);)", line)
        if m and (m[1] or m[2]) in BLOCK_NAMES:
            o_line.setdefault(m[1] or m[2], i)
    o_order = sorted(o_line, key=o_line.get)
    n_pos = {n: nb.find(f'RBMK_{n[5:].upper()}=register("{n}"') for n in BLOCK_NAMES}
    t_pos = {n: ct.find(f"output.accept(NtmBlocks.RBMK_{n[5:].upper()});") for n in BLOCK_NAMES}
    n_order = sorted(BLOCK_NAMES, key=lambda n: n_pos[n])
    t_order = sorted(BLOCK_NAMES, key=lambda n: t_pos[n])
    ck("V4.registration-order", set(o_order) == set(BLOCK_NAMES) and all(v >= 0 for v in n_pos.values()) and all(v >= 0 for v in t_pos.values()) and n_order == o_order and t_order == o_order,
       "the RBMK blocks are declared in NtmBlocks and listed in the machine creative tab in the original registration order of ModBlocks.java:3107-3137 (rods, control, control_mod, control_auto, blank, boiler, reflector, absorber, moderator, "
       "cooler, heater, loader)", (o_order, n_order, t_order))
    hard = re.search(r"this\.setHardness\(([\d.]+)F\);\s*this\.setResistance\(([\d.]+)F\);", inp.o["rbase"])
    lo = re.search(r'rbmk_loader = new RBMKLoader\(Material\.iron\)\.setBlockName\("rbmk_loader"\)\.setCreativeTab\(MainRegistry\.machineTab\)\.setHardness\(([\d.]+)F\)\.setResistance\(([\d.]+)F\)', mb)
    bad = []
    if hard and lo:
        f = lambda s: f"{float(s):.1f}F"  # noqa: E731
        for n, (cls, extra) in NEW_BLOCKS.items():
            h, r = (lo[1], lo[2]) if n == "rbmk_loader" else (hard[1], hard[2])
            want = sq(f'{n.upper()}=register("{n}",()->new{cls}(BlockBehaviour.Properties.of().strength({f(h)},{f(r)}).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops(){extra}));')
            if f"{n.upper()}=register(" not in nb or want not in nb.replace("DeferredBlock<Block>", ""):
                bad.append(n)
    ck("V4.block-properties", bool(hard and lo) and not bad and "noOcclusion" not in "".join(x for x in nb.split(";") if any(f'"{n}"' in x for n in NEW_BLOCKS)),
       "the seven new blocks are the original classes with the original strength (RBMKBase :52-56 hardness 3 / resistance 30; RBMKLoader hardness 50 / resistance 60, ModBlocks.java:2143), iron sound, pickaxe-only drops; opaque like the original "
       "(no isOpaqueCube override); moderated = false / true for rbmk_control / rbmk_control_mod", (bad, hard and hard.groups(), lo and lo.groups()))
    orig_rc = re.search(r'rbmk_control = new RBMKControl\(false\)', mb) and re.search(r'rbmk_control_mod = new RBMKControl\(true\)', mb)
    want_types = [
        'RBMK_CONTROL=BLOCK_ENTITY_TYPES.register("rbmk_control",()->BlockEntityType.Builder.of(RBMKControlManualBlockEntity::new,NtmBlocks.RBMK_CONTROL.get(),NtmBlocks.RBMK_CONTROL_MOD.get()).build(null));',
        'RBMK_CONTROL_AUTO=BLOCK_ENTITY_TYPES.register("rbmk_control_auto",()->BlockEntityType.Builder.of(RBMKControlAutoBlockEntity::new,NtmBlocks.RBMK_CONTROL_AUTO.get()).build(null));',
        'RBMK_BOILER=BLOCK_ENTITY_TYPES.register("rbmk_boiler",()->BlockEntityType.Builder.of(RBMKBoilerBlockEntity::new,NtmBlocks.RBMK_BOILER.get()).build(null));',
        'RBMK_HEATER=BLOCK_ENTITY_TYPES.register("rbmk_heater",()->BlockEntityType.Builder.of(RBMKHeaterBlockEntity::new,NtmBlocks.RBMK_HEATER.get()).build(null));',
        'RBMK_COOLER=BLOCK_ENTITY_TYPES.register("rbmk_cooler",()->BlockEntityType.Builder.of(RBMKCoolerBlockEntity::new,NtmBlocks.RBMK_COOLER.get()).build(null));']
    ck("V4.block-entity-types", bool(orig_rc) and all(w in bet for w in want_types) and "RBMKLoaderBlockEntity" not in bet and "rbmk_loader\"," not in bet and "createNewTileEntity" not in inp.o["rload"],
       "one block entity type for both manual control rods (the original RBMKControl creates TileEntityRBMKControlManual for rbmk_control and rbmk_control_mod, ModBlocks.java:2117-2118), one each for the automatic rod, boiler, heater and cooler, "
       "and none for the loader (a plain block in the original)", [w for w in want_types if w not in bet])
    want_menus = ['RBMK_CONTROL=reg("rbmk_control",RBMKControlMenu::new);', 'RBMK_CONTROL_AUTO=reg("rbmk_control_auto",RBMKControlAutoMenu::new);', 'RBMK_BOILER=reg("rbmk_boiler",RBMKBoilerMenu::new);', 'RBMK_HEATER=reg("rbmk_heater",RBMKHeaterMenu::new);']
    want_screens = ["event.register(NtmMenuTypes.RBMK_CONTROL.get(),RBMKControlScreen::new);", "event.register(NtmMenuTypes.RBMK_CONTROL_AUTO.get(),RBMKControlAutoScreen::new);",
                    "event.register(NtmMenuTypes.RBMK_BOILER.get(),RBMKBoilerScreen::new);", "event.register(NtmMenuTypes.RBMK_HEATER.get(),RBMKHeaterScreen::new);"]
    ck("V4.menu-screen-registration", all(mt.count(w) == 1 for w in want_menus) and all(nmc.count(w) == 1 for w in want_screens) and "RBMK_COOLER" not in mt, "the control, automatic control, boiler and heater menus are registered with their menu classes and "
       "their screens in the client entry, each exactly once (the cooler and the loader have no GUI in the original)", ([w for w in want_menus if mt.count(w) != 1], [w for w in want_screens if nmc.count(w) != 1]))
    want_tesr = ["BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_COOLER.get(),newRenderRBMKLid<>());", "BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_CONTROL.get(),newRenderRBMKControl());",
                 "BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_CONTROL_AUTO.get(),newRenderRBMKControl());", "BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_BOILER.get(),newRenderRBMKPiped<>());",
                 "BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_HEATER.get(),newRenderRBMKPiped<>());"]
    orig_cp = inp.o["cproxy"]
    ck("V4.renderer-registration", all(w in cp for w in want_tesr) and "TileEntityRBMKControlManual.class, new RenderRBMKControlRod()" in orig_cp and "TileEntityRBMKControlAuto.class, new RenderRBMKControlRod()" in orig_cp
       and "RenderRBMKControlRod" not in "".join(x for x in orig_cp.split("\n") if "Boiler" in x or "Heater" in x or "Cooler" in x),
       "ClientProxy: both control rods use the rod renderer (original :433-434), boiler and heater the pipe-stub renderer (the original draws their stubs and lid in the block's ISBRH, RenderRBMKControl :98-129), "
       "the cooler the plain lid renderer (a passive column in the original)", [w for w in want_tesr if w not in cp])
    common = [PIPED, CBLK, ABLK, BOIBLK, HEABLK, COOBLK, LOADBLK, CTL, MAN, AUT, BOI, HEA, COO, CMENU, AMENU, BMENU, HMENU, NB, BET, MT, CT, BASEBE]
    leak = [p for p in common if st.has(p) and re.search(CLIENT_ONLY, blank_comments(lf(st.text(p))))]
    client_ok = all(f"importcom.hbm.inventory.screens.{c}Screen;" in nmc for c in ("RBMKControl", "RBMKControlAuto", "RBMKBoiler", "RBMKHeater")) and "RBMKSteamParticle" in nmc
    ck("V4.client-isolation", not leak and client_ok, "no common class (blocks, block entities, menus, registries, base column) refers to a screen, renderer, particle or client entry; the screens and the particle are used only by NuclearTechModClient "
       "and the renderers by ClientProxy, so a dedicated server loads none of them", (leak, client_ok))


def v4_blocks(ck, inp, st):
    ov = need_ov(inp)
    code = {p: cs(st, p) for p in (PIPED, CBLK, ABLK, BOIBLK, HEABLK, COOBLK)}
    o_own = re.search(r"public boolean hasOwnLid\(\) \{(.*?)\}", inp.o["rbase"], re.S)
    own = set(re.findall(r"this == ModBlocks\.(\w+)", o_own[1])) if o_own else set()
    ck("V4.piped-base", "publicabstractclassRBMKPipedBaseBlockextendsRBMKBaseBlock{" in code[PIPED]
       and "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};" in code[PIPED]
       and "BlockPoscore=level.isClientSide?this.walkToCore(level,pos):this.findCore(level,pos);" in code[PIPED]
       and "if(core==null||!(level.getBlockEntity(core)instanceofRBMKBaseBlockEntityrbmk))returnItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;" in code[PIPED]
       and "if(stack.getItem()instanceofRBMKLidItem){if(!rbmk.hasLid())returnItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;}returnItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;" in code[PIPED]
       and "returnthis.standardOpenBehavior(level,pos,player);" in code[PIPED] and "isOpaqueCube" not in inp.o["rpiped"],
       "RBMKPipedBaseBlock reproduces RBMKBase.openInv (:105-125): the core is looked up from any cell, nothing is found = not consumed, a lid item on a column without a lid is not consumed (the lid is placed), otherwise the GUI opens "
       "unless the player sneaks (standardOpenBehavior); only the core ticks, on both sides (the control rod's client copy of lastLevel)")
    ck("V4.own-lid", own == {"rbmk_control", "rbmk_control_auto", "rbmk_control_mod", "rbmk_control_reasim", "rbmk_control_reasim_auto"}
       and "protectedbooleanhasOwnLid(){returntrue;}" in code[CBLK] and "protectedbooleanhasOwnLid(){returntrue;}" in code[ABLK] and all("hasOwnLid" not in code[p] for p in (BOIBLK, HEABLK, COOBLK)),
       "only the control rods carry their own lid (original RBMKBase.hasOwnLid :68-71 lists control, control_mod, control_auto and the two ReaSim rods): control and automatic control override hasOwnLid, boiler, heater and cooler do not "
       "(they take lids)", own)
    o_fluid = lambda t: re.search(r"return new TileEntityProxyCombo\(([^)]*)\)(\.fluid\(\))?;", t)  # noqa: E731
    r_c, r_a, r_b, r_h, r_k = (lf(inp.o[k]) for k in ("rctl", "rauto", "rboi", "rhea", "rcoo"))
    pb, ph, pc = o_fluid(r_b), o_fluid(r_h), re.search(r"return new TileEntityProxyCombo\(\)\.fluid\(\);", r_k)
    pctl = re.search(r"return new TileEntityProxyCombo\(\);", r_c)
    ck("V4.block-entities", pb and ph and pc and pctl and pb[1] == "false, false, true" and ph[1] == "false, false, true" and not pb[2] and not ph[2]
       and "switch(state.getValue(TYPE)){caseCORE->newRBMKControlManualBlockEntity(pos,state);caseEXTRA->newProxyComboBlockEntity(pos,state);default->null;}" in code[CBLK]
       and "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;returnnewRBMKControlAutoBlockEntity(pos,state);" in code[ABLK]
       and "caseCORE->newRBMKBoilerBlockEntity(pos,state);caseEXTRA->newProxyComboBlockEntity(pos,state).fluid();default->null;" in code[BOIBLK]
       and "caseCORE->newRBMKHeaterBlockEntity(pos,state);caseEXTRA->newProxyComboBlockEntity(pos,state).fluid();default->null;" in code[HEABLK]
       and "caseCORE->newRBMKCoolerBlockEntity(pos,state);caseEXTRA->newProxyComboBlockEntity(pos,state).fluid();default->null;" in code[COOBLK],
       "block entities per cell as the original createNewTileEntity: manual rod core + a plain proxy on the extra cell (only RoR forwarded, RBMKControl :41-46), automatic rod core only (RBMKControlAuto :34-38), boiler and heater core + "
       "fluid-only proxy (TileEntityProxyCombo(false, false, true)), cooler core + fluid proxy (TileEntityProxyCombo().fluid())", (pb and pb.groups(), ph and ph.groups()))
    ck("V4.cooler-block", "publicclassRBMKCoolerBlockextendsRBMKBaseBlock{" in code[COOBLK] and "useItemOn" not in code[COOBLK] and "useWithoutItem" not in code[COOBLK] and "onBlockActivated" not in inp.o["rcoo"] and "extends RBMKBase " in inp.o["rcoo"]
       and "if(state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};" in code[COOBLK],
       "the cooler is a plain column (original RBMKCooler extends RBMKBase, no onBlockActivated, no GUI) whose core ticks")
    # ---- menus
    cont = {k: otext(O + f"inventory/container/{k}.java") for k in ("ContainerRBMKGeneric", "ContainerRBMKControl", "ContainerRBMKControlAuto", "ContainerRBMKHeater")}
    grid = {k: (re.search(r"new Slot\(invPlayer, j \+ i \* 9 \+ 9, (\d+) \+ j \* 18, (\d+) \+ i \* 18 \+ (\d+)\)", t), re.search(r"new Slot\(invPlayer, i, (\d+) \+ i \* 18, (\d+) \+ (\d+)\)", t)) for k, t in cont.items()}
    pos = {k: (g[0][1], int(g[0][2]) + int(g[0][3]), int(g[1][2]) + int(g[1][3])) if g[0] and g[1] and g[0][1] == g[1][1] else None for k, g in grid.items()}
    menus = {CMENU: ("ContainerRBMKControl", "RBMK_CONTROL", "RBMKControlManualBlockEntity"), AMENU: ("ContainerRBMKControlAuto", "RBMK_CONTROL_AUTO", "RBMKControlAutoBlockEntity"),
             BMENU: ("ContainerRBMKGeneric", "RBMK_BOILER", "RBMKBoilerBlockEntity"), HMENU: ("ContainerRBMKHeater", "RBMK_HEATER", "RBMKHeaterBlockEntity")}
    bad = []
    for path, (cname, mtype, be) in menus.items():
        mc = cs(st, path)
        p = pos[cname]
        want = f"super(NtmMenuTypes.{mtype}.get(),id,be);" + ("" if path != HMENU else "this.addSlot(") if p else ""
        if not p or f"super(NtmMenuTypes.{mtype}.get(),id,be);" not in mc or f"this.playerInv(inventory,{p[0]},{p[1]},{p[2]});" not in mc or f"extendsMenuBase<{be}>" not in mc:
            bad.append(path)
    quick_null = all(re.search(r"transferStackInSlot\([^)]*\) \{\s*return null;", cont[k]) for k in ("ContainerRBMKControl",)) and "returnnull;" in squash_lit(blank_comments(cont["ContainerRBMKControlAuto"]))
    gen_body = squash_lit(blank_comments(cont["ContainerRBMKGeneric"]))
    gen_null = "if(var4!=null&&var4.getHasStack()){returnnull;}returnvar3;" in gen_body and "ItemStackvar3=null;" in gen_body
    ck("V4.menus", not bad and quick_null and gen_null and all(cs(st, p).count("returnItemStack.EMPTY;") == 1 for p in (CMENU, AMENU, BMENU)) and cs(st, HMENU).count("returnItemStack.EMPTY;") >= 1,
       "the four menus hold the player inventory exactly where the original containers put it (x 8, rows from y 84 + 20, hotbar y 142 + 20) and take the block entity of their kind; control, automatic control and boiler move nothing on shift-click "
       "(original transferStackInSlot returns null in every branch)", (bad, pos))
    ho = squash_lit(blank_comments(cont["ContainerRBMKHeater"]))
    slot_o = re.search(r"new Slot\(tile, (\d+), (\d+), (\d+)\)", cont["ContainerRBMKHeater"])
    hm = cs(st, HMENU)
    anchors = [("if(par2<=rbmk.getSizeInventory()-1){if(!this.mergeItemStack(var5,rbmk.getSizeInventory(),this.inventorySlots.size(),true)){returnnull;}}elseif(!this.mergeItemStack(var5,0,rbmk.getSizeInventory(),false)){returnnull;}",
                "if(index<=be.getContainerSize()-1){if(!this.moveItemStackTo(stack,be.getContainerSize(),this.slots.size(),true))returnItemStack.EMPTY;}elseif(!this.moveItemStackTo(stack,0,be.getContainerSize(),false)){returnItemStack.EMPTY;}"),
               ("if(var5.stackSize==0){var4.putStack((ItemStack)null);}else{var4.onSlotChanged();}", "if(stack.isEmpty()){slot.setByPlayer(ItemStack.EMPTY);}else{slot.setChanged();}")]
    ck("V4.heater-menu", slot_o is not None and f"this.addSlot(newSlot(be,{slot_o[1]},{slot_o[2]},{slot_o[3]}){{" in hm and all(a in ho and b in hm for a, b in anchors)
       and "returnstack.getItem()instanceofIItemFluidIdentifier;" in hm,
       "the heater menu has the original's single slot 0 at (41, 45) and the original shift-click logic (container slots to the inventory and back, :31-56); NEO only restricts the slot to fluid identifiers (as HeaterHeatexBlockEntity)",
       (slot_o and slot_o.groups(), [a in ho for a, _ in anchors], [b in hm for _, b in anchors]))
    be_menus = {MAN: "RBMKControlMenu", AUT: "RBMKControlAutoMenu", BOI: "RBMKBoilerMenu", HEA: "RBMKHeaterMenu"}
    ck("V4.menu-providers", all(f"returnnew{m}(containerId,inventory,this);" in cs(st, p) for p, m in be_menus.items()), "each GUI block entity opens the menu of its kind")


def v4_screens(ck, inp, st):
    gui_check(ck, "V4.screen-control", "RBMKControlScreen equals GUIRBMKControl: 176 x 186, texture gui_rbmk_control.png, the insertion tooltip at (71, 29, 16, 56), five insertion buttons (118..148, 26 + 11k) sending `level` 1 - 0.25k, five colour buttons "
              "(28..40, 26 + 11k) sending `color` k, the rod bar (75, 29) from (176, 56 - h) with h = (int)(56 * (1 - level)), the selected colour (28, 26 + 11c) from (184, 10c), labels at y 6 and ySize - 96 + 2 "
              "(the ReaSim power widget :38-40, :94-96 is not ported)", inp, st, "gctl", CSCREEN, [sq('Component.literal((int)(be.level*100)+"%")')])
    frags = gui_check(ck, "V4.screen-auto", "RBMKControlAutoScreen equals GUIRBMKControlAuto: 176 x 186, texture gui_rbmk_control_auto.png, the tooltips (124, 29, 16, 56), (58, 26, 28, 19), (61, 48 / 59 / 70, 22, 10), (28, 26 / 37 / 48 / 59 / 70, 30, 10), "
                      "the save button (28, 70, 30 x 10) and the function buttons (61, 48 + 11k, 22 x 10) sending `function` k and the four doubles, the level bar (124, 29) and the function icon (59, 27) from (184, 19f)", inp, st, "gaut", ASCREEN,
                      [sq('Component.literal((int)(be.level*100)+"%")')])
    oc = blank_comments(inp.o["gaut"])
    code = cs(st, ASCREEN)
    fld = re.search(r"new GuiTextField\(this\.fontRendererObj, guiLeft \+ (\d+), guiTop \+ (\d+) \+ (\d+) \* i, (\d+), (\d+)\)", oc)
    ml = re.search(r"if\(i < 2\)\s*this\.fields\[i\]\.setMaxStringLength\((\d+)\);\s*else\s*this\.fields\[i\]\.setMaxStringLength\((\d+)\);", oc)
    sets = re.findall(r"this\.fields\[(\d)\]\.setText\(String\.valueOf\(\(int\)rod\.(\w+)\)\)", oc)
    clamp = re.search(r"double clamp = k < 2 \? (\d+) : (\d+);", oc)
    vals = re.search(r"double\[\] vals = new double\[\] \{(.*?)\};", oc)
    ok = bool(fld and ml and len(sets) == 4 and clamp and vals)
    want = []
    if ok:
        want = [sq(f"this.fields[i]=newEditBox(this.font,this.leftPos+{fld[1]},this.topPos+{fld[2]}+{fld[3]}*i,{fld[4]},{fld[5]},Component.empty());"), sq("this.fields[i].setBordered(false);"),
                sq(f"if(i<2)this.fields[i].setMaxLength({ml[1]});elsethis.fields[i].setMaxLength({ml[2]});")] + [sq(f"this.fields[{i}].setValue(String.valueOf((int)be.{n}));") for i, n in sets]
        want += [sq(f"doubleclamp=k<2?{clamp[1]}:{clamp[2]};"), sq("intj=(int)Mth.clamp(parsed,0,clamp);fields[k].setValue(j+\"\");vals[k]=j;"), sq('fields[k].setValue("0");'), sq(f"double[]vals=newdouble[]{{{vals[1]}}};")]
        want += [sq(f'data.putDouble("{k}",vals[{i}]);') for i, k in enumerate(("levelUpper", "levelLower", "heatUpper", "heatLower"))]
    miss = [w for w in want if w not in code]
    ck("V4.screen-auto-fields", ok and not miss and [n for _, n in sets] == ["levelUpper", "levelLower", "heatUpper", "heatLower"] and len(frags) >= 10,
       "the four parameter fields sit at (30, 27 + 11i) 26 wide and 6 high as the original (GUIRBMKControlAuto.java:45; the unbordered EditBox draws its text at its top, like GuiTextField), hold levelUpper, levelLower, heatUpper, heatLower, take 3, 3, 4, 4 characters, and the save button "
       "clamps them to 0..100 and 0..9999 as ints (non-numbers become 0) before sending the four doubles", (ok, miss))
    gui_check(ck, "V4.screen-boiler", "RBMKBoilerScreen equals GUIRBMKBoiler: 176 x 186, texture gui_rbmk_boiler.png, feed tooltip (126, 24, 16, 56), steam tooltip (89, 39, 8, 28), the compression switch (33..53, 21..85) sending `compression` true, feed bar "
              "i = fill * 58 / max at (126, 82 - i) from (176, 58 - i) 14 x i, steam bar j = fill * 22 / max with j++ above 0 and again above 22 at (91, 65 - j) from (190, 24 - j) 4 x j, the grade icon (36, 24) 14 x 58 from u 194 / 208 / 222 / 236",
              inp, st, "gboi", BSCREEN)
    gui_check(ck, "V4.screen-heater", "RBMKHeaterScreen equals GUIRBMKHeater: 176 x 186, texture gui_rbmk_heater.png, tank tooltips (68, 24, 16, 58) and (126, 24, 16, 58), tanks drawn 14 x 58 at y + 82, icons (72, 72) from (176, 0) and (130, 72) from (186, 0), "
              "both 10 x 10", inp, st, "ghea", HSCREEN)
    # the original sends the button press whatever the mouse button; NEO accepts only the left button for the control rods' buttons (the container screen would otherwise swallow every click)
    cc = cs(st, CSCREEN)
    bc = cs(st, BSCREEN)
    ck("V4.screen-click-rules", "if(button!=GLFW.GLFW_MOUSE_BUTTON_LEFT)returnsuper.mouseClicked(x,y,button);" in cc and "button" not in bc.split("mouseClicked(doublex,doubley,intbutton){")[1].split("returnsuper.mouseClicked")[0]
       and "if(handled)returntrue;if(button!=GLFW.GLFW_MOUSE_BUTTON_LEFT)returnsuper.mouseClicked(x,y,button);" in cs(st, ASCREEN),
       "click handling: the buttons are tested before the container's own handling (it would consume every click inside the GUI); the control and automatic rods accept the left button only (NEO choice), the boiler's compression switch takes any "
       "button, as the original (no button test in GUIRBMKBoiler :41-52)")


def v4_render(ck, inp, st):
    rb = lf(otext(O + "render/block/RenderRBMKControl.java"))
    rt = lf(otext(O + "render/tileentity/RenderRBMKControlRod.java"))
    cp, cc = cs(st, RPIPED), cs(st, RCONTROL)
    world = rb[rb.index("public boolean renderWorldBlock"):]
    bounds = [m.groups() for m in re.finditer(r"setRenderBounds\(([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)\)", world)]
    pipes = [b for b in bounds if b[4] == "0.125"]
    heights = {b[4] for b in pipes}
    icons = re.findall(r'registerIcon\(this\.getTextureName\(\) \+ "(_pipe_\w+)"\)', lf(inp.o["rpiped"]))
    want_pipes = ""
    if len(pipes) == 4 and len(heights) == 1 and pipes[0][1] == "0":
        want_pipes = sq("privatestaticfinalfloat[][]PIPES=newfloat[][]{" + ",".join(f"{{{b[0]}F,{b[2]}F,{b[3]}F,{b[5]}F}}" for b in pipes) + f"}};privatestaticfinalfloatPIPE_HEIGHT={pipes[0][4]}F;")
    ck("V4.piped-renderer", bool(want_pipes) and want_pipes in cp and icons == ["_pipe_top", "_pipe_side"] and 'texture(column,"_pipe_top")' in cp and 'texture(column,"_pipe_side")' in cp
       and "box(topBuf,sideBuf,pose,light,packedOverlay,pipe[0],top,pipe[1],pipe[2],top+PIPE_HEIGHT,pipe[3]);" in cp and "if(be.getLid()!=LidType.NONE){super.render(be,partialTicks,poseStack,buffer,packedLight,packedOverlay);return;}" in cp
       and "textures/block/rbmk/" in cp,
       "RenderRBMKPiped draws the four pipe stubs of the original ISBRH (RenderRBMKControl :120-127: x/z 0.0625..0.4375 and 0.5625..0.9375, 0.125 high) on top of the column's extra block, the top and bottom faces with <name>_pipe_top and the sides "
       "with <name>_pipe_side (RBMKPipedBase.getIcon :19-26), the lid of RenderRBMKLid instead while the column has one", (pipes, icons))
    names = re.findall(r"rbmk_control_(\w+)\.png", rt)
    std = re.search(r'textureStandard = new ResourceLocation\(RefStrings\.MODID \+ ":textures/blocks/rbmk/(\w+)\.png"\)', rt)
    auto = re.search(r'textureAuto = new ResourceLocation\(RefStrings\.MODID \+ ":textures/blocks/rbmk/(\w+)\.png"\)', rt)
    rm = cs(st, RM)
    colors = [n for n in names if n not in ("auto",)]
    want_tex = sq("RBMK_CONTROL_COLOR_TEX=newResourceLocation[]{" + ",".join(f'NuclearTechMod.withDefaultNamespace("textures/block/rbmk/rbmk_control_{n}.png")' for n in colors) + "};")
    ck("V4.rod-textures", std and auto and colors == ["red", "yellow", "green", "blue", "purple"] and want_tex in rm and f'RBMK_CONTROL_TEX=NuclearTechMod.withDefaultNamespace("textures/block/rbmk/{std[1]}.png");' in rm
       and f'RBMK_CONTROL_AUTO_TEX=NuclearTechMod.withDefaultNamespace("textures/block/rbmk/{auto[1]}.png");' in rm
       and "if(crm.color==null)texture=ResourceManager.RBMK_CONTROL_TEX;elsetexture=ResourceManager.RBMK_CONTROL_COLOR_TEX[crm.color.ordinal()];" in cc and "ResourceLocationtexture=ResourceManager.RBMK_CONTROL_AUTO_TEX;" in cc
       and "if(beinstanceofRBMKControlManualBlockEntitycrm)" in cc,
       "the rod head texture is the automatic rod's rbmk_control_auto, or for a manual rod rbmk_control without a colour group, else rbmk_control_<red|yellow|green|blue|purple> by colour ordinal (RenderRBMKControlRod :155-199)",
       (std and std[1], names))
    rods = [re.search(r"rbmk_rods(?:_vbo)? = new HFRWavefrontObject\(new ResourceLocation\(RefStrings\.MODID, \"models/rbmk/rbmk_rods\.obj\"\)\)\.noSmooth\(\)", lf(inp.o["cproxy"]) + lf(otext(O + "main/ResourceManager.java")))]
    ck("V4.rod-head", "for(into=1;o<16;o++){if(be.getLevel().getBlockState(be.getBlockPos().above(o)).is(block)){offset=o;}else{break;}}" in cc and "intlight=LevelRenderer.getLightColor(be.getLevel(),be.getBlockPos().above(offset+1));" in cc
       and "doublelevel=be.lastLevel+(be.level-be.lastLevel)*partialTicks;" in cc and "RenderContext.translate(0.5,offset,0.5);RenderContext.translate(0,(float)level,0);" in cc and 'ResourceManager.rbmk_rods.renderPart("Lid");' in cc
       and "for(into=1;o<16;o++){if(te.getWorldObj().getBlock(te.xCoord,te.yCoord+o,te.zCoord)==te.getBlockType()){offset=o;}else{break;}}" in squash_lit(blank_comments(rt)) and "GL11.glTranslated(x+0.5,y+offset,z+0.5);" in squash_lit(blank_comments(rt))
       and 'renderPart("Lid")' in rt and "control.lastLevel+(control.level-control.lastLevel)*i" in squash_lit(blank_comments(rt)) and "getLightBrightnessForSkyBlocks(control.xCoord,control.yCoord+offset+1,control.zCoord,0)" in squash_lit(blank_comments(rt))
       and '"models/obj/rbmk/rbmk_rods.obj").noSmooth().asVBO()' in rm and rods[0] is not None,
       "the rod head (part `Lid` of rbmk_rods.obj, smooth shading off) sits at the topmost block of the same kind within 15 above the core, raised by lastLevel + (level - lastLevel) * partialTicks, lit by the block above it "
       "(RenderRBMKControlRod :166-209)")


def v4_particle(ck, inp, st):
    o = blank_comments(inp.o["part"])
    n = cs(st, PARTICLE)
    nm = cs(st, NMC)
    age, alpha, scale = (re.search(p, o) for p in (r"this\.particleMaxAge = (\d+);", r"this\.particleAlpha = ([\d.]+)F;", r"this\.particleScale = ([\d.]+)F;"))
    tex = re.search(r"int texIndex = ([^;]*);", o)
    verts = re.findall(r"tess\.addVertexWithUV\((this\.particleScale [-*\d. ]+), ([^,]*), 0, (\w+), (\w+)\);", o)
    ren = [(r"this\.particleScale", "this.quadSize"), (r"this\.particleAge", "age"), (r"this\.particleMaxAge", "this.lifetime")]
    ok = bool(age and alpha and scale and tex and len(verts) == 4)
    want = []
    if ok:
        want = [sq(f"this.lifetime={age[1]};this.alpha={alpha[1]}F;this.quadSize={scale[1]}F;"), sq(f"inttexIndex={rewrite(tex[1], ren)};")]
        want += [sq(f"consumer.addVertex(matrix,{rewrite(x, ren)},{rewrite(y, ren)},0).setUv({u},{v})") for x, y, u, v in verts]
    miss = [w for w in want if w not in n]
    ck("V4.particle", ok and not miss and "if(this.age++>=this.lifetime)this.dead=true;" in n and "RenderType.LIGHTNING_TRANSPARENCY" in n and "RenderStateShard.COLOR_WRITE" in n and "RenderStateShard.NO_CULL" in n
       and 'if("rbmksteam".equals(type)){ParticleEngineNT.INSTANCE.add(newRBMKSteamParticle(level,x,y,z));}' in nm and "rbmk_jet_steam.png" in n and "this.particleAge++" not in n,
       "RBMKSteamParticle equals ParticleRBMKSteam (:20-100): max age 10, alpha 0.25, scale 4, frame index floor(age / maxAge * 20) % 20 - 1 with the age clamped to the maximum, the quad from scale * -0.25 - 0.9375 to scale * 0.25 - 0.9375 and y -0.25 to "
       "scale - 0.25, additive blending (SRC_ALPHA, ONE) without depth writes; it ages one tick at a time and dies past its age, and the aux effect `rbmksteam` creates it (ClientProxy :1718-1720)", (ok, miss))


# ---------------------------------------------------------------- V5 recipes

SIX = {"rbmk_control": 760, "rbmk_control_auto": 762, "rbmk_loader": 771, "rbmk_boiler": 993, "rbmk_heater": 994, "rbmk_cooler": 995}
# original expression -> (generated JSON ingredient, provider expression, registry id or None for a tag): the NEO items the handoffs name for the original ore dictionary / item stacks
INGR = {
    "GRAPHITE.ingot()": ({"item": "hbmsntm:ingot_graphite"}, "NtmItems.INGOT_GRAPHITE.get()", "ingot_graphite"),
    "ModItems.motor": ({"item": "hbmsntm:motor"}, "NtmItems.MOTOR.get()", "motor"),
    "ModBlocks.rbmk_absorber": ({"item": "hbmsntm:rbmk_absorber"}, "NtmBlocks.RBMK_ABSORBER.get()", "rbmk_absorber"),
    "ModBlocks.rbmk_control": ({"item": "hbmsntm:rbmk_control"}, "NtmBlocks.RBMK_CONTROL.get()", "rbmk_control"),
    "DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ADVANCED)": ({"item": "hbmsntm:circuit_military_grade_board"}, "NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get()", "circuit_military_grade_board"),
    "ModItems.crt_display": ({"item": "hbmsntm:crt_display"}, "NtmItems.CRT_DISPLAY.get()", "crt_display"),
    "STEEL.plate()": ({"tag": "c:plates/steel"}, "NtmTags.Items.PLATES_STEEL", None),
    "CU.ingot()": ([{"item": "hbmsntm:ingot_copper"}, {"item": "minecraft:copper_ingot"}], "Ingredient.of(NtmItems.INGOT_COPPER.get(), Items.COPPER_INGOT)", "ingot_copper"),
    "ModItems.tank_steel": ({"item": "hbmsntm:tank_steel"}, "NtmItems.TANK_STEEL.get()", "tank_steel"),
    "CU.pipe()": ({"item": "hbmsntm:pipe_copper"}, "NtmItems.PIPE_COPPER.get()", "pipe_copper"),
    "CU.shell()": ({"item": "hbmsntm:shell_copper"}, "NtmItems.SHELL_COPPER.get()", "shell_copper"),
    "STEEL.shell()": ({"item": "hbmsntm:shell_steel"}, "NtmItems.SHELL_STEEL.get()", "shell_steel"),
    "ModBlocks.rbmk_blank": ({"item": "hbmsntm:rbmk_blank"}, "NtmBlocks.RBMK_BLANK.get()", "rbmk_blank"),
    "ANY_PLASTIC.ingot()": ({"tag": "ntm:ingots_plastic"}, 'ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"))', None),
    "ModItems.plate_polymer": ({"item": "hbmsntm:plate_polymer"}, "NtmItems.PLATE_POLYMER.get()", "plate_polymer"),
    "ModBlocks.steel_grate": ({"item": "hbmsntm:steel_grate"}, "NtmBlocks.STEEL_GRATE.get()", "steel_grate")}
# the recipe book unlock is NEO's own (the original has no advancements): the column or part the recipe is built around
UNLOCK = {"rbmk_control": "rbmk_absorber", "rbmk_control_auto": "rbmk_control", "rbmk_loader": "tank_steel", "rbmk_boiler": "rbmk_blank", "rbmk_heater": "rbmk_blank", "rbmk_cooler": "rbmk_blank"}


def jload(st, path):
    return json.loads(st.text(path)) if st.has(path) else None


def expected_recipe(name, row):
    block, count, pattern, keys = row
    assert block == name
    return {"type": "minecraft:crafting_shaped", "category": "misc", "key": {k: INGR[v][0] for k, v in keys.items()}, "pattern": pattern, "result": {"count": count, "id": "hbmsntm:" + name}}


def expected_advancement(name):
    u = UNLOCK[name]
    return {"parent": "minecraft:recipes/root",
            "criteria": {"has_" + u: {"conditions": {"items": [{"items": "hbmsntm:" + u}]}, "trigger": "minecraft:inventory_changed"},
                         "has_the_recipe": {"conditions": {"recipe": "hbmsntm:" + name}, "trigger": "minecraft:recipe_unlocked"}},
            "requirements": [["has_the_recipe", "has_" + u]], "rewards": {"recipes": ["hbmsntm:" + name]}}


def provider_rows(rp_text):
    """{recipe id: (result field, count, patterns, {key: expression}, unlock id, unlock expression)} of the ShapedRecipeBuilder rows of NtmRecipeProvider that save an rbmk_* recipe of this batch."""
    code = blank_comments(lf(rp_text))
    rows = {}
    for m in re.finditer(r"ShapedRecipeBuilder\.shaped\(RecipeCategory\.MISC, NtmBlocks\.(\w+)\.get\(\), (\d+)\)(.*?)\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\(\"hbmsntm\", \"(\w+)\"\)\);", code, re.S):
        if m[4] not in SIX:
            continue
        lines = [x.strip() for x in m[3].split("\n") if x.strip()]
        pattern = [re.fullmatch(r'\.pattern\("([^"]*)"\)', x)[1] for x in lines if x.startswith(".pattern(")]
        defines = {}
        for x in lines:
            d = re.fullmatch(r"\.define\('(\w)', (.*)\)", x)
            if d:
                defines[d[1]] = d[2]
        un = [re.fullmatch(r'\.unlockedBy\("(\w+)", has\((.*)\)\)', x) for x in lines if x.startswith(".unlockedBy(")]
        rows[m[4]] = (m[1], int(m[2]), pattern, defines, un[0][1] if un else None, un[0][2] if un else None)
    return rows


def v5_recipes(ck, inp, st):
    need_ov(inp)
    rows = {name: inp.recipe_rows[line] for name, line in SIX.items()}
    ck("V5.original-rows", all(rows[n][0] == n and rows[n][1] == 1 for n in SIX) and all(all(v in INGR for v in rows[n][3].values()) for n in SIX) and len(SIX) == 6,
       "the six original rows (CraftingManager.java:760, :762, :771, :993, :994, :995) each make one block of their name and every ingredient expression has a NEO mapping in this script", [(n, [v for v in rows[n][3].values() if v not in INGR]) for n in SIX])
    if not all(rows[n][0] == n and all(v in INGR for v in rows[n][3].values()) for n in SIX):
        return
    bad = {}
    for n in SIX:
        got = jload(st, RECIPES + n + ".json")
        want = expected_recipe(n, rows[n])
        if got != want:
            bad[n] = (got, want)
    ck("V5.recipes-match", not bad, "each generated recipe is a minecraft:crafting_shaped, category misc, with the original row's pattern (CraftingManager.java:760/762/771/993-995), count 1, the result block and each ingredient mapped to the NEO item or tag "
       "(GRAPHITE ingot -> ingot_graphite, circuit ADVANCED -> circuit_military_grade_board, STEEL.plate() -> c:plates/steel, CU.ingot() -> ingot_copper or the vanilla ingot, CU.pipe()/CU.shell()/STEEL.shell() -> pipe_copper/shell_copper/shell_steel, ANY_PLASTIC.ingot() -> ntm:ingots_plastic)",
       {k: v for k, v in list(bad.items())[:2]})
    bad = {}
    for n in SIX:
        got = jload(st, ADV + "misc/" + n + ".json")
        if got != expected_advancement(n):
            bad[n] = (got, expected_advancement(n))
    ck("V5.advancements", not bad, "each recipe has its recipe-book advancement under advancement/recipes/misc: parent recipes/root, an inventory_changed criterion for the unlock item, the recipe_unlocked criterion, requirements and the reward", {k: v for k, v in list(bad.items())[:2]})
    ck("V5.unlock-is-ingredient", all(("hbmsntm:" + UNLOCK[n]) in [i.get("item") for k, v in (jload(st, RECIPES + n + ".json") or {"key": {}})["key"].items() for i in (v if isinstance(v, list) else [v])] for n in SIX),
       "each recipe's unlock item is one of its own ingredients")
    new = sorted(p for p in st.tree if p.startswith(RECIPES) and p not in inp.base_files)
    new_adv = sorted(p for p in st.tree if p.startswith(ADV) and p not in inp.base_files)
    ck("V5.only-six", new == sorted(RECIPES + n + ".json" for n in SIX) and new_adv == sorted(ADV + "misc/" + n + ".json" for n in SIX),
       "exactly six recipes and six advancements were added; none for rbmk_control_mod (CraftingManager.java:761 needs GRAPHITE.block(), which NEO does not have), the ReaSim rows (:764-765) or the anvil rows", (new, new_adv))
    ck("V5.no-control-mod", not st.has(RECIPES + "rbmk_control_mod.json") and RECIPES + "rbmk_control_mod.json" not in st.tree and ADV + "misc/rbmk_control_mod.json" not in st.tree
       and "RBMK_CONTROL_MOD" not in blank_comments(st.text(RP)) and "rbmk_control_mod" not in blank_comments(st.text(RP)), "there is no rbmk_control_mod recipe, advancement or provider row (the original row at :761 needs GRAPHITE.block())")
    prov = provider_rows(st.text(RP))
    bad = {}
    for n in SIX:
        row, r = prov.get(n), rows[n]
        want = ("RBMK_" + n[len("rbmk_"):].upper(), r[1], r[2], {k: INGR[v][1] for k, v in r[3].items()})
        if row is None or row[:4] != want:
            bad[n] = (row, want)
    ck("V5.provider-rows", len(prov) == 6 and not bad, "NtmRecipeProvider.java registers the six shaped rows with the original patterns, count 1, the mapped ingredient expressions and the recipe id hbmsntm:<name>", {k: v for k, v in list(bad.items())[:2]})
    badu = {n: prov[n][4:] for n in SIX if n in prov and prov[n][4:] != ("has_" + UNLOCK[n], INGR["ModBlocks." + UNLOCK[n]][1] if "ModBlocks." + UNLOCK[n] in INGR else INGR["ModItems." + UNLOCK[n]][1])}
    ck("V5.provider-unlocks", not badu and len(prov) == 6, "each provider row unlocks on has_<unlock item> of the same item the generated advancement names", badu)
    # every NEO id the recipes use exists
    ids_items, ids_blocks = lf(st.text(NITEMS)) if st.has(NITEMS) else "", lf(st.text(NB))
    missing = []
    for n in SIX:
        for ing in rows[n][3].values():
            rid = INGR[ing][2]
            if rid is not None and f'register("{rid}"' not in ids_items and f'register("{rid}"' not in ids_blocks:
                missing.append((n, rid))
        if f'register("{n}"' not in ids_blocks:
            missing.append((n, "result"))
    ck("V5.ids-registered", not missing, "every item and block id the six recipes use or make is registered in NtmItems or NtmBlocks", missing)
    ck("V5.tags", 'commonTag("plates/steel")' in st.text(NTAGS) and 'ResourceLocation.fromNamespaceAndPath("c", name)' in st.text(NTAGS) and "PLATES_STEEL" in st.text(ITAGP)
       and 'ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")' in st.text(ITAGP),
       "the tags the recipes use exist in the NEO tag sources: c:plates/steel (NtmTags.Items.PLATES_STEEL, filled by NtmItemTagProvider) and ntm:ingots_plastic")
    ck("V5.anvil-untouched", hashed_equal(inp, st, ANVIL) and not re.search(r"RBMK_(CONTROL|BOILER|COOLER|HEATER|LOADER)", blank_comments(st.text(ANVIL))),
       "AnvilRecipes.java is byte-equal to the start copy and has no rbmk_control / boiler / cooler / heater / loader row: the five tier-4 recycling rows (AnvilRecipes.java:885-901, :941-951) are not ported (the 4-tier anvil is unreachable in NEO)")


# ---------------------------------------------------------------- V6 datagen outputs

NEW6 = ["rbmk_control", "rbmk_control_mod", "rbmk_control_auto", "rbmk_boiler", "rbmk_heater", "rbmk_cooler", "rbmk_loader"]
COLUMN6 = NEW6[:6]
START_PICKAXE_RBMK = ["hbmsntm:rbmk_rod", "hbmsntm:rbmk_rod_mod", "hbmsntm:rbmk_blank", "hbmsntm:rbmk_reflector", "hbmsntm:rbmk_absorber", "hbmsntm:rbmk_moderator"]


def expected_generated():
    out = []
    for n in NEW6:
        out += [G_STATE + n + ".json", G_BMODEL + n + ".json", G_IMODEL + n + ".json", G_LOOT + n + ".json"]
    out += [RECIPES + n + ".json" for n in SIX] + [ADV + "misc/" + n + ".json" for n in SIX]
    return sorted(out)


def expected_block_model(n):
    if n == "rbmk_loader":
        return {"parent": "minecraft:block/cube_all", "textures": {"all": "hbmsntm:block/rbmk_loader"}}
    return {"parent": "minecraft:block/cube_column", "textures": {"end": f"hbmsntm:block/rbmk/{n}_top", "side": f"hbmsntm:block/rbmk/{n}_side"}}


def expected_loot(n):
    return {"type": "minecraft:block", "pools": [{"bonus_rolls": 0.0, "conditions": [{"condition": "minecraft:survives_explosion"}], "entries": [{"type": "minecraft:item", "name": "hbmsntm:" + n}], "rolls": 1.0}],
            "random_sequence": "hbmsntm:blocks/" + n}


def v6_datagen(ck, inp, st):
    need_ov(inp)
    new = sorted(p for p in st.tree if p.startswith(GEN) and p not in inp.base_files)
    ck("V6.added-files", new == expected_generated() and len(new) == 40, "exactly 40 generated files were added: blockstate, block model, item model and loot table for each of the 7 new blocks (28) plus the six recipes and six advancements",
       (sorted(set(new) ^ set(expected_generated()))[:6], len(new)))
    changed = sorted(p for p in st.tree if p.startswith(GEN) and p in inp.base_files and st.tree[p] != inp.base_files[p])
    gone = sorted(p for p in inp.base_files if p.startswith(GEN) and p not in st.tree)
    ck("V6.changed-files", changed == sorted([STAMP, EN, PICK]) and not gone, "of the generated files that existed at the start only the migration stamp, en_us.json and the pickaxe tag changed, and none was deleted", (changed, gone))
    # ---- the original textures behind the models
    mb, rb = inp.ol["mb"], inp.ol["rbase"]
    want = {2117: 'RBMKControl(false).setBlockName("rbmk_control")', 2118: 'RBMKControl(true).setBlockName("rbmk_control_mod")', 2119: 'RBMKControlAuto().setBlockName("rbmk_control_auto")', 2123: 'RBMKBoiler().setBlockName("rbmk_boiler")',
            2129: 'RBMKCooler().setBlockName("rbmk_cooler")', 2130: 'RBMKHeater().setBlockName("rbmk_heater")', 2143: 'RBMKLoader(Material.iron).setBlockName("rbmk_loader")'}
    miss = at_lines(mb, want)
    for n, ln in zip(COLUMN6, (2117, 2118, 2119, 2123, 2130, 2129)):
        if f'setBlockTextureName(RefStrings.MODID + ":rbmk/{n}")' not in mb[ln - 1]:
            miss.append((ln, n, mb[ln - 1].strip()[:100]))
    if 'setBlockTextureName(RefStrings.MODID + ":rbmk_loader")' not in mb[2142]:
        miss.append((2143, "loader texture"))
    miss += at_lines(rb, {76: 'this.blockIcon = reg.registerIcon(this.getTextureName() + "_side");', 77: 'this.textureTop = reg.registerIcon(this.getTextureName() + "_top");', 92: "return side == 0 || side == 1 ? textureTop : blockIcon;"})
    ck("V6.original-textures", not miss, "ModBlocks.java:2117-2119, :2123, :2129-2130 name the textures rbmk/<block> and :2143 rbmk_loader; RBMKBase.java:75-92 draws <texture>_top on the up and down faces and <texture>_side elsewhere (cube_column end / side); the loader has one texture on every face (cube_all)", miss)
    # ---- the generated models
    bad = {}
    for n in NEW6:
        got = jload(st, G_BMODEL + n + ".json")
        if got != expected_block_model(n):
            bad[n] = got
    ck("V6.block-models", not bad, "the six columns have cube_column block models with end = rbmk/<name>_top and side = rbmk/<name>_side; rbmk_loader is a cube_all with block/rbmk_loader", dict(list(bad.items())[:2]))
    bad = {n: jload(st, G_STATE + n + ".json") for n in NEW6 if jload(st, G_STATE + n + ".json") != {"variants": {"": {"model": "hbmsntm:block/" + n}}}}
    ck("V6.blockstates", not bad, "each new block has a single-variant blockstate that points at its block model (no rotation: the original columns do not rotate)", dict(list(bad.items())[:2]))
    bad = {n: jload(st, G_IMODEL + n + ".json") for n in NEW6 if jload(st, G_IMODEL + n + ".json") != {"parent": "hbmsntm:block/" + n}}
    ck("V6.item-models", not bad, "each new block's item model inherits its block model (the original's four-segment inventory render is not ported)", dict(list(bad.items())[:2]))
    bad = {n: jload(st, G_LOOT + n + ".json") for n in NEW6 if jload(st, G_LOOT + n + ".json") != expected_loot(n)}
    ck("V6.loot-tables", not bad, "each new block drops itself (dropSelf: one roll, survives_explosion, random_sequence hbmsntm:blocks/<name>); the original columns drop themselves (no getDrops override)", dict(list(bad.items())[:2]))
    tex = [RES + f"textures/block/rbmk/{n}_{p}.png" for n in COLUMN6 for p in ("top", "side")] + [RES + "textures/block/rbmk_loader.png"]
    ck("V6.model-textures-exist", all(t in st.tree for t in tex) and len(tex) == 13, "every texture the new block models reference exists under assets/hbmsntm/textures/block (12 column faces and the loader)", [t for t in tex if t not in st.tree])
    # ---- pickaxe tag
    pk, pk0 = jload(st, PICK), json.loads(inp.start[PICK])
    vals, vals0 = pk["values"], pk0["values"]
    added = ["hbmsntm:" + n for n in NEW6]
    ck("V6.pickaxe-tag", pk.get("replace", False) == pk0.get("replace", False) and sorted(vals) == sorted(vals0 + added) and collections.Counter(vals) == collections.Counter(vals0) + collections.Counter(added) and [v for v in vals if v in vals0] == vals0
       and all(v in vals0 for v in START_PICKAXE_RBMK), "the pickaxe tag holds the start values in their order plus the 7 new blocks, once each (the start list already repeats 4 entries, which stay as they were; the original columns are iron material; NEO's rbmk columns are pickaxe blocks)", (sorted(set(vals) ^ set(vals0 + added))[:6]))
    # ---- providers: additive
    allowed_del = {BSP: ["* RenderRBMKLid. The debris blocks bake models/obj/rbmk/debris.obj with their own texture (original RenderPribris); their", "* items use a flat icon of that texture.",
                         "for(DeferredBlock<? extends Block> column : new DeferredBlock[] {NtmBlocks.RBMK_BLANK, NtmBlocks.RBMK_MODERATOR, NtmBlocks.RBMK_ABSORBER, NtmBlocks.RBMK_REFLECTOR}) {"],
                   LOOT: [], TAGP: []}
    want_ins = {BSP: ["for(DeferredBlock<? extends Block> column : new DeferredBlock[] {NtmBlocks.RBMK_BLANK, NtmBlocks.RBMK_MODERATOR, NtmBlocks.RBMK_ABSORBER, NtmBlocks.RBMK_REFLECTOR,",
                      "NtmBlocks.RBMK_CONTROL, NtmBlocks.RBMK_CONTROL_MOD, NtmBlocks.RBMK_CONTROL_AUTO,", "NtmBlocks.RBMK_BOILER, NtmBlocks.RBMK_HEATER, NtmBlocks.RBMK_COOLER}) {",
                      "this.simpleBlockWithItem(NtmBlocks.RBMK_LOADER.get(), this.models().cubeAll(name(NtmBlocks.RBMK_LOADER), modLoc(\"block/rbmk_loader\")));"],
                LOOT: [f"this.dropSelf(NtmBlocks.{n.upper()}.get());" for n in NEW6],
                TAGP: ["NtmBlocks.RBMK_CONTROL.get(),", "NtmBlocks.RBMK_CONTROL_MOD.get(),", "NtmBlocks.RBMK_CONTROL_AUTO.get(),", "NtmBlocks.RBMK_BOILER.get(),", "NtmBlocks.RBMK_HEATER.get(),", "NtmBlocks.RBMK_COOLER.get(),",
                       "NtmBlocks.RBMK_LOADER.get(),"]}
    badp = {}
    for path in (BSP, LOOT, TAGP):
        dele, ins = diff_summary(inp.start[path], lf(st.text(path)))
        code_ins = [x for x in ins if not x.startswith(("//", "*", "/*"))]
        code_del = [x for x in dele if not x.startswith(("//", "*", "/*"))]
        com_del = [x for x in dele if x.startswith(("//", "*", "/*"))]
        wd = allowed_del[path]
        if sorted(code_ins) != sorted(want_ins[path]) or sorted(dele) != sorted(wd) or len(code_del) != len([x for x in wd if not x.startswith(("//", "*", "/*"))]) or len(com_del) != len([x for x in wd if x.startswith(("//", "*", "/*"))]):
            badp[path.rsplit("/", 1)[1]] = (dele[:4], code_ins[:8])
    ck("V6.providers-additive", not badp, "NtmBlockStateProvider, NtmBlockLootTableProvider and NtmBlockTagProvider differ from their start copies only by the added registrations (the 6 columns in the registerRBMK column list, the cubeAll loader, 7 dropSelf lines, 7 pickaxe entries) "
       "and, in the state provider, the rewritten column-list line and two javadoc lines it extends; nothing else was removed", badp)
    ck("V6.provider-order", pickaxe_order_ok(st), "the pickaxe tag provider lists the control columns after rbmk_rod_mod and the steam columns after rbmk_moderator, which is the order of the generated tag")
    # ---- the migration stamp
    stamp = jload(st, STAMP)
    ins_keys = set(stamp["inputs"])
    stale = sorted(k for k in set(stamp["inputs"]) | set(inp.stamp_now) if stamp["inputs"].get(k) != inp.stamp_now.get(k))
    ck("V6.stamp-inputs-fresh", not stale and stamp["version"] == 1, "migration-stamp.json records, for every src/main/java and src/main/resources input and the build files, the hash the Gradle rule gives today (text files are hashed with LF line endings); a mismatch means runData was not rerun after the edit", stale[:6])
    gen_stale = sorted(k for k in set(stamp["generated"]) | set(inp.gen_now) if stamp["generated"].get(k) != inp.gen_now.get(k))
    ck("V6.stamp-generated-fresh", not gen_stale, "the stamp's generated hashes equal the files in src/generated/resources (the 40 added files, en_us.json and the pickaxe tag included)", gen_stale[:6])

    def fp(d):
        return hashlib.sha256("".join(f"{k}{chr(0)}{v}{chr(10)}" for k, v in d.items()).encode("utf-8")).hexdigest()
    ck("V6.stamp-fingerprints", fp(stamp["inputs"]) == stamp["inputFingerprint"] and fp(stamp["generated"]) == stamp["generatedFingerprint"],
       "the stamp's two fingerprints are the SHA-256 of its own input and generated entries (path, NUL, hash, newline, as gradle/migration-resources.gradle:144-147), so the file was not edited by hand",
       (fp(stamp["inputs"]) == stamp["inputFingerprint"], fp(stamp["generated"]) == stamp["generatedFingerprint"]))


def pickaxe_order_ok(st):
    text = lf(st.text(TAGP))
    order = ["NtmBlocks.RBMK_ROD_MOD.get(),", "NtmBlocks.RBMK_CONTROL.get(),", "NtmBlocks.RBMK_CONTROL_MOD.get(),", "NtmBlocks.RBMK_CONTROL_AUTO.get(),", "NtmBlocks.RBMK_BLANK.get(),", "NtmBlocks.RBMK_REFLECTOR.get(),",
             "NtmBlocks.RBMK_ABSORBER.get(),", "NtmBlocks.RBMK_MODERATOR.get(),", "NtmBlocks.RBMK_BOILER.get(),", "NtmBlocks.RBMK_HEATER.get(),", "NtmBlocks.RBMK_COOLER.get(),", "NtmBlocks.RBMK_LOADER.get(),"]
    pos = [text.find(o) for o in order]
    return all(p >= 0 for p in pos) and pos == sorted(pos)


# ---------------------------------------------------------------- V7 language

GUI_TIPS_FIRST, GUI_TIPS_LAST = 72, 89
GUI_TIP_LITERALS = ["Function: ", "Linear", "Quadratic", "Inverse Quadratic", "Select linear interpolation", "Select quadratic interpolation", "Select inverse quadratic interpolation",
                    "Level at max heat", "Should be smaller than level at min heat", "Level at min heat", "Should be larger than level at max heat", "Max heat", "Must be larger than min heat",
                    "Min heat", "Must be smaller than max heat", "Save parameters"]
LOCAL_FROM_TIPS = {"container.rbmkControlAuto.function": lambda t: t[0] + "%s", "container.rbmkControlAuto.linear": lambda t: t[1], "container.rbmkControlAuto.quadUp": lambda t: t[2],
                   "container.rbmkControlAuto.quadDown": lambda t: t[3], "container.rbmkControlAuto.selectLinear": lambda t: t[4], "container.rbmkControlAuto.selectQuadUp": lambda t: t[5],
                   "container.rbmkControlAuto.selectQuadDown": lambda t: t[6], "container.rbmkControlAuto.levelUpper": lambda t: t[7] + "$" + t[8],
                   "container.rbmkControlAuto.levelLower": lambda t: t[9] + "$" + t[10], "container.rbmkControlAuto.heatUpper": lambda t: t[11] + "$" + t[12],
                   "container.rbmkControlAuto.heatLower": lambda t: t[13] + "$" + t[14], "container.rbmkControlAuto.save": lambda t: t[15]}


def expected_lang():
    """[(NEO key, kind, source key, source en, source zh, target en, target zh)]: the 47 upstream keys (target = source) and the 12 local ones."""
    exp = [(nk, "upstream", ok, e, z, e, z) for nk, ok, e, z, _, _ in UP_ALL]
    exp += [(nk, "local", None, None, None, en, zh) for nk, (en, zh) in LOCAL_A.items()]
    return exp


def v7_lang(ck, inp, st):
    need_ov(inp)
    exp = expected_lang()
    keys = [e[0] for e in exp]
    ck("V7.expected-59", len(exp) == 59 and len(set(keys)) == 59 and sum(1 for e in exp if e[1] == "upstream") == 47 and sum(1 for e in exp if e[1] == "local") == 12 and sorted(keys) == NEW_KEYS,
       "59 keys are expected: 47 upstream (21 control and 26 steam: the original English and Chinese lines are the NEO text) and 12 local (container.rbmkControlAuto.*)")
    # the local keys' English is the original's hard-coded tooltip text, derived from GUIRBMKControlAuto.java:72-89
    gl = inp.ol["gaut"]
    lits = [x for ln in gl[GUI_TIPS_FIRST - 1:GUI_TIPS_LAST] for x in re.findall(r'"((?:[^"\\]|\\.)*)"', ln)]
    ck("V7.original-tooltips", lits == GUI_TIP_LITERALS and all(LOCAL_FROM_TIPS[k](lits) == LOCAL_A[k][0] for k in LOCAL_A) and set(LOCAL_FROM_TIPS) == set(LOCAL_A)
       and "func" in gl[GUI_TIPS_FIRST - 1] and "Save parameters" in gl[GUI_TIPS_LAST - 1],
       "GUIRBMKControlAuto.java:72-89 holds the 16 hard-coded tooltip strings in that order (function line, three function names, three selector tips, four two-line limit tips, save); the 12 local English values are those strings (`$` joins the two lines of a tip, `%s` ends the function line)",
       [x for x in lits if x not in GUI_TIP_LITERALS][:4])
    cites = []
    for path in (LP, ASCREEN):
        text = lf(st.text(path))
        for m in re.finditer(r"hard-coded[^()\n]*\(:(\d+)-(\d+)\)", text):
            a, b = int(m[1]), int(m[2])
            seg = "\n".join(gl[a - 1:b])
            if "Save parameters" not in seg or "Function: " not in seg:
                cites.append((path.rsplit("/", 1)[1], m[0][:100], f"original lines {a}-{b} start with: {gl[a - 1].strip()[:60] if a <= len(gl) else None}"))
    ck("V7.tooltip-cites", not cites, "every comment of NtmLanguageProvider / RBMKControlAutoScreen that cites a line range of GUIRBMKControlAuto for its hard-coded tooltips cites the lines that hold them (:72-89)", cites)
    lp = lf(st.text(LP))
    want_lines = {}
    for nk, kind, sk, sen, szh, ten, tzh in exp:
        holder = nk[len("block.hbmsntm."):].upper() if nk.startswith("block.hbmsntm.") and not nk.endswith(".desc") else None
        want_lines[nk] = f'this.add(NtmBlocks.{holder}, "{ten}");' if holder else f'this.add("{nk}", "{ten}");'
    lpl = [l.strip() for l in lp.split("\n")]
    ck("V7.provider", all(lpl.count(l) == 1 for l in want_lines.values()), "NtmLanguageProvider adds the 59 keys once each with the English text (the seven blocks through their registry holders)", [l for l in want_lines.values() if lpl.count(l) != 1][:4])
    ldel, lins = diff_summary(inp.start[LP], lp)
    code_ins = sorted(x for x in lins if x.startswith("this.add("))
    ck("V7.provider-insert-only", not ldel and code_ins == sorted(want_lines.values()) and len([x for x in lins if not x.startswith(("//", "*", "/*"))]) == 59,
       "the provider differs from its start copy only by these 59 added lines (plus comments); nothing was removed", (ldel[:3], len(code_ins)))
    en, en_dups = json_pairs(st.text(EN))
    en0, _ = json_pairs(inp.start[EN])
    zh_text = st.text(ZH)
    zh, zh_dups = json_pairs(zh_text)
    zh0, _ = json_pairs(inp.start[ZH])
    ck("V7.en-values", not en_dups and all(en.get(e[0]) == e[5] for e in exp), "generated en_us.json has the 59 keys with the provider's English and no duplicate key", [(e[0], en.get(e[0]), e[5]) for e in exp if en.get(e[0]) != e[5]][:3])
    changed_en = sorted(k for k in set(en) | set(en0) if en.get(k) != en0.get(k))
    ck("V7.en-only-these", changed_en == sorted(keys) and len(en) == len(en0) + 59 == NEW_EN_KEYS and len(en0) == START_EN_KEYS, f"en_us.json changed only in the 59 new keys and holds {NEW_EN_KEYS} keys ({START_EN_KEYS} at the start)", (changed_en[:5], len(en), len(en0)))
    ck("V7.zh-values", not zh_dups and all(zh.get(e[0]) == e[6] for e in exp), "zh_cn.json has the 59 keys: upstream values verbatim from zh_CN.lang, the 12 local ones as the handoff gives them (the limit tips say 控制棒抽出量)", [(e[0], zh.get(e[0]), e[6]) for e in exp if zh.get(e[0]) != e[6]][:3])
    changed_zh = sorted(k for k in set(zh) | set(zh0) if zh.get(k) != zh0.get(k))
    ck("V7.zh-only-these", changed_zh == sorted(keys) and len(zh) == len(zh0) + 59 == NEW_ZH_KEYS and len(zh0) == START_ZH_KEYS, f"zh_cn.json changed in nothing but the 59 new keys and holds {NEW_ZH_KEYS} keys ({START_ZH_KEYS} at the start)", (changed_zh[:5], len(zh), len(zh0)))
    ordered, ordered0 = list(zh.keys()), list(zh0.keys())
    ck("V7.zh-order", (ordered == sorted(ordered)) if ordered0 == sorted(ordered0) else [k for k in ordered if k in zh0] == ordered0, "zh_cn.json keeps its key order (sorted when the start copy is sorted; else the start order with the new keys inserted)")
    ph = lambda s: (sorted(re.findall(r"%(?:\d+\$)?[sd]", s)), s.count("$"))  # noqa: E731
    ck("V7.placeholders", all(ph(en.get(e[0], "")) == ph(zh.get(e[0], "")) for e in exp), "every new key keeps the same placeholders and `$` line breaks in English and Chinese", [e[0] for e in exp if ph(en.get(e[0], "")) != ph(zh.get(e[0], ""))][:4])
    ck("V7.upstream-verbatim", all(e[1] != "upstream" or (zh.get(e[0]) == inp.o_zh[e[2]][0][0] and en.get(e[0]) == inp.o_en[e[2]][0][0]) for e in exp), "the 47 upstream values equal en_US.lang / zh_CN.lang byte for byte")
    map_text = st.text(MAP)
    ck("V7.crlf", zh_text.count("\r\n") == zh_text.count("\n") > 0 and inp.start[ZH].count("\r\n") == inp.start[ZH].count("\n") and zh_text.count("\r\n") - inp.start[ZH].count("\r\n") == 59
       and "\r\n" not in st.text(EN) and format_ok(zh_text, zh) and map_text.count("\r\n") == map_text.count("\n") > 0 and format_ok(map_text, json.loads(map_text))
       and map_text.count("\r\n") - inp.start[MAP].count("\r\n") == sum(8 if e[1] == "upstream" else 6 for e in exp),
       "zh_cn.json grew by exactly 59 CRLF lines with no lone LF, zh_cn-map.json keeps CRLF and the standard layout (8 lines per upstream and 6 per local entry added), en_us.json stays LF",
       (zh_text.count("\r\n"), zh_text.count("\n"), inp.start[ZH].count("\r\n"), map_text.count("\r\n"), map_text.count("\n")))
    mp = json.loads(map_text)
    mp0 = json.loads(inp.start[MAP])
    entries, entries0 = mp["entries"], mp0["entries"]
    bad = {}
    for nk, kind, sk, sen, szh, ten, tzh in exp:
        e = entries.get(nk)
        if e is None or e.get("kind") != kind or e.get("target_en") != ten or e.get("target_zh") != tzh:
            bad[nk] = e
        elif kind == "upstream" and e != {"kind": "upstream", "source_en": sen, "source_key": sk, "source_zh": szh, "target_en": ten, "target_zh": tzh}:
            bad[nk] = e
        elif kind == "local" and (not str(e.get("reason", "")).strip() or set(e) != {"kind", "reason", "target_en", "target_zh"}):
            bad[nk] = e
    ck("V7.map-entries", not bad, "the mapping has one entry per key: upstream entries carry source_key / source_en / source_zh from the original and the NEO text; local entries carry a reason", dict(list(bad.items())[:3]))
    badr = [k for k in LOCAL_A if "GUIRBMKControlAuto.java:72-89" not in str(entries.get(k, {}).get("reason", ""))]
    ck("V7.map-local-reasons", not badr and len(LOCAL_A) == 12, "the 12 local entries' reasons cite GUIRBMKControlAuto.java:72-89, where the original's hard-coded tooltips are", badr)
    ck("V7.map-dodd-level", entries.get("tile.rbmk.dodd.level", {}).get("target_zh") == "控制棒深度" and zh.get("tile.rbmk.dodd.level") == "控制棒深度" and inp.o_zh["tile.rbmk.dodd.level"][0][0] == "控制棒深度",
       "the upstream key tile.rbmk.dodd.level keeps the upstream Chinese 控制棒深度 (only the two local limit tips use 控制棒抽出量)")
    changed_map = sorted(k for k in set(entries) | set(entries0) if entries.get(k) != entries0.get(k))
    kinds, kinds0 = collections.Counter(e["kind"] for e in entries.values()), collections.Counter(e["kind"] for e in entries0.values())
    ck("V7.map-only-these", changed_map == sorted(keys) and mp["source_commit"] == mp0["source_commit"] and mp["schema_version"] == mp0["schema_version"] and len(entries) == len(entries0) + 59 == NEW_MAP_KEYS and len(entries0) == START_MAP_KEYS
       and kinds["upstream"] - kinds0["upstream"] == 47 and kinds["local"] - kinds0["local"] == 12 and kinds["deferred"] == kinds0["deferred"] and (kinds["upstream"], kinds["local"], kinds["deferred"]) == (1870, 696, 107),
       f"the mapping changed only in the 59 new entries and holds {NEW_MAP_KEYS} entries: upstream 1,870, local 696, deferred 107; source_commit and schema_version unchanged", (changed_map[:5], dict(kinds)))
    ordered = list(entries.keys())
    ck("V7.map-sorted", ordered == sorted(ordered) and list(entries0.keys()) == sorted(entries0.keys()), "the mapping keeps its sorted key order")
    ck("V7.map-matches-files", all(entries[k].get("target_en") == en.get(k) and entries[k].get("target_zh") == zh.get(k) for k in keys if k in entries), "for the 59 keys the mapping's target English / Chinese equal the generated en_us.json and zh_cn.json values")
    ck("V7.start-copies-consistent", len(en0) == START_EN_KEYS and len(zh0) == START_ZH_KEYS and len(entries0) == START_MAP_KEYS and not [k for k in keys if k in en0 or k in zh0 or k in entries0],
       f"none of the 59 keys existed in the start copies of en_us.json, zh_cn.json and the mapping ({START_EN_KEYS} / {START_ZH_KEYS} / {START_MAP_KEYS} keys)")


# ---------------------------------------------------------------- V8 resources

def v8_resources(ck, inp, st):
    need_ov(inp)
    own = json.loads(st.text(OWN))
    assets = own["assets"]
    targets = [RES + n for _, n in IMPORTS]
    ck("V8.record", len(assets) == 46 and own.get("batch") == "Goal24D" and own.get("source_commit") == ORIGINAL_HEAD and own.get("kind") == "import" and sorted(a["target_path"] for a in assets) == sorted(targets)
       and str(own.get("note", "")).strip() != "" and format_ok(st.text(OWN), own),
       "migration/goal24d-resource-ownership.json (batch Goal24D, kind import, original at aee05a40f) lists the 46 imported files, in the standard JSON layout", (len(assets), own.get("batch"), own.get("source_commit")))
    bad = [t for t in targets if t not in st.files or t not in inp.o_res or st.files[t] != inp.o_res[t] or sha(st.files[t]) != sha(inp.o_res[t])]
    ck("V8.bytes-equal-original", not bad, "each of the 46 NEO files is byte-equal (SHA-256) to the original working-tree file (the OBJ file is the CRLF worktree bytes)", bad[:5])
    by_target = {a["target_path"]: a for a in assets}
    bad_rec, bad_png, bad_commit, bad_text = [], [], [], []
    for orig, neo in IMPORTS:
        t = RES + neo
        a, data = by_target.get(t), st.files.get(t)
        if a is None or data is None:
            bad_rec.append(t)
            continue
        if not (sha(data) == a.get("target_sha256") == a.get("source_sha256") and a.get("bytes") == len(data) and a.get("source_path") == O_RES + orig and t == t.lower()):
            bad_rec.append(t)
        if orig.endswith(".png") and png_size(data) != a.get("png_size"):
            bad_png.append(t)
        if not orig.endswith(".png") and "png_size" in a:
            bad_png.append(t)
        if inp.last_commit.get(t, "") and inp.last_commit.get(t) != a.get("source_last_change_commit"):
            bad_commit.append(t)
        if not str(a.get("description", "")).strip() or "retained byte-for-byte" not in str(a.get("ownership", "")):
            bad_text.append(t)
    ck("V8.record-matches", not bad_rec and not bad_png and not bad_text, "each record entry's source and target path, SHA-256 (source = target = file), byte count and PNG size (none for .obj) equal the file; target paths are lowercase; description and ownership text are present", (bad_rec[:3], bad_png[:3], bad_text[:3]))
    ck("V8.last-commit", "error" not in inp.last_commit and not bad_commit and len(inp.last_commit) == 46, "source_last_change_commit equals `git log -1 --format=%H -- <path>` in the original for all 46", (bad_commit[:3], inp.last_commit.get("error")))
    bad = []
    for orig, neo in IMPORTS:
        if not orig.endswith(".obj"):
            continue
        t, a, data, blob = RES + neo, by_target.get(RES + neo, {}), st.files.get(RES + neo, b""), inp.o_blob.get(RES + neo)
        if blob is None or not (a.get("worktree_crlf_lines") == data.count(b"\r\n") > 0 and a.get("blob_sha256") == sha(blob) and a.get("blob_bytes") == len(blob) and a.get("normalized_sha256") == sha(data.replace(b"\r\n", b"\n"))
                                and a.get("normalized_equal_to_blob") is True and a.get("normalized_sha256") == a.get("blob_sha256") and data != blob):
            bad.append(t)
    ck("V8.obj-fields", not bad and len([1 for o, _ in IMPORTS if o.endswith(".obj")]) == 1, "the OBJ record carries the worktree CRLF line count, the Git blob hash and size (`git show HEAD:<path>` in the original) and the LF-normalised hash that equals the blob (the worktree is CRLF, the blob LF)", bad)
    ni = own.get("not_imported", [])
    ni_paths = [x["source_path"] for x in ni]
    want_ni = [O_RES + n for n in NOT_IMPORTED_A + [PARTICLE_ORIG]]
    neo_absent = [n for n in NOT_IMPORTED_A[1:] if (RES + "textures/block/rbmk/" + n.rsplit("/", 1)[1]) in st.tree]
    ck("V8.not-imported", len(ni) == 13 and sorted(ni_paths) == sorted(want_ni) and all(x.get("present_in_original") is True and str(x.get("reason", "")).strip() for x in ni) and all(inp.o_not_imported.values()) and inp.o_particle is not None and not neo_absent,
       "not_imported lists the 13 files the handoffs name (rbmk_control.png, rbmk_control_base.png, the ten ReaSim control textures, the steam particle) with reasons; they exist in the original and the control_base and ReaSim textures are absent from NEO", (sorted(set(ni_paths) ^ set(want_ni)), neo_absent))
    ctl = RES + "textures/block/rbmk/rbmk_control.png"
    own24a = json.loads((ROOT / "migration/goal24a-resource-ownership.json").read_text(encoding="utf-8"))
    rec24a = [a for a in own24a["assets"] if a["target_path"] == ctl]
    orig_ctl = (ORIGINAL / (O_RES + "textures/blocks/rbmk/rbmk_control.png")).read_bytes()
    ck("V8.control-png-reuse", len(rec24a) == 1 and rec24a[0]["target_sha256"] == sha(orig_ctl) == st.tree.get(ctl) and hashed_equal(inp, st, ctl) and "Goal24A" in next((x["reason"] for x in ni if x["source_path"].endswith("/rbmk_control.png")), "") and ctl in st.tree,
       "rbmk_control.png (the plain rod head) is the Goal24A file: its record in goal24a-resource-ownership.json, the file in NEO, the start copy and the original have one SHA-256, and Goal24D's not_imported entry says it is reused")
    partsha = sha(inp.o_particle) if inp.o_particle else None
    ck("V8.particle-reuse", st.has(PARTICLE_NEO) and sha(st.files[PARTICLE_NEO]) == partsha and hashed_equal(inp, st, PARTICLE_NEO) and partsha in next((x["reason"] for x in ni if x["source_path"].endswith("rbmk_jet_steam.png")), ""),
       "the steam vent particle texture in NEO (particle_no_sheet/rbmk_jet_steam.png) is byte-equal to the original, is the unchanged start file, and its not_imported reason quotes that SHA-256")
    base_res = {p for p in inp.base_files if p.startswith(RES)}
    new_res = {p for p in st.tree if p.startswith(RES) and p not in base_res}
    changed_res = [p for p in base_res if st.tree.get(p) != inp.base_files[p]]
    ck("V8.no-unlisted", new_res == set(targets) and changed_res == [ZH], "the new files under assets/hbmsntm are exactly the 46 listed imports and the only existing resource that changed is zh_cn.json", (sorted(new_res ^ set(targets))[:5], changed_res[:5]))
    guis = [RES + "textures/gui/reactors/" + n for n in ("gui_rbmk_control.png", "gui_rbmk_control_auto.png", "gui_rbmk_boiler.png", "gui_rbmk_heater.png")]
    ck("V8.gui-textures", all(g in st.files and png_size(st.files[g]) == [256, 256] for g in guis), "the four GUI textures are 256 x 256 PNGs, the default blit atlas size the screens' rectangles assume", [(g.rsplit("/", 1)[1], png_size(st.files[g]) if g in st.files else None) for g in guis])
    miss = [t for t in [RES + f"textures/block/rbmk/{n}_{p}.png" for n in ("rbmk_control", "rbmk_control_mod", "rbmk_control_auto") for p in ("side", "top", "pipe_side", "pipe_top")] if t not in st.tree]
    ck("V8.texture-set", not miss and len(IMPORTS_A) == 21 and len(IMPORTS_B) == 25, "the 12 control column textures (side, top, pipe_side, pipe_top for three blocks) exist; package A holds 21 imports and package B 25", miss)


# ---------------------------------------------------------------- V9 scope

ALLOWED_MIGRATION = ("migration/goal24d-", "migration/GOAL24")
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md", "migration/RESOURCE-OWNERSHIP.md"}
UNTOUCHED = [SLOT, DIALS, RLID, ANVIL, RODBLK, J + "blocks/machine/rbmk/RBMKPassiveBlock.java", J + "blocks/machine/rbmk/RBMKDebrisBlock.java", J + "blocks/machine/rbmk/RBMKDebrisBurningBlock.java",
             J + "blocks/machine/rbmk/RBMKDebrisRadiatingBlock.java", BE + "RBMKType.java", BE + "RBMKColumnType.java", BE + "RBMKRodBlockEntity.java", BE + "RBMKBlankBlockEntity.java", BE + "RBMKModeratorBlockEntity.java",
             BE + "RBMKReflectorBlockEntity.java", BE + "RBMKAbsorberBlockEntity.java", BE + "IRBMKFluxReceiver.java", BE + "IRBMKLoadable.java", J + "particle/NtmParticleTypes.java", J + "render/model/loader/NtmGeometry.java",
             J + "config/NtmConfig.java", J + "gametest/RBMKCoreGameTests.java", J + "gametest/RBMKFuelGameTests.java", J + "gametest/RBMKReactorGameTests.java", J + "gametest/HazardGameTests.java"]
BSP_LOOP = "for(DeferredBlock<? extends Block> column : new DeferredBlock[] {NtmBlocks.RBMK_BLANK, NtmBlocks.RBMK_MODERATOR, NtmBlocks.RBMK_ABSORBER, NtmBlocks.RBMK_REFLECTOR}) {"
ALLOWED_DELETIONS = {
    RNH: ["* (Goal 26), the outgasser (Goal 25) and the control rods (Goal24D); their branches are left as comments where they sit.", "}", "// Original :332-340: CONTROL_ROD scales the flux by its insertion or stops the stream (TileEntityRBMKControl, Goal24D);",
          "// no column reports CONTROL_ROD yet.", "else if(type == RBMKType.REFLECTOR) {", "// Original :377-397: a CONTROL_ROD last node passes the scaled flux on to the block behind it (Goal24D, GitHub issue #1933)."],
    BASEBLK: ["return this.getLid(level, pos) != LidType.NONE ? LID_SHAPE : Shapes.block();"],
    BASEBE: ["// Original :500-539: the overpressure branch blows up the collected pipe networks. Pipes are collected only from the", "// steam channels of Goal24D, so in 24A this never has anything to do.", "if(RBMKDials.getOverpressure())",
             "handleOverpressure();", "/** Overpressure hook of the meltdown; the steam channels (Goal24D) fill it in. */", "protected void handleOverpressure() { }"],
    BSP: ["* RenderRBMKLid. The debris blocks bake models/obj/rbmk/debris.obj with their own texture (original RenderPribris); their", "* items use a flat icon of that texture.", BSP_LOOP],
    RP: ["// rbmk_lid_glass rows (:753-754, NEO has no glass_lead or glass_boron), the rbmk_moderator row (:756, NEO has no graphite", "// block) and rbmk_control (:760, Goal24D)."]}


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v9_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    imports = [RES + n for _, n in IMPORTS]
    expected = set(NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, OWN, PICK, GT] + imports + gen_new)
    extra = [p for p in changed if p not in expected and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V9.no-extra-paths", not extra, "every changed src/ and migration/ path since the start belongs to the batch: the new and edited production files, the language files, the 46 imports, the generated outputs, the GameTest file and the migration records", extra[:10])
    ck("V9.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != GT]
    ck("V9.expected-all-changed", not never, "every expected production, resource and generated path really differs from the start (the GameTest file is checked in V10)", never[:5])
    ck("V9.counts", len(NEW_CLASSES) == 24 and len(EDITED) == 15 and len(imports) == 46 and len(gen_new) == 40 and len(set(NEW_CLASSES + EDITED)) == 39,
       "24 new production classes, 15 edited production files, 46 imported resources, 40 new generated files", (len(NEW_CLASSES), len(EDITED), len(imports), len(gen_new)))
    ck("V9.new-classes-new", all(p not in inp.base_files for p in NEW_CLASSES + [OWN]) and all(p in inp.base_files for p in EDITED), "the 24 new classes and the ownership record did not exist at the start and the 15 edited files did")
    ck("V9.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED),
       "the Goal24A / 24B / 24C files outside the handoffs (RBMKSlottedBaseBlockEntity, RBMKDials, the rod, passive and debris columns and their block entities, RBMKType, RBMKColumnType, RenderRBMKLid, NtmParticleTypes, NtmGeometry, NtmConfig, AnvilRecipes, "
       "the older RBMK GameTests) are byte-equal to the start", [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    bad, eol = {}, []
    for p in EDITED:
        live = st.text(p)
        dele, _ = diff_summary(inp.start[p], live)
        if sorted(dele) != sorted(ALLOWED_DELETIONS.get(p, [])):
            bad[p.rsplit("/", 1)[1]] = [x[:100] for x in dele if x not in ALLOWED_DELETIONS.get(p, [])][:3] or ["an allowed deletion is missing"]
        if ("\r\n" in inp.start[p]) != ("\r\n" in live) or live.count("\r\n") not in (0, live.count("\n")):
            eol.append(p)
    ck("V9.edited-additive", not bad, "the 15 edited production files differ from their start copies by additions plus these removals only: the replaced overpressure hook and its two comment lines in RBMKBaseBlockEntity, the restructured REFLECTOR branch and its comments in RBMKNeutronHandler, "
       "the collision-shape line of RBMKBaseBlock, the column-list line and two javadoc lines of NtmBlockStateProvider, two comment lines of NtmRecipeProvider", bad)
    ck("V9.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF, no mixed lines)", eol)
    rest = sorted(p for p in changed if p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT)
    ck("V9.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V9.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V10 / V11 / V12

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")
GT_AREAS = ("control", "neutron", "auto", "boiler", "heater", "cooler", "loader", "ports", "nbt", "recipes")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v10_gametest(ck, inp, st):
    ck("V10.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests (counted by @GameTest( in every other class of the gametest package)", other_gametests())
    ck("V10.present", st.has(GT), "RBMKControlSteamGameTests.java exists (written by the GameTest verifier)")
    if not st.has(GT):
        return dict(rbmk_control_steam_tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V10.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "RBMKControlSteamGameTests has @GameTest methods, each public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = []
    for args in tests.values():
        m = re.search(r"batch\s*=\s*([^,)]+)", args)
        batches.append(m[1].strip().strip('"') if m else None)
    ck("V10.own-batch", len(tests) >= 1 and None not in batches and len(set(batches)) == len(batches), "every test has its own batch (the neutron StreamWorld, the chunk radiation and the fluid networks are per level and shared by simultaneous tests)", batches)
    ck("V10.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "RBMKControlSteamGameTests is a @GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false), like the other RBMK GameTests")
    ck("V10.marker", f'"{GT_MARK} {{}} passed"' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = []
    for name in tests:
        try:
            if f'"{name}"' not in body(live, f"void {name}(GameTestHelper helper)"):
                miss.append(name)
        except ValueError:
            miss.append(name)
    ck("V10.report-name", not miss, "every test method passes its own name to the passed helper", miss)
    ck("V10.areas", all(any(a in n for n in tests) for a in GT_AREAS), "the test names cover the batch's areas: " + ", ".join(GT_AREAS), [a for a in GT_AREAS if not any(a in n for n in tests)])
    ck("V10.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKControlSteamGameTests references no client class")
    return dict(rbmk_control_steam_tests=sorted(tests))


def v11_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    # the expected total is counted from the @GameTest annotations of the source files (the other classes plus this one), not taken from a literal
    total = other_gametests() + gametest_total([live])
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V11.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({other_gametests()} in the other classes + {len(tests)} RBMKControlSteamGameTests, counted from the @GameTest annotations)", (match and match[0], total))
    ck("V11.annotation-total", other_gametests() == START_GAMETESTS and gametest_total([live]) == len(tests), f"the other classes hold the {START_GAMETESTS} start tests and every @GameTest( of RBMKControlSteamGameTests is a method of the form checked in V10 ({len(tests)})")
    ck("V11.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V11.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V11.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()))


def inner_expected(text):
    code = blank_comments(lf(text))
    anon = len(re.findall(r"new\s+[A-Z][\w.<>]*\s*\([^();{}]*\)\s*\{", code))
    nested = len(re.findall(r"^[ \t]{4,}(?:(?:public|private|protected|static|final|abstract)\s+)*(?:class|record|enum|interface)\s+\w+", code, re.M))
    return anon + nested


def v12_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    live_en, _ = json_pairs(st.text(EN))
    live_zh, _ = json_pairs(st.text(ZH))
    keys = [e[0] for e in expected_lang()]
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files and not p.endswith("/.migration-stamp.json")]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names and not c.endswith("/package-info")]
        short = {}
        for c, p in classes.items():
            have = len([n for n in names if n.startswith(c + "$") and n.endswith(".class")])
            if have < inner_expected(st.text(p)):
                short[c] = (have, inner_expected(st.text(p)))
        ck("V12.classes", not missing, "the JAR has the 24 new production classes and RBMKControlSteamGameTests", missing)
        ck("V12.inner-classes", not short, "the JAR has at least as many inner/anonymous classes as the sources declare", short)
        res = [RES + n for _, n in IMPORTS]
        bad = [p for p in res if p[len("src/main/resources/"):] not in names or jar.read(p[len("src/main/resources/"):]) != st.files.get(p)]
        ck("V12.resources", not bad and len(res) == 46, "the 46 imported textures, OBJ model and GUI textures in the JAR are byte-equal to the source files", bad[:5])
        gbad = [p for p in gen_new + [EN, PICK] if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V12.generated", not gbad and len(gen_new) == 40, "the 40 new generated blockstates, models, loot tables, recipes and advancements, en_us.json and the pickaxe tag in the JAR are byte-equal to the live files", gbad[:5])
        ck("V12.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V12.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in keys if data.get(k) != source.get(k) or k not in data}
            ck(f"V12.{Path(entry).name}", not bad, f"{entry} in the JAR carries the 59 new keys with the values of the source file", dict(list(bad.items())[:3]))
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- V4 (cont.) collision of the columns with their own lid

def v4_collision(ck, inp, st):
    need_ov(inp)
    o = inp.ol["rbase"]
    m = at_lines(o, {68: "public boolean hasOwnLid() {", 78: "if(hasOwnLid()) return;", 128: "public AxisAlignedBB getCollisionBoundingBoxFromPool(World world, int x, int y, int z) {", 130: "float height = 0.0F;", 141: "if(rbmk.hasLid()) {", 142: "height += 0.25F;",
                     147: "y + this.maxY + height"})
    code = cs(st, BASEBLK)
    shape = re.search(r"LID_SHAPE=Shapes\.box\(0,0,0,1,([\d.]+),1\);", code)
    ck("V4.own-lid-collision", not m and bool(shape) and abs(float(shape[1]) - (1 + 0.25)) < 1e-9
       and "returnthis.hasOwnLid()||this.getLid(level,pos)!=LidType.NONE?LID_SHAPE:Shapes.block();" in code and "protectedbooleanhasOwnLid(){returnfalse;}" in code,
       "RBMKBaseBlock.getCollisionShape raises the box by 0.25 (LID_SHAPE 1.25 = 1 + the original's `height += 0.25F`, RBMKBase.java:128-147) when the column has a lid or carries its own (hasOwnLid, RBMKBase.java:68; the control columns have no lid state, so the shape asks it); the base answer is false", m)


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None, v1=True):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    if v1:
        guarded(ck, "V1", v1_original, inp, st)
    for fn in (v2_control, v2_neutron):
        guarded(ck, "V2", fn, inp, st)
    for fn in (v3_steam, v3_loader_base):
        guarded(ck, "V3", fn, inp, st)
    for fn in (v4_registrations, v4_blocks, v4_screens, v4_render, v4_particle, v4_collision):
        guarded(ck, "V4", fn, inp, st)
    guarded(ck, "V5", v5_recipes, inp, st)
    guarded(ck, "V6", v6_datagen, inp, st)
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


def gen_edit(path, edit):
    """Edit a generated JSON file in the datagen layout (2-space JSON, LF, no trailing newline)."""
    def apply(st):
        data = json.loads(st.text(path))
        edit(data)
        st.set_text(path, json.dumps(data, indent=2, ensure_ascii=False))
    return apply


def own_edit(edit):
    return lambda st: st.set_text(OWN, json_edit(st.text(OWN), edit))


def OE(name, fn):
    """Edit the original's source text in memory (never on disk): V1 / V2 / V3 must notice a moved or changed line."""
    def apply(st):
        st.orig_edits[name] = fn
    return apply


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    return [
        # ---- V1 / V2 / V3: the original's text (in memory); a moved or changed line must fail loudly
        ("orig_control_speed", "V1.|V2.", OE("ctl", lambda x: rep1(x, "speed = 0.00277D;", "speed = 0.0028D;"))),
        ("orig_boiler_table", "V1.|V3.", OE("boi", lambda x: rep1(x, "if(type == Fluids.SUPERHOTSTEAM) return 450D;", "if(type == Fluids.SUPERHOTSTEAM) return 400D;"))),
        ("orig_cooler_timer", "V1.|V3.", OE("coo", lambda x: rep1(x, "timer = 60;", "timer = 50;"))),
        ("orig_overpressure_fifth", "V1.|V3.", OE("base", lambda x: rep1(x, "pipeBlocks.size() / 5, 100", "pipeBlocks.size() / 4, 100"))),
        ("orig_recipe_cooler_row", "V1.|V5.", OE("cm", lambda x: rep1(x, "'I', ModItems.plate_polymer, 'G', ModBlocks.steel_grate });", "'I', ModItems.plate_polymer, 'G', ModBlocks.steel_plate });"))),
        ("orig_anvil_row_input", "V1.", OE("ar", lambda x: rep1(x, "new ComparableStack(ModBlocks.rbmk_boiler)", "new ComparableStack(ModBlocks.rbmk_blank)"))),
        ("orig_loader_connect", "V1.|V3.", OE("rload", lambda x: rep1(x, "if(dir == ForgeDirection.UP) return type.hasTrait(FT_Heatable.class);", "if(dir == ForgeDirection.DOWN) return type.hasTrait(FT_Heatable.class);"))),
        ("orig_particle_age", "V1.", OE("part", lambda x: rep1(x, "this.particleMaxAge = 10;", "this.particleMaxAge = 12;"))),
        ("orig_tooltip_text", "V7.", OE("gaut", lambda x: rep1(x, '"Save parameters"', '"Save parameter"'))),
        # ---- V2 control rods
        ("ctl_speed", "V2.", t(CTL, "speed = 0.00277D;", "speed = 0.0028D;")),
        ("ctl_up_clamp_dropped", "V2.", t(CTL, "if(level > targetLevel) level = targetLevel;", "")),
        ("ctl_down_ignores_dial", "V2.", t(CTL, "level -= speed * RBMKDials.getControlSpeed();", "level -= speed;")),
        ("ctl_lid_removable", "V2.", t(CTL, "public boolean isLidRemovable() {\n        return false;", "public boolean isLidRemovable() {\n        return true;")),
        ("ctl_tracking_range", "V2.", t(CTL, "return 100;", "return 64;")),
        ("ctl_nbt_key", "V2.", t(CTL, 'tag.putDouble("targetLevel", this.targetLevel);', 'tag.putDouble("target", this.targetLevel);')),
        ("man_surge_exponent", "V2.", t(MAN, "Math.pow((1D - this.level), 15)", "Math.pow((1D - this.level), 14)")),
        ("man_permission_radius", "V2.", t(MAN, ".length() < 20;", ".length() < 25;")),
        ("man_starting_level_dropped", "V2.", t(MAN, "this.startingLevel = this.level;", "")),
        ("man_color_toggle_dropped", "V2.", t(MAN, "this.color = null;\n            } else {\n                this.color = newCol;", "this.color = newCol;\n            } else {\n                this.color = newCol;")),
        ("auto_quad_up_exponent", "V2.", t(AUT, "Math.pow((this.heat - this.heatLower) / (this.heatUpper - this.heatLower), 2)", "Math.pow((this.heat - this.heatLower) / (this.heatUpper - this.heatLower), 3)")),
        ("auto_target_scale", "V2.", t(AUT, "this.targetLevel = fauxLevel * 0.01D;", "this.targetLevel = fauxLevel * 0.02D;")),
        ("auto_clamp_dropped", "V2.", t(AUT, "this.targetLevel = Mth.clamp(this.targetLevel, 0D, 1D);", "")),
        ("auto_lower_bound", "V2.", t(AUT, "double lowerBound = Math.min(this.heatLower, this.heatUpper);", "double lowerBound = this.heatLower;")),
        ("rnh_control_mult_dropped", "V2.", t(RNH, "this.fluxQuantity *= rod.getMult();\n                        continue;", "continue;")),
        ("rnh_control_level_gate", "V2.", t(RNH, "if(rod.level > 0.0D) {", "if(rod.level >= 0.0D) {")),
        ("rnh_tail_checks_last_pos", "V2.", t(RNH, "if(NeutronNodeWorld.getNode(level, pos) == null) {", "if(NeutronNodeWorld.getNode(level, lastPos) == null) {")),
        ("rnh_tail_mult_gate", "V2.", t(RNH, "if(rod.getMult() > 0.0D) {", "if(rod.getMult() >= 0.0D) {")),
        # ---- V3 steam channel, heater, cooler, loader, ports, overpressure
        ("boi_table_hot", "V3.", t(BOI, "if(type == Fluids.HOTSTEAM) return 300D;", "if(type == Fluids.HOTSTEAM) return 350D;")),
        ("boi_factor_superhot", "V3.", t(BOI, "if(type == Fluids.SUPERHOTSTEAM) return 100D;", "if(type == Fluids.SUPERHOTSTEAM) return 90D;")),
        ("boi_vent_delay", "V3.", t(BOI, "this.ventDelay = 20 + world.random.nextInt(10);", "this.ventDelay = 25 + world.random.nextInt(10);")),
        ("boi_vent_range", "V3.", t(BOI, ", 100, new AuxParticle(", ", 64, new AuxParticle(")),
        ("boi_vent_pitch", "V3.", t(BOI, "SoundSource.BLOCKS, 2F, 1F + world.random.nextFloat() * 0.25F", "SoundSource.BLOCKS, 2F, 1F")),
        ("boi_ultrahot_hundred", "V3.", t(BOI, "steamProduced = (int)Math.floor((heatProvided / HEAT_PER_MB_WATER) * 100D / steamFactor);", "steamProduced = (int)Math.floor((heatProvided / HEAT_PER_MB_WATER) / steamFactor);")),
        ("boi_compressor_fill_captured_first", "V3.", t(BOI, "if(type == Fluids.STEAM) {          steam.setTankType(Fluids.HOTSTEAM);         steam.setFill(steam.getFill() / 10); }",
                                                         "if(type == Fluids.STEAM) { int kept = steam.getFill(); steam.setTankType(Fluids.HOTSTEAM); steam.setFill(kept / 10); }")),
        ("boi_compressor_fill_before_type", "V3.", t(BOI, "steam.setTankType(Fluids.SUPERHOTSTEAM);    steam.setFill(steam.getFill() / 10);", "steam.setFill(steam.getFill() / 10);    steam.setTankType(Fluids.SUPERHOTSTEAM);")),
        ("boi_compressor_guard", "V3.", t(BOI, "if(this.heat > 50 && this.feed.getFill() > 0) return;", "if(this.heat > 60 && this.feed.getFill() > 0) return;")),
        ("base_collect_after_melt", "V3.", T(BASEBE, lambda x: swap_lines(x, "rbmk.collectOverpressurePipes(pipes);", "rbmk.onMelt(minDist + 1);"))),
        ("hea_tu_per_degree", "V3.", t(HEA, "double TU_PER_DEGREE = 2_000D * eff;", "double TU_PER_DEGREE = 1_000D * eff;")),
        ("hea_temperature_floor", "V3.", t(HEA, "if(tempRange > 0 && eff > 0) {", "if(tempRange >= 0 && eff > 0) {")),
        ("hea_heat_efficiency_dropped", "V3.", t(HEA, "this.heat -= (step.heatReq * ops / TU_PER_DEGREE) * trait.getEfficiency(HeatingType.HEATEXCHANGER);", "this.heat -= (step.heatReq * ops / TU_PER_DEGREE);")),
        ("coo_timer", "V3.", t(COO, "timer = 60;", "timer = 50;")),
        ("coo_heat_taken", "V3.", t(COO, "neighbor.heat -= 200;", "neighbor.heat -= 100;")),
        ("coo_heat_floor", "V3.", t(COO, "if(neighbor.heat < 20) neighbor.heat = 20;", "if(neighbor.heat < 0) neighbor.heat = 0;")),
        ("coo_scan_width", "V3.", t(COO, "int x = this.worldPosition.getX() - 2 + i / 5;", "int x = this.worldPosition.getX() - 1 + i / 5;")),
        ("coo_fluid_threshold", "V3.", t(COO, "if(t0.getFill() >= 50 &&", "if(t0.getFill() >= 100 &&")),
        ("coo_fluid_moved", "V3.", t(COO, "t1.setFill(t1.getFill() + 50);", "t1.setFill(t1.getFill() + 40);")),
        ("base_overpressure_fifth", "V3.", t(BASEBE, "Math.min(pipeBlocks.size() / 5, 100)", "Math.min(pipeBlocks.size() / 4, 100)")),
        ("base_overpressure_cap", "V3.", t(BASEBE, "Math.min(pipeBlocks.size() / 5, 100)", "Math.min(pipeBlocks.size() / 5, 200)")),
        ("base_overpressure_fire", "V3.", t(BASEBE, "5F, false, Level.ExplosionInteraction.NONE", "5F, true, Level.ExplosionInteraction.NONE")),
        ("base_overpressure_gate", "V3.", t(BASEBE, "if(RBMKDials.getOverpressure() && !pipes.isEmpty())", "if(!pipes.isEmpty())")),
        ("base_ports_top", "V3.", t(BASEBE, "cons.add(new DirPos(core.above(h + 1), Direction.UP));", "cons.add(new DirPos(core.above(h), Direction.UP));")),
        ("base_ports_close_loader", "V3.", t(BASEBE, "loader = core.below();", "loader = core.below(2);")),
        ("loader_up_trait", "V3.", t(LOADBLK, "if(dir == Direction.UP) return type.hasTrait(FT_Heatable.class);", "if(dir == Direction.UP) return type.hasTrait(FT_Coolable.class);")),
        ("loader_pfm_dropped", "V3.", t(LOADBLK, " || type == Fluids.PERFLUOROMETHYL", "")),
        ("boiler_client_import", "V3.|V4.", t(BOI, "package com.hbm.blockentity.machine.rbmk;", "package com.hbm.blockentity.machine.rbmk;\n\nimport net.minecraft.client.Minecraft;")),
        # ---- V4 registrations, blocks, screens, renderers, particle
        ("reg_boiler_block_dropped", "V4.", T(NB, lambda x: drop_line(x, "RBMK_BOILER = register("))),
        ("reg_menu_duplicated", "V4.", T(MT, lambda x: dup_line(x, 'RBMK_BOILER = reg("rbmk_boiler"'))),
        ("reg_block_entity_wrong_block", "V4.", t(BET, "RBMKCoolerBlockEntity::new, NtmBlocks.RBMK_COOLER.get()", "RBMKCoolerBlockEntity::new, NtmBlocks.RBMK_HEATER.get()")),
        ("reg_screen_dropped", "V4.", T(NMC, lambda x: drop_line(x, "RBMKHeaterScreen::new);"))),
        ("reg_piped_renderer_dropped", "V4.", T(CP, lambda x: drop_line(x, "NtmBlockEntityTypes.RBMK_BOILER.get(), new RenderRBMKPiped<>()"))),
        ("reg_tab_order", "V4.", T(CT, lambda x: swap_lines(x, "output.accept(NtmBlocks.RBMK_CONTROL);", "output.accept(NtmBlocks.RBMK_CONTROL_AUTO);"))),
        ("block_own_lid_dropped", "V4.", t(CBLK, "protected boolean hasOwnLid() {\n        return true;", "protected boolean hasOwnLid() {\n        return false;")),
        ("collision_ignores_own_lid", "V4.", t(BASEBLK, "this.hasOwnLid() || ", "")),
        ("lid_shape_height", "V4.", t(BASEBLK, "Shapes.box(0, 0, 0, 1, 1.25, 1)", "Shapes.box(0, 0, 0, 1, 1.3, 1)")),
        ("heater_slot_any_item", "V4.", t(HMENU, "return stack.getItem() instanceof IItemFluidIdentifier;", "return true;")),
        ("screen_control_height", "V4.", t(CSCREEN, "this.imageHeight = 186;", "this.imageHeight = 187;")),
        ("screen_control_step", "V4.", t(CSCREEN, 'data.putDouble("level", 1.0D - (k * 0.25D));', 'data.putDouble("level", 1.0D - (k * 0.2D));')),
        ("screen_boiler_payload", "V4.", t(BSCREEN, 'data.putBoolean("compression", true);', 'data.putBoolean("compression", false);')),
        ("screen_auto_field_height", "V4.", t(ASCREEN, "26, 6, Component.empty());", "26, 8, Component.empty());")),
        ("render_control_texture", "V4.", t(RCONTROL, "texture = ResourceManager.RBMK_CONTROL_TEX;", "texture = ResourceManager.RBMK_CONTROL_AUTO_TEX;")),
        ("particle_age", "V4.", t(PARTICLE, "this.lifetime = 10;", "this.lifetime = 12;")),
        ("particle_alpha", "V4.", t(PARTICLE, "this.alpha = 0.25F;", "this.alpha = 0.5F;")),
        # ---- V5 recipes
        ("recipe_pattern", "V5.", gen_edit(RECIPES + "rbmk_control.json", lambda d: d["pattern"].__setitem__(0, "BB "))),
        ("recipe_ingredient", "V5.", gen_edit(RECIPES + "rbmk_boiler.json", lambda d: d["key"]["C"].__setitem__("item", "hbmsntm:pipe_steel"))),
        ("recipe_count", "V5.", gen_edit(RECIPES + "rbmk_loader.json", lambda d: d["result"].__setitem__("count", 2))),
        ("recipe_tag_to_item", "V5.", gen_edit(RECIPES + "rbmk_heater.json", lambda d: d["key"].__setitem__("I", {"item": "hbmsntm:ingot_polymer"}))),
        ("recipe_control_mod_added", "V5.|V6.", lambda st: st.set_bytes(RECIPES + "rbmk_control_mod.json", b"{}")),
        ("advancement_criterion", "V5.", gen_edit(ADV + "misc/rbmk_cooler.json", lambda d: d["criteria"]["has_rbmk_blank"]["conditions"]["items"][0].__setitem__("items", "hbmsntm:rbmk_control"))),
        ("anvil_recipes_touched", "V5.", T(ANVIL, lambda x: x + "\n// stray\n")),
        ("provider_pattern_changed", "V5.", t(RP, '.pattern("CIC")\n                .pattern("PRP")', '.pattern("CIC")\n                .pattern("PPP")')),
        # ---- V6 datagen outputs
        ("blockstate_model", "V6.", gen_edit(G_STATE + "rbmk_loader.json", lambda d: d["variants"][""].__setitem__("model", "hbmsntm:block/rbmk_boiler"))),
        ("block_model_texture", "V6.", gen_edit(G_BMODEL + "rbmk_cooler.json", lambda d: d["textures"].__setitem__("side", "hbmsntm:block/rbmk/rbmk_cooler_top"))),
        ("loot_rolls", "V6.", gen_edit(G_LOOT + "rbmk_heater.json", lambda d: d["pools"][0].__setitem__("rolls", 2.0))),
        ("item_model_parent", "V6.", gen_edit(G_IMODEL + "rbmk_control_auto.json", lambda d: d.__setitem__("parent", "hbmsntm:block/rbmk_control"))),
        ("pickaxe_entry_dropped", "V6.", T(PICK, lambda x: drop_line(x, '"hbmsntm:rbmk_loader",'))),
        ("generated_extra_file", "V6.", lambda st: st.set_bytes(G_STATE + "rbmk_stray.json", b"{}")),
        ("provider_tag_extra_block", "V6.", t(TAGP, "NtmBlocks.RBMK_LOADER.get(),", "NtmBlocks.RBMK_LOADER.get(),\n                        NtmBlocks.PRIBRIS.get(),")),
        ("stamp_generated_hash", "V6.", lambda st: st.set_text(STAMP, json_edit(st.text(STAMP), lambda d: d["generated"].__setitem__(next(iter(d["generated"])), "0" * 64)))),
        ("stamp_input_hash", "V6.", lambda st: st.set_text(STAMP, json_edit(st.text(STAMP), lambda d: d["inputs"].__setitem__(CTL, "0" * 64)))),
        # ---- V7 language
        ("zh_value_changed", "V7.", zh_set("block.hbmsntm.rbmk_boiler", "RBMK蒸汽管道")),
        ("zh_local_tip_reverted", "V7.", zh_set("container.rbmkControlAuto.levelLower", "最低温度时的控制棒深度$应大于最高温度时的控制棒深度")),
        ("zh_key_removed", "V7.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("tile.rbmk.dodd.t1_p")))),
        ("zh_crlf_broken", "V7.", Bx(ZH, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_crlf_broken", "V7.", Bx(MAP, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_source_zh_changed", "V7.", map_set("tile.rbmk.dodd.mult", "source_zh", "乘数")),
        ("map_local_reason_cite", "V7.", map_set("container.rbmkControlAuto.save", "reason", "Goal24D：原版 GUIRBMKControlAuto.java:170-187 的悬停提示为硬编码英文。")),
        ("map_kind_flipped", "V7.", map_set("container.rbmkControlAuto.linear", "kind", "upstream")),
        ("map_entry_removed", "V7.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"].pop("block.hbmsntm.rbmk_heater")))),
        ("provider_string_changed", "V7.", t(LP, 'this.add(NtmBlocks.RBMK_COOLER, "RBMK Cooler");', 'this.add(NtmBlocks.RBMK_COOLER, "RBMK Cooler ");')),
        ("en_value_changed", "V7.", lambda st: st.set_text(EN, st.text(EN).replace('"Feed Pressure"', '"Feed pressure"'))),
        ("tooltip_cite_wrong", "V7.", t(ASCREEN, "hard-coded English in the original (:72-89)", "hard-coded English in the original (:170-187)")),
        # ---- V8 resources
        ("texture_byte_flipped", "V8.", Bx(TEX + "rbmk/rbmk_control_side.png", flip_byte)),
        ("gui_texture_byte_flipped", "V8.", Bx(GUITEX + "gui_rbmk_boiler.png", flip_byte)),
        ("obj_line_endings_changed", "V8.", Bx(OBJDIR + "rbmk_rods.obj", lambda b: b.replace(b"\r\n", b"\n"))),
        ("particle_byte_flipped", "V8.", Bx(PARTICLE_NEO, flip_byte)),
        ("texture_deleted", "V8.", D(TEX + "rbmk/rbmk_heater_pipe_top.png")),
        ("reasim_texture_imported", "V8.", lambda st: st.set_bytes(TEX + "rbmk/rbmk_control_reasim_top.png", b"x")),
        ("ownership_asset_dropped", "V8.", own_edit(lambda d: d["assets"].pop(5))),
        ("ownership_sha_changed", "V8.", own_edit(lambda d: d["assets"][7].__setitem__("target_sha256", "0" * 64))),
        ("ownership_obj_field", "V8.", own_edit(lambda d: next(a for a in d["assets"] if a["target_path"].endswith("rbmk_rods.obj")).__setitem__("worktree_crlf_lines", 375))),
        ("ownership_not_imported_dropped", "V8.", own_edit(lambda d: d["not_imported"].pop())),
        # ---- V9 scope
        ("stray_src_file_added", "V9.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}")),
        ("unrelated_src_file_touched", "V9.", touch(DIALS)),
        ("anvil_file_touched", "V9.|V5.", touch(ANVIL)),
        ("unrelated_migration_file_added", "V9.", lambda st: st.set_bytes("migration/stray.json", b"{}")),
        ("edited_file_line_removed", "V9.", T(NB, lambda x: drop_line(x, "RBMK_ABSORBER = register("))),
        ("edited_file_eol_mixed", "V9.", Bx(NB, lambda b: b.replace(b"\r\n", b"\n", 1) if b"\r\n" in b else b.replace(b"\n", b"\r\n", 1))),
        # ---- V10 GameTest source
        ("gt_marker_changed", "V10.", T(GT, lambda x: x.replace('"' + GT_MARK + ' {} passed"', '"[hbm-rbmk] {} passed"')), GT),
        ("gt_holder_removed", "V10.", T(GT, lambda x: rep1(x, "@GameTestHolder(NuclearTechMod.MODID)", "")), GT),
        ("gt_batch_shared", "V10.", T(GT, lambda x: rep1(x, 'batch = "rbmk_cs_surge"', 'batch = "rbmk_cs_neutron"')), GT),
        ("gt_client_class", "V10.", T(GT, lambda x: rep1(x, "public class RBMKControlSteamGameTests {", "public class RBMKControlSteamGameTests {\n    private static final Class<?> BAD = net.minecraft.client.Minecraft.class;")), GT),
        ("gt_deleted", "V10.", D(GT), GT),
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
            try:
                inp2.ov, inp2.ov_error = parse_original(inp2), None
            except Exception as error:  # noqa: BLE001
                inp2.ov, inp2.ov_error = None, repr(error)
        ck = static_suite(inp2, mutated, v1=bool(mutated.orig_edits))
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


# ---------------------------------------------------------------- main

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
    for sec, value in secs.items():
        print(f"{sec}: {value['status']} ({value.get('passed', 0)}/{value.get('checks', 0)})")
    print(f"checks {ck.passed()} passed, {len(ck.failed())} failed; mutations {len(applied) - len(undetected)}/{len(applied)} detected"
          + (f" ({len(skipped)} skipped: {skipped})" if skipped else "") + f"; report: {(OUT / 'report.json').relative_to(ROOT).as_posix()}")
    sys.exit(0 if not ck.failed() and not undetected else 1)


if __name__ == "__main__":
    main()
