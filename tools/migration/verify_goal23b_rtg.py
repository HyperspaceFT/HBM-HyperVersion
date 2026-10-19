"""Verify the Goal23B batch statically: RTG pellets, depleted pellets, decay and config, hazards, recipes, models, language and textures.

Read-only for both worktrees. Writes only build/migration/goal23b/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal23b/baseline-files and baseline.json):
- V0  Inputs: original HEAD and clean status, the start copies hash-equal to baseline.json, the NEO files present.
- V1  The original table, parsed from the read-only original (ModItems.java:2645-2656, ItemRTGPelletDepleted, MineralRecipes.java:205-226,
      HazardRegistry.java:337-347/:618-627, MachineConfig/VersatileConfig, ItemRTGPellet) and asserted against the task book literals.
- V2  Lifespans emulated in IEEE float32 as the original RTGUtil.getLifespan computes them.
- V3  NEO registration and semantics: NtmItems, RTGPelletItem, RTGPelletDepletedItem, RTGUtil, CommonConfig.
- V4  The ten pellet and four recycling recipes (generated JSON and the provider source).
- V5  The eleven hazard rows, the helper, the modifier and the float32 levels.
- V6  Models, creative tab and the 47 language keys (provider, generated en_us.json, zh_cn.json, mapping).
- V7  The 15 textures against the original and goal23b-resource-ownership.json.
- V8  Scope: the src/ paths changed since the start.
- V9  GameTests (source): RTGPelletGameTests and the HazardGameTests RTG guard.
- V10 (--gametest-log) the GameTest log; V11 (--jar) the packaged JAR; "not run" when the flag is absent.
- V12 In-memory mutations of the NEO inputs (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal23b_rtg.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal23b"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
NI = J + "items/NtmItems.java"
CC = J + "config/CommonConfig.java"
NC = J + "config/NtmConfig.java"
HR = J + "hazard/HazardRegistry.java"
RP = J + "datagen/NtmRecipeProvider.java"
MP = J + "datagen/NtmItemModelProvider.java"
LP = J + "datagen/NtmLanguageProvider.java"
CT = J + "inventory/NtmCreativeTabs.java"
HGT = J + "gametest/HazardGameTests.java"
RGT = J + "gametest/RTGPelletGameTests.java"
RPI = J + "items/machine/RTGPelletItem.java"
RPD = J + "items/machine/RTGPelletDepletedItem.java"
RTGU = J + "util/RTGUtil.java"
MOD = J + "hazard/modifier/HazardModifierRTGRadiation.java"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
MAP = "migration/localization/zh_cn-map.json"
OWN = "migration/goal23b-resource-ownership.json"
REV = "migration/goal23b-localization-review.json"
GEN = "src/generated/resources/"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
STAMP = GEN + ".migration-stamp.json"
TEX = "src/main/resources/assets/hbmsntm/textures/item/"
MODELS = GEN + "assets/hbmsntm/models/item/"
RECIPES = GEN + "data/hbmsntm/recipe/"
ADVS = GEN + "data/hbmsntm/advancement/recipes/misc/"
GAMETEST_DIR = J + "gametest/"

O = "src/main/java/com/hbm/"
O_MODITEMS = O + "items/ModItems.java"
O_DEPLETED = O + "items/machine/ItemRTGPelletDepleted.java"
O_PELLET = O + "items/machine/ItemRTGPellet.java"
O_RTGUTIL = O + "util/RTGUtil.java"
O_HALF = O + "interfaces/HalfLifeType.java"
O_MINERAL = O + "crafting/MineralRecipes.java"
O_HAZARD = O + "hazard/HazardRegistry.java"
O_MODIFIER = O + "hazard/modifier/HazardModifierRTGRadiation.java"
O_MACHINE = O + "config/MachineConfig.java"
O_VERSATILE = O + "config/VersatileConfig.java"
O_LANG = "src/main/resources/assets/hbm/lang/"
O_TEX = "src/main/resources/assets/hbm/textures/items/"

JAVA_MODIFIED = [NI, CC, HR, RP, MP, LP, CT, HGT]
JAVA_NEW = [RPI, RPD, RTGU, MOD, RGT]
COPIED = [NI, CC, NC, HR, RP, MP, LP, CT, HGT, STAMP, EN, ZH, TEX + "pellet_rtg.png", MAP]

# ---- the task book table (GOAL23B.md B1), written as literals so a parser bug is caught.
# (id, heat as int or (rtgDecay, otherwise), depleted material, half-life, HalfLifeType, life in ticks)
TABLE = [
    ("pellet_rtg_radium", 3, "LEAD", 16.0, "LONG", 11520000000),
    ("pellet_rtg_weak", 5, "LEAD", 1.0, "LONG", 720000000),
    ("pellet_rtg", 10, "LEAD", 87.7, "MEDIUM", 631440000),
    ("pellet_rtg_strontium", 15, "ZIRCONIUM", 29.0, "MEDIUM", 208800000),
    ("pellet_rtg_cobalt", 15, "NICKEL", 5.3, "MEDIUM", 38160000),
    ("pellet_rtg_actinium", 20, "LEAD", 21.8, "MEDIUM", 156960000),
    ("pellet_rtg_americium", 20, "NEPTUNIUM", 4.7, "LONG", 3384000000),
    ("pellet_rtg_polonium", 50, "LEAD", 138.0, "SHORT", 9936000),
    ("pellet_rtg_gold", (200, 100), "MERCURY", 2.7, "SHORT", 194400),
    ("pellet_rtg_lead", (600, 200), "BISMUTH", 0.3, "SHORT", 21600),
]
IDS = [r[0] for r in TABLE]
NEW_IDS = [i for i in IDS if i != "pellet_rtg"]
MATS = ["BISMUTH", "MERCURY", "NEPTUNIUM", "LEAD", "ZIRCONIUM", "NICKEL"]
# recipes in the original order (MineralRecipes.java:205-214): result, ingredients (IRON.plate() is plate_iron)
RECIPE_ROWS = [
    ("pellet_rtg", ["billet_pu238"] * 3), ("pellet_rtg_radium", ["billet_ra226"] * 3), ("pellet_rtg_weak", ["billet_u238", "billet_u238", "billet_pu238"]),
    ("pellet_rtg_strontium", ["billet_sr90"] * 3), ("pellet_rtg_cobalt", ["billet_co60"] * 3), ("pellet_rtg_actinium", ["billet_actinium"] * 3),
    ("pellet_rtg_polonium", ["billet_polonium"] * 3), ("pellet_rtg_lead", ["billet_pb209"] * 3), ("pellet_rtg_gold", ["billet_au198"] * 3),
    ("pellet_rtg_americium", ["billet_am241"] * 3)]
RECYCLE_NEO = [("BISMUTH", "billet_bismuth", 3), ("LEAD", "ingot_lead", 2), ("NEPTUNIUM", "billet_neptunium", 3), ("ZIRCONIUM", "billet_zirconium", 3)]
# hazard rows (HazardRegistry.java:337-346): pellet, expression, target, hot, blinding; and the expected float32 level
HAZARD_ROWS = [
    ("pellet_rtg", "pu238*rtg", 0, 3, 0, 15.0), ("pellet_rtg_radium", "ra226*rtg", 0, 0, 0, 11.25),
    ("pellet_rtg_weak", "(pu238+(u238*2))*billet", 0, 0, 0, 5.25), ("pellet_rtg_strontium", "sr90*rtg", 0, 0, 0, 22.5),
    ("pellet_rtg_cobalt", "co60*rtg", 0, 0, 0, 45.0), ("pellet_rtg_actinium", "ac227*rtg", 0, 0, 0, 45.0),
    ("pellet_rtg_polonium", "po210*rtg", 0, 3, 0, 112.5), ("pellet_rtg_lead", "pb209*rtg", 0, 7, 50, 15000.0),
    ("pellet_rtg_gold", "au198*rtg", 0, 5, 0, 750.0), ("pellet_rtg_americium", "am241*rtg", 0, 0, 0, 12.75)]
NP_ROW = ("NEPTUNIUM", "np237*rtg", 3.75)
CONSTANTS = ["pu238", "ra226", "u238", "sr90", "co60", "ac227", "po210", "pb209", "au198", "am241", "np237", "billet", "rtg"]
CONFIG_ROWS = [("scaleRTGPower", "SCALE_RTG_POWER", "Should RTG/Betavoltaic fuel power scale down as it decays?", "false"),
               ("doRTGsDecay", "DO_RTGS_DECAY", "Should RTG/Betavoltaic fuel decay at all?", "true")]
EXT_KEYS = {"desc.item.rtgExtended": "EXTENDED INFO:", "desc.item.rtgTicks": "%s / %s ticks",
            "desc.item.rtgRemaining": "Time remaining: %s y, %s d, %s h", "desc.item.rtgMaxLife": "Maximum life: %s y, %s d, %s h"}
RTG_TESTS = ["rtg_pellet_lifespans", "rtg_pellet_decay", "rtg_pellet_scaled_power", "rtg_pellet_depletion", "rtg_pellet_recipes", "rtg_pellet_hazards",
             "rtg_pellet_stack_size", "rtg_pellet_living_radium", "rtg_pellet_tooltip_and_use"]
GUARD_TEST = "hazard_none_for_ores_and_unlisted"
HASH_SKIP = ("__pycache__",)


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
        self.items.append(dict(id=cid, status="PASS" if ok else "FAIL", label=label, detail="" if ok else str(detail)[:700]))
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


def method_span(text, signature):
    """(open_brace, close_brace, blanked code) of the unique method whose header contains signature."""
    code = blank_comments(text)
    found = [m.start() for m in re.finditer(re.escape(signature), code)]
    if len(found) != 1:
        raise ValueError(f"{signature!r} occurs {len(found)} times")
    open_index = code.index("{", found[0])
    return open_index, match_brace(code, open_index), code


def method_text(text, signature):
    o, c, _ = method_span(text, signature)
    return lf(text[o:c + 1])


def norm(code):
    return re.sub(r"\s+", " ", code).strip()


def squash(code):
    return re.sub(r"\s+", "", code)


def method_code(text, signature):
    """The method body with comments removed and whitespace collapsed (the structure, not the layout)."""
    o, c, code = method_span(text, signature)
    return norm(code[o + 1:c])


def method_block_lines(text, signature):
    """Stripped non-blank lines of the method with the comment lines directly above it (text is line-ending normalised)."""
    text = lf(text)
    o, c, code = method_span(text, signature)
    sig = code.rfind("\n", 0, code.index(signature)) + 1
    lines_before = text[:sig].split("\n")[:-1]
    keep = []
    while lines_before and lines_before[-1].strip().startswith(("//", "/*", "*")):
        keep.insert(0, lines_before.pop())
    return [x.strip() for x in keep + text[sig:c + 1].split("\n") if x.strip()]


def eol_of(text):
    return "\r" if "\r\n" in text and text.count("\r\n") == text.count("\n") else ""


def non_equal_ops(start, live):
    """List of (tag, start lines, live lines) of every non-equal opcode, line endings normalised."""
    key = (start, live)
    cached = _OPS.get(key)
    if cached is None:
        s, l = lf(start).split("\n"), lf(live).split("\n")
        cached = [(tag, s[i1:i2], l[j1:j2]) for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, s, l, autojunk=False).get_opcodes() if tag != "equal"]
        _OPS[key] = cached
    return cached


_OPS = {}


def diff_summary(start, live):
    """(deleted start lines, inserted live lines), both stripped and without blank lines."""
    ops = non_equal_ops(start, live)
    deleted = [x.strip() for _, s, _ in ops for x in s if x.strip()]
    inserted = [x.strip() for _, _, l in ops for x in l if x.strip()]
    return deleted, inserted


def insert_only(start, live):
    ops = non_equal_ops(start, live)
    if any(tag == "delete" or tag == "replace" for tag, _, _ in ops):
        return False, [(tag, s[:3], l[:3]) for tag, s, l in ops if tag != "insert"]
    return True, [x for _, _, l in ops for x in l]


def json_pairs(text):
    dups = []

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(k for k in set(keys) if keys.count(k) > 1)
        return dict(pairs)
    return json.loads(text, object_pairs_hook=hook), dups


def parse_lang(path):
    result = {}
    for line in read_text(path).lstrip("﻿").split("\n"):
        line = line.rstrip("\r")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result.setdefault(key, value)
    return result


def format_ok(text, data):
    plain = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return text == plain or text == crlf(plain)


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


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


def json_edit(text, edit, entries=False):
    data = json.loads(text)
    edit(data["entries"] if entries else data)
    eol = "\r\n" if "\r\n" in text else "\n"
    return json.dumps(data, indent=2, ensure_ascii=False).replace("\n", eol) + eol


def java_string(literal):
    return literal.replace('\\"', '"').replace("\\\\", "\\")


# ---------------------------------------------------------------- float32 emulation

def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


class F32:
    """A Java float: every operation rounds to IEEE binary32 (double arithmetic is exact enough for + - * /)."""

    def __init__(self, v):
        self.v = f32(float(v))

    @staticmethod
    def _o(o):
        return o.v if isinstance(o, F32) else f32(float(o))

    def __add__(self, o):
        return F32(self.v + self._o(o))

    __radd__ = __add__

    def __mul__(self, o):
        return F32(self.v * self._o(o))

    __rmul__ = __mul__

    def __sub__(self, o):
        return F32(self.v - self._o(o))

    def __rsub__(self, o):
        return F32(self._o(o) - self.v)

    def __truediv__(self, o):
        return F32(self.v / self._o(o))


def eval_float(expr, names):
    return eval(re.sub(r"(\d)[fF]\b", r"\1", expr), {"__builtins__": {}}, {k: v for k, v in names.items()})  # noqa: S307 - own constant expressions


def float_constants(text):
    """name -> F32 for every `public static final float NAME = expr;` that evaluates with the earlier ones."""
    names = {}
    for name, expr in re.findall(r"public static final float (\w+) = ([^;]+);", blank_comments(text)):
        try:
            value = eval_float(expr, names)
            names[name] = value if isinstance(value, F32) else F32(value)
        except Exception:  # noqa: BLE001 - a constant that depends on a later one or on a non-float expression
            pass
    return names


def java_lifespan(half, typ, real=False, mult=1.5):
    """Original RTGUtil.getLifespan(float, type, realYears) followed by (long) (... * 1.5), with float32 rounding at every float operation."""
    days = 365 if real else 100
    ints = {"LONG": 48000 * days * 100, "MEDIUM": 48000 * days, "SHORT": 48000}[typ]
    life = f32(f32(float(ints)) * f32(float(half)))  # int -> float, float * float -> float
    base = int(life)  # (long) float truncates toward zero
    return int(float(base) * mult)  # long * double -> double, (long) truncates


def naive_lifespan(half, typ, real=False, mult=1.5):
    days = 365 if real else 100
    ints = {"LONG": 48000 * days * 100, "MEDIUM": 48000 * days, "SHORT": 48000}[typ]
    return int(ints * float(half) * mult)


# ---------------------------------------------------------------- state and inputs

class State:
    """The mutable view of the NEO tree the checks read: bytes of every loaded file and sha256 of every file under src, migration, tools."""

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
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root).decode("utf-8")


def hash_tree():
    hashes = {}
    for top in ("src", "migration", "tools"):
        for base, dirs, names in os.walk(ROOT / top):
            dirs[:] = [d for d in dirs if d not in HASH_SKIP]
            for name in names:
                path = Path(base) / name
                hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def gametest_count(texts):
    return sum(len(re.findall(r"@GameTest\(", t)) for t in texts)


def otext(path):
    return lf(read_text(ORIGINAL / path))


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files = baseline, baseline["files"]
    inp.start = {p: read_text(START / p) for p in COPIED if p != TEX + "pellet_rtg.png"}
    inp.start_png = (START / TEX / "pellet_rtg.png").read_bytes()
    inp.start_hash_ok = {p: sha((START / p).read_bytes()) == inp.base_files.get(p) for p in baseline["copied_scope"]}
    try:
        head = git(ORIGINAL, "rev-parse", "HEAD").strip()
        status = git(ORIGINAL, "status", "--porcelain=v1")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.o_en = parse_lang(ORIGINAL / O_LANG / "en_US.lang")
    inp.o_zh = parse_lang(ORIGINAL / O_LANG / "zh_CN.lang")
    inp.o = {name: otext(path) for name, path in dict(moditems=O_MODITEMS, depleted=O_DEPLETED, pellet=O_PELLET, rtgutil=O_RTGUTIL, half=O_HALF,
                                                      mineral=O_MINERAL, hazard=O_HAZARD, modifier=O_MODIFIER, machine=O_MACHINE, versatile=O_VERSATILE).items()}
    inp.o_png = {i: (ORIGINAL / O_TEX / (i + ".png")).read_bytes() for i in IDS + ["pellet_rtg_depleted." + m.lower() for m in MATS] if (ORIGINAL / O_TEX / (i + ".png")).exists()}
    gametest_dir = ROOT / GAMETEST_DIR
    inp.gametest_other = gametest_count(read_text(p) for p in sorted(gametest_dir.glob("*.java")) if p.name not in ("HazardGameTests.java", "RTGPelletGameTests.java"))
    files = {}
    paths = [NI, CC, NC, HR, RP, MP, LP, CT, HGT, RPI, RPD, RTGU, MOD, ZH, MAP, OWN, REV, EN, STAMP, TEX + "pellet_rtg.png", J + "hazard/HazardSystem.java"]
    if (ROOT / RGT).exists():
        paths.append(RGT)
    for pattern_dir, pattern in ((MODELS, "pellet_rtg*.json"), (RECIPES, "pellet_rtg*.json"), (TEX, "pellet_rtg*.png")):
        paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / pattern_dir).glob(pattern))]
    for path in paths:
        if (ROOT / path).exists():
            files[path] = (ROOT / path).read_bytes()
    return inp, State(files, hash_tree())


def hashed_equal(inp, st, path):
    return path in inp.base_files and st.tree.get(path) == inp.base_files[path]


# ---------------------------------------------------------------- original parsing (V1)

ROW = re.compile(r'^\s*(?P<var>\w+) = new ItemRTGPellet\((?P<heat>\d+|VersatileConfig\.rtgDecay\(\) \? \d+ : \d+)\)\.setDecays\(DepletedRTGMaterial\.(?P<mat>\w+), '
                 r'\(long\) \(RTGUtil\.getLifespan\((?P<half>[\d.]+)F, HalfLifeType\.(?P<type>\w+), (?P<real>\w+)\) \* (?P<mult>[\d.]+)\)\)'
                 r'\.setUnlocalizedName\("(?P<id>\w+)"\)(?P<tail>.*)$')


def parse_heat(text):
    m = re.match(r"(?:VersatileConfig\.rtgDecay\(\)|\(\) -> RTGUtil\.rtgDecay\(\)) \? (\d+) : (\d+)$", text)
    return (int(m[1]), int(m[2])) if m else int(text)


def parse_original(inp):
    o = inp.o
    p = {}
    mi = o["moditems"].split("\n")
    rows = []
    for n in range(2647, 2657):
        m = ROW.match(mi[n - 1])
        if not m:
            raise ValueError(f"ModItems.java:{n} does not match the pellet row shape: {mi[n - 1]!r}")
        rows.append(dict(line=n, id=m["id"], var=m["var"], heat=parse_heat(m["heat"]), mat=m["mat"], half=float(m["half"]), type=m["type"], real=m["real"], mult=float(m["mult"]),
                         control_tab=".setCreativeTab(MainRegistry.controlTab)" in m["tail"], texture_is_id=f'.setTextureName(RefStrings.MODID + ":{m["id"]}")' in m["tail"],
                         explicit_stack_1=".setMaxStackSize(1)" in m["tail"]))
    p["rows"] = rows
    p["depleted_line"] = (2645, mi[2644].strip())
    p["depleted_enum"] = re.findall(r"\b([A-Z]+)\b", re.search(r"enum DepletedRTGMaterial \{(.*?)\}", o["depleted"], re.S)[1])
    p["halflife_enum"] = re.findall(r"\b([A-Z]+)\b", blank_comments(re.search(r"enum HalfLifeType \{(.*?)\}", o["half"], re.S)[0]).split("{", 1)[1])
    mr = o["mineral"].split("\n")
    pr = []
    for n in range(205, 215):
        m = re.search(r"new ShapelessOreRecipe\(new ItemStack\(ModItems\.(\w+)\), new Object\[\] \{ (.*?) \}\)\);", mr[n - 1])
        if not m:
            raise ValueError(f"MineralRecipes.java:{n}: {mr[n - 1]!r}")
        pr.append(dict(line=n, id=m[1], ingredients=["plate_iron" if x == "IRON.plate()" else x.replace("ModItems.", "") for x in m[2].split(", ")]))
    p["recipes"] = pr
    rec = []
    for n in range(217, 222):
        m = re.search(r"addShapelessRecipe\(new ItemStack\(ModItems\.(\w+), (\d+)\), new Object\[\] \{ new ItemStack\(ModItems\.pellet_rtg_depleted, 1, DepletedRTGMaterial\.(\w+)\.ordinal\(\)\) \}\);", mr[n - 1])
        if not m:
            raise ValueError(f"MineralRecipes.java:{n}: {mr[n - 1]!r}")
        rec.append(dict(line=n, result=m[1], count=int(m[2]), mat=m[3]))
    p["recycle"] = rec
    nickel = "\n".join(mr[221:226])
    p["nickel"] = dict(guarded='OreDictionary.doesOreNameExist("ingotNickel")' in mr[221], count2="nickel.stackSize = 2;" in nickel, mat="DepletedRTGMaterial.NICKEL.ordinal()" in mr[224],
                       closes=mr[225].strip() == "}")
    hz = o["hazard"].split("\n")
    hrows = []
    for n in range(337, 347):
        m = re.match(r"^\s*registerRTGPellet\((\w+), ([^,]+), ([^,)]+)((?:, [^,)]+)*)\);", hz[n - 1])
        if not m:
            raise ValueError(f"HazardRegistry.java:{n}: {hz[n - 1]!r}")
        extra = [float(x.strip().rstrip("fF")) for x in m[4].split(",") if x.strip()]
        hrows.append(dict(line=n, pellet=m[1], expr=squash(m[2]), target=float(m[3].rstrip("fF")), hot=extra[0] if extra else 0.0, blinding=extra[1] if len(extra) > 1 else 0.0))
    p["hazard"] = hrows
    m = re.match(r"^\s*HazardSystem\.register\(new ItemStack\((\w+), 1, DepletedRTGMaterial\.(\w+)\.ordinal\(\)\), makeData\(RADIATION, ([^)]+)\)\);", hz[346])
    p["hazard_np"] = dict(line=347, item=m[1], mat=m[2], expr=squash(m[3])) if m else None
    p["hazard_lines"] = {n: hz[n - 1].strip() for n in (144, 145, 618, 619, 621)}
    p["constants"] = float_constants(o["hazard"])
    machine = o["machine"].split("\n")
    cfg = []
    for n in (14, 15):
        m = re.search(r'(\w+) = CommonConfig\.createConfigBool\(config, CATEGORY_MACHINE, "([^"]+)", "([^"]*)", (true|false)\);', machine[n - 1])
        cfg.append(dict(line=n, field=m[1], key=m[2], comment=m[3], default=m[4]) if m else None)
    p["config"] = cfg
    p["config_fields"] = re.findall(r"protected static boolean (\w+) = (true|false);", o["machine"])
    p["versatile"] = (squash(method_code(o["versatile"], "public static boolean rtgDecay()")), squash(method_code(o["versatile"], "public static boolean scaleRTGPower()")))
    pl = o["pellet"].split("\n")
    p["facts"] = [java_string(re.match(r'^\s*"((?:[^"\\]|\\.)*)",?\s*$', pl[n - 1])[1]) for n in range(41, 57)]
    p["facts_frame"] = (pl[39].strip(), pl[56].strip())
    p["pellet_ctor"] = squash(method_code(o["pellet"], "public ItemRTGPellet(int heatIn)"))
    p["pellet_facts_use"] = "facts[world.rand.nextInt(facts.length)]" in o["pellet"] and "random.orb" in o["pellet"]
    p["rtgutil_lifespan"] = squash(method_code(o["rtgutil"], "public static long getLifespan(float halfLife, HalfLifeType type, boolean realYears)"))
    p["helper"] = (squash(method_code(o["hazard"], "private static void registerRTGPellet(Item pellet, float base, float target, float hot, float blinding)")),
                   squash(method_code(o["hazard"], "private static void registerRTGPellet(Item pellet, float base, float target) {")),
                   squash(method_code(o["hazard"], "private static void registerRTGPellet(Item pellet, float base, float target, float hot) {")))
    p["modifier"] = squash(method_code(o["modifier"], "public float modify(ItemStack stack, EntityLivingBase holder, float level)"))
    return p


def heat_of(row):
    return row["heat"]


# ---------------------------------------------------------------- V0

def v0_inputs(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("V0.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    ck("V0.baseline-copies-match", all(inp.start_hash_ok.values()) and len(inp.start_hash_ok) == 20, "every baseline-files copy (20) hashes to its baseline.json entry",
       [p for p, v in inp.start_hash_ok.items() if not v])
    needed = [NI, CC, NC, HR, RP, MP, LP, CT, HGT, RPI, RPD, RTGU, MOD, ZH, MAP, OWN, REV, EN, STAMP]
    ck("V0.neo-files-present", all(st.has(p) for p in needed), "the modified and new NEO files exist", [p for p in needed if not st.has(p)])
    ck("V0.baseline-head", inp.baseline.get("source_head") == ORIGINAL_HEAD, "baseline.json records the original HEAD", inp.baseline.get("source_head"))


# ---------------------------------------------------------------- V1

def v1_original(ck, inp, st, facts_out=None):
    p = inp.parsed
    rows = p["rows"]
    facts = {}
    ck("V1.moditems-rows", [r["id"] for r in rows] == IDS and [r["line"] for r in rows] == list(range(2647, 2657)) and all(r["var"] == r["id"] for r in rows),
       "ModItems.java:2647-2656 are the ten ItemRTGPellet rows in the construction order radium, weak, pellet_rtg, strontium, cobalt, actinium, americium, polonium, gold, lead",
       [(r["line"], r["id"]) for r in rows])
    table = [(r["id"], r["heat"], r["mat"], r["half"], r["type"]) for r in rows]
    ck("V1.moditems-table-literal", table == [(t[0], t[1], t[2], t[3], t[4]) for t in TABLE], "the parsed heat, depleted material, half-life and HalfLifeType equal the task book B1 table literals",
       [(a, b) for a, b in zip(table, TABLE) if a != b[:5]])
    ck("V1.moditems-mult", all(r["mult"] == 1.5 and r["real"] == "false" for r in rows), "every row is (long) (RTGUtil.getLifespan(h, type, false) * 1.5)", [(r["id"], r["mult"], r["real"]) for r in rows])
    ck("V1.moditems-tab-texture", all(r["control_tab"] and r["texture_is_id"] for r in rows), "every row is in the control tab with its own texture name")
    facts["explicit_setMaxStackSize_1"] = {r["id"]: r["explicit_stack_1"] for r in rows}
    dl = p["depleted_line"]
    ck("V1.depleted-line", dl[0] == 2645 and "new ItemRTGPelletDepleted().setContainerItem(plate_iron)" in dl[1] and '.setUnlocalizedName("pellet_rtg_depleted")' in dl[1] and "controlTab" in dl[1],
       "ModItems.java:2645 is pellet_rtg_depleted = new ItemRTGPelletDepleted().setContainerItem(plate_iron) in the control tab", dl[1])
    ck("V1.depleted-enum", p["depleted_enum"] == MATS, "DepletedRTGMaterial is BISMUTH, MERCURY, NEPTUNIUM, LEAD, ZIRCONIUM, NICKEL", p["depleted_enum"])
    ck("V1.halflife-enum", p["halflife_enum"] == ["SHORT", "MEDIUM", "LONG"], "HalfLifeType is SHORT, MEDIUM, LONG", p["halflife_enum"])
    ck("V1.recipe-pellets", [(r["id"], r["ingredients"]) for r in p["recipes"]] == [(i, b + ["plate_iron"]) for i, b in RECIPE_ROWS] and [r["line"] for r in p["recipes"]] == list(range(205, 215)),
       "MineralRecipes.java:205-214 are the ten shapeless pellet recipes: three billets (weak: 2 u238 + 1 pu238) and IRON.plate(), in that order", [(r["id"], r["ingredients"]) for r in p["recipes"]])
    ck("V1.recipe-recycling", [(r["mat"], r["result"], r["count"], r["line"]) for r in p["recycle"]] == [("BISMUTH", "billet_bismuth", 3, 217), ("LEAD", "ingot_lead", 2, 218), ("MERCURY", "ingot_mercury", 2, 219),
                                                                                                         ("NEPTUNIUM", "billet_neptunium", 3, 220), ("ZIRCONIUM", "billet_zirconium", 3, 221)],
       "MineralRecipes.java:217-221 recycle bismuth 3 billet_bismuth, lead 2 ingot_lead, mercury 2 ingot_mercury, neptunium 3 billet_neptunium, zirconium 3 billet_zirconium", p["recycle"])
    ck("V1.recipe-nickel", all(p["nickel"].values()), "MineralRecipes.java:222-226 is the ingotNickel-guarded nickel x2 recycling recipe", p["nickel"])
    ck("V1.hazard-rows", [(r["pellet"], r["expr"], r["target"], r["hot"], r["blinding"]) for r in p["hazard"]] == [(h[0], h[1], float(h[2]), float(h[3]), float(h[4])) for h in HAZARD_ROWS]
       and [r["line"] for r in p["hazard"]] == list(range(337, 347)), "HazardRegistry.java:337-346 are the ten registerRTGPellet rows with the task book expressions, target 0, hot and blinding",
       [(r["pellet"], r["expr"], r["target"], r["hot"], r["blinding"]) for r in p["hazard"]])
    np_row = p["hazard_np"]
    ck("V1.hazard-np-row", bool(np_row) and (np_row["item"], np_row["mat"], np_row["expr"]) == ("pellet_rtg_depleted", NP_ROW[0], NP_ROW[1]),
       "HazardRegistry.java:347 registers the NEPTUNIUM depleted pellet stack with RADIATION np237 * rtg", np_row)
    hl = p["hazard_lines"]
    ck("V1.hazard-constants", hl[144].startswith("public static final float billet = 0.5F;") and hl[145].startswith("public static final float rtg = billet * 3;") and "registerRTGPellet(Item pellet" in hl[621],
       "HazardRegistry.java:144-145 are billet = 0.5F and rtg = billet * 3 (the task book says :146 for rtg; the line is :145) and :618-627 hold the helper", hl)
    ck("V1.hazard-constant-values", all(n in p["constants"] for n in CONSTANTS), "the thirteen constants the rows use evaluate in float32", [n for n in CONSTANTS if n not in p["constants"]])
    ck("V1.config", [(c["key"], c["comment"], c["default"]) for c in p["config"] if c] == [("9.00_scaleRTGPower", "Should RTG/Betavoltaic fuel power scale down as it decays?", "false"),
                                                                                      ("9.01_doRTGsDecay", "Should RTG/Betavoltaic fuel decay at all?", "true")]
       and p["config_fields"] == [("scaleRTGPower", "false"), ("doRTGsDecay", "true")], "MachineConfig.java:14-15 are 9.00_scaleRTGPower (false) and 9.01_doRTGsDecay (true) with the two comments", p["config"])
    ck("V1.versatile", p["versatile"] == ("returnGeneralConfig.enable528||MachineConfig.doRTGsDecay;", "returnGeneralConfig.enable528||MachineConfig.scaleRTGPower;"),
       "VersatileConfig.rtgDecay() = enable528 || doRTGsDecay and scaleRTGPower() = enable528 || scaleRTGPower", p["versatile"])
    ck("V1.pellet-class", p["pellet_ctor"] == "heat=(short)heatIn;setMaxStackSize(1);pelletList.add(this);" and p["pellet_facts_use"] and len(p["facts"]) == 16 and p["facts_frame"][1] == "};",
       "ItemRTGPellet: constructor setMaxStackSize(1) + pelletList.add(this), 16 facts at :41-56 shown on right click with random.orb", (p["pellet_ctor"], len(p["facts"]), p["facts_frame"]))
    ck("V1.rtgutil-lifespan", p["rtgutil_lifespan"].startswith("floatlife=0;switch(type)") and "return(long)life;" in p["rtgutil_lifespan"], "the original RTGUtil.getLifespan is a float switch followed by (long) life")
    ck("V1.modifier", p["modifier"] == "if(stack.getItem()instanceofItemRTGPellet){ItemRTGPelletfuel=(ItemRTGPellet)stack.getItem();doubledepletion=fuel.getDurabilityForDisplay(stack);"
                                       "level=(float)(level+(this.target-level)*depletion);}returnlevel;", "the original HazardModifierRTGRadiation is level + (target - level) * getDurabilityForDisplay")
    facts["task_book_vs_source"] = dict(rtg_constant_line_in_task_book_b1=146, rtg_constant_line_in_original=145, billet_line_in_original=144,
                                        note="GOAL23B.md B1 cites HazardRegistry.java:146 for rtg = billet * 3; the line is :145 (B2 says :145)")
    facts["original_table"] = [(r["line"], r["id"], r["heat"], r["mat"], r["half"], r["type"]) for r in rows]
    facts["original_facts"] = p["facts"]
    facts["constants"] = {k: v.v for k, v in p["constants"].items() if k in CONSTANTS}
    if facts_out is not None:
        facts_out["V1"] = facts


# ---------------------------------------------------------------- V2

def v2_lifespans(ck, inp, st, facts_out=None):
    p = inp.parsed
    emulated = {r["id"]: java_lifespan(r["half"], r["type"], False, r["mult"]) for r in p["rows"]}
    expected = {t[0]: t[5] for t in TABLE}
    ck("V2.original-lifespans", emulated == expected, "the float32 emulation of the original getLifespan(...) * 1.5 gives 11,520,000,000 / 720,000,000 / 631,440,000 / 208,800,000 / 38,160,000 / "
       "156,960,000 / 3,384,000,000 / 9,936,000 / 194,400 / 21,600 for the parsed rows", {k: (emulated.get(k), v) for k, v in expected.items() if emulated.get(k) != v})
    ck("V2.sample-420960000", java_lifespan(87.7, "MEDIUM", False, 1.0) == 420960000, "RTGUtil.getLifespan(87.7F, MEDIUM, false) is 420,960,000 in float32 (the GameTest sample)", java_lifespan(87.7, "MEDIUM", False, 1.0))
    naive = {r["id"]: naive_lifespan(r["half"], r["type"], False, r["mult"]) for r in p["rows"]}
    differs = {k: (naive[k], expected[k]) for k in expected if naive[k] != expected[k]}
    neo = neo_rows(st)
    neo_life = {r["id"]: java_lifespan(r["half"], r["type"], False, r["mult"]) for r in neo} if neo else {}
    ck("V2.neo-lifespans", neo_life == expected, "the float32 emulation of the NtmItems.java registration parameters gives the same ten lifespans", {k: (neo_life.get(k), v) for k, v in expected.items() if neo_life.get(k) != v})
    if facts_out is not None:
        facts_out["V2"] = dict(emulated_float32=emulated, naive_double=naive, naive_differs_from_float32=differs,
                               note="a double computation of 48000 * days * 100 * half * 1.5 differs from the float32 emulation for the ids in naive_differs_from_float32 (informational, not a failure)")


# ---------------------------------------------------------------- V3

NEO_ROW = re.compile(r'^\s*public static final DeferredItem<Item> (?P<var>\w+) = ITEMS\.register\("(?P<id>\w+)", \(\) -> new RTGPelletItem\(new Item\.Properties\(\), '
                     r'(?P<heat>\d+|\(\) -> RTGUtil\.rtgDecay\(\) \? \d+ : \d+)\)\.setDecays\(DepletedRTGMaterial\.(?P<mat>\w+), \(long\) \(RTGUtil\.getLifespan\('
                     r'(?P<half>[\d.]+)F, HalfLifeType\.(?P<type>\w+), (?P<real>\w+)\) \* (?P<mult>[\d.]+)\)\)\); // :(?P<line>\d+)\s*$')
NEO_DEPLETED = 'public static final DeferredItem<Item> PELLET_RTG_DEPLETED = ITEMS.register("pellet_rtg_depleted", () -> new RTGPelletDepletedItem(new Item.Properties().craftRemainder(PLATE_IRON.get())));'


def pellet_block(st):
    """(block lines after `// Pellets` up to the blank line, index in the file) of NtmItems.java."""
    lines = lf(st.text(NI)).split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip() == "// Pellets"]
    if len(idx) != 1:
        raise ValueError(f"`// Pellets` occurs {len(idx)} times")
    block = []
    for l in lines[idx[0] + 1:]:
        if not l.strip():
            break
        block.append(l)
    return block, idx[0]


def neo_rows(st):
    try:
        block, _ = pellet_block(st)
    except Exception:  # noqa: BLE001
        return []
    rows = []
    for l in block:
        m = NEO_ROW.match(l)
        if m:
            rows.append(dict(var=m["var"], id=m["id"], heat=parse_heat(m["heat"]), mat=m["mat"], half=float(m["half"]), type=m["type"], real=m["real"], mult=float(m["mult"]), line=int(m["line"])))
    return rows


def v3_registration(ck, inp, st, facts_out=None):
    p = inp.parsed
    block, at = pellet_block(st)
    rows = neo_rows(st)
    comments = [l for l in block if l.strip().startswith("//")]
    ck("V3.block-shape", len(block) >= 16 and all(l.strip().startswith("//") for l in block[:4]) and all(NEO_ROW.match(l) for l in block[4:14]) and block[14].strip().startswith("// :2645")
       and all(l.strip().startswith("//") for l in block[14:-1]) and block[-1].strip() == NEO_DEPLETED,
       "the `// Pellets` block is 4 comment lines, the ten RTGPelletItem registrations, the `// :2645` comment (one or more lines) and the pellet_rtg_depleted registration",
       [l.strip()[:100] for l in block])
    ck("V3.row-order", [r["id"] for r in rows] == IDS and [r["var"] for r in rows] == [i.upper() for i in IDS], "the ten pellets are registered in the original construction order with the constant names PELLET_RTG...", [r["id"] for r in rows])
    ck("V3.row-source-lines", [r["line"] for r in rows] == [r["line"] for r in p["rows"]], "each registration's `// :NNNN` comment is the original ModItems.java line of that pellet", [r["line"] for r in rows])
    mism = []
    for r, o in zip(rows, p["rows"]):
        if (r["id"], r["heat"], r["mat"], r["half"], r["type"], r["real"], r["mult"]) != (o["id"], o["heat"], o["mat"], o["half"], o["type"], o["real"], o["mult"]):
            mism.append((r["id"], (r["heat"], r["mat"], r["half"], r["type"], r["mult"]), (o["heat"], o["mat"], o["half"], o["type"], o["mult"])))
    ck("V3.row-parameters", not mism and len(rows) == 10, "heat (gold 200/100 and lead 600/200 as `() -> RTGUtil.rtgDecay() ? a : b`), depleted material, half-life, HalfLifeType and `* 1.5` equal the original rows", mism)
    ck("V3.gold-lead-heat-supplier", {r["id"]: r["heat"] for r in rows if isinstance(r["heat"], tuple)} == {"pellet_rtg_gold": (200, 100), "pellet_rtg_lead": (600, 200)},
       "only gold and lead use the runtime heat supplier", {r["id"]: r["heat"] for r in rows if isinstance(r["heat"], tuple)})
    text = st.text(NI)
    ck("V3.only-ten-pellet-items", text.count("new RTGPelletItem(") == 10 and text.count('ITEMS.register("pellet_rtg"') == 1 and text.count("new RTGPelletDepletedItem(") == 1,
       "NtmItems registers exactly ten RTGPelletItem, one of them pellet_rtg (ID kept), and one RTGPelletDepletedItem")
    start = inp.start[NI]
    deleted, inserted = diff_summary(start, text)
    old_line = 'public static final DeferredItem<Item> PELLET_RTG = ITEMS.register("pellet_rtg", () -> new Item(new Item.Properties()));'
    imports = ["import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;", "import com.hbm.util.RTGUtil;", "import com.hbm.util.RTGUtil.HalfLifeType;"]
    ck("V3.ntmitems-insert-only", deleted == [old_line] and len(inserted) == 3 + len(block) and all(i in imports for i in inserted[:3]) and collections.Counter(inserted[3:]) == collections.Counter(x.strip() for x in block),
       "NtmItems is the start copy plus 3 imports and the pellet block, except the replaced `new Item(...)` PELLET_RTG line", (deleted, len(inserted)))
    ck("V3.ntmitems-crlf", eol_of(text) == eol_of(start) == "\r", "NtmItems keeps CRLF line endings")
    # enum and class shapes
    dep = st.text(RPD)
    ck("V3.depleted-enum", re.findall(r"\b([A-Z]+)\b", re.search(r"enum DepletedRTGMaterial \{(.*?)\}", blank_comments(dep), re.S)[1]) == p["depleted_enum"], "RTGPelletDepletedItem.DepletedRTGMaterial equals the original enum order (ordinal = hbmsntm:meta)")
    ck("V3.depleted-class", "extends EnumMultiItem" in dep and "super(properties, DepletedRTGMaterial.class, true, true);" in dep, "RTGPelletDepletedItem is an EnumMultiItem with multiName and multiTexture like the original")
    item = st.text(RPI)

    def mc(sig):
        return method_code(item, sig)
    shapes = {
        "ctor-int": (mc("public RTGPelletItem(Properties properties, int heat)"), "this(properties, () -> heat);"),
        "ctor": (mc("public RTGPelletItem(Properties properties, IntSupplier heat)"), "super(properties.stacksTo(1)); this.heat = heat; PELLETS.add(this);"),
        "setDecays": (mc("public RTGPelletItem setDecays(DepletedRTGMaterial mat, long life)"), "doesDecay = true; decayMaterial = mat; lifespan = life; return this;"),
        "getDecayItem": (mc("public ItemStack getDecayItem()"), "return decayMaterial == null ? ItemStack.EMPTY : MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, decayMaterial.ordinal());"),
        "handleDecay-2": (mc("public static ItemStack handleDecay(ItemStack stack, RTGPelletItem instance) {"), "return handleDecay(stack, instance, RTGUtil.rtgDecay());"),
        "handleDecay-3": (mc("public static ItemStack handleDecay(ItemStack stack, RTGPelletItem instance, boolean decay)"),
                          "if(instance.getDoesDecay() && decay) { if(instance.getLifespan(stack) <= 0) return instance.getDecayItem(); else instance.decay(stack); } return stack;"),
        "decay": (mc("public void decay(ItemStack stack)"), "if(stack.getItem() instanceof RTGPelletItem pellet) { if(!pellet.getDoesDecay()) return; setLifespan(stack, getLifespan(stack) - 1); }"),
        "getLifespan": (mc("public long getLifespan(ItemStack stack)"), "if(stack.getItem() instanceof RTGPelletItem) { CompoundTag tag = TagsUtil.getCustomData(stack); "
                        "return tag.contains(KEY_DEPLETION, Tag.TAG_ANY_NUMERIC) ? tag.getLong(KEY_DEPLETION) : getMaxLifespan(); } return 0;"),
        "setLifespan": (mc("public static void setLifespan(ItemStack stack, long life)"), "CompoundTag tag = TagsUtil.getCustomData(stack); tag.putLong(KEY_DEPLETION, life); TagsUtil.putCustomData(stack, tag);"),
        "getScaledPower": (mc("public static int getScaledPower(RTGPelletItem fuel, ItemStack stack)"),
                           "return (short) Math.ceil(fuel.getHeat() * ((double) fuel.getLifespan(stack) / (double) fuel.getMaxLifespan()));"),
        "getDepletion": (mc("public double getDepletion(ItemStack stack)"), "if(getMaxLifespan() <= 0) return 0D; return 1D - (double) getLifespan(stack) / (double) getMaxLifespan();"),
        "isBarVisible": (mc("public boolean isBarVisible(ItemStack stack)"), "return getDoesDecay() && getLifespan(stack) != getMaxLifespan();"),
    }
    bad = {k: v[0] for k, v in shapes.items() if v[0] != v[1]}
    ck("V3.item-shapes", not bad, "RTGPelletItem: stacksTo(1) in the constructor, PELLETS.add(this), setDecays, handleDecay (<= 0 returns the decay stack), decay writes life - 1, getLifespan reads the key "
       "and writes nothing, getScaledPower = (short) ceil(heat * (double) life / (double) max), getDepletion = 1 - life/max, isBarVisible", bad)
    ck("V3.item-key-facts", 'KEY_DEPLETION = "PELLET_DEPLETION"' in item and re.search(r"FACTS = 16;", item) and "PELLETS = new ArrayList<>()" in item, "the key is PELLET_DEPLETION, FACTS = 16 and PELLETS is the static list")
    use = mc("public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)")
    ck("V3.item-use", "if(this == NtmItems.PELLET_RTG.get())" in use and "if(!level.isClientSide) {" in use and 0 <= use.find("!level.isClientSide") < use.find("sendSystemMessage") and "level.random.nextInt(FACTS) + 1" in use
       and "SoundEvents.EXPERIENCE_ORB_PICKUP" in use and use.count("this ==") == 1 and "super.use(level, player, hand)" in use, "use acts only for pellet_rtg, only when !level.isClientSide: a random fact (1..16) in a system message and the orb sound", use)
    code = blank_comments(item)
    keys = set(re.findall(r'Component\.(?:translatable|literal)\("([\w.]+)"', code))
    ck("V3.item-tooltip-keys", {"desc.item.rtgHeat", "desc.item.rtgDecay", "desc.item.rtgExtended", "desc.item.rtgTicks", "desc.item.rtgRemaining", "desc.item.rtgMaxLife"} <= keys
       and 'this.getDescriptionId() + ".desc"' in code and 'Component.translatable("desc.item.pellet_rtg.fact." +' in code and "tooltipFlag.isAdvanced()" in code and "RTGUtil.scaleRTGPower()" in code,
       "appendHoverText uses <id>.desc, desc.item.rtgHeat (scaled when scaleRTGPower), rtgDecay, and the four extended keys under the advanced flag", sorted(keys))
    # RTGUtil
    ru = st.text(RTGU)

    def uc(sig):
        return method_code(ru, sig)
    shapes = {
        "rtgDecay": (uc("public static boolean rtgDecay()"), "return NtmConfig.enable528() || NtmConfig.COMMON.DO_RTGS_DECAY.get();"),
        "scaleRTGPower": (uc("public static boolean scaleRTGPower()"), "return NtmConfig.enable528() || NtmConfig.COMMON.SCALE_RTG_POWER.get();"),
        "getPower-3": (uc("public static int getPower(RTGPelletItem fuel, ItemStack stack, boolean scale)"), "return scale ? RTGPelletItem.getScaledPower(fuel, stack) : fuel.getHeat();"),
        "getPower-2": (uc("public static int getPower(RTGPelletItem fuel, ItemStack stack) {"), "return getPower(fuel, stack, scaleRTGPower());"),
        "updateRTGs-2": (uc("public static int updateRTGs(NonNullList<ItemStack> inventory, int[] rtgSlots) {"), "return updateRTGs(inventory, rtgSlots, rtgDecay(), scaleRTGPower());"),
    }
    bad = {k: v[0] for k, v in shapes.items() if v[0] != v[1]}
    ck("V3.rtgutil-switches", not bad, "RTGUtil.rtgDecay/scaleRTGPower = enable528 || the config key, getPower scales only when asked, the default updateRTGs reads both switches", bad)
    upd = uc("public static int updateRTGs(NonNullList<ItemStack> inventory, int[] rtgSlots, boolean decay, boolean scale)")
    ck("V3.rtgutil-update", "newHeat += getPower(pellet, stack, scale);" in upd and "inventory.set(slot, RTGPelletItem.handleDecay(stack, pellet, decay));" in upd
       and upd.index("newHeat += getPower") < upd.index("handleDecay(") and "return newHeat;" in upd and "if(stack.isEmpty()) continue;" in upd, "the explicit updateRTGs adds getPower before handleDecay, skips empty and non-pellet slots and returns the heat", upd)
    ck("V3.rtgutil-hasheat", "instanceof RTGPelletItem" in uc("public static boolean hasHeat(NonNullList<ItemStack> inventory, int[] rtgSlots)"), "hasHeat tests for RTGPelletItem")
    life = squash(uc("public static long getLifespan(float halfLife, HalfLifeType type, boolean realYears)"))
    ck("V3.rtgutil-lifespan", life == p["rtgutil_lifespan"].replace("switch(type)", "switch(type)") and "life=48000*halfLife;" in life, "RTGUtil.getLifespan is the original float code (squashed bodies are equal)", life)
    ck("V3.rtgutil-halflife", re.findall(r"\b([A-Z]+)\b", blank_comments(re.search(r"enum HalfLifeType \{(.*?)\n    \}", ru, re.S)[1])) == p["halflife_enum"], "RTGUtil.HalfLifeType is SHORT, MEDIUM, LONG as the original")
    # CommonConfig
    cc = st.text(CC)
    start_cc = inp.start[CC]
    deleted, inserted = diff_summary(start_cc, cc)
    ck("V3.config-insert-only", not deleted and len(inserted) == 14, "CommonConfig is the start copy plus 14 inserted lines (comment, two fields, the rtg section)", (deleted, len(inserted)))
    ck("V3.config-crlf", eol_of(cc) == eol_of(start_cc) == "\r" and hashed_equal(inp, st, NC), "CommonConfig keeps CRLF and NtmConfig is unchanged")
    pushed = re.search(r'builder\.push\("rtg"\);(.*?)builder\.pop\(\);', cc, re.S)
    cfg_ok, cfg_detail = bool(pushed), []
    if pushed:
        section = pushed[1]
        for (key, field, comment, default), o in zip(CONFIG_ROWS, p["config"]):
            m = re.search(field + r' = builder\s*\.comment\("([^"]*)"\)\s*\.translation\("([^"]*)"\)\s*\.define\("(\w+)", (true|false)\);', section)
            want = (o["comment"] if o else None, "hbmsntm.configuration." + key, key, o["default"] if o else None)
            got = (m[1], m[2], m[3], m[4]) if m else None
            if got != want or o is None or o["key"].split("_", 1)[1] != key or (key, default, comment) != (o["key"].split("_", 1)[1], o["default"], o["comment"]):
                cfg_ok = False
                cfg_detail.append((got, want))
    ck("V3.config-rtg-section", cfg_ok and len(re.findall(r"public final BooleanValue (SCALE_RTG_POWER|DO_RTGS_DECAY);", cc)) == 2,
       "section `rtg` has scaleRTGPower (false) and doRTGsDecay (true), the comments equal the original MachineConfig's and the translation keys are hbmsntm.configuration.<name>", cfg_detail)
    en_keys, _ = json_pairs(st.text(EN))
    zh_keys, _ = json_pairs(st.text(ZH))
    ck("V3.config-no-language-entry", not [k for k in en_keys if k.startswith("hbmsntm.configuration.")] and not [k for k in zh_keys if k.startswith("hbmsntm.configuration.")]
       and len(re.findall(r'\.translation\("hbmsntm\.configuration\.', cc)) >= 81, "no existing hbmsntm.configuration.* key has a language entry (none of the 81+ translation keys, the two new ones included)")
    if facts_out is not None:
        facts_out["V3"] = dict(neo_rows=[(r["line"], r["id"], r["heat"], r["mat"], r["half"], r["type"]) for r in rows], block_lines=len(block))


# ---------------------------------------------------------------- V4

def jload(st, path):
    return json.loads(st.text(path))


def v4_recipes(ck, inp, st, facts_out=None):
    p = inp.parsed
    bad = []
    for (pid, billets), o in zip(RECIPE_ROWS, p["recipes"]):
        path = f"{RECIPES}{pid}.json"
        if not st.has(path):
            bad.append((pid, "missing"))
            continue
        data = jload(st, path)
        want_ing = sorted(f"hbmsntm:{x}" for x in o["ingredients"])
        got_ing = sorted(i.get("item") for i in data.get("ingredients", []) if set(i) == {"item"})
        ok = (data.get("type") == "minecraft:crafting_shapeless" and data.get("category") == "misc" and got_ing == want_ing and len(data.get("ingredients", [])) == 4
              and data.get("result") == {"count": 1, "id": f"hbmsntm:{pid}"} and set(data) == {"type", "category", "ingredients", "result"})
        if not ok:
            bad.append((pid, data))
        if o["id"] != pid:
            bad.append((pid, "original id differs", o["id"]))
    ck("V4.pellet-recipes", not bad, "the ten generated pellet recipes are minecraft:crafting_shapeless with the original's ingredient multiset (3 billets + hbmsntm:plate_iron) and result count 1", bad)
    rec_bad = []
    originals = {r["mat"]: r for r in p["recycle"]}
    for mat, result, count in RECYCLE_NEO:
        path = f"{RECIPES}pellet_rtg_depleted_{mat.lower()}.json"
        if not st.has(path):
            rec_bad.append((mat, "missing"))
            continue
        data = jload(st, path)
        o = originals[mat]
        ing = data.get("ingredients", [])
        ing_ok = (len(ing) == 1 and ing[0].get("type") == "neoforge:components" and ing[0].get("items") == "hbmsntm:pellet_rtg_depleted"
                  and ing[0].get("components") == {"hbmsntm:meta": MATS.index(mat)} and ing[0].get("strict", False) is False and set(ing[0]) <= {"type", "components", "items", "strict"})
        if not (data.get("type") == "minecraft:crafting_shapeless" and ing_ok and data.get("result") == {"count": count, "id": f"hbmsntm:{result}"}
                and (o["result"], o["count"]) == (result, count) and set(data) == {"type", "category", "ingredients", "result"}):
            rec_bad.append((mat, data))
    ck("V4.recycling-recipes", not rec_bad, "pellet_rtg_depleted_{bismuth,lead,neptunium,zirconium}: one neoforge:components ingredient on hbmsntm:pellet_rtg_depleted with hbmsntm:meta = the ordinal, "
       "strict absent or false, results 3 billet_bismuth / 2 ingot_lead / 3 billet_neptunium / 3 billet_zirconium (equal to the original's counts)", rec_bad)
    ck("V4.no-mercury-nickel", not st.has(RECIPES + "pellet_rtg_depleted_mercury.json") and not st.has(RECIPES + "pellet_rtg_depleted_nickel.json")
       and not [k for k in st.tree if k.startswith(RECIPES + "pellet_rtg_depleted_") and k.endswith(("mercury.json", "nickel.json"))], "no pellet_rtg_depleted_mercury and no pellet_rtg_depleted_nickel recipe exists")
    ck("V4.recipe-file-set", sorted(k[len(RECIPES):] for k in st.files if k.startswith(RECIPES + "pellet_rtg")) == sorted([f"{i}.json" for i in IDS] + [f"pellet_rtg_depleted_{m.lower()}.json" for _, m in [(0, x[0]) for x in RECYCLE_NEO]]),
       "the pellet_rtg* recipe files are exactly the 10 + 4")
    # provider source
    prov = st.text(RP)
    start = inp.start[RP]
    deleted, inserted = diff_summary(start, prov)
    blocks = []
    for sig in ("private void registerRTGPelletRecipes(RecipeOutput recipeOutput)", "private void addRTGPelletRecipe(", "private void addRTGRecyclingRecipe("):
        blocks += method_block_lines(prov, sig)
    expected = collections.Counter(blocks + ["import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;", "import java.util.Locale;", "registerRTGPelletRecipes(recipeOutput);"])
    ck("V4.provider-insert-only", not deleted and collections.Counter(inserted) == expected, "NtmRecipeProvider is the start copy plus two imports, the call and the three RTG methods with their comments", (deleted[:3], len(inserted), sum(expected.values())))
    body = method_code(prov, "private void registerRTGPelletRecipes(RecipeOutput recipeOutput)")
    prow = re.findall(r"addRTGPelletRecipe\(recipeOutput, NtmItems\.(\w+)\.get\(\), NtmItems\.(\w+)\.get\(\), NtmItems\.(\w+)\.get\(\), NtmItems\.(\w+)\.get\(\)\);", body)
    lines = lf(prov).split("\n")
    pcomments = [int(m[1]) for l in lines for m in [re.search(r"addRTGPelletRecipe\(recipeOutput, .*\); // :(\d+)\s*$", l)] if m]
    ck("V4.provider-pellet-rows", [(r[0].lower(), [x.lower() for x in r[1:]]) for r in prow] == [(o["id"], [x for x in o["ingredients"] if x != "plate_iron"]) for o in p["recipes"]] and pcomments == [o["line"] for o in p["recipes"]],
       "registerRTGPelletRecipes lists the ten pellets in the original order with the original's billets and the original MineralRecipes line in each comment", (prow, pcomments))
    rrow = re.findall(r"addRTGRecyclingRecipe\(recipeOutput, DepletedRTGMaterial\.(\w+), NtmItems\.(\w+)\.get\(\), (\d+)\);", body)
    rcomments = [int(m[1]) for l in lines for m in [re.search(r"addRTGRecyclingRecipe\(recipeOutput, .*\); // :(\d+)\s*$", l)] if m]
    ck("V4.provider-recycling-rows", [(m, r.lower(), int(c)) for m, r, c in rrow] == RECYCLE_NEO and rcomments == [217, 218, 220, 221], "the four recycling rows equal the original's bismuth, lead, neptunium and zirconium rows (counts and lines)", (rrow, rcomments))
    pm = method_block_lines(prov, "private void registerRTGPelletRecipes(RecipeOutput recipeOutput)")
    joined = "\n".join(pm)
    ck("V4.provider-skipped-comments", re.search(r"// :219, mercury -> 2 ingot_mercury, is not registered", joined) and re.search(r"// :222-226, nickel", joined), "the provider comments the two skipped rows (:219 mercury, :222-226 nickel) with their reason")
    one = method_code(prov, "private void addRTGPelletRecipe(")
    two = method_code(prov, "private void addRTGRecyclingRecipe(")
    ck("V4.provider-builders", "ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, pellet, 1)" in one and ".requires(first) .requires(second) .requires(third) .requires(NtmItems.PLATE_IRON.get())" in one
       and 'ResourceLocation.fromNamespaceAndPath("hbmsntm", pelletName)' in one and "ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, result, count)" in two
       and ".requires(DataComponentIngredient.of(false, NtmDataComponents.META, material.ordinal(), NtmItems.PELLET_RTG_DEPLETED.get()))" in two
       and '"pellet_rtg_depleted_" + material.name().toLowerCase(Locale.US)' in two, "the builders: three billets + plate_iron into the pellet id; a non-strict META DataComponentIngredient into pellet_rtg_depleted_<material>", (one, two))
    ck("V4.provider-crlf", eol_of(prov) == eol_of(start) == "\r", "NtmRecipeProvider keeps CRLF line endings")


# ---------------------------------------------------------------- V5

def hazard_pellet_rows(code_method):
    rows = []
    for m in re.finditer(r"registerRTGPellet\((\w+), ([^,]+), ([^,)]+)((?:, [^,)]+)*)\);", code_method):
        extra = [float(x.strip().rstrip("fF")) for x in m[4].split(",") if x.strip()]
        rows.append((m[1].lower(), squash(m[2]), float(m[3].rstrip("fF")), extra[0] if extra else 0.0, extra[1] if len(extra) > 1 else 0.0))
    return rows


def v5_hazards(ck, inp, st, facts_out=None):
    p = inp.parsed
    text = st.text(HR)
    start = inp.start[HR]
    sig = "private static void registerRTGPellets()"
    body = method_code(text, sig)
    rows = hazard_pellet_rows(body)
    want = [(r["pellet"], r["expr"], r["target"], r["hot"], r["blinding"]) for r in p["hazard"]]
    ck("V5.rows-equal-original", rows == want and rows == [(h[0], h[1], float(h[2]), float(h[3]), float(h[4])) for h in HAZARD_ROWS],
       "registerRTGPellets holds the ten registerRTGPellet rows of the original (pellet, expression, target 0, hot, blinding) in the original order", [(a, b) for a, b in zip(rows, want) if a != b] or rows)
    statements = [s.strip() for s in body.split(";") if s.strip()]
    np_state = [s for s in statements if "PELLET_RTG_DEPLETED" in s]
    np_ok = len(np_state) == 1 and norm(np_state[0]) == "HazardSystem.register(MetaHelper.newStack(PELLET_RTG_DEPLETED, 1, DepletedRTGMaterial.NEPTUNIUM.ordinal()), makeData(RADIATION, np237 * rtg))"
    ck("V5.np-stack-row", np_ok and len(statements) == 11 and p["hazard_np"]["mat"] == "NEPTUNIUM" and p["hazard_np"]["expr"] == "np237*rtg",
       "the depleted neptunium row is a MetaHelper.newStack(PELLET_RTG_DEPLETED, 1, NEPTUNIUM.ordinal()) stack row with RADIATION np237 * rtg, and the method has exactly 11 statements", (np_state, len(statements)))
    ck("V5.call-order", re.search(r"registerMaterialAddendum\(\);\s*registerRTGPellets\(\);", blank_comments(text)) is not None, "registerRTGPellets() is called right after registerMaterialAddendum()")
    helper = squash(method_code(text, "private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target, float hot, float blinding)"))
    o_helper = p["helper"][0].replace("HazardSystem.register(pellet,data);", "HazardSystem.register(pellet.get(),data);")
    h2 = squash(method_code(text, "private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target) {"))
    h4 = squash(method_code(text, "private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target, float hot) {"))
    ck("V5.helper", helper == o_helper and h2 == p["helper"][1] and h4 == p["helper"][2] and "newHazardModifierRTGRadiation(target)" in helper.replace("(", "(", 1),
       "the helper adds RADIATION base with HazardModifierRTGRadiation(target), HOT when hot > 0, BLINDING when blinding > 0 (the original's body) and the two overloads", (helper, o_helper))
    deleted, inserted = diff_summary(start, text)
    old_comment = "// :337-347, the eleven RTG pellet rows (registerRTGPellet), are deferred with the RTG modifier: NEO has no HazardModifierRTGRadiation."
    blocks = method_block_lines(text, sig)
    lines = lf(text).split("\n")
    first = next(i for i, l in enumerate(lines) if "private static void registerRTGPellet(DeferredItem<Item> pellet, float base, float target) {" in l)
    last = next(i for i in range(first, len(lines)) if lines[i].startswith("    }") and i > first + 3 and "HazardSystem.register(pellet.get(), data);" in "\n".join(lines[first:i]))
    blocks += [x.strip() for x in lines[first:last + 1] if x.strip()]
    expected = collections.Counter(blocks + ["import com.hbm.hazard.modifier.HazardModifierRTGRadiation;", "import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;", "registerRTGPellets();",
                                             "// :337-347, the eleven RTG pellet rows (registerRTGPellet), are registered in registerRTGPellets (Goal23B)."])
    ck("V5.registry-insert-only", deleted == [old_comment] and collections.Counter(inserted) == expected,
       "HazardRegistry is the start copy plus two imports, the call, the registerRTGPellets method, the three helpers and the one replaced comment line (the :337-347 deferral now points to registerRTGPellets)", (deleted, len(inserted), sum(expected.values())))
    ck("V5.registry-crlf", eol_of(text) == eol_of(start) == "\r", "HazardRegistry keeps CRLF line endings")
    names = float_constants(text)
    ck("V5.constants-equal-original", all(n in names and n in p["constants"] and names[n].v == p["constants"][n].v for n in CONSTANTS) and names["rtg"].v == f32(1.5),
       "the thirteen constants (pu238 ra226 u238 sr90 co60 ac227 po210 pb209 au198 am241 np237 billet rtg) equal the original's in float32", {n: (names.get(n) and names[n].v, p["constants"].get(n) and p["constants"][n].v) for n in CONSTANTS})
    levels, exp_levels = [], []
    for row, h in zip(rows, HAZARD_ROWS):
        levels.append(eval_float(row[1], names).v if all(n in names for n in CONSTANTS) else None)
        exp_levels.append(f32(h[5]))
    levels.append(eval_float("np237*rtg", names).v)
    exp_levels.append(f32(NP_ROW[2]))
    ck("V5.levels", levels == exp_levels, "the float32 levels from NEO's constants are 15, 11.25, 5.25, 22.5, 45, 45, 112.5, 15000, 750, 12.75 and 3.75", list(zip(levels, exp_levels)))
    mod = st.text(MOD)
    mbody = squash(method_code(mod, "public float modify(ItemStack stack, LivingEntity holder, float level)"))
    ck("V5.modifier", mbody == "if(!(stack.getItem()instanceofRTGPelletItemfuel))returnlevel;doubledepletion=fuel.getDepletion(stack);level=(float)(level+(this.target-level)*depletion);returnlevel;"
       and "extends HazardModifier" in mod, "HazardModifierRTGRadiation.modify is level + (target - level) * depletion, guarded by instanceof RTGPelletItem (other stacks keep their level)", mbody)
    if facts_out is not None:
        facts_out["V5"] = dict(rows=rows, float32_levels=levels, expected_levels=exp_levels)


# ---------------------------------------------------------------- V6

def expected_lang(inp, review):
    """key -> dict(kind, en, zh, source_key, source_en, source_zh) for the 47 new keys."""
    out = {}

    def up(key, source):
        out[key] = dict(kind="upstream", en=inp.o_en[source], zh=inp.o_zh[source], source_key=source, source_en=inp.o_en[source], source_zh=inp.o_zh[source])
    up("item.hbmsntm.pellet_rtg.desc", "item.pellet_rtg.desc")
    for i in NEW_IDS:
        up(f"item.hbmsntm.{i}", f"item.{i}.name")
        up(f"item.hbmsntm.{i}.desc", f"item.{i}.desc")
    for m in MATS:
        up(f"item.hbmsntm.pellet_rtg_depleted.{m.lower()}", f"item.pellet_rtg_depleted.{m.lower()}.name")
    up("desc.item.rtgHeat", "desc.item.rtgHeat")
    up("desc.item.rtgDecay", "desc.item.rtgDecay")
    out["item.hbmsntm.pellet_rtg_polonium.desc"]["kind"] = "local"
    out["item.hbmsntm.pellet_rtg_polonium.desc"]["zh"] = review.get("item.hbmsntm.pellet_rtg_polonium.desc", {}).get("zh")
    for k, en in EXT_KEYS.items():
        out[k] = dict(kind="local", en=en, zh=review.get(k, {}).get("zh"))
    for n, fact in enumerate(inp.parsed["facts"], 1):
        out[f"desc.item.pellet_rtg.fact.{n}"] = dict(kind="local", en=fact.replace("%", "%%"), zh=review.get(f"desc.item.pellet_rtg.fact.{n}", {}).get("zh"))
    return out


def placeholders(text):
    return collections.Counter(re.findall(r"%%|%[sd]", text))


def v6_models_lang(ck, inp, st, facts_out=None):
    # --- models
    bad = []
    for i in NEW_IDS:
        path = f"{MODELS}{i}.json"
        want = {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/{i}"}}
        if not st.has(path) or jload(st, path) != want:
            bad.append(i)
        if f"{TEX}{i}.png" not in st.tree:
            bad.append(i + ".png")
    ck("V6.models-nine", not bad and jload(st, MODELS + "pellet_rtg.json") == {"parent": "minecraft:item/generated", "textures": {"layer0": "hbmsntm:item/pellet_rtg"}},
       "the nine new pellet models are minecraft:item/generated with layer0 hbmsntm:item/<id> (texture present); pellet_rtg.json is unchanged in shape", bad)
    dep_ok = st.has(MODELS + "pellet_rtg_depleted.json") and jload(st, MODELS + "pellet_rtg_depleted.json") == {"overrides": [
        {"model": f"hbmsntm:item/pellet_rtg_depleted_{n}", "predicate": {"hbmsntm:item_meta": float(n)}} for n in range(6)]}
    sub_ok = all(st.has(f"{MODELS}pellet_rtg_depleted_{n}.json") and jload(st, f"{MODELS}pellet_rtg_depleted_{n}.json") ==
                 {"parent": "minecraft:item/generated", "textures": {"layer0": f"hbmsntm:item/pellet_rtg_depleted.{m.lower()}"}} and f"{TEX}pellet_rtg_depleted.{m.lower()}.png" in st.tree for n, m in enumerate(MATS))
    ck("V6.models-depleted", dep_ok and sub_ok, "pellet_rtg_depleted.json has the six hbmsntm:item_meta overrides 0..5 and pellet_rtg_depleted_0..5.json point to hbmsntm:item/pellet_rtg_depleted.<material> (texture present)")
    ck("V6.model-file-set", sorted(k[len(MODELS):] for k in st.files if k.startswith(MODELS + "pellet_rtg")) == sorted(["pellet_rtg.json"] + [f"{i}.json" for i in NEW_IDS] + ["pellet_rtg_depleted.json"] + [f"pellet_rtg_depleted_{n}.json" for n in range(6)]),
       "the generated pellet_rtg* models are exactly 1 + 9 + 1 + 6")
    mp = st.text(MP)
    deleted, inserted = diff_summary(inp.start[MP], mp)
    ck("V6.model-provider-eol", eol_of(mp) == eol_of(inp.start[MP]), "NtmItemModelProvider keeps its line-ending convention")
    ck("V6.model-provider", not deleted and collections.Counter(inserted) == collections.Counter(["// Goal23B RTG pellets; pellet_rtg_depleted (EnumMultiItem) gets its meta overrides from the ICustomItemModelRegister loop above."]
                                                                                                    + [f"this.basicItem(NtmItems.{i.upper()}.get());" for i in NEW_IDS]), "NtmItemModelProvider is the start copy plus one comment and nine basicItem calls (no custom model for pellet_rtg_depleted)", (deleted, inserted))
    # --- creative tab
    ct = st.text(CT)
    lines = lf(ct).split("\n")
    icon = [i for i, l in enumerate(lines) if ".icon(() -> new ItemStack(NtmItems.PELLET_RTG.get()))" in l]
    seq = []
    if len(icon) == 1:
        end = next((i for i in range(icon[0] + 1, len(lines)) if "CREATIVE_MODE_TABS.register(" in lines[i]), len(lines))
        seq = [(i, l.strip()) for i, l in enumerate(lines[icon[0]:end], icon[0]) if "PELLET_RTG" in l and i != icon[0]]
    want_seq = [f"output.accept(NtmItems.{i.upper()});" for i in IDS] + ["addMetaItems(output, NtmItems.PELLET_RTG_DEPLETED.get());"]
    contiguous = bool(seq) and [i for i, _ in seq] == list(range(seq[0][0], seq[0][0] + len(seq)))
    ck("V6.creative-tab", len(icon) == 1 and [l for _, l in seq] == want_seq and contiguous and ct.count("PELLET_RTG") == 12,
       "NtmCreativeTabs CONTROL keeps the PELLET_RTG icon and lists the ten pellets in registration order followed by addMetaItems(output, PELLET_RTG_DEPLETED.get()), contiguous, 12 PELLET_RTG references in the file", [l for _, l in seq])
    deleted, inserted = diff_summary(inp.start[CT], ct)
    ck("V6.creative-insert-only", not deleted and collections.Counter(x for x in inserted if not x.startswith("//")) == collections.Counter(want_seq) and eol_of(ct) == "\r"
       and any(x.startswith("//") for x in inserted), "NtmCreativeTabs is the start copy plus a block of // comment lines and the eleven item lines (nothing else), CRLF kept", (deleted, len(inserted)))
    o_register = re.findall(r"GameRegistry\.registerItem\((pellet_rtg\w*), ", inp.o["moditems"])
    neo_order = list(IDS) + ["pellet_rtg_depleted"]
    facts_v6 = dict(original_registerItem_order=o_register, neo_creative_tab_order=neo_order, creative_order_differs_from_original=o_register != neo_order,
                    note="NEO lists the pellets in construction order (ModItems.java:2647-2656, the handoff's registration order); the original registers the items with registerItem in a different "
                         "order (polonium before americium, ModItems.java:5040-5050), which decides its creative-tab order. Documented in the NtmCreativeTabs comment; reported, not failed.")
    # --- language
    review_data = jload(st, REV)
    review = {e["key"]: e for e in review_data["new_keys"]}
    exp = expected_lang(inp, review)
    keys = sorted(exp)
    live_en, edups = json_pairs(st.text(EN))
    live_zh, zdups = json_pairs(st.text(ZH))
    start_en, _ = json_pairs(inp.start[EN])
    start_zh, _ = json_pairs(inp.start[ZH])
    ck("V6.key-count", len(exp) == 47 and len(set(keys)) == 47, "the expected key set has 47 keys (19 names/descriptions, 6 depleted, 2 tooltip, 4 extended, 16 facts)", len(exp))
    en_added = {k: live_en[k] for k in live_en if k not in start_en}
    zh_added = {k: live_zh[k] for k in live_zh if k not in start_zh}
    ck("V6.en-added-exact", set(en_added) == set(keys), "the generated en_us.json gains exactly the 47 keys", (sorted(set(en_added) ^ set(keys))[:6], len(en_added)))
    ck("V6.zh-added-exact", set(zh_added) == set(keys), "zh_cn.json gains exactly the 47 keys", (sorted(set(zh_added) ^ set(keys))[:6], len(zh_added)))
    ck("V6.en-values", all(live_en.get(k) == exp[k]["en"] for k in keys), "every English value equals the original en_US.lang (names, descriptions, tooltips), the original ItemRTGPellet literals (extended lines, facts with % -> %%)",
       {k: (live_en.get(k), exp[k]["en"]) for k in keys if live_en.get(k) != exp[k]["en"]})
    ck("V6.zh-upstream-values", all(live_zh.get(k) == exp[k]["zh"] for k in keys if exp[k]["kind"] == "upstream"), "the 25 upstream-Chinese keys equal the original zh_CN.lang (including the space in the lead pellet name)",
       {k: (live_zh.get(k), exp[k]["zh"]) for k in keys if exp[k]["kind"] == "upstream" and live_zh.get(k) != exp[k]["zh"]})
    local = [k for k in keys if exp[k]["kind"] == "local"]
    ck("V6.zh-local-values", len(local) == 21 and all(exp[k]["zh"] and live_zh.get(k) == exp[k]["zh"] and re.search(r"[一-鿿]", live_zh[k]) and placeholders(live_zh[k]) == placeholders(live_en[k]) for k in local),
       "the 21 local keys have Chinese equal to goal23b-localization-review.json, with CJK text and the same placeholders (%s, %%) as the English", [k for k in local if live_zh.get(k) != exp[k]["zh"] or placeholders(live_zh.get(k, "")) != placeholders(live_en.get(k, ""))])
    polonium = "item.hbmsntm.pellet_rtg_polonium.desc"
    ck("V6.polonium-desc-differs", live_zh.get(polonium) != inp.o_zh.get("item.pellet_rtg_polonium.desc") and live_zh.get(polonium), "the polonium description is a local retranslation (it differs from the original Chinese)")
    en_other = [k for k in start_en if k not in live_en or start_en[k] != live_en[k]]
    zh_other = [k for k in start_zh if k not in live_zh or start_zh[k] != live_zh[k]]
    ck("V6.no-other-change", not en_other and not zh_other and not edups and not zdups, "no other en_us.json / zh_cn.json key is removed, changed or duplicated", (en_other[:3], zh_other[:3], edups[:3], zdups[:3]))
    for name, start, live in (("en_us.json", inp.start[EN], st.text(EN)), ("zh_cn.json", inp.start[ZH], st.text(ZH))):
        ok, ins = insert_only(start, live)
        ck(f"V6.{name}-47-lines", ok and len(ins) == 47, f"{name} is the start text plus exactly 47 inserted lines", ins[:3])
        ck(f"V6.{name}-eol", eol_of(live) == eol_of(start), f"{name} keeps the start line-ending convention ({'CRLF' if eol_of(start) else 'LF'})")
    ck("V6.zh-format", format_ok(st.text(ZH), live_zh), "zh_cn.json is json.dumps(indent=2, ensure_ascii=False) in one line-ending convention")
    # --- provider
    prov = st.text(LP)
    deleted, inserted = diff_summary(inp.start[LP], prov)
    adds = [x for x in inserted if x.startswith("this.add(")]
    ck("V6.provider-insert-only", not deleted and len(adds) == 47 and len(inserted) == 47 + 1 + 4 and "import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;" in inserted
       and all(x.startswith("//") for x in inserted if not x.startswith("this.add(") and not x.startswith("import ")), "NtmLanguageProvider is the start copy plus one import, 47 this.add lines and 4 comment lines", (deleted, len(inserted), len(adds)))
    values = {}
    for x in adds:
        m = (re.match(r'this\.add\(NtmItems\.(\w+), DESC, "((?:[^"\\]|\\.)*)"\);$', x) and ("desc",) + re.match(r'this\.add\(NtmItems\.(\w+), DESC, "((?:[^"\\]|\\.)*)"\);$', x).groups()) \
            or (re.match(r'this\.add\(NtmItems\.PELLET_RTG_DEPLETED, this\.getName\(DepletedRTGMaterial\.(\w+)\), "((?:[^"\\]|\\.)*)"\);$', x) and ("dep",) + re.match(
                r'this\.add\(NtmItems\.PELLET_RTG_DEPLETED, this\.getName\(DepletedRTGMaterial\.(\w+)\), "((?:[^"\\]|\\.)*)"\);$', x).groups()) \
            or (re.match(r'this\.add\(NtmItems\.(\w+), "((?:[^"\\]|\\.)*)"\);$', x) and ("name",) + re.match(r'this\.add\(NtmItems\.(\w+), "((?:[^"\\]|\\.)*)"\);$', x).groups()) \
            or (re.match(r'this\.add\("([\w.]+)", "((?:[^"\\]|\\.)*)"\);$', x) and ("key",) + re.match(r'this\.add\("([\w.]+)", "((?:[^"\\]|\\.)*)"\);$', x).groups())
        if not m:
            values[x] = None
            continue
        kind, a, b = m
        key = {"desc": f"item.hbmsntm.{a.lower()}.desc", "dep": f"item.hbmsntm.pellet_rtg_depleted.{a.lower()}", "name": f"item.hbmsntm.{a.lower()}", "key": a}[kind]
        values[key] = java_string(b)
    ck("V6.provider-agrees", values == {k: exp[k]["en"] for k in keys}, "the provider strings (47) equal the original English and the generated en_us.json values",
       {k: (values.get(k), exp[k]["en"] if k in exp else None) for k in set(values) | set(keys) if values.get(k) != (exp[k]["en"] if k in exp else None)})
    ck("V6.provider-crlf", eol_of(prov) == eol_of(inp.start[LP]) == "\r", "NtmLanguageProvider keeps CRLF line endings")
    # --- mapping
    live_map, mdups = json_pairs(st.text(MAP))
    start_map, _ = json_pairs(inp.start[MAP])
    le, se = live_map["entries"], start_map["entries"]
    added = [k for k in le if k not in se]
    ck("V6.map-added-exact", sorted(added) == keys, "the mapping gains exactly the 47 entries", (sorted(set(added) ^ set(keys))[:5], len(added)))
    ck("V6.map-no-other-change", not [k for k in se if k not in le or se[k] != le[k]] and not mdups and {k: v for k, v in live_map.items() if k != "entries"} == {k: v for k, v in start_map.items() if k != "entries"},
       "no other mapping entry or top-level field changes")
    mbad = []
    n_up = n_local = 0
    for k in keys:
        e, x = le.get(k, {}), exp[k]
        if x["kind"] == "upstream":
            n_up += 1
            want = dict(kind="upstream", source_en=x["source_en"], source_key=x["source_key"], source_zh=x["source_zh"], target_en=x["en"], target_zh=x["zh"])
            if e != want:
                mbad.append((k, e))
        else:
            n_local += 1
            base = {"kind", "reason", "target_en", "target_zh"}
            ok = e.get("kind") == "local" and isinstance(e.get("reason"), str) and e["reason"].strip() and e.get("target_en") == live_en.get(k) and e.get("target_zh") == live_zh.get(k)
            if k == polonium:
                ok = ok and e.get("source_en") == inp.o_en["item.pellet_rtg_polonium.desc"] and e.get("source_zh") == inp.o_zh["item.pellet_rtg_polonium.desc"] and e.get("source_key") == "item.pellet_rtg_polonium.desc" \
                    and set(e) == base | {"source_en", "source_key", "source_zh"}
            else:
                ok = ok and set(e) == base
            if not ok:
                mbad.append((k, e))
    ck("V6.map-entries", not mbad and (n_up, n_local) == (26, 21), "26 upstream entries (source_zh = the original zh_CN.lang, targets equal) and 21 local entries with a reason (polonium description also keeps its source fields)", mbad)
    ck("V6.map-agrees", all(le.get(k, {}).get("target_en") == live_en.get(k) and le.get(k, {}).get("target_zh") == live_zh.get(k) for k in keys), "for the 47 keys the mapping target_en/target_zh equal the generated en_us.json and zh_cn.json")
    ck("V6.map-format", format_ok(st.text(MAP), live_map) and eol_of(st.text(MAP)) == eol_of(inp.start[MAP]), "the mapping is json.dumps(indent=2, ensure_ascii=False) in the start line-ending convention")
    ck("V6.review-agrees", {k: (v["en"], v["zh"], v["kind"]) for k, v in review.items()} == {k: (live_en.get(k), live_zh.get(k), exp[k]["kind"]) for k in keys}
       and review_data.get("upstream", 0) + review_data.get("local", 0) > 0, "goal23b-localization-review.json lists the 47 keys with the live English/Chinese and the expected kinds")
    # --- the Java keys exist
    used = {k for k in re.findall(r'Component\.translatable\("([\w.]+)"', blank_comments(st.text(RPI))) if not k.endswith(".")}  # the fact key is a prefix + 1..16
    ck("V6.item-keys-exist", all(k in live_en and k in live_zh for k in used), "every literal translation key of RTGPelletItem exists in en_us.json and zh_cn.json", sorted(k for k in used if k not in live_en or k not in live_zh))
    if facts_out is not None:
        facts_out["V6"] = dict(keys=keys, kinds=dict(collections.Counter(exp[k]["kind"] for k in keys)), **facts_v6)


# ---------------------------------------------------------------- V7

def v7_textures(ck, inp, st, facts_out=None):
    own = json.loads(st.text(OWN))
    want = {f"{TEX}{i}.png" for i in NEW_IDS} | {f"{TEX}pellet_rtg_depleted.{m.lower()}.png" for m in MATS}
    assets = {a["target_path"]: a for a in own["assets"]}
    ck("V7.ownership-set", set(assets) == want and len(own["assets"]) == 15, "goal23b-resource-ownership.json lists exactly the 15 new textures", sorted(set(assets) ^ want))
    bad = []
    for target, a in assets.items():
        name = Path(target).name
        src = ORIGINAL / O_TEX / name
        live = st.files.get(target)
        if live is None or not src.exists() or live != src.read_bytes() or sha(live) != a["sha256"] or len(live) != a["bytes"] or a["source_path"] != O_TEX + name:
            bad.append(name)
    ck("V7.textures-byte-equal", not bad, "the 15 PNGs are byte-identical to the original textures/items files and to the ownership record (sha256, bytes, source path)", bad)
    live = st.files.get(TEX + "pellet_rtg.png")
    orig = (ORIGINAL / O_TEX / "pellet_rtg.png").read_bytes()
    un = own["unchanged"][0]
    ck("V7.pellet-rtg-png", live == inp.start_png == orig and un["target_sha256"] == un["source_sha256"] == sha(orig), "the existing pellet_rtg.png is unchanged against the start copy and equal to the original (and recorded as unchanged)")
    ck("V7.not-imported", {n["source_path"] for n in own["not_imported"]} == {O_TEX + "pellet_rtg_berkelium.png", O_TEX + "pellet_rtg_americium_tier2.png"}
       and all(not (ROOT / TEX / Path(n["source_path"]).name).exists() for n in own["not_imported"]), "pellet_rtg_berkelium and pellet_rtg_americium_tier2 are recorded as not imported and absent from NEO")
    ck("V7.texture-file-set", sorted(k[len(TEX):] for k in st.files if k.startswith(TEX + "pellet_rtg")) == sorted(Path(w).name for w in want | {TEX + "pellet_rtg.png"}), "the pellet_rtg* textures in NEO are exactly pellet_rtg.png + the 15")


# ---------------------------------------------------------------- V8

def v8_scope(ck, inp, st, facts_out=None):
    base, cur = inp.base_files, st.tree
    src = {p for p in cur if p.startswith("src/")}
    changed = {p for p in src if base.get(p) != cur[p]} | {p for p in base if p.startswith("src/") and p not in cur}
    recipe_ids = IDS + [f"pellet_rtg_depleted_{m.lower()}" for _, m in [(0, x[0]) for x in RECYCLE_NEO]]
    generated = {EN, STAMP} | {f"{MODELS}{i}.json" for i in NEW_IDS} | {MODELS + "pellet_rtg_depleted.json"} | {f"{MODELS}pellet_rtg_depleted_{n}.json" for n in range(6)} \
        | {f"{RECIPES}{r}.json" for r in recipe_ids} | {f"{ADVS}{r}.json" for r in recipe_ids}
    textures = {f"{TEX}{i}.png" for i in NEW_IDS} | {f"{TEX}pellet_rtg_depleted.{m.lower()}.png" for m in MATS}
    expected = set(JAVA_MODIFIED) | set(JAVA_NEW) | {ZH} | textures | generated
    ck("V8.no-unexpected-path", not (changed - expected), "no src/ path outside the batch's modified and new Java files, zh_cn.json, 15 textures and the generated output changed", sorted(changed - expected)[:8])
    gt = {HGT, RGT}
    ck("V8.expected-present", not ((expected - gt) - changed), "every expected src/ path (all but the two GameTest files) changed or was added", sorted((expected - gt) - changed)[:8])
    ck("V8.gametest-files-changed", gt <= changed, "HazardGameTests.java and RTGPelletGameTests.java changed / were added", sorted(gt - changed))
    ck("V8.originals-untouched", inp.original_ok[0], "the original worktree is unchanged (HEAD at the recorded commit, clean)")
    ck("V8.no-removed", not [p for p in base if p.startswith("src/") and p not in cur], "no src/ file was removed", [p for p in base if p.startswith("src/") and p not in cur][:5])
    ck("V8.untouched-neighbours", hashed_equal(inp, st, NC), "NtmConfig is unchanged")
    if facts_out is not None:
        gen_changed = sorted(p for p in changed if p in generated)
        facts_out["V8"] = dict(src_changed=sorted(changed), generated_changed=gen_changed, generated_count=len(gen_changed),
                               not_in_expected=sorted(changed - expected), outside_src={top: sorted(p for p in ({q for q in cur if q.startswith(top)} | {q for q in base if q.startswith(top)}) if base.get(p) != cur.get(p))
                                                                                         for top in ("migration/", "tools/")})


# ---------------------------------------------------------------- V9

TEST_ANNOTATED = re.compile(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper helper\)")


def v9_gametests(ck, inp, st, facts_out=None):
    if not st.has(RGT):
        ck("V9.rtg-file", False, "RTGPelletGameTests.java exists (not yet written by the GameTest builder?)", RGT)
    else:
        live = st.text(RGT)
        tests = {name: args for args, name in TEST_ANNOTATED.findall(live)}
        ck("V9.rtg-nine-tests", list(tests) == RTG_TESTS or sorted(tests) == sorted(RTG_TESTS), "RTGPelletGameTests has the nine @GameTest methods " + ", ".join(RTG_TESTS), sorted(tests))
        ck("V9.rtg-annotation-count", len(re.findall(r"@GameTest\(", live)) == 9, "RTGPelletGameTests has exactly 9 @GameTest( annotations", len(re.findall(r"@GameTest\(", live)))
        ends = [n for n in RTG_TESTS if f'done(helper, "{n}");' not in method_text(live, f"void {n}(GameTestHelper helper)")]
        ck("V9.rtg-logs", 'LOGGER.info("[hbm-rtg] {} passed", name);' in live and not ends, "every test ends in done(helper, \"<name>\"), which logs `[hbm-rtg] <name> passed` and succeeds", ends)
    live, start = st.text(HGT), inp.start[HGT]
    sigs = re.findall(r"public static void (\w+)\(GameTestHelper helper\)", start)
    changed = []
    for name in sigs:
        sig = f"void {name}(GameTestHelper helper)"
        try:
            same = method_text(live, sig) == method_text(start, sig)
        except ValueError as error:
            same = False
            changed.append(f"{name}: {error}")
            continue
        if not same:
            changed.append(name)
    ck("V9.hazard-only-guard-body-changed", changed == [GUARD_TEST], f"in HazardGameTests only the body of {GUARD_TEST} (the RTG guard) differs from the start; every other test method equals it", changed)
    stray = []
    # comment-only changes outside the guard method
    try:
        g_open, g_close, _ = method_span(lf(live), f"void {GUARD_TEST}(GameTestHelper helper)")
        s_open, s_close, _ = method_span(lf(start), f"void {GUARD_TEST}(GameTestHelper helper)")
        outside_live = lf(live)[:g_open] + lf(live)[g_close + 1:]
        outside_start = lf(start)[:s_open] + lf(start)[s_close + 1:]
        o_ops = non_equal_ops(outside_start, outside_live)
        stray = [x.strip() for _, a, b in o_ops for x in a + b if x.strip() and not x.strip().startswith(("*", "//", "/*"))]
    except ValueError as error:
        stray = [repr(error)]
    ck("V9.hazard-other-changes-are-comments", not stray, "outside the guard method only comment lines of HazardGameTests changed", stray[:4])
    guard = method_text(live, f"void {GUARD_TEST}(GameTestHelper helper)")
    ck("V9.hazard-guard-now-asserts-row", not re.search(r'"tile_lab_broken", "pellet_rtg"', guard) and "HazardRegistry.rtg" in guard and "HazardRegistry.HOT" in guard and "pellet_rtg" in guard
       and "deferred with the RTG modifier" not in lf(live), "the guard no longer lists pellet_rtg as hazard-free: it asserts RADIATION pu238 * rtg and HOT, and the `deferred with the RTG modifier` comments are gone")
    ck("V9.hazard-annotation-count", len(re.findall(r"@GameTest\(", live)) == len(re.findall(r"@GameTest\(", start)), "HazardGameTests keeps its @GameTest( count", (len(re.findall(r"@GameTest\(", live)), len(re.findall(r"@GameTest\(", start))))
    ck("V9.hazard-eol", eol_of(live) == eol_of(start), "HazardGameTests keeps its line endings")


# ---------------------------------------------------------------- V10 / V11

def start_gametest_total(inp):
    return inp.gametest_other + len(re.findall(r"@GameTest\(", inp.start[HGT]))


def v10_log(ck, inp, st, path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    total = start_gametest_total(inp) + 9
    live_total = inp.gametest_other + len(re.findall(r"@GameTest\(", st.text(HGT))) + (len(re.findall(r"@GameTest\(", st.text(RGT))) if st.has(RGT) else 0)
    match = re.search(r"All (\d+) required tests passed", text)
    ck("V10.log-all-passed", bool(match) and int(match[1]) == total, f"{Path(path).name} says `All {total} required tests passed` (start annotation total {start_gametest_total(inp)} + 9)", (match and match[0], total))
    ck("V10.annotation-total", live_total == total, "the live @GameTest( total equals start + 9", (live_total, total))
    ck("V10.log-no-failed", not re.search(r"required tests failed|optional tests failed|\bfailed!|\(optional\) .* failed", text), "the log has no failed-test line or summary")
    for name in RTG_TESTS:
        ck(f"V10.log-{name}", f"[hbm-rtg] {name} passed" in text, f"the log has `[hbm-rtg] {name} passed`")
    ck("V10.log-build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    return dict(all_passed=match and match[0], expected_total=total)


def v11_jar(ck, inp, st, path):
    classes = ["com/hbm/items/machine/RTGPelletItem.class", "com/hbm/items/machine/RTGPelletDepletedItem.class", "com/hbm/util/RTGUtil.class", "com/hbm/hazard/modifier/HazardModifierRTGRadiation.class",
               "com/hbm/util/RTGUtil$HalfLifeType.class", "com/hbm/items/machine/RTGPelletDepletedItem$DepletedRTGMaterial.class", "com/hbm/gametest/RTGPelletGameTests.class"]
    live_en, _ = json_pairs(st.text(EN))
    live_zh, _ = json_pairs(st.text(ZH))
    review = {e["key"]: e for e in jload(st, REV)["new_keys"]}
    keys = sorted(expected_lang(inp, review))
    recipe_ids = IDS + [f"pellet_rtg_depleted_{m.lower()}" for _, m in [(0, x[0]) for x in RECYCLE_NEO]]
    models = [f"{i}.json" for i in NEW_IDS] + ["pellet_rtg_depleted.json"] + [f"pellet_rtg_depleted_{n}.json" for n in range(6)]
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        ck("V11.classes", all(c in names for c in classes), "the JAR has the four new production classes, RTGUtil$HalfLifeType, RTGPelletDepletedItem$DepletedRTGMaterial and the GameTest class", [c for c in classes if c not in names])
        ck("V11.pellet-key-in-class", b"PELLET_DEPLETION" in jar.read(classes[0]) if classes[0] in names else False, "RTGPelletItem.class carries the PELLET_DEPLETION constant (string presence only)")
        bad = [Path(t).name for t in [f"{TEX}{i}.png" for i in NEW_IDS] + [f"{TEX}pellet_rtg_depleted.{m.lower()}.png" for m in MATS]
               if "assets/hbmsntm/textures/item/" + Path(t).name not in names or jar.read("assets/hbmsntm/textures/item/" + Path(t).name) != st.files.get(t)]
        ck("V11.textures", not bad, "the 15 textures in the JAR are byte-equal to the source files", bad)
        ck("V11.models", all("assets/hbmsntm/models/item/pellet_rtg" + (m if m.startswith("pellet") is False else m[len("pellet_rtg"):]) in names or "assets/hbmsntm/models/item/" + m in names for m in models) and
           all(("assets/hbmsntm/models/item/" + m) in names for m in models), "the JAR has the 16 new models", [m for m in models if "assets/hbmsntm/models/item/" + m not in names])
        ck("V11.recipes", all(f"data/hbmsntm/recipe/{r}.json" in names for r in recipe_ids), "the JAR has the 14 recipes", [r for r in recipe_ids if f"data/hbmsntm/recipe/{r}.json" not in names])
        for entry, source in (("assets/hbmsntm/lang/en_us.json", live_en), ("assets/hbmsntm/lang/zh_cn.json", live_zh)):
            if entry not in names:
                ck(f"V11.{Path(entry).name}", False, f"{entry} is in the JAR")
                continue
            data = json.loads(jar.read(entry).decode("utf-8"))
            bad = {k: data.get(k) for k in keys if data.get(k) != source.get(k)}
            ck(f"V11.{Path(entry).name}", not bad, f"{entry} in the JAR carries the 47 keys with the values of the source file", bad)
    return dict(jar=str(path), jar_sha256=sha(Path(path).read_bytes()), jar_bytes=Path(path).stat().st_size, note="the JAR checks establish packaged names, bytes and language values, not runtime behavior")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st, facts_out=None):
    ck = Checks()
    guarded(ck, "V0", v0_inputs, inp, st)
    guarded(ck, "V1", v1_original, inp, st, facts_out)
    guarded(ck, "V2", v2_lifespans, inp, st, facts_out)
    guarded(ck, "V3", v3_registration, inp, st, facts_out)
    guarded(ck, "V4", v4_recipes, inp, st, facts_out)
    guarded(ck, "V5", v5_hazards, inp, st, facts_out)
    guarded(ck, "V6", v6_models_lang, inp, st, facts_out)
    guarded(ck, "V7", v7_textures, inp, st, facts_out)
    guarded(ck, "V8", v8_scope, inp, st, facts_out)
    guarded(ck, "V9", v9_gametests, inp, st, facts_out)
    return ck


def T(path, fn):
    return lambda st: st.set_text(path, fn(st.text(path)))


def Bx(path, fn):
    return lambda st: st.set_bytes(path, fn(st.files[path]))


def D(path):
    return lambda st: st.delete(path)


def flip_byte(data):
    out = bytearray(data)
    out[len(out) // 2] ^= 0x01
    return bytes(out)


def mutations():
    """(label, expected failing-section prefixes, applicator(State), required path or None)."""
    return [
        ("pellet_heat_changed", "V3.|V6.", T(NI, lambda t: rep1(t, '"pellet_rtg_radium", () -> new RTGPelletItem(new Item.Properties(), 3)', '"pellet_rtg_radium", () -> new RTGPelletItem(new Item.Properties(), 4)')), None),
        ("pellet_half_life_changed", "V3.|V2.", T(NI, lambda t: rep1(t, "getLifespan(5.3F", "getLifespan(5.4F")), None),
        ("half_life_type_changed", "V3.|V2.", T(NI, lambda t: rep1(t, "getLifespan(29.0F, HalfLifeType.MEDIUM", "getLifespan(29.0F, HalfLifeType.LONG")), None),
        ("depleted_material_changed", "V3.", T(NI, lambda t: rep1(t, "DepletedRTGMaterial.NEPTUNIUM, (long) (RTGUtil.getLifespan(4.7F", "DepletedRTGMaterial.LEAD, (long) (RTGUtil.getLifespan(4.7F")), None),
        ("gold_heat_supplier_swapped", "V3.", T(NI, lambda t: rep1(t, "RTGUtil.rtgDecay() ? 200 : 100", "RTGUtil.rtgDecay() ? 100 : 200")), None),
        ("pellet_order_swapped", "V3.|V6.", T(NI, lambda t: swap_lines(t, '"pellet_rtg_strontium"', '"pellet_rtg_cobalt"')), None),
        ("pellet_registered_as_plain_item", "V3.", T(NI, lambda t: rep1(t, '"pellet_rtg_weak", () -> new RTGPelletItem(new Item.Properties(), 5).setDecays(DepletedRTGMaterial.LEAD, (long) (RTGUtil.getLifespan(1.0F, HalfLifeType.LONG, false) * 1.5)))',
                                                                       '"pellet_rtg_weak", () -> new Item(new Item.Properties()))')), None),
        ("stray_line_in_ntmitems", "V3.", T(NI, lambda t: t.replace("    // Cells", "    // stray\r\n    // Cells", 1)), None),
        ("depleted_enum_order_swapped", "V3.", T(RPD, lambda t: swap_lines(t, "        MERCURY,", "        NEPTUNIUM,")), None),
        ("stacksto_removed", "V3.", T(RPI, lambda t: rep1(t, "super(properties.stacksTo(1));", "super(properties);")), None),
        ("craft_remainder_removed", "V3.", T(NI, lambda t: rep1(t, ".craftRemainder(PLATE_IRON.get())", "")), None),
        ("get_lifespan_writes_back", "V3.", T(RPI, lambda t: rep1(t, "tag.contains(KEY_DEPLETION, Tag.TAG_ANY_NUMERIC) ? tag.getLong(KEY_DEPLETION) : getMaxLifespan();", "tag.contains(KEY_DEPLETION, Tag.TAG_ANY_NUMERIC) ? tag.getLong(KEY_DEPLETION) : setAndGet(stack);")), None),
        ("decay_writes_life_plus_one", "V3.", T(RPI, lambda t: rep1(t, "getLifespan(stack) - 1", "getLifespan(stack) + 1")), None),
        ("handle_decay_threshold", "V3.", T(RPI, lambda t: rep1(t, "instance.getLifespan(stack) <= 0", "instance.getLifespan(stack) < 0")), None),
        ("scaled_power_floor", "V3.", T(RPI, lambda t: rep1(t, "Math.ceil(fuel.getHeat()", "Math.floor(fuel.getHeat()")), None),
        ("depletion_formula", "V3.", T(RPI, lambda t: rep1(t, "return 1D - (double) getLifespan(stack)", "return 0D - (double) getLifespan(stack)")), None),
        ("use_not_server_only", "V3.", T(RPI, lambda t: rep1(t, "if(!level.isClientSide) {", "if(level.isClientSide) {")), None),
        ("rtg_decay_and_instead_of_or", "V3.", T(RTGU, lambda t: rep1(t, "NtmConfig.enable528() || NtmConfig.COMMON.DO_RTGS_DECAY.get()", "NtmConfig.enable528() && NtmConfig.COMMON.DO_RTGS_DECAY.get()")), None),
        ("scale_power_reads_wrong_key", "V3.", T(RTGU, lambda t: rep1(t, "NtmConfig.COMMON.SCALE_RTG_POWER.get()", "NtmConfig.COMMON.DO_RTGS_DECAY.get()")), None),
        ("update_decays_before_power", "V3.", T(RTGU, lambda t: swap_lines(t, "newHeat += getPower(pellet, stack, scale);", "inventory.set(slot, RTGPelletItem.handleDecay(stack, pellet, decay));")), None),
        ("lifespan_double_arithmetic", "V3.", T(RTGU, lambda t: rep1(t, "life = 48000 * halfLife;", "life = (float) (48000 * (double) halfLife);")), None),
        ("config_default_changed", "V3.", T(CC, lambda t: rep1(t, '.define("doRTGsDecay", true)', '.define("doRTGsDecay", false)')), None),
        ("config_comment_changed", "V3.", T(CC, lambda t: rep1(t, "Should RTG/Betavoltaic fuel decay at all?", "Should RTG fuel decay at all?")), None),
        ("config_key_renamed", "V3.", T(CC, lambda t: rep1(t, '.define("scaleRTGPower", false)', '.define("scaleRtgPower", false)')), None),
        ("config_language_entry_added", "V3.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("hbmsntm.configuration.doRTGsDecay", "RTG衰变"))), None),
        ("pellet_recipe_deleted", "V4.|V8.", D(RECIPES + "pellet_rtg_gold.json"), RECIPES + "pellet_rtg_gold.json"),
        ("pellet_recipe_plate_removed", "V4.", T(RECIPES + "pellet_rtg_weak.json", lambda t: json_edit(t, lambda d: d["ingredients"].pop())), RECIPES + "pellet_rtg_weak.json"),
        ("pellet_recipe_billet_changed", "V4.", T(RECIPES + "pellet_rtg_radium.json", lambda t: rep1(t.replace("billet_ra226", "billet_ra226X", 1), "billet_ra226X", "billet_pu238")), RECIPES + "pellet_rtg_radium.json"),
        ("recycling_meta_changed", "V4.", T(RECIPES + "pellet_rtg_depleted_neptunium.json", lambda t: rep1(t, '"hbmsntm:meta": 2', '"hbmsntm:meta": 3')), RECIPES + "pellet_rtg_depleted_neptunium.json"),
        ("recycling_strict_true", "V4.", T(RECIPES + "pellet_rtg_depleted_lead.json", lambda t: json_edit(t, lambda d: d["ingredients"][0].__setitem__("strict", True))), RECIPES + "pellet_rtg_depleted_lead.json"),
        ("recycling_count_changed", "V4.", T(RECIPES + "pellet_rtg_depleted_bismuth.json", lambda t: rep1(t, '"count": 3', '"count": 2')), RECIPES + "pellet_rtg_depleted_bismuth.json"),
        ("mercury_recipe_added", "V4.", lambda st: st.set_text(RECIPES + "pellet_rtg_depleted_mercury.json", "{}"), None),
        ("provider_recycling_row_changed", "V4.", T(RP, lambda t: rep1(t, "DepletedRTGMaterial.LEAD, NtmItems.INGOT_LEAD.get(), 2)", "DepletedRTGMaterial.LEAD, NtmItems.INGOT_LEAD.get(), 3)")), None),
        ("provider_skipped_comment_removed", "V4.", T(RP, lambda t: drop_line(t, "// :219, mercury")), None),
        ("hazard_row_deleted", "V5.", T(HR, lambda t: drop_line(t, "registerRTGPellet(PELLET_RTG_COBALT, co60 * rtg, 0); // :341")), None),
        ("hazard_constant_changed", "V5.", T(HR, lambda t: rep1(t, "public static final float co60 = 30.0F;", "public static final float co60 = 31.0F;")), None),
        ("hazard_hot_argument_changed", "V5.", T(HR, lambda t: rep1(t, "po210 * rtg, 0, 3F); // :343", "po210 * rtg, 0, 4F); // :343")), None),
        ("hazard_blinding_removed", "V5.", T(HR, lambda t: rep1(t, "pb209 * rtg, 0, 7F, 50F);", "pb209 * rtg, 0, 7F);")), None),
        ("hazard_expression_changed", "V5.", T(HR, lambda t: rep1(t, "(pu238 + (u238 * 2)) * billet, 0); // :339", "(pu238 + u238) * billet, 0); // :339")), None),
        ("hazard_np_row_removed", "V5.", T(HR, lambda t: drop_line(t, "MetaHelper.newStack(PELLET_RTG_DEPLETED, 1, DepletedRTGMaterial.NEPTUNIUM.ordinal())")), None),
        ("hazard_call_removed", "V5.", T(HR, lambda t: rep1(t, "        registerMaterialAddendum();\r\n        registerRTGPellets();", "        registerMaterialAddendum();")), None),
        ("hazard_helper_hot_condition", "V5.", T(HR, lambda t: rep1(t, "if(hot > 0) data.addEntry(new HazardEntry(HOT, hot));", "if(hot >= 0) data.addEntry(new HazardEntry(HOT, hot));")), None),
        ("hazard_deferral_comment_restored", "V5.", T(HR, lambda t: rep1(t, "are registered in registerRTGPellets (Goal23B).", "are deferred with the RTG modifier: NEO has no HazardModifierRTGRadiation.")), None),
        ("modifier_formula_changed", "V5.", T(MOD, lambda t: rep1(t, "(this.target - level) * depletion", "(level - this.target) * depletion")), None),
        ("modifier_guard_removed", "V5.", T(MOD, lambda t: rep1(t, "if(!(stack.getItem() instanceof RTGPelletItem fuel)) return level;", "RTGPelletItem fuel = (RTGPelletItem) stack.getItem();")), None),
        ("zh_key_dropped", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("item.hbmsntm.pellet_rtg_gold"))), None),
        ("zh_fact_dropped", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.pop("desc.item.pellet_rtg.fact.7"))), None),
        ("upstream_chinese_changed", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("item.hbmsntm.pellet_rtg_radium", "镭226放射性同位素燃料靶丸"))), None),
        ("lead_pellet_space_removed", "V6.", lambda st: st.set_text(ZH, json_edit(st.text(ZH), lambda d: d.__setitem__("item.hbmsntm.pellet_rtg_lead", "铅-209放射性同位素燃料靶丸"))), None),
        ("en_key_dropped", "V6.", T(EN, lambda t: drop_line(t, '"desc.item.rtgHeat"')), None),
        ("fact_percent_unescaped", "V6.", T(EN, lambda t: rep1(t, "Roughly 20%% of", "Roughly 20% of")), None),
        ("mapping_upstream_kind_flipped", "V6.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda e: e["item.hbmsntm.pellet_rtg_weak"].__setitem__("kind", "local"), True)), None),
        ("mapping_source_zh_changed", "V6.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda e: e["item.hbmsntm.pellet_rtg_cobalt"].__setitem__("source_zh", "钴60放射性同位素燃料靶丸"), True)), None),
        ("mapping_entry_dropped", "V6.", lambda st: st.set_text(MAP, json_edit(st.text(MAP), lambda e: e.pop("desc.item.rtgTicks"), True)), None),
        ("provider_string_changed", "V6.", T(LP, lambda t: rep1(t, '"Gold-198 RTG Pellet"', '"Gold-198 RTG Pellets"')), None),
        ("model_texture_changed", "V6.", T(MODELS + "pellet_rtg_gold.json", lambda t: rep1(t, "hbmsntm:item/pellet_rtg_gold", "hbmsntm:item/pellet_rtg_lead")), MODELS + "pellet_rtg_gold.json"),
        ("depleted_override_changed", "V6.", T(MODELS + "pellet_rtg_depleted.json", lambda t: rep1(t, '"hbmsntm:item_meta": 2.0', '"hbmsntm:item_meta": 3.0')), MODELS + "pellet_rtg_depleted.json"),
        ("model_provider_line_dropped", "V6.", T(MP, lambda t: drop_line(t, "this.basicItem(NtmItems.PELLET_RTG_POLONIUM.get());")), None),
        ("creative_tab_line_dropped", "V6.", T(CT, lambda t: drop_line(t, "output.accept(NtmItems.PELLET_RTG_COBALT);")), None),
        ("creative_tab_depleted_dropped", "V6.", T(CT, lambda t: drop_line(t, "addMetaItems(output, NtmItems.PELLET_RTG_DEPLETED.get());")), None),
        ("creative_tab_icon_changed", "V6.", T(CT, lambda t: rep1(t, ".icon(() -> new ItemStack(NtmItems.PELLET_RTG.get()))", ".icon(() -> new ItemStack(NtmItems.PELLET_RTG_LEAD.get()))")), None),
        ("texture_byte_flipped", "V7.", Bx(TEX + "pellet_rtg_polonium.png", flip_byte), TEX + "pellet_rtg_polonium.png"),
        ("depleted_texture_byte_flipped", "V7.", Bx(TEX + "pellet_rtg_depleted.nickel.png", flip_byte), TEX + "pellet_rtg_depleted.nickel.png"),
        ("existing_texture_changed", "V7.", Bx(TEX + "pellet_rtg.png", flip_byte), TEX + "pellet_rtg.png"),
        ("ownership_sha_changed", "V7.", lambda st: st.set_text(OWN, rep1(st.text(OWN), '"sha256": "30c808d4', '"sha256": "40c808d4')), None),
        ("stray_src_file_added", "V8.", lambda st: st.set_bytes("src/main/java/com/hbm/Stray.java", b"class Stray {}"), None),
        ("unrelated_src_file_touched", "V8.", T("src/main/java/com/hbm/hazard/HazardSystem.java", lambda t: t + "\n// mutation\n"), "src/main/java/com/hbm/hazard/HazardSystem.java"),
        ("gametest_annotation_removed", "V9.", T(RGT, lambda t: rep1(t, "public static void rtg_pellet_decay(GameTestHelper helper)", "static void rtg_pellet_decay(GameTestHelper helper)") if re.search(r"@GameTest\([^)]*\)\s*public static void rtg_pellet_decay", t) else t),
         RGT),
        ("gametest_method_renamed", "V9.", T(RGT, lambda t: rep1(t, "rtg_pellet_hazards(GameTestHelper helper)", "rtg_pellet_hazards_x(GameTestHelper helper)")), RGT),
        ("hazard_other_test_body_changed", "V9.", T(HGT, lambda t: rep1(t, 'done(helper, "hazard_living_addendum_fire_and_asbestos");', 'done(helper, "hazard_living_addendum_fire_and_asbestos_x");')), None),
        ("hazard_guard_deferral_restored", "V9.", T(HGT, lambda t: rep1(t, '"tile_lab_broken")) {', '"tile_lab_broken", "pellet_rtg")) {') if '"tile_lab_broken")) {' in t else t + "\n// mutation\n"), None),
    ]


def mutate_all(inp, st, base_failed):
    results = {}
    for label, prefixes, apply, required in mutations():
        if required is not None and not st.has(required) and required in (RGT,):
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=None, skipped=f"{required} is absent")
            continue
        mutated = st.copy()
        try:
            apply(mutated)
        except AssertionError as error:
            results[label] = dict(expected_section=prefixes, failed=[], crashes=[], detected=False, error=f"mutation did not apply: {error}")
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
    for sec in ("V10", "V11"):
        out.setdefault(sec, [])
    result = {}
    for sec in sorted(out, key=lambda s: int(s[1:])):
        items = out[sec]
        if sec in ("V10", "V11") and not items:
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
    try:
        inp.parsed = parse_original(inp)
    except Exception as error:  # noqa: BLE001
        print(f"FATAL: the original could not be parsed: {error!r}")
        sys.exit(2)
    facts = {}
    ck = static_suite(inp, st, facts)
    base_failed = set(ck.failed())
    extra = {}
    if args.gametest_log:
        extra["gametest_log"] = guarded(ck, "V10", v10_log, inp, st, args.gametest_log)
    if args.jar:
        extra["jar"] = guarded(ck, "V11", v11_jar, inp, st, args.jar)
    muts = mutate_all(inp, st, base_failed)
    applied = {k: v for k, v in muts.items() if v.get("detected") is not None}
    undetected = [k for k, v in applied.items() if not v["detected"]]
    skipped = [k for k, v in muts.items() if v.get("detected") is None]

    production = JAVA_MODIFIED + JAVA_NEW + [ZH, EN, STAMP, MAP, OWN, REV]
    secs = sections(ck)
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        pass_=not ck.failed() and not undetected,
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(applied) - len(undetected), mutations_applied=len(applied), mutations_skipped=skipped),
        sections=secs, failed=ck.failed(), undetected_mutations=undetected,
        checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256={p: st.tree.get(p) for p in production},
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
