"""Verify the Goal23C batch statically: thermo_element, rtg_unit, the four ass.* rows, the machine_rtg RT generator (block, block entity, menu, screen,
OBJ renderer, six-way power), the 23B leftovers (mercury recycling, JEI depleted-pellet subtype), language, resources and the RTGGameTests source.

Read-only for both worktrees. Writes only build/migration/goal23c/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal23c/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original (TileEntityMachineRTG, ContainerMachineRTG, GUIMachineRTG, RenderRTG, ModBlocks, AssemblyMachineRecipes, MineralRecipes, ModItems,
      the lang files) parsed from the read-only worktree and asserted against the task book literals (GOAL23C.md C1).
- V2  NEO block entity MachineRTGBlockEntity.
- V3  NEO block, menu, screen and renderer, each coordinate cross-checked against V1.
- V4  Registration points, exactly once each, and client-class isolation.
- V5  The four assembly rows against V1 through the ingredient translation table.
- V6  23B leftovers: mercury recycling recipe (provider, generated JSON), still no nickel, JEI ignoreMeta, RTGPelletGameTests assertions.
- V7  Language: the eight keys in the provider, en_us.json, zh_cn.json and the mapping.
- V8  The five imported resources against the original, the git blob and goal23c-resource-ownership.json.
- V9  Scope: the src/ paths changed since the start equal the expected set; insert-only checks against the start copies.
- V10 GameTests (source): RTGGameTests and the RTGPelletGameTests diff.
- V11 (--gametest-log) the GameTest log; V12 (--jar) the packaged JAR; "not run" when the flag is absent.
- V13 In-memory mutations of the NEO inputs (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal23c_rtg_machine.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal23c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
BEP = J + "blockentity/machine/MachineRTGBlockEntity.java"
BLK = J + "blocks/machine/MachineRTGBlock.java"
MENU = J + "inventory/menus/MachineRTGMenu.java"
SCR = J + "inventory/screens/MachineRTGScreen.java"
REN = J + "render/blockentity/RenderRTG.java"
MENUBASE = J + "inventory/menus/MenuBase.java"
NB = J + "blocks/NtmBlocks.java"
NBET = J + "blockentity/NtmBlockEntityTypes.java"
NMT = J + "inventory/NtmMenuTypes.java"
NMC = J + "main/NuclearTechModClient.java"
CP = J + "main/ClientProxy.java"
RM = J + "main/ResourceManager.java"
NI = J + "items/NtmItems.java"
CT = J + "inventory/NtmCreativeTabs.java"
AMR = J + "inventory/recipes/AssemblyMachineRecipes.java"
RP = J + "datagen/NtmRecipeProvider.java"
JEI = J + "handler/jei/NtmJeiPlugin.java"
LOOT = J + "datagen/NtmBlockLootTableProvider.java"
TAG = J + "datagen/NtmBlockTagProvider.java"
MP = J + "datagen/NtmItemModelProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
RPGT = J + "gametest/RTGPelletGameTests.java"
RGT = J + "gametest/RTGGameTests.java"
GAMETEST_DIR = J + "gametest/"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal23c-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
RECIPES = GEN + "data/hbmsntm/recipe/"
ADVS = GEN + "data/hbmsntm/advancement/recipes/misc/"
RES = "src/main/resources/assets/hbmsntm/"

R_OBJ = RES + "models/obj/machines/rtg.obj"
R_TEX = RES + "textures/models/machines/rtg.png"
R_GUI = RES + "textures/gui/gui_rtg.png"
R_TE = RES + "textures/item/thermo_element.png"
R_RU = RES + "textures/item/rtg_unit.png"
O_RES_DIR = "src/main/resources/assets/hbm/"
RESOURCES = {R_OBJ: O_RES_DIR + "models/machines/rtg.obj", R_TEX: O_RES_DIR + "textures/models/machines/rtg.png", R_GUI: O_RES_DIR + "textures/gui/gui_rtg.png",
             R_TE: O_RES_DIR + "textures/items/thermo_element.png", R_RU: O_RES_DIR + "textures/items/rtg_unit.png"}

G_STATE = GEN + "assets/hbmsntm/blockstates/machine_rtg.json"
G_BMODEL = GEN + "assets/hbmsntm/models/block/machine_rtg_particle.json"
G_IM_RTG = GEN + "assets/hbmsntm/models/item/machine_rtg.json"
G_IM_TE = GEN + "assets/hbmsntm/models/item/thermo_element.json"
G_IM_RU = GEN + "assets/hbmsntm/models/item/rtg_unit.json"
G_LOOT = GEN + "data/hbmsntm/loot_table/blocks/machine_rtg.json"
G_TAG = GEN + "data/minecraft/tags/block/mineable/pickaxe.json"
G_REC = RECIPES + "pellet_rtg_depleted_mercury.json"
G_ADV = ADVS + "pellet_rtg_depleted_mercury.json"
GENERATED = [STAMP, EN, G_STATE, G_BMODEL, G_IM_RTG, G_IM_TE, G_IM_RU, G_LOOT, G_TAG, G_REC, G_ADV]

NEW_CLASSES = [BLK, BEP, MENU, SCR, REN]
EDITED = [NB, NBET, NMT, NMC, CP, RM, NI, CT, AMR, RP, JEI, LOOT, TAG, MP]
COPIED = EDITED + [LP, RPGT, STAMP, EN, ZH, MAP]

# original files
O = "src/main/java/com/hbm/"
O_TE = O + "tileentity/machine/TileEntityMachineRTG.java"
O_CONTAINER = O + "inventory/container/ContainerMachineRTG.java"
O_GUI = O + "inventory/gui/GUIMachineRTG.java"
O_RENDER = O + "render/tileentity/RenderRTG.java"
O_MODBLOCKS = O + "blocks/ModBlocks.java"
O_MODITEMS = O + "items/ModItems.java"
O_ASM = O + "inventory/recipes/AssemblyMachineRecipes.java"
O_MINERAL = O + "crafting/MineralRecipes.java"
O_LANG = "src/main/resources/assets/hbm/lang/"

GT_TESTS = ["rtg_place_initial", "rtg_generation", "rtg_heat_cap", "rtg_decay_in_machine", "rtg_power_network", "rtg_slot_rules", "rtg_nbt_and_sync",
            "rtg_break_drops", "rtg_assembly_rows", "rtg_slot_semantics"]
GT_BATCH = "rtg_machine"
GT_MARK = "[hbm-rtg-machine]"
START_GAMETESTS = 112
HASH_SKIP = ("__pycache__",)

# (NEO key, original key, en_US.lang line, zh_CN.lang line)
LANG = [("block.hbmsntm.machine_rtg", "tile.machine_rtg_grey.name", 5907, 5080), ("container.rtg", "container.rtg", 808, 646),
        ("desc.gui.rtg.heat", "desc.gui.rtg.heat", 989, 807), ("desc.gui.rtg.pellets", "desc.gui.rtg.pellets", 990, 808),
        ("desc.gui.rtg.pelletHeat", "desc.gui.rtg.pelletHeat", 991, 809), ("desc.gui.rtg.pelletPower", "desc.gui.rtg.pelletPower", 992, 810),
        ("item.hbmsntm.thermo_element", "item.thermo_element.name", 4655, 4062), ("item.hbmsntm.rtg_unit", "item.rtg_unit.name", 4437, 3869)]
KEYS = [k[0] for k in LANG]
EXPECT_LANG = {"block.hbmsntm.machine_rtg": ("RT Generator", "放射性同位素发电机"), "container.rtg": ("RT Generator", "放射性同位素发电机"),
               "desc.gui.rtg.heat": ("§eCurrent heat level: %s", "§e当前热等级：%s"), "desc.gui.rtg.pellets": ("Accepted Pellets:", "接受的靶丸："),
               "desc.gui.rtg.pelletHeat": ("%s (%s heat)", "%s (%s 热量)"), "desc.gui.rtg.pelletPower": ("%s (%s HE/tick)", "%s (%s HE/刻)"),
               "item.hbmsntm.thermo_element": ("Thermoelectric Element", "热电元件"), "item.hbmsntm.rtg_unit": ("RTG Unit", "放射性同位素单元")}
COUNTS_NOW = dict(en=2451, zh=2344, map=2451, upstream=1720, local=624, deferred=107)


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


def brace_depth(code, start, end):
    """Net brace depth of code[start:end] (strings skipped)."""
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


def split_top(text):
    """Split on commas outside parentheses, brackets and strings."""
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
    """The method body with comments removed and whitespace collapsed (the structure, not the layout)."""
    o, c, code = method_span(text, signature)
    return norm(code[o + 1:c])


def mcode(text, signature):
    return squash(method_code(text, signature))


def whole(text):
    """The whole file with comments removed and every whitespace character removed."""
    return squash(blank_comments(lf(text)))


def eol_of(text):
    return "\r" if "\r\n" in text and text.count("\r\n") == text.count("\n") else ""


_OPS = {}


def non_equal_ops(start, live):
    """List of (tag, i1, i2, start lines, live lines) of every non-equal opcode, line endings normalised."""
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


# ---------------------------------------------------------------- state and inputs

class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file, sha256 of every file under src, migration, tools and
    the per-file references to the client classes."""

    def __init__(self, files, tree, refs):
        self.files, self.tree, self.refs = files, tree, refs

    def copy(self):
        return State(dict(self.files), dict(self.tree), {k: dict(v) for k, v in self.refs.items()})

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
    for top in ("src", "migration", "tools"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


REF_PATTERNS = dict(MachineRTGScreen=re.compile(r"\bMachineRTGScreen\b"), RenderRTG=re.compile(r"\bRenderRTG\b"), ResourceManagerRTG=re.compile(r"\bResourceManager\.(?:rtg|RTG_TEX)\b"))


def scan_refs():
    refs = {}
    for base, dirs, names in os.walk(ROOT / "src/main/java"):
        for name in names:
            if not name.endswith(".java"):
                continue
            path = Path(base) / name
            text = path.read_bytes().decode("utf-8", errors="replace")
            hit = {k: len(p.findall(text)) for k, p in REF_PATTERNS.items() if p.search(text)}
            if hit:
                refs[path.relative_to(ROOT).as_posix()] = hit
    return refs


def gametest_count(texts):
    return sum(len(re.findall(r"@GameTest\(", t)) for t in texts)


def otext(path):
    return lf(read_text(ORIGINAL / path))


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start = {p: read_text(START / p) for p in COPIED}
    inp.start_hash_ok = {p: (START / p).exists() and sha((START / p).read_bytes()) == inp.base_files.get(p) for p in baseline["copied_scope"]}
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").decode("utf-8").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1").decode("utf-8")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o_en_lines = parse_lang_lines(read_text(ORIGINAL / O_LANG / "en_US.lang"))
    inp.o_zh_lines = parse_lang_lines(read_text(ORIGINAL / O_LANG / "zh_CN.lang"))
    inp.o = {name: otext(path) for name, path in dict(te=O_TE, container=O_CONTAINER, gui=O_GUI, render=O_RENDER, modblocks=O_MODBLOCKS, moditems=O_MODITEMS, asm=O_ASM,
                                                      mineral=O_MINERAL).items()}
    inp.o_res = {t: (ORIGINAL / s).read_bytes() for t, s in RESOURCES.items() if (ORIGINAL / s).exists()}
    inp.o_obj_blob = None
    try:
        inp.o_obj_blob = git(ORIGINAL, "show", "HEAD:" + RESOURCES[R_OBJ])
    except Exception as error:  # noqa: BLE001
        inp.o_obj_blob = repr(error).encode("utf-8")
    inp.gametest_other = gametest_count(read_text(p) for p in sorted((ROOT / GAMETEST_DIR).glob("*.java")) if p.name != "RTGGameTests.java")
    files = {}
    paths = NEW_CLASSES + EDITED + [LP, RPGT, ZH, MAP, OWN, MENUBASE, RGT] + GENERATED + list(RESOURCES)
    for pattern_dir, pattern in ((RECIPES, "pellet_rtg_depleted*.json"), (ADVS, "pellet_rtg_depleted*.json")):
        paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / pattern_dir).glob(pattern))]
    for path in paths:
        if (ROOT / path).exists():
            files[path] = (ROOT / path).read_bytes()
    return inp, State(files, hash_tree(), scan_refs())


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


def jload(st, path):
    return json.loads(st.text(path))


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    ck("V0.baseline-copies-match", all(inp.start_hash_ok.values()) and len(inp.start_hash_ok) == 27, "every baseline-files copy (27) hashes to its baseline.json entry",
       [p for p, v in inp.start_hash_ok.items() if not v])
    needed = NEW_CLASSES + EDITED + [LP, RPGT, ZH, MAP, OWN, MENUBASE] + GENERATED + list(RESOURCES)
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified and generated NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD, "baseline.json records the original HEAD", inp.baseline.get("source_head"))


# ---------------------------------------------------------------- V1

ORIG_GUI = {
    "size": (r"this\.xSize=(\d+);this\.ySize=(\d+);", (176, 188)),
    "texture": (r'":(textures/gui/gui_rtg\.png)"', ("textures/gui/gui_rtg.png",)),
    "electricity": (r"drawElectricityInfo\(this,mouseX,mouseY,guiLeft\+(\d+),guiTop\+(\d+),(\d+),(\d+),rtg\.power,rtg\.powerMax\)", (146, 9, 16, 51)),
    "heat_stat": (r'resolveKeyArray\("desc\.gui\.rtg\.heat",rtg\.heat\);this\.drawCustomInfoStat\(mouseX,mouseY,guiLeft\+(\d+),guiTop\+(\d+),(\d+),(\d+),mouseX,mouseY,heatText\)', (124, 9, 16, 51)),
    "pellet_panel": (r"drawCustomInfoStat\(mouseX,mouseY,guiLeft-(\d+),guiTop\+(\d+),(\d+),(\d+),guiLeft-(\d+),guiTop\+(\d+)\+(\d+),pelletText\)", (12, 25, 16, 16, 8, 36, 16)),
    "pellet_scale": (r'resolveKey\("desc\.gui\.rtg\.pelletPower",I18nUtil\.resolveKey\(pellet\.getUnlocalizedName\(\)\+"\.name"\),pellet\.getHeat\(\)\*(\d+)\)', (5,)),
    "pellet_header": (r'pelletText\[0\]=I18nUtil\.resolveKey\("(desc\.gui\.rtg\.pellets)"\)', ("desc.gui.rtg.pellets",)),
    "title": (r"drawString\(name,(\d+)-this\.fontRendererObj\.getStringWidth\(name\)/2,(\d+),(\d+)\)", (60, 7, 10925486)),
    "inventory_label": (r'drawString\(I18n\.format\("container\.inventory"\),(\d+),this\.ySize-(\d+)\+(\d+),(\d+)\)', (8, 96, 2, 4210752)),
    "heat_bar": (r"rtg\.hasHeat\(\)\)\{inti=rtg\.getHeatScaled\((\d+)\);drawTexturedModalRect\(guiLeft\+(\d+),guiTop\+(\d+)-i,(\d+),(\d+)\+\((\d+)-i\),(\d+),i\);",
                 (51, 124, 61, 176, 10, 51, 16)),
    "power_bar": (r"rtg\.hasPower\(\)\)\{inti=\(int\)rtg\.getPowerScaled\((\d+)\);drawTexturedModalRect\(guiLeft\+(\d+),guiTop\+(\d+)-i,(\d+),(\d+)\+\((\d+)-i\),(\d+),i\);",
                  (51, 146, 61, 192, 10, 51, 16)),
    "info_panel": (r"drawInfoPanel\(guiLeft-(\d+),guiTop\+(\d+),(\d+),(\d+),(\d+)\)", (12, 25, 16, 16, 2)),
}
NEO_GUI = {
    "size": (r"this\.imageWidth=(\d+);this\.imageHeight=(\d+);", (176, 188)),
    "texture": (r'withDefaultNamespace\("(textures/gui/gui_rtg\.png)"\)', ("textures/gui/gui_rtg.png",)),
    "electricity": (r"drawElectricityInfo\(guiGraphics,mouseX,mouseY,this\.leftPos\+(\d+),this\.topPos\+(\d+),(\d+),(\d+),this\.be\.power,MachineRTGBlockEntity\.MAX_POWER\)", (146, 9, 16, 51)),
    "heat_stat": (r'drawCustomInfoStat\(guiGraphics,mouseX,mouseY,this\.leftPos\+(\d+),this\.topPos\+(\d+),(\d+),(\d+),Component\.translatable\("desc\.gui\.rtg\.heat",this\.be\.heat\)\)',
                  (124, 9, 16, 51)),
    "pellet_panel": (r"drawCustomInfoStat\(guiGraphics,mouseX,mouseY,this\.leftPos-(\d+),this\.topPos\+(\d+),(\d+),(\d+),this\.leftPos-(\d+),this\.topPos\+(\d+)\+(\d+),pellets\)",
                     (12, 25, 16, 16, 8, 36, 16)),
    "pellet_scale": (r'for\(RTGPelletItempellet:RTGPelletItem\.PELLETS\)\{pellets\.add\(Component\.translatable\("desc\.gui\.rtg\.pelletPower",pellet\.getDescription\(\),pellet\.getHeat\(\)\*(\d+)\)\);\}',
                     (5,)),
    "pellet_header": (r'pellets\.add\(Component\.translatable\("(desc\.gui\.rtg\.pellets)"\)\);', ("desc.gui.rtg.pellets",)),
    "title": (r"drawString\(this\.font,this\.title,(\d+)-this\.font\.width\(this\.title\)/2,(\d+),(\d+),false\)", (60, 7, 10925486)),
    "inventory_label": (r"drawString\(this\.font,this\.playerInventoryTitle,(\d+),this\.imageHeight-(\d+)\+(\d+),(\d+),false\)", (8, 96, 2, 4210752)),
    "heat_bar": (r"this\.be\.hasHeat\(\)\)\{inti=this\.be\.getHeatScaled\((\d+)\);guiGraphics\.blit\(TEXTURE,this\.leftPos\+(\d+),this\.topPos\+(\d+)-i,(\d+),(\d+)\+\((\d+)-i\),(\d+),i,256,256\);",
                 (51, 124, 61, 176, 10, 51, 16)),
    "power_bar": (r"this\.be\.hasPower\(\)\)\{inti=\(int\)this\.be\.getPowerScaled\((\d+)\);guiGraphics\.blit\(TEXTURE,this\.leftPos\+(\d+),this\.topPos\+(\d+)-i,(\d+),(\d+)\+\((\d+)-i\),(\d+),i,256,256\);",
                  (51, 146, 61, 192, 10, 51, 16)),
    "info_panel": (r"this\.drawInfoPanel\(guiGraphics,this\.leftPos-(\d+),this\.topPos\+(\d+),(\d+)\)", (12, 25, 2)),
}
ORIG_CONNECTORS = {"POS_X": (("ix+1", "iy", "iz"), 0, None), "NEG_X": (("ix-1", "iy", "iz"), 180, -180), "NEG_Z": (("ix", "iy", "iz-1"), 90, -90), "POS_Z": (("ix", "iy", "iz+1"), -90, 90)}
NEO_CONNECTORS = {"EAST": ("east", 0, None), "WEST": ("west", 180, -180), "NORTH": ("north", 90, -90), "SOUTH": ("south", -90, 90)}
ORIG_TO_NEO_DIR = {"POS_X": "EAST", "NEG_X": "WEST", "NEG_Z": "NORTH", "POS_Z": "SOUTH"}
CONNECTOR_TAIL = r'(\{GL11\.glRotatef\((-?\d+),0F,1F,0F\);ResourceManager\.rtg\.renderPart\("Connector"\);GL11\.glRotatef\((-?\d+),0F,1F,0F\);\}|ResourceManager\.rtg\.renderPart\("Connector"\);)'


def parse_gui(code, spec):
    return {name: grab(code, pattern) for name, (pattern, _) in spec.items()}


def orig_connectors(code):
    found = {}
    pattern = r"Library\.canConnect\(te\.getWorldObj\(\),([^,]+),([^,]+),([^,]+),Library\.(\w+)\)\)" + CONNECTOR_TAIL
    for m in re.finditer(pattern, code):
        angle = int(m[6]) if m[6] is not None else 0
        restore = int(m[7]) if m[7] is not None else None
        found[m[4]] = ((m[1], m[2], m[3]), angle, restore)
    return found


def neo_connectors(code):
    found = {}
    pattern = (r"Library\.canConnect\(level,pos\.(\w+)\(\),Direction\.(\w+)\)\)(\{RenderContext\.mulPose\(Axis\.YP\.rotationDegrees\((-?\d+)F\)\);ResourceManager\.rtg\.renderPart\(\"Connector\"\);"
               r"RenderContext\.mulPose\(Axis\.YP\.rotationDegrees\((-?\d+)F\)\);\}|ResourceManager\.rtg\.renderPart\(\"Connector\"\);)")
    for m in re.finditer(pattern, code):
        found[m[2]] = (m[1], int(m[4]) if m[4] is not None else 0, int(m[5]) if m[5] is not None else None)
    return found


def orig_assembly_rows(text):
    """name -> dict(setup, output, inputs, ex) for the register statements in the original lines 155-160 and 295-296."""
    lines = lf(text).split("\n")
    rows = {}
    for first, last in ((155, 160), (295, 296)):
        block = "\n".join(lines[first - 1:last])
        for m in re.finditer(r'this\.register\(new GenericRecipe\("(ass\.\w+)"\)\.setup\((\d+), (\d+)\)\.outputItems\(new ItemStack\(([\w.]+), (\d+)\)\)\s*\.inputItems\((.*?)\)\);', block, re.S):
            body = m[6]
            inputs = [(k, e, int(n)) for k, e, n in re.findall(r"new (OreDictStack|ComparableStack)\(([\w.]+(?:\(\))?), (\d+)\)", body)]
            leftover = re.sub(r"new (?:OreDictStack|ComparableStack)\([\w.]+(?:\(\))?, \d+\)", "", body)
            rows[m[1]] = dict(setup=(int(m[2]), int(m[3])), output=(m[4], int(m[5])), inputs=inputs, ex="inputItemsEx" in m[0], clean=re.fullmatch(r"[\s,]*", leftover) is not None)
    return rows


# original ingredient -> (kind, name) in the NEO form
TRANSLATE = {("OreDictStack", "STEEL.plate()"): ("tag", "NtmTags.Items.PLATES_STEEL"), ("OreDictStack", "CU.plate()"): ("tag", "NtmTags.Items.PLATES_COPPER"),
             ("OreDictStack", "ANY_PLASTIC.ingot()"): ("tag", 'ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm","ingots_plastic"))'),
             ("OreDictStack", "PB.plateCast()"): ("cast", "LEAD"), ("OreDictStack", "MINGRADE.wireFine()"): ("item", "WIRE_RED_COPPER"),
             ("OreDictStack", "GOLD.wireFine()"): ("item", "WIRE_GOLD"), ("OreDictStack", "NETHERQUARTZ.dust()"): ("item", "POWDER_QUARTZ"),
             ("OreDictStack", "SI.billet()"): ("item", "BILLET_SILICON"), ("ComparableStack", "ModItems.thermo_element"): ("item", "THERMO_ELEMENT"),
             ("ComparableStack", "ModItems.rtg_unit"): ("item", "RTG_UNIT")}
OUT_TRANSLATE = {"ModItems.thermo_element": ("item", "THERMO_ELEMENT"), "ModItems.rtg_unit": ("item", "RTG_UNIT"), "ModBlocks.machine_rtg": ("block", "MACHINE_RTG")}
# the task book rows (GOAL23C C1), written as literals so a parser bug is caught: setup, output, inputs
TASK_ROWS = {
    "ass.thermoelement": ((60, 100), ("thermo_element", 1), [("OreDictStack", "STEEL.plate()", 1), ("OreDictStack", "MINGRADE.wireFine()", 2), ("OreDictStack", "NETHERQUARTZ.dust()", 2)]),
    "ass.thermoelementsilicon": ((60, 100), ("thermo_element", 1), [("OreDictStack", "STEEL.plate()", 1), ("OreDictStack", "GOLD.wireFine()", 2), ("OreDictStack", "SI.billet()", 1)]),
    "ass.rtgunit": ((100, 100), ("rtg_unit", 1), [("OreDictStack", "PB.plateCast()", 2), ("OreDictStack", "CU.plate()", 4), ("ComparableStack", "ModItems.thermo_element", 2)]),
    "ass.rtg": ((200, 100), ("machine_rtg", 1), [("ComparableStack", "ModItems.rtg_unit", 3), ("OreDictStack", "STEEL.plate()", 4), ("OreDictStack", "MINGRADE.wireFine()", 16),
                                                 ("OreDictStack", "ANY_PLASTIC.ingot()", 4)]),
}


def v1_original(ck, inp, st, facts=None):
    o = inp.o
    te = o["te"]
    tcode = whole(te)
    ck("V1.te-ctor-slots", mcode(te, "public TileEntityMachineRTG()") == "super(15);", "TileEntityMachineRTG() is super(15)")
    heat = grab(tcode, r"publicfinalintheatMax=VersatileConfig\.rtgDecay\(\)\?(\d+):(\d+);")
    ck("V1.te-heatmax", heat == (600, 200), "heatMax = VersatileConfig.rtgDecay() ? 600 : 200 (a final field in the original)", heat)
    ck("V1.te-powermax", grab(tcode, r"publicfinallongpowerMax=(\d+);") == (100000,), "powerMax = 100000")
    slot_io = re.search(r"slot_io=newint\[\]\{([\d,]+)\}", tcode)
    ck("V1.te-slot-io", slot_io is not None and [int(x) for x in slot_io[1].split(",")] == list(range(15)), "slot_io is 0..14", slot_io and slot_io[1])
    ck("V1.te-name", mcode(te, "public String getName()") == 'return"container.rtg";', 'getName returns "container.rtg"')
    ck("V1.te-nbt", mcode(te, "public void readFromNBT(NBTTagCompound nbt)") == 'super.readFromNBT(nbt);power=nbt.getLong("power");heat=nbt.getInteger("heat");'
       and mcode(te, "public void writeToNBT(NBTTagCompound nbt)") == 'super.writeToNBT(nbt);nbt.setLong("power",power);nbt.setInteger("heat",heat);',
       "NBT keys power (long) and heat (int), super first")
    update = mcode(te, "public void updateEntity()")
    ck("V1.te-update-order", update == "if(!worldObj.isRemote){this.setupPowerPorts(getPorts());this.updateAllPorts();this.providePower();heat=RTGUtil.updateRTGs(slots,slot_io);"
       "if(heat>heatMax)heat=heatMax;power+=heat*5;if(power>powerMax)power=powerMax;networkPackNT(50);}",
       "updateEntity (server): providePower() before heat = RTGUtil.updateRTGs, heat cap, power += heat * 5, power cap, networkPackNT(50) last", update)
    ck("V1.te-heat-times-5-and-pack-50", grab(update, r"power\+=heat\*(\d+);") == (5,) and grab(update, r"networkPackNT\((\d+)\)") == (50,), "the multiplier is 5 and the sync interval 50")
    ck("V1.te-serialize", mcode(te, "public void serialize(ByteBuf buf)") == "super.serialize(buf);buf.writeLong(power);"
       and mcode(te, "public void deserialize(ByteBuf buf)") == "super.deserialize(buf);power=buf.readLong();", "serialize writes only power (heat goes through the container)")
    ck("V1.te-automation", mcode(te, "public boolean canExtractItem(int i, ItemStack itemStack, int j)") == "returnfalse;" and "isItemValidForSlot" in tcode
       and not re.search(r"booleanisItemValidForSlot", tcode), "canExtractItem is false and there is no isItemValidForSlot override (insert goes through the base class)")
    ck("V1.te-scaled", mcode(te, "public long getPowerScaled(long i)") == "return(power*i)/powerMax;" and mcode(te, "public int getHeatScaled(int i)") == "return(heat*i)/heatMax;",
       "getPowerScaled and getHeatScaled are (value * i) / max")
    # container
    container = o["container"]
    slots = [tuple(int(x) for x in m) for m in re.findall(r"new Slot\(tedf, (\d+), (\d+), (\d+)\)", container)]
    ck("V1.container-slots", slots == [(i, 16 + 18 * (i % 5), 18 + 18 * (i // 5)) for i in range(15)], "ContainerMachineRTG has the 15 slots at (16 + 18*(i%5), 18 + 18*(i/5))", slots)
    ck("V1.container-player", "new Slot(invPlayer, j + i * 9 + 9, 8 + j * 18, 106 + i * 18)" in container and "new Slot(invPlayer, i, 8 + i * 18, 164)" in container,
       "player inventory at (8 + 18j, 106 + 18i), hotbar at (8 + 18i, 164)")
    # GUI
    gui = whole(o["gui"])
    parsed = parse_gui(gui, ORIG_GUI)
    bad = {k: (parsed[k], ORIG_GUI[k][1]) for k in ORIG_GUI if parsed[k] != ORIG_GUI[k][1]}
    ck("V1.gui-coordinates", not bad, "GUIMachineRTG: 176x188 gui_rtg.png, electricity (+146,+9,16,51), heat stat (+124,+9,16,51), pellet list (-12,+25,16,16) at (-8,+36+16) with heat*5, title 60/7/10925486, "
       "heat bar (124,61-i) from (176,10+(51-i)), power bar (146,61-i) from (192,10+(51-i)), scaled by 51, drawInfoPanel(-12,+25,16,16,2)", bad)
    ck("V1.gui-keys", all(f'"{k}"' in o["gui"] for k in ("desc.gui.rtg.heat", "desc.gui.rtg.pellets", "desc.gui.rtg.pelletPower")), "the GUI uses desc.gui.rtg.heat, .pellets and .pelletPower (pelletHeat is defined but unused)")
    # renderer
    render = whole(o["render"])
    ck("V1.render-body", "GL11.glRotatef(180,0F,1F,0F);bindTexture(ResourceManager.rtg_tex);ResourceManager.rtg.renderPart(\"Gen\");" in render, "RenderRTG rotates 180 degrees, binds rtg_tex and draws Gen")
    conn = orig_connectors(render)
    ck("V1.render-connectors", conn == ORIG_CONNECTORS, "Connector for POS_X (no turn), NEG_X (180), NEG_Z (90), POS_Z (-90), each restored by the inverse rotation", conn)
    # block
    mb = o["modblocks"].split("\n")
    ck("V1.block-line-1855", re.search(r'machine_rtg = new MachineRTG\(Material\.iron\)\.setBlockName\("machine_rtg_grey"\)\.setHardness\(5\.0F\)\.setResistance\(10\.0F\)\.setCreativeTab\(MainRegistry\.machineTab\)', mb[1854]) is not None,
       "ModBlocks.java:1855 is machine_rtg = MachineRTG(iron) named machine_rtg_grey, hardness 5.0, resistance 10.0, machine tab", mb[1854].strip())
    # assembly rows
    rows = orig_assembly_rows(o["asm"])
    bad = []
    for name, (setup, output, inputs) in TASK_ROWS.items():
        row = rows.get(name)
        if not row or row["setup"] != setup or row["output"] != (f"ModItems.{output[0]}" if output[0] != "machine_rtg" else "ModBlocks.machine_rtg", output[1]) or row["inputs"] != inputs or row["ex"] or not row["clean"]:
            bad.append((name, row))
    ck("V1.assembly-rows", not bad and sorted(rows) == sorted(TASK_ROWS), "AssemblyMachineRecipes.java:155-160,295-296 are the four task book rows (setup, output, inputs with shapes and counts; ass.rtg has no inputItemsEx)", bad)
    # mineral and items
    mr = o["mineral"].split("\n")
    ck("V1.mercury-recipe", re.search(r"addShapelessRecipe\(new ItemStack\(ModItems\.ingot_mercury, 2\), new Object\[\] \{ new ItemStack\(ModItems\.pellet_rtg_depleted, 1, DepletedRTGMaterial\.MERCURY\.ordinal\(\)\) \}\);", mr[218]) is not None,
       "MineralRecipes.java:219 recycles the MERCURY depleted pellet into 2 ingot_mercury", mr[218].strip())
    mi = o["moditems"].split("\n")
    ck("V1.ingot-mercury-is-nugget-mercury", 'ingot_mercury = new ItemCustomLore().setUnlocalizedName("nugget_mercury")' in mi[2281] and 'nugget_mercury = new Item().setUnlocalizedName("nugget_mercury_tiny")' in mi[2280],
       "ModItems.java:2281-2282: ingot_mercury is registered under the name nugget_mercury (NEO NUGGET_MERCURY), nugget_mercury under nugget_mercury_tiny", (mi[2280].strip(), mi[2281].strip()))
    # language
    bad = {}
    for neo_key, o_key, en_line, zh_line in LANG:
        en_row, zh_row = inp.o_en_lines[en_line - 1], inp.o_zh_lines[zh_line - 1]
        if not en_row.startswith(o_key + "=") or not zh_row.startswith(o_key + "="):
            bad[neo_key] = (en_row, zh_row)
            continue
        want = EXPECT_LANG[neo_key]
        if (en_row.split("=", 1)[1].rstrip("\r"), zh_row.split("=", 1)[1].rstrip("\r")) != want:
            bad[neo_key] = (en_row, zh_row)
    ck("V1.lang-lines", not bad, "en_US.lang:808,989-992,4437,4655,5907 and zh_CN.lang:646,807-810,3869,4062,5080 carry the eight keys with the task book text", bad)
    if facts is not None:
        facts["V1"] = dict(heat_max=heat, assembly_rows={k: dict(setup=v["setup"], output=v["output"], inputs=v["inputs"]) for k, v in rows.items()},
                           note_original_automation="the original getAccessibleSlotsFromSide returns slot_io and canInsertItem defers to isItemValidForSlot (base class: false), so insertion is closed; NEO's empty getSlotsForFace is the same closed behaviour")
        inp.orig_rows = rows
        inp.orig_connectors = conn


# ---------------------------------------------------------------- V2

def v2_block_entity(ck, inp, st, facts=None):
    t = st.text(BEP)
    code = whole(t)
    ck("V2.ctor", mcode(t, "public MachineRTGBlockEntity(BlockPos pos, BlockState state)") == "super(NtmBlockEntityTypes.MACHINE_RTG.get(),pos,state,15);" and grab(code, r"publicclassMachineRTGBlockEntityextendsMachineBaseBlockEntityimplementsIEnergyProviderMK2\{") == (),
       "MachineRTGBlockEntity extends MachineBaseBlockEntity implements IEnergyProviderMK2 and calls super(MACHINE_RTG type, pos, state, 15) like super(15)")
    ck("V2.max-power", grab(code, r"publicstaticfinallongMAX_POWER=(\d+(?:_\d+)*)L;") is not None and int(re.search(r"MAX_POWER=([\d_]+)L;", code)[1].replace("_", "")) == 100000
       and "100_000L" in t, "MAX_POWER = 100_000L (the original powerMax = 100000)")
    hm = grab(mcode(t, "public static int getHeatMax()"), r"returnRTGUtil\.rtgDecay\(\)\?(\d+):(\d+);")
    ck("V2.heat-max-runtime", hm == (600, 200) and "publicstaticintgetHeatMax()" in code and not re.search(r"static\s+final\s+int\s+\w*[hH]eat\w*\s*=", blank_comments(t)),
       "getHeatMax() reads RTGUtil.rtgDecay() ? 600 : 200 at run time (a method, not a static final field)", hm)
    update = mcode(t, "public void updateEntity()")
    ck("V2.update-client-return", update.startswith("if(this.level==null||this.level.isClientSide)return;"), "updateEntity returns on the client (and without a level)")
    i_provide, i_update = update.find("this.tryProvide("), update.find("RTGUtil.updateRTGs(this.slots,SLOT_IO)")
    ck("V2.provide-before-update", 0 <= i_provide < i_update and "for(DirPospos:this.getConPos())this.tryProvide(this.level,pos.makeCompat(),pos.getDir());" in update,
       "tryProvide for the getConPos() positions runs BEFORE RTGUtil.updateRTGs(slots, SLOT_IO) (the original provides first)", (i_provide, i_update))
    conpos = mcode(t, "public DirPos[] getConPos()")
    ck("V2.six-positions", "Direction[]directions=Direction.values();" in conpos and "this.worldPosition.relative(directions[i])" in conpos and "newDirPos(this.worldPosition.relative(directions[i]),directions[i])" in conpos
       and len(__import__("re").findall(r"\w+", "NORTH SOUTH EAST WEST UP DOWN")) == 6, "getConPos covers Direction.values() (six sides) with the neighbour position and its direction")
    order = [update.find(x) for x in ("this.heat=RTGUtil.updateRTGs(this.slots,SLOT_IO);", "if(this.heat>getHeatMax())this.heat=getHeatMax();", "this.power+=(long)this.heat*5L;",
                                     "if(this.power>MAX_POWER)this.power=MAX_POWER;", "this.setChanged();", "this.networkPackNT(50);")]
    ck("V2.update-order", all(x >= 0 for x in order) and order == sorted(order), "heat from updateRTGs, heat cap at getHeatMax(), power += heat * 5, power cap at MAX_POWER, setChanged, networkPackNT in that order", order)
    ck("V2.update-constants", grab(update, r"this\.power\+=\(long\)this\.heat\*(\d+)L;") == (5,) and grab(update, r"networkPackNT\((\d+)\);$") == (50,) and update.endswith("this.networkPackNT(50);"),
       "the multiplier is 5 and networkPackNT(50) is the last statement")
    ck("V2.set-changed-condition", "booleandecays=RTGUtil.rtgDecay()&&RTGUtil.hasHeat(this.slots,SLOT_IO);" in update
       and "if(decays||this.power!=previousPower||this.heat!=previousHeat)this.setChanged();" in update, "setChanged() is called when a pellet decays or power/heat change")
    ck("V2.heat-scaled", mcode(t, "public int getHeatScaled(int i)") == "returnthis.heat*i/getHeatMax();" and mcode(t, "public long getPowerScaled(long i)") == "returnthis.power*i/MAX_POWER;",
       "getHeatScaled / getPowerScaled are integer value * i / max")
    ck("V2.can-place", mcode(t, "public boolean canPlaceItem(int slot, ItemStack stack)") == "returnslot>=0&&slot<15&&stack.getItem()instanceofRTGPelletItem;",
       "canPlaceItem accepts only RTGPelletItem in slots 0..14")
    ck("V2.slot-io", re.search(r"SLOT_IO=\{([\d,]+)\}", code) is not None and [int(x) for x in re.search(r"SLOT_IO=\{([\d,]+)\}", code)[1].split(",")] == list(range(15)), "SLOT_IO is 0..14")
    ck("V2.stack-size-one", mcode(t, "public int getMaxStackSize()") == "return1;", "getMaxStackSize() is 1")
    ck("V2.automation-closed", mcode(t, "public int[] getSlotsForFace(Direction direction)") == "returnNO_SLOTS;" and "NO_SLOTS=newint[0]" in code
       and mcode(t, "public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction)") == "returnfalse;"
       and mcode(t, "public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction)") == "returnfalse;", "getSlotsForFace is empty; canPlaceItemThroughFace and canTakeItemThroughFace are false")
    load = mcode(t, "protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    save = mcode(t, "protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries)")
    ck("V2.nbt", load == 'super.loadAdditional(tag,registries);this.power=Math.max(0L,Math.min(MAX_POWER,tag.getLong("power")));this.heat=tag.getInt("heat");'
       and save == 'super.saveAdditional(tag,registries);tag.putLong("power",this.power);tag.putInt("heat",this.heat);',
       "NBT: power (putLong/getLong, clamped to [0, MAX_POWER] on load) and heat (putInt/getInt), super first (same keys as the original's power/heat)", (load, save))
    ser = mcode(t, "public void serialize(RegistryFriendlyByteBuf buf)")
    de = mcode(t, "public void deserialize(RegistryFriendlyByteBuf buf)")
    ck("V2.sync-symmetric", ser == "super.serialize(buf);buf.writeLong(this.power);buf.writeInt(this.heat);" and de == "super.deserialize(buf);this.power=buf.readLong();this.heat=buf.readInt();",
       "serialize/deserialize are symmetric: super, long power, int heat", (ser, de))
    ck("V2.default-name", mcode(t, "protected Component getDefaultName()") == 'returnComponent.translatable("container.rtg");', 'getDefaultName is the translatable "container.rtg"')
    ck("V2.no-provider-speed-override", "getProviderSpeed" not in code, "no getProviderSpeed override (the interface default applies)")
    ck("V2.provider-unsubscribe", mcode(t, "private void removeNetworkSubscriptions()") == "if(this.level==null||this.level.isClientSide)return;for(NodeNetnet:newArrayList<>(UniNodespace.activeNodeNets)){if(netinstanceofPowerNetMK2powerNet)powerNet.removeProvider(this);}"
       and mcode(t, "public void onChunkUnloaded()") == "this.removeNetworkSubscriptions();super.onChunkUnloaded();" and mcode(t, "public void setRemoved()") == "this.removeNetworkSubscriptions();super.setRemoved();",
       "the provider is removed from every PowerNetMK2 in onChunkUnloaded and setRemoved")
    ck("V2.power-accessors", mcode(t, "public long getPower()") == "returnthis.power;" and mcode(t, "public long getMaxPower()") == "returnMAX_POWER;"
       and "longbounded=Math.max(0L,Math.min(MAX_POWER,power));" in mcode(t, "public void setPower(long power)"), "getPower, getMaxPower and the bounded setPower")
    ck("V2.has-heat-power", mcode(t, "public boolean hasHeat()") == "returnRTGUtil.hasHeat(this.slots,SLOT_IO);" and mcode(t, "public boolean hasPower()") == "returnthis.power>0;", "hasHeat is any pellet slot (RTGUtil.hasHeat), hasPower is power > 0")
    ck("V2.create-menu", mcode(t, "public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player)") == "returnnewMachineRTGMenu(id,inventory,this);", "createMenu returns MachineRTGMenu")
    ck("V2.eol-lf", eol_of(t) == "" and "\r" not in t, "MachineRTGBlockEntity.java has LF line endings")


# ---------------------------------------------------------------- V3

def v3_block_menu_screen_renderer(ck, inp, st, facts=None):
    blk = st.text(BLK)
    bcode = whole(blk)
    ck("V3.block-no-state", not re.search(r"createBlockStateDefinition|IntegerProperty|BooleanProperty|DirectionProperty|EnumProperty|BlockStateProperties|HorizontalDirectionalBlock|registerDefaultState|FACING", bcode)
       and "publicclassMachineRTGBlockextendsBaseEntityBlockimplementsICustomBlockModelRegister" in bcode, "MachineRTGBlock has no block-state property or facing (the original has none)")
    ck("V3.block-on-remove", mcode(blk, "public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean movedByPiston)")
       == "if(!state.is(newState.getBlock())&&level.getBlockEntity(pos)instanceofMachineRTGBlockEntityrtg){Containers.dropContents(level,pos,rtg);}super.onRemove(state,level,pos,newState,movedByPiston);",
       "onRemove drops the 15 slots (Containers.dropContents) when the block is replaced, then calls super (original breakBlock)")
    ck("V3.block-ticker", mcode(blk, "public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type)")
       == "return(lvl,pos,st,be)->{if(beinstanceofITickabletickable)tickable.updateEntity();};" and "returnnewMachineRTGBlockEntity(pos,state);" in bcode, "the block has a ticker that calls updateEntity and creates MachineRTGBlockEntity")
    ck("V3.block-use", "player.openMenu(newSimpleMenuProvider(menu,menu.getDisplayName()),pos);" in bcode and "RenderShape.MODEL" in bcode, "right click opens the menu, render shape MODEL")
    ck("V3.block-register-model", mcode(blk, "public void registerModel(BlockStateProvider provider, ResourceLocation modelLocation)")
       == 'provider.simpleBlock(this,provider.models().getBuilder(modelLocation.getPath()+"_particle").texture("particle",NuclearTechMod.withDefaultNamespace("block/block_steel")));'
          'provider.itemModels().getBuilder(modelLocation.getPath()).parent(newModelFile.UncheckedModelFile("builtin/entity"));', "registerModel is the particle-only block model plus the builtin/entity item model")
    # menu
    menu = st.text(MENU)
    mc = mcode(menu, "public MachineRTGMenu(int id, Inventory inventory, MachineRTGBlockEntity be)")
    slots_call = grab(mc, r"this\.addSlots\(be,(\d+),(\d+),(\d+),(\d+),(\d+)\);")
    player_call = grab(mc, r"this\.playerInv\(inventory,(\d+),(\d+),(\d+)\);")
    base = st.text(MENUBASE)
    base_ok = ("this.addSlots(container, from, x, y, rows, cols, 18);" in base and "col + row * cols + from, x + col * slotSize, y + row * slotSize" in base
               and "x + y * 9 + 9, playerInvX + x * 18, playerInvY + y * 18" in base and "new SlotNonRetarded(inventory, x, playerInvX + x * 18, playerHotbarY)" in base)
    ck("V3.menu-calls", slots_call == (0, 16, 18, 3, 5) and player_call == (8, 106, 164) and base_ok,
       "MachineRTGMenu is addSlots(be, 0, 16, 18, 3, 5) and playerInv(inventory, 8, 106, 164) over MenuBase's 18-pixel helpers", (slots_call, player_call, base_ok))
    if slots_call and player_call and base_ok:
        frm, x, y, rows, cols = slots_call
        neo_slots = [(frm + c + r * cols, x + c * 18, y + r * 18) for r in range(rows) for c in range(cols)]
        px, py, hy = player_call
        neo_player = [(c + r * 9 + 9, px + c * 18, py + r * 18) for r in range(3) for c in range(9)] + [(c, px + c * 18, hy) for c in range(9)]
        orig_slots = [(i, 16 + 18 * (i % 5), 18 + 18 * (i // 5)) for i in range(15)]
        orig_player = [(j + i * 9 + 9, 8 + j * 18, 106 + i * 18) for i in range(3) for j in range(9)] + [(i, 8 + i * 18, 164) for i in range(9)]
        # the original rows are validated against these formulas in V1.container-*
        ck("V3.menu-slots-equal-original", neo_slots == orig_slots and neo_player == orig_player, "the 15 machine slots and the 36 player slots derived from the NEO calls equal the original container coordinates")
    else:
        ck("V3.menu-slots-equal-original", False, "the menu slot calls could not be derived")
    ck("V3.menu-quick-move", "quickMoveStack" not in blank_comments(menu) and "extends MenuBase<MachineRTGBlockEntity>" in menu and "public ItemStack quickMoveStack" in base,
       "MachineRTGMenu inherits MenuBase.quickMoveStack (it does not override it)")
    # screen
    scr = st.text(SCR)
    # The heat bar is clamped to its slot (the server's heat cap can differ from the client config); the clamp is checked on its own below.
    clamp = "inti=Math.min(51,this.be.getHeatScaled(51));"
    parsed = parse_gui(whole(scr).replace(clamp, "inti=this.be.getHeatScaled(51);"), NEO_GUI)
    ck("V3.screen-heat-clamp", whole(scr).count(clamp) == 1, "the heat bar height is Math.min(51, getHeatScaled(51)) (NEO-only clamp to the 51-pixel slot; the original has no clamp)")
    bad = {k: (parsed[k], NEO_GUI[k][1]) for k in NEO_GUI if parsed[k] != NEO_GUI[k][1]}
    ck("V3.screen-coordinates", not bad, "MachineRTGScreen: 176x188 gui_rtg.png, electricity (+146,+9,16,51), heat stat (+124,+9,16,51), pellet list (-12,+25,16,16) at (-8,+36+16) with heat*5, title 60/7/10925486, "
       "inventory label (8, imageHeight-96+2), bars from (176/192, 10+(51-i)) at (124/146, 61-i), scaled by 51, drawInfoPanel(-12,+25,2)", bad)
    ck("V3.screen-background", "guiGraphics.blit(TEXTURE,this.leftPos,this.topPos,0,0,this.imageWidth,this.imageHeight,256,256);" in whole(scr) and "extendsInfoScreen<MachineRTGMenu>" in whole(scr), "the background blits gui_rtg.png over the whole image; the screen extends InfoScreen")
    o_parsed = parse_gui(whole(inp.o["gui"]), ORIG_GUI)
    cross = {}
    for k in ("size", "electricity", "heat_stat", "pellet_panel", "pellet_scale", "title", "inventory_label", "heat_bar", "power_bar"):
        if o_parsed[k] != parsed[k]:
            cross[k] = (o_parsed[k], parsed[k])
    for k in ("info_panel",):
        if o_parsed[k] is None or parsed[k] is None or (o_parsed[k][0], o_parsed[k][1], o_parsed[k][4]) != (parsed[k][0], parsed[k][1], parsed[k][2]):
            cross[k] = (o_parsed[k], parsed[k])
    ck("V3.screen-equals-original", not cross and "pellet.getHeat()*5" in whole(scr), "every parsed screen coordinate equals the parsed original GUI value", cross)
    ck("V3.screen-pellet-list", "for(RTGPelletItempellet:RTGPelletItem.PELLETS)" in whole(scr) and 'Component.translatable("desc.gui.rtg.pelletPower",pellet.getDescription(),pellet.getHeat()*5)' in whole(scr),
       "the pellet list is built over RTGPelletItem.PELLETS with the pellet name and getHeat() * 5")
    # renderer
    ren = st.text(REN)
    rcode = whole(ren)
    body = mcode(ren, "public void render(MachineRTGBlockEntity be, MultiBufferSource buffer, float partialTicks)")
    ck("V3.render-body", body.startswith("RenderContext.translate(0.5F,0F,0.5F);RenderContext.mulPose(Axis.YP.rotationDegrees(180F));this.bindTexture(ResourceManager.RTG_TEX);ResourceManager.rtg.renderPart(\"Gen\");"),
       "RenderRTG centres, rotates 180 degrees, binds RTG_TEX and draws Gen first")
    conn = neo_connectors(body)
    ck("V3.render-connectors", conn == NEO_CONNECTORS and body.count('renderPart("Connector")') == 4, "Connector for EAST (no turn), WEST (180), NORTH (90), SOUTH (-90), each restored, guarded by Library.canConnect(level, pos.<dir>(), Direction.<DIR>)", conn)
    orig = getattr(inp, "orig_connectors", None)
    if orig is None:
        orig = orig_connectors(whole(inp.o["render"]))
    ck("V3.render-equals-original", {ORIG_TO_NEO_DIR[k]: (v[1], v[2]) for k, v in orig.items()} == {k: (v[1], v[2]) for k, v in conn.items()}, "the four connector angles equal the original's per direction (POS_X=EAST, NEG_X=WEST, NEG_Z=NORTH, POS_Z=SOUTH)")
    item = rcode[rcode.find("publicBlockEntityWithoutLevelRenderergetRenderer()"):]
    ck("V3.render-item", item and 'ResourceManager.rtg.renderPart("Gen");' in item and "Connector" not in item and "getItemForRenderer(){returnNtmBlocks.MACHINE_RTG.asItem();}" in rcode,
       "the item renderer draws Gen only (the original RenderRTGBlock) and is registered for machine_rtg")
    # ResourceManager
    rm = st.text(RM)
    rmc = whole(rm)
    ck("V3.resource-manager", rmc.count('rtg=newHFRWavefrontObject("models/obj/machines/rtg.obj").asVBO();') == 1 and "publicstaticIModelCustomrtg;" in rmc
       and rmc.count('RTG_TEX=NuclearTechMod.withDefaultNamespace("textures/models/machines/rtg.png");') == 1,
       "ResourceManager.rtg loads models/obj/machines/rtg.obj and RTG_TEX is textures/models/machines/rtg.png (each once)")
    ck("V3.eol-lf", all(eol_of(st.text(p)) == "" and "\r" not in st.text(p) for p in NEW_CLASSES), "the five new classes have LF line endings")


# ---------------------------------------------------------------- V4

def count(text, needle):
    return blank_comments(lf(text)).count(needle)


def tab_sections(text):
    code = lf(text)
    marks = [(m.start(), m[1]) for m in re.finditer(r"public static final Supplier<CreativeModeTab> (\w+) = CREATIVE_MODE_TABS\.register\(", code)]
    out = {}
    for n, (pos, name) in enumerate(marks):
        out[name] = code[pos:marks[n + 1][0] if n + 1 < len(marks) else len(code)]
    return out


def v4_registration(ck, inp, st, facts=None):
    nb = st.text(NB)
    line = [l for l in lf(nb).split("\n") if 'MACHINE_RTG = register("machine_rtg"' in l]
    ck("V4.block", len(line) == 1 and count(nb, '"machine_rtg"') == 1 and count(nb, "MACHINE_RTG =") == 1 and "new MachineRTGBlock(BlockBehaviour.Properties.of()" in line[0]
       and grab(line[0], r"\.strength\((\d+\.\d+)F, (\d+\.\d+)F\)") == ("5.0", "10.0") and ".requiresCorrectToolForDrops()" in line[0] and ".noOcclusion()" in line[0],
       'NtmBlocks.MACHINE_RTG is registered once as "machine_rtg" (MachineRTGBlock, strength 5.0F/10.0F, requiresCorrectToolForDrops, noOcclusion; original hardness 5, resistance 10)', line)
    nbet = st.text(NBET)
    ck("V4.block-entity-type", count(nbet, '"machine_rtg"') == 1 and count(nbet, "MACHINE_RTG =") == 1 and whole(nbet).count("MACHINE_RTG=BLOCK_ENTITY_TYPES.register(\"machine_rtg\",()->BlockEntityType.Builder.of(MachineRTGBlockEntity::new,NtmBlocks.MACHINE_RTG.get()).build(null));") == 1,
       "NtmBlockEntityTypes.MACHINE_RTG is registered once for MachineRTGBlockEntity on the machine_rtg block")
    nmt = st.text(NMT)
    ck("V4.menu-type", count(nmt, '"machine_rtg"') == 1 and whole(nmt).count('MACHINE_RTG=reg("machine_rtg",MachineRTGMenu::new);') == 1, "NtmMenuTypes.MACHINE_RTG is registered once")
    nmc = st.text(NMC)
    ck("V4.screen", count(nmc, "MachineRTGScreen::new") == 1 and whole(nmc).count("event.register(NtmMenuTypes.MACHINE_RTG.get(),MachineRTGScreen::new);") == 1
       and count(nmc, "import com.hbm.inventory.screens.MachineRTGScreen;") == 1, "NuclearTechModClient registers MachineRTGScreen for the menu once (and imports it once)")
    cp = st.text(CP)
    ck("V4.renderer", count(cp, "new RenderRTG()") == 1 and whole(cp).count("BlockEntityRenderers.register(NtmBlockEntityTypes.MACHINE_RTG.get(),newRenderRTG());") == 1,
       "ClientProxy registers RenderRTG for the block entity type once")
    ni = st.text(NI)
    ck("V4.items", count(ni, 'ITEMS.register("thermo_element"') == 1 and count(ni, 'ITEMS.register("rtg_unit"') == 1
       and whole(ni).count('THERMO_ELEMENT=ITEMS.register("thermo_element",()->newItem(newItem.Properties()));') == 1 and whole(ni).count('RTG_UNIT=ITEMS.register("rtg_unit",()->newItem(newItem.Properties()));') == 1,
       "NtmItems registers THERMO_ELEMENT and RTG_UNIT once each as plain Item")
    mp = st.text(MP)
    ck("V4.item-models", count(mp, "this.basicItem(NtmItems.THERMO_ELEMENT.get());") == 1 and count(mp, "this.basicItem(NtmItems.RTG_UNIT.get());") == 1, "NtmItemModelProvider has one basicItem for each of the two items")
    tabs = tab_sections(st.text(CT))
    ct = st.text(CT)
    machine = [l.strip() for l in tabs.get("MACHINE", "").split("\n")]
    idx = machine.index("output.accept(NtmBlocks.MACHINE_DIESEL);") if "output.accept(NtmBlocks.MACHINE_DIESEL);" in machine else -1
    ck("V4.creative-tabs", count(ct, "NtmBlocks.MACHINE_RTG") == 1 and count(ct, "NtmItems.RTG_UNIT") == 1 and count(ct, "NtmItems.THERMO_ELEMENT") == 1
       and idx >= 0 and machine[idx + 1] == "output.accept(NtmBlocks.MACHINE_RTG);" and count(tabs.get("PARTS", ""), "output.accept(NtmItems.RTG_UNIT.get());") == 1
       and count(tabs.get("CONTROL", ""), "output.accept(NtmItems.THERMO_ELEMENT);") == 1,
       "creative tabs: MACHINE_RTG right after MACHINE_DIESEL in MACHINE, RTG_UNIT in PARTS, THERMO_ELEMENT in CONTROL, one reference each", (idx, sorted(tabs)))
    ck("V4.loot-provider", count(st.text(LOOT), "this.dropSelf(NtmBlocks.MACHINE_RTG.get());") == 1 and count(st.text(LOOT), "MACHINE_RTG") == 1, "NtmBlockLootTableProvider has one dropSelf for the block")
    ck("V4.tag-provider", count(st.text(TAG), "NtmBlocks.MACHINE_RTG.get(),") == 1 and count(st.text(TAG), "MACHINE_RTG") == 1, "NtmBlockTagProvider lists the block once")
    # generated resources
    tag = json.loads(st.text(G_TAG)) if st.has(G_TAG) else {}
    ck("V4.generated-tag", tag.get("values", []).count("hbmsntm:machine_rtg") == 1 and tag.get("values", []).count("hbmsntm:machine_diesel") == 1, "the generated mineable/pickaxe tag lists hbmsntm:machine_rtg once")
    ck("V4.generated-json", st.has(G_STATE) and jload(st, G_STATE) == {"variants": {"": {"model": "hbmsntm:block/machine_rtg_particle"}}} and jload(st, G_BMODEL) == {"textures": {"particle": "hbmsntm:block/block_steel"}}
       and jload(st, G_IM_RTG) == {"parent": "minecraft:builtin/entity"} and jload(st, G_IM_TE) == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/thermo_element"}}
       and jload(st, G_IM_RU) == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/rtg_unit"}},
       "the generated blockstate, particle model and the three item models have the expected content")
    loot = jload(st, G_LOOT) if st.has(G_LOOT) else {}
    pool = (loot.get("pools") or [{}])[0]
    ck("V4.generated-loot", loot.get("type") == "minecraft:block" and len(loot.get("pools", [])) == 1 and pool.get("rolls") == 1.0 and pool.get("entries") == [{"type": "minecraft:item", "name": "hbmsntm:machine_rtg"}]
       and pool.get("conditions") == [{"condition": "minecraft:survives_explosion"}], "the generated loot table drops hbmsntm:machine_rtg (survives_explosion)", loot)
    # client isolation
    allowed = lambda p: p in (J + "main/NuclearTechModClient.java", J + "main/ClientProxy.java") or p.startswith(J + "render/") or p.startswith(J + "inventory/screens/")  # noqa: E731
    leaks = {p: hit for p, hit in st.refs.items() if not allowed(p) and p != RM and any(k in hit for k in REF_PATTERNS)}
    ck("V4.client-isolation", not leaks, "MachineRTGScreen, RenderRTG and ResourceManager.rtg/RTG_TEX are referenced only from main/NuclearTechModClient.java, main/ClientProxy.java, render/ and inventory/screens/ (and ResourceManager itself)", leaks)
    ck("V4.client-refs-present", set(k for p, h in st.refs.items() for k in h) >= set(REF_PATTERNS), "the scan found the three client references (the scan itself works)", sorted(st.refs)[:5])
    if facts is not None:
        facts["V4"] = dict(client_reference_files={p: h for p, h in sorted(st.refs.items()) if any(k in h for k in REF_PATTERNS)})


# ---------------------------------------------------------------- V5

def neo_assembly_statements(text):
    """(name, norm statement text) of every `this.register(new GenericRecipe("ass.*")...)` in registerDefaults with its brace depth below the method."""
    text = lf(text)
    code = blank_comments(text)
    open_index, _, _ = method_span(text, "public void registerDefaults()")
    out = []
    for m in re.finditer(r'this\.register\(new GenericRecipe\("(ass\.\w+)"\)', code):
        close = match_paren(code, code.index("(", m.start()))
        before = code[:m.start()].rstrip()
        depth = brace_depth(code, open_index, m.start())
        out.append((m[1], norm(code[m.start():close + 1]), depth if before[-1:] in (";", "{", "}") else -1))
    return out


def parse_neo_row(statement):
    m = re.match(r'this\.register\(new GenericRecipe\("(ass\.\w+)"\)\.setup\((\d+), (\d+)\)\.outputItems\(new ItemStack\(Ntm(Items|Blocks)\.(\w+)\.get\(\), (\d+)\)\)\s*\.inputItems\((.*)\)\)$', statement)
    if not m:
        raise ValueError(f"unparsable statement {statement!r}")
    inputs = []
    for arg in split_top(m[7]):
        a = re.sub(r"\s+", "", arg)
        if (g := re.fullmatch(r"newRecipesCommon\.TagStack\((.*),(\d+)\)", a)):
            inputs.append(("tag", g[1], int(g[2])))
        elif (g := re.fullmatch(r"newComparableStack\(NtmItems\.(\w+)\.get\(\),(\d+)\)", a)):
            inputs.append(("item", g[1], int(g[2])))
        elif (g := re.fullmatch(r"NtmItems\.castPlateIngredient\(CastPlateItem\.Type\.(\w+),(\d+)\)", a)):
            inputs.append(("cast", g[1], int(g[2])))
        else:
            inputs.append(("?", a, 0))
    return dict(name=m[1], setup=(int(m[2]), int(m[3])), output=("item" if m[4] == "Items" else "block", m[5], int(m[6])), inputs=inputs)


def v5_assembly(ck, inp, st, facts=None):
    live = neo_assembly_statements(st.text(AMR))
    start = neo_assembly_statements(inp.start[AMR])
    by_name = collections.defaultdict(list)
    for name, statement, depth in live:
        by_name[name].append((statement, depth))
    rows = getattr(inp, "orig_rows", None) or orig_assembly_rows(inp.o["asm"])
    bad = []
    parsed = {}
    for name, (setup, output, inputs) in TASK_ROWS.items():
        if len(by_name.get(name, [])) != 1:
            bad.append((name, "registered", len(by_name.get(name, []))))
            continue
        row = parse_neo_row(by_name[name][0][0])
        parsed[name] = row
        orow = rows[name]
        want_inputs = []
        for kind, expr, n in orow["inputs"]:
            t = TRANSLATE[(kind, expr)]
            want_inputs.append((t[0], t[1], n))
        want_out = OUT_TRANSLATE[orow["output"][0]]
        if row["setup"] != orow["setup"] or row["output"] != (want_out[0], want_out[1], orow["output"][1]) or row["inputs"] != want_inputs:
            bad.append((name, row, want_inputs))
    ck("V5.rows-equal-translated-original", not bad, "the four NEO rows equal the original rows through the translation table (setup, output, ingredient kind, item/tag, count, order)", bad)
    ck("V5.rows-equal-task-book", all(name in parsed and parsed[name]["setup"] == TASK_ROWS[name][0] and parsed[name]["output"][2] == TASK_ROWS[name][1][1]
                                      and [i[2] for i in parsed[name]["inputs"]] == [i[2] for i in TASK_ROWS[name][2]] for name in TASK_ROWS), "setups (60/100, 60/100, 100/100, 200/100), output counts and ingredient counts equal the task book literals", parsed)
    ck("V5.no-enable528-condition", all(len(by_name.get(n, [])) == 1 and by_name[n][0][1] == 1 for n in TASK_ROWS), "the four rows are registered directly in registerDefaults, outside any enable528 / if block",
       {n: [d for _, d in by_name.get(n, [])] for n in TASK_ROWS})
    start_counter = collections.Counter((n, s) for n, s, _ in start)
    live_counter = collections.Counter((n, s) for n, s, _ in live)
    new = live_counter - start_counter
    ck("V5.existing-rows-unchanged", not (start_counter - live_counter) and sorted(n for n, _ in new.elements()) == sorted(TASK_ROWS), "every pre-existing ass.* row of the start copy is present and textually unchanged; the only new ones are the four",
       dict(removed=list((start_counter - live_counter).elements())[:3], added=sorted(n for n, _ in new.elements())))
    text = st.text(AMR)
    ck("V5.no-ex-inputs", all("inputItemsEx" not in s for n, s, _ in live if n in TASK_ROWS), "the four rows have no inputItemsEx (the original has none either)")
    ck("V5.result-items", "NtmItems.THERMO_ELEMENT" in text and "NtmBlocks.MACHINE_RTG.get()" in text and "NtmItems.RTG_UNIT" in text, "the rows use the NEO objects for thermo_element, rtg_unit and machine_rtg")
    if facts is not None:
        facts["V5"] = dict(neo_rows=parsed)


# ---------------------------------------------------------------- V6

def v6_leftovers(ck, inp, st, facts=None):
    rp = st.text(RP)
    start = inp.start[RP]
    sig = "private void registerRTGPelletRecipes(RecipeOutput recipeOutput)"
    code = method_code(rp, sig)
    rows = re.findall(r"addRTGRecyclingRecipe\(recipeOutput, DepletedRTGMaterial\.(\w+), NtmItems\.(\w+)\.get\(\), (\d+)\);", code)
    ck("V6.provider-rows", rows == [("BISMUTH", "BILLET_BISMUTH", "3"), ("LEAD", "INGOT_LEAD", "2"), ("MERCURY", "NUGGET_MERCURY", "2"), ("NEPTUNIUM", "BILLET_NEPTUNIUM", "3"), ("ZIRCONIUM", "BILLET_ZIRCONIUM", "3")],
       "the provider's recycling rows are BISMUTH 3 billet_bismuth, LEAD 2 ingot_lead, MERCURY 2 nugget_mercury (the original's ingot_mercury), NEPTUNIUM 3, ZIRCONIUM 3", rows)
    ck("V6.provider-no-nickel", "NICKEL" not in code and "NICKEL" not in blank_comments(rp), "the provider still registers no NICKEL recycling row (the original's :222-226 row needs another mod's ingotNickel)")
    merc = "addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.MERCURY, NtmItems.NUGGET_MERCURY.get(), 2);"
    ck("V6.provider-23b-rows-unchanged", norm(method_code(start, sig)) == norm(code.replace(merc, "", 1)).replace("  ", " ") or squash(method_code(start, sig)) == squash(code.replace(merc, "", 1)),
       "the ten pellet rows and the four 23B recycling rows are unchanged (the method equals the start copy plus the mercury row)")
    ck("V6.nugget-mercury", 'ITEMS.register("nugget_mercury"' in st.text(NI) if st.has(NI) else False, "NEO's NUGGET_MERCURY is the item registered as nugget_mercury (the original's ingot_mercury)")
    rec = jload(st, G_REC) if st.has(G_REC) else {}
    want = {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"type": "neoforge:components", "components": {"hbmsntm:meta": 1}, "items": "hbmsntm:pellet_rtg_depleted"}],
            "result": {"count": 2, "id": "hbmsntm:nugget_mercury"}}
    ck("V6.generated-recipe", rec == want, "pellet_rtg_depleted_mercury.json is shapeless: one neoforge:components ingredient (hbmsntm:meta 1 on pellet_rtg_depleted, not strict), result 2 hbmsntm:nugget_mercury", rec)
    lead = jload(st, RECIPES + "pellet_rtg_depleted_lead.json") if st.has(RECIPES + "pellet_rtg_depleted_lead.json") else {}
    ck("V6.recipe-shape-like-siblings", lead and set(rec.get("ingredients", [{}])[0]) == set(lead["ingredients"][0]) and rec.get("type") == lead.get("type"), "the mercury recipe has the same ingredient shape as the 23B lead recycling recipe")
    adv = jload(st, G_ADV) if st.has(G_ADV) else {}
    ck("V6.generated-advancement", adv.get("rewards", {}).get("recipes") == ["hbmsntm:pellet_rtg_depleted_mercury"] and "has_pellet_rtg_depleted" in adv.get("criteria", {}), "the recipe advancement rewards hbmsntm:pellet_rtg_depleted_mercury")
    nickel = sorted(p for p in st.tree if p.startswith("src/") and "pellet_rtg_depleted_nickel" in p)
    ck("V6.no-nickel-recipe-file", not nickel, "no pellet_rtg_depleted_nickel recipe or advancement file exists", nickel)
    recipe_files = sorted(p[len(RECIPES):] for p in st.tree if p.startswith(RECIPES + "pellet_rtg_depleted"))
    ck("V6.depleted-recipe-set", recipe_files == [f"pellet_rtg_depleted_{m}.json" for m in ("bismuth", "lead", "mercury", "neptunium", "zirconium")], "the generated depleted-pellet recipes are exactly bismuth, lead, mercury, neptunium, zirconium", recipe_files)
    jei = st.text(JEI)
    m = re.search(r"List<Item> ignoreMeta = List\.of\((.*?)\);", blank_comments(lf(jei)), re.S)
    ck("V6.jei-ignore-meta", m is not None and m[1].count("NtmItems.PELLET_RTG_DEPLETED.get()") == 1 and not re.search(r"NtmItems\.PELLET_RTG(?!_DEPLETED)\w*", jei), "NtmJeiPlugin lists NtmItems.PELLET_RTG_DEPLETED.get() exactly once in ignoreMeta and none of the ten pellets")
    # RTGPelletGameTests
    pt = st.text(RPGT)
    body = ""
    try:
        body = method_code(pt, "public static void rtg_pellet_recipes(GameTestHelper helper)")
    except ValueError:
        pass
    ck("V6.pellet-test-mercury", "pellet_rtg_depleted_mercury" in body and "NUGGET_MERCURY" in body and "List.of(\"pellet_rtg_depleted_mercury\", \"pellet_rtg_depleted_nickel\")" not in body
       and "List.of(DepletedRTGMaterial.MERCURY, DepletedRTGMaterial.NICKEL)" not in body, "RTGPelletGameTests.rtg_pellet_recipes asserts the mercury recipe (2 nugget_mercury) and no longer asserts its absence", body[-300:])
    ck("V6.pellet-test-nickel", re.search(r"pellet_rtg_depleted_nickel.{0,300}isEmpty\(\)", body) is not None and "DepletedRTGMaterial.NICKEL" in body, "RTGPelletGameTests.rtg_pellet_recipes still asserts that there is no nickel recipe")


# ---------------------------------------------------------------- V7

def v7_language(ck, inp, st, facts=None):
    live_en, edups = json_pairs(st.text(EN))
    live_zh, zdups = json_pairs(st.text(ZH))
    start_en, _ = json_pairs(inp.start[EN])
    start_zh, _ = json_pairs(inp.start[ZH])
    live_map, mdups = json_pairs(st.text(MAP))
    start_map, _ = json_pairs(inp.start[MAP])
    le, se = live_map["entries"], start_map["entries"]
    ck("V7.counts", (len(live_en), len(live_zh), len(le)) == (COUNTS_NOW["en"], COUNTS_NOW["zh"], COUNTS_NOW["map"])
       and dict(collections.Counter(e["kind"] for e in le.values())) == dict(upstream=COUNTS_NOW["upstream"], local=COUNTS_NOW["local"], deferred=COUNTS_NOW["deferred"])
       and (len(start_en), len(start_zh), len(se)) == (2443, 2336, 2443), "en_us.json 2,451 keys, zh_cn.json 2,344, mapping 2,451 (upstream 1,720, local 624, deferred 107); the start copies had 2,443 / 2,336 / 2,443",
       (len(live_en), len(live_zh), len(le), dict(collections.Counter(e["kind"] for e in le.values()))))
    en_added = {k: live_en[k] for k in live_en if k not in start_en}
    zh_added = {k: live_zh[k] for k in live_zh if k not in start_zh}
    map_added = [k for k in le if k not in se]
    ck("V7.added-exact", set(en_added) == set(KEYS) == set(zh_added) == set(map_added), "en_us.json, zh_cn.json and the mapping each gain exactly the eight keys", (sorted(set(en_added) ^ set(KEYS)), sorted(set(zh_added) ^ set(KEYS)), sorted(set(map_added) ^ set(KEYS))))
    ck("V7.values-equal-original", all(live_en.get(k) == EXPECT_LANG[k][0] and live_zh.get(k) == EXPECT_LANG[k][1] for k in KEYS)
       and all(inp.o_en_lines[a - 1].split("=", 1)[1].rstrip("\r") == live_en.get(k) and inp.o_zh_lines[b - 1].split("=", 1)[1].rstrip("\r") == live_zh.get(k) for k, _, a, b in LANG),
       "the English and Chinese values of the eight keys equal the original en_US.lang / zh_CN.lang lines and the task book", {k: (live_en.get(k), live_zh.get(k)) for k in KEYS})
    ck("V7.no-other-change", not [k for k in start_en if live_en.get(k) != start_en[k]] and not [k for k in start_zh if live_zh.get(k) != start_zh[k]] and not [k for k in se if le.get(k) != se[k]]
       and not edups and not zdups and not mdups and {k: v for k, v in live_map.items() if k != "entries"} == {k: v for k, v in start_map.items() if k != "entries"},
       "no other key of the three files is removed, changed or duplicated; the mapping's top-level fields are unchanged")
    for name, start_text, live_text, n in (("en_us.json", inp.start[EN], st.text(EN), 8), ("zh_cn.json", inp.start[ZH], st.text(ZH), 8), ("zh_cn-map.json", inp.start[MAP], st.text(MAP), 64)):
        ok, ins = insert_only(start_text, live_text)
        ck(f"V7.{name}-insert-only", ok and len([x for x in ins if x.strip()]) == n, f"{name} is the start text plus exactly {n} inserted lines", ins[:3])
        ck(f"V7.{name}-eol", eol_of(live_text) == eol_of(start_text), f"{name} keeps the start line-ending convention ({'CRLF' if eol_of(start_text) else 'LF'})")
    ck("V7.format", format_ok(st.text(ZH), live_zh) and format_ok(st.text(MAP), live_map), "zh_cn.json and the mapping are json.dumps(indent=2, ensure_ascii=False) in one line-ending convention")
    mbad = []
    for neo_key, o_key, _, _ in LANG:
        e = le.get(neo_key, {})
        en, zh = EXPECT_LANG[neo_key]
        want = dict(kind="upstream", source_en=en, source_key=o_key, source_zh=zh, target_en=en, target_zh=zh)
        if e != want:
            mbad.append((neo_key, e))
    ck("V7.map-entries", not mbad, "the eight mapping entries are upstream with source_key, source_en/source_zh (the original) and target_en/target_zh (the live files)", mbad)
    ck("V7.placeholders", all(re.findall(r"%[sd]", EXPECT_LANG[k][0]) == re.findall(r"%[sd]", live_zh.get(k, "")) for k in KEYS), "the Chinese values keep the English placeholders")
    prov = st.text(LP)
    deleted, inserted = diff_summary(inp.start[LP], prov)
    adds = [x for x in inserted if x.startswith("this.add(")]
    values = {}
    for x in adds:
        m1 = re.match(r'this\.add\(NtmItems\.(\w+), "((?:[^"\\]|\\.)*)"\);$', x)
        m2 = re.match(r'this\.add\("([\w.]+)", "((?:[^"\\]|\\.)*)"\);$', x)
        if m1:
            values[f"item.hbmsntm.{m1[1].lower()}"] = java_string(m1[2])
        elif m2:
            values[m2[1]] = java_string(m2[2])
        else:
            values[x] = None
    ck("V7.provider", not deleted and len(adds) == 8 and len(inserted) == 10 and all(x.startswith("//") for x in inserted if x not in adds) and values == {k: EXPECT_LANG[k][0] for k in KEYS},
       "NtmLanguageProvider is the start copy plus the eight add lines (English equal to the original) and two comment lines", (deleted, values))
    ck("V7.provider-eol", eol_of(prov) == eol_of(inp.start[LP]) == "\r", "NtmLanguageProvider keeps CRLF line endings")


# ---------------------------------------------------------------- V8

def v8_resources(ck, inp, st, facts=None):
    own = json.loads(st.text(OWN))
    assets = {a["target_path"]: a for a in own["assets"]}
    ck("V8.ownership-set", set(assets) == set(RESOURCES) and len(own["assets"]) == 5 and all(a["source_path"] == RESOURCES[t] for t, a in assets.items())
       and own.get("source_commit") == ORIGINAL_HEAD, "goal23c-resource-ownership.json lists exactly the five imports with their source paths at the recorded commit", sorted(set(assets) ^ set(RESOURCES)))
    bad = []
    for target, source in RESOURCES.items():
        a = assets.get(target, {})
        live, orig = st.files.get(target), inp.o_res.get(target)
        if live is None or orig is None or live != orig or sha(live) != a.get("sha256") or len(live) != a.get("bytes"):
            bad.append(Path(target).name)
    ck("V8.byte-equal", not bad, "the five NEO resources are byte-identical to the original worktree files and to the ownership record (sha256, bytes)", bad)
    pngs = [(t, png_size(st.files[t]), tuple(assets[t].get("png_size", ()))) for t in RESOURCES if t.endswith(".png") and t in st.files and t in assets]
    ck("V8.png-sizes", all(s is not None and tuple(s) == r for _, s, r in pngs) and len(pngs) == 4, "the four PNGs are valid PNGs with the recorded sizes (84x84, 256x256, 16x16, 16x16)", pngs)
    obj_live = st.files.get(R_OBJ, b"")
    blob = inp.o_obj_blob or b""
    obj_a = assets.get(R_OBJ, {})
    ck("V8.obj-blob", lf(obj_live.decode("utf-8", errors="replace")).encode("utf-8") == blob and sha(blob) == obj_a.get("blob_sha256") == obj_a.get("normalized_sha256") and len(blob) == obj_a.get("blob_bytes")
       and obj_a.get("normalized_equal_to_blob") is True and obj_live.count(b"\r\n") == obj_a.get("worktree_crlf_lines"), "the OBJ equals the original worktree bytes and, line-ending normalised, the git blob at HEAD (recorded hashes agree)",
       (len(blob), obj_a.get("blob_bytes")))
    objects = re.findall(rb"^o (\w+)", obj_live, re.M)
    ck("V8.obj-objects", objects == [b"Connector", b"Gen"] and obj_a.get("objects") == ["Connector", "Gen"], "the OBJ has the objects Connector and Gen (the parts RenderRTG draws)", objects)
    ni = {n["source_path"] for n in own.get("not_imported", [])}
    ck("V8.not-imported", O_RES_DIR + "textures/blocks/rtg.png" in ni and not (ROOT / RES / "textures/block/rtg.png").exists(), "the block icon textures/blocks/rtg.png is recorded as not imported and absent from NEO", sorted(ni))


# ---------------------------------------------------------------- V9

def v9_scope(ck, inp, st, facts=None):
    base, cur = inp.base_files, st.tree
    changed = {p for p in cur if p.startswith("src/") and base.get(p) != cur[p]} | {p for p in base if p.startswith("src/") and p not in cur}
    expected = set(NEW_CLASSES) | set(EDITED) | {LP, ZH, RGT, RPGT} | set(RESOURCES) | set(GENERATED)
    ck("V9.no-unexpected-path", not (changed - expected), "no src/ path outside the batch's new classes, edited production files, provider, zh_cn.json, resources, GameTest files and the generated output changed", sorted(changed - expected)[:10])
    ck("V9.expected-present", not ((expected - {RGT, RPGT}) - changed), "every expected src/ path (all but the two GameTest files) changed or was added", sorted((expected - {RGT, RPGT}) - changed)[:10])
    ck("V9.gametest-files-changed", {RGT, RPGT} <= changed, "RTGGameTests.java is new and RTGPelletGameTests.java changed (pending until the GameTest builder is done)", sorted({RGT, RPGT} - changed))
    ck("V9.set-equal", changed == expected, "the changed src/ set equals the expected set (5 new classes, 14 edited files, provider, zh_cn.json, 5 resources, 2 GameTest files, 11 generated files)", (sorted(changed - expected)[:5], sorted(expected - changed)[:5]))
    ck("V9.no-removed", not [p for p in base if p.startswith("src/") and p not in cur], "no src/ file was removed", [p for p in base if p.startswith("src/") and p not in cur][:5])
    ck("V9.originals-untouched", inp.original_ok[0], "the original worktree is unchanged (HEAD at the recorded commit, clean)")
    gen_changed = sorted(p for p in changed if p in GENERATED)
    ck("V9.generated-set", set(gen_changed) == set(GENERATED), "the generated files that changed are exactly the stamp, en_us.json, the blockstate, particle model, three item models, loot table, pickaxe tag, mercury recipe and its advancement", sorted(set(GENERATED) ^ set(gen_changed)))
    # insert-only against the start copies
    expect_inserts = {
        NB: ["// Original machine_rtg (internal name machine_rtg_grey, ModBlocks.java:1855): hardness 5, resistance 10.",
             'public static final DeferredBlock<Block> MACHINE_RTG = register("machine_rtg", () -> new MachineRTGBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops().noOcclusion()));'],
        NBET: ["public static final Supplier<BlockEntityType<MachineRTGBlockEntity>> MACHINE_RTG = BLOCK_ENTITY_TYPES.register(", '"machine_rtg",', "() -> BlockEntityType.Builder.of(", "MachineRTGBlockEntity::new,",
               "NtmBlocks.MACHINE_RTG.get())", ".build(null));"],
        NMT: ['public static final DeferredHolder<MenuType<?>, MenuType<MachineRTGMenu>> MACHINE_RTG = reg("machine_rtg", MachineRTGMenu::new);'],
        NMC: ["import com.hbm.inventory.screens.MachineRTGScreen;", "event.register(NtmMenuTypes.MACHINE_RTG.get(), MachineRTGScreen::new);"],
        CP: ["BlockEntityRenderers.register(NtmBlockEntityTypes.MACHINE_RTG.get(), new RenderRTG());"],
        RM: ['public static final ResourceLocation RTG_TEX = NuclearTechMod.withDefaultNamespace("textures/models/machines/rtg.png");', "public static IModelCustom rtg;",
             'rtg = new HFRWavefrontObject("models/obj/machines/rtg.obj").asVBO();'],
        NI: ['public static final DeferredItem<Item> THERMO_ELEMENT = ITEMS.register("thermo_element", () -> new Item(new Item.Properties())); // original ModItems.java:717,2804',
             'public static final DeferredItem<Item> RTG_UNIT = ITEMS.register("rtg_unit", () -> new Item(new Item.Properties())); // original ModItems.java:563,2565'],
        CT: ["output.accept(NtmItems.RTG_UNIT.get());", "output.accept(NtmItems.THERMO_ELEMENT);", "output.accept(NtmBlocks.MACHINE_RTG);"],
        JEI: ["// The six depleted RTG pellets are separate JEI ingredients; the ten pellets stay one entry each, whatever their remaining life.", "NtmItems.PELLET_RTG_DEPLETED.get(),"],
        LOOT: ["this.dropSelf(NtmBlocks.MACHINE_RTG.get());"], TAG: ["NtmBlocks.MACHINE_RTG.get(),"],
        MP: ["this.basicItem(NtmItems.THERMO_ELEMENT.get());", "this.basicItem(NtmItems.RTG_UNIT.get());"],
    }
    bad = {}
    for path, want in expect_inserts.items():
        ok, ins = insert_only(inp.start[path], st.text(path))
        got = [x.strip() for x in ins if x.strip()] if ok else ins
        if not ok or collections.Counter(got) != collections.Counter(want):
            bad[Path(path).name] = got if ok else ins
    # AssemblyMachineRecipes: the inserted lines are the three comment lines and the four statements
    ok, ins = insert_only(inp.start[AMR], st.text(AMR))
    if ok:
        statements = [s for n, s, _ in neo_assembly_statements(st.text(AMR)) if n in TASK_ROWS]
        stmt_lines = []
        code_lines = lf(st.text(AMR)).split("\n")
        for n in TASK_ROWS:
            first = next(i for i, l in enumerate(code_lines) if f'new GenericRecipe("{n}")' in l)
            last = first
            while not code_lines[last].rstrip().endswith(";"):
                last += 1
            stmt_lines += [x.strip() for x in code_lines[first:last + 1]]
        comments = [x.strip() for x in ins if x.strip().startswith("//")]
        rest = [x.strip() for x in ins if x.strip() and not x.strip().startswith("//")]
        if len(comments) != 3 or collections.Counter(rest) != collections.Counter(stmt_lines) or len(statements) != 4:
            bad["AssemblyMachineRecipes"] = (len(comments), len(rest), len(stmt_lines))
    else:
        bad["AssemblyMachineRecipes"] = ins
    ck("V9.insert-only", not bad, "the 13 registration/datagen files are the start copy plus exactly the expected inserted lines (AssemblyMachineRecipes: three comment lines and the four statements)", bad)
    deleted, inserted = diff_summary(inp.start[RP], st.text(RP))
    ck("V9.provider-diff", len(deleted) == 2 and all(x.startswith("//") for x in deleted) and ":219, mercury" in deleted[0] and len(inserted) == 3
       and inserted[2] == "addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.MERCURY, NtmItems.NUGGET_MERCURY.get(), 2);" and all(x.startswith("//") for x in inserted[:2]),
       "NtmRecipeProvider differs from the start copy only by the replaced two-line mercury comment (now two comment lines and the mercury row)", (deleted, inserted))
    ck("V9.eol-kept", all(eol_of(st.text(p)) == eol_of(inp.start[p]) for p in EDITED + [LP, RPGT, ZH, EN, MAP]), "every edited file keeps its start line-ending convention", [p for p in EDITED + [LP, RPGT, ZH, EN, MAP] if eol_of(st.text(p)) != eol_of(inp.start[p])])
    if facts is not None:
        outside = {top: sorted(p for p in ({q for q in cur if q.startswith(top)} | {q for q in base if q.startswith(top)}) if base.get(p) != cur.get(p)) for top in ("migration/", "tools/")}
        facts["V9"] = dict(src_changed=sorted(changed), generated_changed=gen_changed, not_in_expected=sorted(changed - expected), outside_src_info_only=outside)


# ---------------------------------------------------------------- V10

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def v10_gametests(ck, inp, st, facts=None):
    if not st.has(RGT):
        ck("V10.rtg-file", False, "RTGGameTests.java exists (the GameTest builder has not written it yet: pending)", RGT)
    else:
        live = st.text(RGT)
        code = blank_comments(live)
        tests = {name: args for args, name in TEST_ANNOTATED.findall(code)}
        ck("V10.rtg-file", True, "RTGGameTests.java exists")
        ck("V10.rtg-ten-tests", sorted(tests) == sorted(GT_TESTS), "RTGGameTests has the ten @GameTest methods " + ", ".join(GT_TESTS), sorted(tests))
        ck("V10.rtg-annotation-count", len(re.findall(r"@GameTest\(", code)) == 10, "RTGGameTests has exactly 10 @GameTest( annotations", len(re.findall(r"@GameTest\(", code)))
        literal = f'batch = "{GT_BATCH}"'
        const = re.search(r'String BATCH = "([^"]+)"', code)
        ck("V10.rtg-batch", bool(tests) and all((literal in a) or ("batch = BATCH" in a and const and const[1] == GT_BATCH) for a in tests.values()), f"every @GameTest uses batch {GT_BATCH}", tests)
        ck("V10.rtg-logger-marker", re.search(r"LOGGER\.info\(\"\[hbm-rtg-machine\] \{\} passed\"", code) is not None or code.count(GT_MARK + " ") >= 1, "the class logs `[hbm-rtg-machine] <name> passed` through LOGGER")
        missing = []
        for name in GT_TESTS:
            try:
                body = method_code(live, f"void {name}(GameTestHelper helper)")
            except ValueError:
                missing.append(name)
                continue
            if f'"{name}"' not in body:
                missing.append(name)
        ck("V10.rtg-tests-report-their-name", not missing, "every test method passes its own name to the passed-line helper", missing)
        ck("V10.rtg-eol-lf", "\r" not in live, "RTGGameTests.java has LF line endings")
        ck("V10.rtg-no-production-client", not re.search(r"\bMachineRTGScreen\b|\bRenderRTG\b|\bResourceManager\b", code), "RTGGameTests does not reference the screen, the renderer or ResourceManager")
    others = inp.gametest_other
    ck("V10.start-total", others == START_GAMETESTS, "the other GameTest classes hold the 112 pre-batch tests", others)
    # RTGPelletGameTests
    start, live = inp.start[RPGT], st.text(RPGT)
    s_lines = lf(start).split("\n")
    j_idx = [i for i, l in enumerate(s_lines) if "the four recycling recipes" in l]
    b_idx = [i for i, l in enumerate(s_lines) if "// The original has no recycling recipe for the mercury and nickel pellets." in l]
    if len(j_idx) != 1 or len(b_idx) != 1:
        ck("V10.pellet-regions", False, "the start copy has the javadoc phrase and the mercury/nickel comment once", (j_idx, b_idx))
        return
    k_idx = [i for i, l in enumerate(s_lines) if "There is no machine here" in l]
    j, b0 = j_idx[0], b_idx[0]
    k = k_idx[0] if len(k_idx) == 1 else -10
    b1 = b0 + 7
    shape_ok = s_lines[b1].strip() == "}" and s_lines[b1 + 1].strip() == "}).run();"
    ck("V10.pellet-regions", shape_ok, f"the start copy's mercury/nickel block is lines {b0 + 1}-{b1 + 1} (comment, two loops), followed by `}}).run();` (the handoff's 408-415 is off by one)", (b0 + 1, b1 + 1, s_lines[b1], s_lines[b1 + 1]))
    ops = non_equal_ops(start, live)
    stray = []
    for tag, i1, i2, s_part, l_part in ops:
        in_block = (b0 <= i1 and i2 <= b1 + 1) if tag != "insert" else (b0 <= i1 <= b1 + 1)
        in_doc = (i1, i2) in ((j, j + 1), (k, k + 2))
        if not (in_block or in_doc):
            stray.append((tag, i1 + 1, s_part[:2], l_part[:2]))
    ck("V10.pellet-diff-scope", not stray, "RTGPelletGameTests differs from the start copy only in the mercury/nickel block and the class-javadoc lines (the recycling-recipes phrase :72 and the two-line `There is no machine here` sentence :81-82, as the main agent accepted)", stray[:4])
    doc_ops = [o for o in ops if (o[1], o[2]) == (j, j + 1)]
    block_ops = [o for o in ops if o[1] >= b0 and (o[2] <= b1 + 1 if o[0] != "insert" else o[1] <= b1 + 1)]
    ck("V10.pellet-changed", bool(doc_ops) and bool(block_ops) and "mercury" in " ".join(doc_ops[0][4]).lower()
       and any((o[1], o[2]) == (k, k + 2) and "RTGGameTests" in " ".join(o[4]) for o in ops), "the javadoc phrase now also names the mercury row, the `There is no machine here` sentence points to RTGGameTests and the block was replaced",
       (len(doc_ops), len(block_ops)))
    ck("V10.pellet-annotation-count", len(re.findall(r"@GameTest\(", live)) == len(re.findall(r"@GameTest\(", start)) == 9, "RTGPelletGameTests keeps its nine @GameTest( annotations")
    ck("V10.pellet-eol", eol_of(live) == eol_of(start) == "" and "\r" not in live, "RTGPelletGameTests keeps its LF line endings")
    ck("V10.pellet-recycle-rows-kept", "recycleRecipes()" in live and live.count("recycleRows.size() == 4") == 1, "recycleRecipes() and its four-row assertion are unchanged")


# ---------------------------------------------------------------- V11 / V12

def v11_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    n_new = len(re.findall(r"@GameTest\(", blank_comments(st.text(RGT)))) if st.has(RGT) else 0
    total = START_GAMETESTS + n_new
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V11.log-all-passed", bool(match) and int(match[1]) == total and n_new > 0, f"{Path(path).name} says `All {total} required tests passed` (112 + {n_new} @GameTest methods in RTGGameTests)", (match and match[0], total))
    live_total = inp.gametest_other + n_new
    ck("V11.annotation-total", live_total == total, "the live @GameTest( total equals 112 + RTGGameTests", (live_total, total))
    ck("V11.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in GT_TESTS:
        ck(f"V11.log-{name}", f"{GT_MARK} {name} passed" in text, f"the log has `{GT_MARK} {name} passed`")
    ck("V11.log-rtg-pellet-recipes", "[hbm-rtg] rtg_pellet_recipes passed" in text, "the log has `[hbm-rtg] rtg_pellet_recipes passed`")
    ck("V11.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total, log=str(path))


def inner_expected(text):
    code = blank_comments(lf(text))
    anon = len(re.findall(r"new\s+[A-Z][\w.<>]*\s*\([^();{}]*\)\s*\{", code))
    nested = len(re.findall(r"^[ \t]{4,}(?:(?:public|private|protected|static|final|abstract)\s+)*(?:class|record|enum|interface)\s+\w+", code, re.M))
    return anon + nested


def v12_jar(ck, inp, st, path):
    classes = {"MachineRTGBlock": "com/hbm/blocks/machine/MachineRTGBlock", "MachineRTGBlockEntity": "com/hbm/blockentity/machine/MachineRTGBlockEntity", "MachineRTGMenu": "com/hbm/inventory/menus/MachineRTGMenu",
               "MachineRTGScreen": "com/hbm/inventory/screens/MachineRTGScreen", "RenderRTG": "com/hbm/render/blockentity/RenderRTG", "RTGGameTests": "com/hbm/gametest/RTGGameTests"}
    sources = {"MachineRTGBlock": BLK, "MachineRTGBlockEntity": BEP, "MachineRTGMenu": MENU, "MachineRTGScreen": SCR, "RenderRTG": REN, "RTGGameTests": RGT}
    live_en, _ = json_pairs(st.text(EN))
    live_zh, _ = json_pairs(st.text(ZH))
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        inner = {}
        missing = []
        for short, cls in classes.items():
            if cls + ".class" not in names:
                missing.append(cls)
            inner[short] = sorted(n for n in names if n.startswith(cls + "$") and n.endswith(".class"))
        need = {short: inner_expected(st.text(sources[short])) if st.has(sources[short]) else 0 for short in classes}
        short_inner = {k: (len(inner[k]), need[k]) for k in classes if len(inner[k]) < need[k]}
        ck("V12.classes", not missing, "the JAR has MachineRTGBlock, MachineRTGBlockEntity, MachineRTGMenu, MachineRTGScreen, RenderRTG and RTGGameTests", missing)
        ck("V12.inner-classes", not short_inner, "the JAR has at least as many inner/anonymous classes as the sources declare", short_inner)
        bad = [Path(t).name for t in RESOURCES if t[len("src/main/resources/"):] not in names or jar.read(t[len("src/main/resources/"):]) != st.files.get(t)]
        ck("V12.resources", not bad, "the five imported resources in the JAR are byte-equal to the source files", bad)
        gbad = [p for p in GENERATED if p not in (STAMP, EN) and (p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p))]
        ck("V12.generated", not gbad, "the generated blockstate, models, loot table, pickaxe tag, mercury recipe and advancement in the JAR are byte-equal to the live files", gbad)
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V12.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in KEYS if data.get(k) != source.get(k) or k not in data}
            ck(f"V12.{Path(entry).name}", not bad, f"{entry} in the JAR carries the eight keys with the values of the source file", bad)
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, inner_classes=inner,
                note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st, facts)
    guarded(ck, "V2", v2_block_entity, inp, st, facts)
    guarded(ck, "V3", v3_block_menu_screen_renderer, inp, st, facts)
    guarded(ck, "V4", v4_registration, inp, st, facts)
    guarded(ck, "V5", v5_assembly, inp, st, facts)
    guarded(ck, "V6", v6_leftovers, inp, st, facts)
    guarded(ck, "V7", v7_language, inp, st, facts)
    guarded(ck, "V8", v8_resources, inp, st, facts)
    guarded(ck, "V9", v9_scope, inp, st, facts)
    guarded(ck, "V10", v10_gametests, inp, st, facts)
    return ck


def T(path, fn):
    return lambda st: st.set_text(path, fn(st.text(path)))


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


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None, check ids that must pass in the unmutated tree)."""
    rtg_lead_row = "addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.MERCURY, NtmItems.NUGGET_MERCURY.get(), 2);"
    return [
        # V2 block entity
        ("heatmax_600_to_500", "V2.", T(BEP, lambda t: rep1(t, "RTGUtil.rtgDecay() ? 600 : 200", "RTGUtil.rtgDecay() ? 500 : 200")), None, ()),
        ("heatmax_static_final_field", "V2.", T(BEP, lambda t: rep1(t, "public static int getHeatMax() {\n        return RTGUtil.rtgDecay() ? 600 : 200;\n    }",
                                                                  "private static final int HEAT_MAX = RTGUtil.rtgDecay() ? 600 : 200;\n    public static int getHeatMax() {\n        return HEAT_MAX;\n    }")), None, ()),
        ("max_power_10000", "V2.", T(BEP, lambda t: rep1(t, "MAX_POWER = 100_000L", "MAX_POWER = 10_000L")), None, ()),
        ("heat_times_4", "V2.", T(BEP, lambda t: rep1(t, "(long) this.heat * 5L", "(long) this.heat * 4L")), None, ()),
        ("provide_after_update", "V2.", T(BEP, lambda t: swap_lines(t, "for(DirPos pos : this.getConPos())", "this.heat = RTGUtil.updateRTGs(this.slots, SLOT_IO);")), None, ()),
        ("network_pack_20", "V2.", T(BEP, lambda t: rep1(t, "this.networkPackNT(50);", "this.networkPackNT(20);")), None, ()),
        ("max_stack_64", "V2.", T(BEP, lambda t: rep1(t, "public int getMaxStackSize() {\n        return 1;", "public int getMaxStackSize() {\n        return 64;")), None, ()),
        ("slots_for_face_slot_0", "V2.", T(BEP, lambda t: rep1(t, "getSlotsForFace(Direction direction) { return NO_SLOTS; }", "getSlotsForFace(Direction direction) { return new int[] { 0 }; }")), None, ()),
        ("take_through_face_true", "V2.", T(BEP, lambda t: rep1(t, "canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }", "canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return true; }")), None, ()),
        ("place_through_face_true", "V2.", T(BEP, lambda t: rep1(t, "canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }", "canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) { return true; }")), None, ()),
        ("nbt_heat_key_renamed", "V2.", T(BEP, lambda t: rep1(t, 'tag.putInt("heat", this.heat)', 'tag.putInt("heat2", this.heat)')), None, ()),
        ("nbt_power_as_int", "V2.", T(BEP, lambda t: rep1(t, 'tag.putLong("power", this.power)', 'tag.putInt("power", (int) this.power)')), None, ()),
        ("serialize_order_swapped", "V2.", T(BEP, lambda t: swap_lines(t, "buf.writeLong(this.power);", "buf.writeInt(this.heat);")), None, ()),
        ("set_changed_removed", "V2.", T(BEP, lambda t: rep1(t, "if(decays || this.power != previousPower || this.heat != previousHeat) this.setChanged();", "")), None, ()),
        ("heat_cap_removed", "V2.", T(BEP, lambda t: rep1(t, "if(this.heat > getHeatMax()) this.heat = getHeatMax();", "")), None, ()),
        ("power_cap_removed", "V2.", T(BEP, lambda t: rep1(t, "if(this.power > MAX_POWER) this.power = MAX_POWER;", "")), None, ()),
        ("can_place_any_item", "V2.", T(BEP, lambda t: rep1(t, "stack.getItem() instanceof RTGPelletItem", "true")), None, ()),
        ("client_guard_removed", "V2.", T(BEP, lambda t: rep_first(t, "if(this.level == null || this.level.isClientSide) return;", "")), None, ()),
        ("setremoved_unsubscribe_dropped", "V2.", T(BEP, lambda t: rep1(t, "this.removeNetworkSubscriptions();\n        super.setRemoved();", "super.setRemoved();")), None, ()),
        ("default_name_changed", "V2.", T(BEP, lambda t: rep1(t, 'Component.translatable("container.rtg")', 'Component.translatable("container.rtg2")')), None, ()),
        ("provider_speed_override_added", "V2.", T(BEP, lambda t: rep1(t, "@Override public long getMaxPower()", "@Override public long getProviderSpeed() { return 1L; }\n    @Override public long getMaxPower()")), None, ()),
        # V3
        ("block_on_remove_no_drops", "V3.", T(BLK, lambda t: rep1(t, "Containers.dropContents(level, pos, rtg);", "")), None, ()),
        ("block_state_property_added", "V3.", T(BLK, lambda t: rep1(t, "@Override protected RenderShape getRenderShape", "protected void createBlockStateDefinition(Object builder) { }\n    @Override protected RenderShape getRenderShape")), None, ()),
        ("block_ticker_removed", "V3.", T(BLK, lambda t: rep1(t, "tickable.updateEntity();", "")), None, ()),
        ("menu_slot_x_16_to_17", "V3.", T(MENU, lambda t: rep1(t, "this.addSlots(be, 0, 16, 18, 3, 5);", "this.addSlots(be, 0, 17, 18, 3, 5);")), None, ()),
        ("menu_hotbar_y", "V3.", T(MENU, lambda t: rep1(t, "this.playerInv(inventory, 8, 106, 164);", "this.playerInv(inventory, 8, 106, 165);")), None, ()),
        ("screen_bar_source_y_10_to_11", "V3.", T(SCR, lambda t: rep1(t, "176, 10 + (51 - i)", "176, 11 + (51 - i)")), None, ()),
        ("screen_title_colour", "V3.", T(SCR, lambda t: rep1(t, "7, 10925486, false", "7, 10925487, false")), None, ()),
        ("screen_electricity_x", "V3.", T(SCR, lambda t: rep1(t, "this.leftPos + 146, this.topPos + 9, 16, 51, this.be.power", "this.leftPos + 147, this.topPos + 9, 16, 51, this.be.power")), None, ()),
        ("screen_pellet_power_x4", "V3.", T(SCR, lambda t: rep1(t, "pellet.getHeat() * 5", "pellet.getHeat() * 4")), None, ()),
        ("screen_heat_clamp_removed", "V3.", T(SCR, lambda t: rep1(t, "Math.min(51, this.be.getHeatScaled(51))", "this.be.getHeatScaled(51)")), None, ()),
        ("screen_heat_clamp_changed", "V3.", T(SCR, lambda t: rep1(t, "Math.min(51, this.be.getHeatScaled(51))", "Math.min(50, this.be.getHeatScaled(51))")), None, ()),
        ("screen_height", "V3.", T(SCR, lambda t: rep1(t, "this.imageHeight = 188;", "this.imageHeight = 189;")), None, ()),
        ("screen_texture", "V3.", T(SCR, lambda t: rep1(t, "textures/gui/gui_rtg.png", "textures/gui/gui_rtg2.png")), None, ()),
        ("render_connector_angle_90_to_minus_90", "V3.", T(REN, lambda t: rep_first(t, "rotationDegrees(90F)", "rotationDegrees(-90F)")), None, ()),
        ("render_connector_direction", "V3.", T(REN, lambda t: rep1(t, "Library.canConnect(level, pos.west(), Direction.WEST)", "Library.canConnect(level, pos.east(), Direction.WEST)")), None, ()),
        ("render_item_draws_connector", "V3.", T(REN, lambda t: rep1(t, "RenderRTG.this.bindTexture(ResourceManager.RTG_TEX);", 'RenderRTG.this.bindTexture(ResourceManager.RTG_TEX);\n                ResourceManager.rtg.renderPart("Connector");')), None, ()),
        ("render_part_name", "V3.", T(REN, lambda t: rep_first(t, 'renderPart("Gen")', 'renderPart("Gen2")')), None, ()),
        ("resource_manager_obj_path", "V3.", T(RM, lambda t: rep1(t, "models/obj/machines/rtg.obj", "models/obj/machines/rtg2.obj")), None, ()),
        ("resource_manager_tex_path", "V3.", T(RM, lambda t: rep1(t, "textures/models/machines/rtg.png", "textures/models/machines/rtg2.png")), None, ()),
        # V4
        ("reg_block_removed", "V4.", T(NB, lambda t: drop_line(t, 'MACHINE_RTG = register("machine_rtg"')), None, ()),
        ("reg_block_strength", "V4.", T(NB, lambda t: line_edit(t, 'MACHINE_RTG = register("machine_rtg"', "strength(5.0F, 10.0F)", "strength(5.0F, 11.0F)")), None, ()),
        ("reg_block_no_tool_requirement", "V4.", T(NB, lambda t: line_edit(t, 'MACHINE_RTG = register("machine_rtg"', ".requiresCorrectToolForDrops()", "")), None, ()),
        ("reg_block_entity_type_renamed", "V4.", T(NBET, lambda t: rep1(t, '"machine_rtg",', '"machine_rtg2",')), None, ()),
        ("reg_menu_removed", "V4.", T(NMT, lambda t: drop_line(t, "MACHINE_RTG")), None, ()),
        ("reg_screen_removed", "V4.", T(NMC, lambda t: drop_line(t, "MachineRTGScreen::new")), None, ()),
        ("reg_renderer_removed", "V4.", T(CP, lambda t: drop_line(t, "new RenderRTG()")), None, ()),
        ("creative_machine_removed", "V4.", T(CT, lambda t: drop_line(t, "output.accept(NtmBlocks.MACHINE_RTG);")), None, ()),
        ("creative_machine_moved", "V4.", T(CT, lambda t: swap_lines(t, "output.accept(NtmBlocks.MACHINE_RTG);", "output.accept(NtmBlocks.MACHINE_WOOD_BURNER);")), None, ()),
        ("creative_parts_removed", "V4.", T(CT, lambda t: drop_line(t, "output.accept(NtmItems.RTG_UNIT.get());")), None, ()),
        ("creative_control_removed", "V4.", T(CT, lambda t: drop_line(t, "output.accept(NtmItems.THERMO_ELEMENT);")), None, ()),
        ("item_thermo_not_plain", "V4.", T(NI, lambda t: line_edit(t, 'ITEMS.register("thermo_element"', "new Item(new Item.Properties())", "new Item(new Item.Properties().stacksTo(1))")), None, ()),
        ("item_model_removed", "V4.", T(MP, lambda t: drop_line(t, "this.basicItem(NtmItems.RTG_UNIT.get());")), None, ()),
        ("loot_dropself_removed", "V4.", T(LOOT, lambda t: drop_line(t, "MACHINE_RTG")), None, ()),
        ("tag_entry_removed", "V4.", T(TAG, lambda t: drop_line(t, "MACHINE_RTG")), None, ()),
        ("generated_pickaxe_entry_removed", "V4.", T(G_TAG, lambda t: drop_line(t, '"hbmsntm:machine_rtg",')), None, ()),
        ("generated_loot_deleted", "V4.|V9.", D(G_LOOT), None, ()),
        ("generated_blockstate_changed", "V4.", T(G_STATE, lambda t: rep1(t, "machine_rtg_particle", "machine_rtg_particle2")), None, ()),
        ("client_class_leaks_into_common", "V4.", lambda st: st.refs.__setitem__(BLK, {"RenderRTG": 1}), None, ()),
        # V5
        ("asm_count_changed", "V5.|V9.", T(AMR, lambda t: rep1(t, "new ComparableStack(NtmItems.WIRE_RED_COPPER.get(), 16)", "new ComparableStack(NtmItems.WIRE_RED_COPPER.get(), 15)")), None, ()),
        ("asm_rtg_setup_200_to_100", "V5.|V9.", T(AMR, lambda t: rep1(t, 'new GenericRecipe("ass.rtg").setup(200, 100)', 'new GenericRecipe("ass.rtg").setup(100, 100)')), None, ()),
        ("asm_thermo_setup_changed", "V5.|V9.", T(AMR, lambda t: rep1(t, 'new GenericRecipe("ass.thermoelement").setup(60, 100)', 'new GenericRecipe("ass.thermoelement").setup(60, 101)')), None, ()),
        ("asm_row_renamed", "V5.|V9.", T(AMR, lambda t: rep1(t, 'new GenericRecipe("ass.rtgunit")', 'new GenericRecipe("ass.rtgunit2")')), None, ()),
        ("asm_wire_swapped", "V5.|V9.", T(AMR, lambda t: rep1(t, "new ComparableStack(NtmItems.WIRE_GOLD.get(), 2)", "new ComparableStack(NtmItems.WIRE_RED_COPPER.get(), 2)")), None, ()),
        ("asm_cast_plate_type", "V5.|V9.", T(AMR, lambda t: rep1(t, "CastPlateItem.Type.LEAD, 2", "CastPlateItem.Type.COPPER, 2")), None, ()),
        ("asm_output_count", "V5.|V9.", T(AMR, lambda t: rep1(t, "new ItemStack(NtmBlocks.MACHINE_RTG.get(), 1)", "new ItemStack(NtmBlocks.MACHINE_RTG.get(), 2)")), None, ()),
        ("asm_existing_row_changed", "V5.|V9.", T(AMR, lambda t: rep1(t, 'new GenericRecipe("ass.dieselgen").setup(200, 100)', 'new GenericRecipe("ass.dieselgen").setup(200, 101)')), None, ()),
        ("asm_row_inside_enable528_block", "V5.", T(AMR, lambda t: rep1(t, '        this.register(new GenericRecipe("ass.rtg")', '        if(!NtmConfig.enable528()) this.register(new GenericRecipe("ass.rtg")')), None, ()),
        # V6
        ("mercury_row_removed", "V6.", T(RP, lambda t: drop_line(t, rtg_lead_row)), None, ()),
        ("mercury_count_changed", "V6.", T(RP, lambda t: rep1(t, rtg_lead_row, rtg_lead_row.replace("get(), 2)", "get(), 3)"))), None, ()),
        ("mercury_result_changed", "V6.", T(RP, lambda t: rep1(t, rtg_lead_row, rtg_lead_row.replace("NUGGET_MERCURY", "INGOT_LEAD"))), None, ()),
        ("nickel_row_added", "V6.", T(RP, lambda t: rep1(t, rtg_lead_row, rtg_lead_row + "\r\n        addRTGRecyclingRecipe(recipeOutput, DepletedRTGMaterial.NICKEL, NtmItems.NUGGET_MERCURY.get(), 2);")), None, ()),
        ("nickel_recipe_file_added", "V6.", lambda st: st.set_text(RECIPES + "pellet_rtg_depleted_nickel.json", "{}"), None, ()),
        ("mercury_json_meta_changed", "V6.", T(G_REC, lambda t: rep1(t, '"hbmsntm:meta": 1', '"hbmsntm:meta": 2')), None, ()),
        ("mercury_json_count_changed", "V6.", T(G_REC, lambda t: rep1(t, '"count": 2', '"count": 3')), None, ()),
        ("mercury_json_strict", "V6.", T(G_REC, lambda t: json_edit(t, lambda d: d["ingredients"][0].__setitem__("strict", True))), None, ()),
        ("mercury_json_deleted", "V6.|V9.", D(G_REC), None, ()),
        ("jei_line_removed", "V6.", T(JEI, lambda t: drop_line(t, "NtmItems.PELLET_RTG_DEPLETED.get(),")), None, ()),
        ("jei_pellet_added", "V6.", T(JEI, lambda t: rep1(t, "NtmItems.PELLET_RTG_DEPLETED.get(),", "NtmItems.PELLET_RTG_DEPLETED.get(),\r\n                NtmItems.PELLET_RTG.get(),")), None, ()),
        ("pellet_test_mercury_assert_dropped", "V6.", T(RPGT, lambda t: t.replace("NUGGET_MERCURY", "INGOT_LEAD")), RPGT, ("V6.pellet-test-mercury",)),
        # V7
        ("zh_value_changed", "V7.", zh_set("container.rtg", "放射性发电机"), None, ()),
        ("zh_tooltip_placeholder_dropped", "V7.", zh_set("desc.gui.rtg.pelletPower", "%s (%s HE/刻"), None, ()),
        ("en_key_dropped", "V7.", T(EN, lambda t: drop_line(t, '"container.rtg"')), None, ()),
        ("zh_stray_key_added", "V7.", zh_set("hbmsntm.stray", "x"), None, ()),
        ("map_kind_flipped", "V7.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["container.rtg"].__setitem__("kind", "local"))), None, ()),
        ("map_source_zh_changed", "V7.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda d: d["entries"]["item.hbmsntm.rtg_unit"].__setitem__("source_zh", "RTG单元"))), None, ()),
        ("provider_string_changed", "V7.", T(LP, lambda t: rep1(t, '"Accepted Pellets:"', '"Accepted pellets:"')), None, ()),
        # V8
        ("obj_byte_flipped", "V8.", Bx(R_OBJ, flip_byte), None, ()),
        ("gui_png_byte_flipped", "V8.", Bx(R_GUI, flip_byte), None, ()),
        ("thermo_png_byte_flipped", "V8.", Bx(R_TE, flip_byte), None, ()),
        ("ownership_sha_changed", "V8.", lambda st: st.set_text(OWN, json_edit(st.text(OWN), lambda d: d["assets"][0].__setitem__("sha256", "0" * 64))), None, ()),
        ("obj_deleted", "V8.|V9.|V0.", D(R_OBJ), None, ()),
        # V9
        ("stray_src_file_added", "V9.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}"), None, ()),
        ("unrelated_src_file_touched", "V9.", touch(J + "hazard/HazardSystem.java"), None, ()),
        ("unrelated_resource_touched", "V9.", touch(RES + "textures/gui/gui_diesel.png"), None, ()),
        ("edited_file_line_inserted", "V9.", T(NMT, lambda t: rep1(t, "MACHINE_RTG = reg(", "STRAY = reg(\"stray\", MachineRTGMenu::new);\r\n    public static final DeferredHolder<MenuType<?>, MenuType<MachineRTGMenu>> MACHINE_RTG = reg(")), None, ()),
        # V10
        ("gt_annotation_removed", "V10.", T(RGT, lambda t: rep_first(t, "@GameTest(", "// @GameTest(")), RGT, ("V10.rtg-ten-tests", "V10.rtg-annotation-count")),
        ("gt_batch_changed", "V10.", T(RGT, lambda t: rep_first(t, "batch = BATCH", 'batch = "other"')), RGT, ("V10.rtg-batch",)),
        ("gt_method_renamed", "V10.", T(RGT, lambda t: rep1(t, "rtg_heat_cap(GameTestHelper helper)", "rtg_heat_cap_x(GameTestHelper helper)")), RGT, ("V10.rtg-ten-tests",)),
        ("pellet_gt_stray_line", "V10.", T(RPGT, lambda t: t + "\n// mutation\n"), None, ("V10.pellet-diff-scope",)),
        ("pellet_gt_annotation_added", "V10.", T(RPGT, lambda t: t + "\n// @GameTest(mutation)\n"), None, ()),
        ("pellet_gt_other_assert_changed", "V10.", T(RPGT, lambda t: rep1(t, "recycleRows.size() == 4", "recycleRows.size() == 5")), None, ()),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for label, prefixes, apply, required, requires_ok in mutations():
        if required is not None and not st.has(required):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        blocked = [c for c in requires_ok if c in base_failed]
        if blocked:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"the unmutated tree already fails {blocked} (the GameTest builder's work is pending)")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except (AssertionError, KeyError, ValueError, StopIteration) as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error!r}"[:300])
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
    production = NEW_CLASSES + EDITED + [LP, ZH, EN, STAMP, MAP, OWN, RGT, RPGT] + list(RESOURCES) + GENERATED
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(applied) - len(undetected), mutations_applied=len(applied), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.tree.get(p) for p in dict.fromkeys(production)},
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
