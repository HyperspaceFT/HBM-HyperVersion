"""Verify Goal21D (material radiation hazards: OreDictManager DictFrame rows and the fuel/yellowcake item rows registered in NEO
HazardRegistry), statically.

Read-only for both worktrees. Writes build/migration/goal21d/verify/hazard-report.json and, only with --write-record,
migration/goal21d-hazard-review.json. No game, Gradle or network.

- A1  Original anchors, parsed from the read-only original working tree (HEAD 6a11998d): OreDictManager target rows (:347-374, :454-455,
      :490-495), DictFrame (:737-962: hazard methods, shape multipliers, registerHazards, hazNugget/hazIngot), frame declarations, Mats
      autogen lines, HazardRegistry constants, blacklist :517-518 and the item-level rows :289-329, :473-474.
- A2  The expected table, generated from A1 alone: NEO id -> ordered (type, float32) entries, mutex and original line. Every row/shape ends
      in exactly one state: registered / "NEO 缺物品，跳过" / "决定 13：矿石不登记". Identity = same name, checked against NtmItems and NtmBlocks.
- A3  The NEO HazardRegistry parsed statically (comments stripped for semantics): frame chains and item-level rows resolved with NEO's own
      constants in float32 and required to equal A2 exactly (entry order, mutex, line comments); no duplicate registration; no ore block;
      nothing out of scope.
- A4  The start diff: HazardRegistry equals the frozen start copy plus insertions only; line endings; hazard system files, CommonEvents,
      language files and the zh map hash-equal to baseline.json; no other src/ path changed.
- A5  The arithmetic samples of the task book.
- A6  In-memory mutations of the NEO text; each must make at least one check fail.
- A7  Optional --gametest-log PATH and --jar PATH.

python -B -X utf8 tools/migration/verify_goal21d_hazards.py [--write-record] [--gametest-log PATH] [--jar PATH]
"""
import argparse
import difflib
import functools
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal21d"
START = BATCH / "baseline-files"
REPORT = BATCH / "verify/hazard-report.json"
RECORD = ROOT / "migration/goal21d-hazard-review.json"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
HAZ = J + "hazard/HazardRegistry.java"
NTM_ITEMS = J + "items/NtmItems.java"
NTM_BLOCKS = J + "blocks/NtmBlocks.java"
RAW_INGOT = J + "items/RawIngotItem.java"
GAMETEST = J + "gametest/HazardGameTests.java"
GAMETEST_DIR = J + "gametest/"
STAMP = "src/generated/resources/.migration-stamp.json"
COMMON_EVENTS = J + "main/CommonEvents.java"
UNCHANGED_HAZARD_FILES = [J + "hazard/HazardSystem.java", J + "hazard/HazardData.java", J + "hazard/HazardEntry.java"]
UNCHANGED_HAZARD_DIRS = [J + "hazard/type/", J + "hazard/modifier/", J + "hazard/transformer/"]
LANGUAGE_FILES = ["src/main/resources/assets/hbmsntm/lang/zh_cn.json", "migration/localization/zh_cn-map.json",
                  "src/generated/resources/assets/hbmsntm/lang/en_us.json", J + "datagen/NtmLanguageProvider.java"]

O = "src/main/java/com/hbm/"
O_ODM = O + "inventory/OreDictManager.java"
O_HAZ = O + "hazard/HazardRegistry.java"
O_MATS = O + "inventory/material/Mats.java"

OLD_TEST_COUNT = 51
GAMETEST_BATCH = "hazard_materials"

ST_REG = "已登记"
ST_SKIP = "NEO 缺物品，跳过"
ST_ORE = "决定 13：矿石不登记"
STATES = (ST_REG, ST_SKIP, ST_ORE)

TYPES = ("RADIATION", "HOT", "BLINDING", "HYDROACTIVE")

# (original OreDictManager line, frame constant)
FRAME_ROWS = [(347, "U"), (348, "U233"), (349, "U235"), (350, "U238"), (351, "TH232"), (352, "PU"), (353, "PURG"), (354, "PU238"),
              (355, "PU239"), (356, "PU240"), (357, "PU241"), (358, "AM241"), (359, "AM242"), (360, "AMRG"), (361, "NP237"),
              (362, "PO210"), (363, "TC99"), (364, "RA226"), (365, "AC227"), (366, "CO60"), (367, "AU198"), (368, "PB209"),
              (369, "SA326"), (370, "SA327"), (371, "SBD"), (372, "SRN"), (373, "GH336"), (374, "MUD"), (454, "LI"), (455, "NA"),
              (490, "SR"), (491, "SR90"), (492, "I131"), (493, "XE135"), (494, "CS137"), (495, "AT209")]
FRAME_DECL = {"U": 128, "U233": 129, "U235": 130, "U238": 131, "TH232": 132, "PU": 133, "PURG": 134, "PU238": 135, "PU239": 136,
              "PU240": 137, "PU241": 138, "AM241": 139, "AM242": 140, "AMRG": 141, "NP237": 142, "PO210": 143, "TC99": 144, "RA226": 145,
              "AC227": 146, "CO60": 147, "AU198": 148, "PB209": 149, "SA326": 150, "SA327": 151, "SBD": 152, "SRN": 153, "GH336": 154,
              "MUD": 155, "LI": 252, "NA": 254, "SR": 294, "SR90": 295, "I131": 296, "XE135": 297, "CS137": 298, "AT209": 299}
HAZ_CALLS = {"rad": "RADIATION", "hot": "HOT", "blinding": "BLINDING", "hydro": "HYDROACTIVE"}
SHAPE_CONST = {"nugget": "nugget", "billet": "billet", "ingot": "ingot", "dustSmall": "powder_tiny", "dust": "powder", "plate": "plate",
               "plateCast": "plateCast", "block": "block", "ore": "ore", "oreNether": "ore"}
ORE_SHAPES = ("ore", "oreNether")
AUTO_CALLS = {"hazNugget": ("nugget", "NUGGET", "nugget_"), "hazIngot": ("ingot", "INGOT", "ingot_")}
# frame constant -> Mats material constant (original Mats.java:135,137,139)
AUTOGEN_MAT = {"LI": "MAT_LITHIUM", "NA": "MAT_SODIUM", "SR": "MAT_STRONTIUM"}
MAT_NAME = {"MAT_LITHIUM": "lithium", "MAT_SODIUM": "sodium", "MAT_STRONTIUM": "strontium"}

ITEM_ROW_LINES = list(range(289, 294)) + list(range(295, 299)) + list(range(300, 304)) + list(range(305, 308)) + \
    list(range(309, 313)) + list(range(314, 317)) + list(range(318, 322)) + list(range(323, 326)) + list(range(327, 330)) + [473, 474]

# NEO-only or out-of-scope ids that Goal21D must leave unregistered (task book, handoff)
NEO_ONLY_UNREGISTERED = ["powder_co60_tiny", "ingot_i131"]
OUT_OF_SCOPE_ID = re.compile(r"^(crystal_|pellet_rtg|plate_fuel|pile_|rbmk|pwr|watz|ore_)|^(powder_caesium|billet_balefire_gold|billet_flashlead|"
                             r"billet_po210be|billet_ra226be|billet_pu238be|ingot_phosphorus|block_white_phosphorus|ingot_asbestos|powder_asbestos|"
                             r"block_asbestos|powder_co60_tiny|ingot_i131)$")

SAMPLES = [("ingot_uranium", "RADIATION", "0.35"), ("nugget_uranium", "RADIATION", "0.035"), ("billet_uranium", "RADIATION", "0.175"),
           ("powder_uranium", "RADIATION", "1.05"), ("block_uranium", "RADIATION", "3.5"), ("ingot_pu239", "RADIATION", "5"),
           ("block_pu239", "RADIATION", "50"), ("ingot_plutonium", "RADIATION", "7.5"), ("powder_yellowcake", "RADIATION", "1.05"),
           ("block_yellowcake", "RADIATION", "10.5")]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def lf(data):
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def eol_kind(data):
    crlf = data.count(b"\r\n")
    lone = data.count(b"\n") - crlf
    return "CRLF" if crlf and not lone else "LF" if lone and not crlf else "MIXED" if crlf else "NONE"


def flat(text):
    return " ".join(text.split())


def git(root, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + root.as_posix(), *args], cwd=root).decode("utf-8")


class Reader:
    """Every file read is hashed (raw bytes) into the report."""

    def __init__(self):
        self.hashes = {}

    def bytes(self, base, rel, label):
        data = (base / rel).read_bytes()
        self.hashes[f"{label}:{rel}"] = sha(data)
        return data

    def text(self, base, rel, label):
        return lf(self.bytes(base, rel, label))


# ---------------------------------------------------------------- float32 and Java expressions

def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def f32_bits(x):
    return struct.pack(">f", x).hex()


def f32_repr(x):
    for p in range(1, 10):
        s = f"{x:.{p}g}"
        if f32(float(s)) == x:
            return repr(float(s))
    return repr(x)


_TOKEN = re.compile(r"\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?[fFdDlL]?|\.\d+[fF]?|[A-Za-z_][\w.]*|[-+*/()]|\S")


def eval_float(expr, consts):
    """Evaluates a Java float expression (literals, constants, + - * / and parentheses), rounding to float32 after every operation."""
    tokens = _TOKEN.findall(expr)
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take():
        pos[0] += 1
        return tokens[pos[0] - 1]

    def factor():
        t = take()
        if t == "(":
            v = add()
            assert take() == ")", "unbalanced parentheses in " + expr
            return v
        if t == "-":
            return -factor()
        if re.fullmatch(r"\d[\d_]*\.?\d*(?:[eE][+-]?\d+)?[fF]", t) or re.fullmatch(r"\.\d+[fF]", t):
            return f32(float(t[:-1].replace("_", "")))
        if re.fullmatch(r"\d[\d_]*", t):
            return f32(float(t.replace("_", "")))
        if re.fullmatch(r"[A-Za-z_][\w.]*", t):
            name = t[len("HazardRegistry."):] if t.startswith("HazardRegistry.") else t
            assert name in consts, f"unknown constant {name!r} in {expr!r}"
            return consts[name]
        raise AssertionError(f"unsupported token {t!r} in {expr!r}")

    def mul():
        v = factor()
        while peek() in ("*", "/"):
            op = take()
            r = factor()
            v = f32(v * r) if op == "*" else f32(v / r)
        return v

    def add():
        v = mul()
        while peek() in ("+", "-"):
            op = take()
            r = mul()
            v = f32(v + r) if op == "+" else f32(v - r)
        return v

    value = add()
    assert pos[0] == len(tokens), f"trailing tokens in {expr!r}"
    return value


@functools.lru_cache(maxsize=None)
def strip_keep(src):
    """Comments blanked, string literals kept, every newline kept (line numbers survive)."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in src[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def float_consts(text):
    """All `public static final float NAME = EXPR;` of a Java file, evaluated in float32 (constants may reference earlier constants)."""
    raw = dict(re.findall(r"public static final float (\w+)\s*=\s*([^;]+);", strip_keep(text)))
    values = {}
    busy = set()

    def value(name):
        if name not in values:
            assert name not in busy, "constant cycle " + name
            busy.add(name)
            values[name] = eval_float(raw[name], LazyConsts())
            busy.discard(name)
        return values[name]

    class LazyConsts(dict):
        def __contains__(self, key):
            return key in raw

        def __getitem__(self, key):
            return value(key)

    return {name: value(name) for name in raw}


def split_args(text):
    args, depth, cur = [], 0, []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    last = "".join(cur).strip()
    if last or args:
        args.append(last)
    return args


def matching_paren(text, open_index):
    depth = 0
    for j in range(open_index, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    raise AssertionError("unbalanced parentheses: " + text[open_index:open_index + 80])


def parse_chain(chain):
    """`.rad(u) .nugget(A, B)` -> [("rad", ["u"]), ("nugget", ["A", "B"])]."""
    calls, i = [], 0
    head = re.compile(r"\s*\.(\w+)\(")
    while i < len(chain):
        if not chain[i:].strip():
            break
        m = head.match(chain, i)
        assert m, "cannot parse call chain at: " + chain[i:i + 60]
        end = matching_paren(chain, m.end() - 1)
        calls.append((m.group(1), split_args(chain[m.end():end])))
        i = end + 1
    return calls


def parse_makedata(text):
    """`makeData(RADIATION, e)` / `makeData().addEntry(T, e)...` -> [(type, expr)]."""
    text = text.strip()
    m = re.match(r"makeData\(", text)
    assert m, "not a makeData expression: " + text[:60]
    end = matching_paren(text, m.end() - 1)
    args = split_args(text[m.end():end])
    rest = text[end + 1:]
    if not args:
        entries = []
        for name, a in parse_chain(rest):
            assert name == "addEntry" and len(a) == 2, f"unsupported makeData chain call {name}{a}"
            entries.append((a[0], a[1]))
        return entries
    assert len(args) == 2 and not rest.strip(), "unsupported makeData form: " + text[:80]
    return [(args[0], args[1])]


def block_span(code, signature):
    """(start index, end index of the closing brace) of the one block whose header contains signature."""
    start = code.find(signature)
    assert start >= 0, "block not found: " + signature
    assert code.find(signature, start + 1) < 0, "ambiguous block: " + signature
    i = code.index("{", start)
    depth = 0
    for j in range(i, len(code)):
        if code[j] == "{":
            depth += 1
        elif code[j] == "}":
            depth -= 1
            if depth == 0:
                return start, j
    raise AssertionError("unbalanced block: " + signature)


def line_of(code, index):
    return code.count("\n", 0, index) + 1


def need(lines, number, *parts):
    line = lines[number - 1]
    for part in parts:
        assert part in line, f"original line {number} no longer contains {part!r}: {line.strip()[:120]!r}"


def fmt(value):
    return float(f32_repr(value))


# ---------------------------------------------------------------- A1: original anchors

def parse_original(ctx):
    """Everything derived from the original; independent of the NEO tree."""
    odm_text = ctx["original"][O_ODM]
    odm = odm_text.split("\n")
    haz_text = ctx["original"][O_HAZ]
    haz = haz_text.split("\n")
    consts = float_consts(haz_text)
    model = dict(consts=consts, rows=[], notes=[])

    # frame declarations
    decl = {}
    for number, line in enumerate(odm, 1):
        m = re.match(r"\s*public static final DictFrame (\w+) = new DictFrame\((.*)\);", line)
        if m:
            decl[m.group(1)] = (number, re.findall(r'"([^"]*)"', m.group(2)))
    model["frame_decl"] = {name: decl[name][0] for _, name in FRAME_ROWS}
    model["frame_mats"] = {name: decl[name][1] for _, name in FRAME_ROWS}
    model["all_frames"] = decl

    # DictFrame shape methods :838-886, hazard methods :791-795
    frame_text = "\n".join(odm[735:962])
    shapes = {}
    for m in re.finditer(r"public DictFrame (\w+)\(Object\.\.\. \w+\) \{\s*hazMult = HazardRegistry\.(\w+);\s*return makeObject\((\w+)", frame_text):
        shapes[m.group(1)] = (m.group(2), m.group(3))
    model["shape_const"] = {name: const for name, (const, _) in shapes.items()}
    model["haz_methods"] = dict(re.findall(r"public DictFrame (\w+)\(float \w+\) \{\s*return this\.haz\(new HazardEntry\(HazardRegistry\.(\w+), \w+\)\);", frame_text))
    model["auto"] = dict((m.group(1), (m.group(2), m.group(3))) for m in re.finditer(
        r"public DictFrame (haz\w+)\(\) \{\s*hazMult = HazardRegistry\.(\w+);\s*return autoRegHazard\((\w+)\);", frame_text))

    # the target rows
    for number, frame in FRAME_ROWS:
        line = odm[number - 1]
        m = re.match(r"\s*(\w+)\s+(\..*?);", line)
        assert m and m.group(1) == frame, f"OreDictManager line {number} is not the {frame} row: {line.strip()[:100]!r}"
        model["rows"].append(dict(line=number, frame=frame, calls=parse_chain(m.group(2)), text=line.strip()))

    # item-level rows
    items = []
    for number in ITEM_ROW_LINES:
        m = re.match(r"\s*HazardSystem\.register\((\w+), (makeData.*)\);\s*$", haz[number - 1])
        assert m, f"HazardRegistry line {number} is not an item-level row: {haz[number - 1].strip()[:100]!r}"
        items.append(dict(line=number, name=m.group(1), entries=[(t, e) for t, e in parse_makedata(m.group(2))]))
    model["item_rows"] = items
    for number in range(289, 330):
        if number not in ITEM_ROW_LINES:
            assert not haz[number - 1].strip(), f"HazardRegistry line {number} is neither a row nor blank"

    # Mats autogen
    autogen = {}
    for number in (135, 137, 139):
        m = re.match(r"\s*public static final NTMMaterial (MAT_\w+)\s*=\s*make\w+\((\d+),\s*(\w+),.*\.setAutogen\(([^)]*)\)", ctx["original"][O_MATS].split("\n")[number - 1])
        assert m, f"Mats.java line {number} is not a setAutogen line"
        autogen[m.group(3)] = (m.group(1), [s.strip() for s in m.group(4).split(",")], number, int(m.group(2)))
    model["autogen"] = autogen
    ingot_nugget_frames = set()
    for line in ctx["original"][O_MATS].split("\n"):
        m = re.match(r"\s*public static final NTMMaterial (MAT_\w+)\s*=\s*make\w+\(\d+,\s*(\w+),.*\.setAutogen\(([^)]*)\)", line)
        if m and {"INGOT", "NUGGET"} & {x.strip() for x in m.group(3).split(",")}:
            ingot_nugget_frames.add(m.group(2))
    model["ingot_nugget_frames"] = ingot_nugget_frames
    return model


def c_a_rows(ctx):
    model = ctx["model"]
    assert len(model["rows"]) == 36, "target rows"
    assert model["frame_decl"] == FRAME_DECL, "frame declaration lines moved: " + str({k: v for k, v in model["frame_decl"].items() if FRAME_DECL[k] != v})
    odm = ctx["original"][O_ODM].split("\n")
    for number, text in ((357, "//.block(block_pu241);"), (369, ".plateCast(Mats.MAT_SCHRABIDIUM.make(plate_cast))"), (354, ".hot(3F)"), (362, ".hot(3)"),
                         (368, ".blinding(50F)"), (368, ".hot(7)"), (454, ".hazNugget()"), (455, ".hazIngot()"), (490, ".hazIngot()"), (490, ".hazNugget()")):
        need(odm, number, text)
    assert flat(" ".join(odm[343:346])).startswith("/* * RADIOACTIVE */"), "RADIOACTIVE banner moved"
    return "36 target rows at the exact lines (:347-374, :454-455, :490-495), frame constants at :128-155, :252, :254, :294-299"


def c_a_dictframe(ctx):
    model = ctx["model"]
    expected = {"nugget": "nugget", "billet": "billet", "ingot": "ingot", "dustSmall": "powder_tiny", "dust": "powder", "plate": "plate",
                "plateCast": "plateCast", "block": "block", "ore": "ore", "oreNether": "ore", "gem": "gem", "crystal": "gem"}
    assert model["shape_const"] == expected, f"DictFrame shape multipliers {model['shape_const']}"
    assert model["haz_methods"] == {"rad": "RADIATION", "hot": "HOT", "blinding": "BLINDING", "asbestos": "ASBESTOS", "hydro": "HYDROACTIVE"}, "DictFrame hazard methods"
    assert model["auto"] == {"hazNugget": ("nugget", "NUGGET"), "hazIngot": ("ingot", "INGOT")}, f"hazNugget/hazIngot {model['auto']}"
    odm = ctx["original"][O_ODM].split("\n")
    text = flat("\n".join(odm[837:962]))
    assert "makeObject(NUGGET, nugget).makeObject(TINY, nugget)" in text, "nugget registers NUGGET and TINY keys (:840)"
    assert 'if("ingot".equals(tag)) { registerStack("", stack); }' in text, "ingot also registers the bare key (:958-960)"
    assert "if(!hazards.isEmpty() && hazMult > 0F) { HazardData data = new HazardData().setMutex(0b1); for(HazardEntry hazard : hazards) { data.addEntry(hazard.clone(hazMult)); } HazardSystem.register(dictKey, data); }" in text, \
        "registerHazards (:933-944): setMutex(0b1) and clone(hazMult) on every entry"
    assert "registerHazards(hazards, hazMult, tag + mat)" in text, "registerHazards is called per ore key"
    assert "float hazMult = 1.0F;" in flat(odm[739 - 1]) or "float hazMult = 1.0F;" in odm[738], "initial hazMult"
    clone = ctx["original"][O + "hazard/HazardEntry.java"]
    assert "new HazardEntry(type, baseLevel * mult)" in clone and "clone.mods = this.mods" in clone, "HazardEntry.clone multiplies the base level"
    return "hazard methods :791-795; shapes :838-886 -> nugget .1 (and TINY), billet .5, ingot 1, dustSmall 3*.1, dust 3, plate 1, plateCast 3, block 10, ore 1; " \
           "registerHazards :933-944 setMutex(0b1) + clone(hazMult) per entry; hazNugget/hazIngot :913-921"


def c_a_constants(ctx):
    c = ctx["model"]["consts"]
    given = dict(nugget=0.1, ingot=1.0, gem=1.0, plate=1.0, powder_mult=3.0, block=10.0, billet=0.5, u=0.35, uzh=0.125, uf=0.5, puf=4.25,
                 thf=1.75, npf=1.5, mox=2.5, amf=4.75, saf=5.85, yc=0.35, pu=7.5, pu238=10.0, pu239=5.0, sa326=15.0, sr=1.5, sb=1.5)
    for name, value in given.items():
        assert c[name] == f32(value), f"original constant {name} = {c[name]}, expected {value}"
    assert c["powder"] == 3.0 and c["powder_tiny"] == f32(0.1 * 3) == c["powder_tiny"] and c["plateCast"] == 3.0, "derived shape constants"
    haz = ctx["original"][O_HAZ].split("\n")
    need(haz, 93, "public static final float uzh = 0.125F;")
    need(haz, 517, "for(String ore : TH232.all(MaterialShapes.ORE)) HazardSystem.blacklist(ore);")
    need(haz, 518, "for(String ore : U.all(MaterialShapes.ORE)) HazardSystem.blacklist(ore);")
    return "float32 constants (u .35, uzh .125 at :93, sr = sb = sa326 * .1, saf 5.85, ...), blacklist :517-518 for the U and TH232 ore keys"


def c_a_autogen(ctx):
    auto = ctx["model"]["autogen"]
    assert set(auto) == {"NA", "SR", "LI"}, "autogen frames"
    assert "NUGGET" in auto["NA"][1] and "INGOT" in auto["NA"][1], "Mats.java:135 sodium autogen NUGGET + INGOT"
    assert "NUGGET" in auto["SR"][1] and "INGOT" in auto["SR"][1], "Mats.java:137 strontium autogen NUGGET + INGOT"
    assert "NUGGET" in auto["LI"][1] and "INGOT" not in auto["LI"][1], "Mats.java:139 lithium autogen NUGGET, no INGOT"
    assert {k: v[0] for k, v in auto.items()} == {"NA": "MAT_SODIUM", "SR": "MAT_STRONTIUM", "LI": "MAT_LITHIUM"}, "autogen material constants"
    assert (auto["NA"][3], auto["SR"][3], auto["LI"][3]) == (1100, 3800, 300), "autogen material ids (the ingot_raw / nugget_raw metas)"
    hazard_frames = {name for _, name in FRAME_ROWS}
    found = ctx["model"]["ingot_nugget_frames"] & hazard_frames
    assert found == {"NA", "SR", "LI"}, "hazard frames with an autogen ingot or nugget: " + str(found)
    odm = ctx["original"][O_ODM].split("\n")
    need(odm, 550, "mat.autogen.contains(MaterialShapes.INGOT)", "new ItemStack(ModItems.ingot_raw, 1, mat.id)")
    need(odm, 551, "mat.autogen.contains(MaterialShapes.NUGGET)", "new ItemStack(ModItems.nugget_raw, 1, mat.id)")
    return "Mats.java:135 MAT_SODIUM 1100 (NUGGET, INGOT), :137 MAT_STRONTIUM 3800 (NUGGET, INGOT), :139 MAT_LITHIUM 300 (NUGGET); OreDictManager.java:550-551 register " \
           "them as ingot_raw / nugget_raw metas; no other hazard frame has an autogen ingot or nugget"


def c_a_itemrows(ctx):
    rows = ctx["model"]["item_rows"]
    assert len(rows) == 35, f"{len(rows)} item-level rows"
    haz = ctx["original"][O_HAZ].split("\n")
    need(haz, 293, "billet_uzh", "uzh * billet")
    need(haz, 473, "powder_yellowcake", "yc * powder")
    need(haz, 474, "block_yellowcake", "yc * block * powder_mult")
    return "35 item-level rows: :289-293, :295-298, :300-303, :305-307, :309-312, :314-316, :318-321, :323-325, :327-329, :473-474"


def c_a_no_overlap(ctx):
    """No direct original row registers an item that a frame row also covers (it would carry two sources)."""
    model, neo = ctx["model"], ctx["neo_ids"]
    frame_names = set()
    for row in model["rows"]:
        for call, args in row["calls"]:
            if call in SHAPE_CONST and call not in ORE_SHAPES:
                frame_names.update(a for a in args if re.fullmatch(r"\w+", a))
    direct = set(re.findall(r"HazardSystem\.register\((\w+),", ctx["original"][O_HAZ]))
    both = sorted(frame_names & direct)
    assert not both, "items registered by a frame row and by a direct HazardRegistry row: " + str(both)
    shared = []
    for name, (line, mats) in model["all_frames"].items():
        if name in model["frame_mats"]:
            continue
        for hazard_frame, hmats in model["frame_mats"].items():
            if set(mats) & set(hmats):
                shared.append((name, hazard_frame))
    assert shared == [("ST", "SR")], f"frames sharing a material name with a hazard frame: {shared}"
    return "no frame item has a direct original row; the only non-hazard frame sharing a material name is ST (powder_strontium, also in SR)"


# ---------------------------------------------------------------- A2: the expected table (from the original alone)

def identity(name, shape, neo):
    if not re.fullmatch(r"\w+", name):
        return None
    order = ("block", "item") if shape == "block" else ("item", "block")
    for kind in order:
        if name in neo[kind + "_ids"]:
            return kind, name
    return None


def build_table(ctx):
    """Every original row/shape/argument as one table row with its state; entries are float32 values."""
    model, neo = ctx["model"], ctx["neo_ids"]
    consts = model["consts"]
    rows = []
    for row in model["rows"]:
        hazards, mult, mats = [], None, model["frame_mats"][row["frame"]]
        for call, args in row["calls"]:
            if call in HAZ_CALLS:
                assert len(args) == 1
                hazards.append((HAZ_CALLS[call], eval_float(args[0], consts)))
                continue
            if call in SHAPE_CONST:
                mult = consts[SHAPE_CONST[call]]
                targets = [(a, call) for a in args]
            elif call in AUTO_CALLS:
                const, tag, prefix = AUTO_CALLS[call]
                mult = consts[const]
                mat = AUTOGEN_MAT[row["frame"]]
                autogen = model["autogen"][row["frame"]]
                assert tag in autogen[1], f"{row['frame']}: no autogen {tag} for {call}"
                targets = [(prefix + MAT_NAME[mat], const)] if call == "hazNugget" else [(f"ingot_raw meta {autogen[3]}", const)]
            else:
                raise AssertionError(f"unknown call {call} in OreDictManager:{row['line']}")
            entries = [(t, f32(v * mult)) for t, v in hazards] if hazards and mult > 0 else []
            for arg, shape in targets:
                base = dict(orig_line=row["line"], frame=row["frame"], source="OreDictManager.DictFrame", call=call, original=arg, mutex=0b1,
                            entries=entries, neo_id=None, neo_kind=None, reason=None)
                if call in ORE_SHAPES:
                    base.update(state=ST_ORE, reason="Goal21 decision 13: NEO has no ore dictionary and ore blocks are never registered; the original "
                                                     "blacklists the U and TH232 ore keys at HazardRegistry.java:517-518, the PU nether ore and the SA326 ores do carry hazards there")
                elif call in AUTO_CALLS:
                    if call == "hazNugget":
                        ident = identity(arg, "nugget", neo)
                    else:
                        meta = model["autogen"][row["frame"]][3]
                        ident = ("stack", f"ingot_raw#{meta}") if "ingot_raw" in neo["item_ids"] and meta in neo["raw_metas"].values() else None
                    note = f"{call}() registers only the ore key {AUTO_CALLS[call][1].lower()}{mats[0]}; in the original it reaches the autogen {AUTO_CALLS[call][1]} of " \
                           f"{AUTOGEN_MAT[row['frame']]} (Mats.java:{model['autogen'][row['frame']][2]}, OreDictManager.java:{550 if call == 'hazIngot' else 551})"
                    if ident:
                        base.update(state=ST_REG, neo_id=ident[1], neo_kind=ident[0],
                                    reason=note + ("; NEO's ingot_raw item with that meta, registered as a stack" if ident[0] == "stack" else f"; NEO's dedicated item {ident[1]} stands for it"))
                    else:
                        base.update(state=ST_SKIP, reason=note + f"; NEO has no {arg}")
                else:
                    ident = identity(arg, call, neo)
                    if ident:
                        base.update(state=ST_REG, neo_id=ident[1], neo_kind=ident[0])
                    elif call == "plateCast":
                        base.update(state=ST_SKIP, reason="NEO has no cast plate (original: Mats.MAT_SCHRABIDIUM.make(plate_cast))")
                    else:
                        base.update(state=ST_SKIP, reason=f"NEO has no item or block {arg}")
                rows.append(base)
    for row in model["item_rows"]:
        entries = [(t, eval_float(e, consts)) for t, e in row["entries"]]
        shape = "block" if row["name"].startswith("block_") else "item"
        ident = identity(row["name"], shape, neo)
        base = dict(orig_line=row["line"], frame=None, source="HazardRegistry.registerItems", call="register", original=row["name"], mutex=None,
                    entries=entries, neo_id=None, neo_kind=None, reason=None)
        if ident:
            base.update(state=ST_REG, neo_id=ident[1], neo_kind=ident[0])
        else:
            base.update(state=ST_SKIP, reason=f"NEO has no item or block {row['name']}")
        rows.append(base)
    return rows


def c_a2_table(ctx):
    table = ctx["table"]
    assert all(r["state"] in STATES for r in table), "a row has a state outside the three allowed"
    registered = [r for r in table if r["state"] == ST_REG]
    ids = [r["neo_id"] for r in registered]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, "NEO ids that two rows register: " + str(dup)
    for r in table:
        assert r["state"] == ST_REG or r["reason"], "a skipped row without a reason: " + str(r["original"])
        if r["state"] == ST_REG:
            assert r["entries"] and all(isinstance(v, float) and v > 0 for _, v in r["entries"]), f"{r['neo_id']}: no entries"
    neo = ctx["neo_ids"]
    for name in NEO_ONLY_UNREGISTERED:
        assert name in neo["item_ids"], f"{name} is not a NEO item any more"
        assert name not in ids, f"{name} must stay unregistered"
    counts = {s: sum(1 for r in table if r["state"] == s) for s in STATES}
    return f"{len(table)} rows: {counts[ST_REG]} {ST_REG}, {counts[ST_SKIP]} {ST_SKIP}, {counts[ST_ORE]} {ST_ORE}; every registered NEO id unique"


def c_a2_skips(ctx):
    skips = sorted((r["orig_line"], r["original"]) for r in ctx["table"] if r["state"] == ST_SKIP)
    return f"{len(skips)} skipped rows: " + ", ".join(f":{n} {o}" for n, o in skips)


# ---------------------------------------------------------------- NEO ids and the NEO model

def neo_id_maps(items_text, blocks_text, raw_text):
    def table(text, cls):
        pat = rf"public static final Deferred{cls}<[^>]*>\s+(\w+)\s*=\s*(?:\w+\.)?\w+\(\s*\"([^\"]+)\""
        return {const: ident for const, ident in re.findall(pat, strip_keep(text))}
    item_c, block_c = table(items_text, "Item"), table(blocks_text, "Block")
    raw = {name: int(meta) for name, meta in re.findall(r"\b([A-Z]\w+)\((\d+), \"hbmmat\.", raw_text)}
    return dict(item_c=item_c, block_c=block_c, item_ids={i: c for c, i in item_c.items()}, block_ids={i: c for c, i in block_c.items()}, raw_metas=raw)


def resolve_target(arg, neo):
    arg = arg.strip()
    arg = arg[:-len(".get()")] if arg.endswith(".get()") else arg
    if arg.startswith("NtmBlocks."):
        const, kinds = arg[len("NtmBlocks."):], ("block",)
    elif arg.startswith("NtmItems."):
        const, kinds = arg[len("NtmItems."):], ("item",)
    else:
        const, kinds = arg, ("item", "block")
    for kind in kinds:
        if const in neo[kind + "_c"]:
            return kind, neo[kind + "_c"][const]
    raise AssertionError(f"cannot resolve {arg!r} to a NEO item or block")


def neo_frame_class(code):
    """Semantics of the private Frame class: hazard methods, shape multipliers and the registration body."""
    start, end = block_span(code, "private static class Frame")
    body = flat(code[start:end + 1])
    haz = dict(re.findall(r"Frame (\w+)\(float \w+\) \{ return haz\(new HazardEntry\((\w+), \w+\)\); \}", body))
    shapes = {name: const.replace("HazardRegistry.", "") for name, const in re.findall(r"Frame (\w+)\(ItemLike\.\.\. things\) \{ return shape\(([\w.]+), things\); \}", body)}
    stack_shapes = {name: const.replace("HazardRegistry.", "") for name, const in re.findall(r"Frame (\w+)\(ItemStack\.\.\. stacks\) \{ return shape\(([\w.]+), stacks\); \}", body)}
    return dict(span=(line_of(code, start), line_of(code, end)), body=body, haz=haz, shapes=shapes, stack_shapes=stack_shapes)


def resolve_arg(arg, neo):
    """Frame argument -> (kind, id): an item/block constant, or rawIngot(RawIngotItem.Type.X) -> a stack of ingot_raw."""
    m = re.fullmatch(r"rawIngot\(RawIngotItem\.Type\.(\w+)\)", arg.strip())
    if m:
        assert "INGOT_RAW" in neo["item_c"] and neo["item_c"]["INGOT_RAW"] == "ingot_raw", "INGOT_RAW is not ingot_raw"
        return "stack", f"ingot_raw#{neo['raw_metas'][m.group(1)]}"
    return resolve_target(arg, neo)


def neo_model(ctx):
    """Parses the NEO HazardRegistry into frame registrations, item-level rows and the full key list."""
    text = ctx["live"][HAZ]
    code = strip_keep(text)
    raw = text.split("\n")
    codelines = code.split("\n")
    neo = ctx["neo_ids"]
    consts = float_consts(text)
    frame = neo_frame_class(code)

    start, end = block_span(code, "private static void registerMaterials()")
    first, last = line_of(code, start), line_of(code, end)
    frame_lines, issues = [], []
    for number in range(first + 1, last):
        c = codelines[number - 1].strip()
        if not c:
            continue
        m = re.fullmatch(r"frame\(\)((?:\.\w+\(.*?\))+);", c)
        if not m:
            issues.append(f"registerMaterials line {number} is not a frame chain: {c[:80]!r}")
            continue
        comment = re.search(r"//\s*:(\d+)\b", raw[number - 1])
        regs, hazards, mult = [], [], None
        for call, args in parse_chain(m.group(1)):
            if call in frame["haz"]:
                hazards.append((frame["haz"][call], eval_float(args[0], consts)))
            elif call in frame["shapes"]:
                mult = consts[frame["shapes"][call]]
                for a in args:
                    kind, ident = resolve_arg(a, neo)
                    if kind == "stack":
                        assert call in frame["stack_shapes"] and frame["stack_shapes"][call] == frame["shapes"][call], f"line {number}: no ItemStack overload of {call} with the same multiplier"
                    regs.append(dict(id=ident, kind=kind, call=call, entries=[(t, f32(v * mult)) for t, v in hazards]))
            else:
                issues.append(f"line {number}: unknown frame call {call}")
        frame_lines.append(dict(line=number, comment=int(comment.group(1)) if comment else None, regs=regs))

    items_start, items_end = block_span(code, "public static void registerItems()")
    ifirst, ilast = line_of(code, items_start), line_of(code, items_end)
    keys, rows = [], {}
    for number in range(ifirst + 1, ilast):
        c = codelines[number - 1].strip()
        if not c.startswith("HazardSystem.register("):
            continue
        open_index = c.index("(")
        close = matching_paren(c, open_index)
        args = split_args(c[open_index + 1:close])
        target = args[0]
        m = re.fullmatch(r"(item|block)\(([\w.]+)\)", target)
        if m:
            kind, ident = resolve_target(m.group(2) if m.group(1) == "item" else m.group(2), neo)
            if m.group(1) == "item" and not m.group(2).startswith(("NtmBlocks.", "NtmItems.")):
                kind, ident = ("item", neo["item_c"][m.group(2)]) if m.group(2) in neo["item_c"] else resolve_target(m.group(2), neo)
            declared = m.group(1)
            keys.append((ident, number))
            entries = [(t, eval_float(e, consts)) for t, e in parse_makedata(c[open_index + 1:close].split(",", 1)[1])]
            rows[ident] = dict(line=number, kind=kind, declared=declared, entries=entries,
                               comment=(lambda mm: int(mm.group(1)) if mm else None)(re.search(r"//\s*:(\d+)\b", raw[number - 1])))
        elif re.fullmatch(r"Items\.\w+|Blocks\.\w+", target):
            keys.append(("minecraft:" + target.split(".")[1].lower(), number))
        elif re.fullmatch(r"Ntm(Items|Blocks)\.\w+\.get\(\)", target):
            keys.append((resolve_target(target, neo)[1], number))
        else:
            keys.append((flat(target), number))
    for number in range(ifirst + 1, ilast):
        c = codelines[number - 1].strip()
        m = re.match(r"(registerBreedingRodRadiation|registerOtherFuel|registerOtherWaste)\((.*)\);", c)
        if m:
            args = split_args(m.group(2))
            keys.append((m.group(1) + ":" + ",".join(args[:2] if m.group(1) == "registerOtherFuel" else args[:1]), number))
    for fl in frame_lines:
        for reg in fl["regs"]:
            keys.append((reg["id"], fl["line"]))
    return dict(consts=consts, frame=frame, frame_lines=frame_lines, issues=issues, item_rows=rows, keys=keys,
                reg_span=(first, last), items_span=(ifirst, ilast))


def expected_by_line(ctx):
    """original OreDictManager line -> ordered [(id, kind, entries)] of the registered rows."""
    out = {}
    for r in ctx["table"]:
        if r["state"] == ST_REG and r["source"].startswith("OreDictManager"):
            out.setdefault(r["orig_line"], []).append((r["neo_id"], r["neo_kind"], r["entries"]))
    return out


def same_entries(a, b):
    return [(t, f32_bits(v)) for t, v in a] == [(t, f32_bits(v)) for t, v in b]


def c_a3_frames(ctx):
    nm = ctx["nm"]
    assert not nm["issues"], "; ".join(nm["issues"])
    numbers = [fl["comment"] for fl in nm["frame_lines"]]
    assert numbers == [n for n, _ in FRAME_ROWS], f"`// :NNN` comments {numbers} != the original lines"
    expected = expected_by_line(ctx)
    for fl in nm["frame_lines"]:
        want = expected.get(fl["comment"], [])
        got = [(r["id"], r["kind"], r["entries"]) for r in fl["regs"]]
        assert [(i, k) for i, k, _ in got] == [(i, k) for i, k, _ in want], f"line {fl['line']} (:{fl['comment']}): items {[(i, k) for i, k, _ in got]} != {[(i, k) for i, k, _ in want]}"
        for (i, _, e), (_, _, we) in zip(got, want):
            assert same_entries(e, we), f"line {fl['line']} (:{fl['comment']}) {i}: entries {[(t, f32_repr(v)) for t, v in e]} != {[(t, f32_repr(v)) for t, v in we]}"
    n = sum(len(fl["regs"]) for fl in nm["frame_lines"])
    return f"36 frame lines in original order with `// :NNN`; {n} item/block registrations equal the expected ids, entry order and float32 values"


def c_a3_frame_class(ctx):
    f = ctx["nm"]["frame"]
    assert f["haz"] == {"rad": "RADIATION", "hot": "HOT", "blinding": "BLINDING", "hydro": "HYDROACTIVE"}, f"Frame hazard methods {f['haz']}"
    expected = {k: v for k, v in {"nugget": "nugget", "billet": "billet", "ingot": "ingot", "dustSmall": "powder_tiny", "dust": "powder",
                                   "plate": "plate", "block": "block"}.items()}
    assert f["shapes"] == expected, f"Frame shape multipliers {f['shapes']}"
    body = f["body"]
    assert "private final List<HazardEntry> hazards = new ArrayList<>();" in body, "Frame.hazards"
    assert "private Frame haz(HazardEntry hazard) { hazards.add(hazard); return this; }" in body, "Frame.haz adds in call order"
    assert f["stack_shapes"] == {"ingot": "ingot"}, f"Frame ItemStack overloads {f['stack_shapes']}"
    assert "private Frame shape(float hazMult, ItemLike... things) { for(ItemLike thing : things) HazardSystem.register(thing.asItem(), data(hazMult)); return this; }" in body, \
        "Frame.shape(ItemLike...) must register data(hazMult) on thing.asItem() (itemMap)"
    assert "private Frame shape(float hazMult, ItemStack... stacks) { for(ItemStack stack : stacks) HazardSystem.register(stack, data(hazMult)); return this; }" in body, \
        "Frame.shape(ItemStack...) must register data(hazMult) on the stack (stackMap)"
    assert "private HazardData data(float hazMult) { HazardData data = new HazardData().setMutex(0b1); for(HazardEntry hazard : hazards) data.addEntry(hazard.clone(hazMult)); return data; }" in body, \
        "Frame.data must build `new HazardData().setMutex(0b1)` with every entry cloned by hazMult"
    code = strip_keep(ctx["live"][HAZ])
    assert "private static ItemStack rawIngot(RawIngotItem.Type type) { return MetaHelper.newStack(INGOT_RAW, type.meta); }" in flat(code), "rawIngot helper"
    return "Frame: rad/hot/blinding/hydro -> RADIATION/HOT/BLINDING/HYDROACTIVE in call order; shape multipliers nugget, billet, ingot, powder_tiny, powder, plate, block; " \
           "setMutex(0b1), clone(hazMult) per entry; ItemLike shapes on thing.asItem() (itemMap), the ingot(ItemStack...) overload on the stack (stackMap)"


def c_a3_item_rows(ctx):
    nm = ctx["nm"]
    inserted = ctx["diff"]["inserted"]
    text = ctx["live"][HAZ].split("\n")
    expected = {r["neo_id"]: r for r in ctx["table"] if r["state"] == ST_REG and r["source"].startswith("HazardRegistry")}
    new_ids = {i for i, row in nm["item_rows"].items() if row["line"] in inserted}
    assert new_ids == set(expected), f"item-level rows in the inserted lines: extra {sorted(new_ids - set(expected))}, missing {sorted(set(expected) - new_ids)}"
    for ident, want in expected.items():
        row = nm["item_rows"][ident]
        assert row["kind"] == want["neo_kind"] and row["declared"] == want["neo_kind"], f"{ident}: registered through {row['declared']}(), expected {want['neo_kind']}"
        assert same_entries(row["entries"], want["entries"]), f"{ident}: entries {[(t, f32_repr(v)) for t, v in row['entries']]} != {[(t, f32_repr(v)) for t, v in want['entries']]}"
        if want["orig_line"] <= 329:
            assert row["comment"] == want["orig_line"], f"{ident}: line comment :{row['comment']}, original line {want['orig_line']}"
    for number, marker in ((min(nm["item_rows"][i]["line"] for i in expected if expected[i]["orig_line"] <= 329), ":289-329"),
                           (nm["item_rows"]["powder_yellowcake"]["line"], ":473-474")):
        above = next(text[n - 1] for n in range(number - 1, 0, -1) if text[n - 1].strip())
        assert marker in above, f"the block comment above line {number} does not cite {marker}: {above.strip()[:90]!r}"
    for ident in ("powder_yellowcake", "block_yellowcake"):
        assert nm["item_rows"][ident]["comment"] is None, f"{ident}: yellowcake rows carry a block comment, not a `// :NNN`"
    return f"{len(expected)} item-level rows (33 fuel + 2 yellowcake): ids, item()/block() kind, ordered float32 entries (blinding 5F * shape), no mutex, `// :NNN` equals the original line"


def c_a3_registered_set(ctx):
    nm = ctx["nm"]
    inserted = ctx["diff"]["inserted"]
    frame_ids = [r["id"] for fl in nm["frame_lines"] for r in fl["regs"]]
    item_ids = [i for i, row in nm["item_rows"].items() if row["line"] in inserted]
    registered = sorted(frame_ids + item_ids)
    expected = sorted(r["neo_id"] for r in ctx["table"] if r["state"] == ST_REG)
    assert registered == expected, f"registered ids differ from the expected set: extra {sorted(set(registered) - set(expected))}, missing {sorted(set(expected) - set(registered))}"
    bad = sorted(i for i in registered if OUT_OF_SCOPE_ID.search(i))
    assert not bad, "out-of-scope or NEO-only ids registered: " + str(bad)
    for name in NEO_ONLY_UNREGISTERED:
        assert name not in registered, name + " is registered"
    stacks = sorted(i for i in registered if i.startswith("ingot_raw#"))
    assert stacks == ["ingot_raw#1100", "ingot_raw#3800"], f"ingot_raw metas registered: {stacks}; the other metas (1 redstone, 6000, 501, 41) must stay hazard-free"
    return f"{len(registered)} ids registered by Goal21D, exactly the expected set; none of the NEO-only or out-of-scope ids ({', '.join(NEO_ONLY_UNREGISTERED)}, crystals, rad-source billets, RTG pellets, P_WHITE, asbestos, ...)"


def c_a3_no_duplicates(ctx):
    seen, dup = {}, []
    for key, line in ctx["nm"]["keys"]:
        if key in seen:
            dup.append((key, seen[key], line))
        seen[key] = line
    assert not dup, "registered twice (key, first line, second line): " + str(dup[:6])
    return f"{len(ctx['nm']['keys'])} registration keys in registerItems and registerMaterials, none twice"


def c_a3_no_ores(ctx):
    code = strip_keep(ctx["live"][HAZ])
    found = sorted(set(re.findall(r"\bORE_\w+", code)))
    assert not found, "ore blocks referenced in HazardRegistry: " + str(found)
    ids = [i for i, _ in ctx["nm"]["keys"]]
    assert not [i for i in ids if i.startswith("ore_")], "an ore id is registered"
    return "no ORE_* constant in HazardRegistry.java and no ore_* id registered"


def c_a3_structure(ctx):
    nm = ctx["nm"]
    code = strip_keep(ctx["live"][HAZ])
    start, end = block_span(code, "public static void registerItems()")
    assert flat(code[start:end]).count("registerMaterials();") == 1, "registerItems must call registerMaterials() once"
    assert code.count("registerMaterials()") == 2, "registerMaterials declared once and called once"
    assert re.search(r"private static void registerMaterials\(\)", code), "registerMaterials is private static void"
    consts = nm["consts"]
    expected = ctx["model"]["consts"]
    used = ["u", "u233", "u235", "u238", "th232", "pu", "purg", "pu238", "pu239", "pu240", "pu241", "am241", "am242", "amrg", "np237", "po210", "tc99",
            "ra226", "ac227", "co60", "au198", "pb209", "sa326", "sa327", "sb", "sr", "gh336", "mud", "sr90", "i131", "xe135", "cs137", "at209", "uf", "uzh",
            "puf", "thf", "npf", "mox", "amf", "saf", "yc", "nugget", "billet", "ingot", "powder", "powder_tiny", "plate", "block", "powder_mult"]
    wrong = {n: (consts.get(n), expected[n]) for n in used if consts.get(n) != expected[n]}
    assert not wrong, "NEO constants differ from the original: " + str(wrong)
    assert ctx["live"][HAZ].count("public static final float uzh = 0.125F;") == 1, "uzh constant line"
    return "registerMaterials() private, called once from registerItems; the 51 constants the rows use equal the original in float32 (uzh = 0.125F added)"


# ---------------------------------------------------------------- A4: start diff and scope

@functools.lru_cache(maxsize=16)
def diff_info(start, live):
    a, b = start.split("\n"), live.split("\n")
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    bad = [op for op in ops if op[0] not in ("equal", "insert")]
    inserted, hunks = set(), []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "insert":
            inserted.update(range(j1 + 1, j2 + 1))
            hunks.append((i1 + 1, j1 + 1, j2, j2 - j1))
    return dict(bad=bad[:3], inserted=inserted, hunks=hunks)


def c_a4_insert_only(ctx):
    info = ctx["diff"]
    assert not info["bad"], "HazardRegistry differs from the frozen start by more than insertions: " + str(info["bad"])
    assert ctx["eol"][HAZ] == ctx["start_eol"][HAZ] == "CRLF", f"line endings start {ctx['start_eol'][HAZ]} live {ctx['eol'][HAZ]}"
    assert not ctx["bom"][HAZ], "HazardRegistry gained a BOM"
    return f"start + {sum(h[3] for h in info['hunks'])} inserted lines in {len(info['hunks'])} hunks (live lines " + ", ".join(
        f"{h[1]}-{h[2]}" for h in info["hunks"]) + "); every start line unchanged and in order; CRLF kept"


def c_a4_inserted_lines(ctx):
    nm, info = ctx["nm"], ctx["diff"]
    lines = ctx["live"][HAZ].split("\n")
    rm_first, rm_last = nm["reg_span"]
    # the javadoc above registerMaterials() starts the generated span; the Frame class closes it
    code = strip_keep(ctx["live"][HAZ])
    j = rm_first
    while j > 1 and "/**" not in lines[j - 1]:
        j -= 1
    span = (j, nm["frame"]["span"][1])
    assert span[0] < rm_first and rm_first - span[0] < 10, "registerMaterials() has no javadoc"
    allowed_imports = {"import net.minecraft.world.level.ItemLike;", "import java.util.ArrayList;", "import java.util.List;",
                       "import net.minecraft.world.item.ItemStack;", "import com.hbm.items.RawIngotItem;"}
    expected_ids = {r["neo_id"] for r in ctx["table"] if r["state"] == ST_REG and r["source"].startswith("HazardRegistry")}
    stray = []
    for number in sorted(info["inserted"]):
        if span[0] <= number <= span[1]:
            continue
        s = lines[number - 1].strip()
        if not s or s == "}" or s.startswith(("//", "/*", "*")) or s in allowed_imports or s == "registerMaterials();":
            continue
        if re.fullmatch(r"public static final float uzh = 0\.125F;( //.*)?", s):
            continue
        m = re.match(r"HazardSystem\.register\((?:item|block)\(([\w.]+)\), makeData", s)
        if m and any(number == row["line"] and ident in expected_ids for ident, row in nm["item_rows"].items()):
            continue
        stray.append((number, s[:80]))
    assert not stray, "inserted lines that are not part of the Goal21D change: " + str(stray[:5])
    ins = sum(1 for n in info["inserted"] if span[0] <= n <= span[1])
    return f"{ins} inserted lines form registerMaterials() and the Frame class (live :{span[0]}-{span[1]}); every other inserted line is a blank, comment, brace, " \
           f"ItemLike/ArrayList/List import, the uzh constant, an item-level row of the expected set or the registerMaterials() call"


def c_a4_hashes(ctx):
    base = ctx["baseline_files"]
    paths = list(UNCHANGED_HAZARD_FILES) + [COMMON_EVENTS] + sorted(p for p in base if p.startswith(tuple(UNCHANGED_HAZARD_DIRS)))
    bad = [p for p in paths if p not in base or ctx["hashes"].get(p) != base[p]]
    assert not bad, "differ from baseline.json: " + str(bad)
    assert ctx["start_hash"] == base[HAZ], "baseline-files HazardRegistry.java is not the baseline.json file"
    return f"{len(paths)} files (HazardSystem, HazardData, HazardEntry, hazard/type, modifier, transformer, CommonEvents) hash-equal to baseline.json; the start copy equals baseline.json"


def c_a4_scope(ctx):
    changed = ctx["scope_changed"]
    allowed = {HAZ, GAMETEST, STAMP}
    extra = sorted(set(changed) - allowed)
    assert not extra, "src/ paths changed against baseline.json outside the Goal21D scope: " + str(extra[:8])
    assert HAZ in changed, "HazardRegistry.java is unchanged"
    return f"{len(changed)} src/ path(s) differ from baseline.json: " + ", ".join(sorted(changed))


def c_a4_language(ctx):
    base = ctx["baseline_files"]
    bad = [p for p in LANGUAGE_FILES if ctx["hashes"].get(p) != base.get(p)]
    assert not bad, "language files or zh mapping changed: " + str(bad)
    return "zh_cn.json, zh_cn-map.json, generated en_us.json and NtmLanguageProvider.java hash-equal to baseline.json (no new key)"


# ---------------------------------------------------------------- A5: arithmetic samples

def c_a5_samples(ctx):
    rows = {r["neo_id"]: r for r in ctx["table"] if r["state"] == ST_REG}
    nm = ctx["nm"]
    out = []
    for ident, typ, decimal in SAMPLES:
        row = rows[ident]
        expected = dict(row["entries"])[typ]
        live = None
        for fl in nm["frame_lines"]:
            for reg in fl["regs"]:
                if reg["id"] == ident:
                    live = dict(reg["entries"])[typ]
        if ident in nm["item_rows"]:
            live = dict(nm["item_rows"][ident]["entries"])[typ]
        assert live is not None, ident + " is not registered in NEO"
        assert live == expected, f"{ident}: NEO {f32_repr(live)} != original {f32_repr(expected)}"
        assert abs(live - float(decimal)) <= 1e-6 * float(decimal), f"{ident}: {f32_repr(live)} is not {decimal}"
        out.append(f"{ident} {typ} {f32_repr(live)}")
    return "; ".join(out)


# ---------------------------------------------------------------- GameTest class and A7

def gametest_tests(text):
    code = strip_keep(text)
    consts = dict(re.findall(r'static final String (\w+) = "([^"]*)";', code))
    found = {}
    for m in re.finditer(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper", code):
        batch = re.search(r'batch\s*=\s*("([^"]*)"|(\w+))', m.group(1))
        found[m.group(2)] = None if not batch else batch.group(2) if batch.group(2) is not None else consts.get(batch.group(3))
    return found


def c_g_gametest_class(ctx):
    text = ctx["gametest"]
    if text is None:
        return ("pending", GAMETEST + " not written yet")
    code = strip_keep(text)
    assert "@GameTestHolder(" in code and "@PrefixGameTestTemplate(false)" in code, "GameTestHolder / PrefixGameTestTemplate"
    found = gametest_tests(text)
    assert found, "no @GameTest methods"
    wrong = {n: b for n, b in found.items() if b != GAMETEST_BATCH}
    assert not wrong, f"GameTests not in batch {GAMETEST_BATCH!r}: {wrong}"
    forbidden = re.findall(r"makeMockPlayer|makeMockServerPlayer|FakePlayer|FakePlayerFactory|java\.lang\.reflect|getDeclaredField|getDeclaredMethod|setAccessible|"
                           r"import (?:net\.minecraft\.client|net\.neoforged\.neoforge\.client|com\.mojang\.blaze3d|com\.hbm\.render)", code)
    assert not forbidden, "forbidden in the GameTest class: " + str(forbidden)
    assert code.count("check(") > 20, "GameTest class barely asserts anything"
    return f"{len(found)} GameTests in batch {GAMETEST_BATCH}: {', '.join(found)}; no mock/fake player, reflection or client imports"


def c_a7_log(ctx):
    path = ctx.get("gametest_log")
    if not path:
        return ("pending", "no --gametest-log given")
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    names = list(gametest_tests(ctx["gametest"]))
    old = sum(len(gametest_tests(ctx["gametest_others"][p])) for p in ctx["gametest_others"])
    assert old == OLD_TEST_COUNT, f"{old} pre-existing GameTests in the source, expected {OLD_TEST_COUNT}"
    total = old + len(names)
    m = re.search(r"All (\d+) required tests passed", text)
    assert m, "no `All N required tests passed` line"
    assert int(m.group(1)) == total, f"All {m.group(1)} required tests passed, expected {total} ({old} old + {len(names)} new)"
    assert re.search(rf"{total} GAME TESTS COMPLETE", text), "no `GAME TESTS COMPLETE` line for the expected count"
    assert not re.search(r"required tests failed|optional tests failed", text), "the log reports failed tests"
    missing = [n for n in names if not re.search(rf"\[hbm-hazard\] {re.escape(n)} passed", text)]
    assert not missing, "tests without a pass marker in the log: " + str(missing)
    batches = [int(k) for k in re.findall(rf"Running test batch '{GAMETEST_BATCH}:\d+' \((\d+) tests\)", text)]
    assert sum(batches) == len(names), f"batch {GAMETEST_BATCH}: {batches} tests, expected {len(names)}"
    assert "BUILD SUCCESSFUL" in text, "no BUILD SUCCESSFUL"
    return f"{Path(path).name}: `All {total} required tests passed`, {len(names)} pass markers for {', '.join(names)}, BUILD SUCCESSFUL"


def c_a7_jar(ctx):
    jar = ctx.get("jar")
    if not jar:
        return ("pending", "no --jar given")
    for cls in ("com/hbm/hazard/HazardRegistry.class", "com/hbm/hazard/HazardRegistry$Frame.class", "com/hbm/gametest/HazardGameTests.class"):
        assert cls in jar["names"], "JAR lacks " + cls
    return "JAR has HazardRegistry, HazardRegistry$Frame and HazardGameTests"


# ---------------------------------------------------------------- original git state

def git_checks():
    head = git(ORIGINAL, "rev-parse", "HEAD").strip()
    status = git(ORIGINAL, "status", "--porcelain=v1", "--untracked-files=all")
    return {"A_original_head_clean": dict(status="pass" if head == ORIGINAL_HEAD and status == "" else "fail",
                                          detail=f"original HEAD {head}, status {'clean' if status == '' else status[:200]!r}")}


# ---------------------------------------------------------------- registry of checks

CHECKS = [
    ("A1_target_rows", c_a_rows), ("A1_dictframe", c_a_dictframe), ("A1_constants", c_a_constants), ("A1_autogen", c_a_autogen),
    ("A1_item_rows", c_a_itemrows), ("A1_no_overlap", c_a_no_overlap),
    ("A2_expected_table", c_a2_table), ("A2_skips", c_a2_skips),
    ("A3_frame_chains", c_a3_frames), ("A3_frame_class", c_a3_frame_class), ("A3_item_rows", c_a3_item_rows), ("A3_registered_set", c_a3_registered_set),
    ("A3_no_duplicates", c_a3_no_duplicates), ("A3_no_ores", c_a3_no_ores), ("A3_structure_and_constants", c_a3_structure),
    ("A4_insert_only", c_a4_insert_only), ("A4_inserted_lines", c_a4_inserted_lines), ("A4_hash_equal_files", c_a4_hashes), ("A4_change_scope", c_a4_scope),
    ("A4_language_unchanged", c_a4_language),
    ("A5_arithmetic_samples", c_a5_samples),
    ("G_gametest_class", c_g_gametest_class), ("A7_gametest_log", c_a7_log), ("A7_jar", c_a7_jar),
]


def run_checks(ctx):
    results = {}
    try:
        prepare_full(ctx)
        prep_error = None
    except (AssertionError, KeyError, ValueError, IndexError, AttributeError, TypeError) as error:
        prep_error = f"{type(error).__name__}: {error}"[:600]
    for name, fn in CHECKS:
        try:
            if prep_error and name.startswith(("A3_", "A4_inserted", "A5_")):
                raise AssertionError("NEO HazardRegistry cannot be analysed: " + prep_error)
            out = fn(ctx)
            results[name] = dict(status=out[0], detail=out[1]) if isinstance(out, tuple) else dict(status="pass", detail=out)
        except (AssertionError, KeyError, ValueError, IndexError, AttributeError, TypeError, StopIteration, re.error) as error:
            results[name] = dict(status="fail", detail=f"{type(error).__name__}: {error}"[:600])
    return results


def prepare_full(ctx):
    """Prepares model, table and diff separately so that a broken NEO file fails only the checks that read it."""
    for key in ("model", "neo_ids", "table", "diff", "nm"):
        ctx.pop(key, None)
    ctx["model"] = parse_original(ctx)
    ctx["neo_ids"] = neo_id_maps(ctx["items_text"], ctx["blocks_text"], ctx["raw_text"])
    ctx["table"] = build_table(ctx)
    ctx["diff"] = diff_info(ctx["start"][HAZ], ctx["live"][HAZ])
    ctx["nm"] = neo_model(ctx)


# ---------------------------------------------------------------- A6: mutations (in memory only)

def clone(ctx):
    out = dict(ctx)
    for key, value in ctx.items():
        if isinstance(value, dict):
            out[key] = dict(value)
        elif isinstance(value, list):
            out[key] = list(value)
    return out


def mut(old, new, path=HAZ, count=1):
    def change(ctx):
        text = ctx["live"][path] if path != GAMETEST else ctx["gametest"]
        assert text.count(old) == count, ("mutation anchor", old[:80], text.count(old))
        if path == GAMETEST:
            ctx["gametest"] = text.replace(old, new)
        else:
            ctx["live"][path] = text.replace(old, new)
    return change


def mut_swap(a, b):
    def change(ctx):
        text = ctx["live"][HAZ]
        assert text.count(a) == 1 and text.count(b) == 1, ("swap anchors", a, b)
        ctx["live"][HAZ] = text.replace(a, "@@").replace(b, a).replace("@@", b)
    return change


def mut_set(key, value, sub=None):
    def change(ctx):
        if sub is None:
            ctx[key] = value
        else:
            ctx[key][sub] = value
    return change


FRAME_395 = "        frame().rad(at209).hot(20F).dust(POWDER_AT209); // :495\n"
DEBRIS_METAL_ROW = "        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));\n"
HES_ROW = "        HazardSystem.register(item(NUGGET_HES), makeData(RADIATION, saf * nugget)); // :323\n"
CALL = "        registerMaterials();\n"

MUTATIONS = [
    ("shape_multiplier_billet_0_6", mut("public static final float billet = 0.5F;", "public static final float billet = 0.6F;")),
    ("material_constant_u_0_36", mut("public static final float u = 0.35F;", "public static final float u = 0.36F;")),
    ("uzh_constant_changed", mut("public static final float uzh = 0.125F;", "public static final float uzh = 0.25F;")),
    ("pu238_hot_dropped", mut("frame().rad(pu238).hot(3F).nugget(NUGGET_PU238)", "frame().rad(pu238).nugget(NUGGET_PU238)")),
    ("items_swapped_between_frames", mut_swap(".nugget(NUGGET_PU239)", ".nugget(NUGGET_PU240)")),
    ("shape_dropped_u235_billet", mut(".billet(BILLET_U235)", "")),
    ("frame_row_dropped_at209", mut(FRAME_395.replace("395", "495"), "")),
    ("ore_block_added_to_frame", mut(".block(NtmBlocks.BLOCK_URANIUM)", ".block(NtmBlocks.BLOCK_URANIUM, NtmBlocks.ORE_URANIUM)")),
    ("ore_block_item_row_added", mut(CALL, "        HazardSystem.register(block(NtmBlocks.ORE_THORIUM), makeData(RADIATION, 1F));\n" + CALL)),
    ("out_of_scope_caesium_registered", mut(CALL, "        HazardSystem.register(item(POWDER_CAESIUM), makeData().addEntry(HYDROACTIVE, 1F).addEntry(HOT, 3F));\n" + CALL)),
    ("neo_only_co60_tiny_registered", mut(".dust(POWDER_CO60); // :366", ".dust(POWDER_CO60, POWDER_CO60_TINY); // :366")),
    ("neo_only_i131_ingot_registered", mut("frame().rad(i131).hot(1F).dustSmall(POWDER_I131_TINY)", "frame().rad(i131).hot(1F).ingot(INGOT_I131).dustSmall(POWDER_I131_TINY)")),
    ("duplicate_existing_registration", mut(DEBRIS_METAL_ROW, DEBRIS_METAL_ROW + DEBRIS_METAL_ROW)),
    ("duplicate_new_registration", mut(HES_ROW, HES_ROW + HES_ROW)),
    ("clone_hazMult_replaced_by_1F", mut("hazard.clone(hazMult)", "hazard.clone(1F)")),
    ("setMutex_dropped", mut(".setMutex(0b1)", "")),
    ("setMutex_wrong_bit", mut(".setMutex(0b1)", ".setMutex(0b10)")),
    ("preexisting_line_edited", mut("wst * rod_dual * 11.5F, false);", "wst * rod_dual * 11F, false);")),
    ("preexisting_line_deleted", mut("        HazardSystem.register(item(DEBRIS_ELEMENT), makeData(RADIATION, 100F));\n", "")),
    ("line_comment_wrong", mut("// :348\n", "// :358\n")),
    ("yellowcake_block_without_powder_mult", mut("makeData(RADIATION, yc * block * powder_mult)", "makeData(RADIATION, yc * block)")),
    ("fuel_row_wrong_constant", mut("makeData(RADIATION, uf * billet)); // :290", "makeData(RADIATION, puf * billet)); // :290")),
    ("blinding_factor_dropped", mut("addEntry(BLINDING, 5F * nugget)", "addEntry(BLINDING, 5F)")),
    ("entry_order_swapped_pb209", mut(".rad(pb209).blinding(50F).hot(7F)", ".rad(pb209).hot(7F).blinding(50F)")),
    ("blinding_value_changed", mut(".rad(sa327).blinding(50F)", ".rad(sa327).blinding(40F)")),
    ("hydro_value_changed", mut(".hydro(3F).dustSmall(POWDER_CS137_TINY)", ".hydro(1F).dustSmall(POWDER_CS137_TINY)")),
    ("nugget_shape_uses_powder", mut("Frame nugget(ItemLike... things) { return shape(HazardRegistry.nugget, things); }",
                                     "Frame nugget(ItemLike... things) { return shape(powder, things); }")),
    ("hydro_method_wrong_type", mut("Frame hydro(float h) { return haz(new HazardEntry(HYDROACTIVE, h)); }", "Frame hydro(float h) { return haz(new HazardEntry(HOT, h)); }")),
    ("registerMaterials_call_removed", mut(CALL, "")),
    ("ore_nether_id_registered", mut(".dust(POWDER_PLUTONIUM).block(NtmBlocks.BLOCK_PLUTONIUM); // :352", ".dust(POWDER_PLUTONIUM).block(NtmBlocks.BLOCK_PLUTONIUM, NtmBlocks.ORE_NETHER_PLUTONIUM); // :352")),
    ("raw_ingot_redstone_registered", mut("frame().hydro(1F).ingot(rawIngot(RawIngotItem.Type.SODIUM))", "frame().hydro(1F).ingot(rawIngot(RawIngotItem.Type.SODIUM), rawIngot(RawIngotItem.Type.REDSTONE))")),
    ("raw_ingot_sodium_meta_swapped_to_slag", mut("frame().hydro(1F).ingot(rawIngot(RawIngotItem.Type.SODIUM))", "frame().hydro(1F).ingot(rawIngot(RawIngotItem.Type.SLAG))")),
    ("raw_ingot_strontium_dropped", mut(".ingot(rawIngot(RawIngotItem.Type.STRONTIUM))", "")),
    ("raw_ingot_registered_on_item_map", mut("HazardSystem.register(stack, data(hazMult))", "HazardSystem.register(stack.getItem(), data(hazMult))")),
    ("crystal_registered", mut(CALL, "        HazardSystem.register(item(CRYSTAL_COAL), makeData(RADIATION, u * block));\n" + CALL)),
    ("strontium_nugget_dropped", mut(".dust(POWDER_STRONTIUM).nugget(NUGGET_STRONTIUM); // :490", ".dust(POWDER_STRONTIUM); // :490")),
    ("line_endings_flipped_to_lf", mut_set("eol", "LF", HAZ)),
    ("hazard_system_hash_changed", mut_set("hashes", "0" * 64, J + "hazard/HazardSystem.java")),
    ("hazard_type_hash_changed", mut_set("hashes", "0" * 64, J + "hazard/type/HazardTypeRadiation.java")),
    ("common_events_hash_changed", mut_set("hashes", "0" * 64, COMMON_EVENTS)),
    ("zh_map_hash_changed", mut_set("hashes", "0" * 64, "migration/localization/zh_cn-map.json")),
    ("other_src_file_changed", lambda ctx: ctx.__setitem__("scope_changed", ctx["scope_changed"] + [J + "items/NtmItems.java"])),
    ("original_blinding_shape_moved", lambda ctx: ctx["original"].__setitem__(O_ODM, ctx["original"][O_ODM].replace("hazMult = HazardRegistry.nugget;", "hazMult = HazardRegistry.billet;", 1))),
    ("original_row_moved", lambda ctx: ctx["original"].__setitem__(O_ODM, "\n" + ctx["original"][O_ODM])),
    ("original_constant_moved", lambda ctx: ctx["original"].__setitem__(O_HAZ, ctx["original"][O_HAZ].replace("uzh = 0.125F", "uzh = 0.25F", 1))),
]

DIFF_ONLY = {"preexisting_line_edited", "preexisting_line_deleted", "line_endings_flipped_to_lf"}


def mut_all(old, new, path):
    def change(ctx):
        text = ctx["gametest"]
        assert old in text, ("mutation anchor", old)
        ctx["gametest"] = text.replace(old, new, 1) if old != f'"{GAMETEST_BATCH}"' else text.replace(old, new)
    return change


def run_mutations(ctx, baseline_results):
    passing = {n for n, r in baseline_results.items() if r["status"] == "pass"}
    muts = list(MUTATIONS)
    if ctx["gametest"] is not None:
        muts += [("gametest_mock_player_added", mut_all("check(", "helper.makeMockPlayer(null); check(", GAMETEST)),
                 ("gametest_batch_wrong", mut_all(f'"{GAMETEST_BATCH}"', '"hazard_materials_x"', GAMETEST)),
                 ("gametest_reflection_added", mut_all("@GameTestHolder(", "import java.lang.reflect.Field;\n@GameTestHolder(", GAMETEST))]
    out = {}
    for label, change in muts:
        mutated = clone(ctx)
        change(mutated)
        results = run_checks(mutated)
        failed = sorted(n for n in passing if n in results and results[n]["status"] == "fail")
        kind = "diff" if label in DIFF_ONLY or label.startswith(("original_", "gametest_", "hazard_", "common_", "zh_", "other_")) else "code"
        semantic = [n for n in failed if n not in ("A4_insert_only", "A4_inserted_lines")]
        out[label] = dict(kind=kind, detected=bool(failed), semantic_detected=bool(semantic), failing_checks=failed,
                          first_message=results[failed[0]]["detail"][:300] if failed else None)
    return out


# ---------------------------------------------------------------- context

def build_context(reader, gametest_log, jar_path):
    ctx = {}
    ctx["live"] = {HAZ: reader.text(ROOT, HAZ, "neo")}
    ctx["start"] = {HAZ: reader.text(START, HAZ, "start")}
    raw = reader.bytes(ROOT, HAZ, "neo")
    start_raw = reader.bytes(START, HAZ, "start")
    ctx["eol"] = {HAZ: eol_kind(raw)}
    ctx["start_eol"] = {HAZ: eol_kind(start_raw)}
    ctx["bom"] = {HAZ: raw.startswith(b"\xef\xbb\xbf")}
    ctx["start_hash"] = sha(start_raw)
    ctx["original"] = {p: reader.text(ORIGINAL, p, "original") for p in (O_ODM, O_HAZ, O_MATS, O + "hazard/HazardEntry.java")}
    ctx["items_text"] = reader.text(ROOT, NTM_ITEMS, "neo")
    ctx["blocks_text"] = reader.text(ROOT, NTM_BLOCKS, "neo")
    ctx["raw_text"] = reader.text(ROOT, RAW_INGOT, "neo")
    ctx["gametest"] = reader.text(ROOT, GAMETEST, "neo") if (ROOT / GAMETEST).is_file() else None
    ctx["gametest_others"] = {str(p.relative_to(ROOT).as_posix()): reader.text(ROOT, p.relative_to(ROOT).as_posix(), "neo")
                              for p in sorted((ROOT / GAMETEST_DIR).glob("*.java")) if p.name != "HazardGameTests.java"}
    baseline = json.loads(reader.text(BATCH, "baseline.json", "batch"))
    ctx["baseline_files"] = baseline["files"]

    # whole-tree scope against the frozen hashes, and the hashes of the files the A4 checks compare
    hashes, scope = {}, []
    for path in sorted((ROOT / "src").rglob("*")):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            h = sha(path.read_bytes())
            hashes[rel] = h
            if baseline["files"].get(rel) != h:
                scope.append(rel)
    scope += [p for p in baseline["files"] if p.startswith("src/") and p not in hashes]
    ctx["scope_changed"] = sorted(set(scope))
    for p in LANGUAGE_FILES:
        if p not in hashes and (ROOT / p).is_file():
            hashes[p] = sha((ROOT / p).read_bytes())
    ctx["hashes"] = hashes
    ctx["gametest_log"] = str(gametest_log) if gametest_log else None
    ctx["jar"] = None
    if jar_path:
        with zipfile.ZipFile(jar_path) as z:
            ctx["jar"] = dict(names=set(z.namelist()))
        reader.hashes["jar:" + str(jar_path)] = sha(Path(jar_path).read_bytes())
    return ctx


def table_json(table):
    out = []
    for r in table:
        out.append(dict(original_line=r["orig_line"], source=r["source"], frame=r["frame"], shape=r["call"], original_name=r["original"], state=r["state"],
                        neo_id=r["neo_id"], neo_kind=r["neo_kind"], mutex=r["mutex"],
                        entries=[dict(type=t, value=fmt(v), float32_bits=f32_bits(v)) for t, v in r["entries"]], reason=r["reason"]))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write-record", action="store_true", help="also write migration/goal21d-hazard-review.json")
    parser.add_argument("--gametest-log", help="check a runGameTestServer log")
    parser.add_argument("--jar", help="check the packaged JAR")
    args = parser.parse_args()
    reader = Reader()
    ctx = build_context(reader, args.gametest_log, args.jar)
    results = {**git_checks(), **run_checks(ctx)}
    mutations = run_mutations(ctx, results)
    after = Reader()
    build_context(after, args.gametest_log, args.jar)
    results["inputs_stable_during_run"] = dict(status="pass" if after.hashes == reader.hashes else "fail",
                                               detail="every file read has the same SHA-256 after the run")

    counts = {s: sum(1 for r in results.values() if r["status"] == s) for s in ("pass", "fail", "pending")}
    detected = sum(1 for m in mutations.values() if m["detected"])
    final = bool(args.gametest_log and args.jar)
    semantic_missing = sorted(k for k, m in mutations.items() if m["kind"] == "code" and not m["semantic_detected"])
    ok = counts["fail"] == 0 and detected == len(mutations) and len(mutations) >= 13 and not semantic_missing and (not final or counts["pending"] == 0)
    table = ctx["table"] if "table" in ctx else []
    state_counts = {s: sum(1 for r in table if r["state"] == s) for s in STATES}
    rows_json = table_json(table)
    report = dict(tool="tools/migration/verify_goal21d_hazards.py", ok=ok, final=final,
                  code_mutations_without_semantic_catch=semantic_missing,
                  evidence="Static source, JSON, byte and float32 arithmetic checks over the live NEO tree, the frozen Goal21D start copy and the read-only "
                           "original; mutations are applied in memory only. No game, server or world: HazardRegistry's values are asserted on the real registry "
                           "and per tick on a Pig only by HazardGameTests (A7 checks that its log passed).",
                  original_head=ORIGINAL_HEAD, counts=counts, transcription_counts=state_counts, transcription_rows=len(table), checks=results,
                  transcription=rows_json, skips=[r for r in rows_json if r["state"] == ST_SKIP], mutations=mutations,
                  mutations_detected=f"{detected}/{len(mutations)}", files_read_sha256=reader.hashes)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.write_record:
        record = dict(goal="21D", date="2026-10-17", status="partial-unverified",
                      evidence_layer="static source review of the original 6a11998d and the NEO tree (this record is generated from tools/migration/verify_goal21d_hazards.py); "
                                     "registry values and the per-tick path on a Pig are asserted by the GameTests in HazardGameTests; carrying the materials as a player "
                                     "(HazardSystem.updatePlayerInventory) is existing NEO behaviour and is left to the unified in-game acceptance",
                      summary=dict(transcription_rows=len(table), states=state_counts, checks=counts, mutations_detected=f"{detected}/{len(mutations)}",
                                   verifier="tools/migration/verify_goal21d_hazards.py", report="build/migration/goal21d/verify/hazard-report.json",
                                   scope_decisions=["ore and oreNether shapes are never registered (Goal21 decision 13)", "SA326 plateCast: NEO has no cast plate",
                                                    "hazNugget()/hazIngot() only register ore keys, which reach the original's autogen nugget_raw/ingot_raw; "
                                                    "NEO's ingot_raw metas 1100 (sodium) and 3800 (strontium) stand for NA and SR hazIngot (review F1), "
                                                    "nugget_strontium for SR hazNugget; the Li and Na nuggets have no NEO item",
                                                    "NEO-only items powder_co60_tiny and ingot_i131 stay unregistered",
                                                    "crystals, powder_caesium, rad-source billets, RTG pellets, pile/RBMK/PWR/watz/plate fuels, P_WHITE and the ASBESTOS frame stay out of scope"]),
                      transcription=rows_json)
        RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, r in results.items():
        if r["status"] != "pass":
            print(f"{r['status'].upper()}: {name}: {r['detail'] if isinstance(r['detail'], str) else json.dumps(r['detail'])}")
    for label, m in mutations.items():
        if not m["detected"]:
            print(f"UNDETECTED MUTATION: {label}")
        elif m["kind"] == "code" and not m["semantic_detected"]:
            print(f"MUTATION CAUGHT ONLY BY AN EXACT DIFF: {label}")
    print(f"report: {REPORT}" + (f"; record: {RECORD}" if args.write_record else ""))
    print(f"Goal21D hazards: {counts['pass']} checks passed; transcription {len(table)} rows ({state_counts[ST_REG]} {ST_REG}, {state_counts[ST_SKIP]} {ST_SKIP}, "
          f"{state_counts[ST_ORE]} {ST_ORE}); {detected}/{len(mutations)} mutations detected"
          + (f"; {counts['pending']} pending" if counts["pending"] else "") + (f"; {counts['fail']} FAILED" if counts["fail"] else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
