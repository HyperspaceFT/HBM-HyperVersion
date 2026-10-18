"""Verify the Goal22C batch (plutonium/MOX/U233 fuel closure) statically against the original: the eleven fuel alloy rows, the four ZIRNOX rod
recipes, the generated recipe and advancement JSONs, the deferred rows, the provider diff, the frozen files, the GameTest sources, the GameTest log
and the built JAR.

Read-only for both worktrees. Writes only build/migration/goal22c/verify/report.json. No game, Gradle, javac or network.

Package under test (production diff against the frozen start in build/migration/goal22c/baseline-files and baseline.json):
- O  Original: the clean 6a11998d checkout; MineralRecipes.java lines 156,157,159,160,162,163,165,166,177,178,419 and RodRecipes.java lines 31,32,33,37
     (+ the addZIRNOXRod helpers :250-257) parsed into (result, count, ingredient multiset); ore names resolved through OreDictManager (the typo
     "nuggetPluonium240" flagged); the parsed rows equal the task-book table; EnumZirnoxType and ZirnoxType have the same constants, order, maxLife, heat.
- R  Recipes: the 15 generated recipe JSONs (shapeless, ingredient multiset, result id/count, rod meta component and no custom data) and their
     advancement JSONs equal the mapped original rows; the 15 ids are new against the start and registered items only.
- P  Provider: NtmRecipeProvider.java is the start copy plus inserted lines only; the inserted lines carry every original line reference; the ids occur once.
- D  Deferred: no LES/lithium rod recipe, no tiny-powder recipe of these materials, no recipe takes a hot waste item as input.
- S  Scope: the changed src/ paths are exactly the provider, FuelClosureGameTests, the stamp and the 30 generated JSONs; the frozen files equal their baseline.
- T  GameTest source: the five FuelClosureGameTests methods, server-side imports only, LF line endings.
- L  (--gametest-log) J (--jar) the GameTest log and the built JAR carry the batch.
- M  In-memory mutations (never written); each must make a check of the expected section fail.

python -B -X utf8 tools/migration/verify_goal22c_fuel.py [--gametest-log PATH] [--jar PATH]
"""
import argparse
import difflib
import functools
import json
import os
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_goal22a_closeout import Checks, guarded, read_text, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT.parent / "Hbm-s-Nuclear-Tech-GIT"
BATCH = ROOT / "build/migration/goal22c"
START = BATCH / "baseline-files"
OUT = BATCH / "verify"
ORIGINAL_HEAD = "6a11998d5852ff3da326f0130357e10431ae3839"

J = "src/main/java/com/hbm/"
GEN = "src/generated/resources/"
PROVIDER = J + "datagen/NtmRecipeProvider.java"
TESTS = J + "gametest/FuelClosureGameTests.java"
ZROD = J + "items/machine/ZirnoxRodItem.java"
NTMITEMS = J + "items/NtmItems.java"
REACTOR = J + "blockentity/machine/ReactorZirnoxBlockEntity.java"
HAZARD = J + "hazard/HazardRegistry.java"
LANG_PROVIDER = J + "datagen/NtmLanguageProvider.java"
PUREX = J + "inventory/recipes/PUREXRecipes.java"
EN = GEN + "assets/hbmsntm/lang/en_us.json"
ZH = "src/main/resources/assets/hbmsntm/lang/zh_cn.json"
STAMP = GEN + ".migration-stamp.json"
RECIPE_DIR = GEN + "data/hbmsntm/recipe/"
ADV_DIR = GEN + "data/hbmsntm/advancement/recipes/misc/"
FROZEN = [REACTOR, ZROD, HAZARD, NTMITEMS, LANG_PROVIDER, PUREX, EN, ZH]
JAR_TESTS = "com/hbm/gametest/FuelClosureGameTests.class"

O_MINERAL = "src/main/java/com/hbm/crafting/MineralRecipes.java"
O_RODS = "src/main/java/com/hbm/crafting/RodRecipes.java"
O_ZROD = "src/main/java/com/hbm/items/machine/ItemZirnoxRod.java"
O_OREDICT = "src/main/java/com/hbm/inventory/OreDictManager.java"

HASH_SKIP = ("__pycache__",)

# The task book (GOAL22C.md C1) as an independent table: (id, original line, result item, count, {ingredient: count}) in NEO ids.
ALLOY = [
    ("billet_thorium_fuel_from_billets", 156, "billet_thorium_fuel", 6, {"billet_th232": 5, "billet_u233": 1}),
    ("billet_thorium_fuel_from_nuggets", 157, "billet_thorium_fuel", 1, {"nugget_th232": 5, "nugget_u233": 1}),
    ("billet_uranium_fuel_from_billets", 159, "billet_uranium_fuel", 6, {"billet_u238": 5, "billet_u235": 1}),
    ("billet_uranium_fuel_from_nuggets", 160, "billet_uranium_fuel", 1, {"nugget_u238": 5, "nugget_u235": 1}),
    ("billet_plutonium_fuel_from_billets", 162, "billet_plutonium_fuel", 3, {"billet_u238": 2, "billet_pu_mix": 1}),
    ("billet_plutonium_fuel_from_nuggets", 163, "billet_plutonium_fuel", 1, {"nugget_pu_mix": 2, "nugget_u238": 4}),
    ("billet_pu_mix_from_billets", 165, "billet_pu_mix", 3, {"billet_pu239": 2, "billet_pu240": 1}),
    ("billet_pu_mix_from_nuggets", 166, "billet_pu_mix", 1, {"nugget_pu239": 4, "nugget_pu240": 2}),
    ("billet_mox_fuel_from_billets", 177, "billet_mox_fuel", 3, {"billet_uranium_fuel": 2, "billet_pu239": 1}),
    ("billet_mox_fuel_from_nuggets", 178, "billet_mox_fuel", 1, {"nugget_pu239": 2, "nugget_uranium_fuel": 4}),
    ("ingot_pu_mix_from_nuggets", 419, "ingot_pu_mix", 1, {"nugget_pu239": 6, "nugget_pu240": 3}),
]
RODS = [
    ("rod_zirnox_mox_fuel", 31, "MOX_FUEL", {"rod_zirnox_empty": 1, "billet_mox_fuel": 2}),
    ("rod_zirnox_plutonium_fuel", 32, "PLUTONIUM_FUEL", {"rod_zirnox_empty": 1, "billet_plutonium_fuel": 2}),
    ("rod_zirnox_u233_fuel", 33, "U233_FUEL", {"rod_zirnox_empty": 1, "billet_u233": 2}),
    ("rod_zirnox_zfb_mox", 37, "ZFB_MOX", {"rod_zirnox_empty": 1, "billet_mox_fuel": 1, "billet_zirconium": 1}),
]
NEW_IDS = [r[0] for r in ALLOY] + [r[0] for r in RODS]
RECIPE_PATHS = [RECIPE_DIR + i + ".json" for i in NEW_IDS]
ADV_PATHS = [ADV_DIR + i + ".json" for i in NEW_IDS]
EXPECTED_DELTA = {PROVIDER, TESTS, STAMP, *RECIPE_PATHS, *ADV_PATHS}
ALLOY_LINES = [r[1] for r in ALLOY]
ROD_LINES = [r[1] for r in RODS]
DEFERRED_TINY_LINES = [158, 161, 164, 167, 420]

# Original item name -> NEO item id (identity apart from case: ModItems.x is NtmItems.X, registered "x").
ITEM_MAP = {n: n for n in (
    "billet_th232", "billet_u233", "nugget_th232", "nugget_u233", "billet_thorium_fuel", "billet_u238", "billet_u235", "billet_uranium_fuel",
    "nugget_u238", "nugget_u235", "billet_plutonium_fuel", "billet_pu_mix", "nugget_pu_mix", "billet_pu239", "billet_pu240", "nugget_pu239",
    "nugget_pu240", "billet_mox_fuel", "nugget_uranium_fuel", "ingot_pu_mix", "rod_zirnox_empty", "rod_zirnox", "billet_zirconium")}
# Ore names the rows use -> the NEO item. Each is resolved through OreDictManager (frame primary name + .nugget()/.billet() registration) and must agree.
ORE_MAP = {"nuggetThorium232": "nugget_th232", "nuggetUranium233": "nugget_u233", "nuggetUranium238": "nugget_u238", "nuggetUranium235": "nugget_u235",
           "nuggetPlutonium239": "nugget_pu239", "nuggetPlutonium240": "nugget_pu240", "billetPlutonium239": "billet_pu239"}
# Upstream typo: the ore name nothing registers; NEO uses the intended item (recorded as upstream-shared).
TYPO_ORES = {"nuggetPluonium240": dict(intended="nuggetPlutonium240", item="nugget_pu240", note="upstream-shared typo: no OreDictManager frame or registration uses this spelling, so the original row is uncraftable; NEO uses the intended nugget_pu240")}
ZIRNOX_CONSTANTS = 11


@functools.lru_cache(maxsize=None)
def jparse(text):
    return json.loads(text)


def jedit(text, edit):
    data = json.loads(text)
    edit(data)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def lf(text):
    return text.replace("\r\n", "\n")


# ---------------------------------------------------------------- original parsing

def split_top(text):
    parts, depth, cur, j, n = [], 0, [], 0, len(text)
    while j < n:
        c = text[j]
        if c in "\"'":
            k = j + 1
            while k < n and text[k] != c:
                k += 2 if text[k] == "\\" else 1
            cur.append(text[j:k + 1])
            j = k + 1
            continue
        if c in "({[":
            depth += 1
        elif c in ")}]":
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


def parse_oredict(text):
    """({frame: [names]}, {(frame, kind): item}) from the DictFrame declarations and the registerOres() chains."""
    frames = {}
    for m in re.finditer(r"public static final DictFrame (\w+)\s*=\s*new DictFrame\((.*?)\);", text):
        frames[m[1]] = re.findall(r'"([^"]+)"', m[2])
    start = text.index("public static void registerOres()")
    registered = {}
    for line in text[start:].split("\n"):
        m = re.match(r"^\t\t(\w+)\s+\.", line)
        if not m or m[1] not in frames:
            continue
        for kind, item in re.findall(r"\.(nugget|billet|ingot)\((\w+)\)", line):
            registered.setdefault((m[1], kind), item)
    return frames, registered


def resolve_ore(frames, registered, ore):
    """(item, frame) when the ore name is the primary name of exactly one frame with that registration, else None."""
    for kind in ("nugget", "billet"):
        if ore.startswith(kind):
            material = ore[len(kind):]
            hits = [f for f, names in frames.items() if names and names[0] == material]
            if len(hits) == 1 and (hits[0], kind) in registered:
                return registered[(hits[0], kind)], hits[0]
    return None


def frame_ore(frames, frame, kind):
    return kind + frames[frame][0]


def token_item(token, frames, registered, notes):
    """One ingredient token of an original Object[] -> (original item name, how it resolved)."""
    token = token.strip()
    m = re.fullmatch(r"ModItems\.(\w+)", token)
    if m:
        return m[1], "item"
    m = re.fullmatch(r'"(\w+)"', token)
    if m:
        ore = m[1]
        hit = resolve_ore(frames, registered, ore)
        if hit:
            return hit[0], f"ore {ore} -> {hit[1]}"
        if ore in TYPO_ORES:
            notes.append(f"{ore}: {TYPO_ORES[ore]['note']}")
            return TYPO_ORES[ore]["item"], f"ore {ore} (unresolved upstream typo) -> {TYPO_ORES[ore]['item']}"
        raise ValueError(f"ore name {ore} does not resolve through OreDictManager")
    m = re.fullmatch(r"(\w+)\.(billet|nugget)\(\)", token)
    if m and m[1] in frames:
        ore = frame_ore(frames, m[1], m[2])
        hit = resolve_ore(frames, registered, ore)
        if hit:
            return hit[0], f"frame {m[1]}.{m[2]}() = {ore} -> {hit[0]}"
        raise ValueError(f"{token} does not resolve")
    raise ValueError(f"unparsed ingredient token {token!r}")


def object_array(line):
    m = re.search(r"new Object\[\]\s*\{(.*)\}\s*\)", line)
    return split_top(m[1]) if m else None


def parse_alloy_line(lines, number, frames, registered):
    line = lines[number - 1].strip()
    if line.startswith("//"):
        raise ValueError(f"MineralRecipes.java:{number} is commented out")
    m = re.search(r"new ItemStack\(ModItems\.(\w+)(?:,\s*(\d+))?\)\s*,\s*new Object\[\]", line)
    tokens = object_array(line)
    if not m or tokens is None:
        raise ValueError(f"MineralRecipes.java:{number} is not a shapeless row: {line[:80]}")
    notes, resolved, how, ores = [], Counter(), [], {}
    for token in tokens:
        item, via = token_item(token, frames, registered, notes)
        resolved[item] += 1
        how.append(via)
        if token.startswith('"'):
            ores[token.strip('"')] = item
    return dict(source="MineralRecipes.java", line=number, result=m[1], count=int(m[2] or 1), ingredients=dict(resolved), via=how, notes=notes, ores=ores, tiny="tiny" in line)


def parse_rod_line(lines, number, helper, frames, registered):
    line = lines[number - 1].strip()
    if line.startswith("//"):
        raise ValueError(f"RodRecipes.java:{number} is commented out")
    notes = []
    m = re.fullmatch(r"addZIRNOXRod\(\s*(.+?)\s*,\s*EnumZirnoxType\.(\w+)\s*\);", line)
    if m:
        arg, rod_type = m[1], m[2]
        kind = "dict" if re.fullmatch(r"[A-Z0-9]+", arg) else "item"
        template = helper[kind]
        arg_token = f"{arg}.billet()" if kind == "dict" else arg
        resolved, how = Counter(), []
        for part in template:
            token = arg_token if part == "BILLET" else part
            item, via = token_item(token, frames, registered, notes)
            resolved[item] += 1
            how.append(via)
        return dict(source="RodRecipes.java", line=number, result="rod_zirnox", count=1, rod_type=rod_type, ingredients=dict(resolved), via=how, notes=notes, ores={})
    m = re.fullmatch(r"CraftingManager\.addShapelessAuto\(new ItemStack\(ModItems\.rod_zirnox, 1, EnumZirnoxType\.(\w+)\.ordinal\(\)\), new Object\[\] \{(.*)\}\);", line)
    if not m:
        raise ValueError(f"RodRecipes.java:{number} is neither addZIRNOXRod nor addShapelessAuto: {line[:80]}")
    resolved, how = Counter(), []
    for token in split_top(m[2]):
        item, via = token_item(token, frames, registered, notes)
        resolved[item] += 1
        how.append(via)
    return dict(source="RodRecipes.java", line=number, result="rod_zirnox", count=1, rod_type=m[1], ingredients=dict(resolved), via=how, notes=notes, ores={})


def parse_helpers(lines):
    """The two addZIRNOXRod helper bodies (:250-257) as ingredient templates; BILLET marks the argument slot."""
    out = {}
    text = "\n".join(lines[249:257])
    plain = re.search(r"addZIRNOXRod\(Item billet, EnumZirnoxType num\)\s*\{\s*CraftingManager\.addShapelessAuto\(new ItemStack\(ModItems\.rod_zirnox, 1, num\.ordinal\(\)\), new Object\[\] \{ ModItems\.rod_zirnox_empty, billet, billet \}\);", text)
    dict_ = re.search(r"addZIRNOXRod\(DictFrame mat, EnumZirnoxType num\)\s*\{\s*CraftingManager\.addShapelessAuto\(new ItemStack\(ModItems\.rod_zirnox, 1, num\.ordinal\(\)\), new Object\[\] \{ ModItems\.rod_zirnox_empty, mat\.billet\(\), mat\.billet\(\) \}\);", text)
    if not plain or not dict_:
        raise ValueError("the addZIRNOXRod helpers at RodRecipes.java:250-257 do not have the expected shape")
    out["item"] = ["ModItems.rod_zirnox_empty", "BILLET", "BILLET"]
    out["dict"] = ["ModItems.rod_zirnox_empty", "BILLET", "BILLET"]
    return out


def parse_enum(text, name_pattern):
    """[(name, maxLife, heat, breeding)] of the ZIRNOX enum body in declaration order."""
    m = re.search(name_pattern + r"\s*\{(.*?);", text, re.S)
    if not m:
        raise ValueError("enum not found")
    out = []
    for c in re.finditer(r"(\w+)\(\s*([\d_]+)\s*,\s*(\d+)\s*(?:,\s*(true|false))?\)", m[1]):
        out.append((c[1], int(c[2].replace("_", "")), int(c[3]), c[4] == "true"))
    return out


# ---------------------------------------------------------------- inputs

class State:
    """The mutable view of the NEO tree the checks read: file texts (None when absent) and sha256 of every src file."""

    def __init__(self, texts, hashes):
        self.texts, self.hashes = texts, hashes

    def copy(self):
        return State(dict(self.texts), dict(self.hashes))

    def set(self, path, text):
        self.texts[path] = text
        self.hashes[path] = sha(text.encode("utf-8"))

    def drop(self, path):
        self.texts[path] = None
        self.hashes.pop(path, None)


class Inputs:
    pass


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", "-c", "safe.directory=" + ORIGINAL.as_posix(), *args], cwd=ORIGINAL).decode("utf-8")


def hash_tree():
    hashes = {}
    for base, dirs, names in os.walk(ROOT / "src"):
        dirs[:] = [d for d in dirs if d not in HASH_SKIP]
        for name in names:
            path = Path(base) / name
            hashes[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return hashes


def collect():
    inp = Inputs()
    baseline = json.loads((BATCH / "baseline.json").read_text(encoding="utf-8"))
    inp.baseline, inp.base_files, inp.copied = baseline, baseline["files"], baseline["copied_scope"]
    inp.start = {p: read_text(START / p) for p in (PROVIDER, EN)}
    inp.start_hash_ok = {p: sha((START / p).read_bytes()) == inp.base_files.get(p) for p in inp.copied if (START / p).is_file()}
    try:
        head = git("rev-parse", "HEAD").strip()
        status = git("status", "--porcelain=v1")
        inp.original_ok = (head == ORIGINAL_HEAD and status == "", head, status)
    except Exception as error:  # noqa: BLE001
        inp.original_ok = (False, repr(error), "")
    inp.parse_error = None
    inp.rows, inp.helper, inp.original_enum, inp.deferred, inp.oredict_facts = [], None, [], {}, {}
    try:
        mineral = lf(read_text(ORIGINAL / O_MINERAL)).split("\n")
        rods = lf(read_text(ORIGINAL / O_RODS)).split("\n")
        oredict = lf(read_text(ORIGINAL / O_OREDICT))
        frames, registered = parse_oredict(oredict)
        inp.helper = parse_helpers(rods)
        for number in ALLOY_LINES:
            inp.rows.append(parse_alloy_line(mineral, number, frames, registered))
        for number in ROD_LINES:
            inp.rows.append(parse_rod_line(rods, number, inp.helper, frames, registered))
        inp.original_enum = parse_enum(lf(read_text(ORIGINAL / O_ZROD)), r"enum EnumZirnoxType")
        inp.deferred = dict(
            les_rod=rods[34].strip(), lithium_rod=rods[35].strip(),
            tiny_lines={n: ("tiny" in mineral[n - 1]) for n in DEFERRED_TINY_LINES},
            typo_spellings_in_oredict=oredict.count("Pluonium"))
        inp.oredict_facts = dict(frames={f: frames[f] for f in ("U233", "U235", "U238", "TH232", "PU239", "PU240", "ZR") if f in frames},
                                 typo_resolves=resolve_ore(frames, registered, "nuggetPluonium240") is not None,
                                 intended_resolves=resolve_ore(frames, registered, "nuggetPlutonium240"))
    except Exception as error:  # noqa: BLE001
        inp.parse_error = repr(error)
    texts = {}
    for path in (PROVIDER, TESTS, ZROD, NTMITEMS, *ADV_PATHS):
        texts[path] = read_text(ROOT / path) if (ROOT / path).is_file() else None
    for p in (ROOT / RECIPE_DIR).glob("*.json"):
        texts[p.relative_to(ROOT).as_posix()] = read_text(p)
    for path in RECIPE_PATHS:
        texts.setdefault(path, None)
    inp.test_annotations = sum(len(re.findall(r"@GameTest\(", read_text(p))) for p in sorted((ROOT / J / "gametest").glob("*.java")))
    return inp, State(texts, hash_tree())


# ---------------------------------------------------------------- O original

def mapped_rows(inp):
    """The parsed original rows with NEO ids: (id from the task book by line, result, count, {ingredient: n}, rod type)."""
    out = {}
    for row in inp.rows:
        ing = {}
        for item, n in row["ingredients"].items():
            ing[ITEM_MAP.get(item, "?" + item)] = n
        out[(row["source"], row["line"])] = dict(result=ITEM_MAP.get(row["result"], "?" + row["result"]), count=row["count"], ingredients=ing, rod_type=row.get("rod_type"))
    return out


def o_original(ck, inp, st):
    ok, head, status = inp.original_ok
    ck("O.original-head-clean", ok, f"the original is at {ORIGINAL_HEAD[:8]} with a clean worktree", (head, status))
    ck("O.start-copies-match", all(inp.start_hash_ok.values()) and bool(inp.start_hash_ok), "every baseline-files copy hashes to its baseline.json entry", [p for p, v in inp.start_hash_ok.items() if not v])
    ck("O.parsed", inp.parse_error is None and len(inp.rows) == len(ALLOY) + len(RODS), f"the original parses into {len(ALLOY) + len(RODS)} rows (11 alloy rows, 4 rod rows)", inp.parse_error or len(inp.rows))
    if inp.parse_error:
        return
    mapped = mapped_rows(inp)
    bad = []
    for rid, line, result, count, ingredients in ALLOY:
        got = mapped.get(("MineralRecipes.java", line))
        if got != dict(result=result, count=count, ingredients=ingredients, rod_type=None):
            bad.append((rid, line, got))
    for rid, line, rod_type, ingredients in RODS:
        got = mapped.get(("RodRecipes.java", line))
        if got != dict(result="rod_zirnox", count=1, ingredients=ingredients, rod_type=rod_type):
            bad.append((rid, line, got))
    ck("O.rows-equal-task-book", not bad, "every parsed original row equals the task-book table under the explicit item/ore mapping", bad[:3])
    ck("O.items-explicitly-mapped", not any(i.startswith("?") for r in mapped.values() for i in (*r["ingredients"], r["result"])), "every original item name is in the explicit ITEM_MAP", [r for r in mapped.values() if any(i.startswith("?") for i in r["ingredients"])][:2])
    neo_items = st.texts.get(NTMITEMS) or ""
    missing = sorted({i for i in ITEM_MAP.values() if not re.search(r'"' + re.escape(i) + r'"', neo_items)})
    ck("O.neo-items-registered", not missing, "every mapped NEO item id is registered in NtmItems.java", missing)
    # ore names: the explicit table agrees with OreDictManager; the typo is flagged and unresolvable
    notes = [n for r in inp.rows for n in r["notes"]]
    facts = inp.oredict_facts
    ck("O.typo-flagged", any("nuggetPluonium240" in n for n in notes) and facts.get("typo_resolves") is False and inp.deferred["typo_spellings_in_oredict"] == 0 and facts.get("intended_resolves") and facts["intended_resolves"][0] == "nugget_pu240",
       "nuggetPluonium240 is the only unresolved ore name (no OreDictManager spelling), flagged as an upstream typo and mapped to nugget_pu240", (notes, facts))
    ore_items = {}
    for row in inp.rows:
        ore_items.update(row["ores"])
    ore_bad = [ore for ore, item in ore_items.items() if ore not in TYPO_ORES and ORE_MAP.get(ore) != item]
    ck("O.ore-names-through-oredict", not ore_bad and set(ORE_MAP) <= set(ore_items) and set(ore_items) - set(ORE_MAP) == set(TYPO_ORES),
       "every ore name the rows use resolves through OreDictManager to the item of the explicit ORE_MAP (the typo aside)", (ore_bad, sorted(ore_items.items())))
    # the two enums agree
    neo_enum = parse_enum(st.texts.get(ZROD) or "", r"enum ZirnoxType")
    ck("O.enum-parity", len(inp.original_enum) == ZIRNOX_CONSTANTS and [(n, l, h, b) for n, l, h, b in neo_enum] == inp.original_enum,
       "EnumZirnoxType and ZirnoxType have the same 11 constants in the same order with the same maxLife, heat and breeding flag", (inp.original_enum, neo_enum))
    want = {"MOX_FUEL": (165000, 75), "PLUTONIUM_FUEL": (175000, 65), "U233_FUEL": (150000, 100), "ZFB_MOX": (50000, 35)}
    got = {n: (l, h) for n, l, h, _ in neo_enum if n in want}
    ck("O.enum-four-types", got == want, "MOX_FUEL 165,000/75, PLUTONIUM_FUEL 175,000/65, U233_FUEL 150,000/100, ZFB_MOX 50,000/35 in NEO", got)
    names = [n for n, *_ in inp.original_enum]
    ck("O.deferred-rows-still-deferred", inp.deferred["les_rod"].startswith("addZIRNOXRod(ModItems.billet_les") and "LI.ingot()" in inp.deferred["lithium_rod"] and all(inp.deferred["tiny_lines"].values()) and names.index("LES_FUEL") == 8 and names.index("LITHIUM") == 9,
       "the original LES rod (:35) and lithium rod (:36) are as the task book defers them; the five 'tiny' rows (ore prefix 'tiny' is the nugget alias, "
       "OreDictManager.java:839) duplicate the nugget rows and are not ported", inp.deferred)


# ---------------------------------------------------------------- R recipes

def ingredient_items(recipe):
    out = Counter()
    for entry in recipe.get("ingredients", []):
        out[entry.get("item", "?") if isinstance(entry, dict) else "?"] += 1
    return out


def r_recipes(ck, inp, st):
    neo_items = st.texts.get(NTMITEMS) or ""
    problems, unknown = [], []
    for rid, line, result, count, ingredients in ALLOY:
        text = st.texts.get(RECIPE_DIR + rid + ".json")
        if text is None:
            problems.append((rid, "missing"))
            continue
        js = jparse(text)
        want = Counter({"hbmsntm:" + k: v for k, v in ingredients.items()})
        if set(js) != {"type", "category", "ingredients", "result"} or js.get("type") != "minecraft:crafting_shapeless" or js.get("category") != "misc":
            problems.append((rid, "type/category/keys", sorted(js)))
        elif ingredient_items(js) != want:
            problems.append((rid, "ingredients", dict(ingredient_items(js)), dict(want)))
        elif js["result"] != {"count": count, "id": "hbmsntm:" + result}:
            problems.append((rid, "result", js["result"]))
        for item in [*ingredient_items(js), js.get("result", {}).get("id")]:
            if not re.search(r'"' + re.escape(str(item).split(":")[-1]) + r'"', neo_items):
                unknown.append((rid, item))
    ck("R.alloy-recipes", not problems, "the 11 alloy recipe JSONs are crafting_shapeless/misc with the original ingredient multiset and result id and count (no components)", problems[:3])
    rod_problems = []
    ordinals = {n: i for i, (n, *_) in enumerate(parse_enum(st.texts.get(ZROD) or "", r"enum ZirnoxType"))}
    for rid, line, rod_type, ingredients in RODS:
        text = st.texts.get(RECIPE_DIR + rid + ".json")
        if text is None:
            rod_problems.append((rid, "missing"))
            continue
        js = jparse(text)
        want = Counter({"hbmsntm:" + k: v for k, v in ingredients.items()})
        if set(js) != {"type", "category", "ingredients", "result"} or js.get("type") != "minecraft:crafting_shapeless" or js.get("category") != "misc":
            rod_problems.append((rid, "type/category/keys", sorted(js)))
        elif ingredient_items(js) != want:
            rod_problems.append((rid, "ingredients", dict(ingredient_items(js)), dict(want)))
        elif js["result"] != {"components": {"hbmsntm:meta": ordinals.get(rod_type, -1)}, "count": 1, "id": "hbmsntm:rod_zirnox"}:
            rod_problems.append((rid, "result", js["result"]))
        for item in ingredient_items(js):
            if not re.search(r'"' + re.escape(item.split(":")[-1]) + r'"', neo_items):
                unknown.append((rid, item))
    ck("R.rod-recipes", not rod_problems, "the 4 rod recipe JSONs are crafting_shapeless/misc with the original ingredients and the result rod_zirnox x1 with exactly the meta component = ZirnoxType ordinal (no custom_data, no life)", rod_problems[:3])
    ck("R.items-registered", not unknown, "every item id the 15 recipes name is registered in NtmItems.java", unknown[:3])
    adv_problems = []
    for rid in NEW_IDS:
        text = st.texts.get(ADV_DIR + rid + ".json")
        if text is None:
            adv_problems.append((rid, "missing"))
            continue
        js = jparse(text)
        criteria = js.get("criteria", {})
        own = criteria.get("has_the_recipe")
        others = {k: v for k, v in criteria.items() if k != "has_the_recipe"}
        recipe_json = jparse(st.texts[RECIPE_DIR + rid + ".json"]) if st.texts.get(RECIPE_DIR + rid + ".json") else {}
        ingredient_ids = set(ingredient_items(recipe_json))
        ok = (js.get("parent") == "minecraft:recipes/root" and own == {"conditions": {"recipe": "hbmsntm:" + rid}, "trigger": "minecraft:recipe_unlocked"}
              and len(others) == 1 and next(iter(others.values())).get("trigger") == "minecraft:inventory_changed"
              and js.get("requirements") == [["has_the_recipe", next(iter(others))]] and js.get("rewards") == {"recipes": ["hbmsntm:" + rid]})
        triggered = [i["items"] for v in others.values() for i in v.get("conditions", {}).get("items", [])]
        if not ok or not triggered or not all(t in ingredient_ids for t in triggered):
            adv_problems.append((rid, js.get("rewards"), triggered))
    ck("R.advancements", not adv_problems, "the 15 advancement JSONs unlock exactly their own recipe on has_the_recipe or an inventory_changed of one of its ingredients", adv_problems[:3])
    base_recipe_ids = {p for p in inp.base_files if p.startswith(RECIPE_DIR)}
    live_recipe_ids = {p for p, t in st.texts.items() if p.startswith(RECIPE_DIR) and t is not None}
    gained = live_recipe_ids - base_recipe_ids
    ck("R.ids-new-no-collision", gained == set(RECIPE_PATHS) and not (set(RECIPE_PATHS) & base_recipe_ids) and len(set(NEW_IDS)) == len(NEW_IDS),
       "the generated recipe directory gained exactly the 15 ids against the start; none existed before (no collision with addBilletRecipe/addNuggetCrafting ids)", dict(extra=sorted(gained - set(RECIPE_PATHS))[:5], missing=sorted(set(RECIPE_PATHS) - gained)[:5]))
    ck("R.no-recipe-removed", base_recipe_ids <= set(st.hashes), "no recipe JSON of the start was removed", sorted(base_recipe_ids - set(st.hashes))[:3])


# ---------------------------------------------------------------- P provider

def p_provider(ck, inp, st):
    start, live = inp.start[PROVIDER].split("\n"), (st.texts.get(PROVIDER) or "").split("\n")
    ops = [(t, i1, i2, j1, j2) for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, start, live, autojunk=False).get_opcodes() if t != "equal"]
    inserted = [line for t, i1, i2, j1, j2 in ops if t == "insert" for line in live[j1:j2]]
    removed = [t for t, *_ in ops if t != "insert"]
    ck("P.insert-only", not removed and bool(inserted), "NtmRecipeProvider.java differs from the start copy by inserted lines only (no removed or changed line)", dict(ops=[(t, i1, i2, j1, j2) for t, i1, i2, j1, j2 in ops if t != "insert"][:3]))
    text = "\n".join(inserted)
    missing = [f":{n}" for n in ALLOY_LINES if not re.search(r"//\s*:" + str(n) + r"\b", text)]
    missing += [f"RodRecipes.java:{n}" for n in ROD_LINES if not re.search(r"RodRecipes\.java:" + str(n) + r"\b", text)]
    ck("P.line-references", not missing, "the inserted lines carry the original line reference of every row (MineralRecipes :156..:419, RodRecipes.java:31,32,33,37)", missing)
    live_text = "\n".join(live)
    start_text = "\n".join(start)
    bad_ids = [i for i in NEW_IDS if live_text.count(f'"{i}"') != 1 or start_text.count(f'"{i}"') != 0]
    ck("P.ids-once", not bad_ids, "each of the 15 recipe ids occurs once in the provider and not in the start copy", bad_ids)
    call = [i for i, line in enumerate(live) if line.strip() == "registerFuelAlloyRecipes(recipeOutput);"]
    after = live[call[0] - 1].strip() if call else None
    definition = [i for i, line in enumerate(live) if "private void registerFuelAlloyRecipes(RecipeOutput recipeOutput)" in line]
    ck("P.call-after-billets", len(call) == 1 and after == "registerBilletRecipes(recipeOutput);" and len(definition) == 1,
       "registerFuelAlloyRecipes is defined once and called once, right after registerBilletRecipes", (call, after, definition))
    ck("P.crlf", "\r\n" in (st.texts.get(PROVIDER) or "") and (st.texts.get(PROVIDER) or "").count("\r\n") == (st.texts.get(PROVIDER) or "").count("\n"), "NtmRecipeProvider.java keeps CRLF line endings only")
    rod_blocks = len(re.findall(r"MetaHelper\.newStack\(NtmItems\.ROD_ZIRNOX\.get\(\), 1, ZirnoxType\.(?:MOX_FUEL|PLUTONIUM_FUEL|U233_FUEL|ZFB_MOX)\.ordinal\(\)\)", text))
    code = "\n".join(re.sub(r"//.*$", "", line) for line in inserted)
    ck("P.rod-output-form", rod_blocks == 4 and not re.search(r"life|custom_?data|CustomData", code, re.I), "the four inserted rod recipes use MetaHelper.newStack(ROD_ZIRNOX, 1, type.ordinal()) and the inserted code sets no life or custom data", rod_blocks)


# ---------------------------------------------------------------- D deferred

WASTE_IDS = {"hbmsntm:waste_" + n for n in ("natural_uranium", "uranium", "thorium", "mox", "plutonium", "u233", "u235", "schrabidium", "zfb_mox")}
TINY_TOKENS = ("u238", "u235", "u233", "th232", "pu239", "pu240", "pu_mix", "thorium", "plutonium")


def recipe_inputs(js, key=None):
    """Every (item id, components or None) an ingredient position of the recipe names; the result is skipped."""
    out = []
    if isinstance(js, dict):
        for k, v in js.items():
            if k in ("result", "results", "pattern"):
                continue
            if k == "item" and isinstance(v, str):
                out.append((v, js.get("components")))
            elif k == "items":
                for item in ([v] if isinstance(v, str) else v if isinstance(v, list) else []):
                    if isinstance(item, str):
                        out.append((item, js.get("components")))
                out.extend(recipe_inputs(v) if isinstance(v, (dict, list)) else [])
            else:
                out.extend(recipe_inputs(v))
    elif isinstance(js, list):
        for x in js:
            out.extend(recipe_inputs(x))
    return out


def d_deferred(ck, inp, st):
    les_lithium, tiny, hot, malformed = [], [], [], []
    for path, text in st.texts.items():
        if not path.startswith(RECIPE_DIR) or text is None:
            continue
        try:
            js = jparse(text)
        except ValueError:
            malformed.append(path)
            continue
        result = js.get("result") if isinstance(js.get("result"), dict) else {}
        if result.get("id") == "hbmsntm:rod_zirnox" and result.get("components", {}).get("hbmsntm:meta") in (8, 9):
            les_lithium.append(path)
        for item, components in recipe_inputs(js):
            name = item.split(":")[-1]
            if name.endswith("_tiny") and any(t in name for t in TINY_TOKENS):
                tiny.append((path, item))
            if item in WASTE_IDS and (components is None or (isinstance(components, dict) and components.get("hbmsntm:meta") == 1)):
                hot.append((path, item, components))
    ck("D.no-les-lithium-rod", not les_lithium, "no recipe yields rod_zirnox with meta 8 (LES_FUEL) or 9 (LITHIUM)", les_lithium)
    ck("D.no-tiny-powder-recipe", not tiny, "no recipe takes a tiny powder of U238/U235/U233/Th232/Pu239/Pu240/Pu mix/thorium/plutonium", tiny[:3])
    ck("D.no-hot-waste-input", not hot, "no recipe in the generated tree takes a waste_* item that can match a hot (META 1) stack", hot[:3])
    ck("D.recipes-parse", not malformed, "every recipe JSON parses", malformed[:3])
    new_inputs = [(i, item) for i in NEW_IDS for item, _ in recipe_inputs(jparse(st.texts[RECIPE_DIR + i + ".json"]))] if all(st.texts.get(p) for p in RECIPE_PATHS) else []
    ck("D.new-rows-clean", bool(new_inputs) and not any("tiny" in item or "billet_les" in item or "waste_" in item or "lithium" in item for _, item in new_inputs),
       "none of the 15 new recipes takes a tiny powder, billet_les, lithium or waste item", [x for x in new_inputs if any(t in x[1] for t in ("tiny", "billet_les", "waste_", "lithium"))][:3])


# ---------------------------------------------------------------- S scope

def s_scope(ck, inp, st):
    base, cur = inp.base_files, st.hashes
    changed = {p for p in cur if p.startswith("src/") and base.get(p) != cur[p]} | {p for p in base if p.startswith("src/") and p not in cur}
    ck("S.src-delta-exact", changed == EXPECTED_DELTA, "the src/ paths that changed or were added are exactly the provider, FuelClosureGameTests, the stamp and the 30 generated JSONs",
       dict(unexpected=sorted(changed - EXPECTED_DELTA)[:5], missing=sorted(EXPECTED_DELTA - changed)[:5]))
    ck("S.frozen-files-unchanged", all(p in base and cur.get(p) == base[p] for p in FROZEN),
       "ReactorZirnoxBlockEntity, ZirnoxRodItem, HazardRegistry, NtmItems, NtmLanguageProvider, PUREXRecipes, en_us.json and zh_cn.json equal their baseline hash (no language key added)",
       [p for p in FROZEN if cur.get(p) != base.get(p)])
    gametests = sorted(p for p in base if p.startswith(J + "gametest/"))
    ck("S.existing-gametests-unchanged", bool(gametests) and all(cur.get(p) == base[p] for p in gametests), "every existing gametest source equals its baseline hash", [p for p in gametests if cur.get(p) != base[p]])
    ck("S.new-files-only-expected", all(p in base for p in cur if p.startswith("src/") and p not in EXPECTED_DELTA), "no src/ file outside the expected set is new")


# ---------------------------------------------------------------- T GameTest source

TEST_METHODS = ["fuel_alloy_recipes", "zirnox_rod_recipes", "zirnox_new_rods_heat_and_life", "zirnox_new_rods_deplete", "fuel_closure_purex_to_rods"]


def t_tests(ck, inp, st):
    text = st.texts.get(TESTS)
    ck("T.exists", text is not None, "FuelClosureGameTests.java exists")
    if text is None:
        return
    methods = re.findall(r"@GameTest\([^)]*\)\s*public static void (\w+)\(GameTestHelper", text)
    ck("T.methods", methods == TEST_METHODS and text.count("@GameTest(") == len(TEST_METHODS), f"the class has exactly the {len(TEST_METHODS)} @GameTest methods", methods)
    ck("T.holder", "@GameTestHolder(NuclearTechMod.MODID)" in text and "@PrefixGameTestTemplate(false)" in text and 'TEMPLATE = "gametest_empty"' in text, "@GameTestHolder(MODID), @PrefixGameTestTemplate(false) and the gametest_empty template")
    client = re.findall(r"^import (?:net\.minecraft\.client|com\.hbm\.render|com\.hbm\.main\.NuclearTechModClient|com\.hbm\.main\.ClientProxy)[\w.]*;", text, re.M)
    ck("T.server-only", not client, "the class imports no client class", client)
    ck("T.lf", "\r" not in text, "FuelClosureGameTests.java uses LF line endings")
    ck("T.passed-lines", "[hbm-fuel] {} passed" in text and all(f'passed("{m}")' in text for m in TEST_METHODS), "every test ends with its [hbm-fuel] passed log line")
    ck("T.no-hot-input-and-ids", all(i in text for i in ("billet_u233_from_6_nugget_u233", "purex.zirnoxnu", "purex.zirnoxthmeu")), "the closure test uses the PUREX rows and the billet_u233_from_6_nugget_u233 recipe")


# ---------------------------------------------------------------- L log and J jar

def log_suite(ck, inp, text, name):
    match = re.search(r"All (\d+) required tests passed", text)
    ck("L.all-passed", bool(match) and int(match[1]) == inp.test_annotations, f"{name} contains `All {inp.test_annotations} required tests passed` (N = @GameTest( annotations under gametest/)", (match and match[0], inp.test_annotations))
    ck("L.no-failed-summary", not re.search(r"required tests failed|optional tests failed", text), "the log has no `required/optional tests failed` summary line")
    ck("L.no-failed-line", not re.search(r"\bfailed!|\(optional\) .* failed", text), "the log has no `<test> failed!` or `(optional) <test> failed` line")
    ck("L.no-class-errors", "NoClassDefFoundError" not in text and "invalid dist" not in text, "the log has no NoClassDefFoundError or `invalid dist`")
    ck("L.build-successful", "BUILD SUCCESSFUL" in text, "the log ends in BUILD SUCCESSFUL")
    missing = [n for n in TEST_METHODS if not re.search(r"\[hbm-fuel\] " + re.escape(n) + r" passed", text)]
    ck("L.every-fuel-test", not missing, f"every FuelClosureGameTests method name appears in the log as `[hbm-fuel] <name> passed` ({len(TEST_METHODS)})", missing)
    bad = [ln[:200] for ln in text.split("\n") if "hbm-fuel" in ln and re.search(r"fail|Exception|ERROR", ln, re.I)]
    ck("L.fuel-lines-clean", not bad, "no [hbm-fuel] log line reports a failure", bad[:3])
    return dict(all_passed=match and match[0], fuel_pass_lines=len(re.findall(r"\[hbm-fuel\] \w+ passed", text)))


def read_jar(path):
    wanted = {p[len(GEN):] for p in RECIPE_PATHS + ADV_PATHS} | {JAR_TESTS}
    entries = {}
    with zipfile.ZipFile(path) as jar:
        names = set(jar.namelist())
        for name in wanted:
            entries[name] = jar.read(name) if name in names else None
    return entries


def jar_suite(ck, inp, st, entries):
    for source in RECIPE_PATHS + ADV_PATHS:
        name = source[len(GEN):]
        data = entries.get(name)
        on_disk = (ROOT / source).read_bytes() if (ROOT / source).is_file() else None
        ck(f"J.bytes-{Path(name).parent.name}-{Path(name).name}", data is not None and data == on_disk, f"{name} is in the JAR with bytes equal to {source}", "missing" if data is None else "bytes differ")
    data = entries.get(JAR_TESTS)
    ck("J.class-fuel-closure-tests", data is not None and b"[hbm-fuel] {} passed" in data and all(m.encode() in data for m in TEST_METHODS), f"{JAR_TESTS} is in the JAR and its constant pool carries the test names (string presence only)", "missing" if data is None else "strings missing")


# ---------------------------------------------------------------- suite and mutations

def static_suite(inp, st):
    ck = Checks()
    guarded(ck, "O", o_original, inp, st)
    guarded(ck, "R", r_recipes, inp, st)
    guarded(ck, "P", p_provider, inp, st)
    guarded(ck, "D", d_deferred, inp, st)
    guarded(ck, "S", s_scope, inp, st)
    guarded(ck, "T", t_tests, inp, st)
    return ck


def rep1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def edit(path, fn):
    return lambda st: st.set(path, fn(st.texts[path]))


def jedit_path(path, fn):
    return edit(path, lambda t: jedit(t, fn))


def hash_only(path):
    def go(st):
        st.hashes[path] = "0" * 64
    return go


def add_recipe(name, data):
    def go(st):
        st.set(RECIPE_DIR + name + ".json", json.dumps(data, indent=2) + "\n")
    return go


def mutations():
    """(label, expected failing-section prefix, function(State))."""
    thorium = RECIPE_DIR + "billet_thorium_fuel_from_billets.json"
    nuggets = RECIPE_DIR + "billet_plutonium_fuel_from_nuggets.json"
    pu_mix = RECIPE_DIR + "billet_pu_mix_from_nuggets.json"
    moxrod = RECIPE_DIR + "rod_zirnox_mox_fuel.json"
    u233rod = RECIPE_DIR + "rod_zirnox_u233_fuel.json"
    waste_input = {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"item": "hbmsntm:waste_mox"}], "result": {"count": 1, "id": "minecraft:stick"}}
    return [
        ("ingredient_count_changed", "R.", jedit_path(thorium, lambda d: d["ingredients"].pop())),
        ("result_count_changed", "R.", jedit_path(nuggets, lambda d: d["result"].__setitem__("count", 2))),
        ("nugget_pu240_swapped_to_unknown_item", "R.", edit(pu_mix, lambda t: t.replace("hbmsntm:nugget_pu240", "hbmsntm:nugget_pluonium240"))),
        ("recipe_row_dropped", "R.", lambda st: st.drop(RECIPE_DIR + "billet_mox_fuel_from_nuggets.json")),
        ("advancement_dropped", "R.", lambda st: st.drop(ADV_DIR + "billet_uranium_fuel_from_billets.json")),
        ("rod_output_gets_life_tag", "R.", jedit_path(moxrod, lambda d: d["result"]["components"].__setitem__("minecraft:custom_data", {"life": 0}))),
        ("rod_meta_wrong", "R.", jedit_path(u233rod, lambda d: d["result"]["components"].__setitem__("hbmsntm:meta", 5))),
        ("recipe_type_changed", "R.", edit(thorium, lambda t: t.replace("crafting_shapeless", "crafting_shaped"))),
        ("provider_removed_line", "P.", edit(PROVIDER, lambda t: rep1(t, "        // :163: two reactor-grade plutonium nuggets and four uranium-238 nuggets make one plutonium fuel billet.\r\n", ""))),
        ("provider_changed_existing_line", "P.", edit(PROVIDER, lambda t: rep1(t, "registerBilletRecipes(recipeOutput);\r\n        registerFuelAlloyRecipes", "registerBilletRecipes(recipeOutput) ;\r\n        registerFuelAlloyRecipes"))),
        ("provider_line_reference_missing", "P.", edit(PROVIDER, lambda t: rep1(t, "// :419:", "// :418:"))),
        ("provider_rod_reference_missing", "P.", edit(PROVIDER, lambda t: rep1(t, "Original RodRecipes.java:32:", "Original RodRecipes.java:99:"))),
        ("provider_call_moved", "P.", edit(PROVIDER, lambda t: rep1(rep1(t, "        registerFuelAlloyRecipes(recipeOutput);\r\n", ""), "registerBilletRecipes(recipeOutput);\r\n", "registerBilletRecipes(recipeOutput);\r\n        registerPowderSmeltingRecipes(recipeOutput);\r\n        registerFuelAlloyRecipes(recipeOutput);\r\n"))),
        ("frozen_reactor_hash_changed", "S.", hash_only(REACTOR)),
        ("frozen_nuntmitems_hash_changed", "S.", hash_only(NTMITEMS)),
        ("frozen_en_us_hash_changed", "S.", hash_only(EN)),
        ("extra_src_file_added", "S.", lambda st: st.set(J + "gametest/ExtraGameTests.java", "// x\n")),
        ("enum_heat_changed", "O.", edit(ZROD, lambda t: rep1(t, "MOX_FUEL(165_000, 75)", "MOX_FUEL(165_000, 76)"))),
        ("enum_order_swapped", "O.", edit(ZROD, lambda t: rep1(rep1(rep1(t, "MOX_FUEL(165_000, 75),", "@@A"), "PLUTONIUM_FUEL(175_000, 65),", "MOX_FUEL(165_000, 75),"), "@@A", "PLUTONIUM_FUEL(175_000, 65),"))),
        ("les_rod_recipe_added", "D.", add_recipe("rod_zirnox_les_fuel", {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"item": "hbmsntm:rod_zirnox_empty"}], "result": {"components": {"hbmsntm:meta": 8}, "count": 1, "id": "hbmsntm:rod_zirnox"}})),
        ("tiny_powder_row_added", "D.", add_recipe("billet_uranium_fuel_from_tiny", {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"item": "hbmsntm:powder_u238_tiny"}] * 5 + [{"item": "hbmsntm:powder_u235_tiny"}], "result": {"count": 1, "id": "hbmsntm:billet_uranium_fuel"}})),
        ("hot_waste_input_added", "D.", add_recipe("zz_waste_input", waste_input)),
        ("hot_waste_component_input_added", "D.", add_recipe("zz_hot_waste_input", {"type": "minecraft:crafting_shapeless", "category": "misc", "ingredients": [{"type": "neoforge:components", "items": "hbmsntm:waste_mox", "components": {"hbmsntm:meta": 1}}], "result": {"count": 1, "id": "minecraft:stick"}})),
        ("test_method_removed", "T.", edit(TESTS, lambda t: rep1(t, "public static void zirnox_new_rods_deplete(", "public static void zirnox_new_rods_depleteX("))),
        ("test_client_import_added", "T.", edit(TESTS, lambda t: rep1(t, "import net.minecraft.core.BlockPos;", "import net.minecraft.client.Minecraft;\nimport net.minecraft.core.BlockPos;"))),
        ("test_crlf", "T.", edit(TESTS, lambda t: t.replace("\n", "\r\n"))),
    ]


def run_mutations(inp, st, base_failed):
    results = {}
    for label, prefix, fn in mutations():
        mutated = st.copy()
        fn(mutated)
        failed = static_suite(inp, mutated).failed()
        crashes = [f for f in failed if f.endswith(".crash")]
        real = [f for f in failed if f not in base_failed and not f.endswith(".crash")]
        results[label] = dict(expected_section=prefix, failed=real[:8], crashes=crashes, detected=any(f.startswith(prefix) for f in real))
    return results


def log_mutations():
    return [
        ("log_count_changed", "L.", lambda t: re.sub(r"All \d+ required tests passed", "All 94 required tests passed", t)),
        ("log_fuel_test_line_dropped", "L.", lambda t: t.replace("[hbm-fuel] zirnox_new_rods_deplete passed", "")),
        ("log_failed_line_added", "L.", lambda t: t + "\nfuel_closure_purex_to_rods failed!\n"),
        ("log_not_successful", "L.", lambda t: t.replace("BUILD SUCCESSFUL", "BUILD FAILED")),
    ]


def run_log_mutations(inp, text, name, base_failed):
    results = {}
    for label, prefix, fn in log_mutations():
        ck = Checks()
        log_suite(ck, inp, fn(text), name)
        real = [f for f in ck.failed() if f not in base_failed]
        results[label] = dict(expected_section=prefix, failed=real[:8], crashes=[], detected=any(f.startswith(prefix) for f in real))
    return results


def jar_mutations():
    return [
        ("jar_recipe_bytes_differ", "J.", lambda e: {**e, RECIPE_PATHS[0][len(GEN):]: (e[RECIPE_PATHS[0][len(GEN):]] or b"") + b" "}),
        ("jar_advancement_missing", "J.", lambda e: {**e, ADV_PATHS[3][len(GEN):]: None}),
        ("jar_tests_class_missing", "J.", lambda e: {**e, JAR_TESTS: None}),
    ]


def run_jar_mutations(inp, st, entries, base_failed):
    results = {}
    for label, prefix, fn in jar_mutations():
        ck = Checks()
        jar_suite(ck, inp, st, fn(entries))
        real = [f for f in ck.failed() if f not in base_failed]
        results[label] = dict(expected_section=prefix, failed=real[:8], crashes=[], detected=any(f.startswith(prefix) for f in real))
    return results


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gametest-log", type=Path)
    parser.add_argument("--jar", type=Path)
    args = parser.parse_args()

    inp, st = collect()
    ck = static_suite(inp, st)
    extra = {}
    log_text = jar_entries = None
    if args.gametest_log:
        log_text = args.gametest_log.read_text(encoding="utf-8", errors="replace")
        extra["gametest_log"] = guarded(ck, "L.log", lambda c: log_suite(c, inp, log_text, args.gametest_log.name))
    if args.jar:
        def jar_run(c):
            nonlocal jar_entries
            jar_entries = read_jar(args.jar)
            jar_suite(c, inp, st, jar_entries)
            return dict(jar=str(args.jar), jar_sha256=sha(args.jar.read_bytes()), jar_bytes=args.jar.stat().st_size)
        extra["jar"] = guarded(ck, "J.jar", jar_run)
    base_failed = set(ck.failed())
    muts = run_mutations(inp, st, base_failed)
    if log_text is not None:
        sub = Checks()
        log_suite(sub, inp, log_text, args.gametest_log.name)
        muts.update(run_log_mutations(inp, log_text, args.gametest_log.name, set(sub.failed())))
    if jar_entries is not None:
        sub = Checks()
        jar_suite(sub, inp, st, jar_entries)
        muts.update(run_jar_mutations(inp, st, jar_entries, set(sub.failed())))
    undetected = [k for k, v in muts.items() if not v["detected"]]

    facts = dict(
        original_rows=inp.rows, original_enum=inp.original_enum, deferred_original=inp.deferred, oredict=inp.oredict_facts,
        mapped_rows={f"{k[0]}:{k[1]}": v for k, v in mapped_rows(inp).items()} if not inp.parse_error else None,
        gametest_annotations=inp.test_annotations, expected_src_delta=sorted(EXPECTED_DELTA),
        thorium_fuel_rod_observation="RodRecipes.java:30 addZIRNOXRod(billet_thorium_fuel, THORIUM_FUEL) is outside the fixed 22C scope and has no NEO recipe (reported, not added)")
    production = {p: st.hashes.get(p) for p in (PROVIDER, TESTS)}
    report = dict(
        command=" ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        summary=dict(checks_passed=ck.passed(), checks_failed=len(ck.failed()), mutations_detected=len(muts) - len(undetected), mutations_total=len(muts)),
        failed=ck.failed(), undetected_mutations=undetected, checks=ck.items, facts=facts, mutations=muts, extra=extra,
        production_sha256=production, start_target_head=inp.baseline.get("target_head"), original_head=ORIGINAL_HEAD)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for item in ck.items:
        if item["status"] == "FAIL":
            print(f"FAIL {item['id']}: {item['label']} :: {item['detail']}")
    for label, value in muts.items():
        print(f"{'DETECTED' if value['detected'] else 'MISSED':8} mutation {label}: {value['failed'][:4]}" + (f" crashes={value['crashes']}" if value["crashes"] else ""))
    failed = ck.failed()
    print(f"Goal22C fuel: {ck.passed()} checks passed; {len(muts) - len(undetected)}/{len(muts)} mutations detected"
          + (f"; FAILED checks: {failed}" if failed else "") + (f"; UNDETECTED: {undetected}" if undetected else ""))
    sys.exit(0 if not failed and not undetected else 1)


if __name__ == "__main__":
    main()
