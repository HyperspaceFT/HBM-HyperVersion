"""Verify Goal22D (material hazard registration addendum: HazardRegistry.java:331-335, :478, :485-492 and OreDictManager.java:424, :460 in NEO
HazardRegistry.registerMaterialAddendum), statically. Derived from verify_goal21d_hazards.py.

Read-only for both worktrees. Writes only build/migration/goal22d/verify/report.json. No game, Gradle or network.

- O  The read-only original (HEAD 6a11998d): constants, the D1 rows, DictFrame, and every register / registerRTGPellet / registerPWRFuel statement
     of HazardRegistry.java:329-362, :457-471 and :470-500 plus every hazard DictFrame row of OreDictManager.java:420-462, each classified as exactly one of
     registered (this batch) / registered-before-unchanged / NEO-missing-skip / RTG-deferred / other-system-deferred / ore-not-registered.
- N  The NEO HazardRegistry.registerMaterialAddendum and Frame.asbestos parsed statically and evaluated in float32 against the expected table.
- E  Pre-existing entries unchanged: insert-only diff against the frozen start (plus the one Frame javadoc line), no duplicate registration, no ore.
- S  Scope: src/ equals baseline.json except HazardRegistry.java, HazardGameTests.java and the generation stamp; language files, hazard system, types,
     modifiers, NtmItems and NtmBlocks unchanged.
- K  The skipped list, printed and stored.
- T  The GameTest source: expected method names, the addendum table and the 20-row sample transcribed from the same sources.
- L  Optional --gametest-log PATH.   J  Optional --jar PATH.
- M  In-memory mutations of the inputs; each must make at least one check fail.

python -B -X utf8 tools/migration/verify_goal22d_hazards.py [--gametest-log PATH] [--jar PATH]
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
BATCH = ROOT / "build/migration/goal22d"
START = BATCH / "baseline-files"
REPORT = BATCH / "verify/report.json"
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
HAZARD_FILES = [J + "hazard/HazardSystem.java", J + "hazard/HazardData.java", J + "hazard/HazardEntry.java", COMMON_EVENTS, NTM_ITEMS, NTM_BLOCKS]
HAZARD_DIRS = [J + "hazard/type/", J + "hazard/modifier/", J + "hazard/transformer/"]
LANGUAGE_FILES = ["src/main/resources/assets/hbmsntm/lang/zh_cn.json", "migration/localization/zh_cn-map.json",
                  "src/generated/resources/assets/hbmsntm/lang/en_us.json", J + "datagen/NtmLanguageProvider.java"]

O = "src/main/java/com/hbm/"
O_ODM = O + "inventory/OreDictManager.java"
O_HAZ = O + "hazard/HazardRegistry.java"
O_ENTRY = O + "hazard/HazardEntry.java"

GAMETEST_BATCH = "hazard_materials"
OLD_TESTS = ["hazard_material_registrations", "hazard_raw_ingot_stacks", "hazard_existing_unchanged", "hazard_none_for_ores_and_unlisted",
             "hazard_living_radiation_and_fire", "hazard_living_blinding", "hazard_event_entry_applies_once"]
NEW_TESTS = ["hazard_addendum_registrations", "hazard_existing_sample_unchanged", "hazard_living_crystal_schrabidium",
             "hazard_living_addendum_fire_and_asbestos"]

ST_REG = "registered (this batch)"
ST_BEFORE = "registered-before-unchanged"
ST_SKIP = "NEO-missing-skip"
ST_RTG = "RTG-deferred"
ST_OTHER = "other-system-deferred"
ST_ORE = "ore-not-registered"
STATES = (ST_REG, ST_BEFORE, ST_SKIP, ST_RTG, ST_OTHER, ST_ORE)

TYPE_NAMES = ("RADIATION", "DIGAMMA", "HOT", "BLINDING", "ASBESTOS", "COAL", "HYDROACTIVE", "EXPLOSIVE")
HAZ_CALLS = {"rad": "RADIATION", "hot": "HOT", "blinding": "BLINDING", "hydro": "HYDROACTIVE", "asbestos": "ASBESTOS"}
SHAPE_CONST = {"nugget": "nugget", "billet": "billet", "ingot": "ingot", "dustSmall": "powder_tiny", "dust": "powder", "plate": "plate",
               "plateCast": "plateCast", "block": "block", "ore": "ore", "oreNether": "ore"}

D1_ITEM_LINES = [331, 332, 333, 334, 335, 478] + list(range(485, 493))
D1_FRAME_LINES = [424, 460]
RANGES = [(329, 362), (457, 471), (470, 500)]
ODM_RANGE = (420, 462)
ORIGINAL_ALIAS = {"ModItems.fallout": "fallout_pile", "ModBlocks.fallout": "fallout", "boy_propellant": "little_boy_propellant",
                  "boy_target": "little_boy_target", "boy_bullet": "little_boy_bullet", "man_core": "fat_man_core"}
SPOT_ACCEPTANCE = {("crystal_uranium", "RADIATION"): 3.5, ("crystal_plutonium", "RADIATION"): 75.0, ("crystal_schrabidium", "RADIATION"): 150.0,
                   ("crystal_trixite", "RADIATION"): 250.0, ("billet_flashlead", "HOT"): 7.0, ("powder_caesium", "HYDROACTIVE"): 1.0,
                   ("powder_caesium", "HOT"): 3.0, ("ingot_asbestos", "ASBESTOS"): 1.0, ("powder_asbestos", "ASBESTOS"): 3.0,
                   ("block_asbestos", "ASBESTOS"): 10.0, ("ingot_phosphorus", "HOT"): 5.0}
DIFF_ONLY_CHECKS = ("E1_insert_only", "E2_inserted_lines")


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


def same_entries(a, b):
    return [(t, f32_bits(v)) for t, v in a] == [(t, f32_bits(v)) for t, v in b]


def entries_repr(entries):
    return [(t, f32_repr(v)) for t, v in entries]


# ---------------------------------------------------------------- O: the original

def parse_original(ctx):
    odm = ctx["original"][O_ODM].split("\n")
    haz_text = ctx["original"][O_HAZ]
    haz = haz_text.split("\n")
    consts = float_consts(haz_text)
    model = dict(consts=consts)

    # the D1 item-level rows
    items = []
    for number in D1_ITEM_LINES:
        m = re.match(r"\s*HazardSystem\.register\((?:ModItems\.|ModBlocks\.)?(\w+), (makeData.*)\);\s*$", haz[number - 1])
        assert m, f"HazardRegistry line {number} is not an item-level row: {haz[number - 1].strip()[:100]!r}"
        items.append(dict(line=number, name=m.group(1), entries=parse_makedata(m.group(2))))
    model["item_rows"] = items

    # the D1 frame rows
    frames = []
    for number, frame in zip(D1_FRAME_LINES, ("ASBESTOS", "P_WHITE")):
        m = re.match(r"\s*(\w+)\s+(\..*?);", odm[number - 1])
        assert m and m.group(1) == frame, f"OreDictManager line {number} is not the {frame} row: {odm[number - 1].strip()[:100]!r}"
        frames.append(dict(line=number, frame=frame, calls=parse_chain(m.group(2))))
    model["frame_rows"] = frames

    # DictFrame shape multipliers and hazard methods
    frame_text = "\n".join(odm[735:962])
    shapes = {}
    for m in re.finditer(r"public DictFrame (\w+)\(Object\.\.\. \w+\) \{\s*hazMult = HazardRegistry\.(\w+);\s*return makeObject\((\w+)", frame_text):
        shapes[m.group(1)] = m.group(2)
    model["shape_const"] = shapes
    model["haz_methods"] = dict(re.findall(r"public DictFrame (\w+)\(float \w+\) \{\s*return this\.haz\(new HazardEntry\(HazardRegistry\.(\w+), \w+\)\);", frame_text))
    model["auto"] = dict((m.group(1), (m.group(2), m.group(3))) for m in re.finditer(
        r"public DictFrame (haz\w+)\(\) \{\s*hazMult = HazardRegistry\.(\w+);\s*return autoRegHazard\((\w+)\);", frame_text))

    # every statement of the three ranges
    statements = []
    numbers = sorted({n for lo, hi in RANGES for n in range(lo, hi + 1)})
    for number in numbers:
        m = re.match(r"\s*(HazardSystem\.register|registerRTGPellet|registerPWRFuel)\((.*)\);\s*$", haz[number - 1])
        if m:
            args = split_args(m.group(2))
            statements.append(dict(line=number, call=m.group(1), first=args[0], rest=",".join(args[1:]), text=haz[number - 1].strip()))
        else:
            assert not haz[number - 1].strip() or haz[number - 1].strip().startswith(("//", "/*", "*")), \
                f"HazardRegistry line {number} is neither a hazard statement nor blank/comment: {haz[number - 1].strip()[:100]!r}"
    model["statements"] = statements

    # every hazard DictFrame row of OreDictManager.java:420-462
    odm_rows = []
    for number in range(ODM_RANGE[0], ODM_RANGE[1] + 1):
        line = odm[number - 1]
        m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s+(\..*?);", line)
        if m and re.search(r"\.(rad|hot|hydro|asbestos|blinding|digamma)\(", line):
            odm_rows.append(dict(line=number, frame=m.group(1), calls=parse_chain(m.group(2))))
    model["odm_rows"] = odm_rows
    return model


def c_o_rows(ctx):
    model = ctx["model"]
    assert [r["line"] for r in model["item_rows"]] == D1_ITEM_LINES and len(D1_ITEM_LINES) == 14, "item-level rows"
    haz = ctx["original"][O_HAZ].split("\n")
    need(haz, 332, "billet_flashlead", "pb209 * 1.25F * billet", "addEntry(HOT, 7F)")
    need(haz, 333, "billet_po210be", "pobe * billet")
    need(haz, 478, "powder_caesium", "addEntry(HYDROACTIVE, 1F)", "addEntry(HOT, 3F)")
    need(haz, 490, "crystal_phosphorus", "makeData(HOT, 2F * crystal)")
    need(haz, 491, "crystal_lithium", "makeData(HYDROACTIVE, 1F * crystal)")
    need(haz, 492, "ModItems.crystal_trixite", "trx * crystal")
    need(haz, 476, "ModBlocks.fallout", "fo * powder * 2")
    need(haz, 477, "ModBlocks.block_fallout")
    need(haz, 481, "tile_lab_broken")
    odm = ctx["original"][O_ODM].split("\n")
    need(odm, 424, "ASBESTOS", ".asbestos(1F)", ".ingot(ingot_asbestos)", ".dust(powder_asbestos)", ".block(block_asbestos)", ".ore(ore_asbestos, ore_gneiss_asbestos")
    need(odm, 460, "P_WHITE", ".hot(5)", ".ingot(ingot_phosphorus)", ".block(block_white_phosphorus)")
    assert [r["line"] for r in model["odm_rows"] if r["line"] >= 420] == [424, 454, 455, 460], \
        f"hazard DictFrame rows in OreDictManager.java:420-462: {[r['line'] for r in model['odm_rows']]}"
    return "14 item-level rows at HazardRegistry.java " + ",".join(map(str, D1_ITEM_LINES)) + "; frame rows OreDictManager.java:424 (ASBESTOS) and :460 (P_WHITE); the only hazard DictFrame rows of :420-462 are :424, :454, :455, :460"


def c_o_dictframe(ctx):
    model = ctx["model"]
    expected = {"nugget": "nugget", "billet": "billet", "ingot": "ingot", "dustSmall": "powder_tiny", "dust": "powder", "plate": "plate",
                "plateCast": "plateCast", "block": "block", "ore": "ore", "oreNether": "ore", "gem": "gem", "crystal": "gem"}
    assert model["shape_const"] == expected, f"DictFrame shape multipliers {model['shape_const']}"
    assert model["haz_methods"] == {"rad": "RADIATION", "hot": "HOT", "blinding": "BLINDING", "asbestos": "ASBESTOS", "hydro": "HYDROACTIVE"}, "DictFrame hazard methods"
    odm = ctx["original"][O_ODM].split("\n")
    need(odm, 794, "asbestos(float asb)", "HazardRegistry.ASBESTOS")
    text = flat("\n".join(odm[837:962]))
    assert "if(!hazards.isEmpty() && hazMult > 0F) { HazardData data = new HazardData().setMutex(0b1); for(HazardEntry hazard : hazards) { data.addEntry(hazard.clone(hazMult)); } HazardSystem.register(dictKey, data); }" in text, \
        "registerHazards (:933-944): setMutex(0b1) and clone(hazMult) on every entry"
    clone = ctx["original"][O_ENTRY]
    assert "new HazardEntry(type, baseLevel * mult)" in clone and "clone.mods = this.mods" in clone, "HazardEntry.clone multiplies the base level"
    return "hazard methods :791-795 (asbestos at :794); shapes :838-886 -> ingot 1, dust 3, block 10, ore 1; registerHazards :933-944 setMutex(0b1) + clone(hazMult) per entry"


def c_o_constants(ctx):
    c = ctx["model"]["consts"]
    given = dict(au198=500.0, pb209=10000.0, po210=75.0, ra226=7.5, pu238=30 / 3, radsource_mult=3.0, u=0.35, th232=0.1, pu=7.5, sa326=15.0,
                 trx=25.0, crystal=10.0, block=10.0, billet=0.5, ingot=1.0, powder=3.0, powder_mult=3.0, fo=10.0, yc=0.35)
    for name, value in given.items():
        assert c[name] == f32(value), f"original constant {name} = {c[name]}, expected {value}"
    assert c["pobe"] == f32(c["po210"] * c["radsource_mult"]) == 225.0 and c["rabe"] == 22.5 and c["pube"] == 30.0, "pobe/rabe/pube"
    assert c["sr"] == f32(c["sa326"] * f32(0.1)), "sr = sa326 * 0.1F"
    return "original float32 constants: crystal = block = 10, pobe/rabe/pube = material * radsource_mult (225/22.5/30), sr = sa326 * 0.1F, trx 25, billet .5, powder 3"


# ---------------------------------------------------------------- expected table (from the original alone) and the NEO ids

def neo_id_maps(items_text, blocks_text, raw_text):
    def table(text, cls):
        pat = rf"public static final Deferred{cls}<[^>]*>\s+(\w+)\s*=\s*(?:\w+\.)?\w+\(\s*\"([^\"]+)\""
        return {const: ident for const, ident in re.findall(pat, strip_keep(text))}
    item_c, block_c = table(items_text, "Item"), table(blocks_text, "Block")
    raw = {name: int(meta) for name, meta in re.findall(r"\b([A-Z]\w+)\((\d+), \"hbmmat\.", raw_text)}
    return dict(item_c=item_c, block_c=block_c, item_ids={i: c for c, i in item_c.items()}, block_ids={i: c for c, i in block_c.items()}, raw_metas=raw)


def identity(name, shape, neo):
    if not re.fullmatch(r"\w+", name):
        return None
    order = ("block", "item") if shape == "block" else ("item", "block")
    for kind in order:
        if name in neo[kind + "_ids"]:
            return kind, name
    return None


def build_table(ctx):
    """Every D1 row/shape as one table row; entries are float32 values in the original's order."""
    model, neo = ctx["model"], ctx["neo_ids"]
    consts = model["consts"]
    rows = []
    for row in model["item_rows"]:
        entries = [(t, eval_float(e, consts)) for t, e in row["entries"]]
        shape = "block" if row["name"].startswith("block_") else "item"
        ident = identity(row["name"], shape, neo)
        base = dict(orig_line=row["line"], source="HazardRegistry.registerItems", frame=None, call="register", original=row["name"], mutex=0,
                    entries=entries, neo_id=None, neo_kind=None, reason=None)
        if ident:
            base.update(state=ST_REG, neo_id=ident[1], neo_kind=ident[0])
        else:
            base.update(state=ST_SKIP, reason=f"NEO has no item or block {row['name']}")
        rows.append(base)
    for row in model["frame_rows"]:
        hazards, mult = [], None
        for call, args in row["calls"]:
            if call in HAZ_CALLS:
                assert len(args) == 1
                hazards.append((HAZ_CALLS[call], eval_float(args[0], consts)))
                continue
            assert call in SHAPE_CONST, f"unknown DictFrame call {call} in OreDictManager:{row['line']}"
            mult = consts[SHAPE_CONST[call]]
            entries = [(t, f32(v * mult)) for t, v in hazards]
            for arg in args:
                base = dict(orig_line=row["line"], source="OreDictManager.DictFrame", frame=row["frame"], call=call, original=arg, mutex=0b1,
                            entries=entries, neo_id=None, neo_kind=None, reason=None)
                if call in ("ore", "oreNether"):
                    base.update(state=ST_ORE, reason="Goal21 decision 13: ore shapes are never registered")
                else:
                    ident = identity(arg, call, neo)
                    if ident:
                        base.update(state=ST_REG, neo_id=ident[1], neo_kind=ident[0])
                    else:
                        base.update(state=ST_SKIP, reason=f"NEO has no item or block {arg}")
                rows.append(base)
    return rows


def c_o_table(ctx):
    table = ctx["table"]
    assert all(r["state"] in (ST_REG, ST_SKIP, ST_ORE) for r in table), "a D1 row has an unexpected state"
    registered = [r for r in table if r["state"] == ST_REG]
    ids = [r["neo_id"] for r in registered]
    assert len(ids) == len(set(ids)), "NEO ids that two rows register: " + str(sorted({i for i in ids if ids.count(i) > 1}))
    assert len(registered) == 18, f"{len(registered)} registered D1 rows, expected 18"
    for r in registered:
        assert r["entries"] and all(v > 0 for _, v in r["entries"]), f"{r['neo_id']}: no entries"
    skipped = sorted(r["original"] for r in table if r["state"] == ST_SKIP)
    assert skipped == ["block_white_phosphorus"], f"skipped D1 rows {skipped}"
    ores = [r for r in table if r["state"] == ST_ORE]
    assert len(ores) == 4 and all(r["orig_line"] == 424 for r in ores), "the four ASBESTOS ore arguments"
    by_name = {r["neo_id"]: r for r in registered}
    spot = {(i, t): dict(r["entries"])[t] for i, r in by_name.items() for t, _ in r["entries"]}
    for key, value in SPOT_ACCEPTANCE.items():
        assert key in spot, f"acceptance row {key} is not in the expected table"
        assert abs(spot[key] - value) <= 1e-6 * value, f"{key}: expected table {f32_repr(spot[key])}, acceptance list {value}"
    counts = {s: sum(1 for r in table if r["state"] == s) for s in (ST_REG, ST_SKIP, ST_ORE)}
    return f"{len(table)} D1 rows: {counts[ST_REG]} {ST_REG} (14 item-level + 4 frame), {counts[ST_SKIP]} {ST_SKIP} (block_white_phosphorus), {counts[ST_ORE]} {ST_ORE}; every registered id unique; acceptance values equal"


def classify_original(ctx):
    """Every register / registerRTGPellet / registerPWRFuel statement of the three ranges and every hazard DictFrame element in one of six states."""
    model, neo, start_regs = ctx["model"], ctx["neo_ids"], ctx["start_regs"]
    consts = model["consts"]
    live_new = {r["neo_id"] for r in ctx["table"] if r["state"] == ST_REG}
    out = []
    for st in model["statements"]:
        line, call, first, text = st["line"], st["call"], st["first"], st["text"]
        entry = dict(source="HazardRegistry.java", line=line, element=first if call == "HazardSystem.register" else f"{call}({first})", text=text[:140], neo_id=None, entries=None, category=None, detail=None)
        if call == "registerRTGPellet" or "pellet_rtg" in first:
            entry.update(category=ST_RTG, detail="needs HazardModifierRTGRadiation, which NEO does not have")
        elif call == "registerPWRFuel" or "pile_rod" in first:
            entry.update(category=ST_OTHER, detail="NEO has neither the pile rod / PWR fuel items nor their systems")
        else:
            name = first
            neo_name = ORIGINAL_ALIAS.get(name, name.split(".")[-1])
            shape = "block" if neo_name.startswith("block_") or name == "ModBlocks.fallout" else "item"
            ident = identity(neo_name, shape, neo)
            expected = [(t, eval_float(e, consts)) for t, e in parse_makedata(st["rest"])]
            entry.update(entries=expected)
            if line in D1_ITEM_LINES:
                assert ident and ident[1] in live_new, f"line {line} {name}: not in the expected registered set"
                entry.update(category=ST_REG, neo_id=ident[1], detail="registered by registerMaterialAddendum")
            elif ident is None:
                entry.update(category=ST_SKIP, detail=f"NEO has no item or block {neo_name}")
            elif ident[1] in start_regs:
                entry.update(category=ST_BEFORE, neo_id=ident[1], detail="registered before this batch; entries compared in E3")
            else:
                entry.update(category="UNCLASSIFIED", neo_id=ident[1], detail=f"NEO has {neo_name} but the start copy does not register it")
        out.append(entry)
    for row in model["odm_rows"]:
        line = row["line"]
        for call, args in row["calls"]:
            if call in HAZ_CALLS:
                continue
            if call in ("hazNugget", "hazIngot"):
                mat = {454: "lithium", 455: "sodium"}[line]
                targets = [f"nugget_{mat}"] if call == "hazNugget" else ["ingot_raw#" + str(neo["raw_metas"].get("SODIUM", "?"))]
            else:
                targets = args
            for arg in targets:
                entry = dict(source="OreDictManager.java", line=line, element=f"{row['frame']}.{call}({arg})", text=f"{row['frame']}.{call}", neo_id=None, entries=None, category=None, detail=None)
                if call in ("ore", "oreNether"):
                    entry.update(category=ST_ORE, detail="ore shapes are never registered (Goal21 decision 13)")
                elif arg.startswith("ingot_raw#"):
                    entry.update(category=ST_BEFORE if arg in start_regs else "UNCLASSIFIED", neo_id=arg, detail="NEO's ingot_raw meta registered as a stack in 21D")
                else:
                    ident = identity(arg, "block" if call == "block" else "item", neo)
                    if line in D1_FRAME_LINES:
                        if ident:
                            assert ident[1] in live_new, f"OreDictManager:{line} {arg}: not in the expected registered set"
                            entry.update(category=ST_REG, neo_id=ident[1], detail="registered by registerMaterialAddendum")
                        else:
                            entry.update(category=ST_SKIP, detail=f"NEO has no item or block {arg}")
                    elif ident is None:
                        entry.update(category=ST_SKIP, detail=f"NEO has no item or block {arg}")
                    elif ident[1] in start_regs:
                        entry.update(category=ST_BEFORE, neo_id=ident[1], detail="registered by the 21D frame")
                    else:
                        entry.update(category="UNCLASSIFIED", neo_id=ident[1], detail="not registered in the start copy")
                out.append(entry)
    return out


def c_o_classification(ctx):
    cls = ctx["classification"]
    bad = [e for e in cls if e["category"] not in STATES]
    assert not bad, "unclassified original lines: " + str([(e["source"], e["line"], e["element"], e["detail"]) for e in bad[:6]])
    counts = {s: sum(1 for e in cls if e["category"] == s) for s in STATES}
    rtg = sorted(e["line"] for e in cls if e["category"] == ST_RTG)
    assert rtg == list(range(337, 348)), f"RTG-deferred lines {rtg}"
    neo = ctx["neo_ids"]
    # the deferred systems really are absent from NEO
    assert [i for i in neo["item_ids"] if i.startswith("pellet_rtg")] == ["pellet_rtg"], "NEO pellet_rtg items " + str([i for i in neo["item_ids"] if i.startswith("pellet_rtg")])
    assert not [i for i in neo["item_ids"] if re.match(r"(pile_rod|pwr_fuel)", i)] and not [i for i in neo["block_ids"] if re.match(r"(pile_rod|pwr_fuel)", i)], "NEO has pile rod / PWR fuel items"
    src = ctx["src_names"]
    systems = [n for n in src if re.search(r"PileRod|PWRFuel|EnumPWR|HazardModifierRTG", n)]
    assert not systems, "NEO has pile rod / PWR / RTG-modifier classes: " + str(systems[:5])
    assert "block_fallout" not in neo["block_ids"] and "block_fallout" not in neo["item_ids"] and "tile_lab_broken" not in neo["block_ids"] and \
        "block_white_phosphorus" not in neo["block_ids"] and "block_white_phosphorus" not in neo["item_ids"], "a NEO-missing block exists after all"
    return f"{len(cls)} elements classified, none unclassified: " + ", ".join(f"{s} {counts[s]}" for s in STATES)


def c_o_before_values(ctx):
    """The original value of every registered-before-unchanged item-level row equals NEO's live entry (fallout 60, brick_asbestos 1, coltan 3, ...)."""
    nm = ctx["nm"]
    checked = []
    for e in ctx["classification"]:
        if e["category"] != ST_BEFORE or e["source"] != "HazardRegistry.java":
            continue
        row = nm["regs"].get(e["neo_id"])
        assert row, f"{e['neo_id']} (:{e['line']}) is not registered in NEO"
        assert same_entries(row["entries"], e["entries"]), f"{e['neo_id']} (:{e['line']}): NEO {entries_repr(row['entries'])} != original {entries_repr(e['entries'])}"
        checked.append(f":{e['line']} {e['neo_id']}")
    assert len(checked) >= 10, "too few registered-before rows compared"
    fallout = nm["regs"]["fallout"]["entries"]
    assert fallout == [("RADIATION", 60.0)], f"NEO fallout block {fallout}"
    return f"{len(checked)} registered-before-unchanged item-level rows equal the original value in float32 (fallout block 60 = fo * powder * 2): " + ", ".join(checked)


# ---------------------------------------------------------------- NEO model

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


def resolve_arg(arg, neo):
    m = re.fullmatch(r"rawIngot\(RawIngotItem\.Type\.(\w+)\)", arg.strip())
    if m:
        assert neo["item_c"].get("INGOT_RAW") == "ingot_raw", "INGOT_RAW is not ingot_raw"
        return "stack", f"ingot_raw#{neo['raw_metas'][m.group(1)]}"
    return resolve_target(arg, neo)


def neo_frame_class(code):
    start, end = block_span(code, "private static class Frame")
    body = flat(code[start:end + 1])
    haz = dict(re.findall(r"Frame (\w+)\(float \w+\) \{ return haz\(new HazardEntry\((\w+), \w+\)\); \}", body))
    shapes = {name: const.replace("HazardRegistry.", "") for name, const in re.findall(r"Frame (\w+)\(ItemLike\.\.\. things\) \{ return shape\(([\w.]+), things\); \}", body)}
    stack_shapes = {name: const.replace("HazardRegistry.", "") for name, const in re.findall(r"Frame (\w+)\(ItemStack\.\.\. stacks\) \{ return shape\(([\w.]+), stacks\); \}", body)}
    return dict(span=(line_of(code, start), line_of(code, end)), body=body, haz=haz, shapes=shapes, stack_shapes=stack_shapes)


def parse_region(code, raw, first, last, neo, consts, frame, strict):
    """The statements between two lines of a method body: frame chains, item-level rows and helper calls."""
    codelines = code.split("\n")
    frame_lines, rows, keys, issues = [], {}, [], []
    for number in range(first + 1, last):
        c = codelines[number - 1].strip()
        if not c:
            continue
        comment = re.search(r"//\s*(?:OreDictManager\.java)?:(\d+)", raw[number - 1])
        comment = int(comment.group(1)) if comment else None
        if c.startswith("frame()"):
            m = re.fullmatch(r"frame\(\)((?:\.\w+\(.*?\))+);", c)
            if not m:
                issues.append(f"line {number} is not a frame chain: {c[:80]!r}")
                continue
            regs, hazards = [], []
            for call, args in parse_chain(m.group(1)):
                if call in frame["haz"]:
                    hazards.append((frame["haz"][call], eval_float(args[0], consts)))
                elif call in frame["shapes"]:
                    mult = consts[frame["shapes"][call]]
                    for a in args:
                        kind, ident = resolve_arg(a, neo)
                        if kind == "stack":
                            if not (call in frame["stack_shapes"] and frame["stack_shapes"][call] == frame["shapes"][call]):
                                issues.append(f"line {number}: no ItemStack overload of {call} with the same multiplier")
                        regs.append(dict(id=ident, kind=kind, call=call, line=number, entries=[(t, f32(v * mult)) for t, v in hazards], mutex=0b1))
                else:
                    issues.append(f"line {number}: unknown frame call {call}")
            frame_lines.append(dict(line=number, comment=comment, regs=regs))
            for reg in regs:
                keys.append((reg["id"], number))
            continue
        if c.startswith("HazardSystem.register("):
            open_index = c.index("(")
            close = matching_paren(c, open_index)
            args = split_args(c[open_index + 1:close])
            target = args[0]
            m = re.fullmatch(r"(item|block)\(([\w.]+)\)", target)
            if m:
                kind, ident = resolve_target(m.group(2), neo)
                declared = m.group(1)
            elif re.fullmatch(r"(Items|Blocks)\.\w+", target):
                kind, ident, declared = "vanilla", "minecraft:" + target.split(".")[1].lower(), "vanilla"
            elif re.fullmatch(r"Ntm(Items|Blocks)\.\w+\.get\(\)", target):
                kind, ident = resolve_target(target, neo)
                declared = "get"
            else:
                keys.append((flat(target), number))
                continue
            keys.append((ident, number))
            entries = [(t, eval_float(e, consts)) for t, e in parse_makedata(",".join(args[1:]))]
            rows[ident] = dict(id=ident, line=number, kind=kind, declared=declared, entries=entries, comment=comment, mutex=0)
            continue
        m = re.match(r"(registerBreedingRodRadiation|registerOtherFuel|registerOtherWaste|registerMaterials|registerMaterialAddendum)\((.*)\);", c)
        if m:
            args = split_args(m.group(2))
            keys.append((m.group(1) + ":" + ",".join(args[:2] if m.group(1) == "registerOtherFuel" else args[:1]), number))
        elif strict:
            issues.append(f"line {number}: unexpected statement {c[:80]!r}")
    return dict(frame_lines=frame_lines, rows=rows, keys=keys, issues=issues, span=(first, last))


def neo_model(text, neo, with_addendum):
    code = strip_keep(text)
    raw = text.split("\n")
    consts = float_consts(text)
    frame = neo_frame_class(code)
    spans = {}
    for name, sig in (("items", "public static void registerItems()"), ("materials", "private static void registerMaterials()"),
                      ("addendum", "private static void registerMaterialAddendum()")):
        if name == "addendum" and not with_addendum and "registerMaterialAddendum" not in code:
            continue
        start, end = block_span(code, sig)
        spans[name] = (line_of(code, start), line_of(code, end))
    regions = {name: parse_region(code, raw, lo, hi, neo, consts, frame, strict=(name != "items")) for name, (lo, hi) in spans.items()}
    regs, keys, issues = {}, [], []
    for name, region in regions.items():
        issues += [f"{name}: {i}" for i in region["issues"]]
        keys += region["keys"]
        for ident, row in region["rows"].items():
            regs[ident] = dict(row, region=name)
        for fl in region["frame_lines"]:
            for reg in fl["regs"]:
                regs[reg["id"]] = dict(reg, region=name, comment=fl["comment"], declared="frame")
    return dict(consts=consts, frame=frame, regions=regions, regs=regs, keys=keys, issues=issues, spans=spans)


def c_n_addendum_rows(ctx):
    nm, table = ctx["nm"], ctx["table"]
    assert not nm["issues"], "; ".join(nm["issues"])
    assert "addendum" in nm["regions"], "registerMaterialAddendum() is missing"
    region = nm["regions"]["addendum"]
    expected_items = [r for r in table if r["state"] == ST_REG and r["source"].startswith("HazardRegistry")]
    assert sorted(region["rows"]) == sorted(r["neo_id"] for r in expected_items), \
        f"item-level rows of registerMaterialAddendum: extra {sorted(set(region['rows']) - {r['neo_id'] for r in expected_items})}, missing {sorted({r['neo_id'] for r in expected_items} - set(region['rows']))}"
    order = [row["id"] for row in sorted(region["rows"].values(), key=lambda r: r["line"])]
    assert order == [r["neo_id"] for r in expected_items], f"item-level row order {order}"
    for want in expected_items:
        row = region["rows"][want["neo_id"]]
        assert row["declared"] == "item" and row["kind"] == "item", f"{want['neo_id']}: registered through {row['declared']}()"
        assert row["mutex"] == 0, f"{want['neo_id']} has a mutex"
        assert same_entries(row["entries"], want["entries"]), f"{want['neo_id']}: entries {entries_repr(row['entries'])} != original {entries_repr(want['entries'])}"
        assert row["comment"] == want["orig_line"], f"{want['neo_id']}: line comment :{row['comment']}, original line {want['orig_line']}"
    expected_frames = [r for r in table if r["state"] == ST_REG and r["source"].startswith("OreDictManager")]
    got = [(fl["comment"], reg["id"], reg["kind"], reg["entries"]) for fl in region["frame_lines"] for reg in fl["regs"]]
    want = [(r["orig_line"], r["neo_id"], r["neo_kind"], r["entries"]) for r in expected_frames]
    assert [(a, b, c) for a, b, c, _ in got] == [(a, b, c) for a, b, c, _ in want], f"frame registrations {[(a, b) for a, b, _, _ in got]} != {[(a, b) for a, b, _, _ in want]}"
    for (line, ident, _, entries), (_, _, _, wentries) in zip(got, want):
        assert same_entries(entries, wentries), f"OreDictManager:{line} {ident}: entries {entries_repr(entries)} != original {entries_repr(wentries)}"
    assert [fl["comment"] for fl in region["frame_lines"]] == [424, 460], "frame line comments must cite OreDictManager.java:424 and :460"
    return f"{len(expected_items)} item-level rows (ids, item() kind, ordered float32 entries, no mutex, `// :NNN` = original line) and {len(got)} frame registrations (OreDictManager.java:424 ingot/dust/block, :460 ingot) equal the expected table"


def c_n_frame_class(ctx):
    f = ctx["nm"]["frame"]
    assert f["haz"] == {"rad": "RADIATION", "hot": "HOT", "blinding": "BLINDING", "hydro": "HYDROACTIVE", "asbestos": "ASBESTOS"}, f"Frame hazard methods {f['haz']}"
    assert f["shapes"] == {"nugget": "nugget", "billet": "billet", "ingot": "ingot", "dustSmall": "powder_tiny", "dust": "powder", "plate": "plate", "block": "block"}, f"Frame shapes {f['shapes']}"
    body = f["body"]
    assert "Frame asbestos(float asb) { return haz(new HazardEntry(ASBESTOS, asb)); }" in body, "Frame.asbestos"
    assert "private Frame haz(HazardEntry hazard) { hazards.add(hazard); return this; }" in body, "Frame.haz adds in call order"
    assert "private HazardData data(float hazMult) { HazardData data = new HazardData().setMutex(0b1); for(HazardEntry hazard : hazards) data.addEntry(hazard.clone(hazMult)); return data; }" in body, \
        "Frame.data must build `new HazardData().setMutex(0b1)` with every entry cloned by hazMult"
    assert "for(ItemLike thing : things) HazardSystem.register(thing.asItem(), data(hazMult))" in body, "Frame.shape registers on thing.asItem()"
    code = strip_keep(ctx["live"][HAZ])
    assert flat(code).count("registerMaterialAddendum();") == 1 and flat(code).count("private static void registerMaterialAddendum()") == 1, "registerMaterialAddendum declared and called once"
    start, end = block_span(code, "public static void registerItems()")
    body_items = flat(code[start:end])
    assert body_items.index("registerMaterials();") < body_items.index("registerMaterialAddendum();"), "registerMaterialAddendum() must follow registerMaterials()"
    return "Frame.asbestos -> HazardEntry(ASBESTOS, asb) next to rad/hot/blinding/hydro; shapes and data(hazMult) (setMutex(0b1), clone(hazMult)) as in 21D; registerMaterialAddendum() private, called once after registerMaterials()"


def c_n_constants(ctx):
    live, orig = ctx["nm"]["consts"], ctx["model"]["consts"]
    used = ["au198", "pb209", "po210", "ra226", "pu238", "radsource_mult", "pobe", "rabe", "pube", "u", "th232", "pu", "sr", "sa326", "trx", "crystal", "block",
            "billet", "ingot", "powder", "powder_mult", "powder_tiny", "nugget", "plate", "fo", "yc", "rtg"]
    wrong = {n: (live.get(n), orig.get(n)) for n in used if live.get(n) != orig.get(n)}
    assert not wrong, "NEO constants differ from the original: " + str(wrong)
    return f"the {len(used)} constants the addendum rows use equal the original in float32"


def c_n_comments(ctx):
    text = ctx["live"][HAZ]
    code = strip_keep(text)
    raw = text.split("\n")
    lo, hi = ctx["nm"]["spans"]["addendum"]
    start = lo
    while start > 1 and "/**" not in raw[start - 1]:
        start -= 1
    doc = "\n".join(raw[start - 1:lo])
    assert lo - start < 12, "registerMaterialAddendum() has no javadoc"
    for ref in (":331-335", ":478", ":485-492", ":424", ":460"):
        assert ref in doc, f"the javadoc of registerMaterialAddendum() does not cite {ref}"
    body = "\n".join(raw[lo - 1:hi])
    assert ":337-347" in body and "RTG" in body, "the RTG deferral comment (:337-347) is missing in registerMaterialAddendum()"
    assert "OreDictManager.java:424" in body and "OreDictManager.java:460" in body, "frame lines must cite OreDictManager.java:424 and :460"
    assert "block_white_phosphorus" in text.split("private static void registerMaterialAddendum()")[1] or "no block_white_phosphorus" in body, "block_white_phosphorus skip is not recorded"
    return "javadoc cites :331-335, :478, :485-492, :424, :460; the body records the RTG deferral :337-347 and the missing block_white_phosphorus; every row carries its original line"


# ---------------------------------------------------------------- E: pre-existing entries

@functools.lru_cache(maxsize=16)
def diff_info(start, live):
    a, b = start.split("\n"), live.split("\n")
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    inserted, hunks, replaced, bad = set(), [], [], []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        if tag == "insert":
            inserted.update(range(j1 + 1, j2 + 1))
            hunks.append((i1 + 1, j1 + 1, j2, j2 - j1))
        elif tag == "replace":
            replaced.append((tuple(a[i1:i2]), tuple(b[j1:j2]), j1 + 1))
        else:
            bad.append((tag, i1 + 1, i2))
    return dict(bad=bad[:3], inserted=inserted, hunks=hunks, replaced=replaced, a=a, b=b)


def c_e_insert_only(ctx):
    info = ctx["diff"]
    assert not info["bad"], "HazardRegistry deletes lines against the frozen start: " + str(info["bad"])
    assert len(info["replaced"]) == 1, f"{len(info['replaced'])} changed lines, expected exactly the Frame javadoc line"
    old, new, at = info["replaced"][0]
    assert len(old) == 1 and len(new) == 1 and "rad/hot/hydro/blinding/asbestos" in new[0] and new[0].replace("rad/hot/hydro/blinding/asbestos", "rad/hot/hydro/blinding", 1) == old[0], \
        f"the one changed line is not the Frame javadoc line: {old!r} -> {new!r}"
    assert ctx["eol"][HAZ] == ctx["start_eol"][HAZ] == "CRLF", f"line endings start {ctx['start_eol'][HAZ]} live {ctx['eol'][HAZ]}"
    assert not ctx["bom"][HAZ], "HazardRegistry gained a BOM"
    regs = re.compile(r"\s*(HazardSystem\.register|frame\(\)|register\w+\()")
    start_lines = [l for l in info["a"] if regs.match(l)]
    kept = [l for n, l in enumerate(info["b"], 1) if n not in info["inserted"] and regs.match(l)]
    assert start_lines == kept, "a pre-existing register / frame line differs from the frozen start"
    return f"start + {sum(h[3] for h in info['hunks'])} inserted lines in {len(info['hunks'])} hunks (live lines " + ", ".join(f"{h[1]}-{h[2]}" for h in info["hunks"]) + \
           f") and the one Frame javadoc line (live :{at}, adds /asbestos); all {len(start_lines)} pre-existing register/frame lines byte-identical; CRLF kept, no BOM"


def c_e_inserted_lines(ctx):
    nm, info = ctx["nm"], ctx["diff"]
    lines = ctx["live"][HAZ].split("\n")
    lo, hi = nm["spans"]["addendum"]
    start = lo
    while start > 1 and "/**" not in lines[start - 1]:
        start -= 1
    call_lines = [n for n, l in enumerate(lines, 1) if l.strip() == "registerMaterialAddendum();"]
    asb_lines = [n for n, l in enumerate(lines, 1) if l.strip().startswith("Frame asbestos(float asb)")]
    assert len(call_lines) == 1 and len(asb_lines) == 1, "call or Frame.asbestos line count"
    stray = []
    for number in sorted(info["inserted"]):
        s = lines[number - 1].strip()
        if start <= number <= hi or number in call_lines or number in asb_lines:
            continue
        if s in ("", "}") and start - 2 <= number <= hi + 2:
            continue
        stray.append((number, s[:80]))
    assert not stray, "inserted lines outside registerMaterialAddendum(), its call and Frame.asbestos: " + str(stray[:5])
    ins = sum(1 for n in info["inserted"] if start <= n <= hi)
    return f"{ins} inserted lines form registerMaterialAddendum() (live :{start}-{hi}); the others are the call (:{call_lines[0]}), Frame.asbestos (:{asb_lines[0]}) and blank/brace lines next to the method"


def c_e_existing_entries(ctx):
    start, live = ctx["start_nm"], ctx["nm"]
    changed = []
    for ident, row in start["regs"].items():
        got = live["regs"].get(ident)
        if got is None or not same_entries(got["entries"], row["entries"]) or got.get("mutex") != row.get("mutex"):
            changed.append(ident)
    assert not changed, "pre-existing entries that differ or vanished: " + str(changed[:8])
    start_keys = [k for k, _ in start["keys"]]
    live_keys = [k for k, _ in live["keys"]]
    for k in set(start_keys):
        assert live_keys.count(k) >= start_keys.count(k), "registration key lost: " + k
    new = sorted(set(live["regs"]) - set(start["regs"]))
    assert len(new) == 18, f"{len(new)} new registrations: {new}"
    return f"all {len(start['regs'])} pre-existing registrations (ids, float32 entries, mutex) equal in the live file; exactly 18 new ids"


def c_e_named_existing(ctx):
    code = strip_keep(ctx["live"][HAZ])
    for pattern, label in ((r"HazardSystem\.register\(NtmBlocks\.FALLOUT\.get\(\), makeData\(RADIATION, 60F\)\);", "FALLOUT RADIATION 60"),
                           (r"HazardSystem\.register\(block\(BRICK_ASBESTOS\), makeData\(ASBESTOS, 1F\)\);", "BRICK_ASBESTOS ASBESTOS 1"),
                           (r"HazardSystem\.register\(item\(POWDER_COLTAN_ORE\), makeData\(ASBESTOS, 3F\)\);", "POWDER_COLTAN_ORE ASBESTOS 3")):
        assert len(re.findall(pattern, code)) == 1, label + " is not present exactly once"
    regs = ctx["nm"]["regs"]
    assert regs["fallout"]["entries"] == [("RADIATION", 60.0)] and regs["brick_asbestos"]["entries"] == [("ASBESTOS", 1.0)] and regs["powder_coltan_ore"]["entries"] == [("ASBESTOS", 3.0)], "named existing entries"
    return "fallout block RADIATION 60, brick_asbestos ASBESTOS 1 and powder_coltan_ore ASBESTOS 3 each present once, unchanged"


def c_e_no_duplicates(ctx):
    seen, dup = {}, []
    for key, line in ctx["nm"]["keys"]:
        if key.startswith("registerMaterials") or key.startswith("registerMaterialAddendum"):
            continue
        if key in seen:
            dup.append((key, seen[key], line))
        seen[key] = line
    assert not dup, "registered twice (key, first line, second line): " + str(dup[:6])
    return f"{len(ctx['nm']['keys'])} registration keys across registerItems, registerMaterials and registerMaterialAddendum, none twice"


def c_e_no_ores(ctx):
    code = strip_keep(ctx["live"][HAZ])
    found = sorted(set(re.findall(r"\bORE_\w+", code)))
    assert not found, "ore blocks referenced in HazardRegistry: " + str(found)
    ids = [i for i, _ in ctx["nm"]["keys"]]
    assert not [i for i in ids if i.startswith("ore_")], "an ore id is registered"
    return "no ORE_* constant in HazardRegistry.java and no ore_* id registered"


def c_e_skipped_not_registered(ctx):
    regs = ctx["nm"]["regs"]
    forbidden = ["pellet_rtg", "block_fallout", "tile_lab_broken", "block_white_phosphorus"]
    hit = [i for i in forbidden if i in regs]
    assert not hit, "skipped items appear registered: " + str(hit)
    code = strip_keep(ctx["live"][HAZ])
    assert not re.search(r"PELLET_RTG\w*", code), "a PELLET_RTG constant is referenced in HazardRegistry.java"
    return "pellet_rtg (exists in NEO), block_fallout, tile_lab_broken and block_white_phosphorus are not registered"


# ---------------------------------------------------------------- S: scope

def c_s_scope(ctx):
    allowed = {HAZ, GAMETEST, STAMP}
    changed = ctx["scope_changed"]
    extra = sorted(set(changed) - allowed)
    assert not extra, "src/ paths changed against baseline.json outside the Goal22D scope: " + str(extra[:8])
    assert HAZ in changed, "HazardRegistry.java is unchanged"
    assert GAMETEST in changed, "HazardGameTests.java is unchanged"
    return f"{len(changed)} src/ path(s) differ from baseline.json: " + ", ".join(sorted(changed))


def c_s_no_new_src(ctx):
    live = set(ctx["src_hashes"])
    base = {p for p in ctx["baseline_files"] if p.startswith("src/")}
    new = sorted(live - base)
    gone = sorted(base - live)
    assert not new, "new src/ files: " + str(new[:6])
    assert not gone, "src/ files removed: " + str(gone[:6])
    return f"{len(live)} src/ files, none added or removed against baseline.json"


def c_s_hashes(ctx):
    base = ctx["baseline_files"]
    paths = list(HAZARD_FILES) + sorted(p for p in base if p.startswith(tuple(HAZARD_DIRS)))
    bad = [p for p in paths if p not in base or ctx["hashes"].get(p) != base[p]]
    assert not bad, "differ from baseline.json: " + str(bad)
    assert ctx["start_hash"] == base[HAZ] and ctx["start_test_hash"] == base[GAMETEST], "the baseline-files copies are not the baseline.json files"
    others = [p for p in base if p.startswith(GAMETEST_DIR) and p != GAMETEST]
    bad_tests = [p for p in others if ctx["hashes"].get(p) != base[p]]
    assert not bad_tests, "other GameTest classes changed: " + str(bad_tests)
    return f"{len(paths)} files (HazardSystem, HazardData, HazardEntry, hazard/type, modifier, transformer, CommonEvents, NtmItems, NtmBlocks) and {len(others)} other GameTest classes hash-equal to baseline.json; the start copies equal baseline.json"


def c_s_language(ctx):
    base = ctx["baseline_files"]
    bad = [p for p in LANGUAGE_FILES if ctx["hashes"].get(p) != base.get(p)]
    assert not bad, "language files or zh mapping changed: " + str(bad)
    return "zh_cn.json, zh_cn-map.json, generated en_us.json and NtmLanguageProvider.java hash-equal to baseline.json (no new key)"


# ---------------------------------------------------------------- K: skipped list

def c_k_skips(ctx):
    cls = ctx["classification"]
    skips = [e for e in cls if e["category"] in (ST_RTG, ST_SKIP, ST_ORE, ST_OTHER)]
    names = {(e["category"], e["line"], e["element"]) for e in skips}
    must = [(ST_SKIP, 477, "ModBlocks.block_fallout"), (ST_SKIP, 481, "tile_lab_broken"), (ST_SKIP, 460, "P_WHITE.block(block_white_phosphorus)"),
            (ST_ORE, 424, "ASBESTOS.ore(ore_asbestos)"), (ST_ORE, 424, "ASBESTOS.ore(ore_gneiss_asbestos)")]
    for m in must:
        assert m in names, f"the skipped list lacks {m}"
    rtg = [e for e in skips if e["category"] == ST_RTG]
    assert len(rtg) == 11, f"{len(rtg)} RTG rows, expected 11 (:337-347)"
    lines = ["skipped / deferred (not registered by this batch):"]
    for e in skips:
        lines.append(f"  {e['category']:<22} {e['source'].split('.')[0]}:{e['line']}  {e['element']}")
    ctx["skip_lines"] = lines
    return f"{len(skips)} entries stored in the report: RTG-deferred {len(rtg)} (HazardRegistry.java:337-347, pellet_rtg exists in NEO and stays without a hazard), " \
           f"block_fallout :477, tile_lab_broken :481, block_white_phosphorus (OreDictManager.java:460), 4 ASBESTOS ore arguments (:424), " \
           f"{sum(1 for e in skips if e['category'] == ST_OTHER)} pile_rod / PWR statements"


# ---------------------------------------------------------------- T: the GameTest source

def gametest_tests(text):
    code = strip_keep(text)
    consts = dict(re.findall(r'static final String (\w+) = "([^"]*)";', code))
    found = {}
    for m in re.finditer(r"@GameTest\(([^)]*)\)\s*public static void (\w+)\(GameTestHelper", code):
        batch = re.search(r'batch\s*=\s*("([^"]*)"|(\w+))', m.group(1))
        found[m.group(2)] = None if not batch else batch.group(2) if batch.group(2) is not None else consts.get(batch.group(3))
    return found


def c_t_source(ctx):
    text = ctx["gametest"]
    code = strip_keep(text)
    assert "@GameTestHolder(" in code and "@PrefixGameTestTemplate(false)" in code, "GameTestHolder / PrefixGameTestTemplate"
    found = gametest_tests(text)
    for name in OLD_TESTS + NEW_TESTS:
        assert name in found, f"GameTest {name} is missing"
    assert len(found) == len(OLD_TESTS) + len(NEW_TESTS), f"{len(found)} GameTests in the class, expected {len(OLD_TESTS) + len(NEW_TESTS)}"
    wrong = {n: b for n, b in found.items() if b != GAMETEST_BATCH}
    assert not wrong, f"GameTests not in batch {GAMETEST_BATCH!r}: {wrong}"
    forbidden = re.findall(r"makeMockPlayer|makeMockServerPlayer|FakePlayer|FakePlayerFactory|java\.lang\.reflect|getDeclaredField|getDeclaredMethod|setAccessible|"
                           r"import (?:net\.minecraft\.client|net\.neoforged\.neoforge\.client|com\.mojang\.blaze3d|com\.hbm\.render)", code)
    assert not forbidden, "forbidden in the GameTest class: " + str(forbidden)
    assert "private static final int EXPECTED_ROWS = 165;" in code, "EXPECTED_ROWS (the 21D table) must stay 165"
    assert "private static final int ADDENDUM_ROWS = 18;" in code and "private static final int SAMPLE_ROWS = 20;" in code, "ADDENDUM_ROWS / SAMPLE_ROWS"
    assert ctx["eol"][GAMETEST] == "LF" and ctx["start_test_eol"] == "LF", f"HazardGameTests line endings start {ctx['start_test_eol']} live {ctx['eol'][GAMETEST]}"
    # the old tests are untouched except hazard_none_for_ores_and_unlisted: every old method body equals its body in the frozen start
    def body(t, name):
        c = strip_keep(t)
        start, end = block_span(c, f"public static void {name}(GameTestHelper")
        return flat(c[start:end + 1])
    changed = [n for n in OLD_TESTS if body(ctx["start_test"], n) != body(text, n)]
    assert changed == ["hazard_none_for_ores_and_unlisted"], f"old tests whose body changed: {changed}"
    none_body = body(text, "hazard_none_for_ores_and_unlisted")
    for must in ('"block_white_phosphorus", "block_fallout", "tile_lab_broken", "pellet_rtg"',):
        assert must in none_body, "the RTG deferral guard list is missing in hazard_none_for_ores_and_unlisted"
    for gone in ('"crystal_uranium"', '"powder_caesium"', '"billet_flashlead"', '"ingot_phosphorus"'):
        assert gone not in none_body, f"hazard_none_for_ores_and_unlisted still expects no hazard for {gone}"
    return f"{len(found)} GameTests in batch {GAMETEST_BATCH}: 7 old (6 untouched, hazard_none_for_ores_and_unlisted updated to the unregistered ids + pellet_rtg guard) and 4 new ({', '.join(NEW_TESTS)}); LF kept; no mock player, reflection or client imports"


def c_t_addendum_table(ctx):
    code = strip_keep(ctx["gametest"])
    start, end = block_span(code, "private static List<AddendumRow> addendumRows()")
    rows = []
    for m in re.finditer(r"addendum\(rows, \"([^\"]+)\", (Ntm(?:Items|Blocks)\.\w+), (.*?), (0b1|0)\);", code[start:end]):
        args = split_args(m.group(3))
        assert len(args) == 4, f"addendum row {m.group(1)} has {len(args)} level arguments"
        kind, ident = resolve_target(m.group(2), ctx["neo_ids"])
        levels = [eval_float(a, ctx["nm"]["consts"]) for a in args]
        rows.append((m.group(1), ident, kind, levels, int(m.group(4), 0)))
    assert len(rows) == 18, f"{len(rows)} rows in addendumRows(), expected 18"
    expected = [r for r in ctx["table"] if r["state"] == ST_REG]
    assert [r[1] for r in rows] == [r["neo_id"] for r in expected], f"test table ids {[r[1] for r in rows]} != expected {[r['neo_id'] for r in expected]}"
    order = ("RADIATION", "HOT", "HYDROACTIVE", "ASBESTOS")
    for (label, ident, _, levels, mutex), want in zip(rows, expected):
        got = [(t, v) for t, v in zip(order, levels) if v != 0.0]
        assert sorted((t, f32_bits(v)) for t, v in got) == sorted((t, f32_bits(v)) for t, v in want["entries"]), \
            f"{ident}: test table {entries_repr(got)} != original {entries_repr(want['entries'])}"
        assert mutex == want["mutex"], f"{ident}: test table mutex {mutex}, expected {want['mutex']}"
        assert re.match(r"(:\d+|ODM:\d+)", label) and label.split(":")[1] == str(want["orig_line"]), f"{ident}: label {label} does not cite original line {want['orig_line']}"
    # the plain-number spot checks
    spots = {}
    t_start, t_end = block_span(code, "public static void hazard_addendum_registrations(GameTestHelper")
    for m in re.finditer(r"checkLevel\(new ItemStack\((Ntm(?:Items|Blocks)\.\w+)\.get\(\)\), HazardRegistry\.(\w+), ([\d.]+)F, \"[^\"]*\"\);", code[t_start:t_end]):
        kind, ident = resolve_target(m.group(1), ctx["neo_ids"])
        spots[(ident, m.group(2))] = float(m.group(3))
    by_id = {r["neo_id"]: dict(r["entries"]) for r in expected}
    for key, value in spots.items():
        assert key[0] in by_id and key[1] in by_id[key[0]], f"spot check {key} is not an expected entry"
        assert abs(by_id[key[0]][key[1]] - value) <= 1e-6 * max(1.0, value), f"spot check {key}: {value} != expected {f32_repr(by_id[key[0]][key[1]])}"
    for key, value in SPOT_ACCEPTANCE.items():
        assert spots.get(key) == value, f"the acceptance spot value {key} = {value} is missing in the test"
    total = sum(len(v) for v in by_id.values())
    assert len(spots) == total, f"{len(spots)} spot checks, expected one per expected entry ({total})"
    return f"addendumRows() lists the same 18 rows in order, with levels (float32, the original's order) and mutex equal to the expected table; {len(spots)} plain-number spot checks equal the table and cover the acceptance list"


def baseline_sample_entries(ctx, key):
    """Entries of a row of the frozen start HazardRegistry (key = registry id, 'minecraft:x' or a special form)."""
    start = ctx["start_nm"]
    if key in start["regs"]:
        return start["regs"][key]["entries"]
    text = ctx["start"][HAZ]
    consts = start["consts"]
    m = re.fullmatch(r"rod_quad:(\w+)", key)
    if m:
        hit = re.search(rf"registerBreedingRodRadiation\(BreedingRodType\.{m.group(1)}, ([^)]*)\);", strip_keep(text))
        assert hit, "breeding rod row not found in the start copy"
        return [("RADIATION", f32(eval_float(hit.group(1), consts) * consts["rod_quad"]))]
    m = re.fullmatch(r"waste1:(\w+)", key)
    if m:
        hit = re.search(rf"registerOtherWaste\({m.group(1)}, (.*)\);", strip_keep(text))
        assert hit, "waste row not found in the start copy"
        return [("RADIATION", eval_float(hit.group(1), consts)), ("HOT", 5.0)]
    raise AssertionError("unknown sample key " + key)


def c_t_sample(ctx):
    code = strip_keep(ctx["gametest"])
    start, end = block_span(code, "public static void hazard_existing_sample_unchanged(GameTestHelper")
    body = code[start:end]
    consts = dict(ctx["start_nm"]["consts"])
    for name, ref in re.findall(r"(\w+) = HazardRegistry\.(\w+)", re.search(r"float powder = [^;]*;", body).group(0)):
        consts[name] = consts[ref]
    n = 0
    for m in re.finditer(r"\bsample\(n, ", body):
        open_index = m.start() + len("sample")
        args = split_args(body[open_index + 1:matching_paren(body, open_index)])
        assert args[0] == "n", "sample call form"
        label, stack, pairs = args[1].strip('"'), args[2], args[3:]
        sm = re.fullmatch(r"new ItemStack\((Ntm(?:Items|Blocks)\.\w+\.get\(\)|Items\.\w+)\)", stack)
        mm = re.fullmatch(r"MetaHelper\.newStack\(NtmItems\.(\w+), 1, (?:BreedingRodType\.(\w+)\.ordinal\(\)|(\d+))\)", stack)
        if sm:
            if sm.group(1).startswith("Items."):
                key = "minecraft:" + sm.group(1).split(".")[1].lower()
            else:
                key = resolve_target(sm.group(1), ctx["neo_ids"])[1]
        elif mm and mm.group(1) == "ROD_QUAD":
            key = "rod_quad:" + mm.group(2)
        elif mm and mm.group(1) == "WASTE_PLUTONIUM" and mm.group(3) == "1":
            key = "waste1:WASTE_PLUTONIUM"
        else:
            raise AssertionError("cannot resolve the sample stack " + stack)
        assert len(pairs) % 2 == 0, f"sample {label}: odd pairs"
        got = [(pairs[k].replace("HazardRegistry.", ""), eval_float(pairs[k + 1], consts)) for k in range(0, len(pairs), 2)]
        want = baseline_sample_entries(ctx, key)
        assert sorted((t, f32_bits(v)) for t, v in got) == sorted((t, f32_bits(v)) for t, v in want), \
            f"sample {label}: test {entries_repr(got)} != frozen start {entries_repr(want)}"
        n += 1
    assert n == 20, f"{n} sample rows, expected 20"
    return "all 20 sample rows of hazard_existing_sample_unchanged equal the entries of the frozen start HazardRegistry.java in float32 (types and values, including fallout 60, brick_asbestos 1, powder_coltan_ore 3, white wool 5, blaze powder 4)"


# ---------------------------------------------------------------- L and J

def c_l_log(ctx):
    path = ctx.get("gametest_log")
    if not path:
        return ("pending", "no --gametest-log given")
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    total = 0
    for p in sorted((ROOT / GAMETEST_DIR).glob("*.java")):
        total += len(re.findall(r"@GameTest\(", strip_keep(lf(p.read_bytes()))))
    m = re.search(r"All (\d+) required tests passed", text)
    assert m, "no `All N required tests passed` line"
    assert int(m.group(1)) == total, f"All {m.group(1)} required tests passed, but the source has {total} @GameTest annotations"
    assert re.search(rf"{total} GAME TESTS COMPLETE", text), "no `GAME TESTS COMPLETE` line for the expected count"
    assert not re.search(r"required tests failed|optional tests failed", text), "the log reports failed tests"
    missing = [n for n in OLD_TESTS + NEW_TESTS if not re.search(rf"\[hbm-hazard\] {re.escape(n)} passed", text)]
    assert not missing, "tests without a pass marker in the log: " + str(missing)
    batches = [int(k) for k in re.findall(rf"Running test batch '{GAMETEST_BATCH}:\d+' \((\d+) tests\)", text)]
    assert sum(batches) == len(OLD_TESTS) + len(NEW_TESTS), f"batch {GAMETEST_BATCH}: {batches} tests"
    assert "BUILD SUCCESSFUL" in text, "no BUILD SUCCESSFUL"
    return f"{Path(path).name}: `All {total} required tests passed`, pass markers for the {len(NEW_TESTS)} new and {len(OLD_TESTS)} old hazard tests, BUILD SUCCESSFUL"


def c_j_jar(ctx):
    jar = ctx.get("jar")
    if not jar:
        return ("pending", "no --jar given")
    names = jar["names"]
    for cls in ("com/hbm/hazard/HazardRegistry.class", "com/hbm/hazard/HazardRegistry$Frame.class", "com/hbm/gametest/HazardGameTests.class"):
        assert cls in names, "JAR lacks " + cls
    reg = jar["data"]["com/hbm/hazard/HazardRegistry.class"]
    frame = jar["data"]["com/hbm/hazard/HazardRegistry$Frame.class"]
    tests = jar["data"]["com/hbm/gametest/HazardGameTests.class"]
    assert b"registerMaterialAddendum" in reg, "HazardRegistry.class has no registerMaterialAddendum"
    assert b"asbestos" in frame, "HazardRegistry$Frame.class has no asbestos method"
    for r in ctx["table"]:
        if r["state"] == ST_REG and r["source"].startswith("HazardRegistry"):
            const = ctx["neo_ids"]["item_ids"][r["neo_id"]].encode()
            assert const in reg, f"HazardRegistry.class does not reference {const.decode()}"
    # constant-folded float values in the constant pool (tag 4 + big-endian float); values 0, 1 and 2 compile to fconst
    for r in ctx["table"]:
        if r["state"] == ST_REG and r["source"].startswith("HazardRegistry"):
            for t, v in r["entries"]:
                if v not in (0.0, 1.0, 2.0):
                    assert b"\x04" + struct.pack(">f", v) in reg, f"HazardRegistry.class lacks the float constant {f32_repr(v)} of {r['neo_id']} {t}"
    for name in NEW_TESTS:
        assert name.encode() in tests, f"HazardGameTests.class lacks {name}"
    return "JAR has HazardRegistry (registerMaterialAddendum, the item constants and the folded float constants of the 14 item-level rows), HazardRegistry$Frame (asbestos) and HazardGameTests with the 4 new tests"


# ---------------------------------------------------------------- git state

def git_checks():
    head = git(ORIGINAL, "rev-parse", "HEAD").strip()
    status = git(ORIGINAL, "status", "--porcelain=v1", "--untracked-files=all")
    return {"O0_original_head_clean": dict(status="pass" if head == ORIGINAL_HEAD and status == "" else "fail",
                                           detail=f"original HEAD {head}, status {'clean' if status == '' else status[:200]!r}")}


# ---------------------------------------------------------------- registry of checks

CHECKS = [
    ("O1_original_rows", c_o_rows), ("O2_dictframe", c_o_dictframe), ("O3_constants", c_o_constants), ("O4_expected_table", c_o_table),
    ("O5_line_classification", c_o_classification), ("O6_before_values", c_o_before_values),
    ("N1_addendum_rows", c_n_addendum_rows), ("N2_frame_class_and_structure", c_n_frame_class), ("N3_constants", c_n_constants), ("N4_comments", c_n_comments),
    ("E1_insert_only", c_e_insert_only), ("E2_inserted_lines", c_e_inserted_lines), ("E3_existing_entries", c_e_existing_entries),
    ("E4_named_existing", c_e_named_existing), ("E5_no_duplicates", c_e_no_duplicates), ("E6_no_ores", c_e_no_ores), ("E7_skipped_not_registered", c_e_skipped_not_registered),
    ("S1_scope", c_s_scope), ("S2_no_new_src", c_s_no_new_src), ("S3_hash_equal_files", c_s_hashes), ("S4_language_unchanged", c_s_language),
    ("K_skipped_list", c_k_skips),
    ("T1_gametest_source", c_t_source), ("T2_addendum_table", c_t_addendum_table), ("T3_sample_vs_start", c_t_sample),
    ("L_gametest_log", c_l_log), ("J_jar", c_j_jar),
]
NEED_PREPARE = ("O4", "O5", "O6", "N", "E", "K", "T", "J")


def prepare(ctx):
    """Prepares the original model, the table and the NEO models separately so that a broken input fails only the checks that read it."""
    for key in ("model", "neo_ids", "table", "start_nm", "start_regs", "nm", "diff", "classification"):
        ctx.pop(key, None)
    ctx["model"] = parse_original(ctx)
    ctx["neo_ids"] = neo_id_maps(ctx["items_text"], ctx["blocks_text"], ctx["raw_text"])
    ctx["table"] = build_table(ctx)
    ctx["start_nm"] = neo_model(ctx["start"][HAZ], ctx["neo_ids"], False)
    ctx["start_regs"] = set(ctx["start_nm"]["regs"])
    ctx["nm"] = neo_model(ctx["live"][HAZ], ctx["neo_ids"], True)
    ctx["diff"] = diff_info(ctx["start"][HAZ], ctx["live"][HAZ])
    ctx["classification"] = classify_original(ctx)


def run_checks(ctx):
    results = {}
    prep_error = None
    try:
        prepare(ctx)
    except (AssertionError, KeyError, ValueError, IndexError, AttributeError, TypeError, StopIteration, re.error) as error:
        prep_error = f"{type(error).__name__}: {error}"[:600]
    for name, fn in CHECKS:
        try:
            if prep_error and name.startswith(NEED_PREPARE) and name not in ("O1_original_rows", "O2_dictframe", "O3_constants"):
                raise AssertionError("inputs cannot be analysed: " + prep_error)
            out = fn(ctx)
            results[name] = dict(status=out[0], detail=out[1]) if isinstance(out, tuple) else dict(status="pass", detail=out)
        except (AssertionError, KeyError, ValueError, IndexError, AttributeError, TypeError, StopIteration, re.error) as error:
            results[name] = dict(status="fail", detail=f"{type(error).__name__}: {error}"[:600])
    return results


# ---------------------------------------------------------------- M: mutations (in memory only)

def clone(ctx):
    out = dict(ctx)
    for key, value in ctx.items():
        if isinstance(value, dict):
            out[key] = dict(value)
        elif isinstance(value, list):
            out[key] = list(value)
    return out


def mut(old, new, path=HAZ, count=1):
    """Mutates the NEO HazardRegistry text (path HAZ) or the GameTest source (path GAMETEST)."""
    def change(ctx):
        if path == GAMETEST:
            text = ctx["gametest"]
            assert text.count(old) == count, ("mutation anchor", old[:80], text.count(old))
            ctx["gametest"] = text.replace(old, new)
        else:
            text = ctx["live"][path]
            assert text.count(old) == count, ("mutation anchor", old[:80], text.count(old))
            ctx["live"][path] = text.replace(old, new)
    return change


def mut_o(old, new, path):
    """Mutates a file of the read-only original (in memory)."""
    def change(ctx):
        text = ctx["original"][path]
        assert text.count(old) == 1, ("original mutation anchor", old[:80], text.count(old))
        ctx["original"][path] = text.replace(old, new)
    return change


def mut_set(key, value, sub=None):
    def change(ctx):
        if sub is None:
            ctx[key] = value
        else:
            ctx[key][sub] = value
    return change


def mut_start(old, new):
    def change(ctx):
        text = ctx["start"][HAZ]
        assert text.count(old) == 1, ("start mutation anchor", old[:80], text.count(old))
        ctx["start"][HAZ] = text.replace(old, new)
    return change


CRYSTAL_URANIUM_ROW = "        HazardSystem.register(item(CRYSTAL_URANIUM), makeData(RADIATION, u * crystal)); // :485\n"
CRYSTAL_LITHIUM_ROW = "        HazardSystem.register(item(CRYSTAL_LITHIUM), makeData(HYDROACTIVE, 1F * crystal)); // :491\n"
ASBESTOS_FRAME = "        frame().asbestos(1F)"
CAESIUM_ROW = "makeData().addEntry(HYDROACTIVE, 1F).addEntry(HOT, 3F)); // :478"
CALL = "        registerMaterialAddendum();\n"

MUTATIONS = [
    ("multiplier_crystal_to_block_x2", mut("makeData(RADIATION, u * crystal)); // :485", "makeData(RADIATION, u * block * 2)); // :485")),
    ("constant_trx_25_to_26", mut("public static final float trx = 25.0F;", "public static final float trx = 26.0F;")),
    ("constant_crystal_changed", mut("public static final float crystal = block;", "public static final float crystal = block * 2;")),
    ("constant_radsource_mult_changed", mut("public static final float radsource_mult = 3.0F;", "public static final float radsource_mult = 2.0F;")),
    ("row_dropped_crystal_lithium", mut(CRYSTAL_LITHIUM_ROW, "")),
    ("row_dropped_billet_ra226be", mut("        HazardSystem.register(item(BILLET_RA226BE), makeData(RADIATION, rabe * billet)); // :334\n", "")),
    ("caesium_hot_swapped_for_hydroactive", mut(CAESIUM_ROW, "makeData().addEntry(HYDROACTIVE, 1F).addEntry(HYDROACTIVE, 3F)); // :478")),
    ("caesium_entry_order_swapped", mut(CAESIUM_ROW, "makeData().addEntry(HOT, 3F).addEntry(HYDROACTIVE, 1F)); // :478")),
    ("flashlead_hot_dropped", mut("makeData().addEntry(RADIATION, pb209 * 1.25F * billet).addEntry(HOT, 7F)); // :332", "makeData(RADIATION, pb209 * 1.25F * billet)); // :332")),
    ("flashlead_factor_dropped", mut("pb209 * 1.25F * billet", "pb209 * billet")),
    ("crystal_phosphorus_hot_2_to_3", mut("makeData(HOT, 2F * crystal)); // :490", "makeData(HOT, 3F * crystal)); // :490")),
    ("crystal_schrabidium_wrong_constant", mut("makeData(RADIATION, sa326 * crystal)); // :489", "makeData(RADIATION, sa327 * crystal)); // :489")),
    ("ore_block_added_as_row", mut(ASBESTOS_FRAME, "        HazardSystem.register(block(NtmBlocks.ORE_ASBESTOS), makeData(ASBESTOS, 1F));\n" + ASBESTOS_FRAME)),
    ("ore_block_added_to_frame", mut(".block(NtmBlocks.BLOCK_ASBESTOS);", ".block(NtmBlocks.BLOCK_ASBESTOS, NtmBlocks.ORE_ASBESTOS);")),
    ("duplicate_new_registration", mut(CRYSTAL_URANIUM_ROW, CRYSTAL_URANIUM_ROW + CRYSTAL_URANIUM_ROW)),
    ("duplicate_existing_registration", mut("        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));\n",
                                            "        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));\n        HazardSystem.register(item(DEBRIS_METAL), makeData(RADIATION, 5F));\n")),
    ("existing_row_value_changed_fallout", mut("HazardSystem.register(NtmBlocks.FALLOUT.get(), makeData(RADIATION, 60F));", "HazardSystem.register(NtmBlocks.FALLOUT.get(), makeData(RADIATION, 61F));")),
    ("existing_line_deleted", mut("        HazardSystem.register(item(DEBRIS_ELEMENT), makeData(RADIATION, 100F));\n", "")),
    ("existing_line_edited", mut("wst * rod_dual * 11.5F, false);", "wst * rod_dual * 11F, false);")),
    ("rtg_pellet_registered", mut(CALL, "        HazardSystem.register(item(PELLET_RTG), makeData(RADIATION, pu238 * rtg));\n" + CALL.replace("registerMaterialAddendum", "registerMaterialAddendum"))),
    ("skipped_block_white_phosphorus_registered", mut(".ingot(INGOT_PHOSPHORUS); // OreDictManager.java:460", ".ingot(INGOT_PHOSPHORUS).block(NtmBlocks.FALLOUT); // OreDictManager.java:460")),
    ("asbestos_ingot_uses_dust_shape", mut(".ingot(INGOT_ASBESTOS).dust(POWDER_ASBESTOS)", ".dust(INGOT_ASBESTOS).dust(POWDER_ASBESTOS)")),
    ("asbestos_level_changed", mut("frame().asbestos(1F)", "frame().asbestos(2F)")),
    ("phosphorus_hot_5_to_4", mut("frame().hot(5F).ingot(INGOT_PHOSPHORUS)", "frame().hot(4F).ingot(INGOT_PHOSPHORUS)")),
    ("frame_asbestos_wrong_type", mut("Frame asbestos(float asb) { return haz(new HazardEntry(ASBESTOS, asb)); }", "Frame asbestos(float asb) { return haz(new HazardEntry(HOT, asb)); }")),
    ("frame_asbestos_method_removed", mut("        Frame asbestos(float asb) { return haz(new HazardEntry(ASBESTOS, asb)); }\n", "")),
    ("setMutex_dropped", mut(".setMutex(0b1)", "")),
    ("clone_hazMult_replaced_by_1F", mut("hazard.clone(hazMult)", "hazard.clone(1F)")),
    ("line_comment_wrong", mut("makeData(RADIATION, th232 * crystal)); // :486", "makeData(RADIATION, th232 * crystal)); // :487")),
    ("frame_line_comment_wrong", mut("// OreDictManager.java:424", "// OreDictManager.java:425")),
    ("addendum_call_removed", mut(CALL, "")),
    ("addendum_called_before_materials", mut("        registerMaterials();\n        registerMaterialAddendum();\n", "        registerMaterialAddendum();\n        registerMaterials();\n")),
    ("rtg_comment_removed", mut(":337-347, the eleven RTG pellet rows", "the eleven RTG pellet rows")),
    ("javadoc_changed_beyond_asbestos", mut("rad/hot/hydro/blinding/asbestos collect", "rad/hot/hydro/blinding/asbestos/x collect")),
    ("line_endings_flipped_to_lf", mut_set("eol", "LF", HAZ)),
    ("frozen_hash_hazard_system", mut_set("hashes", "0" * 64, J + "hazard/HazardSystem.java")),
    ("frozen_hash_hazard_type", mut_set("hashes", "0" * 64, J + "hazard/type/HazardTypeRadiation.java")),
    ("frozen_hash_modifier", mut_set("hashes", "0" * 64, J + "hazard/modifier/HazardModifierFuelRadiation.java")),
    ("frozen_hash_common_events", mut_set("hashes", "0" * 64, COMMON_EVENTS)),
    ("frozen_hash_ntm_items", mut_set("hashes", "0" * 64, NTM_ITEMS)),
    ("frozen_hash_zh_map", mut_set("hashes", "0" * 64, "migration/localization/zh_cn-map.json")),
    ("frozen_hash_en_us", mut_set("hashes", "0" * 64, "src/generated/resources/assets/hbmsntm/lang/en_us.json")),
    ("other_src_file_changed", lambda ctx: ctx.__setitem__("scope_changed", ctx["scope_changed"] + [J + "items/NtmItems.java"])),
    ("new_src_file_added", lambda ctx: ctx.__setitem__("src_hashes", {**ctx["src_hashes"], J + "hazard/HazardExtra.java": "0" * 64})),
    ("other_gametest_class_changed", mut_set("hashes", "0" * 64, J + "gametest/SmokeGameTests.java")),
    ("original_constant_moved", mut_o("public static final float crystal = block;", "public static final float crystal = block * 2;", O_HAZ)),
    ("original_row_value_moved", mut_o("makeData(RADIATION, trx * crystal)", "makeData(RADIATION, trx * block)", O_HAZ)),
    ("original_frame_row_moved", mut_o("ASBESTOS\t.asbestos(1F)", "ASBESTOS\t.asbestos(2F)", O_ODM)),
    ("original_existing_value_moved", mut_o("HazardSystem.register(boy_bullet, makeData(RADIATION, u235 * ingot));", "HazardSystem.register(boy_bullet, makeData(RADIATION, u235 * ingot * 3));", O_HAZ)),
    ("start_copy_existing_value_differs", mut_start("        HazardSystem.register(block(BRICK_ASBESTOS), makeData(ASBESTOS, 1F));", "        HazardSystem.register(block(BRICK_ASBESTOS), makeData(ASBESTOS, 2F));")),
    ("gametest_table_value_changed", mut("addendum(rows, \":492\", NtmItems.CRYSTAL_TRIXITE, HazardRegistry.trx * HazardRegistry.crystal,", "addendum(rows, \":492\", NtmItems.CRYSTAL_TRIXITE, HazardRegistry.trx * HazardRegistry.billet,", GAMETEST)),
    ("gametest_table_mutex_changed", mut("NtmItems.INGOT_PHOSPHORUS, 0F, 5F * HazardRegistry.ingot, 0F, 0F, 0b1);", "NtmItems.INGOT_PHOSPHORUS, 0F, 5F * HazardRegistry.ingot, 0F, 0F, 0);", GAMETEST)),
    ("gametest_table_row_removed", mut("        addendum(rows, \":491\", NtmItems.CRYSTAL_LITHIUM, 0F, 0F, 1F * HazardRegistry.crystal, 0F, 0);\n", "", GAMETEST)),
    ("gametest_spot_value_changed", mut("HazardRegistry.RADIATION, 150F, \"crystal_schrabidium\"", "HazardRegistry.RADIATION, 151F, \"crystal_schrabidium\"", GAMETEST)),
    ("gametest_sample_value_changed", mut("sample(n, \"fallout block\", new ItemStack(NtmBlocks.FALLOUT.get()), HazardRegistry.RADIATION, 60F);", "sample(n, \"fallout block\", new ItemStack(NtmBlocks.FALLOUT.get()), HazardRegistry.RADIATION, 61F);", GAMETEST)),
    ("gametest_sample_row_removed", mut("            sample(n, \"green wool\", new ItemStack(Items.GREEN_WOOL), HazardRegistry.RADIATION, 150F);\n", "", GAMETEST)),
    ("gametest_new_test_renamed", mut("public static void hazard_living_crystal_schrabidium(", "public static void hazard_living_crystal_x(", GAMETEST)),
    ("gametest_old_test_changed", mut("checkExact(\"gold_ingot\", new ItemStack(Items.GOLD_INGOT), HazardRegistry.BLINDING, 4F);", "checkExact(\"gold_ingot\", new ItemStack(Items.GOLD_INGOT), HazardRegistry.BLINDING, 5F);", GAMETEST)),
    ("gametest_rtg_guard_removed", mut("\"block_white_phosphorus\", \"block_fallout\", \"tile_lab_broken\", \"pellet_rtg\"", "\"block_white_phosphorus\", \"block_fallout\", \"tile_lab_broken\"", GAMETEST)),
    ("gametest_mock_player_added", mut("check(", "helper.makeMockPlayer(null); check(", GAMETEST, count=None)),
    ("gametest_batch_wrong", mut("batch = BATCH, timeoutTicks = 100)\n    public static void hazard_addendum_registrations", "batch = \"other\", timeoutTicks = 100)\n    public static void hazard_addendum_registrations", GAMETEST)),
    ("gametest_reflection_added", mut("@GameTestHolder(", "import java.lang.reflect.Field;\n@GameTestHolder(", GAMETEST)),
]


def run_mutations(ctx, baseline_results):
    passing = {n for n, r in baseline_results.items() if r["status"] == "pass" and n not in ("O0_original_head_clean", "inputs_stable_during_run")}
    out = {}
    for label, change in MUTATIONS:
        mutated = clone(ctx)
        mutated["original"] = dict(ctx["original"])
        mutated["start"] = dict(ctx["start"])
        mutated["live"] = dict(ctx["live"])
        mutated["hashes"] = dict(ctx["hashes"])
        mutated["src_hashes"] = dict(ctx["src_hashes"])
        mutated["eol"] = dict(ctx["eol"])
        try:
            if label == "gametest_mock_player_added":
                mutated["gametest"] = ctx["gametest"].replace("check(", "helper.makeMockPlayer(null); check(", 1)
            else:
                change(mutated)
        except AssertionError as error:
            out[label] = dict(kind="code", detected=False, semantic_detected=False, failing_checks=[], first_message="MUTATION ANCHOR NOT FOUND: " + str(error)[:200])
            continue
        results = run_checks(mutated)
        failed = sorted(n for n in passing if n in results and results[n]["status"] == "fail")
        kind = "diff" if label.startswith(("line_endings", "frozen_", "other_", "new_src", "original_", "gametest_", "start_copy", "existing_line", "javadoc_")) else "code"
        semantic = [n for n in failed if n not in DIFF_ONLY_CHECKS]
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
    test_raw = reader.bytes(ROOT, GAMETEST, "neo")
    start_test_raw = reader.bytes(START, GAMETEST, "start")
    ctx["eol"] = {HAZ: eol_kind(raw), GAMETEST: eol_kind(test_raw)}
    ctx["start_eol"] = {HAZ: eol_kind(start_raw)}
    ctx["start_test_eol"] = eol_kind(start_test_raw)
    ctx["bom"] = {HAZ: raw.startswith(b"\xef\xbb\xbf")}
    ctx["start_hash"] = sha(start_raw)
    ctx["start_test_hash"] = sha(start_test_raw)
    ctx["original"] = {p: reader.text(ORIGINAL, p, "original") for p in (O_ODM, O_HAZ, O_ENTRY)}
    ctx["items_text"] = reader.text(ROOT, NTM_ITEMS, "neo")
    ctx["blocks_text"] = reader.text(ROOT, NTM_BLOCKS, "neo")
    ctx["raw_text"] = reader.text(ROOT, RAW_INGOT, "neo")
    ctx["gametest"] = lf(test_raw)
    ctx["start_test"] = lf(start_test_raw)
    baseline = json.loads(reader.text(BATCH, "baseline.json", "batch"))
    ctx["baseline_files"] = baseline["files"]

    hashes, scope = {}, []
    for path in sorted((ROOT / "src").rglob("*")):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            h = sha(path.read_bytes())
            hashes[rel] = h
            if baseline["files"].get(rel) != h:
                scope.append(rel)
    ctx["src_hashes"] = dict(hashes)
    scope += [p for p in baseline["files"] if p.startswith("src/") and p not in hashes]
    ctx["scope_changed"] = sorted(set(scope))
    for p in LANGUAGE_FILES:
        if p not in hashes and (ROOT / p).is_file():
            hashes[p] = sha((ROOT / p).read_bytes())
    ctx["hashes"] = hashes
    ctx["src_names"] = [p.name for p in (ROOT / "src/main/java").rglob("*.java")]
    ctx["gametest_log"] = str(gametest_log) if gametest_log else None
    ctx["jar"] = None
    if jar_path:
        with zipfile.ZipFile(jar_path) as z:
            wanted = ("com/hbm/hazard/HazardRegistry.class", "com/hbm/hazard/HazardRegistry$Frame.class", "com/hbm/gametest/HazardGameTests.class")
            ctx["jar"] = dict(names=set(z.namelist()), data={n: z.read(n) for n in wanted if n in z.namelist()})
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
    parser.add_argument("--gametest-log", help="check a runGameTestServer log")
    parser.add_argument("--jar", help="check the packaged JAR")
    args = parser.parse_args()
    reader = Reader()
    ctx = build_context(reader, args.gametest_log, args.jar)
    results = {**git_checks(), **run_checks(ctx)}
    mutations = run_mutations(ctx, results)
    after = Reader()
    build_context(after, args.gametest_log, args.jar)
    results["inputs_stable_during_run"] = dict(status="pass" if after.hashes == reader.hashes else "fail", detail="every file read has the same SHA-256 after the run")

    counts = {s: sum(1 for r in results.values() if r["status"] == s) for s in ("pass", "fail", "pending")}
    detected = sum(1 for m in mutations.values() if m["detected"])
    final = bool(args.gametest_log and args.jar)
    semantic_missing = sorted(k for k, m in mutations.items() if m["kind"] == "code" and not m["semantic_detected"])
    ok = counts["fail"] == 0 and detected == len(mutations) and not semantic_missing and (not final or counts["pending"] == 0)
    table = ctx.get("table", [])
    cls = ctx.get("classification", [])
    class_counts = {s: sum(1 for e in cls if e["category"] == s) for s in STATES}
    production = {p: sha((ROOT / p).read_bytes()) for p in (HAZ, GAMETEST)}
    report = dict(tool="tools/migration/verify_goal22d_hazards.py", ok=ok, final=final, production_sha256=production,
                  code_mutations_without_semantic_catch=semantic_missing,
                  evidence="Static source, JSON, byte and float32 arithmetic checks over the live NEO tree, the frozen Goal22D start copy and the read-only "
                           "original; mutations are applied in memory only. No game, server or world: the registry values and the per-tick path on a Pig are asserted "
                           "only by HazardGameTests (L checks that its log passed).",
                  original_head=ORIGINAL_HEAD, counts=counts, expected_table_counts={s: sum(1 for r in table if r["state"] == s) for s in (ST_REG, ST_SKIP, ST_ORE)},
                  classification_counts=class_counts, checks=results, parsed_original_rows=dict(
                      item_rows=[dict(line=r["line"], name=r["name"], entries=[[t, e] for t, e in r["entries"]]) for r in ctx["model"]["item_rows"]] if "model" in ctx else [],
                      frame_rows=[dict(line=r["line"], frame=r["frame"], calls=[[c, a] for c, a in r["calls"]]) for r in ctx["model"]["frame_rows"]] if "model" in ctx else []),
                  expected_table=table_json(table),
                  classification=[dict(source=e["source"], line=e["line"], element=e["element"], category=e["category"], neo_id=e["neo_id"], detail=e["detail"],
                                       original_entries=None if e["entries"] is None else [dict(type=t, value=fmt(v)) for t, v in e["entries"]]) for e in cls],
                  skipped=ctx.get("skip_lines", []), mutations=mutations, mutations_detected=f"{detected}/{len(mutations)}", files_read_sha256=reader.hashes)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, r in results.items():
        if r["status"] != "pass":
            print(f"{r['status'].upper()}: {name}: {r['detail'] if isinstance(r['detail'], str) else json.dumps(r['detail'])}")
    for label, m in mutations.items():
        if not m["detected"]:
            print(f"UNDETECTED MUTATION: {label}: {m['first_message']}")
        elif m["kind"] == "code" and not m["semantic_detected"]:
            print(f"MUTATION CAUGHT ONLY BY AN EXACT DIFF: {label}")
    for line in ctx.get("skip_lines", []):
        print(line)
    print(f"report: {REPORT}")
    print(f"Goal22D hazards: {counts['pass']} checks passed; classification " + ", ".join(f"{s} {class_counts[s]}" for s in STATES)
          + f"; {detected}/{len(mutations)} mutations detected"
          + (f"; {counts['pending']} pending" if counts["pending"] else "") + (f"; {counts['fail']} FAILED" if counts["fail"] else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
