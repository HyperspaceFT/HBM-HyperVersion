"""Verify the Goal27A batch statically: the 109-material table (Mats), the item registry (MaterialEntries), the fixed smelting entries
(MatDistribution / hbmCrucibleSmelting.json), the multi-material crucible, the scraps (CopperScrapsItem, creative tab, item models, textures),
the shredder gem/ingot -> dust rows, the seven effect icons, language; the scope of the batch and the GameTest source; with --gametest-log the
GameTest log; with --jar the JAR.

Read-only for both worktrees. Writes only build/migration/goal27a/verify/report.json. Runs the two resource scripts with --check (they only
read). No game, Gradle, javac or network.

- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO start commit 71c2f660.
- V1  The original parsed at the cited lines (Mats.java:63-181 declarations, :190-262 factories and lookups, MaterialShapes.java:31-63,
      MatDistribution.java:39-95, TileEntityCrucible.java, ItemScraps.java, ItemAutogen.java, ShredderRecipes.java:55-70, HbmPotion.java:49-62,
      OreDictManager DictFrames, en_US.lang / zh_CN.lang hbmmat.*); a moved line fails.
- V2  NEO source against V1: every material (id, names, behaviour, colours, conversion, autogen, trait, order), factory semantics, the lookup
      order and the integer conversion, MatDistribution defaults (60 rows), handler order, MaterialEntries vs inventory/registry.json, the crucible
      loops and the start-identical rest, MAX_SYNC_ENTRIES, files that must stay byte-identical, MaterialShapes, the shredder rows vs
      inventory/shredder_gap.json, the scraps item, creative tab, model provider, getPreferred, the client boundary.
- V3  Generated: the scraps item model overrides and per-material models, en_us.json (+90 keys, original English but the recorded deviations).
- V4  Language: zh_cn.json and the mapping (84 upstream, 6 local), CRLF, insert-only, no '%'.
- V5  Resources: the textures the models reference, the ownership record, the three byte imports, the seven icons as 18x18 crops of the original
      potions.png (decoded pixels), and the two --check scripts.
- V6  Scope: every src/ and migration/ path changed since baseline.json belongs to the batch (tools/ listed separately); records not yet written
      are pending.
- V7  GameTest source (MaterialSystemGameTests) and with --gametest-log the log.
- V8  (--jar) the packaged JAR; "not run" without the flag.
- V9  In-memory mutations of the NEO inputs, the original text and the log (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal27a_material_system.py [--gametest-log PATH] [--jar PATH]
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
import struct
import subprocess
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal27a"
START = BATCH / "baseline-files"
INV = BATCH / "inventory"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "aee05a40f10fb7bb9b042b65eccaa449ecc1672d"
START_COMMIT = "71c2f660a6afece25d784edbd1bab5591344ffd3"

J = "src/main/java/com/hbm/"
M = J + "inventory/material/"
MATS, SHAPES, ENTRIES, DIST, NTMM = M + "Mats.java", M + "MaterialShapes.java", M + "MaterialEntries.java", M + "MatDistribution.java", M + "NTMMaterial.java"
CCR = J + "inventory/recipes/CopperCastingRecipes.java"
SER = J + "inventory/recipes/loader/SerializableRecipe.java"
SHRED = J + "inventory/recipes/ShredderRecipes.java"
CRU = J + "blockentity/machine/MachineCrucibleBlockEntity.java"
SCRAPS = J + "items/CopperScrapsItem.java"
CTAB = J + "inventory/NtmCreativeTabs.java"
IMP = J + "datagen/NtmItemModelProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
JEIH = J + "handler/jei/CrucibleSmeltingRecipeHandler.java"
JEIP = J + "handler/jei/NtmJeiPlugin.java"
ITEMS = J + "items/NtmItems.java"
BLOCKS = J + "blocks/NtmBlocks.java"
GT_DIR = J + "gametest/"
GT = GT_DIR + "MaterialSystemGameTests.java"
NEW_CLASSES = [ENTRIES, DIST, GT]
EDITED = [MATS, SHAPES, CCR, SER, SHRED, CRU, SCRAPS, CTAB, IMP, LP, JEIH, JEIP]
ENUMS = {"CastPlateItem": J + "items/CastPlateItem.java", "WireDenseItem": J + "items/WireDenseItem.java", "BoltItem": J + "items/BoltItem.java",
         "RawIngotItem": J + "items/RawIngotItem.java"}
# byte-identical to the start (hash in baseline.json)
UNCHANGED = list(ENUMS.values()) + [NTMM, J + "inventory/recipes/CrucibleRecipes.java", J + "inventory/recipes/CrucibleRecipe.java",
                                    J + "blockentity/machine/FoundryMoldBlockEntity.java", J + "lib/ModEffect.java", J + "items/ItemEnums.java",
                                    J + "inventory/RecipesCommon.java", J + "inventory/MetaHelper.java", J + "main/CommonEvents.java",
                                    J + "main/NuclearTechModClient.java", ITEMS, BLOCKS]
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal27a-resource-ownership.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
MODELS = GEN + "assets/hbmsntm/models/item/"
SCRAPS_MODEL = MODELS + "scraps.json"
RES = "src/main/resources/assets/hbmsntm/"
TEX = RES + "textures/item/"
ICONS = RES + "textures/mob_effect/"
JARRES = "src/main/resources/"

O = "src/main/java/com/hbm/"
O_FILES = dict(mats=O + "inventory/material/Mats.java", shapes=O + "inventory/material/MaterialShapes.java", dist=O + "inventory/material/MatDistribution.java",
               odm=O + "inventory/OreDictManager.java", cru=O + "tileentity/machine/TileEntityCrucible.java", scr=O + "items/machine/ItemScraps.java",
               auto=O + "items/special/ItemAutogen.java", shr=O + "inventory/recipes/ShredderRecipes.java", pot=O + "potion/HbmPotion.java",
               mi=O + "items/ModItems.java", rc=O + "inventory/RecipesCommon.java", mold=O + "items/machine/ItemMold.java",
               ser=O + "inventory/recipes/loader/SerializableRecipe.java", crr=O + "inventory/recipes/CrucibleRecipes.java")
O_LANG = "src/main/resources/assets/hbm/lang/"
O_TEX = "src/main/resources/assets/hbm/textures/"
O_ATLAS = O_TEX + "gui/potions.png"

GT_MARK = "[hbm-material]"
START_GAMETESTS = 280
GT_TESTS = ("material_table", "lookup", "crucible", "scraps", "shredder", "effect_icons")
HASH_SKIP = ("__pycache__",)
RECORDS_EXACT = {"migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                 "migration/GOAL27.md", "migration/GOAL27A.md", "migration/GOAL27A-ACCEPTANCE.md", MAP, ZH}
RECORDS_PREFIX = ("migration/goal27a-",)
RECORDS_REQUIRED = ["migration/README.md", "migration/features.json", "migration/UPSTREAM-REVIEWS.md", "migration/LOCALIZATION.md", "migration/FOUNDATIONS.md",
                    "migration/GOAL27A-ACCEPTANCE.md"]

# MatDistribution: NEO-only English / local Chinese decisions recorded by the language package (language-report.md)
EN_DEVIATIONS = {"hbmmat.mingrade": "Red Copper", "hbmmat.cmbsteel": "CMB Steel"}
LOCAL_KEYS = {"hbmmat.ilmenite", "hbmmat.coalcoke", "hbmmat.lignitecoke", "hbmmat.ghiorsium336", "hbmmat.polycarbonate", "casting.scraps.additive"}
ADDITIVE_TEXT = "Additive, not castable!"  # ItemScraps.java:113
# HbmPotion.java:49-62 icon tiles; the 1.7.10 inventory draws tile (x, y) of the 256x256 atlas at (x * 18, 198 + y * 18), 18x18
ICON_ORIGIN_Y, ICON_TILE = 198, 18
NEW_ICONS = ("mutation", "bang", "radx", "radaway", "stability", "potionsickness", "death")
OLD_ICONS = ("taint", "radiation", "lead", "phosphorus")


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
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:1500]))
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


# ---------------------------------------------------------------- text helpers (as verify_goal26d_medicine.py)

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


def sq(code):
    return squash_lit(code)


def method_span(text, signature):
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return found[0], open_index, match_brace(code, open_index), code


def body(text, signature):
    _, o, c, code = method_span(lf(text), signature)
    return sq(code[o + 1:c])


def drop_method(text, signature):
    """The text without the method (signature through closing brace), comments kept elsewhere."""
    text = lf(text)
    start, _, close, _ = method_span(text, signature)
    line_start = text.rfind("\n", 0, start) + 1
    return text[:line_start] + text[close + 1:]


@functools.lru_cache(maxsize=256)
def code_cached(text):
    return sq(blank_comments(text))


def code_of(text):
    return code_cached(lf(text))


def rep1(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new)


def parse_lang(text):
    d = {}
    for i, l in enumerate(lf(text).lstrip("﻿").split("\n"), 1):
        if "=" in l and not l.startswith("#"):
            k, v = l.split("=", 1)
            d.setdefault(k, []).append((v.rstrip("\r"), i))
    return d


def at_lines(lines, expected):
    return [(n, needle, lines[n - 1].strip()[:140] if n <= len(lines) else None) for n, needle in expected.items()
            if n > len(lines) or sq(needle) not in sq(lines[n - 1])]


def missing_order(code, *frags):
    pos = 0
    for f in frags:
        i = code.find(f, pos)
        if i < 0:
            return f
        pos = i + len(f)
    return None


def split_args(args):
    out, depth, cur, quote = [], 0, "", None
    for ch in args:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def call_args(code, start):
    """code[start] is '('; returns (inner text, index after the closing parenthesis)."""
    depth, j = 0, start
    while j < len(code):
        c = code[j]
        if c in "\"'":
            k = j + 1
            while k < len(code) and code[k] != c:
                k += 2 if code[k] == "\\" else 1
            j = k + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return code[start + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced (")


def java_int(token):
    token = token.strip().replace("_", "")
    if re.fullmatch(r"0[xX][0-9a-fA-F]+", token):
        return int(token, 16)
    if re.fullmatch(r"\d+", token):
        return int(token, 10)
    raise ValueError(token)


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


def run_check_script(name):
    proc = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tools/migration" / name), "--check"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout + proc.stderr)[-1500:]


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
    inp.o_atlas = (ORIGINAL / O_ATLAS).read_bytes()
    inp.o_tex = {n: (ORIGINAL / O_TEX / "items" / n).read_bytes() for n in ("scraps.png", "scraps_additive.png", "scraps_bismuth.png")}
    inp.inv = {n: json.loads((INV / n).read_text(encoding="utf-8")) for n in ("registry.json", "shredder_gap.json", "coverage.json", "materials.json")}
    inp.ores_txt = (INV / "matdistribution-ores.txt").read_text(encoding="utf-8")
    tree = hash_tree()
    files = {}
    load = set(NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, OWN, EN, STAMP] + RECORDS_REQUIRED)
    load |= {p for p in tree if p.startswith("src/main/java/") and p.endswith(".java")}
    load |= {p for p in tree if p.startswith(MODELS) and p.rsplit("/", 1)[1].startswith("scraps")}
    load |= {p for p in tree if (p.startswith(TEX) and p.rsplit("/", 1)[1].startswith("scraps")) or p.startswith(ICONS)}
    for p in load:
        if (ROOT / p).exists():
            files[p] = (ROOT / p).read_bytes()
    inp.gt_other = {p.name: read_text(p) for p in sorted((ROOT / GT_DIR).glob("*.java")) if p.name != Path(GT).name}
    status = subprocess.run(["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "tools"], cwd=ROOT, capture_output=True, text=True).stdout
    inp.tools_status = [x.strip() for x in status.splitlines() if x.strip()]
    inp.scripts = {n: run_check_script(n) for n in ("goal27a_scrap_textures.py", "goal27a_effect_icons.py")}
    return inp, State(files, tree)


def oline(inp, key, n):
    return sq(blank_comments(inp.ol[key][n - 1]))


# ---------------------------------------------------------------- original parsers

FACTORY_BEHAVIOUR = {"make": "NOT_SMELTABLE", "makeSmeltable": "SMELTABLE", "makeAdditive": "ADDITIVE", "makeNonSmeltable": "NOT_SMELTABLE"}
DEFAULT_COLOURS = (0xFF4A00, 0x802000, 0xFF4A00)  # NTMMaterial.java fields


def id_value(expr):
    total = 0
    for token in expr.split("+"):
        token = token.strip()
        total += {"_VS": 0, "_AS": 30, "_ES": 20000}[token] if token in ("_VS", "_AS", "_ES") else java_int(token)
    return total


def parse_decls(text, names_of):
    """Every active 'public static final NTMMaterial MAT_X = factory(...)...;' in declaration order."""
    out = []
    code = sq(blank_comments(lf(text)))
    for m in re.finditer(r"publicstaticfinalNTMMaterial(MAT_\w+)=(make\w*)\(", code):
        args, after = call_args(code, m.end() - 1)
        chain = code[after:code.index(";", after)]
        a = split_args(args)
        colours = [java_int(x) for x in a[2:]]
        colours = tuple(colours) if len(colours) == 3 else (colours[0],) * 3 if len(colours) == 1 else DEFAULT_COLOURS
        conv = re.search(r"\.setConversion\((MAT_\w+),(\d+),(\d+)\)", chain)
        auto = re.search(r"\.setAutogen\(([^)]*)\)", chain)
        trait = "METAL" if chain.endswith(".m()") else "NONMETAL" if chain.endswith(".n()") else None
        out.append(dict(field=m[1], factory=m[2], id=id_value(a[0]), names=names_of(a[1]), behaviour=FACTORY_BEHAVIOUR.get(m[2]), colours=colours,
                        conversion=(conv[1], int(conv[2]), int(conv[3])) if conv else None,
                        autogen=sorted(x for x in (auto[1].split(",") if auto and auto[1] else []) if x), trait=trait))
    return out


def orig_frames(inp):
    frames = {}
    code = sq(blank_comments(inp.o["odm"]))
    for m in re.finditer(r"publicstaticfinalDictFrame(\w+)=newDictFrame\(", code):
        args, _ = call_args(code, m.end() - 1)
        if "?" in args:  # GT6 ternary (OreDictManager.java:128): NEO does not port GT6, the else branch applies
            args = args.split(":", 1)[1]
        frames[m[1]] = [x.strip('"') for x in split_args(args)]
    return frames


def orig_materials(inp):
    frames = orig_frames(inp)

    def names(arg):
        m = re.fullmatch(r'df\("(\w+)"\)', arg)
        return [m[1]] if m else frames[arg]
    return parse_decls("\n".join(inp.ol["mats"][62:181]), names)


def neo_materials(text):
    def names(arg):
        m = re.fullmatch(r"names\((.*)\)", arg)
        return [x.strip('"') for x in split_args(m[1])]
    return parse_decls(text, names)


def parse_shapes(text):
    """[(field, quantity, prefixes, noAutogen)] from 'public static final MaterialShapes X = new MaterialShapes(...)'."""
    out, values = [], {}
    code = sq(blank_comments(lf(text)))
    for m in re.finditer(r"publicstaticfinalMaterialShapes(\w+)=newMaterialShapes\(", code):
        args, after = call_args(code, m.end() - 1)
        a = split_args(args)
        expr = re.sub(r"(\w+)\.quantity", lambda x: str(values[x[1]]), a[0])
        if not re.fullmatch(r"[\d*+]+", expr):
            raise ValueError(expr)
        q = eval(expr, {"__builtins__": {}}, {})  # noqa: S307 - digits and * + only
        values[m[1]] = q
        out.append((m[1], q, tuple(x.strip('"') for x in a[1:]), code[after:after + 13] == ".noAutogen()"))
    return out


def amount(expr, quantities):
    m = re.fullmatch(r"(\w+)\.q\((\d+)(?:,(\d+))?\)", expr)
    if not m:
        raise ValueError(expr)
    q = quantities[m[1]] * int(m[2])
    return q // int(m[3]) if m[3] else q


def pairs(args, quantities):
    return tuple((args[i], amount(args[i + 1], quantities)) for i in range(0, len(args), 2))


ORE_TXT = re.compile(r"^(\w+)\.ore\(\): (.*)$")


def ore_items(inp):
    out = {}
    for line in inp.ores_txt.splitlines():
        m = ORE_TXT.match(line.strip())
        if m:
            out[m[1]] = [x.strip() for x in m[2].split(",")]
    return out


def map_orig_key(key):
    simple = {"Blocks.obsidian": "Items.OBSIDIAN", "Blocks.rail": "Items.RAIL", "Blocks.golden_rail": "Items.POWERED_RAIL", "Blocks.detector_rail": "Items.DETECTOR_RAIL",
              "Items.minecart": "Items.MINECART", "newItemStack(Items.coal,1,1)": "Items.CHARCOAL",
              "DictFrame.fromOne(ModItems.chunk_ore,ItemEnums.EnumChunkType.CRYOLITE)": "NtmItems.CHUNK_CRYOLITE",
              "DictFrame.fromOne(ModBlocks.stone_resource,EnumStoneType.LIMESTONE)": "NtmBlocks.RESOURCE_LIMESTONE"}
    if key in simple:
        return simple[key]
    m = re.fullmatch(r"DictFrame\.fromOne\(ModItems\.casing,EnumCasingType\.(\w+)\)", key)
    if m:
        return f"newComparableStack(NtmItems.CASING.get(),1,CasingType.{m[1]})"
    m = re.fullmatch(r"DictFrame\.fromOne\(ModItems\.powder_ash,EnumAshType\.(\w+)\)", key)
    if m:
        return f"NtmItems.POWDER_ASH_{m[1]}"
    m = re.fullmatch(r"ModItems\.(\w+)", key)
    if m:
        return "NtmItems." + m[1].upper()
    raise ValueError(key)


def orig_distribution(inp, quantities):
    """MatDistribution.java:39-95 as NEO rows {neo key: materials}; pipes_steel (:59, deprecated) and the second minecart (:65) dropped."""
    ores = ore_items(inp)
    rows, raw = [], []
    for n in range(39, 96):
        line = oline(inp, "dist", n)
        m = re.fullmatch(r'registerOre\("(\w+)",(.*)\);', line)
        if m:
            raw.append((n, "ore:" + m[1], m[2]))
            rows.append(({"stone": "Items.STONE", "cobblestone": "Items.COBBLESTONE"}[m[1]], pairs(split_args(m[2]), quantities)))
            continue
        m = re.fullmatch(r"registerOre\(OreDictManager\.(\w+)\.ore\(\),(.*)\);", line) or \
            re.fullmatch(r"for\(Stringore:OreDictManager\.(\w+)\.all\(MaterialShapes\.ONLY_ORE\)\)registerOre\(ore,(.*)\);", line)
        if m:
            raw.append((n, "frame:" + m[1], m[2]))
            for item in ores[m[1]]:
                rows.append((item, pairs(split_args(m[2]), quantities)))
            continue
        m = re.fullmatch(r"registerEntry\((.*)\);", line)
        if m:
            a = split_args(m[1])
            raw.append((n, a[0], ",".join(a[1:])))
            if a[0] == "ModItems.pipes_steel":
                continue
            key = map_orig_key(a[0])
            row = (key, pairs(a[1:], quantities))
            if row in rows:
                continue
            rows.append(row)
    return rows, raw


def neo_distribution(text, quantities):
    code = body(text, "public void registerDefaults()")
    rows = []
    loops = list(re.finditer(r"for\(ItemLikeore:ores\(([^)]*)\)\)\{?registerEntry\(ore,(.*?)\);\}?", code))
    rest = code
    for m in loops:
        for item in split_args(m[1]):
            rows.append((item, pairs(split_args(m[2]), quantities)))
        rest = rest.replace(m[0], "", 1)
    for m in re.finditer(r"registerEntry\(((?:[^;])*?)\);", rest):
        a = split_args(m[1])
        rows.append((a[0], pairs(a[1:], quantities)))
    return rows


def id_maps(st):
    out = {}
    for path, kind in ((ITEMS, "NtmItems"), (BLOCKS, "NtmBlocks")):
        code = sq(blank_comments(st.text(path)))
        for m in re.finditer(r"(?:publicstaticfinal)[\w<>,?]+?([A-Z][A-Z0-9_]*)=[\w.]+\(\"([a-z0-9_]+)\"", code):
            out.setdefault(f"{kind}.{m[1]}", "hbmsntm:" + m[2])
    return out


def enum_metas(st):
    out = {}
    for cls, path in ENUMS.items():
        code = sq(blank_comments(st.text(path)))
        m = re.search(r"publicenumType\{(.*?);", code)
        consts = re.findall(r"([A-Z][A-Z0-9_]*)\(([^,()]+)", m[1])
        for i, (name, first) in enumerate(consts):
            out[f"{cls}.Type.{name}.ordinal()"] = i
            if re.fullmatch(r"\d+", first):
                out[f"{cls}.Type.{name}.meta"] = int(first)
    return out


def item_id(expr, ids):
    expr = expr.replace(".get()", "")
    m = re.fullmatch(r"Items\.(\w+)", expr)
    if m:
        return "minecraft:" + m[1].lower()
    if expr in ids:
        return ids[expr]
    raise ValueError(expr)


def neo_entries(st):
    """MaterialEntries.Table rows: [(material field, shape, item id, meta)] in order."""
    code = body(st.text(ENTRIES), "static {")
    ids, metas = id_maps(st), enum_metas(st)
    rows = []
    for m in re.finditer(r"add\(Mats\.(MAT_\w+),MaterialShapes\.(\w+),([^;]*?)\);", code):
        a = split_args(m[3])
        rows.append((m[1], m[2], item_id(a[0], ids), metas[a[1]] if len(a) > 1 else 0))
    return rows


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:9]} with a clean worktree", (head, status))
    bad = [p for p, v in inp.start_hash_ok.items() if not v]
    ck("V0.baseline-copies-match", not bad and len(inp.start_hash_ok) == len(inp.baseline["copied_scope"]) and all(p in inp.start for p in inp.baseline["copied_scope"]),
       f"every baseline-files copy ({len(inp.start_hash_ok)}) hashes to its baseline.json entry", bad[:5])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD and inp.baseline.get("target_head") == START_COMMIT,
       "baseline.json records the original HEAD aee05a40f and the NEO start commit 71c2f660", (inp.baseline.get("source_head"), inp.baseline.get("target_head")))
    ck("V0.neo-head", inp.neo_head == START_COMMIT, "NEO HEAD is still the start commit 71c2f660 (the batch is uncommitted)", inp.neo_head)
    needed = NEW_CLASSES + EDITED + UNCHANGED + [ZH, MAP, EN, STAMP, SCRAPS_MODEL]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the new, modified, unchanged-reference and generated NEO files exist", [p for p in needed if not st.has(p)][:6])
    starts = [p for p in [MATS, SHAPES, CCR, SER, SHRED, CRU, SCRAPS, CTAB, IMP, LP, JEIH, JEIP, ZH, MAP, EN, SCRAPS_MODEL] if not inp.start.get(p)]
    ck("V0.start-copies-of-edited", not starts, "the start copy of every edited file exists in baseline-files", starts)
    ck("V0.inventory", len(inp.inv["registry.json"]) == 375 and len(inp.inv["shredder_gap.json"]) == 14 and len(inp.inv["materials.json"]) == 109,
       "the inventory tables: registry.json 375 rows, shredder_gap.json 14 rows, materials.json 109",
       (len(inp.inv["registry.json"]), len(inp.inv["shredder_gap.json"]), len(inp.inv["materials.json"])))


# ---------------------------------------------------------------- V1

ANCHORS = {
    "mats": {44: "public static List<NTMMaterial> orderedList = new ArrayList();", 63: "//Vanilla and vanilla-like", 88: "//Radioactive", 117: "//Base metals",
             152: "//Alloys", 155: "// public static final NTMMaterial MAT_ALLOY", 175: "//Extension",
             192: "public static NTMMaterial make(int id, DictFrame dict) {", 193: "return new NTMMaterial(id, dict);",
             213: "public static List<MaterialStack> getMaterialsFromItem(ItemStack stack) {", 221: "List<MaterialStack> oreEntries = materialOreEntries.get(name);",
             224: "list.addAll(oreEntries);", 225: "break outer;", 228: "for(Entry<String, MaterialShapes> prefixEntry : prefixByName.entrySet()) {",
             235: "if(material != null && (material.smeltsInto.smeltable == SmeltingBehavior.SMELTABLE || material.smeltsInto.smeltable == SmeltingBehavior.ADDITIVE)) {",
             236: "list.add(new MaterialStack(material, prefixEntry.getValue().q(1)));", 244: "List<MaterialStack> entries = materialEntries.get(new ComparableStack(stack).makeSingular());",
             250: "if(stack.getItem() == ModItems.scraps) {", 251: "list.add(ItemScraps.getMats(stack));",
             257: "public static List<MaterialStack> getSmeltingMaterialsFromItem(ItemStack stack) {",
             260: "baseMats.forEach(x -> smelting.add(new MaterialStack(x.material.smeltsInto, (int) (x.amount * x.material.convOut / x.material.convIn))));"},
    "shapes": {31: 'public static final MaterialShapes ANY = new MaterialShapes(0, "any").noAutogen();', 34: 'ORENETHER = new MaterialShapes(0, "oreNether").noAutogen();',
               63: 'public static final MaterialShapes GRIP =			new MaterialShapes(INGOT.quantity * 2, "grip");', 102: "Mats.prefixByName.put(prefix, this);"},
    "dist": {41: 'registerOre("stone", MAT_STONE, BLOCK.q(1));', 59: "registerEntry(ModItems.pipes_steel,", 65: "registerEntry(Items.minecart, MAT_IRON, INGOT.q(5));",
             68: "if(!Compat.isModLoaded(Compat.MOD_GT6)) {", 69: "registerOre(OreDictManager.IRON.ore(), MAT_IRON, INGOT.q(2), MAT_TITANIUM, NUGGET.q(3), MAT_STONE, QUART.q(1));",
             88: "registerEntry(DictFrame.fromOne(ModBlocks.stone_resource, EnumStoneType.LIMESTONE), MAT_FLUX, DUST.q(10));",
             90: "registerEntry(new ItemStack(Items.coal, 1, 1), MAT_CARBON, NUGGET.q(3));", 135: 'return "hbmCrucibleSmelting.json";'},
    "cru": {64: "public static int recipeZCapacity = MaterialShapes.BLOCK.q(16);", 65: "public static int wasteZCapacity = MaterialShapes.BLOCK.q(16);",
            66: "public static int processTime = 20_000;", 68: "public static int maxHeat = 100_000;", 375: "if(this.heat < maxHeat / 2) return false;",
            380: "int delta = this.heat - (maxHeat / 2);", 381: "delta *= 0.05;",
            389: "List<MaterialStack> materials = Mats.getSmeltingMaterialsFromItem(slots[slot]);", 392: "for(MaterialStack material : materials) {",
            393: "boolean recipeMaterial = recipe != null && (getQuantaFromType(recipe.input, material.material) > 0 || getQuantaFromType(recipe.output, material.material) > 0);",
            455: "public boolean isItemSmeltable(ItemStack stack) {", 457: "List<MaterialStack> materials = Mats.getSmeltingMaterialsFromItem(stack);",
            460: "if(materials.isEmpty()) return false;", 472: "for(MaterialStack mat : materials) {",
            489: "int matMaximum = recipeInputRequired * this.recipeZCapacity / recipeContent;",
            502: "return recipeAmount <= this.recipeZCapacity && wasteAmount <= this.wasteZCapacity && matchesRecipe;"},
    "scr": {49: "if(mat.smeltable == SmeltingBehavior.SMELTABLE || mat.smeltable == SmeltingBehavior.ADDITIVE) {", 64: "return mat.moltenColor;",
            113: 'if(contents.material.smeltable == contents.material.smeltable.ADDITIVE) list.add(EnumChatFormatting.DARK_RED + "Additive, not castable!");'},
    "auto": {59: "if(!textureOverrides.containsKey(mat) && mat.solidColorLight != mat.solidColorDark && (shape == null || mat.autogen.contains(shape))) {",
             105: "return 0xffffff; //custom textures don't need tints", 111: "return mat.moltenColor;"},
    "mi": {2765: 'scraps = new ItemScraps().aot(Mats.MAT_BISMUTH, "scraps_bismuth").setUnlocalizedName("scraps")'},
    "shr": {60: 'generateRecipes("ingot", name, matches, 1);', 61: 'generateRecipes("plate", name, matches, 1);', 63: 'generateRecipes("gem", name, matches, 1);',
            64: 'generateRecipes("crystal", name, matches, 1);', 66: 'generateRecipes("ore", name, matches, 2);'},
    "odm": {128: 'public static final DictFrame U = new DictFrame(Compat.isModLoaded(Compat.MOD_GT6) ? "Uraninite" : "Uranium");', 335: "COAL.gem(Items.coal).dustSmall(powder_coal_tiny).dust(powder_coal);",
            550: "if(mat.autogen.contains(MaterialShapes.INGOT)) for(String name : mat.names) OreDictionary.registerOre(MaterialShapes.INGOT.name() + name, new ItemStack(ModItems.ingot_raw, 1, mat.id));"},
    "rc": {99: "this.meta = stack.getItemDamage();"},
    "mold": {201: "if(registry.startsWith(RefStrings.MODID)) {", 202: 'if(registry.contains("fragment")) continue; // deprioritize fragments'},
    "ser": {91: "recipeHandlers.add(CrucibleRecipes.INSTANCE);", 103: "recipeHandlers.add(new MatDistribution());"},
    "crr": {91: 'this.register(new CrucibleRecipe("crucible.hss").setup(9, new ItemStack(ModItems.ingot_dura_steel))',
            92: ".inputs(new MaterialStack(Mats.MAT_STEEL, n * 5), new MaterialStack(Mats.MAT_TUNGSTEN, n * 3), new MaterialStack(Mats.MAT_COBALT, n * 1))",
            93: ".outputs(new MaterialStack(Mats.MAT_DURA, n * 9)));"},
}


def orig_potions(inp):
    out = {}
    for n in range(49, 63):
        m = re.fullmatch(r'\w+=registerPotion\(PotionConfig\.\w+,(true|false),0x\w+,"potion\.hbm_(\w+)",(\d+),(\d+)\);', oline(inp, "pot", n))
        if m:
            out[m[2]] = (int(m[3]), int(m[4]))
    return out


def orig_hbmmat(inp, lang):
    return {k: v for k, v in lang.items() if k.startswith("hbmmat.")}


def v1_original(ck, inp, st):
    for key, expected in ANCHORS.items():
        miss = at_lines(inp.ol[key], expected)
        ck(f"V1.{key}", not miss, f"{O_FILES[key].rsplit('/', 1)[1]}: the {len(expected)} cited lines hold their text", miss[:4])
    mats = orig_materials(inp)
    ck("V1.materials", len(mats) == 109 and len({m["id"] for m in mats}) == 109 and mats[0]["field"] == "MAT_WOOD" and mats[-1]["field"] == "MAT_PVC",
       "Mats.java:63-181 declares 109 active materials with unique IDs, MAT_WOOD first and MAT_PVC last (MAT_ALLOY commented out)", (len(mats), mats[:1], mats[-1:]))
    conv = [(m["field"], m["conversion"]) for m in mats if m["conversion"]]
    ck("V1.conversions", conv == [("MAT_COAL", ("MAT_CARBON", 2, 1)), ("MAT_LIGNITE", ("MAT_CARBON", 3, 1)), ("MAT_COALCOKE", ("MAT_CARBON", 4, 3)),
                                  ("MAT_PETCOKE", ("MAT_CARBON", 4, 3)), ("MAT_LIGCOKE", ("MAT_CARBON", 4, 3)), ("MAT_GRAPHITE", ("MAT_CARBON", 1, 1)),
                                  ("MAT_DIAMOND", ("MAT_CARBON", 1, 1)), ("MAT_EMERALD", ("MAT_BERYLLIUM", 4, 3))],
       "the eight conversions of Mats.java:68-74,129", conv)
    sm = [m for m in mats if m["behaviour"] in ("SMELTABLE", "ADDITIVE")]
    ck("V1.scrap-materials", len(sm) == 82, "82 SMELTABLE / ADDITIVE materials (ItemScraps.java:49)", len(sm))
    by = {m["field"]: m for m in mats}
    ck("V1.spot", (by["MAT_FERRO"]["id"], by["MAT_U238"]["id"], by["MAT_U238"]["names"], by["MAT_MINGRADE"]["id"], by["MAT_FLUX"]["id"], by["MAT_FLUX"]["behaviour"],
                   by["MAT_SLAG"]["id"], by["MAT_BSCCO"]["id"]) == (37, 9238, ["Uranium238", "U238"], 31, 40, "ADDITIVE", 41, 48),
       "spot values: FERRO 37, U238 9238 (Uranium238, U238), MINGRADE 31, FLUX 40 additive, SLAG 41, BSCCO 48")
    shapes = parse_shapes(inp.o["shapes"])
    ck("V1.shapes", len(shapes) == 31 and dict((f, q) for f, q, _, _ in shapes)["BLOCK"] == 648 and dict((f, q) for f, q, _, _ in shapes)["QUART"] == 162,
       "MaterialShapes.java:31-63: 31 shapes (with ORENETHER), BLOCK 648, QUART 162", [(f, q) for f, q, _, _ in shapes])
    rows, raw = orig_distribution(inp, {f: q for f, q, _, _ in shapes})
    ck("V1.distribution", len(raw) == 44 and len(rows) == 60, "MatDistribution.java:39-95 holds 44 registrations; mapped to NEO keys they are 60 rows (pipes_steel and the second minecart dropped)",
       (len(raw), len(rows)))
    pots = orig_potions(inp)
    ck("V1.potions", pots == {"taint": (0, 0), "radiation": (1, 0), "bang": (3, 0), "mutation": (2, 0), "radx": (5, 0), "lead": (6, 0), "radaway": (7, 0),
                              "phosphorus": (1, 1), "stability": (2, 1), "potionsickness": (3, 1), "death": (4, 1)}, "HbmPotion.java:50-61: the eleven icon tiles", pots)
    en, zh = orig_hbmmat(inp, inp.o_en), orig_hbmmat(inp, inp.o_zh)
    lines = sorted(v[0][1] for v in en.values())
    ck("V1.lang", len(en) == 118 and len(zh) == 116 and lines[0] == 1616 and lines[-1] == 1733 and all(len(v) == 1 for v in en.values()),
       "en_US.lang:1616-1733 holds 118 hbmmat keys once each, zh_CN.lang 116", (len(en), len(zh), lines[:1], lines[-1:]))
    names = {"hbmmat." + m["names"][0].lower() for m in mats}
    ck("V1.lang-covers-materials", names <= set(en) and len(names - set(zh)) == 1 and (names - set(zh)) == {"hbmmat.ilmenite"},
       "every material's hbmmat key is in en_US.lang; zh_CN.lang lacks only hbmmat.ilmenite", (sorted(names - set(en)), sorted(names - set(zh))))


# ---------------------------------------------------------------- V2 NEO source vs original

CLIENT_WORDS = ("net.minecraft.client", "com.mojang.blaze3d", "mezz.jei", "com.hbm.handler.jei", "com.hbm.render", "NuclearTechModClient", "Dist.CLIENT", "OnlyIn")
CLIENT_FREE = [MATS, ENTRIES, DIST, CCR, CRU, SCRAPS, SHAPES, NTMM]


def v2_source(ck, inp, st):
    o_mats, n_mats = orig_materials(inp), neo_materials(st.text(MATS))
    ck("V2.material-count", len(n_mats) == 109, "Mats.java declares 109 materials", len(n_mats))
    ck("V2.material-order", [m["field"] for m in n_mats] == [m["field"] for m in o_mats], "the NEO declaration order is the original's (orderedList order)",
       [(a["field"], b["field"]) for a, b in zip(o_mats, n_mats) if a["field"] != b["field"]][:4])
    by = {m["field"]: m for m in n_mats}
    for key in ("id", "names", "behaviour", "colours", "conversion", "autogen", "trait"):
        bad = [(m["field"], m[key], (by.get(m["field"]) or {}).get(key)) for m in o_mats if (by.get(m["field"]) or {}).get(key) != m[key]]
        ck(f"V2.material-{key}", not bad, f"every material's {key} equals the original declaration (Mats.java:63-181)", bad[:4])
    mats = st.text(MATS)
    mk = body(mats, "public static NTMMaterial make(int id, String[] names)")
    miss = missing_order(mk, "material.id=id;", "material.names=names;", "material.setConversion(material,1,1);", "NTMMaterialtaken=matById.get(id);",
                         "if(taken!=null){thrownewIllegalStateException(", "for(Stringname:names){matByName.put(name,material);}", "orderedList.add(material);", "matById.put(id,material);")
    ck("V2.make", miss is None, "make(): smeltsInto = itself 1 -> 1, a duplicate ID throws before anything is registered, every alias goes into matByName (NTMMaterial(int, DictFrame))", miss)
    for fac, beh in (("makeSmeltable", "SMELTABLE"), ("makeAdditive", "ADDITIVE"), ("makeNonSmeltable", "NOT_SMELTABLE")):
        b = body(mats, f"public static NTMMaterial {fac}(int id, String[] names, int solidColorLight, int solidColorDark, int moltenColor)")
        ck(f"V2.{fac}", b == f"returnmake(id,names).smeltable(SmeltingBehavior.{beh}).setSolidColor(solidColorLight,solidColorDark).setMoltenColor(moltenColor);",
           f"{fac} = make + {beh} + colours (Mats.java:196-206)", b)
    gm = body(mats, "public static List<MaterialStack> getMaterialsFromItem(ItemStack stack)")
    miss = missing_order(gm, "materialOreEntries.get(it.next().location().toString());", "list.add(x.copy());", "tagMatched=true;break;",
                         "if(!tagMatched){for(MaterialEntries.Entryentry:MaterialEntries.getEntries(stack)){",
                         "if(material.smeltsInto.smeltable==SmeltingBehavior.SMELTABLE||material.smeltsInto.smeltable==SmeltingBehavior.ADDITIVE){list.add(newMaterialStack(material,entry.shape().q(1)));break;}",
                         "List<MaterialStack>entries=stack.isDamaged()?null:materialEntries.get(newComparableStack(stack).makeSingular());",
                         "MaterialStackscraps=CopperScrapsItem.getMats(stack);", "returnlist;")
    ck("V2.lookup-order", miss is None, "getMaterialsFromItem: tag entries (first hit replaces the prefix step), else the first SMELTABLE / ADDITIVE MaterialEntries row at shape.q(1), then the item "
       "entries (skipped for a damaged stack: upstream ComparableStack meta = damage, RecipesCommon.java:99), then the scraps (Mats.java:217-252)", miss)
    o_sm = re.sub(r"newArrayList\(\)", "newArrayList<>()", sq(blank_comments("\n".join(inp.ol["mats"][257:261]))))
    ck("V2.smelting-conversion", body(mats, "public static List<MaterialStack> getSmeltingMaterialsFromItem(ItemStack stack)") == o_sm,
       "getSmeltingMaterialsFromItem is the original's integer conversion (Mats.java:258-261)", (body(mats, "public static List<MaterialStack> getSmeltingMaterialsFromItem(ItemStack stack)"), o_sm))
    ck("V2.prefix-map-shared", "publicstaticfinalHashMap<String,MaterialShapes>prefixByName=MaterialShapes.PREFIX_BY_NAME;" in code_of(mats)
       and "PREFIX_BY_NAME.put(prefix,this);" in code_of(st.text(SHAPES)) and "Mats." not in code_of(st.text(SHAPES)),
       "Mats.prefixByName is MaterialShapes.PREFIX_BY_NAME and the MaterialShapes constructor does not touch Mats (class-init cycle)")

    # MaterialShapes: the start's shapes, the original's quantities
    o_sh, n_sh, s_sh = parse_shapes(inp.o["shapes"]), parse_shapes(st.text(SHAPES)), parse_shapes(inp.start[SHAPES])
    ck("V2.shapes-unchanged", n_sh == s_sh, "MaterialShapes constants, quantities, prefixes and noAutogen flags are unchanged from the start", [x for x in n_sh if x not in s_sh][:4])
    oq = {f: q for f, q, _, _ in o_sh}
    ck("V2.shapes-quantities", all(oq.get(f) == q for f, q, _, _ in n_sh) and {f for f, *_ in o_sh} - {f for f, *_ in n_sh} == {"ORENETHER"},
       "every NEO shape has the original quantity (MaterialShapes.java:31-63); only ORENETHER is not ported", [(f, q, oq.get(f)) for f, q, _, _ in n_sh if oq.get(f) != q])

    # MatDistribution
    nq = {f: q for f, q, _, _ in n_sh}
    o_rows, _ = orig_distribution(inp, oq)
    n_rows = neo_distribution(st.text(DIST), nq)
    ck("V2.distribution-count", len(n_rows) == 60 and len(set(r[0] for r in n_rows)) == 60, "MatDistribution.registerDefaults registers 60 distinct keys", len(n_rows))
    ck("V2.distribution-rows", sorted(n_rows) == sorted(o_rows), "every default row equals the original row (MatDistribution.java:41-94) for its NEO key, with the "
       "ore rows on every NEO ore item of matdistribution-ores.txt; pipes_steel skipped, the minecart once, no GT6 branch",
       (sorted(set(n_rows) - set(o_rows))[:3], sorted(set(o_rows) - set(n_rows))[:3]))
    dist = code_of(st.text(DIST))
    ck("V2.distribution-file", 'return"hbmCrucibleSmelting.json";' in dist and "Mats.materialEntries.clear();Mats.materialOreEntries.clear();" in dist and "MOD_GT6" not in dist,
       "MatDistribution uses hbmCrucibleSmelting.json (MatDistribution.java:135), deleteRecipes clears both maps, no GT6 branch")
    rr = body(st.text(DIST), "public void readRecipe(JsonElement recipe)")
    ck("V2.distribution-reader", "if(material==null){" in rr and "continue;" in rr and "thrownewIllegalArgumentException(" in rr,
       "readRecipe skips unknown materials and refuses an unknown item (the lenient reader skips the row)", rr[:300])
    ser = code_of(st.text(SER))
    i_cr, i_md = ser.find("recipeHandlers.add(CrucibleRecipes.INSTANCE);"), ser.find("recipeHandlers.add(newMatDistribution());")
    ck("V2.handler-order", 0 <= i_cr < i_md and ser.count("newMatDistribution()") == 1, "SerializableRecipe registers MatDistribution once, after CrucibleRecipes (SerializableRecipe.java:91,103)", (i_cr, i_md))

    # MaterialEntries vs inventory/registry.json
    rows = neo_entries(st)
    want = [(r["material"], r["shape"], r["item"], r["meta"] or 0) for r in inp.inv["registry.json"]]
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(rows, want)) if a != b]
    ck("V2.entries-table", rows == want, f"MaterialEntries has the {len(want)} rows of inventory/registry.json (material, shape, item, meta) in order", (len(rows), len(want), diff[:3]))
    neo_only = [r for r in inp.inv["registry.json"] if r.get("neo_only")]
    ck("V2.entries-neo-only", len(neo_only) == 5 and all("ORE" not in r["shape"] for r in inp.inv["registry.json"]),
       "5 NEO-only rows and no ORE / ONLY_ORE / ANY row (decision 1: ores melt only through MatDistribution)", [r["item"] for r in neo_only])
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    cov = {c["material"]: c["count"] for c in inp.inv["coverage.json"]["coverage"]}
    ck("V2.entries-coverage", all(counts.get(k, 0) == v for k, v in cov.items()) and sum(1 for v in counts.values() if v) == 98,
       "per-material row counts equal coverage.json; 98 materials have rows", [(k, counts.get(k, 0), v) for k, v in cov.items() if counts.get(k, 0) != v][:5])
    me = st.text(ENTRIES)
    ck("V2.entries-air-guard", "if(resolved==Items.AIR){thrownewIllegalStateException(" in code_of(me), "a row that resolves to air throws instead of matching every empty stack")
    gp = body(me, "public static ItemStack getPreferred(MaterialShapes shape, NTMMaterial material)")
    miss = missing_order(gp, "if(first==null)first=entry;", "if(id.getNamespace().equals(NuclearTechMod.MODID)&&!id.getPath().contains(\"fragment\"))returnentry.stack(1);",
                         "returnfirst==null?ItemStack.EMPTY:first.stack(1);")
    ck("V2.preferred", miss is None, "getPreferred: the first hbmsntm row that is not a fragment, else the first row (ItemMold.java:199-210)", miss)

    # crucible
    cru = st.text(CRU)
    ts = body(cru, "private boolean trySmelt()")
    miss = missing_order(ts, "if(this.heat<MAX_HEAT/2)returnfalse;", "intdelta=(int)((this.heat-MAX_HEAT/2)*0.05D);", "if(this.progress>=PROCESS_TIME){this.progress=0;",
                         "List<Mats.MaterialStack>materials=CopperCastingRecipes.getMaterials(this.slots.get(slot));",
                         "for(Mats.MaterialStackmaterial:materials){booleanrecipeMaterial=recipe!=null&&(recipe.getInputAmount(material.material)>0||recipe.hasOutput(material.material));"
                         "addToStack(recipeMaterial?this.recipeStack:this.wasteStack,material);}", "this.slots.get(slot).shrink(1);")
    ck("V2.crucible-trysmelt", miss is None, "trySmelt: every material of the item goes to the recipe stack if the recipe uses or makes it, else to the waste stack, then one item is "
       "consumed (TileEntityCrucible.java:375-402)", miss)
    sm = body(cru, "public boolean isItemSmeltable(ItemStack stack)")
    miss = missing_order(sm, "List<Mats.MaterialStack>materials=CopperCastingRecipes.getMaterials(stack);", "if(materials.isEmpty())returnfalse;", "booleanmatchesRecipe=recipe==null;",
                         "intrecipeAmount=getQuantaFromType(this.recipeStack,null);", "intwasteAmount=getQuantaFromType(this.wasteStack,null);",
                         "for(Mats.MaterialStackmaterial:materials){if(recipe!=null&&recipe.hasOutput(material.material)){recipeAmount+=material.amount;matchesRecipe=true;continue;}",
                         "intrecipeInputRequired=recipe!=null?recipe.getInputAmount(material.material):0;", "if(recipeInputRequired==0){wasteAmount+=material.amount;}else{",
                         "intmatMaximum=(int)((long)recipeInputRequired*CAPACITY/recipe.getInputAmount());", "intamountStored=getQuantaFromType(this.recipeStack,material.material);",
                         "matchesRecipe=true;recipeAmount+=material.amount;if(amountStored+material.amount>matMaximum)returnfalse;}}",
                         "returnrecipeAmount<=CAPACITY&&wasteAmount<=CAPACITY&&matchesRecipe;")
    ck("V2.crucible-smeltable", miss is None, "isItemSmeltable: the per-material loop of TileEntityCrucible.java:455-503 (outputs poured back, waste for non-recipe materials, per-input "
       "cap required * capacity / content, both capacities)", miss)
    ck("V2.crucible-sync-bound", "privatestaticfinalintMAX_SYNC_ENTRIES=Mats.orderedList.size();" in code_of(cru) and "if(size<0||size>MAX_SYNC_ENTRIES)" in code_of(cru),
       "MAX_SYNC_ENTRIES = Mats.orderedList.size() bounds the synced stack size (a stack can hold more than 64 materials)")
    ck("V2.crucible-constants", "publicstaticfinalintCAPACITY=MaterialShapes.BLOCK.q(16);" in code_of(cru) and "publicstaticfinalintMAX_HEAT=100_000;" in code_of(cru)
       and "publicstaticfinalintPROCESS_TIME=20_000;" in code_of(cru), "CAPACITY BLOCK.q(16), MAX_HEAT 100_000, PROCESS_TIME 20_000 (TileEntityCrucible.java:64-68)")

    def rest(text):
        t = lf(text)
        for sig in ("private boolean trySmelt()", "public boolean isItemSmeltable(ItemStack stack)"):
            t = drop_method(t, sig)
        return re.sub(r"[ \t]*/\*\*(?:(?!\*/).)*\*/\s*private static final int MAX_SYNC_ENTRIES = [^;]*;\n", "", t, flags=re.S)
    a, b = rest(inp.start[CRU]), rest(cru)
    ck("V2.crucible-rest-unchanged", a == b, "apart from trySmelt, isItemSmeltable and the MAX_SYNC_ENTRIES declaration the crucible is identical to the start (constants, save keys "
       "recipe / rec / was / progress / heat, the legacy copper key, readStack and the sync codec)",
       [l for l in difflib.unified_diff(a.split("\n"), b.split("\n"), lineterm="", n=0)][:8])

    # unchanged files
    changed = [p for p in UNCHANGED if inp.base_files.get(p) is None or st.tree.get(p) != inp.base_files.get(p)]
    ck("V2.unchanged", not changed, "CastPlateItem / WireDenseItem / BoltItem / RawIngotItem, NTMMaterial, CrucibleRecipe(s), FoundryMoldBlockEntity, ModEffect, ItemEnums, "
       "RecipesCommon, MetaHelper, CommonEvents, NuclearTechModClient, NtmItems and NtmBlocks are byte-identical to the start", changed)

    # shredder
    lookups = ("public static ItemStack getShredderResult(ItemStack stack)", "public static boolean hasRecipe(ItemStack stack)")
    s0, s1 = lf(inp.start[SHRED]), lf(st.text(SHRED))
    for sig in lookups:
        s0, s1 = drop_method(s0, sig), drop_method(s1, sig)
    s0, s1 = s0.split("\n"), s1.split("\n")
    gr, hr = body(st.text(SHRED), lookups[0]), body(st.text(SHRED), lookups[1])
    ck("V2.shredder-exact-lookup", "WILDCARD" not in gr + hr and "ItemStackresult=RECIPES.get(key);" in gr and "returnresult==null?newItemStack(NtmItems.DUST.get()):result.copy();" in gr
       and hr.endswith("returnRECIPES.containsKey(newComparableStack(stack).makeSingular());"),
       "getShredderResult / hasRecipe use the exact lookup only: NEO's ComparableStack.hashCode has no meta (RecipesCommon.java:107-113), so a wildcard retry would match another "
       "meta's row; the original's meta-aware hashCode (RecipesCommon.java:202) lets its retry (ShredderRecipes.java:437-445) find only wildcard rows", (gr, hr))
    ops = difflib.SequenceMatcher(None, s0, s1, autojunk=False).get_opcodes()
    removed = [s0[i1:i2] for tag, i1, i2, j1, j2 in ops if tag in ("replace", "delete")]
    added = [l for tag, i1, i2, j1, j2 in ops if tag in ("replace", "insert") for l in s1[j1:j2]]
    ck("V2.shredder-insert-only", not removed, "ShredderRecipes outside the two lookup methods: no start line was changed or removed (existing rows unchanged)", removed[:3])
    ids, metas = id_maps(st), enum_metas(st)
    got, other = set(), []
    for line in added:
        c = sq(blank_comments(line))
        if not c or c.startswith("import"):
            continue
        m = re.fullmatch(r"registerIfAbsent\((.*)\);", c)
        if not m:
            other.append(line.strip())
            continue
        a = split_args(m[1])
        inm = re.fullmatch(r"newItemStack\(([\w.()]+)\)", a[0]) or re.fullmatch(r"MetaHelper\.newStack\(([\w.()]+),([\w.()]+)\)", a[0])
        outm = re.fullmatch(r"newItemStack\(([\w.()]+),(\d+)\)", ",".join(a[1:]))
        if not inm or not outm:
            other.append(line.strip())
            continue
        meta = metas.get(inm[2]) if inm.lastindex == 2 else 0
        got.add((item_id(inm[1], ids), meta, item_id(outm[1], ids), int(outm[2])))
    want = {(r["input"], r["meta"] or 0, r["output"], 1) for r in inp.inv["shredder_gap.json"]}
    ck("V2.shredder-rows", got == want and not other and len(want) == 14, "the appended rows are exactly the 14 rows of shredder_gap.json, each 1 dust (ShredderRecipes.java:60-64 "
       "ingot / plate / gem / crystal -> 1)", (sorted(got ^ want)[:4], other[:3]))

    # scraps
    sc = st.text(SCRAPS)
    scc = code_of(sc)
    ck("V2.scraps-model-materials", "publicstaticfinalList<NTMMaterial>MODEL_MATERIALS=Mats.orderedList.stream().filter(material->material!=Mats.MAT_COPPER&&isScrapMaterial(material)).toList();" in scc,
       "MODEL_MATERIALS = the SMELTABLE / ADDITIVE materials in orderedList order without copper (ItemScraps.java:47-49; copper keeps the Goal 5A model)")
    ck("V2.scraps-filter", body(sc, "public static boolean isScrapMaterial(NTMMaterial material)")
       == "returnmaterial.smeltable==NTMMaterial.SmeltingBehavior.SMELTABLE||material.smeltable==NTMMaterial.SmeltingBehavior.ADDITIVE;",
       "isScrapMaterial = SMELTABLE or ADDITIVE (ItemScraps.java:49)")
    ck("V2.scraps-model-values", "publicstaticfinalfloatADDITIVE_LIQUID_MODEL=0.75F;" in scc and "publicstaticfinalfloatLIQUID_MODEL=1F;" in scc
       and body(sc, "public static float getModelValue(int index)") == "return(index+1)/256F;",
       "model values: (index + 1) / 256 per material, 0.75 liquid additive, 1 liquid (decision 6; ItemScraps.java:74-85 liquid icons per behaviour)")
    mt = body(sc, "public static float getModelType(ItemStack stack)")
    ck("V2.scraps-model-type", "if(isLiquid(stack))returncontents.material.smeltable==NTMMaterial.SmeltingBehavior.ADDITIVE?ADDITIVE_LIQUID_MODEL:LIQUID_MODEL;" in mt
       and "intindex=MODEL_MATERIALS.indexOf(contents.material);returnindex<0?0F:getModelValue(index);" in mt, "getModelType: liquid by behaviour, else the material's index", mt)
    tn = body(sc, "public static String getTextureName(NTMMaterial material)")
    ck("V2.scraps-texture-name", tn == 'if(material==Mats.MAT_BISMUTH)return"scraps_bismuth";if(material.solidColorLight==material.solidColorDark)return"scraps_plain";returngetModelName(material);',
       "getTextureName: bismuth's override (ModItems.java:2765), the uncoloured base where light == dark (no recolour, ItemAutogen.java:59), else the recolour", tn)
    gc = body(sc, "public static int getColor(ItemStack stack)")
    ck("V2.scraps-color", "if(isLiquid(stack))returncontents.material.moltenColor;" in gc and '"scraps_plain".equals(getTextureName(contents.material))' in gc
       and "returnplain?contents.material.moltenColor:0xFFFFFF;" in gc, "getColor: liquid molten (ItemScraps.java:59-64); solid plain-texture materials molten, others none (ItemAutogen.java:102-112)", gc)
    ht = body(sc, "public void appendHoverText(ItemStack stack, TooltipContext context, List<Component> tooltip, TooltipFlag flag)")
    ck("V2.scraps-tooltip", 'elseif(contents.material.smeltable==NTMMaterial.SmeltingBehavior.ADDITIVE){tooltip.add(Component.translatable("casting.scraps.additive").withStyle(ChatFormatting.DARK_RED));}' in ht,
       "the liquid additive tooltip line is casting.scraps.additive in dark red (ItemScraps.java:112-113)", ht)
    ct = code_of(st.text(CTAB))
    ck("V2.creative-tab", "for(NTMMaterialmaterial:Mats.orderedList){if(CopperScrapsItem.isScrapMaterial(material))output.accept(CopperScrapsItem.create(newMats.MaterialStack(material,MaterialShapes.INGOT.q(1))));}" in ct,
       "the parts tab lists one ingot of scraps per SMELTABLE / ADDITIVE material in orderedList order (ItemScraps.java:45-53, default amount INGOT.q(1) :124)")
    rs = body(st.text(IMP), "private void registerScraps()")
    miss = missing_order(rs, "for(inti=0;i<CopperScrapsItem.MODEL_MATERIALS.size();i++){", "CopperScrapsItem.getModelValue(i)", 'modLoc("item/"+CopperScrapsItem.getTextureName(material))',
                         "CopperScrapsItem.ADDITIVE_LIQUID_MODEL", 'modLoc("item/scraps_additive")', "CopperScrapsItem.LIQUID_MODEL", 'modLoc("item/scraps_liquid")')
    ck("V2.model-provider", miss is None, "registerScraps: one override per MODEL_MATERIALS entry with its texture, then scraps_additive, then scraps_liquid", miss)
    ck("V2.jei", "CopperCastingRecipes.getSmeltingRecipes()" in code_of(st.text(JEIP)) and "RecipeType<CopperCastingRecipes.SmeltingRecipe>" in code_of(st.text(JEIH)) or
       "RecipeType<SmeltingRecipe>" in code_of(st.text(JEIH)), "the JEI smelting category lists CopperCastingRecipes.getSmeltingRecipes()")
    ccr = st.text(CCR)
    ck("V2.ccr-delegates", body(ccr, "public static List<Mats.MaterialStack> getMaterials(ItemStack stack)") == "returnMats.getSmeltingMaterialsFromItem(stack);"
       and body(ccr, "public static Mats.MaterialStack getMaterial(ItemStack stack)") == "List<Mats.MaterialStack>materials=getMaterials(stack);returnmaterials.isEmpty()?null:materials.get(0);",
       "CopperCastingRecipes.getMaterials = Mats.getSmeltingMaterialsFromItem; getMaterial = the first or null")

    # client boundary
    hits = {p: [w for w in CLIENT_WORDS if w in blank_comments(lf(st.text(p)))] for p in CLIENT_FREE}
    ck("V2.no-client", not any(hits.values()), "Mats, MaterialEntries, MatDistribution, CopperCastingRecipes, the crucible, CopperScrapsItem, MaterialShapes and NTMMaterial reference no "
       "client, blaze3d, render or JEI class", {p: w for p, w in hits.items() if w})


# ---------------------------------------------------------------- V3 generated

def expected_models(inp):
    mats = orig_materials(inp)
    out = []
    for m in mats:
        if m["behaviour"] not in ("SMELTABLE", "ADDITIVE") or m["field"] == "MAT_COPPER":
            continue
        name = "scraps_" + m["names"][0].lower()
        texture = "scraps_bismuth" if m["field"] == "MAT_BISMUTH" else "scraps_plain" if m["colours"][0] == m["colours"][1] else name
        out.append((name, texture))
    return out


def v3_generated(ck, inp, st):
    want = expected_models(inp)
    ck("V3.model-count", len(want) == 81, "81 solid scrap models (82 SMELTABLE / ADDITIVE materials without copper)", len(want))
    data = json.loads(st.text(SCRAPS_MODEL))
    ov = data.get("overrides", [])
    got = [(o.get("predicate", {}).get("hbmsntm:scraps_type"), o.get("model")) for o in ov]
    exp = [((i + 1) / 256, f"hbmsntm:item/{n}") for i, (n, _) in enumerate(want)] + [(0.75, "hbmsntm:item/scraps_additive"), (1.0, "hbmsntm:item/scraps_liquid")]
    ck("V3.scraps-overrides", got == exp, "scraps.json: 81 material overrides at (i + 1) / 256 in orderedList order, then scraps_additive 0.75, then scraps_liquid 1.0",
       [(i, a, b) for i, (a, b) in enumerate(zip(got, exp)) if a != b][:4] or (len(got), len(exp)))
    ck("V3.scraps-base", data.get("parent") == "minecraft:item/generated" and data.get("textures") == {"layer0": "hbmsntm:item/scraps"},
       "the base scraps model keeps item/scraps (copper, Goal 5A)", {k: v for k, v in data.items() if k != "overrides"})
    bad = []
    for name, texture in want + [("scraps_additive", "scraps_additive"), ("scraps_liquid", "scraps_liquid")]:
        p = MODELS + name + ".json"
        d = json.loads(st.text(p)) if st.has(p) else None
        if d != {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/{texture}"}}:
            bad.append((name, d))
    ck("V3.material-models", not bad, "every override model is item/generated with layer0 = its texture (bismuth override, scraps_plain where light == dark, else the recolour)", bad[:4])
    en, en0 = json.loads(st.text(EN)), json.loads(inp.start[EN])
    added = sorted(set(en) - set(en0))
    changed = [k for k in en0 if en.get(k) != en0[k]]
    mats = orig_materials(inp)
    keys = ["hbmmat." + m["names"][0].lower() for m in mats]
    new_mat = [k for k in keys if k not in en0]
    ck("V3.en-added", added == sorted(new_mat + ["casting.scraps.additive"]) and len(added) == 90 and not changed and set(keys) <= set(en),
       "en_us.json gained exactly the 89 missing hbmmat keys and casting.scraps.additive (90) and changed nothing else", (sorted(set(added) ^ set(new_mat + ["casting.scraps.additive"]))[:5], changed[:5]))
    wrong = {}
    for k in keys:
        o = inp.o_en.get(k)
        want_v = EN_DEVIATIONS.get(k, o and o[0][0])
        if en.get(k) != want_v:
            wrong[k] = (en.get(k), want_v)
    ck("V3.en-values", not wrong and en.get("casting.scraps.additive") == ADDITIVE_TEXT, "every hbmmat value is the original English (en_US.lang:1616-1733) except the recorded "
       "mingrade = Red Copper and cmbsteel = CMB Steel; casting.scraps.additive is the original literal (ItemScraps.java:113)", (wrong, en.get("casting.scraps.additive")))
    ck("V3.stamp-present", st.has(STAMP), "the generation stamp exists (its freshness is checked by the Gradle build, not here)")


# ---------------------------------------------------------------- V4 language

def v4_lang(ck, inp, st):
    zt, mt = st.text(ZH), st.text(MAP)
    zh, mp = json.loads(zt), json.loads(mt)["entries"]
    z0, m0 = json.loads(inp.start[ZH]), json.loads(inp.start[MAP])["entries"]
    en = json.loads(st.text(EN))
    new = sorted(set(zh) - set(z0))
    ck("V4.zh-insert-only", all(zh.get(k) == v for k, v in z0.items()) and len(new) == 90, "zh_cn.json keeps every start value and gained 90 keys", (len(new), [k for k, v in z0.items() if zh.get(k) != v][:3]))
    ck("V4.map-insert-only", all(mp.get(k) == v for k, v in m0.items()) and sorted(set(mp) - set(m0)) == new, "the mapping keeps every start entry and gained the same 90 entries",
       sorted(set(mp) - set(m0)) == new)
    en_new = sorted(set(en) - set(json.loads(inp.start[EN])))
    ck("V4.same-keys", new == en_new, "the 90 new Chinese keys are the 90 new English keys", sorted(set(new) ^ set(en_new))[:5])
    up = [k for k in new if mp.get(k, {}).get("kind") == "upstream"]
    loc = {k for k in new if mp.get(k, {}).get("kind") == "local"}
    ck("V4.kinds", len(up) == 84 and loc == LOCAL_KEYS, "84 upstream and 6 local entries (ilmenite, coalcoke, lignitecoke, ghiorsium336, polycarbonate, casting.scraps.additive)", (len(up), sorted(loc ^ LOCAL_KEYS)))
    bad = {}
    for k in up:
        row, o_en, o_zh = mp[k], inp.o_en.get(k), inp.o_zh.get(k)
        if not (o_en and o_zh and row.get("source_key") == k and row.get("source_en") == o_en[0][0] and row.get("source_zh") == o_zh[0][0] == row.get("target_zh") == zh.get(k)
                and row.get("target_en") == en.get(k)):
            bad[k] = (row, o_zh and o_zh[0][0], zh.get(k))
    ck("V4.upstream", not bad, "every upstream entry carries the original key, English and Chinese, and its Chinese is the original zh_CN.lang text", list(bad.items())[:3])
    badl = [k for k in loc if not str(mp[k].get("reason", "")).strip() or mp[k].get("target_zh") != zh.get(k) or mp[k].get("target_en") != en.get(k)]
    ck("V4.local", not badl, "every local entry has a reason and the current Chinese / English text", badl)
    pct = [k for k in new if "%" in zh.get(k, "") or "%" in en.get(k, "")]
    ck("V4.no-percent", not pct, "no new English or Chinese value contains '%'", pct)
    for path, text, start in ((ZH, zt, inp.start[ZH]), (MAP, mt, inp.start[MAP])):
        crlf = "\r\n" in start
        ok = (text.count("\r\n") == text.count("\n")) if crlf else ("\r\n" not in text)
        diff = [l for l in difflib.unified_diff(lf(start).split("\n"), lf(text).split("\n"), lineterm="", n=0) if l[:1] == "-" and not l.startswith("---")]
        removed = [l for l in diff if l.strip() not in ("-", "-}", "-  }", "-},", "-    },")]
        ck(f"V4.eol-{path.rsplit('/', 1)[1]}", ok, f"{path.rsplit('/', 1)[1]} keeps its start line endings ({'CRLF' if crlf else 'LF'})")
        ck(f"V4.lines-{path.rsplit('/', 1)[1]}", len(removed) <= 90 and all(re.fullmatch(r'-\s*("[^"]*": "[^"]*"|\}),?', l) or re.fullmatch(r"-\s*\},?", l) for l in diff),
           f"{path.rsplit('/', 1)[1]}: no start line was rewritten beyond trailing-comma changes at the insertion points", removed[:4])


# ---------------------------------------------------------------- V5 resources

def decode_png(data):
    """(width, height, [RGBA tuples]) for 8-bit grey / RGB / palette / grey-alpha / RGBA and palette depths 1-8, non-interlaced."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, idat, plte, trns = 8, b"", None, None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            assert interlace == 0, "interlaced"
        elif kind == b"PLTE":
            plte = [tuple(chunk[i:i + 3]) for i in range(0, len(chunk), 3)]
        elif kind == b"tRNS":
            trns = chunk
        elif kind == b"IDAT":
            idat += chunk
    raw = zlib.decompress(idat)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    bpp = max(1, channels * depth // 8)
    stride = (w * channels * depth + 7) // 8
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(h):
        f, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = prev[x], prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    px = []
    for row in rows:
        if depth < 8:
            vals = [(row[k // (8 // depth)] >> (8 - depth * (k % (8 // depth) + 1))) & ((1 << depth) - 1) for k in range(w)]
        else:
            vals = list(row)
        for x in range(w):
            if ctype == 3:
                idx = vals[x]
                r, g, b = plte[idx]
                px.append((r, g, b, trns[idx] if trns is not None and idx < len(trns) else 255))
            elif ctype == 6:
                px.append(tuple(vals[x * 4:x * 4 + 4]))
            elif ctype == 2:
                px.append(tuple(vals[x * 3:x * 3 + 3]) + (255,))
            elif ctype == 4:
                g, a = vals[x * 2:x * 2 + 2]
                px.append((g, g, g, a))
            else:
                g = vals[x]
                px.append((g, g, g, 255))
    return w, h, px


def crop(atlas, tx, ty):
    w, _, px = atlas
    x0, y0 = tx * ICON_TILE, ICON_ORIGIN_Y + ty * ICON_TILE
    return [px[(y0 + j) * w + x0 + i] for j in range(ICON_TILE) for i in range(ICON_TILE)]


def v5_resources(ck, inp, st):
    want = expected_models(inp)
    refs = sorted({t for _, t in want} | {"scraps_additive", "scraps_liquid", "scraps"})
    miss = [t for t in refs if not st.has(TEX + t + ".png")]
    ck("V5.textures-exist", not miss and len({t for _, t in want}) == 77, f"every texture the scrap models reference exists ({len(refs)} files; 77 distinct material textures)", miss)
    imports = {"scraps_additive.png": "scraps_additive.png", "scraps_bismuth.png": "scraps_bismuth.png", "scraps.png": "scraps_plain.png"}
    bad = [n for o, n in imports.items() if not st.has(TEX + n) or st.files[TEX + n] != inp.o_tex[o]]
    ck("V5.byte-imports", not bad, "scraps_additive, scraps_bismuth and scraps_plain (= scraps.png) are byte-equal to the original textures", bad)
    atlas = decode_png(inp.o_atlas)
    pots = orig_potions(inp)
    for ids, label in ((NEW_ICONS, "new"), (OLD_ICONS, "existing")):
        wrong = []
        for i in ids:
            p = ICONS + i + ".png"
            if not st.has(p):
                wrong.append((i, "missing"))
                continue
            w, h, px = decode_png(st.files[p])
            if (w, h) != (ICON_TILE, ICON_TILE) or px != crop(atlas, *pots[i]):
                wrong.append((i, w, h, sum(1 for a, b in zip(px, crop(atlas, *pots[i])) if a != b)))
        ck(f"V5.icons-{label}", not wrong, f"the {len(ids)} {label} icons are pixel-equal to the 18x18 tiles of the original potions.png at (x * 18, 198 + y * 18) (HbmPotion.java:50-61)", wrong)
    if not st.has(OWN):
        ck.pending("V5.ownership-pending", f"{OWN} is absent: pending, not passed")
    else:
        own = json.loads(st.text(OWN))
        rows = own.get("imported_assets", []) + own.get("derived_assets", []) + own.get("unchanged_assets", [])
        wrong = [r.get("target_path") for r in rows if not st.has(r.get("target_path", "")) or sha(st.files[r["target_path"]]) != r.get("target_sha256")]
        ck("V5.ownership-hashes", not wrong and own.get("source_commit") == ORIGINAL_HEAD and len(own.get("derived_assets", [])) == 78 and len(own.get("imported_assets", [])) == 3,
           "the ownership record (3 imports, 78 derived, the unchanged list) matches every file's SHA-256 at the original HEAD", wrong[:5])
        srcs = [r for r in own.get("imported_assets", []) if sha((ORIGINAL / r["source_path"]).read_bytes()) != r.get("source_sha256")]
        ck("V5.ownership-sources", not srcs, "every imported source hash equals the original file", [r.get("source_path") for r in srcs])
    for name, (code, tail) in inp.scripts.items():
        ck(f"V5.script-{name}", code == 0, f"python {name} --check exits 0", (code, tail))


# ---------------------------------------------------------------- V6 scope

def changed_paths(inp, st):
    changed = sorted(p for p, h in st.tree.items() if inp.base_files.get(p) != h)
    gone = sorted(p for p in inp.base_files if (p.startswith("src/") or p.startswith("migration/")) and p not in st.tree)
    return changed, gone


def v6_scope(ck, inp, st):
    changed, gone = changed_paths(inp, st)
    want = expected_models(inp)
    gen_expected = {SCRAPS_MODEL, EN, STAMP} | {MODELS + n + ".json" for n, _ in want} | {MODELS + "scraps_additive.json"}
    tex_expected = {TEX + t + ".png" for _, t in want} | {TEX + "scraps_additive.png"} | {ICONS + i + ".png" for i in NEW_ICONS}
    expected = set(NEW_CLASSES + EDITED) | gen_expected | tex_expected
    extra = [p for p in changed if p not in expected and p not in RECORDS_EXACT and not p.startswith(RECORDS_PREFIX)]
    ck("V6.no-extra-paths", not extra, "every changed src/ and migration/ path belongs to the batch (production, generated, resources, the GameTest, the records)", extra[:10])
    ck("V6.nothing-deleted", not gone, "no start file under src/ or migration/ was deleted", gone[:5])
    never = [p for p in set(NEW_CLASSES + EDITED) | {SCRAPS_MODEL, EN} if p not in changed]
    ck("V6.expected-all-changed", not never, "every production, GameTest and generated file the batch edits differs from the start", never[:5])
    gen_mod = [p for p in changed if p.startswith(GEN)]
    ck("V6.gen-changed", set(gen_mod) <= gen_expected, "the generated files that changed are scraps.json, the new scrap models, en_us.json and the stamp", sorted(set(gen_mod) - gen_expected)[:5])
    ck("V6.new-files-new", all(p not in inp.base_files for p in NEW_CLASSES) and all(p in inp.base_files for p in EDITED), "the new classes did not exist at the start; the edited files did")
    eol = [p for p in EDITED if inp.start.get(p) and st.has(p) and (("\r\n" in inp.start[p]) != ("\r\n" in st.text(p)) or st.text(p).count("\r\n") not in (0, st.text(p).count("\n")))]
    ck("V6.edited-eol", not eol, "the edited files keep their start line-ending style (all CRLF or all LF)", eol)
    mixed = [p for p in NEW_CLASSES if st.has(p) and st.text(p).count("\r\n") not in (0, st.text(p).count("\n"))]
    ck("V6.new-class-eol", not mixed, "every new class has one line-ending style", mixed)
    rest = sorted(p for p in changed if p in RECORDS_EXACT or p.startswith(RECORDS_PREFIX))
    ck("V6.records", True, "records changed (allowed): " + ", ".join(rest))
    for p in RECORDS_REQUIRED:
        if p not in changed:
            ck.pending(f"V6.record-pending-{p.rsplit('/', 1)[1]}", f"{p} is not yet written for 27A: pending, not passed")
    ck("V6.tools-listing", True, "tools/ is outside the src/ + migration/ hash scope; git status --porcelain tools: " + "; ".join(inp.tools_status))


# ---------------------------------------------------------------- V7 GameTest

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def gametest_total(texts):
    return sum(len(re.findall(r"@GameTest\(", blank_comments(lf(t)))) for t in texts)


def v7_gametest(ck, inp, st):
    others = gametest_total(inp.gt_other.values())
    ck("V7.other-tests", others == START_GAMETESTS, f"the other GameTest classes hold the {START_GAMETESTS} start tests", others)
    ck("V7.present", st.has(GT), "MaterialSystemGameTests.java exists")
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
    miss = [n for n in tests if f'done(helper, "{n}")' not in live]
    ck("V7.report-name", not miss, "every test passes its own name to the passed helper", miss)
    ck("V7.areas", sorted(tests) == sorted(GT_TESTS), "the tests are " + ", ".join(GT_TESTS), sorted(set(tests) ^ set(GT_TESTS)))
    ck("V7.no-client", not re.search(r"net\.minecraft\.client", code), "MaterialSystemGameTests references no client class")
    consts = [s for s in ("MATERIALS = 109", "SCRAP_MATERIALS = 82", "CAPACITY = 648 * 16", "ENTRY_ROWS = 375", "Mats.java:63-181", "MatDistribution.java:69",
                          "TileEntityCrucible.java:", "ItemScraps.java:", "ItemAutogen.java:", "HbmPotion.java:", "ShredderRecipes.java:55-70", "ItemMold.getOutput",
                          "fe, 144, ti, 24, stone, 162", "c, 36", "c, 24", "Mats.MAT_FLUX, 720", "Mats.MAT_FLUX, 72", "Mats.MAT_STEEL, 288", "fe, 216", "steelMax = 40 * CAPACITY / 72",
                          "CAPACITY - 330", "CAPACITY - 329", "(index + 1) / 256F", "0.75F", "SmokeTestSupport.place(", "b.serialize(out)", "client.deserialize(in)",
                          "loadWithComponents(", "saveWithoutMetadata(", "putInt(\"copper\", 500)", "MaterialEntries.getPreferred(MaterialShapes.NUGGET, Mats.MAT_COBALT)",
                          "RawIngotItem.Type.SLAG.meta", "Items.IRON_NUGGET") if s not in live]
    ck("V7.original-constants", not consts, "the GameTest's expected values are the original's and it cites the original lines; the crucible is placed and driven through the real paths", consts)
    ck("V7.global-restored", "finally {" in live and "Mats.materialEntries.remove(key)" in live and "Mats.materialOreEntries.remove(tagId)" in live,
       "the lookup-order check removes its temporary map entries in finally")
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
    m = re.search(re.escape(GT_MARK) + r" lookup: shape counts per material \((\d+) rows, (\d+) materials covered\): ([^\r\n]*)", text)
    ledger = dict(x.split("=", 1) for x in m[3].split()) if m else {}
    cov = {}
    for r in inp.inv["registry.json"]:
        cov[r["material"]] = cov.get(r["material"], 0) + 1
    names = {mm["field"]: mm["names"][0] for mm in orig_materials(inp)}
    want = {names[f]: str(cov.get(f, 0)) for f in names}
    ck("V7.log-ledger", bool(m) and m[1] == "375" and m[2] == "98" and ledger == want, "the runtime per-material shape counts (logged by lookup) equal registry.json: 375 rows, 98 materials",
       (m and m.group(1, 2), sorted(set(ledger.items()) ^ set(want.items()))[:6]))
    order = re.search(re.escape(GT_MARK) + r" lookup: order checked with the temporary tag entry (\S+)", text)
    ck("V7.log-tag-order", bool(order), "the tag-entry order was checked at run time (the iron ingot carried a tag on the server)", "no tag-order line in the log")
    return dict(all_passed=match and match[0], expected_total=total, ledger=m and m.group(0)[:200], tag=order and order[1])


# ---------------------------------------------------------------- V8 jar

def v8_jar(ck, inp, st, path):
    classes_ = [p.split("/java/")[1][:-5] for p in NEW_CLASSES + EDITED if "/datagen/" not in p]
    want = expected_models(inp)
    res = sorted({TEX + t + ".png" for _, t in want} | {TEX + "scraps_additive.png"} | {ICONS + i + ".png" for i in NEW_ICONS + OLD_ICONS})
    gen = sorted({SCRAPS_MODEL, EN} | {MODELS + n + ".json" for n, _ in want} | {MODELS + "scraps_additive.json"})
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        missing = [c for c in classes_ if c + ".class" not in names]
        ck("V8.classes", not missing, "the JAR has the new and edited classes (Mats, MaterialEntries, MatDistribution, the crucible, CopperScrapsItem, MaterialSystemGameTests ...)", missing)
        bad = [p for p in res if p[len(JARRES):] not in names or jar.read(p[len(JARRES):]) != st.files.get(p)]
        ck("V8.resources", not bad, f"the {len(res)} scrap textures and icons in the JAR are byte-equal to the source files", bad[:5])
        gbad = [p for p in gen if p[len(GEN):] not in names or jar.read(p[len(GEN):]) != st.files.get(p)]
        ck("V8.generated", not gbad, f"the {len(gen)} generated scrap models and en_us.json in the JAR are byte-equal to the tree (the stamp is not packaged)", gbad[:5])
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


def drop_line(path, needle):
    def fn(text):
        lines = text.split("\n")
        hit = [i for i, l in enumerate(lines) if needle in l]
        assert len(hit) == 1, (needle, len(hit))
        del lines[hit[0]]
        return "\n".join(lines)
    return T(path, fn)


def swap_lookup(text):
    """Move the item-entry lookup of getMaterialsFromItem before the MaterialEntries step."""
    m = re.search(r"\n(\s*// Upstream keys durable items[^\n]*\n[^\n]*\n\s*List<MaterialStack> entries = .*?\n\s*if\(entries != null\) \{\n.*?\n\s*\}\n)", text, re.S)
    block = m[1]
    text = text.replace(block, "\n", 1)
    return rep1(text, "        if(!tagMatched) {", block.strip("\n") + "\n\n        if(!tagMatched) {")


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None; the string 'LOG' requires a GameTest log)."""
    t = lambda path, old, new: T(path, lambda x: rep1(x, old, new))  # noqa: E731
    lang_edit = lambda path, key, value: T(path, lambda x: rep1(x, f'"{key}": {json.dumps(json.loads(x)[key], ensure_ascii=False)}', f'"{key}": {json.dumps(value, ensure_ascii=False)}'))  # noqa: E731
    return [
        # GOAL27A.md A4
        ("material_id_changed", "V2.", t(MATS, "makeSmeltable(_AS + 7,", "makeSmeltable(_AS + 27,")),
        ("conversion_deleted", "V2.", t(MATS, ".setConversion(MAT_BERYLLIUM, 4, 3)", "")),
        ("behaviour_not_smeltable", "V2.", t(MATS, "makeSmeltable(_AS + 18,", "makeNonSmeltable(_AS + 18,")),
        ("distribution_ore_row_deleted", "V2.", drop_line(DIST, "ores(NtmBlocks.ORE_COBALT, NtmBlocks.ORE_COBALT_DEEPSLATE)")),
        ("shredder_coal_row_deleted", "V2.", drop_line(SHRED, "registerIfAbsent(new ItemStack(Items.COAL), new ItemStack(NtmItems.POWDER_COAL.get(), 1));")),
        ("effect_icon_swapped", "V5.", lambda st: st.set_bytes(ICONS + "radx.png", st.files[ICONS + "radaway.png"])),
        # handoff B.V9
        ("entries_row_shape_changed", "V2.", t(ENTRIES, "add(Mats.MAT_IRON, MaterialShapes.PLATE, NtmItems.PLATE_IRON);", "add(Mats.MAT_IRON, MaterialShapes.DUST, NtmItems.PLATE_IRON);")),
        ("entries_row_deleted", "V2.", drop_line(ENTRIES, "add(Mats.MAT_LEAD, MaterialShapes.NUGGET, NtmItems.NUGGET_LEAD);")),
        ("iron_ore_stone_nugget", "V2.", t(DIST, "registerEntry(ore, MAT_IRON, INGOT.q(2), MAT_TITANIUM, NUGGET.q(3), MAT_STONE, QUART.q(1));",
                                          "registerEntry(ore, MAT_IRON, INGOT.q(2), MAT_TITANIUM, NUGGET.q(3), MAT_STONE, NUGGET.q(1));")),
        ("distribution_before_crucible", "V2.", T(SER, lambda x: rep1(rep1(x, "        recipeHandlers.add(new MatDistribution());\n", ""),
                                                                       "        recipeHandlers.add(CrucibleRecipes.INSTANCE);\n",
                                                                       "        recipeHandlers.add(new MatDistribution());\n        recipeHandlers.add(CrucibleRecipes.INSTANCE);\n"))),
        ("lookup_order_swapped", "V2.", T(MATS, swap_lookup)),
        ("trysmelt_first_material_only", "V2.", t(CRU, "for(Mats.MaterialStack material : materials) {\n                boolean recipeMaterial",
                                                  "for(Mats.MaterialStack material : materials.subList(0, 1)) {\n                boolean recipeMaterial")),
        ("sync_bound_64", "V2.", t(CRU, "MAX_SYNC_ENTRIES = Mats.orderedList.size();", "MAX_SYNC_ENTRIES = 64;")),
        ("additive_liquid_model_1", "V2.", t(SCRAPS, "ADDITIVE_LIQUID_MODEL = 0.75F;", "ADDITIVE_LIQUID_MODEL = 1F;")),
        ("model_value_128", "V2.", t(SCRAPS, "return (index + 1) / 256F;", "return (index + 1) / 128F;")),
        ("creative_filter_removed", "V2.", t(CTAB, "if(CopperScrapsItem.isScrapMaterial(material)) output.accept(", "output.accept(")),
        ("scrap_texture_byte_flip", "V5.", lambda st: st.set_bytes(TEX + "scraps_iron.png", flip_byte(st.files[TEX + "scraps_iron.png"]))),
        ("language_value_changed", "V3.", lang_edit(EN, "hbmmat.iron", "Iron Metal")),
        ("zh_text_changed", "V4.", lang_edit(ZH, "hbmmat.iron", "铁金属")),
        ("client_import_in_mats", "V2.", t(MATS, "import net.minecraft.tags.TagKey;", "import net.minecraft.tags.TagKey;\nimport net.minecraft.client.Minecraft;")),
        # review fixes (main-agent message)
        ("damaged_guard_dropped", "V2.", t(MATS, "stack.isDamaged() ? null : materialEntries.get(", "materialEntries.get(")),
        ("raw_ingot_shredder_row_deleted", "V2.", drop_line(SHRED, "RawIngotItem.Type.BORAX.meta), new ItemStack(NtmItems.POWDER_BORAX.get(), 1));")),
        ("fragment_skip_dropped", "V2.", t(ENTRIES, ' && !id.getPath().contains("fragment")', "")),
        ("shredder_wildcard_retry", "V2.", t(SHRED, "        ItemStack result = RECIPES.get(key);\n",
                                             "        ItemStack result = RECIPES.get(key);\n        if(result == null) {\n            key.meta = MetaHelper.WILDCARD_VALUE;\n            result = RECIPES.get(key);\n        }\n")),
        # more NEO edits
        ("make_duplicate_unchecked", "V2.", t(MATS, "        if(taken != null) {\n            throw new IllegalStateException(", "        if(taken == null) {\n            throw new IllegalStateException(")),
        ("smelt_conversion_float", "V2.", t(MATS, "(int) (x.amount * x.material.convOut / x.material.convIn)", "(int) (x.amount * (float) x.material.convOut / x.material.convIn)")),
        ("prefix_map_separate", "V2.", t(MATS, "prefixByName = MaterialShapes.PREFIX_BY_NAME;", "prefixByName = new HashMap<>();")),
        ("shape_quantity_changed", "V2.", t(SHAPES, "QUART = new MaterialShapes(162);", "QUART = new MaterialShapes(160);")),
        ("crucible_save_key", "V2.", t(CRU, 'tag.putIntArray("was", writeStack(this.wasteStack));', 'tag.putIntArray("waste", writeStack(this.wasteStack));')),
        ("crucible_waste_cap_dropped", "V2.", t(CRU, "return recipeAmount <= CAPACITY && wasteAmount <= CAPACITY && matchesRecipe;", "return recipeAmount <= CAPACITY && matchesRecipe;")),
        ("texture_bismuth_plain", "V2.", t(SCRAPS, 'if(material == Mats.MAT_BISMUTH) return "scraps_bismuth";', 'if(material == Mats.MAT_BISMUTH) return "scraps_plain";')),
        ("modeffect_touched", "V2.", lambda st: st.set_bytes(J + "lib/ModEffect.java", st.files[J + "lib/ModEffect.java"] + b"\n")),
        ("existing_shredder_row_changed", "V2.", t(SHRED, "registerIfAbsent(new ItemStack(Items.IRON_INGOT), new ItemStack(NtmItems.POWDER_IRON.get(), 1));",
                                                   "registerIfAbsent(new ItemStack(Items.IRON_INGOT), new ItemStack(NtmItems.POWDER_IRON.get(), 2));")),
        # original text edits (V1 and the derived checks)
        ("orig_material_id", "V1.|V2.", OE("mats", lambda x: rep1(x, "makeSmeltable(_AS + 18,	BSCCO", "makeSmeltable(_AS + 19,	BSCCO"))),
        ("orig_distribution_amount", "V1.|V2.", OE("dist", lambda x: rep1(x, "registerOre(OreDictManager.CO.ore(), MAT_COBALT, INGOT.q(1)", "registerOre(OreDictManager.CO.ore(), MAT_COBALT, INGOT.q(2)"))),
        ("orig_line_shift", "V1.", OE("cru", lambda x: "\n" + x)),
        # V3 generated
        ("override_value_changed", "V3.", gen_edit(SCRAPS_MODEL, lambda d: d["overrides"][3]["predicate"].__setitem__("hbmsntm:scraps_type", 0.5))),
        ("additive_after_liquid", "V3.", gen_edit(SCRAPS_MODEL, lambda d: d["overrides"].__setitem__(slice(-2, None), d["overrides"][-2:][::-1]))),
        ("material_model_texture", "V3.", gen_edit(MODELS + "scraps_obsidian.json", lambda d: d["textures"].__setitem__("layer0", "hbmsntm:item/scraps_obsidian"))),
        # V4 / V5
        ("map_reason_removed", "V4.", T(MAP, lambda x: re.sub(r'("hbmmat\.ilmenite": \{[^}]*?"reason": )"[^"]*"', r'\g<1>""', x, count=1))),
        ("zh_percent", "V4.", lang_edit(ZH, "hbmmat.flux", "助熔剂%")),
        ("ownership_hash", "V5.", T(OWN, lambda x: re.sub(r'("target_sha256": ")[0-9a-f]', lambda m: m[1] + ("0" if m.group(0)[-1] != "0" else "1"), x, count=1))),
        ("icon_pixel_flip", "V5.", lambda st: st.set_bytes(ICONS + "death.png", flip_png_pixel(st.files[ICONS + "death.png"]))),
        # V6
        ("stray_edit", "V6.", lambda st: st.set_bytes(J + "items/ModArmorSomething.java", b"x")),
        # V7 source and log
        ("gt_deleted", "V7.|V6.", D(GT)),
        ("gt_batch_shared", "V7.", T(GT, lambda x: x.replace('batch = "material_shredder"', 'batch = "material_scraps"'))),
        ("gt_capacity_wrong", "V7.", T(GT, lambda x: rep1(x, "CAPACITY = 648 * 16", "CAPACITY = 648 * 15"))),
        ("log_total_changed", "V7.", LT(lambda x: re.sub(r"All \d+ required tests passed", "All 280 required tests passed", x)), "LOG"),
        ("log_test_line_missing", "V7.", LT(lambda x: x.replace(f"{GT_MARK} crucible passed", "")), "LOG"),
        ("log_failed_line", "V7.", LT(lambda x: x + "\n[12:00:00] Test materialsystemgametests.crucible failed! required tests failed: 1\n"), "LOG"),
        ("log_ledger_count", "V7.", LT(lambda x: re.sub(r"(lookup: shape counts per material \(\d+ rows, \d+ materials covered\): .*?\bIron=)(\d+)", lambda m: m[1] + str(int(m[2]) + 1), x, count=1)), "LOG"),
    ]


def flip_png_pixel(data):
    """Re-encode the PNG with one pixel changed (keeps it a valid PNG, so only the pixel comparison can notice)."""
    w, h, px = decode_png(data)
    px = list(px)
    r, g, b, a = px[0]
    px[0] = (r ^ 0x10, g, b, 255 if a == 0 else a)
    raw = b"".join(b"\x00" + bytes(c for p in px[y * w:(y + 1) * w] for c in p) for y in range(h))
    chunk = lambda k, d: struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d) & 0xFFFFFFFF)  # noqa: E731
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


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
        except (AssertionError, KeyError, ValueError, StopIteration, IndexError, TypeError, AttributeError) as error:
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
    production = [p for p in changed if p.startswith("src/") and not p.startswith(GEN) and not p.startswith(RES)] + [ZH, MAP]
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), checks_pending=ck.pendings(), mutations_detected=len(applied) - len(undetected),
                     mutations_applied=len(applied), mutations_total=len(muts), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), pending=ck.pendings(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra, scripts={k: dict(exit=v[0], tail=v[1][-400:]) for k, v in inp.scripts.items()},
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
