"""Verify the Goal24E batch statically: the RBMK console (rbmk_console: RBMKConsoleBlockEntity, RBMKConsoleBlock, RBMKConsoleMenu, RBMKConsoleScreen, RenderRBMKConsole),
the linking tool (rbmk_tool: RBMKToolItem), the shutdown sound, the two recipes, the datagen outputs, the new language keys, the imported resources and the GameTest source.

Read-only for both worktrees. Writes only build/migration/goal24e/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal24e/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (console block entity, block, tool, GUI, renderer, resources, recipes, sound, language) parsed from the read-only worktree at the cited lines; a moved line fails loudly.
- V2  The console block entity against V1 (and: no other RBMK file changed).
- V3  Block, menu and item against V1.
- V4  Client: screen, renderer, registrations, client isolation.
- V5  Recipes.
- V6  Datagen outputs.
- V7  Language: the new keys in the provider, en_us.json, zh_cn.json and zh_cn-map.json.
- V8  Resources: the imported files against the original and migration/goal24e-resource-ownership.json.
- V9  Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed separately).
- V10 GameTest source. V11 (--gametest-log) the GameTest log. V12 (--jar) the packaged JAR; "not run" when the flag is absent.
- V13 In-memory mutations of the NEO inputs and of the original text (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal24e_rbmk_console.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal24e"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "1114adf5de758697842e1f2195c0e3928b04abbc"

J = "src/main/java/com/hbm/"
BE = J + "blockentity/machine/rbmk/"
BLK = J + "blocks/machine/rbmk/"
CON = BE + "RBMKConsoleBlockEntity.java"
CBLK = BLK + "RBMKConsoleBlock.java"
CMENU = J + "inventory/menus/RBMKConsoleMenu.java"
CSCREEN = J + "inventory/screens/RBMKConsoleScreen.java"
RCON = J + "render/blockentity/RenderRBMKConsole.java"
TOOL = J + "items/tools/RBMKToolItem.java"
NEW_CLASSES = [CON, CBLK, CMENU, CSCREEN, RCON, TOOL]
NB = J + "blocks/NtmBlocks.java"
BET = J + "blockentity/NtmBlockEntityTypes.java"
MT = J + "inventory/NtmMenuTypes.java"
NITEMS = J + "items/NtmItems.java"
SOUNDS = J + "registry/NtmSoundEvents.java"
SDP = J + "datagen/NtmSoundDefinitionsProvider.java"
NMC = J + "main/NuclearTechModClient.java"
CP = J + "main/ClientProxy.java"
RM = J + "main/ResourceManager.java"
CT = J + "inventory/NtmCreativeTabs.java"
BSP = J + "datagen/NtmBlockStateProvider.java"
IMP = J + "datagen/NtmItemModelProvider.java"
LOOT = J + "datagen/NtmBlockLootTableProvider.java"
TAGP = J + "datagen/NtmBlockTagProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
RP = J + "datagen/NtmRecipeProvider.java"
EDITED = [NB, BET, MT, NITEMS, SOUNDS, SDP, NMC, CP, RM, CT, BSP, IMP, LOOT, TAGP, LP, RP]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal24e-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
PICK = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
SJSON = GEN + "assets/hbmsntm/sounds.json"
G_STATE = GEN + "assets/hbmsntm/blockstates/"
G_BMODEL = GEN + "assets/hbmsntm/models/block/"
G_IMODEL = GEN + "assets/hbmsntm/models/item/"
G_LOOT = GEN + "data/hbmsntm/loot_table/blocks/"
RECIPES = GEN + "data/hbmsntm/recipe/"
ADV = GEN + "data/hbmsntm/advancement/recipes/"
RES = "src/main/resources/assets/hbmsntm/"
GT = J + "gametest/RBMKConsoleGameTests.java"
GT_DIR = J + "gametest/"

# files the console must only read, never change (they stay byte-equal to the start copies)
UNTOUCHED = [BE + n for n in ("RBMKBaseBlockEntity.java", "RBMKColumnType.java", "RBMKControlManualBlockEntity.java", "RBMKControlBlockEntity.java", "RBMKControlAutoBlockEntity.java", "RBMKBoilerBlockEntity.java",
                              "RBMKRodBlockEntity.java", "RBMKSlottedBaseBlockEntity.java", "RBMKDials.java", "RBMKType.java", "RBMKHeaterBlockEntity.java", "RBMKCoolerBlockEntity.java")] + [
    BLK + "RBMKBaseBlock.java", BLK + "RBMKControlBlock.java", BLK + "RBMKRodBlock.java", J + "handler/neutron/RBMKNeutronHandler.java", J + "network/toserver/CompoundTagControl.java",
    J + "network/toclient/BufPacket.java", J + "blocks/DummyableBlock.java", J + "handler/MultiblockHandlerXR.java", J + "inventory/recipes/anvil/AnvilRecipes.java", "src/main/java/api/hbm/block/IToolable.java",
    J + "interfaces/IControlReceiver.java", J + "blockentity/LoadedBaseBlockEntity.java", J + "blockentity/IBufPacketReceiver.java"]

O = "src/main/java/com/hbm/"
O_CON = O + "tileentity/machine/rbmk/TileEntityRBMKConsole.java"
O_BLK = O + "blocks/machine/rbmk/RBMKConsole.java"
O_TOOL = O + "items/tool/ItemRBMKTool.java"
O_GUI = O + "inventory/gui/GUIRBMKConsole.java"
O_REN = O + "render/tileentity/RenderRBMKConsole.java"
O_RM = O + "main/ResourceManager.java"
O_CM = O + "main/CraftingManager.java"
O_TR = O + "crafting/ToolRecipes.java"
O_MB = O + "blocks/ModBlocks.java"
O_MI = O + "items/ModItems.java"
O_TM = O + "tileentity/TileMappings.java"
O_CPROXY = O + "main/ClientProxy.java"
O_EU = O + "util/EnumUtil.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"
O_SOUNDS = O_RES + "sounds.json"

GT_MARK = "[hbm-rbmk-console]"
START_GAMETESTS = 192
HASH_SKIP = ("__pycache__",)

# (NEO key, original key, en_US.lang line, zh_CN.lang line); the texts are read from the original in V1 and compared with NEO in V7
UP = [
    ("block.hbmsntm.rbmk_console", "tile.rbmk_console.name", 6215, 5342),
    ("item.hbmsntm.rbmk_tool", "item.rbmk_tool.name", 4231, 3663),
    ("item.hbmsntm.rbmk_tool.desc", "item.rbmk_tool.desc", 4232, 3664),
    ("item.hbmsntm.rbmk_tool.linked", "item.rbmk_tool.linked", 4233, 3665),
    ("item.hbmsntm.rbmk_tool.set", "item.rbmk_tool.set", 4234, 3666),
    ("rbmk.heat", "rbmk.heat", 4996, 4292),
    ("rbmk.console.assign", "rbmk.console.assign", 5000, 4296),
    ("rbmk.console.none", "rbmk.console.none", 5001, 4297),
    ("rbmk.console.col_temp", "rbmk.console.col_temp", 5002, 4298),
    ("rbmk.console.rod_extraction", "rbmk.console.rod_extraction", 5003, 4299),
    ("rbmk.console.fuel_depletion", "rbmk.console.fuel_depletion", 5004, 4300),
    ("rbmk.console.fuel_poison", "rbmk.console.fuel_poison", 5005, 4301),
    ("rbmk.console.fuel_temp", "rbmk.console.fuel_temp", 5006, 4302),
    ("rbmk.moderated", "rbmk.moderated", 5013, 4309),
    ("rbmk.rod.depletion", "rbmk.rod.depletion", 5014, 4310),
    ("rbmk.rod.xenon", "rbmk.rod.xenon", 5015, 4311),
    ("rbmk.rod.coreTemp", "rbmk.rod.coreTemp", 5016, 4312),
    ("rbmk.rod.skinTemp", "rbmk.rod.skinTemp", 5017, 4313),
    ("rbmk.screen.core", "rbmk.screen.core", 5018, 4314),
    ("rbmk.screen.depletion", "rbmk.screen.depletion", 5019, 4315),
    ("rbmk.screen.rod", "rbmk.screen.rod", 5020, 4316),
    ("rbmk.screen.temp", "rbmk.screen.temp", 5021, 4317),
    ("rbmk.screen.xenon", "rbmk.screen.xenon", 5022, 4318)]
UP_EXISTING_24D = ["rbmk.boiler.water", "rbmk.boiler.steam", "rbmk.boiler.type", "rbmk.control.level", "rbmk.control.red", "rbmk.control.yellow", "rbmk.control.green", "rbmk.control.blue", "rbmk.control.purple"]
GROUPS = [("red", "红"), ("yellow", "黄"), ("green", "绿"), ("blue", "蓝"), ("purple", "紫")]
TYPES = [("blank", "BLANK", "结构柱"), ("fuel", "FUEL", "燃料通道"), ("fuel_sim", "FUEL_SIM", "模拟燃料通道"), ("control", "CONTROL", "控制棒"), ("control_auto", "CONTROL_AUTO", "自动控制棒"),
         ("boiler", "BOILER", "蒸汽管道"), ("moderator", "MODERATOR", "慢化剂"), ("absorber", "ABSORBER", "中子吸收器"), ("reflector", "REFLECTOR", "中子反射器"), ("outgasser", "OUTGASSER", "辐照通道"),
         ("breeder", "BREEDER", "增殖柱"), ("storage", "STORAGE", "存储柱"), ("cooler", "COOLER", "冷却器"), ("heatex", "HEATEX", "流体加热器")]
# local keys: NEO key -> (English, Chinese, GUIRBMKConsole line the English comes from)
LOCAL = {
    "rbmk.console.selectAll": ("Select all control rods", "选择全部控制棒", 95),
    "rbmk.console.deselectAll": ("Deselect all", "取消全部选择", 96),
    "rbmk.console.compressor": ("Cycle steam channel compressor setting", "切换蒸汽管道的压缩档位", 111)}
for _i, (_c, _z) in enumerate(GROUPS):
    LOCAL[f"rbmk.console.group.{_c}.select"] = (f"Left click: Select {_c} group", f"左键：选择{_z}组", 106 + _i)
    LOCAL[f"rbmk.console.group.{_c}.assign"] = (f"Right click: Assign {_c} group", f"右键：分配到{_z}组", 106 + _i)
for _k, _e, _z in TYPES:
    LOCAL[f"rbmk.console.type.{_k}"] = (_e, _z, 88)
UP_KEYS = [u[0] for u in UP]
NEW_KEYS = sorted(UP_KEYS + list(LOCAL))
NEW_COUNT = len(NEW_KEYS)

# imported resources: (original path under assets/hbm, NEO path under assets/hbmsntm)
IMPORTS = [("models/rbmk/rbmk_console.obj", "models/obj/rbmk/rbmk_console.obj"),
           ("textures/models/machines/rbmk_control.png", "textures/models/machines/rbmk_control.png"),
           ("textures/gui/reactors/gui_rbmk_console.png", "textures/gui/reactors/gui_rbmk_console.png"),
           ("textures/blocks/rbmk/rbmk_console.png", "textures/block/rbmk/rbmk_console.png"),
           ("textures/items/rbmk_tool.png", "textures/item/rbmk_tool.png"),
           ("sounds/block/shutdown.ogg", "sounds/block/shutdown.ogg")]
IMPORT_PATHS = [RES + n for _, n in IMPORTS]
OBJ_NEO = RES + "models/obj/rbmk/rbmk_console.obj"
GUI_PNG = RES + "textures/gui/reactors/gui_rbmk_console.png"
TEX_PNG = RES + "textures/models/machines/rbmk_control.png"
ICON_PNG = RES + "textures/block/rbmk/rbmk_console.png"
ITEM_PNG = RES + "textures/item/rbmk_tool.png"
OGG = RES + "sounds/block/shutdown.ogg"

# generated files this batch must add (blockstate / models / loot / recipes / advancements)
GEN_NEW = [G_STATE + "rbmk_console.json", G_BMODEL + "rbmk_console_particle.json", G_IMODEL + "rbmk_console.json", G_IMODEL + "rbmk_tool.json", G_LOOT + "rbmk_console.json",
           RECIPES + "rbmk_console.json", RECIPES + "rbmk_tool.json", ADV + "misc/rbmk_console.json", ADV + "tools/rbmk_tool.json"]
GEN_CHANGED = [STAMP, EN, PICK, SJSON]


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



# ---------------------------------------------------------------- shared helpers of V2..V4

def cs(st, path):
    """The squashed, number-normalised code of a NEO file (comments blanked)."""
    return sq(blank_comments(lf(st.text(path))))


def nbody(st, path, signature):
    """Squashed body of the unique NEO method whose header contains signature."""
    return body(lf(st.text(path)), signature)


def derive(s, pairs):
    """Apply literal replacements to a squashed original string; an anchor that is absent raises (the derivation no longer applies)."""
    for old, new in pairs:
        if old not in s:
            raise ValueError("derivation anchor missing: " + old[:80])
        s = s.replace(old, new)
    return s


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


def absent(code, frags):
    return [f for f in frags if f not in code]


WIRE = re.compile(r"buf\.writeBoolean\(screen\.display!=null\);if\(screen\.display!=null\)buf\.writeUtf\(screen\.display\);|buf\.readBoolean\(\)\?buf\.readUtf\(\):null"
                  r"|BufferUtil\.(?:write|read)String|BufferUtil\.(?:write|read)NBT|buf\.(?:write|read)Nbt|BufferUtil\.(?:write|read)IntArray|buf\.(?:write|read)VarIntArray|buf\.(?:write|read)(?:Boolean|Byte)")


def wire_ops(code):
    """The wire operations of a squashed serialize/deserialize body in source order: Z boolean, B byte, N compound, A int array, S nullable string."""
    out = []
    for m in WIRE.finditer(code):
        s = m[0]
        if "Utf" in s or "String" in s:
            out.append("S")
        elif "NBT" in s or "Nbt" in s:
            out.append("N")
        elif "IntArray" in s:
            out.append("A")
        elif "Boolean" in s:
            out.append("Z")
        else:
            out.append("B")
    return out


def rects(code, left, top):
    """The (x, y, w, h) tuples of the `if(<left>+x<=mouseX&&<left>+x+w>mouseX&&<top>+y<mouseY&&<top>+y+h>=mouseY)` tests of a squashed method body."""
    pat = (r"if\(" + left + r"\+(.+?)<=mouseX&&" + left + r"\+\1\+(.+?)>mouseX&&" + top + r"\+(.+?)<mouseY&&" + top + r"\+\3\+(.+?)>=mouseY\)")
    return [(m[1], m[3], m[2], m[4]) for m in re.finditer(pat, code)]


def info_stats(code, left, top):
    """The (x, y, w, h) of the drawCustomInfoStat calls of a squashed method body, in source order."""
    pat = r"drawCustomInfoStat\((?:guiGraphics,)?mouseX,mouseY," + left + r"\+(.+?)," + top + r"\+(.+?),(\d+),(\d+),mouseX,mouseY"
    return [m.groups() for m in re.finditer(pat, code)]


def control_ops(code, set_prefix):
    """Ordered (type, key) of the `control.<set|put><Type>("key", ...)` statements of a squashed body; Integer and Int are one type."""
    out = []
    for m in re.finditer(r"control\." + set_prefix + r"(\w+?)\(\"([^\"]+)\"", code):
        t = {"Integer": "Int"}.get(m[1], m[1])
        out.append((t, m[2]))
    return out


def sound_calls(code, orig):
    """Ordered (sound, pitch) pairs of the sounds a click handler plays. orig: the original's func_147674_a calls, else the NEO click()/play() helper calls."""
    out = []
    if orig:
        i = 0
        while True:
            j = code.find("func_147674_a(", i)
            if j < 0:
                return out
            end = match_paren(code, j + len("func_147674_a"))
            inner = code[j + len("func_147674_a(") : end]
            m = re.match(r'newResourceLocation\("([^"]+)"\),(.*)$', inner)
            name = {"gui.button.press": "click", "hbm:block.rbmk_az5_cover": "RBMK_AZ5_COVER", "hbm:block.shutdown": "SHUTDOWN"}[m[1]]
            out.append((name, m[2]))
            i = end
    else:
        for m in re.finditer(r"this\.click\(([^;]*)\);|this\.play\(NtmSoundEvents\.(\w+)\.get\(\),([^;]*)\);", code):
            out.append(("click", m[1]) if m[1] is not None else (m[2], m[3]))
        return out


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
    names = dict(con=O_CON, blk=O_BLK, tool=O_TOOL, gui=O_GUI, ren=O_REN, rm=O_RM, cm=O_CM, tr=O_TR, mb=O_MB, mi=O_MI, tm=O_TM, cproxy=O_CPROXY, eu=O_EU)
    inp.o = {name: otext(path) for name, path in names.items()}
    inp.o["sounds"] = lf(read_text(ORIGINAL / O_SOUNDS))
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    inp.o_en_lines = lf(read_text(ORIGINAL / O_LANG / "en_US.lang")).split("\n")
    inp.o_zh_lines = lf(read_text(ORIGINAL / O_LANG / "zh_CN.lang")).split("\n")
    tree = hash_tree()
    files = {}
    load = set(NEW_CLASSES + EDITED + UNTOUCHED + [ZH, MAP, OWN, EN, STAMP, PICK, SJSON, GT, GEN + "assets/hbmsntm/sounds.json"])
    for p in tree:
        if p not in inp.base_files and (p.startswith(GEN) or p.startswith(GT_DIR)):
            load.add(p)
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    for _, neo in IMPORTS:
        if (ROOT / (RES + neo)).exists():
            files[RES + neo] = (ROOT / (RES + neo)).read_bytes()
    for p in GEN_NEW:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.stamp_now, inp.gen_now = stamp_hashes()
    inp.own = json.loads(files[OWN].decode("utf-8")) if OWN in files else {"assets": [], "not_imported": []}
    inp.o_res = {}
    for orig, neo in IMPORTS:
        f = ORIGINAL / (O_RES + orig)
        if f.exists():
            inp.o_res[RES + neo] = f.read_bytes()
    inp.o_blob = {}
    for orig, neo in IMPORTS:
        if orig.endswith(".obj"):
            try:
                inp.o_blob[RES + neo] = git(ORIGINAL, "show", "HEAD:" + O_RES + orig)
            except Exception:  # noqa: BLE001 - reported by V8
                inp.o_blob[RES + neo] = None

    def last_commit(pair):
        return git(ORIGINAL, "log", "-1", "--format=%H", "--", O_RES + pair[0]).decode("utf-8").strip()
    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
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


# ---------------------------------------------------------------- the original: signatures parsed once, anchors checked in V1

# key -> (inputs key, exact method header in the original)
ORIG_SIGS = {
    "con.update": ("con", "public void updateEntity()"),
    "con.rescan": ("con", "private void rescan()"),
    "con.prepare": ("con", "private void prepareScreenInfo()"),
    "con.serialize": ("con", "public void serialize(ByteBuf buf)"),
    "con.deserialize": ("con", "public void deserialize(ByteBuf buf)"),
    "con.perm": ("con", "public boolean hasPermission(EntityPlayer player)"),
    "con.receive": ("con", "public void receiveControl(EntityPlayer player, NBTTagCompound data)"),
    "con.bbox": ("con", "public AxisAlignedBB getRenderBoundingBox()"),
    "con.setTarget": ("con", "public void setTarget(int x, int y, int z)"),
    "con.read": ("con", "public void readFromNBT(NBTTagCompound nbt)"),
    "con.write": ("con", "public void writeToNBT(NBTTagCompound nbt)"),
    "con.rotate": ("con", "public void rotate()"),
    "con.getX": ("con", "public int getXFromIndex(int col)"),
    "con.getZ": ("con", "public int getZFromIndex(int col)"),
    "con.fancy": ("con", "public List<String> getFancyStats()"),
    "blk.create": ("blk", "public TileEntity createNewTileEntity(World world, int meta)"),
    "blk.activated": ("blk", "public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player, int side, float hitX, float hitY, float hitZ)"),
    "blk.dims": ("blk", "public int[] getDimensions()"),
    "blk.offset": ("blk", "public int getOffset()"),
    "blk.fill": ("blk", "public void fillSpace(World world, int x, int y, int z, ForgeDirection dir, int o)"),
    "blk.check": ("blk", "protected boolean checkRequirement(World world, int x, int y, int z, ForgeDirection dir, int o)"),
    "blk.screw": ("blk", "public boolean onScrew(World world, EntityPlayer player, int x, int y, int z, int side, float fX, float fY, float fZ, ToolType tool)"),
    "tool.use": ("tool", "public boolean onItemUse(ItemStack stack, EntityPlayer player, World world, int x, int y, int z, int side, float fX, float fY, float fZ)"),
    "tool.info": ("tool", "public void addInformation(ItemStack stack, EntityPlayer player, List list, boolean bool)"),
    "tool.attr": ("tool", "public Multimap getAttributeModifiers(ItemStack stack)"),
    "ren.render": ("ren", "public void renderTileEntityAt(TileEntity te, double x, double y, double z, float interp)"),
    "ren.column": ("ren", "private void drawColumn(Tessellator tess, double x, double y, double z, float color, double heat)"),
    "ren.dot": ("ren", "private void drawDot(Tessellator tess, double x, double y, double z, float r, float g, float b)"),
    "gui.draw": ("gui", "public void drawScreen(int mouseX, int mouseY, float f)"),
    "gui.click": ("gui", "protected void mouseClicked(int mouseX, int mouseY, int key)"),
    "gui.bg": ("gui", "protected void drawGuiContainerBackgroundLayer(float interp, int mX, int mY)"),
    "gui.key": ("gui", "protected void keyTyped(char c, int i)"),
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


def enum_members(text, name):
    """{member: offset expression} of an original enum `name` (offset constant evaluated)."""
    m = re.search(r"enum " + name + r" \{(.*?);\s*public (?:final )?int offset", text, re.S)
    if not m:
        raise ValueError("enum " + name)
    out = {}
    for mm in re.finditer(r"(\w+)\(([^)]*)\)", blank_comments(m[1])):
        out[mm[1]] = eval(mm[2], {"__builtins__": {}})  # noqa: S307 - integer constants of the original source only
    return out


def parse_rot_table(code_x):
    """{rotation: expression} of a squashed getXFromIndex/getZFromIndex body: switch(rotation){case0:return..;case1:return..;...}return..;"""
    m = re.search(r"switch\((?:this\.)?rotation\)\{(.*)\}return(.*?);$", code_x)
    if not m:
        raise ValueError("no rotation switch: " + code_x[:80])
    return dict(re.findall(r"case(\d):return(.*?);", m[1])), m[2]


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) >= 40 and len(inp.baseline["copied_scope"]) == 47 and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, 47 in copied_scope) hashes to its baseline.json entry", bad)
    needed = NEW_CLASSES + EDITED + [ZH, MAP, OWN, EN, STAMP, PICK, SJSON]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 1114adf5", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.original-parsed", inp.ov is not None, "the original sources were parsed at the cited headers", inp.ov_error)
    ck("V0.untouched-in-baseline", all(p in inp.base_files for p in UNTOUCHED), "every file the console must leave alone exists in baseline.json", [p for p in UNTOUCHED if p not in inp.base_files])


# ---------------------------------------------------------------- V1

def parse_cm_row(line):
    """(result block name, count, pattern rows, {key char: expression}) of one addRecipeAuto row of CraftingManager."""
    m = re.search(r"addRecipeAuto\(new ItemStack\(ModBlocks\.(\w+), (\d+)\), new Object\[\] \{ (.*) \}\);", line)
    if not m:
        raise ValueError("not a recipe row: " + line.strip()[:80])
    return _split_row(m[1], int(m[2]), m[3])


def parse_tool_row(line):
    m = re.search(r"addRecipeAuto\(new ItemStack\(ModItems\.(\w+)\), new Object\[\] \{ (.*) \}\);", line)
    if not m:
        raise ValueError("not a recipe row: " + line.strip()[:80])
    return _split_row(m[1], 1, m[2])


def _split_row(name, count, rest_text):
    parts, depth, cur = [], 0, ""
    for ch in rest_text:
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
    return name, count, pattern, keys


def v1_original(ck, inp, st):
    ov = need_ov(inp)
    L = inp.ol
    # ---- TileEntityRBMKConsole.java: fields and tick
    t = L["con"]
    m = at_lines(t, {43: "private int targetX;", 44: "private int targetY;", 45: "private int targetZ;", 47: "private byte rotation;", 49: "public static final int fluxDisplayBuffer = 60;", 50: "public int[] fluxBuffer = new int[fluxDisplayBuffer];",
                     53: "public RBMKColumn[] columns = new RBMKColumn[15 * 15];", 55: "public RBMKScreen[] screens = new RBMKScreen[6];", 58: "super(0);", 60: "for(int i = 0; i < screens.length; i++) {", 61: "screens[i] = new RBMKScreen();",
                     73: "if(!worldObj.isRemote) {", 75: "if(this.worldObj.getTotalWorldTime() % 10 == 0) {", 78: "rescan();", 80: "prepareScreenInfo();", 83: "this.networkPackNT(50);"})
    order = [73, 75, 78, 80, 83]
    ck("V1.console-fields-tick", not m and order == sorted(order) and "public String getName() {" in t[65] and "return null;" in t[66],
       "TileEntityRBMKConsole.java:43-85: targetX/Y/Z, byte rotation, fluxDisplayBuffer 60, a 15 * 15 column array (one-dimensional), six screens created in the constructor, zero slots; the tick is server-only: every 10th world tick rescan() then "
       "prepareScreenInfo(), and networkPackNT(50) on EVERY tick (the next line after the % 10 block closes, :83); no title (getName null)", m)
    m = at_lines(t, {89: "double flux = 0;", 91: "for(int index = 0; index < columns.length; index++) {", 92: "int rx = getXFromIndex(index);", 93: "int rz = getZFromIndex(index);",
                     95: "TileEntity te = Compat.getTileStandard(worldObj, targetX + rx, targetY, targetZ + rz);", 97: "if(te instanceof TileEntityRBMKBase) {",
                     101: "columns[index] = new RBMKColumn(rbmk.getConsoleType(), rbmk.getNBTForConsole());", 102: 'columns[index].data.setDouble("heat", rbmk.heat);', 103: 'columns[index].data.setDouble("maxHeat", rbmk.maxHeat());',
                     104: 'columns[index].data.setByte("indicator", (byte) rbmk.craneIndicator);', 105: 'if(rbmk.isModerated()) columns[index].data.setBoolean("moderated", true);', 107: "if(te instanceof TileEntityRBMKRod) {",
                     109: "flux += fuel.lastFluxQuantity;", 112: "} else {", 113: "columns[index] = null;", 117: "for(int i = 0; i < this.fluxBuffer.length - 1; i++) {", 118: "this.fluxBuffer[i] = this.fluxBuffer[i + 1];",
                     121: "this.fluxBuffer[this.fluxBuffer.length - 1] = (int) flux;"})
    order = [95, 101, 102, 103, 104, 105, 109, 113, 118, 121]
    ck("V1.rescan", not m and order == sorted(order), "TileEntityRBMKConsole.java:87-122 rescan: for each of the 225 indices the tile at (targetX + rx, targetY, targetZ + rz) read with Compat.getTileStandard (no chunk load); an RBMK base becomes a column "
       "of (getConsoleType, getNBTForConsole) + heat, maxHeat, byte indicator (craneIndicator) and moderated=true only when moderated; a rod adds lastFluxQuantity to the flux; anything else is null; then the 60-entry flux buffer shifts left by one and the "
       "last entry is (int) flux", m)
    m = at_lines(t, {129: "if(screen.type == ScreenType.NONE) {", 130: "screen.display = null;", 137: "for(Integer i : screen.columns) {", 139: "RBMKColumn col = this.columns[i];", 141: "if(col == null) continue;",
                     144: "case COL_TEMP:", 145: "count++;", 146: 'value += col.data.getDouble("heat");', 148: "case FUEL_DEPLETION:", 149: 'if(col.data.hasKey("enrichment")) {', 151: 'value += (100D - (col.data.getDouble("enrichment") * 100D));',
                     154: "case FUEL_POISON:", 155: 'if(col.data.hasKey("xenon")) {', 157: 'value += col.data.getDouble("xenon");', 160: "case FUEL_TEMP:", 161: 'if(col.data.hasKey("c_heat")) {', 163: 'value += col.data.getDouble("c_heat");',
                     166: "case ROD_EXTRACTION:", 167: 'if(col.data.hasKey("level")) {', 169: 'value += col.data.getDouble("level") * 100;', 175: "double result = value / (double) count;", 176: 'String text = ((int)(result * 10)) / 10D + "";',
                     179: 'case COL_TEMP: text = "rbmk.screen.temp=" + text + "°C"; break;', 180: 'case FUEL_DEPLETION: text = "rbmk.screen.depletion=" + text + "%"; break;', 181: 'case FUEL_POISON: text = "rbmk.screen.xenon=" + text + "%"; break;',
                     182: 'case FUEL_TEMP: text = "rbmk.screen.core=" + text + "°C"; break;', 183: 'case ROD_EXTRACTION: text = "rbmk.screen.rod=" + text + "%"; break;', 186: "screen.display = text;"})
    ck("V1.prepare-screen-info", not m, "TileEntityRBMKConsole.java:125-188 prepareScreenInfo: NONE -> display null; otherwise over the screen's column list (null columns skipped): COL_TEMP adds heat, FUEL_DEPLETION 100 - enrichment * 100 when `enrichment` "
       "exists, FUEL_POISON xenon, FUEL_TEMP c_heat, ROD_EXTRACTION level * 100 (each only counted when the key exists); result = value / (double) count (NaN for count 0), text = ((int)(result * 10)) / 10D; prefixes rbmk.screen.temp= (°C), depletion= (%), "
       "xenon= (%), core= (°C), rod= (%)", m)
    m = at_lines(t, {194: "if (this.worldObj.getTotalWorldTime() % 10 == 0) {", 195: "buf.writeBoolean(true);", 198: "if (column == null || column.type == null)", 199: "buf.writeByte(-1);", 201: "buf.writeByte((byte) column.type.ordinal());",
                     202: "BufferUtil.writeNBT(buf, column.data);", 206: "BufferUtil.writeIntArray(buf, fluxBuffer);", 209: "BufferUtil.writeString(buf, screen.display);", 214: "buf.writeBoolean(false);", 217: "buf.writeByte((byte) screen.type.ordinal());",
                     226: "if (buf.readBoolean()) {", 229: "byte ordinal = buf.readByte();", 230: "if (ordinal == -1)", 231: "this.columns[i] = null;", 233: "new RBMKColumn(ColumnType.values()[ordinal], BufferUtil.readNBT(buf));",
                     236: "this.fluxBuffer = BufferUtil.readIntArray(buf);", 239: "screen.display = BufferUtil.readString(buf);", 245: "screen.type = ScreenType.values()[buf.readByte()];"})
    order = [194, 195, 199, 202, 206, 209, 214, 217]
    ck("V1.serialize-sync", not m and order == sorted(order), "TileEntityRBMKConsole.java:190-249: after super, a full packet on world ticks divisible by 10 (boolean true, per column byte -1 or the type ordinal + NBT, the int array, six display strings), "
       "otherwise boolean false + six screen-type ordinals; deserialize mirrors it (-1 = null column)", m)
    ck("V1.permission", not at_lines(t, {253: "Vec3.createVectorHelper(xCoord - player.posX, yCoord - player.posY, zCoord - player.posZ).lengthVector() < 20;"}),
       "TileEntityRBMKConsole.java:251-254 hasPermission: distance from the block corner (xCoord, yCoord, zCoord) to the player < 20")
    m = at_lines(t, {259: 'if(data.hasKey("level")) {', 261: "Set<String> keys = data.func_150296_c();", 265: 'if(key.startsWith("sel_")) {', 267: "int index = data.getInteger(key);", 271: "Compat.getTileStandard(worldObj, targetX + x, targetY, targetZ + z);",
                     273: "if(te instanceof TileEntityRBMKControlManual) {", 275: "rod.startingLevel = rod.level;", 276: 'rod.setTarget(MathHelper.clamp_double(data.getDouble("level"), 0, 1));', 277: "te.markDirty();",
                     283: 'if(data.hasKey("toggle")) {', 284: 'int slot = data.getByte("toggle");', 285: "int next = this.screens[slot].type.ordinal() + 1;", 286: "ScreenType type = ScreenType.values()[next % ScreenType.values().length];", 287: "this.screens[slot].type = type;",
                     290: 'if(data.hasKey("id")) {', 291: 'int slot = data.getByte("id");', 294: "for(int i = 0; i < 15 * 15; i++) {", 295: 'if(data.getBoolean("s" + i)) {', 301: "this.screens[slot].columns = cols;",
                     304: 'if(data.hasKey("assignColor")) {', 305: 'int color = data.getByte("assignColor");', 306: 'int[] cols = data.getIntArray("cols");', 314: "if(te instanceof TileEntityRBMKControlManual) {", 316: "rod.color = EnumUtil.grabEnumSafely(RBMKColor.class, color);",
                     322: 'if(data.hasKey("compressor")) {', 323: 'int[] cols = data.getIntArray("cols");', 331: "if(te instanceof TileEntityRBMKBoiler) {", 333: "rod.cyceCompressor();"})
    order = [259, 283, 290, 304, 322]
    ck("V1.receive-control", not m and order == sorted(order) and ov.b["con.receive"].count("markDirty()") == 2 and "TileEntityRBMKControlAuto" not in ov.b["con.receive"],
       "TileEntityRBMKConsole.java:256-337 receiveControl: five independent groups in this order: `level` (every `sel_*` key -> index -> the manual rod there: startingLevel = level, setTarget(clamp(level, 0, 1)), markDirty), `toggle` (byte slot, "
       "screen type = values()[(ordinal + 1) % 6]), `id` (byte slot, list of s0..s224 true -> the screen's columns), `assignColor` (byte colour + int[] cols -> manual rods get EnumUtil.grabEnumSafely colour; no toggle), `compressor` (cols -> boilers cyceCompressor); "
       "the original validates nothing and never touches the automatic rods", m)
    m = at_lines(t, {361: 'this.targetX = nbt.getInteger("tX");', 362: 'this.targetY = nbt.getInteger("tY");', 363: 'this.targetZ = nbt.getInteger("tZ");', 366: 'this.screens[i].type = ScreenType.values()[nbt.getByte("t" + i)];',
                     367: 'this.screens[i].columns = Arrays.stream(nbt.getIntArray("s" + i)).boxed().toArray(Integer[]::new);', 369: 'rotation = nbt.getByte("rotation");', 376: 'nbt.setInteger("tX", this.targetX);',
                     377: 'nbt.setInteger("tY", this.targetY);', 378: 'nbt.setInteger("tZ", this.targetZ);', 381: 'nbt.setByte("t" + i, (byte) this.screens[i].type.ordinal());', 382: 'nbt.setIntArray("s" + i,', 384: 'nbt.setByte("rotation", rotation);'})
    ck("V1.nbt", not m, "TileEntityRBMKConsole.java:357-385: NBT keys tX, tY, tZ (ints), t<i> (byte screen type ordinal) and s<i> (int array) for the six screens, rotation (byte); the columns and the flux buffer are not saved", m)
    m = at_lines(t, {350: "public void setTarget(int x, int y, int z) {", 351: "this.targetX = x;", 352: "this.targetY = y;", 353: "this.targetZ = z;", 354: "this.markDirty();", 387: "public void rotate() {", 388: "rotation = (byte)((rotation + 1) % 4);",
                     341: "return AxisAlignedBB.getBoundingBox(xCoord - 2, yCoord, zCoord - 2, xCoord + 3, yCoord + 4, zCoord + 3);", 347: "return 65536.0D;"})
    ck("V1.target-rotate-bbox", not m, "TileEntityRBMKConsole.java:339-355, :387-389: setTarget stores the three coordinates and marks dirty; rotate() = (rotation + 1) % 4 (the original only mutates, no markDirty); render bounding box "
       "(x - 2, y, z - 2)..(x + 3, y + 4, z + 3), max render distance squared 65536 (256 blocks)", m)
    ox, oz = ov.b["con.getX"], ov.b["con.getZ"]
    tx, tz = parse_rot_table(ox), parse_rot_table(oz)
    ck("V1.index-mapping", not at_lines(t, {392: "final int i = col % 15 - 7;", 393: "final int j = col / 15 - 7;"}) and tx == ({"0": "i", "1": "-j", "2": "-i", "3": "j"}, "i") and tz == ({"0": "j", "1": "i", "2": "-j", "3": "-i"}, "j"),
       "TileEntityRBMKConsole.java:391-423: i = col % 15 - 7, j = col / 15 - 7; rotation 0 (i | j), 1 (-j | i), 2 (-i | -j), 3 (j | -i) for X | Z, default (i | j)", (tx, tz))
    ct, sc = enum_members(inp.o["con"], "ColumnType"), enum_members(inp.o["con"], "ScreenType")
    ck("V1.enums", ct == {"BLANK": 0, "FUEL": 10, "FUEL_SIM": 90, "CONTROL": 20, "CONTROL_AUTO": 30, "BOILER": 40, "MODERATOR": 50, "ABSORBER": 60, "REFLECTOR": 70, "OUTGASSER": 80, "BREEDER": 100, "STORAGE": 110, "COOLER": 120, "HEATEX": 130}
       and list(ct) == ["BLANK", "FUEL", "FUEL_SIM", "CONTROL", "CONTROL_AUTO", "BOILER", "MODERATOR", "ABSORBER", "REFLECTOR", "OUTGASSER", "BREEDER", "STORAGE", "COOLER", "HEATEX"]
       and sc == {"NONE": 0, "COL_TEMP": 18, "ROD_EXTRACTION": 36, "FUEL_DEPLETION": 54, "FUEL_POISON": 72, "FUEL_TEMP": 90} and list(sc) == ["NONE", "COL_TEMP", "ROD_EXTRACTION", "FUEL_DEPLETION", "FUEL_POISON", "FUEL_TEMP"],
       "TileEntityRBMKConsole.java:502-523, :538-551: ColumnType (14 members, GUI texture u offsets BLANK 0, FUEL 10, FUEL_SIM 90, CONTROL 20, CONTROL_AUTO 30, BOILER 40, MODERATOR 50, ABSORBER 60, REFLECTOR 70, OUTGASSER 80, BREEDER 100, STORAGE 110, "
       "COOLER 120, HEATEX 130) and ScreenType (NONE 0, COL_TEMP 18, ROD_EXTRACTION 36, FUEL_DEPLETION 54, FUEL_POISON 72, FUEL_TEMP 90)", (ct, sc))
    m = at_lines(t, {425: "public static class RBMKColumn {", 437: "if(data != null) {", 440: "this.data = new NBTTagCompound();", 525: "public class RBMKScreen {", 526: "public ScreenType type = ScreenType.NONE;", 527: "public Integer[] columns = new Integer[0];",
                     528: "public String display = null;"})
    ck("V1.column-screen-classes", not m, "TileEntityRBMKConsole.java:425-442, :525-536: RBMKColumn(type, data) turns a null compound into an empty one; RBMKScreen has type NONE, an empty column array and display null", m)
    m = at_lines(t, {448: "if(this.data == null)", 459: 'stats.add(EnumChatFormatting.YELLOW + I18nUtil.resolveKey("rbmk.heat", ((int)((this.data.getDouble("heat") * 10D)) / 10D) + "°C"));',
                     462: "case FUEL:", 463: "case FUEL_SIM:", 464: 'stats.add(EnumChatFormatting.GREEN + I18nUtil.resolveKey("rbmk.rod.depletion", ((int)(((1D - this.data.getDouble("enrichment")) * 100000)) / 1000D) + "%"));',
                     465: 'stats.add(EnumChatFormatting.DARK_PURPLE + I18nUtil.resolveKey("rbmk.rod.xenon", ((int)(((this.data.getDouble("xenon")) * 1000D)) / 1000D) + "%"));',
                     466: 'stats.add(EnumChatFormatting.DARK_RED + I18nUtil.resolveKey("rbmk.rod.coreTemp", ((int)((this.data.getDouble("c_coreHeat") * 10D)) / 10D) + "°C"));',
                     467: 'stats.add(EnumChatFormatting.RED + I18nUtil.resolveKey("rbmk.rod.skinTemp", ((int)((this.data.getDouble("c_heat") * 10D)) / 10D) + "°C", ((int)((this.data.getDouble("c_maxHeat") * 10D)) / 10D) + "°C"));',
                     470: 'stats.add(EnumChatFormatting.BLUE + I18nUtil.resolveKey("rbmk.boiler.water", this.data.getInteger("water"), this.data.getInteger("maxWater")));',
                     471: 'stats.add(EnumChatFormatting.WHITE + I18nUtil.resolveKey("rbmk.boiler.steam", this.data.getInteger("steam"), this.data.getInteger("maxSteam")));',
                     472: 'stats.add(EnumChatFormatting.YELLOW + I18nUtil.resolveKey("rbmk.boiler.type", Fluids.fromID(this.data.getShort("type")).getLocalizedName()));',
                     474: "case CONTROL:", 476: 'if(this.data.hasKey("color")) {', 477: 'short col = this.data.getShort("color");', 479: "if(col >= 0 && col < RBMKColor.values().length)",
                     480: 'stats.add(EnumChatFormatting.YELLOW + I18nUtil.resolveKey("rbmk.control." + RBMKColor.values()[col].name().toLowerCase(Locale.US)));', 483: "case CONTROL_AUTO:",
                     484: 'stats.add(EnumChatFormatting.YELLOW + I18nUtil.resolveKey("rbmk.control.level", ((int)((this.data.getDouble("level") * 100D))) + "%"));', 487: "case HEATEX:",
                     488: 'stats.add(EnumChatFormatting.BLUE + Fluids.fromID(this.data.getShort("type")).getLocalizedName() + " " +', 489: 'this.data.getInteger("water") + "/" + this.data.getInteger("maxWater") + "mB");',
                     490: 'stats.add(EnumChatFormatting.RED + Fluids.fromID(this.data.getShort("hottype")).getLocalizedName() + " " +', 491: 'this.data.getInteger("steam") + "/" + this.data.getInteger("maxSteam") + "mB");',
                     495: 'if(data.getBoolean("moderated"))', 496: 'stats.add(EnumChatFormatting.YELLOW + I18nUtil.resolveKey("rbmk.moderated"));'})
    fancy = ov.b["con.fancy"]
    ck("V1.fancy-stats", not m and "break;caseCONTROL_AUTO:" not in fancy and "caseCONTROL:" in fancy and fancy.index("caseCONTROL:") < fancy.index("caseCONTROL_AUTO:") < fancy.index("caseHEATEX:") and fancy.count("break;") == 4,
       "TileEntityRBMKConsole.java:444-499 getFancyStats: yellow rbmk.heat first; FUEL/FUEL_SIM green depletion ((1 - enrichment) * 100000 / 1000), dark purple xenon, dark red core temperature, red skin temperature + max; BOILER blue water, white steam, "
       "yellow type; CONTROL optional yellow colour group (short 0 <= c < 5) and then FALLS THROUGH (no break) into CONTROL_AUTO's yellow level (int)(level * 100) + %; HEATEX blue/red `<fluid name> n/max mB`; yellow moderated last", m)
    ck("V1.compat-and-enum-util", "grabEnumSafely" in inp.o["eu"] and re.search(r"Math\.abs\(index % \w+\.length\)", inp.o["eu"]) is not None,
       "EnumUtil.java:5-9 grabEnumSafely(clazz, index) = values[abs(index % length)]: any colour byte maps into 0..4", inp.o["eu"][:200])
    # ---- RBMKConsole.java
    b = L["blk"]
    m = at_lines(b, {21: "public class RBMKConsole extends BlockDummyable implements IToolable {", 24: "super(Material.iron);", 25: "this.setHardness(3F);", 26: "this.setResistance(30F);", 32: "if(meta >= this.offset)", 33: "return new TileEntityRBMKConsole();",
                     35: "return null;", 40: "return -1;", 45: "return false;", 50: "return false;", 56: "if(!player.isSneaking()) {", 58: "BossSpawnHandler.markFBI(player);", 60: "int[] pos = this.findCore(world, x, y, z);", 62: "if(pos == null)",
                     68: "if(side == 1) {", 69: "Vec3 vec = Vec3.createVectorHelper(1.375D, 0, 0.75D);", 84: "player.inventory.hasItemStack(new ItemStack(ModItems.book_guide, 1, BookType.RBMK.ordinal()))", 91: "if(world.isRemote)",
                     92: "FMLNetworkHandler.openGui(player, MainRegistry.instance, 0, world, pos[0], pos[1], pos[2]);", 96: "} else {", 97: "return true;", 103: "return new int[] {3, 0, 0, 0, 2, 2};", 108: "return 1;",
                     113: "new int[] {3, 0, 0, 0, 2, 2},", 114: "new int[] {0, 0, 0, 1, 2, 2},", 119: "super.fillSpace(world, x, y, z, dir, o);", 121: "MultiblockHandlerXR.fillSpace(world, x + dir.offsetX * o , y, z + dir.offsetZ * o, new int[] {0, 0, 0, 1, 2, 2}, this, dir);",
                     126: "if(!MultiblockHandlerXR.checkSpace(world, x + dir.offsetX * o , y + dir.offsetY * o, z + dir.offsetZ * o, new int[] {0, 0, 0, 1, 2, 2}, x, y, z, dir))", 127: "return false;",
                     129: "return super.checkRequirement(world, x, y, z, dir, o);", 134: "if(tool != ToolType.SCREWDRIVER)", 135: "return false;", 136: "if(!world.isRemote) {", 137: "int[] pos = findCore(world, x, y, z);",
                     139: "if (tile instanceof TileEntityRBMKConsole) {", 140: "((TileEntityRBMKConsole) tile).rotate();", 143: "return true;"})
    order = [56, 58, 60, 68, 91, 96]
    fill, chk = ov.b["blk.fill"], ov.b["blk.check"]
    ck("V1.block", not m and order == sorted(order) and fill.index("super.fillSpace") < fill.index("MultiblockHandlerXR.fillSpace") and chk.index("MultiblockHandlerXR.checkSpace") < chk.index("super.checkRequirement"),
       "RBMKConsole.java:21-145: a BlockDummyable of iron material, hardness 3 / resistance 30, block entity only for meta >= offset, entity render (-1), not opaque; use: (not sneaking) markFBI, findCore, guide-book branch on the top face (:68-89), "
       "the client opens the GUI for the core (:91-92), sneaking returns true and does nothing; dimensions {3, 0, 0, 0, 2, 2}, offset 1, and a SECOND box {0, 0, 0, 1, 2, 2} at (x + dir.X * o, y, z + dir.Z * o) filled after super.fillSpace (:117-122) and "
       "checked BEFORE super.checkRequirement (:124-130); onScrew only SCREWDRIVER: server findCore + rotate(), returns true (:132-144)", m)
    # ---- ItemRBMKTool.java
    t = L["tool"]
    m = at_lines(t, {31: "Block b = world.getBlock(x, y, z);", 33: "if(b instanceof RBMKBase) {", 35: "int[] pos = ((BlockDummyable)b).findCore(world, x, y, z);", 37: "if(pos != null && !world.isRemote) {", 42: 'stack.stackTagCompound.setInteger("posX", pos[0]);',
                     43: 'stack.stackTagCompound.setInteger("posY", pos[1]);', 44: 'stack.stackTagCompound.setInteger("posZ", pos[2]);', 46: 'new ChatComponentTranslation(this.getUnlocalizedName() + ".linked").setChatStyle(new ChatStyle().setColor(EnumChatFormatting.YELLOW))',
                     49: "return true;", 53: "if(b == ModBlocks.rbmk_console && stack.hasTagCompound()) {", 55: "if(!world.isRemote) {", 57: "int[] pos = ((BlockDummyable)b).findCore(world, x, y, z);",
                     59: "TileEntityRBMKConsole console = (TileEntityRBMKConsole)world.getTileEntity(pos[0], pos[1], pos[2]);", 60: 'int tx = stack.stackTagCompound.getInteger("posX");', 61: 'int ty = stack.stackTagCompound.getInteger("posY");',
                     62: 'int tz = stack.stackTagCompound.getInteger("posZ");', 63: "console.setTarget(tx, ty, tz);", 64: 'new ChatComponentTranslation(this.getUnlocalizedName() + ".set").setChatStyle(new ChatStyle().setColor(EnumChatFormatting.YELLOW))',
                     67: "return true;", 70: "if(b == ModBlocks.rbmk_crane_console && stack.hasTagCompound()) {", 87: "if(b == ModBlocks.rbmk_display && stack.hasTagCompound()) {", 102: "return false;",
                     108: 'for(String s : I18nUtil.resolveKeyArray(this.getUnlocalizedName() + ".desc"))', 109: "list.add(EnumChatFormatting.YELLOW + s);",
                     116: 'multimap.put(SharedMonsterAttributes.attackDamage.getAttributeUnlocalizedName(), new AttributeModifier(field_111210_e, "Weapon modifier", 2, 0));'})
    order = [33, 53, 70, 87, 102]
    mi, mbl = L["mi"], L["mb"]
    ck("V1.tool", not m and order == sorted(order) and "rbmk_tool = new ItemRBMKTool().setUnlocalizedName(\"rbmk_tool\").setMaxStackSize(1).setCreativeTab(MainRegistry.consumableTab).setTextureName(RefStrings.MODID + \":rbmk_tool\");" in mi[3837],
       "ItemRBMKTool.java:26-118 and ModItems.java:3838: onItemUse: an RBMKBase block -> findCore; on the server stores the core's posX/posY/posZ in the stack NBT and tells the player item.rbmk_tool.linked in yellow, returns true (also on the client and "
       "also when the core was not found); the console with ANY NBT -> the console's core gets setTarget(posX, posY, posZ) + yellow .set, returns true; the crane console (:70-85) and rbmk_display (:87-100) branches are Goal 25/26; else false; "
       "tooltip = the .desc key split on $ in yellow; +2 attack damage weapon modifier; max stack size 1, consumable tab", m)
    m = at_lines(mbl, {2131: 'rbmk_console = new RBMKConsole().setBlockName("rbmk_console").setCreativeTab(MainRegistry.machineTab).setBlockTextureName(RefStrings.MODID + ":rbmk/rbmk_console");', 3125: "GameRegistry.registerBlock(rbmk_console, rbmk_console.getUnlocalizedName());"})
    m += at_lines(L["tm"], {418: 'put(TileEntityRBMKConsole.class, "tileentity_rbmk_console");'})
    ck("V1.registration", not m, "ModBlocks.java:2131, :3125 and TileMappings.java:418: rbmk_console is a machine-tab block with the texture rbmk/rbmk_console and the tile entity id tileentity_rbmk_console", m)
    # ---- GUIRBMKConsole.java
    g = L["gui"]
    m = at_lines(g, {34: 'textures/gui/reactors/gui_rbmk_console.png', 41: "private boolean[] selection = new boolean[15 * 15];", 42: "private boolean az5Lid = true;", 43: "private long lastPress = 0;", 51: "this.xSize = 244;", 52: "this.ySize = 172;",
                     63: "this.field = new GuiTextField(this.fontRendererObj, guiLeft + 9, guiTop + 84, 35, 9);", 64: "this.field.setTextColor(0x00ff00);", 65: "this.field.setDisabledTextColour(0x008000);", 66: "this.field.setEnableBackgroundDrawing(false);",
                     67: "this.field.setMaxStringLength(3);", 79: "if(guiLeft + 86 <= mouseX && guiLeft + 86 + 150 > mouseX && guiTop + 11 < mouseY && guiTop + 11 + 10150 >= mouseY) {", 80: "int index = ((mouseX - bX - guiLeft) / size + (mouseY - bY - guiTop) / size * 15);",
                     82: "if(index > 0 && index < console.columns.length) {", 88: "list.add(col.type.toString());", 89: "list.addAll(col.getFancyStats());",
                     95: 'guiLeft + 61, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ "Select all control rods" }', 96: 'guiLeft + 72, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ "Deselect all" }',
                     100: "int id = i * 2 + j + 1;", 101: 'guiLeft + 6 + 40 * j, guiTop + 8 + 21 * i, 18, 18, mouseX, mouseY, new String[]{ EnumChatFormatting.YELLOW + I18nUtil.resolveKey("rbmk.console." + console.screens[id - 1].type.name().toLowerCase(Locale.US), id) }',
                     102: 'guiLeft + 24 + 40 * j, guiTop + 8 + 21 * i, 18, 18, mouseX, mouseY, new String[]{ I18nUtil.resolveKey("rbmk.console.assign", id) }',
                     106: 'guiLeft + 6, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ EnumChatFormatting.RED + "Left click: Select red group", EnumChatFormatting.RED + "Right click: Assign red group" }',
                     107: 'guiLeft + 17, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ EnumChatFormatting.YELLOW + "Left click: Select yellow group", EnumChatFormatting.YELLOW + "Right click: Assign yellow group" }',
                     108: 'guiLeft + 28, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ EnumChatFormatting.GREEN + "Left click: Select green group", EnumChatFormatting.GREEN + "Right click: Assign green group" }',
                     109: 'guiLeft + 39, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ EnumChatFormatting.BLUE + "Left click: Select blue group", EnumChatFormatting.BLUE + "Right click: Assign blue group" }',
                     110: 'guiLeft + 50, guiTop + 70, 10, 10, mouseX, mouseY, new String[]{ EnumChatFormatting.LIGHT_PURPLE + "Left click: Select purple group", EnumChatFormatting.LIGHT_PURPLE + "Right click: Assign purple group" }',
                     111: 'guiLeft + 70, guiTop + 82, 12, 12, mouseX, mouseY, new String[]{ "Cycle steam channel compressor setting" }',
                     116: "if(x <= mouseX && x + width > mouseX && y < mouseY && y + height >= mouseY)"})
    ck("V1.gui-layout-tooltips", not m, "GUIRBMKConsole.java:34-118: 244 x 172, gui_rbmk_console.png, selection[225], az5Lid true, lastPress 0; the field at (9, 84) 35 x 9, green 0x00ff00 / disabled 0x008000, no background, 3 characters; the grid hover (BUGGY: `+ 10150` and `index > 0`, :79 and :82) shows "
       "[type.toString(), getFancyStats]; tooltips (61,70,10,10) select all, (72,70) deselect all, the six screen buttons (6 + 40j, 8 + 21i, 18 x 18, id = i * 2 + j + 1) yellow rbmk.console.<type lower>(id) and (24 + 40j, ...) rbmk.console.assign(id), the five colour buttons "
       "(6 + 11k, 70, 10 x 10) with two coloured lines and (70, 82, 12 x 12) the compressor tip; rectangle test x <= mx < x + w && y < my <= y + h", m)
    m = at_lines(g, {133: "if(guiLeft + 86 <= mouseX && guiLeft + 86 + 150 > mouseX && guiTop + 11 < mouseY && guiTop + 11 + 150 >= mouseY) {", 135: "int index = ((mouseX - bX - guiLeft) / size + (mouseY - bY - guiTop) / size * 15);",
                     137: "if(index >= 0 && index < selection.length && console.columns[index] != null) {", 140: "0.75F + (this.selection[index] ? 0.25F : 0.0F)", 141: "return;",
                     146: "if(guiLeft + 72 <= mouseX && guiLeft + 72 + 10 > mouseX && guiTop + 70 < mouseY && guiTop + 70 + 10 >= mouseY) {", 148: '"gui.button.press"), 0.5F)', 153: "if(guiLeft + 61 <= mouseX && guiLeft + 61 + 10 > mouseX && guiTop + 70 < mouseY && guiTop + 70 + 10 >= mouseY) {",
                     158: "if(console.columns[j] != null && console.columns[j].type == ColumnType.CONTROL) {", 162: '"gui.button.press"), 1.5F)',
                     167: "if(guiLeft + 70 <= mouseX && guiLeft + 70 + 12 > mouseX && guiTop + 82 < mouseY && guiTop + 82 + 12 >= mouseY) {", 169: 'control.setBoolean("compressor", true);',
                     172: "if(console.columns[j] != null && console.columns[j].type == ColumnType.BOILER && this.selection[j]) {", 178: 'control.setIntArray("cols", cols);',
                     179: "PacketDispatcher.wrapper.sendToServer(new NBTControlPacket(control, console.xCoord, console.yCoord, console.zCoord));", 180: '"gui.button.press"), 1F)',
                     184: "for(int k = 0; k < 5; k++) {", 186: "if(guiLeft + 6 + k * 11 <= mouseX && guiLeft + 6 + k * 11 + 10 > mouseX && guiTop + 70 < mouseY && guiTop + 70 + 10 >= mouseY) {",
                     188: "if(key == LEFT_CLICK) {", 193: 'console.columns[j].type == ColumnType.CONTROL && console.columns[j].data.getShort("color") == k', 199: "if(key == RIGTH_CLICK) {",
                     201: 'control.setByte("assignColor", (byte) k);', 204: "console.columns[j].type == ColumnType.CONTROL && this.selection[j]", 214: '"gui.button.press"), 0.8F + k * 0.1F)', 215: "return;"})
    order = [133, 146, 153, 167, 184]
    ck("V1.gui-clicks-1", not m and order == sorted(order) and "return" not in "".join(g[166:182]),
       "GUIRBMKConsole.java:121-217 mouseClicked in this order: the field, grid toggle (cells (86 + 10c, 11 + 10r) in the 150 x 150 box, only non-null columns, pitch 0.75 + 0.25 when selected, return), clear (72,70,10 x 10) pitch 0.5, select all CONTROL (61,70) pitch 1.5, "
       "compressor (70,82,12 x 12): {compressor: true, cols: selected BOILER indices} pitch 1 and NO return (falls through, :166-181), the five colour buttons (6 + 11k, 70, 10 x 10): LEFT selects the CONTROL columns whose short `color` == k, RIGHT sends "
       "{assignColor: (byte) k, cols: selected CONTROL indices}, pitch 0.8 + 0.1k, return", m)
    m = at_lines(g, {220: "if(guiLeft + 30 <= mouseX && guiLeft + 30 + 28 > mouseX && guiTop + 138 < mouseY && guiTop + 138 + 28 >= mouseY) {", 222: "if(az5Lid) {", 223: "az5Lid = false;", 224: '"hbm:block.rbmk_az5_cover"), 0.5F)',
                     225: "} else if(lastPress + 3000 < System.currentTimeMillis()) {", 226: '"hbm:block.shutdown"), 1)', 227: "lastPress = System.currentTimeMillis();", 230: 'control.setDouble("level", 0);',
                     233: "if(console.columns[j] != null && console.columns[j].type == ColumnType.CONTROL)", 234: 'control.setInteger("sel_" + j, j);', 237: "PacketDispatcher.wrapper.sendToServer(new NBTControlPacket(control, console.xCoord, console.yCoord, console.zCoord));",
                     238: '"gui.button.press"), 1F)', 240: "return;", 244: "if(guiLeft + 48 <= mouseX && guiLeft + 48 + 12 > mouseX && guiTop + 82 < mouseY && guiTop + 82 + 12 >= mouseY) {", 248: "if(NumberUtils.isNumber(field.getText())) {",
                     249: "int j = (int)MathHelper.clamp_double(Double.parseDouble(field.getText()), 0, 100);", 250: 'field.setText(j + "");', 251: "level = j * 0.01D;", 253: "return;", 257: 'control.setDouble("level", level);',
                     261: 'control.setInteger("sel_" + j, j);', 265: '"gui.button.press"), 1F)', 275: "if(guiLeft + 6 + 40 * k <= mouseX && guiLeft + 6 + 40 * k + 18 > mouseX && guiTop + 8 + 21 * j < mouseY && guiTop + 8 + 21 * j + 18 >= mouseY) {",
                     273: "int id = j * 2 + k;", 277: 'control.setByte("toggle", (byte) id);', 279: '"gui.button.press"), 0.5F)', 283: "if(guiLeft + 24 + 40 * k <= mouseX && guiLeft + 24 + 40 * k + 18 > mouseX && guiTop + 8 + 21 * j < mouseY && guiTop + 8 + 21 * j + 18 >= mouseY) {",
                     286: 'control.setByte("id", (byte) id);', 290: 'control.setBoolean("s" + s, true);', 295: '"gui.button.press"), 0.75F)'})
    order = [220, 222, 225, 244, 275, 283]
    ck("V1.gui-clicks-2", not m and order == sorted(order),
       "GUIRBMKConsole.java:219-299: AZ-5 (30,138,28 x 28): the first click opens the lid (hbm:block.rbmk_az5_cover, pitch 0.5), later clicks after 3000 ms play hbm:block.shutdown LOCALLY (pitch 1), set lastPress and send {level: 0, sel_j: j for every CONTROL column} "
       "(the AZ-5 packet) + button sound 1, return; save (48,82,12 x 12): a number is clamped to an int 0..100, written back, level = j * 0.01, {level, sel_i for each selected} sent (not a number: return without sending), no return afterwards; screen buttons "
       "(6 + 40k, 8 + 21j, 18 x 18) {toggle: (byte) id} pitch 0.5 (return) and (24 + 40k, ...) {id: (byte) id, s<i>: true for each selected} pitch 0.75 (return), id = 2j + k", m)
    m = at_lines(g, {306: "drawTexturedModalRect(guiLeft, guiTop, 0, 0, xSize, ySize);", 309: "drawTexturedModalRect(guiLeft + 30, guiTop + 138, 228, 172, 28, 28);", 315: "this.console.screens[id].type.offset, 238, 18, 18);", 330: "int x = bX + size * (i % 15);",
                     331: "int y = bY + size * (i / 15);", 333: "int tX = col.type.offset;", 334: "int tY = 172;", 336: "drawTexturedModalRect(guiLeft + x, guiTop + y, tX, tY, size, size);",
                     338: 'int h = Math.min((int)Math.ceil((col.data.getDouble("heat") - 20) * 10 / col.data.getDouble("maxHeat")), 10);', 339: "drawTexturedModalRect(guiLeft + x, guiTop + y + size - h, 0, 192 - h, 10, h);",
                     349: "case CONTROL:", 350: 'int color = col.data.getShort("color");', 351: "if(color > -1)", 352: "drawTexturedModalRect(guiLeft + x, guiTop + y, color * size, 202, 10, 10);", 354: "case CONTROL_AUTO:",
                     355: 'int fr = 8 - (int)Math.ceil((col.data.getDouble("level") * 8));', 356: "drawTexturedModalRect(guiLeft + x + 4, guiTop + y + 1, 24, 183, 2, fr);", 357: "break;",
                     361: 'if(col.data.hasKey("c_heat")) {', 362: 'int fh = (int)Math.ceil((col.data.getDouble("c_heat") - 20) * 8 / col.data.getDouble("c_maxHeat"));', 364: "drawTexturedModalRect(guiLeft + x + 1, guiTop + y + size - fh - 1, 11, 191 - fh, 2, fh);",
                     366: 'int fe = (int)Math.ceil((col.data.getDouble("enrichment")) * 8);', 368: "drawTexturedModalRect(guiLeft + x + 4, guiTop + y + size - fe - 1, 14, 191 - fe, 2, fe);",
                     370: 'int fx = (int)Math.ceil((col.data.getDouble("xenon")) * 8 / 100);', 372: "drawTexturedModalRect(guiLeft + x + 7, guiTop + y + size - fx - 1, 17, 191 - fx, 2, fx);",
                     377: 'int fw = (int)Math.ceil((col.data.getInteger("water")) * 8 / col.data.getDouble("maxWater"));', 378: "drawTexturedModalRect(guiLeft + x + 1, guiTop + y + size - fw - 1, 41, 191 - fw, 3, fw);",
                     379: 'int fs = (int)Math.ceil((col.data.getInteger("steam")) * 8 / col.data.getDouble("maxSteam"));', 380: "drawTexturedModalRect(guiLeft + x + 6, guiTop + y + size - fs - 1, 46, 191 - fs, 3, fs);",
                     382: "if(col.data.getShort(\"type\") == Fluids.STEAM.ordinal())", 383: "drawTexturedModalRect(guiLeft + x + 4, guiTop + y + 1, 44, 183, 2, 2);", 385: "drawTexturedModalRect(guiLeft + x + 4, guiTop + y + 3, 44, 185, 2, 2);",
                     387: "drawTexturedModalRect(guiLeft + x + 4, guiTop + y + 5, 44, 187, 2, 2);", 389: "drawTexturedModalRect(guiLeft + x + 4, guiTop + y + 7, 44, 189, 2, 2);",
                     394: 'int cc = (int)Math.ceil((col.data.getInteger("water")) * 8 / col.data.getDouble("maxWater"));', 395: "drawTexturedModalRect(guiLeft + x + 1, guiTop + y + size - cc - 1, 131, 191 - cc, 3, cc);",
                     396: 'int hc = (int)Math.ceil((col.data.getInteger("steam")) * 8 / col.data.getDouble("maxSteam"));', 397: "drawTexturedModalRect(guiLeft + x + 6, guiTop + y + size - hc - 1, 136, 191 - hc, 3, hc);",
                     401: "if(this.selection[i])", 402: "drawTexturedModalRect(guiLeft + x, guiTop + y, 0, 192, 10, 10);"})
    bg = ov.b["gui.bg"]
    ck("V1.gui-draw-grid", not m and "caseCONTROL:" in bg and bg.index("caseCONTROL:") < bg.index("caseCONTROL_AUTO:") and "intcolor=col.data.getShort(\"color\");if(color>-1)" in bg
       and "break;caseCONTROL_AUTO:" not in bg,
       "GUIRBMKConsole.java:303-403 background: the 244 x 172 panel, the AZ-5 lid (30,138) from (228,172) 28 x 28 while az5Lid, the six screen icons (6 + 40k, 8 + 21j) from (type.offset, 238) 18 x 18, then per non-null column at (86 + 10(i % 15), 11 + 10(i / 15)): the "
       "tile from (type.offset, 172), the heat bar h = min(ceil((heat - 20) * 10 / maxHeat), 10), CONTROL colour overlay from (10 * color, 202) when color > -1 and FALLING THROUGH (no break) to the CONTROL_AUTO rod bar fr = 8 - ceil(level * 8) at (x + 4, y + 1) from (24, 183) "
       "2 x fr; FUEL/FUEL_SIM three bars only with c_heat (x + 1/4/7 from u 11/14/17, ceil, max 8); BOILER water (41) and steam (46) bars and the steam-type dot from (44, 183/185/187/189) at y + 1/3/5/7 for STEAM/HOTSTEAM/SUPERHOTSTEAM/ULTRAHOTSTEAM; "
       "HEATEX bars (131, 136); the selection overlay from (0, 192)", m)
    m = at_lines(g, {405: "int highest = Integer.MIN_VALUE;", 406: "int lowest = Integer.MAX_VALUE;", 417: "tess.setColorOpaque_I(0x00ff00);", 418: "int range = highest - lowest;", 419: "for(int i = 0; i < console.fluxBuffer.length - 1; i++) {",
                     420: "for(int j = 0; j < 2; j++) {", 421: "int k = i + j;", 423: "double x = guiLeft + 7 + k * 74D / console.fluxBuffer.length;", 424: "double y = guiTop + 127 - (flux - lowest) * 24D / Math.max(range, 1);", 414: "GL11.glLineWidth(2F);",
                     432: "double scale = 0.5D;", 434: "(int) ((guiLeft + 8) / scale), (int) ((guiTop + 98) / scale), 0x00ff00);", 435: "(int) ((guiLeft + 80 - this.fontRendererObj.getStringWidth(highest + \"\") * scale) / scale), (int) ((guiTop + 98) / scale), 0x00ff00);",
                     436: "(int) ((guiLeft + 8) / scale), (int) ((guiTop + 133 - this.fontRendererObj.FONT_HEIGHT * scale) / scale), 0x00ff00);", 437: "(int) ((guiLeft + 80 - this.fontRendererObj.getStringWidth(lowest + \"\") * scale) / scale), (int) ((guiTop + 133 - this.fontRendererObj.FONT_HEIGHT * scale) / scale), 0x00ff00);",
                     446: "if(this.field.textboxKeyTyped(c, i))", 449: "if(i == 1 || i == this.mc.gameSettings.keyBindInventory.getKeyCode()) {", 450: "this.mc.thePlayer.closeScreen();", 458: "public boolean doesGuiPauseGame() {", 459: "return false;"})
    ck("V1.gui-graph-keys", not m, "GUIRBMKConsole.java:405-466: the flux graph: highest/lowest of the buffer, GL_LINES width 2 green (0x00ff00): for i in 0..58, segment points k = i and i + 1 at x = guiLeft + 7 + k * 74 / 60, y = guiTop + 127 - (flux - lowest) * 24 / max(range, 1); "
       "labels at scale 0.5: highest at (8, 98) and right-aligned to x 80, lowest at (8, 133 - fontHeight * 0.5) and right-aligned, green; keys: the field first, ESC or the inventory key closes the screen; the screen does not pause the game", m)
    # ---- RenderRBMKConsole.java
    r = L["ren"]
    m = at_lines(r, {26: "GL11.glTranslatef((float)x + 0.5F, (float)y, (float)z + 0.5F);", 32: "case 2: GL11.glRotatef(90, 0F, 1F, 0F); break;", 33: "case 4: GL11.glRotatef(180, 0F, 1F, 0F); break;", 34: "case 3: GL11.glRotatef(270, 0F, 1F, 0F); break;",
                     35: "case 5: GL11.glRotatef(0, 0F, 1F, 0F); break;", 38: "GL11.glTranslated(0.5, 0, 0);", 41: "bindTexture(ResourceManager.rbmk_console_tex);", 42: "ResourceManager.rbmk_console.renderAll();", 50: "tess.setBrightness(240);", 51: "tess.setNormal(1, 0, 0);",
                     60: "double kx = -0.3725D;", 61: "double ky = -(i / 15) * 0.125 + 3.625;", 62: "double kz = -(i % 15) * 0.125 + 0.125D * 7;", 64: 'if(col.data.hasKey("color") && col.data.getByte("color") >= 0) {',
                     66: "if(color == 0) tess.setColorOpaque_I(0xFF0000);", 67: "if(color == 1) tess.setColorOpaque_I(0xFFFF00);", 68: "if(color == 2) tess.setColorOpaque_I(0x008000);", 69: "if(color == 3) tess.setColorOpaque_I(0x0000FF);",
                     70: "if(color == 4) tess.setColorOpaque_I(0x8000FF);", 72: 'double heat = col.data.getDouble("heat") / col.data.getDouble("maxHeat");', 73: "double color = 0.65D + (i % 2) * 0.05D;",
                     74: "tess.setColorOpaque_F((float) (color + ((1 - color) * heat)), (float) color, (float) color);", 77: 'if(col.data.getByte("indicator") > 0) tess.setColorOpaque_F(1F, 1F, 0F);',
                     83: 'drawFuel(tess, kx + 0.01, ky, kz, col.data.getDouble("enrichment")); break;', 84: 'drawControl(tess, kx + 0.01, ky, kz, col.data.getDouble("level")); break;',
                     85: 'drawControlAuto(tess, kx + 0.01, ky, kz, col.data.getDouble("level")); break;', 94: "GL11.glTranslatef(-0.42F, 3.5F, 1.75F);", 95: "GL11.glDepthMask(false);",
                     102: "if(i % 2 == 1)", 103: "GL11.glTranslatef(0, 0, 1.75F * -2);", 105: "GL11.glTranslatef(0, -0.75F * (i / 2), 0);", 112: 'String[] parts = text.split("=");', 114: "if(parts.length == 2) {", 115: "text = I18nUtil.resolveKey(parts[0], parts[1]);",
                     121: "float f3 = Math.min(0.03F, 0.8F / Math.max(width, 1));", 122: "GL11.glScalef(f3, -f3, f3);", 124: "GL11.glRotatef(90, 0, 1, 0);", 126: "font.drawString(text, - width / 2, - height / 2, 0x00ff00);",
                     139: "double width = 0.0625D * 0.75;", 148: "this.drawDot(tess, x, y, z, 0F, 0.25F + (float) (enrichment * 0.75D), 0F);", 152: "this.drawDot(tess, x, y, z, (float) level, (float) level, 0F);", 156: "this.drawDot(tess, x, y, z, (float) level, 0F, (float) level);",
                     161: "double width = 0.03125D;", 162: "double edge = 0.022097D;"})
    dot = ov.b["ren.dot"]
    col = ov.b["ren.column"]
    ck("V1.render", not m and dot.count("tess.addVertex(") == 12 and col.count("tess.addVertex(") == 4,
       "RenderRBMKConsole.java:21-182: translate (x + 0.5, y, z + 0.5); rotate by metadata - offset: 2 -> 90, 4 -> 180, 3 -> 270, 5 -> 0 about +Y; translate (0.5, 0, 0); the whole OBJ with rbmk_console_tex, smooth shading; the columns as full-bright (240) quads, "
       "normal +X, at x -0.3725, y = -(i / 15) * 0.125 + 3.625, z = -(i % 15) * 0.125 + 0.875 with half-width 0.0625 * 0.75 in the YZ plane; colour: a byte `color` >= 0 -> FF0000 / FFFF00 / 008000 / 0000FF / 8000FF, else heat/maxHeat blended from 0.65 + 0.05 * (i % 2); "
       "indicator > 0 -> yellow; dots at x + 0.01 (width 0.03125, edge 0.022097, 12 vertices): FUEL/FUEL_SIM (0, 0.25 + 0.75 * enrichment, 0), CONTROL (level, level, 0), CONTROL_AUTO (level, 0, level); the six screens: translate (-0.42, 3.5, 1.75), no depth write, "
       "odd screens z - 3.5, y - 0.75 * (i / 2), `key=value` -> I18n(key, value), scale min(0.03, 0.8 / max(width, 1)) as (f, -f, f), rotate 90 about +Y, centred, colour 0x00ff00", m)
    # ---- resources and recipes
    rm = L["rm"]
    m = at_lines(rm, {1683: 'public static final HFRWavefrontObjectVBO rbmk_console = new HFRWavefrontObject(new ResourceLocation(RefStrings.MODID, "models/rbmk/rbmk_console.obj")).asVBO();',
                      1694: 'public static final ResourceLocation rbmk_console_tex = new ResourceLocation(RefStrings.MODID, "textures/models/machines/rbmk_control.png");'})
    ck("V1.resource-manager", not m, "ResourceManager.java:1683, :1694: rbmk_console = models/rbmk/rbmk_console.obj (VBO) and rbmk_console_tex = textures/models/machines/rbmk_control.png (the console's model texture)", m)
    cm = L["cm"]
    row = parse_cm_row(cm[988])
    tr = L["tr"]
    trow = parse_tool_row(tr[132])
    inp.console_row, inp.tool_row = row, trow
    enable = at_lines(cm, {987: "if(!GeneralConfig.enable528) {", 996: "}"})
    ck("V1.recipes", row == ("rbmk_console", 1, ["BBB", "DGD", "DCD"], {"B": "B.ingot()", "D": "ModBlocks.deco_rbmk", "G": "KEY_ANYPANE", "C": "DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ANALOG)"})
       and trow == ("rbmk_tool", 1, [" A ", " IA", "I  "], {"A": "PB.ingot()", "I": "IRON.ingot()"}) and not enable and "else" not in "".join(cm[987:996]),
       "CraftingManager.java:989 rbmk_console BBB / DGD / DCD (B = B.ingot() = boron, D = deco_rbmk, G = KEY_ANYPANE, C = analog circuit) inside the !enable528 branch (the default configuration); ToolRecipes.java:133 rbmk_tool ` A `, ` IA`, `I  ` "
       "(A = PB.ingot() lead, I = IRON.ingot()); no anvil row exists for either", (row, trow, enable))
    snd = inp.ol["sounds"]
    ck("V1.sound", '"block.shutdown": {"category": "block", "sounds": [{"name": "block/shutdown", "stream": true}]}' in snd[6] and "rbmk_az5_cover" in "".join(snd),
       "sounds.json:7 block.shutdown: category block, one sound block/shutdown with stream true (the AZ-5 sound the GUI plays locally)", snd[6])
    # ---- language
    en, zh = inp.o_en, inp.o_zh
    bad = []
    for neo, orig, le, lz in UP:
        if not (len(en.get(orig, [])) == 1 and len(zh.get(orig, [])) == 1 and (en[orig][0][1], zh[orig][0][1]) == (le, lz)):
            bad.append((orig, en.get(orig), zh.get(orig)))
    ck("V1.lang", not bad and len(UP) == 23 and len(set(u[0] for u in UP)) == 23 and not [k for k in inp.o_en if "rbmkConsole" in k] and not [k for k in inp.o_zh if "rbmkConsole" in k],
       "the 23 upstream keys (block name, 4 item keys, rbmk.heat, 7 console, moderated, 4 rod, 5 screen) sit once each at the cited en_US.lang / zh_CN.lang lines; the original has no container.rbmkConsole key (the GUI has no title)", bad[:3])
    ck("V1.lang-existing-24d", all(len(en.get(k, [])) == 1 and len(zh.get(k, [])) == 1 for k in UP_EXISTING_24D), "the nine keys Goal24D already imported (rbmk.boiler.*, rbmk.control.*) exist once in the original and are not part of this batch", [k for k in UP_EXISTING_24D if k not in en])
    ck("V1.zh-assign-no-placeholder", "%s" not in zh["rbmk.console.assign"][0][0] and "%s" in en["rbmk.console.assign"][0][0], "zh_CN.lang:4296 rbmk.console.assign has no %s while the English has `#%s` (upstream text, kept as is)", (en["rbmk.console.assign"], zh["rbmk.console.assign"]))
    gl = inp.ol["gui"]
    bad = []
    for k, (e, _z, line) in LOCAL.items():
        if k.startswith("rbmk.console.type."):
            continue
        if e not in gl[line - 1]:
            bad.append((k, line, e))
    types_ok = list(enum_members(inp.o["con"], "ColumnType")) == [e for _, e, _ in TYPES]
    ck("V1.local-texts", not bad and types_ok and len(LOCAL) == 27, "the 27 local English texts are the hard-coded strings of GUIRBMKConsole (:95-96 select/deselect all, :106-110 the five group tips, :111 the compressor tip) and the 14 enum names shown as the type name (:88, col.type.toString())", bad[:3])


# ---------------------------------------------------------------- V2 console block entity against V1

def v2_console(ck, inp, st):
    ov = need_ov(inp)
    text = lf(st.text(CON))
    code = code_of(text)
    ocode = code_of(inp.o["con"])
    nb = lambda sig: body(text, sig)  # noqa: E731
    # ---- fields, constructor, constants
    fields_same = ["publicstaticfinalintfluxDisplayBuffer=60;", "publicint[]fluxBuffer=newint[fluxDisplayBuffer];", "publicRBMKColumn[]columns=newRBMKColumn[15*15];", "publicRBMKScreen[]screens=newRBMKScreen[6];"]
    fields_priv = ["inttargetX;", "inttargetY;", "inttargetZ;", "byterotation;"]
    miss = [f for f in fields_same if f not in ocode or f not in code] + [f for f in fields_priv if "private" + f not in ocode or "public" + f not in code]
    ctor_o = "super(0);for(inti=0;i<screens.length;i++){screens[i]=newRBMKScreen();}"
    ctor_n = "super(NtmBlockEntityTypes.RBMK_CONSOLE.get(),pos,state,0);for(inti=0;i<screens.length;i++){screens[i]=newRBMKScreen();}"
    ck("V2.fields-constants", not miss and ctor_o in ocode and ctor_n in code and "publicint[]getSlotsForFace(Directiondirection){returnnewint[0];}" in code,
       "TileEntityRBMKConsole.java:43-61: targetX/Y/Z and the byte rotation (public in NEO), fluxDisplayBuffer 60 with a 60-entry int[] fluxBuffer, 15 * 15 = 225 columns, six screens created in the constructor, zero slots (super(..., 0); no face exposes a slot)", (miss, ctor_n in code))
    # ---- update
    exp = derive(ov.b["con.update"], [('this.worldObj.theProfiler.startSection("rbmkConsole_rescan");', ""), ("this.worldObj.theProfiler.endSection();", ""), ("this.worldObj.getTotalWorldTime()", "this.level.getGameTime()")])
    head = "if(!worldObj.isRemote){"
    assert exp.startswith(head) and exp.endswith("}")
    eq(ck, "V2.update", "updateEntity is the original tick (:70-85): server only; on every world tick divisible by 10 rescan() then prepareScreenInfo(); networkPackNT(50) on EVERY tick after that block (the profiler calls are not ported)",
       "if(this.level==null||this.level.isClientSide)return;" + exp[len(head):-1], nb("public void updateEntity()"))
    # ---- rescan and the column lookup
    exp = derive(ov.b["con.rescan"], [
        ("intrx=getXFromIndex(index);intrz=getZFromIndex(index);TileEntityte=Compat.getTileStandard(worldObj,targetX+rx,targetY,targetZ+rz);", "BlockEntityte=this.getColumnEntity(index);"),
        ("if(teinstanceofTileEntityRBMKBase){TileEntityRBMKBaserbmk=(TileEntityRBMKBase)te;", "if(teinstanceofRBMKBaseBlockEntityrbmk){"),
        (".setDouble(", ".putDouble("), ('.setByte("indicator",(byte)rbmk.craneIndicator);', '.putByte("indicator",(byte)0);'), (".setBoolean(", ".putBoolean("),
        ("if(teinstanceofTileEntityRBMKRod){TileEntityRBMKRodfuel=(TileEntityRBMKRod)te;", "if(teinstanceofRBMKRodBlockEntityfuel){")])
    eq(ck, "V2.rescan", "rescan is the original (:87-122): per index the tile at the rotated position becomes a column of (getConsoleType, getNBTForConsole) + heat, maxHeat, indicator and moderated (only when true); rods add lastFluxQuantity to the flux; "
       "anything else is null; the 60-entry history shifts left and gets (int) flux. NEO writes indicator 0: the original reads the crane console's craneIndicator (Goal 25)", exp, nb("public void rescan()"))
    compat = lf(otext(O + "util/Compat.java"))
    ck("V2.column-lookup", "if(!isPositionLoaded(world, x, z)) return null;" in compat and "return world.getTileEntity(x, y, z);" in compat
       and nb("private BlockEntity getColumnEntity(int index)") == "BlockPospos=newBlockPos(targetX+getXFromIndex(index),targetY,targetZ+getZFromIndex(index));returnthis.level.isLoaded(pos)?this.level.getBlockEntity(pos):null;",
       "the column lookup is Compat.getTileStandard (Compat.java:265-268: an unloaded position reads null, nothing is loaded): NEO uses level.isLoaded(pos) ? getBlockEntity(pos) : null at (targetX + x, targetY, targetZ + z)")
    # ---- prepareScreenInfo
    exp = derive(ov.b["con.prepare"], [
        ("for(Integeri:screen.columns){RBMKColumncol=this.columns[i];", "for(inti:screen.columns){if(i<0||i>=this.columns.length)continue;RBMKColumncol=this.columns[i];"), (".hasKey(", ".contains("),
        ("*100;}break;}}", "*100;}break;default:break;}}"), ('+"%";break;}screen.display=text;', '+"%";break;default:break;}screen.display=text;')])
    eq(ck, "V2.prepare", "prepareScreenInfo is the original (:125-188): NONE -> null; COL_TEMP heat, FUEL_DEPLETION 100 - enrichment * 100, FUEL_POISON xenon, FUEL_TEMP c_heat, ROD_EXTRACTION level * 100 (each counted only when the key exists), "
       "result = value / (double) count (NaN when nothing counts, shown as 0.0), text = ((int)(result * 10)) / 10D, the five prefixes with their units; NEO skips an index outside the grid (an edited save) and adds the default branches",
       exp, nb("public void prepareScreenInfo()"))
    # ---- serialize / deserialize
    ser, des = nb("public void serialize(RegistryFriendlyByteBuf buf)"), nb("public void deserialize(RegistryFriendlyByteBuf buf)")
    oser, odes = ov.b["con.serialize"], ov.b["con.deserialize"]
    ck("V2.wire-layout", wire_ops(ser) == wire_ops(oser) == list("ZBBNASZB") and wire_ops(des) == wire_ops(odes) == list("ZBNASB"),
       "serialize/deserialize keep the original wire layout (:190-249): full packet = boolean true, per column a byte (-1 or the ordinal) + the NBT, the int array, six nullable strings; short packet = boolean false + six screen-type bytes; "
       "deserialize reads them in that order (NEO: NBT through FriendlyByteBuf, VarInt array, presence boolean + UTF string)", (wire_ops(ser), wire_ops(oser), wire_ops(des), wire_ops(odes)))
    ck("V2.wire-switch", "this.worldObj.getTotalWorldTime()%10==0" in oser and "if(this.level!=null&&this.level.getGameTime()%10==0){buf.writeBoolean(true);" in ser and "}else{buf.writeBoolean(false);" in ser
       and "if(column==null||column.type==null){buf.writeByte(-1);}else{buf.writeByte((byte)column.type.ordinal());buf.writeNbt(column.data);}" in ser and "buf.writeByte((byte)screen.type.ordinal());" in ser
       and "if(buf.readBoolean()){" in des and "byteordinal=buf.readByte();if(ordinal<0){this.columns[i]=null;}else{" in des and "CompoundTagdata=buf.readNbt();this.columns[i]=ordinal<types.length?newRBMKColumn(types[ordinal],data):null;" in des
       and "this.fluxBuffer=buf.readVarIntArray(fluxDisplayBuffer);" in des and "screen.display=buf.readBoolean()?buf.readUtf():null;" in des and "screen.type=screenTypeOf(buf.readByte());" in des,
       "the full/short switch is the world time % 10 at serialization (:194), column -1 = no column, the compound follows every non-negative ordinal; NEO-only client guards: an ordinal beyond the types reads as no column (the compound is still consumed), "
       "the flux history is read with a maximum of 60 entries, a screen type outside 0..5 reads as NONE")
    ck("V2.screen-type-guard", nb("private static ScreenType screenTypeOf(int ordinal)") == "returnordinal>=0&&ordinal<ScreenType.values().length?ScreenType.values()[ordinal]:ScreenType.NONE;",
       "screenTypeOf maps an out-of-range byte to NONE (used by deserialize and loadAdditional)")
    # ---- permission
    exp = "BlockPospos=this.getBlockPos();return" + derive(ov.b["con.perm"], [("return", ""), ("Vec3.createVectorHelper(", "newVec3("), ("xCoord-player.posX", "pos.getX()-player.getX()"), ("yCoord-player.posY", "pos.getY()-player.getY()"),
                                                                              ("zCoord-player.posZ", "pos.getZ()-player.getZ()"), (".lengthVector()", ".length()")])
    eq(ck, "V2.permission", "hasPermission is the original (:251-254): the distance from the block corner (x, y, z) to the player is below 20", exp, nb("public boolean hasPermission(Player player)"))
    # ---- receiveControl
    rc = nb("public void receiveControl(CompoundTag data)")
    sel = nb("private int[] selectedColumns(CompoundTag data)")
    frags = ['if(data.contains("level")){', "doubletarget=data.getDouble(\"level\");", "if(Double.isFinite(target)){", "target=Mth.clamp(target,0,1);", "intprocessed=0;", "for(Stringkey:data.getAllKeys()){", 'if(key.startsWith("sel_")){',
             "if(processed++>=this.columns.length)break;", "intindex=data.getInt(key);", "if(index<0||index>=this.columns.length)continue;", "if(this.getColumnEntity(index)instanceofRBMKControlManualBlockEntityrod){",
             "rod.startingLevel=rod.level;", "rod.setTarget(target);", "rod.setChanged();",
             'if(data.contains("toggle")){', 'intslot=data.getByte("toggle");', "if(slot>=0&&slot<this.screens.length){", "intnext=this.screens[slot].type.ordinal()+1;",
             "ScreenTypetype=ScreenType.values()[next%ScreenType.values().length];", "this.screens[slot].type=type;", "this.setChanged();",
             'if(data.contains("id")){', 'intslot=data.getByte("id");', "if(slot>=0&&slot<this.screens.length){", "for(inti=0;i<15*15;i++){", 'if(data.getBoolean("s"+i)){', "list.add(i);",
             "this.screens[slot].columns=list.stream().mapToInt(Integer::intValue).toArray();", "this.setChanged();",
             'if(data.contains("assignColor")){', 'intcolor=data.getByte("assignColor");', "RBMKColorgroup=RBMKColor.values()[Math.abs(color%RBMKColor.values().length)];", "for(inti:selectedColumns(data)){",
             "if(this.getColumnEntity(i)instanceofRBMKControlManualBlockEntityrod){", "rod.color=group;", "rod.setChanged();",
             'if(data.contains("compressor")){', "for(inti:selectedColumns(data)){", "if(this.getColumnEntity(i)instanceofRBMKBoilerBlockEntityboiler){", "boiler.cyceCompressor();"]
    orc = ov.b["con.receive"]
    olits, nlits = set(re.findall(r'"([^"]*)"', orc)), set(re.findall(r'"([^"]*)"', rc + sel))
    ck("V2.receive-control", not ordered_missing(rc, frags) and olits == nlits == {"level", "sel_", "toggle", "id", "s", "assignColor", "cols", "compressor"} and "RBMKControlAutoBlockEntity" not in rc + sel
       and "MathHelper.clamp_double(data.getDouble(\"level\"),0,1)" in orc and "rod.startingLevel=rod.level;rod.setTarget(" in orc and "EnumUtil.grabEnumSafely(RBMKColor.class,color)" in orc,
       "receiveControl keeps the original's five groups in order with the original keys (:256-337): `level` (clamp 0..1, every sel_ key, startingLevel = level then setTarget on manual rods only), `toggle` (screen type + 1 modulo 6), `id` (s0..s224 -> the screen's columns), "
       "`assignColor` (abs(color % 5) = EnumUtil.grabEnumSafely on manual rods, no toggle), `compressor` (boilers only); NEO-only validation: a finite level, at most 225 sel_ keys, indices 0..224, screen slots 0..5", (ordered_missing(rc, frags)[:4], olits ^ nlits))
    ck("V2.receive-validation", "if(Double.isFinite(target)){" in rc and "if(index<0||index>=this.columns.length)continue;" in rc and rc.count("if(slot>=0&&slot<this.screens.length){") == 2 and "if(processed++>=this.columns.length)break;" in rc
       and "Math.abs(color%RBMKColor.values().length)" in rc and "intcount=Math.min(cols.length,this.columns.length);" in sel and "if(cols[k]>=0&&cols[k]<this.columns.length)valid.add(cols[k]);" in sel
       and "RBMKColor.values().length" not in orc and "grabEnumSafely" in orc,
       "the NEO-only server checks exist where the original trusts the client: finite level, at most 225 sel_ keys, index 0..224, slot 0..5 for toggle and id, colour index abs(color % 5), at most 225 cols entries each within 0..224")
    # ---- AZ-5 packet
    click = ov.b["gui.click"]
    az5 = derive(click[click.index("NBTTagCompoundcontrol=newNBTTagCompound();control.setDouble(\"level\",0);"):], [])
    az5 = az5[:az5.index("PacketDispatcher")]
    exp_az5 = derive(az5, [("NBTTagCompound", "CompoundTag"), ("control.setDouble", "control.putDouble"), ("control.setInteger", "control.putInt"), ("console.columns", "columns"), ("ColumnType.CONTROL", "RBMKColumnType.CONTROL")])
    az = nb("public static CompoundTag buildAZ5Control(RBMKColumn[] columns)")
    eq(ck, "V2.az5-packet", "buildAZ5Control is the AZ-5 packet of GUIRBMKConsole (:229-235): level 0 and sel_<j> for every non-null CONTROL column (not CONTROL_AUTO)", exp_az5 + "returncontrol;", az)
    # ---- NBT
    exp = derive(ov.b["con.read"], [("super.readFromNBT(nbt);", "super.loadAdditional(tag,registries);"), ("nbt.getInteger(", "tag.getInt("),
                                     ('ScreenType.values()[nbt.getByte("t"+i)]', 'screenTypeOf(tag.getByte("t"+i))'), ('Arrays.stream(nbt.getIntArray("s"+i)).boxed().toArray(Integer[]::new)', 'tag.getIntArray("s"+i)'),
                                     ('rotation=nbt.getByte("rotation");', 'this.rotation=(byte)(tag.getByte("rotation")&3);')])
    eq(ck, "V2.nbt-load", "loadAdditional reads the original keys (:357-370): tX, tY, tZ, t<i> (screen type byte), s<i> (int array) and rotation; NEO-only: a bad type byte reads NONE and the rotation is kept within 0..3", exp,
       nb("protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)"))
    exp = derive(ov.b["con.write"], [("super.writeToNBT(nbt);", "super.saveAdditional(tag,registries);"), ("nbt.setInteger(", "tag.putInt("), ('nbt.setByte("t"+i', 'tag.putByte("t"+i'),
                                      ('nbt.setIntArray("s"+i,Arrays.stream(this.screens[i].columns).mapToInt(Integer::intValue).toArray())', 'tag.putIntArray("s"+i,this.screens[i].columns)'),
                                      ('nbt.setByte("rotation",rotation)', 'tag.putByte("rotation",this.rotation)')])
    eq(ck, "V2.nbt-save", "saveAdditional writes the original keys (:372-385): tX, tY, tZ, t<i>, s<i>, rotation; the columns and the flux history are not saved", exp,
       nb("protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)"))
    # ---- target, rotation, index mapping, bounding box
    eq(ck, "V2.set-target", "setTarget stores the three coordinates and marks the entity changed (:350-355)", derive(ov.b["con.setTarget"], [("markDirty", "setChanged")]), nb("public void setTarget(int x, int y, int z)"))
    ck("V2.rotate", ov.b["con.rotate"] == "rotation=(byte)((rotation+1)%4);" and nb("public void rotate()") == "rotation=(byte)((rotation+1)%4);this.setChanged();",
       "rotate() = (rotation + 1) % 4 (:387-389); NEO also marks the console changed so the turn is saved (the original only changes the field)")
    eq(ck, "V2.index-x", "getXFromIndex is the original (:391-406): i = col % 15 - 7, j = col / 15 - 7; rotation 0 i, 1 -j, 2 -i, 3 j", ov.b["con.getX"], nb("public int getXFromIndex(int col)"))
    eq(ck, "V2.index-z", "getZFromIndex is the original (:408-423): rotation 0 j, 1 i, 2 -j, 3 -i, default j", ov.b["con.getZ"], nb("public int getZFromIndex(int col)"))
    exp = "BlockPospos=this.getBlockPos();return" + derive(ov.b["con.bbox"], [("return", ""), ("AxisAlignedBB.getBoundingBox(", "newAABB("), ("xCoord", "pos.getX()"), ("yCoord", "pos.getY()"), ("zCoord", "pos.getZ()")])
    eq(ck, "V2.render-box", "the render bounding box is the original's (:339-342): (x - 2, y, z - 2) to (x + 3, y + 4, z + 3) around the block position", exp, nb("public AABB getRenderBoundingBox()"))
    # ---- enums and column class
    nsc = enum_members(text, "ScreenType")
    osc = enum_members(inp.o["con"], "ScreenType")
    nct = enum_members(lf(st.text(J + "blockentity/machine/rbmk/RBMKColumnType.java")), "RBMKColumnType") if st.has(J + "blockentity/machine/rbmk/RBMKColumnType.java") else None
    oct_ = enum_members(inp.o["con"], "ColumnType")
    ck("V2.enums", nsc == osc and list(nsc) == list(osc) and nct == oct_ and list(nct) == list(oct_) and len(nct) == 14 and len(nsc) == 6,
       "ScreenType (6 members, offsets 0, 18, 36, 54, 72, 90) is the original's, in the original order; the existing RBMKColumnType (14 members, GUI offsets) equals the original ColumnType (:502-523, :538-551)", (nsc, nct))
    ck("V2.column-classes", "publicstaticclassRBMKColumn{publicRBMKColumnTypetype;publicCompoundTagdata;publicRBMKColumn(RBMKColumnTypetype,CompoundTagdata){this.type=type;if(data!=null){this.data=data;}else{this.data=newCompoundTag();}}}" in code
       and "publicstaticclassRBMKScreen{publicScreenTypetype=ScreenType.NONE;publicint[]columns=newint[0];publicStringdisplay=null;}" in code,
       "RBMKColumn(type, data) turns a null compound into an empty one (:425-442) and RBMKScreen starts as NONE, no columns, display null (:525-536)")
    # ---- the files the console only reads
    bad = [p for p in UNTOUCHED if not hashed_equal(inp, st, p)]
    ck("V2.untouched", not bad and len(UNTOUCHED) == 25, "the 25 RBMK, network, multiblock and recipe files the console only reads (RBMKBaseBlockEntity, RBMKColumnType, the control rods, boiler, rods, RBMKBaseBlock, the neutron handler, CompoundTagControl, BufPacket, DummyableBlock, "
       "MultiblockHandlerXR, AnvilRecipes, ...) are byte-equal to the start copies", [p.rsplit("/", 1)[1] for p in bad])
    ck("V2.control-dispatch", "icr.hasPermission(player)" in lf(st.text(J + "network/toserver/CompoundTagControl.java")) and "icr.receiveControl(packet.tag);" in lf(st.text(J + "network/toserver/CompoundTagControl.java")),
       "CompoundTagControl (unchanged) asks hasPermission before it calls receiveControl(tag) on the block entity at the sent position, so the console's 20-block rule applies")
    ck("V2.no-client-import", "net.minecraft.client" not in blank_comments(text) and "com.hbm.render" not in blank_comments(text) and "inventory.screens" not in blank_comments(text),
       "RBMKConsoleBlockEntity imports nothing client-side (no net.minecraft.client, renderer or screen class)")


# ---------------------------------------------------------------- V3 block, menu, item against V1

def v3_block_menu_item(ck, inp, st):
    ov = need_ov(inp)
    blk = cs(st, CBLK)
    # ---- the block
    dims = re.search(r"returnnewint\[\]\{([\d,]+)\};", ov.b["blk.dims"])
    extra = re.search(r"newint\[\]\{([\d,]+)\},this,dir\);$", ov.b["blk.fill"])
    extra_c = re.search(r"newint\[\]\{([\d,]+)\},x,y,z,dir\)\)returnfalse;", ov.b["blk.check"])
    ck("V3.block-dimensions", bool(dims and extra and extra_c) and dims[1] == "3,0,0,0,2,2" and extra[1] == extra_c[1] == "0,0,0,1,2,2" and ov.b["blk.offset"] == "return1;"
       and nbody(st, CBLK, "public int[] getDimensions()") == ov.b["blk.dims"] and nbody(st, CBLK, "public int getOffset()") == ov.b["blk.offset"]
       and f"privatestaticfinalint[]EXTRA_DIMENSIONS=newint[]{{{extra[1] if extra else ''}}};" in blk,
       "RBMKConsoleBlock.getDimensions {3, 0, 0, 0, 2, 2} and getOffset 1 are the original's (RBMKConsole.java:101-109) and the second box constant {0, 0, 0, 1, 2, 2} equals the one in the original fillSpace (:121) and checkRequirement (:126)",
       (dims and dims[1], extra and extra[1], extra_c and extra_c[1]))
    fill = nbody(st, CBLK, "protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset)")
    chk = nbody(st, CBLK, "protected boolean checkRequirement(Level level, BlockPos pos, Direction dir, int offset)")
    ck("V3.block-second-box", fill == "super.fillSpace(level,pos,dir,offset);MultiblockHandlerXR.fillSpace(level,pos.relative(dir,offset),EXTRA_DIMENSIONS,this,dir);"
       and chk == "if(!MultiblockHandlerXR.checkSpace(level,pos.relative(dir,offset),EXTRA_DIMENSIONS,pos,dir))returnfalse;returnsuper.checkRequirement(level,pos,dir,offset);"
       and ov.b["blk.fill"].startswith("super.fillSpace(world,x,y,z,dir,o);MultiblockHandlerXR.fillSpace(world,x+dir.offsetX*o,y,z+dir.offsetZ*o,")
       and ov.b["blk.check"].startswith("if(!MultiblockHandlerXR.checkSpace(world,x+dir.offsetX*o,y+dir.offsetY*o,z+dir.offsetZ*o,") and ov.b["blk.check"].endswith("returnsuper.checkRequirement(world,x,y,z,dir,o);"),
       "the second box is filled after the main box (fillSpace: super first, then MultiblockHandlerXR.fillSpace at the offset core, :117-122) and checked BEFORE the main requirement, a failure returning false (checkRequirement :124-130), both with the same box")
    hard = re.search(r"this\.setHardness\((\d+)F\);\s*this\.setResistance\((\d+)F\);", blank_comments(inp.o["blk"]))
    nb_ = cs(st, NB)
    want = sq(f'RBMK_CONSOLE=register("rbmk_console",()->newRBMKConsoleBlock(BlockBehaviour.Properties.of().noOcclusion().strength({float(hard[1]):.1f}F,{float(hard[2]):.1f}F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops()));') if hard else ""
    ck("V3.block-properties", bool(hard) and want in nb_.replace("DeferredBlock<Block>", "") and nb_.count('register("rbmk_console"') == 1 and "Material.iron" in inp.o["blk"] and "isOpaqueCube() {\n\t\treturn false;" in inp.o["blk"],
       "NtmBlocks.RBMK_CONSOLE has the original strength (hardness 3 / resistance 30, RBMKConsole.java:25-26), is not an occluding cube (isOpaqueCube / renderAsNormalBlock false, :43-51), uses the iron sound, and, as Material.iron, needs a tool for drops (builder correction 2026-10-19)",
       (hard and hard.groups(), want[:140]))
    ck("V3.block-entity", ov.b["blk.create"] == "if(meta>=this.offset)returnnewTileEntityRBMKConsole();returnnull;"
       and nbody(st, CBLK, "public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state)") == "returnstate.getValue(TYPE)==DummyBlockType.CORE?newRBMKConsoleBlockEntity(pos,state):null;"
       and nbody(st, CBLK, "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type)")
       == "if(level.isClientSide||state.getValue(TYPE)!=DummyBlockType.CORE)returnnull;return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};",
       "only the core has a block entity (createNewTileEntity: meta >= offset, :29-36) and only the core ticks, on the server (the original console updates only on the server)")
    act = ov.b["blk.activated"]
    dummy = cs(st, J + "blocks/DummyableBlock.java")
    ck("V3.block-use", nbody(st, CBLK, "protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult)") == "returnthis.standardOpenBehavior(level,pos,player);"
       and "if(!player.isSneaking()){" in act and "FMLNetworkHandler.openGui(player,MainRegistry.instance,0,world,pos[0],pos[1],pos[2]);" in act and act.rstrip("}").endswith("else{returntrue;")
       and "if(level.isClientSide)returnInteractionResult.SUCCESS;if(!player.isShiftKeyDown()){BlockPoscorePos=this.findCore(level,pos);if(corePos==null)returnInteractionResult.FAIL;" in dummy and "returnInteractionResult.CONSUME;}returnInteractionResult.SUCCESS;" in dummy
       and hashed_equal(inp, st, J + "blocks/DummyableBlock.java"),
       "using the console opens the menu for the core unless the player sneaks (original :54-99: not sneaking opens the GUI for the core on the client, sneaking returns true and does nothing); NEO's standardOpenBehavior (unchanged DummyableBlock) opens the menu on the server and "
       "consumes a sneaking click without doing anything. The guide-book branch (:68-89) and markFBI (:58) are not ported")
    ow = ov.b["blk.screw"]
    ck("V3.block-screw", ow == "if(tool!=ToolType.SCREWDRIVER)returnfalse;if(!world.isRemote){int[]pos=findCore(world,x,y,z);TileEntitytile=world.getTileEntity(pos[0],pos[1],pos[2]);if(tileinstanceofTileEntityRBMKConsole){((TileEntityRBMKConsole)tile).rotate();}}returntrue;"
       and nbody(st, CBLK, "public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool)")
       == "if(tool!=ToolType.SCREWDRIVER)returnfalse;if(!level.isClientSide){BlockPoscore=this.findCore(level,pos);if(core!=null&&level.getBlockEntity(core)instanceofRBMKConsoleBlockEntityconsole){console.rotate();}}returntrue;",
       "onScrew acts only for the screwdriver (anything else returns false), on the server rotates the console at the core, and returns true (RBMKConsole.java:132-144); NEO also guards a missing core")
    ck("V3.block-class", "publicclassRBMKConsoleBlockextendsDummyableBlockimplementsIToolable{" in blk and "class RBMKConsole extends BlockDummyable implements IToolable" in inp.o["blk"],
       "RBMKConsoleBlock is a DummyableBlock and an IToolable, like the original BlockDummyable + IToolable")
    # ---- the menu
    menu = cs(st, CMENU)
    ck("V3.menu", "publicclassRBMKConsoleMenuextendsMenuBase<RBMKConsoleBlockEntity>{" in menu and "super(NtmMenuTypes.RBMK_CONSOLE.get(),id,be);" in menu and "addSlot" not in menu and "playerInv" not in menu
       and "publicItemStackquickMoveStack(Playerplayer,intindex){returnItemStack.EMPTY;}" in menu
       and "this(id,inventory,(RBMKConsoleBlockEntity)CompatExternal.getCoreFromPos(inventory.player.level,extraData.readBlockPos()));" in menu and "class GUIRBMKConsole extends GuiScreen" in inp.o["gui"] and "Container" not in blank_comments(inp.o["gui"]).split("class GUIRBMKConsole")[1][:400],
       "RBMKConsoleMenu has no slots and no player inventory (the original GUIRBMKConsole is a plain GuiScreen without a container), moves nothing on shift-click, reads the core position from the open-menu buffer and takes the core block entity")
    ck("V3.menu-provider", "returnnewRBMKConsoleMenu(containerId,inventory,this);" in cs(st, CON) and "returnComponent.translatable(this.getBlockState().getBlock().getDescriptionId());" in cs(st, CON) and "return null;" in inp.o["con"].split("public String getName()")[1][:60],
       "the console opens RBMKConsoleMenu and its title is the block name (the original getName returns null: no title of its own)")
    # ---- the tool item
    tool = cs(st, TOOL)
    use = nbody(st, TOOL, "public InteractionResult useOn(UseOnContext context)")
    frags = ["if(binstanceofRBMKBaseBlockrbmk){", "BlockPoscore=rbmk.findCore(level,pos);", "if(core!=null&&!level.isClientSide){", 'tag.putInt("posX",core.getX());', 'tag.putInt("posY",core.getY());', 'tag.putInt("posZ",core.getZ());',
             "TagsUtil.putCustomData(stack,tag);", 'Component.translatable(this.getDescriptionId()+".linked").withStyle(ChatFormatting.YELLOW)', "returnInteractionResult.sidedSuccess(level.isClientSide);",
             "if(binstanceofRBMKConsoleBlockconsole&&hasPosition(stack)){", "if(!level.isClientSide){", "BlockPoscore=console.findCore(level,pos);", "be.setTarget(tag.getInt(\"posX\"),tag.getInt(\"posY\"),tag.getInt(\"posZ\"));",
             'Component.translatable(this.getDescriptionId()+".set").withStyle(ChatFormatting.YELLOW)', "returnInteractionResult.sidedSuccess(level.isClientSide);", "returnInteractionResult.PASS;"]
    ouse = ov.b["tool.use"]
    olit, nlit = set(re.findall(r'"([^"]*)"', ouse)), set(re.findall(r'"([^"]*)"', use))
    ck("V3.tool-use", not ordered_missing(use, frags) and {"posX", "posY", "posZ", ".linked", ".set"} <= olit and nlit == {"posX", "posY", "posZ", ".linked", ".set"} and "binstanceofRBMKBase" in ouse,
       "RBMKToolItem.useOn is ItemRBMKTool.onItemUse (:28-103): on an RBMK column it stores the core's posX/posY/posZ and says item.rbmk_tool.linked in yellow (server), succeeding on both sides; on the console with a stored position it sets the core's target and says .set in yellow; "
       "anything else passes (the crane console and rbmk_display branches :70-100 are Goals 25 and 26)", (ordered_missing(use, frags)[:3], olit ^ nlit))
    ck("V3.tool-key-check", "privatestaticbooleanhasPosition(ItemStackstack){CompoundTagtag=TagsUtil.getCustomData(stack);returntag.contains(\"posX\")&&tag.contains(\"posY\")&&tag.contains(\"posZ\");}" in tool and "stack.hasTagCompound()" in ouse,
       "NEO-only: the console branch needs the three position keys (the original accepts any NBT: `b == rbmk_console && stack.hasTagCompound()`, :53), so an unlinked tool cannot point a console at 0, 0, 0")
    attr = ov.b["tool.attr"]
    ck("V3.tool-attributes", 'newAttributeModifier(field_111210_e,"Weapon modifier",2,0)' in attr and "SharedMonsterAttributes.attackDamage" in attr
       and "Attributes.ATTACK_DAMAGE,newAttributeModifier(BASE_ATTACK_DAMAGE_ID,2,AttributeModifier.Operation.ADD_VALUE),EquipmentSlotGroup.MAINHAND" in tool,
       "the tool carries the original's +2 attack damage weapon modifier (ItemRBMKTool.java:112-118: attack damage, amount 2, operation 0 = add; main hand)")
    oinfo = ov.b["tool.info"]
    ck("V3.tool-tooltip", 'for(Strings:I18nUtil.resolveKeyArray(this.getUnlocalizedName()+".desc"))list.add(EnumChatFormatting.YELLOW+s);' in oinfo
       and 'for(Strings:I18nUtil.resolveKeyArray(this.getDescriptionId()+".desc"))components.add(Component.literal(s).withStyle(ChatFormatting.YELLOW));' in tool,
       "the tooltip is the .desc key split into lines by I18nUtil.resolveKeyArray, each in yellow (ItemRBMKTool.java:105-110)")
    stack_n = re.search(r"setMaxStackSize\((\d+)\)", inp.o["mi"].split("\n")[3837])
    reg = cs(st, NITEMS)
    ck("V3.tool-stack-size", bool(stack_n) and f'RBMK_TOOL=ITEMS.register("rbmk_tool",()->newRBMKToolItem(newItem.Properties().stacksTo({stack_n[1]})));' in reg.replace("DeferredItem<Item>", "") and stack_n[1] == "1",
       "the tool stacks to 1 (ModItems.java:3838 setMaxStackSize(1))", stack_n and stack_n[1])
    ck("V3.no-client-import", all(not re.search(CLIENT_ONLY, blank_comments(lf(st.text(p)))) for p in (CON, CBLK, CMENU, TOOL)),
       "the block entity, block, menu and tool item refer to no client class (no net.minecraft.client, renderer, screen or client entry)", [p.rsplit("/", 1)[1] for p in (CON, CBLK, CMENU, TOOL) if re.search(CLIENT_ONLY, blank_comments(lf(st.text(p))))])


# ---------------------------------------------------------------- V4 client: registrations, screen, renderer, isolation

CLIENT_ONLY = r"net\.minecraft\.client|com\.hbm\.render|inventory\.screens|RBMKConsoleScreen|RenderRBMKConsole|NuclearTechModClient|ClientProxy"
GUI_RENAMES = [(r"\bguiLeft\b", "leftPos"), (r"\bguiTop\b", "topPos"), (r"\bxSize\b", "imageWidth"), (r"\bySize\b", "imageHeight"), (r"this\.console\.", "be."), (r"\bconsole\.", "be.")]


def v4_registrations(ck, inp, st):
    need_ov(inp)
    nb, bet, mt, items, snd, sdp, nmc, cp, rm, ct = (cs(st, p) for p in (NB, BET, MT, NITEMS, SOUNDS, SDP, NMC, CP, RM, CT))
    ck("V4.reg-block", nb.count('register("rbmk_console"') == 1 and nb.index('RBMK_LOADER=register("rbmk_loader"') < nb.index('RBMK_CONSOLE=register("rbmk_console"'),
       "NtmBlocks registers the rbmk_console block exactly once, after RBMK_LOADER (ModBlocks.java:2131 / :3125; the block item comes from the register helper)")
    want = 'RBMK_CONSOLE=BLOCK_ENTITY_TYPES.register("rbmk_console",()->BlockEntityType.Builder.of(RBMKConsoleBlockEntity::new,NtmBlocks.RBMK_CONSOLE.get()).build(null));'
    ck("V4.reg-block-entity", bet.count(want) == 1 and bet.count('"rbmk_console"') == 1 and bet.index('"rbmk_cooler"') < bet.index('"rbmk_console"') and "tileentity_rbmk_console" in lf(inp.o["tm"]),
       "NtmBlockEntityTypes registers one rbmk_console block entity type, valid for the console block only, after the last RBMK entry (TileMappings.java:418 tileentity_rbmk_console)")
    ck("V4.reg-menu-screen", mt.count('RBMK_CONSOLE=reg("rbmk_console",RBMKConsoleMenu::new);') == 1 and mt.count('"rbmk_console"') == 1 and mt.index('"rbmk_heater"') < mt.index('"rbmk_console"')
       and nmc.count("event.register(NtmMenuTypes.RBMK_CONSOLE.get(),RBMKConsoleScreen::new);") == 1 and nmc.count("importcom.hbm.inventory.screens.RBMKConsoleScreen;") == 1,
       "the console menu type is registered once (after the 24D RBMK menus) and its screen once in the client entry NuclearTechModClient")
    ck("V4.reg-renderer", cp.count("BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_CONSOLE.get(),newRenderRBMKConsole());") == 1 and cp.count("RenderRBMKConsole") == 1 and cp.count("NtmBlockEntityTypes.RBMK_CONSOLE.get()") == 1
       and "bindTileEntitySpecialRenderer(TileEntityRBMKConsole.class,newRenderRBMKConsole())" in sq(blank_comments(inp.o["cproxy"])),
       "ClientProxy registers RenderRBMKConsole for the console block entity exactly once (the original binds it in its ClientProxy too)", cp.count("RenderRBMKConsole"))
    ck("V4.reg-item-sound", items.count('"rbmk_tool"') == 1 and snd.count('"block.shutdown"') == 1 and "SHUTDOWN=reg(\"block.shutdown\");" in snd and snd.index("RBMK_AZ5_COVER") < snd.index("SHUTDOWN="),
       "NtmItems registers rbmk_tool once and NtmSoundEvents registers the block.shutdown sound event once, after block.rbmk_az5_cover")
    ck("V4.reg-sound-definition", sdp.count("NtmSoundEvents.SHUTDOWN") == 1 and 'this.add(NtmSoundEvents.SHUTDOWN,SoundDefinition.definition().with(sound(NuclearTechMod.withDefaultNamespace("block/shutdown")).stream()));' in sdp
       and '"block.shutdown": {"category": "block", "sounds": [{"name": "block/shutdown", "stream": true}]}' in inp.o["sounds"].split("\n")[6],
       "NtmSoundDefinitionsProvider defines block.shutdown once with the sound block/shutdown streamed, as the original sounds.json:7")
    o1683 = re.search(r'new ResourceLocation\(RefStrings\.MODID, "models/(rbmk/rbmk_console\.obj)"\)\)\.asVBO\(\);', inp.o["rm"].split("\n")[1682])
    o1694 = re.search(r'new ResourceLocation\(RefStrings\.MODID, "(textures/models/machines/rbmk_control\.png)"\)', inp.o["rm"].split("\n")[1693])
    ck("V4.reg-resource-manager", bool(o1683 and o1694) and rm.count(f'rbmk_console=newHFRWavefrontObject("models/obj/{o1683[1] if o1683 else ""}").asVBO();') == 1
       and rm.count(f'RBMK_CONSOLE_TEX=NuclearTechMod.withDefaultNamespace("{o1694[1] if o1694 else ""}");') == 1 and rm.count("publicstaticIModelCustomrbmk_console;") == 1,
       "ResourceManager declares the console OBJ (models/obj/rbmk/rbmk_console.obj, smooth, original :1683) and the console model texture (textures/models/machines/rbmk_control.png, :1694) once each")
    ck("V4.reg-creative-tabs", ct.count("output.accept(NtmBlocks.RBMK_CONSOLE);") == 1 and ct.count("output.accept(NtmItems.RBMK_TOOL);") == 1 and ct.index("output.accept(NtmBlocks.RBMK_LOADER);") < ct.index("output.accept(NtmBlocks.RBMK_CONSOLE);")
       and ct.index("output.accept(NtmItems.OIL_DETECTOR);") < ct.index("output.accept(NtmItems.RBMK_TOOL);") < ct.index("output.accept(NtmItems.COLTAN_TOOL);"),
       "the machine tab lists the console once after RBMK_LOADER and the consumable tab lists the tool once between OIL_DETECTOR and COLTAN_TOOL (ModItems.java registration order oil_detector, rbmk_tool, coltan_tool)")
    common = [CON, CBLK, CMENU, TOOL, NB, BET, MT, NITEMS, SOUNDS, CT]
    leak = [p.rsplit("/", 1)[1] for p in common if re.search(CLIENT_ONLY, blank_comments(lf(st.text(p))))]
    ck("V4.client-isolation", not leak and "importcom.hbm.render.blockentity.*;" in cp and "net.minecraft.client" not in blank_comments(lf(st.text(CON))),
       "no common class (block entity, block, menu, tool, block / block entity / menu / item / sound registries, creative tabs) refers to a screen, renderer or net.minecraft.client; the screen is used by NuclearTechModClient and the renderer by ClientProxy only", leak)


def click_ops(code, set_prefix, az5_ops=None):
    """Ordered (type, key) of the control payload statements of a squashed click body; where az5_ops is given, buildAZ5Control stands for them."""
    out = []
    for m in re.finditer(r"control\." + set_prefix + r"(\w+?)\(\"([^\"]+)\"|buildAZ5Control", code):
        if m[0] == "buildAZ5Control":
            out += az5_ops or []
        else:
            out.append(({"Integer": "Int"}.get(m[1], m[1]), m[2]))
    return out


def v4_screen(ck, inp, st):
    ov = need_ov(inp)
    oc = blank_comments(inp.o["gui"])
    scr = lf(st.text(CSCREEN))
    code = sq(blank_comments(scr))
    # ---- panel, texture, field
    size = re.search(r"this\.xSize = (\d+);\s*this\.ySize = (\d+);", oc)
    tex = re.search(r"textures/gui/reactors/(gui_rbmk_console\.png)", oc)
    fld = re.search(r"new GuiTextField\(this\.fontRendererObj, guiLeft \+ (\d+), guiTop \+ (\d+), (\d+), (\d+)\);\s*this\.field\.setTextColor\((0x\w+)\);\s*this\.field\.setDisabledTextColour\((0x\w+)\);\s*this\.field\.setEnableBackgroundDrawing\(false\);\s*this\.field\.setMaxStringLength\((\d+)\);", oc)
    want = []
    if size and tex and fld:
        want = [sq(f"this.imageWidth={size[1]};this.imageHeight={size[2]};"), sq(f'NuclearTechMod.withDefaultNamespace("textures/gui/reactors/{tex[1]}")'),
                sq(f"this.field=newEditBox(this.font,this.leftPos+{fld[1]},this.topPos+{fld[2]},{fld[3]},{fld[4]},Component.empty());this.field.setTextColor({fld[5]});this.field.setTextColorUneditable({fld[6]});this.field.setBordered(false);this.field.setMaxLength({fld[7]});")]
    miss = [w for w in want if w not in code]
    ck("V4.screen-panel-field", bool(want) and not miss and (size[1], size[2]) == ("244", "172"),
       "RBMKConsoleScreen is 244 x 172 with the texture gui_rbmk_console.png and the text field at (9, 84) 35 x 9, green 0x00ff00 (uneditable 0x008000), no background, 3 characters (GUIRBMKConsole.java:34, :51-52, :63-67)", miss)
    # ---- rectangles of the click handler
    neo_click = nbody(st, CSCREEN, "public boolean mouseClicked(double mouseX, double mouseY, int button)")
    orr, nrr = rects(ov.b["gui.click"], "guiLeft", "guiTop"), rects(neo_click, "leftPos", "topPos")
    ck("V4.screen-click-rectangles", len(orr) == 9 and orr == nrr,
       "mouseClicked tests the original's nine rectangles in the original order: the grid (86, 11, 150), clear (72, 70, 10), select all (61, 70, 10), compressor (70, 82, 12), the five colour buttons (6 + 11k, 70, 10), AZ-5 (30, 138, 28), save (48, 82, 12) and the two screen buttons "
       "(6 + 40k and 24 + 40k, 8 + 21j, 18), each as x <= mx < x + w, y < my <= y + h", (len(orr), [(a, b) for a, b in zip(orr, nrr) if a != b][:3]))
    ots, nts = info_stats(ov.b["gui.draw"], "guiLeft", "guiTop"), info_stats(nbody(st, CSCREEN, "public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks)"), "leftPos", "topPos")
    nts = [y for x in nts for y in ([(str(6 + 11 * k), x[1], x[2], x[3]) for k in range(5)] if x[0] == "6+11*k" else [x])]
    ck("V4.screen-tooltip-rectangles", len(ots) == 10 and ots == nts,
       "the ten tooltip rectangles of drawScreen (GUIRBMKConsole.java:95-111) are the original's in order: select all (61, 70), deselect all (72, 70), the six screen buttons' two tips (6 + 40j / 24 + 40j, 8 + 21i, 18 x 18), the five colour buttons (6 + 11k... 10 x 10) and the compressor (70, 82, 12 x 12)",
       (len(ots), [(a, b) for a, b in zip(ots, nts) if a != b][:3]))
    o_cols = re.findall(r"EnumChatFormatting\.(RED|YELLOW|GREEN|BLUE|LIGHT_PURPLE) \+ \"Left click: Select (\w+) group\"", oc)
    n_cols = re.search(r"GROUP_COLORS=newChatFormatting\[\]\{([^}]*)\};", code)
    n_groups = re.search(r"GROUPS=newString\[\]\{([^}]*)\};", code)
    ck("V4.screen-group-colours", len(o_cols) == 5 and n_cols and n_groups and [c for c, _ in o_cols] == [x.replace("ChatFormatting.", "") for x in n_cols[1].split(",")] and [g for _, g in o_cols] == [x.strip('"') for x in n_groups[1].split(",")]
       and "Component.literal(I18nUtil.resolveKey(\"rbmk.console.group.\"+GROUPS[k]+\".select\")).withStyle(GROUP_COLORS[k])" in code and "Component.literal(I18nUtil.resolveKey(\"rbmk.console.group.\"+GROUPS[k]+\".assign\")).withStyle(GROUP_COLORS[k])" in code,
       "the five colour-group tips are coloured RED, YELLOW, GREEN, BLUE, LIGHT_PURPLE for red, yellow, green, blue, purple (GUIRBMKConsole.java:106-110) and read their text from the rbmk.console.group.<colour>.select / .assign keys", (o_cols, n_cols and n_cols[1]))
    # ---- packets and sounds
    az5_ops = control_ops(nbody(st, CON, "public static CompoundTag buildAZ5Control(RBMKColumn[] columns)"), "put")
    o_ops, n_ops = click_ops(ov.b["gui.click"], "set"), click_ops(neo_click, "put", az5_ops)
    ck("V4.screen-packets", o_ops == n_ops and len(o_ops) == 11 and ("Double", "level") in o_ops and az5_ops == [("Double", "level"), ("Int", "sel_")],
       "the control payloads are the original's in the original order (GUIRBMKConsole.java:166-295): compressor {compressor, cols}, colour assign {assignColor, cols}, AZ-5 {level 0, sel_<j>}, save {level, sel_<i>}, screen toggle {toggle}, screen assign {id, s<i>}; the AZ-5 payload is buildAZ5Control",
       (o_ops, n_ops))
    o_snd, n_snd = sound_calls(ov.b["gui.click"], True), sound_calls(neo_click, False)
    ck("V4.screen-sounds", o_snd == n_snd and len(o_snd) == 11 and [s for s, _ in o_snd].count("click") == 9 and ("RBMK_AZ5_COVER", "0.5") in o_snd and ("SHUTDOWN", "1") in o_snd,
       "the click handler plays the original's sounds in order with the original pitches: grid 0.75 / 1.0, clear 0.5, select all 1.5, compressor 1, colour 0.8 + 0.1k, AZ-5 cover 0.5, shutdown 1 then button 1, save 1, screen buttons 0.5 and 0.75 (gui.button.press -> the UI click)",
       (o_snd, n_snd))
    ck("V4.screen-sound-calls", "SimpleSoundInstance.forUI(SoundEvents.UI_BUTTON_CLICK,pitch)" in code and "SimpleSoundInstance.forUI(sound,pitch)" in code and "NtmSoundEvents.SHUTDOWN.get()" in neo_click and "NtmSoundEvents.RBMK_AZ5_COVER.get()" in neo_click,
       "the button sound is the vanilla UI click with the given pitch and the AZ-5 sounds are NtmSoundEvents.RBMK_AZ5_COVER and SHUTDOWN played locally as UI sounds (the shutdown sound never goes to the server)")
    oaz = ov.b["gui.click"]
    ck("V4.screen-az5", "if(az5Lid){az5Lid=false;" in oaz and "elseif(lastPress+3000<System.currentTimeMillis()){" in oaz and "lastPress=System.currentTimeMillis();" in oaz
       and "if(az5Lid){az5Lid=false;" in neo_click and "elseif(lastPress+3000<System.currentTimeMillis()){" in neo_click and "lastPress=System.currentTimeMillis();" in neo_click and "this.send(RBMKConsoleBlockEntity.buildAZ5Control(be.columns));" in neo_click
       and "NtmSoundEvents.SHUTDOWN.get(),1)" in neo_click and "this.click(1);" in neo_click.split("buildAZ5Control")[1].split("return")[0],
       "AZ-5 (GUIRBMKConsole.java:219-241): the first click opens the lid (cover sound), later clicks after 3000 ms play the shutdown sound locally, store the press time and send the AZ-5 payload of the screen's columns, then the button sound; the click always returns true")
    ck("V4.screen-selection-rules", all(x in neo_click for x in ["this.selectedOfType(RBMKColumnType.BOILER)", "this.selectedOfType(RBMKColumnType.CONTROL)", "be.columns[j].type==RBMKColumnType.CONTROL&&be.columns[j].data.getShort(\"color\")==k",
                                                                  "if(be.columns[j]!=null&&be.columns[j].type==RBMKColumnType.CONTROL){this.selection[j]=true;}"])
       and "console.columns[j].type==ColumnType.CONTROL&&console.columns[j].data.getShort(\"color\")==k" in oaz and "console.columns[j].type==ColumnType.BOILER&&this.selection[j]" in oaz and "console.columns[j].type==ColumnType.CONTROL&&this.selection[j]" in oaz
       and "if(button==LEFT_CLICK){" in neo_click and "if(button==RIGTH_CLICK){" in neo_click,
       "the selection buttons act on the original's column types: the compressor sends the selected BOILER columns, a colour's right click the selected CONTROL columns, its left click selects the CONTROL columns whose colour is k, select-all selects every CONTROL column (:158, :172, :193, :204)")
    ck("V4.screen-save", all(x in neo_click for x in ["intj=(int)Mth.clamp(level,0,100);", 'field.setValue(j+"");', 'control.putDouble("level",j*0.01);', 'if(Double.isNaN(level))returntrue;', "if(NumberUtils.isNumber(field.getValue()))"])
       and "intj=(int)MathHelper.clamp_double(Double.parseDouble(field.getText()),0,100);" in oaz and "level=j*0.01;" in oaz and "if(NumberUtils.isNumber(field.getText())){" in oaz,
       "the save button (48, 82) clamps a numeric text to an int 0..100, writes it back, sends level = j * 0.01 with the selection, and sends nothing for a non-number (GUIRBMKConsole.java:244-267); NEO also rejects forms Double.parseDouble cannot read")
    # ---- background layer
    obg = ov.b["gui.bg"]
    bg = nbody(st, CSCREEN, "protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY)")
    o_bl = [rewrite(a, GUI_RENAMES) for a in re.findall(r"drawTexturedModalRect\(([^;]*)\);", obg)]
    n_bl = re.findall(r"(?:guiGraphics\.blit\(TEXTURE|this\.bar\(guiGraphics),([^;]*)\);", bg)
    n_bl = [x for x in n_bl]
    ck("V4.screen-grid-draw", len(o_bl) == len(n_bl) == 19 and o_bl == n_bl,
       "renderBg draws the original's textured rectangles in the original order and with the original coordinates (GUIRBMKConsole.java:303-403): the panel, AZ-5 lid, six screen icons, the tile, heat bar and, per type, the CONTROL colour overlay, the rod bar (from CONTROL falling through to CONTROL_AUTO), the three fuel bars, "
       "the boiler bars and steam dots, the heat exchanger bars, and the selection overlay", (len(o_bl), len(n_bl), [(a, b) for a, b in zip(o_bl, n_bl) if a != b][:3]))
    sw = bg[bg.index("switch(col.type){"):]
    ck("V4.screen-control-fallthrough", "caseCONTROL:" in sw and "caseCONTROL_AUTO:" in sw and "break" not in sw[sw.index("caseCONTROL:"):sw.index("caseCONTROL_AUTO:")] and "caseCONTROL:" in obg and "break" not in obg[obg.index("caseCONTROL:"):obg.index("caseCONTROL_AUTO:")],
       "CONTROL falls through into CONTROL_AUTO in the grid draw, in the original (:349-357) and in NEO: a manual rod also gets the rod bar")
    ck("V4.screen-fuel-clamps", all(x in bg and x in obg for x in ["if(fh>8)fh=8;", "if(fe>8)fe=8;", "if(fx>8)fx=8;"]) and "intfr=8-(int)Math.ceil((col.data.getDouble(\"level\")*8));" in bg and "intfr=8-(int)Math.ceil((col.data.getDouble(\"level\")*8));" in obg
       and "inth=Math.min((int)Math.ceil((col.data.getDouble(\"heat\")-20)*10/col.data.getDouble(\"maxHeat\")),10);" in bg and "inth=Math.min((int)Math.ceil((col.data.getDouble(\"heat\")-20)*10/col.data.getDouble(\"maxHeat\")),10);" in obg,
       "the bar heights are the original's: heat min(ceil((heat - 20) * 10 / maxHeat), 10), rod bar 8 - ceil(level * 8), the fuel bars capped at 8")
    o_dots = [(m[1], rewrite(m[2], GUI_RENAMES)) for m in re.finditer(r'if\(col\.data\.getShort\("type"\)==Fluids\.(\w+)\.ordinal\(\)\)drawTexturedModalRect\(([^;]*)\);', obg)]
    n_dots = [(m[1], m[2]) for m in re.finditer(r"if\(type==Fluids\.(\w+)\.getID\(\)\)guiGraphics\.blit\(TEXTURE,([^;]*)\);", bg)]
    ck("V4.screen-steam-dots", len(o_dots) == len(n_dots) == 4 and o_dots == n_dots and [f for f, _ in o_dots] == ["STEAM", "HOTSTEAM", "SUPERHOTSTEAM", "ULTRAHOTSTEAM"],
       "the steam grade dots of a boiler are drawn for STEAM, HOTSTEAM, SUPERHOTSTEAM and ULTRAHOTSTEAM at the original's coordinates (x + 4, y + 1 / 3 / 5 / 7 from (44, 183 / 185 / 187 / 189)), comparing the type with the fluid ID (the original compares Fluids.X.ordinal(), its ID)", (o_dots, n_dots))
    # ---- flux graph
    ck("V4.screen-flux-graph", "px[j]=(float)(leftPos+7+k*74/be.fluxBuffer.length);" in bg and "py[j]=(float)(topPos+127-(flux-lowest)*24/Math.max(range,1));" in bg and "doublex=guiLeft+7+k*74/console.fluxBuffer.length;" in obg
       and "doubley=guiTop+127-(flux-lowest)*24/Math.max(range,1);" in obg and "for(inti=0;i<be.fluxBuffer.length-1;i++){" in bg and "for(inti=0;i<console.fluxBuffer.length-1;i++){" in obg
       and "intcolor=0xFF00FF00;" in code and "tess.setColorOpaque_I(0x00ff00);" in obg and "consumer.addVertex(matrix,x1-nx,y1-ny,0).setColor(color);" in code,
       "the flux graph joins the 60 buffer points with 59 green segments at x = left + 7 + k * 74 / 60 and y = top + 127 - (flux - lowest) * 24 / max(range, 1) (GUIRBMKConsole.java:405-430; NEO draws each 2 px segment as a quad)")
    o_lab = re.findall(r"this\.fontRendererObj\.drawString\((.*?),0x00ff00\);", obg)
    n_lab = re.findall(r"guiGraphics\.drawString\(this\.font,(.*?),0x00ff00,false\);", bg)
    o_lab = [rewrite(a, [(r"\bguiLeft\b", "leftPos"), (r"\bguiTop\b", "topPos"), (r"this\.fontRendererObj\.getStringWidth\(", "this.font.width("), (r"this\.fontRendererObj\.FONT_HEIGHT", "this.font.lineHeight")]) for a in o_lab]
    ck("V4.screen-flux-labels", len(o_lab) == len(n_lab) == 4 and o_lab == n_lab and "doublescale=0.5;" in obg and "floatscale=0.5;" in bg and "guiGraphics.pose().scale(scale,scale,1);" in bg,
       "the four flux labels are drawn at half scale in green: highest at (8, 98) and right-aligned to x 80, lowest at (8, 133 - fontHeight / 2) and right-aligned (GUIRBMKConsole.java:432-437)", (o_lab, n_lab))
    # ---- fancy stats and the hover fix
    ofs, nfs = ov.b["con.fancy"], nbody(st, CSCREEN, "public static List<Component> getFancyStats(RBMKColumn column)")
    want_stats, pos = [], 0
    while True:
        k = ofs.find("stats.add(", pos)
        if k < 0:
            break
        end = match_paren(ofs, k + len("stats.add"))
        inner = ofs[k + len("stats.add("):end]
        inner = re.sub(r"^EnumChatFormatting\.(\w+)\+(.*)$", r"line(ChatFormatting.\g<1>,\g<2>)", inner)
        inner = inner.replace("this.data.", "data.").replace(".getLocalizedName()", ".getName().getString()").replace(".getInteger(", ".getInt(")
        want_stats.append("stats.add(" + inner + ");")
        pos = end
    bad_stats = [x for x in want_stats if x not in nfs]
    ck("V4.screen-fancy-stats", len(want_stats) == 13 == nfs.count("stats.add(") and not bad_stats and "caseCONTROL:" in ofs and "break;caseCONTROL_AUTO:" not in ofs and "break" not in nfs[nfs.index("caseCONTROL:"):nfs.index("caseCONTROL_AUTO:")],
       "getFancyStats keeps the original's thirteen lines with their colours, keys and number formats (:444-499): heat, the four fuel lines, the three boiler lines, the CONTROL colour line falling through into CONTROL_AUTO's level line, the two heat exchanger lines and moderated last", bad_stats[:3])
    hover = nbody(st, CSCREEN, "public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks)")
    ck("V4.screen-hover-fix", "leftPos+86<=mouseX&&leftPos+86+150>mouseX&&topPos+11<mouseY&&topPos+11+150>=mouseY" in hover and "if(index>=0&&index<be.columns.length){" in hover
       and "guiTop+11+10150>=mouseY" in ov.b["gui.draw"] and "if(index>0&&index<console.columns.length){" in ov.b["gui.draw"],
       "NEO-only fix recorded: the grid hover uses the click handler's bounds and index >= 0, while the original reads guiTop + 11 + 10150 and index > 0 (GUIRBMKConsole.java:79, :82), so its top-left column never showed a tooltip")
    ck("V4.screen-misc", "publicbooleanisPauseScreen(){returnfalse;}" in code and "protectedvoidrenderLabels(GuiGraphicsguiGraphics,intmouseX,intmouseY){}" in code
       and "if(keyCode==GLFW.GLFW_KEY_ESCAPE)returnsuper.keyPressed(keyCode,scanCode,modifiers);" in code and "if(this.field.keyPressed(keyCode,scanCode,modifiers))returntrue;" in code
       and "publicbooleandoesGuiPauseGame(){returnfalse;}" in squash_lit(oc),
       "the screen does not pause the game, draws no labels, closes on escape and sends every other key to the focused field first (GUIRBMKConsole.java:443-459)")
    ck("V4.screen-client-package", "/inventory/screens/" in CSCREEN and "importnet.minecraft.client.gui.GuiGraphics;" in code,
       "RBMKConsoleScreen lives in the client screens package and uses the client GUI classes (only NuclearTechModClient refers to it, see V4.client-isolation)")


def v4_render(ck, inp, st):
    ov = need_ov(inp)
    orc = ov.b["ren.render"]
    oall = code_of(inp.o["ren"])
    rtext = lf(st.text(RCON))
    nall = code_of(rtext)
    nr = nbody(st, RCON, "public void render(RBMKConsoleBlockEntity be, MultiBufferSource buffer, float partialTicks)")
    # ---- rotation
    o_rot = {m[1]: m[2] for m in re.finditer(r"case(\d):GL11\.glRotatef\((\d+),0,1,0\);break;", orc)}
    n_rot = {m[1]: m[2] for m in re.finditer(r"case(\w+)->RenderContext\.mulPose\(Axis\.YP\.rotationDegrees\((\d+)\)\);", nr)}
    meta = {"2": "NORTH", "3": "SOUTH", "4": "WEST", "5": "EAST"}
    ck("V4.render-rotation", o_rot == {"2": "90", "4": "180", "3": "270", "5": "0"} and {meta[k]: v for k, v in o_rot.items()} == n_rot and "Direction facing = be.getBlockState().getValue(DummyableBlock.FACING);" in rtext,
       "the model is turned by the facing as the original's metadata switch (RenderRBMKConsole.java:30-36): meta 2 (north) 90, 4 (west) 180, 3 (south) 270, 5 (east) 0 degrees about +Y", (o_rot, n_rot))
    pairs = [("GL11.glTranslatef((float)x+0.5,(float)y,(float)z+0.5);", "RenderContext.translate(0.5,0,0.5);"), ("GL11.glTranslated(0.5,0,0);", "RenderContext.translate(0.5,0,0);"),
             ("bindTexture(ResourceManager.rbmk_console_tex);ResourceManager.rbmk_console.renderAll();", "bindTexture(ResourceManager.RBMK_CONSOLE_TEX);ResourceManager.rbmk_console.renderAll();"),
             ("doublekx=-0.3725;doubleky=-(i/15)*0.125+3.625;doublekz=-(i%15)*0.125+0.125*7;", "doublekx=-0.3725;doubleky=-(i/15)*0.125+3.625;doublekz=-(i%15)*0.125+0.125*7;"),
             ('if(col.data.hasKey("color")&&col.data.getByte("color")>=0){', 'if(col.data.contains("color")&&col.data.getShort("color")>=0){'),
             ('doubleheat=col.data.getDouble("heat")/col.data.getDouble("maxHeat");doublecolor=0.65+(i%2)*0.05;', 'doubleheat=col.data.getDouble("heat")/col.data.getDouble("maxHeat");doublecolor=0.65+(i%2)*0.05;'),
             ("(float)(color+((1-color)*heat)),(float)color,(float)color", "r=(float)(color+((1-color)*heat));g=(float)color;b=(float)color;"),
             ('if(col.data.getByte("indicator")>0)tess.setColorOpaque_F(1,1,0);', 'if(col.data.getByte("indicator")>0){r=1;g=1;b=0;}'),
             ('drawFuel(tess,kx+0.01,ky,kz,col.data.getDouble("enrichment"));', 'drawFuel(consumer,matrix,light,kx+0.01,ky,kz,col.data.getDouble("enrichment"));'),
             ('drawControl(tess,kx+0.01,ky,kz,col.data.getDouble("level"));', 'drawControl(consumer,matrix,light,kx+0.01,ky,kz,col.data.getDouble("level"));'),
             ('drawControlAuto(tess,kx+0.01,ky,kz,col.data.getDouble("level"));', 'drawControlAuto(consumer,matrix,light,kx+0.01,ky,kz,col.data.getDouble("level"));'),
             ("GL11.glTranslatef(-0.42,3.5,1.75);", "RenderContext.translate(-0.42,3.5,1.75);"),
             ("if(i%2==1)GL11.glTranslatef(0,0,1.75*-2);GL11.glTranslatef(0,-0.75*(i/2),0);", "if(i%2==1)RenderContext.translate(0,0,1.75*-2);RenderContext.translate(0,-0.75*(i/2),0);"),
             ('String[]parts=text.split("=");if(parts.length==2){text=I18nUtil.resolveKey(parts[0],parts[1]);}', 'String[]parts=text.split("=");if(parts.length==2){text=I18nUtil.resolveKey(parts[0],parts[1]);}'),
             ("floatf3=Math.min(0.03,0.8/Math.max(width,1));GL11.glScalef(f3,-f3,f3);", "floatf3=Math.min(0.03,0.8/Math.max(width,1));RenderContext.scale(f3,-f3,f3);"),
             ("GL11.glRotatef(90,0,1,0);", "RenderContext.mulPose(Axis.YP.rotationDegrees(90));"),
             ("font.drawString(text,-width/2,-height/2,0x00ff00);", "font.drawInBatch(text,-width/2,-height/2,0x00ff00,false,")]
    miss_o = [a for a, _ in pairs if a not in orc]
    miss_n = [b for _, b in pairs if b not in nr]
    ck("V4.render-constants", not miss_o and not miss_n,
       "the renderer keeps the original's numbers (RenderRBMKConsole.java:26-126): translate (0.5, 0, 0.5) then (0.5, 0, 0), the column squares at x -0.3725, y = -(i / 15) * 0.125 + 3.625, z = -(i % 15) * 0.125 + 0.875, the heat colour 0.65 + 0.05 * (i % 2) blended with the heat ratio, "
       "the yellow indicator, the dots at x + 0.01, the screen text at (-0.42, 3.5, 1.75), odd screens shifted by -3.5, rows by -0.75, the key=value text, scale min(0.03, 0.8 / width), rotate 90 degrees, centred, 0x00ff00", (miss_o, miss_n))
    o_hex = {m[1]: m[2] for m in re.finditer(r"if\(color==(\d)\)tess\.setColorOpaque_I\((0x\w+)\);", orc)}
    n_hex = {m[1]: m[2] for m in re.finditer(r"case(\d)->(0x\w+);", nr)}
    ck("V4.render-group-colours", o_hex == {"0": "0xFF0000", "1": "0xFFFF00", "2": "0x008000", "3": "0x0000FF", "4": "0x8000FF"} and o_hex == n_hex,
       "the five colour groups are drawn FF0000, FFFF00, 008000, 0000FF, 8000FF (RenderRBMKConsole.java:66-70)", (o_hex, n_hex))
    o_dots = re.findall(r"this\.drawDot\(tess,x,y,z,(.*?)\);", oall)
    n_dots = re.findall(r"drawDot\(consumer,matrix,light,x,y,z,(.*?)\);", nall)
    ck("V4.render-dot-colours", len(o_dots) == len(n_dots) == 3 and o_dots == n_dots == ["0F,0.25F+(float)(enrichment*0.75D),0F", "(float)level,(float)level,0F", "(float)level,0F,(float)level"],
       "the dots are FUEL / FUEL_SIM (0, 0.25 + 0.75 * enrichment, 0), CONTROL (level, level, 0) and CONTROL_AUTO (level, 0, level) (RenderRBMKConsole.java:148, :152, :156)", (o_dots, n_dots))
    o_dv = [split_args(m) for m in re.findall(r"tess\.addVertex\((.*?)\);", ov.b["ren.dot"])]
    n_dv = [split_args(m) for m in re.findall(r"vertex\(consumer,matrix,light,(.*?),r,g,b\);", nbody(st, RCON, "private static void drawDot(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b)"))]
    o_cv = [split_args(m) for m in re.findall(r"tess\.addVertex\((.*?)\);", ov.b["ren.column"])]
    n_cv = [split_args(m) for m in re.findall(r"vertex\(consumer,matrix,light,(.*?),r,g,b\);", nbody(st, RCON, "private static void drawColumn(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b)"))]
    ck("V4.render-quads", o_dv == n_dv and len(o_dv) == 12 and o_cv == n_cv and len(o_cv) == 4 and "doublewidth=0.0625*0.75;" in ov.b["ren.column"] and "doublewidth=0.0625*0.75;" in nbody(st, RCON, "private static void drawColumn(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b)")
       and "doublewidth=0.03125;doubleedge=0.022097;" in ov.b["ren.dot"] and "doublewidth=0.03125;doubleedge=0.022097;" in nbody(st, RCON, "private static void drawDot(VertexConsumer consumer, Matrix4f matrix, int light, double x, double y, double z, float r, float g, float b)"),
       "the column square (4 vertices, half-width 0.0625 * 0.75) and the dot (12 vertices, width 0.03125, edge 0.022097) have the original's vertices in the original order (RenderRBMKConsole.java:135-182)", (o_dv == n_dv, o_cv == n_cv))
    ck("V4.render-box", "returnbe.getRenderBoundingBox();" in nall and "publicclassRenderRBMKConsoleextendsBlockEntityRendererNT<RBMKConsoleBlockEntity>" in nall
       and "getViewDistance(){return256;}" in code_of(lf(read_text(ROOT / (J + "render/blockentity/BlockEntityRendererNT.java")))) and "return65536.0D;" in code_of(inp.o["con"]) and 65536.0 ** 0.5 == 256.0,
       "the renderer uses the block entity's render box (x - 2 .. x + 3, y .. y + 4) and the base renderer's 256 block view distance, the original's 65536 squared (TileEntityRBMKConsole.java:339-348)")
    # ---- item form
    lib = lf(otext(O + "render/item/ItemRenderLibrary.java"))
    ilib = sq(blank_comments(lib[lib.index("renderers.put(Item.getItemFromBlock(ModBlocks.rbmk_console)"):][:600]))
    item = nbody(st, RCON, "public BlockEntityWithoutLevelRenderer getRenderer()")
    ck("V4.render-item", "renderInventory(){GL11.glTranslated(0,-3,0);GL11.glScaled(2.5,2.5,2.5);}" in ilib and "bindTexture(ResourceManager.rbmk_console_tex);ResourceManager.rbmk_console.renderAll();" in ilib
       and "RenderContext.translate(0,-3,0);RenderContext.scale(2.5,2.5,2.5);" in item and "bindTexture(ResourceManager.RBMK_CONSOLE_TEX);ResourceManager.rbmk_console.renderAll();" in item
       and "returnNtmBlocks.RBMK_CONSOLE.asItem();" in nall,
       "the item draws the model with the console texture, lowered by 3 and scaled by 2.5 in the inventory (ItemRenderLibrary.java:669-678)")
    ck("V4.render-isolation", "import net.minecraft.client." in rtext and "RenderRBMKConsole" not in lf(st.text(NB)) and "RenderRBMKConsole" not in lf(st.text(BET)),
       "the renderer is client code and neither the block nor the block entity registry refers to it")


# ---------------------------------------------------------------- V5 recipes

# original ingredient expression -> (generated JSON ingredient(s) accepted, provider expression(s) accepted, registry id or None for a vanilla item / tag)
INGR = {
    "B.ingot()": ([{"item": "hbmsntm:ingot_boron"}], ["NtmItems.INGOT_BORON.get()"], "ingot_boron"),
    "ModBlocks.deco_rbmk": ([{"item": "hbmsntm:deco_rbmk"}], ["NtmBlocks.DECO_RBMK.get()"], "deco_rbmk"),
    "KEY_ANYPANE": ([{"tag": "c:glass_panes"}], ["Tags.Items.GLASS_PANES"], None),
    "DictFrame.fromOne(ModItems.circuit, EnumCircuitType.ANALOG)": ([{"item": "hbmsntm:circuit_analog_board"}], ["NtmItems.CIRCUIT_ANALOG_BOARD.get()"], "circuit_analog_board"),
    "PB.ingot()": ([{"item": "hbmsntm:ingot_lead"}], ["NtmItems.INGOT_LEAD.get()"], "ingot_lead"),
    "IRON.ingot()": ([{"item": "minecraft:iron_ingot"}, {"tag": "c:ingots/iron"}], ["Items.IRON_INGOT", "Tags.Items.INGOTS_IRON"], None)}
# name -> (category in the JSON, advancement folder, provider category, result holder, unlock id, original row attribute)
RECIPE_ROWS = {"rbmk_console": ("misc", "misc", "MISC", "NtmBlocks.RBMK_CONSOLE", "deco_rbmk", "console_row"),
               "rbmk_tool": ("equipment", "tools", "TOOLS", "NtmItems.RBMK_TOOL", "ingot_lead", "tool_row")}


def jload(st, path):
    return json.loads(st.text(path)) if st.has(path) else None


def expected_recipe(name, row):
    block, count, pattern, keys = row
    assert block == name
    return {"type": "minecraft:crafting_shaped", "category": RECIPE_ROWS[name][0], "key": {k: INGR[v][0][0] for k, v in keys.items()}, "pattern": pattern, "result": {"count": count, "id": "hbmsntm:" + name}}


def expected_advancement(name):
    u = RECIPE_ROWS[name][4]
    return {"parent": "minecraft:recipes/root",
            "criteria": {"has_" + u: {"conditions": {"items": [{"items": "hbmsntm:" + u}]}, "trigger": "minecraft:inventory_changed"},
                         "has_the_recipe": {"conditions": {"recipe": "hbmsntm:" + name}, "trigger": "minecraft:recipe_unlocked"}},
            "requirements": [["has_the_recipe", "has_" + u]], "rewards": {"recipes": ["hbmsntm:" + name]}}


def provider_rows(rp_text):
    """{recipe id: (category, holder, count, patterns, {key: expression})} of the console and tool rows of NtmRecipeProvider."""
    code = blank_comments(lf(rp_text))
    rows = {}
    for m in re.finditer(r"ShapedRecipeBuilder\.shaped\(RecipeCategory\.(\w+), (Ntm(?:Blocks|Items)\.\w+)\.get\(\), (\d+)\)(.*?)\.save\(recipeOutput, ResourceLocation\.fromNamespaceAndPath\(\"hbmsntm\", \"(\w+)\"\)\);", code, re.S):
        if m[5] not in RECIPE_ROWS:
            continue
        lines = [x.strip() for x in m[4].split("\n") if x.strip()]
        pattern = [re.fullmatch(r'\.pattern\("([^"]*)"\)', x)[1] for x in lines if x.startswith(".pattern(")]
        defines = {}
        for x in lines:
            d = re.fullmatch(r"\.define\('(\w)', (.*)\)", x)
            if d:
                defines[d[1]] = d[2]
        un = [re.fullmatch(r'\.unlockedBy\("(\w+)", has\((.*)\)\)', x) for x in lines if x.startswith(".unlockedBy(")]
        rows.setdefault(m[5], []).append((m[1], m[2], int(m[3]), pattern, defines, un[0][1] if un else None, un[0][2] if un else None))
    return rows


def v5_recipes(ck, inp, st):
    need_ov(inp)
    rows = {n: getattr(inp, RECIPE_ROWS[n][5]) for n in RECIPE_ROWS}
    ck("V5.original-rows", rows["rbmk_console"][0] == "rbmk_console" and rows["rbmk_tool"][0] == "rbmk_tool" and all(r[1] == 1 for r in rows.values()) and all(v in INGR for r in rows.values() for v in r[3].values()),
       "the two original rows (CraftingManager.java:989 and ToolRecipes.java:133) each make one of their item and every ingredient expression has a NEO mapping in this script", [(n, [v for v in r[3].values() if v not in INGR]) for n, r in rows.items()])
    if not all(v in INGR for r in rows.values() for v in r[3].values()):
        return
    bad = {}
    for n in RECIPE_ROWS:
        got, want = jload(st, RECIPES + n + ".json"), expected_recipe(n, rows[n])
        if got != want:
            bad[n] = (got, want)
    ck("V5.recipes-match", not bad, "each generated recipe is a minecraft:crafting_shaped with the original row's pattern, count 1, the result and each ingredient mapped to the NEO item or tag: rbmk_console BBB / DGD / DCD (B boron ingot, D deco_rbmk, G any glass pane = c:glass_panes, "
       "C analog circuit = circuit_analog_board; CraftingManager.java:989, the !enable528 branch = default configuration); rbmk_tool ` A `, ` IA`, `I  ` (A lead ingot, I iron ingot; ToolRecipes.java:133)", {k: v for k, v in list(bad.items())[:2]})
    bad = {}
    for n, (cat, folder, *_rest) in RECIPE_ROWS.items():
        got = jload(st, ADV + folder + "/" + n + ".json")
        if got != expected_advancement(n):
            bad[n] = (got, expected_advancement(n))
    ck("V5.advancements", not bad, "each recipe has its recipe-book advancement (parent recipes/root, an inventory_changed criterion for the unlock item, the recipe_unlocked criterion, requirements, reward): rbmk_console under recipes/misc unlocked by deco_rbmk, rbmk_tool under recipes/tools unlocked by ingot_lead",
       {k: v for k, v in list(bad.items())[:2]})
    ck("V5.unlock-is-ingredient", all(("hbmsntm:" + RECIPE_ROWS[n][4]) in [i.get("item") for v in (jload(st, RECIPES + n + ".json") or {"key": {}})["key"].values() for i in (v if isinstance(v, list) else [v])] for n in RECIPE_ROWS),
       "each recipe's unlock item is one of its own ingredients")
    new = sorted(p for p in st.tree if p.startswith(RECIPES) and p not in inp.base_files)
    new_adv = sorted(p for p in st.tree if p.startswith(ADV) and p not in inp.base_files)
    changed = sorted(p for p in st.tree if (p.startswith(RECIPES) or p.startswith(ADV)) and p in inp.base_files and st.tree[p] != inp.base_files[p])
    ck("V5.only-two", new == sorted(RECIPES + n + ".json" for n in RECIPE_ROWS) and new_adv == sorted(ADV + f + "/" + n + ".json" for n, (_, f, *_r) in RECIPE_ROWS.items()) and not changed,
       "exactly two recipes and two advancements were added and no existing generated recipe or advancement changed (no anvil row exists for either item in the original)", (new, new_adv, changed))
    prov = provider_rows(st.text(RP))
    bad = {}
    for n, (cat, folder, pcat, holder, unlock, _attr) in RECIPE_ROWS.items():
        r = rows[n]
        got = prov.get(n)
        want = (pcat, holder, r[1], r[2], {k: INGR[v][1] for k, v in r[3].items()})
        if not got or len(got) != 1 or got[0][:4] != want[:4] or any(got[0][4].get(k) not in opts for k, opts in want[4].items()) or set(got[0][4]) != set(want[4]):
            bad[n] = (got, want)
    ck("V5.provider-rows", len(prov) == 2 and not bad, "NtmRecipeProvider registers the two shaped rows once each with the original patterns, count 1, the mapped ingredient expressions and the recipe ids hbmsntm:rbmk_console / hbmsntm:rbmk_tool", {k: v for k, v in list(bad.items())[:2]})
    badu = {n: prov[n][0][5:] for n in RECIPE_ROWS if n in prov and prov[n][0][5] != "has_" + RECIPE_ROWS[n][4]}
    ck("V5.provider-unlocks", not badu and len(prov) == 2, "each provider row unlocks on has_<unlock item> of the item the generated advancement names", badu)
    ids_items, ids_blocks = lf(st.text(NITEMS)), lf(st.text(NB))
    missing = []
    for n in RECIPE_ROWS:
        for ing in rows[n][3].values():
            rid = INGR[ing][2]
            if rid is not None and f'register("{rid}"' not in ids_items and f'register("{rid}"' not in ids_blocks:
                missing.append((n, rid))
        if f'register("{n}"' not in ids_blocks and f'register("{n}"' not in ids_items:
            missing.append((n, "result"))
    ck("V5.ids-registered", not missing, "every NEO item and block id the two recipes use or make is registered in NtmItems or NtmBlocks", missing)
    anvil = J + "inventory/recipes/anvil/AnvilRecipes.java"
    ck("V5.anvil-untouched", hashed_equal(inp, st, anvil) and not re.search(r"RBMK_CONSOLE|RBMK_TOOL", blank_comments(st.text(anvil))),
       "AnvilRecipes.java is byte-equal to the start copy and has no console or tool row (the original has no anvil row for them)")


# ---------------------------------------------------------------- V6 datagen outputs

def expected_loot(n):
    return {"type": "minecraft:block", "pools": [{"bonus_rolls": 0.0, "conditions": [{"condition": "minecraft:survives_explosion"}], "entries": [{"type": "minecraft:item", "name": "hbmsntm:" + n}], "rolls": 1.0}], "random_sequence": "hbmsntm:blocks/" + n}


def line_delta(start, live):
    """(added, removed) Counters of the stripped non-blank, non-comment lines of live against start (alignment independent)."""
    def lines(t):
        return collections.Counter(x.strip() for x in lf(t).split("\n") if x.strip() and not x.strip().startswith(("//", "*", "/*")))
    a, b = lines(start), lines(live)
    return b - a, a - b


def v6_datagen(ck, inp, st):
    need_ov(inp)
    new = sorted(p for p in st.tree if p.startswith(GEN) and p not in inp.base_files)
    ck("V6.added-files", new == sorted(GEN_NEW), "exactly 9 generated files were added: blockstate, particle block model, item model and loot table of the console, the tool's item model, and the two recipes and two advancements",
       (sorted(set(new) ^ set(GEN_NEW))[:6], len(new)))
    changed = sorted(p for p in st.tree if p.startswith(GEN) and p in inp.base_files and st.tree[p] != inp.base_files[p])
    gone = sorted(p for p in inp.base_files if p.startswith(GEN) and p not in st.tree)
    ck("V6.changed-files", changed == sorted(GEN_CHANGED) and not gone, "of the generated files that existed at the start only the migration stamp, en_us.json, the pickaxe tag and sounds.json changed, and none was deleted", (changed, gone))
    # ---- the models
    ck("V6.blockstate", jload(st, G_STATE + "rbmk_console.json") == {"variants": {"": {"model": "hbmsntm:block/rbmk_console_particle"}}},
       "the console's blockstate is a single variant pointing at the particle-only block model (the console is drawn by its renderer, like the Zirnox: machine_zirnox.json)", jload(st, G_STATE + "rbmk_console.json"))
    ck("V6.block-model", jload(st, G_BMODEL + "rbmk_console_particle.json") == {"textures": {"particle": "hbmsntm:block/rbmk/rbmk_console"}},
       "the particle block model names the block icon rbmk/rbmk_console as the break particle (ModBlocks.java:2131 setBlockTextureName rbmk/rbmk_console)", jload(st, G_BMODEL + "rbmk_console_particle.json"))
    ck("V6.item-models", jload(st, G_IMODEL + "rbmk_console.json") == {"parent": "minecraft:builtin/entity", "gui_light": "side"} and jload(st, G_IMODEL + "rbmk_tool.json") == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/rbmk_tool"}},
       "the console item is rendered by its item renderer (builtin/entity, as the Zirnox: machine_zirnox.json) and the tool is a flat item/generated with textures/item/rbmk_tool.png", (jload(st, G_IMODEL + "rbmk_console.json"), jload(st, G_IMODEL + "rbmk_tool.json")))
    ck("V6.loot-table", jload(st, G_LOOT + "rbmk_console.json") == expected_loot("rbmk_console"), "the console drops itself (dropSelf: one roll, survives_explosion, random_sequence hbmsntm:blocks/rbmk_console); the original has no drop override", jload(st, G_LOOT + "rbmk_console.json"))
    ck("V6.model-textures-exist", ICON_PNG in st.tree and ITEM_PNG in st.tree and png_size(st.files.get(ICON_PNG, b"")) == [16, 16] and png_size(st.files.get(ITEM_PNG, b"")) == [16, 16],
       "the textures the new models name exist under assets/hbmsntm/textures (block/rbmk/rbmk_console.png and item/rbmk_tool.png, both 16 x 16)")
    # ---- pickaxe tag
    pk, pk0 = jload(st, PICK), json.loads(inp.start[PICK])
    vals, vals0 = pk["values"], pk0["values"]
    ck("V6.pickaxe-tag", pk.get("replace", False) == pk0.get("replace", False) and collections.Counter(vals) == collections.Counter(vals0) + collections.Counter(["hbmsntm:rbmk_console"]) and [v for v in vals if v in vals0] == vals0
       and vals.index("hbmsntm:rbmk_console") == vals.index("hbmsntm:rbmk_loader") + 1,
       "the pickaxe tag holds the start values in their order plus hbmsntm:rbmk_console right after rbmk_loader (the original console is iron material: pickaxe)", (sorted(set(vals) ^ set(vals0))[:6]))
    # ---- sounds.json
    sj, sj0 = json.loads(st.text(SJSON)), json.loads(inp.start[SJSON])
    new_keys = sorted(set(sj) - set(sj0))
    ck("V6.sounds-json", new_keys == ["block.shutdown"] and sj.get("block.shutdown") == {"sounds": [{"name": "hbmsntm:block/shutdown", "stream": True}]} and all(sj[k] == sj0[k] for k in sj0) and set(sj0) <= set(sj)
       and len(sj) == len(sj0) + 1 and list(sj) == sorted(sj) and list(sj0) == sorted(sj0) and "block.rbmk_az5_cover" in sj,
       "the generated sounds.json gains exactly block.shutdown (hbmsntm:block/shutdown, stream true; the original sounds.json:7) in sorted position and every start entry is unchanged", (new_keys, sj.get("block.shutdown")))
    # ---- providers: additive
    want_add = {
        BSP: ['this.particleOnlyBlock(NtmBlocks.RBMK_CONSOLE, modLoc("block/rbmk/rbmk_console"));'],
        IMP: ["this.basicItem(NtmItems.RBMK_TOOL.get());"],
        LOOT: ["this.dropSelf(NtmBlocks.RBMK_CONSOLE.get());"],
        TAGP: ["NtmBlocks.RBMK_CONSOLE.get(),"]}
    badp = {}
    for path, want in want_add.items():
        add, rem = line_delta(inp.start[path], lf(st.text(path)))
        if sorted(add.elements()) != sorted(want) or rem:
            badp[path.rsplit("/", 1)[1]] = (sorted(add.elements())[:4], sorted(rem.elements())[:3])
    ck("V6.providers-additive", not badp, "NtmBlockStateProvider (particleOnlyBlock for the console, as the Zirnox), NtmItemModelProvider (basicItem for the tool), NtmBlockLootTableProvider (dropSelf) and NtmBlockTagProvider (the pickaxe entry) differ from their start copies by those lines only (plus comments); nothing was removed", badp)
    for path in (BSP, IMP, LOOT, TAGP):
        dele, _ = diff_summary(inp.start[path], lf(st.text(path)))
        if dele:
            badp[path.rsplit("/", 1)[1] + ":removed"] = dele[:3]
    ck("V6.providers-no-removals", not [k for k in badp if k.endswith(":removed")], "no line or comment of the four datagen providers was removed", [k for k in badp if k.endswith(":removed")])
    # ---- the migration stamp
    stamp = jload(st, STAMP)
    stale = sorted(k for k in set(stamp["inputs"]) | set(inp.stamp_now) if stamp["inputs"].get(k) != inp.stamp_now.get(k))
    ck("V6.stamp-inputs-fresh", not stale and stamp["version"] == 1, "migration-stamp.json records, for every src/main/java and src/main/resources input and the build files, the hash the Gradle rule gives today (text files are hashed with LF line endings); a mismatch means runData was not rerun after the edit", stale[:6])
    gen_stale = sorted(k for k in set(stamp["generated"]) | set(inp.gen_now) if stamp["generated"].get(k) != inp.gen_now.get(k))
    ck("V6.stamp-generated-fresh", not gen_stale, "the stamp's generated hashes equal the files in src/generated/resources (the 9 added files, en_us.json, the pickaxe tag and sounds.json included)", gen_stale[:6])

    def fp(d):
        return hashlib.sha256("".join(f"{k}{chr(0)}{v}{chr(10)}" for k, v in d.items()).encode("utf-8")).hexdigest()
    ck("V6.stamp-fingerprints", fp(stamp["inputs"]) == stamp["inputFingerprint"] and fp(stamp["generated"]) == stamp["generatedFingerprint"],
       "the stamp's two fingerprints are the SHA-256 of its own input and generated entries (path, NUL, hash, newline, as gradle/migration-resources.gradle:144-147), so the file was not edited by hand",
       (fp(stamp["inputs"]) == stamp["inputFingerprint"], fp(stamp["generated"]) == stamp["generatedFingerprint"]))


# ---------------------------------------------------------------- V7 language

def jstr(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def provider_line(key, text):
    if key == "block.hbmsntm.rbmk_console":
        return f"this.add(NtmBlocks.RBMK_CONSOLE, {jstr(text)});"
    if key == "item.hbmsntm.rbmk_tool":
        return f"this.add(NtmItems.RBMK_TOOL, {jstr(text)});"
    if key == "item.hbmsntm.rbmk_tool.desc":
        return f"this.add(NtmItems.RBMK_TOOL, DESC, {jstr(text)});"
    if key in ("item.hbmsntm.rbmk_tool.linked", "item.hbmsntm.rbmk_tool.set"):
        return f"this.add(NtmItems.RBMK_TOOL, \".{key.rsplit('.', 1)[1]}\", {jstr(text)});"
    return f"this.add({jstr(key)}, {jstr(text)});"


ASSIGN = "rbmk.console.assign"


def expected_lang(inp):
    """[(NEO key, kind, source key, source en, source zh, target en, target zh)]: 22 upstream keys (target = source), rbmk.console.assign (local, with its upstream source) and the 27 local ones."""
    # rbmk.console.assign is a local adaptation of an upstream key: the original Chinese (zh_CN.lang:4296) lacks the `%s` of en_US.lang:5000, NEO appends " #%s"
    exp = [(nk, "local" if nk == ASSIGN else "upstream", ok, inp.o_en[ok][0][0], inp.o_zh[ok][0][0], inp.o_en[ok][0][0], inp.o_zh[ok][0][0] + (" #%s" if nk == ASSIGN else "")) for nk, ok, _, _ in UP]
    exp += [(nk, "local", None, None, None, en, zh) for nk, (en, zh, _line) in LOCAL.items()]
    return exp


def cited(reason, line):
    for m in re.finditer(r"GUIRBMKConsole\.java:(\d+)(?:-(\d+))?", str(reason)):
        a, b = int(m[1]), int(m[2] or m[1])
        if a <= line <= b:
            return True
    return False


def v7_lang(ck, inp, st):
    need_ov(inp)
    exp = expected_lang(inp)
    keys = [e[0] for e in exp]
    n_up = sum(1 for e in exp if e[1] == "upstream")
    n_loc = len(exp) - n_up
    ck("V7.expected-keys", len(exp) == NEW_COUNT == 50 and len(set(keys)) == 50 and n_up == 22 and n_loc == 28 and sorted(keys) == NEW_KEYS,
       "50 keys are expected: 22 upstream (block name, 4 tool keys, rbmk.heat, 6 console, moderated, 4 rod, 5 screen: the original English and Chinese lines are the NEO text) and 28 local (rbmk.console.assign, select all, deselect all, compressor, 10 colour group tips, 14 column type names)")
    gl = inp.ol["gui"]
    bad = [(k, line) for k, (e, _z, line) in LOCAL.items() if not k.startswith("rbmk.console.type.") and e not in gl[line - 1]]
    ck("V7.original-tooltips", not bad and all("toString" in gl[87] for _ in [0]) and list(enum_members(inp.o["con"], "ColumnType")) == [t[1] for t in TYPES] and len({t[2] for t in TYPES}) == 14,
       "the local English texts are the hard-coded strings of GUIRBMKConsole (:95-96, :106-111) and the column type names shown by col.type.toString() (:88), the 14 ColumnType names", bad[:3])
    lp = lf(st.text(LP))
    want_lines = {nk: provider_line(nk, ten) for nk, kind, sk, sen, szh, ten, tzh in exp}
    lpl = [l.strip() for l in lp.split("\n")]
    ck("V7.provider", all(lpl.count(l) == 1 for l in want_lines.values()), "NtmLanguageProvider adds the 50 keys once each with the English text (the block and tool through their registry holders)", [l for l in want_lines.values() if lpl.count(l) != 1][:4])
    add, rem = line_delta(inp.start[LP], lp)
    ck("V7.provider-insert-only", not rem and sorted(add.elements()) == sorted(want_lines.values()), "the provider differs from its start copy only by these 50 added lines (plus comments); nothing was removed", (sorted(rem.elements())[:3], sorted(set(add.elements()) ^ set(want_lines.values()))[:4]))
    en, en_dups = json_pairs(st.text(EN))
    en0, _ = json_pairs(inp.start[EN])
    zh_text = st.text(ZH)
    zh, zh_dups = json_pairs(zh_text)
    zh0, _ = json_pairs(inp.start[ZH])
    ck("V7.en-values", not en_dups and all(en.get(e[0]) == e[5] for e in exp), "generated en_us.json has the 50 keys with the provider's English and no duplicate key", [(e[0], en.get(e[0]), e[5]) for e in exp if en.get(e[0]) != e[5]][:3])
    changed_en = sorted(k for k in set(en) | set(en0) if en.get(k) != en0.get(k))
    ck("V7.en-only-these", changed_en == sorted(keys) and len(en) == len(en0) + 50, f"en_us.json changed only in the 50 new keys and holds {len(en0) + 50} keys ({len(en0)} at the start)", (changed_en[:5], len(en), len(en0)))
    ck("V7.zh-values", not zh_dups and all(zh.get(e[0]) == e[6] for e in exp), "zh_cn.json has the 50 keys: the 22 upstream values verbatim from zh_CN.lang, rbmk.console.assign as the original Chinese plus ` #%s`, the 27 other local ones as the handoff gives them", [(e[0], zh.get(e[0]), e[6]) for e in exp if zh.get(e[0]) != e[6]][:3])
    changed_zh = sorted(k for k in set(zh) | set(zh0) if zh.get(k) != zh0.get(k))
    ck("V7.zh-only-these", changed_zh == sorted(keys) and len(zh) == len(zh0) + 50, f"zh_cn.json changed in nothing but the 50 new keys and holds {len(zh0) + 50} keys ({len(zh0)} at the start)", (changed_zh[:5], len(zh), len(zh0)))
    ordered, ordered0 = list(zh.keys()), list(zh0.keys())
    ck("V7.zh-order", (ordered == sorted(ordered)) if ordered0 == sorted(ordered0) else [k for k in ordered if k in zh0] == ordered0, "zh_cn.json keeps its key order (sorted when the start copy is sorted; else the start order with the new keys inserted)")
    ph = lambda s: (sorted(re.findall(r"%(?:\d+\$)?[sd]", s)), s.count("$"))  # noqa: E731
    ck("V7.placeholders", all(ph(en.get(e[0], "")) == ph(zh.get(e[0], "")) for e in exp), "every new key, rbmk.console.assign included, keeps the same placeholders and `$` line breaks in English and Chinese (tools/migration/localization.py rejects a mismatch)", [e[0] for e in exp if ph(en.get(e[0], "")) != ph(zh.get(e[0], ""))][:4])
    ck("V7.assign-local", "%s" in en.get(ASSIGN, "") and zh.get(ASSIGN) == inp.o_zh[ASSIGN][0][0] + " #%s" and "%s" not in inp.o_zh[ASSIGN][0][0] and en.get(ASSIGN) == inp.o_en[ASSIGN][0][0],
       "rbmk.console.assign: the English is the original (en_US.lang:5000, `#%s`), the Chinese is the original zh_CN.lang:4296 text (no `%s`) plus ` #%s`, so both languages carry the screen number placeholder")
    ck("V7.upstream-verbatim", all(e[1] != "upstream" or (zh.get(e[0]) == inp.o_zh[e[2]][0][0] and en.get(e[0]) == inp.o_en[e[2]][0][0]) for e in exp), "the 22 upstream values equal en_US.lang / zh_CN.lang byte for byte")
    map_text = st.text(MAP)
    ck("V7.crlf", zh_text.count("\r\n") == zh_text.count("\n") > 0 and inp.start[ZH].count("\r\n") == inp.start[ZH].count("\n") and zh_text.count("\r\n") - inp.start[ZH].count("\r\n") == 50
       and "\r\n" not in st.text(EN) and format_ok(zh_text, zh) and map_text.count("\r\n") == map_text.count("\n") > 0 and format_ok(map_text, json.loads(map_text))
       and map_text.count("\r\n") - inp.start[MAP].count("\r\n") == sum(8 if e[1] == "upstream" else (9 if e[0] == ASSIGN else 6) for e in exp),
       "zh_cn.json grew by exactly 50 CRLF lines with no lone LF, zh_cn-map.json keeps CRLF and the standard layout (8 lines per upstream, 6 per local and 9 for the sourced local rbmk.console.assign entry added), en_us.json stays LF",
       (zh_text.count("\r\n"), zh_text.count("\n"), inp.start[ZH].count("\r\n"), map_text.count("\r\n"), map_text.count("\n")))
    mp, mp0 = json.loads(map_text), json.loads(inp.start[MAP])
    entries, entries0 = mp["entries"], mp0["entries"]
    bad = {}
    for nk, kind, sk, sen, szh, ten, tzh in exp:
        e = entries.get(nk)
        if e is None or e.get("kind") != kind or e.get("target_en") != ten or e.get("target_zh") != tzh:
            bad[nk] = e
        elif kind == "upstream" and e != {"kind": "upstream", "source_en": sen, "source_key": sk, "source_zh": szh, "target_en": ten, "target_zh": tzh}:
            bad[nk] = e
        elif nk == ASSIGN and (set(e) != {"kind", "reason", "source_en", "source_key", "source_zh", "target_en", "target_zh"} or (e["source_en"], e["source_key"], e["source_zh"]) != (sen, sk, szh)
                               or not all(c in str(e["reason"]) for c in ("zh_CN.lang:4296", "en_US.lang:5000"))):
            bad[nk] = e
        elif kind == "local" and nk != ASSIGN and (not str(e.get("reason", "")).strip() or set(e) != {"kind", "reason", "target_en", "target_zh"}):
            bad[nk] = e
    ck("V7.map-entries", not bad, "the mapping has one entry per key: upstream entries carry source_key / source_en / source_zh from the original and the NEO text; local entries carry a reason; rbmk.console.assign is local with its original source_* fields and a reason citing zh_CN.lang:4296 and en_US.lang:5000", dict(list(bad.items())[:3]))
    badr = [k for k, (_e, _z, line) in LOCAL.items() if not cited(entries.get(k, {}).get("reason", ""), line)]
    ck("V7.map-local-reasons", not badr and len(LOCAL) == 27, "the 27 local entries' reasons cite the GUIRBMKConsole.java line that holds their text (:95, :96, :106-110, :111, :88)", badr)
    changed_map = sorted(k for k in set(entries) | set(entries0) if entries.get(k) != entries0.get(k))
    kinds, kinds0 = collections.Counter(e["kind"] for e in entries.values()), collections.Counter(e["kind"] for e in entries0.values())
    ck("V7.map-only-these", changed_map == sorted(keys) and mp["source_commit"] == mp0["source_commit"] and mp["schema_version"] == mp0["schema_version"] and len(entries) == len(entries0) + 50
       and kinds["upstream"] - kinds0["upstream"] == 22 and kinds["local"] - kinds0["local"] == 28 and kinds["deferred"] == kinds0["deferred"],
       f"the mapping changed only in the 50 new entries (22 upstream, 28 local) and holds {len(entries0) + 50} entries; deferred, source_commit and schema_version unchanged", (changed_map[:5], dict(kinds), dict(kinds0)))
    ordered = list(entries.keys())
    ck("V7.map-sorted", ordered == sorted(ordered) and list(entries0.keys()) == sorted(entries0.keys()), "the mapping keeps its sorted key order")
    ck("V7.map-matches-files", all(entries[k].get("target_en") == en.get(k) and entries[k].get("target_zh") == zh.get(k) for k in keys if k in entries), "for the 50 keys the mapping's target English / Chinese equal the generated en_us.json and zh_cn.json values")
    ck("V7.start-copies-consistent", not [k for k in keys if k in en0 or k in zh0 or k in entries0], "none of the 50 keys existed in the start copies of en_us.json, zh_cn.json and the mapping")
    ck("V7.no-container-key", not [k for k in en if "rbmkConsole" in k] and not [k for k in zh if "rbmkConsole" in k], "there is no container.rbmkConsole key: the original GUI has no title and the menu title is the block name")


# ---------------------------------------------------------------- V8 resources

def v8_resources(ck, inp, st):
    need_ov(inp)
    own = json.loads(st.text(OWN))
    assets = own["assets"]
    targets = [RES + n for _, n in IMPORTS]
    ck("V8.record", len(assets) == 6 and own.get("batch") == "Goal24E" and own.get("source_commit") == ORIGINAL_HEAD and own.get("kind") == "import" and sorted(a["target_path"] for a in assets) == sorted(targets)
       and str(own.get("note", "")).strip() != "" and format_ok(st.text(OWN), own),
       "migration/goal24e-resource-ownership.json (batch Goal24E, kind import, original at aee05a40f) lists the 6 imported files, in the standard JSON layout", (len(assets), own.get("batch"), own.get("source_commit")))
    bad = [t for t in targets if t not in st.files or t not in inp.o_res or st.files[t] != inp.o_res[t] or sha(st.files[t]) != sha(inp.o_res[t])]
    ck("V8.bytes-equal-original", not bad, "each of the 6 NEO files (console OBJ, console model texture, GUI, block icon, tool icon, shutdown.ogg) is byte-equal (SHA-256) to the original working-tree file (the OBJ is the CRLF worktree bytes)", bad[:5])
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
    ck("V8.record-matches", not bad_rec and not bad_png and not bad_text, "each record entry's source and target path, SHA-256 (source = target = file), byte count and PNG size (none for .obj and .ogg) equal the file; target paths are lowercase; description and ownership text are present", (bad_rec[:3], bad_png[:3], bad_text[:3]))
    ck("V8.last-commit", "error" not in inp.last_commit and not bad_commit and len(inp.last_commit) == 6, "source_last_change_commit equals `git log -1 --format=%H -- <path>` in the original for all 6", (bad_commit[:3], inp.last_commit.get("error")))
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
    ctl = RES + "textures/block/rbmk/rbmk_control.png"
    ck("V8.not-imported", len(ni) == 1 and ni[0].get("source_path") == O_RES + "textures/blocks/rbmk/rbmk_control.png" and ni[0].get("present_in_original") is True and str(ni[0].get("reason", "")).strip() != ""
       and "Goal24A" in str(ni[0].get("reason")) and ctl in st.tree and hashed_equal(inp, st, ctl) and ctl not in {a["target_path"] for a in assets},
       "not_imported lists the rbmk_control.png head texture (a different file from the console's model texture textures/models/machines/rbmk_control.png) with its reason: it is the Goal24A file, unchanged in NEO", ni[:1])
    ck("V8.gui-texture", png_size(st.files.get(GUI_PNG, b"")) == [256, 256] and png_size(st.files.get(TEX_PNG, b"")) == [202, 174],
       "the console GUI texture is a 256 x 256 PNG (the default blit atlas size the screen's rectangles assume) and the model texture is 202 x 174", (png_size(st.files.get(GUI_PNG, b"")), png_size(st.files.get(TEX_PNG, b""))))
    base_res = {p for p in inp.base_files if p.startswith(RES)}
    new_res = {p for p in st.tree if p.startswith(RES) and p not in base_res}
    changed_res = [p for p in base_res if st.tree.get(p) != inp.base_files[p]]
    ck("V8.no-unlisted", new_res == set(targets) and changed_res == [ZH], "the new files under assets/hbmsntm are exactly the 6 listed imports and the only existing resource that changed is zh_cn.json", (sorted(new_res ^ set(targets))[:5], changed_res[:5]))
    ck("V8.ogg-header", st.files.get(OGG, b"")[:4] == b"OggS", "shutdown.ogg is an Ogg stream (the sound definition points at it)")


# ---------------------------------------------------------------- V9 scope

ALLOWED_MIGRATION = ("migration/goal24e-", "migration/GOAL24")
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md", "migration/RESOURCE-OWNERSHIP.md"}


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v9_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    imports = [RES + n for _, n in IMPORTS]
    expected = set(NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, OWN, PICK, SJSON, GT] + imports + gen_new)
    extra = [p for p in changed if p not in expected and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V9.no-extra-paths", not extra, "every changed src/ and migration/ path since the start belongs to the batch: the new and edited production files, the language files, the 6 imports, the generated outputs, the GameTest file and the migration records", extra[:10])
    ck("V9.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != GT]
    ck("V9.expected-all-changed", not never, "every expected production, resource and generated path really differs from the start (the GameTest file is checked in V10)", never[:5])
    ck("V9.counts", len(NEW_CLASSES) == 6 and len(EDITED) == 16 and len(imports) == 6 and len(gen_new) == 9 and len(set(NEW_CLASSES + EDITED)) == 22,
       "6 new production classes, 16 edited production files, 6 imported resources, 9 new generated files", (len(NEW_CLASSES), len(EDITED), len(imports), len(gen_new)))
    ck("V9.new-classes-new", all(p not in inp.base_files for p in NEW_CLASSES + [OWN]) and all(p in inp.base_files for p in EDITED), "the 6 new classes and the ownership record did not exist at the start and the 16 edited files did")
    ck("V9.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED), "the earlier RBMK, network, multiblock and recipe files outside this batch are byte-equal to the start", [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    others = [p for p in inp.baseline["copied_scope"] if p.endswith(".java") and p not in EDITED and p not in UNTOUCHED and p != GT]
    ck("V9.older-gametests-untouched", all(hashed_equal(inp, st, p) for p in others if "/gametest/" in p), "the older GameTest classes among the start copies (RBMKCoreGameTests, RBMKFuelGameTests, RBMKReactorGameTests, RBMKControlSteamGameTests, SmokeTestSupport) are byte-equal to the start", [p.rsplit("/", 1)[1] for p in others if "/gametest/" in p and not hashed_equal(inp, st, p)])
    bad, eol = {}, []
    for p in EDITED:
        live = st.text(p)
        dele, _ = diff_summary(inp.start[p], live)
        if dele:
            bad[p.rsplit("/", 1)[1]] = [x[:100] for x in dele][:3]
        if ("\r\n" in inp.start[p]) != ("\r\n" in live) or live.count("\r\n") not in (0, live.count("\n")):
            eol.append(p)
    ck("V9.edited-additive", not bad, "the 16 edited production files differ from their start copies by additions only: no line and no comment of the start was removed", bad)
    ck("V9.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF, no mixed lines)", eol)
    rest = sorted(p for p in changed if p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT)
    ck("V9.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V9.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V10 / V11 / V12

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")
GT_AREAS = ("layout", "tool", "scan", "screens", "level", "color", "screen_control", "az5", "flux", "nbt", "sync", "recipes")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


@functools.lru_cache(maxsize=1)
def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name)


def v10_gametest(ck, inp, st):
    ck("V10.other-tests", other_gametests() == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests (counted by @GameTest( in every other class of the gametest package)", other_gametests())
    ck("V10.present", st.has(GT), "RBMKConsoleGameTests.java exists (written by the GameTest verifier)")
    if not st.has(GT):
        return dict(rbmk_console_tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V10.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "RBMKConsoleGameTests has @GameTest methods, each public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = []
    for args in tests.values():
        m = re.search(r"batch\s*=\s*([^,)]+)", args)
        batches.append(m[1].strip().strip('"') if m else None)
    ck("V10.own-batch", len(tests) >= 1 and None not in batches and len(set(batches)) == len(batches), "every test has its own batch (the neutron StreamWorld, the chunk radiation and the fluid networks are per level and shared by simultaneous tests)", batches)
    ck("V10.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "RBMKConsoleGameTests is a @GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false), like the other RBMK GameTests")
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
    ck("V10.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKConsoleGameTests references no client class")
    return dict(rbmk_console_tests=sorted(tests))


def v11_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    # the expected total is counted from the @GameTest annotations of the source files (the other classes plus this one), not taken from a literal
    total = other_gametests() + gametest_total([live])
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V11.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({other_gametests()} in the other classes + {len(tests)} RBMKConsoleGameTests, counted from the @GameTest annotations)", (match and match[0], total))
    ck("V11.annotation-total", other_gametests() == START_GAMETESTS and gametest_total([live]) == len(tests), f"the other classes hold the {START_GAMETESTS} start tests and every @GameTest( of RBMKConsoleGameTests is a method of the form checked in V10 ({len(tests)})")
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
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files and not p.endswith("/.migration-stamp.json")]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes if c + ".class" not in names]
        short = {}
        for c, p in classes.items():
            have = len([n for n in names if n.startswith(c + "$") and n.endswith(".class")])
            if have < inner_expected(st.text(p)):
                short[c] = (have, inner_expected(st.text(p)))
        ck("V12.classes", not missing, "the JAR has the 6 new production classes and RBMKConsoleGameTests", missing)
        ck("V12.inner-classes", not short, "the JAR has at least as many inner/anonymous classes as the sources declare", short)
        res = [RES + n for _, n in IMPORTS]
        bad = [p for p in res if p[len("src/main/resources/"):] not in names or jar.read(p[len("src/main/resources/"):]) != st.files.get(p)]
        ck("V12.resources", not bad and len(res) == 6, "the 6 imported OBJ, textures and sound in the JAR are byte-equal to the source files", bad[:5])
        gbad = [p for p in gen_new + [EN, PICK, SJSON] if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V12.generated", not gbad and len(gen_new) == 9, "the 9 new generated blockstate, models, loot table, recipes and advancements, en_us.json, sounds.json and the pickaxe tag in the JAR are byte-equal to the live files", gbad[:5])
        ck("V12.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V12.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in NEW_KEYS if data.get(k) != source.get(k) or k not in data}
            ck(f"V12.{Path(entry).name}", not bad, f"{entry} in the JAR carries the {NEW_COUNT} new keys with the values of the source file", dict(list(bad.items())[:3]))
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- suite, mutations, main

def static_suite(inp, st, facts=None, v1=True):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    if v1:
        guarded(ck, "V1", v1_original, inp, st)
    guarded(ck, "V2", v2_console, inp, st)
    guarded(ck, "V3", v3_block_menu_item, inp, st)
    for fn in (v4_registrations, v4_screen, v4_render):
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
        # ---- the original's text (in memory): a moved or changed line must fail loudly
        ("orig_packet_range", "V1.|V2.", OE("con", lambda x: rep1(x, "this.networkPackNT(50);", "this.networkPackNT(55);"))),
        ("orig_permission_radius", "V1.|V2.", OE("con", lambda x: rep1(x, "lengthVector() < 20;", "lengthVector() < 25;"))),
        ("orig_depletion_formula", "V1.|V2.", OE("con", lambda x: rep1(x, "value += (100D - (col.data.getDouble(\"enrichment\") * 100D));", "value += (90D - (col.data.getDouble(\"enrichment\") * 100D));"))),
        ("orig_block_dimensions", "V1.|V3.", OE("blk", lambda x: rep1(x, "return new int[] {3, 0, 0, 0, 2, 2};", "return new int[] {4, 0, 0, 0, 2, 2};"))),
        ("orig_tool_key", "V1.|V3.", OE("tool", lambda x: rep1(x, 'stack.stackTagCompound.setInteger("posX", pos[0]);', 'stack.stackTagCompound.setInteger("pX", pos[0]);'))),
        ("orig_az5_cooldown", "V1.|V4.", OE("gui", lambda x: rep1(x, "lastPress + 3000 <", "lastPress + 300 <"))),
        ("orig_flux_scale", "V1.|V4.", OE("gui", lambda x: rep1(x, "k * 74D / console.fluxBuffer.length", "k * 75D / console.fluxBuffer.length"))),
        ("orig_render_origin", "V1.|V4.", OE("ren", lambda x: rep1(x, "double kx = -0.3725D;", "double kx = -0.3825D;"))),
        ("orig_recipe_row", "V1.|V5.", OE("cm", lambda x: rep1(x, "\"BBB\", \"DGD\", \"DCD\", 'B', B.ingot()", "\"BBB\", \"DGD\", \"DCD\", 'B', PB.ingot()"))),
        ("orig_tool_recipe_row", "V1.|V5.", OE("tr", lambda x: rep1(x, 'ItemStack(ModItems.rbmk_tool), new Object[] { " A ", " IA", "I  "', 'ItemStack(ModItems.rbmk_tool), new Object[] { " A ", " IA", "  I"'))),
        ("orig_tool_stack_size", "V1.|V3.", OE("mi", lambda x: rep1(x, 'setUnlocalizedName("rbmk_tool").setMaxStackSize(1)', 'setUnlocalizedName("rbmk_tool").setMaxStackSize(64)'))),
        ("orig_block_texture", "V1.|V6.", OE("mb", lambda x: rep1(x, 'setBlockName("rbmk_console").setCreativeTab(MainRegistry.machineTab).setBlockTextureName(RefStrings.MODID + ":rbmk/rbmk_console")', 'setBlockName("rbmk_console").setCreativeTab(MainRegistry.machineTab).setBlockTextureName(RefStrings.MODID + ":rbmk/rbmk_console2")'))),
        ("orig_sound_definition", "V1.|V4.|V6.", OE("sounds", lambda x: rep1(x, '[{"name": "block/shutdown", "stream": true}]', '[{"name": "block/shutdown2", "stream": true}]'))),
        ("orig_enum_safe", "V1.|V2.", OE("eu", lambda x: rep1(x, "index = Math.abs(index % values.length);", "index = index % values.length;"))),
        ("orig_tile_mapping", "V1.|V4.", OE("tm", lambda x: rep1(x, 'put(TileEntityRBMKConsole.class, "tileentity_rbmk_console");', 'put(TileEntityRBMKConsole.class, "tileentity_rbmk_consol");'))),
        # ---- V2 the console block entity
        ("con_scan_size", "V2.", t(CON, "new RBMKColumn[15 * 15]", "new RBMKColumn[13 * 13]")),
        ("con_index_modulus", "V2.", t(CON, "final int i = col % 15 - 7;\n        final int j = col / 15 - 7;\n        switch (rotation) {\n            case 0: // 0°\n                return i;", "final int i = col % 13 - 7;\n        final int j = col / 15 - 7;\n        switch (rotation) {\n            case 0: // 0°\n                return i;")),
        ("con_rescan_period", "V2.", t(CON, "if(this.level.getGameTime() % 10 == 0) {\n            rescan();", "if(this.level.getGameTime() % 20 == 0) {\n            rescan();")),
        ("con_packet_range", "V2.", t(CON, "this.networkPackNT(50);", "this.networkPackNT(25);")),
        ("con_flux_buffer", "V2.", t(CON, "fluxDisplayBuffer = 60;", "fluxDisplayBuffer = 50;")),
        ("con_flux_shift_dropped", "V2.", t(CON, "this.fluxBuffer[i] = this.fluxBuffer[i + 1];", "")),
        ("con_loaded_guard_dropped", "V2.", t(CON, "this.level.isLoaded(pos) ? this.level.getBlockEntity(pos) : null", "this.level.getBlockEntity(pos)")),
        ("con_col_temp_key", "V2.", t(CON, 'value += col.data.getDouble("heat");', 'value += col.data.getDouble("c_heat");')),
        ("con_depletion_formula", "V2.", t(CON, '(100D - (col.data.getDouble("enrichment") * 100D))', '(col.data.getDouble("enrichment") * 100D)')),
        ("con_truncation", "V2.", t(CON, "((int)(result * 10)) / 10D", "((int)(result * 100)) / 10D")),
        ("con_prefix_unit", "V2.", t(CON, '"rbmk.screen.temp=" + text + "°C"', '"rbmk.screen.temp=" + text + "%"')),
        ("con_rotation_one", "V2.", t(CON, "case 1: // 90°\n                return -j;", "case 1: // 90°\n                return j;")),
        ("con_rotate_modulus", "V2.", t(CON, "rotation = (byte)((rotation + 1) % 4);", "rotation = (byte)((rotation + 1) % 3);")),
        ("con_permission_radius", "V2.", t(CON, ".length() < 20;", ".length() < 21;")),
        ("con_finite_check_dropped", "V2.", t(CON, "if(Double.isFinite(target)) {", "if(true) {")),
        ("con_index_guard_dropped", "V2.", t(CON, "if(index < 0 || index >= this.columns.length) continue;", "")),
        ("con_slot_guard", "V2.", t(CON, "if(slot >= 0 && slot < this.screens.length) {\n                int next", "if(slot >= 0 && slot < 7) {\n                int next")),
        ("con_color_abs_dropped", "V2.", t(CON, "Math.abs(color % RBMKColor.values().length)", "color % RBMKColor.values().length")),
        ("con_assign_on_auto_rods", "V2.", t(CON, "instanceof RBMKControlManualBlockEntity rod) {\n                    rod.color = group;", "instanceof RBMKControlBlockEntity rod) {\n                    rod.color = group;")),
        ("con_compressor_on_all", "V2.", t(CON, "instanceof RBMKBoilerBlockEntity boiler", "instanceof RBMKBaseBlockEntity boiler")),
        ("con_az5_includes_auto", "V2.", t(CON, "columns[j].type == RBMKColumnType.CONTROL)", "columns[j].type == RBMKColumnType.CONTROL || columns[j].type == RBMKColumnType.CONTROL_AUTO)")),
        ("con_az5_level", "V2.", t(CON, 'control.putDouble("level", 0);', 'control.putDouble("level", 0.1);')),
        ("con_serialize_order", "V2.", T(CON, lambda x: swap_lines(x, "buf.writeVarIntArray(this.fluxBuffer);", "for(RBMKColumn column : this.columns) {"))),
        ("con_nbt_key", "V2.", t(CON, 'tag.putInt("tX", this.targetX);', 'tag.putInt("targetX", this.targetX);')),
        ("con_client_import", "V2.", t(CON, "package com.hbm.blockentity.machine.rbmk;", "package com.hbm.blockentity.machine.rbmk;\n\nimport net.minecraft.client.Minecraft;")),
        ("con_render_box", "V2.", t(CON, "pos.getY() + 4, pos.getZ() + 3);", "pos.getY() + 5, pos.getZ() + 3);")),
        ("con_screen_offset", "V2.", t(CON, "FUEL_POISON(4 * 18),", "FUEL_POISON(5 * 18),")),
        # ---- V3 block, menu, item
        ("blk_second_box_fill_dropped", "V3.", T(CBLK, lambda x: drop_line(x, "MultiblockHandlerXR.fillSpace(level, pos.relative(dir, offset), EXTRA_DIMENSIONS"))),
        ("blk_second_box_check_dropped", "V3.", T(CBLK, lambda x: drop_line(x, "if(!MultiblockHandlerXR.checkSpace(level, pos.relative(dir, offset), EXTRA_DIMENSIONS"))),
        ("blk_dimensions", "V3.", t(CBLK, "getDimensions() { return new int[] {3,", "getDimensions() { return new int[] {4,")),
        ("blk_offset", "V3.", t(CBLK, "getOffset() { return 1; }", "getOffset() { return 2; }")),
        ("blk_screw_other_tool", "V3.", t(CBLK, "if(tool != ToolType.SCREWDRIVER) return false;", "if(tool != ToolType.SCREWDRIVER && tool != ToolType.TORCH) return false;")),
        ("blk_core_only_entity", "V3.", t(CBLK, "state.getValue(TYPE) == DummyBlockType.CORE ? new RBMKConsoleBlockEntity(pos, state) : null", "new RBMKConsoleBlockEntity(pos, state)")),
        ("tool_key", "V3.", t(TOOL, 'tag.putInt("posX", core.getX());', 'tag.putInt("x", core.getX());')),
        ("tool_key_check_dropped", "V3.", t(TOOL, "if(b instanceof RBMKConsoleBlock console && hasPosition(stack)) {", "if(b instanceof RBMKConsoleBlock console) {")),
        ("tool_attack_damage", "V3.", t(TOOL, "AttributeModifier.Operation.ADD_VALUE),", "AttributeModifier.Operation.ADD_VALUE),\n                        EquipmentSlotGroup.OFFHAND),//")),
        ("item_stack_size", "V3.", t(NITEMS, "new RBMKToolItem(new Item.Properties().stacksTo(1))", "new RBMKToolItem(new Item.Properties().stacksTo(64))")),
        ("block_strength", "V3.", t(NB, 'new RBMKConsoleBlock(BlockBehaviour.Properties.of().noOcclusion().strength(3.0F, 30.0F)', 'new RBMKConsoleBlock(BlockBehaviour.Properties.of().noOcclusion().strength(2.0F, 30.0F)')),
        # ---- V4 registrations and client
        ("reg_block_dropped", "V4.", T(NB, lambda x: drop_line(x, 'RBMK_CONSOLE = register("rbmk_console"'))),
        ("reg_menu_duplicated", "V4.", T(MT, lambda x: dup_line(x, 'RBMK_CONSOLE = reg("rbmk_console"'))),
        ("reg_block_entity_dropped", "V4.", T(BET, lambda x: drop_line(x, 'RBMK_CONSOLE = BLOCK_ENTITY_TYPES.register("rbmk_console"'))),
        ("reg_screen_dropped", "V4.", T(NMC, lambda x: drop_line(x, "RBMKConsoleScreen::new"))),
        ("reg_renderer_dropped", "V4.", T(CP, lambda x: drop_line(x, "BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_CONSOLE.get(), new RenderRBMKConsole());"))),
        ("reg_renderer_duplicated", "V4.", T(CP, lambda x: dup_line(x, "BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_CONSOLE.get(), new RenderRBMKConsole());"))),
        ("reg_tool_dropped", "V4.", T(NITEMS, lambda x: drop_line(x, 'RBMK_TOOL = ITEMS.register("rbmk_tool"'))),
        ("reg_tab_dropped", "V4.", T(CT, lambda x: drop_line(x, "output.accept(NtmBlocks.RBMK_CONSOLE);"))),
        ("reg_sound_dropped", "V4.", T(SOUNDS, lambda x: drop_line(x, 'SHUTDOWN = reg("block.shutdown");'))),
        ("reg_sound_provider_dropped", "V4.", T(SDP, lambda x: drop_line(x, '.with(sound(NuclearTechMod.withDefaultNamespace("block/shutdown")).stream())'))),
        ("reg_resource_model", "V4.", t(RM, 'new HFRWavefrontObject("models/obj/rbmk/rbmk_console.obj")', 'new HFRWavefrontObject("models/obj/rbmk/rbmk_consoles.obj")')),
        ("screen_flux_scale", "V4.", t(CSCREEN, "k * 74D / be.fluxBuffer.length", "k * 75D / be.fluxBuffer.length")),
        ("screen_az5_cooldown", "V4.", t(CSCREEN, "lastPress + 3000 <", "lastPress + 300 <")),
        ("screen_control_break", "V4.", T(CSCREEN, lambda x: x.replace("case CONTROL_AUTO:", "break;\n            case CONTROL_AUTO:"))),
        ("screen_width", "V4.", t(CSCREEN, "this.imageWidth = 244;", "this.imageWidth = 245;")),
        ("render_origin", "V4.", t(RCON, "double kx = -0.3725D;", "double kx = -0.3825D;")),
        ("render_heat_blend", "V4.", t(RCON, "double color = 0.65D + (i % 2) * 0.05D;", "double color = 0.60D + (i % 2) * 0.05D;")),
        ("render_client_free_block", "V4.", t(CBLK, "package com.hbm.blocks.machine.rbmk;", "package com.hbm.blocks.machine.rbmk;\n\nimport net.minecraft.client.Minecraft;")),
        # ---- V5 recipes
        ("recipe_pattern", "V5.", gen_edit(RECIPES + "rbmk_console.json", lambda d: d["pattern"].__setitem__(0, "BB "))),
        ("recipe_count", "V5.", gen_edit(RECIPES + "rbmk_console.json", lambda d: d["result"].__setitem__("count", 2))),
        ("recipe_tag_to_item", "V5.", gen_edit(RECIPES + "rbmk_console.json", lambda d: d["key"].__setitem__("G", {"item": "minecraft:glass_pane"}))),
        ("recipe_tool_ingredient", "V5.", gen_edit(RECIPES + "rbmk_tool.json", lambda d: d["key"].__setitem__("A", {"item": "hbmsntm:ingot_steel"}))),
        ("recipe_tool_category", "V5.", gen_edit(RECIPES + "rbmk_tool.json", lambda d: d.__setitem__("category", "misc"))),
        ("advancement_criterion", "V5.", gen_edit(ADV + "misc/rbmk_console.json", lambda d: d["criteria"]["has_deco_rbmk"]["conditions"]["items"][0].__setitem__("items", "hbmsntm:rbmk_blank"))),
        ("recipe_extra_file", "V5.|V6.", lambda st: st.set_bytes(RECIPES + "rbmk_console_alt.json", b"{}")),
        ("anvil_recipes_touched", "V5.", T(J + "inventory/recipes/anvil/AnvilRecipes.java", lambda x: x + "\n// stray\n")),
        ("provider_pattern_changed", "V5.", t(RP, '.pattern("DCD")\n                .define(\'B\', NtmItems.INGOT_BORON.get())', '.pattern("DDD")\n                .define(\'B\', NtmItems.INGOT_BORON.get())')),
        ("provider_category", "V5.", t(RP, "ShapedRecipeBuilder.shaped(RecipeCategory.TOOLS, NtmItems.RBMK_TOOL.get(), 1)", "ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmItems.RBMK_TOOL.get(), 1)")),
        # ---- V6 datagen outputs
        ("blockstate_model", "V6.", gen_edit(G_STATE + "rbmk_console.json", lambda d: d["variants"][""].__setitem__("model", "hbmsntm:block/rbmk_blank"))),
        ("block_model_texture", "V6.", gen_edit(G_BMODEL + "rbmk_console_particle.json", lambda d: d["textures"].__setitem__("particle", "hbmsntm:block/rbmk/rbmk_blank"))),
        ("loot_rolls", "V6.", gen_edit(G_LOOT + "rbmk_console.json", lambda d: d["pools"][0].__setitem__("rolls", 2.0))),
        ("item_model_parent", "V6.", gen_edit(G_IMODEL + "rbmk_tool.json", lambda d: d.__setitem__("parent", "minecraft:item/handheld"))),
        ("console_item_model", "V6.", gen_edit(G_IMODEL + "rbmk_console.json", lambda d: d.__setitem__("parent", "hbmsntm:block/rbmk_console_particle"))),
        ("pickaxe_entry_dropped", "V6.", T(PICK, lambda x: drop_line(x, '"hbmsntm:rbmk_console",'))),
        ("sounds_json_stream", "V6.", gen_edit(SJSON, lambda d: d["block.shutdown"]["sounds"][0].pop("stream"))),
        ("generated_extra_file", "V6.", lambda st: st.set_bytes(G_STATE + "rbmk_stray.json", b"{}")),
        ("provider_tag_extra_block", "V6.", t(TAGP, "NtmBlocks.RBMK_CONSOLE.get(),", "NtmBlocks.RBMK_CONSOLE.get(),\n                        NtmBlocks.PRIBRIS.get(),")),
        ("provider_loot_changed", "V6.", t(LOOT, "this.dropSelf(NtmBlocks.RBMK_CONSOLE.get());", "this.dropOther(NtmBlocks.RBMK_CONSOLE.get(), NtmBlocks.RBMK_BLANK.get());")),
        ("stamp_generated_hash", "V6.", lambda st: st.set_text(STAMP, json_edit(st.text(STAMP), lambda d: d["generated"].__setitem__(next(iter(d["generated"])), "0" * 64)))),
        ("stamp_input_hash", "V6.", lambda st: st.set_text(STAMP, json_edit(st.text(STAMP), lambda d: d["inputs"].__setitem__(CON, "0" * 64)))),
        # ---- V7 language
        ("zh_value_changed", "V7.", zh_set("block.hbmsntm.rbmk_console", "RBMK控制台")),
        ("zh_local_tip_changed", "V7.", zh_set("rbmk.console.selectAll", "选择所有控制棒")),
        ("zh_assign_placeholder", "V7.", zh_set("rbmk.console.assign", "将选定列分配给屏幕#%s")),
        ("zh_assign_unsourced", "V7.", zh_set("rbmk.console.assign", "将选定列分配给屏幕")),
        ("map_assign_kind_upstream", "V7.", map_set("rbmk.console.assign", "kind", "upstream")),
        ("map_assign_reason_cite", "V7.", map_set("rbmk.console.assign", "reason", "Goal24E：补上屏幕编号占位符。")),
        ("map_assign_source_zh", "V7.", map_set("rbmk.console.assign", "source_zh", "将选定列分配给屏幕 #%s")),
        ("zh_key_removed", "V7.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("rbmk.screen.xenon")))),
        ("zh_crlf_broken", "V7.", Bx(ZH, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_crlf_broken", "V7.", Bx(MAP, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_source_zh_changed", "V7.", map_set("rbmk.heat", "source_zh", "温度: %s")),
        ("map_local_reason_cite", "V7.", map_set("rbmk.console.compressor", "reason", "Goal24E：原版 GUIRBMKConsole.java:50-60 的悬停提示为硬编码英文。")),
        ("map_kind_flipped", "V7.", map_set("rbmk.console.type.fuel", "kind", "upstream")),
        ("map_entry_removed", "V7.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"].pop("item.hbmsntm.rbmk_tool")))),
        ("provider_string_changed", "V7.", t(LP, 'this.add(NtmBlocks.RBMK_CONSOLE, "RBMK Console");', 'this.add(NtmBlocks.RBMK_CONSOLE, "RBMK Console ");')),
        ("en_value_changed", "V7.", lambda st: st.set_text(EN, st.text(EN).replace('"RBMK Console Linking Device"', '"RBMK Console Linking device"'))),
        # ---- V8 resources
        ("texture_byte_flipped", "V8.", Bx(TEX_PNG, flip_byte)),
        ("gui_texture_byte_flipped", "V8.", Bx(GUI_PNG, flip_byte)),
        ("obj_line_endings_changed", "V8.", Bx(OBJ_NEO, lambda b: b.replace(b"\r\n", b"\n"))),
        ("ogg_byte_flipped", "V8.", Bx(OGG, flip_byte)),
        ("texture_deleted", "V8.", D(ITEM_PNG)),
        ("control_head_texture_imported", "V8.", lambda st: st.set_bytes(RES + "textures/block/rbmk/rbmk_stray.png", b"x")),
        ("ownership_asset_dropped", "V8.", own_edit(lambda d: d.__setitem__("assets", [a for a in d["assets"] if not a["target_path"].endswith(".obj")]))),
        ("ownership_sha_changed", "V8.", own_edit(lambda d: d["assets"][2].__setitem__("target_sha256", "0" * 64))),
        ("ownership_obj_field", "V8.", own_edit(lambda d: next(a for a in d["assets"] if a["target_path"].endswith(".obj")).__setitem__("worktree_crlf_lines", 1))),
        ("ownership_not_imported_dropped", "V8.", own_edit(lambda d: d["not_imported"].pop())),
        # ---- V9 scope
        ("stray_src_file_added", "V9.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}")),
        ("unrelated_src_file_touched", "V9.", touch(J + "blockentity/machine/rbmk/RBMKDials.java")),
        ("anvil_file_touched", "V9.|V5.", touch(J + "inventory/recipes/anvil/AnvilRecipes.java")),
        ("unrelated_migration_file_added", "V9.", lambda st: st.set_bytes("migration/stray.json", b"{}")),
        ("edited_file_line_removed", "V9.", T(NB, lambda x: drop_line(x, "RBMK_ABSORBER = register("))),
        ("edited_file_eol_mixed", "V9.", Bx(NB, lambda b: b.replace(b"\r\n", b"\n", 1) if b"\r\n" in b else b.replace(b"\n", b"\r\n", 1))),
        # ---- V10 GameTest source
        ("gt_marker_changed", "V10.", T(GT, lambda x: x.replace('"' + GT_MARK + ' {} passed"', '"[hbm-rbmk] {} passed"')), GT),
        ("gt_holder_removed", "V10.", T(GT, lambda x: rep1(x, "@GameTestHolder(NuclearTechMod.MODID)", "")), GT),
        ("gt_batch_shared", "V10.", T(GT, lambda x: rep1(x, 'batch = "rbmk_console_az5"', 'batch = "rbmk_console_flux"')), GT),
        ("gt_client_class", "V10.", T(GT, lambda x: rep1(x, "public class RBMKConsoleGameTests {", "public class RBMKConsoleGameTests {\n    private static final Class<?> BAD = net.minecraft.client.Minecraft.class;")), GT),
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
