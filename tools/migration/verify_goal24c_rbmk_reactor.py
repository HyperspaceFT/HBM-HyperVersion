"""Verify the Goal24C batch statically: the RBMK neutron handler (handler/neutron), IRBMKFluxReceiver.receiveFlux and IRBMKLoadable, the slotted column base, the fuel
channel block entity (rbmk_rod / rbmk_rod_mod: RBMKRodBlockEntity, RBMKRodBlock, RBMKRodMenu, RBMKRodScreen, RenderRBMKRod, RBMKElementBakedModel), corium_block, the
meltdown changes in RBMKBaseBlockEntity, the NtmEventHandler hooks, the rbmk_rod recipe, the datagen outputs, the 12 new language keys, the 23 imported resources and the
GameTest source.

Read-only for both worktrees. Writes only build/migration/goal24c/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal24c/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (NeutronHandler, NeutronNodeWorld, NeutronStream, RBMKNeutronHandler, TileEntityRBMKRod, RBMKRod, ContainerRBMKRod, GUIRBMKRod, CoriumFinite, the
      meltdown step, the recipe rows, ModEventHandler.onUnload, the lang lines, the resources) parsed from the read-only worktree at the cited lines; a moved line fails loudly.
- V2  The neutron package against V1.
- V3  NtmEventHandler: call order, unload and stop hooks, nothing else changed.
- V4  The rod block entity against V1, IRBMKFluxReceiver / IRBMKLoadable, RBMKSlottedBaseBlockEntity, the RBMKBaseBlockEntity changes.
- V5  Blocks, menu, screen, renderer and baked model, registrations, creative tab, client isolation.
- V6  Recipes: the generated rbmk_rod recipe, nothing else.
- V7  Datagen outputs: blockstates, models, item models, loot tables, pickaxe tag.
- V8  Language: the 12 new keys in the provider, en_us.json, zh_cn.json and zh_cn-map.json.
- V9  Resources: the 23 imported files against the original and migration/goal24c-resource-ownership.json.
- V10 Scope: every src/ and migration/ path changed since the start is in the expected set (tools/ listed separately).
- V11 GameTest source. V12 (--gametest-log) the GameTest log. V13 (--jar) the packaged JAR; "not run" when the flag is absent.
- V14 In-memory mutations of the NEO inputs (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal24c_rbmk_reactor.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal24c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "1114adf5de758697842e1f2195c0e3928b04abbc"

J = "src/main/java/com/hbm/"
NODEH = J + "handler/neutron/NeutronHandler.java"
NNW = J + "handler/neutron/NeutronNodeWorld.java"
NNODE = J + "handler/neutron/NeutronNode.java"
NSTREAM = J + "handler/neutron/NeutronStream.java"
RNH = J + "handler/neutron/RBMKNeutronHandler.java"
PKG = J + "handler/neutron/package-info.java"
NEUTRON = [NODEH, NNW, NNODE, NSTREAM, RNH]
BE = J + "blockentity/machine/rbmk/"
FLUX = BE + "IRBMKFluxReceiver.java"
LOAD = BE + "IRBMKLoadable.java"
BASEBE = BE + "RBMKBaseBlockEntity.java"
SLOT = BE + "RBMKSlottedBaseBlockEntity.java"
RODBE = BE + "RBMKRodBlockEntity.java"
RODBLK = J + "blocks/machine/rbmk/RBMKRodBlock.java"
BASEBLK = J + "blocks/machine/rbmk/RBMKBaseBlock.java"
CORIUM = J + "blocks/generic/CoriumBlock.java"
MENU = J + "inventory/menus/RBMKRodMenu.java"
SCREEN = J + "inventory/screens/RBMKRodScreen.java"
RENDER = J + "render/blockentity/RenderRBMKRod.java"
RLID = J + "render/blockentity/RenderRBMKLid.java"
BAKED = J + "render/model/RBMKElementBakedModel.java"
GEO = J + "render/model/loader/NtmGeometry.java"
EH = J + "main/NtmEventHandler.java"
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
ANVIL = J + "inventory/recipes/anvil/AnvilRecipes.java"
DIALS = BE + "RBMKDials.java"
ROD_ITEM = J + "items/machine/RBMKRodItem.java"
PELLET_ITEM = J + "items/machine/RBMKPelletItem.java"
LID_ITEM = J + "items/machine/RBMKLidItem.java"
HAZ = J + "hazard/HazardRegistry.java"
GT = J + "gametest/RBMKReactorGameTests.java"
GT_DIR = J + "gametest/"
NEW_CLASSES = NEUTRON + [PKG, LOAD, SLOT, RODBE, RODBLK, CORIUM, MENU, SCREEN, RENDER, BAKED]
EDITED = [FLUX, BASEBE, EH, NB, BET, MT, CT, NMC, CP, RM, RLID, GEO, BSP, LOOT, TAGP, LP, RP]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal24c-resource-ownership.json"
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
GUITEX = RES + "textures/gui/reactors/gui_rbmk_element.png"
INFO = J + "inventory/screens/InfoScreen.java"
NTMCONFIG = J + "config/NtmConfig.java"

O = "src/main/java/com/hbm/"
O_NH = O + "handler/neutron/NeutronHandler.java"
O_NNW = O + "handler/neutron/NeutronNodeWorld.java"
O_NNODE = O + "handler/neutron/NeutronNode.java"
O_NSTREAM = O + "handler/neutron/NeutronStream.java"
O_RNH = O + "handler/neutron/RBMKNeutronHandler.java"
O_PKG = O + "handler/neutron/package-info.java"
O_TE = O + "tileentity/machine/rbmk/"
O_FLUX = O_TE + "IRBMKFluxReceiver.java"
O_LOAD = O_TE + "IRBMKLoadable.java"
O_ROD = O_TE + "TileEntityRBMKRod.java"
O_BASE = O_TE + "TileEntityRBMKBase.java"
O_RODBLK = O + "blocks/machine/rbmk/RBMKRod.java"
O_CONT = O + "inventory/container/ContainerRBMKRod.java"
O_GUI = O + "inventory/gui/GUIRBMKRod.java"
O_CORIUM = O + "blocks/fluid/CoriumFinite.java"
O_MB = O + "blocks/ModBlocks.java"
O_CM = O + "main/CraftingManager.java"
O_AR = O + "inventory/recipes/anvil/AnvilRecipes.java"
O_MEH = O + "main/ModEventHandler.java"
O_GUIINFO = O + "inventory/gui/GuiInfoContainer.java"
O_GFF = O + "blocks/fluid/GenericFiniteFluid.java"
O_RENDER_FC = O + "render/tileentity/RenderRBMKFuelChannel.java"
O_RENDER_ROD = O + "render/block/RenderRBMKRod.java"
O_BASEBLK = O + "blocks/machine/rbmk/RBMKBase.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_RES = "src/main/resources/assets/hbm/"

GT_MARK = "[hbm-rbmk-reactor]"
START_GAMETESTS = 158
HASH_SKIP = ("__pycache__",)

# Chinese and English text of the 12 new language keys (handoff-production.md "Language"; the upstream ones are read from the lang files and compared)
UPSTREAM_KEYS = [  # (NEO key, original key)
    ("block.hbmsntm.rbmk_rod", "tile.rbmk_rod.name"), ("block.hbmsntm.rbmk_rod_mod", "tile.rbmk_rod_mod.name"), ("block.hbmsntm.corium_block", "tile.corium_block.name"),
    ("container.rbmkRod", "container.rbmkRod"), ("tile.rbmk.dodd.fluxSlow", "tile.rbmk.dodd.fluxSlow"), ("tile.rbmk.dodd.fluxFast", "tile.rbmk.dodd.fluxFast"),
    ("tile.rbmk.dodd.hasRod", "tile.rbmk.dodd.hasRod"), ("tile.rbmk.dodd.f_heat", "tile.rbmk.dodd.f_heat"), ("tile.rbmk.dodd.f_xenon", "tile.rbmk.dodd.f_xenon"),
    ("tile.rbmk.dodd.f_yield", "tile.rbmk.dodd.f_yield")]
UPSTREAM_EXPECT = {  # NEO key -> (English, Chinese) as the handoff gives them
    "block.hbmsntm.rbmk_rod": ("RBMK Fuel Channel", "RBMK反应堆燃料通道"), "block.hbmsntm.rbmk_rod_mod": ("RBMK Moderated Fuel Channel", "RBMK反应堆慢化燃料通道"),
    "block.hbmsntm.corium_block": ("Corium", "堆芯熔融物"), "container.rbmkRod": ("RBMK Fuel Rod", "RBMK石墨式反应堆燃料棒"),
    "tile.rbmk.dodd.fluxSlow": ("Flux Slow", "慢中子计数"), "tile.rbmk.dodd.fluxFast": ("Flux Fast", "快中子计数"), "tile.rbmk.dodd.hasRod": ("Has Rod", "是否有燃料棒"),
    "tile.rbmk.dodd.f_heat": ("Fuel Heat", "燃料棒温度"), "tile.rbmk.dodd.f_xenon": ("Fuel Xenon", "氙中毒指数"), "tile.rbmk.dodd.f_yield": ("Fuel Yield", "耐久")}
LOCAL_EXPECT = {
    "container.rbmkRod.autoloaderHot": ("Fuel skin temperature has exceeded 1,000°C,$autoloaders can no longer cycle fuel!", "燃料外壳温度已超过 1,000°C，$自动装料机无法再更换燃料！"),
    "container.rbmkRod.manualHot": ("Fuel skin temperature has exceeded 200°C,$fuel can no longer be removed by hand!", "燃料外壳温度已超过 200°C，$无法再徒手取出燃料！")}
NEW_KEYS = sorted(list(UPSTREAM_EXPECT) + list(LOCAL_EXPECT))
START_EN_KEYS, START_ZH_KEYS, START_MAP_KEYS = 2602, 2495, 2602  # the key counts at the start (2,614 / 2,507 / 2,614 minus the 12)

# the 23 imported resources: (original path under assets/hbm, NEO path under assets/hbmsntm)
TEX_VARIANTS = [("rbmk_element", "rbmk_element"), ("rbmk_element_mod", "rbmk_element_mod")]
TEX_PARTS = ["side", "top", "cover_top", "cover_side", "glass_top", "glass_side", "inner", "fuel"]
IMPORTS = ([(f"textures/blocks/rbmk/{v}_{p}.png", f"textures/block/rbmk/{v}_{p}.png") for v, _ in TEX_VARIANTS for p in TEX_PARTS]
           + [("textures/blocks/corium_still.png", "textures/block/corium_still.png"), ("textures/blocks/corium_still.png.mcmeta", "textures/block/corium_still.png.mcmeta"),
              ("textures/blocks/corium_flowing.png", "textures/block/corium_flowing.png"), ("textures/blocks/corium_flowing.png.mcmeta", "textures/block/corium_flowing.png.mcmeta"),
              ("models/rbmk/rbmk_element.obj", "models/obj/rbmk/rbmk_element.obj"), ("models/rbmk/rbmk_element_rods.obj", "models/obj/rbmk/rbmk_element_rods.obj"),
              ("textures/gui/reactors/gui_rbmk_element.png", "textures/gui/reactors/gui_rbmk_element.png")])
NOT_IMPORTED_MUST = ["textures/blocks/rbmk/rbmk_element.png", "textures/blocks/block_corium.png", "textures/blocks/block_corium_cobble.png"]
REASIM_NOT_IMPORTED = [f"textures/blocks/rbmk/rbmk_element_reasim{m}_{p}.png" for m in ("", "_mod") for p in TEX_PARTS]


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

@functools.lru_cache(maxsize=160)
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


def has_all(code, *needles):
    return [n for n in needles if n not in code]


def rewrite(s, table):
    for pat, rep in table:
        s = re.sub(pat, rep, s)
    return s


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
    return [(n, needle, lines[n - 1].strip()[:120]) for n, needle in expected.items() if n > len(lines) or needle not in lines[n - 1]]


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
    names = dict(nh=O_NH, nnw=O_NNW, nnode=O_NNODE, nstream=O_NSTREAM, rnh=O_RNH, pkg=O_PKG, flux=O_FLUX, load=O_LOAD, rod=O_ROD, base=O_BASE, rodblk=O_RODBLK,
                 cont=O_CONT, gui=O_GUI, corium=O_CORIUM, mb=O_MB, cm=O_CM, ar=O_AR, meh=O_MEH, guiinfo=O_GUIINFO, gff=O_GFF, rfc=O_RENDER_FC, rrod=O_RENDER_ROD, rbase=O_BASEBLK)
    inp.o = {name: otext(path) for name, path in names.items()}
    inp.ol = {name: text.split("\n") for name, text in inp.o.items()}
    inp.o_en = parse_lang(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh = parse_lang(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    tree = hash_tree()
    # the files the checks read
    files = {}
    load = set(NEW_CLASSES + EDITED + [BE + "RBMKType.java", DIALS, ROD_ITEM, PELLET_ITEM, LID_ITEM, HAZ, BASEBLK, ZH, MAP, OWN, EN, STAMP, PICK, ANVIL, IMP, GUITEX, INFO, J + "blocks/DummyableBlock.java", J + "blocks/machine/rbmk/RBMKPassiveBlock.java", J + "gametest/HazardGameTests.java"])
    for p in tree:
        if p not in inp.base_files and (p.startswith(GEN) or p.startswith(GT_DIR)):
            load.add(p)
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    for _, neo in IMPORTS:
        if (ROOT / (RES + neo)).exists():
            files[RES + neo] = (ROOT / (RES + neo)).read_bytes()
    for p in (G_STATE, G_BMODEL, G_IMODEL, G_LOOT):
        for n in ("rbmk_rod", "rbmk_rod_mod", "corium_block", "rbmk_blank"):
            f = ROOT / (p + n + ".json")
            if f.exists():
                files[p + n + ".json"] = f.read_bytes()
    for p in (RECIPES + "rbmk_rod.json", ADV + "misc/rbmk_rod.json"):
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
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
            except Exception:  # noqa: BLE001 - reported by V9
                inp.o_blob[RES + neo] = None
    inp.o_not_imported = {n: (ORIGINAL / (O_RES + n)).exists() for n in NOT_IMPORTED_MUST + REASIM_NOT_IMPORTED}

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


# ---------------------------------------------------------------- the original: signatures parsed once, anchors checked in V1

# key -> (inputs key, exact method header in the original)
ORIG_SIGS = {
    "nh.tick": ("nh", "public void onServerTick(TickEvent.ServerTickEvent event)"),
    "nnw.getNode": ("nnw", "public static NeutronNode getNode(World world, BlockPos pos)"),
    "nnw.removeNode": ("nnw", "public static void removeNode(World world, BlockPos pos)"),
    "nnw.getOrAddWorld": ("nnw", "public static StreamWorld getOrAddWorld(World world)"),
    "nnw.removeAllWorlds": ("nnw", "public static void removeAllWorlds()"),
    "nnw.removeEmptyWorlds": ("nnw", "public static void removeEmptyWorlds()"),
    "nnw.runStreamInteractions": ("nnw", "public void runStreamInteractions(World world)"),
    "nnw.addStream": ("nnw", "public void addStream(NeutronStream stream)"),
    "nnw.removeAllStreams": ("nnw", "public void removeAllStreams()"),
    "nnw.cleanNodes": ("nnw", "public void cleanNodes()"),
    "nnw.sgetNode": ("nnw", "public NeutronNode getNode(BlockPos pos)"),
    "nnw.addNode": ("nnw", "public void addNode(NeutronNode node)"),
    "nnw.sremoveNode": ("nnw", "public void removeNode(BlockPos pos)"),
    "nnw.removeAllStreamsOfType": ("nnw", "public void removeAllStreamsOfType(NeutronStream.NeutronType type)"),
    "ns.ctor1": ("nstream", "public NeutronStream(NeutronNode origin, Vec3 vector)"),
    "ns.ctor2": ("nstream", "public NeutronStream(NeutronNode origin, Vec3 vector, double flux, double ratio, NeutronType type)"),
    "ns.hasNext": ("nstream", "public boolean hasNext()"),
    "ns.next": ("nstream", "public BlockPos next()"),
    "rnh.blockPosToTE": ("rnh", "private static TileEntity blockPosToTE(World worldObj, BlockPos pos)"),
    "rnh.makeNode": ("rnh", "public static RBMKNeutronNode makeNode(StreamWorld streamWorld, TileEntityRBMKBase tile)"),
    "rnh.nodeCtor": ("rnh", "public RBMKNeutronNode(TileEntityRBMKBase tile, RBMKType type, boolean hasLid)"),
    "rnh.addLid": ("rnh", "public void addLid()"),
    "rnh.removeLid": ("rnh", "public void removeLid()"),
    "rnh.hasNext": ("rnh", "public boolean hasNext()"),
    "rnh.next": ("rnh", "public BlockPos next()"),
    "rnh.checkNode": ("rnh", "public List<BlockPos> checkNode(StreamWorld streamWorld)"),
    "rnh.getNodes": ("rnh", "public NeutronNode[] getNodes(StreamWorld streamWorld, boolean addNode)"),
    "rnh.run": ("rnh", "public void runStreamInteraction(World worldObj, StreamWorld streamWorld)"),
    "rnh.getHits": ("rnh", "public int getHits(BlockPos pos)"),
    "rnh.irr1": ("rnh", "public void irradiateFromFlux(BlockPos pos)"),
    "rnh.irr2": ("rnh", "public void irradiateFromFlux(BlockPos pos, int hits)"),
    "rnh.moderate": ("rnh", "public void moderateStream()"),
    "rod.receiveFlux": ("rod", "public void receiveFlux(NeutronStream stream)"),
    "rod.autoloader": ("rod", "public boolean coldEnoughForAutoloader()"),
    "rod.manual": ("rod", "public boolean coldEnoughForManual()"),
    "rod.invalidate": ("rod", "public void invalidate()"),
    "rod.update": ("rod", "public void updateEntity()"),
    "rod.fluxFromType": ("rod", "private double fluxFromType(NType type)"),
    "rod.spreadFlux": ("rod", "public void spreadFlux(double flux, double ratio)"),
    "rod.read": ("rod", "public void readFromNBT(NBTTagCompound nbt)"),
    "rod.write": ("rod", "public void writeToNBT(NBTTagCompound nbt)"),
    "rod.serialize": ("rod", "public void serialize(ByteBuf buf)"),
    "rod.deserialize": ("rod", "public void deserialize(ByteBuf buf)"),
    "rod.diag": ("rod", "public void getDiagData(NBTTagCompound nbt)"),
    "rod.onMelt": ("rod", "public void onMelt(int reduce)"),
    "rod.console": ("rod", "public NBTTagCompound getNBTForConsole()"),
    "rod.canLoad": ("rod", "public boolean canLoad(ItemStack toLoad)"),
    "rod.load": ("rod", "public void load(ItemStack toLoad)"),
    "rod.canUnload": ("rod", "public boolean canUnload()"),
    "rod.provideNext": ("rod", "public ItemStack provideNext()"),
    "rod.unload": ("rod", "public void unload()"),
    "rod.info": ("rod", "public String[] getFunctionInfo()"),
    "rod.ror": ("rod", "public String provideRORValue(String name)"),
    "blk.breakBlock": ("rodblk", "public void breakBlock(World world, int x, int y, int z, Block block, int meta)"),
    "blk.activated": ("rodblk", "public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player, int side, float hitX, float hitY, float hitZ)"),
    "cont.ctor": ("cont", "public ContainerRBMKRod(InventoryPlayer invPlayer, TileEntityRBMKRod tedf)"),
    "cont.slotClick": ("cont", "public ItemStack slotClick(int index, int button, int mode, EntityPlayer player)"),
    "cont.transfer": ("cont", "public ItemStack transferStackInSlot(EntityPlayer player, int par2)"),
    "gui.bg": ("gui", "protected void drawGuiContainerBackgroundLayer(float p_146976_1_, int p_146976_2_, int p_146976_3_)"),
    "gui.draw": ("gui", "public void drawScreen(int mouseX, int mouseY, float f)"),
    "corium.collide": ("corium", "public void onEntityCollidedWithBlock(World world, int x, int y, int z, Entity entity)"),
    "meh.unload": ("meh", "public void onUnload(WorldEvent.Unload event)"),
    "base.invalidate": ("base", "public void invalidate()"),
    "base.chunkUnload": ("base", "public void onChunkUnload()"),
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


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) >= 34 and len(inp.baseline["copied_scope"]) == 34 and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)} on disk, 34 in copied_scope) hashes to its baseline.json entry", bad)
    needed = NEW_CLASSES + EDITED + [ZH, MAP, OWN, EN, STAMP, DIALS, PICK]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 1114adf5", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.original-parsed", inp.ov is not None, "the original sources were parsed at the cited headers", inp.ov_error)


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st):
    ov = need_ov(inp)
    L = inp.ol
    # ---- NeutronHandler.java
    m = at_lines(L["nh"], {16: "@SubscribeEvent", 18: "event.phase != TickEvent.Phase.START", 22: "int cacheTime = 20;", 23: "boolean cacheClear = ticks >= cacheTime;", 24: "if(cacheClear) ticks = 0;",
                           25: "ticks++;", 28: "NeutronNodeWorld.removeEmptyWorlds();", 30: "for(Map.Entry<World, NeutronNodeWorld.StreamWorld> world", 34: "reflectorEfficiency = RBMKDials.getReflectorEfficiency(",
                           35: "absorberEfficiency = RBMKDials.getAbsorberEfficiency(", 36: "moderatorEfficiency = RBMKDials.getModeratorEfficiency(", 41: "columnHeight = RBMKDials.getColumnHeight(world.getKey()) + 1;",
                           42: "fluxRange = RBMKDials.getFluxRange(", 44: "runStreamInteractions(world.getKey());", 45: "removeAllStreams();", 47: "if(cacheClear) world.getValue().cleanNodes();"})
    ck("V1.neutron-handler", not m, "NeutronHandler.java:16-49 runs on ServerTickEvent START: cacheTime 20, cacheClear = ticks >= 20, reset, ticks++, removeEmptyWorlds before the loop, the three efficiencies, columnHeight = getColumnHeight() + 1, "
       "fluxRange, runStreamInteractions, removeAllStreams, cleanNodes when cacheClear", m)
    # ---- NeutronNodeWorld.java
    m = at_lines(L["nnw"], {13: "public static HashMap<World, StreamWorld> streamWorlds = new HashMap<>();", 15: "getNode(World world, BlockPos pos)", 20: "removeNode(World world, BlockPos pos)", 26: "getOrAddWorld(World world)",
                            35: "removeAllWorlds()", 39: "removeEmptyWorlds()", 41: "streamWorld.streams.isEmpty()", 47: "private List<NeutronStream> streams;", 48: "private HashMap<BlockPos, NeutronNode> nodeCache",
                            54: "runStreamInteractions(World world)", 60: "addStream(NeutronStream stream)", 64: "removeAllStreams()", 68: "cleanNodes()", 71: "NeutronStream.NeutronType.RBMK",
                            75: "/* TODO: actually do this and uncache pile nodes", 88: "getNode(BlockPos pos)", 92: "addNode(NeutronNode node)", 96: "removeNode(BlockPos pos)", 100: "removeAllStreamsOfType("})
    ck("V1.node-world", not m, "NeutronNodeWorld.java:13-103 holds the HashMap<World, StreamWorld>, getNode/removeNode/getOrAddWorld/removeAllWorlds/removeEmptyWorlds and the StreamWorld with streams, nodeCache, cleanNodes (RBMK only, pile TODO)", m)
    # ---- NeutronStream.java / NeutronNode.java
    m = at_lines(L["nstream"], {13: "DUMMY", 14: "RBMK", 15: "PILE", 33: "public NeutronStream(NeutronNode origin, Vec3 vector)", 36: "posInstance = origin.pos.clone();", 39: "double flux, double ratio, NeutronType type",
                                47: "NeutronNodeWorld.getOrAddWorld(origin.tile.getWorldObj()).addStream(this);", 55: "getBlocks(int range)", 57: "i = 1;", 62: "return i <= range;",
                                67: "int x = (int) Math.floor(0.5 + vector.xCoord * i);", 68: "int z = (int) Math.floor(0.5 + vector.zCoord * i);", 70: "i++;", 71: "posInstance.mutate(origin.tile.xCoord + x, origin.tile.yCoord, origin.tile.zCoord + z)"})
    ck("V1.neutron-stream", not m, "NeutronStream.java:12-77: DUMMY/RBMK/PILE, the dummy constructor does not register, the full one adds the stream to the origin world, getBlocks i = 1..range with floor(0.5 + v * i)", m)
    m = at_lines(L["nnode"], {12: "protected NeutronType type;", 14: "protected BlockPos pos;", 16: "protected TileEntity tile;", 20: "protected Map<String, Object> data = new HashMap<>();", 25: "this.pos = new BlockPos(tile);"})
    ck("V1.neutron-node", not m, "NeutronNode.java:10-27: type, pos, tile and the untyped data map", m)
    # ---- RBMKNeutronHandler.java
    rl = L["rnh"]
    m = at_lines(rl, {22: "static double moderatorEfficiency;", 23: "reflectorEfficiency", 24: "absorberEfficiency", 25: "static int columnHeight;", 26: "static int fluxRange;", 29: "ROD,", 30: "MODERATOR,", 31: "CONTROL_ROD,",
                      32: "REFLECTOR,", 33: "ABSORBER,", 34: "OUTGASSER,", 35: "OTHER", 39: "Compat.getTileStandard(worldObj", 45: "new RBMKNeutronNode(tile, tile.getRBMKType(), tile.hasLid())",
                      52: 'this.data.put("hasLid", hasLid);', 53: 'this.data.put("type", type);', 58: 'this.data.replace("hasLid", true);', 62: 'this.data.replace("hasLid", false);', 70: "getReaSimNodes()",
                      78: "return (fluxRange + x) * (fluxRange * 2 + 1) + z + fluxRange + 1 < (fluxRange * 2 + 1) * (fluxRange * 2 + 1);", 83: "if(Math.pow(x, 2) + Math.pow(z, 2) <= fluxRange * fluxRange) {", 102: "public List<BlockPos> checkNode(StreamWorld streamWorld)",
                      116: "if(tile instanceof TileEntityRBMKRod && !(tile instanceof TileEntityRBMKRodReaSim))", 118: "if(!rod.hasRod || rod.lastFluxQuantity == 0)", 134: "if(tile instanceof TileEntityRBMKRodReaSim)", 165: "if(rod.hasRod && rod.lastFluxQuantity > 0)",
                      184: "node.tile instanceof TileEntityRBMKRod", 213: "public NeutronNode[] getNodes(StreamWorld streamWorld, boolean addNode)", 220: "Math.floor(0.5 + vector.xCoord * i)", 228: "this.origin.tile.getBlockType() instanceof RBMKBase"})
    ck("V1.rnh-structure", not m, "RBMKNeutronHandler.java:20-240: the static efficiencies, the RBMKType enum, blockPosToTE, makeNode, the node data map and lid methods, getReaSimNodes (hasNext arithmetic :78), checkNode (rod gate :116-118, ReaSim rod :134, circle scan :165, rods along the streams :184), getNodes", m)
    m = at_lines(rl, {242: "public void runStreamInteraction(World worldObj, StreamWorld streamWorld)", 245: "if(fluxQuantity == 0D)", 252: "streamWorld.getNode(pos)", 260: "originTE.getRBMKType(), originTE.hasLid()", 265: "getBlocks(fluxRange)",
                      271: "if(fluxQuantity == 0D)", 281: "int hits = getHits(targetPos);", 282: "if(hits == columnHeight)", 285: "irradiateFromFlux(pos, hits);", 286: "fluxQuantity *= 1 - ((double) hits / columnHeight);",
                      289: "irradiateFromFlux(pos, 0);", 297: "type == RBMKType.OTHER || type == null", 304: 'if(!(boolean) targetNode.data.get("hasLid"))', 305: "(float) (this.fluxQuantity * 0.05F)",
                      307: "type == RBMKType.MODERATOR || nodeTE.isModerated()", 308: "moderatedCount++;", 309: "moderateStream();", 312: "nodeTE instanceof IRBMKFluxReceiver", 315: "type == RBMKType.ROD", 318: "if(rod.hasRod)", 319: "rod.receiveFlux(this);",
                      323: "type == RBMKType.OUTGASSER", 332: "type == RBMKType.CONTROL_ROD", 341: "type == RBMKType.REFLECTOR", 343: "isModerated()", 346: "this.fluxRatio > 0 && moderatedCount > 0", 350: "reflectorEfficiency != 1.0D",
                      351: "this.fluxQuantity *= reflectorEfficiency;", 355: "((TileEntityRBMKRod) originTE).receiveFlux(this);", 357: "type == RBMKType.ABSORBER", 358: "RBMKDials.getAbsorberHeatConversion(worldObj) * this.fluxQuantity",
                      360: "absorberEfficiency == 1", 363: "this.fluxQuantity *= absorberEfficiency;", 367: "getNodes(streamWorld, true)", 369: "nodes[(nodes.length - 1)]", 371: "lastNode == null", 373: "irradiateFromFlux(new BlockPos(origin.tile.xCoord + this.vector.xCoord",
                      379: "lastNodeType == RBMKType.CONTROL_ROD", 400: "public int getHits(BlockPos pos)", 403: "for(int h = 0; h < columnHeight; h++)", 408: "getBlock(pos.getX(), pos.getY() + h, pos.getZ())", 409: "block.isOpaqueCube()",
                      417: "(float) (fluxQuantity * 0.05F * (1 - (double) getHits(pos) / columnHeight))", 421: "(float) (fluxQuantity * 0.05F * (1 - (double) hits / columnHeight))", 425: "fluxRatio *= (1 - moderatorEfficiency);"})
    order = [307, 312, 332, 341, 357]
    ck("V1.rnh-interaction", not m and order == sorted(order), "RBMKNeutronHandler.java:242-426 runStreamInteraction/getHits/irradiateFromFlux/moderateStream: the 0.05F factors, the partial-block formula, the branch order "
       "MODERATOR/isModerated -> IRBMKFluxReceiver (ROD hasRod / OUTGASSER) -> CONTROL_ROD -> REFLECTOR -> ABSORBER, the last-node tail", m)
    # ---- TileEntityRBMKRod.java
    t = L["rod"]
    m = at_lines(t, {49: "extends TileEntityRBMKSlottedBase implements IRBMKFluxReceiver, IRBMKLoadable", 53: "public double fluxFastRatio;", 54: "fluxQuantity", 55: "lastFluxQuantity", 56: "lastFluxRatio", 58: "public boolean hasRod;",
                     59: "public int rodColor = 0;", 62: "private String fuelYield;", 63: "fuelXenon", 64: "fuelHeat", 67: "super(1);", 72: 'return "container.rbmkRod";', 77: "((RBMKRod)this.getBlockType()).moderated", 82: "return 25;",
                     87: "double fastFlux = this.fluxQuantity * this.fluxFastRatio;", 88: "double fastFluxIn = stream.fluxQuantity * stream.fluxRatio;", 90: "this.fluxQuantity += stream.fluxQuantity;", 91: "fluxFastRatio = (fastFlux + fastFluxIn) / fluxQuantity;",
                     96: "ItemRBMKRod.getHullHeat(slots[0]) <= 1_000", 102: "ItemRBMKRod.getHullHeat(slots[0]) <= 200", 111: "ItemRBMKRod.getHullHeat(slots[0]) >= 1500 && !RBMKDials.getMeltdownsDisabled(worldObj)", 112: "this.meltdown();"})
    ck("V1.rod-fields-gates", not m, "TileEntityRBMKRod.java:49-114: fields, one slot, container.rbmkRod, tracking range 25, receiveFlux :86-92, gates <= 1_000 (autoloader) and <= 200 (manual) :94-105, invalidate meltdown at >= 1500 :107-114", m)
    m = at_lines(t, {121: "slots[0].getItem() instanceof ItemRBMKRod", 123: "worldObj.getTotalWorldTime() % 200 == 0", 127: "this.rodColor = rod.colorTint;", 134: "if(rod.specialFluxCurve)", 135: "rod.fluxRatioOut(this.fluxFastRatio, ItemRBMKRod.getEnrichment(slots[0]))",
                     136: "rod.fluxFromRatio(this.fluxQuantity, this.fluxFastRatio)", 137: "rod.burn(worldObj, slots[0], fluxIn)", 140: "if(rType == NType.SLOW)", 141: "fluxRatioOut = 0;", 143: "fluxRatioOut = 1;", 145: "fluxFromType(rod.nType)",
                     146: "rod.burn(worldObj, slots[0], fluxIn)", 149: "rod.updateHeat(worldObj, slots[0], 1.0D);", 150: "this.heat += rod.provideHeat(worldObj, slots[0], heat, 1.0D);", 152: "if(!this.hasLid())", 153: "(float) (this.fluxQuantity * 0.05F)",
                     156: "super.updateEntity();", 158: "if(this.heat > this.maxHeat())", 160: "if(RBMKDials.getMeltdownsDisabled(worldObj))", 161: "ParticleUtil.spawnGasFlame(worldObj, xCoord + 0.5, yCoord + RBMKDials.getColumnHeight(worldObj) + 0.5, zCoord + 0.5, 0, 0.2, 0);",
                     163: "this.meltdown();", 168: "return;", 171: "if(this.heat > 10_000) this.heat = 10_000;", 175: "this.lastFluxQuantity = this.fluxQuantity;", 176: "this.lastFluxRatio = this.fluxFastRatio;", 178: "this.fluxQuantity = 0;",
                     179: "this.fluxFastRatio = 0;", 181: "spreadFlux(fluxQuantityOut, fluxRatioOut);", 183: "hasRod = true;", 187: "this.lastFluxRatio = 0;", 192: "hasRod = false;", 194: "super.updateEntity();"})
    order = [149, 150, 152, 156, 158, 171, 175, 178, 181, 183]
    ck("V1.rod-tick", not m and order == sorted(order), "TileEntityRBMKRod.java:117-197 updateEntity: burn (flux curve or rType), updateHeat, provideHeat, incrementRad when !hasLid (0.05F), super tick, heat > maxHeat (gas flame or meltdown), 10_000 clamp, last*/reset, spreadFlux, hasRod", m)
    m = at_lines(t, {205: "case SLOW: return slowFlux + fastFlux * 0.5;", 206: "case FAST: return fastFlux + slowFlux * 0.3;", 207: "case ANY: return this.fluxQuantity;", 214: "ForgeDirection.NORTH", 215: "ForgeDirection.EAST", 216: "ForgeDirection.SOUTH", 217: "ForgeDirection.WEST",
                     229: "NeutronNodeWorld.removeNode(worldObj, pos);", 233: "NeutronNodeWorld.getOrAddWorld(worldObj)", 237: "RBMKNeutronHandler.makeNode(streamWorld, this)", 246: "new RBMKNeutronHandler.RBMKNeutronStream(node, neutronVector, flux, ratio);"})
    ck("V1.rod-flux", not m, "TileEntityRBMKRod.java:199-248: fluxFromType (SLOW slow + fast * 0.5, FAST fast + slow * 0.3, ANY all), fluxDirs N/E/S/W, spreadFlux (removeNode when flux == 0, one stream per direction)", m)
    m = at_lines(t, {254: 'nbt.hasKey("fluxFast") || nbt.hasKey("fluxSlow")', 256: 'nbt.getDouble("fluxFast") + nbt.getDouble("fluxSlow")', 262: 'nbt.getDouble("fluxQuantity")', 263: 'nbt.getDouble("fluxMod")', 265: 'nbt.getBoolean("hasRod")',
                     273: 'nbt.setDouble("fluxQuantity", this.lastFluxQuantity);', 274: 'nbt.setDouble("fluxMod", this.lastFluxRatio);', 276: 'nbt.setDouble("fluxSlow", this.fluxQuantity * (1 - fluxFastRatio));', 277: 'nbt.setDouble("fluxFast", this.fluxQuantity * fluxFastRatio);',
                     279: 'nbt.setBoolean("hasRod", this.hasRod);', 285: "buf.writeDouble(this.lastFluxQuantity);", 286: "buf.writeDouble(this.lastFluxRatio);", 287: "buf.writeBoolean(this.hasRod);", 288: "buf.writeInt(this.rodColor);",
                     291: '" / " + rod.yield + " ("', 292: 'ItemRBMKRod.getPoison(slots[0]) + "%"', 294: 'String.format("%.6f"', 296: 'String.format("%.2f", rod.meltingPoint)', 302: "this.fluxQuantity = buf.readDouble();", 303: "this.fluxFastRatio = buf.readDouble();",
                     321: 'nbt.setString("f_yield", fuelYield);', 322: 'nbt.setString("f_xenon", fuelXenon);', 323: 'nbt.setString("f_heat", fuelHeat);'})
    ck("V1.rod-nbt-sync", not m, "TileEntityRBMKRod.java:251-325: NBT keys fluxQuantity/fluxMod/hasRod (diag: fluxSlow/fluxFast, read compat :254-260), sync order lastFluxQuantity, lastFluxRatio, hasRod, rodColor, three strings, f_yield/f_xenon/f_heat", m)
    m = at_lines(t, {331: "int h = RBMKDials.getColumnHeight(worldObj);", 332: "MathHelper.clamp_int(reduce, 1, h)", 334: "worldObj.rand.nextInt(3) == 0", 335: "reduce++;", 337: "boolean corium = slots[0] != null", 342: "slots[0] = null;", 346: "for(int i = h; i >= 0; i--)",
                     347: "worldObj.setBlock(xCoord, yCoord + i, zCoord, ModBlocks.corium_block, 5, 3);", 351: "1 + worldObj.rand.nextInt(RBMKDials.getColumnHeight(worldObj))", 354: "spawnDebris(DebrisType.FUEL);", 357: "this.standardMelt(reduce);",
                     362: "2 + worldObj.rand.nextInt(2)", 365: "spawnDebris(DebrisType.GRAPHITE);", 369: "spawnDebris(DebrisType.ELEMENT);", 371: "this.getBlockMetadata() == RBMKBase.DIR_NORMAL_LID.ordinal() + RBMKBase.offset", 372: "spawnDebris(DebrisType.LID);"})
    order = [342, 346, 351, 357, 362, 369, 371]
    ck("V1.rod-melt", not m and order == sorted(order), "TileEntityRBMKRod.java:328-373 onMelt: clamp, 1/3 reduce++, slot cleared, corium h..0 then 1 + rand(h) FUEL debris else standardMelt, 2 + rand(2) GRAPHITE when moderated, ELEMENT, LID when the normal lid", m)
    m = at_lines(t, {392: 'data.setDouble("enrichment"', 393: 'data.setDouble("xenon"', 394: 'data.setDouble("c_heat", ItemRBMKRod.getHullHeat(slots[0]));', 395: 'data.setDouble("c_coreHeat"', 396: 'data.setDouble("c_maxHeat", rod.meltingPoint);',
                     404: "return toLoad != null && slots[0] == null;", 409: "slots[0] = toLoad.copy();", 410: "this.markDirty();", 415: "return slots[0] != null;", 420: "return slots[0];", 425: "slots[0] = null;", 426: "this.markDirty();"})
    ck("V1.rod-console-loadable", not m, "TileEntityRBMKRod.java:386-427: console keys enrichment/xenon/c_heat/c_coreHeat/c_maxHeat, IRBMKLoadable (canLoad = non-null stack and an empty slot, load copies, provideNext returns the slot, unload empties)", m)
    m = at_lines(t, {557: 'PREFIX_VALUE + "columnheat"', 558: '"rodheat"', 559: '"depletion"', 560: '"xenon"', 561: '"fastflux"', 562: '"slowflux"', 563: '"flux"', 569: "return \"\" + (int) this.heat;", 571: "(int) ItemRBMKRod.getHullHeat(slots[0])",
                     572: "(int) (100 - ItemRBMKRod.getEnrichment(slots[0]) * 100)", 573: "(int) (ItemRBMKRod.getPoison(slots[0]))", 575: "(int) (lastFluxQuantity * lastFluxRatio)", 576: "(int) (lastFluxQuantity * (1 - lastFluxRatio))"})
    ck("V1.rod-ror", not m, "TileEntityRBMKRod.java:554-579 IRORValueProvider: seven values columnheat, rodheat, depletion, xenon, fastflux, slowflux, flux in that order", m)
    ck("V1.rod-no-control", "IControlReceiver" not in inp.o["rod"], "TileEntityRBMKRod does not implement IControlReceiver (no take-rod packet, task book correction)")
    # ---- RBMKRod.java, ContainerRBMKRod.java, GUIRBMKRod.java
    b = L["rodblk"]
    m = at_lines(b, {23: "public boolean moderated = false;", 33: "isOpaqueCube() { return false; }", 38: "if(meta >= this.offset) return new TileEntityRBMKRod();", 39: "if(hasExtra(meta)) return new TileEntityProxyCombo().inventory();",
                     45: "!world.isRemote && meta >= this.offset && !RBMKDials.getMeltdownsDisabled(world)", 47: "tile.explodeOnBroken", 48: "ItemRBMKRod.getHullHeat(tile.slots[0]) >= 1500", 49: "tile.meltdown();", 53: "super.breakBlock(", 78: "instanceof ItemRBMKLid",
                     79: "if(!rbmk.hasLid()) return false;", 82: "instanceof ItemRBMKRod && rbmk.slots[0] == null", 84: "stackSize = 1;", 85: "if(!player.capabilities.isCreativeMode) player.getHeldItem().stackSize--;",
                     86: 'world.playSoundEffect(x + 0.5, y + 0.5, z + 0.5, "hbm:item.upgradePlug", 1.0F, 1.0F);', 87: "return false;", 90: "if(!player.isSneaking())", 91: "FMLNetworkHandler.openGui("})
    ck("V1.rod-block", not m, "RBMKRod.java:23-96: moderated flag, not opaque, core TE for meta >= offset and an inventory proxy for extras, breakBlock melts a core with hull >= 1500, onBlockActivated (lid rule, rod insert with creative check and upgradePlug sound, GUI unless sneaking)", m)
    c = L["cont"]
    m = at_lines(c, {18: "new Slot(tedf, 0, 80, 45)", 22: "8 + j * 18, 84 + i * 18 + 20", 27: "8 + i * 18, 142 + 20", 34: "index == 0 && !player.capabilities.isCreativeMode", 36: "rbmk.coldEnoughForManual()", 61: "if(!rbmk.coldEnoughForManual() && !player.capabilities.isCreativeMode) return null;",
                     62: "mergeItemStack(var5, rbmk.getSizeInventory(), this.inventorySlots.size(), true)", 65: "mergeItemStack(var5, 0, rbmk.getSizeInventory(), false)"})
    ck("V1.rod-container", not m, "ContainerRBMKRod.java: slot 0 at (80, 45), player inventory at y 84 + i * 18 + 20 and hotbar 142 + 20, slot 0 clicks and shift-clicks gated by coldEnoughForManual outside creative", m)
    g = L["gui"]
    m = at_lines(g, {24: "xSize = 176;", 25: "ySize = 186;", 32: "!rod.coldEnoughForAutoloader()", 33: '"Fuel skin temperature has exceeded 1,000°C,", "autoloaders can no longer cycle fuel!"', 34: "!rod.coldEnoughForManual()", 35: '"Fuel skin temperature has exceeded 200°C,", "fuel can no longer be removed by hand!"',
                     42: "this.xSize / 2 - this.fontRendererObj.getStringWidth(name) / 2, 6, 4210752", 43: "8, this.ySize - 96 + 2, 4210752", 53: "drawTexturedModalRect(guiLeft + 34, guiTop + 21, 176, 0, 18, 67);", 55: "double depletion = 1D - ItemRBMKRod.getEnrichment(rod.slots[0]);",
                     56: "int d = (int)(depletion * 67);", 57: "drawTexturedModalRect(guiLeft + 34, guiTop + 21, 194, 0, 18, d);", 59: "ItemRBMKRod.getPoisonLevel(rod.slots[0])", 60: "int x = (int)(xenon * 58);", 61: "drawTexturedModalRect(guiLeft + 126, guiTop + 82 - x, 212, 58 - x, 14, x);",
                     64: "drawInfoPanel(guiLeft - 16, guiTop + 20, 16, 16, 6);", 65: "drawInfoPanel(guiLeft - 16, guiTop + 36, 16, 16, 7);"})
    ck("V1.rod-gui", not m, "GUIRBMKRod.java: 176 x 186, depletion bar (34,21)+(194,0,18,(1-enrichment)*67), xenon bar (126, 82-x)+(212, 58-x, 14, x) with x = poisonLevel * 58, info panels 6/7 for autoloader and manual, two hard-coded hover texts", m)
    # ---- corium
    m = at_lines(L["corium"], {25: "setQuantaPerBlock(5);", 52: "entity.setInWeb();", 53: "entity.setFire(3);", 54: "entity.attackEntityFrom(ModDamageSource.radiation, 2F);", 57: "ContaminationUtil.contaminate((EntityLivingBase)entity, HazardType.RADIATION, ContaminationType.CREATIVE, 1F);",
                                72: "rand.nextInt(10) == 0 && world.getBlock(x, y - 1, z) != this", 75: "ModBlocks.block_corium", 77: "ModBlocks.block_corium_cobble"})
    ck("V1.corium", not m and "setResistance(500F)" in L["mb"][2336] and "new CoriumFinite(corium_fluid, fluidcorium)" in L["mb"][2336], "CoriumFinite.java:50-58 sets the entity in a web, on fire for 3, 2F radiation damage and CREATIVE 1F contamination; ModBlocks.java:2337 corium_block resistance 500F; "
       ":72-78 the 1/10 solidify into block_corium / cobble stays unported", m)
    # ---- meltdown step and node removal in TileEntityRBMKBase
    m = at_lines(L["base"], {239: "NeutronNodeWorld.removeNode(worldObj, new BlockPos(this));", 245: "NeutronNodeWorld.removeNode(worldObj, new BlockPos(this));", 477: "for(TileEntityRBMKBase rbmk : columns)", 479: "rbmk instanceof TileEntityRBMKRod && worldObj.getBlock(rbmk.xCoord, rbmk.yCoord, rbmk.zCoord) == ModBlocks.corium_block",
                             481: "x = rbmk.xCoord - 1; x <= rbmk.xCoord + 1", 482: "y = rbmk.yCoord - 1; y <= rbmk.yCoord + 1", 483: "z = rbmk.zCoord - 1; z <= rbmk.zCoord + 1", 487: "worldObj.rand.nextInt(3) == 0 && (b == ModBlocks.pribris || b == ModBlocks.pribris_burning)",
                             489: "RBMKBase.digamma", 490: "ModBlocks.pribris_digamma", 492: "ModBlocks.pribris_radiating"})
    ck("V1.melt-step", not m, "TileEntityRBMKBase.java:237-246 removes the neutron node on invalidate and chunk unload; :477-498 around a fuel column that became corium_block each pribris / pribris_burning in the 3x3x3 box turns into pribris_radiating "
       "(digamma branch) when rand.nextInt(3) == 0, evaluated first", m)
    # ---- recipes, unload
    cm = L["cm"]
    m = at_lines(cm, {987: "if(!GeneralConfig.enable528) {", 991: "new ItemStack(ModBlocks.rbmk_rod, 1)", 992: "new ItemStack(ModBlocks.rbmk_rod_mod, 1)"})
    ck("V1.recipe-rows", not m and '"C", "R", "C", \'C\', STEEL.shell(), \'R\', ModBlocks.rbmk_blank' in cm[990] and "'G', GRAPHITE.block(), 'R', ModBlocks.rbmk_rod, 'B', ModItems.nugget_bismuth" in cm[991]
       and not any("}" == x.strip() or x.strip().startswith("} else") for x in cm[987:991]), "CraftingManager.java:991 shaped rbmk_rod C/R/C (STEEL.shell(), rbmk_blank) and :992 rbmk_rod_mod BGB/GRG/BGB (GRAPHITE.block(), bismuth nugget), both inside the !enable528 branch opened at :987", m)
    ar = L["ar"]
    m = at_lines(ar, {927: "if(!GeneralConfig.enable528) {", 930: "new ComparableStack(ModBlocks.rbmk_rod)", 931: "new ItemStack(ModBlocks.rbmk_blank, 1)", 932: "Mats.MAT_STEEL.id", 933: "setTier(4)", 935: "new ComparableStack(ModBlocks.rbmk_rod_mod)",
                      936: "new ItemStack(ModBlocks.rbmk_rod, 1)", 937: "block_graphite, 4", 938: "nugget_bismuth, 4", 939: "setTier(4)"})
    ck("V1.anvil-rows", not m, "AnvilRecipes.java:927-939: rbmk_rod and rbmk_rod_mod are tier-4 recycling rows (output blank + 2 steel shells; rod + 4 graphite blocks + 4 bismuth nuggets), not construction", m)
    m = at_lines(inp.ol["meh"], {584: "@SubscribeEvent", 585: "public void onUnload(WorldEvent.Unload event)", 586: "NeutronNodeWorld.streamWorlds.remove(event.world);"})
    ck("V1.unload", not m, "ModEventHandler.java:584-587 removes the world's stream world on WorldEvent.Unload", m)
    # ---- language
    en, zh = inp.o_en, inp.o_zh
    want_lines = {"tile.rbmk_rod.name": (6245, 5354), "tile.rbmk_rod_mod.name": (6246, 5355), "tile.corium_block.name": (5420, 4675), "container.rbmkRod": (801, 639), "tile.rbmk.dodd.fluxSlow": (6269, 5950),
                  "tile.rbmk.dodd.fluxFast": (6270, 5951), "tile.rbmk.dodd.hasRod": (6271, 5952), "tile.rbmk.dodd.f_heat": (6280, 5961), "tile.rbmk.dodd.f_xenon": (6281, 5962), "tile.rbmk.dodd.f_yield": (6282, 5963)}
    bad = []
    for neo, orig in UPSTREAM_KEYS:
        e, z = UPSTREAM_EXPECT[neo]
        if not (len(en.get(orig, [])) == 1 and len(zh.get(orig, [])) == 1 and en[orig][0][0] == e and zh[orig][0][0] == z and (en[orig][0][1], zh[orig][0][1]) == want_lines[orig]):
            bad.append(orig)
    ck("V1.lang", not bad, "the ten upstream keys sit once each at en_US.lang:801/5420/6245-6246/6269-6271/6280-6282 and zh_CN.lang:639/4675/5354-5355/5950-5952/5961-5963 with the handoff's texts", bad)
    # ---- resources
    ck("V1.resources", len(inp.o_res) == 23 and all(inp.o_not_imported.values()), "the 23 files to import and the files to leave out (rbmk_element.png, block_corium*.png, the 16 ReaSim textures) exist in the original", [k for k, v in inp.o_not_imported.items() if not v] + [k for _, k in IMPORTS if RES + k not in inp.o_res])


# ---------------------------------------------------------------- V2 neutron package against V1

# 1.7.10 -> 1.21.1 renames applied to the squashed original before the per-method rules below
ORW = [
    (r"Vec3\.createVectorHelper\(", "newVec3("),
    (r"TileEntityRBMKBase", "RBMKBaseBlockEntity"), (r"TileEntityRBMKRod", "RBMKRodBlockEntity"), (r"TileEntityRBMKAbsorber", "RBMKAbsorberBlockEntity"),
    (r"TileEntity", "BlockEntity"),
    (r"getWorldObj\(\)", "getLevel()"), (r"worldObj", "level"), (r"(?<![A-Za-z])World(?![A-Z])", "Level"),
    (r"RBMKDials\.(\w+)\(level\)", r"RBMKDials.\1()"),
    (r"vector\.xCoord", "vector.x"), (r"vector\.zCoord", "vector.z"),
]


def lit(old, new):
    """A literal replacement rule for rewrite()."""
    return re.escape(old), new.replace("\\", "\\\\")


NEO_SIGS = {
    "nh.tick": (NODEH, "public static void onServerTick(MinecraftServer server)"),
    "nnw.getNode": (NNW, "public static NeutronNode getNode(Level level, BlockPos pos)"),
    "nnw.removeNode": (NNW, "public static void removeNode(Level level, BlockPos pos)"),
    "nnw.getOrAddWorld": (NNW, "public static StreamWorld getOrAddWorld(Level level)"),
    "nnw.removeAllWorlds": (NNW, "public static void removeAllWorlds()"),
    "nnw.removeEmptyWorlds": (NNW, "public static void removeEmptyWorlds()"),
    "nnw.runStreamInteractions": (NNW, "public void runStreamInteractions(Level level)"),
    "nnw.addStream": (NNW, "public void addStream(NeutronStream stream)"),
    "nnw.removeAllStreams": (NNW, "public void removeAllStreams()"),
    "nnw.cleanNodes": (NNW, "public void cleanNodes()"),
    "nnw.sgetNode": (NNW, "public NeutronNode getNode(BlockPos pos)"),
    "nnw.addNode": (NNW, "public void addNode(NeutronNode node)"),
    "nnw.sremoveNode": (NNW, "public void removeNode(BlockPos pos)"),
    "nnw.removeAllStreamsOfType": (NNW, "public void removeAllStreamsOfType(NeutronStream.NeutronType type)"),
    "ns.ctor1": (NSTREAM, "public NeutronStream(NeutronNode origin, Vec3 vector)"),
    "ns.ctor2": (NSTREAM, "public NeutronStream(NeutronNode origin, Vec3 vector, double flux, double ratio, NeutronType type)"),
    "ns.hasNext": (NSTREAM, "public boolean hasNext()"),
    "ns.next": (NSTREAM, "public BlockPos next()"),
    "rnh.blockPosToTE": (RNH, "private static BlockEntity blockPosToTE(Level level, BlockPos pos)"),
    "rnh.makeNode": (RNH, "public static RBMKNeutronNode makeNode(StreamWorld streamWorld, RBMKBaseBlockEntity tile)"),
    "rnh.nodeCtor": (RNH, "public RBMKNeutronNode(RBMKBaseBlockEntity tile, RBMKType type, boolean hasLid)"),
    "rnh.addLid": (RNH, "public void addLid()"),
    "rnh.removeLid": (RNH, "public void removeLid()"),
    "rnh.hasNext": (RNH, "public boolean hasNext()"),
    "rnh.next": (RNH, "public BlockPos next()"),
    "rnh.checkNode": (RNH, "public List<BlockPos> checkNode(StreamWorld streamWorld)"),
    "rnh.getNodes": (RNH, "public NeutronNode[] getNodes(StreamWorld streamWorld, boolean addNode)"),
    "rnh.run": (RNH, "public void runStreamInteraction(Level level, StreamWorld streamWorld)"),
    "rnh.getHits": (RNH, "public int getHits(BlockPos pos)"),
    "rnh.irr1": (RNH, "public void irradiateFromFlux(BlockPos pos)"),
    "rnh.irr2": (RNH, "public void irradiateFromFlux(BlockPos pos, int hits)"),
    "rnh.moderate": (RNH, "public void moderateStream()"),
}

NNW_RULES = [(r"\(world\)", "(level)"), (r"\(world,", "(level,")]
# key -> (strip before the renames, cuts after them [(start, end)], rules after the cuts)
NEUTRON_SPEC = {
    "nh.tick": (["if(event.phase!=TickEvent.Phase.START)return;"], [], [(r"RBMKDials\.(\w+)\(world\.getKey\(\)\)", r"RBMKDials.\1()")]),
    "ns.ctor1": ([], [], [lit("posInstance=origin.pos.clone();", "posInstance=origin.pos.mutable();")]),
    "ns.ctor2": ([], [], [lit("posInstance=origin.pos.clone();", "posInstance=origin.pos.mutable();")]),
    "ns.next": ([], [], [lit("returnposInstance.mutate(origin.tile.xCoord+x,origin.tile.yCoord,origin.tile.zCoord+z);",
                             "returnposInstance.set(origin.pos.getX()+x,origin.pos.getY(),origin.pos.getZ()+z);")]),
    "rnh.blockPosToTE": ([], [], [lit("returnCompat.getTileStandard(level,pos.getX(),pos.getY(),pos.getZ());", "returnlevel.isLoaded(pos)?level.getBlockEntity(pos):null;")]),
    "rnh.makeNode": ([], [], [lit("BlockPospos=newBlockPos(tile);", "BlockPospos=tile.getBlockPos();")]),
    "rnh.nodeCtor": ([], [], [lit('this.data.put("hasLid",hasLid);this.data.put("type",type);posInstance=newBlockPos(tile);', "this.hasLid=hasLid;this.rbmkType=type;posInstance=tile.getBlockPos().mutable();")]),
    "rnh.addLid": ([], [], [lit('this.data.replace("hasLid",true);', "this.hasLid=true;")]),
    "rnh.removeLid": ([], [], [lit('this.data.replace("hasLid",false);', "this.hasLid=false;")]),
    "rnh.next": ([], [], [lit("returnposInstance.mutate(tile.xCoord+x,tile.yCoord,tile.zCoord+z);", "returnposInstance.set(pos.getX()+x,pos.getY(),pos.getZ()+z);")]),
    "rnh.checkNode": ([], [("{Iterator<BlockPos>reaSimNodes=getReaSimNodes();if(tileinstanceofRBMKRodBlockEntityReaSim){", "returnlist;}}}")], [
        lit("BlockPospos=newBlockPos(this.tile);", "BlockPospos=this.tile.getBlockPos();"), lit("ForgeDirection[]fluxDirs", "Direction[]fluxDirs"),
        lit("fluxDirs[i].offsetX,0,fluxDirs[i].offsetZ", "fluxDirs[i].getStepX(),0,fluxDirs[i].getStepZ()"),
        lit("if(tileinstanceofRBMKRodBlockEntity&&!(tileinstanceofRBMKRodBlockEntityReaSim)){RBMKRodBlockEntityrod=(RBMKRodBlockEntity)tile;", "if(tileinstanceofRBMKRodBlockEntityrod){"),
        lit("node.tileinstanceofRBMKRodBlockEntity){RBMKRodBlockEntityrod=(RBMKRodBlockEntity)node.tile;", "node.tileinstanceofRBMKRodBlockEntityrod){"),
        lit("list.add(newBlockPos(node.tile));", "list.add(node.tile.getBlockPos());")]),
    "rnh.getNodes": ([], [], [
        lit("BlockPospos=newBlockPos(origin.tile);", "BlockPos.MutableBlockPospos=origin.tile.getBlockPos().mutable();"), lit("Levelworld=origin.tile.getLevel();", "Levellevel=origin.tile.getLevel();"),
        lit("pos.mutate(origin.tile.xCoord+x,origin.tile.yCoord,origin.tile.zCoord+z);", "pos.set(origin.pos.getX()+x,origin.pos.getY(),origin.pos.getZ()+z);"),
        lit("this.origin.tile.getBlockType()instanceofRBMKBase)", "this.origin.tile.getBlockState().getBlock()instanceofRBMKBaseBlock)"), lit("blockPosToTE(world,pos)", "blockPosToTE(level,pos)"),
        lit("if(teinstanceofRBMKBaseBlockEntity){RBMKBaseBlockEntityrbmkBase=(RBMKBaseBlockEntity)te;", "if(teinstanceofRBMKBaseBlockEntityrbmkBase){")]),
    "rnh.run": ([], [("elseif(type==RBMKType.OUTGASSER){", "column.receiveFlux(this);return;}}"), ("elseif(type==RBMKType.CONTROL_ROD){", "continue;}return;}")], [
        lit("BlockPospos=newBlockPos(origin.tile);", "BlockPospos=origin.tile.getBlockPos();"),
        lit("if(teinstanceofRBMKBaseBlockEntity){targetNode=makeNode(streamWorld,(RBMKBaseBlockEntity)te);", "if(teinstanceofRBMKBaseBlockEntityrbmk){targetNode=makeNode(streamWorld,rbmk);"),
        # NEO-only (review B P1): a column in a loaded chunk outside the block-ticking range ends the stream, right after the flux == 0 test
        lit("if(fluxQuantity==0)return;NeutronNodetargetNode=streamWorld.getNode(targetPos);", "if(fluxQuantity==0)return;if(!level.shouldTickBlocksAt(targetPos))return;NeutronNodetargetNode=streamWorld.getNode(targetPos);"),
        # NEO-only hardening: the original casts the origin to TileEntityRBMKRod (a crash when a replaced column is the origin); the return stays
        lit("((RBMKRodBlockEntity)originTE).receiveFlux(this);", "if(originTEinstanceofIRBMKFluxReceiverreceiver)receiver.receiveFlux(this);"),
        lit('irradiateFromFlux(newBlockPos(origin.tile.xCoord+this.vector.x,origin.tile.yCoord,origin.tile.zCoord+this.vector.z));',
            "irradiateFromFlux(BlockPos.containing(origin.pos.getX()+this.vector.x,origin.pos.getY(),origin.pos.getZ()+this.vector.z));"),
        (r"RBMKTypelastNodeType=.*$", ""),
        lit('RBMKTypetype=(RBMKType)targetNode.data.get("type");', "RBMKTypetype=((RBMKNeutronNode)targetNode).getRBMKType();"),
        lit('if(!(boolean)targetNode.data.get("hasLid"))ChunkRadiationManager.proxy.incrementRad(level,targetPos.getX(),targetPos.getY(),targetPos.getZ(),',
            "if(!((RBMKNeutronNode)targetNode).hasLid())ChunkRadiationManager.proxy.incrementRad(level,targetPos,")]),
    "rnh.getHits": ([], [], [lit("Blockblock=origin.tile.getLevel().getBlock(pos.getX(),pos.getY()+h,pos.getZ());if(block.isOpaqueCube())hits+=1;",
                                 "Levellevel=origin.tile.getLevel();BlockPosabove=pos.above(h);BlockStatestate=level.getBlockState(above);if(state.isSolidRender(level,above))hits+=1;")]),
    "rnh.irr1": ([], [], [lit("incrementRad(origin.tile.getLevel(),pos.getX(),pos.getY(),pos.getZ(),", "incrementRad(origin.tile.getLevel(),pos,")]),
    "rnh.irr2": ([], [], [lit("incrementRad(origin.tile.getLevel(),pos.getX(),pos.getY(),pos.getZ(),", "incrementRad(origin.tile.getLevel(),pos,")]),
}


def expected_body(inp, key, spec=None, orw=ORW, default=None):
    """The squashed original body of key, renamed and adapted as its spec says: what the NEO method must equal."""
    strip, cuts, rules = (spec or NEUTRON_SPEC).get(key, default or ([], [], []))
    a = need_ov(inp).b[key]
    for s in strip:
        if s not in a:
            raise ValueError(f"{key}: {s!r} not in the original body")
        a = a.replace(s, "", 1)
    a = rewrite(a, orw)
    for start, end in cuts:
        a = cut(a, start, end)
    return rewrite(a, rules)


def neo_body(st, sigs, key):
    path, sig = sigs[key]
    return body(st.text(path), sig)


def compare_group(ck, cid, label, inp, st, keys, spec=None, orw=ORW, sigs=None, default=None):
    bad = {}
    for key in keys:
        try:
            a, b = expected_body(inp, key, spec, orw, default), neo_body(st, sigs or NEO_SIGS, key)
        except ValueError as error:
            bad[key] = repr(error)
            continue
        if not a or a != b:
            bad[key] = first_diff(a, b)
    return ck(cid, not bad, label, bad)


def v2_neutron(ck, inp, st):
    need_ov(inp)
    txt = {p: lf(st.text(p)) for p in NEUTRON + [PKG]}
    code = {p: code_of(t) for p, t in txt.items()}
    extra = sorted(p for p in st.tree if p.startswith(J + "handler/neutron/") and p not in NEUTRON + [PKG])
    ck("V2.classes", all(st.has(p) for p in NEUTRON) and not extra and not any("PileNeutron" in p for p in st.tree), "the five NEO classes (NeutronHandler, NeutronNodeWorld, NeutronNode, NeutronStream, RBMKNeutronHandler) exist in com.hbm.handler.neutron and "
       "nothing else does: no PileNeutronHandler (the Chicago Pile is not migrated)", extra)
    iso = [p for p in NEUTRON + [PKG] if "net.minecraft.client" in txt[p] or "com.hbm.render" in txt[p]]
    ck("V2.client-isolation", not iso, "the neutron package imports no net.minecraft.client or render class", iso)
    # ---- NeutronHandler
    compare_group(ck, "V2.handler-tick", "NeutronHandler.onServerTick equals the original :16-49 body (cacheTime 20, cacheClear = ticks >= 20 then reset, ticks++, removeEmptyWorlds before the loop, the three efficiencies, "
                  "columnHeight = getColumnHeight() + 1, fluxRange, runStreamInteractions, removeAllStreams, cleanNodes when cacheClear) without the START phase guard", inp, st, ["nh.tick"])
    nh = code[NODEH]
    ck("V2.handler-static", "privatestaticintticks=0;" in nh and "intcacheTime=20;" in nh and nh.index("NeutronNodeWorld.removeEmptyWorlds();") < nh.index("for(Map.Entry<Level,NeutronNodeWorld.StreamWorld>world"),
       "NeutronHandler keeps the static ticks counter, cacheTime 20 and removes the empty worlds before the loop")
    # ---- NeutronNodeWorld
    keys = [k for k in NEO_SIGS if k.startswith("nnw.")]
    compare_group(ck, "V2.node-world-methods", "NeutronNodeWorld and StreamWorld methods equal the original (getNode, removeNode, getOrAddWorld, removeAllWorlds, removeEmptyWorlds, runStreamInteractions, addStream, removeAllStreams, "
                  "cleanNodes with the pile TODO as a comment, getNode, addNode, removeNode, removeAllStreamsOfType)", inp, st, keys, spec={k: ([], [], NNW_RULES) for k in keys})
    nw = code[NNW]
    ck("V2.node-world-map", "publicstaticfinalMap<Level,StreamWorld>streamWorlds=newHashMap<>();" in nw and "publicstaticvoidremoveWorld(Levellevel){streamWorlds.remove(level);}" in nw
       and "privateList<NeutronStream>streams;" in nw and "privateHashMap<BlockPos,NeutronNode>nodeCache=newHashMap<>();" in nw,
       "NeutronNodeWorld keeps Map<Level, StreamWorld> in a HashMap, adds removeWorld(Level) (the original ModEventHandler.onUnload removal), and StreamWorld keeps the streams list and the HashMap<BlockPos, NeutronNode> cache")
    # ---- NeutronStream and NeutronNode
    compare_group(ck, "V2.stream", "NeutronStream constructors (the dummy one does not register, the full one adds the stream to the origin's level) and the getBlocks iterator (floor(0.5 + v * i) over one mutable position) equal the original :33-74", inp, st,
                  ["ns.ctor1", "ns.ctor2", "ns.hasNext", "ns.next"])
    ns = code[NSTREAM]
    ck("V2.stream-type", "enumNeutronType{DUMMY,RBMK}" in re.sub(r"\s", "", blank_comments(txt[NSTREAM])) and "publicNeutronTypetype=NeutronType.DUMMY;" in ns and "PILE" not in ns
       and "publicVec3vector;" in ns and "publicNeutronNodeorigin;" in ns, "NeutronType is DUMMY, RBMK (PILE only as a comment), the stream defaults to DUMMY and keeps origin, fluxQuantity, fluxRatio and the Vec3 vector")
    nn = code[NNODE]
    ck("V2.node", "protectedNeutronTypetype;" in nn and "protectedBlockPospos;" in nn and "protectedBlockEntitytile;" in nn and "this.pos=tile.getBlockPos().immutable();" in nn,
       "NeutronNode keeps type, pos (the immutable block position, the cache key) and the block entity")
    # ---- RBMKNeutronHandler
    rn = code[RNH]
    ck("V2.rnh-statics", has_all(rn, "publicstaticdoublemoderatorEfficiency;", "publicstaticdoublereflectorEfficiency;", "publicstaticdoubleabsorberEfficiency;", "publicstaticintcolumnHeight;", "publicstaticintfluxRange;") == [],
       "the efficiencies, columnHeight and fluxRange are public statics (a GameTest driving a stream sets them; the handler overwrites them every tick)")
    compare_group(ck, "V2.rnh-small", "blockPosToTE (isLoaded, no chunk load), makeNode (cached node or a new one), the node constructor, addLid/removeLid, the getReaSimNodes iterator (hasNext arithmetic and next) and moderateStream equal the original",
                  inp, st, ["rnh.blockPosToTE", "rnh.makeNode", "rnh.nodeCtor", "rnh.addLid", "rnh.removeLid", "rnh.hasNext", "rnh.next", "rnh.moderate"])
    compare_group(ck, "V2.rnh-checknode", "checkNode equals the original :102-197 without the ReaSim rod block (rod gate, circle scan for a loaded rod, rods along the four streams, else remove self)", inp, st, ["rnh.checkNode"])
    compare_group(ck, "V2.rnh-getnodes", "RBMKNeutronStream.getNodes equals the original :213-239 (floor(0.5 + v * i), cached node, RBMK block entity -> makeNode, addNode when asked)", inp, st, ["rnh.getNodes"])
    compare_group(ck, "V2.rnh-run", "runStreamInteraction equals the original :242-398 statement for statement: flux == 0, origin node, loop over getBlocks(fluxRange), the partial-block formula and the origin-position irradiation, the 0.05F rad, "
                  "moderator branch, ROD hasRod receiveFlux and return, reflector (moderatedCount, reflectorEfficiency, IRBMKFluxReceiver on the origin), absorber (heat conversion, efficiency), last-node tail; "
                  "only the OUTGASSER and CONTROL_ROD branches and the control-rod tail are left out; two NEO-only deviations, asserted exactly: `if(!level.shouldTickBlocksAt(targetPos)) return;` right after `if(fluxQuantity == 0D) return;` "
                  "in the loop (the stream ends at a position whose chunk does not tick blocks) and the reflector's `if(originTE instanceof IRBMKFluxReceiver receiver) receiver.receiveFlux(this); return;` instead of the original's unchecked cast of the origin", inp, st, ["rnh.run"])
    raw_run = lf(st.text(RNH))
    ck("V2.rnh-tick-guard", sq(body(raw_run, "public void runStreamInteraction(Level level, StreamWorld streamWorld)")).count("if(!level.shouldTickBlocksAt(targetPos))return;") == 1
       and sq(raw_run).count("shouldTickBlocksAt(") == 1 and "// NEO-only: in 1.7.10 every loaded tile entity ticks" in raw_run,
       "the shouldTickBlocksAt guard occurs once, in runStreamInteraction, and is documented as a NEO-only rule (the 1.7.10 original ticks every loaded tile entity)")
    run = neo_body(st, NEO_SIGS, "rnh.run")
    order = [run.find(m) for m in ("type==RBMKType.MODERATOR||nodeTE.isModerated()", "nodeTEinstanceofIRBMKFluxReceiver", "type==RBMKType.ROD", "elseif(type==RBMKType.REFLECTOR)", "elseif(type==RBMKType.ABSORBER)", "getNodes(streamWorld,true)")]
    raw = lf(st.text(RNH))
    ck("V2.rnh-branch-order", all(i >= 0 for i in order) and order == sorted(order) and "RBMKType.CONTROL_ROD" not in rn and "RBMKType.OUTGASSER" not in rn and "OUTGASSER" in raw and "CONTROL_ROD" in raw
       and "Goal 25" in raw and "Goal24D" in raw and "getRBMKType()==" not in run,
       "the branch order is MODERATOR/isModerated -> IRBMKFluxReceiver (ROD hasRod) -> REFLECTOR -> ABSORBER -> last node; OUTGASSER (Goal 25) and CONTROL_ROD (Goal24D) appear only in comments", order)
    compare_group(ck, "V2.rnh-getHits", "getHits counts the blocks of [0, columnHeight) above the position with isSolidRender (the 1.7.10 Block.isOpaqueCube), irradiateFromFlux scales by 0.05F * (1 - hits / columnHeight) with the origin-position quirk kept in run",
                  inp, st, ["rnh.getHits", "rnh.irr1", "rnh.irr2"])
    ck("V2.rnh-type-enum", has_all(code_of(st.text(BE + "RBMKType.java")), "enumRBMKType{ROD,MODERATOR,CONTROL_ROD,REFLECTOR,ABSORBER,OUTGASSER,OTHER") == [] and "importcom.hbm.blockentity.machine.rbmk.RBMKType;" in rn
       and "enumRBMKType" not in rn, "the node uses the 24A enum RBMKType (ROD, MODERATOR, CONTROL_ROD, REFLECTOR, ABSORBER, OUTGASSER, OTHER) like the original RBMKNeutronHandler.RBMKType")
    ck("V2.rnh-dials", has_all(code_of(st.text(DIALS)), "publicstaticdoublegetReflectorEfficiency()", "publicstaticdoublegetAbsorberEfficiency()", "publicstaticdoublegetModeratorEfficiency()", "publicstaticintgetColumnHeight()", "publicstaticintgetFluxRange()",
                                          "publicstaticdoublegetAbsorberHeatConversion()") == [], "the RBMKDials facade has the world-free getters the handler calls (24A)")
    # ---- package-info keeps the original text
    otext_pkg = inp.o["pkg"]
    start = otext_pkg.index("Hello all, especially Bobcat!!")
    end = otext_pkg.index("*/")
    ck("V2.package-info", otext_pkg[start:end] in txt[PKG] and "Goal24C" in txt[PKG] and "not migrated" in txt[PKG] and txt[PKG].startswith("package com.hbm.handler.neutron;"),
       "package-info.java keeps the original nodespace documentation verbatim (authorship text) and marks the Chicago Pile parts as not migrated")
    return dict(opaque_predicate="BlockState.isSolidRender(level, pos)" if "state.isSolidRender(level,above)" in run or "isSolidRender" in neo_body(st, NEO_SIGS, "rnh.getHits") else "unknown")


# ---------------------------------------------------------------- V3 NtmEventHandler

def v3_event_handler(ck, inp, st):
    live = lf(st.text(EH))
    start = inp.start[EH]
    code = blank_comments(live)
    tick = body(live, "public static void onServerTick(ServerTickEvent.Pre event)")
    calls = ["RTTYSystem.updateBroadcastQueue(event.getServer());", "UniNodespace.updateNodespace(event.getServer());", "MachineRadarBlockEntity.updateSystem(event.getServer());", "MeteorStrikeSystem.update(event.getServer());",
             "NeutronHandler.onServerTick(event.getServer());"]
    ck("V3.tick-order", tick == "".join(calls) and sq(code).count("NeutronHandler.onServerTick(") == 1,
       "ServerTickEvent.Pre calls RTTY, UniNodespace, radar, meteor and then NeutronHandler.onServerTick once (original NeutronHandler runs on the START phase; the four earlier calls keep their order)", tick)
    old_tick = body(start, "public static void onServerTick(ServerTickEvent.Pre event)")
    ck("V3.old-calls-unchanged", old_tick == "".join(calls[:4]), "the start copy's handler held exactly the four earlier calls in the same order", old_tick)
    unload = body(live, "public static void onLevelUnload(LevelEvent.Unload event)")
    ck("V3.unload", unload == "if(event.getLevel()instanceofLevellevel){UniNodespace.removeLevel(level);BlockEntityAccessCache.clearLevel(level);NeutronNodeWorld.removeWorld(level);}",
       "LevelEvent.Unload removes the level's neutron stream world after the two existing removals (original ModEventHandler.onUnload :584-587)", unload)
    stop = body(live, "public static void onServerStopped(ServerStoppedEvent event)")
    ck("V3.stop", stop == "for(Levellevel:newArrayList<>(UniNodespace.levels.keySet()))UniNodespace.removeLevel(level);BlockEntityAccessCache.cache.clear();NeutronNodeWorld.removeAllWorlds();",
       "ServerStoppedEvent clears every neutron stream world after the two existing clears (NEO-only: the original never clears on stop)", stop)
    dele, ins = diff_summary(start, live)
    code_ins = [x for x in ins if not x.startswith("//")]
    ck("V3.only-additions", not dele and sorted(code_ins) == sorted(["import com.hbm.handler.neutron.NeutronHandler;", "import com.hbm.handler.neutron.NeutronNodeWorld;", "NeutronHandler.onServerTick(event.getServer());",
                                                                      "NeutronNodeWorld.removeWorld(level);", "NeutronNodeWorld.removeAllWorlds();"]) and sum(1 for x in ins if x.startswith("//")) == 3,
       "NtmEventHandler differs from its start copy only by the two imports, the three calls and one comment line each", (dele[:3], ins))
    ck("V3.subscriber-once", live.count("NeutronNodeWorld.removeWorld(") == 1 and live.count("NeutronNodeWorld.removeAllWorlds(") == 1 and "LevelTickEvent" in live and "NeutronHandler" not in body(live, "public static void levelTick(LevelTickEvent.Pre event)"),
       "the neutron hooks are called once each and not from the per-level tick handler")


# ---------------------------------------------------------------- V4 rod block entity against V1

ROD_SIGS = {
    "rod.receiveFlux": (RODBE, "public void receiveFlux(NeutronStream stream)"),
    "rod.autoloader": (RODBE, "public boolean coldEnoughForAutoloader()"),
    "rod.manual": (RODBE, "public boolean coldEnoughForManual()"),
    "rod.update": (RODBE, "public void updateEntity()"),
    "rod.fluxFromType": (RODBE, "public double fluxFromType(NType type)"),
    "rod.spreadFlux": (RODBE, "public void spreadFlux(double flux, double ratio)"),
    "rod.read": (RODBE, "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)"),
    "rod.write": (RODBE, "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)"),
    "rod.serialize": (RODBE, "public void serialize(RegistryFriendlyByteBuf buf)"),
    "rod.deserialize": (RODBE, "public void deserialize(RegistryFriendlyByteBuf buf)"),
    "rod.diag": (RODBE, "public void getDiagData(CompoundTag nbt)"),
    "rod.onMelt": (RODBE, "public void onMelt(int reduce)"),
    "rod.console": (RODBE, "public CompoundTag getNBTForConsole()"),
    "rod.canLoad": (RODBE, "public boolean canLoad(ItemStack toLoad)"),
    "rod.load": (RODBE, "public void load(ItemStack toLoad)"),
    "rod.canUnload": (RODBE, "public boolean canUnload()"),
    "rod.provideNext": (RODBE, "public ItemStack provideNext()"),
    "rod.unload": (RODBE, "public void unload()"),
    "rod.info": (RODBE, "public String[] getFunctionInfo()"),
    "rod.ror": (RODBE, "public String provideRORValue(String name)"),
}

SLOT_RULES = [("ItemRBMKRod", "RBMKRodItem"), (r"slots\[0\]", "stack")]
ROD_SPEC = {
    "rod.autoloader": ([], [], [lit("if(slots[0]!=null&&slots[0].getItem()instanceofItemRBMKRod)", "ItemStackstack=this.slots.get(0);if(stack.getItem()instanceofRBMKRodItem)")] + SLOT_RULES),
    "rod.manual": ([], [], [lit("if(slots[0]!=null&&slots[0].getItem()instanceofItemRBMKRod)", "ItemStackstack=this.slots.get(0);if(stack.getItem()instanceofRBMKRodItem)")] + SLOT_RULES),
    "rod.update": ([], [], [
        (r"^if\(!level\.isRemote\)\{(.*)\}$", r"if(this.level==null||this.level.isClientSide)return;\1"),
        lit("if(slots[0]!=null&&slots[0].getItem()instanceofItemRBMKRod){if(this.fluxQuantity>0&&level.getTotalWorldTime()%200==0)SatelliteRayScan.reportEvent(level,xCoord,yCoord,zCoord,RayEvent.INFO_NUCLEAR,300);ItemRBMKRodrod=((ItemRBMKRod)slots[0].getItem());",
            "ItemStackstack=this.slots.get(0);if(stack.getItem()instanceofRBMKRodItemrod){"),
        lit("rod.burn(level,", "rod.burn(this.level,"), lit("rod.updateHeat(level,", "rod.updateHeat(this.level,"), lit("rod.provideHeat(level,", "rod.provideHeat(this.level,"),
        lit("ChunkRadiationManager.proxy.incrementRad(level,xCoord,yCoord,zCoord,", "ChunkRadiationManager.proxy.incrementRad(this.level,this.worldPosition,"),
        lit("ParticleUtil.spawnGasFlame(level,xCoord+0.5,yCoord+RBMKDials.getColumnHeight()+0.5,zCoord+0.5,0,0.2,0);", "spawnGasFlame();"),
        lit("hasRod=true;}else{", "hasRod=true;this.setChanged();}else{")] + SLOT_RULES),
    "rod.spreadFlux": (["if(pos==null)pos=newBlockPos(this);"], [], [
        lit("removeNode(level,pos)", "removeNode(this.level,this.worldPosition)"), lit("getOrAddWorld(level)", "getOrAddWorld(this.level)"), lit("streamWorld.getNode(pos)", "streamWorld.getNode(this.worldPosition)"),
        lit("ForgeDirectiondir", "Directiondir"), lit("dir.offsetX,dir.offsetY,dir.offsetZ", "dir.getStepX(),dir.getStepY(),dir.getStepZ()")]),
    "rod.read": ([], [], [lit("super.readFromNBT(nbt);", "super.loadAdditional(tag,registries);"), (r"nbt\.hasKey\(", "tag.contains("), (r"nbt\.get(Double|Boolean)\(", r"tag.get\1(")]),
    "rod.write": ([], [], [lit("super.writeToNBT(nbt);", "super.saveAdditional(tag,registries);"), (r"if\(!diag\)\{(.*?)\}else\{.*?\}", r"\1"), (r"nbt\.set(Double|Boolean)\(", r"tag.put\1(")]),
    "rod.serialize": ([], [], [
        lit("ItemRBMKRodrod=((ItemRBMKRod)slots[0].getItem());", "ItemStackstack=this.slots.get(0);if(stack.getItem()instanceofRBMKRodItemrod){"), (r"BufferUtil\.writeString\(buf,", "buf.writeUtf("),
        (r'String\.format\("', 'String.format(Locale.US,"'), (r"(rod\.meltingPoint\)\);)\}$", r'\1}else{buf.writeUtf("");buf.writeUtf("");buf.writeUtf("");}}')] + SLOT_RULES),
    "rod.deserialize": ([], [], [(r"BufferUtil\.readString\(buf\)", "buf.readUtf()")]),
    "rod.onMelt": (["if(corium&&slots[0].getItem()==ModItems.rbmk_fuel_drx)RBMKBase.digamma=true;"], [], [
        (r"^", "LidTypelid=this.getLid();"), lit("MathHelper.clamp_int(", "Mth.clamp("), lit("level.rand.", "level.random."),
        lit("booleancorium=slots[0]!=null&&slots[0].getItem()instanceofItemRBMKRod;", "booleancorium=this.slots.get(0).getItem()instanceofRBMKRodItem;"), lit("slots[0]=null;", "this.slots.set(0,ItemStack.EMPTY);"),
        lit("for(inti=h;i>=0;i--){level.setBlock(xCoord,yCoord+i,zCoord,ModBlocks.corium_block,5,3);level.markBlockForUpdate(xCoord,yCoord+i,zCoord);}",
            "DummyableBlock.safeRem=true;try{for(inti=h;i>=0;i--){level.setBlock(this.worldPosition.above(i),NtmBlocks.CORIUM_BLOCK.get().defaultBlockState(),3);}}finally{DummyableBlock.safeRem=false;}"),
        lit("if(this.getBlockMetadata()==RBMKBase.DIR_NORMAL_LID.ordinal()+RBMKBase.offset)spawnDebris(DebrisType.LID);", "if(lid==LidType.STANDARD)spawnDebris(DebrisType.LID);")]),
    "rod.console": ([], [], [
        lit("NBTTagCompounddata=newNBTTagCompound();", "CompoundTagdata=super.getNBTForConsole();"),
        lit("if(slots[0]!=null&&slots[0].getItem()instanceofItemRBMKRod){ItemRBMKRodrod=((ItemRBMKRod)slots[0].getItem());", "ItemStackstack=this.slots.get(0);if(stack.getItem()instanceofRBMKRodItemrod){"),
        (r"data\.setDouble\(", "data.putDouble(")] + SLOT_RULES),
    "rod.canLoad": ([], [], [lit("returntoLoad!=null&&slots[0]==null;", "return!toLoad.isEmpty()&&this.slots.get(0).isEmpty();")]),
    "rod.load": ([], [], [lit("slots[0]=toLoad.copy();this.markDirty();", "this.slots.set(0,toLoad.copy());this.setChanged();")]),
    "rod.canUnload": ([], [], [lit("returnslots[0]!=null;", "return!this.slots.get(0).isEmpty();")]),
    "rod.provideNext": ([], [], [lit("returnslots[0];", "returnthis.slots.get(0);")]),
    "rod.unload": ([], [], [lit("slots[0]=null;this.markDirty();", "this.slots.set(0,ItemStack.EMPTY);this.setChanged();")]),
    "rod.ror": ([], [], [(r"^", "ItemStackstack=this.slots.get(0);"), lit("if(slots[0]!=null&&slots[0].getItem()instanceofItemRBMKRod){", "if(stack.getItem()instanceofRBMKRodItem){")] + SLOT_RULES),
}


def v4_rod(ck, inp, st):
    need_ov(inp)
    raw = lf(st.text(RODBE))
    code = code_of(raw)
    ck("V4.class", "publicclassRBMKRodBlockEntityextendsRBMKSlottedBaseBlockEntityimplementsIRBMKFluxReceiver,IRBMKLoadable,IRORValueProvider{" in code and "IControlReceiver" not in code and "IControlReceiver" not in raw,
       "RBMKRodBlockEntity extends the slotted base and implements IRBMKFluxReceiver, IRBMKLoadable and IRORValueProvider; it is not an IControlReceiver (no take-rod packet)")
    ck("V4.fields", has_all(code, "publicdoublefluxFastRatio;", "publicdoublefluxQuantity;", "publicdoublelastFluxQuantity;", "publicdoublelastFluxRatio;", "publicbooleanhasRod;", "publicintrodColor=0;",
                            "privateStringfuelYield;", "privateStringfuelXenon;", "privateStringfuelHeat;", "NtmBlockEntityTypes.RBMK_ROD.get(),pos,state,1)") == [],
       "the fields are the original's (:53-64): flux ratio/quantity, lastFlux*, hasRod, rodColor, three client strings; one slot")
    ck("V4.name-range-moderated", 'publicStringgetContainerName(){return"container.rbmkRod";}' in code and "publicinttrackingRange(){return25;}" in code
       and "publicbooleanisModerated(){returnthis.getBlockState().getBlock()instanceofRBMKRodBlockrod&&rod.moderated;}" in code,
       "getContainerName is container.rbmkRod (getName is Nameable's in NEO), trackingRange (the sync range of networkPackNT) is 25, isModerated reads the block's moderated flag")
    compare_group(ck, "V4.receive-gates", "receiveFlux (:86-92) and the two gates coldEnoughForAutoloader <= 1_000 and coldEnoughForManual <= 200 (:94-105; true when the slot holds no RBMKRodItem) equal the original", inp, st,
                  ["rod.receiveFlux", "rod.autoloader", "rod.manual"], spec=ROD_SPEC, sigs=ROD_SIGS, default=([], [], []))
    compare_group(ck, "V4.tick", "updateEntity equals the original :117-197 in order: rod colour, flux curve or rType, burn, updateHeat, provideHeat, incrementRad when !hasLid (0.05F), super tick, heat > maxHeat (gas flame or meltdown), "
                  "10_000 clamp, last*/reset, spreadFlux, hasRod; only the SatelliteRayScan report is left out and setChanged is added", inp, st, ["rod.update"], spec=ROD_SPEC, sigs=ROD_SIGS)
    compare_group(ck, "V4.flux", "fluxFromType (SLOW slow + fast * 0.5, FAST fast + slow * 0.3, ANY all) and spreadFlux (removeNode when flux == 0, one stream per direction with the step vector) equal the original :199-248", inp, st,
                  ["rod.fluxFromType", "rod.spreadFlux"], spec=ROD_SPEC, sigs=ROD_SIGS)
    ck("V4.flux-dirs", has_all(code, "publicstaticfinalDirection[]fluxDirs=newDirection[]{Direction.NORTH,Direction.EAST,Direction.SOUTH,Direction.WEST};", "publicdoublefluxFromType(NTypetype)") == [],
       "fluxDirs is NORTH, EAST, SOUTH, WEST and fluxFromType is public (GameTests call it)")
    compare_group(ck, "V4.nbt", "loadAdditional keeps the compat read (fluxFast/fluxSlow present -> quantity = fast + slow, ratio = fast / quantity, else fluxQuantity/fluxMod) and hasRod; saveAdditional writes fluxQuantity = lastFluxQuantity, "
                  "fluxMod = lastFluxRatio, hasRod (the original keys)", inp, st, ["rod.read", "rod.write"], spec=ROD_SPEC, sigs=ROD_SIGS)
    compare_group(ck, "V4.sync", "serialize/deserialize keep the original order (lastFluxQuantity, lastFluxRatio, hasRod, rodColor, three strings iff hasRod) with Locale.US formatting and empty strings when the slot holds no rod", inp, st,
                  ["rod.serialize", "rod.deserialize"], spec=ROD_SPEC, sigs=ROD_SIGS)
    # the diag branch: the original writeToNBT's diag half plus getDiagData (:275-279, :315-325)
    orig_write = need_ov(inp).b["rod.write"]
    diag_half = re.search(r"\}else\{(.*?)\}nbt\.setBoolean", orig_write).group(1).replace("nbt.setDouble(", "nbt.putDouble(")
    diag_expected = ("super.getDiagData(nbt);" + diag_half + 'nbt.putBoolean("hasRod",this.hasRod);' + need_ov(inp).b["rod.diag"].split("diag=false;", 1)[1].replace("nbt.setString(", "nbt.putString("))
    eq(ck, "V4.diag", "getDiagData = super (heat) + the original diag branch (fluxSlow = quantity * (1 - ratio), fluxFast = quantity * ratio, hasRod) + f_yield/f_xenon/f_heat when the strings are set (:268-280, :315-325)", diag_expected, neo_body(st, ROD_SIGS, "rod.diag"))
    compare_group(ck, "V4.melt", "onMelt equals the original :328-373 with the lid read first (getLid), the slot cleared before any block change, corium h..0 inside DummyableBlock.safeRem, 1 + rand(h) FUEL debris else standardMelt, "
                  "2 + rand(2) GRAPHITE when moderated, ELEMENT, LID for the standard lid; the DRX flag is left out", inp, st, ["rod.onMelt"], spec=ROD_SPEC, sigs=ROD_SIGS)
    mc = neo_body(st, ROD_SIGS, "rod.onMelt")
    ck("V4.melt-order", mc.index("LidTypelid=this.getLid();") < mc.index("this.slots.set(0,ItemStack.EMPTY);") < mc.index("level.setBlock(") < mc.index("spawnDebris(DebrisType.FUEL)") < mc.index("spawnDebris(DebrisType.GRAPHITE)") < mc.index("spawnDebris(DebrisType.ELEMENT)") < mc.index("spawnDebris(DebrisType.LID)")
       and mc.count("level.random.")  == 3 and "Math.random" not in mc and "newRandom" not in mc, "onMelt reads the lid first, empties the slot, then changes blocks, then spawns FUEL, GRAPHITE, ELEMENT and LID debris, all random rolls from level.random", mc[:200])
    compare_group(ck, "V4.console-loadable-ror", "getNBTForConsole (enrichment, xenon, c_heat = hull, c_coreHeat, c_maxHeat when the slot holds a rod), IRBMKLoadable (canLoad = non-empty stack and an empty slot with no item check, load copies, "
                  "provideNext returns the slot stack itself, unload empties, load/unload setChanged), the seven RoR names and values in the original order equal the original", inp, st,
                  ["rod.console", "rod.canLoad", "rod.load", "rod.canUnload", "rod.provideNext", "rod.unload", "rod.info", "rod.ror"], spec=ROD_SPEC, sigs=ROD_SIGS)
    ck("V4.console-type", "publicRBMKTypegetRBMKType(){returnRBMKType.ROD;}" in code and "publicRBMKColumnTypegetConsoleType(){returnRBMKColumnType.FUEL;}" in code and "returnnewRBMKRodMenu(containerId,inventory,this);" in code,
       "getRBMKType is ROD, getConsoleType is FUEL, createMenu opens RBMKRodMenu")
    flame = body(raw, "private void spawnGasFlame()")
    ck("V4.gas-flame", has_all(flame, "if(!(this.levelinstanceofServerLevelserverLevel))return;", "getPlayerList().broadcast(null,x,y,z,150,serverLevel.dimension(),", 'data.putFloat("scale",6.5)', "NtmParticleTypes.GAS_FLAME.get()",
                               "x,y,z,0,0.2,0,1,0)", "this.worldPosition.getY()+RBMKDials.getColumnHeight()+0.5") == [] and "getX()+0.5" in flame and "getZ()+0.5" in flame,
       "the meltdowns-disabled flame (original ParticleUtil.spawnGasFlame at x + 0.5, y + columnHeight + 0.5, z + 0.5, velocity (0, 0.2, 0), radius 150, scale 6.5) is sent as GAS_FLAME to players within 150 blocks", flame)
    ck("V4.no-client", "net.minecraft.client" not in raw and "com.hbm.render" not in raw, "RBMKRodBlockEntity imports no client class")
    return dict(tracking_range="trackingRange() = 25 feeds networkPackNT(trackingRange()) in RBMKBaseBlockEntity.updateEntity")


def v4_support(ck, inp, st):
    # ---- IRBMKFluxReceiver
    fl, f0 = lf(st.text(FLUX)), inp.start[FLUX]
    enum_live = re.search(r"enum NType \{.*?\n    \}", fl, re.S)
    enum_start = re.search(r"enum NType \{.*?\n    \}", f0, re.S)
    dele, ins = diff_summary(f0, fl)
    ck("V4.flux-receiver", enum_live and enum_start and enum_live[0] == enum_start[0] and "voidreceiveFlux(NeutronStreamstream);" in code_of(fl) and "importcom.hbm.handler.neutron.NeutronStream;" in code_of(fl)
       and [x for x in ins if not x.startswith(("*", "/**", "//"))] == ["import com.hbm.handler.neutron.NeutronStream;", "void receiveFlux(NeutronStream stream);"],
       "IRBMKFluxReceiver adds only receiveFlux(NeutronStream) (original :19) and its import; the NType enum is unchanged against the start copy", (dele, ins))
    # ---- IRBMKLoadable
    ol = inp.o["load"]
    oc = squash_lit(blank_comments(ol)).replace("publicbooleancanLoad", "booleancanLoad").replace("publicvoidload", "voidload").replace("publicbooleancanUnload", "booleancanUnload").replace("publicItemStackprovideNext", "ItemStackprovideNext").replace("publicvoidunload", "voidunload")
    nc = code_of(st.text(LOAD))
    oc = oc.replace("importnet.minecraft.item.ItemStack;", "importnet.minecraft.world.item.ItemStack;").replace("packagecom.hbm.tileentity.machine.rbmk;", "packagecom.hbm.blockentity.machine.rbmk;").replace("publicinterfaceIRBMKLoadable", "publicinterfaceIRBMKLoadable")

    def jd(t):
        return re.findall(r"@param [^\n]*|@return [^\n]*|Loads the given[^\n]*|Removes the next[^\n]*", t)
    ck("V4.loadable", oc == nc and jd(ol) == jd(st.text(LOAD)), "IRBMKLoadable has the original's five methods canLoad/load/canUnload/provideNext/unload on ItemStack with the original javadoc lines", first_diff(oc, nc))
    # ---- RBMKSlottedBaseBlockEntity
    sl = code_of(st.text(SLOT))
    ck("V4.slotted", has_all(sl, "publicabstractclassRBMKSlottedBaseBlockEntityextendsRBMKBaseBlockEntity{", "super(type,pos,state,slotCount);", "publicabstractStringgetContainerName();", "returnComponent.translatable(this.getContainerName());",
                             "publicint[]getSlotsForFace(Directiondirection){returnnewint[0];}", "publicbooleancanPlaceItem(intslot,ItemStackstack){returnfalse;}",
                             "publicbooleancanTakeItemThroughFace(intindex,ItemStackstack,Directiondirection){returnfalse;}", "publicabstract@NullableAbstractContainerMenucreateMenu(") == [] and sl.count("stillValid(") == 1,
       "RBMKSlottedBaseBlockEntity is abstract, passes the slot count, names the container through getContainerName() and exposes no slots to automation (original ISidedInventory); its single stillValid override is asserted in V4.slotted-valid")
    # NEO-only (review A P2): the original ContainerRBMKRod.canInteractWith always returns true; NEO keeps the 4-block reach of Container.stillValidBlockEntity, measured to the nearest block of the column
    raw_slot = lf(st.text(SLOT))
    want_valid = sq("if(this.level == null || this.level.getBlockEntity(this.worldPosition) != this) return false;"
                    "int y = Mth.clamp(Mth.floor(player.getEyeY()), this.worldPosition.getY(), this.worldPosition.getY() + RBMKDials.getColumnHeight());"
                    "return player.canInteractWithBlock(this.worldPosition.atY(y), 4.0D);")
    got_valid = body(raw_slot, "public boolean stillValid(Player player)") if "public boolean stillValid(Player player)" in raw_slot else None
    ck("V4.slotted-valid", got_valid == want_valid and "@OverridepublicbooleanstillValid(Playerplayer){" in sl and "(canInteractWith is always true)" in raw_slot,
       "stillValid is the NEO-only reach rule: false unless this block entity is still the one at its position, the player's eye y clamped to [core y, core y + RBMKDials.getColumnHeight()], then Player.canInteractWithBlock(core.atY(y), 4.0D); "
       "the original ContainerRBMKRod.canInteractWith is always true (the class comment says so)", (got_valid, want_valid))
    # ---- RBMKBaseBlockEntity: only the handoff's changes against the start copy
    live, start = lf(st.text(BASEBE)), inp.start[BASEBE]
    a = code_of(start)
    edits = [
        ("importcom.hbm.entity.projectile.RBMKDebris.DebrisType;", "importcom.hbm.entity.projectile.RBMKDebris.DebrisType;importcom.hbm.handler.neutron.NeutronNodeWorld;importcom.hbm.handler.neutron.RBMKNeutronHandler.RBMKNeutronNode;"),
        ("super(type,pos,state,0);}", "this(type,pos,state,0);}protectedRBMKBaseBlockEntity(BlockEntityType<?extendsRBMKBaseBlockEntity>type,BlockPospos,BlockStatestate,intslotCount){super(type,pos,state,slotCount);}"),
        ("returnstate.hasProperty(RBMKBaseBlock.LID)?state.getValue(RBMKBaseBlock.LID):LidType.NONE;", "if(!state.hasProperty(RBMKBaseBlock.LID))state=this.getBlockState();returnstate.hasProperty(RBMKBaseBlock.LID)?state.getValue(RBMKBaseBlock.LID):LidType.NONE;"),
        ("publicvoidonLidChanged(){}", "publicvoidonLidChanged(){if(this.level==null||this.level.isClientSide)return;if(NeutronNodeWorld.getNode(this.level,this.worldPosition)instanceofRBMKNeutronNodenode){if(this.hasLid())node.addLid();elsenode.removeLid();}}"
                                       "@OverridepublicvoidsetRemoved(){super.setRemoved();if(this.level!=null&&!this.level.isClientSide)NeutronNodeWorld.removeNode(this.level,this.worldPosition);}"
                                       "@OverridepublicvoidonChunkUnloaded(){super.onChunkUnloaded();if(this.level!=null&&!this.level.isClientSide)NeutronNodeWorld.removeNode(this.level,this.worldPosition);}"),
        ("rbmk.onMelt(minDist+1);}", "rbmk.onMelt(minDist+1);}for(RBMKBaseBlockEntityrbmk:columns){if(rbmkinstanceofRBMKRodBlockEntity&&level.getBlockState(rbmk.getBlockPos()).is(NtmBlocks.CORIUM_BLOCK.get())){BlockPoscore=rbmk.getBlockPos();"
                                     "for(intx=core.getX()-1;x<=core.getX()+1;x++){for(inty=core.getY()-1;y<=core.getY()+1;y++){for(intz=core.getZ()-1;z<=core.getZ()+1;z++){BlockPospos=newBlockPos(x,y,z);BlockStateb=level.getBlockState(pos);"
                                     "if(level.random.nextInt(3)==0&&(b.is(NtmBlocks.PRIBRIS.get())||b.is(NtmBlocks.PRIBRIS_BURNING.get()))){level.setBlock(pos,NtmBlocks.PRIBRIS_RADIATING.get().defaultBlockState(),3);}}}}}}")]
    miss = []
    for old, new in edits:
        if a.count(old) != 1:
            miss.append(old[:50])
        a = a.replace(old, new, 1)
    b = code_of(live)
    ck("V4.base-be", not miss and a == b, "RBMKBaseBlockEntity differs from its start copy only by the handoff's changes: the protected slot-count constructor, the getLid fallback, onLidChanged updating the neutron node's lid flag, setRemoved/onChunkUnloaded "
       "removing the node on the server, and the corium 3x3x3 pribris step (random first, pribris/pribris_burning -> pribris_radiating); the digamma branch is a comment", (miss, first_diff(a, b)))
    compact = re.sub(r"\s+", " ", live.replace("//", " "))
    ck("V4.base-be-comments", "(pribris_digamma after an rbmk_fuel_drx meltdown) is not migrated" in compact and "The random roll comes first for every position" in compact, "the corium step documents the random-first order and the unported digamma branch")
    dele, ins = diff_summary(start, live)
    ck("V4.base-be-deletions", dele == ["* Goal 25); adding their NBT keys later stays compatible. The passive columns have no slots; the slotted columns (Goal24C) share", "* this parent, which is why it is a MachineBaseBlockEntity of size 0.", "super(type, pos, state, 0);",
                                          "/** The lid of this column, kept in the core's block state. */", "/** Called on the server after a lid was put on or taken off; the neutron node's lid flag hooks in here (Goal24C). */", "public void onLidChanged() { }",
                                          "// Original :477-498 turns pribris around molten fuel columns (corium_block) into pribris_radiating. That needs the fuel", "// column of Goal24C and is added there; no passive column triggers it."],
       "the only lines of RBMKBaseBlockEntity that left the file are the 24A comments the handoff replaces (class comment, getLid and onLidChanged javadocs, the :477-498 placeholder comment) and the two replaced statements", dele)


# ---------------------------------------------------------------- V5 blocks, menu, screen, renderer, registrations

V5_SIGS = {
    "corium.collide": (CORIUM, "public void stepOn(Level level, BlockPos pos, BlockState state, Entity entity)"),
    "blk.breakBlock": (RODBLK, "public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean isMoving)"),
    "blk.activated": (RODBLK, "protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult)"),
    "cont.transfer": (MENU, "public ItemStack quickMoveStack(Player player, int index)"),
    "gui.bg": (SCREEN, "protected void renderBg(GuiGraphics guiGraphics, float partialTicks, int mouseX, int mouseY)"),
    "gui.draw": (SCREEN, "public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float partialTicks)"),
}
# strip (before the renames), cuts, rules (after the renames); the numbers stay the original's, only the 1.7.10 -> 1.21.1 call shapes are rewritten
V5_SPEC = {
    "corium.collide": ([], [], [
        lit("entity.setInWeb();", "entity.makeStuckInBlock(state,newVec3(0.25,0.05,0.25));if(!level.isClientSide){"),
        lit("entity.setFire(3);", "entity.igniteForSeconds(3);"),
        lit("entity.attackEntityFrom(ModDamageSource.radiation,2);", "entity.hurt(entity.damageSources().source(NtmDamageTypes.RADIATION),2);"),
        lit("if(entityinstanceofEntityLivingBase)ContaminationUtil.contaminate((EntityLivingBase)entity,", "if(entityinstanceofLivingEntityliving)ContaminationUtil.contaminate(living,"),
        (r"$", "}super.stepOn(level,pos,state,entity);")]),
    "blk.breakBlock": ([], [], [
        lit("!world.isRemote&&meta>=this.offset&&!RBMKDials.getMeltdownsDisabled(world)", "!level.isClientSide&&isCore(state)&&!state.is(newState.getBlock())&&!RBMKDials.getMeltdownsDisabled()"),
        (r"RBMKRodBlockEntitytile=\(RBMKRodBlockEntity\)world\.getBlockEntity\(x,y,z\);if\(tile!=null&&tile\.explodeOnBroken\)\{if\(tile\.slots\[0\]!=null&&tile\.slots\[0\]\.getItem\(\)instanceofItemRBMKRod&&ItemRBMKRod\.getHullHeat\(tile\.slots\[0\]\)>=(\d+)\)\{tile\.meltdown\(\);\}\}\}",
         r"if(level.getBlockEntity(pos)instanceofRBMKRodBlockEntityrod){ItemStackstack=rod.slots.get(0);if(stack.getItem()instanceofRBMKRodItem&&RBMKRodItem.getHullHeat(stack)>=\1){rod.meltdown();}}}"),
        lit("super.breakBlock(world,x,y,z,block,meta);world.removeBlockEntity(x,y,z);", "super.onRemove(state,level,pos,newState,isMoving);")]),
    "blk.activated": (["BossSpawnHandler.markFBI(player);"], [], [
        lit("if(world.isRemote)returntrue;int[]pos=this.findCore(world,x,y,z);if(pos==null)returnfalse;BlockEntityte=world.getBlockEntity(pos[0],pos[1],pos[2]);if(!(teinstanceofRBMKRodBlockEntity))returnfalse;RBMKRodBlockEntityrbmk=(RBMKRodBlockEntity)te;",
            # NEO-only (review): the client follows the dummies down itself (walkToCore, like getLid) because findCore uses the block's shared position list, which the integrated server may use at the same moment
            "BlockPoscore=level.isClientSide?this.walkToCore(level,pos):this.findCore(level,pos);if(core==null||!(level.getBlockEntity(core)instanceofRBMKRodBlockEntityrbmk))returnItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;"),
        lit("if(player.getHeldItem()!=null&&player.getHeldItem().getItem()instanceofItemRBMKLid){if(!rbmk.hasLid())returnfalse;}",
            "if(stack.getItem()instanceofRBMKLidItem){if(!rbmk.hasLid())returnItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;}booleanempty=level.isClientSide?!rbmk.hasRod:rbmk.slots.get(0).isEmpty();"),
        lit("if(player.getHeldItem()!=null&&player.getHeldItem().getItem()instanceofItemRBMKRod&&rbmk.slots[0]==null){rbmk.slots[0]=player.getHeldItem().copy();rbmk.slots[0].stackSize=1;if(!player.capabilities.isCreativeMode)player.getHeldItem().stackSize--;",
            "if(stack.getItem()instanceofRBMKRodItem&&empty){if(!level.isClientSide){rbmk.slots.set(0,stack.copyWithCount(1));if(!player.hasInfiniteMaterials())stack.shrink(1);rbmk.setChanged();"),
        lit('world.playSoundEffect(x+0.5,y+0.5,z+0.5,"hbm:item.upgradePlug",1.0,1.0);returnfalse;}',
            "level.playSound(null,pos.getX()+0.5,pos.getY()+0.5,pos.getZ()+0.5,NtmSoundEvents.UPGRADE_PLUG.get(),SoundSource.PLAYERS,1.0,1.0);}returnItemInteractionResult.sidedSuccess(level.isClientSide);}"),
        lit("if(!player.isSneaking()){FMLNetworkHandler.openGui(player,MainRegistry.instance,0,world,pos[0],pos[1],pos[2]);returntrue;}else{returntrue;}", "returnItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;")]),
    "cont.transfer": ([], [], [
        lit("ItemStackvar3=null;", "ItemStackret=ItemStack.EMPTY;"), lit("Slotvar4=(Slot)this.inventorySlots.get(par2);", "Slotslot=this.slots.get(index);"),
        lit("var4!=null&&var4.getHasStack()", "slot.hasItem()"), lit("ItemStackvar5=var4.getStack();var3=var5.copy();", "ItemStackstack=slot.getItem();ret=stack.copy();"),
        lit("par2<=rbmk.getSizeInventory()-1", "index<=be.getContainerSize()-1"),
        lit("if(!rbmk.coldEnoughForManual()&&!player.capabilities.isCreativeMode)returnnull;", "if(!slot.mayPickup(player))returnItemStack.EMPTY;"),
        lit("this.mergeItemStack(var5,rbmk.getSizeInventory(),this.inventorySlots.size(),true)", "this.moveItemStackTo(stack,be.getContainerSize(),this.slots.size(),true)"),
        lit("this.mergeItemStack(var5,0,rbmk.getSizeInventory(),false)", "this.moveItemStackTo(stack,0,be.getContainerSize(),false)"), (r"returnnull;", "returnItemStack.EMPTY;"),
        lit("if(!this.moveItemStackTo(stack,be.getContainerSize(),this.slots.size(),true)){returnItemStack.EMPTY;}", "if(!this.moveItemStackTo(stack,be.getContainerSize(),this.slots.size(),true))returnItemStack.EMPTY;"),
        lit("if(var5.stackSize==0){var4.putStack((ItemStack)null);}else{var4.onSlotChanged();}", "if(stack.isEmpty()){slot.setByPlayer(ItemStack.EMPTY);}else{slot.setChanged();}"), (r"returnvar3;$", "returnret;")]),
    "gui.bg": (["GL11.glColor4f(1.0,1.0,1.0,1.0);Minecraft.getMinecraft().getTextureManager().bindTexture(texture);"], [], [
        lit("drawTexturedModalRect(guiLeft,guiTop,0,0,xSize,ySize);", "guiGraphics.blit(TEXTURE,this.leftPos,this.topPos,0,0,imageWidth,imageHeight);ItemStackstack=be.slots.get(0);"),
        lit("if(rod.slots[0]!=null&&rod.slots[0].getItem()instanceofItemRBMKRod)", "if(stack.getItem()instanceofRBMKRodItem)"),
        (r"drawTexturedModalRect\(guiLeft\+(\d+),guiTop\+(\d+|82-x),", r"guiGraphics.blit(TEXTURE,this.leftPos+\1,this.topPos+\2,"),
        (r"ItemRBMKRod\.(getEnrichment|getPoisonLevel)\(rod\.slots\[0\]\)", r"RBMKRodItem.\1(stack)"),
        (r"this\.drawInfoPanel\(guiLeft-16,guiTop\+(\d+),16,16,(\d)\)", r"this.drawInfoPanel(guiGraphics,this.leftPos-16,this.topPos+\1,\2)"), (r"rod\.coldEnough", "be.coldEnough")]),
    "gui.draw": ([], [], [
        lit("super.drawScreen(mouseX,mouseY,f);", "super.render(guiGraphics,mouseX,mouseY,partialTicks);"), (r"rod\.coldEnough", "be.coldEnough"),
        (r'this\.drawCustomInfoStat\(mouseX,mouseY,guiLeft-16,guiTop\+(\d+),16,16,guiLeft-8,guiTop\+(\d+)\+16,"Fuel skin temperature has exceeded 1,000°C,","autoloaders can no longer cycle fuel!"\)',
         r'this.drawCustomInfoStat(guiGraphics,mouseX,mouseY,this.leftPos-16,this.topPos+\1,16,16,this.leftPos-8,this.topPos+\2+16,lines("container.rbmkRod.autoloaderHot"))'),
        (r'this\.drawCustomInfoStat\(mouseX,mouseY,guiLeft-16,guiTop\+(\d+),16,16,guiLeft-8,guiTop\+(\d+)\+16,"Fuel skin temperature has exceeded 200°C,","fuel can no longer be removed by hand!"\)',
         r'this.drawCustomInfoStat(guiGraphics,mouseX,mouseY,this.leftPos-16,this.topPos+\1,16,16,this.leftPos-8,this.topPos+\2+16,lines("container.rbmkRod.manualHot"))'),
        (r"$", "this.renderTooltip(guiGraphics,mouseX,mouseY);")]),
}


def once(code, *needles):
    """The needles that do not occur exactly once in the squashed code."""
    return [n for n in needles if code.count(n) != 1]


def v5_blocks(ck, inp, st):
    need_ov(inp)
    rod = lf(st.text(RODBLK))
    rc = code_of(rod)
    ck("V5.rod-class", has_all(rc, "publicclassRBMKRodBlockextendsRBMKBaseBlock{", "publicstaticfinalMapCodec<RBMKRodBlock>CODEC=RecordCodecBuilder.mapCodec(", 'Codec.BOOL.fieldOf("moderated").forGetter(block->block.moderated)',
                              ").apply(instance,RBMKRodBlock::new));", "publicfinalbooleanmoderated;", "this.moderated=moderated;", "protectedMapCodec<RBMKRodBlock>codec(){returnCODEC;}") == [],
       "RBMKRodBlock extends RBMKBaseBlock with the final moderated flag (original RBMKRod.java:23, set by the constructor :25-28) and a codec that carries the flag instead of hardwiring a block entity type")
    nbe = body(rod, "public @Nullable BlockEntity newBlockEntity(BlockPos pos, BlockState state)")
    tick = body(rod, "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type)")
    passive = body(lf(st.text(J + "blocks/machine/rbmk/RBMKPassiveBlock.java")), "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type)")
    orig_blk = inp.o["rodblk"]
    ck("V5.rod-entities", nbe == sq("return switch(state.getValue(TYPE)) { case CORE -> new RBMKRodBlockEntity(pos, state); case EXTRA -> new ProxyComboBlockEntity(pos, state); default -> null; };") and "ProxyComboBlockEntity(pos,state)" in nbe
       and "inventory" not in rc.replace("RBMKRodMenu", "") and tick == passive and "DummyBlockType.CORE" in tick and "TileEntityRBMKRod()" in orig_blk and "TileEntityProxyCombo().inventory()" in orig_blk,
       "the core holds the RBMKRodBlockEntity (original :38 meta >= offset) and the extra block a ProxyComboBlockEntity without the item proxy (original :39 `.inventory()` is deliberately dropped, see the class comment); only the core ticks, as the passive columns", (nbe, tick))
    compare_group(ck, "V5.rod-remove", "onRemove equals the original breakBlock :43-55 (server, core, no meltdowns-disabled dial, hull heat >= 1500 melts down before the column is torn down; the explodeOnBroken flag is a constant true; NEO adds the real-removal test)",
                  inp, st, ["blk.breakBlock"], spec=V5_SPEC, sigs=V5_SIGS)
    compare_group(ck, "V5.rod-use", "useItemOn equals the original onBlockActivated :65-96 without markFBI: no core -> skip, a lid item on a column with no lid -> skip, a rod item into an empty slot -> one copy, shrink unless creative, hbm upgrade plug sound at "
                  "the block centre with volume 1 pitch 1, consumed without the GUI; everything else falls through to the GUI; the one NEO-only deviation is the core lookup, "
                  "`level.isClientSide ? this.walkToCore(level, pos) : this.findCore(level, pos)`", inp, st, ["blk.activated"], spec=V5_SPEC, sigs=V5_SIGS)
    walk = body(rod, "private BlockPos walkToCore(Level level, BlockPos pos)") if "private BlockPos walkToCore(Level level, BlockPos pos)" in rod else None
    want_walk = sq("BlockPos.MutableBlockPos cursor = pos.mutable();"
                   "for(int i = 0; i <= 16; i++) {BlockState state = level.getBlockState(cursor);if(state.getBlock() != this) return null;if(isCore(state)) return cursor.immutable();"
                   "cursor.move(getPointingDirection(state).getOpposite());}return null;")
    lid_loop = sq("for(int i = 0; i <= 16; i++) {BlockState state = level.getBlockState(cursor);if(state == null || state.getBlock() != this) return LidType.NONE;if(isCore(state)) return state.getValue(LID);"
                  "cursor.move(getPointingDirection(state).getOpposite());}")
    base_live = lf(st.text(BASEBLK))
    ck("V5.rod-walk-to-core", walk == want_walk and rc.count("this.walkToCore(") == 1 and rc.count("this.findCore(") == 1 and lid_loop in body(base_live, "public LidType getLid(BlockGetter level, BlockPos pos)")
       and "@NullableprivateBlockPoswalkToCore(Levellevel,BlockPospos){" in rc,
       "walkToCore follows getPointingDirection(...).getOpposite() from the clicked block down to the core (isCore) in at most 17 reads (i = 0..16), null when another block is met or the core is not reached, exactly like the loop of RBMKBaseBlock.getLid; "
       "the client path of useItemOn is the only caller and the server path is the only findCore call", (walk, want_walk))
    uw = body(rod, "protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult)")
    ck("V5.rod-gui-open", uw == "returnthis.standardOpenBehavior(level,pos,player);" and "isShiftKeyDown" in code_of(lf(st.text(J + "blocks/DummyableBlock.java"))) if st.has(J + "blocks/DummyableBlock.java") else uw == "returnthis.standardOpenBehavior(level,pos,player);",
       "an empty-handed click opens the menu through standardOpenBehavior, which opens nothing when sneaking (original :90-96 returns true without the GUI when sneaking)", uw)
    ck("V5.rod-sound", "NtmSoundEvents.UPGRADE_PLUG" in rc and re.search(r'world\.playSoundEffect\([^;]*"hbm:item\.upgradePlug"', orig_blk) is not None, "the insert sound is NtmSoundEvents.UPGRADE_PLUG, the NEO name of the original hbm:item.upgradePlug (:86)")
    # ---- corium_block
    cor = lf(st.text(CORIUM))
    cc = code_of(cor)
    compare_group(ck, "V5.corium-contact", "CoriumBlock.stepOn equals CoriumFinite.onEntityCollidedWithBlock :50-58: web slowdown (setInWeb multipliers 0.25 / 0.05 / 0.25), then on the server fire for 3 seconds, 2 radiation damage and "
                  "radiation contamination (CREATIVE, 1) for a living entity", inp, st, ["corium.collide"], spec=V5_SPEC, sigs=V5_SIGS)
    ck("V5.corium-static", "publicclassCoriumBlockextendsBlock{" in cc and not re.search(r"LiquidBlock|FlowingFluid|BaseFlowingFluid|FluidState|getDrops|randomTick|tick\(|neighborChanged|getFluid", blank_comments(cor))
       and cc.count("@Override") == 1, "CoriumBlock is a plain Block with one override (stepOn): no fluid, no flow or solidify tick (original :72-78 and GenericFiniteFluid are not migrated), no drops")
    # ---- registrations of the blocks (NtmBlocks)
    nb = lf(st.text(NB))
    nbc = code_of(nb)
    mb = inp.o["mb"]
    hard = re.search(r"this\.setHardness\((\d+)F\);", inp.o["rbase"])
    res = re.search(r"this\.setResistance\((\d+)F\);", inp.o["rbase"])
    flags = dict(re.findall(r'(rbmk_rod(?:_mod)?) = new RBMKRod\((true|false)\)', mb))
    ck("V5.rod-registration", bool(hard and res) and flags == {"rbmk_rod": "false", "rbmk_rod_mod": "true"}
       and once(nbc, 'DeferredBlock<Block>RBMK_ROD=register("rbmk_rod",', 'DeferredBlock<Block>RBMK_ROD_MOD=register("rbmk_rod_mod",') == []
       and all(f'DeferredBlock<Block>{c}=register("{i}",()->newRBMKRodBlock(BlockBehaviour.Properties.of().noOcclusion().strength({hard[1]}.0F,{res[1]}.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops(),{flags[i]}));'.replace(" ", "") in nbc
               for c, i in (("RBMK_ROD", "rbmk_rod"), ("RBMK_ROD_MOD", "rbmk_rod_mod")))
       and nbc.index("RBMK_ROD=register") < nbc.index("RBMK_ROD_MOD=register") < nbc.index("RBMK_BLANK=register"),
       "NtmBlocks registers rbmk_rod (moderated false) and rbmk_rod_mod (true) once each before rbmk_blank, hardness 3 / resistance 30 (RBMKBase.java:52-56), metal sound and colour as the passive columns, noOcclusion (RBMKRod.isOpaqueCube is false :33)",
       (hard and hard[1], res and res[1], flags))
    brown = "MapColor.brownColor" in mb
    ch = re.search(r'block_corium = new BlockHazard\(Material\.iron\)[^;]*?setHardness\((\d+)\.0F\)', mb)
    cr = re.search(r'corium_block = new CoriumFinite\(corium_fluid, fluidcorium\)\.setBlockName\("corium_block"\)\.setResistance\((\d+)F\)', mb)
    cl = re.search(r'corium_fluid = new CoriumFluid\(\)[^;]*?\.setLuminosity\((\d+)\)', mb)
    ck("V5.corium-registration", bool(ch and cr and cl and brown) and "setImmovableMobility()" in mb
       and once(nbc, 'DeferredBlock<Block>CORIUM_BLOCK=register("corium_block",') == []
       and f"DeferredBlock<Block>CORIUM_BLOCK=register(\"corium_block\",()->newCoriumBlock(BlockBehaviour.Properties.of().strength({ch[1]}.0F,{cr[1]}.0F).mapColor(MapColor.COLOR_BROWN).lightLevel(state->{cl[1]}).pushReaction(PushReaction.BLOCK).requiresCorrectToolForDrops()));" in nbc
       and nbc.index("PRIBRIS_RADIATING=register") < nbc.index("CORIUM_BLOCK=register"),
       "NtmBlocks registers corium_block once after the debris blocks: hardness 100 (as block_corium :1376), resistance 500 (:2337), light 10 (the fluid's luminosity :2335), brown map colour (:1185), immovable -> PushReaction.BLOCK, no sound/opacity changes",
       (ch and ch[1], cr and cr[1], cl and cl[1], brown))


def v5_menu(ck, inp, st):
    need_ov(inp)
    menu = lf(st.text(MENU))
    mc = code_of(menu)
    oc = inp.o["cont"]
    slot = re.search(r"new Slot\(tedf, 0, (\d+), (\d+)\)", oc)
    rows = re.search(r"new Slot\(invPlayer, j \+ i \* 9 \+ 9, (\d+) \+ j \* 18, (\d+) \+ i \* 18 \+ (\d+)\)", oc)
    hot = re.search(r"new Slot\(invPlayer, i, (\d+) \+ i \* 18, (\d+) \+ (\d+)\)", oc)
    ok = bool(slot and rows and hot)
    y_rows = int(rows[2]) + int(rows[3]) if ok else None
    y_hot = int(hot[2]) + int(hot[3]) if ok else None
    ck("V5.menu-layout", ok and has_all(mc, f"this.addSlot(newSlot(be,0,{slot[1]},{slot[2]}){{", f"this.playerInv(inventory,{rows[1]},{y_rows},{y_hot});", "publicclassRBMKRodMenuextendsMenuBase<RBMKRodBlockEntity>{",
                                         "super(NtmMenuTypes.RBMK_ROD.get(),id,be);", "publicRBMKRodMenu(intid,Inventoryinventory,FriendlyByteBufextraData){this(id,inventory,(RBMKRodBlockEntity)CompatExternal.getCoreFromPos(") == []
       and rows[1] == hot[1], "RBMKRodMenu has the one rod slot at (80, 45) and the player inventory at x 8, y 84 + 20 = 104, hotbar 142 + 20 = 162 (ContainerRBMKRod.java:18-28), a client constructor through the core position",
       (slot and slot.groups(), rows and rows.groups(), hot and hot.groups()))
    sc = inp.ol["cont"]
    gate_ok = ("index == 0 && !player.capabilities.isCreativeMode" in sc[33] and "rbmk.coldEnoughForManual()" in sc[35])
    ck("V5.menu-gates", gate_ok and has_all(mc, "publicbooleanmayPlace(ItemStackstack){returnstack.getItem()instanceofRBMKRodItem;}", "publicbooleanmayPickup(Playerplayer){returnplayer.getAbilities().instabuild||be.coldEnoughForManual();}") == [],
       "slot 0 takes only RBMKRodItem (GOAL24 decision 14, NEO-only) and mayPickup is creative || coldEnoughForManual (original slotClick :34-36: outside creative a rod above 200 degrees cannot be taken; pickup, swap, throw and quick-move all ask mayPickup)")
    compare_group(ck, "V5.menu-transfer", "quickMoveStack equals the original transferStackInSlot :51-77: the rod slot moves to the player inventory (refused when it may not be picked up), player stacks merge into slot 0, empty remainder clears the slot",
                  inp, st, ["cont.transfer"], spec=V5_SPEC, sigs=V5_SIGS)


def v5_screen(ck, inp, st):
    need_ov(inp)
    scr = lf(st.text(SCREEN))
    sc = code_of(scr)
    og = inp.o["gui"]
    wh = re.search(r"xSize = (\d+);\s*this\.ySize = (\d+);", og)
    title = re.search(r"drawString\(name, this\.xSize / 2 - this\.fontRendererObj\.getStringWidth\(name\) / 2, (\d+), \d+\)", og)
    inv = re.search(r'drawString\(I18n\.format\("container\.inventory"\), (\d+), this\.ySize - (\d+) \+ (\d+), \d+\)', og)
    ck("V5.screen-layout", bool(wh and title and inv) and has_all(sc, f"this.imageWidth={wh[1]};", f"this.imageHeight={wh[2]};", f"this.titleLabelX=this.imageWidth/2-this.font.width(this.title)/2;", f"this.titleLabelY={title[1]};",
                                                                  f"this.inventoryLabelX={inv[1]};", f"this.inventoryLabelY=this.imageHeight-{inv[2]}+{inv[3]};", "publicclassRBMKRodScreenextendsInfoScreen<RBMKRodMenu>{") == [],
       "RBMKRodScreen is 176 x 186 (GUIRBMKRod.java:24-25), the title is centred at y 6 and the inventory label sits at (8, imageHeight - 96 + 2) (:42-43)", (wh and wh.groups(), title and title.groups(), inv and inv.groups()))
    ck("V5.screen-texture", 'NuclearTechMod.withDefaultNamespace("textures/gui/reactors/gui_rbmk_element.png")' in sc and 'textures/gui/reactors/gui_rbmk_element.png' in og, "the screen binds textures/gui/reactors/gui_rbmk_element.png (original :20)")
    compare_group(ck, "V5.screen-background", "renderBg equals GUIRBMKRod.drawGuiContainerBackgroundLayer :46-66: the panel, then with a rod the 18 x 67 bar at (34, 21), the depletion overlay (194, 0, 18, (1 - enrichment) * 67), the xenon bar at "
                  "(126, 82 - x) from (212, 58 - x) 14 wide with x = poison level * 58, and the info panels 6 (autoloader) and 7 (manual) at (-16, 20) and (-16, 36)", inp, st, ["gui.bg"], spec=V5_SPEC, sigs=V5_SIGS)
    compare_group(ck, "V5.screen-hover", "render equals GUIRBMKRod.drawScreen :28-36: the two hover areas (16 x 16 at (-16, 20) and (-16, 36), text at (-8, +16)) shown while the autoloader / manual gate is closed, as keyed tooltips", inp, st, ["gui.draw"], spec=V5_SPEC, sigs=V5_SIGS)
    # the hover texts: the two local keys carry the original hard-coded lines joined with '$'
    texts = re.findall(r'drawCustomInfoStat\(mouseX, mouseY, guiLeft - 16, guiTop \+ \d+, 16, 16, guiLeft - 8, guiTop \+ \d+ \+ 16, "([^"]*)", "([^"]*)"\)', og)
    en, _ = json_pairs(st.text(EN))
    joined = ["$".join(t) for t in texts]
    ck("V5.screen-texts", len(texts) == 2 and joined == [en.get("container.rbmkRod.autoloaderHot"), en.get("container.rbmkRod.manualHot")]
       and joined == [LOCAL_EXPECT["container.rbmkRod.autoloaderHot"][0], LOCAL_EXPECT["container.rbmkRod.manualHot"][0]],
       "the generated English of container.rbmkRod.autoloaderHot / manualHot is the two hard-coded lines of GUIRBMKRod.java:33 and :35 joined with `$`", (joined, en.get("container.rbmkRod.autoloaderHot")))
    # the info panel icons: InfoScreen type 6 and 7 are the original GuiInfoContainer's
    o_cases = {int(n): tuple(map(int, a)) for n, *a in re.findall(r"case (\d+): drawTexturedModalRect\(x, y, (\d+), (\d+), (\d+), (\d+)\)", inp.o["guiinfo"])}
    n_cases = {int(n): tuple(map(int, a)) for n, *a in re.findall(r"case (\d+) -> guiGraphics\.blit\(GUI_UTIL, x, y,\s*(\d+), (\d+), (\d+), (\d+)\)", lf(st.text(INFO)))}
    ck("V5.screen-panels", o_cases.get(6) == (8, 16, 16, 16) and o_cases.get(7) == (24, 16, 16, 16) and n_cases.get(6) == o_cases.get(6) and n_cases.get(7) == o_cases.get(7),
       "InfoScreen.drawInfoPanel types 6 (large red !) and 7 (large yellow !) blit the same gui_utility rectangles as GuiInfoContainer.drawInfoPanel :114-115", (o_cases.get(6), o_cases.get(7), n_cases.get(6), n_cases.get(7)))
    ck("V5.screen-lines", has_all(sc, "for(Strings:I18nUtil.resolveKeyArray(key))text.add(Component.literal(s));") == [] and sc.count('lines("container.rbmkRod.') == 2, "the hover keys are split on `$` by I18nUtil.resolveKeyArray (the container.zirnox.* convention)")
    ck("V5.screen-client-package", SCREEN.startswith(J + "inventory/screens/") and "net.minecraft.client.gui.GuiGraphics" in scr, "RBMKRodScreen lives in inventory.screens and uses the client GUI classes")


def v5_render(ck, inp, st):
    need_ov(inp)
    rend = lf(st.text(RENDER))
    rc = code_of(rend)
    ofc = inp.o["rfc"]
    orod = inp.o["rrod"]
    bm = lf(st.text(BAKED))
    bc = code_of(bm)
    tex = re.search(r'texture_rods = new ResourceLocation\(RefStrings\.MODID \+ ":textures/blocks/rbmk/(\w+)\.png"\)', ofc)
    thr = re.search(r"if\(rod\.fluxQuantity > (\d+)\) cherenkov = true;", ofc)
    start = re.search(r"GL11\.glTranslated\(0, (0\.\d+), 0\);", ofc)
    step = re.search(r"for\(double j = 0; j <= offset; j \+= ([\d.]+)\)", ofc)
    col = re.search(r"tess\.setColorRGBA_F\(([\d.]+)F, ([\d.]+)F, ([\d.]+)F, ([\d.]+)F\);", ofc)
    verts = re.findall(r"tess\.addVertex\((-?[\d.]+), j, (-?[\d.]+)\);", ofc)
    ok = all([tex, thr, start, step, col]) and len(verts) == 4
    ck("V5.render-rods", ok and has_all(rc, "publicclassRenderRBMKRodextendsRenderRBMKLid<RBMKRodBlockEntity>{", 'returnbe.getBlockState().getBlock()instanceofRBMKRodBlockrod&&rod.moderated?"rbmk_element_mod":"rbmk_element";',
                                         "booleanhasRod=be.hasRod;", f"booleancherenkov=be.fluxQuantity>{thr[1]};", "intcolor=be.rodColor;", "if(!hasRod&&!cherenkov)return;", "inttop=columnTop(be);",
                                         "bindTexture(ResourceManager.RBMK_ELEMENT_FUEL_TEX);", "RenderContext.setColor(((color&0xFF0000)>>16)/255F,((color&0x00FF00)>>8)/255F,(color&0x0000FF)/255F,1F);",
                                         "for(intj=0;j<top;j++){ResourceManager.rbmk_element_rods.renderPart(\"Rods\");RenderContext.translate(0F,1F,0F);}") == []
       and "BossSpawn" not in rc,
       "RenderRBMKRod draws the rods of RenderRBMKFuelChannel.java:53-65 (rbmk_element_fuel texture for both variants, colour from the rod colour as ColorUtil.fr/fg/fb, one rods part per segment up to the extra block) when the column has a rod; "
       "the lid texture base is rbmk_element / rbmk_element_mod", (tex and tex[1], thr and thr[1]))
    ck("V5.render-cherenkov", ok and has_all(rc, "VertexConsumerglow=buffer.getBuffer(NtmRenderTypes.GLOW);", f"for(doublej=0;j<=top-1;j+={step[1]})", f"floaty=(float)({start[1]}+j);") == []
       and all(rc.count(f"glow.addVertex(matrix,{a}F,y,{b}F).setColor({col[1]}F,{col[2]}F,{col[3]}F,{col[4]}F);") == 1 for a, b in verts)
       and [rc.index(f"glow.addVertex(matrix,{a}F,y,{b}F)") for a, b in verts] == sorted(rc.index(f"glow.addVertex(matrix,{a}F,y,{b}F)") for a, b in verts),
       "the Cherenkov glow (flux above 5) is a flat quad every 0.25 from y 0.75 up to top - 1 with the original's four corners in order and colour (0.4, 0.9, 1.0, 0.1) through NtmRenderTypes.GLOW (additive, untextured, unculled)", (start and start[1], step and step[1], col and col.groups(), verts))
    ck("V5.render-client-only", RENDER.startswith(J + "render/blockentity/") and "net.minecraft.client" in rend and "ResourceManager.RBMK_ELEMENT_FUEL_TEX" in rend, "RenderRBMKRod is a client render class (render.blockentity)")
    # ---- baked model: the level body and the item form
    glt = re.search(r"GL11\.glTranslated\(0, (-[\d.]+), 0\);", orod)
    glsc = re.search(r"GL11\.glScalef\(([\d.]+)F, ([\d.]+)F, ([\d.]+)F\);", orod)
    segs = re.search(r"for\(int i = 0; i < (\d+); i\+\+\)", orod)
    tint = re.search(r"setColorOpaque_I\((0x[0-9A-Fa-f]+)\)", orod)
    parts = re.findall(r'renderPartWithIcon\(\(HFRWavefrontObject\) ResourceManager\.(rbmk_element(?:_rods)?), "(\w+)"', orod)
    ok = all([glt, glsc, segs, tint]) and glsc[1] == glsc[2] == glsc[3]
    ck("V5.baked-item", ok and sorted(set(parts)) == [("rbmk_element", "Cap"), ("rbmk_element", "Inner"), ("rbmk_element_rods", "Rods")]
       and has_all(bc, f"newMatrix4f().translate(0.5F,0.5F-{glt[1][1:]}F,0.5F).scale({glsc[1]}F).translate(0.0F,i,0.0F);", f"for(inti=0;i<{segs[1]};i++){{", f"ITEM_ROD_COLOR={tint[1]};", 'bakeSimpleQuads(List.of("Inner"),segment,inner)',
                   'bakeSimpleQuads(List.of("Cap"),segment,top)', 'bakeSimpleQuads(List.of("Rods"),matrix,sprite)', "for(Directiondir:Direction.Plane.HORIZONTAL)item.add(sideQuad(dir,segment,side));", "tint(quad,ITEM_ROD_COLOR);") == [],
       "the item form is four segments at y -0.675 scaled 0.35 (RenderRBMKRod.java:36-39), each with Inner, Cap, the four side faces and the Rods part tinted 0x304825 (:49-50), baked into RBMKElementBakedModel's non-level quads (no BEWLR)",
       (glt and glt[1], glsc and glsc.groups(), segs and segs[1], tint and tint[1], parts))
    ck("V5.baked-level", has_all(bc, "newMatrix4f().translate(0.5F,0.0F,0.5F);", 'bakeSimpleQuads(List.of("Cap"),level,top)', 'bakeSimpleQuads(List.of("Inner"),level,inner)', "for(Directiondir:Direction.Plane.HORIZONTAL)this.levelSides.put(dir,List.of(sideQuad(dir,level,side)));",
                                 "if(data.has(IN_LEVEL)){if(direction==null)returnlevelQuads;returnlevelSides.getOrDefault(direction,Collections.emptyList());}returndirection==null?itemQuads:Collections.emptyList();",
                                 "ChunkRenderTypeSet.of(RenderType.cutout())", "returnside;") == [],
       "in the level every block of the column draws Cap and Inner plus the four vertical faces of the full cube under their cull direction with the side texture (RenderRBMKRod.java:59-82), cutout render type, particle = side")
    ck("V5.baked-parts", all(("rbmk_element", p) in set(parts) for p in ("Cap", "Inner")) and "Rods" in bm and "net.minecraft.client" in bm, "the baked model uses the OBJ parts Cap, Inner and Rods that the original names (ResourceManager.rbmk_element, rbmk_element_rods)")


REG_COMMON = [FLUX, LOAD, BASEBE, SLOT, RODBE, RODBLK, CORIUM, MENU, NB, BET, MT, CT, EH] + NEUTRON + [PKG]
CLIENT_NAMES = ("RBMKRodScreen", "RenderRBMKRod", "RBMKElementBakedModel")


def v5_registrations(ck, inp, st):
    nbe = code_of(lf(st.text(BET)))
    ck("V5.reg-block-entity", once(nbe, 'publicstaticfinalSupplier<BlockEntityType<RBMKRodBlockEntity>>RBMK_ROD=BLOCK_ENTITY_TYPES.register("rbmk_rod",()->BlockEntityType.Builder.of(RBMKRodBlockEntity::new,NtmBlocks.RBMK_ROD.get(),NtmBlocks.RBMK_ROD_MOD.get()).build(null));') == []
       and nbe.count("RBMKRodBlockEntity::new") == 1 and nbe.count('register("rbmk_rod"') == 1, "NtmBlockEntityTypes registers one rbmk_rod type, valid for both rod blocks (the original has one TileEntityRBMKRod for both, TileMappings tileentity_rbmk_rod), once")
    mt = code_of(lf(st.text(MT)))
    ck("V5.reg-menu", once(mt, 'publicstaticfinalDeferredHolder<MenuType<?>,MenuType<RBMKRodMenu>>RBMK_ROD=reg("rbmk_rod",RBMKRodMenu::new);') == [] and mt.count('reg("rbmk_rod"') == 1 and mt.count("RBMKRodMenu::new") == 1,
       "NtmMenuTypes registers the rbmk_rod menu once")
    client = lf(st.text(NMC))
    cc = code_of(client)
    scr_body = body(client, "public static void registerScreens(RegisterMenuScreensEvent event)")
    ck("V5.reg-screen", scr_body.count("event.register(NtmMenuTypes.RBMK_ROD.get(),RBMKRodScreen::new);") == 1 and cc.count("RBMKRodScreen::new") == 1 and "dist=Dist.CLIENT" in cc,
       "the screen is registered once, inside NuclearTechModClient.registerScreens (the client-dist entry)", scr_body[-200:])
    proxy = lf(st.text(CP))
    ber = body(proxy, "public void registerBlockEntityRenderers()")
    ck("V5.reg-renderer", ber.count("BlockEntityRenderers.register(NtmBlockEntityTypes.RBMK_ROD.get(),newRenderRBMKRod());") == 1 and code_of(proxy).count("newRenderRBMKRod()") == 1,
       "ClientProxy.registerBlockEntityRenderers registers RenderRBMKRod for the rbmk_rod type once, next to the lid renderers")
    rm = code_of(lf(st.text(RM)))
    fuel = inp.o["rfc"]
    ck("V5.reg-resource-manager", once(rm, 'publicstaticfinalResourceLocationRBMK_ELEMENT_FUEL_TEX=NuclearTechMod.withDefaultNamespace("textures/block/rbmk/rbmk_element_fuel.png");', "publicstaticIModelCustomrbmk_element_rods;",
                                       'rbmk_element_rods=newHFRWavefrontObject("models/obj/rbmk/rbmk_element_rods.obj").asVBO();') == []
       and "rbmk_element_fuel.png" in fuel and "rbmk_element_rods_vbo.renderPart(\"Rods\")" in fuel and st.has(RES + "textures/block/rbmk/rbmk_element_fuel.png") and st.has(RES + "models/obj/rbmk/rbmk_element_rods.obj"),
       "ResourceManager holds the rod texture (original texture_rods rbmk_element_fuel) and the rods VBO model once; both files exist (V9 checks their bytes)")
    geo = lf(st.text(GEO))
    gc = code_of(geo)
    ck("V5.reg-geometry", once(gc, "RBMK_DEBRIS,RBMK_ELEMENT}", 'caseRBMK_ELEMENT->newRBMKElementBakedModel(newHFRWavefrontObject("models/obj/rbmk/rbmk_element.obj"),newHFRWavefrontObject("models/obj/rbmk/rbmk_element_rods.obj"),',
                                'spriteGetter.apply(context.getMaterial("side")),spriteGetter.apply(context.getMaterial("top")),spriteGetter.apply(context.getMaterial("inner")),spriteGetter.apply(context.getMaterial("fuel")),context.getTransforms());') == []
       and "caseRBMK_DEBRIS->" in gc, "NtmGeometry has the RBMK_ELEMENT type (the type string rbmk_element of the generated models) and bakes it from the two OBJ files with the side, top, inner and fuel materials and the parent's display transforms, once; RBMK_DEBRIS is kept")
    tab = [l.strip() for l in lf(st.text(CT)).split("\n")]
    i = tab.index("output.accept(NtmBlocks.REACTOR_ZIRNOX);")
    seq = [l for l in tab[i + 1:] if l and not l.startswith("//")][:3]
    ct = "\n".join(tab)
    ck("V5.creative-tab", seq == ["output.accept(NtmBlocks.RBMK_ROD);", "output.accept(NtmBlocks.RBMK_ROD_MOD);", "output.accept(NtmBlocks.RBMK_BLANK);"] and ct.count("NtmBlocks.RBMK_ROD)") == 1 and ct.count("NtmBlocks.RBMK_ROD_MOD)") == 1 and "CORIUM" not in ct,
       "the MACHINE tab lists RBMK_ROD and RBMK_ROD_MOD once each between REACTOR_ZIRNOX and RBMK_BLANK (original registration order ModBlocks.java:3107-3108 before the blank); corium_block has no tab entry (GenericFiniteFluid.java:29 setCreativeTab(null))", seq)


PINS = {  # edited production file -> (the start lines that may leave the file, the number of inserted lines that are not comments)
    FLUX: (["* Original com.hbm.tileentity.machine.rbmk.IRBMKFluxReceiver. Only the neutron types the fuel rods name are ported here (Goal24B);", "* receiveFlux(NeutronStream) arrives with the neutron handler and the fuel column (Goal24C)."], 2),
    EH: ([], 5), NB: ([], 3), BET: ([], 1), MT: ([], 1), CT: ([], 2), NMC: ([], 2), CP: ([], 1), RM: ([], 3),
    RLID: (["String column = BuiltInRegistries.BLOCK.getKey(be.getBlockState().getBlock()).getPath();", "private static int columnTop(RBMKBaseBlockEntity be) {"], 5),
    GEO: (["RBMK_DEBRIS"], 5), BSP: ([], 14), LOOT: ([], 3), TAGP: ([], 3), LP: ([], 12), RP: ([], 8),
}


def v5_scope(ck, inp, st):
    bad = {}
    for path, (want_del, want_ins) in PINS.items():
        live = lf(st.text(path))
        dele, ins = diff_summary(inp.start[path], live)
        code_ins = [x for x in ins if not x.startswith(("//", "*", "/*"))]
        if dele != want_del or len(code_ins) != want_ins:
            bad[path.rsplit("/", 1)[1]] = (dele[:3], len(code_ins), want_ins)
    ck("V5.edited-files", not bad and set(PINS) | {BASEBE} == set(EDITED), "each edited production file differs from its start copy only by the batch's insertions: exactly the expected start lines left the file (FLUX class comment, RenderRBMKLid column lines, NtmGeometry `RBMK_DEBRIS` -> `RBMK_DEBRIS,`) "
       "and the number of inserted code lines is the expected one (RBMKBaseBlockEntity is pinned in V4)", bad)
    leaks = {}
    for path in REG_COMMON:
        text = lf(st.text(path))
        start = inp.start.get(path, "")
        imports = lambda t: sorted(set(re.findall(r"^import (?:static )?(?:net\.minecraft\.client|com\.hbm\.render)[\w.*]*;", t, re.M)))  # noqa: E731
        extra = [x for x in imports(text) if x not in imports(start)]
        named = [n for n in CLIENT_NAMES if n in blank_comments(text) and n not in blank_comments(start)]
        if extra or named:
            leaks[path.rsplit("/", 1)[1]] = extra + named
    ck("V5.client-isolation", not leaks, "no common class (neutron package, fuel channel block entity/block/menu, corium block, interfaces, registries, creative tab, event handler) imports a net.minecraft.client or com.hbm.render class or names the screen, renderer or baked model", leaks)
    nmc = code_of(lf(st.text(NMC)))
    ck("V5.client-entry", "dist=Dist.CLIENT" in nmc and RENDER.startswith(J + "render/") and BAKED.startswith(J + "render/") and SCREEN.startswith(J + "inventory/screens/"),
       "the screen is wired only from the @Mod(dist = Dist.CLIENT) entry and the renderer and baked model are in render packages")


# ---------------------------------------------------------------- V6 recipes

def gen_ok(text, data):
    """The datagen writer's layout: 2-space JSON, LF, no trailing newline."""
    return "\r" not in text and text == json.dumps(data, indent=2, ensure_ascii=False)


def stamp_hash(path, data):
    """The hash migration-resources.gradle records: text files with CRLF/CR folded to LF, everything else raw."""
    name = path.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in {"cfg", "csv", "fsh", "gradle", "java", "json", "lang", "mcmeta", "md", "mtl", "obj", "properties", "toml", "txt", "vsh", "xml", "yaml", "yml"}:
        try:
            data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return sha(data)


def recipe_view(inp):
    """The expected rbmk_rod recipe and advancement, read from CraftingManager.java:991."""
    row = inp.ol["cm"][990]
    m = re.search(r"new ItemStack\(ModBlocks\.rbmk_rod, (\d+)\), new Object\[\] \{ \"(\w)\", \"(\w)\", \"(\w)\", '(\w)', STEEL\.shell\(\), '(\w)', ModBlocks\.rbmk_blank \}", row)
    if not m:
        raise ValueError("CraftingManager.java:991 is not the rbmk_rod row")
    count, pattern, shell_key, blank_key = int(m[1]), [m[2], m[3], m[4]], m[5], m[6]
    recipe = {"type": "minecraft:crafting_shaped", "category": "misc", "key": {shell_key: {"item": "hbmsntm:shell_steel"}, blank_key: {"item": "hbmsntm:rbmk_blank"}}, "pattern": pattern,
              "result": {"count": count, "id": "hbmsntm:rbmk_rod"}}
    advancement = {"parent": "minecraft:recipes/root",
                   "criteria": {"has_rbmk_blank": {"conditions": {"items": [{"items": "hbmsntm:rbmk_blank"}]}, "trigger": "minecraft:inventory_changed"},
                                "has_the_recipe": {"conditions": {"recipe": "hbmsntm:rbmk_rod"}, "trigger": "minecraft:recipe_unlocked"}},
                   "requirements": [["has_the_recipe", "has_rbmk_blank"]], "rewards": {"recipes": ["hbmsntm:rbmk_rod"]}}
    return recipe, advancement, count, pattern, shell_key, blank_key


def v6_recipes(ck, inp, st):
    need_ov(inp)
    recipe, advancement, count, pattern, shell_key, blank_key = recipe_view(inp)
    rpath, apath = RECIPES + "rbmk_rod.json", ADV + "misc/rbmk_rod.json"
    rtext = st.text(rpath) if st.has(rpath) else ""
    atext = st.text(apath) if st.has(apath) else ""
    ok = st.has(rpath) and json.loads(rtext) == recipe and gen_ok(rtext, json.loads(rtext))
    ck("V6.recipe", ok, "data/hbmsntm/recipe/rbmk_rod.json is a shaped recipe C/R/C of two shell_steel (STEEL.shell()) and an rbmk_blank for one rbmk_rod block (CraftingManager.java:991, the !enable528 branch), in the datagen layout",
       rtext[:400])
    ok = st.has(apath) and json.loads(atext) == advancement and gen_ok(atext, json.loads(atext))
    ck("V6.advancement", ok, "the recipe advancement unlocks hbmsntm:rbmk_rod on holding rbmk_blank (has_rbmk_blank) or the recipe", atext[:400])
    recipe_files = sorted(p for p in st.tree if p.startswith(RECIPES) or p.startswith(ADV))
    new_files = sorted(p for p in recipe_files if p not in inp.base_files)
    changed = sorted(p for p in recipe_files if p in inp.base_files and st.tree[p] != inp.base_files[p])
    ck("V6.no-other-recipe", new_files == sorted([rpath, apath]) and not changed, "the only generated recipe or advancement that is new is rbmk_rod and none of the existing ones changed", (new_files, changed[:5]))
    rp = lf(st.text(RP))
    rpc = code_of(rp)
    ck("V6.no-rod-mod", not [p for p in st.tree if ("rbmk_rod_mod" in p) and (p.startswith(RECIPES) or p.startswith(ADV))] and "RBMK_ROD_MOD" not in rpc and "GRAPHITE.block()" in inp.ol["cm"][991]
       and "rbmk_rod_mod" in rp and "needs GRAPHITE.block()" in rp,
       "no rbmk_rod_mod recipe exists or is registered (CraftingManager.java:992 needs GRAPHITE.block(); NEO has no graphite block, as rbmk_moderator) and the provider comment says so")
    ck("V6.anvil-unchanged", st.has(ANVIL) and lf(st.text(ANVIL)) == lf(inp.start[ANVIL]) and hashed_equal(inp, st, ANVIL),
       "AnvilRecipes.java is unchanged against the start copy: the two tier-4 recycling rows (AnvilRecipes.java:927-953) are not ported (the 4-tier anvil is unreachable in NEO)")
    dele, ins = diff_summary(inp.start[RP], rp)
    code_ins = [x for x in ins if not x.startswith(("//", "*", "/*"))]
    want = ["ShapedRecipeBuilder.shaped(RecipeCategory.MISC, NtmBlocks.RBMK_ROD.get(), " + str(count) + ")", ] + [f'.pattern("{c}")' for c in pattern] + [
        f".define('{shell_key}', NtmItems.SHELL_STEEL.get())", f".define('{blank_key}', NtmBlocks.RBMK_BLANK.get())", '.unlockedBy("has_rbmk_blank", has(NtmBlocks.RBMK_BLANK.get()))',
        '.save(recipeOutput, ResourceLocation.fromNamespaceAndPath("hbmsntm", "rbmk_rod"));']
    ck("V6.provider", not dele and code_ins == want, "NtmRecipeProvider differs from its start copy only by the rbmk_rod builder (pattern, ingredients and count from the original row, unlockedBy has_rbmk_blank, id hbmsntm:rbmk_rod)", (dele[:3], code_ins))


# ---------------------------------------------------------------- V7 datagen outputs

BSP_PIN = [
    'this.rbmkElement(NtmBlocks.RBMK_ROD, "rbmk_element");', 'this.rbmkElement(NtmBlocks.RBMK_ROD_MOD, "rbmk_element_mod");',
    'this.simpleBlockWithItem(NtmBlocks.CORIUM_BLOCK.get(), this.models().cubeBottomTop(name(NtmBlocks.CORIUM_BLOCK), modLoc("block/corium_flowing"), modLoc("block/corium_still"), modLoc("block/corium_still")));',
    "}", "private void rbmkElement(DeferredBlock<? extends Block> block, String texture) {", 'String base = "block/rbmk/" + texture;',
    'this.simpleBlockWithItem(block.get(), this.models().withExistingParent(name(block), mcLoc("block/block")).customLoader(RBMKElementLoaderBuilder::new)',
    '.texture("side", modLoc(base + "_side")).texture("top", modLoc(base + "_top")).texture("inner", modLoc(base + "_inner")).texture("fuel", modLoc(base + "_fuel")).end());',
    "protected static class RBMKElementLoaderBuilder extends BlockModelBuilderBase {", "public RBMKElementLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {", "super(parent, helper);", "}",
    "@Override public BakedModelType getType() { return BakedModelType.RBMK_ELEMENT; }", "}"]


def v7_datagen(ck, inp, st):
    need_ov(inp)
    mb, base = inp.o["mb"], {}
    for name in ("rbmk_rod", "rbmk_rod_mod"):
        m = re.search(name + r' = new RBMKRod\((?:true|false)\)\.setBlockName\("' + name + r'"\)\.setCreativeTab\(MainRegistry\.machineTab\)\.setBlockTextureName\(RefStrings\.MODID \+ ":rbmk/(\w+)"\)', mb)
        base[name] = m[1] if m else None
    still = re.search(r'super\(fluid, material, "(\w+)", "(\w+)"\)', inp.o["corium"])
    icon = re.search(r"return \(side == 0 \|\| side == 1\) \? stillIcon : flowingIcon;", inp.o["gff"])
    ck("V7.original-names", base == {"rbmk_rod": "rbmk_element", "rbmk_rod_mod": "rbmk_element_mod"} and still and still.groups() == ("corium_still", "corium_flowing") and icon is not None,
       "the original block textures are rbmk/rbmk_element and rbmk/rbmk_element_mod (ModBlocks.java:2113-2114) and corium shows corium_still on sides 0/1 and corium_flowing around (CoriumFinite ctor, GenericFiniteFluid.getIcon :37-39)", (base, still and still.groups()))
    names = ("rbmk_rod", "rbmk_rod_mod", "corium_block")
    gen_paths = [G_STATE + n + ".json" for n in names] + [G_BMODEL + n + ".json" for n in names] + [G_IMODEL + n + ".json" for n in names] + [G_LOOT + n + ".json" for n in names]
    texts = {p: st.text(p) if st.has(p) else None for p in gen_paths}
    bad = []
    for n in names:
        want = {"variants": {"": {"model": "hbmsntm:block/" + n}}}
        t = texts[G_STATE + n + ".json"]
        if t is None or json.loads(t) != want or not gen_ok(t, json.loads(t)):
            bad.append(n)
    ck("V7.blockstates", not bad, "the three blockstates have the single variant `` -> hbmsntm:block/<name> (the rod and corium models are not rotated)", bad)
    bad = []
    for n in ("rbmk_rod", "rbmk_rod_mod"):
        b = base[n]
        want = {"type": "rbmk_element", "parent": "minecraft:block/block", "loader": "hbmsntm:ntm_geometry_loader",
                "textures": {k: f"hbmsntm:block/rbmk/{b}_{k}" for k in ("fuel", "inner", "side", "top")}}
        t = texts[G_BMODEL + n + ".json"]
        if t is None or json.loads(t) != want or not gen_ok(t, json.loads(t)):
            bad.append(n)
    cm_t = texts[G_BMODEL + "corium_block.json"]
    want = {"parent": "minecraft:block/cube_bottom_top", "textures": {"bottom": "hbmsntm:block/" + still[1], "side": "hbmsntm:block/" + still[2], "top": "hbmsntm:block/" + still[1]}} if still else None
    if cm_t is None or want is None or json.loads(cm_t) != want or not gen_ok(cm_t, json.loads(cm_t)):
        bad.append("corium_block")
    ck("V7.block-models", not bad, "rbmk_rod / rbmk_rod_mod are ntm_geometry_loader models of type rbmk_element (the enum name RBMK_ELEMENT, parent minecraft:block/block for the display transforms) with side, top, inner and fuel of rbmk_element[_mod]_*; "
       "corium_block is cube_bottom_top with corium_still on top and bottom and corium_flowing around", bad)
    refs = set()
    for p in gen_paths:
        if p.startswith(G_BMODEL) and texts[p]:
            refs |= {v for v in json.loads(texts[p]).get("textures", {}).values()}
    missing = [r for r in sorted(refs) if not st.has(TEX + r.split("block/", 1)[1] + ".png")]
    ck("V7.textures-exist", bool(refs) and not missing and st.has(TEX + "corium_still.png.mcmeta") and st.has(TEX + "corium_flowing.png.mcmeta"), "every texture the three block models name exists, and the two corium textures carry their animation metadata", missing)
    bad = []
    for n in names:
        t = texts[G_IMODEL + n + ".json"]
        if t is None or json.loads(t) != {"parent": "hbmsntm:block/" + n} or not gen_ok(t, json.loads(t)):
            bad.append(n)
    ck("V7.item-models", not bad, "each item model has the parent hbmsntm:block/<name> (for the rods this is the baked item form of RBMKElementBakedModel, there is no BEWLR)", bad)
    blank = lf(st.text(G_LOOT + "rbmk_blank.json")) if st.has(G_LOOT + "rbmk_blank.json") else ""
    bad = []
    for n in ("rbmk_rod", "rbmk_rod_mod"):
        t = texts[G_LOOT + n + ".json"]
        if t is None or not blank or t != blank.replace("rbmk_blank", n) or json.loads(t)["pools"][0]["entries"][0]["name"] != "hbmsntm:" + n:
            bad.append(n)
    t = texts[G_LOOT + "corium_block.json"]
    if t is None or json.loads(t) != {"type": "minecraft:block", "random_sequence": "hbmsntm:blocks/corium_block"} or not gen_ok(t, json.loads(t)):
        bad.append("corium_block")
    ck("V7.loot", not bad, "the rods drop themselves exactly as rbmk_blank does (survives_explosion, one roll); corium_block has an empty loot table (the original fluid block drops nothing)", bad)
    # ---- the pickaxe tag: the three entries next to their neighbours, everything else the start text
    pick = lf(st.text(PICK))
    entries = ['"hbmsntm:rbmk_rod",', '"hbmsntm:rbmk_rod_mod",', '"hbmsntm:corium_block",']
    lines = pick.split("\n")
    stripped = [l.strip() for l in lines]
    order_ok = all(stripped.count(e) == 1 for e in entries)
    if order_ok:
        i, j, k = stripped.index(entries[0]), stripped.index(entries[1]), stripped.index(entries[2])
        order_ok = j == i + 1 and stripped[j + 1] == '"hbmsntm:rbmk_blank",' and stripped[k - 1] == '"hbmsntm:pribris_radiating",' and stripped[i - 1] == '"hbmsntm:zirnox_destroyed",'
    without = "\n".join(l for l in lines if l.strip() not in entries)
    ck("V7.pickaxe", order_ok and sha(without.encode("utf-8")) == inp.base_files.get(PICK) and gen_ok(pick, json.loads(pick)),
       "the pickaxe tag gained exactly rbmk_rod, rbmk_rod_mod (before rbmk_blank) and corium_block (after pribris_radiating): removing the three lines gives the start file byte for byte", (order_ok, sha(without.encode("utf-8"))[:12], str(inp.base_files.get(PICK))[:12]))
    # ---- generated files are the provider's output: the new set, the layout, the migration stamp
    gen_new = sorted(p for p in st.tree if p.startswith(GEN) and p not in inp.base_files)
    gen_changed = sorted(p for p in st.tree if p.startswith(GEN) and p in inp.base_files and st.tree[p] != inp.base_files[p])
    expect_new = sorted(gen_paths + [RECIPES + "rbmk_rod.json", ADV + "misc/rbmk_rod.json"])
    ck("V7.generated-set", gen_new == expect_new and gen_changed == sorted([EN, PICK, STAMP]) and len(expect_new) == 14,
       "src/generated/resources gained exactly the 14 files of the three blocks and the rbmk_rod recipe (3 blockstates, 3 block models, 3 item models, 3 loot tables, recipe, advancement) and changed only en_us.json, the pickaxe tag and the stamp", (sorted(set(gen_new) ^ set(expect_new))[:6], gen_changed))
    stamp = json.loads(st.text(STAMP))
    bad = []
    for p in expect_new + [EN, PICK]:
        rel = p[len(GEN):]
        data = st.files.get(p)
        if data is None or stamp["generated"].get(rel) != stamp_hash(p, data):
            bad.append(rel)
    ck("V7.stamp-generated", not bad, "the migration stamp records the hash of each of these 16 generated files as they are on disk: the files are what the last runData wrote, not hand edits", bad[:6])
    stale = []
    for p in sorted(set(NEW_CLASSES + EDITED + [ZH] + [RES + n for _, n in IMPORTS])):
        data = st.files.get(p)
        if data is None or stamp["inputs"].get(p) != stamp_hash(p, data):
            stale.append(p.rsplit("/", 1)[-1])
    ck("V7.stamp-inputs", not stale, "the stamp's input hashes of the 15 new classes, the 17 edited files, zh_cn.json and the 23 imported resources equal the files on disk: runData ran after the last edit of any datagen input", stale[:8])
    bsp = lf(st.text(BSP))
    dele, ins = diff_summary(inp.start[BSP], bsp)
    code_ins = [x for x in ins if not x.startswith(("//", "*", "/*"))]
    ck("V7.provider-state", not dele and code_ins == BSP_PIN, "NtmBlockStateProvider differs from its start copy only by the two rbmkElement rows, the corium cube_bottom_top row (flowing sides, still top and bottom), the rbmkElement helper and the RBMKElementLoaderBuilder (type RBMK_ELEMENT)", (dele[:3], code_ins))
    loot = lf(st.text(LOOT))
    dele, ins = diff_summary(inp.start[LOOT], loot)
    code_ins = [x for x in ins if not x.startswith(("//", "*", "/*"))]
    ck("V7.provider-loot", not dele and code_ins == ["this.dropSelf(NtmBlocks.RBMK_ROD.get());", "this.dropSelf(NtmBlocks.RBMK_ROD_MOD.get());", "this.add(NtmBlocks.CORIUM_BLOCK.get(), noDrop());"],
       "NtmBlockLootTableProvider adds dropSelf for the rods and noDrop() for corium, nothing else", (dele[:3], code_ins))
    tag = lf(st.text(TAGP))
    dele, ins = diff_summary(inp.start[TAGP], tag)
    code_ins = [x for x in ins if not x.startswith(("//", "*", "/*"))]
    ck("V7.provider-tag", not dele and code_ins == ["NtmBlocks.RBMK_ROD.get(),", "NtmBlocks.RBMK_ROD_MOD.get(),", "NtmBlocks.CORIUM_BLOCK.get(),"], "NtmBlockTagProvider adds the three blocks to the pickaxe-mineable list, nothing else", (dele[:3], code_ins))


# ---------------------------------------------------------------- V8 language

def expected_lang(inp):
    """(NEO key, kind, original key, original English, original Chinese, NEO English, NEO Chinese) for the 12 new keys."""
    rows = []
    for neo, orig in UPSTREAM_KEYS:
        en, zh = UPSTREAM_EXPECT[neo]
        rows.append((neo, "upstream", orig, inp.o_en[orig][0][0], inp.o_zh[orig][0][0], en, zh))
    for neo, (en, zh) in LOCAL_EXPECT.items():
        rows.append((neo, "local", None, None, None, en, zh))
    return rows


def v8_lang(ck, inp, st):
    need_ov(inp)
    exp = expected_lang(inp)
    keys = [e[0] for e in exp]
    ck("V8.expected-12", len(exp) == 12 and len(set(keys)) == 12 and sum(1 for e in exp if e[1] == "upstream") == 10 and sum(1 for e in exp if e[1] == "local") == 2
       and all(e[3] == e[5] and e[4] == e[6] for e in exp if e[1] == "upstream"),
       "12 keys are expected: 10 upstream (the original English and Chinese lines are the NEO text) and 2 local (the hover warnings of GUIRBMKRod.java:33/:35)", [e[0] for e in exp if e[1] == "upstream" and (e[3] != e[5] or e[4] != e[6])])
    lp = lf(st.text(LP))
    want_lines = {}
    for nk, kind, sk, sen, szh, ten, tzh in exp:
        block = {"block.hbmsntm.rbmk_rod": "RBMK_ROD", "block.hbmsntm.rbmk_rod_mod": "RBMK_ROD_MOD", "block.hbmsntm.corium_block": "CORIUM_BLOCK"}.get(nk)
        want_lines[nk] = f'this.add(NtmBlocks.{block}, "{ten}");' if block else f'this.add("{nk}", "{ten}");'
    lpl = [l.strip() for l in lp.split("\n")]
    ck("V8.provider", all(lpl.count(l) == 1 for l in want_lines.values()), "NtmLanguageProvider adds the 12 keys once each with the English text (blocks through their registry holders)", [l for l in want_lines.values() if lpl.count(l) != 1][:4])
    ldel, lins = diff_summary(inp.start[LP], lp)
    code_ins = sorted(x for x in lins if x.startswith("this.add("))
    ck("V8.provider-insert-only", not ldel and code_ins == sorted(want_lines.values()) and len([x for x in lins if not x.startswith(("//", "*", "/*"))]) == 12, "the provider differs from its start copy only by these 12 added lines (plus comments)", (ldel[:3], len(code_ins)))
    en, en_dups = json_pairs(st.text(EN))
    en0, _ = json_pairs(inp.start[EN])
    zh_text = st.text(ZH)
    zh, zh_dups = json_pairs(zh_text)
    zh0, _ = json_pairs(inp.start[ZH])
    ck("V8.en-values", not en_dups and all(en.get(e[0]) == e[5] for e in exp), "generated en_us.json has the 12 keys with the provider's English and no duplicate key", [(e[0], en.get(e[0]), e[5]) for e in exp if en.get(e[0]) != e[5]][:3])
    changed_en = sorted(k for k in set(en) | set(en0) if en.get(k) != en0.get(k))
    ck("V8.en-only-these", changed_en == sorted(keys) and len(en) == len(en0) + 12 == 2614 and len(en0) == START_EN_KEYS, "en_us.json changed only in the 12 new keys and holds 2,614 keys (2,602 at the start)", (changed_en[:5], len(en), len(en0)))
    ck("V8.zh-values", not zh_dups and all(zh.get(e[0]) == e[6] for e in exp), "zh_cn.json has the 12 keys: upstream values verbatim from zh_CN.lang, the two local warnings as the handoff gives them", [(e[0], zh.get(e[0]), e[6]) for e in exp if zh.get(e[0]) != e[6]][:3])
    changed_zh = sorted(k for k in set(zh) | set(zh0) if zh.get(k) != zh0.get(k))
    ck("V8.zh-only-these", changed_zh == sorted(keys) and len(zh) == len(zh0) + 12 == 2507 and len(zh0) == START_ZH_KEYS, "zh_cn.json changed in nothing but the 12 new keys and holds 2,507 keys (2,495 at the start)", (changed_zh[:5], len(zh), len(zh0)))
    ordered = list(zh.keys())
    ck("V8.zh-sorted", ordered == sorted(ordered), "zh_cn.json keeps its sorted key order")
    ph = lambda s: (sorted(re.findall(r"%(?:\d+\$)?[sd]", s)), s.count("$"))  # noqa: E731
    ck("V8.placeholders", all(ph(en.get(e[0], "")) == ph(zh.get(e[0], "")) for e in exp), "every new key keeps the same placeholders and `$` line breaks in English and Chinese", [e[0] for e in exp if ph(en.get(e[0], "")) != ph(zh.get(e[0], ""))][:4])
    ck("V8.upstream-verbatim", all(e[1] != "upstream" or (zh.get(e[0]) == inp.o_zh[e[2]][0][0] and en.get(e[0]) == inp.o_en[e[2]][0][0]) for e in exp), "the 10 upstream values equal en_US.lang / zh_CN.lang byte for byte")
    ck("V8.crlf", zh_text.count("\r\n") == zh_text.count("\n") > 0 and inp.start[ZH].count("\r\n") == inp.start[ZH].count("\n") and zh_text.count("\r\n") - inp.start[ZH].count("\r\n") == 12
       and "\r\n" not in st.text(EN) and format_ok(zh_text, zh) and st.text(MAP).count("\r\n") == st.text(MAP).count("\n") > 0 and format_ok(st.text(MAP), json.loads(st.text(MAP)))
       and st.text(MAP).count("\r\n") - inp.start[MAP].count("\r\n") == sum(8 if e[1] == "upstream" else 6 for e in exp),
       "zh_cn.json grew by exactly 12 CRLF lines with no lone LF, zh_cn-map.json keeps CRLF and the standard layout (8 lines per upstream and 6 per local entry added), en_us.json stays LF",
       (zh_text.count("\r\n"), zh_text.count("\n"), inp.start[ZH].count("\r\n"), st.text(MAP).count("\r\n"), st.text(MAP).count("\n")))
    mp = json.loads(st.text(MAP))
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
    ck("V8.map-entries", not bad, "the mapping has one entry per key: upstream entries carry source_key / source_en / source_zh from the original and the NEO text; local entries carry a reason", dict(list(bad.items())[:3]))
    changed_map = sorted(k for k in set(entries) | set(entries0) if entries.get(k) != entries0.get(k))
    kinds, kinds0 = collections.Counter(e["kind"] for e in entries.values()), collections.Counter(e["kind"] for e in entries0.values())
    ck("V8.map-only-these", changed_map == sorted(keys) and mp["source_commit"] == mp0["source_commit"] and mp["schema_version"] == mp0["schema_version"] and len(entries) == len(entries0) + 12 == 2614 and len(entries0) == START_MAP_KEYS
       and kinds["upstream"] - kinds0["upstream"] == 10 and kinds["local"] - kinds0["local"] == 2 and kinds["deferred"] == kinds0["deferred"] and (kinds["upstream"], kinds["local"], kinds["deferred"]) == (1823, 684, 107),
       "the mapping changed only in the 12 new entries and holds 2,614 entries: upstream 1,823, local 684, deferred 107; source_commit and schema_version unchanged", (changed_map[:5], dict(kinds)))
    ordered = list(entries.keys())
    ck("V8.map-sorted", ordered == sorted(ordered) and list(entries0.keys()) == sorted(entries0.keys()), "the mapping keeps its sorted key order")
    ck("V8.map-matches-files", all(entries[k].get("target_en") == en.get(k) and entries[k].get("target_zh") == zh.get(k) for k in keys if k in entries), "for the 12 keys the mapping's target English / Chinese equal the generated en_us.json and zh_cn.json values")
    ck("V8.start-copies-consistent", len(en0) == START_EN_KEYS and len(zh0) == START_ZH_KEYS and len(entries0) == START_MAP_KEYS and not [k for k in keys if k in en0 or k in zh0 or k in entries0],
       "none of the 12 keys existed in the start copies of en_us.json, zh_cn.json and the mapping (2,602 / 2,495 / 2,602 keys)")


# ---------------------------------------------------------------- V9 resources

def v9_resources(ck, inp, st):
    need_ov(inp)
    own = json.loads(st.text(OWN))
    assets = own["assets"]
    targets = [RES + n for _, n in IMPORTS]
    ck("V9.record", len(assets) == 23 and own.get("batch") == "Goal24C" and own.get("source_commit") == ORIGINAL_HEAD and own.get("kind") == "import" and sorted(a["target_path"] for a in assets) == sorted(targets)
       and str(own.get("note", "")).strip() != "" and format_ok(st.text(OWN), own),
       "migration/goal24c-resource-ownership.json (batch Goal24C, kind import, original at aee05a40f) lists the 23 imported files, in the standard JSON layout", (len(assets), own.get("batch"), own.get("source_commit")))
    bad = [t for t in targets if t not in st.files or t not in inp.o_res or st.files[t] != inp.o_res[t] or sha(st.files[t]) != sha(inp.o_res[t])]
    ck("V9.bytes-equal-original", not bad, "each of the 23 NEO files is byte-equal (SHA-256) to the original working-tree file (the OBJ files are the CRLF worktree bytes)", bad[:5])
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
    ck("V9.record-matches", not bad_rec and not bad_png and not bad_text, "each record entry's source and target path, SHA-256 (source = target = file), byte count and PNG size (none for .mcmeta / .obj) equal the file; target paths are lowercase; description and ownership text are present", (bad_rec[:3], bad_png[:3], bad_text[:3]))
    ck("V9.last-commit", "error" not in inp.last_commit and not bad_commit and len(inp.last_commit) == 23, "source_last_change_commit equals `git log -1 --format=%H -- <path>` in the original for all 23", (bad_commit[:3], inp.last_commit.get("error")))
    bad = []
    for orig, neo in IMPORTS:
        if not orig.endswith(".obj"):
            continue
        t, a, data, blob = RES + neo, by_target.get(RES + neo, {}), st.files.get(RES + neo, b""), inp.o_blob.get(RES + neo)
        if blob is None or not (a.get("worktree_crlf_lines") == data.count(b"\r\n") > 0 and a.get("blob_sha256") == sha(blob) and a.get("blob_bytes") == len(blob) and a.get("normalized_sha256") == sha(data.replace(b"\r\n", b"\n"))
                                and a.get("normalized_equal_to_blob") is True and a.get("normalized_sha256") == a.get("blob_sha256") and data != blob):
            bad.append(t)
    ck("V9.obj-fields", not bad and len([1 for o, _ in IMPORTS if o.endswith(".obj")]) == 2, "the two OBJ records carry the worktree CRLF line count, the Git blob hash and size (`git show HEAD:<path>` in the original) and the LF-normalised hash that equals the blob (the worktree is CRLF, the blob LF)", bad)
    ni = own.get("not_imported", [])
    ni_names = [x["source_path"].rsplit("/", 1)[1] for x in ni]
    want_ni = set(n.rsplit("/", 1)[1] for n in NOT_IMPORTED_MUST + REASIM_NOT_IMPORTED)
    neo_has = [n for n in want_ni if (RES + "textures/block/rbmk/" + n) in st.tree]
    keep = [RES + "textures/block/block_corium.png", RES + "textures/block/block_corium_cobble.png"]
    ck("V9.not-imported", len(ni) == 19 and set(ni_names) == want_ni and len(ni_names) == len(set(ni_names)) and all(x.get("present_in_original") is True and str(x.get("reason", "")).strip() for x in ni) and all(inp.o_not_imported.values()) and not neo_has
       and all(hashed_equal(inp, st, p) for p in keep),
       "not_imported lists the 19 files the handoff names (rbmk_element.png, the 16 ReaSim textures, block_corium.png, block_corium_cobble.png) with reasons; they exist in the original, the first 17 are absent from NEO and the two corium block textures are the unchanged start files",
       (sorted(set(ni_names) ^ want_ni), neo_has))
    base_res = {p for p in inp.base_files if p.startswith(RES)}
    new_res = {p for p in st.tree if p.startswith(RES) and p not in base_res}
    changed_res = [p for p in base_res if st.tree.get(p) != inp.base_files[p]]
    ck("V9.no-unlisted", new_res == set(targets) and changed_res == [ZH], "the new files under assets/hbmsntm are exactly the 23 listed imports and the only existing resource that changed is zh_cn.json", (sorted(new_res ^ set(targets))[:5], changed_res[:5]))
    gtex = st.files.get(GUITEX)
    ck("V9.gui-texture", gtex is not None and png_size(gtex) == [256, 256], "gui_rbmk_element.png is a 256 x 256 PNG, the default blit atlas size the screen's rectangles (up to x 226, y 186) assume", png_size(gtex) if gtex else None)


# ---------------------------------------------------------------- V10 scope

ALLOWED_MIGRATION = ("migration/goal24c-", "migration/GOAL24")
ALLOWED_MIGRATION_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md", "migration/RESOURCE-OWNERSHIP.md"}
BASEBLK_OLD = "the slotted columns add theirs later (original openInv"
BASEBLK_NEW = "the slotted columns (RBMKRodBlock) override this and open theirs (original openInv"
UNTOUCHED = [DIALS, NTMCONFIG, ROD_ITEM, PELLET_ITEM, HAZ, LID_ITEM, J +"blocks/machine/rbmk/RBMKPassiveBlock.java", J + "blocks/machine/rbmk/RBMKDebrisBlock.java", J + "blocks/machine/rbmk/RBMKDebrisBurningBlock.java",
             J + "blocks/machine/rbmk/RBMKDebrisRadiatingBlock.java", J + "entity/projectile/RBMKDebris.java", BE + "RBMKType.java", BE + "RBMKColumnType.java", BE + "RBMKBlankBlockEntity.java", BE + "RBMKModeratorBlockEntity.java",
             BE + "RBMKReflectorBlockEntity.java", BE + "RBMKAbsorberBlockEntity.java", ANVIL, INFO, J + "gametest/RBMKCoreGameTests.java", J + "gametest/RBMKFuelGameTests.java", J + "gametest/HazardGameTests.java"]


def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v10_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files]
    imports = [RES + n for _, n in IMPORTS]
    expected = set(NEW_CLASSES + EDITED + [ZH, MAP, EN, STAMP, OWN, PICK, GT, BASEBLK] + imports + gen_new)
    extra = [p for p in changed if p not in expected and not p.startswith(ALLOWED_MIGRATION) and p not in ALLOWED_MIGRATION_EXACT]
    ck("V10.no-extra-paths", not extra, "every changed src/ and migration/ path since the start belongs to the batch: the new and edited production files, the language files, the 23 imports, the generated outputs, the GameTest file and the migration records", extra[:10])
    ck("V10.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in expected if p not in changed and p != GT]
    ck("V10.expected-all-changed", not never, "every expected production, resource and generated path really differs from the start (the GameTest file is checked in V11)", never[:5])
    ck("V10.counts", len(NEW_CLASSES) == 15 and len(EDITED) == 17 and len(imports) == 23 and len(gen_new) == 14 + 0 and len(set(NEW_CLASSES + EDITED)) == 32,
       "15 new production classes, 17 edited production files, 23 imported resources, 14 new generated files", (len(NEW_CLASSES), len(EDITED), len(imports), len(gen_new)))
    ck("V10.new-classes-new", all(p not in inp.base_files for p in NEW_CLASSES + [OWN]) and all(p in inp.base_files for p in EDITED), "the 15 new classes and the ownership record did not exist at the start and the 17 edited files did")
    ck("V10.not-touched", all(hashed_equal(inp, st, p) for p in UNTOUCHED), "the Goal24A / Goal24B files outside the handoff (RBMKDials, NtmConfig, the rod and pellet items, the lid item, HazardRegistry, the passive columns and debris classes and their block entities, RBMKType, AnvilRecipes, InfoScreen, the older "
       "RBMK GameTests) are byte-equal to the start", [p.rsplit("/", 1)[1] for p in UNTOUCHED if not hashed_equal(inp, st, p)])
    # the one Goal24A file the batch touches: a comment-only change of one line of RBMKBaseBlock.useItemOn (review fix)
    start_blk, live_blk = lf(inp.start[BASEBLK]), lf(st.text(BASEBLK))
    ck("V10.base-block-comment", start_blk.count(BASEBLK_OLD) == 1 and live_blk == start_blk.replace(BASEBLK_OLD, BASEBLK_NEW) and ("\r\n" in inp.start[BASEBLK]) == ("\r\n" in st.text(BASEBLK)),
       "RBMKBaseBlock.java (a Goal24A file) differs from the start copy by exactly one comment line in useItemOn: `the slotted columns add theirs later` -> `the slotted columns (RBMKRodBlock) override this and open theirs`; same line endings, nothing else", first_diff(start_blk.replace(BASEBLK_OLD, BASEBLK_NEW), live_blk))
    rest = sorted(p for p in changed if p.startswith(ALLOWED_MIGRATION) or p in ALLOWED_MIGRATION_EXACT)
    ck("V10.records", True, "migration records changed (allowed, not required): " + ", ".join(Path(p).name for p in rest))
    ck("V10.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V11 / V12 / V13

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(t))) for t in texts)


def other_gametests():
    return gametest_total(read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != "RBMKReactorGameTests.java")


def v11_gametest(ck, inp, st):
    ck("V11.other-tests", inp.gametest_other == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests (143 + 15 RBMKFuelGameTests... as counted by @GameTest( in the other classes)", inp.gametest_other)
    ck("V11.present", st.has(GT), "RBMKReactorGameTests.java exists (written by the GameTest verifier)")
    if not st.has(GT):
        return dict(rbmk_reactor_tests=[])
    live = lf(st.text(GT))
    code = blank_comments(live)
    tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
    ck("V11.tests", len(tests) >= 1 and len(tests) == len(re.findall(r"@GameTest\(", code)) and all("batch =" in a for a in tests.values()),
       "RBMKReactorGameTests has @GameTest methods, each public static void name(GameTestHelper helper) with a batch: " + ", ".join(tests), len(tests))
    batches = []
    for args in tests.values():
        m = re.search(r"batch\s*=\s*([^,)]+)", args)
        batches.append(m[1].strip().strip('"') if m else None)
    ck("V11.own-batch", len(tests) >= 1 and None not in batches and len(set(batches)) == len(batches), "every test has its own batch (the neutron StreamWorld and the chunk radiation are per level and shared by simultaneous tests)", batches)
    ck("V11.holder", "@GameTestHolder(NuclearTechMod.MODID)" in code and "@PrefixGameTestTemplate(false)" in code, "RBMKReactorGameTests is a @GameTestHolder(NuclearTechMod.MODID) with @PrefixGameTestTemplate(false), like the other RBMK GameTests")
    ck("V11.marker", f'"{GT_MARK} {{}} passed"' in live, f"the class logs `{GT_MARK} <name> passed`")
    miss = []
    for name in tests:
        try:
            if f'"{name}"' not in body(live, f"void {name}(GameTestHelper helper)"):
                miss.append(name)
        except ValueError:
            miss.append(name)
    ck("V11.report-name", not miss, "every test method passes its own name to the passed helper", miss)
    ck("V11.no-client", not re.search(r"net\.minecraft\.client", code), "RBMKReactorGameTests references no client class")
    return dict(rbmk_reactor_tests=sorted(tests))


def v12_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    live = lf(st.text(GT)) if st.has(GT) else ""
    tests = [n for _, n in TEST_ANNOTATED.findall(blank_comments(live))]
    # the expected total is counted from the @GameTest annotations of the source files (the other classes plus RBMKReactorGameTests), not taken from a literal
    total = inp.gametest_other + gametest_total([live])
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V12.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` ({inp.gametest_other} in the other classes + {len(tests)} RBMKReactorGameTests, counted from the @GameTest annotations)", (match and match[0], total))
    ck("V12.annotation-total", inp.gametest_other == START_GAMETESTS and gametest_total([live]) == len(tests), f"the other classes hold the {START_GAMETESTS} start tests and every @GameTest( of RBMKReactorGameTests is a method of the form checked in V11 ({len(tests)})")
    ck("V12.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in tests:
        ck(f"V12.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V12.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, log=str(path), log_sha256=sha(Path(path).read_bytes()))


def inner_expected(text):
    code = blank_comments(lf(text))
    anon = len(re.findall(r"new\s+[A-Z][\w.<>]*\s*\([^();{}]*\)\s*\{", code))
    nested = len(re.findall(r"^[ \t]{4,}(?:(?:public|private|protected|static|final|abstract)\s+)*(?:class|record|enum|interface)\s+\w+", code, re.M))
    return anon + nested


def v13_jar(ck, inp, st, path):
    classes = {p.split("/java/")[1][:-5]: p for p in NEW_CLASSES + ([GT] if st.has(GT) else [])}
    live_en, _ = json_pairs(st.text(EN))
    live_zh, _ = json_pairs(st.text(ZH))
    keys = [e[0] for e in expected_lang(inp)]
    gen_new = [p for p in st.tree if p.startswith(GEN) and p not in inp.base_files and not p.endswith("/.migration-stamp.json")]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        # A javadoc-only package-info.java compiles to no class file (main-agent fix after the first --jar run).
        missing = [c for c in classes if c + ".class" not in names and not c.endswith("/package-info")]
        short = {}
        for c, p in classes.items():
            have = len([n for n in names if n.startswith(c + "$") and n.endswith(".class")])
            if have < inner_expected(st.text(p)):
                short[c] = (have, inner_expected(st.text(p)))
        ck("V13.classes", not missing, "the JAR has the 15 new production classes and RBMKReactorGameTests", missing)
        ck("V13.inner-classes", not short, "the JAR has at least as many inner/anonymous classes as the sources declare", short)
        res = [RES + n for _, n in IMPORTS]
        bad = [p for p in res if p[len("src/main/resources/"):] not in names or jar.read(p[len("src/main/resources/"):]) != st.files.get(p)]
        ck("V13.resources", not bad and len(res) == 23, "the 23 imported textures, animation files, OBJ models and the GUI texture in the JAR are byte-equal to the source files", bad[:5])
        gbad = [p for p in gen_new + [EN, PICK] if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p, (ROOT / p).read_bytes())]
        ck("V13.generated", not gbad and len(gen_new) == 14, "the 14 new generated blockstates, models, loot tables, recipe and advancement, en_us.json and the pickaxe tag in the JAR are byte-equal to the live files", gbad[:5])
        ck("V13.zh_cn", "assets/hbmsntm/lang/zh_cn.json" in names and jar.read("assets/hbmsntm/lang/zh_cn.json") == st.files[ZH], "zh_cn.json in the JAR equals the source file")
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V13.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in keys if data.get(k) != source.get(k) or k not in data}
            ck(f"V13.{Path(entry).name}", not bad, f"{entry} in the JAR carries the 12 new keys with the values of the source file", dict(list(bad.items())[:3]))
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts=None, v1=True):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    if v1:
        guarded(ck, "V1", v1_original, inp, st)
    r2 = guarded(ck, "V2", v2_neutron, inp, st)
    guarded(ck, "V3", v3_event_handler, inp, st)
    r4 = guarded(ck, "V4", v4_rod, inp, st)
    guarded(ck, "V4", v4_support, inp, st)
    for fn in (v5_blocks, v5_menu, v5_screen, v5_render, v5_registrations, v5_scope):
        guarded(ck, "V5", fn, inp, st)
    guarded(ck, "V6", v6_recipes, inp, st)
    guarded(ck, "V7", v7_datagen, inp, st)
    guarded(ck, "V8", v8_lang, inp, st)
    guarded(ck, "V9", v9_resources, inp, st)
    guarded(ck, "V10", v10_scope, inp, st)
    r11 = guarded(ck, "V11", v11_gametest, inp, st)
    if facts is not None:
        facts["V2"], facts["V4"], facts["V11"] = r2, r4, r11
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
    """Edit the original's source text in memory (never on disk): V1 must notice a moved or changed line."""
    def apply(st):
        st.orig_edits[name] = fn
    return apply


def regex_sub(text, pattern, repl):
    new, n = re.subn(pattern, repl, text, flags=re.S)
    assert n == 1, (pattern, n)
    return new


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None)."""
    rod = lambda old, new: T(RODBE, lambda t: rep1(t, old, new))  # noqa: E731
    rnh = lambda old, new: T(RNH, lambda t: rep1(t, old, new))  # noqa: E731
    blk = lambda old, new: T(RODBLK, lambda t: rep1(t, old, new))  # noqa: E731
    return [
        # ---- V1 original (in-memory edits of the original text; a moved or changed line must fail loudly)
        ("orig_gate_200_to_250", "V1.", OE("rod", lambda t: rep1(t, "ItemRBMKRod.getHullHeat(slots[0]) <= 200", "ItemRBMKRod.getHullHeat(slots[0]) <= 250"))),
        ("orig_cache_time", "V1.", OE("nh", lambda t: rep1(t, "int cacheTime = 20;", "int cacheTime = 25;"))),
        ("orig_hull_1500", "V1.", OE("rodblk", lambda t: rep1(t, "ItemRBMKRod.getHullHeat(tile.slots[0]) >= 1500", "ItemRBMKRod.getHullHeat(tile.slots[0]) >= 1600"))),
        ("orig_corium_fire", "V1.", OE("corium", lambda t: rep1(t, "entity.setFire(3);", "entity.setFire(5);"))),
        ("orig_unload_hook", "V1.", OE("meh", lambda t: rep1(t, "NeutronNodeWorld.streamWorlds.remove(event.world);", "NeutronNodeWorld.streamWorlds.clear();"))),
        ("orig_recipe_row", "V1.", OE("cm", lambda t: rep1(t, "\"C\", \"R\", \"C\", 'C', STEEL.shell(), 'R', ModBlocks.rbmk_blank", "\"C\", \"R\", \"C\", 'C', CU.shell(), 'R', ModBlocks.rbmk_blank"))),
        # ---- V2 neutron package
        ("rnh_irradiation_factor", "V2.", T(RNH, lambda t: rep1(t, "incrementRad(level, targetPos, (float) (this.fluxQuantity * 0.05F));", "incrementRad(level, targetPos, (float) (this.fluxQuantity * 0.5F));"))),
        ("rnh_swap_moderator_reflector", "V2.", T(RNH, lambda t: swap_lines(t, "if(type == RBMKType.MODERATOR || nodeTE.isModerated()) {", "else if(type == RBMKType.REFLECTOR) {"))),
        ("rnh_rod_return_dropped", "V2.", T(RNH, lambda t: rep1(t, "rod.receiveFlux(this);\n                            return;", "rod.receiveFlux(this);"))),
        ("rnh_reflector_return_dropped", "V2.", T(RNH, lambda t: rep1(t, "receiver.receiveFlux(this);\n                    return;", "receiver.receiveFlux(this);"))),
        ("rnh_reflector_receives_on_node", "V2.", rnh("if(originTE instanceof IRBMKFluxReceiver receiver)", "if(nodeTE instanceof IRBMKFluxReceiver receiver)")),
        ("rnh_reflector_cast_restored", "V2.", rnh("if(originTE instanceof IRBMKFluxReceiver receiver)\n                        receiver.receiveFlux(this);", "((IRBMKFluxReceiver) originTE).receiveFlux(this);")),
        ("rnh_tick_guard_dropped", "V2.", rnh("if(!level.shouldTickBlocksAt(targetPos))\n                    return;", "")),
        ("rnh_tick_guard_after_node_lookup", "V2.", T(RNH, lambda t: rep1(rep1(t, "if(!level.shouldTickBlocksAt(targetPos))\n                    return;", ""),
                                                                         "NeutronNode targetNode = streamWorld.getNode(targetPos);", "NeutronNode targetNode = streamWorld.getNode(targetPos);\n                if(!level.shouldTickBlocksAt(targetPos))\n                    return;"))),
        ("rnh_tick_guard_negated", "V2.", rnh("if(!level.shouldTickBlocksAt(targetPos))", "if(level.shouldTickBlocksAt(targetPos))")),
        ("rnh_absorber_heat_changed", "V2.", rnh("RBMKDials.getAbsorberHeatConversion() * this.fluxQuantity", "RBMKDials.getAbsorberHeatConversion() + this.fluxQuantity")),
        ("rnh_origin_irradiation_moved", "V2.", rnh("(float) (fluxQuantity * 0.05F * (1 - (double) hits / columnHeight))", "(float) (fluxQuantity * 0.05F * (1 - (double) hits / (columnHeight + 1)))")),
        ("rnh_opaque_test_changed", "V2.", rnh("if(state.isSolidRender(level, above))", "if(state.canOcclude())")),
        ("rnh_client_import_added", "V2.|V5.", rnh("package com.hbm.handler.neutron;", "package com.hbm.handler.neutron;\n\nimport net.minecraft.client.Minecraft;")),
        ("handler_cache_time", "V2.", T(NODEH, lambda t: rep1(t, "int cacheTime = 20;", "int cacheTime = 40;"))),
        ("handler_empty_worlds_dropped", "V2.", T(NODEH, lambda t: drop_line(t, "NeutronNodeWorld.removeEmptyWorlds();"))),
        ("handler_column_height", "V2.", T(NODEH, lambda t: rep1(t, "RBMKNeutronHandler.columnHeight = RBMKDials.getColumnHeight() + 1;", "RBMKNeutronHandler.columnHeight = RBMKDials.getColumnHeight();"))),
        ("stream_blocks_rounding", "V2.", T(NSTREAM, lambda t: rep1(t, "Math.floor(0.5 + vector.x * i)", "Math.floor(vector.x * i)"))),
        ("world_map_key", "V2.", T(NNW, lambda t: rep1(t, "Map<Level, StreamWorld> streamWorlds", "Map<net.minecraft.resources.ResourceKey<Level>, StreamWorld> streamWorlds"))),
        ("pile_handler_added", "V2.|V10.", lambda st: st.set_text(J + "handler/neutron/PileNeutronHandler.java", "package com.hbm.handler.neutron;\npublic class PileNeutronHandler {}\n")),
        # ---- V3 event handler
        ("eh_neutron_before_radar", "V3.", T(EH, lambda t: swap_lines(t, "NeutronHandler.onServerTick(event.getServer());", "MachineRadarBlockEntity.updateSystem(event.getServer());"))),
        ("eh_remove_world_dropped", "V3.", T(EH, lambda t: drop_line(t, "NeutronNodeWorld.removeWorld(level);"))),
        ("eh_remove_all_dropped", "V3.", T(EH, lambda t: drop_line(t, "NeutronNodeWorld.removeAllWorlds();"))),
        # ---- V4 rod block entity and support
        ("rod_flux_from_type_coefficient", "V4.", rod("case FAST: return fastFlux + slowFlux * 0.3;", "case FAST: return fastFlux + slowFlux * 0.5;")),
        ("rod_manual_gate", "V4.", rod("RBMKRodItem.getHullHeat(stack) <= 200;", "RBMKRodItem.getHullHeat(stack) <= 250;")),
        ("rod_autoloader_gate", "V4.", rod("RBMKRodItem.getHullHeat(stack) <= 1_000;", "RBMKRodItem.getHullHeat(stack) <= 1_500;")),
        ("rod_tick_radiation_factor", "V4.", rod("incrementRad(this.level, this.worldPosition, (float) (this.fluxQuantity * 0.05F));", "incrementRad(this.level, this.worldPosition, (float) (this.fluxQuantity * 0.5F));")),
        ("rod_tracking_range", "V4.", rod("return 25;", "return 24;")),
        ("rod_nbt_key_renamed", "V4.", rod('tag.putDouble("fluxQuantity", this.lastFluxQuantity);', 'tag.putDouble("fluxQty", this.lastFluxQuantity);')),
        ("rod_compat_branch_dropped", "V4.", rod('if(tag.contains("fluxFast") || tag.contains("fluxSlow")) {', "if(false) {")),
        ("rod_melt_lid_read_dropped", "V4.", T(RODBE, lambda t: drop_line(t, "LidType lid = this.getLid();"))),
        ("rod_corium_range_shortened", "V4.", rod("for(int i = h; i >= 0; i--) {", "for(int i = h; i > 0; i--) {")),
        ("rod_ror_name_changed", "V4.", T(RODBE, lambda t: rep_first(t, 'PREFIX_VALUE + "fastflux"', 'PREFIX_VALUE + "fastfluxx"'))),
        ("rod_can_load_item_check", "V4.", rod("return !toLoad.isEmpty() && this.slots.get(0).isEmpty();", "return toLoad.getItem() instanceof RBMKRodItem && this.slots.get(0).isEmpty();")),
        ("rod_control_receiver_added", "V4.", rod("implements IRBMKFluxReceiver, IRBMKLoadable, IRORValueProvider {", "implements IRBMKFluxReceiver, IRBMKLoadable, IRORValueProvider, IControlReceiver {")),
        ("rod_client_import_added", "V4.|V5.", rod("package com.hbm.blockentity.machine.rbmk;", "package com.hbm.blockentity.machine.rbmk;\n\nimport net.minecraft.client.Minecraft;")),
        ("slotted_valid_reach_8", "V4.", T(SLOT, lambda t: rep1(t, "this.worldPosition.atY(y), 4.0D)", "this.worldPosition.atY(y), 8.0D)"))),
        ("slotted_valid_clamp_top_removed", "V4.", T(SLOT, lambda t: rep1(t, "this.worldPosition.getY() + RBMKDials.getColumnHeight())", "this.worldPosition.getY())"))),
        ("slotted_valid_override_removed", "V4.", T(SLOT, lambda t: regex_sub(t, r"    @Override\n    public boolean stillValid\(Player player\) \{.*?\n    \}\n\n", ""))),
        ("slotted_valid_identity_check_dropped", "V4.", T(SLOT, lambda t: rep1(t, "this.level == null || this.level.getBlockEntity(this.worldPosition) != this", "this.level == null"))),
        ("flux_ntype_reordered", "V4.",T(FLUX, lambda t: swap_lines(t, 'FAST("trait.rbmk.neutron.fast")', 'SLOW("trait.rbmk.neutron.slow")'))),
        ("base_be_lid_node_update_dropped", "V4.", T(BASEBE, lambda t: rep1(t, "node.addLid();", "node.removeLid();"))),
        ("base_be_random_not_first", "V4.", T(BASEBE, lambda t: rep1(t, "level.random.nextInt(3) == 0 && (b.is(NtmBlocks.PRIBRIS.get()) || b.is(NtmBlocks.PRIBRIS_BURNING.get()))", "(b.is(NtmBlocks.PRIBRIS.get()) || b.is(NtmBlocks.PRIBRIS_BURNING.get())) && level.random.nextInt(3) == 0"))),
        # ---- V5 blocks, menu, screen, registrations
        ("block_hull_threshold", "V5.", blk("RBMKRodItem.getHullHeat(stack) >= 1500", "RBMKRodItem.getHullHeat(stack) >= 1600")),
        ("block_creative_check_inverted", "V5.", blk("if(!player.hasInfiniteMaterials()) stack.shrink(1);", "if(player.hasInfiniteMaterials()) stack.shrink(1);")),
        ("block_client_core_lookup_server_path", "V5.", blk("level.isClientSide ? this.walkToCore(level, pos) : this.findCore(level, pos)", "this.findCore(level, pos)")),
        ("block_walk_to_core_steps", "V5.", blk("for(int i = 0; i <= 16; i++) {", "for(int i = 0; i <= 17; i++) {")),
        ("block_walk_to_core_direction", "V5.", blk("cursor.move(getPointingDirection(state).getOpposite());", "cursor.move(getPointingDirection(state));")),
        ("corium_damage", "V5.",T(CORIUM, lambda t: rep1(t, "NtmDamageTypes.RADIATION), 2F);", "NtmDamageTypes.RADIATION), 1F);"))),
        ("corium_fire_seconds", "V5.", T(CORIUM, lambda t: rep1(t, "entity.igniteForSeconds(3);", "entity.igniteForSeconds(4);"))),
        ("menu_slot_position", "V5.", T(MENU, lambda t: rep1(t, "new Slot(be, 0, 80, 45)", "new Slot(be, 0, 80, 46)"))),
        ("menu_pickup_creative_dropped", "V5.", T(MENU, lambda t: rep1(t, "player.getAbilities().instabuild || be.coldEnoughForManual()", "be.coldEnoughForManual()"))),
        ("screen_height", "V5.", T(SCREEN, lambda t: rep1(t, "this.imageHeight = 186;", "this.imageHeight = 187;"))),
        ("screen_xenon_rectangle", "V5.", T(SCREEN, lambda t: rep1(t, "212, 58 - x, 14, x)", "212, 58 - x, 13, x)"))),
        ("render_cherenkov_threshold", "V5.", T(RENDER, lambda t: rep1(t, "be.fluxQuantity > 5", "be.fluxQuantity > 6"))),
        ("registration_dropped", "V5.", T(NB, lambda t: drop_line(t, "RBMK_ROD_MOD = register("))),
        ("registration_duplicated_menu", "V5.", T(MT, lambda t: dup_line(t, 'RBMK_ROD = reg("rbmk_rod"'))),
        ("registration_corium_light", "V5.", T(NB, lambda t: rep1(t, "COLOR_BROWN).lightLevel(state -> 10)", "COLOR_BROWN).lightLevel(state -> 15)"))),
        ("registration_screen_dropped", "V5.", T(NMC, lambda t: drop_line(t, "RBMKRodScreen::new);"))),
        ("registration_renderer_dropped", "V5.", T(CP, lambda t: drop_line(t, "new RenderRBMKRod()"))),
        ("registration_geometry_dropped", "V5.", T(GEO, lambda t: rep1(t, "RBMK_DEBRIS,\n        RBMK_ELEMENT\n", "RBMK_DEBRIS\n"))),
        ("tab_order_swapped", "V5.", T(CT, lambda t: swap_lines(t, "output.accept(NtmBlocks.RBMK_ROD);", "output.accept(NtmBlocks.RBMK_ROD_MOD);"))),
        ("tab_corium_added", "V5.", T(CT, lambda t: insert_after(t, "output.accept(NtmBlocks.RBMK_ROD_MOD);", "                        output.accept(NtmBlocks.CORIUM_BLOCK);"))),
        ("menu_client_import_added", "V5.", T(MENU, lambda t: rep1(t, "package com.hbm.inventory.menus;", "package com.hbm.inventory.menus;\n\nimport net.minecraft.client.Minecraft;"))),
        ("corium_fluid_added", "V5.", T(CORIUM, lambda t: rep1(t, "public class CoriumBlock extends Block {", "public class CoriumBlock extends Block {\n\n    @Override\n    public net.minecraft.world.level.material.FluidState getFluidState(BlockState state) { return null; }"))),
        # ---- V6 recipes
        ("recipe_count", "V6.", gen_edit(RECIPES + "rbmk_rod.json", lambda d: d["result"].__setitem__("count", 2))),
        ("recipe_pattern", "V6.", gen_edit(RECIPES + "rbmk_rod.json", lambda d: d["pattern"].__setitem__(1, "S"))),
        ("recipe_ingredient", "V6.", gen_edit(RECIPES + "rbmk_rod.json", lambda d: d["key"]["C"].__setitem__("item", "hbmsntm:shell_iron"))),
        ("recipe_rod_mod_added", "V6.", lambda st: st.set_bytes(RECIPES + "rbmk_rod_mod.json", b"{}")),
        ("anvil_recipes_changed", "V6.", T(ANVIL, lambda t: t + "\n// stray\n")),
        # ---- V7 datagen outputs
        ("blockstate_model_changed", "V7.", gen_edit(G_STATE + "rbmk_rod_mod.json", lambda d: d["variants"][""].__setitem__("model", "hbmsntm:block/rbmk_rod"))),
        ("block_model_texture_changed", "V7.", gen_edit(G_BMODEL + "rbmk_rod_mod.json", lambda d: d["textures"].__setitem__("side", "hbmsntm:block/rbmk/rbmk_element_side"))),
        ("block_model_type_changed", "V7.", gen_edit(G_BMODEL + "rbmk_rod.json", lambda d: d.__setitem__("type", "rbmk_debris"))),
        ("loot_corium_gets_drop", "V7.", lambda st: st.set_text(G_LOOT + "corium_block.json", st.text(G_LOOT + "rbmk_rod.json").replace("rbmk_rod", "corium_block"))),
        ("pickaxe_entry_dropped", "V7.", T(PICK, lambda t: drop_line(t, '"hbmsntm:corium_block",'))),
        ("generated_hand_edit", "V7.", lambda st: st.set_text(G_IMODEL + "rbmk_rod.json", st.text(G_IMODEL + "rbmk_rod.json") + "\n")),
        ("provider_edit_without_rundata", "V7.", T(BSP, lambda t: rep1(t, 'String base = "block/rbmk/" + texture;', 'String base = "block/rbmk/" + texture + "";'))),
        ("provider_tag_extra_block", "V7.", T(TAGP, lambda t: rep1(t, "NtmBlocks.CORIUM_BLOCK.get(),", "NtmBlocks.CORIUM_BLOCK.get(),\n                        NtmBlocks.PRIBRIS.get(),"))),
        # ---- V8 language
        ("zh_value_changed", "V8.", zh_set("container.rbmkRod", "RBMK燃料棒")),
        ("zh_local_value_changed", "V8.", zh_set("container.rbmkRod.manualHot", "燃料外壳温度已超过 250°C，$无法再徒手取出燃料！")),
        ("zh_key_removed", "V8.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("tile.rbmk.dodd.f_yield")))),
        ("zh_crlf_broken", "V8.", Bx(ZH, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_crlf_broken", "V8.", Bx(MAP, lambda b: b.replace(b"\r\n", b"\n", 1))),
        ("map_source_zh_changed", "V8.", map_set("tile.rbmk.dodd.hasRod", "source_zh", "有无燃料棒")),
        ("map_target_zh_changed", "V8.", map_set("block.hbmsntm.corium_block", "target_zh", "堆芯熔融")),
        ("map_reason_removed", "V8.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["container.rbmkRod.autoloaderHot"].pop("reason")))),
        ("map_kind_flipped", "V8.", map_set("container.rbmkRod.manualHot", "kind", "upstream")),
        ("map_entry_removed", "V8.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"].pop("block.hbmsntm.rbmk_rod_mod")))),
        ("provider_string_changed", "V8.", T(LP, lambda t: rep1(t, 'this.add(NtmBlocks.CORIUM_BLOCK, "Corium");', 'this.add(NtmBlocks.CORIUM_BLOCK, "Corium ");'))),
        ("en_value_changed", "V8.", lambda st: st.set_text(EN, st.text(EN).replace('"Flux Fast"', '"Fast Flux"'))),
        # ---- V9 resources
        ("texture_byte_flipped", "V9.", Bx(TEX + "rbmk/rbmk_element_side.png", flip_byte)),
        ("corium_mcmeta_byte_flipped", "V9.", Bx(TEX + "corium_still.png.mcmeta", flip_byte)),
        ("obj_line_endings_changed", "V9.", Bx(OBJDIR + "rbmk_element_rods.obj", lambda b: b.replace(b"\r\n", b"\n"))),
        ("gui_texture_byte_flipped", "V9.", Bx(GUITEX, flip_byte)),
        ("texture_deleted", "V9.|V10.", D(TEX + "rbmk/rbmk_element_mod_fuel.png")),
        ("reasim_texture_imported", "V9.|V10.", lambda st: st.set_bytes(TEX + "rbmk/rbmk_element_reasim_side.png", b"x")),
        ("ownership_obj_dropped", "V9.", own_edit(lambda d: d["assets"].remove(next(a for a in d["assets"] if a["target_path"].endswith("rbmk_element_rods.obj"))))),
        ("ownership_sha_changed", "V9.", own_edit(lambda d: d["assets"][5].__setitem__("target_sha256", "0" * 64))),
        ("ownership_obj_field_changed", "V9.", own_edit(lambda d: next(a for a in d["assets"] if a["target_path"].endswith("rbmk_element.obj")).__setitem__("worktree_crlf_lines", 785))),
        ("ownership_not_imported_dropped", "V9.", own_edit(lambda d: d["not_imported"].pop())),
        # ---- V10 scope
        ("stray_src_file_added", "V10.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}")),
        ("unrelated_src_file_touched", "V10.", touch(DIALS)),
        ("unrelated_migration_file_added", "V10.", lambda st: st.set_bytes("migration/stray.json", b"{}")),
        ("base_block_code_changed", "V10.", T(BASEBLK, lambda t: rep1(t, "return super.useItemOn(stack, state, level, pos, player, hand, hitResult);", "return ItemInteractionResult.SKIP_DEFAULT_BLOCK_INTERACTION;"))),
        ("base_block_comment_extended", "V10.", T(BASEBLK, lambda t: rep1(t, "override this and open theirs (original openInv", "override this and open theirs too (original openInv"))),
        ("base_block_comment_reverted", "V10.", T(BASEBLK, lambda t: rep1(t, "the slotted columns (RBMKRodBlock) override this and open theirs (original openInv", "the slotted columns add theirs later (original openInv"))),
        ("production_file_reverted", "V10.",lambda st: st.tree.__setitem__(NB, st.inp_base[NB])),
        # ---- V11 GameTest source
        ("gt_marker_changed", "V11.", T(GT, lambda t: t.replace('"' + GT_MARK + ' {} passed"', '"[hbm-rbmk] {} passed"')), GT),
        ("gt_holder_removed", "V11.", T(GT, lambda t: rep1(t, "@GameTestHolder(NuclearTechMod.MODID)", "")), GT),
        ("gt_batch_shared", "V11.", T(GT, lambda t: rep1(t, 'batch = "rbmk_reactor_ignition"', 'batch = "rbmk_reactor_nodes"')), GT),
        ("gt_deleted", "V11.", D(GT), GT),
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
        mutated.inp_base = inp.base_files
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
    for sec in ("V12", "V13"):
        out.setdefault(sec, [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec in ("V12", "V13") and not items:
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
    inp.gametest_other = other_gametests()
    st.orig_edits = {}
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V12", v12_log, inp, st, args.gametest_log)
    if args.jar:
        extra["jar"] = guarded(ck, "V13", v13_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]
    secs = sections(ck)
    secs["V14"] = dict(status="PASS" if not undetected else "FAIL", checks=len(applied), passed=len(applied) - len(undetected), failed=undetected, skipped=skipped)
    production = NEW_CLASSES + EDITED + [LP, ZH, EN, STAMP, MAP, OWN, GT, BASEBLK]
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
